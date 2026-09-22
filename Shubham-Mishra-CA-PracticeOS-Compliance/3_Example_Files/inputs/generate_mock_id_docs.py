"""
One-off script to generate dummy, realistically-formatted PAN card and GST
certificate images for testing Agent 1 (Onboarding). No real client data.
Run: python generate_mock_id_docs.py
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = os.path.dirname(__file__)


def font(size, bold=False):
    names = ["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_pan_card(path, name, father, dob, pan):
    img = Image.new("RGB", (860, 540), "#eef3f8")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 859, 90], fill="#0b3d91")
    d.text((30, 25), "INCOME TAX DEPARTMENT   |   GOVT. OF INDIA (SAMPLE)", font=font(24, True), fill="white")
    d.rectangle([20, 110, 839, 519], outline="#0b3d91", width=3)
    d.text((40, 140), "Permanent Account Number Card", font=font(20, True), fill="#0b3d91")
    d.text((40, 200), f"Permanent Account Number", font=font(16), fill="#333")
    d.text((40, 225), pan, font=font(28, True), fill="black")
    d.text((40, 280), "Name", font=font(16), fill="#333")
    d.text((40, 305), name, font=font(22, True), fill="black")
    d.text((40, 350), "Father's Name", font=font(16), fill="#333")
    d.text((40, 375), father, font=font(22, True), fill="black")
    d.text((40, 420), "Date of Birth", font=font(16), fill="#333")
    d.text((40, 445), dob, font=font(22, True), fill="black")
    d.text((40, 490), "SAMPLE / DUMMY DOCUMENT - FOR TESTING ONLY", font=font(14, True), fill="#c62828")
    img.save(path)


def make_gst_certificate(path, legal_name, trade_name, gstin, address, reg_date, entity_type):
    img = Image.new("RGB", (900, 700), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 899, 70], fill="#0b3d91")
    d.text((30, 20), "GOODS AND SERVICES TAX (SAMPLE) - REGISTRATION CERTIFICATE", font=font(18, True), fill="white")
    d.text((30, 90), "Form GST REG-06", font=font(16, True), fill="#0b3d91")
    fields = [
        ("1. GSTIN", gstin),
        ("2. Legal Name", legal_name),
        ("3. Trade Name, if any", trade_name),
        ("4. Constitution of Business", entity_type),
        ("5. Address of Principal Place of Business", address),
        ("6. Date of Liability", reg_date),
        ("7. Period of Validity", "From " + reg_date + " To Not Applicable"),
        ("8. Type of Registration", "Regular"),
    ]
    y = 140
    for label, value in fields:
        d.text((30, y), label, font=font(15), fill="#555")
        d.text((30, y + 22), value, font=font(18, True), fill="black")
        y += 65
    d.text((30, 640), "SAMPLE / DUMMY DOCUMENT - FOR TESTING ONLY, NOT A REAL GST CERTIFICATE", font=font(14, True), fill="#c62828")
    img.save(path)


if __name__ == "__main__":
    make_pan_card(
        os.path.join(OUT_DIR, "sample_pan_individual_01.png"),
        name="RAVI KUMAR SHARMA",
        father="SURESH KUMAR SHARMA",
        dob="14/06/1988",
        pan="ABCDE1234F",
    )
    make_pan_card(
        os.path.join(OUT_DIR, "sample_pan_individual_02.png"),
        name="PRIYA VENKATESH",
        father="MURALI VENKATESH",
        dob="02/11/1992",
        pan="PQRST5678K",
    )
    make_gst_certificate(
        os.path.join(OUT_DIR, "sample_gst_cert_company_01.png"),
        legal_name="RIVERSTONE TRADERS PRIVATE LIMITED",
        trade_name="RIVERSTONE TRADERS",
        gstin="07ABCDE1234F1Z5",
        address="12 Nehru Place, New Delhi, Delhi - 110019",
        reg_date="01/07/2021",
        entity_type="Private Limited Company",
    )
    make_gst_certificate(
        os.path.join(OUT_DIR, "sample_gst_cert_proprietor_01.png"),
        legal_name="RAVI KUMAR SHARMA",
        trade_name="SHARMA ENTERPRISES",
        gstin="07PQRST5678K1Z2",
        address="45 Karol Bagh, New Delhi, Delhi - 110005",
        reg_date="15/03/2019",
        entity_type="Proprietorship",
    )
    print("Generated 4 sample ID documents in", OUT_DIR)
