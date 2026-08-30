import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from app.models.review import ReviewedStatement, CorrectionStatus
from app.services.review_service import ReviewService
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

class CorrectionService:
    def __init__(self, review_service: ReviewService, audit_service: AuditService, profile_suggestion_service=None):
        self.review_service = review_service
        self.audit_service = audit_service
        self.profile_suggestion_service = profile_suggestion_service

    def _parse_decimal(self, val: Any) -> Optional[Decimal]:
        if val is None or str(val).strip() == "":
            return None
        return Decimal(str(val).replace(",", "").strip())

    def apply_edit(self, job_id: str, expected_revision: int, transaction_id: str, field_updates: Dict[str, Any], reason: Optional[str] = None) -> ReviewedStatement:
        statement = self.review_service.load_reviewed_statement(job_id)
        
        if statement.review_revision != expected_revision:
            raise ValueError("REVIEW_REVISION_CONFLICT")
            
        tx = next((t for t in statement.transactions if t.transaction_id == transaction_id), None)
        if not tx:
            raise ValueError(f"Transaction {transaction_id} not found.")
            
        revision_before = statement.review_revision
        statement.review_revision += 1
        
        # apply edits and audit
        for field_name, new_val in field_updates.items():
            if field_name not in ['transaction_date', 'value_date', 'narration', 'reference_number', 'cheque_number', 'debit', 'credit', 'balance']:
                continue
                
            old_val = getattr(tx, field_name)
            
            parsed_new_val = new_val
            if field_name in ['debit', 'credit', 'balance']:
                parsed_new_val = self._parse_decimal(new_val)
                
            # format values for audit
            str_old = str(old_val) if old_val is not None else None
            str_new = str(parsed_new_val) if parsed_new_val is not None else None
            
            if str_old != str_new:
                setattr(tx, field_name, parsed_new_val)
                tx.user_corrected = True
                tx.correction_count += 1
                tx.review_status = CorrectionStatus.CORRECTED
                
                event = self.audit_service.create_event(
                    job_id=job_id,
                    action="FIELD_EDIT",
                    transaction_id=transaction_id,
                    field_name=field_name,
                    before_value=str_old,
                    after_value=str_new,
                    reason=reason,
                    source_page=tx.source_page,
                    source_row=tx.source_row,
                    review_revision_before=revision_before,
                    review_revision_after=statement.review_revision
                )
                if self.profile_suggestion_service:
                    self.profile_suggestion_service.generate_suggestion(job_id, event)
                
        self.review_service.trigger_revalidation(statement)
        self.review_service.save_reviewed_statement(statement)
        return statement

    def mark_non_transaction(self, job_id: str, expected_revision: int, transaction_id: str, reason: Optional[str] = None) -> ReviewedStatement:
        statement = self.review_service.load_reviewed_statement(job_id)
        if statement.review_revision != expected_revision: raise ValueError("REVIEW_REVISION_CONFLICT")
        
        tx = next((t for t in statement.transactions if t.transaction_id == transaction_id), None)
        if not tx: raise ValueError("Not found")
        
        rev_before = statement.review_revision
        statement.review_revision += 1
        
        old_status = tx.review_status.value
        tx.review_status = CorrectionStatus.NON_TRANSACTION
        tx.user_corrected = True
        
        event = self.audit_service.create_event(
            job_id=job_id, action="MARK_NON_TRANSACTION", transaction_id=transaction_id,
            before_value=old_status, after_value="NON_TRANSACTION", reason=reason,
            review_revision_before=rev_before, review_revision_after=statement.review_revision
        )
        if self.profile_suggestion_service:
            self.profile_suggestion_service.generate_suggestion(job_id, event)
        
        self.review_service.trigger_revalidation(statement)
        self.review_service.save_reviewed_statement(statement)
        return statement

    def revert_transaction(self, job_id: str, expected_revision: int, transaction_id: str) -> ReviewedStatement:
        statement = self.review_service.load_reviewed_statement(job_id)
        if statement.review_revision != expected_revision: raise ValueError("REVIEW_REVISION_CONFLICT")
        
        tx = next((t for t in statement.transactions if t.transaction_id == transaction_id), None)
        if not tx: raise ValueError("Not found")
        
        rev_before = statement.review_revision
        statement.review_revision += 1
        
        # Load baseline to revert
        import json
        baseline_path = self.review_service.temp_dir / 'jobs' / job_id / 'normalization' / 'normalized_statement.json'
        with open(baseline_path, 'r', encoding='utf-8') as f:
            baseline_data = json.load(f)
            
        orig_tx_dict = next((bt for bt in baseline_data.get("transactions", []) 
                             if bt.get("source_row") == tx.source_row and bt.get("source_page") == tx.source_page), None)
                             
        if orig_tx_dict:
            tx.transaction_date = orig_tx_dict.get("transaction_date")
            tx.value_date = orig_tx_dict.get("value_date")
            tx.narration = orig_tx_dict.get("narration", "")
            tx.reference_number = orig_tx_dict.get("reference_number")
            tx.cheque_number = orig_tx_dict.get("cheque_number")
            
            if orig_tx_dict.get("debit") is not None: tx.debit = Decimal(str(orig_tx_dict["debit"]))
            else: tx.debit = None
            if orig_tx_dict.get("credit") is not None: tx.credit = Decimal(str(orig_tx_dict["credit"]))
            else: tx.credit = None
            if orig_tx_dict.get("balance") is not None: tx.balance = Decimal(str(orig_tx_dict["balance"]))
            else: tx.balance = None
            
            tx.user_corrected = False
            tx.review_status = CorrectionStatus.UNREVIEWED
            
            event = self.audit_service.create_event(
                job_id=job_id, action="REVERT_CORRECTION", transaction_id=transaction_id,
                review_revision_before=rev_before, review_revision_after=statement.review_revision
            )
            if self.profile_suggestion_service:
                self.profile_suggestion_service.generate_suggestion(job_id, event)
            
        self.review_service.trigger_revalidation(statement)
        self.review_service.save_reviewed_statement(statement)
        return statement

    def merge_rows(self, job_id: str, expected_revision: int, parent_ids: list[str], merged_data: Dict[str, Any]) -> ReviewedStatement:
        import uuid
        statement = self.review_service.load_reviewed_statement(job_id)
        if statement.review_revision != expected_revision: raise ValueError("REVIEW_REVISION_CONFLICT")
        
        parents = [t for t in statement.transactions if t.transaction_id in parent_ids]
        if len(parents) != len(parent_ids): raise ValueError("Not all parents found")
        
        rev_before = statement.review_revision
        statement.review_revision += 1
        
        for p in parents:
            p.review_status = CorrectionStatus.SUPERSEDED
            
        new_id = str(uuid.uuid4())
        from app.models.review import ReviewedTransaction
        new_tx = ReviewedTransaction(
            transaction_id=new_id,
            original_transaction_id=parents[0].original_transaction_id,
            derived_from_transaction_ids=parent_ids,
            transaction_date=merged_data.get("transaction_date"),
            value_date=merged_data.get("value_date"),
            narration=merged_data.get("narration", ""),
            reference_number=merged_data.get("reference_number"),
            cheque_number=merged_data.get("cheque_number"),
            debit=self._parse_decimal(merged_data.get("debit")),
            credit=self._parse_decimal(merged_data.get("credit")),
            balance=self._parse_decimal(merged_data.get("balance")),
            source_page=parents[0].source_page,
            user_corrected=True,
            review_status=CorrectionStatus.MERGED_RESULT
        )
        statement.transactions.append(new_tx)
        
        event = self.audit_service.create_event(
            job_id=job_id, action="ROW_MERGE", transaction_id=new_id, affected_transaction_ids=parent_ids,
            review_revision_before=rev_before, review_revision_after=statement.review_revision
        )
        if self.profile_suggestion_service:
            self.profile_suggestion_service.generate_suggestion(job_id, event)
        
        self.review_service.trigger_revalidation(statement)
        self.review_service.save_reviewed_statement(statement)
        return statement

    def split_row(self, job_id: str, expected_revision: int, parent_id: str, child_data_list: list[Dict[str, Any]]) -> ReviewedStatement:
        import uuid
        statement = self.review_service.load_reviewed_statement(job_id)
        if statement.review_revision != expected_revision: raise ValueError("REVIEW_REVISION_CONFLICT")
        
        parent = next((t for t in statement.transactions if t.transaction_id == parent_id), None)
        if not parent: raise ValueError("Parent not found")
        
        rev_before = statement.review_revision
        statement.review_revision += 1
        
        parent.review_status = CorrectionStatus.SUPERSEDED
        
        child_ids = []
        from app.models.review import ReviewedTransaction
        for cdata in child_data_list:
            new_id = str(uuid.uuid4())
            child_ids.append(new_id)
            new_tx = ReviewedTransaction(
                transaction_id=new_id,
                original_transaction_id=parent.original_transaction_id,
                derived_from_transaction_ids=[parent_id],
                transaction_date=cdata.get("transaction_date"),
                value_date=cdata.get("value_date"),
                narration=cdata.get("narration", ""),
                reference_number=cdata.get("reference_number"),
                cheque_number=cdata.get("cheque_number"),
                debit=self._parse_decimal(cdata.get("debit")),
                credit=self._parse_decimal(cdata.get("credit")),
                balance=self._parse_decimal(cdata.get("balance")),
                source_page=parent.source_page,
                user_corrected=True,
                review_status=CorrectionStatus.SPLIT_CHILD
            )
            statement.transactions.append(new_tx)
            
        event = self.audit_service.create_event(
            job_id=job_id, action="ROW_SPLIT", transaction_id=parent_id, affected_transaction_ids=child_ids,
            review_revision_before=rev_before, review_revision_after=statement.review_revision
        )
        if self.profile_suggestion_service:
            self.profile_suggestion_service.generate_suggestion(job_id, event)
        
        self.review_service.trigger_revalidation(statement)
        self.review_service.save_reviewed_statement(statement)
        return statement
        
    def restore_transaction(self, job_id: str, expected_revision: int, transaction_id: str, reason: Optional[str] = None) -> ReviewedStatement:
        statement = self.review_service.load_reviewed_statement(job_id)
        if statement.review_revision != expected_revision: raise ValueError("REVIEW_REVISION_CONFLICT")
        
        tx = next((t for t in statement.transactions if t.transaction_id == transaction_id), None)
        if not tx: raise ValueError("Not found")
        
        rev_before = statement.review_revision
        statement.review_revision += 1
        
        old_status = tx.review_status.value
        tx.review_status = CorrectionStatus.CORRECTED if tx.user_corrected else CorrectionStatus.REVIEWED
        
        self.audit_service.create_event(
            job_id=job_id, action="RESTORE_TRANSACTION", transaction_id=transaction_id,
            before_value=old_status, after_value=tx.review_status.value, reason=reason,
            review_revision_before=rev_before, review_revision_after=statement.review_revision
        )
        
        self.review_service.trigger_revalidation(statement)
        self.review_service.save_reviewed_statement(statement)
        return statement
