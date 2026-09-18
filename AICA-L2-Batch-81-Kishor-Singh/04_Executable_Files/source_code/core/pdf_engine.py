"""Low-level PDF utilities built on PyMuPDF (fitz).

Everything that needs to open, inspect or rasterize a PDF for preview goes
through here, so encryption handling, corrupt-file detection and page-size
queries are consistent across the signing, merge, split, organizer and
watermark engines.

LICENSING NOTE: PyMuPDF is dual-licensed AGPL-3.0-only / commercial (Artifex
Software) -- see https://github.com/pymupdf/pymupdf. This is a conscious,
documented trade-off (PyMuPDF's redaction/rendering/text-layout support is
more mature than permissive alternatives) made for a private, non-commercial
build. Before distributing this application beyond personal/internal use --
to other CAs, clients, or as a sold product -- either purchase a commercial
PyMuPDF license from Artifex, or migrate this module and its callers
(signature_engine, merge_engine, split_engine, page_organizer,
watermark_engine, ocr_engine, redaction_engine, comparison_engine) to
permissively-licensed alternatives such as pikepdf + pypdf + reportlab.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from utils.validation import EncryptedPdfError, ValidationError


@dataclass
class PageInfo:
    index: int  # 0-based
    width_pt: float
    height_pt: float

    @property
    def page_number(self) -> int:  # 1-based, for display
        return self.index + 1

    @property
    def is_landscape(self) -> bool:
        return self.width_pt > self.height_pt


def _attempt_repair_with_pikepdf(path: Path) -> bytes | None:
    """Best-effort repair of a structurally damaged PDF using pikepdf/qpdf.

    Many "corrupt" PDFs encountered in office use (truncated downloads,
    scanner firmware quirks, older Acrobat producers) are actually just
    malformed enough that PyMuPDF's stricter parser refuses them, while
    qpdf's tolerant rewriter can still make sense of them. On success this
    returns fully rewritten PDF bytes for :func:`open_pdf` to retry with;
    returns ``None`` if pikepdf isn't installed or repair also fails, in
    which case the caller reports the original "may be corrupted" error.
    """
    try:
        import io

        import pikepdf
    except ImportError:
        return None
    try:
        with pikepdf.open(str(path)) as pdf:
            buf = io.BytesIO()
            pdf.save(buf)
            return buf.getvalue()
    except Exception:
        return None


def open_pdf(path: str | Path, password: str | None = None) -> fitz.Document:
    """Open a PDF, raising friendly errors for corruption/encryption.

    Callers are responsible for closing the returned document (use it as a
    context manager: ``with open_pdf(p) as doc:``; :class:`fitz.Document`
    supports the context-manager protocol).
    """
    path = Path(path)
    if not path.exists():
        raise ValidationError(f"File not found:\n{path}")
    try:
        doc = fitz.open(str(path))
    except Exception as first_exc:  # pragma: no cover - fitz raises plain Exception
        repaired_bytes = _attempt_repair_with_pikepdf(path)
        if repaired_bytes is None:
            raise ValidationError(f"'{path.name}' could not be opened. It may be corrupted.") from first_exc
        try:
            doc = fitz.open(stream=repaired_bytes, filetype="pdf")
        except Exception as exc:
            raise ValidationError(f"'{path.name}' could not be opened. It may be corrupted.") from exc

    if doc.needs_pass:
        if not password:
            doc.close()
            raise EncryptedPdfError(f"'{path.name}' is password protected. Please supply a password.")
        if not doc.authenticate(password):
            doc.close()
            raise EncryptedPdfError(f"Incorrect password for '{path.name}'.")
        # authenticate() returns a permission bitmask on success (or 0 on
        # user-password-only docs granting full perms); verify we actually
        # have edit permission before allowing further processing.
        perms = doc.permissions
        if not (perms & fitz.PDF_PERM_MODIFY):
            doc.close()
            raise ValidationError(
                f"'{path.name}' is protected against modification by its owner "
                "password. It cannot be signed, merged or split without the "
                "owner's permission."
            )

    if doc.page_count == 0:
        doc.close()
        raise ValidationError(f"'{path.name}' has no pages.")

    return doc


def get_page_count(path: str | Path, password: str | None = None) -> int:
    with open_pdf(path, password) as doc:
        return doc.page_count


def is_encrypted(path: str | Path) -> bool:
    try:
        doc = fitz.open(str(path))
    except Exception:
        return False
    encrypted = doc.needs_pass
    doc.close()
    return encrypted


def get_page_info(doc: fitz.Document, index: int) -> PageInfo:
    page = doc[index]
    rect = page.rect
    return PageInfo(index=index, width_pt=rect.width, height_pt=rect.height)


def render_page_to_png_bytes(doc: fitz.Document, index: int, zoom: float = 1.5) -> bytes:
    """Rasterize a page for on-screen preview. ``zoom`` 1.0 == 72 DPI."""
    page = doc[index]
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    return pixmap.tobytes("png")


def validate_pdf_integrity(path: str | Path) -> tuple[bool, str]:
    """Quick structural sanity check, used before adding a file to a batch."""
    try:
        with open_pdf(path) as doc:
            _ = doc.page_count
        return True, ""
    except EncryptedPdfError:
        return True, "Password protected"
    except ValidationError as exc:
        return False, str(exc)
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"Unreadable PDF: {exc}"


@dataclass
class RepairOutcome:
    output_path: str
    page_count: int
    repaired: bool  # False if the source already opened cleanly and no repair was needed


def repair_pdf(source_path: str | Path, output_path: str | Path) -> RepairOutcome:
    """Standalone "Repair PDF" tool: rewrite a structurally damaged file into a clean copy.

    This exposes the same pikepdf/qpdf-based recovery that :func:`open_pdf`
    already falls back to automatically for corrupt files, as a tool the
    user can invoke directly on a file that seems fine but behaves oddly in
    other viewers -- rewriting via qpdf often fixes subtle structural issues
    even when the file already opens.
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise ValidationError(f"File not found:\n{source_path}")

    repaired_bytes = _attempt_repair_with_pikepdf(source_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if repaired_bytes is not None:
        output_path.write_bytes(repaired_bytes)
        with fitz.open(str(output_path)) as doc:
            page_count = doc.page_count
        return RepairOutcome(output_path=str(output_path), page_count=page_count, repaired=True)

    # pikepdf either isn't installed or couldn't improve on the original --
    # fall back to confirming the file at least opens as-is via PyMuPDF, and
    # copy it through unchanged rather than claiming a repair that didn't happen.
    with open_pdf(source_path) as doc:
        page_count = doc.page_count
    output_path.write_bytes(source_path.read_bytes())
    return RepairOutcome(output_path=str(output_path), page_count=page_count, repaired=False)
