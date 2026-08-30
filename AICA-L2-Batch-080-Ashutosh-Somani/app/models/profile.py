from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime, timezone
import json

@dataclass
class ColumnDefinition:
    canonical_name: str
    x0: float
    x1: float
    required: bool = False
    
    def to_dict(self):
        return {
            "canonical_name": self.canonical_name,
            "x0": self.x0,
            "x1": self.x1,
            "required": self.required
        }
        
    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            canonical_name=d.get("canonical_name", ""),
            x0=float(d.get("x0", 0.0)),
            x1=float(d.get("x1", 0.0)),
            required=bool(d.get("required", False))
        )

@dataclass
class TableRegion:
    x0: float
    top: float
    x1: float
    bottom: float
    
    def to_dict(self):
        return {
            "x0": self.x0,
            "top": self.top,
            "x1": self.x1,
            "bottom": self.bottom
        }
        
    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            x0=float(d.get("x0", 0.0)),
            top=float(d.get("top", 0.0)),
            x1=float(d.get("x1", 0.0)),
            bottom=float(d.get("bottom", 0.0))
        )

@dataclass
class BankProfile:
    profile_id: str
    profile_name: str
    bank_name: str
    account_type: str = ""
    layout_version: str = "1.0"
    
    profile_schema_version: int = 1
    
    created_at: str = ""
    updated_at: str = ""
    active: bool = True
    
    page_width: float = 0.0
    page_height: float = 0.0
    page_size_tolerance: float = 2.0
    
    expected_header_signatures: List[str] = field(default_factory=list)
    
    table_bbox: Optional[TableRegion] = None
    continuation_table_bbox: Optional[TableRegion] = None
    column_definitions: List[ColumnDefinition] = field(default_factory=list)
    
    row_y_tolerance: float = 2.0
    
    date_formats: List[str] = field(default_factory=lambda: ["%d/%m/%Y"])
    amount_format: str = "standard"
    cr_dr_convention: str = "standard"
    
    header_removal_rules: List[str] = field(default_factory=list)
    footer_removal_rules: List[str] = field(default_factory=list)
    
    continuation_rules: Dict[str, str] = field(default_factory=dict)
    
    extractor_preference: str = "coordinate"
    
    revision_number: int = 1
    notes: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self):
        return {
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "bank_name": self.bank_name,
            "account_type": self.account_type,
            "layout_version": self.layout_version,
            "profile_schema_version": self.profile_schema_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "active": self.active,
            "page_width": self.page_width,
            "page_height": self.page_height,
            "page_size_tolerance": self.page_size_tolerance,
            "expected_header_signatures": self.expected_header_signatures,
            "table_bbox": self.table_bbox.to_dict() if self.table_bbox else None,
            "continuation_table_bbox": self.continuation_table_bbox.to_dict() if self.continuation_table_bbox else None,
            "column_definitions": [c.to_dict() for c in self.column_definitions],
            "row_y_tolerance": self.row_y_tolerance,
            "date_formats": self.date_formats,
            "amount_format": self.amount_format,
            "cr_dr_convention": self.cr_dr_convention,
            "header_removal_rules": self.header_removal_rules,
            "footer_removal_rules": self.footer_removal_rules,
            "continuation_rules": self.continuation_rules,
            "extractor_preference": self.extractor_preference,
            "revision_number": self.revision_number,
            "notes": self.notes
        }
        
    @classmethod
    def from_dict(cls, d: dict):
        profile = cls(
            profile_id=d.get("profile_id", ""),
            profile_name=d.get("profile_name", ""),
            bank_name=d.get("bank_name", "")
        )
        profile.account_type = d.get("account_type", "")
        profile.layout_version = d.get("layout_version", "1.0")
        profile.profile_schema_version = int(d.get("profile_schema_version", 1))
        profile.created_at = d.get("created_at", "")
        profile.updated_at = d.get("updated_at", "")
        profile.active = bool(d.get("active", True))
        profile.page_width = float(d.get("page_width", 0.0))
        profile.page_height = float(d.get("page_height", 0.0))
        profile.page_size_tolerance = float(d.get("page_size_tolerance", 2.0))
        profile.expected_header_signatures = d.get("expected_header_signatures", [])
        
        tbox = d.get("table_bbox")
        if tbox:
            profile.table_bbox = TableRegion.from_dict(tbox)
            
        cbox = d.get("continuation_table_bbox")
        if cbox:
            profile.continuation_table_bbox = TableRegion.from_dict(cbox)
            
        profile.column_definitions = [ColumnDefinition.from_dict(c) for c in d.get("column_definitions", [])]
        profile.row_y_tolerance = float(d.get("row_y_tolerance", 2.0))
        profile.date_formats = d.get("date_formats", ["%d/%m/%Y"])
        profile.amount_format = d.get("amount_format", "standard")
        profile.cr_dr_convention = d.get("cr_dr_convention", "standard")
        profile.header_removal_rules = d.get("header_removal_rules", [])
        profile.footer_removal_rules = d.get("footer_removal_rules", [])
        profile.continuation_rules = d.get("continuation_rules", {})
        profile.extractor_preference = d.get("extractor_preference", "coordinate")
        profile.revision_number = d.get("revision_number", 1)
        profile.notes = d.get("notes", "")
        
        return profile
