"""Acceptance criterion 2 (§18) — no statutory sentence in any `.py` file.

Protocol §5 names this test specifically: check it is actually running and
not excluded. It is not marked xfail or skipped, and it must not be.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"
RENDER_DIR = APP_DIR / "render"

# Phrases that only ever appear inside statutory or professional prose. A hit
# means document text has leaked out of `content/` and into code, where a
# manager cannot review it and version control cannot diff it meaningfully.
STATUTORY_MARKERS = (
    "according to the information and explanations",
    "in our opinion and to the best of our information",
    "we have audited the accompanying",
    "the management has represented",
    "based on such audit procedures",
    "nothing has come to our notice",
    "true and fair view",
    "reasonable assurance",
    "the company has disclosed",
    "we do not express an opinion",
)

MAX_RENDER_LITERAL = 120


def _python_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _string_constants(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def _docstrings(tree: ast.AST) -> set[int]:
    """Docstring node ids — commentary about the law is not the law."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    ids.add(id(first.value))
    return ids


@pytest.mark.parametrize("path", _python_files(APP_DIR), ids=lambda p: p.name)
def test_no_statutory_prose_in_python(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_ids = _docstrings(tree)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in doc_ids:
            continue
        lowered = node.value.lower()
        for marker in STATUTORY_MARKERS:
            if marker in lowered:
                offenders.append(f"line {node.lineno}: {marker!r}")
    assert not offenders, (
        f"{path.relative_to(PROJECT_ROOT)} contains statutory prose; "
        f"move it to content/ — {offenders}"
    )


@pytest.mark.parametrize("path", _python_files(RENDER_DIR), ids=lambda p: p.name)
def test_renderers_hold_no_document_text(path: Path) -> None:
    """§3.4 — the two renderers must never contain independent copies of
    document text. A long literal in a renderer is how that starts."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_ids = _docstrings(tree)
    long_literals = [
        f"line {node.lineno}: {len(node.value)} chars"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in doc_ids
        and len(node.value) > MAX_RENDER_LITERAL
    ]
    assert not long_literals, (
        f"{path.relative_to(PROJECT_ROOT)} has string literals over "
        f"{MAX_RENDER_LITERAL} chars: {long_literals}"
    )


def test_no_eval_or_exec_anywhere() -> None:
    """§1 forbidden list. The clause repository is authored data; if it could
    reach `eval`, editing a YAML file would be arbitrary code execution."""
    offenders: list[str] = []
    for path in _python_files(APP_DIR):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"eval", "exec", "compile"}
            ):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}")
    assert not offenders, f"eval/exec/compile found: {offenders}"


def test_marker_list_actually_matches_real_prose() -> None:
    """Guards the guard. If the markers stopped matching anything, the test
    above would pass vacuously forever."""
    sample = (
        "According to the information and explanations given to us, "
        "there were no such transactions."
    )
    assert any(m in sample.lower() for m in STATUTORY_MARKERS)
