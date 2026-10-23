"""Disclosure checklist and applicability screens.

Each item is judged from the statements and the books where that is possible (derived), otherwise it is
listed as information a person must obtain (manual), with what to ask for. Nothing is marked complete
unless the draft actually contains it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..format import allowed_units, rs
from ..model import Model

PATH = Path(__file__).with_name("checklist_non_ind_as.json")

# Thresholds, in rupees, as currently notified. Edit here when the law changes.
CRORE = 10_000_000
SMALL_COMPANY_CAPITAL, SMALL_COMPANY_TURNOVER = 4 * CRORE, 40 * CRORE
CARO_NET_WORTH, CARO_BORROWINGS, CARO_REVENUE = 1 * CRORE, 1 * CRORE, 10 * CRORE
IFC_TURNOVER, IFC_BORROWINGS = 50 * CRORE, 25 * CRORE
CSR_NET_WORTH, CSR_TURNOVER, CSR_PROFIT = 500 * CRORE, 1000 * CRORE, 5 * CRORE
TAX_AUDIT_TURNOVER, TAX_AUDIT_TURNOVER_DIGITAL = 1 * CRORE, 10 * CRORE

STATUSES = ["Complete", "Partly provided", "Information required", "Observation", "Applies (likely)",
            "Exempt (likely)", "Not applicable"]


@dataclass
class Item:
    id: str
    area: str
    requirement: str
    ref: str
    status: str
    evidence: str
    ask: str = ""


class _Ctx:
    def __init__(self, m: Model, tieouts):
        self.m, self.tieouts = m, tieouts
        self.mapped = m.mapping
        self.f, self.pl = m.figures, m.figures["pl"]
        live = self.mapped[(self.mapped["opening"].abs() + self.mapped["closing"].abs()) > 0.005]
        self.live = live
        self.lines = set(live["line"])

    def subs(self, line):
        return list(dict.fromkeys(str(s) for s in self.live.loc[self.live["line"] == line, "sub"]))

    def applies(self, token: str) -> bool:
        if token == "always" or token == "csr":
            return True
        if token.startswith("line:"):
            return token[5:] in self.lines
        if token == "borrowings":
            return bool({"NCL.LTB", "CL.STB"} & self.lines)
        if token == "secured_borrowings":
            return any(re.search(r"(?<!un)secured", s, re.I) for l in ("NCL.LTB", "CL.STB") for s in self.subs(l))
        if token == "related_loans_in":
            return any("related part" in s.lower() for s in self.subs("NCL.LTB"))
        if token == "related_loans_out":
            return any("related part" in s.lower() for l in ("CA.STLA", "NCA.LTLA") for s in self.subs(l))
        if token == "related_party":
            return (self.applies("related_loans_in") or self.applies("related_loans_out")
                    or any("directors" in s.lower() for s in self.subs("EXP.EMP")))
        if token == "rent":
            return "Rent" in self.subs("EXP.OTH")
        if token == "ppe_immovable":
            return any(s in ("Land", "Buildings") for s in self.subs("NCA.PPE"))
        if token == "investments":
            return bool(self.f["cur"]["investments"] or self.f["prev"]["investments"])
        if token == "donation_ledgers":
            return any("donation" in s.lower() or "political" in s.lower() for s in self.subs("EXP.OTH"))
        if token == "loans_given":
            return bool({"CA.STLA", "NCA.LTLA"} & self.lines) or self.applies("investments")
        raise ValueError(f"Unknown applicability token {token}")


def _derived(ctx: _Ctx, id: str) -> tuple[str, str]:
    m, pl, cur = ctx.m, ctx.pl, ctx.f["cur"]
    turnover, capital, profit = pl["revenue"], cur["share_capital"], pl["pat"]
    borrowings = cur["ltb"] + cur["stb"]
    if id == "P1":
        return "Complete", "Two columns: current year and previous year (Tally's opening balances)."
    if id == "P2":
        return "Information required", "The previous-year column is blank; only one year's trial balance was loaded."
    if id == "P3":
        cls = [f for f in m.flags if f.kind == "Classification"]
        if cls:
            return "Partly provided", f"{len(cls)} classification judgement(s) flagged for confirmation: {', '.join(f.ref for f in cls)}."
        return "Complete", "All ledgers classified by rule with no open judgements."
    if id == "P4":
        income = pl["revenue"] + pl["other_income"]
        if m.unit.key == "rupees":
            return "Observation", ("Figures are in whole rupees. Schedule III makes rounding off compulsory (GN para 6.15): "
                                   "total income under Rs 100 crore is rounded to hundreds, thousands, lakhs or millions.")
        ok = any(u.key == m.unit.key for u in allowed_units(income))
        return ("Complete", f"{m.unit.label}, one unit throughout, which is permitted for total income of {rs(income)}.") if ok else \
               ("Observation", f"{m.unit.label} is not a permitted unit for total income of {rs(income)} (GN para 6.15).")
    if id == "P6":
        from .ratios import compute_ratios
        rr = compute_ratios(m)
        flagged = [r.name for r in rr if r.flagged]
        unmeasured = [r.name for r in rr if r.cur is not None and r.prev is None]
        txt = (f"{sum(r.cur is not None for r in rr)} of {len(rr)} ratios are in the notes with their numerators and denominators. "
               f"{len(flagged)} moved more than 25% and need management's reason; {len(unmeasured)} cannot be compared "
               "without the previous year's profit and loss.")
        return ("Partly provided" if flagged or unmeasured else "Complete"), txt
    if id == "L11":
        wanted = {"Power and fuel": "power and fuel", "Rent": "rent", "Repairs to machinery": "repairs to machinery",
                  "Repairs to buildings": "repairs to buildings", "Insurance": "insurance", "Rates and taxes": "rates and taxes",
                  "Miscellaneous expenses": "miscellaneous"}
        have = {s.lower() for s in ctx.subs("EXP.OTH")}
        shown = [k for k, v in wanted.items() if v in have]
        return "Complete", ("Shown separately: " + (", ".join(shown) or "none of these heads has a balance") + ". "
                            "Other expenses that exceed 1% of revenue or Rs 1,00,000 are listed individually.")
    if id == "P5":
        bad = [c for c in ctx.tieouts if c.id.startswith("F") and c.status == "Fail"]
        return ("Complete", "Every noted line has a note and each note agrees to the face.") if not bad else \
               ("Observation", f"{len(bad)} face-to-note differences: {', '.join(c.id for c in bad)}.")
    if id == "S6":
        return "Partly provided", "Movement of the surplus is shown; the nature, purpose and appropriations of each reserve are not in Tally."
    if id == "O1":
        return "Partly provided", "Shown by nature (statutory dues, outstanding expenses). Whether any dues are overdue needs confirmation."
    if id == "A1":
        return "Partly provided", "Net book value and its movement are shown. Gross block, accumulated depreciation and impairment are not in Tally."
    if id == "A4":
        return "Partly provided", "Inventories are classified (" + ", ".join(ctx.subs("CA.INV")) + "). The valuation method is required."
    if id == "A8":
        return "Partly provided", "Cash, current accounts and bank deposits are shown separately. Maturity of deposits, lien and earmarking are required."
    if id == "L2":
        return "Complete", "Shown by nature: " + ", ".join(ctx.subs("REV.OI")) + "."
    if id == "L4":
        subs = ctx.subs("EXP.FIN")
        return ("Complete", "Only interest expense is booked: " + ", ".join(subs) + ".")
    if id == "L5":
        limit = max(0.01 * turnover, 100_000)
        big = [s for s in ctx.live[ctx.live["line"] == "EXP.OTH"].itertuples() if abs(s.closing) >= limit]
        return "Complete", (f"The threshold is {rs(limit)}. Every sub-head is listed separately in the note; "
                            f"{len(big)} ledger(s) exceed the threshold.")
    if id == "L7":
        if profit > 0 and pl["tax"] == 0:
            return "Observation", f"Profit of {rs(profit)} but no tax expense (current or deferred) is recorded."
        return "Complete", "Tax expense is recognised."
    if id == "L9":
        return "Not applicable", (f"Net worth {rs(cur['equity'])}, turnover {rs(turnover)} and profit {rs(profit)} are below the Sec 135 "
                                  f"thresholds ({rs(CSR_NET_WORTH)} / {rs(CSR_TURNOVER)} / {rs(CSR_PROFIT)}); the test uses the preceding year.") \
            if (cur["equity"] < CSR_NET_WORTH and turnover < CSR_TURNOVER and profit < CSR_PROFIT) else \
            ("Applies (likely)", "A Sec 135 threshold is crossed; CSR obligation and disclosure apply.")
    if id == "AS2":
        small = capital <= SMALL_COMPANY_CAPITAL and turnover <= SMALL_COMPANY_TURNOVER
        return "Complete", "Cash flow statement included (AS 3, indirect method)." + (
            " It may be optional if the company is a small company (Sec 2(40))." if small else "")
    if id == "AS5":
        if pl["dep"] > 0 and not (cur["dtl"] or ctx.f["prev"]["dtl"]):
            return "Observation", f"Depreciation of {rs(pl['dep'])} was charged but no deferred tax is recognised. Compare with tax depreciation."
        return "Complete", "Deferred tax is recognised or no timing differences arise."
    if id == "X1":
        ok = capital <= SMALL_COMPANY_CAPITAL and turnover <= SMALL_COMPANY_TURNOVER
        txt = (f"Paid-up capital {rs(capital)} (limit {rs(SMALL_COMPANY_CAPITAL)}) and turnover {rs(turnover)} "
               f"(limit {rs(SMALL_COMPANY_TURNOVER)}). Also confirm it is not a public company, a holding or subsidiary "
               "company, or a Section 8 company.")
        return ("Applies (likely)" if ok else "Not applicable"), txt
    if id == "X2":
        net_worth = cur["equity"]
        ok = net_worth <= CARO_NET_WORTH and borrowings <= CARO_BORROWINGS and turnover <= CARO_REVENUE
        txt = (f"Paid-up capital plus reserves {rs(net_worth)} (limit {rs(CARO_NET_WORTH)}); borrowings {rs(borrowings)} "
               f"(limit {rs(CARO_BORROWINGS)}); total revenue {rs(turnover)} (limit {rs(CARO_REVENUE)}). Applies to a private "
               "company that is not a subsidiary or holding company of a public company; confirm its status and the "
               "highest borrowings during the year.")
        return ("Exempt (likely)" if ok else "Applies (likely)"), txt
    if id == "X3":
        ok = turnover < IFC_TURNOVER and borrowings < IFC_BORROWINGS
        txt = (f"Turnover {rs(turnover)} (limit {rs(IFC_TURNOVER)}) and borrowings {rs(borrowings)} (limit {rs(IFC_BORROWINGS)}). "
               "The exemption is for a private company; confirm its status.")
        return ("Exempt (likely)" if ok else "Applies (likely)"), txt
    if id == "X4":
        if turnover > TAX_AUDIT_TURNOVER:
            return "Applies (likely)", (f"Turnover {rs(turnover)} exceeds {rs(TAX_AUDIT_TURNOVER)}. The limit is {rs(TAX_AUDIT_TURNOVER_DIGITAL)} "
                                        "only if cash receipts and payments are 5% or less of the total; check this.")
        return "Not applicable", f"Turnover {rs(turnover)} is within {rs(TAX_AUDIT_TURNOVER)}."
    raise ValueError(f"No derived test for {id}")


def evaluate_checklist(m: Model, tieouts) -> list[Item]:
    ctx = _Ctx(m, tieouts)
    out = []
    for it in json.loads(PATH.read_text(encoding="utf-8"))["items"]:
        applies = ctx.applies(it["applies"])
        if it["mode"] == "derived":
            status, evidence = _derived(ctx, it["id"]) if applies else ("Not applicable", "No balance in this area.")
            ask = ""
        elif applies:
            status, evidence, ask = "Information required", "Not available in Tally.", it.get("ask", "")
        else:
            status, evidence, ask = "Not applicable", "No balance or transaction of this kind in the books.", ""
        out.append(Item(it["id"], it["area"], it["requirement"], it["ref"], status, evidence, ask))
    return out
