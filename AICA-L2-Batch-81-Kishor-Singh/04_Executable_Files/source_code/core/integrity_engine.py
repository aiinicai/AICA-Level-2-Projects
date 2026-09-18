"""QR integrity stamping and local verification.

Design, deliberately scoped to what is honestly achievable offline:

1. :func:`stamp_document_id` generates a short document ID, encodes it in a
   QR code, and stamps both the QR image *and* the ID as plain text onto the
   document -- **before** any further processing (OCR, watermarking,
   cryptographic signing). This avoids the classic self-reference error of
   hashing a file that already contains its own final hash: the ID is fixed
   first, and the hash of the truly final bytes is registered afterwards.

2. :func:`register_final_hash` computes the SHA-256 of the final, fully
   processed file and stores ``document_id -> (hash, filename, timestamp)``
   in the local SQLite database (see :mod:`utils.database`).

3. :func:`verify_file` reads a document's plain-text "Doc ID:" line (printed
   next to the QR precisely so verification never needs a QR *decoder*
   dependency), looks it up in the local registry, and reports whether the
   current file's hash matches what was registered.

**This is a local-machine registry, not a public verification service.**
Scanning the QR alone proves nothing to a third party -- it encodes the
document ID as a convenience/future-proofing measure (a later, genuinely
server-backed Phase 3 could resolve the same ID over the network), but
today, verification only works by opening this app on the same computer
(or a copy of the same database) where the document was originally
registered. The README and UI make this limitation explicit.
"""
from __future__ import annotations

import hashlib
import io
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import qrcode

from core.page_selection import resolve_pages
from core.pdf_engine import open_pdf
from core.signature_engine import MM_TO_PT
from models.enums import PositionPreset
from utils.database import Database

_ID_PREFIX = "CADOCUFLOW-VERIFY"
_ID_LINE_PATTERN = re.compile(r"Doc ID:\s*([A-F0-9]{8,16})")


def generate_document_id() -> str:
    return uuid.uuid4().hex[:12].upper()


def compute_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class StampResult:
    document_id: str
    output_path: str


def stamp_document_id(
    source_path: str | Path,
    output_path: str | Path,
    document_id: str | None = None,
    position: PositionPreset = PositionPreset.BOTTOM_LEFT,
    page_rule_expression: str = "last",
    box_size_mm: float = 20.0,
    margin_mm: float = 10.0,
) -> StampResult:
    """Stamp a QR code + human-readable Doc ID onto the resolved page(s).

    Call this *first*, before OCR/watermarking/signing -- the ID must be
    fixed before any later step, and the final SHA-256 is only registered
    once every other processing step is complete (see module docstring).
    """
    doc_id = document_id or generate_document_id()
    qr_img = qrcode.make(f"{_ID_PREFIX}:{doc_id}")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_bytes = buf.getvalue()

    box_size_pt = box_size_mm * MM_TO_PT
    margin_pt = margin_mm * MM_TO_PT

    with open_pdf(source_path) as doc:
        pages = resolve_pages(page_rule_expression, doc.page_count)
        for page_no in pages:
            page = doc[page_no - 1]
            rect = page.rect
            if position == PositionPreset.BOTTOM_RIGHT:
                x = rect.width - margin_pt - box_size_pt
                y = rect.height - margin_pt - box_size_pt
            elif position == PositionPreset.TOP_LEFT:
                x, y = margin_pt, margin_pt
            elif position == PositionPreset.TOP_RIGHT:
                x, y = rect.width - margin_pt - box_size_pt, margin_pt
            else:  # BOTTOM_LEFT default
                x, y = margin_pt, rect.height - margin_pt - box_size_pt

            qr_rect = fitz.Rect(x, y, x + box_size_pt, y + box_size_pt)
            page.insert_image(qr_rect, stream=qr_bytes, overlay=True)
            page.insert_text(
                fitz.Point(x, y + box_size_pt + 9), f"Doc ID: {doc_id}", fontsize=7, fontname="helv", color=(0, 0, 0)
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=3, deflate=True)

    return StampResult(document_id=doc_id, output_path=str(output_path))


def register_final_hash(database: Database, document_id: str, final_file_path: str | Path, operator: str = "") -> str:
    """Register the SHA-256 of the truly final file. Call this last, after
    every other processing step (including cryptographic signing) is done."""
    sha256 = compute_sha256(final_file_path)
    database.register_integrity_record(document_id, sha256, Path(final_file_path).name, operator)
    return sha256


def extract_document_id(path: str | Path) -> str | None:
    with open_pdf(path) as doc:
        for i in range(doc.page_count):
            match = _ID_LINE_PATTERN.search(doc[i].get_text())
            if match:
                return match.group(1)
    return None


@dataclass
class VerificationResult:
    document_id: str | None
    registered_locally: bool
    hash_matches: bool | None  # None when not registered (nothing to compare against)
    registered_at: str | None = None
    registered_filename: str | None = None
    current_sha256: str = ""


def verify_file(path: str | Path, database: Database) -> VerificationResult:
    """Check a document against this computer's local integrity registry.

    Returns a result even when nothing is found -- callers must present a
    clear "not registered on this computer" state rather than assuming
    failure means tampering; the record may simply live in a different
    installation's database.
    """
    document_id = extract_document_id(path)
    current_hash = compute_sha256(path)
    if not document_id:
        return VerificationResult(document_id=None, registered_locally=False, hash_matches=None, current_sha256=current_hash)

    record = database.get_integrity_record(document_id)
    if not record:
        return VerificationResult(document_id=document_id, registered_locally=False, hash_matches=None, current_sha256=current_hash)

    return VerificationResult(
        document_id=document_id,
        registered_locally=True,
        hash_matches=(current_hash == record["sha256"]),
        registered_at=record["registered_at"],
        registered_filename=record["filename"],
        current_sha256=current_hash,
    )
