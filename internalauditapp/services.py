"""Business logic: risk scoring, sampling, ratings and library-driven setup."""
import json
import math
import random

import db
import library

RISK_WEIGHTS = {
    "f_financial": 0.25,
    "f_fraud": 0.20,
    "f_regulatory": 0.15,
    "f_complexity": 0.15,
    "f_change": 0.10,
    "f_control_env": 0.15,
}

FINDING_RATINGS = ["Critical", "High", "Medium", "Low"]
CLOSED_STATUSES = ("Implemented", "Closed", "Risk Accepted")

# Minimum sample sizes for tests of operating effectiveness of manual controls
# (common practice in IIA / Big-4 methodologies).
FREQUENCY_SAMPLES = {
    "Annual": (1, 1),
    "Quarterly": (2, 2),
    "Monthly": (2, 5),
    "Weekly": (5, 15),
    "Daily": (20, 40),
    "Multiple times a day": (25, 60),
}


def _int(v, default=3):
    try:
        return max(1, min(5, int(float(v))))
    except (TypeError, ValueError):
        return default


def score_universe(row):
    """Compute weighted inherent risk score (0-100), impact, likelihood and level."""
    f = {k: _int(row.get(k)) for k in RISK_WEIGHTS}
    score = sum(f[k] * w for k, w in RISK_WEIGHTS.items()) / 5 * 100
    impact = round((f["f_financial"] + f["f_regulatory"] + f["f_fraud"]) / 3)
    likelihood = round((f["f_complexity"] + f["f_change"] + f["f_control_env"]) / 3)
    if score >= 80:
        level, freq = "High", "Annual"
    elif score >= 60:
        level, freq = "Medium", "Every 2 years"
    else:
        level, freq = "Low", "Every 3 years"
    row.update(f)
    row.update({"risk_score": round(score, 1), "impact": impact, "likelihood": likelihood,
                "risk_level": level})
    if not row.get("audit_frequency"):
        row["audit_frequency"] = freq
    return row


def universe_rows_for_entity(company_id, entity, industries):
    rows = []
    inds = [entity["industry"]] if entity.get("industry") in library.INDUSTRIES else industries
    for p in library.processes_for_industries(inds):
        d = p.get("default_risk", {})
        imp, lik = _int(d.get("impact")), _int(d.get("likelihood"))
        fraud = max(imp, lik) if any(i.get("fraud_risk") for i in p.get("items", [])) else lik
        row = {
            "company_id": company_id, "entity_id": entity["id"], "process_code": p["code"],
            "process_name": p["name"], "industry": p["industry"],
            "f_financial": imp, "f_fraud": fraud, "f_regulatory": imp,
            "f_complexity": lik, "f_change": 3, "f_control_env": lik,
        }
        rows.append(score_universe(row))
    return rows


def procedures_from_library(engagement_id, process_codes):
    rows, sort = [], 0
    for code in process_codes:
        p = library.get_process(code)
        if not p:
            continue
        for it in p.get("items", []):
            sort += 1
            rows.append({
                "engagement_id": engagement_id, "process_code": code,
                "subprocess": it.get("subprocess"), "risk_id": it.get("risk_id"),
                "risk": it.get("risk"), "risk_rating": it.get("risk_rating"),
                "assertion": it.get("assertion"), "control_id": it.get("control_id"),
                "control": it.get("control"), "control_type": it.get("control_type"),
                "control_nature": it.get("control_nature"), "frequency": it.get("frequency"),
                "key_control": 1 if it.get("key_control") else 0,
                "fraud_risk": 1 if it.get("fraud_risk") else 0,
                "steps": "\n".join(it.get("procedures", [])),
                "sample_size": suggested_sample(it.get("frequency"), it.get("control_nature"),
                                                it.get("risk_rating")),
                "sample_method": "Random",
                "status": "Not Started", "design_result": "Not Tested", "oe_result": "Not Tested",
                "sort": sort,
            })
    db.insert_many("procedures", rows)
    return len(rows)


def pbc_from_library(engagement_id, process_codes, requested_from=""):
    rows = []
    for code in process_codes:
        p = library.get_process(code)
        if not p:
            continue
        for item in p.get("pbc", []):
            rows.append({"engagement_id": engagement_id, "item": item, "process_code": code,
                         "requested_from": requested_from, "requested_on": db.today(),
                         "status": "Requested"})
    db.insert_many("pbc", rows)
    return len(rows)


def suggested_sample(frequency, nature=None, risk="Medium", population=None):
    if nature == "Automated":
        return 1
    if frequency in FREQUENCY_SAMPLES:
        lo, hi = FREQUENCY_SAMPLES[frequency]
        n = hi if risk == "High" else lo if risk == "Low" else round((lo + hi) / 2)
    else:  # event-driven / transactional
        pop = population or 0
        if pop and pop <= 10:
            n = min(pop, 3)
        elif pop and pop <= 50:
            n = 5
        elif pop and pop <= 250:
            n = 15
        else:
            n = 25 if risk != "High" else 40
    if population:
        n = min(n, int(population))
    return int(n)


def attribute_sample_size(confidence=95, tolerable_rate=10, expected_errors=0):
    """Attribute sampling with Poisson approximation (zero or few expected deviations)."""
    factors = {  # confidence: reliability factors for 0..3 expected deviations
        90: [2.31, 3.89, 5.33, 6.69],
        95: [3.00, 4.75, 6.30, 7.76],
        99: [4.61, 6.64, 8.41, 10.05],
    }
    conf = min(factors, key=lambda c: abs(c - float(confidence)))
    e = max(0, min(3, int(expected_errors)))
    rate = max(0.5, float(tolerable_rate)) / 100
    return int(math.ceil(factors[conf][e] / rate))


def mus_sample_size(book_value, tolerable_misstatement, confidence=95):
    rf = {90: 2.31, 95: 3.0, 99: 4.61}
    conf = min(rf, key=lambda c: abs(c - float(confidence)))
    tm = float(tolerable_misstatement)
    if tm <= 0:
        return 0, 0
    n = int(math.ceil(float(book_value) * rf[conf] / tm))
    interval = float(book_value) / n if n else 0
    return n, round(interval, 2)


def random_selection(population, size, seed=None):
    seed = int(seed) if seed not in (None, "") else random.randint(1000, 999999)
    rng = random.Random(seed)
    population = int(population)
    size = min(int(size), population)
    picks = sorted(rng.sample(range(1, population + 1), size))
    return picks, seed


def engagement_rating(findings):
    counts = {r: 0 for r in FINDING_RATINGS}
    for f in findings:
        if f.get("rating") in counts:
            counts[f["rating"]] += 1
    if counts["Critical"] or counts["High"] >= 3:
        return "Unsatisfactory"
    if counts["High"]:
        return "Needs Significant Improvement"
    if counts["Medium"]:
        return "Needs Improvement"
    return "Satisfactory"


def is_overdue(f):
    due = f.get("revised_due_date") or f.get("due_date")
    return bool(due) and f.get("status") not in CLOSED_STATUSES and due < db.today()


def next_ref(table, company_id, prefix, column="ref"):
    rows = db.query(f"SELECT {column} FROM {table} WHERE company_id = ? AND {column} LIKE ?",
                    (company_id, f"{prefix}%"))
    nums = []
    for r in rows:
        tail = (r[column] or "")[len(prefix):]
        if tail.isdigit():
            nums.append(int(tail))
    return f"{prefix}{(max(nums) + 1) if nums else 1:03d}"


def load_json(v, default=None):
    try:
        return json.loads(v) if v else (default if default is not None else [])
    except (TypeError, ValueError):
        return default if default is not None else []
