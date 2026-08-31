from datetime import date

from app.models.aggregator import Aggregator
from app.models.branch import Branch
from app.seed import seed_database
from app.services.aggregator_service import create_or_update_settlement_batch
from app.services.daybook_service import save_manual_daybook_entry
from app.services.gst_report_service import (
    apply_adjustment,
    compute_gst_payable,
    generate_pdf_gst_report,
    generate_table14_eco_csv,
    get_gst_payable_report,
    gst_inclusive_tax,
    gst_offline_figures,
    save_gst_adjustments,
    table14_row_from_tax,
)


def _post_sample_sales(db):
    seed_database(db=db)
    branch = db.query(Branch).filter(Branch.code == "NOIDA01").first()
    save_manual_daybook_entry(
        db, branch.id, date(2026, 4, 1),
        cash=1050, card_qr=2100, zomato=4200, swiggy=5250, dineout=3150,
    )
    save_manual_daybook_entry(
        db, branch.id, date(2026, 4, 2),
        cash=2100, card_qr=0, zomato=0, swiggy=0, dineout=0,
    )
    return branch


def test_gst_inclusive_tax_matches_sheet_formula():
    assert gst_inclusive_tax(29664) == 29664 * 5 / 105
    assert gst_inclusive_tax(105) == 5


def test_aggregator_net_is_packing_only_and_taxed():
    report = compute_gst_payable(
        [{
            "date": date(2026, 6, 1),
            "cash": 1050,
            "card_qr": 2100,
            "dineout": 3150,
            "zomato": 4200,
            "swiggy": 5250,
        }],
        packing={"zomato": 210, "swiggy": 105},
    )
    assert report["adjustment"]["zomato"] == 210
    assert report["adjustment"]["swiggy"] == 105
    assert report["net"]["zomato"] == 210
    assert report["net"]["swiggy"] == 105
    assert report["tax"]["zomato"] == 10
    assert report["tax"]["swiggy"] == 5
    assert report["tax"]["cash"] == 50
    assert report["tax_to_deposit"] == (
        report["tax"]["cash"] + report["tax"]["card_qr"] + report["tax"]["dineout"]
        + report["tax"]["zomato"] + report["tax"]["swiggy"]
    )
    assert report["tax_to_deposit"] == 50 + 100 + 150 + 10 + 5


def test_tax_to_deposit_without_packing_excludes_aggregator_sales():
    report = compute_gst_payable([
        {
            "date": date(2026, 6, 1),
            "cash": 1050,
            "card_qr": 2100,
            "dineout": 3150,
            "zomato": 4200,
            "swiggy": 5250,
        }
    ])
    assert report["net"]["zomato"] == 0
    assert report["tax"]["zomato"] == 0
    assert report["tax_to_deposit"] == 300
    assert report["basic_total"] == report["basic"]["cash"] + report["basic"]["card_qr"] + report["basic"]["dineout"]


def test_table14_reverses_5_percent_tax_and_splits_halves():
    figures = table14_row_from_tax(99666)
    assert figures["net"] == 1993320
    assert figures["cgst"] == 49833
    assert figures["sgst"] == 49833
    assert figures["igst"] == 0
    assert figures["cgst"] + figures["sgst"] == figures["tax"]


def test_offline_csv_uses_basic_and_splits_tax():
    report = compute_gst_payable([
        {
            "date": date(2026, 6, 1),
            "cash": 1050,
            "card_qr": 2100,
            "dineout": 3150,
            "zomato": 0,
            "swiggy": 0,
        }
    ])
    figures = gst_offline_figures(report)
    assert figures["basic_total"] == report["basic_total"]
    assert figures["cgst"] + figures["sgst"] == report["tax_to_deposit"]
    assert figures["total_value"] == figures["basic_total"] + figures["cgst"] + figures["sgst"]


def test_adjustment_add_and_less():
    assert apply_adjustment(100, 10, "less") == 90
    assert apply_adjustment(100, 10, "add") == 110
    report = compute_gst_payable(
        [{"date": date(2026, 6, 1), "cash": 1050, "card_qr": 0, "dineout": 0, "zomato": 0, "swiggy": 0}],
        {"mode": "less", "cash": 105, "available_balance": 10},
    )
    assert report["net"]["cash"] == 945
    assert report["tax"]["cash"] == 45
    assert report["available_balance"] == 10
    assert report["additional_requirement"] == 35


def test_gst_report_imports_packing_from_aggregator(db_session):
    branch = _post_sample_sales(db_session)
    zomato = db_session.query(Aggregator).filter(Aggregator.code == "ZOMATO").first()
    swiggy = db_session.query(Aggregator).filter(Aggregator.code == "SWIGGY").first()
    create_or_update_settlement_batch(
        db_session, "Z-PACK", zomato.id, branch.id, date(2026, 4, 1), date(2026, 4, 5),
        10000, 8000,
        deductions_data=[{"deduction_type": "PACKING_CHARGES", "amount": 210}],
    )
    create_or_update_settlement_batch(
        db_session, "S-PACK", swiggy.id, branch.id, date(2026, 4, 1), date(2026, 4, 5),
        8000, 6000,
        deductions_data=[{"deduction_type": "PACKING_CHARGES", "amount": 105}],
    )
    data = get_gst_payable_report(db_session, None, date(2026, 4, 1), date(2026, 4, 30))
    assert data["adjustment"]["zomato"] == 210
    assert data["adjustment"]["swiggy"] == 105
    assert data["net"]["zomato"] == 210
    assert data["tax"]["zomato"] == 10
    assert data["tax_to_deposit"] == data["tax"]["cash"] + data["tax"]["card_qr"] + data["tax"]["dineout"] + 10 + 5
    updated = save_gst_adjustments(
        db_session, None, date(2026, 4, 1), date(2026, 4, 30),
        "less", 100, 0, 0, 999, 999, 500,
    )
    assert updated["available_balance"] == 500
    assert updated["adjustment"]["cash"] == 100
    assert updated["adjustment"]["zomato"] == 210
    pdf = generate_pdf_gst_report(db_session, None, date(2026, 4, 1), date(2026, 4, 30))
    assert pdf.startswith(b"%PDF")


def test_table14_csv_uses_aggregator_s_no_11_tax(db_session):
    branch = _post_sample_sales(db_session)
    zomato = db_session.query(Aggregator).filter(Aggregator.code == "ZOMATO").first()
    swiggy = db_session.query(Aggregator).filter(Aggregator.code == "SWIGGY").first()
    create_or_update_settlement_batch(
        db_session, "Z-TAX", zomato.id, branch.id, date(2026, 4, 1), date(2026, 4, 5),
        10000, 8000,
        deductions_data=[{"deduction_type": "GST_9_5", "amount": 99666}],
    )
    create_or_update_settlement_batch(
        db_session, "S-TAX", swiggy.id, branch.id, date(2026, 4, 6), date(2026, 4, 12),
        8000, 6000,
        deductions_data=[{"deduction_type": "GST_9_5", "amount": 49016}],
    )
    payload, filename = generate_table14_eco_csv(db_session, None, date(2026, 4, 1), date(2026, 4, 30))
    text = payload.decode("utf-8-sig")
    assert filename.startswith("GST_TABLE14_ECO_9_5_")
    assert "Liable to pay tax u/s 9(5)" in text
    assert "09AADCD4946L1Z8" in text
    assert "ETERNAL LIMITED" in text
    assert "09AAFCB7707D1ZS" in text
    assert "1993320.00" in text
    assert "49833.00" in text
    assert "980320.00" in text
    assert "24508.00" in text


def test_gst_report_api_and_exports(client, db_session):
    _post_sample_sales(db_session)
    login = client.post("/api/auth/login", json={"email": "admin", "password": "admin"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    page = client.get("/gst-payable-report", headers=headers)
    assert page.status_code == 200
    assert b"GST Payable Report" in page.content
    assert b"Custom range" not in page.content
    assert b"Export Excel" not in page.content
    report = client.get(
        "/api/gst-report?start_date=2026-04-01&end_date=2026-04-30",
        headers=headers,
    )
    assert report.status_code == 200
    body = report.json()
    assert body["tax_to_deposit"] > 0
    saved = client.post("/api/gst-report/adjustments", json={
        "start_date": "2026-04-01",
        "end_date": "2026-04-30",
        "mode": "add",
        "cash": 50,
        "available_balance": 25,
    }, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["adjustment"]["mode"] == "add"
    excel = client.get("/api/gst-report/export/excel?start_date=2026-04-01&end_date=2026-04-30", headers=headers)
    pdf = client.get("/api/reports/export/gst/pdf?start_date=2026-04-01&end_date=2026-04-30", headers=headers)
    b2cs = client.get("/api/gst-report/export/b2cs?start_date=2026-04-01&end_date=2026-04-30", headers=headers)
    hsn = client.get("/api/gst-report/export/hsn-b2cs?start_date=2026-04-01&end_date=2026-04-30", headers=headers)
    table14 = client.get("/api/gst-report/export/table14?start_date=2026-04-01&end_date=2026-04-30", headers=headers)
    assert excel.status_code == 404
    assert pdf.status_code == 200
    assert b2cs.status_code == 200
    assert hsn.status_code == 200
    assert table14.status_code == 200
    table14_text = table14.content.decode("utf-8-sig")
    assert "Nature of Supply" in table14_text
    assert "Liable to pay tax u/s 9(5)" in table14_text
    assert "GSTIN of E-Commerce Operator" in table14_text
    b2cs_text = b2cs.content.decode("utf-8-sig")
    b2cs_headers = [h.strip() for h in b2cs_text.splitlines()[0].split(",")]
    b2cs_row = [c.strip() for c in b2cs_text.splitlines()[1].split(",")]
    assert "Place Of Supply" in b2cs_text
    assert "09-Uttar Pradesh" in b2cs_text
    assert b2cs_headers[-1] == "Rate"
    assert b2cs_row[-1] == "5"
    hsn_text = hsn.content.decode("utf-8-sig")
    hsn_headers = [h.strip() for h in hsn_text.splitlines()[0].split(",")]
    hsn_row = [c.strip() for c in hsn_text.splitlines()[1].split(",")]
    assert "996331" in hsn_text
    assert "Central Tax Amount" in hsn_text
    assert hsn_headers[-1] == "Rate"
    assert hsn_row[-1] == "5"
    assert "B2CS CSV" in page.text or b"B2CS CSV" in page.content
    assert "Table 14 CSV" in page.text or b"Table 14 CSV" in page.content
