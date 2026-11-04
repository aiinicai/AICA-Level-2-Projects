import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("================================================================")
    print("RUNNING END-TO-END MULTI-COMPANY & EXPORTS VERIFICATION SUITE")
    print("================================================================")

    # 1. Test Listing Companies
    print("\n[TEST 1] Listing Registered Companies...")
    r = requests.get(f"{BASE_URL}/api/companies")
    assert r.status_code == 200, f"Failed listing companies: {r.text}"
    comps = r.json()
    print(f"-> Found {len(comps)} companies: {[c['company_name'] for c in comps]}")
    assert len(comps) >= 1
    c1 = comps[0]
    assert c1["is_active"] is True

    # 2. Test PIN Verification
    print("\n[TEST 2] Testing 4-Digit Security PIN Verification...")
    # Wrong PIN
    r_bad = requests.post(f"{BASE_URL}/api/companies/verify-pin", json={"company_id": c1["id"], "pin": "0000"})
    assert r_bad.status_code == 401, f"Expected 401 for wrong PIN, got {r_bad.status_code}"
    print("-> Wrong PIN (0000) correctly rejected with 401 Unauthorized.")

    # Correct PIN
    r_good = requests.post(f"{BASE_URL}/api/companies/verify-pin", json={"company_id": c1["id"], "pin": "1234"})
    assert r_good.status_code == 200, f"Expected 200 for correct PIN, got {r_good.status_code}"
    print("-> Correct PIN (1234) successfully authenticated with 200 OK.")

    # 3. Test Creating a New Company with 4-Digit PIN
    print("\n[TEST 3] Creating New Company with 4-Digit PIN...")
    new_comp_payload = {
        "company_name": "Demo Business 9",
        "trn": "DEMO-TRN",
        "pin": "5678",
        "company_address": "Fictional Demo Address",
        "currency": "AED",
        "currency_symbol": "AED",
        "phone": "DEMO-PHONE",
        "email": "demo@example.com"
    }
    r_create = requests.post(f"{BASE_URL}/api/companies/create", json=new_comp_payload)
    assert r_create.status_code == 200, f"Failed creating company: {r_create.text}"
    c2 = r_create.json()
    print(f"-> New Company Created: {c2['company_name']} (ID: {c2['id']})")
    assert c2["is_active"] is True

    # Verify Company 2 database is completely fresh with $0.00 balances
    print("\n[TEST 4] Verifying Data Isolation in Company 2...")
    r_c2_tb = requests.get(f"{BASE_URL}/api/reports/trial-balance", headers={"X-Company-Id": c2["id"]})
    assert r_c2_tb.status_code == 200
    tb2 = r_c2_tb.json()
    print(f"-> Company 2 Trial Balance: Closing Debit = {tb2['total_closing_debit']}, Closing Credit = {tb2['total_closing_credit']}")
    assert tb2["total_closing_debit"] == 0.0, "Company 2 should start with clean $0.00 balances"

    r_c2_inv = requests.get(f"{BASE_URL}/api/inventory/items", headers={"X-Company-Id": c2["id"]})
    assert r_c2_inv.status_code == 200
    assert len(r_c2_inv.json()) == 0, "Company 2 should start with 0 inventory items"
    print("-> Company 2 isolated database successfully verified with clean 0 transactions and $0.00 ledger.")

    # 4. Test Switching back to Company 1 using PIN 1234
    print("\n[TEST 5] Switching back to Company 1 using PIN 1234...")
    r_switch = requests.post(f"{BASE_URL}/api/companies/switch", json={"company_id": c1["id"], "pin": "1234"})
    assert r_switch.status_code == 200, f"Failed switching: {r_switch.text}"
    c1_switched = r_switch.json()
    print(f"-> Successfully switched to active company: {c1_switched['company_name']}")
    assert c1_switched["is_active"] is True

    # 5. Verify Company 1 Data is preserved intact
    print("\n[TEST 6] Verifying Company 1 Data Preservation...")
    r_c1_tb = requests.get(f"{BASE_URL}/api/reports/trial-balance")
    assert r_c1_tb.status_code == 200
    tb1 = r_c1_tb.json()
    print(f"-> Company 1 Trial Balance Total: Closing Debit = {tb1['total_closing_debit']}, Closing Credit = {tb1['total_closing_credit']}")
    assert tb1["total_closing_debit"] == tb1["total_closing_credit"], "Company 1 trial balance must balance"

    # 6. Verify Dashboard KPIs and Charts Data
    print("\n[TEST 7] Verifying Live Dashboard KPIs and Charts Data...")
    r_kpis = requests.get(f"{BASE_URL}/api/reports/dashboard-kpis")
    assert r_kpis.status_code == 200
    kpis = r_kpis.json()
    print(f"-> Dashboard KPIs: Revenue={kpis['total_revenue']}, Net Profit={kpis['net_profit']}, Cash/Bank={kpis['cash_bank_balance']}, Open AR={kpis['open_ar']}, Open AP={kpis['open_ap']}")

    r_charts = requests.get(f"{BASE_URL}/api/reports/charts-data")
    assert r_charts.status_code == 200
    charts = r_charts.json()
    assert "trend_analysis" in charts
    assert "sales_by_customer" in charts
    assert "aging_summary" in charts
    assert "budget_vs_actual" in charts
    print("-> Charts data structure verified with trend, sales_by_customer, aging_summary, and budget_vs_actual.")

    # 7. Verify UAE FTA VAT 201 Return
    print("\n[TEST 8] Verifying UAE FTA VAT Return Data...")
    r_tax = requests.get(f"{BASE_URL}/api/tax/return-summary")
    assert r_tax.status_code == 200
    tax = r_tax.json()
    print(f"-> VAT Return: Box 1 Standard Output={tax['box1_output_standard']['tax_amount']}, Box 3 Standard Input={tax['box3_input_standard']['tax_amount']}, Net Tax={tax['box4_net_tax']['tax_amount']}")

    # 8. Verify Index HTML and Static JS Assets
    print("\n[TEST 9] Verifying Frontend HTML and Asset Loading...")
    r_index = requests.get(f"{BASE_URL}/")
    assert r_index.status_code == 200
    html = r_index.text
    assert "Demo Business 21" in html
    assert "modal-company-switcher" in html
    assert "modal-verify-pin" in html
    assert "modal-create-company" in html
    assert "downloadDashboardPPT" in html
    assert "downloadManagementPackPDF" in html
    assert "exportDashboardExcel" in html
    assert "exportTaxReturnExcel" in html
    assert "downloadFinancialStatementsPDF" in html
    assert "pptxgenjs" in html.lower()
    print("-> Frontend index.html verified with all modal IDs, PPTXGenJS script tag, and export action buttons.")

    r_js = requests.get(f"{BASE_URL}/static/js/app.js")
    assert r_js.status_code == 200
    js = r_js.text
    assert "window.downloadDashboardPPT" in js
    assert "window.downloadManagementPackPDF" in js
    assert "window.exportDashboardExcel" in js
    assert "window.exportTaxReturnExcel" in js
    assert "window.downloadFinancialStatementsPDF" in js
    assert "window.submitPinVerification" in js
    assert "window.requestSwitchCompany" in js
    assert "window.submitCreateCompany" in js
    assert "DYNAMICS ENTERPRISE GLOBAL LLC" not in js, "Hardcoded company name must not exist in app.js"
    print("-> app.js verified with all export handlers, PIN security functions, and zero hardcoded company names.")

    print("\n================================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! ZERO ERRORS.")
    print("================================================================")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
        sys.exit(1)
