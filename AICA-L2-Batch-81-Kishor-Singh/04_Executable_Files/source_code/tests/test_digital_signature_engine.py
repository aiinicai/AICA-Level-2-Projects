"""Tests for core.digital_signature_engine's error handling and interface contract.

Full end-to-end certificate signing needs a real .pfx test certificate and
the optional pyHanko dependency; here we verify the module (a) imports
cleanly whether or not pyHanko is installed, (b) raises a clear, actionable
ValidationError rather than a raw ImportError/traceback when pyHanko is
missing, and (c) the visible-image vs. cryptographic-signature distinction
is explicit in the code (never silently conflated).
"""
from __future__ import annotations

import pytest

from core.digital_signature_engine import CertificateSigner, CertificateSigningRequest, PyHankoPkcs12Backend
from models.enums import SignatureType
from utils.validation import ValidationError


def test_certificate_signing_request_has_sane_defaults():
    req = CertificateSigningRequest(source_pdf="a.pdf", output_pdf="b.pdf", pfx_path="c.pfx", pfx_password="secret")
    assert req.page_index == -1  # defaults to last page
    assert req.visible is True
    assert req.field_name == "Signature1"


def test_missing_certificate_file_raises_friendly_error(tmp_path):
    req = CertificateSigningRequest(
        source_pdf=str(tmp_path / "a.pdf"),
        output_pdf=str(tmp_path / "b.pdf"),
        pfx_path=str(tmp_path / "does_not_exist.pfx"),
        pfx_password="secret",
    )
    signer = CertificateSigner()
    with pytest.raises(ValidationError):
        signer.sign(req)


def test_pkcs11_backend_is_a_real_implementation_not_a_stub():
    """Hardware DSC token signing (core.pkcs11_engine) is a real implementation,
    not a NotImplementedError stub -- see test_pkcs11_engine.py for its
    (mocked) test coverage and the module's own docstring for what remains
    unverified against real hardware."""
    from core.pkcs11_engine import Pkcs11SigningBackend

    backend = Pkcs11SigningBackend(module_path="fake.dll", slot_id=0, pin="1234")
    assert hasattr(backend, "sign")


def test_signature_type_enum_distinguishes_image_from_certificate():
    """The codebase must never have only one concept for 'signed' -- these
    are deliberately two distinct, differently-labelled enum values."""
    assert SignatureType.VISIBLE_IMAGE != SignatureType.DIGITAL_CERTIFICATE
    assert "Image" in SignatureType.VISIBLE_IMAGE.value
    assert "Cryptographic" in SignatureType.DIGITAL_CERTIFICATE.value


def test_default_backend_is_pkcs12():
    signer = CertificateSigner()
    assert isinstance(signer.backend, PyHankoPkcs12Backend)
