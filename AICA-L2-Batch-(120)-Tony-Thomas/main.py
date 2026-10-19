import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.database import engine, Base, SessionLocal
from app import seed_data
from app.api import coa_tb, gl, budget, p2p, ap, ar, tax, reports, approvals, inventory, settings, companies

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist and seed demo database
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data.seed_database(db, force_reset=False)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Demo Business 21",
    description="All in one Accounting & Inventory System for Retail and Wholesale Trading of Consumer Goods",
    version="3.0.0",
    lifespan=lifespan
)

import sys

# Static and Templates
if getattr(sys, 'frozen', False):
    CURRENT_DIR = sys._MEIPASS
else:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(CURRENT_DIR, "app", "static")
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "app", "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include API Routers
app.include_router(companies.router)
app.include_router(settings.router)
app.include_router(inventory.router)
app.include_router(coa_tb.router)
app.include_router(gl.router)
app.include_router(budget.router)
app.include_router(p2p.router)
app.include_router(ap.router)
app.include_router(ar.router)
app.include_router(tax.router)
app.include_router(reports.router)
app.include_router(approvals.router)

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
