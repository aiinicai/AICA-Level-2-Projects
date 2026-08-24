from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class ReconciliationMatch(Base):
    __tablename__ = "reconciliation_matches"

    id = Column(Integer, primary_key=True, index=True)
    match_type = Column(String(50), nullable=False) # CARD_QR, AGGREGATOR, CASH
    source_entity = Column(String(50), nullable=False) # e.g. daily_sales, card_qr_reconciliations, settlement_batches
    source_id = Column(Integer, nullable=False)
    target_entity = Column(String(50), nullable=False) # e.g. bank_transactions
    target_id = Column(Integer, nullable=False)

    match_method = Column(String(50), nullable=False) # EXACT_REF, EXACT_AMOUNT_DATE, TOLERANCE, MANUAL
    confidence_score = Column(Float, default=1.0) # 0.0 to 1.0
    matched_by = Column(String(100), nullable=False, default="SYSTEM")
    reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
