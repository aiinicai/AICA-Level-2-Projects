"""
ai_assistant.py
Wraps the AI provider used to turn the raw tax computation into a
plain-language explanation for the employee, and to answer their follow-up
questions — grounded strictly in numbers the app itself already computed.

PROVIDER-AGNOSTIC BY DESIGN: this module auto-detects whichever API key is
configured in Streamlit secrets and routes calls to that provider. Anyone
deploying this app can supply EITHER an ANTHROPIC_API_KEY OR a
GEMINI_API_KEY — not both required, and no code change needed either way.
If ANTHROPIC_API_KEY is present, Claude is used. Otherwise, if
GEMINI_API_KEY is present, Gemini is used. If neither is present, every AI
panel shows a clear fallback message — the core calculator keeps working
regardless.
"""

import os
import streamlit as st

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from google import genai
except ImportError:
    genai = None


def _get_secret(name: str):
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return os.environ.get(name)


def _detect_provider():
    """Returns ('anthropic', client) or ('gemini', client) for whichever key
    is configured, or (None, None) if neither is available or the matching
    SDK isn't installed."""
    anthropic_key = _get_secret("ANTHROPIC_API_KEY")
    if anthropic_key and anthropic is not None:
        return "anthropic", anthropic.Anthropic(api_key=anthropic_key)

    gemini_key = _get_secret("GEMINI_API_KEY")
    if gemini_key and genai is not None:
        return "gemini", genai.Client(api_key=gemini_key)

    return None, None


def _call_model(system_prompt: str, user_content: str, max_tokens: int = 400) -> str:
    """Routes a single-turn prompt to whichever provider is configured.
    Raises on failure so callers can produce their own fallback message."""
    provider, client = _detect_provider()

    if provider is None:
        raise RuntimeError(
            "No AI provider configured — set either ANTHROPIC_API_KEY or "
            "GEMINI_API_KEY in Streamlit secrets."
        )

    if provider == "anthropic":
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))

    # provider == "gemini"
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=user_content,
        config={"system_instruction": system_prompt, "max_output_tokens": max_tokens},
    )
    return response.text


def build_context(inp, old_result, new_result) -> str:
    """Builds a compact, factual context block from the computed results,
    so the model explains real numbers instead of guessing."""
    return f"""
Employee: {inp.name or "Employee"} | Age band: {inp.age_band}
Gross annual salary: Rs.{old_result.gross_salary:,.0f}
Other income: Rs.{inp.other_income:,.0f}

OLD REGIME:
  HRA exemption (Sec 11 r/w Sec 19 & Sch. II): Rs.{old_result.exemptions:,.0f}
  Standard deduction (Sec 19): Rs.{old_result.standard_deduction:,.0f}
  Chapter VI-A equivalent deductions (Sec 123/124/126) + home loan interest (Sec 22(2)): Rs.{old_result.chapter_via_deductions:,.0f}
  Taxable income: Rs.{old_result.taxable_income:,.0f}
  Total tax (incl. cess): Rs.{old_result.total_tax:,.0f}
  Monthly TDS (Sec 392): Rs.{old_result.monthly_tds:,.0f}

NEW REGIME (Sec 202, default):
  Standard deduction (Sec 19): Rs.{new_result.standard_deduction:,.0f}
  Taxable income: Rs.{new_result.taxable_income:,.0f}
  Rebate applied (Sec 156): Rs.{new_result.rebate:,.0f}
  Total tax (incl. cess): Rs.{new_result.total_tax:,.0f}
  Monthly TDS (Sec 392): Rs.{new_result.monthly_tds:,.0f}
""".strip()


def explain_tds(inp, old_result, new_result, question: str = None) -> str:
    """Produces a plain-language explanation or answer, grounded in the
    already-computed figures. Falls back to a clear message if no AI
    provider is configured, so the app never breaks during a live demo."""
    provider, _ = _detect_provider()
    if provider is None:
        return (
            "⚠️ AI explanation is not available right now — no AI provider is "
            "configured. Add either ANTHROPIC_API_KEY or GEMINI_API_KEY under "
            "Streamlit secrets to enable this panel. (The rest of the "
            "calculator works fully without it.)"
        )

    context = build_context(inp, old_result, new_result)
    user_question = question or (
        "Explain in simple, friendly language why my monthly TDS is what it is, "
        "which regime is better for me and by how much, and one concrete step "
        "I could take to reduce my tax. Keep it under 150 words. Cite section "
        "numbers from the Income Tax Act, 2025 where relevant (e.g. Section 123, "
        "Section 22(2), Section 202, Section 392) rather than the old 1961 numbers."
    )
    system_prompt = (
        "You are a helpful assistant embedded in a salary TDS calculator "
        "used by employees who are not tax experts. Always base your answer "
        "strictly on the figures given in the context — never invent numbers. "
        "Be warm, clear, and concise."
    )

    try:
        return _call_model(system_prompt, f"Context:\n{context}\n\nQuestion: {user_question}")
    except Exception as e:
        return f"⚠️ Could not reach the AI service right now ({e}). Try again in a moment."


# ---------------------------------------------------------------------------
# Tax FAQ (Educational) — a deliberately separate, more restricted function.
#
# Unlike explain_tds() above, this is NOT grounded in any employee's actual
# computed figures. It answers general tax-concept questions (capital gains,
# ITR filing steps, deductions, etc.) but is explicitly instructed to refuse
# computing anyone's personal tax liability, since that requires structured
# inputs (cost basis, holding period, indexation, etc.) this panel doesn't
# collect. Keeping this as a separate function — with its own system prompt —
# means the two panels can never accidentally share behavior.
# ---------------------------------------------------------------------------

FAQ_SYSTEM_PROMPT = (
    "You are a general tax-education assistant embedded in a company salary "
    "tool, answering questions from employees who are not tax experts. Your "
    "role is strictly educational — you explain how Indian income tax "
    "concepts and provisions work in general terms.\n\n"
    "Hard rules:\n"
    "1. NEVER compute or state a specific rupee tax liability for the user's "
    "personal situation, even if they give you numbers (e.g. 'I sold shares "
    "for Rs.X, what do I owe?'). Politely decline and explain that an accurate "
    "computation needs full details (cost basis, holding period, indexation, "
    "other income, exemptions claimed) that should be reviewed by a qualified "
    "Chartered Accountant.\n"
    "2. You MAY explain concepts generally — e.g. how LTCG/STCG on equities "
    "work, what ITR form suits what situation, filing deadlines, general "
    "provisions — using correct section numbers from the Income Tax Act, 2025 "
    "(e.g. Section 196 for short-term equity gains [erstwhile Section 111A], "
    "Section 198 for long-term equity gains [erstwhile Section 112A], "
    "Section 197 for other long-term capital gains [erstwhile Section 112]).\n"
    "3. Always close with a brief reminder to consult a CA for advice specific "
    "to their situation.\n"
    "4. Keep answers under 180 words, plain language, no jargon without "
    "explanation."
)


GENERIC_SOURCE_NOTE = (
    "\n\n📌 *For the exact provision text, refer to the Income Tax Act, 2025 on "
    "incometax.gov.in, or consult a Chartered Accountant.*"
)


def answer_tax_faq(question: str) -> str:
    """Answers a general, educational tax question. Deliberately does not
    accept or use any personal computed figures — see module docstring.

    Every answer ends with a generic, non-fabricated source note appended
    here in code (not left to the model) — this app has no live web-search
    tool wired in, so the model has no real citation it pulled the answer
    from. Appending a specific-looking source would risk fabricating a
    citation; a generic pointer to the real Act and to a CA is truthful
    and still useful."""
    provider, _ = _detect_provider()
    if provider is None:
        return (
            "⚠️ AI explanation is not available right now — no AI provider is "
            "configured. Add either ANTHROPIC_API_KEY or GEMINI_API_KEY under "
            "Streamlit secrets to enable this panel."
        )
    if not question or not question.strip():
        return "Please type a question to get started."

    try:
        answer = _call_model(FAQ_SYSTEM_PROMPT, question.strip())
        return answer + GENERIC_SOURCE_NOTE
    except Exception as e:
        return f"⚠️ Could not reach the AI service right now ({e}). Try again in a moment."
