"""
NR Tax Advisor - AI Advisory Engine
Generates structured NR Tax advisory using Claude API + Treaty PDFs
"""

import anthropic
import os
try:
    from treaty_reader import get_treaty_text_for_country, search_treaty_for_topic
except ImportError:
    try:
        from treaties_reader import get_treaty_text_for_country, search_treaty_for_topic
    except ImportError:
        get_treaty_text_for_country = None
        search_treaty_for_topic = None

# ITA 2025 domestic rates reference
DOMESTIC_RATES = {
    "dividend": {"rate": 20, "section": "Section 393 read with Section 115A ITA 2025"},
    "interest": {"rate": 20, "section": "Section 393 ITA 2025"},
    "royalty": {"rate": 10, "section": "Section 393 read with Section 115A ITA 2025"},
    "fts": {"rate": 10, "section": "Section 393 ITA 2025"},
    "capital gains": {"rate": "As applicable", "section": "Section 393 ITA 2025"},
    "salary": {"rate": "Slab rates", "section": "Section 393 ITA 2025"},
}

SYSTEM_PROMPT = """You are DTAA Advisor, an expert AI assistant for Indian Chartered Accountants.
You operate exclusively under the Income Tax Act, 2025 (ITA 2025) and Income Tax Rules, 2026.

CRITICAL — DETERMINE PAYMENT DIRECTION FIRST:
Before any analysis, identify:
- WHO is paying? (Indian entity or Foreign entity)
- WHO is receiving? (Indian entity or Foreign entity)
- Is this OUTBOUND (India paying to NR) → Form 145/146 applies
- Is this INBOUND (NR paying to India) → Form 145/146 does NOT apply; FTC under Section 91 applies
State the direction explicitly in section (b) Facts before proceeding.
NEVER assume outbound if facts indicate inbound.

CRITICAL ITA 2025 RULES — NEVER VIOLATE:

1. FORM 145 replaces Form 15CA (w.e.f. 1 April 2026) — Section 397(3)(d) ITA 2025
2. FORM 146 replaces Form 15CB (w.e.f. 1 April 2026) — Section 397(3)(d) ITA 2025
3. FORM 41 replaces Form 10F — Rule 75, Section 159(8) ITA 2025 — MANDATORY always
4. Section 393 replaces Section 195 for TDS on NR payments
5. Rule 220(3) replaces Rule 37BB — exempt list expanded to 33 categories
6. NEVER say Form 15CA, Form 15CB, Form 10F, Section 195, or Rule 37BB

RISK RATING — ALWAYS start every response with one of:
🟢 LOW RISK — Treaty position well-settled
🟡 MEDIUM RISK — Interpretational uncertainty, recommend CA certification
🔴 HIGH RISK — GAAR/PPT/LOB challenge likely, recommend Advance Ruling under Section 245Q

ADVISORY STRUCTURE for full queries:
(a) Risk Rating
(b) Facts of Transaction
(c) Applicable DTAA and Article
(d) Rate Analysis — DTAA vs Domestic Section 393
(e) Form 145 Part (A/B/C/D) and Form 146 requirement
(f) Documents Required (including Form 41 — mandatory)
(g) GAAR/PPT/MLI Risk Assessment
(h) CA Recommendation — Practical + Conservative position

SPECIAL FLAGS:
- USA: LOB clause Article 21 — NOT MLI signatory
- Mauritius: Post-2016 protocol — CG on shares taxable from Apr 2017
- Singapore: Make-available test Article 12(4)(b) for FTS
- Netherlands: HIGH GAAR scrutiny — treaty shopping
- UAE: No domestic tax — beneficial ownership critical

CASE LAW to cite:
- Engineering Analysis SC 2021 — software royalty
- GE India Technology — Section 393 obligation
- Azadi Bachao Andolan — treaty shopping
- Nestle SA SC 2023 — TRC not conclusive
- CBDT Circulars 333, 728, 7/2007

END every advisory with:
Disclaimer: This advisory is for general guidance only. Verify with actual treaty text and CBDT notification before filing.
Source: India-[Country] DTAA | ITA 2025 Section [X] | Rule 220 IT Rules 2026"""


def get_claude_client():
    """Initialize Anthropic client"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured in Streamlit Secrets. Please contact administrator.")
    return anthropic.Anthropic(api_key=api_key)


def generate_advisory(country, income_type, transaction_details, include_treaty_text=True):
    """Generate full DTAA advisory for a transaction"""
    client = get_claude_client()

    # Get relevant treaty text
    treaty_context = ""
    if include_treaty_text:
        treaty_text, source = search_treaty_for_topic(
            country,
            f"{income_type} royalty FTS dividend interest Article",
            max_chars=4000
        )
        if treaty_text:
            treaty_context = f"""
ACTUAL TREATY TEXT FROM OFFICIAL CBDT PDF ({source}):
{treaty_text}

Use the above actual treaty text to give precise article numbers and exact rates.
"""

    # Get domestic rate
    income_lower = income_type.lower()
    domestic_info = DOMESTIC_RATES.get(income_lower, {"rate": "20%", "section": "Section 393 ITA 2025"})

    user_message = f"""
Country of Payee: {country}
Nature of Income: {income_type}
Domestic Section 393 Rate: {domestic_info['rate']}% under {domestic_info['section']}
Transaction Details: {transaction_details}

{treaty_context}

Please provide a complete DTAA advisory following the 8-point structure.
Start with the risk rating. Use ITA 2025 terminology throughout.
Always mention Form 41, Form 145 Part, and Form 146 requirements.
"""
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


def generate_notice_reply(notice_type, country, facts, treaty_article=""):
    """Generate formal IT department notice reply"""
    client = get_claude_client()

    # Get treaty context
    treaty_context = ""
    treaty_text, source = search_treaty_for_topic(
        country,
        f"{notice_type} permanent establishment PE royalty FTS Article 7 Article 12",
        max_chars=3000
    )
    if treaty_text:
        treaty_context = f"""
ACTUAL TREATY TEXT ({source}):
{treaty_text}
"""

    user_message = f"""
Draft a formal reply to an Income Tax Department notice.

Notice Type: {notice_type}
Country of Foreign Entity: {country}
Treaty Article in Dispute: {treaty_article}
Facts: {facts}

{treaty_context}

Draft a complete formal notice reply with:
1. Formal header (To: Assessing Officer)
2. Facts of the transaction
3. Treaty article analysis with exact article numbers from treaty text
4. Supporting case law (cite GE India, Engineering Analysis, Azadi Bachao, CBDT Circulars as relevant)
5. OECD commentary where applicable
6. Prayer (5 specific prayers)
7. Enclosures list

Use ITA 2025 — Section 393 (not 195), Form 145 (not 15CA), Form 41 (not Form 10F).
Be formal and submission-ready.
"""
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


def generate_rate_comparison(country):
    """Generate rate comparison table for a country"""
    client = get_claude_client()

    treaty_text, source = get_treaty_text_for_country(country, max_chars=5000)
    treaty_context = f"TREATY TEXT ({source}):\n{treaty_text}" if treaty_text else ""

    user_message = f"""
Generate a rate comparison table for India-{country} DTAA.

{treaty_context}

Provide a structured table comparing:
- Dividend: DTAA rate vs Domestic 20% (Section 393)
- Interest: DTAA rate vs Domestic 20%
- Royalty: DTAA rate vs Domestic 10%
- FTS: DTAA rate vs Domestic 10%
- Capital Gains: treatment

For each: state the treaty article number, beneficial rate, and any special conditions.
Flag where domestic rate is lower than DTAA rate (use ⚠️).
Also state: MLI status, GAAR risk level, Form 41 requirement.
"""
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


def classify_form_145(income_type, amount_lakhs, taxable, dtaa_claimed):
    """Determine correct Form 145 Part"""
    client = get_claude_client()

    user_message = f"""
Determine the correct Form 145 Part for this remittance under ITA 2025:

Nature of Payment: {income_type}
Amount: Rs. {amount_lakhs} lakhs
Taxable in India: {taxable}
DTAA Benefit Claimed: {dtaa_claimed}

Under Rule 220 of Income Tax Rules 2026 (replacing Rule 37BB):
- Part A: Taxable, aggregate ≤ Rs. 5 lakh
- Part B: Taxable, > Rs. 5 lakh, AO certificate u/s 395(1)/395(2)
- Part C: Taxable, > Rs. 5 lakh, Form 146 (CA Certificate) obtained
- Part D: Not taxable (except Rule 220(3) exempt list — 33 categories)

State:
1. Correct Form 145 Part
2. Whether Form 146 (CA Certificate) is required
3. Whether Form 41 is mandatory (always yes for DTAA claims)
4. Key compliance steps
5. Penalty for non-compliance (Section 271-I ITA 2025)
"""
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text
