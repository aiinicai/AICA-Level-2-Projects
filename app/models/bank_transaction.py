from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    bank_account = Column(String(50), nullable=False)
    tx_date = Column(Date, nullable=False, index=True)
    value_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    reference_no = Column(String(100), nullable=True, index=True)
    
    credit_amount = Column(Float, default=0.0)
    debit_amount = Column(Float, default=0.0)
    amount = Column(Float, default=0.0) # Net amount (+ for credit, - for debit)
    
    is_matched = Column(Boolean, default=False)
    matched_type = Column(String(50), nullable=True) # CARD_QR, AGGREGATOR
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    import_batch = relationship("ImportBatch", back_populates="bank_transactions")
