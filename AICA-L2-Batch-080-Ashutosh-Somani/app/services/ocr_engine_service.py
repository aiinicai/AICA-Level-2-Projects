import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path
import pypdfium2 as pdfium
import numpy as np
import threading

logger = logging.getLogger(__name__)

_global_ocr_engine = None
_ocr_engine_lock = threading.Lock()

class OcrEngineService:
    def __init__(self, config):
        self.config = config
        self.render_dpi = self.config.getint('ocr', 'render_dpi', fallback=250)
        self.min_confidence = self.config.getint('ocr', 'minimum_word_confidence', fallback=70)
        
        # Lazy load to avoid importing if disabled
        self._ocr = None
        
    def _get_engine(self):
        global _global_ocr_engine
        if _global_ocr_engine is None:
            with _ocr_engine_lock:
                if _global_ocr_engine is None:
                    try:
                        from rapidocr_onnxruntime import RapidOCR
                        # Use conservative thread settings for ONNX Runtime to avoid oversubscription
                        _global_ocr_engine = RapidOCR(text_score=0.1)
                    except ImportError as e:
                        logger.error(f"RapidOCR import failed: {e}")
                        raise RuntimeError("OCR engine missing")
        return _global_ocr_engine

    def ocr_page(self, pdf_path: str, page_number: int, pdf_page_width: float, pdf_page_height: float, roi_bbox: tuple = None, dpi: int = None) -> Tuple[List[Dict[str, Any]], str]:
        """
        Renders a specific page, OCRs it, and maps coordinates back to PDF space.
        Returns (words, raw_text)
        """
        engine = self._get_engine()
        
        # 1. Render page to image in memory
        try:
            pdf = pdfium.PdfDocument(pdf_path)
            # pypdfium2 is 0-indexed, so page_number - 1
            page = pdf[page_number - 1]
            
            # Use fixed scale based on desired DPI. 72 DPI is standard PDF scale (1.0).
            scale = (dpi or self.render_dpi) / 72.0
            bitmap = page.render(
                scale=scale,
                rotation=0,
            )
            pil_image = bitmap.to_pil()
            img_array = np.array(pil_image)
            
            rendered_width = pil_image.width
            rendered_height = pil_image.height
            
            # Close resources
            page.close()
            pdf.close()
        except Exception as e:
            logger.error(f"Page rendering failed for page {page_number}: {e}")
            raise
            
        # If roi_bbox is provided, crop the image array
        roi_x0, roi_y0 = 0, 0
        if roi_bbox:
            # roi_bbox is in PDF coordinates: (x0, top, x1, bottom)
            rx0, rtop, rx1, rbot = roi_bbox
            # scale to image coordinates
            img_rx0 = int(max(0, rx0 * (rendered_width / pdf_page_width)))
            img_rx1 = int(min(rendered_width, rx1 * (rendered_width / pdf_page_width)))
            img_rtop = int(max(0, rtop * (rendered_height / pdf_page_height)))
            img_rbot = int(min(rendered_height, rbot * (rendered_height / pdf_page_height)))
            
            img_array = img_array[img_rtop:img_rbot, img_rx0:img_rx1]
            roi_x0 = img_rx0
            roi_y0 = img_rtop
            
        # 2. Run OCR (under lock to prevent concurrent ONNX crashing)
        try:
            with _ocr_engine_lock:
                ocr_res, _ = engine(img_array)
        except Exception as e:
            logger.error(f"OCR inference failed for page {page_number}: {e}")
            raise
            
        words = []
        raw_text_lines = []
        
        if not ocr_res:
            return words, ""
            
        # 3. Process and scale coordinates
        scale_x = pdf_page_width / rendered_width
        scale_y = pdf_page_height / rendered_height
        
        for dt_box, rec_res, score in ocr_res:
            # rapidocr returns confidence 0.0 - 1.0. We normalize to 0-100
            confidence = round(float(score) * 100, 2)
            
            # dt_box is [tl, tr, br, bl]
            x_coords = [p[0] for p in dt_box]
            y_coords = [p[1] for p in dt_box]
            
            img_x0, img_x1 = min(x_coords) + roi_x0, max(x_coords) + roi_x0
            img_y0, img_y1 = min(y_coords) + roi_y0, max(y_coords) + roi_y0
            
            # Map back to PDF space
            pdf_x0 = img_x0 * scale_x
            pdf_x1 = img_x1 * scale_x
            pdf_top = img_y0 * scale_y
            pdf_bottom = img_y1 * scale_y
            
            # Safety bounds
            pdf_x0 = max(0.0, min(pdf_x0, pdf_page_width))
            pdf_x1 = max(0.0, min(pdf_x1, pdf_page_width))
            pdf_top = max(0.0, min(pdf_top, pdf_page_height))
            pdf_bottom = max(0.0, min(pdf_bottom, pdf_page_height))
            
            words.append({
                "text": rec_res,
                "x0": pdf_x0,
                "x1": pdf_x1,
                "top": pdf_top,
                "bottom": pdf_bottom,
                "confidence": confidence,
                "source_type": "OCR"
            })
            raw_text_lines.append(rec_res)
            
        return words, "\n".join(raw_text_lines)
