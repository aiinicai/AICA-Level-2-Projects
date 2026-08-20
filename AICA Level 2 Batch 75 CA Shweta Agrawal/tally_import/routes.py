"""
Tally Multi-Source Import — Tools module for the BNPSY Office Dashboard.

Stages Bank Statement, Journal Entry, GSTR-2B, and GSTR-1 rows and posts them
to Tally Prime as vouchers only after explicit approval in the React staging
grid. Both reads (ledger list, duplicate-check voucher history) and writes
(voucher posting) go through Tally's XML/HTTP Gateway (default localhost:9000)
— nothing here talks to the separate Tally Prime MCP connector, since that
only exists inside a Claude Code session, not a server process.

The API is intentionally stateless: the browser holds the staging rows as a
JS array and POSTs the whole array back for each operation (resolve/dupcheck/
post). This avoids a server-side session store, at the cost of re-sending the
staging table on every call — fine at the row counts this tool sees in
practice (single-digit-thousands per run at most).
"""
from __future__ import annotations

import datetime as dt
import io
import json
import uuid

import pandas as pd
from flask import Blueprint, request, jsonify, session, send_file

from . import mapping as map_store
from . import bank_rules
from . import classify
from . import masters_xml as mx
from . import pdf_bank
from . import voucher_xml as vx
from .gateway import TallyClient, TallyConnectionError, TallyGatewayError
from .parsers import bank, journal, gstr2b, gstr1
from .parsers.common import new_row

tally_bp = Blueprint("tally_import", __name__, url_prefix="/api/tools/tally")

BANK_GROUPS = {"bank accounts", "bank occ a/c", "cash-in-hand"}


@tally_bp.before_request
def _require_login():
    """Standalone build: this tool has no login system of its own -- if you
    deploy it somewhere other than your own machine, put it behind a reverse
    proxy with auth (or add one here) before exposing it on a network."""
    pass


def _client() -> TallyClient:
    url = request.args.get("gateway_url") or (request.get_json(silent=True) or {}).get("gateway_url") or "http://localhost:9000"
    return TallyClient(url=url)


def _row_to_json(row: dict) -> dict:
    out = dict(row)
    if isinstance(out.get("date"), (dt.date, dt.datetime)):
        out["date"] = out["date"].isoformat()
    return out


def _row_from_json(row: dict) -> dict:
    out = dict(row)
    if out.get("date"):
        try:
            out["date"] = dt.date.fromisoformat(out["date"][:10])
        except (ValueError, TypeError):
            pass
    return out


def _read_upload(f) -> pd.DataFrame:
    name = f.filename.lower()
    if name.endswith(".csv"):
        return pd.read_csv(f)
    if name.endswith(".xls"):
        return pd.read_excel(f, engine="xlrd")
    return pd.read_excel(f, engine="openpyxl")


def _excel_engine(filename: str) -> str:
    return "xlrd" if filename.lower().endswith(".xls") else "openpyxl"


# ── connection ────────────────────────────────────────────────────────────────

@tally_bp.route("/connection", methods=["POST"])
def connection():
    body = request.get_json(silent=True) or {}
    client = TallyClient(url=body.get("gateway_url") or "http://localhost:9000")
    ok, msg = client.check_connection()
    return jsonify({"ok": ok, "message": msg})


@tally_bp.route("/ledgers", methods=["POST"])
def ledgers():
    body = request.get_json(silent=True) or {}
    client = TallyClient(url=body.get("gateway_url") or "http://localhost:9000")
    try:
        led = client.list_ledgers()
        groups = client.list_groups()
    except (TallyConnectionError, TallyGatewayError) as e:
        return jsonify({"ok": False, "error": str(e)}), 502
    led = classify.classify_ledgers(led, groups)
    bank_names = [l["name"] for l in led if l["parent"].strip().lower() in BANK_GROUPS]
    expense_ledgers = classify.expense_side_ledgers(led)
    return jsonify({"ok": True, "ledgers": led, "bank_ledger_names": bank_names, "expense_ledgers": expense_ledgers})


REQUIRED_VOUCHER_TYPES = ["Indirect Expense", "Capital Asset"]  # custom types, base Purchase

CATEGORY_TO_GROUP = {
    "Purchase": "Purchase Accounts",
    "Direct Expense": "Direct Expenses",
    "Indirect Expense": "Indirect Expenses",
    "Capital Asset": "Fixed Assets",
}


def _missing_items(client, body):
    """Fetches current Tally state and returns everything this run needs that
    isn't there yet, as a flat list of {'kind', 'name', 'parent', 'gstin'?, 'state'?}
    plus the vt_status/ledger_status/row_issues shape the readiness UI expects.
    Shared by /readiness, /masters-xml, and /create-masters so they never drift."""
    led = client.list_ledgers()
    groups = client.list_groups()
    voucher_types = client.list_voucher_types()

    led = classify.classify_ledgers(led, groups)
    ledger_names = {l["name"] for l in led}
    vt_names = {v["name"] for v in voucher_types}
    bank_contra_groups = body.get("bank_contra_groups") or {}

    items = []
    vt_status = {}
    for name in REQUIRED_VOUCHER_TYPES:
        exists = name in vt_names
        vt_status[name] = exists
        if not exists:
            items.append({"kind": "voucher_type", "name": name, "parent": "Purchase"})

    purchase_ledger = body.get("purchase_ledger") or "Purchase"
    sales_ledger = body.get("sales_ledger") or "Sales"
    ledger_status = {
        "purchase_ledger": {"name": purchase_ledger, "exists": purchase_ledger in ledger_names},
        "sales_ledger": {"name": sales_ledger, "exists": sales_ledger in ledger_names},
    }
    if not ledger_status["purchase_ledger"]["exists"]:
        items.append({"kind": "ledger", "name": purchase_ledger, "parent": "Purchase Accounts"})
    if not ledger_status["sales_ledger"]["exists"]:
        items.append({"kind": "ledger", "name": sales_ledger, "parent": "Sales Accounts"})

    row_issues = []
    seen = {(i["kind"], i["name"]) for i in items}
    for r in body.get("rows", []):
        if r.get("source") == "Bank":
            bank_ledger = (r.get("primary_ledger") or "").strip()
            key = ("ledger", bank_ledger)
            if bank_ledger and bank_ledger not in ledger_names and key not in seen:
                seen.add(key)
                row_issues.append({"kind": "bank_ledger", "name": bank_ledger})
                items.append({"kind": "ledger", "name": bank_ledger, "parent": "Bank Accounts"})
            # The contra side of a Bank row could be almost any ledger type
            # (vendor, customer, expense, another bank) -- too ambiguous to
            # guess a group for, so it only gets created once the caller has
            # explicitly picked a group for this name (via bank_contra_groups).
            contra = (r.get("contra_raw") or "").strip()
            if contra and not r.get("contra_ledger"):
                key2 = ("bank_contra", contra)
                if key2 not in seen:
                    seen.add(key2)
                    chosen_group = bank_contra_groups.get(contra)
                    row_issues.append({"kind": "bank_contra", "name": contra, "chosen_group": chosen_group})
                    if chosen_group:
                        items.append({"kind": "ledger", "name": contra, "parent": chosen_group})
            continue
        if r.get("source") != "GSTR2B":
            continue
        if r.get("status") == "LedgerNotFound":
            vendor = (r.get("contra_raw") or "").strip()
            key = ("ledger", vendor)
            if vendor and key not in seen:
                seen.add(key)
                gstin = r.get("gstin")
                row_issues.append({"kind": "vendor", "name": vendor, "gstin": gstin})
                items.append({"kind": "ledger", "name": vendor, "parent": "Sundry Creditors",
                              "gstin": gstin, "state": mx.state_from_gstin(gstin)})
        exp = r.get("expense_ledger")
        key = ("ledger", exp)
        if exp and exp not in ledger_names and key not in seen:
            seen.add(key)
            group = CATEGORY_TO_GROUP.get(r.get("expense_category"), "Indirect Expenses")
            row_issues.append({"kind": "expense_ledger", "name": exp, "category": r.get("expense_category")})
            items.append({"kind": "ledger", "name": exp, "parent": group})

        # Tax legs use the plain "IGST"/"CGST"/"SGST"/"CESS" column names as
        # ledger names directly -- create them under Duties & Taxes rather than
        # flag-only, since these are standard, low-risk ledgers unlike
        # vendor-specific ones.
        try:
            tax_legs = json.loads(r.get("tax_json") or "[]")
        except (ValueError, TypeError):
            tax_legs = []
        for leg in tax_legs:
            tax_name = leg[0] if isinstance(leg, (list, tuple)) and leg else None
            key = ("ledger", tax_name)
            if tax_name and tax_name not in ledger_names and key not in seen:
                seen.add(key)
                row_issues.append({"kind": "tax_ledger", "name": tax_name})
                items.append({"kind": "ledger", "name": tax_name, "parent": "Duties & Taxes"})

    return items, vt_status, ledger_status, row_issues


@tally_bp.route("/readiness", methods=["POST"])
def readiness():
    """Pre-flight check: are the masters this run needs already in Tally?
    Never creates anything -- just reports what's missing."""
    body = request.get_json(silent=True) or {}
    client = TallyClient(url=body.get("gateway_url") or "http://localhost:9000")
    try:
        items, vt_status, ledger_status, row_issues = _missing_items(client, body)
    except (TallyConnectionError, TallyGatewayError) as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    return jsonify({
        "ok": True, "ready": not items,
        "voucher_types": vt_status, "default_ledgers": ledger_status, "row_issues": row_issues,
    })


@tally_bp.route("/masters-xml", methods=["POST"])
def masters_xml_download():
    """Builds a Tally-importable XML file of everything missing, for
    Gateway of Tally -> Import Data -> Masters -- an alternative to the live
    /create-masters endpoint for firms that prefer to review before creating."""
    body = request.get_json(silent=True) or {}
    client = TallyClient(url=body.get("gateway_url") or "http://localhost:9000")
    try:
        items, _, _, _ = _missing_items(client, body)
    except (TallyConnectionError, TallyGatewayError) as e:
        return jsonify({"error": str(e)}), 502

    if not items:
        return jsonify({"error": "Nothing missing -- run a readiness check first, or everything already exists in Tally."}), 400

    fragments = [
        mx.voucher_type_fragment(i["name"], i["parent"]) if i["kind"] == "voucher_type"
        else mx.ledger_fragment(i["name"], i["parent"], gstin=i.get("gstin"), state=i.get("state"))
        for i in items
    ]
    xml_text = mx.build_masters_file(fragments)
    buf = io.BytesIO(xml_text.encode("utf-8"))
    return send_file(
        buf, as_attachment=True, download_name="tally_import_missing_masters.xml",
        mimetype="application/xml",
    )


@tally_bp.route("/create-masters", methods=["POST"])
def create_masters():
    """Live-creates everything the readiness check found missing, over the same
    HTTP gateway used for reads/posting. Shows exactly what will be created
    before this is called (the frontend re-runs /readiness first)."""
    body = request.get_json(silent=True) or {}
    client = TallyClient(url=body.get("gateway_url") or "http://localhost:9000")
    try:
        items, _, _, _ = _missing_items(client, body)
    except (TallyConnectionError, TallyGatewayError) as e:
        return jsonify({"error": str(e)}), 502

    results = []
    for i in items:
        if i["kind"] == "voucher_type":
            ok, msg = client.create_voucher_type(i["name"], i["parent"])
        else:
            ok, msg = client.create_ledger(i["name"], i["parent"], gstin=i.get("gstin"), state=i.get("state"))
        results.append({"kind": i["kind"], "name": i["name"], "ok": ok, "message": msg})

    created = sum(1 for r in results if r["ok"])
    failed = len(results) - created
    return jsonify({"ok": True, "results": results, "created": created, "failed": failed})


# ── templates ─────────────────────────────────────────────────────────────────

@tally_bp.route("/template/gstr2b", methods=["GET"])
def gstr2b_template():
    headers = ["sno", "Supplier Name", "GSTIN", "Get in period", "Reconcile in period",
               "Invoice No", "POS", "Invoice Date", "Invoice Value", "Taxable Value",
               "IGST", "CGST", "SGST", "CESS", "R1 Date", "RC", "Remark/Matching Criteria"]

    def sheet_rows(sample_doc_no):
        return [
            ["<Legal Name> (<GSTIN>) (F.Y.:<financial year>)"] + [""] * (len(headers) - 1),
            [""] * len(headers),
            headers,
            [1, "ABC Traders", "06ABFFA9443D1ZM", "Aug, 2025", "Aug, 2025", sample_doc_no,
             "UTTAR PRADESH", "22/08/2025", 78966.00, 75205.60, 3760.28, 0, 0, 0,
             "11-09-2025", "No", ""],
        ]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(sheet_rows("2025-26/SR-1205")).to_excel(writer, index=False, header=False, sheet_name="invoice")
        pd.DataFrame(sheet_rows("2025-26/CN-014")).to_excel(writer, index=False, header=False, sheet_name="note")
    buf.seek(0)
    return send_file(
        buf, as_attachment=True, download_name="GSTR2B_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@tally_bp.route("/template/bank", methods=["GET"])
def bank_template():
    headers = ["Date", "Narration", "Ledger (Bank)", "Contra Ledger", "Debit/Credit", "Amount"]
    rows = [
        headers,
        ["22/08/2025", "NEFT to ABC Traders", "HDFC Bank", "ABC Traders", "Debit", 15000],
        ["23/08/2025", "Receipt from XYZ Ltd", "HDFC Bank", "XYZ Ltd", "Credit", 22000],
        ["25/08/2025", "Transfer to ICICI Bank", "HDFC Bank", "ICICI Bank", "Debit", 50000],
    ]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False, header=False, sheet_name="bank")
    buf.seek(0)
    return send_file(
        buf, as_attachment=True, download_name="Bank_Statement_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── mapping table ─────────────────────────────────────────────────────────────

@tally_bp.route("/mapping", methods=["GET"])
def get_mapping():
    return jsonify({"mapping": map_store.load_mapping()})


@tally_bp.route("/mapping", methods=["PUT"])
def put_mapping():
    body = request.get_json(silent=True) or {}
    m = body.get("mapping")
    if not isinstance(m, dict):
        return jsonify({"error": "Expected {mapping: {...}}"}), 400
    map_store.save_mapping({str(k): str(v) for k, v in m.items() if k})
    return jsonify({"ok": True})


# ── parse ─────────────────────────────────────────────────────────────────────

@tally_bp.route("/parse/<source>", methods=["POST"])
def parse(source):
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    try:
        if source == "gstr2b":
            if f.filename.lower().endswith(".csv"):
                raw = pd.read_csv(f, header=None)
                rows = gstr2b._parse_sheet(raw, f.filename)
            else:
                rows = gstr2b.parse_workbook(f, _excel_engine(f.filename))
            return jsonify({"rows": [_row_to_json(r) for r in rows]})

        if source == "gstr1":
            mode = request.form.get("mode", "source_of_truth")
            engine = None if f.filename.lower().endswith(".csv") else _excel_engine(f.filename)
            rows = gstr1.parse_workbook(f, f.filename, engine, mode=mode)
            return jsonify({"rows": [_row_to_json(r) for r in rows]})

        df = _read_upload(f)
        if source == "bank":
            rows = bank.parse(df)
        elif source == "journal":
            rows = journal.parse(df)
        else:
            return jsonify({"error": f"Unknown source '{source}'"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"rows": [_row_to_json(r) for r in rows]})


# ── bank statement: column mapping ──────────────────────────────────────────────

def _read_bank_file(f) -> pd.DataFrame:
    """Reads a bank statement upload (CSV/XLSX/XLS/PDF) into a DataFrame. PDF
    password, if any, comes from the 'password' form field."""
    name = f.filename.lower()
    if name.endswith(".pdf"):
        password = request.form.get("password") or None
        return pdf_bank.extract_table(f, password)
    if name.endswith(".csv"):
        return pd.read_csv(f)
    return pd.read_excel(f, engine=_excel_engine(f.filename))


@tally_bp.route("/bank/preview", methods=["POST"])
def bank_preview():
    """Reads just the header row + a few sample rows so the frontend can build
    a column-mapping form -- no fixed template required. Works the same for
    CSV/XLSX/XLS and (optionally password-protected) PDF statements."""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    try:
        df = _read_bank_file(f)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    headers = [str(c) for c in df.columns]
    sample = df.head(5).fillna("").astype(str).values.tolist()
    return jsonify({"headers": headers, "sample_rows": sample})


@tally_bp.route("/bank/parse-mapped", methods=["POST"])
def bank_parse_mapped():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded"}), 400
    mapping_json = request.form.get("mapping", "{}")
    bank_ledger = request.form.get("bank_ledger", "")
    try:
        mapping = json.loads(mapping_json)
        df = _read_bank_file(f)
        rows, skipped_bad_dates = bank.parse_mapped(df, mapping, bank_ledger)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"rows": [_row_to_json(r) for r in rows], "skipped_bad_dates": skipped_bad_dates})


# ── bank narration rules ─────────────────────────────────────────────────────────

@tally_bp.route("/bank/rules", methods=["GET"])
def get_bank_rules():
    return jsonify({"rules": bank_rules.load_rules()})


@tally_bp.route("/bank/rules", methods=["PUT"])
def put_bank_rules():
    body = request.get_json(silent=True) or {}
    rules = body.get("rules")
    if not isinstance(rules, list):
        return jsonify({"error": "Expected {rules: [{contains, ledger}, ...]}"}), 400
    cleaned = [
        {"contains": str(r.get("contains", "")).strip(), "ledger": str(r.get("ledger", "")).strip()}
        for r in rules if r.get("contains") and r.get("ledger")
    ]
    bank_rules.save_rules(cleaned)
    return jsonify({"ok": True})


# ── resolve ledgers ───────────────────────────────────────────────────────────

def _norm_gstin(g) -> str:
    return "".join(str(g or "").split()).upper()


@tally_bp.route("/resolve", methods=["POST"])
def resolve():
    body = request.get_json(silent=True) or {}
    rows = [_row_from_json(r) for r in body.get("rows", [])]
    ledgers_full = body.get("ledgers", [])
    ledger_names = [l["name"] for l in ledgers_full] if ledgers_full else body.get("ledger_names", [])
    bank_names = set(body.get("bank_ledger_names", []))
    gstin_map = {}
    category_of = {}
    for l in ledgers_full:
        g = _norm_gstin(l.get("gstin"))
        if g:
            gstin_map[g] = l["name"]
        if l.get("category"):
            category_of[l["name"]] = l["category"]

    for row in rows:
        if row.get("source") == "Journal":
            for col in ("primary_ledger", "contra_ledger"):
                if row.get(col) not in ledger_names:
                    row["status"] = "UnMatched"
                    row["error"] = f"'{row.get(col)}' not found in Tally (exact match required for Journal)."
            continue

        # The bank ledger itself (e.g. "HDFC Bank") also has to exist in Tally --
        # only the contra side was ever checked before this. Still resolve the
        # contra side below so the row shows the complete picture either way.
        bank_missing = row.get("source") == "Bank" and row.get("primary_ledger") not in ledger_names

        if not row.get("contra_ledger"):
            raw = row.get("contra_raw") or ""
            row_gstin = _norm_gstin(row.get("gstin"))

            matched_ledger = gstin_map.get(row_gstin) if row_gstin else None
            match_method = "gstin" if matched_ledger else None

            if not matched_ledger:
                res = map_store.resolve(raw, ledger_names)
                if res["ledger"]:
                    matched_ledger = res["ledger"]
                    match_method = res["status"]  # 'saved' | 'exact' | 'fuzzy'
                    if match_method == "fuzzy":
                        map_store.set_mapping(raw, matched_ledger)

            if matched_ledger:
                row["contra_ledger"] = matched_ledger
                row["match_method"] = match_method
            else:
                row["status"] = "LedgerNotFound"
                hint = f"GSTIN {row.get('gstin')}" if row_gstin else f"'{raw}'"
                row["error"] = (
                    f"No Tally ledger matches {hint} (checked by GSTIN and by name). "
                    f"Create this ledger in Tally before posting this row."
                )

            if row.get("source") == "Bank" and row.get("contra_ledger") in bank_names:
                row["voucher_type"] = "Contra"

        if bank_missing:
            bank_msg = f"Bank ledger '{row.get('primary_ledger')}' not found in Tally."
            row["status"] = "LedgerNotFound"
            row["error"] = f"{bank_msg} {row.get('error') or ''}".strip()

        # GSTR2B: default/suggest the Purchase/Expense/Capital-Asset ledger for this row.
        # Learned suggestions (from ledgers the user previously posted this vendor against)
        # take priority over the plain "Purchase" fallback.
        if row.get("source") == "GSTR2B":
            if row.get("itc_eligible") is None:
                row["itc_eligible"] = True
            if not row.get("expense_ledger"):
                suggestion = classify.suggest_expense_ledger(row.get("contra_ledger") or "")
                row["expense_ledger"] = suggestion or body.get("default_purchase_ledger") or "Purchase"
            row["expense_category"] = category_of.get(row["expense_ledger"], "Purchase")

        # Tax legs (GSTR2B/GSTR1) carry the plain column name ("CGST" etc.) as a
        # placeholder ledger name -- resolve it against a saved mapping (e.g. the
        # firm's real "Input CGST" ledger) the same way vendor names are resolved,
        # instead of posting/creating a literally-named "CGST" ledger.
        if row.get("source") in ("GSTR2B", "GSTR1") and row.get("tax_json"):
            try:
                legs = json.loads(row["tax_json"])
            except (ValueError, TypeError):
                legs = []
            changed = False
            for leg in legs:
                if not isinstance(leg, list) or len(leg) != 2:
                    continue
                raw_tax_name = leg[0]
                res = map_store.resolve(raw_tax_name, ledger_names)
                if res["ledger"] and res["ledger"] != raw_tax_name:
                    leg[0] = res["ledger"]
                    changed = True
            if changed:
                row["tax_json"] = json.dumps(legs)

    return jsonify({"rows": [_row_to_json(r) for r in rows]})


# ── duplicate check ───────────────────────────────────────────────────────────

@tally_bp.route("/dupcheck", methods=["POST"])
def dupcheck():
    body = request.get_json(silent=True) or {}
    rows = [_row_from_json(r) for r in body.get("rows", [])]
    from_date = dt.date.fromisoformat(body.get("from_date"))
    to_date = dt.date.fromisoformat(body.get("to_date"))
    client = TallyClient(url=body.get("gateway_url") or "http://localhost:9000")

    checked = {}
    warnings = []
    for row in rows:
        ledger = row.get("primary_ledger") or row.get("contra_ledger")
        if not ledger:
            continue
        if ledger not in checked:
            try:
                checked[ledger] = client.ledger_vouchers(ledger, from_date, to_date)
            except (TallyConnectionError, TallyGatewayError) as e:
                warnings.append(f"Could not fetch vouchers for '{ledger}': {e}")
                checked[ledger] = []
        vouchers = checked[ledger]
        row_date = row["date"].strftime("%Y%m%d") if isinstance(row.get("date"), dt.date) else str(row.get("date"))
        row_amt = abs(float(row.get("amount") or 0))
        for v in vouchers:
            if v["date"] == row_date and abs(float(v.get("amount") or 0)) == row_amt:
                row["status"] = "Duplicate"
                row["duplicate_hint"] = f"Matches existing {v['voucher_type']} {v['voucher_number']} on {v['date']}"
                break

    return jsonify({"rows": [_row_to_json(r) for r in rows], "warnings": warnings})


# ── post ──────────────────────────────────────────────────────────────────────

def _require(row: dict, *fields: str) -> None:
    """Raises a clear, row-specific error instead of letting a missing ledger
    (e.g. an unresolved vendor) crash deep inside the XML builder with an
    unhelpful 'NoneType has no attribute...' error."""
    missing = [f for f in fields if not row.get(f)]
    if missing:
        friendly = {
            "contra_ledger": "vendor/contra ledger not resolved -- run 'Resolve ledgers' (and 'Create in Tally' if it's flagged LedgerNotFound) first",
            "primary_ledger": "primary ledger is blank",
            "expense_ledger": "Purchase/Expense/Asset ledger not selected for this row",
        }
        reasons = "; ".join(friendly.get(f, f"'{f}' is missing") for f in missing)
        raise ValueError(f"Cannot post this row: {reasons}.")


def _build_voucher_xml(row: dict, purchase_ledger: str, sales_ledger: str) -> str:
    vt = row.get("voucher_type")
    date = row["date"]
    if vt == "Payment":
        _require(row, "primary_ledger", "contra_ledger")
        return vx.payment_voucher(date, row["primary_ledger"], row["contra_ledger"], float(row["amount"]), row.get("narration") or "", row.get("reference"))
    if vt == "Receipt":
        _require(row, "primary_ledger", "contra_ledger")
        return vx.receipt_voucher(date, row["primary_ledger"], row["contra_ledger"], float(row["amount"]), row.get("narration") or "", row.get("reference"))
    if vt == "Contra":
        _require(row, "primary_ledger", "contra_ledger")
        return vx.contra_voucher(date, row["primary_ledger"], row["contra_ledger"], float(row["amount"]), row.get("narration") or "", row.get("reference"))
    if vt == "Journal":
        _require(row, "primary_ledger", "contra_ledger")
        return vx.journal_voucher(date, row["primary_ledger"], row["contra_ledger"], float(row["amount"]), row.get("narration") or "")
    if vt == "Purchase":
        _require(row, "contra_ledger")
        legs = json.loads(row.get("tax_json") or "[]")
        debit_ledger = row.get("expense_ledger") or purchase_ledger
        # "Indirect Expense" and "Capital Asset" post under their own Tally Voucher
        # Type (base type Purchase); everything else uses the plain Purchase type.
        posting_vch_type = row.get("expense_category") if row.get("expense_category") in ("Indirect Expense", "Capital Asset") else "Purchase"
        return vx.purchase_voucher(date, row["contra_ledger"], debit_ledger, float(row["taxable_value"]), legs, row.get("narration") or "", row.get("reference"), voucher_type=posting_vch_type)
    if vt == "Sales":
        _require(row, "contra_ledger")
        legs = json.loads(row.get("tax_json") or "[]")
        return vx.sales_voucher(date, row["contra_ledger"], sales_ledger, float(row["taxable_value"]), legs, row.get("narration") or "", row.get("reference"))
    raise ValueError(f"Unsupported voucher_type '{vt}'")


@tally_bp.route("/post", methods=["POST"])
def post():
    body = request.get_json(silent=True) or {}
    rows = [_row_from_json(r) for r in body.get("rows", []) if r.get("select")]
    purchase_ledger = body.get("purchase_ledger") or "Purchase"
    sales_ledger = body.get("sales_ledger") or "Sales"
    client = TallyClient(url=body.get("gateway_url") or "http://localhost:9000")

    results = []
    for row in rows:
        try:
            x = _build_voucher_xml(row, purchase_ledger, sales_ledger)
            ok, msg = client.post_voucher(x)
            row["status"] = "Posted" if ok else "Failed"
            row["error"] = "" if ok else msg
            if ok and row.get("source") == "GSTR2B" and row.get("expense_ledger"):
                classify.remember_vendor_expense(row.get("contra_ledger") or "", row["expense_ledger"])
            if ok and row.get("source") == "GSTR2B" and row.get("itc_eligible") is False:
                msg = (msg + " " if msg else "") + (
                    "ITC marked ineligible on this row -- posted with full input credit as-is; "
                    "reverse the ineligible portion manually in Tally via Alt+J (GST Stat Adjustment "
                    "> Reversal of Input Tax Credit) before filing GSTR-3B."
                )
        except Exception as e:
            ok, msg = False, str(e)
            row["status"] = "Failed"
            row["error"] = msg
        results.append({**_row_to_json(row), "result": "Posted" if ok else "Failed", "message": msg})

    posted = sum(1 for r in results if r["result"] == "Posted")
    failed = len(results) - posted
    return jsonify({"results": results, "posted": posted, "failed": failed})


@tally_bp.route("/log.xlsx", methods=["POST"])
def download_log():
    body = request.get_json(silent=True) or {}
    results = body.get("results", [])
    if not results:
        return jsonify({"error": "No results to export"}), 400
    df = pd.DataFrame(results)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Posting Log")
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"tally_import_log_{dt.datetime.now():%Y%m%d_%H%M%S}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
