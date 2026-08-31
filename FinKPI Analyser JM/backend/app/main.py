import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import config
from .database import engine, Base, SessionLocal
from .models import UserModel, CompanyModel, TrialBalanceModel
from .auth import hash_password
from .api import (
    auth_routes,
    company_routes,
    tb_routes,
    financial_routes,
    kpi_routes,
    analysis_routes,
    report_routes
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Full-stack Financial KPI Analyzer RESTful API & Dashboard for 10-Period Trial Balance comparative analysis.",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(company_routes.router)
app.include_router(tb_routes.router)
app.include_router(financial_routes.router)
app.include_router(kpi_routes.router)
app.include_router(analysis_routes.router)
app.include_router(report_routes.router)

def seed_demo_data():
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.username == config.DEMO_USER).first()
        if not user:
            user = UserModel(
                username=config.DEMO_USER,
                email="admin@finkpi.com",
                password_hash=hash_password(config.DEMO_PASSWORD),
                role="admin",
                is_active=True
            )
            db.add(user)
            db.commit()

        company = db.query(CompanyModel).filter(CompanyModel.company_code == "COMP001").first()
        if not company:
            company = CompanyModel(
                company_code="COMP001",
                company_name="ABC Manufacturing Co.",
                industry="Manufacturing",
                currency="USD",
                currency_unit="thousands",
                fiscal_year_start=1,
                shares_outstanding=1000000.0,
                headcount=500
            )
            db.add(company)
            db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

seed_demo_data()

# Root frontend dashboard route
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>FinKPI Analyzer Backend Running. Open /docs for API Swagger.</h1>")

@app.get("/health")
def health_check():
    return {"status": "healthy", "app": config.APP_NAME, "version": config.APP_VERSION}

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
