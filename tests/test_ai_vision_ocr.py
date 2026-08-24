import io
from PIL import Image
from app.services.ai_vision_ocr import extract_daybook_with_ai, _num, _normalize_date


def test_num_parser():
    assert _num("12,000") == 12000.0
    assert _num(0) == 0.0
    assert _num(None) is None
    assert _num("-") is None


def test_ai_maps_daybook_json(monkeypatch):
    from app.services import ai_vision_ocr as svc

    monkeypatch.setattr(svc, "extract_figures_from_image", lambda _b: {
        "date": "2026-08-21",
        "opening_balance": 9382,
        "today_sale": 79277,
        "cash": 12000,
        "credit_card": 24853,
        "paytm": 0,
        "swiggy": 6297,
        "zomato": 24869,
        "dineout": 11273,
        "site_expenses": 8650,
        "salary_advance": None,
        "closing_balance": 198,
        "expense_items": [{"description": "Gas", "amount": 400}],
    })
    monkeypatch.setattr(svc, "get_gemini_api_key", lambda: "test-key")
    out = extract_daybook_with_ai(b"x", "sheet.jpg")
    assert out["status"] == "SUCCESS"
    assert out["date"] == "2026-08-21"
    assert out["cash"] == 12000.0
    assert out["card_qr"] == 24853.0
    assert out["swiggy"] == 6297.0
    assert out["zomato"] == 24869.0
    assert out["dineout"] == 11273.0
    assert out["opening_balance"] == 9382.0
    assert out["closing_balance"] == 198.0
    assert out["handwritten_total"] == 79277.0
    assert out["fields"]["card_qr"]["status"] == "CONFIRMED"


def test_normalize_iso_date():
    assert _normalize_date("2026-08-21", "WhatsApp Image 2026-05-06.jpeg") == "2026-08-21"


def test_normalize_named_month_date():
    assert _normalize_date("01 April 2026", "edc.jpg") == "2026-04-01"


def _reading(**kwargs):
    base = {
        "status": "SUCCESS",
        "date_from_document": True,
        "fields": {},
        "parsed_rows": [],
        "itemized_expenses": [],
        "handwritten_total": None,
        "processing_time_sec": 0.1,
    }
    base.update(kwargs)
    return base


def test_merge_prefers_pos_sales_and_cashbook_balances():
    from app.services.ai_vision_ocr import merge_register_readings

    merged = merge_register_readings([
        _reading(
            image_kind="DAYBOOK",
            filename="cashbook.jpg",
            date="2026-04-01",
            cash=471,
            card_qr=None,
            zomato=None,
            swiggy=None,
            dineout=None,
            opening_balance=1661,
            site_expenses=1658,
            salary_advance=None,
            closing_balance=474,
            itemized_expenses=[{"description": "Milk", "amount": 116}],
        ),
        _reading(
            image_kind="PETPOOJA",
            filename="pos.jpg",
            date="2026-04-01",
            cash=471,
            card_qr=4765,
            zomato=13897,
            swiggy=7645,
            dineout=None,
            opening_balance=None,
            site_expenses=None,
            salary_advance=None,
            closing_balance=None,
        ),
        _reading(
            image_kind="EDC",
            filename="edc.jpg",
            date="2026-04-01",
            cash=None,
            card_qr=4765,
            zomato=None,
            swiggy=None,
            dineout=None,
            opening_balance=None,
            site_expenses=None,
            salary_advance=None,
            closing_balance=None,
        ),
    ])
    assert merged["date"] == "2026-04-01"
    assert merged["cash"] == 471
    assert merged["card_qr"] == 4765
    assert merged["zomato"] == 13897
    assert merged["swiggy"] == 7645
    assert merged["opening_balance"] == 1661
    assert merged["site_expenses"] == 1658
    assert merged["closing_balance"] == 474
    assert merged["field_sources"]["cash"] == "PETPOOJA"
    assert merged["field_sources"]["card_qr"] == "PETPOOJA"
    assert merged["field_sources"]["opening_balance"] == "DAYBOOK"
    assert merged["field_sources"]["closing_balance"] == "DAYBOOK"
    assert merged["mismatches"] == []
    assert any(v["field"] == "cash" for v in merged["verifications"])
    assert any(v["field"] == "card_qr" for v in merged["verifications"])
    assert merged["calculated_total"] == 471 + 4765 + 13897 + 7645


def test_merge_flags_card_mismatch():
    from app.services.ai_vision_ocr import merge_register_readings

    merged = merge_register_readings([
        _reading(image_kind="PETPOOJA", filename="pos.jpg", date="2026-04-01",
                 cash=471, card_qr=4765, zomato=100, swiggy=0, dineout=None,
                 opening_balance=None, site_expenses=None, salary_advance=None, closing_balance=None),
        _reading(image_kind="EDC", filename="edc.jpg", date="2026-04-01",
                 cash=None, card_qr=4800, zomato=None, swiggy=None, dineout=None,
                 opening_balance=None, site_expenses=None, salary_advance=None, closing_balance=None),
    ])
    assert merged["card_qr"] == 4765
    assert merged["field_sources"]["card_qr"] == "PETPOOJA"
    assert any(m["field"] == "card_qr" for m in merged["mismatches"])


def test_merge_uses_daybook_cash_when_pos_missing():
    from app.services.ai_vision_ocr import merge_register_readings

    merged = merge_register_readings([
        _reading(image_kind="DAYBOOK", filename="cashbook.jpg", date="2026-04-01",
                 cash=471, card_qr=None, zomato=None, swiggy=None, dineout=None,
                 opening_balance=1661, site_expenses=458, salary_advance=None, closing_balance=474),
        _reading(image_kind="EDC", filename="edc.jpg", date="2026-04-01",
                 cash=None, card_qr=4765, zomato=None, swiggy=None, dineout=None,
                 opening_balance=None, site_expenses=None, salary_advance=None, closing_balance=None),
    ])
    assert merged["cash"] == 471
    assert merged["field_sources"]["cash"] == "DAYBOOK"
    assert merged["card_qr"] == 4765
    assert merged["field_sources"]["card_qr"] == "EDC"


def test_parse_image_requires_ai_key_for_real_photo(monkeypatch):
    from app.services.image_ocr_service import parse_image_to_dict
    from app.services import ai_vision_ocr as svc

    monkeypatch.setattr(svc, "ai_ocr_configured", lambda: False)
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, format="JPEG")
    out = parse_image_to_dict(buf.getvalue(), "daybook.jpg")
    assert out["status"] == "ERROR"
    assert "Gemini" in out["error_detail"]
