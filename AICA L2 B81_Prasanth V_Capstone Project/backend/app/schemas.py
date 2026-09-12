from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# --- AUTH & USER ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "STANDARD_USER"  # ADMIN or STANDARD_USER
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- COMPANY ---
class CompanyBase(BaseModel):
    name: str
    short_name: str
    address: Optional[str] = None
    asset_id_prefix: str = "FA"
    numbering_format: str = "{PREFIX}-{NUM:6}"
    starting_number: int = 1
    is_active: bool = True

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    address: Optional[str] = None
    asset_id_prefix: Optional[str] = None
    numbering_format: Optional[str] = None
    starting_number: Optional[int] = None
    current_number: Optional[int] = None
    is_active: Optional[bool] = None

class CompanyOut(CompanyBase):
    id: int
    logo_path: Optional[str] = None
    current_number: int
    created_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True

# --- ASSET ---
class AssetBase(BaseModel):
    company_id: int
    asset_id: str
    asset_type: str = "FIXED_ASSET"  # FIXED_ASSET, STOCK
    description: Optional[str] = None
    location: Optional[str] = None
    sap_number: Optional[str] = None
    serial_number: Optional[str] = None
    department: Optional[str] = None
    cost_centre: Optional[str] = None
    custodian: Optional[str] = None
    purchase_date: Optional[str] = None
    code_type: str = "BARCODE"  # BARCODE, QR_CODE

class AssetCreate(AssetBase):
    auto_generate_id: bool = False
    is_override: bool = False
    override_reason: Optional[str] = None

class DuplicateCheckRequest(BaseModel):
    company_id: int
    asset_id: str

class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    existing_asset: Optional[Dict[str, Any]] = None

class DuplicateOverrideRequest(BaseModel):
    company_id: int
    asset_id: str
    justification_reason: str
    asset_data: Optional[AssetBase] = None

class ReprintRequest(BaseModel):
    reason: str

class AssetOut(AssetBase):
    id: int
    status: str
    print_count: int
    is_override: bool
    override_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    company_name: Optional[str] = None
    company_logo_path: Optional[str] = None

    class Config:
        from_attributes = True

# --- BULK UPLOAD ---
class BulkValidationRow(BaseModel):
    row_number: int
    company_name: Optional[str] = None
    company_id: Optional[int] = None
    asset_id: Optional[str] = None
    asset_type: str = "FIXED_ASSET"
    sap_number: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    serial_number: Optional[str] = None
    department: Optional[str] = None
    cost_centre: Optional[str] = None
    custodian: Optional[str] = None
    purchase_date: Optional[str] = None
    code_type: str = "BARCODE"
    status: str = "VALID"  # VALID, DUPLICATE_DB, DUPLICATE_BATCH, MISSING_REQUIRED, INVALID_FORMAT
    error_message: Optional[str] = None
    existing_record: Optional[Dict[str, Any]] = None
    override_reason: Optional[str] = None

class BulkValidationSummary(BaseModel):
    total_rows: int
    valid_count: int
    duplicate_count: int
    missing_fields_count: int
    invalid_format_count: int
    rows: List[BulkValidationRow]

class BulkGenerateRequest(BaseModel):
    rows: List[BulkValidationRow]

# --- TAG TEMPLATE ---
class TagTemplateBase(BaseModel):
    template_name: str
    company_id: Optional[int] = None
    width_mm: float = 70.0
    height_mm: float = 35.0
    code_type: str = "BARCODE"
    code_position: str = "BOTTOM"
    show_logo: bool = True
    show_company_name: bool = True
    field_visibility: Dict[str, bool] = Field(default_factory=dict)
    font_settings: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False

class TagTemplateCreate(TagTemplateBase):
    pass

class TagTemplateOut(TagTemplateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- LABEL SIZES & PRINTING ---
class LabelSizeBase(BaseModel):
    name: str
    category: str = "CUSTOM"
    width_mm: float
    height_mm: float
    gap_mm: float = 3.0
    orientation: str = "PORTRAIT"
    dpi: int = 300
    is_preset: bool = False

class LabelSizeCreate(LabelSizeBase):
    pass

class LabelSizeOut(LabelSizeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SheetLayoutConfig(BaseModel):
    page_size: str = "A4"  # A4, A3, LETTER
    orientation: str = "PORTRAIT"  # PORTRAIT, LANDSCAPE
    label_width_mm: float = 70.0
    label_height_mm: float = 35.0
    margin_top_mm: float = 10.0
    margin_bottom_mm: float = 10.0
    margin_left_mm: float = 10.0
    margin_right_mm: float = 10.0
    horizontal_gap_mm: float = 3.0
    vertical_gap_mm: float = 3.0
    columns: Optional[int] = None
    rows: Optional[int] = None

class DirectPrintJob(BaseModel):
    printer_name: str
    asset_ids: List[int]
    label_size_id: Optional[int] = None
    copies: int = 1

# --- AUDIT LOG ---
class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[str] = None
    result: str
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- DASHBOARD & SETTINGS ---
class DashboardStats(BaseModel):
    total_companies: int
    total_tags_generated: int
    tags_generated_today: int
    fixed_assets_count: int
    stock_assets_count: int
    duplicate_attempts_count: int
    duplicate_overrides_count: int
    recent_activity: List[Dict[str, Any]] = []

class CompanyStat(BaseModel):
    company_id: int
    company_name: str
    short_name: str
    total_tags: int
    fixed_assets: int
    stock_assets: int
    tags_today: int
    last_asset_id: Optional[str] = None

class SystemSettingsOut(BaseModel):
    id: int
    default_company_id: Optional[int] = None
    default_asset_type: str = "FIXED_ASSET"
    default_code_type: str = "BARCODE"
    default_label_size_id: Optional[int] = None
    default_page_size: str = "A4"
    default_export_format: str = "EXCEL"
    app_name: str = "Asset Tagging & Label Management System"

    class Config:
        from_attributes = True
