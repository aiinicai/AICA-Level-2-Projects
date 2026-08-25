from backend.app.database import SessionLocal
from backend.app.models import TrialBalanceModel, CompanyModel

def check_db_quarters():
    db = SessionLocal()
    company = db.query(CompanyModel).filter(CompanyModel.company_code == "COMP001").first()
    if not company:
        print("Company COMP001 not found!")
        return

    q_types = db.query(TrialBalanceModel.quarter, TrialBalanceModel.fiscal_year).filter(TrialBalanceModel.company_id == company.id).distinct().all()
    print("DISTINCT (QUARTER, FISCAL_YEAR) IN DB:")
    for q, fy in q_types:
        count = db.query(TrialBalanceModel).filter(TrialBalanceModel.company_id == company.id, TrialBalanceModel.quarter == q, TrialBalanceModel.fiscal_year == fy).count()
        print(f"  Quarter: '{q}', Year: '{fy}' -> {count} rows")

    db.close()

if __name__ == "__main__":
    check_db_quarters()
