from app.models.exception import ExceptionRecord
from decimal import Decimal
from typing import Optional

class ExceptionService:
    @staticmethod
    def create_exception(
        code: str, 
        transaction_index: Optional[int] = None,
        source_page: Optional[int] = None,
        source_row: Optional[int] = None,
        difference: Optional[Decimal] = None,
        context: Optional[str] = None
    ) -> ExceptionRecord:
        severity, message, review_required = ExceptionService._get_metadata_for_code(code)
        
        return ExceptionRecord(
            exception_code=code,
            severity=severity,
            message=message,
            transaction_index=transaction_index,
            source_page=source_page,
            source_row=source_row,
            financial_difference=difference,
            review_required=review_required,
            context=context
        )

    @staticmethod
    def _get_metadata_for_code(code: str):
        # returns (severity, message, review_required)
        mappings = {
            "BALANCE_MISMATCH": ("ERROR", "Row balance does not mathematically reconcile.", True),
            "PAGE_TRANSITION_BALANCE_MISMATCH": ("ERROR", "Balance mismatch occurred across a page transition.", True),
            "STATEMENT_CLOSING_MISMATCH": ("CRITICAL", "Statement closing balance does not match aggregate total.", True),
            "MISSING_OPENING_BALANCE": ("WARNING", "Statement missing opening balance; early transactions cannot be validated.", False),
            "MISSING_CLOSING_BALANCE": ("WARNING", "Statement missing closing balance; full reconciliation impossible.", False),
            "MISSING_TRANSACTION_BALANCE": ("WARNING", "Transaction has no explicit balance.", True),
            "BOTH_DEBIT_AND_CREDIT_NONZERO": ("ERROR", "Both debit and credit fields contain non-zero amounts.", True),
            "NO_DEBIT_OR_CREDIT": ("WARNING", "Neither debit nor credit fields contain amounts.", True),
            "ZERO_AMOUNT_TRANSACTION": ("WARNING", "Transaction amount evaluates to zero.", True),
            "INVALID_TRANSACTION_DATE": ("ERROR", "Transaction date is malformed or missing.", True),
            "DATE_OUTSIDE_STATEMENT_PERIOD": ("WARNING", "Transaction date falls outside the reported statement period.", True),
            "MIXED_DATE_SEQUENCE": ("WARNING", "Dates reverse or shift order unexpectedly.", True),
            "MALFORMED_AMOUNT": ("ERROR", "Amount string could not be parsed securely.", True),
            "AMBIGUOUS_DIRECTION": ("ERROR", "Debit/Credit direction could not be determined.", True),
            "NORMALIZATION_WARNING": ("WARNING", "Row had a normalization structural warning.", True),
            "POSSIBLE_DUPLICATE": ("WARNING", "Transaction closely matches another row.", True)
        }
        
        return mappings.get(code, ("INFO", "Unknown exception code.", True))
