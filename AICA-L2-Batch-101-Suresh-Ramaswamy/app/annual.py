"""Year-to-date view and annual reconciliation (FY) built from the returns already stored for a client.

Every return (project) of the client is rebuilt exactly as the GSTR-1 Summary tab builds it, then the months of one
financial year are put side by side:
  * YTD grid           - month-wise taxable value / tax by section, documents, flags for missing or unusual months
  * 3B / books check   - GSTR-3B and books figures are typed in by the user (kept per client and FY) and compared
  * GSTR-9 helper      - the FY totals arranged like GSTR-9 Tables 4 and 5 (a worksheet, not a filed return)
"""
import json
from collections import OrderedDict
from decimal import Decimal
from typing import Dict, List

from . import gstr1
from .classifier import classify_all
from .exporters import derive_docs
from .utils import D, q2, ZERO

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]
FY_MONTHS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]          # April .. March
TAX = ("igst", "cgst", "sgst", "cess")
NUM = ("taxable",) + TAX
ENTRY_KEYS = ("tb_taxable", "tb_igst", "tb_cgst", "tb_sgst", "tb_cess", "bk_taxable")
ENTRY_LABELS = {"tb_taxable": "GSTR-3B outward value: 3.1(a)+(b)+(c)+(e)", "tb_igst": "GSTR-3B IGST",
                "tb_cgst": "GSTR-3B CGST", "tb_sgst": "GSTR-3B SGST/UTGST", "tb_cess": "GSTR-3B Cess",
                "bk_taxable": "Books / sales register taxable value (net of credit notes)"}

# GSTR-9 worksheet rows -> how they are made from the GSTR-1 tables
G9_ROWS = [
    ("4A", "Supplies to unregistered persons (B2C)"),
    ("4B", "Supplies to registered persons (B2B)"),
    ("4C", "Zero rated supply (export) on payment of tax"),
    ("4D", "Supply to SEZs on payment of tax"),
    ("4E", "Deemed exports"),
    ("4F", "Advances on which tax is paid but invoice not issued (net: received - adjusted)"),
    ("4I", "Credit notes issued"),
    ("4J", "Debit notes issued"),
    ("5A", "Zero rated supply (export) without payment of tax"),
    ("5B", "Supply to SEZs without payment of tax"),
    ("5D", "Exempted (other than nil rated / non-GST)"),
    ("5E", "Nil rated"),
    ("5F", "Non-GST supply"),
]


def zero_row():
    return {k: ZERO for k in NUM}


def fy_label_start(fy: str) -> int:
    return int(str(fy)[:4])


def fy_of_month(fy: str, month: int) -> int:
    """Calendar year of a month inside the FY (April-December = start year, January-March = start year + 1)."""
    s = fy_label_start(fy)
    return s if month >= 4 else s + 1


def previous_fy(fy: str) -> str:
    s = fy_label_start(fy) - 1
    return f"{s}-{str(s + 1)[-2:]}"


def load_outputs(db, client: dict, project: dict, settings: dict, schema: dict) -> dict:
    """Same tables / summary the GSTR-1 Summary tab shows for one stored return."""
    pid = project["id"]
    lines = db.load_lines(pid)
    sets = db.datasets(pid)
    docs = db.load_docs(pid)
    classify_all(lines, settings)
    if not docs and (lines or sets):
        docs = derive_docs(lines, sets)
    pre, final = gstr1.build_tables(lines, sets, client, settings, schema)
    summary = gstr1.summarize(final, client["gstin"][:2], schema)
    return {"lines": lines, "sets": sets, "docs": docs, "pre": pre, "final": final, "summary": summary}


def _add(d, x, sign=1):
    for k in NUM:
        d[k] += sign * x[k]


def metrics(out: dict, own_state: str) -> dict:
    """Month figures in the buckets used by the YTD grid and the GSTR-9 worksheet."""
    final = out["final"]
    m = {k: zero_row() for k in ("b2b", "b2cl", "b2cs", "exp", "cdn", "nilex", "total", "g9_4A", "g9_4B", "g9_4C",
                                  "g9_4D", "g9_4E", "g9_4F", "g9_4I", "g9_4J", "g9_5A", "g9_5B")}
    for key in ("b2b", "b2cl", "b2cs", "exp", "cdnr", "cdnur"):
        for r in final.get(key, []):
            x = gstr1.row_tax(key, r, own_state)
            bucket = "cdn" if key in ("cdnr", "cdnur") else key
            _add(m[bucket], x)
            _add(m["total"], x)
            if key == "b2b":
                it = r.get("invoice_type", "")
                g = {"SEZ supplies with payment": "g9_4D", "SEZ supplies without payment": "g9_5B",
                     "Deemed Exp": "g9_4E"}.get(it, "g9_4B")
                _add(m[g], x)
            elif key in ("b2cl", "b2cs"):
                _add(m["g9_4A"], x)
            elif key == "exp":
                _add(m["g9_5A" if r.get("export_type") == "WOPAY" else "g9_4C"], x)
            else:                                           # credit / debit notes (credit already negative)
                if r.get("note_type") == "C":
                    _add(m["g9_4I"], x, -1)                  # shown as a positive credit-note value
                else:
                    _add(m["g9_4J"], x)
    for key, sign in (("at", 1), ("atadj", -1)):
        for r in final.get(key, []):
            _add(m["g9_4F"], gstr1.row_tax(key, r, own_state), sign)
    nil = {"nil_rated": ZERO, "exempted": ZERO, "non_gst": ZERO}
    for r in final.get("exemp", []):
        for s in nil:
            nil[s] += D(r.get(s))
    m["nilex"]["taxable"] = sum(nil.values(), ZERO)
    m["g9_5E"] = {**zero_row(), "taxable": nil["nil_rated"]}
    m["g9_5D"] = {**zero_row(), "taxable": nil["exempted"]}
    m["g9_5F"] = {**zero_row(), "taxable": nil["non_gst"]}
    m["hsn_taxable"] = sum((D(r.get("taxable")) for r in final.get("hsn", [])), ZERO)
    m["amend_rows"] = sum(len(final.get(k, [])) for k in gstr1.TABLE_META if gstr1.TABLE_META[k].get("amend"))
    docs = out["docs"]
    inv = [d for d in docs if d.nature == "Invoices for outward supply"]
    m["docs_total"] = sum(d.total for d in inv)
    m["docs_cancelled"] = sum(d.cancelled for d in inv)
    m["docs_cn"] = sum(d.total for d in docs if d.nature == "Credit Note")
    m["docs_dn"] = sum(d.total for d in docs if d.nature == "Debit Note")
    m["lines"] = len(out["lines"])
    m["rows"] = sum(len(v) for v in final.values())
    return m


ANNUAL_KEY = "annual"          # year-level figures typed by the user, kept with the monthly entries
NINEC_FIELDS = [
    ("fs_turnover", "GSTR-9C Table 5A - turnover as per audited annual financial statements"),
    ("c9_adj", "GSTR-9C Table 5B to 5P - net reconciling items (+ adds, - reduces) to reach the turnover as per GST"),
]


def entries_key(client_id: int, fy: str) -> str:
    return f"annual_entries_{client_id}_{fy}"


def load_entries(db, client_id: int, fy: str) -> dict:
    try:
        return json.loads(db.get_settings().get(entries_key(client_id, fy), "{}") or "{}")
    except Exception:   # noqa
        return {}


def save_entries(db, client_id: int, fy: str, entries: dict):
    db.set_setting(entries_key(client_id, fy), json.dumps(entries))


def build_year(db, client: dict, fy: str, settings: dict, schema: dict) -> dict:
    """-> {"months": [row...], "total": row, "g9": [...], "flags": [...]}; one row per month of the FY."""
    own = client["gstin"][:2]
    projects = {(p["month"], p["year"]): p for p in db.projects(client["id"]) if p.get("fy") == fy}
    entries = load_entries(db, client["id"], fy)
    qrmp = str(client.get("return_type", "")).lower().startswith("quarterly")
    rows, flags = [], []
    tot = {"b2b": zero_row(), "b2cl": zero_row(), "b2cs": zero_row(), "exp": zero_row(), "cdn": zero_row(),
           "total": zero_row(), "nilex": zero_row()}
    g9 = OrderedDict((c, zero_row()) for c, _ in G9_ROWS)
    totals = {"docs_total": 0, "docs_cancelled": 0, "hsn_taxable": ZERO, "amend_rows": 0}
    for mo in FY_MONTHS:
        yr = fy_of_month(fy, mo)
        p = projects.get((mo, yr))
        row = {"month": mo, "year": yr, "label": f"{MONTH_NAMES[mo - 1][:3]} {yr}", "pid": p["id"] if p else None,
               "has_data": False, "m": None, "entry": entries.get(f"{yr}-{mo:02d}", {}), "flags": []}
        if p:
            out = load_outputs(db, client, p, settings, schema)
            m = metrics(out, own)
            row["m"] = m
            row["has_data"] = bool(m["rows"])
            row["csv_status"] = p.get("csv_status", "")
            if row["has_data"]:
                for k in tot:
                    _add(tot[k], m[k])
                for c, _ in G9_ROWS:
                    _add(g9[c], m["g9_" + c])
                for k in totals:
                    totals[k] += m[k]
        rows.append(row)
    # ---- flags
    have = [r for r in rows if r["has_data"]]
    first = rows.index(have[0]) if have else 0
    last = rows.index(have[-1]) if have else -1
    avg = (sum((r["m"]["total"]["taxable"] for r in have), ZERO) / len(have)) if have else ZERO
    for i, r in enumerate(rows):
        if r["has_data"]:
            m = r["m"]
            if avg > 0 and (m["total"]["taxable"] < avg * Decimal("0.5") or m["total"]["taxable"] > avg * Decimal("1.5")):
                r["flags"].append("Taxable value is more than 50% away from the monthly average - check the files")
            if m["docs_total"] == 0 and m["total"]["taxable"] != 0:
                r["flags"].append("No document series (Table 13)")
            if m["hsn_taxable"] and abs(m["hsn_taxable"] - (m["total"]["taxable"] + m["nilex"]["taxable"])) > Decimal("5"):
                r["flags"].append("HSN taxable value differs from outward supplies")
            if m["amend_rows"]:
                r["flags"].append(f"{m['amend_rows']} amendment row(s) - differential not computed")
        elif have and first < i < last and not qrmp:
            r["flags"].append("No data between months that have data - upload the missing month")
        e = r["entry"]
        if r["has_data"] and e.get("tb_taxable") not in (None, ""):
            d = r["m"]["total"]["taxable"] + r["m"]["nilex"]["taxable"] - D(e.get("tb_taxable"))
            if abs(d) > Decimal("1"):
                r["flags"].append(f"GSTR-1 vs GSTR-3B taxable value differs by {q2(d):,}")
    return {"fy": fy, "months": rows, "tot": tot, "g9": g9, "totals": totals, "qrmp": qrmp, "avg": q2(avg)}


def month_columns(r):
    """Flat numbers for a month row (zeros when there is no data)."""
    z = zero_row()
    m = r["m"] if r["has_data"] else None
    g = lambda k: (m[k] if m else z)   # noqa: E731
    return {"b2b": g("b2b"), "b2cl": g("b2cl"), "b2cs": g("b2cs"), "exp": g("exp"), "cdn": g("cdn"),
            "total": g("total"), "nilex": g("nilex")}


def diff_rows(year: dict) -> List[dict]:
    """GSTR-1 vs GSTR-3B vs books, month by month."""
    out = []
    t = {k: ZERO for k in ("g1_tax", "g1_taxable", "tb_taxable", "tb_tax", "bk_taxable")}
    for r in year["months"]:
        e = r["entry"]
        g1 = r["m"]["total"] if r["has_data"] else zero_row()
        g1_tax = g1["igst"] + g1["cgst"] + g1["sgst"] + g1["cess"]
        nil = r["m"]["nilex"]["taxable"] if r["has_data"] else ZERO
        tb_tax = sum((D(e.get(k)) for k in ("tb_igst", "tb_cgst", "tb_sgst", "tb_cess")), ZERO)
        row = {"label": r["label"], "g1_taxable": g1["taxable"], "g1_nil": nil, "g1_tax": g1_tax,
               "tb_taxable": D(e.get("tb_taxable")), "tb_tax": tb_tax, "bk_taxable": D(e.get("bk_taxable")),
               "entered": any(str(e.get(k, "")).strip() for k in ENTRY_KEYS), "has_data": r["has_data"]}
        row["d_3b_taxable"] = row["g1_taxable"] + nil - row["tb_taxable"]
        row["d_3b_tax"] = row["g1_tax"] - row["tb_tax"]
        row["d_bk_taxable"] = row["g1_taxable"] + nil - row["bk_taxable"]
        out.append(row)
        for k, v in (("g1_tax", g1_tax), ("g1_taxable", g1["taxable"] + nil), ("tb_taxable", row["tb_taxable"]),
                     ("tb_tax", tb_tax), ("bk_taxable", row["bk_taxable"])):
            t[k] += v
    return out, t


def export_year(path, client: dict, year: dict) -> None:
    """Excel workbook: YTD grid, GSTR-1 vs GSTR-3B vs books, GSTR-9 worksheet."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    head = PatternFill("solid", fgColor="1F3864")
    bold = Font(bold=True)
    white = Font(bold=True, color="FFFFFF")

    def sheet(ws, title, header, rows, widths=None, note=None, money_from=1):
        ws.title = title
        ws.append([f"{client['name']}  |  {client['gstin']}  |  FY {year['fy']}"])
        ws["A1"].font = Font(bold=True, size=12)
        ws.append([title])
        ws.append([])
        ws.append(header)
        for c in ws[4]:
            c.fill, c.font = head, white
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for r in rows:
            ws.append([float(v) if isinstance(v, Decimal) else v for v in r])
        for row in ws.iter_rows(min_row=5):
            for c in row[money_from:]:
                if isinstance(c.value, float):
                    c.number_format = "#,##0.00;[Red]-#,##0.00"
        for i, w in enumerate(widths or [], 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "B5"
        if note:
            ws.append([])
            for n in note:
                ws.append([n])
        last = ws.max_row
        return last

    # ---- 1 YTD
    ws = wb.active
    hdr = ["Month", "B2B taxable", "B2CL taxable", "B2CS taxable", "Exports taxable", "Credit/debit notes (net)",
           "Total taxable (net)", "Nil / exempt / non-GST", "IGST", "CGST", "SGST/UTGST", "Cess", "Total tax",
           "Invoices (Table 13)", "Cancelled", "Credit notes", "Debit notes", "HSN taxable", "Status / flags"]
    rows = []
    tt = {k: ZERO for k in ("tx", "i", "c", "s", "ce")}
    for r in year["months"]:
        cols = month_columns(r)
        m = r["m"] if r["has_data"] else None
        t = cols["total"]
        rows.append([r["label"], cols["b2b"]["taxable"], cols["b2cl"]["taxable"], cols["b2cs"]["taxable"],
                     cols["exp"]["taxable"], cols["cdn"]["taxable"], t["taxable"], cols["nilex"]["taxable"],
                     t["igst"], t["cgst"], t["sgst"], t["cess"], t["igst"] + t["cgst"] + t["sgst"] + t["cess"],
                     m["docs_total"] if m else "", m["docs_cancelled"] if m else "", m["docs_cn"] if m else "",
                     m["docs_dn"] if m else "", m["hsn_taxable"] if m else "",
                     ("; ".join(r["flags"]) if r["flags"] else ("OK" if r["has_data"] else "No return / no data"))])
    T, tot = year["tot"], year["totals"]
    rows.append(["TOTAL (year to date)", T["b2b"]["taxable"], T["b2cl"]["taxable"], T["b2cs"]["taxable"],
                 T["exp"]["taxable"], T["cdn"]["taxable"], T["total"]["taxable"], T["nilex"]["taxable"],
                 T["total"]["igst"], T["total"]["cgst"], T["total"]["sgst"], T["total"]["cess"],
                 sum((T["total"][k] for k in TAX), ZERO), tot["docs_total"], tot["docs_cancelled"], "", "",
                 tot["hsn_taxable"], ""])
    last = sheet(ws, "YTD", hdr, rows, [14] + [14] * 17 + [70],
                 note=["Tax is taxable value x rate from the GSTR-1 data (credit notes negative). Amendment tables carry "
                       "revised values only; the differential is not computed.",
                       "The income details are subject to verification of the filed returns on the GST Portal.",
                       "R Suresh & Associates, Chartered Accountants"])
    for c in ws[last - 3 if False else 5 + len(rows) - 1]:
        c.font = bold

    # ---- 2 3B / books
    ws2 = wb.create_sheet()
    dr, t = diff_rows(year)
    hdr2 = ["Month", "Books (this app) taxable, net", "Books (this app) nil/exempt/non-GST", "Books (this app) tax",
            "GSTR-3B filed outward value 3.1(a)+(b)+(c)+(e)", "GSTR-3B filed tax", "Books of account taxable (typed)",
            "Diff value: Books (taxable + nil/exempt) - 3B", "Diff tax: Books - 3B",
            "Diff: this app - books of account"]
    rows2 = [[d["label"], d["g1_taxable"], d["g1_nil"], d["g1_tax"], d["tb_taxable"] if d["entered"] else "",
              d["tb_tax"] if d["entered"] else "", d["bk_taxable"] or "", d["d_3b_taxable"] if d["entered"] else "",
              d["d_3b_tax"] if d["entered"] else "", d["d_bk_taxable"] if d["bk_taxable"] else ""] for d in dr]
    rows2.append(["TOTAL", t["g1_taxable"] - sum((d["g1_nil"] for d in dr), ZERO), sum((d["g1_nil"] for d in dr), ZERO),
                  t["g1_tax"], t["tb_taxable"], t["tb_tax"], t["bk_taxable"], t["g1_taxable"] - t["tb_taxable"],
                  t["g1_tax"] - t["tb_tax"], t["g1_taxable"] - t["bk_taxable"]])
    sheet(ws2, "Books vs GSTR-3B", hdr2, rows2, [14] + [18] * 9,
          note=["Books (this app) = the figures prepared in this app from the client's files (the GSTR-1 as it should be). "
                "It is NOT the GSTR-1 as filed - the filed GSTR-1 is compared in the sheets '1 Books vs GSTR-1' and "
                "'2 GSTR-1 vs GSTR-3B'. GSTR-3B figures come from the uploaded GSTR-3B PDF or were typed in; the books of "
                "account figure is typed in. A blank means nothing was entered.",
                "Value difference = taxable + nil/exempt/non-GST - GSTR-3B outward value (3.1 a+b+c+e).",
                "R Suresh & Associates, Chartered Accountants"])

    # ---- 3 GSTR-9 worksheet
    ws3 = wb.create_sheet()
    rows3 = []
    for code, label in G9_ROWS:
        v = year["g9"][code]
        rows3.append([code, label, v["taxable"], v["cgst"], v["sgst"], v["igst"], v["cess"]])
    sheet(ws3, "GSTR-9 worksheet", ["Table", "Description", "Taxable value", "Central tax", "State/UT tax",
                                    "Integrated tax", "Cess"], rows3, [8, 70, 18, 16, 16, 16, 14], money_from=2,
          note=["Worksheet only: figures are the totals of the GSTR-1 data for the year, arranged like GSTR-9 Tables 4 and 5.",
                "Amendments (Tables 9A/9C/10 of GSTR-1) are not netted, and amendments made in the next year's GSTR-1 are not "
                "included; add them as GSTR-9 Tables 4K/4L and 10-14 require.",
                "Table 4G (inward supplies on reverse charge), Table 6 (ITC), 7, 8 and 9 come from GSTR-3B / GSTR-2B and "
                "are not produced here.",
                "R Suresh & Associates, Chartered Accountants"])
    wb.save(path)
