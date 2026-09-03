"""
The drafting layer.

The language model is used for exactly two things: explaining a movement
in words, and drafting correspondence.  It is never asked to compute,
classify a ledger for the face of the statements, or conclude on a CARO
clause.  Every draft it produces carries the disclaimer and goes to the
auditor for review.

Where no API key is configured the module falls back to a deterministic
template, so the application runs end to end offline -- useful when
demonstrating on a machine with no network, and when an engagement's
confidentiality terms rule out sending anything to a third party.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .formatting import compact, inr
from .pipeline import DISCLAIMER, EngagementResult
from .ratios import RatioResult

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

GEMINI_MODEL = os.environ.get("AUDITLENS_MODEL", "gemini-2.0-flash")
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


@dataclass
class Draft:
    title: str
    body: str
    source: str          # "model" | "template"
    prompt_file: str = ""
    disclaimer: str = DISCLAIMER


def load_prompt(name: str) -> str:
    """Read a versioned system instruction from the prompts directory."""
    path = PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _call_gemini(system_instruction: str, user_content: str) -> str | None:
    """Call the Gemini API. Returns None when unavailable for any reason."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import urllib.error
        import urllib.request

        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {
                # Low temperature: this is professional correspondence, not prose.
                "temperature": 0.2,
                "topP": 0.8,
                "maxOutputTokens": 1024,
            },
        }
        request = urllib.request.Request(
            GEMINI_ENDPOINT.format(model=GEMINI_MODEL) + f"?key={api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        # A drafting failure must never take down the analytical review.
        return None


# --------------------------------------------------------------------------
# Ratio variance explanations
# --------------------------------------------------------------------------

def _ratio_template(r: RatioResult) -> str:
    movement = "increased" if r.variance and r.variance > 0 else "decreased"
    return (
        f"The {r.name.lower()} {movement} from {r.prior_value:.2f} to {r.value:.2f}, "
        f"a movement of {abs(r.variance) * 100:.1f} per cent. The numerator "
        f"({r.numerator_label.lower()}) stood at {compact(r.numerator)} and the "
        f"denominator ({r.denominator_label.lower()}) at {compact(r.denominator)}. "
        "[Management to state the commercial reason for the movement.]"
    )


def explain_ratio_movements(result: EngagementResult) -> list[Draft]:
    """Draft the note explaining every ratio that moved beyond 25 per cent."""
    system = load_prompt("ratio_variance_note.md")
    drafts: list[Draft] = []

    for r in result.ratios.to_explain:
        context = (
            f"Client: {result.inputs.client_name}\n"
            f"Financial year: {result.inputs.financial_year}\n"
            f"Ratio: {r.name}\n"
            f"Numerator: {r.numerator_label} = {inr(r.numerator)}\n"
            f"Denominator: {r.denominator_label} = {inr(r.denominator)}\n"
            f"Current year: {r.formatted()}\n"
            f"Previous year: {r.prior_value}\n"
            f"Movement: {r.variance * 100:+.1f} per cent\n"
            f"Revenue moved from {inr(result.prior_figures.revenue_from_operations) if result.prior_figures else 'n/a'} "
            f"to {inr(result.figures.revenue_from_operations)}.\n"
            f"Profit after tax moved from {inr(result.prior_figures.profit_after_tax) if result.prior_figures else 'n/a'} "
            f"to {inr(result.figures.profit_after_tax)}.\n"
        )
        text = _call_gemini(system, context) if system else None
        drafts.append(
            Draft(
                title=f"Note on the movement in {r.name}",
                body=text or _ratio_template(r),
                source="model" if text else "template",
                prompt_file="ratio_variance_note.md",
            )
        )
    return drafts


# --------------------------------------------------------------------------
# Journal entry enquiry
# --------------------------------------------------------------------------

def draft_je_enquiry(result: EngagementResult, limit: int = 25) -> Draft:
    """Draft the enquiry list sent to management on the selected entries."""
    if not result.je_analysis:
        return Draft("Journal entry enquiry", "No general ledger was supplied.", "template")

    flags = sorted(result.je_analysis.all_flags, key=lambda f: -f.amount)[:limit]
    lines = [
        f"{i}. Entry {f.entry_id} dated "
        f"{f.posting_date.strftime('%d-%m-%Y') if f.posting_date else 'n/a'} "
        f"for {compact(f.amount)}, posted by {f.posted_by}. Selected because: {f.reason.lower()}."
        for i, f in enumerate(flags, start=1)
    ]
    listing = "\n".join(lines)

    system = load_prompt("je_enquiry.md")
    context = (
        f"Client: {result.inputs.client_name}\n"
        f"Financial year: {result.inputs.financial_year}\n"
        f"Performance materiality: {inr(result.materiality.performance)}\n"
        f"Entries selected: {len(result.je_analysis.flagged_entries)} of "
        f"{result.je_analysis.total_entries}\n\n"
        f"Selections:\n{listing}"
    )
    text = _call_gemini(system, context) if system else None

    fallback = (
        f"Dear Sir or Madam,\n\n"
        f"As part of our audit of {result.inputs.client_name} for the financial year "
        f"{result.inputs.financial_year}, and in accordance with SA 240, we have tested "
        f"the journal entries recorded during the year. The following entries have been "
        f"selected for examination. Please provide the supporting documentation and the "
        f"authorisation for each, together with an explanation of the circumstances in "
        f"which the entry was passed.\n\n"
        f"{listing}\n\n"
        f"Selection of an entry does not imply that anything is wrong with it.\n\n"
        f"Yours faithfully,\n[Engagement partner]"
    )
    return Draft(
        title="Enquiry to management on journal entries selected under SA 240",
        body=text or fallback,
        source="model" if text else "template",
        prompt_file="je_enquiry.md",
    )


# --------------------------------------------------------------------------
# Analytical review memorandum
# --------------------------------------------------------------------------

def draft_analytical_memorandum(result: EngagementResult) -> Draft:
    """Draft the one-page analytical review memorandum for the audit file."""
    h = result.headlines()
    f, pf = result.figures, result.prior_figures

    def movement(current: float, prior: float | None) -> str:
        if not prior:
            return "no comparative"
        change = (current - prior) / abs(prior)
        return f"{change * 100:+.1f} per cent"

    facts = (
        f"Client: {result.inputs.client_name}\n"
        f"Financial year: {result.inputs.financial_year}\n"
        f"Revenue: {compact(f.revenue_from_operations)} "
        f"({movement(f.revenue_from_operations, pf.revenue_from_operations if pf else None)})\n"
        f"Profit before tax: {compact(f.profit_before_tax)} "
        f"({movement(f.profit_before_tax, pf.profit_before_tax if pf else None)})\n"
        f"Profit after tax: {compact(f.profit_after_tax)}\n"
        f"Total assets: {compact(f.total_assets)}\n"
        f"Overall materiality: {compact(result.materiality.overall)} "
        f"({result.materiality.percentage:.2%} of {result.materiality.benchmark_label.lower()})\n"
        f"Ratios requiring explanation under Schedule III: "
        f"{', '.join(r.name for r in result.ratios.to_explain) or 'none'}\n"
        f"Journal entries selected under SA 240: {h['je_entries_flagged']} of {h['je_total_entries']}\n"
        f"Benford first-digit test: {h['benford_conclusion']}\n"
        f"Schedule III mapping coverage: {h['mapping_coverage']:.1%}, "
        f"{h['ledgers_for_review']} ledger(s) awaiting the auditor's confirmation\n"
        f"Balance sheet: {h['balance_sheet_reconciliation']}\n"
    )

    system = load_prompt("analytical_memorandum.md")
    text = _call_gemini(system, facts) if system else None

    fallback = (
        f"ANALYTICAL REVIEW MEMORANDUM\n"
        f"{result.inputs.client_name} - financial year {result.inputs.financial_year}\n\n"
        f"{facts}\n"
        f"Matters for the engagement partner's attention:\n"
        + "".join(
            f"  - {r.name} moved {r.variance * 100:+.1f} per cent and requires an "
            f"explanation in the notes under Schedule III.\n"
            for r in result.ratios.to_explain
        )
        + (
            f"  - {h['ledgers_for_review']} ledger(s) could not be mapped to Schedule III "
            f"with full confidence and require the auditor's classification.\n"
            if h["ledgers_for_review"] else ""
        )
        + (
            "  - " + "\n  - ".join(result.sample.warnings) + "\n"
            if result.sample and result.sample.warnings else ""
        )
        + f"\n{DISCLAIMER}"
    )
    return Draft(
        title="Analytical review memorandum",
        body=text or fallback,
        source="model" if text else "template",
        prompt_file="analytical_memorandum.md",
    )


def draft_all(result: EngagementResult) -> dict:
    return {
        "memorandum": draft_analytical_memorandum(result),
        "ratio_notes": explain_ratio_movements(result),
        "je_enquiry": draft_je_enquiry(result),
    }
