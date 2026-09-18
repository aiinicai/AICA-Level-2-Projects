"""End-to-end test of core.digital_signature_engine's PKCS#12 signing path.

This was previously only error-path tested (Phase 1), since pyHanko wasn't
installed in the dev environment at the time. Now that it is, this test
performs a REAL cryptographic signature over a self-signed test certificate
and validates it with pyHanko's own validator -- confirming both byte-range
integrity ("intact") and chain-of-trust validity ("valid") against the test
root. This is the most legally significant feature in the whole
application, so it gets its own dedicated, thorough end-to-end test rather
than relying only on unit-level mocks.
"""
from __future__ import annotations

import asyncio
import datetime

import fitz
import pytest

pytest.importorskip("pyhanko")

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from core.digital_signature_engine import CertificateSigner, CertificateSigningRequest


@pytest.fixture
def test_certificate():
    """A throwaway, self-signed RSA certificate + PFX -- never used for anything but this test."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CA Kishor Singh (Test)")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return key, cert


@pytest.fixture
def test_pfx(tmp_path, test_certificate):
    key, cert = test_certificate
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=b"test-signing-cert", key=key, cert=cert, cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(b"testpass123"),
    )
    path = tmp_path / "test_cert.pfx"
    path.write_bytes(pfx_bytes)
    return path


@pytest.fixture
def unsigned_pdf(tmp_path):
    doc = fitz.open()
    doc.new_page(width=595, height=842).insert_text((72, 100), "Agreement requiring a digital signature.")
    path = tmp_path / "to_sign.pdf"
    doc.save(str(path))
    doc.close()
    return path


def test_pkcs12_signing_produces_a_genuinely_valid_cryptographic_signature(tmp_path, test_pfx, unsigned_pdf, test_certificate):
    _key, cert = test_certificate
    output_path = tmp_path / "signed.pdf"

    signer = CertificateSigner()
    request = CertificateSigningRequest(
        source_pdf=str(unsigned_pdf), output_pdf=str(output_path), pfx_path=str(test_pfx), pfx_password="testpass123",
        reason="Approval of agreement", location="Bengaluru", field_name="Signature1",
    )
    signer.sign(request)

    assert output_path.exists()

    import asn1crypto.x509 as asn1_x509
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import async_validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext

    der_bytes = cert.public_bytes(serialization.Encoding.DER)
    asn1_cert = asn1_x509.Certificate.load(der_bytes)

    with open(output_path, "rb") as f:
        reader = PdfFileReader(f)
        sigs = reader.embedded_signatures
        assert len(sigs) == 1

        vc = ValidationContext(trust_roots=[asn1_cert], allow_fetching=False, revocation_mode="soft-fail")
        status = asyncio.run(async_validate_pdf_signature(sigs[0], vc))

    assert status.intact  # the signed byte range was not tampered with
    assert status.valid  # chains to our trusted test root
    assert "CA Kishor Singh (Test)" in status.signing_cert.subject.human_friendly


def test_tampering_after_signing_is_detected(tmp_path, test_pfx, unsigned_pdf, test_certificate):
    """A cryptographic signature must catch post-signing modification --
    this is exactly what distinguishes it from a cosmetic image stamp.

    Flips one byte inside the ORIGINAL (pre-signature) portion of the file --
    incremental signing appends the signature after the source bytes
    untouched, so any single-byte change in that original prefix must fall
    inside the signature's covered byte range and break integrity.
    """
    _key, cert = test_certificate
    output_path = tmp_path / "signed.pdf"
    original_source_length = len(unsigned_pdf.read_bytes())

    signer = CertificateSigner()
    signer.sign(CertificateSigningRequest(
        source_pdf=str(unsigned_pdf), output_pdf=str(output_path), pfx_path=str(test_pfx), pfx_password="testpass123",
    ))

    tampered = bytearray(output_path.read_bytes())
    flip_at = original_source_length // 2
    tampered[flip_at] = (tampered[flip_at] + 1) % 256
    tampered_path = tmp_path / "tampered.pdf"
    tampered_path.write_bytes(bytes(tampered))

    import asn1crypto.x509 as asn1_x509
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import async_validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext

    der_bytes = cert.public_bytes(serialization.Encoding.DER)
    asn1_cert = asn1_x509.Certificate.load(der_bytes)

    with open(tampered_path, "rb") as f:
        reader = PdfFileReader(f)
        sigs = reader.embedded_signatures
        vc = ValidationContext(trust_roots=[asn1_cert], allow_fetching=False, revocation_mode="soft-fail")
        status = asyncio.run(async_validate_pdf_signature(sigs[0], vc))

    assert status.intact is False


def test_wrong_password_raises_clear_error(tmp_path, test_pfx, unsigned_pdf):
    signer = CertificateSigner()
    request = CertificateSigningRequest(
        source_pdf=str(unsigned_pdf), output_pdf=str(tmp_path / "out.pdf"),
        pfx_path=str(test_pfx), pfx_password="wrong-password",
    )
    from utils.validation import ValidationError

    with pytest.raises(ValidationError):
        signer.sign(request)


def test_signature_lands_on_requested_page(tmp_path, test_pfx, test_certificate):
    _key, cert = test_certificate
    doc = fitz.open()
    for i in range(3):
        doc.new_page(width=595, height=842).insert_text((72, 100), f"Page {i + 1}")
    src = tmp_path / "multi.pdf"
    doc.save(str(src))
    doc.close()

    output_path = tmp_path / "signed.pdf"
    signer = CertificateSigner()
    signer.sign(CertificateSigningRequest(
        source_pdf=str(src), output_pdf=str(output_path), pfx_path=str(test_pfx), pfx_password="testpass123",
        page_index=-1,  # last page
    ))

    with fitz.open(str(output_path)) as result_doc:
        assert result_doc.page_count == 3
