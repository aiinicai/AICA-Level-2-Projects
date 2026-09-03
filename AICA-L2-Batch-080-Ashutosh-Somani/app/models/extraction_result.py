from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class RawWord:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    page_number: int
    source_type: str = "DIGITAL"
    confidence: Optional[float] = None

    @property
    def ocr_confidence(self) -> Optional[float]:
        """Alias for confidence — standardized as float 0-100."""
        return self.confidence

    @ocr_confidence.setter
    def ocr_confidence(self, value: Optional[float]):
        self.confidence = value

@dataclass
class RawTableCandidate:
    page_number: int
    bbox: tuple # (x0, top, x1, bottom)
    row_count: int
    column_count: int
    detection_method: str
    source_type: str = "DIGITAL"
    ocr_confidence: Optional[float] = None
    cells: List[List[str]] = field(default_factory=list)

@dataclass
class RawPage:
    page_number: int
    width: float
    height: float
    raw_text: str
    word_count: int
    character_count: int
    source_type: str = "DIGITAL"
    words: List[RawWord] = field(default_factory=list)
    table_candidates: List[RawTableCandidate] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    extraction_status: str = "success"

@dataclass
class ExtractionResult:
    job_id: str
    extractor_used: str
    extractor_version: str
    status: str
    page_count: int
    pages_processed: int
    total_words: int
    total_characters: int
    text_layer_status: str
    table_candidate_count: int
    warnings: List[str] = field(default_factory=list)
    pages: List[RawPage] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Simple serialization for local JSON storage."""
        import json
        import dataclasses
        return dataclasses.asdict(self)
