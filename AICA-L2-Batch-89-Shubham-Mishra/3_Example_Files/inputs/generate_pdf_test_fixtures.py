"""
One-off script to generate two PDF test fixtures for Agent 1's PDF path:
1. sample_gst_cert_text_layer.pdf   - real selectable text (tests pdfplumber text path)
2. sample_pan_scanned.pdf           - a PNG dropped into a PDF page with no text
                                       layer (tests the rasterize-and-vision fallback)
Run: python generate_pdf_test_fixtures.py
"""
import os
from fpdf import FPDF
from PIL import Image

OUT_DIR = os.path.dirname(__file__)


def make_text_layer_pdf(path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    lines = [
        "GOODS AND SERVICES TAX (SAMPLE) - REGISTRATION CERTIFICATE",
        "Form GST REG-06",
        "",
        "1. GSTIN: 29ABCDE1234F1Z8",
        "2. Legal Name: SUNRISE EXPORTS LLP",
        "3. Trade Name: SUNRISE EXPORTS",
        "4. Constitution of Business: LLP",
        "5. Address of Principal Place of Business: 21 MG Road, Bengaluru, Karnataka - 560001",
        "6. Date of Liability: 01/04/2020",
        "7. Type of Registration: Regular",
        "",
        "SAMPLE / DUMMY DOCUMENT - FOR TESTING ONLY",
    ]
    for line in lines:
        pdf.cell(0, 10, text=line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(path)


def make_scanned_pdf(source_png, path):
    img = Image.open(source_png).convert("RGB")
    img.save(path, "PDF", resolution=150.0)


if __name__ == "__main__":
    make_text_layer_pdf(os.path.join(OUT_DIR, "sample_gst_cert_text_layer.pdf"))
    make_scanned_pdf(
        os.path.join(OUT_DIR, "sample_pan_individual_01.png"),
        os.path.join(OUT_DIR, "sample_pan_scanned.pdf"),
    )
    print("Generated 2 PDF test fixtures in", OUT_DIR)
