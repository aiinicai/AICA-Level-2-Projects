"""
Stage 6 — app/upload/validation.py (form validation for the Data
Upload form).

Pure functions, no Flask/SQLAlchemy dependency for the logic itself
(though importing anything under `app.*` still runs `app/__init__.py`
first). Ran for real under `pytest` in the delivery sandbox — see the
Stage 5/6 delivery notes for the sandbox's real-Flask + shimmed-
SQLAlchemy setup. Also runs unmodified once real dependencies are
installed per requirements.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.upload.validation import ALLOWED_EXTENSIONS, FILE_TYPES, validate_upload_form


def test_allowed_extensions_are_csv_and_xlsx_only():
    # Legacy .xls deliberately excluded — see validation.py's own
    # comment: supporting it would need the unapproved `xlrd` package.
    assert ALLOWED_EXTENSIONS == (".csv", ".xlsx")


def test_valid_csv_upload_has_no_errors():
    errors = validate_upload_form("trial_balance.csv", "TB", size_bytes=1024)
    assert errors == {}


def test_valid_xlsx_upload_has_no_errors():
    errors = validate_upload_form("general_ledger.xlsx", "GL", size_bytes=2048)
    assert errors == {}


def test_missing_filename_rejected():
    errors = validate_upload_form("", "TB", size_bytes=0)
    assert "file" in errors


def test_unsupported_extension_rejected():
    for filename in ("data.xls", "data.pdf", "data.txt", "data"):
        errors = validate_upload_form(filename, "TB", size_bytes=1024)
        assert "file" in errors, f"expected {filename!r} to be rejected"


def test_empty_file_rejected():
    errors = validate_upload_form("trial_balance.csv", "TB", size_bytes=0)
    assert "file" in errors


def test_invalid_file_type_rejected():
    errors = validate_upload_form("trial_balance.csv", "NOT_A_TYPE", size_bytes=1024)
    assert "file_type" in errors


def test_missing_file_type_rejected():
    errors = validate_upload_form("trial_balance.csv", "", size_bytes=1024)
    assert "file_type" in errors


def test_every_declared_file_type_is_individually_valid():
    for file_type in FILE_TYPES:
        errors = validate_upload_form("data.csv", file_type, size_bytes=1024)
        assert "file_type" not in errors, f"{file_type!r} should be a valid file_type"


def test_extension_check_is_case_insensitive():
    errors = validate_upload_form("TRIAL_BALANCE.CSV", "TB", size_bytes=1024)
    assert errors == {}
