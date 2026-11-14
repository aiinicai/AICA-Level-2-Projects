"""Draft Financial Statements Marker.

Works on a copy of the uploaded draft financial statements workbook so that the entity's own format
(sheets, layout, fonts, number formats, column widths, formulas) is preserved exactly. The marker only:
  1. Fills in YELLOW the existing line items / note headings affected by a review point and attaches a
     cell comment with the issue ID and the requirement;
  2. Inserts the missing disclosures inside the existing Notes sheet (same columns and fonts as the
     surrounding note text), filled in YELLOW, with amounts left as [___] for management to complete;
  3. Adds one index sheet at the end listing every yellow change (the financial statement sheets are untouched otherwise).
"""

import io
import re
from copy import copy
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

YELLOW = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
BLANK = "[___]"

# Line items / note headings that each review point relates to.
ANCHORS = {
    "ARITH-BS-EQUATION": ["total assets", "total equity and liabilities"],
    "ARITH-CFS-RECON": ["cash and cash equivalents"],
    "SCH3-TP-AGEING": ["trade payables"],
    "SCH3-MSMED-SEC22": ["trade payables"],
    "SCH3-TR-AGEING": ["trade receivables"],
    "SCH3-DIRECTOR-RECEIVABLES": ["trade receivables"],
    "SCH3-CWIP-AGEING": ["capital work-in-progress", "capital work in progress", "cwip"],
    "SCH3-INTANGIBLE-CWIP": ["intangible assets under development"],
    "SCH3-PROMOTER-TABLE": ["share capital"],
    "SCH3-RATIOS-OMISSION": ["ratios"],
    "SCH3-RATIOS-VARIANCE": ["ratios"],
    "SCH3-TITLE-DEEDS": ["property, plant and equipment"],
    "SCH3-ROC-CHARGES": ["borrowings"],
    "SCH3-BANK-RETURNS-RECON": ["borrowings"],
    "SCH3-EARMARKED-BANK": ["cash and cash equivalents", "bank balances"],
    "SCH3-LOANS-TO-PROMOTERS-KMPS": ["loans"],
    "SCH3-ROUNDING-OFF": ["balance sheet as at", "statement of profit and loss"],
    "INDAS-16-PPE-POLICY": ["significant accounting policies", "property, plant and equipment"],
    "INDAS-19-SENSITIVITY": ["employee benefits"],
    "INDAS-19-MORTALITY": ["employee benefits"],
    "INDAS-12-TAX-RECON": ["tax expense"],
    "INDAS-115-DISAGGREGATION": ["revenue from operations"],
    "INDAS-115-CONTRACT-BALANCES": ["revenue from operations"],
    "AS-20-EPS-OMISSION": ["profit for the year", "profit for the period"],
}

# Note in which a missing disclosure is incorporated (matched against note headings).
TARGET_NOTE = {
    "SCH3-TP-AGEING": "trade payables",
    "SCH3-MSMED-SEC22": "trade payables",
    "SCH3-TR-AGEING": "trade receivables",
    "SCH3-DIRECTOR-RECEIVABLES": "trade receivables",
    "SCH3-CWIP-AGEING": "capital work",
    "SCH3-INTANGIBLE-CWIP": "intangible",
    "SCH3-PROMOTER-TABLE": "share capital",
    "SCH3-RATIOS-OMISSION": "ratios",
    "SCH3-RATIOS-VARIANCE": "ratios",
    "SCH3-ROC-CHARGES": "borrowings",
    "SCH3-BANK-RETURNS-RECON": "borrowings",
    "SCH3-EARMARKED-BANK": "cash and",
    "INDAS-19-SENSITIVITY": "employee benefit",
    "INDAS-19-MORTALITY": "employee benefit",
    "INDAS-12-TAX-RECON": "tax",
    "LTB-TERMS": "borrowings",
    "AUDITOR-FEE": "other expenses",
    "EMP-BEN": "employee",
}

# Draft disclosure wording (Schedule III / standard format). Amounts are left blank on purpose.
TEMPLATES = {
    "SCH3-TP-AGEING": [
        "Trade Payables ageing schedule (outstanding for following periods from due date of payment):",
        f"Particulars | Unbilled | Not due | Less than 1 year | 1-2 years | 2-3 years | More than 3 years | Total",
        f"(i) MSME | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK}",
        f"(ii) Others | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK}",
        f"(iii) Disputed dues - MSME | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK}",
        f"(iv) Disputed dues - Others | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK} | {BLANK}",
    ],
    "SCH3-MSMED-SEC22": [
        "Dues to Micro and Small Enterprises (Section 22 of the MSMED Act, 2006):",
        f"(a) Principal amount and interest due thereon remaining unpaid to any supplier at the end of the year: {BLANK}",
        f"(b) Interest paid in terms of Section 16, along with the amount of payment made beyond the appointed day: {BLANK}",
        f"(c) Interest due and payable for the period of delay in making payment (paid beyond appointed day, without interest): {BLANK}",
        f"(d) Interest accrued and remaining unpaid at the end of the year: {BLANK}",
        f"(e) Further interest remaining due and payable in succeeding years until actually paid (disallowable u/s 23): {BLANK}",
    ],
    "SCH3-TR-AGEING": [
        "Trade Receivables ageing schedule (outstanding for following periods from due date of payment):",
        "Particulars | Unbilled | Not due | Less than 6 months | 6 months-1 year | 1-2 years | 2-3 years | More than 3 years | Total",
        f"(i) Undisputed - considered good | {BLANK}",
        f"(ii) Undisputed - which have significant increase in credit risk | {BLANK}",
        f"(iii) Undisputed - credit impaired | {BLANK}",
        f"(iv) Disputed - considered good | {BLANK}",
        f"(v) Disputed - which have significant increase in credit risk | {BLANK}",
        f"(vi) Disputed - credit impaired | {BLANK}",
    ],
    "SCH3-DIRECTOR-RECEIVABLES": [
        f"Debts due by directors or other officers of the company or any of them either severally or jointly with any other person, "
        f"or by firms or private companies in which any director is a partner, director or member: {BLANK} (state 'Nil' if none).",
    ],
    "SCH3-CWIP-AGEING": [
        "Capital Work-in-Progress ageing schedule (amount in CWIP for a period of):",
        "CWIP | Less than 1 year | 1-2 years | 2-3 years | More than 3 years | Total",
        f"Projects in progress | {BLANK}",
        f"Projects temporarily suspended | {BLANK}",
        "For projects whose completion is overdue or has exceeded cost compared to original plan: completion schedule (To be completed in < 1 yr / 1-2 yrs / 2-3 yrs / > 3 yrs).",
    ],
    "SCH3-INTANGIBLE-CWIP": [
        "Intangible assets under development ageing schedule:",
        "Particulars | Less than 1 year | 1-2 years | 2-3 years | More than 3 years | Total",
        f"Projects in progress | {BLANK}",
        f"Projects temporarily suspended | {BLANK}",
    ],
    "SCH3-PROMOTER-TABLE": [
        "Shares held by promoters at the end of the year:",
        "S. No. | Promoter name | No. of shares | % of total shares | % change during the year",
        f"1 | {BLANK} | {BLANK} | {BLANK} | {BLANK}",
    ],
    "SCH3-RATIOS-OMISSION": [
        "Ratios (with numerator, denominator, current year, previous year, % variance and reason for variance > 25%):",
        "Current ratio | Debt-equity ratio | Debt service coverage ratio | Return on equity ratio | Inventory turnover ratio | "
        "Trade receivables turnover ratio | Trade payables turnover ratio | Net capital turnover ratio | Net profit ratio | "
        "Return on capital employed | Return on investment",
    ],
    "SCH3-RATIOS-VARIANCE": [
        f"Reason for change in ratio by more than 25% as compared to the preceding year: {BLANK} (to be given for each such ratio).",
    ],
    "SCH3-TITLE-DEEDS": [
        "Title deeds of immovable properties not held in the name of the company: Relevant line item | Description | Gross carrying value | "
        "Held in the name of | Whether promoter/director or relative/employee | Period held | Reason (state 'Nil' if none).",
    ],
    "SCH3-BENAMI-PROPERTY": [
        "No proceedings have been initiated or are pending against the Company for holding any benami property under the "
        "Benami Transactions (Prohibition) Act, 1988 and the rules made thereunder. [Management to confirm]",
    ],
    "SCH3-BANK-RETURNS-RECON": [
        "Quarterly returns / statements of current assets filed with banks or financial institutions are in agreement with the books of account "
        f"[or: summary of reconciliation and reasons of material discrepancies: {BLANK}].",
    ],
    "SCH3-WILFUL-DEFAULTER": [
        "The Company has not been declared a wilful defaulter by any bank or financial institution or other lender. [Management to confirm]",
    ],
    "SCH3-STRUCK-OFF": [
        "Relationship with struck off companies (Section 248 of the Companies Act, 2013 / Section 560 of the Companies Act, 1956): "
        f"Name | Nature of transactions | Balance outstanding | Relationship - {BLANK} (state 'Nil' if none).",
    ],
    "SCH3-ROC-CHARGES": [
        "There are no charges or satisfaction yet to be registered with the Registrar of Companies beyond the statutory period. [Management to confirm]",
    ],
    "SCH3-LAYERING": [
        "The Company has complied with the number of layers prescribed under clause (87) of Section 2 of the Act read with the "
        "Companies (Restriction on number of Layers) Rules, 2017. [Management to confirm]",
    ],
    "SCH3-LOANS-TO-PROMOTERS-KMPS": [
        "Loans or advances in the nature of loans granted to promoters, directors, KMPs and related parties, repayable on demand or without "
        f"specifying terms or period of repayment: Type of borrower | Amount outstanding | % to total loans - {BLANK} (state 'Nil' if none).",
    ],
    "SCH3-UNDISCLOSED-INCOME": [
        "The Company has no transaction not recorded in the books of account that has been surrendered or disclosed as income during the year "
        "in the tax assessments under the Income Tax Act, 1961. [Management to confirm]",
    ],
    "SCH3-CRYPTO-CURRENCY": [
        "The Company has not traded or invested in crypto currency or virtual currency during the financial year. [Management to confirm]",
    ],
    "SCH3-EARMARKED-BANK": [
        f"Bank balances include: earmarked balances (e.g. unpaid dividend) {BLANK}; balances held as margin money / security against borrowings, "
        f"guarantees and other commitments {BLANK}; bank deposits with more than 12 months maturity {BLANK}.",
    ],
}

TEMPLATES.update({
    "AUDITOR-FEE": [
        "Payments to the auditor:",
        f"(a) As auditor: {BLANK}",
        f"(b) For taxation matters: {BLANK}",
        f"(c) For company law matters: {BLANK}",
        f"(d) For other services: {BLANK}",
        f"(e) For reimbursement of expenses: {BLANK}",
    ],
    "LTB-TERMS": [
        f"Terms of repayment: {BLANK} (repayable on demand / in instalments of {BLANK} from {BLANK}); rate of interest: {BLANK} "
        "(state if interest-free); security: unsecured / {BLANK}. Amounts repayable within twelve months: {BLANK}.",
    ],
    "EMP-BEN": [
        f"Defined benefit plan (gratuity): principal actuarial assumptions - discount rate {BLANK}, salary escalation {BLANK}, "
        f"attrition {BLANK}, mortality table {BLANK}.",
        f"Reconciliation of the defined benefit obligation: opening {BLANK}; current service cost {BLANK}; interest cost {BLANK}; "
        f"benefits paid {BLANK}; actuarial (gain)/loss {BLANK}; closing {BLANK}.",
    ],
})

REGULATORY_CODES = {
    "SCH3-BENAMI-PROPERTY", "SCH3-WILFUL-DEFAULTER", "SCH3-STRUCK-OFF", "SCH3-LAYERING", "SCH3-UNDISCLOSED-INCOME",
    "SCH3-CRYPTO-CURRENCY", "SCH3-TITLE-DEEDS", "SCH3-LOANS-TO-PROMOTERS-KMPS",
}


def _text(v: Any) -> str:
    return str(v).strip().lower() if v is not None else ""


def _is_note_heading(v: Any) -> bool:
    return bool(re.match(r"^\s*note\s*(no\.?)?\s*\d+", _text(v)))


class DraftFSMarker:
    """Marks review points on a copy of the entity's own draft financial statements workbook."""

    @classmethod
    def is_supported(cls, filename: Optional[str]) -> bool:
        return bool(filename) and filename.lower().endswith((".xlsx", ".xlsm"))

    @classmethod
    def mark(cls, source_bytes: bytes, filename: str, issues: List[Dict[str, Any]]) -> Tuple[bytes, List[Dict[str, Any]]]:
        keep_vba = filename.lower().endswith(".xlsm")
        wb = openpyxl.load_workbook(io.BytesIO(source_bytes), keep_vba=keep_vba)
        notes_ws = cls._notes_sheet(wb)
        changes: List[Dict[str, Any]] = []

        regulatory: List[Dict[str, Any]] = []
        new_notes: List[Tuple[Dict[str, Any], List[str]]] = []
        # Phase 1 - highlight the exact rows each observation cites, while row numbers are still the original ones
        for issue in issues:
            if not cls._highlight_evidence(wb, issue, changes):
                cls._highlight_anchors(wb, issue, changes)
        # Phase 2 - incorporate draft wording only where a disclosure is genuinely missing
        for issue in issues:
            code = issue.get("rule_code", "")
            if issue.get("nature", "Disclosure gap") != "Disclosure gap" or notes_ws is None or code == "NOTE-XREF":
                continue
            if code in REGULATORY_CODES:
                regulatory.append(issue)
                continue
            lines = TEMPLATES.get(code) or cls._fallback_lines(issue)
            if not cls._insert_disclosure(wb, issue, lines, changes):
                new_notes.append((issue, lines))

        # Disclosures with no existing note are added after the last existing note, one block per area
        groups: Dict[str, List[Tuple[Dict[str, Any], List[str]]]] = {}
        for issue, lines in new_notes:
            heading = issue.get("sub_title") or re.sub(r"^.*?/\s*", "", issue.get("ref", "")) or issue.get("category", "Disclosure")
            heading = re.sub(r"^(notes to accounts|note on)\s*[-:]?\s*", "", heading, flags=re.I).strip() or "Disclosure"
            groups.setdefault(heading[:1].upper() + heading[1:], []).append((issue, lines))
        if notes_ws is not None and regulatory:
            seen_codes = set()
            for issue in regulatory:
                if issue.get("rule_code") not in seen_codes:
                    seen_codes.add(issue.get("rule_code"))
                    groups.setdefault("Additional Regulatory Information (Schedule III)", []).append(
                        (issue, TEMPLATES.get(issue.get("rule_code"), cls._fallback_lines(issue))))

        for heading, members in groups.items():
            lines = []
            for issue, member_lines in members:
                lines += [f"[{issue.get('issue_id', '')}] {member_lines[0]}"] + member_lines[1:]
            group = {"issue_id": ", ".join(i.get("issue_id", "") for i, _ in members),
                     "description": heading, "statutory_ref": "; ".join(dict.fromkeys(i.get("statutory_ref", "") for i, _ in members))}
            cls._append_note(wb, notes_ws, heading, lines, group, changes)

        # Cells move when rows are inserted, so addresses are read only once all changes are made
        for ch in changes:
            ch["cell"] = ch["cell"].coordinate
        cls._add_index_sheet(wb, changes)
        wb.calculation.fullCalcOnLoad = True
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue(), changes

    # ------------------------------------------------------------------
    @staticmethod
    def _notes_sheet(wb) -> Optional[Any]:
        """The sheet where additional notes are appended: the last notes sheet."""
        sheets = [ws for ws in wb.worksheets if "note" in ws.title.lower()]
        if sheets:
            return sheets[-1]
        for ws in wb.worksheets:
            if any(_is_note_heading(c.value) for row in ws.iter_rows(max_col=2) for c in row):
                return ws
        return None

    @staticmethod
    def _fallback_lines(issue: Dict[str, Any]) -> List[str]:
        return [f"{issue.get('suggested_correction') or issue.get('action', '')}"]

    @classmethod
    def _comment(cls, cell, issue: Dict[str, Any]) -> None:
        body = f"{issue.get('issue_id', '')}: {issue.get('description', '')}\nRef: {issue.get('statutory_ref', '')}"
        if cell.comment:
            body = cell.comment.text + "\n\n" + body
        cell.comment = Comment(body[:1500], "FRR Review")
        cell.comment.width, cell.comment.height = 320, 160

    @classmethod
    def _highlight_evidence(cls, wb, issue: Dict[str, Any], changes: List[Dict[str, Any]]) -> bool:
        """Highlights the rows cited as evidence; returns False when the observation has no located rows."""
        done = False
        for ev in issue.get("evidence", []):
            sheet, row = ev.get("sheet"), ev.get("row") or 0
            if sheet not in wb.sheetnames or row <= 0:
                continue
            ws = wb[sheet]
            cells = [c for c in ws[row] if c.value is not None]
            if not cells:
                continue
            for c in ws[row][: ws.max_column]:
                c.fill = YELLOW
            cls._comment(cells[0], issue)
            changes.append({"issue_id": issue.get("issue_id"), "sheet": sheet, "cell": cells[0],
                            "type": "Existing line highlighted", "text": str(ev.get("text", cells[0].value))[:160],
                            "reference": issue.get("statutory_ref", "")})
            done = True
        return done

    @classmethod
    def _highlight_anchors(cls, wb, issue: Dict[str, Any], changes: List[Dict[str, Any]]) -> None:
        keys = ANCHORS.get(issue.get("rule_code", ""))
        if not keys:
            return
        for ws in wb.worksheets:
            for row in ws.iter_rows(max_col=min(ws.max_column, 3)):
                for cell in row:
                    t = _text(cell.value)
                    if not t or not any(k in t for k in keys):
                        continue
                    if "note" in ws.title.lower() and not _is_note_heading(cell.value):
                        continue
                    for c in ws[cell.row]:
                        if c.value is not None or c.column <= ws.max_column:
                            c.fill = YELLOW
                    cls._comment(cell, issue)
                    changes.append({"issue_id": issue.get("issue_id"), "sheet": ws.title, "cell": cell,
                                    "type": "Existing line highlighted", "text": str(cell.value)[:120],
                                    "reference": issue.get("statutory_ref", "")})
                    break

    @staticmethod
    def _safe_to_insert(wb, ws, at_row: int) -> bool:
        if any(r.max_row >= at_row for r in ws.merged_cells.ranges):
            return False
        title = ws.title.lower()
        for other in wb.worksheets:
            for row in other.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("="):
                        if other is ws and c.row >= at_row:
                            return False
                        if other is not ws and title in c.value.lower():
                            return False
        return True

    @staticmethod
    def _row_text(ws, r: int) -> Tuple[Optional[str], int]:
        """First text cell of a row (notes are often indented into columns B-D) and its column."""
        for col in range(1, min(ws.max_column, 6) + 1):
            v = ws.cell(r, col).value
            if isinstance(v, str) and v.strip():
                return v, col
        return None, 1

    @classmethod
    def _note_block_end(cls, ws, keyword: str) -> Optional[Tuple[int, int, int]]:
        start, col = None, 1
        for r in range(1, ws.max_row + 1):
            v, c = cls._row_text(ws, r)
            if start is None and _is_note_heading(v) and keyword in _text(v):
                start, col = r, c
            elif start is not None and (_is_note_heading(v) or _text(v).startswith("note (additional)")):
                end = r - 1
                while end > start and all(x.value is None for x in ws[end]):
                    end -= 1
                return start, end, col
        return (start, ws.max_row, col) if start else None

    @classmethod
    def _write_lines(cls, ws, at_row: int, lines: List[str], style_row: int, issue: Dict[str, Any],
                     changes: List[Dict[str, Any]], heading: Optional[str] = None, col: int = 1) -> None:
        ref = ws.cell(style_row, col)
        first = lines[0] if lines[0].startswith("[") else f"[{issue.get('issue_id', '')}] {lines[0]}"
        rows = ([heading] if heading else []) + [first] + lines[1:]
        for offset, line in enumerate(rows):
            c = ws.cell(at_row + offset, col, line)
            c.font = copy(ref.font)
            if heading and offset == 0:
                c.font = Font(name=ref.font.name, size=ref.font.size, bold=True)
            c.alignment = copy(ref.alignment) if ref.has_style else Alignment(wrap_text=True, vertical="top")
            c.number_format = ref.number_format
            c.fill = YELLOW
            changes.append({"issue_id": issue.get("issue_id"), "sheet": ws.title, "cell": c,
                            "type": "Disclosure inserted", "text": line[:120], "reference": issue.get("statutory_ref", "")})
        cls._comment(ws.cell(at_row, col), issue)

    @classmethod
    def _insert_disclosure(cls, wb, issue: Dict[str, Any], lines: List[str], changes: List[Dict[str, Any]]) -> bool:
        """Inserts inside the matching existing note (in whichever notes sheet holds it); False when no note can take it."""
        keyword = TARGET_NOTE.get(issue.get("rule_code", ""))
        if not keyword:
            return False
        for ws in wb.worksheets:
            if "index" in ws.title.lower():
                continue
            block = cls._note_block_end(ws, keyword)
            if not block:
                continue
            at = block[1] + 1
            if cls._safe_to_insert(wb, ws, at):
                ws.insert_rows(at, len(lines))
                cls._write_lines(ws, at, lines, block[1], issue, changes, col=block[2])
                return True
        return False

    @classmethod
    def _append_note(cls, wb, ws, heading: str, lines: List[str], issue: Dict[str, Any], changes: List[Dict[str, Any]]) -> None:
        last = ws.max_row
        while last > 1 and all(c.value is None for c in ws[last]):
            last -= 1
        _, col = cls._row_text(ws, last)
        cls._write_lines(ws, last + 2, lines, last, issue, changes, heading=f"Note (Additional): {heading}", col=col)

    @staticmethod
    def _add_index_sheet(wb, changes: List[Dict[str, Any]]) -> None:
        ws = wb.create_sheet("Yellow Changes Index")
        ws.append(["Issue ID", "Sheet", "Cell", "Nature of change", "Line item / disclosure", "Reference"])
        for c in ws[1]:
            c.font = Font(bold=True)
        for ch in changes:
            ws.append([ch["issue_id"], ch["sheet"], ch["cell"], ch["type"], ch["text"], ch["reference"]])
        for i, w in enumerate([14, 22, 8, 24, 70, 60], start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    @staticmethod
    def preview(marked_bytes: bytes, original_bytes: bytes) -> Dict[str, Dict[str, Any]]:
        """Grid of values + yellow flags per sheet for on-screen display (formula results taken from the original)."""
        marked = openpyxl.load_workbook(io.BytesIO(marked_bytes), keep_links=False)
        cached = openpyxl.load_workbook(io.BytesIO(original_bytes), data_only=True, keep_links=False)
        out = {}
        for ws in marked.worksheets:
            if ws.title == "Yellow Changes Index" or re.search(r"trial\s*balance|\btb\b", ws.title, re.I):
                continue                     # working sheets stay in the download but are not previewed
            src = cached[ws.title] if ws.title in cached.sheetnames else None
            grid, yellow = [], []
            for row in ws.iter_rows():
                vals, flags = [], []
                for c in row:
                    v = c.value
                    if isinstance(v, str) and v.startswith("=") and src is not None:
                        v = src.cell(c.row, c.column).value
                    vals.append("" if v is None else v)
                    flags.append(bool(c.fill and c.fill.fill_type == "solid" and str(c.fill.fgColor.rgb).endswith("FFFF00")))
                grid.append(vals)
                yellow.append(flags)
            out[ws.title] = {"grid": grid, "yellow": yellow}
        return out
