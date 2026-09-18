import sqlite3
import os
import datetime
import pandas as pd
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_audit.db")
DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")

STATUS_CHOICES = [
    "Not Started",
    "Data Awaited from Bank",
    "Data Awaited from Borrower",
    "Documents Under Review",
    "Visit Planned",
    "Visit Completed",
    "Stock Verification Completed",
    "Report Preparation",
    "Review Pending",
    "Partner Review Completed",
    "Report Submitted",
    "Closed",
    "Delayed"
]

DOC_CATEGORIES = [
    "Appointment Letter",
    "Bank Data",
    "Stock Statements",
    "Visit Photographs",
    "Audit Report",
    "Supporting Documents"
]

def get_connection():
    os.makedirs(DOCS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Team Member', -- 'Partner', 'Team Member'
        email TEXT,
        mobile TEXT,
        status TEXT NOT NULL DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Audit Assignments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        borrower_name TEXT NOT NULL,
        bank_name TEXT NOT NULL,
        allotment_date TEXT,
        acceptance_date TEXT,
        data_req_bank_date TEXT,
        data_req_borrower_date TEXT,
        pending_details TEXT,
        team_person_name TEXT,
        team_person_number TEXT,
        target_visit_date TEXT,
        actual_visit_date TEXT,
        audit_status TEXT DEFAULT 'Not Started',
        review_partner_date TEXT,
        report_target_date TEXT,
        report_submission_date TEXT,
        remarks TEXT,
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_status_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 3. Activity Log Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER,
        borrower_name TEXT,
        user_name TEXT NOT NULL,
        action TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assignment_id) REFERENCES audit_assignments (id) ON DELETE SET NULL
    );
    """)
    
    # 4. Reminders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER,
        borrower_name TEXT,
        recipient_name TEXT,
        recipient_email TEXT,
        recipient_phone TEXT,
        reminder_type TEXT NOT NULL,
        message TEXT NOT NULL,
        channel TEXT DEFAULT 'Email',
        status TEXT DEFAULT 'Sent',
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assignment_id) REFERENCES audit_assignments (id) ON DELETE SET NULL
    );
    """)
    
    # 5. Documents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        doc_category TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        uploaded_by TEXT NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assignment_id) REFERENCES audit_assignments (id) ON DELETE CASCADE
    );
    """)
    
    # 6. System Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    
    conn.commit()
    conn.close()

# ----------------- ACTIVITY LOGS -----------------

def log_activity(assignment_id: Optional[int], borrower_name: str, user_name: str, action: str, old_val: Optional[str] = None, new_val: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO activity_logs (assignment_id, borrower_name, user_name, action, old_value, new_value, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, borrower_name, user_name, action, str(old_val or ""), str(new_val or ""), now_str))
    conn.commit()
    conn.close()

def get_activity_logs(limit: int = 100, assignment_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if assignment_id:
        cursor.execute("SELECT * FROM activity_logs WHERE assignment_id = ? ORDER BY id DESC LIMIT ?", (assignment_id, limit))
    else:
        cursor.execute("SELECT * FROM activity_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

# ----------------- AUDIT ASSIGNMENTS CRUD -----------------

def get_all_assignments(user_role: str = "Partner", team_person_name: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if user_role == "Partner" or not team_person_name:
        cursor.execute("SELECT * FROM audit_assignments ORDER BY id DESC")
    else:
        cursor.execute("SELECT * FROM audit_assignments WHERE team_person_name LIKE ? ORDER BY id DESC", (f"%{team_person_name}%",))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_assignment_by_id(assignment_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_assignments WHERE id = ?", (assignment_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_assignment(data: Dict[str, Any], user_name: str = "System") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO audit_assignments (
            borrower_name, bank_name, allotment_date, acceptance_date,
            data_req_bank_date, data_req_borrower_date, pending_details,
            team_person_name, team_person_number, target_visit_date,
            actual_visit_date, audit_status, review_partner_date,
            report_target_date, report_submission_date, remarks,
            created_by, created_at, updated_at, last_status_update
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("borrower_name", "").strip(),
        data.get("bank_name", "").strip(),
        data.get("allotment_date"),
        data.get("acceptance_date"),
        data.get("data_req_bank_date"),
        data.get("data_req_borrower_date"),
        data.get("pending_details", ""),
        data.get("team_person_name", "").strip(),
        data.get("team_person_number", "").strip(),
        data.get("target_visit_date"),
        data.get("actual_visit_date"),
        data.get("audit_status", "Not Started"),
        data.get("review_partner_date"),
        data.get("report_target_date"),
        data.get("report_submission_date"),
        data.get("remarks", ""),
        user_name,
        now_str,
        now_str,
        now_str
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    log_activity(
        assignment_id=new_id,
        borrower_name=data.get("borrower_name", ""),
        user_name=user_name,
        action="Created New Audit Assignment",
        new_val=f"Bank: {data.get('bank_name')}, Assigned: {data.get('team_person_name')}"
    )
    return new_id

def update_assignment(assignment_id: int, data: Dict[str, Any], user_name: str) -> bool:
    old = get_assignment_by_id(assignment_id)
    if not old:
        return False
        
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    status_changed = (data.get("audit_status") != old.get("audit_status"))
    last_status_update = now_str if status_changed else old.get("last_status_update", now_str)
    
    cursor.execute("""
        UPDATE audit_assignments SET
            borrower_name = ?,
            bank_name = ?,
            allotment_date = ?,
            acceptance_date = ?,
            data_req_bank_date = ?,
            data_req_borrower_date = ?,
            pending_details = ?,
            team_person_name = ?,
            team_person_number = ?,
            target_visit_date = ?,
            actual_visit_date = ?,
            audit_status = ?,
            review_partner_date = ?,
            report_target_date = ?,
            report_submission_date = ?,
            remarks = ?,
            updated_at = ?,
            last_status_update = ?
        WHERE id = ?
    """, (
        data.get("borrower_name", old["borrower_name"]),
        data.get("bank_name", old["bank_name"]),
        data.get("allotment_date", old["allotment_date"]),
        data.get("acceptance_date", old["acceptance_date"]),
        data.get("data_req_bank_date", old["data_req_bank_date"]),
        data.get("data_req_borrower_date", old["data_req_borrower_date"]),
        data.get("pending_details", old["pending_details"]),
        data.get("team_person_name", old["team_person_name"]),
        data.get("team_person_number", old["team_person_number"]),
        data.get("target_visit_date", old["target_visit_date"]),
        data.get("actual_visit_date", old["actual_visit_date"]),
        data.get("audit_status", old["audit_status"]),
        data.get("review_partner_date", old["review_partner_date"]),
        data.get("report_target_date", old["report_target_date"]),
        data.get("report_submission_date", old["report_submission_date"]),
        data.get("remarks", old["remarks"]),
        now_str,
        last_status_update,
        assignment_id
    ))
    conn.commit()
    conn.close()
    
    # Check for logged changes
    tracked_fields = [
        ("audit_status", "Audit Status"),
        ("pending_details", "Pending Details"),
        ("actual_visit_date", "Actual Visit Date"),
        ("review_partner_date", "Review Date"),
        ("report_submission_date", "Report Submission Date"),
        ("team_person_name", "Assigned Person"),
        ("remarks", "Remarks")
    ]
    
    for key, label in tracked_fields:
        old_val = str(old.get(key) or "")
        new_val = str(data.get(key) or "")
        if old_val != new_val:
            log_activity(
                assignment_id=assignment_id,
                borrower_name=data.get("borrower_name", old["borrower_name"]),
                user_name=user_name,
                action=f"Updated {label}",
                old_val=old_val,
                new_val=new_val
            )
            
    return True

def delete_assignment(assignment_id: int, user_name: str) -> bool:
    old = get_assignment_by_id(assignment_id)
    if not old:
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_assignments WHERE id = ?", (assignment_id,))
    cursor.execute("DELETE FROM documents WHERE assignment_id = ?", (assignment_id,))
    cursor.execute("DELETE FROM reminders WHERE assignment_id = ?", (assignment_id,))
    conn.commit()
    conn.close()
    
    log_activity(
        assignment_id=assignment_id,
        borrower_name=old["borrower_name"],
        user_name=user_name,
        action="Deleted Audit Assignment",
        old_val=f"ID #{assignment_id} ({old['borrower_name']})",
        new_val="DELETED"
    )
    return True

# ----------------- USERS CRUD -----------------

def get_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, role, email, mobile, status, created_at FROM users ORDER BY full_name")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_user(username: str, password_hash: str, full_name: str, role: str, email: str, mobile: str, status: str = "Active") -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, role, email, mobile, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                full_name = excluded.full_name,
                role = excluded.role,
                email = excluded.email,
                mobile = excluded.mobile,
                status = excluded.status
        """, (username, password_hash, full_name, role, email, mobile, status))
        conn.commit()
        success = True
    except Exception as e:
        print("Error saving user:", e)
        success = False
    finally:
        conn.close()
    return success

def delete_user(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True

# ----------------- DOCUMENTS CRUD -----------------

def save_document(assignment_id: int, doc_category: str, file_name: str, file_bytes: bytes, uploaded_by: str) -> bool:
    try:
        assign_dir = os.path.join(DOCS_DIR, f"assignment_{assignment_id}")
        os.makedirs(assign_dir, exist_ok=True)
        safe_filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name.replace(' ', '_')}"
        file_path = os.path.join(assign_dir, safe_filename)
        
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        file_size = len(file_bytes)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (assignment_id, doc_category, file_name, file_path, file_size, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (assignment_id, doc_category, file_name, file_path, file_size, uploaded_by))
        conn.commit()
        conn.close()
        
        log_activity(
            assignment_id=assignment_id,
            borrower_name=f"Assignment #{assignment_id}",
            user_name=uploaded_by,
            action="Uploaded Document",
            new_val=f"{doc_category}: {file_name} ({round(file_size/1024, 1)} KB)"
        )
        return True
    except Exception as e:
        print("Error saving document:", e)
        return False

def get_assignment_documents(assignment_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE assignment_id = ? ORDER BY id DESC", (assignment_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_all_documents() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, a.borrower_name, a.bank_name 
        FROM documents d 
        LEFT JOIN audit_assignments a ON d.assignment_id = a.id 
        ORDER BY d.id DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

# ----------------- REMINDERS & SETTINGS -----------------

def log_reminder(assignment_id: Optional[int], borrower_name: str, recipient_name: str, recipient_email: str, recipient_phone: str, reminder_type: str, message: str, channel: str = "Email", status: str = "Sent"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reminders (assignment_id, borrower_name, recipient_name, recipient_email, recipient_phone, reminder_type, message, channel, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, borrower_name, recipient_name, recipient_email, recipient_phone, reminder_type, message, channel, status))
    conn.commit()
    conn.close()

def get_reminders(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reminders ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_setting(key: str, default_val: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default_val

def save_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO system_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database ready.")
