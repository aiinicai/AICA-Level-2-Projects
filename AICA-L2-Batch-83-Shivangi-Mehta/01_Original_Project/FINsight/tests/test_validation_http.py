"""
Stage 7 — full HTTP round trip for the Data Quality screen: the
"not mapped yet" guard, running a validation, and persisting the
VALIDATED/ERROR result onto `uploaded_files.upload_status`.

Uses only synthetic, fabricated CSV content — never real client or
financial data.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


def _upload_file(client, filename, file_bytes, file_type):
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(file_bytes), filename), "file_type": file_type},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    from app.services import upload_service
    return upload_service.list_uploads(engagement_id)[0].file_id


def _confirm_mapping(client, file_id, field_by_position: dict):
    data = {f"target_field__{pos}": field for pos, field in field_by_position.items()}
    r = client.post(f"/data/mapping/{file_id}/", data=data, follow_redirects=False)
    assert r.status_code == 302


TB_ROWS = [
    {"Account": "Cash", "Debit": 100000, "Credit": 0},
    {"Account": "Sales", "Debit": 0, "Credit": 100000},
]


def test_data_quality_before_mapping_shows_a_map_first_message(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")

    r = client.get(f"/data/quality/{file_id}/")
    assert r.status_code == 200
    page = body(r)
    assert "confirm mappings" in page.lower() or "confirmed column mappings" in page.lower()


def test_data_quality_after_full_mapping_shows_validated(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")
    _confirm_mapping(client, file_id, {0: "account_name", 1: "debit_amount", 2: "credit_amount"})

    r = client.get(f"/data/quality/{file_id}/")
    assert r.status_code == 200
    page = body(r)
    assert "VALIDATED" in page
    assert "100.0%" in page


def test_saving_data_quality_result_persists_status_to_validated(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")
    _confirm_mapping(client, file_id, {0: "account_name", 1: "debit_amount", 2: "credit_amount"})

    r = client.post(f"/data/quality/{file_id}/", follow_redirects=False)
    assert r.status_code == 200
    assert "Saved" in body(r)

    from app.services import upload_service
    assert upload_service.get_upload(file_id).upload_status == "VALIDATED"


def test_missing_essential_field_produces_error_status_end_to_end(client):
    _create_and_select_engagement(client)
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(TB_ROWS), "TB")
    # Only map "Credit" to something irrelevant — account_name and any
    # amount field are left unmapped.
    _confirm_mapping(client, file_id, {2: "reference_number"})

    r = client.post(f"/data/quality/{file_id}/", follow_redirects=False)
    assert r.status_code == 200
    page = body(r)
    assert "ERROR" in page

    from app.services import upload_service
    assert upload_service.get_upload(file_id).upload_status == "ERROR"


def test_bad_data_still_validates_but_lowers_the_quality_score(client):
    _create_and_select_engagement(client)
    rows = [{"Account": "Cash", "Debit": "not a number", "Credit": 0}]
    file_id = _upload_file(client, "trial_balance.csv", _csv_bytes(rows), "TB")
    _confirm_mapping(client, file_id, {0: "account_name", 1: "debit_amount", 2: "credit_amount"})

    r = client.get(f"/data/quality/{file_id}/")
    page = body(r)
    assert "VALIDATED" in page
    assert "100.0%" not in page
