from __future__ import annotations

import copy
import unittest

from agent_runtime.contracts import TOOLS
from agent_runtime.validation import execute


class ConsumerRuleApplicationTests(unittest.TestCase):
    def _payload(self, definitions, fields):
        request = copy.deepcopy(TOOLS["validation.inspectConsumerRuleBundle"]["examples"]["validInput"])
        request["rules"] = [
            {
                "id": f"rule-{index}",
                "version": "1.0.0",
                "origin": f"https://consumer.example.invalid/rules/{index}",
                "scope": request["bundle"]["scope"],
                "definition": definition,
            }
            for index, definition in enumerate(definitions, start=1)
        ]
        receipt = execute("validation.inspectConsumerRuleBundle", request)
        return {"contractVersion": "1.0.0", "bundleReceipt": receipt, "fields": fields}

    def test_applies_required_interval_enum_and_cross_field_rules(self):
        payload = self._payload(
            [
                "field.sampleSize.required=true",
                "field.sampleSize.minimum=1",
                "field.sampleSize.maximum=10",
                'field.status.enum=["accepted","pending"]',
                "field.start.required=true",
                "field.end.required=true",
                "relation.start.less_or_equal.end=true",
            ],
            [
                {"id": "sampleSize", "type": "decimal", "value": "3"},
                {"id": "status", "type": "text", "value": "accepted"},
                {"id": "start", "type": "date", "value": "2026-01-01"},
                {"id": "end", "type": "date", "value": "2026-01-02"},
            ],
        )
        result = execute("validation.applyConsumerRules", payload)

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["consistencyStatus"], "consistent")
        self.assertEqual(result["veracityStatus"], "not_checked")
        self.assertEqual(len(result["ruleResults"]), 7)
        self.assertEqual({item["status"] for item in result["ruleResults"]}, {"pass"})
        self.assertEqual(result["authority"], "none")

    def test_required_missing_value_fails_and_names_consumer_rule(self):
        result = execute(
            "validation.applyConsumerRules",
            self._payload(["field.sampleSize.required=true"], [{"id": "sampleSize", "type": "decimal"}]),
        )

        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["fields"][0]["status"], "invalid")
        self.assertEqual(result["ruleResults"][0]["ruleId"], "rule-1")
        self.assertEqual(result["ruleResults"][0]["status"], "fail")

    def test_optional_missing_value_is_permitted_by_consumer_rule(self):
        result = execute(
            "validation.applyConsumerRules",
            self._payload(["field.note.required=false"], [{"id": "note", "type": "text"}]),
        )

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["fields"][0]["status"], "missing")
        self.assertIn("opcional ausente", result["fields"][0]["detail"])

    def test_missing_value_without_consumer_requiredness_is_inconclusive(self):
        result = execute(
            "validation.applyConsumerRules",
            self._payload(["field.note.enum=[\"known\"]"], [{"id": "note", "type": "text"}]),
        )

        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["ruleResults"][0]["status"], "not_evaluated")
        self.assertTrue(any("note" in item for item in result["unresolved"]))

    def test_interval_and_enum_violations_identify_failing_rule(self):
        interval = execute(
            "validation.applyConsumerRules",
            self._payload(["field.score.minimum=1", "field.score.maximum=5"], [{"id": "score", "type": "decimal", "value": "6"}]),
        )
        enumeration = execute(
            "validation.applyConsumerRules",
            self._payload(['field.status.enum=["active","pending"]'], [{"id": "status", "type": "text", "value": "deleted"}]),
        )

        self.assertEqual(interval["status"], "invalid")
        self.assertEqual(interval["ruleResults"][-1]["status"], "fail")
        self.assertEqual(enumeration["status"], "invalid")
        self.assertEqual(enumeration["ruleResults"][0]["status"], "fail")

    def test_cross_field_failure_and_missing_value_are_not_conflated(self):
        failed = execute(
            "validation.applyConsumerRules",
            self._payload(
                ["relation.start.less_or_equal.end=true"],
                [{"id": "start", "type": "date", "value": "2026-02-02"}, {"id": "end", "type": "date", "value": "2026-02-01"}],
            ),
        )
        missing = execute(
            "validation.applyConsumerRules",
            self._payload(
                ["relation.start.less_or_equal.end=true"],
                [{"id": "start", "type": "date", "value": "2026-02-02"}, {"id": "end", "type": "date"}],
            ),
        )

        self.assertEqual(failed["status"], "invalid")
        self.assertEqual(failed["consistencyStatus"], "inconsistent")
        self.assertEqual(missing["status"], "inconclusive")
        self.assertEqual(missing["relations"][0]["status"], "not_evaluated")

    def test_conflicting_rules_have_no_precedence(self):
        result = execute(
            "validation.applyConsumerRules",
            self._payload(
                ["field.score.minimum=1", "field.score.minimum=2"],
                [{"id": "score", "type": "decimal", "value": "3"}],
            ),
        )

        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["fields"], [])
        self.assertIn("precedência", result["unresolved"][0])

    def test_contradictory_interval_is_reported_without_evaluating_fields(self):
        result = execute(
            "validation.applyConsumerRules",
            self._payload(
                ["field.score.minimum=10", "field.score.maximum=5"],
                [{"id": "score", "type": "decimal", "value": "7"}],
            ),
        )

        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["fields"], [])
        self.assertEqual({item["status"] for item in result["ruleResults"]}, {"conflict"})

    def test_unknown_rule_fails_closed_without_partial_application(self):
        result = execute(
            "validation.applyConsumerRules",
            self._payload(["field.score.regex=^[0-9]+$"], [{"id": "score", "type": "text", "value": "123"}]),
        )

        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["fields"], [])
        self.assertEqual(result["ruleResults"][0]["status"], "not_evaluated")

    def test_bundle_digest_is_checked_before_evaluation(self):
        payload = self._payload(["field.score.minimum=1"], [{"id": "score", "type": "decimal", "value": "2"}])
        payload["bundleReceipt"]["rules"][0]["definitionDigest"] = "0" * 64
        result = execute("validation.applyConsumerRules", payload)

        self.assertEqual(result["code"], "invalid_request")

    def test_optional_quantity_is_not_silently_converted_for_ranges(self):
        result = execute(
            "validation.applyConsumerRules",
            self._payload(
                ["field.weight.minimum=1 kg"],
                [{"id": "weight", "type": "quantity", "value": "1500", "unit": "g", "allowedUnits": ["kg", "g"]}],
            ),
        )

        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["ruleResults"][0]["status"], "not_evaluated")
        self.assertIn("não houve conversão", result["ruleResults"][0]["detail"])


if __name__ == "__main__":
    unittest.main()
