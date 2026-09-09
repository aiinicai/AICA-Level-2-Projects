from datetime import datetime


def _now():
    return datetime.now().isoformat(timespec="seconds")


def generate_next_asset_id(conn, category_id, category_code, mode="CATEGORY"):
    """Atomically generate the next Asset ID (transaction-safe)."""
    cur = conn.cursor()
    if mode == "GLOBAL":
        cur.execute("SELECT last_sequence FROM global_id_sequence WHERE seq_key='GLOBAL'")
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO global_id_sequence(seq_key, last_sequence) VALUES ('GLOBAL', 0)")
            next_seq = 1
        else:
            next_seq = row["last_sequence"] + 1
        cur.execute("UPDATE global_id_sequence SET last_sequence=? WHERE seq_key='GLOBAL'", (next_seq,))
        conn.commit()
        return f"ADP-{next_seq:06d}"

    cur.execute("SELECT last_sequence FROM asset_id_sequences WHERE category_id=?", (category_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO asset_id_sequences(category_id, category_code, last_sequence) VALUES (?,?,0)",
                    (category_id, category_code))
        next_seq = 1
    else:
        next_seq = row["last_sequence"] + 1
    cur.execute("UPDATE asset_id_sequences SET last_sequence=? WHERE category_id=?", (next_seq, category_id))
    conn.commit()
    return f"{category_code}-{next_seq:06d}"


def insert_asset(conn, asset_id, data):
    now = _now()
    columns = [
        "asset_id", "asset_name", "category_id", "description", "location", "department",
        "purchase_date", "date_put_to_use", "original_cost", "capitalised_cost", "residual_value",
        "useful_life_years", "useful_life_months", "companies_act_method", "companies_act_rate",
        "income_tax_block_id", "income_tax_rate", "quantity", "vendor_name", "invoice_number",
        "opening_wdv", "opening_accum_dep", "opening_tax_wdv", "status", "disposal_date",
        "disposal_value", "buyer_name", "remarks", "parent_asset_id", "is_depreciable",
        "created_at", "modified_at",
    ]
    values = {c: data.get(c) for c in columns}
    values["asset_id"] = asset_id
    values["created_at"] = now
    values["modified_at"] = now
    if not values.get("status"):
        values["status"] = "ACTIVE"
    if values.get("is_depreciable") is None:
        values["is_depreciable"] = 1
    placeholders = ",".join("?" for _ in columns)
    conn.execute(f"INSERT INTO assets ({','.join(columns)}) VALUES ({placeholders})",
                 [values[c] for c in columns])
    conn.commit()


def update_asset(conn, asset_id, fields):
    if not fields:
        return
    fields = dict(fields)
    fields["modified_at"] = _now()
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [asset_id]
    conn.execute(f"UPDATE assets SET {columns} WHERE asset_id = ?", values)
    conn.commit()


def get_asset(conn, asset_id):
    return conn.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()


def list_assets(conn, status=None, category_id=None, search=None):
    query = """SELECT a.*, c.category_name, c.category_code FROM assets a
               JOIN asset_categories c ON a.category_id = c.category_id"""
    conditions, params = [], []
    if status:
        conditions.append("a.status = ?")
        params.append(status)
    if category_id:
        conditions.append("a.category_id = ?")
        params.append(category_id)
    if search:
        conditions.append("(a.asset_id LIKE ? OR a.asset_name LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY a.asset_id"
    return conn.execute(query, params).fetchall()


def set_status(conn, asset_id, status):
    conn.execute("UPDATE assets SET status=?, modified_at=? WHERE asset_id=?", (status, _now(), asset_id))
    conn.commit()
def delete_asset(conn, asset_id):
    """Hard delete an asset from the database."""
    conn.execute("DELETE FROM assets WHERE asset_id = ?", (asset_id,))
    conn.commit()