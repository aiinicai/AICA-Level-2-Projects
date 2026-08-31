from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import reset_active_client_slug, set_active_client_slug
from app.services.client_store import is_testing, resolve_active_slug
from app.services.client_runtime import bootstrap_clients
import app.models  # noqa: F401 — register all tables for create_all

from app.api.views import router as views_router
from app.api.auth import router as auth_router
from app.api.branches import router as branches_router
from app.api.daybook import router as daybook_router
from app.api.cash_rec import router as cash_rec_router
from app.api.card_qr_rec import router as card_qr_router
from app.api.aggregators import router as aggregators_router
from app.api.imports import router as imports_router
from app.api.reports import router as reports_router
from app.api.attendance_rec import router as attendance_router
from app.api.audit import router as audit_router
from app.api.settings import router as settings_router
from app.api.users import router as users_router
from app.api.gst_report import router as gst_report_router
from app.api.clients import router as clients_router

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount Static Assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include Routers
app.include_router(views_router)
app.include_router(auth_router)
app.include_router(branches_router)
app.include_router(daybook_router)
app.include_router(cash_rec_router)
app.include_router(card_qr_router)
app.include_router(aggregators_router)
app.include_router(imports_router)
app.include_router(reports_router)
app.include_router(attendance_router)
app.include_router(audit_router)
app.include_router(settings_router)
app.include_router(users_router)
app.include_router(gst_report_router)
app.include_router(clients_router)


@app.middleware("http")
async def attach_client_context(request: Request, call_next):
    slug = resolve_active_slug(request.cookies.get("restroreco_client") or "")
    request.state.client_slug = slug
    token = set_active_client_slug(slug)
    try:
        return await call_next(request)
    finally:
        reset_active_client_slug(token)

@app.on_event("startup")
def startup_event():
    if is_testing():
        return
    bootstrap_clients()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
