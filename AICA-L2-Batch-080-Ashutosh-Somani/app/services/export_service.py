import os
import datetime
from pathlib import Path
from decimal import Decimal
import logging
from app.services.review_service import ReviewService
from app.services.audit_service import AuditService
from app.services.validation_service import ValidationService
from app.exporters.excel_exporter import ExcelExporter
from app.models.review import CorrectionStatus
from app.database.db import get_db_connection

logger = logging.getLogger(__name__)

class ExportService:
    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config.get('paths', 'output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.amount_format = config.get('excel', 'amount_format', fallback="#,##0.00")
        
        self.review_service = ReviewService(config)
        self.audit_service = AuditService(config)
        self.validation_service = ValidationService(config)

    def _get_masked_account(self, account_num):
        if not account_num:
            return ""
        if len(account_num) <= 4:
            return "****"
        return "*" * (len(account_num) - 4) + account_num[-4:]

    def _get_export_payload(self, job_id):
        # Determine source
        import json
        temp_base = Path(self.config.get('paths', 'temp', fallback='temp'))
        norm_path = temp_base / 'jobs' / job_id / 'normalization' / 'normalized_statement.json'
        norm_tx_count = 0
        if norm_path.exists():
            try:
                with open(norm_path, 'r', encoding='utf-8') as f:
                    norm_data_check = json.load(f)
                    norm_tx_count = len(norm_data_check.get('transactions', []))
            except Exception:
                norm_tx_count = 0

        rev_path = self.review_service.get_reviewed_statement_path(job_id)
        reviewed_stmt = None
        if rev_path.exists():
            candidate_stmt = self.review_service.load_reviewed_statement(job_id)
            if candidate_stmt and len(candidate_stmt.transactions) == 0 and norm_tx_count > 0:
                logger.warning(f"Rejecting reviewed statement for job {job_id} as stale (0 rows vs {norm_tx_count} normalized rows)")
                reviewed_stmt = None
            else:
                reviewed_stmt = candidate_stmt

        if reviewed_stmt:
            source_type = "Reviewed"
            revision = reviewed_stmt.review_revision
        else:
            source_type = "Machine Normalized"
            revision = None

        if reviewed_stmt:
            # We must use reviewed data and re-validate if needed
            self.review_service.trigger_revalidation(reviewed_stmt)
            vdata = self.review_service.load_reviewed_validation(job_id)
            from app.models.validation import StatementValidationResult, TransactionValidationResult
            from app.models.exception import ExceptionRecord
            val_summary = StatementValidationResult(**vdata.get('summary', {}))
            tx_validations = [TransactionValidationResult(**v) for v in vdata.get('transactions', [])]
            all_exceptions = [ExceptionRecord(**e) for e in vdata.get('exceptions', [])]
            
            transactions_data = []
            for i, tx in enumerate(reviewed_stmt.transactions):
                # Exclude NON_TRANSACTION and SUPERSEDED from financial transactions list
                if tx.review_status in [CorrectionStatus.NON_TRANSACTION, CorrectionStatus.SUPERSEDED]:
                    continue
                
                # Format to flat dict
                tx_dict = tx.to_dict()
                tx_dict['transaction_type'] = tx_dict.get('transaction_type', '')
                # Find matching validation
                val = next((v for v in tx_validations if v.transaction_index == i), None)
                tx_dict['validation_status'] = val.validation_status if val else ""
                tx_dict['review_status'] = tx.review_status.value if tx.review_status else ""
                
                transactions_data.append(tx_dict)
                
            # Load metadata from original normalization
            import json
            norm_path = Path(self.config.get('paths', 'temp')) / 'jobs' / job_id / 'normalization' / 'normalized_statement.json'
            if norm_path.exists():
                with open(norm_path, 'r') as f:
                    norm_data = json.load(f)
                    metadata = norm_data.get('metadata', {})
            else:
                metadata = {}
            audit_events = [e.to_dict() for e in self.audit_service.get_events(job_id)]
            
        else:
            # Machine normalized source
            import json
            norm_path = Path(self.config.get('paths', 'temp')) / 'jobs' / job_id / 'normalization' / 'normalized_statement.json'
            if not norm_path.exists():
                raise FileNotFoundError("Normalization data missing")
            with open(norm_path, 'r') as f:
                norm_data = json.load(f)
                
            transactions_data = []
            from app.models.validation import StatementValidationResult, TransactionValidationResult
            from app.models.exception import ExceptionRecord
            
            # Load machine validation
            val_path = Path(self.config.get('paths', 'temp')) / 'jobs' / job_id / 'validation' / 'validation_result.json'
            if val_path.exists():
                with open(val_path, 'r') as f:
                    vdata = json.load(f)
                    val_summary = StatementValidationResult(**vdata['summary'])
                    tx_validations = [TransactionValidationResult(**v) for v in vdata['transactions']]
                    all_exceptions = [ExceptionRecord(**e) for e in vdata['exceptions']]
            else:
                val_summary, tx_validations, all_exceptions = self.validation_service.validate_statement(job_id)
                
            for i, tx in enumerate(norm_data.get('transactions', [])):
                tx_dict = tx.copy()
                for k in ['debit', 'credit', 'balance']:
                    if tx_dict.get(k) is not None:
                        tx_dict[k] = Decimal(str(tx_dict[k]))
                
                # Parse dates correctly if we want openpyxl to treat them as dates (skip for simplicity if None)
                if tx_dict.get('transaction_date'):
                    try:
                        tx_dict['transaction_date'] = datetime.datetime.strptime(tx_dict['transaction_date'], '%Y-%m-%d').date()
                    except ValueError:
                        pass
                if tx_dict.get('value_date'):
                    try:
                        tx_dict['value_date'] = datetime.datetime.strptime(tx_dict['value_date'], '%Y-%m-%d').date()
                    except ValueError:
                        pass

                val = next((v for v in tx_validations if v.transaction_index == i), None)
                tx_dict['validation_status'] = val.validation_status if val else ""
                tx_dict['review_status'] = "UNREVIEWED"
                tx_dict['user_corrected'] = False
                transactions_data.append(tx_dict)
                
            metadata = norm_data.get('metadata', {})
            audit_events = []

        # Exceptions filter (unresolved only)
        # Note: In our system all current exceptions are by definition unresolved.
        exceptions_data = []
        for e in all_exceptions:
            d = e.to_dict()
            # If reviewing, we can attach the transaction_id
            if reviewed_stmt and d.get('transaction_index') is not None:
                # find tx id
                if d['transaction_index'] < len(reviewed_stmt.transactions):
                    d['transaction_id'] = reviewed_stmt.transactions[d['transaction_index']].transaction_id
            exceptions_data.append(d)

        # Build summary
        with get_db_connection(self.config) as conn:
            job_row = conn.execute("SELECT display_name, sha256 FROM processing_jobs WHERE id=?", (job_id,)).fetchone()
            
        # Check OCR usage
        ocr_used = "No"
        if any(tx.get('source_type') == 'OCR' for tx in transactions_data):
            ocr_used = "Yes"

        summary = {
            "export_source": source_type,
            "review_revision": revision,
            "ocr_used": ocr_used,
            "app_version": self.config.get('application', 'version', fallback='0.8.0'),
            "bank_name": metadata.get("bank_name", ""),
            "account_holder": metadata.get("account_holder", ""),
            "account_number": self._get_masked_account(metadata.get("account_number", "")),
            "ifsc": metadata.get("ifsc", ""),
            "statement_period": f"{metadata.get('period_start','')} to {metadata.get('period_end','')}",
            "opening_balance": getattr(val_summary, 'opening_balance', None),
            "total_debits": getattr(val_summary, 'total_debits', None),
            "total_credits": getattr(val_summary, 'total_credits', None),
            "expected_closing_balance": getattr(val_summary, 'expected_closing_balance', None),
            "statement_closing_balance": getattr(val_summary, 'statement_closing_balance', None),
            "difference": getattr(val_summary, 'difference', None),
            "transaction_count": len(transactions_data),
            "corrected_transaction_count": sum(1 for t in transactions_data if t.get('user_corrected')),
            "exceptions_count": len(exceptions_data),
            "critical_exceptions": sum(1 for e in exceptions_data if e.get('severity') == 'CRITICAL'),
            "error_exceptions": sum(1 for e in exceptions_data if e.get('severity') == 'ERROR'),
            "warning_exceptions": sum(1 for e in exceptions_data if e.get('severity') == 'WARNING'),
            "validation_result": getattr(val_summary, 'validation_status', 'UNKNOWN'),
            "export_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_filename": job_row['display_name'] if job_row else "",
            "source_sha256": job_row['sha256'] if job_row else ""
        }
        
        # Convert Decimals in summary safely
        for k in ['opening_balance', 'total_debits', 'total_credits', 'expected_closing_balance', 'statement_closing_balance', 'difference']:
            if summary[k] is not None:
                summary[k] = Decimal(str(summary[k]))

        return {
            'transactions': transactions_data,
            'summary': summary,
            'exceptions': exceptions_data,
            'audit': audit_events,
            'source_filename': summary['source_filename']
        }

    def _get_safe_filename(self, job_id, original_name):
        import re
        safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', original_name)
        base = Path(safe_name).stem
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base}_validated_{timestamp}.xlsx"
        
        # Check collision
        filepath = self.output_dir / filename
        counter = 1
        while filepath.exists():
            filename = f"{base}_validated_{timestamp}_{counter}.xlsx"
            filepath = self.output_dir / filename
            counter += 1
            
        return filepath

    def export_excel(self, job_id, progress_callback=None):
        if progress_callback: progress_callback(10, "Preparing current dataset")
        payload = self._get_export_payload(job_id)
        
        if progress_callback: progress_callback(30, "Validating export source")
        filepath = self._get_safe_filename(job_id, payload['source_filename'])
        
        exporter = ExcelExporter(self.amount_format)
        exporter.export(filepath, payload, progress_callback=progress_callback)
        
        # Save to export history
        with get_db_connection(self.config) as conn:
            try:
                conn.execute('''
                    INSERT INTO export_history 
                    (job_id, filename, source_type, review_revision, validation_status, application_version) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    job_id, 
                    filepath.name, 
                    payload['summary']['export_source'],
                    payload['summary']['review_revision'],
                    payload['summary']['validation_result'],
                    payload['summary']['app_version']
                ))
                conn.commit()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to write to export_history: {e}")
        
        return filepath
