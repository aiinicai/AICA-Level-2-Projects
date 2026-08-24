from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date

class CashRecCreateUpdate(BaseModel):
    branch_id: int
    rec_date: date
    opening_balance: Optional[float] = None
    site_expenses_inv_rec: float = 0.0
    site_expenses_inv_not_rec: float = 0.0
    advance_salary_1_5: float = 0.0
    advance_salary_6_15: float = 0.0
    advance_salary_16_31: float = 0.0
    transfer_base_kitchen: float = 0.0
    service_charge: float = 0.0
    other_adjustments: float = 0.0
    actual_closing_balance: float = 0.0
    remarks: Optional[str] = None
    salary_advance_splits: Optional[List[Dict[str, Any]]] = None
    original_branch_id: Optional[int] = None
    original_rec_date: Optional[date] = None
