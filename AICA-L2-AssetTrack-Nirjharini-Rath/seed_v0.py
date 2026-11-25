"""Sample data seeder for the Windows v0 Edition (populates 12 realistic office assets on first launch)."""

from __future__ import annotations

from datetime import date, timedelta

from app.database import get_connection, init_db, new_id, utc_now_iso
from app.excel_exporter import save_master_excel


def seed_if_empty() -> None:
    init_db()
    with get_connection() as conn:
        if conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] > 0:
            return
        now = utc_now_iso()
        today = date.today()

        v_carp, v_ac, v_it, v_stat = new_id(), new_id(), new_id(), new_id()
        conn.executemany(
            "INSERT INTO vendors (id, name, vendor_type, contact_person, phone, email, address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (v_carp, "Sharma Woodworks", "CARPENTER", "Rajesh Sharma", "+919861011223", "sharma@example.com", "Saheed Nagar", now),
                (v_ac, "CoolBreeze AC Care", "SERVICE_CENTER", "Amit Verma", "+919861022334", "ac@example.com", "Janpath Road", now),
                (v_it, "Kalinga IT Solutions", "SERVICE_CENTER", "Sandeep Mohanty", "+919861033445", "it@example.com", "Nayapalli", now),
                (v_stat, "Metro Office Supplies", "STATIONERY", "Priya Nair", "+919861066778", "orders@example.com", "Master Canteen", now),
            ],
        )

        assets = [
            ("AST-FURN-001", "Executive Conference Table", "FURNITURE", "Boardroom", 58000, v_carp, "ANNUAL", (today + timedelta(days=5)).isoformat(), "OPERATIONAL"),
            ("AST-FURN-002", "Ergonomic High-Back Chair #1", "FURNITURE", "Boardroom", 12500, v_carp, "ANNUAL", (today + timedelta(days=60)).isoformat(), "OPERATIONAL"),
            ("AST-FURN-003", "Steel Fireproof Filing Cabinet", "FURNITURE", "Record Room", 22000, v_carp, "ANNUAL", (today + timedelta(days=90)).isoformat(), "OPERATIONAL"),
            ("AST-ELEC-001", "Daikin Inverter Split AC 2.0T", "ELECTRICAL", "Boardroom", 58500, v_ac, "QUARTERLY", (today - timedelta(days=3)).isoformat(), "NEEDS_REPAIR"),
            ("AST-ELEC-002", "Voltas Cassette AC 3.0T", "ELECTRICAL", "Audit Floor", 89000, v_ac, "QUARTERLY", (today + timedelta(days=18)).isoformat(), "OPERATIONAL"),
            ("AST-ELEC-003", "APC Smart-UPS 3000VA", "ELECTRICAL", "Server Room", 62000, v_it, "BI_ANNUAL", (today + timedelta(days=45)).isoformat(), "OPERATIONAL"),
            ("AST-IT-001", "HP LaserJet Pro MFP M428fdw", "IT_HARDWARE", "Audit Floor", 36500, v_it, "QUARTERLY", (today + timedelta(days=4)).isoformat(), "OPERATIONAL"),
            ("AST-IT-002", "Canon imageCLASS Copier", "IT_HARDWARE", "Print Bay", 49000, v_it, "QUARTERLY", (today + timedelta(days=25)).isoformat(), "IN_MAINTENANCE"),
            ("AST-IT-003", "Dell OptiPlex 7010 Workstation", "IT_HARDWARE", "Tax Wing", 54000, v_it, "BI_ANNUAL", (today + timedelta(days=120)).isoformat(), "OPERATIONAL"),
            ("AST-FIXT-001", "Kent Grand+ RO Water Purifier", "OFFICE_FIXTURES", "Pantry", 19500, v_ac, "QUARTERLY", (today + timedelta(days=10)).isoformat(), "OPERATIONAL"),
            ("AST-FIXT-002", "eSSL Biometric Access Terminal", "OFFICE_FIXTURES", "Main Entrance", 16800, v_it, "BI_ANNUAL", (today + timedelta(days=80)).isoformat(), "OPERATIONAL"),
            ("AST-MACH-001", "Fellowes 99Ci Paper Shredder", "MACHINERY", "Record Room", 27500, v_stat, "QUARTERLY", (today + timedelta(days=50)).isoformat(), "OPERATIONAL"),
        ]
        first_ac_id = None
        for tag, name, cat, loc, cost, vid, cyc, nm, st in assets:
            aid = new_id()
            if tag == "AST-ELEC-001":
                first_ac_id = aid
            conn.execute(
                """
                INSERT INTO assets (id, asset_tag, name, category, location, purchase_date, purchase_cost, vendor_id, maintenance_cycle, next_maintenance_date, status, photos, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?)
                """,
                (aid, tag, name, cat, loc, (today - timedelta(days=200)).isoformat(), float(cost), vid, cyc, nm, st, now),
            )

        if first_ac_id:
            conn.execute(
                "INSERT INTO maintenance_records (id, asset_id, vendor_id, scheduled_date, cost, description, status, photos, created_at) VALUES (?, ?, ?, ?, ?, ?, 'SCHEDULED', '[]', ?)",
                (new_id(), first_ac_id, v_ac, today.isoformat(), 1800.0, "Quarterly filter wash & drain pipe cleaning", now),
            )

        conn.executemany(
            "INSERT INTO recurring_consumables (id, item_name, category, current_stock, unit, minimum_reorder_threshold, preferred_vendor_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (new_id(), "A4 Copier Paper (75 GSM)", "PAPER", 3, "Reams", 8, v_stat, now),
                (new_id(), "HP 77A Black Toner", "INK", 1, "Cartridges", 3, v_stat, now),
                (new_id(), "Whiteboard Markers", "WRITING", 14, "Packs", 5, v_stat, now),
                (new_id(), "Audit Box Files", "PAPER", 24, "Pieces", 10, v_stat, now),
            ],
        )
    save_master_excel()


if __name__ == "__main__":
    seed_if_empty()
    print("v0 sample data seeded.")
