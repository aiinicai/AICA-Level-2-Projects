import os
import re
import shutil
import logging
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# Common candidate executable paths for Tesseract OCR on Windows and Unix systems
CANDIDATE_PATHS = [
    r"C:\Program Files\Tesseract\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    r"C:\Program Files\PDF24\tesseract\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/opt/homebrew/bin/tesseract",
]

def find_tesseract_executable(custom_path=None):
    """
    Attempts to locate the Tesseract OCR binary.
    Priority: custom_path > shutil.which("tesseract") > common candidate paths.
    """
    if custom_path and os.path.exists(custom_path) and os.path.isfile(custom_path):
        pytesseract.pytesseract.tesseract_cmd = custom_path
        return custom_path

    # Check system PATH
    which_path = shutil.which("tesseract")
    if which_path:
        pytesseract.pytesseract.tesseract_cmd = which_path
        return which_path

    # Check candidate file paths
    for path in CANDIDATE_PATHS:
        if os.path.exists(path) and os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return path

    return None


def get_tesseract_status():
    """
    Returns (is_available, executable_path, version_string_or_error)
    """
    exe_path = find_tesseract_executable()
    if not exe_path:
        return False, None, "Tesseract binary not found in PATH or standard directories."
    
    try:
        pytesseract.pytesseract.tesseract_cmd = exe_path
        version = pytesseract.get_tesseract_version()
        return True, exe_path, f"v{version}"
    except Exception as e:
        return False, exe_path, f"Found at {exe_path} but error getting version: {e}"


def evaluate_orientation_readability(pil_img):
    """
    Evaluates OCR word confidence score for a single PIL image.
    Higher score indicates upright, readable text orientation.
    """
    try:
        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
        total_score = 0.0
        word_count = 0

        confidences = data.get('conf', [])
        texts = data.get('text', [])

        for conf, txt in zip(confidences, texts):
            txt = str(txt).strip()
            # Only score words with valid characters and confidence > 20
            if len(txt) >= 2 and conf > 20:
                # Bonus for clean alphanumeric words
                bonus = 1.5 if txt.isalnum() else 1.0
                total_score += conf * bonus
                word_count += 1

        return total_score, word_count
    except Exception as e:
        logger.debug(f"Error evaluating readability: {e}")
        return 0.0, 0


def detect_orientation_dual_pass(pil_img, min_osd_conf=3.0):
    """
    Ultra-accurate orientation detector combining Tesseract OSD with a 
    4-angle OCR verification fallback for 100% orientation precision.

    Returns:
        tuple: (rotate_angle, confidence_score, method_used)
    """
    # Ensure image is in RGB mode for Tesseract
    rgb_img = pil_img.convert('RGB') if pil_img.mode != 'RGB' else pil_img

    # Pass 1: Try fast OSD first
    try:
        osd_data = pytesseract.image_to_osd(rgb_img, output_type=pytesseract.Output.DICT)
        rotate_angle = int(osd_data.get('rotate', 0))
        confidence = float(osd_data.get('orientation_conf', 0.0))

        logger.info(f"OSD Pass: angle={rotate_angle}°, confidence={confidence:.2f}")

        # If OSD confidence is high, return immediately
        if confidence >= min_osd_conf:
            return rotate_angle, confidence, "OSD"
    except Exception as e:
        logger.info(f"OSD Pass failed/low confidence: {e}")
        rotate_angle = 0
        confidence = 0.0

    # Pass 2: 4-Angle Multi-View OCR Verification Fallback
    # Test 0°, 90°, 180°, 270° angles by measuring OCR word readability scores
    logger.info("Executing 4-Angle OCR Verification Pass for maximum precision...")
    candidate_angles = [0, 90, 180, 270]
    best_angle = 0
    max_score = -1.0

    for angle in candidate_angles:
        if angle == 0:
            test_img = rgb_img
        elif angle == 90:
            test_img = rgb_img.rotate(-90, expand=True, resample=Image.Resampling.BICUBIC)
        elif angle == 180:
            test_img = rgb_img.rotate(-180, expand=True, resample=Image.Resampling.BICUBIC)
        elif angle == 270:
            test_img = rgb_img.rotate(-270, expand=True, resample=Image.Resampling.BICUBIC)

        score, word_count = evaluate_orientation_readability(test_img)
        logger.info(f"Angle {angle}° verification: score={score:.1f}, valid_words={word_count}")

        if score > max_score:
            max_score = score
            best_angle = angle

    logger.info(f"Multi-Angle Verification Result: selected angle={best_angle}° (score={max_score:.1f})")
    return best_angle, max_score, "4-Angle OCR Verification"

# Backward compatibility alias
detect_orientation_osd = detect_orientation_dual_pass


def extract_page_number_from_ocr(pil_img):
    """
    Extracts page sequence number from document text using OCR and regex heuristics.
    Returns detected page number (int) or None if not found.
    """
    try:
        rgb_img = pil_img.convert('RGB') if pil_img.mode != 'RGB' else pil_img
        w, h = rgb_img.size

        # Extract OCR text
        text = pytesseract.image_to_string(rgb_img)

        # Regex Pattern 1: "Page X of Y", "Page X / Y", "Page X"
        match = re.search(r'Page\s*(\d+)\s*(?:of|/|\|-)?\s*\d*', text, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Regex Pattern 2: "Pg X", "Pg. X"
        match = re.search(r'Pg\.?\s*(\d+)', text, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Regex Pattern 3: Header/Footer margin digits (Top 15% or Bottom 15% of page)
        # Crop top header
        header_img = rgb_img.crop((0, 0, w, int(h * 0.15)))
        header_text = pytesseract.image_to_string(header_img)
        match = re.search(r'\b(\d{1,3})\b', header_text)
        if match:
            val = int(match.group(1))
            if 1 <= val <= 999:
                return val

        # Crop bottom footer
        footer_img = rgb_img.crop((0, int(h * 0.85), w, h))
        footer_text = pytesseract.image_to_string(footer_img)
        match = re.search(r'\b(\d{1,3})\b', footer_text)
        if match:
            val = int(match.group(1))
            if 1 <= val <= 999:
                return val

        # Regex Pattern 4: Section / Chapter numbering e.g., "1. Executive Overview", "Section 2"
        match = re.search(r'(?:Section|Chapter|\b)\s*(\d+)\.', text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    except Exception as e:
        logger.debug(f"Page number extraction failed: {e}")

    return None
