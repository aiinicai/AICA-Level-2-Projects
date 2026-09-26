"""
pdf_export.py
--------------
Close-binder-ready PDF, restyled to Big 4 review-package standard:

  1. Cover page — title, watermark, run parameters, legal notice.
  2. Contents page.
  3. Executive Summary — KPI tiles, the variance bridge (waterfall)
     chart and a severity-distribution chart.
  4. Entity Summary table.
  5. One "card" per material line, per entity — the fact pattern
     (prior/current/variance/severity/status) followed by the
     AI-Generated Commentary (reference only, grey/italic) and the
     Controller Final Commentary (the authoritative text) clearly
     labelled and visually distinct.
  6. Controller Sign-Off block.

Every page carries a running footer (legal notice + page number) via a
small custom canvas.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image, KeepTogether, HRFlowable,
)

from ..legal import PROJECT_NOTICE, SHORT_NOTICE, DRAFT_WATERMARK, FINAL_WATERMARK
from . import charts

NAVY = colors.HexColor("#14213D")
NAVY_LIGHT = colors.HexColor("#1F335A")
GOLD = colors.HexColor("#C9A227")
GREY = colors.HexColor("#5A6472")
LGREY = colors.HexColor("#F6F7F9")
GREEN = colors.HexColor("#1E7A46")
RED = colors.HexColor("#B00020")
WARN_BG = colors.HexColor("#FFF7E0")


def _readiness(run):
    rows = list(run["rows"].values())
    material_rows = [r for r in rows if r["data"]["is_material"]]
    approved = [r for r in material_rows if r["status"] == "approved"]
    signed = run["signoff"]["controller_name"] is not None
    ready = signed and len(material_rows) > 0 and len(approved) == len(material_rows)
    return ready, len(material_rows), len(approved)


class _FooterCanvas(pdfcanvas.Canvas):
    """Adds a page-numbered footer + tiny watermark chip to every page."""

    def __init__(self, *args, watermark="", watermark_color=GREY, **kwargs):
        super().__init__(*args, **kwargs)
        self._watermark = watermark
        self._watermark_color = watermark_color
        self._saved_states = []

    def showPage(self):
        self._draw_footer()
        super().showPage()

    def save(self):
        self._draw_footer()
        super().save()

    def _draw_footer(self):
        self.saveState()
        self.setFont("Helvetica", 7)
        self.setFillColor(GREY)
        self.drawString(1.6*cm, 1.1*cm, SHORT_NOTICE)
        self.setFillColor(self._watermark_color)
        self.setFont("Helvetica-Bold", 7)
        self.drawRightString(A4[0] - 1.6*cm, 1.1*cm, self._watermark)
        self.setFillColor(GREY)
        self.setFont("Helvetica", 7)
        self.drawCentredString(A4[0] / 2, 1.1*cm, f"Page {self.getPageNumber()}")
        self.restoreState()


def build_pdf(run: dict) -> bytes:
    meta = run["meta"]
    rows = list(run["rows"].values())
    ready, n_material, n_approved = _readiness(run)
    watermark = FINAL_WATERMARK if ready else DRAFT_WATERMARK
    watermark_color = GREEN if ready else RED

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=1.6*cm, bottomMargin=1.8*cm, leftMargin=1.8*cm, rightMargin=1.8*cm,
        title=f"{meta.get('statement_label','')} Flux Analysis",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CoverTitle", parent=styles["Title"], fontSize=24, textColor=NAVY, spaceAfter=6)
    subtitle_style = ParagraphStyle("CoverSub", parent=styles["Normal"], fontSize=13, textColor=GREY, spaceAfter=4, alignment=1)
    wm_style = ParagraphStyle("Watermark", parent=styles["Normal"], fontSize=14, textColor=watermark_color, alignment=1, spaceBefore=14, spaceAfter=14)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=10, textColor=NAVY, alignment=1, spaceAfter=2)
    legal_style = ParagraphStyle("Legal", parent=styles["Normal"], fontSize=8, textColor=GREY, alignment=1, leading=11)
    section_style = ParagraphStyle("Section", parent=styles["Heading1"], fontSize=15, textColor=NAVY, spaceBefore=4, spaceAfter=10)
    subsection_style = ParagraphStyle("Subsection", parent=styles["Heading2"], fontSize=12, textColor=NAVY, spaceBefore=6, spaceAfter=8)
    toc_style = ParagraphStyle("Toc", parent=styles["Normal"], fontSize=11.5, textColor=NAVY, spaceAfter=10, leftIndent=6)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9, leading=12.5)
    body_b = ParagraphStyle("BodyB", parent=body, fontName="Helvetica-Bold")
    line_title = ParagraphStyle("LineTitle", parent=styles["Heading3"], fontSize=10.5, textColor=NAVY, spaceBefore=0, spaceAfter=4)
    label_ai = ParagraphStyle("LabelAI", parent=body, fontSize=7.5, textColor=GREY, fontName="Helvetica-BoldOblique", spaceAfter=2)
    text_ai = ParagraphStyle("TextAI", parent=body, fontSize=8.5, textColor=GREY, fontName="Helvetica-Oblique", leading=11.5)
    label_ctrl = ParagraphStyle("LabelCtrl", parent=body, fontSize=7.5, textColor=colors.HexColor("#8A6400"), fontName="Helvetica-Bold", spaceAfter=2)
    text_ctrl = ParagraphStyle("TextCtrl", parent=body, fontSize=8.5, textColor=NAVY, leading=11.5)

    elements = []

    # ---------------- Cover page ----------------
    elements.append(Spacer(1, 3.2*cm))
    elements.append(Paragraph("Financial Statement Flux Analyzer", title_style))
    elements.append(Paragraph(f"{meta.get('statement_label','')} Flux Analysis", subtitle_style))
    elements.append(Paragraph(meta.get("comparison_label", ""), subtitle_style))
    elements.append(Paragraph(watermark, wm_style))
    elements.append(Spacer(1, 0.6*cm))
    elements.append(Paragraph(f"Materiality threshold: {meta.get('threshold_pct','')}% (min. $1,000 floor)", meta_style))
    elements.append(Paragraph(f"Prepared: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", meta_style))
    elements.append(Paragraph("AICA Level 2 Capstone — Batch 89 · CA Shrey Chopra", meta_style))
    elements.append(Spacer(1, 2.2*cm))
    elements.append(HRFlowable(width="60%", thickness=0.6, color=colors.HexColor("#D6DBE2"), hAlign="CENTER"))
    elements.append(Spacer(1, 0.4*cm))
    elements.append(Paragraph(PROJECT_NOTICE, legal_style))
    elements.append(PageBreak())

    # ---------------- Contents ----------------
    entities = sorted(set(r["data"]["entity"] for r in rows))
    elements.append(Paragraph("Contents", section_style))
    toc_items = ["1.  Executive Summary", "2.  Entity Summary"]
    for i, e in enumerate(entities, start=3):
        toc_items.append(f"{i}.  Material Flux — {e}")
    toc_items.append(f"{len(entities)+3}.  Controller Sign-Off")
    for item in toc_items:
        elements.append(Paragraph(item, toc_style))
    elements.append(PageBreak())

    # ---------------- Executive summary ----------------
    elements.append(Paragraph("1.  Executive Summary", section_style))

    material = [r for r in rows if r["data"]["is_material"]]
    net_variance = sum(r["data"]["variance_usd"] for r in rows)
    kpis = [
        ("Entities", str(len(entities))),
        ("Lines Reviewed", str(len(rows))),
        ("Flagged Material", str(len(material))),
        ("Controller-Approved", f"{n_approved} / {n_material}"),
        ("Net Variance", f"${net_variance:,.0f}"),
    ]
    kpi_table = Table([[Paragraph(f"<b><font size=15 color='#14213D'>{v}</font></b>", body) for _, v in kpis],
                        [Paragraph(f"<font size=7.5 color='#5A6472'>{k}</font>", body) for k, _ in kpis]],
                       colWidths=[3.4*cm]*5)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LGREY),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
    ]))
    elements += [kpi_table, Spacer(1, 0.5*cm)]

    material_dicts = [r["data"] for r in rows]
    deltas, prior_total, current_total = charts.entity_totals(material_dicts)
    wf_png = charts.waterfall_chart(deltas, prior_total, current_total,
                                     title=f"Net Variance Bridge — {meta.get('statement_label','')}")
    sev_png = charts.severity_bar_chart(charts.severity_counts(material_dicts))

    wf_img = Image(io.BytesIO(wf_png), width=17*cm, height=8.2*cm)
    elements += [wf_img, Spacer(1, 0.4*cm)]
    sev_img = Image(io.BytesIO(sev_png), width=13*cm, height=9.5*cm)
    elements += [sev_img, PageBreak()]

    # ---------------- Entity summary ----------------
    elements.append(Paragraph("2.  Entity Summary", section_style))
    by_entity = {}
    for r in rows:
        d = r["data"]
        e = d["entity"]
        by_entity.setdefault(e, {"lines": 0, "material": 0, "approved": 0, "net": 0.0})
        by_entity[e]["lines"] += 1
        if d["is_material"]:
            by_entity[e]["material"] += 1
            if r["status"] == "approved":
                by_entity[e]["approved"] += 1
        by_entity[e]["net"] += d["variance_usd"]

    summary_data = [["Entity", "Lines Reviewed", "Material Flags", "Controller-Approved", "Net Variance ($)"]]
    for e, v in by_entity.items():
        summary_data.append([e, str(v["lines"]), str(v["material"]), f"{v['approved']}/{v['material']}" if v["material"] else "—", f"{v['net']:,.0f}"])
    summary_table = Table(summary_data, hAlign="LEFT", colWidths=[5.3*cm, 2.9*cm, 2.9*cm, 3.1*cm, 3.1*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DBE2")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LGREY]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements += [summary_table, PageBreak()]

    # ---------------- Per-entity material line cards ----------------
    for idx, entity in enumerate(entities, start=3):
        entity_rows = [r for r in rows if r["data"]["entity"] == entity and r["data"]["is_material"]]
        elements.append(Paragraph(f"{idx}.  Material Flux — {entity}", section_style))
        if not entity_rows:
            elements.append(Paragraph("No lines breached the materiality threshold for this entity.", body))
            elements.append(PageBreak())
            continue

        for r in entity_rows:
            d = r["data"]
            sev = (d.get("severity") or "standard").upper()
            sev_color = {"HIGH": RED, "ELEVATED": colors.HexColor("#B98A00"), "STANDARD": GREY}.get(sev, GREY)
            status_color = GREEN if r["status"] == "approved" else (RED if r["status"] == "rejected" else GREY)

            fact_data = [
                ["Category", "Prior ($)", "Current ($)", "Variance ($)", "Variance (%)", "Severity", "Status"],
                [
                    d["category"], f"{d['prior_amount']:,.0f}", f"{d['current_amount']:,.0f}",
                    f"{d['variance_usd']:,.0f}", f"{d['variance_pct']:,.1f}%", sev, r["status"].upper(),
                ],
            ]
            fact_table = Table(fact_data, colWidths=[3.0*cm, 2.4*cm, 2.4*cm, 2.4*cm, 1.9*cm, 2.1*cm, 2.1*cm])
            fact_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), GREY),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E3E6EA")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("TEXTCOLOR", (5, 1), (5, 1), sev_color),
                ("FONTNAME", (5, 1), (6, 1), "Helvetica-Bold"),
                ("TEXTCOLOR", (6, 1), (6, 1), status_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))

            block = [
                Paragraph(d["line_item"], line_title),
                fact_table,
                Spacer(1, 5),
                Paragraph("AI-GENERATED COMMENTARY — REFERENCE ONLY", label_ai),
                Paragraph(r["ai_commentary"], text_ai),
                Spacer(1, 5),
                Paragraph("CONTROLLER FINAL COMMENTARY", label_ctrl),
                Paragraph(r["controller_commentary"], text_ctrl),
                Spacer(1, 12),
                HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#E3E6EA")),
                Spacer(1, 8),
            ]
            elements.append(KeepTogether(block))

        elements.append(PageBreak())

    # ---------------- Sign-off ----------------
    signoff = run["signoff"]
    ts = signoff.get("signed_off_at")
    ts_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if ts else "(pending)"
    elements.append(Paragraph(f"{len(entities)+3}.  Controller Sign-Off", section_style))
    signoff_data = [
        ["Status", "FINAL — all material items approved" if ready else f"DRAFT — {n_approved}/{n_material} material items approved"],
        ["Controller", f"{signoff.get('controller_name') or '(pending)'}  —  {signoff.get('controller_title') or '(pending)'}"],
        ["Signed off", ts_str],
    ]
    signoff_table = Table(signoff_data, colWidths=[3.5*cm, 12.5*cm])
    signoff_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F6")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E3E6EA")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements += [signoff_table, Spacer(1, 0.4*cm), Paragraph(
        "Every AI-Generated Commentary note in this report is a system-drafted reference and is never treated "
        "as final. The Controller Final Commentary is the one authoritative, editable field, and this report "
        "only carries the FINAL watermark once every material line above is marked APPROVED and the controller "
        "named here has signed off. Final judgement on each flagged item rests with the controller, not with "
        "the rule engine or any AI-assisted wording.",
        body,
    )]

    def _make_canvas(*args, **kwargs):
        return _FooterCanvas(*args, watermark=watermark, watermark_color=watermark_color, **kwargs)

    doc.build(elements, canvasmaker=_make_canvas)
    return buf.getvalue()
