"""Domain errors. The API layer maps these to HTTP status codes."""


class NoticeMateError(Exception):
    status_code = 400
    code = "error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(NoticeMateError):
    status_code = 422
    code = "validation_error"


class AuthError(NoticeMateError):
    status_code = 401
    code = "auth_error"


class PermissionDenied(NoticeMateError):
    status_code = 403
    code = "permission_denied"


class NotFound(NoticeMateError):
    status_code = 404
    code = "not_found"


class Conflict(NoticeMateError):
    status_code = 409
    code = "conflict"


class PrivacyBlocked(NoticeMateError):
    """Raised when a transmission is refused because redaction failed or approval is missing."""

    status_code = 451
    code = "privacy_blocked"


class ProviderError(NoticeMateError):
    status_code = 502
    code = "ai_provider_error"


class ExtractionError(NoticeMateError):
    status_code = 422
    code = "extraction_error"
