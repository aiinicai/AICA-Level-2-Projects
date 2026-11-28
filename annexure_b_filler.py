#!/usr/bin/env python3
"""
GST Refund Annexure-B (RFD-01) filler
=====================================
Reads a Purchase Register (xlsx/xls/csv, all sheets) and fills the ORIGINAL
GST Department GST_REFUND_ANNEXURE_B.xlsb utility, sheet RFD_ANNEXURE_B.

WHY EXCEL COM?
  .xlsb cannot be written by openpyxl/pandas, and re-saving as xlsx/xlsm would
  destroy the utility's macros, validations and formulas. The only reliable way
  to keep the original workbook intact is to drive real Excel (Windows) and
  write values into the existing cells only. Hence: pywin32.

REQUIREMENTS (Windows + desktop MS Excel):
  pip install pandas openpyxl pywin32

USAGE:
  python annexure_b_filler.py ^
      --template GST_REFUND_ANNEXURE_B.xlsb ^
      --register PurchaseRegister.xlsx ^
      --gstin 08ABCDE1234F1Z5 --from-period 042025 --to-period 062025 ^
      --outdir out

  Add --dry-run to only produce the reports (no Excel needed).
  Add --map "invoice_no=Bill No,taxable=Basic Amt" to override column mapping.

NOTHING IS GUESSED: values that cannot be determined from the register are left
blank and listed in the "Manual Review" / "Missing Info" sheets.
"""
import argparse, re, shutil, sys
from pathlib import Path
import pandas as pd

MAX_ROWS = 10000
SHEET = "RFD_ANNEXURE_B"

# ---------------------------------------------------------------- dropdowns
SUPPLY_TYPES = {
    "import of goods": "Import of Goods",
    "import of services": "Import of Services",
    "sez goods": "Import of Goods (Supplies from SEZ to DTA)",
    "sez services": "Import of Services (Supplies from SEZ to DTA)",
    "registered": "Inward Supplies from Registered Persons",
    "rcm registered": "Inward Supplies liable to Reverse Charge (Registered Persons)",
    "rcm unregistered": "Inward Supplies liable to Reverse Charge (Unregistered Persons)",
    "isd": "Inward Supplies from ISD",
}
DOC_TYPES = {"invoice": "Invoice/Bill of Entry", "bill of entry": "Invoice/Bill of Entry",
             "boe": "Invoice/Bill of Entry", "credit note": "Credit Note",
             "debit note": "Debit Note", "cn": "Credit Note", "dn": "Debit Note"}
CATEGORIES = {"inputs": "Inputs", "input": "Inputs", "goods": "Inputs",
              "input services": "Input Services", "services": "Input Services",
              "capital goods": "Capital Goods", "capital": "Capital Goods"}

# ------------------------------------------------- register column aliases
ALIASES = {
    "gstin": ["gstin of supplier", "supplier gstin", "gstin", "gstin/uin", "vendor gstin"],
    "name": ["supplier name", "trade/legal name", "party name", "vendor name", "name of supplier"],
    "invoice_no": ["invoice number", "invoice no", "inv no", "bill no", "document number", "doc no", "bill of entry number"],
    "invoice_date": ["invoice date", "inv date", "bill date", "document date", "doc date"],
    "invoice_value": ["invoice value", "inv value", "bill value", "gross amount", "total amount"],
    "hsn": ["hsn/sac", "hsn", "sac", "hsn code", "sac code"],
    "taxable": ["taxable value", "taxable amount", "basic amount", "taxable"],
    "cgst": ["central tax", "cgst", "cgst amount"],
    "sgst": ["state/ut tax", "state tax", "sgst/utgst", "sgst", "utgst", "sgst amount"],
    "igst": ["integrated tax", "igst", "igst amount"],
    "cess": ["cess", "cess amount"],
    "supply_nature": ["nature of supply", "type of inward supply", "supply type", "purchase type"],
    "rcm": ["reverse charge", "rcm", "rev charge"],
    "doc_type": ["document type", "type of document", "doc type", "voucher type"],
    "category": ["category of input supplies", "category", "input category", "nature of purchase"],
    "port_code": ["port code"],
    "itc_elig": ["itc eligibility", "eligibility of itc", "itc eligible", "eligibility", "itc availability"],
    "inelig_cgst": ["ineligible cgst", "itc ineligible cgst"],
    "inelig_sgst": ["ineligible sgst", "itc ineligible sgst"],
    "inelig_igst": ["ineligible igst", "itc ineligible igst"],
    "inelig_cess": ["ineligible cess", "itc ineligible cess"],
    "section_175": ["section 17(5)", "blocked credit", "blocked under 17(5)", "17(5)"],
    "period": ["return period", "period", "gstr-3b period", "itc period"],
}


def norm(s):
    return re.sub(r"[^a-z0-9/()]+", " ", str(s).lower()).strip()


# ---------------------------------------------------------------- GSTIN check
_CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def gstin_ok(g):
    g = str(g or "").strip().upper()
    if not _RE.match(g):
        return False
    tot = 0
    for i, c in enumerate(g[:14]):
        p = _CH.index(c) * (1 if i % 2 == 0 else 2)
        tot += p // 36 + p % 36
    return _CH[(36 - tot % 36) % 36] == g[14]


# ------------------------------------------------------------ read register
def load_register(path, overrides):
    p = Path(path)
    sheets = (pd.read_excel(p, sheet_name=None, header=None, dtype=object)
              if p.suffix.lower() != ".csv" else {"csv": pd.read_csv(p, header=None, dtype=object)})
    frames, log = [], []
    for sname, raw in sheets.items():
        if raw.empty:
            continue
        # header row = row with most alias hits in first 30 rows
        best, best_i = 0, None
        for i in range(min(30, len(raw))):
            cells = {norm(v) for v in raw.iloc[i].dropna()}
            hits = sum(1 for al in ALIASES.values() if cells & {norm(a) for a in al})
            if hits > best:
                best, best_i = hits, i
        if best < 4:
            log.append(f"Sheet '{sname}': no recognisable header row - SKIPPED (check manually)")
            continue
        df = raw.iloc[best_i + 1:].copy()
        df.columns = [str(c).strip() for c in raw.iloc[best_i]]
        colmap = {}
        for key, al in ALIASES.items():
            if key in overrides:
                colmap[key] = overrides[key]
                continue
            for c in df.columns:
                if norm(c) in {norm(a) for a in al}:
                    colmap[key] = c
                    break
        out = pd.DataFrame({k: df[v] for k, v in colmap.items() if v in df.columns})
        for k in ALIASES:
            if k not in out:
                out[k] = None
        out["src_sheet"] = sname
        out["src_row"] = df.index + 1  # 1-based Excel row in source sheet
        frames.append(out.dropna(how="all", subset=[c for c in ALIASES if c in out]))
        log.append(f"Sheet '{sname}': header row {best_i + 1}, mapped {sorted(colmap)}; "
                   f"unmapped {sorted(set(ALIASES) - set(colmap))}")
    if not frames:
        sys.exit("No usable sheet found in Purchase Register.")
    return pd.concat(frames, ignore_index=True), log


def num(v):
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() in ("", "-"):
            return 0.0
        return round(float(str(v).replace(",", "")), 2)
    except ValueError:
        return float("nan")


def to_date(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return None
    d = pd.to_datetime(v, dayfirst=True, errors="coerce")
    return None if pd.isna(d) else d


def yn(v):
    s = str(v or "").strip().lower()
    return True if s in ("y", "yes", "true", "1") else False if s in ("n", "no", "false", "0") else None


# --------------------------------------------------------------- processing
def process(reg, gstin_applicant, from_p, to_p):
    rows, review, missing = [], [], []

    def flag(i, r, msg, bucket):
        bucket.append({"Source Sheet": r["src_sheet"], "Source Row": r["src_row"],
                       "Invoice No": r["invoice_no"], "Supplier GSTIN": r["gstin"], "Issue": msg})

    fp = pd.Timestamp(int(from_p[2:]), int(from_p[:2]), 1)
    tp = pd.Timestamp(int(to_p[2:]), int(to_p[:2]), 1) + pd.offsets.MonthEnd(0)

    seen = {}
    for i, r in reg.iterrows():
        issues = []
        gst = str(r["gstin"] or "").strip().upper()
        inv = str(r["invoice_no"] or "").strip()
        dt = to_date(r["invoice_date"])
        cg, sg, ig, ce = (num(r[k]) for k in ("cgst", "sgst", "igst", "cess"))
        taxable, invval = num(r["taxable"]), num(r["invoice_value"])
        hsn = re.sub(r"\D", "", str(r["hsn"] or ""))
        if any(pd.isna(x) for x in (cg, sg, ig, ce, taxable, invval)):
            flag(i, r, "Non-numeric amount in a tax/value column", missing)
            continue

        # period filter (use register period if given, else invoice/doc date)
        if dt is None:
            issues.append("Missing/invalid document date")
        elif not (fp <= dt <= tp):
            flag(i, r, f"Document date {dt:%d-%m-%Y} outside {from_p}-{to_p}; "
                       f"kept - confirm ITC availment period (GSTR-3B) before filing", review)

        # document type
        dtp = DOC_TYPES.get(norm(r["doc_type"])) if r["doc_type"] is not None else None
        if not dtp:
            issues.append("Type of Document not identifiable")

        # type of inward supply - only from explicit info
        nat = norm(r["supply_nature"]) if r["supply_nature"] is not None else ""
        rcm = yn(r["rcm"])
        stype = None
        for k, v in SUPPLY_TYPES.items():
            if nat == norm(v) or nat == k:
                stype = v
        if not stype:
            if rcm is True:
                stype = SUPPLY_TYPES["rcm registered"] if gstin_ok(gst) else SUPPLY_TYPES["rcm unregistered"]
            elif rcm is False and gstin_ok(gst):
                stype = SUPPLY_TYPES["registered"]
        if not stype:
            issues.append("Type of Inward Supply not determinable (no nature/RCM info)")

        # category - explicit column, or SAC (99xxxx) => Input Services; else flag
        cat = CATEGORIES.get(norm(r["category"])) if r["category"] is not None else None
        if not cat:
            if hsn.startswith("99"):
                cat = "Input Services"
            else:
                issues.append("Category of Input Supplies not stated (Inputs / Capital Goods?)")

        # identity checks
        if not inv:
            issues.append("Missing invoice number")
        if stype and "Import" not in stype and "Unregistered" not in stype and not gstin_ok(gst):
            issues.append("Supplier GSTIN missing/invalid format or checksum")
        if not hsn:
            issues.append("HSN/SAC missing")
        elif len(hsn) not in (2, 4, 6, 8):
            issues.append(f"HSN/SAC '{hsn}' has unusual length")
        if "Import" in (stype or "") and not str(r["port_code"] or "").strip() and dtp == "Invoice/Bill of Entry":
            issues.append("Port code missing for import")

        # duplicates (same GSTIN+doc no+date+HSN+tax amounts)
        key = (gst, inv, str(dt), hsn, taxable, cg, sg, ig, ce)
        if key in seen:
            flag(i, r, f"Possible DUPLICATE of source row {seen[key]}; both retained - delete one if confirmed", review)
        else:
            seen[key] = r["src_row"]

        # tax-vs-value sanity
        if invval and taxable and abs(invval - (taxable + cg + sg + ig + ce)) > 1.5:
            flag(i, r, f"Invoice value {invval} != taxable+tax {taxable + cg + sg + ig + ce:.2f} "
                       f"(may be multi-line invoice, round-off or non-GST items)", review)

        # ITC eligibility - never assume
        total = round(cg + sg + ig + ce, 2)
        el_txt = norm(r["itc_elig"]) if r["itc_elig"] is not None else ""
        blk_flag = yn(r["section_175"])
        blocked, eligible, el_amt, inel_amt = None, None, None, None
        inel_cols = [num(r[k]) for k in ("inelig_cgst", "inelig_sgst", "inelig_igst", "inelig_cess")]
        if any(r[k] is not None and not pd.isna(r[k]) for k in
               ("inelig_cgst", "inelig_sgst", "inelig_igst", "inelig_cess")):
            inel_amt = round(sum(inel_cols), 2)
            el_amt = round(total - inel_amt, 2)
            eligible = "Yes" if el_amt > 0 else "No"
            blocked = "Yes" if (blk_flag or "17(5)" in el_txt) and inel_amt > 0 else "No" if blk_flag is False else None
            if inel_amt > total + 0.01:
                issues.append("Ineligible ITC exceeds total tax")
        elif "17(5)" in el_txt or "blocked" in el_txt or blk_flag is True:
            blocked, eligible, el_amt, inel_amt = "Yes", "No", 0.0, total
        elif el_txt in ("ineligible", "not eligible", "no", "n"):
            eligible, el_amt, inel_amt = "No", 0.0, total  # blocked status NOT assumed
            issues.append("Ineligible but 17(5) status not stated - confirm Yes/No for 'blocked'")
        elif el_txt in ("eligible", "yes", "y", "inputs", "input services", "capital goods", "all other itc"):
            blocked, eligible, el_amt, inel_amt = "No", "Yes", total, 0.0
        else:
            issues.append("ITC eligibility not determinable from register")

        for m in issues:
            flag(i, r, m, missing if any(w in m for w in ("Missing", "missing", "not stated", "not determinable",
                                                         "not identifiable", "Non-")) else review)

        rows.append({
            "Type of Inward Supply": stype, "Type of Document": dtp, "GSTIN of Supplier": gst or None,
            "Name of Supplier": r["name"], "Document Number": inv,
            "Document Date": dt.strftime("%d-%m-%Y") if dt is not None else None,
            "Port Code": r["port_code"], "Invoice Value": invval, "Category": cat, "HSN/SAC": hsn or None,
            "Central Tax": cg, "State/UT Tax": sg, "Integrated Tax": ig, "Cess": ce, "Total ITC": total,
            "Blocked 17(5)": blocked, "Eligible for ITC": eligible,
            "Eligible ITC": el_amt, "Ineligible ITC": inel_amt,
            "_src": f"{r['src_sheet']}!{r['src_row']}", "_hasissue": bool(issues),
        })
    return pd.DataFrame(rows), pd.DataFrame(review), pd.DataFrame(missing)


# --------------------------------------------------- write into XLSB (Excel)
HDR_KEYS = [  # (substring to find in template header, DataFrame column)
    ("sr", None), ("type of inward", "Type of Inward Supply"), ("type of document", "Type of Document"),
    ("gstin of the supplier", "GSTIN of Supplier"), ("name of the supplier", "Name of Supplier"),
    ("document number", "Document Number"), ("document date", "Document Date"), ("port code", "Port Code"),
    ("invoice value", "Invoice Value"), ("category", "Category"), ("hsn", "HSN/SAC"),
    ("central tax", "Central Tax"), ("state", "State/UT Tax"), ("integrated", "Integrated Tax"),
    ("cess", "Cess"), ("total input tax", "Total ITC"), ("blocked", "Blocked 17(5)"),
    ("eligible for itc", "Eligible for ITC"), ("amount of eligible", "Eligible ITC"),
    ("amount of ineligible", "Ineligible ITC"),
]


def write_xlsb(template, out_path, chunk, gstin, from_p, to_p, start_sr):
    import win32com.client as win32  # Windows + desktop Excel only
    shutil.copy2(template, out_path)
    xl = win32.DispatchEx("Excel.Application")
    xl.Visible, xl.DisplayAlerts = False, False
    try:
        wb = xl.Workbooks.Open(str(Path(out_path).resolve()))
        ws = wb.Worksheets(SHEET)
        used = ws.UsedRange
        # locate header row/cols by text (first 40 rows) - template structure is not altered
        hdr_row, cols = None, {}
        for r in range(1, 41):
            found = {}
            for c in range(1, 40):
                t = norm(ws.Cells(r, c).Value2 or "")
                for sub, col in HDR_KEYS:
                    if col and sub in t and col not in found.values():
                        found[c] = col
                        break
            if len(found) >= 12:
                hdr_row, cols = r, found
                break
        if not hdr_row:
            raise RuntimeError("Could not locate header row in RFD_ANNEXURE_B - pass cell map manually")
        first = hdr_row + 1
        # skip a numbering row such as (1)(2)(3) if present
        while str(ws.Cells(first, min(cols)).Value2 or "").strip().startswith("(") or \
                str(ws.Cells(first, min(cols)).Value2 or "").strip().isdigit() and first < hdr_row + 3 and False:
            first += 1
        # header fields: label -> write in next cell to the right (logged)
        for label, val in (("gstin of the applicant", gstin), ("from return period", from_p),
                           ("to return period", to_p)):
            hit = ws.UsedRange.Find(label, LookAt=2)  # xlPart
            if hit is None:
                print(f"  ! header label '{label}' not found - fill manually")
                continue
            tgt = hit.Offset(1, 0) if hit.Row < hdr_row - 1 and ws.Cells(hit.Row + 1, hit.Column).Value2 is None \
                else hit.Offset(0, 1)
            tgt.NumberFormat = "@"
            tgt.Value2 = val
            print(f"  header '{label}' -> {tgt.Address}")
        n = len(chunk)
        sr_col = next((c for c in range(1, 6) if "sr" in norm(ws.Cells(hdr_row, c).Value2 or "")), None)
        for c, name in cols.items():
            rng = ws.Range(ws.Cells(first, c), ws.Cells(first + n - 1, c))
            vals = [[None if (v is None or (isinstance(v, float) and pd.isna(v))) else v]
                    for v in chunk[name].tolist()]
            if name in ("Document Date", "GSTIN of Supplier", "HSN/SAC", "Document Number", "Port Code"):
                rng.NumberFormat = "@"  # keep DD-MM-YYYY / leading zeros as text
            rng.Value2 = tuple(tuple(v) for v in vals)
        if sr_col:
            rng = ws.Range(ws.Cells(first, sr_col), ws.Cells(first + n - 1, sr_col))
            rng.Value2 = tuple((start_sr + k,) for k in range(n))
        wb.Save()
        wb.Close(False)
    finally:
        xl.Quit()


# ------------------------------------------------------------------ reports
def write_reports(df, review, missing, log, outdir, files):
    p = Path(outdir) / "Annexure_B_Reconciliation_Report.xlsx"
    inv_count = df[["GSTIN of Supplier", "Document Number", "Document Date"]].drop_duplicates().shape[0]
    inv_val = df.drop_duplicates(["GSTIN of Supplier", "Document Number", "Document Date"])["Invoice Value"].sum()
    signed = lambda col: df[col].fillna(0).where(df["Type of Document"] != "Credit Note", -df[col].fillna(0)).sum()
    rec = pd.DataFrame({"Item": [
        "Total line items", "Total unique documents", "Total invoice value (unique docs)",
        "Total CGST", "Total SGST/UTGST", "Total IGST", "Total Cess", "Total ITC (tax)",
        "Total eligible ITC", "Total ineligible ITC", "Lines with undetermined eligibility",
        "Utility files produced", "NOTE"],
        "Value": [len(df), inv_count, round(inv_val, 2), df["Central Tax"].sum().round(2),
                  df["State/UT Tax"].sum().round(2), df["Integrated Tax"].sum().round(2),
                  df["Cess"].sum().round(2), df["Total ITC"].sum().round(2),
                  df["Eligible ITC"].fillna(0).sum().round(2), df["Ineligible ITC"].fillna(0).sum().round(2),
                  int(df["Eligible ITC"].isna().sum()), ", ".join(files),
                  "Amounts shown as per register (credit notes not netted). Eligible+Ineligible = Total ITC only "
                  "for lines where eligibility was determinable. Reversals (Rule 38/42/43, 17(5)) are NOT computed - "
                  "take from GSTR-3B."]})
    with pd.ExcelWriter(p, engine="openpyxl") as xw:
        rec.to_excel(xw, sheet_name="Reconciliation", index=False)
        df.drop(columns=["_hasissue"]).to_excel(xw, sheet_name="Annexure-B Data", index=False)
        (review if not review.empty else pd.DataFrame({"Result": ["None"]})).to_excel(xw, sheet_name="Manual Review", index=False)
        (missing if not missing.empty else pd.DataFrame({"Result": ["None"]})).to_excel(xw, sheet_name="Missing Info", index=False)
        pd.DataFrame({"Processing log": log}).to_excel(xw, sheet_name="Log", index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(
                    60, max(len(str(c.value or "")) for c in col) + 2)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--register", required=True)
    ap.add_argument("--gstin", required=True, help="Applicant GSTIN")
    ap.add_argument("--from-period", required=True, help="MMYYYY")
    ap.add_argument("--to-period", required=True, help="MMYYYY")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--map", default="", help="key=Column,key=Column overrides")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not gstin_ok(a.gstin):
        sys.exit("Applicant GSTIN failed format/checksum validation - please confirm it.")
    for p_ in (a.from_period, a.to_period):
        if not re.fullmatch(r"(0[1-9]|1[0-2])\d{4}", p_):
            sys.exit("Return periods must be MMYYYY.")
    Path(a.outdir).mkdir(exist_ok=True)
    overrides = dict(kv.split("=", 1) for kv in a.map.split(",") if "=" in kv)

    reg, log = load_register(a.register, overrides)
    for l in log:
        print(l)
    df, review, missing = process(reg, a.gstin, a.from_period, a.to_period)
    df = df.sort_values(["Document Date", "Document Number"], kind="stable", na_position="last").reset_index(drop=True)

    files = []
    if not a.dry_run:
        for n, s in enumerate(range(0, len(df), MAX_ROWS), 1):
            out = Path(a.outdir) / f"GST_REFUND_ANNEXURE_B_part{n}.xlsb"
            write_xlsb(a.template, out, df.iloc[s:s + MAX_ROWS], a.gstin, a.from_period, a.to_period, s + 1)
            files.append(out.name)
            print("Written", out)
    rp = write_reports(df, review, missing, log, a.outdir, files)
    print(f"\nReport: {rp}\nLines: {len(df)} | manual review: {len(review)} | missing info: {len(missing)}")
    print("Next: open each .xlsb in Excel, run the utility's own Validate, then Generate JSON.")


if __name__ == "__main__":
    main()
