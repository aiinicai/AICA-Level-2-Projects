"""Rules added for scanned (OCR) invoices: GSTIN repair, amounts in words, arithmetic choice of
totals, rates not read as amounts, date formats, item checks and the second OCR pass merge."""
from datetime import date
from decimal import Decimal as D

from ipt.core.gstin import repair_ocr_gstin
from ipt.core.numwords import words_to_amount
from ipt.core.textnorm import parse_date
from ipt.services.extraction.layout import Line, Word
from ipt.services.extraction.parser import DATE_RE, ParsedInvoice, _amounts, parse
from ipt.services.extraction.pipeline import _fill_missing
from ipt.services.extraction.reconcile import solve
from tests.pdfgen import gst

SUP = gst("08DWIPR2155G1Z")      # 08DWIPR2155G1ZA
OWN = gst("08IEWPS1264C1Z")


def _lines(rows):
    """rows: [(y, [(x, text), ...])] -> Line objects as OCR would give them."""
    out = []
    for y, words in rows:
        out.append(Line([Word(t, x, y, x + 6 * len(t), y + 8) for x, t in words], 0))
    return out


def test_gstin_repair_extra_char_and_confusions():
    assert repair_ocr_gstin("O8S" + SUP[2:]) == SUP                # stray 'S' inserted, O for 0
    assert repair_ocr_gstin("OS" + OWN[2:]) == OWN                 # 'OS' for '08'
    assert repair_ocr_gstin("O@" + SUP[2:]) == SUP                 # '@' for 0
    assert repair_ocr_gstin(SUP[:14] + "!") in (None, SUP)         # '!' only accepted if it decides
    assert repair_ocr_gstin("random words here") is None


def test_amount_in_words():
    assert words_to_amount("INR Seventeen Thousand Five Hundred Seventy Three Only") == D("17573")
    assert words_to_amount("INR Two Thousand Two Hundred Fifty One and Thirty Eight paise Only") == D("2251.38")
    assert words_to_amount("One Lakh Twenty Thousand Only") == D("120000")
    assert words_to_amount("Thousand Erght Hundred") is None      # an unreadable word -> nothing


def test_rate_is_not_an_amount():
    assert _amounts("CGST@2.5% 1,570.00") == [D("1570.00")]
    assert _amounts("2.50 % 1,570.00") == [D("1570.00")]


def test_dates_from_scans():
    assert parse_date("6.Oct-26") == date(2026, 10, 6)
    assert parse_date("16 Oct 26") == date(2026, 10, 16)
    assert DATE_RE.search("18-Oct-2600").group(1) == "18-Oct-26"
    assert DATE_RE.search("26-27/640") is None                     # an invoice number is not a date


def test_solver_picks_unique_combination_and_rupee_misread():
    texts = ["QUICK LIME 14.645 MTON 5,975 4,375.19 91,879.07", "Round Off 0.07", "TOTAL 791,879",
             "2522 87,503.88 2.5% 2,187.60 2.5% 2,187.60"]
    sol = solve(texts, intra=True)
    assert (sol.taxable, sol.cgst, sol.sgst, sol.total) == (D("87503.88"), D("2187.60"), D("2187.60"), D("91879"))
    assert solve(["Total 100.00", "Tax 5.00"], intra=True) is None   # nothing consistent -> nothing


def test_parse_fills_totals_by_arithmetic_and_flags_conflicts():
    rows = [(20, [(40, "TAX"), (70, "INVOICE")]), (40, [(40, "GSTIN:"), (80, SUP)]),
            (60, [(40, "Invoice"), (90, "No."), (300, "Dated")]),
            (70, [(40, "SM/26-27/260"), (300, "14-Oct-26")]),
            (200, [(40, "Taxable"), (90, "Value"), (200, "16,736.00")]),
            (210, [(40, "CGST"), (200, "418.40")]), (220, [(40, "SGST"), (200, "418.40")]),
            (240, [(40, "INR"), (70, "Seventeen"), (140, "Thousand"), (200, "Five"), (230, "Hundred"),
                   (280, "Seventy"), (330, "Three"), (370, "Only")])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    assert p.fields["invoice_no"] == "SM/26-27/260" and p.fields["invoice_date"] == date(2026, 10, 14)
    assert p.fields["invoice_total"] == D("17573")                  # only in words; arithmetic confirms it
    assert p.fields["taxable_total"] == D("16736.00") and p.fields["cgst"] == D("418.40")
    # a total printed next to its label that does not add up is kept but marked for checking
    rows2 = rows[:-1] + [(240, [(40, "Grand"), (90, "Total"), (200, "18,000.00")]),
                         (250, [(40, "Amount"), (100, "17,573.00")])]
    p2 = parse(_lines(rows2), from_ocr=True, company_gstin=OWN)
    assert p2.fields["invoice_total"] == D("18000.00") and p2.confidence["invoice_total"] <= 0.55


def test_tax_rows_are_not_items_and_bad_items_flagged():
    rows = [(100, [(40, "Description"), (200, "HSN/SAC"), (260, "Quantity"), (330, "Rate"), (400, "Amount")]),
            (115, [(40, "QUICK"), (80, "LIME"), (200, "25221000"), (260, "40.000"), (330, "6,280.00"),
                   (400, "62,800.00")]),
            (130, [(40, "OUTPUT"), (90, "CGST"), (400, "1,570.00")]),
            (300, [(40, "Total"), (400, "65,940.00")])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    assert len(p.items) == 1 and p.items[0]["description"] == "QUICK LIME"
    assert p.item_confidence <= 0.55                                # 40 x 6,280 is not 62,800


def test_second_pass_only_fills_missing_fields():
    a, b = ParsedInvoice(), ParsedInvoice()
    a.put("invoice_no", "A-1", 0.75)
    b.put("invoice_no", "B-9", 0.75)
    b.put("invoice_date", date(2026, 10, 1), 0.75)
    _fill_missing(a, b)
    assert a.fields["invoice_no"] == "A-1" and a.fields["invoice_date"] == date(2026, 10, 1)


def test_image_cleaning_works_without_opencv(monkeypatch):
    import sys
    from PIL import Image
    from ipt.services.extraction import sources
    monkeypatch.setitem(sys.modules, "cv2", None)          # simulate a PC without OpenCV
    out = sources.clean_image(Image.new("RGB", (400, 300), "white"))
    assert out.size == (400, 300) and out.mode == "L"


def test_scan_amounts_that_do_not_add_up_are_flagged():
    rows = [(20, [(40, "TAX"), (70, "INVOICE")]), (200, [(40, "Taxable"), (90, "Value"), (200, "45,027.69")]),
            (210, [(40, "CGST"), (200, "250.00")]), (220, [(40, "SGST"), (200, "2.50")])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    assert all(p.confidence[k] <= 0.55 for k in ("taxable_total", "cgst", "sgst"))


def test_ocr_noise_as_supplier_name_is_flagged():
    rows = [(20, [(40, "TW"), (60, "ne"), (80, "ee")]), (30, [(40, "TAX"), (70, "INVOICE")]),
            (40, [(40, "GSTIN:"), (80, SUP)])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    if p.fields.get("supplier_name"):
        assert p.confidence["supplier_name"] <= 0.55


def test_damaged_copy_of_own_gstin_is_never_the_supplier():
    damaged = gst("05" + OWN[2:4] + "X" + OWN[5:14])      # valid checksum, state + 1 PAN char changed
    rows = [(20, [(40, "TAX"), (70, "INVOICE")]), (40, [(40, "GSTIN:"), (80, damaged)]),
            (200, [(40, "Taxable"), (90, "Value"), (200, "20,498.00")]),
            (210, [(40, "CGST"), (200, "512.45")]), (220, [(40, "SGST"), (200, "512.45")]),
            (240, [(40, "Total"), (200, "21,523.00")])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    assert p.fields.get("supplier_gstin") is None
    assert p.fields.get("igst") is None and p.fields["cgst"] == D("512.45")


def test_round_off_above_one_rupee_is_replaced_when_totals_agree():
    rows = [(20, [(40, "TAX"), (70, "INVOICE")]), (40, [(40, "GSTIN:"), (80, SUP)]),
            (200, [(40, "Taxable"), (90, "Value"), (200, "87,503.88")]),
            (210, [(40, "CGST"), (200, "2,187.60")]), (220, [(40, "SGST"), (200, "2,187.60")]),
            (230, [(40, "Round"), (90, "Off"), (200, "7.00")]),
            (240, [(40, "Total"), (200, "91,879.00")])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    assert p.fields["round_off"] == D("-0.08")


def test_rate_read_as_tax_amount_is_replaced_by_checked_amount():
    rows = [(20, [(40, "TAX"), (70, "INVOICE")]), (40, [(40, "GSTIN:"), (80, SUP)]),
            (200, [(40, "Taxable"), (90, "Value"), (200, "45,027.60")]),
            (210, [(40, "CGST"), (200, "2.50")]), (215, [(300, "1,125.69")]), (220, [(40, "SGST"), (200, "2.50")]),
            (240, [(40, "Total"), (200, "47,279.00")])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    assert p.fields["cgst"] == D("1125.69") and p.fields["sgst"] == D("1125.69")


def test_rupee_sign_read_as_digit_in_total_is_corrected():
    rows = [(20, [(40, "TAX"), (70, "INVOICE")]), (40, [(40, "GSTIN:"), (80, SUP)]),
            (200, [(40, "Taxable"), (90, "Value"), (200, "2,970.00")]),
            (210, [(40, "CGST"), (200, "74.25")]), (220, [(40, "SGST"), (200, "74.25")]),
            (230, [(40, "Round"), (90, "Off"), (200, "0.50")]),
            (240, [(40, "Total"), (90, "Amount"), (200, "23,119.00")]),
            (250, [(40, "THREE"), (90, "THOUSAND"), (150, "ONE"), (180, "HUNDRED"), (230, "AND"), (260, "NINETEEN"),
                   (310, "RUPEES"), (350, "ONLY")])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    assert p.fields["invoice_total"] == D("3119")


def test_gstin_without_label_is_found():
    rows = [(20, [(40, "TAX"), (70, "INVOICE")]), (30, [(40, "-OB" + SUP[2:]), (200, "TAX")])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    assert p.fields.get("supplier_gstin") == SUP


def test_ocr_engine_choice(monkeypatch):
    from ipt.services.extraction import sources
    monkeypatch.setenv("IPT_OCR_ENGINE", "tesseract")
    assert sources.ocr_engine() == "tesseract"
    monkeypatch.setenv("IPT_OCR_ENGINE", "auto")
    assert sources.ocr_engine() == ("rapidocr" if sources.rapid_available() else "tesseract")


def test_item_rate_misread_by_one_digit_is_repaired_and_header_over_two_lines():
    rows = [(100, [(250, "HSN/SAC Quantity"), (370, "Rate"), (410, "per"), (450, "Amount")]),
            (104, [(40, "Descrption of Gcods")]),
            (125, [(250, "25210090 28.130 MT"), (370, "615.00"), (410, "MT"), (450, "22,925.95")]),
            (132, [(40, "Lime Stone Chips")]),
            (150, [(40, "OUTPUT"), (90, "CGST"), (400, "573.15")]),
            (300, [(40, "Total"), (400, "24,072.00")])]
    p = parse(_lines(rows), from_ocr=True, company_gstin=OWN)
    (it,) = p.items
    assert it["description"] == "Lime Stone Chips" and it["hsn_sac"] == "25210090"
    assert it["qty"] == D("28.130") and it["unit"] == "MT"
    assert it["rate"] == D("815.00") and it["taxable_value"] == D("22925.95")   # 615 -> 815, checked by qty x rate
    assert p.item_confidence <= 0.65
