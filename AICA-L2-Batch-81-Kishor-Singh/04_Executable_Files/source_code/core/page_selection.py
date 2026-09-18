"""Page-selection expression parsing.

This module is the single source of truth for turning a human-friendly page
rule (``"1,3,5-8,last"``, ``"Every 2nd page"``, ``"Last 2 pages"`` ...) into a
concrete, sorted, de-duplicated list of 1-indexed page numbers for a PDF with
a known page count.

Because every PDF in a batch can have a different page count, the resolution
always happens per-document at processing time -- never once for the whole
batch -- so "Last Page" independently means page 7 of a 7-page file and page
42 of a 42-page file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from models.enums import PageSelectionMode
from utils.validation import ValidationError


@dataclass
class PageSelectionRule:
    """A structured, UI-friendly description of which pages to target.

    ``mode`` drives which of the other fields are consulted. ``custom_expression``
    is always available as an escape hatch (mode=CUSTOM) and is also what gets
    persisted for templates, since it is a complete, unambiguous representation.
    """

    mode: PageSelectionMode = PageSelectionMode.LAST_PAGE
    custom_expression: str = ""
    single_page: int = 1
    multiple_pages: str = "1,3,5"
    range_start: int = 1
    range_end: int = 1
    nth: int = 2
    last_n: int = 2

    def to_expression(self) -> str:
        """Collapse the structured rule into the canonical text expression."""
        m = self.mode
        if m == PageSelectionMode.CUSTOM:
            return self.custom_expression.strip() or "all"
        if m == PageSelectionMode.SINGLE_PAGE:
            return str(self.single_page)
        if m == PageSelectionMode.MULTIPLE_PAGES:
            return self.multiple_pages.strip()
        if m == PageSelectionMode.PAGE_RANGE:
            return f"{self.range_start}-{self.range_end}"
        if m == PageSelectionMode.FIRST_PAGE:
            return "first"
        if m == PageSelectionMode.LAST_PAGE:
            return "last"
        if m == PageSelectionMode.FIRST_AND_LAST:
            return "first,last"
        if m == PageSelectionMode.ALL_PAGES:
            return "all"
        if m == PageSelectionMode.ODD_PAGES:
            return "odd"
        if m == PageSelectionMode.EVEN_PAGES:
            return "even"
        if m == PageSelectionMode.EVERY_NTH_PAGE:
            return f"every:{self.nth}"
        if m == PageSelectionMode.LAST_N_PAGES:
            return f"lastn:{self.last_n}"
        raise ValidationError(f"Unknown page selection mode: {m}")

    def resolve(self, total_pages: int) -> list[int]:
        return resolve_pages(self.to_expression(), total_pages)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "custom_expression": self.custom_expression,
            "single_page": self.single_page,
            "multiple_pages": self.multiple_pages,
            "range_start": self.range_start,
            "range_end": self.range_end,
            "nth": self.nth,
            "last_n": self.last_n,
        }

    @staticmethod
    def from_dict(data: dict) -> "PageSelectionRule":
        return PageSelectionRule(
            mode=PageSelectionMode(data.get("mode", PageSelectionMode.LAST_PAGE.value)),
            custom_expression=data.get("custom_expression", ""),
            single_page=int(data.get("single_page", 1)),
            multiple_pages=data.get("multiple_pages", "1,3,5"),
            range_start=int(data.get("range_start", 1)),
            range_end=int(data.get("range_end", 1)),
            nth=int(data.get("nth", 2)),
            last_n=int(data.get("last_n", 2)),
        )

    @staticmethod
    def from_expression(expression: str) -> "PageSelectionRule":
        """Best-effort reconstruction of a structured rule from raw text.

        Used when loading legacy/custom expressions into the UI combo boxes.
        Anything that doesn't cleanly match a known shorthand falls back to
        ``CUSTOM`` with the expression preserved verbatim (lossless).
        """
        expr = expression.strip().lower()
        simple = {
            "first": PageSelectionMode.FIRST_PAGE,
            "last": PageSelectionMode.LAST_PAGE,
            "first,last": PageSelectionMode.FIRST_AND_LAST,
            "all": PageSelectionMode.ALL_PAGES,
            "odd": PageSelectionMode.ODD_PAGES,
            "even": PageSelectionMode.EVEN_PAGES,
        }
        if expr in simple:
            return PageSelectionRule(mode=simple[expr])
        m = re.fullmatch(r"every:(\d+)", expr)
        if m:
            return PageSelectionRule(mode=PageSelectionMode.EVERY_NTH_PAGE, nth=int(m.group(1)))
        m = re.fullmatch(r"lastn:(\d+)", expr)
        if m:
            return PageSelectionRule(mode=PageSelectionMode.LAST_N_PAGES, last_n=int(m.group(1)))
        m = re.fullmatch(r"(\d+)-(\d+)", expr)
        if m:
            return PageSelectionRule(
                mode=PageSelectionMode.PAGE_RANGE,
                range_start=int(m.group(1)),
                range_end=int(m.group(2)),
            )
        m = re.fullmatch(r"\d+", expr)
        if m:
            return PageSelectionRule(mode=PageSelectionMode.SINGLE_PAGE, single_page=int(expr))
        if re.fullmatch(r"[\d,\-\s]+", expr) and "," in expr:
            return PageSelectionRule(mode=PageSelectionMode.MULTIPLE_PAGES, multiple_pages=expression.strip())
        return PageSelectionRule(mode=PageSelectionMode.CUSTOM, custom_expression=expression.strip())


_TOKEN_RE = re.compile(r"^\s*(first|last|odd|even|all|every:\d+|lastn:\d+|\d+\s*-\s*\d+|\d+)\s*$", re.IGNORECASE)


def resolve_pages(expression: str, total_pages: int) -> list[int]:
    """Resolve a page-selection expression against a concrete page count.

    Returns a sorted list of unique, 1-indexed page numbers, all guaranteed to
    be within ``1..total_pages``. Raises :class:`ValidationError` on a
    malformed expression or on a page count <= 0.

    Supported grammar (comma-separated, freely combinable)::

        1                single page
        1,3,5            explicit list
        2-10             inclusive range
        first / last     shorthand for page 1 / page N
        first,last       both
        all              every page
        odd / even       odd / even numbered pages
        every:N          every Nth page (1, 1+N, 1+2N, ...)
        lastn:N          the last N pages
        combinations e.g. "1,3,5-8,last"
    """
    if total_pages <= 0:
        raise ValidationError("Document has no pages.")
    if not expression or not expression.strip():
        raise ValidationError("Page selection expression is empty.")

    expr = expression.strip().lower()
    pages: set[int] = set()

    if expr == "all":
        return list(range(1, total_pages + 1))
    if expr == "odd":
        return [p for p in range(1, total_pages + 1) if p % 2 == 1]
    if expr == "even":
        return [p for p in range(1, total_pages + 1) if p % 2 == 0]

    for raw_token in expr.split(","):
        token = raw_token.strip()
        if not token:
            continue
        if token == "first":
            pages.add(1)
        elif token == "last":
            pages.add(total_pages)
        elif token == "all":
            pages.update(range(1, total_pages + 1))
        elif token == "odd":
            pages.update(p for p in range(1, total_pages + 1) if p % 2 == 1)
        elif token == "even":
            pages.update(p for p in range(1, total_pages + 1) if p % 2 == 0)
        elif token.startswith("every:"):
            n = _parse_positive_int(token.split(":", 1)[1], "every:N")
            pages.update(range(1, total_pages + 1, n))
        elif token.startswith("lastn:"):
            n = _parse_positive_int(token.split(":", 1)[1], "lastn:N")
            start = max(1, total_pages - n + 1)
            pages.update(range(start, total_pages + 1))
        elif "-" in token:
            parts = token.split("-")
            if len(parts) != 2:
                raise ValidationError(f"Invalid page range: '{token}'")
            start_s, end_s = (p.strip() for p in parts)
            start = 1 if start_s == "first" else _parse_positive_int(start_s, "range start")
            end = total_pages if end_s == "last" else _parse_positive_int(end_s, "range end")
            if start > end:
                start, end = end, start
            pages.update(range(start, end + 1))
        else:
            pages.add(_parse_positive_int(token, "page number"))

    out_of_range = [p for p in pages if p < 1 or p > total_pages]
    valid = sorted(p for p in pages if 1 <= p <= total_pages)
    if not valid:
        raise ValidationError(
            f"Page selection '{expression}' does not match any page in a "
            f"{total_pages}-page document."
        )
    # Silently clamp out-of-range page numbers (e.g. "1,3,5,20" on a 10 page
    # doc) rather than failing the whole file -- this is the friendliest
    # behaviour for heterogeneous batches. Reasoning for that is intentional:
    # a rule set once should keep working across documents of varying length.
    del out_of_range
    return valid


def _parse_positive_int(token: str, what: str) -> int:
    token = token.strip()
    if not token.isdigit() or int(token) < 1:
        raise ValidationError(f"Invalid {what}: '{token}'")
    return int(token)


def pages_to_ranges(pages: list[int]) -> list[tuple[int, int]]:
    """Collapse a sorted list of 1-indexed page numbers into contiguous (start, end) runs.

    Used by the merge/split engines to minimise the number of low-level
    ``insert_pdf`` calls while still supporting sparse selections exactly.
    """
    if not pages:
        return []
    ranges: list[tuple[int, int]] = []
    start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
            continue
        ranges.append((start, prev))
        start = prev = p
    ranges.append((start, prev))
    return ranges


def describe_expression(expression: str) -> str:
    """Human-readable summary of an expression, for confirmation dialogs."""
    expr = expression.strip().lower()
    presets = {
        "first": "First Page",
        "last": "Last Page",
        "first,last": "First and Last Page",
        "all": "All Pages",
        "odd": "Odd Pages",
        "even": "Even Pages",
    }
    if expr in presets:
        return presets[expr]
    if expr.startswith("every:"):
        return f"Every {expr.split(':', 1)[1]}(th) Page"
    if expr.startswith("lastn:"):
        return f"Last {expr.split(':', 1)[1]} Pages"
    return f"Custom ({expression})"
