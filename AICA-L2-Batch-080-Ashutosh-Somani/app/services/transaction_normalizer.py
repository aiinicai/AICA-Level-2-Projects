from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from app.models.transaction import Transaction
from app.utils.date_utils import parse_date
from app.utils.amount_utils import parse_amount
import logging

logger = logging.getLogger(__name__)

class TransactionNormalizer:
    def __init__(self, default_date_order: str = 'DMY'):
        self.default_date_order = default_date_order
        
    def _map_headers(self, headers: List[str]) -> Dict[str, int]:
        """
        Generically map header strings to canonical names.
        Returns a mapping of {canonical_name: column_index}.
        """
        mapping = {}
        for idx, header in enumerate(headers):
            h = (header or '').strip().lower()
            if not h: continue
            
            if 'date' in h and 'txn' not in h and 'value' not in h:
                mapping['transaction_date'] = idx
            elif 'txn date' in h or 'transaction date' in h:
                mapping['transaction_date'] = idx
            elif 'value date' in h:
                mapping['value_date'] = idx
            elif h in ['narration', 'particulars', 'description', 'transaction details']:
                mapping['narration'] = idx
            elif h in ['reference', 'reference no', 'ref no', 'ref']:
                mapping['reference_number'] = idx
            elif h in ['cheque no', 'chq no']:
                mapping['cheque_number'] = idx
            elif h in ['debit', 'withdrawal', 'withdrawal amount']:
                mapping['debit'] = idx
            elif h in ['credit', 'deposit', 'deposit amount']:
                mapping['credit'] = idx
            elif h in ['amount']:
                mapping['amount'] = idx
            elif h in ['cr/dr', 'cr / dr', 'type', 'dr_cr']:
                mapping['dr_cr'] = idx
            elif h in ['balance', 'closing balance']:
                mapping['balance'] = idx
            
            # Direct canonical name match (for Profile Coordinate Extractor)
            if h in ['transaction_date', 'value_date', 'narration', 'reference_number', 'cheque_number', 'debit', 'credit', 'amount', 'dr_cr', 'balance']:
                mapping[h] = idx
                
        return mapping

    def _is_transaction_table(self, mapping: Dict[str, int]) -> bool:
        """
        Determine if the mapped headers constitute a valid transaction table.
        Needs a date, and either (debit and credit) OR (amount and dr_cr).
        """
        has_date = 'transaction_date' in mapping
        has_dr_cr = ('debit' in mapping and 'credit' in mapping)
        has_amt_type = ('amount' in mapping and 'dr_cr' in mapping)
        
        return has_date and (has_dr_cr or has_amt_type)

    def normalize(self, raw_tables: List[dict]) -> Tuple[List[Transaction], List[str]]:
        transactions = []
        warnings = []
        
        # 1. Identify Candidate Tables (one per page)
        valid_tables_by_page = {}
        target_mappings = {}
        
        for table in raw_tables:
            if not table.get('cells') or len(table['cells']) < 2:
                continue
                
            page_num = table.get('page_number', 1)
                
            # Assume first row is header
            headers = [str(c) if c else '' for c in table['cells'][0]]
            mapping = self._map_headers(headers)
            
            if self._is_transaction_table(mapping):
                if page_num in valid_tables_by_page:
                    warnings.append(f"ambiguous_table_mapping: Multiple valid transaction tables found on page {page_num}. Selected first.")
                    continue # Skip duplicates on the same page
                valid_tables_by_page[page_num] = table
                target_mappings[page_num] = mapping
                
        if not valid_tables_by_page:
            warnings.append("no_transaction_table")
            return transactions, warnings
            
        # 2. Process Rows Page by Page
        sorted_pages = sorted(valid_tables_by_page.keys())
        
        for page_num in sorted_pages:
            target_table = valid_tables_by_page[page_num]
            target_mapping = target_mappings[page_num]
            
            headers = [str(c) if c else '' for c in target_table['cells'][0]]
            rows = target_table['cells'][1:]
            
            for row_idx, row in enumerate(rows):
                # Safe cell fetch
                def get_cell(col_name: str) -> str:
                    if col_name in target_mapping:
                        idx = target_mapping[col_name]
                        if idx < len(row):
                            return (row[idx] or '').strip()
                    return ''
    
                raw_date = get_cell('transaction_date')
                raw_narration = get_cell('narration')
                raw_ref = get_cell('reference_number')
                raw_bal = get_cell('balance')
                
                # Repeated header check
                if [str(c).strip().lower() for c in row] == [h.strip().lower() for h in headers]:
                    continue
                    
                # Footer filtering
                if 'page' in raw_date.lower() and len(row) <= 2: # heuristic for simple footers
                    continue
    
                date_val, date_status = parse_date(raw_date, self.default_date_order)
                
                # Multiline continuation logic:
                if not date_val and raw_narration and not any([get_cell('debit'), get_cell('credit'), get_cell('amount'), raw_bal]):
                    # If we have a previous transaction, append
                    if transactions:
                        prev_txn = transactions[-1]
                        if prev_txn.narration:
                            prev_txn.narration += " " + raw_narration
                        else:
                            prev_txn.narration = raw_narration
                        # We consider it handled
                        continue
                    else:
                        warnings.append(f"continuation_unresolved: page {page_num} row {row_idx+1}")
                        continue
                
                if not date_val and not raw_narration and not any([get_cell('debit'), get_cell('credit'), get_cell('amount'), raw_bal]):
                    continue # completely empty row
                    
                if not date_val and any([get_cell('debit'), get_cell('credit'), get_cell('amount')]):
                    warnings.append(f"unresolved_ambiguous_row: date-less row with amounts at page {page_num} row {row_idx+1}")
                    continue
                    
                txn = Transaction(
                    source_page=target_table.get('page_number'),
                    source_row=row_idx + 1,
                    source_type=target_table.get('source_type', 'DIGITAL'),
                    ocr_confidence=target_table.get('ocr_confidence', None),
                    raw_date=raw_date,
                    raw_narration=raw_narration,
                    raw_reference=raw_ref,
                    raw_balance=raw_bal,
                    transaction_date=date_val,
                    narration=raw_narration,
                    reference_number=raw_ref
                )
                
                if date_status != 'success':
                    txn.normalization_warnings.append("unparseable_date")
                    
                # Parse Amounts
                # Case A: Debit / Credit
                if 'debit' in target_mapping and 'credit' in target_mapping:
                    raw_dr = get_cell('debit')
                    raw_cr = get_cell('credit')
                    txn.raw_debit = raw_dr
                    txn.raw_credit = raw_cr
                    
                    dr_val, _ = parse_amount(raw_dr)
                    cr_val, _ = parse_amount(raw_cr)
                    
                    if dr_val is not None and cr_val is None:
                        txn.debit = dr_val
                        txn.credit = None
                        txn.transaction_type = 'Debit'
                    elif cr_val is not None and dr_val is None:
                        txn.debit = None
                        txn.credit = cr_val
                        txn.transaction_type = 'Credit'
                    elif dr_val is not None and cr_val is not None:
                        txn.debit = dr_val
                        txn.credit = cr_val
                        if dr_val > 0 and cr_val == 0:
                            txn.transaction_type = 'Debit'
                        elif cr_val > 0 and dr_val == 0:
                            txn.transaction_type = 'Credit'
                        else:
                            txn.transaction_type = None
                    else:
                        txn.debit = None
                        txn.credit = None
                        txn.transaction_type = None
                    
                # Case B: Amount + CR/DR type
                elif 'amount' in target_mapping and 'dr_cr' in target_mapping:
                    raw_amt = get_cell('amount')
                    raw_type = get_cell('dr_cr')
                    txn.raw_debit = raw_amt if 'DR' in raw_type.upper() or 'D' in raw_type.upper() else ''
                    txn.raw_credit = raw_amt if 'CR' in raw_type.upper() or 'C' in raw_type.upper() else ''
                    
                    amt_val, hint = parse_amount(raw_amt)
                    
                    if hint == 'CR' or 'CR' in raw_type.upper() or 'C' == raw_type.upper():
                        txn.credit = amt_val
                        txn.transaction_type = 'Credit'
                    elif hint == 'DR' or 'DR' in raw_type.upper() or 'D' == raw_type.upper():
                        txn.debit = amt_val
                        txn.transaction_type = 'Debit'
                    elif amt_val is not None:
                        # Ambiguous
                        txn.normalization_warnings.append("ambiguous_direction")
                        # Put it in debit as a fallback for now? No, do not guess!
                        pass
    
                bal_val, bal_hint = parse_amount(raw_bal)
                if bal_val is not None:
                    if bal_hint == 'DR':
                        txn.balance = -bal_val
                    else:
                        txn.balance = bal_val
                elif raw_bal:
                     txn.normalization_warnings.append("malformed_amount: balance")
                     
                # Error check
                if txn.debit is None and txn.credit is None and (txn.raw_debit or txn.raw_credit):
                     txn.normalization_warnings.append("malformed_amount")
                     
                if len(txn.normalization_warnings) > 0:
                    txn.normalization_status = "warning"
                else:
                    txn.normalization_status = "success"
                    
                transactions.append(txn)
                
        return transactions, warnings
