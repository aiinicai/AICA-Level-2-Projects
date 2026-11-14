import re
import os
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, Any, List, Optional, Tuple
import pdfplumber
import openpyxl

def parse_indian_number(text: Optional[str]) -> Optional[Decimal]:
    """
    Parses Indian number strings with commas, rupees, brackets for negative:
    e.g. '₹ 47,44,316.24' -> Decimal('4744316.24')
    '(1,50,000)' -> Decimal('-150000.00')
    '15.50 Lakhs' -> Decimal('1550000.00')
    '2.5 Crores' -> Decimal('25000000.00')
    """
    if not text:
        return None
    cleaned = text.strip()
    
    # Check for Lakhs / Crores suffix
    lakh_match = re.search(r'([\d\.]+)\s*(?:lakh|lakhs|lac|lacs)', cleaned, re.IGNORECASE)
    if lakh_match:
        try:
            return (Decimal(lakh_match.group(1)) * Decimal("100000")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            pass
            
    cr_match = re.search(r'([\d\.]+)\s*(?:crore|crores|cr)', cleaned, re.IGNORECASE)
    if cr_match:
        try:
            return (Decimal(cr_match.group(1)) * Decimal("10000000")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            pass
            
    # Check for negative brackets like (1,00,000)
    is_negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        is_negative = True
        cleaned = cleaned[1:-1].strip()
    elif cleaned.startswith("-"):
        is_negative = True
        cleaned = cleaned[1:].strip()
        
    # Remove Currency symbols and commas
    cleaned = re.sub(r'[₹RsINR,\s]', '', cleaned)
    try:
        val = Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return -val if is_negative else val
    except InvalidOperation:
        return None

def extract_pan(text: str) -> Optional[str]:
    """Extracts valid Indian PAN pattern: [A-Z]{5}[0-9]{4}[A-Z]{1}"""
    match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b', text)
    return match.group(1) if match else None

def extract_gstin(text: str) -> Optional[str]:
    """Extracts valid Indian GSTIN pattern: 2 digits + 10 char PAN + 1 entity num + Z + 1 check digit"""
    match = re.search(r'\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b', text)
    return match.group(1) if match else None

class DocumentExtractorService:
    @staticmethod
    def extract_document(file_path: str, category_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extracts financial and identity data from PDF or Excel documents.
        Returns a list of extracted metric dictionaries.
        """
        if not os.path.exists(file_path):
            return []
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return DocumentExtractorService._extract_pdf(file_path, category_hint)
        elif ext in [".xlsx", ".xls", ".csv"]:
            return DocumentExtractorService._extract_excel(file_path, category_hint)
        return []

    @staticmethod
    def _extract_pdf(file_path: str, category_hint: Optional[str]) -> List[Dict[str, Any]]:
        extracted = []
        try:
            with pdfplumber.open(file_path) as pdf:
                # Pre-scan for presence of primary financial statement pages (Balance Sheet or P&L)
                has_primary_statement = False
                for p in pdf.pages:
                    ptxt = (p.extract_text() or "").lower()
                    if any(h in ptxt for h in [
                        "balance sheet as at", "statement of profit and loss", 
                        "balance sheet as on", "trading and profit and loss", "profit & loss account"
                    ]):
                        has_primary_statement = True
                        break

                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    
                    # 1. Detect ITR-V Acknowledgement
                    if "INCOME TAX RETURN ACKNOWLEDGEMENT" in text or "e-Filing Acknowledgement Number" in text:
                        extracted.extend(DocumentExtractorService._parse_itr_page(text, page_num))
                        
                    # 2. Detect GSTR-3B
                    elif "Form GSTR-3B" in text or "Details of Outward supplies" in text:
                        extracted.extend(DocumentExtractorService._parse_gstr3b_page(text, page_num))
                        
                    # 3. Detect Bank Statement
                    elif any(bank in text for bank in ["ICICI BANK", "STATE BANK OF INDIA", "HDFC BANK", "UNION BANK", "PUNJAB NATIONAL BANK"]):
                        extracted.extend(DocumentExtractorService._parse_bank_statement_page(text, page_num))
                        
                    # 4. Financial Statements (Balance Sheet & P&L)
                    else:
                        # If the PDF contains primary statement pages, skip the secondary note pages
                        ptxt_lower = text.lower()
                        is_primary_page = any(h in ptxt_lower for h in [
                            "balance sheet as at", "statement of profit and loss", 
                            "balance sheet as on", "trading and profit and loss", "profit & loss account"
                        ])
                        if has_primary_statement and not is_primary_page:
                            continue

                        extracted.extend(DocumentExtractorService._parse_financial_statement_page(page, text, page_num))
                        
        except Exception as e:
            # Handle corrupted or scanned PDFs gracefully
            extracted.append({
                "metric_name": "extraction_error",
                "raw_value": str(e),
                "normalized_value": None,
                "confidence": 0.0,
                "page_or_sheet": "1",
                "financial_period": "Unknown"
            })
            
        return extracted

    @staticmethod
    def _parse_itr_page(text: str, page_num: int) -> List[Dict[str, Any]]:
        metrics = []
        # Assessment Year
        ay_match = re.search(r'Assessment\s*Year\s*[:\n\r\s]*([0-9]{4}-[0-9]{2,4})', text, re.IGNORECASE)
        ay = ay_match.group(1) if ay_match else "Unknown"
        
        # Ack Number
        ack_match = re.search(r'Acknowledgement\s*Number\s*[:\s]*([0-9]{10,20})', text, re.IGNORECASE)
        if ack_match:
            metrics.append({
                "metric_name": "itr_ack_number",
                "raw_value": ack_match.group(1),
                "normalized_value": None,
                "confidence": 0.95,
                "page_or_sheet": str(page_num),
                "financial_period": ay
            })
            
        # PAN
        pan = extract_pan(text)
        if pan:
            metrics.append({
                "metric_name": "pan",
                "raw_value": pan,
                "normalized_value": None,
                "confidence": 0.99,
                "page_or_sheet": str(page_num),
                "financial_period": ay
            })
            
        # Gross Total Income
        gti_match = re.search(r'Gross\s*Total\s*Income\s*[:\s]*([₹0-9,]+(?:\.[0-9]{2})?)', text, re.IGNORECASE)
        if gti_match:
            val = parse_indian_number(gti_match.group(1))
            metrics.append({
                "metric_name": "gross_total_income",
                "raw_value": gti_match.group(1),
                "normalized_value": val,
                "confidence": 0.90,
                "page_or_sheet": str(page_num),
                "financial_period": ay
            })
            
        # Total Tax Payable / Paid
        tax_match = re.search(r'Total\s*Tax\s*(?:Payable|Paid)\s*[:\s]*([₹0-9,]+(?:\.[0-9]{2})?)', text, re.IGNORECASE)
        if tax_match:
            val = parse_indian_number(tax_match.group(1))
            metrics.append({
                "metric_name": "total_tax_paid",
                "raw_value": tax_match.group(1),
                "normalized_value": val,
                "confidence": 0.88,
                "page_or_sheet": str(page_num),
                "financial_period": ay
            })
            
        return metrics

    @staticmethod
    def _parse_gstr3b_page(text: str, page_num: int) -> List[Dict[str, Any]]:
        metrics = []
        gstin = extract_gstin(text)
        year_match = re.search(r'Year\s*[:\s]*([0-9]{4}-[0-9]{2,4})', text, re.IGNORECASE)
        period_match = re.search(r'Period\s*[:\s]*([A-Za-z0-9\-]+)', text, re.IGNORECASE)
        
        fin_period = f"{year_match.group(1) if year_match else 'FY 24-25'} ({period_match.group(1) if period_match else 'Qtr'})"
        
        if gstin:
            metrics.append({
                "metric_name": "gstin",
                "raw_value": gstin,
                "normalized_value": None,
                "confidence": 0.98,
                "page_or_sheet": str(page_num),
                "financial_period": fin_period
            })
            
        # Outward taxable supplies (turnover)
        turnover_match = re.search(r'Outward\s*taxable\s*supplies[^\n\r0-9]*([0-9,]+(?:\.[0-9]{2})?)', text, re.IGNORECASE)
        if turnover_match:
            val = parse_indian_number(turnover_match.group(1))
            metrics.append({
                "metric_name": "gst_taxable_turnover",
                "raw_value": turnover_match.group(1),
                "normalized_value": val,
                "confidence": 0.92,
                "page_or_sheet": str(page_num),
                "financial_period": fin_period
            })
            
        return metrics

    @staticmethod
    def _parse_bank_statement_page(text: str, page_num: int) -> List[Dict[str, Any]]:
        metrics = []
        # Try to find Account Number
        acc_match = re.search(r'Account\s*(?:No|Number)\s*[:\s]*([0-9X\*\-]+)', text, re.IGNORECASE)
        if acc_match:
            metrics.append({
                "metric_name": "bank_account_number",
                "raw_value": acc_match.group(1),
                "normalized_value": None,
                "confidence": 0.90,
                "page_or_sheet": str(page_num),
                "financial_period": "Rolling 12M"
            })
            
        # Detect closing balance on statement
        balance_match = re.search(r'(?:Closing|Available|Clear)\s*Balance\s*[:\s]*([₹0-9,]+(?:\.[0-9]{2})?)', text, re.IGNORECASE)
        if balance_match:
            val = parse_indian_number(balance_match.group(1))
            metrics.append({
                "metric_name": "closing_bank_balance",
                "raw_value": balance_match.group(1),
                "normalized_value": val,
                "confidence": 0.85,
                "page_or_sheet": str(page_num),
                "financial_period": "Rolling 12M"
            })
            
        return metrics

    @staticmethod
    def _parse_financial_statement_page(page: Any, text: str, page_num: int) -> List[Dict[str, Any]]:
        from collections import defaultdict
        metrics = []

        try:
            words = page.extract_words()
        except Exception:
            words = []

        if words:
            lines_dict = defaultdict(list)
            for w in words:
                matched = False
                for line_top in lines_dict:
                    if abs(w['top'] - line_top) < 3.2:
                        lines_dict[line_top].append(w)
                        matched = True
                        break
                if not matched:
                    lines_dict[w['top']].append(w)

            sorted_tops = sorted(lines_dict.keys())
            col_cy_x, col_py_x = None, None
            cy_year, py_year = "2026", "2025"

            # Scan specifically for column header row containing "March" or "31" or "CY"
            for top in sorted_tops:
                lw = sorted(lines_dict[top], key=lambda x: x['x0'])
                lstr = ' '.join(w['text'] for w in lw)
                if 'forming part' in lstr.lower():
                    continue
                if ('march' in lstr.lower() or 'particulars' in lstr.lower()) and ('202' in lstr or '201' in lstr):
                    year_words = [w for w in lw if re.search(r'202\d', w['text'])]
                    if len(year_words) >= 2 and abs(year_words[1]['x0'] - year_words[0]['x0']) > 40:
                        year_words.sort(key=lambda x: x['x0'])
                        col_cy_x = year_words[0]['x0']
                        col_py_x = year_words[1]['x0']
                        cy_year = re.search(r'202\d', year_words[0]['text']).group(0)
                        py_year = re.search(r'202\d', year_words[1]['text']).group(0)
                        break
                    march_words = [w for w in lw if 'march' in w['text'].lower() or '31' in w['text']]
                    if len(march_words) >= 2 and abs(march_words[1]['x0'] - march_words[0]['x0']) > 40:
                        march_words.sort(key=lambda x: x['x0'])
                        col_cy_x = march_words[0]['x0']
                        col_py_x = march_words[1]['x0']
                        break

            is_primary_statement = any(h in text.lower() for h in [
                "balance sheet as at", "statement of profit and loss", 
                "balance sheet as on", "trading and profit and loss", "profit & loss account"
            ])

            if not col_cy_x or not col_py_x:
                if is_primary_statement:
                    col_cy_x = 428.0
                    col_py_x = 522.0
                else:
                    return []

            div_x = (col_cy_x + col_py_x) / 2
            start_num_x = col_cy_x - 35.0

            cy_period = f"FY {int(cy_year)-1}-{cy_year[-2:]} (Provisional/Estimated)"
            py_period = f"FY {int(py_year)-1}-{py_year[-2:]} (Audited)"

            METRIC_MAP = [
                ("revenue_from_operations", ["revenue from operations (gross)", "revenue from operations (net)", "total revenue from operations", "revenue from operations", "gross turnover", "gross sales"]),
                ("other_income", ["total other income", "other income"]),
                ("total_income", ["total income (i+ii)", "total income", "total revenue"]),
                ("cost_of_goods_sold", ["cost of goods sold", "cost of material", "purchases of stock-in-trade", "raw material consumed"]),
                ("employee_benefits_expense", ["total employee benefits expense", "employee benefits expense"]),
                ("finance_costs", ["total finance costs", "finance costs", "interest expense", "finance charges"]),
                ("depreciation", ["depreciation and amortization", "depreciation"]),
                ("other_expenses", ["total other expenses", "other expenses", "administrative expenses"]),
                ("total_expenses", ["total expenses"]),
                ("profit_before_tax", ["profit before exceptional", "profit before tax", "profit before partners", "pbt"]),
                ("tax_expense", ["current tax", "tax expense", "provision for tax"]),
                ("pat", ["profit/(loss) for the year", "profit/(loss) for the period", "profit for the year", "profit after tax"]),
                ("tangible_net_worth", ["owners' capital account", "proprietor capital account", "owner's funds", "share capital", "equity capital"]),
                ("long_term_borrowings", ["long-term borrowings", "long term borrowings"]),
                ("other_long_term_liabilities", ["other long-term liabilities", "other long term liabilities", "other non-current liabilities"]),
                ("short_term_borrowings", ["short-term borrowings", "short term borrowings"]),
                ("trade_payables", ["total trade payables", "trade payables", "sundry creditors"]),
                ("other_current_liabilities", ["other current liabilities"]),
                ("short_term_provisions", ["short-term provisions", "short term provisions"]),
                ("current_liabilities", ["total current liabilities", "current liabilities"]),
                ("fixed_assets", ["property, plant and equipment", "tangible assets", "fixed assets"]),
                ("non_current_investments", ["non-current investments", "non current investments"]),
                ("long_term_loans_advances", ["long term loans and advances", "long-term loans and advances"]),
                ("current_investments", ["current investments", "short-term investments"]),
                ("inventories", ["total inventories", "inventories"]),
                ("trade_receivables", ["total trade receivables", "trade receivables", "sundry debtors"]),
                ("cash_and_bank", ["cash and bank balances", "cash and cash equivalents"]),
                ("short_term_loans_advances", ["short term loans and advances", "short-term loans and advances"]),
                ("other_current_assets", ["other current assets"]),
                ("current_assets", ["total current assets", "current assets"]),
            ]

            def clean_val(s: str) -> Optional[Decimal]:
                if not s or s in ['-', '--', '', 'None']:
                    return None
                is_neg = s.startswith('(') and s.endswith(')')
                cleaned = re.sub(r'[₹RsINR,\s\(\)]', '', s)
                try:
                    val = Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    return -val if is_neg else val
                except Exception:
                    return None

            seen_keys = set()
            total_statement_count = 0
            for top in sorted_tops:
                lw = sorted(lines_dict[top], key=lambda x: x['x0'])
                p_words = [w['text'] for w in lw if w['x0'] < start_num_x]
                cy_words = [w['text'] for w in lw if start_num_x <= w['x0'] < div_x]
                py_words = [w['text'] for w in lw if w['x0'] >= div_x]

                p_text = ' '.join(p_words).strip().lower()
                cy_raw = ''.join(cy_words).replace(' ', '')
                py_raw = ''.join(py_words).replace(' ', '')

                if not p_text or (not cy_raw and not py_raw):
                    continue

                cy_val = clean_val(cy_raw)
                py_val = clean_val(py_raw)

                # Special handling for "Total" row in Balance Sheet
                if p_text == "total" or p_text == "total equity and liabilities":
                    total_statement_count += 1
                    target_metric = "total_liabilities" if total_statement_count == 1 else "total_assets"
                    if cy_val is not None and (target_metric, "CY") not in seen_keys:
                        seen_keys.add((target_metric, "CY"))
                        metrics.append({
                            "metric_name": target_metric,
                            "raw_value": cy_raw,
                            "normalized_value": cy_val,
                            "confidence": 0.99,
                            "page_or_sheet": f"Page {page_num}",
                            "financial_period": cy_period
                        })
                    if py_val is not None and (target_metric, "PY") not in seen_keys:
                        seen_keys.add((target_metric, "PY"))
                        metrics.append({
                            "metric_name": target_metric,
                            "raw_value": py_raw,
                            "normalized_value": py_val,
                            "confidence": 0.99,
                            "page_or_sheet": f"Page {page_num}",
                            "financial_period": py_period
                        })
                    continue

                for metric_name, kw_list in METRIC_MAP:
                    if any(kw in p_text for kw in kw_list):
                        if cy_val is not None and (metric_name, "CY") not in seen_keys:
                            seen_keys.add((metric_name, "CY"))
                            metrics.append({
                                "metric_name": metric_name,
                                "raw_value": cy_raw,
                                "normalized_value": cy_val,
                                "confidence": 0.95,
                                "page_or_sheet": f"Page {page_num}",
                                "financial_period": cy_period
                            })

                        if py_val is not None and (metric_name, "PY") not in seen_keys:
                            seen_keys.add((metric_name, "PY"))
                            metrics.append({
                                "metric_name": metric_name,
                                "raw_value": py_raw,
                                "normalized_value": py_val,
                                "confidence": 0.95,
                                "page_or_sheet": f"Page {page_num}",
                                "financial_period": py_period
                            })
                        break

        # Fallback text regex if word extraction was empty
        if not metrics:
            rev_match = re.search(r'Revenue\s*from\s*Operations[^\d]*([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
            if rev_match and len(rev_match.group(1).replace(',', '')) > 4:
                metrics.append({
                    "metric_name": "revenue_from_operations",
                    "raw_value": rev_match.group(1),
                    "normalized_value": parse_indian_number(rev_match.group(1)),
                    "confidence": 0.80,
                    "page_or_sheet": f"Page {page_num}",
                    "financial_period": "FY 2024-25 (Audited)"
                })

            pat_match = re.search(r'Profit\s*(?:for\s*the\s*year|After\s*Tax|PAT)[^\d]*([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
            if pat_match and len(pat_match.group(1).replace(',', '')) > 4:
                metrics.append({
                    "metric_name": "pat",
                    "raw_value": pat_match.group(1),
                    "normalized_value": parse_indian_number(pat_match.group(1)),
                    "confidence": 0.80,
                    "page_or_sheet": f"Page {page_num}",
                    "financial_period": "FY 2024-25 (Audited)"
                })

        return metrics

    @staticmethod
    def _extract_excel(file_path: str, category_hint: Optional[str]) -> List[Dict[str, Any]]:
        extracted = []
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            for sheetname in wb.sheetnames:
                ws = wb[sheetname]
                for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                    if not row:
                        continue
                    row_str = " ".join([str(c) for c in row if c is not None])
                    
                    # Check for EMI Obligation rows
                    if any(kw in row_str.lower() for kw in ["sanction", "outstanding", "emi", "tenure"]):
                        for c_idx, cell in enumerate(row):
                            val = parse_indian_number(str(cell))
                            if val and val > Decimal("1000"):
                                extracted.append({
                                    "metric_name": "existing_facility_amount",
                                    "raw_value": str(cell),
                                    "normalized_value": val,
                                    "confidence": 0.80,
                                    "page_or_sheet": f"{sheetname}:R{r_idx}C{c_idx+1}",
                                    "financial_period": "Current"
                                })
                                break
        except Exception as e:
            extracted.append({
                "metric_name": "excel_extraction_error",
                "raw_value": str(e),
                "normalized_value": None,
                "confidence": 0.0,
                "page_or_sheet": "Sheet1",
                "financial_period": "Unknown"
            })
        return extracted
