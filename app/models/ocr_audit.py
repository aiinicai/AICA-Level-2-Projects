from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class OCRAuditLog(Base):
    __tablename__ = "ocr_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_image_b64 = Column(Text, nullable=True)
    preprocessed_image_b64 = Column(Text, nullable=True)
    amount_crop_b64 = Column(Text, nullable=True)
    
    raw_ocr_response = Column(JSON, nullable=True)
    parsed_rows = Column(JSON, nullable=True)
    field_mapping = Column(JSON, nullable=True)
    
    handwritten_total = Column(Float, nullable=True)
    calculated_total = Column(Float, default=0.0)
    total_difference = Column(Float, default=0.0)
    
    user_overrides = Column(JSON, nullable=True)
    final_saved_values = Column(JSON, nullable=True)
    extraction_trace = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
