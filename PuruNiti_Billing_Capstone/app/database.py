import os
import sqlite3
import json
import glob
import re
import shutil
from app.license_manager import load_config, save_config, get_base_dir

def get_database_dir():
    """Reads configured database path from config.json."""
    config = load_config()
    db_path = config.get("database_path", "")
    if not db_path:
        db_path = os.path.join(get_base_dir(), "database")
    os.makedirs(db_path, exist_ok=True)
    return db_path

def get_invoices_dir():
    """Gets invoices subfolder path (retained for backup migrations)."""
    inv_path = os.path.join(get_database_dir(), "invoices")
    os.makedirs(inv_path, exist_ok=True)
    return inv_path

def get_db_connection():
    """Establishes an SQLite database connection with row factory and foreign keys active."""
    db_file = os.path.join(get_database_dir(), "puruniti_billing.db")
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

DEFAULT_SETTINGS = {
    "next_invoice_number": 1,
    "invoice_prefix": "INV-",
    "active_seller_id": "My Business Name",
    "sellers": {
        "My Business Name": {
            "trade_name": "My Business Name",
            "address": "123 Business Street, City, State, PIN-000000",
            "mobile": "+91 98765 43210",
            "email": "contact@mybusiness.com",
            "gstin": "27AAAAA0000A1Z1",
            "bank_name": "State Bank of India",
            "account_number": "123456789012",
            "ifsc": "SBIN0001234",
            "branch": "Main Branch",
            "declaration": "We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct."
        }
    }
}

def init_sqlite_db():
    """Creates the SQLite tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Sellers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sellers (
            trade_name TEXT PRIMARY KEY,
            address TEXT,
            mobile TEXT,
            email TEXT,
            gstin TEXT,
            bank_name TEXT,
            account_number TEXT,
            ifsc TEXT,
            branch TEXT,
            declaration TEXT
        );
    """)
    
    # Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT,
            mobile TEXT,
            email TEXT,
            address TEXT,
            gstin TEXT,
            pan TEXT,
            pin TEXT,
            place_of_supply TEXT
        );
    """)
    
    # Invoices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_number TEXT PRIMARY KEY,
            date TEXT,
            invoice_type TEXT,
            gst_treatment TEXT,
            place_of_supply TEXT,
            rcm INTEGER,
            subtotal REAL,
            cgst_total REAL,
            sgst_total REAL,
            igst_total REAL,
            cess_total REAL,
            round_off REAL,
            grand_total REAL,
            seller_trade_name TEXT,
            customer_name TEXT,
            customer_mobile TEXT,
            customer_address TEXT,
            customer_gstin TEXT,
            customer_pan TEXT,
            customer_pin TEXT,
            ship_to_name TEXT,
            ship_to_mobile TEXT,
            ship_to_address TEXT,
            ship_to_gstin TEXT
        );
    """)
    
    # Invoice items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            name TEXT,
            hsn TEXT,
            qty REAL,
            rate REAL,
            gst_rate REAL,
            cess_rate REAL,
            taxable_amount REAL,
            cgst_amount REAL,
            sgst_amount REAL,
            igst_amount REAL,
            cess_amount REAL,
            total_amount REAL,
            FOREIGN KEY (invoice_number) REFERENCES invoices(invoice_number) ON DELETE CASCADE
        );
    """)
    
    # Settings key-values table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    
    # Timesheets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timesheets (
            timesheet_id TEXT PRIMARY KEY,
            client_name TEXT,
            start_date TEXT,
            end_date TEXT,
            total_hours REAL,
            total_amount REAL,
            linked_invoice_number TEXT,
            status TEXT
        );
    """)
    
    # Timesheet entries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timesheet_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timesheet_id TEXT,
            date TEXT,
            activity TEXT,
            hours REAL,
            rate REAL,
            line_total REAL,
            FOREIGN KEY (timesheet_id) REFERENCES timesheets(timesheet_id) ON DELETE CASCADE
        );
    """)
    # Alter invoices to add template_style if not exists
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN template_style TEXT")
    except Exception:
        pass
        
    # Payments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            amount REAL,
            payment_date TEXT,
            payment_mode TEXT,
            reference_number TEXT,
            notes TEXT,
            FOREIGN KEY (invoice_number) REFERENCES invoices(invoice_number) ON DELETE CASCADE
        );
    """)

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            security_question TEXT,
            security_answer_hash TEXT
        );
    """)

    # Default Admin Provisioning
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        import hashlib
        import uuid
        salt = uuid.uuid4().hex
        admin_pass_hash = f"{salt}:" + hashlib.sha256((salt + "admin123").encode('utf-8')).hexdigest()
        ans_salt = uuid.uuid4().hex
        admin_ans_hash = f"{ans_salt}:" + hashlib.sha256((ans_salt + "admin").encode('utf-8')).hexdigest()
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, security_question, security_answer_hash)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", admin_pass_hash, "admin", "What is the default role?", admin_ans_hash))
        
    conn.commit()
    conn.close()

def get_settings():
    """Retrieves settings, building them dynamically from SQLite."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Load sellers
        cursor.execute("SELECT * FROM sellers")
        sellers_rows = cursor.fetchall()
        sellers_dict = {}
        for r in sellers_rows:
            sellers_dict[r["trade_name"]] = dict(r)
            
        # Load config attributes
        cursor.execute("SELECT key, value FROM settings")
        settings_rows = cursor.fetchall()
        settings_map = {r["key"]: r["value"] for r in settings_rows}
        
        if not sellers_dict:
            # First time setup, populate defaults
            conn.close()
            res = dict(DEFAULT_SETTINGS)
            res["seller"] = res["sellers"][res["active_seller_id"]]
            save_settings(res)
            return res
            
        next_num = int(settings_map.get("next_invoice_number", 1))
        prefix = settings_map.get("invoice_prefix", "INV-")
        active_seller = settings_map.get("active_seller_id", list(sellers_dict.keys())[0])
        
        conn.close()
        
        res = {
            "next_invoice_number": next_num,
            "invoice_prefix": prefix,
            "active_seller_id": active_seller,
            "sellers": sellers_dict,
            "seller": sellers_dict.get(active_seller, list(sellers_dict.values())[0])
        }
        return res
    except Exception as e:
        print(f"Error loading settings from SQL: {e}")
        conn.close()
        res = dict(DEFAULT_SETTINGS)
        res["seller"] = res["sellers"][res["active_seller_id"]]
        return res

def save_settings(settings):
    """Saves settings keys and seller profiles to SQLite database."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Save config variables
        for key in ["next_invoice_number", "invoice_prefix", "active_seller_id"]:
            if key in settings:
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (key, str(settings[key]))
                )
                
        # Clear old sellers to keep active profiles sync
        cursor.execute("DELETE FROM sellers")
        
        # Save sellers dict
        sellers = settings.get("sellers", {})
        for name, data in sellers.items():
            cursor.execute("""
                INSERT OR REPLACE INTO sellers (
                    trade_name, address, mobile, email, gstin, 
                    bank_name, account_number, ifsc, branch, declaration
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, data.get("address", ""), data.get("mobile", ""), data.get("email", ""),
                data.get("gstin", ""), data.get("bank_name", ""), data.get("account_number", ""),
                data.get("ifsc", ""), data.get("branch", ""), data.get("declaration", "")
            ))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving settings to SQL: {e}")
        return False
    finally:
        conn.close()

def get_customers():
    """Loads customers list from SQLite."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM customers ORDER BY name ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error loading customers from SQL: {e}")
        return []
    finally:
        conn.close()

def save_customers(customers):
    """Saves complete customer list in transaction block."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM customers")
        for c in customers:
            cursor.execute("""
                INSERT INTO customers (id, name, mobile, email, address, gstin, pan, pin, place_of_supply)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c.get("id"), c.get("name"), c.get("mobile", ""), c.get("email", ""),
                c.get("address", ""), c.get("gstin", ""), c.get("pan", ""),
                c.get("pin", ""), c.get("place_of_supply", "")
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving customers: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def save_invoice(invoice_data):
    """Saves the invoice and items in a transactional SQLite block."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        inv_no = invoice_data.get("invoice_number", "").strip()
        if not inv_no:
            raise ValueError("Invoice number is empty.")
            
        cust = invoice_data.get("customer", {})
        ship = invoice_data.get("ship_to", {})
        seller = invoice_data.get("seller", {})
        summary = invoice_data.get("summary", {})
        
        # 1. Write invoice header
        cursor.execute("""
            INSERT OR REPLACE INTO invoices (
                invoice_number, date, invoice_type, gst_treatment, place_of_supply, rcm,
                subtotal, cgst_total, sgst_total, igst_total, cess_total, round_off, grand_total,
                seller_trade_name, customer_name, customer_mobile, customer_address, 
                customer_gstin, customer_pan, customer_pin,
                ship_to_name, ship_to_mobile, ship_to_address, ship_to_gstin, template_style
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv_no, invoice_data.get("date"), invoice_data.get("invoice_type"),
            invoice_data.get("gst_treatment"), invoice_data.get("place_of_supply"),
            1 if invoice_data.get("rcm") else 0,
            summary.get("subtotal", 0.0), summary.get("cgst_total", 0.0),
            summary.get("sgst_total", 0.0), summary.get("igst_total", 0.0),
            summary.get("cess_total", 0.0), summary.get("round_off", 0.0),
            summary.get("grand_total", 0.0),
            seller.get("trade_name", ""),
            cust.get("name", ""), cust.get("mobile", ""), cust.get("address", ""),
            cust.get("gstin", ""), cust.get("pan", ""), cust.get("pin", ""),
            ship.get("name", ""), ship.get("mobile", ""), ship.get("address", ""), ship.get("gstin", ""),
            invoice_data.get("template_style", "Classic Elegant")
        ))
        
        # 2. Clear and write invoice line items
        cursor.execute("DELETE FROM invoice_items WHERE invoice_number = ?", (inv_no,))
        
        for item in invoice_data.get("items", []):
            cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_number, name, hsn, qty, rate, gst_rate, cess_rate,
                    taxable_amount, cgst_amount, sgst_amount, igst_amount, cess_amount, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inv_no, item.get("name"), item.get("hsn", ""),
                item.get("qty", 1.0), item.get("rate", 0.0),
                item.get("gst_rate", 0.0), item.get("cess_rate", 0.0),
                item.get("taxable_amount", 0.0), item.get("cgst_amount", 0.0),
                item.get("sgst_amount", 0.0), item.get("igst_amount", 0.0),
                item.get("cess_amount", 0.0), item.get("total_amount", 0.0)
            ))
            
        # 3. Handle Auto Invoice Number Increment
        cursor.execute("SELECT value FROM settings WHERE key = 'invoice_prefix'")
        prefix_row = cursor.fetchone()
        prefix = prefix_row[0] if prefix_row else "INV-"
        
        cursor.execute("SELECT value FROM settings WHERE key = 'next_invoice_number'")
        next_num_row = cursor.fetchone()
        next_num = int(next_num_row[0]) if next_num_row else 1
        
        expected_auto_num = f"{prefix}{next_num:04d}"
        
        if inv_no == expected_auto_num:
            # Save configuration through SQL directly
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("next_invoice_number", str(next_num + 1))
            )
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving invoice: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_invoice(invoice_number):
    """Deletes invoice header and line items from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM invoices WHERE invoice_number = ?", (invoice_number,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting invoice: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_invoice(invoice_number):
    """Loads invoice data and its items from SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM invoices WHERE invoice_number = ?", (invoice_number,))
        inv_row = cursor.fetchone()
        if not inv_row:
            return None
            
        invoice = dict(inv_row)
        # Cast RCM
        invoice["rcm"] = True if invoice["rcm"] == 1 else False
        
        # Build embedded models structure
        invoice["customer"] = {
            "name": invoice.pop("customer_name", ""),
            "mobile": invoice.pop("customer_mobile", ""),
            "address": invoice.pop("customer_address", ""),
            "gstin": invoice.pop("customer_gstin", ""),
            "pan": invoice.pop("customer_pan", ""),
            "pin": invoice.pop("customer_pin", "")
        }
        invoice["ship_to"] = {
            "name": invoice.pop("ship_to_name", ""),
            "mobile": invoice.pop("ship_to_mobile", ""),
            "address": invoice.pop("ship_to_address", ""),
            "gstin": invoice.pop("ship_to_gstin", "")
        }
        
        # Load seller details
        cursor.execute("SELECT * FROM sellers WHERE trade_name = ?", (invoice.get("seller_trade_name"),))
        seller_row = cursor.fetchone()
        invoice["seller"] = dict(seller_row) if seller_row else {}
        
        # Load invoice items
        cursor.execute("SELECT * FROM invoice_items WHERE invoice_number = ?", (invoice_number,))
        items_rows = cursor.fetchall()
        invoice["items"] = [dict(item) for item in items_rows]
        
        # Construct summary
        invoice["summary"] = {
            "subtotal": invoice.pop("subtotal", 0.0),
            "cgst_total": invoice.pop("cgst_total", 0.0),
            "sgst_total": invoice.pop("sgst_total", 0.0),
            "igst_total": invoice.pop("igst_total", 0.0),
            "cess_total": invoice.pop("cess_total", 0.0),
            "round_off": invoice.pop("round_off", 0.0),
            "grand_total": invoice.pop("grand_total", 0.0)
        }
        
        return invoice
    except Exception as e:
        print(f"Error loading invoice: {e}")
        return None
    finally:
        conn.close()

def get_all_invoices():
    """Loads all invoices metadata from SQLite."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Load in reverse date order
        cursor.execute("SELECT * FROM invoices ORDER BY date DESC, invoice_number DESC")
        rows = cursor.fetchall()
        invoices = []
        for r in rows:
            inv = dict(r)
            inv["rcm"] = True if inv["rcm"] == 1 else False
            inv["customer"] = {
                "name": inv.pop("customer_name", ""),
                "mobile": inv.pop("customer_mobile", ""),
                "address": inv.pop("customer_address", ""),
                "gstin": inv.pop("customer_gstin", ""),
                "pan": inv.pop("customer_pan", ""),
                "pin": inv.pop("customer_pin", "")
            }
            inv["summary"] = {
                "subtotal": inv.pop("subtotal", 0.0),
                "cgst_total": inv.pop("cgst_total", 0.0),
                "sgst_total": inv.pop("sgst_total", 0.0),
                "igst_total": inv.pop("igst_total", 0.0),
                "cess_total": inv.pop("cess_total", 0.0),
                "round_off": inv.pop("round_off", 0.0),
                "grand_total": inv.pop("grand_total", 0.0)
            }
            inv["seller"] = {"trade_name": inv.get("seller_trade_name", "")}
            
            # Load items for this invoice
            cursor.execute("SELECT * FROM invoice_items WHERE invoice_number = ?", (inv["invoice_number"],))
            inv["items"] = [dict(item) for item in cursor.fetchall()]
            
            invoices.append(inv)
        return invoices
    except Exception as e:
        print(f"Error getting invoices from SQLite: {e}")
        return []
    finally:
        conn.close()

def search_invoices(query):
    """Searches invoices by invoice number or customer name."""
    if not query:
        return get_all_invoices()
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = """
            SELECT * FROM invoices 
            WHERE invoice_number LIKE ? 
               OR customer_name LIKE ? 
               OR customer_mobile LIKE ?
            ORDER BY date DESC, invoice_number DESC
        """
        match = f"%{query}%"
        cursor.execute(sql, (match, match, match))
        rows = cursor.fetchall()
        invoices = []
        for r in rows:
            inv = dict(r)
            inv["customer"] = {
                "name": inv.pop("customer_name", ""),
                "mobile": inv.pop("customer_mobile", "")
            }
            inv["summary"] = {
                "grand_total": inv.pop("grand_total", 0.0)
            }
            invoices.append(inv)
        return invoices
    except Exception as e:
        print(f"Error searching invoices: {e}")
        return []
    finally:
        conn.close()

def get_next_invoice_number():
    """Generates next sequential candidate invoice number."""
    settings = get_settings()
    prefix = settings.get("invoice_prefix", "INV-")
    next_num = settings.get("next_invoice_number", 1)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        while True:
            candidate = f"{prefix}{next_num:04d}"
            cursor.execute("SELECT 1 FROM invoices WHERE invoice_number = ?", (candidate,))
            if not cursor.fetchone():
                break
            next_num += 1
        return candidate
    finally:
        conn.close()

def update_database_path(new_path):
    """Configures a new database path and migrates the SQLite DB and backups to it."""
    old_path = get_database_dir()
    if os.path.abspath(old_path) == os.path.abspath(new_path):
        return True
    try:
        os.makedirs(new_path, exist_ok=True)
        
        # Move puruniti_billing.db
        old_db = os.path.join(old_path, "puruniti_billing.db")
        new_db = os.path.join(new_path, "puruniti_billing.db")
        if os.path.exists(old_db) and not os.path.exists(new_db):
            shutil.copy2(old_db, new_db)
            
        config = load_config()
        config["database_path"] = new_path
        save_config(config)
        return True
    except Exception as e:
        print(f"Error shifting database: {e}")
        return False

def migrate_json_to_sqlite():
    """Automated startup importer to transition old settings, CRM and invoices JSON data to SQLite."""
    init_sqlite_db()
    db_dir = get_database_dir()
    
    # 1. Check legacy settings.json
    settings_file = os.path.join(db_dir, "settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r") as f:
                data = json.load(f)
                save_settings(data)
            shutil.move(settings_file, os.path.join(db_dir, "settings_migrated.json.bak"))
            print("Legacy settings migrated successfully.")
        except Exception as e:
            print(f"Error migrating settings: {e}")
            
    # 2. Check legacy customers.json
    customers_file = os.path.join(db_dir, "customers.json")
    if os.path.exists(customers_file):
        try:
            with open(customers_file, "r") as f:
                data = json.load(f)
                save_customers(data.get("customers", []))
            shutil.move(customers_file, os.path.join(db_dir, "customers_migrated.json.bak"))
            print("Legacy customers CRM migrated successfully.")
        except Exception as e:
            print(f"Error migrating customers: {e}")
            
    # 3. Check legacy invoices directory
    inv_dir = os.path.join(db_dir, "invoices")
    if os.path.exists(inv_dir):
        json_files = glob.glob(os.path.join(inv_dir, "*.json"))
        if json_files:
            migrated_dir = os.path.join(inv_dir, "migrated_bak")
            os.makedirs(migrated_dir, exist_ok=True)
            
            for file_path in json_files:
                try:
                    with open(file_path, "r") as f:
                        invoice_data = json.load(f)
                        save_invoice(invoice_data)
                    shutil.move(file_path, os.path.join(migrated_dir, os.path.basename(file_path)))
                except Exception as e:
                    print(f"Failed to migrate file {file_path}: {e}")
            print("Legacy JSON invoice files migrated successfully.")
            
def save_timesheet(ts):
    """Saves or updates a timesheet and its entries inside a transaction."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        
        # 1. Insert or Replace Timesheet metadata
        cursor.execute("""
            INSERT OR REPLACE INTO timesheets (
                timesheet_id, client_name, start_date, end_date, 
                total_hours, total_amount, linked_invoice_number, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ts.get("timesheet_id"),
            ts.get("client_name"),
            ts.get("start_date"),
            ts.get("end_date"),
            float(ts.get("total_hours", 0.0)),
            float(ts.get("total_amount", 0.0)),
            ts.get("linked_invoice_number"),
            ts.get("status", "Draft")
        ))
        
        # 2. Delete existing entries first
        cursor.execute("DELETE FROM timesheet_entries WHERE timesheet_id = ?", (ts.get("timesheet_id"),))
        
        # 3. Insert new entries
        for entry in ts.get("entries", []):
            cursor.execute("""
                INSERT INTO timesheet_entries (
                    timesheet_id, date, activity, hours, rate, line_total
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ts.get("timesheet_id"),
                entry.get("date"),
                entry.get("activity"),
                float(entry.get("hours", 0.0)),
                float(entry.get("rate", 0.0)),
                float(entry.get("line_total", 0.0))
            ))
            
        cursor.execute("COMMIT")
        return True
    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"Error saving timesheet: {e}")
        return False
    finally:
        conn.close()

def get_timesheet(timesheet_id):
    """Loads a timesheet and its entries."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet_id,))
        row = cursor.fetchone()
        if not row:
            return None
            
        ts = dict(row)
        cursor.execute("SELECT * FROM timesheet_entries WHERE timesheet_id = ? ORDER BY date ASC, id ASC", (timesheet_id,))
        ts["entries"] = [dict(entry) for entry in cursor.fetchall()]
        return ts
    except Exception as e:
        print(f"Error getting timesheet: {e}")
        return None
    finally:
        conn.close()

def get_all_timesheets():
    """Loads all timesheets from database."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM timesheets ORDER BY start_date DESC, timesheet_id DESC")
        rows = cursor.fetchall()
        timesheets = []
        for row in rows:
            ts = dict(row)
            cursor.execute("SELECT * FROM timesheet_entries WHERE timesheet_id = ? ORDER BY date ASC, id ASC", (ts["timesheet_id"],))
            ts["entries"] = [dict(entry) for entry in cursor.fetchall()]
            timesheets.append(ts)
        return timesheets
    except Exception as e:
        print(f"Error listing timesheets: {e}")
        return []
    finally:
        conn.close()

def delete_timesheet(timesheet_id):
    """Deletes a timesheet and cascade-deletes its entries."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("DELETE FROM timesheets WHERE timesheet_id = ?", (timesheet_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting timesheet: {e}")
        return False
    finally:
        conn.close()

def update_timesheet_status(timesheet_id, status, linked_invoice=None):
    """Updates status and invoice linkage on a timesheet."""
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE timesheets 
            SET status = ?, linked_invoice_number = ? 
            WHERE timesheet_id = ?
        """, (status, linked_invoice, timesheet_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating timesheet status: {e}")
        return False
    finally:
        conn.close()

# --- USER AUTHENTICATION HELPERS ---

def hash_password(password, salt=None):
    import hashlib
    import uuid
    if not salt:
        salt = uuid.uuid4().hex
    hashed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(stored_hash, password):
    if not stored_hash or ":" not in stored_hash:
        return False
    salt, hashed = stored_hash.split(':')
    return hash_password(password, salt) == stored_hash

def add_user(username, password, role, question=None, answer=None):
    init_sqlite_db()
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        pass_hash = hash_password(password)
        ans_hash = hash_password(answer) if answer else None
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, security_question, security_answer_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (username, pass_hash, role, question, ans_hash))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    init_sqlite_db()
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return None
        user = dict(row)
        if verify_password(user["password_hash"], password):
            return user
        return None
    except Exception as e:
        print(f"Error authenticating: {e}")
        return None
    finally:
        conn.close()

def change_password(username, new_password):
    init_sqlite_db()
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        pass_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (pass_hash, username))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error changing password: {e}")
        return False
    finally:
        conn.close()

def update_user_recovery(username, question, answer):
    init_sqlite_db()
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        ans_hash = hash_password(answer)
        cursor.execute("""
            UPDATE users 
            SET security_question = ?, security_answer_hash = ? 
            WHERE username = ?
        """, (question, ans_hash, username))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating recovery: {e}")
        return False
    finally:
        conn.close()

def reset_password_with_recovery(username, answer, new_password):
    init_sqlite_db()
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT security_answer_hash FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row or not row["security_answer_hash"]:
            return False
        if verify_password(row["security_answer_hash"], answer):
            pass_hash = hash_password(new_password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (pass_hash, username))
            conn.commit()
            return True
        return False
    except Exception as e:
        print(f"Error resetting password: {e}")
        return False
    finally:
        conn.close()

def get_user(username):
    init_sqlite_db()
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, username, role, security_question FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None
    finally:
        conn.close()

def get_all_users():
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, username, role, security_question FROM users ORDER BY username ASC")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error listing users: {e}")
        return []
    finally:
        conn.close()

def delete_user(username):
    init_sqlite_db()
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT role FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return False
        if row["role"] == "admin":
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            if cursor.fetchone()[0] <= 1:
                return False  # Cannot delete the only admin!
        
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False
    finally:
        conn.close()

# --- PAYMENT HELPERS ---

def add_payment(invoice_number, amount, payment_date, payment_mode, reference_number, notes):
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO payments (invoice_number, amount, payment_date, payment_mode, reference_number, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (invoice_number, amount, payment_date, payment_mode, reference_number, notes))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding payment: {e}")
        return False
    finally:
        conn.close()

def get_payments_for_invoice(invoice_number):
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM payments WHERE invoice_number = ? ORDER BY payment_date DESC, id DESC", (invoice_number,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting payments: {e}")
        return []
    finally:
        conn.close()

def delete_payment(payment_id):
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting payment: {e}")
        return False
    finally:
        conn.close()

def get_invoice_payment_summary(invoice_number):
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT grand_total FROM invoices WHERE invoice_number = ?", (invoice_number,))
        row = cursor.fetchone()
        if not row:
            return None
        grand_total = row["grand_total"]
        
        cursor.execute("SELECT SUM(amount) AS total_paid FROM payments WHERE invoice_number = ?", (invoice_number,))
        paid_row = cursor.fetchone()
        total_paid = paid_row["total_paid"] if paid_row["total_paid"] else 0.0
        
        return {
            "grand_total": grand_total,
            "total_paid": total_paid,
            "outstanding": max(0.0, grand_total - total_paid)
        }
    except Exception as e:
        print(f"Error getting invoice payment summary: {e}")
        return None
    finally:
        conn.close()

# --- AGING ANALYSIS HELPERS ---

def parse_invoice_date(date_str):
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.today()

def get_aging_report(brackets_str="30, 60, 90"):
    try:
        brackets = [int(b.strip()) for b in brackets_str.split(",") if b.strip()]
    except Exception:
        brackets = [30, 60, 90]
    brackets.sort()
    
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    from datetime import datetime
    today = datetime.today()
    
    try:
        cursor.execute("""
            SELECT invoice_number, date, customer_name, grand_total 
            FROM invoices
        """)
        invoices = cursor.fetchall()
        
        cursor.execute("SELECT invoice_number, SUM(amount) AS total_paid FROM payments GROUP BY invoice_number")
        payments_map = {row["invoice_number"]: row["total_paid"] for row in cursor.fetchall()}
        
        report = {}
        for inv in invoices:
            inv_no = inv["invoice_number"]
            cust_name = inv["customer_name"] or "Walk-in Customer"
            grand_total = inv["grand_total"] or 0.0
            paid = payments_map.get(inv_no, 0.0)
            outstanding = grand_total - paid
            
            if cust_name not in report:
                report[cust_name] = {
                    "customer_name": cust_name,
                    "total_invoiced": 0.0,
                    "total_paid": 0.0,
                    "outstanding_balance": 0.0,
                    "brackets": [0.0] * (len(brackets) + 1)
                }
                
            r = report[cust_name]
            r["total_invoiced"] += grand_total
            r["total_paid"] += paid
            r["outstanding_balance"] += outstanding
            
            if outstanding > 0.001:
                inv_date = parse_invoice_date(inv["date"])
                age_days = (today - inv_date).days
                
                bucket_idx = len(brackets)
                for idx, limit in enumerate(brackets):
                    if age_days <= limit:
                        bucket_idx = idx
                        break
                r["brackets"][bucket_idx] += outstanding
                
        return list(report.values())
    except Exception as e:
        print(f"Error generating aging report: {e}")
        return []
    finally:
        conn.close()

def get_payments_by_period(start_date=None, end_date=None):
    init_sqlite_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT p.id, p.invoice_number, p.amount, p.payment_date, p.payment_mode, p.reference_number, p.notes, i.customer_name
            FROM payments p
            LEFT JOIN invoices i ON p.invoice_number = i.invoice_number
        """
        params = []
        if start_date and end_date:
            query += " WHERE p.payment_date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            query += " WHERE p.payment_date >= ?"
            params = [start_date]
        elif end_date:
            query += " WHERE p.payment_date <= ?"
            params = [end_date]
            
        query += " ORDER BY p.payment_date DESC, p.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting payments by period: {e}")
        return []
    finally:
        conn.close()
