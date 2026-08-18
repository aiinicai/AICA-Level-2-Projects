from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime

try:
    from .database import Base
except ImportError:
    from database import Base

class WPEntity(Base):
    __tablename__ = "wp_entities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    status = Column(String(20), default="Active")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class FDRecord(Base):
    __tablename__ = "fd_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_id = Column(Integer, nullable=False, index=True)
    financial_year = Column(String(20), nullable=False, index=True)
    
    bank_name = Column(String(100), nullable=False)
    fd_account_number = Column(String(50), nullable=False)
    principal_amount = Column(Float, default=0.0)
    date_of_issue = Column(String(30), nullable=False)  # YYYY-MM-DD
    date_of_maturity = Column(String(30), nullable=False)  # YYYY-MM-DD
    interest_rate = Column(Float, default=0.0)
    compounding_frequency = Column(String(30), default="Quarterly")
    opening_accrued_interest = Column(Float, default=0.0)
    tds_deducted = Column(Float, default=0.0)
    status = Column(String(20), default="Active")  # Active or Matured

    # Movement Schedule Fields
    opening_principal = Column(Float, default=0.0)
    created_principal = Column(Float, default=0.0)
    matured_principal = Column(Float, default=0.0)
    settled_accrued_interest = Column(Float, default=0.0)

    # Roll-Forward Tracking Fields
    is_roll_forward = Column(Boolean, default=False)
    py_record_id = Column(Integer, nullable=True)

    # Computed Statutory Fields
    original_maturity_days = Column(Integer, default=0)
    remaining_maturity_days = Column(Integer, default=0)
    interest_income = Column(Float, default=0.0)
    closing_accrued_interest = Column(Float, default=0.0)
    closing_principal = Column(Float, default=0.0)
    closing_total_balance = Column(Float, default=0.0)
    classification_class = Column(String(20), default="Class 2")  # Class 1, Class 2, Class 3
    classification_label = Column(String(100), default="Other Current Bank Balances")
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "financial_year": self.financial_year,
            "bank_name": self.bank_name,
            "fd_account_number": self.fd_account_number,
            "principal_amount": self.principal_amount,
            "date_of_issue": self.date_of_issue,
            "date_of_maturity": self.date_of_maturity,
            "interest_rate": self.interest_rate,
            "compounding_frequency": self.compounding_frequency,
            "opening_accrued_interest": self.opening_accrued_interest,
            "tds_deducted": self.tds_deducted,
            "status": self.status,
            "opening_principal": self.opening_principal,
            "created_principal": self.created_principal,
            "matured_principal": self.matured_principal,
            "settled_accrued_interest": self.settled_accrued_interest,
            "is_roll_forward": self.is_roll_forward,
            "py_record_id": self.py_record_id,
            "original_maturity_days": self.original_maturity_days,
            "remaining_maturity_days": self.remaining_maturity_days,
            "interest_income": self.interest_income,
            "closing_accrued_interest": self.closing_accrued_interest,
            "closing_principal": self.closing_principal,
            "closing_total_balance": self.closing_total_balance,
            "classification_class": self.classification_class,
            "classification_label": self.classification_label,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AS26Entry(Base):
    __tablename__ = "as26_entries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_id = Column(Integer, nullable=False, index=True)
    financial_year = Column(String(20), nullable=False, index=True)
    
    deductor_name = Column(String(150), nullable=False)
    tan = Column(String(30), nullable=False)
    section = Column(String(20), default="194A")
    amount_paid = Column(Float, default=0.0)
    tds_deducted = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "financial_year": self.financial_year,
            "deductor_name": self.deductor_name,
            "tan": self.tan,
            "section": self.section,
            "amount_paid": self.amount_paid,
            "tds_deducted": self.tds_deducted,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
