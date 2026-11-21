from __future__ import annotations

import copy
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from agent_runtime.contracts import TOOLS, error_result
from agent_runtime.orchestration import run_task
from agent_runtime.validation import execute


def _task(stages, **options):
    return {
        "contractVersion": "1.0.0",
        "objective": "Validar uma afirmação e regras do consumidor",
        "stages": stages,
        **options,
    }


def _claim(data_type="study_result", claim="Afirmação sintética A"):
    return dict(
        TOOLS["validation.verifyClaim"]["examples"]["validInput"],
        dataType=data_type,
        claim=claim,
        candidateReferences=[],
    )


class ValidationOrchestrationTests(unittest.TestCase):
    def test_direct_claim_routes_by_type_and_reports_missing_source_inconclusive(self):
        result = run_task(
            _task(
                [
                    {
                        "id": "claim",
                        "tool": "validation.verifyClaim",
                        "input": _claim("study_result"),
                    }
                ]
            )
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verdict"], "inconclusive")
        self.assertIn("study", {item["sourceKind"] for item in result["stages"][0]["result"]["verificationPlan"]})
        self.assertTrue(any("fonte independente" in item for item in result["missingDependencies"]))
        self.assertEqual(result["stages"][0]["mode"], "deterministic")

    def test_composed_inspect_then_apply_consumers_rules_with_validated_reference(self):
        bundle = copy.deepcopy(TOOLS["validation.inspectConsumerRuleBundle"]["examples"]["validInput"])
        result = run_task(
            _task(
                [
                    {"id": "inspect", "tool": "validation.inspectConsumerRuleBundle", "input": bundle},
                    {
                        "id": "apply",
                        "tool": "validation.applyConsumerRules",
                        "dependsOn": ["inspect"],
                        "input": {
                            "contractVersion": "1.0.0",
                            "bundleReceipt": {"$resultFrom": "inspect"},
                            "fields": [{"id": "sampleSize", "type": "decimal", "value": "3"}],
                        },
                    },
                ]
            )
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual([stage["status"] for stage in result["stages"]], ["completed", "completed"])
        self.assertEqual(result["stages"][1]["result"]["status"], "valid")
        self.assertEqual(result["stages"][1]["result"]["veracityStatus"], "not_checked")
        self.assertEqual(result["verdict"], "inconclusive")
        self.assertEqual(result["delegation"]["subagents"], 0)

    def test_search_audit_preserves_every_filter_and_reports_no_opener(self):
        audit = copy.deepcopy(TOOLS["validation.auditSearchResults"]["examples"]["validInput"])
        result = run_task(
            _task([{"id": "audit", "tool": "validation.auditSearchResults", "input": audit}])
        )
        output = result["stages"][0]["result"]["audits"][0]
        self.assertFalse(output["reopened"])
        self.assertEqual(output["decision"], "inconclusive")
        self.assertEqual(len(output["filterResults"]), len(audit["requiredFilters"]))
        self.assertTrue(any("abridor independente" in item for item in result["missingDependencies"]))

    def test_unknown_tool_duplicate_ids_forward_edges_and_unlisted_refs_fail_closed(self):
        claim = {"id": "a", "tool": "validation.verifyClaim", "input": _claim()}
        for stages in (
            [{"id": "a", "tool": "shell", "input": {}}],
            [claim, claim],
            [{"id": "a", "tool": "validation.verifyClaim", "dependsOn": ["later"], "input": _claim()}],
            [
                claim,
                {
                    "id": "b",
                    "tool": "validation.applyConsumerRules",
                    "input": {"contractVersion": "1.0.0", "bundleReceipt": {"$resultFrom": "a"}, "fields": [{"id": "x", "type": "text", "value": "x"}]},
                },
            ],
        ):
            with self.subTest(stages=stages):
                self.assertEqual(run_task(_task(stages))["code"], "invalid_request")

    def test_failed_dependency_blocks_consumer_but_independent_step_runs(self):
        malformed = {"contractVersion": "wrong"}
        result = run_task(
            _task(
                [
                    {"id": "bad", "tool": "validation.verifyClaim", "input": malformed},
                    {"id": "blocked", "tool": "validation.verifyClaim", "dependsOn": ["bad"], "input": _claim()},
                    {"id": "independent", "tool": "validation.verifyClaim", "input": _claim("official_indicator")},
                ]
            )
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual([stage["status"] for stage in result["stages"]], ["failed", "blocked", "completed"])
        self.assertEqual(result["stages"][1]["blockedBy"], ["bad"])
        self.assertIn("official_indicator", {item["sourceKind"] for item in result["stages"][2]["result"]["verificationPlan"]})

    def test_retries_only_explicit_recoverable_error_and_marks_fixture_simulated(self):
        calls = 0

        def fixture(tool, payload):
            nonlocal calls
            calls += 1
            if calls == 1:
                return error_result("unavailable", "synthetic retry", retryable=True)
            return execute(tool, payload)

        result = run_task(
            _task(
                [{"id": "claim", "tool": "validation.verifyClaim", "input": _claim()}],
                limits={"maxAttempts": 2},
            ),
            execute_tool=fixture,
        )
        self.assertEqual(calls, 2)
        self.assertEqual(result["stages"][0]["attempts"], 2)
        self.assertEqual(result["stages"][0]["mode"], "simulated")
        self.assertEqual(result["status"], "completed")

    def test_retry_limit_and_task_limits_are_enforced(self):
        calls = 0

        def unavailable(tool, payload):
            nonlocal calls
            calls += 1
            return error_result("unavailable", "synthetic", retryable=True)

        result = run_task(
            _task(
                [{"id": "claim", "tool": "validation.verifyClaim", "input": _claim()}],
                limits={"maxAttempts": 1},
            ),
            execute_tool=unavailable,
        )
        self.assertEqual(calls, 1)
        self.assertEqual(result["status"], "failed")
        too_many = run_task(
            _task(
                [
                    {"id": f"s{i}", "tool": "validation.verifyClaim", "input": _claim()}
                    for i in range(2)
                ],
                limits={"maxSteps": 1},
            )
        )
        self.assertEqual(too_many["code"], "invalid_request")

    def test_cooperative_cancellation_and_timeout_are_observable(self):
        cancelled = threading.Event()

        def cancel_during_call(tool, payload):
            result = execute(tool, payload)
            cancelled.set()
            return result

        cancelled_result = run_task(
            _task([{"id": "claim", "tool": "validation.verifyClaim", "input": _claim()}]),
            execute_tool=cancel_during_call,
            cancel_event=cancelled,
        )
        self.assertEqual(cancelled_result["status"], "cancelled")
        self.assertEqual(cancelled_result["stages"][0]["status"], "cancelled")
        self.assertNotIn("result", cancelled_result["stages"][0])

        ticks = iter([0.0, 0.0, 0.0, 2.0, 2.0, 2.0])
        timeout_result = run_task(
            _task(
                [{"id": "claim", "tool": "validation.verifyClaim", "input": _claim()}],
                limits={"timeoutMs": 1000},
            ),
            clock=lambda: next(ticks, 2.0),
        )
        self.assertEqual(timeout_result["status"], "timed_out")
        self.assertEqual(timeout_result["stages"][0]["status"], "timed_out")

    def test_checkpoint_resume_revalidates_result_and_skips_completed_stage(self):
        task = _task([{"id": "claim", "tool": "validation.verifyClaim", "input": _claim()}])
        first = run_task(task)
        calls = 0

        def should_not_run(tool, payload):
            nonlocal calls
            calls += 1
            raise AssertionError("completed stage must not be repeated")

        resumed = run_task({**task, "resume": first["checkpoint"]}, execute_tool=should_not_run)
        self.assertEqual(calls, 0)
        self.assertEqual(resumed["taskId"], first["taskId"])
        self.assertEqual(resumed["stages"][0]["mode"], "checkpoint_untrusted")
        self.assertEqual(resumed["verdict"], "inconclusive")
        mismatched = run_task({**_task([{"id": "claim", "tool": "validation.verifyClaim", "input": _claim("study_result", "Outra afirmação")}]), "resume": first["checkpoint"]})
        self.assertEqual(mismatched["code"], "invalid_request")

    def test_simultaneous_requests_keep_ids_objectives_and_sources_separate(self):
        def invoke(data_type, label):
            request = _task([{"id": "claim", "tool": "validation.verifyClaim", "input": _claim(data_type, label)}])
            return run_task(request)

        with ThreadPoolExecutor(max_workers=2) as pool:
            study, indicator = list(pool.map(lambda item: invoke(*item), [("study_result", "Estudo A"), ("official_indicator", "Indicador B")]))
        self.assertNotEqual(study["taskId"], indicator["taskId"])
        self.assertIn("study", {item["sourceKind"] for item in study["stages"][0]["result"]["verificationPlan"]})
        self.assertIn("official_indicator", {item["sourceKind"] for item in indicator["stages"][0]["result"]["verificationPlan"]})
        self.assertEqual(study["objective"], "Validar uma afirmação e regras do consumidor")

    def test_unknown_fields_oversized_task_and_bad_checkpoint_are_rejected(self):
        base = _task([{"id": "claim", "tool": "validation.verifyClaim", "input": _claim()}])
        self.assertEqual(run_task({**base, "shell": "whoami"})["code"], "invalid_request")
        self.assertEqual(run_task(_task([{"id": "claim", "tool": "validation.verifyClaim", "input": {"payload": "x" * 81000}}]))["code"], "limit_exceeded")
        self.assertEqual(run_task({**base, "resume": {"contractVersion": "1.0.0", "taskId": "x" * 36, "objectiveDigest": "0" * 64, "completedStages": []}})["code"], "invalid_request")


if __name__ == "__main__":
    unittest.main()
