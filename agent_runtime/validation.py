"""Typed evidence plans and honest outcomes without implicit source access."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from .contracts import CONTRACT, ContractViolation, error_result, validate_input, validate_result
from .consumer_rules import inspect_consumer_rule_bundle


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
}

_DECIMAL_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_CHECK_DIGIT_OPERATORS = {"equals", "not_equals"}
_ORDER_OPERATORS = {
    "less_than",
    "less_or_equal",
    "greater_than",
    "greater_or_equal",
}


def _cpf_has_valid_check_digits(value: str) -> bool:
    if re.fullmatch(r"[0-9]{11}", value) is None or len(set(value)) == 1:
        return False

    digits = [int(char) for char in value]
    first_sum = sum(digit * weight for digit, weight in zip(digits[:9], range(10, 1, -1)))
    first_check = (first_sum * 10) % 11
    if first_check == 10:
        first_check = 0
    if digits[9] != first_check:
        return False

    second_sum = sum(digit * weight for digit, weight in zip(digits[:10], range(11, 1, -1)))
    second_check = (second_sum * 10) % 11
    if second_check == 10:
        second_check = 0
    return digits[10] == second_check


def _parse_field_value(field: dict[str, Any]) -> tuple[Any, str, str]:
    field_type = field["type"]
    if "value" not in field:
        if field["required"]:
            return None, "invalid", "Campo obrigatório ausente."
        return None, "missing", "Campo opcional ausente; nenhuma regra foi aprovada por ausência."

    value = field["value"]
    if field_type == "cpf":
        if not _cpf_has_valid_check_digits(value):
            return None, "invalid", "CPF com formato ou dígitos verificadores inválidos."
        return value, "valid", "Formato e dígitos verificadores válidos; identidade não verificada."
    if field_type == "date":
        if _DATE_PATTERN.fullmatch(value) is None:
            return None, "invalid", "Use uma data ISO válida no formato AAAA-MM-DD."
        try:
            return date.fromisoformat(value), "valid", "Data ISO válida."
        except ValueError:
            return None, "invalid", "A data não existe no calendário."
    if field_type in {"decimal", "quantity"}:
        if _DECIMAL_PATTERN.fullmatch(value) is None:
            return None, "invalid", "Use um decimal canônico com ponto, sem separador de milhar ou expoente."
        try:
            number = Decimal(value)
        except InvalidOperation:
            return None, "invalid", "Valor decimal inválido."
        if field_type == "quantity":
            unit = field["unit"]
            if unit not in field["allowedUnits"]:
                return None, "invalid", "A unidade não consta no conjunto declarado pelo consumidor."
            return (number, unit), "valid", "Valor decimal e unidade compatíveis com a declaração do consumidor; sem conversão."
        return number, "valid", "Formato decimal válido."
    if field_type == "text":
        if not value.strip():
            return None, "invalid", "O valor textual está vazio."
        return value, "valid", "Valor textual presente; nenhuma veracidade foi verificada."
    raise ContractViolation("Unsupported field type")


def _compare_relation(
    left: dict[str, Any],
    right: dict[str, Any],
    operator: str,
    left_value: Any,
    right_value: Any,
) -> tuple[str, str]:
    left_type = left["type"]
    right_type = right["type"]
    if left_type != right_type:
        raise ContractViolation("A relação deve comparar campos do mesmo tipo")
    if operator in _ORDER_OPERATORS and left_type not in {"date", "decimal", "quantity"}:
        raise ContractViolation("Ordenação só é suportada para datas e valores numéricos")
    if operator not in _CHECK_DIGIT_OPERATORS | _ORDER_OPERATORS:
        raise ContractViolation("Operador de relação não suportado")
    if left_type == "quantity" and left["unit"] != right["unit"]:
        return "not_evaluated", "Unidades diferentes; não há conversão declarada."

    if operator == "equals":
        passed = left_value == right_value
    elif operator == "not_equals":
        passed = left_value != right_value
    elif operator == "less_than":
        passed = left_value < right_value
    elif operator == "less_or_equal":
        passed = left_value <= right_value
    elif operator == "greater_than":
        passed = left_value > right_value
    else:
        passed = left_value >= right_value

    if passed:
        return "pass", "A relação declarada pelo consumidor foi satisfeita."
    return "fail", "A relação declarada pelo consumidor não foi satisfeita."


def validate_declared_fields(spec: dict[str, Any]) -> dict[str, Any]:
    """Check consumer-declared field formats and relations without asserting truth."""
    fields = spec["fields"]
    by_id: dict[str, dict[str, Any]] = {}
    parsed_values: dict[str, Any] = {}
    field_results = []
    syntax_states: list[str] = []

    for field in fields:
        field_id = field["id"]
        if field_id in by_id:
            raise ContractViolation("Field identifiers must be unique")
        by_id[field_id] = field

        field_type = field["type"]
        if field_type == "quantity":
            allowed_units = field.get("allowedUnits")
            if "unit" not in field or not allowed_units or len(set(allowed_units)) != len(allowed_units):
                raise ContractViolation("Quantity fields require a unit and unique consumer-declared allowedUnits")
        elif "unit" in field or "allowedUnits" in field:
            raise ContractViolation("Units are only valid for quantity fields")

        parsed_value, status, detail = _parse_field_value(field)
        if status == "valid":
            parsed_values[field_id] = parsed_value
            syntax_states.append("valid")
        elif status == "missing":
            syntax_states.append("incomplete")
        else:
            syntax_states.append("invalid")
        field_results.append({"id": field_id, "status": status, "detail": detail})

    relation_results = []
    for relation in spec["relations"]:
        left_id = relation["leftField"]
        right_id = relation["rightField"]
        if left_id not in by_id or right_id not in by_id:
            raise ContractViolation("Relation references an undeclared field")
        if left_id == right_id:
            raise ContractViolation("Relation must reference two different fields")
        left = by_id[left_id]
        right = by_id[right_id]
        operator = relation["operator"]

        if left["type"] != right["type"]:
            raise ContractViolation("A relation must compare fields of the same type")
        if operator in _ORDER_OPERATORS and left["type"] not in {"date", "decimal", "quantity"}:
            raise ContractViolation("Ordering is supported only for dates and numeric fields")
        if left_id not in parsed_values or right_id not in parsed_values:
            status = "not_evaluated"
            detail = "Campo ausente ou inválido; a relação não foi avaliada."
        else:
            status, detail = _compare_relation(left, right, operator, parsed_values[left_id], parsed_values[right_id])
        relation_results.append(
            {
                "leftField": left_id,
                "operator": operator,
                "rightField": right_id,
                "status": status,
                "detail": detail,
            }
        )

    if "invalid" in syntax_states:
        syntax_status = "invalid"
    elif "incomplete" in syntax_states:
        syntax_status = "incomplete"
    else:
        syntax_status = "valid"

    relation_states = {item["status"] for item in relation_results}
    if not relation_results:
        consistency_status = "not_applicable"
    elif "fail" in relation_states:
        consistency_status = "inconsistent"
    elif "not_evaluated" in relation_states:
        consistency_status = "inconclusive"
    else:
        consistency_status = "consistent"

    if syntax_status == "invalid" or consistency_status == "inconsistent":
        status = "invalid"
    elif syntax_status == "incomplete" or consistency_status == "inconclusive":
        status = "inconclusive"
    else:
        status = "valid"

    result = {
        "status": status,
        "syntaxStatus": syntax_status,
        "consistencyStatus": consistency_status,
        "veracityStatus": "not_checked",
        "fields": field_results,
        "relations": relation_results,
        "notes": ["Veracidade, identidade e autorização não são estabelecidas por checagens estruturais."],
    }
    return result


def verify_claim(payload: dict[str, Any]) -> dict[str, Any]:
    ambiguous_type = payload["dataType"] == "other"
    plan = [] if ambiguous_type else [
        {"sourceKind": source_kind, "reason": reason}
        for source_kind, reason in _PLANS[payload["dataType"]]
    ]
    if ambiguous_type:
        unresolved = ["Tipo de dado ou contexto ambíguo; solicite esclarecimento antes de escolher uma fonte."]
    else:
        unresolved = ["Nenhum conector de fonte está configurado; referências candidatas não foram reabertas."]
    if payload["candidateReferences"]:
        unresolved.append("Referências candidatas não são prova e não foram reabertas independentemente.")
    if payload["dataType"] == "authorized_system_record":
        unresolved.append("Não foi fornecida autorização de sistema nem conector autorizado.")
    if payload.get("userFilters"):
        unresolved.append("Filtros do usuário não foram conferidos em uma fonte independente.")
    field_validation = None
    format_check = "not_checked"
    scope = "Afirmação e contexto recebidos; evidência factual e regra de formato permanecem sem verificação."
    if "fieldValidation" in payload:
        field_validation = validate_declared_fields(payload["fieldValidation"])
        if field_validation["syntaxStatus"] == "valid":
            format_check = "valid"
        elif field_validation["syntaxStatus"] == "invalid":
            format_check = "invalid"
        unresolved.append("Checagens de formato e consistência não verificam a veracidade dos fatos.")
        if any(field["type"] == "cpf" for field in payload["fieldValidation"]["fields"]):
            unresolved.append("Dígitos verificadores de CPF não confirmam identidade.")
        scope = "Campos e relações declarados pelo consumidor foram avaliados; evidência factual permanece sem verificação."
    else:
        unresolved.append("Formato não conferido: a solicitação não inclui regra ou esquema de formato.")
    result = {
        "contractVersion": VERSION,
        "verdict": "inconclusive",
        "formatCheck": format_check,
        "scope": scope,
        "evidence": [],
        "verificationPlan": plan,
        "unresolved": unresolved,
    }
    if field_validation is not None:
        result["fieldValidation"] = field_validation
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
        if tool_name == "validation.inspectConsumerRuleBundle":
            return inspect_consumer_rule_bundle(payload)
        raise ContractViolation("Unknown tool")
    except ContractViolation as exc:
        return error_result("invalid_request", str(exc))
    except (KeyError, TypeError, ValueError):
        return error_result("internal_error", "The validation request could not be completed.")
