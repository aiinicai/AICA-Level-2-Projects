"""
FastAPI backend for the CA PracticeOS Compliance AI Agent Layer.
Wed 16 Sep: setup. Thu 17 Sep: Agent 1 (Onboarding). Fri 18 Sep: Agent 3
(Compliance) - the product's headline / protected-priority feature.
Sat 19 Sep: Agent 2 (Drafting), wired into Agent 3.
Fri 19 Sep (later): multi-tenant auth (signup/approval/login) + team
management + tenant-scoped client storage, mounted from auth_routes.py.
"""
import csv
import io
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.compliance import CHECKLISTS, ComplianceAgent
from agents.drafting import DraftingAgent
from agents.onboarding import OnboardingAgent
from auth_routes import router as auth_router
from db import Base, engine
from schema import CLIENT_MASTER_HEADERS, to_client_master_row

app = FastAPI(title="CA PracticeOS Compliance - AI Agent Layer")

# The L1 app (CA_PracticeOS_Compliance.html) calls this backend directly from
# the browser - it may be opened as a local file (origin "null") or served
# from any local/static host, so origins can't be pinned to one value. No
# cookies/auth are used by this API, so a permissive origin policy here does
# not expose credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
app.include_router(auth_router)

_onboarding_agent: OnboardingAgent | None = None
_compliance_agent: ComplianceAgent | None = None
_drafting_agent: DraftingAgent | None = None


def get_onboarding_agent() -> OnboardingAgent:
    global _onboarding_agent
    if _onboarding_agent is None:
        _onboarding_agent = OnboardingAgent()
    return _onboarding_agent


def get_compliance_agent() -> ComplianceAgent:
    global _compliance_agent
    if _compliance_agent is None:
        _compliance_agent = ComplianceAgent()
    return _compliance_agent


def get_drafting_agent() -> DraftingAgent:
    global _drafting_agent
    if _drafting_agent is None:
        _drafting_agent = DraftingAgent()
    return _drafting_agent


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/onboarding/extract")
async def extract_client(file: UploadFile = File(...)):
    """Agent 1: photo/PDF of a PAN card or GST certificate -> Client Master row (JSON)."""
    suffix = Path(file.filename or "upload").suffix
    if suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".pdf"}:
        raise HTTPException(400, f"Unsupported file type: {suffix}")

    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        agent = get_onboarding_agent()
        result = agent.run(tmp_path)
        result["source_file"] = file.filename
        return result
    except Exception as exc:
        raise HTTPException(500, f"Extraction failed: {exc}") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/api/onboarding/extract-csv")
async def extract_client_csv(file: UploadFile = File(...)):
    """Same as /extract, but returns a one-row CSV matching the L1 app's
    Client Master import template, ready to feed straight into its
    'Upload / Update Client Master' feature."""
    suffix = Path(file.filename or "upload").suffix
    if suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".pdf"}:
        raise HTTPException(400, f"Unsupported file type: {suffix}")

    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        agent = get_onboarding_agent()
        result = agent.run(tmp_path)
    except Exception as exc:
        raise HTTPException(500, f"Extraction failed: {exc}") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CLIENT_MASTER_HEADERS)
    writer.writerow(to_client_master_row(result["row"]))
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=client_master_row.csv"},
    )


class ComplianceCheckRequest(BaseModel):
    text: str
    doc_type: str | None = None


@app.get("/api/compliance/document-types")
def list_document_types():
    return {"document_types": list(CHECKLISTS.keys())}


@app.post("/api/compliance/check")
def check_compliance(payload: ComplianceCheckRequest):
    """Agent 3: drafted document text -> pass/fail + missing-clause report."""
    agent = get_compliance_agent()
    try:
        return agent.run(payload.text, payload.doc_type)
    except Exception as exc:
        raise HTTPException(500, f"Compliance check failed: {exc}") from exc


@app.post("/api/compliance/check-file")
async def check_compliance_file(file: UploadFile = File(...), doc_type: str | None = Form(None)):
    """Same as /check, but takes an uploaded .txt/.html draft instead of raw JSON text."""
    data = await file.read()
    text = data.decode("utf-8", errors="replace")
    agent = get_compliance_agent()
    try:
        return agent.run(text, doc_type)
    except Exception as exc:
        raise HTTPException(500, f"Compliance check failed: {exc}") from exc


class DraftingRequest(BaseModel):
    instruction: str


@app.post("/api/drafting/generate")
def generate_draft(payload: DraftingRequest):
    """Agent 2: one plain-English instruction -> extracted params + filled draft."""
    agent = get_drafting_agent()
    try:
        return agent.run(payload.instruction)
    except Exception as exc:
        raise HTTPException(500, f"Drafting failed: {exc}") from exc


@app.post("/api/drafting/generate-and-check")
def generate_and_check(payload: DraftingRequest):
    """Agent 2 -> Agent 3 connected end to end: drafts the document, then
    immediately runs the compliance check on its own output, with no manual
    step in between."""
    drafting_agent = get_drafting_agent()
    compliance_agent = get_compliance_agent()
    try:
        draft = drafting_agent.run(payload.instruction)
        compliance = compliance_agent.run(draft["draft_text"], draft["doc_type"])
        return {"agent2": draft, "agent3": compliance}
    except Exception as exc:
        raise HTTPException(500, f"Drafting/compliance pipeline failed: {exc}") from exc
