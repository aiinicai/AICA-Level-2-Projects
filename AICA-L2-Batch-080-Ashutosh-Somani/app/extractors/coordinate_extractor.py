import logging
from typing import List, Dict, Any, Tuple
from app.models.profile import BankProfile
from app.models.extraction_result import ExtractionResult, RawTableCandidate, RawWord

logger = logging.getLogger(__name__)

class CoordinateExtractor:
    def __init__(self, profile: BankProfile):
        self.profile = profile

    def extract(self, extraction_result: ExtractionResult) -> ExtractionResult:
        """
        Takes an existing ExtractionResult (from Stage 3), uses its RawWords,
        and re-builds table_candidates based on the BankProfile layout.
        Returns a mutated ExtractionResult.
        """
        if not self.profile.column_definitions:
            logger.warning("No column definitions in profile.")
            return extraction_result
            
        columns = sorted(self.profile.column_definitions, key=lambda c: c.x0)
        
        table_candidates = []
        
        for page in extraction_result.pages:
            if page.page_number == 1:
                table_bbox = self.profile.table_bbox
            else:
                table_bbox = self.profile.continuation_table_bbox
                if not table_bbox and self.profile.table_bbox:
                    # Structural fallback: find first valid date in date column
                    from app.models.profile import TableRegion
                    from app.utils.date_utils import parse_date
                    
                    dynamic_top = 0
                    date_col = next((c for c in columns if 'date' in (c.canonical_name or '').lower() and 'value' not in (c.canonical_name or '').lower()), None)
                    
                    if date_col:
                        date_words = [w for w in page.words if date_col.x0 <= (w.x0 + w.x1) / 2.0 <= date_col.x1]
                        date_words.sort(key=lambda w: w.top)
                        for dw in date_words:
                            parsed, status = parse_date(dw.text)
                            if parsed and status == 'success':
                                dynamic_top = max(0, dw.top - self.profile.row_y_tolerance - 2)
                                break
                    
                    if not dynamic_top:
                        dynamic_top = page.height * 0.05
                        
                    table_bbox = TableRegion(
                        x0=self.profile.table_bbox.x0,
                        top=dynamic_top,
                        x1=self.profile.table_bbox.x1,
                        bottom=self.profile.table_bbox.bottom
                    )
            
            # Filter words to only those in table bbox
            valid_words = page.words
            if table_bbox and table_bbox.x1 > 0 and table_bbox.bottom > 0:
                valid_words = []
                for w in page.words:
                    # Require at least 50% of the word to be inside the table_bbox vertically
                    overlap_top = max(w.top, table_bbox.top)
                    overlap_bottom = min(w.bottom, table_bbox.bottom)
                    overlap_h = overlap_bottom - overlap_top
                    w_h = w.bottom - w.top
                    if w_h > 0 and (overlap_h / w_h) >= 0.5:
                        valid_words.append(w)
            
            if not valid_words:
                continue
                
            # Group words by row using row_y_tolerance and dynamic median height
            import statistics
            heights = [(w.bottom - w.top) for w in valid_words if w.bottom > w.top]
            median_h = statistics.median(heights) if heights else 10.0
            
            # Use max of profile tolerance and ~40% of median height to be safe
            dynamic_tolerance = max(self.profile.row_y_tolerance, median_h * 0.4)
            
            valid_words.sort(key=lambda w: w.top)
            
            rows = []
            current_row = []
            current_top = None
            current_bottom = None
            
            for w in valid_words:
                if not current_row:
                    current_row.append(w)
                    current_top = w.top
                    current_bottom = w.bottom
                else:
                    cy = (w.top + w.bottom) / 2.0
                    # if center of word falls within the expanded vertical bounds of current row
                    if (current_top - dynamic_tolerance) <= cy <= (current_bottom + dynamic_tolerance):
                        current_row.append(w)
                        current_top = min(current_top, w.top)
                        current_bottom = max(current_bottom, w.bottom)
                    else:
                        rows.append(current_row)
                        current_row = [w]
                        current_top = w.top
                        current_bottom = w.bottom
            if current_row:
                rows.append(current_row)
                
            # Now assign to columns
            cells = []
            
            # Add header row explicitly for the TransactionNormalizer to map
            header_row = [c.canonical_name for c in columns]
            cells.append(header_row)
            
            physical_rows = []
            for row_words in rows:
                row_cells = [""] * len(columns)
                
                # Sort words horizontally first to prevent jumbled OCR concatenation
                row_words.sort(key=lambda w: w.x0)
                
                for w in row_words:
                    best_col_idx = -1
                    best_overlap = 0
                    w_width = w.x1 - w.x0
                    center_x = (w.x0 + w.x1) / 2
                    
                    for i, col in enumerate(columns):
                        # Calculate overlap
                        overlap_left = max(w.x0, col.x0)
                        overlap_right = min(w.x1, col.x1)
                        overlap_width = overlap_right - overlap_left
                        
                        if overlap_width > 0:
                            if overlap_width > best_overlap:
                                best_overlap = overlap_width
                                best_col_idx = i
                        elif col.x0 <= center_x <= col.x1:
                            # Fallback to center if no positive overlap (rare but possible due to bounds)
                            if best_overlap == 0:
                                best_col_idx = i
                                
                    if best_col_idx != -1:
                        if row_cells[best_col_idx]:
                            row_cells[best_col_idx] += " " + w.text
                        else:
                            row_cells[best_col_idx] = w.text
                
                # Check for empty row
                if any(cell.strip() for cell in row_cells):
                    physical_rows.append(row_cells)
            
            # Find date column index
            date_idx = None
            for i, col in enumerate(columns):
                c = (col.canonical_name or '').lower()
                if 'date' in c and 'value' not in c:
                    date_idx = i
                    break
            
            logical_rows = []
            for p_row in physical_rows:
                if date_idx is not None and p_row[date_idx].strip() != "":
                    # Starts a new logical row
                    logical_rows.append(p_row)
                else:
                    # Continuation row
                    if not logical_rows:
                        # Found continuation before any date row, keep it as is
                        logical_rows.append(p_row)
                    else:
                        # Merge into the last logical row
                        target = logical_rows[-1]
                        for i in range(len(columns)):
                            val = p_row[i].strip()
                            if not val:
                                continue
                            
                            col_name = columns[i].canonical_name
                            target_val = target[i].strip()
                            
                            if not target_val:
                                target[i] = val
                            else:
                                if col_name in ['narration', 'reference_number', 'cheque_number']:
                                    target[i] = target_val + " " + val
                                elif col_name in ['debit', 'credit', 'amount', 'balance']:
                                    # Prefer non-zero amount
                                    from app.utils.amount_utils import parse_amount
                                    target_num, _ = parse_amount(target_val)
                                    val_num, _ = parse_amount(val)
                                    
                                    target_is_zero = target_num == 0 if target_num is not None else False
                                    val_is_zero = val_num == 0 if val_num is not None else False
                                    
                                    if target_is_zero and not val_is_zero:
                                        target[i] = val
                                    # Otherwise keep target_val
                                else:
                                    # Keep first value for dates or other fields
                                    pass
            
            cells.extend(logical_rows)
                    
            if len(cells) > 1: # more than just header
                # Calculate page source_type and confidence from words
                source_type = page.source_type if hasattr(page, 'source_type') else "DIGITAL"
                confs = [w.confidence for w in valid_words if hasattr(w, 'confidence') and w.confidence is not None]
                avg_conf = sum(confs)/len(confs) if confs else None
                
                tc = RawTableCandidate(
                    page_number=page.page_number,
                    bbox=(table_bbox.x0, table_bbox.top, table_bbox.x1, table_bbox.bottom) if table_bbox else (0,0,page.width,page.height),
                    row_count=len(cells),
                    column_count=len(columns),
                    detection_method="profile_coordinates",
                    source_type=source_type,
                    ocr_confidence=avg_conf,
                    cells=cells
                )
                page.table_candidates = [tc]
            else:
                page.table_candidates = []
                
        # Re-calc candidate count
        extraction_result.table_candidate_count = sum(len(p.table_candidates) for p in extraction_result.pages)
        extraction_result.extractor_used = f"coordinate_extractor_{self.profile.profile_id}"
        
        return extraction_result
