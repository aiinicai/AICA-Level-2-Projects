import pdfplumber
import configparser
import logging
from typing import Dict, Any
from app.extractors.base_extractor import BaseExtractor
from app.models.extraction_result import ExtractionResult, RawPage, RawWord, RawTableCandidate

logger = logging.getLogger(__name__)

class PdfPlumberExtractor(BaseExtractor):
    @property
    def name(self) -> str:
        return "pdfplumber"

    @property
    def version(self) -> str:
        return pdfplumber.__version__

    def can_handle(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        # pdfplumber can generally handle any unlocked PDF
        return True

    def extract(self, job_id: str, file_path: str, config: configparser.ConfigParser) -> ExtractionResult:
        result = ExtractionResult(
            job_id=job_id,
            extractor_used=self.name,
            extractor_version=self.version,
            status="extracting",
            page_count=0,
            pages_processed=0,
            total_words=0,
            total_characters=0,
            text_layer_status="uncertain",
            table_candidate_count=0
        )
        
        try:
            with pdfplumber.open(file_path) as pdf:
                result.page_count = len(pdf.pages)
                
                for i, page in enumerate(pdf.pages):
                    page_num = i + 1
                    raw_text = page.extract_text() or ""
                    
                    # Extract words
                    plumber_words = page.extract_words(
                        x_tolerance=3, 
                        y_tolerance=3, 
                        keep_blank_chars=False, 
                        use_text_flow=False, 
                        horizontal_ltr=True, 
                        vertical_ttb=True
                    )
                    
                    words = []
                    for w in plumber_words:
                        words.append(RawWord(
                            text=w['text'],
                            x0=float(w['x0']),
                            x1=float(w['x1']),
                            top=float(w['top']),
                            bottom=float(w['bottom']),
                            page_number=page_num
                        ))
                        
                    # Extract table candidates (generic)
                    table_candidates = []
                    plumber_tables = page.find_tables()
                    for t in plumber_tables:
                        cells = t.extract(x_tolerance=3, y_tolerance=3)
                        table_candidates.append(RawTableCandidate(
                            page_number=page_num,
                            bbox=t.bbox,
                            row_count=len(cells) if cells else 0,
                            column_count=max((len(row) for row in cells if row), default=0),
                            detection_method="pdfplumber.find_tables()",
                            cells=cells
                        ))
                    
                    raw_page = RawPage(
                        page_number=page_num,
                        width=float(page.width),
                        height=float(page.height),
                        raw_text=raw_text,
                        word_count=len(words),
                        character_count=len(raw_text),
                        words=words,
                        table_candidates=table_candidates
                    )
                    
                    result.pages.append(raw_page)
                    result.pages_processed += 1
                    result.total_words += raw_page.word_count
                    result.total_characters += raw_page.character_count
                    result.table_candidate_count += len(table_candidates)
                    
                result.status = "success"
                
                # Diagnostic Text-Layer Classification
                if result.total_words == 0:
                    result.text_layer_status = "none"
                    result.warnings.append("No usable digital text was detected. This statement can be processed using local OCR. Processing remains on this computer.")
                elif result.total_words < result.page_count * 20: # heuristic: < 20 words per page avg
                    result.text_layer_status = "limited"
                else:
                    result.text_layer_status = "usable"
                    
        except Exception as e:
            logger.error(f"pdfplumber extraction failed for {job_id}: {e}")
            result.status = "failed"
            result.warnings.append(str(e))
            
        return result
