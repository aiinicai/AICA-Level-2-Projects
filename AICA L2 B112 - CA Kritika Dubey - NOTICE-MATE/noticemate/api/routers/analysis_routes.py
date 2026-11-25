"""Notices, issues, evidence, reconciliation, tax law & computation, client requests."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from ...services import evidence, info_request, issues, notices, reconciliation, taxcalc, taxlaw
from ...services.drafting import select_legal_refs
from .. import schemas as S
from ..deps import current_user

router = APIRouter()


# ---- notices ----
@router.post("/documents/{doc_id}/parse-notice")
def parse_notice(doc_id: int, acknowledge_partial: bool = False, user=Depends(current_user)):
    return notices.create_from_document(user, doc_id, acknowledge_partial=acknowledge_partial)


@router.get("/cases/{case_id}/notices")
def list_notices(case_id: int, user=Depends(current_user)):
    return notices.list_notices(user, case_id)


@router.put("/notices/{notice_id}/field")
def edit_field(notice_id: int, body: S.NoticeFieldIn, user=Depends(current_user)):
    return notices.update_field(user, notice_id, body.field, body.value)


@router.post("/notices/{notice_id}/verify-deadline")
def verify_deadline(notice_id: int, body: S.DeadlineIn, user=Depends(current_user)):
    return notices.verify_deadline(user, notice_id, body.deadline, body.source)


@router.get("/deadlines")
def deadlines(user=Depends(current_user)):
    return notices.upcoming_deadlines(user)


# ---- issues ----
@router.post("/notices/{notice_id}/issues")
def gen_issues(notice_id: int, replace: bool = False, user=Depends(current_user)):
    return issues.generate_from_notice(user, notice_id, replace=replace)


@router.get("/cases/{case_id}/issues")
def list_issues(case_id: int, user=Depends(current_user)):
    return issues.list_issues(user, case_id)


@router.post("/cases/{case_id}/issues")
def add_issue(case_id: int, body: S.IssueIn, user=Depends(current_user)):
    return issues.add_issue(user, case_id, body.query_text, body.category, body.amount)


@router.post("/cases/{case_id}/issues/merge")
def merge_issues(case_id: int, body: S.IssueMergeIn, user=Depends(current_user)):
    target = issues.get_issue(user, body.target_issue_id)
    if target["case_id"] != case_id:
        from ...core.errors import ValidationError
        raise ValidationError("Selected main issue does not belong to this case.")
    return issues.merge_issues(user, body.target_issue_id, body.source_issue_ids, body.query_text)


@router.put("/issues/{issue_id}/query")
def update_issue_query(issue_id: int, body: S.IssueQueryUpdateIn, user=Depends(current_user)):
    return issues.update_query_text(user, issue_id, body.query_text)


@router.put("/issues/{issue_id}/analysis")
def upd_analysis(issue_id: int, body: S.AnalysisUpdateIn, user=Depends(current_user)):
    return issues.update_analysis(user, issue_id, body.updates)


@router.get("/issues/{issue_id}/suggest-strategy")
def suggest(issue_id: int, user=Depends(current_user)):
    return issues.suggest_strategy(user, issue_id)


@router.put("/issues/{issue_id}/strategy")
def strategy(issue_id: int, body: S.StrategyIn, user=Depends(current_user)):
    return issues.set_strategy(user, issue_id, body.strategy, body.reason)


@router.put("/issues/{issue_id}/legal-refs")
def legal_refs(issue_id: int, body: S.SelectRefsIn, user=Depends(current_user)):
    return select_legal_refs(user, issue_id, body.ref_keys)


@router.get("/meta/strategies")
def strategies():
    return issues.STRATEGIES


# ---- evidence ----
@router.post("/cases/{case_id}/evidence/automap")
def automap(case_id: int, user=Depends(current_user)):
    return {"created": evidence.auto_map(user, case_id)}


@router.get("/cases/{case_id}/evidence")
def matrix(case_id: int, user=Depends(current_user)):
    return evidence.matrix(user, case_id)


@router.get("/cases/{case_id}/evidence/gaps")
def gaps(case_id: int, user=Depends(current_user)):
    return evidence.gaps(user, case_id)


@router.put("/evidence/{evidence_id}")
def assess(evidence_id: int, body: S.EvidenceAssessIn, user=Depends(current_user)):
    return evidence.assess(user, evidence_id, **body.model_dump())


# ---- reconciliation ----
@router.post("/cases/{case_id}/recon/bank-vs-book")
def bank_vs_book(case_id: int, body: S.BankBookIn, user=Depends(current_user)):
    return reconciliation.run_bank_vs_book(user, case_id, body.statement_doc, body.book_doc)


@router.post("/cases/{case_id}/recon/cash-chronology")
def cash_chron(case_id: int, body: S.CashChronIn, user=Depends(current_user)):
    mapping = [r.model_dump() for r in body.source_mapping] if body.source_mapping else None
    return reconciliation.run_cash_chronology(user, case_id, body.cash_book_doc, body.statement_doc, body.opening_balance, mapping)


@router.post("/cases/{case_id}/recon/ledger-compare")
def ledger_compare(case_id: int, body: S.LedgerCompareIn, user=Depends(current_user)):
    return reconciliation.run_ledger_compare(user, case_id, **body.model_dump())


@router.post("/cases/{case_id}/recon/fs-tie-out")
def fs(case_id: int, body: S.FSIn, user=Depends(current_user)):
    return reconciliation.run_fs_tie_out(user, case_id, [f.model_dump() for f in body.figures])


@router.get("/cases/{case_id}/recon")
def runs(case_id: int, user=Depends(current_user)):
    return reconciliation.list_runs(user, case_id)


# ---- tax law & computation ----
@router.post("/law/applicable")
def applicable(body: S.LawIn, user=Depends(current_user)):
    return taxlaw.determine_applicable_law(body.year_label, body.label_type, body.notice_date, body.proceeding_type)


@router.get("/law/refs")
def refs(status: str | None = None, user=Depends(current_user)):
    return taxlaw.list_refs(status)


@router.post("/law/refs")
def add_ref(body: S.LegalRefIn, user=Depends(current_user)):
    return taxlaw.add_ref(user, **body.model_dump())


@router.post("/law/refs/{ref_key}/verify")
def verify_ref(ref_key: str, body: S.VerifyRefIn, user=Depends(current_user)):
    return taxlaw.verify_ref(user, ref_key, body.source_url)


@router.post("/law/refs/{ref_key}/unverify")
def unverify_ref(ref_key: str, user=Depends(current_user)):
    return taxlaw.unverify_ref(user, ref_key)


@router.post("/cases/{case_id}/tax/simulate")
def simulate(case_id: int, body: S.TaxSimIn, user=Depends(current_user)):
    return taxcalc.simulate(user, case_id, assessment_year=body.assessment_year, assessee_category=body.assessee_category,
                            returned_income=body.returned_income, additions=[a.model_dump() for a in body.additions])


@router.get("/cases/{case_id}/tax")
def computations(case_id: int, user=Depends(current_user)):
    return taxcalc.list_computations(user, case_id)


# ---- client information requests ----
@router.post("/cases/{case_id}/client-request")
def client_request(case_id: int, include_requires_verification: bool = False, user=Depends(current_user)):
    return info_request.generate(user, case_id, include_requires_verification=include_requires_verification)


@router.post("/cases/{case_id}/client-request/text", response_class=PlainTextResponse)
def client_request_text(case_id: int, include_requires_verification: bool = False, user=Depends(current_user)):
    return info_request.as_text(info_request.generate(user, case_id, include_requires_verification=include_requires_verification,
                                                      require_assessment=False))
