# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""The dashboard report as a formatted PDF (reportlab, A4 portrait).

Title band, report details, four key-figure cards, status and classification doughnuts, the liability
maturity chart and table, the interest-vs-principal line chart, the 12/24/60-month payments table, the
60-month detail table (header repeated on every page) and notes. Charts are native vector graphics.

Amounts carry the currency CODE ("INR 2,85,62,181.77"), not its symbol: the standard PDF fonts cannot draw
every symbol (for example the rupee sign), a code prints correctly everywhere and is unambiguous.
"""
from io import BytesIO

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.doughnut import Doughnut
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    HRFlowable,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from core.branding import OWNERSHIP
from core.dashboard_report import CLASSIFICATION_HEX, COLORS, STATUS_HEX, file_stem, money_text, number_text
from core.formatting import format_approx

PAGE_W, PAGE_H = A4
MARGIN = 36
CONTENT_W = PAGE_W - 2 * MARGIN


def _c(hex_color: str):
    return colors.HexColor("#" + hex_color)


def _latin1(text) -> str:
    """Text the standard PDF fonts can draw (anything else becomes '?')."""
    return str(text).encode("cp1252", "replace").decode("cp1252")


def _escape(text) -> str:
    return _latin1(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles() -> dict:
    base = dict(fontName="Helvetica", fontSize=9, leading=12, textColor=_c("1A2233"))
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.white),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=10, leading=13, textColor=_c("C9D3EA")),
        "band_right": ParagraphStyle("band_right", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.white, alignment=TA_RIGHT),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=_c(COLORS["navy"]), spaceBefore=10, spaceAfter=2),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=_c(COLORS["navy"]), spaceAfter=2),
        "body": ParagraphStyle("body", **base),
        "muted": ParagraphStyle("muted", **{**base, "fontSize": 8, "leading": 10.5, "textColor": _c(COLORS["muted"])}),
        "note": ParagraphStyle("note", **{**base, "fontSize": 8.5, "leading": 11.5, "spaceAfter": 3}),
        "label": ParagraphStyle("label", **{**base, "fontSize": 8.5, "textColor": _c(COLORS["muted"])}),
        "cell": ParagraphStyle("cell", **{**base, "fontSize": 8.5, "leading": 10.5}),
        "cell_right": ParagraphStyle("cell_right", **{**base, "fontSize": 8.5, "leading": 10.5, "alignment": TA_RIGHT}),
        "th": ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8.5, leading=10.5, textColor=colors.white),
        "th_right": ParagraphStyle("th_right", fontName="Helvetica-Bold", fontSize=8.5, leading=10.5, textColor=colors.white, alignment=TA_RIGHT),
        "kpi_label": ParagraphStyle("kpi_label", **{**base, "fontSize": 9, "fontName": "Helvetica-Bold", "textColor": _c(COLORS["muted"])}),
        "kpi_value": ParagraphStyle("kpi_value", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=_c("1A2233")),
        "kpi_sub": ParagraphStyle("kpi_sub", **{**base, "fontSize": 8.5, "textColor": _c(COLORS["muted"])}),
        "center": ParagraphStyle("center", **{**base, "alignment": TA_CENTER}),
    }


def _section(title: str, st: dict) -> list:
    return [Paragraph(_escape(title), st["h2"]), HRFlowable(width="100%", thickness=1.2, color=_c(COLORS["navy"]), spaceAfter=5)]


def _table(header: list, rows: list, widths: list, st: dict, total: list = None, right_from: int = 1, repeat: bool = True, font: float = 8.5) -> Table:
    """A table with a navy header, zebra rows and an optional bold total row; columns from ``right_from`` are right-aligned."""
    def cell(text, header_row=False, bold=False, index=0):
        style = st["th_right" if index >= right_from else "th"] if header_row else st["cell_right" if index >= right_from else "cell"]
        text = _escape(text)
        return Paragraph("<b>{}</b>".format(text) if bold else text, style)

    data = [[cell(h, True, index=i) for i, h in enumerate(header)]]
    data += [[cell(v, index=i) for i, v in enumerate(row)] for row in rows]
    if total is not None:
        data.append([cell(v, bold=True, index=i) for i, v in enumerate(total)])
    table = Table(data, colWidths=widths, repeatRows=1 if repeat else 0)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _c(COLORS["navy"])),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, _c(COLORS["line"])),
        ("BOX", (0, 0), (-1, -1), 0.6, _c(COLORS["line"])),
    ]
    last_body = len(rows)
    for index in range(1, last_body + 1):
        if index % 2 == 0:
            style.append(("BACKGROUND", (0, index), (-1, index), _c(COLORS["zebra"])))
    if total is not None:
        style += [("BACKGROUND", (0, last_body + 1), (-1, last_body + 1), _c(COLORS["band"])), ("LINEABOVE", (0, last_body + 1), (-1, last_body + 1), 1, _c(COLORS["navy"]))]
    table.setStyle(TableStyle(style))
    return table


# --------------------------------------------------------------------------- #
# charts
# --------------------------------------------------------------------------- #
def _doughnut(items: list, palette: dict, center_label: str, width: float = 250, height: float = 135) -> Drawing:
    """A doughnut with the total in the middle and a legend (colour, label, count, share) beside it."""
    drawing = Drawing(width, height)
    total = sum(item["count"] for item in items)
    if total <= 0:
        drawing.add(String(width / 2, height / 2, "No leases in this currency", fontName="Helvetica-Oblique", fontSize=9, textAnchor="middle", fillColor=_c(COLORS["muted"])))
        return drawing
    chart = Doughnut()
    chart.x, chart.y, chart.width, chart.height = 8, 8, height - 16, height - 16
    chart.data = [[item["count"] for item in items]]
    chart.labels = [""] * len(items)
    chart.innerRadiusFraction = 0.58
    chart.slices.strokeColor, chart.slices.strokeWidth = colors.white, 1.5
    for index in range(len(items)):
        chart.slices[0, index].strokeColor = colors.white
    for index, item in enumerate(items):
        chart.slices[0, index].fillColor = _c(palette.get(item["label"], "9AA5B1"))  # (ring, slice)
    drawing.add(chart)
    centre = 8 + (height - 16) / 2
    drawing.add(String(centre, centre + 1, str(total), fontName="Helvetica-Bold", fontSize=16, textAnchor="middle", fillColor=_c("1A2233")))
    drawing.add(String(centre, centre - 10, center_label, fontName="Helvetica", fontSize=7, textAnchor="middle", fillColor=_c(COLORS["muted"])))
    top = height / 2 + 8 * len(items)
    for index, item in enumerate(items):
        y = top - index * 16
        drawing.add(Rect(height + 2, y - 2, 8, 8, fillColor=_c(palette.get(item["label"], "9AA5B1")), strokeColor=None))
        drawing.add(String(height + 15, y - 1, _latin1("{} - {} ({:.0f}%)".format(item["label"], item["count"], item["percent"])), fontName="Helvetica", fontSize=8, fillColor=_c("1A2233")))
    return drawing


def _nothing_to_show(width: float, height: float, text: str) -> Drawing:
    drawing = Drawing(width, height)
    drawing.add(String(width / 2, height / 2, text, fontName="Helvetica-Oblique", fontSize=9, textAnchor="middle", fillColor=_c(COLORS["muted"])))
    return drawing


def _bars(buckets: list, report: dict, width: float = 270, height: float = 150) -> Drawing:
    values = [bucket["value"] for bucket in buckets]
    if not any(values):
        return _nothing_to_show(width, height, "No payments due in the next 5 years")
    drawing = Drawing(width, height)
    style = report["number_style"]
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 52, 24, width - 62, height - 44
    chart.data = [values]
    chart.categoryAxis.categoryNames = [bucket["label"] for bucket in buckets]
    chart.categoryAxis.labels.fontName, chart.categoryAxis.labels.fontSize = "Helvetica", 8
    top = max(values) if values and max(values) > 0 else 1.0
    chart.valueAxis.valueMin, chart.valueAxis.valueMax = 0, top * 1.22
    chart.valueAxis.labels.fontName, chart.valueAxis.labels.fontSize = "Helvetica", 7
    chart.valueAxis.labelTextFormat = lambda v: format_approx(v, style)
    chart.valueAxis.visibleGrid, chart.valueAxis.gridStrokeColor, chart.valueAxis.gridStrokeWidth = 1, _c(COLORS["line"]), 0.4
    chart.bars[0].fillColor, chart.bars[0].strokeColor = _c(COLORS["blue"]), None
    chart.barLabelFormat = lambda v: format_approx(v, style) if v else ""
    chart.barLabels.nudge, chart.barLabels.fontName, chart.barLabels.fontSize = 7, "Helvetica", 7
    chart.groupSpacing = 10
    drawing.add(chart)
    return drawing


def _lines(report: dict, width: float = CONTENT_W, height: float = 190) -> Drawing:
    monthly = report["monthly"]
    style = report["number_style"]
    interest, principal = [float(v) for v in monthly["interest"]], [float(v) for v in monthly["principal"]]
    if not any(interest + principal):
        return _nothing_to_show(width, height, "No payments fall in the next 60 months")
    drawing = Drawing(width, height)
    chart = HorizontalLineChart()
    chart.x, chart.y, chart.width, chart.height = 58, 30, width - 72, height - 58
    chart.data = [interest, principal]
    chart.categoryAxis.categoryNames = [m.strftime("%b %Y") if index % 6 == 0 else "" for index, m in enumerate(monthly["month"])]  # a label every 6 months
    chart.categoryAxis.labels.fontName, chart.categoryAxis.labels.fontSize = "Helvetica", 7
    chart.categoryAxis.visibleTicks = 0
    low, high = min(0.0, min(interest + principal)), max(interest + principal + [1.0])
    chart.valueAxis.valueMin, chart.valueAxis.valueMax = low * 1.1, high * 1.1
    chart.valueAxis.labels.fontName, chart.valueAxis.labels.fontSize = "Helvetica", 7
    chart.valueAxis.labelTextFormat = lambda v: format_approx(v, style)
    chart.valueAxis.visibleGrid, chart.valueAxis.gridStrokeColor, chart.valueAxis.gridStrokeWidth = 1, _c(COLORS["line"]), 0.4
    for line, hex_color in zip(chart.lines, (COLORS["interest"], COLORS["principal"])):
        line.strokeColor, line.strokeWidth, line.symbol = _c(hex_color), 1.8, None
    chart.joinedLines = 1
    drawing.add(chart)
    x = 58
    for label, hex_color in (("Interest expense", COLORS["interest"]), ("Principal repayment", COLORS["principal"])):
        drawing.add(Line(x, height - 12, x + 18, height - 12, strokeColor=_c(hex_color), strokeWidth=2))
        drawing.add(String(x + 23, height - 15, label, fontName="Helvetica", fontSize=8, fillColor=_c("1A2233")))
        x += 130
    return drawing


# --------------------------------------------------------------------------- #
# page furniture
# --------------------------------------------------------------------------- #
def _numbered_canvas(report: dict):
    class NumberedCanvas(canvas.Canvas):
        """Draws 'Page X of Y' (and the running header) on every page once the total is known."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved = []

        def showPage(self):
            self._saved.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved)
            for index, state in enumerate(self._saved, start=1):
                self.__dict__.update(state)
                self._furniture(index, total)
                super().showPage()
            super().save()

        def _furniture(self, page: int, total: int) -> None:
            self.setStrokeColor(_c(COLORS["line"]))
            self.setLineWidth(0.6)
            self.line(MARGIN, 30, PAGE_W - MARGIN, 30)
            self.setFont("Helvetica", 7.5)
            self.setFillColor(_c(COLORS["muted"]))
            self.drawString(MARGIN, 20, "LeaseIQ Pro - Portfolio Dashboard Report")
            self.drawCentredString(PAGE_W / 2, 9, OWNERSHIP)
            self.drawCentredString(PAGE_W / 2, 20, _latin1("{}  |  {}".format(report["currency"], report["month_label"])))
            self.drawRightString(PAGE_W - MARGIN, 20, "Page {} of {}".format(page, total))
            if page > 1:  # running header
                self.setFont("Helvetica-Bold", 8)
                self.setFillColor(_c(COLORS["navy"]))
                self.drawString(MARGIN, PAGE_H - 24, _latin1("Portfolio Dashboard Report - {} - {}".format(report["month_label"], report["currency_name"])))
                self.setStrokeColor(_c(COLORS["navy"]))
                self.setLineWidth(1)
                self.line(MARGIN, PAGE_H - 28, PAGE_W - MARGIN, PAGE_H - 28)

    return NumberedCanvas


# --------------------------------------------------------------------------- #
# the document
# --------------------------------------------------------------------------- #
def _story(report: dict) -> list:
    st = _styles()
    story = []

    band = Table(
        [[
            [Paragraph("LeaseIQ Pro", st["subtitle"]), Paragraph("Portfolio Dashboard Report", st["title"])],
            [Paragraph(_escape(report["month_label"]), st["band_right"]), Paragraph(_escape(report["currency_name"]), ParagraphStyle("br2", parent=st["subtitle"], alignment=TA_RIGHT))],
        ]],
        colWidths=[CONTENT_W * 0.62, CONTENT_W * 0.38],
    )
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _c(COLORS["navy"])), ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14), ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [band, Spacer(1, 10)]

    # report details: label / value pairs, two per row
    pairs = [
        ("Prepared by", report["prepared_by"] or "-"), ("Generated on", report["generated_at"].strftime("%d-%b-%Y %H:%M")),
        ("Currency", report["currency_name"]), ("Number format", report["number_format_label"]),
        ("Leases included", report["include_label"]), ("Reporting view", report["framework_label"]),
        ("Leases counted", "{} of {} in {}".format(report["leases_counted"], report["total_leases"], report["currency"])), ("", ""),
    ]
    rows = [
        [Paragraph(_escape(a[0]), st["label"]), Paragraph(_escape(a[1]), st["body"]), Paragraph(_escape(b[0]), st["label"]), Paragraph(_escape(b[1]), st["body"])]
        for a, b in zip(pairs[0::2], pairs[1::2])
    ]
    details = Table(rows, colWidths=[78, CONTENT_W / 2 - 78, 78, CONTENT_W / 2 - 78])
    details.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LINEBELOW", (0, 0), (-1, -1), 0.3, _c(COLORS["line"]))]))
    story += _section("Report details", st) + [details]

    # key figures: 2 x 2 cards so long amounts never wrap
    accents = [COLORS["blue"], COLORS["green"], COLORS["purple"], COLORS["orange"]]
    cards = []
    for kpi, accent in zip(report["kpis"], accents):
        value = "{:,}".format(kpi["value"]) if kpi["kind"] == "count" else money_text(kpi["value"], report)
        if kpi["kind"] == "count":
            sub = kpi["note"] or "All statuses"
        elif kpi["change_percent"] is None:
            sub = "No earlier month to compare"
        else:
            sub = "{:+.1f}% vs last month (was {})".format(kpi["change_percent"], money_text(kpi["previous"], report))
        cards.append([Paragraph(_escape(kpi["label"]), st["kpi_label"]), Paragraph(_escape(value), st["kpi_value"]), Paragraph(_escape(sub), st["kpi_sub"])])
    grid = Table([[cards[0], cards[1]], [cards[2], cards[3]]], colWidths=[CONTENT_W / 2 - 4, CONTENT_W / 2 - 4], hAlign="CENTER")
    style = [("BACKGROUND", (0, 0), (-1, -1), colors.white), ("BOX", (0, 0), (0, 0), 0.6, _c(COLORS["line"])), ("BOX", (1, 0), (1, 0), 0.6, _c(COLORS["line"])), ("BOX", (0, 1), (0, 1), 0.6, _c(COLORS["line"])), ("BOX", (1, 1), (1, 1), 0.6, _c(COLORS["line"])), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    for (column, row), accent in zip(((0, 0), (1, 0), (0, 1), (1, 1)), accents):
        style.append(("LINEABOVE", (column, row), (column, row), 3, _c(accent)))
    grid.setStyle(TableStyle(style + [("COLPADDING", (0, 0), (-1, -1), 0)] if False else style))
    story += _section("Key figures - {}".format(report["month_label"]), st) + [grid, Spacer(1, 4)]

    # status and classification side by side
    half = CONTENT_W / 2 - 4
    status_cell = [Paragraph("Leases by Status", st["h3"]), _doughnut(report["status"], STATUS_HEX, "Leases", half)]
    class_cell = [Paragraph("Leases by Classification (ASC 842)", st["h3"]), _doughnut(report["classification"], CLASSIFICATION_HEX, "Classified", half)]
    both = Table([[status_cell, class_cell]], colWidths=[half + 4, half + 4])
    both.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    story += [CondPageBreak(190)] + _section("Portfolio by status and classification", st) + [both]

    # maturity
    maturity_rows = [[b["label"], b["range"], number_text(b["value"], report)] for b in report["maturity"]]
    maturity_table = _table(["Year", "Period", "Payments ({})".format(report["currency"])], maturity_rows, [38, 92, 100], st, ["Total", "", number_text(report["maturity_total"], report)], right_from=2, repeat=False)
    layout = Table([[_bars(report["maturity"], report), maturity_table]], colWidths=[CONTENT_W - 240, 240])
    layout.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [CondPageBreak(190)] + _section("Lease Liability Maturity (Next 5 Years) - undiscounted payments", st) + [layout]

    # interest vs principal
    story += [KeepTogether(_section("Interest vs. Principal - Next 60 Months (Portfolio)", st) + [_lines(report), Paragraph(_escape(report["crossover_text"]), st["muted"])])]

    # future payments
    pay_rows = [[p["label"], number_text(p["total"], report), number_text(p["interest"], report), number_text(p["principal"], report), "{:.1f}%".format(p["interest_share"] * 100), "{:.1f}%".format(p["principal_share"] * 100)] for p in report["payments"]]
    pay_table = _table(["Period", "Total payments", "Interest", "Principal", "Interest share", "Principal share"], pay_rows, [72, 100, 100, 100, 75, 76], st, repeat=False)
    story += [KeepTogether(_section("Future Payments Overview ({})".format(report["currency"]), st) + [pay_table, Spacer(1, 2), Paragraph("Total payments = interest + principal in every period.", st["muted"])])]

    # monthly detail
    monthly = report["monthly"]
    rows = [[m.strftime("%b %Y"), number_text(i, report), number_text(p, report), number_text(c, report)] for m, i, p, c in zip(monthly["month"], monthly["interest"], monthly["principal"], monthly["cash"])]
    totals = report["monthly_totals"]
    detail = _table(["Month", "Interest expense", "Principal repayment", "Total payment"], rows, [90, CONTENT_W / 3 - 30, CONTENT_W / 3 - 30, CONTENT_W / 3 - 30], st, ["Total (60 months)", number_text(totals["interest"], report), number_text(totals["principal"], report), number_text(totals["cash"], report)], font=8)
    story += [CondPageBreak(120)] + _section("Monthly detail - next 60 months ({})".format(report["currency"]), st) + [detail]

    # notes
    notes = [Paragraph("<b>{}.</b>  {}".format(number, _escape(text)), st["note"]) for number, text in enumerate(report["notes"], start=1)]
    story += [CondPageBreak(120)] + _section("Notes and definitions", st) + notes
    return story


def build_pdf(report: dict) -> bytes:
    """The formatted PDF as bytes, ready to be downloaded."""
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN + 6, bottomMargin=MARGIN + 6,
        title=report["title"], author="LeaseIQ Pro", subject=_latin1("{} - {}".format(report["currency_name"], report["month_label"])),
    )
    doc.addPageTemplates([PageTemplate(id="report", frames=[Frame(MARGIN, MARGIN + 6, CONTENT_W, PAGE_H - 2 * MARGIN - 12, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)])])
    doc.build(_story(report), canvasmaker=_numbered_canvas(report))
    return buffer.getvalue()


def pdf_file_name(report: dict) -> str:
    return file_stem(report) + ".pdf"
