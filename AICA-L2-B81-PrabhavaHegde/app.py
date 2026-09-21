"""
Local API server. Binds to 127.0.0.1 only - this never listens on a network interface.

The UI is a separate concern. Every piece of state the interface needs is exposed
as JSON here, so the frontend can be rebuilt without touching assessment logic.

Run:  python app.py [--clients-dir PATH] [--port N] [--no-browser]
      (opens the browser at http://127.0.0.1:8731 by default)

Assessment files live in clients/ beside the exe (or beside app.py when run from
source). On first start, when that folder holds no assessment, a fictitious
sample assessment is created so the evidence gate can be seen at once.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shutil
import sys
import threading
import time
import webbrowser
from datetime import date
from pathlib import Path, PureWindowsPath

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai_layer
import role as role_module
from catalogue import applicable, load_catalogue, score
from models import Client, Project
from report import build_report, report_filename


def _resource_dir() -> Path:
    """Where bundled read-only files live: rules/, ui/, config.yaml.

    Under PyInstaller --onefile these are extracted to a temp folder that is
    deleted on exit, so they must be read from sys._MEIPASS rather than __file__.
    """
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))


def _data_dir() -> Path:
    """Where assessments are written: beside the exe when frozen, never inside
    the PyInstaller bundle, which is wiped on exit."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


RES = _resource_dir()
DATA = _data_dir()
PORT = 8731


def _load_config() -> dict:
    # A config.yaml beside the exe wins over the bundled copy, so the AI
    # provider can be switched without rebuilding.
    for path in (DATA / "config.yaml", RES / "config.yaml"):
        if path.is_file():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


CONFIG = _load_config()
AI_CFG = CONFIG.get("ai", {}) or {}
CLIENTS_DIR = DATA / (CONFIG.get("assessment", {}) or {}).get("clients_dir", "clients")

CATALOGUE = load_catalogue(RES / "rules")
# Control ids are checked before any file is written, so a path-like id never
# reaches the evidence folder.
CATALOGUE_IDS = {c.id for c in CATALOGUE}

app = FastAPI(title="DPDP Readiness Assessor", docs_url="/api/docs")


def _provider():
    return ai_layer.get_provider(AI_CFG.get("provider"), model=AI_CFG.get("model") or None)


# --------------------------------------------------------------------------
# Loopback and same-origin guard
#
# Binding to 127.0.0.1 keeps other machines out, but not other web pages open in
# the user's own browser:
# - DNS rebinding: a hostile domain re-points itself at 127.0.0.1. Its requests
#   still carry its own name in Host, so only a loopback Host is served.
# - Cross-site writes: a page on any site can POST here without a preflight.
#   A write whose Origin is not this server's own is refused, so a stranger's
#   page cannot attach "evidence" that satisfies the gate.
# --------------------------------------------------------------------------

LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
_SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
_HOST_RE = re.compile(r"^(?P<name>[A-Za-z0-9.\-]+)(?::(?P<port>[0-9]{1,5}))?$")


def _loopback_host(host_header: str) -> str | None:
    m = _HOST_RE.fullmatch(host_header.strip())
    if not m or m.group("name").lower() not in LOOPBACK_HOSTS:
        return None
    port = m.group("port")
    return m.group("name").lower() + (f":{port}" if port else "")


@app.middleware("http")
async def loopback_same_origin_only(request, call_next):
    host = _loopback_host(request.headers.get("host", ""))
    if host is None:
        return JSONResponse({"detail": "This server answers only to 127.0.0.1 or localhost."},
                            status_code=400)
    if request.method not in _SAFE_METHODS:
        origin = request.headers.get("origin")
        site = request.headers.get("sec-fetch-site")
        if origin is not None and origin.lower() != f"http://{host}":
            return JSONResponse({"detail": "Cross-origin write refused."}, status_code=403)
        if site is not None and site.lower() not in ("same-origin", "none"):
            return JSONResponse({"detail": "Cross-origin write refused."}, status_code=403)
    return await call_next(request)


# --------------------------------------------------------------------------
# Request bodies
# --------------------------------------------------------------------------

class NewClient(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    entity_type: str = Field(max_length=100)
    sector: str | None = Field(None, max_length=200)
    contact_person: str | None = Field(None, max_length=200)
    assessed_by: str | None = Field(None, max_length=200)
    assessment_date: str = Field(default_factory=lambda: date.today().isoformat(), max_length=10)
    flags: list[str] = []


class RoleAnswers(BaseModel):
    answers: dict[str, bool]


class ResponseUpdate(BaseModel):
    status: str
    assessor_note: str = Field("", max_length=4000)
    mgmt_response: str = Field("", max_length=4000)
    mgmt_owner: str = Field("", max_length=200)
    mgmt_target_date: str = Field("", max_length=40)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    if not slug:
        raise HTTPException(400, "Client name must contain at least one letter or digit.")
    return slug[:120]


# What slugify can produce, and nothing else, so a decoded '..' or backslash
# can never walk out of clients/.
SLUG_RE = re.compile(r"[A-Za-z0-9_]{1,255}")

# Names Windows would silently misread: NTFS alternate data streams, device
# names, and characters it refuses outright.
_BAD_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_DEVICE_NAMES = re.compile(r"(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[0-9]|LPT[0-9])", re.IGNORECASE)


def usable_evidence_name(name: str) -> bool:
    if _BAD_NAME_CHARS.search(name) or name != name.rstrip(" ."):
        return False
    stem = name.split(".", 1)[0].rstrip(" ")
    return not _DEVICE_NAMES.fullmatch(stem) and len(name) <= 200


def open_project(slug: str) -> Project:
    if not SLUG_RE.fullmatch(slug):
        raise HTTPException(404, "No assessment found with that name.")
    clients = CLIENTS_DIR.resolve()
    folder = (clients / slug).resolve()
    if folder.parent != clients or not (folder / "assessment.db").is_file():
        raise HTTPException(404, f"No assessment found for '{slug}'.")
    return Project(folder)


def scope_for(project: Project) -> list:
    """The controls that apply to this engagement, given role and profile flags."""
    client = project.get_client()
    if not client:
        raise HTTPException(400, "Client profile not saved yet.")
    return applicable(CATALOGUE, client.role, client.flags)


def control_payload(c, resp: dict, ev_count: int) -> dict:
    return {
        "id": c.id, "rule_id": c.rule_id, "rule_ref": c.rule_ref, "rule_title": c.rule_title,
        "title": c.title, "question": c.question, "guidance": c.guidance,
        "evidence_required": c.evidence_required, "weight": c.weight,
        "severity": c.severity_if_absent, "needs_evidence": c.needs_evidence,
        "citation_status": c.citation_status,
        "status": resp.get("status"),
        "assessor_note": resp.get("assessor_note", ""),
        "mgmt_response": resp.get("mgmt_response", ""),
        "mgmt_owner": resp.get("mgmt_owner", ""),
        "mgmt_target_date": resp.get("mgmt_target_date", ""),
        "evidence_count": ev_count,
        # Claimed but unevidenced. The UI strikes the row the moment this is true.
        "evidence_missing": c.needs_evidence and ev_count == 0
                            and resp.get("status") in ("Present", "Partial"),
    }


# --------------------------------------------------------------------------
# Meta
# --------------------------------------------------------------------------

@app.get("/api/meta")
def meta():
    """Everything the UI needs to render without hardcoding domain knowledge."""
    provider = _provider()
    rules = {}
    for c in CATALOGUE:
        rules.setdefault(c.rule_id, {"rule_id": c.rule_id, "title": c.rule_title,
                                     "ref": c.rule_ref, "controls": 0, "weight": 0})
        rules[c.rule_id]["controls"] += 1
        rules[c.rule_id]["weight"] += c.weight
    return {
        "statuses": ["Present", "Partial", "Absent"],
        "bands": [
            {"name": "Critical", "from": 0, "to": 39.9},
            {"name": "Developing", "from": 40, "to": 69.9},
            {"name": "Substantial", "from": 70, "to": 89.9},
            {"name": "Mature", "from": 90, "to": 100},
        ],
        "rules": sorted(rules.values(), key=lambda r: int(r["rule_id"][1:])),
        "total_controls": len(CATALOGUE),
        "ai_provider": provider.name,
        "ai_active": provider.name != "offline",
        "entity_types": ["Private Limited Company", "Public Limited Company", "LLP",
                         "Partnership Firm", "Proprietorship", "Trust", "Society", "HUF"],
        "profile_flags": [],
    }


@app.get("/api/role/questions")
def role_questions():
    return {
        "questions": [{"id": q["id"], "text": q["text"]} for q in role_module.QUESTIONS],
        "note": role_module.ROLE_NOTE,
    }


# --------------------------------------------------------------------------
# Assessments
# --------------------------------------------------------------------------

@app.get("/api/clients")
def list_clients():
    out = []
    if not CLIENTS_DIR.is_dir():
        return out
    for folder in sorted(CLIENTS_DIR.iterdir()):
        if not (folder / "assessment.db").exists():
            continue
        p = Project(folder)
        try:
            c = p.get_client()
            if c:
                controls = applicable(CATALOGUE, c.role, c.flags)
                ids = {x.id for x in controls}
                result = score(controls, p.statuses(), p.evidence_counts())
                out.append({
                    "slug": folder.name, "name": c.name, "entity_type": c.entity_type,
                    "role": c.role, "assessment_date": c.assessment_date,
                    "score": result["score"], "band": result["band"],
                    "answered": sum(1 for cid in p.statuses() if cid in ids),
                    "total": len(controls),
                })
        finally:
            p.close()
    return out


@app.post("/api/clients")
def create_client(body: NewClient):
    slug = slugify(body.name)
    if (CLIENTS_DIR / slug / "assessment.db").exists():
        raise HTTPException(409, f"An assessment for '{body.name}' already exists.")
    project = Project(CLIENTS_DIR / slug)
    try:
        project.save_client(Client(
            name=body.name.strip(), entity_type=body.entity_type, sector=body.sector,
            contact_person=body.contact_person, assessed_by=body.assessed_by,
            assessment_date=body.assessment_date,
            role="fiduciary",          # provisional until the role questions are answered
            flags=set(body.flags),
        ))
    finally:
        project.close()
    return {"slug": slug}


@app.get("/api/clients/{slug}")
def get_client(slug: str):
    p = open_project(slug)
    try:
        c = p.get_client()
    finally:
        p.close()
    return {
        "slug": slug, "name": c.name, "entity_type": c.entity_type, "sector": c.sector,
        "contact_person": c.contact_person, "assessed_by": c.assessed_by,
        "assessment_date": c.assessment_date, "role": c.role,
        "role_reasoning": c.role_reasoning, "flags": sorted(c.flags),
    }


@app.post("/api/clients/{slug}/role")
def set_role(slug: str, body: RoleAnswers):
    p = open_project(slug)
    try:
        finding = role_module.determine(body.answers)
        p.set_role(finding.role, finding.reasoning)
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        p.close()
    return {"role": finding.role, "score": finding.score,
            "reasoning": finding.reasoning, "borderline": finding.borderline}


@app.get("/api/clients/{slug}/controls")
def get_controls(slug: str):
    p = open_project(slug)
    try:
        controls = scope_for(p)
        responses, counts = p.responses(), p.evidence_counts()
    finally:
        p.close()
    return [control_payload(c, responses.get(c.id, {}), counts.get(c.id, 0)) for c in controls]


@app.put("/api/clients/{slug}/controls/{control_id}")
def update_response(slug: str, control_id: str, body: ResponseUpdate):
    if control_id not in CATALOGUE_IDS:
        raise HTTPException(404, f"Unknown control '{control_id}'.")
    if body.status not in ("Present", "Partial", "Absent"):
        raise HTTPException(400, "Status must be Present, Partial or Absent.")
    p = open_project(slug)
    try:
        changed = p.set_response(control_id, body.status, body.assessor_note, body.mgmt_response,
                                 body.mgmt_owner, body.mgmt_target_date)
        result = score(scope_for(p), p.statuses(), p.evidence_counts())
    finally:
        p.close()
    # Live score, so the UI updates inline.
    return {"saved": control_id, "changed": changed, "score": result}


@app.post("/api/clients/{slug}/controls/{control_id}/evidence")
async def upload_evidence(slug: str, control_id: str, file: UploadFile, description: str = ""):
    if control_id not in CATALOGUE_IDS:
        raise HTTPException(404, f"Unknown control '{control_id}'.")
    # A client can send a path as the file name; only the base name survives.
    safe = PureWindowsPath(file.filename or "").name
    if not safe or safe in (".", ".."):
        raise HTTPException(400, "The uploaded file has no usable name.")
    if not usable_evidence_name(safe):
        raise HTTPException(400, "The file name is not one Windows can store as it is. "
                                 "Rename the file and attach it again.")

    p = open_project(slug)
    tmp_dir = p.folder / ".upload" / secrets.token_hex(8)
    try:
        if control_id not in p.statuses():
            raise HTTPException(400, "Choose a status for this control before attaching evidence.")
        content = await file.read()
        # An empty file evidences nothing, and must not open the gate.
        if not content:
            raise HTTPException(400, "The file is empty. Attach the document that evidences this control.")
        tmp_dir.mkdir(parents=True)
        tmp = tmp_dir / safe
        tmp.write_bytes(content)
        p.add_evidence(control_id, tmp, description[:500])
        counts = p.evidence_counts()
        result = score(scope_for(p), p.statuses(), counts)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        p.close()
    return {"control_id": control_id, "evidence_count": counts.get(control_id, 0), "score": result}


@app.get("/api/clients/{slug}/evidence")
def get_evidence(slug: str):
    p = open_project(slug)
    try:
        return p.evidence()
    finally:
        p.close()


@app.get("/api/clients/{slug}/score")
def get_score(slug: str):
    p = open_project(slug)
    try:
        controls = scope_for(p)
        responses = p.responses()
        result = score(controls, p.statuses(), p.evidence_counts())
    finally:
        p.close()

    by_rule = {}
    for c in controls:
        r = by_rule.setdefault(c.rule_id, {"rule_id": c.rule_id, "title": c.rule_title,
                                           "Present": 0, "Partial": 0, "Absent": 0, "weight": 0})
        r[responses.get(c.id, {}).get("status") or "Absent"] += 1
        r["weight"] += c.weight
    result["by_rule"] = sorted(by_rule.values(), key=lambda r: int(r["rule_id"][1:]))
    return result


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

@app.post("/api/clients/{slug}/report")
def generate_report(slug: str, use_ai: bool = True):
    p = open_project(slug)
    try:
        controls = scope_for(p)
        statuses = p.statuses()
        # The score is computed here, before and independently of any model call.
        result = score(controls, statuses, p.evidence_counts())

        ai_text = {}
        provider = _provider()
        if use_ai and provider.name != "offline":
            # Only id, title, status and weight cross the network. No client
            # name, notes, responses or evidence content.
            findings = [
                ai_layer.Finding(control=c.id, title=c.title,
                                 status=statuses.get(c.id, "Absent"), weight=c.weight)
                for c in controls if statuses.get(c.id, "Absent") in ("Absent", "Partial")
            ]
            ai_text = ai_layer.draft_findings(provider, findings)

        out = build_report(p, controls, p.responses(), result, ai_text)
    finally:
        p.close()
    return {
        "file": out.name,
        "download": f"/api/clients/{slug}/report/download",
        "score": result["score"], "band": result["band"],
        "ai_used": bool(ai_text), "provider": provider.name,
        "findings_drafted": len(ai_text),
    }


@app.get("/api/clients/{slug}/report/download")
def download_report(slug: str):
    p = open_project(slug)
    try:
        client = p.get_client()
        chosen = p.output_dir / report_filename(client) if client else None
    finally:
        p.close()
    if chosen is None or not chosen.is_file():
        raise HTTPException(404, "No report generated yet.")
    return FileResponse(
        chosen, filename=chosen.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# --------------------------------------------------------------------------
# Static UI. Mounted last so /api routes always win.
# --------------------------------------------------------------------------

UI_DIR = RES / "ui"
if UI_DIR.exists():
    app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")


def _port(value: str) -> int:
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a port number: {value!r}") from None
    if not 1 <= n <= 65535:
        raise argparse.ArgumentTypeError(f"port must be from 1 to 65535, not {n}")
    return n


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DPDP Readiness Assessor (capstone edition).")
    parser.add_argument("--clients-dir", default=None, metavar="PATH",
                        help="Folder that holds the assessment files. Default: clients beside the program.")
    parser.add_argument("--port", type=_port, default=PORT,
                        help=f"Port on 127.0.0.1 to listen on. Default: {PORT}.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser window.")
    parser.add_argument("--no-sample", action="store_true",
                        help="Do not create the fictitious sample assessment in an empty folder.")
    return parser.parse_args(argv)


def serve(port: int, on_ready=None) -> bool:
    """Run the server until it stops. Returns False if it never started listening.

    on_ready is called only after THIS process is listening, so a port held by
    another copy never gets a browser window pointed at the wrong files.
    """
    # The host is fixed: only the port is configurable.
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    finished = threading.Event()

    def _when_listening() -> None:
        while not finished.is_set():
            if server.started:
                on_ready(server)
                return
            time.sleep(0.1)

    if on_ready is not None:
        threading.Thread(target=_when_listening, daemon=True).start()
    try:
        server.run()
    except SystemExit:
        pass
    finally:
        finished.set()
    return bool(server.started)


def main(argv: list[str] | None = None) -> None:
    global CLIENTS_DIR
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="backslashreplace")
            except (OSError, ValueError):
                pass
    args = parse_args(argv)
    if args.clients_dir:
        CLIENTS_DIR = Path(args.clients_dir).expanduser().resolve()
    if CLIENTS_DIR.exists() and not CLIENTS_DIR.is_dir():
        raise SystemExit(f"Not a folder: {CLIENTS_DIR}")
    CLIENTS_DIR.mkdir(parents=True, exist_ok=True)

    if not args.no_sample and not any(CLIENTS_DIR.glob("*/assessment.db")):
        import demo_seed
        demo_seed.seed(CLIENTS_DIR, CATALOGUE)
        print("Created the fictitious sample assessment (Meridian Textiles).", flush=True)

    url = f"http://127.0.0.1:{args.port}"
    provider = _provider()
    print(f"DPDP Readiness Assessor on {url}", flush=True)
    print(f"Assessment files: {CLIENTS_DIR}", flush=True)
    print(f"AI drafting: {provider.name}"
          + ("" if provider.name != "offline" else " (set GEMINI_API_KEY to enable Gemini)"), flush=True)
    print("Close this window to stop the app.", flush=True)
    on_ready = None if args.no_browser else (lambda _server: webbrowser.open(url))
    if not serve(args.port, on_ready):
        raise SystemExit(
            f"Could not listen on 127.0.0.1:{args.port}. The port is in use, perhaps by another "
            "copy of this app. Close it, or start this one with --port and a different number.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        # A double-clicked exe closes its window at once; keep it open so the
        # reason (a port in use, for instance) can be read.
        if exc.code not in (None, 0) and getattr(sys, "frozen", False):
            print(exc.code if isinstance(exc.code, str) else "", flush=True)
            try:
                input("Press Enter to close.")
            except EOFError:
                pass
        raise
