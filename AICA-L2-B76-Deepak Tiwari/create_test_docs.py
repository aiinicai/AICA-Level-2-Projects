import os
import io
import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

def generate_sample_document_image(title, body_text, width=1200, height=1600):
    """
    Creates a clean synthetic document page image with black text on white background.
    """
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try loading default font or truetype
    try:
        font_large = ImageFont.truetype("arial.ttf", 32)
        font_body = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font_large = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # Header title
    draw.rectangle([50, 50, width - 50, 150], fill=(230, 230, 250), outline=(100, 100, 200), width=4)
    draw.text((80, 80), title, fill=(0, 0, 128), font=font_large)

    # Document body text paragraph lines
    y = 200
    for paragraph in range(3):
        for line in body_text:
            draw.text((80, y), line, fill=(20, 20, 20), font=font_body)
            y += 42
            if y > height - 100:
                break
        y += 25

    # Decorative border lines
    draw.line([80, height - 60, width - 80, height - 60], fill=(150, 150, 150), width=2)
    draw.text((80, height - 45), "Confidential Document - Generated for DocDeskew AI Testing", fill=(120, 120, 120), font=font_body)

    return img


def apply_skew_and_rotation(pil_img, rotate_angle=0, skew_angle=0.0):
    """
    Applies 90/180/270 degree rotation and fine float skew angle in degrees.
    """
    res = pil_img.copy()

    # Apply 90/180/270 rotation first
    if rotate_angle in [90, 180, 270]:
        res = res.rotate(-rotate_angle, expand=True, fillcolor=(255, 255, 255))

    # Apply fine skew angle using OpenCV affine transform
    if abs(skew_angle) > 0.01:
        rgb = np.array(res)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]
        center = (w // 2, h // 2)

        M = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]

        rotated = cv2.warpAffine(
            bgr, M, (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        res = Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))

    return res


def create_all_test_assets(output_dir="sample_test_docs"):
    os.makedirs(output_dir, exist_ok=True)
    generated_files = []

    text_sample_1 = [
        "ANNUAL FINANCIAL REPORT SUMMARY - FY 2026",
        "1. Executive Overview: Total revenue increased by 24.5% year-over-year.",
        "2. Operational Metrics: Customer retention rate maintained at 98.2%.",
        "3. Financial Breakdown:",
        "   - Gross Revenue: $14,250,000 USD",
        "   - Net Operating Income: $3,840,000 USD",
        "   - R&D Allocation: $2,100,000 USD",
        "4. Conclusion and Strategic Plan for Next Quarter.",
    ]

    text_sample_2 = [
        "TECHNICAL SYSTEM ARCHITECTURE & PROTOCOLS",
        "Section A: Microservices Topology and Event Bus Integration.",
        "1. Distributed Ledger Authentication Framework",
        "2. Data Processing Pipeline & Automated Deskew Engine",
        "3. Real-time Optical Character Recognition (OCR) Optimization",
        "4. End-to-End Encryption and Security Audit Logs.",
    ]

    # Test 1: Image rotated 90° CW with +5.0° skew
    img1 = generate_sample_document_image("TEST PAGE 1 (Rotated 90 + Skewed 5 deg)", text_sample_1)
    img1_modified = apply_skew_and_rotation(img1, rotate_angle=90, skew_angle=5.0)
    p1 = os.path.join(output_dir, "test_page_1_rot90_skew5.png")
    img1_modified.save(p1)
    generated_files.append(p1)

    # Test 2: Image rotated 180° upside down with -7.5° skew
    img2 = generate_sample_document_image("TEST PAGE 2 (Rotated 180 + Skewed -7.5 deg)", text_sample_2)
    img2_modified = apply_skew_and_rotation(img2, rotate_angle=180, skew_angle=-7.5)
    p2 = os.path.join(output_dir, "test_page_2_rot180_skew7.png")
    img2_modified.save(p2)
    generated_files.append(p2)

    # Test 3: Multi-page PDF document with rotated/skewed pages
    pdf_path = os.path.join(output_dir, "test_multipage_doc.pdf")
    pdf_doc = pymupdf.open()

    for idx, (title, texts, rot, skew) in enumerate([
        ("PDF Page 1 - Normal Orientation with +3.5 deg Skew", text_sample_1, 0, 3.5),
        ("PDF Page 2 - Rotated 270 deg with -4.0 deg Skew", text_sample_2, 270, -4.0),
    ]):
        base_img = generate_sample_document_image(title, texts)
        mod_img = apply_skew_and_rotation(base_img, rotate_angle=rot, skew_angle=skew)
        
        # Save mod_img to bytes
        buffer = io.BytesIO()
        mod_img.save(buffer, format="JPEG", quality=95)
        img_bytes = buffer.getvalue()
        w, h = mod_img.size
        page = pdf_doc.new_page(width=w, height=h)
        rect = pymupdf.Rect(0, 0, w, h)
        page.insert_image(rect, stream=img_bytes)

    pdf_doc.save(pdf_path)
    pdf_doc.close()
    generated_files.append(pdf_path)

    print("Successfully created synthetic test documents:")
    for f in generated_files:
        print(f"  - {f}")

    return generated_files


if __name__ == "__main__":
    create_all_test_assets()
