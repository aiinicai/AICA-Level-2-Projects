import os
from backend.app.database import SessionLocal, engine, Base
from backend.app.models import UserModel, CompanyModel, TrialBalanceModel
from backend.app.auth import hash_password
from backend.app.config import config
from backend.app.parser import parse_excel_trial_balance

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create Admin user
        user = db.query(UserModel).filter(UserModel.username == config.DEMO_USER).first()
        if not user:
            user = UserModel(
                username=config.DEMO_USER,
                email="admin@finkpi.com",
                password_hash=hash_password(config.DEMO_PASSWORD),
                role="admin",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create Demo Company COMP001
        company = db.query(CompanyModel).filter(CompanyModel.company_code == "COMP001").first()
        if not company:
            company = CompanyModel(
                company_code="COMP001",
                company_name="ABC Manufacturing Co.",
                industry="Manufacturing",
                currency="USD",
                currency_unit="thousands",
                fiscal_year_start=1,
                shares_outstanding=1000000.0,
                headcount=500
            )
            db.add(company)
            db.commit()
            db.refresh(company)

        # Load and parse sample Excel file if exists
        excel_file = "TrialBalance_COMP001_FY2023_FY2024.xlsx"
        if os.path.exists(excel_file):
            print(f"Loading {excel_file}...")
            with open(excel_file, "rb") as f:
                parsed = parse_excel_trial_balance(f.read())
            
            # Clear old records
            db.query(TrialBalanceModel).filter(TrialBalanceModel.company_id == company.id).delete()

            recs = [
                TrialBalanceModel(
                    company_id=company.id,
                    fiscal_year=r["fiscal_year"],
                    quarter=r["quarter"],
                    period_id=r["period_id"],
                    period_sequence=r["period_sequence"],
                    account_code=r["account_code"],
                    account_name=r["account_name"],
                    category=r["category"],
                    sub_category=r["sub_category"],
                    account_type=r["account_type"],
                    normal_balance=r["normal_balance"],
                    debit_amount=r["debit_amount"],
                    credit_amount=r["credit_amount"],
                    net_balance=r["net_balance"]
                )
                for r in parsed["records"]
            ]
            db.bulk_save_objects(recs)
            db.commit()
            print(f"Seeded {len(recs)} Trial Balance records across {parsed['periods_detected']} periods for COMP001.")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
