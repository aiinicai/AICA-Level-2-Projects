# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""The disclosure report as a Word document (python-docx, A4 landscape).

Draws ``core.reports`` sections generically: a shaded title band, real Heading styles (so Word's navigation pane works),
paragraphs, bullet lists and tables with a shaded header row that repeats across pages, zebra rows and bold totals,
right-aligned numbers, 'Page X of Y' in the footer. Widths are set on the table AND on every cell so the layout holds
in Word and other viewers.
"""
from io import BytesIO

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Pt, RGBColor

from core.branding import OWNERSHIP
from core.dashboard_report import COLORS
from core.reports import cell_text, column_widths, report_file_stem

FONT = "Arial"
PAGE_W_EMU, PAGE_H_EMU = 10692130, 7560310  # A4 landscape (297 x 210 mm)
MARGIN_EMU = 640080  # 0.7 in
CONTENT_EMU = PAGE_W_EMU - 2 * MARGIN_EMU


def _rgb(hex_color: str) -> RGBColor:
    return RGBColor.from_string(hex_color.upper())


def _shade(cell, hex_color: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    for existing in properties.findall(qn("w:shd")):
        properties.remove(existing)
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")  # 'clear', never 'solid' (solid renders black)
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), hex_color)
    properties.append(shading)


def _borders(table, color: str = COLORS["line"]) -> None:
    properties = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement("w:" + edge)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)
        borders.append(element)
    properties.append(borders)


def _repeat_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    element = OxmlElement("w:tblHeader")
    element.set(qn("w:val"), "true")
    properties.append(element)


def _no_split(row) -> None:
    properties = row._tr.get_or_add_trPr()
    properties.append(OxmlElement("w:cantSplit"))


def _field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    for kind, text in (("begin", None), (None, instruction), ("end", None)):
        if kind:
            element = OxmlElement("w:fldChar")
            element.set(qn("w:fldCharType"), kind)
        else:
            element = OxmlElement("w:instrText")
            element.set(qn("xml:space"), "preserve")
            element.text = text
        run._r.append(element)
    run.font.size, run.font.color.rgb, run.font.name = Pt(8), _rgb(COLORS["muted"]), FONT


def _style(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = FONT, Pt(9.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.paragraph_format.space_after = Pt(4)
    for name, size, color in (("Heading 1", 15, COLORS["navy"]), ("Heading 2", 11.5, COLORS["navy"]), ("Heading 3", 10, COLORS["muted"])):
        style = document.styles[name]
        style.font.name, style.font.size, style.font.bold, style.font.color.rgb = FONT, Pt(size), True, _rgb(color)
        style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before, style.paragraph_format.space_after = Pt(12 if name == "Heading 1" else 8), Pt(4)


def _cell_text(cell, text: str, bold=False, color=None, align=None, size=8.5) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    if align is not None:
        paragraph.alignment = align
    run = paragraph.add_run(text)
    run.bold, run.font.size, run.font.name = bold, Pt(size), FONT
    if color:
        run.font.color.rgb = _rgb(color)


def _table(document: Document, block: dict, report: dict) -> None:
    columns, kinds = block["columns"], [kind for _, kind in block["columns"]]
    widths = [int(w) for w in column_widths(block, CONTENT_EMU)]
    if block.get("title"):
        document.add_heading(block["title"], level=2).paragraph_format.keep_with_next = True
    total = [block["total"]] if block.get("total") else []
    table = document.add_table(rows=1 + len(block["rows"]) + len(total), cols=len(columns))
    table.alignment, table.autofit = WD_TABLE_ALIGNMENT.CENTER, False
    table.style = document.styles["Table Grid"]
    _borders(table)
    for index, (header, kind) in enumerate(columns):
        cell = table.rows[0].cells[index]
        _shade(cell, COLORS["navy"])
        _cell_text(cell, header, bold=True, color="FFFFFF", align=WD_ALIGN_PARAGRAPH.RIGHT if kind != "text" else WD_ALIGN_PARAGRAPH.LEFT)
    _repeat_header(table.rows[0])
    for row_index, values in enumerate(block["rows"] + total, start=1):
        is_total = bool(total) and row_index == len(block["rows"]) + 1
        _no_split(table.rows[row_index])
        for index, value in enumerate(values):
            cell = table.rows[row_index].cells[index]
            text = value if isinstance(value, str) else cell_text(value, kinds[index], report)
            _cell_text(cell, text, bold=is_total, align=WD_ALIGN_PARAGRAPH.RIGHT if kinds[index] != "text" else WD_ALIGN_PARAGRAPH.LEFT)
            if is_total:
                _shade(cell, COLORS["band"])
            elif row_index % 2 == 0:
                _shade(cell, COLORS["zebra"])
    for row in table.rows:  # widths on every cell (Word and other viewers honour cell widths, not just the table's)
        for index, cell in enumerate(row.cells):
            cell.width = Emu(widths[index])
    for note in block.get("notes", []):
        paragraph = document.add_paragraph()
        run = paragraph.add_run(note)
        run.italic, run.font.size, run.font.color.rgb = True, Pt(8), _rgb(COLORS["muted"])
    document.add_paragraph().paragraph_format.space_after = Pt(2)


def build_report_docx(report: dict) -> bytes:
    """The disclosure report as .docx bytes."""
    document = Document()
    _style(document)
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = Emu(PAGE_W_EMU), Emu(PAGE_H_EMU)
    section.left_margin = section.right_margin = Emu(MARGIN_EMU)
    section.top_margin, section.bottom_margin = Emu(600000), Emu(600000)

    footer = section.footer.paragraphs[0]
    footer.text = ""
    run = footer.add_run("LeaseIQ Pro - {}   |   {}   |   as at {}      Page ".format(report["title"], report["currency"], report["as_at_label"]))
    run.font.size, run.font.color.rgb, run.font.name = Pt(8), _rgb(COLORS["muted"]), FONT
    _field(footer, "PAGE")
    tail = footer.add_run(" of ")
    tail.font.size, tail.font.color.rgb, tail.font.name = Pt(8), _rgb(COLORS["muted"]), FONT
    _field(footer, "NUMPAGES")
    ownership = section.footer.add_paragraph()
    ownership.alignment = WD_ALIGN_PARAGRAPH.CENTER
    line = ownership.add_run(OWNERSHIP)
    line.font.size, line.font.color.rgb, line.font.name = Pt(8), _rgb(COLORS["muted"]), FONT

    band = document.add_table(rows=1, cols=2)
    band.autofit = False
    left, right = band.rows[0].cells
    for cell, width in ((left, int(CONTENT_EMU * 0.65)), (right, int(CONTENT_EMU * 0.35))):
        _shade(cell, COLORS["navy"])
        cell.width = Emu(width)
    _cell_text(left, "LeaseIQ Pro", color="C9D3EA", size=9)
    for text, size in ((report["title"], 20),):
        run = left.add_paragraph().add_run(text)
        run.bold, run.font.size, run.font.name, run.font.color.rgb = True, Pt(size), FONT, _rgb("FFFFFF")
    _cell_text(right, "as at " + report["as_at_label"], bold=True, color="FFFFFF", align=WD_ALIGN_PARAGRAPH.RIGHT, size=12)
    extra = right.add_paragraph()
    extra.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = extra.add_run(report["currency_name"])
    run.font.size, run.font.name, run.font.color.rgb = Pt(9), FONT, _rgb("C9D3EA")
    document.add_paragraph()

    for section_data in report["sections"]:
        document.add_heading(section_data["title"], level=1)
        for block in section_data["blocks"]:
            kind = block["type"]
            if kind == "text":
                document.add_paragraph(block["text"])
            elif kind == "heading":
                document.add_heading(block["text"], level=3 if block["level"] >= 4 else 2)
            elif kind == "bullets":
                for item in block["items"]:
                    document.add_paragraph(item, style="List Bullet")
            elif kind == "table":
                _table(document, block, report)

    document.core_properties.title = report["title"]
    document.core_properties.author = "LeaseIQ Pro"
    document.core_properties.subject = "{} - as at {}".format(report["currency_name"], report["as_at_label"])
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def report_docx_name(report: dict) -> str:
    return report_file_stem(report) + ".docx"
