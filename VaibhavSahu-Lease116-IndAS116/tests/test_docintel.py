"""Agreement-reader tests on fictional sample agreements (digital PDF, scanned PDF, Word, text)."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.docintel.ocr import rapidocr_available
from app.docintel.pipeline import run_pipeline
from app.docintel.textfix import normalize_ocr_text
from app.docintel.textnum import find_amounts, find_dates, find_durations, words_to_number
from app.docintel.verify import verify_quote

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "agreements"


def _fields(res):
    return {k: v["value"] for k, v in res.fields.items()}


def test_indian_amount_words_and_dates():
    a = find_amounts("a monthly fee of Rs. 4,50,000/- (Rupees Four Lakh Fifty Thousand Only)")[0]
    assert a.value == Decimal("450000") and a.words_match is True
    assert words_to_number("Rupees One Crore Twenty Five Lakh Only") == Decimal("12500000")
    assert [d.value for d in find_dates("on this 15th day of March, 2025 till 31/03/2030")] == [date(2025, 3, 15), date(2030, 3, 31)]
    assert find_durations("a period of 60 (sixty) months")[0][0] == 60
    assert find_durations("lock-in of three (3) years")[0][0] == 36


def test_ocr_text_repair():
    fixed = normalize_ocr_text("hereinafter referred toas the\"Lessor\"AND LMNRetail PrivateLimited foraperiodof9(nine)years")
    assert "referred to as" in fixed and "LMN Retail Private Limited" in fixed and "for a period of 9 (nine) years" in fixed


def test_quote_verification_rejects_hallucination():
    pages = [(1, "The licence fee shall be Rs. 4,50,000 per month payable in advance.")]
    assert verify_quote("licence fee shall be Rs. 4,50,000 per month", pages)[0] is True
    assert verify_quote("licence fee shall be Rs. 5,00,000 per month plus maintenance", pages)[0] is False


def test_evidence_sentence_boundaries_after_figures_and_clause_numbers():
    """Evidence quotes stop at a sentence that ends with a figure, but not at clause numbers or abbreviations."""
    from app.docintel.rules import DocText
    t = ("LEASE AGREEMENT\nThis Lease Agreement is made at Pune on this 10th day of March, 2025.\n"
         "1. The Lessor leases the premises for a period of 36 months commencing from 1st April, 2025.\n"
         "2. The Lessee shall pay a monthly rent of Rs. 1,50,000 on or before the 5th day of each month. "
         "3. The deposit is Rs. 9,00,000. The rate is 7.5. See clause 2.3. Done")
    dt = DocText([(1, t)])

    def quote(word):
        a, b = dt.sentence(t.index(word))
        return dt.ev(a, b).quote

    assert quote("commencing") == "1. The Lessor leases the premises for a period of 36 months commencing from 1st April, 2025."
    assert quote("monthly rent") == "2. The Lessee shall pay a monthly rent of Rs. 1,50,000 on or before the 5th day of each month."
    assert quote("deposit") == "3. The deposit is Rs. 9,00,000."
    assert quote("rate is") == "The rate is 7.5."
    assert quote("See clause") == "See clause 2.3."


def test_premises_description_stops_before_term():
    from app.docintel.rules import RuleExtractor
    for t in ("1. The Lessor hereby leases to the Lessee the warehouse bearing Shed No. B-2 situated at Sample Industrial Estate, "
              "Bhiwandi admeasuring 40,000 sq. ft. for a period of 9 (nine) years commencing from 1st February, 2025.",
              "1. The Lessor hereby leases to the Lessee the warehouse bearing Shed No. B-2 situated at Sample Industrial Estate, "
              "Bhiwandi admeasuring 40,000 sq. ft.for a period of 9 (nine) years commencing from 1st February, 2025."):
        c = RuleExtractor([(1, t)]).run()
        assert c["asset_description"][0].value == ("warehouse bearing Shed No. B-2 situated at Sample Industrial Estate, "
                                                   "Bhiwandi admeasuring 40,000 sq. ft.")


def test_office_leave_and_license_pdf():
    res, doc = run_pipeline((SAMPLES / "Sample_Leave_and_License_Office.pdf").read_bytes(), "office.pdf")
    f = _fields(res)
    assert f["agreement_type"] == "LEAVE_AND_LICENSE"
    assert f["lessor_name"] == "ABC Realty Private Limited"
    assert f["lessee_name"] == "XYZ Technologies Private Limited"
    assert f["commencement_date"] == "2025-04-01" and f["expiry_date"] == "2030-03-31"
    assert f["tenure_months"] == 60 and f["lock_in_months"] == 36
    assert f["rent_amount"] == "450000" and f["rent_frequency"] == "MONTHLY"
    assert f["payment_timing"] == "ADVANCE" and f["payment_due_day"] == 7
    assert f["escalation_pct"] == "5" and f["escalation_every_months"] == 12
    assert f["rent_free_days"] == 60
    assert f["deposit_amount"] == "2700000" and f["deposit_interest_free"] is True
    assert f["cam_amount"] == "55000" and f["stamp_duty_amount"] == "118500"
    assert f["renewal_at_option_of"] == "MUTUAL" and f["lessee_termination_notice_months"] == 3
    assert f["restoration_obligation"] is True and f["sublease_permitted"] is False
    assert res.missing_essentials == []
    codes = {x["code"] for x in res.flags}
    assert {"LOCK_IN_TERM", "RENEWAL_MUTUAL", "DEPOSIT_IND_AS_109", "RENT_FREE", "NON_LEASE", "RESTORATION", "IDC"} <= codes
    d = res.draft
    assert d["payment_terms"]["due_day"] == 7 and d["payment_terms"]["alignment"] == "CALENDAR"
    assert d["options"][0]["kind"] == "TERMINATION" and d["options"][0]["exercise_date"] == "2028-03-31"
    assert d["deposit"]["refund_date"] == "2030-04-01"
    assert {i["description"] for i in d["idc"]} == {"Stamp duty (e-stamp)", "Brokerage"}
    # evidence boxes exist for highlighted fields on the digital PDF
    assert res.fields["rent_amount"]["boxes"]


def test_equipment_docx_purchase_option():
    res, _ = run_pipeline((SAMPLES / "Sample_Equipment_Lease.docx").read_bytes(), "equipment.docx")
    f = _fields(res)
    assert f["agreement_type"] == "EQUIPMENT_LEASE"
    assert f["lessor_name"] == "DEF Leasing Limited" and f["lessee_name"] == "GHI Auto Components Private Limited"
    assert f["commencement_date"] == "2025-07-01" and f["tenure_months"] == 36
    assert f["rent_amount"] == "600000" and f["rent_frequency"] == "QUARTERLY" and f["payment_timing"] == "ARREARS"
    assert f["purchase_option_price"] == "500000"
    assert f["substitution_right"] is True
    assert any(o["kind"] == "PURCHASE" for o in res.draft["options"])


def test_retail_variable_rent():
    res, _ = run_pipeline((SAMPLES / "Sample_Retail_Lease_Revenue_Share.txt").read_bytes(), "retail.txt")
    f = _fields(res)
    assert f["rent_amount"] == "300000" and f["tenure_months"] == 108
    assert f["variable_rent"] and "revenue share" in f["variable_rent"].lower()
    assert f["cam_amount"] == "225000"          # Rs. 90 psf x 2,500 sq ft, derived
    assert "VARIABLE_RENT" in {x["code"] for x in res.flags}


class FakeLLM:
    name = "fake"
    model = "fake-model"

    def extract(self, pages, keys=None):
        return {
            "rent_amount": {"value": "450000", "quote": "monthly license fee of Rs. 4,50,000/-", "page": 2, "confidence": 0.9},
            "lessor_name": {"value": "ABC Realty Pvt Ltd", "quote": "ABC Realty Private Limited, a company", "page": 2, "confidence": 0.9},
            "deposit_amount": {"value": "3000000", "quote": "security deposit of Rs. 30,00,000", "page": 3, "confidence": 0.95},
            "purchase_option_price": {"value": "999", "quote": "option to purchase at Rs. 999", "page": 1, "confidence": 0.9},
        }


def test_pipeline_merge_with_llm_agreement_conflict_and_hallucination():
    res, _ = run_pipeline((SAMPLES / "Sample_Leave_and_License_Office.pdf").read_bytes(), "office.pdf", llm=FakeLLM(),
                          provider_name="fake")
    fr = res.fields
    assert fr["rent_amount"]["status"] == "AGREED" and fr["rent_amount"]["confidence"] >= 0.95
    assert fr["deposit_amount"]["status"] == "CONFLICT" and fr["deposit_amount"]["value"] == "2700000"
    assert fr["purchase_option_price"]["status"] == "AI_UNVERIFIED" and fr["purchase_option_price"]["confidence"] <= 0.35


@pytest.mark.skipif(not rapidocr_available(), reason="RapidOCR not installed")
def test_scanned_warehouse_ocr_and_computer_vision():
    res, doc = run_pipeline((SAMPLES / "Sample_Warehouse_Lease_Deed_SCANNED.pdf").read_bytes(), "warehouse.pdf")
    f = _fields(res)
    assert doc.ocr_used
    assert f["lessor_name"] == "PQR Logistics Parks LLP" and f["lessee_name"] == "LMN Retail Private Limited"
    assert f["commencement_date"] == "2025-02-01" and f["tenure_months"] == 108
    assert f["rent_amount"] == "1200000" and f["deposit_amount"] == "7200000"
    assert f["escalation_pct"] == "15" and f["escalation_every_months"] == 36
    assert f["renewal_at_option_of"] == "LESSEE"
    page = res.document["page_info"][0]
    assert page["vision"]["stamps"], "blue seal should be detected by computer vision"
    assert abs(page["vision"]["skew_angle"]) > 1.0, "tilted scan should be deskewed"
    assert "STAMP_DETECTED" in {x["code"] for x in res.flags}
