"""Tests for core.pkcs11_engine, using a MOCKED PKCS#11 module and pyHanko
PKCS#11 signer -- there is no physical USB token or software token
(SoftHSM2) available in this environment. These tests verify our adapter's
own logic (slot/token/certificate mapping, PIN error handling, the 32-bit/
64-bit driver mismatch hint, and correct wiring into the shared pyHanko
signing pipeline) -- they do NOT verify behaviour against a real driver.
See core/pkcs11_engine.py's module docstring for how to test against a
real (software) token yourself.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from core.pkcs11_engine import (
    Pkcs11SigningBackend,
    list_available_tokens,
    list_certificates_on_token,
)
from utils.validation import ValidationError


def _install_fake_pkcs11_module():
    """Install a minimal fake `pkcs11` module into sys.modules so
    `import pkcs11` inside core.pkcs11_engine resolves to our mock,
    without needing the real python-pkcs11 C extension behaviour."""
    fake = types.ModuleType("pkcs11")
    fake.lib = MagicMock()
    fake.Attribute = types.SimpleNamespace(CLASS="CLASS", SUBJECT="SUBJECT", SERIAL_NUMBER="SERIAL_NUMBER")
    fake.ObjectClass = types.SimpleNamespace(CERTIFICATE="CERTIFICATE")

    class PinIncorrect(Exception):
        pass

    class PinLocked(Exception):
        pass

    fake.exceptions = types.SimpleNamespace(PinIncorrect=PinIncorrect, PinLocked=PinLocked)
    sys.modules["pkcs11"] = fake
    return fake


@pytest.fixture
def fake_pkcs11():
    original = sys.modules.get("pkcs11")
    fake = _install_fake_pkcs11_module()
    yield fake
    if original is not None:
        sys.modules["pkcs11"] = original
    else:
        sys.modules.pop("pkcs11", None)


def _make_mock_slot(slot_id, label, manufacturer, model):
    token = MagicMock()
    token.label = label
    token.manufacturer_id = manufacturer
    token.model = model
    slot = MagicMock()
    slot.slot_id = slot_id
    slot.get_token.return_value = token
    return slot, token


def test_list_available_tokens_maps_slots_correctly(fake_pkcs11):
    slot, _token = _make_mock_slot(0, "My DSC Token  ", "Vendor Inc  ", "Model X  ")
    lib_instance = MagicMock()
    lib_instance.get_slots.return_value = [slot]
    fake_pkcs11.lib.return_value = lib_instance

    tokens = list_available_tokens("fake_driver.dll")

    assert len(tokens) == 1
    assert tokens[0].slot_id == 0
    assert tokens[0].label == "My DSC Token"  # whitespace stripped
    assert tokens[0].manufacturer == "Vendor Inc"
    lib_instance.finalize.assert_called_once()


def test_list_available_tokens_raises_when_none_present(fake_pkcs11):
    lib_instance = MagicMock()
    lib_instance.get_slots.return_value = []
    fake_pkcs11.lib.return_value = lib_instance

    with pytest.raises(ValidationError, match="No hardware token"):
        list_available_tokens("fake_driver.dll")


def test_load_library_oserror_gives_32bit_hint(fake_pkcs11):
    fake_pkcs11.lib.side_effect = OSError("%1 is not a valid Win32 application")

    with pytest.raises(ValidationError, match="32-bit"):
        list_available_tokens("wrong_arch.dll")


def test_list_available_tokens_missing_python_pkcs11_package():
    original = sys.modules.pop("pkcs11", None)
    try:
        with patch.dict(sys.modules, {"pkcs11": None}):
            with pytest.raises(ValidationError, match="python-pkcs11"):
                list_available_tokens("driver.dll")
    finally:
        if original is not None:
            sys.modules["pkcs11"] = original


def test_list_certificates_maps_certificate_objects(fake_pkcs11):
    slot, token = _make_mock_slot(1, "Token", "Vendor", "Model")
    lib_instance = MagicMock()
    lib_instance.get_slots.return_value = [slot]
    fake_pkcs11.lib.return_value = lib_instance

    cert_obj = MagicMock()
    cert_obj.label = "My Signing Cert"
    cert_obj.__contains__ = lambda self, key: True
    cert_obj.__getitem__ = lambda self, key: b"\x01\x02\x03" if key == "SUBJECT" else b"\xaa\xbb"

    session_cm = MagicMock()
    session_cm.__enter__.return_value.get_objects.return_value = [cert_obj]
    token.open.return_value = session_cm

    certs = list_certificates_on_token("driver.dll", slot_id=1, pin="1234")

    assert len(certs) == 1
    assert certs[0].label == "My Signing Cert"
    assert certs[0].subject == "010203"
    assert certs[0].serial_number == "aabb"


def test_list_certificates_wrong_pin_raises_clear_error(fake_pkcs11):
    slot, token = _make_mock_slot(1, "Token", "Vendor", "Model")
    lib_instance = MagicMock()
    lib_instance.get_slots.return_value = [slot]
    fake_pkcs11.lib.return_value = lib_instance
    token.open.side_effect = fake_pkcs11.exceptions.PinIncorrect()

    with pytest.raises(ValidationError, match="Incorrect PIN"):
        list_certificates_on_token("driver.dll", slot_id=1, pin="0000")


def test_list_certificates_locked_pin_raises_clear_error(fake_pkcs11):
    slot, token = _make_mock_slot(1, "Token", "Vendor", "Model")
    lib_instance = MagicMock()
    lib_instance.get_slots.return_value = [slot]
    fake_pkcs11.lib.return_value = lib_instance
    token.open.side_effect = fake_pkcs11.exceptions.PinLocked()

    with pytest.raises(ValidationError, match="locked"):
        list_certificates_on_token("driver.dll", slot_id=1, pin="0000")


def test_list_certificates_token_removed_raises(fake_pkcs11):
    lib_instance = MagicMock()
    lib_instance.get_slots.return_value = []  # no slots -- token was removed
    fake_pkcs11.lib.return_value = lib_instance

    with pytest.raises(ValidationError, match="no longer present"):
        list_certificates_on_token("driver.dll", slot_id=1, pin="0000")


# --------------------------------------------------------- signing backend

def test_pkcs11_backend_calls_shared_signing_pipeline_with_correct_signer():
    fake_session = MagicMock()
    fake_signer_instance = MagicMock()

    fake_pyhanko_pkcs11 = types.ModuleType("pyhanko.sign.pkcs11")
    fake_pyhanko_pkcs11.open_pkcs11_session = MagicMock(return_value=fake_session)
    fake_pyhanko_pkcs11.PKCS11Signer = MagicMock(return_value=fake_signer_instance)

    with patch.dict(sys.modules, {"pyhanko.sign.pkcs11": fake_pyhanko_pkcs11}):
        with patch("core.pkcs11_engine.sign_with_pyhanko_signer", return_value="output.pdf") as mock_sign:
            backend = Pkcs11SigningBackend(module_path="driver.dll", slot_id=0, pin="1234", cert_label="MyCert")
            from core.digital_signature_engine import CertificateSigningRequest

            request = CertificateSigningRequest(source_pdf="a.pdf", output_pdf="b.pdf", pfx_path="", pfx_password="")
            result = backend.sign(request)

    assert result == "output.pdf"
    fake_pyhanko_pkcs11.open_pkcs11_session.assert_called_once_with("driver.dll", slot_no=0, user_pin="1234")
    fake_pyhanko_pkcs11.PKCS11Signer.assert_called_once_with(fake_session, cert_label="MyCert")
    mock_sign.assert_called_once_with(request, fake_signer_instance)
    fake_session.close.assert_called_once()


def test_pkcs11_backend_session_closed_even_on_signing_failure():
    fake_session = MagicMock()
    fake_pyhanko_pkcs11 = types.ModuleType("pyhanko.sign.pkcs11")
    fake_pyhanko_pkcs11.open_pkcs11_session = MagicMock(return_value=fake_session)
    fake_pyhanko_pkcs11.PKCS11Signer = MagicMock(return_value=MagicMock())

    with patch.dict(sys.modules, {"pyhanko.sign.pkcs11": fake_pyhanko_pkcs11}):
        with patch("core.pkcs11_engine.sign_with_pyhanko_signer", side_effect=RuntimeError("token error")):
            backend = Pkcs11SigningBackend(module_path="driver.dll", slot_id=0, pin="1234")
            from core.digital_signature_engine import CertificateSigningRequest

            request = CertificateSigningRequest(source_pdf="a.pdf", output_pdf="b.pdf", pfx_path="", pfx_password="")
            with pytest.raises(ValidationError, match="could not complete"):
                backend.sign(request)

    fake_session.close.assert_called_once()


def test_pkcs11_backend_missing_pyhanko_pkcs11_extra():
    with patch.dict(sys.modules, {"pyhanko.sign.pkcs11": None}):
        backend = Pkcs11SigningBackend(module_path="driver.dll", slot_id=0, pin="1234")
        from core.digital_signature_engine import CertificateSigningRequest

        request = CertificateSigningRequest(source_pdf="a.pdf", output_pdf="b.pdf", pfx_path="", pfx_password="")
        with pytest.raises(ValidationError, match="pkcs11"):
            backend.sign(request)
