from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class CompanyCreate(BaseModel):
    company_code: str
    company_name: str
    industry: Optional[str] = "Manufacturing"
    currency: Optional[str] = "INR"
    currency_unit: Optional[str] = "thousands"
    fiscal_year_start: Optional[int] = 1
    shares_outstanding: Optional[float] = 1000000.0
    headcount: Optional[int] = 500

class CompanyResponse(BaseModel):
    id: str
    company_code: str
    company_name: str
    industry: Optional[str]
    currency: Optional[str]
    currency_unit: Optional[str]
    fiscal_year_start: int
    shares_outstanding: float
    headcount: int

class APIResponse(BaseModel):
    success: bool = True
    statusCode: int = 200
    message: str = "Success"
    data: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = None

class KPIValue(BaseModel):
    value: float
    unit: str
    qoq_delta: Optional[float] = None
    qoq_pct: Optional[float] = None
    yoy_delta: Optional[float] = None
    yoy_pct: Optional[float] = None
    trend_8Q: List[float] = []
    benchmark: Optional[float] = None
    status: Optional[str] = None
    rag_status: Optional[str] = None   # GREEN, AMBER, RED
    trend_dir: Optional[str] = None    # improving, declining, stable
