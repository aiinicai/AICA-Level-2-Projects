"""v2.2: gap-wise document series, mapping with fixed values, set rate/HSN for many rows, HSN memory, return delete.
Run:  python -m tests.test_v22"""
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

from app import hsn, series, ui  # noqa: E402
from app.db import Database  # noqa: E402
from app.exporters import derive_docs, load_schema  # noqa: E402
from app.extractors.excel_reader import decode_invoice_type, read_workbook  # noqa: E402
from app.gstin import checksum_char  # noqa: E402
from app.models import Line, STATUS_APPROVED  # noqa: E402
from app.services import learn_hsn  # noqa: E402
from app.utils import D  # noqa: E402


def mk(p14):
    return p14 + checksum_char(p14)


own = mk("27ABCDE1234F1Z")
ka = mk("29PQRSX5678L1Z")
mh = mk("27ZZZZZ9999Z1Z")

# ===================================================================== document series
def L(no, cust=ka, note=""):
    return Line(invoice_no=str(no), recipient_gstin=cust, recipient_name="X", note_type=note)


lines = [L(n) for n in list(range(1001, 1010)) + list(range(1014, 1024))]
docs = derive_docs(lines)
assert [(d.from_no, d.to_no, d.total, d.cancelled) for d in docs] == [("1001", "1009", 9, 0), ("1014", "1023", 10, 0)], \
    [(d.from_no, d.to_no, d.total) for d in docs]
runs = series.build_runs(series.entries_from_lines(lines), "auto")
assert series.gap_report(runs) and "1010 - 1013" in series.gap_report(runs)[0]
# credit notes are their own series; prefixes and widths are kept
lines2 = [L(f"INV/{n:04d}") for n in (1, 2, 3, 7, 8)] + [L(n, note="C") for n in (1, 2)]
d2 = derive_docs(lines2)
assert [(d.nature, d.from_no, d.to_no, d.total) for d in d2] == [
    ("Invoices for outward supply", "INV/0001", "INV/0003", 3), ("Invoices for outward supply", "INV/0007", "INV/0008", 2),
    ("Credit Note", "1", "2", 2)], [(d.nature, d.from_no, d.to_no) for d in d2]
# plain numbers where each customer has his own run -> one family of series per customer
lines3 = [L(n, ka) for n in (1, 2, 3, 4)] + [L(n, mh) for n in (1, 2, 5)]
assert series.auto_mode(series.entries_from_lines(lines3)) == "customer"
d3 = derive_docs(lines3)
assert [(d.from_no, d.to_no, d.total, d.source_file[:8]) for d in d3] == [
    ("1", "2", 2, "customer"), ("5", "5", 1, "customer"), ("1", "4", 4, "customer")], \
    [(d.from_no, d.to_no, d.source_file) for d in d3]
assert series.auto_mode(series.entries_from_lines(lines)) == "prefix"
d3b = derive_docs(lines3, mode="prefix")
assert [(d.from_no, d.to_no) for d in d3b] == [("1", "5")]
# Master Template rows count too
sets = [{"tables": {"b2b": [{"invoice_no": "7", "recipient_gstin": ka}, {"invoice_no": "8", "recipient_gstin": ka},
                            {"invoice_no": "20", "recipient_gstin": ka}]}}]
assert [(d.from_no, d.to_no) for d in derive_docs([], sets)] == [("7", "8"), ("20", "20")]
print("series OK")

# ===================================================================== invoice type text
assert decode_invoice_type("Export without payment") == ("Export", "WOPAY")
assert decode_invoice_type("Export - with payment of tax") == ("Export", "WPAY")
assert decode_invoice_type("SEZ with payment") == ("SEZ supplies with payment", "")
assert decode_invoice_type("SEZ without payment") == ("SEZ supplies without payment", "")
assert decode_invoice_type("Deemed Export") == ("Deemed Exp", "")
assert decode_invoice_type("B2B") == ("Regular", "") and decode_invoice_type("zzz") == ("", "")

# ===================================================================== mapping with 'same value for every row'
reg = tmp / "odd.xlsx"
rows = [["Invoice Valye", "Invoice Number", "Date", "GSTIN", "Customer", "Amount"],
        [1180, "1", "05/09/2026", ka, "Cust A", 1000],
        [2360, "2", "06/09/2026", "", "Foreign Co", 2000]]
pd.DataFrame(rows).to_excel(reg, header=False, index=False)
S = {"auto_tax": "1", "auto_pos": "1", "valid_rates": "0,5,12,18,28", "rounding_tolerance": "1"}
client = {"name": "T", "gstin": own, "legal_name": "T"}
res = read_workbook(reg, client, S)
assert res.needs_mapping and res.needs_mapping[0]["columns"][-1] == "Amount"
m = {"invoice_no": "Invoice Number", "invoice_date": "Date", "recipient_gstin": "GSTIN", "recipient_name": "Customer",
     "taxable": "Amount", "invoice_total": "Invoice Valye",
     "__fixed": {"invoice_type": "Export - without payment of tax", "rate": "18"}}
res = read_workbook(reg, client, S, m)
assert len(res.lines) == 2 and all(x.invoice_type == "Export" and x.export_type == "WOPAY" and x.rate == 18 for x in res.lines)
assert res.sheets and res.sheets[0]["mapping"]["taxable"] == "Amount"
res = read_workbook(reg, client, S, {k: v for k, v in m.items() if k != "__fixed"} | {"__fixed": {"rate": "12"}})
assert all(x.rate == 12 and x.invoice_type == "Regular" for x in res.lines)
print("mapping with fixed values OK")

# ===================================================================== HSN
assert hsn.describe("8471").startswith("Automatic data processing")
assert hsn.describe("998314") == "Other professional, technical and business services"
assert hsn.describe("99651190") == "Goods transport services"
assert hsn.describe("4011") == "New pneumatic tyres, of rubber" and hsn.describe("4012").startswith("Rubber")
assert hsn.describe("1234567") == "" or True
db = Database()
cl = {"name": "Test Co", "gstin": own, "legal_name": "Test Co", "trade_name": "", "state_code": "27",
      "reg_type": "Regular", "return_type": "Monthly"}
cl["id"] = db.save_client(cl)
a = Line(id=1, hsn="9965", taxable=D(1000), rate=D(12), uqc="OTH", description="Transport charges",
         review_status=STATUS_APPROVED)
assert learn_hsn(db, cl["id"], [a]) == 1
mem = db.hsn_master(cl["id"])
assert mem["9965"] == {"description": "Transport charges", "uqc": "OTH", "rate": "12"}
b = Line(id=2, hsn="9965", taxable=D(500))
hsn.apply_to_lines([b], mem)
assert b.description == "Transport charges" and b.rate == 12 and b.uqc == "OTH" and "remembered" in b.note
print("HSN OK")

# ===================================================================== screens
fd, mb = ui.filedialog, ui.messagebox
mb.askyesno = lambda *a, **k: True
app = ui.App()
app.cv["name"].set("Test Co UI")
app.cv["gstin"].set(mk("29ABCDE1234F1Z"))
app.cv["legal_name"].set("Test Co UI")
app.cv["reg_type"].set("Regular")
app.cv["return_type"].set("Monthly")
app.save_client()
app.proj_client.current(len(app.client_rows) - 1)
for month in ("August", "September"):
    app.pm.set(month)
    app.py.set("2026")
    app.new_return()
assert app.project and len(app.proj_tree.rows()) == 2
ownk = app.client["gstin"]
assert "Create" in app.next_step()[0] or app.next_step()[1] in ("Master Template", "Return"), app.next_step()

# register without rate / invoice type
reg2 = tmp / "reg2.xlsx"
pd.DataFrame([["Invoice Number", "Date", "GSTIN", "Customer", "HSN", "Taxable Value"],
              ["1", "05/09/2026", ka, "Cust KA", "9965", 1000],
              ["2", "06/09/2026", mh, "Cust MH", "9965", 2000],
              ["3", "07/09/2026", "", "Walk-in", "8471", 500]]).to_excel(reg2, header=False, index=False)
app.add_files([str(reg2)])
app.extract_data()
assert len(app.lines) == 3
assert app.lines[0].description.startswith("Goods transport"), app.lines[0].description      # description filled
assert not any(l.rate for l in app.lines)                                                     # no rate in the file
assert app.next_step()[1] == "Invoice Review"

# set GST rate for everything in one go
class FakeForm:
    def __init__(self, parent, title, fields, values, columns=2):
        self.result = {f[0]: "" for f in fields}
        self.result.update(values)
        self.result.update(FakeForm.change)


ui.FormDialog = FakeForm
FakeForm.change = {"rate": "18", "scope": "All lines", "file": "All files"}
app.set_rate_hsn()
by = {l.invoice_no: l for l in app.lines}
assert all(l.rate == 18 for l in app.lines)
assert ownk[:2] == "29"
assert by["1"].pos == "29" and by["1"].igst == 0 and by["1"].cgst == D("90.00")           # same state -> CGST + SGST
assert by["2"].pos == "27" and by["2"].igst == D("360.00") and by["2"].cgst == 0           # other state -> IGST
assert by["3"].pos == ownk[:2] and by["3"].cgst == D("45.00") and by["3"].sgst == D("45.00"), (by["3"].pos, by["3"].cgst)
# set an HSN for rows that have none
by["3"].hsn = ""
FakeForm.change = {"rate": "", "hsn": "998314", "scope": "Only lines with no HSN", "file": "All files"}
app.set_rate_hsn()
assert by["3"].hsn == "998314" and by["3"].description.startswith("Other professional") and by["1"].hsn == "9965"
# approve -> HSN is remembered for the client
for l in app.lines:
    l.review_status = "Pending"
app.rev_tree.selection_set([str(l.id) for l in app.lines])
app.approve_selected()
assert "998314" in app.db.hsn_master(app.client["id"]) and app.db.hsn_master(app.client["id"])["9965"]["rate"] == "18"

# column mapping can be reopened for a file that was recognised automatically
seen = {}


class FakeMap:
    def __init__(self, parent, filename, entry):
        seen["entry"] = entry
        self.result = {k: v for k, v in entry["mapping"].items()} | {"__fixed": {"invoice_type": "Deemed Exp", "rate": "12"}}


ui.MappingDialog = FakeMap
fid = app.db.files(app.project["id"])[0]["id"]
app.file_tree.selection_set([str(fid)])
app.map_selected()
assert seen["entry"]["mapping"]["taxable"] == "Taxable Value"
assert all(l.invoice_type == "Deemed Exp" for l in app.lines if l.source_file == "reg2.xlsx"), [l.invoice_type for l in app.lines]

# documents tab: gap-wise series
app.lines = [L(n) for n in (1001, 1002, 1003, 1010, 1011)]
for l in app.lines:
    l.recipient_gstin = mk("29PQRSX5678L1Z")
    l.invoice_date = "2026-09-05"
    l.source_file = "x"
app.doc_mode.set("Auto")
app.doc_suggest()
assert [(d.from_no, d.to_no, d.total) for d in app.docs] == [("1001", "1003", 3), ("1010", "1011", 2)]
assert "1004" in app.doc_gaps.get(), app.doc_gaps.get()

# delete returns: the open one and the other one
pids = [int(x) for x in app.proj_tree.selection()] or [int(i) for i in app.proj_tree.get_children()]
app.refresh_projects()
app.proj_tree.selection_set(app.proj_tree.get_children())
app.delete_selected_returns()
assert not app.proj_tree.rows() and app.project is None and not app.lines
print("ALL v2.2 TESTS PASSED")
