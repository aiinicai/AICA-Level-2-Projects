import os
import re
import csv
import io
import uuid
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from .database import get_db, log_audit

def sanitize_cell(val: Any) -> str:
    """Protects against spreadsheet formula injection."""
    if val is None:
        return ""
    s = str(val).strip()
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s

def compute_file_hash(file_bytes: bytes) -> str:
    """Computes SHA-256 hash of file content for duplicate file detection."""
    return hashlib.sha256(file_bytes).hexdigest()

def parse_amount(val: Any) -> Decimal:
    """Parses money amounts into exact Decimal, handling commas, currencies and parenthesized negatives."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    s = str(val).strip()
    if not s:
        return Decimal("0.00")
    # Handle (1,234.50) as negative
    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        is_negative = True
        s = s[1:].strip()
    # Remove currency symbols and formatting commas
    s = re.sub(r"[^\d.]", "", s)
    if not s:
        return Decimal("0.00")
    try:
        amt = Decimal(s)
        return -amt if is_negative else amt
    except Exception:
        return Decimal("0.00")

def parse_file_upload(
    file_bytes: bytes, 
    filename: str, 
    source_type: str, 
    account_id: str, 
    period_id: str,
    password: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parses uploaded ledger or bank statement files.
    Supports CSV, TSV, XLSX, XLS, OFX, QFX, MT940, CAMT.053 XML, Text/Scanned PDF, and Images.
    Returns (normalized_transactions, metadata)
    """
    ext = os.path.splitext(filename)[1].lower()
    file_hash = compute_file_hash(file_bytes)
    records = []
    metadata = {
        "filename": filename,
        "file_hash": file_hash,
        "source_type": source_type,
        "record_count": 0,
        "total_inflows": 0.0,
        "total_outflows": 0.0,
        "opening_balance": None,
        "closing_balance": None,
        "is_ocr": False,
        "is_encrypted": False
    }

    supported_exts = ('.csv', '.tsv', '.txt', '.xlsx', '.xls', '.ofx', '.qfx', '.xml', '.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif')
    if ext not in supported_exts:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats: Excel (.xlsx, .xls), CSV/TSV, "
            f"SWIFT MT940 (.txt, .sta), OFX/QFX, CAMT.053 XML (.xml), PDF (.pdf), and Scanned Images (.png, .jpg, .tiff)."
        )

    if ext in ('.csv', '.tsv', '.txt'):
        text_content = file_bytes.decode('utf-8', errors='ignore')
        # Check if MT940
        if ":60F:" in text_content or ":61:" in text_content:
            records, meta = parse_mt940_text(text_content, filename)
            metadata.update(meta)
        elif "<OFX>" in text_content or "<STMTTRN>" in text_content:
            records, meta = parse_ofx_text(text_content, filename)
            metadata.update(meta)
        elif "<Document" in text_content and ("BkToCstmrStmt" in text_content or "camt.053" in text_content):
            records, meta = parse_camt053_xml(text_content, filename)
            metadata.update(meta)
        else:
            delimiter = '\t' if ext == '.tsv' or '\t' in text_content[:500] else ','
            df = pd.read_csv(io.StringIO(text_content), sep=delimiter, dtype=str)
            records = parse_dataframe(df, source_type, filename)

    elif ext in ('.xlsx', '.xls'):
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        records = parse_dataframe(df, source_type, filename)

    elif ext in ('.ofx', '.qfx'):
        text_content = file_bytes.decode('utf-8', errors='ignore')
        records, meta = parse_ofx_text(text_content, filename)
        metadata.update(meta)

    elif ext == '.xml':
        text_content = file_bytes.decode('utf-8', errors='ignore')
        if "BkToCstmrStmt" in text_content or "camt.053" in text_content:
            records, meta = parse_camt053_xml(text_content, filename)
            metadata.update(meta)
        elif "<OFX>" in text_content or "<STMTTRN>" in text_content:
            records, meta = parse_ofx_text(text_content, filename)
            metadata.update(meta)
        else:
            raise ValueError("Unrecognized XML schema. Supported banking XML format: CAMT.053 (ISO 20022).")

    elif ext == '.pdf':
        records, meta = parse_pdf_document(file_bytes, filename, source_type, password)
        metadata.update(meta)

    elif ext in ('.png', '.jpg', '.jpeg', '.tiff', '.tif'):
        records, meta = parse_image_ocr(file_bytes, filename, source_type)
        metadata.update(meta)

    # Calculate sums
    inflows = Decimal("0.00")
    outflows = Decimal("0.00")
    for r in records:
        amt = Decimal(str(r["signed_amount"]))
        if amt > 0:
            inflows += amt
        else:
            outflows += amt

    metadata["record_count"] = len(records)
    metadata["total_inflows"] = float(inflows)
    metadata["total_outflows"] = float(outflows)

    return records, metadata

def parse_dataframe(df: pd.DataFrame, source_type: str, filename: str) -> List[Dict[str, Any]]:
    # Clean column names
    col_map = {}
    for col in df.columns:
        norm = str(col).strip().lower().replace(" ", "_").replace(".", "")
        col_map[norm] = col

    def get_val(row, *candidates):
        for c in candidates:
            if c in col_map:
                v = row[col_map[c]]
                if pd.notna(v):
                    return str(v).strip()
        return None

    results = []
    for idx, row in df.iterrows():
        date_val = get_val(row, "transaction_date", "date", "tx_date", "posting_date", "value_date")
        desc = get_val(row, "description", "narrative", "details", "particulars", "memo", "line_description") or "Transaction"
        ref = get_val(row, "reference", "ref", "ref_no", "reference_number", "trans_ref", "document_number")
        chk = get_val(row, "cheque_number", "cheque", "check_no", "chk_no")
        pay_id = get_val(row, "payment_id", "voucher_no", "payment_ref", "transfer_id")
        journal_id = get_val(row, "journal_id", "gl_batch", "journal_batch", "je_header_id")
        counterparty = get_val(row, "counterparty", "party", "beneficiary", "vendor_customer")
        
        debit_val = get_val(row, "debit", "dr", "withdrawal", "payment")
        credit_val = get_val(row, "credit", "cr", "deposit", "receipt")
        amt_val = get_val(row, "amount", "net_amount", "signed_amount")

        # Standard cash convention:
        # Inflow (Deposit / Receipt) = + signed amount
        # Outflow (Withdrawal / Payment) = - signed amount
        debit_dec = parse_amount(debit_val)
        credit_dec = parse_amount(credit_val)

        if debit_val is not None or credit_val is not None:
            if source_type == "Oracle Ledger":
                # In General Ledger: Debit Cash = Inflow (+), Credit Cash = Outflow (-)
                signed_amt = debit_dec - credit_dec
            else:
                # In Bank Statement: Deposit/Credit = Inflow (+), Debit/Withdrawal = Outflow (-)
                signed_amt = credit_dec - debit_dec
        elif amt_val is not None:
            signed_amt = parse_amount(amt_val)
        else:
            continue

        # Format date
        date_str = datetime.now().strftime("%Y-%m-%d")
        if date_val is not None:
            try:
                date_str = pd.to_datetime(str(date_val)).strftime("%Y-%m-%d")
            except Exception:
                date_str = str(date_val)[:10]

        results.append({
            "source": source_type,
            "tx_date": date_str,
            "posting_date": date_str,
            "value_date": date_str,
            "description": str(desc),
            "counterparty": str(counterparty) if counterparty else None,
            "reference": str(ref) if ref else None,
            "cheque_number": str(chk) if chk else None,
            "payment_id": str(pay_id) if pay_id else None,
            "journal_id": str(journal_id) if journal_id else None,
            "debit": float(debit_dec) if debit_dec else (float(abs(signed_amt)) if signed_amt < 0 else 0.0),
            "credit": float(credit_dec) if credit_dec else (float(signed_amt) if signed_amt > 0 else 0.0),
            "signed_amount": float(signed_amt),
            "doc_name": filename,
            "doc_row": int(idx) + 1,
            "confidence_score": 1.0,
            "is_uncertain": 0
        })

    return results

def parse_mt940_text(text: str, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Parses standard SWIFT MT940 statement text."""
    records = []
    meta = {}
    lines = text.splitlines()
    curr_tx = None

    for idx, line in enumerate(lines):
        line = line.strip()
        if line.startswith(":60F:") or line.startswith(":60M:"):
            m = re.match(r":60[FM]:([CD])(\d{6})([A-Z]{3})([\d,]+)", line)
            if m:
                d_c, d_str, ccy, amt_str = m.groups()
                amt = Decimal(amt_str.replace(",", "."))
                meta["opening_balance"] = float(amt if d_c == "C" else -amt)

        elif line.startswith(":62F:") or line.startswith(":62M:"):
            m = re.match(r":62[FM]:([CD])(\d{6})([A-Z]{3})([\d,]+)", line)
            if m:
                d_c, d_str, ccy, amt_str = m.groups()
                amt = Decimal(amt_str.replace(",", "."))
                meta["closing_balance"] = float(amt if d_c == "C" else -amt)

        elif line.startswith(":61:"):
            m = re.match(r":61:(\d{6})(\d{4})?([CD]|RC|RD)([\d,]+)[A-Z]{4}([^\n/]+)?(//([^\n]+))?", line)
            if m:
                val_date, _, dc, amt_str, desc_part, _, ref_part = m.groups()
                amt = Decimal(amt_str.replace(",", "."))
                signed = amt if dc in ("C", "RC") else -amt
                try:
                    yy, mm, dd = "20" + val_date[:2], val_date[2:4], val_date[4:6]
                    d_iso = f"{yy}-{mm}-{dd}"
                except Exception:
                    d_iso = datetime.now().strftime("%Y-%m-%d")

                curr_tx = {
                    "source": "Bank Statement",
                    "tx_date": d_iso,
                    "posting_date": d_iso,
                    "value_date": d_iso,
                    "description": (desc_part or "Bank Movement").strip(),
                    "reference": (ref_part or "").strip() or None,
                    "signed_amount": float(signed),
                    "debit": float(amt) if signed < 0 else 0.0,
                    "credit": float(amt) if signed > 0 else 0.0,
                    "doc_name": filename,
                    "doc_row": idx + 1,
                    "confidence_score": 1.0,
                    "is_uncertain": 0
                }
                records.append(curr_tx)
        elif line.startswith(":86:") and curr_tx:
            narrative = line[4:].strip()
            curr_tx["description"] = f"{curr_tx['description']} {narrative}".strip()

    return records, meta

def parse_ofx_text(text: str, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Parses standard OFX / QFX statement format."""
    records = []
    meta = {}
    stmttrns = re.findall(r"<STMTTRN>([\s\S]*?)</STMTTRN>", text, re.IGNORECASE)
    for idx, block in enumerate(stmttrns):
        def get_tag(tag):
            m = re.search(rf"<{tag}>([^<\r\n]+)", block, re.IGNORECASE)
            return m.group(1).strip() if m else None

        trnamt = get_tag("TRNAMT")
        fitid = get_tag("FITID")
        name = get_tag("NAME") or get_tag("MEMO") or "Bank Transaction"
        dtposted = get_tag("DTPOSTED") or ""
        checknum = get_tag("CHECKNUM")

        signed_amt = Decimal(trnamt) if trnamt else Decimal("0.00")
        date_iso = datetime.now().strftime("%Y-%m-%d")
        if len(dtposted) >= 8:
            date_iso = f"{dtposted[:4]}-{dtposted[4:6]}-{dtposted[6:8]}"

        records.append({
            "source": "Bank Statement",
            "tx_date": date_iso,
            "posting_date": date_iso,
            "value_date": date_iso,
            "description": name,
            "reference": fitid,
            "cheque_number": checknum,
            "signed_amount": float(signed_amt),
            "debit": float(abs(signed_amt)) if signed_amt < 0 else 0.0,
            "credit": float(signed_amt) if signed_amt > 0 else 0.0,
            "doc_name": filename,
            "doc_row": idx + 1,
            "confidence_score": 1.0,
            "is_uncertain": 0
        })

    bal_match = re.search(r"<LEDGERBAL>[\s\S]*?<BALAMT>([^<\r\n]+)", text, re.IGNORECASE)
    if bal_match:
        meta["closing_balance"] = float(bal_match.group(1).strip())

    return records, meta

def parse_camt053_xml(xml_content: str, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Parses ISO 20022 CAMT.053 XML statement files."""
    records = []
    meta = {}

    # Strip XML namespaces for simplified element access
    clean_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_content, count=1)
    try:
        root = ET.fromstring(clean_xml)
    except Exception as e:
        raise ValueError(f"Failed to parse CAMT.053 XML: {str(e)}")

    # Extract Balances
    for bal in root.iter("Bal"):
        tp = bal.find(".//Tp/CdOrPrtry/Cd")
        amt_el = bal.find("Amt")
        cdt_dbt = bal.find("CdtDbtInd")
        if tp is not None and amt_el is not None and amt_el.text:
            amt = Decimal(amt_el.text)
            signed = amt if (cdt_dbt is not None and cdt_dbt.text == "CRDT") else -amt
            if tp.text == "OPBD":
                meta["opening_balance"] = float(signed)
            elif tp.text == "CLBD":
                meta["closing_balance"] = float(signed)

    # Extract Statement Entries (<Ntry>)
    row_idx = 1
    for ntry in root.iter("Ntry"):
        amt_el = ntry.find("Amt")
        cdt_dbt = ntry.find("CdtDbtInd")
        if amt_el is None or not amt_el.text:
            continue

        raw_amt = Decimal(amt_el.text)
        is_credit = (cdt_dbt is not None and cdt_dbt.text == "CRDT")
        signed_amt = raw_amt if is_credit else -raw_amt

        # Date
        def get_elem_text(elem, *xpaths):
            for xp in xpaths:
                found = elem.find(xp)
                if found is not None and found.text:
                    return found.text.strip()
            return None

        date_text = get_elem_text(ntry, ".//BookgDt/Dt", ".//ValDt/Dt", ".//BookgDt/DtTm")
        date_str = date_text[:10] if date_text else datetime.now().strftime("%Y-%m-%d")

        # Reference & Details
        ref_val = get_elem_text(ntry, ".//NtryDtls/TxDtls/Refs/EndToEndId", ".//NtryDtls/TxDtls/Refs/AcctSvcrRef", ".//AcctSvcrRef")
        desc_val = get_elem_text(ntry, ".//NtryDtls/TxDtls/RmtInf/Ustrd", ".//AddtlNtryInf") or "CAMT.053 Bank Entry"
        party_val = get_elem_text(ntry, ".//NtryDtls/TxDtls/RltdPties/Cdtr/Nm", ".//NtryDtls/TxDtls/RltdPties/Dbtr/Nm")

        records.append({
            "source": "Bank Statement",
            "tx_date": date_str,
            "posting_date": date_str,
            "value_date": date_str,
            "description": desc_val[:150],
            "counterparty": party_val,
            "reference": ref_val,
            "cheque_number": None,
            "signed_amount": float(signed_amt),
            "debit": float(raw_amt) if not is_credit else 0.0,
            "credit": float(raw_amt) if is_credit else 0.0,
            "doc_name": filename,
            "doc_row": row_idx,
            "confidence_score": 1.0,
            "is_uncertain": 0
        })
        row_idx += 1

    return records, meta

def parse_pdf_document(file_bytes: bytes, filename: str, source_type: str, password: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Handles text and encrypted PDFs securely without retaining password."""
    meta = {"is_encrypted": False, "is_ocr": False}
    full_text = ""

    # Try PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if doc.is_encrypted:
            meta["is_encrypted"] = True
            if not password:
                raise ValueError("PDF is password-protected. Please provide the document password to decrypt and process.")
            auth_ok = doc.authenticate(password)
            if not auth_ok:
                raise ValueError("Incorrect PDF password. Decryption failed.")
        full_text = "\n".join([page.get_text() for page in doc])
    except ImportError:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            meta["is_encrypted"] = True
            if not password:
                raise ValueError("PDF is password-protected. Please provide the document password to decrypt and process.")
            decrypt_res = reader.decrypt(password)
            if decrypt_res == 0:
                raise ValueError("Incorrect PDF password. Decryption failed.")
        full_text = "\n".join([p.extract_text() or "" for p in reader.pages])

    if not full_text.strip():
        # Scanned PDF with no digital text layer
        meta["is_ocr"] = True
        return parse_image_ocr(file_bytes, filename, source_type)

    records = parse_pdf_text_lines(full_text, source_type, filename)
    return records, meta

def parse_image_ocr(file_bytes: bytes, filename: str, source_type: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Performs OCR on scanned PDFs or image formats (PNG, JPG, TIFF).
    Checks for pytesseract availability and provides clear diagnostic if absent.
    """
    meta = {"is_ocr": True}
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)
        records = parse_pdf_text_lines(text, source_type, filename)
        for r in records:
            r["confidence_score"] = 0.85
            r["is_uncertain"] = 1 # Mandatory review for OCR
        return records, meta
    except ImportError:
        raise ValueError(
            "Scanned Image / OCR processing requires 'pytesseract' and Tesseract OCR engine. "
            "Please upload digital statement formats (Excel, CSV, MT940, OFX, CAMT.053 XML, or text-based PDF), "
            "or configure Tesseract OCR in the server environment."
        )
    except Exception as e:
        raise ValueError(f"OCR processing failed: {str(e)}")

def parse_pdf_text_lines(text: str, source_type: str, filename: str) -> List[Dict[str, Any]]:
    """Extracts tabular statement lines from text."""
    records = []
    lines = text.splitlines()
    date_regex = re.compile(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})")
    amt_regex = re.compile(r"([-+]?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2}))")

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        date_match = date_regex.search(line)
        amt_matches = amt_regex.findall(line)
        if date_match and amt_matches:
            d_str = date_match.group(1)
            raw_amt = amt_matches[-1]
            amt = parse_amount(raw_amt)
            rem_desc = line.replace(d_str, "").replace(raw_amt, "").strip()
            if not rem_desc:
                rem_desc = f"{source_type} Item"

            try:
                parsed_dt = pd.to_datetime(d_str).strftime("%Y-%m-%d")
            except Exception:
                parsed_dt = datetime.now().strftime("%Y-%m-%d")

            records.append({
                "source": source_type,
                "tx_date": parsed_dt,
                "posting_date": parsed_dt,
                "value_date": parsed_dt,
                "description": rem_desc[:120],
                "reference": f"PDF-REF-{idx+1:04d}",
                "signed_amount": float(amt),
                "debit": float(abs(amt)) if amt < 0 else 0.0,
                "credit": float(amt) if amt > 0 else 0.0,
                "doc_name": filename,
                "doc_row": idx + 1,
                "confidence_score": 1.0,
                "is_uncertain": 0
            })
    return records

def import_master_data(file_bytes: bytes, filename: str, master_type: str, user: str = "Administrator") -> Dict[str, Any]:
    """
    Bulk imports Companies or Bank Accounts from Excel or CSV.
    Preserves leading zeros on account numbers and references.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext in ('.csv', '.tsv', '.txt'):
        delimiter = '\t' if ext == '.tsv' else ','
        df = pd.read_csv(io.BytesIO(file_bytes), sep=delimiter, dtype=str)
    elif ext in ('.xlsx', '.xls'):
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    else:
        raise ValueError("Unsupported master data file format. Use Excel (.xlsx, .xls) or CSV.")

    conn = get_db()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    imported_count = 0

    try:
        if master_type.lower() == "companies":
            # Required: code, name. Optional: reporting_currency
            for _, row in df.iterrows():
                code = str(row.get("code") or row.get("Company Code") or "").strip()
                name = str(row.get("name") or row.get("Company Name") or "").strip()
                ccy = str(row.get("reporting_currency") or row.get("Currency") or "USD").strip().upper()
                if not code or not name:
                    continue
                c_id = f"CMP-{code.replace(' ', '_').upper()}"
                cur.execute("""
                    INSERT INTO companies (id, code, name, reporting_currency, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET name=excluded.name, reporting_currency=excluded.reporting_currency
                """, (c_id, code, name, ccy, now_iso))
                imported_count += 1

        elif master_type.lower() in ("accounts", "bank_accounts"):
            # Required: company_code, bank_name, account_number, gl_account.
            for _, row in df.iterrows():
                comp_code = str(row.get("company_code") or row.get("Company Code") or "").strip()
                bank_name = str(row.get("bank_name") or row.get("Bank Name") or "").strip()
                acc_num = str(row.get("account_number") or row.get("Account Number") or "").strip()
                gl_acc = str(row.get("gl_account") or row.get("GL Account") or "").strip()
                ccy = str(row.get("currency") or row.get("Currency") or "USD").strip().upper()
                branch = str(row.get("branch") or row.get("Branch") or "Main").strip()
                iban = str(row.get("iban") or row.get("IBAN") or "").strip()
                gl_sub = str(row.get("gl_sub_account") or row.get("Sub Account") or "").strip()

                if not bank_name or not acc_num or not gl_acc:
                    continue

                # Find company ID
                cur.execute("SELECT id FROM companies WHERE code = ?", (comp_code,))
                c_row = cur.fetchone()
                comp_id = c_row["id"] if c_row else "CMP-01"

                a_id = f"ACC-{uuid.uuid4().hex[:8].upper()}"
                cur.execute("""
                    INSERT INTO bank_accounts (id, company_id, bank_name, branch, account_number, iban, currency, gl_account, gl_sub_account, status, opening_balance, recon_start_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', 0.0, '2026-09-01', ?)
                """, (a_id, comp_id, bank_name, branch, acc_num, iban, ccy, gl_acc, gl_sub, now_iso))
                imported_count += 1
        else:
            raise ValueError(f"Unknown master data type '{master_type}'. Use 'companies' or 'accounts'.")

        log_audit(conn, user, "BULK_MASTER_IMPORT", master_type, "bulk", None, {"imported_count": imported_count}, f"Imported {imported_count} {master_type} from {filename}")
        conn.commit()
        return {"success": True, "master_type": master_type, "imported_count": imported_count}
    finally:
        conn.close()
