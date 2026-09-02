import re
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.services.client_backup import backup_client_zip, restore_client_from_zip
from app.services.client_runtime import prepare_client_database
from app.services.client_store import (
    COOKIE_NAME,
    add_client,
    data_root,
    delete_client,
    get_client,
    list_clients,
    load_registry,
    public_client,
    set_active_id,
    update_client,
)

router = APIRouter(prefix="/api/clients", tags=["Clients"])


class ClientCreate(BaseModel):
    name: str
    address: str = ""
    gstin: str = ""


class ClientUpdate(BaseModel):
    name: str = ""
    address: str = ""
    gstin: str = ""


class ClientSelect(BaseModel):
    id: str


def _cookie_args():
    return {"httponly": False, "max_age": 60 * 60 * 24 * 365, "samesite": "lax", "path": "/"}


@router.get("")
def list_client_records():
    registry = load_registry()
    active_id = registry.get("active_id") or ""
    return {
        "active_id": active_id,
        "storage_root": str(data_root()),
        "clients": [public_client(item, active_id) for item in list_clients()],
    }


@router.post("/select")
def select_client(payload: ClientSelect, response: Response):
    try:
        client = set_active_id(payload.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response.set_cookie(COOKIE_NAME, client["id"], **_cookie_args())
    return {"ok": True, "client": public_client(client, client["id"])}


@router.post("")
@router.post("/create")
def create_client(payload: ClientCreate, response: Response, user: User = Depends(require_admin)):
    name = (payload.name or "").strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Enter a client name")
    try:
        client = add_client(name, address=payload.address, gstin=payload.gstin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prepare_client_database(client, include_samples=False, include_demo_branches=False)
    set_active_id(client["id"])
    response.set_cookie(COOKIE_NAME, client["id"], **_cookie_args())
    return public_client(client, client["id"])


@router.put("/{client_id}")
def edit_client(client_id: str, payload: ClientUpdate, user: User = Depends(require_admin)):
    try:
        client = update_client(client_id, payload.name, payload.address, payload.gstin)
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    registry = load_registry()
    return public_client(client, registry.get("active_id") or "")


@router.delete("/{client_id}")
def remove_client(client_id: str, response: Response, user: User = Depends(require_admin), db=Depends(get_db)):
    db.close()
    try:
        result = delete_client(client_id)
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    if result.get("active_id"):
        response.set_cookie(COOKIE_NAME, result["active_id"], **_cookie_args())
    return result


@router.get("/{client_id}/backup")
def download_client_backup(client_id: str, user: User = Depends(require_admin)):
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", client["name"]).strip("_") or "client"
    stamp = datetime.now().strftime("%Y%m%d")
    filename = f"{safe}_{stamp}.zip"
    tmp = NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    backup_client_zip(client, Path(tmp.name))
    return FileResponse(tmp.name, filename=filename, media_type="application/zip")


@router.post("/restore")
def restore_client_backup(
    response: Response,
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a client backup ZIP only")
    try:
        client = restore_client_from_zip(file.file, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    prepare_client_database(client, include_samples=False, include_demo_branches=False)
    set_active_id(client["id"])
    response.set_cookie(COOKIE_NAME, client["id"], **_cookie_args())
    return public_client(client, client["id"])
