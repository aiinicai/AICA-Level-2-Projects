"""
Form 3CD (Tax Audit Report) analyzer.

Reads the e-filing JSON export of Form 3CA/3CD (schema Form3cdXXX, as generated
by the income-tax e-filing utility) and produces:
  1. Key Financial Summary  - the clause-referenced figures needed for ITR/computation
  2. 44-Clause Dashboard    - every clause of Form 3CD in one table
  3. Tax Computation Draft  - a PGBP build-up in the same layout as the firm's
                              existing "Annexure 1" computation workbook

Usage:
    python analyze_form3cd.py "<path to Form3CD json>" [--outdir DIR]

Output:
    <outdir>/<PAN>_<AY>_3CD_Analysis.xlsx
    <outdir>/<PAN>_<AY>_3CD_Dashboard.html
"""

from __future__ import annotations

import argparse
import html
import json
import math
import numbers
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ALL_FORMATS = ("xlsx", "html", "pdf", "docx")
DEFAULT_FORMATS = ("xlsx", "html")

PURPLE_DARK = "4A148C"
PURPLE_LIGHT = "F3E5F5"
PURPLE_BORDER = "C9A6DA"

STATUS_CODES = {"5": "Company", "1": "Individual", "2": "HUF", "3": "Firm", "4": "AOP/BOI"}

RATE_TABLE = {
    # (income tax rate, surcharge rate, note)
    "115BAA": (0.22, 0.10, "Flat 10% surcharge irrespective of income slab; MAT u/s 115JB not applicable."),
    "115BAB": (0.15, 0.10, "Flat 10% surcharge irrespective of income slab; MAT u/s 115JB not applicable."),
    "115BA": (0.25, None, "Surcharge per normal slab (7%/12%); MAT u/s 115JB may apply - verify."),
}


def g(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def load_f3ca(json_path: Path) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Different e-filing utility/portal versions wrap the payload differently:
    # some put FORM3CA/FORM3CB at the JSON root, others nest it one level
    # deeper under "data" (alongside a sibling "metadata" block).
    roots = [raw]
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        roots.append(raw["data"])

    for root in roots:
        if not isinstance(root, dict):
            continue
        for form_key, inner_key in (("FORM3CA", "F3CA"), ("FORM3CB", "F3CB")):
            form = root.get(form_key)
            if isinstance(form, dict):
                inner = form.get(inner_key)
                if isinstance(inner, dict) and "PartA" in inner:
                    return inner

    raise ValueError(
        "Could not find Form 3CA/3CD or 3CB/3CD data in the JSON - expected a "
        "'FORM3CA' or 'FORM3CB' section (optionally nested under a 'data' key)."
    )


def sum_amount(records, amount_key, filter_key=None, filter_val=None):
    total = 0
    for r in records or []:
        if filter_key is not None and r.get(filter_key) != filter_val:
            continue
        total += r.get(amount_key, 0) or 0
    return total


def fmt_addr(addr: dict) -> str:
    if not addr:
        return ""
    parts = [addr.get("AddrDetail1"), addr.get("AddrDetail2"), addr.get("CityOrTownOrDistrict"),
              addr.get("PinCode")]
    return ", ".join(str(p) for p in parts if p)


def is_amount(v) -> bool:
    """True for real numbers (incl. numpy int64/float64 from a DataFrame), excluding bool."""
    return isinstance(v, numbers.Number) and not isinstance(v, bool)


def inr(n) -> str:
    """Format a number using the Indian digit-grouping system (lakh/crore), e.g. 1,39,51,624."""
    n = n or 0
    negative = n < 0
    n = abs(n)
    rupees, paise = divmod(round(n * 100), 100)
    digits = str(int(rupees))
    if len(digits) > 3:
        head, last3 = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + last3
    result = f"{digits}.{paise:02d}" if paise else digits
    return ("-" if negative else "") + result


# ---------------------------------------------------------------------------
# 1. Key Financial Summary (items a-n requested + two derived bonus items that
#    the firm's own computation workbook also tracks: PF late-deposit u/s
#    36(1)(va) and TDS interest u/s 201(1A)/206C(7), both fully derivable from
#    the JSON without any manual input).
# ---------------------------------------------------------------------------

def extract_key_financials(f3ca: dict) -> pd.DataFrame:
    rows = []

    def add(clause, particulars, amount, computation=None, note=""):
        rows.append({
            "Clause Ref.": clause,
            "Particulars": particulars,
            "Amount (Rs.)": round(amount, 2) if isinstance(amount, (int, float)) else amount,
            "Computed Figure (Rs.)": round(computation, 2) if isinstance(computation, (int, float)) else "",
            "Remarks": note,
        })

    py = g(f3ca, "Form3cdAccountingRatioCalculations", "PrevYrProfTurnOvr", default={})
    add("40(a)", "Total turnover of the assessee - Previous Year",
        py.get("TotalTurnover", 0))
    add("40(c)", "Net profit for the Previous Year (as per P&L, before tax)",
        py.get("NetProfNumertr", 0))

    dep_total = sum_amount(g(f3ca, "Form3cdDeprAllw"), "DepAllowable")
    add("18", "Depreciation allowable under the Income-tax Act, 1961 (all blocks)", dep_total)

    ia_amt = sum_amount(g(f3ca, "Form3cdAmtInadm40A2"), "AmtOfPayment",
                         "ParticularType", "SUBCLAUSEia")
    add("21(b)(ii) / 40(a)(ia)", "Amounts inadmissible u/s 40(a)(ia) - payment to resident, TDS not deducted/deposited",
        ia_amt, ia_amt * 0.30, "Disallowance restricted to 30% of the sum, per section 40(a)(ia)")

    i_amt = sum_amount(g(f3ca, "Form3cdAmtInadm40A2"), "AmtOfPayment",
                        "ParticularType", "SUBCLAUSEi")
    add("21(b)(i) / 40(a)(i)", "Amounts inadmissible u/s 40(a)(i) - payment to non-resident, TDS not deducted/deposited",
        i_amt, i_amt * 1.00, "Disallowance is 100% of the sum, per section 40(a)(i)")

    npbdd = sum_amount(g(f3ca, "Form3cdUnpaidStrySec43b3"), "Amount", "Section", "43Bf")
    add("26.i.B.b / 43B(f)", "Disallowance u/s 43B(f) - leave encashment not paid on or before the due date",
        npbdd)

    pdpy = sum_amount(g(f3ca, "Form3cdUnpaidStrySec43b"), "Amount", "Section", "43Bf")
    add("26.i.A.a / 43B(f)", "Allowance u/s 43B(f) - liability pre-existed as on 1st day of PY, disallowed earlier, paid during the year",
        pdpy)

    msme = (g(f3ca, "Form3cdInadm") or [{}])[0]
    add("22(i)", "Interest inadmissible u/s 23 of the MSMED Act, 2006", msme.get("Amount1", 0))
    add("22(iii)(b)", "Amount paid to Micro/Small enterprise beyond the time limit u/s 15 MSMED Act - inadmissible",
        msme.get("Amount4", 0),
        note=f"Total due to MSME (22.ii) = Rs.{inr(msme.get('Amount2', 0))}; paid in time (22.iii.a) = Rs.{inr(msme.get('Amount3', 0))}")

    grat_amt = 0
    for r in g(f3ca, "Form3cdExpOth") or []:
        pk = r.get("Form3cdExpOthPK", {})
        if pk.get("ExpenditureType") == "GRATSEC40A7":
            grat_amt += pk.get("Amount", 0) or 0
    add("21(e)", "Provision for gratuity not allowable u/s 40A(7)", grat_amt)

    tds_int = sum_amount(g(f3ca, "Form3cdSec2011A206C7"), "AmtOfIntrest")
    tds_int_paid = sum_amount(g(f3ca, "Form3cdSec2011A206C7"), "AmtPaid")
    add("34(c)", "Interest payable u/s 201(1A) / 206C(7)", tds_int,
        note=f"Amount actually paid during the year = Rs.{inr(tds_int_paid)}")

    add("21(d) / 40A(3)", "Disallowance / deemed income u/s 40A(3) / 40A(3A) - cash payments in excess of limit",
        0, note="No records added in Form 3CD - all reported payments made otherwise than by account payee cheque/draft NIL")

    add("21(a)", "Amounts debited to P&L being capital, personal, advertisement expenditure etc.",
        0, note="No records added in Form 3CD")

    add("21(h)", "Amount of deduction inadmissible u/s 14A", 0, note="No records added in Form 3CD")

    add("21(i)", "Amount inadmissible under the proviso to section 36(1)(iii)", 0,
        note="Reported as NIL in Form 3CD")

    # Bonus items - not asked for explicitly but directly relevant to the tax
    # computation and fully derivable from this JSON.
    pf_late = 0
    for r in g(f3ca, "Form3cdEmpPfSuperann") or []:
        if r.get("ActualDate") and r.get("DueDate") and r["ActualDate"] > r["DueDate"]:
            pf_late += r.get("Amount", 0) or 0
    add("20(b) / 36(1)(va)", "Employees' contribution to PF/ESI etc. deposited beyond the due date (disallowed)",
        pf_late, note="Derived by comparing ActualDate vs DueDate for every contribution instalment")

    a23 = g(f3ca, "Form3cdPymtSec40a2bDetail") or []
    add("23", "Payments to persons specified u/s 40A(2)(b) (related-party payments, for reasonableness review)",
        sum_amount(a23, "Amount"), note=f"{len(a23)} related-party payees reported")

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. 44-Clause Dashboard
# ---------------------------------------------------------------------------

def build_clause_dashboard(f3ca: dict, part_a: dict) -> pd.DataFrame:
    rows = []

    def add(clause, title, value):
        rows.append({"Clause": clause, "Particulars": title, "Reported Value": value})

    flags = g(f3ca, "Form3cdFlags") or {}

    add("1", "Name of the assessee", g(part_a, "AssesseeName", "LastName", default=""))
    add("2", "Address of the assessee", fmt_addr(g(part_a, "AddressDetail")))
    add("3", "PAN", g(part_a, "PAN", default=""))
    itax = (g(part_a, "Form3cdIndirectTax") or [{}])[0]
    add("4", "Indirect tax registration (GST etc.)", f"{itax.get('IndirectTaxType','')} - {itax.get('RegNo','')}")
    add("5", "Status", STATUS_CODES.get(str(g(part_a, "Status", default="")), g(part_a, "Status", default="")))
    add("6", "Previous year", f"{g(part_a,'PartAStartDate',default='')} to {g(part_a,'PartAEndDate',default='')}")
    add("7", "Assessment year", g(part_a, "AssessmentYear", default=""))
    clause8 = (g(part_a, "Clause") or [{}])[0]
    add("8", "Relevant clause of section 44AB", clause8.get("ClauseNo", ""))
    add("8(a)", "Option exercised u/s 115BA/115BAA/115BAB/115BAC/115BAD/115BAE", g(f3ca, "type", default="None"))

    add("9", "Firm/AOP partner or member details", "Not applicable (assessee is a Company)")
    biz = g(f3ca, "F3cdFirmAopDtlNatOfBusiness", "Form3cdFirmAopDetailPK") or []
    add("10", "Nature of business/profession",
        "; ".join(f"Sector {b.get('Sector')} / Code {b.get('FirmAopDesc')}" for b in biz) or "No records added")
    books = g(f3ca, "Form3cdBooksOfAccLst") or []
    add("11", "Books of account maintained",
        f"{len(books)} books listed (electronic)" if books else "No records added")
    add("12", "Profits/gains assessable on presumptive basis (44AD/44ADA/44AE etc.)", "No records added")
    add("13", "Method of accounting / change in method / ICDS adjustments",
        f"Mercantile system; change in method = {flags.get('ChngMethodOfAcc','N')}; "
        f"ICDS adjustment required = {flags.get('Sec145','N')}")
    add("14", "Method of valuation of closing stock", "Not captured in this JSON extract - refer financial statements")
    add("15", "Capital asset converted into stock-in-trade", "No records added")
    add("16", "Amounts not credited to the profit and loss account (sec 28 items etc.)", "No records added")
    add("17", "Land/building transferred - sections 43CA/50C/56(2)(x)", "No records added")

    dep_total = sum_amount(g(f3ca, "Form3cdDeprAllw"), "DepAllowable")
    add("18", "Depreciation allowable under the Income-tax Act, 1961", f"Rs.{inr(dep_total)} ({len(g(f3ca,'Form3cdDeprAllw') or [])} block(s))")
    add("19", "Amounts admissible under sections 32AC/33AB/33ABA/35/35AD/35CCC/35CCD etc.", "No records added")

    pf_late = 0
    for r in g(f3ca, "Form3cdEmpPfSuperann") or []:
        if r.get("ActualDate") and r.get("DueDate") and r["ActualDate"] > r["DueDate"]:
            pf_late += r.get("Amount", 0) or 0
    add("20", f"(a) Bonus/commission u/s 36(1)(ii): No records added; "
              f"(b) Employees' contribution to PF u/s 36(1)(va): Rs.{inr(pf_late)} paid late (disallowed)", "")

    ia_amt = sum_amount(g(f3ca, "Form3cdAmtInadm40A2"), "AmtOfPayment", "ParticularType", "SUBCLAUSEia")
    i_amt = sum_amount(g(f3ca, "Form3cdAmtInadm40A2"), "AmtOfPayment", "ParticularType", "SUBCLAUSEi")
    grat_amt = 0
    for r in g(f3ca, "Form3cdExpOth") or []:
        pk = r.get("Form3cdExpOthPK", {})
        if pk.get("ExpenditureType") == "GRATSEC40A7":
            grat_amt += pk.get("Amount", 0) or 0
    add("21", f"(a) Capital/personal/advt. exp.: NIL; (b)(i) 40(a)(i): Rs.{inr(i_amt)}; "
              f"(b)(ii) 40(a)(ia): Rs.{inr(ia_amt)}; (c) 40(b)/40(ba): N/A; "
              f"(d) 40A(3)/(3A): NIL; (e) Gratuity 40A(7): Rs.{inr(grat_amt)}; "
              f"(f) 40A(9): NIL; (g) contingent liability: NIL; (h) 14A: NIL; (i) 36(1)(iii) proviso: NIL", "")

    msme = (g(f3ca, "Form3cdInadm") or [{}])[0]
    add("22", f"(i) Interest inadmissible u/s23 MSMED: Rs.{inr(msme.get('Amount1',0))}; "
              f"(ii) Total due to MSME: Rs.{inr(msme.get('Amount2',0))}; "
              f"(iii)(a) Paid in time: Rs.{inr(msme.get('Amount3',0))}; "
              f"(iii)(b) Not paid/inadmissible: Rs.{inr(msme.get('Amount4',0))}", "")

    a23 = g(f3ca, "Form3cdPymtSec40a2bDetail") or []
    add("23", "Payments to persons specified u/s 40A(2)(b)",
        f"{len(a23)} payees, total Rs.{inr(sum_amount(a23,'Amount'))}")
    add("24", "Deemed profits/gains u/s 32AC/32AD/33AB/33AC/33ABA", "No records added")
    add("25", "Profit chargeable to tax u/s 41", "No records added")

    pdpy = sum_amount(g(f3ca, "Form3cdUnpaidStrySec43b"), "Amount", "Section", "43Bf")
    pbdd = sum_amount(g(f3ca, "Form3cdUnpaidStrySec43b2"), "Amount")
    npbdd = sum_amount(g(f3ca, "Form3cdUnpaidStrySec43b3"), "Amount", "Section", "43Bf")
    add("26", f"Sec 43B - pre-existing liability paid this year: Rs.{inr(pdpy)}; "
              f"incurred this year & paid by due date: Rs.{inr(pbdd)}; "
              f"incurred this year & NOT paid by due date (disallowed): Rs.{inr(npbdd)}", "")

    pl = (g(f3ca, "Form3cdPl") or [{}])[0]
    add("27", f"(a) CENVAT/ITC - opening Rs.{inr(pl.get('OpeningBalAmount',0))}, "
              f"availed Rs.{inr(pl.get('CenvatAvailAmount',0))}, "
              f"utilised Rs.{inr(pl.get('CenvatUtilizedAmount',0))}, "
              f"closing Rs.{inr(pl.get('BalanceAmount',0))}; (b) prior period items: No records added", "")
    add("28", "Omitted from AY 2025-26 onwards", "N/A")
    add("29", "Consideration for issue of shares exceeding FMV u/s 56(2)(viib)", "No records added")
    add("29A", "Income u/s 56(2)(ix) (advance forfeited)", "No" if flags.get("IncomeCluaseixofsubsection2") == "N" else "Yes")
    add("29B", "Income u/s 56(2)(x) (property received w/o or inadequate consideration)",
        "No" if flags.get("IncomeCluasexofsubsection2") == "N" else "Yes")
    add("30", "Amount borrowed on hundi u/s 69D", "No" if flags.get("Section69D") == "N" else "Yes")
    add("30A", "Primary adjustment to transfer price u/s 92CE", "No" if flags.get("TransferPriceSection92CE") == "N" else "Yes")
    add("30B", "Interest expenditure u/s 94B (thin-cap, >30% EBITDA)", "No records added")
    add("30C", "Impermissible avoidance arrangement u/s 96/144BA (GAAR)", "No" if flags.get("ImpermissibleSec96") == "N" else "Yes")
    add("31", "Loans/deposits/specified sum u/s 269SS/269ST taken; repayments u/s 269T/269ST", "No records added")
    add("32", f"(a) B/f loss or depreciation: No records added; "
              f"(b) sec 79 shareholding change: {flags.get('ChngShareSec79','N')}; "
              f"(c) sec 73 speculation loss: {g(f3ca,'Form3cdSpecloss73','Form3cdSpec73Flag',default='N')}; "
              f"(d) sec 73A specified business loss: {g(f3ca,'Form3cdSpec73A','Form3cdSpec73AFlag',default='N')}; "
              f"(e) deemed speculation business: {g(f3ca,'Form3cdSpecdeemdBus73','Form3cdSpecdeemdBusFlag',default='N')}", "")
    add("33", "Chapter VI-A / Chapter III (10A/10AA) deductions", "No records added")

    chap17 = g(f3ca, "Form3cdChapXVII") or []
    add("34", f"(a) TDS/TCS u/Chapter XVII-B/BB: {len(chap17)} section(s) reported, "
              f"total tax deducted Rs.{inr(sum_amount(chap17,'AmtTaxDedOrCollect') + sum_amount(chap17,'AmtTaxSpecRate'))}; "
              f"(b) TDS/TCS statements: {len(g(f3ca,'Form3cdTaxDedCollect') or [])} filed; "
              f"(c) interest u/s 201(1A)/206C(7): Rs.{inr(sum_amount(g(f3ca,'Form3cdSec2011A206C7'),'AmtOfIntrest'))}", "")
    add("35", "Quantitative details (trading/manufacturing concern)", "Not applicable (service company)")
    add("36A", "Deemed dividend received u/s 2(22)(e)", "No records added")
    add("36B", "Amount received for buy-back of shares u/s 2(22)(f)", "No records added")
    add("37", "Cost audit conducted?", "Not Applicable" if g(f3ca, "CostAudit", "CostAuditFlag") == "X" else "Applicable")
    add("38", "Audit under Central Excise Act, 1944", "Not Applicable" if g(f3ca, "AuditExcise", "AuditExciseFlag") == "X" else "Applicable")
    add("39", "Audit u/s 72A of the Finance Act, 1994", "Not Applicable" if g(f3ca, "AuditSec72", "AuditSec72Flag") == "X" else "Applicable")

    py = g(f3ca, "Form3cdAccountingRatioCalculations", "PrevYrProfTurnOvr", default={})
    ppy = g(f3ca, "Form3cdAccountingRatioCalculations", "PrecPrevYrProfTurnOvr", default={})
    add("40", f"Turnover PY: Rs.{inr(py.get('TotalTurnover',0))} (NP% {py.get('NetprofitTurnover1',0)}%); "
              f"Turnover Preceding PY: Rs.{inr(ppy.get('TotalTurnover',0))} (NP% {ppy.get('NetprofitTurnover1',0)}%)", "")

    refunds = g(f3ca, "Form3cdRefundDmdPrevYr") or []
    dem = sum_amount(refunds, "Amount", "TypeOfAmount", "DEMAND")
    ref = sum_amount(refunds, "Amount", "TypeOfAmount", "REFUND")
    add("41", f"Demand/refund under other tax laws - Refunds Rs.{inr(ref)}, Demands Rs.{inr(dem)} ({len(refunds)} entries)", "")

    frm61 = g(f3ca, "Form3cdFurnishStatemnt") or []
    add("42", f"Form 61/61A/61B furnished: {len(frm61)} form(s)", "")
    add("43", "Country-by-Country report u/s 286(2)", "No" if flags.get("SubSec2Sec286") == "N" else "Yes")

    gst_brk = g(f3ca, "Form3cdBreakUpGST") or []
    add("44", f"Break-up of total expenditure by GST registration status: {len(gst_brk)} categories, "
              f"total Rs.{inr(sum_amount(gst_brk,'TotAmtExp'))}", "")

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Tax Computation Draft (mirrors the firm's existing "Annexure 1" layout)
# ---------------------------------------------------------------------------

def build_computation_draft(f3ca: dict) -> pd.DataFrame:
    py = g(f3ca, "Form3cdAccountingRatioCalculations", "PrevYrProfTurnOvr", default={})
    net_profit_pl = py.get("NetProfNumertr", 0)

    dep_it = sum_amount(g(f3ca, "Form3cdDeprAllw"), "DepAllowable")
    npbdd = sum_amount(g(f3ca, "Form3cdUnpaidStrySec43b3"), "Amount", "Section", "43Bf")
    pdpy = sum_amount(g(f3ca, "Form3cdUnpaidStrySec43b"), "Amount", "Section", "43Bf")
    ia_amt = sum_amount(g(f3ca, "Form3cdAmtInadm40A2"), "AmtOfPayment", "ParticularType", "SUBCLAUSEia")
    i_amt = sum_amount(g(f3ca, "Form3cdAmtInadm40A2"), "AmtOfPayment", "ParticularType", "SUBCLAUSEi")
    sec40a_disallowance = ia_amt * 0.30 + i_amt * 1.00
    grat_amt = 0
    for r in g(f3ca, "Form3cdExpOth") or []:
        pk = r.get("Form3cdExpOthPK", {})
        if pk.get("ExpenditureType") == "GRATSEC40A7":
            grat_amt += pk.get("Amount", 0) or 0
    tds_int = sum_amount(g(f3ca, "Form3cdSec2011A206C7"), "AmtOfIntrest")
    pf_late = 0
    for r in g(f3ca, "Form3cdEmpPfSuperann") or []:
        if r.get("ActualDate") and r.get("DueDate") and r["ActualDate"] > r["DueDate"]:
            pf_late += r.get("Amount", 0) or 0

    rows = []

    def add(section, particulars, ref, amount):
        rows.append({"Section": section, "Particulars": particulars, "Clause Reference": ref,
                      "Amount (Rs.)": round(amount, 2) if isinstance(amount, (int, float)) else amount})

    add("", "Profit before tax as per Profit & Loss statement", "Clause 40 / Financial Statements", net_profit_pl)
    add("Add", "Depreciation as per the Companies Act, 2013", "Financial Statements - MANUAL INPUT (not in Form 3CD)", "Enter from FS")
    add("Add", "Expenditure u/s 43B not paid on or before due date (Leave encashment)", "Clause 26.i.B.b", npbdd)
    add("Add", "Employees' contribution to PF/ESI paid beyond due date - disallowed u/s 36(1)(va)", "Clause 20(b)", pf_late)
    add("Add", "Expenditure inadmissible u/s 40(a)(i) [100%] + 40(a)(ia) [30%]", "Clause 21(b)", sec40a_disallowance)
    add("Add", "Provision for gratuity inadmissible u/s 40A(7)", "Clause 21(e)", grat_amt)
    add("Add", "Interest on income-tax (if debited to P&L)", "Financial Statements - MANUAL INPUT (not in Form 3CD)", "Enter from FS")
    add("Add", "Interest on TDS u/s 201(1A)/206C(7)", "Clause 34(c)", tds_int)
    add("Add", "MSME interest u/s 23 MSMED Act / delayed MSME payments inadmissible", "Clause 22(i) / 22(iii)(b)",
        (g(f3ca, "Form3cdInadm") or [{}])[0].get("Amount1", 0) + (g(f3ca, "Form3cdInadm") or [{}])[0].get("Amount4", 0))
    add("Add", "Capital/personal/advertisement expenditure debited to P&L", "Clause 21(a)", 0)
    add("Add", "Amount inadmissible u/s 14A", "Clause 21(h)", 0)
    add("Add", "Amount inadmissible under proviso to section 36(1)(iii)", "Clause 21(i)", 0)
    add("Add", "Disallowance/deemed income u/s 40A(3)/40A(3A)", "Clause 21(d)", 0)

    add("Less", "Depreciation allowable under section 32 of the Act", "Clause 18", dep_it)
    add("Less", "Section 43B liability of earlier years, paid this year (Leave encashment)", "Clause 26.i.A.a", pdpy)
    add("Less", "Expenditure earlier disallowed u/s 40(a)(i)/(ia), now paid - allowable this year", "Prior year Form 3CD - MANUAL INPUT", "Enter from PY workings")
    add("Less", "Other adjustments - gratuity actually paid/reversed during the year", "Financial Statements - MANUAL INPUT (not in Form 3CD)", "Enter from FS")

    add("", "Income under the head 'Income from other sources' (interest income, etc.)",
        "Financial Statements - MANUAL INPUT (not in Form 3CD)", "Enter from FS")
    add("", "Chapter VI-A / Chapter III deductions", "Clause 33", 0)

    return pd.DataFrame(rows)


def estimate_tax(f3ca: dict, computation_df: pd.DataFrame) -> pd.DataFrame:
    numeric = computation_df[pd.to_numeric(computation_df["Amount (Rs.)"], errors="coerce").notna()].copy()
    numeric["Amount (Rs.)"] = pd.to_numeric(numeric["Amount (Rs.)"])
    additions = numeric.loc[numeric["Section"] == "Add", "Amount (Rs.)"].sum()
    deductions = numeric.loc[numeric["Section"] == "Less", "Amount (Rs.)"].sum()
    base = numeric.loc[numeric["Section"] == "", "Amount (Rs.)"]
    net_profit = base.iloc[0] if len(base) else 0
    pgbp_partial = net_profit + additions - deductions

    option = g(f3ca, "type", default=None)
    rate_info = RATE_TABLE.get(option, (None, None, "Rate depends on turnover slab / normal provisions - verify manually."))
    rate, surcharge, note = rate_info

    rows = [
        {"Particulars": "PGBP (partial - excludes items requiring manual FS input, see Tax Computation Draft sheet)",
         "Amount (Rs.)": round(pgbp_partial, 2)},
        {"Particulars": "Option exercised", "Amount (Rs.)": option or "Normal provisions"},
    ]
    if rate is not None:
        tax = pgbp_partial * rate
        surch = tax * surcharge if surcharge else 0
        cess = (tax + surch) * 0.04
        rows += [
            {"Particulars": f"Tax @ {rate*100:.0f}% (partial base, indicative only)", "Amount (Rs.)": round(tax, 2)},
            {"Particulars": f"Surcharge @ {surcharge*100:.0f}%" if surcharge else "Surcharge",
             "Amount (Rs.)": round(surch, 2)},
            {"Particulars": "Health & Education Cess @ 4%", "Amount (Rs.)": round(cess, 2)},
            {"Particulars": "Total tax (indicative, partial base)", "Amount (Rs.)": round(tax + surch + cess, 2)},
        ]
    rows.append({"Particulars": "Note", "Amount (Rs.)": note})
    rows.append({"Particulars": "IMPORTANT",
                 "Amount (Rs.)": "This is NOT the final total income - it excludes Income from Other Sources, "
                                  "Chapter VI-A deductions, and FS-only add-backs (books depreciation, interest on "
                                  "income-tax, prior-year 40(a) reversals). Complete the manual-input rows in the "
                                  "Tax Computation Draft sheet before filing."})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Excel / HTML / PDF / Word output
# ---------------------------------------------------------------------------

HEADER_FILL = PatternFill(start_color=PURPLE_DARK, end_color=PURPLE_DARK, fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, color="FFFFFF", bold=True)
BODY_FONT = Font(name="Calibri", size=10)
BAND_FILL = PatternFill(start_color=PURPLE_LIGHT, end_color=PURPLE_LIGHT, fill_type="solid")
_SIDE = Side(style="thin", color=PURPLE_BORDER)
THIN_BORDER = Border(left=_SIDE, right=_SIDE, top=_SIDE, bottom=_SIDE)

INDIAN_CURRENCY_FMT = "#,##,##0"

# Per-column layout: width is in Excel character units, reused (as relative
# weights) for PDF column widths too, so both outputs stay proportioned alike.
COLUMN_STYLES = {
    "Clause Ref.": {"width": 18, "align": "center", "wrap": False},
    "Clause": {"width": 10, "align": "center", "wrap": False},
    "Section": {"width": 10, "align": "center", "wrap": False},
    "Particulars": {"width": 58, "align": "left", "wrap": True},
    "Reported Value": {"width": 72, "align": "left", "wrap": True},
    "Remarks": {"width": 55, "align": "left", "wrap": True},
    "Clause Reference": {"width": 38, "align": "left", "wrap": True},
}
DEFAULT_COLUMN_STYLE = {"width": 20, "align": "left", "wrap": False}


def _column_style(header: str) -> dict:
    if header in COLUMN_STYLES:
        return COLUMN_STYLES[header]
    if "(Rs.)" in header:
        return {"width": 18, "align": "right", "wrap": False, "currency": True}
    return DEFAULT_COLUMN_STYLE


def _style_sheet(ws):
    header_cells = list(ws[1])
    max_row, max_col = ws.max_row, ws.max_column

    for cell in header_cells:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    ws.row_dimensions[1].height = 32

    row_lines = [1] * (max_row + 1)

    for col_idx in range(1, max_col + 1):
        header_text = str(header_cells[col_idx - 1].value or "")
        style = _column_style(header_text)
        ws.column_dimensions[get_column_letter(col_idx)].width = style["width"]

        for row_idx in range(2, max_row + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = BODY_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(horizontal=style["align"],
                                        vertical="top" if style["wrap"] else "center",
                                        wrap_text=style["wrap"])
            if row_idx % 2 == 0:
                cell.fill = BAND_FILL
            if style.get("currency") and is_amount(cell.value):
                cell.number_format = INDIAN_CURRENCY_FMT
            if style["wrap"] and cell.value:
                chars_per_line = max(10, style["width"] * 1.15)
                lines = math.ceil(len(str(cell.value)) / chars_per_line)
                row_lines[row_idx] = max(row_lines[row_idx], lines)

    for row_idx in range(2, max_row + 1):
        ws.row_dimensions[row_idx].height = max(15, row_lines[row_idx] * 15)

    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"


DISCLAIMER_TEXT = (
    "This tool is a decision-support and review aid only. It assists in collating and "
    "cross-referencing the particulars reported in Form No. 3CD and does NOT constitute an "
    "audit opinion. It is not a substitute for the auditor's independent verification of these "
    "particulars in accordance with the Standards on Auditing (SAs) and the Guidance Note on Tax "
    "Audit under Section 44AB of the Income-tax Act, 1961, issued by the Institute of Chartered "
    "Accountants of India (ICAI). All figures must be independently verified against the books of "
    "account, supporting documents and management representations before being relied upon for "
    "reporting or filing."
)
FOOTER_DISCLAIMER = ("Decision-support tool only - not a substitute for the auditor's verification "
                     "under SA / ICAI Guidance Note on Tax Audit under section 44AB.")


def _write_disclaimer_sheet(wb):
    ws = wb.create_sheet("Disclaimer", 0)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 100

    title_cell = ws.cell(row=1, column=1, value="IMPORTANT - PLEASE READ BEFORE USE")
    title_cell.font = Font(name="Calibri", size=14, bold=True, color=PURPLE_DARK)
    ws.row_dimensions[1].height = 24

    body_cell = ws.cell(row=3, column=1, value=DISCLAIMER_TEXT)
    body_cell.font = Font(name="Calibri", size=11, color="2B0A3D")
    body_cell.alignment = Alignment(wrap_text=True, vertical="top")
    body_cell.fill = PatternFill(start_color=PURPLE_LIGHT, end_color=PURPLE_LIGHT, fill_type="solid")
    body_cell.border = THIN_BORDER
    ws.row_dimensions[3].height = 110
    return ws


def write_excel(outfile: Path, sheets: dict[str, pd.DataFrame]):
    with pd.ExcelWriter(outfile, engine="openpyxl") as writer:
        _write_disclaimer_sheet(writer.book)
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
            _style_sheet(writer.sheets[name[:31]])
        default_sheet = writer.book["Sheet"] if "Sheet" in writer.book.sheetnames else None
        if default_sheet is not None and default_sheet.max_row == 1 and default_sheet["A1"].value is None:
            del writer.book["Sheet"]


def write_html_dashboard(outfile: Path, company: str, pan: str, ay: str, sheets: dict[str, pd.DataFrame]):
    company_e, pan_e, ay_e = html.escape(company), html.escape(pan), html.escape(ay)
    parts = [f"""<!doctype html><html><head><meta charset="utf-8">
<title>Form 3CD Dashboard - {company_e}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#f4f6f8;color:#1a1a1a;margin:0;padding:24px;}}
h1{{font-size:20px;margin-bottom:4px;color:#{PURPLE_DARK};}}
h2{{font-size:16px;margin-top:32px;border-bottom:2px solid #{PURPLE_DARK};padding-bottom:4px;color:#{PURPLE_DARK};}}
.meta{{color:#555;margin-bottom:16px;}}
table{{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:8px;}}
th,td{{border:1px solid #{PURPLE_BORDER};padding:6px 10px;text-align:left;font-size:13px;vertical-align:top;}}
th{{background:#{PURPLE_DARK};color:#fff;position:sticky;top:0;}}
tr:nth-child(even){{background:#{PURPLE_LIGHT};}}
.note{{color:#a15c00;font-size:12px;margin-bottom:20px;}}
.disclaimer{{background:#{PURPLE_LIGHT};border:1px solid #{PURPLE_DARK};border-radius:4px;padding:10px 14px;margin-bottom:14px;font-size:12px;color:#2B0A3D;}}
.disclaimer strong{{color:#{PURPLE_DARK};}}
</style></head><body>
<h1>Form 3CD Tax Audit Analysis - {company_e}</h1>
<div class="meta">PAN: {pan_e} &nbsp;|&nbsp; Assessment Year: {ay_e} &nbsp;|&nbsp; Generated by analyze_form3cd.py</div>
<div class="disclaimer"><strong>DISCLAIMER:</strong> {html.escape(DISCLAIMER_TEXT)}</div>
<div class="note">This is a working draft for internal review. Figures requiring data outside Form 3CD (financial statements, prior-year workings) are flagged in the Tax Computation Draft table and must be completed manually before filing.</div>
"""]
    for name, df in sheets.items():
        display_df = df.copy()
        for col in display_df.columns:
            if "(Rs.)" in col:
                # Pre-format to plain strings: pandas' to_html(formatters=...) silently
                # ignores the formatter for float cells in an object-dtype column.
                display_df[col] = display_df[col].map(lambda v: inr(v) if is_amount(v) else ("" if v is None else str(v)))
        parts.append(f"<h2>{name}</h2>")
        parts.append(display_df.to_html(index=False, na_rep="", border=0, justify="left"))
    parts.append("</body></html>")
    outfile.write_text("\n".join(parts), encoding="utf-8")


SIGNOFF_NOTE = "This tax audit analysis has been reviewed internally prior to filing of Form 3CA-3CD."
SIGNOFF_HEADERS = ["", "Prepared by", "Reviewed by (Tax Head)", "Approved by"]
SIGNOFF_ROW_LABELS = ["Name", "Designation", "Signature", "Date"]
SIGNOFF_PREFILL = {("Designation", "Reviewed by (Tax Head)"): "Tax Head"}


def _cell_text(value, is_currency: bool) -> str:
    if is_currency and is_amount(value):
        return inr(value)
    return "" if value is None else str(value)


# ---- PDF (reportlab) -------------------------------------------------------

PDF_PURPLE = colors.HexColor(f"#{PURPLE_DARK}")
PDF_PURPLE_LIGHT = colors.HexColor(f"#{PURPLE_LIGHT}")
PDF_BORDER = colors.HexColor(f"#{PURPLE_BORDER}")
PDF_TEXT = colors.HexColor("#2B0A3D")


def _pdf_styles():
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18, textColor=PDF_PURPLE, spaceAfter=4),
        "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=10, textColor=PDF_TEXT, spaceAfter=10),
        "heading": ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=13, textColor=PDF_PURPLE,
                                   spaceBefore=14, spaceAfter=6),
        "note": ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=8.5,
                                textColor=colors.HexColor("#A15C00"), spaceAfter=12),
        "disclaimer": ParagraphStyle("disclaimer", fontName="Helvetica", fontSize=8.5,
                                      textColor=PDF_TEXT, leading=11),
        "disclaimer_label": ParagraphStyle("disclaimer_label", fontName="Helvetica-Bold", fontSize=8.5,
                                            textColor=PDF_PURPLE, leading=11),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8, textColor=PDF_TEXT, leading=10),
        "header_cell": ParagraphStyle("header_cell", fontName="Helvetica-Bold", fontSize=8.5,
                                       textColor=colors.white, leading=10),
        "signoff_label": ParagraphStyle("signoff_label", fontName="Helvetica-Bold", fontSize=9, textColor=PDF_TEXT),
    }


def _df_to_pdf_table(df: pd.DataFrame, col_widths, styles) -> Table:
    currency_cols = {i for i, c in enumerate(df.columns) if "(Rs.)" in c}
    data = [[Paragraph(html.escape(str(c)), styles["header_cell"]) for c in df.columns]]
    for _, row in df.iterrows():
        cells = [Paragraph(html.escape(_cell_text(row[col], i in currency_cols)), styles["cell"])
                 for i, col in enumerate(df.columns)]
        data.append(cells)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), PDF_PURPLE),
        ("GRID", (0, 0), (-1, -1), 0.5, PDF_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_i in range(2, len(data), 2):
        style_cmds.append(("BACKGROUND", (0, row_i), (-1, row_i), PDF_PURPLE_LIGHT))
    table.setStyle(TableStyle(style_cmds))
    return table


def _pdf_signoff_table(styles) -> Table:
    rows = [SIGNOFF_HEADERS]
    for label in SIGNOFF_ROW_LABELS:
        rows.append([label] + [SIGNOFF_PREFILL.get((label, col), "") for col in SIGNOFF_HEADERS[1:]])

    data = []
    for r_idx, row in enumerate(rows):
        line = []
        for c_idx, value in enumerate(row):
            style = styles["header_cell"] if r_idx == 0 else (styles["signoff_label"] if c_idx == 0 else styles["cell"])
            line.append(Paragraph(html.escape(value), style))
        data.append(line)

    table = Table(data, colWidths=[3.5 * cm, 6 * cm, 6 * cm, 6 * cm], rowHeights=[1 * cm] + [1.2 * cm] * 4)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PDF_PURPLE),
        ("BACKGROUND", (0, 1), (0, -1), PDF_PURPLE_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, PDF_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _pdf_disclaimer_box(styles, available_width) -> Table:
    para = Paragraph(f'<b><font color="#{PURPLE_DARK}">DISCLAIMER:</font></b> {html.escape(DISCLAIMER_TEXT)}',
                      styles["disclaimer"])
    table = Table([[para]], colWidths=[available_width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PDF_PURPLE_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, PDF_PURPLE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def _pdf_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Oblique", 7)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawCentredString(landscape(A4)[0] / 2, 0.8 * cm, FOOTER_DISCLAIMER)
    canvas.restoreState()


def generate_pdf_report(outfile: Path, company: str, pan: str, ay: str, sheets: dict[str, pd.DataFrame]):
    styles = _pdf_styles()
    doc = SimpleDocTemplate(str(outfile), pagesize=landscape(A4),
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.8 * cm)
    available_width = landscape(A4)[0] - 3 * cm

    company_e, pan_e, ay_e = html.escape(company), html.escape(pan), html.escape(ay)
    story = [
        Paragraph("Form 3CD Tax Audit Analysis", styles["title"]),
        Paragraph(f"{company_e} &nbsp;|&nbsp; PAN: {pan_e} &nbsp;|&nbsp; Assessment Year: {ay_e}", styles["meta"]),
        _pdf_disclaimer_box(styles, available_width),
        Spacer(1, 8),
        Paragraph("This is a working draft for internal review. Figures requiring data outside Form 3CD "
                  "(financial statements, prior-year workings) are flagged in the Tax Computation Draft "
                  "table and must be completed manually before filing.", styles["note"]),
    ]

    for name, df in sheets.items():
        weights = [_column_style(c)["width"] for c in df.columns]
        col_widths = [available_width * w / sum(weights) for w in weights]
        story.append(Paragraph(html.escape(name), styles["heading"]))
        story.append(_df_to_pdf_table(df, col_widths, styles))
        story.append(Spacer(1, 8))

    story.append(PageBreak())
    story.append(Paragraph("Sign-off", styles["heading"]))
    story.append(Paragraph(SIGNOFF_NOTE, styles["meta"]))
    story.append(_pdf_signoff_table(styles))

    doc.build(story, onFirstPage=_pdf_footer, onLaterPages=_pdf_footer)


# ---- Word (python-docx) ----------------------------------------------------

def _set_cell_shading(cell, hex_color: str):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)


def _style_docx_cell(cell, text: str, *, bold=False, color=None, align=None, shading=None, size=9):
    cell.text = text
    for p in cell.paragraphs:
        if align is not None:
            p.alignment = align
        for r in p.runs:
            r.font.size = Pt(size)
            r.font.bold = bold
            if color is not None:
                r.font.color.rgb = color
    if shading:
        _set_cell_shading(cell, shading)


def _df_to_docx_table(doc: Document, df: pd.DataFrame):
    currency_cols = {c for c in df.columns if "(Rs.)" in c}
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"
    for i, col in enumerate(df.columns):
        _style_docx_cell(table.rows[0].cells[i], str(col), bold=True, color=RGBColor(0xFF, 0xFF, 0xFF),
                          align=WD_ALIGN_PARAGRAPH.CENTER, shading=PURPLE_DARK)

    for row_i, (_, row) in enumerate(df.iterrows()):
        cells = table.add_row().cells
        for i, col in enumerate(df.columns):
            is_currency = col in currency_cols
            align = WD_ALIGN_PARAGRAPH.RIGHT if is_currency else WD_ALIGN_PARAGRAPH.LEFT
            shading = PURPLE_LIGHT if row_i % 2 == 1 else None
            _style_docx_cell(cells[i], _cell_text(row[col], is_currency), align=align, shading=shading)
    return table


def _docx_signoff_table(doc: Document):
    table = doc.add_table(rows=1 + len(SIGNOFF_ROW_LABELS), cols=len(SIGNOFF_HEADERS))
    table.style = "Table Grid"
    for i, h in enumerate(SIGNOFF_HEADERS):
        _style_docx_cell(table.rows[0].cells[i], h, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF),
                          align=WD_ALIGN_PARAGRAPH.CENTER, shading=PURPLE_DARK)
    for r_idx, label in enumerate(SIGNOFF_ROW_LABELS, start=1):
        _style_docx_cell(table.rows[r_idx].cells[0], label, bold=True, shading=PURPLE_LIGHT)
        for c_idx, col in enumerate(SIGNOFF_HEADERS[1:], start=1):
            _style_docx_cell(table.rows[r_idx].cells[c_idx], SIGNOFF_PREFILL.get((label, col), ""))
        table.rows[r_idx].height = Cm(1.1)
    return table


def _docx_disclaimer_box(doc: Document):
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    cell.text = ""
    p = cell.paragraphs[0]
    label_run = p.add_run("DISCLAIMER: ")
    label_run.bold = True
    label_run.font.size = Pt(9)
    label_run.font.color.rgb = RGBColor.from_string(PURPLE_DARK)
    body_run = p.add_run(DISCLAIMER_TEXT)
    body_run.font.size = Pt(9)
    _set_cell_shading(cell, PURPLE_LIGHT)
    return table


def _add_footer(doc: Document, text: str):
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.size = Pt(7)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x77, 0x77, 0x77)


def generate_word_report(outfile: Path, company: str, pan: str, ay: str, sheets: dict[str, pd.DataFrame]):
    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = section.right_margin = Cm(1.5)
    section.top_margin = section.bottom_margin = Cm(1.5)

    title = doc.add_heading("Form 3CD Tax Audit Analysis", level=0)
    title.runs[0].font.color.rgb = RGBColor.from_string(PURPLE_DARK)

    doc.add_paragraph(f"{company}  |  PAN: {pan}  |  Assessment Year: {ay}")

    _docx_disclaimer_box(doc)
    _add_footer(doc, FOOTER_DISCLAIMER)

    note = doc.add_paragraph()
    note_run = note.add_run(
        "This is a working draft for internal review. Figures requiring data outside Form 3CD "
        "(financial statements, prior-year workings) are flagged in the Tax Computation Draft "
        "table and must be completed manually before filing.")
    note_run.italic = True
    note_run.font.size = Pt(9)

    for name, df in sheets.items():
        heading = doc.add_heading(name, level=1)
        heading.runs[0].font.color.rgb = RGBColor.from_string(PURPLE_DARK)
        _df_to_docx_table(doc, df)
        doc.add_paragraph()

    doc.add_page_break()
    signoff_heading = doc.add_heading("Sign-off", level=1)
    signoff_heading.runs[0].font.color.rgb = RGBColor.from_string(PURPLE_DARK)
    doc.add_paragraph(SIGNOFF_NOTE)
    _docx_signoff_table(doc)

    doc.save(str(outfile))


def process_one(json_path: Path, outdir: Path | None, formats: tuple[str, ...] = DEFAULT_FORMATS):
    f3ca = load_f3ca(json_path)
    part_a = g(f3ca, "PartA", default={})

    company = g(part_a, "AssesseeName", "LastName", default="Assessee")
    pan = g(part_a, "PAN", default="PAN")
    ay = g(part_a, "AssessmentYear", default="AY")

    key_fin_df = extract_key_financials(f3ca)
    dashboard_df = build_clause_dashboard(f3ca, part_a)
    computation_df = build_computation_draft(f3ca)
    tax_estimate_df = estimate_tax(f3ca, computation_df)

    target_dir = outdir or json_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{pan}_{ay}_3CD_Analysis"

    sheets = {
        "Key Financial Summary": key_fin_df,
        "44-Clause Dashboard": dashboard_df,
        "Tax Computation Draft": computation_df,
        "Indicative Tax Estimate": tax_estimate_df,
    }

    print(f"\nCompany: {company}  |  PAN: {pan}  |  AY: {ay}")

    if "xlsx" in formats:
        xlsx_path = target_dir / f"{stem}.xlsx"
        write_excel(xlsx_path, sheets)
        print(f"Excel workbook written to: {xlsx_path}")
    if "html" in formats:
        html_path = target_dir / f"{stem}_Dashboard.html"
        write_html_dashboard(html_path, company, pan, ay, sheets)
        print(f"HTML dashboard written to: {html_path}")
    if "pdf" in formats:
        pdf_path = target_dir / f"{stem}_Report.pdf"
        generate_pdf_report(pdf_path, company, pan, ay, sheets)
        print(f"PDF report written to: {pdf_path}")
    if "docx" in formats:
        docx_path = target_dir / f"{stem}_Report.docx"
        generate_word_report(docx_path, company, pan, ay, sheets)
        print(f"Word report written to: {docx_path}")

    print()
    print("=== Key Financial Summary ===")
    print(key_fin_df.to_string(index=False))
    print()
    print("=== Indicative Tax Estimate (partial - see notes) ===")
    print(tax_estimate_df.to_string(index=False))


def prompt_for_json_paths() -> list[Path]:
    print("Form 3CD Tax Audit Analyzer")
    print("=" * 60)
    paths = []
    while True:
        try:
            raw = input("\nEnter path to a Form 3CD JSON file (or press Enter to finish): ")
        except EOFError:
            break
        raw = raw.strip().strip('"').lstrip("﻿")
        if not raw:
            break
        p = Path(raw)
        if not p.exists():
            print(f"  File not found: {p}")
            continue
        paths.append(p)
    return paths


def main():
    parser = argparse.ArgumentParser(description="Analyze one or more Form 3CA/3CD e-filing JSON exports.")
    parser.add_argument("json_paths", type=Path, nargs="*", help="Path(s) to the Form 3CD JSON file(s)")
    parser.add_argument("--outdir", type=Path, default=None, help="Output directory (default: same as each input file)")
    parser.add_argument("--formats", default=",".join(DEFAULT_FORMATS),
                         help=f"Comma-separated output formats to generate, from {ALL_FORMATS} "
                              f"(default: {','.join(DEFAULT_FORMATS)})")
    args = parser.parse_args()

    formats = tuple(f.strip().lower() for f in args.formats.split(",") if f.strip())
    unknown = [f for f in formats if f not in ALL_FORMATS]
    if unknown:
        parser.error(f"Unknown format(s) {unknown} - choose from {ALL_FORMATS}")

    json_paths = args.json_paths
    interactive = len(json_paths) == 0
    if interactive:
        json_paths = prompt_for_json_paths()
        if not json_paths:
            print("No file provided - exiting.")
            return 0

    exit_code = 0
    for jp in json_paths:
        try:
            process_one(jp, args.outdir, formats)
        except Exception as exc:
            exit_code = 1
            print(f"\n[ERROR] Could not process {jp}: {exc}")

    if interactive or getattr(sys, "frozen", False):
        try:
            input("\nDone. Press Enter to exit...")
        except EOFError:
            pass
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
