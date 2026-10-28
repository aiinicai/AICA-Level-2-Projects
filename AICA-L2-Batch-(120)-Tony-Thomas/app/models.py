import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base

class Account(Base):
    __tablename__ = "accounts"

    account_code = Column(String(50), primary_key=True, index=True)
    account_name = Column(String(150), nullable=False)
    account_type = Column(String(50), nullable=False)  # Asset, Liability, Equity, Revenue, Expense
    sub_category = Column(String(100), nullable=False)
    is_control_account = Column(Boolean, default=False)
    opening_debit = Column(Float, default=0.0)
    opening_credit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    voucher_lines = relationship("VoucherLine", back_populates="account")
    budgets = relationship("Budget", back_populates="account")

class JournalVoucher(Base):
    __tablename__ = "journal_vouchers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    voucher_no = Column(String(50), unique=True, index=True, nullable=False)
    posting_date = Column(Date, nullable=False, default=datetime.date.today)
    source_module = Column(String(50), nullable=False)  # OB, GL-JV, AR-INV, AR-RCPT, PO-GRN, AP-INV, AP-PMT, TAX
    document_ref = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    total_debit = Column(Float, default=0.0)
    total_credit = Column(Float, default=0.0)
    status = Column(String(50), default="Approved")  # Draft, Pending Approval, Approved, Rejected
    created_by = Column(String(100), default="Submitter")
    approved_by = Column(String(100), nullable=True)
    rejection_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    lines = relationship("VoucherLine", back_populates="voucher", cascade="all, delete-orphan")

class VoucherLine(Base):
    __tablename__ = "voucher_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    voucher_id = Column(Integer, ForeignKey("journal_vouchers.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, nullable=False, default=1)
    account_code = Column(String(50), ForeignKey("accounts.account_code"), nullable=False)
    account_name = Column(String(150), nullable=False)
    description = Column(String(255), default="")
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)

    voucher = relationship("JournalVoucher", back_populates="lines")
    account = relationship("Account", back_populates="voucher_lines")

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fiscal_year = Column(Integer, nullable=False, default=2026)
    account_code = Column(String(50), ForeignKey("accounts.account_code"), nullable=False)
    department = Column(String(100), nullable=False)
    annual_budget = Column(Float, default=0.0)
    notes = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    account = relationship("Account", back_populates="budgets")

class Vendor(Base):
    __tablename__ = "vendors"

    vendor_code = Column(String(50), primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    trn = Column(String(50), nullable=False)
    payment_terms = Column(String(100), default="Net 30")
    bank_details = Column(String(255), default="")
    email = Column(String(100), default="")
    phone = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Customer(Base):
    __tablename__ = "customers"

    customer_code = Column(String(50), primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    trn = Column(String(50), nullable=False)
    email = Column(String(100), default="")
    phone = Column(String(50), default="")
    billing_address = Column(Text, default="")
    credit_limit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class TaxCode(Base):
    __tablename__ = "tax_codes"

    code = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    rate = Column(Float, default=5.0)  # percentage, e.g. 5.0 for 5%
    type = Column(String(50), default="Both")  # Sales, Purchase, Both
    description = Column(String(255), default="")

class PurchaseRequisition(Base):
    __tablename__ = "purchase_requisitions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pr_number = Column(String(50), unique=True, index=True, nullable=False)
    pr_date = Column(Date, nullable=False, default=datetime.date.today)
    department = Column(String(100), nullable=False)
    status = Column(String(50), default="Draft")  # Draft, Pending Approval, Approved, Rejected, Converted to PO
    total_amount = Column(Float, default=0.0)
    budget_override = Column(Boolean, default=False)
    created_by = Column(String(100), default="Submitter")
    approved_by = Column(String(100), nullable=True)
    rejection_comment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    lines = relationship("PRLine", back_populates="pr", cascade="all, delete-orphan")

class PRLine(Base):
    __tablename__ = "pr_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pr_id = Column(Integer, ForeignKey("purchase_requisitions.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, default=1)
    description = Column(String(255), nullable=False)
    account_code = Column(String(50), ForeignKey("accounts.account_code"), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)

    pr = relationship("PurchaseRequisition", back_populates="lines")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    po_number = Column(String(50), unique=True, index=True, nullable=False)
    pr_number = Column(String(50), nullable=True)
    po_date = Column(Date, nullable=False, default=datetime.date.today)
    delivery_date = Column(Date, nullable=False, default=datetime.date.today)
    vendor_code = Column(String(50), ForeignKey("vendors.vendor_code"), nullable=False)
    tax_code = Column(String(50), ForeignKey("tax_codes.code"), default="VAT-STD-5")
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(50), default="Draft")  # Draft, Pending Approval, Approved, Rejected, Partially Received, Fully Received
    created_by = Column(String(100), default="Submitter")
    approved_by = Column(String(100), nullable=True)
    rejection_comment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    vendor = relationship("Vendor")
    tax = relationship("TaxCode")
    lines = relationship("POLine", back_populates="po", cascade="all, delete-orphan")

class POLine(Base):
    __tablename__ = "po_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, default=1)
    item_code = Column(String(50), nullable=True)
    description = Column(String(255), nullable=False)
    account_code = Column(String(50), ForeignKey("accounts.account_code"), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    received_qty = Column(Float, default=0.0)
    invoiced_qty = Column(Float, default=0.0)
    line_subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)

    po = relationship("PurchaseOrder", back_populates="lines")

class GoodsReceiptNote(Base):
    __tablename__ = "goods_receipt_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    grn_number = Column(String(50), unique=True, index=True, nullable=False)
    po_number = Column(String(50), nullable=False)
    grn_date = Column(Date, nullable=False, default=datetime.date.today)
    vendor_delivery_ref = Column(String(100), nullable=True)
    status = Column(String(50), default="Draft")  # Draft, Pending Approval, Approved, Rejected
    voucher_no = Column(String(50), nullable=True)
    created_by = Column(String(100), default="Submitter")
    approved_by = Column(String(100), nullable=True)
    rejection_comment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    lines = relationship("GRNLine", back_populates="grn", cascade="all, delete-orphan")

class GRNLine(Base):
    __tablename__ = "grn_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    grn_id = Column(Integer, ForeignKey("goods_receipt_notes.id", ondelete="CASCADE"), nullable=False)
    po_line_id = Column(Integer, nullable=True)
    item_code = Column(String(50), nullable=True)
    account_code = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    received_qty = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    line_amount = Column(Float, default=0.0)

    grn = relationship("GoodsReceiptNote", back_populates="lines")

class APInvoice(Base):
    __tablename__ = "ap_invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    invoice_mode = Column(String(50), default="Mode_A_PO")  # Mode_A_PO, Mode_B_Direct
    vendor_code = Column(String(50), ForeignKey("vendors.vendor_code"), nullable=False)
    vendor_invoice_ref = Column(String(100), nullable=False)
    po_number = Column(String(50), nullable=True)
    grn_number = Column(String(50), nullable=True)
    invoice_date = Column(Date, nullable=False, default=datetime.date.today)
    due_date = Column(Date, nullable=False, default=datetime.date.today)
    expense_account_code = Column(String(50), nullable=True)
    tax_code = Column(String(50), ForeignKey("tax_codes.code"), default="VAT-STD-5")
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    status = Column(String(50), default="Draft")  # Draft, Pending Approval, Approved, Rejected
    payment_status = Column(String(50), default="Unpaid")  # Unpaid, Partially Paid, Paid
    voucher_no = Column(String(50), nullable=True)
    created_by = Column(String(100), default="Submitter")
    approved_by = Column(String(100), nullable=True)
    rejection_comment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    vendor = relationship("Vendor")
    tax = relationship("TaxCode")

class APPayment(Base):
    __tablename__ = "ap_payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    payment_number = Column(String(50), unique=True, index=True, nullable=False)
    payment_date = Column(Date, nullable=False, default=datetime.date.today)
    vendor_code = Column(String(50), ForeignKey("vendors.vendor_code"), nullable=False)
    bank_account_code = Column(String(50), ForeignKey("accounts.account_code"), nullable=False)
    payment_ref = Column(String(100), nullable=False)
    payment_method = Column(String(50), default="Bank Transfer")
    total_amount = Column(Float, default=0.0)
    status = Column(String(50), default="Draft")  # Draft, Pending Approval, Approved, Rejected
    voucher_no = Column(String(50), nullable=True)
    created_by = Column(String(100), default="Submitter")
    approved_by = Column(String(100), nullable=True)
    rejection_comment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    vendor = relationship("Vendor")
    bank_account = relationship("Account")
    lines = relationship("APPaymentLine", back_populates="payment", cascade="all, delete-orphan")

class APPaymentLine(Base):
    __tablename__ = "ap_payment_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    payment_id = Column(Integer, ForeignKey("ap_payments.id", ondelete="CASCADE"), nullable=False)
    ap_invoice_id = Column(Integer, ForeignKey("ap_invoices.id"), nullable=False)
    invoice_number = Column(String(50), nullable=False)
    amount_paid = Column(Float, default=0.0)

    payment = relationship("APPayment", back_populates="lines")
    invoice = relationship("APInvoice")

class ARInvoice(Base):
    __tablename__ = "ar_invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_code = Column(String(50), ForeignKey("customers.customer_code"), nullable=False)
    invoice_date = Column(Date, nullable=False, default=datetime.date.today)
    due_date = Column(Date, nullable=False, default=datetime.date.today)
    subtotal = Column(Float, default=0.0)
    discount_total = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    status = Column(String(50), default="Draft")  # Draft, Pending Approval, Approved, Rejected
    payment_status = Column(String(50), default="Unpaid")  # Unpaid, Partially Paid, Paid
    voucher_no = Column(String(50), nullable=True)
    created_by = Column(String(100), default="Submitter")
    approved_by = Column(String(100), nullable=True)
    rejection_comment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer")
    lines = relationship("ARInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")

class ARInvoiceLine(Base):
    __tablename__ = "ar_invoice_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("ar_invoices.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(Integer, default=1)
    item_code = Column(String(50), nullable=True)
    description = Column(String(255), nullable=False)
    revenue_account_code = Column(String(50), ForeignKey("accounts.account_code"), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    tax_code = Column(String(50), ForeignKey("tax_codes.code"), default="VAT-STD-5")
    net_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)

    invoice = relationship("ARInvoice", back_populates="lines")
    revenue_account = relationship("Account")
    tax = relationship("TaxCode")

class ARReceipt(Base):
    __tablename__ = "ar_receipts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    receipt_number = Column(String(50), unique=True, index=True, nullable=False)
    receipt_date = Column(Date, nullable=False, default=datetime.date.today)
    customer_code = Column(String(50), ForeignKey("customers.customer_code"), nullable=False)
    bank_account_code = Column(String(50), ForeignKey("accounts.account_code"), nullable=False)
    receipt_ref = Column(String(100), nullable=False)
    receipt_method = Column(String(50), default="Bank Wire")
    total_amount = Column(Float, default=0.0)
    status = Column(String(50), default="Draft")  # Draft, Pending Approval, Approved, Rejected
    voucher_no = Column(String(50), nullable=True)
    created_by = Column(String(100), default="Submitter")
    approved_by = Column(String(100), nullable=True)
    rejection_comment = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer")
    bank_account = relationship("Account")
    lines = relationship("ARReceiptLine", back_populates="receipt", cascade="all, delete-orphan")

class ARReceiptLine(Base):
    __tablename__ = "ar_receipt_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    receipt_id = Column(Integer, ForeignKey("ar_receipts.id", ondelete="CASCADE"), nullable=False)
    ar_invoice_id = Column(Integer, ForeignKey("ar_invoices.id"), nullable=False)
    invoice_number = Column(String(50), nullable=False)
    amount_received = Column(Float, default=0.0)

    receipt = relationship("ARReceipt", back_populates="lines")
    invoice = relationship("ARInvoice")

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    category = Column(String(100), default="Grocery & Packaged Goods")
    barcode = Column(String(50), nullable=True)
    unit = Column(String(50), default="Pcs")
    cost_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    stock_quantity = Column(Float, default=0.0)
    reorder_level = Column(Float, default=10.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    movement_date = Column(Date, nullable=False, default=datetime.date.today)
    item_code = Column(String(50), nullable=False, index=True)
    item_name = Column(String(150), nullable=False)
    movement_type = Column(String(50), nullable=False)  # OPENING, PURCHASE_RECEIPT, SALES_DISPATCH, STOCK_ADJUSTMENT
    reference_doc = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)  # positive for in, negative for out
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CompanySetting(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(150), default="Demo Business 48")
    company_trn = Column(String(100), default="DEMO-TRN")
    company_address = Column(String(255), default="Fictional Demo Address")
    currency = Column(String(20), default="USD")
    currency_symbol = Column(String(10), default="$")
    phone = Column(String(50), default="DEMO-PHONE")
    email = Column(String(100), default="demo@example.com")

class ARCreditNote(Base):
    __tablename__ = "ar_credit_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    credit_note_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_code = Column(String(50), ForeignKey("customers.customer_code"), nullable=False)
    original_invoice_number = Column(String(50), nullable=True)
    credit_note_date = Column(Date, nullable=False, default=datetime.date.today)
    reason = Column(String(255), nullable=False)
    subtotal = Column(Float, default=0.0)
    tax_code = Column(String(50), default="VAT-STD-5")
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(50), default="Approved")
    voucher_no = Column(String(50), nullable=True)
    created_by = Column(String(100), default="Owner / Accountant")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer")

class APCreditNote(Base):
    __tablename__ = "ap_credit_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    credit_note_number = Column(String(50), unique=True, index=True, nullable=False)
    vendor_code = Column(String(50), ForeignKey("vendors.vendor_code"), nullable=False)
    original_invoice_number = Column(String(50), nullable=True)
    credit_note_date = Column(Date, nullable=False, default=datetime.date.today)
    reason = Column(String(255), nullable=False)
    subtotal = Column(Float, default=0.0)
    tax_code = Column(String(50), default="VAT-STD-5")
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(50), default="Approved")
    voucher_no = Column(String(50), nullable=True)
    created_by = Column(String(100), default="Owner / Accountant")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    vendor = relationship("Vendor")


