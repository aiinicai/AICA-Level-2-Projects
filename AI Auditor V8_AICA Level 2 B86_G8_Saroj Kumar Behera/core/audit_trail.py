"""
AI Auditor V8 - Audit Trail & Data Versioning
Tracks all modifications, user overrides, and extraction adjustments.
"""

from dataclasses import dataclass, field
import datetime
from typing import List, Dict, Any

@dataclass
class AuditLogEntry:
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    action: str = "EDIT"  # "EXTRACT", "EDIT", "MAP", "OVERRIDE", "THRESHOLD_CHANGE"
    statement_type: str = ""
    line_item: str = ""
    field_modified: str = ""  # "value", "standard_key", "category"
    old_value: Any = None
    new_value: Any = None
    reason_notes: str = ""
    user: str = "Auditor"

class AuditTrail:
    def __init__(self):
        self.entries: List[AuditLogEntry] = []

    def record(self, action: str, statement_type: str, line_item: str, field_modified: str, old_val: Any, new_val: Any, notes: str = "", user: str = "Auditor"):
        entry = AuditLogEntry(
            action=action,
            statement_type=statement_type,
            line_item=line_item,
            field_modified=field_modified,
            old_value=old_val,
            new_value=new_val,
            reason_notes=notes,
            user=user
        )
        self.entries.append(entry)

    def to_list_of_dicts(self) -> List[Dict[str, Any]]:
        return [
            {
                "timestamp": e.timestamp,
                "action": e.action,
                "statement_type": e.statement_type,
                "line_item": e.line_item,
                "field_modified": e.field_modified,
                "old_value": str(e.old_value),
                "new_value": str(e.new_value),
                "reason_notes": e.reason_notes,
                "user": e.user
            }
            for e in self.entries
        ]
