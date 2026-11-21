"""Apply a bounded consumer-rule language without executing rule text."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from .contracts import ContractViolation


_FIELD_RULE = re.compile(r"field\.([A-Za-z][A-Za-z0-9_.-]{0,63})\.(required|minimum|maximum|enum)=(.+)\Z")
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_ORDER = {"less_than", "less_or_equal", "greater_than", "greater_or_equal"}


def _rule_identity(rule: dict[str, Any]) -> tuple[str, str, str]:
    return rule["id"], rule["version"], rule["scope"]


def _parse_rules(receipt: dict[str, Any], fields: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    parsed: list[dict[str, Any]] = []
    conflicts: list[dict[str, str]] = []
    identities: dict[tuple[str, str, str], tuple[str, str]] = {}
    targets: dict[tuple[str, ...], tuple[str, str]] = {}

    for rule in receipt["rules"]:
        if rule["scope"] != receipt["bundle"]["scope"]:
            return [], [{"ruleId": rule["id"], "target": rule["scope"], "status": "not_evaluated", "detail": "Regra fora do escopo do pacote; nenhuma regra foi aplicada."}]
        expected_digest = hashlib.sha256(rule["definition"].encode("utf-8")).hexdigest()
        if rule["definitionDigest"] != expected_digest:
            raise ContractViolation("Consumer rule digest does not match its declared definition")

        signature = (rule["origin"], rule["definition"])
        identity = _rule_identity(rule)
        previous_identity = identities.get(identity)
        if previous_identity is not None and previous_identity != signature:
            conflicts.append({"ruleId": rule["id"], "target": rule["scope"], "status": "conflict", "detail": "A identidade declarada tem definições divergentes; nenhuma precedência foi escolhida."})
            continue
        identities[identity] = signature

        field_match = _FIELD_RULE.fullmatch(rule["definition"])
        relation = _match_relation(rule["definition"], fields)
        if field_match:
            field_id, property_name, raw_value = field_match.groups()
            if field_id not in fields:
                conflicts.append({"ruleId": rule["id"], "target": f"field.{field_id}", "status": "fail", "detail": "A regra declara um campo que não foi recebido."})
                continue
            if property_name == "required":
                if raw_value not in {"true", "false"}:
                    return [], [{"ruleId": rule["id"], "target": f"field.{field_id}.required", "status": "not_evaluated", "detail": "Valor de obrigatoriedade não suportado; nenhuma regra foi aplicada."}]
                value: Any = raw_value == "true"
            elif property_name in {"minimum", "maximum"}:
                if len(raw_value) > 128:
                    return [], [{"ruleId": rule["id"], "target": f"field.{field_id}.{property_name}", "status": "not_evaluated", "detail": "Limite excede o formato suportado; nenhuma regra foi aplicada."}]
                value = raw_value
            else:
                try:
                    value = json.loads(raw_value)
                except json.JSONDecodeError:
                    return [], [{"ruleId": rule["id"], "target": f"field.{field_id}.enum", "status": "not_evaluated", "detail": "Enumeração deve ser uma lista JSON de strings; nenhuma regra foi aplicada."}]
                if not isinstance(value, list) or not value or len(value) > 50 or any(not isinstance(item, str) for item in value) or len(set(value)) != len(value):
                    return [], [{"ruleId": rule["id"], "target": f"field.{field_id}.enum", "status": "not_evaluated", "detail": "Enumeração deve conter de 1 a 50 strings distintas; nenhuma regra foi aplicada."}]
            target = ("field", field_id, property_name)
            normalized = json.dumps(value, ensure_ascii=False, sort_keys=True)
            previous_target = targets.get(target)
            if previous_target is not None and previous_target[0] != normalized:
                conflicts.append({"ruleId": rule["id"], "target": ".".join(target), "status": "conflict", "detail": "Regras do consumidor discordam para o mesmo campo; nenhuma precedência foi escolhida."})
                continue
            targets[target] = (normalized, rule["id"])
            parsed.append({"ruleId": rule["id"], "kind": "field", "fieldId": field_id, "property": property_name, "value": value, "target": f"field.{field_id}.{property_name}"})
        elif relation is not None:
            left_id, operator, right_id = relation
            target = ("relation", left_id, operator, right_id)
            previous_target = targets.get(target)
            if previous_target is not None:
                parsed.append({"ruleId": rule["id"], "kind": "relation", "leftField": left_id, "operator": operator, "rightField": right_id, "target": f"relation.{left_id}.{operator}.{right_id}"})
                continue
            targets[target] = ("true", rule["id"])
            parsed.append({"ruleId": rule["id"], "kind": "relation", "leftField": left_id, "operator": operator, "rightField": right_id, "target": f"relation.{left_id}.{operator}.{right_id}"})
        else:
            return [], [{"ruleId": rule["id"], "target": "unsupported", "status": "not_evaluated", "detail": "Sintaxe da regra não suportada; nenhuma regra foi aplicada."}]

    return parsed, conflicts


def _match_relation(definition: str, fields: dict[str, dict[str, Any]]) -> tuple[str, str, str] | None:
    prefix = "relation."
    suffix = "=true"
    if not definition.startswith(prefix) or not definition.endswith(suffix):
        return None
    body = definition[len(prefix) : -len(suffix)]
    matches = [
        (left_id, operator, right_id)
        for left_id in fields
        for operator in ("equals", "not_equals", "less_than", "less_or_equal", "greater_than", "greater_or_equal")
        for right_id in fields
        if body == f"{left_id}.{operator}.{right_id}"
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _parse_bound(field: dict[str, Any], raw: str) -> Any:
    kind = field["type"]
    if kind == "date":
        if _DATE.fullmatch(raw) is None:
            raise ContractViolation("Date bounds must use YYYY-MM-DD")
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise ContractViolation("Date bound is not a calendar date") from exc
    if kind == "decimal":
        if _DECIMAL.fullmatch(raw) is None:
            raise ContractViolation("Decimal bounds must use canonical decimal notation")
        try:
            return Decimal(raw)
        except InvalidOperation as exc:
            raise ContractViolation("Decimal bound is invalid") from exc
    if kind == "quantity":
        parts = raw.rsplit(" ", 1)
        if len(parts) != 2 or _DECIMAL.fullmatch(parts[0]) is None or parts[1] not in field.get("allowedUnits", []):
            raise ContractViolation("Quantity bounds must use a declared value and unit")
        return Decimal(parts[0]), parts[1]
    raise ContractViolation("Intervals are supported only for dates, decimals, and declared quantities")


def _parse_enum_value(field: dict[str, Any], raw: str) -> Any:
    kind = field["type"]
    if kind == "date":
        if _DATE.fullmatch(raw) is None:
            raise ContractViolation("Date enumeration values must use YYYY-MM-DD")
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise ContractViolation("Date enumeration contains an invalid calendar date") from exc
    if kind == "decimal":
        if _DECIMAL.fullmatch(raw) is None:
            raise ContractViolation("Decimal enumeration values must use canonical decimal notation")
        return Decimal(raw)
    if kind == "quantity":
        parts = raw.rsplit(" ", 1)
        if len(parts) != 2 or _DECIMAL.fullmatch(parts[0]) is None or parts[1] not in field.get("allowedUnits", []):
            raise ContractViolation("Quantity enumeration values must use declared values and units")
        return Decimal(parts[0]), parts[1]
    if kind == "cpf":
        from .validation import _parse_field_value

        parsed, status, _ = _parse_field_value({"type": "cpf", "value": raw, "required": True})
        if status != "valid":
            raise ContractViolation("CPF enumeration contains an invalid format")
        return parsed
    return raw


def _evaluate(payload: dict[str, Any], parsed_rules: list[dict[str, Any]]) -> dict[str, Any]:
    from .validation import _compare_relation, _parse_field_value

    field_specs = {field["id"]: field for field in payload["fields"]}
    rules_by_field: dict[str, dict[str, list[dict[str, Any]]]] = {}
    relation_rules = []
    for rule in parsed_rules:
        if rule["kind"] == "relation":
            relation_rules.append(rule)
        else:
            rules_by_field.setdefault(rule["fieldId"], {}).setdefault(rule["property"], []).append(rule)

    for field_id, field_rules in rules_by_field.items():
        minimum_rules = field_rules.get("minimum", [])
        maximum_rules = field_rules.get("maximum", [])
        if not minimum_rules or not maximum_rules:
            continue
        field = field_specs[field_id]
        try:
            minimum = _parse_bound(field, minimum_rules[0]["value"])
            maximum = _parse_bound(field, maximum_rules[0]["value"])
        except ContractViolation:
            continue
        if field["type"] == "quantity" and minimum[1] != maximum[1]:
            continue
        if minimum > maximum:
            rule_results = [
                {"ruleId": rule["ruleId"], "target": rule["target"], "status": "conflict", "detail": "Intervalo declarado não contém valores; nenhuma precedência foi escolhida."}
                for rule in minimum_rules + maximum_rules
            ]
            return {
                "contractVersion": "1.0.0", "status": "conflict", "consistencyStatus": "inconclusive", "veracityStatus": "not_checked",
                "bundle": {"id": payload["bundleReceipt"]["bundle"]["id"], "version": payload["bundleReceipt"]["bundle"]["version"]},
                "fields": [], "relations": [], "ruleResults": rule_results,
                "unresolved": [f"Intervalo contraditório declarado para o campo {field_id}."], "provenance": "declared_only", "authority": "none",
            }

    field_results = []
    parsed_values: dict[str, Any] = {}
    field_states: dict[str, str] = {}
    rule_results: list[dict[str, str]] = []
    unresolved: list[str] = []

    for field_id, field in field_specs.items():
        field_rules = rules_by_field.get(field_id, {})
        required_rules = field_rules.get("required", [])
        required = required_rules[0]["value"] if required_rules else False
        parse_spec = dict(field, required=required)
        parsed, parse_status, parse_detail = _parse_field_value(parse_spec)
        has_value = "value" in field
        if parse_status == "valid":
            parsed_values[field_id] = parsed
        elif parse_status == "missing" and has_value is False and not required_rules:
            unresolved.append(f"Campo {field_id}: ausência sem regra de obrigatoriedade declarada.")

        field_failures = []
        field_inconclusive = parse_status == "missing" and not required_rules
        for required_rule in required_rules:
            required_status = "fail" if not has_value and required else "pass"
            required_detail = "Campo obrigatório ausente conforme regra do consumidor." if required_status == "fail" else "Obrigatoriedade aplicada conforme regra do consumidor."
            if parse_status == "missing" and not required:
                required_detail = "Campo opcional ausente conforme regra do consumidor."
            rule_results.append({"ruleId": required_rule["ruleId"], "target": required_rule["target"], "status": required_status, "detail": required_detail})
            if required_status == "fail":
                field_failures.append(required_rule["ruleId"])

        if parse_status == "invalid":
            field_failures.extend(
                rule["ruleId"]
                for key, rules in field_rules.items()
                if key in {"minimum", "maximum", "enum"}
                for rule in rules
            )
            if not field_failures:
                field_inconclusive = False

        for property_name in ("minimum", "maximum", "enum"):
            for rule in field_rules.get(property_name, []):
                if parse_status == "missing":
                    status = "pass" if required_rules and not required else "not_evaluated"
                    detail = "Campo opcional ausente; restrição não se aplica." if status == "pass" else "Campo ausente; restrição não pôde ser avaliada."
                elif parse_status != "valid":
                    status = "not_evaluated"
                    detail = "Valor inválido; restrição não pôde ser avaliada."
                else:
                    try:
                        if property_name == "enum":
                            allowed = [_parse_enum_value(field, item) for item in rule["value"]]
                            passed = parsed in allowed
                            if field["type"] == "quantity" and not passed and any(item[1] != parsed[1] for item in allowed):
                                status = "not_evaluated"
                                detail = "A enumeração inclui outra unidade; não houve conversão para decidir equivalência."
                                field_inconclusive = True
                                rule_results.append({"ruleId": rule["ruleId"], "target": rule["target"], "status": status, "detail": detail})
                                continue
                            detail = "Valor pertence à enumeração declarada." if passed else "Valor não pertence à enumeração declarada."
                        else:
                            bound = _parse_bound(field, rule["value"])
                            if field["type"] == "quantity" and parsed[1] != bound[1]:
                                status = "not_evaluated"
                                detail = "Unidade diferente da regra declarada; não houve conversão."
                                rule_results.append({"ruleId": rule["ruleId"], "target": rule["target"], "status": status, "detail": detail})
                                field_inconclusive = True
                                continue
                            passed = parsed >= bound if property_name == "minimum" else parsed <= bound
                            detail = "Valor está dentro do limite declarado." if passed else "Valor excede o limite declarado."
                        status = "pass" if passed else "fail"
                    except (ContractViolation, InvalidOperation, TypeError):
                        status = "not_evaluated"
                        detail = "Tipo de campo e regra não podem ser comparados com segurança."
                rule_results.append({"ruleId": rule["ruleId"], "target": rule["target"], "status": status, "detail": detail})
                if status == "fail":
                    field_failures.append(rule["ruleId"])
                elif status == "not_evaluated":
                    field_inconclusive = True

        if field_failures or parse_status == "invalid":
            state = "invalid"
            detail = parse_detail if parse_status == "invalid" else "Uma regra declarada pelo consumidor foi violada."
        elif field_inconclusive:
            state = "missing"
            detail = "Campo sem regra suficiente para decidir sua ausência ou restrições."
        elif parse_status == "missing":
            state = "missing"
            detail = "Campo opcional ausente conforme regra declarada pelo consumidor."
        else:
            state = "valid"
            detail = parse_detail
        field_states[field_id] = state
        field_results.append({"id": field_id, "status": state, "detail": detail})

    relation_results = []
    for rule in relation_rules:
        left_id, right_id = rule["leftField"], rule["rightField"]
        if left_id not in field_specs or right_id not in field_specs:
            status, detail = "fail", "A relação referencia um campo que não foi recebido."
        elif left_id == right_id:
            status, detail = "fail", "A relação deve comparar dois campos diferentes."
        elif field_specs[left_id]["type"] != field_specs[right_id]["type"]:
            status, detail = "fail", "A relação compara campos de tipos diferentes."
        elif rule["operator"] in _ORDER and field_specs[left_id]["type"] not in {"date", "decimal", "quantity"}:
            status, detail = "fail", "Ordenação só é suportada para datas e números."
        elif left_id not in parsed_values or right_id not in parsed_values:
            status, detail = "not_evaluated", "Um dos campos está ausente ou inválido."
        else:
            status, detail = _compare_relation(field_specs[left_id], field_specs[right_id], rule["operator"], parsed_values[left_id], parsed_values[right_id])
        relation_results.append({"ruleId": rule["ruleId"], "leftField": left_id, "operator": rule["operator"], "rightField": right_id, "status": status, "detail": detail})
        rule_results.append({"ruleId": rule["ruleId"], "target": rule["target"], "status": status, "detail": detail})

    states = [item["status"] for item in rule_results]
    if any(state == "fail" for state in states) or any(item["status"] == "invalid" for item in field_results):
        result_status = "invalid"
    elif any(state == "not_evaluated" for state in states) or unresolved:
        result_status = "inconclusive"
    else:
        result_status = "valid"
    relation_states = {item["status"] for item in relation_results}
    if not relation_results:
        consistency = "not_applicable"
    elif "fail" in relation_states:
        consistency = "inconsistent"
    elif "not_evaluated" in relation_states:
        consistency = "inconclusive"
    else:
        consistency = "consistent"

    return {
        "contractVersion": "1.0.0",
        "status": result_status,
        "consistencyStatus": consistency,
        "veracityStatus": "not_checked",
        "bundle": {"id": payload["bundleReceipt"]["bundle"]["id"], "version": payload["bundleReceipt"]["bundle"]["version"]},
        "fields": field_results,
        "relations": relation_results,
        "ruleResults": rule_results,
        "unresolved": unresolved,
        "provenance": "declared_only",
        "authority": "none",
    }


def apply_consumer_rules(payload: dict[str, Any]) -> dict[str, Any]:
    receipt = payload["bundleReceipt"]
    if receipt["status"] == "conflict" or receipt["conflicts"]:
        conflicts = [
            {"ruleId": item["id"], "target": item["scope"], "status": "conflict", "detail": "O pacote declara origens ou conteúdos divergentes; nenhuma regra foi aplicada."}
            for item in receipt["conflicts"]
        ]
        return {
            "contractVersion": "1.0.0", "status": "conflict", "consistencyStatus": "inconclusive", "veracityStatus": "not_checked",
            "bundle": {"id": receipt["bundle"]["id"], "version": receipt["bundle"]["version"]},
            "fields": [], "relations": [], "ruleResults": conflicts,
            "unresolved": ["Pacote conflituoso; nenhuma precedência foi escolhida."], "provenance": "declared_only", "authority": "none",
        }
    fields = {field["id"]: field for field in payload["fields"]}
    if len(fields) != len(payload["fields"]):
        raise ContractViolation("Field identifiers must be unique")
    for field in payload["fields"]:
        if field["type"] == "quantity":
            allowed_units = field.get("allowedUnits")
            if "unit" not in field or not allowed_units or len(set(allowed_units)) != len(allowed_units):
                raise ContractViolation("Quantity fields require a unit and unique consumer-declared allowedUnits")
        elif "unit" in field or "allowedUnits" in field:
            raise ContractViolation("Units are only valid for quantity fields")
    parsed_rules, conflicts = _parse_rules(receipt, fields)
    if conflicts:
        states = {item["status"] for item in conflicts}
        status = "conflict" if "conflict" in states else "invalid" if "fail" in states else "inconclusive"
        return {
            "contractVersion": "1.0.0", "status": status, "consistencyStatus": "inconclusive", "veracityStatus": "not_checked",
            "bundle": {"id": receipt["bundle"]["id"], "version": receipt["bundle"]["version"]},
            "fields": [], "relations": [], "ruleResults": conflicts,
            "unresolved": ["Regras do consumidor têm conflito ou não podem ser aplicadas sem precedência."], "provenance": "declared_only", "authority": "none",
        }
    return _evaluate(payload, parsed_rules)
