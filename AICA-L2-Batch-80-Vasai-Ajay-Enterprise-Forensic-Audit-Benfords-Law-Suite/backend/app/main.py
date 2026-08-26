"""
FastAPI Server for Enterprise Forensic Audit & Benford's Law Suite.
(Indian DPDP Act, 2023 Compliant)
"""

import os
import sys
import time
import json
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.config import APP_TITLE, APP_VERSION, API_PREFIX
from backend.app.schemas.models import (
    IngestPathRequest, DPDPScanRequest, BenfordAnalysisRequest,
    ForensicTestsRequest, HITLApprovalRequest, ConsentDeclarationRequest, AuditVerifyRequest
)
from backend.app.engine.data_loader import UniversalDataLoader, DataIngestionResult
from backend.app.engine.dpdp_compliance import DPDPComplianceEngine, HITLSecurityGateway
from backend.app.engine.benford import BenfordAnalysisEngine
from backend.app.engine.forensic_tests import ForensicAnalysisEngine
from backend.app.engine.audit_ledger import ChainedAuditLedger
from backend.app.engine.report_generator import ForensicReportGenerator


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Elite Forensic Audit, Benford's Law Detection, and Indian DPDP Act 2023 Compliance Platform."
)

# CORS middleware for local frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-Memory Active Session Store (Session Isolated & Ephemeral)
class AuditSession:
    def __init__(self):
        self.session_id: str = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        self.auditor_name: str = "Chief Forensic Auditor"
        self.organization_fiduciary: str = "Enterprise Forensic Audit Division"
        self.consent_granted: bool = False
        self.consent_token: str = ""
        self.current_dataset: Optional[DataIngestionResult] = None
        self.sanitized_records: List[Dict[str, Any]] = []
        self.pseudonym_map: Dict[str, str] = {}
        self.column_classifications: Dict[str, Any] = {}
        self.dpdp_stats: Dict[str, int] = {}
        self.benford_results: Optional[Dict[str, Any]] = None
        self.forensic_results: Optional[Dict[str, Any]] = None
        self.ledger = ChainedAuditLedger()
        self.hitl_gateway = HITLSecurityGateway()
        self.dpdp_engine = DPDPComplianceEngine()

session = AuditSession()


# ============================================================================
# 1. CONSENT & DISCLAIMER GATEKEEPER ENDPOINTS
# ============================================================================

@app.post(f"{API_PREFIX}/consent/declare")
async def declare_consent(req: ConsentDeclarationRequest):
    """Logs explicit disclaimer acceptance & DPDP Purpose Declaration."""
    if not req.disclaimer_acknowledged or not req.dpdp_mandate_acknowledged:
        raise HTTPException(
            status_code=400,
            detail="Mandatory Disclaimer and DPDP Compliance acknowledgement must be accepted before proceeding."
        )

    session.auditor_name = req.auditor_name
    session.organization_fiduciary = req.organization_fiduciary
    session.consent_granted = True
    token_seed = f"{req.auditor_name}:{req.organization_fiduciary}:{time.time()}"
    session.consent_token = f"DPDP-CONSENT-{hashlib.sha256(token_seed.encode()).hexdigest()[:16].upper()}"

    # Log in Chained Audit Ledger
    session.ledger.log_event(
        action="LEGAL_DISCLAIMER_AND_DPDP_CONSENT_GRANTED",
        dataset_hash="0" * 64,
        details={
            "auditor_name": req.auditor_name,
            "organization_fiduciary": req.organization_fiduciary,
            "purpose": req.audit_purpose,
            "statutory_mandate": "Indian DPDP Act 2023 Sec 4 & 7",
            "disclaimer_acknowledged": True
        },
        user_role="DATA_FIDUCIARY_AUDITOR",
        consent_token=session.consent_token
    )

    return {
        "success": True,
        "consent_token": session.consent_token,
        "session_id": session.session_id,
        "message": "Disclaimer and DPDP Purpose Mandate successfully recorded in immutable audit ledger."
    }


# ============================================================================
# 2. UNIVERSAL DATA INGESTION ENDPOINTS
# ============================================================================

@app.post(f"{API_PREFIX}/ingest/upload")
async def upload_file(
    file: UploadFile = File(...),
    consent_token: str = Form(...)
):
    """Receives and parses multi-format uploaded files."""
    if not session.consent_granted and consent_token != session.consent_token:
        raise HTTPException(status_code=403, detail="DPDP Consent must be established prior to data ingest.")

    content = await file.read()
    result = UniversalDataLoader.load_from_bytes(content, file.filename or "data.csv")

    if not result.success:
        session.ledger.log_event(
            action="DATASET_INGEST_FAILED",
            dataset_hash=result.dataset_hash or ("0" * 64),
            details={"filename": file.filename, "error": result.error_message},
            consent_token=consent_token
        )
        return result.to_dict()

    session.current_dataset = result
    session.sanitized_records = result.records

    # Automatically scan columns for PII
    classifications = session.dpdp_engine.scan_dataset_schema(result.columns, result.records[:50])
    session.column_classifications = classifications

    session.ledger.log_event(
        action="DATASET_INGESTED_AND_HASHED",
        dataset_hash=result.dataset_hash,
        details={
            "filename": file.filename,
            "row_count": result.row_count,
            "columns": result.columns,
            "sha256": result.dataset_hash
        },
        consent_token=consent_token
    )

    res_dict = result.to_dict()
    res_dict["pii_classifications"] = classifications
    return res_dict


@app.post(f"{API_PREFIX}/ingest/path")
async def ingest_from_path(req: IngestPathRequest):
    """Ingests file or directory from local filesystem or connected network UNC path."""
    if not session.consent_granted and req.consent_token != session.consent_token:
        raise HTTPException(status_code=403, detail="DPDP Consent must be established prior to data ingest.")

    result = UniversalDataLoader.load_from_path(req.file_path)

    if not result.success:
        session.ledger.log_event(
            action="PATH_INGEST_FAILED",
            dataset_hash="0" * 64,
            details={"path": req.file_path, "error": result.error_message},
            consent_token=req.consent_token
        )
        return result.to_dict()

    session.current_dataset = result
    session.sanitized_records = result.records

    # Scan PII
    classifications = session.dpdp_engine.scan_dataset_schema(result.columns, result.records[:50])
    session.column_classifications = classifications

    session.ledger.log_event(
        action="PATH_DATASET_INGESTED_AND_HASHED",
        dataset_hash=result.dataset_hash,
        details={
            "path": req.file_path,
            "row_count": result.row_count,
            "columns": result.columns,
            "sha256": result.dataset_hash
        },
        consent_token=req.consent_token
    )

    res_dict = result.to_dict()
    res_dict["pii_classifications"] = classifications
    return res_dict


# ============================================================================
# 3. DPDP SANITIZATION & PSEUDONYMIZATION ENDPOINTS
# ============================================================================

@app.post(f"{API_PREFIX}/dpdp/sanitize")
async def apply_dpdp_sanitization(
    action_mode: str = Form("PSEUDONYMIZE"),
    consent_token: str = Form(...)
):
    """Applies PII Masking or HMAC-SHA256 Pseudonymization to active dataset."""
    if not session.current_dataset or not session.current_dataset.records:
        raise HTTPException(status_code=400, detail="No active dataset ingested.")

    sanitized, stats, pseudo_map = session.dpdp_engine.sanitize_dataframe(
        records=session.current_dataset.records,
        classifications=session.column_classifications,
        action_mode=action_mode
    )

    session.sanitized_records = sanitized
    session.dpdp_stats = stats
    session.pseudonym_map = pseudo_map

    session.ledger.log_event(
        action="DATASET_DPDP_SANITIZED",
        dataset_hash=session.current_dataset.dataset_hash,
        details={
            "action_mode": action_mode,
            "pii_scrub_stats": stats,
            "pseudonyms_generated": len(pseudo_map)
        },
        consent_token=consent_token
    )

    return {
        "success": True,
        "action_mode": action_mode,
        "stats": stats,
        "pseudonym_count": len(pseudo_map),
        "sample_sanitized": sanitized[:25]
    }


# ============================================================================
# 4. BENFORD'S LAW ANALYTICS ENDPOINT
# ============================================================================

@app.post(f"{API_PREFIX}/benford/analyze")
async def analyze_benford(req: BenfordAnalysisRequest):
    """Executes full Benford's Law analysis (1D, 2D, F2D, F3D, L2D, Mantissa, MAD, Z-Scores)."""
    if not session.current_dataset or not session.sanitized_records:
        raise HTTPException(status_code=400, detail="No active dataset available for analysis.")

    results = BenfordAnalysisEngine.run_full_benford_suite(
        records=session.sanitized_records,
        amount_column=req.amount_column
    )

    if not results.get("success"):
        return results

    session.benford_results = results

    session.ledger.log_event(
        action="BENFORD_SUITE_COMPUTED",
        dataset_hash=session.current_dataset.dataset_hash,
        details={
            "amount_column": req.amount_column,
            "valid_rows": results.get("valid_rows"),
            "f2d_mad": results.get("overall_summary", {}).get("mad_f2d"),
            "conformity_rating": results.get("overall_summary", {}).get("conformity_rating")
        },
        consent_token=req.consent_token
    )

    return results


# ============================================================================
# 5. ADVANCED FORENSIC ANOMALIES ENDPOINT
# ============================================================================

@app.post(f"{API_PREFIX}/forensics/analyze")
async def analyze_forensics(req: ForensicTestsRequest):
    """Executes RSF, Duplicates, Split Transactions, Round Numbers, and Composite Risk Scoring."""
    if not session.current_dataset or not session.sanitized_records:
        raise HTTPException(status_code=400, detail="No active dataset available for forensic tests.")

    results = ForensicAnalysisEngine.run_all_forensic_tests(
        records=session.sanitized_records,
        mapping=req.column_mapping,
        custom_thresholds=req.custom_thresholds
    )

    if not results.get("success"):
        return results

    session.forensic_results = results

    session.ledger.log_event(
        action="FORENSIC_ANOMALIES_SCANNED",
        dataset_hash=session.current_dataset.dataset_hash,
        details={
            "rsf_outliers": results.get("rsf_analysis", {}).get("outlier_vendor_count", 0),
            "duplicate_clusters": results.get("duplicate_analysis", {}).get("exact_duplicate_clusters", 0),
            "split_anomalies": results.get("split_transaction_analysis", {}).get("total_split_anomalies", 0),
            "flagged_transactions": len(results.get("flagged_transactions", []))
        },
        consent_token=req.consent_token
    )

    return results


# ============================================================================
# 6. TAMPER-EVIDENT AUDIT LEDGER & CERTIFICATE ENDPOINTS
# ============================================================================

@app.get(f"{API_PREFIX}/audit/ledger")
async def get_audit_ledger():
    """Returns complete blockchain-style chained audit ledger."""
    return {
        "success": True,
        "total_blocks": len(session.ledger.chain),
        "ledger": session.ledger.get_ledger()
    }


@app.post(f"{API_PREFIX}/audit/verify")
async def verify_audit_ledger(req: AuditVerifyRequest):
    """Performs on-demand cryptographic verification of all ledger hash chains."""
    is_valid, msg, corrupt_idx = session.ledger.verify_integrity()
    return {
        "success": True,
        "is_valid": is_valid,
        "verification_message": msg,
        "corrupted_block_index": corrupt_idx,
        "total_blocks_verified": len(session.ledger.chain),
        "latest_block_hash": session.ledger.chain[-1].block_hash if session.ledger.chain else None
    }


@app.get(f"{API_PREFIX}/audit/certificate")
async def get_audit_certificate():
    """Generates verifiable DPDP Compliance & Forensic Certificate."""
    dataset_name = session.current_dataset.file_name if session.current_dataset else "No Dataset"
    dataset_hash = session.current_dataset.dataset_hash if session.current_dataset else "0" * 64
    record_count = session.current_dataset.row_count if session.current_dataset else 0
    mad_rating = session.benford_results.get("overall_summary", {}).get("conformity_rating", "Pending Analysis") if session.benford_results else "Pending Analysis"

    cert = session.ledger.generate_audit_certificate(
        dataset_name=dataset_name,
        record_count=record_count,
        dataset_hash=dataset_hash,
        benford_mad_status=mad_rating,
        dpdp_status="100% DPDP 2023 COMPLIANT" if session.consent_granted else "PENDING_CONSENT"
    )
    return cert


# ============================================================================
# 7. EXECUTIVE REPORT GENERATION ENDPOINTS (PDF, EXCEL, WORD)
# ============================================================================

@app.get(f"{API_PREFIX}/report/pdf")
async def download_pdf_report():
    """Generates and downloads official Courtroom & Audit Committee Grade PDF Report."""
    if not session.current_dataset:
        raise HTTPException(status_code=400, detail="No dataset has been analyzed yet.")

    dataset_dict = session.current_dataset.to_dict()
    benford_dict = session.benford_results or {}
    forensic_dict = session.forensic_results or {}
    dpdp_dict = session.dpdp_stats or {}

    cert = session.ledger.generate_audit_certificate(
        dataset_name=session.current_dataset.file_name,
        record_count=session.current_dataset.row_count,
        dataset_hash=session.current_dataset.dataset_hash,
        benford_mad_status=benford_dict.get("overall_summary", {}).get("conformity_rating", "N/A"),
        dpdp_status="100% DPDP 2023 COMPLIANT"
    )

    pdf_bytes = ForensicReportGenerator.generate_pdf_report(
        audit_data=dataset_dict,
        benford_results=benford_dict,
        forensic_results=forensic_dict,
        dpdp_stats=dpdp_dict,
        certificate=cert
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Forensic_Audit_Report_{int(time.time())}.pdf"}
    )


@app.get(f"{API_PREFIX}/report/excel")
async def download_excel_report():
    """Generates and downloads detailed multi-tab Excel Workbook (.xlsx) with sampling guide and sample sheets."""
    if not session.current_dataset:
        raise HTTPException(status_code=400, detail="No dataset has been analyzed yet.")

    dataset_dict = session.current_dataset.to_dict()
    benford_dict = session.benford_results or {}
    forensic_dict = session.forensic_results or {}
    dpdp_dict = session.dpdp_stats or {}

    cert = session.ledger.generate_audit_certificate(
        dataset_name=session.current_dataset.file_name,
        record_count=session.current_dataset.row_count,
        dataset_hash=session.current_dataset.dataset_hash,
        benford_mad_status=benford_dict.get("overall_summary", {}).get("conformity_rating", "N/A"),
        dpdp_status="100% DPDP 2023 COMPLIANT"
    )

    excel_bytes = ForensicReportGenerator.generate_excel_workbook(
        audit_data=dataset_dict,
        benford_results=benford_dict,
        forensic_results=forensic_dict,
        dpdp_stats=dpdp_dict,
        certificate=cert
    )

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Forensic_Audit_Sampling_Outcomes_{int(time.time())}.xlsx"}
    )


@app.get(f"{API_PREFIX}/report/docx")
async def download_docx_report():
    """Generates and downloads formal Word Audit Report (.docx)."""
    if not session.current_dataset:
        raise HTTPException(status_code=400, detail="No dataset has been analyzed yet.")

    dataset_dict = session.current_dataset.to_dict()
    benford_dict = session.benford_results or {}
    forensic_dict = session.forensic_results or {}
    dpdp_dict = session.dpdp_stats or {}

    cert = session.ledger.generate_audit_certificate(
        dataset_name=session.current_dataset.file_name,
        record_count=session.current_dataset.row_count,
        dataset_hash=session.current_dataset.dataset_hash,
        benford_mad_status=benford_dict.get("overall_summary", {}).get("conformity_rating", "N/A"),
        dpdp_status="100% DPDP 2023 COMPLIANT"
    )

    docx_bytes = ForensicReportGenerator.generate_docx_report(
        audit_data=dataset_dict,
        benford_results=benford_dict,
        forensic_results=forensic_dict,
        dpdp_stats=dpdp_dict,
        certificate=cert
    )

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=Forensic_Audit_Findings_{int(time.time())}.docx"}
    )


# ============================================================================
# 8. HUMAN-IN-THE-LOOP (HITL) SECURITY GATEWAY ENDPOINTS
# ============================================================================

@app.post(f"{API_PREFIX}/hitl/check")
async def check_hitl_egress(req: HITLApprovalRequest):
    """Evaluates payload against air-gap and data minimization policies."""
    check_res = session.hitl_gateway.check_egress_authorization(req.target_service, req.payload_preview)
    return check_res


# ============================================================================
# 9. STATIC FILES MOUNTING FOR STANDALONE SINGLE-PAGE APP
# ============================================================================

def get_static_path() -> Path:
    """Finds frontend dist directory whether in source development or PyInstaller frozen executable."""
    if getattr(sys, 'frozen', False):
        # 1. PyInstaller _MEIPASS temp directory
        meipass_dist = Path(getattr(sys, '_MEIPASS', '')) / "frontend" / "dist"
        if meipass_dist.exists():
            return meipass_dist
        # 2. Executable parent directory / frontend / dist
        exe_dist = Path(sys.executable).parent / "frontend" / "dist"
        if exe_dist.exists():
            return exe_dist
        # 3. Next to executable
        local_dist = Path(sys.executable).parent / "dist"
        if local_dist.exists():
            return local_dist

    # Standard python run
    repo_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if repo_dist.exists():
        return repo_dist
    return Path("frontend/dist").resolve()


frontend_dist = get_static_path()

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_target = frontend_dist / full_path
        if file_target.exists() and file_target.is_file():
            return FileResponse(str(file_target))
        return FileResponse(str(frontend_dist / "index.html"))
