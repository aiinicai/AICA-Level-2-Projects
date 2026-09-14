import sys
import os
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from services.excel_parser import load_sample_dataset, generate_sample_templates
from services.fs_generator import generate_financial_statements
from services.ratio_engine import calculate_ratios
from services.validation_engine import run_validation_checks
from services.export_service import export_formula_linked_excel, export_pdf_review_pack

def test_full_flow():
    print("Testing FS Builder Lite v0.2 Backend Execution...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    # 1. Create client
    client = models.Client(
        name="Test Apex Engineering Industries Ltd",
        entity_type="Private Limited Company",
        reporting_period="FY 2024-25",
        previous_year_period="FY 2023-24"
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    print(f"1. Client Created: ID={client.id}, Name={client.name}")

    # 2. Load sample data
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_data")
    load_sample_dataset(client.id, sample_dir, db)
    print("2. Sample Trial Balance and 6 supporting schedules loaded.")

    # 3. Generate Financial Statements
    fs = generate_financial_statements(client.id, db)
    print(f"3. Balance Sheet Tallied: {fs.is_tallied} (Diff={fs.difference})")

    # 4. Ratios
    ratios = calculate_ratios(client.id, db)
    print(f"4. Ratios Calculated: {len(ratios)} ratios computed.")

    # 5. Validations
    validations = run_validation_checks(client.id, db)
    print(f"5. Audit Validations Run: {len(validations)} checks evaluated.")

    # 6. Export Excel & PDF
    exports_dir = os.path.join(os.path.dirname(__file__), "exports")
    excel_path = export_formula_linked_excel(client.id, exports_dir, db)
    pdf_path = export_pdf_review_pack(client.id, exports_dir, db)
    print(f"6. Excel Exported: {excel_path}")
    print(f"7. PDF Exported: {pdf_path}")

    print("\nSYSTEM TEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_flow()
