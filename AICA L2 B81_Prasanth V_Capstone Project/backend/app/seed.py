import os
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import User, Company, Asset, TagTemplate, LabelSize, AuditLog, SystemSettings, DuplicateOverride
from .auth import get_password_hash

def seed_database(reset_data: bool = False):
    """
    Initializes and seeds database schema.
    If reset_data=True, clears previous logs, companies and assets and seeds fresh TATA & Reliance companies.
    """
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        if reset_data:
            # Clear in exact foreign-key order
            db.query(SystemSettings).delete()
            db.query(DuplicateOverride).delete()
            db.query(AuditLog).delete()
            db.query(Asset).delete()
            db.query(TagTemplate).delete()
            db.query(Company).delete()
            db.commit()

        # 1. Demo Users
        admin_user = db.query(User).filter(User.email == "prasanth@gmail.com").first()
        if not admin_user:
            admin_user = User(
                email="prasanth@gmail.com",
                password_hash=get_password_hash("123456789"),
                full_name="Prasanth (Lead Consultant)",
                role="ADMIN",
                is_active=True
            )
            db.add(admin_user)

        std_user = db.query(User).filter(User.email == "mahesh@gmail.com").first()
        if not std_user:
            std_user = User(
                email="mahesh@gmail.com",
                password_hash=get_password_hash("987654321"),
                full_name="Mahesh (Tagging Field Officer)",
                role="STANDARD_USER",
                is_active=True
            )
            db.add(std_user)

        db.commit()
        db.refresh(admin_user)
        db.refresh(std_user)

        # 2. Fresh Demo Companies: TATA & Reliance
        tata = db.query(Company).filter(Company.short_name == "TATA").first()
        if not tata:
            tata = Company(
                name="Tata Consultancy Services Limited",
                short_name="TATA",
                logo_path="/uploads/logos/tata_logo.png",
                address="Bombay House, 24 Homi Mody Street, Mumbai, Maharashtra 400001",
                asset_id_prefix="TATA",
                numbering_format="{PREFIX}-{NUM:6}",
                starting_number=1,
                current_number=3,
                is_active=True,
                created_by=admin_user.id
            )
            db.add(tata)

        reliance = db.query(Company).filter(Company.short_name == "Reliance").first()
        if not reliance:
            reliance = Company(
                name="Reliance Industries Limited",
                short_name="Reliance",
                logo_path="/uploads/logos/reliance_logo.png",
                address="Maker Chambers IV, 222 Nariman Point, Mumbai, Maharashtra 400021",
                asset_id_prefix="RIL",
                numbering_format="{PREFIX}-{NUM:6}",
                starting_number=1,
                current_number=3,
                is_active=True,
                created_by=admin_user.id
            )
            db.add(reliance)

        db.commit()
        db.refresh(tata)
        db.refresh(reliance)

        # 3. Rich System Templates Library
        system_templates = [
            {
                "template_name": "Standard Corporate (Reference)",
                "width_mm": 70.0,
                "height_mm": 35.0,
                "code_type": "BARCODE",
                "code_position": "BOTTOM",
                "show_logo": True,
                "show_company_name": True,
                "field_visibility": {"sap_number": True, "description": True, "location": True},
                "font_settings": {"company_size": 9, "label_size": 7, "value_size": 7},
                "is_default": True
            },
            {
                "template_name": "Compact QR Asset Label (60 × 30 mm)",
                "width_mm": 60.0,
                "height_mm": 30.0,
                "code_type": "QR_CODE",
                "code_position": "RIGHT",
                "show_logo": True,
                "show_company_name": True,
                "field_visibility": {"sap_number": True, "description": True, "location": True},
                "font_settings": {"company_size": 8, "label_size": 6.5, "value_size": 6.5},
                "is_default": False
            },
            {
                "template_name": "Industrial Heavy Duty (100 × 50 mm)",
                "width_mm": 100.0,
                "height_mm": 50.0,
                "code_type": "BARCODE",
                "code_position": "BOTTOM",
                "show_logo": True,
                "show_company_name": True,
                "field_visibility": {"sap_number": True, "description": True, "location": True, "serial_number": True, "department": True},
                "font_settings": {"company_size": 11, "label_size": 8, "value_size": 8},
                "is_default": False
            },
            {
                "template_name": "Warehouse Bin & Stock Tag (100 × 75 mm)",
                "width_mm": 100.0,
                "height_mm": 75.0,
                "code_type": "BARCODE",
                "code_position": "BOTTOM",
                "show_logo": True,
                "show_company_name": True,
                "field_visibility": {"sap_number": True, "description": True, "location": True, "custodian": True},
                "font_settings": {"company_size": 12, "label_size": 9, "value_size": 9},
                "is_default": False
            },
            {
                "template_name": "IT Hardware & Laptop Tag (50 × 25 mm)",
                "width_mm": 50.0,
                "height_mm": 25.0,
                "code_type": "QR_CODE",
                "code_position": "RIGHT",
                "show_logo": True,
                "show_company_name": True,
                "field_visibility": {"sap_number": True, "description": True, "location": False},
                "font_settings": {"company_size": 7.5, "label_size": 6, "value_size": 6},
                "is_default": False
            },
            {
                "template_name": "Asset Micro-Tag (38 × 25 mm)",
                "width_mm": 38.0,
                "height_mm": 25.0,
                "code_type": "BARCODE",
                "code_position": "BOTTOM",
                "show_logo": False,
                "show_company_name": True,
                "field_visibility": {"sap_number": False, "description": True, "location": False},
                "font_settings": {"company_size": 7, "label_size": 5.5, "value_size": 5.5},
                "is_default": False
            },
            {
                "template_name": "Brother DK-11209 Standard (62 × 29 mm)",
                "width_mm": 62.0,
                "height_mm": 29.0,
                "code_type": "BARCODE",
                "code_position": "BOTTOM",
                "show_logo": True,
                "show_company_name": True,
                "field_visibility": {"sap_number": True, "description": True, "location": True},
                "font_settings": {"company_size": 8, "label_size": 6.5, "value_size": 6.5},
                "is_default": False
            },
            {
                "template_name": "DYMO 30252 Multi-Purpose (89 × 28 mm)",
                "width_mm": 89.0,
                "height_mm": 28.0,
                "code_type": "QR_CODE",
                "code_position": "RIGHT",
                "show_logo": True,
                "show_company_name": True,
                "field_visibility": {"sap_number": True, "description": True, "location": True},
                "font_settings": {"company_size": 8.5, "label_size": 7, "value_size": 7},
                "is_default": False
            }
        ]

        for tmpl in system_templates:
            existing = db.query(TagTemplate).filter(TagTemplate.template_name == tmpl["template_name"]).first()
            if not existing:
                db.add(TagTemplate(**tmpl))

        # 4. Standard Label Sizes Presets
        label_presets = [
            ("70 × 35 mm (Standard Corporate)", "CUSTOM", 70.0, 35.0, 3.0, "PORTRAIT", 300),
            ("60 × 30 mm (Compact Asset Tag)", "CUSTOM", 60.0, 30.0, 3.0, "PORTRAIT", 300),
            ("50 × 25 mm (Small Equipment)", "CUSTOM", 50.0, 25.0, 2.0, "PORTRAIT", 300),
            ("38 × 25 mm (Mini Tag)", "CUSTOM", 38.0, 25.0, 2.0, "PORTRAIT", 300),
            ("100 × 50 mm (Industrial Large)", "ZEBRA", 100.0, 50.0, 3.0, "PORTRAIT", 300),
            ("100 × 75 mm (Pallet / Stock Rack)", "ZEBRA", 100.0, 75.0, 3.0, "PORTRAIT", 300),
            ("Brother DK-11209 (62 × 29 mm)", "BROTHER", 62.0, 29.0, 3.0, "PORTRAIT", 300),
            ("DYMO 30252 (89 × 28 mm)", "DYMO", 89.0, 28.0, 3.0, "PORTRAIT", 300),
            ("TSC Standard (75 × 50 mm)", "TSC", 75.0, 50.0, 3.0, "PORTRAIT", 300),
        ]

        for name, cat, w, h, gap, orient, dpi in label_presets:
            existing_size = db.query(LabelSize).filter(LabelSize.name == name).first()
            if not existing_size:
                db.add(LabelSize(
                    name=name,
                    category=cat,
                    width_mm=w,
                    height_mm=h,
                    gap_mm=gap,
                    orientation=orient,
                    dpi=dpi,
                    is_preset=True
                ))

        # 5. Clean Demo Assets for TATA and Reliance
        sample_assets = [
            {
                "company_id": tata.id,
                "asset_id": "TATA-000001",
                "asset_type": "FIXED_ASSET",
                "description": "SERVER DELL POWEREDGE R750",
                "location": "MUM-DC-BAY-12",
                "sap_number": "41009821-0",
                "serial_number": "PE-89104",
                "department": "Cloud Infrastructure",
                "cost_centre": "CC-TATA-101",
                "custodian": "Sunil Mehta",
                "purchase_date": "2024-06-15",
                "code_type": "BARCODE",
                "status": "PRINTED",
                "print_count": 1,
                "created_by": admin_user.id
            },
            {
                "company_id": tata.id,
                "asset_id": "TATA-000002",
                "asset_type": "FIXED_ASSET",
                "description": "CISCO CATALYST 9300 SWITCH",
                "location": "MUM-DC-RACK-04",
                "sap_number": "41009821-1",
                "serial_number": "CS-44109",
                "department": "Network Engineering",
                "cost_centre": "CC-TATA-102",
                "custodian": "Priya Sharma",
                "purchase_date": "2024-07-20",
                "code_type": "QR_CODE",
                "status": "GENERATED",
                "print_count": 0,
                "created_by": admin_user.id
            },
            {
                "company_id": tata.id,
                "asset_id": "TATA-000003",
                "asset_type": "STOCK",
                "description": "FIBER OPTIC PATCH CABLE 10M",
                "location": "WH-STORE-B2",
                "sap_number": "10048201",
                "serial_number": "LOT-2025-FIBER",
                "department": "Inventory Management",
                "cost_centre": "CC-TATA-105",
                "custodian": "Rajiv Nambiar",
                "purchase_date": "2025-01-10",
                "code_type": "BARCODE",
                "status": "PRINTED",
                "print_count": 1,
                "created_by": std_user.id
            },
            {
                "company_id": reliance.id,
                "asset_id": "RIL-000001",
                "asset_type": "FIXED_ASSET",
                "description": "HIGH PRESSURE REFINERY VALVE 400A",
                "location": "JAM-REFINERY-UNIT-3",
                "sap_number": "92004510-0",
                "serial_number": "RV-992140",
                "department": "Petrochemical Maintenance",
                "cost_centre": "CC-RIL-401",
                "custodian": "Amit Patel",
                "purchase_date": "2024-04-10",
                "code_type": "BARCODE",
                "status": "PRINTED",
                "print_count": 1,
                "created_by": admin_user.id
            },
            {
                "company_id": reliance.id,
                "asset_id": "RIL-000002",
                "asset_type": "FIXED_ASSET",
                "description": "5G BASEBAND PROCESSING UNIT",
                "location": "JIO-NOC-NAVIMUMBAI",
                "sap_number": "92004510-1",
                "serial_number": "BBU-5G-8812",
                "department": "Telecom & 5G Rollout",
                "cost_centre": "CC-RIL-502",
                "custodian": "Kavita Nair",
                "purchase_date": "2024-08-01",
                "code_type": "QR_CODE",
                "status": "GENERATED",
                "print_count": 0,
                "created_by": admin_user.id
            },
            {
                "company_id": reliance.id,
                "asset_id": "RIL-000003",
                "asset_type": "STOCK",
                "description": "POLYMERIC CATALYST DRUMS (200L)",
                "location": "HAZ-STORAGE-BAY-7",
                "sap_number": "10099412",
                "serial_number": "BATCH-2025-CAT",
                "department": "Raw Materials",
                "cost_centre": "CC-RIL-201",
                "custodian": "Vikas Deshmukh",
                "purchase_date": "2025-02-15",
                "code_type": "BARCODE",
                "status": "GENERATED",
                "print_count": 0,
                "created_by": std_user.id
            }
        ]

        for s_ast in sample_assets:
            exists = db.query(Asset).filter(
                Asset.company_id == s_ast["company_id"],
                Asset.asset_id == s_ast["asset_id"]
            ).first()
            if not exists:
                db.add(Asset(**s_ast))

        # 6. System Settings
        settings = db.query(SystemSettings).first()
        if not settings:
            db.add(SystemSettings(
                default_company_id=tata.id,
                default_asset_type="FIXED_ASSET",
                default_code_type="BARCODE",
                default_page_size="A4",
                default_export_format="EXCEL",
                app_name="Asset Tagging & Label Management System"
            ))
        else:
            settings.default_company_id = tata.id

        db.commit()
        print("Database reseeded with TATA and Reliance companies successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database(reset_data=True)
