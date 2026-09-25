"""Typed user-safe errors.

Exception messages in this module may be shown to an end user. Detailed causes are
logged separately and are never rendered into HTML in production.
"""


class IBCExpertError(Exception):
    """Base application error with a safe display message."""


class ValidationError(IBCExpertError):
    """User supplied data failed validation."""


class AuthenticationError(IBCExpertError):
    """Authentication failed without disclosing which check failed."""


class AccountLockedError(AuthenticationError):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        super().__init__(
            f"Too many unsuccessful attempts. Try again in {self.retry_after_seconds} seconds."
        )


class IntegrityError(IBCExpertError):
    """Authenticated data, backup, audit chain, or licence was altered."""


class LicenceError(IBCExpertError):
    """Licence or trial state is invalid or unavailable."""


class LicenceRestrictedError(LicenceError):
    """Requested operation is unavailable under the current entitlement."""


class ClockRollbackError(LicenceError):
    """The local wall clock moved materially behind trusted state."""


class StorageError(IBCExpertError):
    """Persistent storage operation failed."""


class DocumentError(IBCExpertError):
    """Document validation, extraction, OCR, or vault operation failed."""


class UnsafeArchiveError(DocumentError):
    """ZIP safety limits or path containment checks failed."""


class BackupError(IBCExpertError):
    """Backup could not be created, validated, or restored."""


class ConfigurationError(IBCExpertError):
    """Required secure configuration is unavailable."""
