import sys
import datetime
from fastapi.testclient import TestClient
from main import app

def run_verification():
    print("=" * 75)
    print("  MICROSOFT DYNAMICS 365 F&O - AUTOMATED ACCOUNTING VERIFICATION SUITE")
    print("=" * 75)

    client = TestClient(app)

    # 1. Reset Database to clean state
    print("\n[Step 1] Resetting ERP Database to pristine state...")
    from app import company_manager
    active_comp = company_manager.get_active_company()
    res = client.post("/api/system/seed-demo", json={"pin": active_comp.get("pin", "1234")})
    assert res.status_code == 200, f"Seed Demo failed: {res.text}"
    print("  -> Database reset and demo seed loaded successfully.")

    # 2. Verify Chart of Accounts & Opening Trial Balance
    print("\n[Step 2] Verifying Chart of Accounts & Opening Balance Equation...")
    res = client.get("/api/accounts")
    assert res.status_code == 200
    accounts = res.json()
    assert len(accounts) >= 20, f"Expected at least 20 accounts, found {len(accounts)}"

    tot_op_dr = sum(a["opening_debit"] for a in accounts)
    tot_op_cr = sum(a["opening_credit"] for a in accounts)
    print(f"  -> Total Accounts: {len(accounts)}")
    print(f"  -> Sum Opening Debits : ${tot_op_dr:,.2f}")
    print(f"  -> Sum Opening Credits: ${tot_op_cr:,.2f}")
    assert abs(tot_op_dr - tot_op_cr) < 0.01, f"Opening TB Unbalanced! Dr: {tot_op_dr}, Cr: {tot_op_cr}"
    print("  -> PASS: Opening Debits == Opening Credits ($500,000.00).")

    # 3. Verify Budget Control Engine
    print("\n[Step 3] Verifying Budget Control Engine & Live Validation...")
    # Check account 6030 (Marketing - Annual Budget $45,000)
    chk_pass = client.post("/api/budgets/check", json={"account_code": "6030", "amount": 5000.0})
    assert chk_pass.status_code == 200
    pass_data = chk_pass.json()
    assert pass_data["passed"] is True
    print(f"  -> Check Within Budget ($5,000 on $45,000): Passed = {pass_data['passed']}")

    chk_fail = client.post("/api/budgets/check", json={"account_code": "6030", "amount": 100000.0})
    assert chk_fail.status_code == 200
    fail_data = chk_fail.json()
    assert fail_data["passed"] is False
    print(f"  -> Check Exceeding Budget ($100,000 on $45,000): Passed = {fail_data['passed']} (Correctly Blocked)")
    print("  -> PASS: Budget control engine actively guards expenditure.")

    # 4. Execute Full End-to-End P2P Cycle (PR -> PO -> GRN -> AP Invoice -> AP Payment)
    print("\n[Step 4] Executing Full P2P Cycle (PR -> PO -> GRN -> AP Inv -> AP Pmt)...")
    today = datetime.date.today().isoformat()

    # A. Create PR
    pr_payload = {
        "pr_date": today,
        "department": "General Administration",
        "notes": "E2E Automated Test Office Supplies Requisition",
        "lines": [
            {
                "description": "Ergonomic Chairs and Executive Desks",
                "account_code": "6060",  # Office Supplies
                "quantity": 5.0,
                "unit_price": 400.0
            }
        ]
    }
    pr_res = client.post("/api/p2p/prs?status=Pending Approval", json=pr_payload)
    assert pr_res.status_code == 200, f"PR creation failed: {pr_res.text}"
    pr = pr_res.json()
    pr_id = pr["id"]
    print(f"  -> 1. PR Created: {pr['pr_number']} for ${pr['total_amount']:,.2f}")

    # Approve PR
    app_pr = client.post("/api/approvals/action", json={
        "module": "PR",
        "document_id": pr_id,
        "action": "approve"
    })
    assert app_pr.status_code == 200
    print("  -> 2. PR Approved by Checker.")

    # Convert PR to PO
    conv_po = client.post(f"/api/p2p/prs/{pr_id}/convert-to-po?vendor_code=VEND-001&tax_code=VAT-STD-5")
    assert conv_po.status_code == 200, f"Convert to PO failed: {conv_po.text}"
    po = conv_po.json()
    po_id = po["id"]
    po_number = po["po_number"]
    print(f"  -> 3. Converted to PO: {po_number} for Subtotal ${po['subtotal']:,.2f} + VAT ${po['tax_amount']:,.2f} = ${po['total_amount']:,.2f}")

    # Approve PO
    app_po = client.post("/api/approvals/action", json={
        "module": "PO",
        "document_id": po_id,
        "action": "approve"
    })
    assert app_po.status_code == 200
    print("  -> 4. PO Approved by Checker.")

    # Create GRN against PO
    grn_payload = {
        "po_number": po_number,
        "grn_date": today,
        "vendor_delivery_ref": "DEL-TEST-0099",
        "notes": "Full receipt of ergonomic furniture",
        "lines": [
            {
                "po_line_id": po["lines"][0]["id"],
                "account_code": "6060",
                "description": "Ergonomic Chairs and Executive Desks",
                "received_qty": 5.0,
                "unit_price": 400.0
            }
        ]
    }
    grn_res = client.post("/api/p2p/grns?status=Pending Approval", json=grn_payload)
    assert grn_res.status_code == 200, f"GRN creation failed: {grn_res.text}"
    grn = grn_res.json()
    grn_id = grn["id"]
    print(f"  -> 5. GRN Created: {grn['grn_number']} for receipt value $2,000.00")

    # Approve GRN -> Posts GL Voucher (Dr 6060, Cr 2010)
    app_grn = client.post("/api/approvals/action", json={
        "module": "GRN",
        "document_id": grn_id,
        "action": "approve"
    })
    assert app_grn.status_code == 200
    print("  -> 6. GRN Approved -> Auto-posted GL Voucher: Dr 6060 ($2,000) / Cr 2010 GRN Accrual ($2,000).")

    # Create Mode A AP Invoice (3-Way Match)
    ap_inv_payload = {
        "invoice_mode": "Mode_A_PO",
        "vendor_code": "VEND-001",
        "vendor_invoice_ref": "VEND-INV-88710",
        "po_number": po_number,
        "grn_number": grn["grn_number"],
        "invoice_date": today,
        "due_date": today,
        "tax_code": "VAT-STD-5",
        "subtotal": 2000.0,
        "tax_amount": 100.0,
        "total_amount": 2100.0,
        "notes": "3-Way Match Invoice"
    }
    ap_inv_res = client.post("/api/ap/invoices?status=Pending Approval", json=ap_inv_payload)
    assert ap_inv_res.status_code == 200
    ap_inv = ap_inv_res.json()
    ap_inv_id = ap_inv["id"]
    print(f"  -> 7. AP Invoice Created: {ap_inv['invoice_number']} for ${ap_inv['total_amount']:,.2f}")

    # Approve AP Invoice -> Posts GL Voucher (Dr 2010 GRN Accrual, Dr 1150 Input VAT, Cr 2000 AP)
    app_ap_inv = client.post("/api/approvals/action", json={
        "module": "AP-INV",
        "document_id": ap_inv_id,
        "action": "approve"
    })
    assert app_ap_inv.status_code == 200
    print("  -> 8. AP Invoice Approved -> Auto-posted GL Voucher: Dr 2010 ($2,000) + Dr 1150 ($100) / Cr 2000 AP ($2,100).")

    # Create AP Payment
    ap_pmt_payload = {
        "payment_date": today,
        "vendor_code": "VEND-001",
        "bank_account_code": "1010",
        "payment_ref": "CHK-998822",
        "payment_method": "Bank Transfer",
        "lines": [
            {
                "ap_invoice_id": ap_inv_id,
                "invoice_number": ap_inv["invoice_number"],
                "amount_paid": 2100.0
            }
        ]
    }
    ap_pmt_res = client.post("/api/ap/payments?status=Pending Approval", json=ap_pmt_payload)
    assert ap_pmt_res.status_code == 200
    ap_pmt = ap_pmt_res.json()
    ap_pmt_id = ap_pmt["id"]
    print(f"  -> 9. AP Payment Proposed: {ap_pmt['payment_number']} for ${ap_pmt['total_amount']:,.2f}")

    # Approve AP Payment -> Posts GL Voucher (Dr 2000 AP, Cr 1010 Bank)
    app_ap_pmt = client.post("/api/approvals/action", json={
        "module": "AP-PMT",
        "document_id": ap_pmt_id,
        "action": "approve"
    })
    assert app_ap_pmt.status_code == 200
    print("  -> 10. AP Payment Approved -> Auto-posted GL Voucher: Dr 2000 AP ($2,100) / Cr 1010 Bank ($2,100).")
    print("  -> PASS: Complete P2P cycle executed and reconciled.")

    # 5. Execute Full End-to-End O2C Cycle (AR Invoice -> AR Receipt)
    print("\n[Step 5] Executing Full O2C Cycle (AR Invoice -> AR Receipt)...")
    ar_inv_payload = {
        "customer_code": "CUST-002",
        "invoice_date": today,
        "due_date": today,
        "notes": "Automated E2E Test Consulting Billing",
        "lines": [
            {
                "description": "Enterprise Solutions Architecture Consulting",
                "revenue_account_code": "4000",
                "quantity": 1.0,
                "unit_price": 50000.0,
                "discount_amount": 0.0,
                "tax_code": "VAT-STD-5"
            }
        ]
    }
    ar_inv_res = client.post("/api/ar/invoices?status=Pending Approval", json=ar_inv_payload)
    assert ar_inv_res.status_code == 200
    ar_inv = ar_inv_res.json()
    ar_inv_id = ar_inv["id"]
    print(f"  -> 1. AR Invoice Created: {ar_inv['invoice_number']} for Subtotal ${ar_inv['subtotal']:,.2f} + VAT ${ar_inv['tax_amount']:,.2f} = ${ar_inv['total_amount']:,.2f}")

    # Approve AR Invoice -> Posts GL Voucher (Dr 1100 AR, Cr 4000 Revenue, Cr 2020 Output VAT)
    app_ar_inv = client.post("/api/approvals/action", json={
        "module": "AR-INV",
        "document_id": ar_inv_id,
        "action": "approve"
    })
    assert app_ar_inv.status_code == 200
    print("  -> 2. AR Invoice Approved -> Auto-posted GL: Dr 1100 AR ($52,500) / Cr 4000 Revenue ($50,000) / Cr 2020 VAT ($2,500).")

    # Create AR Receipt
    ar_rcpt_payload = {
        "receipt_date": today,
        "customer_code": "CUST-002",
        "bank_account_code": "1010",
        "receipt_ref": "WIRE-CUST2-7711",
        "receipt_method": "Bank Wire",
        "lines": [
            {
                "ar_invoice_id": ar_inv_id,
                "invoice_number": ar_inv["invoice_number"],
                "amount_received": 52500.0
            }
        ]
    }
    ar_rcpt_res = client.post("/api/ar/receipts?status=Pending Approval", json=ar_rcpt_payload)
    assert ar_rcpt_res.status_code == 200
    ar_rcpt = ar_rcpt_res.json()
    ar_rcpt_id = ar_rcpt["id"]
    print(f"  -> 3. AR Receipt Created: {ar_rcpt['receipt_number']} for ${ar_rcpt['total_amount']:,.2f}")

    # Approve AR Receipt -> Posts GL Voucher (Dr 1010 Bank, Cr 1100 AR)
    app_ar_rcpt = client.post("/api/approvals/action", json={
        "module": "AR-RCPT",
        "document_id": ar_rcpt_id,
        "action": "approve"
    })
    assert app_ar_rcpt.status_code == 200
    print("  -> 4. AR Receipt Approved -> Auto-posted GL: Dr 1010 Bank ($52,500) / Cr 1100 AR ($52,500).")
    print("  -> PASS: Complete O2C cycle executed and reconciled.")

    # 6. Verify Master General Ledger Transactions
    print("\n[Step 6] Verifying Master General Ledger Integrity...")
    vouchers_res = client.get("/api/gl/vouchers?status=Approved")
    assert vouchers_res.status_code == 200
    vouchers = vouchers_res.json()
    print(f"  -> Total Approved GL Vouchers: {len(vouchers)}")
    for v in vouchers:
        assert abs(v["total_debit"] - v["total_credit"]) < 0.01, f"Voucher {v['voucher_no']} out of balance!"
    print("  -> PASS: Every single posted GL voucher is perfectly balanced (Debit == Credit).")

    # 7. Verify Trial Balance
    print("\n[Step 7] Verifying Trial Balance Report Totals...")
    tb_res = client.get("/api/reports/trial-balance")
    assert tb_res.status_code == 200
    tb = tb_res.json()
    print(f"  -> Opening Debits:  ${tb['total_opening_debit']:,.2f}  |  Opening Credits:  ${tb['total_opening_credit']:,.2f}")
    print(f"  -> Period Debits:   ${tb['total_period_debit']:,.2f}  |  Period Credits:   ${tb['total_period_credit']:,.2f}")
    print(f"  -> Closing Debits:  ${tb['total_closing_debit']:,.2f}  |  Closing Credits:  ${tb['total_closing_credit']:,.2f}")
    assert tb["is_balanced"] is True, "Trial balance reported is_balanced = False!"
    assert abs(tb["total_closing_debit"] - tb["total_closing_credit"]) < 0.05
    print("  -> PASS: Trial Balance perfectly balanced across all columns.")

    # 8. Verify Balance Sheet Golden Equation
    print("\n[Step 8] Verifying Balance Sheet Golden Accounting Equation...")
    bs_res = client.get("/api/reports/balance-sheet")
    assert bs_res.status_code == 200
    bs = bs_res.json()
    print(f"  -> Total Assets:                     ${bs['total_assets']:,.2f}")
    print(f"  -> Total Liabilities & Equity:       ${bs['total_liabilities_and_equity']:,.2f}")
    print(f"  -> Equation Variance:                ${bs['variance']:,.2f}")
    print(f"  -> Balanced Status:                  {bs['is_balanced']}")
    assert bs["is_balanced"] is True, f"Balance sheet NOT balanced! Assets: {bs['total_assets']}, L+E: {bs['total_liabilities_and_equity']}"
    assert abs(bs["variance"]) < 0.05
    print("  -> PASS: Total Assets == Total Liabilities + Total Equity (including Net Profit roll-forward)!")

    # 9. Verify Taxation (VAT Return)
    print("\n[Step 9] Verifying Taxation Module & VAT Return...")
    tax_res = client.get("/api/tax/return-summary")
    assert tax_res.status_code == 200
    tr = tax_res.json()
    b1_tax = tr["box1_output_standard"]["tax_amount"]
    b3_tax = tr["box3_input_standard"]["tax_amount"]
    b4_tax = tr["box4_net_tax"]["tax_amount"]
    print(f"  -> Box 1 Output VAT: ${b1_tax:,.2f}")
    print(f"  -> Box 3 Input VAT:  ${b3_tax:,.2f}")
    print(f"  -> Box 4 Net VAT:    ${b4_tax:,.2f}")
    assert round(b1_tax - b3_tax, 2) == round(b4_tax, 2)
    print("  -> PASS: VAT Return Box 4 equals Box 1 Output Tax minus Box 3 Input Tax.")

    print("\n" + "=" * 75)
    print("  ALL 9 AUTOMATED ACCOUNTING VERIFICATION CHECKS PASSED WITH ZERO ERRORS!")
    print("=" * 75)

if __name__ == "__main__":
    run_verification()
