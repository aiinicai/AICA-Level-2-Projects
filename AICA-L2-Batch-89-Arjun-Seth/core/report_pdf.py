# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""The disclosure report as a formatted PDF (reportlab, A4 landscape).

Draws ``core.reports`` sections generically: title band, one section after another (headings, paragraphs, bullets and
tables with a navy header, zebra rows and bold totals; long tables repeat their header on every page), running header
and 'Page X of Y'. Amounts show in accounting style with the currency stated in the table titles / details; text
uses the standard PDF fonts, so anything they cannot draw degrades to '?' instead of failing.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from core.branding import OWNERSHIP
from core.dashboard_pdf import _c, _escape, _latin1, _section, _styles
from core.dashboard_report import COLORS
from core.reports import cell_text, column_widths, report_file_stem

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 36
CONTENT_W = PAGE_W - 2 * MARGIN


def _numbered_canvas(report: dict):
    class NumberedCanvas(canvas.Canvas):
        """'Page X of Y' and the running header, drawn once the page total is known."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved = []

        def showPage(self):
            self._saved.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved)
            for number, state in enumerate(self._saved, start=1):
                self.__dict__.update(state)
                self._furniture(number, total)
                super().showPage()
            super().save()

        def _furniture(self, page: int, total: int) -> None:
            self.setStrokeColor(_c(COLORS["line"]))
            self.setLineWidth(0.6)
            self.line(MARGIN, 30, PAGE_W - MARGIN, 30)
            self.setFont("Helvetica", 7.5)
            self.setFillColor(_c(COLORS["muted"]))
            self.drawString(MARGIN, 20, "LeaseIQ Pro - {}".format(report["title"]))
            self.drawCentredString(PAGE_W / 2, 9, OWNERSHIP)
            self.drawCentredString(PAGE_W / 2, 20, _latin1("{}  |  as at {}".format(report["currency"], report["as_at_label"])))
            self.drawRightString(PAGE_W - MARGIN, 20, "Page {} of {}".format(page, total))
            if page > 1:
                self.setFont("Helvetica-Bold", 8)
                self.setFillColor(_c(COLORS["navy"]))
                self.drawString(MARGIN, PAGE_H - 24, _latin1("{} - as at {} - {}".format(report["title"], report["as_at_label"], report["currency_name"])))
                self.setStrokeColor(_c(COLORS["navy"]))
                self.setLineWidth(1)
                self.line(MARGIN, PAGE_H - 28, PAGE_W - MARGIN, PAGE_H - 28)

    return NumberedCanvas


def _table_flowable(block: dict, report: dict, st: dict) -> Table:
    columns, kinds = block["columns"], [kind for _, kind in block["columns"]]
    widths = column_widths(block, CONTENT_W)

    def cell(value, index, style_name, bold=False):
        text = _escape(cell_text(value, kinds[index], report)) if not isinstance(value, str) else _escape(value)
        style = st["cell_right" if (kinds[index] != "text" and style_name == "cell") else style_name]
        return Paragraph("<b>{}</b>".format(text) if bold else text, style)

    def head(text, index):
        return Paragraph(_escape(text), st["th_right"] if kinds[index] != "text" else st["th"])

    data = [[head(header, i) for i, (header, _) in enumerate(columns)]]
    data += [[cell(v, i, "cell") for i, v in enumerate(row)] for row in block["rows"]]
    if block.get("total"):
        data.append([cell(v, i, "cell", bold=True) for i, v in enumerate(block["total"])])
    table = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _c(COLORS["navy"])), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, _c(COLORS["line"])), ("BOX", (0, 0), (-1, -1), 0.6, _c(COLORS["line"])),
    ]
    body = len(block["rows"])
    for index in range(2, body + 1, 2):
        style.append(("BACKGROUND", (0, index), (-1, index), _c(COLORS["zebra"])))
    if block.get("total"):
        style += [("BACKGROUND", (0, body + 1), (-1, body + 1), _c(COLORS["band"])), ("LINEABOVE", (0, body + 1), (-1, body + 1), 1, _c(COLORS["navy"]))]
    table.setStyle(TableStyle(style))
    return table


def _blocks(section: dict, report: dict, st: dict) -> list:
    story = []
    bullet_style = ParagraphStyle("bullet", parent=st["note"], leftIndent=12, bulletIndent=2)
    for block in section["blocks"]:
        kind = block["type"]
        if kind == "text":
            story.append(Paragraph(_escape(block["text"]), st["note"]))
        elif kind == "heading":
            story += [CondPageBreak(70), Paragraph(_escape(block["text"]), st["h3"] if block["level"] <= 3 else ParagraphStyle("h4", parent=st["h3"], fontSize=9, textColor=_c(COLORS["muted"])))]
        elif kind == "bullets":
            story += [Paragraph(_escape(item), bullet_style, bulletText="\u2022") for item in block["items"]]
        elif kind == "table":
            parts = []
            if block.get("title"):
                parts.append(Paragraph(_escape(block["title"]), st["h3"]))
            table = _table_flowable(block, report, st)
            if len(block["rows"]) <= 14:
                story.append(KeepTogether(parts + [table] + [Paragraph(_escape(n), st["muted"]) for n in block.get("notes", [])]))
            else:
                story += parts + [table] + [Paragraph(_escape(n), st["muted"]) for n in block.get("notes", [])]
            story.append(Spacer(1, 8))
    return story


def build_report_pdf(report: dict) -> bytes:
    """The disclosure report as PDF bytes."""
    st = _styles()
    story = []
    band = Table(
        [[
            [Paragraph("LeaseIQ Pro", st["subtitle"]), Paragraph(_escape(report["title"]), st["title"])],
            [Paragraph(_escape("as at " + report["as_at_label"]), st["band_right"]), Paragraph(_escape(report["currency_name"]), ParagraphStyle("br2", parent=st["subtitle"], alignment=TA_RIGHT))],
        ]],
        colWidths=[CONTENT_W * 0.65, CONTENT_W * 0.35],
    )
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _c(COLORS["navy"])), ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14), ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [band, Spacer(1, 6)]
    for section in report["sections"]:
        story += [CondPageBreak(110)] + _section(section["title"], st) + _blocks(section, report, st)
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=landscape(A4), leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN + 6, bottomMargin=MARGIN + 6,
                          title=report["title"], author="LeaseIQ Pro", subject=_latin1("{} - as at {}".format(report["currency_name"], report["as_at_label"])))
    doc.addPageTemplates([PageTemplate(id="report", frames=[Frame(MARGIN, MARGIN + 6, CONTENT_W, PAGE_H - 2 * MARGIN - 12, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)])])
    doc.build(story, canvasmaker=_numbered_canvas(report))
    return buffer.getvalue()


def report_pdf_name(report: dict) -> str:
    return report_file_stem(report) + ".pdf"
