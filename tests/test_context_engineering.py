import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from app.context_engineering.runtime import (
    BudgetExceeded,
    end_run,
    record_evidence,
    reserve_expert_call,
    start_run,
)
from app.analytics.agent import LocalAnalyticsAgent
from app.analytics.conversation import ConversationStateStore
from app.tools.markdown_tools import generate_markdown
from app.orchestration.parallel_research import _collect_fast_path
from app.evals.trajectory import evaluate_trajectory
from app.tools.evidence_tools import verify_claim_support


class ContextEngineeringTests(unittest.TestCase):
    def test_call_budget_is_a_programmatic_guardrail(self):
        with tempfile.TemporaryDirectory() as directory:
            token = start_run(directory)
            try:
                # Directly lower the test run limit without altering machine-wide environment.
                from app.context_engineering.runtime import current_state

                current_state().max_expert_calls = 1
                reserve_expert_call("external_intelligence", "test")
                with self.assertRaises(BudgetExceeded):
                    reserve_expert_call("internal_knowledge", "test")
            finally:
                summary = end_run(token)
            self.assertEqual(summary["expert_calls"], 1)

    def test_claim_validator_requires_registered_evidence_and_quote(self):
        with tempfile.TemporaryDirectory() as directory:
            token = start_run(directory)
            try:
                evidence_id = record_evidence("经营数据", {"summary": "收入下降 12%"})
                result = json.loads(
                    verify_claim_support.invoke(
                        {
                            "claims_json": json.dumps(
                                [{"claim": "收入下降 12%", "evidence_ids": [evidence_id], "evidence_quote": "收入下降 12%"}],
                                ensure_ascii=False,
                            )
                        }
                    )
                )
                self.assertEqual(result["review"][0]["support_level"], "direct")
                missing = json.loads(
                    verify_claim_support.invoke(
                        {"claims_json": '[{"claim":"增长","evidence_ids":["ev_missing"]}]'}
                    )
                )
                self.assertEqual(missing["review"][0]["support_level"], "insufficient")
            finally:
                end_run(token)

    def test_trajectory_eval_checks_expected_experts(self):
        result = evaluate_trajectory(
            [
                {"event": "expert_started", "expert": "external_intelligence"},
                {"event": "expert_started", "expert": "analytics"},
            ],
            {"required_experts": ["external_intelligence", "internal_knowledge"]},
        )
        self.assertFalse(result["passed"])
        self.assertEqual(result["missing_experts"], ["internal_knowledge"])

    def test_embedded_analytics_graph_builds_without_infrastructure(self):
        self.assertIsNotNone(LocalAnalyticsAgent()._build_graph())

    def test_semantic_parse_merges_metrics_dimensions_and_replaces_filters(self):
        store = ConversationStateStore()
        store.hydrate("session", "近30天收入")
        merged = store.merge_semantic_parse(
            "session",
            {
                "metrics": ["收入", "利润率"],
                "dimensions": ["区域", "产品线"],
                "filters": ["华北"],
                "replace_filters": True,
                "time_range": "近30天",
                "limit": 10,
            },
        )
        self.assertEqual(merged["metrics"], ["收入", "利润率"])
        self.assertEqual(merged["dimensions"], ["区域", "产品线"])
        self.assertEqual(merged["filters"], ["华北"])
        self.assertEqual(merged["limit"], 10)

    def test_formal_report_requires_claim_support_review(self):
        with tempfile.TemporaryDirectory() as directory:
            token = start_run(directory)
            try:
                result = generate_markdown.invoke({"content": "# report", "filename": "report"})
                self.assertIn("必须先完成 verify_claim_support", result)
            finally:
                end_run(token)

    def test_parallel_fast_path_keeps_other_sources_alive_after_one_failure(self):
        async def failing_operation():
            raise ConnectionError("external service unavailable")

        result = asyncio.run(_collect_fast_path("external_intelligence", failing_operation()))
        self.assertEqual(result["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
