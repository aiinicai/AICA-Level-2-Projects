"""Print output contains only the document. Build Prompt v2 §8.8, §18.10.

The prototype had no print CSS and printed the whole application. These
assertions are deliberately about the stylesheet's content: a browser is not
available here, so the honest test is that the rules exist and say what they
must. Gate B confirms it on paper.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CSS = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.css").read_text(
    encoding="utf-8"
)

CHROME_SELECTORS = (".sidebar", ".topbar", ".form-panel", ".findings", ".no-print")


@pytest.fixture(scope="module")
def print_block() -> str:
    """The body of the @media print rule."""
    start = CSS.index("@media print")
    depth = 0
    for i, char in enumerate(CSS[start:], start=start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return CSS[start : i + 1]
    raise AssertionError("unbalanced @media print block")


def test_media_print_block_exists() -> None:
    assert "@media print" in CSS


@pytest.mark.parametrize("selector", CHROME_SELECTORS)
def test_every_chrome_element_is_hidden(print_block: str, selector: str) -> None:
    assert selector in print_block, f"{selector} is not hidden when printing"


def test_chrome_is_hidden_with_display_none(print_block: str) -> None:
    assert re.search(r"display:\s*none", print_block)


def test_document_surface_is_not_hidden(print_block: str) -> None:
    # Hiding the chrome is only half of it; the document must survive.
    surface = re.search(r"\.document-surface\s*\{([^}]*)\}", print_block)
    assert surface is not None
    assert "display: none" not in surface.group(1)
    assert "box-shadow: none" in surface.group(1)


def test_page_is_a4_with_the_specified_margins() -> None:
    page = re.search(r"@page\s*\{([^}]*)\}", CSS)
    assert page is not None
    body = page.group(1)
    assert "size: A4" in body
    assert "25mm 25mm 25mm 30mm" in body


@pytest.mark.parametrize("selector", [".doc-signature", ".doc-table", ".doc-letterhead"])
def test_signature_and_tables_do_not_split_across_pages(print_block: str, selector: str) -> None:
    assert selector in print_block


def test_break_inside_avoid_present(print_block: str) -> None:
    assert "break-inside: avoid" in print_block
    assert "page-break-inside: avoid" in print_block


def test_document_font_matches_docx_output() -> None:
    # §8.5 / §18.9 — preview and DOCX must agree: Times New Roman 10 pt.
    surface = re.search(r"\.document-surface\s*\{([^}]*)\}", CSS)
    assert surface is not None
    assert "Times New Roman" in CSS
    assert "font-size: 10pt" in surface.group(1)


def test_no_external_asset_references() -> None:
    """§1 — air-gapped. A single @import or remote url() breaks that."""
    assert "@import" not in CSS
    remote = re.findall(r"url\(\s*['\"]?(https?:)?//", CSS)
    assert not remote, f"remote asset reference in app.css: {remote}"
