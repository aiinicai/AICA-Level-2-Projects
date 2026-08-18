from typing import List, Optional
from datetime import datetime
import os
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    from .database import get_db, init_db, DB_PATH
    from .models import Client, GSTRecord, LedgerRecord
    from .pdf_parser import parse_gst_pdf, parse_reg06_pdf
except ImportError:
    from database import get_db, init_db, DB_PATH
    from models import Client, GSTRecord, LedgerRecord
    from pdf_parser import parse_gst_pdf, parse_reg06_pdf

# Ensure tables are initialized
init_db()

router = APIRouter()

# --- Pydantic Schemas ---
class ClientSchema(BaseModel):
    name: str
    trade_name: Optional[str] = None
    gstin: str
    status: Optional[str] = "Active"
    constitution: Optional[str] = None
    address: Optional[str] = None
    registration_date: Optional[str] = None

class UpdateClientSchema(BaseModel):
    name: Optional[str] = None
    trade_name: Optional[str] = None
    gstin: Optional[str] = None  # Frozen once created
    status: Optional[str] = None
    constitution: Optional[str] = None
    address: Optional[str] = None
    registration_date: Optional[str] = None

class CreateGSTRecordSchema(BaseModel):
    client_id: int
    return_type: str
    financial_year: str
    period: str
    turnover: float = 0.0
    tax_liability: float = 0.0
    due_date: Optional[str] = None
    actual_filing_date: Optional[str] = None
    # GSTR-1 Breakdown
    b2b_supplies: Optional[float] = 0.0
    b2c_large: Optional[float] = 0.0
    b2c_small: Optional[float] = 0.0
    exports: Optional[float] = 0.0
    nil_exempt: Optional[float] = 0.0
    cr_dr_notes: Optional[float] = 0.0
    total_tax_liability: Optional[float] = 0.0
    # GSTR-3B Breakdown
    outward_taxable_3_1_a: Optional[float] = 0.0
    inward_rcm_3_1_d: Optional[float] = 0.0
    zero_rated_3_1_b: Optional[float] = 0.0
    nil_exempt_3_1_c: Optional[float] = 0.0
    itc_available_4_a: Optional[float] = 0.0
    itc_reversed_4_b: Optional[float] = 0.0
    net_itc_4_c: Optional[float] = 0.0

class UpdateGSTRecordSchema(BaseModel):
    return_type: Optional[str] = None
    financial_year: Optional[str] = None
    period: Optional[str] = None
    turnover: Optional[float] = None
    tax_liability: Optional[float] = None
    due_date: Optional[str] = None
    actual_filing_date: Optional[str] = None
    # GSTR-1 Breakdown
    b2b_supplies: Optional[float] = None
    b2c_large: Optional[float] = None
    b2c_small: Optional[float] = None
    exports: Optional[float] = None
    nil_exempt: Optional[float] = None
    cr_dr_notes: Optional[float] = None
    total_tax_liability: Optional[float] = None
    # GSTR-3B Breakdown
    outward_taxable_3_1_a: Optional[float] = None
    inward_rcm_3_1_d: Optional[float] = None
    zero_rated_3_1_b: Optional[float] = None
    nil_exempt_3_1_c: Optional[float] = None
    itc_available_4_a: Optional[float] = None
    itc_reversed_4_b: Optional[float] = None
    net_itc_4_c: Optional[float] = None

class CreateLedgerSchema(BaseModel):
    financial_year: str = "2023-24"
    ledger_type: str  # "Cash" or "Credit"
    date: str  # YYYY-MM-DD
    description: Optional[str] = ""
    amount: float = 0.0


# ==========================================
# 1. CLIENT GATEKEEPER & MASTER DATA ENDPOINTS
# ==========================================

@router.get("/clients")
def get_clients(db: Session = Depends(get_db)):
    """Fetch all clients for the directory launchpad."""
    clients = db.query(Client).order_by(Client.created_at.desc()).all()
    return {
        "status": "success",
        "count": len(clients),
        "clients": [c.to_dict() for c in clients]
    }

@router.get("/clients/{client_id}")
def get_client(client_id: int, db: Session = Depends(get_db)):
    """Fetch a single client's profile."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"status": "success", "client": client.to_dict()}

@router.post("/clients")
def create_client(payload: ClientSchema, db: Session = Depends(get_db)):
    """Create a new client profile."""
    client = Client(
        name=payload.name.strip(),
        trade_name=(payload.trade_name or payload.name).strip(),
        gstin=payload.gstin.strip().upper(),
        status=payload.status or "Active",
        constitution=payload.constitution,
        address=payload.address,
        registration_date=payload.registration_date
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return {"status": "success", "client": client.to_dict()}

@router.put("/clients/{client_id}")
def update_client(client_id: int, payload: UpdateClientSchema, db: Session = Depends(get_db)):
    """Update a client's master details."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if payload.name is not None:
        client.name = payload.name.strip()
    if payload.trade_name is not None:
        client.trade_name = payload.trade_name.strip()
    # Note: GSTIN is frozen once created
    if payload.status is not None:
        client.status = payload.status
    if payload.constitution is not None:
        client.constitution = payload.constitution.strip()
    if payload.address is not None:
        client.address = payload.address.strip()
    if payload.registration_date is not None:
        client.registration_date = payload.registration_date.strip()

    db.commit()
    db.refresh(client)
    return {"status": "success", "client": client.to_dict()}

@router.delete("/clients/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    """Delete a client and all associated data."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    db.delete(client)
    db.commit()
    return {"status": "success", "deleted_id": client_id}


# ==========================================
# 2. MASTER DATA IMPORT (PDF REG-06 & MOCK GSP API)
# ==========================================

@router.post("/upload_reg06_pdf")
async def upload_reg06_pdf(
    client_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Parses Form GST REG-06 (Registration Certificate) PDF with strict GSTIN validation.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    contents = await file.read()
    parsed = parse_reg06_pdf(contents)

    # OBJECTIVE 1: STRICT GSTIN FREEZE VALIDATION
    extracted_gstin = parsed.get("extracted_gstin") or parsed.get("gstin")
    if extracted_gstin and extracted_gstin.strip().upper() != client.gstin.strip().upper():
        raise HTTPException(
            status_code=400,
            detail="Error: GSTIN mismatch. This document belongs to a different client."
        )

    if parsed["legal_name"]:
        client.name = parsed["legal_name"]
    if parsed["trade_name"]:
        client.trade_name = parsed["trade_name"]
    if parsed["constitution"]:
        client.constitution = parsed["constitution"]
    if parsed["address"]:
        client.address = parsed["address"]
    if parsed["registration_date"]:
        client.registration_date = parsed["registration_date"]
    client.status = "Active"

    db.commit()
    db.refresh(client)
    return {
        "status": "success",
        "message": "Master Data updated from Form GST REG-06",
        "client": client.to_dict(),
        "parsed_raw": parsed
    }

@router.get("/fetch_gstin_public/{gstin}")
def fetch_gstin_public(gstin: str):
    """Mock GSP Public API endpoint for GSTIN lookup."""
    clean_gstin = gstin.strip().upper()
    state_code = clean_gstin[:2] if len(clean_gstin) >= 2 else "27"
    state_names = {"27": "Maharashtra", "07": "Delhi", "29": "Karnataka", "09": "Uttar Pradesh", "33": "Tamil Nadu"}
    state_name = state_names.get(state_code, "Maharashtra")

    return {
        "status": "success",
        "source": "GSP Public API (OTP-Free Mock)",
        "data": {
            "gstin": clean_gstin,
            "legal_name": f"ENTERPRISE {clean_gstin[2:7]} PRIVATE LIMITED",
            "trade_name": f"{clean_gstin[2:7]} SOLUTIONS",
            "status": "Active",
            "constitution": "Private Limited Company",
            "address": f"Plot No 101, Central Business Park, Sector 4, {state_name} - {state_code}0001",
            "registration_date": "2017-07-01",
            "jurisdiction": f"State - Ward {clean_gstin[7:9]} {state_name}"
        }
    }


# ==========================================
# 3. STRICT FY-SCOPED & VALIDATED GST RECORD ENDPOINTS
# ==========================================

@router.post("/upload_pdf")
async def upload_pdf(
    client_id: int = Form(...),
    files: List[UploadFile] = File(...),
    return_type: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Parses uploaded GSTR PDFs with strict GSTIN freeze and Return Type validation.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    processed_records = []
    
    for upload in files:
        contents = await upload.read()
        parsed_data = parse_gst_pdf(contents, override_return_type=return_type)

        # OBJECTIVE 1: STRICT GSTIN FREEZE VALIDATION
        extracted_gstin = parsed_data.get("extracted_gstin")
        if extracted_gstin and extracted_gstin.strip().upper() != client.gstin.strip().upper():
            raise HTTPException(
                status_code=400,
                detail="Error: GSTIN mismatch. This document belongs to a different client."
            )

        # OBJECTIVE 1: DOCUMENT TYPE VALIDATION
        raw_text = parsed_data.get("raw_text", "").upper()
        target_type = return_type or parsed_data.get("return_type")

        if target_type == "GSTR-1":
            if "GSTR-1" not in raw_text and "FORM GSTR-1" not in raw_text and "GSTR1" not in raw_text:
                raise HTTPException(
                    status_code=400,
                    detail="Error: Wrong type of return uploaded."
                )
        elif target_type == "GSTR-3B":
            if "GSTR-3B" not in raw_text and "FORM GSTR-3B" not in raw_text and "GSTR3B" not in raw_text:
                raise HTTPException(
                    status_code=400,
                    detail="Error: Wrong type of return uploaded."
                )

        existing = db.query(GSTRecord).filter(
            GSTRecord.client_id == client_id,
            GSTRecord.return_type == parsed_data["return_type"],
            GSTRecord.period == parsed_data["period"]
        ).first()

        if existing:
            existing.financial_year = parsed_data["financial_year"]
            existing.turnover = parsed_data["turnover"]
            existing.tax_liability = parsed_data["tax_liability"]
            existing.due_date = parsed_data["due_date"]
            existing.actual_filing_date = parsed_data["actual_filing_date"]
            # Update breakdown columns
            existing.b2b_supplies = parsed_data["b2b_supplies"]
            existing.b2c_large = parsed_data["b2c_large"]
            existing.b2c_small = parsed_data["b2c_small"]
            existing.exports = parsed_data["exports"]
            existing.nil_exempt = parsed_data["nil_exempt"]
            existing.cr_dr_notes = parsed_data["cr_dr_notes"]
            existing.total_tax_liability = parsed_data["total_tax_liability"]
            existing.outward_taxable_3_1_a = parsed_data["outward_taxable_3_1_a"]
            existing.inward_rcm_3_1_d = parsed_data["inward_rcm_3_1_d"]
            existing.zero_rated_3_1_b = parsed_data["zero_rated_3_1_b"]
            existing.nil_exempt_3_1_c = parsed_data["nil_exempt_3_1_c"]
            existing.itc_available_4_a = parsed_data["itc_available_4_a"]
            existing.itc_reversed_4_b = parsed_data["itc_reversed_4_b"]
            existing.net_itc_4_c = parsed_data["net_itc_4_c"]

            db.commit()
            db.refresh(existing)
            processed_records.append(existing.to_dict())
        else:
            new_record = GSTRecord(
                client_id=client_id,
                return_type=parsed_data["return_type"],
                financial_year=parsed_data["financial_year"],
                period=parsed_data["period"],
                turnover=parsed_data["turnover"],
                tax_liability=parsed_data["tax_liability"],
                due_date=parsed_data["due_date"],
                actual_filing_date=parsed_data["actual_filing_date"],
                is_edited=False,
                b2b_supplies=parsed_data["b2b_supplies"],
                b2c_large=parsed_data["b2c_large"],
                b2c_small=parsed_data["b2c_small"],
                exports=parsed_data["exports"],
                nil_exempt=parsed_data["nil_exempt"],
                cr_dr_notes=parsed_data["cr_dr_notes"],
                total_tax_liability=parsed_data["total_tax_liability"],
                outward_taxable_3_1_a=parsed_data["outward_taxable_3_1_a"],
                inward_rcm_3_1_d=parsed_data["inward_rcm_3_1_d"],
                zero_rated_3_1_b=parsed_data["zero_rated_3_1_b"],
                nil_exempt_3_1_c=parsed_data["nil_exempt_3_1_c"],
                itc_available_4_a=parsed_data["itc_available_4_a"],
                itc_reversed_4_b=parsed_data["itc_reversed_4_b"],
                net_itc_4_c=parsed_data["net_itc_4_c"]
            )
            db.add(new_record)
            db.commit()
            db.refresh(new_record)
            processed_records.append(new_record.to_dict())

    return {
        "status": "success",
        "count": len(processed_records),
        "records": processed_records
    }

@router.get("/records")
def get_records(
    client_id: int = Query(...),
    financial_year: str = Query(...),
    return_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Fetch GST records strictly filtered by client_id AND financial_year."""
    query = db.query(GSTRecord).filter(
        GSTRecord.client_id == client_id,
        GSTRecord.financial_year == financial_year
    )
    if return_type and return_type != "All":
        query = query.filter(GSTRecord.return_type == return_type)

    records = query.order_by(GSTRecord.period.desc()).all()
    return {
        "status": "success",
        "client_id": client_id,
        "financial_year": financial_year,
        "count": len(records),
        "records": [r.to_dict() for r in records]
    }

@router.post("/records")
def create_record(payload: CreateGSTRecordSchema, db: Session = Depends(get_db)):
    """Manually add a new GST record with full breakdown fields."""
    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    record = GSTRecord(
        client_id=payload.client_id,
        return_type=payload.return_type,
        financial_year=payload.financial_year,
        period=payload.period,
        turnover=payload.turnover,
        tax_liability=payload.tax_liability,
        due_date=payload.due_date,
        actual_filing_date=payload.actual_filing_date,
        is_edited=False,
        b2b_supplies=payload.b2b_supplies or 0.0,
        b2c_large=payload.b2c_large or 0.0,
        b2c_small=payload.b2c_small or 0.0,
        exports=payload.exports or 0.0,
        nil_exempt=payload.nil_exempt or 0.0,
        cr_dr_notes=payload.cr_dr_notes or 0.0,
        total_tax_liability=payload.total_tax_liability or payload.tax_liability or 0.0,
        outward_taxable_3_1_a=payload.outward_taxable_3_1_a or payload.turnover or 0.0,
        inward_rcm_3_1_d=payload.inward_rcm_3_1_d or 0.0,
        zero_rated_3_1_b=payload.zero_rated_3_1_b or 0.0,
        nil_exempt_3_1_c=payload.nil_exempt_3_1_c or 0.0,
        itc_available_4_a=payload.itc_available_4_a or 0.0,
        itc_reversed_4_b=payload.itc_reversed_4_b or 0.0,
        net_itc_4_c=payload.net_itc_4_c or 0.0
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"status": "success", "record": record.to_dict()}

@router.put("/records/{record_id}")
def update_record(record_id: int, payload: UpdateGSTRecordSchema, db: Session = Depends(get_db)):
    """Updates a GST record and sets is_edited = True."""
    record = db.query(GSTRecord).filter(GSTRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="GST record not found")

    if payload.return_type is not None:
        record.return_type = payload.return_type
    if payload.financial_year is not None:
        record.financial_year = payload.financial_year
    if payload.period is not None:
        record.period = payload.period
    if payload.turnover is not None:
        record.turnover = payload.turnover
    if payload.tax_liability is not None:
        record.tax_liability = payload.tax_liability
    if payload.due_date is not None:
        record.due_date = payload.due_date
    if payload.actual_filing_date is not None:
        record.actual_filing_date = payload.actual_filing_date

    # GSTR-1 Breakdown Updates
    if payload.b2b_supplies is not None:
        record.b2b_supplies = payload.b2b_supplies
    if payload.b2c_large is not None:
        record.b2c_large = payload.b2c_large
    if payload.b2c_small is not None:
        record.b2c_small = payload.b2c_small
    if payload.exports is not None:
        record.exports = payload.exports
    if payload.nil_exempt is not None:
        record.nil_exempt = payload.nil_exempt
    if payload.cr_dr_notes is not None:
        record.cr_dr_notes = payload.cr_dr_notes
    if payload.total_tax_liability is not None:
        record.total_tax_liability = payload.total_tax_liability

    # GSTR-3B Breakdown Updates
    if payload.outward_taxable_3_1_a is not None:
        record.outward_taxable_3_1_a = payload.outward_taxable_3_1_a
    if payload.inward_rcm_3_1_d is not None:
        record.inward_rcm_3_1_d = payload.inward_rcm_3_1_d
    if payload.zero_rated_3_1_b is not None:
        record.zero_rated_3_1_b = payload.zero_rated_3_1_b
    if payload.nil_exempt_3_1_c is not None:
        record.nil_exempt_3_1_c = payload.nil_exempt_3_1_c
    if payload.itc_available_4_a is not None:
        record.itc_available_4_a = payload.itc_available_4_a
    if payload.itc_reversed_4_b is not None:
        record.itc_reversed_4_b = payload.itc_reversed_4_b
    if payload.net_itc_4_c is not None:
        record.net_itc_4_c = payload.net_itc_4_c

    record.is_edited = True

    db.commit()
    db.refresh(record)
    return {"status": "success", "record": record.to_dict()}

@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    """Deletes a GST record."""
    record = db.query(GSTRecord).filter(GSTRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="GST record not found")
    db.delete(record)
    db.commit()
    return {"status": "success", "deleted_id": record_id}


# ==========================================
# 4. STRICT FY-SCOPED DASHBOARDS
# ==========================================

@router.get("/dashboard/comparison")
def get_comparison_dashboard(
    client_id: int = Query(...),
    financial_year: str = Query(...),
    db: Session = Depends(get_db)
):
    """Month-by-month GSTR-1 vs GSTR-3B comparison."""
    records = db.query(GSTRecord).filter(
        GSTRecord.client_id == client_id,
        GSTRecord.financial_year == financial_year
    ).all()
    
    periods_dict = {}
    for r in records:
        p = r.period
        if p not in periods_dict:
            periods_dict[p] = {"gstr1": None, "gstr3b": None}
        if r.return_type == "GSTR-1":
            periods_dict[p]["gstr1"] = r
        elif r.return_type == "GSTR-3B":
            periods_dict[p]["gstr3b"] = r

    comparison_list = []
    for period, data in sorted(periods_dict.items()):
        g1 = data["gstr1"]
        g3 = data["gstr3b"]

        t1 = g1.turnover if g1 else 0.0
        t3 = g3.turnover if g3 else 0.0
        t_diff = round(t1 - t3, 2)

        l1 = g1.tax_liability if g1 else 0.0
        l3 = g3.tax_liability if g3 else 0.0
        l_diff = round(l1 - l3, 2)

        is_match = (t_diff == 0.0) and (l_diff == 0.0) and (g1 is not None and g3 is not None)
        status = "Match" if is_match else ("Mismatch" if (g1 and g3) else "Pending Import")

        comparison_list.append({
            "period": period,
            "gstr1_turnover": t1,
            "gstr3b_turnover": t3,
            "turnover_diff": t_diff,
            "gstr1_liability": l1,
            "gstr3b_liability": l3,
            "liability_diff": l_diff,
            "has_gstr1": g1 is not None,
            "has_gstr3b": g3 is not None,
            "status": status
        })

    return {
        "status": "success",
        "financial_year": financial_year,
        "count": len(comparison_list),
        "comparison": comparison_list
    }

@router.get("/dashboard/filing")
def get_filing_dashboard(
    client_id: int = Query(...),
    financial_year: str = Query(...),
    db: Session = Depends(get_db)
):
    """Calculates delayed returns and compliance for a specific client AND financial_year."""
    records = db.query(GSTRecord).filter(
        GSTRecord.client_id == client_id,
        GSTRecord.financial_year == financial_year
    ).order_by(GSTRecord.period.desc()).all()

    total_filed = len(records)
    total_delayed = 0
    filing_list = []

    for r in records:
        status = "Data Not Available"
        days_delayed = 0

        if r.due_date and r.actual_filing_date:
            try:
                due_d = datetime.strptime(r.due_date, "%Y-%m-%d")
                actual_d = datetime.strptime(r.actual_filing_date, "%Y-%m-%d")
                delta = (actual_d - due_d).days
                if delta > 0:
                    status = "Delayed"
                    days_delayed = delta
                    total_delayed += 1
                else:
                    status = "On-Time"
            except Exception:
                status = "On-Time"

        filing_list.append({
            "id": r.id,
            "period": r.period,
            "return_type": r.return_type,
            "due_date": r.due_date or "N/A",
            "actual_filing_date": r.actual_filing_date or "N/A",
            "status": status,
            "days_delayed": days_delayed,
            "is_edited": r.is_edited
        })

    summary_msg = f"{total_delayed} out of {total_filed} returns filed have been delayed for {financial_year}." if total_filed > 0 else f"No GST returns filed yet for {financial_year}."

    return {
        "status": "success",
        "financial_year": financial_year,
        "summary": {
            "total_filed": total_filed,
            "total_delayed": total_delayed,
            "message": summary_msg
        },
        "filing_compliance": filing_list
    }


# ==========================================
# 5. SCOPED ELECTRONIC LEDGERS
# ==========================================

@router.get("/ledgers/{client_id}")
def get_client_ledgers(
    client_id: int,
    financial_year: str = Query("2023-24"),
    db: Session = Depends(get_db)
):
    """Fetch Cash and Credit ledger records for a client scoped by FY."""
    ledgers = db.query(LedgerRecord).filter(
        LedgerRecord.client_id == client_id,
        LedgerRecord.financial_year == financial_year
    ).order_by(LedgerRecord.date.desc()).all()

    total_cash = sum(l.amount for l in ledgers if l.ledger_type == "Cash")
    total_credit = sum(l.amount for l in ledgers if l.ledger_type == "Credit")

    return {
        "status": "success",
        "financial_year": financial_year,
        "total_cash": round(total_cash, 2),
        "total_credit": round(total_credit, 2),
        "count": len(ledgers),
        "ledgers": [l.to_dict() for l in ledgers]
    }

@router.post("/ledgers/{client_id}")
def create_ledger_entry(client_id: int, payload: CreateLedgerSchema, db: Session = Depends(get_db)):
    """Add a new Cash or Credit ledger record."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    ledger = LedgerRecord(
        client_id=client_id,
        financial_year=payload.financial_year,
        ledger_type=payload.ledger_type,
        date=payload.date,
        description=payload.description or f"{payload.ledger_type} Ledger Entry",
        amount=payload.amount
    )
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    return {"status": "success", "ledger": ledger.to_dict()}

@router.delete("/ledgers/{ledger_id}")
def delete_ledger_entry(ledger_id: int, db: Session = Depends(get_db)):
    """Delete a ledger record."""
    ledger = db.query(LedgerRecord).filter(LedgerRecord.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger record not found")

    db.delete(ledger)
    db.commit()
    return {"status": "success", "deleted_id": ledger_id}


# ==========================================
# 6. SETTINGS ENDPOINT
# ==========================================

@router.get("/settings/{client_id}")
def get_client_settings(client_id: int, db: Session = Depends(get_db)):
    """Returns database repository absolute path and client statistics."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    g1_count = db.query(GSTRecord).filter(GSTRecord.client_id == client_id, GSTRecord.return_type == "GSTR-1").count()
    g3_count = db.query(GSTRecord).filter(GSTRecord.client_id == client_id, GSTRecord.return_type == "GSTR-3B").count()
    ledger_count = db.query(LedgerRecord).filter(LedgerRecord.client_id == client_id).count()

    db_size = 0
    if DB_PATH.exists():
        db_size = DB_PATH.stat().st_size

    # OBJECTIVE 4: DESCENDING FY LIST
    supported_fys = ["2025-26", "2024-25", "2023-24", "2022-23", "2021-22"]

    return {
        "status": "success",
        "client": client.to_dict(),
        "financial_years": supported_fys,
        "database_repository": {
            "absolute_path": str(DB_PATH.resolve()),
            "file_name": DB_PATH.name,
            "size_bytes": db_size,
            "size_formatted": f"{db_size / 1024:.2f} KB" if db_size < 1048576 else f"{db_size / 1048576:.2f} MB"
        },
        "stats": {
            "gstr1_records": g1_count,
            "gstr3b_records": g3_count,
            "total_gst_records": g1_count + g3_count,
            "ledger_entries": ledger_count
        }
    }
