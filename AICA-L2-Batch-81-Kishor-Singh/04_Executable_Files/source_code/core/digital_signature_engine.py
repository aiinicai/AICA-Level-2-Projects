"""Certificate-based cryptographic PDF signing (PKCS#12 / .pfx / .p12).

This is deliberately a *separate* module and code path from
:mod:`core.signature_engine`. A visible signature image is a cosmetic
overlay; the output of this module is a real PAdES/PKCS#7 signature over the
document bytes, verifiable in Adobe Reader / any PDF validator. The two must
never be conflated in the UI or in generated reports.

Implementation uses `pyHanko <https://github.com/MatthiasValvekens/pyHanko>`_,
a maintained, standards-based PDF signing library. pyHanko is an optional
dependency (see requirements.txt) -- if it is not installed, this module
raises a clear, actionable error rather than silently falling back to an
image stamp.

Hardware token (USB DSC / PKCS#11) support
-------------------------------------------
Many Indian/international Digital Signature Certificate (DSC) USB tokens
(ePass2003, ProxKey, etc.) expose their private key via a manufacturer
PKCS#11 driver rather than as an exportable .pfx file. That path is
implemented in :mod:`core.pkcs11_engine` as a second :class:`SigningBackend`
(``Pkcs11SigningBackend``) sharing this module's signing pipeline via
:func:`sign_with_pyhanko_signer` -- see that module's docstring for what is
and isn't verified (real vendor hardware requires the vendor's own
middleware and has not been tested against a physical token).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from utils.validation import ValidationError


@dataclass
class CertificateSigningRequest:
    """Everything needed to produce one cryptographic signature on one PDF."""

    source_pdf: str
    output_pdf: str
    pfx_path: str
    pfx_password: str
    reason: str = ""
    location: str = ""
    contact_info: str = ""
    field_name: str = "Signature1"
    page_index: int = -1  # -1 == last page
    visible: bool = True
    box_x_pt: float = 36.0
    box_y_pt: float = 36.0
    box_width_pt: float = 180.0
    box_height_pt: float = 60.0
    visible_text: str = ""  # optional extra text drawn in the signature box


class SigningBackend(Protocol):
    """Swappable backend interface so a future PKCS#11/hardware-token signer
    can be added without changing calling code in the UI/workers."""

    def sign(self, request: CertificateSigningRequest) -> str: ...


def _require_pyhanko():
    try:
        from pyhanko.sign import signers, fields  # noqa: F401
    except ImportError as exc:
        raise ValidationError(
            "Certificate-based digital signing requires the 'pyHanko' "
            "package, which is not installed. Install it with:\n\n"
            "    pip install pyHanko\n\n"
            "and restart the application."
        ) from exc


def sign_with_pyhanko_signer(request: CertificateSigningRequest, signer) -> str:
    """Shared signing pipeline used by every backend once a pyHanko ``Signer``
    object has been constructed (PKCS#12 or PKCS#11) -- builds the signature
    field, applies the incremental update, and writes the output file."""
    from pyhanko.sign import fields, PdfSignatureMetadata
    from pyhanko.sign.fields import SigFieldSpec
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign.signers.pdf_signer import PdfSigner

    from core.pdf_engine import open_pdf

    with open_pdf(request.source_pdf) as doc:
        total_pages = doc.page_count
    page_index = total_pages - 1 if request.page_index < 0 else request.page_index

    with open(request.source_pdf, "rb") as f:
        writer = IncrementalPdfFileWriter(f)
        sig_field_spec = SigFieldSpec(
            sig_field_name=request.field_name,
            on_page=page_index,
            box=(
                request.box_x_pt,
                request.box_y_pt,
                request.box_x_pt + request.box_width_pt,
                request.box_y_pt + request.box_height_pt,
            ),
        )
        fields.append_signature_field(writer, sig_field_spec)

        meta = PdfSignatureMetadata(
            field_name=request.field_name,
            reason=request.reason or None,
            location=request.location or None,
        )
        pdf_signer = PdfSigner(meta, signer=signer)

        output_path = Path(request.output_pdf)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as out_f:
            pdf_signer.sign_pdf(writer, output=out_f)

    return str(output_path)


class PyHankoPkcs12Backend:
    """Signs using a PKCS#12 (.pfx/.p12) file loaded directly from disk.

    The certificate password is used only in-memory for the duration of the
    signing call and is never written to disk, logs, or the settings/audit
    database.
    """

    def sign(self, request: CertificateSigningRequest) -> str:
        _require_pyhanko()
        from pyhanko.sign import signers

        pfx_path = Path(request.pfx_path)
        if not pfx_path.exists():
            raise ValidationError(f"Certificate file not found:\n{pfx_path}")

        try:
            signer = signers.SimpleSigner.load_pkcs12(
                pfx_file=str(pfx_path), passphrase=request.pfx_password.encode("utf-8")
            )
        except Exception as exc:
            raise ValidationError(
                "Could not load the certificate. Please check the .pfx/.p12 "
                "file and password are correct and the certificate is not "
                "expired or corrupted."
            ) from exc
        if signer is None:
            raise ValidationError("Certificate password is incorrect or the file is not a valid PKCS#12 certificate.")

        return sign_with_pyhanko_signer(request, signer)


class CertificateSigner:
    """Facade used by the UI/workers; hides which concrete backend is active."""

    def __init__(self, backend: SigningBackend | None = None):
        self.backend = backend or PyHankoPkcs12Backend()

    def sign(self, request: CertificateSigningRequest) -> str:
        return self.backend.sign(request)
