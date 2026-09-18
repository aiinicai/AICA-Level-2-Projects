"""
AI Auditor V8 - OCR Engine for Scanned Financial Statements
Uses PyMuPDF to render pages to images, PIL for enhancement, and pytesseract for OCR text extraction.
"""

import os
import re
from typing import List, Dict, Optional, Tuple, Any
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

class OCREngine:
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        else:
            # Common Windows Tesseract install locations
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
            ]
            for p in common_paths:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

    @staticmethod
    def is_tesseract_available() -> bool:
        """Checks if tesseract executable is callable."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Converts to grayscale, enhances contrast, and sharpens for optimal tabular OCR."""
        # Convert to grayscale
        gray = image.convert('L')
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(2.0)
        # Slight thresholding / binarization
        threshold_val = 180
        binary = enhanced.point(lambda p: 255 if p > threshold_val else 0)
        return binary

    def ocr_image(self, image: Image.Image) -> str:
        """Performs OCR on a PIL Image."""
        if not self.is_tesseract_available():
            return "OCR Unavailable: Tesseract OCR is not installed or configured on the system path."
            
        prep_img = self.preprocess_image(image)
        # PSM 6: Assume a single uniform block of text
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(prep_img, config=custom_config)
        return text

    def ocr_image_to_table_rows(self, image: Image.Image) -> List[List[str]]:
        """Extracts text and parses row lines into tabular tokens."""
        raw_text = self.ocr_image(image)
        lines = raw_text.splitlines()
        rows = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            # Split multiple spaces or tabs into columns
            parts = re.split(r'\s{2,}|\t', line_str)
            if len(parts) >= 2:
                rows.append([p.strip() for p in parts if p.strip()])
            else:
                # Try regex matching item and trailing numbers
                match = re.match(r'^(.*?)\s+([\(\d,\.\-\)]+)\s+([\(\d,\.\-\)]+)$', line_str)
                if match:
                    rows.append([match.group(1).strip(), match.group(2).strip(), match.group(3).strip()])
                else:
                    rows.append([line_str])
        return rows
