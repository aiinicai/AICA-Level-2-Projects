from typing import Dict, Any, List
import logging
from app.models.extraction_result import ExtractionResult, RawPage

logger = logging.getLogger(__name__)

class OcrEligibilityService:
    def __init__(self, config):
        self.config = config
        self.ocr_enabled = self.config.getboolean('ocr', 'enabled', fallback=False)
        self.word_threshold = self.config.getint('ocr', 'limited_text_word_threshold', fallback=20)
        
    def assess_job(self, extraction_result: ExtractionResult) -> Dict[str, Any]:
        page_assessments = []
        requires_ocr_count = 0
        
        if not self.ocr_enabled:
            return {
                "overall_status": "OCR_DISABLED",
                "requires_ocr_count": 0,
                "pages": []
            }

        for page in extraction_result.pages:
            if page.word_count < self.word_threshold:
                status = "OCR_REQUIRED"
                requires_ocr_count += 1
            else:
                status = "DIGITAL_USABLE"
                
            page_assessments.append({
                "page_number": page.page_number,
                "status": status,
                "word_count": page.word_count
            })
            
        overall_status = "OCR_NOT_NEEDED"
        if requires_ocr_count == len(extraction_result.pages) and requires_ocr_count > 0:
            overall_status = "OCR_REQUIRED"
        elif requires_ocr_count > 0:
            overall_status = "MIXED_PDF_OCR_REQUIRED"

        return {
            "overall_status": overall_status,
            "requires_ocr_count": requires_ocr_count,
            "pages": page_assessments
        }
