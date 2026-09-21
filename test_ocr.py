"""A real OCR smoke test when the external Tesseract binary is installed."""
from io import BytesIO
import pytest
from PIL import Image, ImageDraw, ImageFont
from services.pdf_service import extract_text_from_pdf
from services.ocr_service import find_tesseract


def test_real_scanned_pdf():
    executable = find_tesseract()
    if not executable:
        pytest.skip("Tesseract external dependency is not installed")
    image = Image.new("RGB", (1800, 1400), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 38)
    except OSError:
        font = ImageFont.load_default(size=38)
    draw.multiline_text((100, 100), "FICTIONAL INCOME TAX NOTICE\nSection 142(1)\nPlease provide bank statements and interest certificates.\nSubmit your response by 27 September 2026.\nReference: DEMO-SCAN-001", fill="black", font=font, spacing=25)
    pdf = BytesIO()
    image.save(pdf, format="PDF", resolution=150)
    image.close()
    result = extract_text_from_pdf(pdf.getvalue())
    assert result.status == "ocr"
    assert "142(1)" in result.text
    assert "27 September 2026" in result.text
