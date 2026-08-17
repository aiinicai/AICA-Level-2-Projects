"""Strict, offline ingestion for purchase and payment ledgers.

This module deliberately stops at the boundary of :mod:`clock45.engine`: it
turns user-owned files or pasted rows into ``PurchaseLine`` and
``PaymentLine`` objects, but makes no tax or legal judgement.

Every public import function returns an :class:`ImportResult`.  A malformed
row or a control-total mismatch raises :class:`IngestError`; callers must not
continue to an assessment after that exception.
"""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from .engine import PaymentLine, PurchaseLine
from .normalise import normalise_name


PURCHASE_FIELDS = (
    "invoice_number", "invoice_date", "vendor_name", "vendor_pan_or_gstin",
    "vendor_pan", "vendor_gstin", "amount", "udyam_no", "enterprise_class",
    "classification_year", "nic_code", "major_activity", "registration_status",
    "udyam_verification_source", "grn_date", "agreement_credit_days",
    "agreed_due_date", "actual_payment_date", "outstanding_amount",
    "ledger_category", "vendor_contact", "remarks",
)
PAYMENT_FIELDS = ("invoice_number", "payment_date", "amount")
OPTIONAL_PURCHASE_FIELDS = set(PURCHASE_FIELDS) - {
    "invoice_number", "invoice_date", "vendor_name", "amount",
}

PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")
UDYAM_RE = re.compile(r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$")

_HEADER_ALIASES = {
    "invoice_number": (
        "invoice number", "invoice no", "invoice #", "bill number",
        "bill no", "voucher number", "voucher no", "reference",
    ),
    "invoice_date": ("invoice date", "bill date", "voucher date", "date"),
    "payment_date": ("payment date", "paid date", "voucher date", "date"),
    "vendor_name": (
        "vendor name", "supplier name", "party name", "party ledger name",
        "ledger name", "vendor", "supplier", "party",
    ),
    "vendor_pan_or_gstin": (
        "vendor pan or gstin", "pan or gstin", "vendor gstin", "supplier gstin",
        "gstin", "gst number", "gst no", "vendor pan", "supplier pan", "pan",
    ),
    "vendor_pan": ("vendor pan", "supplier pan", "party pan", "pan"),
    "vendor_gstin": (
        "vendor gstin", "supplier gstin", "party gstin", "gstin",
        "gst number", "gst no",
    ),
    "amount": (
        "invoice amount", "payment amount", "voucher amount", "gross amount",
        "taxable amount", "amount", "value",
    ),
    "grn_date": (
        "grn date", "goods receipt date", "goods received date", "receipt date",
    ),
    "agreement_credit_days": (
        "agreement credit days", "agreed credit days", "credit days",
        "payment terms days", "payment terms", "credit period",
    ),
    "udyam_no": (
        "udyam registration number", "udyam registration no", "udyam number",
        "udyam no", "udyam",
    ),
    "enterprise_class": (
        "enterprise classification", "enterprise class", "enterprise type",
        "msme classification", "msme class", "msme type", "type of enterprise",
    ),
    "classification_year": (
        "udyam classification year", "classification year", "enterprise year",
    ),
    "nic_code": ("nic code", "nic", "national industry classification code"),
    "major_activity": (
        "major activity", "udyam activity", "business activity", "activity",
    ),
    "registration_status": (
        "udyam registration status", "msme registration status", "registration status",
    ),
    "udyam_verification_source": (
        "udyam verification source", "evidence source", "verification source",
    ),
    "agreed_due_date": (
        "agreed payment due date", "agreed due date", "payment due date", "due date",
    ),
    "actual_payment_date": (
        "actual payment date", "settlement date", "date paid", "paid date",
    ),
    "outstanding_amount": (
        "outstanding amount", "amount outstanding", "balance outstanding", "closing balance",
    ),
    "ledger_category": (
        "ledger expense category", "expense category", "ledger category", "expense ledger",
    ),
    "vendor_contact": (
        "vendor contact", "supplier contact", "contact person", "contact",
    ),
    "remarks": ("remarks", "remark", "comments", "notes"),
}

_TOTAL_MARKERS = {
    "total", "grand total", "control total", "ledger total", "declared total",
}
_MAPPING_FILENAME = "clock45_column_mappings.json"
_DATE_FORMATS = (
    "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
    "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %b %y",
    "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d",
)


@dataclass(frozen=True)
class RowProblem:
    row_number: int
    reasons: tuple[str, ...]
    values: dict[str, str]


@dataclass(frozen=True)
class ConfirmationFlag:
    row_number: int
    field: str
    value: str
    reason: str


@dataclass(frozen=True)
class ControlTotals:
    lines_read: int
    total_value_read: Decimal
    total_value_accounted_for: Decimal
    ties: bool
    declared_total: Optional[Decimal] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "lines_read": self.lines_read,
            "total_value_read": self.total_value_read,
            "total_value_accounted_for": self.total_value_accounted_for,
            "declared_total": self.declared_total,
            "ties": self.ties,
        }


@dataclass(frozen=True)
class ImportResult:
    purchases: list[PurchaseLine]
    payments: list[PaymentLine]
    control_totals: ControlTotals
    confirmations: list[ConfirmationFlag] = field(default_factory=list)
    source: str = ""
    vendor_data: dict[str, "VendorImportData"] = field(default_factory=dict)
    invoice_supplements: dict[str, "InvoiceSupplement"] = field(default_factory=dict)
    unmapped_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class VendorImportData:
    vendor_id: str
    vendor_name: str
    pan: str = ""
    gstin: str = ""
    udyam_no: str = ""
    enterprise_class: str = ""
    classification_year: str = ""
    nic_code: str = ""
    major_activity: str = ""
    registration_status: str = ""
    verification_source: str = ""
    contact: str = ""


@dataclass(frozen=True)
class InvoiceSupplement:
    invoice_id: str
    agreed_due_date: Optional[date] = None
    actual_payment_date: Optional[date] = None
    outstanding_amount: Optional[Decimal] = None
    ledger_category: str = ""
    remarks: str = ""


@dataclass(frozen=True)
class ColumnDetection:
    columns: tuple[str, ...]
    suggested_mapping: dict[str, str]
    confidence: dict[str, str] = field(default_factory=dict)


class IngestError(ValueError):
    """Fatal import error carrying rows and control totals for the UI."""

    def __init__(
        self,
        message: str,
        *,
        row_problems: Optional[list[RowProblem]] = None,
        control_totals: Optional[ControlTotals] = None,
    ) -> None:
        super().__init__(message)
        self.row_problems = row_problems or []
        self.control_totals = control_totals


def _blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        # Handles pandas NA/NaN without importing pandas here.
        if value != value:
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def parse_indian_date(value: Any, *, field_name: str = "date") -> date:
    """Parse common Indian ledger dates, Excel dates, or date objects."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        serial = float(value)
        if 1 <= serial <= 100000:
            return (datetime(1899, 12, 30) + timedelta(days=serial)).date()
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"{field_name} {text!r} is not a recognised date "
        "(use DD-MM-YYYY, DD/MM/YY or DD-Mon-YYYY)"
    )


def parse_indian_amount(value: Any) -> Decimal:
    """Parse ledger money including Indian commas, symbols and Dr/Cr suffixes.

    ``Dr`` and ``Cr`` describe accounting presentation. Engine lines carry a
    positive invoice/payment magnitude, so the returned value is absolute.
    Parentheses and leading minus signs are accepted for the same reason.
    """
    if isinstance(value, bool) or _blank(value):
        raise ValueError("amount is blank")
    text = str(value).strip()
    text = re.sub(r"(?i)\s*(dr|cr)\.?\s*$", "", text).strip()
    negative_parentheses = text.startswith("(") and text.endswith(")")
    if negative_parentheses:
        text = text[1:-1].strip()
    text = re.sub(r"(?i)^(?:inr|rs\.?|₹)\s*", "", text).strip()
    text = text.replace(",", "").replace(" ", "")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text):
        raise ValueError(f"amount {value!r} is not a valid number")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"amount {value!r} is not a valid number") from exc
    if negative_parentheses:
        amount = -amount
    return abs(amount).quantize(Decimal("0.01"))


def _normalise_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower()).strip()


def suggest_mapping_details(
    columns: Iterable[Any], record_type: str = "purchase"
) -> tuple[dict[str, str], dict[str, str]]:
    """Return non-conflicting suggestions and a review-friendly confidence label."""
    from difflib import SequenceMatcher

    original = [str(c) for c in columns]
    normalised = {_normalise_header(c): c for c in original}
    wanted = PURCHASE_FIELDS if record_type == "purchase" else PAYMENT_FIELDS
    suggestions: dict[str, str] = {}
    confidence: dict[str, str] = {}
    used: set[str] = set()
    for field_name in wanted:
        aliases = _HEADER_ALIASES[field_name]
        exact = next(
            (normalised[alias] for alias in aliases
             if alias in normalised and normalised[alias] not in used),
            None,
        )
        if exact:
            suggestions[field_name] = exact
            confidence[field_name] = "HIGH"
            used.add(exact)
            continue
        candidates = []
        for normalised_column, original_column in normalised.items():
            if original_column in used:
                continue
            score = max(SequenceMatcher(None, normalised_column, alias).ratio() for alias in aliases)
            candidates.append((score, original_column))
        if candidates:
            score, candidate = max(candidates)
            if score >= 0.86:
                suggestions[field_name] = candidate
                confidence[field_name] = "MEDIUM"
                used.add(candidate)
    return suggestions, confidence


def suggest_mapping(columns: Iterable[Any], record_type: str = "purchase") -> dict[str, str]:
    """Suggest a mapping; the UI must still present it for user confirmation."""
    return suggest_mapping_details(columns, record_type)[0]


def _read_table(path: Path, sheet_name: Any = 0):
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - deployment guard
        raise IngestError("pandas is required to import Excel and CSV files") from exc
    suffix = path.suffix.lower()
    try:
        if suffix in {".xlsx", ".xlsm"}:
            return pd.read_excel(path, sheet_name=sheet_name, dtype=object, keep_default_na=False)
        if suffix == ".csv":
            return pd.read_csv(path, dtype=object, keep_default_na=False, encoding="utf-8-sig")
    except Exception as exc:
        raise IngestError(f"Could not read {path.name}: {exc}") from exc
    raise IngestError("Only .xlsx, .xlsm and .csv files are supported")


def detect_columns(path: str | Path, *, record_type: str = "purchase", sheet_name: Any = 0) -> ColumnDetection:
    table = _read_table(Path(path), sheet_name)
    columns = tuple(str(c) for c in table.columns)
    mapping, confidence = suggest_mapping_details(columns, record_type)
    return ColumnDetection(columns, mapping, confidence)


def _validate_mapping(mapping: Mapping[str, str], columns: Iterable[str], record_type: str) -> None:
    wanted = PURCHASE_FIELDS if record_type == "purchase" else PAYMENT_FIELDS
    optional = OPTIONAL_PURCHASE_FIELDS if record_type == "purchase" else set()
    missing = [field for field in wanted if field not in optional and not mapping.get(field)]
    if missing:
        raise IngestError("Column mapping is incomplete: " + ", ".join(missing))
    known = {str(c) for c in columns}
    absent = [f"{field} -> {column}" for field, column in mapping.items()
              if field in wanted and column and column not in known]
    if absent:
        raise IngestError("Mapped columns were not found: " + ", ".join(absent))
    selected = [column for field, column in mapping.items() if field in wanted and column]
    duplicates = sorted({column for column in selected if selected.count(column) > 1})
    if duplicates:
        raise IngestError(
            "One ledger column cannot be mapped to two fields: " + ", ".join(duplicates)
        )


def save_client_mapping(
    folder: str | Path,
    client_id: str,
    mapping: Mapping[str, str],
    *,
    record_type: str = "purchase",
) -> Path:
    """Remember a mapping only inside the folder explicitly chosen by the user."""
    base = Path(folder)
    if not base.exists() or not base.is_dir():
        raise IngestError(f"Chosen mapping folder does not exist: {base}")
    target = base / _MAPPING_FILENAME
    payload: dict[str, Any] = {}
    if target.exists():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IngestError(f"Could not read saved mappings: {exc}") from exc
    payload.setdefault(client_id, {})[record_type] = dict(mapping)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(target)
    return target


def load_client_mapping(
    folder: str | Path,
    client_id: str,
    *,
    record_type: str = "purchase",
) -> Optional[dict[str, str]]:
    target = Path(folder) / _MAPPING_FILENAME
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        found = payload.get(client_id, {}).get(record_type)
        return dict(found) if found else None
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise IngestError(f"Could not read saved mappings: {exc}") from exc


def _row_values(row: Mapping[str, Any]) -> dict[str, str]:
    return {str(k): "" if _blank(v) else str(v) for k, v in row.items()}


def _is_total_row(row: Mapping[str, Any], mapping: Mapping[str, str]) -> bool:
    candidates = [mapping.get("invoice_number"), mapping.get("vendor_name")]
    return any(
        column and _normalise_header(row.get(column, "")) in _TOTAL_MARKERS
        for column in candidates
    )


def _parse_rows(
    rows: Iterable[tuple[int, Mapping[str, Any]]],
    mapping: Mapping[str, str],
    *,
    record_type: str,
    source: str,
    expected_total: Any = None,
    source_columns: Optional[Iterable[str]] = None,
) -> ImportResult:
    purchases: list[PurchaseLine] = []
    payments: list[PaymentLine] = []
    problems: list[RowProblem] = []
    declared_total = parse_indian_amount(expected_total) if expected_total is not None else None
    detail_rows = 0
    read_total = Decimal("0.00")
    vendor_data: dict[str, VendorImportData] = {}
    invoice_supplements: dict[str, InvoiceSupplement] = {}
    seen_invoices: set[str] = set()
    confirmations: list[ConfirmationFlag] = []

    def raw(row: Mapping[str, Any], field_name: str) -> str:
        column = mapping.get(field_name)
        return "" if not column or _blank(row.get(column)) else str(row.get(column)).strip()

    for row_number, row in rows:
        if all(_blank(value) for value in row.values()):
            continue
        if _is_total_row(row, mapping):
            try:
                row_total = parse_indian_amount(row.get(mapping["amount"]))
                if declared_total is not None and declared_total != row_total:
                    problems.append(RowProblem(
                        row_number,
                        (f"declared total {row_total} conflicts with supplied control total {declared_total}",),
                        _row_values(row),
                    ))
                declared_total = row_total
            except ValueError as exc:
                problems.append(RowProblem(row_number, (str(exc),), _row_values(row)))
            continue

        detail_rows += 1
        reasons: list[str] = []
        amount: Optional[Decimal] = None
        try:
            amount = parse_indian_amount(row.get(mapping["amount"]))
            read_total += amount
        except ValueError as exc:
            reasons.append(str(exc))

        invoice_id = str(row.get(mapping["invoice_number"], "")).strip()
        if not invoice_id:
            reasons.append("invoice number is blank")
        elif record_type == "purchase" and invoice_id.casefold() in seen_invoices:
            reasons.append(f"duplicate invoice number {invoice_id!r} in the same upload")

        if record_type == "purchase":
            vendor_name = str(row.get(mapping["vendor_name"], "")).strip()
            if not vendor_name:
                reasons.append("vendor name is blank")
            combined = raw(row, "vendor_pan_or_gstin").upper().replace(" ", "")
            pan = raw(row, "vendor_pan").upper().replace(" ", "")
            gstin = raw(row, "vendor_gstin").upper().replace(" ", "")
            if combined:
                if PAN_RE.fullmatch(combined):
                    pan = pan or combined
                elif GSTIN_RE.fullmatch(combined):
                    gstin = gstin or combined
                else:
                    reasons.append(
                        f"vendor PAN or GSTIN {combined!r} is malformed; use a 10-character PAN or 15-character GSTIN"
                    )
            if pan and not PAN_RE.fullmatch(pan):
                reasons.append(f"vendor PAN {pan!r} is malformed")
            if gstin and not GSTIN_RE.fullmatch(gstin):
                reasons.append(f"vendor GSTIN {gstin!r} is malformed")
            vendor_id = gstin or pan or ("NAME:" + normalise_name(vendor_name) if vendor_name else "")
            try:
                invoice_date = parse_indian_date(
                    row.get(mapping["invoice_date"]), field_name="invoice date"
                )
            except ValueError as exc:
                reasons.append(str(exc))
                invoice_date = None
            grn_date = None
            grn_column = mapping.get("grn_date")
            if grn_column and not _blank(row.get(grn_column)):
                try:
                    grn_date = parse_indian_date(row.get(grn_column), field_name="GRN date")
                except ValueError as exc:
                    reasons.append(str(exc))
            agreement_days = None
            days_column = mapping.get("agreement_credit_days")
            if days_column and not _blank(row.get(days_column)):
                raw_days = row.get(days_column)
                try:
                    numeric_days = Decimal(str(raw_days).strip())
                    if (numeric_days != numeric_days.to_integral_value()
                            or numeric_days < 0 or numeric_days > 3650):
                        raise ValueError
                    agreement_days = int(numeric_days)
                except (InvalidOperation, ValueError):
                    reasons.append(
                        f"agreement credit days {raw_days!r} must be a whole number from 0 to 3650"
                    )

            udyam_no = raw(row, "udyam_no").upper().replace(" ", "")
            if udyam_no and not UDYAM_RE.fullmatch(udyam_no):
                reasons.append(f"Udyam number {udyam_no!r} is malformed")
            enterprise_class = raw(row, "enterprise_class").upper()
            enterprise_class = re.sub(r"\s+ENTERPRISE$", "", enterprise_class)
            if enterprise_class in {"NOT AVAILABLE", "UNREGISTERED", "N/A", "NA"}:
                enterprise_class = ""
            if enterprise_class and enterprise_class not in {"MICRO", "SMALL", "MEDIUM"}:
                reasons.append(
                    f"enterprise class {enterprise_class!r} must be Micro, Small, Medium or blank"
                )
            classification_year = raw(row, "classification_year")
            if classification_year and not re.fullmatch(r"20\d{2}-\d{2}", classification_year):
                reasons.append(
                    f"classification year {classification_year!r} must look like 2025-26"
                )
            nic_code = re.sub(r"\D", "", raw(row, "nic_code"))
            if nic_code and not 2 <= len(nic_code) <= 5:
                reasons.append("NIC code must contain between 2 and 5 digits")

            agreed_due_date = None
            if raw(row, "agreed_due_date"):
                try:
                    agreed_due_date = parse_indian_date(
                        raw(row, "agreed_due_date"), field_name="agreed payment due date"
                    )
                    if invoice_date and agreed_due_date < invoice_date:
                        reasons.append("agreed payment due date is before the invoice date")
                except ValueError as exc:
                    reasons.append(str(exc))
            actual_payment_date = None
            if raw(row, "actual_payment_date"):
                try:
                    actual_payment_date = parse_indian_date(
                        raw(row, "actual_payment_date"), field_name="actual payment date"
                    )
                    if invoice_date and actual_payment_date < invoice_date:
                        reasons.append("actual payment date is before the invoice date")
                except ValueError as exc:
                    reasons.append(str(exc))
            outstanding_amount = None
            if raw(row, "outstanding_amount"):
                try:
                    outstanding_amount = parse_indian_amount(raw(row, "outstanding_amount"))
                    if amount is not None and outstanding_amount > amount:
                        reasons.append("outstanding amount cannot exceed the invoice amount")
                except ValueError as exc:
                    reasons.append(str(exc).replace("amount", "outstanding amount", 1))
            if amount is not None and actual_payment_date and outstanding_amount == amount:
                reasons.append(
                    "actual payment date is present but outstanding amount equals the full invoice amount"
                )
            candidate_vendor = VendorImportData(
                vendor_id=vendor_id,
                vendor_name=vendor_name,
                pan=pan,
                gstin=gstin,
                udyam_no=udyam_no,
                enterprise_class=enterprise_class,
                classification_year=classification_year,
                nic_code=nic_code,
                major_activity=raw(row, "major_activity"),
                registration_status=raw(row, "registration_status"),
                verification_source=raw(row, "udyam_verification_source"),
                contact=raw(row, "vendor_contact"),
            )
            earlier_vendor = vendor_data.get(vendor_id)
            if earlier_vendor:
                for attribute, label in (
                    ("udyam_no", "Udyam number"),
                    ("enterprise_class", "enterprise class"),
                    ("classification_year", "classification year"),
                    ("nic_code", "NIC code"),
                    ("major_activity", "major activity"),
                ):
                    old = str(getattr(earlier_vendor, attribute) or "").strip()
                    new = str(getattr(candidate_vendor, attribute) or "").strip()
                    if old and new and old.casefold() != new.casefold():
                        reasons.append(
                            f"{label} conflicts with an earlier row for the same vendor: {old!r} versus {new!r}"
                        )
            if not reasons and amount is not None and invoice_date is not None:
                purchases.append(PurchaseLine(
                    invoice_id, vendor_id, vendor_name, invoice_date, amount,
                    grn_date, agreement_days,
                ))
                seen_invoices.add(invoice_id.casefold())
                vendor_data[vendor_id] = candidate_vendor
                invoice_supplements[invoice_id] = InvoiceSupplement(
                    invoice_id=invoice_id,
                    agreed_due_date=agreed_due_date,
                    actual_payment_date=actual_payment_date,
                    outstanding_amount=outstanding_amount,
                    ledger_category=raw(row, "ledger_category"),
                    remarks=raw(row, "remarks"),
                )
                if actual_payment_date:
                    inferred_payment = amount - (outstanding_amount or Decimal("0.00"))
                    if inferred_payment > 0:
                        payments.append(PaymentLine(invoice_id, actual_payment_date, inferred_payment))
                        if outstanding_amount is None:
                            confirmations.append(ConfirmationFlag(
                                row_number=row_number,
                                field="actual_payment_date",
                                value=actual_payment_date.isoformat(),
                                reason=(
                                    "A full settlement was inferred because Actual Payment Date was supplied "
                                    "without Outstanding Amount. Confirm this before relying on the result."
                                ),
                            ))
        else:
            try:
                payment_date = parse_indian_date(
                    row.get(mapping["payment_date"]), field_name="payment date"
                )
            except ValueError as exc:
                reasons.append(str(exc))
                payment_date = None
            if not reasons and amount is not None and payment_date is not None:
                payments.append(PaymentLine(invoice_id, payment_date, amount))

        if reasons:
            problems.append(RowProblem(row_number, tuple(reasons), _row_values(row)))

    accounted_total = sum(
        (line.amount for line in (purchases if record_type == "purchase" else payments)),
        Decimal("0.00"),
    )
    ties = not problems and read_total == accounted_total
    if declared_total is not None:
        ties = ties and read_total == declared_total
    totals = ControlTotals(detail_rows, read_total, accounted_total, ties, declared_total)
    if problems:
        raise IngestError(
            f"Import refused: {len(problems)} row(s) could not be parsed. "
            "Correct every listed row and import again.",
            row_problems=problems,
            control_totals=totals,
        )
    if not ties:
        expected = f"; declared total is {declared_total}" if declared_total is not None else ""
        raise IngestError(
            f"Import refused: control totals do not tie. Read {read_total}, "
            f"accounted for {accounted_total}{expected}.",
            control_totals=totals,
        )
    mapped = {column for column in mapping.values() if column}
    all_source_columns = source_columns if source_columns is not None else ()
    unmapped = tuple(str(column) for column in all_source_columns if str(column) not in mapped)
    return ImportResult(
        purchases, payments, totals, confirmations=confirmations, source=source,
        vendor_data=vendor_data,
        invoice_supplements=invoice_supplements,
        unmapped_columns=unmapped,
    )


def import_excel_or_csv(
    path: str | Path,
    mapping: Mapping[str, str],
    *,
    record_type: str = "purchase",
    sheet_name: Any = 0,
    expected_total: Any = None,
    client_id: Optional[str] = None,
    mapping_folder: Optional[str | Path] = None,
) -> ImportResult:
    """Import a mapped Excel/CSV file and refuse all partial imports."""
    if record_type not in {"purchase", "payment"}:
        raise IngestError("record_type must be 'purchase' or 'payment'")
    source_path = Path(path)
    table = _read_table(source_path, sheet_name)
    _validate_mapping(mapping, table.columns, record_type)
    rows = ((int(index) + 2, row.to_dict()) for index, row in table.iterrows())
    result = _parse_rows(
        rows, mapping, record_type=record_type, source=str(source_path),
        expected_total=expected_total, source_columns=table.columns,
    )
    if client_id is not None or mapping_folder is not None:
        if not client_id or mapping_folder is None:
            raise IngestError("Both client_id and mapping_folder are required to remember a mapping")
        save_client_mapping(mapping_folder, client_id, mapping, record_type=record_type)
    return result


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].upper()


def _first_text(element: ET.Element, names: Iterable[str]) -> str:
    wanted = {name.upper() for name in names}
    for child in element.iter():
        if _local_name(child.tag) in wanted and child.text and child.text.strip():
            return child.text.strip()
    return ""


def _ledger_amount(voucher: ET.Element, party_name: str) -> str:
    fallback = ""
    for entry in voucher.iter():
        if _local_name(entry.tag) not in {"ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST"}:
            continue
        ledger = _first_text(entry, ("LEDGERNAME",))
        amount = _first_text(entry, ("AMOUNT",))
        if amount and not fallback:
            fallback = amount
        if amount and party_name and ledger.casefold() == party_name.casefold():
            return amount
    return fallback or _first_text(voucher, ("AMOUNT",))


def _vendor_from_narration(narration: str) -> str:
    clean = re.sub(r"\s+", " ", narration).strip()
    match = re.search(
        r"(?i)(?:purchased?\s+from|paid\s+to|vendor|party)\s*[:\-]?\s*"
        r"(.+?)(?=\s+(?:for|against|invoice|bill)\b|$)",
        clean,
    )
    return (match.group(1) if match else clean).strip(" .,-")


def import_tally_xml(path: str | Path | bytes) -> ImportResult:
    """Import Tally purchase/payment vouchers, preserving confirmation flags."""
    try:
        if isinstance(path, bytes):
            root = ET.fromstring(path)
            source_label = "Tally XML upload"
        else:
            source_path = Path(path)
            root = ET.parse(source_path).getroot()
            source_label = str(source_path)
    except (OSError, ET.ParseError) as exc:
        raise IngestError(f"Could not parse Tally XML: {exc}") from exc

    purchases: list[PurchaseLine] = []
    payments: list[PaymentLine] = []
    confirmations: list[ConfirmationFlag] = []
    problems: list[RowProblem] = []
    total_read = Decimal("0.00")
    line_count = 0

    vouchers = [node for node in root.iter() if _local_name(node.tag) == "VOUCHER"]
    for row_number, voucher in enumerate(vouchers, 1):
        voucher_type = _first_text(voucher, ("VOUCHERTYPENAME",))
        kind = "purchase" if "purchase" in voucher_type.casefold() else (
            "payment" if "payment" in voucher_type.casefold() else ""
        )
        if not kind:
            continue
        line_count += 1
        reasons: list[str] = []
        voucher_number = _first_text(voucher, ("VOUCHERNUMBER", "REFERENCE"))
        if not voucher_number:
            reasons.append("voucher number is blank")
        try:
            voucher_date = parse_indian_date(_first_text(voucher, ("DATE",)), field_name="voucher date")
        except ValueError as exc:
            reasons.append(str(exc))
            voucher_date = None

        party_name = _first_text(voucher, ("PARTYLEDGERNAME",))
        narration_used = False
        if not party_name:
            narration = _first_text(voucher, ("NARRATION",))
            party_name = _vendor_from_narration(narration) if narration else ""
            narration_used = bool(party_name)
        if not party_name:
            reasons.append("party ledger name is blank and could not be extracted from narration")
        try:
            amount = parse_indian_amount(_ledger_amount(voucher, party_name))
            total_read += amount
        except ValueError as exc:
            reasons.append(str(exc))
            amount = None

        if kind == "purchase":
            if not reasons and voucher_date is not None and amount is not None:
                vendor_id = "NAME:" + normalise_name(party_name)
                purchases.append(PurchaseLine(
                    voucher_number, vendor_id, party_name, voucher_date, amount
                ))
        else:
            invoice_reference = _first_text(voucher, ("BILLALLOCATIONS.LIST",))
            # BILLALLOCATIONS.LIST is a container; NAME contains the invoice ref.
            for node in voucher.iter():
                if _local_name(node.tag) == "BILLALLOCATIONS.LIST":
                    invoice_reference = _first_text(node, ("NAME",))
                    if invoice_reference:
                        break
            if not invoice_reference:
                invoice_reference = voucher_number
                confirmations.append(ConfirmationFlag(
                    row_number, "invoice_number", invoice_reference,
                    "Tally payment has no bill allocation; confirm the invoice reference",
                ))
            if not reasons and voucher_date is not None and amount is not None:
                payments.append(PaymentLine(invoice_reference, voucher_date, amount))

        if narration_used:
            confirmations.append(ConfirmationFlag(
                row_number, "vendor_name", party_name,
                "Vendor name was extracted from narration; user confirmation is required",
            ))
        if reasons:
            problems.append(RowProblem(row_number, tuple(reasons), {
                "voucher_type": voucher_type,
                "voucher_number": voucher_number,
                "party_name": party_name,
            }))

    accounted = sum((p.amount for p in purchases), Decimal("0.00")) + sum(
        (p.amount for p in payments), Decimal("0.00")
    )
    totals = ControlTotals(line_count, total_read, accounted, not problems and total_read == accounted)
    if problems or not totals.ties:
        raise IngestError(
            f"Tally import refused: {len(problems)} voucher(s) could not be parsed.",
            row_problems=problems,
            control_totals=totals,
        )
    return ImportResult(purchases, payments, totals, confirmations, source_label)


class ManualEntryGrid:
    """Editable in-memory row model for a desktop grid, including Excel paste."""

    def __init__(self, record_type: str = "purchase") -> None:
        if record_type not in {"purchase", "payment"}:
            raise IngestError("record_type must be 'purchase' or 'payment'")
        self.record_type = record_type
        self.rows: list[dict[str, Any]] = []

    def add_row(self, **values: Any) -> int:
        self.rows.append(dict(values))
        return len(self.rows) - 1

    def update_row(self, index: int, **values: Any) -> None:
        self.rows[index].update(values)

    def delete_row(self, index: int) -> None:
        del self.rows[index]

    def paste_from_excel(self, clipboard_text: str) -> dict[str, str]:
        reader = csv.reader(io.StringIO(clipboard_text), delimiter="\t")
        matrix = list(reader)
        if not matrix:
            raise IngestError("Nothing was pasted")
        headers = [str(value).strip() for value in matrix[0]]
        if not any(headers):
            raise IngestError("Pasted data has no header row")
        for values in matrix[1:]:
            padded = values + [""] * max(0, len(headers) - len(values))
            self.rows.append(dict(zip(headers, padded)))
        return suggest_mapping(headers, self.record_type)

    def import_rows(
        self,
        mapping: Mapping[str, str],
        *,
        expected_total: Any = None,
    ) -> ImportResult:
        columns = {key for row in self.rows for key in row}
        _validate_mapping(mapping, columns, self.record_type)
        return _parse_rows(
            ((number, row) for number, row in enumerate(self.rows, 1)),
            mapping,
            record_type=self.record_type,
            source="manual entry",
            expected_total=expected_total,
            source_columns=columns,
        )
