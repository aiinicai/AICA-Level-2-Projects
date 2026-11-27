"""
DirhamTrack AI - Python Auto Categorization & Red Flag Engine
Handles UAE merchant pattern recognition, learning memory, and anomaly detection.
"""

import re
from typing import Dict, List, Optional, Tuple

UAE_BASE_RULES: Dict[str, List[str]] = {
    "Petrol": ["enoc", "adnoc", "eppco", "emarat", "shell", "petrol", "fuel", "autopro", "tasjeel"],
    "Food": [
        "kfc", "mcdonald", "starbucks", "tim hortons", "al baik", "subway", "texas chicken",
        "hardees", "costa coffee", "paul cafe", "shake shack", "pizza hut", "domino",
        "burger king", "dunkin", "five guys", "cheesecake factory", "nando", "wagamama",
        "restaurant", "cafe", "cafeteria", "bakery", "kitchen", "bistro", "dining"
    ],
    "Groceries": [
        "carrefour", "lulu", "nesto", "spinneys", "viva", "choithrams", "union coop",
        "grandiose", "west zone", "al maya", "hypermarket", "supermarket", "mart", "grocery"
    ],
    "Utilities": ["dewa", "sewa", "fewa", "aadc", "addc", "empower", "tabreed", "electricity", "water"],
    "Telecom": ["etisalat", "e&", " du ", "du telecom", "emirates integrated", "virgin mobile"],
    "Shopping": [
        "amazon", "noon", "namshi", "zara", "h&m", "apple store", "sharaf dg", "centrepoint",
        "max fashion", "splash", "sephora", "ikea", "shein", "asos", "bath & body", "adidas", "nike"
    ],
    "Transport": ["rta", "salik", "careem", "uber", "dubai taxi", "darb", "parking", "metro", "tram", "bus"],
    "Healthcare": ["aster", "life pharmacy", "boots", "supercare", "nmc", "medcare", "pharmacy", "clinic", "hospital"],
    "Entertainment": ["netflix", "spotify", "vox cinemas", "reel cinemas", "osn", "youtube", "cinema"],
    "Travel": ["flydubai", "emirates air", "air arabia", "etihad", "booking.com", "airbnb", "hotel", "resort"],
    "Education": ["gems education", "taaleem", "school", "university", "academy", "udemy", "coursera"],
    "Other": []
}

def clean_merchant_name(raw: str) -> str:
    """Strip POS prefixes, mall suffixes, and normalize whitespace."""
    if not raw:
        return "Unknown Merchant"
    text = re.sub(r'^(POS PURCHASE|PURCHASE AT|PAYMENT TO|TRX AT|DEBIT:?|CARD TRX AT)\s+', '', raw, flags=re.IGNORECASE)
    text = re.sub(r'\s+(MALL OF THE EMIRATES|DUBAI MALL|MIRDIF|DEIRA|ABU DHABI|SHARJAH|BRANCH \d+|STORE \d+|DXB|UAE|AE|LLC|FZCO)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[*#\-_]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def categorize_merchant(merchant_name: str, user_rules: Optional[Dict[str, str]] = None) -> Tuple[str, float]:
    """
    Categorizes merchant with confidence score.
    user_rules: dictionary mapping lowercase keyword -> category (learned memory).
    """
    normalized = merchant_name.lower().strip()

    # 1. Check user custom rules first
    if user_rules:
        for keyword, cat in user_rules.items():
            if keyword.lower() in normalized:
                return cat, 1.0

    # 2. Check base UAE rules
    for category, keywords in UAE_BASE_RULES.items():
        for kw in keywords:
            if kw in normalized:
                return category, 0.95

    return "Other", 0.30

def check_red_flag(amount_aed: float, currency: str, merchant: str, high_threshold: float = 1500.0) -> Tuple[bool, Optional[str]]:
    curr = currency.upper().strip()
    if curr not in ["AED", "DIRHAM", "DHS"]:
        return True, f"Foreign currency transaction ({curr}) outside UAE standard."

    lower_m = merchant.lower()
    foreign_flags = ["steam", "apple.com/bill", "alibaba", "aliexpress", "paypal *uk", "stripe *ca"]
    for f in foreign_flags:
        if f in lower_m:
            return True, "International merchant outside UAE banking network."

    if amount_aed > high_threshold:
        return True, f"Unusually high transaction (> AED {high_threshold:,.2f})."

    return False, None
