from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BranchCreate(BaseModel):
    code: str
    name: str
    address: Optional[str] = None
    opening_cash_balance: float = 0.0
    is_base_kitchen: bool = False
    is_active: bool = True
    contact_details: Optional[str] = None

class BranchUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    opening_cash_balance: Optional[float] = None
    is_base_kitchen: Optional[bool] = None
    is_active: Optional[bool] = None
    contact_details: Optional[str] = None

class BranchSchema(BranchCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
