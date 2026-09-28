"""
Monthly monitor: refresh data, run the LookThrough policy checks, and push the result to n8n.

    python bridge/monitor_push.py [--refresh] [--dry-run]

  --refresh   rebuild the dataset from the internet first (prices, NAVs; AMC files already applied)
  --dry-run   build and validate the payload, print it, send nothing

The payload is built only from the MCP server's tool outputs, i.e. the reconciled reference
engine; n8n receives figures and never recalculates them. Configuration comes from the
environment or a local .env file (never committed):

    LOOKTHROUGH_N8N_WEBHOOK=https://<instance>.app.n8n.cloud/webhook/lookthrough-monitor
    LOOKTHROUGH_N8N_TOKEN=<the value stored in the n8n "LookThrough monitor token" credential>
    LOOKTHROUGH_N8N_HEADER=X-LookThrough-Token            (optional; must match the credential's header name)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "lookthrough.monitor/1"
STATUSES = {"BREACH", "within limit", "NOT COMPUTABLE"}


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def build_payload():
    sys.path.insert(0, str(ROOT / "mcp_server"))
    import lookthrough_mcp as S  # imports the reconciled engine on the current dataset

    ps = S.portfolio_summary("ALL")["data"]
    lt = S.look_through_exposure("ALL", 1)["data"]
    pc = S.policy_check("ALL")["data"]
    pv = S.data_provenance()["data"]
    top = lt["top_exposures"][0] if lt["top_exposures"] else {}
    body = {
        "schema": SCHEMA,
        "as_on": S.AS_ON,
        "built_at": pv.get("dataset_built_at"),
        "sent_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {"value_cr": ps["value_cr"], "xirr_pct": ps["xirr_pct"],
                    "not_looked_through_cr": ps["look_through"]["not_looked_through_cr"]},
        "exposure": {"largest": top.get("company"), "largest_pct": top.get("pct_of_equity")},
        "policy": {"tests": pc["tests"], "breaches": pc["breaches"], "not_computable": pc["not_computable"]},
        "provenance": {"warnings": pv["warnings"], "schemes_without_disclosure": pv["schemes_without_disclosure"],
                       "amc_files": len(pv["amc_files"])},
    }
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    body["payload_sha256"] = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    return body


def validate(p):
    """The same rules the n8n 'Validate Payload' node applies, so a bad payload fails here first."""
    errs = []
    if p.get("schema") != SCHEMA:
        errs.append("schema")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(p.get("as_on"))):
        errs.append("as_on")
    v = p.get("summary", {}).get("value_cr")
    if not isinstance(v, (int, float)) or v != v:
        errs.append("summary.value_cr")
    tests = p.get("policy", {}).get("tests")
    if not tests or any(not isinstance(t.get("test"), str) or t.get("status") not in STATUSES for t in tests):
        errs.append("policy.tests")
    if len(p.get("payload_sha256", "")) != 64:
        errs.append("payload_sha256")
    return errs


def post(p):
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass
    url, token = os.environ.get("LOOKTHROUGH_N8N_WEBHOOK"), os.environ.get("LOOKTHROUGH_N8N_TOKEN")
    header = os.environ.get("LOOKTHROUGH_N8N_HEADER", "X-LookThrough-Token")
    if not url or not token:
        raise SystemExit("Set LOOKTHROUGH_N8N_WEBHOOK and LOOKTHROUGH_N8N_TOKEN in .env (see the docstring).")
    if not url.startswith("https://"):
        raise SystemExit("The webhook URL must be https.")
    req = urllib.request.Request(url, data=json.dumps(p).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", header: token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main(argv):
    load_env()
    if "--refresh" in argv:
        print("Refreshing market data ...")
        subprocess.run([sys.executable, str(ROOT / "bridge" / "lookthrough_bridge.py"), "refresh"], check=True)
    p = build_payload()
    errs = validate(p)
    if errs:
        raise SystemExit(f"Payload failed validation: {errs}")
    print(f"as_on {p['as_on']} | value Rs {p['summary']['value_cr']} cr | breaches {p['policy']['breaches']} | "
          f"not computable {p['policy']['not_computable']} | sha256 {p['payload_sha256'][:16]}...")
    if "--dry-run" in argv:
        print(json.dumps(p, indent=1, ensure_ascii=False))
        return 0
    status, text = post(p)
    print(f"n8n responded {status}: {text[:300]}")
    log = ROOT / "logs" / "monitor_push.jsonl"
    log.parent.mkdir(exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "as_on": p["as_on"], "status": status,
                            "sha256": p["payload_sha256"], "response": text[:300]}) + "\n")
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
