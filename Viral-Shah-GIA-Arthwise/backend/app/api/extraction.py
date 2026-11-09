import os
import json
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, require_role, verify_proposal_access
from backend.app.models.models import ExtractedData, ProposalDocument, CMAProject, Proposal, User, AuditLog
from backend.app.schemas.schemas import (
    ExtractedDataResponse, ExtractedDataUpdate, 
    ManualFinancialsPayload, ManualSingleMetricCreate
)
from backend.app.services.extractor_service import DocumentExtractorService
from backend.app.services.cma_service import generate_default_cma

router = APIRouter(prefix="/proposals/{proposal_id}/extractions", tags=["Data Extraction & Review"])

FS_METRIC_ORDER = {
    # 1. Statement of Profit & Loss (P&L)
    "revenue_from_operations": 10,
    "other_income": 12,
    "total_income": 14,
    "cost_of_goods_sold": 20,
    "employee_benefits_expense": 22,
    "other_expenses": 24,
    "ebitda": 26,
    "finance_costs": 28,
    "depreciation": 30,
    "total_expenses": 32,
    "profit_before_tax": 34,
    "tax_expense": 36,
    "pat": 38,
    
    # 2. Balance Sheet: Equity & Liabilities
    "tangible_net_worth": 50,
    "long_term_borrowings": 52,
    "other_long_term_liabilities": 53,
    "short_term_borrowings": 54,
    "trade_payables": 56,
    "other_current_liabilities": 58,
    "short_term_provisions": 59,
    "current_liabilities": 60,
    "total_liabilities": 62,
    
    # 3. Balance Sheet: Assets
    "fixed_assets": 70,
    "non_current_investments": 71,
    "long_term_loans_advances": 72,
    "current_investments": 73,
    "inventories": 74,
    "trade_receivables": 75,
    "cash_and_bank": 76,
    "short_term_loans_advances": 77,
    "other_current_assets": 78,
    "current_assets": 80,
    "total_assets": 82,

    # 4. Statutory & Banking
    "itr_gross_total_income": 90,
    "itr_total_income": 92,
    "itr_tax_payable": 94,
    "gstr3b_taxable_turnover": 100,
    "gstr3b_total_tax": 102,
    "bank_annual_credits": 110,
    "bank_abb": 112
}

@router.get("", response_model=List[ExtractedDataResponse])
def get_extracted_data(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_proposal_access(proposal_id, current_user, db)
    records = db.query(ExtractedData).filter(ExtractedData.proposal_id == proposal_id).all()
    # Sort strictly by financial period, then standard Financial Statement sequence
    records.sort(key=lambda r: (
        r.financial_period or "",
        FS_METRIC_ORDER.get(r.metric_name, 999),
        r.metric_name
    ))
    return records

@router.post("/reparse")
def reparse_all_documents(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst", "reviewer"]))
):
    """
    Re-runs the spatial document extractor on all uploaded files for this case.
    Replaces obsolete/erroneous extractions with high-confidence figures.
    """
    proposal = verify_proposal_access(proposal_id, current_user, db)
    docs = db.query(ProposalDocument).filter(ProposalDocument.proposal_id == proposal_id).all()
    if not docs:
        raise HTTPException(status_code=400, detail="No uploaded documents found for this case to re-parse.")

    # Remove previous extracted data
    db.query(ExtractedData).filter(ExtractedData.proposal_id == proposal_id).delete()
    db.commit()

    total_extracted = 0
    found_revenue = None

    for doc in docs:
        if not doc.file_path or not os.path.exists(doc.file_path):
            continue
        extracted_items = DocumentExtractorService.extract_document(doc.file_path, doc.category)
        for item in extracted_items:
            rec = ExtractedData(
                proposal_id=proposal_id,
                document_id=doc.id,
                page_or_sheet=item.get("page_or_sheet"),
                financial_period=item.get("financial_period"),
                metric_name=item["metric_name"],
                raw_value=item.get("raw_value"),
                normalized_value=item.get("normalized_value"),
                confidence=item.get("confidence", 0.95),
                verification_status="verified",
                verified_by_user_id=current_user.id
            )
            db.add(rec)
            total_extracted += 1

            if item["metric_name"] == "revenue_from_operations" and item.get("normalized_value"):
                period_str = str(item.get("financial_period") or "")
                if "2024-25" in period_str or not found_revenue:
                    found_revenue = Decimal(str(item["normalized_value"]))

    # Ensure EBITDA is present for all extracted periods
    periods = db.query(ExtractedData.financial_period).filter(ExtractedData.proposal_id == proposal_id).distinct().all()
    for (p_name,) in periods:
        if not p_name:
            continue
        existing_ebitda = db.query(ExtractedData).filter(
            ExtractedData.proposal_id == proposal_id,
            ExtractedData.financial_period == p_name,
            ExtractedData.metric_name == "ebitda"
        ).first()
        if not existing_ebitda:
            tot_inc_rec = db.query(ExtractedData).filter(
                ExtractedData.proposal_id == proposal_id,
                ExtractedData.financial_period == p_name,
                ExtractedData.metric_name == "total_income"
            ).first()
            rev_rec = db.query(ExtractedData).filter(
                ExtractedData.proposal_id == proposal_id,
                ExtractedData.financial_period == p_name,
                ExtractedData.metric_name == "revenue_from_operations"
            ).first()
            cogs_rec = db.query(ExtractedData).filter(
                ExtractedData.proposal_id == proposal_id,
                ExtractedData.financial_period == p_name,
                ExtractedData.metric_name == "cost_of_goods_sold"
            ).first()
            emp_rec = db.query(ExtractedData).filter(
                ExtractedData.proposal_id == proposal_id,
                ExtractedData.financial_period == p_name,
                ExtractedData.metric_name == "employee_benefits_expense"
            ).first()
            oth_rec = db.query(ExtractedData).filter(
                ExtractedData.proposal_id == proposal_id,
                ExtractedData.financial_period == p_name,
                ExtractedData.metric_name == "other_expenses"
            ).first()

            inc_val = (tot_inc_rec.normalized_value if tot_inc_rec else None) or (rev_rec.normalized_value if rev_rec else None)
            if inc_val:
                cogs_val = cogs_rec.normalized_value if cogs_rec else Decimal("0.0")
                emp_val = emp_rec.normalized_value if emp_rec else Decimal("0.0")
                oth_val = oth_rec.normalized_value if oth_rec else Decimal("0.0")
                ebitda_val = inc_val - (cogs_val + emp_val + oth_val)
                doc_id_to_use = (rev_rec.document_id if rev_rec else None) or (tot_inc_rec.document_id if tot_inc_rec else docs[0].id)
                ebitda_rec = ExtractedData(
                    proposal_id=proposal_id,
                    document_id=doc_id_to_use,
                    page_or_sheet="Calculated EBITDA",
                    financial_period=p_name,
                    metric_name="ebitda",
                    raw_value=f"{ebitda_val:,.2f}",
                    normalized_value=ebitda_val,
                    confidence=1.0,
                    verification_status="verified",
                    verified_by_user_id=current_user.id
                )
                db.add(ebitda_rec)
                total_extracted += 1

    db.commit()

    # Automatically anchor CMA Workspace base year to newly extracted turnover
    if found_revenue:
        cma = db.query(CMAProject).filter(CMAProject.proposal_id == proposal_id).first()
        cma_data = generate_default_cma(
            base_turnover_fy25=found_revenue,
            requested_cc_limit=proposal.requested_amount,
            requested_term_loan=proposal.requested_amount * Decimal("0.5")
        )
        if not cma:
            cma = CMAProject(
                proposal_id=proposal_id,
                base_year="FY 2024-25",
                data_json=json.dumps(cma_data),
                is_reconciled=True,
                balance_sheet_diff=Decimal("0.00"),
                cash_flow_diff=Decimal("0.00")
            )
            db.add(cma)
        else:
            cma.data_json = json.dumps(cma_data)
        db.commit()

    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="REPARSE_DOCUMENTS",
        resource_type="extracted_data",
        resource_id=proposal.id,
        details_json=f"Re-parsed {len(docs)} documents. Extracted {total_extracted} verified figures."
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "reparsed_documents_count": len(docs),
        "extracted_metrics_count": total_extracted,
        "message": f"Successfully re-parsed {len(docs)} documents and extracted {total_extracted} verified financial figures!"
    }

@router.post("/manual-financials")
def save_manual_financials(
    proposal_id: str,
    payload: ManualFinancialsPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst", "reviewer"]))
):
    """
    Allows staff to manually enter or edit year-wise Financial Statements (P&L and Balance Sheet).
    Saves as verified metrics and synchronizes to CMA and Underwriting.
    """
    proposal = verify_proposal_access(proposal_id, current_user, db)

    doc = db.query(ProposalDocument).filter(
        ProposalDocument.proposal_id == proposal_id,
        ProposalDocument.category == "financial_statements"
    ).first()
    doc_id = doc.id if doc else "manual_entry"

    saved_count = 0
    base_year_revenue = None

    for entry in payload.entries:
        period = entry.financial_period.strip()

        field_mapping = {
            "revenue_from_operations": entry.revenue_from_operations,
            "other_income": entry.other_income,
            "cost_of_goods_sold": entry.cost_of_goods_sold,
            "employee_benefits_expense": entry.employee_benefits_expense,
            "finance_costs": entry.finance_costs,
            "depreciation": entry.depreciation,
            "other_expenses": entry.other_expenses,
            "tax_expense": entry.tax_expense,
            "pat": entry.pat,
            "tangible_net_worth": entry.tangible_net_worth,
            "long_term_borrowings": entry.long_term_borrowings,
            "other_long_term_liabilities": entry.other_long_term_liabilities,
            "short_term_borrowings": entry.short_term_borrowings,
            "trade_payables": entry.trade_payables,
            "other_current_liabilities": entry.other_current_liabilities,
            "short_term_provisions": entry.short_term_provisions,
            "fixed_assets": entry.fixed_assets,
            "non_current_investments": entry.non_current_investments,
            "long_term_loans_advances": entry.long_term_loans_advances,
            "current_investments": entry.current_investments,
            "inventories": entry.inventories,
            "trade_receivables": entry.trade_receivables,
            "cash_and_bank": entry.cash_and_bank,
            "short_term_loans_advances": entry.short_term_loans_advances,
            "other_current_assets": entry.other_current_assets,
        }

        # Auto-compute totals
        rev = entry.revenue_from_operations or Decimal("0.0")
        oth_inc = entry.other_income or Decimal("0.0")
        tot_inc = rev + oth_inc
        if tot_inc > 0:
            field_mapping["total_income"] = tot_inc

        cogs = entry.cost_of_goods_sold or Decimal("0.0")
        emp = entry.employee_benefits_expense or Decimal("0.0")
        oth_exp = entry.other_expenses or Decimal("0.0")
        if tot_inc > 0:
            field_mapping["ebitda"] = tot_inc - (cogs + emp + oth_exp)

        fin = entry.finance_costs or Decimal("0.0")
        depr = entry.depreciation or Decimal("0.0")
        tot_exp = cogs + emp + fin + depr + oth_exp
        if tot_exp > 0:
            field_mapping["total_expenses"] = tot_exp
            pbt = tot_inc - tot_exp
            field_mapping["profit_before_tax"] = pbt
            if entry.pat is None:
                tax = entry.tax_expense or Decimal("0.0")
                field_mapping["pat"] = pbt - tax

        st_borrow = entry.short_term_borrowings or Decimal("0.0")
        payables = entry.trade_payables or Decimal("0.0")
        oth_cl = entry.other_current_liabilities or Decimal("0.0")
        st_prov = entry.short_term_provisions or Decimal("0.0")
        cl = st_borrow + payables + oth_cl + st_prov
        if cl > 0:
            field_mapping["current_liabilities"] = cl

        tnw = entry.tangible_net_worth or Decimal("0.0")
        lt_borrow = entry.long_term_borrowings or Decimal("0.0")
        oth_lt = entry.other_long_term_liabilities or Decimal("0.0")
        tot_liab = tnw + lt_borrow + oth_lt + cl
        if tot_liab > 0:
            field_mapping["total_liabilities"] = tot_liab

        inv = entry.inventories or Decimal("0.0")
        rec = entry.trade_receivables or Decimal("0.0")
        cash = entry.cash_and_bank or Decimal("0.0")
        c_inv = entry.current_investments or Decimal("0.0")
        st_loans = entry.short_term_loans_advances or Decimal("0.0")
        oth_ca = entry.other_current_assets or Decimal("0.0")
        ca = inv + rec + cash + c_inv + st_loans + oth_ca
        if ca > 0:
            field_mapping["current_assets"] = ca

        fa = entry.fixed_assets or Decimal("0.0")
        nc_inv = entry.non_current_investments or Decimal("0.0")
        lt_loans = entry.long_term_loans_advances or Decimal("0.0")
        tot_assets = fa + nc_inv + lt_loans + ca
        if tot_assets > 0:
            field_mapping["total_assets"] = tot_assets

        if ("2024-25" in period or "audited" in period.lower()) and rev > 0:
            base_year_revenue = rev
        elif not base_year_revenue and rev > 0:
            base_year_revenue = rev

        for metric_name, val in field_mapping.items():
            if val is None:
                continue
            existing = db.query(ExtractedData).filter(
                ExtractedData.proposal_id == proposal_id,
                ExtractedData.metric_name == metric_name,
                ExtractedData.financial_period == period
            ).first()

            if existing:
                existing.normalized_value = val
                existing.raw_value = f"{val:,.2f}"
                existing.verification_status = "verified"
                existing.confidence = 1.0
                existing.page_or_sheet = "Manual Staff Entry"
                existing.verified_by_user_id = current_user.id
            else:
                new_item = ExtractedData(
                    proposal_id=proposal_id,
                    document_id=doc_id,
                    page_or_sheet="Manual Staff Entry",
                    financial_period=period,
                    metric_name=metric_name,
                    raw_value=f"{val:,.2f}",
                    normalized_value=val,
                    confidence=1.0,
                    verification_status="verified",
                    verified_by_user_id=current_user.id
                )
                db.add(new_item)
            saved_count += 1

    db.commit()

    if payload.sync_to_cma and base_year_revenue:
        cma = db.query(CMAProject).filter(CMAProject.proposal_id == proposal_id).first()
        cma_data = generate_default_cma(
            base_turnover_fy25=base_year_revenue,
            requested_cc_limit=proposal.requested_amount,
            requested_term_loan=proposal.requested_amount * Decimal("0.5")
        )
        if not cma:
            cma = CMAProject(
                proposal_id=proposal_id,
                base_year="FY 2024-25",
                data_json=json.dumps(cma_data),
                is_reconciled=True,
                balance_sheet_diff=Decimal("0.00"),
                cash_flow_diff=Decimal("0.00")
            )
            db.add(cma)
        else:
            cma.data_json = json.dumps(cma_data)
        db.commit()

    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="MANUAL_FINANCIALS_ENTRY",
        resource_type="extracted_data",
        resource_id=proposal.id,
        details_json=f"Staff manually saved {saved_count} metrics across {len(payload.entries)} periods."
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "saved_metrics_count": saved_count,
        "message": f"Successfully saved {saved_count} financial metrics across {len(payload.entries)} periods!"
    }

@router.patch("/{record_id}", response_model=ExtractedDataResponse)
def update_extracted_figure(
    proposal_id: str,
    record_id: str,
    update_in: ExtractedDataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst", "reviewer"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    rec = db.query(ExtractedData).filter(
        ExtractedData.id == record_id,
        ExtractedData.proposal_id == proposal_id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Extracted record not found")
        
    old_status = rec.verification_status
    old_val = str(rec.normalized_value)
    
    if update_in.normalized_value is not None:
        rec.normalized_value = update_in.normalized_value
    rec.verification_status = update_in.verification_status
    if update_in.reviewer_notes:
        rec.reviewer_notes = update_in.reviewer_notes
    rec.verified_by_user_id = current_user.id
    
    db.commit()
    db.refresh(rec)
    
    audit = AuditLog(
        user_id=current_user.id,
        client_id=proposal.client_id,
        proposal_id=proposal.id,
        action="VERIFY_DATA",
        resource_type="extracted_data",
        resource_id=rec.id,
        details_json=f"Metric '{rec.metric_name}': status {old_status}->{rec.verification_status}, val {old_val}->{rec.normalized_value}"
    )
    db.add(audit)
    db.commit()
    
    return rec

@router.delete("/{record_id}")
def delete_extracted_record(
    proposal_id: str,
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "analyst", "reviewer"]))
):
    proposal = verify_proposal_access(proposal_id, current_user, db)
    rec = db.query(ExtractedData).filter(
        ExtractedData.id == record_id,
        ExtractedData.proposal_id == proposal_id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Extracted record not found")
    db.delete(rec)
    db.commit()
    return {"success": True, "message": "Record deleted"}
