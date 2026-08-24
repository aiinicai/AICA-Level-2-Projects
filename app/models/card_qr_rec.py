from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class CardQrReconciliation(Base):
    __tablename__ = "card_qr_reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    sale_date = Column(Date, nullable=False, index=True)

    card_qr_sales_amount = Column(Float, default=0.0) # Pulled from Day Book
    received_amount = Column(Float, default=0.0) # Received from bank statement
    difference = Column(Float, default=0.0) # Card_QR_Sales - Received_Amount

    settlement_date = Column(Date, nullable=True)
    bank_reference = Column(String(100), nullable=True)
    bank_account = Column(String(50), nullable=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True)

    status = Column(String(20), default="PENDING") # MATCHED, DIFFERENCE, PENDING, MANUALLY_MATCHED
    match_method = Column(String(50), nullable=True) # EXACT_REF, EXACT_AMOUNT_DATE, DATE_TOLERANCE, MANUAL
    remarks = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    branch = relationship("Branch", back_populates="card_qr_reconciliations")
    bank_transaction = relationship("BankTransaction")
