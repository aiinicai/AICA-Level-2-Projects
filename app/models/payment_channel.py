from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class PaymentChannel(Base):
    __tablename__ = "payment_channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True) # Cash, Card/QR, Zomato, Swiggy, Dineout
    code = Column(String(20), unique=True, nullable=False, index=True)
    channel_type = Column(String(20), nullable=False) # CASH, BANK, AGGREGATOR, OTHER
    reconciliation_method = Column(String(50), nullable=False, default="AUTOMATIC") # PHYSICAL_COUNT, BANK_STATEMENT, AGGREGATOR_SETTLEMENT
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mappings = relationship("ChannelMapping", back_populates="payment_channel", cascade="all, delete-orphan")
    daily_sales = relationship("DailySale", back_populates="payment_channel")

class ChannelMapping(Base):
    __tablename__ = "channel_mappings"

    id = Column(Integer, primary_key=True, index=True)
    payment_channel_id = Column(Integer, ForeignKey("payment_channels.id"), nullable=False)
    alias = Column(String(100), nullable=False, index=True) # Header text found in Excel like "Cash Sale", "UPI", "Credit Card"
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True) # Nullable = global mapping

    payment_channel = relationship("PaymentChannel", back_populates="mappings")
