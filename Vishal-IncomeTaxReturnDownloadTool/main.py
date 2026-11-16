"""
main.py
-------
FastAPI backend for the ITR-V download tool.

Flow (matches the HTML page in static/index.html):
  1. POST /api/login            -> PAN + Password -> masked email/mobile
  2. POST /api/confirm-email    -> check typed email against real one
  3. POST /api/confirm-mobile   -> check typed mobile against real one
  4. GET  /api/assessment-years -> (once both confirmed) list AYs for this PAN
  5. POST /api/download-itrv    -> download the ITR-V PDF for chosen AY

Run:
    pip install -r requirements.txt
    playwright install chromium
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from session_manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await manager.start()
    yield
    await manager.stop()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


# ---------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------
class LoginBody(BaseModel):
    pan: str
    password: str


class SessionBody(BaseModel):
    session_id: str


class ConfirmEmailBody(SessionBody):
    email: str


class ConfirmMobileBody(SessionBody):
    mobile: str


class DownloadBody(SessionBody):
    assessment_year: str


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.post("/api/login")
async def login(body: LoginBody):
    result = await manager.login(body.pan.strip().upper(), body.password)
    return result


@app.post("/api/confirm-email")
async def confirm_email(body: ConfirmEmailBody):
    ok = manager.confirm_email(body.session_id, body.email)
    return {"ok": ok, "error": None if ok else "Email does not match"}


@app.post("/api/confirm-mobile")
async def confirm_mobile(body: ConfirmMobileBody):
    ok = manager.confirm_mobile(body.session_id, body.mobile)
    return {"ok": ok, "error": None if ok else "Mobile number does not match"}


@app.get("/api/assessment-years")
async def assessment_years(session_id: str):
    return await manager.list_assessment_years(session_id)


@app.post("/api/download-itrv")
async def download_itrv(body: DownloadBody):
    result = await manager.download_itrv(body.session_id, body.assessment_year)
    if result.get("ok"):
        return FileResponse(
            result["file"],
            media_type="application/pdf",
            filename=f"ITRV_{body.assessment_year}.pdf",
        )
    return result