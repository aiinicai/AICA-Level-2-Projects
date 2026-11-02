"""Evidence-based FRRB Review Engine.

Principles (from the reviewer's FRRB Technical Review practice):
1. Accuracy over quantity - an observation is raised only when a deviation is substantiated.
2. Applicability first - every check first establishes, from the company's own figures and disclosures,
   whether the item / transaction exists. A nil or absent item is logged as "Not applicable", never reported.
3. No hallucination - every observation carries located evidence (sheet / page, row, caption, amounts).
4. No checklist observations - "negative statement" items (benami, crypto, wilful defaulter, struck-off,
   layers, etc.) are not reported merely because a statement is absent.
5. Holistic analysis - the strongest observations come from cross-checking one part of the report
   against another (face vs notes, ratio table vs workings, related-party note vs balances, etc.).
6. Every observation is classified: Non-compliance, Disclosure gap, Inconsistency, Potential concern,
   or Requires verification.
"""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.fs_model import FSModel, Line
from core.knowledge_base import KnowledgeBase

NATURES = ["Non-compliance", "Inconsistency", "Disclosure gap", "Potential concern", "Requires verification"]

# Exact statutory text for non-Ind AS / AS requirements (Ind AS / AS paragraphs come from the knowledge base).
STATUTE = {
    "SEC129": ("Section 129(1), Companies Act, 2013",
               "The financial statements shall give a true and fair view of the state of affairs of the company or companies, "
               "comply with the accounting standards notified under section 133 and shall be in the form or forms as may be "
               "provided for different class or classes of companies in Schedule III."),
    "SEC2_40": ("Section 2(40), Companies Act, 2013 (proviso)",
                "Provided that the financial statement, with respect to One Person Company, small company, dormant company and "
                "private company (if such private company is a start-up), may not include the cash flow statement."),
    "SCH3_COMPARATIVE": ("Schedule III - General Instructions for preparation of financial statements",
                         "Except in the case of the first Financial Statements laid before the Company after incorporation, the "
                         "corresponding amounts (comparatives) for the immediately preceding reporting period for all items shown in "
                         "the Financial Statements including notes shall also be given."),
    "SCH3_CROSSREF": ("Schedule III - General Instructions for preparation of financial statements",
                      "Each item on the face of the Balance Sheet and Statement of Profit and Loss shall be cross-referenced to any "
                      "related information in the notes to accounts."),
    "SCH3_PPE_CAPTION": ("Schedule III, Division I, Part I - Form of Balance Sheet (as amended by MCA Notification G.S.R. 207(E) dated 24.03.2021)",
                         "Non-current assets: (a) Property, Plant and Equipment and Intangible assets - (i) Property, Plant and Equipment; "
                         "(ii) Intangible assets; (iii) Capital work-in-progress; (iv) Intangible assets under development."),
    "SCH3_PL_EXPENSES": ("Schedule III, {div}, Part II - Form of Statement of Profit and Loss",
                         "Expenses: Cost of materials consumed; Purchases of Stock-in-Trade; Changes in inventories of finished goods, "
                         "work-in-progress and Stock-in-Trade; Employee benefits expense; Finance costs; Depreciation and amortization "
                         "expense; Other expenses."),
    "SCH3_RATIOS": ("Schedule III, {div}, Part I - General Instructions, Additional Regulatory Information - Ratios (G.S.R. 207(E))",
                    "Following Ratios to be disclosed:- (a) Current Ratio, (b) Debt-Equity Ratio, (c) Debt Service Coverage Ratio, "
                    "(d) Return on Equity Ratio, (e) Inventory turnover ratio, (f) Trade Receivables turnover ratio, (g) Trade payables "
                    "turnover ratio, (h) Net capital turnover ratio, (i) Net profit ratio, (j) Return on Capital employed, (k) Return on "
                    "investment. The company shall explain the items included in numerator and denominator for computing the above "
                    "ratios. Further explanation shall be provided for any change in the ratio by more than 25% as compared to the preceding year."),
    "SCH3_LTB_TERMS": ("Schedule III, {div}, Part I - General Instructions: Borrowings",
                       "Terms of repayment of term loans and other loans shall be stated."),
    "SCH3_AUDITOR": ("Schedule III, {div}, Part II - General Instructions: Additional information",
                     "Payments to the auditor as (a) auditor, (b) for taxation matters, (c) for company law matters, (d) for other "
                     "services, (e) for reimbursement of expenses."),
    "SCH3_ONE_PERCENT": ("Schedule III, {div}, Part II - General Instructions: Additional information",
                         "Any item of income or expenditure which exceeds one per cent of the revenue from operations or Rs. 10,00,000, "
                         "whichever is higher, shall be disclosed separately."),
    "SCH3_TP_AGEING": ("Schedule III, {div}, Part I - General Instructions: Trade Payables (G.S.R. 207(E))",
                       "Trade Payables ageing schedule - outstanding for following periods from due date of payment: Less than 1 year, "
                       "1-2 years, 2-3 years, More than 3 years, for (i) MSME, (ii) Others, (iii) Disputed dues - MSME, (iv) Disputed dues - Others."),
    "SCH3_TR_AGEING": ("Schedule III, {div}, Part I - General Instructions: Trade Receivables (G.S.R. 207(E))",
                       "Trade Receivables ageing schedule - outstanding for following periods from due date of payment: Less than 6 months, "
                       "6 months-1 year, 1-2 years, 2-3 years, More than 3 years, for undisputed and disputed receivables (considered good / "
                       "significant increase in credit risk / credit impaired)."),
    "SCH3_CWIP": ("Schedule III, {div}, Part I - General Instructions, Additional Regulatory Information: Capital work-in-progress (G.S.R. 207(E))",
                  "CWIP ageing schedule (Less than 1 year, 1-2 years, 2-3 years, More than 3 years) for projects in progress and projects "
                  "temporarily suspended; and for overdue / cost-overrun projects, a CWIP completion schedule."),
    "SCH3_IAUD": ("Schedule III, {div}, Part I - General Instructions, Additional Regulatory Information: Intangible assets under development",
                  "Intangible assets under development ageing schedule for projects in progress and projects temporarily suspended, "
                  "and a completion schedule for overdue / cost-overrun projects."),
    "SCH3_PROMOTER": ("Schedule III, {div}, Part I - General Instructions: Share Capital",
                      "Shares held by promoters at the end of the year: Promoter name, No. of shares, % of total shares, % change during the year."),
    "SCH3_TITLE": ("Schedule III, {div}, Part I - General Instructions, Additional Regulatory Information: Title deeds of immovable property",
                   "The company shall provide the details of all the immovable property (other than properties where the company is the "
                   "lessee and the lease agreements are duly executed in favour of the lessee) whose title deeds are not held in the name of the company."),
    "SCH3_QTR": ("Schedule III, {div}, Part I - General Instructions, Additional Regulatory Information: Borrowings secured against current assets",
                 "Where the Company has borrowings from banks or financial institutions on the basis of security of current assets, it shall "
                 "disclose whether quarterly returns or statements of current assets filed by the Company with banks or financial institutions "
                 "are in agreement with the books of accounts; if not, summary of reconciliation and reasons of material discrepancies."),
    "MSMED22": ("Section 22, Micro, Small and Medium Enterprises Development Act, 2006",
                "(i) the principal amount and the interest due thereon (to be shown separately) remaining unpaid to any supplier as at the end "
                "of each accounting year; (ii) the amount of interest paid by the buyer in terms of section 16, along with the amount of the "
                "payment made to the supplier beyond the appointed day during each accounting year; (iii) the amount of interest due and payable "
                "for the period of delay in making payment ... ; (iv) the amount of interest accrued and remaining unpaid at the end of each "
                "accounting year; and (v) the amount of further interest remaining due and payable even in the succeeding years ..."),
    "SEC2_85": ("Section 2(85), Companies Act, 2013 read with Rule 2(1)(t), Companies (Specification of Definitions Details) Rules, 2014",
                "Small company: paid-up share capital not exceeding Rs. 4 crore and turnover not exceeding Rs. 40 crore (as amended w.e.f. 15.09.2022)."),
}


def _close(a: Optional[float], b: Optional[float], rel: float = 0.001, abs_tol: float = 1.0) -> bool:
    if a is None or b is None:
        return True
    return abs(a - b) <= max(abs_tol, rel * max(abs(a), abs(b)))


def _fmt(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:,.2f}"


def _vals(ln: Line) -> List[float]:
    """Amounts on a line, ignoring a leading serial number."""
    nums = list(ln.numbers)
    if nums and ln.raw and isinstance(ln.raw[0], (int, float)) and float(ln.raw[0]).is_integer() and 0 < ln.raw[0] <= 40 and nums[0] == ln.raw[0]:
        nums = nums[1:]
    return nums


class ReviewEngine:
    """Runs applicability-gated, evidence-based checks over an FSModel."""

    def __init__(self, model: FSModel, profile: Dict[str, Any]):
        self.m = model
        self.profile = profile
        self.ind_as = "ind as" in profile.get("framework", "").lower()
        self.div = profile.get("schedule_iii_division", "Division II")
        self.unit = model.unit
        self.findings: List[Dict[str, Any]] = []
        self.log: List[Dict[str, str]] = []

    # ------------------------------------------------------------------ helpers
    def _std(self, ind: str, legacy: str) -> str:
        return ind if self.ind_as else legacy

    def req(self, *keys: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """keys: 'STATUTE:KEY' or 'Ind AS 7|phrase' -> (citations, [{'ref','text'}])."""
        refs, texts = [], []
        for k in keys:
            if k.startswith("STATUTE:"):
                name, text = STATUTE[k[8:]]
                name = name.format(div=self.div)
                refs.append(name)
                texts.append({"ref": name, "text": text})
            else:
                std, phrase = k.split("|", 1)
                hit = KnowledgeBase.find_paragraph(std, phrase)
                if hit:
                    refs.append(f"{std}, Paragraph {hit['para']}")
                    texts.append({"ref": hit["ref"], "text": hit["text"]})
                else:
                    refs.append(std)
        return refs, texts

    def record(self, code: str, area: str, applicable: bool, basis: str, result: str) -> None:
        self.log.append({"Check": code, "Area": area, "Applicable": "Yes" if applicable else "No",
                         "Applicability basis (from the financial statements)": basis, "Result": result})

    def raise_obs(self, code: str, title: str, sub_title: str, nature: str, view: str, matter: str,
                  evidence: List[Line], req_keys: List[str], correction: str, significance: str = "Medium",
                  extra_evidence: Optional[List[Dict[str, Any]]] = None, area: str = "") -> None:
        refs, texts = self.req(*req_keys)
        ev = [{"sheet": e.sheet, "row": e.row, "text": e.cite(self.unit)} for e in evidence]
        ev += extra_evidence or []
        if not ev:
            return                                  # principle 3: never report without located evidence
        location = "; ".join(dict.fromkeys(f"{e['sheet']}" + (f" r{e['row']}" if e.get("row") else "") for e in ev))
        self.findings.append({
            "rule_code": code, "title": title, "sub_title": sub_title, "nature": nature, "view": view, "matter": matter,
            "evidence": ev, "statutory_ref": "; ".join(refs), "source_requirements": texts,
            "requirement_text": " | ".join(f"[{t['ref']}] {t['text']}" for t in texts),
            "suggested_correction": correction, "significance": significance, "basis": "Cross-verification of the financial statements"
            if nature in ("Inconsistency",) else "Applicability-based verification",
            # fields used by the existing views / Excel / Draft FS marker
            "category": area or title, "ref": location[:200], "description": view, "current_disclosure": matter,
            "action": correction, "status": nature, "risk": significance,
        })
        self.record(code, area or title, True, sub_title, f"Observation raised ({nature})")

    # ------------------------------------------------------------------ run
    def run(self) -> Dict[str, Any]:
        checks: List[Callable[[], None]] = [
            self.c_bs_totals, self.c_pl_arithmetic, self.c_reserves_profit, self.c_eps,
            self.c_cash_flow, self.c_formula_errors, self.c_other_periods, self.c_ratios,
            self.c_related_parties, self.c_receivables, self.c_payables, self.c_ppe_depreciation,
            self.c_deferred_tax_movement, self.c_investment_classification, self.c_note_references,
            self.c_combined_cogs, self.c_captions, self.c_borrowing_terms, self.c_current_tax,
            self.c_auditor_remuneration, self.c_one_percent_items, self.c_policies,
            self.g_cwip, self.g_iaud, self.g_promoter, self.g_title_deeds, self.g_quarterly_returns,
            self.c_eps_diluted, self.c_ind_as_specific, self.c_employee_benefits, self.c_cash_flow_tax_and_netting,
        ]
        for chk in checks:
            try:
                chk()
            except Exception as exc:                 # a failing check must never produce a guess
                self.record(chk.__name__, "Internal", False, f"Check could not be completed: {exc}", "Not evaluated")
        for i, f in enumerate(self.findings, start=1):
            f["issue_id"] = f"OBS-{i:02d}"
        return {"findings": self.findings, "checks": self.log}

    # ================================================================== cross-verification checks
    def _bs_totals(self) -> Tuple[Optional[Line], Optional[Line]]:
        totals = self.m.find(r"^total\b", "bs", with_amount=True)
        headings = [l for l in self.m.lines if self.m.statement_of(l) == "bs"
                    and re.fullmatch(r"(assets|equity and liabilities)", l.label.strip(), re.I)]
        assets, eql = [], []
        for t in totals:
            if re.search(r"asset", t.label, re.I) and not re.search(r"liabilit", t.label, re.I):
                assets.append(t)
            elif re.search(r"equity|liabilit", t.label, re.I):
                eql.append(t)
            else:                                    # untitled 'TOTAL': belongs to the latest heading above it
                above = [h for h in headings if h.sheet == t.sheet and h.row < t.row]
                if above:
                    (assets if re.fullmatch(r"assets", above[-1].label.strip(), re.I) else eql).append(t)
        return (assets[-1] if assets else None), (eql[-1] if eql else None)

    def c_bs_totals(self) -> None:
        a, e = self._bs_totals()
        if not a or not e or a is e:
            self.record("BS-EQUATION", "Balance Sheet", False, "Total assets / total equity and liabilities not located", "Not evaluated")
            return
        diffs = [(yr, getattr(a, yr), getattr(e, yr)) for yr in ("cy", "py")
                 if not _close(getattr(a, yr), getattr(e, yr))]
        if not diffs:
            self.record("BS-EQUATION", "Balance Sheet", True, f"Totals located at {a.loc} and {e.loc}", "No exception")
            return
        d = "; ".join(f"{'current' if y == 'cy' else 'previous'} year: Total assets {_fmt(x)} vs Total equity and liabilities {_fmt(z)} (difference {_fmt(abs(x - z))})" for y, x, z in diffs)
        self.raise_obs("BS-EQUATION", "Schedule III, Companies Act, 2013", "Balance Sheet does not balance", "Inconsistency",
                       f"The Balance Sheet does not balance - {d}. A Balance Sheet that does not balance cannot present a true and fair view.",
                       f"Balance Sheet totals: {d}.", [a, e], ["STATUTE:SEC129"],
                       "Identify and correct the unreconciled difference before the financial statements are approved.", "High", area="Balance Sheet")

    def c_pl_arithmetic(self) -> None:
        pbt = [l for l in self.m.find(r"profit.*before\s+tax|before\s+tax", "pl", True) if not re.search(r"exceptional|extraordinary", l.label, re.I)]
        pat = self.m.find(r"profit.*for\s+the\s+(period|year)|profit\s+after\s+tax", "pl", True)
        pat = [l for l in pat if not re.search(r"continuing|discontinu|before", l.label, re.I)] or pat
        if not pbt or not pat:
            self.record("PL-ARITH", "Statement of Profit and Loss", False, "Profit before tax / profit for the year not located", "Not evaluated")
            return
        pbt_l, pat_l = pbt[-1], pat[-1]
        taxes = [l for l in self.m.find(r"current\s+tax|taxes?\s+current|deferred\s+tax|earlier\s+years|mat credit|tax expense", "pl", True)
                 if pbt_l.row < l.row < pat_l.row and not re.search(r"discontinu", l.label, re.I)]
        issues = []
        for yr in ("cy", "py"):
            p, q = getattr(pbt_l, yr), getattr(pat_l, yr)
            if p is None or q is None:
                continue
            tax = sum((getattr(t, yr) or 0) for t in taxes)
            other = sum((getattr(l, yr) or 0) for l in self.m.find(r"discontinu.*after tax|prior period", "pl", True) if l.row < pat_l.row)
            if not _close(p - tax + other, q):
                issues.append(f"{'CY' if yr == 'cy' else 'PY'}: PBT {_fmt(p)} less tax {_fmt(tax)} = {_fmt(p - tax + other)}, but profit reported {_fmt(q)}")
        if issues:
            self.raise_obs("PL-ARITH", "Schedule III, Companies Act, 2013", "Statement of Profit and Loss - arithmetic", "Inconsistency",
                           "Profit for the period does not equal profit before tax less tax expense. " + "; ".join(issues) + ".",
                           "; ".join(issues), [pbt_l, pat_l] + taxes, ["STATUTE:SEC129"],
                           "Reconcile the tax expense and profit lines; correct the face of the Statement of Profit and Loss.", "High", area="Statement of Profit and Loss")
        else:
            self.record("PL-ARITH", "Statement of Profit and Loss", True, f"PBT {pbt_l.loc}, profit {pat_l.loc}", "No exception")

    def c_reserves_profit(self) -> None:
        pat = self.m.find(r"profit.*for\s+the\s+(period|year)", "pl", True)
        pat = [l for l in pat if not re.search(r"continuing|discontinu|before", l.label, re.I)] or pat
        reserve_heads = [(s, r) for s, r, t in self.m.texts if re.search(r"reserves?\s*(&|and)\s*surplus|retained earnings|other equity", t, re.I)
                         and self.m.statement_of(Line(s, r, "")) == "notes"]
        note = [l for l in self.m.find(r"(net\s+)?profit.*(for the year|for the period|as per)|surplus.*statement of profit", "notes", True)
                if any(s == l.sheet and 0 < l.row - r <= 15 for s, r in reserve_heads)]
        if not pat or not note:
            self.record("RESERVES-PAT", "Reserves / Other equity", False, "Profit transferred to reserves not located in notes", "Not evaluated")
            return
        p, n = pat[-1], note[0]
        if _close(p.cy, n.cy) and _close(p.py, n.py):
            self.record("RESERVES-PAT", "Reserves / Other equity", True, f"{n.loc}", "No exception")
            return
        self.raise_obs("RESERVES-PAT", self._std("Ind AS 1", "Schedule III, Companies Act, 2013"), "Reserves - profit for the year",
                       "Inconsistency",
                       f"The profit carried to reserves / retained earnings ({_fmt(n.cy)}) does not agree with the profit for the year in the "
                       f"Statement of Profit and Loss ({_fmt(p.cy)}).",
                       f"{n.cite(self.unit)} vs {p.cite(self.unit)}.", [n, p],
                       ["Ind AS 1|statement of changes in equity includes the following"] if self.ind_as else ["STATUTE:SEC129"],
                       "Reconcile the movement in reserves with the Statement of Profit and Loss.", "High", area="Reserves")

    def c_eps(self) -> None:
        eps = self.m.first(r"^\(?1?\)?\s*basic|basic\s+(eps|earnings)", "pl") or self.m.first(r"earnings per share.*basic|basic", "notes")
        pat = self.m.find(r"profit.*for\s+the\s+(period|year)", "pl", True)
        pat = [l for l in pat if not re.search(r"continuing|discontinu|before", l.label, re.I)] or pat
        shares = self.m.first(r"(weighted average )?number of (equity )?shares|shares outstanding at the end", "notes")
        if not eps or not pat or not shares or not self.m.unit_factor:
            self.record("EPS-RECOMPUTE", "Earnings per share", False, "EPS, profit or number of shares not located", "Not evaluated")
            return
        sh = shares.cy or (_vals(shares)[0] if _vals(shares) else None)
        if not sh:
            return
        computed = pat[-1].cy * self.m.unit_factor / sh
        if eps.cy and abs(computed - eps.cy) > max(0.02, 0.02 * abs(eps.cy)):
            self.raise_obs("EPS-RECOMPUTE", self._std("Ind AS 33", "AS 20"), "Earnings per share", "Inconsistency",
                           f"Basic EPS reported as {eps.cy:.2f} does not agree with profit for the year divided by number of shares ({computed:.2f}).",
                           f"{eps.cite()}; {pat[-1].cite(self.unit)}; {shares.cite()}.", [eps, pat[-1], shares],
                           [self._std("Ind AS 33|shall calculate basic earnings per share", "AS 20|basic earnings per share should be calculated")],
                           "Recompute basic EPS on the weighted average number of equity shares outstanding.", "Medium", area="EPS")
        else:
            self.record("EPS-RECOMPUTE", "Earnings per share", True, f"Recomputed {computed:.2f} vs reported {eps.cy}", "No exception")

    def c_cash_flow(self) -> None:
        cf_lines = [l for l in self.m.lines if self.m.statement_of(l) == "cf"]
        cf_present = bool(cf_lines) or any(self.m.statement_of(Line(s, r, "")) == "cf" for s, r, _ in self.m.texts)
        small = self.profile.get("small_company") or self.profile.get("one_person_company")
        if cf_present and not cf_lines:
            self.record("CFS", "Cash Flow Statement", True, "Cash flow statement located (amounts not parsed)", "Not evaluated")
            return
        if not cf_lines:
            if small:
                self.record("CFS", "Cash Flow Statement", False, "No cash flow statement; company qualifies as a small company (Section 2(40) proviso)", "Not applicable")
            else:
                self.raise_obs("CFS-MISSING", self._std("Ind AS 7", "AS 3"), "Cash flow statement not located", "Requires verification",
                               "No cash flow statement was located in the uploaded financial statements, and the company does not appear to "
                               "qualify for the exemption available to one person / small / dormant companies. If the complete financial "
                               "statements also omit it, this is a non-compliance.",
                               "No sheet / page titled cash flow statement in the uploaded file.", [],
                               ["STATUTE:SEC2_40"], "Confirm that a cash flow statement forms part of the financial statements.", "Medium",
                               extra_evidence=[{"sheet": "Financial statements", "row": 0, "text": "No sheet / page titled cash flow statement"}],
                               area="Cash Flow Statement")
            return
        sheet = cf_lines[0].sheet
        heading_years = sorted({int(y) for s, r, t in self.m.texts if s == sheet for y in re.findall(r"(?:year ended|as at)[^0-9]{0,20}(?:31(?:st)?\s*march,?\s*)?(20\d{2})", t, re.I)})
        errs = [e for e in self.m.errors if e[0] == sheet]
        ye = self.m.year_end
        stale = ye and heading_years and ye not in heading_years
        bs_cash = self.m.first(r"^cash and cash equivalents$|^cash and bank balances$", "bs")
        cf_close = self.m.first(r"(cash|cash equivalents).*(end of|closing)", "cf")
        mismatch = bs_cash and cf_close and cf_close.cy is not None and not _close(bs_cash.cy, cf_close.cy)
        if not (stale or errs or mismatch):
            self.record("CFS", "Cash Flow Statement", True, f"Cash flow statement located ({sheet})", "No exception")
            return
        points, ev = [], []
        if stale:
            points.append(f"the statement is headed / columned for the year(s) {', '.join(map(str, heading_years))} although the financial statements are for the year ended 31 March {ye}")
            ev += [{"sheet": s, "row": r, "text": t[:160]} for s, r, t in self.m.texts if s == sheet and re.search(r"20(1\d|2[0-9])", t)][:3]
        if errs:
            points.append(f"{len(errs)} cells display spreadsheet errors (e.g. {errs[0][2]} at {errs[0][1]}) in place of amounts")
            ev.append({"sheet": sheet, "row": 0, "text": f"Error values at {', '.join(e[1] for e in errs[:8])}{'…' if len(errs) > 8 else ''}"})
        if mismatch:
            points.append(f"closing cash and cash equivalents ({_fmt(cf_close.cy)}) does not agree with the Balance Sheet ({_fmt(bs_cash.cy)})")
        exempt = (" The company appears to qualify as a small company (paid-up capital and turnover within the Section 2(85) limits), "
                  "so a cash flow statement may be omitted under the proviso to Section 2(40); however, where one is presented it must "
                  "relate to the reporting period and be complete and accurate.") if small else ""
        self.raise_obs("CFS-INVALID", self._std("Ind AS 7", "AS 3"), "Cash flow statement", "Non-compliance",
                       "The cash flow statement presented does not relate to / is not consistent with the financial statements under review: "
                       + "; ".join(points) + "." + exempt,
                       "Cash flow statement: " + "; ".join(points) + ".", [],
                       [self._std("Ind AS 7|shall prepare a statement of cash flows", "AS 3|cash flow statement should report cash flows during the period classified"),
                        "STATUTE:SEC2_40" if small else "STATUTE:SEC129"],
                       "Replace the statement with a cash flow statement for FY current and previous year (or, if the small company exemption is "
                       "availed, omit it and remove the reference from the index / notes).", "High", extra_evidence=ev or [{"sheet": sheet, "row": 0, "text": "Cash flow statement"}],
                       area="Cash Flow Statement")

    def c_formula_errors(self) -> None:
        errs = [e for e in self.m.errors if self.m.statement_of(Line(e[0], 0, "")) != "cf"]
        if not errs:
            self.record("FORMULA-ERRORS", "Presentation", True, "Scanned all statement and note sheets", "No exception")
            return
        by_sheet: Dict[str, List[str]] = {}
        for s, c, v in errs:
            by_sheet.setdefault(s, []).append(c)
        ev = [{"sheet": s, "row": 0, "text": f"{len(cs)} error value(s) e.g. {', '.join(cs[:6])}"} for s, cs in by_sheet.items()]
        self.raise_obs("FORMULA-ERRORS", "Schedule III, Companies Act, 2013", "Presentation of notes", "Non-compliance",
                       f"The notes display spreadsheet error values (#REF! etc.) in {len(by_sheet)} sheet(s) - "
                       f"{', '.join(by_sheet)}. Financial statements containing unresolved formula errors are not fit for approval and signature.",
                       "Error values appear in: " + "; ".join(f"{e['sheet']} ({e['text']})" for e in ev) + ".", [], ["STATUTE:SEC129"],
                       "Remove working columns / correct the formulae so that only reported amounts appear.", "Medium", extra_evidence=ev,
                       area="Presentation")

    def c_other_periods(self) -> None:
        ye = self.m.year_end
        if not ye:
            self.record("OTHER-PERIODS", "Presentation", False, "Reporting date not determinable", "Not evaluated")
            return
        cols: Dict[str, set] = {}
        narrative = []
        for s, r, t in self.m.texts:
            st = self.m.statement_of(Line(s, r, ""))
            if st == "cf":
                continue
            for y in re.findall(r"31(?:st)?[\s\-]*mar(?:ch)?[\s,\-]*(20\d{2})|march\s+31,?\s*(20\d{2})", t, re.I):
                yr = int(y[0] or y[1])
                if yr < ye - 1 and len(t) < 60:
                    cols.setdefault(s, set()).add(yr)
            m = re.search(r"(?:financial\s+)?year\s+ended\s+(?:on\s+)?(?:31(?:st)?\s*march,?\s*|march\s+31,?\s*)(20\d{2})", t, re.I)
            if m and int(m.group(1)) < ye - 1 and len(t) >= 60:
                narrative.append({"sheet": s, "row": r, "text": t[:220]})
        if not cols and not narrative:
            self.record("OTHER-PERIODS", "Presentation", True, f"Reporting date 31 March {ye}", "No exception")
            return
        ev = [{"sheet": s, "row": 0, "text": f"Columns for year(s) ended 31 March {', '.join(map(str, sorted(ys)))}"} for s, ys in cols.items()]
        ev += narrative[:3]
        parts = []
        if cols:
            parts.append(f"notes in {len(cols)} sheet(s) ({', '.join(cols)}) present columns for periods earlier than the comparative year "
                         f"(31 March {ye - 1}), apparently working columns carried forward from earlier years")
        if narrative:
            parts.append("narrative disclosures refer to an earlier financial year as if it were the reporting period (e.g. \"" + narrative[0]["text"][:90] + "…\")")
        self.raise_obs("OTHER-PERIODS", "Schedule III, Companies Act, 2013", "Periods presented", "Inconsistency",
                       "The financial statements include information that does not relate to the current or comparative period: " + "; ".join(parts) + ".",
                       "; ".join(parts) + ".", [], ["STATUTE:SCH3_COMPARATIVE"],
                       f"Present only the year ended 31 March {ye} and the comparative year; update narrative notes to the reporting period.",
                       "Medium", extra_evidence=ev, area="Presentation")

    RATIO_NAMES = {
        "Current ratio": r"current\s+ratio", "Debt-equity ratio": r"debt[\s\-–]*equity", "Debt service coverage ratio": r"debt\s+service",
        "Return on equity": r"return\s+on\s+equity", "Inventory turnover": r"inventory\s+turnover", "Trade receivables turnover": r"receivables?\s+turnover",
        "Trade payables turnover": r"payables?\s+turnover", "Net capital turnover": r"net\s+capital\s+turnover", "Net profit ratio": r"net\s+profit\s+ratio",
        "Return on capital employed": r"return\s+on\s+capital", "Return on investment": r"return\s+on\s+investment",
    }

    def c_ratios(self) -> None:
        ratio_lines = {k: [l for l in self.m.lines if re.search(p, l.label, re.I) and _vals(l)] for k, p in self.RATIO_NAMES.items()}
        found = {k: v for k, v in ratio_lines.items() if v}
        if not found:
            if self.m.mentions(r"current ratio|debt[- ]equity ratio|ratio analysis|analytical ratios"):
                self.record("RATIOS", "Ratios", True, "Ratio note located (narrative form)", "Values not parsed - not evaluated")
                return
            self.raise_obs("RATIOS-MISSING", "Schedule III, Companies Act, 2013", "Ratios", "Requires verification",
                           "No note disclosing the ratios required by the 2021 amendment to Schedule III was located in the uploaded financial "
                           "statements. If the complete financial statements also omit it, this is a disclosure gap.",
                           "No note disclosing the prescribed ratios was located.", [], ["STATUTE:SCH3_RATIOS"],
                           "Disclose the eleven prescribed ratios with numerator / denominator and reasons for variance above 25%.",
                           "Medium", extra_evidence=[{"sheet": "Notes", "row": 0, "text": "No ratio note located"}], area="Ratios")
            return
        problems, ev = [], []
        for name, lines in found.items():
            cys = []
            for l in lines:
                v = _vals(l)
                if v and not any(abs(v[0] - c) <= max(0.02, 0.02 * abs(c)) for c in cys):
                    cys.append(v[0])
            if len(cys) > 1:
                problems.append(f"{name}: {' vs '.join(f'{c:.2f}' for c in cys)}")
                ev += [{"sheet": l.sheet, "row": l.row, "text": f'"{l.label}" - {_vals(l)[0]:.2f}'} for l in lines[:3]]
        # numerator / denominator checks against the face of the statements
        pat = self.m.find(r"profit.*for\s+the\s+(period|year)", "pl", True)
        pat = [l for l in pat if not re.search(r"continuing|discontinu|before", l.label, re.I)] or pat
        pbt = [l for l in self.m.find(r"before\s+tax", "pl", True)]
        roe_num = self.m.first(r"net\s+profit\s+after\s+tax", "notes")
        if roe_num and pat and pbt and _vals(roe_num) and abs(_vals(roe_num)[0] - (pbt[-1].cy or 0)) < 0.05 and not _close(pbt[-1].cy, pat[-1].cy):
            problems.append(f"Return on equity numerator described as profit after tax uses {_vals(roe_num)[0]:,.2f}, which is profit before tax "
                            f"(profit after tax is {pat[-1].cy:,.2f})")
            ev.append({"sheet": roe_num.sheet, "row": roe_num.row, "text": roe_num.cite(self.unit)})
        ca, cl, wc = (self.m.first(r"^current\s+assets\b", "notes"), self.m.first(r"^current\s+liabilities\b", "notes"),
                      self.m.first(r"^working\s+capital\b", "notes"))
        if ca and cl and wc and _vals(ca) and _vals(cl) and _vals(wc):
            computed = _vals(ca)[0] - _vals(cl)[0]
            if not _close(computed, _vals(wc)[0]):
                problems.append(f"Working capital used for Net capital turnover is {_vals(wc)[0]:,.2f}, whereas current assets less current "
                                f"liabilities is {computed:,.2f}")
                ev.append({"sheet": wc.sheet, "row": wc.row, "text": wc.cite(self.unit)})
        debt = self.m.first(r"^total\s+debt\b", "notes")
        borrow = sum((l.cy or 0) for l in self.m.find(r"borrowings", "bs", True))
        if debt and _vals(debt) and borrow and not _close(_vals(debt)[0], borrow):
            problems.append(f"Total debt used for the Debt-equity ratio is {_vals(debt)[0]:,.2f}, whereas borrowings in the Balance Sheet total {borrow:,.2f}")
            ev.append({"sheet": debt.sheet, "row": debt.row, "text": debt.cite(self.unit)})
        missing = [k for k in self.RATIO_NAMES if k not in found]
        if not problems:
            self.record("RATIOS", "Ratios", True, f"{len(found)} ratios located", "No exception" if not missing else f"Ratios not located: {', '.join(missing)}")
            return
        self.raise_obs("RATIOS-INCONSISTENT", "Schedule III, Companies Act, 2013", "Ratios - computation and consistency", "Inconsistency",
                       "The ratios disclosed do not reconcile with their own computations and / or with the audited figures: "
                       + "; ".join(problems) + ". The basis of computation should be reconciled with the financial statements so that the disclosed "
                       "ratios, and the explanations for variances above 25%, are accurate.",
                       "; ".join(problems) + ".", [], ["STATUTE:SCH3_RATIOS"],
                       "Recompute each ratio from the audited figures, align the ratio table with the workings and revise the variance explanations.",
                       "High", extra_evidence=ev, area="Ratios")

    def c_related_parties(self) -> None:
        start = [t for t in self.m.texts if re.search(r"related\s+part(y|ies)\s+disclos", t[2], re.I)]
        if not start:
            self.record("RPT", "Related parties", False, "No related party note located", "Not evaluated")
            return
        sheet, row0 = start[0][0], start[0][1]
        bal_marker = [t for t in self.m.texts if t[0] == sheet and t[1] > row0 and re.search(r"outstanding\s+balance|balance.*year\s*end|closing balance", t[2], re.I)]
        block = [l for l in self.m.lines if l.sheet == sheet and l.row > row0]
        if not bal_marker:
            self.record("RPT", "Related parties", True, f"Related party note at {sheet} r{row0}", "Outstanding balances not separately located")
            self.raise_obs("RPT-BALANCES", self._std("Ind AS 24", "AS 18"), "Related party disclosures - outstanding balances", "Disclosure gap",
                           "The related party note discloses transactions for the year but not the year-end outstanding balances.",
                           f"Related party note at {sheet} row {row0} - no outstanding balances located.", [],
                           [self._std("Ind AS 24|the amount of outstanding balances", "AS 18|the amounts or appropriate proportions of outstanding items")],
                           "Disclose outstanding balances (with terms, security and guarantees) for each category of related party.", "Medium",
                           extra_evidence=[{"sheet": sheet, "row": row0, "text": start[0][2][:120]}], area="Related parties")
            return
        brow = bal_marker[0][1]
        txn = [l for l in block if l.row < brow]
        end = min([t[1] for t in self.m.texts if t[0] == sheet and t[1] > brow
                   and re.search(r"\bratios?\b|^note\s*\d+", t[2], re.I)] or [10**6])
        bal = [l for l in block if brow < l.row < end]
        problems, ev = [], []
        # the n-th "loan" line in the transactions block corresponds to the n-th line of the same caption in the balances block
        loan_labels = {l.label.lower() for l in txn if re.search(r"loan|borrow|deposit|advance", l.label, re.I)}
        for lab in loan_labels:
            t_lines = [l for l in txn if l.label.lower() == lab]
            b_lines = [l for l in bal if l.label.lower() == lab]
            for tl, bl in zip(t_lines, b_lines):
                tv, bv = _vals(tl), _vals(bl)
                if len(bv) >= 2 and tv and all(abs(x) < 0.005 for x in tv[:2]) and not _close(bv[0], bv[1], abs_tol=0.5):
                    party = next((x.label for x in reversed([x for x in block if x.row <= bl.row])
                                  if re.search(r"\b(mr|mrs|ms|m/s|shri|smt)\.?\s", x.label, re.I)), "")
                    party = re.split(r"\s+(remuneration|loan)", party, 1, flags=re.I)[0] if party else ""
                    problems.append(f"{party + ' - ' if party else ''}{tl.label}: transactions shown as nil, but the balance moved from "
                                    f"{bv[1]:,.2f} to {bv[0]:,.2f} (net movement {bv[0] - bv[1]:,.2f})")
                    ev += [{"sheet": tl.sheet, "row": tl.row, "text": tl.cite()}, {"sheet": bl.sheet, "row": bl.row, "text": bl.cite()}]
        rem_rpt = sum(_vals(l)[0] for l in txn if re.search(r"remuneration", l.label, re.I) and _vals(l))
        rem_note = self.m.first(r"directors?['’]?\s*remuneration", "notes")
        if rem_rpt and rem_note and rem_note.sheet != sheet and not _close(rem_rpt, rem_note.cy, abs_tol=0.5):
            problems.append(f"directors' remuneration in the related party note totals {rem_rpt:,.2f}, whereas {rem_note.loc} shows {_fmt(rem_note.cy)}")
            ev.append({"sheet": rem_note.sheet, "row": rem_note.row, "text": rem_note.cite(self.unit)})
        if not problems:
            self.record("RPT", "Related parties", True, f"Related party note at {sheet} r{row0}", "No exception")
            return
        self.raise_obs("RPT-INCONSISTENT", self._std("Ind AS 24", "AS 18"), "Related party disclosures", "Inconsistency",
                       "The related party disclosures are internally inconsistent: " + "; ".join(problems) + ". Repayments / receipts of loans "
                       "are related party transactions that must be disclosed for the year.",
                       "; ".join(problems) + ".", [],
                       [self._std("Ind AS 24|information about those transactions and outstanding balances",
                                  "AS 18|the reporting enterprise should disclose the following")],
                       "Disclose the loans taken / repaid during the year for each related party and reconcile with the movement in balances.",
                       "High", extra_evidence=ev, area="Related parties")

    def c_receivables(self) -> None:
        tr = self.m.has_value(r"^trade\s+receivables$|^sundry\s+debtors$", "bs")
        if not tr:
            self.record("TR", "Trade receivables", False, "No trade receivables in the Balance Sheet", "Not applicable")
            return
        ageing = [l for l in self.m.find(r"undisputed.*good|undisputed.*considered good", "notes", True)]
        has_ageing = bool(ageing) or self.m.mentions(r"less\s+than\s+6\s+months")
        if not has_ageing:
            self.raise_obs("SCH3-TR-AGEING", "Schedule III, Companies Act, 2013", "Trade receivables ageing", "Disclosure gap",
                           f"Trade receivables of {_fmt(tr.cy)} are reported, but the ageing schedule prescribed by Schedule III is not presented.",
                           f"{tr.cite(self.unit)}; no ageing schedule located in the notes.", [tr], ["STATUTE:SCH3_TR_AGEING"],
                           "Present the trade receivables ageing schedule for the current and previous year.", "Medium", area="Trade receivables")
            return
        over6 = self.m.first(r"exceeding\s+(6|six)\s+months|more than\s+(6|six)\s+months", "notes")
        cy_age = [l for l in ageing if not _close(l.cy, tr.cy) or True]
        first = next((l for l in ageing), None)
        if over6 and first and over6.cy and _vals(first):
            buckets = _vals(first)
            beyond6 = sum(buckets[1:-1]) if len(buckets) >= 3 else 0
            if over6.cy > 0 and not _close(beyond6, over6.cy):
                self.raise_obs("TR-AGEING-CONFLICT", "Schedule III, Companies Act, 2013", "Trade receivables - conflicting ageing", "Inconsistency",
                               f"The trade receivables ageing schedule shows {_fmt(buckets[0])} outstanding for less than six months "
                               f"and {_fmt(beyond6)} beyond six months, whereas another note states that {_fmt(over6.cy)} is outstanding for a "
                               f"period exceeding six months. Both disclosures cannot be correct.",
                               f"{first.cite(self.unit)}; {over6.cite(self.unit)}.", [first, over6], ["STATUTE:SCH3_TR_AGEING"],
                               "Reconcile the ageing and remove the superseded 'exceeding six months' disclosure (replaced by the ageing schedule from 2021).",
                               "High", area="Trade receivables")
                return
        self.record("TR", "Trade receivables", True, f"Trade receivables {tr.cite(self.unit)}", "No exception")

    def c_payables(self) -> None:
        tp = self.m.has_value(r"^trade\s+payables|^sundry\s+creditors", "bs")
        if not tp:
            self.record("TP", "Trade payables", False, "No trade payables in the Balance Sheet", "Not applicable")
            return
        msme_rows = self.m.find(r"^\(?i\)?\s*msme$|^msme\b|micro\s+(and|&)\s+small", "notes", True)
        msme = next((l for l in msme_rows if (l.cy or (_vals(l)[0] if _vals(l) else 0)) and not re.search(r"other than", l.label, re.I)), None)
        has_ageing = self.m.mentions(r"trade\s+payables?\s+ageing|outstanding for following periods.*payment") and self.m.mentions(r"\bmsme\b")
        if not has_ageing:
            self.raise_obs("SCH3-TP-AGEING", "Schedule III, Companies Act, 2013", "Trade payables ageing", "Disclosure gap",
                           f"Trade payables of {_fmt(tp.cy)} are reported, but the ageing schedule prescribed by Schedule III is not presented.",
                           f"{tp.cite(self.unit)}; no ageing schedule located.", [tp], ["STATUTE:SCH3_TP_AGEING"],
                           "Present the trade payables ageing schedule (MSME / Others / Disputed) for both years.", "Medium", area="Trade payables")
        msme_amt = (msme.cy if msme and msme.cy is not None else (_vals(msme)[0] if msme and _vals(msme) else 0)) if msme else 0
        if msme_amt and msme_amt > 0:
            if not (self.m.mentions(r"appointed day") or self.m.mentions(r"section\s*16") or self.m.mentions(r"interest\s+(due|accrued).*unpaid")):
                self.raise_obs("SCH3-MSMED-SEC22", "Schedule III | MSMED Act, 2006", "Dues to micro and small enterprises", "Disclosure gap",
                               f"Dues to micro and small enterprises of {_fmt(msme_amt)} are reported, but the particulars required by "
                               "Section 22 of the MSMED Act, 2006 (principal and interest unpaid, interest paid under Section 16, interest due "
                               "for delay, interest accrued and further interest) are not furnished.",
                               f"{msme.cite(self.unit)}.", [msme], ["STATUTE:MSMED22"],
                               "Furnish the Section 22 particulars (i) to (v), and reconcile them with the ageing schedule.", "Medium",
                               area="Trade payables")
                return
        self.record("TP", "Trade payables", True, f"{tp.cite(self.unit)}; MSME dues {_fmt(msme_amt)}",
                    "No exception" if msme_amt else "MSME dues nil - Section 22 particulars not applicable")

    def c_ppe_depreciation(self) -> None:
        dep = self.m.first(r"^depreciation", "pl")
        if not dep or not dep.cy:
            self.record("PPE-DEP", "PPE", False, "Depreciation not located in the Statement of Profit and Loss", "Not evaluated")
            return
        sheets = {l.sheet for l in self.m.lines if re.search(r"fixed[\s_]*asset|property,?\s*plant|ppe", l.sheet + " " + self.m.sheet_titles.get(l.sheet, ""), re.I)}
        if not sheets:
            self.record("PPE-DEP", "PPE", False, "PPE note not located", "Not evaluated")
            return
        totals = [l for l in self.m.lines if l.sheet in sheets and re.search(r"^(sub\s*)?total", l.label, re.I)]
        found = any(any(abs(n - dep.cy) < 0.02 for n in l.numbers) for l in totals)
        if found:
            self.record("PPE-DEP", "PPE", True, f"Depreciation {dep.cite(self.unit)} agrees to the PPE note", "No exception")
        else:
            self.raise_obs("PPE-DEP", self._std("Ind AS 16", "AS 10"), "Depreciation - face vs PPE note", "Inconsistency",
                           f"Depreciation charged in the Statement of Profit and Loss ({_fmt(dep.cy)}) is not traceable to the depreciation for the year in the PPE note.",
                           f"{dep.cite(self.unit)}; PPE note totals in {', '.join(sheets)} do not show this amount.", [dep] + totals[:2],
                           [self._std("Ind AS 16|a reconciliation of the carrying amount at the beginning and end of the period", "AS 10|reconciliation of the carrying amount")],
                           "Reconcile the depreciation charge with the PPE movement schedule.", "Medium", area="PPE")

    def c_deferred_tax_movement(self) -> None:
        dt_pl = self.m.first(r"^deferred\s+tax", "pl")
        dtl = self.m.first(r"deferred\s+tax\s+liabilit", "bs")
        dta = self.m.first(r"deferred\s+tax\s+asset", "bs")
        if not dt_pl or (not dtl and not dta):
            self.record("DT-MOVE", "Deferred tax", False, "Deferred tax not located on both faces", "Not evaluated")
            return
        def net(yr):
            return (getattr(dtl, yr) or 0 if dtl else 0) - (getattr(dta, yr) or 0 if dta else 0)
        movement = net("cy") - net("py")
        if self.ind_as and self.m.mentions(r"other comprehensive income"):
            self.record("DT-MOVE", "Deferred tax", True, "Ind AS - part of the movement may be in OCI", "Not evaluated")
            return
        if _close(movement, dt_pl.cy or 0):
            self.record("DT-MOVE", "Deferred tax", True, f"Net DTL movement {movement:,.2f} = charge {dt_pl.cy}", "No exception")
            return
        self.raise_obs("DT-MOVE", self._std("Ind AS 12", "AS 22"), "Deferred tax - movement", "Inconsistency",
                       f"The deferred tax charge in the Statement of Profit and Loss ({_fmt(dt_pl.cy)}) does not equal the movement in the net "
                       f"deferred tax balance in the Balance Sheet ({movement:,.2f}).",
                       f"{dt_pl.cite(self.unit)}; " + "; ".join(x.cite(self.unit) for x in (dtl, dta) if x) + ".", [dt_pl] + [x for x in (dtl, dta) if x],
                       [self._std("Ind AS 12|the following shall also be disclosed separately", "AS 22|comprising current tax and deferred tax")],
                       "Reconcile the deferred tax charge with the movement in deferred tax assets / liabilities.", "Medium", area="Taxation")

    def c_investment_classification(self) -> None:
        if self.ind_as:
            self.record("INV-CLASS", "Investments", False, "Ind AS - classification governed by Ind AS 109", "Not evaluated")
            return
        bs = [l for l in self.m.lines if self.m.statement_of(l) == "bs"]
        current_inv = None
        in_current = False
        for l in bs:
            if re.fullmatch(r"current\s+assets", l.label.strip(), re.I):
                in_current = True
            elif re.fullmatch(r"non[- ]current\s+assets", l.label.strip(), re.I):
                in_current = False
            elif in_current and re.fullmatch(r"(current\s+)?investments", l.label.strip(), re.I) and (l.cy or 0) > 0:
                current_inv = l
        if not current_inv:
            self.record("INV-CLASS", "Investments", False, "No current investments on the face", "Not applicable")
            return
        lt = self.m.text_hits(r"long[- ]term\s+(cost|investment)|valued at long term cost|non[- ]trade", 3)
        if not lt:
            self.record("INV-CLASS", "Investments", True, f"{current_inv.cite(self.unit)}", "No exception")
            return
        self.raise_obs("INV-CLASS", "AS 13 | Schedule III, Companies Act, 2013", "Classification of investments", "Inconsistency",
                       f"Investments of {_fmt(current_inv.cy)} are presented under Current Assets, whereas the investment note / policy "
                       f"describes them as long-term investments carried at cost (\"{lt[0][2][:80]}\"). An investment that is not intended to be "
                       "held for not more than one year is a long-term investment and is presented as a non-current investment.",
                       f"{current_inv.cite(self.unit)}; note text at {lt[0][0]} row {lt[0][1]}.", [current_inv],
                       ["AS 13|current investment is an investment that is by its nature readily realisable"],
                       "Reclassify the investment as a non-current investment (or revise the note if it is genuinely current).", "Medium",
                       extra_evidence=[{"sheet": s, "row": r, "text": t[:160]} for s, r, t in lt[:2]], area="Investments")

    def c_note_references(self) -> None:
        a, _ = self._bs_totals()
        total = (a.cy or a.py) if a else None
        if not total:
            self.record("NOTE-XREF", "Presentation", False, "Balance Sheet total not located", "Not evaluated")
            return
        missing = []
        for l in self.m.lines:
            if self.m.statement_of(l) != "bs" or l.note or re.search(r"^total|^sub|^\s*$", l.label, re.I):
                continue
            amt = max(abs(l.cy or 0), abs(l.py or 0))
            if amt >= 0.01 * abs(total) and re.search(r"[a-z]", l.label):
                missing.append(l)
        if not missing:
            self.record("NOTE-XREF", "Presentation", True, "All material Balance Sheet captions carry a note reference", "No exception")
            return
        self.raise_obs("NOTE-XREF", "Schedule III, Companies Act, 2013", "Cross-referencing to notes", "Disclosure gap",
                       "The following material Balance Sheet captions carry no note reference and no supporting note was identified: "
                       + "; ".join(f"{l.label} (CY {_fmt(l.cy)}, PY {_fmt(l.py)})" for l in missing) + ".",
                       "; ".join(l.cite(self.unit) for l in missing) + ".", missing, ["STATUTE:SCH3_CROSSREF"],
                       "Add notes giving the composition of each caption (e.g. nature of provisions and their movement) and cross-reference them.",
                       "Low", area="Presentation")

    def c_combined_cogs(self) -> None:
        l = self.m.first(r"cost of\s+materials?\s+consumed.*(including|incl\.|and).*changes?\s+in\s+inventor", "pl")
        if not l:
            self.record("PL-HEADS", "Statement of Profit and Loss", True, "Expense heads reviewed", "No exception")
            return
        self.raise_obs("PL-HEADS", "Schedule III, Companies Act, 2013", "Expense heads on the face", "Non-compliance",
                       f"\"{l.label}\" is presented as a single expense head ({_fmt(l.cy)}). Schedule III requires cost of materials consumed and "
                       "changes in inventories of finished goods, work-in-progress and stock-in-trade to be presented separately on the face.",
                       f"{l.cite(self.unit)}.", [l], ["STATUTE:SCH3_PL_EXPENSES"],
                       "Present cost of materials consumed (raw material only) and changes in inventories of FG / WIP separately.", "Low",
                       area="Statement of Profit and Loss")

    def c_captions(self) -> None:
        hits: List[Line] = []
        if not self.ind_as and self.div == "Division I":
            hits = [l for l in self.m.lines if self.m.statement_of(l) == "bs" and re.fullmatch(r"(fixed assets|tangible assets)", l.label.strip(), re.I)]
            texts = self.m.text_hits(r"^note\s*\d+\s*[-–:]\s*fixed assets", 2)
            key = "STATUTE:SCH3_PPE_CAPTION"
            view = ("The Balance Sheet uses the pre-2021 captions \"Fixed assets\" / \"Tangible assets\". Division I of Schedule III, as amended "
                    "by G.S.R. 207(E) with effect from 1 April 2021, prescribes \"Property, Plant and Equipment and Intangible assets\" with "
                    "\"Property, Plant and Equipment\" as the sub-head.")
        elif self.ind_as:
            texts = self.m.text_hits(r"\bfixed assets\b|\bnet block\b|\blong[- ]term investments\b|\bextraordinary items?\b", 6)
            key = "Ind AS 16|a reconciliation of the carrying amount at the beginning and end of the period"
            view = ("Captions from the pre-Ind AS framework continue to be used (e.g. \"Fixed Assets\", \"Net Block\", \"Long term investments\", "
                    "\"Extraordinary items\"), which do not correspond to the terminology of the applicable Ind AS and Schedule III, Division II.")
        else:
            texts = []
            key = ""
        if not hits and not texts:
            self.record("CAPTIONS", "Presentation", True, "Captions reviewed against the applicable format", "No exception")
            return
        extra = [{"sheet": s, "row": r, "text": t[:120]} for s, r, t in texts]
        req = [key]
        if self.ind_as and any(re.search(r"extraordinary", t[2], re.I) for t in texts):
            req.append("Ind AS 1|shall not present any items of income or expense as extraordinary items")
        self.raise_obs("CAPTIONS", "Schedule III, Companies Act, 2013", "Captions / terminology", "Non-compliance", view,
                       "Captions used: " + "; ".join([l.cite() for l in hits] + [f"{s} r{r}: \"{t[:60]}\"" for s, r, t in texts]) + ".",
                       hits, req, "Align the captions with the prescribed format and terminology.", "Low", extra_evidence=extra, area="Presentation")

    def c_borrowing_terms(self) -> None:
        ltb = self.m.has_value(r"long[- ]term\s+borrowings|^borrowings$", "bs")
        if not ltb or not (ltb.cy or 0):
            self.record("LTB-TERMS", "Borrowings", False, "No long-term borrowings outstanding", "Not applicable")
            return
        if self.m.text_hits(r"repay|instal|tenure|terms of (the )?(loan|borrowing)|interest[- ]free|repayable", 1):
            self.record("LTB-TERMS", "Borrowings", True, ltb.cite(self.unit), "No exception")
            return
        parts = [l for l in self.m.find(r"loan", "notes", True) if l.cy and re.search(r"borrow", self.m.sheet_titles.get(l.sheet, "") + l.sheet + l.section, re.I) or (l.cy and re.search(r"unsecured loan", l.label, re.I))][:4]
        self.raise_obs("LTB-TERMS", "Schedule III, Companies Act, 2013", "Long-term borrowings - terms", "Disclosure gap",
                       f"Long-term borrowings of {_fmt(ltb.cy)} are reported without disclosure of the terms of repayment, rate of interest "
                       "(or that they are interest-free) and security, if any.",
                       "; ".join(x.cite(self.unit) for x in [ltb] + parts) + ".", [ltb] + parts, ["STATUTE:SCH3_LTB_TERMS"],
                       "State the repayment terms, interest rate and security for each loan; classify amounts repayable within 12 months as current.",
                       "Medium", area="Borrowings")

    def c_current_tax(self) -> None:
        pbt = [l for l in self.m.find(r"before\s+tax", "pl", True)]
        if not pbt or (pbt[-1].cy or 0) <= 0:
            self.record("CURRENT-TAX", "Taxation", False, "No profit before tax in the current year", "Not applicable")
            return
        ct = self.m.first(r"current\s+tax|taxes?\s+current", "pl")
        charged = [l for l in self.m.find(r"current\s+tax|taxes?\s+current|^tax\s+expense|^income\s+tax|^provision for tax", "pl", True)
                   if (l.cy or 0) and not re.search(r"deferred|earlier", l.label, re.I)]
        if charged:
            self.record("CURRENT-TAX", "Taxation", True, charged[0].cite(self.unit), "No exception")
            return
        if ct and ct.cy:
            self.record("CURRENT-TAX", "Taxation", True, f"{ct.cite(self.unit)}", "No exception")
            return
        if self.m.mentions(r"brought forward|unabsorbed|set[- ]off|115JB|minimum alternate tax|no provision for (current )?tax"):
            self.record("CURRENT-TAX", "Taxation", True, "Nil current tax explained in the notes", "No exception")
            return
        ev = [pbt[-1]] + ([ct] if ct else [])
        reserves = self.m.first(r"^reserves\s*(and|&)\s*surplus|^other\s+equity", "bs")
        context = ""
        if reserves and (reserves.cy or 0) < 0:
            ev.append(reserves)
            context = (f" Reserves and surplus are negative ({_fmt(reserves.cy)}), so brought forward losses may explain the nil charge; "
                       "the basis should nevertheless be verified and stated, including the position under Section 115JB.")
        self.raise_obs("CURRENT-TAX", self._std("Ind AS 12", "AS 22") + " | Income-tax Act, 1961", "Current tax", "Requires verification",
                       f"Profit before tax of {_fmt(pbt[-1].cy)} is reported but no current tax is provided and no explanation (e.g. set-off of "
                       "brought forward losses / unabsorbed depreciation, or MAT under Section 115JB) is given." + context,
                       "; ".join(x.cite(self.unit) for x in ev) + ".", ev,
                       [self._std("Ind AS 12|the major components of tax expense", "AS 22|comprising current tax and deferred tax")],
                       "Verify the tax computation; disclose the basis for nil current tax.", "Medium", area="Taxation")

    def c_auditor_remuneration(self) -> None:
        fee = self.m.has_value(r"audit\s*fees?|auditor['’]?s?\s+remuneration|payment to auditors?", "notes")
        if not fee:
            self.record("AUDITOR-FEE", "Other expenses", False, "No auditor remuneration line", "Not applicable")
            return
        if self.m.mentions(r"taxation matters|company law matters|tax audit"):
            self.record("AUDITOR-FEE", "Other expenses", True, fee.cite(self.unit), "No exception")
            return
        self.raise_obs("AUDITOR-FEE", "Schedule III, Companies Act, 2013", "Payments to the auditor", "Disclosure gap",
                       f"Payment to the auditor is disclosed as a single amount ({_fmt(fee.cy)}) without the bifurcation prescribed by Schedule III "
                       "(as auditor, for taxation matters, for company law matters, for other services, reimbursement of expenses).",
                       f"{fee.cite(self.unit)}.", [fee], ["STATUTE:SCH3_AUDITOR"],
                       "Disclose the payments to the auditor in the prescribed categories.", "Low", area="Other expenses")

    def c_one_percent_items(self) -> None:
        rev = self.m.amount(r"^revenue\s+from\s+operations", "pl")
        if not rev or not self.m.unit_factor:
            self.record("ONE-PCT", "Other expenses", False, "Revenue not located", "Not evaluated")
            return
        threshold = max(0.01 * rev, 1_000_000 / self.m.unit_factor)
        lumps = [l for l in self.m.find(r"^(miscellaneous|misc\.?|sundry|others?)\b(?!.*(liabilit|payable|asset|receivable|income tax))", "notes", True)
                 if (l.cy or 0) > threshold]
        if not lumps:
            self.record("ONE-PCT", "Other income / expenses", True, f"Threshold {threshold:,.2f} ({self.unit})", "No exception")
            return
        self.raise_obs("ONE-PCT", "Schedule III, Companies Act, 2013", "Items exceeding 1% / Rs 10 lakh", "Non-compliance",
                       "Aggregated items exceed the threshold for separate disclosure (higher of 1% of revenue from operations and Rs 10 lakh = "
                       f"{threshold:,.2f}): " + "; ".join(f"{l.label} {_fmt(l.cy)}" for l in lumps) + ".",
                       "; ".join(l.cite(self.unit) for l in lumps) + ".", lumps, ["STATUTE:SCH3_ONE_PERCENT"],
                       "Disclose the nature and amount of each component exceeding the threshold.", "Low", area="Other income / expenses")

    def c_policies(self) -> None:
        checks = [
            ("POL-CASH-EQ", r"cash equivalents?.{0,120}(original )?maturit(y|ies) of (less than |up to |upto )?(twelve|12) months",
             self._std("Ind AS 7|three months or less from the date of acquisition", "AS 3|three months or less from the date of acquisition"),
             "Cash and cash equivalents", "The accounting policy treats deposits with an original maturity of up to twelve months as cash equivalents. "
             "An investment normally qualifies as a cash equivalent only when it has a short maturity of three months or less from the date of acquisition.",
             "Restrict cash equivalents to deposits of three months or less; present other deposits as other bank balances and restate the cash flow statement.",
             "Non-compliance"),
            ("POL-DEP-DISPOSAL", r"(deletion|disposal|sold).{0,60}no depreciation|no depreciation.{0,60}(deletion|disposal|sold)",
             self._std("Ind AS 16|depreciation of an asset ceases at the earlier of", "AS 10|depreciation of an asset ceases at the earlier of"),
             "Property, plant and equipment", "The policy states that no depreciation is charged on assets in the year of disposal, whereas "
             "depreciation ceases only on the date the asset is derecognised or classified as held for sale.",
             "Charge depreciation up to the date of disposal and revise the policy.", "Non-compliance"),
            ("POL-INV-MARKET", r"(waste|scrap|by[- ]product|inventor).{0,40}market (price|value)",
             self._std("Ind AS 2|inventories shall be measured at the lower of cost and net realisable value", "AS 2|inventories should be valued at the lower of cost and net realisable value"),
             "Inventories", "The inventory policy measures certain inventories at \"market price\", whereas inventories are measured at the lower of "
             "cost and net realisable value (an entity-specific value, not market price).",
             "Revise the policy and verify the carrying amount on the lower of cost and NRV basis.", "Potential concern"),
        ]
        if self.ind_as:
            checks += [
                ("POL-IND101", r"(restat|previous year).{0,80}ind\s?as\s?101|ind\s?as\s?101.{0,80}restat",
                 "Ind AS 101|an entity shall apply this ind as in", "Accounting policies",
                 "The policy refers to Ind AS 101 as the basis for restating comparatives although these are not the company's first Ind AS "
                 "financial statements; restatements are governed by Ind AS 8 / Ind AS 1.", "Revise the policy to refer to Ind AS 8 and Ind AS 1.", "Potential concern"),
                ("POL-LEASE", r"operating lease.{0,120}(expense|charged|recognised)|lease rentals? (are|is) (charged|recognised)",
                 "Ind AS 116|at the commencement date, a lessee shall recognise", "Leases",
                 "The policy describes lessee leases as operating leases with rentals expensed, a model not available to lessees under Ind AS 116 "
                 "(other than short-term / low-value leases).", "Recognise right-of-use assets and lease liabilities or state the exemption applied.",
                 "Potential concern"),
            ]
        for code, rx, req_key, area, view, fix, nature in checks:
            hits = self.m.text_hits(rx, 2)
            if code == "POL-LEASE" and self.m.mentions(r"right[- ]of[- ]use"):
                hits = []
            if code == "POL-INV-MARKET" and hits and re.search(r"net realisable value", hits[0][2], re.I):
                hits = []
            if not hits:
                self.record(code, area, True, "Policy text reviewed", "No exception")
                continue
            self.raise_obs(code, req_key.split("|")[0], area, nature, view,
                           f"Policy text at {hits[0][0]} row {hits[0][1]}: \"{hits[0][2][:200]}\"", [], [req_key], fix, "Medium",
                           extra_evidence=[{"sheet": s, "row": r, "text": t[:200]} for s, r, t in hits], area=area)
        if self.ind_as and self.m.year_end and self.m.year_end >= 2024:
            sig = self.m.text_hits(r"significant accounting polic", 1)
            if sig and not self.m.mentions(r"material accounting polic"):
                self.raise_obs("POL-MATERIAL", "Ind AS 1", "Accounting policies", "Non-compliance",
                               "Accounting policies are presented as 'significant accounting policies'. Ind AS 1 as amended (effective 1 April 2023) "
                               "requires disclosure of material accounting policy information.",
                               f"Heading at {sig[0][0]} row {sig[0][1]}: \"{sig[0][2][:80]}\"", [], ["Ind AS 1|disclose material accounting policy information"],
                               "Re-present the policies as material accounting policy information.", "Low",
                               extra_evidence=[{"sheet": sig[0][0], "row": sig[0][1], "text": sig[0][2][:120]}], area="Accounting policies")

    # ================================================================== applicability-gated disclosure checks
    def g_cwip(self) -> None:
        l = self.m.has_value(r"capital\s+work[- ]in[- ]progress|^cwip", "bs")
        if not l:
            self.record("SCH3-CWIP", "Capital work-in-progress", False, "CWIP is nil in both years", "Not applicable")
            return
        if self.m.mentions(r"projects?\s+in\s+progress|cwip\s+ageing|temporarily\s+suspended"):
            self.record("SCH3-CWIP", "Capital work-in-progress", True, l.cite(self.unit), "No exception")
            return
        self.raise_obs("SCH3-CWIP-AGEING", "Schedule III, Companies Act, 2013", "CWIP ageing", "Disclosure gap",
                       f"Capital work-in-progress of {_fmt(l.cy)} (PY {_fmt(l.py)}) is reported, but the CWIP ageing schedule is not presented.",
                       f"{l.cite(self.unit)}.", [l], ["STATUTE:SCH3_CWIP"], "Present the CWIP ageing (and completion) schedule.", "Medium", area="CWIP")

    def g_iaud(self) -> None:
        l = self.m.has_value(r"intangible\s+assets?\s+under\s+development", "bs")
        if not l:
            self.record("SCH3-IAUD", "Intangible assets under development", False, "Nil in both years", "Not applicable")
            return
        if self.m.mentions(r"projects?\s+in\s+progress"):
            self.record("SCH3-IAUD", "Intangible assets under development", True, l.cite(self.unit), "No exception")
            return
        self.raise_obs("SCH3-INTANGIBLE-CWIP", "Schedule III, Companies Act, 2013", "Intangible assets under development", "Disclosure gap",
                       f"Intangible assets under development of {_fmt(l.cy)} are reported without the prescribed ageing schedule.",
                       f"{l.cite(self.unit)}.", [l], ["STATUTE:SCH3_IAUD"], "Present the ageing schedule.", "Medium", area="Intangible assets")

    def g_promoter(self) -> None:
        sc = self.m.has_value(r"^(equity\s+)?share\s+capital", "bs")
        if not sc:
            self.record("SCH3-PROMOTER", "Share capital", False, "No share capital line", "Not applicable")
            return
        if self.m.mentions(r"promoter"):
            self.record("SCH3-PROMOTER", "Share capital", True, "Promoter shareholding table located", "No exception")
            return
        self.raise_obs("SCH3-PROMOTER-TABLE", "Schedule III, Companies Act, 2013", "Promoter shareholding", "Disclosure gap",
                       "The share capital note does not disclose shares held by promoters at the end of the year and the % change during the year.",
                       f"{sc.cite(self.unit)}; no promoter shareholding table located.", [sc], ["STATUTE:SCH3_PROMOTER"],
                       "Add the promoter shareholding table for both years.", "Medium", area="Share capital")

    def g_title_deeds(self) -> None:
        prop = self.m.has_value(r"\bland\b|building|premises|immovable", "notes")
        if not prop:
            self.record("SCH3-TITLE", "PPE - title deeds", False, "No land / building in the PPE schedule", "Not applicable")
            return
        if self.m.mentions(r"title\s+deeds?|immovable\s+propert(y|ies).{0,60}(held in (the )?name|name of)"):
            self.record("SCH3-TITLE", "PPE - title deeds", True, f"{prop.cite(self.unit)}; title-deed statement located", "No exception")
            return
        self.raise_obs("SCH3-TITLE-DEEDS", "Schedule III, Companies Act, 2013", "Title deeds of immovable property", "Disclosure gap",
                       f"The company holds immovable property ({prop.label}: {_fmt(prop.cy)}) but the financial statements do not state whether "
                       "the title deeds are held in the name of the company (or give the prescribed details where they are not).",
                       f"{prop.cite(self.unit)}.", [prop], ["STATUTE:SCH3_TITLE"],
                       "Add the title-deeds disclosure (or the prescribed table of exceptions).", "Medium", area="PPE")

    def g_quarterly_returns(self) -> None:
        secured_wc = self.m.text_hits(r"cash credit|working capital (loan|limit|facilit)|hypothecation of (stock|inventor|book debts|receivables|current assets)", 2)
        if not secured_wc:
            self.record("SCH3-QTR", "Borrowings", False, "No bank borrowings secured on current assets", "Not applicable")
            return
        if self.m.mentions(r"quarterly\s+(returns?|statements?)"):
            self.record("SCH3-QTR", "Borrowings", True, "Quarterly returns statement located", "No exception")
            return
        self.raise_obs("SCH3-BANK-RETURNS-RECON", "Schedule III, Companies Act, 2013", "Borrowings secured against current assets", "Disclosure gap",
                       "The company has bank borrowings secured on current assets, but does not state whether the quarterly returns / statements "
                       "of current assets filed with the bank agree with the books of account.",
                       f"{secured_wc[0][0]} row {secured_wc[0][1]}: \"{secured_wc[0][2][:150]}\"", [], ["STATUTE:SCH3_QTR"],
                       "Disclose agreement of quarterly returns with books, or the reconciliation and reasons for material differences.", "Medium",
                       extra_evidence=[{"sheet": s, "row": r, "text": t[:150]} for s, r, t in secured_wc], area="Borrowings")

    def c_eps_diluted(self) -> None:
        basic = self.m.first(r"basic", "pl")
        if not basic:
            self.record("EPS-DILUTED", "EPS", False, "EPS not on the face", "Not evaluated")
            return
        if self.m.mentions(r"diluted"):
            self.record("EPS-DILUTED", "EPS", True, "Diluted EPS presented", "No exception")
            return
        if not self.ind_as and self.profile.get("smc"):
            self.record("EPS-DILUTED", "EPS", False, "Small and Medium-sized Company - AS 20 permits omission of diluted EPS", "Not applicable")
            return
        self.raise_obs("EPS-DILUTED", self._std("Ind AS 33", "AS 20"), "Diluted EPS", "Non-compliance",
                       "Only basic EPS is presented on the face of the Statement of Profit and Loss; diluted EPS is required to be presented "
                       "(with equal prominence) even if it equals basic EPS.",
                       f"{basic.cite()}.", [basic],
                       [self._std("Ind AS 33|shall present in the statement of profit and loss basic and diluted earnings per share",
                                  "AS 20|should present basic and diluted earnings per share on the face")],
                       "Present diluted EPS for both years.", "Low", area="EPS")

    def c_ind_as_specific(self) -> None:
        if not self.ind_as:
            self.record("IND-AS-SET", "Ind AS disclosures", False, f"Framework is {self.profile.get('framework')}", "Not applicable")
            return
        tax = self.m.first(r"total\s+tax\s+expense|^tax\s+expense|current\s+tax", "pl")
        if tax and (tax.cy or 0) and not self.m.mentions(r"reconciliation.{0,80}(tax|effective)|effective\s+tax\s+rate|applicable\s+tax\s+rate"):
            self.raise_obs("INDAS-12-TAX-RECON", "Ind AS 12", "Tax reconciliation", "Disclosure gap",
                           f"Tax expense of {_fmt(tax.cy)} is recognised, but no numerical reconciliation between tax expense and accounting profit "
                           "multiplied by the applicable tax rate is disclosed.",
                           f"{tax.cite(self.unit)}; no reconciliation located.", [tax], ["Ind AS 12|an explanation of the relationship between tax expense"],
                           "Disclose the numerical tax rate reconciliation.", "Medium", area="Taxation")
        else:
            self.record("INDAS-12-TAX-RECON", "Taxation", bool(tax), "Tax expense / reconciliation reviewed", "No exception")
        if not self.m.mentions(r"\bsegment"):
            rev = self.m.first(r"^revenue\s+from\s+operations", "pl")
            if rev:
                self.raise_obs("INDAS-108-SEGMENTS", "Ind AS 108", "Operating segments", "Disclosure gap",
                               "No operating segment information (or statement that the company operates in a single segment, with entity-wide "
                               "disclosures on products, geography and major customers) is given.",
                               f"{rev.cite(self.unit)}; the word 'segment' does not appear in the financial statements.", [rev],
                               ["Ind AS 108|an entity shall provide information about the extent of its reliance on its major customers"],
                               "Disclose segment information or the single-segment statement with entity-wide disclosures.", "Medium", area="Segments")
        borrow = [l for l in self.m.find(r"borrowings", "bs", True) if not _close(l.cy, l.py)]
        if borrow and [l for l in self.m.lines if self.m.statement_of(l) == "cf"] and not self.m.mentions(r"changes in liabilities arising from financing|net debt reconciliation"):
            self.raise_obs("INDAS-7-NET-DEBT-RECON", "Ind AS 7", "Changes in liabilities from financing activities", "Disclosure gap",
                           "Borrowings changed during the year but the reconciliation of liabilities arising from financing activities is not disclosed.",
                           "; ".join(l.cite(self.unit) for l in borrow) + ".", borrow, ["Ind AS 7|changes in liabilities arising from financing activities"],
                           "Disclose the reconciliation of opening and closing liabilities arising from financing activities.", "Low", area="Cash Flow Statement")
        fa_sheets = {l.sheet for l in self.m.lines if re.search(r"financial assets", l.label + " " + l.section, re.I)}
        nonfin = [l for l in self.m.lines if l.sheet in fa_sheets and (l.cy or 0) > 0
                  and re.search(r"\bgst\b|input tax|prepaid|advance(s)? (for|to) (purchase|supplier|vendor)|balances? with (government|statutory)", l.label, re.I)]
        if nonfin:
            self.raise_obs("INDAS-32-NONFIN", "Ind AS 32 | Schedule III, Companies Act, 2013", "Classification - financial assets", "Inconsistency",
                           "Items that are not contractual rights to receive cash (GST credit, prepaid expenses, advances for purchases) are "
                           "presented within financial assets: " + "; ".join(f"{l.label} {_fmt(l.cy)}" for l in nonfin) + ".",
                           "; ".join(l.cite(self.unit) for l in nonfin) + ".", nonfin, ["Ind AS 32|a financial asset is any asset that is"],
                           "Present these balances under other (non-financial) assets.", "Medium", area="Classification")

    def c_employee_benefits(self) -> None:
        db = self.m.has_value(r"gratuity|defined\s+benefit|leave encashment|compensated absences", "notes") or self.m.has_value(r"long[- ]term\s+provisions", "bs")
        if not db:
            self.record("EMP-BEN", "Employee benefits", False, "No defined benefit obligation / provision", "Not applicable")
            return
        if not self.ind_as and self.profile.get("smc"):
            self.record("EMP-BEN", "Employee benefits", False, "SMC - AS 15 relaxations available; detailed actuarial disclosures not mandatory", "Not applicable")
            return
        missing = []
        if not self.m.mentions(r"discount rate|actuarial assumption"):
            missing.append("principal actuarial assumptions")
        if self.ind_as and not self.m.mentions(r"sensitivity"):
            missing.append("sensitivity analysis")
        if not self.m.mentions(r"opening (balance|obligation).{0,80}(benefit|obligation)|reconciliation of (the )?(opening|present value)"):
            missing.append("reconciliation of the obligation")
        if not missing:
            self.record("EMP-BEN", "Employee benefits", True, db.cite(self.unit), "No exception")
            return
        self.raise_obs("EMP-BEN", self._std("Ind AS 19", "AS 15"), "Defined benefit plans", "Disclosure gap",
                       f"A defined benefit obligation exists ({db.label}: {_fmt(db.cy)}) but the following required disclosures are not given: "
                       + ", ".join(missing) + ".", f"{db.cite(self.unit)}.", [db],
                       [self._std("Ind AS 19|significant actuarial assumptions used to determine the present value", "AS 15|should disclose the following information about defined benefit plans")],
                       "Provide the actuarial disclosures for the defined benefit plan.", "Medium", area="Employee benefits")

    def c_cash_flow_tax_and_netting(self) -> None:
        cf = [l for l in self.m.lines if self.m.statement_of(l) == "cf"]
        if not cf or [e for e in self.m.errors if e[0] == cf[0].sheet]:
            self.record("CFS-TAX-NET", "Cash Flow Statement", False, "No usable cash flow statement", "Not evaluated")
            return
        prov = [l for l in cf if re.search(r"provision for (income )?tax", l.label, re.I) and (l.cy or 0)]
        if prov and not any(re.search(r"tax(es)? paid|income tax paid|direct taxes paid", l.label, re.I) for l in cf):
            self.raise_obs("CFS-TAX", self._std("Ind AS 7", "AS 3"), "Cash flows from taxes on income", "Non-compliance",
                           "Operating cash flows are adjusted for the provision for taxation (an accrual) instead of disclosing income taxes actually paid.",
                           "; ".join(l.cite(self.unit) for l in prov) + ".", prov,
                           [self._std("Ind AS 7|cash flows arising from taxes on income shall be separately disclosed",
                                      "AS 3|cash flows arising from taxes on income should be separately disclosed")],
                           "Disclose income taxes paid (net of refunds) under operating activities.", "Medium", area="Cash Flow Statement")
        net = [l for l in cf if re.search(r"increase\s*/?\s*\(?decrease\)?\s*in\s+(long[- ]term\s+)?borrowings|net\s+(proceeds|movement).*borrow", l.label, re.I) and (l.cy or 0)]
        gross = any(re.search(r"proceeds from|repayment of", l.label, re.I) for l in cf)
        if net and not gross:
            self.raise_obs("CFS-NETTING", self._std("Ind AS 7", "AS 3"), "Gross presentation of financing cash flows", "Potential concern",
                           "Borrowings are presented in the cash flow statement as a net increase / decrease. Proceeds and repayments of term borrowings "
                           "are major classes of gross cash flows and are reported separately unless the net-reporting exceptions apply.",
                           "; ".join(l.cite(self.unit) for l in net) + ".", net,
                           [self._std("Ind AS 7|shall report separately major classes of gross cash receipts and gross cash payments arising from investing and financing",
                                      "AS 3|should report separately major classes of gross cash receipts and gross cash payments arising from investing and financing")],
                           "Present proceeds from and repayment of borrowings separately.", "Low", area="Cash Flow Statement")
