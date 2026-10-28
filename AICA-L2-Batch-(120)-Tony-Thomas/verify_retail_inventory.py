import sys
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_retail_inventory():
    print("===========================================================================")
    print("  ALL IN ONE ACCOUNTANT - RETAIL & INVENTORY VERIFICATION SUITE")
    print("===========================================================================")

    # 1. Company Settings Verification
    print("\n[Step 1] Verifying Company Profile & Settings Setup...")
    res = client.get("/api/settings")
    assert res.status_code == 200, f"Failed GET /api/settings: {res.text}"
    comp = res.json()
    print(f"  -> Initial Company: {comp['company_name']}, TRN: {comp['company_trn']}")

    update_payload = {
        "company_name": "Demo Business 13",
        "company_trn": "DEMO-TRN",
        "company_address": "Fictional Demo Address",
        "phone": "DEMO-PHONE",
        "email": "demo@example.com",
        "currency": "USD",
        "currency_symbol": "$"
    }
    res = client.post("/api/settings", json=update_payload)
    assert res.status_code == 200, f"Failed POST /api/settings: {res.text}"
    saved_comp = res.json()
    assert saved_comp["company_name"] == "Demo Business 13"
    print(f"  -> Successfully updated company profile: {saved_comp['company_name']}")

    import time
    ts = int(time.time())
    cust_code = f"CUST-RET-{ts}"
    vend_code = f"VEND-FMCG-{ts}"
    item_code = f"OATS-{ts}"

    # 2. Add New Customer & Vendor
    print("\n[Step 2] Verifying New Customer & Vendor Creation...")
    cust_payload = {
        "customer_code": cust_code,
        "name": "Demo Business 16",
        "trn": "DEMO-TRN",
        "credit_limit": 45000.0,
        "billing_address": "Fictional Demo Address",
        "email": "demo@example.com",
        "phone": "DEMO-PHONE"
    }
    res = client.post("/api/ar/customers", json=cust_payload)
    assert res.status_code == 200, f"Failed Customer create: {res.text}"
    print(f"  -> Created Customer: {res.json()['name']} ({res.json()['customer_code']})")

    vend_payload = {
        "vendor_code": vend_code,
        "name": "Demo Business 18",
        "trn": "DEMO-TRN",
        "payment_terms": "Net 30",
        "bank_details": "DEMO BANK DETAILS - NOT A REAL ACCOUNT",
        "email": "demo@example.com",
        "phone": "DEMO-PHONE"
    }
    res = client.post("/api/ap/vendors", json=vend_payload)
    assert res.status_code == 200, f"Failed Vendor create: {res.text}"
    print(f"  -> Created Vendor: {res.json()['name']} ({res.json()['vendor_code']})")

    # 3. Inventory Catalog & Adding New Product
    print("\n[Step 3] Verifying Inventory Items & Adding New SKU...")
    res = client.get("/api/inventory/items")
    assert res.status_code == 200
    items = res.json()
    print(f"  -> Current SKUs in Store: {len(items)}")

    new_item_payload = {
        "item_code": item_code,
        "name": "Whole Rolled Oats 1kg",
        "category": "Breakfast & Spreads",
        "barcode": f"6291{ts}",
        "unit": "Pack",
        "cost_price": 7.50,
        "selling_price": 12.00,
        "stock_quantity": 100.0,
        "reorder_level": 20.0
    }
    res = client.post("/api/inventory/items", json=new_item_payload)
    assert res.status_code == 200, f"Failed Item create: {res.text}"
    created_item = res.json()
    print(f"  -> Created SKU: {created_item['name']} ({created_item['item_code']}), Stock: {created_item['stock_quantity']}")

    # 4. Stock Adjustment (Damage / Spoilage)
    print("\n[Step 4] Verifying Stock Adjustment & Auto GL Posting...")
    adjust_payload = {
        "item_code": item_code,
        "adjustment_type": "Damage / Spoilage",
        "quantity": -5.0,
        "reason": "Damaged pack during warehouse transit"
    }
    res = client.post("/api/inventory/adjust", json=adjust_payload)
    assert res.status_code == 200, f"Failed adjust: {res.text}"
    adj_res = res.json()
    print(f"  -> Stock adjusted by -5. New stock: {adj_res['item']['stock_quantity']} (GL Voucher: {adj_res['voucher_no']})")
    assert adj_res["item"]["stock_quantity"] == 95.0

    # 5. Sales Invoice with Auto GL, Auto COGS, and Inventory Stock Deduction
    print("\n[Step 5] Verifying 1-Person Sales Invoice Submission (Auto-Post GL & Inventory)...")
    inv_payload = {
        "customer_code": cust_code,
        "invoice_date": "2026-10-18",
        "due_date": "2026-11-18",
        "notes": "Wholesale supply of rolled oats",
        "lines": [
            {
                "item_code": item_code,
                "description": "Whole Rolled Oats 1kg",
                "revenue_account_code": "4000",
                "quantity": 20.0,
                "unit_price": 12.00,
                "discount_amount": 0.0,
                "tax_code": "VAT-STD-5"
            }
        ]
    }
    res = client.post("/api/ar/invoices?status=Approved&created_by=Owner / Accountant", json=inv_payload)
    assert res.status_code == 200, f"Failed Sales Invoice: {res.text}"
    inv_res = res.json()
    assert inv_res["status"] == "Approved", f"Expected Approved, got {inv_res['status']}"
    print(f"  -> Invoice {inv_res['invoice_number']} posted immediately as Approved! (GL Voucher: {inv_res['voucher_no']})")

    # Check inventory deduction: 95.0 - 20.0 = 75.0
    res = client.get("/api/inventory/items")
    oats_item = next(i for i in res.json() if i["item_code"] == item_code)
    assert oats_item["stock_quantity"] == 75.0, f"Expected 75.0, got {oats_item['stock_quantity']}"
    print(f"  -> Verified stock deduction: 95.0 - 20.0 = {oats_item['stock_quantity']} packs remaining")

    # Check Stock Movements
    res = client.get("/api/inventory/movements")
    movs = res.json()
    assert any(m["reference_doc"] == inv_res["invoice_number"] and m["movement_type"] == "SALES_DISPATCH" for m in movs)
    print(f"  -> Verified StockMovement logged for SALES_DISPATCH with Ref {inv_res['invoice_number']}")

    # 6. Verify Summary & KPIs
    print("\n[Step 6] Verifying Store Inventory Valuation Summary & KPIs...")
    res = client.get("/api/inventory/summary")
    assert res.status_code == 200
    sum_data = res.json()
    print(f"  -> Total Store SKUs: {sum_data['total_skus']}")
    print(f"  -> Total Inventory Valuation: ${sum_data['total_inventory_valuation']:,.2f}")

    res = client.get("/api/reports/dashboard-kpis")
    kpis = res.json()
    print(f"  -> Dashboard KPI Stock Valuation: ${kpis['total_inventory_valuation']:,.2f}")
    assert kpis["total_inventory_valuation"] == sum_data["total_inventory_valuation"]

    print("\n===========================================================================")
    print("  ALL RETAIL & INVENTORY VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("===========================================================================")

if __name__ == "__main__":
    test_retail_inventory()
