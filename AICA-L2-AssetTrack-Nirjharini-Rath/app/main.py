"""Streamlined FastAPI app for the Windows v0 Edition (no auth, no AI, no WhatsApp API, no scheduler, no GIS)."""

from __future__ import annotations

import io
import json
import re
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from pydantic import BaseModel, Field

from app import config
from app.database import (
    calculate_next_maintenance_date,
    generate_next_asset_tag,
    get_connection,
    init_db,
    new_id,
    parse_json_list,
    utc_now_iso,
)
from app.excel_exporter import generate_excel_bytes, save_master_excel
from app.qr_generator import generate_qr_svg


def _wa_link(phone: str, message: str) -> Optional[str]:
    digits = re.sub(r"[^0-9]", "", phone or "")
    if not digits:
        return None
    return f"https://wa.me/{digits}?text={quote(message)}"


def _dump(model: BaseModel) -> dict:
    return model.model_dump(exclude_unset=True) if hasattr(model, "model_dump") else model.dict(exclude_unset=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config.ensure_directories()
    init_db()
    yield


app = FastAPI(title="AssetTrack v0", version="1.0.0", lifespan=lifespan)

config.ensure_directories()
app.mount("/static/uploads", StaticFiles(directory=str(config.UPLOADS_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


# --- Schemas ---

class VendorIn(BaseModel):
    name: str = Field(..., min_length=1)
    vendor_type: str = "SERVICE_CENTER"
    contact_person: Optional[str] = None
    phone: str = Field(..., min_length=5)
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class AssetIn(BaseModel):
    asset_tag: Optional[str] = None
    name: str = Field(..., min_length=1)
    category: str = "OFFICE_FIXTURES"
    location: str = Field(..., min_length=1)
    purchase_date: Optional[str] = None
    purchase_cost: Optional[float] = Field(None, ge=0)
    vendor_id: Optional[str] = None
    warranty_end_date: Optional[str] = None
    maintenance_cycle: str = "QUARTERLY"
    next_maintenance_date: Optional[str] = None
    status: str = "OPERATIONAL"
    photos: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class AssetPatch(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class MaintenanceIn(BaseModel):
    asset_id: str
    vendor_id: Optional[str] = None
    scheduled_date: str
    completed_date: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)
    description: str = Field(..., min_length=1)
    status: str = "SCHEDULED"
    photos: list[str] = Field(default_factory=list)


class MaintenancePatch(BaseModel):
    status: Optional[str] = None
    completed_date: Optional[str] = None
    cost: Optional[float] = None
    description: Optional[str] = None


class StationeryIn(BaseModel):
    item_name: str = Field(..., min_length=1)
    category: str = "PAPER"
    current_stock: int = Field(0, ge=0)
    unit: str = "Reams"
    minimum_reorder_threshold: int = Field(5, ge=0)
    preferred_vendor_id: Optional[str] = None


class StockAdjust(BaseModel):
    delta: int


# --- Pages ---

@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return config.render_template(templates, request, "index.html", {"company_name": config.COMPANY_NAME})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/assets/{asset_id}", response_class=HTMLResponse)
def asset_detail_page(asset_id: str, request: Request):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT a.*, v.name AS vendor_name, v.phone AS vendor_phone
            FROM assets a LEFT JOIN vendors v ON a.vendor_id = v.id
            WHERE a.id = ?
            """,
            (asset_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found")
        maint = [
            {**dict(m), "photos": parse_json_list(m["photos"])}
            for m in conn.execute(
                """
                SELECT m.*, v.name AS vendor_name
                FROM maintenance_records m LEFT JOIN vendors v ON m.vendor_id = v.id
                WHERE m.asset_id = ? ORDER BY m.scheduled_date DESC
                """,
                (asset_id,),
            ).fetchall()
        ]
    asset = {**dict(row), "photos": parse_json_list(row["photos"])}
    base = str(request.base_url).rstrip("/")
    qr_url = f"{base}/q/{asset['asset_tag']}"
    wa_msg = f"Hello {asset.get('vendor_name') or 'Team'}, our asset {asset['name']} ({asset['asset_tag']}) at {asset['location']} requires maintenance."
    return config.render_template(
        templates,
        request,
        "asset_detail.html",
        {
            "company_name": config.COMPANY_NAME,
            "asset": asset,
            "maintenance_records": maint,
            "qr_svg": generate_qr_svg(qr_url, module_size=4, border=3),
            "qr_url": qr_url,
            "wa_url": _wa_link(asset.get("vendor_phone") or "", wa_msg),
        },
    )


@app.get("/qr/print", response_class=HTMLResponse)
def print_qr_page(request: Request, asset_id: Optional[str] = Query(None)):
    with get_connection() as conn:
        if asset_id:
            rows = conn.execute("SELECT id, asset_tag, name, location FROM assets WHERE id = ?", (asset_id,)).fetchall()
        else:
            rows = conn.execute("SELECT id, asset_tag, name, location FROM assets ORDER BY asset_tag ASC").fetchall()
    base = str(request.base_url).rstrip("/")
    stickers = [
        {
            "asset_tag": r["asset_tag"],
            "name": r["name"],
            "location": r["location"],
            "svg": generate_qr_svg(f"{base}/q/{r['asset_tag']}", module_size=4, border=3),
        }
        for r in rows
    ]
    return config.render_template(
        templates,
        request,
        "qr_print.html",
        {"company_name": config.COMPANY_NAME, "base_url": base, "stickers": stickers},
    )


@app.get("/api/assets/{asset_id}/qr.svg")
def asset_qr_svg(asset_id: str, request: Request):
    with get_connection() as conn:
        row = conn.execute("SELECT asset_tag FROM assets WHERE id = ? OR asset_tag = ?", (asset_id, asset_id)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    base = str(request.base_url).rstrip("/")
    return Response(content=generate_qr_svg(f"{base}/q/{row['asset_tag']}"), media_type="image/svg+xml")


@app.get("/q/{asset_tag}", response_class=HTMLResponse)
def qr_quick_page(asset_tag: str, request: Request):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT a.*, v.name AS vendor_name, v.phone AS vendor_phone FROM assets a LEFT JOIN vendors v ON a.vendor_id = v.id WHERE a.asset_tag = ?",
            (asset_tag,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset = {**dict(row), "photos": parse_json_list(row["photos"])}
    return config.render_template(
        templates,
        request,
        "qr_quick.html",
        {"company_name": config.COMPANY_NAME, "asset": asset},
    )


@app.post("/api/q/{asset_tag}/status")
def qr_quick_status(asset_tag: str, status: str = Form("OPERATIONAL"), issue_note: str = Form("")):
    with get_connection() as conn:
        asset = conn.execute("SELECT id, vendor_id FROM assets WHERE asset_tag = ?", (asset_tag,)).fetchone()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        conn.execute("UPDATE assets SET status = ? WHERE id = ?", (status, asset["id"]))
        if status == "NEEDS_REPAIR" and issue_note.strip():
            conn.execute(
                """
                INSERT INTO maintenance_records (id, asset_id, vendor_id, scheduled_date, description, status, photos, created_at)
                VALUES (?, ?, ?, ?, ?, 'SCHEDULED', '[]', ?)
                """,
                (new_id(), asset["id"], asset["vendor_id"], date.today().isoformat(), issue_note.strip(), utc_now_iso()),
            )
    save_master_excel()
    return {"success": True, "asset_tag": asset_tag, "status": status}


# --- Photo Uploads ---

@app.post("/api/uploads")
async def upload_photo(file: UploadFile = File(...)):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    config.ensure_directories()
    fname = f"img_{uuid.uuid4().hex}.jpg"
    dest = config.UPLOADS_DIR / fname
    try:
        with Image.open(io.BytesIO(raw)) as img:
            rgb = img.convert("RGB")
            rgb.thumbnail((1600, 1600))
            rgb.save(dest, format="JPEG", quality=82, optimize=True)
            rgb.close()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")
    return {"url": f"/static/uploads/{fname}"}


# --- Dashboard (Live Calculation + wa.me Links Only) ---

@app.get("/api/dashboard")
def get_dashboard():
    today = date.today()
    with get_connection() as conn:
        total_assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        operational = conn.execute("SELECT COUNT(*) FROM assets WHERE status = 'OPERATIONAL'").fetchone()[0]
        attention = conn.execute("SELECT COUNT(*) FROM assets WHERE status IN ('NEEDS_REPAIR', 'IN_MAINTENANCE')").fetchone()[0]
        total_value = conn.execute("SELECT COALESCE(SUM(purchase_cost), 0) FROM assets").fetchone()[0] or 0.0
        open_maint = conn.execute("SELECT COUNT(*) FROM maintenance_records WHERE status != 'COMPLETED'").fetchone()[0]
        low_stock_rows = conn.execute(
            """
            SELECT c.*, v.name AS vendor_name, v.phone AS vendor_phone
            FROM recurring_consumables c LEFT JOIN vendors v ON c.preferred_vendor_id = v.id
            WHERE c.current_stock <= c.minimum_reorder_threshold
            ORDER BY c.current_stock ASC
            """
        ).fetchall()
        due_rows = conn.execute(
            """
            SELECT a.*, v.name AS vendor_name, v.phone AS vendor_phone
            FROM assets a LEFT JOIN vendors v ON a.vendor_id = v.id
            WHERE a.status != 'DECOMMISSIONED' AND a.next_maintenance_date IS NOT NULL
            ORDER BY a.next_maintenance_date ASC
            """
        ).fetchall()

    maint_alerts = []
    for a in due_rows:
        try:
            due = date.fromisoformat(a["next_maintenance_date"][:10])
        except ValueError:
            continue
        delta = (due - today).days
        if delta > 30:
            continue
        sev = "RED" if delta <= 0 else ("ORANGE" if delta <= 7 else "YELLOW")
        lbl = "OVERDUE" if delta < 0 else ("DUE TODAY" if delta == 0 else f"DUE IN {delta}D")
        msg = (
            f"Hello {a['vendor_name'] or 'Team'}, this is from {config.COMPANY_NAME}. "
            f"Our asset {a['name']} ({a['asset_tag']}) at {a['location']} is due for maintenance on {a['next_maintenance_date']}. "
            "Please confirm your availability."
        )
        maint_alerts.append(
            {
                "asset_id": a["id"],
                "asset_tag": a["asset_tag"],
                "asset_name": a["name"],
                "location": a["location"],
                "next_maintenance_date": a["next_maintenance_date"],
                "severity": sev,
                "label": lbl,
                "vendor_name": a["vendor_name"],
                "wa_url": _wa_link(a["vendor_phone"] or "", msg),
            }
        )

    low_stock_alerts = []
    for s in low_stock_rows:
        qty_order = max(s["minimum_reorder_threshold"] * 2, 10)
        msg = (
            f"Hello {s['vendor_name'] or 'Supplier'}, this is from {config.COMPANY_NAME}. "
            f"Stock for {s['item_name']} is low ({s['current_stock']} {s['unit']} left). "
            f"Please send {qty_order} {s['unit']}."
        )
        low_stock_alerts.append(
            {
                "id": s["id"],
                "item_name": s["item_name"],
                "current_stock": s["current_stock"],
                "unit": s["unit"],
                "minimum_reorder_threshold": s["minimum_reorder_threshold"],
                "vendor_name": s["vendor_name"],
                "wa_url": _wa_link(s["vendor_phone"] or "", msg),
            }
        )

    return {
        "kpis": {
            "total_assets": total_assets,
            "operational_assets": operational,
            "attention_assets": attention,
            "total_value": round(float(total_value), 2),
            "open_maintenance": open_maint,
            "low_stock_count": len(low_stock_alerts),
        },
        "maintenance_alerts": maint_alerts,
        "low_stock_alerts": low_stock_alerts,
    }


# --- Assets CRUD ---

@app.get("/api/assets")
def list_assets(q: Optional[str] = None, category: Optional[str] = None, status: Optional[str] = None):
    sql = "SELECT a.*, v.name AS vendor_name, v.phone AS vendor_phone FROM assets a LEFT JOIN vendors v ON a.vendor_id = v.id WHERE 1=1"
    params: list = []
    if category:
        sql += " AND a.category = ?"
        params.append(category)
    if status:
        sql += " AND a.status = ?"
        params.append(status)
    if q:
        like = f"%{q.strip()}%"
        sql += " AND (a.asset_tag LIKE ? OR a.name LIKE ? OR a.location LIKE ?)"
        params.extend([like, like, like])
    sql += " ORDER BY a.created_at DESC"
    with get_connection() as conn:
        items = []
        for r in conn.execute(sql, params).fetchall():
            d = dict(r)
            d["photos"] = parse_json_list(d["photos"])
            msg = f"Hello {d['vendor_name'] or 'Team'}, our asset {d['name']} ({d['asset_tag']}) at {d['location']} needs attention."
            d["wa_url"] = _wa_link(d.get("vendor_phone") or "", msg)
            items.append(d)
    return {"items": items, "total": len(items)}


@app.post("/api/assets", status_code=201)
def create_asset(payload: AssetIn):
    aid = new_id()
    now = utc_now_iso()
    next_m = payload.next_maintenance_date or calculate_next_maintenance_date(payload.maintenance_cycle, payload.purchase_date)
    with get_connection() as conn:
        tag = (payload.asset_tag or "").strip() or generate_next_asset_tag(conn, payload.category)
        try:
            conn.execute(
                """
                INSERT INTO assets (
                    id, asset_tag, name, category, location, purchase_date, purchase_cost,
                    vendor_id, warranty_end_date, maintenance_cycle, next_maintenance_date,
                    status, photos, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    aid, tag, payload.name.strip(), payload.category, payload.location.strip(),
                    payload.purchase_date, payload.purchase_cost, payload.vendor_id or None,
                    payload.warranty_end_date, payload.maintenance_cycle, next_m,
                    payload.status, json.dumps(payload.photos), payload.notes, now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        row = dict(conn.execute("SELECT * FROM assets WHERE id = ?", (aid,)).fetchone())
    save_master_excel()
    row["photos"] = parse_json_list(row["photos"])
    return row


@app.put("/api/assets/{asset_id}")
def update_asset(asset_id: str, payload: AssetPatch):
    updates = _dump(payload)
    if not updates:
        return {"updated": True}
    clause = ", ".join(f"{k} = ?" for k in updates.keys())
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE assets SET {clause} WHERE id = ?", list(updates.values()) + [asset_id])
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset not found")
    save_master_excel()
    return {"updated": True, "id": asset_id}


@app.delete("/api/assets/{asset_id}")
def delete_asset(asset_id: str):
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset not found")
    save_master_excel()
    return {"deleted": True}


# --- Singular Maintenance Log CRUD ---

@app.get("/api/maintenance")
def list_maintenance():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.*, a.asset_tag, a.name AS asset_name, v.name AS vendor_name, v.phone AS vendor_phone
            FROM maintenance_records m
            JOIN assets a ON m.asset_id = a.id
            LEFT JOIN vendors v ON m.vendor_id = v.id
            ORDER BY m.scheduled_date DESC
            """
        ).fetchall()
    items = [{**dict(r), "photos": parse_json_list(r["photos"])} for r in rows]
    return {"items": items, "total": len(items)}


@app.post("/api/maintenance", status_code=201)
def create_maintenance(payload: MaintenanceIn):
    mid = new_id()
    now = utc_now_iso()
    with get_connection() as conn:
        asset = conn.execute("SELECT id, maintenance_cycle FROM assets WHERE id = ?", (payload.asset_id,)).fetchone()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        conn.execute(
            """
            INSERT INTO maintenance_records (id, asset_id, vendor_id, scheduled_date, completed_date, cost, description, status, photos, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, payload.asset_id, payload.vendor_id or None, payload.scheduled_date, payload.completed_date, payload.cost, payload.description.strip(), payload.status, json.dumps(payload.photos), now),
        )
        if payload.status == "COMPLETED":
            comp = payload.completed_date or payload.scheduled_date
            nxt = calculate_next_maintenance_date(asset["maintenance_cycle"], comp)
            conn.execute("UPDATE assets SET status='OPERATIONAL', last_maintenance_date=?, next_maintenance_date=? WHERE id=?", (comp, nxt, payload.asset_id))
        elif payload.status == "IN_PROGRESS":
            conn.execute("UPDATE assets SET status='IN_MAINTENANCE' WHERE id=?", (payload.asset_id,))
        row = dict(conn.execute("SELECT * FROM maintenance_records WHERE id = ?", (mid,)).fetchone())
    save_master_excel()
    row["photos"] = parse_json_list(row["photos"])
    return row


@app.put("/api/maintenance/{record_id}")
def update_maintenance(record_id: str, payload: MaintenancePatch):
    updates = _dump(payload)
    if not updates:
        return {"updated": True}
    clause = ", ".join(f"{k} = ?" for k in updates.keys())
    with get_connection() as conn:
        cur = conn.execute(f"UPDATE maintenance_records SET {clause} WHERE id = ?", list(updates.values()) + [record_id])
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        row = conn.execute("SELECT * FROM maintenance_records WHERE id = ?", (record_id,)).fetchone()
        if row and row["status"] == "COMPLETED":
            asset = conn.execute("SELECT maintenance_cycle FROM assets WHERE id = ?", (row["asset_id"],)).fetchone()
            comp = row["completed_date"] or row["scheduled_date"]
            if asset:
                nxt = calculate_next_maintenance_date(asset["maintenance_cycle"], comp)
                conn.execute("UPDATE assets SET status='OPERATIONAL', last_maintenance_date=?, next_maintenance_date=? WHERE id=?", (comp, nxt, row["asset_id"]))
    save_master_excel()
    return {"updated": True}


@app.delete("/api/maintenance/{record_id}")
def delete_maintenance(record_id: str):
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM maintenance_records WHERE id = ?", (record_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found")
    save_master_excel()
    return {"deleted": True}


# --- Vendors CRUD ---

@app.get("/api/vendors")
def list_vendors(q: Optional[str] = None):
    sql = "SELECT * FROM vendors WHERE 1=1"
    params: list = []
    if q:
        like = f"%{q.strip()}%"
        sql += " AND (name LIKE ? OR contact_person LIKE ? OR phone LIKE ?)"
        params.extend([like, like, like])
    sql += " ORDER BY name ASC"
    with get_connection() as conn:
        items = []
        for r in conn.execute(sql, params).fetchall():
            d = dict(r)
            d["wa_url"] = _wa_link(d["phone"], f"Hello {d['name']}, reaching out from {config.COMPANY_NAME}.")
            items.append(d)
    return {"items": items, "total": len(items)}


@app.post("/api/vendors", status_code=201)
def create_vendor(payload: VendorIn):
    vid = new_id()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO vendors (id, name, vendor_type, contact_person, phone, email, address, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (vid, payload.name.strip(), payload.vendor_type, payload.contact_person, payload.phone.strip(), payload.email, payload.address, payload.notes, utc_now_iso()),
        )
        row = dict(conn.execute("SELECT * FROM vendors WHERE id = ?", (vid,)).fetchone())
    save_master_excel()
    return row


@app.delete("/api/vendors/{vendor_id}")
def delete_vendor(vendor_id: str):
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Vendor not found")
    save_master_excel()
    return {"deleted": True}


# --- Stationery CRUD + +/- Stock Adjust ---

@app.get("/api/stationery")
def list_stationery():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT c.*, v.name AS vendor_name, v.phone AS vendor_phone FROM recurring_consumables c LEFT JOIN vendors v ON c.preferred_vendor_id = v.id ORDER BY c.item_name ASC"
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["is_low_stock"] = d["current_stock"] <= d["minimum_reorder_threshold"]
        qty_order = max(d["minimum_reorder_threshold"] * 2, 10)
        msg = f"Hello {d['vendor_name'] or 'Supplier'}, this is from {config.COMPANY_NAME}. Stock for {d['item_name']} is {d['current_stock']} {d['unit']}. Please restock {qty_order} {d['unit']}."
        d["wa_url"] = _wa_link(d.get("vendor_phone") or "", msg)
        items.append(d)
    return {"items": items, "total": len(items)}


@app.post("/api/stationery", status_code=201)
def create_stationery(payload: StationeryIn):
    sid = new_id()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO recurring_consumables (id, item_name, category, current_stock, unit, minimum_reorder_threshold, preferred_vendor_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sid, payload.item_name.strip(), payload.category, payload.current_stock, payload.unit.strip(), payload.minimum_reorder_threshold, payload.preferred_vendor_id or None, utc_now_iso()),
        )
        row = dict(conn.execute("SELECT * FROM recurring_consumables WHERE id = ?", (sid,)).fetchone())
    save_master_excel()
    return row


@app.post("/api/stationery/{item_id}/adjust")
def adjust_stationery(item_id: str, payload: StockAdjust):
    with get_connection() as conn:
        cur_row = conn.execute("SELECT current_stock FROM recurring_consumables WHERE id = ?", (item_id,)).fetchone()
        if not cur_row:
            raise HTTPException(status_code=404, detail="Item not found")
        new_qty = max(0, cur_row["current_stock"] + payload.delta)
        conn.execute("UPDATE recurring_consumables SET current_stock = ? WHERE id = ?", (new_qty, item_id))
    save_master_excel()
    return {"id": item_id, "current_stock": new_qty}


@app.delete("/api/stationery/{item_id}")
def delete_stationery(item_id: str):
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM recurring_consumables WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
    save_master_excel()
    return {"deleted": True}


# --- Excel Export ---

@app.get("/api/export/excel")
def export_excel():
    save_master_excel()
    return Response(
        content=generate_excel_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="v0_assets_master.xlsx"'},
    )
