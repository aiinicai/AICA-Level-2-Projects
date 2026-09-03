from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class CorrectionAction(Enum):
    FIELD_EDIT = "FIELD_EDIT"
    ROW_MERGE = "ROW_MERGE"
    ROW_SPLIT = "ROW_SPLIT"
    MARK_NON_TRANSACTION = "MARK_NON_TRANSACTION"
    RESTORE_TRANSACTION = "RESTORE_TRANSACTION"
    REVERT_CORRECTION = "REVERT_CORRECTION"
    PROFILE_SUGGESTION_CREATED = "PROFILE_SUGGESTION_CREATED"

@dataclass
class CorrectionEvent:
    event_id: str
    job_id: str
    timestamp: str
    action: CorrectionAction
    
    transaction_id: Optional[str] = None
    affected_transaction_ids: List[str] = field(default_factory=list)
    
    field_name: Optional[str] = None
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    
    reason: Optional[str] = None
    source_page: Optional[int] = None
    source_row: Optional[int] = None
    
    review_revision_before: int = 0
    review_revision_after: int = 0
    
    validation_status_before: Optional[str] = None
    validation_status_after: Optional[str] = None
    
    profile_suggestion_created: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "job_id": self.job_id,
            "timestamp": self.timestamp,
            "action": self.action.value,
            "transaction_id": self.transaction_id,
            "affected_transaction_ids": self.affected_transaction_ids,
            "field_name": self.field_name,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "reason": self.reason,
            "source_page": self.source_page,
            "source_row": self.source_row,
            "review_revision_before": self.review_revision_before,
            "review_revision_after": self.review_revision_after,
            "validation_status_before": self.validation_status_before,
            "validation_status_after": self.validation_status_after,
            "profile_suggestion_created": self.profile_suggestion_created
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorrectionEvent':
        return cls(
            event_id=data["event_id"],
            job_id=data["job_id"],
            timestamp=data["timestamp"],
            action=CorrectionAction(data["action"]),
            transaction_id=data.get("transaction_id"),
            affected_transaction_ids=data.get("affected_transaction_ids", []),
            field_name=data.get("field_name"),
            before_value=data.get("before_value"),
            after_value=data.get("after_value"),
            reason=data.get("reason"),
            source_page=data.get("source_page"),
            source_row=data.get("source_row"),
            review_revision_before=data.get("review_revision_before", 0),
            review_revision_after=data.get("review_revision_after", 0),
            validation_status_before=data.get("validation_status_before"),
            validation_status_after=data.get("validation_status_after"),
            profile_suggestion_created=data.get("profile_suggestion_created", False)
        )
