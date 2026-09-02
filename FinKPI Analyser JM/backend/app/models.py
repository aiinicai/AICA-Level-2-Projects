import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Boolean, Index, Text
)
from sqlalchemy.orm import relationship
from .database import Base

class UserModel(Base):
    __tablename__ = "users"

    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username      = Column(String(50), unique=True, nullable=False, index=True)
    email         = Column(String(200))
    password_hash = Column(String(200), nullable=False)
    role          = Column(String(20), default="analyst")  # admin, analyst, viewer
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

class CompanyModel(Base):
    __tablename__ = "companies"

    id                 = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_code       = Column(String(20), unique=True, nullable=False, index=True)
    company_name       = Column(String(200), nullable=False)
    industry           = Column(String(100), default="Manufacturing")
    currency           = Column(String(10), default="INR")
    currency_unit      = Column(String(20), default="thousands")
    fiscal_year_start  = Column(Integer, default=1)  # 1 = Jan, 4 = Apr
    shares_outstanding = Column(Float, default=1000000.0)
    headcount          = Column(Integer, default=500)
    created_at         = Column(DateTime, default=datetime.utcnow)

    trial_balances     = relationship("TrialBalanceModel", back_populates="company", cascade="all, delete-orphan")
    statements         = relationship("FinancialStatementModel", back_populates="company", cascade="all, delete-orphan")

class TrialBalanceModel(Base):
    __tablename__ = "trial_balance"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id      = Column(String(36), ForeignKey("companies.id"), nullable=False)
    fiscal_year     = Column(String(10), nullable=False)   # FY2023, FY2024
    quarter         = Column(String(10), nullable=False)   # Q1, Q2, Q3, Q4, Annual
    period_id       = Column(String(10))                   # P01..P10
    period_sequence = Column(Integer)                      # 1..8, 0 for annual
    account_code    = Column(String(20), nullable=False)
    account_name    = Column(String(200), nullable=False)
    category        = Column(String(50))
    sub_category    = Column(String(100))
    account_type    = Column(String(20), nullable=False)   # Asset, Liability, Equity, Revenue, Expense
    normal_balance  = Column(String(10), default="Debit")  # Debit, Credit
    debit_amount    = Column(Float, default=0.0)
    credit_amount   = Column(Float, default=0.0)
    net_balance     = Column(Float, nullable=False)        # Debit - Credit
    uploaded_at     = Column(DateTime, default=datetime.utcnow)

    company         = relationship("CompanyModel", back_populates="trial_balances")

    __table_args__ = (
        Index("ix_tb_company_period", "company_id", "fiscal_year", "quarter"),
        Index("ix_tb_type", "company_id", "fiscal_year", "quarter", "account_type"),
    )

class FinancialStatementModel(Base):
    __tablename__ = "financial_statements"

    id             = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id     = Column(String(36), ForeignKey("companies.id"), nullable=False)
    fiscal_year    = Column(String(10), nullable=False)
    quarter        = Column(String(10), nullable=False)
    statement_type = Column(String(30), nullable=False)   # income_statement, balance_sheet, cash_flow
    payload_json   = Column(Text, nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)

    company        = relationship("CompanyModel", back_populates="statements")
