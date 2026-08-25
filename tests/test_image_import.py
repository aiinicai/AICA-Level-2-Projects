import pytest
import io
from PIL import Image, ImageDraw, ImageFont
from app.services.image_ocr_service import parse_image_to_dataframe
from app.services.import_service import parse_file_to_dataframe

def create_sample_sales_image() -> bytes:
    img = Image.new('RGB', (400, 250), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    text_content = (
        "Daily Sales Report\n"
        "Date: 2026-05-06\n"
        "Cash Sale: 42500\n"
        "Credit Card: 38400\n"
        "Zomato: 24500\n"
        "Swiggy: 18200\n"
        "Dineout: 9800\n"
    )
    d.text((20, 20), text_content, fill=(0, 0, 0))
    
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()

def test_image_dataframe_parser():
    img_bytes = create_sample_sales_image()
    df = parse_file_to_dataframe(img_bytes, "WhatsApp Image 2026-05-06 at 1.04.39 AM.jpeg")
    
    assert df is not None
    assert len(df) >= 1
    assert "Date" in df.columns
