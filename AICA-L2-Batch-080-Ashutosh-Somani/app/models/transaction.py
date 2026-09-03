from dataclasses import dataclass, field
from typing import Optional, List
from decimal import Decimal
import datetime

@dataclass
class Transaction:
    transaction_date: Optional[datetime.date] = None
    value_date: Optional[datetime.date] = None
    narration: Optional[str] = None
    reference_number: Optional[str] = None
    cheque_number: Optional[str] = None
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    balance: Optional[Decimal] = None
    branch: Optional[str] = None
    transaction_type: Optional[str] = None
    currency: Optional[str] = None
    
    # Source Traceability
    source_page: Optional[int] = None
    source_row: Optional[int] = None
    source_type: str = "DIGITAL"
    ocr_confidence: Optional[float] = None
    raw_text: Optional[str] = None
    raw_date: Optional[str] = None
    raw_narration: Optional[str] = None
    raw_reference: Optional[str] = None
    raw_debit: Optional[str] = None
    raw_credit: Optional[str] = None
    raw_balance: Optional[str] = None
    
    extractor_used: Optional[str] = None
    profile_used: Optional[str] = None
    normalization_status: str = "unresolved"
    normalization_warnings: List[str] = field(default_factory=list)
    user_corrected: bool = False
    
    def to_dict(self):
        """Serialize for local JSON storage."""
        import dataclasses
        d = dataclasses.asdict(self)
        # Convert Decimals to string exactly, avoiding float
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = str(v)
            elif isinstance(v, datetime.date):
                d[k] = v.isoformat()
        return d
