import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from app import models, schemas

# Sequence Number Helpers
def get_next_sequence_number(db: Session, prefix: str, model_class, field_name: str) -> str:
    count = db.query(func.count(getattr(model_class, field_name))).filter(
        getattr(model_class, field_name).like(f"{prefix}-%")
    ).scalar() or 0
    return f"{prefix}-{count + 1:04d}"

# Journal Voucher CRUD
def create_journal_voucher_entry(
    db: Session,
    voucher_no: str,
    posting_date: datetime.date,
    source_module: str,
    document_ref: str,
    description: str,
    lines: List[Dict[str, Any]],
    created_by: str = "System",
    approved_by: Optional[str] = "System",
    status: str = "Approved"
) -> models.JournalVoucher:
    total_debit = round(sum(l.get("debit", 0.0) for l in lines), 2)
    total_credit = round(sum(l.get("credit", 0.0) for l in lines), 2)

    # Double entry check
    if abs(total_debit - total_credit) > 0.01:
        raise ValueError(f"Unbalanced journal voucher! Total Debit: {total_debit}, Total Credit: {total_credit}")

    jv = models.JournalVoucher(
        voucher_no=voucher_no,
        posting_date=posting_date,
        source_module=source_module,
        document_ref=document_ref,
        description=description,
        total_debit=total_debit,
        total_credit=total_credit,
        status=status,
        created_by=created_by,
        approved_by=approved_by,
        approved_at=datetime.datetime.utcnow() if status == "Approved" else None
    )
    db.add(jv)
    db.flush()

    line_idx = 1
    for l in lines:
        acc = db.query(models.Account).filter(models.Account.account_code == l["account_code"]).first()
        acc_name = acc.account_name if acc else l.get("account_name", "Unknown Account")
        vline = models.VoucherLine(
            voucher_id=jv.id,
            line_no=line_idx,
            account_code=l["account_code"],
            account_name=acc_name,
            description=l.get("description", description),
            debit=round(l.get("debit", 0.0), 2),
            credit=round(l.get("credit", 0.0), 2)
        )
        db.add(vline)
        line_idx += 1

    db.commit()
    db.refresh(jv)
    return jv

# Budget Metrics Engine
def get_account_budget_metrics(db: Session, account_code: str, fiscal_year: int = 2026) -> Dict[str, Any]:
    acc = db.query(models.Account).filter(models.Account.account_code == account_code).first()
    acc_name = acc.account_name if acc else ""

    # Approved Budget
    budget_row = db.query(models.Budget).filter(
        models.Budget.account_code == account_code,
        models.Budget.fiscal_year == fiscal_year
    ).first()
    approved_budget = budget_row.annual_budget if budget_row else 0.0

    # 1. Pre-Encumbrance:
    # PRs in Draft, Pending Approval, or Approved that have NOT been converted to PO
    pr_lines = db.query(models.PRLine).join(models.PurchaseRequisition).filter(
        models.PRLine.account_code == account_code,
        models.PurchaseRequisition.status.in_(["Draft", "Pending Approval", "Approved"])
    ).all()
    pre_encumbrance = sum(pr.total_amount for pr in pr_lines)

    # 2. Encumbrance:
    # Approved POs not yet invoiced: (quantity - invoiced_qty) * unit_price
    po_lines = db.query(models.POLine).join(models.PurchaseOrder).filter(
        models.POLine.account_code == account_code,
        models.PurchaseOrder.status.in_(["Approved", "Partially Received"])
    ).all()
    encumbrance = sum(max(0.0, (pol.quantity - pol.invoiced_qty)) * pol.unit_price for pol in po_lines)

    # 3. Actual Consumed:
    # Posted GL vouchers on this account from AP-INV, GL-JV, PO-GRN
    # Note: Net debit (debit - credit) on this expense/asset account
    vlines = db.query(models.VoucherLine).join(models.JournalVoucher).filter(
        models.VoucherLine.account_code == account_code,
        models.JournalVoucher.status == "Approved",
        models.JournalVoucher.source_module != "OB"
    ).all()
    actual_consumed = sum(vl.debit - vl.credit for vl in vlines)

    # Available Budget
    committed = pre_encumbrance + encumbrance + actual_consumed
    available = approved_budget - committed
    utilization_pct = (committed / approved_budget * 100.0) if approved_budget > 0 else 0.0

    return {
        "account_code": account_code,
        "account_name": acc_name,
        "fiscal_year": fiscal_year,
        "approved_budget": round(approved_budget, 2),
        "pre_encumbrance": round(pre_encumbrance, 2),
        "encumbrance": round(encumbrance, 2),
        "actual_consumed": round(actual_consumed, 2),
        "committed_amount": round(committed, 2),
        "available_budget": round(available, 2),
        "utilization_percentage": round(utilization_pct, 1)
    }

# Check budget availability for transaction line
def check_budget_availability(db: Session, account_code: str, amount: float) -> schemas.BudgetCheckResponse:
    metrics = get_account_budget_metrics(db, account_code)
    available = metrics["available_budget"]
    passed = (available >= amount) or (metrics["approved_budget"] == 0 and amount <= 0)

    variance = round(available - amount, 2)
    if passed:
        message = f"Budget Available: ${available:,.2f} (PASS - Remaining after tx: ${variance:,.2f})"
    else:
        message = f"Insufficient Budget: Exceeds by ${abs(variance):,.2f} (Available: ${available:,.2f}, Requested: ${amount:,.2f})"

    return schemas.BudgetCheckResponse(
        passed=passed,
        account_code=account_code,
        account_name=metrics["account_name"],
        annual_budget=metrics["approved_budget"],
        committed_amount=metrics["committed_amount"],
        available_budget=available,
        requested_amount=amount,
        variance=variance,
        message=message
    )

# P2P Workflow Actions
def convert_pr_to_po(db: Session, pr_id: int, vendor_code: str, tax_code: str = "VAT-STD-5") -> models.PurchaseOrder:
    pr = db.query(models.PurchaseRequisition).filter(models.PurchaseRequisition.id == pr_id).first()
    if not pr:
        raise ValueError("PR not found")
    if pr.status != "Approved":
        raise ValueError("Only Approved PRs can be converted to Purchase Orders")

    tax = db.query(models.TaxCode).filter(models.TaxCode.code == tax_code).first()
    tax_rate = tax.rate if tax else 5.0

    po_num = get_next_sequence_number(db, "PO-2026", models.PurchaseOrder, "po_number")
    
    subtotal = 0.0
    tax_total = 0.0
    po_lines = []

    for idx, pr_l in enumerate(pr.lines, start=1):
        line_sub = round(pr_l.quantity * pr_l.unit_price, 2)
        line_tax = round(line_sub * (tax_rate / 100.0), 2)
        line_tot = round(line_sub + line_tax, 2)
        subtotal += line_sub
        tax_total += line_tax

        pol = models.POLine(
            line_no=idx,
            description=pr_l.description,
            account_code=pr_l.account_code,
            quantity=pr_l.quantity,
            unit_price=pr_l.unit_price,
            received_qty=0.0,
            invoiced_qty=0.0,
            line_subtotal=line_sub,
            tax_amount=line_tax,
            line_total=line_tot
        )
        po_lines.append(pol)

    po = models.PurchaseOrder(
        po_number=po_num,
        pr_number=pr.pr_number,
        po_date=datetime.date.today(),
        delivery_date=datetime.date.today() + datetime.timedelta(days=14),
        vendor_code=vendor_code,
        tax_code=tax_code,
        subtotal=round(subtotal, 2),
        tax_amount=round(tax_total, 2),
        total_amount=round(subtotal + tax_total, 2),
        status="Draft",
        created_by="Submitter",
        lines=po_lines
    )
    db.add(po)
    pr.status = "Converted to PO"
    db.commit()
    db.refresh(po)
    return po

def apply_po_inventory_receipt(db: Session, po: models.PurchaseOrder) -> None:
    """
    When a Purchase Order is approved, automatically increment inventory on hand
    and append an incoming stock movement to the Stock Movement Ledger.
    """
    for pol in po.lines:
        target_item = None
        if pol.item_code:
            target_item = db.query(models.InventoryItem).filter(models.InventoryItem.item_code == pol.item_code).first()
        if not target_item and pol.description:
            desc_clean = pol.description.strip().lower()
            target_item = db.query(models.InventoryItem).filter(
                (func.lower(models.InventoryItem.item_code) == desc_clean) |
                (func.lower(models.InventoryItem.name) == desc_clean)
            ).first()
            if not target_item:
                target_item = db.query(models.InventoryItem).filter(
                    models.InventoryItem.name.ilike(f"%{pol.description.strip()}%")
                ).first()

        if target_item:
            pol.item_code = target_item.item_code
            existing_mov = db.query(models.StockMovement).filter(
                models.StockMovement.reference_doc == po.po_number,
                models.StockMovement.item_code == target_item.item_code
            ).first()

            if not existing_mov:
                old_qty = target_item.stock_quantity or 0.0
                target_item.stock_quantity = old_qty + pol.quantity
                pol.received_qty = pol.quantity

                # Recalculate weighted average unit cost
                if target_item.stock_quantity > 0:
                    old_cost = target_item.cost_price or 0.0
                    new_val = (max(0.0, old_qty) * old_cost) + (pol.quantity * pol.unit_price)
                    target_item.cost_price = round(new_val / target_item.stock_quantity, 2)

                line_amt = round(pol.quantity * pol.unit_price, 2)
                db.add(models.StockMovement(
                    movement_date=po.po_date,
                    item_code=target_item.item_code,
                    item_name=target_item.name,
                    movement_type="PURCHASE_RECEIPT",
                    reference_doc=po.po_number,
                    quantity=pol.quantity,
                    unit_cost=pol.unit_price,
                    total_cost=line_amt,
                    notes=f"Purchased from {po.vendor_code} on PO {po.po_number}"
                ))
    db.commit()

def approve_grn_and_post_gl(db: Session, grn_id: int, approver: str = "Checker (Finance Manager)") -> models.GoodsReceiptNote:
    grn = db.query(models.GoodsReceiptNote).filter(models.GoodsReceiptNote.id == grn_id).first()
    if not grn:
        raise ValueError("GRN not found")
    if grn.status == "Approved":
        return grn

    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_number == grn.po_number).first()
    if not po:
        raise ValueError(f"Associated PO {grn.po_number} not found")

    voucher_no = get_next_sequence_number(db, "PO-GRN", models.JournalVoucher, "voucher_no")
    voucher_lines = []
    total_received_amount = 0.0

    # Auto-accounting on GRN:
    # Dr Expense / Asset Account (PO Line Account)
    # Cr GRN Accrual (Account 2010)
    for line in grn.lines:
        line_amt = round(line.received_qty * line.unit_price, 2)
        total_received_amount += line_amt
        voucher_lines.append({
            "account_code": line.account_code,
            "description": f"GRN {grn.grn_number} receipt: {line.description}",
            "debit": line_amt,
            "credit": 0.0
        })
        # update po line received qty
        if line.po_line_id:
            pol = db.query(models.POLine).filter(models.POLine.id == line.po_line_id).first()
            if pol:
                pol.received_qty += line.received_qty
                if not line.item_code and pol.item_code:
                    line.item_code = pol.item_code

        # Update Inventory Stock if item_code is present or matching
        target_item = None
        if line.item_code:
            target_item = db.query(models.InventoryItem).filter(models.InventoryItem.item_code == line.item_code).first()
        if not target_item and line.description:
            desc_clean = line.description.strip().lower()
            target_item = db.query(models.InventoryItem).filter(
                (func.lower(models.InventoryItem.item_code) == desc_clean) |
                (func.lower(models.InventoryItem.name) == desc_clean)
            ).first()
            if not target_item:
                target_item = db.query(models.InventoryItem).filter(
                    models.InventoryItem.name.ilike(f"%{line.description.strip()}%")
                ).first()

        if target_item:
            line.item_code = target_item.item_code
            # Check if stock movement for this PO & item was already recorded by PO creation
            existing_mov = db.query(models.StockMovement).filter(
                models.StockMovement.reference_doc == grn.po_number,
                models.StockMovement.item_code == target_item.item_code
            ).first()

            if not existing_mov:
                old_qty = target_item.stock_quantity or 0.0
                target_item.stock_quantity = old_qty + line.received_qty
                # Update weighted average cost price
                if target_item.stock_quantity > 0:
                    old_cost = target_item.cost_price or 0.0
                    new_val = (max(0.0, old_qty) * old_cost) + (line.received_qty * line.unit_price)
                    target_item.cost_price = round(new_val / target_item.stock_quantity, 2)
                # Log stock movement
                db.add(models.StockMovement(
                    movement_date=grn.grn_date,
                    item_code=target_item.item_code,
                    item_name=target_item.name,
                    movement_type="PURCHASE_RECEIPT",
                    reference_doc=grn.grn_number,
                    quantity=line.received_qty,
                    unit_cost=line.unit_price,
                    total_cost=line_amt,
                    notes=f"Purchase receipt via GRN {grn.grn_number} (PO: {grn.po_number})"
                ))
            else:
                existing_mov.notes = f"Purchase receipt verified via GRN {grn.grn_number} (PO: {grn.po_number})"

    voucher_lines.append({
        "account_code": "2010",  # GRN Accrual Account
        "account_name": "GRN Accrual (Uninvoiced Receipts)",
        "description": f"GRN Accrual for GRN {grn.grn_number} (PO {grn.po_number})",
        "debit": 0.0,
        "credit": round(total_received_amount, 2)
    })

    create_journal_voucher_entry(
        db=db,
        voucher_no=voucher_no,
        posting_date=grn.grn_date,
        source_module="PO-GRN",
        document_ref=grn.grn_number,
        description=f"GRN Receipt Voucher for {grn.grn_number} (PO: {grn.po_number})",
        lines=voucher_lines,
        created_by=grn.created_by,
        approved_by=approver,
        status="Approved"
    )

    # Check PO completion
    all_received = all(pol.received_qty >= pol.quantity for pol in po.lines)
    po.status = "Fully Received" if all_received else "Partially Received"

    grn.status = "Approved"
    grn.voucher_no = voucher_no
    grn.approved_by = approver
    db.commit()
    db.refresh(grn)
    return grn

def approve_ap_invoice_and_post_gl(db: Session, invoice_id: int, approver: str = "Checker (Finance Manager)") -> models.APInvoice:
    inv = db.query(models.APInvoice).filter(models.APInvoice.id == invoice_id).first()
    if not inv:
        raise ValueError("AP Invoice not found")
    if inv.status == "Approved":
        return inv

    voucher_no = get_next_sequence_number(db, "AP-INV", models.JournalVoucher, "voucher_no")
    voucher_lines = []

    if inv.invoice_mode == "Mode_A_PO":
        # Mode A: PO/GRN-Backed (3-Way Match)
        # Dr GRN Accrual (2010) - reversing accrual
        # Dr Input VAT (1150)
        # Cr Accounts Payable (2000)
        voucher_lines.append({
            "account_code": "2010",
            "account_name": "GRN Accrual (Uninvoiced Receipts)",
            "description": f"Clear GRN Accrual on AP Inv {inv.invoice_number} (PO: {inv.po_number})",
            "debit": round(inv.subtotal, 2),
            "credit": 0.0
        })
        if inv.tax_amount > 0:
            voucher_lines.append({
                "account_code": "1150",
                "account_name": "Input VAT / Tax Recoverable",
                "description": f"Input VAT for AP Inv {inv.invoice_number}",
                "debit": round(inv.tax_amount, 2),
                "credit": 0.0
            })
        voucher_lines.append({
            "account_code": "2000",
            "account_name": "Accounts Payable Control",
            "description": f"Payable to {inv.vendor_code} on Inv {inv.invoice_number} (Ref: {inv.vendor_invoice_ref})",
            "debit": 0.0,
            "credit": round(inv.total_amount, 2)
        })

        # Update invoiced_qty on PO lines if PO exists
        if inv.po_number:
            po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_number == inv.po_number).first()
            if po:
                for pol in po.lines:
                    pol.invoiced_qty = pol.quantity

    else:
        # Mode B: Direct Expense Invoice
        # Dr Expense Account
        # Dr Input VAT (1150)
        # Cr Accounts Payable (2000)
        exp_code = inv.expense_account_code or "5000"
        exp_acc = db.query(models.Account).filter(models.Account.account_code == exp_code).first()
        exp_name = exp_acc.account_name if exp_acc else "Operating Expense"

        voucher_lines.append({
            "account_code": exp_code,
            "account_name": exp_name,
            "description": f"Direct Expense for AP Inv {inv.invoice_number} ({inv.vendor_invoice_ref})",
            "debit": round(inv.subtotal, 2),
            "credit": 0.0
        })
        if inv.tax_amount > 0:
            voucher_lines.append({
                "account_code": "1150",
                "account_name": "Input VAT / Tax Recoverable",
                "description": f"Input VAT for AP Inv {inv.invoice_number}",
                "debit": round(inv.tax_amount, 2),
                "credit": 0.0
            })
        voucher_lines.append({
            "account_code": "2000",
            "account_name": "Accounts Payable Control",
            "description": f"Payable to {inv.vendor_code} on Inv {inv.invoice_number}",
            "debit": 0.0,
            "credit": round(inv.total_amount, 2)
        })

    create_journal_voucher_entry(
        db=db,
        voucher_no=voucher_no,
        posting_date=inv.invoice_date,
        source_module="AP-INV",
        document_ref=inv.invoice_number,
        description=f"AP Invoice {inv.invoice_number} from {inv.vendor_code} (Vendor Ref: {inv.vendor_invoice_ref})",
        lines=voucher_lines,
        created_by=inv.created_by,
        approved_by=approver,
        status="Approved"
    )

    inv.status = "Approved"
    inv.voucher_no = voucher_no
    inv.approved_by = approver
    db.commit()
    db.refresh(inv)
    return inv

def approve_ap_payment_and_post_gl(db: Session, payment_id: int, approver: str = "Checker (Finance Manager)") -> models.APPayment:
    pmt = db.query(models.APPayment).filter(models.APPayment.id == payment_id).first()
    if not pmt:
        raise ValueError("AP Payment not found")
    if pmt.status == "Approved":
        return pmt

    voucher_no = get_next_sequence_number(db, "AP-PMT", models.JournalVoucher, "voucher_no")

    disbursing_account = pmt.bank_account_code
    disbursing_name = pmt.bank_account.account_name if pmt.bank_account else "Bank Account"
    if pmt.payment_method in ["Cash", "Cash (Petty Cash)"]:
        disbursing_account = "1010"
        petty = db.query(models.Account).filter(models.Account.account_code == "1010").first()
        disbursing_name = petty.account_name if petty else "Petty Cash Account"

    # Accounting on AP Payment:
    # Dr Accounts Payable Control (2000)
    # Cr Bank Account / Petty Cash (1000 / 1010)
    voucher_lines = [
        {
            "account_code": "2000",
            "account_name": "Accounts Payable Control",
            "description": f"Payment to {pmt.vendor_code} via {pmt.payment_ref} ({pmt.payment_method})",
            "debit": round(pmt.total_amount, 2),
            "credit": 0.0
        },
        {
            "account_code": disbursing_account,
            "account_name": disbursing_name,
            "description": f"Disbursement {pmt.payment_number} ({pmt.payment_ref})",
            "debit": 0.0,
            "credit": round(pmt.total_amount, 2)
        }
    ]

    create_journal_voucher_entry(
        db=db,
        voucher_no=voucher_no,
        posting_date=pmt.payment_date,
        source_module="AP-PMT",
        document_ref=pmt.payment_number,
        description=f"AP Payment {pmt.payment_number} to {pmt.vendor_code} ({pmt.payment_ref})",
        lines=voucher_lines,
        created_by=pmt.created_by,
        approved_by=approver,
        status="Approved"
    )

    # Apply payment to invoices
    for line in pmt.lines:
        inv = db.query(models.APInvoice).filter(models.APInvoice.id == line.ap_invoice_id).first()
        if inv:
            inv.paid_amount = round(inv.paid_amount + line.amount_paid, 2)
            if inv.paid_amount >= inv.total_amount - 0.01:
                inv.payment_status = "Paid"
            else:
                inv.payment_status = "Partially Paid"

    pmt.status = "Approved"
    pmt.voucher_no = voucher_no
    pmt.approved_by = approver
    db.commit()
    db.refresh(pmt)
    return pmt

def approve_ar_invoice_and_post_gl(db: Session, invoice_id: int, approver: str = "Checker (Finance Manager)") -> models.ARInvoice:
    inv = db.query(models.ARInvoice).filter(models.ARInvoice.id == invoice_id).first()
    if not inv:
        raise ValueError("AR Invoice not found")
    if inv.status == "Approved":
        return inv

    voucher_no = get_next_sequence_number(db, "AR-INV", models.JournalVoucher, "voucher_no")
    voucher_lines = []

    # Accounting on AR Invoice:
    # Dr Accounts Receivable Control (1100) - Gross Total
    # Cr Revenue Account(s) - Net Amount per line
    # Cr Output VAT / Tax Payable (2020) - Total Tax Amount
    voucher_lines.append({
        "account_code": "1100",
        "account_name": "Accounts Receivable Control",
        "description": f"Receivable from {inv.customer_code} on Invoice {inv.invoice_number}",
        "debit": round(inv.total_amount, 2),
        "credit": 0.0
    })

    # Group lines by revenue account
    revenue_totals = {}
    for line in inv.lines:
        acc = line.revenue_account_code or "4000"
        revenue_totals[acc] = revenue_totals.get(acc, 0.0) + line.net_amount

    for acc_code, net_amt in revenue_totals.items():
        acc = db.query(models.Account).filter(models.Account.account_code == acc_code).first()
        acc_name = acc.account_name if acc else "Sales Revenue"
        voucher_lines.append({
            "account_code": acc_code,
            "account_name": acc_name,
            "description": f"Sales Revenue on Invoice {inv.invoice_number}",
            "debit": 0.0,
            "credit": round(net_amt, 2)
        })

    if inv.tax_amount > 0:
        voucher_lines.append({
            "account_code": "2020",
            "account_name": "Output VAT / Tax Payable",
            "description": f"Output VAT on Invoice {inv.invoice_number}",
            "debit": 0.0,
            "credit": round(inv.tax_amount, 2)
        })

    create_journal_voucher_entry(
        db=db,
        voucher_no=voucher_no,
        posting_date=inv.invoice_date,
        source_module="AR-INV",
        document_ref=inv.invoice_number,
        description=f"AR Sales Invoice {inv.invoice_number} to {inv.customer_code}",
        lines=voucher_lines,
        created_by=inv.created_by,
        approved_by=approver,
        status="Approved"
    )

    # Process inventory deduction and COGS entry for items sold
    total_cogs_amount = 0.0
    cogs_breakdown = []
    for line in inv.lines:
        target_item = None
        if line.item_code:
            target_item = db.query(models.InventoryItem).filter(models.InventoryItem.item_code == line.item_code).first()
        if not target_item and line.description:
            desc_clean = line.description.strip().lower()
            target_item = db.query(models.InventoryItem).filter(
                (func.lower(models.InventoryItem.item_code) == desc_clean) |
                (func.lower(models.InventoryItem.name) == desc_clean)
            ).first()
            if not target_item:
                target_item = db.query(models.InventoryItem).filter(
                    models.InventoryItem.name.ilike(f"%{line.description.strip()}%")
                ).first()

        if target_item:
            line.item_code = target_item.item_code
            existing_mov = db.query(models.StockMovement).filter(
                models.StockMovement.reference_doc == inv.invoice_number,
                models.StockMovement.item_code == target_item.item_code
            ).first()

            if not existing_mov:
                target_item.stock_quantity = max(0.0, (target_item.stock_quantity or 0.0) - line.quantity)
                line_cost = round(line.quantity * (target_item.cost_price or 0.0), 2)
                total_cogs_amount += line_cost
                cogs_breakdown.append(f"{target_item.name}: ${line_cost}")

                # Log stock movement
                db.add(models.StockMovement(
                    movement_date=inv.invoice_date,
                    item_code=target_item.item_code,
                    item_name=target_item.name,
                    movement_type="SALES_DISPATCH",
                    reference_doc=inv.invoice_number,
                    quantity=-line.quantity,
                    unit_cost=target_item.cost_price or 0.0,
                    total_cost=line_cost,
                    notes=f"Sold to {inv.customer_code} on Invoice {inv.invoice_number}"
                ))

    if total_cogs_amount > 0:
        cogs_vno = get_next_sequence_number(db, "GL-COGS", models.JournalVoucher, "voucher_no")
        create_journal_voucher_entry(
            db=db,
            voucher_no=cogs_vno,
            posting_date=inv.invoice_date,
            source_module="GL-JV",
            document_ref=inv.invoice_number,
            description=f"Cost of Goods Sold (COGS) Recognition for Invoice {inv.invoice_number}",
            lines=[
                {"account_code": "5000", "account_name": "Cost of Goods Sold / Merchandise Stock", "description": f"COGS for Inv {inv.invoice_number}", "debit": round(total_cogs_amount, 2), "credit": 0.0},
                {"account_code": "1200", "account_name": "Inventory / Merchandise Store Stock", "description": f"Relieve inventory on Inv {inv.invoice_number}", "debit": 0.0, "credit": round(total_cogs_amount, 2)}
            ],
            created_by="System",
            approved_by="System",
            status="Approved"
        )

    inv.status = "Approved"
    inv.voucher_no = voucher_no
    inv.approved_by = approver
    db.commit()
    db.refresh(inv)
    return inv

def approve_ar_receipt_and_post_gl(db: Session, receipt_id: int, approver: str = "Checker (Finance Manager)") -> models.ARReceipt:
    rcpt = db.query(models.ARReceipt).filter(models.ARReceipt.id == receipt_id).first()
    if not rcpt:
        raise ValueError("AR Receipt not found")
    if rcpt.status == "Approved":
        return rcpt

    voucher_no = get_next_sequence_number(db, "AR-RCPT", models.JournalVoucher, "voucher_no")

    receiving_account = rcpt.bank_account_code
    receiving_name = rcpt.bank_account.account_name if rcpt.bank_account else "Bank Account"
    method_val = getattr(rcpt, "receipt_method", None) or getattr(rcpt, "payment_method", "Bank Wire")
    if method_val in ["Cash", "Cash (Petty Cash)"]:
        receiving_account = "1010"
        petty = db.query(models.Account).filter(models.Account.account_code == "1010").first()
        receiving_name = petty.account_name if petty else "Petty Cash Account"

    # Accounting on AR Receipt:
    # Dr Bank Account / Petty Cash (1000 / 1010)
    # Cr Accounts Receivable Control (1100)
    voucher_lines = [
        {
            "account_code": receiving_account,
            "account_name": receiving_name,
            "description": f"Collection from {rcpt.customer_code} ({rcpt.receipt_ref}) via {method_val}",
            "debit": round(rcpt.total_amount, 2),
            "credit": 0.0
        },
        {
            "account_code": "1100",
            "account_name": "Accounts Receivable Control",
            "description": f"Clear AR for {rcpt.customer_code} on Receipt {rcpt.receipt_number}",
            "debit": 0.0,
            "credit": round(rcpt.total_amount, 2)
        }
    ]

    create_journal_voucher_entry(
        db=db,
        voucher_no=voucher_no,
        posting_date=rcpt.receipt_date,
        source_module="AR-RCPT",
        document_ref=rcpt.receipt_number,
        description=f"AR Bank Receipt {rcpt.receipt_number} from {rcpt.customer_code} ({rcpt.receipt_ref})",
        lines=voucher_lines,
        created_by=rcpt.created_by,
        approved_by=approver,
        status="Approved"
    )

    # Apply receipt to invoices
    for line in rcpt.lines:
        inv = db.query(models.ARInvoice).filter(models.ARInvoice.id == line.ar_invoice_id).first()
        if inv:
            inv.paid_amount = round(inv.paid_amount + line.amount_received, 2)
            if inv.paid_amount >= inv.total_amount - 0.01:
                inv.payment_status = "Paid"
            else:
                inv.payment_status = "Partially Paid"

    rcpt.status = "Approved"
    rcpt.voucher_no = voucher_no
    rcpt.approved_by = approver
    db.commit()
    db.refresh(rcpt)
    return rcpt

# Financial Statement Engines
def calculate_trial_balance(db: Session, as_of_date: Optional[datetime.date] = None) -> schemas.TrialBalanceReport:
    if not as_of_date:
        as_of_date = datetime.date.today()

    accounts = db.query(models.Account).order_by(models.Account.account_code).all()

    # Query period debits and credits from approved vouchers up to as_of_date (excluding Opening Balance OB module)
    period_query = db.query(
        models.VoucherLine.account_code,
        func.sum(models.VoucherLine.debit).label("sum_debit"),
        func.sum(models.VoucherLine.credit).label("sum_credit")
    ).join(models.JournalVoucher).filter(
        models.JournalVoucher.status == "Approved",
        models.JournalVoucher.source_module != "OB",
        models.JournalVoucher.posting_date <= as_of_date
    ).group_by(models.VoucherLine.account_code).all()

    period_map = {row.account_code: (row.sum_debit or 0.0, row.sum_credit or 0.0) for row in period_query}

    rows = []
    tot_op_dr = 0.0
    tot_op_cr = 0.0
    tot_per_dr = 0.0
    tot_per_cr = 0.0
    tot_cls_dr = 0.0
    tot_cls_cr = 0.0

    for acc in accounts:
        op_dr = acc.opening_debit or 0.0
        op_cr = acc.opening_credit or 0.0
        per_dr, per_cr = period_map.get(acc.account_code, (0.0, 0.0))

        tot_op_dr += op_dr
        tot_op_cr += op_cr
        tot_per_dr += per_dr
        tot_per_cr += per_cr

        # Compute closing balance based on normal account balance
        # Asset, Expense: Normal Balance is Debit
        # Liability, Equity, Revenue: Normal Balance is Credit
        if acc.account_type in ["Asset", "Expense"]:
            net = (op_dr - op_cr) + (per_dr - per_cr)
            if net >= 0:
                cls_dr = net
                cls_cr = 0.0
            else:
                cls_dr = 0.0
                cls_cr = abs(net)
        else:
            net = (op_cr - op_dr) + (per_cr - per_dr)
            if net >= 0:
                cls_dr = 0.0
                cls_cr = net
            else:
                cls_dr = abs(net)
                cls_cr = 0.0

        tot_cls_dr += cls_dr
        tot_cls_cr += cls_cr

        rows.append(schemas.TrialBalanceRow(
            account_code=acc.account_code,
            account_name=acc.account_name,
            account_type=acc.account_type,
            sub_category=acc.sub_category,
            opening_debit=round(op_dr, 2),
            opening_credit=round(op_cr, 2),
            period_debit=round(per_dr, 2),
            period_credit=round(per_cr, 2),
            closing_debit=round(cls_dr, 2),
            closing_credit=round(cls_cr, 2)
        ))

    is_balanced = (
        abs(tot_op_dr - tot_op_cr) < 0.05 and
        abs(tot_per_dr - tot_per_cr) < 0.05 and
        abs(tot_cls_dr - tot_cls_cr) < 0.05
    )

    return schemas.TrialBalanceReport(
        as_of_date=as_of_date,
        rows=rows,
        total_opening_debit=round(tot_op_dr, 2),
        total_opening_credit=round(tot_op_cr, 2),
        total_period_debit=round(tot_per_dr, 2),
        total_period_credit=round(tot_per_cr, 2),
        total_closing_debit=round(tot_cls_dr, 2),
        total_closing_credit=round(tot_cls_cr, 2),
        is_balanced=is_balanced
    )

def calculate_profit_and_loss(
    db: Session,
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None
) -> schemas.ProfitLossReport:
    if not to_date:
        to_date = datetime.date.today()
    if not from_date:
        from_date = datetime.date(to_date.year, 1, 1)

    accounts = db.query(models.Account).filter(
        models.Account.account_type.in_(["Revenue", "Expense"])
    ).order_by(models.Account.account_code).all()

    # Query period lines in date range
    vlines = db.query(
        models.VoucherLine.account_code,
        func.sum(models.VoucherLine.debit).label("sum_debit"),
        func.sum(models.VoucherLine.credit).label("sum_credit")
    ).join(models.JournalVoucher).filter(
        models.JournalVoucher.status == "Approved",
        models.JournalVoucher.source_module != "OB",
        models.JournalVoucher.posting_date >= from_date,
        models.JournalVoucher.posting_date <= to_date
    ).group_by(models.VoucherLine.account_code).all()

    movement_map = {row.account_code: (row.sum_debit or 0.0, row.sum_credit or 0.0) for row in vlines}

    revenue_items = []
    cogs_items = []
    opex_items = []

    total_revenue = 0.0
    total_cogs = 0.0
    total_opex = 0.0

    for acc in accounts:
        # Check if there is budget for this account
        budget_row = db.query(models.Budget).filter(
            models.Budget.account_code == acc.account_code,
            models.Budget.fiscal_year == to_date.year
        ).first()
        budget_amt = budget_row.annual_budget if budget_row else 0.0

        dr, cr = movement_map.get(acc.account_code, (0.0, 0.0))

        if acc.account_type == "Revenue":
            # Normal credit balance
            amt = round(cr - dr, 2)
            if amt != 0 or budget_amt > 0:
                revenue_items.append({
                    "account_code": acc.account_code,
                    "account_name": acc.account_name,
                    "sub_category": acc.sub_category,
                    "amount": amt,
                    "budget": budget_amt,
                    "variance": round(amt - budget_amt, 2)
                })
                total_revenue += amt

        elif acc.account_type == "Expense":
            # Normal debit balance
            amt = round(dr - cr, 2)
            item = {
                "account_code": acc.account_code,
                "account_name": acc.account_name,
                "sub_category": acc.sub_category,
                "amount": amt,
                "budget": budget_amt,
                "variance": round(budget_amt - amt, 2)  # positive means favorable (under budget)
            }
            if acc.sub_category in ["Cost of Goods Sold", "Direct Costs", "Cost of Sales"]:
                cogs_items.append(item)
                total_cogs += amt
            else:
                opex_items.append(item)
                total_opex += amt

    gross_profit = round(total_revenue - total_cogs, 2)
    gross_margin_pct = round((gross_profit / total_revenue * 100.0), 2) if total_revenue > 0 else 0.0
    net_profit = round(gross_profit - total_opex, 2)
    net_margin_pct = round((net_profit / total_revenue * 100.0), 2) if total_revenue > 0 else 0.0

    return schemas.ProfitLossReport(
        from_date=from_date,
        to_date=to_date,
        revenue_items=revenue_items,
        total_revenue=round(total_revenue, 2),
        cogs_items=cogs_items,
        total_cogs=round(total_cogs, 2),
        gross_profit=gross_profit,
        gross_margin_pct=gross_margin_pct,
        operating_expenses=opex_items,
        total_operating_expenses=round(total_opex, 2),
        net_profit=net_profit,
        net_margin_pct=net_margin_pct
    )

def calculate_balance_sheet(db: Session, as_of_date: Optional[datetime.date] = None) -> schemas.BalanceSheetReport:
    if not as_of_date:
        as_of_date = datetime.date.today()

    tb = calculate_trial_balance(db, as_of_date)
    pl = calculate_profit_and_loss(db, datetime.date(as_of_date.year, 1, 1), as_of_date)

    asset_items = []
    liability_items = []
    equity_items = []

    total_assets = 0.0
    total_liabilities = 0.0
    total_equity = 0.0

    for row in tb.rows:
        if row.account_type == "Asset":
            balance = round(row.closing_debit - row.closing_credit, 2)
            if balance != 0.0:
                asset_items.append({
                    "account_code": row.account_code,
                    "account_name": row.account_name,
                    "sub_category": row.sub_category,
                    "amount": balance
                })
                total_assets += balance

        elif row.account_type == "Liability":
            balance = round(row.closing_credit - row.closing_debit, 2)
            if balance != 0.0:
                liability_items.append({
                    "account_code": row.account_code,
                    "account_name": row.account_name,
                    "sub_category": row.sub_category,
                    "amount": balance
                })
                total_liabilities += balance

        elif row.account_type == "Equity":
            balance = round(row.closing_credit - row.closing_debit, 2)
            if balance != 0.0:
                equity_items.append({
                    "account_code": row.account_code,
                    "account_name": row.account_name,
                    "sub_category": row.sub_category,
                    "amount": balance
                })
                total_equity += balance

    # CRITICAL: Roll current period Net Profit into Equity
    current_net_profit = pl.net_profit
    equity_items.append({
        "account_code": "PL-ROLL",
        "account_name": "Current Period Net Profit / (Loss)",
        "sub_category": "Retained Earnings Roll-Forward",
        "amount": round(current_net_profit, 2)
    })
    total_equity += current_net_profit

    total_assets = round(total_assets, 2)
    total_liabilities = round(total_liabilities, 2)
    total_equity = round(total_equity, 2)
    total_l_and_e = round(total_liabilities + total_equity, 2)
    variance = round(total_assets - total_l_and_e, 2)
    is_balanced = abs(variance) < 0.05

    return schemas.BalanceSheetReport(
        as_of_date=as_of_date,
        assets=schemas.BalanceSheetSection(
            title="Assets",
            items=asset_items,
            total=total_assets
        ),
        liabilities=schemas.BalanceSheetSection(
            title="Liabilities",
            items=liability_items,
            total=total_liabilities
        ),
        equity=schemas.BalanceSheetSection(
            title="Equity",
            items=equity_items,
            total=total_equity
        ),
        total_assets=total_assets,
        total_liabilities_and_equity=total_l_and_e,
        variance=variance,
        is_balanced=is_balanced
    )

def calculate_tax_return(
    db: Session,
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None
) -> schemas.TaxReturnReport:
    if not to_date:
        to_date = datetime.date.today()
    if not from_date:
        from_date = datetime.date(to_date.year, 1, 1)

    # Box 1: Output Tax (Standard Rated Supplies from Approved AR Invoices)
    ar_std = db.query(models.ARInvoice).filter(
        models.ARInvoice.status == "Approved",
        models.ARInvoice.invoice_date >= from_date,
        models.ARInvoice.invoice_date <= to_date,
        models.ARInvoice.tax_amount > 0
    ).all()
    b1_net = round(sum(inv.subtotal - inv.discount_total for inv in ar_std), 2)
    b1_tax = round(sum(inv.tax_amount for inv in ar_std), 2)

    # Box 2: Zero-Rated / Exempt Supplies from Approved AR Invoices
    ar_zero = db.query(models.ARInvoice).filter(
        models.ARInvoice.status == "Approved",
        models.ARInvoice.invoice_date >= from_date,
        models.ARInvoice.invoice_date <= to_date,
        models.ARInvoice.tax_amount == 0
    ).all()
    b2_net = round(sum(inv.subtotal - inv.discount_total for inv in ar_zero), 2)

    # Box 3: Input Tax (Standard Rated Expenses/Purchases from Approved AP Invoices)
    ap_std = db.query(models.APInvoice).filter(
        models.APInvoice.status == "Approved",
        models.APInvoice.invoice_date >= from_date,
        models.APInvoice.invoice_date <= to_date,
        models.APInvoice.tax_amount > 0
    ).all()
    b3_net = round(sum(inv.subtotal for inv in ap_std), 2)
    b3_tax = round(sum(inv.tax_amount for inv in ap_std), 2)

    # Box 4: Net Tax = Box 1 Output Tax - Box 3 Input Tax
    b4_net_tax = round(b1_tax - b3_tax, 2)
    is_payable = (b4_net_tax >= 0)

    return schemas.TaxReturnReport(
        from_date=from_date,
        to_date=to_date,
        box1_output_standard=schemas.TaxReturnBox(
            box_number="Box 1",
            title="Standard Rated Supplies (Output Tax)",
            net_amount=b1_net,
            tax_amount=b1_tax,
            description="Taxable supplies subject to standard indirect tax (5% VAT) on customer sales."
        ),
        box2_zero_exempt=schemas.TaxReturnBox(
            box_number="Box 2",
            title="Zero-Rated / Exempt Supplies",
            net_amount=b2_net,
            tax_amount=0.0,
            description="Supplies taxed at 0% or exempt from tax."
        ),
        box3_input_standard=schemas.TaxReturnBox(
            box_number="Box 3",
            title="Standard Rated Expenses & Purchases (Input Tax)",
            net_amount=b3_net,
            tax_amount=b3_tax,
            description="Recoverable indirect tax paid on vendor invoices and allowable operating expenses."
        ),
        box4_net_tax=schemas.TaxReturnBox(
            box_number="Box 4",
            title="Net Tax Payable / (Refundable)",
            net_amount=round(b1_net - b3_net, 2),
            tax_amount=b4_net_tax,
            description="Net indirect tax liability payable to the tax authority or refund due."
        ),
        is_payable=is_payable
    )

def get_dashboard_kpis(db: Session) -> schemas.DashboardKPIs:
    today = datetime.date.today()
    start_of_year = datetime.date(today.year, 1, 1)

    pl = calculate_profit_and_loss(db, start_of_year, today)
    tax_ret = calculate_tax_return(db, start_of_year, today)

    # Cash & Bank Balance: sum of closing balances of all 'Bank' sub_category accounts
    bank_accs = db.query(models.Account).filter(models.Account.sub_category == "Bank").all()
    cash_balance = 0.0
    tb = calculate_trial_balance(db, today)
    bank_codes = {b.account_code for b in bank_accs}
    for row in tb.rows:
        if row.account_code in bank_codes:
            cash_balance += (row.closing_debit - row.closing_credit)

    # Open AR: Approved AR Invoices that are Unpaid or Partially Paid
    open_ar_invs = db.query(models.ARInvoice).filter(
        models.ARInvoice.status == "Approved",
        models.ARInvoice.payment_status.in_(["Unpaid", "Partially Paid"])
    ).all()
    open_ar = sum(max(0.0, inv.total_amount - inv.paid_amount) for inv in open_ar_invs)

    # Open AP: Approved AP Invoices that are Unpaid or Partially Paid
    open_ap_invs = db.query(models.APInvoice).filter(
        models.APInvoice.status == "Approved",
        models.APInvoice.payment_status.in_(["Unpaid", "Partially Paid"])
    ).all()
    open_ap = sum(max(0.0, inv.total_amount - inv.paid_amount) for inv in open_ap_invs)

    # Overall Budget Utilization:
    all_budgets = db.query(models.Budget).filter(models.Budget.fiscal_year == today.year).all()
    tot_budget = sum(b.annual_budget for b in all_budgets)
    tot_consumed = 0.0
    for b in all_budgets:
        m = get_account_budget_metrics(db, b.account_code, today.year)
        tot_consumed += m["committed_amount"]

    budget_util_pct = (tot_consumed / tot_budget * 100.0) if tot_budget > 0 else 0.0

    # Count of pending items across all modules
    pending_count = (
        db.query(func.count(models.JournalVoucher.id)).filter(models.JournalVoucher.status == "Pending Approval").scalar() +
        db.query(func.count(models.PurchaseRequisition.id)).filter(models.PurchaseRequisition.status == "Pending Approval").scalar() +
        db.query(func.count(models.PurchaseOrder.id)).filter(models.PurchaseOrder.status == "Pending Approval").scalar() +
        db.query(func.count(models.GoodsReceiptNote.id)).filter(models.GoodsReceiptNote.status == "Pending Approval").scalar() +
        db.query(func.count(models.APInvoice.id)).filter(models.APInvoice.status == "Pending Approval").scalar() +
        db.query(func.count(models.APPayment.id)).filter(models.APPayment.status == "Pending Approval").scalar() +
        db.query(func.count(models.ARInvoice.id)).filter(models.ARInvoice.status == "Pending Approval").scalar() +
        db.query(func.count(models.ARReceipt.id)).filter(models.ARReceipt.status == "Pending Approval").scalar()
    )

    # Inventory Valuation
    inv_items = db.query(models.InventoryItem).all()
    total_inv_val = sum(i.stock_quantity * i.cost_price for i in inv_items)

    return schemas.DashboardKPIs(
        total_revenue=pl.total_revenue,
        total_expenses=pl.total_operating_expenses + pl.total_cogs,
        net_profit=pl.net_profit,
        net_margin_pct=pl.net_margin_pct,
        cash_bank_balance=round(cash_balance, 2),
        open_ar=round(open_ar, 2),
        open_ap=round(open_ap, 2),
        net_tax_payable=tax_ret.box4_net_tax.tax_amount,
        budget_utilization_pct=round(budget_util_pct, 1),
        pending_approvals_count=pending_count,
        total_inventory_valuation=round(total_inv_val, 2)
    )

# Unified Pending Approval List
def get_all_pending_approvals(db: Session) -> List[schemas.ApprovalItemResponse]:
    items = []

    # GL JVs
    gl_jvs = db.query(models.JournalVoucher).filter(models.JournalVoucher.status == "Pending Approval").all()
    for j in gl_jvs:
        items.append(schemas.ApprovalItemResponse(
            module="GL",
            document_id=j.id,
            document_number=j.voucher_no,
            date=j.posting_date,
            party_or_desc=j.description,
            amount=j.total_debit,
            status=j.status,
            created_by=j.created_by,
            created_at=j.created_at
        ))

    # PRs
    prs = db.query(models.PurchaseRequisition).filter(models.PurchaseRequisition.status == "Pending Approval").all()
    for p in prs:
        items.append(schemas.ApprovalItemResponse(
            module="PR",
            document_id=p.id,
            document_number=p.pr_number,
            date=p.pr_date,
            party_or_desc=f"{p.department} Requisition",
            amount=p.total_amount,
            status=p.status,
            created_by=p.created_by,
            created_at=p.created_at
        ))

    # POs
    pos = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.status == "Pending Approval").all()
    for p in pos:
        items.append(schemas.ApprovalItemResponse(
            module="PO",
            document_id=p.id,
            document_number=p.po_number,
            date=p.po_date,
            party_or_desc=f"Vendor: {p.vendor_code}",
            amount=p.total_amount,
            status=p.status,
            created_by=p.created_by,
            created_at=p.created_at
        ))

    # GRNs
    grns = db.query(models.GoodsReceiptNote).filter(models.GoodsReceiptNote.status == "Pending Approval").all()
    for g in grns:
        amt = sum(l.line_amount for l in g.lines)
        items.append(schemas.ApprovalItemResponse(
            module="GRN",
            document_id=g.id,
            document_number=g.grn_number,
            date=g.grn_date,
            party_or_desc=f"PO: {g.po_number}",
            amount=round(amt, 2),
            status=g.status,
            created_by=g.created_by,
            created_at=g.created_at
        ))

    # AP Invoices
    ap_invs = db.query(models.APInvoice).filter(models.APInvoice.status == "Pending Approval").all()
    for a in ap_invs:
        items.append(schemas.ApprovalItemResponse(
            module="AP-INV",
            document_id=a.id,
            document_number=a.invoice_number,
            date=a.invoice_date,
            party_or_desc=f"Vendor: {a.vendor_code} ({a.vendor_invoice_ref})",
            amount=a.total_amount,
            status=a.status,
            created_by=a.created_by,
            created_at=a.created_at
        ))

    # AP Payments
    ap_pmts = db.query(models.APPayment).filter(models.APPayment.status == "Pending Approval").all()
    for p in ap_pmts:
        items.append(schemas.ApprovalItemResponse(
            module="AP-PMT",
            document_id=p.id,
            document_number=p.payment_number,
            date=p.payment_date,
            party_or_desc=f"Vendor: {p.vendor_code} ({p.payment_ref})",
            amount=p.total_amount,
            status=p.status,
            created_by=p.created_by,
            created_at=p.created_at
        ))

    # AR Invoices
    ar_invs = db.query(models.ARInvoice).filter(models.ARInvoice.status == "Pending Approval").all()
    for a in ar_invs:
        items.append(schemas.ApprovalItemResponse(
            module="AR-INV",
            document_id=a.id,
            document_number=a.invoice_number,
            date=a.invoice_date,
            party_or_desc=f"Customer: {a.customer_code}",
            amount=a.total_amount,
            status=a.status,
            created_by=a.created_by,
            created_at=a.created_at
        ))

    # AR Receipts
    ar_rcpts = db.query(models.ARReceipt).filter(models.ARReceipt.status == "Pending Approval").all()
    for r in ar_rcpts:
        items.append(schemas.ApprovalItemResponse(
            module="AR-RCPT",
            document_id=r.id,
            document_number=r.receipt_number,
            date=r.receipt_date,
            party_or_desc=f"Customer: {r.customer_code} ({r.receipt_ref})",
            amount=r.total_amount,
            status=r.status,
            created_by=r.created_by,
            created_at=r.created_at
        ))

    return items


def create_ar_credit_note_and_post_gl(
    db: Session,
    cn_in: schemas.ARCreditNoteCreate,
    created_by: str = "Owner / Accountant"
) -> models.ARCreditNote:
    cn_num = get_next_sequence_number(db, "CN-AR-2026", models.ARCreditNote, "credit_note_number")
    cn_date = cn_in.credit_note_date or datetime.date.today()
    orig_inv = cn_in.original_invoice_number or cn_in.original_invoice_ref
    tot_amt = round(cn_in.total_amount if cn_in.total_amount is not None else (cn_in.total_credit if cn_in.total_credit is not None else cn_in.subtotal + cn_in.tax_amount), 2)
    tax_amt = round(cn_in.tax_amount if cn_in.tax_amount is not None else (tot_amt - cn_in.subtotal), 2)

    cn = models.ARCreditNote(
        credit_note_number=cn_num,
        customer_code=cn_in.customer_code,
        original_invoice_number=orig_inv,
        credit_note_date=cn_date,
        reason=cn_in.reason,
        subtotal=round(cn_in.subtotal, 2),
        tax_code=cn_in.tax_code or "STANDARD_5",
        tax_amount=tax_amt,
        total_amount=tot_amt,
        status="Approved",
        created_by=created_by
    )
    db.add(cn)
    db.commit()
    db.refresh(cn)

    # Accounting for AR Credit Note (Customer Sales Return / Allowance):
    # Dr Sales Revenue / Returns (4000) for subtotal
    # Dr Output VAT (2020) for tax_amount (reversal of tax liability)
    # Cr Accounts Receivable Control (1100) for total_amount
    voucher_no = get_next_sequence_number(db, "AR-CRN", models.JournalVoucher, "voucher_no")
    voucher_lines = [
        {
            "account_code": "4000",
            "account_name": "Sales Revenue - Consumer Goods",
            "description": f"Sales Credit / Return on {cn.credit_note_number} ({cn.reason})",
            "debit": round(cn.subtotal, 2),
            "credit": 0.0
        }
    ]
    if cn.tax_amount > 0:
        voucher_lines.append({
            "account_code": "2020",
            "account_name": "Output VAT / Tax Payable",
            "description": f"Output VAT Adjustment on {cn.credit_note_number}",
            "debit": round(cn.tax_amount, 2),
            "credit": 0.0
        })
    voucher_lines.append({
        "account_code": "1100",
        "account_name": "Accounts Receivable Control",
        "description": f"Credit Customer {cn.customer_code} on {cn.credit_note_number}",
        "debit": 0.0,
        "credit": round(cn.total_amount, 2)
    })

    create_journal_voucher_entry(
        db=db,
        voucher_no=voucher_no,
        posting_date=cn.credit_note_date,
        source_module="AR-INV",
        document_ref=cn.credit_note_number,
        description=f"Sales Credit Note {cn.credit_note_number} to {cn.customer_code} ({cn.reason})",
        lines=voucher_lines,
        created_by=created_by,
        approved_by=created_by,
        status="Approved"
    )

    # If linked to an original invoice, reduce outstanding balance
    if cn.original_invoice_number:
        orig = db.query(models.ARInvoice).filter(models.ARInvoice.invoice_number == cn.original_invoice_number).first()
        if orig:
            orig.paid_amount = round(orig.paid_amount + cn.total_amount, 2)
            if orig.paid_amount >= orig.total_amount - 0.01:
                orig.payment_status = "Paid"
            else:
                orig.payment_status = "Partially Paid"

    cn.voucher_no = voucher_no
    db.commit()
    db.refresh(cn)
    return cn


def create_ap_credit_note_and_post_gl(
    db: Session,
    cn_in: schemas.APCreditNoteCreate,
    created_by: str = "Owner / Accountant"
) -> models.APCreditNote:
    cn_num = get_next_sequence_number(db, "CN-AP-2026", models.APCreditNote, "credit_note_number")
    cn_date = cn_in.credit_note_date or datetime.date.today()
    orig_inv = cn_in.original_invoice_number or cn_in.original_invoice_ref
    tot_amt = round(cn_in.total_amount if cn_in.total_amount is not None else (cn_in.total_credit if cn_in.total_credit is not None else cn_in.subtotal + cn_in.tax_amount), 2)
    tax_amt = round(cn_in.tax_amount if cn_in.tax_amount is not None else (tot_amt - cn_in.subtotal), 2)

    cn = models.APCreditNote(
        credit_note_number=cn_num,
        vendor_code=cn_in.vendor_code,
        original_invoice_number=orig_inv,
        credit_note_date=cn_date,
        reason=cn_in.reason,
        subtotal=round(cn_in.subtotal, 2),
        tax_code=cn_in.tax_code or "STANDARD_5",
        tax_amount=tax_amt,
        total_amount=tot_amt,
        status="Approved",
        created_by=created_by
    )
    db.add(cn)
    db.commit()
    db.refresh(cn)

    # Accounting for AP Credit Note (Purchase Return / Vendor Rebate):
    # Dr Accounts Payable Control (2000) for total_amount (reduces liability)
    # Cr Inventory / Merchandise Store Stock (1200) for subtotal
    # Cr Input VAT (1150) for tax_amount (reversal of input VAT claimed)
    voucher_no = get_next_sequence_number(db, "AP-CRN", models.JournalVoucher, "voucher_no")
    voucher_lines = [
        {
            "account_code": "2000",
            "account_name": "Accounts Payable Control",
            "description": f"Debit Vendor {cn.vendor_code} on {cn.credit_note_number}",
            "debit": round(cn.total_amount, 2),
            "credit": 0.0
        },
        {
            "account_code": "1200",
            "account_name": "Inventory / Merchandise Store Stock",
            "description": f"Purchase Return / Stock Relief on {cn.credit_note_number} ({cn.reason})",
            "debit": 0.0,
            "credit": round(cn.subtotal, 2)
        }
    ]
    if cn.tax_amount > 0:
        voucher_lines.append({
            "account_code": "1150",
            "account_name": "Input VAT / Tax Recoverable",
            "description": f"Input VAT Adjustment on {cn.credit_note_number}",
            "debit": 0.0,
            "credit": round(cn.tax_amount, 2)
        })

    create_journal_voucher_entry(
        db=db,
        voucher_no=voucher_no,
        posting_date=cn.credit_note_date,
        source_module="AP-INV",
        document_ref=cn.credit_note_number,
        description=f"Purchase Credit Note {cn.credit_note_number} from {cn.vendor_code} ({cn.reason})",
        lines=voucher_lines,
        created_by=created_by,
        approved_by=created_by,
        status="Approved"
    )

    # If linked to an original invoice, reduce outstanding balance
    if cn.original_invoice_number:
        orig = db.query(models.APInvoice).filter(models.APInvoice.invoice_number == cn.original_invoice_number).first()
        if orig:
            orig.paid_amount = round(orig.paid_amount + cn.total_amount, 2)
            if orig.paid_amount >= orig.total_amount - 0.01:
                orig.payment_status = "Paid"
            else:
                orig.payment_status = "Partially Paid"

    cn.voucher_no = voucher_no
    db.commit()
    db.refresh(cn)
    return cn

