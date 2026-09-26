"""
AuditVault - Database Connection, Session Management, and Auto-Initialization.
Creates tables and seeds default Admin, Managers, Team Members, Clients, and Engagements.
Ensures both CA firm and enterprise demo profiles are fully populated.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import hashlib
import json

from models import (
    Base, User, Client, Team, TeamMemberMapping, Engagement,
    EngagementTeamAssignment, IDRItem, RCMLineItem, WorkingPaper,
    Observation, CommentThread, AuditTrailEntry, Notification
)
from auth import hash_password
from utils import (
    ensure_vault_directories, get_line_item_storage_dir,
    current_indian_date_str, current_indian_timestamp_str,
    save_uploaded_file, sanitize_folder_name
)

# SQLite database file path in the project root
DB_FILE = Path(__file__).resolve().parent / "auditvault.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Thread-safe engine for Streamlit
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
SessionLocal = scoped_session(SessionFactory)


def get_db():
    """Yield a database session."""
    return SessionLocal()


def init_db():
    """
    Initialize database tables and pre-populate with default roles,
    users, sample clients, teams, engagements, IDRs, and RCM items.
    """
    ensure_vault_directories()
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_schema_migrations()
    db = SessionLocal()

    # Check and seed baseline demo data
    seed_data(db)
    _backfill_audit_integrity_hashes(db)
    db.close()


def _apply_lightweight_schema_migrations():
    """Add backward-compatible columns required by newer AuditVault releases."""
    with engine.begin() as connection:
        rcm_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(rcm_items)").fetchall()
        }
        if rcm_columns and "sub_process" not in rcm_columns:
            connection.exec_driver_sql("ALTER TABLE rcm_items ADD COLUMN sub_process VARCHAR(150)")

        user_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        }
        if user_columns and "is_deleted" not in user_columns:
            connection.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0"
            )
        if user_columns and "deleted_at" not in user_columns:
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN deleted_at DATETIME")

        audit_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(audit_trail)").fetchall()
        }
        audit_additions = {
            "actor_role": "VARCHAR(50)",
            "target_role": "VARCHAR(50)",
            "target_name": "VARCHAR(150)",
            "action_category": "VARCHAR(50)",
            "rbac_rule_applied": "VARCHAR(255)",
            "previous_state_json": "TEXT",
            "new_state_json": "TEXT",
            "metadata_json": "TEXT",
            "previous_hash": "VARCHAR(64)",
            "integrity_hash": "VARCHAR(64)",
        }
        for column_name, column_type in audit_additions.items():
            if audit_columns and column_name not in audit_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE audit_trail ADD COLUMN {column_name} {column_type}"
                )


def _backfill_audit_integrity_hashes(db):
    """Create a deterministic hash chain for legacy and newly seeded audit rows."""
    entries = db.query(AuditTrailEntry).order_by(AuditTrailEntry.id.asc()).all()
    previous_hash = "GENESIS"
    changed = False
    for entry in entries:
        payload = {
            "id": entry.id,
            "timestamp": entry.timestamp_str,
            "action": entry.action_type,
            "entity": entry.target_entity,
            "target_id": entry.target_id or "",
            "description": entry.description,
            "user_id": entry.user_id,
            "actor": entry.acting_user_name,
            "previous_hash": previous_hash,
        }
        expected_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        if entry.previous_hash != previous_hash or entry.integrity_hash != expected_hash:
            entry.previous_hash = previous_hash
            entry.integrity_hash = expected_hash
            changed = True
        previous_hash = expected_hash
    if changed:
        db.commit()


def seed_data(db):
    """Seed comprehensive demo data for immediate testing out-of-the-box."""
    now = datetime.utcnow()
    t_str = current_indian_timestamp_str()

    # 1. Create Default Users (Ensure Admin, Managers, Auditors exist)
    # Admin
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            password_hash=hash_password("admin123"),
            name="Sunil Mehra",
            age=42,
            designation="Chief Audit Executive / IT Admin",
            email="admin@auditvault.in",
            phone="+91 98200 11223",
            role="Admin",
            theme_preference="light",
            is_first_login=False,
            created_at=now
        )
        db.add(admin_user)
        db.commit()

    # Manager: Rohit Sharma
    mgr_rohit = db.query(User).filter(User.username == "rohit.sharma").first()
    if not mgr_rohit:
        mgr_rohit = User(
            username="rohit.sharma",
            password_hash=hash_password("manager123"),
            name="Rohit Sharma",
            age=36,
            designation="Internal Audit Manager",
            email="rohit.sharma@firm.in",
            phone="+91 98111 22334",
            role="Manager",
            theme_preference="light",
            is_first_login=False,
            created_at=now
        )
        db.add(mgr_rohit)
        db.commit()

    # Manager: CA Rajesh Sharma
    mgr1 = db.query(User).filter(User.username == "manager.rajesh").first()
    if not mgr1:
        mgr1 = User(
            username="manager.rajesh",
            password_hash=hash_password("manager123"),
            name="CA Rajesh Sharma",
            age=38,
            designation="Senior Audit Manager & Partner",
            email="rajesh.sharma@auditvault.in",
            phone="+91 98199 44556",
            role="Manager",
            theme_preference="light",
            is_first_login=False,
            created_at=now
        )
        db.add(mgr1)
        db.commit()

    # Auditor: Anita Kulkarni
    aud_anita = db.query(User).filter(User.username == "anita.kulkarni").first()
    if not aud_anita:
        aud_anita = User(
            username="anita.kulkarni",
            password_hash=hash_password("auditor123"),
            name="Anita Kulkarni",
            age=28,
            designation="Lead Internal Auditor",
            email="anita.kulkarni@firm.in",
            phone="+91 98222 33445",
            role="Team Member",
            theme_preference="light",
            is_first_login=False,
            created_at=now
        )
        db.add(aud_anita)
        db.commit()

    # Auditor: Vikram N.
    aud_vikram = db.query(User).filter(User.username == "vikram.n").first()
    if not aud_vikram:
        aud_vikram = User(
            username="vikram.n",
            password_hash=hash_password("auditor123"),
            name="Vikram N.",
            age=26,
            designation="Audit Associate",
            email="vikram.n@firm.in",
            phone="+91 98333 44556",
            role="Team Member",
            theme_preference="light",
            is_first_login=False,
            created_at=now
        )
        db.add(aud_vikram)
        db.commit()

    # Auditor: Neha Patil
    aud_neha = db.query(User).filter(User.username == "neha.patil").first()
    if not aud_neha:
        aud_neha = User(
            username="neha.patil",
            password_hash=hash_password("auditor123"),
            name="Neha Patil",
            age=25,
            designation="IT Systems Auditor (CISA)",
            email="neha.patil@firm.in",
            phone="+91 98444 55667",
            role="Team Member",
            theme_preference="light",
            is_first_login=False,
            created_at=now
        )
        db.add(aud_neha)
        db.commit()

    # Read-only-style presentation account. Login is bound to its first device.
    demo_viewer = db.query(User).filter(User.username == "demo.viewer").first()
    if not demo_viewer:
        demo_viewer = User(
            username="demo.viewer",
            password_hash=hash_password("AuditVault@Demo2026"),
            name="Demo Viewer",
            age=30,
            designation="Presentation Auditor",
            email="demo.viewer@auditvault.local",
            phone="",
            role="Team Member",
            theme_preference="light",
            is_first_login=False,
            created_at=now
        )
        db.add(demo_viewer)
        db.commit()

    # 2. Clients
    clients_to_create = [
        ("Sundaram Textiles Ltd.", "Textiles & Manufacturing", "K. Sundaram (CFO)", "sundaram@sundaramtextiles.com", "+91 44 2855 1122", "12 Club House Road, Anna Salai, Chennai - 600002"),
        ("Kaveri Pharma Pvt. Ltd.", "Pharmaceuticals & Healthcare", "Dr. V. Raman", "v.raman@kaveripharma.com", "+91 80 4123 5566", "Biotech City, Electronic City Phase 1, Bengaluru - 560100"),
        ("Mehta & Sons Traders", "Retail & Trading", "Rajesh Mehta", "rmehta@mehtasons.com", "+91 22 2345 6789", "Charni Road, Opera House, Mumbai - 400004"),
        ("Orbit Logistics Corp.", "Logistics & Supply Chain", "G. S. Brar", "gsbrar@orbitlogistics.com", "+91 11 4567 8900", "Transport Nagar, New Delhi - 110037"),
        ("Tata Global Infotech Ltd.", "Information Technology & ITES", "Venkatesh Raman", "v.raman@tataglobal.com", "+91 22 6677 8899", "Maker Chambers IV, Nariman Point, Mumbai - 400021"),
        ("HDFC Financial Services Ltd.", "Banking & BFSI", "Ritu Singhania", "ritu.s@hdfcfin.com", "+91 22 4567 1122", "HDFC House, Churchgate, Mumbai - 400020")
    ]

    client_map = {}
    for c_name, c_ind, c_spoc, c_mail, c_phone, c_addr in clients_to_create:
        c_obj = db.query(Client).filter(Client.name == c_name).first()
        if not c_obj:
            c_obj = Client(
                name=c_name,
                industry=c_ind,
                contact_person=c_spoc,
                contact_email=c_mail,
                contact_phone=c_phone,
                address=c_addr,
                created_at=now
            )
            db.add(c_obj)
            db.commit()
        client_map[c_name] = c_obj

    # 3. Teams
    teams_to_create = [
        ("Team 1 - BFSI & Corporate Governance", "Focused on statutory compliances, treasury, and internal financial controls.", [aud_anita.user_id, aud_vikram.user_id, aud_neha.user_id]),
        ("Team 2 - ITGC & Digital Forensics", "Specializing in IT General Controls, SAP access, and cybersecurity audits.", [aud_vikram.user_id, aud_neha.user_id]),
        ("Team 3 - Supply Chain & Operations", "Procure-to-Pay (P2P), inventory, and logistics verification.", [aud_anita.user_id, aud_vikram.user_id])
    ]

    for t_name, t_desc, member_ids in teams_to_create:
        t_obj = db.query(Team).filter(Team.name == t_name).first()
        if not t_obj:
            t_obj = Team(
                name=t_name,
                description=t_desc,
                created_by_manager_id=mgr_rohit.user_id,
                created_at=now
            )
            db.add(t_obj)
            db.commit()

            for uid in member_ids:
                db.add(TeamMemberMapping(team_id=t_obj.team_id, user_id=uid))
            db.commit()

    # 4. Engagements
    # Primary Engagement: Sundaram Textiles Ltd.
    sundaram_client = client_map.get("Sundaram Textiles Ltd.")
    eng_sundaram = db.query(Engagement).filter(Engagement.engagement_code == "ENG-2026-014").first()
    if not eng_sundaram and sundaram_client:
        eng_sundaram = Engagement(
            engagement_code="ENG-2026-014",
            client_id=sundaram_client.client_id,
            title="Procure-to-Pay (P2P) Internal Audit",
            process_under_audit="Procure-to-Pay",
            audit_period_start="01-04-2025",
            audit_period_end="31-03-2026",
            scope="Comprehensive audit of vendor onboarding, purchase orders, 3-way matching, and disbursements.",
            areas_covered="Vendor Master, Purchase Requisitions, PO DOA Approvals, Goods Receipts (GRN), Invoicing",
            estimated_budget=1450000.0,
            deadline="31-10-2026",
            status="In Progress",
            manager_id=mgr_rohit.user_id,
            engagement_letter_filename="Sundaram_P2P_Engagement_Letter.pdf",
            is_locked=False,
            created_at=now
        )
        db.add(eng_sundaram)
        db.commit()

        # Assignments
        db.add_all([
            EngagementTeamAssignment(engagement_id=eng_sundaram.engagement_id, user_id=aud_anita.user_id, role_in_audit="Lead Auditor"),
            EngagementTeamAssignment(engagement_id=eng_sundaram.engagement_id, user_id=aud_vikram.user_id, role_in_audit="Field Auditor"),
            EngagementTeamAssignment(engagement_id=eng_sundaram.engagement_id, user_id=aud_neha.user_id, role_in_audit="Reviewer")
        ])
        db.commit()

        # RCM items for Sundaram
        rcm_sundaram_items = [
            ("P2P-01", "Vendor Onboarding & Due Diligence", "RSK-01", "Purchase orders raised without approval or exceeding DOA limits.", "CTL-01", "System-enforced PO approval matrix requiring CFO sign-off above ₹ 5,00,000.", "Preventive", "Sample 25 POs and verify approvals against DOA matrix…", aud_anita.user_id, "In Progress", True),
            ("P2P-02", "Purchase Order Issuance", "RSK-02", "POs split to circumvent Delegation of Authority thresholds.", "CTL-02", "System blocks split POs to the same vendor within 30 days.", "Detective", "Extract procurement dump and verify potential split POs.", aud_vikram.user_id, "Fieldwork", True),
            ("P2P-03", "3-Way Invoice Matching", "RSK-03", "Payment released without verified physical receipt of goods (GRN).", "CTL-03", "SAP S/4HANA enforces automated 3-way match (PO, GRN, Vendor Invoice).", "Preventive", "Sample 30 invoice vouchers. Inspect GRN and warehouse gate pass.", aud_anita.user_id, "Submitted", True),
            ("P2P-04", "Payment Disbursements", "RSK-04", "Duplicate payments or incorrect beneficiary bank accounts.", "CTL-04", "Corporate net banking enforces maker-checker with OTP token authorization.", "Preventive", "Inspect corporate net banking audit log for 100% payments > ₹ 10 Lakhs.", aud_anita.user_id, "Reviewed", True),
        ]

        for lid, proc, r_id, r_desc, c_id, c_desc, c_type, a_proc, resp_id, stt, lck in rcm_sundaram_items:
            rcm_row = RCMLineItem(
                engagement_id=eng_sundaram.engagement_id,
                line_item_id=lid,
                process_area=proc,
                risk_id=r_id,
                risk_description=r_desc,
                control_id=c_id,
                control_description=c_desc,
                control_type=c_type,
                audit_procedure=a_proc,
                person_responsible_id=resp_id,
                status=stt,
                manager_locked=lck,
                review_status="Reviewed" if stt == "Reviewed" else "Pending"
            )
            db.add(rcm_row)
            db.commit()

            # Seed Observation for P2P-01
            if lid == "P2P-01":
                db.add(Observation(
                    engagement_id=eng_sundaram.engagement_id,
                    rcm_item_id=rcm_row.id,
                    observation_text="In 4 out of 25 sampled contracts, milestone approvals were documented retrospectively 12 days after invoice generation.",
                    risk_rating="High",
                    recommendation="Enforce a hard system check in SAP ERP preventing invoice generation without signed Delivery Acceptance.",
                    management_response="IT team tasked to enforce automated validation by 15-October-2026.",
                    updated_by_id=aud_anita.user_id,
                    updated_by_name=aud_anita.name
                ))

                # Seed Comments
                db.add_all([
                    CommentThread(
                        engagement_id=eng_sundaram.engagement_id,
                        rcm_item_id=rcm_row.id,
                        sender_id=mgr_rohit.user_id,
                        sender_name="Rohit (Manager)",
                        sender_role="Manager",
                        message="Please explain the 4 POs approved after invoice date.",
                        is_query=True,
                        timestamp=datetime(2026, 9, 23, 14, 20)
                    ),
                    CommentThread(
                        engagement_id=eng_sundaram.engagement_id,
                        rcm_item_id=rcm_row.id,
                        sender_id=aud_anita.user_id,
                        sender_name="Anita",
                        sender_role="Team Member",
                        message="Vendor confirmation attached in today's folder.",
                        is_query=False,
                        timestamp=datetime(2026, 9, 24, 10, 5)
                    )
                ])

                # Seed Sample Working Paper
                try:
                    p2p_dir = get_line_item_storage_dir(eng_sundaram.engagement_id, sundaram_client.name, "P2P-01", "24-09-2026")
                    sample_file = p2p_dir / "PO_sample.xlsx"
                    with open(sample_file, "w", encoding="utf-8") as f:
                        f.write("P2P Sample Testing Sheet - PO approvals\nTesting conducted by Anita Kulkarni")

                    db.add(WorkingPaper(
                        engagement_id=eng_sundaram.engagement_id,
                        rcm_item_id=rcm_row.id,
                        line_item_id="P2P-01",
                        filename="PO_sample.xlsx",
                        file_path=str(sample_file),
                        file_size_bytes=sample_file.stat().st_size,
                        version_date="24-09-2026",
                        uploaded_by_id=aud_anita.user_id,
                        uploaded_by_name=aud_anita.name,
                        uploaded_at=datetime(2026, 9, 24, 10, 5)
                    ))
                except Exception:
                    pass

        # Seed IDR items for Sundaram (so Export IDR downloads real data)
        db.add_all([
            IDRItem(engagement_id=eng_sundaram.engagement_id, item_code="IDR-01", requirement_description="Vendor Master Database with GSTIN and PAN details", department_spoc="Procurement Head", priority="High", target_date="15-08-2026", status="Received", updated_by_name="Anita Kulkarni"),
            IDRItem(engagement_id=eng_sundaram.engagement_id, item_code="IDR-02", requirement_description="Purchase Order Register for FY 2025-26 in Excel format", department_spoc="Commercial Lead", priority="High", target_date="20-08-2026", status="Received", updated_by_name="Anita Kulkarni"),
            IDRItem(engagement_id=eng_sundaram.engagement_id, item_code="IDR-03", requirement_description="Delegation of Authority (DOA) financial approval matrix", department_spoc="CFO Office", priority="High", target_date="10-08-2026", status="Received", updated_by_name="Rohit Sharma"),
            IDRItem(engagement_id=eng_sundaram.engagement_id, item_code="IDR-04", requirement_description="Listing of retrospective PO approvals and emergency purchases", department_spoc="Procurement Head", priority="Medium", target_date="25-08-2026", status="Partially Received", updated_by_name="Anita Kulkarni"),
            IDRItem(engagement_id=eng_sundaram.engagement_id, item_code="IDR-05", requirement_description="3-Way Match Exception and Tolerance Override Reports from SAP", department_spoc="IT ERP Lead", priority="Medium", target_date="30-08-2026", status="Requested", updated_by_name="Anita Kulkarni"),
        ])
        db.commit()

    # Ensure the device-bound demo viewer can see one populated engagement.
    if eng_sundaram and demo_viewer:
        demo_assignment = db.query(EngagementTeamAssignment).filter(
            EngagementTeamAssignment.engagement_id == eng_sundaram.engagement_id,
            EngagementTeamAssignment.user_id == demo_viewer.user_id
        ).first()
        if not demo_assignment:
            db.add(EngagementTeamAssignment(
                engagement_id=eng_sundaram.engagement_id,
                user_id=demo_viewer.user_id,
                role_in_audit="Demo Observer"
            ))
            db.commit()

    # Kaveri Pharma Pvt. Ltd. (Overdue)
    kaveri_client = client_map.get("Kaveri Pharma Pvt. Ltd.")
    if kaveri_client and not db.query(Engagement).filter(Engagement.engagement_code == "ENG-2026-015").first():
        db.add(Engagement(
            engagement_code="ENG-2026-015",
            client_id=kaveri_client.client_id,
            title="Inventory Management & Valuation Review",
            process_under_audit="Inventory Mgmt",
            audit_period_start="01-04-2025",
            audit_period_end="31-03-2026",
            scope="Review of warehouse storage, physical stock-taking, batch expiry management, and slow-moving provisions.",
            areas_covered="Finished Goods, Active Pharmaceutical Ingredients (API), Cold Chain Logistics",
            estimated_budget=1820000.0,
            deadline="18-09-2026",
            status="Overdue",
            manager_id=mgr_rohit.user_id,
            is_locked=False,
            created_at=now
        ))
        db.commit()

    # Mehta & Sons Traders (Completed)
    mehta_client = client_map.get("Mehta & Sons Traders")
    if mehta_client and not db.query(Engagement).filter(Engagement.engagement_code == "ENG-2026-016").first():
        db.add(Engagement(
            engagement_code="ENG-2026-016",
            client_id=mehta_client.client_id,
            title="Payroll & Statutory Compliances Audit",
            process_under_audit="Payroll",
            audit_period_start="01-04-2026",
            audit_period_end="30-06-2026",
            scope="Review of attendance records, salary processing, PF, ESI, Professional Tax, and TDS deductions.",
            areas_covered="HR Master Data, Overtime Approvals, Full & Final Settlements",
            estimated_budget=950000.0,
            deadline="30-08-2026",
            status="Completed",
            manager_id=mgr_rohit.user_id,
            is_locked=True,
            completed_at=now,
            created_at=now
        ))
        db.commit()

    # Orbit Logistics Corp. (Draft)
    orbit_client = client_map.get("Orbit Logistics Corp.")
    if orbit_client and not db.query(Engagement).filter(Engagement.engagement_code == "ENG-2026-017").first():
        db.add(Engagement(
            engagement_code="ENG-2026-017",
            client_id=orbit_client.client_id,
            title="Fixed Assets & Fleet Management Audit",
            process_under_audit="Fixed Assets",
            audit_period_start="01-07-2025",
            audit_period_end="30-06-2026",
            scope="Review of fleet vehicle capitalization, physical verification, fuel cards, and maintenance billing.",
            areas_covered="Fleet Asset Register, GPS Tracking Logs, Tyre Life Tracking",
            estimated_budget=1250000.0,
            deadline="15-11-2026",
            status="Draft",
            manager_id=mgr_rohit.user_id,
            is_locked=False,
            created_at=now
        ))
        db.commit()

    # Initial Audit Trail Records
    if db.query(AuditTrailEntry).count() == 0:
        db.add_all([
            AuditTrailEntry(
                timestamp=datetime(2026, 9, 23, 9, 1),
                timestamp_str="23-09-2026 09:01",
                action_type="LOGIN",
                target_entity="Session",
                target_id="rohit.sharma",
                description="Rohit Sharma signed in.",
                user_id=mgr_rohit.user_id,
                acting_user_name="Rohit S."
            ),
            AuditTrailEntry(
                timestamp=datetime(2026, 9, 23, 17, 40),
                timestamp_str="23-09-2026 17:40",
                action_type="STATUS_CHANGE",
                target_entity="Engagement",
                target_id="ENG-2026-011",
                description="ENG-2026-011 reopened with justification memo.",
                user_id=mgr_rohit.user_id,
                acting_user_name="Rohit S."
            ),
            AuditTrailEntry(
                timestamp=datetime(2026, 9, 24, 9, 12),
                timestamp_str="24-09-2026 09:12",
                action_type="IMPERSONATION",
                target_entity="User",
                target_id="vikram.n",
                description="Admin Sunil Mehra accessed AuditVault as Vikram N.",
                user_id=aud_vikram.user_id,
                acting_user_name="Admin (as Vikram N.)",
                true_admin_id=admin_user.user_id,
                true_admin_name=admin_user.name
            ),
            AuditTrailEntry(
                timestamp=datetime(2026, 9, 24, 10, 5),
                timestamp_str="24-09-2026 10:05",
                action_type="UPLOAD",
                target_entity="WorkingPaper",
                target_id="PO_sample.xlsx",
                description="Uploaded PO_sample.xlsx → P2P-01 (saved in /P2P-01/24-09-2026/).",
                user_id=aud_anita.user_id,
                acting_user_name="Anita K."
            )
        ])
        db.commit()
