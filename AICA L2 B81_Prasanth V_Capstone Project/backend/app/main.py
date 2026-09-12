import os
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from .config import UPLOADS_DIR, BASE_DIR
from .database import engine, Base
from .seed import seed_database
from .routers import (
    auth, companies, assets, bulk, printing, templates, audit, dashboard, admin
)

# Initialize FastAPI application
app = FastAPI(
    title="Asset Tagging & Label Management System",
    description="Enterprise Multi-Company Fixed Asset & Inventory Tagging Engine",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Friendly User Error Handler (Specification Requirement #40)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_str = str(exc)
    print(f"[ERROR LOG] Path: {request.url.path} | Error: {error_str}")
    # Return polite, actionable message to user
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Unable to complete the operation. Please verify your data and try again."}
    )

# Register API Routers
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(assets.router)
app.include_router(bulk.router)
app.include_router(printing.router)
app.include_router(templates.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(admin.router)

# Mount uploads directory for logos and assets
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Frontend Static Files Mount (if built)
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("uploads/"):
            return JSONResponse(status_code=404, content={"detail": "API endpoint not found"})
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse(status_code=404, content={"detail": "Frontend build not found"})

@app.on_event("startup")
def on_startup():
    seed_database()

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Asset Tagging Engine v1.0.0"}
