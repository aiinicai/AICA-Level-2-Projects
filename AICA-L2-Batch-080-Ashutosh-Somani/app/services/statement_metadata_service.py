import re
from typing import Optional
from app.models.statement import StatementMetadata
from app.utils.amount_utils import parse_amount
from app.utils.date_utils import parse_date

class StatementMetadataService:
    def extract_metadata(self, raw_text: str, default_date_order: str = 'DMY') -> StatementMetadata:
        """
        Generically extracts statement metadata using conservative regexes.
        """
        meta = StatementMetadata()
        
        # Account Number
        # Look for A/C No, Account No, Account Number followed by digits
        ac_match = re.search(r'(?:A/C\s*NO|ACCOUNT\s*NO|ACCOUNT\s*NUMBER)[\s\.:-]*([0-9A-Z]{6,20})', raw_text, re.IGNORECASE)
        if ac_match:
            meta.account_number = ac_match.group(1)
            
        # IFSC
        ifsc_match = re.search(r'(?:IFSC|RTGS).*?([A-Z]{4}0[A-Z0-9]{6})', raw_text, re.IGNORECASE)
        if ifsc_match:
            meta.ifsc = ifsc_match.group(1).upper()
            
        # Generic Period extraction
        period_match = re.search(r'(?:STATEMENT\s*PERIOD|PERIOD|FROM)[\s\.:-]*(\d{1,2}[-/\.][A-Z0-9]+[-/\.]\d{2,4})\s*(?:TO|-|AND)\s*(\d{1,2}[-/\.][A-Z0-9]+[-/\.]\d{2,4})', raw_text, re.IGNORECASE)
        if period_match:
            start_date, _ = parse_date(period_match.group(1), default_date_order)
            end_date, _ = parse_date(period_match.group(2), default_date_order)
            if start_date:
                meta.statement_start_date = start_date.isoformat()
            if end_date:
                meta.statement_end_date = end_date.isoformat()
                
        return meta
