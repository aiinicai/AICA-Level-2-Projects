"""Small encryption boundary for tenant integration credentials."""
import os

from cryptography.fernet import Fernet, InvalidToken


class CredentialVaultError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = os.getenv("TASKCHECKER_CREDENTIAL_KEY", "").strip().encode("ascii")
    if not key:
        raise CredentialVaultError(
            "TASKCHECKER_CREDENTIAL_KEY is missing; generate one with "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key)
    except (ValueError, TypeError) as exc:
        raise CredentialVaultError("TASKCHECKER_CREDENTIAL_KEY is not a valid Fernet key") from exc


def encrypt_secret(value: bytes) -> str:
    return _fernet().encrypt(value).decode("ascii")


def decrypt_secret(value: str) -> bytes:
    try:
        return _fernet().decrypt(value.encode("ascii"))
    except InvalidToken as exc:
        raise CredentialVaultError("Unable to decrypt credential; the encryption key may have changed") from exc
