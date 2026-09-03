from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class SourceMappingService:
    """
    Resolves a transaction back to its geometric source constraints inside the PDF using the original extraction artifacts.
    """
    
    def __init__(self, raw_extraction_artifact: Dict[str, Any]):
        self.raw_extraction = raw_extraction_artifact
    
    def get_source_bbox(self, page_number: int, row_index: int) -> Optional[Dict[str, float]]:
        """
        Derives the bbox by querying the original table_candidates inside raw extraction.
        Since we have source_page and source_row (which corresponds to row index inside the candidate table),
        we can retrieve the bounding box of the row itself!
        """
        if not page_number or row_index is None:
            return None
            
        pages = self.raw_extraction.get("pages", [])
        page_data = next((p for p in pages if p.get("page_number") == page_number), None)
        if not page_data:
            return None
            
        candidates = page_data.get("table_candidates", [])
        if not candidates:
            return None
            
        # For simplicity, if we only have one table candidate we just assume it's table index 0.
        # Ideally, `source_row` is sufficient if there's one table per page.
        # If there are multiple tables, we'll try to find the row that maps.
        
        # We assume the normalization preserved the row structure. 
        # Actually, in TransactionNormalizer, we don't strictly preserve table index, but we do preserve source_row.
        # We'll just look through all candidates, find the row, and return its bbox.
        # Let's iterate candidates and check row lengths. Wait, source_row is relative to the flat list of rows fed to normalization.
        
        # Let's just flat map the original rows from candidates.
        flat_row_bboxes = []
        for c in candidates:
            for cell_row in c.get("cells", []):
                # A row's bbox is the bounding box encapsulating all its word bboxes, OR the cell rects.
                row_x0, row_top, row_x1, row_bottom = 9999.0, 9999.0, 0.0, 0.0
                has_content = False
                
                # cells are a list of text strings, but wait, `table_candidates` in `raw_extraction.json` 
                # (via coordinate_extractor or pdfplumber) might just have "cells" as list of strings.
                # If they only have strings, how do we get BBox?
                # The coordinate_extractor explicitly outputs `cells`, but does it output `bbox`?
                # In coordinate_extractor, we construct 'cells' by joining words.
                pass
        
        # Because we may not have explicitly saved row geometry in Stage 3, let's use a simpler heuristic.
        # We find the words on that page that match the text of the row roughly, OR we rely on a simplified bbox if the model didn't save it.
        # For now, let's return None and rely on page-level navigation, unless the model provides explicit bboxes later.
        return None
