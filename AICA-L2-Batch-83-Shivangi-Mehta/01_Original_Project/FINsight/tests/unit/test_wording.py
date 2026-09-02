"""
Stage 8 — app/rules/wording.py + app/rules/base_rule.py's ExceptionDraft
guard (pure functions, no DB/Flask).
Run with: pytest tests/unit/test_wording.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from app.rules import wording
from app.rules.base_rule import ExceptionDraft


def test_assert_non_definitive_allows_clean_text():
    wording.assert_non_definitive("This appears inconsistent with the expected treatment.")  # no raise


@pytest.mark.parametrize("term", wording.FORBIDDEN_TERMS)
def test_assert_non_definitive_rejects_every_forbidden_term(term):
    with pytest.raises(wording.DefinitiveLanguageError):
        wording.assert_non_definitive(f"This is a {term} case.")


def test_assert_non_definitive_is_case_insensitive():
    with pytest.raises(wording.DefinitiveLanguageError):
        wording.assert_non_definitive("This is NON-COMPLIANT with the standard.")


def test_label_line_format():
    assert wording.label_line(wording.REVIEW_REQUIRED, "something odd") == "Review Required: something odd"


def test_label_line_also_rejects_forbidden_language():
    with pytest.raises(wording.DefinitiveLanguageError):
        wording.label_line(wording.REVIEW_REQUIRED, "this is a confirmed violation")


def test_exception_draft_construction_succeeds_with_clean_text():
    draft = ExceptionDraft(
        label=wording.POTENTIAL_EXCEPTION,
        area="Test Area",
        trigger_condition="Variance exceeds tolerance.",
        explanation="The recorded figure differs from the reference expectation.",
        suggested_query="Please explain.",
        risk_level="LOW",
    )
    assert draft.label == wording.POTENTIAL_EXCEPTION


def test_exception_draft_rejects_definitive_explanation():
    with pytest.raises(wording.DefinitiveLanguageError):
        ExceptionDraft(
            label=wording.POTENTIAL_EXCEPTION,
            area="Test Area",
            trigger_condition="ok",
            explanation="This is a confirmed violation of the standard.",
            suggested_query="Please explain.",
            risk_level="LOW",
        )


def test_exception_draft_rejects_definitive_trigger_condition():
    with pytest.raises(wording.DefinitiveLanguageError):
        ExceptionDraft(
            label=wording.POTENTIAL_EXCEPTION,
            area="Test Area",
            trigger_condition="This is non-compliant.",
            explanation="ok",
            suggested_query="Please explain.",
            risk_level="LOW",
        )
