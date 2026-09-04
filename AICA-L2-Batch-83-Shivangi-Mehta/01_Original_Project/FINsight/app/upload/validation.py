"""
Form validation for the Data Upload form (Stage 6). Pure functions, no
Flask/SQLAlchemy dependency — same testable-in-isolation pattern as
`app/engagement/validation.py`.

`FILE_TYPES` mirrors the comment already on the approved
`app/models/uploads.py`'s `UploadedFile.file_type` field exactly —
nothing here invents a new allowed value.
"""
from __future__ import annotations

FILE_TYPES = (
    "TB", "GL", "JE", "SALES", "PURCHASE", "BANK", "AR", "AP",
    "FIXED_ASSETS", "GST", "TDS", "PRIOR_YEAR", "OTHER",
)

FILE_TYPE_LABELS = {
    "TB": "Trial Balance",
    "GL": "General Ledger",
    "JE": "Journal Entries",
    "SALES": "Sales Register",
    "PURCHASE": "Purchase Register",
    "BANK": "Bank Statement",
    "AR": "Accounts Receivable",
    "AP": "Accounts Payable",
    "FIXED_ASSETS": "Fixed Assets Register",
    "GST": "GST Data",
    "TDS": "TDS Data",
    "PRIOR_YEAR": "Prior Year Data",
    "OTHER": "Other",
}

# Stage 6 scope note (flagged in the Stage 6 delivery, not a schema
# change): only .csv and .xlsx are accepted. Legacy binary .xls is
# deliberately NOT supported — reading it would need the `xlrd` package,
# which is not on the approved dependency list (Blueprint Section L only
# names pandas + openpyxl). Adding it would be a new dependency, which
# Stage 5 round 2 already established requires being flagged and
# approved first, not added quietly to make a format work.
ALLOWED_EXTENSIONS = (".csv", ".xlsx")


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def validate_upload_form(filename: str, file_type: str, size_bytes: int) -> dict[str, str]:
    """Validate the Data Upload form. Returns an errors dict keyed by
    field name; empty dict means valid.

    Takes plain primitives (filename, file_type, size_bytes) rather than
    a werkzeug FileStorage object, so this stays directly unit-testable
    without Flask — the route extracts these from `request.files`/
    `request.form` and passes them in.
    """
    errors: dict[str, str] = {}

    filename = (filename or "").strip()
    if not filename:
        errors["file"] = "Choose a file to upload."
    elif _extension(filename) not in ALLOWED_EXTENSIONS:
        allowed = " or ".join(ALLOWED_EXTENSIONS)
        errors["file"] = f"Unsupported file type — only {allowed} files are accepted."
    elif size_bytes <= 0:
        errors["file"] = "This file appears to be empty."

    if file_type not in FILE_TYPES:
        errors["file_type"] = "Select the type of data this file contains."

    return errors
