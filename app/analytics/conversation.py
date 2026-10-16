"""可序列化的连续问数状态：继承、替换和清除分开处理。"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import asdict, dataclass, field
from threading import RLock


@dataclass
class StructuredQueryState:
    metrics: list[str] = field(default_factory=list)
    time_range: str | None = None
    dimensions: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)
    sort: str | None = None
    limit: int | None = None


class ConversationStateStore:
    """进程内短期记忆；生产多副本部署时替换为 Redis 即可。"""

    def __init__(self) -> None:
        self._states: dict[str, tuple[deque[str], StructuredQueryState]] = {}
        self._lock = RLock()

    def hydrate(self, session_id: str, question: str) -> dict:
        with self._lock:
            history, state = self._states.setdefault(session_id, (deque(maxlen=6), StructuredQueryState()))
            self._update(state, question)
            context = list(history)
            history.append(question)
            structured = asdict(state)
            return {
                "conversation_context": context,
                "structured_query": structured,
                "analysis_query": self._full_intent(question, structured),
                "correction_attempts": 0,
            }

    def merge_semantic_parse(self, session_id: str, parsed: dict) -> dict:
        """将 LLM 解析出的指标/维度/条件与当前会话状态做显式合并。"""
        with self._lock:
            _history, state = self._states.setdefault(session_id, (deque(maxlen=6), StructuredQueryState()))
            for name in ("metrics", "dimensions", "filters"):
                values = parsed.get(name)
                if isinstance(values, list) and values:
                    cleaned = [str(value).strip() for value in values if str(value).strip()]
                    if name == "filters" and parsed.get("replace_filters"):
                        setattr(state, name, cleaned)
                    else:
                        merged = list(dict.fromkeys([*getattr(state, name), *cleaned]))
                        setattr(state, name, merged)
            for name in ("time_range", "sort", "limit"):
                value = parsed.get(name)
                if value not in (None, "", []):
                    setattr(state, name, value)
            return asdict(state)

    @staticmethod
    def full_intent(question: str, state: dict) -> str:
        return ConversationStateStore._full_intent(question, state)

    @staticmethod
    def _update(state: StructuredQueryState, question: str) -> None:
        # 不将业务术语硬编码为唯一真相；模型/Schema 检索仍决定最终字段和指标。
        replacements = any(marker in question for marker in ("改成", "改为", "换成", "替换为"))
        time_match = re.search(r"(?:近|最近)\s*\d+\s*(?:天|周|月)|本月|本季度|今年|去年", question)
        if time_match:
            state.time_range = time_match.group(0)
        limit_match = re.search(r"(?:前|top)\s*(\d+)", question, re.IGNORECASE)
        if limit_match:
            state.limit = int(limit_match.group(1))
        if any(token in question for token in ("最低", "最小", "升序", "从低到高")):
            state.sort = "ascending"
        elif any(token in question for token in ("最高", "最大", "降序", "从高到低")):
            state.sort = "descending"
        candidates = [part.strip() for part in re.split(r"[、，,和与]", question) if 1 < len(part.strip()) < 30]
        if replacements and candidates:
            state.filters = candidates[-1:]

    @staticmethod
    def _full_intent(question: str, state: dict) -> str:
        inherited = [f"{key}={value}" for key, value in state.items() if value not in (None, [], "")]
        return question if not inherited else f"{question}\n继承的分析状态：{'；'.join(inherited)}"


conversation_state_store = ConversationStateStore()
