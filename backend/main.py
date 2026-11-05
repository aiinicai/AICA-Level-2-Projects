"""
DirhamTrack AI - FastAPI Backend Server
Serves categorization endpoints, notification parsers, and financial ledger calculations.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import re
import datetime
from categorizer import categorize_merchant, clean_merchant_name, check_red_flag
import database

app = FastAPI(
    title="DirhamTrack AI API",
    description="Python FastAPI backend for UAE Bank notification parsing and merchant auto-categorization",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    database.init_db()

class NotificationRequest(BaseModel):
    title: str
    body: str
    timestamp: Optional[str] = None

class CategorizeRequest(BaseModel):
    merchant: str
    user_rules: Optional[Dict[str, str]] = None

class CorrectionRequest(BaseModel):
    keyword: str
    category: str

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "DirhamTrack AI UAE Banking Engine",
        "version": "1.0.0",
        "currency": "AED"
    }

@app.post("/api/v1/categorize")
def api_categorize(req: CategorizeRequest):
    cleaned = clean_merchant_name(req.merchant)
    category, confidence = categorize_merchant(cleaned, req.user_rules)
    return {
        "raw_merchant": req.merchant,
        "cleaned_merchant": cleaned,
        "category": category,
        "confidence": confidence
    }

@app.post("/api/v1/parse-notification")
def api_parse_notification(req: NotificationRequest):
    full_text = f"{req.title} {req.body}".strip()
    
    # 1. Detect Bank
    bank_name = "UAE Bank"
    if re.search(r'emirates\s*nbd|enbd', full_text, re.I): bank_name = "Emirates NBD"
    elif re.search(r'adcb', full_text, re.I): bank_name = "ADCB"
    elif re.search(r'fab|first\s*abu\s*dhabi', full_text, re.I): bank_name = "FAB"
    elif re.search(r'mashreq', full_text, re.I): bank_name = "Mashreq"
    elif re.search(r'dib|dubai\s*islamic', full_text, re.I): bank_name = "Dubai Islamic Bank"
    elif re.search(r'cbd', full_text, re.I): bank_name = "CBD"

    # 2. Income vs Expense
    tx_type = "expense"
    if re.search(r'salary|credited|refund|deposit|received', full_text, re.I) and not re.search(r'debited|spent|purchase', full_text, re.I):
        tx_type = "income"

    # 3. Extract Card / Account Mask
    card_mask = ""
    card_match = re.search(r'(?:ending|card|account|acct|no\.?)\s*(?:in|ending\s*in)?\s*(?:x+|\*+)?([0-9]{4})', full_text, re.I)
    if card_match:
        card_mask = f"•••• {card_match.group(1)}"

    # 4. Extract Amount & Currency
    currency = "AED"
    original_currency = None
    amount = 0.0
    original_amount = None

    foreign_match = re.search(r'\b(USD|EUR|GBP|INR|SAR|OMR|QAR|KWD|CAD|AUD)\s*([0-9,]+\.[0-9]{2})', full_text, re.I)
    aed_match = re.search(r'\b(?:AED|DHS|DIRHAM)\s*([0-9,]+(?:\.[0-9]{1,2})?)', full_text, re.I)

    if foreign_match:
        original_currency = foreign_match.group(1).upper()
        original_amount = float(foreign_match.group(2).replace(',', ''))
        # Estimated AED rate
        rates = {"USD": 3.6725, "EUR": 3.98, "GBP": 4.65, "INR": 0.044, "SAR": 0.98}
        rate = rates.get(original_currency, 3.6725)
        amount = round(original_amount * rate, 2)
    elif aed_match:
        amount = float(aed_match.group(1).replace(',', ''))
    else:
        num = re.search(r'([0-9]+(?:\.[0-9]{2}))', full_text)
        if num:
            amount = float(num.group(1))

    # 5. Extract Merchant
    merchant = "Unknown Merchant"
    m_match = re.search(r'\b(?:at|to|in)\s+([A-Z0-9\s&.\-/\*]+?)(?:\s+(?:on|dated|ref|avail|avbl|limit|balance|with|from)|\.|\,|$)', full_text, re.I)
    if m_match:
        merchant = m_match.group(1).strip()
    elif tx_type == "income":
        merchant = "Salary / Bank Credit"

    cleaned_merchant = clean_merchant_name(merchant)
    category, _ = categorize_merchant(cleaned_merchant)
    is_red_flag, red_flag_reason = check_red_flag(amount, original_currency or currency, cleaned_merchant)

    return {
        "success": amount > 0,
        "bank": bank_name,
        "amount_aed": amount,
        "original_amount": original_amount,
        "original_currency": original_currency,
        "currency": currency,
        "merchant": cleaned_merchant,
        "category": category,
        "card_mask": card_mask,
        "type": tx_type,
        "is_red_flag": is_red_flag,
        "red_flag_reason": red_flag_reason,
        "date": datetime.date.today().isoformat()
    }

@app.post("/api/v1/corrections")
def api_add_correction(req: CorrectionRequest):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO merchant_rules (keyword, category, updated_at)
        VALUES (?, ?, ?)
    """, (req.keyword.lower().strip(), req.category, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return {"status": "saved", "keyword": req.keyword, "category": req.category}
