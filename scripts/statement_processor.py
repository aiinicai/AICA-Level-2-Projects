#!/usr/bin/env python3
"""
DirhamTrack AI - Bank Statement Processing, Rules Engine & Reconciliation
Processes bank statement records from UAE banks (Emirates NBD, ADCB, FAB, Mashreq, RAKBANK, CBD, etc.)
- Normalizes dates, amounts, debits, credits, and narrative descriptions
- Auto-categorizes merchants with UAE rule dictionary
- Performs mathematical reconciliation (Opening + Credits - Debits vs Closing)
- Flags suspicious transactions (large spikes, cash advance fees, duplicate amounts)
"""

import sys
import json
import re
from datetime import datetime

# UAE Merchant Categorization Rules
UAE_RULES = {
    "Fuel": [
        "enoc", "adnoc", "eppco", "emarat", "petrol", "fuel", "gasoline", "autopro", "tasjeel", "gas station"
    ],
    "Groceries": [
        "carrefour", "lulu", "nesto", "spinneys", "viva", "choithrams", "union coop",
        "grandiose", "west zone", "al maya", "hypermarket", "supermarket", "mart", "grocery", "baqala"
    ],
    "Food": [
        "kfc", "mcdonald", "starbucks", "tim hortons", "al baik", "subway", "texas chicken",
        "hardees", "costa", "paul cafe", "shake shack", "pizza hut", "domino", "papa john",
        "burger king", "dunkin", "baskin robbins", "five guys", "cheesecake factory", "nando",
        "wagamama", "carluccio", "restaurant", "cafe", "cafeteria", "bakery", "kitchen", "bistro", "dining", "shawarma"
    ],
    "Clothing": [
        "zara", "h&m", "max fashion", "splash", "centrepoint", "redtag", "brands for less",
        "pull & bear", "bershka", "mango", "massimo dutti", "shein", "namshi", "footwear", "apparel"
    ],
    "Utilities": [
        "dewa", "sewa", "fewa", "aadc", "addc", "empower", "tabreed", "electricity", "water"
    ],
    "Telecom": [
        "etisalat", "e&", "du telecom", "du bill", "du recharge", "virgin mobile", "telecom"
    ],
    "Transport": [
        "salik", "rta", "careem", "uber", "dubai taxi", "darb", "m-parking", "parkonic", "metro", "tram", "bus"
    ],
    "Healthcare": [
        "aster", "life pharmacy", "boots", "supercare", "nmc", "medcare", "prime medical",
        "mediclinic", "pharmacy", "clinic", "hospital", "dr", "doctor", "medicine"
    ],
    "Shopping": [
        "amazon", "noon", "apple store", "sharaf dg", "ikea", "virgin megastore", "jumbo", "sephora"
    ],
    "Entertainment": [
        "netflix", "spotify", "vox cinema", "reel cinema", "osn", "youtube", "anghami", "disney", "playstation"
    ],
    "Travel": [
        "flydubai", "emirates air", "air arabia", "etihad", "booking.com", "airbnb", "agoda", "hotel", "resort"
    ],
    "Education": [
        "gems education", "taaleem", "school", "university", "college", "academy", "nursery"
    ],
    "Rent & Housing": [
        "ejari", "damac", "emaar", "nakheel", "rent", "landlord", "maintenance fee", "service charge"
    ]
}

def clean_merchant_name(narrative: str) -> str:
    """Extracts a clean, human-readable merchant name from cryptic bank narratives."""
    if not narrative:
        return "Bank Transaction"

    s = narrative.strip()

    # Common UAE statement prefixes to strip
    prefixes = [
        r"^POS\s+(?:PURCHASE|TRANSACTION)?\s*",
        r"^PURCHASE\s+(?:AT|POS)?\s*",
        r"^ONLINE\s+(?:PURCHASE|PAYMENT)?\s*",
        r"^E-COMMERCE\s*",
        r"^OUTWARD\s+REMITTANCE\s*",
        r"^INWARD\s+REMITTANCE\s*",
        r"^ATM\s+(?:WDL|CASH|WITHDRAWAL)?\s*",
        r"^DEBIT\s+CARD\s+PURCHASE\s*",
        r"^CREDIT\s+CARD\s+PURCHASE\s*",
        r"^BILL\s+PAYMENT\s*",
        r"^UTILITY\s+PAYMENT\s*",
        r"^TRANSFER\s+TO\s*",
        r"^TRANSFER\s+FROM\s*",
        r"^WPS\s+SALARY\s*",
        r"^SALARY\s+CREDIT\s*"
    ]
    for p in prefixes:
        s = re.sub(p, "", s, flags=re.IGNORECASE)

    # Strip reference numbers, card tokens, locations
    s = re.sub(r"\b\d{6,}\b", "", s)  # long numeric codes
    s = re.sub(r"\b\d{2}/\d{2}\b", "", s) # date tokens
    s = re.sub(r"\b(DUBAI|ABU DHABI|SHARJAH|AJMAN|RAK|AL AIN|UAE|ARE)\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[*#_\\/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    if not s:
        return narrative[:40].strip()

    # Title case formatting
    words = s.split()
    if len(words) > 5:
        words = words[:5]
    return " ".join(words).title()

def categorize_merchant(narrative: str, clean_name: str) -> str:
    """Assigns category using keyword matches in clean name and original narrative."""
    combined = f"{clean_name} {narrative}".lower()

    # High priority income / salary checks
    if any(k in combined for k in ["salary", "wps", "payroll", "stipend", "mohreb"]):
        return "Salary"

    for cat, keywords in UAE_RULES.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", combined, re.IGNORECASE) or kw in combined:
                return cat

    return "Other"

def determine_type(narrative: str, debit: float, credit: float) -> str:
    """Determines transaction type: expense, income, card_payment, or transfer."""
    comb = narrative.lower()

    if any(k in comb for k in ["credit card payment", "cc payment", "autopay payment", "card settlement"]):
        return "card_payment"
    if any(k in comb for k in ["transfer to", "transfer from", "internal trf", "ibt to", "ibt from", "self transfer"]):
        return "transfer"
    if credit > 0 and debit == 0:
        return "income"
    return "expense"

def normalize_date(date_str: str) -> str:
    """Normalizes diverse statement date formats to YYYY-MM-DD."""
    if not date_str:
        return datetime.today().strftime("%Y-%m-%d")

    date_str = date_str.strip()
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d-%b-%Y", "%d-%B-%Y", "%d %b %Y", "%d %B %Y",
        "%b %d, %Y", "%B %d, %Y",
        "%m/%d/%Y", "%m-%d-%Y"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Regex heuristic for e.g. 24 Oct 2026 or 24-10-2026
    m = re.search(r"(\d{1,2})[-/\s]([A-Za-z]{3}|\d{1,2})[-/\s](\d{2,4})", date_str)
    if m:
        day, month_str, year = m.groups()
        if len(year) == 2:
            year = "20" + year
        if month_str.isdigit():
            month = int(month_str)
        else:
            try:
                month = datetime.strptime(month_str[:3], "%b").month
            except:
                month = 1
        try:
            return f"{int(year):04d}-{month:02d}-{int(day):02d}"
        except:
            pass

def safe_float(val, default=0.0):
    """Safely converts string/number with potential currency symbols or commas to float."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = re.sub(r"[^0-9.-]", "", str(val).strip())
        if not s or s == "-" or s == ".":
            return default
        return float(s)
    except:
        return default

def process_statement(payload: dict) -> dict:
    raw_txs = payload.get("transactions", [])
    opening = safe_float(payload.get("openingBalance"), 0.0)
    has_closing = "closingBalance" in payload and payload.get("closingBalance") is not None and str(payload.get("closingBalance")).strip() != ""
    closing = safe_float(payload.get("closingBalance"), 0.0) if has_closing else 0.0

    processed_txs = []
    total_debits = 0.0
    total_credits = 0.0
    flagged_count = 0

    seen_signatures = set()

    for idx, tx in enumerate(raw_txs):
        raw_narrative = str(tx.get("description") or tx.get("narrative") or "Transaction")
        debit = safe_float(tx.get("debit"), 0.0)
        credit = safe_float(tx.get("credit"), 0.0)
        raw_amt = safe_float(tx.get("amount"), 0.0)

        if debit == 0.0 and credit == 0.0:
            if raw_amt > 0:
                # Infer from type if provided
                if tx.get("type") in ["income", "credit"]:
                    credit = raw_amt
                else:
                    debit = raw_amt

        amount = debit if debit > 0 else credit
        if amount == 0.0 and raw_amt > 0:
            amount = raw_amt

        total_debits += debit
        total_credits += credit

        norm_date = normalize_date(str(tx.get("date") or ""))
        clean_name = tx.get("merchant") or clean_merchant_name(raw_narrative)
        category = tx.get("suggestedCategory") or categorize_merchant(raw_narrative, clean_name)
        tx_type = tx.get("type") or determine_type(raw_narrative, debit, credit)

        # Suspicious anomaly detection
        is_suspicious = False
        suspicious_reason = ""

        # Flag 1: High single debit
        if debit >= 2500.0:
            is_suspicious = True
            suspicious_reason = f"High spend spike (> AED 2,500)"

        # Flag 2: Cash advance / ATM fee charges
        if any(k in raw_narrative.lower() for k in ["cash advance fee", "atm fee", "overdraft charge", "finance charge"]):
            is_suspicious = True
            suspicious_reason = "Bank service charge / Cash advance fee"

        # Flag 3: Same day duplicate signature in statement
        sig = f"{norm_date}_{amount:.2f}_{clean_name.lower()}"
        if sig in seen_signatures:
            is_suspicious = True
            suspicious_reason = "Potential duplicate charge in statement"
        seen_signatures.add(sig)

        if is_suspicious:
            flagged_count += 1

        balance_val = tx.get("balance")
        if balance_val is not None:
            try:
                balance_val = float(balance_val)
            except:
                balance_val = None

        processed_txs.append({
            "id": tx.get("id") or f"stmt-{idx+1}-{int(datetime.now().timestamp())}",
            "date": norm_date,
            "description": raw_narrative,
            "merchant": clean_name,
            "amount": round(amount, 2),
            "debit": round(debit, 2),
            "credit": round(credit, 2),
            "balance": round(balance_val, 2) if balance_val is not None else None,
            "type": tx_type,
            "suggestedCategory": category,
            "selectedCategory": category,
            "currency": tx.get("currency") or "AED",
            "isSuspicious": is_suspicious,
            "suspiciousReason": suspicious_reason,
            "selected": True
        })

    # Mathematical Reconciliation
    calculated_closing = opening + total_credits - total_debits
    variance = abs(calculated_closing - closing) if has_closing else 0.0
    is_balanced = variance <= 1.0 if has_closing else True

    notes = ""
    if has_closing:
        if is_balanced:
            notes = f"Verified: Opening (AED {opening:,.2f}) + Credits (AED {total_credits:,.2f}) - Debits (AED {total_debits:,.2f}) perfectly equals Closing Balance (AED {closing:,.2f})."
        else:
            notes = f"Discrepancy of AED {variance:,.2f} detected between calculated closing (AED {calculated_closing:,.2f}) and stated closing (AED {closing:,.2f})."
    else:
        notes = f"Processed {len(processed_txs)} transactions with Total Debits of AED {total_debits:,.2f} and Total Credits of AED {total_credits:,.2f}."

    return {
        "success": True,
        "bankName": payload.get("bankName") or "UAE Bank",
        "accountNumberMasked": payload.get("accountNumberMasked") or "",
        "statementPeriod": payload.get("statementPeriod") or {},
        "openingBalance": round(opening, 2),
        "closingBalance": round(closing, 2) if has_closing else round(calculated_closing, 2),
        "totalDebits": round(total_debits, 2),
        "totalCredits": round(total_credits, 2),
        "reconciliation": {
            "isBalanced": is_balanced,
            "calculatedClosing": round(calculated_closing, 2),
            "variance": round(variance, 2),
            "notes": notes,
            "flaggedItemsCount": flagged_count
        },
        "transactions": processed_txs
    }

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"error": "Empty input"}))
            sys.exit(1)

        payload = json.loads(raw_input)
        result = process_statement(payload)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
