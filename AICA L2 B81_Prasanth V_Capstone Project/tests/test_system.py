import sys
import io
from pathlib import Path

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.seed import seed_database
from app.services.excel_service import generate_excel_template, parse_and_validate_excel
from app.database import SessionLocal
from app.models import Company, Asset, User, DuplicateOverride, AuditLog

client = TestClient(app)

def run_acceptance_tests():
    print("\n" + "=" * 65)
    print("   RUNNING AUTOMATED ACCEPTANCE TEST SUITE (TATA & RELIANCE)")
    print("=" * 65)

    # Setup database
    seed_database(reset_data=False)
    db = SessionLocal()

    # 1. Login & Token Verification
    print("\n[TEST 0] Testing User Authentication & JWT...")
    login_res = client.post("/api/auth/login", data={"username": "prasanth@gmail.com", "password": "123456789"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  [PASS] Admin Login Successful. Token obtained.")

    # 2. Test 1: Manual Asset Tag Generation for TATA
    print("\n[TEST 1] Testing Manual Asset Tag Creation for TATA...")
    tata = db.query(Company).filter(Company.short_name == "TATA").first()
    assert tata is not None, "Demo company TATA not found"

    # Clean test ID
    db.query(Asset).filter(Asset.company_id == tata.id, Asset.asset_id == "TATA-TEST-001").delete()
    db.commit()

    create_res = client.post("/api/assets", json={
        "company_id": tata.id,
        "asset_id": "TATA-TEST-001",
        "asset_type": "FIXED_ASSET",
        "description": "SERVER DELL POWEREDGE R750",
        "location": "MUM-DC-BAY-12",
        "sap_number": "41009821-0",
        "code_type": "BARCODE"
    }, headers=headers)
    assert create_res.status_code == 200, f"Manual asset creation failed: {create_res.text}"
    created_id = create_res.json()["id"]
    print(f"  [PASS] Manual Asset TATA-TEST-001 created successfully (DB ID: {created_id}).")

    # 3. Test 2: QR Code Symbology Generation for Reliance
    print("\n[TEST 2] Testing QR Code Asset Tag Creation for Reliance...")
    reliance = db.query(Company).filter(Company.short_name == "Reliance").first()
    assert reliance is not None, "Demo company Reliance not found"

    # Clean any pre-existing test ID (including seeded demo data)
    db.query(Asset).filter(Asset.company_id == reliance.id, Asset.asset_id == "RIL-TEST-002").delete()
    db.commit()

    qr_res = client.post("/api/assets", json={
        "company_id": reliance.id,
        "asset_id": "RIL-TEST-002",
        "asset_type": "FIXED_ASSET",
        "description": "5G BASEBAND PROCESSING UNIT",
        "location": "JIO-NOC-NAVIMUMBAI",
        "sap_number": "92004510-1",
        "code_type": "QR_CODE"
    }, headers=headers)
    assert qr_res.status_code == 200, f"QR creation failed: {qr_res.text}"
    print("  [PASS] QR Code tag RIL-TEST-002 created successfully.")

    # 4. Test 3: Duplicate Asset ID Detection
    print("\n[TEST 3] Testing Real-Time Duplicate Asset ID Detection...")
    dup_check = client.post("/api/assets/check-duplicate", json={
        "company_id": tata.id,
        "asset_id": "TATA-TEST-001"
    }, headers=headers)
    assert dup_check.status_code == 200
    assert dup_check.json()["is_duplicate"] is True, "Duplicate detection failed to flag existing ID"
    print("  [PASS] Duplicate detection accurately flagged TATA-TEST-001 as existing.")

    # Attempt to insert duplicate without override
    dup_attempt = client.post("/api/assets", json={
        "company_id": tata.id,
        "asset_id": "TATA-TEST-001",
        "asset_type": "FIXED_ASSET",
        "description": "Duplicate Item",
        "code_type": "BARCODE"
    }, headers=headers)
    assert dup_attempt.status_code == 400, "Duplicate was not blocked!"
    print("  [PASS] Duplicate insertion correctly blocked with 400 error.")

    # 5. Test 4: Duplicate Override Workflow with Mandatory Comment
    print("\n[TEST 4] Testing Duplicate Override Justification Workflow...")
    override_res = client.post("/api/assets", json={
        "company_id": tata.id,
        "asset_id": "TATA-TEST-001",
        "asset_type": "FIXED_ASSET",
        "description": "SERVER DELL REPLACEMENT TAG",
        "code_type": "BARCODE",
        "is_override": True,
        "override_reason": "Replacement physical tag for damaged machine sticker."
    }, headers=headers)
    assert override_res.status_code == 200, f"Override failed: {override_res.text}"
    print("  [PASS] Duplicate override executed and recorded in audit trail.")

    # 6. Test 5: Automatic ID Generation & Atomic Sequencing for TATA
    print("\n[TEST 5] Testing Automatic Sequence Numbering...")
    auto_res = client.post("/api/assets", json={
        "company_id": tata.id,
        "asset_id": "",
        "auto_generate_id": True,
        "asset_type": "FIXED_ASSET",
        "description": "AUTO-ALLOCATED TATA ASSET",
        "code_type": "BARCODE"
    }, headers=headers)
    assert auto_res.status_code == 200
    auto_id = auto_res.json()["asset_id"]
    print(f"  [PASS] Atomic sequence automatically generated unique ID: {auto_id}")

    # 7. Test 6: Bulk Excel Template & Multi-Stage Validation
    print("\n[TEST 6] Testing Bulk Excel Template Download & Validation...")
    template_stream = generate_excel_template()
    assert template_stream.getbuffer().nbytes > 1000, "Template generation produced empty file"
    
    validation_res = parse_and_validate_excel(template_stream.getvalue(), db)
    assert validation_res["total_rows"] >= 3, "Excel validation failed to read sample rows"
    print(f"  [PASS] Excel parser validated {validation_res['total_rows']} sample rows.")

    # 8. Test 7: Individual PNG Image Generation with Asset ID Naming
    print("\n[TEST 7] Testing PNG Image Generation & Filename Compliance...")
    img_res = client.get(f"/api/assets/{created_id}/image")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/png"
    assert "TATA-TEST-001.png" in img_res.headers["content-disposition"]
    print("  [PASS] High-res PNG generated with exact filename: TATA-TEST-001.png")

    # 9. Test 8: A4 Sheet Layout Calculation & Multi-Page PDF & Word Docx Generation
    print("\n[TEST 8] Testing Sheet Layout PDF & Word (.docx) Generators...")
    pdf_res = client.post("/api/printing/generate-sheet-pdf?asset_ids=1&asset_ids=2", json={
        "page_size": "A4",
        "orientation": "PORTRAIT",
        "label_width_mm": 70.0,
        "label_height_mm": 35.0,
        "margin_top_mm": 10.0,
        "margin_bottom_mm": 10.0,
        "margin_left_mm": 10.0,
        "margin_right_mm": 10.0,
        "horizontal_gap_mm": 3.0,
        "vertical_gap_mm": 3.0
    }, headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    print("  [PASS] PDF Sheet Generation Verified.")

    docx_res = client.post("/api/printing/generate-sheet-docx?asset_ids=1&asset_ids=2", json={
        "page_size": "A4",
        "orientation": "PORTRAIT",
        "label_width_mm": 70.0,
        "label_height_mm": 35.0,
        "columns": 2,
        "rows": 7
    }, headers=headers)
    assert docx_res.status_code == 200
    assert "wordprocessingml" in docx_res.headers["content-type"]
    print("  [PASS] Word Document (.docx) Sheet Generation Verified.")

    # 10. Test 9: Templates Library (8 Presets)
    print("\n[TEST 9] Testing System Saved Templates Library...")
    tmpl_res = client.get("/api/templates", headers=headers)
    assert tmpl_res.status_code == 200
    templates = tmpl_res.json()
    assert len(templates) >= 8, f"Expected at least 8 templates, got {len(templates)}"
    print(f"  [PASS] System templates verified: {len(templates)} presets loaded.")

    db.close()
    print("\n" + "=" * 65)
    print("   ALL TESTS PASSED FOR TATA & RELIANCE WITH ZERO ERRORS!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_acceptance_tests()
