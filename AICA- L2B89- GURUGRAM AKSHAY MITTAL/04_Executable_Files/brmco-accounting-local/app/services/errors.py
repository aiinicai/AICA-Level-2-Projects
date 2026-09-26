"""Errors that carry a message meant for the end user."""
from __future__ import annotations


class UserError(Exception):
    """An ordinary, expected problem (bad input, missing batch...). Shown to the user as-is."""

    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFound(UserError):
    status_code = 404
