# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Technical accounting memo.

The AI is a WRITER here, never a calculator:

* ``build_memo_facts``   turns the lease's validated inputs and SAVED calculation results into
  plain, fully-formatted fact sentences (every amount already written out).
* ``generate_memo``      sends ONLY those facts to the AI and asks for six prose sections. Raw
  contract text is never involved, and the AI is told to copy numbers, not compute them.
* ``check_memo``         scans the finished memo and flags any amount that is not in the facts,
  any of the six sections that is missing, and a missing lease-liability / ROU-asset figure.
* ``build_template_memo`` writes the same six sections straight from the facts with NO AI, so a
  correct memo is always available (offline, or when the AI is busy).

Pure Python: no UI framework and no database.
"""
import re
from datetime import date

from core.extraction import ExtractionError, call_gemini
from core.formatting import (
    DEFAULT_CURRENCY,
    DEFAULT_NUMBER_FORMAT,
    currency_decimals,
    currency_label,
    format_approx,
    format_money,
)
from core.results import format_tests

MEMO_SECTIONS = [
    "Background",
    "Relevant guidance",
    "Classification conclusion",
    "Initial measurement",
    "Journal entries summary",
    "Overall conclusion",
]
MIN_MEMO_CHARS = 200

_FRAMEWORK_TEXT = {"IND_AS_116": "Ind AS 116", "ASC_842": "ASC 842", "BOTH": "Ind AS 116 and ASC 842"}
_METHOD_TEXT = {
    "gross_accum": "gross cost with accumulated amortization",
    "net_direct": "a single straight-line lease cost with the ROU asset reduced directly",
}
# Static reference text (from the Excel memo). The AI may only rephrase these; it is told not to add references.
_GUIDANCE = [
    "Ind AS 116 Leases: a single lessee model, with recognition exemptions for short-term and low-value leases.",
    "ASC 842 Leases: classification as a finance lease or an operating lease using five criteria; an operating lease "
    "carries a single straight-line lease cost (ASC 842-20-25-6).",
    "The framework, elections, options and the discount rate must be verified by the reviewer.",
]
_DISCLAIMER = (
    "This is a draft for professional review and not a final accounting opinion; a reviewer must validate the contract, "
    "guidance, discount rate, options, variable payments and all journal entries before use."
)


# --------------------------------------------------------------------------- #
# facts
# --------------------------------------------------------------------------- #
def _as_date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _line_total(lines: list, account: str, side: str) -> float:
    return sum(line[side] for line in lines if line["account"] == account)


def _signed(lines: list, account: str) -> float:
    """Debit minus credit for one account in an entry."""
    return _line_total(lines, account, "debit") - _line_total(lines, account, "credit")


def build_memo_facts(
    lease_case_data: dict,
    calculation_results: dict,
    currency: str = None,
    number_format: str = DEFAULT_NUMBER_FORMAT,
) -> dict:
    """Fact sentences for each memo section, built ONLY from validated inputs and saved results.

    ``lease_case_data``: lease_ref, status, lessor, lessee, asset_type, currency, commencement_date, end_date,
    term_months, base_rent, escalation, prepaid_rent, prepaid_rent_months, deposit, idc, incentives,
    restoration_cost, ibr, reporting_framework, classification_override, ... (missing values are skipped).
    ``calculation_results``: the output of ``core.workflow.get_stored_results``.

    Returns {"lease_ref", "sections": {title: [sentence, ...]}, "text": all facts as text, "key_amounts": {...}}.
    """
    case = lease_case_data
    calc = calculation_results["calculation"]
    classification = calculation_results["classification"]
    journal = calculation_results["journal"]
    code = currency or case.get("currency") or DEFAULT_CURRENCY

    def money(value):
        return format_money(value, code, number_format)

    def pct(value, decimals=2):
        return "{:.{d}%}".format(float(value), d=decimals)

    ref = case.get("lease_ref") or calculation_results["case"].get("lease_ref") or "(unreferenced)"
    status = case.get("status") or calculation_results["case"].get("status")

    # ---- Background ----
    background = ["Lease reference: {}.".format(ref)]
    if case.get("lessee") or case.get("lessor"):
        background.append(
            "{} (the lessee) leases {} from {} (the lessor).".format(
                case.get("lessee") or "The lessee",
                (case.get("asset_type") or "the asset").lower(),
                case.get("lessor") or "the lessor",
            )
        )
    start, end = _as_date(case.get("commencement_date")), _as_date(case.get("end_date"))
    if case.get("term_months") and start:
        term = "The lease term is {} months from {}".format(case["term_months"], start.strftime("%d-%b-%Y"))
        background.append(term + (" to {}.".format(end.strftime("%d-%b-%Y")) if end else "."))
    if case.get("base_rent") is not None:
        rent = "The monthly rent in the first lease year is {}".format(money(case["base_rent"]))
        if case.get("escalation"):
            rent += ", increasing by {} each year".format(pct(case["escalation"]))
        background.append(rent + ".")
    if case.get("prepaid_rent"):
        background.append(
            "{} of rent was paid in advance, covering the first {} month(s).".format(
                money(case["prepaid_rent"]), case.get("prepaid_rent_months") or 0
            )
        )
    for key, label in (
        ("deposit", "The refundable security deposit is {}."),
        ("idc", "Initial direct costs are {}."),
        ("restoration_cost", "The restoration obligation is {}."),
        ("incentives", "Lease incentives received are {}."),
    ):
        if case.get(key):
            background.append(label.format(money(case[key])))
    if case.get("ibr") is not None:
        background.append(
            "The discount rate (incremental borrowing rate) is {} per year, applied monthly as {}.".format(
                pct(case["ibr"]), "{:.4%}".format(calc["monthly_rate"])
            )
        )
    framework = _FRAMEWORK_TEXT.get(case.get("reporting_framework") or "BOTH", "Ind AS 116 and ASC 842")
    background.append("Reporting framework: {}. Amounts are in {}.".format(framework, currency_label(code)))

    # ---- Classification ----
    asc842 = classification["asc842_classification"]
    classification_facts = ["ASC 842 classification: {}.".format(asc842)]
    if classification.get("is_override"):
        computed = "FINANCE LEASE" if any(t["met"] == "Y" for t in classification["tests"]) else "OPERATING LEASE"
        classification_facts.append(
            "This classification was set manually (override); the five tests alone would have given {}.".format(computed)
        )
    for row in format_tests(classification["tests"]):
        classification_facts.append(
            "{}: computed {} against a threshold of {}; criterion {}met.".format(
                row["Test"], row["Computed"], row["Threshold"], "" if row["Met"] == "Yes" else "not "
            )
        )
    classification_facts.append("Ind AS 116: {}. {}".format(classification["ind_as116_exemption"], classification["ind_as116_rationale"]))
    classification_facts.append(
        "ROU asset method under ASC 842: {}.".format(_METHOD_TEXT.get(classification["rou_method"], classification["rou_method"]))
    )

    # ---- Initial measurement ----
    liability, rou = calc["lease_liability_initial"], calc["rou_asset_gross"]
    measurement = [
        "The lease liability is {} (approximately {}), being the present value of the net contractual lease payments "
        "discounted at {} per month.".format(money(liability), format_approx(liability, number_format), "{:.4%}".format(calc["monthly_rate"])),
        "The security deposit has a present value of {}, a discount of {} from its nominal amount.".format(
            money(calc["security_deposit_pv"]), money(calc["security_deposit_discount"])
        ),
        "The right-of-use asset is {}: the lease liability plus prepaid rent, initial direct costs and restoration "
        "obligation, less incentives, plus the security-deposit discount.".format(money(rou)),
        "Total contractual rent is {}; total undiscounted lease payments are {}.".format(
            money(calc["total_contractual_rent"]), money(calc["total_undiscounted_payments"])
        ),
    ]
    if classification["rou_method"] == "net_direct":
        measurement.append(
            "Under ASC 842 as an operating lease, the single straight-line lease cost is {} per month.".format(
                money(calc["single_lease_cost_per_month"])
            )
        )

    # ---- Journal entries ----
    legs = {letter: journal["day1"][letter] for letter in "ABC"}
    totals = {letter: sum(line["debit"] for line in lines) for letter, lines in legs.items()}
    balanced = all(abs(sum(l["debit"] for l in lines) - sum(l["credit"] for l in lines)) < 0.01 for lines in legs.values())
    journal_facts = [
        "Day 1, Leg A (lease liability and ROU asset): {}; Leg B (security deposit paid): {}; Leg C (deposit "
        "remeasured to present value): {}.".format(money(totals["A"]), money(totals["B"]), money(totals["C"])),
        "Each Day 1 leg {} (debits equal credits).".format("balances" if balanced else "DOES NOT balance"),
    ]
    periods = sorted(journal["periodic"]["IND_AS_116"])
    if periods:
        period = 3 if 3 in periods else periods[0]
        ind = journal["periodic"]["IND_AS_116"][period]
        asc = journal["periodic"]["ASC_842"][period]
        journal_facts.append(
            "Period {} entry under Ind AS 116: interest expense {}, principal reduction of the lease liability {}, "
            "ROU amortization {}, and security-deposit accretion {}.".format(
                period,
                money(_line_total(ind, "Interest Expense", "debit")),
                money(_signed(ind, "Lease Liability")),
                money(_line_total(ind, "Amortization Expense \u2013 ROU Asset", "debit")),
                money(_line_total(ind, "Security Deposit Receivable", "debit")),
            )
        )
        if any(line["account"] == "Lease Expense" for line in asc):
            journal_facts.append(
                "Period {} entry under ASC 842 (operating): single lease cost {} with a direct ROU asset reduction of {}.".format(
                    period,
                    money(_line_total(asc, "Lease Expense", "debit")),
                    money(-_signed(asc, "Right-of-Use Asset (direct reduction)")),
                )
            )
        else:
            journal_facts.append("Period {} entry under ASC 842 (finance): the same as under Ind AS 116.".format(period))

    # ---- Overall conclusion ----
    conclusion = [
        "On the validated inputs the lease is {} under Ind AS 116 and {} under ASC 842 (ROU method: {}).".format(
            classification["ind_as116_exemption"], asc842, classification["rou_method"]
        ),
        "Approval status: {}.".format(status),
        _DISCLAIMER,
    ]

    sections = {
        "Background": background,
        "Relevant guidance": list(_GUIDANCE),
        "Classification conclusion": classification_facts,
        "Initial measurement": measurement,
        "Journal entries summary": journal_facts,
        "Overall conclusion": conclusion,
    }
    text = "\n\n".join(
        "{}\n{}".format(title.upper(), "\n".join("- " + fact for fact in facts)) for title, facts in sections.items()
    )
    return {
        "lease_ref": ref,
        "sections": sections,
        "text": text,
        # compared at the precision the memo displays (a yen amount is shown without decimals)
        "key_amounts": {
            "lease liability": round(float(liability), currency_decimals(code)),
            "right-of-use asset": round(float(rou), currency_decimals(code)),
        },
    }


# --------------------------------------------------------------------------- #
# writing the memo
# --------------------------------------------------------------------------- #
def build_memo_prompt(facts: dict) -> str:
    """The instruction sent to the AI: rules + the facts. Contains NO contract text."""
    return (
        "You are a technical accounting writer preparing a DRAFT memo for a reviewer.\n\n"
        "RULES (very important):\n"
        "- Use ONLY the facts listed below. Do not add facts, figures, dates, names or accounting references that are "
        "not written in the facts.\n"
        "- Do NOT calculate, convert, round or restate any number. Copy every amount, percentage and date exactly as "
        "written in the facts, including the currency symbol and the digit grouping.\n"
        "- If something is not in the facts, do not mention it.\n"
        "- Write clear, professional prose: 2 to 5 sentences per section. Plain text only: no tables and no markdown "
        "symbols such as ** or #.\n\n"
        "STRUCTURE: write exactly these six sections in this order, each starting with its title on its own line:\n"
        "{titles}\n\n"
        "FACTS:\n{facts}\n"
    ).format(titles="\n".join("{}. {}".format(i, t) for i, t in enumerate(MEMO_SECTIONS, start=1)), facts=facts["text"])


def clean_memo(reply) -> str:
    """Tidy the AI's reply: remove code fences and markdown emphasis."""
    text = (reply or "").strip()
    fenced = re.match(r"^```(?:\w+)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    text = text.replace("**", "")
    text = re.sub(r"(?m)^#{1,6}\s*", "", text)
    return text.strip()


def generate_memo(
    lease_case_data: dict,
    calculation_results: dict,
    llm=None,
    currency: str = None,
    number_format: str = DEFAULT_NUMBER_FORMAT,
) -> str:
    """Ask the AI to write the memo from validated, already-computed figures ONLY.

    ``llm`` is any function ``prompt -> reply text`` (default: Gemini in plain-text mode); tests pass a fake.
    Raises ExtractionError if the AI fails or returns an empty / very short memo.
    """
    facts = build_memo_facts(lease_case_data, calculation_results, currency, number_format)
    prompt = build_memo_prompt(facts)
    reply = (llm or (lambda p: call_gemini(p, json_mode=False)))(prompt)
    memo = clean_memo(reply)
    if len(memo) < MIN_MEMO_CHARS:
        raise ExtractionError("The AI returned an empty or very short memo. Please try again, or use the template.")
    return memo


def build_template_memo(facts: dict) -> str:
    """The same six sections written directly from the facts - no AI, always consistent with the results."""
    parts = ["TECHNICAL ACCOUNTING MEMO - DRAFT", "Lease {}".format(facts["lease_ref"]), ""]
    for number, title in enumerate(MEMO_SECTIONS, start=1):
        parts.append("{}. {}".format(number, title))
        parts.extend("- " + fact for fact in facts["sections"][title])
        parts.append("")
    return "\n".join(parts).strip()


# --------------------------------------------------------------------------- #
# checking the finished memo
# --------------------------------------------------------------------------- #
_NUMBER = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(\s*(?:%|(?:lakh|crore|million|billion|thousand)\b))?", re.IGNORECASE)


def _numbers(text: str) -> list:
    """[(token as written, numeric value, unit or None)] for every number in ``text``."""
    found = []
    for match in _NUMBER.finditer(text):
        token = match.group(1).rstrip(",")
        found.append((token, float(token.replace(",", "")), (match.group(2) or "").strip() or None))
    return found


def check_memo(memo_text: str, facts: dict) -> dict:
    """Compare the memo against the facts it was allowed to use.

    ``unverified``: amounts / percentages / big numbers in the memo that are NOT in the facts (possible
    hallucinations). Small plain whole numbers (below 100, no unit) are not judged.
    ``missing_amounts``: the lease liability or ROU asset was not quoted exactly.
    ``missing_sections``: one of the six sections has no heading.
    """
    allowed = {round(value, 4) for _, value, _ in _numbers(facts["text"])}
    unverified = []
    for token, value, unit in _numbers(memo_text):
        if round(value, 4) in allowed:
            continue
        if ("," in token or "." in token or value >= 100 or unit) and (token + (" " + unit if unit else "")) not in unverified:
            unverified.append(token + (" " + unit if unit else ""))

    memo_values = [value for _, value, _ in _numbers(memo_text)]
    missing_amounts = [
        label for label, amount in facts["key_amounts"].items() if not any(abs(value - amount) < 0.006 for value in memo_values)
    ]
    missing_sections = [
        title
        for title in MEMO_SECTIONS
        if not re.search(r"(?im)^\W*(?:\d+[.)]\s*)?{}\b".format(re.escape(title)), memo_text)
    ]
    return {
        "ok": not (unverified or missing_amounts or missing_sections),
        "unverified": unverified,
        "missing_amounts": missing_amounts,
        "missing_sections": missing_sections,
    }
