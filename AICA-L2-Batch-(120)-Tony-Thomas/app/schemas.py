import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Account Schemas
class AccountBase(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    sub_category: str
    is_control_account: bool = False
    opening_debit: float = 0.0
    opening_credit: float = 0.0

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

class OpeningTBUploadRow(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    sub_category: str
    is_control_account: bool = False
    opening_debit: float = 0.0
    opening_credit: float = 0.0

class OpeningTBValidationResponse(BaseModel):
    valid: bool
    total_debit: float
    total_credit: float
    variance: float
    row_count: int
    message: str

# Journal Voucher Schemas
class VoucherLineCreate(BaseModel):
    account_code: str
    description: Optional[str] = ""
    debit: float = 0.0
    credit: float = 0.0

class VoucherLineResponse(BaseModel):
    id: int
    line_no: int
    account_code: str
    account_name: str
    description: Optional[str] = ""
    debit: float
    credit: float

    class Config:
        from_attributes = True

class JournalVoucherCreate(BaseModel):
    posting_date: datetime.date
    source_module: str = "GL-JV"
    document_ref: str
    description: str
    lines: List[VoucherLineCreate]

class JournalVoucherResponse(BaseModel):
    id: int
    voucher_no: str
    posting_date: datetime.date
    source_module: str
    document_ref: str
    description: str
    total_debit: float
    total_credit: float
    status: str
    created_by: str
    approved_by: Optional[str] = None
    rejection_comment: Optional[str] = None
    created_at: datetime.datetime
    lines: List[VoucherLineResponse] = []

    class Config:
        from_attributes = True

# Budget Schemas
class BudgetCreate(BaseModel):
    fiscal_year: int = 2026
    account_code: str
    department: str
    annual_budget: float
    notes: Optional[str] = ""

class BudgetResponse(BaseModel):
    id: int
    fiscal_year: int
    account_code: str
    account_name: Optional[str] = ""
    department: str
    annual_budget: float
    pre_encumbrance: float = 0.0
    encumbrance: float = 0.0
    actual_consumed: float = 0.0
    available_budget: float = 0.0
    utilization_percentage: float = 0.0
    notes: Optional[str] = ""

    class Config:
        from_attributes = True

class BudgetCheckRequest(BaseModel):
    account_code: str
    amount: float
    department: Optional[str] = None

class BudgetCheckResponse(BaseModel):
    passed: bool
    account_code: str
    account_name: str
    annual_budget: float
    committed_amount: float  # pre-encumbrance + encumbrance + actual
    available_budget: float
    requested_amount: float
    variance: float
    message: str

# Vendor & Customer
class VendorCreate(BaseModel):
    vendor_code: str
    name: str
    trn: str
    payment_terms: str = "Net 30"
    bank_details: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""

class VendorResponse(VendorCreate):
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

class VendorUpdate(BaseModel):
    name: Optional[str] = None
    trn: Optional[str] = None
    payment_terms: Optional[str] = None
    bank_details: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class CustomerCreate(BaseModel):
    customer_code: str
    name: str
    trn: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    billing_address: Optional[str] = ""
    credit_limit: float = 0.0

class CustomerResponse(CustomerCreate):
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    trn: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    billing_address: Optional[str] = None
    credit_limit: Optional[float] = None

class TaxCodeCreate(BaseModel):
    code: str
    name: str
    rate: float
    type: str = "Both"
    description: Optional[str] = ""

class TaxCodeResponse(TaxCodeCreate):
    class Config:
        from_attributes = True

# PR Schemas
class PRLineCreate(BaseModel):
    description: str
    account_code: str
    quantity: float
    unit_price: float

class PRLineResponse(BaseModel):
    id: int
    line_no: int
    description: str
    account_code: str
    quantity: float
    unit_price: float
    total_amount: float

    class Config:
        from_attributes = True

class PRCreate(BaseModel):
    pr_date: datetime.date
    department: str
    notes: Optional[str] = ""
    lines: List[PRLineCreate]

class PRResponse(BaseModel):
    id: int
    pr_number: str
    pr_date: datetime.date
    department: str
    status: str
    total_amount: float
    budget_override: bool
    created_by: str
    approved_by: Optional[str] = None
    rejection_comment: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime
    lines: List[PRLineResponse] = []

    class Config:
        from_attributes = True

# PO Schemas
class POLineCreate(BaseModel):
    item_code: Optional[str] = None
    description: str
    account_code: str
    quantity: float
    unit_price: float

class POLineResponse(BaseModel):
    id: int
    line_no: int
    item_code: Optional[str] = None
    description: str
    account_code: str
    quantity: float
    unit_price: float
    received_qty: float
    invoiced_qty: float
    line_subtotal: float
    tax_amount: float
    line_total: float

    class Config:
        from_attributes = True

class POCreate(BaseModel):
    pr_number: Optional[str] = None
    po_date: datetime.date
    delivery_date: datetime.date
    vendor_code: str
    tax_code: str = "VAT-STD-5"
    notes: Optional[str] = ""
    lines: List[POLineCreate]

class POResponse(BaseModel):
    id: int
    po_number: str
    pr_number: Optional[str] = None
    po_date: datetime.date
    delivery_date: datetime.date
    vendor_code: str
    vendor_name: Optional[str] = ""
    tax_code: str
    subtotal: float
    tax_amount: float
    total_amount: float
    status: str
    created_by: str
    approved_by: Optional[str] = None
    rejection_comment: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime
    lines: List[POLineResponse] = []

    class Config:
        from_attributes = True

# GRN Schemas
class GRNLineCreate(BaseModel):
    po_line_id: int
    item_code: Optional[str] = None
    account_code: str
    description: str
    received_qty: float
    unit_price: float

class GRNLineResponse(BaseModel):
    id: int
    po_line_id: Optional[int] = None
    item_code: Optional[str] = None
    account_code: str
    description: str
    received_qty: float
    unit_price: float
    line_amount: float

    class Config:
        from_attributes = True

class GRNCreate(BaseModel):
    po_number: str
    grn_date: datetime.date
    vendor_delivery_ref: Optional[str] = ""
    notes: Optional[str] = ""
    lines: List[GRNLineCreate]

class GRNResponse(BaseModel):
    id: int
    grn_number: str
    po_number: str
    grn_date: datetime.date
    vendor_delivery_ref: Optional[str] = None
    status: str
    voucher_no: Optional[str] = None
    created_by: str
    approved_by: Optional[str] = None
    rejection_comment: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime
    total_amount: Optional[float] = 0.0
    lines: List[GRNLineResponse] = []

    class Config:
        from_attributes = True

# AP Invoice Schemas
class APInvoiceCreate(BaseModel):
    invoice_mode: str = "Mode_A_PO"  # Mode_A_PO, Mode_B_Direct
    vendor_code: str
    vendor_invoice_ref: str
    po_number: Optional[str] = None
    grn_number: Optional[str] = None
    invoice_date: datetime.date
    due_date: datetime.date
    expense_account_code: Optional[str] = None
    tax_code: str = "VAT-STD-5"
    subtotal: float
    tax_amount: float
    total_amount: float
    notes: Optional[str] = ""

class APInvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    invoice_mode: str
    vendor_code: str
    vendor_name: Optional[str] = ""
    vendor_invoice_ref: str
    po_number: Optional[str] = None
    grn_number: Optional[str] = None
    invoice_date: datetime.date
    due_date: datetime.date
    expense_account_code: Optional[str] = None
    tax_code: str
    subtotal: float
    tax_amount: float
    total_amount: float
    paid_amount: float
    remaining_balance: float = 0.0
    status: str
    payment_status: str
    voucher_no: Optional[str] = None
    created_by: str
    approved_by: Optional[str] = None
    rejection_comment: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# AP Payment Schemas
class APPaymentLineCreate(BaseModel):
    ap_invoice_id: int
    invoice_number: str
    amount_paid: float

class APPaymentLineResponse(BaseModel):
    id: int
    ap_invoice_id: int
    invoice_number: str
    amount_paid: float

    class Config:
        from_attributes = True

class APPaymentCreate(BaseModel):
    payment_date: datetime.date
    vendor_code: str
    bank_account_code: str
    payment_ref: str
    payment_method: str = "Bank Transfer"
    notes: Optional[str] = ""
    lines: List[APPaymentLineCreate]

class APPaymentResponse(BaseModel):
    id: int
    payment_number: str
    payment_date: datetime.date
    vendor_code: str
    vendor_name: Optional[str] = ""
    bank_account_code: str
    payment_ref: str
    payment_method: str
    total_amount: float
    status: str
    voucher_no: Optional[str] = None
    created_by: str
    approved_by: Optional[str] = None
    rejection_comment: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime
    lines: List[APPaymentLineResponse] = []

    class Config:
        from_attributes = True

# AR Invoice Schemas
class ARInvoiceLineCreate(BaseModel):
    item_code: Optional[str] = None
    description: str
    revenue_account_code: str
    quantity: float
    unit_price: float
    discount_amount: float = 0.0
    tax_code: str = "VAT-STD-5"

class ARInvoiceLineResponse(BaseModel):
    id: int
    line_no: int
    item_code: Optional[str] = None
    description: str
    revenue_account_code: str
    quantity: float
    unit_price: float
    discount_amount: float
    tax_code: str
    net_amount: float
    tax_amount: float
    total_amount: float

    class Config:
        from_attributes = True

class ARInvoiceCreate(BaseModel):
    customer_code: str
    invoice_date: datetime.date
    due_date: datetime.date
    notes: Optional[str] = ""
    lines: List[ARInvoiceLineCreate]

class ARInvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    customer_code: str
    customer_name: Optional[str] = ""
    customer_trn: Optional[str] = ""
    customer_address: Optional[str] = ""
    invoice_date: datetime.date
    due_date: datetime.date
    subtotal: float
    discount_total: float
    tax_amount: float
    total_amount: float
    paid_amount: float
    remaining_balance: float = 0.0
    status: str
    payment_status: str
    voucher_no: Optional[str] = None
    created_by: str
    approved_by: Optional[str] = None
    rejection_comment: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime
    lines: List[ARInvoiceLineResponse] = []

    class Config:
        from_attributes = True

# AR Receipt Schemas
class ARReceiptLineCreate(BaseModel):
    ar_invoice_id: int
    invoice_number: str
    amount_received: float

class ARReceiptLineResponse(BaseModel):
    id: int
    ar_invoice_id: int
    invoice_number: str
    amount_received: float

    class Config:
        from_attributes = True

class ARReceiptCreate(BaseModel):
    receipt_date: datetime.date
    customer_code: str
    bank_account_code: str
    receipt_ref: str
    receipt_method: str = "Bank Wire"
    notes: Optional[str] = ""
    lines: List[ARReceiptLineCreate]

class ARReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    receipt_date: datetime.date
    customer_code: str
    customer_name: Optional[str] = ""
    bank_account_code: str
    receipt_ref: str
    receipt_method: str
    total_amount: float
    status: str
    voucher_no: Optional[str] = None
    created_by: str
    approved_by: Optional[str] = None
    rejection_comment: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime
    lines: List[ARReceiptLineResponse] = []

    class Config:
        from_attributes = True

# Workflow & Approval Schemas
class ApprovalActionRequest(BaseModel):
    action: str  # "approve" or "reject"
    comment: Optional[str] = ""
    budget_override: Optional[bool] = False
    approved_by: Optional[str] = "Checker (Finance Manager)"

class ApprovalItemResponse(BaseModel):
    module: str  # GL, PR, PO, GRN, AP-INV, AP-PMT, AR-INV, AR-RCPT
    document_id: int
    document_number: str
    date: datetime.date
    party_or_desc: str
    amount: float
    status: str
    created_by: str
    created_at: datetime.datetime

# Reports Schemas
class TrialBalanceRow(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    sub_category: str
    opening_debit: float
    opening_credit: float
    period_debit: float
    period_credit: float
    closing_debit: float
    closing_credit: float

class TrialBalanceReport(BaseModel):
    as_of_date: datetime.date
    rows: List[TrialBalanceRow]
    total_opening_debit: float
    total_opening_credit: float
    total_period_debit: float
    total_period_credit: float
    total_closing_debit: float
    total_closing_credit: float
    is_balanced: bool

class ProfitLossReport(BaseModel):
    from_date: datetime.date
    to_date: datetime.date
    revenue_items: List[Dict[str, Any]]
    total_revenue: float
    cogs_items: List[Dict[str, Any]]
    total_cogs: float
    gross_profit: float
    gross_margin_pct: float
    operating_expenses: List[Dict[str, Any]]
    total_operating_expenses: float
    net_profit: float
    net_margin_pct: float

class BalanceSheetSection(BaseModel):
    title: str
    items: List[Dict[str, Any]]
    total: float

class BalanceSheetReport(BaseModel):
    as_of_date: datetime.date
    assets: BalanceSheetSection
    liabilities: BalanceSheetSection
    equity: BalanceSheetSection
    total_assets: float
    total_liabilities_and_equity: float
    variance: float
    is_balanced: bool

class TaxReturnBox(BaseModel):
    box_number: str
    title: str
    net_amount: float
    tax_amount: float
    description: str

class TaxReturnReport(BaseModel):
    from_date: datetime.date
    to_date: datetime.date
    box1_output_standard: TaxReturnBox
    box2_zero_exempt: TaxReturnBox
    box3_input_standard: TaxReturnBox
    box4_net_tax: TaxReturnBox
    is_payable: bool

class DashboardKPIs(BaseModel):
    total_revenue: float
    total_expenses: float
    net_profit: float
    net_margin_pct: float
    cash_bank_balance: float
    open_ar: float
    open_ap: float
    net_tax_payable: float
    budget_utilization_pct: float
    pending_approvals_count: int
    total_inventory_valuation: Optional[float] = 0.0

# Company Setting Schemas
class CompanySettingBase(BaseModel):
    company_name: str
    company_trn: str
    company_address: str
    currency: str = "USD"
    currency_symbol: str = "$"
    phone: Optional[str] = ""
    email: Optional[str] = ""

class CompanySettingUpdate(CompanySettingBase):
    pass

class CompanySettingResponse(CompanySettingBase):
    id: int
    class Config:
        from_attributes = True

# Inventory Schemas
class InventoryItemBase(BaseModel):
    item_code: str
    name: str
    category: str = "Grocery & Packaged Goods"
    barcode: Optional[str] = ""
    unit: str = "Pcs"
    cost_price: float = 0.0
    selling_price: float = 0.0
    stock_quantity: float = 0.0
    reorder_level: float = 10.0

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    barcode: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    reorder_level: Optional[float] = None

class InventoryItemResponse(InventoryItemBase):
    id: int
    total_value: float = 0.0
    is_low_stock: bool = False
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

class StockAdjustmentCreate(BaseModel):
    item_code: str
    adjustment_type: str  # "ADD" or "REDUCE" or "SET"
    quantity: float
    reason: str  # "Damage / Spoilage", "Stock Take Count", "Write-off", "Opening Count"

class StockMovementResponse(BaseModel):
    id: int
    movement_date: datetime.date
    item_code: str
    item_name: str
    movement_type: str
    reference_doc: str
    quantity: float
    unit_cost: float
    total_cost: float
    notes: Optional[str] = None
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

# Credit Note Schemas
class ARCreditNoteCreate(BaseModel):
    customer_code: str
    original_invoice_number: Optional[str] = None
    original_invoice_ref: Optional[str] = None
    credit_note_date: Optional[datetime.date] = None
    reason: str
    subtotal: float
    tax_code: Optional[str] = "STANDARD_5"
    tax_amount: float = 0.0
    total_amount: Optional[float] = None
    total_credit: Optional[float] = None

class ARCreditNoteResponse(BaseModel):
    id: int
    credit_note_number: str
    customer_code: str
    customer_name: Optional[str] = ""
    original_invoice_number: Optional[str] = None
    original_invoice_ref: Optional[str] = None
    credit_note_date: datetime.date
    reason: str
    subtotal: float
    tax_code: str
    tax_amount: float
    total_amount: float
    total_credit: Optional[float] = None
    status: str
    voucher_no: Optional[str] = None
    created_by: str
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

class APCreditNoteCreate(BaseModel):
    vendor_code: str
    original_invoice_number: Optional[str] = None
    original_invoice_ref: Optional[str] = None
    credit_note_date: Optional[datetime.date] = None
    reason: str
    subtotal: float
    tax_code: Optional[str] = "STANDARD_5"
    tax_amount: float = 0.0
    total_amount: Optional[float] = None
    total_credit: Optional[float] = None

class APCreditNoteResponse(BaseModel):
    id: int
    credit_note_number: str
    vendor_code: str
    vendor_name: Optional[str] = ""
    original_invoice_number: Optional[str] = None
    original_invoice_ref: Optional[str] = None
    credit_note_date: datetime.date
    reason: str
    subtotal: float
    tax_code: str
    tax_amount: float
    total_amount: float
    total_credit: Optional[float] = None
    status: str
    voucher_no: Optional[str] = None
    created_by: str
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


