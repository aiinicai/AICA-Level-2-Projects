#!/usr/bin/env python3
"""
run_gst_automation.py - one-click pipeline:  invoice PDFs -> GST summary -> GSTR-1 JSON

    STEP 1  engines/gst_sales_summary.py
            Reads every PDF in "Input Invoices" and writes GST-Sales-Summary.xlsx
            (sheet 1 "Summary", plus "Exceptions" and "Run Notes").

    STEP 2  engines/gstr1_json.py
            Reads SHEET 1 of the Step 1 workbook and writes
              GSTR1_<GSTIN>_<MMYYYY>.json         -> upload on the GST portal
              GSTR1_<GSTIN>_<MMYYYY>_checks.xlsx  -> checks, reconciliation,
                                                     Table 12 HSN, Table 13 docs

The supplier GSTIN and the return period are read from the invoices, so there
is nothing to type. Every run goes to its own dated folder under "Output".

Runs entirely offline. Double-click "Run GST Automation.bat", or:
    python run_gst_automation.py [--input FOLDER] [--period MM-YYYY]
"""

import argparse
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engines import gst_sales_summary as step1   # noqa: E402
from engines import gstr1_json as step2          # noqa: E402

# ------------------------------------------------------------ settings
# Change these only if the client's position is different.
RCM_RATE = 18.0               # rate applied to reverse-charge rows that carry no tax
RCM_MODE = "computed"         # "computed" = rate + tax amounts; "nil" = rate with nil tax
HSN_DIGITS = 4                # 4 if turnover up to Rs 5 crore, 6 if above
JSON_VERSION = "GST3.2.2"     # change only if the portal rejects the file

FAILED_RECORD = {
    "invoice_no": "", "date": None, "party": "EXTRACTION FAILED",
    "party_gstin": "", "hsn": "", "taxable": 0.0, "igst": 0.0, "cgst": 0.0,
    "sgst": 0.0, "cess": 0.0, "invoice_value": 0.0, "printed_total": None,
    "rounding": 0.0, "tax_total": 0.0, "rc_flag": "", "is_rcm": False,
    "remark": "", "rate": "", "pos_code": "", "pos_state": "",
    "supplier_gstin": "",
}


def line(char="-"):
    print("  " + char * 66)


def open_folder(path):
    """Show the output folder in Explorer (skipped when GST_NO_OPEN is set)."""
    if os.name == "nt" and not os.environ.get("GST_NO_OPEN"):
        os.startfile(path)


def list_pdfs(folder):
    """Each PDF once (on Windows *.pdf and *.PDF match the same file)."""
    seen, pdfs = set(), []
    for name in sorted(os.listdir(folder), key=str.lower):
        full = folder / name
        if name.lower().endswith(".pdf") and full.is_file():
            key = os.path.normcase(str(full.resolve()))
            if key not in seen:
                seen.add(key)
                pdfs.append(full)
    return pdfs


def most_common(values):
    values = [v for v in values if v]
    return Counter(values).most_common(1)[0][0] if values else None


def main():
    ap = argparse.ArgumentParser(description="Invoice PDFs -> GST summary -> GSTR-1 JSON")
    ap.add_argument("--input", default=str(HERE / "Input Invoices"),
                    help="folder holding the sales invoice PDFs")
    ap.add_argument("--period", default=None,
                    help="return period MM-YYYY (default: read from the invoice dates)")
    args = ap.parse_args()

    in_dir = Path(args.input)
    print()
    line("=")
    print("    GST AUTOMATION :  Invoice PDFs  ->  GST Summary  ->  GSTR-1 JSON")
    line("=")

    if not in_dir.is_dir():
        in_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n  Created the folder:  {in_dir}")
        print("  Put the month's sales invoice PDFs in it and run again.")
        return 1
    pdfs = list_pdfs(in_dir)
    if not pdfs:
        print(f"\n  No PDF invoices found in:  {in_dir}")
        print("  Put the month's sales invoice PDFs in it and run again.")
        return 1

    run_dir = HERE / "Output" / datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================ STEP 1
    print(f"\n  STEP 1 of 2  -  reading {len(pdfs)} invoice PDF(s)")
    records = []
    for i, path in enumerate(pdfs, 1):
        print(f"    [{i:>3}/{len(pdfs)}] {path.name}")
        try:
            records.append(step1.extract_invoice(str(path)))
        except Exception as exc:                       # one bad PDF must not stop the batch
            rec = dict(FAILED_RECORD, file=path.name, notes=[f"extraction failed: {exc}"])
            records.append(rec)
            print(f"            FAILED - {exc}")

    period = args.period or most_common(
        [r["date"].strftime("%m-%Y") for r in records if r.get("date")])
    supplier = most_common([r.get("supplier_gstin") for r in records])

    issues = step1.validate(records, period)
    summary_path = run_dir / "GST-Sales-Summary.xlsx"
    step1.write_excel(records, issues, str(summary_path), period)

    s1_err = sum(1 for i in issues if i["Severity"] == "Error")
    s1_rev = sum(1 for i in issues if i["Severity"] == "Review")
    taxable = sum(r["taxable"] for r in records)
    tax = sum(r["igst"] + r["cgst"] + r["sgst"] for r in records)
    print()
    print(f"    Summary written   : {summary_path.name}")
    print(f"    Invoices          : {len(records)}")
    print(f"    Taxable value     : {taxable:>15,.2f}")
    print(f"    Total GST         : {tax:>15,.2f}")
    print(f"    Return period     : {period or 'could not be read'}")
    print(f"    Supplier GSTIN    : {supplier or 'could not be read'}")
    print(f"    Errors / Review   : {s1_err} / {s1_rev}   (see the Exceptions sheet)")

    if not supplier or not period:
        print("\n  Cannot go on to Step 2 without the supplier GSTIN and period.")
        print("  Check the Exceptions sheet of the summary.")
        open_folder(run_dir)
        return 1

    # ============================================================ STEP 2
    mmyyyy = period.replace("-", "")
    out_json = run_dir / f"GSTR1_{supplier}_{mmyyyy}.json"
    out_report = run_dir / f"GSTR1_{supplier}_{mmyyyy}_checks.xlsx"
    print(f"\n  STEP 2 of 2  -  building the GSTR-1 JSON from sheet 1 of {summary_path.name}")
    try:
        info = step2.generate(
            summary_path=str(summary_path), out_json=str(out_json),
            out_report=str(out_report), supplier_gstin=supplier, period=mmyyyy,
            sheet_name=None,                      # None = sheet 1 of the Step 1 file
            default_rate=RCM_RATE, rcm_mode=RCM_MODE, version=JSON_VERSION,
            hsn_digits=HSN_DIGITS)
    except ValueError as exc:
        print(f"\n  STEP 2 stopped: {exc}")
        open_folder(run_dir)
        return 1

    print(f"    Rows read         : {info['read']}")
    print(f"    In the JSON       : {info['included']}  ({info['recipients']} recipient GSTINs)")
    print(f"    Taxable in JSON   : {info['taxable']:>15,.2f}")
    print(f"    Tax in JSON       : {info['tax']:>15,.2f}")
    print(f"    Errors / Warnings : {len(info['errors'])} / {len(info['warnings'])}"
          f"   (see the Checks sheet)")
    for issue in info["errors"][:10]:
        print(f"      ERROR  {issue.invno}: {issue.message}")

    print()
    line("=")
    if info["json_written"]:
        print(f"    DONE.  JSON ready:  {out_json.name}")
        print("    Upload: gst.gov.in > Returns Dashboard > GSTR-1 > Prepare Offline > Upload")
        print("    Table 12 (HSN) and Table 13 (documents) are in the _checks workbook -")
        print("    key them on the portal, then compare the portal summary with the")
        print("    Reconciliation sheet before filing.")
    else:
        print("    NO JSON WRITTEN - fix the rows listed as Error on the Checks sheet,")
        print("    correct the invoices (or the summary) and run again.")
    line("=")
    print(f"\n  All files are in:\n    {run_dir}\n")
    open_folder(run_dir)
    return 0 if info["json_written"] else 1


if __name__ == "__main__":
    sys.exit(main())
