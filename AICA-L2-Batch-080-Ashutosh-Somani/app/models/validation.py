from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

@dataclass
class TransactionValidationResult:
    transaction_index: int
    source_page: Optional[int]
    source_row: Optional[int]
    
    # Financial fields
    previous_balance: Optional[Decimal] = None
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    expected_balance: Optional[Decimal] = None
    actual_balance: Optional[Decimal] = None
    difference: Optional[Decimal] = None
    
    validation_status: str = "NOT_VERIFIABLE"
    exception_codes: List[str] = field(default_factory=list)
    review_score: int = 0
    source_type: str = "DIGITAL"
    ocr_confidence: Optional[float] = None
    
    def to_dict(self):
        return {
            "transaction_index": self.transaction_index,
            "source_page": self.source_page,
            "source_row": self.source_row,
            "previous_balance": str(self.previous_balance) if self.previous_balance is not None else None,
            "debit": str(self.debit) if self.debit is not None else None,
            "credit": str(self.credit) if self.credit is not None else None,
            "expected_balance": str(self.expected_balance) if self.expected_balance is not None else None,
            "actual_balance": str(self.actual_balance) if self.actual_balance is not None else None,
            "difference": str(self.difference) if self.difference is not None else None,
            "validation_status": self.validation_status,
            "exception_codes": self.exception_codes,
            "review_score": self.review_score,
            "source_type": self.source_type,
            "ocr_confidence": self.ocr_confidence
        }

@dataclass
class StatementValidationResult:
    opening_balance: Optional[Decimal] = None
    total_debits: Decimal = Decimal("0")
    total_credits: Decimal = Decimal("0")
    expected_closing_balance: Optional[Decimal] = None
    statement_closing_balance: Optional[Decimal] = None
    difference: Optional[Decimal] = None
    
    transaction_count: int = 0
    validated_transaction_count: int = 0
    transactions_with_balance: int = 0
    transactions_not_verifiable: int = 0
    balance_mismatch_count: int = 0
    exception_count: int = 0
    validation_status: str = "NOT_VERIFIABLE"
    
    def to_dict(self):
        return {
            "opening_balance": str(self.opening_balance) if self.opening_balance is not None else None,
            "total_debits": str(self.total_debits),
            "total_credits": str(self.total_credits),
            "expected_closing_balance": str(self.expected_closing_balance) if self.expected_closing_balance is not None else None,
            "statement_closing_balance": str(self.statement_closing_balance) if self.statement_closing_balance is not None else None,
            "difference": str(self.difference) if self.difference is not None else None,
            "transaction_count": self.transaction_count,
            "validated_transaction_count": self.validated_transaction_count,
            "transactions_with_balance": self.transactions_with_balance,
            "transactions_not_verifiable": self.transactions_not_verifiable,
            "balance_mismatch_count": self.balance_mismatch_count,
            "exception_count": self.exception_count,
            "validation_status": self.validation_status
        }
