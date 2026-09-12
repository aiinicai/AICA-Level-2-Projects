from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TagTemplate, User
from ..schemas import TagTemplateOut, TagTemplateCreate
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/api/templates", tags=["Tag Templates"])

@router.get("", response_model=List[TagTemplateOut])
def get_templates(company_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(TagTemplate)
    if company_id:
        query = query.filter((TagTemplate.company_id == company_id) | (TagTemplate.company_id == None))
    return query.order_by(TagTemplate.is_default.desc(), TagTemplate.template_name.asc()).all()

@router.post("", response_model=TagTemplateOut)
def create_template(
    payload: TagTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = TagTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

@router.put("/{template_id}", response_model=TagTemplateOut)
def update_template(
    template_id: int,
    payload: TagTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tmpl = db.query(TagTemplate).filter(TagTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    for k, v in payload.model_dump().items():
        setattr(tmpl, k, v)

    db.commit()
    db.refresh(tmpl)
    return tmpl

@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tmpl = db.query(TagTemplate).filter(TagTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    tmpl_name = tmpl.template_name
    db.delete(tmpl)
    db.commit()
    return {"message": f"Template '{tmpl_name}' deleted successfully", "id": template_id}
