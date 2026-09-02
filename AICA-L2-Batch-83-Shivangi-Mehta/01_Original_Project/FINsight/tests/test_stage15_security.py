"""
Stage 15 — Security, Privacy & Offline-First Hardening test suite.

Covers, per the Stage 15 instruction's section 24 list: no external
network dependency, no external AI dependency, no CDN dependency,
upload extension restrictions, filename/path-traversal protection,
absolute-path protection, uploaded files cannot overwrite application
files, engagement isolation, object-level access consistency, SQL
injection resistance, XSS escaping, error responses that expose neither
a stack trace nor a filesystem path, secrets not exposed, the database
not being publicly served, evidence paths staying local, and SEBI
remaining non-executable. Items 19-24 (existing Accounting/Audit/Tax/
Unified Review/Query/Working Paper/Stage 14 UX suites still passing)
are covered by simply running the full suite alongside this file, not
duplicated here.

Uses only synthetic, fabricated data and harmless test payloads —
never real client/financial data, and no malicious payload is ever
actually executed, per the standing instruction and the Stage 15
instruction's own "these are security tests only" note.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest

from config import TestConfig
from app import create_app

REPO_ROOT = Path(__file__).resolve().parent.parent


# --- fixtures ----------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    """CSRF disabled (TestConfig default) — matches every other HTTP
    test file in this project; see config.py's Stage 15 note for why."""
    class IsolatedConfig(TestConfig):
        DATA_INPUT_DIR = tmp_path / "data_input"

    app = create_app(IsolatedConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app.test_client()


@pytest.fixture()
def csrf_client(tmp_path):
    """A second client with CSRF protection explicitly forced ON, to
    exercise the real enforcement path end to end (config.py's
    CSRF_ENABLED default for the real application, not the test
    convenience default)."""
    class CsrfEnabledConfig(TestConfig):
        DATA_INPUT_DIR = tmp_path / "data_input"
        CSRF_ENABLED = True

    app = create_app(CsrfEnabledConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app.test_client()


def body(resp):
    return resp.get_data(as_text=True)


def _create_and_select_engagement(client, entity_name="Acme Manufacturing Ltd"):
    r = client.post("/engagement/new", data={"entity_name": entity_name, "financial_year": "2025-26"}, follow_redirects=False)
    assert r.status_code == 302
    from app.services import engagement_service
    with client.session_transaction() as sess:
        return sess["current_engagement_id"]


def _csv_bytes(rows) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


# =============================================================================
# 1-3: offline-first — no network, no external AI, no CDN (static source scan)
# =============================================================================

_SOURCE_FILES = [
    p for p in (list((REPO_ROOT / "app").rglob("*.py")) + list((REPO_ROOT / "frontend").rglob("*.py")))
    if "__pycache__" not in p.parts
]
_TEMPLATE_FILES = list((REPO_ROOT / "frontend" / "templates").rglob("*.html"))
_JS_FILES = list((REPO_ROOT / "frontend" / "static" / "js").rglob("*.js"))
_CSS_FILES = list((REPO_ROOT / "frontend" / "static" / "css").rglob("*.css"))


def test_no_outbound_network_call_in_application_source():
    banned = re.compile(r"\brequests\.(get|post|put|delete|request)\(|urllib\.request|httpx\.|aiohttp\.|socket\.socket\(|fetch\(|XMLHttpRequest")
    # frontend/static/js/api.js is a 3-line, code-free stub whose only
    # content is a comment reading "Thin fetch() wrapper — stub." — read
    # and confirmed during the Stage 15 review to contain no actual
    # call.
    #
    # app/security/lan_auth.py (Stage 16) uses `socket.socket(` for local
    # LAN-IP display only (Stage 16 Section 15): a UDP/SOCK_DGRAM socket
    # "connected" to a private, non-routable address purely so the OS
    # reports which local interface it would use — no packet leaves this
    # machine for a connectionless socket used this way, and the address
    # it nominally targets isn't on the public internet. This is the
    # opposite of an outbound network dependency, not an instance of one;
    # read and confirmed during the Stage 16 review. See
    # get_local_lan_ip()'s own docstring for the full explanation.
    #
    # Excluded by name, not silently — these are the only two exclusions
    # in this scan.
    known_safe = {
        REPO_ROOT / "frontend" / "static" / "js" / "api.js",
        REPO_ROOT / "app" / "security" / "lan_auth.py",
    }
    offenders = []
    for f in _SOURCE_FILES + _JS_FILES:
        if f in known_safe:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        if banned.search(text):
            offenders.append(str(f.relative_to(REPO_ROOT)))
    assert offenders == [], f"Outbound network call pattern found in: {offenders}"


def test_no_external_ai_provider_wired_up():
    banned = re.compile(r"\b(openai|OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|anthropic\.Client|genai\.)", re.I)
    offenders = []
    for f in _SOURCE_FILES:
        text = f.read_text(encoding="utf-8", errors="ignore")
        if banned.search(text):
            offenders.append(str(f.relative_to(REPO_ROOT)))
    assert offenders == [], f"External AI provider reference found in: {offenders}"


def test_ai_blueprint_is_a_true_disabled_stub(client):
    r = client.get("/api/ai/ping")
    assert r.status_code == 200
    data = r.get_json()
    assert data["enabled"] is False
    assert data["status"] == "stub"


def test_no_cdn_or_external_frontend_resource():
    banned = re.compile(r"(cdn\.|googleapis\.com|jsdelivr|unpkg\.com|cloudflare\.com|fontawesome)", re.I)
    offenders = []
    for f in _TEMPLATE_FILES + _JS_FILES + _CSS_FILES:
        text = f.read_text(encoding="utf-8", errors="ignore")
        if banned.search(text):
            offenders.append(str(f.relative_to(REPO_ROOT)))
    assert offenders == [], f"External frontend resource reference found in: {offenders}"


def test_no_external_href_or_src_in_templates():
    banned = re.compile(r'(href|src)=["\']https?://')
    offenders = []
    for f in _TEMPLATE_FILES:
        text = f.read_text(encoding="utf-8", errors="ignore")
        if banned.search(text):
            offenders.append(str(f.relative_to(REPO_ROOT)))
    assert offenders == [], f"External href/src found in: {offenders}"


def test_core_screens_load_and_respond_purely_locally(client):
    """Not a genuine network-isolation test (see the Stage 15 report's
    section 25 for that limitation, honestly disclosed) — this confirms
    the core workflow screens all return a normal response from this
    single local Flask process with no outbound calls made during the
    request (nothing here can reach the network at all in this sandbox,
    so any accidental outbound call would raise/hang rather than pass
    silently)."""
    for path in ("/", "/engagement/", "/data/upload/", "/data/mapping/", "/data/quality/",
                 "/review/", "/review/findings", "/queries/", "/settings/", "/reports/"):
        assert client.get(path).status_code == 200


# =============================================================================
# 4: file upload extension restrictions
# =============================================================================

def test_upload_rejects_disallowed_extension(client):
    _create_and_select_engagement(client)
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(b"MZ\x90\x00fake-exe-bytes"), "malware.exe"), "file_type": "AP"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    assert "fs-field-error" in body(r)
    from app.services import upload_service
    from app.services import engagement_service
    with client.session_transaction() as sess:
        engagement_id = sess["current_engagement_id"]
    assert upload_service.list_uploads(engagement_id) == []


def test_upload_rejects_html_disguised_as_data(client):
    _create_and_select_engagement(client)
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(b"<script>alert(1)</script>"), "payload.html"), "file_type": "AP"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    assert "fs-field-error" in body(r)


# =============================================================================
# 5-6: filename / path traversal / absolute path protection
# =============================================================================

@pytest.mark.parametrize("malicious_name", [
    "../../../test.txt",
    "..\\..\\test.txt",
    "../../app.py",
    "/etc/passwd",
    "C:\\temp\\test.txt",
    "test;rm.txt",
    "test<script>.csv",
])
def test_build_stored_path_never_escapes_the_engagement_directory(tmp_path, malicious_name):
    from app.services.upload_service import _build_stored_path

    input_dir = tmp_path / "data_input"
    stored_path = _build_stored_path(input_dir, engagement_id=1, original_filename=malicious_name)

    engagement_dir = (input_dir / "1").resolve()
    resolved = stored_path.resolve()
    assert str(resolved).startswith(str(engagement_dir))
    # secure_filename() strips path separators — no directory component
    # from the malicious name survives into the final path segment.
    assert ".." not in resolved.name
    assert "/" not in resolved.name.replace(str(engagement_dir), "")


def test_upload_with_path_traversal_filename_stays_confined_on_disk(client, tmp_path):
    engagement_id = _create_and_select_engagement(client)
    r = client.post(
        "/data/upload/",
        # A valid .csv extension so this reaches the actual path-safety
        # code (an extensionless traversal payload like "../../etc/passwd"
        # is rejected earlier, at the file-type check, before ever
        # reaching upload_service — a fine outcome, but it wouldn't
        # exercise the path-confinement logic this test targets).
        data={"file": (io.BytesIO(_csv_bytes([{"a": 1}])), "../../../../etc/passwd.csv"), "file_type": "AP"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 302  # a valid CSV, just with a hostile filename — accepted and safely stored

    from app.services import upload_service
    upload = upload_service.list_uploads(engagement_id)[-1]
    stored = Path(upload.stored_path).resolve()
    expected_root = (tmp_path / "data_input" / str(engagement_id)).resolve()
    assert str(stored).startswith(str(expected_root))
    assert stored.exists()


# =============================================================================
# 7: uploaded files cannot overwrite application files
# =============================================================================

def test_upload_cannot_overwrite_an_application_source_file(client):
    _create_and_select_engagement(client)
    before = (REPO_ROOT / "app" / "__init__.py").read_text()

    r = client.post(
        "/data/upload/",
        # ".csv" so the upload is accepted at all (see the previous
        # test's comment); secure_filename() then strips every path
        # separator regardless, so even an accepted traversal-style name
        # can never resolve back onto a real application file.
        data={"file": (io.BytesIO(_csv_bytes([{"a": 1}])), "../../../../app/__init__.py.csv"), "file_type": "AP"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 302

    after = (REPO_ROOT / "app" / "__init__.py").read_text()
    assert before == after  # untouched


# =============================================================================
# 8-9: engagement isolation / object-level access
# =============================================================================

def _seed_tax_finding(client, entity_name):
    engagement_id = _create_and_select_engagement(client, entity_name)
    from app.services import engagement_service
    engagement_service.save_entity_profile(engagement_id, {
        "entity_type": "Company", "industry": None, "is_listed": False,
        "accounting_framework": "AS", "is_gst_registered": False,
        "statutory_audit_applicable": False, "tax_audit_status": "REQUIRES_REVIEW",
        "consolidated_fs_applicable": False, "prior_year_data_available": False,
        "turnover": None, "overall_materiality": None, "performance_materiality": None,
        "clearly_trivial_threshold": None,
    })
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes([
            {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
        ])), "ap.csv"), "file_type": "AP"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 302

    from app.services import upload_service, mapping_service
    file_id = upload_service.list_uploads(engagement_id)[-1].file_id
    client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "party_name", "target_field__1": "transaction_date",
        "target_field__2": "credit_amount", "target_field__3": "debit_amount",
    })
    mapping_service.mark_file_status(file_id, "VALIDATED")

    from app import extensions
    from app.models.rules import TaxRule
    extensions.SessionLocal.add(TaxRule(
        rule_id="TAX-MSME-013", topic="MSME Delayed-Payment Review Screen",
        is_active=True, verification_status="VERIFIED",
        legislative_act="IT_ACT_1961", provision_reference="Section 43B(h), Income-tax Act, 1961",
        suggested_action="Confirm MSME registration and agreed payment terms before concluding on disallowance.",
    ))
    extensions.SessionLocal.commit()

    r = client.post("/review/", data={"modules": ["TAX"]})
    assert r.status_code == 200

    from app.services import unified_review_service as usvc
    finding = usvc.get_unified_findings(engagement_id)[0]
    return engagement_id, finding.finding_id, file_id


def test_engagement_b_cannot_open_engagement_a_working_paper(client):
    engagement_a, exception_id_a, _ = _seed_tax_finding(client, "Engagement A Pvt Ltd")
    _create_and_select_engagement(client, "Engagement B Pvt Ltd")  # now current

    r = client.get(f"/exceptions/{exception_id_a}/")
    assert r.status_code == 404


def test_engagement_b_cannot_open_engagement_a_finding_detail(client):
    engagement_a, exception_id_a, _ = _seed_tax_finding(client, "Engagement A Pvt Ltd")
    _create_and_select_engagement(client, "Engagement B Pvt Ltd")

    r = client.get(f"/review/findings/TAX/{exception_id_a}")
    assert r.status_code == 404


def test_engagement_b_cannot_open_engagement_a_uploaded_file_mapping(client):
    engagement_a, _, file_id_a = _seed_tax_finding(client, "Engagement A Pvt Ltd")
    _create_and_select_engagement(client, "Engagement B Pvt Ltd")

    r = client.get(f"/data/mapping/{file_id_a}/")
    assert r.status_code == 404


def test_engagement_b_cannot_open_engagement_a_uploaded_file_validation(client):
    engagement_a, _, file_id_a = _seed_tax_finding(client, "Engagement A Pvt Ltd")
    _create_and_select_engagement(client, "Engagement B Pvt Ltd")

    r = client.get(f"/data/quality/{file_id_a}/")
    assert r.status_code == 404


def test_engagement_b_findings_centre_never_lists_engagement_a_findings(client):
    engagement_a, exception_id_a, _ = _seed_tax_finding(client, "Engagement A Pvt Ltd")
    _create_and_select_engagement(client, "Engagement B Pvt Ltd")

    r = client.get("/review/findings")
    assert "TAX-MSME-013" not in body(r)


def test_engagement_b_query_centre_never_lists_engagement_a_queries(client):
    engagement_a, exception_id_a, _ = _seed_tax_finding(client, "Engagement A Pvt Ltd")
    _create_and_select_engagement(client, "Engagement B Pvt Ltd")

    r = client.get("/queries/")
    assert "TAX-MSME-013" not in body(r)


# =============================================================================
# 10: SQL injection resistance
# =============================================================================

_SQLI_PAYLOADS = ["'", '"', ";", "--", "OR 1=1", "'; DROP TABLE engagements; --"]


@pytest.mark.parametrize("payload", _SQLI_PAYLOADS)
def test_query_centre_search_resists_sql_injection_payloads(client, payload):
    _create_and_select_engagement(client)
    r = client.get("/queries/", query_string={"search": payload})
    assert r.status_code == 200  # never a 500 / DB error

    from app.services import engagement_service
    assert engagement_service.list_engagements() != []  # engagements table still intact


@pytest.mark.parametrize("payload", _SQLI_PAYLOADS)
def test_findings_centre_filters_resist_sql_injection_payloads(client, payload):
    _create_and_select_engagement(client)
    r = client.get("/review/findings", query_string={"rule_id": payload, "status": payload})
    assert r.status_code == 200


def test_new_engagement_form_resists_sql_injection_in_entity_name(client):
    r = client.post("/engagement/new", data={
        "entity_name": "Acme'; DROP TABLE engagements; --",
        "financial_year": "2025-26",
    }, follow_redirects=False)
    assert r.status_code == 302
    from app.services import engagement_service
    assert len(engagement_service.list_engagements()) == 1  # table intact, row created normally


# =============================================================================
# 11: XSS escaping
# =============================================================================

_XSS_PAYLOAD = '<script>alert("test")</script>'


def test_entity_name_xss_payload_is_escaped_not_executed(client):
    _create_and_select_engagement(client, entity_name=_XSS_PAYLOAD)
    r = client.get("/engagement/")
    page = body(r)
    assert "<script>alert(" not in page
    assert "&lt;script&gt;" in page


def test_working_paper_reviewer_notes_xss_payload_is_escaped(client):
    _, exception_id, _ = _seed_tax_finding(client, "Acme Manufacturing Ltd")
    r = client.post(f"/exceptions/{exception_id}/", data={
        "assigned_to": "", "reviewer_query_text": "", "management_response": "",
        "evidence_description": "", "evidence_reference": "", "reviewer_comments": "",
        "resolution": "", "reviewer_notes": _XSS_PAYLOAD,
        "status": "", "status_reason": "",
    })
    page = body(r)
    assert "<script>alert(" not in page

    r = client.get(f"/exceptions/{exception_id}/")
    page = body(r)
    assert "<script>alert(" not in page
    assert "&lt;script&gt;" in page


def test_search_field_xss_payload_is_escaped_in_query_centre(client):
    _create_and_select_engagement(client)
    r = client.get("/queries/", query_string={"search": _XSS_PAYLOAD})
    page = body(r)
    assert "<script>alert(" not in page


# =============================================================================
# 12-13: error responses expose no stack trace / filesystem path
# =============================================================================

def test_404_response_shows_no_traceback_or_filesystem_path(client):
    r = client.get("/exceptions/999999/")
    assert r.status_code == 404
    page = body(r)
    assert "Traceback" not in page
    assert "File \"" not in page
    assert str(REPO_ROOT) not in page
    assert "/home/" not in page


def test_csrf_rejection_shows_no_traceback_or_filesystem_path(csrf_client):
    r = csrf_client.post("/engagement/new", data={"entity_name": "X", "financial_year": "2025-26"})
    assert r.status_code == 400
    page = body(r)
    assert "Traceback" not in page
    assert str(REPO_ROOT) not in page
    assert "expired" in page.lower() or "unexpected source" in page.lower()


def test_unmapped_file_validation_error_has_no_stack_trace(client):
    engagement_id = _create_and_select_engagement(client)
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes([{"a": 1}])), "ap.csv"), "file_type": "AP"},
        content_type="multipart/form-data",
    )
    from app.services import upload_service
    file_id = upload_service.list_uploads(engagement_id)[-1].file_id
    r = client.get(f"/data/quality/{file_id}/")
    assert r.status_code == 200
    assert "Traceback" not in body(r)


# =============================================================================
# 14: secrets not exposed
# =============================================================================

def test_secret_key_never_appears_in_any_rendered_response(client):
    from config import DEV_SECRET_KEY_FALLBACK
    for path in ("/", "/engagement/", "/settings/", "/health"):
        page = body(client.get(path))
        assert DEV_SECRET_KEY_FALLBACK not in page


def test_health_endpoint_exposes_only_documented_feature_flags(client):
    r = client.get("/health")
    data = r.get_json()
    assert set(data.keys()) == {"status", "app", "stage", "ai_enabled", "lan_mode_enabled"}


# =============================================================================
# 15: database / config files not publicly served as static files
# =============================================================================

@pytest.mark.parametrize("path", [
    "/static/../database/finsight.db",
    "/static/../../database/finsight.db",
    "/static/../.env",
    "/static/../config.py",
    "/database/finsight.db",
    "/.env",
])
def test_sensitive_files_are_not_served_through_static_or_direct_routes(client, path):
    r = client.get(path)
    assert r.status_code in (404, 400)
    assert b"SECRET_KEY" not in r.data


def test_static_route_only_serves_frontend_static_directory(client):
    r = client.get("/static/css/design-system.css")
    assert r.status_code == 200
    r = client.get("/static/js/forms.js")
    assert r.status_code == 200


# =============================================================================
# 16: evidence paths remain local (plain text reference, never a fetchable path)
# =============================================================================

def test_evidence_reference_is_stored_as_plain_text_with_no_serving_route(client):
    _, exception_id, _ = _seed_tax_finding(client, "Acme Manufacturing Ltd")
    r = client.post(f"/exceptions/{exception_id}/", data={
        "assigned_to": "", "reviewer_query_text": "", "management_response": "Vendor responded.",
        "evidence_description": "Vendor declaration letter",
        "evidence_reference": "../../etc/passwd",
        "reviewer_comments": "", "resolution": "", "reviewer_notes": "",
        "status": "", "status_reason": "",
    })
    assert r.status_code == 200
    from app.services import query_service
    wp = query_service.get_working_paper(exception_id)
    # Stored exactly as submitted text — FinSight never opens, reads, or
    # serves a file from this value; there is no route anywhere in the
    # app that treats evidence_reference as a filesystem path.
    assert wp.response.evidence_reference == "../../etc/passwd"


def test_no_route_in_the_app_serves_a_file_by_arbitrary_path():
    import app as app_pkg
    flask_app = app_pkg.create_app(TestConfig)
    for rule in flask_app.url_map.iter_rules():
        # No route pattern in this app accepts a raw path/filename
        # segment intended to be read back and streamed to the client
        # (confirmed during the Stage 15 review: no send_file/
        # send_from_directory call exists anywhere in app/ outside
        # Flask's own built-in static handler).
        assert "filename" not in rule.arguments or rule.endpoint == "static"


# =============================================================================
# 17: sensitive information is not logged
# =============================================================================

def test_no_application_code_logs_reviewer_or_financial_content():
    banned = re.compile(r"(logger|log)\.(info|debug|warning|error|exception)\([^)]*\b(reviewer_notes|evidence_description|evidence_reference|file_bytes|management_response)\b", re.I)
    offenders = []
    for f in _SOURCE_FILES:
        text = f.read_text(encoding="utf-8", errors="ignore")
        if banned.search(text):
            offenders.append(str(f.relative_to(REPO_ROOT)))
    assert offenders == [], f"Sensitive-content logging found in: {offenders}"


# =============================================================================
# 18: SEBI remains non-executable
# =============================================================================

def test_sebi_route_is_get_only_and_produces_no_findings(client):
    _create_and_select_engagement(client)
    r = client.get("/review/sebi/")
    assert r.status_code == 200
    assert "outside current" in body(r).lower() or "not part of finsight v1" in body(r).lower() or "deferred" in body(r).lower() or "V1" in body(r)

    r = client.post("/review/sebi/")
    assert r.status_code in (404, 405)  # no POST handler exists at all


def test_review_endpoint_never_accepts_sebi_as_a_module(client):
    _create_and_select_engagement(client)
    r = client.post("/review/", data={"modules": ["SEBI"]})
    assert r.status_code == 200
    from app.services import unified_review_service as usvc
    assert "SEBI" not in usvc.MODULES


# =============================================================================
# CSRF enforcement itself
# =============================================================================

def test_csrf_protected_post_without_token_is_rejected(csrf_client):
    r = csrf_client.post("/engagement/new", data={"entity_name": "Acme", "financial_year": "2025-26"})
    assert r.status_code == 400


def test_csrf_protected_post_with_correct_token_succeeds(csrf_client):
    page = body(csrf_client.get("/engagement/new"))
    match = re.search(r'name="csrf_token" value="([0-9a-f]+)"', page)
    assert match, "csrf_field() did not render a token"
    token = match.group(1)

    r = csrf_client.post("/engagement/new", data={
        "entity_name": "Acme", "financial_year": "2025-26", "csrf_token": token,
    }, follow_redirects=False)
    assert r.status_code == 302


def test_csrf_protected_post_with_wrong_token_is_rejected(csrf_client):
    csrf_client.get("/engagement/new")  # mint a real token in this session
    r = csrf_client.post("/engagement/new", data={
        "entity_name": "Acme", "financial_year": "2025-26", "csrf_token": "0" * 64,
    })
    assert r.status_code == 400


def test_get_requests_are_never_blocked_by_csrf(csrf_client):
    for path in ("/", "/engagement/", "/data/upload/", "/settings/"):
        assert csrf_client.get(path).status_code == 200


def test_every_post_form_in_the_app_carries_the_csrf_field():
    offenders = []
    for f in _TEMPLATE_FILES:
        text = f.read_text(encoding="utf-8", errors="ignore")
        # Split on each <form method="post" — every one of them must be
        # followed (within a reasonable window) by a csrf_field() call.
        for m in re.finditer(r'<form method="post"', text):
            window = text[m.end(): m.end() + 400]
            if "csrf_field()" not in window:
                offenders.append(f"{f.relative_to(REPO_ROOT)} @ {m.start()}")
    assert offenders == [], f"POST form missing csrf_field(): {offenders}"
