"""Offline, deterministic parsing of Udyam registration certificates.

The parser is deliberately separate from the statutory classification module.
It extracts facts from a document, records what it could not read, and requires
the desktop workflow to obtain human confirmation before any value is used.
No network service, AI model, or external API is involved.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional


PARSER_VERSION = "udyam-text-v1"
UDYAM_PATTERN = re.compile(r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b", re.IGNORECASE)
PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)


class UdyamParseError(ValueError):
    """A safe, actionable failure while reading an evidence document."""

    def __init__(self, message: str, *, code: str = "PARSE_FAILED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ClassificationHistoryEntry:
    classification_year: str
    enterprise_class: str
    classification_date: Optional[date] = None


@dataclass(frozen=True)
class NicActivity:
    nic_code: str
    activity: str = ""


@dataclass(frozen=True)
class UdyamCertificateData:
    udyam_no: Optional[str] = None
    enterprise_name: Optional[str] = None
    enterprise_class: Optional[str] = None
    major_activity: Optional[str] = None
    pan: Optional[str] = None
    organisation_type: Optional[str] = None
    incorporation_date: Optional[date] = None
    commencement_date: Optional[date] = None
    registration_date: Optional[date] = None
    registered_address: Optional[str] = None
    classification_history: tuple[ClassificationHistoryEntry, ...] = ()
    nic_activities: tuple[NicActivity, ...] = ()
    parser_version: str = PARSER_VERSION
    source_sha256: str = ""
    extraction_method: str = "PDF_TEXT"
    field_status: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    def class_for_year(self, financial_year: str) -> Optional[ClassificationHistoryEntry]:
        """Return only an exact certificate-year match; never guess across years."""
        return next(
            (item for item in self.classification_history
             if item.classification_year == financial_year),
            None,
        )


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip(" :-\n\t")


def _label_value(text: str, label: str, following_labels: tuple[str, ...]) -> Optional[str]:
    stops = "|".join(re.escape(item) for item in following_labels)
    match = re.search(
        rf"{re.escape(label)}\s*[:\-]?\s*(.+?)(?=\s*(?:{stops})\s*[:\-]?|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    return _clean(match.group(1)) if match and _clean(match.group(1)) else None


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", value)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%d/%m/%Y").date()
    except ValueError:
        return None


def extract_pdf_text(content: bytes) -> str:
    if not content.startswith(b"%PDF"):
        raise UdyamParseError(
            "The selected file is not a valid PDF certificate.", code="INVALID_PDF"
        )
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise UdyamParseError(
                "The Udyam PDF is password-protected. Save an unlocked copy and upload it again.",
                code="PASSWORD_PROTECTED",
            )
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except UdyamParseError:
        raise
    except Exception as exc:
        raise UdyamParseError(
            f"The Udyam PDF could not be read: {exc}", code="CORRUPTED_PDF"
        ) from exc
    if len(_clean(text)) < 80:
        raise UdyamParseError(
            "This appears to be a scanned/image-only certificate. The original is retained, "
            "but automatic OCR is not available in this offline build; enter the values manually.",
            code="OCR_REQUIRED",
        )
    return text


def parse_udyam_text(text: str, *, source_sha256: str = "") -> UdyamCertificateData:
    """Parse text from current and annexure-style Udyam certificates."""
    raw = text.replace("\r", "\n")
    flat = _clean(raw)
    if "UDYAM" not in flat.upper():
        raise UdyamParseError(
            "The document does not appear to be an Udyam registration certificate.",
            code="NOT_UDYAM",
        )

    udyam_match = UDYAM_PATTERN.search(flat)
    udyam_no = udyam_match.group(0).upper() if udyam_match else None

    enterprise_name = _label_value(
        flat,
        "NAME OF ENTERPRISE",
        ("TYPE OF ENTERPRISE", "OWNER NAME", "TYPE OF ORGANISATION"),
    )
    if not enterprise_name:
        enterprise_name = _label_value(
            flat,
            "Name of Enterprise",
            ("Owner Name", "PAN", "Do you have GSTIN"),
        )

    history: list[ClassificationHistoryEntry] = []
    seen_years: set[str] = set()
    for match in re.finditer(
        r"(?:^|\n)\s*\d+\s+(20\d{2}-\d{2})\s+"
        r"(Micro|Small|Medium)\s+(\d{2}/\d{2}/\d{4})",
        raw,
        re.IGNORECASE,
    ):
        year = match.group(1)
        if year in seen_years:
            continue
        seen_years.add(year)
        history.append(ClassificationHistoryEntry(
            year,
            match.group(2).upper(),
            _parse_date(match.group(3)),
        ))

    class_match = re.search(
        r"Type of Enterprise\s*\*?\s*(?:SNo\..*?)?\b(Micro|Small|Medium)\b",
        flat,
        re.IGNORECASE,
    )
    enterprise_class = history[0].enterprise_class if history else (
        class_match.group(1).upper() if class_match else None
    )

    activity_match = re.search(
        r"MAJOR ACTIVITY\s*[:\-]?\s*(MANUFACTURING|SERVICES?|TRADING)",
        flat,
        re.IGNORECASE,
    )
    major_activity = activity_match.group(1).upper() if activity_match else None

    pan_match = re.search(r"\bPAN\s*[:\-]?\s*([A-Z]{5}\d{4}[A-Z])\b", flat, re.IGNORECASE)
    pan = pan_match.group(1).upper() if pan_match else None

    organisation_type = _label_value(
        flat,
        "Type of Organisation",
        ("Name of Enterprise", "Owner Name", "PAN"),
    )

    incorporation_date = _parse_date(_label_value(
        flat,
        "DATE OF INCORPORATION / REGISTRATION OF ENTERPRISE",
        ("DATE OF COMMENCEMENT OF PRODUCTION/BUSINESS", "NATIONAL INDUSTRY"),
    )) or _parse_date(_label_value(
        flat,
        "Date of Incorporation",
        ("Date of Commencement of Production/Business", "Bank Details"),
    ))
    commencement_date = _parse_date(_label_value(
        flat,
        "DATE OF COMMENCEMENT OF PRODUCTION/BUSINESS",
        ("NATIONAL INDUSTRY", "DATE OF UDYAM REGISTRATION"),
    )) or _parse_date(_label_value(
        flat,
        "Date of Commencement of Production/Business",
        ("Bank Details", "Employment Details"),
    ))
    registration_date = _parse_date(_label_value(
        flat,
        "DATE OF UDYAM REGISTRATION",
        ("Date of Printing", "Disclaimer", "IEC Details"),
    ))

    address_match = re.search(
        r"OFFI(?:C|CI)AL ADDRESS OF ENTERPRISE\s*(.+?)"
        r"(?=\s+Mobile\s|\s+DATE OF INCORPORATION|\s+National Industry)",
        flat,
        re.IGNORECASE | re.DOTALL,
    )
    registered_address = _clean(address_match.group(1)) if address_match else None

    nic_activities: list[NicActivity] = []
    seen_nic: set[str] = set()
    for nic_match in re.finditer(r"\b(\d{5})\s*-\s*([^\n]{3,180}?)(?=\b\d{5}\s*-|Trading|Manufacturing|Services|$)", raw, re.IGNORECASE):
        code = nic_match.group(1)
        if code in seen_nic:
            continue
        seen_nic.add(code)
        nic_activities.append(NicActivity(code, _clean(nic_match.group(2))))
    if not nic_activities:
        for code in re.findall(r"\b(?:NIC\s*5\s*Digit\s*)?(\d{5})\b", flat, re.IGNORECASE):
            if code not in seen_nic:
                seen_nic.add(code)
                nic_activities.append(NicActivity(code, major_activity or ""))

    values = {
        "udyam_no": udyam_no,
        "enterprise_name": enterprise_name,
        "enterprise_class": enterprise_class,
        "major_activity": major_activity,
        "pan": pan,
        "organisation_type": organisation_type,
        "incorporation_date": incorporation_date,
        "commencement_date": commencement_date,
        "registration_date": registration_date,
        "registered_address": registered_address,
        "classification_history": history,
        "nic_activities": nic_activities,
    }
    field_status = {
        key: "EXTRACTED" if value else "NOT_FOUND" for key, value in values.items()
    }
    warnings = []
    if not history:
        warnings.append(
            "No year-wise classification table was found. Confirm which classification applies to the project year."
        )
    if not udyam_no or not enterprise_name:
        warnings.append("Key certificate identity fields are missing and require manual review.")
    return UdyamCertificateData(
        udyam_no=udyam_no,
        enterprise_name=enterprise_name,
        enterprise_class=enterprise_class,
        major_activity=major_activity,
        pan=pan,
        organisation_type=organisation_type,
        incorporation_date=incorporation_date,
        commencement_date=commencement_date,
        registration_date=registration_date,
        registered_address=registered_address,
        classification_history=tuple(history),
        nic_activities=tuple(nic_activities),
        source_sha256=source_sha256,
        field_status=field_status,
        warnings=tuple(warnings),
    )


def parse_udyam_certificate(
    content: bytes,
    *,
    filename: str = "certificate.pdf",
    media_type: str = "application/pdf",
) -> UdyamCertificateData:
    """Read a Udyam PDF. Image-only documents are retained for manual review."""
    if not content:
        raise UdyamParseError("The selected certificate is empty.", code="EMPTY_FILE")
    suffix = Path(filename).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"} or media_type.startswith("image/"):
        raise UdyamParseError(
            "Image certificates can be retained as evidence, but automatic OCR is not available "
            "in this offline build. Enter and confirm the certificate values manually.",
            code="OCR_REQUIRED",
        )
    if suffix != ".pdf" and media_type != "application/pdf":
        raise UdyamParseError(
            "Upload a PDF, PNG or JPEG Udyam certificate.", code="UNSUPPORTED_FILE"
        )
    digest = hashlib.sha256(content).hexdigest()
    return parse_udyam_text(extract_pdf_text(content), source_sha256=digest)
