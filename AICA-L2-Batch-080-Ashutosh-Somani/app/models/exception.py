from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass
class ExceptionRecord:
    exception_code: str
    severity: str
    message: str
    transaction_index: Optional[int] = None
    source_page: Optional[int] = None
    source_row: Optional[int] = None
    financial_difference: Optional[Decimal] = None
    review_required: bool = True
    context: Optional[str] = None
    
    def to_dict(self):
        return {
            "exception_code": self.exception_code,
            "severity": self.severity,
            "message": self.message,
            "transaction_index": self.transaction_index,
            "source_page": self.source_page,
            "source_row": self.source_row,
            "financial_difference": str(self.financial_difference) if self.financial_difference is not None else None,
            "review_required": self.review_required,
            "context": self.context
        }
