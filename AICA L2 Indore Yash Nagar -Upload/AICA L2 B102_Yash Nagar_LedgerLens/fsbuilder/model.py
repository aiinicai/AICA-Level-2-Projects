"""Turn mapped ledgers into presentable Schedule III statements, notes and review items.

Everything here is numbers and structure; rendering to Word/Excel is in render.py.
Amounts are whole rupees. Totals are sums of the rounded figures so every column foots.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .cashflow import build_cash_flow
from .format import Unit, as_unit, dmy, rnd, rs
from .mapping import Rulebook
from .statements import line_totals
from .tb import TrialBalance

# Information the Companies Act requires in the notes that a Tally trial balance cannot supply.
# Shown as open items; nothing is invented.
DISCLOSURE_GAPS = {
    "EQ.SC": ["Authorised, issued, subscribed and paid-up shares (number and amount), par value and rights/preferences",
              "Reconciliation of shares outstanding at the start and end of the year",
              "Shareholders holding more than 5%, and promoter shareholding at the end and at the beginning of the year with the % change"],
    "EQ.RS": ["Nature and purpose of each reserve; any appropriations (dividend, transfer to reserves) for the year"],
    "NCL.LTB": ["Terms of repayment, rate of interest and security for each loan; defaults; current maturities of "
                "long-term debt (to be shown under other current liabilities)",
                "Loans from directors and other related parties: terms and amounts (related-party disclosure)"],
    "CL.TP": ["Ageing of trade payables from the due date of payment (less than 1 year, 1-2, 2-3, more than 3 years): MSME, others and disputed dues",
              "Dues to micro and small enterprises (MSMED Act, 2006): principal, interest, payments beyond 45 days"],
    "CL.OCL": ["Current maturities of long-term borrowings; statutory dues overdue, if any"],
    "NCA.PPE": ["Gross block, accumulated depreciation and impairment for each class; additions, disposals and "
                "transfers (Tally shows only the net book value here)",
                "Useful lives or depreciation rates and method; title deeds of immovable property; revaluation, if any"],
    "CA.INV": ["Basis of valuation (lower of cost and net realisable value) and how closing stock was determined"],
    "CA.TR": ["Ageing of trade receivables from the due date of payment (under 6 months, 6 months to 1 year, 1-2, 2-3, over 3 years): undisputed and disputed, good and doubtful",
              "Receivables from related parties and from directors; provision for doubtful debts"],
    "CA.CBB": ["Maturity and any lien/margin on bank deposits; earmarked balances"],
    "REV.OPS": ["Break-up of revenue by product/service where material; GST treatment of sales"],
    "EXP.OTH": ["Payment to auditors: audit fee, tax audit, other services, reimbursements",
                "Items of other expenses exceeding 1% of revenue or Rs 1,00,000, whichever is higher, shown separately",
                "CSR expenditure (Sec 135) if applicable; value of imports and foreign exchange earnings/outgo"],
}
GENERAL_GAPS = [
    "Significant accounting policies (AS 1) and the basis of preparation",
    "Earnings per share (AS 20): number of equity shares and weighted average",
    "Related-party disclosures (AS 18): names, relationships, transactions and balances (including director remuneration)",
    "Contingent liabilities and commitments (AS 29); employee benefits (AS 15); segment information (AS 17) if applicable",
    "The 11 ratios required by Schedule III with explanations for changes above 25%",
]

BS_SECTIONS = [
    ("EQUITY AND LIABILITIES", None),
    ("Shareholders' funds", ["EQ.SC", "EQ.RS"]),
    ("Non-current liabilities", ["NCL.LTB", "NCL.DTL", "NCL.OLL", "NCL.LTP"]),
    ("Current liabilities", ["CL.STB", "CL.TP", "CL.OCL", "CL.STP"]),
    ("TOTAL EQUITY AND LIABILITIES", "TOTAL_L"),
    ("ASSETS", None),
    ("Non-current assets", ["NCA.PPE", "NCA.INTG", "NCA.CWIP", "NCA.NCI", "NCA.DTA", "NCA.LTLA", "NCA.ONCA"]),
    ("Current assets", ["CA.CI", "CA.INV", "CA.TR", "CA.CBB", "CA.STLA", "CA.OCA"]),
    ("TOTAL ASSETS", "TOTAL_A"),
]
PL_EXPENSE_LINES = ["EXP.COM", "EXP.PST", "EXP.CHI", "EXP.EMP", "EXP.FIN", "EXP.DEP", "EXP.OTH"]


@dataclass
class Row:
    label: str
    note: int | None = None
    cur: int | None = None
    prev: int | None = None
    kind: str = "item"            # head | sub | item | subitem | total | blank
    flags: list = field(default_factory=list)


@dataclass
class Note:
    no: int
    title: str
    header: list
    rows: list                    # lists: [label, v1, v2, ...] (ints/None) ; a str-only row is a sub-heading
    total: list | None = None
    gaps: list = field(default_factory=list)
    comment: str = ""
    movement: dict | None = None   # optional second table: header, rows, total, comment
    kind: str = "amounts"          # "text" for a note whose cells are words (the ratios), not rupee amounts


@dataclass
class Flag:
    ref: str                      # R1.. classification judgements, O1.. observations
    kind: str                     # "Classification" | "Observation"
    area: str
    ledger: str
    amount: int | None
    text: str
    line: str = ""


@dataclass
class Signatories:
    """Who signs the statements: the auditors on the left, the Board on the right. Blank fields print as lines to fill in."""
    firm: str = "XYZ Chartered Accountants"
    frn: str = ""
    partner: str = ""
    membership: str = ""
    place: str = ""
    sign_date: date | None = None            # date the auditors sign
    company: str = ""                        # defaults to the company name
    directors: list = field(default_factory=lambda: [("", ""), ("", "")])   # (name, DIN) for two directors
    board_date: date | None = None           # date the directors sign


@dataclass
class Model:
    company: str
    as_at: date
    prev_as_at: date
    bs: list
    pl: list
    notes: list
    flags: list
    basis: list
    general_gaps: list
    mapping: pd.DataFrame
    rounding: list
    profit: int = 0
    cashflow: list = field(default_factory=list)
    cf_notes: list = field(default_factory=list)
    cce: list = field(default_factory=list)   # components of cash and cash equivalents
    figures: dict = field(default_factory=dict)   # raw components for the reviewer (whole rupees)
    cf: dict = field(default_factory=dict)
    unit: Unit = field(default_factory=lambda: as_unit(None))   # how amounts are presented; all amounts are multiples of unit.step
    sign: Signatories | None = None
    review: object = None                 # the reviewer's result, set when the files are written (AI remarks go into the Excel file)
    disclosures: list = field(default_factory=list)   # additional regulatory information and statutory disclosures (fsbuilder.disclosures)


def _letters(i: int) -> str:
    return "abcdefghijklmnopqrstuvwxyz"[i]


def _roman(i: int) -> str:
    return ["i", "ii", "iii", "iv", "v", "vi"][i]


def build_model(tb: TrialBalance, mapped: pd.DataFrame, rb: Rulebook | None = None, unit=None) -> Model:
    rb = rb or Rulebook.load()
    lines = rb.lines
    totals = line_totals(mapped, rb)
    unit = as_unit(unit)
    step = unit.step
    as_at = tb.to_date or date.today()
    prev_as_at = date(as_at.year - 1, as_at.month, as_at.day) if not (as_at.month == 2 and as_at.day == 29) else date(as_at.year - 1, 2, 28)
    basis = list(tb.adjustments) + list(tb.warnings)
    rounding: list = []

    # ---- subs by line, rounded (statement amounts) ----
    subs: dict[str, list] = {}
    for r in totals.itertuples(index=False):
        subs.setdefault(r.line, []).append([r.sub, rnd(r.closing, step), rnd(r.opening, step)])

    # P&L profit from the rounded P&L lines, then the surplus sub is set to it so P&L and BS agree
    def line_sum(k, col):
        return sum(s[col] for s in subs.get(k, []))
    income = sum(line_sum(k, 1) for k in ("REV.OPS", "REV.OI"))
    expense = sum(line_sum(k, 1) for k in PL_EXPENSE_LINES + ["TAX.CUR", "TAX.DEF"])
    profit = income - expense

    # reserves: split reserves from the surplus account so the note can show the movement
    res_subs = subs.get("EQ.RS", [])
    surplus_bf_cur = sum(s[2] for s in res_subs if s[0].startswith("Surplus in statement"))   # = opening balance
    other_res = [s for s in res_subs if not s[0].startswith("Surplus")]
    surplus_cf = surplus_bf_cur + profit
    subs["EQ.RS"] = other_res + ([["Surplus in the statement of profit and loss", surplus_cf, surplus_bf_cur]]
                                 if (surplus_cf or surplus_bf_cur) else [])

    def total(k, col):
        return sum(s[col] for s in subs.get(k, []))

    # ---- rounding reconciliation of the balance sheet ----
    for col, label in ((1, as_at), (2, prev_as_at)):
        a = sum(total(k, col) for k in lines if lines[k]["statement"] == "BS" and lines[k]["side"] == "A")
        e = sum(total(k, col) for k in lines if lines[k]["statement"] == "BS" and lines[k]["side"] == "L")
        if a != e:
            diff = a - e
            cand = max((s for k in lines if lines[k]["statement"] == "BS" and lines[k]["side"] == "L" for s in subs.get(k, [])),
                       key=lambda s: abs(s[col]), default=None)
            if cand is not None and abs(diff) <= 25 * step:
                cand[col] += diff
                rounding.append(f"Rounding difference of {rs(diff)} at {dmy(label)} absorbed in '{cand[0]}' "
                                "so that the balance sheet agrees.")
            else:
                basis.append(f"Balance sheet at {dmy(label)} does not agree: assets {rs(a)} vs equity and liabilities {rs(e)}.")
    basis += rounding

    # ---- flags (classification judgements) ----
    flags: list[Flag] = []
    line_flags: dict[str, list] = {}
    for r in mapped.itertuples(index=False):
        if r.review and (abs(r.opening) >= 0.005 or abs(r.closing) >= 0.005 or r.source == "unmapped"):
            ref = f"R{len([f for f in flags if f.kind == 'Classification']) + 1}"
            sign = -1 if lines.get(r.line, {}).get("side") == "L" else 1
            flags.append(Flag(ref, "Classification", r.line_label, r.ledger, rnd(sign * r.closing, step), r.review, r.line))
            line_flags.setdefault(r.line, []).append(ref)

    # ---- numbered notes (BS lines first, then P&L), only for lines with an amount ----
    notes: list[Note] = []
    note_no: dict[str, int] = {}
    order = sorted((k for k in lines if k in subs and (total(k, 1) or total(k, 2))), key=lambda k: lines[k]["order"])
    cy, py = f"As at {dmy(as_at)}", f"As at {dmy(prev_as_at)}"
    cyp = f"Year ended {dmy(as_at)}"
    pl_n: dict = {}
    for k in order:
        n = len(notes) + 1
        note_no[k] = n
        is_bs = lines[k]["statement"] == "BS"
        hdr = ["Particulars", cy, py] if is_bs else ["Particulars", cyp]
        rows = []
        for s in sorted(subs[k], key=lambda s: -abs(s[1])):
            if s[1] or s[2]:
                rows.append([s[0], s[1], s[2]] if is_bs else [s[0], s[1]])
        t = [total(k, 1), total(k, 2)] if is_bs else [total(k, 1)]
        note = Note(n, lines[k]["label"], hdr, rows, ["Total"] + t, gaps=DISCLOSURE_GAPS.get(k, []))
        if k == "EQ.RS":
            note.rows = [r for r in rows if not r[0].startswith("Surplus")]
            note.rows += [["Surplus in the statement of profit and loss:"],
                          ["Opening balance", surplus_bf_cur, None],
                          ["Add: profit for the year", profit, None],
                          ["Closing balance", surplus_cf, surplus_bf_cur]]
        if k == "NCA.PPE":
            note.comment = ("Net book values as recorded in Tally. Depreciation is credited directly to the asset "
                            "in the books, so gross block and accumulated depreciation are not available.")
        notes.append(note)

    # PPE movement table from period debits/credits, when available (live XML does not carry them)
    led = tb.ledgers.set_index("name")
    ppe = mapped[mapped["line"] == "NCA.PPE"]
    if len(ppe) and "NCA.PPE" in note_no and led.loc[ppe["ledger"], "period_dr"].notna().all():
        mv = []
        for cls, g in ppe.groupby("sub"):
            idx = g["ledger"]
            mv.append([cls, rnd(g["opening"].sum(), step), rnd(led.loc[idx, "period_dr"].sum(), step),
                       rnd(-led.loc[idx, "period_cr"].sum(), step), rnd(g["closing"].sum(), step)])
        mv.sort(key=lambda r: -abs(r[4]))
        next(n for n in notes if n.no == note_no["NCA.PPE"]).movement = {
            "title": "Movement in net book value during the year",
            "header": ["Class", "Opening", "Additions", "Deductions / depreciation", "Closing"], "rows": mv,
            "total": ["Total"] + [sum(r[i] for r in mv) for i in range(1, 5)],
            "comment": "Deductions include depreciation charged directly to the asset."}

    # ---- balance sheet rows ----
    def flagged(row, k):
        row.flags = line_flags.get(k, [])
        return row

    def item_row(k, label=None, kind="item"):
        return flagged(Row(label or lines[k]["label"], note_no.get(k), total(k, 1), total(k, 2), kind), k)

    present = lambda k: k in note_no  # noqa: E731
    bs: list[Row] = []
    sec_no = 0
    for title, keys in BS_SECTIONS:
        if keys is None:
            bs.append(Row(title, kind="head"))
            sec_no = 0
        elif isinstance(keys, str):
            side = "L" if keys == "TOTAL_L" else "A"
            c = sum(total(k, 1) for k in lines if lines[k]["statement"] == "BS" and lines[k]["side"] == side)
            p = sum(total(k, 2) for k in lines if lines[k]["statement"] == "BS" and lines[k]["side"] == side)
            bs.append(Row(title, None, c, p, "total"))
        else:
            have = [k for k in keys if present(k)]
            if not have:
                continue
            sec_no += 1
            bs.append(Row(f"{sec_no}. {title}", kind="sub"))
            ppe_group = [k for k in ("NCA.PPE", "NCA.INTG", "NCA.CWIP") if k in have]
            rest = [k for k in have if k not in ppe_group]
            li = 0
            if ppe_group:
                bs.append(Row(f"({_letters(li)}) Property, plant and equipment and intangible assets", kind="item"))
                for j, k in enumerate(ppe_group):
                    bs.append(item_row(k, f"({_roman(j)}) {lines[k]['label']}", "subitem"))
                li += 1
            for k in rest:
                bs.append(item_row(k, f"({_letters(li)}) {lines[k]['label']}"))
                li += 1

    # ---- profit and loss rows ----
    def pl_item(k, label=None):
        return flagged(Row(label or lines[k]["label"], note_no.get(k), total(k, 1), None), k)

    pl: list[Row] = []
    ops, oi = total("REV.OPS", 1), total("REV.OI", 1)
    pl.append(pl_item("REV.OPS", "I. Revenue from operations"))
    pl.append(pl_item("REV.OI", "II. Other income"))
    total_income = ops + oi
    pl.append(Row("III. Total income (I + II)", None, total_income, None, "total"))
    pl.append(Row("IV. Expenses:", kind="sub"))
    for k in PL_EXPENSE_LINES:
        if present(k):
            pl.append(pl_item(k))
    total_exp = sum(total(k, 1) for k in PL_EXPENSE_LINES)
    pl.append(Row("Total expenses", None, total_exp, None, "total"))
    pbt = total_income - total_exp
    pl.append(Row("V. Profit / (loss) before tax (III - IV)", None, pbt, None, "total"))
    tax = total("TAX.CUR", 1) + total("TAX.DEF", 1)
    pl.append(Row("VI. Tax expense:", kind="sub"))
    pl.append(flagged(Row("(1) Current tax", note_no.get("TAX.CUR"), total("TAX.CUR", 1), None, "subitem"), "TAX.CUR"))
    pl.append(Row("(2) Deferred tax", note_no.get("TAX.DEF"), total("TAX.DEF", 1), None, "subitem"))
    pl.append(Row("VII. Profit / (loss) for the year (V - VI)", None, pbt - tax, None, "total"))
    pl.append(Row("VIII. Earnings per equity share (Rs): to be computed",
                  None, None, None, "item"))
    assert pbt - tax == profit, "profit mismatch between P&L and reserves"

    # ---- cash flow statement (AS 3, indirect) ----
    def pick(line, pred):
        return sum(x[1] for x in subs.get(line, []) if pred(x[0]))
    cf = build_cash_flow(subs, lines, dict(
        pbt=pbt, profit=profit, tax_expense=tax, dep=total("EXP.DEP", 1), fin=total("EXP.FIN", 1),
        interest=pick("REV.OI", lambda n: n == "Interest income"),
        dividend=pick("REV.OI", lambda n: n == "Dividend income"),
        gain=pick("REV.OI", lambda n: n.startswith("Net gain on sale"))), line_flags.get("CA.CBB", []))
    if cf["diff"]:
        basis.append(f"Cash flow statement does not reconcile to the balance sheet by {rs(cf['diff'])}.")
    cashflow = [Row(lab, None, v, None, kind, fl) for lab, v, kind, fl in cf["rows"]]
    cce = [[x[0], x[1], x[2]] for x in subs.get("CA.CBB", []) if not x[0].startswith("Other bank balances") and (x[1] or x[2])]

    # ---- raw figures for the reviewer (ratios, analytics) ----
    def tl(prefix, col):
        return sum(total(k, col) for k in lines if k.startswith(prefix))
    figures = {}
    for col, name in ((1, "cur"), (2, "prev")):
        figures[name] = dict(
            ca=tl("CA.", col), cl=tl("CL.", col), ltb=total("NCL.LTB", col), stb=total("CL.STB", col),
            equity=total("EQ.SC", col) + total("EQ.RS", col), share_capital=total("EQ.SC", col), inv=total("CA.INV", col),
            tr=total("CA.TR", col), tp=total("CL.TP", col), intang=total("NCA.INTG", col), dtl=total("NCL.DTL", col),
            investments=total("NCA.NCI", col) + total("CA.CI", col), ppe=total("NCA.PPE", col),
            cce=sum(x[col] for x in subs.get("CA.CBB", []) if not x[0].startswith("Other bank balances")),
            other_bank=sum(x[col] for x in subs.get("CA.CBB", []) if x[0].startswith("Other bank balances")),
            ocl=total("CL.OCL", col))
    figures["pl"] = dict(
        revenue=ops, other_income=oi, pat=profit, pbt=pbt, tax=tax, fin=total("EXP.FIN", 1), dep=total("EXP.DEP", 1),
        cogs=total("EXP.COM", 1) + total("EXP.PST", 1) + total("EXP.CHI", 1),
        purchases=pick("EXP.COM", lambda n: not n.startswith("Opening less closing")) + total("EXP.PST", 1),
        interest_income=pick("REV.OI", lambda n: n == "Interest income"),
        employee=total("EXP.EMP", 1), other_exp=total("EXP.OTH", 1),
        lt_repaid=max(0, -cf["buckets"]["lt_debt"]), cfo=cf["cfo"])
    figures["pl_prev"] = None   # previous-year P&L is not loaded

    # ---- observations the builder can state from the numbers alone ----
    obs: list[Flag] = []

    def add_obs(area, text, amount=None):
        obs.append(Flag(f"O{len(obs) + 1}", "Observation", area, "", amount, text))
    add_obs("Comparatives", "Only one year's trial balance was loaded, so the previous-year columns of the statement of "
            "profit and loss and the cash flow statement are blank. Load the previous year's data to complete them.")
    if profit > 0 and not tax:
        add_obs("Tax", f"The books show a profit of {rs(profit)} but no income-tax expense or provision (current or "
                "deferred). Confirm the tax computation and book the provision before finalising.", profit)
    inv = mapped[mapped["line"] == "CA.INV"]
    purchases = total("EXP.COM", 1)
    if len(inv) and (inv["opening"] - inv["closing"]).abs().max() < 0.5 and purchases > 0:
        add_obs("Inventories", "Closing stock equals opening stock for every inventory ledger although "
                f"purchases were {rs(purchases)}. Confirm the year-end stock was recorded; otherwise cost of "
                "materials and profit are misstated.", rnd(inv["closing"].sum(), step))
    paid_up, turnover = total("EQ.SC", 1), total("REV.OPS", 1)
    if 0 < paid_up <= 40_000_000 and turnover <= 400_000_000:
        add_obs("Cash flow statement", f"Paid-up capital of {rs(paid_up)} and turnover of {rs(turnover)} are within the "
                "small-company limits (Rs 4 crore and Rs 40 crore, as currently notified), in which case a cash flow "
                "statement is not mandatory (Sec 2(40)). Confirm the company's status; it is included for completeness.")
    flags += obs

    model = Model(tb.company or "Company", as_at, prev_as_at, bs, pl, notes, flags, basis, GENERAL_GAPS, mapped,
                  rounding, profit, cashflow, cf["notes"], cce, figures, cf, unit)
    model.notes.append(ratio_note(model, len(model.notes) + 1))
    from .disclosures import disclosure_sections
    model.disclosures = disclosure_sections(model)
    return model


def ratio_note(model: "Model", number: int, explanations: dict | None = None) -> Note:
    """Schedule III (Division I, additional regulatory information, GN para 8.9.12): the 11 ratios, the line items
    in each numerator and denominator, and the reason for any change above 25%.
    `explanations` maps ratio id -> text, used when a reviewer or the AI has supplied the reasons."""
    from .reviewer.ratios import compute_ratios, fmt_value, fmt_variance
    explanations = explanations or {}
    ratios = compute_ratios(model)

    def reason(r):
        if r.id in explanations:
            return explanations[r.id]
        if r.flagged:
            return "[Management to explain: the change exceeds 25%]"
        if r.cur is not None and r.prev is None:
            return "Previous-year figure needs the previous year's profit and loss."
        return "-" if r.cur is not None else "Not applicable"
    rows = [[r.name, fmt_value(r, r.cur), fmt_value(r, r.prev), fmt_variance(r.variance), reason(r)] for r in ratios]
    definitions = [[r.name, r.formula.split(" / ", 1)[0], r.formula.split(" / ", 1)[-1]] for r in ratios]
    return Note(number, "Analytical ratios", ["Ratio", "Current year", "Previous year", "% change", "Reason for change over 25%"],
                rows, None, kind="text",
                gaps=["Return on investment: the time-weighted method needs the market value and cash flows of the investment portfolio"]
                if any(r.id == "roi" and r.cur is None for r in ratios) else [],
                comment="A ratio is shown as not measurable where it needs the previous year's profit and loss, which was not loaded.",
                movement={"title": "Items included in the numerator and denominator", "header": ["Ratio", "Numerator", "Denominator"],
                          "rows": definitions, "total": None, "comment": "Definitions follow the ICAI Guidance Note on Division I, Annexure B."})
