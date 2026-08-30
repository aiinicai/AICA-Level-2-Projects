import json
import logging
import uuid
import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from app.models.review import ReviewedStatement, ReviewedTransaction, ReviewStatus, CorrectionStatus
from app.services.validation_service import ValidationService
from app.database.db import get_db_connection

logger = logging.getLogger(__name__)

class ReviewService:
    def __init__(self, config):
        self.config = config
        
        if hasattr(config, 'get') and hasattr(config, 'read'):
            temp_dir_str = config.get('paths', 'temp', fallback='temp')
        elif hasattr(config, 'get') and 'APP_CONFIG' in config:
            temp_dir_str = config['APP_CONFIG'].get('paths', 'temp', fallback='temp')
        else:
            temp_dir_str = 'temp'
        self.temp_dir = Path(temp_dir_str)
        self.validator = ValidationService(config)

    def get_review_dir(self, job_id: str) -> Path:
        return self.temp_dir / 'jobs' / job_id / 'review'
        
    def get_reviewed_statement_path(self, job_id: str) -> Path:
        return self.get_review_dir(job_id) / 'reviewed_statement.json'

    def get_reviewed_validation_path(self, job_id: str) -> Path:
        return self.get_review_dir(job_id) / 'reviewed_validation.json'

    def initialize_review(self, job_id: str) -> ReviewedStatement:
        """
        Creates the isolated review artifact from the machine baseline if it doesn't exist.
        """
        review_dir = self.get_review_dir(job_id)
        review_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = self.get_reviewed_statement_path(job_id)
        if file_path.exists():
            return self.load_reviewed_statement(job_id)
            
        # Load machine baseline
        baseline_path = self.temp_dir / 'jobs' / job_id / 'normalization' / 'normalized_statement.json'
        if not baseline_path.exists():
            raise FileNotFoundError(f"Machine baseline missing for job {job_id}")
            
        with open(baseline_path, 'r', encoding='utf-8') as f:
            baseline_data = json.load(f)
            
        statement = ReviewedStatement(
            job_id=job_id,
            review_revision=1,
            review_status=ReviewStatus.IN_PROGRESS
        )
        
        for tx in baseline_data.get("transactions", []):
            tx_id = str(uuid.uuid4())
            rtx = ReviewedTransaction(
                transaction_id=tx_id,
                original_transaction_id=tx_id,
                transaction_date=tx.get("transaction_date"),
                value_date=tx.get("value_date"),
                narration=tx.get("narration", ""),
                reference_number=tx.get("reference_number"),
                cheque_number=tx.get("cheque_number"),
                source_page=tx.get("source_page"),
                source_row=tx.get("source_row"),
                extractor_used=baseline_data.get("extractor_used"),
                profile_used=baseline_data.get("profile_used")
            )
            # Safely set decimals
            from decimal import Decimal
            if tx.get("debit") is not None: rtx.debit = Decimal(str(tx["debit"]))
            if tx.get("credit") is not None: rtx.credit = Decimal(str(tx["credit"]))
            if tx.get("balance") is not None: rtx.balance = Decimal(str(tx["balance"]))
            
            statement.transactions.append(rtx)
            
        self.save_reviewed_statement(statement)
        
        # Copy initial validation
        val_baseline = self.temp_dir / 'jobs' / job_id / 'validation' / 'validation_result.json'
        if val_baseline.exists():
            with open(val_baseline, 'r') as f:
                val_data = json.load(f)
            with open(self.get_reviewed_validation_path(job_id), 'w') as f:
                json.dump(val_data, f)
                
        # Update SQLite status
        with get_db_connection(self.config) as conn:
            conn.execute("UPDATE processing_jobs SET review_status = 'IN_PROGRESS', review_revision = 1 WHERE id = ?", (job_id,))
            conn.commit()
            
        return statement

    def load_reviewed_statement(self, job_id: str) -> ReviewedStatement:
        path = self.get_reviewed_statement_path(job_id)
        if not path.exists():
            return self.initialize_review(job_id)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return ReviewedStatement.from_dict(data)
            
    def load_reviewed_validation(self, job_id: str) -> Dict[str, Any]:
        path = self.get_reviewed_validation_path(job_id)
        if not path.exists():
            val_baseline = self.temp_dir / 'jobs' / job_id / 'validation' / 'validation_result.json'
            if val_baseline.exists():
                with open(val_baseline, 'r') as f: return json.load(f)
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_reviewed_statement(self, statement: ReviewedStatement) -> None:
        path = self.get_reviewed_statement_path(statement.job_id)
        temp_path = path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(statement.to_dict(), f, indent=2)
        temp_path.replace(path)

    def trigger_revalidation(self, statement: ReviewedStatement) -> Dict[str, Any]:
        """
        Runs the full Stage 5 validator on the reviewed dataset.
        Returns the new validation result dictionary.
        """
        # Map ReviewedStatement -> Dictionary expected by _perform_validation
        
        # Only include active transactions
        active_txns = [t for t in statement.transactions if t.review_status not in (CorrectionStatus.SUPERSEDED, CorrectionStatus.NON_TRANSACTION)]
        
        norm_dict = {
            "job_id": statement.job_id,
            "metadata": {},
            "transactions": []
        }
        
        for t in active_txns:
            tx_dict = {
                "transaction_id": t.transaction_id,  # Added dynamically
                "transaction_date": t.transaction_date,
                "value_date": t.value_date,
                "narration": t.narration,
                "reference_number": t.reference_number,
                "cheque_number": t.cheque_number,
                "debit": float(t.debit) if t.debit is not None else None,
                "credit": float(t.credit) if t.credit is not None else None,
                "balance": float(t.balance) if t.balance is not None else None,
                "source_page": t.source_page,
                "source_row": t.source_row
            }
            norm_dict["transactions"].append(tx_dict)
            
        val_summary, tx_results, all_exceptions = self.validator._perform_validation(norm_dict)
        
        # Determine overall review status
        is_valid = val_summary.validation_status == "VALID"
        statement.review_status = ReviewStatus.REVIEWED_VALID if is_valid else ReviewStatus.REVIEWED_WITH_EXCEPTIONS
        
        # Save validation output
        val_path = self.get_reviewed_validation_path(statement.job_id)
        temp_path = val_path.with_suffix('.tmp')
        
        result_dict = {
            "summary": val_summary.to_dict(),
            "transactions": [tx.to_dict() for tx in tx_results],
            "exceptions": [ex.to_dict() for ex in all_exceptions]
        }
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2)
        temp_path.replace(val_path)
        
        # Update DB aggregate
        with get_db_connection(self.config) as conn:
            conn.execute("""
                UPDATE processing_jobs 
                SET review_status = ?, review_revision = ?, review_exception_count = ?, last_reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (statement.review_status.value, statement.review_revision, len(all_exceptions), statement.job_id))
            conn.commit()
            
        return result_dict
