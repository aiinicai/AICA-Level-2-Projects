"""Date utility functions for parsing Indian banking transaction dates and FY calculation."""

from datetime import datetime, date
from typing import Optional, Tuple
import re

DATE_PATTERNS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d-%b-%Y",
    "%d %B %Y",
    "%d-%B-%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d.%m.%y",
    "%d %b %y",
    "%d-%b-%y",
]

def parse_date(date_str: any) -> Optional[date]:
    """Parse various string representations of dates into a datetime.date object."""
    if date_str is None:
        return None
    if isinstance(date_str, (datetime, date)):
        return date_str.date() if isinstance(date_str, datetime) else date_str
    
    text = str(date_str).strip()
    if not text or text.lower() in ("nan", "nat", "none", "-", ""):
        return None
    
    # Clean string - remove time part if present (e.g., "15/04/2024 10:30:00")
    text = re.split(r'[\sT]+', text)[0]
    
    for fmt in DATE_PATTERNS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
            
    # Try dateutil parser if standard formats fail
    try:
        from dateutil import parser as dt_parser
        dt = dt_parser.parse(text, dayfirst=True)
        return dt.date()
    except Exception:
        pass
        
    return None

def get_financial_year(dt: date) -> str:
    """Return Financial Year string in format FY 2024-25 for an Indian accounting year (Apr-Mar)."""
    if not dt:
        return "Unknown"
    year = dt.year
    if dt.month >= 4:
        return f"FY {year}-{(year + 1) % 100:02d}"
    else:
        return f"FY {year - 1}-{year % 100:02d}"

def get_fy_quarter(dt: date) -> str:
    """Return FY Quarter string (Q1: Apr-Jun, Q2: Jul-Sep, Q3: Oct-Dec, Q4: Jan-Mar)."""
    if not dt:
        return "Unknown"
    m = dt.month
    if 4 <= m <= 6:
        return "Q1 (Apr-Jun)"
    elif 7 <= m <= 9:
        return "Q2 (Jul-Sep)"
    elif 10 <= m <= 12:
        return "Q3 (Oct-Dec)"
    else:
        return "Q4 (Jan-Mar)"

def get_month_year(dt: date) -> str:
    """Return formatted Month-Year string (e.g. 'Apr 2024')."""
    if not dt:
        return "Unknown"
    return dt.strftime("%b %Y")

def get_month_sort_key(dt: date) -> str:
    """Return YYYY-MM sortable string."""
    if not dt:
        return "9999-99"
    return dt.strftime("%Y-%m")
