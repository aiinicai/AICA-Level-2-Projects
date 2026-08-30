import logging
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.models.extraction_result import ExtractionResult, RawPage, RawWord
from app.services.ocr_eligibility_service import OcrEligibilityService
from app.services.ocr_engine_service import OcrEngineService
from app.services.job_state_service import get_job
from app.services.profile_manager import ProfileManager

logger = logging.getLogger(__name__)

class OcrService:
    def __init__(self, config):
        self.config = config
        temp_dir = self.config.get('paths', 'temp', fallback='temp')
        self.jobs_dir = Path(temp_dir) / 'jobs'
        self.eligibility_svc = OcrEligibilityService(config)
        self.engine_svc = OcrEngineService(config)
        
    def _get_job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id
        
    def _get_ocr_dir(self, job_id: str) -> Path:
        ocr_dir = self._get_job_dir(job_id) / "ocr"
        ocr_dir.mkdir(exist_ok=True, parents=True)
        return ocr_dir

    def run_ocr(self, job_id: str, extraction_result: ExtractionResult, force_pages: list = None, cancel_event=None) -> str:
        """Run OCR on eligible pages and produce ocr_result.json and effective_extraction.json.
        Returns one of: OCR_COMPLETE, OCR_PARTIAL, OCR_CANCELLED, OCR_PAGE_LIMIT_EXCEEDED, OCR_FAILED.
        """
        from app.services.pdf_intake_service import get_job_pdf_path
        # Load PDF path
        pdf_path = get_job_pdf_path(job_id, self.config)
        if not pdf_path or not pdf_path.exists():
            logger.error(f"Source PDF missing for job {job_id}")
            return "OCR_FAILED"

        assessments = self.eligibility_svc.assess_job(extraction_result)

        pages_to_ocr = []
        if force_pages:
            pages_to_ocr = force_pages
        else:
            for page_ast in assessments.get('pages', []):
                if page_ast['status'] == 'OCR_REQUIRED':
                    pages_to_ocr.append(page_ast['page_number'])

        if not pages_to_ocr:
            logger.info("No pages require OCR.")
            return "OCR_COMPLETE"

        # Max page guard from config
        max_pages = self.config.getint('ocr', 'max_pages', fallback=250)
        if len(pages_to_ocr) > max_pages:
            logger.error(f"Requested OCR pages ({len(pages_to_ocr)}) exceed max_pages ({max_pages})")
            return "OCR_PAGE_LIMIT_EXCEEDED"

        logger.info(f"Starting OCR for job {job_id}, pages: {pages_to_ocr}")

        low_conf_count = 0
        pages_completed = 0
        failed_pages = set()
        ocr_pages = []

        for page_num in pages_to_ocr:
            # Cancellation check before processing each page
            if cancel_event and cancel_event.is_set():
                logger.info(f"OCR cancelled for job {job_id} before page {page_num}")
                return "OCR_CANCELLED"
            # find original page dims
            orig_page = next((p for p in extraction_result.pages if p.page_number == page_num), None)
            if not orig_page:
                continue
            try:
                job_data = get_job(self.config, job_id)
                prof_id = job_data.get('profile_id') if job_data else None
                roi_bbox = None
                if prof_id:
                    pm = ProfileManager(self.config)
                    prof = pm.get_profile(prof_id)
                    if prof:
                        if page_num == 1 and prof.table_bbox:
                            roi_bbox = (max(0, prof.table_bbox.x0 - 20), max(0, prof.table_bbox.top - 20), min(orig_page.width, prof.table_bbox.x1 + 20), min(orig_page.height, prof.table_bbox.bottom + 20))
                        elif page_num > 1 and prof.continuation_table_bbox:
                            roi_bbox = (max(0, prof.continuation_table_bbox.x0 - 20), max(0, prof.continuation_table_bbox.top - 20), min(orig_page.width, prof.continuation_table_bbox.x1 + 20), min(orig_page.height, prof.continuation_table_bbox.bottom + 20))
                            
                # Pass 1: 150 DPI
                words_dict, raw_text = self.engine_svc.ocr_page(
                    str(pdf_path),
                    page_num,
                    orig_page.width,
                    orig_page.height,
                    roi_bbox=roi_bbox,
                    dpi=150
                )
                
                # Check confidence
                pass1_low = sum(1 for w in words_dict if w['confidence'] < self.engine_svc.min_confidence)
                if len(words_dict) > 0 and (pass1_low / len(words_dict)) > 0.15:
                    logger.info(f"Page {page_num} pass 1 low confidence {pass1_low}/{len(words_dict)}. Rerunning at 300 DPI.")
                    words_dict, raw_text = self.engine_svc.ocr_page(
                        str(pdf_path),
                        page_num,
                        orig_page.width,
                        orig_page.height,
                        roi_bbox=roi_bbox,
                        dpi=300
                    )

                page_low_conf_count = 0
                word_objects = []
                for w in words_dict:
                    if w["confidence"] < self.engine_svc.min_confidence:
                        page_low_conf_count += 1
                        low_conf_count += 1
                    word_objects.append(RawWord(
                        text=w["text"],
                        x0=w["x0"], x1=w["x1"],
                        top=w["top"], bottom=w["bottom"],
                        page_number=page_num,
                        source_type="OCR",
                        confidence=w["confidence"],
                    ))
                page_warnings = []
                if page_low_conf_count > 0:
                    page_warnings.append("LOW_OCR_CONFIDENCE")
                
                ocr_pages.append(RawPage(
                    page_number=page_num,
                    width=orig_page.width,
                    height=orig_page.height,
                    raw_text=raw_text,
                    word_count=len(word_objects),
                    character_count=len(raw_text),
                    source_type="OCR",
                    words=word_objects,
                    table_candidates=[],
                    warnings=page_warnings,
                ))
                pages_completed += 1
            except Exception as e:
                logger.error(f"Failed to OCR page {page_num}: {e}")
                failed_pages.add(page_num)
                ocr_pages.append(RawPage(
                    page_number=page_num,
                    width=orig_page.width,
                    height=orig_page.height,
                    raw_text="",
                    word_count=0,
                    character_count=0,
                    source_type="OCR_FAILED",
                    words=[],
                    warnings=[f"OCR Failed: {str(e)}"],
                ))

        # Write OCR result
        ocr_result_path = self._get_ocr_dir(job_id) / "ocr_result.json"
        ocr_res_dict = {
            "job_id": job_id,
            "ocr_engine": "rapidocr-onnxruntime",
            "ocr_engine_version": "1.2.3",
            "pages_requested": len(pages_to_ocr),
            "pages_completed": pages_completed,
            "low_confidence_word_count": low_conf_count,
            "completed_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "pages": [p.__dict__ for p in ocr_pages],
        }
        # fix nested words for JSON serialization
        for p_dict in ocr_res_dict["pages"]:
            if "words" in p_dict:
                p_dict["words"] = [w.__dict__ if hasattr(w, "__dict__") else w for w in p_dict["words"]]
        with open(ocr_result_path, "w", encoding="utf-8") as f:
            json.dump(ocr_res_dict, f, indent=2)

        # Write Effective Extraction (only OCR pages are merged)
        self._generate_effective_extraction(job_id, extraction_result, ocr_pages)

        # Determine overall status
        if cancel_event and cancel_event.is_set():
            return "OCR_CANCELLED"
        if failed_pages:
            return "OCR_PARTIAL"
        return "OCR_COMPLETE"

    def _generate_effective_extraction(self, job_id: str, orig_extraction: ExtractionResult, ocr_pages: list):
        effective_pages = []
        ocr_page_map = {p.page_number: p for p in ocr_pages if p.source_type == "OCR"}
        
        for orig_page in orig_extraction.pages:
            if orig_page.page_number in ocr_page_map:
                effective_pages.append(ocr_page_map[orig_page.page_number])
            else:
                effective_pages.append(orig_page)
                
        # Clone original extraction and replace pages
        import copy
        effective_ext = copy.deepcopy(orig_extraction)
        effective_ext.pages = effective_pages
        
        eff_path = self._get_ocr_dir(job_id) / "effective_extraction.json"
        with open(eff_path, 'w', encoding='utf-8') as f:
            json.dump(effective_ext.to_dict(), f, indent=2)
