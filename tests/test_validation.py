from __future__ import annotations

import unittest

from agent_runtime.contracts import TOOLS
from agent_runtime.validation import execute


class ValidationRuntimeTests(unittest.TestCase):
    def test_plans_match_claim_data_type_without_claiming_a_verdict(self):
        expected = {
            "study_result": {"study", "scholarly_repository"},
            "official_indicator": {"official_indicator"},
            "registry_record": {"public_registry"},
            "standard_or_norm": {"standards_body"},
            "offer_or_price": {"seller_or_offer"},
            "technical_documentation": {"technical_documentation"},
            "authorized_system_record": {"authorized_system_record"},
            "general_fact": {"other"},
            "other": {"other"},
        }
        template = TOOLS["validation.verifyClaim"]["examples"]["validInput"]
        for data_type, kinds in expected.items():
            with self.subTest(data_type=data_type):
                result = execute("validation.verifyClaim", dict(template, dataType=data_type, candidateReferences=[]))
                self.assertEqual(result["verdict"], "inconclusive")
                self.assertEqual(result["formatCheck"], "not_checked")
                self.assertEqual({item["sourceKind"] for item in result["verificationPlan"]}, kinds)
                self.assertEqual(result["evidence"], [])

    def test_system_record_requires_authorized_source(self):
        template = TOOLS["validation.verifyClaim"]["examples"]["validInput"]
        result = execute(
            "validation.verifyClaim",
            dict(template, dataType="authorized_system_record", candidateReferences=[]),
        )
        self.assertTrue(any("autorização" in item.lower() for item in result["unresolved"]))
        self.assertEqual(result["verdict"], "inconclusive")

    def test_candidates_are_never_treated_as_reopened_evidence(self):
        template = TOOLS["validation.verifyClaim"]["examples"]["validInput"]
        result = execute("validation.verifyClaim", dict(template, userFilters=["categoria=camisa", "cor=branca"]))
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["verdict"], "inconclusive")
        self.assertTrue(any("não foram reabertas independentemente" in item.lower() for item in result["unresolved"]))
        self.assertTrue(any("filtros do usuário" in item.lower() for item in result["unresolved"]))

    def test_search_audit_keeps_every_filter_and_does_not_trust_excerpt(self):
        template = TOOLS["validation.auditSearchResults"]["examples"]["validInput"]
        result = execute("validation.auditSearchResults", template)
        audit = result["audits"][0]
        self.assertFalse(audit["reopened"])
        self.assertEqual(audit["decision"], "inconclusive")
        self.assertEqual([item["filterId"] for item in audit["filterResults"]], ["category", "color", "size"])
        self.assertEqual({item["status"] for item in audit["filterResults"]}, {"unverifiable"})
        self.assertTrue(all("trecho da Busca não constitui verificação" in item["evidence"] for item in audit["filterResults"]))

    def test_empty_search_result_set_stays_empty(self):
        template = TOOLS["validation.auditSearchResults"]["examples"]["validInput"]
        result = execute("validation.auditSearchResults", dict(template, candidates=[]))
        self.assertEqual(result["audits"], [])

    def test_invalid_request_fails_with_contract_error(self):
        invalid = dict(TOOLS["validation.verifyClaim"]["examples"]["invalidInput"])
        result = execute("validation.verifyClaim", invalid)
        self.assertEqual(result["code"], "invalid_request")


if __name__ == "__main__":
    unittest.main()
