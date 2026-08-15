from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'cosmetic-inv-secret-key-2024')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()

# Create the main app
app = FastAPI(title="Cosmetic Inventory Management System")
api_router = APIRouter(prefix="/api")

# ==================== MODELS ====================

class UserRole:
    ADMIN = "admin"
    PRODUCTION_MANAGER = "production_manager"
    STORE_KEEPER = "store_keeper"
    VIEWER = "viewer"

class UserBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    role: str = UserRole.VIEWER
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: str = UserRole.VIEWER

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool

class SupplierBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    contact_person: str
    phone: str
    email: str
    address: str
    material_type: str  # chemicals, packing
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SupplierCreate(BaseModel):
    name: str
    contact_person: str
    phone: str
    email: str
    address: str
    material_type: str

class RawMaterialBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    sku: str
    category: str  # chemical, packing
    unit: str  # kg, liters, pieces
    current_stock: float = 0
    min_stock_level: float
    max_stock_level: float
    unit_price: float
    supplier_id: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RawMaterialCreate(BaseModel):
    name: str
    sku: str
    category: str
    unit: str
    min_stock_level: float
    max_stock_level: float
    unit_price: float
    supplier_id: Optional[str] = None

class BatchBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_number: str
    material_id: str
    material_name: str
    quantity: float
    manufacturing_date: str
    expiry_date: str
    supplier_id: Optional[str] = None
    purchase_order_id: Optional[str] = None
    status: str = "in_stock"  # in_stock, issued, consumed, expired
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class BatchCreate(BaseModel):
    batch_number: str
    material_id: str
    quantity: float
    manufacturing_date: str
    expiry_date: str
    supplier_id: Optional[str] = None
    purchase_order_id: Optional[str] = None

class PurchaseOrderBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    po_number: str
    supplier_id: str
    supplier_name: str
    items: List[dict]  # [{material_id, material_name, quantity, unit_price}]
    total_amount: float
    status: str = "pending"  # pending, approved, received, cancelled
    order_date: str
    expected_delivery: str
    received_date: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    items: List[dict]
    order_date: str
    expected_delivery: str
    notes: Optional[str] = None

class ProductBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    sku: str
    category: str  # shampoo, facewash, serum, moisturizer
    description: Optional[str] = None
    batch_size: float  # standard production batch size
    unit: str  # liters, kg
    formula: List[dict] = []  # [{material_id, material_name, quantity}]
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ProductCreate(BaseModel):
    name: str
    sku: str
    category: str
    description: Optional[str] = None
    batch_size: float
    unit: str
    formula: List[dict] = []

class ChemistReportBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    report_number: str
    product_id: str
    product_name: str
    batch_number: str
    batch_size: float
    materials_required: List[dict]  # [{material_id, material_name, quantity, batch_id}]
    status: str = "pending"  # pending, approved, issued, in_production
    requested_by: str
    approved_by: Optional[str] = None
    issued_date: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ChemistReportCreate(BaseModel):
    product_id: str
    batch_size: float
    materials_required: List[dict]
    notes: Optional[str] = None

class ProductionBatchBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_number: str
    product_id: str
    product_name: str
    chemist_report_id: str
    quantity_produced: float
    stage: str = "processing"  # processing, packaging, dispatch, completed
    start_date: str
    end_date: Optional[str] = None
    quality_check: str = "pending"  # pending, passed, failed
    notes: Optional[str] = None
    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ProductionBatchCreate(BaseModel):
    product_id: str
    chemist_report_id: str
    quantity_produced: float
    start_date: str
    notes: Optional[str] = None

class PackagingRecordBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    production_batch_id: str
    batch_number: str
    product_name: str
    packaging_materials: List[dict]  # [{material_id, material_name, quantity}]
    units_packed: int
    unit_size: str  # 100ml, 200ml, etc
    start_date: str
    end_date: Optional[str] = None
    status: str = "in_progress"  # in_progress, completed
    packed_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PackagingRecordCreate(BaseModel):
    production_batch_id: str
    packaging_materials: List[dict]
    units_packed: int
    unit_size: str
    start_date: str

class DispatchRecordBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dispatch_number: str
    packaging_record_id: str
    batch_number: str
    product_name: str
    quantity_dispatched: int
    destination: str
    dispatch_date: str
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    status: str = "dispatched"  # dispatched, delivered
    delivered_date: Optional[str] = None
    dispatched_by: str
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DispatchRecordCreate(BaseModel):
    packaging_record_id: str
    quantity_dispatched: int
    destination: str
    dispatch_date: str
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    notes: Optional[str] = None

class StockMovementBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    material_id: str
    material_name: str
    movement_type: str  # in, out
    quantity: float
    reference_type: str  # purchase_order, chemist_report, adjustment
    reference_id: str
    batch_id: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_roles(allowed_roles: List[str]):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_count = await db.users.count_documents({})
    role = UserRole.ADMIN if user_count == 0 else user_data.role
    
    user = UserBase(
        email=user_data.email,
        name=user_data.name,
        role=role
    )
    user_dict = user.model_dump()
    user_dict["password_hash"] = hash_password(user_data.password)
    
    await db.users.insert_one(user_dict)
    token = create_token(user.id, user.role)
    
    return {
        "token": token,
        "user": UserResponse(**user_dict).model_dump()
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account disabled")
    
    token = create_token(user["id"], user["role"])
    return {
        "token": token,
        "user": UserResponse(**user).model_dump()
    }

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(**user)

# ==================== USER MANAGEMENT ====================

@api_router.get("/users")
async def get_users(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return users

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))
    
    result = await db.users.update_one({"id": user_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User updated"}

# ==================== SUPPLIERS ====================

@api_router.post("/suppliers")
async def create_supplier(data: SupplierCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    supplier = SupplierBase(**data.model_dump())
    await db.suppliers.insert_one(supplier.model_dump())
    return supplier.model_dump()

@api_router.get("/suppliers")
async def get_suppliers(user: dict = Depends(get_current_user)):
    suppliers = await db.suppliers.find({}, {"_id": 0}).to_list(1000)
    return suppliers

@api_router.get("/suppliers/{supplier_id}")
async def get_supplier(supplier_id: str, user: dict = Depends(get_current_user)):
    supplier = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@api_router.put("/suppliers/{supplier_id}")
async def update_supplier(supplier_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    result = await db.suppliers.update_one({"id": supplier_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier updated"}

@api_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    result = await db.suppliers.delete_one({"id": supplier_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted"}

# ==================== RAW MATERIALS ====================

@api_router.post("/materials")
async def create_material(data: RawMaterialCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    material = RawMaterialBase(**data.model_dump())
    await db.materials.insert_one(material.model_dump())
    return material.model_dump()

@api_router.get("/materials")
async def get_materials(category: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if category:
        query["category"] = category
    materials = await db.materials.find(query, {"_id": 0}).to_list(1000)
    return materials

@api_router.get("/materials/{material_id}")
async def get_material(material_id: str, user: dict = Depends(get_current_user)):
    material = await db.materials.find_one({"id": material_id}, {"_id": 0})
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material

@api_router.put("/materials/{material_id}")
async def update_material(material_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    result = await db.materials.update_one({"id": material_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"message": "Material updated"}

@api_router.delete("/materials/{material_id}")
async def delete_material(material_id: str, user: dict = Depends(require_roles([UserRole.ADMIN]))):
    result = await db.materials.delete_one({"id": material_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"message": "Material deleted"}

# ==================== BATCHES ====================

@api_router.post("/batches")
async def create_batch(data: BatchCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    material = await db.materials.find_one({"id": data.material_id}, {"_id": 0})
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    batch = BatchBase(
        **data.model_dump(),
        material_name=material["name"]
    )
    await db.batches.insert_one(batch.model_dump())
    
    # Update material stock
    await db.materials.update_one(
        {"id": data.material_id},
        {"$inc": {"current_stock": data.quantity}}
    )
    
    return batch.model_dump()

@api_router.get("/batches")
async def get_batches(material_id: Optional[str] = None, status: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if material_id:
        query["material_id"] = material_id
    if status:
        query["status"] = status
    batches = await db.batches.find(query, {"_id": 0}).to_list(1000)
    return batches

@api_router.put("/batches/{batch_id}")
async def update_batch(batch_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    result = await db.batches.update_one({"id": batch_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"message": "Batch updated"}

# ==================== PURCHASE ORDERS ====================

async def generate_po_number():
    count = await db.purchase_orders.count_documents({})
    return f"PO-{datetime.now().strftime('%Y%m')}-{str(count + 1).zfill(4)}"

@api_router.post("/purchase-orders")
async def create_purchase_order(data: PurchaseOrderCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    supplier = await db.suppliers.find_one({"id": data.supplier_id}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    total_amount = sum(item["quantity"] * item["unit_price"] for item in data.items)
    po_number = await generate_po_number()
    
    po = PurchaseOrderBase(
        **data.model_dump(),
        po_number=po_number,
        supplier_name=supplier["name"],
        total_amount=total_amount,
        created_by=user["id"]
    )
    await db.purchase_orders.insert_one(po.model_dump())
    return po.model_dump()

@api_router.get("/purchase-orders")
async def get_purchase_orders(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    pos = await db.purchase_orders.find(query, {"_id": 0}).to_list(1000)
    return pos

@api_router.get("/purchase-orders/{po_id}")
async def get_purchase_order(po_id: str, user: dict = Depends(get_current_user)):
    po = await db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po

@api_router.put("/purchase-orders/{po_id}")
async def update_purchase_order(po_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    result = await db.purchase_orders.update_one({"id": po_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return {"message": "Purchase order updated"}

@api_router.post("/purchase-orders/{po_id}/receive")
async def receive_purchase_order(po_id: str, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    po = await db.purchase_orders.find_one({"id": po_id}, {"_id": 0})
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if po["status"] != "approved":
        raise HTTPException(status_code=400, detail="PO must be approved before receiving")
    
    # Create batches and update stock for each item
    for item in po["items"]:
        batch_number = f"B-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        batch = BatchBase(
            batch_number=batch_number,
            material_id=item["material_id"],
            material_name=item["material_name"],
            quantity=item["quantity"],
            manufacturing_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            expiry_date=(datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d"),
            supplier_id=po["supplier_id"],
            purchase_order_id=po_id
        )
        await db.batches.insert_one(batch.model_dump())
        
        await db.materials.update_one(
            {"id": item["material_id"]},
            {"$inc": {"current_stock": item["quantity"]}}
        )
        
        # Record stock movement
        movement = StockMovementBase(
            material_id=item["material_id"],
            material_name=item["material_name"],
            movement_type="in",
            quantity=item["quantity"],
            reference_type="purchase_order",
            reference_id=po_id,
            batch_id=batch.id,
            created_by=user["id"]
        )
        await db.stock_movements.insert_one(movement.model_dump())
    
    await db.purchase_orders.update_one(
        {"id": po_id},
        {"$set": {"status": "received", "received_date": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Purchase order received and stock updated"}

# ==================== PRODUCTS ====================

@api_router.post("/products")
async def create_product(data: ProductCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.PRODUCTION_MANAGER]))):
    product = ProductBase(**data.model_dump())
    await db.products.insert_one(product.model_dump())
    return product.model_dump()

@api_router.get("/products")
async def get_products(category: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if category:
        query["category"] = category
    products = await db.products.find(query, {"_id": 0}).to_list(1000)
    return products

@api_router.get("/products/{product_id}")
async def get_product(product_id: str, user: dict = Depends(get_current_user)):
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@api_router.put("/products/{product_id}")
async def update_product(product_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.PRODUCTION_MANAGER]))):
    result = await db.products.update_one({"id": product_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product updated"}

# ==================== CHEMIST REPORTS ====================

async def generate_report_number():
    count = await db.chemist_reports.count_documents({})
    return f"CR-{datetime.now().strftime('%Y%m')}-{str(count + 1).zfill(4)}"

@api_router.post("/chemist-reports")
async def create_chemist_report(data: ChemistReportCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.PRODUCTION_MANAGER]))):
    product = await db.products.find_one({"id": data.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    batch_number = f"PB-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    report_number = await generate_report_number()
    
    report = ChemistReportBase(
        **data.model_dump(),
        report_number=report_number,
        product_name=product["name"],
        batch_number=batch_number,
        requested_by=user["id"]
    )
    await db.chemist_reports.insert_one(report.model_dump())
    return report.model_dump()

@api_router.get("/chemist-reports")
async def get_chemist_reports(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    reports = await db.chemist_reports.find(query, {"_id": 0}).to_list(1000)
    return reports

@api_router.get("/chemist-reports/{report_id}")
async def get_chemist_report(report_id: str, user: dict = Depends(get_current_user)):
    report = await db.chemist_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@api_router.put("/chemist-reports/{report_id}")
async def update_chemist_report(report_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.PRODUCTION_MANAGER]))):
    result = await db.chemist_reports.update_one({"id": report_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Report updated"}

@api_router.post("/chemist-reports/{report_id}/issue-materials")
async def issue_materials(report_id: str, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    report = await db.chemist_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report["status"] != "approved":
        raise HTTPException(status_code=400, detail="Report must be approved before issuing materials")
    
    # Check and deduct stock for each material
    for material_req in report["materials_required"]:
        material = await db.materials.find_one({"id": material_req["material_id"]}, {"_id": 0})
        if not material:
            raise HTTPException(status_code=404, detail=f"Material {material_req['material_name']} not found")
        
        if material["current_stock"] < material_req["quantity"]:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {material_req['material_name']}")
        
        await db.materials.update_one(
            {"id": material_req["material_id"]},
            {"$inc": {"current_stock": -material_req["quantity"]}}
        )
        
        # Record stock movement
        movement = StockMovementBase(
            material_id=material_req["material_id"],
            material_name=material_req["material_name"],
            movement_type="out",
            quantity=material_req["quantity"],
            reference_type="chemist_report",
            reference_id=report_id,
            batch_id=material_req.get("batch_id"),
            created_by=user["id"]
        )
        await db.stock_movements.insert_one(movement.model_dump())
    
    await db.chemist_reports.update_one(
        {"id": report_id},
        {"$set": {"status": "issued", "issued_date": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Materials issued successfully"}

# ==================== PRODUCTION BATCHES ====================

@api_router.post("/production-batches")
async def create_production_batch(data: ProductionBatchCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.PRODUCTION_MANAGER]))):
    product = await db.products.find_one({"id": data.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    report = await db.chemist_reports.find_one({"id": data.chemist_report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Chemist report not found")
    
    batch = ProductionBatchBase(
        **data.model_dump(),
        batch_number=report["batch_number"],
        product_name=product["name"],
        created_by=user["id"]
    )
    await db.production_batches.insert_one(batch.model_dump())
    
    # Update chemist report status
    await db.chemist_reports.update_one(
        {"id": data.chemist_report_id},
        {"$set": {"status": "in_production"}}
    )
    
    return batch.model_dump()

@api_router.get("/production-batches")
async def get_production_batches(stage: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if stage:
        query["stage"] = stage
    batches = await db.production_batches.find(query, {"_id": 0}).to_list(1000)
    return batches

@api_router.get("/production-batches/{batch_id}")
async def get_production_batch(batch_id: str, user: dict = Depends(get_current_user)):
    batch = await db.production_batches.find_one({"id": batch_id}, {"_id": 0})
    if not batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    return batch

@api_router.put("/production-batches/{batch_id}")
async def update_production_batch(batch_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.PRODUCTION_MANAGER]))):
    result = await db.production_batches.update_one({"id": batch_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Production batch not found")
    return {"message": "Production batch updated"}

# ==================== PACKAGING ====================

@api_router.post("/packaging-records")
async def create_packaging_record(data: PackagingRecordCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.PRODUCTION_MANAGER]))):
    prod_batch = await db.production_batches.find_one({"id": data.production_batch_id}, {"_id": 0})
    if not prod_batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    
    record = PackagingRecordBase(
        **data.model_dump(),
        batch_number=prod_batch["batch_number"],
        product_name=prod_batch["product_name"],
        packed_by=user["id"]
    )
    await db.packaging_records.insert_one(record.model_dump())
    
    # Deduct packaging materials from stock
    for mat in data.packaging_materials:
        await db.materials.update_one(
            {"id": mat["material_id"]},
            {"$inc": {"current_stock": -mat["quantity"]}}
        )
        
        movement = StockMovementBase(
            material_id=mat["material_id"],
            material_name=mat["material_name"],
            movement_type="out",
            quantity=mat["quantity"],
            reference_type="packaging",
            reference_id=record.id,
            created_by=user["id"]
        )
        await db.stock_movements.insert_one(movement.model_dump())
    
    # Update production batch stage
    await db.production_batches.update_one(
        {"id": data.production_batch_id},
        {"$set": {"stage": "packaging"}}
    )
    
    return record.model_dump()

@api_router.get("/packaging-records")
async def get_packaging_records(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    records = await db.packaging_records.find(query, {"_id": 0}).to_list(1000)
    return records

@api_router.put("/packaging-records/{record_id}")
async def update_packaging_record(record_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.PRODUCTION_MANAGER]))):
    result = await db.packaging_records.update_one({"id": record_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Packaging record not found")
    return {"message": "Packaging record updated"}

# ==================== DISPATCH ====================

async def generate_dispatch_number():
    count = await db.dispatch_records.count_documents({})
    return f"DSP-{datetime.now().strftime('%Y%m')}-{str(count + 1).zfill(4)}"

@api_router.post("/dispatch-records")
async def create_dispatch_record(data: DispatchRecordCreate, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    pkg_record = await db.packaging_records.find_one({"id": data.packaging_record_id}, {"_id": 0})
    if not pkg_record:
        raise HTTPException(status_code=404, detail="Packaging record not found")
    
    dispatch_number = await generate_dispatch_number()
    
    record = DispatchRecordBase(
        **data.model_dump(),
        dispatch_number=dispatch_number,
        batch_number=pkg_record["batch_number"],
        product_name=pkg_record["product_name"],
        dispatched_by=user["id"]
    )
    await db.dispatch_records.insert_one(record.model_dump())
    
    # Update production batch stage
    prod_batch = await db.production_batches.find_one({"batch_number": pkg_record["batch_number"]}, {"_id": 0})
    if prod_batch:
        await db.production_batches.update_one(
            {"id": prod_batch["id"]},
            {"$set": {"stage": "dispatch"}}
        )
    
    return record.model_dump()

@api_router.get("/dispatch-records")
async def get_dispatch_records(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    records = await db.dispatch_records.find(query, {"_id": 0}).to_list(1000)
    return records

@api_router.put("/dispatch-records/{record_id}")
async def update_dispatch_record(record_id: str, update_data: dict, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.STORE_KEEPER]))):
    result = await db.dispatch_records.update_one({"id": record_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Dispatch record not found")
    return {"message": "Dispatch record updated"}

# ==================== STOCK MOVEMENTS ====================

@api_router.get("/stock-movements")
async def get_stock_movements(material_id: Optional[str] = None, movement_type: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {}
    if material_id:
        query["material_id"] = material_id
    if movement_type:
        query["movement_type"] = movement_type
    movements = await db.stock_movements.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return movements

# ==================== DASHBOARD & REPORTS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    # Material counts
    total_materials = await db.materials.count_documents({})
    chemical_count = await db.materials.count_documents({"category": "chemical"})
    packing_count = await db.materials.count_documents({"category": "packing"})
    
    # Low stock materials
    low_stock = await db.materials.find(
        {"$expr": {"$lt": ["$current_stock", "$min_stock_level"]}},
        {"_id": 0}
    ).to_list(100)
    
    # Stage counts
    pending_po = await db.purchase_orders.count_documents({"status": "pending"})
    pending_reports = await db.chemist_reports.count_documents({"status": "pending"})
    in_production = await db.production_batches.count_documents({"stage": "processing"})
    in_packaging = await db.production_batches.count_documents({"stage": "packaging"})
    dispatched_today = await db.dispatch_records.count_documents({
        "dispatch_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    })
    
    # Supplier count
    total_suppliers = await db.suppliers.count_documents({})
    
    # Products count
    total_products = await db.products.count_documents({})
    
    # Expiring batches (within 30 days)
    thirty_days_later = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    expiring_batches = await db.batches.find({
        "expiry_date": {"$lte": thirty_days_later, "$gte": today},
        "status": "in_stock"
    }, {"_id": 0}).to_list(100)
    
    return {
        "materials": {
            "total": total_materials,
            "chemicals": chemical_count,
            "packing": packing_count,
            "low_stock": low_stock
        },
        "suppliers": total_suppliers,
        "products": total_products,
        "stages": {
            "pending_po": pending_po,
            "pending_reports": pending_reports,
            "in_production": in_production,
            "in_packaging": in_packaging,
            "dispatched_today": dispatched_today
        },
        "expiring_batches": expiring_batches
    }

@api_router.get("/reports/consumption")
async def get_consumption_report(start_date: str, end_date: str, user: dict = Depends(get_current_user)):
    movements = await db.stock_movements.find({
        "movement_type": "out",
        "created_at": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(10000)
    
    # Group by material
    consumption_by_material = {}
    for m in movements:
        mid = m["material_id"]
        if mid not in consumption_by_material:
            consumption_by_material[mid] = {
                "material_name": m["material_name"],
                "total_quantity": 0,
                "movements": []
            }
        consumption_by_material[mid]["total_quantity"] += m["quantity"]
        consumption_by_material[mid]["movements"].append(m)
    
    return list(consumption_by_material.values())

@api_router.get("/reports/stage-wise")
async def get_stage_wise_report(user: dict = Depends(get_current_user)):
    # Get all production batches grouped by stage
    stages = ["processing", "packaging", "dispatch", "completed"]
    report = {}
    
    for stage in stages:
        batches = await db.production_batches.find({"stage": stage}, {"_id": 0}).to_list(1000)
        report[stage] = {
            "count": len(batches),
            "batches": batches
        }
    
    return report

@api_router.get("/reports/inventory-summary")
async def get_inventory_summary(user: dict = Depends(get_current_user)):
    materials = await db.materials.find({}, {"_id": 0}).to_list(1000)
    
    summary = {
        "chemicals": {"items": [], "total_value": 0},
        "packing": {"items": [], "total_value": 0}
    }
    
    for mat in materials:
        value = mat["current_stock"] * mat["unit_price"]
        item = {**mat, "stock_value": value}
        
        if mat["category"] == "chemical":
            summary["chemicals"]["items"].append(item)
            summary["chemicals"]["total_value"] += value
        else:
            summary["packing"]["items"].append(item)
            summary["packing"]["total_value"] += value
    
    return summary

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "Cosmetic Inventory Management System API"}

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
