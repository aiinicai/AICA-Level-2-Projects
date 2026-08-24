from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ClientBase(BaseModel):
    name: str
    entity_type: str = "Private Limited Company"
    reporting_period: str = "FY 2024-25"
    previous_year_period: str = "FY 2023-24"
    currency: str = "INR (in Lakhs)"
    accounting_framework: str = "IGAAP"
    schedule_format: str = "Schedule III Division I"
    prepared_by: str = "CA Staff"
    reviewed_by: str = "CA Partner"

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TrialBalanceLineSchema(BaseModel):
    id: int
    ledger_code: Optional[str] = None
    ledger_name: str
    original_group: Optional[str] = None
    cy_amount: float
    py_amount: float
    type: Optional[str] = None
    suggested_classification: Optional[str] = None
    final_classification: Optional[str] = None
    financial_statement: Optional[str] = None
    note_number: Optional[str] = None
    current_non_current: Optional[str] = None
    user_override: bool = False

    class Config:
        from_attributes = True

class MappingUpdateRequest(BaseModel):
    id: int
    final_classification: str
    financial_statement: str
    note_number: str
    current_non_current: str

class RuleCreateRequest(BaseModel):
    pattern: str
    target_classification: str
    target_statement: str
    note_number: str
    current_non_current: str

class NoteSchema(BaseModel):
    id: int
    note_number: str
    title: str
    content: str
    suggested_content: str
    table_json: Optional[str] = None
    is_modified: bool

    class Config:
        from_attributes = True

class NoteUpdateRequest(BaseModel):
    content: str

class AccountingPolicySchema(BaseModel):
    id: int
    policy_number: str
    title: str
    content: str
    suggested_content: str
    is_applicable: bool
    is_modified: bool

    class Config:
        from_attributes = True

class AccountingPolicyUpdateRequest(BaseModel):
    content: str

class AccountingPolicyToggleRequest(BaseModel):
    is_applicable: bool

class BalanceSheetLine(BaseModel):
    particulars: str
    note_number: str
    cy_amount: float
    py_amount: float
    is_header: bool = False
    is_subtotal: bool = False
    is_total: bool = False

class ProfitAndLossLine(BaseModel):
    particulars: str
    note_number: str
    cy_amount: float
    py_amount: float
    is_header: bool = False
    is_subtotal: bool = False
    is_total: bool = False

class FinancialStatementResponse(BaseModel):
    balance_sheet: List[BalanceSheetLine]
    profit_and_loss: List[ProfitAndLossLine]
    is_tallied: bool
    difference: float

class RatioItem(BaseModel):
    code: str
    name: str
    formula: str
    cy_value: float
    py_value: float
    unit: str
    movement: str
    interpretation: str

class ValidationItem(BaseModel):
    code: str
    check_name: str
    category: str  # Upload / Accounting / Financial / Disclosure
    status: str    # Passed / Warning / Critical
    message: str
    details: str

class CashFlowAdjustmentSchema(BaseModel):
    id: int
    client_id: int
    adjustment_type: str
    description: str
    amount: float
    py_amount: float
    category: str
    remarks: Optional[str] = None

    class Config:
        from_attributes = True

class CashFlowAdjustmentCreate(BaseModel):
    adjustment_type: str
    description: str
    amount: float
    py_amount: float = 0.0
    category: str = "Operating"
    remarks: Optional[str] = None

class CashFlowLine(BaseModel):
    particulars: str
    cy_amount: float
    py_amount: float
    is_header: bool = False
    is_subtotal: bool = False
    is_total: bool = False
    indent: int = 0

class CashFlowWorkingItem(BaseModel):
    particulars: str
    source_sheet: str = ""
    section: str = ""
    cy_balance: float
    py_balance: float
    delta: float
    movement: float = 0.0
    effect_on_cash: float
    formula_used: str = ""
    review_comment: str = ""
    category: str

class CashFlowResponse(BaseModel):
    statement: List[CashFlowLine]
    working: List[CashFlowWorkingItem]
    opening_cash: float
    closing_cash: float
    py_opening_cash: float
    py_closing_cash: float
    net_movement: float
    py_net_movement: float
    is_reconciled: bool
    difference: float


# -------------------------------------------------------------
# USER MANAGEMENT & AUTHENTICATION SCHEMAS
# -------------------------------------------------------------
class UserSchema(BaseModel):
    id: int
    employee_code: str
    name: str
    email: str
    mobile: Optional[str] = None
    department: str
    role: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    employee_code: str
    name: str
    email: str
    mobile: Optional[str] = None
    department: str = "Audit & Assurance"
    role: str = "Executive"
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class LoginRequest(BaseModel):
    login_id: str  # Email or Employee Code
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 1800  # 30 minutes
    user: UserSchema


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    user_id: int
    new_password: str

