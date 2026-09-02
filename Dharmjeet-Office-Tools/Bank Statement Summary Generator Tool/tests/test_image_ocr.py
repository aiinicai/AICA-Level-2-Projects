"""Test image OCR parsing with synthetic bank statement image."""

import os
import pytest
from PIL import Image, ImageDraw, ImageFont
import io

from ingestion.image_ocr import read_image_statement

def create_mock_statement_image() -> bytes:
    """Create a synthetic clear image of a bank statement table."""
    img = Image.new('RGB', (1400, 700), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Title & Metadata
    draw.text((50, 40), "STATE BANK OF INDIA - ACCOUNT STATEMENT", fill=(0, 50, 100))
    draw.text((50, 70), "Account Number: 123456789012 | Period: 01/04/2024 to 30/04/2024", fill=(50, 50, 50))
    
    # Table Header
    headers = "Date            Narration                               Ref No       Debit        Credit       Balance"
    draw.text((50, 120), headers, fill=(0, 0, 0))
    draw.line([(50, 145), (1350, 145)], fill=(0, 0, 0), width=2)
    
    # Row 1
    draw.text((50, 160), "05/04/2024      ACH CR SALARY FROM TECH CORP            ACH001                    125000.00    125000.00", fill=(0, 0, 0))
    # Row 2
    draw.text((50, 200), "10/04/2024      UPI/412345678901/Rahul Sharma/Payment   UPI002       4500.00                   120500.00", fill=(0, 0, 0))
    # Row 3
    draw.text((50, 240), "15/04/2024      BY CASH DEPOSIT - SELF AT BNA           BNA003                    55000.00     175500.00", fill=(0, 0, 0))
    # Row 4
    draw.text((50, 280), "20/04/2024      ATM CASH WITHDRAWAL                     ATM004       10000.00                  165500.00", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=95)
    return buf.getvalue()

def test_read_image_statement_rapidocr():
    img_bytes = create_mock_statement_image()
    df = read_image_statement(img_bytes, filename="mock_sbi_photo.jpeg")
    
    assert not df.empty, "Image statement DataFrame should not be empty"
    assert len(df) >= 3, f"Should extract at least 3 transactions, got {len(df)}"
    assert "SBI" in df["source_bank"].iloc[0] or "State Bank" in df["source_bank"].iloc[0] or "Generic" in df["source_bank"].iloc[0]
