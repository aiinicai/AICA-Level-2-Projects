import io
from typing import List, Dict, Any, Tuple
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session
from ..models import Company, Asset

EXCEL_COLUMNS = [
    ("Company", "Company short name or full name (e.g. TATA or Reliance)", True),
    ("Asset Type", "FIXED_ASSET or STOCK", True),
    ("Asset ID", "Unique Asset ID (leave blank to auto-generate)", False),
    ("SAP No", "SAP Master Asset Number (e.g. 36007672-0)", False),
    ("Description", "Asset Item Description (e.g. WEIG-MCHN)", True),
    ("Location", "Physical Location / Sub-location (e.g. MCP)", False),
    ("Serial Number", "Manufacturer Serial Number", False),
    ("Department", "Department (e.g. Production / Quality)", False),
    ("Cost Centre", "Cost Centre code", False),
    ("Custodian", "User / Responsible Person", False),
    ("Purchase Date", "YYYY-MM-DD or DD/MM/YYYY", False),
    ("Code Type", "BARCODE or QR_CODE", False)
]

def generate_excel_template() -> io.BytesIO:
    """
    Generates a beautifully styled corporate Excel template for bulk asset upload.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Asset Upload Template"

    # Theme colors
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark Blue
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    # Write Headers
    for col_num, (col_name, _, is_required) in enumerate(EXCEL_COLUMNS, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = f"{col_name} *" if is_required else col_name
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    # Sample rows for demonstration
    sample_data = [
        ("TATA", "FIXED_ASSET", "TATA-900001", "36007672-0", "WEIG-MCHN", "MCP", "SN-98231", "Production", "CC-4010", "Rajesh Kumar", "2024-03-15", "BARCODE"),
        ("TATA", "FIXED_ASSET", "TATA-900002", "36007672-1", "CENTRIFUGE-PRO", "LAB-2", "SN-54122", "Quality Control", "CC-4020", "Dr. Anita Rao", "2024-04-10", "QR_CODE"),
        ("Reliance", "STOCK", "RIL-900101", "10024951", "FILTER-MEMBRANE 0.2U", "WH-BAY-4", "BATCH-2025-A", "Warehouse", "CC-1050", "Store Manager", "2025-01-20", "BARCODE"),
    ]

    for row_idx, row_data in enumerate(sample_data, 2):
        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = val
            cell.font = Font(name="Arial", size=10)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")

    # Add Instructions tab
    ws_info = wb.create_sheet(title="Instructions")
    ws_info.cell(row=1, column=1, value="Bulk Asset Upload Guidelines").font = Font(size=14, bold=True, color="1E3A8A")
    instructions = [
        "1. Columns marked with an asterisk (*) are mandatory.",
        "2. Asset ID: If left blank, the system will automatically allocate the next sequence ID for the company.",
        "3. Asset Type: Supported values are 'FIXED_ASSET' or 'STOCK' (or 'Fixed Asset' / 'Stock').",
        "4. Code Type: Supported values are 'BARCODE' or 'QR_CODE' (defaults to BARCODE).",
        "5. Duplicate Prevention: If an Asset ID already exists, the upload validation screen will highlight it and request an override reason before generation.",
        "6. Maximum recommended records per single batch: 2,000 items."
    ]
    for idx, inst in enumerate(instructions, 3):
        ws_info.cell(row=idx, column=1, value=inst).font = Font(name="Arial", size=10)

    # Adjust column widths
    for sheet in [ws, ws_info]:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 14)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def parse_and_validate_excel(file_contents: bytes, db: Session) -> Dict[str, Any]:
    """
    Parses an uploaded Excel file and performs multi-stage duplicate & schema validation.
    """
    wb = openpyxl.load_workbook(filename=io.BytesIO(file_contents), data_only=True)
    ws = wb.active

    # Load active companies into lookup dict
    companies = db.query(Company).all()
    company_by_name = {c.name.strip().lower(): c for c in companies}
    company_by_short = {c.short_name.strip().lower(): c for c in companies}
    default_company = companies[0] if companies else None

    # Find headers
    headers = [str(cell.value or "").strip().lower().replace("*", "").strip() for cell in ws[1]]
    
    rows_result = []
    seen_in_batch = set()

    total_count = 0
    valid_count = 0
    duplicate_count = 0
    missing_fields_count = 0
    invalid_format_count = 0

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # Ignore completely empty rows
        if not any(row):
            continue

        total_count += 1
        row_dict = {}
        for h_idx, h_name in enumerate(headers):
            if h_idx < len(row):
                row_dict[h_name] = row[h_idx]

        company_raw = str(row_dict.get("company", "") or "").strip()
        asset_type_raw = str(row_dict.get("asset type", "") or "FIXED_ASSET").strip()
        asset_id_raw = str(row_dict.get("asset id", "") or "").strip()
        sap_no_raw = str(row_dict.get("sap no", "") or row_dict.get("sap number", "") or "").strip()
        description_raw = str(row_dict.get("description", "") or "").strip()
        location_raw = str(row_dict.get("location", "") or "").strip()
        serial_no_raw = str(row_dict.get("serial number", "") or "").strip()
        dept_raw = str(row_dict.get("department", "") or "").strip()
        cost_centre_raw = str(row_dict.get("cost centre", "") or row_dict.get("cost center", "") or "").strip()
        custodian_raw = str(row_dict.get("custodian", "") or "").strip()
        purchase_date_raw = str(row_dict.get("purchase date", "") or "").strip()
        code_type_raw = str(row_dict.get("code type", "") or "BARCODE").strip().upper()

        # Match company
        target_company = None
        if company_raw:
            target_company = company_by_name.get(company_raw.lower()) or company_by_short.get(company_raw.lower())
        if not target_company and default_company:
            target_company = default_company

        # Normalize asset type
        normalized_type = "FIXED_ASSET"
        if "stock" in asset_type_raw.lower() or "inv" in asset_type_raw.lower():
            normalized_type = "STOCK"

        # Normalize code type
        if "qr" in code_type_raw.lower():
            code_type_raw = "QR_CODE"
        else:
            code_type_raw = "BARCODE"

        # Check validation status
        status = "VALID"
        error_msg = None
        existing_info = None

        if not target_company:
            status = "MISSING_REQUIRED"
            error_msg = "Company not found and no default company configured"
            missing_fields_count += 1
        elif not description_raw:
            status = "MISSING_REQUIRED"
            error_msg = "Asset Description is mandatory"
            missing_fields_count += 1
        elif asset_id_raw:
            # Check duplicate in batch
            batch_key = (target_company.id, asset_id_raw)
            if batch_key in seen_in_batch:
                status = "DUPLICATE_BATCH"
                error_msg = f"Duplicate Asset ID '{asset_id_raw}' repeated within this Excel file"
                duplicate_count += 1
            else:
                seen_in_batch.add(batch_key)
                # Check duplicate in database
                existing_asset = db.query(Asset).filter(
                    Asset.company_id == target_company.id,
                    Asset.asset_id == asset_id_raw
                ).first()

                if existing_asset:
                    status = "DUPLICATE_DB"
                    error_msg = f"Asset ID '{asset_id_raw}' already exists in database for company '{target_company.name}'"
                    duplicate_count += 1
                    existing_info = {
                        "id": existing_asset.id,
                        "asset_id": existing_asset.asset_id,
                        "company_name": target_company.name,
                        "description": existing_asset.description,
                        "asset_type": existing_asset.asset_type,
                        "created_at": existing_asset.created_at.strftime("%Y-%m-%d %H:%M"),
                        "created_by": existing_asset.creator.full_name if existing_asset.creator else "System"
                    }

        if status == "VALID":
            valid_count += 1

        rows_result.append({
            "row_number": row_idx,
            "company_name": target_company.name if target_company else company_raw,
            "company_id": target_company.id if target_company else None,
            "asset_id": asset_id_raw or None,
            "asset_type": normalized_type,
            "sap_number": sap_no_raw or None,
            "description": description_raw,
            "location": location_raw or None,
            "serial_number": serial_no_raw or None,
            "department": dept_raw or None,
            "cost_centre": cost_centre_raw or None,
            "custodian": custodian_raw or None,
            "purchase_date": purchase_date_raw or None,
            "code_type": code_type_raw,
            "status": status,
            "error_message": error_msg,
            "existing_record": existing_info,
            "override_reason": None
        })

    return {
        "total_rows": total_count,
        "valid_count": valid_count,
        "duplicate_count": duplicate_count,
        "missing_fields_count": missing_fields_count,
        "invalid_format_count": invalid_format_count,
        "rows": rows_result
    }

def export_assets_to_excel(assets: List[Asset]) -> io.BytesIO:
    """
    Exports asset records to a formatted Excel file.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Asset Register"

    headers = [
        "Asset ID", "Company", "Asset Type", "Description", "Location",
        "SAP No", "Serial No", "Department", "Cost Centre", "Custodian",
        "Purchase Date", "Code Type", "Status", "Print Count", "Duplicate Override",
        "Override Reason", "Created By", "Created Date"
    ]

    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")

    for col_num, h_title in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = h_title
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )

    for row_idx, ast in enumerate(assets, 2):
        row_values = [
            ast.asset_id,
            ast.company.name if ast.company else "N/A",
            ast.asset_type,
            ast.description,
            ast.location or "",
            ast.sap_number or "",
            ast.serial_number or "",
            ast.department or "",
            ast.cost_centre or "",
            ast.custodian or "",
            ast.purchase_date or "",
            ast.code_type,
            ast.status,
            ast.print_count,
            "Yes" if ast.is_override else "No",
            ast.override_reason or "",
            ast.creator.full_name if ast.creator else "System",
            ast.created_at.strftime("%Y-%m-%d %H:%M:%S") if ast.created_at else ""
        ]
        for col_idx, val in enumerate(row_values, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = val
            cell.font = Font(name="Arial", size=9)
            cell.border = thin_border

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
