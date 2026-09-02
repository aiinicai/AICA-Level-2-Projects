from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False) # DAILY_SALES, CASH_EXPENSE, BANK_STATEMENT, AGGREGATOR_SETTLEMENT
    source_name = Column(String(50), nullable=False) # Branch Code or Aggregator Code
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    total_rows = Column(Integer, default=0)
    success_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    status = Column(String(20), default="COMPLETED") # PROCESSING, COMPLETED, FAILED, PARTIAL

    errors = relationship("ImportErrorLog", back_populates="import_batch", cascade="all, delete-orphan")
    daily_sales = relationship("DailySale", back_populates="import_batch")
    bank_transactions = relationship("BankTransaction", back_populates="import_batch")
    settlement_batches = relationship("SettlementBatch", back_populates="import_batch")

class ImportErrorLog(Base):
    __tablename__ = "import_error_logs"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(Text, nullable=True)
    error_message = Column(Text, nullable=False)

    import_batch = relationship("ImportBatch", back_populates="errors")
