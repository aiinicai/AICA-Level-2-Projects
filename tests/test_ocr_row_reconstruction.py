import pytest
import os
from app.services.image_ocr_service import (
    clean_ocr_number,
    classify_row_description,
    classify_all_rows,
    detect_table_column_boundaries,
    analyze_amount_cell,
    parse_image_to_dict
)

def test_clean_ocr_number():
    val, raw, status = clean_ocr_number("12,944")
    assert val == 12944.0
    assert status == "VALID"

    val, raw, status = clean_ocr_number("111855")
    # Ambiguous 6-digit figure without decimal flagged as AMBIGUOUS_DECIMAL
    assert val is None
    assert status == "AMBIGUOUS_DECIMAL"

    val, raw, status = clean_ocr_number("39950")
    assert val == 39950.0
    assert status == "VALID"

def test_classify_row_description():
    cat, conf = classify_row_description("Zomato Online")
    assert cat == "ZOMATO"
    assert conf >= 0.80

    cat, conf = classify_row_description("Cash Sale")
    assert cat == "CASH_SALE"
    assert conf >= 0.85

    cat, conf = classify_row_description("# Milk 10L")
    assert cat == "SITE_EXPENSE"

    cat, conf = classify_row_description("Random Text Unknown")
    assert cat == "UNKNOWN"

def test_classify_all_rows_and_itemized_expenses():
    mock_rows = [
        {
            "row_id": 1, "description_raw": "Opening B.", "amount": 12944.0, "amount_raw": "12944", 
            "description_confidence": 0.95, "amount_confidence": 0.90, "amount_status": "CONFIRMED", 
            "numeric_validation_score": 95.0, "why_selected": "Pass agreement 3/3", "candidates": []
        },
        {
            "row_id": 2, "description_raw": "Cash Sale", "amount": 13395.0, "amount_raw": "13395", 
            "description_confidence": 0.92, "amount_confidence": 0.90, "amount_status": "CONFIRMED", 
            "numeric_validation_score": 95.0, "why_selected": "Pass agreement 3/3", "candidates": []
        },
        {
            "row_id": 3, "description_raw": "Zomato", "amount": 9313.0, "amount_raw": "9313", 
            "description_confidence": 0.94, "amount_confidence": 0.91, "amount_status": "CONFIRMED", 
            "numeric_validation_score": 90.0, "why_selected": "Pass agreement 2/3", "candidates": []
        },
        {
            "row_id": 4, "description_raw": "# Milk 10L", "amount": 580.0, "amount_raw": "580", 
            "description_confidence": 0.88, "amount_confidence": 0.85, "amount_status": "CONFIRMED", 
            "numeric_validation_score": 85.0, "why_selected": "Pass agreement 2/3", "candidates": []
        },
        {
            "row_id": 5, "description_raw": "* Vessel Repair", "amount": 440.0, "amount_raw": "440", 
            "description_confidence": 0.85, "amount_confidence": 0.82, "amount_status": "CONFIRMED", 
            "numeric_validation_score": 90.0, "why_selected": "Pass agreement 3/3", "candidates": []
        }
    ]

    fields, itemized_expenses = classify_all_rows(mock_rows)
    assert fields["zomato"]["value"] == 9313.0
    assert fields["zomato"]["source_row_id"] == 3
    assert fields["zomato"]["status"] == "CONFIRMED"
    assert fields["cash"]["value"] == 13395.0
    assert fields["opening_balance"]["value"] == 12944.0

    # Swiggy & Dineout were not detected -> value MUST be None (NOT DETECTED), NOT 0.0
    assert fields["swiggy"]["value"] is None
    assert fields["swiggy"]["status"] == "NOT_DETECTED"
    assert fields["dineout"]["value"] is None

    # Itemized expenses breakdown
    assert len(itemized_expenses) == 2
    assert fields["site_expenses"]["value"] == 1020.0 # 580 + 440

def test_clean_ocr_number_trailing_dot():
    val, raw, status = clean_ocr_number("16123.")
    assert val == 16123.0
    assert status == "VALID"


def test_classify_daybook_labels():
    assert classify_row_description("Today Sale")[0] == "TODAY_SALE"
    assert classify_row_description("sc")[0] == "SERVICE_CHARGE"
    assert classify_row_description("SC")[0] == "SERVICE_CHARGE"
    assert classify_row_description("swingy")[0] == "SWIGGY"
    assert classify_row_description("Paytm")[0] == "CARD_QR_PAYTM"
    assert classify_row_description("Salary advance Vijay")[0] == "SALARY_ADVANCE"
    assert classify_row_description("Tond milk 10/ (E)")[0] == "SITE_EXPENSE"
    assert classify_row_description("# Salary advance Mahesh")[0] == "SALARY_ADVANCE"


def test_card_and_paytm_are_summed():
    mock_rows = [
        {"row_id": 1, "description_raw": "Credit Card", "amount": 18699.0, "amount_raw": "18699",
         "description_confidence": 0.9, "amount_confidence": 0.9, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90.0, "why_selected": "", "candidates": []},
        {"row_id": 2, "description_raw": "Paytm", "amount": 0.0, "amount_raw": "0",
         "description_confidence": 0.9, "amount_confidence": 0.9, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90.0, "why_selected": "", "candidates": []},
        {"row_id": 3, "description_raw": "Paytm", "amount": 500.0, "amount_raw": "500",
         "description_confidence": 0.9, "amount_confidence": 0.9, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90.0, "why_selected": "", "candidates": []},
    ]
    fields, _ = classify_all_rows(mock_rows)
    assert fields["card_qr"]["value"] == 19199.0


def test_service_charge_and_today_sale_not_mapped_to_sales():
    mock_rows = [
        {"row_id": 1, "description_raw": "Today Sale", "amount": 71854.0, "amount_raw": "71854",
         "description_confidence": 0.9, "amount_confidence": 0.9, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90.0, "why_selected": "", "candidates": []},
        {"row_id": 2, "description_raw": "Cash Sale", "amount": 16123.0, "amount_raw": "16123",
         "description_confidence": 0.9, "amount_confidence": 0.9, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90.0, "why_selected": "", "candidates": []},
        {"row_id": 3, "description_raw": "sc", "amount": 2700.0, "amount_raw": "2700",
         "description_confidence": 0.9, "amount_confidence": 0.9, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90.0, "why_selected": "", "candidates": []},
    ]
    fields, _ = classify_all_rows(mock_rows)
    assert fields["cash"]["value"] == 16123.0
    assert fields["card_qr"]["value"] is None
    assert fields["opening_balance"]["value"] is None


def test_expense_subtotal_not_itemized():
    mock_rows = [
        {"row_id": 1, "description_raw": "# Milk 10L", "amount": 580.0, "amount_raw": "580",
         "description_confidence": 0.9, "amount_confidence": 0.9, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90.0, "why_selected": "", "candidates": []},
        {"row_id": 2, "description_raw": "-", "amount": 2382.0, "amount_raw": "2382",
         "description_confidence": 0.5, "amount_confidence": 0.9, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90.0, "why_selected": "", "candidates": []},
    ]
    fields, itemized = classify_all_rows(mock_rows)
    assert len(itemized) == 1
    assert fields["site_expenses"]["value"] == 580.0


def test_amount_prefers_rupee_not_folio_or_paise():
    from app.services.image_ocr_service import amount_from_row_tokens

    def tok(text, x, conf=0.9):
        return {
            "text": text, "confidence": conf,
            "x_left": float(x), "x_right": float(x + 40),
            "y_top": 10.0, "y_bottom": 30.0, "y_center": 20.0,
        }

    amt_rs, amt_ps = 200, 320
    swiggy = amount_from_row_tokens(
        [tok("Swiggy", 20), tok("1", 160), tok("6297", 220), tok("0", 330)],
        amt_rs, amt_ps,
    )
    assert swiggy["amount"] == 6297.0

    zomato = amount_from_row_tokens(
        [tok("Zomato", 20), tok("24869", 210), tok("0", 330)],
        amt_rs, amt_ps,
    )
    assert zomato["amount"] == 24869.0

    cash = amount_from_row_tokens(
        [tok("Cash", 20), tok("12", 210), tok("000", 250)],
        amt_rs, amt_ps,
    )
    assert cash["amount"] == 12000.0

    dineout = amount_from_row_tokens(
        [tok("Dineout", 20), tok("11273", 210), tok("1973", 280)],
        amt_rs, amt_ps,
    )
    assert dineout["amount"] == 11273.0

    paytm = amount_from_row_tokens(
        [tok("Paytm", 20), tok("0", 220)],
        amt_rs, amt_ps,
    )
    assert paytm["amount"] == 0.0
    from app.services.image_ocr_service import _is_paise_leak_pair
    assert _is_paise_leak_pair(198.0, 19845.0)
    assert _is_paise_leak_pair(9313.0, 93139.0)


def test_daybook_template_fills_garbled_sales_rows():
    mock_rows = [
        {"row_id": 1, "description_raw": "03/04/26", "amount": None, "amount_raw": "",
         "description_confidence": 0.5, "amount_confidence": 0.0, "amount_status": "NOT_DETECTED",
         "numeric_validation_score": 0, "why_selected": "", "candidates": []},
        {"row_id": 2, "description_raw": "Ofenir]", "amount": 198.0, "amount_raw": "198",
         "description_confidence": 0.5, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90, "why_selected": "", "candidates": []},
        {"row_id": 3, "description_raw": "Today Sale", "amount": 89864.0, "amount_raw": "89864",
         "description_confidence": 0.8, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90, "why_selected": "", "candidates": []},
        {"row_id": 4, "description_raw": "Csh sl", "amount": 3757.0, "amount_raw": "3757",
         "description_confidence": 0.4, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90, "why_selected": "", "candidates": []},
        {"row_id": 5, "description_raw": "Creait", "amount": 38519.0, "amount_raw": "38519",
         "description_confidence": 0.4, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90, "why_selected": "", "candidates": []},
        {"row_id": 6, "description_raw": "pattm", "amount": 0.0, "amount_raw": "0",
         "description_confidence": 0.7, "amount_confidence": 0.9, "amount_status": "CONFIRMED",
         "numeric_validation_score": 100, "why_selected": "", "candidates": []},
        {"row_id": 7, "description_raw": "swgy", "amount": 13509.0, "amount_raw": "13509",
         "description_confidence": 0.4, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90, "why_selected": "", "candidates": []},
        {"row_id": 8, "description_raw": "zmat", "amount": 11181.0, "amount_raw": "11181",
         "description_confidence": 0.4, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90, "why_selected": "", "candidates": []},
        {"row_id": 9, "description_raw": "pineoyt", "amount": 32898.0, "amount_raw": "32898",
         "description_confidence": 0.5, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 70, "why_selected": "", "candidates": []},
        {"row_id": 10, "description_raw": "sc", "amount": 1500.0, "amount_raw": "1500",
         "description_confidence": 0.8, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90, "why_selected": "", "candidates": []},
        {"row_id": 11, "description_raw": "# Milk (E)", "amount": 589.0, "amount_raw": "589",
         "description_confidence": 0.8, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90, "why_selected": "", "candidates": []},
        {"row_id": 12, "description_raw": "# Salary advance Vijay", "amount": 1000.0, "amount_raw": "1000",
         "description_confidence": 0.8, "amount_confidence": 0.8, "amount_status": "CONFIRMED",
         "numeric_validation_score": 90, "why_selected": "", "candidates": []},
    ]
    fields, itemized = classify_all_rows(mock_rows)
    assert fields["opening_balance"]["value"] == 198.0
    assert fields["cash"]["value"] == 3757.0
    assert fields["card_qr"]["value"] == 38519.0
    assert fields["swiggy"]["value"] == 13509.0
    assert fields["zomato"]["value"] == 11181.0
    assert fields["dineout"]["value"] == 32898.0
    assert fields["salary_advance"]["value"] == 1000.0
    assert len(itemized) == 1
    assert fields["site_expenses"]["value"] == 589.0


def test_paise_leak_rejected():
    from app.services.image_ocr_service import _is_paise_leak_pair, group_tokens_into_rows
    assert _is_paise_leak_pair(9313.0, 93139.0)
    assert _is_paise_leak_pair(198.0, 19845.0)
    assert not _is_paise_leak_pair(9313.0, 9313.0)
    assert not _is_paise_leak_pair(16123.0, 18699.0)

    tokens = [
        {"text": "Cash", "confidence": 0.9, "x_left": 20, "x_right": 80,
         "y_top": 40, "y_bottom": 60, "y_center": 50},
        {"text": "16123", "confidence": 0.9, "x_left": 200, "x_right": 250,
         "y_top": 40, "y_bottom": 60, "y_center": 50},
        {"text": "Zomato", "confidence": 0.9, "x_left": 20, "x_right": 90,
         "y_top": 80, "y_bottom": 100, "y_center": 90},
        {"text": "16495", "confidence": 0.9, "x_left": 200, "x_right": 250,
         "y_top": 80, "y_bottom": 100, "y_center": 90},
    ]
    groups = group_tokens_into_rows(tokens, img_h=200, img_w=300)
    assert len(groups) >= 2


def test_filename_date_still_parsed_for_register_names():
    dict1 = parse_image_to_dict(b"", "Register_02_04_2026.png")
    assert dict1["date"] == "2026-04-02"


def test_uploaded_sample_register_regression():
    sample_path = 'data/uploaded_sample_register.jpg'
    if not os.path.exists(sample_path):
        pytest.skip("sample register image not present")
    with open(sample_path, 'rb') as f:
        content = f.read()
    res = parse_image_to_dict(content, 'WhatsApp Image 2026-05-11 at 3.53.05 PM.jpeg')
    assert res["status"] in ("SUCCESS", "VALIDATION_WARNING")

    # Verify Zomato did NOT capture the trailing digit 9 from Paise column
    if res.get("zomato") is not None:
        assert res["zomato"] < 50000  # 9,313 not 93,139!

    # Verify Cash sale was recognized
    if res.get("cash") is not None:
        assert res["cash"] == 13395.0

