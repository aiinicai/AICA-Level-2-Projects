"""Auto-completion (place of supply from GSTIN, tax = taxable x rate), bulk delete, skip-error upload.
Run:  python -m tests.test_auto"""
import os
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
os.environ["CAGST_DATA"] = str(tmp / "data")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import tk_stub  # noqa: E402

tk_stub.install()

import pandas as pd  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

from app import autofill, gstr1, ui  # noqa: E402
from app.db import Database  # noqa: E402
from app.exporters import load_schema  # noqa: E402
from app.gstin import checksum_char  # noqa: E402
from app.models import Line, STATUS_APPROVED  # noqa: E402
from app.services import extract_file, register_file, import_master_template, remove_template_rows  # noqa: E402
from app.utils import D  # noqa: E402


def mk(p14):
    return p14 + checksum_char(p14)


own = mk("27ABCDE1234F1Z")
ka = mk("29PQRSX5678L1Z")        # Karnataka customer
mh = mk("27ZZZZZ9999Z1Z")        # Maharashtra customer (same state as supplier)

# ===================================================================== A. pure engine
S = {"auto_tax": "1", "auto_pos": "1", "rounding_tolerance": "1.00", "valid_rates": "0,5,12,18,28"}
l = Line(id=1, taxable=D("10000"), rate=D("18"), recipient_gstin=ka, supplier_gstin=own)
ch = autofill.autofill_line(l, "27", S)
assert l.pos == "29" and l.igst == D("1800.00") and l.cgst == 0 and l.sgst == 0, (l.pos, l.igst, ch)
l = Line(id=2, taxable=D("5000"), rate=D("12"), recipient_gstin=mh, supplier_gstin=own)
autofill.autofill_line(l, "27", S)
assert l.pos == "27" and l.igst == 0 and l.cgst == D("300.00") and l.sgst == D("300.00")
l = Line(id=3, taxable=D("1000"), rate=D("5"), supplier_gstin=own)                    # unregistered
autofill.autofill_line(l, "27", S)
assert l.pos == "27" and l.cgst == D("25.00") and "assumed" in l.note
l = Line(id=4, taxable=D("1000"), rate=D("18"), supplier_gstin=own, invoice_type="Export")
autofill.autofill_line(l, "27", S)
assert l.pos == "96" and l.igst == D("180.00")
l = Line(id=5, taxable=D("1000"), rate=D("18"), recipient_gstin=ka, reverse_charge="Y")
autofill.autofill_line(l, "27", S)
assert l.tax_total == 0
l = Line(id=6, taxable=D("1000"), rate=D("18"), recipient_gstin=ka, export_type="WOPAY")
autofill.autofill_line(l, "27", S)
assert l.tax_total == 0
l = Line(id=7, taxable=D("-2000"), rate=D("18"), recipient_gstin=mh, note_type="C")       # credit note
autofill.autofill_line(l, "27", S)
assert l.cgst == D("-180.00") and l.sgst == D("-180.00")
l = Line(id=8, taxable=D("1000"), rate=D("18"), recipient_gstin=mh, igst=D("999"))        # wrong tax in source
autofill.autofill_line(l, "27", S)
assert l.igst == 0 and l.cgst == D("90.00") and "replaced" in l.note
l = Line(id=9, taxable=D("1000"), recipient_gstin=ka, igst=D("180"))                      # rate inferred from tax
autofill.autofill_line(l, "27", S)
assert l.rate == D("18") and l.igst == D("180.00")
l = Line(id=10, taxable=D("1000"), rate=D("18"), recipient_gstin=ka, pos="27", cgst=D("90"), sgst=D("90"))
autofill.autofill_line(l, "27", S)                                                        # explicit POS is respected
assert l.pos == "27" and l.cgst == D("90.00")
S_off = dict(S, auto_tax="0", auto_pos="0")
l = Line(id=11, taxable=D("1000"), rate=D("18"), recipient_gstin=ka)
autofill.autofill_line(l, "27", S_off)
assert l.pos == "" and l.tax_total == 0, "switched-off settings must not change anything"
print("engine OK")

# ===================================================================== B. minimal Excel register
reg = tmp / "min_register.xlsx"
rows = [["Bill No", "Bill Date", "Party Name", "GSTIN", "Taxable Value", "GST %"],
        ["A1", "05/09/2026", "Cust KA", ka, 10000, 18],
        ["A2", "06/09/2026", "Cust MH", mh, 5000, 12],
        ["A3", "07/09/2026", "Walk-in", "", 1000, 5]]
pd.DataFrame(rows).to_excel(reg, header=False, index=False)
db = Database()
client = {"name": "Test Co", "gstin": own, "legal_name": "Test Co Pvt Ltd", "trade_name": "", "state_code": "27",
          "reg_type": "Regular", "return_type": "Monthly"}
client["id"] = db.save_client(client)
schema = load_schema()
pid = db.create_project(client["id"], "2026-27", 9, 2026, "Monthly", schema["schema_version"])
project = db.get_project(pid)
settings = db.get_settings()
assert settings["auto_tax"] == "1" and settings["auto_pos"] == "1"
fid, msg = register_file(db, client, project, reg)
res = extract_file(db, client, project, fid, settings)
by = {x.invoice_no: x for x in res.lines}
print("minimal register lines:", len(res.lines), res.messages)
assert len(by) == 3, res.messages
assert by["A1"].pos == "29" and by["A1"].igst == D("1800.00")
assert by["A2"].pos == "27" and by["A2"].cgst == D("300.00") and by["A2"].sgst == D("300.00")
assert by["A3"].pos == "27" and by["A3"].cgst == D("25.00")

# ===================================================================== C. minimal Master Template
blank = tmp / "blank.xlsx"
gstr1.write_master_template(blank, schema, client, project, sample=False)


def fill(path, sheet, data):
    wb = load_workbook(path)
    ws = wb[sheet]
    matrix = gstr1._sheet_matrix(ws)
    spec = schema["tables"][next(k for k, t in schema["tables"].items() if t["sheet"] == sheet)]
    hi = gstr1._find_header(matrix, {gstr1._NORM(c["header"]) for c in spec["columns"]})
    hdr_row = matrix[hi][0]
    col = {gstr1._NORM(v): ci for ci, v in enumerate(matrix[hi][1], 1) if v}
    r = hdr_row + 1
    for rec in data:
        for h, v in rec.items():
            ws.cell(r, col[gstr1._NORM(h)], v)
        r += 1
    wb.save(path)


tpl = tmp / "client_min.xlsx"
tpl.write_bytes(blank.read_bytes())
fill(tpl, "B2B", [
    {"GSTIN/UIN of Recipient": ka, "Invoice Number": "T1", "Invoice date": "05-09-2026", "Rate": 18, "Taxable Value": 10000},
    {"GSTIN/UIN of Recipient": ka, "Invoice Number": "T1", "Invoice date": "05-09-2026", "Rate": 5, "Taxable Value": 2000},
    {"GSTIN/UIN of Recipient": mh, "Invoice Number": "T2", "Invoice date": "06-09-2026", "Rate": 12, "Taxable Value": 5000}])
fill(tpl, "B2CS", [{"Rate": 18, "Taxable Value": 7000}])
fill(tpl, "HSN", [{"HSN": "8471", "UQC": "NOS-NUMBERS", "Total Quantity": 3, "Rate": 18, "Taxable Value": 10000}])
ctx = gstr1.make_ctx(client, project, settings, schema)
r = gstr1.read_master_template(tpl, schema, ctx, tpl.name)
assert not r.errors, [(i.ref, i.message) for i in r.errors]
b2b = {(x["invoice_no"], x["rate"]): x for x in r.tables["b2b"]}
assert all(x["pos"] == ("29" if x["invoice_no"] == "T1" else "27") for x in r.tables["b2b"])
t1v = D(next(x["invoice_value"] for x in r.tables["b2b"] if x["invoice_no"] == "T1"))
assert t1v == D("10000") * D("1.18") + D("2000") * D("1.05"), t1v           # 11800 + 2100
assert r.tables["b2cs"][0]["pos"] == "27"                                    # unregistered -> supplier state
h = r.tables["hsn"][0]
assert D(h["igst"]) + D(h["cgst"]) + D(h["sgst"]) == D("1800.00"), h
codes = {i.code for i in r.issues}
assert {"POS_FROM_GSTIN", "POS_ASSUMED", "VALUE_CALC", "HSN_TAX_CALC"} <= codes, codes
print("minimal template OK:", sorted(codes))

# ===================================================================== D. skip-error upload + row removal
bad = tmp / "client_bad.xlsx"
bad.write_bytes(blank.read_bytes())
fill(bad, "B2B", [
    {"GSTIN/UIN of Recipient": ka, "Invoice Number": "G1", "Invoice date": "05-09-2026", "Rate": 18, "Taxable Value": 1000},
    {"GSTIN/UIN of Recipient": ka, "Invoice Number": "B1", "Invoice date": "31-02-2026", "Rate": 18, "Taxable Value": 1000},
    {"GSTIN/UIN of Recipient": ka, "Invoice Number": "B2", "Invoice date": "05-09-2026", "Rate": 18, "Taxable Value": 500},
    {"GSTIN/UIN of Recipient": ka, "Invoice Number": "B2", "Invoice date": "05-09-2026", "Rate": 12, "Taxable Value": "abc"},
    {"GSTIN/UIN of Recipient": "29BADGSTIN", "Invoice Number": "B3", "Invoice date": "05-09-2026", "Rate": 18, "Taxable Value": 100},
    {"GSTIN/UIN of Recipient": mh, "Invoice Number": "G2", "Invoice date": "06-09-2026", "Rate": 12, "Taxable Value": 5000}])
strict = gstr1.read_master_template(bad, schema, ctx, bad.name)
assert strict.errors and not strict.skipped
r2, ds, msg = import_master_template(db, client, project, bad, settings, schema)
assert ds is None and "nothing was imported" in msg
r3, ds, msg = import_master_template(db, client, project, bad, settings, schema, skip_errors=True)
assert ds, (msg, [(i.ref, i.message) for i in r3.errors])
kept = sorted({x["invoice_no"] for x in r3.tables["b2b"]})
assert kept == ["G1", "G2"], kept                       # B1 bad date, B2 (one bad row => whole invoice), B3 bad GSTIN
assert r3.skipped == 4 and sum(1 for i in r3.issues if i.code == "ROW_SKIPPED") >= 3
assert not r3.errors
print("skip-errors OK; kept", kept, "skipped rows", r3.skipped)

sets = db.datasets(pid)
rows_g = sets[0]["tables"]["b2b"]
target = {(rows_g[0]["__file"], rows_g[0]["__ref"])}
n = remove_template_rows(db, sets, target)
assert n == 1 and [x["invoice_no"] for x in db.datasets(pid)[0]["tables"]["b2b"]] == ["G2"]
print("remove_template_rows OK")

# ===================================================================== E. screens: Ctrl+A, bulk delete, auto-fill
fd, mb = ui.filedialog, ui.messagebox
mb.askyesno = lambda *a, **k: True
app = ui.App()
app.cv["name"].set("Test Co2")
app.cv["gstin"].set(mk("29ABCDE1234F1Z"))
app.cv["legal_name"].set("Test Co2")
app.cv["reg_type"].set("Regular")
app.cv["return_type"].set("Monthly")
app.save_client()
app.proj_client.current(0)
app.pm.set("September")
app.py.set("2026")
app.new_return()
assert app.project
ownk = app.client["gstin"]
mhc = mk("29PQRSX5678L1Z")        # customer in another state than the supplier
same = mk("27ZZZZZ9999Z1Z")


def L(i, inv, gstin, taxable, rate, **kw):
    x = Line(id=i, source_file="reg.xlsx", source_ref=f"r{i}", supplier_gstin=ownk, invoice_no=inv,
             invoice_date="2026-09-05", recipient_gstin=gstin, recipient_name="X", hsn="8471", uqc="NOS",
             qty=D(1), taxable=D(taxable), rate=D(rate))
    for k, v in kw.items():
        setattr(x, k, v)
    return x


good = L(1, "OK1", mhc, 1000, 18)
badl = [L(2, "BAD1", "27BADGSTIN00000", 1000, 18), L(3, "BAD2", "XX", 1000, 18),
        L(4, "BAD3", mhc, 1000, 18, invoice_date="")]
app.lines = [good] + badl
app.run_checks()
n_auto = autofill.autofill_lines(app.lines, ownk[:2], app.settings)
app.run_checks()
assert good.pos == "29" and good.igst == D("180.00")
app.refresh_review()
app.select_all_lines()
assert len(app.rev_tree.selection()) == 4
app.select_error_lines()
sel = set(app.rev_tree.selection())
assert sel == {"2", "3", "4"}, sel
app.delete_lines()                                          # same call as the Delete key
assert [l.invoice_no for l in app.lines] == ["OK1"]
# delete ALL error lines from a different entry point
app.lines += [L(5, "BAD5", "29BAD", 10, 18), L(6, "OK2", mhc, 500, 18)]
autofill.autofill_lines(app.lines, ownk[:2], app.settings)
app.run_checks()
app.delete_error_lines()
assert [l.invoice_no for l in app.lines] == ["OK1", "OK2"], [l.invoice_no for l in app.lines]
# bulk auto-fill + POS from GSTIN
for x in app.lines:
    x.pos, x.igst, x.cgst, x.sgst = "", Decimal(0), Decimal(0), Decimal(0)
app.autofill_selected()
assert all(x.pos == "29" and x.igst for x in app.lines)
app.lines[0].pos = "27"
app.lines[0].igst = Decimal(0)
app.rev_tree.selection_set(["1"])
app.pos_from_gstin_selected()
assert app.lines[0].pos == "29" and app.lines[0].igst == D("180.00")
# edit dialog: changing the GSTIN re-derives POS, changing taxable recalculates tax
class FakeForm:
    def __init__(self, parent, title, fields, values, columns=2, extra_buttons=None):
        self.result = dict(values)
        self.result.update(FakeForm.change)


ui.FormDialog = FakeForm
FakeForm.change = {"recipient_gstin": same, "taxable": "2000"}
app.rev_tree.selection_set(["1"])
app.edit_line()
x = app.lines[0]
assert x.pos == "27" and x.cgst == D("180.00") and x.sgst == D("180.00") and x.igst == 0, (x.pos, x.igst, x.cgst)
FakeForm.change = {"igst": "7"}                               # a manual tax edit is respected
x.igst = Decimal(0)
app.rev_tree.selection_set(["1"])
app.edit_line()
# validation tab: delete the rows behind selected issues (invoice lines and template rows)
app.lines = [L(7, "BAD7", "27BADGSTIN00000", 100, 18), L(8, "OK7", mhc, 100, 18)]
autofill.autofill_lines(app.lines, ownk[:2], app.settings)
app.run_checks()
app.refresh_validation()
app.select_error_issues()
assert app.val_tree.selection()
app.delete_issue_rows()
assert [l.invoice_no for l in app.lines] == ["OK7"]
print("screen logic OK")

# template rows through the screen: skip-errors upload, then delete via the issue list
fd.askopenfilename = lambda **k: str(bad)
app.skip_err.set(True)
bad_k = tmp / "bad_k.xlsx"
wb = load_workbook(bad)
for row in wb["Return Info"].iter_rows(min_row=1, max_row=12):
    if row[0].value and str(row[0].value).startswith("GSTIN"):
        row[1].value = ownk
wb.save(bad_k)
fd.askopenfilename = lambda **k: str(bad_k)
app.master_upload()
assert app.sets and any(i.code == "ROW_SKIPPED" for i in app.last_upload_issues), ui.messagebox.calls[-3:]
ds = app.sets[-1]
inv_before = sorted({r["invoice_no"] for r in ds["tables"]["b2b"]})
assert inv_before == ["G1", "G2"], inv_before
ds["tables"]["b2b"][0]["rate"] = "7"                       # unusual rate => a warning that points to a template row
app.db.update_dataset(ds["id"], ds["tables"])
app.sets = app.db.datasets(app.project["id"])
app.run_checks()
app.v_sev.set("All")
app.refresh_validation()
pick = [str(n) for n, i in enumerate(app.issues) if i.code == "RATE_UNUSUAL" and i.ref]
assert pick, [(i.code, i.ref) for i in app.issues]
app.val_tree.selection_set(pick)
app.delete_issue_rows()
left = sorted({r["invoice_no"] for r in app.sets[-1]["tables"]["b2b"]})
assert left == ["G2"], left
print("ALL AUTOFILL / BULK DELETE TESTS PASSED")
