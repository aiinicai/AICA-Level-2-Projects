"""
Stage 6 — full HTTP round trip through the real Flask app for the Data
Upload screen: uploading a file for the current engagement, duplicate
detection, unreadable-file rejection, and the "no engagement selected"
guard.

Uses only synthetic, fabricated CSV/XLSX content (fake trial balance
rows) — never real client or financial data, per the standing
instruction. Nothing in this file (or the route/service it exercises)
makes a network call of any kind — row-counting is done locally via
pandas/openpyxl against bytes already in the request body.

NOTE ON THIS SANDBOX: ran for real under `pytest`, through a genuinely
real Flask 3.1.3, with the SQLAlchemy ORM layer underneath
`upload_service.py` simulated by a scoped shim against a real SQLite
file — see the Stage 5 delivery notes for the sandbox's dependency
situation (SQLAlchemy/Alembic remain uninstallable; pandas/openpyxl are
genuinely real and unmodified here).

    pip install -r requirements.txt
    pytest tests/test_upload_http.py -v
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
    """Isolates DATA_INPUT_DIR to a pytest tmp_path per test — this is
    the first stage whose routes actually write files, and plain
    TestConfig (used unmodified by test_app_factory.py/test_dashboard.py,
    where nothing writes to disk) would otherwise have every test in
    this file write real files into the real repo's data/input/
    directory. Caught during Stage 6 delivery verification: an early
    version of this fixture used bare TestConfig and left stray files
    behind in the repo after every test run."""
    class IsolatedUploadTestConfig(TestConfig):
        DATA_INPUT_DIR = tmp_path / "data_input"

    app = create_app(IsolatedUploadTestConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app.test_client()


def body(resp):
    return resp.get_data(as_text=True)


SYNTHETIC_TB_ROWS = [
    {"account": "Cash", "debit": 100000, "credit": 0},
    {"account": "Sales", "debit": 0, "credit": 100000},
]


def _csv_bytes(rows=SYNTHETIC_TB_ROWS) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


def _xlsx_bytes(rows=SYNTHETIC_TB_ROWS) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def _create_and_select_engagement(client, entity_name="Acme Manufacturing Ltd"):
    r = client.post(
        "/engagement/new",
        data={"entity_name": entity_name, "financial_year": "2025-26"},
        follow_redirects=False,
    )
    assert r.status_code == 302  # engagement.new auto-selects it as current (Stage 5)


def _upload(client, filename, file_bytes, file_type):
    return client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(file_bytes), filename), "file_type": file_type},
        content_type="multipart/form-data",
        follow_redirects=False,
    )


# --- No engagement selected --------------------------------------------

def test_upload_page_with_no_engagement_shows_empty_state_not_the_form(client):
    r = client.get("/data/upload/")
    assert r.status_code == 200
    page = body(r)
    assert "No current engagement selected" in page
    assert 'name="file"' not in page  # the upload form itself is not shown


# --- Successful upload ---------------------------------------------------

def test_csv_upload_succeeds_and_appears_in_the_list(client):
    _create_and_select_engagement(client)
    r = _upload(client, "trial_balance.csv", _csv_bytes(), "TB")
    assert r.status_code == 302  # redirect back to the upload page on success

    page = body(client.get("/data/upload/"))
    assert "trial_balance.csv" in page
    assert "Trial Balance" in page  # FILE_TYPE_LABELS["TB"]
    assert "UPLOADED" in page
    assert ">2<" in page  # row_count, 2 synthetic data rows


def test_xlsx_upload_succeeds(client):
    _create_and_select_engagement(client)
    r = _upload(client, "general_ledger.xlsx", _xlsx_bytes(), "GL")
    assert r.status_code == 302

    page = body(client.get("/data/upload/"))
    assert "general_ledger.xlsx" in page
    assert "General Ledger" in page


# --- Validation ------------------------------------------------------------

def test_upload_without_a_file_type_shows_a_field_error(client):
    _create_and_select_engagement(client)
    r = _upload(client, "trial_balance.csv", _csv_bytes(), "")
    assert r.status_code == 200  # re-renders the form, no redirect
    assert "Select the type of data" in body(r)


def test_upload_with_unsupported_extension_rejected(client):
    _create_and_select_engagement(client)
    r = _upload(client, "trial_balance.pdf", b"%PDF-1.4 not a real pdf", "TB")
    assert r.status_code == 200
    assert "only .csv or .xlsx files are accepted" in body(r)


def test_upload_of_unreadable_xlsx_rejected_with_a_friendly_message(client):
    _create_and_select_engagement(client)
    r = _upload(client, "corrupt.xlsx", b"not actually an xlsx file" * 20, "TB")
    assert r.status_code == 200
    assert "Could not read this file" in body(r)
    # Nothing should have been persisted for the rejected upload.
    assert "corrupt.xlsx" not in body(client.get("/data/upload/"))


# --- Duplicate detection ----------------------------------------------------

def test_duplicate_upload_rejected_with_a_clear_message(client):
    _create_and_select_engagement(client)
    file_bytes = _csv_bytes()
    _upload(client, "trial_balance.csv", file_bytes, "TB")

    r = _upload(client, "trial_balance_again.csv", file_bytes, "TB")
    assert r.status_code == 200  # rejected, not redirected
    assert "already uploaded" in body(r)

    # Still only the one, original upload in the list.
    page = body(client.get("/data/upload/"))
    assert page.count("trial_balance.csv") >= 1
    assert "trial_balance_again.csv" not in page


# --- Oversized upload (MAX_CONTENT_LENGTH / config.py's MAX_UPLOAD_SIZE_BYTES)

def test_oversized_upload_rejected_with_413_and_a_friendly_message(tmp_path):
    """A dedicated client (not the shared `client` fixture) so this test
    can override MAX_UPLOAD_SIZE_BYTES without affecting every other
    test in this file. Uses a 1 MB limit (not a tiny byte count) so the
    friendly message's rounding is checked at a realistic scale — a
    genuinely tiny limit like 200 bytes would legitimately still show
    "0.0 MB" to one decimal place, which is correct there, not a bug."""
    class OneMbLimitConfig(TestConfig):
        MAX_UPLOAD_SIZE_BYTES = 1024 * 1024
        DATA_INPUT_DIR = tmp_path / "data_input"

    app = create_app(OneMbLimitConfig)
    from app import extensions
    from app.models import Base
    Base.metadata.create_all(extensions.engine)
    tiny_client = app.test_client()

    _create_and_select_engagement(tiny_client)
    r = _upload(tiny_client, "trial_balance.csv", b"x" * (2 * 1024 * 1024), "TB")
    assert r.status_code == 413
    assert r.get_json()["error"] == "file_too_large"
    # Regression: this used to integer-divide MAX_CONTENT_LENGTH by
    # 1024*1024, which is fine at a clean value like this but silently
    # rounded any non-multiple-of-1MB limit down — fixed to one decimal.
    assert "1.0 MB" in r.get_json()["message"]


def test_same_file_content_allowed_for_a_different_engagement(client):
    file_bytes = _csv_bytes()
    _create_and_select_engagement(client, "Acme Manufacturing Ltd")
    _upload(client, "trial_balance.csv", file_bytes, "TB")

    _create_and_select_engagement(client, "Beta Traders LLP")  # switches current engagement
    r = _upload(client, "trial_balance.csv", file_bytes, "TB")
    assert r.status_code == 302  # succeeds — different engagement, not a duplicate

    page = body(client.get("/data/upload/"))
    assert "trial_balance.csv" in page


# --- Multi-file upload convenience (post-Stage-17 fix) ----------------------
#
# The Upload screen's file picker now accepts several files in one
# submission, each with its own `file_type__<index>` field (built by
# frontend/static/js/upload.js in the real browser; simulated here by
# posting the same shape of multipart form directly, exactly how a
# real submission from the new picker looks on the wire). Every file
# still goes through the exact same validate_upload_form() /
# upload_service.save_uploaded_file() calls as a single-file upload —
# these tests are about the batch behavior (partial failure, per-file
# results, engagement association), not new validation/business logic.


def _upload_multi(client, files):
    """files: list of (filename, file_bytes, file_type) tuples, all
    submitted as one multipart POST — the same request shape the new
    multi-file picker produces (a repeated `file` field plus one
    `file_type__<index>` field per file, index matching submission
    order)."""
    data = {"file": [(io.BytesIO(fb), fn) for fn, fb, _ft in files]}
    for index, (_fn, _fb, file_type) in enumerate(files):
        data[f"file_type__{index}"] = file_type
    return client.post(
        "/data/upload/",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )


def test_multi_file_upload_all_succeed(client):
    _create_and_select_engagement(client)
    r = _upload_multi(client, [
        ("trial_balance.csv", _csv_bytes(), "TB"),
        ("general_ledger.csv", _csv_bytes([{"account": "Bank", "debit": 5000, "credit": 0}]), "GL"),
        ("bank_statement.csv", _csv_bytes([{"account": "Bank", "debit": 0, "credit": 5000}]), "BANK"),
    ])
    assert r.status_code == 200  # multi-file result page, not a redirect
    page = body(r)
    assert page.count("Uploaded") >= 3  # one "Uploaded" badge per successful file
    assert "trial_balance.csv" in page
    assert "general_ledger.csv" in page
    assert "bank_statement.csv" in page

    listing = body(client.get("/data/upload/"))
    assert "trial_balance.csv" in listing
    assert "general_ledger.csv" in listing
    assert "bank_statement.csv" in listing


def test_multi_file_upload_one_succeeds_one_fails_no_rollback(client):
    _create_and_select_engagement(client)
    r = _upload_multi(client, [
        ("trial_balance.csv", _csv_bytes(), "TB"),
        ("not_a_real_file.pdf", b"%PDF-1.4 not a real pdf", "TB"),
    ])
    assert r.status_code == 200
    page = body(r)
    assert "Uploaded" in page
    assert "Failed" in page
    assert "only .csv or .xlsx files are accepted" in page

    # The successful file was kept — nothing rolled back because its
    # sibling in the same batch failed.
    listing = body(client.get("/data/upload/"))
    assert "trial_balance.csv" in listing
    assert "UPLOADED" in listing
    assert "not_a_real_file.pdf" not in listing


def test_multi_file_upload_duplicate_within_same_batch(client):
    _create_and_select_engagement(client)
    file_bytes = _csv_bytes()
    r = _upload_multi(client, [
        ("trial_balance.csv", file_bytes, "TB"),
        ("trial_balance_copy.csv", file_bytes, "TB"),  # identical content, same batch
    ])
    assert r.status_code == 200
    page = body(r)
    assert "Uploaded" in page
    assert "Failed" in page
    assert "already uploaded" in page

    listing = body(client.get("/data/upload/"))
    assert "trial_balance.csv" in listing
    assert "trial_balance_copy.csv" not in listing


def test_multi_file_upload_assigns_correct_type_to_each_file(client):
    _create_and_select_engagement(client)
    _upload_multi(client, [
        ("sales.csv", _csv_bytes([{"account": "Sales", "debit": 0, "credit": 1000}]), "SALES"),
        ("purchases.csv", _csv_bytes([{"account": "Purchases", "debit": 1000, "credit": 0}]), "PURCHASE"),
    ])

    listing = body(client.get("/data/upload/"))
    # Each file's row shows the type label that was actually assigned to
    # it, not the other file's type or a default.
    sales_pos = listing.find("sales.csv")
    purchase_pos = listing.find("purchases.csv")
    assert sales_pos != -1 and purchase_pos != -1
    assert "Sales Register" in listing
    assert "Purchase Register" in listing


def test_multi_file_upload_all_linked_to_current_engagement(client):
    _create_and_select_engagement(client, "Acme Manufacturing Ltd")
    _upload_multi(client, [
        ("tb.csv", _csv_bytes(), "TB"),
        ("gl.csv", _csv_bytes([{"account": "Bank", "debit": 1, "credit": 0}]), "GL"),
    ])

    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]

    from app.services import upload_service
    uploads = upload_service.list_uploads(engagement_id)
    assert len(uploads) == 2
    assert {u.engagement_id for u in uploads} == {engagement_id}
    assert {u.original_filename for u in uploads} == {"tb.csv", "gl.csv"}


def test_multi_file_upload_review_dataset_aggregates_all_validated_files(client):
    """End-to-end proof that dataset_service.load_engagement_dataset()
    still aggregates every validated file exactly as before — nothing
    about this convenience change touches mapping, validation, or the
    dataset the review engines read."""
    _create_and_select_engagement(client)
    r = _upload_multi(client, [
        ("tb.csv", _csv_bytes(), "TB"),
        ("gl.csv", _csv_bytes([{"date": "2025-04-01", "account": "Bank", "debit": 1, "credit": 0}]), "GL"),
    ])
    assert r.status_code == 200

    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]

    from app.services import mapping_service, upload_service, validation_service, dataset_service

    uploads = {u.original_filename: u for u in upload_service.list_uploads(engagement_id)}
    assert set(uploads) == {"tb.csv", "gl.csv"}

    # Map + validate each file independently, exactly as a user would —
    # this is unmodified Stage 7/8 behavior, not something this change
    # touches. (GL's own essential-field rules require transaction_date
    # in addition to account_name/an amount field — unchanged Stage 7
    # logic, just needing a complete-enough mapping here to reach
    # VALIDATED rather than ERROR.)
    mapping_service.confirm_mappings(uploads["tb.csv"].file_id, [
        {"source_column": "account", "target_field": "account_name", "confidence_score": None},
        {"source_column": "debit", "target_field": "debit_amount", "confidence_score": None},
        {"source_column": "credit", "target_field": "credit_amount", "confidence_score": None},
    ])
    mapping_service.mark_file_status(uploads["tb.csv"].file_id, "MAPPED")
    result = validation_service.evaluate_file(upload_service.get_upload(uploads["tb.csv"].file_id))
    validation_service.save_validation_result(upload_service.get_upload(uploads["tb.csv"].file_id), result)

    mapping_service.confirm_mappings(uploads["gl.csv"].file_id, [
        {"source_column": "date", "target_field": "transaction_date", "confidence_score": None},
        {"source_column": "account", "target_field": "account_name", "confidence_score": None},
        {"source_column": "debit", "target_field": "debit_amount", "confidence_score": None},
        {"source_column": "credit", "target_field": "credit_amount", "confidence_score": None},
    ])
    mapping_service.mark_file_status(uploads["gl.csv"].file_id, "MAPPED")
    result2 = validation_service.evaluate_file(upload_service.get_upload(uploads["gl.csv"].file_id))
    validation_service.save_validation_result(upload_service.get_upload(uploads["gl.csv"].file_id), result2)

    dataset = dataset_service.load_engagement_dataset(engagement_id)
    assert "TB" in dataset and len(dataset["TB"]) > 0
    assert "GL" in dataset and len(dataset["GL"]) > 0


def test_multi_file_upload_single_file_via_new_picker_still_redirects(client):
    """A single file submitted through the NEW multi-file field shape
    (file_type__0 present) behaves the same as the classic single-file
    path on a clean success: redirect, no results table needed."""
    _create_and_select_engagement(client)
    r = _upload_multi(client, [("trial_balance.csv", _csv_bytes(), "TB")])
    assert r.status_code == 302

    listing = body(client.get("/data/upload/"))
    assert "trial_balance.csv" in listing


def test_single_file_classic_upload_path_still_unchanged(client):
    """Belt-and-braces regression check alongside the pre-existing
    single-file tests above: the classic unindexed `file`/`file_type`
    submission shape (no `file_type__<n>` fields at all) still takes
    the original Stage 6 code path and behaves identically."""
    _create_and_select_engagement(client)
    r = _upload(client, "trial_balance.csv", _csv_bytes(), "TB")
    assert r.status_code == 302

    listing = body(client.get("/data/upload/"))
    assert "trial_balance.csv" in listing
    assert "UPLOADED" in listing
