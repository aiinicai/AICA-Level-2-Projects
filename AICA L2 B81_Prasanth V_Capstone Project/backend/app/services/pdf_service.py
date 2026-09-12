import io
import os
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import A4, A3, letter, landscape, portrait
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128, qr
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Group
from reportlab.lib.utils import ImageReader
from PIL import Image
from .barcode_service import generate_barcode_image, generate_qr_image

def draw_single_asset_label(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    asset_data: Dict[str, Any],
    logo_path: Optional[str] = None
):
    """
    Draws a single asset label on the canvas at (x, y) with specified (width, height) in points.
    Matches the reference corporate asset tag design.
    """
    c.saveState()
    
    # Outer label border
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setLineWidth(0.75)
    c.setFillColor(colors.white)
    c.rect(x, y, width, height, fill=1, stroke=1)

    pad = 2.0 * mm
    content_x = x + pad
    content_y = y + pad
    content_w = width - (2 * pad)
    content_h = height - (2 * pad)

    company_name = (asset_data.get("company_name") or "CORPORATE ASSET").upper()
    sap_no = asset_data.get("sap_number") or "-"
    description = (asset_data.get("description") or "").upper()
    location = (asset_data.get("location") or "-").upper()
    asset_id = asset_data.get("asset_id") or "AST-000000"
    code_type = (asset_data.get("code_type") or "BARCODE").upper()

    # Draw Header (Company Name / Logo)
    header_top = y + height - 3.0 * mm
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(colors.HexColor("#0F172A"))

    # If logo exists, draw small logo at top left
    logo_drawn = False
    if logo_path and os.path.exists(logo_path):
        try:
            logo_img = ImageReader(logo_path)
            logo_w = 12 * mm
            logo_h = 5 * mm
            c.drawImage(logo_img, content_x, header_top - logo_h + 1.5 * mm, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
            c.drawString(content_x + logo_w + 2 * mm, header_top - 2.5 * mm, company_name[:32])
            logo_drawn = True
        except Exception:
            pass

    if not logo_drawn:
        c.drawCentredString(x + (width / 2.0), header_top - 1.5 * mm, company_name[:40])

    # Thin separator below header
    sep_y = header_top - 4.5 * mm
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.5)
    c.line(content_x, sep_y, content_x + content_w, sep_y)

    if "QR" in code_type:
        # --- QR CODE LAYOUT (Code on Right) ---
        qr_size = min(content_h * 0.65, 20 * mm)
        qr_x = content_x + content_w - qr_size - 1 * mm
        qr_y = content_y + (content_h - qr_size) / 2.0 - 1 * mm

        # Draw QR code
        qr_img = generate_qr_image(asset_id, box_size=6, border=1)
        qr_reader = ImageReader(qr_img)
        c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

        # Draw text details on Left
        text_x = content_x
        curr_y = sep_y - 3.5 * mm
        line_spacing = 3.2 * mm

        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(colors.HexColor("#1E293B"))

        def draw_kv(label: str, val: str, cur_y: float):
            c.setFont("Helvetica-Bold", 6.0)
            c.drawString(text_x, cur_y, f"{label:<12}:")
            c.setFont("Helvetica", 6.0)
            c.drawString(text_x + 14 * mm, cur_y, val[:22])

        draw_kv("SAP NO", sap_no, curr_y)
        draw_kv("DESCRIPTION", description, curr_y - line_spacing)
        draw_kv("LOCATION", location, curr_y - (2 * line_spacing))

        # Bottom Asset ID
        c.setFont("Helvetica-Bold", 7.0)
        c.drawString(content_x, content_y + 1 * mm, f"Asset ID: {asset_id}")

    else:
        # --- BARCODE LAYOUT (Reference layout: Key-values top, Barcode bottom) ---
        curr_y = sep_y - 3.0 * mm
        line_spacing = 2.8 * mm

        def draw_kv(label: str, val: str, cur_y: float):
            c.setFont("Helvetica-Bold", 6.0)
            c.setFillColor(colors.HexColor("#1E293B"))
            c.drawString(content_x, cur_y, f"{label:<14}:")
            c.setFont("Helvetica", 6.0)
            c.setFillColor(colors.HexColor("#0F172A"))
            c.drawString(content_x + 16 * mm, cur_y, val[:36])

        draw_kv("SAP NO", sap_no, curr_y)
        draw_kv("DESCRIPTION", description, curr_y - line_spacing)
        draw_kv("LOCATION", location, curr_y - (2 * line_spacing))

        # Barcode area separator
        barcode_sep_y = curr_y - (2.5 * line_spacing)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.setLineWidth(0.5)
        c.line(content_x, barcode_sep_y, content_x + content_w, barcode_sep_y)

        # Draw Code 128 Barcode
        barcode_img = generate_barcode_image(asset_id)
        barcode_reader = ImageReader(barcode_img)
        barcode_h = 7.5 * mm
        barcode_w = content_w * 0.85
        barcode_x = x + (width - barcode_w) / 2.0
        barcode_y = content_y + 3.0 * mm

        c.drawImage(barcode_reader, barcode_x, barcode_y, width=barcode_w, height=barcode_h)

        # Text below barcode
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.drawCentredString(x + (width / 2.0), content_y + 0.5 * mm, asset_id)

    c.restoreState()

def generate_sheet_pdf(
    assets_data: List[Dict[str, Any]],
    page_size_name: str = "A4",
    orientation: str = "PORTRAIT",
    label_width_mm: float = 70.0,
    label_height_mm: float = 35.0,
    margin_top_mm: float = 10.0,
    margin_bottom_mm: float = 10.0,
    margin_left_mm: float = 10.0,
    margin_right_mm: float = 10.0,
    horizontal_gap_mm: float = 3.0,
    vertical_gap_mm: float = 3.0,
    custom_cols: Optional[int] = None,
    custom_rows: Optional[int] = None
) -> io.BytesIO:
    """
    Generates a high-precision multi-page PDF sheet (A4, A3, etc.) containing the asset labels.
    """
    if page_size_name.upper() == "A3":
        page_dim = A3
    elif page_size_name.upper() == "LETTER":
        page_dim = letter
    else:
        page_dim = A4

    if orientation.upper() == "LANDSCAPE":
        page_w, page_h = landscape(page_dim)
    else:
        page_w, page_h = portrait(page_dim)

    # Convert mm to points (1 mm = 2.834645 pt)
    lbl_w = label_width_mm * mm
    lbl_h = label_height_mm * mm
    m_top = margin_top_mm * mm
    m_bottom = margin_bottom_mm * mm
    m_left = margin_left_mm * mm
    m_right = margin_right_mm * mm
    gap_x = horizontal_gap_mm * mm
    gap_y = vertical_gap_mm * mm

    # Usable area
    usable_w = page_w - m_left - m_right
    usable_h = page_h - m_top - m_bottom

    # Calculate optimal cols & rows if not provided
    cols = custom_cols or max(1, int((usable_w + gap_x) / (lbl_w + gap_x)))
    rows = custom_rows or max(1, int((usable_h + gap_y) / (lbl_h + gap_y)))

    labels_per_page = cols * rows

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(page_w, page_h))

    for idx, asset_item in enumerate(assets_data):
        page_idx = idx % labels_per_page
        if idx > 0 and page_idx == 0:
            pdf.showPage()

        # Calculate grid row and col (row 0 is top)
        col_i = page_idx % cols
        row_i = page_idx // cols

        # Calculate position (PDF origin is bottom-left)
        pos_x = m_left + col_i * (lbl_w + gap_x)
        pos_y = page_h - m_top - (row_i + 1) * lbl_h - row_i * gap_y

        logo_path = asset_item.get("logo_path")
        draw_single_asset_label(pdf, pos_x, pos_y, lbl_w, lbl_h, asset_item, logo_path)

    pdf.save()
    buffer.seek(0)
    return buffer

def generate_single_label_pdf(
    asset_data: Dict[str, Any],
    width_mm: float = 70.0,
    height_mm: float = 35.0,
    logo_path: Optional[str] = None
) -> io.BytesIO:
    """
    Generates a single label PDF with custom label dimensions (suitable for direct thermal label printers).
    """
    page_w = width_mm * mm
    page_h = height_mm * mm

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(page_w, page_h))
    draw_single_asset_label(pdf, 0, 0, page_w, page_h, asset_data, logo_path)
    pdf.save()
    buffer.seek(0)
    return buffer
