# ============================================================
# FILE: app.py
# PROJECT: FinKPI Analyzer - Complete Single File Application
# INSTALL: pip install fastapi uvicorn sqlalchemy pandas openpyxl
#          python-jose passlib python-multipart numpy pydantic-settings
#          aiofiles jinja2
# RUN:     python app.py
# URL:     http://localhost:8000
# DOCS:    http://localhost:8000/docs
# ============================================================

# ─────────────────────────────────────────────────────────────
# SECTION 1: IMPORTS
# ─────────────────────────────────────────────────────────────
import os
import sys
import json
import uuid
import math
import warnings
import uvicorn
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

warnings.filterwarnings("ignore")

from fastapi import (
    FastAPI, HTTPException, Depends, UploadFile,
    File, Form, status, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import JWTError, jwt
from passlib.context import CryptContext

from sqlalchemy import (
    create_engine, Column, String, Float,
    Integer, DateTime, ForeignKey, Boolean, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────
# SECTION 2: CONFIGURATION
# ─────────────────────────────────────────────────────────────
class Config:
    APP_NAME         = "FinKPI Analyzer"
    APP_VERSION      = "1.0.0"
    DATABASE_URL     = "sqlite:///./finkpi.db"
    SECRET_KEY       = "finkpi-secret-key-2024-change-in-production"
    ALGORITHM        = "HS256"
    TOKEN_EXPIRE_MIN = 1440
    DEMO_USER        = "admin"
    DEMO_PASSWORD    = "admin123"

    REQUIRED_SHEETS = [
        "TB_Q1_FY2023","TB_Q2_FY2023","TB_Q3_FY2023","TB_Q4_FY2023",
        "TB_Annual_FY2023",
        "TB_Q1_FY2024","TB_Q2_FY2024","TB_Q3_FY2024","TB_Q4_FY2024",
        "TB_Annual_FY2024"
    ]

    BENCHMARKS = {
        "gross_profit_margin"  : 38.0,
        "net_profit_margin"    : 12.0,
        "ebitda_margin"        : 18.0,
        "operating_margin"     : 14.0,
        "roa"                  : 8.0,
        "roe"                  : 15.0,
        "roce"                 : 12.0,
        "current_ratio"        : 1.5,
        "quick_ratio"          : 1.0,
        "cash_ratio"           : 0.5,
        "debt_to_equity"       : 1.0,
        "debt_to_assets"       : 0.5,
        "interest_coverage"    : 3.0,
        "net_debt_to_ebitda"   : 2.5,
        "asset_turnover"       : 0.8,
        "inventory_turnover"   : 5.0,
        "receivables_turnover" : 8.0,
        "dso"                  : 45.0,
        "dpo"                  : 35.0,
        "ccc"                  : 55.0,
    }

config = Config()

# ─────────────────────────────────────────────────────────────
# SECTION 3: DATABASE
# ─────────────────────────────────────────────────────────────
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────
# SECTION 4: MODELS
# ─────────────────────────────────────────────────────────────
class UserModel(Base):
    __tablename__ = "users"
    id            = Column(String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    username      = Column(String(50), unique=True, nullable=False, index=True)
    email         = Column(String(200))
    password_hash = Column(String(200), nullable=False)
    role          = Column(String(20), default="analyst")
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

class CompanyModel(Base):
    __tablename__       = "companies"
    id                  = Column(String(36), primary_key=True,
                                 default=lambda: str(uuid.uuid4()))
    company_code        = Column(String(20), unique=True,
                                 nullable=False, index=True)
    company_name        = Column(String(200), nullable=False)
    industry            = Column(String(100))
    currency            = Column(String(10), default="USD")
    currency_unit       = Column(String(20), default="thousands")
    fiscal_year_start   = Column(Integer, default=1)
    shares_outstanding  = Column(Float, default=0)
    is_active           = Column(Boolean, default=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    trial_balances      = relationship(
        "TrialBalanceModel",
        back_populates="company",
        cascade="all, delete-orphan"
    )

class TrialBalanceModel(Base):
    __tablename__    = "trial_balance"
    id               = Column(String(36), primary_key=True,
                              default=lambda: str(uuid.uuid4()))
    company_id       = Column(String(36), ForeignKey("companies.id"),
                              nullable=False)
    fiscal_year      = Column(String(10), nullable=False)
    quarter          = Column(String(10), nullable=False)
    period_id        = Column(String(10))
    period_sequence  = Column(Integer)
    account_code     = Column(String(20), nullable=False)
    account_name     = Column(String(200), nullable=False)
    category         = Column(String(50))
    sub_category     = Column(String(100))
    account_type     = Column(String(20), nullable=False)
    amount           = Column(Float, nullable=False)  # + Debit | - Credit
    uploaded_at      = Column(DateTime, default=datetime.utcnow)
    company          = relationship("CompanyModel", back_populates="trial_balances")

    __table_args__ = (
        Index("ix_tb_main", "company_id", "fiscal_year", "quarter"),
        Index("ix_tb_type", "company_id", "fiscal_year", "quarter", "account_type"),
    )

# ─────────────────────────────────────────────────────────────
# SECTION 5: SCHEMAS
# ─────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class CompanyCreate(BaseModel):
    company_code       : str
    company_name       : str
    industry           : Optional[str] = "Manufacturing"
    currency           : Optional[str] = "USD"
    currency_unit      : Optional[str] = "thousands"
    shares_outstanding : Optional[float] = 0

class APIResponse(BaseModel):
    success    : bool = True
    statusCode : int  = 200
    message    : str  = "Success"
    data       : Any  = None
    meta       : Optional[Dict] = None

# ─────────────────────────────────────────────────────────────
# SECTION 6: AUTH HELPERS
# ─────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
http_bearer = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: Dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(
        minutes=config.TOKEN_EXPIRE_MIN
    )
    return jwt.encode(payload, config.SECRET_KEY,
                      algorithm=config.ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: Session = Depends(get_db)
):
    try:
        payload  = jwt.decode(
            credentials.credentials,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM]
        )
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    user = db.query(UserModel).filter(
        UserModel.username == username
    ).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ─────────────────────────────────────────────────────────────
# SECTION 7: EXCEL PARSER
# ─────────────────────────────────────────────────────────────
SHEET_MAP = {
    "TB_Q1_FY2023":     ("Q1",     "FY2023", "P01", 1),
    "TB_Q2_FY2023":     ("Q2",     "FY2023", "P02", 2),
    "TB_Q3_FY2023":     ("Q3",     "FY2023", "P03", 3),
    "TB_Q4_FY2023":     ("Q4",     "FY2023", "P04", 4),
    "TB_Annual_FY2023": ("Annual", "FY2023", "P05", 0),
    "TB_Q1_FY2024":     ("Q1",     "FY2024", "P06", 5),
    "TB_Q2_FY2024":     ("Q2",     "FY2024", "P07", 6),
    "TB_Q3_FY2024":     ("Q3",     "FY2024", "P08", 7),
    "TB_Q4_FY2024":     ("Q4",     "FY2024", "P09", 8),
    "TB_Annual_FY2024": ("Annual", "FY2024", "P10", 0),
}

def parse_excel_file(file_bytes: bytes) -> Dict:
    """Parse 10-sheet Excel Trial Balance. Amount: + = Debit | - = Credit"""
    try:
        xl = pd.ExcelFile(BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Cannot read Excel file: {e}")

    missing = [s for s in config.REQUIRED_SHEETS if s not in xl.sheet_names]
    if missing:
        raise ValueError(f"Missing sheets: {missing}")

    all_records = []
    val_report  = {}
    errors      = []

    for sheet in config.REQUIRED_SHEETS:
        try:
            df = xl.parse(sheet)
            df.columns = [
                str(c).strip().replace(" ", "_").replace("-", "_")
                for c in df.columns
            ]

            needed = [
                "Account_Code","Account_Name","Category",
                "Sub_Category","Account_Type","Amount"
            ]
            miss_cols = [c for c in needed if c not in df.columns]
            if miss_cols:
                errors.append(f"{sheet}: Missing columns {miss_cols}")
                continue

            df = df.dropna(subset=["Account_Code", "Account_Name"])
            df["Amount"]       = pd.to_numeric(df["Amount"], errors="coerce")
            df = df.dropna(subset=["Amount"])
            df["Account_Code"] = df["Account_Code"].astype(str).str.strip()
            df["Account_Name"] = df["Account_Name"].astype(str).str.strip()
            df["Account_Type"] = df["Account_Type"].astype(str).str.strip()
            df["Category"]     = df["Category"].astype(str).str.strip()
            df["Sub_Category"] = df["Sub_Category"].astype(str).str.strip()

            total      = round(float(df["Amount"].sum()), 2)
            balanced   = abs(total) < 10.0
            q, fy, pid, seq = SHEET_MAP[sheet]

            val_report[sheet] = {
                "rows"       : len(df),
                "sum_amount" : total,
                "is_balanced": balanced,
            }

            for _, row in df.iterrows():
                all_records.append({
                    "account_code"   : str(row["Account_Code"]).strip(),
                    "account_name"   : str(row["Account_Name"]).strip(),
                    "category"       : str(row.get("Category", "")).strip(),
                    "sub_category"   : str(row.get("Sub_Category", "")).strip(),
                    "account_type"   : str(row.get("Account_Type", "")).strip(),
                    "amount"         : float(row["Amount"]),
                    "quarter"        : q,
                    "fiscal_year"    : fy,
                    "period_id"      : pid,
                    "period_sequence": seq,
                })

        except Exception as e:
            errors.append(f"{sheet}: Error — {e}")

    return {
        "records"          : all_records,
        "validation_report": val_report,
        "errors"           : errors,
        "total_records"    : len(all_records),
        "periods_detected" : len(val_report),
    }

# ─────────────────────────────────────────────────────────────
# SECTION 8: FINANCIAL ENGINE
# ─────────────────────────────────────────────────────────────
def safe_div(num: float, den: float, default: float = 0.0) -> float:
    if den == 0 or den is None:
        return default
    try:
        r = num / den
        return round(r, 4) if not math.isnan(r) else default
    except Exception:
        return default

def get_rag(kpi_name: str, value: float) -> str:
    bm = config.BENCHMARKS.get(kpi_name)
    if bm is None:
        return "GREY"
    higher_better = {
        "gross_profit_margin","net_profit_margin","ebitda_margin",
        "operating_margin","roa","roe","roce","current_ratio",
        "quick_ratio","cash_ratio","interest_coverage",
        "asset_turnover","inventory_turnover","receivables_turnover"
    }
    lower_better = {
        "debt_to_equity","debt_to_assets",
        "net_debt_to_ebitda","dso","ccc"
    }
    if kpi_name in higher_better:
        if value >= bm * 1.05: return "GREEN"
        if value >= bm * 0.85: return "AMBER"
        return "RED"
    if kpi_name in lower_better:
        if value <= bm * 0.95: return "GREEN"
        if value <= bm * 1.15: return "AMBER"
        return "RED"
    return "GREY"

class FinancialEngine:
    """
    Builds financial statements from trial balance records.
    SINGLE AMOUNT COLUMN RULE: + = Debit | - = Credit
    """

    def __init__(self, records: List[Dict]):
        self.df = pd.DataFrame(records) if records else pd.DataFrame()
        if not self.df.empty:
            self.df["amount"] = pd.to_numeric(
                self.df["amount"], errors="coerce"
            ).fillna(0)

    # ── Helpers ───────────────────────────────────────────────
    def _period_df(self, q: str, fy: str) -> pd.DataFrame:
        if self.df.empty:
            return pd.DataFrame()
        return self.df[
            (self.df["quarter"] == q) &
            (self.df["fiscal_year"] == fy)
        ].copy()

    def _sub_sum(
        self, df: pd.DataFrame,
        acct_type: str, keyword: str
    ) -> float:
        if df.empty:
            return 0.0
        mask = (
            (df["account_type"] == acct_type) &
            (df["sub_category"].str.contains(
                keyword, case=False, na=False
            ))
        )
        return float(df[mask]["amount"].sum())

    def _type_sum(self, df: pd.DataFrame, acct_type: str) -> float:
        if df.empty:
            return 0.0
        return float(df[df["account_type"] == acct_type]["amount"].sum())

    # ─────────────────────────────────────────────────────────
    # INCOME STATEMENT
    # ─────────────────────────────────────────────────────────
    def income_statement(self, q: str, fy: str) -> Dict:
        df = self._period_df(q, fy)
        if df.empty:
            return {}

        # ── Revenue (credits = negative → abs) ───────────────
        rev_df       = df[df["account_type"] == "Revenue"]
        returns_mask = rev_df["sub_category"].str.contains(
            "Return|Discount|Allowance|Rebate", case=False, na=False
        )

        gross_revenue = abs(float(rev_df[~returns_mask]["amount"].sum()))
        sales_returns = abs(float(rev_df[returns_mask]["amount"].sum()))
        net_revenue   = gross_revenue - sales_returns

        # ── COGS ──────────────────────────────────────────────
        cogs_mask     = (
            (df["account_type"] == "Expense") &
            (df["sub_category"].str.contains(
                "COGS|Cost of Good|Direct Cost|Manufacturing Cost",
                case=False, na=False
            ))
        )
        cogs_df       = df[cogs_mask]

        cogs_material    = float(cogs_df[
            cogs_df["sub_category"].str.contains(
                "Material|Raw Material", case=False, na=False
            )]["amount"].sum())

        cogs_labor       = float(cogs_df[
            cogs_df["sub_category"].str.contains(
                "Labor|Labour|Direct Labor|Direct Labour",
                case=False, na=False
            )]["amount"].sum())

        cogs_overhead    = float(cogs_df[
            cogs_df["sub_category"].str.contains(
                "Overhead|Mfg OH|Manufacturing OH",
                case=False, na=False
            )]["amount"].sum())

        cogs_depr        = float(cogs_df[
            cogs_df["sub_category"].str.contains(
                "Depr|Depreciation", case=False, na=False
            )]["amount"].sum())

        cogs_freight     = float(cogs_df[
            cogs_df["sub_category"].str.contains(
                "Freight|Shipping|Logistics|Transport",
                case=False, na=False
            )]["amount"].sum())

        cogs_warranty    = float(cogs_df[
            cogs_df["sub_category"].str.contains(
                "Warranty|Provision", case=False, na=False
            )]["amount"].sum())

        cogs_packaging   = float(cogs_df[
            cogs_df["sub_category"].str.contains(
                "Packaging|Package|Packing", case=False, na=False
            )]["amount"].sum())

        cogs_royalties   = float(cogs_df[
            cogs_df["sub_category"].str.contains(
                "Royalt|License Fee|Royalty", case=False, na=False
            )]["amount"].sum())

        # Everything else in COGS
        known_cogs_kw = (
            "Material|Raw Material|Labor|Labour|Overhead|Mfg OH|"
            "Depr|Depreciation|Freight|Shipping|Warranty|Packaging|Royalt"
        )
        cogs_other    = float(cogs_df[
            ~cogs_df["sub_category"].str.contains(
                known_cogs_kw, case=False, na=False
            )]["amount"].sum())

        total_cogs = (
            cogs_material + cogs_labor + cogs_overhead + cogs_depr +
            cogs_freight  + cogs_warranty + cogs_packaging +
            cogs_royalties + cogs_other
        )
        gross_profit = net_revenue - total_cogs

        # ── Operating Expenses ────────────────────────────────
        # Exclude COGS items from expense
        cogs_keywords = (
            "COGS|Cost of Good|Direct Cost|Manufacturing Cost"
        )
        opex_df = df[
            (df["account_type"] == "Expense") &
            (~df["sub_category"].str.contains(
                cogs_keywords, case=False, na=False
            )) &
            (~df["sub_category"].str.contains(
                "Interest|Tax|Non-Operating|Other Income",
                case=False, na=False
            ))
        ].copy()

        # Sales & Marketing
        sm_salaries  = float(opex_df[
            opex_df["sub_category"].str.contains(
                "Sales Salary|Sales Staff|Business Dev Salary",
                case=False, na=False
            )]["amount"].sum())

        sm_commission = float(opex_df[
            opex_df["sub_category"].str.contains(
                "Commission|Sales Commission", case=False, na=False
            )]["amount"].sum())

        sm_marketing  = float(opex_df[
            opex_df["sub_category"].str.contains(
                "Marketing|Digital Marketing|Content Marketing",
                case=False, na=False
            )]["amount"].sum())

        sm_advertising = float(opex_df[
            opex_df["sub_category"].str.contains(
                "Advertising|Ad Spend|Media Buy",
                case=False, na=False
            )]["amount"].sum())

        sm_travel     = float(opex_df[
            opex_df["sub_category"].str.contains(
                "Travel|Business Travel|Travel Expense",
                case=False, na=False
            )]["amount"].sum())
