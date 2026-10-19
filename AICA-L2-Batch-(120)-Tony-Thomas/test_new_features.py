import sys
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_full_features():
    print("==================================================")
    print("RUNNING AUTOMATED VERIFICATION OF NEW FEATURES")
    print("==================================================")

    # 1. Check Companies and State
    res = client.get("/api/companies")
    assert res.status_code == 200, f"Failed to get companies: {res.text}"
    companies = res.json()
    print(f"PASS: Loaded {len(companies)} company profiles.")

    # 2. Test Vendor & PO / GRN workflow for 3-Way Match
    # Check vendors
    v_res = client.get("/api/ap/vendors")
    assert v_res.status_code == 200
    vendors = v_res.json()
    if not vendors:
        # Create a vendor
        ven_create = client.post("/api/ap/vendors", json={
            "vendor_code": "VEN-TEST-99",
            "name": "Demo Business 11",
            "trn": "TRN-9988776655",
            "payment_terms": "Net 30"
        })
        assert ven_create.status_code == 200
        vendor_code = "VEN-TEST-99"
    else:
        vendor_code = vendors[0]["vendor_code"]

    # Create PO
    po_create = client.post("/api/p2p/pos?status=Approved&created_by=Owner", json={
        "po_date": "2026-10-19",
        "delivery_date": "2026-10-25",
        "vendor_code": vendor_code,
        "payment_terms": "Net 30",
        "tax_code": "STANDARD_5",
        "lines": [
            {
                "description": "Bulk Basmati Rice Bags 10kg",
                "account_code": "1200",
                "quantity": 50,
                "unit_price": 20.0
            }
        ]
    })
    assert po_create.status_code == 200, f"PO Creation failed: {po_create.text}"
    po_data = po_create.json()
    po_number = po_data["po_number"]
    po_line_id = po_data["lines"][0]["id"]
    print(f"PASS: Created PO {po_number} with line total: 50 * $20 = $1,000")

    # Create GRN receiving 40 units ($800 value)
    grn_create = client.post("/api/p2p/grns?status=Approved&created_by=Owner", json={
        "grn_date": "2026-10-19",
        "po_number": po_number,
        "delivery_note_ref": "DN-TEST-44",
        "lines": [
            {
                "po_line_id": po_line_id,
                "item_code": "TEST-RICE",
                "account_code": "1200",
                "description": "Bulk Basmati Rice Bags 10kg",
                "received_qty": 40.0,
                "unit_price": 20.0
            }
        ]
    })
    assert grn_create.status_code == 200, f"GRN Creation failed: {grn_create.text}"
    grn_data = grn_create.json()
    grn_number = grn_data["grn_number"]
    print(f"PASS: Created & Approved GRN {grn_number} with received value: 40 * $20 = $800")

    # TEST ITEM 1: 3-WAY MATCHING CEILING ENFORCEMENT
    # Try creating an AP invoice with subtotal $950 (exceeding GRN value of $800) -> MUST FAIL (400)
    inv_over = client.post("/api/ap/invoices?status=Approved&created_by=Owner", json={
        "invoice_mode": "Mode_A_PO",
        "vendor_code": vendor_code,
        "vendor_invoice_ref": "INV-OVER-LIMIT",
        "po_number": po_number,
        "grn_number": grn_number,
        "invoice_date": "2026-10-19",
        "due_date": "2026-11-19",
        "tax_code": "STANDARD_5",
        "subtotal": 950.0,
        "tax_amount": 47.50,
        "total_amount": 997.50
    })
    assert inv_over.status_code == 400, f"Expected 400 Bad Request on over-billed GRN, got {inv_over.status_code}: {inv_over.text}"
    print(f"PASS: 3-Way Match correctly BLOCKED over-billing ($950 > $800 max): {inv_over.json()['detail']}")

    # Now create valid invoice <= $800 ($800 subtotal) -> MUST SUCCEED (200)
    inv_valid = client.post("/api/ap/invoices?status=Approved&created_by=Owner", json={
        "invoice_mode": "Mode_A_PO",
        "vendor_code": vendor_code,
        "vendor_invoice_ref": "INV-MATCHED-800",
        "po_number": po_number,
        "grn_number": grn_number,
        "invoice_date": "2026-10-19",
        "due_date": "2026-11-19",
        "tax_code": "STANDARD_5",
        "subtotal": 800.0,
        "tax_amount": 40.0,
        "total_amount": 840.0
    })
    assert inv_valid.status_code == 200, f"Valid invoice failed: {inv_valid.text}"
    valid_inv_data = inv_valid.json()
    inv_number = valid_inv_data["invoice_number"]
    print(f"PASS: 3-Way Match PASSED for invoice within GRN limit: {inv_number}, Total Payable: $840")

    # TEST ITEM 2: AP PURCHASE CREDIT NOTE
    # Issue a $100 credit note (+ $5 VAT = $105) against the invoice
    ap_cn_res = client.post("/api/ap/credit-notes", json={
        "vendor_code": vendor_code,
        "original_invoice_ref": inv_number,
        "credit_note_date": "2026-10-19",
        "reason": "Damaged goods returned to vendor",
        "subtotal": 100.0,
        "tax_code": "STANDARD_5",
        "tax_amount": 5.0,
        "total_credit": 105.0
    })
    assert ap_cn_res.status_code == 200, f"AP Credit Note creation failed: {ap_cn_res.text}"
    ap_cn_data = ap_cn_res.json()
    cn_number = ap_cn_data["credit_note_number"]
    cn_voucher = ap_cn_data["voucher_no"]
    print(f"PASS: Purchase Credit Note created: {cn_number}, GL Voucher: {cn_voucher}, Total Credit: $105")

    # Verify original invoice remaining balance is reduced ($840 - $105 = $735)
    inv_check = client.get(f"/api/ap/invoices")
    inv_obj = next(i for i in inv_check.json() if i["invoice_number"] == inv_number)
    assert abs(inv_obj["remaining_balance"] - 735.0) < 0.01, f"Remaining balance expected 735.0, got {inv_obj['remaining_balance']}"
    print(f"PASS: Original invoice remaining balance successfully reduced to ${inv_obj['remaining_balance']}")

    # TEST ITEM 3: VENDOR CASH DISBURSEMENT (PETTY CASH ACCOUNT 1010)
    # Pay $200 via "Cash"
    ap_pmt_res = client.post("/api/ap/payments?status=Approved&created_by=Owner", json={
        "payment_date": "2026-10-19",
        "vendor_code": vendor_code,
        "bank_account_code": "1010",
        "payment_ref": "CASH-PMT-777",
        "payment_method": "Cash",
        "lines": [
            {
                "ap_invoice_id": inv_obj["id"],
                "invoice_number": inv_number,
                "amount_paid": 200.0
            }
        ]
    })
    assert ap_pmt_res.status_code == 200, f"AP Payment failed: {ap_pmt_res.text}"
    pmt_data = ap_pmt_res.json()
    pmt_voucher = pmt_data["voucher_no"]
    print(f"PASS: AP Cash Payment recorded: {pmt_data['payment_number']}, Voucher: {pmt_voucher}")

    # Verify voucher credited account 1010
    vouch_res = client.get(f"/api/gl/vouchers/{pmt_voucher}")
    assert vouch_res.status_code == 200
    vouch_data = vouch_res.json()
    credit_line = next(l for l in vouch_data["lines"] if l["credit"] > 0)
    assert credit_line["account_code"] == "1010", f"Expected account 1010 credited, got {credit_line['account_code']}"
    print(f"PASS: Verified Cash payment directly credited Petty Cash Account {credit_line['account_code']} ({credit_line['account_name']})")

    # TEST ITEM 4: CUSTOMER AR SALES INVOICE & CREDIT NOTE & CASH COLLECTION
    # Check or create customer
    c_res = client.get("/api/ar/customers")
    assert c_res.status_code == 200
    customers = c_res.json()
    if not customers:
        cust_create = client.post("/api/ar/customers", json={
            "customer_code": "CUST-TEST-01",
            "name": "Demo Business 12",
            "trn": "TRN-1122334455",
            "credit_limit": 50000.0
        })
        assert cust_create.status_code == 200
        customer_code = "CUST-TEST-01"
    else:
        customer_code = customers[0]["customer_code"]

    # Create Sales Invoice $500 + $25 VAT = $525
    ar_inv_res = client.post("/api/ar/invoices?status=Approved&created_by=Owner", json={
        "customer_code": customer_code,
        "invoice_date": "2026-10-19",
        "due_date": "2026-11-19",
        "lines": [
            {
                "description": "Premium Sunflower Oil 5L Cans",
                "revenue_account_code": "4000",
                "quantity": 10.0,
                "unit_price": 50.0,
                "discount_amount": 0.0,
                "tax_code": "STANDARD_5"
            }
        ]
    })
    assert ar_inv_res.status_code == 200, f"AR Invoice failed: {ar_inv_res.text}"
    ar_inv_data = ar_inv_res.json()
    ar_inv_num = ar_inv_data["invoice_number"]
    print(f"PASS: Created & Approved Sales Invoice {ar_inv_num}, Total: $525")

    # Issue Sales Credit Note $50 (+ $2.50 VAT = $52.50)
    ar_cn_res = client.post("/api/ar/credit-notes", json={
        "customer_code": customer_code,
        "original_invoice_number": ar_inv_num,
        "credit_note_date": "2026-10-19",
        "reason": "Price correction / Volume rebate",
        "subtotal": 50.0,
        "tax_code": "STANDARD_5",
        "tax_amount": 2.50,
        "total_credit": 52.50
    })
    assert ar_cn_res.status_code == 200, f"AR Credit Note failed: {ar_cn_res.text}"
    ar_cn_data = ar_cn_res.json()
    print(f"PASS: Sales Credit Note created: {ar_cn_data['credit_note_number']}, Voucher: {ar_cn_data['voucher_no']}, Total: $52.50")

    # Verify invoice remaining balance reduced ($525 - $52.50 = $472.50)
    ar_inv_chk = client.get("/api/ar/invoices")
    ar_inv_obj = next(i for i in ar_inv_chk.json() if i["invoice_number"] == ar_inv_num)
    assert abs(ar_inv_obj["remaining_balance"] - 472.50) < 0.01
    print(f"PASS: Verified customer invoice open balance reduced to ${ar_inv_obj['remaining_balance']}")

    # TEST ITEM 5: CUSTOMER CASH COLLECTION (PETTY CASH ACCOUNT 1010)
    # Collect $200 in Cash
    rcpt_res = client.post("/api/ar/receipts?status=Approved&created_by=Owner", json={
        "receipt_date": "2026-10-19",
        "customer_code": customer_code,
        "bank_account_code": "1010",
        "receipt_ref": "CASH-RCPT-888",
        "receipt_method": "Cash",
        "lines": [
            {
                "ar_invoice_id": ar_inv_obj["id"],
                "invoice_number": ar_inv_num,
                "amount_received": 200.0
            }
        ]
    })
    assert rcpt_res.status_code == 200, f"AR Receipt failed: {rcpt_res.text}"
    rcpt_data = rcpt_res.json()
    rcpt_voucher = rcpt_data["voucher_no"]
    print(f"PASS: Customer Cash Receipt recorded: {rcpt_data['receipt_number']}, Voucher: {rcpt_voucher}")

    # Verify voucher debited account 1010
    vouch_rcpt = client.get(f"/api/gl/vouchers/{rcpt_voucher}")
    assert vouch_rcpt.status_code == 200
    debit_line = next(l for l in vouch_rcpt.json()["lines"] if l["debit"] > 0)
    assert debit_line["account_code"] == "1010", f"Expected account 1010 debited, got {debit_line['account_code']}"
    print(f"PASS: Verified Cash receipt directly debited Petty Cash Account {debit_line['account_code']} ({debit_line['account_name']})")

    # TEST ITEM 6: VERIFY GENERAL LEDGER BALANCE EQUALITY
    tb_res = client.get("/api/reports/trial-balance")
    assert tb_res.status_code == 200
    tb = tb_res.json()
    print(f"PASS: Trial Balance Total Closing Dr: ${tb['total_closing_debit']:,.2f} | Total Closing Cr: ${tb['total_closing_credit']:,.2f}")
    assert tb["is_balanced"], f"Trial balance out of balance! Dr: {tb['total_closing_debit']}, Cr: {tb['total_closing_credit']}"

    # TEST ITEM 7: DASHBOARD KPIS AND REPORT ENDPOINTS
    kpis_res = client.get("/api/reports/dashboard-kpis")
    assert kpis_res.status_code == 200
    charts_res = client.get("/api/reports/charts-data")
    assert charts_res.status_code == 200
    print("PASS: Dashboard KPIs and Charts Data endpoints returned HTTP 200 successfully.")

    print("\n>>> ALL TEST CASES PASSED WITH 100% SUCCESS! <<<")

if __name__ == "__main__":
    test_full_features()
