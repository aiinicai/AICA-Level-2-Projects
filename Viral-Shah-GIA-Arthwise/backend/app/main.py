import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import engine, Base, SessionLocal
from backend.app.core.security import hash_password
from backend.app.models.models import User
from backend.app.services.financial_calculator import PRELIMINARY_ASSESSMENT_DISCLAIMER
from backend.app.api.lenders import seed_lenders_if_empty

# Routers
from backend.app.api.auth import router as auth_router
from backend.app.api.clients import router as clients_router
from backend.app.api.proposals import router as proposals_router
from backend.app.api.checklist import router as checklist_router
from backend.app.api.documents import router as documents_router
from backend.app.api.extraction import router as extraction_router
from backend.app.api.evaluation import router as evaluation_router
from backend.app.api.cma import router as cma_router
from backend.app.api.lenders import router as lenders_router
from backend.app.api.reports import router as reports_router
from backend.app.api.admin import router as admin_router
from backend.app.api.master import router as master_router
from backend.app.api.companies import router as companies_router, seed_company_if_empty
from backend.app.services.location_service import seed_locations_if_empty

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production Loan Proposal Evaluation, CMA Projections and Debt Syndication Platform for Indian Financial Intermediaries."
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db_seeds():
    db = SessionLocal()
    try:
        # Seed default users if empty
        if db.query(User).count() == 0:
            default_users = [
                User(
                    email="admin@giaarthwise.com",
                    hashed_password=hash_password("Admin@123"),
                    full_name="Chief Credit Administrator",
                    role="admin"
                ),
                User(
                    email="analyst@giaarthwise.com",
                    hashed_password=hash_password("Analyst@123"),
                    full_name="Senior Debt Syndication Analyst",
                    role="analyst"
                ),
                User(
                    email="reviewer@giaarthwise.com",
                    hashed_password=hash_password("Reviewer@123"),
                    full_name="Principal Credit Reviewer",
                    role="reviewer"
                ),
                User(
                    email="client@giaarthwise.com",
                    hashed_password=hash_password("Client@123"),
                    full_name="Borrower Authorized Signatory",
                    role="client"
                )
            ]
            for u in default_users:
                db.add(u)
            db.commit()
            
        # Seed default lenders and policies
        seed_lenders_if_empty(db)

        seed_locations_if_empty(db)
        seed_company_if_empty(db)

        # Ensure dedicated case backend folders exist for all proposals
        from backend.app.models.models import Proposal
        from backend.app.core.config import get_case_dir
        for prop in db.query(Proposal).all():
            get_case_dir(prop.proposal_code)
    finally:
        db.close()

init_db_seeds()

# Register API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(clients_router, prefix=settings.API_V1_STR)
app.include_router(proposals_router, prefix=settings.API_V1_STR)
app.include_router(checklist_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(extraction_router, prefix=settings.API_V1_STR)
app.include_router(evaluation_router, prefix=settings.API_V1_STR)
app.include_router(cma_router, prefix=settings.API_V1_STR)
app.include_router(lenders_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(master_router, prefix=settings.API_V1_STR)
app.include_router(companies_router, prefix=settings.API_V1_STR)

@app.get("/api/v1/logos/{filename}")
def get_company_logo(filename: str):
    file_path = os.path.join(settings.STORAGE_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Logo not found")

@app.get("/api/health")
def health():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "regulatory_notice": PRELIMINARY_ASSESSMENT_DISCLAIMER
    }

@app.get("/download/app.apk")
def download_apk():
    apk_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "android", "bin", "giaarthwise-loan-facilitator.apk")
    if os.path.exists(apk_path):
        return FileResponse(
            apk_path,
            media_type="application/vnd.android.package-archive",
            filename="giaarthwise-loan-facilitator.apk"
        )
    raise HTTPException(
        status_code=404,
        detail="APK file is being prepared or not yet compiled. Run ./android/build_apk.sh to build the APK."
    )

# Mount Frontend Static Build for single-port deployment & PWA serving
from fastapi.staticfiles import StaticFiles
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

