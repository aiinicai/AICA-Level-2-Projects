from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

# User & Auth
class UserLogin(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "analyst"
    client_id: Optional[str] = None

class PasswordResetRequest(BaseModel):
    new_password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    client_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Master Data: GST, Promoter, Bank, Facility
class GSTRegistrationCreate(BaseModel):
    gstin: str
    state: Optional[str] = None
    status: str = "active"
    filing_frequency: str = "monthly"

class GSTRegistrationResponse(BaseModel):
    id: str
    entity_id: str
    gstin: str
    gstin_masked: Optional[str] = None
    state: Optional[str] = None
    status: str
    filing_frequency: str

    class Config:
        from_attributes = True

class PromoterCreate(BaseModel):
    name: str
    role: str # proprietor, partner, director, co_applicant, guarantor
    pan: Optional[str] = None
    din: Optional[str] = None
    ownership_pct: float = 0.0
    cibil_score: Optional[int] = None
    mobile: Optional[str] = None
    email: Optional[str] = None

class PromoterResponse(BaseModel):
    id: str
    entity_id: str
    name: str
    role: str
    pan_masked: Optional[str] = None
    din: Optional[str] = None
    ownership_pct: float
    cibil_score: Optional[int] = None
    mobile: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True

class BankAccountCreate(BaseModel):
    bank_name: str
    branch: Optional[str] = None
    account_type: str
    account_number: str
    ifsc: Optional[str] = None
    average_monthly_balance: Decimal = Decimal("0.0")
    statement_from: Optional[str] = None
    statement_to: Optional[str] = None

class BankAccountResponse(BaseModel):
    id: str
    entity_id: str
    bank_name: str
    branch: Optional[str] = None
    account_type: str
    account_number_masked: str
    ifsc: Optional[str] = None
    average_monthly_balance: Decimal
    statement_from: Optional[str] = None
    statement_to: Optional[str] = None

    class Config:
        from_attributes = True

class ExistingFacilityCreate(BaseModel):
    lender_name: str
    facility_type: str
    sanctioned_limit: Decimal
    outstanding_balance: Decimal
    interest_rate: float
    monthly_emi: Decimal
    residual_tenure_months: int
    primary_security: Optional[str] = None
    collateral_security: Optional[str] = None
    sanction_date: Optional[str] = None
    renewal_date: Optional[str] = None

class ExistingFacilityResponse(BaseModel):
    id: str
    entity_id: str
    lender_name: str
    facility_type: str
    sanctioned_limit: Decimal
    outstanding_balance: Decimal
    interest_rate: float
    monthly_emi: Decimal
    residual_tenure_months: int
    primary_security: Optional[str] = None
    collateral_security: Optional[str] = None
    sanction_date: Optional[str] = None
    renewal_date: Optional[str] = None

    class Config:
        from_attributes = True

# Entity & Client
class EntityCreate(BaseModel):
    legal_name: str
    trade_name: Optional[str] = None
    constitution: str
    pan: Optional[str] = None
    cin: Optional[str] = None
    udyam_reg: Optional[str] = None
    date_of_incorporation: Optional[str] = None
    business_activity: Optional[str] = None
    registered_address: Optional[str] = None

class EntityResponse(BaseModel):
    id: str
    client_id: str
    legal_name: str
    trade_name: Optional[str] = None
    constitution: str
    pan_masked: Optional[str] = None
    cin: Optional[str] = None
    udyam_reg: Optional[str] = None
    date_of_incorporation: Optional[str] = None
    business_activity: Optional[str] = None
    registered_address: Optional[str] = None
    promoters: List[PromoterResponse] = []
    gst_registrations: List[GSTRegistrationResponse] = []
    bank_accounts: List[BankAccountResponse] = []
    existing_facilities: List[ExistingFacilityResponse] = []

    class Config:
        from_attributes = True

class ClientCreate(BaseModel):
    primary_contact_name: str
    phone: str
    email: str
    constitution: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None

class ClientResponse(BaseModel):
    id: str
    client_code: str
    primary_contact_name: str
    phone: str
    email: str
    constitution: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    is_deleted: bool = False
    created_at: datetime
    entities: List[EntityResponse] = []

    class Config:
        from_attributes = True

class CustomerOnboardRequest(BaseModel):
    # Customer Details
    customer_name: str
    primary_contact: Optional[str] = None
    email: str
    phone: str
    constitution: str = "pvt_ltd"
    address: Optional[str] = None
    city: Optional[str] = "Vadodara"
    state: Optional[str] = "Gujarat"
    pin_code: Optional[str] = None

    # Entity Details
    pan: Optional[str] = None
    date_of_incorporation: Optional[str] = None
    business_activity: Optional[str] = None

    # Promoter / Director Details
    promoter_name: Optional[str] = None
    promoter_pan: Optional[str] = None
    cibil_score: Optional[int] = None
    ownership_pct: Optional[float] = 100.0

    # Initial Loan Proposal Request
    create_proposal: bool = True
    product_type: Optional[str] = "cash_credit_od"
    requested_amount: Optional[Decimal] = Decimal("10000000")
    tenure_months: Optional[int] = 60
    purpose: Optional[str] = "Working capital facilities against receivables and enterprise contracts"
    target_rate: Optional[float] = 9.25

class CustomerOnboardResponse(BaseModel):
    status: str
    client_id: str
    client_code: str
    entity_id: str
    proposal_id: Optional[str] = None
    proposal_code: Optional[str] = None
    checklist_count: int = 0
    message: str

# Proposal & Checklist
class ProposalCreate(BaseModel):
    client_id: str
    entity_id: str
    product_type: str
    requested_amount: Decimal
    tenure_months: int = 60
    purpose: Optional[str] = None
    target_rate: float = 9.5

class ProposalStatusUpdate(BaseModel):
    status: str
    review_notes: Optional[str] = None

class ProposalRequirementsUpdate(BaseModel):
    product_type: Optional[str] = None
    requested_amount: Optional[Decimal] = None
    tenure_months: Optional[int] = None
    purpose: Optional[str] = None
    target_rate: Optional[float] = None

class ProposalResponse(BaseModel):
    id: str
    proposal_code: str
    client_id: str
    entity_id: str
    product_type: str
    requested_amount: Decimal
    tenure_months: int
    purpose: Optional[str] = None
    target_rate: float
    status: str
    assigned_analyst_id: Optional[str] = None
    assigned_reviewer_id: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChecklistItemUpdate(BaseModel):
    is_applicable: Optional[bool] = None
    na_reason: Optional[str] = None
    is_received: Optional[bool] = None
    period_required: Optional[str] = None
    verification_status: Optional[str] = None
    missing_details: Optional[str] = None
    remarks: Optional[str] = None

class ChecklistItemResponse(BaseModel):
    id: str
    proposal_id: str
    document_name: str
    category: str
    is_applicable: bool
    na_reason: Optional[str] = None
    is_received: bool
    period_required: Optional[str] = None
    verification_status: str
    missing_details: Optional[str] = None
    remarks: Optional[str] = None

    class Config:
        from_attributes = True

# Proposal Document & Extraction
class ProposalDocumentResponse(BaseModel):
    id: str
    proposal_id: str
    category: str
    original_filename: str
    stored_filename: str
    file_size: int
    mime_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ExtractedDataCreate(BaseModel):
    document_id: str
    page_or_sheet: Optional[str] = None
    financial_period: Optional[str] = None
    metric_name: str
    raw_value: Optional[str] = None
    normalized_value: Optional[Decimal] = None
    confidence: float = 1.0

class ExtractedDataUpdate(BaseModel):
    normalized_value: Optional[Decimal] = None
    verification_status: str # unverified, verified, adjusted, rejected
    reviewer_notes: Optional[str] = None

class ExtractedDataResponse(BaseModel):
    id: str
    proposal_id: str
    document_id: str
    page_or_sheet: Optional[str] = None
    financial_period: Optional[str] = None
    metric_name: str
    raw_value: Optional[str] = None
    normalized_value: Optional[Decimal] = None
    confidence: float
    verification_status: str
    reviewer_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class YearWiseFinancialEntry(BaseModel):
    financial_period: str # e.g. "FY 2024-25 (Audited)", "FY 2025-26 (Provisional)"
    revenue_from_operations: Optional[Decimal] = None
    other_income: Optional[Decimal] = None
    cost_of_goods_sold: Optional[Decimal] = None
    employee_benefits_expense: Optional[Decimal] = None
    finance_costs: Optional[Decimal] = None
    depreciation: Optional[Decimal] = None
    other_expenses: Optional[Decimal] = None
    tax_expense: Optional[Decimal] = None
    pat: Optional[Decimal] = None

    tangible_net_worth: Optional[Decimal] = None
    long_term_borrowings: Optional[Decimal] = None
    other_long_term_liabilities: Optional[Decimal] = None
    short_term_borrowings: Optional[Decimal] = None
    trade_payables: Optional[Decimal] = None
    other_current_liabilities: Optional[Decimal] = None
    short_term_provisions: Optional[Decimal] = None
    fixed_assets: Optional[Decimal] = None
    non_current_investments: Optional[Decimal] = None
    long_term_loans_advances: Optional[Decimal] = None
    current_investments: Optional[Decimal] = None
    inventories: Optional[Decimal] = None
    trade_receivables: Optional[Decimal] = None
    cash_and_bank: Optional[Decimal] = None
    short_term_loans_advances: Optional[Decimal] = None
    other_current_assets: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None
    total_assets: Optional[Decimal] = None

class ManualFinancialsPayload(BaseModel):
    entries: List[YearWiseFinancialEntry]
    sync_to_cma: bool = True

class ManualSingleMetricCreate(BaseModel):
    metric_name: str
    financial_period: str
    normalized_value: Decimal
    raw_value: Optional[str] = None
    page_or_sheet: Optional[str] = "Manual Entry"
    verification_status: str = "verified"
    reviewer_notes: Optional[str] = None

# Financial Evaluation Inputs & Outputs
class FinancialEvaluationInput(BaseModel):
    proposal_id: str
    monthly_income_or_cash_accrual: Decimal
    total_existing_emi: Decimal
    interest_rate: float = 9.5
    tenure_months: int = 60
    assessed_collateral_value: Decimal = Decimal("0.0")
    max_foir_pct: float = 60.0
    max_ltv_pct: float = 75.0
    min_dscr_target: float = 1.35
    
    # Financial indicators for business/project loans
    pat: Decimal = Decimal("0.0")
    depreciation: Decimal = Decimal("0.0")
    finance_costs: Decimal = Decimal("0.0")
    existing_term_debt_repayment: Decimal = Decimal("0.0")
    ebitda: Decimal = Decimal("0.0")
    current_assets: Decimal = Decimal("0.0")
    current_liabilities: Decimal = Decimal("0.0")
    inventory: Decimal = Decimal("0.0")
    tangible_net_worth: Decimal = Decimal("0.0")
    total_outside_liabilities: Decimal = Decimal("0.0")
    turnover: Decimal = Decimal("0.0")
    sundry_debtors: Decimal = Decimal("0.0")
    sundry_creditors: Decimal = Decimal("0.0")
    cogs: Decimal = Decimal("0.0")
    total_purchases: Decimal = Decimal("0.0")

class FinancialEvaluationResponse(BaseModel):
    proposal_id: str
    requested_amount: Decimal
    proposed_emi: Decimal
    foir_pct: float
    ltv_pct: float
    dscr: float
    icr: float
    current_ratio: float
    quick_ratio: float
    debt_equity_ratio: float
    tol_tnw_ratio: float
    debtor_days: int
    inventory_days: int
    creditor_days: int
    net_working_capital_cycle_days: int
    
    # Capped eligibility calculations
    eligible_loan_foir: Decimal
    eligible_loan_ltv: Decimal
    eligible_loan_dscr: Decimal
    preliminary_eligible_amount: Decimal
    limiting_factor: str
    disclaimer: str

    class Config:
        from_attributes = True

# CMA Workspace
class CMAProjectSave(BaseModel):
    base_year: str = "FY 2024-25"
    data: Dict[str, Any]

class CMAProjectResponse(BaseModel):
    id: str
    proposal_id: str
    base_year: str
    data: Dict[str, Any]
    is_reconciled: bool
    balance_sheet_diff: Decimal
    cash_flow_diff: Decimal
    created_at: datetime
    updated_at: datetime

# Lender & Policy
class LenderPolicyResponse(BaseModel):
    id: str
    lender_id: str
    lender_code: str
    lender_name: str
    lender_category: str
    product_type: str
    policy_name: str
    min_loan: Decimal
    max_loan: Decimal
    max_foir: float
    max_ltv: float
    min_dscr: float
    min_icr: float
    min_cibil: int
    min_vintage_years: float
    min_turnover: Decimal
    benchmark_rate: float
    required_docs: List[str] = []
    is_active: bool

class PolicyFitEvaluation(BaseModel):
    lender_id: str
    lender_code: str
    lender_name: str
    product_type: str
    fit_status: str # "ELGIBLE", "BORDERLINE", "INELIGIBLE"
    max_eligible_amount: Decimal
    benchmark_rate: float

# Master Locations (India City & State LOV)
class LocationCity(BaseModel):
    id: Optional[str] = None
    city: str
    state: str
    tier: Optional[str] = "tier2"

class LocationCreate(BaseModel):
    city: str
    state: str
    tier: Optional[str] = "tier2"

# PAN Verification & Validation
class PANValidationRequest(BaseModel):
    pan: str
    entity_name: Optional[str] = None
    constitution: Optional[str] = None

class PANValidationResponse(BaseModel):
    pan: str
    is_valid: bool
    status: str # "VALID" or "INVALID"
    entity_type: str
    entity_type_code: str
    constitution_match: bool
    name_match: Optional[bool] = None
    expected_constitution: Optional[str] = None
    pan_type: str
    verification_source: str
    message: str
    normalized_pan: str

# White-Label Company Master
class CompanyProfileBase(BaseModel):
    company_code: str
    company_name: str
    brand_name: str
    tagline: Optional[str] = None
    logo_data: Optional[str] = None
    primary_color: Optional[str] = "#1b2632"
    secondary_color: Optional[str] = "#a45139"
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    cin: Optional[str] = None

class CompanyProfileCreate(CompanyProfileBase):
    pass

class CompanyProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    brand_name: Optional[str] = None
    tagline: Optional[str] = None
    logo_data: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    cin: Optional[str] = None

class CompanyProfileResponse(CompanyProfileBase):
    id: str
    is_active: bool
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True
