import datetime
from sqlalchemy.orm import Session
from app import models, crud

def init_clean_database(db: Session, force_reset: bool = False):
    """
    Initializes a production-ready clean ERP database with ZERO dummy transactions.
    - Preserves existing user data (Company Profile, Opening Balances, Customers, Vendors).
    - Standard Chart of Accounts created with 0.00 opening balances if not already created.
    - Standard Tax Codes (5% VAT, 0%, Exempt).
    - All user entries are saved persistently in local SQLite erp_ledger.db.
    """
    models.Base.metadata.create_all(bind=db.get_bind())

    if force_reset:
        # Wipe all transactional & master data for clean production use
        db.query(models.VoucherLine).delete()
        db.query(models.JournalVoucher).delete()
        db.query(models.APPaymentLine).delete()
        db.query(models.APPayment).delete()
        db.query(models.APInvoice).delete()
        db.query(models.ARReceiptLine).delete()
        db.query(models.ARReceipt).delete()
        db.query(models.ARInvoiceLine).delete()
        db.query(models.ARInvoice).delete()
        db.query(models.GRNLine).delete()
        db.query(models.GoodsReceiptNote).delete()
        db.query(models.POLine).delete()
        db.query(models.PurchaseOrder).delete()
        db.query(models.PRLine).delete()
        db.query(models.PurchaseRequisition).delete()
        db.query(models.Budget).delete()
        db.query(models.StockMovement).delete()
        db.query(models.InventoryItem).delete()
        db.query(models.Customer).delete()
        db.query(models.Vendor).delete()
        for a in db.query(models.Account).all():
            a.opening_debit = 0.0
            a.opening_credit = 0.0
        db.commit()

    # 1. Company Settings (Preserve if user has already set it!)
    cs = db.query(models.CompanySetting).first()
    if not cs:
        cs = models.CompanySetting(
            company_name="Demo Business 21",
            company_trn="DEMO-TRN",
            company_address="Fictional Demo Address",
            phone="DEMO-PHONE",
            email="demo@example.com",
            currency="USD",
            currency_symbol="$"
        )
        db.add(cs)
        db.commit()

    # 2. Standard Tax Codes (Only create if not present)
    if db.query(models.TaxCode).count() == 0:
        tax_codes = [
            models.TaxCode(code="VAT-STD-5", name="Standard Indirect Tax 5%", rate=5.0, type="Both", description="Standard rate indirect tax / VAT"),
            models.TaxCode(code="VAT-ZERO-0", name="Zero-Rated Supplies 0%", rate=0.0, type="Both", description="Supplies taxed at zero percent"),
            models.TaxCode(code="VAT-EXEMPT", name="Exempt from Indirect Tax", rate=0.0, type="Both", description="Financial and exempt supplies")
        ]
        for tc in tax_codes:
            db.add(tc)
        db.commit()

    # 3. Standard Chart of Accounts (Only create if not present, with 0.00 opening balances!)
    if db.query(models.Account).count() == 0:
        accounts_data = [
            {"code": "1010", "name": "Cash at Bank - Primary Operating", "type": "Asset", "sub": "Bank", "ctrl": False},
            {"code": "1020", "name": "Cash at Bank - Payroll & Treasury", "type": "Asset", "sub": "Bank", "ctrl": False},
            {"code": "1100", "name": "Accounts Receivable Control", "type": "Asset", "sub": "Accounts Receivable", "ctrl": True},
            {"code": "1150", "name": "Input VAT / Tax Recoverable", "type": "Asset", "sub": "Tax Input", "ctrl": True},
            {"code": "1200", "name": "Inventory / Merchandise Store Stock", "type": "Asset", "sub": "Inventory/GRN", "ctrl": False},
            {"code": "1500", "name": "Property, Plant & Equipment", "type": "Asset", "sub": "Fixed Assets", "ctrl": False},
            
            {"code": "2000", "name": "Accounts Payable Control", "type": "Liability", "sub": "Accounts Payable", "ctrl": True},
            {"code": "2010", "name": "GRN Accrual (Uninvoiced Receipts)", "type": "Liability", "sub": "GRN Accrual", "ctrl": True},
            {"code": "2020", "name": "Output VAT / Tax Payable", "type": "Liability", "sub": "Tax Output", "ctrl": True},
            {"code": "2100", "name": "Accrued Payroll & Statutory Liabilities", "type": "Liability", "sub": "Accrued Liabilities", "ctrl": False},

            {"code": "3000", "name": "Share Capital", "type": "Equity", "sub": "Share Capital", "ctrl": False},
            {"code": "3010", "name": "Retained Earnings", "type": "Equity", "sub": "Retained Earnings", "ctrl": False},

            {"code": "4000", "name": "Sales Revenue - Wholesale & Retail", "type": "Revenue", "sub": "Sales Revenue", "ctrl": False},
            {"code": "4010", "name": "Sales Revenue - Consumer Goods Trading", "type": "Revenue", "sub": "Sales Revenue", "ctrl": False},
            {"code": "4020", "name": "Other Operating Income", "type": "Revenue", "sub": "Other Revenue", "ctrl": False},

            {"code": "5000", "name": "Cost of Goods Sold / Direct Materials", "type": "Expense", "sub": "Cost of Goods Sold", "ctrl": False},
            {"code": "5010", "name": "Direct Delivery & Packaging Costs", "type": "Expense", "sub": "Cost of Goods Sold", "ctrl": False},
            {"code": "6000", "name": "Salaries & Staff Benefits", "type": "Expense", "sub": "Operating Expense", "ctrl": False},
            {"code": "6010", "name": "Rent & Store Facilities", "type": "Expense", "sub": "Operating Expense", "ctrl": False},
            {"code": "6020", "name": "IT & Software Subscriptions", "type": "Expense", "sub": "Operating Expense", "ctrl": False},
            {"code": "6030", "name": "Advertising & Store Marketing", "type": "Expense", "sub": "Operating Expense", "ctrl": False},
            {"code": "6040", "name": "Legal & Audit Advisory Fees", "type": "Expense", "sub": "Operating Expense", "ctrl": False},
            {"code": "6050", "name": "Travel & Local Transport", "type": "Expense", "sub": "Operating Expense", "ctrl": False},
            {"code": "6060", "name": "Utilities & Store General Expenses", "type": "Expense", "sub": "Operating Expense", "ctrl": False}
        ]
        for itm in accounts_data:
            acc = models.Account(
                account_code=itm["code"],
                account_name=itm["name"],
                account_type=itm["type"],
                sub_category=itm["sub"],
                is_control_account=itm["ctrl"],
                opening_debit=0.0,
                opening_credit=0.0
            )
            db.add(acc)
        db.commit()

def seed_database(db: Session, force_reset: bool = False):
    init_clean_database(db, force_reset=force_reset)

def seed_demo_data(db: Session):
    """Explicitly loads a sample demo dataset for testing or presentation purposes."""
    init_clean_database(db, force_reset=True)
    today = datetime.date.today()

    # 1. Company Settings
    cs = db.query(models.CompanySetting).first()
    if not cs:
        cs = models.CompanySetting(
            company_name="Demo Business 13",
            company_trn="DEMO-TRN",
            company_address="Fictional Demo Address",
            phone="DEMO-PHONE",
            email="demo@example.com",
            currency="USD",
            currency_symbol="$"
        )
        db.add(cs)
    else:
        cs.company_name = "Demo Business 13"
    db.commit()

    # 2. Tax Codes
    tax_codes = [
        models.TaxCode(code="VAT-STD-5", name="Standard Indirect Tax 5%", rate=5.0, type="Both", description="Standard rate indirect tax / VAT"),
        models.TaxCode(code="VAT-ZERO-0", name="Zero-Rated Supplies 0%", rate=0.0, type="Both", description="Supplies taxed at zero percent"),
        models.TaxCode(code="VAT-EXEMPT", name="Exempt from Indirect Tax", rate=0.0, type="Both", description="Financial and exempt supplies")
    ]
    for tc in tax_codes:
        if not db.query(models.TaxCode).filter(models.TaxCode.code == tc.code).first():
            db.add(tc)
    db.commit()

    # 3. Chart of Accounts (24 Accounts across Asset, Liability, Equity, Revenue, Expense)
    accounts_data = [
        # Assets (1000 - 1999)
        {"code": "1010", "name": "Cash at Bank - Primary Operating", "type": "Asset", "sub": "Bank", "ctrl": False, "op_dr": 250000.0, "op_cr": 0.0},
        {"code": "1020", "name": "Cash at Bank - Payroll & Treasury", "type": "Asset", "sub": "Bank", "ctrl": False, "op_dr": 50000.0, "op_cr": 0.0},
        {"code": "1100", "name": "Accounts Receivable Control", "type": "Asset", "sub": "Accounts Receivable", "ctrl": True, "op_dr": 60000.0, "op_cr": 0.0},
        {"code": "1150", "name": "Input VAT / Tax Recoverable", "type": "Asset", "sub": "Tax Input", "ctrl": True, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "1200", "name": "Inventory / Goods in Transit", "type": "Asset", "sub": "Inventory/GRN", "ctrl": False, "op_dr": 40000.0, "op_cr": 0.0},
        {"code": "1500", "name": "Property, Plant & Equipment", "type": "Asset", "sub": "Fixed Assets", "ctrl": False, "op_dr": 100000.0, "op_cr": 0.0},
        
        # Liabilities (2000 - 2999)
        {"code": "2000", "name": "Accounts Payable Control", "type": "Liability", "sub": "Accounts Payable", "ctrl": True, "op_dr": 0.0, "op_cr": 45000.0},
        {"code": "2010", "name": "GRN Accrual (Uninvoiced Receipts)", "type": "Liability", "sub": "GRN Accrual", "ctrl": True, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "2020", "name": "Output VAT / Tax Payable", "type": "Liability", "sub": "Tax Output", "ctrl": True, "op_dr": 0.0, "op_cr": 5000.0},
        {"code": "2100", "name": "Accrued Payroll & Statutory Liabilities", "type": "Liability", "sub": "Accrued Liabilities", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},

        # Equity (3000 - 3999)
        {"code": "3000", "name": "Share Capital", "type": "Equity", "sub": "Share Capital", "ctrl": False, "op_dr": 0.0, "op_cr": 300000.0},
        {"code": "3010", "name": "Retained Earnings", "type": "Equity", "sub": "Retained Earnings", "ctrl": False, "op_dr": 0.0, "op_cr": 150000.0},

        # Revenue (4000 - 4999)
        {"code": "4000", "name": "Sales Revenue - Enterprise Solutions", "type": "Revenue", "sub": "Sales Revenue", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "4010", "name": "Sales Revenue - Cloud & Managed Services", "type": "Revenue", "sub": "Sales Revenue", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "4020", "name": "Other Operating Income", "type": "Revenue", "sub": "Other Revenue", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},

        # Expenses (5000 - 6999)
        {"code": "5000", "name": "Cost of Goods Sold / Direct Materials", "type": "Expense", "sub": "Cost of Goods Sold", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "5010", "name": "Direct Consulting & Subcontractor Fees", "type": "Expense", "sub": "Cost of Goods Sold", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "6000", "name": "Salaries & Staff Benefits", "type": "Expense", "sub": "Operating Expense", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "6010", "name": "Rent & Facilities Operations", "type": "Expense", "sub": "Operating Expense", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "6020", "name": "IT Infrastructure & Cloud Subscriptions", "type": "Expense", "sub": "Operating Expense", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "6030", "name": "Marketing, PR & Lead Generation", "type": "Expense", "sub": "Operating Expense", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "6040", "name": "Legal & Audit Advisory Fees", "type": "Expense", "sub": "Operating Expense", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "6050", "name": "Travel & Client Hospitality", "type": "Expense", "sub": "Operating Expense", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0},
        {"code": "6060", "name": "Office Supplies & Telecommunications", "type": "Expense", "sub": "Operating Expense", "ctrl": False, "op_dr": 0.0, "op_cr": 0.0}
    ]

    for item in accounts_data:
        acc = db.query(models.Account).filter(models.Account.account_code == item["code"]).first()
        if not acc:
            acc = models.Account(
                account_code=item["code"],
                account_name=item["name"],
                account_type=item["type"],
                sub_category=item["sub"],
                is_control_account=item["ctrl"],
                opening_debit=item["op_dr"],
                opening_credit=item["op_cr"]
            )
            db.add(acc)
        else:
            acc.opening_debit = item["op_dr"]
            acc.opening_credit = item["op_cr"]
    db.commit()

    # 4. Opening Balance Journal Voucher (OB-0001)
    ob_lines = []
    tot_dr = sum(i["op_dr"] for i in accounts_data)
    tot_cr = sum(i["op_cr"] for i in accounts_data)
    for i in accounts_data:
        if i["op_dr"] > 0 or i["op_cr"] > 0:
            ob_lines.append({
                "account_code": i["code"],
                "account_name": i["name"],
                "description": "Opening Balance Initialization",
                "debit": i["op_dr"],
                "credit": i["op_cr"]
            })

    crud.create_journal_voucher_entry(
        db=db,
        voucher_no="OB-0001",
        posting_date=datetime.date(today.year, 1, 1),
        source_module="OB",
        document_ref="OB-INIT",
        description="Opening Trial Balance Migration & Initialization",
        lines=ob_lines,
        created_by="System Admin",
        approved_by="Chief Financial Officer",
        status="Approved"
    )

    # 5. Vendors
    vendors = [
        models.Vendor(
            vendor_code="VEND-001",
            name="Demo Business 25",
            trn="DEMO-TRN",
            payment_terms="Net 30",
            bank_details="DEMO BANK DETAILS - NOT A REAL ACCOUNT",
            email="demo@example.com",
            phone="DEMO-PHONE"
        ),
        models.Vendor(
            vendor_code="VEND-002",
            name="Demo Business 27",
            trn="DEMO-TRN",
            payment_terms="Net 15",
            bank_details="DEMO BANK DETAILS - NOT A REAL ACCOUNT",
            email="demo@example.com",
            phone="DEMO-PHONE"
        ),
        models.Vendor(
            vendor_code="VEND-003",
            name="Demo Business 29",
            trn="DEMO-TRN",
            payment_terms="Net 30",
            bank_details="DEMO BANK DETAILS - NOT A REAL ACCOUNT",
            email="demo@example.com",
            phone="DEMO-PHONE"
        )
    ]
    for v in vendors:
        db.add(v)

    # 6. Customers
    customers = [
        models.Customer(
            customer_code="CUST-001",
            name="Demo Business 31",
            trn="DEMO-TRN",
            email="demo@example.com",
            phone="DEMO-PHONE",
            billing_address="Fictional Demo Address",
            credit_limit=250000.0
        ),
        models.Customer(
            customer_code="CUST-002",
            name="Demo Business 33",
            trn="DEMO-TRN",
            email="demo@example.com",
            phone="DEMO-PHONE",
            billing_address="Fictional Demo Address",
            credit_limit=350000.0
        ),
        models.Customer(
            customer_code="CUST-003",
            name="Demo Business 35",
            trn="DEMO-TRN",
            email="demo@example.com",
            phone="DEMO-PHONE",
            billing_address="Fictional Demo Address",
            credit_limit=150000.0
        )
    ]
    for c in customers:
        db.add(c)
    db.commit()

    # 7. Annual Budgets for Fiscal Year
    budgets = [
        models.Budget(fiscal_year=today.year, account_code="6000", department="Human Resources & Ops", annual_budget=200000.0, notes="Annual staffing & executive payroll"),
        models.Budget(fiscal_year=today.year, account_code="6010", department="General Administration", annual_budget=60000.0, notes="Office lease & physical facilities"),
        models.Budget(fiscal_year=today.year, account_code="6020", department="Information Technology", annual_budget=50000.0, notes="Cloud infrastructure, Azure & ERP licensing"),
        models.Budget(fiscal_year=today.year, account_code="6030", department="Sales & Marketing", annual_budget=45000.0, notes="Digital marketing campaigns & exhibitions"),
        models.Budget(fiscal_year=today.year, account_code="6040", department="Finance & Corporate", annual_budget=35000.0, notes="External audit, compliance and legal retainer"),
        models.Budget(fiscal_year=today.year, account_code="6050", department="Sales & Marketing", annual_budget=25000.0, notes="Client roadshows and executive travel"),
        models.Budget(fiscal_year=today.year, account_code="6060", department="General Administration", annual_budget=15000.0, notes="Stationery, printing, consumables")
    ]
    for b in budgets:
        db.add(b)
    db.commit()

    # 8. Sample Transactions (Approved Cycle 1 - P2P & O2C)
    # A. Approved PR
    pr1 = models.PurchaseRequisition(
        pr_number="PR-2026-0001",
        pr_date=today - datetime.timedelta(days=25),
        department="Information Technology",
        status="Converted to PO",
        total_amount=12000.0,
        budget_override=False,
        created_by="Submitter (Operations)",
        approved_by="Checker (Finance Manager)",
        notes="High-performance Azure cloud instances for ERP cluster"
    )
    db.add(pr1)
    db.flush()
    db.add(models.PRLine(
        pr_id=pr1.id,
        line_no=1,
        description="Azure Cloud Infrastructure Annual Allocation",
        account_code="6020",
        quantity=1.0,
        unit_price=12000.0,
        total_amount=12000.0
    ))
    db.commit()

    # B. Approved PO
    po1 = models.PurchaseOrder(
        po_number="PO-2026-0001",
        pr_number="PR-2026-0001",
        po_date=today - datetime.timedelta(days=24),
        delivery_date=today - datetime.timedelta(days=10),
        vendor_code="VEND-002",
        tax_code="VAT-STD-5",
        subtotal=12000.0,
        tax_amount=600.0,
        total_amount=12600.0,
        status="Fully Received",
        created_by="Submitter (Operations)",
        approved_by="Checker (Finance Manager)",
        notes="Standard delivery per Cloud Service Level Agreement"
    )
    db.add(po1)
    db.flush()
    db.add(models.POLine(
        po_id=po1.id,
        line_no=1,
        description="Azure Cloud Infrastructure Annual Allocation",
        account_code="6020",
        quantity=1.0,
        unit_price=12000.0,
        received_qty=1.0,
        invoiced_qty=1.0,
        line_subtotal=12000.0,
        tax_amount=600.0,
        line_total=12600.0
    ))
    db.commit()

    # C. Approved GRN
    grn1 = models.GoodsReceiptNote(
        grn_number="GRN-2026-0001",
        po_number="PO-2026-0001",
        grn_date=today - datetime.timedelta(days=20),
        vendor_delivery_ref="DN-EM-88210",
        status="Approved",
        voucher_no="PO-GRN-0001",
        created_by="Submitter (Operations)",
        approved_by="Checker (Finance Manager)",
        notes="Provisioning verified and acceptance sign-off complete"
    )
    db.add(grn1)
    db.flush()
    db.add(models.GRNLine(
        grn_id=grn1.id,
        po_line_id=1,
        account_code="6020",
        description="Azure Cloud Infrastructure Annual Allocation",
        received_qty=1.0,
        unit_price=12000.0,
        line_amount=12000.0
    ))
    db.commit()

    # GL Voucher for GRN
    crud.create_journal_voucher_entry(
        db=db,
        voucher_no="PO-GRN-0001",
        posting_date=today - datetime.timedelta(days=20),
        source_module="PO-GRN",
        document_ref="GRN-2026-0001",
        description="GRN Receipt Voucher for GRN-2026-0001 (PO: PO-2026-0001)",
        lines=[
            {"account_code": "6020", "account_name": "IT Infrastructure & Cloud Subscriptions", "description": "Cloud cluster receipt", "debit": 12000.0, "credit": 0.0},
            {"account_code": "2010", "account_name": "GRN Accrual (Uninvoiced Receipts)", "description": "Accrual for uninvoiced cloud service", "debit": 0.0, "credit": 12000.0}
        ],
        created_by="Submitter (Operations)",
        approved_by="Checker (Finance Manager)",
        status="Approved"
    )

    # D. Approved AP Invoice (Mode A - 3-Way Match)
    ap_inv1 = models.APInvoice(
        invoice_number="AP-INV-2026-0001",
        invoice_mode="Mode_A_PO",
        vendor_code="VEND-002",
        vendor_invoice_ref="INV-ECH-2026-992",
        po_number="PO-2026-0001",
        grn_number="GRN-2026-0001",
        invoice_date=today - datetime.timedelta(days=18),
        due_date=today + datetime.timedelta(days=12),
        tax_code="VAT-STD-5",
        subtotal=12000.0,
        tax_amount=600.0,
        total_amount=12600.0,
        paid_amount=12600.0,
        status="Approved",
        payment_status="Paid",
        voucher_no="AP-INV-0001",
        created_by="Submitter (Finance Officer)",
        approved_by="Checker (Finance Manager)",
        notes="Matched against PO-2026-0001 & GRN-2026-0001"
    )
    db.add(ap_inv1)
    db.commit()

    # GL Voucher for AP Invoice
    crud.create_journal_voucher_entry(
        db=db,
        voucher_no="AP-INV-0001",
        posting_date=today - datetime.timedelta(days=18),
        source_module="AP-INV",
        document_ref="AP-INV-2026-0001",
        description="AP Invoice AP-INV-2026-0001 from VEND-002",
        lines=[
            {"account_code": "2010", "account_name": "GRN Accrual (Uninvoiced Receipts)", "description": "Reversal of GRN accrual", "debit": 12000.0, "credit": 0.0},
            {"account_code": "1150", "account_name": "Input VAT / Tax Recoverable", "description": "Input indirect tax 5%", "debit": 600.0, "credit": 0.0},
            {"account_code": "2000", "account_name": "Accounts Payable Control", "description": "Payable to Emirates Cloud Hosting", "debit": 0.0, "credit": 12600.0}
        ],
        created_by="Submitter (Finance Officer)",
        approved_by="Checker (Finance Manager)",
        status="Approved"
    )

    # E. Approved AP Payment
    ap_pmt1 = models.APPayment(
        payment_number="AP-PMT-2026-0001",
        payment_date=today - datetime.timedelta(days=14),
        vendor_code="VEND-002",
        bank_account_code="1010",
        payment_ref="WTR-2026-0912",
        payment_method="Bank Transfer",
        total_amount=12600.0,
        status="Approved",
        voucher_no="AP-PMT-0001",
        created_by="Submitter (Finance Officer)",
        approved_by="Checker (Finance Manager)",
        notes="Electronic settlement via Primary Operating Bank"
    )
    db.add(ap_pmt1)
    db.flush()
    db.add(models.APPaymentLine(
        payment_id=ap_pmt1.id,
        ap_invoice_id=ap_inv1.id,
        invoice_number=ap_inv1.invoice_number,
        amount_paid=12600.0
    ))
    db.commit()

    # GL Voucher for AP Payment
    crud.create_journal_voucher_entry(
        db=db,
        voucher_no="AP-PMT-0001",
        posting_date=today - datetime.timedelta(days=14),
        source_module="AP-PMT",
        document_ref="AP-PMT-2026-0001",
        description="Disbursement to VEND-002 (Ref: WTR-2026-0912)",
        lines=[
            {"account_code": "2000", "account_name": "Accounts Payable Control", "description": "Settlement of AP-INV-2026-0001", "debit": 12600.0, "credit": 0.0},
            {"account_code": "1010", "account_name": "Cash at Bank - Primary Operating", "description": "Bank transfer out", "debit": 0.0, "credit": 12600.0}
        ],
        created_by="Submitter (Finance Officer)",
        approved_by="Checker (Finance Manager)",
        status="Approved"
    )

    # F. Approved AR Invoice (Sales to Apex Capital)
    ar_inv1 = models.ARInvoice(
        invoice_number="INV-2026-0001",
        customer_code="CUST-001",
        invoice_date=today - datetime.timedelta(days=15),
        due_date=today + datetime.timedelta(days=15),
        subtotal=85000.0,
        discount_total=0.0,
        tax_amount=4250.0,
        total_amount=89250.0,
        paid_amount=50000.0,
        status="Approved",
        payment_status="Partially Paid",
        voucher_no="AR-INV-0001",
        created_by="Submitter (Finance Officer)",
        approved_by="Checker (Finance Manager)",
        notes="Enterprise ERP Architecture & Implementation Phase 1 Milestone"
    )
    db.add(ar_inv1)
    db.flush()
    db.add(models.ARInvoiceLine(
        invoice_id=ar_inv1.id,
        line_no=1,
        description="Dynamics 365 Architecture Consulting & Engineering Phase 1",
        revenue_account_code="4000",
        quantity=1.0,
        unit_price=85000.0,
        discount_amount=0.0,
        tax_code="VAT-STD-5",
        net_amount=85000.0,
        tax_amount=4250.0,
        total_amount=89250.0
    ))
    db.commit()

    # GL Voucher for AR Invoice
    crud.create_journal_voucher_entry(
        db=db,
        voucher_no="AR-INV-0001",
        posting_date=today - datetime.timedelta(days=15),
        source_module="AR-INV",
        document_ref="INV-2026-0001",
        description="Customer Sales Tax Invoice INV-2026-0001 to CUST-001",
        lines=[
            {"account_code": "1100", "account_name": "Accounts Receivable Control", "description": "Customer receivable Apex Capital", "debit": 89250.0, "credit": 0.0},
            {"account_code": "4000", "account_name": "Sales Revenue - Enterprise Solutions", "description": "Enterprise Solutions Consulting Milestone", "debit": 0.0, "credit": 85000.0},
            {"account_code": "2020", "account_name": "Output VAT / Tax Payable", "description": "5% Indirect Tax Output", "debit": 0.0, "credit": 4250.0}
        ],
        created_by="Submitter (Finance Officer)",
        approved_by="Checker (Finance Manager)",
        status="Approved"
    )

    # G. Approved AR Bank Receipt
    ar_rcpt1 = models.ARReceipt(
        receipt_number="REC-2026-0001",
        receipt_date=today - datetime.timedelta(days=8),
        customer_code="CUST-001",
        bank_account_code="1010",
        receipt_ref="WIRE-APEX-44910",
        receipt_method="Bank Wire",
        total_amount=50000.0,
        status="Approved",
        voucher_no="AR-RCPT-0001",
        created_by="Submitter (Finance Officer)",
        approved_by="Checker (Finance Manager)",
        notes="First tranche remittance against Phase 1 invoice"
    )
    db.add(ar_rcpt1)
    db.flush()
    db.add(models.ARReceiptLine(
        receipt_id=ar_rcpt1.id,
        ar_invoice_id=ar_inv1.id,
        invoice_number=ar_inv1.invoice_number,
        amount_received=50000.0
    ))
    db.commit()

    # GL Voucher for AR Receipt
    crud.create_journal_voucher_entry(
        db=db,
        voucher_no="AR-RCPT-0001",
        posting_date=today - datetime.timedelta(days=8),
        source_module="AR-RCPT",
        document_ref="REC-2026-0001",
        description="Collection from CUST-001 on INV-2026-0001",
        lines=[
            {"account_code": "1010", "account_name": "Cash at Bank - Primary Operating", "description": "Wire transfer received from Apex Capital", "debit": 50000.0, "credit": 0.0},
            {"account_code": "1100", "account_name": "Accounts Receivable Control", "description": "Partial settlement of INV-2026-0001", "debit": 0.0, "credit": 50000.0}
        ],
        created_by="Submitter (Finance Officer)",
        approved_by="Checker (Finance Manager)",
        status="Approved"
    )

    # 9. Sample Pending Approval Items (To populate the Approval Center immediately!)
    # A. Pending PR
    pr2 = models.PurchaseRequisition(
        pr_number="PR-2026-0002",
        pr_date=today - datetime.timedelta(days=3),
        department="Sales & Marketing",
        status="Pending Approval",
        total_amount=8500.0,
        budget_override=False,
        created_by="Submitter (Marketing Specialist)",
        notes="Q2 Regional Brand Sponsorship & Tech Expo Booth Space"
    )
    db.add(pr2)
    db.flush()
    db.add(models.PRLine(
        pr_id=pr2.id,
        line_no=1,
        description="Q2 Tech Expo Exhibition Booth Space & Signage",
        account_code="6030",
        quantity=1.0,
        unit_price=8500.0,
        total_amount=8500.0
    ))

    # B. Pending PO
    po2 = models.PurchaseOrder(
        po_number="PO-2026-0002",
        pr_number=None,
        po_date=today - datetime.timedelta(days=2),
        delivery_date=today + datetime.timedelta(days=7),
        vendor_code="VEND-001",
        tax_code="VAT-STD-5",
        subtotal=6500.0,
        tax_amount=325.0,
        total_amount=6825.0,
        status="Pending Approval",
        created_by="Submitter (Procurement Officer)",
        notes="Office Ergonomic Workstations and Server Racks"
    )
    db.add(po2)
    db.flush()
    db.add(models.POLine(
        po_id=po2.id,
        line_no=1,
        description="Custom Server Rack Cabinets and UPS",
        account_code="6060",
        quantity=2.0,
        unit_price=3250.0,
        received_qty=0.0,
        invoiced_qty=0.0,
        line_subtotal=6500.0,
        tax_amount=325.0,
        line_total=6825.0
    ))

    # C. Pending AP Direct Expense Invoice (Mode B)
    ap_inv2 = models.APInvoice(
        invoice_number="AP-INV-2026-0002",
        invoice_mode="Mode_B_Direct",
        vendor_code="VEND-003",
        vendor_invoice_ref="INV-PRIME-2026-104",
        invoice_date=today - datetime.timedelta(days=1),
        due_date=today + datetime.timedelta(days=29),
        expense_account_code="6040",
        tax_code="VAT-STD-5",
        subtotal=7500.0,
        tax_amount=375.0,
        total_amount=7875.0,
        paid_amount=0.0,
        status="Pending Approval",
        payment_status="Unpaid",
        created_by="Submitter (Finance Officer)",
        notes="Corporate legal compliance and contractual review retainer"
    )
    db.add(ap_inv2)

    # D. Pending AR Sales Invoice
    ar_inv2 = models.ARInvoice(
        invoice_number="INV-2026-0002",
        customer_code="CUST-002",
        invoice_date=today - datetime.timedelta(days=1),
        due_date=today + datetime.timedelta(days=30),
        subtotal=42000.0,
        discount_total=0.0,
        tax_amount=2100.0,
        total_amount=44100.0,
        paid_amount=0.0,
        status="Pending Approval",
        payment_status="Unpaid",
        created_by="Submitter (Finance Officer)",
        notes="Omnichannel ERP Integration and Retail POS Connector"
    )
    db.add(ar_inv2)
    db.flush()
    db.add(models.ARInvoiceLine(
        invoice_id=ar_inv2.id,
        line_no=1,
        description="Retail POS Gateway Integration Services",
        revenue_account_code="4010",
        quantity=1.0,
        unit_price=42000.0,
        discount_amount=0.0,
        tax_code="VAT-STD-5",
        net_amount=42000.0,
        tax_amount=2100.0,
        total_amount=44100.0
    ))

    # E. Pending Manual Journal Voucher
    jv_pending = models.JournalVoucher(
        voucher_no="JV-2026-0001",
        posting_date=today,
        source_module="GL-JV",
        document_ref="ADJ-DEP-01",
        description="Monthly Depreciation Expense Allocation on Plant & Equipment",
        total_debit=2500.0,
        total_credit=2500.0,
        status="Pending Approval",
        created_by="Submitter (Senior Accountant)"
    )
    db.add(jv_pending)
    db.flush()
    db.add(models.VoucherLine(
        voucher_id=jv_pending.id,
        line_no=1,
        account_code="6010",
        account_name="Rent & Facilities Operations",
        description="Depreciation charge on fixtures",
        debit=2500.0,
        credit=0.0
    ))
    db.add(models.VoucherLine(
        voucher_id=jv_pending.id,
        line_no=2,
        account_code="1500",
        account_name="Property, Plant & Equipment",
        description="Accumulated depreciation credit",
        debit=0.0,
        credit=2500.0
    ))

    db.commit()
    seed_inventory_catalog(db, today)


def seed_inventory_catalog(db: Session, today=None):
    if today is None:
        today = datetime.date.today()
    
    items = [
        {"item_code": "RICE-BAS-5KG", "name": "Royal Basmati Rice 5kg", "category": "Food & Grains", "barcode": "6291001001", "unit": "Bag", "cost_price": 18.00, "selling_price": 26.50, "stock_quantity": 250.0, "reorder_level": 30.0},
        {"item_code": "OIL-SUN-1.8L", "name": "Pure Sunflower Cooking Oil 1.8L", "category": "Oils & Ghee", "barcode": "6291001002", "unit": "Bottle", "cost_price": 12.00, "selling_price": 17.50, "stock_quantity": 180.0, "reorder_level": 25.0},
        {"item_code": "MILK-FRESH-1L", "name": "Farm Fresh Full Cream Milk 1L", "category": "Dairy & Chilled", "barcode": "6291001003", "unit": "Carton", "cost_price": 3.20, "selling_price": 5.00, "stock_quantity": 320.0, "reorder_level": 50.0},
        {"item_code": "TEA-CEY-100", "name": "Ceylon Premium Tea Bags 100s", "category": "Beverages", "barcode": "6291001004", "unit": "Box", "cost_price": 8.50, "selling_price": 13.00, "stock_quantity": 140.0, "reorder_level": 20.0},
        {"item_code": "DET-ACT-3KG", "name": "Active Clean Laundry Detergent 3kg", "category": "Household Care", "barcode": "6291001005", "unit": "Pack", "cost_price": 15.00, "selling_price": 22.00, "stock_quantity": 110.0, "reorder_level": 15.0},
        {"item_code": "WAT-MIN-24PK", "name": "Pure Mineral Drinking Water 24x500ml", "category": "Beverages", "barcode": "6291001006", "unit": "Case", "cost_price": 6.50, "selling_price": 10.50, "stock_quantity": 200.0, "reorder_level": 30.0},
        {"item_code": "FLR-WHT-10KG", "name": "Golden Wheat Flour 10kg", "category": "Food & Grains", "barcode": "6291001007", "unit": "Bag", "cost_price": 16.00, "selling_price": 24.00, "stock_quantity": 90.0, "reorder_level": 15.0},
        {"item_code": "HNY-BLS-500G", "name": "Pure Natural Blossom Honey 500g", "category": "Breakfast & Spreads", "barcode": "6291001008", "unit": "Jar", "cost_price": 14.50, "selling_price": 21.00, "stock_quantity": 75.0, "reorder_level": 10.0}
    ]

    for it in items:
        existing = db.query(models.InventoryItem).filter(models.InventoryItem.item_code == it["item_code"]).first()
        if not existing:
            item_obj = models.InventoryItem(**it)
            db.add(item_obj)
            db.add(models.StockMovement(
                movement_date=today,
                item_code=it["item_code"],
                item_name=it["name"],
                movement_type="OPENING_STOCK",
                reference_doc="INIT-STOCK",
                quantity=it["stock_quantity"],
                unit_cost=it["cost_price"],
                total_cost=round(it["stock_quantity"] * it["cost_price"], 2),
                notes="Initial store & warehouse inventory stock count"
            ))

    # Also add retail & wholesale customers if not existing
    supermarket_customers = [
        {"customer_code": "CUST-RET-01", "name": "Demo Business 37", "trn": "TRN-RETAIL-000", "email": "demo@example.com", "phone": "DEMO-PHONE", "billing_address": "Fictional Demo Address", "credit_limit": 5000.0},
        {"customer_code": "CUST-WHO-01", "name": "Demo Business 39", "trn": "DEMO-TRN", "email": "demo@example.com", "phone": "DEMO-PHONE", "billing_address": "Fictional Demo Address", "credit_limit": 50000.0},
        {"customer_code": "CUST-WHO-02", "name": "Demo Business 41", "trn": "DEMO-TRN", "email": "demo@example.com", "phone": "DEMO-PHONE", "billing_address": "Fictional Demo Address", "credit_limit": 30000.0}
    ]
    for c_data in supermarket_customers:
        if not db.query(models.Customer).filter(models.Customer.customer_code == c_data["customer_code"]).first():
            db.add(models.Customer(**c_data))

    # Also add supermarket FMCG vendors if not existing
    supermarket_vendors = [
        {"vendor_code": "VEND-FMCG-01", "name": "Demo Business 43", "trn": "DEMO-TRN", "payment_terms": "Net 30", "bank_details": "DEMO BANK DETAILS - NOT A REAL ACCOUNT", "email": "demo@example.com", "phone": "DEMO-PHONE"},
        {"vendor_code": "VEND-FMCG-02", "name": "Demo Business 45", "trn": "DEMO-TRN", "payment_terms": "Net 15", "bank_details": "DEMO BANK DETAILS - NOT A REAL ACCOUNT", "email": "demo@example.com", "phone": "DEMO-PHONE"},
        {"vendor_code": "VEND-FMCG-03", "name": "Demo Business 47", "trn": "DEMO-TRN", "payment_terms": "Net 30", "bank_details": "DEMO BANK DETAILS - NOT A REAL ACCOUNT", "email": "demo@example.com", "phone": "DEMO-PHONE"}
    ]
    for v_data in supermarket_vendors:
        if not db.query(models.Vendor).filter(models.Vendor.vendor_code == v_data["vendor_code"]).first():
            db.add(models.Vendor(**v_data))

    db.commit()
