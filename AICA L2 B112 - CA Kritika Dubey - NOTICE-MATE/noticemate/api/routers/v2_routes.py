"""v2 endpoints: dashboard, structured analysis, extended reconciliation, party register,
legal research, review comments/decisions/history, AI provider status & connection test.
All v1 endpoints are unchanged."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response

from ...services import (ai_gateway, analysis, dashboard, drafting, parties, recon_extended, research, review, taxlaw)
from .. import schemas as S
from ..deps import current_user

router = APIRouter()
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("/dashboard")
def dash(user=Depends(current_user)):
    return dashboard.summary(user)


# ---- AI providers ----
@router.get("/ai/providers")
def providers(user=Depends(current_user)):
    return ai_gateway.status()


@router.post("/ai/providers/{provider}/test")
def test_provider(provider: str, user=Depends(current_user)):
    return ai_gateway.test_connection(user, provider)


# ---- structured analysis ----
@router.post("/cases/{case_id}/analysis/local")
def analysis_local(case_id: int, body: S.AnalysisLocalIn, user=Depends(current_user)):
    return analysis.build_local(user, case_id, body.notice_id)


@router.post("/cases/{case_id}/analysis/ai/prepare")
def analysis_ai_prepare(case_id: int, body: S.AnalysisAIIn, user=Depends(current_user)):
    return analysis.prepare_ai(user, case_id, body.notice_id, body.provider)


@router.post("/ai/submissions/{sid}/ingest-analysis")
def analysis_ingest(sid: int, user=Depends(current_user)):
    return analysis.ingest_ai(user, sid)


@router.get("/cases/{case_id}/analysis")
def analysis_list(case_id: int, user=Depends(current_user)):
    return analysis.list_for_case(user, case_id)


@router.get("/analysis/{aid}")
def analysis_get(aid: int, user=Depends(current_user)):
    return analysis.get(user, aid)


@router.put("/analysis/{aid}")
def analysis_edit(aid: int, body: S.AnalysisEditIn, user=Depends(current_user)):
    return analysis.edit(user, aid, body.content)


@router.post("/analysis/{aid}/decision")
def analysis_decision(aid: int, body: S.DecisionIn, user=Depends(current_user)):
    return analysis.review_decision(user, aid, body.decision, body.comment)


@router.get("/analysis/{aid}/text", response_class=PlainTextResponse)
def analysis_text(aid: int, user=Depends(current_user)):
    return analysis.render_text(analysis.get(user, aid)["content_json"])


@router.get("/analysis/{aid}/docx")
def analysis_docx(aid: int, user=Depends(current_user)):
    a = analysis.get(user, aid)
    return Response(analysis.render_docx(a["content_json"]), media_type=DOCX,
                    headers={"Content-Disposition": f'attachment; filename="analysis_v{a["version"]}_DRAFT.docx"'})


# ---- extended reconciliation ----
@router.post("/cases/{case_id}/recon/match")
def recon_match(case_id: int, body: S.MatchIn, user=Depends(current_user)):
    return recon_extended.run_match(user, case_id, **body.model_dump())


@router.post("/cases/{case_id}/recon/bank-book-vs-ledger")
def recon_bb_ledger(case_id: int, body: S.BankBookLedgerIn, user=Depends(current_user)):
    return recon_extended.run_bank_book_vs_ledger(user, case_id, **body.model_dump())


@router.post("/cases/{case_id}/recon/sales-vs-bank")
def recon_sales_bank(case_id: int, body: S.SalesBankIn, user=Depends(current_user)):
    return recon_extended.run_sales_vs_bank(user, case_id, **body.model_dump())


@router.post("/cases/{case_id}/recon/ais-vs-books")
def recon_ais(case_id: int, body: S.AISIn, user=Depends(current_user)):
    return recon_extended.run_ais_vs_books(user, case_id, **body.model_dump())


@router.post("/cases/{case_id}/recon/debtors-vs-receipts")
def recon_debtors(case_id: int, body: S.DebtorsIn, user=Depends(current_user)):
    return recon_extended.run_debtors_vs_receipts(user, case_id, **body.model_dump())


# ---- party register (lenders / partner capital / customer advances) ----
@router.get("/cases/{case_id}/parties")
def party_list(case_id: int, user=Depends(current_user)):
    return parties.summary(user, case_id)


@router.get("/meta/party-checklists")
def party_checklists():
    return {k: {kk: v[0] for kk, v in d.items()} for k, d in parties.CHECKLISTS.items()}


@router.post("/cases/{case_id}/parties")
def party_add(case_id: int, body: S.PartyIn, user=Depends(current_user)):
    return parties.upsert(user, case_id, **body.model_dump())


@router.put("/cases/{case_id}/parties/{rid}")
def party_update(case_id: int, rid: int, body: S.PartyIn, user=Depends(current_user)):
    return parties.upsert(user, case_id, record_id=rid, **body.model_dump())


@router.delete("/parties/{rid}")
def party_delete(rid: int, user=Depends(current_user)):
    parties.delete(user, rid)
    return {"ok": True}


# ---- legal research ----
@router.get("/research/status")
def research_status(user=Depends(current_user)):
    return research.live_status()


@router.post("/cases/{case_id}/research")
def research_create(case_id: int, body: S.ResearchIn, user=Depends(current_user)):
    return research.create(user, case_id, body.question, body.issue_id)


@router.get("/cases/{case_id}/research")
def research_list(case_id: int, user=Depends(current_user)):
    return research.list_notes(user, case_id)


@router.post("/research/{nid}/ai/prepare")
def research_ai(nid: int, body: S.ResearchAIIn, user=Depends(current_user)):
    return research.prepare_ai(user, nid, body.provider, body.live)


@router.post("/ai/submissions/{sid}/ingest-research")
def research_ingest(sid: int, user=Depends(current_user)):
    return research.ingest_ai(user, sid)


@router.put("/research/{nid}/propositions/{idx}")
def research_prop(nid: int, idx: int, body: S.PropositionIn, user=Depends(current_user)):
    return research.set_proposition_status(user, nid, idx, body.status, body.source_url, body.note)


@router.post("/research/{nid}/propositions/{idx}/promote")
def research_promote(nid: int, idx: int, body: S.PromoteIn, user=Depends(current_user)):
    return research.promote_to_registry(user, nid, idx, body.ref_key)


@router.post("/law/refs/v2")
def add_ref_v2(body: S.LegalRefV2In, user=Depends(current_user)):
    return taxlaw.add_ref(user, **body.model_dump())


@router.post("/law/refs/{ref_key}/verify/v2")
def verify_ref_v2(ref_key: str, body: S.VerifyRefV2In, user=Depends(current_user)):
    return taxlaw.verify_ref(user, ref_key, body.source_url, body.effective_from, body.note)


# ---- review workflow ----
@router.get("/cases/{case_id}/review/history")
def review_history(case_id: int, user=Depends(current_user)):
    return review.history(user, case_id)


@router.get("/cases/{case_id}/review/comments")
def comments(case_id: int, user=Depends(current_user)):
    return review.list_comments(user, case_id)


@router.post("/drafts/{draft_id}/comments")
def add_comment(draft_id: int, body: S.CommentIn, user=Depends(current_user)):
    return review.add_comment(user, draft_id, body.section, body.comment)


@router.post("/comments/{cid}/resolve")
def resolve(cid: int, body: S.ResolveIn, user=Depends(current_user)):
    return review.resolve_comment(user, cid, body.resolution)


@router.post("/drafts/{draft_id}/reject")
def reject(draft_id: int, body: S.RejectIn, user=Depends(current_user)):
    return review.reject(user, draft_id, body.comment, body.decision)


@router.get("/drafts/{a}/diff/{b}")
def diff(a: int, b: int, user=Depends(current_user)):
    return drafting.diff_versions(user, a, b)


@router.get("/cases/{case_id}/annexures")
def annexures(case_id: int, user=Depends(current_user)):
    return drafting.annexure_index(user, case_id)


@router.get("/cases/{case_id}/annexures.csv", response_class=PlainTextResponse)
def annexures_csv(case_id: int, user=Depends(current_user)):
    rows = drafting.annexure_index(user, case_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Annexure", "Description", "Document type", "Relevant queries", "Evidence status", "SHA-256 (prefix)"])
    for r in rows:
        w.writerow([r["label"], r["description"], r["doc_type"], ", ".join(r["relevant_queries"]), ", ".join(r["evidence_status"]),
                    r["sha256_prefix"]])
    return buf.getvalue()
