from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class StatementMetadata:
    bank_name: Optional[str] = None
    account_type: Optional[str] = None
    account_holder: Optional[str] = None
    account_number: Optional[str] = None
    ifsc: Optional[str] = None
    branch: Optional[str] = None
    currency: Optional[str] = None
    statement_start_date: Optional[str] = None
    statement_end_date: Optional[str] = None
    opening_balance: Optional[str] = None
    closing_balance: Optional[str] = None
    source_job_id: Optional[str] = None
    metadata_warnings: List[str] = field(default_factory=list)
