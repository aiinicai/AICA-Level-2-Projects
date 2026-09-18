from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import Company, Asset

def generate_next_asset_id(db: Session, company_id: int) -> str:
    """
    Atomically generates the next unique Asset ID for a given company.
    Uses database row update with optimistic/pessimistic sequencing.
    """
    company = db.query(Company).filter(Company.id == company_id).with_for_update().first()
    if not company:
        raise ValueError(f"Company ID {company_id} not found")

    prefix = company.asset_id_prefix or "FA"
    format_str = company.numbering_format or "{PREFIX}-{NUM:6}"
    current_num = max(company.current_number or 0, (company.starting_number or 1) - 1)

    now = datetime.now()
    year_str = str(now.year)
    short_year = str(now.year)[2:]

    # Find the next free number that does not collide with an existing asset
    while True:
        current_num += 1
        num_str_6 = f"{current_num:06d}"
        num_str_5 = f"{current_num:05d}"
        num_str_4 = f"{current_num:04d}"
        num_str = str(current_num)

        # Render format
        rendered_id = format_str.replace("{PREFIX}", prefix)\
                                .replace("{COMPANY}", company.short_name or prefix)\
                                .replace("{YEAR}", year_str)\
                                .replace("{YY}", short_year)\
                                .replace("{NUM:6}", num_str_6)\
                                .replace("{NUM:5}", num_str_5)\
                                .replace("{NUM:4}", num_str_4)\
                                .replace("{NUM}", num_str)

        # Fallback if standard format didn't have placeholders
        if rendered_id == format_str:
            rendered_id = f"{prefix}-{num_str_6}"

        # Check if this ID already exists in this company
        exists = db.query(Asset.id).filter(
            Asset.company_id == company_id,
            Asset.asset_id == rendered_id
        ).first()

        if not exists:
            company.current_number = current_num
            db.commit()
            return rendered_id
