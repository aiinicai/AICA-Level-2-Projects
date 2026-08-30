from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from decimal import Decimal

class ReviewStatus(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEWED_WITH_EXCEPTIONS = "REVIEWED_WITH_EXCEPTIONS"
    REVIEWED_VALID = "REVIEWED_VALID"

class CorrectionStatus(Enum):
    UNREVIEWED = "UNREVIEWED"
    REVIEWED = "REVIEWED"
    CORRECTED = "CORRECTED"
    NON_TRANSACTION = "NON_TRANSACTION"
    SUPERSEDED = "SUPERSEDED"
    SPLIT_CHILD = "SPLIT_CHILD"
    MERGED_RESULT = "MERGED_RESULT"

@dataclass
class ReviewedTransaction:
    transaction_id: str
    original_transaction_id: str
    
    transaction_date: Optional[str] = None
    value_date: Optional[str] = None
    narration: str = ""
    reference_number: Optional[str] = None
    cheque_number: Optional[str] = None
    
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    balance: Optional[Decimal] = None
    
    # Traceability
    source_page: Optional[int] = None
    source_row: Optional[int] = None
    source_bbox: Optional[Dict[str, float]] = None
    
    extractor_used: Optional[str] = None
    profile_used: Optional[str] = None
    
    # Review Metadata
    user_corrected: bool = False
    correction_count: int = 0
    review_status: CorrectionStatus = CorrectionStatus.UNREVIEWED
    derived_from_transaction_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "original_transaction_id": self.original_transaction_id,
            "transaction_date": self.transaction_date,
            "value_date": self.value_date,
            "narration": self.narration,
            "reference_number": self.reference_number,
            "cheque_number": self.cheque_number,
            "debit": str(self.debit) if self.debit is not None else None,
            "credit": str(self.credit) if self.credit is not None else None,
            "balance": str(self.balance) if self.balance is not None else None,
            "source_page": self.source_page,
            "source_row": self.source_row,
            "source_bbox": self.source_bbox,
            "extractor_used": self.extractor_used,
            "profile_used": self.profile_used,
            "user_corrected": self.user_corrected,
            "correction_count": self.correction_count,
            "review_status": self.review_status.value,
            "derived_from_transaction_ids": self.derived_from_transaction_ids
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewedTransaction':
        return cls(
            transaction_id=data["transaction_id"],
            original_transaction_id=data.get("original_transaction_id", data["transaction_id"]),
            transaction_date=data.get("transaction_date"),
            value_date=data.get("value_date"),
            narration=data.get("narration", ""),
            reference_number=data.get("reference_number"),
            cheque_number=data.get("cheque_number"),
            debit=Decimal(data["debit"]) if data.get("debit") is not None else None,
            credit=Decimal(data["credit"]) if data.get("credit") is not None else None,
            balance=Decimal(data["balance"]) if data.get("balance") is not None else None,
            source_page=data.get("source_page"),
            source_row=data.get("source_row"),
            source_bbox=data.get("source_bbox"),
            extractor_used=data.get("extractor_used"),
            profile_used=data.get("profile_used"),
            user_corrected=data.get("user_corrected", False),
            correction_count=data.get("correction_count", 0),
            review_status=CorrectionStatus(data.get("review_status", "UNREVIEWED")),
            derived_from_transaction_ids=data.get("derived_from_transaction_ids", [])
        )

@dataclass
class ReviewedStatement:
    job_id: str
    review_revision: int = 1
    review_status: ReviewStatus = ReviewStatus.NOT_STARTED
    transactions: List[ReviewedTransaction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "review_revision": self.review_revision,
            "review_status": self.review_status.value,
            "transactions": [t.to_dict() for t in self.transactions]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewedStatement':
        return cls(
            job_id=data["job_id"],
            review_revision=data.get("review_revision", 1),
            review_status=ReviewStatus(data.get("review_status", "NOT_STARTED")),
            transactions=[ReviewedTransaction.from_dict(t) for t in data.get("transactions", [])]
        )
