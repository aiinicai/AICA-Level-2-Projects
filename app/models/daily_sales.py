from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class DailySale(Base):
    __tablename__ = "daily_sales"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    sale_date = Column(Date, nullable=False, index=True)
    payment_channel_id = Column(Integer, ForeignKey("payment_channels.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False, default=0.0)
    
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True)
    status = Column(String(20), default="UNRECONCILED") # UNRECONCILED, RECONCILED, DIFFERENCE
    remarks = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    branch = relationship("Branch", back_populates="daily_sales")
    payment_channel = relationship("PaymentChannel", back_populates="daily_sales")
    import_batch = relationship("ImportBatch", back_populates="daily_sales")
