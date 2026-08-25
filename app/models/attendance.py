from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Float, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    name_key = Column(String(120), nullable=False, index=True)
    rank = Column(String(80), nullable=True)
    team = Column(String(80), nullable=True)
    is_active = Column(Boolean, default=True)
    first_seen_date = Column(Date, nullable=True)
    last_seen_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    monthly_salary = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    marks = relationship("AttendanceMark", back_populates="employee", cascade="all, delete-orphan")
    salary_advances = relationship("SalaryAdvance", back_populates="employee", cascade="all, delete-orphan")
    bank_advances = relationship("BankAdvance", back_populates="employee", cascade="all, delete-orphan")


class AttendanceMark(Base):
    __tablename__ = "attendance_marks"
    __table_args__ = (
        UniqueConstraint("employee_id", "work_date", name="uq_attendance_employee_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    work_date = Column(Date, nullable=False, index=True)
    mark = Column(String(8), nullable=False)
    raw_mark = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = relationship("Employee", back_populates="marks")


class SalaryAdvance(Base):
    __tablename__ = "salary_advances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    advance_date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False, default=0.0)
    source = Column(String(40), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="salary_advances")


class BankAdvance(Base):
    __tablename__ = "bank_advances"
    __table_args__ = (
        UniqueConstraint("employee_id", "year", "month", name="uq_bank_advance_employee_month"),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = relationship("Employee", back_populates="bank_advances")
