import os
import io
import re
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.import_batch import ImportBatch, ImportErrorLog
from app.models.branch import Branch
from app.models.payment_channel import PaymentChannel, ChannelMapping
from app.models.daily_sales import DailySale
from app.models.cash_rec import CashReconciliation
from app.models.bank_transaction import BankTransaction
from app.models.settlement import SettlementBatch, AggregatorDeduction
from app.models.aggregator import Aggregator
from app.services.audit_service import log_action
from app.services.cash_service import create_or_update_cash_reconciliation
from app.services.aggregator_service import create_or_update_settlement_batch

def normalize_column_name(col_name: str) -> str:
    return str(col_name).strip().lower().replace("_", " ").replace("-", " ")

def get_channel_id_for_alias(db: Session, raw_alias: str, branch_id: Optional[int] = None) -> Optional[int]:
    clean_alias = normalize_column_name(raw_alias)
    
    # 1. Exact or partial match in ChannelMapping
    mappings = db.query(ChannelMapping).all()
    for m in mappings:
        if normalize_column_name(m.alias) == clean_alias or m.alias.lower() in clean_alias:
            return m.payment_channel_id

    # 2. Check PaymentChannel names
    channels = db.query(PaymentChannel).all()
    for c in channels:
        ch_name = normalize_column_name(c.name)
        if ch_name in clean_alias or clean_alias in ch_name:
            return c.id

    return None

def parse_file_to_dataframe(file_content: bytes, filename: str) -> pd.DataFrame:
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(io.BytesIO(file_content))
    elif ext == ".csv":
        df = pd.read_csv(io.BytesIO(file_content))
    elif ext == ".pdf":
        df = _parse_ledger_pdf_to_dataframe(file_content, filename)
    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
        from app.services.image_ocr_service import parse_image_to_dataframe
        df = parse_image_to_dataframe(file_content, filename)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Only .xlsx, .xls, .csv, .pdf, and image files (.jpg, .jpeg, .png, .webp) are supported.")
    return df

def process_daily_sales_import(
    db: Session,
    file_content: bytes,
    filename: str,
    branch_id: int,
    custom_mappings: Optional[Dict[str, int]] = None,
    user=None
) -> ImportBatch:
    df = parse_file_to_dataframe(file_content, filename)
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise ValueError("Invalid Branch selected for import.")

    batch = ImportBatch(
        filename=filename,
        file_type="DAILY_SALES",
        source_name=branch.name,
        uploaded_by_id=user.id if user else None,
        total_rows=len(df),
        status="PROCESSING"
    )
    db.add(batch)
    db.flush()

    success_count = 0
    failed_count = 0
    duplicate_count = 0

    # Auto-detect date column
    date_col = None
    for col in df.columns:
        if "date" in normalize_column_name(col):
            date_col = col
            break
    if not date_col and len(df.columns) > 0:
        date_col = df.columns[0] # Fallback to first column

    for idx, row in df.iterrows():
        row_num = idx + 2 # 1-indexed + header row
        try:
            # Parse Date
            raw_date = row.get(date_col)
            if pd.isna(raw_date):
                err = ImportErrorLog(import_batch=batch, row_number=row_num, raw_data=str(row.to_dict()), error_message="Missing or invalid Date value.")
                db.add(err)
                failed_count += 1
                continue

            sale_date = pd.to_datetime(raw_date).date()

            # Iterate sales channel columns in row
            for col in df.columns:
                if col == date_col:
                    continue

                raw_amt = row.get(col)
                if pd.isna(raw_amt):
                    continue
                try:
                    amt = float(raw_amt)
                except ValueError:
                    continue

                if amt < 0:
                    continue # Skip non-positive sales if standard sales

                # Resolve Channel ID
                channel_id = custom_mappings.get(col) if custom_mappings else get_channel_id_for_alias(db, col, branch_id)
                if not channel_id:
                    # Skip columns that aren't sales channels (like remarks, total sales, etc.)
                    continue

                # Check duplicate
                existing_sale = db.query(DailySale).filter(
                    DailySale.branch_id == branch_id,
                    DailySale.sale_date == sale_date,
                    DailySale.payment_channel_id == channel_id
                ).first()

                if existing_sale:
                    existing_sale.amount = amt
                    existing_sale.import_batch_id = batch.id
                    duplicate_count += 1
                else:
                    new_sale = DailySale(
                        branch_id=branch_id,
                        sale_date=sale_date,
                        payment_channel_id=channel_id,
                        amount=amt,
                        import_batch_id=batch.id
                    )
                    db.add(new_sale)

            success_count += 1

        except Exception as e:
            err = ImportErrorLog(import_batch=batch, row_number=row_num, raw_data=str(row.to_dict()), error_message=str(e))
            db.add(err)
            failed_count += 1

    batch.success_rows = success_count
    batch.failed_rows = failed_count
    batch.duplicate_rows = duplicate_count
    batch.status = "COMPLETED" if failed_count == 0 else "PARTIAL"

    db.commit()
    log_action(db, "IMPORT_DAILY_SALES", "ImportBatch", batch.id, None, {"filename": filename, "success": success_count, "failed": failed_count}, user=user)

    posted_q = db.query(DailySale.sale_date).filter(DailySale.import_batch_id == batch.id)
    posted_dates = [d for (d,) in posted_q.all() if d]
    if posted_dates:
        from app.services.cash_service import post_daybook_to_related_tabs
        post_daybook_to_related_tabs(
            db, branch_id, min(posted_dates), max(posted_dates), user=user
        )

    return batch

_BANK_ACCOUNT_HINTS = (
    "bank", "kotak", "axis", "hdfc", "icici", "sbi", "pnb", "yes bank",
    "idfc", "indusind", "federal", "canara", "union bank", "bank of baroda",
    "indian bank", "uco", "rbl", "au bank", "aubank", "hsbc",
    "standard chartered", "citi", "paytm bank",
)
_LEDGER_SKIP_ACCOUNTS = (
    "sales", "service charge", "service charges", "opening", "closing",
    "total", "balance b/d", "balance c/d", "profit", "discount",
    "commission", "round off",
)
_LEDGER_SKIP_TYPES = (
    "jrnl", "journal", "jnl", "pymt", "payment", "cntr", "contra", "c/f",
)


def _ledger_text(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return re.sub(r"\s+", " ", str(val).strip())


def _ledger_amount(val) -> float:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    raw = str(val).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    raw = re.sub(r"[^\d.\-]", "", raw)
    if not raw or raw in (".", "-", "-."):
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _is_bank_ledger_account(name: str) -> bool:
    n = _ledger_text(name).lower()
    if not n or n in ("nan", "none", "-"):
        return False
    if any(skip in n for skip in _LEDGER_SKIP_ACCOUNTS) and "bank" not in n:
        return False
    return any(hint in n for hint in _BANK_ACCOUNT_HINTS)


def _is_skipped_ledger_type(val: str) -> bool:
    return _ledger_text(val).lower() in _LEDGER_SKIP_TYPES


def _col_map(df: pd.DataFrame) -> Dict[str, Any]:
    return {normalize_column_name(c): c for c in df.columns}


def _pick_col(cols: Dict[str, Any], *names):
    for name in names:
        if name in cols:
            return cols[name]
    for key, original in cols.items():
        for name in names:
            if name and name in key:
                return original
    return None


def _is_tally_ledger(df: pd.DataFrame) -> bool:
    cols = _col_map(df)
    has_account = _pick_col(cols, "account") is not None
    has_type = _pick_col(cols, "type") is not None
    has_credit = _pick_col(cols, "credit", "credit(rs.)", "credit (rs.)", "credit rs", "credit(rs)") is not None
    return bool(has_account and (has_type or has_credit))


def _header_score(values: List[str]) -> int:
    joined = " ".join(values)
    score = 0
    for token in ("date", "type", "account", "credit", "debit", "balance", "vch", "bill"):
        if token in joined:
            score += 1
    return score


def _promote_header_frame(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        return raw if raw is not None else pd.DataFrame()
    best_idx, best_score = 0, -1
    scan = min(25, len(raw))
    for i in range(scan):
        values = [normalize_column_name(_ledger_text(v)) for v in list(raw.iloc[i].values)]
        score = _header_score(values)
        if score > best_score:
            best_score = score
            best_idx = i
    if best_score < 2:
        return raw
    headers = []
    seen = {}
    for v in list(raw.iloc[best_idx].values):
        name = _ledger_text(v) or "Column"
        count = seen.get(name, 0) + 1
        seen[name] = count
        headers.append(name if count == 1 else f"{name}_{count}")
    body = raw.iloc[best_idx + 1:].copy()
    width = len(body.columns)
    if len(headers) < width:
        headers.extend(f"Column_{i}" for i in range(len(headers) + 1, width + 1))
    body.columns = headers[:width]
    body = body.dropna(how="all")
    return body.reset_index(drop=True)


_PDF_DATE = re.compile(r"^\d{1,2}[-/](?:[A-Za-z]{3}|\d{1,2})[-/]\d{2,4}$")
_PDF_TYPE = re.compile(r"^(Rcpt|Receipt|Jrnl|Journal|Jnl|Pymt|Payment|Cntr|Contra)$", re.I)
_PDF_MONEY = re.compile(r"[\d,]+\.\d{2}")


def _parse_ledger_pdf_text_rows(text: str) -> List[List[str]]:
    rows = [["Date", "Type", "Vch/Bill No", "Account", "Debit(Rs.)", "Credit(Rs.)", "Balance(Rs.)"]]
    for raw_line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        parts = line.split(" ")
        if len(parts) < 3 or not _PDF_DATE.match(parts[0]) or not _PDF_TYPE.match(parts[1]):
            continue
        tx_date, tx_type = parts[0], parts[1]
        rest = " ".join(parts[2:])
        amounts = _PDF_MONEY.findall(rest)
        account = rest
        for amt in amounts:
            account = account.replace(amt, " ")
        account = re.sub(r"\s+", " ", account).replace(" Dr", "").replace(" Cr", "").strip()
        debit = credit = balance = ""
        if tx_type.lower() in ("rcpt", "receipt"):
            if len(amounts) >= 2:
                credit, balance = amounts[0], amounts[-1]
            elif amounts:
                credit = amounts[0]
        else:
            if len(amounts) >= 2:
                debit, balance = amounts[0], amounts[-1]
            elif amounts:
                debit = amounts[0]
        rows.append([tx_date, tx_type, "", account, debit, credit, balance])
    return rows


def _parse_ledger_pdf_to_dataframe(file_content: bytes, filename: str) -> pd.DataFrame:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ValueError("PDF ledger import needs pdfplumber. Run: pip install pdfplumber") from exc

    tables: List[pd.DataFrame] = []
    text_chunks: List[str] = []
    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        if not pdf.pages:
            raise ValueError("The PDF has no pages.")
        for page in pdf.pages:
            extracted = page.extract_tables() or []
            for table in extracted:
                cleaned = [[_ledger_text(c) for c in (row or [])] for row in table if row and any(_ledger_text(c) for c in row)]
                if cleaned:
                    tables.append(pd.DataFrame(cleaned))
            page_text = page.extract_text() or ""
            if page_text:
                text_chunks.append(page_text)

    frames = [_promote_header_frame(t) for t in tables if t is not None and not t.empty]
    frames = [f for f in frames if f is not None and not f.empty]
    if frames:
        df = pd.concat(frames, ignore_index=True)
        if _is_tally_ledger(df) or _pick_col(_col_map(df), "date"):
            return df.dropna(how="all").reset_index(drop=True)

    text_rows = _parse_ledger_pdf_text_rows("\n".join(text_chunks))
    if len(text_rows) > 1:
        raw = pd.DataFrame(text_rows)
        return _promote_header_frame(raw)

    raise ValueError("Could not read a Date / Type / Account / Credit table from this PDF. Export the Tally ledger as Excel if the PDF is a scan.")


def _load_bank_or_ledger_dataframe(file_content: bytes, filename: str) -> pd.DataFrame:
    """Read a bank statement or Tally ledger, promoting the real header row."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return _parse_ledger_pdf_to_dataframe(file_content, filename)
    if ext not in (".xlsx", ".xls"):
        return parse_file_to_dataframe(file_content, filename)

    raw = pd.read_excel(io.BytesIO(file_content), header=None)
    if raw.empty:
        return raw

    best_idx, best_score = 0, -1
    scan = min(25, len(raw))
    for i in range(scan):
        values = [normalize_column_name(_ledger_text(v)) for v in list(raw.iloc[i].values)]
        score = _header_score(values)
        if score > best_score:
            best_score = score
            best_idx = i
    if best_score < 2:
        return parse_file_to_dataframe(file_content, filename)

    headers = []
    seen = {}
    for v in list(raw.iloc[best_idx].values):
        name = _ledger_text(v) or "Column"
        count = seen.get(name, 0) + 1
        seen[name] = count
        headers.append(name if count == 1 else f"{name}_{count}")
    body = raw.iloc[best_idx + 1:].copy()
    body.columns = headers
    body = body.dropna(how="all")
    return body.reset_index(drop=True)


def process_bank_statement_import(
    db: Session,
    file_content: bytes,
    filename: str,
    bank_account: str,
    user=None
) -> ImportBatch:
    df = _load_bank_or_ledger_dataframe(file_content, filename)
    is_ledger = _is_tally_ledger(df)
    source = (bank_account or "Bank Ledger")[:50]
    if is_ledger:
        source = (bank_account or "Card / QR Ledger")[:50]

    batch = ImportBatch(
        filename=filename,
        file_type="TALLY_LEDGER" if is_ledger else "BANK_STATEMENT",
        source_name=source,
        uploaded_by_id=user.id if user else None,
        total_rows=len(df),
        status="PROCESSING"
    )
    db.add(batch)
    db.flush()

    cols = _col_map(df)
    date_col = _pick_col(cols, "tx date", "transaction date", "date") or df.columns[0]
    type_col = _pick_col(cols, "type")
    account_col = _pick_col(cols, "account")
    desc_col = _pick_col(cols, "description", "narration", "particulars", "account")
    ref_col = _pick_col(cols, "vch/bill no", "vch bill no", "vch no", "bill no", "reference", "ref no", "chq/ref no", "utr")
    credit_col = _pick_col(cols, "credit(rs.)", "credit (rs.)", "credit rs.", "credit rs", "credit(rs)", "credit amount", "cr amount", "credit")
    debit_col = _pick_col(cols, "debit(rs.)", "debit (rs.)", "debit rs.", "debit rs", "debit(rs)", "debit amount", "dr amount", "debit")
    amt_col = _pick_col(cols, "amount")

    success_count = 0
    failed_count = 0
    duplicate_count = 0
    skipped_count = 0

    for idx, row in df.iterrows():
        row_num = int(idx) + 2
        try:
            raw_date = row.get(date_col)
            if raw_date is None or (isinstance(raw_date, float) and pd.isna(raw_date)) or _ledger_text(raw_date) == "":
                skipped_count += 1
                continue
            tx_date = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
            if pd.isna(tx_date):
                skipped_count += 1
                continue
            tx_date = tx_date.date()

            ledger_account = _ledger_text(row.get(account_col)) if account_col else ""
            row_type = _ledger_text(row.get(type_col)) if type_col else ""

            if is_ledger:
                if _is_skipped_ledger_type(row_type):
                    skipped_count += 1
                    continue
                if not _is_bank_ledger_account(ledger_account):
                    skipped_count += 1
                    continue

            cr_val = _ledger_amount(row.get(credit_col)) if credit_col else 0.0
            dr_val = _ledger_amount(row.get(debit_col)) if debit_col else 0.0

            if cr_val == 0.0 and dr_val == 0.0 and amt_col:
                val = _ledger_amount(row.get(amt_col))
                if val >= 0:
                    cr_val = val
                else:
                    dr_val = abs(val)

            if is_ledger and cr_val <= 0:
                skipped_count += 1
                continue

            desc = _ledger_text(row.get(desc_col)) if desc_col else ledger_account
            ref = _ledger_text(row.get(ref_col)) if ref_col else ""
            account_name = (ledger_account or bank_account or "Bank")[:50]

            existing_tx = db.query(BankTransaction).filter(
                BankTransaction.bank_account == account_name,
                BankTransaction.tx_date == tx_date,
                BankTransaction.credit_amount == cr_val,
                BankTransaction.debit_amount == dr_val,
                BankTransaction.reference_no == ref
            ).first()

            if existing_tx:
                duplicate_count += 1
            else:
                bank_tx = BankTransaction(
                    bank_account=account_name,
                    tx_date=tx_date,
                    description=desc or ledger_account,
                    reference_no=ref,
                    credit_amount=cr_val,
                    debit_amount=dr_val,
                    amount=cr_val - dr_val,
                    import_batch_id=batch.id
                )
                db.add(bank_tx)
                success_count += 1

        except Exception as e:
            err = ImportErrorLog(import_batch=batch, row_number=row_num, raw_data=str(row.to_dict()), error_message=str(e))
            db.add(err)
            failed_count += 1

    batch.success_rows = success_count
    batch.failed_rows = failed_count
    batch.duplicate_rows = duplicate_count
    batch.status = "COMPLETED" if failed_count == 0 else "PARTIAL"
    batch._skipped_rows = skipped_count
    batch._import_mode = "TALLY_LEDGER" if is_ledger else "BANK_STATEMENT"

    db.commit()
    log_action(db, "IMPORT_BANK_STATEMENT", "ImportBatch", batch.id, None, {
        "filename": filename,
        "success": success_count,
        "skipped": skipped_count,
        "mode": batch._import_mode,
    }, user=user)

    return batch

def _swiggy_to_float(val) -> Optional[float]:
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    raw = str(val).strip().replace(",", "").replace("₹", "").replace("%", "")
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _swiggy_column_indexes(df: pd.DataFrame) -> Tuple[int, int]:
    """Use Particulars + Total only. Never read the Rules column."""
    names = [re.sub(r"\s+", " ", str(c).strip().lower()) for c in df.columns]
    particular_idx = 0
    amount_idx = len(names) - 1
    for i, name in enumerate(names):
        if "rule" in name:
            if amount_idx == i:
                amount_idx = max(0, i - 1) if i else len(names) - 1
            continue
        if name in ("s.no", "s.no.", "s no", "sno", "sr no", "sr.no", "sr. no.", "#"):
            continue
        if "particular" in name or name in ("description", "line item", "narration"):
            particular_idx = i
        if name in ("total", "amount") or name.endswith(" total"):
            amount_idx = i
    first = names[0] if names else ""
    if particular_idx == 0 and first.startswith("s.no"):
        particular_idx = 1 if len(names) > 1 else 0
    if amount_idx == particular_idx and len(names) > 1:
        amount_idx = len(names) - 1
    return particular_idx, amount_idx


def _swiggy_row_text_and_amount(row, particular_idx: int, amount_idx: int) -> Tuple[str, float]:
    values = list(row)
    particular_raw = values[particular_idx] if particular_idx < len(values) else ""
    particular = "" if pd.isna(particular_raw) else str(particular_raw).strip().lower()
    particular = re.sub(r"\s+", " ", particular)

    amount = _swiggy_to_float(values[amount_idx]) if amount_idx < len(values) else None
    if amount is None:
        for idx in range(len(values) - 1, -1, -1):
            if idx == particular_idx:
                continue
            name = str(row.index[idx]).strip().lower() if hasattr(row, "index") else ""
            if "rule" in name:
                continue
            amount = _swiggy_to_float(values[idx])
            if amount is not None:
                break
    return particular, abs(amount or 0.0)


def _swiggy_item_no(text: str) -> Optional[int]:
    match = re.match(r"^(\d+)\b", text.strip())
    return int(match.group(1)) if match else None


_SWIGGY_SHEET_HINTS = (
    "item total",
    "total customer paid",
    "net payout",
    "swiggy fees",
    "gst collected",
    "discount share",
    "swiggy one",
    "cost per click",
    "pocket hero",
    "gst on service fee",
    "merchant share of cancelled",
    "commissionable value",
    "payment mechanism",
    "government charges",
    "tds 194",
    "investment in growth",
    "total ads",
    "hyperpure",
)


def _dataframe_payout_score(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    values = [str(v).lower() for v in df.fillna("").astype(str).values.flatten()[:2500]]
    blob = " ".join(values)
    return sum(1 for hint in _SWIGGY_SHEET_HINTS if hint in blob)


def _extract_headered_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Rebuild a table when title rows sit above Particulars / Total."""
    if raw is None or raw.empty:
        return raw
    for i in range(min(25, len(raw))):
        cells = [str(v).strip().lower() for v in raw.iloc[i].tolist() if pd.notna(v)]
        joined = " ".join(cells)
        if "particular" in joined or "mapping rule" in joined or ("description" in joined and "total" in joined):
            header = [
                str(v).strip() if pd.notna(v) and str(v).strip() else f"col_{j}"
                for j, v in enumerate(raw.iloc[i].tolist())
            ]
            body = raw.iloc[i + 1:].copy()
            body.columns = header
            return body.reset_index(drop=True)
    raw = raw.copy()
    raw.columns = [f"col_{j}" for j in range(len(raw.columns))]
    if raw.columns.size > 0:
        raw = raw.rename(columns={"col_0": "Particulars"})
    return raw


def _load_best_payout_df(xls: pd.ExcelFile) -> pd.DataFrame:
    best_df = pd.DataFrame()
    best_score = -1
    for name in xls.sheet_names:
        try:
            raw = pd.read_excel(xls, sheet_name=name, header=None)
            framed = _extract_headered_frame(raw)
            default = pd.read_excel(xls, sheet_name=name)
        except Exception:
            continue
        name_l = str(name).strip().lower()
        bonus = 0
        if name_l == "payout breakup":
            bonus += 20
        if name_l in ("glossary", "hsummary", "hdiscount", "order level"):
            bonus -= 8
        for cand in (framed, default):
            score = _dataframe_payout_score(cand) + bonus
            if score > best_score:
                best_score = score
                best_df = cand
    return best_df


def _sno_column_index(df: pd.DataFrame) -> Optional[int]:
    names = [re.sub(r"\s+", " ", str(c).strip().lower()) for c in df.columns]
    for i, name in enumerate(names):
        compact = name.replace(" ", "").replace(".", "")
        if compact in ("sno", "srno") or name.startswith("s.no"):
            return i
    return None


def _parse_flex_date(text: str) -> Optional[date]:
    text = (text or "").strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _extract_metadata_from_workbook(db: Session, xls: pd.ExcelFile) -> Tuple[Optional[int], Optional[date], Optional[date]]:
    branches = db.query(Branch).all()
    branch_id = None
    dates: List[date] = []
    date_pat = re.compile(r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b")
    for name in xls.sheet_names:
        try:
            raw = pd.read_excel(xls, sheet_name=name, header=None)
        except Exception:
            continue
        for cell in raw.values.flatten():
            if pd.isna(cell):
                continue
            cell_str = str(cell).strip()
            if not cell_str or cell_str.lower() == "nan":
                continue
            low = cell_str.lower()
            if branch_id is None:
                for b in branches:
                    if b.name.lower() in low or b.code.lower() in low:
                        branch_id = b.id
                        break
            for match in date_pat.findall(cell_str):
                parsed = _parse_flex_date(match)
                if parsed:
                    dates.append(parsed)
    start = min(dates) if dates else None
    end = max(dates) if dates else None
    return branch_id, start, end


def _parse_swiggy_settlement(df: pd.DataFrame) -> Tuple[float, float, Dict[str, float]]:
    """
    Swiggy payout mapping (client rules):

    A. Total Customer Paid [1+2-3+4]
       1 Item Total, 2 Packaging, 3 Discount Share, 4 GST Collected
       Commissionable Value = Item Total - GST Collected (shown in working notes)
       Reconciling Total Sale = Customer Paid - GST Collected
         so Sale - Payout = Platform + Ads + Complaints + TCS + TDS

    B. Swiggy Fees (6-15) → Online Platform Charges

    C. Customer Complaints & Cancellation (16-17) → Miscellaneous

    D. Ads (Top Picks / Cost Per Click) → Business Promotion

    E. Taxes
       18 GST Deduction → GST Sec 9(5) (informational)
       19 TCS → TCS
       20 TDS → TDS Receivable

    F. Net Payout [A+B+C+D+E]
    """
    particular_idx, amount_idx = _swiggy_column_indexes(df)
    payout = 0.0
    total_customer_paid = 0.0
    item_total = 0.0
    gst_collected = 0.0

    deductions = {
        "COMMISSION": 0.0,
        "PROMOTION": 0.0,
        "TCS": 0.0,
        "TDS": 0.0,
        "GST_9_5": 0.0,
        "PACKING_CHARGES": 0.0,
        "MISC": 0.0,
    }

    found_b_fees = False
    found_c_complaints = False
    found_ads_total = False

    for _, row in df.iterrows():
        c_norm, val_total = _swiggy_row_text_and_amount(row, particular_idx, amount_idx)
        if not c_norm or c_norm in ("particulars", "particular", "description"):
            continue
        item_no = _swiggy_item_no(c_norm)

        if re.match(r"^orders?\b", c_norm):
            continue

        if "net payout" in c_norm:
            payout = val_total
            continue

        if "total customer paid" in c_norm:
            total_customer_paid = val_total
            continue

        if "item total" in c_norm and "customer" not in c_norm:
            if item_no == 1 or item_total == 0.0:
                item_total = val_total
            continue

        if (
            "gst collected" in c_norm
            and "deduction" not in c_norm
            and "service fee" not in c_norm
            and "9(5)" not in c_norm
            and "on behalf" not in c_norm
        ):
            if item_no in (4, 5) or gst_collected == 0.0:
                gst_collected = val_total
            continue

        if "packaging charge" in c_norm or "packing charge" in c_norm:
            deductions["PACKING_CHARGES"] += val_total
            continue

        if "discount share" in c_norm or "restaurant discount" in c_norm:
            continue

        if "b swiggy fees" in c_norm or c_norm.startswith("b swiggy"):
            deductions["COMMISSION"] += val_total
            found_b_fees = True
            continue

        if "c customer complaint" in c_norm:
            deductions["MISC"] += val_total
            found_c_complaints = True
            continue

        if "growth investment in ads" in c_norm:
            deductions["PROMOTION"] += val_total
            found_ads_total = True
            continue

        if c_norm.startswith("d other charges") or c_norm.startswith("e total tax"):
            continue

        if (
            "gst deduction" in c_norm
            or "paid by swiggy on behalf" in c_norm
            or "section 9(5)" in c_norm
            or "gst paid by" in c_norm
        ):
            deductions["GST_9_5"] += val_total
            continue

        if re.search(r"\btcs\b", c_norm) and "gst" not in c_norm:
            deductions["TCS"] += val_total
            continue

        if re.search(r"\btds\b", c_norm):
            deductions["TDS"] += val_total
            continue

        is_ad_line = (
            "top picks" in c_norm
            or "cost per click" in c_norm
            or "cpc" in c_norm
            or "ads offers" in c_norm
            or re.search(r"\bads\b", c_norm)
        ) and "growth investment" not in c_norm
        if is_ad_line:
            if not found_ads_total:
                deductions["PROMOTION"] += val_total
            continue

        is_b_fee_line = (
            (item_no is not None and 6 <= item_no <= 15)
            or "long distance" in c_norm
            or "payment collection" in c_norm
            or "pocket hero" in c_norm
            or "swiggy one" in c_norm
            or "restaurant cancellation" in c_norm
            or "call center" in c_norm
            or "delivery fee sponsored" in c_norm
            or "bolt fee" in c_norm
            or "gst on service fee" in c_norm
            or "no fees week" in c_norm
            or (re.search(r"\bcommission\b", c_norm) and "commissionable" not in c_norm)
        )
        if is_b_fee_line:
            already_in_b = found_b_fees and item_no is not None and 6 <= item_no <= 15
            already_in_b = already_in_b or (
                found_b_fees and "gst on service fee" in c_norm and (item_no is None or item_no <= 15)
            )
            if not already_in_b:
                deductions["COMMISSION"] += val_total
            continue

        is_c_line = (
            (item_no is not None and item_no in (16, 17))
            or "merchant share of cancelled" in c_norm
            or "refund for customer complaint" in c_norm
        )
        if is_c_line:
            if not found_c_complaints:
                deductions["MISC"] += val_total
            continue

        if "e other charges" in c_norm:
            deductions["MISC"] += val_total
            continue

        if "packaging material" in c_norm:
            deductions["MISC"] += val_total
            continue

    # Sale that ties to payout: Customer Paid − GST Collected
    # (= Item Total + Packaging + Discount Share). Item − GST is the working note only.
    if total_customer_paid > 0.0:
        gross_sales = round(total_customer_paid - gst_collected, 2)
        if gross_sales < 0:
            gross_sales = total_customer_paid
    elif item_total > 0.0:
        gross_sales = round(item_total - gst_collected, 2)
        if gross_sales < 0:
            gross_sales = item_total
    else:
        gross_sales = 0.0

    return gross_sales, payout, deductions


def _empty_deductions() -> Dict[str, float]:
    return {
        "COMMISSION": 0.0,
        "PROMOTION": 0.0,
        "TCS": 0.0,
        "TDS": 0.0,
        "GST_9_5": 0.0,
        "PACKING_CHARGES": 0.0,
        "MISC": 0.0,
    }


def _zomato_section_text(text: str) -> str:
    """Turn 'B. Service fees...' into 'b service fees...' so headers match."""
    return re.sub(r"^([a-i])[\.\):\-]\s+", r"\1 ", text)


def _parse_zomato_settlement(df: pd.DataFrame) -> Tuple[float, float, Dict[str, float]]:
    """
    Zomato payout mapping (client rules from payout breakup):

    A. Net order value / sales
       Total Sale = A − GST paid by Zomato under 9(5)  [same idea as Swiggy Customer Paid − GST]
       Commissionable value is the working note when A is missing
       Packaging charges → informational

    B. Service fees & payment mechanism fees → Online Platform Charges
       plus C.12 Taxes on service & payment mechanism fees

    C. Government charges
       12 Taxes on service & payment mechanism fees → Online Platform Charges
       13 Tax collected at source + TCS IGST → TCS
       14 TDS 194O → TDS Receivable
       15 GST paid by Zomato on behalf of restaurant → GST Sec 9(5) (info)

    D. Other order level deductions (16–18) → Miscellaneous
    E. Ads / dining ads / miscellaneous services → Business Promotion
    F / G. Hyperpure and other deductions → Miscellaneous
    H. Additions (cancellation refund, kitchen tip, TDS 194H, service-fee rebate) → Miscellaneous credits
    I. Net Payout / Pending amount → Payout
    """
    particular_idx, amount_idx = _swiggy_column_indexes(df)
    sno_idx = _sno_column_index(df)
    payout = 0.0
    pending_payout = 0.0
    settled_payout = 0.0
    a_total = 0.0
    commissionable = 0.0
    gst_collected = 0.0
    deductions = _empty_deductions()

    found_b_fees = False
    found_d_misc = False
    found_e_ads = False
    found_h_add = False

    for _, row in df.iterrows():
        c_norm, val_total = _swiggy_row_text_and_amount(row, particular_idx, amount_idx)
        if sno_idx is not None:
            values = list(row)
            sno_raw = values[sno_idx] if sno_idx < len(values) else ""
            sno = "" if pd.isna(sno_raw) else re.sub(r"\s+", " ", str(sno_raw).strip().lower())
            if sno and sno not in c_norm:
                c_norm = f"{sno} {c_norm}".strip()
        if not c_norm or c_norm in ("particulars", "particular", "description", "mapping rules"):
            continue
        item_no = _swiggy_item_no(c_norm)
        is_section = item_no is None
        c_norm = _zomato_section_text(c_norm)

        if is_section and (
            c_norm.startswith("settlement breakdown")
            or "total (i10" in c_norm
        ):
            continue

        if is_section and ("c government charge" in c_norm or c_norm.startswith("c government")):
            continue

        if is_section and ("b service fee" in c_norm or c_norm.startswith("b service")):
            if val_total > 0.001:
                deductions["COMMISSION"] += val_total
                found_b_fees = True
            continue

        if is_section and ("d other order level" in c_norm or c_norm.startswith("d other order")):
            if val_total > 0.001:
                deductions["MISC"] += val_total
                found_d_misc = True
            continue

        if is_section and ("e investment in growth" in c_norm or c_norm.startswith("e investment")):
            if val_total > 0.001:
                deductions["PROMOTION"] += val_total
                found_e_ads = True
            continue

        if is_section and (
            "f investment in hyperpure" in c_norm
            or c_norm.startswith("f investment")
            or c_norm.startswith("g other deduction")
        ):
            deductions["MISC"] += val_total
            continue

        if is_section and ("h total addition" in c_norm or c_norm.startswith("h total")):
            if val_total > 0.001:
                deductions["MISC"] -= val_total
                found_h_add = True
            continue

        if is_section and (
            "net order value" in c_norm
            or re.match(r"^a[\.\)]?\s+(net order|sales?|customer)\b", c_norm)
        ):
            a_total = val_total
            continue

        if "commissionable value" in c_norm:
            commissionable = val_total
            continue

        if (
            "total gst collected" in c_norm
            or ("gst collected from customer" in c_norm)
        ):
            gst_collected = val_total
            continue

        if "net payout" in c_norm:
            payout = val_total
            continue
        if "pending amount" in c_norm:
            pending_payout = val_total
            continue
        if c_norm.startswith("amount settled") or c_norm.startswith("amount settle"):
            settled_payout = val_total
            continue

        if "packaging charge" in c_norm or "packing charge" in c_norm:
            deductions["PACKING_CHARGES"] += val_total
            continue

        if (
            "gst paid by zomato" in c_norm
            or "section 9(5)" in c_norm
            or "under sec 9" in c_norm
            or "under section 9" in c_norm
        ):
            deductions["GST_9_5"] += val_total
            continue

        if "tax collected at source" in c_norm or re.search(r"\btcs igst\b", c_norm):
            deductions["TCS"] += val_total
            continue
        if re.search(r"\btcs\b", c_norm) and "gst" not in c_norm and "194" not in c_norm:
            deductions["TCS"] += val_total
            continue

        if "tds 194o" in c_norm or "tds 194 o" in c_norm:
            deductions["TDS"] += val_total
            continue
        if re.search(r"\btds\b", c_norm) and "194 h" not in c_norm and "194h" not in c_norm:
            if "addition" not in c_norm:
                deductions["TDS"] += val_total
                continue

        is_addition = (
            "cancellation refund" in c_norm
            or "tip for kitchen" in c_norm
            or "tds 194 h" in c_norm
            or "tds 194h" in c_norm
            or "service fees rebate" in c_norm
            or "service fee rebate" in c_norm
        )
        if is_addition:
            if not found_h_add:
                deductions["MISC"] -= val_total
            continue

        is_promo = (
            "total ads" in c_norm
            or "dining ads" in c_norm
            or "miscellaneous services" in c_norm
            or "miscellaneous sevices" in c_norm
        )
        if is_promo:
            if not found_e_ads:
                deductions["PROMOTION"] += val_total
            continue

        is_platform = (
            "taxes on service" in c_norm
            or "payment mechanism" in c_norm
            or "fulfilment fee" in c_norm
            or "fulfillment fee" in c_norm
            or "service fee capping" in c_norm
            or (
                "service fee" in c_norm
                and "rebate" not in c_norm
                and "restaurant-level" not in c_norm
                and "miscellaneous services" not in c_norm
                and "taxes on service" not in c_norm
            )
        )
        if is_platform:
            # B header already holds service / payment / fulfilment. Item 12 tax is in C.
            already_in_b = found_b_fees and "taxes on service" not in c_norm
            if not already_in_b:
                deductions["COMMISSION"] += val_total
            continue

        is_misc_deduction = (
            "customer compensation" in c_norm
            or "rejection penalty" in c_norm
            or "delivery charges recovery" in c_norm
            or "credit note" in c_norm
            or "debit note" in c_norm
            or "promo recovery" in c_norm
            or "brand loyalty" in c_norm
            or "express order" in c_norm
            or "amount received in cash" in c_norm
            or "adjustments from previous" in c_norm
            or "hyperpure" in c_norm
            or "extra inventory" in c_norm
            or "order level deduction" in c_norm
        )
        if is_misc_deduction:
            if not found_d_misc:
                deductions["MISC"] += val_total
            continue

    if payout == 0.0:
        payout = pending_payout or settled_payout

    gst_9_5 = deductions["GST_9_5"]
    # Sale that ties to payout: A − GST 9(5), same as Swiggy Customer Paid − GST.
    if a_total > 0.0:
        gross_sales = round(a_total - gst_9_5, 2)
        if gross_sales < 0:
            gross_sales = a_total
    elif commissionable > 0.0:
        gross_sales = commissionable
    elif gst_collected > 0.0:
        gross_sales = 0.0
    else:
        gross_sales = 0.0

    return gross_sales, payout, deductions


def process_aggregator_settlement_import(
    db: Session,
    file_bytes: bytes,
    filename: str,
    aggregator_id: int,
    branch_id: int,
    period_start_date: date,
    period_end_date: date,
    user=None
) -> Tuple[ImportBatch, SettlementBatch]:
    ext = filename.split(".")[-1].lower()
    
    if ext in ["xlsx", "xls"]:
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
        meta_branch, meta_start, meta_end = _extract_metadata_from_workbook(db, xls)
        if meta_branch:
            branch_id = meta_branch
        if meta_start:
            period_start_date = meta_start
        if meta_end:
            period_end_date = meta_end
        df = _load_best_payout_df(xls)
        if df is None or df.empty:
            df = pd.read_excel(xls, sheet_name=0)
    elif ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        # OCR Image photo
        from app.services.image_ocr_service import parse_image_to_dict
        extracted = parse_image_to_dict(file_bytes, filename)
        df = pd.DataFrame([extracted])

    aggregator = db.query(Aggregator).filter(Aggregator.id == aggregator_id).first()
    if not aggregator:
        raise ValueError("Aggregator not found")

    batch = ImportBatch(
        filename=filename,
        file_type="AGGREGATOR_SETTLEMENT",
        source_name=f"{aggregator.name} - Branch {branch_id}",
        uploaded_by_id=user.id if user else None,
        total_rows=len(df)
    )
    db.add(batch)
    db.flush()

    is_swiggy = aggregator.code.upper() == "SWIGGY" or "swiggy" in filename.lower()

    if is_swiggy:
        gross_sales, payout, deductions = _parse_swiggy_settlement(df)
        if gross_sales == 0.0 and payout == 0.0:
            raise ValueError(
                "Could not read Swiggy payout figures from this file. "
                "Use the sheet with Particulars and Total (Item Total, Customer Paid, Net Payout)."
            )
    else:
        gross_sales, payout, deductions = _parse_zomato_settlement(df)
        if gross_sales == 0.0 and payout == 0.0:
            raise ValueError(
                "Could not read Zomato payout figures from this file. "
                "Use the payout breakup sheet (Commissionable Value, Net Payout, and mapping lines)."
            )

    # Convert deductions map to list of dicts
    deductions_list = [
        {"deduction_type": k, "description": f"Imported {k}", "amount": round(v, 2)}
        for k, v in deductions.items() if abs(v) > 0.001
    ]

    batch_no = f"SETTLE-{aggregator.code}-{period_start_date.strftime('%Y%m%d')}-{period_end_date.strftime('%Y%m%d')}"

    settlement_batch = create_or_update_settlement_batch(
        db=db,
        batch_no=batch_no,
        aggregator_id=aggregator_id,
        branch_id=branch_id,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        gross_sales=round(gross_sales, 2),
        payout=round(payout, 2),
        settlement_date=period_end_date,
        deductions_data=deductions_list,
        import_batch_id=batch.id,
        user=user
    )

    batch.success_rows = len(df)
    batch.status = "COMPLETED"
    db.commit()

    return batch, settlement_batch

def delete_import_batch(db: Session, batch_id: int, user=None) -> bool:
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        return False

    # 1. Delete associated Daily Sales
    db.query(DailySale).filter(DailySale.import_batch_id == batch.id).delete()

    # 2. Delete associated Bank Transactions
    db.query(BankTransaction).filter(BankTransaction.import_batch_id == batch.id).delete()

    # 3. Delete associated Settlement Batches and Deductions
    s_batches = db.query(SettlementBatch).filter(SettlementBatch.import_batch_id == batch.id).all()
    for sb in s_batches:
        db.query(AggregatorDeduction).filter(AggregatorDeduction.settlement_batch_id == sb.id).delete()
        db.delete(sb)

    # 4. Delete Error logs
    db.query(ImportErrorLog).filter(ImportErrorLog.import_batch_id == batch.id).delete()

    # 5. Delete batch record
    filename = batch.filename
    db.delete(batch)
    db.commit()

    log_action(db, "DELETE_IMPORT_BATCH", "ImportBatch", batch_id, None, {"filename": filename}, user=user)
    return True
