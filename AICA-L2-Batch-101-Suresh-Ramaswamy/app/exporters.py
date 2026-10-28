"""CSV export of all GSTR-1 tables, reports, documents register helpers and output-folder handling."""
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

import pandas as pd

from . import config, gstr1
from .classifier import is_implemented
from .config import SECTIONS
from .models import DocSeries, STATUS_APPROVED
from .schema import load_schema, save_schema, headers_status  # noqa: F401  (re-exported for the UI)
from .utils import D, q2, sha256_file, ZERO
from .validation import Issue, blocking_errors, ERROR


# ---------------------------------------------------------------- documents register
def build_docs(docs: List[DocSeries]) -> List[dict]:
    return [{"nature": d.nature, "from_no": d.from_no, "to_no": d.to_no,
             "total": d.total, "cancelled": d.cancelled} for d in docs]


def derive_docs(lines, sets=None, mode: str = "auto") -> List[DocSeries]:
    """Series worked out from the invoices / notes received (invoice lines and Master Template rows).
    Every gap in the numbering ends a series and starts a new one. Always flagged 'derived' (unverified)."""
    from .series import entries_from_lines, entries_from_sets, build_runs, runs_to_docs, auto_mode
    entries = entries_from_lines(lines) + entries_from_sets(sets)
    m = auto_mode(entries) if mode == "auto" else mode
    return runs_to_docs(build_runs(entries, m), m)


def docs_headers(schema: dict) -> List[str]:
    return [c["header"] for c in schema["tables"]["docs"]["columns"]]


def doc_natures(schema: dict) -> List[str]:
    for c in schema["tables"]["docs"]["columns"]:
        if c["source"] == "nature":
            return c.get("choices", [])
    return []


def write_docs_template(path: Path, schema: dict) -> Path:
    """Blank stand-alone Documents template (Table 13 layout). .csv = headings only; .xlsx = sheet + lists."""
    p = Path(path)
    headers = docs_headers(schema)
    natures = doc_natures(schema)
    if p.suffix.lower() == ".csv":
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)
        return p
    from openpyxl.worksheet.datavalidation import DataValidation
    instructions = pd.DataFrame({"How to fill the 'Documents' sheet": [
        "1. Fill one row per document series. Do not change, delete or reorder the column headings.",
        "2. 'Nature of Document': pick from the drop-down (list on the 'Valid natures' sheet).",
        "3. 'Sr. No. From' / 'Sr. No. To': first and last number of the series exactly as printed, e.g. INV001 / INV100.",
        "4. 'Total Number': all documents issued in the series including cancelled ones. "
        "If left blank it is calculated from the From/To range when the numbers share a prefix.",
        "5. 'Cancelled': documents in the series that were cancelled (leave blank or 0 if none).",
        "6. Use a separate row for each series (different prefix, branch, financial-year series, or document type).",
        "7. Serial numbers must be at most 16 characters. Save the file and upload it with 'Upload Filled Documents File'.",
        "8. Rows are checked on upload; if any row has a problem nothing is imported and the row numbers are listed.",
    ]})
    examples = pd.DataFrame([
        [natures[0] if natures else "", "INV001", "INV100", 100, 2],
        [natures[0] if natures else "", "EXP001", "EXP015", 15, 0],
        ["Credit Note", "CN001", "CN010", 10, 1],
    ], columns=headers)
    with pd.ExcelWriter(p, engine="openpyxl") as xw:
        pd.DataFrame(columns=headers).to_excel(xw, sheet_name="Documents", index=False)
        pd.DataFrame({"Valid values for 'Nature of Document'": natures}).to_excel(xw, sheet_name="Valid natures",
                                                                                   index=False)
        instructions.to_excel(xw, sheet_name="Instructions", index=False)
        examples.to_excel(xw, sheet_name="Examples", index=False)
        ws = xw.book["Documents"]
        for col, width in zip("ABCDE", (62, 18, 18, 14, 12)):
            ws.column_dimensions[col].width = width
        for row in ws.iter_rows(min_row=2, max_row=500, min_col=2, max_col=3):
            for c in row:
                c.number_format = "@"
        dv = DataValidation(type="list", formula1=f"'Valid natures'!$A$2:$A${len(natures) + 1}",
                            allow_blank=True, showErrorMessage=True,
                            errorTitle="Nature of Document", error="Choose a value from the list.")
        ws.add_data_validation(dv)
        dv.add("A2:A500")
        xw.book["Valid natures"].column_dimensions["A"].width = 80
        xw.book["Instructions"].column_dimensions["A"].width = 120
        for col, width in zip("ABCDE", (34, 16, 16, 14, 12)):
            xw.book["Examples"].column_dimensions[col].width = width
    return p


def _cell_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v != v:
            return ""
        if v.is_integer():
            return str(int(v))
    return str(v).strip()


def parse_docs_matrix(matrix, schema: dict, source_name: str = ""):
    """matrix = [(excel_row_number, [cell values])]. Returns (series, problems). Raises ValueError when the
    column headings do not follow the template."""
    headers = docs_headers(schema)
    norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())  # noqa: E731
    hi = None
    for i, (_, vals) in enumerate(matrix[:20]):
        got = {norm(v) for v in vals if _cell_text(v)}
        if sum(1 for h in headers if norm(h) in got) >= 3:
            hi = i
            break
    if hi is None:
        raise ValueError("This file does not follow the Documents template.\nColumn headings not found: "
                         + ", ".join(headers) + "\n\nDownload the sample template and copy your data into it.")
    pos = {}
    for ci, v in enumerate(matrix[hi][1]):
        if _cell_text(v):
            pos.setdefault(norm(v), ci)
    missing = [h for h in headers if norm(h) not in pos]
    if missing:
        raise ValueError("This file does not follow the Documents template.\nMissing column heading(s): "
                         + ", ".join(missing) + "\n\nDownload the sample template and copy your data into it.")
    idx = [pos[norm(h)] for h in headers]
    h_nat, h_from, h_to, h_total, h_can = headers[:5]
    allowed = {n.lower(): n for n in doc_natures(schema)}
    out: List[DocSeries] = []
    problems: List[str] = []
    seen = set()

    def as_int(text, label, rown):
        t = _cell_text(text)
        if t == "":
            return None
        d = D(t, None)
        if d is None or d != d.to_integral() or d < 0:
            problems.append(f"Row {rown}: {label} '{t}' must be a whole number (0 or more)")
            return -1
        return int(d)

    for rown, vals in matrix[hi + 1:]:
        cells = [_cell_text(vals[i]) if i < len(vals) else "" for i in idx]
        if not any(cells):
            continue
        nat_raw, frm, to, tot_raw, can_raw = cells
        n_before = len(problems)
        nat = allowed.get(nat_raw.lower())
        if not nat:
            problems.append(f"Row {rown}: Nature of Document '{nat_raw}' is blank or not an allowed value")
        for lbl, v in ((h_from, frm), (h_to, to)):
            if not v:
                problems.append(f"Row {rown}: {lbl} is blank")
            elif len(v) > 16:
                problems.append(f"Row {rown}: {lbl} '{v}' is longer than 16 characters")
        total = as_int(tot_raw, h_total, rown)
        cancelled = as_int(can_raw, h_can, rown)
        if total is None and frm and to:
            a, b = re.match(r"^(.*?)(\d+)$", frm), re.match(r"^(.*?)(\d+)$", to)
            if a and b and a.group(1) == b.group(1) and int(b.group(2)) >= int(a.group(2)):
                total = int(b.group(2)) - int(a.group(2)) + 1
            else:
                problems.append(f"Row {rown}: {h_total} is blank and cannot be calculated from '{frm}' - '{to}'")
        cancelled = 0 if cancelled is None else cancelled
        if total is not None and total >= 0 and cancelled >= 0 and cancelled > total:
            problems.append(f"Row {rown}: Cancelled ({cancelled}) is more than Total Number ({total})")
        key = (nat, frm.upper(), to.upper())
        if nat and frm and key in seen:
            problems.append(f"Row {rown}: duplicate of an earlier row ({nat}, {frm} - {to})")
        seen.add(key)
        if len(problems) == n_before:
            out.append(DocSeries(nature=nat, from_no=frm, to_no=to, total=total, cancelled=cancelled,
                                 origin="register", source_file=source_name))
    return out, problems


def register_table13(path: Path, schema: dict):
    """If an Excel invoice register (e.g. from Smart Billing) carries a Documents / Table 13 sheet, return
    (series, problems); otherwise None."""
    p = Path(path)
    if p.suffix.lower() not in (".xlsx", ".xlsm", ".xls"):
        return None
    try:
        names = pd.ExcelFile(p).sheet_names
    except Exception:  # noqa
        return None
    if not any(n.strip().lower() == "documents" or "table 13" in n.strip().lower() for n in names):
        return None
    try:
        return read_docs_template(p, schema)
    except ValueError:
        return None


def read_docs_template(path: Path, schema: dict, allow_empty: bool = False):
    """Strictly read a stand-alone Documents file (.xlsx/.csv). Returns (series, problems)."""
    p = Path(path)
    try:
        if p.suffix.lower() == ".csv":
            df = pd.read_csv(p, header=None, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        else:
            xl = pd.ExcelFile(p)
            names = {n.strip().lower(): n for n in xl.sheet_names}
            sheet = (names.get("documents") or names.get("documents issued (table 13)")
                     or next((n for k, n in names.items() if "table 13" in k or k.startswith("documents")), None)
                     or xl.sheet_names[0])
            df = xl.parse(sheet, header=None, dtype=str, keep_default_na=False)
    except Exception as e:  # noqa
        raise ValueError(f"The file could not be opened: {e}")
    matrix = [(i + 1, list(r)) for i, r in enumerate(df.values.tolist())]
    out, problems = parse_docs_matrix(matrix, schema, p.name)
    if not out and not problems and not allow_empty:
        problems.append("The file has no data rows below the headings.")
    return out, problems


# ---------------------------------------------------------------- output folders
def project_dir(client: dict, project: dict, base: Optional[Path] = None) -> Path:
    base = Path(base) if base else config.DATA_ROOT
    fy = "FY_" + project["fy"].replace("-", "_")
    return (base / "clients" / client["gstin"] / fy /
            f"GSTR1_{project['year']}_{project['month']:02d}")


def make_project_folders(client: dict, project: dict, base: Optional[Path] = None) -> Path:
    p = project_dir(client, project, base)
    for sub in ("source_files", "extracted_data", "review_reports", "output"):
        (p / sub).mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------- reports
def issues_frame(issues: List[Issue]) -> pd.DataFrame:
    cols = ["severity", "code", "message", "ref", "source_file", "invoice_no", "action"]
    return pd.DataFrame([{c: getattr(i, c) for c in cols} for i in issues], columns=cols)


def _autowidth(xw):
    for ws in xw.book.worksheets:
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(
                60, max(12, max(len(str(c.value or "")) for c in col) + 2))


def export_exception_report(path: Path, issues: List[Issue], lines) -> Path:
    manual = [{"section": l.section, "section_name": SECTIONS.get(l.section, ("",))[0],
               "source_file": l.source_file, "source_ref": l.source_ref, "invoice_no": l.invoice_no,
               "invoice_date": l.invoice_date, "recipient_gstin": l.recipient_gstin,
               "taxable": str(l.taxable), "igst": str(l.igst), "cgst": str(l.cgst), "sgst": str(l.sgst),
               "status": l.review_status}
              for l in lines if l.review_status != "Rejected" and not is_implemented(l.section)]
    pending = [{"source_file": l.source_file, "source_ref": l.source_ref, "invoice_no": l.invoice_no,
                "status": l.review_status, "note": l.note}
               for l in lines if l.review_status not in (STATUS_APPROVED, "Rejected")]
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        issues_frame(issues).to_excel(xw, sheet_name="Validation issues", index=False)
        pd.DataFrame(manual, columns=["section", "section_name", "source_file", "source_ref", "invoice_no",
                                      "invoice_date", "recipient_gstin", "taxable", "igst", "cgst", "sgst",
                                      "status"]).to_excel(xw, sheet_name="Manual reporting required", index=False)
        pd.DataFrame(pending, columns=["source_file", "source_ref", "invoice_no", "status", "note"]).to_excel(
            xw, sheet_name="Not approved", index=False)
        _autowidth(xw)
    return Path(path)


def export_issue_report(path: Path, issues: List[Issue]) -> Path:
    """Stand-alone issue list (used for template upload problems)."""
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        issues_frame(issues).to_excel(xw, sheet_name="Issues", index=False)
        _autowidth(xw)
    return Path(path)


def summary_frame(summary: List[dict]) -> pd.DataFrame:
    rows = []
    tot = {k: ZERO for k in ("taxable", "igst", "cgst", "sgst", "cess")}
    for s in summary:
        note = ""
        if s["key"] in ("cdnr", "cdnur"):
            note = "Net of credit notes (credit notes negative)"
        elif s["key"] in ("exemp", "hsn"):
            note = "Information table - not part of the tax total"
        elif s["key"] in ("at", "atadj"):
            note = "Tax computed on gross advance - not part of the tax total"
        elif s.get("amend"):
            note = "Revised values only - differential not computed"
        rows.append({"Table": s["title"], "Rows": s["rows"], "Documents": s["docs"], "Taxable value": s["taxable"],
                     "IGST": s["igst"], "CGST": s["cgst"], "SGST/UTGST": s["sgst"], "Cess": s["cess"],
                     "Total": s["total"], "Note": note})
        if s["key"] in ("b2b", "b2cl", "b2cs", "exp", "cdnr", "cdnur"):
            for k in tot:
                tot[k] += s[k]
    rows.append({"Table": "TOTAL - Tables 4, 5, 6A, 7 and 9B (net)", "Rows": "", "Documents": "",
                 "Taxable value": q2(tot["taxable"]), "IGST": q2(tot["igst"]), "CGST": q2(tot["cgst"]),
                 "SGST/UTGST": q2(tot["sgst"]), "Cess": q2(tot["cess"]),
                 "Total": q2(sum(tot.values(), ZERO)), "Note": "Tax is calculated as taxable value x rate"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- export
def export_documents_only(client: dict, project: dict, docs: List[DocSeries], base: Path,
                          confirm_overwrite: Callable[[List[str]], bool] = lambda x: False) -> dict:
    """Write only documents.csv (Table 13) from the document register - no invoices needed."""
    from .validation import validate_all  # local import: avoids a cycle at module load
    if not docs:
        raise ValueError("The document register is empty. Upload the filled Documents file first.")
    schema = load_schema()
    errs = [i for i in validate_all([], client, docs, {}, None) if i.severity == ERROR]
    if errs:
        raise ValueError("Fix these document-register errors first:\n" + "\n".join(i.message for i in errs[:10]))
    root = make_project_folders(client, project, base)
    out = root / "output"
    target = out / schema["tables"]["docs"]["filename"]
    if target.exists() and not confirm_overwrite([target.name]):
        raise ValueError("Export cancelled - the existing file was not overwritten.")
    rows = build_docs(docs)
    gstr1.write_csv(target, "docs", rows, schema)
    return {"file": target, "rows": len(rows), "sha256": sha256_file(target),
            "schema_version": schema["schema_version"],
            "verified": schema.get("verified_against_official_tool", False)}


def export_project(client: dict, project: dict, lines, sets: List[dict], docs: List[DocSeries],
                   issues: List[Issue], settings: dict, base: Optional[Path] = None, override: bool = False,
                   override_reason: str = "",
                   confirm_overwrite: Callable[[List[str]], bool] = lambda x: False) -> dict:
    """Generate every GSTR-1 CSV that has data, plus summary and reports.
    Raises ValueError when blocked (unresolved errors, nothing to export, overwrite refused)."""
    schema = load_schema()
    blocked = blocking_errors(issues, lines)
    if blocked and not (override and override_reason.strip()):
        raise ValueError(f"{len(blocked)} unresolved error(s). Resolve them, or tick the override box and "
                         "record a reason.")
    pre, final = gstr1.build_tables(lines, sets, client, settings, schema)
    summary = gstr1.summarize(final, client["gstin"][:2], schema)
    doc_rows = build_docs(docs)
    if not any(final.values()) and not doc_rows:
        raise ValueError("Nothing to export: no approved invoice lines, no template data and no document register.")
    recon = gstr1.reconcile(lines, pre, final, docs, summary, settings)
    root = make_project_folders(client, project, base)
    out = root / "output"
    tables = schema["tables"]
    targets = {}
    for key in tables:
        rows = doc_rows if key == "docs" else final.get(key, [])
        if rows:
            targets[key] = rows
    files = {k: out / tables[k]["filename"] for k in targets}
    extra = [out / "gstr1_summary.xlsx", out / "validation_report.xlsx", out / "reconciliation_report.xlsx",
             out / "manifest.json"]
    existing = [p.name for p in list(files.values()) + extra if p.exists()]
    if existing and not confirm_overwrite(existing):
        raise ValueError("Export cancelled - existing files were not overwritten.")
    written = {}
    for key, rows in targets.items():
        gstr1.write_csv(files[key], key, rows, schema)
        written[tables[key]["filename"]] = sha256_file(files[key])
    with pd.ExcelWriter(out / "gstr1_summary.xlsx", engine="openpyxl") as xw:
        summary_frame(summary).to_excel(xw, sheet_name="Summary", index=False)
        _autowidth(xw)
    export_exception_report(out / "validation_report.xlsx", issues, lines)
    with pd.ExcelWriter(out / "reconciliation_report.xlsx", engine="openpyxl") as xw:
        pd.DataFrame(recon, columns=["check", "source", "processed", "difference", "status", "note"]).to_excel(
            xw, sheet_name="Reconciliation", index=False)
        _autowidth(xw)
    (root / "extracted_data" / "lines.json").write_text(
        json.dumps([l.to_dict() for l in lines], indent=1), encoding="utf-8")
    n_ver, n_tot, ver_text = headers_status(schema)
    manifest = {
        "generated": datetime.now().isoformat(timespec="seconds"), "gstin": client["gstin"],
        "period": f"{project['month']:02d}/{project['year']}", "schema_version": schema["schema_version"],
        "headers_verified_tables": n_ver, "tables_in_schema": n_tot, "header_status": ver_text,
        "files_sha256": written, "override_used": bool(blocked), "override_reason": override_reason,
        "rows": {k: len(v) for k, v in targets.items()},
        "template_files": [s["filename"] for s in sets], "notice": schema.get("notice", ""),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"folder": out, "files": written, "rows": {k: len(v) for k, v in targets.items()}, "recon": recon,
            "summary": summary, "schema_version": schema["schema_version"], "header_status": ver_text,
            "verified": n_ver == n_tot and n_tot > 0, "overrode": bool(blocked)}
