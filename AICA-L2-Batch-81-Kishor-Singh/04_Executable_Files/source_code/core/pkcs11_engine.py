"""Hardware DSC token (PKCS#11) signing.

Many Indian/international Digital Signature Certificate (DSC) USB tokens
(ePass2003, Watchdata ProxKey, mToken, etc.) expose their private key
through a manufacturer-supplied PKCS#11 driver (a native ``.dll`` on
Windows) rather than as an exportable ``.pfx`` file. This module talks to
that driver via ``python-pkcs11`` (slot/token/certificate discovery) and
``pyhanko.sign.pkcs11`` (the actual signing operation, which never
extracts the private key -- it asks the token to sign a digest and gets
the signature back).

**Honesty about what is and isn't verified here:** this code is exercised
by real, thorough unit tests -- but every one of them runs against a
*mocked* PKCS#11 module, not a physical token or even a software token
(SoftHSM2). I did not download and run a third-party PKCS#11 binary as
part of building this; that crosses into "executing an untrusted binary"
territory I won't do autonomously. If you want to verify this against a
real software token, install SoftHSM2 for Windows yourself from
https://github.com/disig/SoftHSM2-for-Windows (a well-known open-source
project used exactly for this) and point ``module_path`` at its
``softhsm2-x64.dll``. Real vendor hardware (ePass2003/ProxKey/etc.) has
its own quirks -- most notably many ship a **32-bit-only** driver DLL,
which will fail to load into this application's 64-bit Python process
with an error like "%1 is not a valid Win32 application"; there is no
software workaround for that beyond obtaining a 64-bit driver from the
vendor or running a 32-bit build of the application.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.digital_signature_engine import CertificateSigningRequest, sign_with_pyhanko_signer
from utils.validation import ValidationError

_32BIT_DLL_HINT = (
    "If this is a genuine PKCS#11 driver file, the most common cause is a "
    "32-bit/64-bit mismatch: many DSC token vendors only ship a 32-bit "
    "driver DLL, which cannot be loaded by this application's 64-bit "
    "Python process. Check with your token vendor for a 64-bit driver, or "
    "run a 32-bit build of this application."
)


@dataclass
class Pkcs11TokenInfo:
    slot_id: int
    label: str
    manufacturer: str
    model: str


@dataclass
class Pkcs11CertificateInfo:
    label: str
    subject: str
    serial_number: str


def _load_library(module_path: str):
    try:
        import pkcs11
    except ImportError as exc:
        raise ValidationError(
            "Hardware token signing requires the 'python-pkcs11' package, which is not installed. "
            "Install it with:\n\n    pip install python-pkcs11\n\nand restart the application."
        ) from exc
    try:
        return pkcs11.lib(module_path)
    except OSError as exc:
        raise ValidationError(
            f"Could not load the PKCS#11 driver at:\n{module_path}\n\n{_32BIT_DLL_HINT}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - surface any other native-library error clearly
        raise ValidationError(f"Could not load the PKCS#11 driver at:\n{module_path}\n\n{exc}") from exc


def list_available_tokens(module_path: str) -> list[Pkcs11TokenInfo]:
    """Enumerate tokens currently present in a reader, via the given driver DLL."""
    lib = _load_library(module_path)
    tokens = []
    try:
        for slot in lib.get_slots(token_present=True):
            token = slot.get_token()
            tokens.append(
                Pkcs11TokenInfo(
                    slot_id=slot.slot_id, label=token.label.strip(),
                    manufacturer=token.manufacturer_id.strip(), model=token.model.strip(),
                )
            )
    finally:
        lib.finalize()
    if not tokens:
        raise ValidationError(
            "No hardware token was detected. Make sure the USB token is plugged in and its "
            "driver is installed, then try again."
        )
    return tokens


def list_certificates_on_token(module_path: str, slot_id: int, pin: str) -> list[Pkcs11CertificateInfo]:
    """List signing-capable certificates stored on a token. Requires the user PIN."""
    import pkcs11
    from pkcs11 import ObjectClass

    lib = _load_library(module_path)
    try:
        slot = next((s for s in lib.get_slots(token_present=True) if s.slot_id == slot_id), None)
        if slot is None:
            raise ValidationError("The selected token is no longer present. Re-insert it and try again.")
        token = slot.get_token()
        try:
            with token.open(user_pin=pin) as session:
                certs = []
                for obj in session.get_objects({pkcs11.Attribute.CLASS: ObjectClass.CERTIFICATE}):
                    label = obj.label or ""
                    subject = bytes(obj[pkcs11.Attribute.SUBJECT]).hex() if pkcs11.Attribute.SUBJECT in obj else ""
                    serial = bytes(obj[pkcs11.Attribute.SERIAL_NUMBER]).hex() if pkcs11.Attribute.SERIAL_NUMBER in obj else ""
                    certs.append(Pkcs11CertificateInfo(label=label, subject=subject, serial_number=serial))
                return certs
        except pkcs11.exceptions.PinIncorrect as exc:
            raise ValidationError("Incorrect PIN for this token.") from exc
        except pkcs11.exceptions.PinLocked as exc:
            raise ValidationError(
                "This token's PIN is locked out after too many incorrect attempts. "
                "Contact your certificate issuer to unlock it."
            ) from exc
    finally:
        lib.finalize()


class Pkcs11SigningBackend:
    """Signs using a certificate/private key stored on a PKCS#11 hardware token.

    The private key never leaves the token -- this backend only sends the
    PIN and a digest to sign; it does not and cannot extract key material.
    The PIN is used only in-memory for the duration of this call.
    """

    def __init__(self, module_path: str, slot_id: int, pin: str, cert_label: str | None = None):
        self.module_path = module_path
        self.slot_id = slot_id
        self.pin = pin
        self.cert_label = cert_label

    def sign(self, request: CertificateSigningRequest) -> str:
        try:
            from pyhanko.sign.pkcs11 import PKCS11Signer, open_pkcs11_session
        except ImportError as exc:
            raise ValidationError(
                "Hardware token signing requires the 'pyHanko' package with its PKCS#11 extra. "
                "Install it with:\n\n    pip install \"pyHanko[pkcs11]\"\n\nand restart the application."
            ) from exc

        try:
            session = open_pkcs11_session(self.module_path, slot_no=self.slot_id, user_pin=self.pin)
        except OSError as exc:
            raise ValidationError(f"Could not load the PKCS#11 driver at:\n{self.module_path}\n\n{_32BIT_DLL_HINT}") from exc
        except Exception as exc:  # noqa: BLE001 - PIN errors, no-token-present, etc. from python-pkcs11
            raise ValidationError(f"Could not open a session with the hardware token: {exc}") from exc

        try:
            signer = PKCS11Signer(session, cert_label=self.cert_label)
            return sign_with_pyhanko_signer(request, signer)
        except Exception as exc:  # noqa: BLE001 - surfaces token signing failures with a clear message
            raise ValidationError(f"The hardware token could not complete the signing operation: {exc}") from exc
        finally:
            session.close()
