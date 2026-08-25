"""Narration Parser for Indian Bank Statements.
Extracts transaction mode, counterparty name, VPA / account number, and reference numbers.
"""

import re
from typing import Dict, Any, Tuple

# Noise words to clean out from extracted party names
NOISE_WORDS = {
    "P2A", "P2M", "P2P", "TRANSFER", "TRF", "DR", "CR", "INR", "REF", "TXN",
    "BIL", "VPS", "RET", "REV", "IMPS", "NEFT", "RTGS", "UPI", "NACH", "ACH",
    "CMS", "CORP", "BANK", "PAYMENT", "PAID", "FROM", "TO", "BY", "FOR",
    "PVT", "LTD", "LIMITED", "PRIVATE", "LLP", "SERVICES", "INDIA", "A/C", "AC"
}

def clean_party_name(raw_name: str) -> str:
    """Clean and standardize a counterparty name."""
    if not raw_name:
        return "Unknown"
    
    # Strip non-alphanumeric noise at start/end
    cleaned = re.sub(r'^[_\W0-9]+|[_\W]+$', '', raw_name).strip()
    
    # Replace multiple slashes or hyphens with spaces
    cleaned = re.sub(r'[\/_\-]+', ' ', cleaned)
    # Remove excessive spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Capitalize cleanly
    words = cleaned.split()
    if not words:
        return "Unknown"
    
    # If the entire word is just numbers or single chars, keep or return Unknown
    if all(len(w) <= 1 or w.isdigit() for w in words):
        return raw_name.strip()
        
    return " ".join(w.capitalize() if not w.isupper() or len(w) > 4 else w for w in words)


def parse_narration(narration: str) -> Dict[str, Any]:
    """
    Parse narration text to extract mode, counterparty name, counterparty handle/account, and reference.
    Returns:
        {
            "mode": str,
            "counterparty_name": str,
            "counterparty_vpa": str,
            "reference_no": str,
            "cleaned_narration": str
        }
    """
    if not narration or not isinstance(narration, str):
        return {
            "mode": "OTHERS",
            "counterparty_name": "Unknown",
            "counterparty_vpa": "",
            "reference_no": "",
            "cleaned_narration": ""
        }
    
    text = narration.strip()
    upper = text.upper()
    
    mode = "OTHERS"
    counterparty_name = ""
    counterparty_vpa = ""
    ref_no = ""
    
    # 1. UPI Parsing
    # Examples:
    # "UPI/412345678901/Mr Rahul Sharma/rahul@okaxis/Payment for supplies"
    # "UPI-412345678901-RAHUL SHARMA-rahul@oksbi-Payment"
    # "UPI/DR/412345678901/AMAZON/amazon@apl/Payment"
    # "UPI/CR/412345678901/JOHN DOE/johndoe@icici/AXIS/..."
    # "UPI/PAYTM/9876543210@paytm/Paytm User"
    if "UPI" in upper:
        mode = "UPI"
        # Match standard UPI format with slashes: UPI/[DR|CR]/[RRN]/[NAME]/[VPA]/... or UPI/[RRN]/[NAME]/[VPA]/...
        parts = [p.strip() for p in text.split('/') if p.strip()]
        
        # Check for VPA handles (e.g., something@bank)
        vpa_match = re.search(r'([a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+)', text)
        if vpa_match:
            counterparty_vpa = vpa_match.group(1)
            
        # Extract RRN (12 digits typically)
        rrn_match = re.search(r'\b(\d{12})\b', text)
        if rrn_match:
            ref_no = rrn_match.group(1)
            
        if len(parts) >= 3:
            # Determine which part has the name
            potential_names = []
            for p in parts[1:]:
                # Ignore pure digits, short codes like DR/CR/NA/YESB/HDFC, or VPAs
                if p.upper() in ("DR", "CR", "UPI", "NA", "OK") or p.isdigit() or "@" in p:
                    continue
                potential_names.append(p)
            if potential_names:
                counterparty_name = potential_names[0]
        
        # Fallback regex for UPI-NAME-REF
        if not counterparty_name:
            dash_parts = [p.strip() for p in text.split('-') if p.strip()]
            for p in dash_parts:
                if len(p) > 2 and not p.isdigit() and p.upper() not in ("UPI", "DR", "CR") and "@" not in p:
                    counterparty_name = p
                    break

    # 2. NEFT Parsing
    # Examples:
    # "NEFT-HDFC0001234-N123456789-RAMESH ENTERPRISES-PAYMENT"
    # "NEFT CR-PUNB0123456-SHREE GANESH TRADERS-N089123456"
    # "NEFT/N123456789/MAHESH KUMAR/SBIN0001234"
    elif "NEFT" in upper:
        mode = "NEFT"
        utr_match = re.search(r'\b(N[A-Za-z0-9]{11,18}|\d{12,18})\b', text)
        if utr_match:
            ref_no = utr_match.group(1)
            
        ifsc_match = re.search(r'\b([A-Z]{4}0[A-Z0-9]{6})\b', text)
        if ifsc_match:
            counterparty_vpa = ifsc_match.group(1) # Store IFSC as counterparty account/bank handle
            
        # Extract name from delimiter split
        delim = '-' if '-' in text else '/'
        parts = [p.strip() for p in text.split(delim) if p.strip()]
        for p in parts:
            p_upper = p.upper()
            if "NEFT" in p_upper or (ifsc_match and p == ifsc_match.group(1)) or (utr_match and p == utr_match.group(1)):
                continue
            if len(p) > 2 and not p.isdigit():
                counterparty_name = p
                break

    # 3. RTGS Parsing
    # Examples:
    # "RTGS-ICIC0000001-R123456789-ABC METALS LTD"
    # "RTGS/SBIN0001234/XYZ CORP/UTR12345"
    elif "RTGS" in upper:
        mode = "RTGS"
        utr_match = re.search(r'\b(R[A-Za-z0-9]{11,20}|\d{12,20})\b', text)
        if utr_match:
            ref_no = utr_match.group(1)
            
        ifsc_match = re.search(r'\b([A-Z]{4}0[A-Z0-9]{6})\b', text)
        if ifsc_match:
            counterparty_vpa = ifsc_match.group(1)
            
        delim = '-' if '-' in text else '/'
        parts = [p.strip() for p in text.split(delim) if p.strip()]
        for p in parts:
            p_upper = p.upper()
            if "RTGS" in p_upper or (ifsc_match and p == ifsc_match.group(1)) or (utr_match and p == utr_match.group(1)):
                continue
            if len(p) > 2 and not p.isdigit():
                counterparty_name = p
                break

    # 4. IMPS Parsing
    # Examples:
    # "IMPS/P2A/412345678901/RAMA KRISHNA/HDFC0000123"
    # "IMPS-412345678901-DEEPAK VERMA-SBI"
    # "MMT/IMPS/412345678901/ANIL/..."
    elif "IMPS" in upper or "MMT" in upper:
        mode = "IMPS"
        rrn_match = re.search(r'\b(\d{12})\b', text)
        if rrn_match:
            ref_no = rrn_match.group(1)
            
        parts = [p.strip() for p in re.split(r'[\/\-]', text) if p.strip()]
        for p in parts:
            p_upper = p.upper()
            if p_upper in ("IMPS", "MMT", "P2A", "P2P", "P2M", "DR", "CR", "RET", "REV") or p.isdigit() or len(p) < 3:
                continue
            # Ignore pure IFSC codes
            if re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', p_upper):
                counterparty_vpa = p
                continue
            counterparty_name = p
            break

    # 5. Cheque / Clearing Parsing
    # Examples:
    # "CHQ PAID-000123"
    # "CHEQUE DEPOSIT - 000456 - SELF"
    # "CLG/000789/SBI"
    # "BY CHEQUE-000112"
    elif any(k in upper for k in ["CHQ", "CHEQUE", "CLG", "CLEARING", "CTS"]):
        mode = "CHQ"
        chq_match = re.search(r'\b(\d{6})\b', text)
        if chq_match:
            ref_no = chq_match.group(1)
        
        # Name might be in narration
        parts = [p.strip() for p in re.split(r'[\/\-\:]', text) if p.strip()]
        for p in parts:
            p_upper = p.upper()
            if any(k in p_upper for k in ["CHQ", "CHEQUE", "CLG", "PAID", "DEP", "TRF", "CLR"]) or p.isdigit():
                continue
            if len(p) > 2:
                counterparty_name = p
                break

    # 6. ATM / Cash Withdrawal & Deposit Parsing
    # Examples:
    # "ATM CASH WITHDRAWAL - S1NA000123 - CONNAUGHT PLACE"
    # "CASH DEPOSIT AT CDM/BNA BR 0123"
    # "BY CASH - SELF DEPOSIT"
    # "NFS*ATM WDL*123456*NEW DELHI"
    # "MATM CASH WDL"
    elif any(k in upper for k in ["ATM", "CDM", "BNA", "CASH", "NFS*", "MATM"]):
        if any(k in upper for k in ["ATM", "NFS*", "MATM"]) or "WDL" in upper or "WITHDRAWAL" in upper:
            mode = "ATM" if "ATM" in upper or "NFS*" in upper or "MATM" in upper else "CASH"
        elif "DEP" in upper or "DEPOSIT" in upper or "BY CASH" in upper:
            mode = "CASH"
        else:
            mode = "CASH"
            
        counterparty_name = "Self / Cash Transaction"

    # 7. POS / Debit Card / Swipes
    # Examples:
    # "POS 412345678901 RELIANCE RETAIL MUMBAI"
    # "ECOM/AMAZON INDIA/412345678901"
    # "SWIPE AT STARBUCKS"
    elif any(k in upper for k in ["POS ", "POS/", "POS-", "ECOM", "DEBIT CARD", "VISA", "MASTERCARD", "RUPAY", "SWIPE"]):
        mode = "POS"
        # Merchant name extraction
        parts = [p.strip() for p in re.split(r'[\/\-\*]', text) if p.strip()]
        for p in parts:
            p_upper = p.upper()
            if any(k in p_upper for k in ["POS", "ECOM", "TXN", "PUR", "DEBIT", "CARD"]) or p.isdigit():
                continue
            if len(p) > 2:
                counterparty_name = p
                break
        if not counterparty_name:
            # Try removing 'POS ' and taking first 3 words
            m = re.sub(r'^(POS\s*|ECOM\s*|DEBIT CARD\s*)', '', text, flags=re.IGNORECASE).strip()
            counterparty_name = " ".join(m.split()[:4])

    # 8. ACH / NACH / ECS / Mandate / Auto-Debit
    # Examples:
    # "ACH/HDFC BANK LTD/LOAN123456"
    # "NACH/BAJAJ FINANCE/EMI"
    # "ECS/TATA CAPITAL/000123"
    elif any(k in upper for k in ["ACH", "NACH", "ECS", "MANDATE", "AUTO DEBIT"]):
        mode = "ACH"
        parts = [p.strip() for p in re.split(r'[\/\-]', text) if p.strip()]
        for p in parts:
            p_upper = p.upper()
            if p_upper in ("ACH", "NACH", "ECS", "MANDATE", "DR", "CR") or p.isdigit():
                continue
            if len(p) > 2:
                counterparty_name = p
                break

    # 9. Interest & Bank System Entries
    # Examples:
    # "INT.PD 01-01-2024 TO 31-03-2024"
    # "CAPITALIZED INT"
    # "CONSOLIDATED CHG + GST"
    # "SMS ALERT CHARGES"
    elif any(k in upper for k in ["INT.PD", "INTEREST PAID", "INTEREST CREDIT", "SB INT", "MOD BAL INT", "SWEEP INT"]):
        mode = "INT"
        counterparty_name = "Bank Interest Credit"
    elif any(k in upper for k in ["SMS CHG", "CONSOLIDATED CHG", "MIN BAL", "AMC CHG", "FOLIO CHG", "SERVICE CHG"]):
        mode = "BANK_CHG"
        counterparty_name = "Bank Charges"

    # 10. General Internal Transfers / By Transfer / To Transfer
    # Examples:
    # "TO TRANSFER-INB/123456789/MR AMIT"
    # "BY TRANSFER-NEFT*..."
    # "TRF FROM 100234567890"
    # "TRF TO 200345678901"
    elif any(k in upper for k in ["TRANSFER", "TRF", "TO TRANSFER", "BY TRANSFER", "INB", "MB"]):
        mode = "TRANSFER"
        # Extract account number if present
        acc_match = re.search(r'\b(\d{9,18})\b', text)
        if acc_match:
            counterparty_vpa = "A/C: " + acc_match.group(1)
            
        parts = [p.strip() for p in re.split(r'[\/\-\:]', text) if p.strip()]
        for p in parts:
            p_upper = p.upper()
            if any(k in p_upper for k in ["TRANSFER", "TRF", "TO", "BY", "INB", "MB", "DR", "CR"]) or p.isdigit():
                continue
            if len(p) > 2:
                counterparty_name = p
                break

    # Final cleanup of counterparty name
    counterparty_name = clean_party_name(counterparty_name)
    if not counterparty_name or counterparty_name == "Unknown":
        # Check if first 3-4 words of narration give any readable entity
        words = text.split()
        if words:
            candidate = " ".join(words[:4])
            # If not pure gibberish, use as fallback
            if len(candidate) > 2:
                counterparty_name = clean_party_name(candidate)

    return {
        "mode": mode,
        "counterparty_name": counterparty_name if counterparty_name else "Unknown",
        "counterparty_vpa": counterparty_vpa,
        "reference_no": ref_no,
        "cleaned_narration": text
    }
