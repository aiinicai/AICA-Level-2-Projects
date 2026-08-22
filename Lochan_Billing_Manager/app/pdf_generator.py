"""
pdf_generator.py
-----------------
Builds a professional invoice PDF using ReportLab, matching the firm's
sample invoice layout:

  Header  : office address (left) | firm name & tagline (center) |
            mobile/email/website (right)
  Meta    : Dated / Invoice No. / firm PAN & GSTIN (left) vs.
            Client / GSTIN / Address / State / State Code / Place of
            Supply (right)
  Items   : Assignment/Work Executed | Service Accounting Code | Amount
  Totals  : Sub Total, CGST, SGST, IGST, Total (with amount in words)
  Sign    : Authorized Signatory block
  Footer  : Banking details + Terms & Conditions

This module has no GUI dependency -- it only needs an invoice dict (see
database.py / utils.compute_invoice_totals for the expected shape) and an
output file path.
"""

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
    KeepTogether,
)

from app import config, utils

PRIMARY_BLUE = colors.HexColor(config.COLOR_PRIMARY_BLUE)
ACCENT_RED = colors.HexColor(config.COLOR_ACCENT_RED)
LIGHT_GREY = colors.HexColor(config.COLOR_LIGHT_GREY)
BORDER_GREY = colors.HexColor(config.COLOR_BORDER_GREY)
TEXT_DARK = colors.HexColor(config.COLOR_TEXT_DARK)
TAGLINE_GREY = colors.HexColor("#595959")  # matches the muted grey tagline in the firm's sample bill

styles = getSampleStyleSheet()

STYLE_ADDR = ParagraphStyle(
    "Addr", parent=styles["Normal"], fontName="Helvetica", fontSize=8.3,
    leading=11, textColor=TEXT_DARK,
)
STYLE_ADDR_BOLD_LABEL = ParagraphStyle(
    "AddrBoldLabel", parent=STYLE_ADDR, fontName="Helvetica-Bold",
)
STYLE_FIRM_NAME = ParagraphStyle(
    "FirmName", parent=styles["Normal"], fontName="Times-Bold",
    fontSize=23, leading=24, alignment=TA_CENTER, textColor=PRIMARY_BLUE,
    spaceAfter=1,
)
STYLE_FIRM_TAGLINE = ParagraphStyle(
    "FirmTagline", parent=styles["Normal"], fontName="Helvetica",
    fontSize=9.5, leading=11, alignment=TA_CENTER, textColor=TAGLINE_GREY,
    spaceBefore=0,
)
STYLE_CONTACT = ParagraphStyle(
    "Contact", parent=styles["Normal"], fontName="Helvetica", fontSize=8.3,
    leading=11, alignment=TA_RIGHT, textColor=TEXT_DARK,
)
STYLE_LABEL_VALUE = ParagraphStyle(
    "LabelValue", parent=styles["Normal"], fontName="Helvetica", fontSize=9,
    leading=13, textColor=TEXT_DARK,
)
STYLE_LABEL_VALUE_BOLD = ParagraphStyle(
    "LabelValueBold", parent=STYLE_LABEL_VALUE, fontName="Helvetica-Bold",
)
STYLE_TABLE_HEADER = ParagraphStyle(
    "TableHeader", parent=styles["Normal"], fontName="Helvetica-Bold",
    fontSize=9.5, leading=12, alignment=TA_CENTER, textColor=colors.white,
)
STYLE_ITEM_TEXT = ParagraphStyle(
    "ItemText", parent=styles["Normal"], fontName="Helvetica", fontSize=9,
    leading=12, textColor=TEXT_DARK,
)
STYLE_ITEM_CENTER = ParagraphStyle(
    "ItemCenter", parent=STYLE_ITEM_TEXT, alignment=TA_CENTER,
)
STYLE_ITEM_RIGHT = ParagraphStyle(
    "ItemRight", parent=STYLE_ITEM_TEXT, alignment=TA_RIGHT,
)
STYLE_TOTAL_LABEL = ParagraphStyle(
    "TotalLabel", parent=styles["Normal"], fontName="Helvetica-Bold",
    fontSize=9.5, leading=12, textColor=TEXT_DARK,
)
STYLE_TOTAL_VALUE = ParagraphStyle(
    "TotalValue", parent=STYLE_TOTAL_LABEL, alignment=TA_RIGHT,
)
STYLE_WORDS = ParagraphStyle(
    "Words", parent=styles["Normal"], fontName="Helvetica-BoldOblique",
    fontSize=8.7, leading=11, textColor=TEXT_DARK,
)
STYLE_SIGN = ParagraphStyle(
    "Sign", parent=styles["Normal"], fontName="Helvetica", fontSize=9,
    leading=12, alignment=TA_CENTER, textColor=TEXT_DARK,
)
STYLE_SIGN_BOLD = ParagraphStyle(
    "SignBold", parent=STYLE_SIGN, fontName="Helvetica-Bold",
)
STYLE_FOOTER_HEADING = ParagraphStyle(
    "FooterHeading", parent=styles["Normal"], fontName="Helvetica-Bold",
    fontSize=9.5, leading=12, textColor=PRIMARY_BLUE,
)
STYLE_FOOTER_TEXT = ParagraphStyle(
    "FooterText", parent=styles["Normal"], fontName="Helvetica", fontSize=8,
    leading=11, textColor=TEXT_DARK,
)


def _p(text, style=STYLE_LABEL_VALUE):
    text = "" if text is None else str(text)
    return Paragraph(text.replace("\n", "<br/>"), style)


def _build_header():
    addr_lines = "<br/>".join(config.FIRM_ADDRESS_LINES)
    left = [
        _p(f"<b>{config.FIRM_OFFICE_LABEL}</b>", STYLE_ADDR),
        _p(addr_lines, STYLE_ADDR),
    ]
    center = [
        _p(config.FIRM_NAME, STYLE_FIRM_NAME),
        _p(config.FIRM_TAGLINE, STYLE_FIRM_TAGLINE),
    ]
    contact_lines = [f"Mobile No. {config.FIRM_MOBILE_NUMBERS}"]
    contact_lines += [f"Email : {e}" for e in config.FIRM_EMAILS]
    contact_lines.append(f"Website : {config.FIRM_WEBSITE}")
    right = [_p("<br/>".join(contact_lines), STYLE_CONTACT)]

    from reportlab.platypus import Table as _T
    left_tbl = _T([[l] for l in left], colWidths=[5.5 * cm])
    center_tbl = _T([[c] for c in center], colWidths=[7 * cm])
    right_tbl = _T([[r] for r in right], colWidths=[5.5 * cm])

    header_tbl = Table(
        [[left_tbl, center_tbl, right_tbl]],
        colWidths=[5.6 * cm, 7.0 * cm, 5.6 * cm],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return header_tbl


def _build_meta_block(invoice):
    customer = invoice.get("customer", {})
    left_rows = [
        [_p("Dated", STYLE_LABEL_VALUE_BOLD), _p(f": {invoice.get('invoice_date_display', invoice.get('invoice_date', ''))}", STYLE_LABEL_VALUE)],
        [_p("Invoice", STYLE_LABEL_VALUE_BOLD), _p(f": {invoice.get('invoice_number', '')}", STYLE_LABEL_VALUE)],
        [_p(""), _p("")],
        [_p("PAN", STYLE_LABEL_VALUE_BOLD), _p(f": {config.FIRM_PAN}", STYLE_LABEL_VALUE)],
        [_p("GSTIN", STYLE_LABEL_VALUE_BOLD), _p(f": {config.FIRM_GSTIN}", STYLE_LABEL_VALUE)],
    ]
    right_rows = [
        [_p("Client", STYLE_LABEL_VALUE_BOLD), _p(f": {customer.get('name', '')}", STYLE_LABEL_VALUE)],
        [_p("GSTIN / UIN", STYLE_LABEL_VALUE_BOLD), _p(f": {customer.get('gstin', '') or 'Unregistered'}", STYLE_LABEL_VALUE)],
        [_p("Address", STYLE_LABEL_VALUE_BOLD), _p(f": {customer.get('address', '')}", STYLE_LABEL_VALUE)],
        [_p("State", STYLE_LABEL_VALUE_BOLD), _p(f": {customer.get('state_name', '')}", STYLE_LABEL_VALUE)],
        [_p("State Code", STYLE_LABEL_VALUE_BOLD), _p(f": {customer.get('state_code', '')}", STYLE_LABEL_VALUE)],
        [_p("Place of supply", STYLE_LABEL_VALUE_BOLD), _p(f": {customer.get('place_of_supply', 'Same as above') or 'Same as above'}", STYLE_LABEL_VALUE)],
    ]

    left_tbl = Table(left_rows, colWidths=[2.0 * cm, 5.4 * cm])
    right_tbl = Table(right_rows, colWidths=[2.8 * cm, 8.0 * cm])
    for t in (left_tbl, right_tbl):
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ]))

    outer = Table([[left_tbl, right_tbl]], colWidths=[7.4 * cm, 10.8 * cm])
    outer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER_GREY),
        ("LINEAFTER", (0, 0), (0, 0), 0.8, BORDER_GREY),
        ("LINEBELOW", (0, 0), (-1, -1), 0.8, BORDER_GREY),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return outer


def _build_items_table(invoice, computed):
    data = [[
        _p("Assignment / Work Executed", STYLE_TABLE_HEADER),
        _p("Service Accounting Code", STYLE_TABLE_HEADER),
        _p("Amount (Rs.)", STYLE_TABLE_HEADER),
    ]]
    for item in computed["items"]:
        data.append([
            _p(item.get("particulars", ""), STYLE_ITEM_TEXT),
            _p(item.get("sac", ""), STYLE_ITEM_CENTER),
            _p(utils.format_currency(item.get("amount", 0)), STYLE_ITEM_RIGHT),
        ])

    # pad with a minimum number of blank rows so short invoices still look
    # like a proper table (matches the sample's generous row height)
    min_rows = 3
    while len(data) - 1 < min_rows:
        data.append([_p("&nbsp;", STYLE_ITEM_TEXT), _p(""), _p("")])

    col_widths = [9.7 * cm, 3.9 * cm, 4.6 * cm]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER_GREY),
        ("INNERGRID", (0, 0), (-1, 0), 0.8, BORDER_GREY),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BORDER_GREY),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, BORDER_GREY),
        ("BOX", (0, 1), (0, -1), 0.4, BORDER_GREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEAFTER", (0, 0), (1, -1), 0.4, BORDER_GREY),
    ]
    tbl.setStyle(TableStyle(style))
    return tbl


def _fmt_rate(rate):
    return utils.format_gst_rate(rate)


def _tax_row(label, amount, show_dash):
    value = "-" if show_dash else utils.format_currency(amount)
    return [
        _p(label, STYLE_TOTAL_LABEL),
        _p(""),
        _p(value, STYLE_TOTAL_VALUE),
    ]


def _build_totals_table(computed):
    intra = computed["is_intra_state"]
    subtotal = computed["subtotal"] or 0
    overall_rate = (computed["total_gst"] / subtotal * 100) if subtotal else 0
    half_rate = overall_rate / 2

    rows = [
        [_p("Sub Total:", STYLE_TOTAL_LABEL), _p(""), _p(utils.format_currency(computed["subtotal"]), STYLE_TOTAL_VALUE)],
        _tax_row(f"Add: Central Goods and Service Tax (CGST) @ {_fmt_rate(half_rate)}%", computed["cgst"], not intra),
        _tax_row(f"Add: State Goods and Service Tax (SGST) @ {_fmt_rate(half_rate)}%", computed["sgst"], not intra),
        _tax_row(f"Add: Integrated Goods and Service Tax (IGST) @ {_fmt_rate(overall_rate)}%", computed["igst"], intra),
    ]
    if abs(computed.get("round_off", 0)) > 0.001:
        rows.append([
            _p("Round Off:", STYLE_TOTAL_LABEL), _p(""),
            _p(utils.format_currency(computed["round_off"]), STYLE_TOTAL_VALUE),
        ])
    words = utils.amount_in_words_rupees(computed["grand_total"])
    rows.append([
        _p(f"Total: ({words})", STYLE_WORDS), _p(""),
        _p(utils.format_currency(computed["grand_total"]), STYLE_TOTAL_VALUE),
    ])

    col_widths = [9.7 * cm, 3.9 * cm, 4.6 * cm]
    tbl = Table(rows, colWidths=col_widths)
    style = [
        ("SPAN", (0, r), (1, r)) for r in range(len(rows))
    ] + [
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER_GREY),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER_GREY),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, BORDER_GREY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEAFTER", (1, 0), (1, -1), 0, colors.white),
    ]
    tbl.setStyle(TableStyle(style))
    return tbl


def _build_signature_block():
    rows = [
        [_p("")],
        [_p("")],
        [_p(config.SIGNATORY_LINE_1, STYLE_SIGN)],
        [_p(config.SIGNATORY_LINE_2, STYLE_SIGN_BOLD)],
        [_p(config.SIGNATORY_LINE_3, STYLE_SIGN)],
    ]
    tbl = Table(rows, colWidths=[6.5 * cm])
    tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEABOVE", (0, 2), (0, 2), 0.8, TEXT_DARK),
    ]))
    wrapper = Table([[Spacer(1, 1), tbl]], colWidths=[12.1 * cm, 6.1 * cm])
    wrapper.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return wrapper


def _build_footer():
    bank_rows = [
        [_p("Name", STYLE_FOOTER_TEXT), _p(f": {config.BANK_ACCOUNT_NAME}", STYLE_FOOTER_TEXT)],
        [_p("Bank Name", STYLE_FOOTER_TEXT), _p(f": {config.BANK_NAME}", STYLE_FOOTER_TEXT)],
        [_p("Account No.", STYLE_FOOTER_TEXT), _p(f": {config.BANK_ACCOUNT_NO}", STYLE_FOOTER_TEXT)],
        [_p("Address of Bank", STYLE_FOOTER_TEXT), _p(f": {config.BANK_ADDRESS}", STYLE_FOOTER_TEXT)],
        [_p("IFSC Code", STYLE_FOOTER_TEXT), _p(f": {config.BANK_IFSC}", STYLE_FOOTER_TEXT)],
    ]
    if config.BANK_UPI_ID:
        bank_rows.append([_p("UPI ID", STYLE_FOOTER_TEXT), _p(f": {config.BANK_UPI_ID}", STYLE_FOOTER_TEXT)])

    bank_tbl = Table(bank_rows, colWidths=[3.2 * cm, 8 * cm])
    bank_tbl.hAlign = "LEFT"  # Table defaults to centering on the page when
    # narrower than the content width -- without this the whole block drifts
    # right instead of sitting flush under the "Banking Details..." heading.
    bank_tbl.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    terms_flowables = [_p("Terms and Conditions:", STYLE_FOOTER_HEADING), Spacer(1, 2)]
    letters = "abcdefghijklmnopqrstuvwxyz"
    for i, term in enumerate(config.TERMS_AND_CONDITIONS):
        terms_flowables.append(_p(f"{letters[i]}) {term}", STYLE_FOOTER_TEXT))
        terms_flowables.append(Spacer(1, 2))

    footer_flow = [
        HRFlowable(width="100%", thickness=0.8, color=BORDER_GREY, spaceBefore=4, spaceAfter=6),
        _p("Banking Details for Electronic Payments", STYLE_FOOTER_HEADING),
        Spacer(1, 3),
        bank_tbl,
        Spacer(1, 8),
    ] + terms_flowables

    return footer_flow


def generate_invoice_pdf(invoice: dict, output_path: str) -> str:
    """
    Render `invoice` (as produced by the GUI / stored in the JSON database,
    already run through utils.compute_invoice_totals under invoice["computed"])
    to a PDF at `output_path`. Returns output_path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    computed = invoice.get("computed")
    if computed is None:
        customer = invoice.get("customer", {})
        computed = utils.compute_invoice_totals(
            invoice.get("items", []), customer.get("state_code", "")
        )

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.4 * cm, rightMargin=1.4 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
        title=f"Invoice {invoice.get('invoice_number', '')}",
        author=config.FIRM_NAME,
    )

    story = []
    story.append(_build_header())
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.4, color=PRIMARY_BLUE, spaceAfter=8))
    story.append(_build_meta_block(invoice))
    story.append(Spacer(1, 10))
    story.append(_build_items_table(invoice, computed))
    story.append(_build_totals_table(computed))
    story.append(Spacer(1, 22))
    story.append(_build_signature_block())
    story.append(Spacer(1, 14))
    story.extend(_build_footer())

    doc.build(story)
    return output_path
