"""IBC Expert localhost FastAPI application factory.

The web layer contains orchestration only. Persistent/business logic remains in services.
It is intentionally reachable only through the loopback interface and is suitable for the
PyWebView desktop shell.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from urllib.parse import quote
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import AppConfig
from app.core.errors import AuthenticationError, DocumentError, IBCExpertError, LicenceError, ValidationError
from app.core.paths import AppPaths
from app.db.connection import connect
from app.db.migrate import migrate
from app.documents.safety import sanitize_filename
from app.documents.vault import DocumentVault
from app.licensing.service import LicenseService
from app.legal.service import LegalService, VERIFICATION_STATES
from app.licensing.trial import TrialService, TrialStatus
from app.security.audit import AuditService
from app.security.auth import AuthService, AuthenticatedUser
from app.security.kdf import derive_subkey
from app.security.sessions import Session, SessionManager
from app.security.network import install_outbound_network_guard
from app.services.clients import ClientService
from app.services.dashboard import DashboardService
from app.services.forms import FormService
from app.services.backup import BackupService
from app.services.backup_schedule import BackupScheduleService
from app.workflow.engine import WorkflowService
from app.workflow.recommendations import RecommendationEngine
from app.plugins.manager import EventBus, PluginManager
from app.plugins.sample import SAMPLE_PLUGIN
from app.services.imports import LocalImportService
from app.services.review_imports import StructuredImportService, TARGET_FIELDS
from app.web.security import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    CsrfManager,
    SecurityHeadersMiddleware,
    clear_auth_cookies,
    set_auth_cookies,
)

LOGGER = logging.getLogger("ibc_expert.web")
BASE_DIR = Path(__file__).resolve().parent


def _client_service(app: FastAPI, session: Session) -> ClientService:
    audit_key = derive_subkey(session.master_key, "audit-log", "global")
    return ClientService(app.state.db, session.master_key, AuditService(app.state.db, audit_key))


def _legal_service(app: FastAPI, session: Session) -> LegalService:
    audit_key = derive_subkey(session.master_key, "audit-log", "global")
    return LegalService(app.state.db, AuditService(app.state.db, audit_key))


def _document_vault(app: FastAPI, session: Session) -> DocumentVault:
    audit_key = derive_subkey(session.master_key, "audit-log", "global")
    return DocumentVault(
        app.state.db,
        app.state.paths.vault,
        session.master_key,
        AuditService(app.state.db, audit_key),
    )



def _audit(app: FastAPI, session: Session) -> AuditService:
    return AuditService(app.state.db, derive_subkey(session.master_key, "audit-log", "global"))

def _workflow_service(app: FastAPI, session: Session) -> WorkflowService:
    return WorkflowService(app.state.db, _audit(app, session))

def _form_service(app: FastAPI, session: Session) -> FormService:
    return FormService(app.state.db, _audit(app, session))

def _recommendation_service(app: FastAPI, session: Session) -> RecommendationEngine:
    return RecommendationEngine(app.state.db, _audit(app, session))

def _backup_service(app: FastAPI, session: Session) -> BackupService:
    return BackupService(app.state.db, app.state.paths.database, app.state.paths.vault, app.state.paths.backups, session.master_key, _audit(app, session))

def _backup_schedule_service(app: FastAPI, session: Session) -> BackupScheduleService:
    return BackupScheduleService(app.state.db, _backup_service(app, session))

def _structured_import_service(app: FastAPI, session: Session) -> StructuredImportService:
    return StructuredImportService(
        app.state.db,
        _document_vault(app, session),
        app.state.events,
        _client_service(app, session),
        _legal_service(app, session),
    )

def _optional_int(value: str | int | None, label: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} is invalid.") from exc
    if parsed <= 0:
        raise ValidationError(f"{label} is invalid.")
    return parsed


async def _save_uploaded_file(app: FastAPI, upload: UploadFile, *, max_bytes: int = 100 * 1024 * 1024) -> Path:
    original = sanitize_filename(upload.filename or "document")
    upload_dir = app.state.paths.temp / f"upload-{uuid.uuid4().hex}"
    upload_dir.mkdir(parents=True, exist_ok=False)
    target = upload_dir / original
    total = 0
    try:
        with open(target, "xb") as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise DocumentError("Uploaded file exceeds the configured 100 MB limit.")
                handle.write(chunk)
        if total == 0:
            raise DocumentError("Uploaded file is empty.")
        return target
    except Exception:
        target.unlink(missing_ok=True)
        try:
            upload_dir.rmdir()
        except OSError:
            pass
        raise
    finally:
        await upload.close()


def _session_from_request(app: FastAPI, request: Request) -> Session:
    try:
        return app.state.sessions.require(request.cookies.get(SESSION_COOKIE))
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _trial_service(paths: AppPaths, cfg: AppConfig) -> TrialService:
    return TrialService(
        paths.trial_primary,
        paths.trial_secondary,
        paths.config / "installation-secret.bin",
        paths.trial_secondary.parent / "installation-secret-redundant.bin",
        rollback_tolerance_minutes=cfg.clock_rollback_tolerance_minutes,
    )


def _load_public_key(paths: AppPaths, explicit: bytes | None) -> bytes | None:
    if explicit is not None:
        if len(explicit) != 32:
            raise RuntimeError("Injected owner licence public key must contain exactly 32 bytes.")
        return explicit
    candidates = [
        paths.public_key,
        BASE_DIR.parent / "resources" / "licence_public_key.hex",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            raw = bytes.fromhex(candidate.read_text(encoding="ascii").strip())
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"Owner licence public key is invalid: {candidate}") from exc
        if len(raw) != 32:
            raise RuntimeError(f"Owner licence public key must contain 32 bytes: {candidate}")
        return raw
    return None


def _licence_status(app: FastAPI) -> TrialStatus:
    if app.state.licence is not None:
        return app.state.licence.status()
    return app.state.trial.check(licensed=False)


def _active_licence(app: FastAPI) -> dict[str, Any] | None:
    row = app.state.db.execute(
        """SELECT licence_id,licence_type,customer_name,organisation,starts_at,expires_at,
                  device_allowance,installed_at,status
           FROM licences WHERE status='ACTIVE' ORDER BY installed_at DESC LIMIT 1"""
    ).fetchone()
    return dict(row) if row else None


def _template_context(request: Request, **extra: Any) -> dict[str, Any]:
    app = request.app
    ctx: dict[str, Any] = {
        "request": request,
        "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
        "app_name": "IBC EXPERT",
        "licence_status": _licence_status(app),
        "active_licence": _active_licence(app),
        "licence_verification_configured": app.state.licence is not None,
    }
    ctx.update(extra)
    return ctx


def _form_payload(**values: str) -> dict[str, Any]:
    return {key: value for key, value in values.items()}


def _authenticated_user(app: FastAPI, session: Session) -> AuthenticatedUser:
    row = app.state.db.execute(
        "SELECT display_name,totp_secret_encrypted,is_active FROM users WHERE id=?", (session.user_id,)
    ).fetchone()
    if row is None or not int(row["is_active"]):
        raise HTTPException(status_code=401, detail="The local user account is unavailable.")
    return AuthenticatedUser(
        session.user_id,
        session.username,
        str(row["display_name"]),
        session.master_key,
        row["totp_secret_encrypted"] is not None,
    )


def _normal_session(app: FastAPI, request: Request, *, api: bool = False) -> Session:
    session = _session_from_request(app, request)
    status = _licence_status(app)
    if status.normal_use_allowed:
        try:
            _backup_schedule_service(app, session).run_if_due(default_retention=app.state.config.backup_retention)
        except Exception as exc:
            # Backup failures must be visible in Backup settings but must not lock the user out.
            LOGGER.warning("Scheduled local backup attempt failed: %s", exc)
        return session
    if api:
        raise HTTPException(status_code=403, detail="Activation is required before normal application use.")
    raise HTTPException(status_code=307, headers={"Location": "/activation"})


def create_app(
    *,
    data_root: Path | str | None = None,
    config: AppConfig | None = None,
    licence_public_key: bytes | None = None,
) -> FastAPI:
    paths = AppPaths.discover(data_root)
    paths.ensure()
    cfg = config or AppConfig.load(paths.config / "app_config.json")
    if cfg.host != "127.0.0.1":
        raise RuntimeError("IBC Expert refuses to bind to a non-loopback host.")
    if cfg.allow_outbound_integrations:
        raise RuntimeError("Internet integrations remain disabled in this build. Future secure updater support is reserved but not enabled.")
    install_outbound_network_guard()

    db = connect(paths.database)
    migrate(db)
    trial = _trial_service(paths, cfg)
    public_key = _load_public_key(paths, licence_public_key)

    app = FastAPI(
        title="IBC Expert Local API",
        version="0.1.14-dev",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.paths = paths
    app.state.config = cfg
    app.state.db = db
    app.state.auth = AuthService(db)
    app.state.sessions = SessionManager(idle_minutes=cfg.session_minutes)
    app.state.csrf = CsrfManager()
    app.state.trial = trial
    app.state.licence = LicenseService(db, trial, public_key) if public_key is not None else None
    app.state.pending_totp = {}
    app.state.document_notices = {}
    app.state.legal_notices = {}
    app.state.events = EventBus(db)
    app.state.plugins = PluginManager(db)
    app.state.plugins.register(SAMPLE_PLUGIN)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.add_middleware(SecurityHeadersMiddleware)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    app.state.templates = templates

    @app.exception_handler(IBCExpertError)
    async def app_error_handler(request: Request, exc: IBCExpertError):
        LOGGER.warning("Application error on %s: %s", request.url.path, type(exc).__name__)
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": str(exc)}, status_code=400)
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context=_template_context(request, message=str(exc)),
            status_code=400,
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        if exc.status_code == 307 and exc.headers and exc.headers.get("Location"):
            return RedirectResponse(exc.headers["Location"], status_code=303)
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)
        if exc.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context=_template_context(request, message=str(exc.detail)),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.on_event("shutdown")
    def close_database() -> None:
        app.state.sessions.clear()
        app.state.pending_totp.clear()
        app.state.document_notices.clear()
        app.state.legal_notices.clear()
        app.state.db.close()

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok", "binding": "127.0.0.1-only"}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        if not app.state.auth.has_users():
            return RedirectResponse("/setup", status_code=303)
        try:
            app.state.sessions.require(request.cookies.get(SESSION_COOKIE))
        except AuthenticationError:
            return RedirectResponse("/login", status_code=303)
        status = _licence_status(app)
        return RedirectResponse("/dashboard" if status.normal_use_allowed else "/activation", status_code=303)

    @app.get("/setup", response_class=HTMLResponse)
    def setup_page(request: Request):
        if app.state.auth.has_users():
            return RedirectResponse("/login", status_code=303)
        csrf = request.cookies.get(CSRF_COOKIE) or app.state.csrf.issue()
        response = templates.TemplateResponse(
            request=request,
            name="setup.html",
            context=_template_context(request, csrf_token=csrf),
        )
        response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="strict", path="/")
        return response

    @app.post("/setup", response_class=HTMLResponse)
    def setup_submit(
        request: Request,
        username: str = Form(...),
        display_name: str = Form(...),
        password: str = Form(...),
        password_confirm: str = Form(...),
        csrf_token: str = Form(...),
    ):
        if app.state.auth.has_users():
            return RedirectResponse("/login", status_code=303)
        app.state.csrf.validate(request, csrf_token)
        if password != password_confirm:
            raise HTTPException(status_code=400, detail="The two passwords do not match.")
        app.state.auth.create_first_user(username, display_name, password)
        return RedirectResponse("/login?created=1", status_code=303)

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, created: int = 0):
        if not app.state.auth.has_users():
            return RedirectResponse("/setup", status_code=303)
        csrf = request.cookies.get(CSRF_COOKIE) or app.state.csrf.issue()
        response = templates.TemplateResponse(
            request=request,
            name="login.html",
            context=_template_context(request, csrf_token=csrf, created=bool(created)),
        )
        response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="strict", path="/")
        return response

    @app.post("/login", response_class=HTMLResponse)
    def login_submit(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        totp_code: str = Form(""),
        csrf_token: str = Form(...),
    ):
        app.state.csrf.validate(request, csrf_token)
        try:
            user = app.state.auth.authenticate(username, password, totp_code or None)
        except AuthenticationError:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context=_template_context(
                    request,
                    error="The User ID, password or security code is incorrect.",
                    csrf_token=csrf_token,
                    created=False,
                ),
                status_code=401,
            )
        token = app.state.sessions.create(user.id, user.username, user.master_key)
        csrf = app.state.csrf.issue()
        status = _licence_status(app)
        response = RedirectResponse("/dashboard" if status.normal_use_allowed else "/activation", status_code=303)
        set_auth_cookies(response, token, csrf)
        return response

    @app.post("/logout")
    def logout(request: Request, csrf_token: str = Form(...)):
        app.state.csrf.validate(request, csrf_token)
        try:
            session = app.state.sessions.require(request.cookies.get(SESSION_COOKIE))
            app.state.pending_totp.pop(session.user_id, None)
        except AuthenticationError as exc:
            LOGGER.debug("Logout request had no active session: %s", exc)
        app.state.sessions.revoke(request.cookies.get(SESSION_COOKIE))
        response = RedirectResponse("/login", status_code=303)
        clear_auth_cookies(response)
        return response

    @app.get("/activation", response_class=HTMLResponse)
    def activation_page(request: Request, activated: int = 0):
        session = _session_from_request(app, request)
        return templates.TemplateResponse(
            request=request,
            name="activation.html",
            context=_template_context(request, session=session, activated=bool(activated)),
        )

    @app.post("/activation")
    def activation_submit(
        request: Request,
        activation_id: str = Form(...),
        activation_code: str = Form(...),
        csrf_token: str = Form(...),
    ):
        session = _session_from_request(app, request)
        app.state.csrf.validate(request, csrf_token)
        if app.state.licence is None:
            raise HTTPException(
                status_code=503,
                detail="Owner licence verification key is not installed in this build. Activation cannot be validated.",
            )
        app.state.licence.activate(activation_id.strip(), activation_code.strip())
        return RedirectResponse("/activation?activated=1", status_code=303)

    @app.get("/security", response_class=HTMLResponse)
    def security_page(request: Request, changed: str = ""):
        session = _normal_session(app, request)
        user = _authenticated_user(app, session)
        return templates.TemplateResponse(
            request=request,
            name="security.html",
            context=_template_context(request, session=session, user=user, changed=changed),
        )

    @app.get("/security/totp/setup", response_class=HTMLResponse)
    def totp_setup_page(request: Request):
        session = _normal_session(app, request)
        user = _authenticated_user(app, session)
        if app.state.auth.totp_enabled(user.id):
            return RedirectResponse("/security", status_code=303)
        secret, uri = app.state.auth.begin_totp_setup(user)
        app.state.pending_totp[user.id] = secret
        return templates.TemplateResponse(
            request=request,
            name="totp_setup.html",
            context=_template_context(request, session=session, user=user, secret=secret, provisioning_uri=uri),
        )

    @app.post("/security/totp/enable")
    def totp_enable(request: Request, verification_code: str = Form(...), csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        user = _authenticated_user(app, session)
        secret = app.state.pending_totp.get(user.id)
        if not secret:
            raise HTTPException(status_code=400, detail="TOTP setup session expired. Start setup again.")
        app.state.auth.enable_totp(user, secret, verification_code)
        app.state.pending_totp.pop(user.id, None)
        return RedirectResponse("/security?changed=enabled", status_code=303)

    @app.post("/security/totp/disable")
    def totp_disable(request: Request, verification_code: str = Form(...), csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        user = _authenticated_user(app, session)
        app.state.auth.disable_totp(user, verification_code)
        app.state.pending_totp.pop(user.id, None)
        return RedirectResponse("/security?changed=disabled", status_code=303)

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard(request: Request):
        session = _normal_session(app, request)
        metrics = DashboardService(app.state.db).metrics()
        progress = DashboardService(app.state.db).process_progress()
        clients = _client_service(app, session).search(status="ACTIVE", limit=8)
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context=_template_context(request, session=session, metrics=metrics, progress=progress, clients=clients),
        )

    @app.get("/clients", response_class=HTMLResponse)
    def clients_page(request: Request, q: str = "", status: str = "ACTIVE"):
        session = _normal_session(app, request)
        clients = _client_service(app, session).search(q, status or None, limit=250)
        return templates.TemplateResponse(
            request=request,
            name="clients.html",
            context=_template_context(request, session=session, clients=clients, q=q, status=status),
        )

    @app.get("/clients/new", response_class=HTMLResponse)
    def client_new_page(request: Request):
        session = _normal_session(app, request)
        return templates.TemplateResponse(
            request=request,
            name="client_form.html",
            context=_template_context(request, session=session, client=None, mode="create"),
        )

    @app.post("/clients/new")
    def client_create(
        request: Request,
        name: str = Form(...), corporate_debtor: str = Form(""), cin: str = Form(""), pan: str = Form(""),
        gst: str = Form(""), registered_office: str = Form(""), industry: str = Form(""),
        primary_email: str = Form(""), primary_phone: str = Form(""), notes: str = Form(""),
        custom_fields: str = Form("{}"), csrf_token: str = Form(...),
    ):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        client_id = _client_service(app, session).create(
            _form_payload(name=name, corporate_debtor=corporate_debtor, cin=cin, pan=pan, gst=gst,
                          registered_office=registered_office, industry=industry, primary_email=primary_email,
                          primary_phone=primary_phone, notes=notes, custom_fields=custom_fields),
            user_id=session.user_id,
        )
        return RedirectResponse(f"/clients/{client_id}", status_code=303)

    @app.get("/clients/{client_id}", response_class=HTMLResponse)
    def client_detail(request: Request, client_id: int):
        session = _normal_session(app, request)
        service = _client_service(app, session)
        client = service.get(client_id, include_deleted=True)
        history = service.history(client_id)[:50]
        matters = [dict(row) for row in app.state.db.execute(
            "SELECT id,title,matter_type,case_number,status,updated_at FROM matters WHERE client_id=? ORDER BY updated_at DESC",
            (client_id,),
        ).fetchall()]
        documents = _document_vault(app, session).list_documents(client_id=client_id, limit=25)
        return templates.TemplateResponse(
            request=request,
            name="client_detail.html",
            context=_template_context(
                request, session=session, client=client, history=history, matters=matters, documents=documents
            ),
        )

    @app.get("/clients/{client_id}/edit", response_class=HTMLResponse)
    def client_edit_page(request: Request, client_id: int):
        session = _normal_session(app, request)
        client = _client_service(app, session).get(client_id, include_deleted=True)
        return templates.TemplateResponse(
            request=request,
            name="client_form.html",
            context=_template_context(request, session=session, client=client, mode="edit"),
        )

    @app.post("/clients/{client_id}/edit")
    def client_edit(
        request: Request, client_id: int,
        name: str = Form(...), corporate_debtor: str = Form(""), cin: str = Form(""), pan: str = Form(""),
        gst: str = Form(""), registered_office: str = Form(""), industry: str = Form(""),
        primary_email: str = Form(""), primary_phone: str = Form(""), notes: str = Form(""),
        custom_fields: str = Form("{}"), row_version: int = Form(...), csrf_token: str = Form(...),
    ):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        _client_service(app, session).update(
            client_id,
            _form_payload(name=name, corporate_debtor=corporate_debtor, cin=cin, pan=pan, gst=gst,
                          registered_office=registered_office, industry=industry, primary_email=primary_email,
                          primary_phone=primary_phone, notes=notes, custom_fields=custom_fields),
            expected_version=row_version,
            user_id=session.user_id,
        )
        return RedirectResponse(f"/clients/{client_id}", status_code=303)

    @app.post("/clients/{client_id}/status/{action}")
    def client_status(request: Request, client_id: int, action: str, csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        service = _client_service(app, session)
        actions = {"archive": service.archive, "restore": service.restore, "delete": service.soft_delete}
        if action not in actions:
            raise HTTPException(status_code=404, detail="Unknown client action.")
        actions[action](client_id, user_id=session.user_id)
        return RedirectResponse(f"/clients/{client_id}", status_code=303)

    @app.post("/clients/{client_id}/permanent-delete")
    def client_permanent_delete(
        request: Request, client_id: int, confirmation_name: str = Form(...), csrf_token: str = Form(...)
    ):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        _client_service(app, session).permanent_delete(client_id, confirmation_name, user_id=session.user_id)
        return RedirectResponse("/clients?status=DELETED", status_code=303)

    def _document_page_data(session: Session, *, q: str = "", client_id: int | None = None, matter_id: int | None = None, category: str = "") -> dict[str, Any]:
        vault = _document_vault(app, session)
        clients = [dict(row) for row in app.state.db.execute(
            "SELECT id,name,status FROM clients WHERE status!='DELETED' ORDER BY name COLLATE NOCASE"
        ).fetchall()]
        matters = [dict(row) for row in app.state.db.execute(
            "SELECT id,client_id,title,status FROM matters ORDER BY title COLLATE NOCASE"
        ).fetchall()]
        categories = [str(row[0]) for row in app.state.db.execute(
            "SELECT DISTINCT category FROM documents WHERE category IS NOT NULL AND TRIM(category)!='' ORDER BY category COLLATE NOCASE"
        ).fetchall()]
        return {
            "documents": vault.list_documents(query=q, client_id=client_id, matter_id=matter_id, category=category, limit=250),
            "clients": clients,
            "matters": matters,
            "categories": categories,
        }

    @app.get("/documents", response_class=HTMLResponse)
    def documents_page(
        request: Request,
        q: str = "",
        client_id: str = "",
        matter_id: str = "",
        category: str = "",
        notice: str = "",
    ):
        session = _normal_session(app, request)
        parsed_client = _optional_int(client_id, "Client")
        parsed_matter = _optional_int(matter_id, "Matter")
        page = _document_page_data(session, q=q, client_id=parsed_client, matter_id=parsed_matter, category=category)
        notice_data = app.state.document_notices.pop(notice, None) if notice else None
        return templates.TemplateResponse(
            request=request,
            name="documents.html",
            context=_template_context(
                request,
                session=session,
                q=q,
                selected_client_id=parsed_client,
                selected_matter_id=parsed_matter,
                selected_category=category,
                notice=notice_data,
                **page,
            ),
        )

    @app.post("/documents/upload")
    async def document_upload(
        request: Request,
        file: UploadFile = File(...),
        client_id: str = Form(""),
        matter_id: str = Form(""),
        category: str = Form(""),
        tags: str = Form(""),
        force_ocr: str = Form(""),
        csrf_token: str = Form(...),
    ):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        parsed_client = _optional_int(client_id, "Client")
        parsed_matter = _optional_int(matter_id, "Matter")
        original_name = sanitize_filename(file.filename or "document")
        temporary = await _save_uploaded_file(app, file)
        try:
            vault = _document_vault(app, session)
            duplicate_id = vault.find_duplicate(temporary, client_id=parsed_client, matter_id=parsed_matter)
            document_id = vault.ingest(
                temporary,
                client_id=parsed_client,
                matter_id=parsed_matter,
                category=category,
                tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
                source_label="Local upload",
                force_ocr=force_ocr == "1",
                user_id=session.user_id,
            )
        finally:
            temporary.unlink(missing_ok=True)
            try:
                temporary.parent.rmdir()
            except OSError:
                pass
        token = uuid.uuid4().hex
        app.state.document_notices[token] = {
            "kind": "duplicate" if duplicate_id is not None else "uploaded",
            "document_id": document_id,
            "filename": original_name,
        }
        return RedirectResponse(f"/documents?notice={token}", status_code=303)

    @app.post("/documents/import-zip")
    async def document_zip_import(
        request: Request,
        file: UploadFile = File(...),
        client_id: str = Form(""),
        matter_id: str = Form(""),
        category: str = Form(""),
        tags: str = Form(""),
        csrf_token: str = Form(...),
    ):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        parsed_client = _optional_int(client_id, "Client")
        parsed_matter = _optional_int(matter_id, "Matter")
        temporary = await _save_uploaded_file(app, file)
        try:
            result = _document_vault(app, session).import_zip(
                temporary,
                client_id=parsed_client,
                matter_id=parsed_matter,
                category=category,
                tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
                user_id=session.user_id,
            )
        finally:
            temporary.unlink(missing_ok=True)
            try:
                temporary.parent.rmdir()
            except OSError:
                pass
        token = uuid.uuid4().hex
        app.state.document_notices[token] = {"kind": "zip", **result}
        return RedirectResponse(f"/documents?notice={token}", status_code=303)

    @app.get("/documents/{document_id}", response_class=HTMLResponse)
    def document_detail(request: Request, document_id: int, changed: str = ""):
        session = _normal_session(app, request)
        document = _document_vault(app, session).metadata(document_id)
        return templates.TemplateResponse(
            request=request,
            name="document_detail.html",
            context=_template_context(request, session=session, document=document, changed=changed),
        )

    @app.post("/documents/{document_id}/metadata")
    def document_metadata_update(
        request: Request,
        document_id: int,
        category: str = Form(""),
        tags: str = Form(""),
        review_status: str = Form(...),
        csrf_token: str = Form(...),
    ):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        _document_vault(app, session).update_metadata(
            document_id,
            category=category,
            tags=tags,
            review_status=review_status,
            user_id=session.user_id,
        )
        return RedirectResponse(f"/documents/{document_id}?changed=metadata", status_code=303)

    @app.post("/documents/{document_id}/ocr")
    def document_ocr(request: Request, document_id: int, csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        _document_vault(app, session).reprocess_ocr(document_id, user_id=session.user_id)
        return RedirectResponse(f"/documents/{document_id}?changed=ocr", status_code=303)

    @app.get("/documents/{document_id}/download")
    def document_download(request: Request, document_id: int):
        session = _normal_session(app, request)
        vault = _document_vault(app, session)
        document = vault.metadata(document_id, text_limit=0)
        clear = vault.read(document_id)
        vault.audit.append(
            "DOCUMENT_EXPORTED",
            f"Exported document '{document['safe_filename']}'.",
            entity_type="document",
            entity_id=document_id,
            user_id=session.user_id,
            details={"destination": "authenticated-local-download"},
        )
        filename = quote(sanitize_filename(document["safe_filename"]))
        return Response(
            content=clear,
            media_type=document["media_type"],
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
        )


    @app.get("/legal", response_class=HTMLResponse)
    def legal_page(request: Request, q: str = "", exact: str = "", entity_type: str = "", verification_status: str = "", statute_id: str = "", notice: str = ""):
        session = _normal_session(app, request)
        service = _legal_service(app, session)
        parsed_statute = _optional_int(statute_id, "Statute")
        results = service.search(q, exact_phrase=exact == "1", entity_type=entity_type or None,
                                 verification_status=verification_status or None, statute_id=parsed_statute) if q.strip() else []
        statutes = service.list_statutes(limit=500)
        judgments = service.list_judgments(limit=100)
        notice_data = app.state.legal_notices.pop(notice, None) if notice else None
        return templates.TemplateResponse(request=request, name="legal.html", context=_template_context(
            request, session=session, q=q, exact=exact == "1", entity_type=entity_type,
            verification_status=verification_status, selected_statute_id=parsed_statute,
            statutes=statutes, judgments=judgments, results=results, verification_states=sorted(VERIFICATION_STATES), notice=notice_data))

    @app.post("/legal/statutes")
    def legal_add_statute(request: Request, title: str = Form(...), short_title: str = Form(""), statute_type: str = Form(...),
                          jurisdiction: str = Form("India"), identifier: str = Form(""), verification_status: str = Form("REVIEW_REQUIRED"),
                          source_document_id: str = Form(""), csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        sid = _legal_service(app, session).add_statute({"title": title, "short_title": short_title, "statute_type": statute_type,
            "jurisdiction": jurisdiction, "identifier": identifier, "verification_status": verification_status,
            "source_document_id": _optional_int(source_document_id, "Source document")}, user_id=session.user_id)
        return RedirectResponse(f"/legal/statutes/{sid}", status_code=303)

    @app.get("/legal/statutes/{statute_id}", response_class=HTMLResponse)
    def legal_statute_detail(request: Request, statute_id: int):
        session = _normal_session(app, request); service = _legal_service(app, session)
        return templates.TemplateResponse(request=request, name="legal_statute.html", context=_template_context(
            request, session=session, statute=service.statute_detail(statute_id), verification_states=sorted(VERIFICATION_STATES)))

    @app.post("/legal/statutes/{statute_id}/provisions")
    def legal_add_provision(request: Request, statute_id: int, provision_type: str = Form(...), number_label: str = Form(""),
                            heading: str = Form(""), text_content: str = Form(...), effective_from: str = Form(""),
                            source_document_id: str = Form(""), source_page: str = Form(""), amendment_identifier: str = Form(""),
                            verification_status: str = Form("REVIEW_REQUIRED"), csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        pid = _legal_service(app, session).add_provision(statute_id, {"provision_type": provision_type, "number_label": number_label,
            "heading": heading, "text_content": text_content, "effective_from": effective_from,
            "source_document_id": _optional_int(source_document_id, "Source document"), "source_page": _optional_int(source_page, "Source page"),
            "amendment_identifier": amendment_identifier, "verification_status": verification_status}, user_id=session.user_id)
        return RedirectResponse(f"/legal/provisions/{pid}", status_code=303)

    @app.get("/legal/provisions/{provision_id}", response_class=HTMLResponse)
    def legal_provision_detail(request: Request, provision_id: int, on_date: str = ""):
        session = _normal_session(app, request); service = _legal_service(app, session); provision = service.provision_detail(provision_id)
        point = service.provision_at(provision["provision_uuid"], on_date) if on_date else None
        return templates.TemplateResponse(request=request, name="legal_provision.html", context=_template_context(
            request, session=session, provision=provision, point_in_time=point, on_date=on_date, verification_states=sorted(VERIFICATION_STATES)))

    @app.post("/legal/provisions/{provision_id}/version")
    def legal_version_provision(request: Request, provision_id: int, effective_from: str = Form(...), new_text: str = Form(...),
                                amendment_identifier: str = Form(...), source_document_id: str = Form(""), source_page: str = Form(""),
                                verification_status: str = Form("REVIEW_REQUIRED"), csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        new_id = _legal_service(app, session).version_provision(provision_id, effective_from, new_text, amendment_identifier,
            _optional_int(source_document_id, "Source document"), _optional_int(source_page, "Source page"), verification_status, session.user_id)
        return RedirectResponse(f"/legal/provisions/{new_id}", status_code=303)

    @app.post("/legal/judgments")
    def legal_add_judgment(request: Request, title: str = Form(...), court: str = Form(...), judgment_date: str = Form(""),
                           case_number: str = Form(""), neutral_citation: str = Form(""), reported_citation: str = Form(""),
                           parties: str = Form(""), text_content: str = Form(...), holding_summary: str = Form(""),
                           source_document_id: str = Form(""), source_page: str = Form(""), verification_status: str = Form("REVIEW_REQUIRED"), csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        jid = _legal_service(app, session).add_judgment({"title": title, "court": court, "judgment_date": judgment_date, "case_number": case_number,
            "neutral_citation": neutral_citation, "reported_citation": reported_citation, "parties": parties, "text_content": text_content,
            "holding_summary": holding_summary, "source_document_id": _optional_int(source_document_id, "Source document"),
            "source_page": _optional_int(source_page, "Source page"), "verification_status": verification_status}, user_id=session.user_id)
        return RedirectResponse(f"/legal/judgments/{jid}", status_code=303)

    @app.get("/legal/judgments/{judgment_id}", response_class=HTMLResponse)
    def legal_judgment_detail(request: Request, judgment_id: int):
        session = _normal_session(app, request)
        return templates.TemplateResponse(request=request, name="legal_judgment.html", context=_template_context(
            request, session=session, judgment=_legal_service(app, session).judgment_detail(judgment_id), verification_states=sorted(VERIFICATION_STATES)))

    @app.post("/legal/{entity_type}/{entity_id}/verification")
    def legal_verification(request: Request, entity_type: str, entity_id: int, verification_status: str = Form(...), csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        _legal_service(app, session).set_verification_status(entity_type, entity_id, verification_status, user_id=session.user_id)
        target = {"statute": f"/legal/statutes/{entity_id}", "provision": f"/legal/provisions/{entity_id}", "judgment": f"/legal/judgments/{entity_id}"}.get(entity_type, "/legal")
        return RedirectResponse(target, status_code=303)

    @app.post("/legal/import-json")
    async def legal_import_json(request: Request, file: UploadFile = File(...), csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        temporary = await _save_uploaded_file(app, file, max_bytes=25 * 1024 * 1024)
        try: counts = _legal_service(app, session).import_json_package(temporary, user_id=session.user_id)
        finally:
            temporary.unlink(missing_ok=True)
            try: temporary.parent.rmdir()
            except OSError: pass
        token = uuid.uuid4().hex; app.state.legal_notices[token] = {"kind": "import", **counts}
        return RedirectResponse(f"/legal?notice={token}", status_code=303)

    @app.get("/api/v1/legal/search")
    def api_legal_search(request: Request, q: str, exact: bool = False, entity_type: str = "", verification_status: str = "", statute_id: int | None = None):
        session = _normal_session(app, request, api=True)
        return {"results": _legal_service(app, session).search(q, exact_phrase=exact, entity_type=entity_type or None,
            verification_status=verification_status or None, statute_id=statute_id)}

    @app.get("/workflow", response_class=HTMLResponse)
    def workflow_page(request: Request):
        session = _normal_session(app, request)
        definitions = [dict(r) for r in app.state.db.execute("SELECT * FROM process_definitions WHERE active=1 ORDER BY process_type,name,version DESC").fetchall()]
        matters = [dict(r) for r in app.state.db.execute("SELECT m.id,m.title,c.name AS client_name FROM matters m JOIN clients c ON c.id=m.client_id ORDER BY m.updated_at DESC").fetchall()]
        instances = [dict(r) for r in app.state.db.execute("SELECT pi.id,pi.status,pd.name AS definition_name,pd.process_type,m.title AS matter_title,c.name AS client_name FROM process_instances pi JOIN process_definitions pd ON pd.id=pi.process_definition_id JOIN matters m ON m.id=pi.matter_id JOIN clients c ON c.id=m.client_id ORDER BY pi.updated_at DESC").fetchall()]
        return templates.TemplateResponse(request=request,name="workflow.html",context=_template_context(request,session=session,definitions=definitions,matters=matters,instances=instances))

    @app.post("/workflow/definitions")
    def workflow_create_definition(request: Request, name: str=Form(...), process_type: str=Form(...), version: int=Form(...), stages_json: str=Form(...), csrf_token: str=Form(...)):
        session=_normal_session(app,request); app.state.csrf.validate(request,csrf_token)
        try: stages=json.loads(stages_json)
        except json.JSONDecodeError as exc: raise ValidationError("Stages must be valid JSON.") from exc
        if not isinstance(stages,list): raise ValidationError("Stages JSON must be a list.")
        _workflow_service(app,session).create_definition(name,process_type,version,stages,user_id=session.user_id)
        return RedirectResponse("/workflow",status_code=303)

    @app.post("/workflow/start")
    def workflow_start(request: Request, matter_id: int=Form(...), definition_id: int=Form(...), csrf_token: str=Form(...)):
        session=_normal_session(app,request); app.state.csrf.validate(request,csrf_token)
        iid=_workflow_service(app,session).instantiate(matter_id,definition_id,user_id=session.user_id)
        return RedirectResponse(f"/workflow/{iid}",status_code=303)

    @app.get("/workflow/{instance_id}", response_class=HTMLResponse)
    def workflow_detail(request: Request, instance_id: int):
        session=_normal_session(app,request); service=_workflow_service(app,session)
        head=app.state.db.execute("SELECT pi.*,pd.name AS definition_name,m.title AS matter_title,c.name AS client_name FROM process_instances pi JOIN process_definitions pd ON pd.id=pi.process_definition_id JOIN matters m ON m.id=pi.matter_id JOIN clients c ON c.id=m.client_id WHERE pi.id=?",(instance_id,)).fetchone()
        if head is None: raise ValidationError("Workflow instance was not found.")
        stages=service.stages(instance_id)
        for stage in stages:
            stage["checklist"]=[dict(r) for r in app.state.db.execute("SELECT * FROM checklists WHERE process_stage_id=? ORDER BY sequence_number",(stage["id"],)).fetchall()]
        return templates.TemplateResponse(request=request,name="workflow_detail.html",context=_template_context(request,session=session,instance=dict(head),stages=stages))

    @app.post("/workflow/{instance_id}/recalculate")
    def workflow_recalculate(request: Request, instance_id: int, csrf_token: str=Form(...)):
        session=_normal_session(app,request); app.state.csrf.validate(request,csrf_token)
        _workflow_service(app,session).recalculate(instance_id,"Manual recalculation",session.user_id)
        return RedirectResponse(f"/workflow/{instance_id}",status_code=303)

    @app.post("/workflow/stages/{stage_id}/status")
    def workflow_stage_status(request: Request, stage_id: int, instance_id: int=Form(...), status: str=Form(...), notes: str=Form(""), csrf_token: str=Form(...)):
        session=_normal_session(app,request); app.state.csrf.validate(request,csrf_token)
        _workflow_service(app,session).set_stage_status(stage_id,status,notes,session.user_id)
        return RedirectResponse(f"/workflow/{instance_id}",status_code=303)

    @app.get("/recommendations", response_class=HTMLResponse)
    def recommendations_page(request: Request):
        session=_normal_session(app,request)
        matters=[dict(r) for r in app.state.db.execute("SELECT m.id,m.title,c.name AS client_name FROM matters m JOIN clients c ON c.id=m.client_id ORDER BY m.updated_at DESC").fetchall()]
        recs=[dict(r) for r in app.state.db.execute("SELECT r.*,m.title AS matter_title,c.name AS client_name,ci.citation_text FROM recommendations r JOIN matters m ON m.id=r.matter_id JOIN clients c ON c.id=m.client_id JOIN citations ci ON ci.id=r.citation_id WHERE r.dismissed=0 ORDER BY r.generated_at DESC").fetchall()]
        return templates.TemplateResponse(request=request,name="recommendations.html",context=_template_context(request,session=session,matters=matters,recommendations=recs))

    @app.post("/recommendations/generate")
    def recommendations_generate(request: Request,matter_id: int=Form(...),csrf_token: str=Form(...)):
        session=_normal_session(app,request); app.state.csrf.validate(request,csrf_token)
        _recommendation_service(app,session).generate_for_matter(matter_id)
        return RedirectResponse("/recommendations",status_code=303)

    @app.get("/forms", response_class=HTMLResponse)
    def forms_page(request: Request):
        session=_normal_session(app,request)
        forms=[dict(r) for r in app.state.db.execute("SELECT * FROM forms WHERE active=1 ORDER BY updated_at DESC").fetchall()]
        matters=[dict(r) for r in app.state.db.execute("SELECT m.id,m.title,c.name AS client_name FROM matters m JOIN clients c ON c.id=m.client_id ORDER BY m.updated_at DESC").fetchall()]
        versions=[dict(r) for r in app.state.db.execute("SELECT fv.id,fv.version_number,fv.created_at,f.name AS form_name,m.title AS matter_title FROM form_versions fv JOIN forms f ON f.id=fv.form_id LEFT JOIN matters m ON m.id=fv.matter_id ORDER BY fv.created_at DESC LIMIT 100").fetchall()]
        return templates.TemplateResponse(request=request,name="forms.html",context=_template_context(request,session=session,forms=forms,matters=matters,versions=versions))

    @app.post("/forms/templates")
    def form_add_template(request: Request,name:str=Form(...),form_code:str=Form(""),classification:str=Form("PRACTITIONER_TEMPLATE"),template_content:str=Form(...),csrf_token:str=Form(...)):
        session=_normal_session(app,request); app.state.csrf.validate(request,csrf_token)
        _form_service(app,session).add_template(name=name,template=template_content,classification=classification,form_code=form_code or None)
        return RedirectResponse("/forms",status_code=303)

    @app.post("/forms/generate")
    def form_generate(request: Request,form_id:int=Form(...),matter_id:int=Form(...),csrf_token:str=Form(...)):
        session=_normal_session(app,request); app.state.csrf.validate(request,csrf_token)
        vid=_form_service(app,session).generate(form_id,matter_id)
        return RedirectResponse(f"/forms/{vid}",status_code=303)

    @app.get("/forms/{version_id}", response_class=HTMLResponse)
    def form_version_detail(request: Request,version_id:int):
        session=_normal_session(app,request); content=_form_service(app,session).content(version_id)
        row=app.state.db.execute("SELECT fv.*,f.name AS form_name,m.title AS matter_title FROM form_versions fv JOIN forms f ON f.id=fv.form_id LEFT JOIN matters m ON m.id=fv.matter_id WHERE fv.id=?",(version_id,)).fetchone()
        if row is None: raise ValidationError("Generated form version was not found.")
        return templates.TemplateResponse(request=request,name="form_detail.html",context=_template_context(request,session=session,version=dict(row),content=content))

    @app.post("/forms/{version_id}/export")
    def form_export(request: Request,version_id:int,output_type:str=Form(...),csrf_token:str=Form(...)):
        session=_normal_session(app,request); app.state.csrf.validate(request,csrf_token)
        target=_form_service(app,session).export(version_id,app.state.paths.root/"exports",output_type)
        return FileResponse(str(target),filename=target.name,media_type="application/octet-stream")


    @app.get("/imports", response_class=HTMLResponse)
    def imports_page(request: Request):
        session = _normal_session(app, request)
        service = LocalImportService(app.state.db, _document_vault(app, session), app.state.events)
        structured = _structured_import_service(app, session)
        clients = [dict(r) for r in app.state.db.execute("SELECT id,name FROM clients WHERE status!='DELETED' ORDER BY name COLLATE NOCASE").fetchall()]
        matters = [dict(r) for r in app.state.db.execute("SELECT id,client_id,title FROM matters ORDER BY title COLLATE NOCASE").fetchall()]
        return templates.TemplateResponse(request=request, name="imports.html", context=_template_context(
            request, session=session, imports=service.history(), clients=clients, matters=matters,
            target_fields=TARGET_FIELDS, profiles=structured.profiles()
        ))

    @app.post("/imports/local")
    async def import_local_file(request: Request, file: UploadFile = File(...), client_id: str = Form(""), matter_id: str = Form(""),
                                category: str = Form(""), tags: str = Form(""), csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        temporary = await _save_uploaded_file(app, file)
        try:
            service = LocalImportService(app.state.db, _document_vault(app, session), app.state.events)
            result = service.import_file(temporary, client_id=_optional_int(client_id, "Client"), matter_id=_optional_int(matter_id, "Matter"),
                                         category=category or None, tags=[t.strip() for t in tags.split(",") if t.strip()], user_id=session.user_id)
            notice = "Imported successfully." if not result.get("duplicate") else "File already existed; existing document retained."
        finally:
            temporary.unlink(missing_ok=True)
            try: temporary.parent.rmdir()
            except OSError: pass
        return RedirectResponse("/imports?notice=" + quote(notice), status_code=303)

    @app.post("/imports/structured")
    async def import_structured_file(request: Request, file: UploadFile = File(...), target_type: str = Form(...),
                                     mapping_json: str = Form(""), profile_name: str = Form(""), csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        temporary = await _save_uploaded_file(app, file, max_bytes=50 * 1024 * 1024)
        try:
            mapping = None
            if mapping_json.strip():
                try:
                    mapping = json.loads(mapping_json)
                except json.JSONDecodeError as exc:
                    raise ValidationError("Column mapping must be valid JSON.") from exc
            result = _structured_import_service(app, session).stage_structured(
                temporary, target_type=target_type, mapping=mapping, profile_name=profile_name.strip() or None, user_id=session.user_id
            )
            notice = f"Staged {result['review_items']} row(s) for manual review. Nothing was created automatically."
        finally:
            temporary.unlink(missing_ok=True)
            try: temporary.parent.rmdir()
            except OSError: pass
        return RedirectResponse("/review-queue?notice=" + quote(notice), status_code=303)

    @app.post("/imports/legal-source")
    async def import_legal_source_review(request: Request, file: UploadFile = File(...), client_id: str = Form(""), matter_id: str = Form(""),
                                         tags: str = Form(""), csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        temporary = await _save_uploaded_file(app, file)
        try:
            result = _structured_import_service(app, session).stage_legal_source_document(
                temporary, client_id=_optional_int(client_id, "Client"), matter_id=_optional_int(matter_id, "Matter"),
                tags=[t.strip() for t in tags.split(",") if t.strip()], user_id=session.user_id
            )
            notice = "Legal source stored locally and sent to manual review. No legal data was auto-verified."
        finally:
            temporary.unlink(missing_ok=True)
            try: temporary.parent.rmdir()
            except OSError: pass
        return RedirectResponse("/review-queue?notice=" + quote(notice), status_code=303)

    @app.get("/review-queue", response_class=HTMLResponse)
    def review_queue_page(request: Request, status: str = "PENDING"):
        session = _normal_session(app, request)
        service = _structured_import_service(app, session)
        return templates.TemplateResponse(request=request, name="review_queue.html", context=_template_context(
            request, session=session, items=service.list_review(status=status), status=status
        ))

    @app.get("/review-queue/{review_id}", response_class=HTMLResponse)
    def review_queue_detail(request: Request, review_id: int):
        session = _normal_session(app, request)
        item = _structured_import_service(app, session).get_review(review_id)
        return templates.TemplateResponse(request=request, name="review_detail.html", context=_template_context(
            request, session=session, item=item, payload_pretty=json.dumps(item["payload"], ensure_ascii=False, indent=2, sort_keys=True)
        ))

    @app.post("/review-queue/{review_id}/save")
    def review_queue_save(request: Request, review_id: int, payload_json: str = Form(...), csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError as exc:
            raise ValidationError("Review payload must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValidationError("Review payload must be a JSON object.")
        _structured_import_service(app, session).update_payload(review_id, payload, user_id=session.user_id)
        return RedirectResponse(f"/review-queue/{review_id}?notice=" + quote("Review values saved."), status_code=303)

    @app.post("/review-queue/{review_id}/resolve")
    def review_queue_resolve(request: Request, review_id: int, note: str = Form(""), csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        result = _structured_import_service(app, session).resolve(review_id, user_id=session.user_id, note=note)
        notice = f"Review resolved; created/confirmed {result['created_entity_type']} record {result['created_entity_id']}."
        return RedirectResponse("/review-queue?notice=" + quote(notice), status_code=303)

    @app.post("/review-queue/{review_id}/reject")
    def review_queue_reject(request: Request, review_id: int, note: str = Form(""), csrf_token: str = Form(...)):
        session = _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        _structured_import_service(app, session).reject(review_id, user_id=session.user_id, note=note)
        return RedirectResponse("/review-queue?notice=" + quote("Review item rejected."), status_code=303)

    @app.get("/plugins", response_class=HTMLResponse)
    def plugins_page(request: Request):
        session = _normal_session(app, request)
        return templates.TemplateResponse(request=request, name="plugins.html", context=_template_context(
            request, session=session, plugins=app.state.plugins.list_plugins()
        ))

    @app.post("/plugins/{plugin_key}/toggle")
    def plugin_toggle(request: Request, plugin_key: str, enabled: str = Form("0"), csrf_token: str = Form(...)):
        _normal_session(app, request)
        app.state.csrf.validate(request, csrf_token)
        app.state.plugins.set_enabled(plugin_key, enabled == "1")
        return RedirectResponse("/plugins", status_code=303)

    @app.get("/backups", response_class=HTMLResponse)
    def backups_page(request: Request, notice: str = ""):
        session = _normal_session(app, request)
        items = [dict(r) for r in app.state.db.execute("SELECT * FROM backups ORDER BY created_at DESC, id DESC").fetchall()]
        schedule = _backup_schedule_service(app, session).get_policy(default_retention=app.state.config.backup_retention)
        return templates.TemplateResponse(
            request=request,
            name="backups.html",
            context=_template_context(
                request,
                session=session,
                backups=items,
                schedule=schedule,
                database_path=str(app.state.paths.database),
                backup_path=str(app.state.paths.backups),
                notice=notice,
            ),
        )

    @app.post("/backups/create")
    def backup_create(request: Request, label: str = Form(""), csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        _backup_service(app, session).create(label.strip() or None, backup_type="MANUAL")
        return RedirectResponse("/backups?notice=" + quote("Encrypted local backup created."), status_code=303)

    @app.post("/backups/schedule")
    def backup_schedule_update(
        request: Request,
        enabled: str = Form("0"),
        interval_days: int = Form(1),
        retention: int = Form(20),
        csrf_token: str = Form(...),
    ):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        try:
            _backup_schedule_service(app, session).update_policy(
                enabled=enabled == "1",
                interval_days=interval_days,
                retention=retention,
                default_retention=app.state.config.backup_retention,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return RedirectResponse("/backups?notice=" + quote("Local backup schedule updated."), status_code=303)

    @app.post("/backups/schedule/run")
    def backup_schedule_run(request: Request, csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        _backup_schedule_service(app, session).run_now(default_retention=app.state.config.backup_retention)
        return RedirectResponse("/backups?notice=" + quote("Scheduled backup run completed."), status_code=303)

    @app.post("/backups/retention/apply")
    def backup_retention_apply(request: Request, csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        service = _backup_schedule_service(app, session)
        deleted = service.apply_retention()
        return RedirectResponse("/backups?notice=" + quote(f"Retention applied. {deleted} old scheduled backup(s) removed."), status_code=303)

    @app.post("/backups/{backup_id}/verify")
    def backup_verify(request: Request, backup_id: int, csrf_token: str = Form(...)):
        session = _normal_session(app, request); app.state.csrf.validate(request, csrf_token)
        row = app.state.db.execute("SELECT path,status FROM backups WHERE id=?", (backup_id,)).fetchone()
        if row is None or row["status"] == "DELETED":
            raise ValidationError("Backup record was not found or has been deleted by retention.")
        _backup_service(app, session).verify(Path(row["path"]))
        return RedirectResponse("/backups?notice=" + quote("Backup integrity verified."), status_code=303)


    @app.get("/api/v1/review-queue")
    def api_review_queue(request: Request, status: str = "PENDING"):
        session = _normal_session(app, request, api=True)
        return {"items": _structured_import_service(app, session).list_review(status=status)}

    # Versioned localhost API. Mutating calls require the same authenticated session and CSRF token.
    @app.get("/api/v1/dashboard")
    def api_dashboard(request: Request):
        _normal_session(app, request, api=True)
        service = DashboardService(app.state.db)
        return {"metrics": service.metrics(), "process_progress": service.process_progress()}

    @app.get("/api/v1/licence")
    def api_licence(request: Request):
        _session_from_request(app, request)
        status = _licence_status(app)
        return {
            "mode": status.mode,
            "days_remaining": status.days_remaining,
            "expires_at": status.expires_at,
            "request_code": status.request_code,
            "normal_use_allowed": status.normal_use_allowed,
            "warning": status.warning,
            "active_licence": _active_licence(app),
        }

    @app.get("/api/v1/clients")
    def api_clients(request: Request, q: str = "", status: str = "ACTIVE", limit: int = 100):
        session = _normal_session(app, request, api=True)
        return {"items": _client_service(app, session).search(q, status or None, limit)}

    @app.post("/api/v1/clients")
    async def api_client_create(request: Request):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        try:
            payload = await request.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Request body must contain valid JSON.") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object.")
        client_id = _client_service(app, session).create(payload, user_id=session.user_id)
        return JSONResponse({"id": client_id}, status_code=201)

    @app.get("/api/v1/documents")
    def api_documents(
        request: Request,
        q: str = "",
        client_id: int | None = None,
        matter_id: int | None = None,
        category: str = "",
        limit: int = 100,
    ):
        session = _normal_session(app, request, api=True)
        items = _document_vault(app, session).list_documents(
            query=q, client_id=client_id, matter_id=matter_id, category=category, limit=limit
        )
        return {"items": items}

    @app.get("/api/v1/documents/{document_id}")
    def api_document_detail(request: Request, document_id: int):
        session = _normal_session(app, request, api=True)
        return _document_vault(app, session).metadata(document_id)

    @app.get("/api/v1/documents/{document_id}/download")
    def api_document_download(request: Request, document_id: int):
        session = _normal_session(app, request, api=True)
        vault = _document_vault(app, session)
        document = vault.metadata(document_id, text_limit=0)
        clear = vault.read(document_id)
        filename = quote(sanitize_filename(document["safe_filename"]))
        return Response(
            content=clear,
            media_type=document["media_type"],
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
        )

    @app.post("/api/v1/documents/upload")
    async def api_document_upload(
        request: Request,
        file: UploadFile = File(...),
        client_id: str = Form(""),
        matter_id: str = Form(""),
        category: str = Form(""),
        tags: str = Form(""),
        force_ocr: str = Form(""),
    ):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        parsed_client = _optional_int(client_id, "Client")
        parsed_matter = _optional_int(matter_id, "Matter")
        temporary = await _save_uploaded_file(app, file)
        try:
            vault = _document_vault(app, session)
            duplicate_id = vault.find_duplicate(temporary, client_id=parsed_client, matter_id=parsed_matter)
            document_id = vault.ingest(
                temporary,
                client_id=parsed_client,
                matter_id=parsed_matter,
                category=category,
                tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
                source_label="Local API upload",
                force_ocr=force_ocr == "1",
                user_id=session.user_id,
            )
        finally:
            temporary.unlink(missing_ok=True)
            try:
                temporary.parent.rmdir()
            except OSError:
                pass
        return JSONResponse({"id": document_id, "duplicate": duplicate_id is not None}, status_code=200 if duplicate_id else 201)

    @app.post("/api/v1/documents/import-zip")
    async def api_document_zip_import(
        request: Request,
        file: UploadFile = File(...),
        client_id: str = Form(""),
        matter_id: str = Form(""),
        category: str = Form(""),
        tags: str = Form(""),
    ):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        parsed_client = _optional_int(client_id, "Client")
        parsed_matter = _optional_int(matter_id, "Matter")
        temporary = await _save_uploaded_file(app, file)
        try:
            result = _document_vault(app, session).import_zip(
                temporary,
                client_id=parsed_client,
                matter_id=parsed_matter,
                category=category,
                tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
                user_id=session.user_id,
            )
        finally:
            temporary.unlink(missing_ok=True)
            try:
                temporary.parent.rmdir()
            except OSError:
                pass
        return result

    @app.post("/api/v1/documents/{document_id}/ocr")
    def api_document_ocr(request: Request, document_id: int):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        result = _document_vault(app, session).reprocess_ocr(document_id, user_id=session.user_id)
        return {"id": document_id, "ocr_status": result.ocr_status, "method": result.method, "text_length": len(result.text)}

    @app.post("/api/v1/documents/{document_id}/metadata")
    async def api_document_metadata(request: Request, document_id: int):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        try:
            payload = await request.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Request body must contain valid JSON.") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object.")
        _document_vault(app, session).update_metadata(
            document_id,
            category=payload.get("category"),
            tags=payload.get("tags"),
            review_status=str(payload.get("review_status", "REVIEW_REQUIRED")),
            user_id=session.user_id,
        )
        return {"id": document_id, "updated": True}


    @app.get("/api/v1/status")
    def api_status(request: Request):
        session = _session_from_request(app, request)
        status = _licence_status(app)
        return {
            "api_version": "v1",
            "application_version": "0.1.14-dev",
            "user": {"id": session.user_id, "username": session.username},
            "licence_mode": status.mode,
            "normal_use_allowed": status.normal_use_allowed,
            "offline_only": True,
            "database": "local",
            "internet_updates_enabled": False,
        }

    @app.get("/api/v1/clients/{client_id}")
    def api_client_detail(request: Request, client_id: int):
        session = _normal_session(app, request, api=True)
        return _client_service(app, session).get(client_id)

    @app.put("/api/v1/clients/{client_id}")
    async def api_client_update(request: Request, client_id: int):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object.")
        try:
            expected_version = int(payload.pop("row_version"))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="row_version is required and must be an integer.") from exc
        version = _client_service(app, session).update(client_id, payload, expected_version, user_id=session.user_id)
        return {"id": client_id, "row_version": version, "updated": True}

    @app.post("/api/v1/clients/{client_id}/status/{action}")
    def api_client_status(request: Request, client_id: int, action: str):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        service = _client_service(app, session)
        if action == "archive":
            service.archive(client_id, user_id=session.user_id)
        elif action == "restore":
            service.restore(client_id, user_id=session.user_id)
        elif action == "delete":
            service.soft_delete(client_id, user_id=session.user_id)
        else:
            raise HTTPException(status_code=404, detail="Unknown client status action.")
        return {"id": client_id, "action": action, "updated": True}

    @app.get("/api/v1/legal/statutes")
    def api_legal_statutes(request: Request, verification_status: str = "", limit: int = 500):
        session = _normal_session(app, request, api=True)
        return {"items": _legal_service(app, session).list_statutes(verification_status=verification_status or None, limit=limit)}

    @app.get("/api/v1/legal/statutes/{statute_id}")
    def api_legal_statute(request: Request, statute_id: int):
        session = _normal_session(app, request, api=True)
        return _legal_service(app, session).statute_detail(statute_id)

    @app.get("/api/v1/legal/provisions/{provision_id}")
    def api_legal_provision(request: Request, provision_id: int):
        session = _normal_session(app, request, api=True)
        return _legal_service(app, session).provision_detail(provision_id)

    @app.get("/api/v1/legal/judgments")
    def api_legal_judgments(request: Request, verification_status: str = "", court: str = "", limit: int = 250):
        session = _normal_session(app, request, api=True)
        return {"items": _legal_service(app, session).list_judgments(verification_status=verification_status or None, court=court or None, limit=limit)}

    @app.get("/api/v1/legal/judgments/{judgment_id}")
    def api_legal_judgment(request: Request, judgment_id: int):
        session = _normal_session(app, request, api=True)
        return _legal_service(app, session).judgment_detail(judgment_id)

    @app.get("/api/v1/workflow/instances")
    def api_workflow_instances(request: Request, matter_id: int | None = None):
        _normal_session(app, request, api=True)
        sql = "SELECT * FROM process_instances"
        params: list[Any] = []
        if matter_id is not None:
            sql += " WHERE matter_id=?"; params.append(matter_id)
        sql += " ORDER BY id DESC LIMIT 250"
        return {"items": [dict(r) for r in app.state.db.execute(sql, params).fetchall()]}

    @app.get("/api/v1/workflow/instances/{instance_id}/stages")
    def api_workflow_stages(request: Request, instance_id: int):
        session = _normal_session(app, request, api=True)
        return {"items": _workflow_service(app, session).stages(instance_id)}

    @app.post("/api/v1/workflow/instances/{instance_id}/recalculate")
    async def api_workflow_recalculate(request: Request, instance_id: int):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        payload = await request.json()
        reason = str(payload.get("reason", "API-requested recalculation")) if isinstance(payload, dict) else "API-requested recalculation"
        changed = _workflow_service(app, session).recalculate(instance_id, reason, user_id=session.user_id)
        return {"instance_id": instance_id, "changed_deadlines": changed}

    @app.post("/api/v1/recommendations/generate")
    async def api_recommendations_generate(request: Request):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        payload = await request.json()
        if not isinstance(payload, dict) or not payload.get("matter_id"):
            raise HTTPException(status_code=400, detail="matter_id is required.")
        matter_id = int(payload["matter_id"])
        return {"items": _recommendation_service(app, session).generate_for_matter(matter_id)}

    @app.get("/api/v1/forms")
    def api_forms(request: Request):
        _normal_session(app, request, api=True)
        forms = [dict(r) for r in app.state.db.execute("SELECT id,name,form_code,classification,template_type,verification_status,active,updated_at FROM forms ORDER BY name").fetchall()]
        return {"items": forms}

    @app.get("/api/v1/forms/versions/{version_id}")
    def api_form_version(request: Request, version_id: int):
        session = _normal_session(app, request, api=True)
        row = app.state.db.execute("SELECT id,form_id,matter_id,version_number,output_type,output_path,created_at FROM form_versions WHERE id=?", (version_id,)).fetchone()
        if row is None:
            raise ValidationError("Generated form version was not found.")
        result = dict(row)
        result["content"] = _form_service(app, session).content(version_id)
        return result

    @app.get("/api/v1/backups")
    def api_backups(request: Request):
        session = _normal_session(app, request, api=True)
        policy = _backup_schedule_service(app, session).get_policy(default_retention=app.state.config.backup_retention)
        items = [dict(r) for r in app.state.db.execute("SELECT id,backup_uuid,path,created_at,size_bytes,status,backup_type,label FROM backups ORDER BY created_at DESC LIMIT 250").fetchall()]
        return {"policy": policy.__dict__, "items": items}

    @app.post("/api/v1/backups/create")
    async def api_backup_create(request: Request):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        payload = await request.json()
        label = str(payload.get("label", "")).strip() if isinstance(payload, dict) else ""
        path = _backup_service(app, session).create(label=label or None)
        return JSONResponse({"path": str(path), "created": True}, status_code=201)

    @app.get("/api/v1/plugins")
    def api_plugins(request: Request):
        _normal_session(app, request, api=True)
        return {"items": app.state.plugins.list_plugins(), "internet_update_permission_available": False}

    @app.post("/api/v1/review-queue/{review_id}/resolve")
    async def api_review_resolve(request: Request, review_id: int):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        payload = await request.json()
        note = str(payload.get("note", "")).strip() if isinstance(payload, dict) else ""
        return _structured_import_service(app, session).resolve(review_id, user_id=session.user_id, note=note or None)

    @app.post("/api/v1/review-queue/{review_id}/reject")
    async def api_review_reject(request: Request, review_id: int):
        session = _normal_session(app, request, api=True)
        app.state.csrf.validate(request, request.headers.get("X-CSRF-Token"))
        payload = await request.json()
        note = str(payload.get("note", "")).strip() if isinstance(payload, dict) else ""
        _structured_import_service(app, session).reject(review_id, user_id=session.user_id, note=note or None)
        return {"id": review_id, "rejected": True}

    return app
