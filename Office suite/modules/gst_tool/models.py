from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

try:
    from .database import Base
except ImportError:
    from database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # Legal Name
    trade_name = Column(String(100), nullable=True)  # Trade Name
    gstin = Column(String(20), nullable=False, index=True)  # Frozen once created
    status = Column(String(20), default="Active")  # "Active" or "Inactive"
    constitution = Column(String(100), nullable=True)  # e.g., Proprietorship, Private Limited
    address = Column(String(250), nullable=True)  # Principal Place of Business Address
    registration_date = Column(String(30), nullable=True)  # Date of Liability / Registration
    created_at = Column(DateTime, default=datetime.utcnow)

    records = relationship("GSTRecord", back_populates="client", cascade="all, delete-orphan")
    ledgers = relationship("LedgerRecord", back_populates="client", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "trade_name": self.trade_name or self.name,
            "gstin": self.gstin,
            "status": self.status or "Active",
            "constitution": self.constitution or "Not Specified",
            "address": self.address or "Not Specified",
            "registration_date": self.registration_date or "N/A",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "record_count": len(self.records) if self.records else 0,
            "ledger_count": len(self.ledgers) if self.ledgers else 0
        }

class GSTRecord(Base):
    __tablename__ = "gst_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    return_type = Column(String(20), nullable=False, index=True)  # "GSTR-1" or "GSTR-3B"
    financial_year = Column(String(20), nullable=False, index=True)  # "2023-24"
    period = Column(String(30), nullable=False)  # "April 2023"
    turnover = Column(Float, default=0.0)
    tax_liability = Column(Float, default=0.0)
    due_date = Column(String(30), nullable=True)  # YYYY-MM-DD
    actual_filing_date = Column(String(30), nullable=True)  # YYYY-MM-DD
    is_edited = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # GSTR-1 Breakdown Columns
    b2b_supplies = Column(Float, default=0.0)
    b2c_large = Column(Float, default=0.0)
    b2c_small = Column(Float, default=0.0)
    exports = Column(Float, default=0.0)
    nil_exempt = Column(Float, default=0.0)
    cr_dr_notes = Column(Float, default=0.0)
    total_tax_liability = Column(Float, default=0.0)

    # GSTR-3B Breakdown Columns
    outward_taxable_3_1_a = Column(Float, default=0.0)
    inward_rcm_3_1_d = Column(Float, default=0.0)
    zero_rated_3_1_b = Column(Float, default=0.0)
    nil_exempt_3_1_c = Column(Float, default=0.0)
    itc_available_4_a = Column(Float, default=0.0)
    itc_reversed_4_b = Column(Float, default=0.0)
    net_itc_4_c = Column(Float, default=0.0)

    client = relationship("Client", back_populates="records")

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "return_type": self.return_type,
            "financial_year": self.financial_year,
            "period": self.period,
            "turnover": self.turnover,
            "tax_liability": self.tax_liability,
            "due_date": self.due_date,
            "actual_filing_date": self.actual_filing_date,
            "is_edited": self.is_edited,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # GSTR-1 Breakdown
            "b2b_supplies": self.b2b_supplies or 0.0,
            "b2c_large": self.b2c_large or 0.0,
            "b2c_small": self.b2c_small or 0.0,
            "exports": self.exports or 0.0,
            "nil_exempt": self.nil_exempt or 0.0,
            "cr_dr_notes": self.cr_dr_notes or 0.0,
            "total_tax_liability": self.total_tax_liability or self.tax_liability or 0.0,
            # GSTR-3B Breakdown
            "outward_taxable_3_1_a": self.outward_taxable_3_1_a or self.turnover or 0.0,
            "inward_rcm_3_1_d": self.inward_rcm_3_1_d or 0.0,
            "zero_rated_3_1_b": self.zero_rated_3_1_b or 0.0,
            "nil_exempt_3_1_c": self.nil_exempt_3_1_c or 0.0,
            "itc_available_4_a": self.itc_available_4_a or 0.0,
            "itc_reversed_4_b": self.itc_reversed_4_b or 0.0,
            "net_itc_4_c": self.net_itc_4_c or 0.0
        }

class LedgerRecord(Base):
    __tablename__ = "ledger_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    financial_year = Column(String(20), nullable=False, default="2023-24", index=True)
    ledger_type = Column(String(20), nullable=False)  # "Cash" or "Credit"
    date = Column(String(30), nullable=False)  # YYYY-MM-DD
    description = Column(String(200), nullable=True)
    amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="ledgers")

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "financial_year": self.financial_year,
            "ledger_type": self.ledger_type,
            "date": self.date,
            "description": self.description,
            "amount": self.amount,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
