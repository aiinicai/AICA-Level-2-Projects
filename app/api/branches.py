from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.dependencies import require_accounts_or_admin, require_any_staff, require_admin
from app.schemas.branch import BranchSchema, BranchCreate, BranchUpdate
from app.services import master_service
from app.models.user import User

router = APIRouter(prefix="/api/branches", tags=["Branches"])

@router.get("", response_model=List[BranchSchema])
def get_all_branches(
    active_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_staff)
):
    return master_service.get_branches(db, active_only=active_only)

@router.post("", response_model=BranchSchema)
def create_new_branch(
    data: BranchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    existing = master_service.get_branch_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Branch code '{data.code}' already exists.")
    return master_service.create_branch(db, data.dict(), current_user=user)

@router.put("/{branch_id}", response_model=BranchSchema)
def update_existing_branch(
    branch_id: int,
    data: BranchUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    updated = master_service.update_branch(db, branch_id, data.dict(exclude_unset=True), current_user=user)
    if not updated:
        raise HTTPException(status_code=404, detail="Branch not found")
    return updated
