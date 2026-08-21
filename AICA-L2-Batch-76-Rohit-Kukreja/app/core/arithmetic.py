"""Sub-totals for a fixed schedule. Decision 73.

A schedule's computed row states how it is reached -- "revenue - expenses" --
and that expression is evaluated here.

The same rule as `when` expressions in §3.3: the repository is data, and data
is never executed. `eval` would run anything a clause file asked it to, so the
expression is parsed and walked, and any node not on the list below is refused
at load time rather than at render time.

Addition and subtraction only. A statutory schedule adds its lines up; it does
not multiply them, and admitting division would admit dividing by zero.
"""

from __future__ import annotations

import ast
from decimal import Decimal

_ALLOWED: frozenset[type[ast.AST]] = frozenset(
    {
        ast.Expression,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.UnaryOp,
        ast.USub,
        ast.UAdd,
        ast.Name,
        ast.Load,
        ast.Constant,
    }
)


class ArithmeticExpressionError(ValueError):
    """The expression is not one this evaluator will accept."""


def parse(expression: str, where: str = "") -> ast.Expression:
    """Parse and vet an expression. Raises rather than returning a bad tree."""
    prefix = f"{where}: " if where else ""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ArithmeticExpressionError(f"{prefix}{expression!r} is not an expression") from exc

    for node in ast.walk(tree):
        if type(node) not in _ALLOWED:
            raise ArithmeticExpressionError(
                f"{prefix}{expression!r} uses {type(node).__name__}, which is not allowed here"
            )
        if isinstance(node, ast.Constant) and not isinstance(node.value, int | float):
            raise ArithmeticExpressionError(f"{prefix}{expression!r} has a non-numeric constant")
    return tree


def names(expression: str, where: str = "") -> frozenset[str]:
    """Every row key the expression refers to."""
    return frozenset(
        node.id for node in ast.walk(parse(expression, where)) if isinstance(node, ast.Name)
    )


def evaluate(expression: str, values: dict[str, Decimal | None]) -> Decimal | None:
    """The expression's value, or None when any row it needs is still blank.

    None rather than nought, deliberately. A sub-total shown as 0 reads as a
    figure someone arrived at; blank reads as what it is -- not filled in yet --
    and the export gate can tell the two apart.
    """
    tree = parse(expression)

    def walk(node: ast.AST) -> Decimal | None:
        match node:
            case ast.Expression():
                return walk(node.body)
            case ast.Constant():
                return Decimal(str(node.value))
            case ast.Name():
                return values.get(node.id)
            case ast.UnaryOp(op=ast.USub(), operand=operand):
                inner = walk(operand)
                return None if inner is None else -inner
            case ast.UnaryOp(op=ast.UAdd(), operand=operand):
                return walk(operand)
            case ast.BinOp(left=left, op=op, right=right):
                a, b = walk(left), walk(right)
                if a is None or b is None:
                    return None
                return a + b if isinstance(op, ast.Add) else a - b
        raise ArithmeticExpressionError(f"unexpected node {type(node).__name__}")

    return walk(tree)
