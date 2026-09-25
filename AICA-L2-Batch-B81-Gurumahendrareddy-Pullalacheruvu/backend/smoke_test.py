import json, sys
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)
fails = []

r = c.post("/api/auth/login", json={"email":"guru@northwindrobotics.in","password":"cashrunway"})
assert r.status_code == 200, r.text
tok = r.json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
print("  OK   login ->", r.json()["user"]["name"], "|", r.json()["user"]["role"])

# unauthenticated must be refused
assert c.get("/api/today").status_code == 401
print("  OK   unauthenticated request refused")

GETS = ["/api/health","/api/entities","/api/top-strip","/api/definitions","/api/activity",
        "/api/today","/api/runway-burn","/api/liquidity","/api/money-in","/api/money-out",
        "/api/cash-calendar","/api/plan-vs-actual","/api/capital-debt","/api/scenarios",
        "/api/alerts","/api/alerts/rules","/api/board-packs","/api/manual-entries",
        "/api/setup/data-sources","/api/setup/users","/api/setup/settings"]
for p in GETS:
    r = c.get(p, headers=H)
    if r.status_code != 200:
        fails.append((p, r.status_code, r.text[:200])); print(f"  FAIL {p} -> {r.status_code}")
    else:
        print(f"  OK   {p}  ({len(r.content):,} bytes)")

# traces
tr = [("bank_accounts",{}),("burn_entries",{"category":"People","months":3}),
      ("invoices",{"bucket":"90+"}),("ratio",{"key":"days_cash"}),
      ("health_components",{}),("runway_basis",{})]
for kind, extra in tr:
    r = c.get("/api/trace", headers=H, params={"kind":kind, **extra})
    ok = r.status_code == 200
    if not ok: fails.append((f"trace:{kind}", r.status_code, r.text[:200]))
    print(f"  {'OK  ' if ok else 'FAIL'} trace/{kind}"
          + (f"  {r.json().get('count','')} rows" if ok else f" -> {r.status_code}"))

# writes
r = c.post("/api/scenarios/evaluate", headers=H, json={"collections_pct_of_plan":80,"hiring":"freeze"})
print(f"  {'OK  ' if r.status_code==200 else 'FAIL'} scenarios/evaluate ->",
      r.json().get("verdict"), r.json().get("runway_months"))
if r.status_code!=200: fails.append(("evaluate",r.status_code,r.text[:200]))

r = c.post("/api/alerts/run?dry_run=true", headers=H)
if r.status_code==200:
    d=r.json(); print(f"  OK   alerts/run dry -> {len(d['fired'])} would fire, {len(d['suppressed'])} suppressed")
    for f in d["fired"][:6]: print("        •", f["title"][:70])
else:
    fails.append(("alerts/run",r.status_code,r.text[:300])); print("  FAIL alerts/run", r.status_code, r.text[:200])

r = c.get("/api/setup/plan/template", headers=H)
print(f"  {'OK  ' if r.status_code==200 else 'FAIL'} plan template ({len(r.content):,} bytes xlsx)")
if r.status_code!=200: fails.append(("template",r.status_code,""))

# statutory earmark write + activity log
due = c.get("/api/money-out", headers=H).json()["statutory"]["rows"]
gap_row = next(x for x in due if x["gap"]>0)
r = c.patch(f"/api/statutory/{gap_row['id']}", headers=H, json={"earmarked_amount": gap_row["amount"]})
print(f"  {'OK  ' if r.status_code==200 else 'FAIL'} earmark statutory -> funded={r.json().get('funded')}")
if r.status_code!=200: fails.append(("earmark",r.status_code,r.text[:200]))
act = c.get("/api/activity", headers=H).json()
print("        latest activity:", act[0]["summary"][:80])

# board pack generate + read back
r = c.post("/api/board-packs", headers=H, json={"title":"September board pack","scenario_ids":[1,3]})
if r.status_code==200:
    pid=r.json()["id"]; p=c.get(f"/api/board-packs/{pid}", headers=H).json()
    print(f"  OK   board pack #{pid} generated, {len(p['sections'])} sections, "
          f"runway stated {p['runway_stated']:.1f} mo, snapshot frozen")
else:
    fails.append(("boardpack",r.status_code,r.text[:300])); print("  FAIL board pack", r.text[:200])

# read-only role must be blocked from writing
r = c.post("/api/auth/login", json={"email":"rohan@northstarventures.in","password":"cashrunway"})
BH = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = c.post("/api/scenarios", headers=BH, json={"name":"x","levers":{}})
print(f"  {'OK  ' if r.status_code==403 else 'FAIL'} board read-only blocked from writing ({r.status_code})")
if r.status_code!=403: fails.append(("rbac",r.status_code,r.text[:200]))
r = c.get("/api/today", headers=BH)
print(f"  {'OK  ' if r.status_code==200 else 'FAIL'} board read-only can still read ({r.status_code})")

# ---------------------------------------------------------------------------
# Board visibility. Two properties, and the second is the one that matters:
# detail is hidden, and the figures are IDENTICAL. A board pack that disagrees
# with the CFO's screen destroys the only thing this tool is for.
# ---------------------------------------------------------------------------
REAL_NAMES = ["Bharat Metro", "Sterling Cement", "Aurora Pharma", "Vidyut Grid",
              "Coastal Logistics", "Sensedge", "Prestige Office", "Kanoria",
              "Trilok", "Meridian Media"]
SCREENS = ["/api/today", "/api/money-in", "/api/money-out", "/api/alerts",
           "/api/cash-calendar", "/api/runway-burn", "/api/liquidity",
           "/api/plan-vs-actual", "/api/capital-debt"]

leaked = []
for ep in SCREENS:
    body = c.get(ep, headers=BH).text
    leaked += [f"{ep}: {n}" for n in REAL_NAMES if n in body]
print(f"  {'OK  ' if not leaked else 'FAIL'} no counterparty name reaches the board "
      f"across {len(SCREENS)} screens, in fields or in prose")
if leaked:
    fails.append(("board-mask-leak", leaked[:6]))

cfo_five = c.get("/api/today", headers=H).json()["five_numbers"]
brd_five = c.get("/api/today", headers=BH).json()["five_numbers"]
same = [(x.get("label"), x.get("display"), y.get("display"))
        for x, y in zip(cfo_five, brd_five) if x.get("display") != y.get("display")]
print(f"  {'OK  ' if not same else 'FAIL'} every headline figure identical for the "
      f"board and the CFO")
if same:
    fails.append(("board-figures-differ", same))

r = c.get("/api/activity", headers=BH)
ok = r.status_code == 403 and "restricted" in r.text
print(f"  {'OK  ' if ok else 'FAIL'} a withheld screen says so rather than showing "
      f"an empty page ({r.status_code})")
if not ok:
    fails.append(("board-blocked-endpoint", r.status_code))

# ---------------------------------------------------------------------------
# Set-up workbook: the template, the worked example, and the row-level report.
# ---------------------------------------------------------------------------
from app.services import setupimport                                  # noqa: E402
from app.seed.exampledata import example_rows                         # noqa: E402

book = setupimport.build_template(example_rows())
rep = setupimport.validate(book)
ok = rep["rejected"] == 0 and rep["accepted"] > 50
print(f"  {'OK  ' if ok else 'FAIL'} the worked example validates against its own "
      f"template ({rep['accepted']} rows, {rep['rejected']} rejected)")
if not ok:
    fails.append(("example-workbook", rep["errors"][:4]))

print()
print("FAILURES:", len(fails))
for f in fails: print("  ", f)
sys.exit(1 if fails else 0)
