"""No real client or firm identifier may enter the repository.

The precedent documents supplied for authoring are live files — a real
client's management representation letter addressed to a real audit firm.
They are a wording reference only. Names, addresses and engagement details
from them must never reach the clause repository, the seed data, the tests
or the docs.

This test exists because the leak would be easy and silent: authoring a
clause by adapting a precedent is exactly the moment a company name gets
copied along with the sentence.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Identifiers appearing in the supplied precedents. Extend this list whenever
# new precedents arrive.
FORBIDDEN = (
    "SHI Plastic",
    "SHI Plastics Machinery",
    "B S R & Co",
    "BSR & Co",
    "DLF Cyber City",
    "Gurgaon",
)

SEARCHED_SUFFIXES = {".py", ".yaml", ".yml", ".html", ".css", ".js", ".md", ".toml"}
SKIPPED_DIRS = {
    ".venv",
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "data",
    "htmlcov",
}


def _searchable_files() -> list[Path]:
    out: list[Path] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SEARCHED_SUFFIXES:
            continue
        if SKIPPED_DIRS & set(path.parts):
            continue
        out.append(path)
    return out


@pytest.mark.parametrize("needle", FORBIDDEN)
def test_no_precedent_identifier_appears_anywhere(needle: str) -> None:
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    offenders = []
    for path in _searchable_files():
        if path.name == Path(__file__).name:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:  # pragma: no cover - binary asset
            continue
        if pattern.search(text):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert not offenders, (
        f"{needle!r} from a client precedent appears in: {offenders}. "
        "Precedents are a wording reference; identifiers must not be copied."
    )


def test_the_guard_actually_searches_something() -> None:
    """Guards the guard: if the file walk stopped matching, the test above
    would pass vacuously forever."""
    files = _searchable_files()
    assert len(files) > 50
    assert any(f.suffix == ".yaml" for f in files)
    assert any(f.suffix == ".py" for f in files)
