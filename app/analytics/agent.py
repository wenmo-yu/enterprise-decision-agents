"""将语义问数能力作为当前平台内的 LangGraph 子图运行。

节点顺序保持为：状态继承 → 三路 Schema 检索 → Schema 依赖扩展 → SQL 生成 →
只读预检 → 一次纠错 → 有上限执行。它不经过本地 HTTP 或另一个仓库的服务进程。
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, TypedDict

import httpx
from elasticsearch import AsyncElasticsearch
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlglot import exp, parse

from app.agent.llm import model
from app.analytics.conversation import conversation_state_store
from app.analytics.settings import AnalyticsSettings


class AnalyticsState(TypedDict, total=False):
    question: str
    session_id: str
    analysis_query: str
    conversation_context: list[str]
    structured_query: dict[str, Any]
    correction_attempts: int
    columns: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    values: list[dict[str, Any]]
    schema_context: list[dict[str, Any]]
    sql: str
    error: str | None
    result: list[dict[str, Any]]


class ReadOnlySQLGuard:
    """程序级拒绝写 SQL、多语句和文件读写函数。"""

    @staticmethod
    def validate(sql: str) -> str:
        if re.search(r"\b(for\s+update|lock\s+in\s+share\s+mode)\b", sql, flags=re.IGNORECASE):
            raise ValueError("不允许带锁的读取语句")
        try:
            statements = parse(sql, read="mysql")
        except Exception as exc:
            raise ValueError("SQL 解析失败，仅允许一条只读查询") from exc
        if len(statements) != 1 or not isinstance(statements[0], exp.Query):
            raise ValueError("仅允许一条 SELECT 或 WITH 查询")
        forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Command)
        if any(isinstance(node, forbidden) for node in statements[0].walk()):
            raise ValueError("检测到非只读 SQL 操作")
        if any(token in sql.lower() for token in ("into outfile", "into dumpfile", "load_file(")):
            raise ValueError("不允许文件读写相关 SQL")
        return statements[0].sql(dialect="mysql")


class LocalAnalyticsAgent:
    """以当前进程的 Qdrant、Elasticsearch 与 MySQL 资源运行问数子图。"""

    def __init__(self, settings: AnalyticsSettings | None = None) -> None:
        self.settings = settings or AnalyticsSettings.from_env()

    async def run(self, question: str, session_id: str) -> dict[str, Any]:
        self.settings.validate()
        state = {"question": question, "session_id": session_id, **conversation_state_store.hydrate(session_id, question)}
        graph = self._build_graph()
        result = await graph.ainvoke(state)
        if result.get("error"):
            return {"execution_status": "failed", "error": result["error"], "structured_query": result.get("structured_query", {})}
        return {
            "execution_status": "completed",
            "data": result.get("result", []),
            "sql_audit": {"sql": result.get("sql"), "read_only": True, "max_rows": self.settings.max_rows},
            "structured_query": result.get("structured_query", {}),
            "retrieval": {"columns": len(result.get("columns", [])), "metrics": len(result.get("metrics", [])), "values": len(result.get("values", []))},
        }

    def _build_graph(self):
        graph = StateGraph(AnalyticsState)
        graph.add_node("retrieve_schema", self._retrieve_schema)
        graph.add_node("expand_schema", self._expand_schema)
        graph.add_node("generate_sql", self._generate_sql)
        graph.add_node("validate_sql", self._validate_sql)
        graph.add_node("correct_sql", self._correct_sql)
        graph.add_node("run_sql", self._run_sql)
        graph.add_node("report_failure", lambda state: {"error": state.get("error") or "问数失败"})
        graph.add_edge(START, "retrieve_schema")
        graph.add_edge("retrieve_schema", "expand_schema")
        graph.add_edge("expand_schema", "generate_sql")
        graph.add_edge("generate_sql", "validate_sql")
        graph.add_conditional_edges(
            "validate_sql",
            lambda state: "run_sql" if not state.get("error") else "correct_sql" if state.get("correction_attempts", 0) < 1 else "report_failure",
            {"run_sql": "run_sql", "correct_sql": "correct_sql", "report_failure": "report_failure"},
        )
        graph.add_edge("correct_sql", "validate_sql")
        graph.add_edge("run_sql", END)
        graph.add_edge("report_failure", END)
        return graph.compile()

    def _openai(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "not-configured"), base_url=os.getenv("OPENAI_BASE_URL"))

    async def _embedding(self, query: str) -> list[float]:
        client = self._openai()
        try:
            response = await client.embeddings.create(model=self.settings.embedding_model, input=query)
            return response.data[0].embedding
        finally:
            await client.close()

    async def _retrieve_schema(self, state: AnalyticsState) -> dict[str, Any]:
        """字段、指标 Dense 召回与字段值 ES 召回并行，随后可选 Cross-Encoder 重排。"""
        vector = await self._embedding(state["analysis_query"])
        qdrant = AsyncQdrantClient(url=self.settings.qdrant_url)
        es = AsyncElasticsearch(hosts=[self.settings.elasticsearch_url])
        try:
            columns_task = qdrant.query_points(collection_name=self.settings.column_collection, query=vector, limit=20)
            metrics_task = qdrant.query_points(collection_name=self.settings.metric_collection, query=vector, limit=12)
            values_task = es.search(index=self.settings.value_index, query={"match": {"value": state["analysis_query"]}}, size=20)
            columns_raw, metrics_raw, values_raw = await asyncio.gather(columns_task, metrics_task, values_task, return_exceptions=True)
            columns = [] if isinstance(columns_raw, Exception) else [dict(point.payload or {}) for point in columns_raw.points]
            metrics = [] if isinstance(metrics_raw, Exception) else [dict(point.payload or {}) for point in metrics_raw.points]
            values = [] if isinstance(values_raw, Exception) else [dict(hit.get("_source", {})) for hit in values_raw.get("hits", {}).get("hits", [])]
            columns = await self._rerank(state["analysis_query"], columns, "description")
            metrics = await self._rerank(state["analysis_query"], metrics, "description")
            return {"columns": columns, "metrics": metrics, "values": values}
        finally:
            await qdrant.close()
            await es.close()

    async def _rerank(self, query: str, candidates: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
        url = os.getenv("ANALYTICS_RERANKER_URL", "").strip()
        if not url or not candidates:
            return candidates
        documents = [str(item.get(field) or item.get("name") or "") for item in candidates]
        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.post(url, json={"query": query, "texts": documents, "return_text": False})
                response.raise_for_status()
                ranking = response.json()
            indexes = [item["index"] for item in ranking if isinstance(item, dict) and isinstance(item.get("index"), int)]
            return [candidates[index] for index in indexes if 0 <= index < len(candidates)]
        except httpx.HTTPError:
            return candidates

    async def _expand_schema(self, state: AnalyticsState) -> dict[str, Any]:
        """补齐被召回表的时间字段和主外键，避免 Join Key 因 Top-K 被遗漏。"""
        table_ids = sorted({str(column.get("table_id")) for column in state.get("columns", []) if column.get("table_id")})
        if not table_ids:
            return {"schema_context": state.get("columns", [])}
        engine = create_async_engine(self.settings.metadata_database_url, pool_pre_ping=True)
        try:
            async with engine.connect() as connection:
                dependency_query = text("""
                    SELECT id, table_id, name, type, role, description, alias
                    FROM column_info
                    WHERE table_id IN :table_ids
                      AND (role IN ('primary_key', 'foreign_key')
                           OR name IN ('date', 'date_id', 'year', 'quarter', 'month', 'day'))
                """).bindparams(bindparam("table_ids", expanding=True))
                result = await connection.execute(dependency_query, {"table_ids": table_ids})
                dependencies = [dict(row) for row in result.mappings().all()]
            merged = {str(item.get("id") or item.get("name")): item for item in state.get("columns", [])}
            for column in dependencies:
                merged.setdefault(str(column.get("id") or column.get("name")), column)
            return {"schema_context": list(merged.values())}
        finally:
            await engine.dispose()

    async def _generate_sql(self, state: AnalyticsState) -> dict[str, Any]:
        instruction = """你是企业经营问数专家。仅基于提供的 Schema 与指标口径生成一条 MySQL SELECT 或 WITH 查询。
禁止写操作、禁止多语句、禁止猜测未提供字段。只输出 SQL，不要 Markdown。"""
        payload = {
            "question": state["analysis_query"], "structured_query": state.get("structured_query", {}),
            "history": state.get("conversation_context", []), "columns": state.get("schema_context", []),
            "metrics": state.get("metrics", []), "value_candidates": state.get("values", []),
        }
        response = await model.ainvoke([SystemMessage(content=instruction), HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str))])
        return {"sql": str(response.content).strip().removeprefix("```sql").removesuffix("```").strip(), "error": None}

    async def _validate_sql(self, state: AnalyticsState) -> dict[str, Any]:
        try:
            safe_sql = ReadOnlySQLGuard.validate(state.get("sql", ""))
            engine = create_async_engine(self.settings.warehouse_database_url, pool_pre_ping=True)
            try:
                async with engine.connect() as connection:
                    await asyncio.wait_for(connection.execute(text(f"EXPLAIN {safe_sql}")), timeout=self.settings.timeout_seconds)
            finally:
                await engine.dispose()
            return {"sql": safe_sql, "error": None}
        except Exception as error:
            return {"error": str(error)}

    async def _correct_sql(self, state: AnalyticsState) -> dict[str, Any]:
        prompt = "修复以下 SQL，使其成为一条只读 MySQL 查询。仅输出 SQL。"
        response = await model.ainvoke([SystemMessage(content=prompt), HumanMessage(content=json.dumps({"sql": state.get("sql"), "error": state.get("error"), "schema": state.get("schema_context", [])}, ensure_ascii=False, default=str))])
        return {"sql": str(response.content).strip().removeprefix("```sql").removesuffix("```").strip(), "correction_attempts": state.get("correction_attempts", 0) + 1}

    async def _run_sql(self, state: AnalyticsState) -> dict[str, Any]:
        safe_sql = ReadOnlySQLGuard.validate(state["sql"])
        engine = create_async_engine(self.settings.warehouse_database_url, pool_pre_ping=True)
        try:
            async with engine.connect() as connection:
                result = await asyncio.wait_for(connection.execute(text(safe_sql)), timeout=self.settings.timeout_seconds)
                rows = [dict(row) for row in result.mappings().fetchmany(self.settings.max_rows)]
            return {"result": rows, "error": None}
        finally:
            await engine.dispose()
