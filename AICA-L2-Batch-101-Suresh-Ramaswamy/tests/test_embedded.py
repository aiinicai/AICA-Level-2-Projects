"""Smart Billing PDFs are read exactly from the data stored inside them."""
import os, sys, tempfile
tmp = tempfile.mkdtemp()
os.environ["SMARTBILLING_DB"] = tmp + "/db"; os.environ["SMARTBILLING_PDF"] = tmp + "/pdf"
sys.path.insert(0, "/home/claude/billing")
import smartbilling as sb
from pypdf import PdfReader
from app.extractors.pdf_reader import lines_from_embedded
S = dict(sb.DEFAULT_SETTINGS); S.update({"gstin": "33DEMOA1234B1ZD", "state_code": "33", "trade_name": "B", "address": "x"})
d = {"doc_type": "Tax Invoice", "invoice_no": "894", "date": "2026-09-29", "reverse_charge": "N", "pos": "33",
     "customer": {"name": "Thiru Nanda Gopal", "gstin": "", "address": "Pennalur", "state": "33"}, "ship_same": True, "ship_to": {},
     "items": [{"desc": "Sold Hallow Block", "hsn": "681011", "kind": "Goods", "supply": "Taxable", "qty": "200", "uqc": "NOS", "rate": "45", "disc": "0", "gst_pct": "18"}]}
d = sb.compute(d, S); p = tmp + "/a.pdf"; sb.build_pdf(p, d, S)
kw = PdfReader(p).metadata.get("/Keywords")
lines, msgs = lines_from_embedded(kw, {"gstin": "33DEMOA1234B1ZD", "name": "B"}, "a.pdf")
l = lines[0]
assert (l.invoice_no, l.invoice_date, l.hsn, str(l.taxable), str(l.cgst), str(l.sgst), str(l.invoice_total)) == ("894", "2026-09-29", "681011", "9000.00", "810.00", "810.00", "10620"), l
assert str(l.rate) == "18.00" or str(l.rate) == "18", l.rate
assert lines_from_embedded("plain text", {"gstin": "x", "name": "y"}, "z") is None
print("ALL EMBEDDED PDF TESTS PASSED")
