from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Aggregator(Base):
    __tablename__ = "aggregators"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True) # ZOMATO, SWIGGY, DINEOUT
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    file_format_spec = Column(Text, nullable=True) # JSON config for header mappings

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    settlement_batches = relationship("SettlementBatch", back_populates="aggregator")
