from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class AccountingHead(Base):
    __tablename__ = "accounting_heads"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    head_type = Column(String(30), nullable=False) # EXPENSE, ASSET, TAX, REVENUE, DEDUCTION
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deductions = relationship("AggregatorDeduction", back_populates="accounting_head")
