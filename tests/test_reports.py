import pytest
from app.main import app
from app.services import report_service
from app.core.dependencies import require_any_staff, require_admin
from app.models.user import User

def test_report_service_excel_daybook(db_session):
    excel_bytes = report_service.generate_excel_daybook_report(db_session)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

def test_report_service_pdf_daybook(db_session):
    pdf_bytes = report_service.generate_pdf_daybook_report(db_session)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_report_service_excel_cash_rec(db_session):
    excel_bytes = report_service.generate_excel_cash_reconciliation_report(db_session)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

def test_report_service_pdf_cash_rec(db_session):
    pdf_bytes = report_service.generate_pdf_cash_reconciliation_report(db_session)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_report_service_excel_card_qr(db_session):
    excel_bytes = report_service.generate_excel_card_qr_report(db_session)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

def test_report_service_pdf_card_qr(db_session):
    pdf_bytes = report_service.generate_pdf_card_qr_report(db_session)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_report_service_excel_aggregator(db_session):
    excel_bytes = report_service.generate_excel_aggregator_report(db_session)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

def test_report_service_pdf_aggregator(db_session):
    pdf_bytes = report_service.generate_pdf_aggregator_report(db_session)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_report_service_excel_audit(db_session):
    excel_bytes = report_service.generate_excel_audit_report(db_session)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

def test_report_service_pdf_audit(db_session):
    pdf_bytes = report_service.generate_pdf_audit_report(db_session)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

def test_analytics_summary_data(db_session):
    data = report_service.get_analytics_summary_data(db_session)
    assert "channel_distribution" in data
    assert "sales_trend" in data
    assert "branch_performance" in data
    assert "reconciliation_status" in data

def test_export_api_endpoints(client, db_session):
    mock_user = User(id=1, email="admin@test.com", full_name="Admin User", is_active=True)
    app.dependency_overrides[require_any_staff] = lambda: mock_user
    app.dependency_overrides[require_admin] = lambda: mock_user

    # Test daybook Excel & PDF API
    r1 = client.get("/api/reports/export/daybook/excel")
    assert r1.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in r1.headers["content-type"]

    r2 = client.get("/api/reports/export/daybook/pdf")
    assert r2.status_code == 200
    assert "application/pdf" in r2.headers["content-type"]

    # Test Cash Rec PDF API
    r3 = client.get("/api/reports/export/cash-rec/pdf")
    assert r3.status_code == 200

    # Test Card/QR PDF API
    r4 = client.get("/api/reports/export/card-qr/pdf")
    assert r4.status_code == 200

    # Test Aggregator PDF API
    r5 = client.get("/api/reports/export/aggregator/pdf")
    assert r5.status_code == 200

    # Test Analytics API
    r6 = client.get("/api/reports/analytics")
    assert r6.status_code == 200
    assert "channel_distribution" in r6.json()

def test_export_api_empty_query_params(client, db_session):
    mock_user = User(id=1, email="admin@test.com", full_name="Admin User", is_active=True)
    app.dependency_overrides[require_any_staff] = lambda: mock_user
    app.dependency_overrides[require_admin] = lambda: mock_user

    # Test empty string query params (which previously triggered 422 errors)
    r1 = client.get("/api/reports/export/daybook/excel?branch_id=&start_date=&end_date=")
    assert r1.status_code == 200

    r2 = client.get("/api/reports/export/daybook/pdf?branch_id=&start_date=&end_date=")
    assert r2.status_code == 200

    r3 = client.get("/api/reports/export/cash-rec/excel?branch_id=&start_date=&end_date=")
    assert r3.status_code == 200

    r4 = client.get("/api/reports/export/card-qr/pdf?branch_id=&start_date=&end_date=&status=")
    assert r4.status_code == 200

    r5 = client.get("/api/reports/export/aggregator/excel?aggregator_id=&branch_id=&start_date=&end_date=")
    assert r5.status_code == 200

    r6 = client.get("/api/reports/analytics?branch_id=&start_date=&end_date=")
    assert r6.status_code == 200


def test_pdf_letterhead_uses_client_database_details(db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("RESTRORECO_DATA_DIR", str(tmp_path))
    from io import BytesIO

    import pdfplumber

    from app.services.client_store import add_client
    from app.services.pdf_header import CLIENT_TOP_MARGIN, get_report_client, header_top_margin
    from app.services.gst_report_service import generate_pdf_gst_report

    client = add_client(
        "Omega Kitchen Pvt Ltd",
        address="12 MG Road, Noida, Uttar Pradesh",
        gstin="09AABCU9603R1ZM",
    )
    assert client["name"] == "Omega Kitchen Pvt Ltd"
    info = get_report_client()
    assert info["name"] == "Omega Kitchen Pvt Ltd"
    assert info["address"] == "12 MG Road, Noida, Uttar Pradesh"
    assert info["gstin"] == "09AABCU9603R1ZM"
    assert header_top_margin() == CLIENT_TOP_MARGIN

    pdf_bytes = report_service.generate_pdf_daybook_report(db_session)
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    assert "Omega Kitchen Pvt Ltd" in text
    assert "09AABCU9603R1ZM" in text
    assert "12 MG Road" in text

    gst_pdf = generate_pdf_gst_report(db_session)
    with pdfplumber.open(BytesIO(gst_pdf)) as pdf:
        gst_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    assert "Omega Kitchen Pvt Ltd" in gst_text
    assert "GSTIN: 09AABCU9603R1ZM" in gst_text


def test_export_period_label_uses_financial_year():
    from datetime import date

    from app.services.report_service import _export_period_label

    assert _export_period_label(date(2026, 4, 1), date(2027, 3, 31)) == "FY 2026-27"
    assert _export_period_label(date(2026, 8, 1), date(2026, 8, 31)) == "August 2026"

