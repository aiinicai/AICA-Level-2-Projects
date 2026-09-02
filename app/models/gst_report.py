from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from app.core.database import Base


class GstReportInput(Base):
    __tablename__ = "gst_report_inputs"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    adj_mode = Column(String(8), nullable=False, default="less")
    adj_cash = Column(Float, default=0.0)
    adj_card_qr = Column(Float, default=0.0)
    adj_dineout = Column(Float, default=0.0)
    adj_zomato = Column(Float, default=0.0)
    adj_swiggy = Column(Float, default=0.0)
    available_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
