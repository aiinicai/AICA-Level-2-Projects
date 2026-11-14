from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import MasterLocation
from backend.app.schemas.schemas import (
    LocationCity, LocationCreate, PANValidationRequest, PANValidationResponse
)
from backend.app.services.pan_service import PANValidationService
from backend.app.services.location_service import INDIAN_STATES

router = APIRouter(prefix="/master", tags=["Master Data, Locations & PAN Validation"])

@router.get("/states", response_model=List[str])
def get_indian_states():
    """
    Returns the comprehensive list of Indian States and Union Territories.
    """
    return INDIAN_STATES

@router.get("/cities", response_model=List[LocationCity])
def get_cities(
    query: Optional[str] = Query(None, description="Search city name prefix or substring"),
    state: Optional[str] = Query(None, description="Filter by state"),
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Returns cities list for auto-prompt and auto-fill.
    Supports substring match across city and state names.
    """
    q = db.query(MasterLocation)
    if state and state.strip():
        q = q.filter(MasterLocation.state.ilike(f"%{state.strip()}%"))
    if query and query.strip():
        search = f"%{query.strip()}%"
        q = q.filter(
            (MasterLocation.city.ilike(search)) |
            (MasterLocation.state.ilike(search))
        )
    return q.order_by(MasterLocation.city.asc()).limit(limit).all()

@router.post("/cities", response_model=LocationCity)
def add_new_city(
    loc_in: LocationCreate,
    db: Session = Depends(get_db)
):
    """
    Allow user to add a new city/town to the master database if not prompted.
    The LOV is never restrictive; user can freely type new locations.
    """
    city_clean = loc_in.city.strip()
    state_clean = loc_in.state.strip()

    if not city_clean or not state_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="City and State are required."
        )

    existing = db.query(MasterLocation).filter(
        MasterLocation.city.ilike(city_clean),
        MasterLocation.state.ilike(state_clean)
    ).first()

    if existing:
        return existing

    new_loc = MasterLocation(
        city=city_clean,
        state=state_clean,
        tier=loc_in.tier or "tier3",
        is_custom=True
    )
    db.add(new_loc)
    db.commit()
    db.refresh(new_loc)
    return new_loc

@router.post("/pan/validate", response_model=PANValidationResponse)
def validate_pan(req: PANValidationRequest):
    """
    Rigorous Indian PAN string validation:
    1. Validates 10-char alphanumeric structure (5 letters, 4 digits, 1 letter).
    2. Validates 4th character against taxpayer category (Company 'C', Individual 'P', Firm/LLP 'F', Trust 'T', etc.).
    3. Cross-checks constitution match if supplied (e.g. Pvt Ltd requires 'C').
    4. Validates 5th character against entity surname or legal name.
    5. Returns complete verification metadata.
    """
    result = PANValidationService.validate_pan(
        pan=req.pan,
        entity_name=req.entity_name,
        constitution=req.constitution
    )
    return result
