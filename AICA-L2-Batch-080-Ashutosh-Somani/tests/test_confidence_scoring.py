import pytest
from app.services.confidence_service import ConfidenceService
from app.models.exception import ExceptionRecord
from decimal import Decimal

def test_confidence_perfect():
    score = ConfidenceService.calculate_score([], is_structurally_valid=True, is_balance_verified=True)
    assert score == 100

def test_confidence_missing_prior_but_structurally_valid():
    score = ConfidenceService.calculate_score([], is_structurally_valid=True, is_balance_verified=False)
    assert score == 90

def test_confidence_structural_invalid():
    score = ConfidenceService.calculate_score([], is_structurally_valid=False, is_balance_verified=False)
    assert score == 20

def test_confidence_critical_exception():
    exc = [ExceptionRecord("STATEMENT_CLOSING_MISMATCH", "CRITICAL", "msg")]
    score = ConfidenceService.calculate_score(exc, is_structurally_valid=True, is_balance_verified=True)
    assert score == 20

def test_confidence_error_exception():
    exc = [ExceptionRecord("BALANCE_MISMATCH", "ERROR", "msg")]
    score = ConfidenceService.calculate_score(exc, is_structurally_valid=True, is_balance_verified=False)
    assert score == 40

def test_confidence_warning_exception():
    exc = [ExceptionRecord("NORMALIZATION_WARNING", "WARNING", "msg")]
    score = ConfidenceService.calculate_score(exc, is_structurally_valid=True, is_balance_verified=True)
    assert score == 70
