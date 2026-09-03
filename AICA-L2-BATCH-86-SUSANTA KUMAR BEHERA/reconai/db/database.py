import json
import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from reconai.models.session import ReconciliationSession, AuditTrailEvent
from reconai.models.client import ClientProfile, BankAccountProfile, ClientBookProfile
from reconai.models.transaction import (
    StatementTransaction,
    LedgerEntry,
    MatchRecord,
    AuditFlag,
    TransactionType,
    MatchStatus,
    AuditSeverity,
    AuditCategory,
)
from reconai.config import AppConfig, get_app_base_dir, get_default_db_path


class DatabaseManager:
    """Manages SQLite storage for Client Master, sessions, transactions, matches, and audit trail."""

    def __init__(self, db_path: Optional[str] = None, auto_seed: bool = True):
        if db_path is None:
            self.db_path = get_default_db_path()
        else:
            p = Path(db_path)
            if not p.is_absolute():
                self.db_path = str(get_app_base_dir() / p)
            else:
                self.db_path = str(p)
        self.auto_seed = auto_seed
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Client Master Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT,
                    pan TEXT,
                    gstin TEXT,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    approved_vendors_json TEXT,
                    default_auditor_notes TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # Bank Accounts Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bank_accounts (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    bank_name TEXT NOT NULL,
                    account_no TEXT NOT NULL,
                    ifsc TEXT,
                    branch TEXT,
                    account_type TEXT,
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                )
            """)

            # Client Accounting Books Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS client_books (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    book_name TEXT NOT NULL,
                    software TEXT,
                    account_head TEXT,
                    opening_balance REAL,
                    linked_bank_account TEXT,
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                )
            """)

            # Sessions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    client_id TEXT,
                    client_name TEXT,
                    period_label TEXT,
                    auditor_remarks TEXT,
                    partner_opinion TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    config_json TEXT
                )
            """)

            # Migration: Ensure new columns exist if upgraded
            cursor.execute("PRAGMA table_info(sessions)")
            existing_cols = [c["name"] for c in cursor.fetchall()]
            if "client_id" not in existing_cols:
                cursor.execute("ALTER TABLE sessions ADD COLUMN client_id TEXT")
            if "auditor_remarks" not in existing_cols:
                cursor.execute("ALTER TABLE sessions ADD COLUMN auditor_remarks TEXT")
            if "partner_opinion" not in existing_cols:
                cursor.execute("ALTER TABLE sessions ADD COLUMN partner_opinion TEXT")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statements (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    source_row_ref TEXT,
                    date TEXT,
                    description TEXT,
                    amount TEXT,
                    type TEXT,
                    balance TEXT,
                    raw_data_json TEXT,
                    matched INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ledgers (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    source_row_ref TEXT,
                    date TEXT,
                    description TEXT,
                    amount TEXT,
                    type TEXT,
                    account_name TEXT,
                    voucher_type TEXT,
                    approver_ref TEXT,
                    gstin TEXT,
                    tds_section TEXT,
                    raw_data_json TEXT,
                    matched INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    statement_tx_id TEXT,
                    ledger_entry_id TEXT,
                    status TEXT,
                    confidence_score REAL,
                    rule_applied TEXT,
                    plain_english_reason TEXT,
                    manual_override INTEGER,
                    notes TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_flags (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    target_type TEXT,
                    source_row_ref TEXT,
                    entry_id TEXT,
                    rule_name TEXT,
                    severity TEXT,
                    category TEXT,
                    plain_english_reason TEXT,
                    suggested_action TEXT,
                    entry_summary_json TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    timestamp TEXT,
                    action TEXT,
                    details TEXT,
                    user TEXT,
                    metadata_json TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()

            # Seed default client master profiles if database is empty
            if self.auto_seed:
                cursor.execute("SELECT count(*) as cnt FROM clients")
                if cursor.fetchone()["cnt"] == 0:
                    c1_id = "client-sun-health-care"
                    cursor.execute("""
                        INSERT INTO clients (id, name, entity_type, pan, gstin, email, phone, address, approved_vendors_json, default_auditor_notes, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        c1_id,
                        "SUN HEALTH CARE HOSPITAL",
                        "PROPRIETORSHIP",
                        "AAAPS1234F",
                        "21AAAPS1234F1Z5",
                        "sunhealthcare@gmail.com",
                        "9876543210",
                        "GOILUNDI SQUARE, KAMAPALLI ROAD BERHAMPUR, ODISHA 760001",
                        json.dumps(["CHOKADOLA ASSOCIATES", "SURGICARE", "KPS Agencies", "T S R Pharmaceuticals", "MS P P Pharmaceuticals"]),
                        "Regular monthly statutory reconciliation and expense audit for Sun Health Care Hospital.",
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ))
                    cursor.execute("""
                        INSERT INTO bank_accounts (id, client_id, bank_name, account_no, ifsc, branch, account_type)
                        VALUES 
                        ('ba-sun-1', ?, 'Bank of Maharashtra', '60453403246', 'MAHB0002179', 'KHODASINGI', 'CURRENT'),
                        ('ba-sun-2', ?, 'Bank of Maharashtra', '60396048669', 'MAHB0002179', 'KHODASINGI', 'CURRENT'),
                        ('ba-sun-3', ?, 'Bank of Maharashtra', '60456567202', 'MAHB0002179', 'KHODASINGI', 'CURRENT')
                    """, (c1_id, c1_id, c1_id))
                    cursor.execute("""
                        INSERT INTO client_books (id, client_id, book_name, software, account_head, opening_balance, linked_bank_account)
                        VALUES
                        ('cb-sun-1', ?, 'BOM CA 60453403246 (SUN EYE CARE) Book', 'Tally Prime', 'Bank Accounts', 2808619.47, '60453403246'),
                        ('cb-sun-2', ?, 'BOM CA 60396048669 (SUN HEALTH CARE) Book', 'Tally Prime', 'Bank Accounts', 0.0, '60396048669'),
                        ('cb-sun-3', ?, 'Cash Book', 'Tally Prime', 'Cash-in-hand', 0.0, NULL)
                    """, (c1_id, c1_id, c1_id))

                    c2_id = "client-sivanshi-traders"
                    cursor.execute("""
                        INSERT INTO clients (id, name, entity_type, pan, gstin, email, phone, address, approved_vendors_json, default_auditor_notes, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        c2_id,
                        "SIVANSHI TRADERS",
                        "PROPRIETORSHIP",
                        "BBNPT5678G",
                        "21BBNPT5678G1Z2",
                        "sivanshitraders@gmail.com",
                        "9876501234",
                        "KHATA NO- 917/1453, MAIN ROAD, TANGANNAPALLI, GANJAM, ODISHA 761003",
                        json.dumps(["KAVITA BISHOI", "PARBATI RICE MILL", "SIBARAM PADHIALI"]),
                        "Monthly BRS and expense audit for Sivanshi Traders IDFC First Bank account.",
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ))
                    cursor.execute("""
                        INSERT INTO bank_accounts (id, client_id, bank_name, account_no, ifsc, branch, account_type)
                        VALUES ('ba-siv-1', ?, 'IDFC FIRST Bank', '55555555306', 'IDFB0060743', 'BERHAMPUR', 'CURRENT')
                    """, (c2_id,))
                    cursor.execute("""
                        INSERT INTO client_books (id, client_id, book_name, software, account_head, opening_balance, linked_bank_account)
                        VALUES ('cb-siv-1', ?, 'IDFC BANK Book (SIVANSHI TRADERS)', 'Tally Prime', 'Bank Accounts', 0.0, '55555555306')
                    """, (c2_id,))

                    conn.commit()

    # ================= Client Master Operations =================
    def save_client(self, client: ClientProfile):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            client.updated_at = datetime.now()
            cursor.execute("""
                INSERT OR REPLACE INTO clients (
                    id, name, entity_type, pan, gstin, email, phone, address,
                    approved_vendors_json, default_auditor_notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client.id, client.name, client.entity_type, client.pan, client.gstin,
                client.email, client.phone, client.address,
                json.dumps(client.approved_vendors), client.default_auditor_notes,
                client.created_at.isoformat(), client.updated_at.isoformat(),
            ))

            cursor.execute("DELETE FROM bank_accounts WHERE client_id = ?", (client.id,))
            for ba in client.bank_accounts:
                cursor.execute("""
                    INSERT INTO bank_accounts (id, client_id, bank_name, account_no, ifsc, branch, account_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ba.id, client.id, ba.bank_name, ba.account_no, ba.ifsc, ba.branch, ba.account_type))

            cursor.execute("DELETE FROM client_books WHERE client_id = ?", (client.id,))
            for cb in client.books:
                cursor.execute("""
                    INSERT INTO client_books (id, client_id, book_name, software, account_head, opening_balance, linked_bank_account)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (cb.id, client.id, cb.book_name, cb.software, cb.account_head, cb.opening_balance, cb.linked_bank_account))

            conn.commit()

    def get_client(self, client_id: str) -> Optional[ClientProfile]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
            row = cursor.fetchone()
            if not row:
                return None

            cursor.execute("SELECT * FROM bank_accounts WHERE client_id = ?", (client_id,))
            ba_rows = cursor.fetchall()
            bank_accounts = [
                BankAccountProfile(
                    id=ba["id"],
                    bank_name=ba["bank_name"],
                    account_no=ba["account_no"],
                    ifsc=ba["ifsc"],
                    branch=ba["branch"],
                    account_type=ba["account_type"],
                )
                for ba in ba_rows
            ]

            cursor.execute("SELECT * FROM client_books WHERE client_id = ?", (client_id,))
            cb_rows = cursor.fetchall()
            books = [
                ClientBookProfile(
                    id=cb["id"],
                    book_name=cb["book_name"],
                    software=cb["software"] or "Tally Prime",
                    account_head=cb["account_head"] or "Bank Accounts",
                    opening_balance=float(cb["opening_balance"] or 0.0),
                    linked_bank_account=cb["linked_bank_account"],
                )
                for cb in cb_rows
            ]

            return ClientProfile(
                id=row["id"],
                name=row["name"],
                entity_type=row["entity_type"],
                pan=row["pan"],
                gstin=row["gstin"],
                email=row["email"],
                phone=row["phone"],
                address=row["address"],
                approved_vendors=json.loads(row["approved_vendors_json"] or "[]"),
                default_auditor_notes=row["default_auditor_notes"],
                bank_accounts=bank_accounts,
                books=books,
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    def list_clients(self) -> List[ClientProfile]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM clients ORDER BY name ASC")
            client_ids = [r["id"] for r in cursor.fetchall()]
        return [self.get_client(cid) for cid in client_ids if self.get_client(cid)]

    def delete_client(self, client_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bank_accounts WHERE client_id = ?", (client_id,))
            cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            conn.commit()

    # ================= Session Operations =================
    def save_session(self, session: ReconciliationSession):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (
                    session_id, client_id, client_name, period_label, auditor_remarks, partner_opinion,
                    created_at, updated_at, config_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.client_id,
                session.client_name,
                session.period_label,
                session.auditor_remarks,
                session.partner_opinion,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.config.model_dump_json(),
            ))

            cursor.execute("DELETE FROM statements WHERE session_id = ?", (session.session_id,))
            cursor.execute("DELETE FROM ledgers WHERE session_id = ?", (session.session_id,))
            cursor.execute("DELETE FROM matches WHERE session_id = ?", (session.session_id,))
            cursor.execute("DELETE FROM audit_flags WHERE session_id = ?", (session.session_id,))
            cursor.execute("DELETE FROM audit_trail WHERE session_id = ?", (session.session_id,))

            for s in session.statements:
                cursor.execute("""
                    INSERT INTO statements (id, session_id, source_row_ref, date, description, amount, type, balance, raw_data_json, matched)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s.id, session.session_id, str(s.source_row_ref), s.date.isoformat(), s.description,
                    str(s.amount), s.type.value, str(s.balance) if s.balance else None,
                    json.dumps(s.raw_data), 1 if s.matched else 0,
                ))

            for l in session.ledger_entries:
                cursor.execute("""
                    INSERT INTO ledgers (id, session_id, source_row_ref, date, description, amount, type, account_name, voucher_type, approver_ref, gstin, tds_section, raw_data_json, matched)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    l.id, session.session_id, str(l.source_row_ref), l.date.isoformat(), l.description,
                    str(l.amount), l.type.value, l.account_name, l.voucher_type, l.approver_ref,
                    l.gstin, l.tds_section, json.dumps(l.raw_data), 1 if l.matched else 0,
                ))

            for m in session.matches:
                cursor.execute("""
                    INSERT INTO matches (id, session_id, statement_tx_id, ledger_entry_id, status, confidence_score, rule_applied, plain_english_reason, manual_override, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    m.id, session.session_id, m.statement_tx_id, m.ledger_entry_id, m.status.value,
                    m.confidence_score, m.rule_applied, m.plain_english_reason,
                    1 if m.manual_override else 0, m.notes,
                ))

            for f in session.audit_flags:
                cursor.execute("""
                    INSERT INTO audit_flags (id, session_id, target_type, source_row_ref, entry_id, rule_name, severity, category, plain_english_reason, suggested_action, entry_summary_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f.id, session.session_id, f.target_type, str(f.source_row_ref), f.entry_id,
                    f.rule_name, f.severity.value, f.category.value, f.plain_english_reason,
                    f.suggested_action, json.dumps(f.entry_summary or {}),
                ))

            for event in session.audit_trail:
                cursor.execute("""
                    INSERT INTO audit_trail (id, session_id, timestamp, action, details, user, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.id, session.session_id, event.timestamp.isoformat(), event.action,
                    event.details, event.user, json.dumps(event.metadata),
                ))

            conn.commit()

    def load_session(self, session_id: str) -> Optional[ReconciliationSession]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            s_row = cursor.fetchone()
            if not s_row:
                return None

            config = AppConfig.model_validate_json(s_row["config_json"])
            session = ReconciliationSession(
                session_id=s_row["session_id"],
                client_id=s_row["client_id"] if "client_id" in s_row.keys() else None,
                client_name=s_row["client_name"],
                period_label=s_row["period_label"],
                auditor_remarks=s_row["auditor_remarks"] or "" if "auditor_remarks" in s_row.keys() else "",
                partner_opinion=s_row["partner_opinion"] or "" if "partner_opinion" in s_row.keys() else "",
                created_at=datetime.fromisoformat(s_row["created_at"]),
                updated_at=datetime.fromisoformat(s_row["updated_at"]),
                config=config,
            )

            cursor.execute("SELECT * FROM statements WHERE session_id = ?", (session_id,))
            for r in cursor.fetchall():
                session.statements.append(
                    StatementTransaction(
                        id=r["id"],
                        source_row_ref=r["source_row_ref"],
                        date=datetime.fromisoformat(r["date"]).date(),
                        description=r["description"],
                        amount=Decimal(r["amount"]),
                        type=TransactionType(r["type"]),
                        balance=Decimal(r["balance"]) if r["balance"] else None,
                        raw_data=json.loads(r["raw_data_json"]),
                        matched=bool(r["matched"]),
                    )
                )

            cursor.execute("SELECT * FROM ledgers WHERE session_id = ?", (session_id,))
            for r in cursor.fetchall():
                session.ledger_entries.append(
                    LedgerEntry(
                        id=r["id"],
                        source_row_ref=r["source_row_ref"],
                        date=datetime.fromisoformat(r["date"]).date(),
                        description=r["description"],
                        amount=Decimal(r["amount"]),
                        type=TransactionType(r["type"]),
                        account_name=r["account_name"],
                        voucher_type=r["voucher_type"],
                        approver_ref=r["approver_ref"],
                        gstin=r["gstin"],
                        tds_section=r["tds_section"],
                        raw_data=json.loads(r["raw_data_json"]),
                        matched=bool(r["matched"]),
                    )
                )

            cursor.execute("SELECT * FROM matches WHERE session_id = ?", (session_id,))
            for r in cursor.fetchall():
                session.matches.append(
                    MatchRecord(
                        id=r["id"],
                        statement_tx_id=r["statement_tx_id"],
                        ledger_entry_id=r["ledger_entry_id"],
                        status=MatchStatus(r["status"]),
                        confidence_score=r["confidence_score"],
                        rule_applied=r["rule_applied"],
                        plain_english_reason=r["plain_english_reason"],
                        manual_override=bool(r["manual_override"]),
                        notes=r["notes"],
                    )
                )

            cursor.execute("SELECT * FROM audit_flags WHERE session_id = ?", (session_id,))
            for r in cursor.fetchall():
                session.audit_flags.append(
                    AuditFlag(
                        id=r["id"],
                        target_type=r["target_type"],
                        source_row_ref=r["source_row_ref"],
                        entry_id=r["entry_id"],
                        rule_name=r["rule_name"],
                        severity=AuditSeverity(r["severity"]),
                        category=AuditCategory(r["category"]),
                        plain_english_reason=r["plain_english_reason"],
                        suggested_action=r["suggested_action"],
                        entry_summary=json.loads(r["entry_summary_json"]),
                    )
                )

            cursor.execute("SELECT * FROM audit_trail WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
            for r in cursor.fetchall():
                session.audit_trail.append(
                    AuditTrailEvent(
                        id=r["id"],
                        timestamp=datetime.fromisoformat(r["timestamp"]),
                        action=r["action"],
                        details=r["details"],
                        user=r["user"],
                        metadata=json.loads(r["metadata_json"]),
                    )
                )

            return session

    def list_sessions(self, client_id: Optional[str] = None) -> List[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if client_id:
                cursor.execute("SELECT session_id, client_id, client_name, period_label, updated_at FROM sessions WHERE client_id = ? ORDER BY updated_at DESC", (client_id,))
            else:
                cursor.execute("SELECT session_id, client_id, client_name, period_label, updated_at FROM sessions ORDER BY updated_at DESC")
            return [dict(r) for r in cursor.fetchall()]
