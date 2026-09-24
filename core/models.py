"""
Data models and Status Enums for TDS & TCS Certificate PDF Auto-Renamer.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any


class ProcessingStatus(str, Enum):
    PENDING = "Pending"
    ANALYZING = "Analyzing"
    EXTRACTED = "Extracted"
    PREVIEW_READY = "Preview Ready"
    RENAMED = "Renamed"
    COPIED = "Copied"
    MOVED = "Moved"
    SKIPPED = "Skipped"
    ERROR = "Error"
    UNDO_SUCCESS = "Undone"
    UNDO_ERROR = "Undo Error"


@dataclass
class CertificateData:
    file_path: Path
    original_filename: str = ""
    file_size_bytes: int = 0
    act: str = "Unknown Act"
    form_type: str = "Unknown Form"
    form_code: str = ""
    category: str = "Unknown"
    deductee_name: str = ""
    deductee_pan: str = ""
    deductor_name: str = ""
    deductor_tan: str = ""
    financial_year: str = ""
    assessment_year: str = ""
    quarter: str = ""
    certificate_no: str = ""
    proposed_filename: str = ""
    final_filepath: Optional[Path] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    message: str = ""
    confidence_score: float = 0.0
    raw_text_snippet: str = ""
    is_scanned: bool = False
    processing_time_ms: float = 0.0

    def __post_init__(self):
        if not self.original_filename and self.file_path:
            self.original_filename = Path(self.file_path).name
        if not self.file_size_bytes and self.file_path:
            try:
                self.file_size_bytes = Path(self.file_path).stat().st_size
            except Exception:
                self.file_size_bytes = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for QAbstractTableModel and Excel export."""
        return {
            "Original File": self.original_filename,
            "Governing Act": self.act,
            "Form Type": self.form_type,
            "Category": self.category,
            "Deductee / Collectee": self.deductee_name,
            "PAN": self.deductee_pan,
            "TAN": self.deductor_tan,
            "FY": self.financial_year,
            "AY": self.assessment_year,
            "Quarter": self.quarter,
            "Certificate No": self.certificate_no,
            "Proposed Filename": self.proposed_filename,
            "Status": self.status.value if isinstance(self.status, ProcessingStatus) else str(self.status),
            "Message": self.message,
            "File Path": str(self.file_path),
            "Final Path": str(self.final_filepath) if self.final_filepath else "",
        }
