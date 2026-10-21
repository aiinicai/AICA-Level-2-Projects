"""PDF text parsing: ISO date, item table, GST split."""
from app.extractors.pdf_reader import parse_invoice_text
from app.utils import parse_rates

T = """Demo  Block  Works
Mobile:  +91  9840000000  |  GSTIN:  33DEMOA1234B1ZD
Invoice  No:  INV-202610-001  Customer  Name:  MSM  INFRATECH
Date:  2026-10-18  Mobile:
GSTIN:  33ABIFM5938Q1ZJ
Item  Description  HSN  Qty  Rate  GST  %  Amount  GST  Total
Hallow  Block  681011  1.0  4000.00  18.0%  4000.00  720.00  4720.00
PVC  Story  68011  3.0  250.00  18.0%  750.00  135.00  885.00
Subtotal:  4750.00
Grand  Total:  5605.00
"""
r = parse_invoice_text(T, {"gstin": "33DEMOA1234B1ZD", "name": "X"}, parse_rates("0,5,12,18,28"), "p", "a.pdf")
assert len(r) == 2
assert r[0].invoice_date == "2026-10-18" and r[0].hsn == "681011" and str(r[0].cgst) == "360.00"
assert str(r[0].invoice_total) == "5605.00" and str(r[1].taxable) == "750.00"
print("ALL PDF TESTS PASSED")
