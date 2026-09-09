"""
QR generation & tagging (blueprint §02, "QR code generation & tagging, in
detail"). The QR payload is deliberately just a short, versioned deep link
keyed on the asset ID — never asset attributes — so the code stays valid
even if the asset transfers or its cost centre changes.
"""

import io

import qrcode
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def qr_payload_url(asset):
    base = settings.FAR_SETTINGS["QR_BASE_URL"].rstrip("/")
    return f"{base}/a/{asset.asset_id}"


def generate_qr_png_bytes(asset):
    img = qrcode.make(qr_payload_url(asset))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


LABEL_W, LABEL_H = 60 * mm, 35 * mm
COLS, ROWS = 3, 8


def generate_batch_label_pdf(assets):
    """
    Batch label sheet — "support bulk label generation for a purchase batch
    ... as one print run, not one-by-one." Lays out COLS x ROWS labels per
    A4 page, each with the QR code, asset ID, and a short description.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    margin_x = (page_w - COLS * LABEL_W) / 2
    margin_y = (page_h - ROWS * LABEL_H) / 2

    for idx, asset in enumerate(assets):
        page_pos = idx % (COLS * ROWS)
        if idx > 0 and page_pos == 0:
            c.showPage()
        col = page_pos % COLS
        row = page_pos // COLS
        x = margin_x + col * LABEL_W
        y = page_h - margin_y - (row + 1) * LABEL_H

        c.rect(x, y, LABEL_W, LABEL_H)
        qr_png = generate_qr_png_bytes(asset)
        from reportlab.lib.utils import ImageReader
        qr_img = ImageReader(io.BytesIO(qr_png))
        qr_size = LABEL_H - 6 * mm
        c.drawImage(qr_img, x + 3 * mm, y + 3 * mm, width=qr_size, height=qr_size)

        text_x = x + qr_size + 6 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(text_x, y + LABEL_H - 8 * mm, asset.asset_id)
        c.setFont("Helvetica", 6.5)
        desc = asset.description[:34]
        c.drawString(text_x, y + LABEL_H - 14 * mm, desc)
        c.drawString(text_x, y + LABEL_H - 19 * mm, asset.asset_class.name[:30])
        c.setFont("Helvetica-Oblique", 5.5)
        c.drawString(text_x, y + 3 * mm, "far.company internal asset tag")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
