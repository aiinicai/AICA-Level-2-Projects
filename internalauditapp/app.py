"""AuditPro - Internal Audit Management System (Flask API + static frontend)."""
import json
import os
import traceback
import uuid
import webbrowser
from collections import Counter
from threading import Timer

from flask import Flask, abort, jsonify, request, send_file, send_from_directory
from werkzeug.utils import secure_filename

import analytics
import db
import library
import reports
import seed
import services

FRONTEND_DIR = os.path.join(db.BASE_DIR, "frontend")
ANALYTICS_DIR = os.path.join(db.UPLOAD_DIR, "analytics")

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

RESOURCES = {"entities", "auditors", "universe", "plans", "engagements", "procedures", "pbc", "findings",
             "followups", "review_notes", "time_entries", "attachments"}

ENUMS = {
    "company_types": ["Single Entity", "Multinational Group"],
    "entity_types": ["Holding", "Subsidiary", "Branch", "Joint Venture", "Associate", "Division"],
    "audit_types": ["Assurance", "Advisory / Consulting", "Compliance", "IT Audit", "Investigation",
                    "Follow-up", "Continuous Auditing"],
    "engagement_statuses": ["Planned", "Planning", "Fieldwork", "Reporting", "Closed", "Cancelled"],
    "quarters": ["Q1", "Q2", "Q3", "Q4"],
    "procedure_statuses": ["Not Started", "In Progress", "Prepared", "Reviewed"],
    "test_results": ["Not Tested", "Effective", "Partially Effective", "Ineffective", "Not Applicable"],
    "finding_ratings": services.FINDING_RATINGS,
    "finding_statuses": ["Open", "In Progress", "Implemented", "Closed", "Risk Accepted"],
    "finding_categories": ["Control Design", "Operating Effectiveness", "Compliance", "Fraud / Misconduct",
                           "Efficiency / Value for Money", "Financial Reporting", "IT / Cyber", "Governance"],
    "root_causes": ["People / Training", "Process / Policy gap", "Technology / System", "Oversight / Monitoring",
                    "Resources", "Third party", "Deliberate override"],
    "pbc_statuses": ["Requested", "Partially Received", "Received", "Not Applicable"],
    "phases": ["Planning", "Fieldwork", "Reporting", "Follow-up", "Administration", "Training"],
    "plan_statuses": ["Draft", "Submitted", "Approved", "In Execution", "Closed"],
    "auditor_roles": ["Head of Internal Audit", "Audit Manager", "Senior Auditor", "Auditor", "IT Auditor",
                      "Co-source / External"],
    "frequencies": ["Annual", "Every 2 years", "Every 3 years", "Ad hoc"],
    "risk_factors": [
        {"key": "f_financial", "label": "Financial materiality", "weight": 25},
        {"key": "f_fraud", "label": "Fraud risk", "weight": 20},
        {"key": "f_regulatory", "label": "Regulatory / compliance", "weight": 15},
        {"key": "f_complexity", "label": "Process complexity", "weight": 15},
        {"key": "f_change", "label": "Degree of change", "weight": 10},
        {"key": "f_control_env", "label": "Control environment weakness", "weight": 15},
    ],
    "countries": ["United Arab Emirates", "Saudi Arabia", "Oman", "Qatar", "Bahrain", "Kuwait", "India",
                  "Egypt", "Jordan", "United Kingdom", "United States", "Singapore", "Other"],
    "currencies": ["AED", "SAR", "OMR", "QAR", "BHD", "KWD", "INR", "EGP", "JOD", "GBP", "USD", "EUR", "SGD"],
}


def ok(data=None, **kw):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload.update(kw)
    return jsonify(payload)


def body():
    return request.get_json(silent=True) or {}


@app.errorhandler(Exception)
def handle_error(exc):
    code = getattr(exc, "code", 500)
    if not isinstance(code, int):
        code = 500
    if code >= 500:
        traceback.print_exc()
    return jsonify({"ok": False, "error": getattr(exc, "description", None) or str(exc)}), code


# ------------------------------------------------------------------ frontend
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    if path.startswith("api/"):
        abort(404)
    full = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


# ------------------------------------------------------------------ meta
@app.get("/api/meta")
def meta():
    return ok({"industries": library.INDUSTRIES, "enums": ENUMS, "library_errors": library.LOAD_ERRORS,
               "library_processes": len(library.PROCESSES),
               "analytics_tests": [{"key": k, **v} for k, v in analytics.TESTS.items()]})


# ------------------------------------------------------------------ companies
def company_or_404(cid):
    c = db.one("SELECT * FROM companies WHERE id = ?", (cid,))
    if not c:
        abort(404, "Company not found")
    c["industries"] = services.load_json(c["industries"])
    return c


@app.get("/api/companies")
def list_companies():
    rows = db.query("SELECT * FROM companies ORDER BY name")
    for c in rows:
        c["industries"] = services.load_json(c["industries"])
        cid = c["id"]
        c["entity_count"] = db.one("SELECT COUNT(*) n FROM entities WHERE company_id = ?", (cid,))["n"]
        c["engagement_count"] = db.one("SELECT COUNT(*) n FROM engagements WHERE company_id = ?", (cid,))["n"]
        c["open_findings"] = db.one("SELECT COUNT(*) n FROM findings WHERE company_id = ? AND status NOT IN "
                                    "('Implemented','Closed','Risk Accepted')", (cid,))["n"]
    return ok(rows)


@app.post("/api/companies")
def create_company():
    b = body()
    if not (b.get("name") or "").strip():
        abort(400, "Company name is required")
    industries = [i for i in b.get("industries", []) if i in library.INDUSTRIES]
    b["industries"] = industries
    cid = db.insert("companies", b)
    entities = b.get("entities") or []
    if not entities:
        entities = [{"name": b["name"], "entity_type": "Holding" if b.get("company_type") == "Multinational Group"
                     else "Subsidiary", "country": b.get("country"), "currency": b.get("base_currency"),
                     "industry": industries[0] if len(industries) == 1 else ""}]
    created = []
    for e in entities:
        if not (e.get("name") or "").strip():
            continue
        e["company_id"] = cid
        e.setdefault("currency", b.get("base_currency"))
        e["id"] = db.insert("entities", e)
        created.append(e)
    if b.get("populate_universe", True):
        rows = []
        for e in created:
            rows.extend(services.universe_rows_for_entity(cid, e, industries))
        db.insert_many("universe", rows)
    for a in b.get("auditors") or []:
        if a.get("name"):
            a["company_id"] = cid
            db.insert("auditors", a)
    db.log(cid, "company", cid, "created", b["name"])
    return ok(company_or_404(cid))


@app.get("/api/companies/<int:cid>")
def get_company(cid):
    return ok(company_or_404(cid))


@app.put("/api/companies/<int:cid>")
def update_company(cid):
    b = body()
    if "industries" in b:
        b["industries"] = [i for i in b["industries"] if i in library.INDUSTRIES]
    db.update("companies", cid, b)
    db.log(cid, "company", cid, "updated")
    return ok(company_or_404(cid))


@app.delete("/api/companies/<int:cid>")
def delete_company(cid):
    eng_ids = [r["id"] for r in db.query("SELECT id FROM engagements WHERE company_id = ?", (cid,))]
    for eid in eng_ids:
        _delete_engagement_children(eid)
    fids = [r["id"] for r in db.query("SELECT id FROM findings WHERE company_id = ?", (cid,))]
    for fid in fids:
        db.execute("DELETE FROM followups WHERE finding_id = ?", (fid,))
    for t in ("findings", "engagements", "plans", "universe", "entities", "auditors", "attachments",
              "analytics_runs", "activity_log"):
        db.execute(f"DELETE FROM {t} WHERE company_id = ?", (cid,))
    db.delete("companies", cid)
    return ok()


@app.post("/api/companies/demo")
def create_demo():
    cid = seed.create_demo(create_engagement)
    return ok(company_or_404(cid))


@app.post("/api/companies/<int:cid>/universe/populate")
def populate_universe(cid):
    """Add library processes missing from the universe (e.g. after adding an entity or industry)."""
    company = company_or_404(cid)
    existing = {(r["entity_id"], r["process_code"]) for r in
                db.query("SELECT entity_id, process_code FROM universe WHERE company_id = ?", (cid,))}
    rows = []
    for e in db.query("SELECT * FROM entities WHERE company_id = ?", (cid,)):
        for r in services.universe_rows_for_entity(cid, e, company["industries"]):
            if (r["entity_id"], r["process_code"]) not in existing:
                rows.append(r)
    db.insert_many("universe", rows)
    return ok({"added": len(rows)})


# ------------------------------------------------------------------ generic CRUD
def _enrich(resource, rows):
    if not rows:
        return rows
    if resource in ("universe", "engagements", "findings"):
        ents = {e["id"]: e["name"] for e in db.query("SELECT id, name FROM entities")}
        for r in rows:
            r["entity_name"] = ents.get(r.get("entity_id"), "")
    if resource == "findings":
        engs = {e["id"]: e for e in db.query("SELECT id, ref, title FROM engagements")}
        for r in rows:
            r["overdue"] = services.is_overdue(r)
            e = engs.get(r.get("engagement_id"))
            r["engagement_ref"] = e["ref"] if e else ""
            r["engagement_title"] = e["title"] if e else ""
            p = library.get_process(r.get("process_code"))
            r["process_name"] = p["name"] if p else (r.get("process_code") or "")
            r["followup_count"] = 0
        counts = {x["finding_id"]: x["n"] for x in db.query(
            "SELECT finding_id, COUNT(*) n FROM followups GROUP BY finding_id")}
        for r in rows:
            r["followup_count"] = counts.get(r["id"], 0)
    if resource == "engagements":
        plans = {p["id"]: p for p in db.query("SELECT id, year, title FROM plans")}
        fc = {}
        for f in db.query("SELECT engagement_id, rating FROM findings"):
            fc.setdefault(f["engagement_id"], Counter())[f["rating"]] += 1
        pc = {}
        for p in db.query("SELECT engagement_id, status FROM procedures"):
            pc.setdefault(p["engagement_id"], Counter())[p["status"]] += 1
        hrs = {h["engagement_id"]: h["h"] for h in db.query(
            "SELECT engagement_id, SUM(hours) h FROM time_entries GROUP BY engagement_id")}
        for r in rows:
            r["process_codes"] = services.load_json(r.get("process_codes"))
            r["plan_year"] = plans.get(r.get("plan_id"), {}).get("year")
            r["findings"] = dict(fc.get(r["id"], {}))
            procs = pc.get(r["id"], Counter())
            total = sum(procs.values())
            r["procedure_total"] = total
            r["procedure_done"] = procs.get("Prepared", 0) + procs.get("Reviewed", 0)
            r["progress"] = round(r["procedure_done"] / total * 100) if total else 0
            r["actual_hours"] = round(hrs.get(r["id"], 0) or 0, 1)
    return rows


@app.get("/api/<resource>")
def list_resource(resource):
    if resource not in RESOURCES:
        abort(404)
    cols = set(db.columns(resource))
    where, params = [], []
    for k, v in request.args.items():
        if k in cols and v != "":
            where.append(f"{k} = ?")
            params.append(v)
    order = "sort, id" if resource == "procedures" else "risk_score DESC" if resource == "universe" else "id"
    sql = f"SELECT * FROM {resource}" + (f" WHERE {' AND '.join(where)}" if where else "") + f" ORDER BY {order}"
    return ok(_enrich(resource, db.query(sql, params)))


@app.get("/api/<resource>/<int:rid>")
def get_resource(resource, rid):
    if resource not in RESOURCES:
        abort(404)
    row = db.one(f"SELECT * FROM {resource} WHERE id = ?", (rid,))
    if not row:
        abort(404)
    return ok(_enrich(resource, [row])[0])


def _company_of(resource, row):
    if row.get("company_id"):
        return row["company_id"]
    if row.get("engagement_id"):
        e = db.one("SELECT company_id FROM engagements WHERE id = ?", (row["engagement_id"],))
        return e["company_id"] if e else None
    if row.get("finding_id"):
        f = db.one("SELECT company_id FROM findings WHERE id = ?", (row["finding_id"],))
        return f["company_id"] if f else None
    return None


@app.post("/api/<resource>")
def create_resource(resource):
    if resource not in RESOURCES or resource == "attachments":
        abort(404)
    b = body()
    if resource == "engagements":
        return ok(create_engagement(b))
    if resource == "universe":
        services.score_universe(b)
    if resource == "findings":
        if b.get("engagement_id"):
            e = db.one("SELECT company_id, entity_id FROM engagements WHERE id = ?", (b["engagement_id"],))
            if e:
                b.setdefault("company_id", e["company_id"])
                b.setdefault("entity_id", e["entity_id"])
        if not b.get("company_id"):
            abort(400, "company_id is required")
        if not b.get("ref"):
            b["ref"] = services.next_ref("findings", b["company_id"], "F-")
        if not (b.get("title") or "").strip():
            abort(400, "Finding title is required")
    if resource == "followups":
        b.setdefault("update_date", db.today())
        if b.get("status"):
            upd = {"status": b["status"]}
            if b["status"] in ("Implemented", "Closed"):
                upd["closed_on"] = db.today()
            db.update("findings", b["finding_id"], upd)
    if resource == "review_notes":
        b.setdefault("raised_on", db.today())
    if resource == "time_entries":
        b.setdefault("entry_date", db.today())
    rid = db.insert(resource, b)
    row = db.one(f"SELECT * FROM {resource} WHERE id = ?", (rid,))
    db.log(_company_of(resource, row), resource, rid, "created",
           row.get("title") or row.get("name") or row.get("item") or row.get("note") or "")
    return ok(_enrich(resource, [row])[0])


@app.put("/api/<resource>/<int:rid>")
def update_resource(resource, rid):
    if resource not in RESOURCES:
        abort(404)
    row = db.one(f"SELECT * FROM {resource} WHERE id = ?", (rid,))
    if not row:
        abort(404)
    b = body()
    if resource == "universe":
        merged = dict(row)
        merged.update(b)
        if "audit_frequency" not in b:
            merged["audit_frequency"] = None
        b = services.score_universe(merged)
    if resource == "findings" and b.get("status") in ("Implemented", "Closed") and not row.get("closed_on"):
        b["closed_on"] = db.today()
    if resource == "review_notes" and b.get("status") == "Cleared" and not row.get("cleared_on"):
        b["cleared_on"] = db.today()
    if resource == "pbc" and b.get("status") == "Received" and not row.get("received_on"):
        b["received_on"] = db.today()
    db.update(resource, rid, b)
    row = db.one(f"SELECT * FROM {resource} WHERE id = ?", (rid,))
    changed = ", ".join(k for k in b if k not in ("id",))[:200]
    db.log(_company_of(resource, row), resource, rid, "updated", changed)
    return ok(_enrich(resource, [row])[0])


def _delete_engagement_children(eid):
    for t in ("procedures", "pbc", "review_notes", "time_entries"):
        db.execute(f"DELETE FROM {t} WHERE engagement_id = ?", (eid,))
    for a in db.query("SELECT * FROM attachments WHERE engagement_id = ?", (eid,)):
        _remove_file(a)
    db.execute("DELETE FROM attachments WHERE engagement_id = ?", (eid,))


def _remove_file(att):
    try:
        os.remove(os.path.join(db.UPLOAD_DIR, att["stored_name"]))
    except OSError:
        pass


@app.delete("/api/<resource>/<int:rid>")
def delete_resource(resource, rid):
    if resource not in RESOURCES:
        abort(404)
    row = db.one(f"SELECT * FROM {resource} WHERE id = ?", (rid,))
    if not row:
        abort(404)
    if resource == "engagements":
        _delete_engagement_children(rid)
        for f in db.query("SELECT id FROM findings WHERE engagement_id = ?", (rid,)):
            db.execute("DELETE FROM followups WHERE finding_id = ?", (f["id"],))
        db.execute("DELETE FROM findings WHERE engagement_id = ?", (rid,))
    if resource == "findings":
        db.execute("DELETE FROM followups WHERE finding_id = ?", (rid,))
    if resource == "plans":
        db.execute("UPDATE engagements SET plan_id = NULL WHERE plan_id = ?", (rid,))
    if resource == "entities":
        db.execute("DELETE FROM universe WHERE entity_id = ?", (rid,))
    if resource == "attachments":
        _remove_file(row)
    db.delete(resource, rid)
    db.log(_company_of(resource, row), resource, rid, "deleted",
           row.get("title") or row.get("name") or row.get("filename") or "")
    return ok()


# ------------------------------------------------------------------ engagements
def create_engagement(b):
    if not (b.get("title") or "").strip():
        abort(400, "Engagement title is required")
    if not b.get("company_id"):
        abort(400, "company_id is required")
    codes = [c for c in (b.get("process_codes") or []) if library.get_process(c)]
    b["process_codes"] = codes
    if not b.get("ref"):
        year = (b.get("planned_start") or db.today())[:4]
        b["ref"] = services.next_ref("engagements", b["company_id"], f"IA-{year}-")
    if codes and not b.get("objective"):
        objs = []
        for c in codes:
            objs.extend(library.get_process(c).get("objectives", []))
        b["objective"] = "\n".join(f"- {o}" for o in objs[:10])
    if codes and not b.get("scope"):
        b["scope"] = "Processes in scope: " + "; ".join(library.get_process(c)["name"] for c in codes) + "."
    eid = db.insert("engagements", b)
    if b.get("load_library", True):
        services.procedures_from_library(eid, codes)
    if b.get("load_pbc", True):
        services.pbc_from_library(eid, codes, b.get("auditee_contact") or "")
    db.log(b["company_id"], "engagements", eid, "created", b["title"])
    return _enrich("engagements", [db.one("SELECT * FROM engagements WHERE id = ?", (eid,))])[0]


@app.get("/api/engagements/<int:eid>/full")
def engagement_full(eid):
    eng = db.one("SELECT * FROM engagements WHERE id = ?", (eid,))
    if not eng:
        abort(404)
    eng = _enrich("engagements", [eng])[0]
    data = {
        "engagement": eng,
        "procedures": db.query("SELECT * FROM procedures WHERE engagement_id = ? ORDER BY sort, id", (eid,)),
        "pbc": db.query("SELECT * FROM pbc WHERE engagement_id = ? ORDER BY id", (eid,)),
        "findings": _enrich("findings", db.query("SELECT * FROM findings WHERE engagement_id = ? ORDER BY ref", (eid,))),
        "review_notes": db.query("SELECT * FROM review_notes WHERE engagement_id = ? ORDER BY id DESC", (eid,)),
        "time_entries": db.query("SELECT * FROM time_entries WHERE engagement_id = ? ORDER BY entry_date DESC, id DESC", (eid,)),
        "attachments": db.query("SELECT * FROM attachments WHERE engagement_id = ? ORDER BY id DESC", (eid,)),
        "suggested_rating": None,
    }
    data["suggested_rating"] = services.engagement_rating(data["findings"])
    return ok(data)


@app.post("/api/engagements/<int:eid>/processes")
def add_processes(eid):
    eng = db.one("SELECT * FROM engagements WHERE id = ?", (eid,))
    if not eng:
        abort(404)
    current = services.load_json(eng["process_codes"])
    new = [c for c in body().get("process_codes", []) if c not in current and library.get_process(c)]
    services.procedures_from_library(eid, new)
    if body().get("load_pbc", True):
        services.pbc_from_library(eid, new, eng.get("auditee_contact") or "")
    db.update("engagements", eid, {"process_codes": current + new})
    db.log(eng["company_id"], "engagements", eid, "processes added", ", ".join(new))
    return ok({"added": len(new)})


@app.post("/api/engagements/<int:eid>/rating")
def compute_rating(eid):
    findings = db.query("SELECT rating FROM findings WHERE engagement_id = ?", (eid,))
    rating = services.engagement_rating(findings)
    db.update("engagements", eid, {"overall_rating": rating})
    return ok({"overall_rating": rating})


@app.post("/api/procedures/<int:pid>/signoff")
def signoff(pid):
    b = body()
    proc = db.one("SELECT * FROM procedures WHERE id = ?", (pid,))
    if not proc:
        abort(404)
    role, name = b.get("role"), (b.get("name") or "").strip()
    if role == "preparer":
        if not name:
            abort(400, "Preparer name is required")
        if proc["oe_result"] == "Not Tested" and proc["design_result"] == "Not Tested":
            abort(400, "Record a design or operating effectiveness result before signing off")
        db.update("procedures", pid, {"prepared_by": name, "prepared_on": db.today(), "status": "Prepared"})
    elif role == "reviewer":
        if not proc.get("prepared_by"):
            abort(400, "Procedure must be prepared before review sign-off")
        open_notes = db.one("SELECT COUNT(*) n FROM review_notes WHERE procedure_id = ? AND status = 'Open'", (pid,))["n"]
        if open_notes:
            abort(400, f"{open_notes} open review note(s) must be cleared before review sign-off")
        if name and name == proc["prepared_by"]:
            abort(400, "Reviewer must be different from the preparer (segregation of duties)")
        db.update("procedures", pid, {"reviewed_by": name, "reviewed_on": db.today(), "status": "Reviewed"})
    elif role == "clear":
        db.update("procedures", pid, {"prepared_by": None, "prepared_on": None, "reviewed_by": None,
                                      "reviewed_on": None, "status": "In Progress"})
    else:
        abort(400, "Unknown role")
    eng = db.one("SELECT company_id FROM engagements WHERE id = ?", (proc["engagement_id"],))
    db.log(eng["company_id"] if eng else None, "procedures", pid, f"sign-off {role}", name)
    return ok(db.one("SELECT * FROM procedures WHERE id = ?", (pid,)))


@app.post("/api/procedures/<int:pid>/finding")
def finding_from_procedure(pid):
    proc = db.one("SELECT * FROM procedures WHERE id = ?", (pid,))
    if not proc:
        abort(404)
    eng = db.one("SELECT * FROM engagements WHERE id = ?", (proc["engagement_id"],))
    rating = proc["risk_rating"] if proc["risk_rating"] in services.FINDING_RATINGS else "Medium"
    f = {
        "company_id": eng["company_id"], "engagement_id": eng["id"], "entity_id": eng["entity_id"],
        "procedure_id": pid, "ref": services.next_ref("findings", eng["company_id"], "F-"),
        "title": f"Control weakness - {proc['subprocess'] or proc['control_id']}",
        "process_code": proc["process_code"], "rating": rating,
        "category": "Control Design" if proc["design_result"] == "Ineffective" else "Operating Effectiveness",
        "condition": proc.get("testing_notes") or "", "criteria": proc.get("control") or "",
        "effect": proc.get("risk") or "", "status": "Open",
    }
    fid = db.insert("findings", f)
    db.log(eng["company_id"], "findings", fid, "created from procedure", proc["control_id"] or "")
    return ok(_enrich("findings", [db.one("SELECT * FROM findings WHERE id = ?", (fid,))])[0])


# ------------------------------------------------------------------ plans
@app.post("/api/plans/<int:plan_id>/generate")
def generate_plan(plan_id):
    plan = db.one("SELECT * FROM plans WHERE id = ?", (plan_id,))
    if not plan:
        abort(404)
    b = body()
    levels = b.get("levels") or ["High"]
    max_n = int(b.get("max_engagements") or 50)
    hours = {"High": 240, "Medium": 160, "Low": 100}
    already = {r["universe_id"] for r in db.query(
        "SELECT universe_id FROM engagements WHERE plan_id = ? AND universe_id IS NOT NULL", (plan_id,))}
    units = [u for u in db.query("SELECT u.*, e.name AS entity_name FROM universe u LEFT JOIN entities e "
                                 "ON e.id = u.entity_id WHERE u.company_id = ? ORDER BY u.risk_score DESC",
                                 (plan["company_id"],))
             if u["risk_level"] in levels and u["id"] not in already][:max_n]
    created = []
    for i, u in enumerate(units):
        q = f"Q{min(4, 1 + i * 4 // max(1, len(units)))}"
        qn = int(q[1])
        year = plan["year"] or int(db.today()[:4])
        start = f"{year}-{(qn - 1) * 3 + 1:02d}-01"
        end = f"{year}-{qn * 3:02d}-{'31' if qn in (1, 4) else '30'}"
        e = create_engagement({
            "company_id": plan["company_id"], "plan_id": plan_id, "entity_id": u["entity_id"],
            "universe_id": u["id"], "title": f"{u['process_name']} - {u.get('entity_name') or ''}".strip(" -"),
            "audit_type": "Assurance", "status": "Planned", "quarter": q,
            "planned_start": start, "planned_end": end, "budget_hours": hours.get(u["risk_level"], 160),
            "process_codes": [u["process_code"]], "period_from": f"{year - 1}-01-01", "period_to": f"{year - 1}-12-31",
            "load_library": b.get("load_library", True), "load_pbc": b.get("load_library", True),
        })
        created.append(e)
    return ok({"created": len(created)})


# ------------------------------------------------------------------ dashboard
@app.get("/api/dashboard")
def dashboard():
    cid = request.args.get("company_id", type=int)
    company_or_404(cid)
    engs = _enrich("engagements", db.query("SELECT * FROM engagements WHERE company_id = ?", (cid,)))
    findings = _enrich("findings", db.query("SELECT * FROM findings WHERE company_id = ?", (cid,)))
    uni = db.query("SELECT * FROM universe WHERE company_id = ?", (cid,))
    open_f = [f for f in findings if f["status"] not in services.CLOSED_STATUSES]
    heat = Counter(f"{u['impact']}-{u['likelihood']}" for u in uni)
    by_entity = Counter(f["entity_name"] or "Group" for f in open_f)
    by_process = Counter(f["process_name"] or "Other" for f in findings)
    today = db.today()
    upcoming = sorted([f for f in open_f if (f.get("revised_due_date") or f.get("due_date") or "") >= today],
                      key=lambda f: f.get("revised_due_date") or f.get("due_date"))[:8]
    total_budget = sum(e.get("budget_hours") or 0 for e in engs)
    total_actual = sum(e.get("actual_hours") or 0 for e in engs)
    activity = db.query("SELECT * FROM activity_log WHERE company_id = ? ORDER BY id DESC LIMIT 12", (cid,))
    done = sum(1 for e in engs if e["status"] in ("Reporting", "Closed"))
    return ok({
        "kpis": {
            "engagements": len(engs), "completed": done,
            "plan_completion": round(done / len(engs) * 100) if engs else 0,
            "findings": len(findings), "open_findings": len(open_f),
            "open_high": sum(1 for f in open_f if f["rating"] in ("Critical", "High")),
            "overdue": sum(1 for f in open_f if f["overdue"]),
            "universe": len(uni), "high_risk_units": sum(1 for u in uni if u["risk_level"] == "High"),
            "budget_hours": total_budget, "actual_hours": round(total_actual, 1),
            "implementation_rate": round(sum(1 for f in findings if f["status"] in ("Implemented", "Closed"))
                                         / len(findings) * 100) if findings else 0,
        },
        "engagement_status": Counter(e["status"] for e in engs),
        "finding_ratings": Counter(f["rating"] for f in findings),
        "open_by_rating": Counter(f["rating"] for f in open_f),
        "finding_status": Counter("Overdue" if f["overdue"] else f["status"] for f in findings),
        "heatmap": heat,
        "by_entity": by_entity.most_common(8),
        "by_process": by_process.most_common(8),
        "upcoming_actions": upcoming,
        "overdue_actions": sorted([f for f in open_f if f["overdue"]],
                                  key=lambda f: f.get("revised_due_date") or f.get("due_date"))[:8],
        "active_engagements": [e for e in engs if e["status"] in ("Planning", "Fieldwork", "Reporting")][:8],
        "activity": activity,
    })


@app.get("/api/activity")
def activity():
    cid = request.args.get("company_id", type=int)
    return ok(db.query("SELECT * FROM activity_log WHERE company_id = ? ORDER BY id DESC LIMIT 500", (cid,)))


# ------------------------------------------------------------------ library
@app.get("/api/library")
def library_list():
    return ok(library.summary(), errors=library.LOAD_ERRORS)


@app.get("/api/library/<code>")
def library_get(code):
    p = library.get_process(code)
    if not p:
        abort(404)
    return ok(p)


# ------------------------------------------------------------------ sampling
@app.post("/api/sampling/size")
def sampling_size():
    b = body()
    method = b.get("method", "frequency")
    if method == "attribute":
        n = services.attribute_sample_size(b.get("confidence", 95), b.get("tolerable_rate", 10),
                                           b.get("expected_errors", 0))
        pop = int(b.get("population") or 0)
        return ok({"sample_size": min(n, pop) if pop else n,
                   "basis": f"Attribute sampling, {b.get('confidence', 95)}% confidence, "
                            f"{b.get('tolerable_rate', 10)}% tolerable deviation, "
                            f"{b.get('expected_errors', 0)} expected deviation(s)"})
    if method == "mus":
        n, interval = services.mus_sample_size(b.get("book_value") or 0, b.get("tolerable_misstatement") or 1,
                                               b.get("confidence", 95))
        return ok({"sample_size": n, "interval": interval,
                   "basis": f"Monetary unit sampling, {b.get('confidence', 95)}% confidence, sampling interval {interval:,.2f}"})
    n = services.suggested_sample(b.get("frequency"), b.get("nature"), b.get("risk", "Medium"),
                                  int(b.get("population") or 0) or None)
    return ok({"sample_size": n, "basis": f"Control frequency guidance ({b.get('frequency')}, {b.get('nature') or 'Manual'}, "
                                          f"{b.get('risk', 'Medium')} risk)"})


@app.post("/api/sampling/select")
def sampling_select():
    b = body()
    if not b.get("population") or not b.get("size"):
        abort(400, "Population and sample size are required")
    picks, seed_used = services.random_selection(b["population"], b["size"], b.get("seed"))
    return ok({"items": picks, "seed": seed_used})


# ------------------------------------------------------------------ analytics
@app.post("/api/analytics/upload")
def analytics_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        abort(400, "No file uploaded")
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".csv", ".txt", ".xlsx", ".xlsm"):
        abort(400, "Supported formats: CSV, TXT, XLSX")
    os.makedirs(ANALYTICS_DIR, exist_ok=True)
    token = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(ANALYTICS_DIR, token)
    f.save(path)
    headers, rows = analytics.read_table(path)
    preview = [{k: (str(v) if v is not None else "") for k, v in r.items()} for r in rows[:15]]
    return ok({"token": token, "file_name": f.filename, "headers": headers, "rows": len(rows),
               "preview": preview, "mapping": analytics.guess_mapping(headers)})


@app.post("/api/analytics/run")
def analytics_run():
    b = body()
    token = os.path.basename(b.get("token") or "")
    path = os.path.join(ANALYTICS_DIR, token)
    if not token or not os.path.isfile(path):
        abort(400, "Uploaded file not found - please upload again")
    headers, rows = analytics.read_table(path)
    try:
        res = analytics.run_test(b.get("test"), headers, rows, b.get("mapping") or {}, b.get("params") or {})
    except ValueError as exc:
        abort(400, str(exc))
    rid = db.insert("analytics_runs", {
        "company_id": b.get("company_id"), "engagement_id": b.get("engagement_id") or None,
        "test": b.get("test"), "file_name": b.get("file_name"), "params": json.dumps(b.get("params") or {}),
        "total_records": len(rows), "exceptions": res["summary"].get("exceptions", 0),
        "result": json.dumps(res, default=str), "run_on": db.now()})
    db.log(b.get("company_id"), "analytics", rid, "run", f"{b.get('test')} on {b.get('file_name')}")
    res["run_id"] = rid
    res["exceptions_preview"] = res["exceptions"][:500]
    res["exceptions_total"] = len(res["exceptions"])
    del res["exceptions"]
    return ok(res)


@app.get("/api/analytics/runs")
def analytics_runs():
    cid = request.args.get("company_id", type=int)
    rows = db.query("SELECT id, company_id, engagement_id, test, file_name, params, total_records, exceptions, run_on "
                    "FROM analytics_runs WHERE company_id = ? ORDER BY id DESC", (cid,))
    return ok(rows)


@app.get("/api/analytics/runs/<int:rid>/export")
def analytics_export(rid):
    run = db.one("SELECT * FROM analytics_runs WHERE id = ?", (rid,))
    if not run:
        abort(404)
    return send_file(reports.analytics_excel(run), as_attachment=True)


@app.delete("/api/analytics/runs/<int:rid>")
def analytics_delete(rid):
    db.delete("analytics_runs", rid)
    return ok()


# ------------------------------------------------------------------ attachments
@app.post("/api/attachments/upload")
def upload_attachment():
    f = request.files.get("file")
    if not f or not f.filename:
        abort(400, "No file uploaded")
    name = secure_filename(f.filename) or "file"
    stored = f"{uuid.uuid4().hex}_{name}"
    path = os.path.join(db.UPLOAD_DIR, stored)
    f.save(path)
    form = request.form
    row = {k: (form.get(k) or None) for k in ("company_id", "engagement_id", "procedure_id", "finding_id", "description")}
    row.update({"filename": f.filename, "stored_name": stored, "size": os.path.getsize(path), "uploaded_on": db.now()})
    aid = db.insert("attachments", row)
    db.log(row.get("company_id"), "attachments", aid, "uploaded", f.filename)
    return ok(db.one("SELECT * FROM attachments WHERE id = ?", (aid,)))


@app.get("/api/attachments/<int:aid>/download")
def download_attachment(aid):
    a = db.one("SELECT * FROM attachments WHERE id = ?", (aid,))
    if not a:
        abort(404)
    return send_file(os.path.join(db.UPLOAD_DIR, a["stored_name"]), as_attachment=True, download_name=a["filename"])


# ------------------------------------------------------------------ reports
@app.get("/api/reports/engagement/<int:eid>/docx")
def report_engagement(eid):
    return send_file(reports.engagement_report(eid), as_attachment=True)


@app.get("/api/reports/engagement/<int:eid>/racm")
def report_racm(eid):
    return send_file(reports.racm_excel(eid), as_attachment=True)


@app.get("/api/reports/board/<int:cid>/pptx")
def report_board(cid):
    year = request.args.get("year", type=int)
    return send_file(reports.board_presentation(cid, year), as_attachment=True)


@app.get("/api/reports/plan/<int:cid>/<int:plan_id>/docx")
def report_plan(cid, plan_id):
    return send_file(reports.plan_document(cid, plan_id), as_attachment=True)


@app.get("/api/reports/findings/<int:cid>/xlsx")
def report_findings(cid):
    return send_file(reports.findings_excel(cid), as_attachment=True)


@app.get("/api/reports/universe/<int:cid>/xlsx")
def report_universe(cid):
    return send_file(reports.universe_excel(cid), as_attachment=True)


def main():
    db.init_db()
    port = int(os.environ.get("AUDIT_APP_PORT") or os.environ.get("PORT") or "5050")
    url = f"http://127.0.0.1:{port}"
    print("=" * 60)
    print("  AuditPro - Internal Audit Management System")
    print(f"  Running at {url}   (press Ctrl+C to stop)")
    if library.LOAD_ERRORS:
        print("  WARNING - library load errors:", library.LOAD_ERRORS)
    print(f"  Procedure library: {len(library.PROCESSES)} processes loaded")
    print("=" * 60)
    if os.environ.get("AUDIT_APP_NO_BROWSER") != "1":
        Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
