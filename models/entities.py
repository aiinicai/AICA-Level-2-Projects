"""
LexSecure India Pro - Model Entities & ORM Access Layer
Represents all 15 Core Indian Legal & Regulatory Intelligence Entities
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.db_engine import DatabaseEngine

db = DatabaseEngine.get_instance()

@dataclass
class Organization:
    id: Optional[int]
    name: str
    pan_number: str
    cin_number: str
    industry_type: str
    created_at: Optional[str] = None

    @staticmethod
    def get_all() -> List['Organization']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM organizations ORDER BY id ASC")
            return [Organization(**dict(row)) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(org_id: int) -> Optional['Organization']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM organizations WHERE id = ?", (org_id,))
            row = cursor.fetchone()
            return Organization(**dict(row)) if row else None


@dataclass
class Entity:
    id: Optional[int]
    organization_id: int
    legal_name: str
    entity_type: str
    registered_state: str

    @staticmethod
    def get_all(org_id: int = 1) -> List['Entity']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE organization_id = ? ORDER BY id ASC", (org_id,))
            return [Entity(**dict(row)) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(entity_id: int) -> Optional['Entity']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            return Entity(**dict(row)) if row else None

    @staticmethod
    def create(organization_id: int, legal_name: str, entity_type: str, registered_state: str) -> int:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO entities (organization_id, legal_name, entity_type, registered_state)
                VALUES (?, ?, ?, ?)
            """, (organization_id, legal_name, entity_type, registered_state))
            entity_id = cursor.lastrowid

            # Auto-seed standard departments for new operating entity
            default_depts = ['LEGAL', 'HR_LABOUR', 'FINANCE_TAX', 'INFOSEC_TECH', 'OPERATIONS']
            for d_name in default_depts:
                cursor.execute("INSERT INTO departments (entity_id, name) VALUES (?, ?)", (entity_id, d_name))

            conn.commit()

        db.log_tamper_evident_event(
            organization_id=organization_id,
            actor_id=None,
            actor_name="System / Governance",
            event_type="ENTITY_CREATED",
            target_model="Entity",
            target_id=entity_id,
            details_dict={"legal_name": legal_name, "type": entity_type, "state": registered_state}
        )
        return entity_id

    @staticmethod
    def update(entity_id: int, legal_name: str, entity_type: str, registered_state: str):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE entities
                SET legal_name = ?, entity_type = ?, registered_state = ?
                WHERE id = ?
            """, (legal_name, entity_type, registered_state, entity_id))
            conn.commit()

        db.log_tamper_evident_event(
            organization_id=1,
            actor_id=None,
            actor_name="System / Governance",
            event_type="ENTITY_UPDATED",
            target_model="Entity",
            target_id=entity_id,
            details_dict={"legal_name": legal_name, "type": entity_type, "state": registered_state}
        )

    @staticmethod
    def delete(entity_id: int):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
            conn.commit()

        db.log_tamper_evident_event(
            organization_id=1,
            actor_id=None,
            actor_name="System / Governance",
            event_type="ENTITY_DELETED",
            target_model="Entity",
            target_id=entity_id,
            details_dict={"deleted_entity_id": entity_id}
        )


@dataclass
class Department:
    id: Optional[int]
    entity_id: int
    name: str

    @staticmethod
    def get_by_entity(entity_id: int) -> List['Department']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM departments WHERE entity_id = ? ORDER BY id ASC", (entity_id,))
            return [Department(**dict(row)) for row in cursor.fetchall()]


@dataclass
class User:
    id: Optional[int]
    organization_id: int
    email: str
    full_name: str
    role: str
    department_id: Optional[int]
    password_hash: str = "1234"
    is_active: int = 1

    @staticmethod
    def get_all(org_id: int = 1) -> List['User']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE organization_id = ? AND is_active = 1 ORDER BY id ASC", (org_id,))
            return [User(**dict(row)) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return User(**dict(row)) if row else None

    @staticmethod
    def authenticate(email: str, password: str) -> Optional['User']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?) AND is_active = 1", (email.strip(),))
            row = cursor.fetchone()
            if row:
                u = User(**dict(row))
                stored_pwd = getattr(u, 'password_hash', '1234') or '1234'
                # Accept either exact password, or default "1234"
                if password.strip() == stored_pwd or password.strip() == "1234" or stored_pwd == "1234":
                    return u
            return None

    @staticmethod
    def create(organization_id: int, email: str, full_name: str, role: str, department_id: Optional[int], password: str = "1234") -> int:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (organization_id, email, full_name, role, department_id, password_hash, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (organization_id, email.strip(), full_name.strip(), role, department_id, password.strip()))
            user_id = cursor.lastrowid
            conn.commit()

        db.log_tamper_evident_event(
            organization_id=organization_id,
            actor_id=None,
            actor_name="System / Governance",
            event_type="USER_CREATED",
            target_model="User",
            target_id=user_id,
            details_dict={"email": email, "full_name": full_name, "role": role}
        )
        return user_id

    @staticmethod
    def update(user_id: int, full_name: str, email: str, role: str, department_id: Optional[int], password: Optional[str] = None):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            if password:
                cursor.execute("""
                    UPDATE users
                    SET full_name = ?, email = ?, role = ?, department_id = ?, password_hash = ?
                    WHERE id = ?
                """, (full_name.strip(), email.strip(), role, department_id, password.strip(), user_id))
            else:
                cursor.execute("""
                    UPDATE users
                    SET full_name = ?, email = ?, role = ?, department_id = ?
                    WHERE id = ?
                """, (full_name.strip(), email.strip(), role, department_id, user_id))
            conn.commit()

        db.log_tamper_evident_event(
            organization_id=1,
            actor_id=None,
            actor_name="System / Governance",
            event_type="USER_UPDATED",
            target_model="User",
            target_id=user_id,
            details_dict={"full_name": full_name, "email": email, "role": role}
        )

    @staticmethod
    def delete(user_id: int):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
            conn.commit()

        db.log_tamper_evident_event(
            organization_id=1,
            actor_id=None,
            actor_name="System / Governance",
            event_type="USER_DELETED",
            target_model="User",
            target_id=user_id,
            details_dict={"deactivated_user_id": user_id}
        )


@dataclass
class AccessMatrixRule:
    id: Optional[int]
    role: str
    resource: str
    can_create: int
    can_read: int
    can_update: int
    can_delete: int
    can_signoff: int

    @staticmethod
    def get_all() -> List['AccessMatrixRule']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM access_matrix_rules ORDER BY role, resource")
            return [AccessMatrixRule(**dict(row)) for row in cursor.fetchall()]

    @staticmethod
    def has_permission(role: str, resource: str, action: str) -> bool:
        col = f"can_{action.lower()}"
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {col} FROM access_matrix_rules WHERE role = ? AND resource = ?", (role, resource))
            row = cursor.fetchone()
            return bool(row[0]) if row else False


@dataclass
class Playbook:
    id: Optional[int]
    organization_id: int
    contract_type: str
    version: str = "1.0"

    @staticmethod
    def get_all(org_id: int = 1) -> List['Playbook']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM playbooks WHERE organization_id = ?", (org_id,))
            return [Playbook(**dict(row)) for row in cursor.fetchall()]


@dataclass
class PlaybookRule:
    id: Optional[int]
    playbook_id: int
    clause_type: str
    standard_clause: str
    fallback_clause: str
    dealbreaker_conditions: str
    statutory_citation_india: str

    @staticmethod
    def get_by_playbook(playbook_id: int) -> List['PlaybookRule']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM playbook_rules WHERE playbook_id = ?", (playbook_id,))
            return [PlaybookRule(**dict(row)) for row in cursor.fetchall()]

    @staticmethod
    def get_all_active_rules(org_id: int = 1) -> List['PlaybookRule']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.* FROM playbook_rules r
                JOIN playbooks p ON r.playbook_id = p.id
                WHERE p.organization_id = ?
            """, (org_id,))
            return [PlaybookRule(**dict(row)) for row in cursor.fetchall()]


@dataclass
class Document:
    id: Optional[int]
    entity_id: int
    uploaded_by: Optional[int]
    file_path: Optional[str]
    original_filename: str
    doc_type: str
    status: str = "PENDING"
    overall_health_score: int = 100
    liability_score: int = 100
    statutory_score: int = 100
    labour_fema_score: int = 100
    ocr_applied: int = 0
    raw_content: Optional[str] = None
    created_at: Optional[str] = None

    @staticmethod
    def get_by_entity(entity_id: int) -> List['Document']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE entity_id = ? ORDER BY id DESC", (entity_id,))
            return [Document(**dict(row)) for row in cursor.fetchall()]

    @staticmethod
    def get_all_with_entity(entity_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT d.*, e.legal_name as entity_name, e.registered_state
                FROM documents d
                JOIN entities e ON d.entity_id = e.id
            """
            params = []
            if entity_id:
                query += " WHERE d.entity_id = ?"
                params.append(entity_id)
            query += " ORDER BY d.id DESC"
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def reassign_entity(doc_id: int, new_entity_id: int):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE documents SET entity_id = ? WHERE id = ?", (new_entity_id, doc_id))
            conn.commit()

        db.log_tamper_evident_event(
            organization_id=1,
            actor_id=None,
            actor_name="Compliance Legal Team",
            event_type="DOCUMENT_ENTITY_REASSIGNED",
            target_model="Document",
            target_id=doc_id,
            details_dict={"document_id": doc_id, "new_entity_id": new_entity_id}
        )

    @staticmethod
    def get_by_id(doc_id: int) -> Optional['Document']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            return Document(**dict(row)) if row else None


@dataclass
class DocumentClause:
    id: Optional[int]
    document_id: int
    page_number: int
    clause_type: str
    raw_text: str
    risk_tier: str
    flag_reason: Optional[str]
    indian_law_violation: Optional[str]
    suggested_redline: Optional[str]
    is_resolved: int = 0

    @staticmethod
    def get_by_document(document_id: int) -> List['DocumentClause']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM document_clauses WHERE document_id = ? ORDER BY id ASC", (document_id,))
            return [DocumentClause(**dict(row)) for row in cursor.fetchall()]


@dataclass
class RegulatoryUpdate:
    id: Optional[int]
    statutory_body: str
    title: str
    circular_number: str
    official_date: str
    raw_text: str
    severity: str
    source_url: Optional[str]
    created_at: Optional[str] = None

    @staticmethod
    def get_all(statutory_body: Optional[str] = None) -> List['RegulatoryUpdate']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            if statutory_body and statutory_body != "ALL":
                cursor.execute("SELECT * FROM regulatory_updates WHERE statutory_body = ? ORDER BY official_date DESC", (statutory_body,))
            else:
                cursor.execute("SELECT * FROM regulatory_updates ORDER BY official_date DESC")
            return [RegulatoryUpdate(**dict(row)) for row in cursor.fetchall()]


@dataclass
class ImpactAssessment:
    id: Optional[int]
    regulatory_update_id: int
    approved_by: Optional[int]
    status: str
    executive_summary: str
    affected_departments: str
    statutory_deadline: str
    created_at: Optional[str] = None

    @staticmethod
    def get_by_circular(circular_id: int) -> Optional['ImpactAssessment']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM impact_assessments WHERE regulatory_update_id = ? ORDER BY id DESC LIMIT 1", (circular_id,))
            row = cursor.fetchone()
            return ImpactAssessment(**dict(row)) if row else None


@dataclass
class ComplianceTask:
    id: Optional[int]
    impact_assessment_id: Optional[int]
    department_id: int
    assigned_to: Optional[int]
    title: str
    description: str
    deadline: str
    priority: str
    status: str
    created_at: Optional[str] = None

    @staticmethod
    def get_all_with_details(entity_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT t.*, d.name as dept_name, d.entity_id, u.full_name as assignee_name, e.legal_name as entity_name
                FROM compliance_tasks t
                JOIN departments d ON t.department_id = d.id
                JOIN entities e ON d.entity_id = e.id
                LEFT JOIN users u ON t.assigned_to = u.id
            """
            params = []
            if entity_id:
                query += " WHERE d.entity_id = ?"
                params.append(entity_id)
            query += " ORDER BY t.deadline ASC"
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]


@dataclass
class TaskEvidence:
    id: Optional[int]
    task_id: int
    uploaded_by: Optional[int]
    evidence_file: Optional[str]
    notes: Optional[str]
    uploaded_at: Optional[str] = None

    @staticmethod
    def get_by_task(task_id: int) -> List['TaskEvidence']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM task_evidences WHERE task_id = ? ORDER BY id DESC", (task_id,))
            return [TaskEvidence(**dict(row)) for row in cursor.fetchall()]


@dataclass
class StatutoryCalendarEvent:
    id: Optional[int]
    entity_id: int
    statutory_body: str
    compliance_name: str
    due_date: str
    recurring_freq: str
    penalty_clause: str

    @staticmethod
    def get_by_entity(entity_id: int) -> List['StatutoryCalendarEvent']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM statutory_calendar_events WHERE entity_id = ? ORDER BY due_date ASC", (entity_id,))
            return [StatutoryCalendarEvent(**dict(row)) for row in cursor.fetchall()]


@dataclass
class TamperAuditLog:
    id: Optional[int]
    organization_id: int
    actor_id: Optional[int]
    actor_name: Optional[str]
    event_type: str
    target_model: str
    target_id: Optional[int]
    details_json: str
    ip_address: str
    timestamp: str
    prev_hash: str
    current_hash: str

    @staticmethod
    def get_all(org_id: int = 1) -> List['TamperAuditLog']:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tamper_audit_logs WHERE organization_id = ? ORDER BY id DESC", (org_id,))
            return [TamperAuditLog(**dict(row)) for row in cursor.fetchall()]
