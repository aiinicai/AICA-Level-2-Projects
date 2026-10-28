"""
Cents & Sensibility — Claude API layer
1. PDF financial-statement extraction (document intelligence)
2. Auditor's Lens: SA 520 workpaper, SA 570 assessment, audit inquiries
3. MD&A-style narrative commentary

Design principles:
- All AI outputs are DRAFTS for professional review (human-in-the-loop).
- If no API key is configured, rule-based fallbacks keep the app demo-safe offline.
"""

import base64
import json
import re

MODEL = "claude-sonnet-4-6"

from .data_ingestion import LINE_ITEMS, LABEL_BY_KEY, derive
from .ratio_engine import compute_ratios, variance_table
from .forensic_scores import liquidity_stress_flags


def _client(api_key: str):
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def _extract_json(text: str):
    """Robustly pull the first JSON object out of a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response.")
    return json.loads(text[start:end + 1])


# ---------------------------------------------------------------------------
# 1. EXTRACTION (document intelligence)
# ---------------------------------------------------------------------------
_RESIDUAL_RULES = """- Keep the numbers in the SAME unit as printed; report that unit in unit_detected.
- Expenses and costs are POSITIVE numbers. A loss (PBT/PAT) is NEGATIVE.
- If a line item is absent, use 0 and mention it in extraction_notes.
- Map EVERY Balance Sheet line into exactly one field - nothing may be dropped.
  Residual rules: all non-current liabilities without a dedicated field (lease
  liabilities, deferred tax, other financial/other non-current liabilities) go
  into lt_borrowings; current lease liabilities into st_borrowings; other
  current financial liabilities and current tax liabilities into
  other_current_liab; CWIP, right-of-use assets, goodwill, intangibles,
  non-current loans/other financial assets/tax assets into other_nc_assets;
  current investments and other current financial assets into
  other_current_assets; combine cash and other bank balances into cash.
- SELF-CHECK before answering: the sum of your asset fields must equal the
  printed TOTAL ASSETS, and equity + liability fields must equal printed TOTAL
  EQUITY AND LIABILITIES, for BOTH years. If they differ, adjust the 'other'
  buckets until they match, and state what you adjusted in extraction_notes.
- Map P&L intelligently: e.g. purchases/cost of materials + changes in
  inventories together map to material_cost; professional fees and similar
  operating lines without a dedicated field map into other_expenses.
- Do not invent figures. Accuracy over completeness.
- The text may contain placeholders such as [ENTITY_1] or [PERSON_2]. Ignore them;
  they are not financial figures."""


_WORKBOOK_RULES = """
- The text is a multi-sheet Excel workbook: each sheet starts with [Sheet: name]. It may hold
  the Balance Sheet, the Statement of Profit & Loss, separate sheets of notes to accounts,
  and/or a trial balance. Use the NOTES to classify and break up lines (other expenses,
  borrowings, other assets and liabilities) so every line lands in the right field.
- Where face-of-statement totals and notes both appear, the face totals govern and the
  notes must reconcile to them; say in extraction_notes if they do not.
- If the workbook is a TRIAL BALANCE (ledger heads with debit/credit or closing balances),
  build the statements: group ledger heads into the schedule, take income less expenses as
  the profit for the year (add it to reserves), show nothing twice, and state in
  extraction_notes which heads you grouped where. Where only one year is present, set the
  other year to 0.
"""


def _extraction_prompt(source_desc: str, workbook: bool = False) -> str:
    schema_lines = "\n".join(
        f'  "{key}": <number>   // {label} ({stmt})'
        for key, label, stmt, _ in LINE_ITEMS
    )
    return f"""You are a chartered accountant's data-extraction assistant.
{source_desc} contains a company's financial statements (Balance Sheet and
Statement of Profit & Loss), typically with two comparative years.

Extract the figures into EXACTLY this JSON structure and return ONLY the JSON,
no preamble, no markdown fences:

{{{{
  "unit_detected": "<e.g. Rupees in Lakhs / Crores / Millions / absolute - as printed>",
  "current_year_label": "<e.g. FY 2024-25 or 31-03-2025>",
  "previous_year_label": "<...>",
  "CY": {{{{
{schema_lines}
  }}}},
  "PY": {{{{ ...same keys... }}}},
  "extraction_notes": ["<any ambiguity, aggregation you performed, or figures you could not find>"]
}}}}

Rules:
{_RESIDUAL_RULES}{_WORKBOOK_RULES if workbook else ""}"""


def _parse_extraction(raw: str) -> tuple[dict, list[str]]:
    parsed = _extract_json(raw)
    data = {"CY": {}, "PY": {}, "PY2": None}
    for period in ("CY", "PY"):
        block = parsed.get(period, {})
        for key, *_ in LINE_ITEMS:
            try:
                data[period][key] = float(block.get(key, 0) or 0)
            except (TypeError, ValueError):
                data[period][key] = 0.0
    notes = list(parsed.get("extraction_notes", []))
    if parsed.get("unit_detected"):
        notes.insert(0, f"Unit detected: {parsed['unit_detected']}")
    if parsed.get("current_year_label"):
        notes.insert(1, f"Years: {parsed.get('current_year_label')} vs "
                        f"{parsed.get('previous_year_label')}")
    return data, notes


def _text_of(msg) -> str:
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def extract_from_pdf(pdf_bytes: bytes, api_key: str) -> tuple[dict, list[str]]:
    """
    NON-PRIVATE route: the PDF file itself is sent to the Claude API.
    Use extract_from_text() with redacted text when Privacy mode is on.
    """
    client = _client(api_key)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document",
                 "source": {"type": "base64", "media_type": "application/pdf",
                            "data": base64.standard_b64encode(pdf_bytes).decode()}},
                {"type": "text", "text": _extraction_prompt("The attached PDF")},
            ],
        }],
    )
    return _parse_extraction(_text_of(msg))


def extract_from_text(redacted_text: str, api_key: str, redactor=None,
                      workbook: bool = False) -> tuple[dict, list[str]]:
    """
    PRIVATE route: only locally extracted, already-redacted TEXT is sent.
    If a redactor is supplied, the egress guard re-checks the exact outgoing
    prompt and raises RedactionError (nothing sent) if anything survives.
    """
    prompt = (_extraction_prompt("The text below", workbook=workbook)
              + "\n\n----- BEGIN FINANCIAL STATEMENT TEXT -----\n"
              + redacted_text
              + "\n----- END FINANCIAL STATEMENT TEXT -----")
    if redactor is not None:
        redactor.assert_clean(prompt, where="the extraction request")
        redactor.assert_clean(redacted_text, where="the statement text", include_lines=True)
    client = _client(api_key)
    msg = client.messages.create(model=MODEL, max_tokens=8000,
                                 messages=[{"role": "user", "content": prompt}])
    return _parse_extraction(_text_of(msg))


# ---------------------------------------------------------------------------
# Shared context builder for the analysis prompts
# ---------------------------------------------------------------------------
def _analysis_context(data: dict, materiality_pct: float) -> str:
    cy, py = derive(data["CY"]), derive(data["PY"])
    ratios_cy = compute_ratios(data["CY"])
    ratios_py = compute_ratios(data["PY"])
    var_rows = [r for r in variance_table(data, materiality_pct) if r["Flag"]]
    stress = liquidity_stress_flags(data)

    def fmt(d):
        keys = ["revenue", "other_income", "material_cost", "employee_cost",
                "finance_cost", "depreciation", "other_expenses", "pbt", "pat",
                "total_equity", "total_debt", "receivables", "inventory",
                "trade_payables", "cash", "total_assets", "working_capital"]
        return {LABEL_BY_KEY.get(k, k): round(d[k], 2) for k in keys if k in d}

    return json.dumps({
        "current_year_figures": fmt(cy),
        "previous_year_figures": fmt(py),
        "current_year_ratios": {k: (round(v, 2) if v is not None else None)
                                for k, v in ratios_cy.items()},
        "previous_year_ratios": {k: (round(v, 2) if v is not None else None)
                                 for k, v in ratios_py.items()},
        "variances_breaching_threshold": var_rows,
        "materiality_threshold_pct": materiality_pct,
        "stress_indicators": stress,
    }, indent=1)


# ---------------------------------------------------------------------------
# 2. AUDITOR'S LENS (LLM)
# ---------------------------------------------------------------------------
def auditors_lens(data: dict, api_key: str, materiality_pct: float,
                  company: str = "the entity", redactor=None) -> dict:
    """
    Returns {"workpaper": [...], "going_concern": [...], "inquiries": [...]}
    With a redactor: the entity is referred to by a token, the outgoing prompt is
    guard-checked, and real names are restored locally in the response.
    """
    if redactor is not None:
        company = redactor.entity_alias()
    context = _analysis_context(data, materiality_pct)
    prompt = f"""You are an experienced audit manager in an Indian CA firm preparing
analytical-procedure documentation for the audit of {company}.

DATA (already computed; do not recompute, cite these numbers):
{context}

Produce ONLY this JSON (no markdown fences, no preamble):
{{
 "workpaper": [
   {{"area": "<e.g. Revenue>",
     "expectation": "<expectation developed from prior year / relationships, per SA 520>",
     "actual": "<current-year actual with the number>",
     "variance": "<quantified variance>",
     "possible_explanations": "<plausible business explanations>",
     "corroboration_required": "<audit evidence needed to corroborate>"}}
   // 5 to 7 rows covering the flagged variances
 ],
 "going_concern": [
   {{"indicator": "<SA 570 indicator category (financial/operating/other)>",
     "observation": "<what the data shows, with numbers>",
     "assessment": "<present / not present / requires inquiry>"}}
   // 4 to 6 rows
 ],
 "inquiries": [
   "<specific management inquiry question tied to an actual figure>"
   // 8 to 10 questions
 ]
}}

Style: precise, professional Indian audit language; every point must reference
actual numbers from the data; frame everything as draft workpaper content that
the engagement partner will review."""

    if redactor is not None:
        redactor.assert_clean(prompt, where="the Auditor's Lens request")
    client = _client(api_key)
    msg = client.messages.create(model=MODEL, max_tokens=8000,
                                 messages=[{"role": "user", "content": prompt}])
    out = _extract_json(_text_of(msg))
    return redactor.restore_obj(out) if redactor is not None else out


def auditors_lens_fallback(data: dict, materiality_pct: float) -> dict:
    """Rule-based offline fallback so the demo never depends on connectivity."""
    flagged = [r for r in variance_table(data, materiality_pct) if r["Flag"]]
    wp = []
    for r in flagged[:7]:
        wp.append({
            "area": r["Item"],
            "expectation": f"Approximately {r['Prior Year (Expectation basis)']} "
                           f"(prior-year basis, stable-relationship expectation per SA 520)",
            "actual": str(r["Current Year (Actual)"]),
            "variance": f"{r['Change %']}% vs expectation "
                        f"(threshold {materiality_pct}%)",
            "possible_explanations": "To be obtained from management.",
            "corroboration_required": "Corroborate management explanation with "
                                      "supporting documentation and substantive evidence.",
        })
    gc = [{"indicator": "Financial", "observation": s, "assessment": "Requires inquiry"}
          for s in liquidity_stress_flags(data)]
    inq = [f"Please explain the movement in {r['Item']} "
           f"({r['Prior Year (Expectation basis)']} → {r['Current Year (Actual)']}, "
           f"{r['Change %']}%)." for r in flagged[:8]]
    return {"workpaper": wp, "going_concern": gc, "inquiries": inq or
            ["No variances breached the threshold — consider lowering the threshold."]}


# ---------------------------------------------------------------------------
# 3. NARRATIVE COMMENTARY (LLM)
# ---------------------------------------------------------------------------
def narrative(data: dict, api_key: str, scores: dict, materiality_pct: float,
              company: str = "the entity", redactor=None) -> str:
    if redactor is not None:
        company = redactor.entity_alias()
    context = _analysis_context(data, materiality_pct)
    prompt = f"""You are drafting an MD&A-style financial commentary on {company}
for a chartered accountant's report. Composite health assessment already computed:
{json.dumps(scores)}

DATA:
{context}

Write 450–600 words of flowing professional prose (no bullet lists, no headings
except the three natural paragraphs' opening bolded phrases like
**Operating performance.** / **Financial position and liquidity.** /
**Observations and red flags.**). Cite actual numbers throughout. In the final
paragraph, candidly state red-flag observations and note that this commentary is
AI-assisted draft analysis requiring professional review. Indian financial
terminology (lakhs/crores as given, ₹)."""

    if redactor is not None:
        redactor.assert_clean(prompt, where="the narrative request")
    client = _client(api_key)
    msg = client.messages.create(model=MODEL, max_tokens=1500,
                                 messages=[{"role": "user", "content": prompt}])
    out = _text_of(msg)
    return redactor.restore(out) if redactor is not None else out
