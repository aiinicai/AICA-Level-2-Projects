from datetime import datetime


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT setting_value FROM application_settings WHERE setting_key=?", (key,)).fetchone()
    return row["setting_value"] if row else default


def set_setting(conn, key, value):
    conn.execute(
        """INSERT INTO application_settings (setting_key, setting_value) VALUES (?, ?)
           ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value""",
        (key, str(value)),
    )
    conn.commit()


def all_settings(conn):
    rows = conn.execute("SELECT setting_key, setting_value FROM application_settings").fetchall()
    return {r["setting_key"]: r["setting_value"] for r in rows}


def get_current_deferred_tax_rate(conn):
    row = conn.execute(
        "SELECT deferred_tax_rate FROM tax_settings WHERE active=1 ORDER BY setting_id DESC LIMIT 1"
    ).fetchone()
    return float(row["deferred_tax_rate"]) if row else 25.0


def set_deferred_tax_rate(conn, rate):
    conn.execute("UPDATE tax_settings SET active=0 WHERE active=1")
    conn.execute("INSERT INTO tax_settings (deferred_tax_rate, effective_from, active) VALUES (?, date('now'), 1)",
                 (rate,))
    conn.commit()


def list_tax_blocks(conn, active_only=False):
    q = "SELECT * FROM tax_blocks"
    if active_only:
        q += " WHERE active=1"
    q += " ORDER BY block_name"
    return conn.execute(q).fetchall()


def create_tax_block(conn, name, code, description, default_rate, applicable_from=None, applicable_to=None):
    conn.execute(
        """INSERT INTO tax_blocks(block_name, block_code, description, default_rate,
           applicable_from, applicable_to, active) VALUES (?,?,?,?,?,?,1)""",
        (name, code, description, default_rate, applicable_from, applicable_to),
    )
    conn.commit()


def log_audit(conn, action, entity, entity_id, old_value="", new_value=""):
    conn.execute(
        """INSERT INTO audit_log(action, entity, entity_id, old_value, new_value, timestamp)
           VALUES (?,?,?,?,?,?)""",
        (action, entity, str(entity_id), str(old_value), str(new_value),
         datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()