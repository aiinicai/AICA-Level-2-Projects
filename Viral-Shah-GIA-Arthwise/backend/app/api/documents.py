import os
import uuid
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.core.config import settings, get_case_dir
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, verify_proposal_access
from backend.app.models.models import ProposalDocument, ExtractedData, AuditLog, User, DocumentChecklistItem
from backend.app.schemas.schemas import ProposalDocumentResponse
from backend.app.services.extractor_service import DocumentExtractorService

router = APIRouter(prefix="/proposals/{proposal_id}/documents", tags=["Document Upload & Storage"])

@router.get("", response_model=List[ProposalDocumentResponse])
def get_documents(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_proposal_access(proposal_id, current_user, db)
    docs = db.query(ProposalDocument).filter(ProposalDocument.proposal_id == proposal_id).all()
    return docs

@router.post("", response_model=ProposalDocumentResponse)
async def upload_document(
    proposal_id: str,
    category: str = Form(...),
    file: UploadFile = File(...),
    checklist_item_id: Optional[str] = Form(None),
    financial_period: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    
    # 1. Extension validation
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
        
    # Read bytes and check size
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed limit (50 MB)")
        
    # SHA-256 for integrity & deduplication
    sha256_hash = hashlib.sha256(content).hexdigest()
    
    # Save directly inside the dedicated case-wise backend folder
    case_dir = get_case_dir(proposal.proposal_code)
    stored_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    storage_path = os.path.join(case_dir, stored_name)
    
    with open(storage_path, "wb") as f:
        f.write(content)
        
    new_doc = ProposalDocument(
        proposal_id=proposal_id,
        category=category,
        original_filename=file.filename,
        stored_filename=stored_name,
        file_path=storage_path,
        file_hash_sha256=sha256_hash,
        file_size=len(content),
        mime_type=file.content_type,
        uploaded_by_user_id=current_user.id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # 2. Local-first extraction
    extracted_items = DocumentExtractorService.extract_document(storage_path, category)
    for item in extracted_items:
        rec = ExtractedData(
            proposal_id=proposal_id,
            document_id=new_doc.id,
            page_or_sheet=item.get("page_or_sheet"),
            financial_period=financial_period or item.get("financial_period"),
            metric_name=item["metric_name"],
            raw_value=item.get("raw_value"),
            normalized_value=item.get("normalized_value"),
            confidence=item.get("confidence", 1.0),
            verification_status="unverified"
        )
        db.add(rec)
    db.commit()

    # 3. Update checklist status if matching or specified
    chk = None
    if checklist_item_id:
        chk = db.query(DocumentChecklistItem).filter(
            DocumentChecklistItem.id == checklist_item_id,
            DocumentChecklistItem.proposal_id == proposal_id
        ).first()
    if not chk:
        chk = db.query(DocumentChecklistItem).filter(
            DocumentChecklistItem.proposal_id == proposal_id,
            DocumentChecklistItem.category == category,
            DocumentChecklistItem.is_received == False
        ).first()
    if chk:
        chk.is_received = True
        chk.verification_status = "verified"
        chk.missing_details = None
        db.commit()
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="UPLOAD",
        resource_type="document",
        resource_id=new_doc.id,
        details_json=f"Uploaded '{file.filename}' ({len(extracted_items)} figures extracted)"
    )
    db.add(audit)
    db.commit()
    
    return new_doc

import shutil
from pydantic import BaseModel

class AttachDossierFileRequest(BaseModel):
    relative_path: str
    category: str
    checklist_item_id: Optional[str] = None

def classify_dossier_file(rel_path: str, filename: str) -> str:
    lower_path = rel_path.lower()
    lower_name = filename.lower()
    if any(k in lower_name or k in lower_path for k in ['financial statement', 'balance sheet', 'p&l']):
        return 'financial_statements'
    elif any(k in lower_name or k in lower_path for k in ['itr', 'computation', 'assessment']):
        return 'itr'
    elif any(k in lower_name or k in lower_path for k in ['gstr', 'gst returns', 'gstr3b', 'gstr-3b']):
        return 'gst'
    elif any(k in lower_name or k in lower_path for k in ['bank statement', 'current account', 'icici', 'union bank', 'account statement']):
        return 'bank_statement'
    elif any(k in lower_name or k in lower_path for k in ['pan', 'incorporation', 'moa', 'aoa', 'udyam', 'startup', 'identity']):
        return 'kyc'
    elif any(k in lower_name or k in lower_path for k in ['purchase order', 'work order', 'breakup', 'work orders', 'customers']):
        return 'purchase_orders'
    elif any(k in lower_name or k in lower_path for k in ['sanction', 'tl sanction', 'loan agreement', 'facility letter']):
        return 'sanction_letter'
    else:
        return 'other'

@router.get("/dossier-library")
def get_dossier_library(
    proposal_id: str,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns available documents ONLY from the dedicated case backend folder
    (`cases/{proposal_code}/`) and documents uploaded for this specific proposal.
    DOES NOT return generic sample reference files!
    """
    proposal = verify_proposal_access(proposal_id, current_user, db)
    case_dir = get_case_dir(proposal.proposal_code)
    library = []
    seen_files = set()

    # 1. Scan Dedicated Case Folder first
    if os.path.exists(case_dir):
        for root, _, filenames in os.walk(case_dir):
            for f in filenames:
                if not f.startswith('.') and not f.startswith(('CMA_', 'DPR_', 'Memorandum_')):
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, case_dir)
                    cat = classify_dossier_file(rel_p, f)
                    if category and category != "all" and cat != category:
                        continue
                    seen_files.add(f.lower())
                    library.append({
                        "relative_path": f"case:{rel_p}",
                        "filename": f,
                        "folder": f"📁 Case Folder ({proposal.proposal_code})",
                        "category": cat,
                        "size_bytes": os.path.getsize(full_p),
                        "is_case_file": True
                    })

    # 2. Also include documents already uploaded or stored for this proposal
    for doc in proposal.documents:
        if doc.original_filename.lower() not in seen_files:
            seen_files.add(doc.original_filename.lower())
            cat = doc.category
            if category and category != "all" and cat != category:
                continue
            library.append({
                "relative_path": f"case:{doc.stored_filename}",
                "filename": doc.original_filename,
                "folder": f"📄 Uploaded ({proposal.proposal_code})",
                "category": cat,
                "size_bytes": doc.file_size or 0,
                "is_case_file": True
            })

    # Sort: by category and filename
    library.sort(key=lambda x: (x["category"], x["filename"]))
    return library

@router.post("/attach-dossier-file")
def attach_dossier_file(
    proposal_id: str,
    req: AttachDossierFileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Attaches a selected reference document directly from the case folder or dossier library,
    executes local extraction, and links to the checklist item.
    """
    from backend.app.models.models import DocumentChecklistItem

    proposal = verify_proposal_access(proposal_id, current_user, db)
    case_dir = get_case_dir(proposal.proposal_code)

    # Check whether source is from dedicated case folder
    raw_rel = req.relative_path
    if raw_rel.startswith("case:"):
        source_rel = raw_rel[len("case:"):]
    else:
        source_rel = raw_rel

    source_path = os.path.join(case_dir, source_rel)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="Selected file not found in case folder")
    
    storage_path = source_path
    filename = os.path.basename(source_path)
        
    ext = os.path.splitext(filename)[1].lower()
    file_size = os.path.getsize(storage_path)
    
    with open(storage_path, "rb") as f:
        sha256_hash = hashlib.sha256(f.read()).hexdigest()
        
    new_doc = ProposalDocument(
        proposal_id=proposal_id,
        category=req.category,
        original_filename=filename,
        stored_filename=os.path.basename(storage_path),
        file_path=storage_path,
        file_hash_sha256=sha256_hash,
        file_size=file_size,
        mime_type="application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        uploaded_by_user_id=current_user.id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # Run extraction
    extracted_items = DocumentExtractorService.extract_document(storage_path, req.category)
    for item in extracted_items:
        rec = ExtractedData(
            proposal_id=proposal_id,
            document_id=new_doc.id,
            page_or_sheet=item.get("page_or_sheet"),
            financial_period=item.get("financial_period"),
            metric_name=item["metric_name"],
            raw_value=item.get("raw_value"),
            normalized_value=item.get("normalized_value"),
            confidence=item.get("confidence", 1.0),
            verification_status="verified",
            verified_by_user_id=current_user.id
        )
        db.add(rec)
        
    # Update checklist item if specified
    if req.checklist_item_id:
        chk = db.query(DocumentChecklistItem).filter(
            DocumentChecklistItem.id == req.checklist_item_id,
            DocumentChecklistItem.proposal_id == proposal_id
        ).first()
        if chk:
            chk.is_received = True
            chk.verification_status = "verified"
            chk.missing_details = f"Attached: {filename}"
            
    db.commit()
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="ATTACH_DOCUMENT",
        resource_type="document",
        resource_id=new_doc.id,
        details_json=f"Linked '{filename}' ({len(extracted_items)} figures extracted)"
    )
    db.add(audit)
    db.commit()
    
    return {
        "status": "success",
        "document_id": new_doc.id,
        "filename": filename,
        "extracted_metrics_count": len(extracted_items)
    }

@router.get("/case-folder")
def get_case_folder_info(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the absolute path to this case's folder on disk,
    along with the list of files currently inside it.
    """
    proposal = verify_proposal_access(proposal_id, current_user, db)
    case_dir = get_case_dir(proposal.proposal_code)
    
    files = []
    if os.path.exists(case_dir):
        for f in os.listdir(case_dir):
            if not f.startswith('.'):
                fp = os.path.join(case_dir, f)
                if os.path.isfile(fp):
                    files.append({
                        "filename": f,
                        "size_bytes": os.path.getsize(fp),
                        "is_report": f.startswith(('CMA_', 'DPR_', 'Memorandum_'))
                    })
    
    return {
        "proposal_code": proposal.proposal_code,
        "case_folder": case_dir,
        "total_files": len(files),
        "files": files
    }

@router.post("/sync-case-folder")
def sync_case_folder(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Scans the proposal's dedicated case folder (`cases/{proposal_code}/`),
    auto-links all present documents to their matching primary checklist items,
    and runs local financial extraction.
    """
    from backend.app.models.models import DocumentChecklistItem

    proposal = verify_proposal_access(proposal_id, current_user, db)
    case_dir = get_case_dir(proposal.proposal_code)
    
    if not os.path.exists(case_dir):
        os.makedirs(case_dir, exist_ok=True)
        return {
            "status": "success",
            "case_folder": case_dir,
            "message": "Case folder was empty. Created folder successfully.",
            "synced_count": 0,
            "extracted_metrics": 0,
            "files": []
        }

    checklist_items = db.query(DocumentChecklistItem).filter(
        DocumentChecklistItem.proposal_id == proposal_id
    ).all()

    synced_files = []
    total_metrics = 0

    for root, _, filenames in os.walk(case_dir):
        for fname in filenames:
            if fname.startswith('.') or fname.startswith(('CMA_', 'DPR_', 'Memorandum_')):
                continue
            
            ext = os.path.splitext(fname)[1].lower()
            if ext not in settings.ALLOWED_EXTENSIONS:
                continue

            file_path = os.path.join(root, fname)
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                sha256_hash = hashlib.sha256(f.read()).hexdigest()

            category = classify_dossier_file(fname, fname)

            # Check if this document already exists
            doc = db.query(ProposalDocument).filter(
                ProposalDocument.proposal_id == proposal_id,
                ProposalDocument.file_hash_sha256 == sha256_hash
            ).first()

            if not doc:
                doc = ProposalDocument(
                    proposal_id=proposal_id,
                    category=category,
                    original_filename=fname,
                    stored_filename=fname,
                    file_path=file_path,
                    file_hash_sha256=sha256_hash,
                    file_size=file_size,
                    mime_type="application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    uploaded_by_user_id=current_user.id
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)

                # Run extraction
                extracted = DocumentExtractorService.extract_document(file_path, category)
                for item in extracted:
                    rec = ExtractedData(
                        proposal_id=proposal_id,
                        document_id=doc.id,
                        page_or_sheet=item.get("page_or_sheet"),
                        financial_period=item.get("financial_period"),
                        metric_name=item["metric_name"],
                        raw_value=item.get("raw_value"),
                        normalized_value=item.get("normalized_value"),
                        confidence=item.get("confidence", 1.0),
                        verification_status="verified",
                        verified_by_user_id=current_user.id
                    )
                    db.add(rec)
                total_metrics += len(extracted)

            # Link with best-matching checklist item
            for chk in checklist_items:
                if chk.category == category or (category == "financial_statements" and "financial" in chk.document_name.lower()):
                    chk.is_received = True
                    chk.verification_status = "verified"
                    chk.missing_details = f"Auto-linked from case folder: {fname}"
                    break

            synced_files.append({
                "filename": fname,
                "category": category,
                "size_bytes": file_size
            })

    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="SYNC_CASE_FOLDER",
        resource_type="document",
        resource_id=proposal.id,
        details_json=f"Synced {len(synced_files)} files from case folder '{case_dir}'"
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "case_folder": case_dir,
        "synced_count": len(synced_files),
        "extracted_metrics": total_metrics,
        "files": synced_files,
        "message": f"Successfully scanned case folder: {len(synced_files)} documents auto-linked and {total_metrics} financial metrics extracted."
    }

@router.post("/auto-map-all-dossier")
def auto_map_all_dossier(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Auto Mapper: Automatically scans the proposal's dedicated case folder
    (`cases/{proposal_code}/`), classifies files by checklist category,
    attaches them to matching checklist items, and extracts metrics.
    """
    from backend.app.models.models import DocumentChecklistItem

    proposal = verify_proposal_access(proposal_id, current_user, db)
    case_dir = get_case_dir(proposal.proposal_code)
    checklist_items = db.query(DocumentChecklistItem).filter(
        DocumentChecklistItem.proposal_id == proposal_id
    ).all()

    if not os.path.exists(case_dir):
        return {
            "status": "info",
            "documents_attached": 0,
            "metrics_extracted": 0,
            "message": f"Case folder cases/{proposal.proposal_code} is empty. Drop files into this case folder to auto-map."
        }

    case_files = []
    for root, _, filenames in os.walk(case_dir):
        for f in filenames:
            if not f.startswith('.') and not f.startswith(('CMA_', 'DPR_', 'Memorandum_')):
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, case_dir)
                cat = classify_dossier_file(rel_p, f)
                case_files.append((full_p, f, cat))

    if not case_files:
        return {
            "status": "info",
            "documents_attached": 0,
            "metrics_extracted": 0,
            "message": f"Case folder cases/{proposal.proposal_code} is empty. Drop files into this case folder to auto-map."
        }

    attached_count = 0
    total_metrics = 0
    used_files = set()

    for chk in checklist_items:
        matching = [cf for cf in case_files if cf[2] == chk.category and cf[0] not in used_files]
        if not matching:
            matching = [cf for cf in case_files if cf[0] not in used_files and any(k.lower() in cf[1].lower() for k in chk.document_name.split()[:2] if len(k) > 3)]

        if matching:
            full_source, filename, cat = matching[0]
            used_files.add(full_source)
            ext = os.path.splitext(filename)[1].lower()
            stored_name = f"{uuid.uuid4().hex}{ext}"
            storage_path = os.path.join(settings.STORAGE_DIR, stored_name)
            shutil.copyfile(full_source, storage_path)

            with open(storage_path, "rb") as f:
                sha256_hash = hashlib.sha256(f.read()).hexdigest()

            new_doc = ProposalDocument(
                proposal_id=proposal_id,
                category=chk.category,
                original_filename=filename,
                stored_filename=stored_name,
                file_path=storage_path,
                file_hash_sha256=sha256_hash,
                file_size=os.path.getsize(storage_path),
                mime_type="application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                uploaded_by_user_id=current_user.id
            )
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)

            extracted = DocumentExtractorService.extract_document(storage_path, chk.category)
            for item in extracted:
                rec = ExtractedData(
                    proposal_id=proposal_id,
                    document_id=new_doc.id,
                    page_or_sheet=item.get("page_or_sheet"),
                    financial_period=item.get("financial_period"),
                    metric_name=item["metric_name"],
                    raw_value=item.get("raw_value"),
                    normalized_value=item.get("normalized_value"),
                    confidence=item.get("confidence", 1.0),
                    verification_status="verified",
                    verified_by_user_id=current_user.id
                )
                db.add(rec)
            total_metrics += len(extracted)

            chk.is_received = True
            chk.received_document_id = new_doc.id
            chk.verification_status = "verified"
            chk.missing_details = f"Verified from Case Folder: {filename}"
            attached_count += 1

    db.commit()
    return {
        "status": "success",
        "documents_attached": attached_count,
        "metrics_extracted": total_metrics,
        "message": f"Auto-attached {attached_count} documents from cases/{proposal.proposal_code} and extracted {total_metrics} metrics."
    }

@router.get("/{document_id}/download")
def download_document(
    proposal_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    doc = db.query(ProposalDocument).filter(
        ProposalDocument.id == document_id,
        ProposalDocument.proposal_id == proposal_id
    ).first()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document not found on storage")
        
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="DOWNLOAD",
        resource_type="document",
        resource_id=doc.id,
        details_json=f"Downloaded '{doc.original_filename}'"
    )
    db.add(audit)
    db.commit()
    
    return FileResponse(
        path=doc.file_path,
        filename=doc.original_filename,
        media_type=doc.mime_type or "application/octet-stream"
    )
