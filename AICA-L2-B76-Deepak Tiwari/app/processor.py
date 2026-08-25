import os
import io
import uuid
import logging
import cv2
import numpy as np
import pymupdf  # PyMuPDF
from PIL import Image

from .tesseract_utils import detect_orientation_dual_pass, extract_page_number_from_ocr
from .utils import pil_to_cv2, cv2_to_pil, rotate_pil_image, create_thumbnail

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}
SUPPORTED_PDF_EXTS = {'.pdf'}


class DeskewEngine:
    """
    OpenCV-based document deskewing engine.
    Detects skew angle of text lines and rotates image with white padding.
    """

    @staticmethod
    def detect_skew_angle(cv2_bgr, max_angle=30.0):
        """
        Detects document skew angle in degrees using OpenCV contour bounding box
        and Hough line analysis.

        Returns:
            float: Detected skew angle in degrees (negative = CCW, positive = CW),
                   or 0.0 if no dominant text line detected.
        """
        try:
            gray = cv2.cvtColor(cv2_bgr, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            # Threshold / binarize
            # Inverse binary threshold: text is white (255), background is black (0)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Morphological dilation to merge text characters into horizontal text blocks/lines
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
            dilated = cv2.dilate(thresh, kernel, iterations=2)

            # Find contours
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            min_area = (w * h) * 0.0005  # Ignore small noise contours
            rect_angles = []

            for c in contours:
                area = cv2.contourArea(c)
                if area < min_area:
                    continue

                # Compute minimum area bounding box
                rect = cv2.minAreaRect(c)
                (cx, cy), (rw, rh), angle = rect

                # Standardize rectangle angle across OpenCV versions:
                if rw < rh:
                    angle = angle - 90.0 if angle > 0 else angle + 90.0
                
                # Normalize angle to [-45, 45]
                while angle > 45.0:
                    angle -= 90.0
                while angle < -45.0:
                    angle += 90.0

                if abs(angle) <= max_angle:
                    rect_angles.append(angle)

            # Hough Line Transform fallback/validation
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=w * 0.15, maxLineGap=20)

            line_angles = []
            if lines is not None:
                for line in lines:
                    coords = np.array(line).flatten()
                    if len(coords) < 4:
                        continue
                    x1, y1, x2, y2 = coords[:4]
                    dx = float(x2 - x1)
                    dy = float(y2 - y1)
                    if dx == 0:
                        continue
                    angle_rad = np.arctan2(dy, dx)
                    angle_deg = float(np.degrees(angle_rad))
                    
                    # Normalize to [-45, 45]
                    while angle_deg > 45.0:
                        angle_deg -= 90.0
                    while angle_deg < -45.0:
                        angle_deg += 90.0

                    if abs(angle_deg) <= max_angle:
                        line_angles.append(angle_deg)

            # Combine contour and Hough line metrics
            all_angles = rect_angles + line_angles

            if not all_angles:
                return 0.0

            median_angle = float(np.median(all_angles))
            logger.info(f"Deskew detection: median angle = {median_angle:.2f}° from {len(all_angles)} samples")

            if abs(median_angle) > max_angle:
                return 0.0

            return median_angle

        except Exception as e:
            logger.warning(f"Error in OpenCV deskew detection: {e}")
            return 0.0

    @staticmethod
    def deskew_image(pil_img, max_angle=30.0, min_threshold=0.3):
        """
        Deskews PIL Image if detected skew angle > min_threshold.
        Returns (deskewed_pil_image, float_skew_angle)
        """
        cv2_img = pil_to_cv2(pil_img)
        skew_angle = DeskewEngine.detect_skew_angle(cv2_img, max_angle=max_angle)

        if abs(skew_angle) < min_threshold:
            return pil_img, 0.0

        h, w = cv2_img.shape[:2]
        center = (w // 2, h // 2)

        # Get rotation matrix for OpenCV (negative angle for OpenCV rotates clockwise)
        M = cv2.getRotationMatrix2D(center, skew_angle, 1.0)

        # Calculate new bounding dimensions so corners aren't truncated
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        # Adjust the translation in matrix
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]

        # Perform affine transformation with white background padding
        rotated = cv2.warpAffine(
            cv2_img, M, (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )

        return cv2_to_pil(rotated), skew_angle


class DocumentItem:
    """Represents a single document page item in the processing queue."""

    def __init__(self, file_path, page_num=0, total_pages=1, original_pil_img=None):
        self.id = str(uuid.uuid4())
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.page_num = page_num  # 0-indexed page
        self.total_pages = total_pages

        self.original_image = original_pil_img
        self.processed_image = None
        self.thumbnail_image = None

        self.auto_rotate_angle = 0   # 0, 90, 180, 270 (from OCR)
        self.manual_rotate_angle = 0 # 0, 90, 180, 270 (user override)
        self.deskew_angle = 0.0      # Fine skew angle in degrees
        self.detected_page_seq = None # AI Extracted page sequence number

        self.status = "Ready"        # "Ready", "Processing", "Done", "Error"
        self.error_message = None

        if self.original_image is not None:
            self.thumbnail_image = create_thumbnail(self.original_image)

    @property
    def display_name(self):
        prefix = f"[P.{self.detected_page_seq}] " if self.detected_page_seq is not None else ""
        if self.total_pages > 1:
            return f"{prefix}{self.file_name} (Page {self.page_num + 1}/{self.total_pages})"
        return f"{prefix}{self.file_name}"

    @property
    def total_rotation_angle(self):
        """Combined rotation (Auto-rotate + Manual rotation) modulo 360."""
        return (self.auto_rotate_angle + self.manual_rotate_angle) % 360


COMPRESSION_PRESETS = {
    "Balanced (Recommended)": {
        "max_dim": 1920,
        "jpeg_quality": 75,
        "convert_grayscale": False
    },
    "High Quality": {
        "max_dim": 2600,
        "jpeg_quality": 88,
        "convert_grayscale": False
    },
    "Smallest File (Max Compression)": {
        "max_dim": 1400,
        "jpeg_quality": 60,
        "convert_grayscale": False
    },
    "Original Size (No Compression)": {
        "max_dim": None,
        "jpeg_quality": 95,
        "convert_grayscale": False
    }
}


class DocumentProcessor:
    """Document loader, auto-rotator, deskewer, and PDF exporter."""

    @staticmethod
    def load_file(file_path):
        """
        Loads a file (PDF or Image) and returns a list of DocumentItem objects.
        """
        ext = os.path.splitext(file_path)[1].lower()
        items = []

        if ext in SUPPORTED_PDF_EXTS:
            try:
                doc = pymupdf.open(file_path)
                total_pages = len(doc)
                for page_idx in range(total_pages):
                    page = doc.load_page(page_idx)
                    # Render page to high-res image (300 DPI -> matrix zoom 300/72 ~ 4.16)
                    pix = page.get_pixmap(dpi=200)
                    mode = "RGB" if pix.alpha == 0 else "RGBA"
                    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                    if mode == "RGBA":
                        # Convert RGBA to RGB with white background
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[3])
                        img = bg

                    item = DocumentItem(file_path, page_num=page_idx, total_pages=total_pages, original_pil_img=img)
                    items.append(item)
                doc.close()
            except Exception as e:
                logger.error(f"Failed to load PDF file '{file_path}': {e}")
                raise RuntimeError(f"Could not open PDF file '{os.path.basename(file_path)}': {e}")

        elif ext in SUPPORTED_IMAGE_EXTS:
            try:
                img = Image.open(file_path)
                img.load() # Load image data into memory
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                item = DocumentItem(file_path, page_num=0, total_pages=1, original_pil_img=img)
                items.append(item)
            except Exception as e:
                logger.error(f"Failed to load image file '{file_path}': {e}")
                raise RuntimeError(f"Could not open image file '{os.path.basename(file_path)}': {e}")
        else:
            raise ValueError(f"Unsupported file format: '{ext}'")

        return items

    @staticmethod
    def process_item(item, do_auto_rotate=True, do_deskew=True, min_osd_conf=3.0, deskew_threshold=0.3):
        """
        Processes a single DocumentItem:
        1. Auto-rotates using Dual-Pass Tesseract OSD + 4-Angle OCR verification.
        2. Fine deskews using OpenCV.
        3. Applies manual rotation override.
        4. Extracts page sequence number via AI OCR.
        """
        item.status = "Processing"
        try:
            curr_img = item.original_image.copy()

            # Step 1: Ultra-Accurate Dual-Pass Auto-Rotation (OSD + 4-Angle Verification)
            if do_auto_rotate:
                auto_angle, score, method = detect_orientation_dual_pass(curr_img, min_osd_conf=min_osd_conf)
                item.auto_rotate_angle = auto_angle
                if auto_angle != 0:
                    curr_img = rotate_pil_image(curr_img, auto_angle)
            else:
                item.auto_rotate_angle = 0

            # Step 2: Deskewing via OpenCV
            if do_deskew:
                curr_img, skew_deg = DeskewEngine.deskew_image(curr_img, min_threshold=deskew_threshold)
                item.deskew_angle = skew_deg
            else:
                item.deskew_angle = 0.0

            # Step 3: Manual rotation override (if user clicked Rotate CW/CCW buttons)
            if item.manual_rotate_angle != 0:
                curr_img = rotate_pil_image(curr_img, item.manual_rotate_angle)

            # Step 4: Extract page sequence number via OCR text analysis
            item.detected_page_seq = extract_page_number_from_ocr(curr_img)

            item.processed_image = curr_img
            item.thumbnail_image = create_thumbnail(curr_img)
            item.status = "Done"
            item.error_message = None

        except Exception as e:
            logger.error(f"Error processing item '{item.display_name}': {e}", exc_info=True)
            item.status = "Error"
            item.error_message = str(e)
            item.processed_image = item.original_image.copy()

        return item

    @staticmethod
    def auto_arrange_items(items):
        """
        Sorts document items automatically in ascending order of detected OCR page numbers.
        Returns (sorted_items, count_reordered).
        """
        indexed_items = []
        for idx, item in enumerate(items):
            # Ensure page sequence is extracted
            if item.detected_page_seq is None:
                img = item.processed_image if item.processed_image is not None else item.original_image
                if img is not None:
                    item.detected_page_seq = extract_page_number_from_ocr(img)

            seq = item.detected_page_seq if item.detected_page_seq is not None else (999900 + idx)
            indexed_items.append((seq, idx, item))

        # Sort primary by detected page number, secondary by original position
        indexed_items.sort(key=lambda x: (x[0], x[1]))
        sorted_items = [x[2] for x in indexed_items]

        # Check how many items changed position
        reordered_count = sum(1 for i, orig in enumerate(items) if sorted_items[i].id != orig.id)
        return sorted_items, reordered_count

    @staticmethod
    def export_pdf(items, output_pdf_path, do_auto_rotate=True, do_deskew=True, compression_preset="Balanced (Recommended)", progress_callback=None):
        """
        Processes all items (if not already processed) and saves as a compressed merged PDF file.
        Returns dict with output_path, final_file_size, and compression_stats.
        """
        if not items:
            raise ValueError("No document pages to export.")

        preset = COMPRESSION_PRESETS.get(compression_preset, COMPRESSION_PRESETS["Balanced (Recommended)"])
        max_dim = preset["max_dim"]
        quality = preset["jpeg_quality"]

        pdf_doc = pymupdf.open()

        for idx, item in enumerate(items):
            if progress_callback:
                progress_callback(idx + 1, len(items), f"Compressing & Merging Page {idx + 1}/{len(items)}: {item.display_name}")

            # Process item if not done
            if item.processed_image is None or item.status != "Done":
                DocumentProcessor.process_item(item, do_auto_rotate=do_auto_rotate, do_deskew=do_deskew)

            img = item.processed_image.copy()

            # Downsample dimension if max_dim is set
            if max_dim:
                w, h = img.size
                if max(w, h) > max_dim:
                    ratio = max_dim / float(max(w, h))
                    new_w = max(1, int(w * ratio))
                    new_h = max(1, int(h * ratio))
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Compress to JPEG byte stream
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            img_bytes = buffer.getvalue()

            # Create a PyMuPDF page matching image dimension
            w, h = img.size
            page = pdf_doc.new_page(width=w, height=h)
            rect = pymupdf.Rect(0, 0, w, h)
            page.insert_image(rect, stream=img_bytes)

        # Save merged PDF with stream deflation and garbage collection
        pdf_doc.save(output_pdf_path, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True)
        pdf_doc.close()

        final_size = os.path.getsize(output_pdf_path)
        logger.info(f"Successfully exported compressed merged PDF ({len(items)} pages, size={final_size / 1024 / 1024:.2f} MB) to '{output_pdf_path}'")
        
        return {
            "output_path": output_pdf_path,
            "final_size": final_size,
            "page_count": len(items)
        }
