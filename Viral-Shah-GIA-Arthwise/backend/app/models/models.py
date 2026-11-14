import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Numeric
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="analyst") # admin, analyst, reviewer, client
    is_active = Column(Boolean, default=True)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    client = relationship("Client", back_populates="users", foreign_keys=[client_id])
    audit_logs = relationship("AuditLog", back_populates="user")

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    client_code = Column(String(50), unique=True, index=True, nullable=False)
    primary_contact_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    constitution = Column(String(50), nullable=False) # individual, salaried, proprietorship, partnership, llp, pvt_ltd, public_ltd
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pin_code = Column(String(20), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    users = relationship("User", back_populates="client")
    entities = relationship("Entity", back_populates="client", cascade="all, delete-orphan")
    proposals = relationship("Proposal", back_populates="client", cascade="all, delete-orphan")

class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    legal_name = Column(String(255), nullable=False)
    trade_name = Column(String(255), nullable=True)
    constitution = Column(String(50), nullable=False)
    pan = Column(String(20), nullable=True)
    pan_masked = Column(String(20), nullable=True)
    cin = Column(String(50), nullable=True)
    udyam_reg = Column(String(50), nullable=True)
    date_of_incorporation = Column(String(20), nullable=True)
    business_activity = Column(Text, nullable=True)
    registered_address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    client = relationship("Client", back_populates="entities")
    gst_registrations = relationship("GSTRegistration", back_populates="entity", cascade="all, delete-orphan")
    promoters = relationship("Promoter", back_populates="entity", cascade="all, delete-orphan")
    bank_accounts = relationship("BankAccount", back_populates="entity", cascade="all, delete-orphan")
    existing_facilities = relationship("ExistingFacility", back_populates="entity", cascade="all, delete-orphan")
    proposals = relationship("Proposal", back_populates="entity")

class GSTRegistration(Base):
    __tablename__ = "gst_registrations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    gstin = Column(String(30), nullable=False)
    gstin_masked = Column(String(30), nullable=True)
    state = Column(String(100), nullable=True)
    status = Column(String(50), default="active") # active, suspended, cancelled
    filing_frequency = Column(String(20), default="monthly") # monthly, quarterly
    created_at = Column(DateTime, default=get_utc_now)

    entity = relationship("Entity", back_populates="gst_registrations")

class Promoter(Base):
    __tablename__ = "promoters"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False) # proprietor, partner, director, co_applicant, guarantor
    pan = Column(String(20), nullable=True)
    pan_masked = Column(String(20), nullable=True)
    din = Column(String(20), nullable=True)
    ownership_pct = Column(Float, default=0.0)
    cibil_score = Column(Integer, nullable=True)
    mobile = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    entity = relationship("Entity", back_populates="promoters")

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    bank_name = Column(String(255), nullable=False)
    branch = Column(String(255), nullable=True)
    account_type = Column(String(50), nullable=False) # current, cc, od, savings
    account_number_masked = Column(String(50), nullable=False)
    ifsc = Column(String(20), nullable=True)
    average_monthly_balance = Column(Numeric(15, 2), default=0.0)
    statement_from = Column(String(20), nullable=True)
    statement_to = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    entity = relationship("Entity", back_populates="bank_accounts")

class ExistingFacility(Base):
    __tablename__ = "existing_facilities"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    lender_name = Column(String(255), nullable=False)
    facility_type = Column(String(100), nullable=False) # home_loan, lap, business_loan, cash_credit, overdraft, term_loan
    sanctioned_limit = Column(Numeric(15, 2), default=0.0)
    outstanding_balance = Column(Numeric(15, 2), default=0.0)
    interest_rate = Column(Float, default=0.0)
    monthly_emi = Column(Numeric(15, 2), default=0.0)
    residual_tenure_months = Column(Integer, default=0)
    primary_security = Column(Text, nullable=True)
    collateral_security = Column(Text, nullable=True)
    sanction_date = Column(String(20), nullable=True)
    renewal_date = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    entity = relationship("Entity", back_populates="existing_facilities")

class Proposal(Base):
    __tablename__ = "proposals"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    proposal_code = Column(String(50), unique=True, index=True, nullable=False)
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    product_type = Column(String(50), nullable=False) # home_loan, lap, business_loan_secured, business_loan_unsecured, cash_credit_od, working_capital, project_finance_term_loan, balance_transfer_topup
    requested_amount = Column(Numeric(15, 2), nullable=False)
    tenure_months = Column(Integer, default=60)
    purpose = Column(Text, nullable=True)
    target_rate = Column(Float, default=9.5)
    status = Column(String(50), default="lead") # lead, onboarding, proposal_draft, document_collection, extraction_verification, financial_analysis, lender_comparison, reviewer_approval, report_generation, submission_tracking, sanctioned, rejected
    assigned_analyst_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_reviewer_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    client = relationship("Client", back_populates="proposals")
    entity = relationship("Entity", back_populates="proposals")
    documents = relationship("ProposalDocument", back_populates="proposal", cascade="all, delete-orphan")
    checklist_items = relationship("DocumentChecklistItem", back_populates="proposal", cascade="all, delete-orphan")
    extracted_data = relationship("ExtractedData", back_populates="proposal", cascade="all, delete-orphan")
    evaluations = relationship("FinancialEvaluation", back_populates="proposal", cascade="all, delete-orphan")
    cma_projects = relationship("CMAProject", back_populates="proposal", cascade="all, delete-orphan")

class ProposalDocument(Base):
    __tablename__ = "proposal_documents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    proposal_id = Column(String(36), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False) # financial_statements, itr, gst, bank_statement, cibil, emi_sheet, sanction_letter, debtors_ageing, purchase_orders, kyc, property
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_hash_sha256 = Column(String(64), nullable=True)
    file_size = Column(Integer, default=0)
    mime_type = Column(String(100), nullable=True)
    uploaded_by_user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    proposal = relationship("Proposal", back_populates="documents")
    extracted_records = relationship("ExtractedData", back_populates="document", cascade="all, delete-orphan")

class DocumentChecklistItem(Base):
    __tablename__ = "document_checklist_items"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    proposal_id = Column(String(36), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False)
    document_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    is_applicable = Column(Boolean, default=True)
    na_reason = Column(Text, nullable=True) # mandatory if is_applicable is False
    is_received = Column(Boolean, default=False)
    period_required = Column(String(100), nullable=True)
    verification_status = Column(String(50), default="requested") # requested, partially_received, received, verified, rejected, expired, superseded, not_applicable
    missing_details = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    proposal = relationship("Proposal", back_populates="checklist_items")

class ExtractedData(Base):
    __tablename__ = "extracted_data"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    proposal_id = Column(String(36), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(36), ForeignKey("proposal_documents.id", ondelete="CASCADE"), nullable=False)
    page_or_sheet = Column(String(50), nullable=True)
    financial_period = Column(String(50), nullable=True) # FY 2023-24, FY 2024-25, etc.
    metric_name = Column(String(100), nullable=False) # revenue, pat, depreciation, debt, ebitda, etc.
    raw_value = Column(String(255), nullable=True)
    normalized_value = Column(Numeric(15, 2), nullable=True)
    confidence = Column(Float, default=1.0) # 0.0 to 1.0 or manual
    verification_status = Column(String(50), default="unverified") # unverified, verified, adjusted, rejected
    verified_by_user_id = Column(String(36), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    proposal = relationship("Proposal", back_populates="extracted_data")
    document = relationship("ProposalDocument", back_populates="extracted_records")

class FinancialEvaluation(Base):
    __tablename__ = "financial_evaluations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    proposal_id = Column(String(36), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1)
    evaluation_date = Column(DateTime, default=get_utc_now)
    
    # Cash flow & repayment inputs
    monthly_income_or_cash_accrual = Column(Numeric(15, 2), default=0.0)
    total_existing_emi = Column(Numeric(15, 2), default=0.0)
    proposed_emi = Column(Numeric(15, 2), default=0.0)
    foir_pct = Column(Float, default=0.0)
    
    # Collateral & security
    assessed_collateral_value = Column(Numeric(15, 2), default=0.0)
    ltv_pct = Column(Float, default=0.0)
    
    # Financial Ratios
    dscr = Column(Float, default=0.0)
    icr = Column(Float, default=0.0)
    current_ratio = Column(Float, default=0.0)
    quick_ratio = Column(Float, default=0.0)
    debt_equity_ratio = Column(Float, default=0.0)
    tol_tnw_ratio = Column(Float, default=0.0)
    debtor_days = Column(Integer, default=0)
    inventory_days = Column(Integer, default=0)
    creditor_days = Column(Integer, default=0)
    
    # Eligibility outputs
    eligible_loan_foir = Column(Numeric(15, 2), default=0.0)
    eligible_loan_ltv = Column(Numeric(15, 2), default=0.0)
    eligible_loan_dscr = Column(Numeric(15, 2), default=0.0)
    preliminary_eligible_amount = Column(Numeric(15, 2), default=0.0)
    limiting_factor = Column(String(100), nullable=True) # FOIR Capped, Collateral LTV Capped, DSCR Capped, Product Max Capped, Requested Amount
    
    is_snapshot = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    proposal = relationship("Proposal", back_populates="evaluations")

class CMAProject(Base):
    __tablename__ = "cma_projects"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    proposal_id = Column(String(36), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False)
    base_year = Column(String(20), default="FY 2024-25")
    data_json = Column(Text, nullable=False) # JSON storing Form I to VII multi-period matrix
    is_reconciled = Column(Boolean, default=True)
    balance_sheet_diff = Column(Numeric(15, 2), default=0.0)
    cash_flow_diff = Column(Numeric(15, 2), default=0.0)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    proposal = relationship("Proposal", back_populates="cma_projects")

class Lender(Base):
    __tablename__ = "lenders"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(50), default="public_bank") # public_bank, private_bank, nbfc
    created_at = Column(DateTime, default=get_utc_now)

    policies = relationship("LenderPolicy", back_populates="lender", cascade="all, delete-orphan")

class LenderPolicy(Base):
    __tablename__ = "lender_policies"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    lender_id = Column(String(36), ForeignKey("lenders.id", ondelete="CASCADE"), nullable=False)
    product_type = Column(String(50), nullable=False)
    policy_name = Column(String(255), nullable=False)
    min_loan = Column(Numeric(15, 2), default=0.0)
    max_loan = Column(Numeric(15, 2), default=0.0)
    max_foir = Column(Float, default=60.0)
    max_ltv = Column(Float, default=75.0)
    min_dscr = Column(Float, default=1.35)
    min_icr = Column(Float, default=1.5)
    min_cibil = Column(Integer, default=700)
    min_vintage_years = Column(Float, default=3.0)
    min_turnover = Column(Numeric(15, 2), default=0.0)
    benchmark_rate = Column(Float, default=9.5)
    required_docs_json = Column(Text, nullable=True) # JSON array of mandatory docs
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)

    lender = relationship("Lender", back_populates="policies")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    client_id = Column(String(36), nullable=True)
    proposal_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False) # CREATE, UPDATE, DELETE, VIEW, DOWNLOAD, VERIFY, APPROVE, EXPORT
    resource_type = Column(String(100), nullable=False) # proposal, document, evaluation, cma, user
    resource_id = Column(String(100), nullable=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    user = relationship("User", back_populates="audit_logs")

class MasterLocation(Base):
    __tablename__ = "master_locations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    tier = Column(String(20), default="tier2") # tier1, tier2, tier3
    is_custom = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_utc_now)

class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_code = Column(String(50), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    brand_name = Column(String(100), nullable=False)
    tagline = Column(String(255), nullable=True)
    logo_data = Column(Text, nullable=True) # Data URL or relative image path
    primary_color = Column(String(20), default="#1b2632")
    secondary_color = Column(String(20), default="#a45139")
    website = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pin_code = Column(String(20), nullable=True)
    pan = Column(String(20), nullable=True)
    gstin = Column(String(25), nullable=True)
    cin = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_utc_now)
