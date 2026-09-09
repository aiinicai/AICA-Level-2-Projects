from datetime import datetime


def _now():
    return datetime.now().isoformat(timespec="seconds")


def has_existing_disposal(conn, asset_id):
    row = conn.execute("SELECT COUNT(*) as c FROM disposal_records WHERE asset_id=?", (asset_id,)).fetchone()
    return row["c"] > 0


def insert_disposal(conn, data):
    columns = [
        "asset_id", "disposal_date", "sale_consideration", "selling_expenses", "buyer_name",
        "invoice_number", "remarks", "original_cost", "accumulated_depreciation", "net_book_value",
        "net_sale_proceeds", "profit_loss", "profit_loss_type", "tax_opening_wdv", "tax_closing_wdv",
        "tax_impact", "tax_impact_type", "carrying_amount_before", "tax_base_before",
        "temporary_difference_before", "deferred_tax_before", "created_at",
    ]
    data = dict(data)
    data["created_at"] = _now()
    placeholders = ",".join("?" for _ in columns)
    conn.execute(f"INSERT INTO disposal_records ({','.join(columns)}) VALUES ({placeholders})",
                 [data.get(c) for c in columns])
    conn.commit()


def get_disposal(conn, asset_id):
    return conn.execute("SELECT * FROM disposal_records WHERE asset_id=?", (asset_id,)).fetchone()


def list_disposals(conn):
    return conn.execute(
        """SELECT d.*, a.asset_name, a.purchase_date FROM disposal_records d
           JOIN assets a ON d.asset_id = a.asset_id ORDER BY d.disposal_date"""
    ).fetchall()


def get_disposals_in_period(conn, period_start, period_end):
    """Used by the block-of-assets Income-tax calculation to determine how much sale
    consideration should reduce each block's WDV for the given period."""
    return conn.execute(
        """SELECT d.asset_id, d.sale_consideration, d.disposal_date, a.income_tax_block_id
           FROM disposal_records d JOIN assets a ON d.asset_id = a.asset_id
           WHERE d.disposal_date BETWEEN ? AND ?""",
        (period_start, period_end),
    ).fetchall()

def delete_disposal_record(conn, asset_id):
    """Removes the disposal record for an asset."""
    conn.execute("DELETE FROM disposal_records WHERE asset_id = ?", (asset_id,))
    conn.commit()