"""
ai_commentary.py
-----------------
Drafts flux commentary in the register of a Big 4 senior manager reviewing
a close binder: precise about the number, explicit about what needs to be
substantiated, and clear that this is a DRAFT for the controller to accept,
edit, or reject — never a final answer.

Two layers, deliberately kept separate:

1. `draft_commentary()` — deterministic, rule-based. Decides the wording
   from the numbers, the statement type (Income Statement / Balance
   Sheet), the category (Revenue, Assets, etc.), and the severity tier.
   This ALWAYS runs, needs no API key, and is what ships in the export if
   the AI-polish step is left off or fails.

2. `enhance_commentary()` / `enhance_dataframe()` — OPTIONAL. Sends the
   rule-based draft through an LLM (OpenAI) to smooth the prose into a
   more natural senior-manager voice. It is instructed to preserve every
   number, every ask, and the "draft, pending controller sign-off" framing
   exactly — it may only improve how the sentence reads, never what it
   claims or concludes. On any failure it falls back to the rule-based
   text automatically.

Neither layer ever marks an item as resolved. Resolution is a controller
action, recorded by review_store.py — see routes.py.
"""

from __future__ import annotations

CLOSING_NOTE = (
    "This is a system-drafted note for the preparer to substantiate; "
    "final classification and disposition rest with the Controller upon review."
)

SEVERITY_OPENERS = {
    "high": "This is a high-severity variance warranting immediate preparer explanation and controller attention before the close is finalized.",
    "elevated": "This is an elevated variance; preparer explanation should be obtained and reviewed prior to sign-off.",
    "standard": "This variance exceeds the materiality threshold agreed for this cycle and should be substantiated in the ordinary course of close review.",
}

# Category-aware professional-skepticism framing, by statement type,
# category, and direction of movement.
IS_FRAMING = {
    "Revenue": {
        "up": "This is a favorable movement. Recommend corroborating against underlying volume and pricing data, and confirming revenue cut-off at period end.",
        "down": "This is an unfavorable movement. Recommend assessing for revenue recognition timing differences, contract losses, or customer attrition, and confirming no unrecorded revenue exists.",
    },
    "Cost of Sales": {
        "up": "This is an unfavorable movement. Recommend validating against volume growth and reviewing the gross margin trend for consistency.",
        "down": "This is a favorable movement. Recommend confirming the completeness of cost accruals — a lower cost of sales should not reflect an understatement.",
    },
    "Operating Expenses": {
        "up": "This is an unfavorable movement. Recommend obtaining vendor-level detail and confirming the increase does not reflect double-booking or expense acceleration.",
        "down": "This is a favorable movement. Recommend confirming no expense has been inadvertently omitted, deferred, or reclassified below the line.",
    },
    "Other Income/Expense": {
        "up": "Recommend confirming the classification and non-recurring nature of this item, particularly where FX or one-off items are involved.",
        "down": "Recommend confirming the classification and non-recurring nature of this item, particularly where FX or one-off items are involved.",
    },
}

BS_FRAMING = {
    "Assets": {
        "up": "Recommend confirming existence, valuation, and recoverability of the increased balance (e.g. an aging analysis for receivables, physical verification for inventory).",
        "down": "Recommend confirming completeness — that no asset has been derecognized, written off, or impaired without appropriate authorization.",
    },
    "Liabilities": {
        "up": "Recommend confirming completeness and classification (current vs. non-current), and that the increase reflects a bona fide obligation as at period end.",
        "down": "Recommend confirming the liability was appropriately settled or extinguished, and not merely reclassified or omitted in error.",
    },
    "Equity": {
        "up": "Recommend confirming this ties to Board-approved capital transactions, dividend resolutions, or the comprehensive income movement for the period.",
        "down": "Recommend confirming this ties to Board-approved capital transactions, dividend resolutions, or the comprehensive income movement for the period.",
    },
}

GENERIC_FRAMING = {
    "up": "Recommend obtaining a documented explanation for this movement from the process owner.",
    "down": "Recommend obtaining a documented explanation for this movement from the process owner.",
}


def draft_commentary(row: dict, statement_type: str, comparison_phrase: str, threshold_pct: float) -> str:
    """Deterministic, rule-based Big-4-senior-manager-style commentary."""
    if not row.get("is_material"):
        return "Within materiality threshold — no commentary required for this cycle."

    line = row["line_item"]
    category = row.get("category", "Uncategorized")
    variance = row["variance_usd"]
    pct = row["variance_pct"]
    severity = row.get("severity", "standard")

    direction = "increased" if variance > 0 else "decreased"
    dir_key = "up" if variance > 0 else "down"
    magnitude = abs(variance)

    if row["prior_amount"] == 0:
        fact = f"{line} is a new balance of ${row['current_amount']:,.0f} with no prior-period comparative."
    else:
        fact = f"{line} {direction} by ${magnitude:,.0f} ({pct:,.1f}%) {comparison_phrase}, exceeding the {threshold_pct:.0f}% materiality threshold agreed for this cycle."

    if statement_type == "income_statement":
        framing = IS_FRAMING.get(category, GENERIC_FRAMING)[dir_key]
    elif statement_type == "balance_sheet":
        framing = BS_FRAMING.get(category, GENERIC_FRAMING)[dir_key]
    else:
        framing = GENERIC_FRAMING[dir_key]

    opener = SEVERITY_OPENERS.get(severity, SEVERITY_OPENERS["standard"])

    return f"{fact} {opener} {framing} {CLOSING_NOTE}"


# ---------------------------------------------------------------------
# Optional LLM polish layer — never changes facts, only wording.
# ---------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a Big 4 audit/advisory senior manager reviewing a client's flux/variance "
    "commentary before it goes into the close binder. Rewrite the given draft into "
    "one or two crisp, professional sentences in that register — precise, "
    "unembellished, and appropriately skeptical. "
    "Rules: keep every number exactly as given; keep every recommendation/ask in the "
    "draft; keep the final sentence that says this is a draft pending controller "
    "review; do not invent a root cause that was not stated; do not soften the "
    "request for substantiation. Return only the rewritten text, nothing else."
)


def is_available() -> bool:
    try:
        import openai  # noqa: F401
        return True
    except ImportError:
        return False


def enhance_commentary(draft: str, api_key: str, model: str = "gpt-4o-mini") -> tuple[str, str | None]:
    if not api_key:
        return draft, "No API key provided."
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": draft},
            ],
            temperature=0.2,
            max_tokens=180,
        )
        text = response.choices[0].message.content.strip()
        if not text:
            return draft, "Empty response from model."
        return text, None
    except Exception as exc:  # noqa: BLE001
        return draft, f"AI enhancement skipped ({exc.__class__.__name__})."


def enhance_dataframe(flux_df, api_key: str, model: str = "gpt-4o-mini"):
    df = flux_df.copy()
    n_ok, n_failed = 0, 0
    for idx, row in df[df["is_material"]].iterrows():
        text, error = enhance_commentary(row["commentary"], api_key, model=model)
        df.at[idx, "commentary"] = text
        if error:
            n_failed += 1
        else:
            n_ok += 1
    return df, n_ok, n_failed
