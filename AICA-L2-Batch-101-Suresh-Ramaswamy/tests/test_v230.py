"""v2.3.0: year-to-date view, annual reconciliation, HSN placeholder check (synthetic demo files)."""
import glob, os, sys, tempfile
from decimal import Decimal
from pathlib import Path
tmp = Path(tempfile.mkdtemp()); os.environ["CAGST_DATA"] = str(tmp / "data")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import annual, gstr1, config
from app.db import Database
from app.schema import load_schema
from app.services import register_file, extract_file

from openpyxl import Workbook
from datetime import datetime
SHOP = "DEMO MEDICALS"
wb = Workbook(); ws = wb.active
for r in ([SHOP], ["addr"], ["HSNwise Sales Report  From 01/09/26 To 30/09/26"], ["Report Generated On"], [], [],
          ["ProductCode", "ProductName", "HSN Code", "Tax Rate", "UQC", "Total Quantity", "Base", "SGST", "CGST", "IGST", "CESS", "Total Value"],
          ["1", "PRODUCT A", "30049069", "5% GST", "NOS-NUMBERS", 5, 300, 7.5, 7.5, 0, 0, 315],
          ["2", "PRODUCT B", "30049099", "Exempted", "NOS-NUMBERS", 1, 50, 0, 0, 0, 0, 50],
          ["3", "PRODUCT C", "30049099", "18% GST", "NOS-NUMBERS", 1, 30, 2.7, 2.7, 0, 0, 35.4]):
    ws.append(r)
hsn = [str(tmp / "hsn.xlsx")]; wb.save(hsn[0])
wb = Workbook(); ws = wb.active
for r in ([SHOP], ["addr"], ["GST Output Register  From 01/09/26 To 30/09/26"], ["Report Generated On"], [],
          ["Bill Date", "Series", "Series Description", "BillCount", "From BillNo", "To BillNo", "Exempt", "5% GST Base", "2.5% SGST", "2.5% CGST", "5% IGST Base", "5% IGST", "18% GST Base"],
          [datetime(2026, 9, 1), "C", "C-CASH BILL", 8, "C01002623", "C01002630", 0, 200, 5, 5, 0, 0, 30],
          [datetime(2026, 9, 1), None, "Datewise Total", 8, None, None, 0, 200, 5, 5, 0, 0, 30],
          [datetime(2026, 9, 3), "C", "C-CASH BILL", 3, "C01002632", "C01002634", 50, 100, 2.5, 2.5, 0, 0, 0],
          [None, None, "Grand Total :", 11, None, None, 50, 300, 7.5, 7.5, 0, 0, 30]):
    ws.append(r)
reg = [str(tmp / "reg.xlsx")]; wb.save(reg[0])
db = Database(); schema = load_schema(); settings = db.get_settings()
cid = db.save_client(dict(name="Demo Medicals", gstin="33AAAAA0000A1Z5", legal_name="", trade_name="", state_code="33",
                          reg_type="Regular", return_type="Monthly"))
client = [c for c in db.clients() if c["id"] == cid][0]
for (mo, yr) in [(9, 2026), (8, 2026), (4, 2026)]:
    pid = db.create_project(cid, "2026-27", mo, yr, "Monthly", schema.get("version", ""))
    proj = db.get_project(pid)
    for f in (hsn[0], reg[0]):
        fid, msg = register_file(db, client, proj, f)
        res = extract_file(db, client, proj, fid, settings)
        if res.docs:
            db.save_docs(pid, db.load_docs(pid) + res.docs)
y = annual.build_year(db, client, "2026-27", settings, schema)
have = [r["label"] for r in y["months"] if r["has_data"]]
assert have == ["Apr 2026", "Aug 2026", "Sep 2026"], have
sep = [r for r in y["months"] if r["label"] == "Sep 2026"][0]
t = sep["m"]["total"]
assert t["taxable"] == Decimal("330.00"), t                      # B2CS 22,133.81 + 344.58
assert sep["m"]["nilex"]["taxable"] == Decimal("50.00"), sep["m"]["nilex"]
assert sep["m"]["docs_total"] == 12, sep["m"]["docs_total"]
may = [r for r in y["months"] if r["label"] == "May 2026"][0]
assert any("missing" in f.lower() for f in may["flags"]), may["flags"]
assert y["tot"]["total"]["taxable"] == t["taxable"] * 3
# 3B / books entries
annual.save_entries(db, cid, "2026-27", {"2026-09": {"tb_taxable": "380.00", "tb_cgst": "300", "tb_sgst": "300", "bk_taxable": "370"}})
y = annual.build_year(db, client, "2026-27", settings, schema)
dr, tot = annual.diff_rows(y)
s = [d for d in dr if d["label"] == "Sep 2026"][0]
assert s["entered"] and s["d_3b_taxable"] == Decimal("330.00") + Decimal("50.00") - Decimal("380.00"), s
# GSTR-9 worksheet buckets
assert y["g9"]["4A"]["taxable"] == t["taxable"] * 3 and y["g9"]["5E"]["taxable"] + y["g9"]["5D"]["taxable"] == Decimal("150.00"), y["g9"]
# export
out = tmp / "ytd.xlsx"
annual.export_year(out, client, y)
from openpyxl import load_workbook
wb = load_workbook(out)
assert wb.sheetnames == ["YTD", "GSTR-1 vs 3B vs Books", "GSTR-9 worksheet"], wb.sheetnames
# prior year (FY 25-26) with no data must not crash
y0 = annual.build_year(db, client, "2025-26", settings, schema)
assert not any(r["has_data"] for r in y0["months"]) and annual.fy_of_month("2025-26", 1) == 2026
# HSN placeholder
ctx = gstr1.make_ctx(client, db.get_project(db.projects(cid)[0]["id"]), settings, schema)
rows = [dict(hsn="00000002", uqc="NOS-NUMBERS", qty="2", rate="5", taxable="103.76", igst="0", cgst="2.59", sgst="2.59",
             total_value="108.95", __file="x.xlsx", __ref="HSN report: MELAMET CREAM 15GM; SUHAGRA 25 MG")]
iss = gstr1.validate_table("hsn", rows, ctx)
assert any(i.code == "HSN_PLACEHOLDER" and "MELAMET" in i.message for i in iss), [i.code for i in iss]
print("ALL v2.3.0 TESTS PASSED")
