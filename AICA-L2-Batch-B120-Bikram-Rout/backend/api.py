import os
import io
import uuid
import json
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from .database import get_db, log_audit
from .reconciliation import (
    calculate_brs, 
    run_auto_matching, 
    manual_match, 
    partial_match, 
    confirm_suggested_match, 
    reject_suggested_match, 
    unmatch_group, 
    rollover_period, 
    to_decimal
)
from .importers import parse_file_upload, import_master_data, compute_file_hash
from .exporters import export_brs_excel, export_brs_pdf
from .seed_data import seed_database

router = APIRouter(prefix="/api")

# Models
class ManualMatchRequest(BaseModel):
    account_id: str
    period_id: str
    ledger_ids: List[str]
    bank_ids: List[str]
    user: str = "Finance User"
    notes: Optional[str] = ""

class PartialMatchRequest(BaseModel):
    account_id: str
    period_id: str
    ledger_id: str
    bank_id: str
    allocated_amount: float
    user: str = "Finance User"
    notes: Optional[str] = ""

class ConfirmSuggestedRequest(BaseModel):
    match_group_id: str
    user: str = "Finance User"

class RejectSuggestedRequest(BaseModel):
    match_group_id: str
    user: str = "Finance User"
    reason: Optional[str] = "Suggestion rejected"

class UnmatchRequest(BaseModel):
    match_group_id: str
    user: str = "Finance User"
    reason: str = "Manual unmatch requested"

class PeriodWorkflowRequest(BaseModel):
    period_id: str
    target_status: str # Draft, In Progress, Submitted, Reviewed, Approved, Locked
    user: str
    role: str
    notes: Optional[str] = ""

class UnlockPeriodRequest(BaseModel):
    period_id: str
    user: str
    role: str
    reason: str

class RolloverPeriodRequest(BaseModel):
    account_id: str
    current_period_id: str
    next_period_name: str
    start_date: str
    end_date: str
    user: str = "Finance User"

class CategorizeRequest(BaseModel):
    transaction_id: str
    category: str
    user: str = "Finance User"

class CreateCompanyRequest(BaseModel):
    code: str
    name: str
    reporting_currency: str = "USD"
    user: str = "Administrator"

class CreateAccountRequest(BaseModel):
    company_id: str
    bank_name: str
    branch: Optional[str] = "Main"
    account_number: str
    iban: Optional[str] = ""
    currency: str = "USD"
    gl_account: str
    gl_sub_account: Optional[str] = ""
    ledger: Optional[str] = "PRIMARY_LEDGER"
    legal_entity: Optional[str] = ""
    owner: Optional[str] = "Finance Manager"
    preparer: Optional[str] = "John Reynolds"
    reviewer: Optional[str] = "Elena Vasquez"
    approver: Optional[str] = "Robert Vance"
    opening_balance: float = 0.0
    recon_start_date: Optional[str] = "2026-09-01"
    user: str = "Administrator"

# ----------------- COMPANIES & ACCOUNTS -----------------

@router.get("/companies")
def get_companies():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM companies ORDER BY name ASC")
    companies = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"companies": companies}

@router.post("/companies/create")
def create_company(req: CreateCompanyRequest):
    conn = get_db()
    cur = conn.cursor()
    cid = f"CMP-{req.code.replace(' ', '_').upper()}"
    now_iso = datetime.now().isoformat()
    try:
        cur.execute("""
            INSERT INTO companies (id, code, name, reporting_currency, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (cid, req.code.strip(), req.name.strip(), req.reporting_currency.strip().upper(), now_iso))
        log_audit(conn, req.user, "CREATE_COMPANY", "company", cid, None, req.dict(), f"Created company {req.name}")
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Failed to create company: {str(e)}")
    conn.close()
    return {"success": True, "id": cid, "code": req.code, "name": req.name}

@router.get("/accounts")
def get_accounts(company_id: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()
    if company_id:
        cur.execute("""
            SELECT a.*, c.name as company_name 
            FROM bank_accounts a 
            JOIN companies c ON a.company_id = c.id
            WHERE a.company_id = ?
            ORDER BY a.bank_name, a.account_number
        """, (company_id,))
    else:
        cur.execute("""
            SELECT a.*, c.name as company_name 
            FROM bank_accounts a 
            JOIN companies c ON a.company_id = c.id
            ORDER BY c.name, a.bank_name
        """)
    accounts = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"accounts": accounts}

@router.post("/accounts/create")
def create_account(req: CreateAccountRequest):
    conn = get_db()
    cur = conn.cursor()
    aid = f"ACC-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.now().isoformat()
    try:
        cur.execute("""
            INSERT INTO bank_accounts (id, company_id, bank_name, branch, account_number, iban, currency, gl_account, gl_sub_account, ledger, legal_entity, owner, preparer, reviewer, approver, status, opening_balance, recon_start_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?, ?)
        """, (
            aid, req.company_id, req.bank_name, req.branch, req.account_number.strip(), req.iban.strip() if req.iban else None,
            req.currency.strip().upper(), req.gl_account.strip(), req.gl_sub_account.strip() if req.gl_sub_account else None,
            req.ledger, req.legal_entity, req.owner, req.preparer, req.reviewer, req.approver,
            req.opening_balance, req.recon_start_date, now_iso
        ))
        
        # Also create initial period (e.g. 2026-09)
        pid = f"PER-{uuid.uuid4().hex[:8].upper()}"
        cur.execute("""
            INSERT INTO periods (id, account_id, period_name, start_date, end_date, status, bank_opening_balance, bank_closing_balance, ledger_opening_balance, ledger_closing_balance, residual_diff, created_at)
            VALUES (?, ?, '2026-09', '2026-09-01', '2026-09-30', 'Draft', ?, ?, ?, ?, 0.0, ?)
        """, (pid, aid, req.opening_balance, req.opening_balance, req.opening_balance, req.opening_balance, now_iso))

        log_audit(conn, req.user, "CREATE_ACCOUNT", "account", aid, None, req.dict(), f"Created bank account {req.bank_name} {req.account_number}")
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Failed to create account: {str(e)}")
    conn.close()
    return {"success": True, "id": aid, "period_id": pid}

@router.get("/periods")
def get_periods(account_id: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()
    if account_id:
        cur.execute("SELECT * FROM periods WHERE account_id = ? ORDER BY period_name DESC", (account_id,))
    else:
        cur.execute("SELECT * FROM periods ORDER BY period_name DESC")
    periods = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"periods": periods}

@router.post("/periods/rollover")
def rollover_period_endpoint(req: RolloverPeriodRequest):
    res = rollover_period(
        account_id=req.account_id,
        current_period_id=req.current_period_id,
        next_period_name=req.next_period_name,
        start_date=req.start_date,
        end_date=req.end_date,
        user=req.user
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/periods/unlock")
def unlock_period_endpoint(req: UnlockPeriodRequest):
    if req.role not in ("Administrator", "Approver"):
        raise HTTPException(status_code=403, detail="Permission Denied: Only Administrator or Approver can reopen a locked period.")
    if not req.reason or len(req.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="A mandatory, documented business reason is required to unlock a locked period.")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status FROM periods WHERE id = ?", (req.period_id,))
    p = cur.fetchone()
    if not p:
        conn.close()
        raise HTTPException(status_code=404, detail="Period not found")

    old_status = p["status"]
    cur.execute("UPDATE periods SET status = 'In Progress', locked_at = NULL, locked_by = NULL WHERE id = ?", (req.period_id,))
    log_audit(conn, req.user, "UNLOCK_PERIOD", "period", req.period_id, old_status, "In Progress", req.reason)
    conn.commit()
    conn.close()
    return {"success": True, "period_id": req.period_id, "new_status": "In Progress"}

# ----------------- DASHBOARDS -----------------

@router.get("/dashboard/summary")
def get_dashboard_summary():
    conn = get_db()
    try:
        cur = conn.cursor()

        def scalar(sql, params=()):
            cur.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row and row[0] is not None else 0

        # --- reporting period: latest period in the database -------------
        cur.execute("SELECT MAX(period_name) FROM periods")
        row = cur.fetchone()
        period_name = row[0] if row and row[0] else None
        as_of = None
        if period_name:
            cur.execute("SELECT MAX(end_date) FROM periods WHERE period_name = ?", (period_name,))
            row = cur.fetchone()
            as_of = row[0] if row and row[0] else None
        if not as_of:
            cur.execute("SELECT date('now')")
            as_of = cur.fetchone()[0]

        # --- account / period counts --------------------------------------
        total_accounts = scalar("SELECT COUNT(*) FROM bank_accounts WHERE status = 'Active'")
        active_recon_accounts = scalar("SELECT COUNT(DISTINCT account_id) FROM transactions")
        approved_periods = scalar("SELECT COUNT(*) FROM periods WHERE status IN ('Approved', 'Locked')")
        in_progress_periods = scalar("SELECT COUNT(*) FROM periods WHERE status = 'In Progress'")
        draft_periods = scalar("SELECT COUNT(*) FROM periods WHERE status = 'Draft'")

        # Accounts reconciled = latest-period periods that are Approved/Locked.
        # (A stored residual of 0 on a Draft period only means it has not been
        # calculated yet, so it must not be counted as balanced.)
        balanced_accounts = scalar(
            "SELECT COUNT(*) FROM periods WHERE period_name = ? AND status IN ('Approved', 'Locked')",
            (period_name,))
        variance_accounts = scalar(
            "SELECT COUNT(*) FROM periods WHERE period_name = ? AND status NOT IN ('Approved', 'Locked')",
            (period_name,))
        total_residual_variance = float(scalar(
            "SELECT SUM(ABS(COALESCE(residual_diff, 0))) FROM periods WHERE period_name = ?",
            (period_name,)))

        # --- transaction match statistics ---------------------------------
        cur.execute(
            "SELECT COUNT(*), SUM(ABS(signed_amount)) FROM transactions "
            "WHERE recon_status IN ('Unmatched', 'Exception', 'Suggested Match')")
        r = cur.fetchone()
        unmatched_count = int(r[0] or 0)
        unmatched_gross_exposure = float(r[1] or 0.0)

        cur.execute(
            "SELECT COUNT(*), SUM(ABS(signed_amount)) FROM transactions WHERE recon_status = 'Matched'")
        r = cur.fetchone()
        matched_count = int(r[0] or 0)
        matched_amount = float(r[1] or 0.0)

        total_tx_count = matched_count + unmatched_count
        match_rate = round(matched_count / total_tx_count * 100, 2) if total_tx_count else 0.0

        # --- balances by currency (latest period) -------------------------
        cur.execute("""
            SELECT a.currency,
                   SUM(p.ledger_closing_balance) AS total_ledger,
                   SUM(p.bank_closing_balance)   AS total_bank,
                   SUM(p.residual_diff)          AS total_residual
            FROM periods p
            JOIN bank_accounts a ON p.account_id = a.id
            WHERE p.period_name = ?
            GROUP BY a.currency
        """, (period_name,))
        currency_balances = []
        for r in cur.fetchall():
            d = dict(r)
            for k in ("total_ledger", "total_bank", "total_residual"):
                d[k] = float(d[k] or 0.0)
            currency_balances.append(d)

        # --- accounts with the largest residual differences ---------------
        cur.execute("""
            SELECT a.id AS account_id, a.id AS id, a.bank_name, a.account_number, a.currency,
                   c.name AS company_name,
                   p.id AS period_id, p.period_name,
                   p.ledger_closing_balance, p.bank_closing_balance, p.residual_diff, p.status
            FROM periods p
            JOIN bank_accounts a ON p.account_id = a.id
            LEFT JOIN companies c ON a.company_id = c.id
            WHERE ABS(COALESCE(p.residual_diff, 0)) > 0
            ORDER BY ABS(p.residual_diff) DESC
            LIMIT 5
        """)
        top_variances = [dict(r) for r in cur.fetchall()]

        # --- outstanding aging (days before the reporting period end) -----
        cur.execute("""
            SELECT
                SUM(CASE WHEN JULIANDAY(:d) - JULIANDAY(tx_date) <= 30 THEN 1 ELSE 0 END),
                SUM(CASE WHEN JULIANDAY(:d) - JULIANDAY(tx_date) BETWEEN 31 AND 60 THEN 1 ELSE 0 END),
                SUM(CASE WHEN JULIANDAY(:d) - JULIANDAY(tx_date) BETWEEN 61 AND 90 THEN 1 ELSE 0 END),
                SUM(CASE WHEN JULIANDAY(:d) - JULIANDAY(tx_date) > 90 THEN 1 ELSE 0 END)
            FROM transactions
            WHERE recon_status IN ('Unmatched', 'Exception', 'Suggested Match')
        """, {"d": as_of})
        ag = [int(x or 0) for x in cur.fetchone()]
        aging_buckets = {"0-30": ag[0], "31-60": ag[1], "61-90": ag[2], "90+": ag[3]}
        aging = {"0-30 Days": ag[0], "31-60 Days": ag[1], "61-90 Days": ag[2], "90+ Days": ag[3]}
    finally:
        conn.close()

    return {
        # ---- keys read by frontend/static/js/app.js -----------------------
        "total_accounts": total_accounts,
        "reconciled_accounts": balanced_accounts,
        "unreconciled_accounts": variance_accounts,
        "match_rate_percentage": match_rate,
        "matched_tx_count": matched_count,
        "unmatched_tx_count": unmatched_count,
        "gross_unmatched_exposure": unmatched_gross_exposure,
        "total_residual_variance": total_residual_variance,
        "pending_periods": in_progress_periods + draft_periods,
        "currency_balances": currency_balances,
        "top_variances": top_variances,
        "aging_buckets": aging_buckets,
        # ---- original keys, kept so nothing else breaks -------------------
        "total_active_accounts": total_accounts,
        "active_recon_accounts": active_recon_accounts,
        "reconciled_approved_periods": approved_periods,
        "in_progress_periods": in_progress_periods,
        "draft_periods": draft_periods,
        "unmatched_count": unmatched_count,
        "unmatched_gross_exposure": unmatched_gross_exposure,
        "matched_count": matched_count,
        "matched_amount": matched_amount,
        "match_rate": match_rate,
        "aging": aging,
        "report_period": period_name,
        "aging_as_of": as_of,
    }

# ----------------- RECONCILIATION WORKSPACE -----------------

@router.get("/reconciliation/{account_id}/{period_id}")
def get_reconciliation_workspace(account_id: str, period_id: str, status_filter: Optional[str] = None, search: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM transactions WHERE account_id = ? AND period_id = ?"
    params = [account_id, period_id]

    if status_filter and status_filter != "All":
        query += " AND recon_status = ?"
        params.append(status_filter)

    if search:
        query += " AND (description LIKE ? OR reference LIKE ? OR cheque_number LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    query += " ORDER BY tx_date ASC"
    cur.execute(query, params)
    txs = [dict(r) for r in cur.fetchall()]

    ledger_txs = [t for t in txs if t["source"] == "Oracle Ledger"]
    bank_txs = [t for t in txs if t["source"] == "Bank Statement"]

    # Compute BRS
    brs = calculate_brs(account_id, period_id)

    # Get active match groups
    cur.execute("""
        SELECT mg.*, COUNT(mgi.transaction_id) as item_count 
        FROM match_groups mg 
        JOIN match_group_items mgi ON mg.id = mgi.match_group_id
        WHERE mg.account_id = ? AND mg.period_id = ?
        GROUP BY mg.id
        ORDER BY mg.matched_at DESC
    """, (account_id, period_id))
    match_groups = [dict(r) for r in cur.fetchall()]

    conn.close()

    return {
        "ledger_transactions": ledger_txs,
        "bank_transactions": bank_txs,
        "match_groups": match_groups,
        "brs": brs
    }

@router.post("/reconciliation/auto-match")
def auto_match_endpoint(account_id: str = Query(...), period_id: str = Query(...), user: str = Query("Finance Specialist")):
    res = run_auto_matching(account_id, period_id, user=user)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/reconciliation/manual-match")
def manual_match_endpoint(req: ManualMatchRequest):
    res = manual_match(req.account_id, req.period_id, req.ledger_ids, req.bank_ids, user=req.user, notes=req.notes or "")
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/reconciliation/partial-match")
def partial_match_endpoint(req: PartialMatchRequest):
    res = partial_match(req.account_id, req.period_id, req.ledger_id, req.bank_id, req.allocated_amount, user=req.user, notes=req.notes or "")
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/reconciliation/confirm-suggested")
def confirm_suggested_endpoint(req: ConfirmSuggestedRequest):
    res = confirm_suggested_match(req.match_group_id, user=req.user)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/reconciliation/reject-suggested")
def reject_suggested_endpoint(req: RejectSuggestedRequest):
    res = reject_suggested_match(req.match_group_id, user=req.user, reason=req.reason or "")
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/reconciliation/unmatch")
def unmatch_endpoint(req: UnmatchRequest):
    res = unmatch_group(req.match_group_id, user=req.user, reason=req.reason)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@router.post("/reconciliation/categorize")
def categorize_endpoint(req: CategorizeRequest):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE transactions SET category = ? WHERE id = ?", (req.category, req.transaction_id))
    log_audit(conn, req.user, "CATEGORIZE_TRANSACTION", "transaction", req.transaction_id, None, {"category": req.category}, f"Assigned category {req.category}")
    conn.commit()
    conn.close()
    return {"success": True, "transaction_id": req.transaction_id, "category": req.category}

# ----------------- BRS STATEMENT -----------------

@router.get("/brs/{account_id}/{period_id}")
def get_brs_endpoint(account_id: str, period_id: str):
    res = calculate_brs(account_id, period_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

# ----------------- DATA VALIDATION -----------------

@router.get("/validation/{account_id}/{period_id}")
def get_validation_report(account_id: str, period_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM periods WHERE id = ? AND account_id = ?", (period_id, account_id))
    period = cur.fetchone()
    if not period:
        conn.close()
        raise HTTPException(status_code=404, detail="Period not found")

    cur.execute("SELECT * FROM transactions WHERE account_id = ? AND period_id = ?", (account_id, period_id))
    txs = [dict(r) for r in cur.fetchall()]

    checks = []

    # 1. Statement Movement Math Check
    bank_txs = [t for t in txs if t["source"] == "Bank Statement"]
    bank_open = to_decimal(period["bank_opening_balance"])
    bank_close = to_decimal(period["bank_closing_balance"])
    bank_moves = sum((to_decimal(t["signed_amount"]) for t in bank_txs), Decimal("0.00"))
    calc_bank_close = (bank_open + bank_moves).quantize(Decimal("0.01"))
    bank_math_pass = (calc_bank_close == bank_close) or len(bank_txs) == 0

    checks.append({
        "name": "Bank Statement Mathematical Integrity",
        "description": "Opening Balance + Sum of Movements = Closing Balance",
        "expected": float(bank_close),
        "calculated": float(calc_bank_close),
        "status": "PASS" if bank_math_pass else "WARNING",
        "details": f"Opening: {bank_open}, Movements: {bank_moves}, Target: {bank_close}"
    })

    # 2. Oracle Ledger Movement Math Check
    ledger_txs = [t for t in txs if t["source"] == "Oracle Ledger"]
    ledger_open = to_decimal(period["ledger_opening_balance"])
    ledger_close = to_decimal(period["ledger_closing_balance"])
    ledger_moves = sum((to_decimal(t["signed_amount"]) for t in ledger_txs), Decimal("0.00"))
    calc_ledger_close = (ledger_open + ledger_moves).quantize(Decimal("0.01"))
    ledger_math_pass = (calc_ledger_close == ledger_close) or len(ledger_txs) == 0

    checks.append({
        "name": "Oracle Ledger Mathematical Integrity",
        "description": "Ledger Opening + Sum of Signed Postings = Ledger Closing",
        "expected": float(ledger_close),
        "calculated": float(calc_ledger_close),
        "status": "PASS" if ledger_math_pass else "WARNING",
        "details": f"Opening: {ledger_open}, Postings: {ledger_moves}, Target: {ledger_close}"
    })

    # 3. Currency Isolation Check
    cur.execute("SELECT currency FROM bank_accounts WHERE id = ?", (account_id,))
    acc_ccy = cur.fetchone()["currency"]
    invalid_ccy_count = sum(1 for t in txs if t["currency"] != acc_ccy)

    checks.append({
        "name": "Currency Consistency & Isolation",
        "description": f"All transactions must match Account Currency ({acc_ccy})",
        "expected": 0,
        "calculated": invalid_ccy_count,
        "status": "PASS" if invalid_ccy_count == 0 else "FAIL",
        "details": f"Found {invalid_ccy_count} foreign currency records"
    })

    # 4. Mandatory Fields Check (Date, Amount, Description)
    missing_fields_count = sum(1 for t in txs if not t.get("tx_date") or not t.get("description") or t.get("signed_amount") is None)
    checks.append({
        "name": "Mandatory Attribute Completeness",
        "description": "Transactions must contain valid Date, Signed Amount and Description",
        "expected": 0,
        "calculated": missing_fields_count,
        "status": "PASS" if missing_fields_count == 0 else "FAIL",
        "details": f"{missing_fields_count} rows missing mandatory attributes"
    })

    # 5. Potential Duplicate Payment Review
    seen = {}
    dup_candidates = 0
    for t in txs:
        key = (t["source"], t["tx_date"], t["signed_amount"], (t["description"] or "").strip().lower())
        if key in seen:
            dup_candidates += 1
        seen[key] = True

    checks.append({
        "name": "Duplicate Transaction Screening",
        "description": "Screening identical Date/Amount/Description items for review",
        "expected": 0,
        "calculated": dup_candidates,
        "status": "INFO" if dup_candidates > 0 else "PASS",
        "details": f"Found {dup_candidates} potential repeat payments flagged for review"
    })

    conn.close()
    return {"checks": checks, "total_records": len(txs)}

# ----------------- UPLOAD CENTRE -----------------

@router.post("/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    account_id: str = Form(...),
    period_id: str = Form(...),
    source_type: str = Form(...), # 'Oracle Ledger' or 'Bank Statement'
    user: str = Form("Upload User"),
    password: Optional[str] = Form(None),
    allow_replace: Optional[bool] = Form(False)
):
    conn = get_db()
    cur = conn.cursor()

    # Check period locked status
    cur.execute("SELECT status FROM periods WHERE id = ?", (period_id,))
    p_row = cur.fetchone()
    if p_row and p_row["status"] in ("Locked", "Approved"):
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail=f"Period '{period_id}' is in '{p_row['status']}' state. File upload prohibited without authorized unlock."
        )

    contents = await file.read()
    filename = file.filename or "upload.dat"
    file_hash = compute_file_hash(contents)

    # Duplicate file detection
    cur.execute("SELECT * FROM uploaded_files WHERE file_hash = ? AND account_id = ? AND period_id = ?", (file_hash, account_id, period_id))
    existing_file = cur.fetchone()
    if existing_file and not allow_replace:
        conn.close()
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate File Detected: File '{filename}' (SHA256: {file_hash[:12]}...) has already been imported into this period. Please check or confirm overwrite."
        )

    try:
        records, meta = parse_file_upload(contents, filename, source_type, account_id, period_id, password=password)
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

    if not records:
        conn.close()
        raise HTTPException(status_code=400, detail="No valid transaction rows found in file. Supported: XLSX, XLS, CSV, MT940, OFX, CAMT.053 XML, PDF.")

    batch_id = f"UP-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.now().isoformat()

    # Get account currency
    cur.execute("SELECT currency FROM bank_accounts WHERE id = ?", (account_id,))
    acc_row = cur.fetchone()
    ccy = acc_row["currency"] if acc_row else "USD"

    # If replacing an existing batch of this source, clean old batch if allow_replace
    if existing_file and allow_replace:
        old_batch = existing_file["batch_id"]
        cur.execute("DELETE FROM transactions WHERE batch_id = ? AND recon_status = 'Unmatched'", (old_batch,))
        cur.execute("DELETE FROM uploaded_files WHERE batch_id = ?", (old_batch,))

    for r in records:
        t_id = f"TX-{uuid.uuid4().hex[:10].upper()}"
        cur.execute("""
            INSERT INTO transactions (id, account_id, period_id, source, tx_date, posting_date, value_date, description, counterparty, reference, cheque_number, payment_id, journal_id, debit, credit, signed_amount, currency, doc_name, doc_row, batch_id, validation_status, recon_status, confidence_score, is_uncertain, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Valid', 'Unmatched', ?, ?, ?)
        """, (
            t_id, account_id, period_id, r["source"], r["tx_date"], r.get("posting_date"), r.get("value_date"),
            r["description"], r.get("counterparty"), r.get("reference"), r.get("cheque_number"),
            r.get("payment_id"), r.get("journal_id"), r.get("debit", 0.0), r.get("credit", 0.0),
            r["signed_amount"], ccy, r["doc_name"], r.get("doc_row", 1), batch_id,
            r.get("confidence_score", 1.0), r.get("is_uncertain", 0), now_iso
        ))

    # Track uploaded file
    file_record_id = f"FIL-{uuid.uuid4().hex[:8].upper()}"
    cur.execute("""
        INSERT INTO uploaded_files (id, file_hash, filename, file_size, uploaded_at, uploaded_by, account_id, period_id, source_type, batch_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (file_record_id, file_hash, filename, len(contents), now_iso, user, account_id, period_id, source_type, batch_id))

    # If file contains statement closing balance, optionally update period
    if meta.get("closing_balance") is not None:
        if source_type == "Bank Statement":
            cur.execute("UPDATE periods SET bank_closing_balance = ? WHERE id = ?", (meta["closing_balance"], period_id))
        else:
            cur.execute("UPDATE periods SET ledger_closing_balance = ? WHERE id = ?", (meta["closing_balance"], period_id))

    log_audit(conn, user, "FILE_UPLOAD", "batch", batch_id, None, {
        "filename": filename,
        "file_hash": file_hash[:16],
        "source": source_type,
        "count": len(records),
        "inflows": meta["total_inflows"],
        "outflows": meta["total_outflows"]
    }, f"Uploaded {len(records)} records from {filename}")

    conn.commit()
    conn.close()

    # Re-calculate BRS
    brs = calculate_brs(account_id, period_id)

    return {
        "success": True,
        "batch_id": batch_id,
        "records_imported": len(records),
        "metadata": meta,
        "brs": brs
    }

@router.post("/master-data/import")
async def import_master_data_endpoint(
    file: UploadFile = File(...),
    master_type: str = Form(...), # 'companies' or 'accounts'
    user: str = Form("Administrator")
):
    contents = await file.read()
    filename = file.filename or "master.xlsx"
    try:
        res = import_master_data(contents, filename, master_type, user=user)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- APPROVAL WORKFLOW -----------------

@router.get("/approvals")
def get_approvals_queue():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, a.bank_name, a.account_number, a.currency, a.preparer, a.reviewer, a.approver,
               c.name as company_name
        FROM periods p
        JOIN bank_accounts a ON p.account_id = a.id
        JOIN companies c ON a.company_id = c.id
        ORDER BY p.period_name DESC, p.created_at DESC
    """)
    periods = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Enrich with BRS results
    enriched = []
    for p in periods:
        brs = calculate_brs(p["account_id"], p["id"])
        p["residual_difference"] = brs["residual_difference"]
        p["is_reconciled"] = brs["is_reconciled"]
        enriched.append(p)

    return {"queue": enriched}

@router.post("/approvals/action")
def period_workflow_action(req: PeriodWorkflowRequest):
    """
    Workflow transitions:
    Draft -> In Progress -> Submitted -> Reviewed -> Approved -> Locked
    Enforces Segregation of Duties:
    - Preparer cannot approve own account (unless admin exception)
    - Residual must be 0.00 to approve
    - Reopening locked period requires reason
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, a.preparer, a.reviewer, a.approver 
        FROM periods p
        JOIN bank_accounts a ON p.account_id = a.id
        WHERE p.id = ?
    """, (req.period_id,))
    p = cur.fetchone()
    if not p:
        conn.close()
        raise HTTPException(status_code=404, detail="Period not found")

    old_status = p["status"]
    now_iso = datetime.now().isoformat()

    # Check Segregation of Duties for 'Approved'
    if req.target_status == "Approved":
        brs = calculate_brs(p["account_id"], req.period_id)
        if not brs["is_reconciled"]:
            conn.close()
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot approve period with non-zero residual variance ({brs['residual_difference']}). All items must balance exactly!"
            )
        if req.user.lower() == (p["preparer"] or "").lower() and req.role != "Administrator":
            conn.close()
            raise HTTPException(
                status_code=403, 
                detail="Segregation of Duties Violation: Preparer cannot approve their own reconciliation!"
            )

    if req.target_status == "Locked":
        cur.execute("UPDATE periods SET status = 'Locked', locked_at = ?, locked_by = ? WHERE id = ?", (now_iso, req.user, req.period_id))
    elif req.target_status == "Approved":
        cur.execute("UPDATE periods SET status = 'Approved', approved_by = ? WHERE id = ?", (req.user, req.period_id))
    elif req.target_status == "Reviewed":
        cur.execute("UPDATE periods SET status = 'Reviewed', reviewed_by = ? WHERE id = ?", (req.user, req.period_id))
    else:
        cur.execute("UPDATE periods SET status = ? WHERE id = ?", (req.target_status, req.period_id))

    log_audit(conn, req.user, "WORKFLOW_TRANSITION", "period", req.period_id, old_status, req.target_status, req.notes or f"Status changed to {req.target_status}")
    conn.commit()
    conn.close()

    return {"success": True, "period_id": req.period_id, "previous_status": old_status, "new_status": req.target_status}

# ----------------- REPORTS & EXPORTS -----------------

@router.get("/reports/excel/{account_id}/{period_id}")
def download_excel_report(account_id: str, period_id: str):
    excel_stream = export_brs_excel(account_id, period_id)
    filename = f"BRS_Report_{account_id}_{period_id}.xlsx"
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/reports/pdf/{account_id}/{period_id}")
def download_pdf_report(account_id: str, period_id: str):
    pdf_stream = export_brs_pdf(account_id, period_id)
    filename = f"BRS_Statement_{account_id}_{period_id}.pdf"
    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ----------------- AUDIT & RULES -----------------

@router.get("/audit-logs")
def get_audit_logs(limit: int = 100):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    logs = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"logs": logs}

@router.get("/rules")
def get_rules():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rules ORDER BY priority ASC")
    rules = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"rules": rules}

@router.post("/system/reset-demo")
def reset_demo_endpoint():
    seed_database(force=True)
    return {"success": True, "message": "Demo data reset successfully with Section 15 acceptance test"}
