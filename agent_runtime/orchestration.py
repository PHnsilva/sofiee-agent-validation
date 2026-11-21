"""Bounded, request-scoped coordination for the validation domain tools."""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .contracts import CONTRACT, ERROR_SCHEMA, ContractViolation, error_result, validate, validate_result
from .validation import execute


ROOT = Path(__file__).resolve().parents[1]
TASK_SCHEMA = json.loads((ROOT / "contracts" / "v1" / "task.schema.json").read_text(encoding="utf-8"))
TASK_RESULT_SCHEMA = json.loads(
    (ROOT / "contracts" / "v1" / "task-result.schema.json").read_text(encoding="utf-8")
)


TASK_TOOLS = {
    "validation.verifyClaim",
    "validation.auditSearchResults",
    "validation.inspectConsumerRuleBundle",
    "validation.applyConsumerRules",
}
_DEFAULT_LIMITS = {
    "maxSteps": 8,
    "timeoutMs": 60_000,
    "maxAttempts": 1,
    "maxConcurrency": 1,
    "maxDelegationDepth": 0,
}
_EXECUTE = Callable[[str, dict[str, Any]], dict[str, Any]]


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _definition(task: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    return {
        "contractVersion": task["contractVersion"],
        "objective": task["objective"],
        "stages": [
            {
                "id": stage["id"],
                "tool": stage["tool"],
                "input": stage["input"],
                "dependsOn": stage.get("dependsOn", []),
            }
            for stage in task["stages"]
        ],
        "limits": limits,
    }


def _stage_digest(stage: dict[str, Any]) -> str:
    return _canonical_digest(
        {
            "id": stage["id"],
            "tool": stage["tool"],
            "input": stage["input"],
            "dependsOn": stage.get("dependsOn", []),
        }
    )


def _validate_graph(stages: list[dict[str, Any]], limits: dict[str, int]) -> None:
    if len(stages) > limits["maxSteps"]:
        raise ContractViolation("Task exceeds maxSteps")
    ids: set[str] = set()
    for stage in stages:
        if stage["id"] in ids:
            raise ContractViolation("Stage IDs must be unique")
        if stage["tool"] not in TASK_TOOLS:
            raise ContractViolation("Task tool is not available")
        dependencies = stage.get("dependsOn", [])
        if len(dependencies) != len(set(dependencies)):
            raise ContractViolation("Stage dependencies must be unique")
        if any(dependency not in ids for dependency in dependencies):
            raise ContractViolation("Dependencies must reference earlier declared stages")
        ids.add(stage["id"])


def _references(value: Any) -> set[str]:
    if isinstance(value, list):
        return set().union(*(_references(item) for item in value)) if value else set()
    if isinstance(value, dict):
        if "$resultFrom" in value:
            if set(value) != {"$resultFrom"} or not isinstance(value["$resultFrom"], str):
                raise ContractViolation("Result references must contain only a stage ID")
            return {value["$resultFrom"]}
        return set().union(*(_references(item) for item in value.values())) if value else set()
    return set()


def _resolve(value: Any, results: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, list):
        return [_resolve(item, results) for item in value]
    if isinstance(value, dict):
        if "$resultFrom" in value:
            if set(value) != {"$resultFrom"}:
                raise ContractViolation("Result references must contain only a stage ID")
            stage_id = value["$resultFrom"]
            if stage_id not in results:
                raise ContractViolation("Referenced stage has no completed result")
            return copy.deepcopy(results[stage_id])
        return {key: _resolve(item, results) for key, item in value.items()}
    return value


def _missing_dependencies(tool: str, payload: dict[str, Any], result: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if tool == "validation.verifyClaim" and result.get("verdict") == "inconclusive":
        if any("conector" in item.lower() and "configurado" in item.lower() for item in result.get("unresolved", [])):
            missing.append(f"fonte independente autorizada para dataType={payload['dataType']}")
    if tool == "validation.auditSearchResults" and any(
        not audit.get("reopened", False) for audit in result.get("audits", [])
    ):
        missing.append("abridor independente e autorizado para as referências auditadas")
    return missing


def _domain_verdict(results: list[dict[str, Any]]) -> str:
    for result in reversed(results):
        verdict = result.get("verdict")
        if verdict in {"confirmed", "refuted", "inconclusive", "not_checkable"}:
            return verdict
        if result.get("veracityStatus") == "not_checked":
            return "inconclusive"
        audits = result.get("audits")
        if isinstance(audits, list) and any(item.get("decision") == "inconclusive" for item in audits):
            return "inconclusive"
    return "inconclusive"


def _checkpoint_stages(stages: list[dict[str, Any]], definitions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": stage["id"],
            "tool": stage["tool"],
            "stageDigest": _stage_digest(definitions[stage["id"]]),
            "result": stage["result"],
        }
        for stage in stages
        if stage["status"] == "completed" and "result" in stage
    ]


def run_task(
    payload: Any,
    *,
    execute_tool: _EXECUTE | None = None,
    cancel_event: threading.Event | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Execute only validated, side-effect-free runtime tools, in declared order."""
    try:
        encoded_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(encoded_payload) > 80_000:
            return error_result("limit_exceeded", "Task exceeds 80000 bytes.")
        validate(TASK_SCHEMA, payload)
        limits = dict(_DEFAULT_LIMITS)
        limits.update(payload.get("limits", {}))
        stages_def = payload["stages"]
        _validate_graph(stages_def, limits)
        for stage in stages_def:
            references = _references(stage["input"])
            if not references.issubset(set(stage.get("dependsOn", []))):
                raise ContractViolation("Every result reference must be declared as a dependency")
        definition = _definition(payload, limits)
        objective_digest = _canonical_digest(definition)
        task_id = payload.get("resume", {}).get("taskId", str(uuid.uuid4()))
        try:
            task_id = str(uuid.UUID(task_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ContractViolation("Checkpoint taskId must be a UUID") from exc
        by_id = {stage["id"]: stage for stage in stages_def}
        resumed: dict[str, dict[str, Any]] = {}
        if payload.get("resume"):
            checkpoint = payload["resume"]
            if checkpoint["objectiveDigest"] != objective_digest:
                raise ContractViolation("Checkpoint belongs to a different task definition")
            for item in checkpoint["completedStages"]:
                if item["id"] in resumed:
                    raise ContractViolation("Checkpoint stage IDs must be unique")
                stage = by_id.get(item["id"])
                if stage is None or item["tool"] != stage["tool"] or item["stageDigest"] != _stage_digest(stage):
                    raise ContractViolation("Checkpoint stage does not match the current task")
                validate_result(item["tool"], item["result"])
                resumed[item["id"]] = item
    except (ContractViolation, KeyError, TypeError, ValueError, RecursionError) as exc:
        return error_result("invalid_request", str(exc) or "Task contract is invalid")

    run = execute_tool or execute
    start = clock()
    stage_results: dict[str, dict[str, Any]] = {}
    stage_states: dict[str, str] = {}
    output_stages: list[dict[str, Any]] = []
    missing: list[str] = []
    stop_status: str | None = None

    for stage in stages_def:
        if cancel_event is not None and cancel_event.is_set():
            stop_status = "cancelled"
            break
        if clock() - start >= limits["timeoutMs"] / 1000:
            stop_status = "timed_out"
            break
        stage_id = stage["id"]
        tool = stage["tool"]
        if stage_id in resumed:
            item = resumed[stage_id]
            stage_results[stage_id] = item["result"]
            stage_states[stage_id] = "completed"
            output_stages.append(
                {"id": stage_id, "tool": tool, "status": "completed", "mode": "checkpoint_untrusted", "attempts": 0, "result": item["result"]}
            )
            continue
        blocked_by = [dependency for dependency in stage.get("dependsOn", []) if stage_states.get(dependency) != "completed"]
        if blocked_by:
            stage_states[stage_id] = "blocked"
            output_stages.append(
                {"id": stage_id, "tool": tool, "status": "blocked", "mode": "deterministic", "attempts": 0, "blockedBy": blocked_by}
            )
            continue
        try:
            stage_input = _resolve(stage["input"], stage_results)
            if not isinstance(stage_input, dict):
                raise ContractViolation("Resolved tool input must be an object")
            attempts = 0
            stage_record: dict[str, Any] = {
                "id": stage_id,
                "tool": tool,
                "status": "failed",
                "mode": "simulated" if execute_tool else "deterministic",
                "attempts": 0,
            }
            while attempts < limits["maxAttempts"]:
                if cancel_event is not None and cancel_event.is_set():
                    stop_status = "cancelled"
                    stage_record["status"] = "cancelled"
                    break
                if clock() - start >= limits["timeoutMs"] / 1000:
                    stop_status = "timed_out"
                    stage_record["status"] = "timed_out"
                    break
                attempts += 1
                stage_record["attempts"] = attempts
                try:
                    result = run(tool, stage_input)
                except KeyboardInterrupt:
                    stop_status = "cancelled"
                    stage_record["status"] = "cancelled"
                    break
                if not isinstance(result, dict):
                    result = error_result("internal_error", "Tool returned a non-object result")
                if "code" in result:
                    try:
                        validate(ERROR_SCHEMA, result)
                    except ContractViolation:
                        result = error_result("internal_error", "Tool error failed its output contract")
                    stage_record["error"] = result
                    if result.get("retryable") is True and attempts < limits["maxAttempts"]:
                        continue
                    stage_record["status"] = "failed"
                    break
                try:
                    validate_result(tool, result)
                except ContractViolation:
                    stage_record["error"] = error_result("internal_error", "Tool result failed its output contract")
                    stage_record["status"] = "failed"
                    break
                if cancel_event is not None and cancel_event.is_set():
                    stop_status = "cancelled"
                    stage_record["status"] = "cancelled"
                    break
                if clock() - start >= limits["timeoutMs"] / 1000:
                    stop_status = "timed_out"
                    stage_record["status"] = "timed_out"
                    break
                stage_record["result"] = result
                stage_record["status"] = "completed"
                stage_results[stage_id] = result
                missing.extend(_missing_dependencies(tool, stage_input, result))
                break
            stage_states[stage_id] = stage_record["status"]
            output_stages.append(stage_record)
            if stop_status:
                break
        except (ContractViolation, KeyError, TypeError, ValueError, RecursionError) as exc:
            stage_states[stage_id] = "failed"
            output_stages.append(
                {
                    "id": stage_id,
                    "tool": tool,
                    "status": "failed",
                    "mode": "deterministic",
                    "attempts": 0,
                    "error": error_result("invalid_request", str(exc) or "Stage input is invalid"),
                }
            )

    if stop_status:
        for stage in stages_def[len(output_stages):]:
            output_stages.append(
                {"id": stage["id"], "tool": stage["tool"], "status": stop_status, "mode": "deterministic", "attempts": 0}
            )
    states = [stage["status"] for stage in output_stages]
    failed = any(state in {"failed", "blocked"} for state in states)
    if stop_status:
        status = stop_status
    elif failed and any(state == "completed" for state in states):
        status = "partial"
    elif failed:
        status = "failed"
    else:
        status = "completed"
    result_values = [stage["result"] for stage in output_stages if "result" in stage]
    checkpoint = {
        "contractVersion": CONTRACT["contractVersion"],
        "taskId": task_id,
        "objectiveDigest": objective_digest,
        "completedStages": _checkpoint_stages(output_stages, by_id),
    }
    response = {
        "contractVersion": CONTRACT["contractVersion"],
        "taskId": task_id,
        "objective": payload["objective"],
        "status": status,
        "verdict": _domain_verdict(result_values),
        "stages": output_stages,
        "missingDependencies": sorted(set(missing)),
        "limits": limits,
        "delegation": {"depthUsed": 0, "subagents": 0, "reason": "Ferramentas determinísticas executadas localmente; não há processo isolado."},
        "checkpoint": checkpoint,
    }
    validate(TASK_RESULT_SCHEMA, response)
    return response
