import datetime
import re
from typing import Optional, Tuple

MONTHS = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'september': 9, 'sept': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
}

def parse_date(date_str: str, default_order: str = 'DMY') -> Tuple[Optional[datetime.date], str]:
    """
    Parses a date string safely without external dependencies.
    Returns (date_obj, status)
    """
    if not date_str or not date_str.strip():
        return None, "empty"
        
    s = re.sub(r'\s+', ' ', date_str.strip()).lower()
    
    # 1. YYYY-MM-DD
    m = re.match(r'^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$', s)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), "success"
        except ValueError:
            return None, "invalid_date"

    # 2. DD MMM YYYY or DD-MMM-YYYY
    m = re.match(r'^(\d{1,2})[-/.\s]+([a-z]{3,9})[-/.\s]+(\d{2,4})$', s)
    if m:
        day = int(m.group(1))
        month_str = m.group(2)
        year = int(m.group(3))
        
        if month_str not in MONTHS:
            return None, "invalid_month_string"
        month = MONTHS[month_str]
        
        if year < 100:
            year += 2000
            
        try:
            return datetime.date(year, month, day), "success"
        except ValueError:
            return None, "invalid_date"
            
    # 3. DD/MM/YYYY or MM/DD/YYYY based on default_order
    m = re.match(r'^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$', s)
    if m:
        p1 = int(m.group(1))
        p2 = int(m.group(2))
        year = int(m.group(3))
        if year < 100:
            year += 2000
            
        if default_order == 'DMY':
            day, month = p1, p2
        else: # MDY
            month, day = p1, p2
            
        try:
            return datetime.date(year, month, day), "success"
        except ValueError:
            return None, "invalid_date"
            
    return None, "unparseable"
