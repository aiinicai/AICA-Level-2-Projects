import re
import io
import logging
from datetime import datetime, date
import pdfplumber

logger = logging.getLogger("PDFParser")

def clean_date_str(raw_str: str) -> str:
    """Normalizes raw date strings extracted from PDF text."""
    clean = re.sub(r"[^\w\s\-\/\.]", "", str(raw_str)).strip()
    return clean

def parse_fd_pdf(pdf_bytes: bytes) -> dict:
    """
    Parses Bank FD advice/receipt PDF text to extract:
    Bank Name, FD Account Number, Principal Amount, Interest Rate,
    Date of Issue, Date of Maturity, Compounding Frequency.
    """
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        logger.warning(f"pdfplumber exception/non-binary PDF: {e}")

    # Fallback to text decoding if pdfplumber extracted empty text
    if not text.strip():
        try:
            text = pdf_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    # 1. Bank Name Extraction
    bank_name = "State Bank of India"  # Default fallback bank
    bank_match = re.search(r"([A-Za-z\s]+(?:Bank|Co-operative|Housing|Finance|Capital|Mutual))\b", text, re.IGNORECASE)
    if bank_match:
        cand = bank_match.group(1).strip()
        if len(cand) > 3 and not cand.lower().startswith("the"):
            bank_name = cand

    # 2. FD Account Number Extraction
    fd_account = "FD-AUTOPARSED"
    acc_match = re.search(r"(?:FD|Fixed\s*Deposit|Account|Deposit|Receipt|Advice)\s*(?:No|Num|Number|Ref|Id)?[\.\:]?\s*([A-Za-z0-9\-\/]{5,25})", text, re.IGNORECASE)
    if acc_match:
        fd_account = acc_match.group(1).strip()

    # 3. Principal Amount Extraction (Robust Multi-Regex Search)
    principal = 0.0
    
    # Priority Patterns for Principal / Deposit Amount
    principal_patterns = [
        r"(?:Principal\s*(?:Amount)?|Deposit\s*Amount|FD\s*Amount|Face\s*Value|Sum\s*Deposited|Value\s*of\s*Deposit|Amount\s*Deposited)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
        r"(?:Amount\s*\(?Rs\.?\)?)\s*[:\-]?\s*([\d,]+(?:\.\d{2})?)",
        r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)\s*(?:deposited|only|principal|sum)",
    ]

    for pat in principal_patterns:
        amt_match = re.search(pat, text, re.IGNORECASE)
        if amt_match:
            try:
                val_str = amt_match.group(1).replace(",", "")
                val_flt = float(val_str)
                if val_flt > 0:
                    principal = val_flt
                    break
            except ValueError:
                pass

    # Fallback: Find numeric currency values in text if no explicit label match
    if principal <= 0:
        all_numbers = re.findall(r"\b\d{1,3}(?:,\d{2,3})+(?:\.\d{2})?\b|\b\d{4,9}\.\d{2}\b", text)
        clean_nums = []
        for num in all_numbers:
            try:
                flt = float(num.replace(",", ""))
                if 1000 <= flt <= 100000000:
                    clean_nums.append(flt)
            except ValueError:
                pass
        if clean_nums:
            principal = min(clean_nums) if len(clean_nums) > 1 else clean_nums[0]

    # 4. Interest Rate Extraction
    rate = 7.0
    rate_match = re.search(r"(?:Rate\s*of\s*Interest|Interest\s*Rate|ROI|Rate|@)\s*[:\-]?\s*([\d\.]+)\s*%", text, re.IGNORECASE)
    if rate_match:
        try:
            rate = float(rate_match.group(1))
        except ValueError:
            pass

    # 5. Date Extraction
    issue_date = "2024-04-01"
    maturity_date = "2025-04-01"

    # Search for all date candidates in text
    date_matches = re.findall(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}[\/\-\.][A-Za-z]{3}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b", text)
    
    valid_dates = []
    for raw_d in date_matches:
        d_clean = clean_date_str(raw_d)
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"]:
            try:
                dt = datetime.strptime(d_clean, fmt).date()
                if 2000 <= dt.year <= 2045:
                    valid_dates.append(dt)
                    break
            except ValueError:
                pass

    if len(valid_dates) >= 2:
        valid_dates.sort()
        issue_date = valid_dates[0].strftime("%Y-%m-%d")
        maturity_date = valid_dates[-1].strftime("%Y-%m-%d")
    elif len(valid_dates) == 1:
        issue_date = valid_dates[0].strftime("%Y-%m-%d")

    # 6. Compounding Frequency
    freq = "Quarterly"
    if re.search(r"Monthly", text, re.IGNORECASE):
        freq = "Monthly"
    elif re.search(r"Half-Yearly|Half\s*Yearly", text, re.IGNORECASE):
        freq = "Half-Yearly"
    elif re.search(r"Annual|Yearly", text, re.IGNORECASE):
        freq = "Annual"
    elif re.search(r"Simple", text, re.IGNORECASE):
        freq = "Simple"

    return {
        "bank_name": bank_name,
        "fd_account_number": fd_account,
        "principal_amount": principal,
        "interest_rate": rate,
        "date_of_issue": issue_date,
        "date_of_maturity": maturity_date,
        "compounding_frequency": freq,
        "opening_accrued_interest": 0.0,
        "tds_deducted": 0.0,
        "status": "Active"
    }
