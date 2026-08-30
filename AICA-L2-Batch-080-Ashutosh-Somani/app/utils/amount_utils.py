from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple
import re

def parse_amount(amount_str: str) -> Tuple[Optional[Decimal], str]:
    """
    Parses a monetary string strictly into a Decimal.
    Handles commas, Indian numbering, negatives, parentheses, and CR/DR suffixes.
    Returns (amount, direction_hint). Direction hint is 'CR', 'DR', or None.
    Amount is ALWAYS positive (absolute value) if CR/DR hint is provided. 
    If negative sign or parens used, amount is negative, hint is None.
    """
    if not amount_str or not amount_str.strip():
        return None, None
        
    s = amount_str.strip().upper()
    
    # Check CR/DR explicit suffix
    direction = None
    if s.endswith('CR'):
        direction = 'CR'
        s = s[:-2].strip()
    elif s.endswith('DR'):
        direction = 'DR'
        s = s[:-2].strip()
        
    # Remove currency symbols (₹, INR, Rs)
    s = re.sub(r'^[₹\sA-Z]*', '', s).strip()
    
    # Handle parens (negative)
    is_negative = False
    if s.startswith('(') and s.endswith(')'):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith('-'):
        is_negative = True
        s = s[1:].strip()
        
    # Remove commas
    s = s.replace(',', '')
    
    if not s:
        return None, direction
        
    try:
        val = Decimal(s)
        if is_negative:
            val = -val
        return val, direction
    except InvalidOperation:
        return None, direction
