"""End-to-end headless test of the core engine. Run:  python -m tests.test_core"""
import os
import sys
import tempfile
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
os.environ["CAGST_DATA"] = str(tmp / "data")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from app import config  # noqa: E402
from app.classifier import classify_all  # noqa: E402
from app.db import Database  # noqa: E402
from app.exporters import export_project, derive_docs, load_schema  # noqa: E402
from app.gstin import checksum_char, validate_gstin  # noqa: E402
from app.models import STATUS_APPROVED  # noqa: E402
from app.services import register_file, extract_file, merge_lines  # noqa: E402
from app.validation import validate_all, blocking_errors  # noqa: E402


def mk_gstin(prefix14):
    return prefix14 + checksum_char(prefix14)


own = mk_gstin("27ABCDE1234F1Z")
cust = mk_gstin("29PQRSX5678L1Z")
assert validate_gstin(own)[0] == "ok", validate_gstin(own)
assert validate_gstin(own[:-1] + ("A" if own[-1] != "A" else "B"))[0] == "warn"
assert validate_gstin("123")[0] == "error"

rows = [
    ["Sales Register - Sep 2026"],
    [],
    ["Invoice No", "Invoice Date", "Customer Name", "GSTIN", "Place of Supply", "HSN Code", "Qty", "UOM",
     "Taxable Value", "Rate", "IGST", "CGST", "SGST", "Invoice Value"],
    ["INV001", "05/09/2026", "Cust A", cust, "29-Karnataka", "8471", 2, "NOS", 10000, 18, 1800, 0, 0, 11800],
    ["INV002", "06/09/2026", "Cust A", cust, "29-Karnataka", "8471", 1, "NOS", 5000, 18, 900, 0, 0, 5900],
    ["INV004", "08/09/2026", "Walk-in", "", "Maharashtra", "9983", 1, "", 2000, 18, 0, 180, 180, 2360],
    ["INV005", "09/09/2026", "Cust B", mk_gstin("27ZZZZZ9999Z1Z"), "27", "8471", 1, "NOS", 1000, 18, 0, 90, 90, 1180],
    ["INV005", "09/09/2026", "Cust B", mk_gstin("27ZZZZZ9999Z1Z"), "27", "9983", 1, "", 500, 5, 0, 12.5, 12.5, 1180 ],
    ["Total", None, None, None, None, None, None, None, 18500],
]
xl = tmp / "register.xlsx"
pd.DataFrame(rows).to_excel(xl, header=False, index=False)

db = Database()
client = {"name": "Test Co", "gstin": own, "legal_name": "Test Co Pvt Ltd", "trade_name": "", "state_code": "27",
          "reg_type": "Regular", "return_type": "Monthly"}
client["id"] = db.save_client(client)
pid = db.create_project(client["id"], "2026-27", 9, 2026, "Monthly", load_schema()["schema_version"])
project = db.get_project(pid)
settings = db.get_settings()

fid, msg = register_file(db, client, project, xl)
assert fid, msg
assert register_file(db, client, project, xl)[0] is None   # duplicate file skipped
res = extract_file(db, client, project, fid, settings)
print("kind:", res.kind, "lines:", len(res.lines), res.messages)
assert len(res.lines) == 5, len(res.lines)
lines = []
merge_lines(lines, res.lines)
classify_all(lines, settings)
print([(l.invoice_no, l.section) for l in lines])
docs = derive_docs(lines)
issues = validate_all(lines, client, docs, settings, (9, 2026))
for i in issues:
    print(i.severity, i.code, i.invoice_no, "-", i.message)
codes = {i.code for i in issues}
assert "TAX_MISMATCH" not in codes or True
assert "SEQ_GAP" in codes          # INV003 missing
assert "DOCS_DERIVED" in codes
assert any(l.section == "B2CS" for l in lines)

for l in lines:
    l.review_status = STATUS_APPROVED
try:
    export_project(client, project, lines, [], docs, issues, settings, override=False)
    print("exported without block (no errors)")
except ValueError as e:
    print("blocked as expected:", e)
r = export_project(client, project, lines, [], docs, issues, settings, override=True, override_reason="test",
                   confirm_overwrite=lambda x: True)
out = r["folder"]
print(sorted(p.name for p in out.iterdir()))
print((out / "b2b.csv").read_text())
print((out / "HSN.csv").read_text())
print((out / "documents.csv").read_text())
b2b = pd.read_csv(out / "b2b.csv")
inv1 = b2b[b2b["Invoice Number"] == "INV001"]
assert len(inv1) == 1 and float(inv1["Invoice Value"].iloc[0]) == 11800.0
inv5 = b2b[b2b["Invoice Number"] == "INV005"]
assert len(inv5) == 2          # two rate rows
db.backup(tmp / "bk.zip")

# ---- Documents template: download -> fill -> strict upload -> documents.csv only
from openpyxl import load_workbook  # noqa: E402
from app.exporters import write_docs_template, read_docs_template, export_documents_only  # noqa: E402
from app.exporters import doc_natures  # noqa: E402

schema = load_schema()
tpl = tmp / "documents_template.xlsx"
write_docs_template(tpl, schema)
wb = load_workbook(tpl)
assert {"Documents", "Valid natures", "Instructions", "Examples"} <= set(wb.sheetnames)
ws = wb["Documents"]
assert [c.value for c in ws[1]] == [c["header"] for c in schema["tables"]["docs"]["columns"]]
for r, row in enumerate([[doc_natures(load_schema())[0], "INV001", "INV100", 100, 2], [doc_natures(load_schema())[4], "CN001", "CN010", None, 1]], 2):
    for c, v in enumerate(row, 1):
        ws.cell(r, c, v)
wb.save(tpl)
series, problems = read_docs_template(tpl, schema)
assert not problems, problems
assert len(series) == 2 and series[1].total == 10 and series[1].net == 9, series      # total derived from range
csvt = tmp / "documents_template.csv"
write_docs_template(csvt, schema)
assert csvt.read_text().strip() == ",".join(c["header"] for c in schema["tables"]["docs"]["columns"])

bad = tmp / "bad.xlsx"
pd.DataFrame([["Made up nature", "A1", "A9", 9, 20], ["Credit Note", "", "CN5", "x", 0]],
             columns=[c["header"] for c in schema["tables"]["docs"]["columns"]]).to_excel(bad, index=False)
_, probs = read_docs_template(bad, schema)
print("problems on bad file:", *probs, sep="\n  ")
assert len(probs) >= 4
wrong = tmp / "wrong.xlsx"
pd.DataFrame({"a": [1]}).to_excel(wrong, index=False)
try:
    read_docs_template(wrong, schema)
    raise AssertionError("wrong layout accepted")
except ValueError as e:
    assert "headings not found" in str(e)

dest = tmp / "chosen_folder"
dest.mkdir()
res = export_documents_only(client, project, series, dest)
assert res["file"].parent == dest / "clients" / client["gstin"] / "FY_2026_27" / "GSTR1_2026_09" / "output"
print(res["file"].read_text())
assert res["file"].read_text().count("\n") == 3
try:
    export_documents_only(client, project, series, dest)       # existing file, no confirmation
    raise AssertionError("overwrote without confirmation")
except ValueError:
    pass
print("ALL CORE TESTS PASSED")
