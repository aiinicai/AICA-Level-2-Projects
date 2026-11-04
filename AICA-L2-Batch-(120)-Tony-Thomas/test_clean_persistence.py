import time
from fastapi.testclient import TestClient
from main import app
from app.database import SessionLocal
from app import seed_data, models

client = TestClient(app)

def test_clean_slate_and_migration():
    print("===========================================================================")
    print("  ALL IN ONE ACCOUNTANT - CLEAN SLATE & DATA PERSISTENCE VERIFICATION")
    print("===========================================================================")

    # 1. Reset to Clean Slate
    print("\n[Step 1] Triggering Clean Production Slate Reset...")
    from app import company_manager
    comps = company_manager.load_companies()
    active_comp = [c for c in comps if c.get("is_active")][0]
    pin = active_comp.get("pin", "1234")
    db_file = active_comp.get("db_file")

    # Verify wrong PIN is rejected
    fail_res = client.post("/api/system/reset-clean", json={"pin": "0000"})
    assert fail_res.status_code == 401, f"Expected 401, got {fail_res.status_code}"
    print("  -> Verified reset correctly rejected with wrong PIN.")

    res = client.post("/api/system/reset-clean", json={"pin": pin})
    assert res.status_code == 200, f"Reset clean failed: {res.text}"
    print(f"  -> Reset Response: {res.json()['message']}")

    # Check zero transactions
    from app import database
    sm = database.get_sessionmaker_for_path(db_file) if db_file else SessionLocal
    db = sm()
    try:
        voucher_count = db.query(models.JournalVoucher).count()
        inv_count = db.query(models.ARInvoice).count()
        bill_count = db.query(models.APInvoice).count()
        cust_count = db.query(models.Customer).count()
        vend_count = db.query(models.Vendor).count()
        accounts = db.query(models.Account).all()
        tot_op_dr = sum(a.opening_debit for a in accounts)
        tot_op_cr = sum(a.opening_credit for a in accounts)

        print(f"  -> Vouchers: {voucher_count} (Expected: 0)")
        print(f"  -> Customer Invoices: {inv_count} (Expected: 0)")
        print(f"  -> Vendor Bills: {bill_count} (Expected: 0)")
        print(f"  -> Customers: {cust_count} (Expected: 0)")
        print(f"  -> Vendors: {vend_count} (Expected: 0)")
        print(f"  -> Opening Debits: ${tot_op_dr:.2f}, Opening Credits: ${tot_op_cr:.2f}")

        assert voucher_count == 0
        assert inv_count == 0
        assert bill_count == 0
        assert cust_count == 0
        assert vend_count == 0
        assert tot_op_dr == 0.0
        assert tot_op_cr == 0.0
        assert len(accounts) == 24
        print("  -> PASS: Clean slate verified with exactly 0 transactions and 0 opening balances.")
    finally:
        db.close()

    # 2. Company Profile Setup
    print("\n[Step 2] Testing Company Profile Setup & Customization...")
    company_payload = {
        "company_name": "Demo Retail Company",
        "company_trn": "DEMO-TRN",
        "company_address": "Fictional Demo Address",
        "phone": "DEMO-PHONE",
        "email": "demo@example.com",
        "currency": "AED",
        "currency_symbol": "AED"
    }
    res = client.post("/api/settings", json=company_payload)
    assert res.status_code == 200
    saved_comp = res.json()
    assert saved_comp["company_name"] == "Demo Retail Company"
    print(f"  -> Successfully configured company: {saved_comp['company_name']}")

    # 3. Add Customers & Vendors (Data Event Entry)
    print("\n[Step 3] Adding Customer and Vendor Records...")
    cust_res = client.post("/api/ar/customers", json={
        "customer_code": "CUST-001",
        "name": "Demo Business 6",
        "trn": "DEMO-TRN",
        "email": "demo@example.com",
        "phone": "DEMO-PHONE",
        "billing_address": "Fictional Demo Address",
        "credit_limit": 50000.0
    })
    assert cust_res.status_code == 200
    print(f"  -> Created Customer: {cust_res.json()['name']} ({cust_res.json()['customer_code']})")

    vend_res = client.post("/api/ap/vendors", json={
        "vendor_code": "VEND-001",
        "name": "Demo Business 8",
        "trn": "DEMO-TRN",
        "payment_terms": "Net 30",
        "bank_details": "DEMO BANK DETAILS - NOT A REAL ACCOUNT",
        "email": "demo@example.com",
        "phone": "DEMO-PHONE"
    })
    assert vend_res.status_code == 200
    print(f"  -> Created Vendor: {vend_res.json()['name']} ({vend_res.json()['vendor_code']})")

    # 4. Opening Trial Balance Migration Entry
    print("\n[Step 4] Entering Opening Trial Balance (Data Migration)...")
    # Say the business has $120,000 in Bank, $30,000 Inventory, balanced by $100,000 Capital and $50,000 Retained Earnings
    migration_rows = [
        {"account_code": "1010", "account_name": "Cash at Bank - Primary Operating", "account_type": "Asset", "sub_category": "Bank", "is_control_account": False, "opening_debit": 120000.0, "opening_credit": 0.0},
        {"account_code": "1200", "account_name": "Inventory / Merchandise Store Stock", "account_type": "Asset", "sub_category": "Inventory/GRN", "is_control_account": False, "opening_debit": 30000.0, "opening_credit": 0.0},
        {"account_code": "3000", "account_name": "Share Capital", "account_type": "Equity", "sub_category": "Share Capital", "is_control_account": False, "opening_debit": 0.0, "opening_credit": 100000.0},
        {"account_code": "3010", "account_name": "Retained Earnings", "account_type": "Equity", "sub_category": "Retained Earnings", "is_control_account": False, "opening_debit": 0.0, "opening_credit": 50000.0}
    ]
    res = client.post("/api/opening-tb/save", json=migration_rows)
    assert res.status_code == 200, f"Opening TB save failed: {res.text}"
    print(f"  -> Opening TB Migration Result: {res.json()['message']}")

    # Verify OB-0001 voucher exists and is balanced
    res = client.get("/api/gl/vouchers/OB-0001")
    assert res.status_code == 200
    ob_v = res.json()
    assert ob_v["total_debit"] == 150000.0
    assert ob_v["total_credit"] == 150000.0
    print(f"  -> Verified OB-0001 Voucher in General Ledger: Total ${ob_v['total_debit']:,.2f} balanced.")

    # 5. Create a New Year Current Transaction (Sales Invoice)
    print("\n[Step 5] Entering Current Year Transaction against Customer...")
    inv_payload = {
        "customer_code": "CUST-001",
        "invoice_date": "2026-10-18",
        "due_date": "2026-11-18",
        "lines": [
            {
                "description": "Wholesale Consumer Goods Supply",
                "revenue_account_code": "4000",
                "quantity": 10.0,
                "unit_price": 500.0,
                "discount_amount": 0.0,
                "tax_code": "VAT-STD-5"
            }
        ]
    }
    res = client.post("/api/ar/invoices?status=Approved&created_by=Owner / Accountant", json=inv_payload)
    assert res.status_code == 200
    inv = res.json()
    print(f"  -> Created Invoice {inv['invoice_number']} for ${inv['total_amount']:,.2f}")

    # Check Customer Statement
    print("\n[Step 6] Testing Customer Statement & History Endpoint...")
    res = client.get("/api/ar/customers/CUST-001/statement")
    assert res.status_code == 200
    stmt = res.json()
    assert stmt["customer"]["name"] == "Demo Business 6"
    assert stmt["total_invoiced"] == 5250.0
    assert stmt["outstanding_balance"] == 5250.0
    assert len(stmt["invoices"]) == 1
    print(f"  -> Customer Statement Verified: Total Invoiced ${stmt['total_invoiced']:,.2f}, Balance ${stmt['outstanding_balance']:,.2f}")

    # 6. Test App Restart / Persistence (Re-running lifespan or init_clean_database without force_reset)
    print("\n[Step 7] Simulating Server Restart & Verifying Data Persistence...")
    db = sm()
    try:
        # Calling init_clean_database(db, force_reset=False) as main.py does on startup
        seed_data.init_clean_database(db, force_reset=False)

        # Check company name wasn't overwritten
        cs = db.query(models.CompanySetting).first()
        assert cs.company_name == "Demo Retail Company"
        print(f"  -> Persisted Company Name: {cs.company_name}")

        # Check customer was preserved
        c = db.query(models.Customer).filter(models.Customer.customer_code == "CUST-001").first()
        assert c is not None
        assert c.name == "Demo Business 6"
        print(f"  -> Persisted Customer: {c.name}")

        # Check vendor was preserved
        v = db.query(models.Vendor).filter(models.Vendor.vendor_code == "VEND-001").first()
        assert v is not None
        assert v.name == "Demo Business 8"
        print(f"  -> Persisted Vendor: {v.name}")

        # Check invoice was preserved
        i = db.query(models.ARInvoice).first()
        assert i is not None
        print(f"  -> Persisted Invoice: {i.invoice_number} (${i.total_amount:,.2f})")

        # Check Opening Balances were preserved
        ob_voucher = db.query(models.JournalVoucher).filter(models.JournalVoucher.voucher_no == "OB-0001").first()
        assert ob_voucher is not None
        assert ob_voucher.total_debit == 150000.0
        print(f"  -> Persisted Opening TB: ${ob_voucher.total_debit:,.2f}")

    finally:
        db.close()

    print("\n===========================================================================")
    print("  ALL CLEAN SLATE, MIGRATION & PERSISTENCE CHECKS PASSED WITH 100% SUCCESS!")
    print("===========================================================================")

if __name__ == "__main__":
    test_clean_slate_and_migration()
