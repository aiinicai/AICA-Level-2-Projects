"""
Generates a realistic 3-page commercial lease PDF for testing.
Uses PyMuPDF to create a clean, multi-page PDF document.
"""
from pathlib import Path
import pymupdf

def generate_pdf():
    txt_path = Path(__file__).resolve().parent / "sample_commercial_lease.txt"
    pdf_path = Path(__file__).resolve().parent / "sample_commercial_lease.pdf"

    with open(txt_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    doc = pymupdf.open()
    
    # Split content across 3 pages
    sections = [
        full_text[:full_text.find("NOW THEREFORE")],
        full_text[full_text.find("NOW THEREFORE"):full_text.find("5. SECURITY DEPOSIT")],
        full_text[full_text.find("5. SECURITY DEPOSIT"):]
    ]

    for sec in sections:
        page = doc.new_page(width=595, height=842) # A4
        # Add header
        page.insert_text((50, 40), "OFFICIAL LEASE DOCUMENT - STRICTLY CONFIDENTIAL", fontsize=8, color=(0.4, 0.4, 0.4))
        # Insert body text inside a bounding box
        rect = pymupdf.Rect(50, 60, 545, 780)
        page.insert_textbox(rect, sec.strip(), fontsize=10, fontname="helv", align=0)
        # Add footer
        page.insert_text((50, 810), f"Page {len(doc)} of 3", fontsize=8, color=(0.5, 0.5, 0.5))

    doc.save(str(pdf_path))
    doc.close()
    print(f"Generated sample PDF at: {pdf_path}")

if __name__ == "__main__":
    generate_pdf()
