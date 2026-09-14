import os
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from database import engine, Base, get_db, check_db_health
import models
import schemas

from services.excel_parser import (
    load_sample_dataset, parse_trial_balance, parse_ar_ageing,
    parse_ap_ageing, parse_cwip_ageing, parse_related_parties,
    parse_borrowings, parse_contingencies, get_sample_file_path
)
from services.mapping_engine import auto_map_ledgers, apply_auto_mapping, save_manual_override, suggest_mapping_rule
from services.fs_generator import generate_financial_statements
from services.notes_engine import generate_or_update_notes
from services.accounting_policies_engine import generate_or_update_accounting_policies
from services.cash_flow_engine import generate_cash_flow_statement, get_cash_flow_validations
from services.ratio_engine import calculate_ratios
from services.validation_engine import run_validation_checks
from services.export_service import export_formula_linked_excel, export_pdf_review_pack
from services.word_export_service import export_word_financial_report
from services.auth_service import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin, seed_default_users, ROLES
)
from datetime import datetime

# Create database tables & seed initial users
try:
    models.Base.metadata.create_all(bind=engine)
    db_init = next(get_db())
    seed_default_users(db_init)
except Exception as e:
    print(f"Database initialization warning: {e}")

app = FastAPI(
    title="SW India - FS Builder Lite v0.2 API",
    description="Schedule III Division I Financial Statement Generator and Audit Pack System",

    version="0.2.0"
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://192.168.1.78:5173",
        "http://192.168.1.4:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"http://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_data")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)


@app.on_event("startup")
async def startup_event():
    print("API running at http://127.0.0.1:8000")
    print("Health endpoint available at /health")
    print("Auth endpoint available at /auth/login")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/health")
def system_health_check():
    db_health = check_db_health()
    return {
        "status": "online",
        "app": "FS Builder Lite v0.2",
        "database": db_health
    }


@app.get("/api/health/db")
def db_health_check():
    return check_db_health()

os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)


@app.get("/")
def read_root():
    return {
        "app_name": "FS Builder Lite v0.2",
        "firm": "SW INDIA | Chartered Accountants",
        "status": "Operational",
        "confidentiality": "Localhost - Zero Cloud Data Egress"
    }


# -------------------------------------------------------------
# CLIENT ENTITY MANAGEMENT ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/clients", response_model=List[schemas.ClientResponse])
def get_clients(db: Session = Depends(get_db)):
    return db.query(models.Client).all()


@app.post("/api/clients", response_model=schemas.ClientResponse)
def create_client(client: schemas.ClientCreate, db: Session = Depends(get_db)):
    db_client = models.Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)

    # Pre-populate sample notes and policies
    generate_or_update_accounting_policies(db_client.id, db)
    generate_or_update_notes(db_client.id, db)
    return db_client


@app.get("/api/clients/{client_id}", response_model=schemas.ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@app.post("/api/clients/{client_id}/load-sample-data")
def load_sample_data_endpoint(client_id: int, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    load_sample_dataset(client_id, SAMPLE_DIR, db)
    auto_map_ledgers(client_id, db)
    generate_or_update_accounting_policies(client_id, db)
    generate_or_update_notes(client_id, db)
    return {"status": "success", "message": "Sample trial balance and supporting schedules loaded successfully"}


# -------------------------------------------------------------
# UPLOAD CENTER ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/sample-templates/{file_type}")
def get_sample_template(file_type: str):
    path = get_sample_file_path(SAMPLE_DIR, file_type)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Template file not found")
    filename = os.path.basename(path)
    return FileResponse(path=path, filename=filename)


@app.post("/api/upload/trial-balance/{client_id}")
def upload_tb(client_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOADS_DIR, f"tb_{client_id}_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file.file.read())

    lines = parse_trial_balance(client_id, filepath, db)
    auto_map_ledgers(client_id, db)
    return {"status": "success", "count": len(lines)}


@app.post("/api/upload/ar-ageing/{client_id}")
def upload_ar(client_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOADS_DIR, f"ar_{client_id}_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return parse_ar_ageing(client_id, filepath, db)


@app.post("/api/upload/ap-ageing/{client_id}")
def upload_ap(client_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOADS_DIR, f"ap_{client_id}_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return parse_ap_ageing(client_id, filepath, db)


@app.post("/api/upload/cwip-ageing/{client_id}")
def upload_cwip(client_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOADS_DIR, f"cwip_{client_id}_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return parse_cwip_ageing(client_id, filepath, db)


@app.post("/api/upload/related-parties/{client_id}")
def upload_rpt(client_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOADS_DIR, f"rpt_{client_id}_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return parse_related_parties(client_id, filepath, db)


@app.post("/api/upload/borrowings/{client_id}")
def upload_borrowings(client_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOADS_DIR, f"bor_{client_id}_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return parse_borrowings(client_id, filepath, db)


@app.post("/api/upload/contingencies/{client_id}")
def upload_contingencies(client_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    filepath = os.path.join(UPLOADS_DIR, f"cont_{client_id}_{file.filename}")
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return parse_contingencies(client_id, filepath, db)


# -------------------------------------------------------------
# LEDGER MAPPING & RULE STUDIO ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/mapping/{client_id}", response_model=List[schemas.TrialBalanceLineSchema])
def get_mapping(client_id: int, db: Session = Depends(get_db)):
    lines = db.query(models.TrialBalanceLine).filter(models.TrialBalanceLine.client_id == client_id).all()
    if not lines:
        return []
    return lines


@app.post("/api/mapping/auto-map/{client_id}")
def auto_map_endpoint(client_id: int, db: Session = Depends(get_db)):
    lines = apply_auto_mapping(client_id, db)
    return {"status": "success", "mapped_count": len(lines)}


@app.put("/api/mapping/update")
def update_mapping_endpoint(req: schemas.MappingUpdateRequest, db: Session = Depends(get_db)):
    return save_manual_override(
        line_id=req.id,
        final_cls=req.final_classification,
        statement=req.financial_statement,
        note_num=req.note_number,
        cur_non_cur=req.current_non_current,
        db=db
    )


@app.get("/api/rules")
def get_rules(db: Session = Depends(get_db)):
    return db.query(models.MappingRule).all()


@app.post("/api/rules")
def create_rule(rule: schemas.RuleCreateRequest, db: Session = Depends(get_db)):
    db_rule = models.MappingRule(**rule.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


@app.post("/api/rules/test")
def test_rule(ledger_name: str, original_group: str = "", db: Session = Depends(get_db)):
    return suggest_mapping_rule(ledger_name, original_group, db)


# -------------------------------------------------------------
# FINANCIAL STATEMENTS & NOTES ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/financial-statements/{client_id}", response_model=schemas.FinancialStatementResponse)
def get_financial_statements_api(client_id: int, db: Session = Depends(get_db)):
    return generate_financial_statements(client_id, db)


@app.get("/api/notes/{client_id}", response_model=List[schemas.NoteSchema])
def get_notes_api(client_id: int, db: Session = Depends(get_db)):
    return generate_or_update_notes(client_id, db)


@app.put("/api/notes/{note_id}")
def update_note_api(note_id: int, req: schemas.NoteUpdateRequest, db: Session = Depends(get_db)):
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.content = req.content
    note.is_modified = True
    db.commit()
    return note


@app.post("/api/notes/{note_id}/reset")
def reset_note_api(note_id: int, db: Session = Depends(get_db)):
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.content = note.suggested_content
    note.is_modified = False
    db.commit()
    return note


@app.post("/api/notes/{client_id}/regenerate")
def regenerate_notes_api(client_id: int, db: Session = Depends(get_db)):
    notes = generate_or_update_notes(client_id, db)
    return {"status": "success", "count": len(notes), "message": "All notes regenerated from current trial balance data"}


@app.post("/api/financial-statements/{client_id}/refresh")
def refresh_financial_statements_api(client_id: int, db: Session = Depends(get_db)):
    fs = generate_financial_statements(client_id, db)
    generate_or_update_notes(client_id, db)
    return {"status": "success", "is_tallied": fs.is_tallied, "difference": fs.difference}



# -------------------------------------------------------------
# ACCOUNTING POLICIES ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/accounting-policies/{client_id}", response_model=List[schemas.AccountingPolicySchema])
def get_accounting_policies_api(client_id: int, db: Session = Depends(get_db)):
    return generate_or_update_accounting_policies(client_id, db)


@app.put("/api/accounting-policies/{policy_id}")
def update_accounting_policy_api(policy_id: int, req: schemas.AccountingPolicyUpdateRequest, db: Session = Depends(get_db)):
    pol = db.query(models.AccountingPolicy).filter(models.AccountingPolicy.id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail="Accounting Policy not found")
    pol.content = req.content
    pol.is_modified = True
    db.commit()
    return pol


@app.post("/api/accounting-policies/{policy_id}/reset")
def reset_accounting_policy_api(policy_id: int, db: Session = Depends(get_db)):
    pol = db.query(models.AccountingPolicy).filter(models.AccountingPolicy.id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail="Accounting Policy not found")
    pol.content = pol.suggested_content
    pol.is_modified = False
    db.commit()
    return pol


@app.put("/api/accounting-policies/{policy_id}/toggle-applicability")
def toggle_accounting_policy_applicability(policy_id: int, req: schemas.AccountingPolicyToggleRequest, db: Session = Depends(get_db)):
    pol = db.query(models.AccountingPolicy).filter(models.AccountingPolicy.id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail="Accounting Policy not found")
    pol.is_applicable = req.is_applicable
    db.commit()
    return {"status": "success", "message": f"Policy applicability set to {pol.is_applicable}"}


# -------------------------------------------------------------
# AS 3 CASH FLOW STATEMENT ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/cash-flow/{client_id}", response_model=schemas.CashFlowResponse)
def get_cash_flow_api(client_id: int, db: Session = Depends(get_db)):
    return generate_cash_flow_statement(client_id, db)


@app.get("/api/cash-flow/adjustments/{client_id}", response_model=List[schemas.CashFlowAdjustmentSchema])
def get_cash_flow_adjustments_api(client_id: int, db: Session = Depends(get_db)):
    return db.query(models.CashFlowAdjustment).filter(models.CashFlowAdjustment.client_id == client_id).all()


@app.post("/api/cash-flow/adjustments/{client_id}", response_model=schemas.CashFlowAdjustmentSchema)
def create_cash_flow_adjustment_api(client_id: int, req: schemas.CashFlowAdjustmentCreate, db: Session = Depends(get_db)):
    adj = models.CashFlowAdjustment(client_id=client_id, **req.dict())
    db.add(adj)
    db.commit()
    db.refresh(adj)
    return adj


@app.get("/api/cash-flow/validations/{client_id}")
def get_cash_flow_validations_api(client_id: int, db: Session = Depends(get_db)):
    return get_cash_flow_validations(client_id, db)


# -------------------------------------------------------------
# SUPPORTING SCHEDULES GETTERS
# -------------------------------------------------------------
@app.get("/api/schedules/{client_id}")
def get_supporting_schedules(client_id: int, db: Session = Depends(get_db)):
    def to_dict(obj):
        d = {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        return d

    return {
        "ar":            [to_dict(r) for r in db.query(models.ARAgeing).filter(models.ARAgeing.client_id == client_id).all()],
        "ap":            [to_dict(r) for r in db.query(models.APAgeing).filter(models.APAgeing.client_id == client_id).all()],
        "cwip":          [to_dict(r) for r in db.query(models.CWIPAgeing).filter(models.CWIPAgeing.client_id == client_id).all()],
        "rpt":           [to_dict(r) for r in db.query(models.RelatedParty).filter(models.RelatedParty.client_id == client_id).all()],
        "borrowings":    [to_dict(r) for r in db.query(models.Borrowing).filter(models.Borrowing.client_id == client_id).all()],
        "contingencies": [to_dict(r) for r in db.query(models.Contingency).filter(models.Contingency.client_id == client_id).all()],
    }


# -------------------------------------------------------------
# RATIOS & VALIDATION ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/ratios/{client_id}", response_model=List[schemas.RatioItem])
def get_ratios_api(client_id: int, db: Session = Depends(get_db)):
    return calculate_ratios(client_id, db)


@app.get("/api/validations/{client_id}", response_model=List[schemas.ValidationItem])
def get_validations_api(client_id: int, db: Session = Depends(get_db)):
    return run_validation_checks(client_id, db)


# -------------------------------------------------------------
# EXPORT REPORTS ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/export/excel/{client_id}")
def export_excel_api(client_id: int, db: Session = Depends(get_db)):
    path = export_formula_linked_excel(client_id, EXPORTS_DIR, db)
    filename = os.path.basename(path)
    return FileResponse(path=path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/export/pdf/{client_id}")
def export_pdf_api(client_id: int, db: Session = Depends(get_db)):
    path = export_pdf_review_pack(client_id, EXPORTS_DIR, db)
    filename = os.path.basename(path)
    return FileResponse(path=path, filename=filename, media_type="application/pdf")


@app.get("/api/export/word/{client_id}")
def export_word_api(client_id: int, db: Session = Depends(get_db)):
    path = export_word_financial_report(client_id, EXPORTS_DIR, db)
    filename = os.path.basename(path)
    return FileResponse(path=path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


# -------------------------------------------------------------
# USER MANAGEMENT & AUTHENTICATION ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/users/roles")
def get_user_roles():
    return {"roles": ROLES}


@app.post("/auth/login", response_model=schemas.TokenResponse)
@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login_api(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    login_str = req.login_id.strip()
    user = db.query(models.User).filter(
        (models.User.email.ilike(login_str)) | (models.User.employee_code.ilike(login_str))
    ).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Employee Code / Email or Password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Please contact your System Administrator."
        )

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_seconds": 1800,  # 30 Minutes
        "user": user
    }


@app.post("/api/auth/logout")
def logout_api(current_user: models.User = Depends(get_current_user)):
    return {"status": "success", "message": f"User {current_user.name} logged out successfully"}


@app.get("/api/auth/me", response_model=schemas.UserSchema)
def get_current_user_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/api/auth/change-password")
def change_password_api(
    req: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"status": "success", "message": "Password changed successfully"}


@app.post("/api/auth/reset-password")
def reset_password_api(
    req: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"status": "success", "message": f"Password for user {user.name} reset successfully"}


@app.get("/api/users", response_model=List[schemas.UserSchema])
def list_users_api(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.User).order_by(models.User.id).all()


@app.post("/api/users", response_model=schemas.UserSchema)
def create_user_api(
    req: schemas.UserCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    # Check duplicate employee code or email
    if db.query(models.User).filter(models.User.employee_code.ilike(req.employee_code)).first():
        raise HTTPException(status_code=400, detail=f"Employee Code '{req.employee_code}' already exists")

    if db.query(models.User).filter(models.User.email.ilike(req.email)).first():
        raise HTTPException(status_code=400, detail=f"Email '{req.email}' already exists")

    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(ROLES)}")

    new_user = models.User(
        employee_code=req.employee_code.upper().strip(),
        name=req.name.strip(),
        email=req.email.lower().strip(),
        mobile=req.mobile.strip() if req.mobile else None,
        department=req.department.strip(),
        role=req.role,
        hashed_password=hash_password(req.password),
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.put("/api/users/{user_id}", response_model=schemas.UserSchema)
def update_user_api(
    user_id: int,
    req: schemas.UserUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.name is not None:
        user.name = req.name.strip()
    if req.email is not None:
        user.email = req.email.lower().strip()
    if req.mobile is not None:
        user.mobile = req.mobile.strip()
    if req.department is not None:
        user.department = req.department.strip()
    if req.role is not None:
        if req.role not in ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role")
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active

    db.commit()
    db.refresh(user)
    return user


@app.delete("/api/users/{user_id}")
def delete_user_api(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own active administrator account")

    user.is_active = False
    db.commit()
    return {"status": "success", "message": f"User {user.name} deactivated successfully"}



# --- METADATA & SIGNATURE CONTROLS ---

class ClientMetadataSchema(BaseModel):
    client_name: str
    cin_number: str = None
    financial_year_ended: str = None

@app.post("/api/client-metadata/{client_id}")
def update_client_metadata(client_id: int, meta: ClientMetadataSchema, db: Session = Depends(get_db)):
    db_meta = db.query(models.ClientMetadata).filter_by(client_id=client_id).first()
    if not db_meta:
        db_meta = models.ClientMetadata(client_id=client_id, **meta.dict())
        db.add(db_meta)
    else:
        for k, v in meta.dict().items():
            setattr(db_meta, k, v)
    
    # Update master client name as well for fallback
    client = db.query(models.Client).filter_by(id=client_id).first()
    if client:
        client.name = meta.client_name
        
    db.commit()
    return {"status": "success"}

@app.get("/api/client-metadata/{client_id}")
def get_client_metadata(client_id: int, db: Session = Depends(get_db)):
    db_meta = db.query(models.ClientMetadata).filter_by(client_id=client_id).first()
    if not db_meta:
        client = db.query(models.Client).filter_by(id=client_id).first()
        return {"client_name": client.name if client else "", "cin_number": "", "financial_year_ended": ""}
    return {
        "client_name": db_meta.client_name,
        "cin_number": db_meta.cin_number,
        "financial_year_ended": db_meta.financial_year_ended
    }

class DirectorSchema(BaseModel):
    name: str
    designation: str
    din: str = None

@app.post("/api/client-metadata/{client_id}/directors")
def update_directors(client_id: int, directors: list[DirectorSchema], db: Session = Depends(get_db)):
    db.query(models.DirectorMaster).filter_by(client_id=client_id).delete()
    for d in directors:
        db.add(models.DirectorMaster(client_id=client_id, **d.dict()))
    db.commit()
    return {"status": "success"}

@app.get("/api/client-metadata/{client_id}/directors")
def get_directors(client_id: int, db: Session = Depends(get_db)):
    dirs = db.query(models.DirectorMaster).filter_by(client_id=client_id).all()
    return [{"name": d.name, "designation": d.designation, "din": d.din} for d in dirs]

class CSSchema(BaseModel):
    name: str
    membership_no: str = None

@app.post("/api/client-metadata/{client_id}/cs")
def update_cs(client_id: int, cs: CSSchema, db: Session = Depends(get_db)):
    db.query(models.CompanySecretary).filter_by(client_id=client_id).delete()
    if cs.name:
        db.add(models.CompanySecretary(client_id=client_id, **cs.dict()))
    db.commit()
    return {"status": "success"}

@app.get("/api/client-metadata/{client_id}/cs")
def get_cs(client_id: int, db: Session = Depends(get_db)):
    cs = db.query(models.CompanySecretary).filter_by(client_id=client_id).first()
    return {"name": cs.name, "membership_no": cs.membership_no} if cs else None

class CFOSchema(BaseModel):
    name: str

@app.post("/api/client-metadata/{client_id}/cfo")
def update_cfo(client_id: int, cfo: CFOSchema, db: Session = Depends(get_db)):
    db.query(models.ChiefFinancialOfficer).filter_by(client_id=client_id).delete()
    if cfo.name:
        db.add(models.ChiefFinancialOfficer(client_id=client_id, **cfo.dict()))
    db.commit()
    return {"status": "success"}

@app.get("/api/client-metadata/{client_id}/cfo")
def get_cfo(client_id: int, db: Session = Depends(get_db)):
    cfo = db.query(models.ChiefFinancialOfficer).filter_by(client_id=client_id).first()
    return {"name": cfo.name} if cfo else None

class AdditionalDisclosureSchema(BaseModel):
    title: str
    content: str
    insert_after_note: str
    sequence_no: int

@app.post("/api/additional-disclosures/{client_id}")
def add_additional_disclosure(client_id: int, disc: AdditionalDisclosureSchema, db: Session = Depends(get_db)):
    db.add(models.AdditionalDisclosure(client_id=client_id, **disc.dict()))
    db.commit()
    return {"status": "success"}

@app.get("/api/additional-disclosures/{client_id}")
def get_additional_disclosures(client_id: int, db: Session = Depends(get_db)):
    discs = db.query(models.AdditionalDisclosure).filter_by(client_id=client_id).order_by(models.AdditionalDisclosure.sequence_no).all()
    return [{"id": d.disclosure_id, "title": d.title, "content": d.content, "insert_after_note": d.insert_after_note, "sequence_no": d.sequence_no} for d in discs]

@app.delete("/api/additional-disclosures/{client_id}/{disc_id}")
def delete_additional_disclosure(client_id: int, disc_id: int, db: Session = Depends(get_db)):
    db.query(models.AdditionalDisclosure).filter_by(disclosure_id=disc_id, client_id=client_id).delete()
    db.commit()
    return {"status": "success"}


# --- CUSTOM RULES ---

from pydantic import BaseModel

class CustomRuleSchema(BaseModel):
    rule_name: str
    rule_type: str
    condition_field: str
    operator: str
    condition_value: str
    output_value: str
    note_number: str = None
    statement: str = None
    severity: str = None
    priority: int = 10
    is_active: bool = True

@app.post("/api/rules/{client_id}")
def create_rule(client_id: int, rule: CustomRuleSchema, db: Session = Depends(get_db)):
    db_rule = models.CustomRule(client_id=client_id, **rule.dict())
    db.add(db_rule)
    db.commit()
    return {"status": "success", "rule_id": db_rule.rule_id}

@app.get("/api/rules/{client_id}")
def get_rules(client_id: int, db: Session = Depends(get_db)):
    rules = db.query(models.CustomRule).filter((models.CustomRule.client_id == client_id) | (models.CustomRule.client_id == None)).order_by(models.CustomRule.priority).all()
    return rules

@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: int, rule: CustomRuleSchema, db: Session = Depends(get_db)):
    db.query(models.CustomRule).filter_by(rule_id=rule_id).update(rule.dict())
    db.commit()
    return {"status": "success"}

@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    db.query(models.CustomRule).filter_by(rule_id=rule_id).delete()
    db.commit()
    return {"status": "success"}

@app.post("/api/rules/{rule_id}/toggle")
def toggle_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(models.CustomRule).filter_by(rule_id=rule_id).first()
    if rule:
        rule.is_active = not rule.is_active
        db.commit()
    return {"status": "success"}

# --- PDF EXPORT OVERRIDE ---
from services.pdf_export_service import export_pdf_financial_report

@app.get("/api/export/pdf/{client_id}")
def export_pdf(client_id: int, db: Session = Depends(get_db)):
    try:
        export_dir = os.path.join(os.getcwd(), "exports")
        filepath = export_pdf_financial_report(client_id, export_dir, db)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="PDF generation failed to write file")
        return FileResponse(
            filepath,
            media_type='application/pdf',
            filename=os.path.basename(filepath)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
