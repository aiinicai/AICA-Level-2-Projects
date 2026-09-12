from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from .database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="STANDARD_USER", nullable=False)  # ADMIN, STANDARD_USER
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    assets = relationship("Asset", back_populates="creator", foreign_keys="Asset.created_by")
    audit_logs = relationship("AuditLog", back_populates="user")
    overrides = relationship("DuplicateOverride", back_populates="user")

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    short_name = Column(String(50), unique=True, index=True, nullable=False)
    logo_path = Column(String(500), nullable=True)
    address = Column(Text, nullable=True)
    asset_id_prefix = Column(String(20), default="FA", nullable=False)
    numbering_format = Column(String(50), default="{PREFIX}-{NUM:6}", nullable=False)
    starting_number = Column(Integer, default=1, nullable=False)
    current_number = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    assets = relationship("Asset", back_populates="company", cascade="all, delete-orphan")
    templates = relationship("TagTemplate", back_populates="company", cascade="all, delete-orphan")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(100), nullable=False, index=True)
    asset_type = Column(String(50), default="FIXED_ASSET", nullable=False)  # FIXED_ASSET, STOCK
    description = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)
    sap_number = Column(String(100), nullable=True, index=True)
    serial_number = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    cost_centre = Column(String(100), nullable=True)
    custodian = Column(String(255), nullable=True)
    purchase_date = Column(String(50), nullable=True)
    
    code_type = Column(String(20), default="BARCODE", nullable=False)  # BARCODE, QR_CODE
    status = Column(String(50), default="GENERATED", nullable=False)  # GENERATED, PRINTED, REPRINTED, CANCELLED
    print_count = Column(Integer, default=0, nullable=False)
    is_override = Column(Boolean, default=False, nullable=False)
    override_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    company = relationship("Company", back_populates="assets")
    creator = relationship("User", back_populates="assets", foreign_keys=[created_by])
    overrides = relationship("DuplicateOverride", back_populates="asset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_asset_company_asset_id", "company_id", "asset_id"),
    )

class DuplicateOverride(Base):
    __tablename__ = "duplicate_overrides"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True)
    duplicate_asset_id = Column(String(100), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    justification_reason = Column(Text, nullable=False)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    asset = relationship("Asset", back_populates="overrides")
    user = relationship("User", back_populates="overrides")
    company = relationship("Company")

class TagTemplate(Base):
    __tablename__ = "tag_templates"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    template_name = Column(String(100), nullable=False)
    width_mm = Column(Float, default=70.0, nullable=False)
    height_mm = Column(Float, default=35.0, nullable=False)
    code_type = Column(String(20), default="BARCODE", nullable=False)
    code_position = Column(String(20), default="BOTTOM", nullable=False)  # BOTTOM, RIGHT
    show_logo = Column(Boolean, default=True, nullable=False)
    show_company_name = Column(Boolean, default=True, nullable=False)
    field_visibility = Column(JSON, default=dict, nullable=False)  # e.g., {"sap_number": true, "description": true, "location": true}
    font_settings = Column(JSON, default=dict, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    company = relationship("Company", back_populates="templates")

class LabelSize(Base):
    __tablename__ = "label_sizes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), default="CUSTOM", nullable=False)  # ZEBRA, BROTHER, DYMO, TSC, SHEET, CUSTOM
    width_mm = Column(Float, nullable=False)
    height_mm = Column(Float, nullable=False)
    gap_mm = Column(Float, default=3.0, nullable=False)
    orientation = Column(String(20), default="PORTRAIT", nullable=False)
    dpi = Column(Integer, default=300, nullable=False)
    is_preset = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

class PrinterConfig(Base):
    __tablename__ = "printer_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    printer_type = Column(String(50), default="LOCAL_DRIVER", nullable=False)
    target_printer_name = Column(String(255), nullable=True)
    default_label_size_id = Column(Integer, ForeignKey("label_sizes.id"), nullable=True)
    dpi = Column(Integer, default=300, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    result = Column(String(50), default="SUCCESS", nullable=False)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True)
    default_company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    default_asset_type = Column(String(50), default="FIXED_ASSET")
    default_code_type = Column(String(20), default="BARCODE")
    default_label_size_id = Column(Integer, ForeignKey("label_sizes.id"), nullable=True)
    default_page_size = Column(String(20), default="A4")
    default_export_format = Column(String(20), default="EXCEL")
    app_name = Column(String(100), default="Asset Tagging & Label Management System")
