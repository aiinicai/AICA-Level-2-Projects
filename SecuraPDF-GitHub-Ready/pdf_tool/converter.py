"""Offline PDF operations and best-effort editable PDF-to-DOCX conversion."""
from __future__ import annotations

import io
import os
import re
from pathlib import Path
import tempfile
from decimal import Decimal, InvalidOperation
from typing import Callable

import pymupdf
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from pypdf import PdfReader, PdfWriter


Progress = Callable[[int, str], None]


def inspect_pdf(path: str | Path) -> dict:
    """Return practical document diagnostics without changing the source."""
    with pymupdf.open(path) as pdf:
        pages = []
        for page in pdf:
            tables = []
            try:
                tables = [(t.row_count, t.col_count) for t in page.find_tables().tables]
            except Exception:
                pass
            pages.append({"size_pt": (round(page.rect.width, 2), round(page.rect.height, 2)),
                          "text_chars": len(page.get_text().strip()),
                          "images": len(page.get_images()), "tables": tables})
        return {"page_count": len(pdf), "pages": pages,
                "selectable_text": any(p["text_chars"] for p in pages)}


def _safe_sheet_name(name: str, existing: set[str]) -> str:
    name = re.sub(r"[\\/*?:\[\]]", "_", name).strip(" '") or "Sheet"
    base = name[:31]
    candidate = base
    suffix = 2
    while candidate.casefold() in {n.casefold() for n in existing}:
        tag = f"_{suffix}"
        candidate = f"{base[:31 - len(tag)]}{tag}"
        suffix += 1
    existing.add(candidate)
    return candidate


def _excel_number(value) -> tuple[Decimal | None, str | None]:
    """Parse a complete numeric cell value and return its Excel display format."""
    text = str(value or "").strip().replace("\u2212", "-").replace("\u2013", "-")
    if not text or re.fullmatch(r"\d{1,4}[./-]\d{1,2}[./-]\d{2,4}", text):
        return None, None  # Keep date-like values as text rather than misreading them as amounts.

    negative_parentheses = text.startswith("(") and text.endswith(")")
    if negative_parentheses:
        text = text[1:-1].strip()
    percent = text.endswith("%")
    if percent:
        text = text[:-1].strip()

    currency_prefix = ""
    for token, excel_literal in (("₹", '"₹" '), ("INR", '"₹" '),
                                 ("Rs.", '"Rs." '), ("Rs", '"Rs." '),
                                 ("$", '"$" '), ("€", '"€" '), ("£", '"£" ')):
        if text.lower().startswith(token.lower()):
            currency_prefix = excel_literal
            text = text[len(token):].strip()
            break
    if not currency_prefix:
        for token, excel_literal in (("₹", '"₹"'), ("INR", '"₹"'),
                                     ("Rs.", '"Rs."'), ("Rs", '"Rs."'),
                                     ("$", '"$"'), ("€", '"€"'), ("£", '"£"')):
            if text.lower().endswith(token.lower()):
                currency_prefix = excel_literal
                text = text[:-len(token)].strip()
                break

    text = text.replace("/-", "").replace(",", "").replace("\u00a0", "").replace(" ", "")
    if negative_parentheses:
        text = "-" + text
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text):
        return None, None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None, None
    if not number.is_finite() or len(number.as_tuple().digits) > 15:
        return None, None  # Excel preserves only 15 significant digits.

    decimal_places = len(text.rsplit(".", 1)[1]) if "." in text else 0
    if percent:
        number /= Decimal(100)
        number_format = "0" + ("." + "0" * decimal_places if decimal_places else "") + "%"
    else:
        integer_part = text.lstrip("+-").split(".", 1)[0]
        if len(integer_part) > 1 and integer_part.startswith("0"):
            number_format = "0" * len(integer_part)
        else:
            number_format = currency_prefix + "#,##0"
        if decimal_places:
            number_format += "." + "0" * decimal_places
        if number < 0:
            number_format += ";[Red]-" + number_format.split(";", 1)[0]
    return number, number_format


def convert_to_xlsx(source: str | Path, output: str | Path,
                    progress: Progress | None = None) -> dict:
    """Extract detected PDF tables and other selectable text to an Excel workbook."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("The Excel output must be a different file from the PDF input.")
    if output.suffix.lower() != ".xlsx":
        raise ValueError("Choose an Excel .xlsx output file.")

    workbook = Workbook()
    workbook.remove(workbook.active)
    used_names: set[str] = set()
    table_count = 0
    text_page_count = 0
    try:
        with pymupdf.open(source) as pdf:
            if pdf.needs_pass:
                raise ValueError("This PDF is password protected.")
            if not len(pdf):
                raise ValueError("The PDF contains no pages.")
            for page_index, page in enumerate(pdf, 1):
                try:
                    found_tables = list(page.find_tables().tables)
                except Exception:
                    found_tables = []
                table_rects = [tuple(table.bbox) for table in found_tables]
                text_rows = []
                for block in page.get_text("dict", sort=True).get("blocks", []):
                    if block.get("type") != 0:
                        continue
                    if any(_intersection_ratio(tuple(block.get("bbox", (0, 0, 0, 0))), rect) > 0.35
                           for rect in table_rects):
                        continue
                    text = "\n".join(
                        "".join(span.get("text", "") for span in line.get("spans", []))
                        for line in block.get("lines", [])
                    ).strip()
                    if text:
                        text_rows.append([text])
                if text_rows:
                    sheet = workbook.create_sheet(_safe_sheet_name(f"Page {page_index} Text", used_names))
                    for row in text_rows:
                        sheet.append(row)
                        sheet.cell(sheet.max_row, 1).alignment = Alignment(wrap_text=True, vertical="top")
                    sheet.column_dimensions["A"].width = 100
                    text_page_count += 1
                for table_index, found_table in enumerate(found_tables, 1):
                    data = found_table.extract() or []
                    if not any(any(_has_visible_table_text(value) for value in (row or [])) for row in data):
                        continue
                    sheet = workbook.create_sheet(
                        _safe_sheet_name(f"P{page_index} Table {table_index}", used_names)
                    )
                    max_columns = max((len(row or []) for row in data), default=0)
                    for row in data:
                        values = list(row or [])
                        values.extend([None] * (max_columns - len(values)))
                        sheet.append(values)
                    for cell in sheet[1]:
                        cell.font = Font(bold=True)
                        cell.fill = PatternFill("solid", fgColor="DCEAF7")
                    for row in sheet.iter_rows():
                        for cell in row:
                            cell.alignment = Alignment(wrap_text=True, vertical="top")
                            number, number_format = _excel_number(cell.value) if cell.value is not None else (None, None)
                            if number is not None:
                                cell.value = number
                                cell.number_format = number_format
                                cell.alignment = Alignment(horizontal="right", wrap_text=True, vertical="top")
                    for column in sheet.columns:
                        letter = column[0].column_letter
                        width = max((len(str(cell.value or "")) for cell in column), default=10)
                        sheet.column_dimensions[letter].width = min(60, max(10, width + 2))
                    sheet.freeze_panes = "A2"
                    if sheet.max_row > 1 and sheet.max_column:
                        sheet.auto_filter.ref = sheet.dimensions
                    table_count += 1
                if progress:
                    progress(int(page_index * 90 / len(pdf)), f"Extracting page {page_index} of {len(pdf)}")
        if not workbook.sheetnames:
            sheet = workbook.create_sheet("PDF content")
            sheet.append(["No selectable text or detectable tables were found. This PDF may be scanned."])
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix=f".{output.stem}_", suffix=".xlsx",
                                         dir=output.parent, delete=False) as temp:
            temp_path = Path(temp.name)
        try:
            workbook.save(temp_path)
            os.replace(temp_path, output)
        finally:
            temp_path.unlink(missing_ok=True)
        return {"tables": table_count, "text_pages": text_page_count, "output": str(output)}
    finally:
        workbook.close()


def compress_pdf(source: str | Path, output: str | Path, *, preset: str = "Medium compress - Moderate quality",
                 progress: Progress | None = None) -> dict:
    """Rewrite a PDF with garbage collection and optional image downsampling."""
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("Choose a different output file so the source PDF is preserved.")
    if output.suffix.lower() != ".pdf":
        raise ValueError("Choose a .pdf output file.")
    options = {
        "High compress - Low quality": (150, 100, 55),
        "Medium compress - Moderate quality": (225, 150, 78),
        "Low compress - High quality": (300, 225, 90),
        # Keep previous function arguments working for existing callers.
        "Lossless": None,
        "Balanced": (225, 150, 78),
        "Smaller file": (150, 100, 55),
    }
    if preset not in options:
        raise ValueError(f"Unknown compression preset: {preset}")
    before = source.stat().st_size
    output.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(source) as pdf:
        if pdf.needs_pass:
            raise ValueError("This PDF is password protected.")
        if not len(pdf):
            raise ValueError("The PDF contains no pages.")
        if progress:
            progress(10, f"Preparing {len(pdf)} page(s)")
        image_options = options[preset]
        if image_options:
            if not hasattr(pdf, "rewrite_images"):
                raise RuntimeError("This PyMuPDF version does not support image compression. Update PyMuPDF and try again.")
            threshold, target, quality = image_options
            pdf.rewrite_images(dpi_threshold=threshold, dpi_target=target, quality=quality)
        if progress:
            progress(75, "Writing compressed PDF")
        with tempfile.NamedTemporaryFile(prefix=f".{output.stem}_", suffix=".pdf",
                                         dir=output.parent, delete=False) as temp:
            temp_path = Path(temp.name)
        try:
            pdf.save(temp_path, garbage=4, clean=1, deflate=1, deflate_images=1,
                     deflate_fonts=1, use_objstms=1, compression_effort=100)
            os.replace(temp_path, output)
        finally:
            temp_path.unlink(missing_ok=True)
        pages = len(pdf)
    after = output.stat().st_size
    return {"pages": pages, "input_bytes": before, "output_bytes": after,
            "saved_bytes": before - after, "output": str(output), "preset": preset}


def _set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), "A6A6A6")


def _set_table_indent(table, points: float) -> None:
    """Place a table at its PDF x-coordinate relative to the Word page margin."""
    tbl_pr = table._tbl.tblPr
    indent = tbl_pr.find(qn("w:tblInd"))
    if indent is None:
        indent = OxmlElement("w:tblInd")
        tbl_pr.append(indent)
    indent.set(qn("w:w"), str(max(0, round(points * 20))))
    indent.set(qn("w:type"), "dxa")


def _set_cell_margins(cell, *, top: int = 35, start: int = 85, bottom: int = 35, end: int = 85) -> None:
    """Set compact, predictable cell padding in twentieths of a point (twips)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = tc_pr.find(qn("w:tcMar"))
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _font_color(rgb: int) -> RGBColor:
    return RGBColor((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255)


def _word_font_name(pdf_name: str) -> str:
    name = pdf_name.split(",")[0]
    name = re.sub(r"^[A-Z]{6}\+", "", name)
    compact = name.lower().replace(" ", "")
    if compact.startswith("timesnewroman"):
        return "Times New Roman"
    if compact.startswith("arial") or compact.startswith("helvetica"):
        return "Arial"
    if compact.startswith("calibri"):
        return "Calibri"
    return name


def _apply_span(run, span: dict, fallback_size: float = 10.0) -> None:
    run.font.name = _word_font_name(span.get("font", "Arial"))
    run.font.size = Pt(max(4, min(72, float(span.get("size", fallback_size)))))
    flags = int(span.get("flags", 0))
    run.bold = bool(flags & 16)
    run.italic = bool(flags & 2)
    run.underline = bool(span.get("underline", False))
    try:
        run.font.color.rgb = _font_color(int(span.get("color", 0)))
    except Exception:
        pass
    # Explicit complex-script font keeps Hindi text editable and Unicode-safe.
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is not None:
        rfonts.set(qn("w:eastAsia"), run.font.name)
        rfonts.set(qn("w:cs"), run.font.name)


def _yellow_highlight_rects(page) -> list[pymupdf.Rect]:
    """Find yellow filled rectangles used as text highlights in the PDF."""
    rects = []
    for drawing in page.get_drawings():
        fill = drawing.get("fill")
        if not fill or len(fill) < 3:
            continue
        red, green, blue = fill[:3]
        if red < 0.85 or green < 0.75 or blue > 0.25:
            continue
        for item in drawing.get("items", []):
            if item[0] == "re":
                rect = pymupdf.Rect(item[1])
                if rect.width > 0 and rect.height > 0:
                    rects.append(rect)
    return rects


def _span_has_yellow_highlight(span: dict, highlight_rects: list[pymupdf.Rect]) -> bool:
    """Return true when a yellow background rectangle substantially covers a span."""
    box = pymupdf.Rect(span.get("bbox", (0, 0, 0, 0)))
    area = box.width * box.height
    if area <= 0:
        return False
    return any(
        (intersection := box & rect).is_valid
        and intersection.width * intersection.height / area >= 0.7
        for rect in highlight_rects
    )


def _table_cell_styles(page, rect) -> list[dict]:
    """Find PDF text spans that lie inside a cell, retaining their source styling."""
    x0, y0, x1, y1 = rect
    matches = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sb = span.get("bbox", (0, 0, 0, 0))
                cx, cy = (sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2
                if x0 - 1 <= cx <= x1 + 1 and y0 - 1 <= cy <= y1 + 1 and span.get("text", "").strip():
                    matches.append(span)
    return matches


def _line_text(line: dict) -> str:
    return " ".join(span.get("text", "") for span in line.get("spans", [])).strip()


def _has_visible_table_text(value) -> bool:
    text = str(value or "")
    text = re.sub(r"[\s\u200b-\u200f\ufeff]", "", text)
    return bool(text)


def _is_short_heading(line: dict) -> bool:
    text = _line_text(line)
    return bool(text and len(text) <= 80 and text == text.upper())


def _split_inline_heading(line: dict) -> list[dict]:
    """Separate an all-caps heading accidentally grouped with sentence text."""
    spans = sorted(line.get("spans", []), key=lambda s: s.get("bbox", (0, 0, 0, 0))[0])
    if len(spans) > 1:
        first = spans[0]
        title = first.get("text", "").strip()
        remainder = " ".join(s.get("text", "") for s in spans[1:]).strip()
        if (title and len(title) <= 48 and title == title.upper()
                and remainder[:1].isupper() and any(ch.islower() for ch in remainder)):
            return [dict(line, spans=[first]), dict(line, spans=spans[1:])]
    if len(spans) == 1:
        text = spans[0].get("text", "")
        match = re.match(r"^([A-Z0-9][A-Z0-9 &/().'-]{2,48})\s+(?=[A-Z][a-z])", text)
        if match:
            title_span = dict(spans[0], text=match.group(1))
            body_span = dict(spans[0], text=text[match.end():])
            return [dict(line, spans=[title_span]), dict(line, spans=[body_span])]
    return [line]


def _paragraph_line_groups(lines: list[dict], page_width: float) -> list[list[dict]]:
    """Join only true wrapped lines; keep captions and short lines on their own rows."""
    expanded = []
    for line in lines:
        expanded.extend(_split_inline_heading(line))
    groups: list[list[dict]] = []
    for line in expanded:
        if not groups:
            groups.append([line])
            continue
        previous = groups[-1][-1]
        previous_bbox = previous.get("bbox", (0, 0, 0, 0))
        bbox = line.get("bbox", (0, 0, 0, 0))
        previous_size = max((float(s.get("size", 10)) for s in previous.get("spans", [])), default=10)
        vertical_gap = bbox[1] - previous_bbox[3]
        previous_text = _line_text(previous)
        current_text = _line_text(line)
        previous_is_heading = _is_short_heading(previous)
        current_is_heading = _is_short_heading(line)
        heading_boundary = previous_is_heading and any(ch.islower() for ch in current_text)
        # Allow a hanging indent on continuation lines while still separating
        # unrelated short caption rows.
        same_left_edge = abs(bbox[0] - groups[-1][0]["bbox"][0]) <= 40
        # Account for PDFs whose text block ends well inside the page edge
        # because of their own right margin (for example at x=526 on a 612 pt
        # page). A fixed 55 pt threshold incorrectly split each justified line.
        reaches_right_edge = previous_bbox[2] >= page_width * 0.85
        is_wrapped_line = reaches_right_edge and same_left_edge and not current_is_heading
        if (heading_boundary or vertical_gap > max(4.5, previous_size * 0.48)
                or not is_wrapped_line):
            groups.append([line])
        else:
            groups[-1].append(line)
    return groups


def _write_positioned_line(paragraph, line: dict, paragraph_start_x: float,
                           *, preserve_wide_gaps: bool = True,
                           highlight_rects: list[pymupdf.Rect] | None = None) -> bool:
    """Write styled spans, preserving wide horizontal PDF gaps with tab stops."""
    spans = sorted(line.get("spans", []), key=lambda s: s.get("bbox", (0, 0, 0, 0))[0])
    previous_right = None
    previous_text = ""
    used_tabs = False
    for span in spans:
        text = span.get("text", "")
        if not text:
            continue
        x0 = float(span.get("bbox", (paragraph_start_x, 0, 0, 0))[0])
        if previous_right is not None:
            gap = x0 - previous_right
            if gap > 18 and preserve_wide_gaps:
                tab_position = max(0, (x0 - paragraph_start_x) / 72)
                if tab_position > 0:
                    paragraph.paragraph_format.tab_stops.add_tab_stop(Inches(tab_position))
                    paragraph.add_run("\t")
                    used_tabs = True
            elif (gap > 1.2 and previous_text and text
                  and not previous_text[-1].isspace() and not text[0].isspace()):
                paragraph.add_run(" ")
        run = paragraph.add_run(text)
        _apply_span(run, span)
        if _span_has_yellow_highlight(span, highlight_rects or []):
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        previous_right = float(span.get("bbox", (x0, 0, x0, 0))[2])
        previous_text = text
    return used_tabs


def _add_table(doc: Document, found_table, page) -> None:
    source_data = found_table.extract() or []
    if not source_data:
        return
    source_cols = max((len(row or []) for row in source_data), default=0)
    if not source_cols:
        return
    source_rows = found_table.rows
    best_row = max(source_rows, key=lambda row: sum(rect is not None for rect in row.cells))
    x_edges = sorted({round(edge, 2) for rect in best_row.cells if rect
                      for edge in (rect[0], rect[2])})
    # Choose a full row's boundaries when the detector's best row has merged cells.
    if len(x_edges) != source_cols + 1:
        x0, _, x1, _ = found_table.bbox
        x_edges = [x0 + (x1 - x0) * i / source_cols for i in range(source_cols + 1)]
    raw_widths = [max(1.0, x_edges[i + 1] - x_edges[i]) for i in range(source_cols)]
    top_nonempty = [str(v or "").strip() for v in source_data[0] if str(v or "").strip()]
    top_rects = source_rows[0].cells
    top_is_merged_caption = (len(top_nonempty) == 1 and
                             (any(rect is None for rect in top_rects) or
                              len([rect for rect in top_rects if rect is not None]) == 1))
    header_row = 1 if top_is_merged_caption and len(source_data) > 1 else 0
    caption_row = 0 if top_is_merged_caption else None

    # PDF table detectors sometimes split a heading row into many short cells,
    # even though most rows show only a few real columns. Keep boundaries that
    # occur in most rows, so those artificial subdivisions fold into the true
    # columns before the Word table is created.
    boundary_counts = [0] * (source_cols + 1)
    for source_row in source_rows:
        rects = source_row.cells
        for edge in range(1, min(source_cols, len(rects))):
            right = rects[edge]
            if right is not None and abs(right[0] - x_edges[edge]) < 2:
                boundary_counts[edge] += 1
    stable_edges = [0] + [
        edge for edge in range(1, source_cols)
        if boundary_counts[edge] > len(source_rows) / 2
    ] + [source_cols]
    all_groups = [list(range(start, end)) for start, end in zip(stable_edges, stable_edges[1:])]
    keep = [gi for gi, group in enumerate(all_groups) if any(
        _has_visible_table_text(row[ci])
        for row in source_data for ci in group if ci < len(row or [])
    )]
    if not keep:
        keep = list(range(len(all_groups)))
    groups = [all_groups[gi] for gi in keep]
    raw_to_group = {}
    for ci in range(source_cols):
        old_group = next(gi for gi, group in enumerate(all_groups) if ci in group)
        target = min(range(len(keep)), key=lambda j: (abs(keep[j] - old_group), keep[j] > old_group))
        raw_to_group[ci] = target
    cols = len(groups)
    rows = []
    multiline_cells = []
    for row in source_data:
        logical = []
        logical_multiline = []
        for group in groups:
            raw_parts = [str(row[ci]) for ci in group if ci < len(row or []) and _has_visible_table_text(row[ci])]
            combined = " ".join(" ".join(part.splitlines()) for part in raw_parts)
            logical.append(" ".join(combined.split()))
            logical_multiline.append(any("\n" in part or "\r" in part for part in raw_parts))
        rows.append(logical)
        multiline_cells.append(logical_multiline)
    widths = [sum(raw_widths[ci] for ci in group) / 72 for group in groups]

    table = doc.add_table(rows=len(rows), cols=cols)
    table.autofit = False
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    _set_table_borders(table)
    _set_table_indent(table, found_table.bbox[0] - 40)
    for ci, width in enumerate(widths):
        table.columns[ci].width = Inches(width)

    # The first row may be a merged caption; otherwise it contains headings.
    row_rect = lambda row_index: next(rect for rect in source_rows[row_index].cells if rect is not None)

    for ri, row in enumerate(rows):
        for ci, value in enumerate(row):
            cell = table.cell(ri, ci)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.width = Inches(widths[ci])
            cell.text = str(value).strip()
            raw_group = groups[ci]
            source_row_rect = row_rect(ri)
            rect = (x_edges[raw_group[0]], source_row_rect[1],
                    x_edges[raw_group[-1] + 1], source_row_rect[3])
            styles = _table_cell_styles(page, rect)
            # A title and column-heading row are semantically bold even when a
            # PDF font subset prevents reliable style extraction.
            bold_fraction = (sum(len(s.get("text", "")) for s in styles if int(s.get("flags", 0)) & 16)
                             / max(1, sum(len(s.get("text", "")) for s in styles)))
            for para in cell.paragraphs:
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.line_spacing = 1.0
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                _set_cell_margins(cell)
                if ri > header_row and len(str(value).strip()) >= 35:
                    # Long narrative cells are usually full-width prose. Word
                    # will justify their reflowed lines without preserving PDF
                    # line-end spaces as separate text.
                    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                if styles:
                    centers = [((s["bbox"][0] + s["bbox"][2]) / 2) for s in styles]
                    if (ri < 2 or not multiline_cells[ri][ci]) and abs(sum(centers) / len(centers) - (rect[0] + rect[2]) / 2) < 12:
                        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in para.runs:
                    representative = max(styles, key=lambda s: len(s.get("text", "")), default={"font": "Times New Roman", "size": 12})
                    run.font.name = _word_font_name(representative.get("font", "Times New Roman"))
                    run.font.size = Pt(float(representative.get("size", 12)))
                    try:
                        run.font.color.rgb = _font_color(int(representative.get("color", 0)))
                    except Exception:
                        pass
                    # Keep semantic table headings bold, but don't promote a
                    # source-styled first data row to bold merely because PDF
                    # span detection overlaps the heading boundary.
                    first_data_row = (ri == header_row + 1 and caption_row is None)
                    run.bold = (ri == header_row or ri == caption_row or
                                (not first_data_row and bold_fraction >= 0.5))
        # Recreate source merges after folding any detector-only sliver columns.
        cell_rects = source_rows[ri].cells
        for rect in cell_rects:
            if rect is None:
                continue
            raw_start = min(range(len(x_edges)), key=lambda i: abs(x_edges[i] - rect[0]))
            raw_end = min(range(len(x_edges)), key=lambda i: abs(x_edges[i] - rect[2])) - 1
            start = raw_to_group[max(0, min(source_cols - 1, raw_start))]
            end_raw = max(raw_start, raw_end)
            end = raw_to_group[max(0, min(source_cols - 1, end_raw))]
            if end > start:
                table.cell(ri, start).merge(table.cell(ri, end))
    # No fixed row height: Word can expand rows to fit the cell content.
    for row in table.rows:
        row.height = None


def _paragraph_alignment(block: dict, page_width: float, left_margin: float = 40.0) -> int:
    x0, _, x1, _ = block["bbox"]
    width = x1 - x0
    content_width = page_width - 2 * left_margin
    lines = block.get("lines", [])
    if width < content_width * 0.78 and abs((x0 + x1) / 2 - page_width / 2) < 10:
        return WD_ALIGN_PARAGRAPH.CENTER
    # Multiline body paragraphs should use Word's full justification. PDF text
    # boxes often report glyph bounds short of the actual line edge, so requiring
    # every line bbox to touch the margins incorrectly classified these as left.
    y_centers = [(line["bbox"][1] + line["bbox"][3]) / 2 for line in lines]
    # PDF extraction reports each line's glyph bounds, which vary even when
    # the source paragraph is justified. Classify a broad multiline text block
    # as a body paragraph without requiring identical line starts.
    forms_paragraph = len(lines) > 1 and max(y_centers) - min(y_centers) > 2
    if forms_paragraph and width >= content_width * 0.55:
        return WD_ALIGN_PARAGRAPH.JUSTIFY
    return WD_ALIGN_PARAGRAPH.LEFT


def convert_to_docx(source: str | Path, output: str | Path, *, mode: str = "editable",
                    page_range: tuple[int, int] | None = None,
                    ocr: bool = False, progress: Progress | None = None) -> dict:
    """Convert pages to a Word document. Page ranges are 1-based inclusive."""
    source, output = Path(source), Path(output)
    report = {"warnings": [], "pages": 0, "tables": 0, "images": 0, "ocr_pages": []}
    with pymupdf.open(source) as pdf:
        if pdf.needs_pass:
            raise ValueError("This PDF is password protected. Unlock it locally and try again.")
        if len(pdf) == 0:
            raise ValueError("The PDF contains no pages.")
        start, end = page_range or (1, len(pdf))
        if start < 1 or end < start or end > len(pdf):
            raise ValueError(f"Page range must be between 1 and {len(pdf)}.")
        pages = list(range(start - 1, end))
        doc = Document()
        section = doc.sections[0]
        first = pdf[pages[0]].rect
        section.page_width = Inches(first.width / 72)
        section.page_height = Inches(first.height / 72)
        section.top_margin = Inches(0.55)
        section.bottom_margin = Inches(0.55)
        section.left_margin = Inches(0.55)
        section.right_margin = Inches(0.55)
        for out_i, page_i in enumerate(pages):
            page = pdf[page_i]
            if out_i:
                section = doc.add_section()
                section.page_width = Inches(page.rect.width / 72)
                section.page_height = Inches(page.rect.height / 72)
                section.top_margin = section.bottom_margin = Inches(0.55)
                section.left_margin = section.right_margin = Inches(0.55)
            if mode == "visual":
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                doc.add_picture(io.BytesIO(pix.tobytes("png")), width=Inches(page.rect.width / 72 - 1.1))
                report["pages"] += 1
                report["images"] += 1
                if progress:
                    progress(int((out_i + 1) * 100 / len(pages)), f"Rendering page {out_i + 1} of {len(pages)}")
                continue

            highlight_rects = _yellow_highlight_rects(page)

            blocks = page.get_text("dict", sort=True)["blocks"]
            searchable_text = page.get_text().strip()
            if not searchable_text and ocr:
                try:
                    tp = page.get_textpage_ocr(language="eng+hin", dpi=200, full=True)
                    blocks = page.get_text("dict", textpage=tp, sort=True)["blocks"]
                    report["ocr_pages"].append(page_i + 1)
                except Exception as exc:
                    report["warnings"].append(f"Page {page_i + 1}: local OCR unavailable ({exc}). Install Tesseract and eng/hin language data.")
            elif not searchable_text:
                report["warnings"].append(f"Page {page_i + 1} appears scanned; text was not OCR'd.")
            try:
                found_tables = list(page.find_tables().tables)
            except Exception:
                found_tables = []
            table_items = [(tuple(t.bbox), t) for t in found_tables]
            items = []
            for bbox, table in table_items:
                items.append((bbox[1], bbox[0], "table", table, bbox))
            for block in blocks:
                bbox = tuple(block.get("bbox", (0, 0, 0, 0)))
                if any(_intersection_ratio(bbox, table_bbox) > 0.35 for table_bbox, _ in table_items):
                    continue
                items.append((bbox[1], bbox[0], "block", block, bbox))
            items.sort(key=lambda x: (x[0], x[1]))
            first_content_y = min((item[0] for item in items), default=40.0)
            # PDF pages often have a large deliberate top offset. Use the first
            # content position as the Word top margin instead of collapsing it
            # into a small paragraph-before value.
            section.top_margin = Inches(max(0.45, first_content_y / 72))
            last_bottom = first_content_y
            for item_index, (_, _, kind, payload, bbox) in enumerate(items):
                if kind == "table":
                    _add_table(doc, payload, page)
                    report["tables"] += 1
                    last_bottom = bbox[3]
                    continue
                block = payload
                if block.get("type") == 1:
                    try:
                        image = block.get("image")
                        if image:
                            width = min(max(0.5, (bbox[2] - bbox[0]) / 72), 6.4)
                            doc.add_picture(io.BytesIO(image), width=Inches(width))
                            report["images"] += 1
                    except Exception as exc:
                        report["warnings"].append(f"Page {page_i + 1}: an image could not be embedded ({exc}).")
                    continue
                lines = block.get("lines", [])
                if not lines:
                    continue
                heading_text = " ".join(
                    span.get("text", "")
                    for line in lines
                    for span in line.get("spans", [])
                ).strip()
                # Short all-caps labels immediately above a detected table
                # are usually table titles (for example, LIST OF DATES AND EVENTS).
                # Center those labels without disturbing ordinary body paragraphs.
                following_table = next(
                    (entry for entry in items[item_index + 1:] if entry[2] == "table"),
                    None,
                )
                is_table_title = (
                    bool(heading_text)
                    and heading_text == heading_text.upper()
                    and len(heading_text) <= 80
                    and following_table is not None
                    and 0 <= following_table[4][1] - bbox[3] <= 36
                )
                paragraph_groups = _paragraph_line_groups(lines, page.rect.width)
                for group_index, line_group in enumerate(paragraph_groups):
                    group_bbox = (
                        min(line["bbox"][0] for line in line_group),
                        min(line["bbox"][1] for line in line_group),
                        max(line["bbox"][2] for line in line_group),
                        max(line["bbox"][3] for line in line_group),
                    )
                    group_block = dict(block, bbox=group_bbox, lines=line_group)
                    group_text = " ".join(_line_text(line) for line in line_group).strip()
                    is_heading = len(line_group) == 1 and _is_short_heading(line_group[0])
                    paragraph = doc.add_paragraph()
                    paragraph.alignment = (WD_ALIGN_PARAGRAPH.CENTER if is_table_title else
                                           _paragraph_alignment(group_block, page.rect.width, left_margin=40))
                    paragraph.paragraph_format.left_indent = Inches(
                        0 if is_table_title or paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER
                        else max(0, group_bbox[0] - 40) / 72
                    )
                    if paragraph.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY:
                        paragraph.paragraph_format.right_indent = Inches(
                            max(0, page.rect.width - 40 - group_bbox[2]) / 72
                        )
                    gap = max(0, group_bbox[1] - last_bottom)
                    if (group_index > 0 and len(paragraph_groups[group_index - 1]) == 1
                            and _is_short_heading(paragraph_groups[group_index - 1][0])):
                        gap = max(gap, 6)
                    paragraph.paragraph_format.space_before = Pt(min(12, gap))
                    paragraph.paragraph_format.space_after = Pt(0)
                    centers = [(line["bbox"][1] + line["bbox"][3]) / 2 for line in line_group]
                    if len(centers) > 1:
                        leading = sorted(centers[i] - centers[i - 1] for i in range(1, len(centers)))
                        font_sizes = [float(span.get("size", 10)) for line in line_group
                                      for span in line.get("spans", [])]
                        min_leading = max(font_sizes, default=10) * 1.05
                        paragraph.paragraph_format.line_spacing = Pt(
                            max(min_leading, min(36, leading[len(leading) // 2]))
                        )
                    paragraph_start_x = max(40.0, group_bbox[0])
                    used_tabs = False
                    for li, line in enumerate(line_group):
                        used_tabs = _write_positioned_line(
                            paragraph, line, paragraph_start_x,
                            preserve_wide_gaps=paragraph.alignment != WD_ALIGN_PARAGRAPH.JUSTIFY,
                            highlight_rects=highlight_rects,
                        ) or used_tabs
                        if li < len(line_group) - 1:
                            paragraph.add_run(" ")
                    if is_table_title and not group_text:
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    last_bottom = max(last_bottom, group_bbox[3])
                last_bottom = max(last_bottom, bbox[3])
            report["pages"] += 1
            if progress:
                progress(int((out_i + 1) * 100 / len(pages)), f"Converting page {out_i + 1} of {len(pages)}")
        if mode == "editable" and not any(p.text.strip() for p in doc.paragraphs) and not report["tables"] and not report["images"]:
            report["warnings"].append("No editable content was extracted.")
        doc.save(output)
    return report


def _intersection_ratio(a, b) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    area = max(1, (a[2] - a[0]) * (a[3] - a[1]))
    return inter / area


def merge_pdfs(inputs: list[str | Path], output: str | Path, progress: Progress | None = None) -> int:
    if len(inputs) < 2:
        raise ValueError("Choose at least two PDF files to merge.")
    writer = PdfWriter()
    try:
        for index, path in enumerate(inputs):
            if progress:
                progress(int(index * 100 / len(inputs)), f"Merging {index + 1} of {len(inputs)} PDFs")
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                raise ValueError(f"Password-protected PDF: {Path(path).name}")
            if not reader.pages:
                raise ValueError(f"PDF contains no pages: {Path(path).name}")
            writer.append(reader)
        with open(output, "wb") as stream:
            writer.write(stream)
        return len(writer.pages)
    finally:
        writer.close()


def split_pdf(source: str | Path, output_dir: str | Path, ranges: list[tuple[int, int]], progress: Progress | None = None) -> list[Path]:
    reader = PdfReader(str(source))
    if reader.is_encrypted:
        raise ValueError("This PDF is password protected.")
    if not reader.pages:
        raise ValueError("The PDF contains no pages.")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base = Path(source).stem
    outputs = []
    total = len(reader.pages)
    try:
        for index, (start, end) in enumerate(ranges, 1):
            if progress:
                progress(int((index - 1) * 100 / len(ranges)), f"Writing part {index} of {len(ranges)}")
            if start < 1 or end < start or end > total:
                raise ValueError(f"Invalid page range {start}-{end}; this PDF has {total} pages.")
            path = output_dir / f"{base}_part{index}_p{start}-{end}.pdf"
            if path.exists():
                raise FileExistsError(f"Output already exists: {path}")
            writer = PdfWriter()
            for p in range(start - 1, end):
                writer.add_page(reader.pages[p])
            with path.open("wb") as stream:
                writer.write(stream)
            outputs.append(path)
    except Exception:
        for path in outputs:
            path.unlink(missing_ok=True)
        raise
    return outputs


def parse_ranges(value: str) -> list[tuple[int, int]]:
    """Parse 1-based comma-separated pages/ranges such as 1-2,4,6-8."""
    result = []
    for piece in value.split(","):
        match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", piece)
        if not match:
            raise ValueError(f"Invalid page range: {piece!r}")
        start = int(match.group(1))
        result.append((start, int(match.group(2) or start)))
    if not result:
        raise ValueError("Enter at least one page or range.")
    return result
