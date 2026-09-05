"""
Universal Entity Model - Task-agnostic entity representation

All extractors must emit entities in this standardized format:
- entity_type: Task-defined string (e.g., "DOCUMENT", "RECORD", "TRANSACTION")
- entity_id: Stable unique identifier
- fields: Dict of extracted field values
- evidence: List of Evidence objects showing where data came from

This enables:
- Core-safe entity handling (no task-specific field names)
- Evidence-based validation
- Cross-file entity matching
- Audit trails
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Evidence:
    """
    Evidence showing where an entity or field value came from.

    Attributes:
        source_file: Filename (e.g., "document.pdf")
        source_path: Full path (optional)
        location: Location within file (e.g., "page:1", "sheet:Data!C12", "row:5")
        text: Extracted text snippet (optional)
        value: Parsed value (optional, for debugging)
    """
    source_file: str
    source_path: Optional[str] = None
    location: Optional[str] = None
    text: Optional[str] = None
    value: Optional[Any] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return asdict(self)


@dataclass
class StandardEntity:
    """
    Standardized entity representation for all tasks.

    Attributes:
        entity_type: Type of entity (task-defined string)
        entity_id: Stable unique identifier
        fields: Dict of field name -> value
        evidence: List of Evidence showing data sources
        confidence: Extraction confidence (0.0-1.0)

    Example:
        StandardEntity(
            entity_type="DOCUMENT",
            entity_id="DOCUMENT:abc123|2025-10-15",
            fields={
                "document_id": "abc123",
                "amount": 1000.0,
                "date": "2025-10-15"
            },
            evidence=[
                Evidence(
                    source_file="document.pdf",
                    location="page:1"
                )
            ]
        )
    """
    entity_type: str
    entity_id: str
    fields: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Evidence] = field(default_factory=list)
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "fields": self.fields,
            "evidence": [e.to_dict() for e in self.evidence],
        }

    def get_field(self, field_name: str, default=None) -> Any:
        """Safely get field value with default"""
        return self.fields.get(field_name, default)

    def has_field(self, field_name: str) -> bool:
        """Check if field exists and is non-empty"""
        value = self.fields.get(field_name)
        return value is not None and value != "" and value != []
