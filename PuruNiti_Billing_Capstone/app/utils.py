def num_to_words_indian(num):
    """Converts a number to Indian Currency words (Rupees X Only)."""
    try:
        num = float(num)
    except (ValueError, TypeError):
        return ""
    
    # Round to 2 decimal places to handle paise
    num = round(num, 2)
    integer_part = int(num)
    paise_part = int(round((num - integer_part) * 100))
    
    if integer_part == 0 and paise_part == 0:
        return "Rupees Zero Only"
    
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", 
             "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def convert_below_thousand(n):
        if n == 0:
            return ""
        elif n < 20:
            return units[n]
        elif n < 100:
            t = tens[n // 10]
            u = units[n % 10]
            return f"{t} {u}".strip()
        else:
            h = units[n // 100]
            rest = convert_below_thousand(n % 100)
            if rest:
                return f"{h} Hundred and {rest}"
            return f"{h} Hundred"

    def convert_to_words(val):
        if val == 0:
            return ""
        
        parts = []
        # Crores (1,00,00,000)
        if val >= 10000000:
            crores = val // 10000000
            val %= 10000000
            crores_words = convert_to_words(crores)
            parts.append((crores, f"{crores_words} Crore"))
        
        # Lakhs (1,00,000)
        if val >= 100000:
            lakhs = val // 100000
            val %= 100000
            parts.append((lakhs, f"{convert_below_thousand(lakhs)} Lakh"))
            
        # Thousands (1,000)
        if val >= 1000:
            thousands = val // 1000
            val %= 1000
            parts.append((thousands, f"{convert_below_thousand(thousands)} Thousand"))
            
        # Remaining hundreds, tens, units
        if val > 0:
            parts.append((val, convert_below_thousand(val)))
            
        # Build the final words string with 'and' connector
        result_parts = []
        for i, (amount, words) in enumerate(parts):
            if not words:
                continue
                
            is_last = (i == len(parts) - 1)
            is_less_than_100 = (amount < 100)
            has_prior = (len(result_parts) > 0)
            
            if is_last and is_less_than_100 and has_prior:
                sep = "and "
            else:
                sep = ""
                
            result_parts.append(f"{sep}{words}")
            
        return " ".join(result_parts).strip()

    rupees_str = ""
    if integer_part > 0:
        rupees_str = f"Rupees {convert_to_words(integer_part)}"
        
    paise_str = ""
    if paise_part > 0:
        paise_str = f"{convert_to_words(paise_part)} Paise"
        
    if rupees_str and paise_str:
        return f"{rupees_str} and {paise_str} Only"
    elif rupees_str:
        return f"{rupees_str} Only"
    elif paise_str:
        return f"{paise_str} Only"
    else:
        return "Rupees Zero Only"

import re

def validate_gstin(gstin):
    """Validates Indian GSTIN (15 characters)."""
    if not gstin:
        return True
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gstin.upper().strip()))

def validate_pan(pan):
    """Validates Indian PAN (10 characters)."""
    if not pan:
        return True
    pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    return bool(re.match(pattern, pan.upper().strip()))

def validate_pin(pin):
    """Validates Indian PIN Code (6 digits)."""
    if not pin:
        return True
    pattern = r"^[1-9][0-9]{5}$"
    return bool(re.match(pattern, pin.strip()))
