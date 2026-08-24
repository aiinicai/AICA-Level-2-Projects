from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class CashTransaction(Base):
    __tablename__ = "cash_transactions"

    id = Column(Integer, primary_key=True, index=True)
    cash_reconciliation_id = Column(Integer, ForeignKey("cash_reconciliations.id"), nullable=False)
    category = Column(String(50), nullable=False) # EXPENSE_INV_REC, EXPENSE_INV_NOT_REC, SALARY_ADV_1_5, SALARY_ADV_6_15, SALARY_ADV_16_31, BASE_KITCHEN_TRANSFER, SERVICE_CHARGE, OTHER
    amount = Column(Float, nullable=False, default=0.0)
    description = Column(String(255), nullable=True)
    voucher_no = Column(String(50), nullable=True)

class CashReconciliation(Base):
    __tablename__ = "cash_reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    rec_date = Column(Date, nullable=False, index=True)

    opening_balance = Column(Float, default=0.0)
    cash_sale = Column(Float, default=0.0)
    site_expenses_inv_rec = Column(Float, default=0.0)
    site_expenses_inv_not_rec = Column(Float, default=0.0)
    advance_salary_1_5 = Column(Float, default=0.0)
    advance_salary_6_15 = Column(Float, default=0.0)
    advance_salary_16_31 = Column(Float, default=0.0)
    transfer_base_kitchen = Column(Float, default=0.0)
    service_charge = Column(Float, default=0.0)
    other_adjustments = Column(Float, default=0.0)

    expected_closing_balance = Column(Float, default=0.0)
    actual_closing_balance = Column(Float, default=0.0)
    difference = Column(Float, default=0.0) # Actual - Expected

    status = Column(String(20), default="PENDING") # RECONCILED, DIFFERENCE, PENDING
    remarks = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    branch = relationship("Branch", back_populates="cash_reconciliations")
