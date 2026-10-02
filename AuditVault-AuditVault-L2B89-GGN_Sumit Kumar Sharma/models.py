"""
AuditVault - Database Models (SQLAlchemy ORM)
Designed for SQLite with full compatibility for PostgreSQL migration.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=True)
    designation = Column(String(100), nullable=True)
    email = Column(String(120), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(String(30), nullable=False)  # "Admin", "Manager", "Team Member"
    profile_picture = Column(String(255), nullable=True)
    theme_preference = Column(String(20), default="light")  # "light", "dark", "system"
    is_first_login = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    created_engagements = relationship("Engagement", back_populates="manager", foreign_keys="Engagement.manager_id")
    assigned_engagements = relationship("EngagementTeamAssignment", back_populates="user")
    comments = relationship("CommentThread", back_populates="sender")
    notifications = relationship("Notification", back_populates="user")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Client(Base):
    __tablename__ = "clients"

    client_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), unique=True, nullable=False, index=True)
    industry = Column(String(100), nullable=True)
    contact_person = Column(String(100), nullable=True)
    contact_email = Column(String(120), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    engagements = relationship("Engagement", back_populates="client")

    def __repr__(self):
        return f"<Client {self.name}>"


class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_by_manager_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    members = relationship("TeamMemberMapping", back_populates="team", cascade="all, delete-orphan")
    engagements = relationship("EngagementTeamAssignment", back_populates="team")

    def __repr__(self):
        return f"<Team {self.name}>"


class TeamMemberMapping(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User")


class Engagement(Base):
    __tablename__ = "engagements"

    engagement_id = Column(Integer, primary_key=True, autoincrement=True)
    engagement_code = Column(String(50), unique=True, nullable=False, index=True)  # e.g. ENG-2026-001
    client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=False)
    title = Column(String(200), nullable=False)
    process_under_audit = Column(String(200), nullable=False)
    audit_period_start = Column(String(20), nullable=False)  # DD-MM-YYYY
    audit_period_end = Column(String(20), nullable=False)    # DD-MM-YYYY
    scope = Column(Text, nullable=True)
    areas_covered = Column(Text, nullable=True)
    estimated_budget = Column(Float, default=0.0)             # Amount in INR
    deadline = Column(String(20), nullable=True)             # DD-MM-YYYY
    status = Column(String(30), default="Draft")             # Draft, Assigned, In Progress, Under Review, Completed
    manager_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    engagement_letter_filename = Column(String(255), nullable=True)
    engagement_letter_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    is_locked = Column(Boolean, default=False)
    consolidation_zip_path = Column(String(500), nullable=True)

    # Relationships
    client = relationship("Client", back_populates="engagements")
    manager = relationship("User", back_populates="created_engagements", foreign_keys=[manager_id])
    team_assignments = relationship("EngagementTeamAssignment", back_populates="engagement", cascade="all, delete-orphan")
    idr_items = relationship("IDRItem", back_populates="engagement", cascade="all, delete-orphan")
    rcm_items = relationship("RCMLineItem", back_populates="engagement", cascade="all, delete-orphan")
    working_papers = relationship("WorkingPaper", back_populates="engagement", cascade="all, delete-orphan")
    comments = relationship("CommentThread", back_populates="engagement", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Engagement {self.engagement_code} - {self.title}>"


class EngagementTeamAssignment(Base):
    __tablename__ = "engagement_team_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engagement_id = Column(Integer, ForeignKey("engagements.engagement_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=True)
    role_in_audit = Column(String(50), default="Auditor")  # Lead Auditor, Field Auditor, Reviewer
    assigned_at = Column(DateTime, default=datetime.utcnow)

    engagement = relationship("Engagement", back_populates="team_assignments")
    user = relationship("User", back_populates="assigned_engagements")
    team = relationship("Team", back_populates="engagements")


class IDRItem(Base):
    """Initial Data Request (IDR) Line Item"""
    __tablename__ = "idr_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engagement_id = Column(Integer, ForeignKey("engagements.engagement_id"), nullable=False)
    item_code = Column(String(50), nullable=False)  # e.g. IDR-01, IDR-02
    requirement_description = Column(Text, nullable=False)
    department_spoc = Column(String(100), nullable=True)
    priority = Column(String(20), default="Medium")  # High, Medium, Low
    target_date = Column(String(20), nullable=True)  # DD-MM-YYYY
    status = Column(String(30), default="Requested")  # Requested, Partially Received, Received, Overdue
    received_date = Column(String(20), nullable=True)  # DD-MM-YYYY
    notes = Column(Text, nullable=True)
    updated_by_name = Column(String(100), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    engagement = relationship("Engagement", back_populates="idr_items")


class RCMLineItem(Base):
    """Risk Control Matrix (RCM) Line Item with Manager Lock and Override Rights"""
    __tablename__ = "rcm_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engagement_id = Column(Integer, ForeignKey("engagements.engagement_id"), nullable=False)
    line_item_id = Column(String(50), nullable=False)  # Unique ID e.g. AREA-01, PROC-01
    process_area = Column(String(150), nullable=False)
    sub_process = Column(String(150), nullable=True)
    risk_id = Column(String(50), nullable=True)
    risk_description = Column(Text, nullable=False)
    control_id = Column(String(50), nullable=True)
    control_description = Column(Text, nullable=False)
    control_type = Column(String(50), default="Preventive")  # Preventive, Detective, Directive
    audit_procedure = Column(Text, nullable=True)
    person_responsible_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    status = Column(String(30), default="Open")  # Open, In Progress, Under Review, Reviewed, Closed
    manager_locked = Column(Boolean, default=False)  # When True, team members cannot modify control details
    manager_notes = Column(Text, nullable=True)
    review_status = Column(String(30), default="Pending")  # Pending, Reviewed, Query Raised
    reviewed_by_name = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    engagement = relationship("Engagement", back_populates="rcm_items")
    assigned_person = relationship("User", foreign_keys=[person_responsible_id])
    working_papers = relationship("WorkingPaper", back_populates="rcm_item", cascade="all, delete-orphan")
    observation = relationship("Observation", back_populates="rcm_item", uselist=False, cascade="all, delete-orphan")
    comments = relationship("CommentThread", back_populates="rcm_item", cascade="all, delete-orphan")


class WorkingPaper(Base):
    """Uploaded Evidence & Working Paper Files with Daily Date Versioning"""
    __tablename__ = "working_papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engagement_id = Column(Integer, ForeignKey("engagements.engagement_id"), nullable=False)
    rcm_item_id = Column(Integer, ForeignKey("rcm_items.id"), nullable=False)
    line_item_id = Column(String(50), nullable=False)  # Denormalized for rapid file path resolution
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    version_date = Column(String(20), nullable=False)  # DD-MM-YYYY (Daily version subfolder)
    file_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    uploaded_by_name = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    engagement = relationship("Engagement", back_populates="working_papers")
    rcm_item = relationship("RCMLineItem", back_populates="working_papers")
    uploader = relationship("User")


class Observation(Base):
    """Audit Observations recorded per RCM Line Item"""
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engagement_id = Column(Integer, ForeignKey("engagements.engagement_id"), nullable=False)
    rcm_item_id = Column(Integer, ForeignKey("rcm_items.id"), unique=True, nullable=False)
    observation_text = Column(Text, nullable=True)
    risk_rating = Column(String(20), default="Medium")  # High, Medium, Low, Informational
    implication = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    management_response = Column(Text, nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    updated_by_name = Column(String(100), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rcm_item = relationship("RCMLineItem", back_populates="observation")


class CommentThread(Base):
    """In-App Review Comment and Query Thread per RCM Line Item"""
    __tablename__ = "comment_threads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engagement_id = Column(Integer, ForeignKey("engagements.engagement_id"), nullable=False)
    rcm_item_id = Column(Integer, ForeignKey("rcm_items.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    sender_name = Column(String(100), nullable=False)
    sender_role = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    is_query = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_by_name = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    engagement = relationship("Engagement", back_populates="comments")
    rcm_item = relationship("RCMLineItem", back_populates="comments")
    sender = relationship("User", back_populates="comments")


class AuditTrailEntry(Base):
    """
    Immutable Audit Trail Log.
    App-level constraint: Append-only. No UPDATE or DELETE is exposed.
    """
    __tablename__ = "audit_trail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    timestamp_str = Column(String(30), nullable=False)  # DD-MM-YYYY HH:MM:SS
    action_type = Column(String(50), nullable=False)    # LOGIN, IMPERSONATE, CREATE, EDIT, UPLOAD, REVIEW, LOCK, REOPEN, EXPORT
    target_entity = Column(String(50), nullable=False)  # Engagement, IDR, RCM, WorkingPaper, User, Client
    target_id = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=False)
    acting_user_name = Column(String(100), nullable=False)
    # Impersonation tracking: true identity of the administrator
    true_admin_id = Column(Integer, nullable=True)
    true_admin_name = Column(String(100), nullable=True)
    ip_address = Column(String(50), default="127.0.0.1")
    actor_role = Column(String(50), nullable=True)
    target_role = Column(String(50), nullable=True)
    target_name = Column(String(150), nullable=True)
    action_category = Column(String(50), nullable=True)
    rbac_rule_applied = Column(String(255), nullable=True)
    previous_state_json = Column(Text, nullable=True)
    new_state_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    previous_hash = Column(String(64), nullable=True)
    integrity_hash = Column(String(64), nullable=True, index=True)

    def __repr__(self):
        return f"<AuditTrail [{self.timestamp_str}] {self.action_type} by {self.acting_user_name}>"


class Notification(Base):
    """In-App Notifications and Alerts for Overdue items and Review actions"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="info")  # info, alert, success, warning
    link_entity = Column(String(50), nullable=True)
    link_id = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
