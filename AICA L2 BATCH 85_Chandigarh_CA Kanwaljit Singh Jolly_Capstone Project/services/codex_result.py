"""Structured output contract shared by the Codex executor and API."""
import json
from typing import Any, Dict


RESULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "summary", "checks", "warnings"],
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "FAIL", "INDETERMINATE"]},
        "summary": {"type": "string"},
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "status", "reason", "evidence"],
                "properties": {
                    "name": {"type": "string"},
                    "status": {"type": "string", "enum": ["PASS", "FAIL", "INDETERMINATE"]},
                    "reason": {
                        "type": "string",
                        "description": "A detailed 4-6 sentence rationale explaining the requirement, inspection performed, exact evidence or gap, expected-versus-actual difference, status, and any correction needed."
                    },
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["path", "detail"],
                            "properties": {
                                "path": {"type": "string"},
                                "detail": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}


def parse_result(raw: str) -> Dict[str, Any]:
    try:
        result = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Codex returned invalid JSON") from exc
    if not isinstance(result, dict) or result.get("verdict") not in {"PASS", "FAIL", "INDETERMINATE"}:
        raise ValueError("Codex result is missing a valid verdict")
    if not isinstance(result.get("summary"), str) or not isinstance(result.get("checks"), list):
        raise ValueError("Codex result does not match the Task Checker contract")
    for check in result["checks"]:
        if not isinstance(check, dict) or check.get("status") not in {"PASS", "FAIL", "INDETERMINATE"}:
            raise ValueError("Codex result contains an invalid check")
        if not all(isinstance(check.get(field), expected) for field, expected in (
            ("name", str), ("reason", str), ("evidence", list)
        )):
            raise ValueError("Codex result contains an invalid check")
        for evidence in check["evidence"]:
            if not isinstance(evidence, dict) or not isinstance(evidence.get("path"), str) or not isinstance(evidence.get("detail"), str):
                raise ValueError("Codex result contains invalid evidence")
    result.setdefault("warnings", [])
    if not isinstance(result["warnings"], list) or not all(isinstance(item, str) for item in result["warnings"]):
        raise ValueError("Codex result contains invalid warnings")
    statuses = [check["status"] for check in result["checks"]]
    derived_verdict = (
        "FAIL" if "FAIL" in statuses
        else "INDETERMINATE" if not statuses or "INDETERMINATE" in statuses
        else "PASS"
    )
    if result["verdict"] != derived_verdict:
        result["warnings"].append(
            f"Overall verdict was normalized from {result['verdict']} to {derived_verdict} to match check results."
        )
        result["verdict"] = derived_verdict
    return result
