"""v2.2.22: HSN-wise sales report and date-wise GST output register."""
import os, sys, tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp()); os.environ["CAGST_DATA"] = str(tmp / "data")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from openpyxl import Workbook
from datetime import datetime
from app.extractors import reports
from app.schema import load_schema

wb = Workbook(); ws = wb.active
for r in (["SHOP"], ["addr"], ["HSNwise Sales Report  From 01/09/26 To 30/09/26"], ["Report Generated On"],
          ["ProductCode", "ProductName", "HSN Code", "Tax Rate", "UQC", "Total Quantity", "Base", "SGST", "CGST", "IGST", "CESS", "Total Value"],
          ["1", "A", "30049069", "5% GST", "NOS-NUMBERS", 2, 100, 2.5, 2.5, 0, 0, 105],
          ["2", "B", "30049069", "5% GST", "NOS-NUMBERS", 3, 200, 5, 5, 0, 0, 210],
          ["3", "C", "30049099", "Exempted", "NOS-NUMBERS", 1, 50, 0, 0, 0, 0, 50],
          [None, "Grand Total:", None, None, None, 6, 350, 7.5, 7.5, 0, 0, 365]):
    ws.append(r)
p = tmp / "hsn.xlsx"; wb.save(p)
assert reports.detect_report(p) == reports.HSN_REPORT
t, m = reports.read_hsn_report(p, load_schema())
rows = {(r["hsn"], r["rate"]): r for r in t["hsn"]}
assert len(rows) == 2 and rows[("30049069", "5")]["taxable"] == "300.00" and rows[("30049069", "5")]["qty"] == "5"
assert rows[("30049099", "0")]["taxable"] == "50.00"

wb = Workbook(); ws = wb.active
for r in (["SHOP"], ["addr"], ["GST Output Register  From 01/09/26 To 30/09/26"], ["Report Generated On"], [],
          ["Bill Date", "Series", "Series Description", "BillCount", "From BillNo", "To BillNo", "Exempt", "5% GST Base", "2.5% SGST", "2.5% CGST", "5% IGST Base", "5% IGST", "18% GST Base"],
          [datetime(2026, 9, 1), "C", "C-CASH BILL", 8, "C01002623", "C01002630", 0, 200, 5, 5, 0, 0, 30],
          [datetime(2026, 9, 1), None, "Datewise Total", 8, None, None, 0, 200, 5, 5, 0, 0, 30],
          [datetime(2026, 9, 3), "C", "C-CASH BILL", 3, "C01002632", "C01002634", 50, 100, 2.5, 2.5, 0, 0, 0],
          [datetime(2026, 9, 3), None, "Datewise Total", 3, None, None, 50, 100, 2.5, 2.5, 0, 0, 0],
          [None, None, "Grand Total :", 11, None, None, 50, 300, 7.5, 7.5, 0, 0, 30], [None, None, None, None, None, None, 50]):
    ws.append(r)
p2 = tmp / "reg.xlsx"; wb.save(p2)
assert reports.detect_report(p2) == reports.OUTPUT_REGISTER
t, m, docs = reports.read_output_register(p2, {"gstin": "33DEMOA1234B1ZD"}, load_schema())
b = {r["rate"]: r["taxable"] for r in t["b2cs"]}
assert b == {"5": "300.00", "18": "30.00"} and t["exemp"][0]["exempted"] == "50.00", (b, t)
assert len(docs) == 1 and docs[0].from_no == "C01002623" and docs[0].to_no == "C01002634" and docs[0].total == 12 and docs[0].cancelled == 1, docs
print("ALL v2.2.22 TESTS PASSED")
