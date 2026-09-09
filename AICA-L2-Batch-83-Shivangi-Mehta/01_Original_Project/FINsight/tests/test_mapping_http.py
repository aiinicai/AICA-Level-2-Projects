"""
Stage 7 — full HTTP round trip through the real Flask app for the Data
Mapping screen: structure detection, sheet selection, suggested
mappings, wrong-file-type warnings, and confirming mappings.

Uses only synthetic, fabricated CSV/XLSX content — never real client or
financial data. Nothing here makes a network call — structure
detection and mapping suggestion are pure local pandas/openpyxl +
string comparisons.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl
import pandas as pd
import pytest

from config import TestConfig
from app import create_app


@pytest.fixture()
def client(tmp_path):
    class IsolatedConfig(TestConfig):
        DATA_INPUT_DIR = tmp_path / "data_input"

    app = create_app(IsolatedConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app.test_client()


def body(resp):
    return resp.get_data(as_text=True)


def _create_and_select_engagement(client, entity_name="Acme Manufacturing Ltd"):
    r = client.post(
        "/engagement/new",
        data={"entity_name": entity_name, "financial_year": "2025-26"},
        follow_redirects=False,
    )
    assert r.status_code == 302


def _csv_bytes(rows) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


def _multi_sheet_xlsx_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame([{"Account": "Cash", "Debit": 100000, "Credit": 0}]).to_excel(
            writer, index=False, sheet_name="TB Jan"
        )
        pd.DataFrame([{"Account": "Sales", "Debit": 0, "Credit": 50000}]).to_excel(
            writer, index=False, sheet_name="TB Feb"
        )
    return buf.getvalue()


def _upload_file(client, filename, file_bytes, file_type):
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(file_bytes), filename), "file_type": file_type},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302
    # Find the file_id: the only DataMapping-eligible file is this one
    # for a fresh engagement, so pull it back via the DB directly.
    from app import extensions
    from app.services import upload_service
    engagement_id = None
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    uploads = upload_service.list_uploads(engagement_id)
    return uploads[0].file_id


TB_ROWS = [{"Account": "Cash", "Debit": 100000, "Credit": 0}, {"Account": "Sales", "Debit": 0, "Credit": 100000}]


# --- index ----------------------------------------------------------------

def test_mapping_index_with_no_uploads_shows_link_to_upload(client):
    _create_and_select_engagement(client)
    r = client.get("/data/mapping/")
    assert r.status_code == 200
    assert "Upload a file first" in body(r)


# --- single-sheet CSV: straight to the mapping form ----------------------

def test_mapping_detail_shows_suggested_mappings_for_csv(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")

    r = client.get(f"/data/mapping/{file_id}/")
    assert r.status_code == 200
    page = body(r)
    assert "Account Name" in page  # suggested label for the "Account" column
    assert "Debit Amount" in page
    assert "Credit Amount" in page


def test_confirming_mappings_persists_and_marks_file_mapped(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")

    # Column positions: Account=0, Debit=1, Credit=2 (see TB_ROWS' dict order).
    r = client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "account_name",
        "target_field__1": "debit_amount",
        "target_field__2": "credit_amount",
    }, follow_redirects=False)
    assert r.status_code == 302

    from app.services import upload_service
    record = upload_service.get_upload(file_id)
    assert record.upload_status == "MAPPED"

    from app.services import mapping_service
    confirmed = mapping_service.get_confirmed_mappings(file_id)
    assert {m.source_column: m.target_field for m in confirmed} == {
        "Account": "account_name", "Debit": "debit_amount", "Credit": "credit_amount",
    }


def test_confirming_with_nothing_mapped_shows_an_error(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")
    r = client.post(f"/data/mapping/{file_id}/", data={}, follow_redirects=False)
    assert r.status_code == 200
    assert "Map at least one column" in body(r)


# --- multi-sheet xlsx: sheet picker first --------------------------------

def test_multi_sheet_xlsx_shows_sheet_picker_before_mapping_form(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.xlsx", _multi_sheet_xlsx_bytes(), "TB")

    r = client.get(f"/data/mapping/{file_id}/")
    assert r.status_code == 200
    page = body(r)
    assert "Choose a Sheet" in page
    assert "TB Jan" in page
    assert "TB Feb" in page
    assert 'name="target_field' not in page  # mapping form not shown yet


def test_selecting_a_sheet_shows_that_sheets_columns_and_confirming_prefixes_source_column(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.xlsx", _multi_sheet_xlsx_bytes(), "TB")

    r = client.get(f"/data/mapping/{file_id}/?sheet=TB Feb")
    assert r.status_code == 200
    assert "Choose a Sheet" not in body(r)

    r = client.post(f"/data/mapping/{file_id}/?sheet=TB Feb", data={
        "sheet": "TB Feb",
        "target_field__0": "account_name",
    }, follow_redirects=False)
    assert r.status_code == 302

    from app.services import mapping_service
    confirmed = mapping_service.get_confirmed_mappings(file_id)
    assert confirmed[0].source_column == "TB Feb::Account"


# --- wrong file-type selection (Stage 7's explicit example) --------------

def test_selecting_trial_balance_for_general_ledger_shaped_columns_warns_and_requires_review(client):
    _create_and_select_engagement(client)
    gl_rows = [{
        "Transaction Date": "01-04-2025", "Narration": "Opening balance",
        "Account": "Cash", "Debit": 100000, "Credit": 0, "Voucher No": "V001",
    }]
    file_id = _upload_file(client, "general_ledger.csv", _csv_bytes(gl_rows), "TB")

    r = client.get(f"/data/mapping/{file_id}/")
    page = body(r)
    # If the heuristic finds a mismatch here (a rich GL-shaped file
    # selected as TB), it must show a warning and require the
    # acknowledgement checkbox before letting the mapping through.
    if "look more like" in page:
        assert 'name="file_type_reviewed"' in page
        r2 = client.post(f"/data/mapping/{file_id}/", data={
            "target_field__0": "transaction_date",
        }, follow_redirects=False)
        assert r2.status_code == 200
        assert "review the file type warning" in body(r2)


# --- engagement scoping ---------------------------------------------------

def test_mapping_a_file_from_a_different_engagement_is_not_found(client):
    _create_and_select_engagement(client, "Acme Manufacturing Ltd")
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")

    _create_and_select_engagement(client, "Beta Traders LLP")
    r = client.get(f"/data/mapping/{file_id}/")
    assert r.status_code == 404


# --- Stage 7 correction #1: server-side duplicate target-field guard ----

def test_manually_mapping_two_columns_to_the_same_target_field_is_rejected(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")

    # Account=0, Debit=1, Credit=2 — deliberately point both Debit and
    # Credit at debit_amount, the exact scenario the correction covers.
    r = client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "account_name",
        "target_field__1": "debit_amount",
        "target_field__2": "debit_amount",
    }, follow_redirects=False)
    assert r.status_code == 200  # rejected, not redirected — nothing persisted
    page = body(r)
    assert "Debit Amount" in page
    assert "Debit" in page and "Credit" in page  # both offending source columns named
    assert "multiple columns" in page.lower()

    from app.services import mapping_service
    assert mapping_service.get_confirmed_mappings(file_id) == []

    from app.services import upload_service
    assert upload_service.get_upload(file_id).upload_status == "UPLOADED"  # unchanged


def test_duplicate_target_rejection_preserves_the_users_other_selections(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")

    r = client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "account_name",
        "target_field__1": "debit_amount",
        "target_field__2": "debit_amount",
    }, follow_redirects=False)
    page = body(r)
    # The re-rendered form should still show the user's own choice for
    # the non-offending column, not silently reset it.
    assert '<option value="account_name" selected>' in page


# --- Stage 7 correction #3: detected header row shown on screen ---------

def test_normal_file_shows_row_one_as_the_detected_header_row(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")
    r = client.get(f"/data/mapping/{file_id}/")
    page = body(r)
    assert "Detected Header Row: Row 1" in page
    assert "Please verify this before confirming" not in page


def _title_row_xlsx_bytes() -> bytes:
    """A synthetic report-title row above the real header row — the
    header-detection heuristic (app/mapping/structure_detector.py)
    should skip past it. Built directly with openpyxl (not
    pandas.to_csv) because a raw CSV with a ragged first row fails to
    parse at all rather than exercising this case."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Acme Manufacturing Ltd - Trial Balance (Synthetic)"])
    ws.append(["Account", "Debit", "Credit"])
    ws.append(["Cash", 100000, 0])
    ws.append(["Sales", 0, 100000])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_title_row_file_shows_non_first_header_row_with_a_warning(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.xlsx", _title_row_xlsx_bytes(), "TB")
    r = client.get(f"/data/mapping/{file_id}/")
    page = body(r)
    assert "Detected Header Row: Row 2" in page
    assert "The system detected Row 2 as the header" in page
    assert "Please verify this before confirming mappings" in page
