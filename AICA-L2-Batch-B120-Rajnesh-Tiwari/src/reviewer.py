"""Structured LLM review for fictional audit findings."""

from __future__ import annotations

import json
import os
from typing import Any


ELEMENTS = ("condition", "criteria", "cause", "impact", "recommendation")
ALLOWED_ELEMENT_STATUSES = ("present", "weak", "missing", "requires_verification")
ALLOWED_OVERALL_STATUSES = (
    "review_ready",
    "needs_minor_revision",
    "needs_major_revision",
    "requires_auditor_verification",
)

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overall_status": {
            "type": "string",
            "enum": list(ALLOWED_OVERALL_STATUSES),
        },
        "element_analysis": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                element: {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": list(ALLOWED_ELEMENT_STATUSES),
                        },
                        "explanation": {"type": "string"},
                    },
                    "required": ["status", "explanation"],
                }
                for element in ELEMENTS
            },
            "required": list(ELEMENTS),
        },
        "unsupported_claims": {
            "type": "array",
            "items": {"type": "string"},
        },
        "questions_for_auditor": {
            "type": "array",
            "items": {"type": "string"},
        },
        "suggested_rewrite": {"type": "string"},
        "human_review_note": {"type": "string"},
    },
    "required": [
        "overall_status",
        "element_analysis",
        "unsupported_claims",
        "questions_for_auditor",
        "suggested_rewrite",
        "human_review_note",
    ],
}

SYSTEM_INSTRUCTIONS = """
You are AuditSense, an internal-audit documentation assistant.

Review only the fictional information supplied by the user. Do not invent
facts, dates, amounts, causes, impacts, policies, controls, or evidence.
If an element is not supported by the supplied text, mark it missing,
weak, or requires_verification and ask a question instead of filling the gap.

Assess Condition, Criteria, Cause, Impact, and Recommendation separately.
Flag broad or unsupported claims. A suggested rewrite must preserve unknowns
and must not add facts. Do not make fraud, legal, regulatory, compliance, or
final-audit conclusions.

The auditor remains responsible for evidence assessment, materiality,
risk assessment, professional judgment, and final approval.
Return only the requested structured response.
""".strip()

IDEAL_ISSUE_SYSTEM_INSTRUCTIONS = """
You are a seasoned Internal Audit Director and expert report writer.
Transform only the supplied fictional raw field notes into a formal,
executive-ready internal audit observation using the 5 Cs: Criteria,
Condition, Cause, Consequence/Impact, and Corrective Action/Recommendation.

Use a professional, objective, concise tone. Use passive voice for errors and
active voice for recommendations. Do not invent data, metrics, policies,
dates, causes, impacts, owners, or evidence. If critical information is not
in the notes, write exactly:
[Information missing in raw notes - Auditor to specify]

Risk rating may be a cautious AI inference from the stated impact, but it is
not an audit conclusion and must be verified by the auditor. Process owner
must be extracted from the notes or use the required missing-information
placeholder. Return only the requested structured response.
""".strip()

IDEAL_ISSUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "observation_title": {"type": "string"},
        "risk_rating": {"type": "string", "enum": ["High", "Medium", "Low"]},
        "risk_rating_basis": {"type": "string"},
        "process_owner": {"type": "string"},
        "observation_summary": {"type": "string"},
        "criteria": {"type": "string"},
        "condition": {"type": "string"},
        "cause": {"type": "string"},
        "consequence": {"type": "string"},
        "corrective_action": {"type": "string"},
        "auditor_verification_note": {"type": "string"},
    },
    "required": [
        "observation_title",
        "risk_rating",
        "risk_rating_basis",
        "process_owner",
        "observation_summary",
        "criteria",
        "condition",
        "cause",
        "consequence",
        "corrective_action",
        "auditor_verification_note",
    ],
}


def _validate_review(review: dict[str, Any]) -> dict[str, Any]:
    """Apply a lightweight defensive check before displaying model output."""
    if review.get("overall_status") not in ALLOWED_OVERALL_STATUSES:
        raise ValueError("The model returned an invalid overall status.")
    analysis = review.get("element_analysis")
    if not isinstance(analysis, dict) or set(analysis) != set(ELEMENTS):
        raise ValueError("The model returned an incomplete element analysis.")
    for element in ELEMENTS:
        item = analysis[element]
        if not isinstance(item, dict):
            raise ValueError(f"Invalid analysis for {element}.")
        if item.get("status") not in ALLOWED_ELEMENT_STATUSES:
            raise ValueError(f"Invalid status for {element}.")
        if not isinstance(item.get("explanation"), str):
            raise ValueError(f"Invalid explanation for {element}.")
    for key in ("unsupported_claims", "questions_for_auditor"):
        if not isinstance(review.get(key), list) or not all(
            isinstance(item, str) for item in review[key]
        ):
            raise ValueError(f"Invalid list returned for {key}.")
    for key in ("suggested_rewrite", "human_review_note"):
        if not isinstance(review.get(key), str):
            raise ValueError(f"Invalid text returned for {key}.")
    return review


def review_finding(payload: dict[str, str]) -> dict[str, Any]:
    """Review a finding with the configured OpenAI Responses API model."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Add it to your local environment "
            "before running an AI review."
        )

    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError(
            "The OpenAI package is not installed. Install requirements.txt first."
        ) from error

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    client = OpenAI(api_key=api_key)
    user_input = json.dumps(payload, ensure_ascii=False, indent=2)

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {
                "role": "user",
                "content": (
                    "Review this fictional audit finding and return the required "
                    "structured result.\n\n" + user_input
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "audit_finding_review",
                "strict": True,
                "schema": REVIEW_SCHEMA,
            }
        },
    )

    output_text = getattr(response, "output_text", "")
    if not output_text:
        raise RuntimeError("The model returned no structured review.")
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise RuntimeError("The model returned invalid JSON.") from error
    return _validate_review(parsed)


def _validate_ideal_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Validate the structured ideal-observation response before display/export."""
    required = (
        "observation_title",
        "risk_rating",
        "risk_rating_basis",
        "process_owner",
        "observation_summary",
        "criteria",
        "condition",
        "cause",
        "consequence",
        "corrective_action",
        "auditor_verification_note",
    )
    if set(issue) != set(required):
        raise ValueError("The model returned an incomplete ideal audit issue.")
    if issue["risk_rating"] not in {"High", "Medium", "Low"}:
        raise ValueError("The model returned an invalid risk rating.")
    if not all(isinstance(issue[key], str) and issue[key].strip() for key in required):
        raise ValueError("The model returned incomplete ideal audit issue text.")
    if len(issue["observation_title"].split()) > 10:
        raise ValueError("The model returned a title longer than 10 words.")
    return issue


def generate_ideal_issue(payload: dict[str, str]) -> dict[str, Any]:
    """Create a 5-C executive-ready issue from fictional raw notes."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Add it to your local environment "
            "before generating an ideal audit issue."
        )

    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError(
            "The OpenAI package is not installed. Install requirements.txt first."
        ) from error

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    client = OpenAI(api_key=api_key)
    user_input = json.dumps(payload, ensure_ascii=False, indent=2)
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": IDEAL_ISSUE_SYSTEM_INSTRUCTIONS},
            {
                "role": "user",
                "content": (
                    "Transform these fictional raw audit notes into the required "
                    "5-C issue. Preserve unknowns explicitly.\n\n" + user_input
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "ideal_audit_issue",
                "strict": True,
                "schema": IDEAL_ISSUE_SCHEMA,
            }
        },
    )
    output_text = getattr(response, "output_text", "")
    if not output_text:
        raise RuntimeError("The model returned no structured ideal audit issue.")
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise RuntimeError("The model returned invalid ideal issue JSON.") from error
    return _validate_ideal_issue(parsed)
