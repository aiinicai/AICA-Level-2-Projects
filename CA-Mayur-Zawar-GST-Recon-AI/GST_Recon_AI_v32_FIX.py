import streamlit as st
import pandas as pd
import re, sqlite3, hashlib, os
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime, date

st.set_page_config(page_title="GST-Recon AI", page_icon="📊", layout="wide")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "gst_recon_tracker.db")
STATUSES = ["Matched", "Amount / Tax Difference", "Missing in Client", "Missing in Portal"]

def canonical_status(value):
    """Return the single display/status spelling used throughout GST-Recon AI.

    Older databases/versions may contain MATCHED, MISSING IN CLIENT, etc.
    Treat those as the same status so dashboard, tracker and carry-forward
    calculations never disagree.
    """
    cleaned = clean_text(value)
    for status in STATUSES:
        if cleaned.casefold() == status.casefold():
            return status
    return cleaned

def repair_tracker_states():
    """Non-destructive repair of legacy tracker state.

    A system-matched transaction is closed automatically and must not appear
    in Open/Carry Forward merely because its accountant action is Pending.
    Genuine exceptions remain carry-forward when still Pending.
    """
    con = db()
    rows = con.execute("SELECT query_id,status,manual_action,carry_forward FROM query_master").fetchall()
    changed = 0
    for qi, status, manual, carry in rows:
        cs = canonical_status(status)
        ca = canonical_action(manual) if 'canonical_action' in globals() else (clean_text(manual) or 'Pending')
        if is_pending_action(ca):
            new_carry = 0 if cs == "Matched" else 1
        else:
            new_carry = 0
        if cs != clean_text(status) or ca != clean_text(manual) or int(carry or 0) != new_carry:
            con.execute("UPDATE query_master SET status=?,manual_action=?,carry_forward=? WHERE query_id=?",
                        (cs, ca, new_carry, qi))
            changed += 1
    if changed:
        con.commit()
    con.close()
    return changed
ACTIONS = ["Pending", "Corrected / Reconciled"]
FIN_COLS = ["Document Value", "Taxable Value", "IGST", "CGST", "SGST", "Cess"]

# ---------------- DATABASE ----------------
def db():
    con = sqlite3.connect(DB_FILE, check_same_thread=False)
    con.execute("""CREATE TABLE IF NOT EXISTS client_master (
        client_id TEXT PRIMARY KEY,
        client_name TEXT NOT NULL,
        gstin TEXT DEFAULT '',
        created_at TEXT,
        updated_at TEXT,
        is_active INTEGER DEFAULT 1,
        deactivated_at TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS query_master (
        query_id TEXT PRIMARY KEY, financial_year TEXT, first_period TEXT, last_period TEXT,
        document_type TEXT, gstin TEXT, document_number TEXT, status TEXT,
        manual_action TEXT DEFAULT 'Pending', correction_date TEXT, carry_forward INTEGER DEFAULT 1,
        first_identified TEXT, last_seen TEXT, remarks TEXT,
        client_id TEXT DEFAULT 'legacy', client_name TEXT DEFAULT 'Legacy / Existing Client',
        party_name TEXT DEFAULT '', resolution_remarks TEXT DEFAULT ''
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, query_id TEXT, period TEXT, event TEXT,
        status TEXT, manual_action TEXT, remarks TEXT, event_time TEXT,
        client_id TEXT DEFAULT 'legacy', client_name TEXT DEFAULT 'Legacy / Existing Client'
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS transaction_records (
        record_id TEXT PRIMARY KEY, query_id TEXT, financial_year TEXT, period TEXT,
        client_id TEXT, client_name TEXT, document_type TEXT, side TEXT, gstin TEXT,
        party_name TEXT, document_number TEXT, document_date TEXT, document_value REAL,
        taxable_value REAL, igst REAL, cgst REAL, sgst REAL, cess REAL,
        source_file TEXT, source_sheet TEXT, saved_at TEXT
    )""")
    # Migrate databases created by earlier versions.
    for table, col, definition in [
        ("client_master","is_active","INTEGER DEFAULT 1"),
        ("client_master","deactivated_at","TEXT DEFAULT NULL"),
        ("query_master","client_id","TEXT DEFAULT 'legacy'"),
        ("query_master","client_name","TEXT DEFAULT 'Legacy / Existing Client'"),
        ("query_master","party_name","TEXT DEFAULT ''"),
        ("query_master","resolution_remarks","TEXT DEFAULT ''"),
        ("history","client_id","TEXT DEFAULT 'legacy'"),
        ("history","client_name","TEXT DEFAULT 'Legacy / Existing Client'"),
    ]:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
    # GSTIN must be unique across active clients. Blank GSTINs are allowed during legacy migration.
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_client_master_gstin ON client_master(gstin) WHERE gstin <> ''")
    con.commit()
    return con

def get_clients(include_inactive=False):
    con = db()
    where = "" if include_inactive else "WHERE COALESCE(is_active,1)=1"
    df = pd.read_sql_query(f"SELECT * FROM client_master {where} ORDER BY client_name", con)
    con.close()
    return df

# ---------------- GSTIN VALIDATION ----------------
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")

def gstin_checksum_is_valid(gstin):
    """Validate the GSTIN format and GSTN-style checksum character."""
    gstin = normalize_gstin(gstin)
    if not GSTIN_REGEX.fullmatch(gstin):
        return False
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    total = 0
    for i, ch in enumerate(gstin[:14]):
        code = chars.index(ch)
        product = code * (1 if i % 2 == 0 else 2)
        total += product // 36 + product % 36
    check_value = (36 - (total % 36)) % 36
    return chars[check_value] == gstin[14]

def validate_gstin(gstin):
    """Return (True, message) or (False, clear user-facing error)."""
    g = normalize_gstin(gstin)
    if not g:
        return False, "GSTIN is required."
    if len(g) != 15:
        return False, f"GSTIN must contain exactly 15 characters. You entered {len(g)}."
    if not GSTIN_REGEX.fullmatch(g):
        return False, (
            "GSTIN format is incorrect. Expected: 2-digit State Code + 5-letter PAN + "
            "4-digit PAN + 1-letter PAN + 1 entity character + Z + 1 check character."
        )
    if not gstin_checksum_is_valid(g):
        return False, "GSTIN check digit is invalid. Please verify the GSTIN from the client's GST registration certificate/portal."
    return True, "GSTIN is valid."

def find_client_by_gstin(gstin, include_inactive=True):
    g = normalize_gstin(gstin)
    if not g:
        return pd.DataFrame()
    con = db()
    where = "" if include_inactive else "AND COALESCE(is_active,1)=1"
    df = pd.read_sql_query(f"SELECT * FROM client_master WHERE gstin=? {where} LIMIT 1", con, params=[g])
    con.close()
    return df

def client_exists_gstin(gstin):
    return not find_client_by_gstin(gstin, include_inactive=True).empty

def deactivate_client(client_id):
    if not client_id:
        return
    con = db(); now = datetime.now().isoformat(timespec="seconds")
    con.execute("UPDATE client_master SET is_active=0, deactivated_at=?, updated_at=? WHERE client_id=?", (now, now, client_id))
    con.commit(); con.close()

def permanently_delete_client(client_id, confirmed=False):
    """Permanently remove a client only after explicit confirmation.

    This function has its own safety gate so database deletion cannot occur merely
    because the function is called. The UI must explicitly pass confirmed=True
    after the user has completed the final confirmation step.
    """
    if not client_id:
        return False, "Client ID is required."
    if confirmed is not True:
        return False, "Permanent deletion blocked. Explicit confirmation is required."

    con = db()
    try:
        # Delete only data belonging to the selected client.
        for table in ("history", "query_master", "transaction_records"):
            con.execute(f"DELETE FROM {table} WHERE client_id=?", (client_id,))
        con.execute("DELETE FROM client_master WHERE client_id=?", (client_id,))
        con.commit()
        return True, "Client and its complete GST-Recon history have been permanently deleted."
    except Exception as e:
        con.rollback()
        return False, f"Permanent deletion failed. No changes were committed: {e}"
    finally:
        con.close()



def _period_reset_backup_path(client_id, fy, period):
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{client_id}_{fy}_{period}").strip("_")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(BASE_DIR, f"gst_recon_tracker_backup_before_reset_{safe}_{stamp}.db")


def backup_database(destination):
    """Create a safe SQLite backup before any destructive period reset."""
    src = sqlite3.connect(DB_FILE, check_same_thread=False)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()
    return destination


def _restore_query_master_after_period_reset(con, query_ids, client_id, fy):
    """Restore query_master to its last state before the deleted period.

    This is used only when the reset period is the latest saved period, so there
    are no later-period events that would need to be reconstructed.
    """
    restored = 0
    deleted = 0
    for qi in query_ids:
        prior = con.execute(
            """SELECT id,period,event,status,manual_action,remarks,event_time
               FROM history
               WHERE query_id=? AND client_id=? AND period NOT IN (SELECT ?)
               ORDER BY event_time DESC, id DESC LIMIT 1""",
            (qi, client_id, "__RESET_TARGET__")
        ).fetchone()
        # The caller has already deleted the target-period history, therefore the
        # query above simply finds the latest remaining history event.
        if not prior:
            con.execute("DELETE FROM query_master WHERE query_id=? AND client_id=?", (qi, client_id))
            deleted += 1
            continue

        _hid, last_period, _event, status, manual_action, remarks, event_time = prior
        tx = con.execute(
            """SELECT document_type,gstin,document_number,party_name
               FROM transaction_records
               WHERE query_id=? AND client_id=? AND financial_year=?
               ORDER BY period DESC, saved_at DESC, record_id DESC LIMIT 1""",
            (qi, client_id, fy)
        ).fetchone()
        existing = con.execute(
            "SELECT first_period,first_identified FROM query_master WHERE query_id=? AND client_id=?",
            (qi, client_id)
        ).fetchone()
        first_period = existing[0] if existing and existing[0] else None
        first_identified = existing[1] if existing and existing[1] else None
        min_hist = con.execute(
            "SELECT MIN(period) FROM history WHERE query_id=? AND client_id=?",
            (qi, client_id)
        ).fetchone()
        if min_hist and min_hist[0]:
            first_period = first_period or min_hist[0]
            first_identified = first_identified or min_hist[0]

        manual_action = clean_text(manual_action) or "Pending"
        carry = 0 if manual_action != "Pending" else (0 if clean_text(status) == "Matched" else 1)
        correction_date = event_time[:10] if manual_action != "Pending" and event_time else None
        party_name = clean_text(tx[3]) if tx and tx[3] else ""
        document_type = tx[0] if tx and tx[0] else None
        gstin = tx[1] if tx and tx[1] else None
        document_number = tx[2] if tx and tx[2] else None
        resolution_remarks = clean_text(remarks) if manual_action != "Pending" else ""

        con.execute("""UPDATE query_master SET
            financial_year=?, first_period=?, last_period=?, document_type=?, gstin=?,
            document_number=?, status=?, manual_action=?, correction_date=?, carry_forward=?,
            first_identified=?, last_seen=?, remarks=?, client_id=?, party_name=?,
            resolution_remarks=?
            WHERE query_id=? AND client_id=?""",
            (fy, first_period or last_period, last_period, document_type, gstin,
             document_number, status, manual_action, correction_date, carry,
             first_identified or last_period, last_period, remarks or "", client_id,
             party_name, resolution_remarks, qi, client_id))
        restored += 1
    return restored, deleted


def reset_saved_period(fy, period, client_id, client_name):
    """Delete ONLY the selected latest saved period, preserving earlier FY work.

    A database backup is created automatically before deletion. The reset removes
    the selected period's source transactions and history, then restores any query
    that existed before that period to its earlier state. Queries first created in
    the reset period are removed completely.
    """
    if not client_id or not fy or not period:
        return False, "Client, FY and period are required.", None

    con = db()
    try:
        periods = pd.read_sql_query(
            """SELECT period, MAX(saved_at) AS last_saved
               FROM transaction_records WHERE financial_year=? AND client_id=?
               GROUP BY period ORDER BY MAX(saved_at)""",
            con, params=(fy, client_id)
        )
        if periods.empty or period not in periods["period"].astype(str).tolist():
            return False, f"{period} is not a saved period for this client/FY.", None

        # Safety rule: reset only the latest SAVED PERIOD IN FY CHRONOLOGY.
        # Do NOT use saved_at or SQL text order here. Q1 (Apr-Jun) may have been
        # saved after Jul-26, but Q1 is still earlier than Jul-26.
        _saved_periods = periods.copy()
        _saved_periods["_period_order"] = _saved_periods["period"].astype(str).map(
            lambda p: period_order_key(fy, p)
        )
        _saved_periods = _saved_periods.sort_values("_period_order").reset_index(drop=True)
        latest_period = str(_saved_periods.iloc[-1]["period"])
        if str(period) != latest_period:
            return False, (
                f"Cannot reset {period} because a later FY period ({latest_period}) is already saved. "
                f"Earlier periods such as Q1/Apr-Jun can remain untouched, but {latest_period} must be reset first."
            ), None

        backup_path = _period_reset_backup_path(client_id, fy, period)
        backup_database(backup_path)

        qids_tx = [r[0] for r in con.execute(
            "SELECT DISTINCT query_id FROM transaction_records WHERE financial_year=? AND client_id=? AND period=?",
            (fy, client_id, period)
        ).fetchall() if r[0]]
        qids_hist = [r[0] for r in con.execute(
            "SELECT DISTINCT query_id FROM history WHERE client_id=? AND period=?",
            (client_id, period)
        ).fetchall() if r[0]]
        affected = sorted(set(qids_tx + qids_hist))

        # Delete only this period's source data and audit events.
        con.execute(
            "DELETE FROM transaction_records WHERE financial_year=? AND client_id=? AND period=?",
            (fy, client_id, period)
        )
        con.execute("DELETE FROM history WHERE client_id=? AND period=?", (client_id, period))

        restored, deleted = _restore_query_master_after_period_reset(con, affected, client_id, fy)
        con.commit()
        msg = (
            f"{period} reset successfully. Deleted {len(affected)} affected query record(s); "
            f"restored {restored} earlier FY query state(s) and removed {deleted} query/queries first created in {period}."
        )
        return True, msg, backup_path
    except Exception as e:
        con.rollback()
        return False, f"Period reset failed. No changes were committed: {e}", None
    finally:
        con.close()

def create_client(client_name, gstin=""):
    name = clean_text(client_name).title()
    g = normalize_gstin(gstin)
    if not name or not g:
        return ""
    existing = find_client_by_gstin(g, include_inactive=True)
    if not existing.empty:
        return ""
    cid = hashlib.sha1((name.upper()+"|"+g).encode("utf-8")).hexdigest()[:16].upper()
    con = db()
    now = datetime.now().isoformat(timespec="seconds")
    try:
        con.execute("""INSERT INTO client_master
            (client_id,client_name,gstin,created_at,updated_at,is_active) VALUES(?,?,?,?,?,1)""",
            (cid, name, g, now, now))
        con.commit()
    except sqlite3.IntegrityError:
        con.rollback(); con.close(); return ""
    con.close()
    return cid

def update_client_gstin(client_id, gstin):
    if not client_id or not gstin:
        return
    con=db(); con.execute("UPDATE client_master SET gstin=?, updated_at=? WHERE client_id=?",
                          (normalize_gstin(gstin), datetime.now().isoformat(timespec="seconds"), client_id))
    con.commit(); con.close()

def qid(row, fy, client_id="legacy"):
    raw = "|".join([
        str(fy), str(client_id), str(row.get("Document Type","")),
        str(row.get("GSTIN","")), normalize_doc_no(row.get("Document Number",""))
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16].upper()

def store_transactions(df, fy, period, client_id, client_name, document_type):
    """Persist normalized source rows for future carry-forward rechecking."""
    if df is None or df.empty:
        return
    con=db(); now=datetime.now().isoformat(timespec="seconds")
    for idx,r in df.reset_index(drop=True).iterrows():
        qi=qid({"Document Type":document_type,"GSTIN":r.get("GSTIN",""),"Document Number":r.get("Document Number","")},fy,client_id)
        side=clean_text(r.get("Side","")); rid=hashlib.sha1(f"{qi}|{side}|{period}|{idx}".encode()).hexdigest()[:24].upper()
        d=pd.to_datetime(r.get("Document Date"),errors="coerce")
        con.execute("""INSERT OR REPLACE INTO transaction_records(
            record_id,query_id,financial_year,period,client_id,client_name,document_type,side,gstin,party_name,document_number,
            document_date,document_value,taxable_value,igst,cgst,sgst,cess,source_file,source_sheet,saved_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rid,qi,fy,period,client_id,client_name,document_type,side,normalize_gstin(r.get("GSTIN","")),clean_text(r.get("Party Name","")),
             clean_text(r.get("Document Number","")),d.isoformat() if pd.notna(d) else "",float(r.get("Document Value",0) or 0),
             float(r.get("Taxable Value",0) or 0),float(r.get("IGST",0) or 0),float(r.get("CGST",0) or 0),float(r.get("SGST",0) or 0),float(r.get("Cess",0) or 0),
             str(r.get("Source File","")),str(r.get("Source Sheet","")),now))
    con.commit(); con.close()


def transaction_to_df(rec):
    if not rec: return pd.DataFrame()
    return pd.DataFrame([{"GSTIN":rec[0],"Party Name":rec[1],"Document Number":rec[2],"Match Number":normalize_doc_no(rec[2]),
        "Document Date":pd.to_datetime(rec[3],errors="coerce"),"Document Value":float(rec[4] or 0),"Taxable Value":float(rec[5] or 0),
        "IGST":float(rec[6] or 0),"CGST":float(rec[7] or 0),"SGST":float(rec[8] or 0),"Cess":float(rec[9] or 0),
        "Source File":rec[10],"Source Sheet":rec[11],"Side":rec[12]}])


def get_transaction_for_query(query_id, side=None):
    con=db(); sql="""SELECT gstin,party_name,document_number,document_date,document_value,taxable_value,igst,cgst,sgst,cess,source_file,source_sheet,side FROM transaction_records WHERE query_id=?"""; params=[query_id]
    if side: sql += " AND side=?"; params.append(side)
    sql += " ORDER BY period DESC, record_id LIMIT 1"
    rec=con.execute(sql,tuple(params)).fetchone(); con.close(); return rec


def find_current_candidate(df, stored_row, fy, client_id, document_type, tolerance):
    """Find a subsequent-period carry-forward candidate using the same GSTIN + document number.

    Automatic carry-forward resolution is intentionally stricter than normal reconciliation:
    document number must match after normalization. Financial values are then checked by
    reconcile(); a financial mismatch remains open for accountant review.
    """
    if df is None or df.empty:
        return None
    target_gstin = normalize_gstin(stored_row.get("GSTIN", ""))
    target_no = normalize_doc_no(stored_row.get("Document Number", ""))
    same = df[
        (df["GSTIN"].map(normalize_gstin) == target_gstin)
        & (df["Document Number"].map(normalize_doc_no) == target_no)
    ].copy()
    if same.empty:
        return None

    # Prefer a financially matching exact-document candidate when presentation duplicates exist.
    def financial_match(r):
        try:
            return all(abs(float(r[x]) - float(stored_row[x])) <= tolerance for x in FIN_COLS)
        except Exception:
            return False
    matched = same[same.apply(financial_match, axis=1)]
    return matched.iloc[0] if not matched.empty else same.iloc[0]


def carry_forward_recheck(fy, period, client_id, client_name, current_portal_b2b, current_client_b2b, current_portal_cdnr, current_client_cdnr, tolerance=1.0):
    """Recheck unresolved prior-period queries against the COMPLETE newly uploaded datasets.

    This deliberately ignores the selected current-period date filter. A document entered
    or reported later can retain an earlier/backdated document date and must still resolve
    the prior-period query. Exact GSTIN + normalized document number is required for
    automatic resolution; financial differences stay open for accountant review.
    """
    tracker=get_tracker(fy,client_id)
    if tracker.empty: return pd.DataFrame(),0,0
    openq=tracker[(tracker["carry_forward"].fillna(0).astype(int)==1) & tracker["manual_action"].map(is_pending_action)].copy()
    if openq.empty: return pd.DataFrame(),0,0
    pmap={"B2B Invoice":current_portal_b2b,"CDNR":current_portal_cdnr}
    cmap={"B2B Invoice":current_client_b2b,"CDNR":current_client_cdnr}
    rows=[]; resolved=0; carried=0
    for _,q in openq.iterrows():
        qi=str(q["query_id"]); dtype=str(q["document_type"]); status=canonical_status(q["status"])
        if status=="Missing in Client":
            rec=get_transaction_for_query(qi,"PORTAL")
            if not rec: continue
            old=transaction_to_df(rec)
            cand=find_current_candidate(cmap.get(dtype,pd.DataFrame()),old.iloc[0],fy,client_id,dtype,tolerance)
            if cand is not None:
                rr=reconcile(old,pd.DataFrame([cand]),dtype,tolerance,0)
                if not rr.empty:
                    rr["Query ID"]=qi
                    base=str(rr.iloc[0]["Remarks"])
                    if canonical_status(rr.iloc[0]["Status"])=="Matched":
                        rr.loc[rr.index[0],"Remarks"]=base+f"; Automatically resolved from carry-forward in {period} (later upload; document date retained as {cand.get('Document Date','')})"
                        rows.append(rr.iloc[0].to_dict()); resolved+=1; continue
                    rr.loc[rr.index[0],"Remarks"]=base+f"; Found in later client upload in {period}, but financial values differ — accountant review required"
                    rows.append(rr.iloc[0].to_dict()); carried+=1; continue
            rr=reconcile(old,pd.DataFrame(),dtype,tolerance,0)
            if not rr.empty:
                rr["Query ID"]=qi; rr.loc[rr.index[0],"Remarks"]=str(rr.iloc[0]["Remarks"])+f"; Carried forward from {q['first_period']} — still unresolved in {period}"; rows.append(rr.iloc[0].to_dict()); carried+=1
        elif status=="Missing in Portal":
            rec=get_transaction_for_query(qi,"CLIENT")
            if not rec: continue
            old=transaction_to_df(rec)
            cand=find_current_candidate(pmap.get(dtype,pd.DataFrame()),old.iloc[0],fy,client_id,dtype,tolerance)
            if cand is not None:
                rr=reconcile(pd.DataFrame([cand]),old,dtype,tolerance,0)
                if not rr.empty:
                    rr["Query ID"]=qi
                    base=str(rr.iloc[0]["Remarks"])
                    if canonical_status(rr.iloc[0]["Status"])=="Matched":
                        rr.loc[rr.index[0],"Remarks"]=base+f"; Automatically resolved from carry-forward in {period} (later portal upload; document date retained as {cand.get('Document Date','')})"
                        rows.append(rr.iloc[0].to_dict()); resolved+=1; continue
                    rr.loc[rr.index[0],"Remarks"]=base+f"; Found in later portal upload in {period}, but financial values differ — accountant review required"
                    rows.append(rr.iloc[0].to_dict()); carried+=1; continue
            rr=reconcile(pd.DataFrame(),old,dtype,tolerance,0)
            if not rr.empty:
                rr["Query ID"]=qi; rr.loc[rr.index[0],"Remarks"]=str(rr.iloc[0]["Remarks"])+f"; Carried forward from {q['first_period']} — still unresolved in {period}"; rows.append(rr.iloc[0].to_dict()); carried+=1
        else:
            carried+=1
    return pd.DataFrame(rows),resolved,carried

def get_party_name_for_query(query_id):
    """Return the best available party name stored for a query.
    This is a defensive fallback for older/newer records where query_master.party_name
    may be blank even though the uploaded transaction record contains the supplier name.
    """
    if not query_id:
        return ""
    con = db()
    row = con.execute(
        """SELECT party_name FROM transaction_records
           WHERE query_id=? AND TRIM(COALESCE(party_name,''))<>''
           ORDER BY period DESC, saved_at DESC LIMIT 1""",
        (str(query_id),)
    ).fetchone()
    con.close()
    return clean_text(row[0]) if row and row[0] else ""

def enrich_tracker_party_names(tracker):
    """Fill blank tracker party names from persisted transaction records."""
    if tracker is None or tracker.empty or "query_id" not in tracker.columns:
        return tracker
    out = tracker.copy()
    if "party_name" not in out.columns:
        out["party_name"] = ""
    for idx in out.index:
        current = clean_text(out.at[idx, "party_name"])
        if not current:
            fallback = get_party_name_for_query(str(out.at[idx, "query_id"]))
            if fallback:
                out.at[idx, "party_name"] = fallback
    return out

def save_results(df, fy, period, client_id, client_name):
    con=db(); now=datetime.now().isoformat(timespec="seconds")
    for _,r in df.iterrows():
        qi=qid(r,fy,client_id)
        remarks=str(r.get("Remarks", r.get("Difference Reason","")))
        system_status = canonical_status(r.get("Status", ""))
        party_name = clean_text(r.get("Party Name", ""))
        if not party_name:
            # Use persisted source transaction data as a reliable fallback.
            party_name = get_party_name_for_query(qi)
        old=con.execute("""SELECT manual_action, first_period, first_identified,
                                  resolution_remarks, carry_forward
                           FROM query_master WHERE query_id=?""",(qi,)).fetchone()
        if old:
            manual, firstp, firstid, resolution_remarks, old_carry = old
            manual = canonical_action(manual) or "Pending"
            # Never lose an accountant's previous resolution.
            new_carry = 0 if not is_pending_action(manual) else (0 if system_status == "Matched" else 1)
            con.execute("""UPDATE query_master SET
                last_period=?, last_seen=?, status=?, remarks=?, carry_forward=?,
                client_id=?, client_name=?, party_name=? WHERE query_id=?""",
                (period,period,system_status,remarks,new_carry,client_id,client_name,party_name,qi))
        else:
            manual="Pending"; resolution_remarks=""
            carry=0 if system_status=="Matched" else 1
            con.execute("""INSERT INTO query_master(
                query_id,financial_year,first_period,last_period,document_type,gstin,
                document_number,status,manual_action,carry_forward,first_identified,
                last_seen,remarks,client_id,client_name,party_name,resolution_remarks)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (qi,fy,period,period,r["Document Type"],r["GSTIN"],r["Document Number"],
                 system_status,manual,carry,period,period,remarks,client_id,client_name,party_name,""))
        con.execute("""INSERT INTO history(
            query_id,period,event,status,manual_action,remarks,event_time,client_id,client_name)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (qi,period,"Reconciliation",system_status,manual,remarks,now,client_id,client_name))
    con.commit(); con.close()

def get_tracker(fy, client_id=None):
    repair_tracker_states()
    con=db()
    if client_id:
        df=pd.read_sql_query("""SELECT * FROM query_master
            WHERE financial_year=? AND client_id=?
            ORDER BY carry_forward DESC, first_period, document_number""",
            con,params=(fy,client_id))
    else:
        df=pd.read_sql_query("""SELECT * FROM query_master
            WHERE financial_year=? ORDER BY carry_forward DESC, first_period, document_number""",
            con,params=(fy,))
    con.close(); return df

RESOLUTION_ACTIONS = [
    "Pending",
    "Corrected / Reconciled",
    "Not in Books – ITC Not Eligible",
    "Not in Books – Intentionally Not Claimed",
    "Accepted Difference – No Action Required",
    "Cancelled / Reversed",
    "Other – Resolved"
]

CLOSED_RESOLUTION_ACTIONS = [x for x in RESOLUTION_ACTIONS if x != "Pending"]

def is_pending_action(value):
    """Treat legacy/case-variant Pending values as the same open state.

    Older test data can contain values such as PENDING.  Those records must
    remain open/carry-forward rather than being incorrectly classified as
    closed merely because of capitalization.
    """
    return clean_text(value).casefold() == "pending"

def canonical_action(value):
    """Convert a saved/manual action to one of the standard resolution labels."""
    cleaned = clean_text(value)
    if is_pending_action(cleaned):
        return "Pending"
    for action in RESOLUTION_ACTIONS:
        if clean_text(action).casefold() == cleaned.casefold():
            return action
    return cleaned

def update_actions(ed, fy, period, client_id, client_name):
    """Save accountant decisions and preserve every change in the audit history.

    A query can be changed later: Pending -> resolved, one resolution -> another,
    or resolved -> Pending (re-open). The current decision lives in query_master;
    every change is appended to history so nothing is silently overwritten.
    """
    con=db(); now=datetime.now().isoformat(timespec="seconds")
    for _,r in ed.iterrows():
        qi=str(r.get("Query ID","")).strip(); action=canonical_action(r.get("Manual Action",""))
        resolution=str(r.get("Resolution Remarks","")).strip()
        if not qi or qi.lower()=="nan" or action not in RESOLUTION_ACTIONS:
            continue

        old_row = con.execute(
            "SELECT manual_action, status, resolution_remarks FROM query_master WHERE query_id=? AND client_id=?",
            (qi,client_id)
        ).fetchone()
        previous_action = canonical_action(old_row[0]) if old_row else "Pending"
        system_status = canonical_status(old_row[1]) if old_row else canonical_status(r.get("System Status",""))
        previous_resolution = str(old_row[2] or "") if old_row else ""

        # Standardized closure reasons. The dropdown controls the wording;
        # remarks explain the particular invoice/query.
        needs_reason = action in {
            "Accepted Difference – No Action Required",
            "Cancelled / Reversed",
            "Other – Resolved",
            "Not in Books – ITC Not Eligible",
            "Not in Books – Intentionally Not Claimed",
        }
        if action != "Pending" and needs_reason and not resolution:
            resolution = "Resolution selected by accountant; detailed note to be added in working papers."

        if action == "Pending":
            # Re-open the query. Its previous closure remains in history.
            con.execute("""UPDATE query_master SET manual_action=?, correction_date=NULL, carry_forward=1,
                resolution_remarks='', last_period=?, last_seen=? WHERE query_id=? AND client_id=?""",
                (action,period,period,qi,client_id))
            final_status=system_status
            if previous_action != "Pending":
                event=f"Accountant changed resolution: {previous_action} → Pending (Re-opened)"
            else:
                event="Accountant kept query open"
            history_note = resolution or "Query re-opened / kept pending for further review."
        else:
            con.execute("""UPDATE query_master SET manual_action=?, correction_date=?,
                carry_forward=0, resolution_remarks=?, last_period=?, last_seen=?
                WHERE query_id=? AND client_id=?""",
                (action,now[:10],resolution,period,period,qi,client_id))
            final_status="Matched"
            if previous_action != action:
                event=f"Accountant changed resolution: {previous_action} → {action}"
            else:
                event="Accountant confirmed resolution"
            history_note = resolution
            if previous_resolution and previous_resolution != resolution:
                history_note = f"Previous note: {previous_resolution} | Current note: {resolution}"

        con.execute("""INSERT INTO history(
            query_id,period,event,status,manual_action,remarks,event_time,client_id,client_name)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (qi,period,event,final_status,action,history_note,now,client_id,client_name))
    con.commit(); con.close()

# ---------------- HELPERS ----------------
def clean_text(x):
    if pd.isna(x): return ""
    return " ".join(str(x).strip().upper().split())

def norm_col(x):
    s=clean_text(x)
    for ch in ["(",")","₹","/","-",".","%",":",",","[","]"]: s=s.replace(ch," ")
    return " ".join(s.split())

def find_col(df, aliases):
    normalized={norm_col(c):c for c in df.columns}
    for a in aliases:
        if norm_col(a) in normalized: return normalized[norm_col(a)]
    for c in df.columns:
        nc=norm_col(c)
        for a in aliases:
            aa=norm_col(a)
            if len(aa)>=6 and (aa in nc or nc in aa): return c
    return None

def to_num(s):
    if s is None: return pd.Series(dtype=float)
    return pd.to_numeric(s.astype(str).str.replace(",","",regex=False).str.replace("₹","",regex=False).str.replace("(","-",regex=False).str.replace(")","",regex=False),errors="coerce").fillna(0.0)

def normalize_gstin(x): return re.sub(r"[^A-Z0-9]","",clean_text(x))
def normalize_doc_no(x):
    """Normalize document numbers for matching without changing the displayed original number.

    GST portal/client exports can contain harmless formatting differences such as spaces,
    slashes, hyphens, dots and leading zeroes (e.g. 00114 vs 114).  Leading zeroes are
    removed only when the complete normalized document number is numeric, so alphanumeric
    numbers such as A00114 are not altered.
    """
    s = re.sub(r"[\s\-/_.]", "", clean_text(x))
    if s.isdigit():
        s = s.lstrip("0") or "0"
    return s

def parse_date(s):
    """Parse normal Excel dates and Excel serial-date numbers safely."""
    if s is None:
        return pd.Series(dtype="datetime64[ns]")
    ser = pd.Series(s).copy()
    out = pd.to_datetime(ser, errors="coerce", dayfirst=True)
    # Excel serial dates are typically numeric values around 20,000–60,000.
    numeric = pd.to_numeric(ser, errors="coerce")
    mask = numeric.between(20000, 60000, inclusive="both") & out.isna()
    if mask.any():
        out.loc[mask] = pd.to_datetime(
            numeric.loc[mask], unit="D", origin="1899-12-30", errors="coerce"
        )
    # If pandas interpreted a numeric serial as nanoseconds (1970...), replace it.
    bad_numeric = numeric.between(20000, 60000, inclusive="both") & out.notna() & (out.dt.year < 2000)
    if bad_numeric.any():
        out.loc[bad_numeric] = pd.to_datetime(
            numeric.loc[bad_numeric], unit="D", origin="1899-12-30", errors="coerce"
        )
    return out

def detect_header_row(file, sheet_name, max_rows=25):
    raw = pd.read_excel(file, sheet_name=sheet_name, header=None, nrows=max_rows)
    strong = [
        "GSTIN of supplier", "Invoice number", "Note number", "Invoice Date",
        "Note date", "Taxable Value", "Invoice Value", "Note Value",
        "Integrated Tax", "Central Tax", "State/UT Tax"
    ]
    scores = []
    for i in range(len(raw)):
        vals = [norm_col(v) for v in raw.iloc[i].tolist() if not pd.isna(v)]
        text = " | ".join(vals)
        score = sum(3 for k in strong if norm_col(k) in text)
        if "INVOICE NUMBER" in text: score += 5
        if "NOTE NUMBER" in text or "NOTE REFUND VOUCHER NUMBER" in text: score += 5
        if "GSTIN OF SUPPLIER" in text: score += 4
        scores.append(score)

    best = max(range(len(scores)), key=lambda i: scores[i]) if scores else 0

    # GST portal 2B/2A Excel commonly has a grouped heading row followed by
    # the actual field-name row. If the winning row is the continuation row,
    # move back one row so read_sheet can combine both header rows.
    if best > 0:
        prev_text = " | ".join(
            [norm_col(v) for v in raw.iloc[best - 1].tolist() if not pd.isna(v)]
        )
        best_text = " | ".join(
            [norm_col(v) for v in raw.iloc[best].tolist() if not pd.isna(v)]
        )
        prev_has_gstin = "GSTIN OF SUPPLIER" in prev_text
        best_is_continuation = any(
            term in best_text
            for term in [
                "INVOICE NUMBER", "INVOICE DATE", "INVOICE VALUE",
                "NOTE NUMBER", "NOTE DATE", "NOTE VALUE",
                "INTEGRATED TAX", "CENTRAL TAX", "STATE UT TAX", "STATE/UT TAX"
            ]
        )
        if prev_has_gstin and best_is_continuation:
            best -= 1
    return best

def read_sheet(file, sheet):
    """Read a sheet and correctly handle GST portal two-row headers."""
    h = detect_header_row(file, sheet)
    raw = pd.read_excel(file, sheet_name=sheet, header=None)
    if raw.empty:
        return h, pd.DataFrame()

    # GST portal GSTR-2B exports commonly use a two-row header:
    # row 1 has grouped headings and the next row has actual field names.
    continuation_terms = [
        "invoice number", "invoice type", "invoice date", "invoice value",
        "note number", "note type", "note date", "note value",
        "integrated tax", "central tax", "state/ut tax", "cess",
        "bill of entry number", "bill of entry date", "bill of entry value"
    ]
    use_two_rows = False
    if h + 1 < len(raw):
        vals = [norm_col(v) for v in raw.iloc[h + 1].tolist() if not pd.isna(v)]
        joined = " | ".join(vals)
        hits = sum(1 for term in continuation_terms if norm_col(term) in joined)
        use_two_rows = hits >= 2

    if use_two_rows:
        top = raw.iloc[h].tolist()
        bottom = raw.iloc[h + 1].tolist()
        names = []
        for a, b in zip(top, bottom):
            if pd.notna(b) and str(b).strip():
                names.append(str(b).strip())
            elif pd.notna(a) and str(a).strip():
                names.append(str(a).strip())
            else:
                names.append("Unnamed")
        # Read actual data after both header rows.
        df = raw.iloc[h + 2:].copy()
        df.columns = names
    else:
        df = raw.iloc[h + 1:].copy()
        names = [str(c).strip() if pd.notna(c) else "Unnamed" for c in raw.iloc[h].tolist()]
        df.columns = names

    df = df.dropna(how="all").copy()
    # Make duplicate/blank headers safe for pandas lookups.
    seen = {}
    clean_cols = []
    for c in df.columns:
        c = str(c).strip() or "Unnamed"
        n = seen.get(c, 0)
        seen[c] = n + 1
        clean_cols.append(c if n == 0 else f"{c}.{n}")
    df.columns = clean_cols
    return h, df

def read_all_sheets(file):
    out=[]
    try:
        sheets = pd.ExcelFile(file).sheet_names
    except Exception as e:
        msg = str(e)
        if str(getattr(file, "name", "")).lower().endswith(".xls") and "xlrd" in msg.lower():
            msg = ("Old .XLS format requires the xlrd package. Please install it in the project venv: "
                   "pip install xlrd>=2.0.1")
        return [("(File Read Error)", None, pd.DataFrame(), msg)]
    for sheet in sheets:
        try:
            h,df=read_sheet(file,sheet); out.append((sheet,h,df,None))
        except Exception as e:
            msg = str(e)
            if str(getattr(file, "name", "")).lower().endswith(".xls") and "xlrd" in msg.lower():
                msg = ("Old .XLS format requires the xlrd package. Please install it in the project venv: "
                       "pip install xlrd>=2.0.1")
            out.append((sheet,None,pd.DataFrame(),msg))
    return out

def classify_sheet(sheet,df):
    s=clean_text(sheet); cols={norm_col(c) for c in df.columns}; txt=" | ".join(cols)
    if "CDNR" in s or "CDNRA" in s or "CDNUR" in s or "CREDIT NOTE" in s or "DEBIT NOTE" in s or "NOTE NUMBER" in txt or "NOTE REFUND VOUCHER NUMBER" in txt: return "CDNR"
    if s in {"B2B","B2BA"} or ("B2B" in s and "B2C" not in s and "B2BUR" not in s): return "B2B"
    has=lambda x:any(x in c for c in cols)
    if has("GSTIN OF SUPPLIER") and has("INVOICE NUMBER") and has("INVOICE VALUE") and has("TAXABLE VALUE"): return "B2B"
    return "OTHER"

def standardize(df, source_file, source_sheet, side, kind):
    gst = find_col(df, ["GSTIN of supplier", "GSTIN of Supplier", "GSTIN"])
    party = find_col(df, ["Trade/Legal name", "Trade/Legal Name", "Supplier Name", "Party Name", "Legal Name"])
    num = find_col(
        df,
        ["Invoice number", "Invoice Number"] if kind == "B2B"
        else ["Note number", "Note/Refund Voucher Number", "Note Voucher Number"]
    )
    dt = find_col(
        df,
        ["Invoice Date", "Invoice date"] if kind == "B2B"
        else ["Note date", "Note/Refund Voucher date", "Note Voucher Date"]
    )
    val = find_col(
        df,
        ["Invoice Value", "Invoice Value(₹)", "Invoice Value (₹)"] if kind == "B2B"
        else ["Note Value", "Note Value (₹)", "Note/Refund Voucher Value", "Note Voucher Value"]
    )
    taxable = find_col(df, ["Taxable Value", "Taxable Value (₹)"])
    ig = find_col(df, ["Integrated Tax", "Integrated Tax(₹)", "Integrated Tax Paid"])
    cg = find_col(df, ["Central Tax", "Central Tax(₹)", "Central Tax Paid"])
    sg = find_col(df, ["State/UT Tax", "State/UT Tax(₹)", "State/UT Tax Paid"])
    ce = find_col(df, ["Cess", "Cess(₹)", "Cess Paid"])
    rate = find_col(df, ["Rate", "Tax Rate", "Rate (%)", "Rate(%)"])

    if not gst or not num:
        return pd.DataFrame()

    o = pd.DataFrame(index=df.index)
    o["GSTIN"] = df[gst].map(normalize_gstin)
    o["Party Name"] = df[party].map(clean_text) if party else ""
    o["Document Number"] = df[num].map(clean_text)
    o["Match Number"] = df[num].map(normalize_doc_no)
    o["Document Date"] = parse_date(df[dt]) if dt else pd.NaT
    o["Document Value"] = to_num(df[val]) if val else 0.0
    o["Taxable Value"] = to_num(df[taxable]) if taxable else 0.0
    o["IGST"] = to_num(df[ig]) if ig else 0.0
    o["CGST"] = to_num(df[cg]) if cg else 0.0
    o["SGST"] = to_num(df[sg]) if sg else 0.0
    o["Cess"] = to_num(df[ce]) if ce else 0.0
    # Keep the portal's rate presentation internally.  In the GST 2A/department
    # Excel utility the same invoice may be printed twice: once with a tax rate
    # (e.g. 5) and once with Rate = "-".  These rows are presentation rows, not
    # two separate transactions.
    o["_Rate Presentation"] = df[rate].map(clean_text) if rate else ""
    o["Source File"] = source_file
    o["Source Sheet"] = source_sheet
    o["Side"] = side
    return o[(o.GSTIN != "") & (o["Match Number"] != "")].reset_index(drop=True)

def collapse_2a_presentation_rows(df):
    """Collapse GST 2A/department utility's two-line presentation of one document.

    The utility can show the same GSTIN + document + date + financial values twice,
    commonly with Rate=5 and Rate=-.  Such rows must reconcile as ONE transaction.
    This function collapses only that very specific presentation pattern and leaves
    genuine duplicate transactions untouched.

    A private remark column records how many source rows were collapsed so the final
    reconciliation can disclose the treatment in Remarks.
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    work = df.copy().reset_index(drop=True)
    for col in ["_Rate Presentation", "Document Date", "GSTIN", "Match Number"] + FIN_COLS:
        if col not in work.columns:
            if col == "Document Date":
                work[col] = pd.NaT
            elif col in FIN_COLS:
                work[col] = 0.0
            else:
                work[col] = ""

    # Only collapse within the same source file/sheet.  This avoids treating two
    # separately uploaded portal files containing the same transaction as a single
    # source row.
    key_cols = ["Source File", "Source Sheet", "GSTIN", "Match Number", "Document Date"] + FIN_COLS
    grouped = work.groupby(key_cols, dropna=False, sort=False)
    keep_rows = []
    collapsed_count = {}

    for key, grp in grouped:
        if len(grp) <= 1:
            for idx in grp.index:
                keep_rows.append(idx)
            continue

        rates = {clean_text(v) for v in grp["_Rate Presentation"].tolist() if clean_text(v)}
        has_dash = "-" in rates
        has_numeric_rate = any(re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", r or "") for r in rates if r != "-")

        # The known GST 2A presentation pattern is: multiple otherwise identical
        # rows, with at least one '-' rate row and at least one numeric rate row.
        if has_dash and has_numeric_rate:
            first_idx = grp.index[0]
            keep_rows.append(first_idx)
            collapsed_count[first_idx] = len(grp)
        else:
            # Same financial identity but no known 2A rate pattern: preserve rows
            # because these could be genuine duplicates.
            keep_rows.extend(list(grp.index))

    result = work.loc[keep_rows].copy().reset_index(drop=True)
    result["_2A Presentation Remark"] = ""
    if collapsed_count:
        # Map original index -> count before reset.
        original_positions = {orig: i for i, orig in enumerate(keep_rows)}
        for orig, count in collapsed_count.items():
            new_i = original_positions.get(orig)
            if new_i is not None:
                result.at[new_i, "_2A Presentation Remark"] = (
                    f"GST 2A utility presentation: {count} source rows collapsed to 1 transaction"
                )
    return result

def financial_equal(p,c,tol): return all(abs(float(p[x])-float(c[x]))<=tol for x in FIN_COLS)
def fin_fingerprint(r): return (r["GSTIN"], round(float(r["Document Value"]),2), round(float(r["Taxable Value"]),2), round(float(r["IGST"]),2), round(float(r["CGST"]),2), round(float(r["SGST"]),2), round(float(r["Cess"]),2))

def period_order_key(fy, period):
    """Return a chronological sort key for a saved FY period.

    The database may have been written at different times (for example Q1 can
    be saved after Jul while still representing Apr-Jun). Reset safety must
    follow GST/FY chronology, not the database save timestamp.
    """
    try:
        start_d, end_d = period_date_range(fy, str(period))
        if end_d is not None:
            return (pd.Timestamp(end_d), str(period))
    except Exception:
        pass
    # Fallback for an unexpected/custom period.
    return (pd.Timestamp.max, str(period))


def get_period_control_summary(fy, client_id):
    """Return processed periods and unresolved/resolved FY query counts for the Control Center."""
    if not client_id:
        return pd.DataFrame(), pd.DataFrame()
    con = db()
    periods = pd.read_sql_query(
        """SELECT period, COUNT(*) AS transaction_rows, MAX(saved_at) AS last_saved
           FROM transaction_records WHERE financial_year=? AND client_id=?
           GROUP BY period""",
        con, params=(fy, client_id)
    )
    queries = pd.read_sql_query(
        """SELECT * FROM query_master WHERE financial_year=? AND client_id=?
           ORDER BY carry_forward DESC, first_period, document_number""",
        con, params=(fy, client_id)
    )
    con.close()
    if not periods.empty:
        periods["_period_order"] = periods["period"].astype(str).map(lambda p: period_order_key(fy, p))
        periods = periods.sort_values("_period_order").drop(columns=["_period_order"]).reset_index(drop=True)
    return periods, queries

def period_sequence(fy):
    """Return the normal monthly sequence for the selected financial year."""
    y = int(str(fy).split('-')[0])
    return [f"Apr-{str(y)[-2:]}", f"May-{str(y)[-2:]}", f"Jun-{str(y)[-2:]}",
            f"Jul-{str(y)[-2:]}", f"Aug-{str(y)[-2:]}", f"Sep-{str(y)[-2:]}",
            f"Oct-{str(y)[-2:]}", f"Nov-{str(y)[-2:]}", f"Dec-{str(y)[-2:]}",
            f"Jan-{str(y+1)[-2:]}", f"Feb-{str(y+1)[-2:]}", f"Mar-{str(y+1)[-2:]}"]

def detected_date_range(*dfs):
    dates = []
    for df in dfs:
        if df is not None and not df.empty and "Document Date" in df.columns:
            d = pd.to_datetime(df["Document Date"], errors="coerce").dropna()
            if not d.empty:
                dates.append(d)
    if not dates:
        return None, None
    all_dates = pd.concat(dates, ignore_index=True)
    return all_dates.min(), all_dates.max()

def period_date_range(fy, period):
    """Return inclusive start/end dates for a selected month or quarter."""
    y1 = int(str(fy).split("-")[0])
    y2 = y1 + 1
    lookup = {
        "Apr": (y1, 4), "May": (y1, 5), "Jun": (y1, 6),
        "Jul": (y1, 7), "Aug": (y1, 8), "Sep": (y1, 9),
        "Oct": (y1, 10), "Nov": (y1, 11), "Dec": (y1, 12),
        "Jan": (y2, 1), "Feb": (y2, 2), "Mar": (y2, 3),
    }
    if str(period).upper().startswith("FULL FY"):
        return pd.Timestamp(y1, 4, 1), pd.Timestamp(y2, 3, 31)

    q = re.search(r"Q([1-4]).*?(Apr|Jul|Oct|Jan)-", period)
    if q:
        qn = int(q.group(1))
        starts = {1:(y1,4), 2:(y1,7), 3:(y1,10), 4:(y2,1)}
        ends = {1:(y1,6), 2:(y1,9), 3:(y1,12), 4:(y2,3)}
        sy, sm = starts[qn]; ey, em = ends[qn]
    else:
        m = re.search(r"(Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar)-\d{2}", period)
        if not m:
            return None, None
        sy, sm = lookup[m.group(1)]
        ey, em = sy, sm
    start_d = pd.Timestamp(sy, sm, 1)
    end_d = pd.Timestamp(ey, em, 1) + pd.offsets.MonthEnd(1)
    return start_d, end_d

def filter_to_period(df, fy, period):
    if df is None or df.empty or "Document Date" not in df.columns:
        return df
    start_d, end_d = period_date_range(fy, period)
    if start_d is None:
        return df
    dates = pd.to_datetime(df["Document Date"], errors="coerce")
    # Keep rows whose document date falls in the selected month/quarter.
    mask = dates.between(start_d, end_d, inclusive="both")
    return df.loc[mask].copy().reset_index(drop=True)

def enrich_party_names(portal, client):
    """Fill missing Party Name using the GSTIN -> name found in portal data first, then client data."""
    p = portal.copy() if portal is not None else pd.DataFrame()
    c = client.copy() if client is not None else pd.DataFrame()
    name_map = {}
    # Portal is deliberately processed first because GSTN portal B2B/CDNR contains the supplier trade/legal name.
    for source in (p, c):
        if source.empty or "GSTIN" not in source.columns or "Party Name" not in source.columns:
            continue
        for _, row in source.iterrows():
            g = normalize_gstin(row.get("GSTIN", ""))
            n = clean_text(row.get("Party Name", ""))
            if g and n and g not in name_map:
                name_map[g] = n
    for df in (p, c):
        if not df.empty and "Party Name" in df.columns:
            df["Party Name"] = df.apply(
                lambda r: clean_text(r.get("Party Name", "")) or name_map.get(normalize_gstin(r.get("GSTIN", "")), ""),
                axis=1
            )
    return p, c

def reconcile(portal,client,doc_type,tolerance=1.0,date_tolerance=0):
    p=portal.copy().reset_index(drop=True) if portal is not None else pd.DataFrame(); c=client.copy().reset_index(drop=True) if client is not None else pd.DataFrame()
    p, c = enrich_party_names(p, c)
    # Use an explicit reconciliation key and positional lookup.
    # This avoids pandas Series attribute/index edge cases during carry-forward rechecks.
    # Always create the reconciliation key column, including on empty dataframes.
    # Carry-forward rechecks intentionally call reconcile() with one side empty.
    for df in (p, c):
        if "GSTIN" not in df.columns:
            df["GSTIN"] = ""
        if "Match Number" not in df.columns:
            df["Match Number"] = ""
        df["_recon_key"] = df["GSTIN"].astype(str).map(normalize_gstin) + "|" + df["Match Number"].astype(str)
    pc=p["_recon_key"].value_counts()
    cc=c["_recon_key"].value_counts()
    used=set(); pairs=[]
    for pi,pr in p.iterrows():
        pr_key = p.at[pi, "_recon_key"]
        cand=c[(c["_recon_key"]==pr_key)&(~c.index.isin(used))]
        match_note=""
        if cand.empty:
            # secondary financial match: document number may differ
            f=fin_fingerprint(pr); alt=c[(c.GSTIN==pr.GSTIN)&(~c.index.isin(used))]
            cand=alt[alt.apply(lambda r: all(abs(float(r[x])-float(pr[x]))<=tolerance for x in FIN_COLS),axis=1)]
            if not cand.empty: match_note="Possible financial match; document number differs"
        if cand.empty: pairs.append((pr,None,"Missing in Client",match_note)); continue
        if len(cand)>1:
            pdte=pr.Document_Date if "Document_Date" in pr else pr["Document Date"]
            cand=cand.assign(_dist=(cand["Document Date"]-pdte).abs().dt.days.fillna(999999)) if pd.notna(pdte) else cand
            cand=cand.sort_values(["_dist","Document Value"] if "_dist" in cand else ["Document Value"])
        ci=cand.index[0]; used.add(ci); pairs.append((pr,c.loc[ci],"Matched Key",match_note))
    for ci,cr in c.iterrows():
        if ci not in used: pairs.append((None,cr,"Missing in Portal",""))
    rows=[]
    for pr,cr,base,note in pairs:
        pv={x:float(pr[x]) if pr is not None else 0.0 for x in FIN_COLS}; cv={x:float(cr[x]) if cr is not None else 0.0 for x in FIN_COLS}
        pdate=pr["Document Date"] if pr is not None else pd.NaT; cdate=cr["Document Date"] if cr is not None else pd.NaT
        dd=abs((pdate-cdate).days) if pd.notna(pdate) and pd.notna(cdate) else None
        reasons=[]
        if base=="Missing in Client": status="Missing in Client"; reasons.append("Not available in client data")
        elif base=="Missing in Portal": status="Missing in Portal"; reasons.append("Not available on portal")
        else:
            diffs={x:pv[x]-cv[x] for x in FIN_COLS}; finok=all(abs(v)<=tolerance for v in diffs.values())
            status="Matched" if finok else "Amount / Tax Difference"
            if not finok:
                for x,v in diffs.items():
                    if abs(v)>tolerance: reasons.append(x)
            pnum=pr["Document Number"]; cnum=cr["Document Number"]
            if normalize_doc_no(pnum)!=normalize_doc_no(cnum): reasons.append("Document No. differs")
            if dd is not None and dd>date_tolerance: reasons.append("Date differs")
            if note: reasons.append(note)
            if not reasons: reasons.append("Financial values matched")
        pr_key = str(p.at[pr.name, "_recon_key"]) if pr is not None and "_recon_key" in p.columns else ""
        cr_key = str(c.at[cr.name, "_recon_key"]) if cr is not None and "_recon_key" in c.columns else ""
        if pr is not None and pr_key and int(pc.get(pr_key, 1)) > 1: reasons.append(f"Duplicate in Portal – {int(pc.get(pr_key, 1))} entries")
        if cr is not None and cr_key and int(cc.get(cr_key, 1)) > 1: reasons.append(f"Duplicate in Client – {int(cc.get(cr_key, 1))} entries")
        if pr is not None and clean_text(pr.get("_2A Presentation Remark", "")):
            reasons.append(clean_text(pr.get("_2A Presentation Remark", "")))
        if cr is not None and clean_text(cr.get("_2A Presentation Remark", "")):
            reasons.append(clean_text(cr.get("_2A Presentation Remark", "")))
        rows.append({"Query ID":"","Document Type":doc_type,"GSTIN":pr.GSTIN if pr is not None else cr.GSTIN,"Party Name":pr["Party Name"] if pr is not None else cr["Party Name"],"Document Number":pr["Document Number"] if pr is not None else cr["Document Number"],"Portal Date":pdate,"Client Date":cdate,"Portal Invoice Value":pv["Document Value"],"Client Invoice Value":cv["Document Value"],"Portal Taxable":pv["Taxable Value"],"Client Taxable":cv["Taxable Value"],"Portal IGST":pv["IGST"],"Client IGST":cv["IGST"],"Portal CGST":pv["CGST"],"Client CGST":cv["CGST"],"Portal SGST":pv["SGST"],"Client SGST":cv["SGST"],"Portal Cess":pv["Cess"],"Client Cess":cv["Cess"],"Value Difference":pv["Document Value"]-cv["Document Value"],"Taxable Difference":pv["Taxable Value"]-cv["Taxable Value"],"Tax Difference":sum(pv[x]-cv[x] for x in ["IGST","CGST","SGST","Cess"]),"Date Difference (Days)":dd,"Remarks":"; ".join(reasons),"Portal Source":pr["Source File"] if pr is not None else "","Portal Sheet":pr["Source Sheet"] if pr is not None else "","Client Source":cr["Source File"] if cr is not None else "","Client Sheet":cr["Source Sheet"] if cr is not None else "","Status":status})
    out=pd.DataFrame(rows)
    if not out.empty: out["Query ID"]=out.apply(lambda r: qid(r,"FY"),axis=1); out["_sort"]=out.Status.map({s:i for i,s in enumerate(STATUSES)}).fillna(99); out=out.sort_values(["_sort","GSTIN","Document Number"]).drop(columns="_sort")
    return out.reset_index(drop=True)

# ---------------- EXCEL ----------------
def excel_download(dfs):
    bio=BytesIO()
    with pd.ExcelWriter(bio,engine="xlsxwriter",datetime_format="dd-mm-yyyy") as writer:
        wb=writer.book; header=wb.add_format({"bold":True,"border":1,"bg_color":"#D9EAF7","align":"center","valign":"vcenter"}); fills={"Matched":wb.add_format({"bg_color":"#C6EFCE","font_color":"#006100"}),"Amount / Tax Difference":wb.add_format({"bg_color":"#FCE4D6","font_color":"#C65911"}),"Missing in Client":wb.add_format({"bg_color":"#F4CCCC","font_color":"#990000"}),"Missing in Portal":wb.add_format({"bg_color":"#D9EAF7","font_color":"#1155CC"})}; money=wb.add_format({"num_format":'#,##0.00;[Red]-#,##0.00'}); dt=wb.add_format({"num_format":"dd-mm-yyyy"})
        for name,df in dfs.items():
            if df is None or df.empty: continue
            ex=df.copy(); sh=name[:31]; ex.to_excel(writer,sheet_name=sh,index=False); ws=writer.sheets[sh]; ws.freeze_panes(1,0); ws.autofilter(0,0,len(ex),max(0,len(ex.columns)-1)); ws.set_row(0,24,header)
            for i,col in enumerate(ex.columns):
                w=min(max(12,len(str(col))+2),34); ws.set_column(i,i,w,dt if ("Date" in str(col) and "Difference" not in str(col)) else money if any(x in str(col) for x in ["Value","Taxable","IGST","CGST","SGST","Cess","Tax Difference"]) else None)
            if "Status" in ex.columns:
                sc=ex.columns.get_loc("Status")
                for r in range(len(ex)):
                    f=fills.get(str(ex.iloc[r]["Status"]));
                    if f:
                        for j in range(len(ex.columns)): ws.write(r+1,j,"" if pd.isna(ex.iloc[r,j]) else ex.iloc[r,j],f)
    bio.seek(0); return bio

# ---------------- UI ----------------
st.title("GST-Recon AI")
st.caption("GST portal vs client purchase register — financial reconciliation + FY query tracker")

with st.sidebar:
    st.header("👤 Client")
    clients = get_clients()
    if not clients.empty:
        clients["client_label"] = clients.apply(
            lambda r: f"{r['client_name']} — {r['gstin']}" if str(r.get('gstin','')).strip() else str(r['client_name']), axis=1
        )
    client_options = ["➕ Add New Client"] + (clients["client_label"].tolist() if not clients.empty else [])
    selected_client = st.selectbox(
        "Select Client", client_options,
        help="Choose an existing client to continue its FY reconciliation history. GSTIN is shown to distinguish clients with similar names."
    )

    client_id = ""
    client_gstin = ""

    if selected_client == "➕ Add New Client":
        client_name = st.text_input("Client Name *", placeholder="Enter client / entity name")
        client_gstin = st.text_input(
            "Client GSTIN *",
            placeholder="Enter 15-character GSTIN",
            max_chars=15,
            help="GSTIN must be exactly 15 characters and must pass format and check-digit validation."
        ).upper().strip()

        if client_gstin:
            ok_gstin, gstin_msg = validate_gstin(client_gstin)
            if ok_gstin:
                duplicate = find_client_by_gstin(client_gstin, include_inactive=True)
                if duplicate.empty:
                    st.success("✅ " + gstin_msg)
                else:
                    existing_row = duplicate.iloc[0]
                    active_text = "active" if int(existing_row.get("is_active", 1) or 1) == 1 else "inactive / discontinued"
                    st.error(
                        f"🚫 Client already exists. GSTIN {normalize_gstin(client_gstin)} is already registered for "
                        f"**{existing_row['client_name']}** ({active_text}). Please select the existing client instead of adding it again."
                    )
            else:
                st.error("❌ " + gstin_msg)

        st.info("Enter both Client Name and GSTIN. Client name may repeat, but GSTIN must be unique.")
    else:
        client_name = selected_client.split(" — ")[0]
        rowc = clients[clients["client_label"] == selected_client].iloc[0]
        client_id = rowc["client_id"]
        client_gstin = normalize_gstin(rowc.get("gstin", ""))

        st.text_input("Client Name", value=client_name, disabled=True)
        entered_existing_gstin = st.text_input(
            "Client GSTIN *",
            value=client_gstin,
            max_chars=15,
            key=f"gstin_existing_{client_id}",
            help="Verify the saved 15-character GSTIN. If it is blank/incorrect, enter the correct GSTIN and save it."
        ).upper().strip()

        if entered_existing_gstin != client_gstin:
            client_gstin = entered_existing_gstin
            ok_gstin, gstin_msg = validate_gstin(client_gstin)
            if ok_gstin:
                duplicate = find_client_by_gstin(client_gstin, include_inactive=True)
                duplicate_other = duplicate[duplicate["client_id"] != client_id] if not duplicate.empty else duplicate
                if not duplicate_other.empty:
                    st.error(f"🚫 This GSTIN is already assigned to client **{duplicate_other.iloc[0]['client_name']}**. GSTIN must be unique.")
                elif st.button("💾 Update Client GSTIN", use_container_width=True):
                    update_client_gstin(client_id, client_gstin)
                    st.success("Client GSTIN updated successfully.")
                    st.rerun()
            elif client_gstin:
                st.error("❌ " + gstin_msg)
        elif client_gstin:
            ok_gstin, gstin_msg = validate_gstin(client_gstin)
            if ok_gstin:
                st.success("✅ GSTIN verified")
            else:
                st.error("❌ Saved GSTIN is invalid: " + gstin_msg)

    st.divider()
    st.header("📅 Reconciliation Period")
    fy=st.selectbox("Financial Year",["2026-27","2025-26","2027-28"])
    months=["Apr-26","May-26","Jun-26","Jul-26","Aug-26","Sep-26","Oct-26","Nov-26","Dec-26","Jan-27","Feb-27","Mar-27"]
    quarter_options=[
        "Q1 — Apr-26 to Jun-26",
        "Q2 — Jul-26 to Sep-26",
        "Q3 — Oct-26 to Dec-26",
        "Q4 — Jan-27 to Mar-27",
    ]
    full_fy_option = "FULL FY — Apr-26 to Mar-27"
    iff_client=st.checkbox("Client is IFF / Quarterly",value=False,
        help="Tick this when the client files through IFF/quarterly reporting. You can still select any individual month, a quarter, or the full financial year.")
    period_options=months + (quarter_options if iff_client else []) + [full_fy_option]
    period=st.selectbox("Reconciliation Period",period_options,
        help="For an IFF/quarterly client, select one month for a monthly check or a quarter for the complete quarter.")
    if period == full_fy_option:
        st.success(f"📊 Full Financial Year reconciliation: {period}")
    elif iff_client:
        if period in quarter_options:
            st.success(f"Quarterly mode: {period}")
        else:
            st.info(f"IFF client — monthly check: {period}")
    else:
        st.info(f"Monthly reconciliation: {period}")
    st.caption("Only unresolved queries are carried forward. Resolved queries remain closed in the FY history.")

    # ---------------- VERSION 22 — FY RECONCILIATION CONTROL CENTER ----------------
    st.divider()
    st.header("🧭 FY Reconciliation Control Center")
    st.caption("This control panel shows what has already been saved for this client/FY and what should happen next. It does not replace the reconciliation engine.")
    repair_tracker_states()
    _period_log, _query_log = get_period_control_summary(fy, client_id)
    _open_count = int(((_query_log.get("carry_forward", pd.Series(dtype=int)).fillna(0).astype(int) == 1) & _query_log.get("manual_action", pd.Series(dtype=str)).map(is_pending_action)).sum()) if not _query_log.empty else 0
    _closed_count = int(len(_query_log) - _open_count) if not _query_log.empty else 0
    _processed_count = int(len(_period_log))
    _selected_processed = bool(not _period_log.empty and _period_log["period"].astype(str).eq(str(period)).any())
    cc1, cc2, cc3, cc4 = st.columns(4)
    cc1.metric("Periods Saved", _processed_count)
    cc2.metric("Open Queries", _open_count)
    cc3.metric("Closed / Resolved", _closed_count)
    cc4.metric("Selected Period Saved", "YES" if _selected_processed else "NO")

    if _selected_processed:
        st.success(f"✅ {period} is already saved in the local database. You can review its reports/history. Re-upload only when you intentionally want to refresh/reprocess that period.")
    else:
        st.info(f"🆕 {period} is not yet saved for this client/FY. Upload the GST portal Excel file(s) and the client Excel file for {period}, confirm the detected date range, then click Start Reconciliation.")

    if _open_count:
        st.warning(f"🔁 {_open_count} unresolved FY quer{'y' if _open_count == 1 else 'ies'} will remain available for carry-forward/recheck when new-period data is uploaded.")
    else:
        st.success("🎉 No unresolved FY queries are currently pending for this client/FY.")

    with st.expander("📅 How to continue the FY — simple workflow", expanded=False):
        st.markdown(
            "**1. Finish Q1 / April / May / June → save resolutions.**\n\n"
            "**2. Change the Reconciliation Period to the next month (for example Jul-26).**\n\n"
            "**3. Upload only the new-period GST portal Excel file(s) and the client Excel file.**\n\n"
            "**4. Click Start Reconciliation.** The system uses the local database to identify unresolved FY queries and rechecks them against the newly uploaded data.\n\n"
            "**5. If an old query is found in the new data → it can be resolved. If it is still absent → it remains open for the next period.**\n\n"
            "**6. Resolved accountant decisions remain closed in FY History and are not carried forward.**"
        )

    if not _period_log.empty:
        _pc = _period_log.copy()
        _pc["Period"] = _pc["period"].astype(str)
        _pc["Transactions Saved"] = _pc["transaction_rows"].astype(int)
        _pc["Last Saved"] = _pc["last_saved"].astype(str)
        st.dataframe(_pc[["Period", "Transactions Saved", "Last Saved"]], hide_index=True, use_container_width=True)


    # ---------------- CLIENT UTILITY ----------------
    with st.expander("⚙️ Client Utility — Manage / Deactivate / Delete", expanded=False):
        st.caption("Use Deactivate for discontinued/cancelled clients. Permanent Delete removes the client's reconciliation history and transaction data from the local database.")
        all_clients = get_clients(include_inactive=True)
        if all_clients.empty:
            st.info("No clients are available for utility actions.")
        else:
            all_clients["utility_label"] = all_clients.apply(
                lambda r: f"{r['client_name']} — {r['gstin']}" + (" [INACTIVE]" if int(r.get('is_active',1) or 1)==0 else ""), axis=1
            )
            utility_label = st.selectbox("Select Client for Utility", all_clients["utility_label"].tolist(), key="utility_client")
            utility_row = all_clients[all_clients["utility_label"] == utility_label].iloc[0]
            utility_id = utility_row["client_id"]
            utility_active = int(utility_row.get("is_active",1) or 1) == 1
            u1,u2 = st.columns(2)
            with u1:
                if utility_active:
                    if st.button("⏸️ Deactivate Client", key="deactivate_client", use_container_width=True):
                        deactivate_client(utility_id)
                        st.success("Client deactivated. Its complete history is preserved and it will no longer appear in the active client list.")
                        st.rerun()
                else:
                    st.info("This client is already inactive.")
            with u2:
                if st.button("🗑️ Permanently Delete Client + History", key="delete_client", use_container_width=True):
                    st.session_state["confirm_delete_client_id"] = utility_id
                    st.session_state["confirm_delete_client_name"] = utility_row["client_name"]
            if st.session_state.get("confirm_delete_client_id") == utility_id:
                st.warning(f"⚠️ Permanent deletion will remove **{utility_row['client_name']} ({utility_row['gstin']})**, all FY queries, resolutions, transaction records and audit history from the local database. This cannot be undone.")
                delete_ack = st.checkbox(
                    f"I understand that ALL data and audit history for {utility_row['client_name']} ({utility_row['gstin']}) will be permanently deleted and cannot be recovered.",
                    key=f"confirm_delete_ack_{utility_id}"
                )
                c1,c2 = st.columns(2)
                with c1:
                    if st.button(
                        "YES — DELETE PERMANENTLY",
                        type="primary",
                        key="confirm_delete_final",
                        use_container_width=True,
                        disabled=not delete_ack
                    ):
                        deleted_ok, delete_msg = permanently_delete_client(
                            utility_id, confirmed=True
                        )
                        if deleted_ok:
                            st.session_state.pop("confirm_delete_client_id", None)
                            st.session_state.pop("confirm_delete_client_name", None)
                            st.session_state.pop(f"confirm_delete_ack_{utility_id}", None)
                            st.success(delete_msg)
                            st.rerun()
                        else:
                            st.error(delete_msg)
                with c2:
                    if st.button("Cancel", key="cancel_delete", use_container_width=True):
                        st.session_state.pop("confirm_delete_client_id", None)
                        st.session_state.pop("confirm_delete_client_name", None)
                        st.session_state.pop(f"confirm_delete_ack_{utility_id}", None)
                        st.rerun()

            # ---------------- PERIOD RESET / REPROCESS ----------------
            with st.expander("♻️ Reset / Reprocess a Saved Period", expanded=False):
                st.warning(
                    "Use this only when a saved month's Excel data was wrong and you want to "
                    "delete that month's stored transactions and re-upload corrected files. "
                    "Earlier FY periods remain untouched."
                )
                st.info(
                    "🔐 Safety rule: only the latest saved period can be reset by itself. "
                    "This prevents later-period carry-forward history from becoming inconsistent."
                )
                reset_periods_df, _reset_queries = get_period_control_summary(fy, utility_id)
                if reset_periods_df.empty:
                    st.info("No saved periods are available for this client/FY.")
                else:
                    _rp = reset_periods_df[["period", "transaction_rows", "last_saved"]].copy()
                    _rp.insert(0, "Select", False)
                    _rp.columns = ["Select", "Period", "Transactions Saved", "Last Saved"]
                    _rp_edit = st.data_editor(
                        _rp,
                        hide_index=True,
                        use_container_width=True,
                        disabled=["Period", "Transactions Saved", "Last Saved"],
                        column_config={
                            "Select": st.column_config.CheckboxColumn(
                                "☑ Select", help="Tick the saved period you want to reset.", default=False
                            ),
                            "Period": st.column_config.TextColumn("Period"),
                        },
                        key=f"period_reset_selector_{utility_id}_{fy}"
                    )
                    _selected_reset = _rp_edit[_rp_edit["Select"] == True].copy()
                    if len(_selected_reset) == 0:
                        st.caption("Tick one saved period above to prepare it for reset.")
                    elif len(_selected_reset) > 1:
                        st.error("Please select only ONE period at a time. Resetting one period at a time is safer for audit control.")
                    else:
                        _reset_period = str(_selected_reset.iloc[0]["Period"])
                        _reset_periods_ordered = reset_periods_df.copy()
                        _reset_periods_ordered["_period_order"] = _reset_periods_ordered["period"].astype(str).map(
                            lambda p: period_order_key(fy, p)
                        )
                        _reset_periods_ordered = _reset_periods_ordered.sort_values("_period_order").reset_index(drop=True)
                        _latest_reset_period = str(_reset_periods_ordered.iloc[-1]["period"])
                        if _reset_period != _latest_reset_period:
                            st.error(
                                f"❌ {_reset_period} cannot be reset alone because {_latest_reset_period} is already saved after it. "
                                "Reset the latest saved period first."
                            )
                        else:
                            st.warning(
                                f"⚠️ You are about to erase the saved **{_reset_period}** reconciliation for **{utility_row['client_name']}**. "
                                "Earlier periods will remain. A database backup will be created automatically before deletion."
                            )
                            _reset_confirm = st.checkbox(
                                f"I understand that all saved transaction data and audit events for {_reset_period} will be removed and I want to reprocess this period.",
                                key=f"reset_confirm_{utility_id}_{fy}_{_reset_period}"
                            )
                            if _reset_confirm and st.button(
                                f"♻️ RESET {utility_row['client_name']} — {_reset_period}",
                                type="primary",
                                key=f"reset_period_{utility_id}_{fy}_{_reset_period}",
                                use_container_width=True
                            ):
                                ok, msg, backup = reset_saved_period(fy, _reset_period, utility_id, utility_row["client_name"])
                                if ok:
                                    # Clear any loaded/reconciliation state for the reset period.
                                    st.session_state.pop("recon_result", None)
                                    st.session_state.pop("saved_review_key", None)
                                    st.success("✅ " + msg)
                                    if backup:
                                        st.info(f"🛡️ Automatic safety backup created: `{os.path.basename(backup)}`")
                                    st.rerun()
                                else:
                                    st.error("❌ " + msg)

# Client must be identified and have a valid GSTIN before saving tracker data.
if not client_id:
    if not client_name.strip():
        st.warning("👤 Please enter the Client Name before uploading data.")
        st.stop()
    if not client_gstin:
        st.warning("🧾 Please enter the Client GSTIN before uploading data.")
        st.stop()
    ok_gstin, gstin_msg = validate_gstin(client_gstin)
    if not ok_gstin:
        st.error("❌ " + gstin_msg)
        st.stop()
    duplicate = find_client_by_gstin(client_gstin, include_inactive=True)
    if not duplicate.empty:
        existing_row = duplicate.iloc[0]
        st.error(
            f"🚫 Client already exists. GSTIN **{normalize_gstin(client_gstin)}** is already registered for **{existing_row['client_name']}**. "
            "Please select the existing client from the Client dropdown. A GSTIN cannot be registered twice."
        )
        st.stop()
    client_id = create_client(client_name, client_gstin)
    if not client_id:
        st.error("🚫 Client could not be created because the GSTIN already exists. Please select the existing client.")
        st.stop()
    client_name = get_clients().query("client_id == @client_id").iloc[0]["client_name"]


def load_saved_period_results(fy, period, client_id, client_name):
    """Rebuild a saved period's reconciliation view from SQLite without re-uploading files.

    This is a review-only loader. It does not modify transaction_records, query_master,
    history, or the saved period. It uses the saved query status as the system finding
    and reconstructs the transaction columns from the latest persisted source records
    available up to the selected period.
    """
    con = db()
    qdf = pd.read_sql_query(
        """SELECT * FROM query_master
           WHERE financial_year=? AND client_id=? AND last_period=?
           ORDER BY document_type, gstin, document_number""",
        con, params=(fy, client_id, period)
    )
    if qdf.empty:
        con.close()
        return pd.DataFrame()

    qdf["status"] = qdf["status"].map(canonical_status)
    qdf["manual_action"] = qdf["manual_action"].map(canonical_action)
    rows = []
    for _, q in qdf.iterrows():
        qi = str(q.get("query_id", ""))
        # Latest saved source record for each side up to the selected period.
        side_rows = {}
        for side in ("PORTAL", "CLIENT"):
            rec = con.execute(
                """SELECT gstin,party_name,document_number,document_date,document_value,
                          taxable_value,igst,cgst,sgst,cess,source_file,source_sheet,side
                   FROM transaction_records
                   WHERE query_id=? AND client_id=? AND side=?
                     AND financial_year=?
                     AND period IN (SELECT period FROM transaction_records
                                    WHERE query_id=? AND client_id=? AND financial_year=?)
                   ORDER BY period DESC, saved_at DESC, record_id DESC LIMIT 1""",
                (qi, client_id, side, fy, qi, client_id, fy)
            ).fetchone()
            side_rows[side] = rec

        pr = side_rows["PORTAL"]
        cr = side_rows["CLIENT"]
        # Prefer the source-side record associated with the query; for carried queries,
        # that may legitimately be from an earlier period.
        base = pr or cr
        if not base:
            continue

        def vals(rec):
            return {
                "GSTIN": clean_text(rec[0]) if rec else clean_text(q.get("gstin", "")),
                "Party Name": clean_text(rec[1]) if rec else clean_text(q.get("party_name", "")),
                "Document Number": clean_text(rec[2]) if rec else clean_text(q.get("document_number", "")),
                "Document Date": pd.to_datetime(rec[3], errors="coerce") if rec else pd.NaT,
                "Document Value": float(rec[4] or 0) if rec else 0.0,
                "Taxable Value": float(rec[5] or 0) if rec else 0.0,
                "IGST": float(rec[6] or 0) if rec else 0.0,
                "CGST": float(rec[7] or 0) if rec else 0.0,
                "SGST": float(rec[8] or 0) if rec else 0.0,
                "Cess": float(rec[9] or 0) if rec else 0.0,
                "Source File": clean_text(rec[10]) if rec else "",
                "Source Sheet": clean_text(rec[11]) if rec else "",
            }
        p = vals(pr) if pr else vals(None)
        c = vals(cr) if cr else vals(None)
        party = clean_text(q.get("party_name", "")) or p["Party Name"] or c["Party Name"] or get_party_name_for_query(qi) or "Not available in source data"
        status = clean_text(q.get("status", ""))
        manual = canonical_action(q.get("manual_action", "Pending")) or "Pending"
        final_status = "Matched" if not is_pending_action(manual) else status
        pdate, cdate = p["Document Date"], c["Document Date"]
        dd = abs((pdate-cdate).days) if pd.notna(pdate) and pd.notna(cdate) else None
        pv, cv = p["Document Value"], c["Document Value"]
        pt, ct = p["Taxable Value"], c["Taxable Value"]
        tax_p = sum(p[x] for x in ["IGST","CGST","SGST","Cess"])
        tax_c = sum(c[x] for x in ["IGST","CGST","SGST","Cess"])
        rows.append({
            "Query ID": qi,
            "Document Type": clean_text(q.get("document_type", "")),
            "GSTIN": clean_text(q.get("gstin", "")) or p["GSTIN"] or c["GSTIN"],
            "Party Name": party,
            "Document Number": clean_text(q.get("document_number", "")) or p["Document Number"] or c["Document Number"],
            "Portal Date": pdate,
            "Client Date": cdate,
            "Portal Invoice Value": pv,
            "Client Invoice Value": cv,
            "Portal Taxable": pt,
            "Client Taxable": ct,
            "Portal IGST": p["IGST"], "Client IGST": c["IGST"],
            "Portal CGST": p["CGST"], "Client CGST": c["CGST"],
            "Portal SGST": p["SGST"], "Client SGST": c["SGST"],
            "Portal Cess": p["Cess"], "Client Cess": c["Cess"],
            "Value Difference": pv-cv,
            "Taxable Difference": pt-ct,
            "Tax Difference": tax_p-tax_c,
            "Date Difference (Days)": dd,
            "Remarks": clean_text(q.get("remarks", "")),
            "Portal Source": p["Source File"], "Portal Sheet": p["Source Sheet"],
            "Client Source": c["Source File"], "Client Sheet": c["Source Sheet"],
            "Status": final_status,
        })
    con.close()
    return pd.DataFrame(rows)

st.info(
    f"📌 **Before uploading:** Please select the correct **Client, Financial Year and Reconciliation Period**. "
    "After upload, GST-Recon AI will show the detected date range and require you to confirm the selected period before reconciliation."
)

st.header("🟢 Step 1 — GST Portal Data")
portal_files=st.file_uploader("Upload one or more GST Portal Excel files (B2B, CDNR, etc.)",type=["xlsx","xls"],accept_multiple_files=True,key="portal_v9")
st.header("🔵 Step 2 — Client Data")
client_file=st.file_uploader("Upload ONE Client Excel file",type=["xlsx","xls"],accept_multiple_files=False,key="client_v9")

# ---------------- SAVED PERIOD REVIEW ----------------
# A saved period must remain reviewable after Streamlit restarts. No upload is
# required merely to review July/Q1 work already stored in SQLite.
_saved_review_key = f"{client_id}|{fy}|{period}"
if st.session_state.get("saved_review_key") != _saved_review_key:
    st.session_state.pop("recon_result", None)
    st.session_state.pop("saved_review_key", None)

_period_log_now, _ = get_period_control_summary(fy, client_id)
_saved_now = bool(not _period_log_now.empty and _period_log_now["period"].astype(str).eq(str(period)).any())
if not portal_files or not client_file:
    if _saved_now:
        st.success(f"📂 **{period} is already saved.** You can review the saved reconciliation and accountant queries without uploading the Excel files again.")
        if st.button(f"📂 Load Saved {period} for Accountant Review", type="primary", use_container_width=True):
            _loaded = load_saved_period_results(fy, period, client_id, client_name)
            if _loaded.empty:
                st.error(f"No saved transaction details could be reconstructed for {period}.")
                st.stop()
            st.session_state["recon_result"] = _loaded
            st.session_state["saved_review_key"] = _saved_review_key
            st.session_state["carry_resolved"] = 0
            st.session_state["carry_open"] = 0
            st.success(f"✅ Saved {period} data loaded. No database records were changed.")
            st.rerun()
        if st.session_state.get("saved_review_key") != _saved_review_key:
            st.info("Click **Load Saved Period for Accountant Review** to open the saved reconciliation results.")
            st.stop()
    else:
        st.info("Upload portal file(s) and one client Excel file to start reconciliation."); st.stop()

# File/sheet detection lists are also used by the Professional Report Center.
# Initialize them even in saved-period review mode, where no files are uploaded.
pinv = []
cinv = []

# If the user loaded a previously saved period for review, do NOT try to
# read/upload files again.  The saved result in session_state is the source for
# the accountant review screen.
_saved_review_active = (
    st.session_state.get("saved_review_key") == _saved_review_key
    and "recon_result" in st.session_state
)

if not _saved_review_active:
    portal_b2b=[]; portal_cdnr=[]; pinv=[]
    for f in portal_files:
        for sh,h,df,e in read_all_sheets(f):
            kind="READ ERROR" if e else classify_sheet(sh,df); pinv.append({"File":f.name,"Sheet":sh,"Detected Type":kind,"Header Row":"" if h is None else h+1,"Rows":len(df),"Status":e or "OK"})
            if kind=="B2B":
                x=standardize(df,f.name,sh,"Portal","B2B");
                if not x.empty: portal_b2b.append(x)
            elif kind=="CDNR":
                x=standardize(df,f.name,sh,"Portal","CDNR");
                if not x.empty: portal_cdnr.append(x)
    client_b2b=[]; client_cdnr=[]; cinv=[]
    for sh,h,df,e in read_all_sheets(client_file):
        kind="READ ERROR" if e else classify_sheet(sh,df); cinv.append({"File":client_file.name,"Sheet":sh,"Detected Type":kind,"Header Row":"" if h is None else h+1,"Rows":len(df),"Status":e or "OK"})
        if kind=="B2B":
            x=standardize(df,client_file.name,sh,"Client","B2B");
            if not x.empty: client_b2b.append(x)
        elif kind=="CDNR":
            x=standardize(df,client_file.name,sh,"Client","CDNR");
            if not x.empty: client_cdnr.append(x)
    pb=pd.concat(portal_b2b,ignore_index=True) if portal_b2b else pd.DataFrame(); pc=pd.concat(portal_cdnr,ignore_index=True) if portal_cdnr else pd.DataFrame(); cb=pd.concat(client_b2b,ignore_index=True) if client_b2b else pd.DataFrame(); cc=pd.concat(client_cdnr,ignore_index=True) if client_cdnr else pd.DataFrame()

    # IMPORTANT: A quarterly/IFF file can contain the full quarter. Apply the user's
    # selected month/quarter to the actual document date before reconciliation.
    pb_all, pc_all, cb_all, cc_all = pb.copy(), pc.copy(), cb.copy(), cc.copy()
    pb = filter_to_period(pb, fy, period)
    pc = filter_to_period(pc, fy, period)
    cb = filter_to_period(cb, fy, period)
    cc = filter_to_period(cc, fy, period)

    # IMPORTANT: GST 2A department Excel utility may print each invoice twice
    # (e.g. Rate=5 and Rate=-). Collapse only that known presentation pattern before
    # reconciliation so one invoice is treated as one transaction.
    pb = collapse_2a_presentation_rows(pb)
    pc = collapse_2a_presentation_rows(pc)
    cb = collapse_2a_presentation_rows(cb)
    cc = collapse_2a_presentation_rows(cc)

    st.subheader("🔎 Automatic File / Sheet Detection"); st.dataframe(pd.DataFrame(pinv+cinv),hide_index=True,use_container_width=True)
    a,b,c,d=st.columns(4); a.metric("Portal B2B Transactions (Selected Period)",len(pb)); b.metric("Portal CDNR Transactions (Selected Period)",len(pc)); c.metric("Client B2B Transactions (Selected Period)",len(cb)); d.metric("Client CDNR Transactions (Selected Period)",len(cc))
    st.divider()
    det_min, det_max = detected_date_range(pb_all, pc_all, cb_all, cc_all)
    if det_min is not None:
        st.info(
            f"📅 **Uploaded data date range detected:** "
            f"{det_min.strftime('%d-%m-%Y')} to {det_max.strftime('%d-%m-%Y')}."
        )

    sel_start, sel_end = period_date_range(fy, period)
    selected_rows_total = len(pb) + len(pc) + len(cb) + len(cc)
    if selected_rows_total == 0:
        st.error(
            f"❌ No transactions were found in the uploaded files for **{period}**. "
            "Please check the Financial Year and Reconciliation Period before proceeding."
        )

    st.warning(
        f"⚠️ **Please confirm the reconciliation period before continuing.** "
        f"You have selected **{period}** for Financial Year **{fy}**. "
        "Kindly verify that this month/quarter is correct for the uploaded GST portal and client data."
    )
    period_confirm = st.checkbox(
        f"✅ I have checked and confirmed the period: {period}",
        key=f"period_confirm_{fy}_{period}"
    )

    st.divider(); st.subheader("⚙️ Reconciliation Settings"); s1,s2=st.columns(2); tolerance=s1.number_input("Amount / Tax tolerance (₹)",0.0,1000.0,1.0,0.50); date_tolerance=s2.number_input("Date tolerance for remarks (days)",0,30,0,1)
    run=st.button("🚀 Start Reconciliation",type="primary",use_container_width=True,disabled=(not period_confirm or selected_rows_total == 0))
    if run:
        if selected_rows_total == 0:
            st.error("No transactions are available for the selected period. Please correct the period selection and upload the appropriate files.")
            st.stop()
        # Permanently save normalized source transactions for future carry-forward.
        store_transactions(pb,fy,period,client_id,client_name,"B2B Invoice")
        store_transactions(cb,fy,period,client_id,client_name,"B2B Invoice")
        store_transactions(pc,fy,period,client_id,client_name,"CDNR")
        store_transactions(cc,fy,period,client_id,client_name,"CDNR")

        r1=reconcile(pb,cb,"B2B Invoice",tolerance,date_tolerance); r2=reconcile(pc,cc,"CDNR",tolerance,date_tolerance); combined=pd.concat([x for x in [r1,r2] if not x.empty],ignore_index=True) if (not r1.empty or not r2.empty) else pd.DataFrame()
        if not combined.empty: combined["Query ID"]=combined.apply(lambda r:qid(r,fy,client_id),axis=1)

        # Automatically recheck unresolved queries from earlier periods.
        carry_df,carry_resolved,carry_open=carry_forward_recheck(
            fy,period,client_id,client_name,
            collapse_2a_presentation_rows(pb_all),
            collapse_2a_presentation_rows(cb_all),
            collapse_2a_presentation_rows(pc_all),
            collapse_2a_presentation_rows(cc_all),
            tolerance
        )
        if not carry_df.empty:
            current_ids=set(combined["Query ID"].astype(str)) if not combined.empty else set()
            carry_df=carry_df[~carry_df["Query ID"].astype(str).isin(current_ids)].copy()
            if not carry_df.empty: combined=pd.concat([combined,carry_df],ignore_index=True) if not combined.empty else carry_df
        if not combined.empty: save_results(combined,fy,period,client_id,client_name)
        st.session_state["carry_resolved"]=carry_resolved
        st.session_state["carry_open"]=carry_open
        st.session_state["recon_result"]=combined
        # IMPORTANT: after a fresh reconciliation, immediately mark this period
        # as an active saved-review session.  This prevents Streamlit reruns caused
        # by accountant Save/Re-open actions from falling back to the upload screen.
        st.session_state["saved_review_key"] = _saved_review_key

if "recon_result" not in st.session_state: st.warning("Click Start Reconciliation to generate analysis."); st.stop()
combined=st.session_state["recon_result"]
if combined.empty: st.error("No B2B or CDNR transactions detected."); st.stop()

st.divider(); st.header("📊 Reconciliation Dashboard"); combined["Status"] = combined["Status"].map(canonical_status); counts=combined.Status.value_counts(); total=len(combined); matched=int(counts.get("Matched",0)); diff=int(counts.get("Amount / Tax Difference",0)); mc=int(counts.get("Missing in Client",0)); mp=int(counts.get("Missing in Portal",0));
cols=st.columns(4); cols[0].metric("Total Transactions",total); cols[1].metric("Matched",matched); cols[2].metric("Amount / Tax Differences",diff); cols[3].metric("Missing",mc+mp)
summary=pd.DataFrame([{"Status":s,"Count":int(counts.get(s,0))} for s in STATUSES]); st.dataframe(summary,hide_index=True,use_container_width=True)
doc_summary=combined.groupby(["Document Type","Status"]).size().reset_index(name="Count"); st.subheader("Document Type Summary"); st.dataframe(doc_summary,hide_index=True,use_container_width=True)

st.subheader("🔍 Reconciliation Results"); f1,f2=st.columns(2); sf=f1.multiselect("Filter Status",STATUSES,STATUSES); dfilt=f2.multiselect("Filter Document Type",sorted(combined["Document Type"].unique()),sorted(combined["Document Type"].unique())); display=combined[combined.Status.isin(sf)&combined["Document Type"].isin(dfilt)].copy(); st.dataframe(display,hide_index=True,use_container_width=True)

# Tracker
st.divider(); st.header(f"📌 FY Query Tracker — {client_name}")
tracker=enrich_tracker_party_names(get_tracker(fy, client_id))
if tracker.empty:
    st.info("No saved FY queries for this client and financial year yet.")
else:
    openq=tracker[(tracker["carry_forward"].fillna(0).astype(int)==1) & tracker.manual_action.map(is_pending_action)].copy()
    closed=tracker[~((tracker["carry_forward"].fillna(0).astype(int)==1) & tracker.manual_action.map(is_pending_action))].copy()
    t1,t2,t3=st.columns(3)
    t1.metric("Open / Carry Forward",len(openq))
    t2.metric("Closed / Resolved",len(closed))
    t3.metric("FY Total Queries",len(tracker))

    # ---------------- ACCOUNTANT RESOLUTION WORKBENCH ----------------
    with st.expander("ℹ️ Accountant Resolution Guide", expanded=False):
        st.markdown("""
**Pending – Carry Forward:** keep the query open for the next period.  

**Corrected / Reconciled:** books have been corrected and the query is closed.  

**Not in Books – ITC Not Eligible:** portal credit reviewed and intentionally not recorded/claimed because ITC is not eligible.  

**Not in Books – Intentionally Not Claimed:** entry exists/was considered but ITC is deliberately not claimed.  

**Accepted Difference – No Action Required:** difference reviewed and accepted.  

**Cancelled / Reversed:** transaction was cancelled/reversed.  

**Other – Resolved:** another documented reason has resolved the query.

The dropdown provides fixed wording so different accountants cannot enter different spellings. **Resolution Remarks** should contain the invoice-specific explanation. Every change is preserved in the audit history.
""")

    if not openq.empty:
        st.subheader("📝 Open Queries — Accountant Resolution")
        st.caption(
            "Each open query has its own standard dropdown and individual Save button. "
            "You can also review all queries first and use the common Save All button at the bottom."
        )

        # Row-by-row resolution UI.  Text areas are used so the complete resolution
        # remark is visible and editable.  Each row also keeps its own Save button.
        open_query_meta = []

        for row_no, (_, r) in enumerate(openq.iterrows(), start=1):
            qi = str(r.get("query_id", "")).strip()
            if not qi or qi.lower() == "nan":
                continue

            st.markdown(f"**Query {row_no}** — `{qi}`")

            # Query identification/details
            c1, c2, c3, c4 = st.columns([1.25, 2.7, 1.35, 1.45])
            c1.markdown(f"**GSTIN**\n\n{r.get('gstin','')}")
            c2.markdown(f"**Party Name**\n\n{r.get('party_name','')}")
            c3.markdown(f"**Document No.**\n\n{r.get('document_number','')}")
            c4.markdown(f"**System Status**\n\n{r.get('status','')}")

            current_action = canonical_action(r.get("manual_action", "Pending")) or "Pending"
            if current_action not in RESOLUTION_ACTIONS:
                current_action = "Pending"

            selected_action = st.selectbox(
                "Accountant Resolution",
                RESOLUTION_ACTIONS,
                index=RESOLUTION_ACTIONS.index(current_action),
                key=f"open_action_{client_id}_{fy}_{period}_{qi}",
                help="Choose one standard resolution. Do not type your own wording here."
            )

            old_note = "" if current_action == "Pending" else str(r.get("resolution_remarks", "") or "")
            resolution_note = st.text_area(
                "Resolution Remarks",
                value=old_note,
                key=f"open_note_{client_id}_{fy}_{period}_{qi}",
                placeholder="Enter a short invoice-specific reason / explanation...",
                height=75,
                help="Optional for Pending. Recommended for every closed/resolved query."
            )

            # Individual save button
            save_col, detail_col = st.columns([1.2, 5.8])
            if save_col.button(
                "💾 Save",
                type="primary",
                key=f"save_one_open_{client_id}_{fy}_{period}_{qi}"
            ):
                one = pd.DataFrame([{
                    "Query ID": qi,
                    "System Status": str(r.get("status", "")),
                    "Manual Action": selected_action,
                    "Resolution Remarks": resolution_note,
                }])
                update_actions(one, fy, period, client_id, client_name)
                # Rebuild the displayed review from SQLite before rerunning.
                # This keeps the accountant workbench alive and shows the updated
                # open/closed state instead of returning to the upload/reconciliation screen.
                refreshed = load_saved_period_results(fy, period, client_id, client_name)
                if not refreshed.empty:
                    st.session_state["recon_result"] = refreshed
                st.session_state["saved_review_key"] = _saved_review_key
                st.success(f"Saved: {r.get('document_number','')} — {selected_action}")
                st.rerun()

            with detail_col.expander("View system remark / query details", expanded=False):
                st.write(str(r.get("remarks", "")))

            # Store the widget keys so the common Save All button can read the
            # current values directly from Streamlit session state.
            open_query_meta.append({
                "query_id": qi,
                "system_status": str(r.get("status", "")),
                "action_key": f"open_action_{client_id}_{fy}_{period}_{qi}",
                "note_key": f"open_note_{client_id}_{fy}_{period}_{qi}",
            })

            st.divider()

        # Common/bulk save button requested by the user.
        st.markdown("### 💾 Save All Open Query Resolutions")
        st.caption(
            "Use this button after reviewing/changing several queries. "
            "It saves the current dropdown selections and remarks for all open queries at once."
        )
        if st.button(
            "💾 Save All Query Resolutions",
            type="primary",
            key=f"save_all_open_{client_id}_{fy}_{period}"
        ):
            bulk_rows = []
            for item in open_query_meta:
                bulk_rows.append({
                    "Query ID": item["query_id"],
                    "System Status": item["system_status"],
                    "Manual Action": st.session_state.get(item["action_key"], "Pending"),
                    "Resolution Remarks": st.session_state.get(item["note_key"], ""),
                })

            if bulk_rows:
                bulk_df = pd.DataFrame(bulk_rows)
                update_actions(bulk_df, fy, period, client_id, client_name)
                refreshed = load_saved_period_results(fy, period, client_id, client_name)
                if not refreshed.empty:
                    st.session_state["recon_result"] = refreshed
                st.session_state["saved_review_key"] = _saved_review_key
                st.success(f"Saved {len(bulk_rows)} open query resolution(s).")
                st.rerun()
    else:
        st.success("🎉 There are no open queries for this client/FY.")

    # ---------------- CHANGE / RE-OPEN CLOSED QUERIES ----------------
    closed_resolved = tracker[~tracker["manual_action"].map(is_pending_action)].copy()
    if not closed_resolved.empty:
        with st.expander(f"🔄 Modify / Re-open Closed Queries ({len(closed_resolved)})", expanded=False):
            st.caption(
                "Select the query or queries you want to reopen. Only the selected rows will be reopened. "
                "The earlier accountant decision is never deleted; it remains permanently recorded in the FY audit trail."
            )

            # Checkbox-based selection requested by the user.  The accountant can
            # select one, several, or all closed queries and then reopen only those.
            cd = closed_resolved[[
                "query_id","last_period","document_type","gstin","party_name","document_number",
                "status","manual_action","resolution_remarks"
            ]].copy()
            cd.insert(0, "Select", False)
            cd.columns = [
                "Select","Query ID","Last Seen","Document Type","GSTIN","Party Name","Document Number",
                "System Status","Accountant Resolution","Resolution Remarks"
            ]

            closed_selected = st.data_editor(
                cd,
                hide_index=True,
                use_container_width=True,
                height=min(520, max(180, 54 + len(cd) * 38)),
                disabled=[
                    "Query ID","Last Seen","Document Type","GSTIN","Party Name",
                    "Document Number","System Status","Accountant Resolution","Resolution Remarks"
                ],
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "☑ Select",
                        help="Tick this box to select the query for reopening.",
                        default=False
                    ),
                    "Query ID": st.column_config.TextColumn("Query ID", width="small"),
                    "Party Name": st.column_config.TextColumn("Party Name", width="large"),
                    "Resolution Remarks": st.column_config.TextColumn("Resolution Remarks", width="large")
                },
                key=f"closed_query_selector_{client_id}_{fy}_{period}"
            )

            selected_rows = closed_selected[closed_selected["Select"] == True].copy()
            selected_count = len(selected_rows)

            st.metric("Selected Queries", selected_count)
            st.caption("☝️ Tick one or more rows in the first column. Only the selected queries will be reopened.")

            if selected_count > 0:
                selected_ids = selected_rows["Query ID"].astype(str).tolist()
                st.info(f"📌 {selected_count} query/queries selected for reopening.")
                if st.button(
                    f"🔄 Re-open Selected Query{'s' if selected_count != 1 else ''}",
                    type="primary",
                    key=f"reopen_selected_{client_id}_{fy}_{period}"
                ):
                    reopen_df = pd.DataFrame([{
                        "Query ID": qid_value,
                        "System Status": str(closed_resolved.loc[closed_resolved["query_id"].astype(str) == qid_value, "status"].iloc[0]),
                        "Manual Action": "Pending",
                        "Resolution Remarks": ""
                    } for qid_value in selected_ids])
                    update_actions(reopen_df, fy, period, client_id, client_name)
                    refreshed = load_saved_period_results(fy, period, client_id, client_name)
                    if not refreshed.empty:
                        st.session_state["recon_result"] = refreshed
                    st.session_state["saved_review_key"] = _saved_review_key
                    st.success(
                        f"✅ Re-opened {selected_count} query/queries. "
                        "They are now available in Open Queries — Accountant Resolution as Pending – Carry Forward."
                    )
                    st.rerun()
            else:
                st.info("☝️ Select at least one closed query using the checkbox in the first column.")

            st.subheader("✅ Current Closed / Resolved Queries")
            closed_display = closed_resolved[[
                "query_id","last_period","document_type","gstin","party_name","document_number",
                "status","manual_action","correction_date","resolution_remarks"
            ]].copy()
            closed_display.columns = [
                "Query ID","Last Seen","Document Type","GSTIN","Party Name","Document Number",
                "Original System Status","Accountant Resolution","Correction Date","Resolution Remarks"
            ]
            st.dataframe(closed_display, hide_index=True, use_container_width=True)

    st.subheader("📚 FY History / Audit Trail")
    hist=tracker.copy()
    hist["Final Status"]=hist.apply(
        lambda r:"Matched" if (not is_pending_action(r.manual_action)) or canonical_status(r.status)=="Matched" else r.status,axis=1
    )
    hist["Resolution"]=hist["manual_action"].apply(
        lambda x:"Open / Carry Forward" if is_pending_action(x) else canonical_action(x)
    )
    hist_display=hist[[
        "client_name","query_id","financial_year","first_period","last_period","document_type",
        "gstin","party_name","document_number","status","Final Status","manual_action","correction_date",
        "carry_forward","remarks","resolution_remarks"
    ]].copy()
    hist_display.columns=[
        "Client","Query ID","FY","First Period","Last Seen","Document Type","GSTIN","Party Name","Document Number",
        "Original System Status","Final Status","Accountant Resolution","Correction Date",
        "Carry Forward","System Remarks","Resolution Remarks"
    ]
    st.dataframe(hist_display,hide_index=True,use_container_width=True)

    # Detailed event history: shows every accountant resolution change, including re-open/re-close actions.
    con_hist=db()
    event_hist=pd.read_sql_query("""SELECT period,event,status,manual_action,remarks,event_time,query_id
        FROM history WHERE client_id=? ORDER BY event_time DESC""", con_hist, params=(client_id,))
    con_hist.close()
    if not event_hist.empty:
        with st.expander("🕘 Detailed Resolution Change History", expanded=False):
            st.dataframe(event_hist, hide_index=True, use_container_width=True)

# Apply accountant resolutions to the current report without losing the original system finding.
report_combined = combined.copy()
if not tracker.empty and "Query ID" in report_combined.columns:
    tr = tracker[[
        "query_id","status","manual_action","correction_date","resolution_remarks"
    ]].copy()
    tr.columns = ["Query ID","Original System Status","Accountant Resolution","Correction Date","Resolution Remarks"]
    report_combined = report_combined.drop(columns=["Original System Status","Accountant Resolution","Correction Date","Resolution Remarks"], errors="ignore")
    report_combined = report_combined.merge(tr, on="Query ID", how="left")
    report_combined["Accountant Resolution"] = report_combined["Accountant Resolution"].fillna("Pending")
    report_combined["Final Status"] = report_combined.apply(
        lambda r: "Matched" if r["Accountant Resolution"] != "Pending" or r["Status"] == "Matched" else r["Status"], axis=1
    )
    report_combined["Resolution Remarks"] = report_combined["Resolution Remarks"].fillna("")
    # Keep Status as the final status so Excel row colouring reflects the accountant's resolution.
    report_combined["System Status"] = report_combined["Status"]
    report_combined["Status"] = report_combined["Final Status"]
    report_combined = report_combined.drop(columns=["Final Status"])
else:
    report_combined["System Status"] = report_combined["Status"]
    report_combined["Accountant Resolution"] = "Pending"
    report_combined["Correction Date"] = ""
    report_combined["Resolution Remarks"] = ""

# Final status summary reflects accountant closure: any documented resolution is green.
final_counts = report_combined["Status"].value_counts() if not report_combined.empty else pd.Series(dtype=int)
final_summary = pd.DataFrame([
    {"Final Status": s, "Count": int(final_counts.get(s, 0))} for s in STATUSES
])

st.divider(); st.subheader("🟢 Final Resolution Summary")
fs1,fs2,fs3,fs4 = st.columns(4)
fs1.metric("🟢 Matched / Resolved", int(final_counts.get("Matched", 0)))
fs2.metric("🟠 Amount / Tax Difference", int(final_counts.get("Amount / Tax Difference", 0)))
fs3.metric("🔴 Missing in Client", int(final_counts.get("Missing in Client", 0)))
fs4.metric("🔵 Missing in Portal", int(final_counts.get("Missing in Portal", 0)))
st.dataframe(final_summary, hide_index=True, use_container_width=True)

# ---------------- PROFESSIONAL REPORT CENTER ----------------
st.divider()
st.subheader("📊 Professional Report Center")
st.caption("Generate focused working-paper reports or download the complete GST-Recon AI report pack. Reports are prepared from the current reconciliation and FY tracker data.")

# Build focused exception reports.
_exception_source = report_combined.copy()
# Working-paper exception reports must use the ORIGINAL SYSTEM FINDING, not the
# green Final Status created by an accountant resolution. This keeps the audit
# trail clear: what the system found vs. what the accountant decided.
_exception_status_col = "System Status" if "System Status" in _exception_source.columns else "Status"
if not _exception_source.empty and _exception_status_col in _exception_source.columns:
    missing_client_report = _exception_source[_exception_source[_exception_status_col].map(canonical_status) == "Missing in Client"].copy()
    missing_portal_report = _exception_source[_exception_source[_exception_status_col].map(canonical_status) == "Missing in Portal"].copy()
    amount_diff_report = _exception_source[_exception_source[_exception_status_col].map(canonical_status) == "Amount / Tax Difference"].copy()
else:
    missing_client_report = pd.DataFrame()
    missing_portal_report = pd.DataFrame()
    amount_diff_report = pd.DataFrame()

# Accountant Resolutions is an FY-level audit report. It should not disappear
# merely because a saved-period review contains no currently visible rows.
resolved_report = tracker[~tracker["manual_action"].map(is_pending_action)].copy() if not tracker.empty else pd.DataFrame()

# A compact party-wise exception summary helps staff explain the issues to the client.
if not _exception_source.empty:
    _party_base = _exception_source.copy()
    if "GSTIN" not in _party_base.columns:
        _party_base["GSTIN"] = ""
    if "Party Name" not in _party_base.columns:
        _party_base["Party Name"] = ""
    _party_base["GSTIN"] = _party_base["GSTIN"].fillna("").astype(str)
    _party_base["Party Name"] = _party_base["Party Name"].fillna("").astype(str)
    _party_base["System Status For Report"] = _party_base[_exception_status_col]
    party_exception_summary = (_party_base.groupby(["GSTIN", "Party Name"], dropna=False)
        .agg(Total_Transactions=("System Status For Report", "size"),
             Matched=("System Status For Report", lambda x: int((x == "Matched").sum())),
             Amount_Tax_Difference=("System Status For Report", lambda x: int((x == "Amount / Tax Difference").sum())),
             Missing_in_Client=("System Status For Report", lambda x: int((x == "Missing in Client").sum())),
             Missing_in_Portal=("System Status For Report", lambda x: int((x == "Missing in Portal").sum())))
        .reset_index())
    party_exception_summary["Total_Exceptions"] = (party_exception_summary["Amount_Tax_Difference"] + party_exception_summary["Missing_in_Client"] + party_exception_summary["Missing_in_Portal"])
    party_exception_summary = party_exception_summary.sort_values(["Total_Exceptions", "Party Name"], ascending=[False, True])
else:
    party_exception_summary = pd.DataFrame()

# Professional report pack: keep all 11 reports as Excel, even when a report has no rows.
# The index is included only inside the ZIP and is not counted as one of the 11 reports.
report_pack = {
    "01_All_Reconciliation": report_combined,
    "02_Exception_Summary": final_summary,
    "03_Missing_in_Client": missing_client_report,
    "04_Missing_in_Portal": missing_portal_report,
    "05_Amount_Tax_Difference": amount_diff_report,
    "06_Accountant_Resolutions": resolved_report,
    "07_FY_Query_Tracker": tracker,
    "08_Party_Exception_Summary": party_exception_summary,
    "09_Document_Type_Summary": doc_summary,
    "10_File_Sheet_Detection": pd.DataFrame((pinv if isinstance(pinv, list) else []) + (cinv if isinstance(cinv, list) else [])),
    "11_FY_Audit_History": hist_display if 'hist_display' in locals() else pd.DataFrame(),
}

_report_purposes = {
    "01_All_Reconciliation": "Complete transaction-wise reconciliation",
    "02_Exception_Summary": "Summary of all reconciliation exceptions",
    "03_Missing_in_Client": "Portal transactions not available in client data",
    "04_Missing_in_Portal": "Client transactions not available on GST portal",
    "05_Amount_Tax_Difference": "Transactions with financial amount/tax differences",
    "06_Accountant_Resolutions": "Accountant actions and resolutions recorded",
    "07_FY_Query_Tracker": "Open, resolved and carry-forward FY queries",
    "08_Party_Exception_Summary": "Party-wise exception analysis",
    "09_Document_Type_Summary": "B2B/CDNR and other document-type summary",
    "10_File_Sheet_Detection": "Uploaded file and sheet detection details",
    "11_FY_Audit_History": "Complete FY audit trail and resolution history",
}

report_index = pd.DataFrame([
    {
        "No.": key[:2],
        "Report": key[3:].replace("_", " "),
        "Purpose": _report_purposes.get(key, "GST-Recon AI working paper report"),
        "Records": int(0 if df is None else len(df)),
        "Format": "Excel (.xlsx)",
    }
    for key, df in report_pack.items()
])

# Report selector: staff can download exactly the report they need.
_report_labels = {
    "Complete Reconciliation": "01_All_Reconciliation",
    "Exception Summary": "02_Exception_Summary",
    "Missing in Client": "03_Missing_in_Client",
    "Missing in Portal": "04_Missing_in_Portal",
    "Amount / Tax Difference": "05_Amount_Tax_Difference",
    "Accountant Resolutions": "06_Accountant_Resolutions",
    "FY Query Tracker": "07_FY_Query_Tracker",
    "Party-wise Exception Summary": "08_Party_Exception_Summary",
    "Document Type Summary": "09_Document_Type_Summary",
    "File / Sheet Detection": "10_File_Sheet_Detection",
    "FY Audit History": "11_FY_Audit_History",
}

rc1, rc2 = st.columns([3.5, 1.5])
with rc1:
    selected_report_label = st.selectbox(
        "Select Report",
        list(_report_labels.keys()),
        key=f"report_center_select_{client_id}_{fy}_{period}",
        help="Choose one focused working-paper report to download."
    )
with rc2:
    st.metric("Reports Available", len(_report_labels))

_selected_key = _report_labels[selected_report_label]
_selected_df = report_pack[_selected_key]
if _selected_df is None or _selected_df.empty:
    _selected_download_df = pd.DataFrame({"Message": ["No records found for this report in the selected reconciliation period."]})
else:
    _selected_download_df = _selected_df
_selected_file = f"GST_Recon_AI_{_selected_key}_{client_name}_{fy}_{period}.xlsx"

rcb1, rcb2 = st.columns([1, 1])
with rcb1:
    st.download_button(
        "⬇️ Download Selected Report",
        data=excel_download({_selected_key: _selected_download_df}),
        file_name=_selected_file,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"download_selected_report_{client_id}_{fy}_{period}"
    )

def _make_report_pack_zip():
    """Create a professional ZIP containing only Excel workbooks.

    Empty reports are deliberately exported as valid .xlsx files with a Message
    sheet instead of .txt files, so the complete pack has a consistent format.
    A 00_Report_Index.xlsx workbook is added as a guide for staff.
    """
    zbio = BytesIO()
    with ZipFile(zbio, "w", ZIP_DEFLATED) as zf:
        # First file: Excel-only index/contents sheet.
        index_bytes = excel_download({"00_Report_Index": report_index}).getvalue()
        zf.writestr("00_Report_Index.xlsx", index_bytes)

        for sheet_name, df in report_pack.items():
            if df is None or df.empty:
                export_df = pd.DataFrame({
                    "Message": [
                        "No records found for this report in the selected reconciliation period."
                    ]
                })
            else:
                export_df = df

            xlsx_bytes = excel_download({sheet_name: export_df}).getvalue()
            # Defensive check: an XLSX is a ZIP package and begins with PK.
            if not xlsx_bytes.startswith(b"PK"):
                raise ValueError(f"Report {sheet_name} did not generate a valid XLSX workbook.")
            zf.writestr(f"{sheet_name}.xlsx", xlsx_bytes)
    zbio.seek(0)
    return zbio

with rcb2:
    st.download_button(
        "📦 Download Complete Report Pack (ZIP)",
        data=_make_report_pack_zip(),
        file_name=f"GST_Recon_AI_Report_Pack_{client_name}_{fy}_{period}.zip",
        mime="application/zip",
        use_container_width=True,
        key=f"download_report_pack_{client_id}_{fy}_{period}"
    )

st.markdown("**Complete Excel Report Pack:** 00 Report Index + 11 working-paper reports. Empty reports are also delivered as valid `.xlsx` files.")
st.success("Reconciliation completed. Review the results before using them for professional GST filing/advisory work.")
st.caption("Version 25 — Chronological Period Reset + safe permanent-delete confirmation + robust Pending carry-forward handling + Party Name reliability + Professional Report Center + FY Reconciliation Control Center.")
