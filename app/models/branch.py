from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=True)
    opening_cash_balance = Column(Float, default=0.0)
    is_base_kitchen = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    contact_details = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="branch")
    daily_sales = relationship("DailySale", back_populates="branch", cascade="all, delete-orphan")
    cash_reconciliations = relationship("CashReconciliation", back_populates="branch", cascade="all, delete-orphan")
    card_qr_reconciliations = relationship("CardQrReconciliation", back_populates="branch", cascade="all, delete-orphan")
    settlement_batches = relationship("SettlementBatch", back_populates="branch", cascade="all, delete-orphan")
