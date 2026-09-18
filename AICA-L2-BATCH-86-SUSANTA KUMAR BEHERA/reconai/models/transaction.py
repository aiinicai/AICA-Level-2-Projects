import datetime
import decimal
import uuid
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    PROBABLE = "PROBABLE"
    UNMATCHED = "UNMATCHED"


class AuditSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AuditCategory(str, Enum):
    DUPLICATE = "DUPLICATE"
    ROUND_AMOUNT = "ROUND_AMOUNT"
    WEEKEND_HOLIDAY = "WEEKEND_HOLIDAY"
    APPROVAL_MISSING = "APPROVAL_MISSING"
    GST_TDS_COMPLIANCE = "GST_TDS_COMPLIANCE"
    ANOMALOUS_CATEGORY = "ANOMALOUS_CATEGORY"
    SUSPICIOUS_PATTERN = "SUSPICIOUS_PATTERN"
    GENERAL = "GENERAL"


class StatementTransaction(BaseModel):
    """Normalized Bank Statement Transaction record."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_row_ref: Any = Field(..., description="Original line or row index in the source file")
    date: datetime.date = Field(..., description="Transaction posting date")
    description: str = Field(..., description="Narration / description / reference")
    amount: decimal.Decimal = Field(..., description="Absolute monetary transaction amount")
    type: TransactionType = Field(..., description="DEBIT (withdrawal/payment) or CREDIT (deposit/receipt)")
    balance: Optional[decimal.Decimal] = Field(default=None, description="Running bank balance if present")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Preserved original row values for full auditability")
    matched: bool = Field(default=False, description="Matching state flag")

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> decimal.Decimal:
        if isinstance(v, decimal.Decimal):
            return abs(v)
        if isinstance(v, (int, float)):
            return abs(decimal.Decimal(str(v)))
        if isinstance(v, str):
            clean = v.replace(",", "").replace("$", "").replace("₹", "").replace("Rs.", "").strip()
            return abs(decimal.Decimal(clean))
        raise ValueError(f"Invalid amount value: {v}")

    @field_validator("balance", mode="before")
    @classmethod
    def validate_balance(cls, v: Any) -> Optional[decimal.Decimal]:
        if v is None or v == "":
            return None
        if isinstance(v, decimal.Decimal):
            return v
        if isinstance(v, (int, float)):
            return decimal.Decimal(str(v))
        if isinstance(v, str):
            clean = v.replace(",", "").replace("$", "").replace("₹", "").replace("Rs.", "").strip()
            if not clean:
                return None
            return decimal.Decimal(clean)
        return None


class LedgerEntry(BaseModel):
    """Normalized Client Books/Ledger Entry (e.g. from Tally, ERP, Excel)."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_row_ref: Any = Field(..., description="Original voucher number or row index")
    date: datetime.date = Field(..., description="Voucher / entry date")
    description: str = Field(..., description="Particulars / narration")
    amount: decimal.Decimal = Field(..., description="Absolute monetary transaction amount")
    type: TransactionType = Field(..., description="DEBIT (bank payment/expense) or CREDIT (bank receipt/income)")
    account_name: Optional[str] = Field(default=None, description="Party / Account Head / Vendor")
    voucher_type: Optional[str] = Field(default=None, description="e.g., Payment, Receipt, Journal, Contra")
    approver_ref: Optional[str] = Field(default=None, description="Authorizer / approver identifier")
    gstin: Optional[str] = Field(default=None, description="GST Identification Number if present")
    tds_section: Optional[str] = Field(default=None, description="TDS Section (e.g., 194C, 194J) if present")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Preserved original row values")
    matched: bool = Field(default=False, description="Matching state flag")

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> decimal.Decimal:
        if isinstance(v, decimal.Decimal):
            return abs(v)
        if isinstance(v, (int, float)):
            return abs(decimal.Decimal(str(v)))
        if isinstance(v, str):
            clean = v.replace(",", "").replace("$", "").replace("₹", "").replace("Rs.", "").strip()
            return abs(decimal.Decimal(clean))
        raise ValueError(f"Invalid amount value: {v}")


class MatchRecord(BaseModel):
    """Represents a matched pair, probable pair, or unmatched entry."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    statement_tx_id: Optional[str] = Field(default=None, description="ID of matched statement transaction")
    ledger_entry_id: Optional[str] = Field(default=None, description="ID of matched ledger entry")
    status: MatchStatus = Field(..., description="MATCHED, PROBABLE, or UNMATCHED")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Match confidence between 0.0 and 1.0")
    rule_applied: str = Field(..., description="Code / Identifier of the matching rule that triggered")
    plain_english_reason: str = Field(..., description="Human-readable explanation of why this match was made")
    manual_override: bool = Field(default=False, description="True if manually created or adjusted by user")
    notes: Optional[str] = Field(default=None, description="Auditor review notes")


class AuditFlag(BaseModel):
    """An expense or compliance anomaly flagged for auditor review."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_type: str = Field(default="LEDGER", description="'LEDGER' or 'STATEMENT'")
    source_row_ref: Any = Field(..., description="Source row or voucher reference")
    entry_id: str = Field(..., description="ID of the flagged entry")
    rule_name: str = Field(..., description="Identifier of the audit rule")
    severity: AuditSeverity = Field(..., description="HIGH, MEDIUM, LOW, or INFO")
    category: AuditCategory = Field(..., description="Category of the audit rule")
    plain_english_reason: str = Field(..., description="Auditor-friendly explanation of why this was flagged")
    suggested_action: str = Field(..., description="Action recommended for the CA / audit team")
    entry_summary: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Summary snapshot of the entry")
