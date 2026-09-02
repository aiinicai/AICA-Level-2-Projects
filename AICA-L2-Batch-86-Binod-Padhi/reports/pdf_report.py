"""
reports/pdf_report.py
Generates the PDF property analysis report using ReportLab.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)

from config import DISCLAIMER

VERDICT_COLORS = {
    "UNDERPRICED": colors.HexColor("#2E7D32"),
    "FAIRLY PRICED": colors.HexColor("#1565C0"),
    "MODERATELY OVERPRICED": colors.HexColor("#EF6C00"),
    "SIGNIFICANTLY OVERPRICED": colors.HexColor("#C62828"),
}


def _table(data, col_widths=None):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6FA")]),
    ]))
    return t


def generate_pdf_report(path, property_input, city_name, locality_name, valuation_output):
    result = valuation_output["result"]
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], textColor=colors.HexColor("#1F4E78"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=colors.HexColor("#1F4E78"))
    small_italic = ParagraphStyle("SmallItalic", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = []

    story.append(Paragraph("India Property Valuation Report", title_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph("1. Property Details", h2))
    story.append(_table([
        ["Field", "Value"],
        ["Location", f"{locality_name}, {city_name}"],
        ["Property Type", f"{property_input.bhk} BHK {property_input.property_type}"],
        ["Carpet Area", f"{property_input.carpet_area:.0f} sqft"],
        ["Built-up Area", f"{property_input.builtup_area:.0f} sqft"],
        ["Asking Price", f"Rs. {property_input.asking_price:,.0f}"],
        ["Expected Monthly Rent", f"Rs. {property_input.expected_rent:,.0f}"],
    ], col_widths=[6 * cm, 9 * cm]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("2. Estimated Market Rent", h2))
    story.append(_table([
        ["Metric", "Value"],
        ["Low (P25)", f"Rs. {result.market_rent_low:,.0f}"],
        ["Median", f"Rs. {result.market_rent_median:,.0f}"],
        ["High (P75)", f"Rs. {result.market_rent_high:,.0f}"],
    ], col_widths=[6 * cm, 9 * cm]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("3. Estimated Fair Value", h2))
    story.append(_table([
        ["Method", "Value"],
        ["Comparable Market Value", f"Rs. {result.comparable_value:,.0f}"],
        ["Rental Capitalization Value", f"Rs. {result.rental_cap_value:,.0f}"],
        ["Adjusted Value", f"Rs. {result.adjusted_value:,.0f}"],
        ["Fair Value Range", f"Rs. {result.fair_value_low:,.0f} - Rs. {result.fair_value_high:,.0f}"],
    ], col_widths=[6 * cm, 9 * cm]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("4. Verdict", h2))
    verdict_style = ParagraphStyle(
        "Verdict", parent=styles["Heading1"],
        textColor=VERDICT_COLORS.get(result.verdict, colors.black), fontSize=18
    )
    story.append(Paragraph(result.verdict, verdict_style))
    story.append(Paragraph(f"Premium/Discount vs Fair Value: {result.premium_pct:+.1f}%", styles["Normal"]))
    story.append(Paragraph(
        f"Suggested Negotiation Range: Rs. {result.fair_value_low:,.0f} - Rs. {result.fair_value_high:,.0f}",
        styles["Normal"]
    ))
    story.append(Paragraph(
        f"Gross Yield: {result.gross_yield:.2f}% | Net Yield: {result.net_yield:.2f}% | "
        f"Price-to-Rent: {result.price_to_rent:.1f} years", styles["Normal"]
    ))
    story.append(Paragraph(
        f"Investment Score: {result.investment_score:.0f}/100 ({result.investment_score_label}) | "
        f"Confidence: {result.confidence_pct:.0f}%", styles["Normal"]
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("5. Methodology & Sources", h2))
    story.append(Paragraph(result.methodology_notes, styles["Normal"]))
    story.append(Paragraph(
        f"Data sources: {', '.join(valuation_output['sources']) or 'None available - import market data.'}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 18))

    story.append(Paragraph("Disclaimer", h2))
    story.append(Paragraph(DISCLAIMER, small_italic))

    doc.build(story)
    return path
