"""Demo data: a fictional multinational group to explore the application."""
import random
from datetime import date, timedelta

import db
import library
import services


def _d(days):
    return (date.today() + timedelta(days=days)).isoformat()


def create_demo(create_engagement):
    """create_engagement is passed in from app.py to avoid a circular import."""
    rng = random.Random(42)
    cid = db.insert("companies", {
        "name": "Crescent Horizon Group (Demo)", "short_code": "CHG", "company_type": "Multinational Group",
        "industries": library.INDUSTRIES, "country": "United Arab Emirates", "base_currency": "AED",
        "fiscal_year_end": "31-Dec", "head_of_audit": "Head of Internal Audit",
        "audit_committee_chair": "Audit Committee Chair", "address": "Dubai, United Arab Emirates",
    })
    entities = [
        ("Crescent Horizon Holding LLC", "Holding", "United Arab Emirates", "AED", ""),
        ("Crescent Home Retail LLC", "Subsidiary", "United Arab Emirates", "AED", "Home Retail"),
        ("Crescent Home Retail KSA", "Subsidiary", "Saudi Arabia", "SAR", "Home Retail"),
        ("Crescent Online FZ-LLC", "Subsidiary", "United Arab Emirates", "AED", "E-commerce"),
        ("Crescent Building Materials Trading LLC", "Subsidiary", "United Arab Emirates", "AED", "Building Material Trading"),
        ("Crescent Building Materials Oman", "Branch", "Oman", "OMR", "Building Material Trading"),
        ("Crescent Properties Development LLC", "Subsidiary", "United Arab Emirates", "AED", "Real Estate Developer"),
    ]
    ent_rows = []
    holding_id = None
    for name, etype, country, cur, ind in entities:
        e = {"company_id": cid, "name": name, "entity_type": etype, "country": country, "currency": cur,
             "industry": ind, "parent_id": holding_id, "ownership_pct": 100}
        e["id"] = db.insert("entities", e)
        holding_id = holding_id or e["id"]
        ent_rows.append(e)
    # holding entity only carries the common processes
    uni = []
    for e in ent_rows:
        inds = [e["industry"]] if e["industry"] else []
        for r in services.universe_rows_for_entity(cid, e, inds):
            for k in services.RISK_WEIGHTS:
                r[k] = max(1, min(5, r[k] + rng.choice([-1, 0, 0, 1])))
            uni.append(services.score_universe(r))
    db.insert_many("universe", uni)

    for name, role, desig in [("Audit Manager A", "Audit Manager", "CIA, ACCA"),
                              ("Senior Auditor B", "Senior Auditor", "CA"),
                              ("Auditor C", "Auditor", "CPA"),
                              ("IT Auditor D", "IT Auditor", "CISA")]:
        db.insert("auditors", {"company_id": cid, "name": name, "role": role, "designation": role,
                               "certifications": desig})

    year = date.today().year
    plan_id = db.insert("plans", {"company_id": cid, "year": year, "title": f"Risk-Based Audit Plan {year}",
                                  "status": "Approved", "available_hours": 4800,
                                  "approved_by": "Audit Committee", "approved_on": f"{year}-01-15"})
    # pick one high-scoring industry process per operating entity plus a group-level one
    picks = []
    for e in ent_rows:
        units = sorted([u for u in db.query("SELECT * FROM universe WHERE entity_id = ?", (e["id"],))
                        if library.get_process(u["process_code"])],
                       key=lambda u: (u["industry"] == "Common", -u["risk_score"]))
        if units:
            picks.append((e, units[0]))
    statuses = ["Closed", "Reporting", "Fieldwork", "Fieldwork", "Planning", "Planned", "Planned"]
    for i, (e, u) in enumerate(picks):
        q = i * 4 // len(picks) + 1
        status = statuses[i % len(statuses)]
        eng = create_engagement({
            "company_id": cid, "plan_id": plan_id, "entity_id": e["id"], "universe_id": u["id"],
            "title": f"{u['process_name']} Review - {e['name']}", "audit_type": "Assurance",
            "status": status, "quarter": f"Q{q}", "period_from": f"{year - 1}-01-01",
            "period_to": f"{year - 1}-12-31", "planned_start": f"{year}-{(q - 1) * 3 + 1:02d}-05",
            "planned_end": f"{year}-{(q - 1) * 3 + 2:02d}-25", "lead_auditor": "Audit Manager A",
            "reviewer": "Head of Internal Audit", "team": "Senior Auditor B, Auditor C",
            "auditee_contact": f"Process Owner - {e['name']}", "budget_hours": 240 if u["risk_level"] == "High" else 160,
            "process_codes": [u["process_code"]],
        })
        _simulate(eng, status, rng)
    db.log(cid, "company", cid, "created", "Demo company generated")
    return cid


def _simulate(eng, status, rng):
    if status in ("Planned",):
        return
    procs = db.query("SELECT * FROM procedures WHERE engagement_id = ? ORDER BY sort", (eng["id"],))
    share = {"Planning": 0.0, "Fieldwork": 0.5, "Reporting": 1.0, "Closed": 1.0}[status]
    tested = procs[:int(len(procs) * share)]
    for p in tested:
        res = rng.choices(["Effective", "Partially Effective", "Ineffective"], [6, 2, 1])[0]
        upd = {"design_result": "Effective", "oe_result": res, "population": rng.randint(80, 2000),
               "testing_notes": f"Sample of {p['sample_size']} items selected randomly and tested against the control attributes. "
                                + ("No exceptions noted." if res == "Effective" else
                                   f"{rng.randint(1, 4)} exception(s) noted - see finding."),
               "conclusion": "Control operating effectively." if res == "Effective" else "Control deficiency identified.",
               "wp_ref": f"WP-{p['sort']:02d}", "status": "Reviewed" if status != "Fieldwork" else "Prepared",
               "prepared_by": "Senior Auditor B", "prepared_on": _d(-40)}
        if upd["status"] == "Reviewed":
            upd.update({"reviewed_by": "Audit Manager A", "reviewed_on": _d(-30)})
        db.update("procedures", p["id"], upd)
        if res != "Effective":
            rating = rng.choice(["High", "Medium", "Medium", "Low"] if res == "Partially Effective"
                                else ["Critical", "High", "High", "Medium"])
            due = _d(rng.choice([-120, -45, -10, 20, 60, 90]))
            fstatus = rng.choice(["Open", "In Progress", "Implemented"]) if status == "Closed" else "Open"
            fid = db.insert("findings", {
                "company_id": eng["company_id"], "engagement_id": eng["id"], "entity_id": eng["entity_id"],
                "procedure_id": p["id"], "ref": services.next_ref("findings", eng["company_id"], "F-"),
                "title": f"Weakness in {p['subprocess'] or 'control'} ({p['control_id']})",
                "process_code": p["process_code"], "rating": rating, "category": "Operating Effectiveness",
                "root_cause_category": rng.choice(["Process / Policy gap", "Oversight / Monitoring", "People / Training"]),
                "condition": f"During testing of {p['control_id']}, exceptions were noted where the control was not performed as designed.",
                "criteria": p["control"], "cause": "Lack of periodic supervisory review and unclear ownership of the control.",
                "effect": p["risk"], "recommendation": "Management should reinforce the control, assign a clear owner and "
                                                       "implement a monthly monitoring review with documented evidence.",
                "mgmt_response": "Agreed." if status in ("Reporting", "Closed") else "",
                "action_plan": "Control owner to be designated and monitoring checklist implemented." if status in ("Reporting", "Closed") else "",
                "owner": "Finance Manager", "due_date": due, "status": fstatus,
                "closed_on": db.today() if fstatus == "Implemented" else None,
            })
            if fstatus != "Open":
                db.insert("followups", {"finding_id": fid, "update_date": _d(-5), "status": fstatus,
                                        "update_text": "Management provided evidence of progress; validated by IA.",
                                        "updated_by": "Auditor C"})
    if tested:
        for ph, hrs in (("Planning", 24), ("Fieldwork", 80 * share + 10), ("Reporting", 20 if share == 1 else 0)):
            if hrs:
                db.insert("time_entries", {"engagement_id": eng["id"], "auditor": "Senior Auditor B",
                                           "entry_date": _d(-35), "hours": hrs, "phase": ph,
                                           "description": f"{ph} activities"})
    if status in ("Reporting", "Closed"):
        findings = db.query("SELECT rating FROM findings WHERE engagement_id = ?", (eng["id"],))
        db.update("engagements", eng["id"], {"overall_rating": services.engagement_rating(findings),
                                             "report_date": _d(-20)})
    for item in db.query("SELECT id FROM pbc WHERE engagement_id = ?", (eng["id"],)):
        db.update("pbc", item["id"], {"status": "Received" if share >= 0.5 else "Requested",
                                      "received_on": _d(-45) if share >= 0.5 else None, "due_on": _d(-50)})
