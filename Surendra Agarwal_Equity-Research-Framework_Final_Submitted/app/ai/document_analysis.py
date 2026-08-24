"""Document/management commentary analysis — Module 5.

Converts DocumentEvidence (already quarantined, page-tracked) into
AIInterpretation objects via the LLM. Every AIInterpretation produced
here is stamped level=LEVEL_2_AI_INTERPRETATION (the model default) and
carries evidence_ids pointing back to the source DocumentEvidence, so
the report layer can never confuse this output with a Level 1 verified
fact.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from app.core.enums import ConfidenceLevel
from app.core.exceptions import LLMProviderError
from app.core.models import AIInterpretation, DocumentEvidence
from app.ai.json_utils import parse_json_response
from app.ai.llm_client import LLMClient
from app.ai.prompts import build_document_analysis_prompt

logger = logging.getLogger(__name__)


def analyze_evidence(
    evidence: DocumentEvidence,
    llm_client: LLMClient,
    *,
    focus: str = "general business and management commentary",
    model_name: str | None = None,
) -> AIInterpretation | None:
    """Analyze one piece of document evidence, returning a single
    AIInterpretation, or None if the model found nothing relevant to
    the given focus area in this excerpt (an expected, common outcome —
    most pages won't be relevant to every focus area, not an error).

    Raises:
        LLMProviderError: if the LLM call fails or returns unparseable JSON.
    """
    system, user = build_document_analysis_prompt(evidence, focus=focus)
    response = llm_client.complete(system=system, user=user)
    data = parse_json_response(response.text)

    claim = data.get("claim")
    if claim is None:
        return None

    confidence_str = str(data.get("confidence", "low")).lower()
    try:
        confidence = ConfidenceLevel(confidence_str)
    except ValueError:
        logger.warning("Unrecognized confidence value %r from LLM; defaulting to LOW.", confidence_str)
        confidence = ConfidenceLevel.LOW

    return AIInterpretation(
        claim=str(claim),
        based_on_evidence_ids=[evidence.evidence_id],
        confidence=confidence,
        model_name=model_name or response.model,
    )


def analyze_evidence_batch(
    evidence_list: list[DocumentEvidence],
    llm_client: LLMClient,
    *,
    focus: str = "general business and management commentary",
    delay_seconds: float = 0.0,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[AIInterpretation]:
    """Analyze a batch of evidence, skipping (with a logged warning, not
    a crash) any individual page whose LLM call fails — one bad page
    should not abort analysis of the rest of a 194-page document.

    Args:
        delay_seconds: pause between each page's API call, proactively
            reducing how often a real account's rate limit gets hit —
            see app/ai/rate_limiting.py. 0 (default) disables pacing.
        progress_callback: if supplied, called as
            progress_callback(completed_count, total_count) after EVERY
            page (success, skip, or failure alike), so a UI progress bar
            always advances — never coupled to Streamlit here, callers
            wire whatever UI update they need through this callback.
    """
    total = len(evidence_list)
    results: list[AIInterpretation] = []
    for i, evidence in enumerate(evidence_list):
        try:
            interpretation = analyze_evidence(evidence, llm_client, focus=focus)
        except LLMProviderError as exc:
            logger.warning(
                "Skipping page %s of %s due to LLM error: %s",
                evidence.page_number, evidence.source_document, exc,
            )
            interpretation = None
        if interpretation is not None:
            results.append(interpretation)
        if progress_callback is not None:
            progress_callback(i + 1, total)
        if delay_seconds > 0 and i < total - 1:
            time.sleep(delay_seconds)
    return results


def compute_management_commentary_summary(
    interpretations: list[AIInterpretation],
) -> dict:
    """Module 5's 'Management Commentary Score' — a simple, transparent
    aggregate over already-produced AIInterpretations, NOT a new
    LLM call. Deliberately minimal (confidence distribution + count) —
    this module does not invent a numeric "score" formula the spec
    didn't define, since presenting an ungrounded composite number
    as though it were meaningful would itself violate Principle 3
    (no fabricated data). The scoring layer (Module 9 / Milestone 7)
    is where component scores with defined weights belong.
    """
    total = len(interpretations)
    by_confidence = {level.value: 0 for level in ConfidenceLevel}
    for interp in interpretations:
        by_confidence[interp.confidence.value] += 1
    return {
        "total_claims_extracted": total,
        "confidence_distribution": by_confidence,
        "note": (
            "This is a factual summary of AI-extracted claims, not a "
            "numeric management-quality score. All claims are Level 2 "
            "(AI Interpretation) and require human review before use."
        ),
    }
