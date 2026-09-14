from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship as sqlalchemy_relationship
from datetime import datetime
from database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    entity_type = Column(String, default="Private Limited Company", index=True)
    reporting_period = Column(String, default="FY 2024-25")
    previous_year_period = Column(String, default="FY 2023-24")
    currency = Column(String, default="INR (in Lakhs)")
    accounting_framework = Column(String, default="IGAAP")
    schedule_format = Column(String, default="Schedule III Division I")
    prepared_by = Column(String, default="CA Staff")
    reviewed_by = Column(String, default="CA Partner")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    tb_lines = sqlalchemy_relationship("TrialBalanceLine", back_populates="client", cascade="all, delete-orphan")
    ar_lines = sqlalchemy_relationship("ARAgeing", back_populates="client", cascade="all, delete-orphan")
    ap_lines = sqlalchemy_relationship("APAgeing", back_populates="client", cascade="all, delete-orphan")
    cwip_lines = sqlalchemy_relationship("CWIPAgeing", back_populates="client", cascade="all, delete-orphan")
    rpt_lines = sqlalchemy_relationship("RelatedParty", back_populates="client", cascade="all, delete-orphan")
    borrowing_lines = sqlalchemy_relationship("Borrowing", back_populates="client", cascade="all, delete-orphan")
    contingency_lines = sqlalchemy_relationship("Contingency", back_populates="client", cascade="all, delete-orphan")
    notes = sqlalchemy_relationship("Note", back_populates="client", cascade="all, delete-orphan")
    accounting_policies = sqlalchemy_relationship("AccountingPolicy", back_populates="client", cascade="all, delete-orphan")
    cash_flow_adjustments = sqlalchemy_relationship("CashFlowAdjustment", back_populates="client", cascade="all, delete-orphan")
    engagements = sqlalchemy_relationship("Engagement", back_populates="client", cascade="all, delete-orphan")
    uploaded_files = sqlalchemy_relationship("UploadedFile", back_populates="client", cascade="all, delete-orphan")
    generated_reports = sqlalchemy_relationship("GeneratedReport", back_populates="client", cascade="all, delete-orphan")
    audit_logs = sqlalchemy_relationship("AuditLog", back_populates="client", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_clients_name_entity", "name", "entity_type"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    mobile = Column(String, nullable=True)
    department = Column(String, default="Audit & Assurance", index=True)
    role = Column(String, default="Executive", index=True)  
    # Roles: System Administrator, Partner, Director, Manager, Assistant Manager, Executive, Article Assistant, Viewer
    is_active = Column(Boolean, default=True, index=True)
    hashed_password = Column(String, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    audit_logs = sqlalchemy_relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index("idx_users_role_active", "role", "is_active"),
        Index("idx_users_emp_email", "employee_code", "email"),
    )



class Engagement(Base):
    __tablename__ = "engagements"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    reporting_period = Column(String, nullable=False, index=True)
    status = Column(String, default="Draft", index=True)  # Draft / In Review / Approved / Filed
    partner_in_charge = Column(String, nullable=True)
    manager_in_charge = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    client = sqlalchemy_relationship("Client", back_populates="engagements")

    __table_args__ = (
        Index("idx_engagements_client_period", "client_id", "reporting_period"),
        Index("idx_engagements_status", "status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user = sqlalchemy_relationship("User", back_populates="audit_logs")
    client = sqlalchemy_relationship("Client", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_client_action", "client_id", "action"),
        Index("idx_audit_logs_timestamp", "timestamp"),
    )


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    file_type = Column(String, nullable=False, index=True)  # Trial Balance / AR / AP / CWIP / etc.
    original_filename = Column(String, nullable=False)
    stored_filepath = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)

    client = sqlalchemy_relationship("Client", back_populates="uploaded_files")

    __table_args__ = (
        Index("idx_uploaded_files_client_type", "client_id", "file_type"),
    )


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    report_type = Column(String, nullable=False, index=True)  # PDF / Excel / Word / FS Draft
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    status = Column(String, default="Completed", index=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)

    client = sqlalchemy_relationship("Client", back_populates="generated_reports")

    __table_args__ = (
        Index("idx_reports_client_type", "client_id", "report_type"),
    )


class TrialBalanceLine(Base):
    __tablename__ = "trial_balance_lines"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    ledger_code = Column(String, nullable=True, index=True)
    ledger_name = Column(String, nullable=False, index=True)
    original_group = Column(String, nullable=True)
    cy_amount = Column(Float, default=0.0)
    py_amount = Column(Float, default=0.0)
    type = Column(String, nullable=True)  # Debit / Credit
    suggested_classification = Column(String, nullable=True)
    final_classification = Column(String, nullable=True, index=True)
    financial_statement = Column(String, nullable=True, index=True)  # Balance Sheet / Profit & Loss
    note_number = Column(String, nullable=True, index=True)
    current_non_current = Column(String, nullable=True)  # Current / Non-Current
    user_override = Column(Boolean, default=False)

    client = sqlalchemy_relationship("Client", back_populates="tb_lines")

    __table_args__ = (
        Index("idx_tb_client_cls", "client_id", "final_classification"),
    )


class MappingRule(Base):
    __tablename__ = "mapping_rules"

    id = Column(Integer, primary_key=True, index=True)
    pattern = Column(String, nullable=False)
    target_classification = Column(String, nullable=False, index=True)
    target_statement = Column(String, nullable=False)
    note_number = Column(String, nullable=True)
    current_non_current = Column(String, nullable=True)


class ARAgeing(Base):
    __tablename__ = "ar_ageing"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    customer_name = Column(String, nullable=False, index=True)
    l6m = Column(Float, default=0.0)
    m6_1y = Column(Float, default=0.0)
    y1_2y = Column(Float, default=0.0)
    y2_3y = Column(Float, default=0.0)
    mor_3y = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    category = Column(String, default="Undisputed Considered Good")
    disputed = Column(String, default="No")
    py_total = Column(Float, default=0.0)

    client = sqlalchemy_relationship("Client", back_populates="ar_lines")


class APAgeing(Base):
    __tablename__ = "ap_ageing"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    vendor_name = Column(String, nullable=False, index=True)
    msme = Column(String, default="No", index=True)
    l1y = Column(Float, default=0.0)
    y1_2y = Column(Float, default=0.0)
    y2_3y = Column(Float, default=0.0)
    mor_3y = Column(Float, default=0.0)
    outstanding_amount = Column(Float, default=0.0)
    category = Column(String, default="Undisputed Dues")
    disputed = Column(String, default="No")
    py_outstanding_amount = Column(Float, default=0.0)

    client = sqlalchemy_relationship("Client", back_populates="ap_lines")


class CWIPAgeing(Base):
    __tablename__ = "cwip_ageing"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    project_name = Column(String, nullable=False, index=True)
    l1y = Column(Float, default=0.0)
    y1_2y = Column(Float, default=0.0)
    y2_3y = Column(Float, default=0.0)
    mor_3y = Column(Float, default=0.0)
    closing_cwip = Column(Float, default=0.0)
    status = Column(String, default="In Progress")
    reason_delay = Column(String, nullable=True)
    py_closing_cwip = Column(Float, default=0.0)

    client = sqlalchemy_relationship("Client", back_populates="cwip_lines")


class RelatedParty(Base):
    __tablename__ = "related_parties"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    name = Column(String, nullable=False, index=True)
    relationship = Column(String, nullable=False)
    nature_tx = Column(String, nullable=False)
    opening_bal = Column(Float, default=0.0)
    debit_tx = Column(Float, default=0.0)
    credit_tx = Column(Float, default=0.0)
    closing_bal = Column(Float, default=0.0)
    category = Column(String, default="KMP/Relative")
    terms = Column(String, nullable=True)
    py_closing_bal = Column(Float, default=0.0)

    client = sqlalchemy_relationship("Client", back_populates="rpt_lines")


class Borrowing(Base):
    __tablename__ = "borrowings"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    lender_name = Column(String, nullable=False, index=True)
    loan_type = Column(String, nullable=False)
    secured_unsecured = Column(String, default="Secured")
    current_non_current = Column(String, default="Non-current")
    opening_bal = Column(Float, default=0.0)
    additions = Column(Float, default=0.0)
    repayments = Column(Float, default=0.0)
    closing_bal = Column(Float, default=0.0)
    interest_rate = Column(String, nullable=True)
    security_details = Column(String, nullable=True)
    repayment_terms = Column(String, nullable=True)
    is_default = Column(String, default="No")
    default_amount = Column(Float, default=0.0)
    py_closing_bal = Column(Float, default=0.0)

    client = sqlalchemy_relationship("Client", back_populates="borrowing_lines")


class Contingency(Base):
    __tablename__ = "contingencies"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    nature = Column(String, nullable=False, index=True)
    forum = Column(String, nullable=True)
    cy_amount = Column(Float, default=0.0)
    py_amount = Column(Float, default=0.0)
    assessment = Column(String, nullable=True)
    provision_required = Column(String, default="No")
    remarks = Column(String, nullable=True)

    client = sqlalchemy_relationship("Client", back_populates="contingency_lines")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    note_number = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    suggested_content = Column(Text, nullable=False)
    table_json = Column(Text, nullable=True)
    is_modified = Column(Boolean, default=False)

    client = sqlalchemy_relationship("Client", back_populates="notes")

    __table_args__ = (
        Index("idx_notes_client_num", "client_id", "note_number"),
    )


class AccountingPolicy(Base):
    __tablename__ = "accounting_policies"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    policy_number = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    suggested_content = Column(Text, nullable=False)
    is_applicable = Column(Boolean, default=True)
    is_modified = Column(Boolean, default=False)

    client = sqlalchemy_relationship("Client", back_populates="accounting_policies")


class CashFlowAdjustment(Base):
    __tablename__ = "cash_flow_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    adjustment_type = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)
    amount = Column(Float, default=0.0)
    py_amount = Column(Float, default=0.0)
    category = Column(String, default="Operating", index=True)  # Operating / Investing / Financing
    remarks = Column(String, nullable=True)

    client = sqlalchemy_relationship("Client", back_populates="cash_flow_adjustments")

    __table_args__ = (
        Index("idx_cf_client_cat", "client_id", "category"),
    )

class ClientMetadata(Base):
    __tablename__ = "client_metadata"
    
    client_id = Column(Integer, ForeignKey("clients.id"), primary_key=True)
    client_name = Column(String, nullable=False)
    cin_number = Column(String, nullable=True)
    financial_year_ended = Column(String, nullable=True)

class DirectorMaster(Base):
    __tablename__ = "director_master"
    
    director_id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    name = Column(String, nullable=False)
    designation = Column(String, nullable=False)
    din = Column(String, nullable=True)

class CompanySecretary(Base):
    __tablename__ = "company_secretary"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    name = Column(String, nullable=False)
    membership_no = Column(String, nullable=True)

class ChiefFinancialOfficer(Base):
    __tablename__ = "chief_financial_officer"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    name = Column(String, nullable=False)

class AdditionalDisclosure(Base):
    __tablename__ = "additional_disclosures"
    
    disclosure_id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    insert_after_note = Column(String, nullable=False)
    sequence_no = Column(Integer, default=1)


class CustomRule(Base):
    __tablename__ = "custom_rules"

    rule_id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True, nullable=True)
    rule_name = Column(String, nullable=False)
    rule_type = Column(String, nullable=False)
    condition_field = Column(String, nullable=False)
    operator = Column(String, nullable=False)
    condition_value = Column(String, nullable=False)
    output_value = Column(String, nullable=False)
    note_number = Column(String, nullable=True)
    statement = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    priority = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_by = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)
