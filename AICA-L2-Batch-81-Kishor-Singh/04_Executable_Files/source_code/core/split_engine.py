"""PDF split/demerge engine: every page, ranges, extraction, every-N, equal parts, page removal."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz

from core.page_selection import pages_to_ranges, resolve_pages
from core.pdf_engine import open_pdf
from utils.validation import ValidationError, validate_pdf_path


@dataclass
class SplitOutputFile:
    output_path: str
    page_count: int
    source_pages: list[int]  # 1-indexed page numbers from the original


@dataclass
class SplitResult:
    source_path: str
    output_files: list[SplitOutputFile] = field(default_factory=list)

    @property
    def total_output_files(self) -> int:
        return len(self.output_files)


class SplitEngine:
    """All split/demerge strategies. Every method reads the source once and
    writes brand-new output files -- the original is never modified."""

    def __init__(self, source_path: str | Path, password: str | None = None, output_folder: str | Path | None = None):
        self.source_path = validate_pdf_path(source_path)
        self.password = password
        self.output_folder = Path(output_folder) if output_folder else self.source_path.parent
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def _base_name(self) -> str:
        return self.source_path.stem

    def _write_subset(self, doc: fitz.Document, pages_1indexed: list[int], out_path: Path) -> SplitOutputFile:
        new_doc = fitz.open()
        try:
            for start, end in pages_to_ranges(pages_1indexed):
                new_doc.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
            new_doc.save(str(out_path), garbage=3, deflate=True)
        finally:
            new_doc.close()
        return SplitOutputFile(output_path=str(out_path), page_count=len(pages_1indexed), source_pages=pages_1indexed)

    # ---------------------------------------------------------------- strategies
    def split_every_page(self) -> SplitResult:
        with open_pdf(self.source_path, self.password) as doc:
            result = SplitResult(source_path=str(self.source_path))
            width = len(str(doc.page_count))
            for i in range(doc.page_count):
                page_no = i + 1
                out_path = self.output_folder / f"{self._base_name()}_Page_{str(page_no).zfill(max(3, width))}.pdf"
                result.output_files.append(self._write_subset(doc, [page_no], out_path))
            return result

    def split_by_ranges(self, ranges: list[str]) -> SplitResult:
        """``ranges`` e.g. ``["1-5", "6-10", "11-20"]``."""
        if not ranges:
            raise ValidationError("No page ranges specified.")
        with open_pdf(self.source_path, self.password) as doc:
            result = SplitResult(source_path=str(self.source_path))
            for idx, expr in enumerate(ranges, start=1):
                pages = resolve_pages(expr.strip(), doc.page_count)
                out_path = self.output_folder / f"{self._base_name()}_Part_{idx}_{expr.strip().replace(':', '')}.pdf"
                result.output_files.append(self._write_subset(doc, pages, out_path))
            return result

    def extract_pages(self, expression: str) -> SplitResult:
        """Extract a single set of pages (e.g. ``"1,3,7-10"``) into one new PDF."""
        with open_pdf(self.source_path, self.password) as doc:
            pages = resolve_pages(expression, doc.page_count)
            out_path = self.output_folder / f"{self._base_name()}_Extracted.pdf"
            result = SplitResult(source_path=str(self.source_path))
            result.output_files.append(self._write_subset(doc, pages, out_path))
            return result

    def split_every_n_pages(self, n: int) -> SplitResult:
        if n < 1:
            raise ValidationError("N must be at least 1.")
        with open_pdf(self.source_path, self.password) as doc:
            result = SplitResult(source_path=str(self.source_path))
            total = doc.page_count
            part = 1
            for start in range(1, total + 1, n):
                end = min(start + n - 1, total)
                pages = list(range(start, end + 1))
                out_path = self.output_folder / f"{self._base_name()}_Part_{part}.pdf"
                result.output_files.append(self._write_subset(doc, pages, out_path))
                part += 1
            return result

    def split_into_equal_parts(self, num_parts: int) -> SplitResult:
        if num_parts < 1:
            raise ValidationError("Number of parts must be at least 1.")
        with open_pdf(self.source_path, self.password) as doc:
            total = doc.page_count
            if num_parts > total:
                raise ValidationError(f"Cannot split a {total}-page document into {num_parts} parts.")
            base, remainder = divmod(total, num_parts)
            result = SplitResult(source_path=str(self.source_path))
            cursor = 1
            for part in range(1, num_parts + 1):
                size = base + (1 if part <= remainder else 0)
                pages = list(range(cursor, cursor + size))
                cursor += size
                out_path = self.output_folder / f"{self._base_name()}_Part_{part}_of_{num_parts}.pdf"
                result.output_files.append(self._write_subset(doc, pages, out_path))
            return result

    def remove_pages(self, expression: str) -> SplitResult:
        """Remove the given pages and save the remaining pages as a new PDF."""
        with open_pdf(self.source_path, self.password) as doc:
            total = doc.page_count
            to_remove = set(resolve_pages(expression, total))
            remaining = [p for p in range(1, total + 1) if p not in to_remove]
            if not remaining:
                raise ValidationError("Removing these pages would leave an empty document.")
            out_path = self.output_folder / f"{self._base_name()}_PagesRemoved.pdf"
            result = SplitResult(source_path=str(self.source_path))
            result.output_files.append(self._write_subset(doc, remaining, out_path))
            return result
