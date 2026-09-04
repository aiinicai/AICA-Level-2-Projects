"""
Pydantic Request/Response Models for Forensic Audit Suite API.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class IngestPathRequest(BaseModel):
    file_path: str = Field(..., description="Local file path or network UNC path")
    consent_token: str = Field(..., description="DPDP Consent Token")


class DPDPScanRequest(BaseModel):
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
    action_mode: str = Field("PSEUDONYMIZE", description="MASK, PSEUDONYMIZE, or NONE")


class BenfordAnalysisRequest(BaseModel):
    amount_column: str
    consent_token: str
    action_mode: str = "PSEUDONYMIZE"


class ForensicTestsRequest(BaseModel):
    column_mapping: Dict[str, str]
    custom_thresholds: Optional[List[float]] = None
    consent_token: str


class HITLApprovalRequest(BaseModel):
    target_service: str
    payload_preview: Dict[str, Any]
    auditor_authorization_pin: str
    consent_token: str


class ConsentDeclarationRequest(BaseModel):
    auditor_name: str
    organization_fiduciary: str
    audit_purpose: str
    disclaimer_acknowledged: bool
    dpdp_mandate_acknowledged: bool


class AuditVerifyRequest(BaseModel):
    session_id: Optional[str] = None
