"""Deterministic Udyam certificate parsing tests. Runs standalone or with pytest."""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reportlab.pdfgen import canvas

from clock45.udyam import UdyamParseError, parse_udyam_certificate, parse_udyam_text


checks = 0


def check(name, got, want):
    global checks
    checks += 1
    if got != want:
        raise AssertionError(f"{name}: got {got!r}, expected {want!r}")
    print(f"  PASS  {name:<42} {got}")


SYNTHETIC_TEXT = """
UDYAM REGISTRATION CERTIFICATE
UDYAM REGISTRATION NUMBER UDYAM-MH-12-0123456
NAME OF ENTERPRISE SAMPLE ENGINEERING WORKS
TYPE OF ENTERPRISE *
SNo. Classification Year Enterprise Type Classification Date
1 2025-26 Small 01/04/2025
2 2024-25 Micro 05/04/2024
MAJOR ACTIVITY MANUFACTURING
OFFICIAL ADDRESS OF ENTERPRISE Flat/Door/Block No. 12 Industrial Area City PUNE Mobile 9000000000
DATE OF INCORPORATION / REGISTRATION OF ENTERPRISE 12/06/2018
DATE OF COMMENCEMENT OF PRODUCTION/BUSINESS 20/06/2018
NATIONAL INDUSTRY CLASSIFICATION CODE(S)
1 25 - Manufacture 2599 - Other fabricated products 25999 - Other fabricated metal products Manufacturing
DATE OF UDYAM REGISTRATION 05/04/2024
Type of Organisation Partnership Name of Enterprise SAMPLE ENGINEERING WORKS
Owner Name SAMPLE OWNER PAN ABCDE1234F
"""


def _pdf_bytes(text: str) -> bytes:
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    y = 800
    for line in text.splitlines():
        pdf.drawString(40, y, line)
        y -= 13
    pdf.save()
    return output.getvalue()


def test_01_structured_text_parser():
    data = parse_udyam_text(SYNTHETIC_TEXT)
    check("01 Udyam number", data.udyam_no, "UDYAM-MH-12-0123456")
    check("01 enterprise name", data.enterprise_name, "SAMPLE ENGINEERING WORKS")
    check("01 current class", data.enterprise_class, "SMALL")
    check("01 major activity", data.major_activity, "MANUFACTURING")
    check("01 PAN", data.pan, "ABCDE1234F")
    check("01 organisation", data.organisation_type, "Partnership")
    check("01 history rows", len(data.classification_history), 2)
    check("01 exact FY class", data.class_for_year("2024-25").enterprise_class, "MICRO")
    check("01 no cross-year guess", data.class_for_year("2023-24"), None)
    check("01 registration date", data.registration_date.isoformat(), "2024-04-05")


def test_02_pdf_and_safe_failures():
    parsed = parse_udyam_certificate(_pdf_bytes(SYNTHETIC_TEXT), filename="sample.pdf")
    check("02 PDF parsed", parsed.udyam_no, "UDYAM-MH-12-0123456")
    check("02 source fingerprint", len(parsed.source_sha256), 64)
    try:
        parse_udyam_certificate(b"not a pdf", filename="bad.pdf")
    except UdyamParseError as exc:
        check("02 corrupt PDF refused", exc.code, "INVALID_PDF")
    else:
        raise AssertionError("Malformed PDF was accepted")
    try:
        parse_udyam_certificate(b"\x89PNG\r\n", filename="scan.png", media_type="image/png")
    except UdyamParseError as exc:
        check("02 OCR limitation explicit", exc.code, "OCR_REQUIRED")
    else:
        raise AssertionError("Image was silently parsed")


if __name__ == "__main__":
    test_01_structured_text_parser()
    test_02_pdf_and_safe_failures()
    print(f"\n{checks} assertions across 2 cases — ALL PASSED")
