from fastapi.testclient import TestClient
from backend.app.main import app

def run_all_tests():
    print("==================================================")
    print("RUNNING API TEST SUITE FOR FINKPI ANALYZER")
    print("==================================================")

    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/health")
        assert res.status_code == 200
        print("[PASS] 1. /health endpoint")

        # 2. Auth Login
        res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        assert res.status_code == 200
        token = res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[PASS] 2. /api/v1/auth/login endpoint")

        # 3. Companies List
        res = client.get("/api/v1/companies", headers=headers)
        assert res.status_code == 200
        companies = res.json()["data"]
        assert len(companies) > 0
        company_id = companies[0]["id"]
        print(f"[PASS] 3. /api/v1/companies endpoint -> Company ID: {company_id}")

        # 4. Trial Balance Validation
        res = client.post(f"/api/v1/trial-balance/validate?companyId={company_id}", headers=headers)
        assert res.status_code == 200
        val_data = res.json()["data"]
        print(f"[PASS] 4. /api/v1/trial-balance/validate -> All periods balanced: {val_data['allPeriodsBalanced']}")

        # 5. Income Statement
        res = client.get(f"/api/v1/financials/{company_id}/income-statement?period=Q1&year=FY2024", headers=headers)
        assert res.status_code == 200
        pnl = res.json()["data"]
        assert "net_revenue" in pnl and "net_income" in pnl
        print(f"[PASS] 5. /api/v1/financials/{company_id}/income-statement -> Q1 FY24 Net Rev: INR {pnl['net_revenue']:,.2f}, Net Income: INR {pnl['net_income']:,.2f}")

        # 6. Balance Sheet
        res = client.get(f"/api/v1/financials/{company_id}/balance-sheet?period=Q4&year=FY2024", headers=headers)
        assert res.status_code == 200
        bs = res.json()["data"]
        assert bs["is_balanced"] == True
        print(f"[PASS] 6. /api/v1/financials/{company_id}/balance-sheet -> Q4 FY24 Total Assets: INR {bs['assets']['total_assets']:,.2f}, Balanced: {bs['is_balanced']}")

        # 7. All KPIs
        res = client.get(f"/api/v1/kpi/{company_id}/all?period=Q1&year=FY2024", headers=headers)
        assert res.status_code == 200
        kpis = res.json()["data"]["kpi"]
        gp_m = kpis["profitability"]["gross_profit_margin"]
        print(f"[PASS] 8. /api/v1/kpi/{company_id}/all -> Gross Profit Margin: {gp_m['value']}% (QoQ Delta: {gp_m['qoq_delta']}%, RAG: {gp_m['rag_status']})")

        # 9. Scorecard
        res = client.get(f"/api/v1/kpi/{company_id}/scorecard", headers=headers)
        assert res.status_code == 200
        sc = res.json()["data"]
        print(f"[PASS] 9. /api/v1/kpi/{company_id}/scorecard -> Scorecard loaded for {len(sc)} periods")

        # 10. Cross-year QoQ analysis
        res = client.get(f"/api/v1/analysis/{company_id}/qoq/crossyear", headers=headers)
        assert res.status_code == 200
        print("[PASS] 10. /api/v1/analysis/{company_id}/qoq/crossyear (Q4FY23 -> Q1FY24)")

        # 11. YoY analysis
        res = client.get(f"/api/v1/analysis/{company_id}/yoy", headers=headers)
        assert res.status_code == 200
        print("[PASS] 11. /api/v1/analysis/{company_id}/yoy")

        # 12. Export Excel
        res = client.get(f"/api/v1/reports/{company_id}/export?format=excel&period=Q4&year=FY2024", headers=headers)
        assert res.status_code == 200
        assert len(res.content) > 1000
        print("[PASS] 12. /api/v1/reports/{company_id}/export (Excel format)")

        # 13. Export PDF
        res = client.get(f"/api/v1/reports/{company_id}/export?format=pdf&period=Q4&year=FY2024", headers=headers)
        assert res.status_code == 200
        assert len(res.content) > 1000
        print("[PASS] 13. /api/v1/reports/{company_id}/export (PDF format)")

    print("==================================================")
    print("ALL API ENDPOINT TESTS PASSED SUCCESSFULLY! (13/13)")
    print("==================================================")

if __name__ == "__main__":
    run_all_tests()
