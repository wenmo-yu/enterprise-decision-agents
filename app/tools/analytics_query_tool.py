"""嵌入式经营问数工具：直接调用当前仓库内的 LangGraph 子图。"""

import json
from typing import Any

from langchain_core.tools import tool

from app.analytics.agent import LocalAnalyticsAgent
from app.api.context import get_thread_context
from app.api.monitor import monitor
from app.context_engineering.runtime import BudgetExceeded, record_expert_result, reserve_expert_call


def _bounded(value: Any, *, max_items: int = 50, max_text: int = 2_000) -> tuple[Any, bool]:
    """在数据结构内限制行数与文本长度，保证返回内容仍是合法 JSON。"""
    if isinstance(value, str):
        return value[:max_text], len(value) > max_text
    if isinstance(value, list):
        items, truncated = [], len(value) > max_items
        for item in value[:max_items]:
            bounded, item_truncated = _bounded(item, max_items=max_items, max_text=max_text)
            items.append(bounded)
            truncated = truncated or item_truncated
        return items, truncated
    if isinstance(value, dict):
        result, truncated = {}, False
        for key, item in value.items():
            bounded, item_truncated = _bounded(item, max_items=max_items, max_text=max_text)
            result[key] = bounded
            truncated = truncated or item_truncated
        return result, truncated
    return value, False


@tool
async def analytics_query(question: str, context: str = "") -> str:
    """在当前应用内执行语义问数：Schema 三路检索、SQL 校验、有限纠错与只读执行。"""
    monitor.report_tool("嵌入式经营问数", {"question": question, "has_context": bool(context)})
    try:
        reserve_expert_call("analytics", f"{question}\n{context}")
        full_question = question if not context else f"{question}\n补充上下文：{context}"
        payload = await LocalAnalyticsAgent().run(full_question, get_thread_context() or "decision-platform")
    except BudgetExceeded as error:
        return f"嵌入式经营问数未执行：{error}"
    except Exception as error:
        return f"嵌入式经营问数失败：{error}"

    if payload.get("execution_status") != "completed":
        return f"嵌入式经营问数失败：{payload.get('error', '未知错误')}"
    payload, truncated = _bounded(payload)
    evidence_id, compact, compacted = record_expert_result("analytics", payload, "经营数据")
    if isinstance(compact, dict):
        compact["evidence_id"] = evidence_id
        compact["truncated"] = bool(truncated or compacted)
    return json.dumps(compact, ensure_ascii=False, default=str)
