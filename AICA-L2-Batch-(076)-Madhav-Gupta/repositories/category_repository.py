from datetime import datetime


def _now():
    return datetime.now().isoformat(timespec="seconds")


def create_category(conn, name, code, description="", default_method="SLM",
                     default_useful_life=None, default_residual_pct=0,
                     default_tax_block_id=None, default_tax_rate=None):
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO asset_categories
           (category_name, category_code, description, default_method, default_useful_life,
            default_residual_pct, default_tax_block_id, default_tax_rate, active, created_at, modified_at)
           VALUES (?,?,?,?,?,?,?,?,1,?,?)""",
        (name, code, description, default_method, default_useful_life,
         default_residual_pct, default_tax_block_id, default_tax_rate, now, now),
    )
    category_id = cur.lastrowid
    cur.execute(
        "INSERT INTO asset_id_sequences (category_id, category_code, last_sequence) VALUES (?, ?, 0)",
        (category_id, code),
    )
    conn.commit()
    return category_id


def update_category(conn, category_id, **fields):
    """Allows editing a category (name, code, defaults). NOTE: existing Asset IDs
    already issued do not change; only NEW assets created after this update will use
    the revised category code as their ID prefix."""
    if not fields:
        return
    fields = dict(fields)
    fields["modified_at"] = _now()
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [category_id]
    conn.execute(f"UPDATE asset_categories SET {columns} WHERE category_id = ?", values)
    if "category_code" in fields:
        conn.execute("UPDATE asset_id_sequences SET category_code=? WHERE category_id=?",
                     (fields["category_code"], category_id))
    conn.commit()


def set_category_active(conn, category_id, active):
    conn.execute("UPDATE asset_categories SET active=?, modified_at=? WHERE category_id=?",
                 (1 if active else 0, _now(), category_id))
    conn.commit()


def get_category(conn, category_id):
    return conn.execute("SELECT * FROM asset_categories WHERE category_id=?", (category_id,)).fetchone()


def get_category_by_code(conn, code):
    return conn.execute("SELECT * FROM asset_categories WHERE category_code=?", (code,)).fetchone()


def list_categories(conn, active_only=False, search=None):
    query = "SELECT * FROM asset_categories"
    conditions, params = [], []
    if active_only:
        conditions.append("active = 1")
    if search:
        conditions.append("(category_name LIKE ? OR category_code LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY category_name"
    return conn.execute(query, params).fetchall()


def existing_codes(conn, exclude_category_id=None):
    if exclude_category_id:
        rows = conn.execute("SELECT category_code FROM asset_categories WHERE category_id != ?",
                             (exclude_category_id,)).fetchall()
    else:
        rows = conn.execute("SELECT category_code FROM asset_categories").fetchall()
    return {r["category_code"] for r in rows}