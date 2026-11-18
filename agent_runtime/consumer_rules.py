"""Inspect consumer-declared rule bundles without trusting them as authority."""

from __future__ import annotations

import hashlib
from typing import Any

from .contracts import validate_result


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _find_conflicts(kind: str, entries: list[dict[str, Any]], content_key: str) -> list[dict[str, str]]:
    seen: dict[tuple[str, str, str], tuple[str, str]] = {}
    conflicts: dict[tuple[str, str, str], dict[str, str]] = {}
    for entry in entries:
        identity = (entry["id"], entry["version"], entry["scope"])
        signature = (entry["origin"], _digest(entry[content_key]))
        previous = seen.get(identity)
        if previous is not None and previous != signature:
            conflicts[identity] = {
                "kind": kind,
                "id": entry["id"],
                "version": entry["version"],
                "scope": entry["scope"],
                "reason": "The same declared identity has different origin or content; no precedence was chosen.",
            }
        else:
            seen[identity] = signature
    return list(conflicts.values())


def inspect_consumer_rule_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    bundle = dict(payload["bundle"])
    documents = [
        {
            "id": item["id"],
            "version": item["version"],
            "origin": item["origin"],
            "scope": item["scope"],
            "contentDigest": _digest(item["content"]),
        }
        for item in payload["documents"]
    ]
    rules = [
        {
            "id": item["id"],
            "version": item["version"],
            "origin": item["origin"],
            "scope": item["scope"],
            "definition": item["definition"],
            "definitionDigest": _digest(item["definition"]),
        }
        for item in payload["rules"]
    ]
    conflicts = _find_conflicts("document", payload["documents"], "content")
    conflicts.extend(_find_conflicts("rule", payload["rules"], "definition"))
    result = {
        "contractVersion": payload["contractVersion"],
        "status": "conflict" if conflicts else "received_untrusted",
        "bundle": bundle,
        "documents": documents,
        "rules": rules,
        "conflicts": conflicts,
        "provenance": "declared_only",
        "authority": "none",
    }
    validate_result("validation.inspectConsumerRuleBundle", result)
    return result
