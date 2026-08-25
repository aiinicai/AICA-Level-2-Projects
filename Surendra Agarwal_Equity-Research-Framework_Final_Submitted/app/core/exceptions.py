"""Custom exception hierarchy.

Split into recoverable (application can catch, log, and continue with a
degraded/partial result) and fatal (application must stop) categories,
per the spec's error-handling requirements: never silently replace
missing data with zero, never suppress calculation errors.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application-raised exceptions."""


# --------------------------------------------------------------------------
# Recoverable — caller should catch, log, and produce a DataStatus-flagged
# result rather than crash the whole pipeline.
# --------------------------------------------------------------------------


class RecoverableError(AppError):
    """Base class for errors that should degrade a single result, not the run."""


class MissingDataError(RecoverableError):
    """Raised when a calculation's required input is absent.

    Callers catch this and return a MetricResult with
    status=DataStatus.MISSING_INPUT rather than propagating a crash.
    """


class InsufficientHistoryError(RecoverableError):
    """Raised when there isn't enough historical data for a calculation
    (e.g. requesting a 5-year CAGR with only 2 years of data)."""


class UnitConversionError(RecoverableError):
    """Raised when a unit cannot be safely converted/reconciled."""


class ValidationFailedError(RecoverableError):
    """Raised by validators.py for BLOCKING-severity issues that should
    halt a specific ingestion, without killing the whole application."""


# --------------------------------------------------------------------------
# Fatal — configuration, connectivity, or integrity problems that should
# stop the application rather than produce a possibly-misleading result.
# --------------------------------------------------------------------------


class FatalError(AppError):
    """Base class for errors that should halt execution."""


class ConfigurationError(FatalError):
    """Missing/invalid configuration, e.g. absent API key when AI layer is invoked."""


class DataIntegrityError(FatalError):
    """Raised when ingested data is internally inconsistent in a way that
    makes any downstream calculation unsafe (e.g. balance sheet doesn't
    balance beyond tolerance, and the caller has chosen not to proceed)."""


class DocumentSecurityError(FatalError):
    """Raised when document quarantine (Module 12) detects content severe
    enough that ingestion should be aborted entirely rather than merely
    flagged."""


class PDFParsingError(RecoverableError):
    """Raised when a PDF cannot be opened or a page cannot be read
    (corrupt file, encrypted without password, unsupported format).
    Recoverable because the caller may still want to proceed with
    whatever pages did parse successfully, or fail that one document
    without halting an entire multi-document ingestion run."""


class LLMProviderError(RecoverableError):
    """Raised on LLM API failures (network, rate limit, malformed response).

    Recoverable because the deterministic layers (1-4) must remain usable
    even if the AI layer is unavailable — Layer 5 failure should degrade
    the report (AI sections marked unavailable), not crash the app.
    """
