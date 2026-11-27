"""Form 26AS reader, on invented text in the two layouts TRACES gives (delimited text and PDF text)."""
from advtax import form26as_read as f

TEXT_FILE = """File Creation Date^27-11-2026^Permanent Account Number (PAN)^ABCDE1234F^Current Status of PAN^Active^Financial Year^2026-27^Assessment Year^2027-28
Name of Assessee^DEMO TRADER
PART-I - Details of Tax Deducted at Source
Sr. No.^Name of Deductor^TAN of Deductor^^^^^Total Amount Paid / Credited^Total Tax Deducted^Total TDS Deposited
1^DEMO BANK LIMITED^MUMD12345B^^^^^120000.00^12000.00^12000.00
^Sr. No.^Section^Transaction Date^Status of Booking^Date of Booking^Remarks^Amount Paid / Credited^Tax Deducted^TDS Deposited
^1^194A^30-Jun-2026^F^15-Jul-2026^-^60000.00^6000.00^6000.00
^2^194A^30-Sep-2026^F^15-Oct-2026^-^60000.00^6000.00^6000.00
2^DEMO BUYERS PRIVATE LIMITED^JDHD54321A^^^^^2500000.00^2500.00^2400.00
PART-VI-Details of Tax Collected at Source
Sr. No.^Name of Collector^TAN of Collector^^^^^Total Amount Paid/ Debited^Total Tax Collected^Total TCS Deposited
1^DEMO MOTORS LIMITED^DELD11111C^^^^^1500000.00^15000.00^15000.00
"""

PDF_TEXT = """Form 26AS Annual Tax Statement
Permanent Account Number (PAN) ABCDE1234F Financial Year 2026-27 Assessment Year 2027-28
PART-I - Details of Tax Deducted at Source
1 DEMO BANK LIMITED MUMD12345B 1,20,000.00 12,000.00 12,000.00
1 194A 30-Jun-2026 F 15-Jul-2026 - 60,000.00 6,000.00 6,000.00
2 DEMO BUYERS PRIVATE
LIMITED JDHD54321A 25,00,000.00 2,500.00 2,400.00
TAN of the deductor MUMD12345B is shown above
"""


def test_delimited_text_layout():
    r = f.parse(TEXT_FILE)
    assert [(x["name"], x["tan"], x["kind"], x["tax_deposited"]) for x in r["rows"]] == [
        ("DEMO BANK LIMITED", "MUMD12345B", "TDS", 12000.0),
        ("DEMO BUYERS PRIVATE LIMITED", "JDHD54321A", "TDS", 2400.0),
        ("DEMO MOTORS LIMITED", "DELD11111C", "TCS", 15000.0)]
    assert r["total_deposited"] == 29400 and r["total_deducted"] == 29500
    assert r["pan"] == "ABCDE1234F" and r["year"] == "2027-28" and r["lines_not_read"] == 0


def test_pdf_text_layout_with_indian_commas_and_wrapped_name():
    r = f.parse(PDF_TEXT)
    assert [(x["tan"], x["tax_deposited"]) for x in r["rows"]] == [("MUMD12345B", 12000.0), ("JDHD54321A", 2400.0)]
    assert r["rows"][0]["amount_paid"] == 120000.0
    assert r["total_deposited"] == 14400
    assert r["lines_not_read"] == 1  # the line that mentions a TAN without amounts is reported, not counted


def test_empty_file_gives_no_rows():
    r = f.parse("nothing useful here")
    assert r["rows"] == [] and r["total_deposited"] == 0 and r["pan"] == ""


def test_plain_text_bytes_are_decoded():
    assert f.read(TEXT_FILE.encode("utf-8"), "26AS.txt")["total_deposited"] == 29400
