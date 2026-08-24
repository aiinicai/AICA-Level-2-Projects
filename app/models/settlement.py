from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class SettlementBatch(Base):
    __tablename__ = "settlement_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_no = Column(String(50), nullable=False, index=True)
    aggregator_id = Column(Integer, ForeignKey("aggregators.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)

    period_start_date = Column(Date, nullable=False)
    period_end_date = Column(Date, nullable=False)
    settlement_date = Column(Date, nullable=True)

    gross_sales = Column(Float, default=0.0) # Total sales from Day Book or Settlement report
    payout = Column(Float, default=0.0) # Actual bank payout received
    total_deductions = Column(Float, default=0.0)
    actual_difference = Column(Float, default=0.0) # Gross Sales - Payout
    difference_adjustment = Column(Float, default=0.0) # Actual Difference - Total Deductions

    status = Column(String(20), default="PENDING") # RECONCILED, DIFFERENCE, PENDING
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True)
    remarks = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    aggregator = relationship("Aggregator", back_populates="settlement_batches")
    branch = relationship("Branch", back_populates="settlement_batches")
    import_batch = relationship("ImportBatch", back_populates="settlement_batches")
    deductions = relationship("AggregatorDeduction", back_populates="settlement_batch", cascade="all, delete-orphan")

class AggregatorDeduction(Base):
    __tablename__ = "aggregator_deductions"

    id = Column(Integer, primary_key=True, index=True)
    settlement_batch_id = Column(Integer, ForeignKey("settlement_batches.id"), nullable=False, index=True)
    deduction_type = Column(String(50), nullable=False) # COMMISSION, PROMOTION, TCS, TDS, MISC, GST_9_5, PACKING_CHARGES
    description = Column(String(255), nullable=True)
    amount = Column(Float, default=0.0)
    accounting_head_id = Column(Integer, ForeignKey("accounting_heads.id"), nullable=True)

    settlement_batch = relationship("SettlementBatch", back_populates="deductions")
    accounting_head = relationship("AccountingHead", back_populates="deductions")
