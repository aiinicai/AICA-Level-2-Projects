"""Promoter pledge disclosure extraction - AI-assisted, Module 5/8 adjacent.

Extracts promoter share pledge/encumbrance status from uploaded SEBI
Regulation 31 (or similar) disclosure filings. This is genuinely
distinct from app/analysis/risk.py's general risk extraction: pledge
filings are legally precise documents with a specific, narrow question
("what % of THIS company's shares are pledged, as of when") rather than
open-ended risk commentary, so this gets its own extraction path with a
prompt built specifically to avoid the most common real misread - a
pledge on an upstream holding entity's shares being conflated with a
pledge on the target company's own shares (see prompts.py's
build_pledge_disclosure_prompt docstring for a real example of exactly
this distinction).

IMPORTANT - never a silent default: this module NEVER produces a "no
pledge" result from the absence of a document. If no pledge-disclosure
document is supplied/analyzed, promoter_pledge_pct simply stays
whatever it already was (typically None/unavailable). A user who
independently knows there is no pledge can assert that explicitly via
the manual-entry checkbox in the UI - clearly labeled as user-asserted,
never conflated with a document-derived finding.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from app.core.exceptions import LLMProviderError
from app.core.models import DocumentEvidence
from app.ai.json_utils import parse_json_response
from app.ai.llm_client import LLMClient
from app.ai.prompts import build_pledge_disclosure_prompt

logger = logging.getLogger(__name__)


def extract_pledge_disclosure_from_evidence(
    evidence: DocumentEvidence, llm_client: LLMClient,
) -> dict | None:
    """Extract pledge disclosure info from one page. Returns None if the
    page contains no pledge/encumbrance disclosure content (the common
    case for most pages of a multi-page filing - not an error).

    Returns a dict: {"pledge_pct": float | None, "status": str | None,
    "as_of_date": str | None, "summary": str, "evidence_id": str,
    "page_number": int} on success.

    Raises:
        LLMProviderError: if the LLM call fails or returns unparseable JSON.
    """
    system, user = build_pledge_disclosure_prompt(evidence)
    response = llm_client.complete(system=system, user=user)
    data = parse_json_response(response.text)

    if not data.get("disclosure_found"):
        return None

    return {
        "pledge_pct": data.get("pledge_pct_of_target_company_shares"),
        "status": data.get("status"),
        "as_of_date": data.get("as_of_date"),
        "summary": data.get("summary", ""),
        "evidence_id": evidence.evidence_id,
        "page_number": evidence.page_number,
    }


def extract_pledge_disclosure_batch(
    evidence_list: list[DocumentEvidence], llm_client: LLMClient,
    *,
    delay_seconds: float = 0.0,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Extract pledge disclosures from a batch of pages, skipping (with a
    logged warning) any page whose LLM call fails.

    Args:
        delay_seconds: pause between each page's API call, proactively
            reducing how often a real account's rate limit gets hit —
            see app/ai/rate_limiting.py. 0 (default) disables pacing.
        progress_callback: if supplied, called as
            progress_callback(completed_count, total_count) after every
            page (success, skip, or failure alike).
    """
    total = len(evidence_list)
    results: list[dict] = []
    for i, evidence in enumerate(evidence_list):
        try:
            result = extract_pledge_disclosure_from_evidence(evidence, llm_client)
        except LLMProviderError as exc:
            logger.warning(
                "Skipping pledge extraction for page %s of %s due to LLM error: %s",
                evidence.page_number, evidence.source_document, exc,
            )
            result = None
        if result is not None:
            results.append(result)
        if progress_callback is not None:
            progress_callback(i + 1, total)
        if delay_seconds > 0 and i < total - 1:
            time.sleep(delay_seconds)
    return results


def summarize_pledge_status(disclosures: list[dict]) -> dict:
    """Convenience: reduce a batch of per-page pledge disclosures into a
    single latest-known status. Prefers the disclosure with the most
    recent as_of_date if dates are parseable; otherwise takes the last
    one found in document order. Returns a dict with 'latest_pledge_pct',
    'as_of_date', 'summary', 'source_evidence_ids' - or an empty-ish dict
    with latest_pledge_pct=None if no disclosures were found at all.

    This function NEVER returns 0 when `disclosures` is empty - an empty
    list means "nothing was found/analyzed," not "confirmed zero."
    """
    if not disclosures:
        return {"latest_pledge_pct": None, "as_of_date": None, "summary": None, "source_evidence_ids": []}

    dated = [d for d in disclosures if d.get("as_of_date")]
    if dated:
        dated.sort(key=lambda d: d["as_of_date"])
        chosen = dated[-1]
    else:
        chosen = disclosures[-1]

    return {
        "latest_pledge_pct": chosen.get("pledge_pct"),
        "as_of_date": chosen.get("as_of_date"),
        "summary": chosen.get("summary"),
        "source_evidence_ids": [d["evidence_id"] for d in disclosures],
    }
