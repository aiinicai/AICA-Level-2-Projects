import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/api/inventory", tags=["Inventory Management"])

@router.get("/items", response_model=List[schemas.InventoryItemResponse])
def get_inventory_items(search: Optional[str] = None, category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.InventoryItem)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (models.InventoryItem.name.ilike(s)) |
            (models.InventoryItem.item_code.ilike(s)) |
            (models.InventoryItem.barcode.ilike(s))
        )
    if category:
        query = query.filter(models.InventoryItem.category == category)

    items = query.order_by(models.InventoryItem.name).all()
    results = []
    for item in items:
        tot_val = round(item.stock_quantity * item.cost_price, 2)
        is_low = item.stock_quantity <= item.reorder_level
        resp = schemas.InventoryItemResponse(
            id=item.id,
            item_code=item.item_code,
            name=item.name,
            category=item.category,
            barcode=item.barcode,
            unit=item.unit,
            cost_price=item.cost_price,
            selling_price=item.selling_price,
            stock_quantity=item.stock_quantity,
            reorder_level=item.reorder_level,
            total_value=tot_val,
            is_low_stock=is_low,
            created_at=item.created_at
        )
        results.append(resp)
    return results

@router.post("/items", response_model=schemas.InventoryItemResponse)
def create_inventory_item(item_in: schemas.InventoryItemCreate, db: Session = Depends(get_db)):
    existing = db.query(models.InventoryItem).filter(models.InventoryItem.item_code == item_in.item_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Item code already exists")

    item = models.InventoryItem(**item_in.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)

    # If opening stock > 0, log opening stock movement
    if item.stock_quantity > 0:
        mov = models.StockMovement(
            movement_date=datetime.date.today(),
            item_code=item.item_code,
            item_name=item.name,
            movement_type="OPENING",
            reference_doc="INIT-STOCK",
            quantity=item.stock_quantity,
            unit_cost=item.cost_price,
            total_cost=round(item.stock_quantity * item.cost_price, 2),
            notes="Opening stock balance"
        )
        db.add(mov)
        db.commit()

    return schemas.InventoryItemResponse(
        id=item.id,
        item_code=item.item_code,
        name=item.name,
        category=item.category,
        barcode=item.barcode,
        unit=item.unit,
        cost_price=item.cost_price,
        selling_price=item.selling_price,
        stock_quantity=item.stock_quantity,
        reorder_level=item.reorder_level,
        total_value=round(item.stock_quantity * item.cost_price, 2),
        is_low_stock=item.stock_quantity <= item.reorder_level,
        created_at=item.created_at
    )

@router.put("/items/{item_code}", response_model=schemas.InventoryItemResponse)
def update_inventory_item(item_code: str, item_update: schemas.InventoryItemUpdate, db: Session = Depends(get_db)):
    item = db.query(models.InventoryItem).filter(models.InventoryItem.item_code == item_code).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    data = item_update.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            setattr(item, k, v)

    db.commit()
    db.refresh(item)
    return schemas.InventoryItemResponse(
        id=item.id,
        item_code=item.item_code,
        name=item.name,
        category=item.category,
        barcode=item.barcode,
        unit=item.unit,
        cost_price=item.cost_price,
        selling_price=item.selling_price,
        stock_quantity=item.stock_quantity,
        reorder_level=item.reorder_level,
        total_value=round(item.stock_quantity * item.cost_price, 2),
        is_low_stock=item.stock_quantity <= item.reorder_level,
        created_at=item.created_at
    )

@router.get("/movements", response_model=List[schemas.StockMovementResponse])
def get_stock_movements(item_code: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.StockMovement)
    if item_code:
        q = q.filter(models.StockMovement.item_code == item_code)
    return q.order_by(models.StockMovement.id.desc()).all()

@router.post("/adjust")
def adjust_inventory_stock(adj: schemas.StockAdjustmentCreate, db: Session = Depends(get_db)):
    item = db.query(models.InventoryItem).filter(models.InventoryItem.item_code == adj.item_code).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    old_qty = item.stock_quantity
    adj_type = (adj.adjustment_type or "").upper()
    change_qty = 0.0

    if adj_type == "SET":
        change_qty = adj.quantity - old_qty
        new_qty = max(0.0, adj.quantity)
    elif adj.quantity < 0 or any(w in adj_type for w in ["DAMAGE", "SPOIL", "EXPIR", "LOSS", "THEFT", "SHRINK", "REDUCE", "WRITE-OFF", "WASTE"]):
        change_qty = -abs(adj.quantity)
        new_qty = max(0.0, old_qty - abs(adj.quantity))
    else:
        change_qty = abs(adj.quantity)
        new_qty = old_qty + change_qty

    item.stock_quantity = new_qty
    total_cost_val = round(abs(change_qty) * item.cost_price, 2)

    adj_doc_num = crud.get_next_sequence_number(db, "ADJ-2026", models.JournalVoucher, "document_ref")

    # Record movement
    mov = models.StockMovement(
        movement_date=datetime.date.today(),
        item_code=item.item_code,
        item_name=item.name,
        movement_type="STOCK_ADJUSTMENT",
        reference_doc=adj_doc_num,
        quantity=change_qty,
        unit_cost=item.cost_price,
        total_cost=total_cost_val,
        notes=f"Stock Adjustment ({adj.reason}) from {old_qty} to {new_qty}"
    )
    db.add(mov)

    # Post accounting voucher for stock change if value > 0
    if total_cost_val > 0:
        voucher_no = crud.get_next_sequence_number(db, "GL-ADJ", models.JournalVoucher, "voucher_no")
        if change_qty < 0:
            # Loss/Spoilage/Shrinkage:
            # Dr 5000 (Cost of Goods Sold / Spoilage)
            # Cr 1200 (Inventory)
            voucher_lines = [
                {"account_code": "5000", "account_name": "Cost of Goods Sold / Direct Materials", "description": f"Inventory Shrinkage/Damage: {item.name} ({adj.reason})", "debit": total_cost_val, "credit": 0.0},
                {"account_code": "1200", "account_name": "Inventory / Merchandise Store Stock", "description": f"Inventory write-off {adj.reason}", "debit": 0.0, "credit": total_cost_val}
            ]
        else:
            # Inventory Gain:
            # Dr 1200 (Inventory)
            # Cr 5000 (Cost of Goods Sold / Recovery)
            voucher_lines = [
                {"account_code": "1200", "account_name": "Inventory / Merchandise Store Stock", "description": f"Inventory count gain: {item.name}", "debit": total_cost_val, "credit": 0.0},
                {"account_code": "5000", "account_name": "Cost of Goods Sold / Direct Materials", "description": f"Inventory count gain {adj.reason}", "debit": 0.0, "credit": total_cost_val}
            ]

        crud.create_journal_voucher_entry(
            db=db,
            voucher_no=voucher_no,
            posting_date=datetime.date.today(),
            source_module="GL-JV",
            document_ref=adj_doc_num,
            description=f"Inventory Adjustment Voucher: {item.name} ({adj.reason})",
            lines=voucher_lines,
            created_by="Store Manager",
            approved_by="Store Manager",
            status="Approved"
        )

    db.commit()
    return {
        "status": "success",
        "message": f"Successfully updated stock for {item.name} from {old_qty} to {new_qty} {item.unit} (Value: ${total_cost_val:,.2f})",
        "stock_quantity": new_qty,
        "change_quantity": change_qty,
        "voucher_no": voucher_no,
        "item": {
            "item_code": item.item_code,
            "name": item.name,
            "stock_quantity": new_qty,
            "cost_price": item.cost_price,
            "selling_price": item.selling_price,
            "unit": item.unit
        }
    }

@router.get("/summary")
def get_inventory_summary(db: Session = Depends(get_db)):
    items = db.query(models.InventoryItem).all()
    tot_skus = len(items)
    tot_val = sum(i.stock_quantity * i.cost_price for i in items)
    low_stock_count = sum(1 for i in items if i.stock_quantity <= i.reorder_level)

    return {
        "total_skus": tot_skus,
        "total_valuation": round(tot_val, 2),
        "total_inventory_valuation": round(tot_val, 2),
        "low_stock_items": low_stock_count
    }
