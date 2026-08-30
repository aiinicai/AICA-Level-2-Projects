import json
import logging
import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from flask import current_app
from typing import Tuple, List, Dict, Optional

from app.services.job_state_service import get_job
from app.services.normalization_service import get_normalization_result
from app.database.db import get_db_connection
from app.models.validation import TransactionValidationResult, StatementValidationResult
from app.models.exception import ExceptionRecord
from app.services.exception_service import ExceptionService
from app.services.confidence_service import ConfidenceService

logger = logging.getLogger(__name__)

class ValidationService:
    def __init__(self, config):
        self.config = config

    def validate_job(self, job_id: str) -> Tuple[bool, Optional[str]]:
        job = get_job(self.config, job_id)
        if not job:
            return False, "Job not found"
            
        norm_data = get_normalization_result(job_id, self.config)
        if not norm_data:
            return False, "Normalization artifact not found."

        try:
            val_summary, tx_results, all_exceptions = self._perform_validation(norm_data)
            
            # Save artifact
            temp_dir = Path(self.config.get('paths', 'temp', fallback='temp'))
            project_root = Path(__file__).resolve().parent.parent.parent
            val_dir = project_root / temp_dir / 'jobs' / job_id / 'validation'
            val_dir.mkdir(exist_ok=True)
            
            artifact_path = val_dir / 'validation_result.json'
            
            artifact_data = {
                "summary": val_summary.to_dict(),
                "transactions": [t.to_dict() for t in tx_results],
                "exceptions": [e.to_dict() for e in all_exceptions]
            }
            
            with open(artifact_path, 'w', encoding='utf-8') as f:
                json.dump(artifact_data, f, ensure_ascii=False)
                
            # Update DB
            total_exceptions = len(all_exceptions)
            balance_mismatches = len([e for e in all_exceptions if e.exception_code in ["BALANCE_MISMATCH", "PAGE_TRANSITION_BALANCE_MISMATCH"]])
            
            with get_db_connection(self.config) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE processing_jobs 
                    SET validation_status = ?,
                        validated_transaction_count = ?,
                        balance_mismatch_count = ?,
                        exception_count = ?,
                        statement_difference = ?,
                        status = 'validated',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    val_summary.validation_status,
                    val_summary.validated_transaction_count,
                    balance_mismatches,
                    total_exceptions,
                    str(val_summary.difference) if val_summary.difference is not None else None,
                    job_id
                ))
            
            return True, None
            
        except Exception as e:
            logger.error(f"Validation failed for job {job_id}: {e}", exc_info=True)
            return False, str(e)

    def _safe_decimal(self, val_str) -> Optional[Decimal]:
        if val_str is None or val_str == "":
            return None
        try:
            return Decimal(str(val_str))
        except InvalidOperation:
            return None

    def _safe_date(self, val_str) -> Optional[datetime.date]:
        if not val_str:
            return None
        try:
            return datetime.date.fromisoformat(val_str)
        except ValueError:
            return None

    def _perform_validation(self, norm_data: dict) -> Tuple[StatementValidationResult, List[TransactionValidationResult], List[ExceptionRecord]]:
        txns = norm_data.get('transactions', [])
        metadata = norm_data.get('metadata', {})
        
        opening_balance = self._safe_decimal(metadata.get('opening_balance'))
        statement_closing = self._safe_decimal(metadata.get('closing_balance'))
        statement_period = metadata.get('statement_period', '')
        # Simple extraction for bounds if present. E.g., '01/04/2023 to 31/03/2024'
        # But since period could be any string from Stage 4, let's keep it abstract or skip bounds checking 
        # unless period is strictly parsed. Wait, the user said: "If statement start/end dates are reliably present... If statement period is unavailable or ambiguous, do not fabricate a period."
        # We'll just look at transaction sequence primarily.
        
        summary = StatementValidationResult()
        summary.opening_balance = opening_balance
        summary.statement_closing_balance = statement_closing
        summary.transaction_count = len(txns)
        
        tx_results = []
        all_exceptions = []
        
        seen_signatures = set()
        last_date = None
        date_sequence = "UNKNOWN"
        date_shifts = 0
        
        # Pass 1: Non-reconciliation checks & Date sequence detection
        temp_results = []
        for idx, t_raw in enumerate(txns):
            exceptions = []
            dr = self._safe_decimal(t_raw.get('debit'))
            cr = self._safe_decimal(t_raw.get('credit'))
            bal = self._safe_decimal(t_raw.get('balance'))
            tx_date_str = t_raw.get('transaction_date')
            tx_date = self._safe_date(tx_date_str)
            narration = t_raw.get('narration', '')
            
            res = TransactionValidationResult(
                transaction_index=idx,
                source_page=t_raw.get('source_page'),
                source_row=t_raw.get('source_row'),
                source_type=t_raw.get('source_type', 'DIGITAL'),
                ocr_confidence=t_raw.get('ocr_confidence'),
                debit=dr,
                credit=cr,
                actual_balance=bal
            )
            
            # Duplicate check
            sig = (tx_date_str, str(dr), str(cr), str(bal), narration)
            if sig in seen_signatures and (dr is not None or cr is not None):
                exceptions.append(ExceptionService.create_exception("POSSIBLE_DUPLICATE", idx, res.source_page, res.source_row))
            seen_signatures.add(sig)
            
            # Structural checks
            is_structurally_valid = True
            if dr is None and cr is None:
                exceptions.append(ExceptionService.create_exception("NO_DEBIT_OR_CREDIT", idx, res.source_page, res.source_row))
                is_structurally_valid = False
            elif dr is not None and cr is not None:
                if dr != Decimal("0") and cr != Decimal("0"):
                    exceptions.append(ExceptionService.create_exception("BOTH_DEBIT_AND_CREDIT_NONZERO", idx, res.source_page, res.source_row))
                    is_structurally_valid = False
                elif dr == Decimal("0") and cr == Decimal("0"):
                    exceptions.append(ExceptionService.create_exception("ZERO_AMOUNT_TRANSACTION", idx, res.source_page, res.source_row))
            elif (dr is not None and dr == Decimal("0")) and cr is None:
                exceptions.append(ExceptionService.create_exception("ZERO_AMOUNT_TRANSACTION", idx, res.source_page, res.source_row))
            elif (cr is not None and cr == Decimal("0")) and dr is None:
                exceptions.append(ExceptionService.create_exception("ZERO_AMOUNT_TRANSACTION", idx, res.source_page, res.source_row))

            if not tx_date:
                exceptions.append(ExceptionService.create_exception("INVALID_TRANSACTION_DATE", idx, res.source_page, res.source_row))
                is_structurally_valid = False
            else:
                if last_date:
                    if tx_date < last_date:
                        direction = "DESCENDING"
                    elif tx_date > last_date:
                        direction = "ASCENDING"
                    else:
                        direction = None
                        
                    if direction:
                        if date_sequence == "UNKNOWN" or date_sequence == "SINGLE_DATE":
                            date_sequence = direction
                        elif date_sequence != direction and date_sequence != "MIXED":
                            date_sequence = "MIXED"
                            date_shifts += 1
                        elif date_sequence == "MIXED":
                            date_shifts += 1
                elif date_sequence == "UNKNOWN":
                    date_sequence = "SINGLE_DATE"
                last_date = tx_date
                
                # Bounds check
                start_date_str = metadata.get('statement_start_date')
                end_date_str = metadata.get('statement_end_date')
                if start_date_str:
                    st_date = self._safe_date(start_date_str)
                    if st_date and tx_date < st_date:
                        exceptions.append(ExceptionService.create_exception("DATE_OUTSIDE_STATEMENT_PERIOD", idx, res.source_page, res.source_row))
                if end_date_str:
                    en_date = self._safe_date(end_date_str)
                    if en_date and tx_date > en_date:
                        exceptions.append(ExceptionService.create_exception("DATE_OUTSIDE_STATEMENT_PERIOD", idx, res.source_page, res.source_row))
                
            for warn in t_raw.get('normalization_warnings', []):
                exceptions.append(ExceptionService.create_exception("NORMALIZATION_WARNING", idx, res.source_page, res.source_row, context=warn))

            # Aggregate totals
            if dr:
                summary.total_debits += dr
            if cr:
                summary.total_credits += cr
                
            if bal is not None:
                summary.transactions_with_balance += 1
            else:
                summary.transactions_not_verifiable += 1

            temp_results.append((res, exceptions, is_structurally_valid))

        # Pass 2: Balance reconciliation based on detected date_sequence
        running_expected_balance = opening_balance
        previous_page = None
        
        if date_sequence == "DESCENDING":
            iterator = list(range(len(txns) - 1, -1, -1))
        else:
            iterator = list(range(len(txns)))
            
        for idx in iterator:
            res, exceptions, is_structurally_valid = temp_results[idx]
            dr = res.debit
            cr = res.credit
            bal = res.actual_balance
            
            eff_dr = dr if dr is not None else Decimal("0")
            eff_cr = cr if cr is not None else Decimal("0")
            
            res.previous_balance = running_expected_balance
            is_balance_verified = False
            
            if running_expected_balance is not None:
                res.expected_balance = running_expected_balance + eff_cr - eff_dr
                
                if bal is not None:
                    res.difference = bal - res.expected_balance
                    if res.difference == Decimal("0"):
                        res.validation_status = "BALANCED"
                        is_balance_verified = True
                        summary.validated_transaction_count += 1
                    else:
                        res.validation_status = "BALANCE_MISMATCH"
                        code = "PAGE_TRANSITION_BALANCE_MISMATCH" if previous_page is not None and res.source_page != previous_page else "BALANCE_MISMATCH"
                        exceptions.append(ExceptionService.create_exception(code, idx, res.source_page, res.source_row, res.difference))
                        
                    running_expected_balance = bal
                else:
                    res.validation_status = "MISSING_BALANCE"
                    exceptions.append(ExceptionService.create_exception("MISSING_TRANSACTION_BALANCE", idx, res.source_page, res.source_row))
                    running_expected_balance = res.expected_balance
            else:
                res.validation_status = "NO_PRIOR_BALANCE"
                if bal is not None:
                    running_expected_balance = bal
                else:
                    exceptions.append(ExceptionService.create_exception("MISSING_TRANSACTION_BALANCE", idx, res.source_page, res.source_row))
            
            previous_page = res.source_page
            
            res.exception_codes = [e.exception_code for e in exceptions]
            res.review_score = ConfidenceService.calculate_score(exceptions, is_structurally_valid, is_balance_verified)
            
            all_exceptions.extend(exceptions)
            
        for res, exceptions, is_structurally_valid in temp_results:
            tx_results.append(res)
            
        if date_sequence == "MIXED" and date_shifts > 0:
            all_exceptions.append(ExceptionService.create_exception("MIXED_DATE_SEQUENCE"))
            
        if opening_balance is None:
            all_exceptions.append(ExceptionService.create_exception("MISSING_OPENING_BALANCE"))
        if statement_closing is None:
            all_exceptions.append(ExceptionService.create_exception("MISSING_CLOSING_BALANCE"))
            
        if opening_balance is not None:
            summary.expected_closing_balance = opening_balance + summary.total_credits - summary.total_debits
            if statement_closing is not None:
                summary.difference = statement_closing - summary.expected_closing_balance
                if date_sequence == "MIXED" and date_shifts > 0:
                    summary.validation_status = "NOT_VERIFIABLE"
                elif summary.difference == Decimal("0"):
                    summary.validation_status = "PASS"
                else:
                    summary.validation_status = "FAIL"
                    all_exceptions.append(ExceptionService.create_exception("STATEMENT_CLOSING_MISMATCH", difference=summary.difference))
            else:
                summary.validation_status = "NOT_VERIFIABLE"
        else:
            summary.validation_status = "NOT_VERIFIABLE"
            
        summary.exception_count = len(all_exceptions)
        summary.balance_mismatch_count = len([e for e in all_exceptions if e.exception_code in ["BALANCE_MISMATCH", "PAGE_TRANSITION_BALANCE_MISMATCH"]])
        
        return summary, tx_results, all_exceptions

def get_validation_result(job_id, config):
    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    project_root = Path(__file__).resolve().parent.parent.parent
    artifact_path = project_root / temp_dir / 'jobs' / job_id / 'validation' / 'validation_result.json'
    
    if artifact_path.exists():
        try:
            with open(artifact_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read validation result for {job_id}: {e}")
    return None
