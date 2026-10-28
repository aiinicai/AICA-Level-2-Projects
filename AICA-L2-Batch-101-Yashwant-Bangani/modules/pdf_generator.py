"""Handwritten-notebook style PDF cue cards (ReportLab) and vector diagrams.

Only latin-1 safe characters are used in PDF text ("Rs." instead of the rupee sign) because
ReportLab's built-in fonts are WinAnsi encoded. Drop a handwriting TTF at
assets/fonts/handwriting.ttf to override the default italic body face.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from reportlab.graphics.shapes import Drawing as _D  # noqa: F401  (re-export friendliness)

from config.icai_resources import CITATION_METADATA, FAIR_USE_NOTICE

if TYPE_CHECKING:  # pragma: no cover
    from modules.revision_engine import Topic

NAVY = colors.HexColor("#0F172A")
SKY = colors.HexColor("#0284C7")
RULE_BLUE = colors.HexColor("#BFDBFE")
MARGIN_RED = colors.HexColor("#FCA5A5")
STICKY_FILL = colors.HexColor("#FEF3C7")
STICKY_BORDER = colors.HexColor("#F59E0B")
SLATE = colors.HexColor("#F8FAFC")

PAGE_W, PAGE_H = A4
LEFT, RIGHT, TOP, BOTTOM = 72.0, 40.0, 78.0, 62.0
LINE_PITCH = 18.0
CONTENT_W = PAGE_W - LEFT - RIGHT

DiagramKind = Literal["ccc", "tradeoff", "flow"]
PdfMode = Literal["blitz", "mastery"]


def _register_body_font() -> tuple[str, str]:
    """Return (body_font, bold_font)."""
    font_path = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "handwriting.ttf"
    if font_path.exists():
        try:
            pdfmetrics.registerFont(TTFont("Handwriting", str(font_path)))
            return "Handwriting", "Handwriting"
        except Exception:  # corrupt font: fall back silently
            pass
    return "Times-Italic", "Times-BoldItalic"


BODY_FONT, BOLD_FONT = _register_body_font()


def esc(text: str) -> str:
    return escape(text)


# ---------------------------------------------------------------------------
# Canvas: faint blue ruled notebook page, margin rule, punch holes, badge, footer
# ---------------------------------------------------------------------------
class NotebookCanvas(Canvas):
    """Canvas that paints the notebook background at the start of every page."""

    def __init__(self, *args: Any, badge: str = "", header: str = "", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._badge = badge
        self._header = header

    def _paint_background(self) -> None:
        self.saveState()
        # ruled lines
        self.setStrokeColor(RULE_BLUE)
        self.setLineWidth(0.5)
        y = PAGE_H - TOP + 4
        while y > BOTTOM - 4:
            self.line(0, y, PAGE_W, y)
            y -= LINE_PITCH
        # margin rules
        self.setStrokeColor(MARGIN_RED)
        self.setLineWidth(0.9)
        self.line(LEFT - 10, 0, LEFT - 10, PAGE_H)
        self.line(LEFT - 13, 0, LEFT - 13, PAGE_H)
        # paper punch holes
        self.setFillColor(colors.HexColor("#E2E8F0"))
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        for frac in (0.2, 0.5, 0.8):
            self.circle(24, PAGE_H * frac, 7, stroke=1, fill=1)
        # header text
        self.setFillColor(NAVY)
        self.setFont("Helvetica-Bold", 8)
        self.drawString(LEFT, PAGE_H - 28, self._header)
        self.setFont("Helvetica", 7)
        self.drawString(LEFT, PAGE_H - 39, "CA Intermediate | Paper 6: Financial Management & Strategic Management")
        # BOS weightage badge (top right)
        bw, bh = 118.0, 46.0
        bx, by = PAGE_W - RIGHT - bw, PAGE_H - 18 - bh
        self.setFillColor(colors.white)
        self.setStrokeColor(SKY)
        self.setLineWidth(2)
        self.roundRect(bx, by, bw, bh, 6, stroke=1, fill=1)
        self.setLineWidth(0.6)
        self.roundRect(bx + 3, by + 3, bw - 6, bh - 6, 4, stroke=1, fill=0)
        self.setFillColor(SKY)
        self.setFont("Helvetica-Bold", 6.5)
        self.drawCentredString(bx + bw / 2, by + bh - 14, "ICAI BOS WEIGHTAGE")
        self.setFillColor(NAVY)
        self.setFont("Helvetica-Bold", 15)
        self.drawCentredString(bx + bw / 2, by + 11, self._badge)
        # footer: fair-use notice + citation line
        self.setFillColor(colors.HexColor("#475569"))
        self.setFont("Helvetica", 5.4)
        lines = simpleSplit(FAIR_USE_NOTICE, "Helvetica", 5.4, PAGE_W - LEFT - RIGHT)
        fy = 36.0
        for ln in lines:
            self.drawString(LEFT, fy, ln)
            fy -= 6.4
        self.drawString(LEFT, 12,
                        f"Source: {CITATION_METADATA['copyright_holder']} | {CITATION_METADATA['canonical_url']} | "
                        f"{CITATION_METADATA['license_nature']}")
        self.drawRightString(PAGE_W - RIGHT, 12, f"Page {self.getPageNumber()}")
        self.restoreState()


def _canvas_factory(badge: str, header: str):
    def make(*args: Any, **kwargs: Any) -> NotebookCanvas:
        return NotebookCanvas(*args, badge=badge, header=header, **kwargs)
    return make


# ---------------------------------------------------------------------------
# Vector diagrams
# ---------------------------------------------------------------------------
def _box(d: Drawing, x: float, y: float, w: float, h: float, text: str,
         fill: Any = colors.white, size: float = 7.5) -> None:
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=NAVY, strokeWidth=1.2))
    lines = text.split("\n")
    ty = y + h / 2 + (len(lines) - 1) * (size + 1) / 2 - size / 3
    for i, ln in enumerate(lines):
        d.add(String(x + w / 2, ty - i * (size + 1.5), ln, fontName="Helvetica-Bold" if i == 0 else "Helvetica",
                     fontSize=size, fillColor=NAVY, textAnchor="middle"))


def _arrow(d: Drawing, x1: float, y1: float, x2: float, y2: float) -> None:
    d.add(Line(x1, y1, x2, y2, strokeColor=SKY, strokeWidth=1.6))
    d.add(Polygon([x2, y2, x2 - 6, y2 + 3.5, x2 - 6, y2 - 3.5], fillColor=SKY, strokeColor=SKY))


def build_diagram(kind: DiagramKind, steps: list[str], width: float = CONTENT_W) -> Drawing:
    if kind == "ccc":
        return _diagram_ccc(width)
    if kind == "tradeoff":
        return _diagram_tradeoff(width)
    return _diagram_flow(steps, width)


def _diagram_ccc(width: float) -> Drawing:
    d = Drawing(width, 128)
    labels = ["Raw material\nstock (RMCP)", "Work-in-process\n(WIPCP)", "Finished goods\n(FGCP)",
              "Debtors\n(DCP)", "Cash\ncollected"]
    n, gap = len(labels), 14.0
    bw = (width - gap * (n - 1)) / n
    fills = [colors.HexColor(c) for c in ("#E0F2FE", "#E0F2FE", "#E0F2FE", "#DCFCE7", "#FEF3C7")]
    for i, lab in enumerate(labels):
        x = i * (bw + gap)
        _box(d, x, 84, bw, 38, lab, fills[i])
        if i < n - 1:
            _arrow(d, x + bw + 1, 103, x + bw + gap - 1, 103)
    end_oc = 4 * bw + 3 * gap
    d.add(Line(0, 70, end_oc, 70, strokeColor=NAVY, strokeWidth=1.2))
    for x in (0, end_oc):
        d.add(Line(x, 66, x, 74, strokeColor=NAVY, strokeWidth=1.2))
    d.add(String(end_oc / 2, 58, "Operating cycle (OC) = RMCP + WIPCP + FGCP + DCP", fontName="Helvetica-Bold",
                 fontSize=8, fillColor=NAVY, textAnchor="middle"))
    start_cp = 1 * (bw + gap) + 8
    d.add(Line(start_cp, 40, end_oc, 40, strokeColor=colors.HexColor("#B91C1C"), strokeWidth=1.2))
    for x in (start_cp, end_oc):
        d.add(Line(x, 36, x, 44, strokeColor=colors.HexColor("#B91C1C"), strokeWidth=1.2))
    d.add(String((start_cp + end_oc) / 2, 28, "Less: Creditors' period (CP)", fontName="Helvetica", fontSize=8,
                 fillColor=colors.HexColor("#B91C1C"), textAnchor="middle"))
    d.add(String(width / 2, 8, "Cash conversion cycle (CCC) = OC - CP   |   Negative CCC (e.g. D-Mart type model) = suppliers fund the business",
                 fontName="Helvetica-Bold", fontSize=7.5, fillColor=SKY, textAnchor="middle"))
    return d


def _diagram_tradeoff(width: float) -> Drawing:
    d = Drawing(width, 128)
    cx = width / 2
    left_x, right_x = 30.0, width - 30.0
    d.add(Polygon([cx, 62, cx - 16, 8, cx + 16, 8], fillColor=colors.HexColor("#E0F2FE"),
                  strokeColor=NAVY, strokeWidth=1.2))
    d.add(Line(left_x, 70, right_x, 54, strokeColor=NAVY, strokeWidth=3))
    _box(d, left_x - 20, 76, 190, 48, "DEBT\nCheaper (Kd), tax shield on interest\nHigher financial risk", colors.HexColor("#DCFCE7"))
    _box(d, right_x - 170, 62, 190, 48, "EQUITY\nCostlier (Ke), no tax shield\nLower financial risk, dilution", colors.HexColor("#FEF3C7"))
    d.add(String(cx + 24, 14, "Balance point: minimise WACC / maximise value", fontName="Helvetica-Bold",
                 fontSize=8, fillColor=SKY, textAnchor="start"))
    return d


def _diagram_flow(steps: list[str], width: float) -> Drawing:
    steps = steps[:5] or ["Start", "End"]
    d = Drawing(width, 70)
    n, gap = len(steps), 16.0
    bw = (width - gap * (n - 1)) / n
    for i, s in enumerate(steps):
        x = i * (bw + gap)
        _box(d, x, 14, bw, 44, s, colors.HexColor("#E0F2FE") if i % 2 == 0 else colors.white, size=7)
        if i < n - 1:
            _arrow(d, x + bw + 1, 36, x + bw + gap - 1, 36)
    return d


# ---------------------------------------------------------------------------
# Flowable builders
# ---------------------------------------------------------------------------
def _styles() -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle("title", fontName=BOLD_FONT, fontSize=19, leading=22, textColor=NAVY,
                                alignment=TA_LEFT, spaceAfter=4),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=SKY,
                            spaceBefore=6, spaceAfter=3),
        "body": ParagraphStyle("body", fontName=BODY_FONT, fontSize=10.5, leading=LINE_PITCH, textColor=NAVY),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=7.8, leading=9.6, textColor=NAVY),
        "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=7.8, leading=9.6, textColor=NAVY),
        "sticky": ParagraphStyle("sticky", fontName=BODY_FONT, fontSize=9.6, leading=11.8, textColor=NAVY),
        "stickyh": ParagraphStyle("stickyh", fontName="Helvetica-Bold", fontSize=8, leading=10,
                                  textColor=colors.HexColor("#92400E")),
    }


def _table(rows: list[list[str]], col_widths: list[float], st: dict[str, ParagraphStyle]) -> Table:
    data: list[list[Paragraph]] = []
    for r_i, row in enumerate(rows):
        style = st["cellb"] if r_i == 0 else st["cell"]
        data.append([Paragraph(esc(c), style) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0F2FE")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.Color(1, 1, 1, alpha=0.88)),
        ("GRID", (0, 0), (-1, -1), 0.5, SKY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _sticky(title: str, items: list[str], st: dict[str, ParagraphStyle]) -> Table:
    inner: list[list[Paragraph]] = [[Paragraph(esc(title), st["stickyh"])]]
    inner += [[Paragraph("&bull; " + esc(i), st["sticky"])] for i in items]
    t = Table(inner, colWidths=[CONTENT_W - 8])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), STICKY_FILL),
        ("BOX", (0, 0), (-1, -1), 1.4, STICKY_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    return t


def build_pdf(topic: "Topic", mode: PdfMode, candidate: str = "Candidate") -> bytes:
    """Render a 1-page ('blitz') or 2-page ('mastery') cue card and return PDF bytes."""
    st = _styles()
    buf = io.BytesIO()
    title_tag = "Exam Morning Blitz (1-Pager)" if mode == "blitz" else "Practical Mastery (2-Pager)"
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=LEFT, rightMargin=RIGHT, topMargin=TOP, bottomMargin=BOTTOM,
        title=f"{topic.title} - {title_tag}", author="Faculty companion (unofficial)",
        subject=f"{CITATION_METADATA['paper']} | Source: {CITATION_METADATA['copyright_holder']}",
        keywords=CITATION_METADATA["canonical_url"],
    )
    story: list[Any] = []
    story.append(Paragraph(esc(topic.title), st["title"]))
    story.append(Paragraph(esc(f"{title_tag} | prepared for CA {candidate}"), st["cell"]))
    story.append(Spacer(1, 4))

    # Formula matrix
    story.append(Paragraph("FORMULA MATRIX", st["h"]))
    story.append(_table([["Concept", "Formula / Rule"]] + [[a, b] for a, b in topic.formulas],
                        [CONTENT_W * 0.30, CONTENT_W * 0.70], st))
    story.append(Spacer(1, 6))

    # Diagram
    story.append(Paragraph("SCHEMATIC", st["h"]))
    story.append(build_diagram(topic.diagram_kind, topic.diagram_steps))
    story.append(Spacer(1, 6))

    # Sticky-note examiner warnings
    limit = 4 if mode == "blitz" else len(topic.traps)
    story.append(KeepTogether([_sticky("EXAMINER WARNINGS - top traps", topic.traps[:limit], st)]))

    if mode == "mastery":
        story.append(PageBreak())
        story.append(Paragraph(esc(f"{topic.title}: working paper"), st["title"]))
        story.append(Paragraph(esc(topic.working_paper_title), st["h"]))
        hdr, *rows = topic.working_paper
        ncols = len(hdr)
        first = CONTENT_W * 0.34 if ncols > 2 else CONTENT_W * 0.4
        rest = (CONTENT_W - first) / (ncols - 1)
        story.append(_table([hdr] + rows, [first] + [rest] * (ncols - 1), st))
        story.append(Spacer(1, 8))
        story.append(Paragraph("PRACTICAL MASTERY STEPS", st["h"]))
        for i, step in enumerate(topic.mastery_steps, 1):
            story.append(Paragraph(f"{i}. {esc(step)}", st["body"]))
        story.append(Spacer(1, 6))
        story.append(_sticky("FACULTY MARGIN NOTE", [topic.faculty_note], st))

    def _paint(canv: Canvas, _doc: Any) -> None:
        if isinstance(canv, NotebookCanvas):
            canv._paint_background()

    doc.build(story, onFirstPage=_paint, onLaterPages=_paint,
              canvasmaker=_canvas_factory(topic.badge, f"{topic.module_name}"))
    return buf.getvalue()
