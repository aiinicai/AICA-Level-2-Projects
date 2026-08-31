"""Variant selection and interpolation. Build Prompt v2 §3.3.

`when` expressions are evaluated by a restricted AST walker permitting
comparisons, and/or/not, `in`, and named variables only. **Never `eval`,
never `exec`** (§1 forbidden list).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, Final

from app.clauses.model import Clause, ClauseVariant

# --------------------------------------------------------------------------
# Restricted expression evaluator
# --------------------------------------------------------------------------

_ALLOWED_NODES: Final[tuple[type[ast.AST], ...]] = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Tuple,
    ast.List,
)

_MAX_EXPRESSION_LENGTH: Final = 500


class ExpressionError(ValueError):
    """Raised when a `when` expression is malformed or uses banned syntax."""


class UnresolvedClauseError(RuntimeError):
    """No variant matched. A hard error, never a silent skip (§3.3)."""


class InterpolationError(KeyError):
    """A `{{ variable }}` had no value in the render context.

    Hard-failing here is deliberate: the alternative is emitting the raw
    token into a document, and §18.4 forbids an unresolved placeholder ever
    reaching an export.
    """


def _validate(tree: ast.AST, expression: str) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ExpressionError(
                f"disallowed syntax {type(node).__name__!r} in expression: {expression!r}"
            )


def evaluate(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate a restricted boolean expression against `context`."""
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        raise ExpressionError("expression too long")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"cannot parse expression: {expression!r}") from exc
    _validate(tree, expression)
    return bool(_eval_node(tree.body, context, expression))


def _eval_node(node: ast.AST, ctx: dict[str, Any], expr: str) -> Any:
    match node:
        case ast.Constant(value=value):
            return value
        case ast.Name(id=name):
            if name not in ctx:
                raise ExpressionError(f"unknown variable {name!r} in expression: {expr!r}")
            return ctx[name]
        case ast.Tuple(elts=elts) | ast.List(elts=elts):
            return [_eval_node(e, ctx, expr) for e in elts]
        case ast.UnaryOp(op=ast.Not(), operand=operand):
            return not _eval_node(operand, ctx, expr)
        case ast.BoolOp(op=op, values=values):
            results = (_eval_node(v, ctx, expr) for v in values)
            return any(results) if isinstance(op, ast.Or) else all(results)
        case ast.Compare(left=left, ops=ops, comparators=comparators):
            current = _eval_node(left, ctx, expr)
            for operator, comparator in zip(ops, comparators, strict=True):
                right = _eval_node(comparator, ctx, expr)
                if not _compare(operator, current, right):
                    return False
                current = right
            return True
        case _:  # pragma: no cover - _validate rejects everything else first
            raise ExpressionError(f"unsupported node in expression: {expr!r}")


def _compare(operator: ast.cmpop, left: Any, right: Any) -> bool:
    match operator:
        case ast.Eq():
            return bool(left == right)
        case ast.NotEq():
            return bool(left != right)
        case ast.Lt():
            return bool(left < right)
        case ast.LtE():
            return bool(left <= right)
        case ast.Gt():
            return bool(left > right)
        case ast.GtE():
            return bool(left >= right)
        case ast.In():
            return left in right
        case ast.NotIn():
            return left not in right
        case _:  # pragma: no cover
            raise ExpressionError(f"unsupported comparison {type(operator).__name__}")


# --------------------------------------------------------------------------
# Interpolation
# --------------------------------------------------------------------------

_TOKEN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def interpolate(text: str, context: dict[str, Any]) -> str:
    """Replace `{{ name }}` tokens from a context dict built once per render.

    Output is *not* HTML-escaped here — this is document prose, and escaping
    is the renderer's job (§3.4). Never pass user HTML through this.
    """
    missing: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in context:
            missing.append(name)
            return match.group(0)
        value = context[name]
        return "" if value is None else str(value)

    result = _TOKEN.sub(_sub, text)
    if missing:
        raise InterpolationError(
            f"no value for {', '.join(sorted(set(missing)))} in render context"
        )
    return result


def unresolved_tokens(text: str) -> tuple[str, ...]:
    """Any surviving `{{ ... }}` or `[...]` placeholder (§18.4 pre-export scan)."""
    braces = [m.group(0) for m in _TOKEN.finditer(text)]
    brackets = re.findall(r"\[[^\]\n]{2,}\]", text)
    return tuple(braces + brackets)


# --------------------------------------------------------------------------
# Clause resolution
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResolvedClause:
    clause: Clause
    variant: ClauseVariant
    body: str

    @property
    def requires_narrative(self) -> bool:
        return self.variant.requires_narrative

    @property
    def is_exception(self) -> bool:
        return self.variant.severity is not None and self.variant.severity == "exception"


def select_variant(clause: Clause, context: dict[str, Any]) -> ClauseVariant:
    """First variant whose `when` matches; otherwise the unconditional fallback."""
    fallback: ClauseVariant | None = None
    for variant in clause.variants:
        if variant.when is None:
            if fallback is None:
                fallback = variant
            continue
        if evaluate(variant.when, context):
            return variant
    if fallback is not None:
        return fallback
    raise UnresolvedClauseError(
        f"no variant of {clause.id!r} matched; "
        f"value={context.get('value')!r}. Add a matching `when` or a fallback."
    )


def resolve(clause: Clause, context: dict[str, Any]) -> ResolvedClause:
    """Select the variant and interpolate its body."""
    variant = select_variant(clause, context)
    return ResolvedClause(
        clause=clause,
        variant=variant,
        body=interpolate(variant.body, context).strip(),
    )
