from backend.app.database import SessionLocal
from backend.app.models import CompanyModel
from fastapi.testclient import TestClient
from backend.app.main import app

def debug_statements_api():
    db = SessionLocal()
    company = db.query(CompanyModel).filter(CompanyModel.company_code == "COMP001").first()
    db.close()
    
    if not company:
        print("ERROR: Company COMP001 not found!")
        return

    with TestClient(app) as client:
        # Auth login
        res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        token = res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test all-statements endpoint
        url = f"/api/v1/financials/{company.id}/all-statements?period=Q1&year=FY2024"
        res = client.get(url, headers=headers)
        print("ALL-STATEMENTS API STATUS:", res.status_code)
        print("ALL-STATEMENTS RESPONSE JSON:")
        import json
        print(json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    debug_statements_api()
