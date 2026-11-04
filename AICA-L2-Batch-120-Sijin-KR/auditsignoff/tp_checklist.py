"""Module C - the firm's TP review checklist (Managerial Remuneration / payments to connected persons).

Source: "TP Updated Final Review Checklist - Managerial Remuneration" (sections 1.1 - 1.13). It REPLACES the earlier
TP_Review_Checklist_Excel_updated.xlsx list. Each checklist row has a stable ID (TP-01 ...); the engine functions that already
existed are re-pointed to the rows they test, three new tests were added (remuneration trace, workbook integrity,
method/PLI terminology) and rows that need judgement or documents not yet readable (BIRF, prior-year file) are listed as manual.

applies: both | full (Full Benchmarking Report only, section 1.8) | update (Financial Update only, section 1.12)
Rows 1.14 are checks the firm added after the sample reports; they were kept so that nothing the engine already catches is lost.
"""
from __future__ import annotations
import re

from .models import Result
from .rules_fs import NotRun

# (section, group, check, trace_to, cls, severity, applies, legacy engine checks, new function name or None)
ROWS = [
 # 1.1 Cover
 ("1.1", "Cover Page", "Company name is correct and identical to engagement records, trade licence, audit report and the rest of the report.", "Trade licence; audit report; report body", "A", "Medium", "both", ["TP-01"], None),
 ("1.1", "Cover Page", "Report title is correct: 'Transfer Pricing Benchmark Analysis' or 'Transfer Pricing Financial Update', matching the nature of the engagement.", "Engagement type; body headings", "A", "Medium", "both", ["TP-02"], None),
 ("1.1", "Cover Page", "Financial year / period agrees with report body and audited / draft financial statements.", "Audit report FY", "A", "High", "both", ["TP-03", "TP-63"], None),
 ("1.1", "Cover Page", "Cover picture is relevant to company activity and to the report (no generic or wrong-industry image).", "Licence activities; business description", "C", "Low", "both", ["TP-04"], None),
 # 1.2 TOC
 ("1.2", "Table of Contents", "TOC is complete: every Heading 1 / Heading 2 in the document appears in the TOC and vice versa.", "Document headings", "A", "Medium", "both", ["TP-17", "TP-18"], None),
 ("1.2", "Table of Contents", "TOC text matches heading text exactly (spelling, numbering, case).", "Document headings", "A", "Low", "both", [], None),
 ("1.2", "Table of Contents", "TOC page numbers equal actual page numbers in the TP Report - Part 2.", "TP Report - Part 2", "A", "Medium", "both", ["TP-13"], None),
 ("1.2", "Table of Contents", "Annexure titles and start pages agree with the TP Report - Part 2.", "Annexure pages", "A", "Medium", "both", [], None),
 ("1.2", "Table of Contents", "TOC formatting: Times New Roman; heading size 19.5; subheadings size 12; text size 11.", "TOC styles / runs", "A", "Low", "both", [], None),
 # 1.3 Company details
 ("1.3", "Company Details and Source Cross-Check", "Company profile in the report (business description, legal form, incorporation, activities, shareholding, ownership chart, group structure, management) agrees with the notes to accounts of the audit report.", "Audit report; notes", "B", "Medium", "both", [], None),
 ("1.3", "Company Details and Source Cross-Check", "Company details agree with the trade licence (licence number, legal name, legal form, address, manager / owners). Licence is valid for the whole period under review and its licensed activities cover the business described in the report.", "Trade licence (issue / expiry dates, activity list)", "A", "High", "both", ["TP-55", "TP-69"], None),
 ("1.3", "Company Details and Source Cross-Check", "Financial figures in report agree with audited / draft FS.", "Audit report", "A", "High", "both", ["TP-35"], None),
 ("1.3", "Company Details and Source Cross-Check", "Financial period in audit report aligns with the period in the Word report.", "Audit report", "A", "High", "both", ["TP-29"], None),
 ("1.3", "Company Details and Source Cross-Check", "Total managerial remuneration stated in report traces to the notes to accounts of the draft / final audit report.", "Audit report notes", "A", "High", "both", [], "rem_trace"),
 ("1.3", "Company Details and Source Cross-Check", "Functional analysis (functions, assets, risks) of the tested party is complete and consistent with the business description, and the report explains why this entity is the tested party.", "Report functional analysis; notes", "C", "Medium", "both", [], None),
 ("1.3", "Company Details and Source Cross-Check", "Remuneration split by component (salary, bonus, allowances, end-of-service benefits, share-based pay, benefits in kind, if any) agrees with the BIRF, and the components add up to the total in the report and notes.", "BIRF; audit report notes", "B", "High", "both", [], None),
 # 1.4 Formatting
 ("1.4", "Formatting (Template Compliance)", "Body text: Times New Roman 11; alignment, indentation, line spacing per approved template.", "Word docx", "A", "Low", "both", ["TP-06", "TP-07", "TP-09"], None),
 ("1.4", "Formatting (Template Compliance)", "Main headings: Times New Roman 19.5; bolding, alignment, spacing, numbering per template.", "Word docx", "B", "Low", "both", ["TP-08"], None),
 ("1.4", "Formatting (Template Compliance)", "Subheadings: Times New Roman 12; bolding, alignment, spacing, numbering per template.", "Word docx", "B", "Low", "both", [], None),
 ("1.4", "Formatting (Template Compliance)", "Tables: Times New Roman 11; headings, alignment, borders, decimal places and units per template.", "Word docx", "B", "Low", "both", ["TP-10"], None),
 ("1.4", "Formatting (Template Compliance)", "Header: 'Transfer Pricing Benchmarking Analysis'; page number at right as dynamic PAGE field. Font TNR 11.", "Word docx", "A", "Low", "both", ["TP-11", "TP-12"], None),
 ("1.4", "Formatting (Template Compliance)", "Footer: approved firm name at right; font TNR 11.", "Word docx", "A", "Medium", "both", ["TP-14", "TP-15"], None),
 ("1.4", "Formatting (Template Compliance)", "Page border: prescribed style, colour; width 1.5 pt (w:sz = 12); on all applicable pages including annexures; same position.", "pgBorders for each section of Word docx", "A", "Low", "both", ["TP-16", "TP-27"], None),
 ("1.4", "Formatting (Template Compliance)", "Editable annexure content (embedded Excel, scanned documents, images): TNR 11 for editable text; visual inspection of objects.", "Embeddings", "B", "Medium", "both", ["TP-26"], None),
 # 1.5 Annexures
 ("1.5", "Annexures and Appendix Mapping", "Each annexure referred to in text exists in the appendix and is numbered sequentially without gaps or duplicates.", "Appendix", "A", "Medium", "both", ["TP-20", "TP-21", "TP-23", "TP-70"], None),
 ("1.5", "Annexures and Appendix Mapping", "Each annexure traces to a specific sheet in the Excel workbook (sheet name, range, values).", "Excel sheets", "A", "High", "both", ["TP-22", "TP-28"], None),
 ("1.5", "Annexures and Appendix Mapping", "Correct Excel file is embedded as object in appendix (compare embedded file hash, sheet names and key values to the submitted workbook).", "word/embeddings", "A", "High", "both", ["TP-24"], None),
 # 1.6 PLI
 ("1.6", "PLI Selection and Computation", "PLI chosen is appropriate for managerial remuneration under TNMM (commonly OP/OR, OP/OC or EC/OC) and its rationale is stated.", "Report; workbook", "C", "Medium", "both", [], None),
 ("1.6", "PLI Selection and Computation", "Operating Profit traces to P&L of final / draft audit report.", "Audit report P&L", "A", "High", "both", ["TP-30"], None),
 ("1.6", "PLI Selection and Computation", "Operating Costs = COS / COGS + operating expenses per audit report; non-operating and financing items excluded as per policy.", "Audit report P&L", "A", "High", "both", ["TP-31"], None),
 ("1.6", "PLI Selection and Computation", "Employee Costs include salaries, managerial remuneration, allowances, benefits and other staff costs, assessed by nature rather than caption; recomputed where aggregated.", "P&L; notes", "B", "Medium", "both", ["TP-32", "TP-34"], None),
 ("1.6", "PLI Selection and Computation", "Operating Revenue traces to revenue figure in P&L.", "Audit report P&L", "B", "High", "both", ["TP-36"], None),
 ("1.6", "PLI Selection and Computation", "Tested party PLI recomputed independently and agrees with word report.", "Report", "A", "High", "both", ["TP-37", "TP-38", "TP-33"], None),
 # 1.7 Workbook integrity
 ("1.7", "Workbook Integrity (Both Report Types)", "PLI formulas are live (no hard-coded values); no broken references, hidden rows / sheets, external links or #REF! errors.", "All sheets of Excel", "A", "Medium", "both", [], "workbook_integrity"),
 # 1.8 Full report only
 ("1.8", "Full Benchmarking Report Only", "Search strategy is documented, logical for the tested party and agrees between report and workbook: database name and version, search date, industry codes, geography, size filters, independence criteria, financial years and loss-making treatment.", "Search Excel sheet; report", "B", "High", "full", ["TP-56"], None),
 ("1.8", "Full Benchmarking Report Only", "Screening funnel: the number of companies at each step in the report agrees with the workbook.", "Search Excel sheet", "A", "High", "full", ["TP-65"], None),
 ("1.8", "Full Benchmarking Report Only", "Manual review: a business description has been reviewed for each accepted comparable and is comparable to the tested party's functions.", "Search Excel sheet", "B", "Medium", "full", ["TP-67"], None),
 ("1.8", "Full Benchmarking Report Only", "A reason is recorded for each rejected comparable; rejection criteria are applied consistently.", "Search Excel sheet", "B", "Medium", "full", [], None),
 ("1.8", "Full Benchmarking Report Only", "Data periods: single-year or multi-year averages are stated and applied consistently across report, workbook and PLI computation.", "Search Excel sheet", "B", "Medium", "full", [], None),
 ("1.8", "Full Benchmarking Report Only", "Method rejection: reasons for not using the other OECD methods are stated and logical.", "Word report", "C", "Medium", "full", [], None),
 ("1.8", "Full Benchmarking Report Only", "Secondary method (CUP or other): sources are dated and relevant, and the rationale is logical.", "PDF if available; Word report", "C", "Medium", "full", ["TP-39", "TP-40"], None),
 ("1.8", "Full Benchmarking Report Only", "Data points and rationale in the secondary analysis agree with the Excel workings and the facts stated in the report.", "PDF if available; Word report", "B", "Medium", "full", ["TP-41", "TP-42", "TP-43"], None),
 ("1.8", "Full Benchmarking Report Only", "Secondary method conclusion is consistent with the primary method conclusion.", "Report conclusion", "C", "Medium", "full", [], None),
 # 1.9 Conclusion and statistics
 ("1.9", "Conclusion and Statistics", "Benchmarking results table is included and formatted per template.", "Conclusion section", "A", "Medium", "both", ["TP-44"], None),
 ("1.9", "Conclusion and Statistics", "Number of comparables correctly stated everywhere.", "Excel workbook count", "A", "Medium", "both", ["TP-45"], None),
 ("1.9", "Conclusion and Statistics", "Minimum, Q1, median, Q3, maximum agree with the final approved workbook; no placeholder or illustrative values.", "Excel workbook", "A", "High", "both", ["TP-46", "TP-64"], None),
 ("1.9", "Conclusion and Statistics", "IQR stated as Q1 to Q3 and tested party actual PLI included.", "Report; Excel workbook", "A", "High", "both", ["TP-47"], None),
 ("1.9", "Conclusion and Statistics", "IQR and statistics agree across executive summary, benchmarking analysis, report tables, conclusion page and annexures.", "All locations", "A", "High", "both", ["TP-49"], None),
 ("1.9", "Conclusion and Statistics", "Comparable details (names, number, descriptions, financial data, PLIs) agree with Excel.", "Excel workbook", "A", "High", "both", ["TP-50"], None),
 ("1.9", "Conclusion and Statistics", "Narrative conclusion (within / outside range, adjustment) agrees with results and methodology.", "Calculated result", "B", "Medium", "both", ["TP-48", "TP-68"], None),
 ("1.9", "Conclusion and Statistics", "Amount of disallowance or final conclusion reconciles with overall information (actual remuneration, arm's length amount, difference).", "Word report", "A", "High", "both", ["TP-57", "TP-59"], None),
 # 1.10 Charts
 ("1.10", "Graphs and Charts", "Data points in charts included within report agree with workbook values.", "Chart XML / image on report", "B", "Medium", "both", ["TP-51"], None),
 ("1.10", "Graphs and Charts", "Scale, axis labels, units, period and legend are correct and not misleading.", "Chart", "C", "Medium", "both", [], None),
 ("1.10", "Graphs and Charts", "Chart message agrees with narrative facts in the report.", "Report text", "C", "Medium", "both", [], None),
 # 1.11 Terminology
 ("1.11", "Method and Terminology Consistency", "Method chosen (e.g. TNMM) is mentioned consistently on every page; no references to a different method.", "Full report scan", "B", "Medium", "both", [], "method_terms"),
 ("1.11", "Method and Terminology Consistency", "Tested party, PLI and period are named identically wherever they appear.", "Full report scan", "B", "Medium", "both", [], None),
 ("1.11", "Method and Terminology Consistency", "Abbreviations defined at first use and used consistently.", "Full report scan", "B", "Low", "both", ["TP-05"], None),
 # 1.12 Financial update only
 ("1.12", "Financial Update Only", "Validity: the prior benchmarking is still within the firm's refresh cycle (commonly a full refresh every 3 years; confirm the firm's and the FTA's position).", "Prior report year / period", "C", "High", "update", [], None),
 ("1.12", "Financial Update Only", "Change in facts: new or departed directors, change in role or time commitment, ownership change, restructuring, new pay structure; reflected in the update.", "BIRF; notes; prior report", "C", "Medium", "update", [], None),
 ("1.12", "Financial Update Only", "Previous-year benchmarking report is attached in the last section of the Word report, and the update states that it must be read with that report (named and dated).", "Last section of Word report", "A", "High", "update", ["TP-25"], None),
 ("1.12", "Financial Update Only", "Same search criteria and database; no unexplained change in method, PLI, tested party or search strategy.", "Prior report; current Word report", "B", "Medium", "update", [], None),
 ("1.12", "Financial Update Only", "Rolled-forward data: latest financial year added to each comparable's data (and the oldest year dropped if averaging); extraction date stated.", "Workbook", "B", "Medium", "update", [], None),
 ("1.12", "Financial Update Only", "Same comparables are retained as in the previous year (fuzzy match on names / IDs).", "Prior report; workbook; current Word report", "B", "High", "update", [], None),
 ("1.12", "Financial Update Only", "Previously accepted comparable now dropped: reason is documented and valid, linked to a status change such as acquisition, delisting, loss of independence, change in business or missing data.", "Current Word report; Excel workbook", "C", "High", "update", [], None),
 ("1.12", "Financial Update Only", "Previously rejected comparable now accepted: reason is documented and valid; no cherry-picking.", "Current Word report; Excel workbook", "C", "High", "update", [], None),
 ("1.12", "Financial Update Only", "Range movement: IQR compared with last year, large changes explained, and the tested party's position stated again.", "Both reports", "C", "Medium", "update", [], None),
 ("1.12", "Financial Update Only", "Year-on-year view: movement in remuneration and in any disallowance compared with the prior year and explained.", "Both reports", "C", "Medium", "update", [], None),
 # 1.13 Regulatory
 ("1.13", "Regulatory Content (OECD and UAE CT TP)", "Report covers the expected components per OECD and FTA guidance: entity and industry analysis, controlled transaction description, method selection, comparability analysis and conclusion (functional analysis is checked at 1.3 and method rejection at 1.8).", "OECD TP Guidelines; FTA TP Guide", "C", "Medium", "both", [], None),
 ("1.13", "Regulatory Content (OECD and UAE CT TP)", "Connected person / related party identification is correct and consistent with the notes to accounts and the BIRF.", "Audit report notes; BIRF", "B", "High", "both", [], None),
 ("1.13", "Regulatory Content (OECD and UAE CT TP)", "References to law, guidelines and thresholds are current.", "Latest FTA / MoF publications", "C", "Medium", "both", [], None),
 ("1.13", "Regulatory Content (OECD and UAE CT TP)", "Whether the related-party disclosure threshold is met (confirm current FTA thresholds).", "FTA thresholds", "A", "High", "both", ["TP-58"], None),
 # 1.14 retained firm-added checks
 ("1.14", "Firm-added checks (retained)", "Continuation labels appear on continued headings/tables where required and nowhere else.", "Report", "B", "Low", "both", ["TP-19"], None),
 ("1.14", "Firm-added checks (retained)", "No unfinished text (XXXX, TBC, [ ], date without year) in the issued report.", "Report", "A", "High", "both", ["TP-60"], None),
 ("1.14", "Firm-added checks (retained)", "No doubled titles or repeated words (e.g. Mr. Mr.).", "Report", "A", "Low", "both", ["TP-61"], None),
 ("1.14", "Firm-added checks (retained)", "No DRAFT watermark or legend in the issued version.", "Report", "A", "High", "both", ["TP-62"], None),
 ("1.14", "Firm-added checks (retained)", "Regions claimed in the narrative agree to the exchanges/countries of the accepted comparables.", "Report", "A", "High", "both", ["TP-66"], None),
 ("1.14", "Firm-added checks (retained)", "Final Word and PDF reviewed after conversion (pagination, borders, headers, footers, tables, objects, annexures).", "Final Word and PDF", "C", "Medium", "both", ["TP-52"], None),
 ("1.14", "Firm-added checks (retained)", "All material review exceptions resolved or documented.", "Review paper", "C", "High", "both", ["TP-53"], None),
 ("1.14", "Firm-added checks (retained)", "Final approved files saved per the firm's document management procedure.", "Engagement file", "C", "Low", "both", ["TP-54"], None),
]

# rows that were manual in the first build and now have a test (rules_tp3.py)
FN = {5: "toc_complete", 6: "toc_text", 8: "toc_annexures", 9: "toc_format", 10: "profile_vs_fs", 15: "functional", 16: "rem_split_birf", 19: "subheading_format",
      28: "pli_rationale", 38: "rejected_reasons", 39: "data_periods", 40: "method_rejection", 43: "secondary_conclusion", 52: "chart_data", 53: "chart_scale",
      54: "chart_message", 56: "naming_consistency", 58: "validity", 59: "change_in_facts", 61: "same_criteria", 62: "rolled_forward", 63: "comps_retained",
      64: "dropped_reason", 65: "added_reason", 66: "range_movement", 67: "yoy", 68: "components", 69: "connected_persons", 70: "law_refs"}
CHECKS = []          # dicts with id, section, ...
for i, r in enumerate(ROWS, 1):
    fn = FN.get(i) or r[8]
    CHECKS.append({"id": f"TP-{i:02d}", "sec": r[0], "grp": r[1], "check": r[2], "trace": r[3], "cls": r[4], "sev": r[5],
                   "applies": r[6], "legacy": r[7], "fn": fn, "impl": bool(r[7] or fn)})
BY_ID = {c["id"]: c for c in CHECKS}
LEGACY_USED = {l for c in CHECKS for l in c["legacy"]}


# ====================================================================== new tests
def _ex(*a, **k):
    from .rules_tp import _ex as e
    return e(*a, **k)


_AMT = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d{5,})(?:\.\d+)?")


def _amounts(text):
    return [float(m.group(1).replace(",", "")) for m in _AMT.finditer(text)]


def rem_trace(c):
    """Managerial / director remuneration stated in the report must appear in the notes to accounts (PS-15)."""
    from .rules_tp2 import _fs_text
    fs = _fs_text(c)
    rx = re.compile(r"(remuneration|compensation|key management|directors?'? (fees|salar)|managerial)", re.I)

    def near(text):
        out = []
        for ln in re.split(r"\n", text):
            if rx.search(ln):
                out += _amounts(ln)
        return out
    rep = [a for a in near(c.doc.all_text) if not (1990 <= a <= 2100)]
    if not rep:
        raise NotRun("No remuneration amount found in the report text - trace manually")
    fsv = near(fs)
    if not fsv:
        raise NotRun("No remuneration / key management amount found in the audited FS text - trace manually")
    def hit(a):
        return any(abs(a - b) <= max(1.0, 0.005 * b) or abs(a - b * 1000) <= max(1.0, 0.005 * b * 1000) for b in fsv)
    if any(hit(a) for a in rep):
        return []
    return [_ex("TP-14", "Remuneration in the report does not trace to the notes to accounts", "High",
                "None of the remuneration amounts in the report (" + ", ".join(f"{a:,.0f}" for a in sorted(set(rep))[:6]) + ") appears against remuneration / key management lines of the FS ("
                + ", ".join(f"{b:,.0f}" for b in sorted(set(fsv))[:6]) + "). Grey area: the FS may disclose key-management compensation on a wider scope (bonus, EOSB, benefits) than the amount benchmarked; confirm the scope before raising.",
                "Report remuneration vs FS notes", "report amount = note amount (or reconciled)", "no match")]


def workbook_integrity(c):
    """Live formulas, no #REF!, hidden sheets/rows/columns, external links in the benchmarking workbook (PS-08 / 1.7)."""
    if not getattr(c, "wb_path", None):
        raise NotRun("Benchmarking workbook not supplied")
    if str(c.wb_path).lower().endswith(".xls"):
        raise NotRun("Old .xls workbook - save as .xlsx to test formulas")
    import openpyxl
    wb = openpyxl.load_workbook(str(c.wb_path), data_only=False)
    wv = openpyxl.load_workbook(str(c.wb_path), data_only=True)
    out, nform, nconst, hidden, errs = [], 0, 0, [], []
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            hidden.append(f"sheet '{ws.title}' ({ws.sheet_state})")
        hr = [r for r, d in ws.row_dimensions.items() if d.hidden]
        hc = [k for k, d in ws.column_dimensions.items() if d.hidden]
        if hr:
            hidden.append(f"'{ws.title}' rows {', '.join(map(str, hr[:6]))}")
        if hc:
            hidden.append(f"'{ws.title}' columns {', '.join(hc[:6])}")
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, str) and v.startswith("="):
                    nform += 1
                    if "#REF!" in v:
                        errs.append(f"{ws.title}!{cell.coordinate} formula contains #REF!")
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    nconst += 1
                elif isinstance(v, str) and v.strip().startswith("#") and v.strip().rstrip("!?").upper() in ("#REF", "#DIV/0", "#N/A", "#VALUE", "#NAME", "#NUM"):
                    errs.append(f"{ws.title}!{cell.coordinate} shows {v.strip()}")
        for row in wv[ws.title].iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.strip() in ("#REF!", "#DIV/0!", "#N/A", "#VALUE!", "#NAME?", "#NUM!"):
                    errs.append(f"{ws.title}!{cell.coordinate} shows {cell.value.strip()}")
    ext = len(getattr(wb, "_external_links", []) or [])
    loc = Path_name(c.wb_path)
    if errs:
        out.append(_ex("TP-30", "Workbook has error values / broken references", "High", "; ".join(sorted(set(errs))[:8]), loc, "no #REF!/#N/A", f"{len(set(errs))} cell(s)"))
    if ext:
        out.append(_ex("TP-30", "Workbook has external links", "Medium", f"{ext} external link(s): figures may depend on another file that is not in the engagement folder.", loc, "none", ext))
    if hidden:
        out.append(_ex("TP-30", "Hidden sheets / rows / columns in the workbook", "Medium", "; ".join(hidden[:8]) + ". Hidden content must be explained or removed before issue.", loc, "none hidden", f"{len(hidden)}"))
    if nform == 0 and nconst:
        out.append(_ex("TP-30", "Workbook contains no formulas - every figure is hard-coded", "Medium", f"{nconst} numeric constants and no formula: the PLIs and quartiles cannot be re-performed from the file.", loc, "live PLI formulas", "0 formulas"))
    return out


def Path_name(p):
    from pathlib import Path
    return Path(str(p)).name


_METHODS = {"TNMM": r"\bTNMM\b|transactional net margin", "CUP": r"\bCUP\b|comparable uncontrolled price",
            "Comparable Profits Method": r"comparable profits? method|\bCPM\b", "Cost Plus": r"cost[- ]plus method",
            "Resale Price": r"resale price method", "Profit Split": r"profit[- ]split"}
_PLIS = {"OP/OC": r"\bOP\s*/\s*OC\b|operating profit (?:to|/|over|on) operating cost|net cost plus", "OP/OR": r"\bOP\s*/\s*OR\b|operating (?:profit )?margin|operating profit (?:to|/|over|on) operating revenue", "EC/OC": r"\bEC\s*/\s*OC\b"}


def method_terms(c):
    """Assisted: how often each method / PLI name is used and where (PS-13). Rejection discussion legitimately names other methods."""
    t = c.full_text()
    pages = getattr(c.doc, "pages", None) or []
    def count(rx):
        n = len(re.findall(rx, t, re.I))
        pg = [i + 1 for i, p in enumerate(pages) if re.search(rx, p, re.I)][:8] if pages else []
        return n, pg
    m = {k: count(v) for k, v in _METHODS.items()}
    p = {k: count(v) for k, v in _PLIS.items()}
    lines = [f"{k}: {n} mention(s)" + (f", pages {pg}" if pg else "") for k, (n, pg) in {**m, **p}.items() if n]
    primary = [k for k in ("TNMM", "CUP") if m[k][0]]
    note = ("Primary method named in the report: " + (", ".join(primary) if primary else "none found") + ". ")
    if m["Comparable Profits Method"][0]:
        note += "'Comparable Profits Method' is a US term - confirm it is not used as the chosen method. "
    if sum(1 for k in ("OP/OC", "OP/OR") if p[k][0]) > 1:
        note += "Both OP/OC and OP/OR appear - confirm the PLI is named identically in every table. "
    f = _ex("TP-56", "Method / PLI names used in the report", "Info", note + "Counts: " + ("; ".join(lines) or "no method names found"), "Whole report", "one method, one PLI name", "; ".join(lines)[:200])
    return [f]


method_terms.assist = True
FUNCS = {"rem_trace": rem_trace, "workbook_integrity": workbook_integrity, "method_terms": method_terms}
from .rules_tp3 import NEW as _NEW
FUNCS.update(_NEW)


# ====================================================================== mapping engine results -> checklist
def report_kind(c):
    from .rules_tp import _norm
    return "update" if re.search(r"financial update", _norm(c)[:3000], re.I) else "full"


_NA = {"full": "Applies to Full Benchmarking Reports only (section 1.8) - this is a Financial Update",
       "update": "Applies to Financial Updates only (section 1.12) - this is a full benchmarking report"}


def apply_checklist(legacy, ctx):
    """legacy: list[Result] from the engine (old internal ids). Returns Results keyed by the new checklist ids."""
    kind = report_kind(ctx)
    by = {r.check_id: r for r in legacy}
    out = []
    for ck in CHECKS:
        if not ck["impl"]:
            continue
        if ck["applies"] != "both" and ck["applies"] != ("full" if kind == "full" else "update"):
            out.append(Result(ck["id"], "NA", [], _NA[ck["applies"]]))
            continue
        parts = [by[l] for l in ck["legacy"] if l in by]
        if ck["fn"]:
            fn = FUNCS[ck["fn"]]
            try:
                f = fn(ctx)
                m = getattr(fn, "mode", None)
                if getattr(fn, "assist", False) or m == "assist":
                    st_ = "REVIEW"
                elif m == "hybrid":
                    st_ = "EXC" if any(x.severity != "Info" for x in f) else ("REVIEW" if f else "PASS")
                else:
                    st_ = "EXC" if f else "PASS"
                parts.append(Result("new", st_, f))
            except NotRun as e:
                parts.append(Result("new", "NA" if str(e).startswith("Applies to") else "NOTRUN", [], str(e)))
            except Exception as e:
                parts.append(Result("new", "NOTRUN", [], f"Rule could not run on this file: {type(e).__name__}: {str(e)[:120]}"))
        fnds = [f for p in parts for f in p.findings]
        for f in fnds:
            f.check_id = ck["id"]
        st = {p.status for p in parts}
        notes = "; ".join(sorted({p.note for p in parts if p.note and p.status in ("NOTRUN", "NA")}))[:300]
        if "EXC" in st:
            status, note = "EXC", ""
        elif "REVIEW" in st:
            status, note = "REVIEW", "Assisted: evidence extracted, reviewer to confirm"
        elif "PASS" in st:
            status, note = "PASS", ("Partly run: " + notes) if "NOTRUN" in st and notes else ""
        elif "NOTRUN" in st:
            status, note = "NOTRUN", notes
        else:
            status, note = "NA", notes
        out.append(Result(ck["id"], status, fnds, note))
    return out


def catalogue_yaml():
    lines = []
    for ck in CHECKS:
        grp = f"{ck['sec']} {ck['grp']}"
        lines.append('- {id: %s, mod: C, grp: "%s", check: "%s", cls: %s, docs: "%s", sev: %s, src: "TP Updated Final Review Checklist (Managerial Remuneration) %s%s", impl: %s}'
                     % (ck["id"], grp, ck["check"].replace('"', "'"), ck["cls"], ck["trace"].replace('"', "'"), ck["sev"], ck["sec"],
                        "" if ck["applies"] == "both" else (" - full report only" if ck["applies"] == "full" else " - financial update only"),
                        "true" if ck["impl"] else "false"))
    return "\n".join(lines)
