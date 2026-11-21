import uuid
import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.dependencies import get_current_user, require_role
from backend.app.core.security import mask_pan, mask_gstin, mask_account_number
from backend.app.core.naming import generate_client_code, generate_proposal_code
from backend.app.models.models import (
    User, Client, Entity, Promoter, BankAccount, ExistingFacility, GSTRegistration, AuditLog
)
from backend.app.schemas.schemas import (
    ClientCreate, ClientResponse, EntityCreate, EntityResponse,
    PromoterCreate, PromoterResponse, BankAccountCreate, BankAccountResponse,
    ExistingFacilityCreate, ExistingFacilityResponse, GSTRegistrationCreate, GSTRegistrationResponse,
    CustomerOnboardRequest, CustomerOnboardResponse
)

router = APIRouter(prefix="/clients", tags=["Clients & Master Data"])

@router.get("", response_model=List[ClientResponse])
def get_clients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "client":
        clients = db.query(Client).filter(Client.id == current_user.client_id, Client.is_deleted == False).all()
    else:
        clients = db.query(Client).filter(Client.is_deleted == False).order_by(Client.created_at.desc()).all()
    return clients

@router.post("", response_model=ClientResponse)
def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    code = generate_client_code(client_in.primary_contact_name, db)
    new_client = Client(
        client_code=code,
        primary_contact_name=client_in.primary_contact_name,
        phone=client_in.phone,
        email=client_in.email,
        constitution=client_in.constitution,
        address=client_in.address,
        city=client_in.city,
        state=client_in.state,
        pin_code=client_in.pin_code,
        is_deleted=False
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        client_id=new_client.id,
        action="CREATE",
        resource_type="client",
        resource_id=new_client.id,
        details_json=f"Created client {new_client.primary_contact_name}"
    )
    db.add(audit)
    db.commit()
    return new_client

@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "client" and current_user.client_id != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.delete("/{client_id}")
def delete_client(
    client_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    client_name = client.primary_contact_name
    client_code = client.client_code

    # Clean up all linked proposal folders and cascade delete proposals
    for p in list(client.proposals):
        case_folder = os.path.join(settings.CASES_DIR, p.proposal_code)
        if os.path.exists(case_folder):
            try:
                shutil.rmtree(case_folder)
            except Exception:
                pass
        db.delete(p)

    # Soft delete the client
    client.is_deleted = True

    audit = AuditLog(
        user_id=current_user.id,
        client_id=client_id,
        action="DELETE",
        resource_type="client",
        resource_id=client_id,
        details_json=f"Deleted customer {client_name} ({client_code})"
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "message": f"Customer {client_name} deleted successfully"}

# Entities
@router.post("/{client_id}/entities", response_model=EntityResponse)
def create_entity(
    client_id: str,
    entity_in: EntityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    entity = Entity(
        client_id=client_id,
        legal_name=entity_in.legal_name,
        trade_name=entity_in.trade_name,
        constitution=entity_in.constitution,
        pan=entity_in.pan,
        pan_masked=mask_pan(entity_in.pan),
        cin=entity_in.cin,
        udyam_reg=entity_in.udyam_reg,
        date_of_incorporation=entity_in.date_of_incorporation,
        business_activity=entity_in.business_activity,
        registered_address=entity_in.registered_address
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity

# Promoters
@router.post("/entities/{entity_id}/promoters", response_model=PromoterResponse)
def add_promoter(
    entity_id: str,
    promoter_in: PromoterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
        
    promoter = Promoter(
        entity_id=entity_id,
        name=promoter_in.name,
        role=promoter_in.role,
        pan=promoter_in.pan,
        pan_masked=mask_pan(promoter_in.pan),
        din=promoter_in.din,
        ownership_pct=promoter_in.ownership_pct,
        cibil_score=promoter_in.cibil_score,
        mobile=promoter_in.mobile,
        email=promoter_in.email
    )
    db.add(promoter)
    db.commit()
    db.refresh(promoter)
    return promoter

# GST Registrations
@router.post("/entities/{entity_id}/gst", response_model=GSTRegistrationResponse)
def add_gst(
    entity_id: str,
    gst_in: GSTRegistrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
        
    gst = GSTRegistration(
        entity_id=entity_id,
        gstin=gst_in.gstin,
        gstin_masked=mask_gstin(gst_in.gstin),
        state=gst_in.state,
        status=gst_in.status,
        filing_frequency=gst_in.filing_frequency
    )
    db.add(gst)
    db.commit()
    db.refresh(gst)
    return gst

# Bank Accounts
@router.post("/entities/{entity_id}/bank-accounts", response_model=BankAccountResponse)
def add_bank_account(
    entity_id: str,
    bank_in: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
        
    bank = BankAccount(
        entity_id=entity_id,
        bank_name=bank_in.bank_name,
        branch=bank_in.branch,
        account_type=bank_in.account_type,
        account_number_masked=mask_account_number(bank_in.account_number),
        ifsc=bank_in.ifsc,
        average_monthly_balance=bank_in.average_monthly_balance,
        statement_from=bank_in.statement_from,
        statement_to=bank_in.statement_to
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank

# Existing Facilities
@router.post("/entities/{entity_id}/existing-facilities", response_model=ExistingFacilityResponse)
def add_existing_facility(
    entity_id: str,
    facility_in: ExistingFacilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
        
    facility = ExistingFacility(
        entity_id=entity_id,
        lender_name=facility_in.lender_name,
        facility_type=facility_in.facility_type,
        sanctioned_limit=facility_in.sanctioned_limit,
        outstanding_balance=facility_in.outstanding_balance,
        interest_rate=facility_in.interest_rate,
        monthly_emi=facility_in.monthly_emi,
        residual_tenure_months=facility_in.residual_tenure_months,
        primary_security=facility_in.primary_security,
        collateral_security=facility_in.collateral_security,
        sanction_date=facility_in.sanction_date,
        renewal_date=facility_in.renewal_date
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility

@router.post("/onboard", response_model=CustomerOnboardResponse)
def onboard_customer(
    req: CustomerOnboardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst"]))
):
    """
    Unified 1-Call Customer Onboarding Endpoint:
    Atomically provisions Client, Entity, Promoter, and creates an initial
    Loan Proposal pre-populated with the standard 7-column primary checklist.
    """
    from backend.app.models.models import Proposal, DocumentChecklistItem
    from backend.app.api.proposals import DEFAULT_CHECKLIST_TEMPLATE

    # 1. Create Client Record
    target_name = req.customer_name or req.primary_contact or "Client"
    client_code = generate_client_code(target_name, db)
    new_client = Client(
        client_code=client_code,
        primary_contact_name=req.primary_contact or req.customer_name,
        phone=req.phone,
        email=req.email,
        constitution=req.constitution,
        address=req.address,
        city=req.city,
        state=req.state,
        pin_code=req.pin_code,
        is_deleted=False
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    # 2. Create Entity Record
    entity = Entity(
        client_id=new_client.id,
        legal_name=req.customer_name,
        trade_name=req.customer_name,
        constitution=req.constitution,
        pan=req.pan,
        pan_masked=mask_pan(req.pan) if req.pan else None,
        date_of_incorporation=req.date_of_incorporation or "2021-04-01",
        business_activity=req.business_activity or "Commercial Enterprise / Services",
        registered_address=req.address
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)

    # 3. Add Promoter if provided
    if req.promoter_name or req.promoter_pan:
        promoter = Promoter(
            entity_id=entity.id,
            name=req.promoter_name or req.primary_contact or req.customer_name,
            role="director" if req.constitution in ["pvt_ltd", "public_ltd"] else "proprietor",
            pan=req.promoter_pan or req.pan,
            pan_masked=mask_pan(req.promoter_pan or req.pan) if (req.promoter_pan or req.pan) else None,
            ownership_pct=req.ownership_pct or 100.0,
            cibil_score=req.cibil_score or 750
        )
        db.add(promoter)
        db.commit()

    proposal_id = None
    proposal_code = None
    checklist_count = 0

    # 4. Create Initial Proposal if requested
    if req.create_proposal:
        from backend.app.core.config import get_case_dir
        proposal_code = generate_proposal_code(target_name, db)
        new_proposal = Proposal(
            proposal_code=proposal_code,
            client_id=new_client.id,
            entity_id=entity.id,
            product_type=req.product_type or "cash_credit_od",
            requested_amount=req.requested_amount or 10000000,
            tenure_months=req.tenure_months or 60,
            purpose=req.purpose or "Working capital facilities",
            target_rate=req.target_rate or 9.25,
            status="lead",
            assigned_analyst_id=current_user.id
        )
        db.add(new_proposal)
        db.commit()
        db.refresh(new_proposal)
        proposal_id = new_proposal.id

        # Ensure dedicated case-wise backend folder is created on disk
        get_case_dir(new_proposal.proposal_code)

        # Pre-populate primary document checklist items
        for item in DEFAULT_CHECKLIST_TEMPLATE:
            chk = DocumentChecklistItem(
                proposal_id=new_proposal.id,
                document_name=item["name"],
                category=item["cat"],
                is_applicable=True,
                is_received=False,
                period_required=item.get("period"),
                verification_status="requested",
                remarks=item.get("remarks")
            )
            db.add(chk)
        db.commit()
        checklist_count = len(DEFAULT_CHECKLIST_TEMPLATE)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        client_id=new_client.id,
        proposal_id=proposal_id,
        action="ONBOARD_CUSTOMER",
        resource_type="client",
        resource_id=new_client.id,
        details_json=f"Onboarded customer '{req.customer_name}' ({req.constitution}) with proposal {proposal_code}"
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "client_id": new_client.id,
        "client_code": client_code,
        "entity_id": entity.id,
        "proposal_id": proposal_id,
        "proposal_code": proposal_code,
        "checklist_count": checklist_count,
        "message": f"Successfully onboarded customer '{req.customer_name}' with proposal {proposal_code} and pre-populated checklist ({checklist_count} items)."
    }
