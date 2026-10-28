"""
PDF Processing Engine with Native MuPDF & Tesseract OCR Support
Preserves page-level mapping and handles scanned, digital, and hybrid PDFs offline.
"""
import io
import os
import re
from typing import Dict, List, Optional, Tuple, Union
from PIL import Image, ImageEnhance, ImageFilter
import pymupdf  # PyMuPDF
import pytesseract
from modules.config import TESSERACT_SEARCH_PATHS

class PDFProcessor:
    def __init__(self, custom_tesseract_cmd: Optional[str] = None):
        self.tesseract_cmd = self._resolve_tesseract(custom_tesseract_cmd)
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def _resolve_tesseract(self, custom_path: Optional[str]) -> Optional[str]:
        """Resolves Tesseract executable path on Windows."""
        if custom_path and os.path.isfile(custom_path):
            return custom_path
        
        for p in TESSERACT_SEARCH_PATHS:
            expanded = os.path.expandvars(p)
            if os.path.isfile(expanded):
                return expanded
            # Also test if available in system PATH
            if p == "tesseract":
                try:
                    # quick check
                    pytesseract.get_tesseract_version()
                    return "tesseract"
                except Exception:
                    pass
        return None

    def is_tesseract_available(self) -> bool:
        """Returns True if Tesseract OCR is operational."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def process_pdf(
        self,
        pdf_input: Union[str, bytes, io.BytesIO],
        password: Optional[str] = None,
        force_ocr: bool = False,
        dpi: int = 200
    ) -> Dict:
        """
        Processes a PDF, detecting scanned pages and running local OCR if needed.
        
        Returns:
            dict containing:
                - success: bool
                - pages: Dict[int, str] (1-indexed page text)
                - full_text: str
                - page_count: int
                - is_scanned: bool
                - page_types: Dict[int, str] ("text", "scanned", "empty")
                - ocr_applied: bool
                - warnings: List[str]
                - error: Optional[str]
        """
        results = {
            "success": False,
            "pages": {},
            "full_text": "",
            "page_count": 0,
            "is_scanned": False,
            "page_types": {},
            "ocr_applied": False,
            "warnings": [],
            "error": None
        }

        try:
            # Load PDF document
            if isinstance(pdf_input, str):
                if not os.path.exists(pdf_input):
                    results["error"] = f"File not found: {pdf_input}"
                    return results
                doc = pymupdf.open(pdf_input)
            elif isinstance(pdf_input, bytes):
                doc = pymupdf.open(stream=pdf_input, filetype="pdf")
            elif isinstance(pdf_input, io.BytesIO):
                doc = pymupdf.open(stream=pdf_input.getvalue(), filetype="pdf")
            else:
                results["error"] = "Unsupported PDF input type."
                return results

            # Check for encryption
            if doc.is_encrypted:
                if password:
                    if not doc.authenticate(password):
                        results["error"] = "Incorrect PDF password provided."
                        return results
                else:
                    # Try empty password
                    if not doc.authenticate(""):
                        results["error"] = "PDF is password-protected. Please provide a decryption password."
                        return results
                    else:
                        results["warnings"].append("PDF was encrypted with a default empty password.")

            page_count = len(doc)
            results["page_count"] = page_count

            if page_count == 0:
                results["error"] = "The PDF contains 0 pages."
                return results

            total_chars = 0
            scanned_pages_count = 0
            ocr_needed = False

            for page_index in range(page_count):
                page_num = page_index + 1
                page = doc[page_index]
                
                # Extract native text
                native_text = page.get_text("text").strip()
                char_count = len(native_text)
                total_chars += char_count

                is_page_scanned = (char_count < 60) or force_ocr

                if is_page_scanned:
                    results["page_types"][page_num] = "scanned"
                    scanned_pages_count += 1
                    ocr_needed = True
                else:
                    results["page_types"][page_num] = "text"
                    results["pages"][page_num] = self._clean_text(native_text)

            # Determine document scan status
            if scanned_pages_count == page_count:
                results["is_scanned"] = True
            elif scanned_pages_count > 0:
                results["is_scanned"] = True
                results["warnings"].append(f"Hybrid PDF detected: {scanned_pages_count} of {page_count} pages appear to be scanned images.")
            else:
                results["is_scanned"] = False

            # If OCR is required for any scanned page
            if ocr_needed:
                tesseract_ready = self.is_tesseract_available()
                if not tesseract_ready:
                    results["warnings"].append(
                        "Tesseract OCR is not installed or configured. Scanned pages could not be transcribed. "
                        "Please configure Tesseract in Settings or install from https://github.com/UB-Mannheim/tesseract/wiki"
                    )
                    # For pages without OCR, keep native text if any
                    for page_index in range(page_count):
                        page_num = page_index + 1
                        if page_num not in results["pages"]:
                            results["pages"][page_num] = self._clean_text(doc[page_index].get_text("text"))
                else:
                    results["ocr_applied"] = True
                    for page_index in range(page_count):
                        page_num = page_index + 1
                        if results["page_types"][page_num] == "scanned" or force_ocr:
                            page = doc[page_index]
                            # Render to high-DPI image natively via MuPDF without poppler
                            pix = page.get_pixmap(dpi=dpi)
                            img = Image.open(io.BytesIO(pix.tobytes("png")))
                            
                            # Preprocess image for OCR quality
                            processed_img = self._preprocess_for_ocr(img)
                            ocr_text = pytesseract.image_to_string(processed_img, config='--psm 1')
                            
                            cleaned_ocr = self._clean_text(ocr_text)
                            if not cleaned_ocr and native_text:
                                cleaned_ocr = native_text
                            
                            results["pages"][page_num] = cleaned_ocr

            # Build full consolidated text with page bookmarks
            combined = []
            for p_num in range(1, page_count + 1):
                p_text = results["pages"].get(p_num, "")
                combined.append(f"--- [PAGE {p_num}] ---\n{p_text}")
            
            results["full_text"] = "\n\n".join(combined)
            results["success"] = True

        except Exception as ex:
            results["error"] = f"Error processing PDF: {str(ex)}"
        finally:
            if 'doc' in locals() and doc:
                doc.close()

        return results

    def _preprocess_for_ocr(self, img: Image.Image) -> Image.Image:
        """Enhances image contrast and binarizes for superior OCR accuracy."""
        try:
            # Convert to grayscale
            gray = img.convert('L')
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(1.8)
            # Sharpen edges
            sharpened = enhanced.filter(ImageFilter.SHARPEN)
            return sharpened
        except Exception:
            return img

    def _clean_text(self, text: str) -> str:
        """Cleans and standardizes extracted text while preserving punctuation and paragraph flow."""
        if not text:
            return ""
        # Normalize carriage returns and non-breaking spaces
        text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\u00a0', ' ')
        # Replace multiple horizontal spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Normalize excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
