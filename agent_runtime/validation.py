"""Typed evidence plans and honest outcomes without implicit source access."""

from __future__ import annotations

from typing import Any

from .contracts import CONTRACT, ContractViolation, error_result, validate_input, validate_result


VERSION = CONTRACT["contractVersion"]

_PLANS: dict[str, list[tuple[str, str]]] = {
    "study_result": [
        ("study", "Reabrir o estudo e conferir método, população, data e limitações."),
        ("scholarly_repository", "Localizar e comparar o estudo em repositórios acadêmicos adequados."),
    ],
    "official_indicator": [
        ("official_indicator", "Consultar a fonte oficial competente e conferir período e localidade."),
    ],
    "registry_record": [
        ("public_registry", "Consultar o cadastro público competente e conferir os identificadores aplicáveis."),
    ],
    "standard_or_norm": [
        ("standards_body", "Conferir a entidade emissora, edição, vigência e cláusula pertinente."),
    ],
    "offer_or_price": [
        ("seller_or_offer", "Reabrir a oferta original atual e conferir variante, preço e condições exatas."),
    ],
    "technical_documentation": [
        ("technical_documentation", "Conferir a documentação original do publicador e a versão correspondente."),
    ],
    "authorized_system_record": [
        ("authorized_system_record", "Consultar o registro somente após configurar conector autorizado e de privilégio mínimo."),
    ],
    "general_fact": [
        ("other", "Identificar e reabrir a fonte primária ou competente para o domínio; não há lista global de sites permitidos."),
    ],
    "other": [
        ("other", "Determinar pelo contexto o tipo de fonte competente e reabri-la independentemente."),
    ],
}


def verify_claim(payload: dict[str, Any]) -> dict[str, Any]:
    plan = [
        {"sourceKind": source_kind, "reason": reason}
        for source_kind, reason in _PLANS[payload["dataType"]]
    ]
    unresolved = ["Nenhum conector de fonte está configurado; referências candidatas não foram reabertas."]
    if payload["candidateReferences"]:
        unresolved.append("Referências candidatas não são prova e não foram reabertas independentemente.")
    if payload["dataType"] == "authorized_system_record":
        unresolved.append("Não foi fornecida autorização de sistema nem conector autorizado.")
    if payload.get("userFilters"):
        unresolved.append("Filtros do usuário não foram conferidos em uma fonte independente.")
    unresolved.append("Formato não conferido: a solicitação não inclui regra ou esquema de formato.")
    result = {
        "contractVersion": VERSION,
        "verdict": "inconclusive",
        "formatCheck": "not_checked",
        "scope": "Afirmação e contexto recebidos; evidência factual e regra de formato permanecem sem verificação.",
        "evidence": [],
        "verificationPlan": plan,
        "unresolved": unresolved,
    }
    validate_result("validation.verifyClaim", result)
    return result


def audit_search_results(payload: dict[str, Any]) -> dict[str, Any]:
    audits = []
    for candidate in payload["candidates"]:
        audits.append(
            {
                "reference": candidate["reference"],
                "reopened": False,
                "filterResults": [
                    {
                        "filterId": required_filter["id"],
                        "status": "unverifiable",
                        "evidence": "Sem abridor independente de fonte; trecho da Busca não constitui verificação.",
                    }
                    for required_filter in payload["requiredFilters"]
                ],
                "decision": "inconclusive",
            }
        )
    result = {"contractVersion": VERSION, "audits": audits}
    validate_result("validation.auditSearchResults", result)
    return result


def execute(tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_input(tool_name, payload)
        if tool_name == "validation.verifyClaim":
            return verify_claim(payload)
        if tool_name == "validation.auditSearchResults":
            return audit_search_results(payload)
        raise ContractViolation("Unknown tool")
    except ContractViolation as exc:
        return error_result("invalid_request", str(exc))
    except (KeyError, TypeError, ValueError):
        return error_result("internal_error", "The validation request could not be completed.")
