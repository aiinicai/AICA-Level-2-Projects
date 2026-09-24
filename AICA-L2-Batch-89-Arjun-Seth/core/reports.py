# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Lease disclosure reports (Ind AS 116 or ASC 842) - the OUTPUT side of LeaseIQ Pro.

Pure Python. Everything is derived from the lease schedules already saved by the calculation engine, for ONE
currency (amounts are never added across currencies), as at a reporting month-end:

* portfolio summary, lease register
* maturity analysis of lease liabilities (undiscounted), reconciliation to the liability, current / non-current split
* lease liability movement and right-of-use asset movement for the 12 months to the reporting date
* lease costs for the period, weighted-average discount rate and remaining term
* the consolidated technical memo (the latest saved memo of each lease, or one generated from its results)
* reconciliation checks that prove the report adds up, and notes

The result is generic: ``report["sections"]`` are lists of blocks (heading / text / bullets / table) so the PDF,
Word and Excel renderers all draw the same content. Ind AS 116 has one on-balance-sheet group (plus exempt
leases); ASC 842 has an operating group and a finance group, each in its own column.
"""
import calendar
import re
from datetime import date, datetime

from core.dashboard import month_index
from core.formatting import CURRENCIES, NUMBER_FORMATS, currency_decimals, format_number, parse_currency
from core.memo_generator import build_memo_facts, build_template_memo

FRAMEWORKS = {"IND_AS_116": "Ind AS 116", "ASC_842": "ASC 842"}
FRAMEWORK_TITLES = {"IND_AS_116": "Ind AS 116 - Leases", "ASC_842": "ASC 842 - Leases"}
BAND_LABELS = [
    "Not later than 1 year",
    "Later than 1 year and not later than 2 years",
    "Later than 2 years and not later than 3 years",
    "Later than 3 years and not later than 4 years",
    "Later than 4 years and not later than 5 years",
    "Later than 5 years",
]


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def month_end(day: date) -> date:
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])


def _date_label(day: date) -> str:
    return "{} {} {}".format(day.day, day.strftime("%B"), day.year)


def _text(text: str) -> dict:
    return {"type": "text", "text": text}


def _heading(text: str, level: int = 3) -> dict:
    return {"type": "heading", "text": text, "level": level}


def _bullets(items: list) -> dict:
    return {"type": "bullets", "items": items}


def _table(title, columns, rows, total=None, notes=None, widths=None) -> dict:
    """``columns``: [(header, kind)] with kind text | money | count | percent | rate | date | months | years."""
    return {"type": "table", "title": title, "columns": columns, "rows": rows, "total": total, "notes": notes or [], "widths": widths}


# --------------------------------------------------------------------------- #
# per-lease analysis
# --------------------------------------------------------------------------- #
def analyse_lease(lease: dict, idx: int) -> dict:
    """Everything the report needs from ONE lease's saved schedule, as at reporting month index ``idx``.

    A lease is 'expired' at the reporting date once its last schedule month is on or before it (its liability and net
    asset are 0 and its gross cost and accumulated amortization are derecognised).
    """
    rows = {month_index(r["period_date"]): r for r in lease["schedule"]}
    first, last = min(rows), max(rows)
    w0 = idx - 11  # first month of the 12-month reporting period
    net_method = lease["rou_method"] == "net_direct"
    first_row = rows[first]
    out = {"first": first, "last": last, "net_method": net_method, "commenced": first <= idx, "expired": last <= idx}

    def liability_at(i):
        row = rows.get(i)
        return row["closing_liability"] if row else 0.0

    def net_at(i):
        row = rows.get(i)
        return row["rou_net_carrying_value"] if row else 0.0

    def active(i):  # on the books at the end of month i (gross method: derecognised once its last month has passed)
        return first <= i < last

    def gross_at(i):
        return (first_row["rou_gross_cost"] or 0.0) if (not net_method and active(i)) else 0.0

    def accum_at(i):
        row = rows.get(i)
        return (row["accum_amortization_closing"] or 0.0) if (not net_method and row and active(i)) else 0.0

    window = [i for i in range(w0, idx + 1) if i in rows]
    out["liability_at"], out["net_at"] = liability_at(idx), net_at(idx)
    out["liability_open"], out["net_open"] = liability_at(w0 - 1), net_at(w0 - 1)
    out["added"] = w0 <= first <= idx
    out["liability_added"] = first_row["opening_liability"] if out["added"] else 0.0
    if net_method:
        out["rou_added"] = (first_row["rou_net_carrying_value"] + (first_row["rou_reduction_plug"] or 0.0)) if out["added"] else 0.0
    else:
        out["rou_added"] = (first_row["rou_gross_cost"] or 0.0) if out["added"] else 0.0
    out["interest"] = sum(rows[i]["interest_expense"] or 0.0 for i in window)
    out["payments"] = sum(rows[i]["net_cash_payment"] or 0.0 for i in window)
    out["amortization"] = sum(((rows[i]["rou_reduction_plug"] if net_method else rows[i]["amortization_expense"]) or 0.0) for i in window)
    out["single_cost"] = sum(rows[i]["single_lease_cost"] or 0.0 for i in window) if net_method else 0.0
    out["gross_open"], out["gross_close"] = gross_at(w0 - 1), gross_at(idx)
    out["accum_open"], out["accum_close"] = accum_at(w0 - 1), accum_at(idx)
    out["expired_in_period"] = (not net_method) and w0 <= last <= idx
    out["gross_expired"] = (first_row["rou_gross_cost"] or 0.0) if out["expired_in_period"] and (first <= idx) else 0.0
    out["accum_expired"] = out["gross_expired"]  # a lease that has run its course is fully amortised
    out["months_active_in_period"] = len([i for i in range(max(first, w0), min(last, idx) + 1)])

    bands = [0.0] * 6
    future_interest = future_principal_12 = 0.0
    for i, row in rows.items():
        if i > idx:
            bands[min((i - idx - 1) // 12, 5)] += row["net_cash_payment"] or 0.0
            future_interest += row["interest_expense"] or 0.0
            if i <= idx + 12:
                future_principal_12 += row["principal_repayment"] or 0.0
    out["bands"], out["future_interest"], out["current_liability"] = bands, future_interest, future_principal_12
    out["remaining_months"] = max(0, last - idx)
    return out


# --------------------------------------------------------------------------- #
# the report
# --------------------------------------------------------------------------- #
def _memo_blocks(text: str) -> list:
    """Turn a memo's text into heading / bullet / paragraph blocks."""
    blocks, bullets = [], []

    def flush():
        if bullets:
            blocks.append(_bullets(list(bullets)))
            bullets.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
        elif stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
        elif re.match(r"^\d+\.\s+\S", stripped) and len(stripped) < 60:
            flush()
            blocks.append(_heading(stripped, 4))
        else:
            flush()
            blocks.append(_text(stripped))
    flush()
    return blocks


def build_disclosure_report(
    leases: list,
    framework: str,
    as_at: date,
    currency: str,
    number_style: str,
    scope_label: str,
    prepared_by: str = "",
    generated_at: datetime = None,
    include_memo: bool = True,
    memo_number_style: str = None,
) -> dict:
    """Assemble the disclosure report for one framework, one currency and one reporting date.

    ``leases``: one dict per lease with ``lease_ref, status, lessor, lessee, asset_type, commencement_date, end_date,
    term_months, ibr, classification, ind_as116_exemption, rou_method, single_lease_cost_per_month`` and ``schedule``
    (the saved schedule rows of THIS framework as dicts); optionally ``memo`` ({"version", "text"}) or, to generate a memo,
    ``memo_stored`` and ``case_data`` (see ``core.memo_generator.build_memo_facts``).
    """
    if framework not in FRAMEWORKS:
        raise ValueError("framework must be one of {}, got {!r}".format(", ".join(FRAMEWORKS), framework))
    code = parse_currency(currency) or str(currency).strip().upper()
    generated_at = generated_at or datetime.now()
    as_at = month_end(as_at)
    idx = month_index(as_at)
    style = number_style
    decimals = currency_decimals(code)
    currency_name = "{} - {}".format(code, CURRENCIES[code][0]) if code in CURRENCIES else code

    usable = [lease for lease in leases if lease.get("schedule")]
    analysed = [(lease, analyse_lease(lease, idx)) for lease in usable]
    included = [(lease, a) for lease, a in analysed if a["commenced"]]
    not_commenced = len(analysed) - len(included)
    skipped_no_schedule = len(leases) - len(usable)

    # ---- groups (each is its own column in the disclosure tables) ----
    if framework == "IND_AS_116":
        on_bs = [(l, a) for l, a in included if l.get("ind_as116_exemption") != "EXEMPT"]
        exempt = [(l, a) for l, a in included if l.get("ind_as116_exemption") == "EXEMPT"]
        groups = [("On-balance-sheet leases", on_bs)]
    else:
        exempt = []
        groups = [
            ("Operating leases", [(l, a) for l, a in included if l.get("classification") != "FINANCE LEASE"]),
            ("Finance leases", [(l, a) for l, a in included if l.get("classification") == "FINANCE LEASE"]),
        ]
    groups = [(label, members) for label, members in groups if members] or [(groups[0][0], [])]
    labels = [label for label, _ in groups]
    multi = len(groups) > 1
    on_books = [pair for _, members in groups for pair in members]

    def total_of(key, members=None):
        return sum(a[key] for _, a in (on_books if members is None else members))

    def by_group(key):
        values = [sum(a[key] for _, a in members) for _, members in groups]
        return values + ([sum(values)] if multi else [])

    columns = [("Item", "text")] + [(label, "money") for label in labels] + ([("Total", "money")] if multi else [])
    ncols = len(columns) - 1
    tolerance = 0.05 + 0.01 * max(1, len(included))
    checks = []

    def check(name, expected, actual):
        checks.append({"name": name, "expected": expected, "actual": actual, "difference": actual - expected, "ok": abs(actual - expected) <= tolerance})

    sections = []

    # ---- 1. report details ----
    details = [
        ["Framework", FRAMEWORK_TITLES[framework]],
        ["Reporting date (as at)", _date_label(as_at)],
        ["Reporting period", "12 months ended {}".format(_date_label(as_at))],
        ["Currency", currency_name],
        ["Number format", NUMBER_FORMATS.get(style, style)],
        ["Leases in scope", scope_label],
        ["Leases included", "{} ({} not yet commenced at the reporting date{})".format(len(included), not_commenced, "; {} without a saved schedule".format(skipped_no_schedule) if skipped_no_schedule else "")],
        ["Prepared by", prepared_by or "-"],
        ["Generated on", generated_at.strftime("%d-%b-%Y %H:%M")],
    ]
    sections.append({"id": "details", "title": "Report details", "blocks": [_table(None, [("Item", "text"), ("Detail", "text")], details, widths=[0.3, 0.7])]})

    # ---- maturity analysis ----
    band_rows = []
    for number, label in enumerate(BAND_LABELS):
        values = [sum(a["bands"][number] for _, a in members) for _, members in groups]
        band_rows.append([label] + values + ([sum(values)] if multi else []))
    undiscounted = [sum(row[c] for row in band_rows) for c in range(1, ncols + 1)]
    interest_future = [sum(a["future_interest"] for _, a in members) for _, members in groups] + ([total_of("future_interest")] if multi else [])
    liability_now = by_group("liability_at")
    current = [sum(a["current_liability"] for _, a in members) for _, members in groups] + ([total_of("current_liability")] if multi else [])
    maturity_total = [["Total undiscounted lease payments"] + undiscounted,
                      ["Less: future interest (unwinding of discount)"] + [-v for v in interest_future],
                      ["Lease liability at the reporting date"] + liability_now]
    check("Maturity analysis: undiscounted payments less future interest equals the lease liability", liability_now[-1], undiscounted[-1] - interest_future[-1])
    check("Lease liability presented as current + non-current equals the total liability", liability_now[-1], current[-1] + (liability_now[-1] - current[-1]))
    maturity_blocks = [
        _text("Undiscounted contractual lease payments after the reporting date, by time band, reconciled to the lease liability."),
        _table("Maturity analysis of lease liabilities", columns, band_rows, total=undiscounted and ["Total undiscounted lease payments"] + undiscounted),
        _table("Reconciliation to the lease liability", columns, [maturity_total[1], maturity_total[2]]),
        _table("Presentation in the balance sheet", columns, [["Current (due within 12 months)"] + current, ["Non-current"] + [l - c for l, c in zip(liability_now, current)]], total=["Total lease liability"] + liability_now),
    ]

    # ---- liability movement ----
    opening, added, interest, payments, closing = by_group("liability_open"), by_group("liability_added"), by_group("interest"), by_group("payments"), by_group("liability_at")
    for position in range(ncols):
        name = (labels + ["Total"])[position] if multi else labels[0]
        check("Lease liability movement closes ({})".format(name), closing[position], opening[position] + added[position] + interest[position] - payments[position])
    movement = [
        ["Opening balance"] + opening, ["Additions (leases commenced in the period)"] + added,
        ["Interest on lease liabilities"] + interest, ["Lease payments"] + [-v for v in payments],
    ]
    liability_blocks = [
        _text("Movement in the lease liability over the 12 months ended {}. Payments are the contractual cash payments in the schedule; rent paid in advance at commencement forms part of the right-of-use asset.".format(_date_label(as_at))),
        _table("Lease liability movement", columns, movement, total=["Closing balance"] + closing),
    ]

    # ---- right-of-use asset movement ----
    rou_blocks = [_text("Movement in the right-of-use assets over the 12 months ended {}.".format(_date_label(as_at)))]
    net_sum_close = 0.0
    for label, members in groups:
        if not members:
            continue
        if members[0][1]["net_method"]:  # ASC 842 operating: one net line
            o, ad, red, cl = (sum(a[k] for _, a in members) for k in ("net_open", "rou_added", "amortization", "net_at"))
            check("Right-of-use asset movement closes ({})".format(label), cl, o + ad - red)
            rou_blocks.append(_table("Right-of-use assets - {} (net carrying value)".format(label), [("Item", "text"), ("Amount", "money")],
                                     [["Opening net carrying value", o], ["Additions", ad], ["Reduction of the asset (amortization)", -red]], total=["Closing net carrying value", cl]))
        else:  # gross cost and accumulated amortization
            go, ad, ex, gc = (sum(a[k] for _, a in members) for k in ("gross_open", "rou_added", "gross_expired", "gross_close"))
            ao, ch, ax, ac = (sum(a[k] for _, a in members) for k in ("accum_open", "amortization", "accum_expired", "accum_close"))
            nc = sum(a["net_at"] for _, a in members)
            check("Gross cost movement closes ({})".format(label), gc, go + ad - ex)
            check("Accumulated amortization movement closes ({})".format(label), ac, ao + ch - ax)
            check("Gross cost less accumulated amortization equals the net carrying value ({})".format(label), nc, gc - ac)
            rou_blocks.append(_table("Right-of-use assets - {} (gross cost and accumulated amortization)".format(label), [("Item", "text"), ("Amount", "money")],
                                     [["Gross cost - opening", go], ["Additions", ad], ["Leases expired / derecognised", -ex], ["Gross cost - closing", gc],
                                      ["Accumulated amortization - opening", ao], ["Amortization charge for the period", ch], ["Leases expired / derecognised", -ax], ["Accumulated amortization - closing", ac]],
                                     total=["Net carrying value", nc]))
        net_sum_close += sum(a["net_at"] for _, a in members)

    # ---- lease costs ----
    interest_total = total_of("interest")
    if framework == "IND_AS_116":
        exempt_cost = 0.0
        for lease, a in exempt:
            exempt_cost += a["months_active_in_period"] * (lease.get("single_lease_cost_per_month") or 0.0)
        cost_rows = [["Interest on lease liabilities", interest_total], ["Depreciation of right-of-use assets", total_of("amortization")],
                     ["Expense relating to exempt leases (short-term / low-value)", exempt_cost]]
        cost_total = interest_total + total_of("amortization") + exempt_cost
        cash_rows = [["Cash paid for amounts included in lease liabilities", total_of("payments")], ["Expense paid for exempt leases (straight-line)", exempt_cost]]
        cost_blocks = [_table("Amounts recognised in profit or loss ({})".format("12 months ended " + _date_label(as_at)), [("Item", "text"), ("Amount", "money")], cost_rows, total=["Total", cost_total]),
                       _table("Total cash outflow for leases", [("Item", "text"), ("Amount", "money")], cash_rows, total=["Total cash outflow", total_of("payments") + exempt_cost])]
    else:
        op = [(l, a) for l, a in included if l.get("classification") != "FINANCE LEASE"]
        fin = [(l, a) for l, a in included if l.get("classification") == "FINANCE LEASE"]
        op_cost = sum(a["single_cost"] for _, a in op)
        fin_amort, fin_interest = sum(a["amortization"] for _, a in fin), sum(a["interest"] for _, a in fin)
        cost_rows = [["Operating lease cost (single straight-line cost)", op_cost], ["Finance lease cost - amortization of right-of-use assets", fin_amort], ["Finance lease cost - interest on lease liabilities", fin_interest]]
        cost_blocks = [
            _table("Lease cost ({})".format("12 months ended " + _date_label(as_at)), [("Item", "text"), ("Amount", "money")], cost_rows, total=["Total lease cost", op_cost + fin_amort + fin_interest]),
            _table("Supplemental cash flow information", [("Item", "text"), ("Amount", "money")],
                   [["Operating cash flows from operating leases", sum(a["payments"] for _, a in op)], ["Financing and operating cash flows from finance leases", sum(a["payments"] for _, a in fin)]],
                   total=["Cash paid for amounts included in lease liabilities", total_of("payments")]),
        ]

    # ---- weighted averages ----
    def weighted(members, key):
        weights = [a["liability_at"] for _, a in members]
        if not members:
            return None
        if sum(weights) <= 0:
            weights = [1.0] * len(members)
        return sum(w * key(l, a) for w, (l, a) in zip(weights, members)) / sum(weights)

    average_rows = []
    for label, members in groups + ([("All leases", on_books)] if multi else []):
        rate = weighted(members, lambda l, a: l["ibr"] or 0.0)
        term = weighted(members, lambda l, a: a["remaining_months"] / 12.0)
        average_rows.append([label, len(members), rate if rate is not None else None, term if term is not None else None])
    average_block = _table("Weighted-average discount rate and remaining lease term", [("Group", "text"), ("Leases", "count"), ("Weighted-average discount rate", "rate"), ("Weighted-average remaining term (years)", "years")], average_rows,
                           notes=["Weighted by the lease liability at the reporting date (equal weights if there is no liability)."])

    # ---- lease register ----
    register = []
    for lease, a in sorted(included, key=lambda pair: (pair[0].get("commencement_date") or date.min, pair[0]["lease_ref"])):
        is_exempt = lease.get("ind_as116_exemption") == "EXEMPT" and framework == "IND_AS_116"
        if framework == "IND_AS_116":
            kind = "Exempt (not on balance sheet)" if is_exempt else "On-balance sheet"
        else:
            kind = "Finance lease" if lease.get("classification") == "FINANCE LEASE" else "Operating lease"
        register.append([lease["lease_ref"], lease.get("lessor") or "-", lease.get("lessee") or "-", lease.get("asset_type") or "-", lease.get("commencement_date"), lease.get("end_date"),
                         lease.get("term_months"), kind, lease.get("ibr"), None if is_exempt else a["liability_at"], None if is_exempt else a["net_at"], lease.get("status") or "-"])
    check("Lease register liabilities add up to the total lease liability", liability_now[-1], sum(r[9] or 0.0 for r in register))
    check("Lease register net right-of-use assets add up to the closing net carrying value", net_sum_close, sum(r[10] or 0.0 for r in register))
    register_columns = [("Lease ID", "text"), ("Lessor", "text"), ("Lessee", "text"), ("Asset", "text"), ("Start date", "date"), ("End date", "date"), ("Months", "count"),
                        ("Classification" if framework == "ASC_842" else "Ind AS 116 treatment", "text"), ("Rate", "rate"), ("Lease liability", "money"), ("ROU asset (net)", "money"), ("Status", "text")]
    register_widths = [0.07, 0.095, 0.095, 0.06, 0.09, 0.09, 0.06, 0.105, 0.05, 0.10, 0.10, 0.085]

    # ---- summary ----
    rate_all = weighted(on_books, lambda l, a: l["ibr"] or 0.0)
    term_all = weighted(on_books, lambda l, a: a["remaining_months"] / 12.0)
    summary_rows = [["Leases included", len(included)]]
    if framework == "IND_AS_116":
        summary_rows += [["On-balance-sheet leases", len(groups[0][1])], ["Exempt leases (short-term / low-value)", len(exempt)]]
    else:
        summary_rows += [["Operating leases", len([1 for l, _ in included if l.get("classification") != "FINANCE LEASE"])], ["Finance leases", len([1 for l, _ in included if l.get("classification") == "FINANCE LEASE"])]]
    summary_money = [["Lease liability at the reporting date", liability_now[-1]], ["\u00a0\u00a0\u00a0of which current", current[-1]], ["\u00a0\u00a0\u00a0of which non-current", liability_now[-1] - current[-1]],
                     ["Right-of-use assets (net) at the reporting date", net_sum_close], ["Interest on lease liabilities (12 months)", interest_total], ["Lease payments (12 months)", total_of("payments")]]
    summary_blocks = [
        _table("Portfolio at a glance", [("Item", "text"), ("Number", "count")], summary_rows),
        _table("Key amounts", [("Item", "text"), ("Amount", "money")], summary_money),
        _table("Averages", [("Item", "text"), ("Value", "text")], [["Weighted-average discount rate", "-" if rate_all is None else "{:.2f}%".format(rate_all * 100)], ["Weighted-average remaining lease term", "-" if term_all is None else "{:.1f} years".format(term_all)]]),
    ]

    sections.append({"id": "summary", "title": "Portfolio summary", "blocks": summary_blocks})
    sections.append({"id": "register", "title": "Lease register", "blocks": [_text("The leases included in this report, with their position at the reporting date."), _table(None, register_columns, register, widths=register_widths)]})
    sections.append({"id": "maturity", "title": "Maturity analysis of lease liabilities", "blocks": maturity_blocks})
    sections.append({"id": "liability", "title": "Lease liability movement", "blocks": liability_blocks})
    sections.append({"id": "rou", "title": "Right-of-use assets", "blocks": rou_blocks})
    sections.append({"id": "costs", "title": "Lease costs and cash flows", "blocks": cost_blocks})
    sections.append({"id": "averages", "title": "Discount rate and remaining term", "blocks": [average_block]})

    # ---- consolidated technical memo ----
    memo_summary = {"saved": 0, "generated": 0}
    if include_memo:
        memo_blocks = [
            _text("This memo consolidates the technical accounting conclusions for the {} lease{} in {} included in this report, as at {}, under {}.".format(
                len(included), "" if len(included) == 1 else "s", currency_name, _date_label(as_at), FRAMEWORK_TITLES[framework])),
        ]
        if framework == "IND_AS_116":
            memo_blocks.append(_text("Classification summary: {} lease{} recognised on the balance sheet and {} exempt under the short-term / low-value recognition exemptions.".format(len(groups[0][1]), "" if len(groups[0][1]) == 1 else "s", len(exempt))))
        else:
            memo_blocks.append(_text("Classification summary: {} operating and {} finance lease{}.".format(len([1 for l, _ in included if l.get("classification") != "FINANCE LEASE"]), len([1 for l, _ in included if l.get("classification") == "FINANCE LEASE"]), "" if len(included) == 1 else "s")))
        memo_blocks.append(_text("Measurement summary: lease liability of {} {} and net right-of-use assets of {} {} at the reporting date.".format(code, format_number(liability_now[-1], style, decimals), code, format_number(net_sum_close, style, decimals))))
        memo_blocks.append(_text("Basis: for each lease the latest saved technical memo is reproduced; where none has been saved, the memo is generated directly from the lease's validated inputs and calculation results. This is a draft for professional review, not a final accounting opinion."))
        for lease, _ in sorted(included, key=lambda pair: pair[0]["lease_ref"]):
            saved = lease.get("memo")
            if saved and saved.get("text"):
                body, source = saved["text"], "saved memo, version {}".format(saved.get("version", "?"))
                memo_summary["saved"] += 1
            elif lease.get("memo_stored") is not None and lease.get("case_data") is not None:
                facts = build_memo_facts(lease["case_data"], lease["memo_stored"], code, memo_number_style or style)
                body, source = build_template_memo(facts), "generated from results"
                memo_summary["generated"] += 1
            else:
                body, source = "No memo has been saved for this lease and its results could not be loaded.", "not available"
            memo_blocks.append(_heading("{} - {} / {}   ({})".format(lease["lease_ref"], lease.get("lessor") or "-", lease.get("lessee") or "-", source), 3))
            memo_blocks += _memo_blocks(body)
        sections.append({"id": "memo", "title": "Consolidated technical memo", "blocks": memo_blocks})

    # ---- checks and notes ----
    passed = len([c for c in checks if c["ok"]])
    check_rows = [[c["name"], c["expected"], c["actual"], c["difference"], "Passed" if c["ok"] else "CHECK"] for c in checks]
    sections.append({"id": "checks", "title": "Reconciliation checks", "blocks": [
        _text("{} of {} reconciliation checks passed. Each check re-derives a total two ways from the saved schedules.".format(passed, len(checks))),
        _table(None, [("Check", "text"), ("Expected", "money"), ("Actual", "money"), ("Difference", "money"), ("Result", "text")], check_rows, widths=[0.5, 0.15, 0.15, 0.1, 0.1]),
    ]})
    notes = [
        "All amounts are in {}. Amounts in other currencies are never added together; run the report again for each currency.".format(currency_name),
        "Figures come from the lease schedules saved when each lease was validated and calculated. Balances are month-end balances at {}; a lease that has not commenced by then is left out, and a lease whose final month is on or before it has a nil balance.".format(_date_label(as_at)),
        "Maturity analysis: undiscounted contractual payments from the month after the reporting date, in 12-month bands.",
        "Current portion of the lease liability = principal repayable in the 12 months after the reporting date; the rest is non-current.",
        "Movements cover the 12 months ended {}. Additions are leases that commenced in that period, measured at commencement.".format(_date_label(as_at)),
    ]
    if framework == "IND_AS_116":
        notes.append("Ind AS 116: leases marked exempt (short-term or low-value election) are not recognised on the balance sheet; their expense is shown on a straight-line basis.")
    else:
        notes.append("ASC 842: operating leases carry a single straight-line lease cost and the asset is reduced by the balancing amount; finance leases carry interest and amortization separately.")
    notes.append("Number format: {}. This report is a draft for professional review and not an audit opinion.".format(NUMBER_FORMATS.get(style, style)))
    sections.append({"id": "notes", "title": "Notes and definitions", "blocks": [_bullets(notes)]})

    return {
        "kind": "disclosure",
        "framework": framework,
        "framework_label": FRAMEWORKS[framework],
        "framework_title": FRAMEWORK_TITLES[framework],
        "title": "Lease Disclosure Report - {}".format(FRAMEWORKS[framework]),
        "as_at": as_at,
        "as_at_label": _date_label(as_at),
        "generated_at": generated_at,
        "prepared_by": prepared_by,
        "currency": code,
        "currency_name": currency_name,
        "symbol": CURRENCIES[code][1] if code in CURRENCIES else code,
        "decimals": decimals,
        "number_style": style,
        "number_format_label": NUMBER_FORMATS.get(style, style),
        "leases_included": len(included),
        "not_commenced": not_commenced,
        "groups": labels,
        "sections": sections,
        "checks": checks,
        "checks_passed": passed,
        "memo": memo_summary,
        "liability_at": liability_now[-1],
    }


def report_file_stem(report: dict) -> str:
    """'LeaseIQ_IndAS116_Disclosures_INR_2026-09-30'"""
    return "LeaseIQ_{}_Disclosures_{}_{}".format(report["framework_label"].replace(" ", ""), report["currency"], report["as_at"].strftime("%Y-%m-%d"))


def cell_text(value, kind: str, report: dict) -> str:
    """How a table cell is shown in text formats (PDF, Word): accounting style - negatives in brackets, nil as a dash."""
    if value is None:
        return "-"
    if kind == "money":
        if abs(value) < 0.005:
            return "-"
        text = format_number(abs(value), report["number_style"], report["decimals"])
        return "({})".format(text) if value < 0 else text
    if kind == "count":
        return "{:,}".format(int(value))
    if kind == "percent":
        return "{:.1f}%".format(value * 100)
    if kind == "rate":
        return "{:.2f}%".format(value * 100)
    if kind == "years":
        return "{:.1f}".format(value)
    if kind == "date":
        return value.strftime("%d-%b-%Y") if hasattr(value, "strftime") else str(value)
    return str(value)


def column_widths(table: dict, total_width: float) -> list:
    """Absolute column widths for a table: the block's own fractions, or a text-length based split."""
    columns = table["columns"]
    if table.get("widths"):
        fractions = table["widths"]
    else:
        weights = []
        for index, (header, kind) in enumerate(columns):
            sample = [len(str(row[index])) if kind == "text" and row[index] is not None else 14 for row in table["rows"]] or [10]
            weights.append(max(min(max(sample + [len(header) * 0.6]), 60), 12 if kind != "text" else 16))
        fractions = [w / sum(weights) for w in weights]
    scale = total_width / sum(fractions)
    return [f * scale for f in fractions]
