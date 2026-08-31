"""Restricted evaluator and interpolation. Build Prompt v2 §3.3.

The security property under test: no expression in the clause repository can
reach the interpreter. `eval` and `exec` are forbidden (§1).
"""

from __future__ import annotations

import pytest

from app.clauses.resolve import (
    ExpressionError,
    InterpolationError,
    evaluate,
    interpolate,
    unresolved_tokens,
)


class TestPermittedSyntax:
    @pytest.mark.parametrize(
        ("expression", "context", "expected"),
        [
            ("value == 'none'", {"value": "none"}, True),
            ("value == 'none'", {"value": "disclosed"}, False),
            ("value != 'none'", {"value": "disclosed"}, True),
            ("value in ['a', 'b']", {"value": "b"}, True),
            ("value not in ['a', 'b']", {"value": "c"}, True),
            ("not applicable", {"applicable": False}, True),
            ("a and b", {"a": True, "b": False}, False),
            ("a or b", {"a": True, "b": False}, True),
            ("turnover > 50", {"turnover": 60}, True),
            ("turnover >= 50 and borrowings <= 25", {"turnover": 50, "borrowings": 25}, True),
            ("1 < n < 10", {"n": 5}, True),
            ("1 < n < 10", {"n": 50}, False),
        ],
    )
    def test_evaluates(self, expression: str, context: dict[str, object], expected: bool) -> None:
        assert evaluate(expression, context) is expected


class TestBannedSyntax:
    """Each of these would be a remote code execution path under `eval`."""

    @pytest.mark.parametrize(
        "expression",
        [
            "__import__('os').system('echo pwned')",
            "open('/etc/passwd').read()",
            "value.__class__.__mro__",
            "[x for x in range(10)]",
            "lambda: 1",
            "value if True else False",
            "print('hi')",
            "value + 1",
            "{'a': 1}",
            "value.upper()",
        ],
    )
    def test_rejected(self, expression: str) -> None:
        with pytest.raises(ExpressionError):
            evaluate(expression, {"value": "x"})

    def test_unknown_variable_is_an_error_not_a_falsy_default(self) -> None:
        # Silently treating an unknown name as falsy would let a typo in a
        # `when` expression quietly suppress a statutory clause.
        with pytest.raises(ExpressionError, match="unknown variable"):
            evaluate("valeu == 'none'", {"value": "none"})

    def test_syntax_error(self) -> None:
        with pytest.raises(ExpressionError, match="cannot parse"):
            evaluate("value ==", {"value": "x"})

    def test_length_limit(self) -> None:
        with pytest.raises(ExpressionError, match="too long"):
            evaluate("value == 'x' and " * 100 + "value == 'x'", {"value": "x"})


class TestInterpolation:
    def test_substitutes(self) -> None:
        out = interpolate("Report on {{ company_name }}.", {"company_name": "ABC Limited"})
        assert out == "Report on ABC Limited."

    def test_whitespace_tolerant(self) -> None:
        assert interpolate("{{value}}/{{ value }}", {"value": "x"}) == "x/x"

    def test_missing_variable_raises(self) -> None:
        # §18.4 — an unresolved token must never reach an exported document.
        with pytest.raises(InterpolationError, match="company_name"):
            interpolate("Report on {{ company_name }}.", {})

    def test_none_renders_empty(self) -> None:
        assert interpolate("[{{ udin }}]", {"udin": None}) == "[]"


class TestPlaceholderScan:
    def test_detects_surviving_tokens(self) -> None:
        assert unresolved_tokens("Hello {{ name }}") == ("{{ name }}",)

    def test_detects_bracket_placeholders(self) -> None:
        # The prototype shipped 63 of these with no way to fill them (§4.4).
        found = unresolved_tokens("[State the modified opinion here]")
        assert found == ("[State the modified opinion here]",)

    def test_clean_text_passes(self) -> None:
        assert unresolved_tokens("No dividend has been declared during the year.") == ()
