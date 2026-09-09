import pandas as pd
from io import BytesIO
from repositories import asset_repository, category_repository, settings_repository
from services import asset_service
from utils.validation import ValidationError
import database

def clean_date(val):
    """Ensures date values from Excel/CSV are converted to YYYY-MM-DD string."""
    if pd.isnull(val) or str(val).strip() == "":
        return None
    try:
        # Convert to pandas datetime then to string format YYYY-MM-DD
        return pd.to_datetime(val).strftime('%Y-%m-%d')
    except Exception:
        # If it's already a weird string, return it and let the service validation handle it
        return str(val).strip()

def get_import_template():
    """Generates a blank Excel template with headers."""
    columns = [
        "Asset Name", "Category Code", "Purchase Date (YYYY-MM-DD)", 
        "Date Put to Use (YYYY-MM-DD)", "Original Cost", "Opening Accum Dep", 
        "Residual Value", "Useful Life (Years)", "Companies Act Method (SLM/WDV)", 
        "Companies Act Rate % (WDV)", "Income Tax Block Code", "Department", "Location"
    ]
    df = pd.DataFrame(columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    return output.getvalue()

def bulk_import_assets(conn, file_path):
    """Reads Excel/CSV and imports assets."""
    # Read the file
    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)
    
    # Pre-fetch mappings
    categories = {c['category_code']: c['category_id'] for c in category_repository.list_categories(conn, active_only=True)}
    blocks = {b['block_code']: b['block_id'] for b in settings_repository.list_tax_blocks(conn, active_only=True)}
    
    import_count = 0
    errors = []

    for index, row in df.iterrows():
        try:
            # 1. Map Codes to IDs
            cat_code = str(row['Category Code']).strip().upper()
            block_code = str(row['Income Tax Block Code']).strip().upper()
            
            if cat_code not in categories:
                raise ValidationError(f"Category Code '{cat_code}' not found.")
            if block_code not in blocks:
                raise ValidationError(f"IT Block Code '{block_code}' not found.")

            # 2. Prepare Data Dictionary with Cleaned Dates
            asset_data = {
                "asset_name": str(row['Asset Name']),
                "category_id": categories[cat_code],
                "purchase_date": clean_date(row['Purchase Date (YYYY-MM-DD)']),
                "date_put_to_use": clean_date(row['Date Put to Use (YYYY-MM-DD)']),
                "original_cost": row['Original Cost'],
                "opening_accum_dep": row['Opening Accum Dep'] if pd.notnull(row['Opening Accum Dep']) else 0,
                "residual_value": row['Residual Value'] if pd.notnull(row['Residual Value']) else 0,
                "useful_life_years": row['Useful Life (Years)'],
                "companies_act_method": str(row['Companies Act Method (SLM/WDV)']).upper().strip(),
                "companies_act_rate": row['Companies Act Rate % (WDV)'] if pd.notnull(row['Companies Act Rate % (WDV)']) else None,
                "income_tax_block_id": blocks[block_code],
                "department": str(row['Department']) if pd.notnull(row['Department']) else "",
                "location": str(row['Location']) if pd.notnull(row['Location']) else "",
            }

            # 3. Create Asset
            asset_service.create_asset(conn, asset_data)
            import_count += 1
            
        except Exception as e:
            errors.append(f"Row {index + 2}: {str(e)}")

    return import_count, errors