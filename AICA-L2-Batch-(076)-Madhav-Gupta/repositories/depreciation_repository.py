from datetime import datetime


def _now():
    return datetime.now().isoformat(timespec="seconds")


def generate_next_run_id(conn):
    cur = conn.cursor()
    cur.execute("SELECT last_sequence FROM global_id_sequence WHERE seq_key='DEP_RUN'")
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO global_id_sequence(seq_key, last_sequence) VALUES ('DEP_RUN', 0)")
        next_seq = 1
    else:
        next_seq = row["last_sequence"] + 1
    cur.execute("UPDATE global_id_sequence SET last_sequence=? WHERE seq_key='DEP_RUN'", (next_seq,))
    conn.commit()
    return f"DEP-RUN-{next_seq:06d}"


def create_run(conn, run_id, financial_year, period_start, period_end, calculation_basis, created_by="SYSTEM"):
    conn.execute(
        """INSERT INTO depreciation_runs
           (run_id, financial_year, period_start, period_end, calculation_basis, status, created_at, created_by)
           VALUES (?,?,?,?,?, 'DRAFT', ?, ?)""",
        (run_id, financial_year, period_start, period_end, calculation_basis, _now(), created_by),
    )
    conn.commit()


def get_run(conn, run_id):
    return conn.execute("SELECT * FROM depreciation_runs WHERE run_id=?", (run_id,)).fetchone()


def list_runs(conn, financial_year=None):
    if financial_year:
        return conn.execute("SELECT * FROM depreciation_runs WHERE financial_year=? ORDER BY created_at DESC",
                             (financial_year,)).fetchall()
    return conn.execute("SELECT * FROM depreciation_runs ORDER BY created_at DESC").fetchall()


def existing_posted_run_for_asset(conn, asset_id, financial_year):
    return conn.execute(
        """SELECT dr.* FROM depreciation_records dr
           JOIN depreciation_runs r ON dr.run_id = r.run_id
           WHERE dr.asset_id=? AND dr.financial_year=? AND r.status='POSTED'""",
        (asset_id, financial_year),
    ).fetchall()


def insert_record(conn, record):
    columns = [
        "run_id", "asset_id", "financial_year", "period_start", "period_end",
        "opening_carrying_amount", "companies_act_method", "companies_act_depreciation",
        "closing_carrying_amount", "status", "created_at",
    ]
    record = dict(record)
    if not record.get("status"):
        record["status"] = "CALCULATED"
    record["created_at"] = _now()
    placeholders = ",".join("?" for _ in columns)
    conn.execute(f"INSERT INTO depreciation_records ({','.join(columns)}) VALUES ({placeholders})",
                 [record.get(c) for c in columns])


def insert_block_record(conn, record):
    columns = [
        "run_id", "block_id", "financial_year", "period_start", "period_end", "opening_wdv",
        "additions_full_rate", "additions_half_rate", "disposals", "wdv_before_depreciation",
        "tax_rate", "depreciation", "closing_wdv", "short_term_capital_gain",
        "closing_carrying_amount_total", "temporary_difference", "deferred_tax_rate",
        "deferred_tax", "deferred_tax_type", "status", "created_at",
    ]
    record = dict(record)
    if not record.get("status"):
        record["status"] = "CALCULATED"
    record["created_at"] = _now()
    placeholders = ",".join("?" for _ in columns)
    conn.execute(f"INSERT INTO tax_block_records ({','.join(columns)}) VALUES ({placeholders})",
                 [record.get(c) for c in columns])


def get_latest_posted_block_record(conn, block_id):
    return conn.execute(
        """SELECT br.* FROM tax_block_records br JOIN depreciation_runs r ON br.run_id = r.run_id
           WHERE br.block_id=? AND r.status='POSTED' ORDER BY br.created_at DESC LIMIT 1""",
        (block_id,),
    ).fetchone()


def get_block_records_for_run(conn, run_id):
    return conn.execute("SELECT * FROM tax_block_records WHERE run_id=?", (run_id,)).fetchall()


def get_block_history(conn, block_id):
    return conn.execute(
        """SELECT br.*, r.status as run_status FROM tax_block_records br
           JOIN depreciation_runs r ON br.run_id = r.run_id
           WHERE br.block_id=? ORDER BY br.period_start""",
        (block_id,),
    ).fetchall()


def update_run_status(conn, run_id, status, totals=None, reversed_run_id=None):
    if totals:
        conn.execute(
            """UPDATE depreciation_runs SET status=?, total_assets=?, total_ca_dep=?,
               total_it_dep=?, total_deferred_tax=? WHERE run_id=?""",
            (status, totals.get("total_assets", 0), totals.get("total_ca_dep", 0),
             totals.get("total_it_dep", 0), totals.get("total_deferred_tax", 0), run_id),
        )
    else:
        conn.execute("UPDATE depreciation_runs SET status=? WHERE run_id=?", (status, run_id))
    if reversed_run_id:
        conn.execute("UPDATE depreciation_runs SET reversed_run_id=? WHERE run_id=?", (reversed_run_id, run_id))
    conn.commit()


def get_records_for_run(conn, run_id):
    return conn.execute(
        """SELECT dr.*, a.asset_name FROM depreciation_records dr
           JOIN assets a ON dr.asset_id = a.asset_id
           WHERE dr.run_id=? ORDER BY dr.asset_id""",
        (run_id,),
    ).fetchall()


def get_history_for_asset(conn, asset_id):
    return conn.execute(
        """SELECT dr.*, r.status as run_status FROM depreciation_records dr
           JOIN depreciation_runs r ON dr.run_id = r.run_id
           WHERE dr.asset_id=? ORDER BY dr.period_start""",
        (asset_id,),
    ).fetchall()