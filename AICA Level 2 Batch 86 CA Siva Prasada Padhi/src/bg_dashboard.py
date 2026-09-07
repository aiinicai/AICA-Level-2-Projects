#!/usr/bin/env python3
"""
BANK GUARANTEE MONITORING — DASHBOARD

Reads the same Google Sheet as the reminder engine and writes a
self-contained HTML dashboard, then opens it in the default browser.

Nothing extra to install: the file is plain HTML and CSS, so it can be
emailed to management, printed, or attached to an audit working paper.

    python bg_dashboard.py                  build and open
    python bg_dashboard.py --no-open        build only
    python bg_dashboard.py --output x.html  choose the file name
"""

import argparse
import os
import re
import sys
import webbrowser
from collections import defaultdict
from datetime import datetime

import bg_monitor_exe as engine

TITLE = "Bank Guarantee Monitoring Dashboard"

AGEING_BUCKETS = [
    ("Already expired", None, -1, "#7f1d1d"),
    ("0 - 10 days", 0, 10, "#c62828"),
    ("11 - 20 days", 11, 20, "#e65100"),
    ("21 - 30 days", 21, 30, "#f9a825"),
    ("31 - 60 days", 31, 60, "#1a73e8"),
    ("61 - 90 days", 61, 90, "#5c6bc0"),
    ("Beyond 90 days", 91, None, "#1b7a3d"),
]


# ──────────────────────────────────────────────────────────────────────────
# Number handling
# ──────────────────────────────────────────────────────────────────────────

def parse_amount(raw):
    """Turn '12,50,000', 'Rs. 1250000/-', '₹ 12.5 L' style text into a float."""
    if raw is None:
        return 0.0
    text = str(raw).strip()
    if not text:
        return 0.0
    text = text.replace(",", "").replace("\u20b9", "")
    text = re.sub(r"(?i)(rs\.?|inr|/-)", "", text).strip()
    match = re.search(r"-?\d+(\.\d+)?", text)
    if not match:
        return 0.0
    value = float(match.group(0))
    if re.search(r"(?i)\bcr\b|crore", text):
        value *= 1e7
    elif re.search(r"(?i)\blac?k?h?s?\b", text):
        value *= 1e5
    return value


def fmt_inr(value):
    """Indian short form: 1,25,00,000 becomes 1.25 Cr."""
    if not value:
        return "—"
    if value >= 1e7:
        return f"{value / 1e7:,.2f} Cr"
    if value >= 1e5:
        return f"{value / 1e5:,.2f} L"
    return f"{value:,.0f}"


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ──────────────────────────────────────────────────────────────────────────
# Data collection
# ──────────────────────────────────────────────────────────────────────────

ERROR_VALUES = ("#N/A", "#REF", "#NAME", "#VALUE", "#DIV", "#NULL", "#ERROR")


def clean_lookup(text):
    """Spreadsheet lookup failures (#N/A and friends) are not bank names."""
    if not text or str(text).strip().upper().startswith(ERROR_VALUES):
        return ""
    return str(text).strip()


def find(headers, pattern):
    for i, h in enumerate(headers):
        if re.search(pattern, h, re.I):
            return i
    return -1


def collect(ss):
    """Read the BG register and return parsed, classified records."""
    sheet = ss.worksheet(engine.BG_SHEET_NAME)
    data = sheet.get_all_values()
    if len(data) <= 1:
        return [], []

    headers = [str(h).strip() for h in data[0]]
    idx = engine.get_header_indexes(headers)
    i_amount = find(headers, r"Amount")
    i_bank = find(headers, r"Issuing\s*Bank|Bank\s*Name|^Bank(?!\s*Guarantee)")
    i_vendor = find(headers, r"Vendor\s*Name|Contractor|Supplier|Party")
    i_purpose = find(headers, r"Purpose")
    i_contract = find(headers, r"Contract\s*Number|Contract\s*No|PO\s*No|Work\s*Order")

    expiry_i = idx["expiryDate"] if idx["expiryDate"] != -1 else 12
    bgdate_i = idx["bgDate"] if idx["bgDate"] != -1 else 7

    today = datetime.now(engine.IST).date()
    records, problems = [], []

    def cell(row, i):
        return row[i].strip() if 0 <= i < len(row) and row[i] else ""

    for n, row in enumerate(data[1:], start=2):
        if all(str(c).strip() == "" for c in row):
            continue

        bg_no = cell(row, idx["bgNumber"]) or f"Row {n}"
        status = (cell(row, idx["status"]) or "Active").strip()
        raw_expiry = cell(row, expiry_i)

        if not raw_expiry:
            problems.append((bg_no, n, "Date of Expiry is blank — row is not monitored"))
            continue

        expiry = engine.parse_date(raw_expiry)
        if not expiry:
            problems.append((bg_no, n, f"Expiry date '{raw_expiry}' could not be read"))
            continue

        bg_date = engine.parse_date(cell(row, bgdate_i))
        if bg_date and expiry <= bg_date:
            problems.append((bg_no, n, "Expiry date is on or before the BG date"))

        if cell(row, i_bank) and not clean_lookup(cell(row, i_bank)):
            problems.append((bg_no, n, "IFS code returns no match — bank and branch unresolved"))

        email = cell(row, idx["email"])
        if status.lower() not in engine.INACTIVE_STATUSES and "@" not in email:
            problems.append((bg_no, n, "No vendor email — notices fall back to the default address"))

        records.append({
            "bg_no": bg_no,
            "vendor": cell(row, i_vendor) or "(not stated)",
            "bank": clean_lookup(cell(row, i_bank)) or "(IFSC lookup unresolved)",
            "purpose": cell(row, i_purpose) or "(not stated)",
            "contract": cell(row, i_contract),
            "amount": parse_amount(cell(row, i_amount)),
            "expiry": expiry,
            "days": (expiry - today).days,
            "status": status,
            "active": status.lower() not in engine.INACTIVE_STATUSES,
        })

    return records, problems


def read_log(ss):
    """Summarise BG_Email_Log: status counts and any failures."""
    try:
        rows = ss.worksheet(engine.LOG_SHEET_NAME).get_all_values()
    except Exception:
        return {}, [], None

    counts = defaultdict(int)
    failures = []
    last = None
    for row in rows[1:]:
        if len(row) < 8:
            continue
        status, stamp, message = row[6], row[4], row[7]
        counts[status] += 1
        if stamp:
            last = stamp
        if status == "Failed":
            failures.append((row[2], stamp, message))
    return dict(counts), failures[-8:], last


# ──────────────────────────────────────────────────────────────────────────
# HTML building blocks
# ──────────────────────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; }
body { margin:0; background:#eef1f5; color:#1f2933;
       font-family:'Segoe UI',Arial,Helvetica,sans-serif; font-size:14px; }
.wrap { max-width:1180px; margin:0 auto; padding:0 22px 40px; }
header { background:linear-gradient(100deg,#16222c 0%,#24384a 100%); color:#fff;
         padding:26px 0 30px; margin-bottom:-34px; }
header .wrap { padding-bottom:0; }
h1 { margin:0; font-size:24px; letter-spacing:.3px; }
.sub { color:#9fb0c0; font-size:13px; margin-top:6px; }
.cards { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:24px; }
.card { flex:1; min-width:190px; background:#fff; border-radius:10px; padding:18px 20px;
        box-shadow:0 2px 10px rgba(20,35,50,.10); border-top:4px solid #1a73e8; }
.card .lbl { font-size:11px; letter-spacing:.9px; text-transform:uppercase; color:#7b8794; }
.card .val { font-size:27px; font-weight:700; margin-top:6px; line-height:1.1; }
.card .note { font-size:12px; color:#7b8794; margin-top:4px; }
.card.red { border-top-color:#c62828; } .card.red .val { color:#c62828; }
.card.amber { border-top-color:#e65100; } .card.amber .val { color:#e65100; }
.card.green { border-top-color:#1b7a3d; } .card.green .val { color:#1b7a3d; }
section { background:#fff; border-radius:10px; padding:20px 22px; margin-bottom:20px;
          box-shadow:0 2px 10px rgba(20,35,50,.07); }
h2 { font-size:15px; margin:0 0 16px; color:#24384a; letter-spacing:.3px;
     border-left:4px solid #1a73e8; padding-left:10px; }
.row { display:flex; gap:20px; flex-wrap:wrap; }
.row > section { flex:1; min-width:340px; }
.bar-row { display:flex; align-items:center; margin-bottom:9px; }
.bar-lbl { width:130px; font-size:12.5px; color:#3e4c59; }
.bar-track { flex:1; background:#f0f3f7; border-radius:4px; height:24px; position:relative; }
.bar-fill { height:24px; border-radius:4px; min-width:3px; }
.bar-val { width:150px; text-align:right; font-size:12.5px; color:#3e4c59; padding-left:10px; }
.cols { display:flex; align-items:flex-end; height:180px; gap:10px;
        border-bottom:2px solid #d3dae2; padding:0 4px; }
.col { flex:1; display:flex; flex-direction:column; justify-content:flex-end;
       align-items:center; height:100%; }
.col .bar { width:100%; background:#1a73e8; border-radius:4px 4px 0 0; }
.col .amt { font-size:10.5px; color:#52606d; margin-bottom:4px; white-space:nowrap; }
.colnames { display:flex; gap:10px; padding:6px 4px 0; }
.colnames div { flex:1; text-align:center; font-size:11px; color:#7b8794; }
table { width:100%; border-collapse:collapse; }
th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.6px;
     color:#7b8794; border-bottom:2px solid #e4e9ef; padding:7px 8px; }
td { padding:8px; border-bottom:1px solid #f0f3f7; font-size:13px; }
td.num, th.num { text-align:right; }
.pill { display:inline-block; padding:2px 9px; border-radius:11px; font-size:11px;
        font-weight:600; color:#fff; }
.footer { text-align:center; color:#7b8794; font-size:11.5px; margin-top:26px; }
"""


def bar_chart(rows, total):
    out = ""
    top = max([r[1] for r in rows] + [1])
    for label, count, amount, colour in rows:
        pct = (count / top * 100) if top else 0
        share = f"{count} BG · {fmt_inr(amount)}" if count else "—"
        out += (f'<div class="bar-row"><div class="bar-lbl">{esc(label)}</div>'
                f'<div class="bar-track"><div class="bar-fill" '
                f'style="width:{pct:.1f}%;background:{colour}"></div></div>'
                f'<div class="bar-val">{share}</div></div>')
    return out


def column_chart(months):
    top = max([m[1] for m in months] + [1])
    cols = "".join(
        f'<div class="col"><div class="amt">{fmt_inr(v) if v else ""}</div>'
        f'<div class="bar" style="height:{(v / top * 130) if top else 0:.0f}px'
        f';{"background:#c62828" if i < 1 else ""}"></div></div>'
        for i, (_, v) in enumerate(months))
    names = "".join(f"<div>{esc(m)}</div>" for m, _ in months)
    return f'<div class="cols">{cols}</div><div class="colnames">{names}</div>'


def table(headers, rows, aligns=None):
    aligns = aligns or [""] * len(headers)
    head = "".join(f'<th class="{a}">{esc(h)}</th>' for h, a in zip(headers, aligns))
    body = ""
    for row in rows:
        body += "<tr>" + "".join(
            f'<td class="{a}">{c}</td>' for c, a in zip(row, aligns)) + "</tr>"
    if not rows:
        body = f'<tr><td colspan="{len(headers)}" style="color:#7b8794">Nothing to report.</td></tr>'
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


# ──────────────────────────────────────────────────────────────────────────
# Page assembly
# ──────────────────────────────────────────────────────────────────────────

def build_html(records, problems, log_counts, failures, last_run, mode):
    now = datetime.now(engine.IST)
    active = [r for r in records if r["active"]]
    live = [r for r in active if r["days"] >= 0]

    total_value = sum(r["amount"] for r in live)
    due30 = [r for r in live if r["days"] <= 30]
    due10 = [r for r in live if r["days"] <= 10]
    expired = [r for r in active if r["days"] < 0]

    # Ageing buckets
    bucket_rows = []
    for label, lo, hi, colour in AGEING_BUCKETS:
        if lo is None:
            group = [r for r in active if r["days"] < 0]
        elif hi is None:
            group = [r for r in active if r["days"] >= lo]
        else:
            group = [r for r in active if lo <= r["days"] <= hi]
        bucket_rows.append((label, len(group), sum(x["amount"] for x in group), colour))

    # Amount falling due by month, next six months
    monthly = defaultdict(float)
    for r in live:
        monthly[r["expiry"].strftime("%b %y")] += r["amount"]
    ordered = sorted({r["expiry"].replace(day=1) for r in live})[:6]
    months = [(d.strftime("%b %y"), monthly.get(d.strftime("%b %y"), 0)) for d in ordered]

    # Bank-wise and vendor-wise
    def group_by(key):
        agg = defaultdict(lambda: [0, 0.0])
        for r in live:
            agg[r[key]][0] += 1
            agg[r[key]][1] += r["amount"]
        return sorted(agg.items(), key=lambda kv: -kv[1][1])[:8]

    banks = [(esc(k), str(v[0]), fmt_inr(v[1]),
              f"{(v[1] / total_value * 100) if total_value else 0:.1f}%")
             for k, v in group_by("bank")]
    vendors = [(esc(k), str(v[0]), fmt_inr(v[1]),
                f"{(v[1] / total_value * 100) if total_value else 0:.1f}%")
               for k, v in group_by("vendor")]

    # Urgent watch list
    watch = sorted(due30, key=lambda r: r["days"])[:12]
    watch_rows = []
    for r in watch:
        colour = "#c62828" if r["days"] <= 10 else ("#e65100" if r["days"] <= 20 else "#f9a825")
        watch_rows.append((
            esc(r["bg_no"]), esc(r["vendor"]), esc(r["bank"]),
            fmt_inr(r["amount"]), r["expiry"].strftime("%d-%m-%Y"),
            f'<span class="pill" style="background:{colour}">{r["days"]} days</span>'))

    log_rows = [(esc(k), str(v)) for k, v in sorted(log_counts.items())]
    fail_rows = [(esc(a), esc(b), esc(c)[:90]) for a, b, c in failures]
    prob_rows = [(esc(a), str(b), esc(c)) for a, b, c in problems[:12]]

    mode_colour = "#c62828" if mode == "PRODUCTION" else "#1b7a3d"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{TITLE}</title><style>{CSS}</style></head>
<body>
<header><div class="wrap">
  <h1>{TITLE}</h1>
  <div class="sub">Generated {now:%d %B %Y, %H:%M} IST &nbsp;·&nbsp; Dispatch mode
    <span class="pill" style="background:{mode_colour}">{esc(mode)}</span>
    &nbsp;·&nbsp; Last engine run: {esc(last_run or "no record")}</div>
</div></header>

<div class="wrap">
  <div class="cards" style="margin-top:44px">
    <div class="card"><div class="lbl">Live guarantees</div>
      <div class="val">{len(live)}</div><div class="note">active and unexpired</div></div>
    <div class="card"><div class="lbl">Value secured</div>
      <div class="val">{fmt_inr(total_value)}</div><div class="note">total exposure covered</div></div>
    <div class="card amber"><div class="lbl">Expiring in 30 days</div>
      <div class="val">{len(due30)}</div><div class="note">{fmt_inr(sum(r['amount'] for r in due30))} at stake</div></div>
    <div class="card red"><div class="lbl">Final notice zone</div>
      <div class="val">{len(due10)}</div><div class="note">10 days or fewer — invocation window</div></div>
    <div class="card{' red' if expired else ' green'}"><div class="lbl">Lapsed, still open</div>
      <div class="val">{len(expired)}</div><div class="note">expired but not marked closed</div></div>
  </div>

  <section>
    <h2>Expiry pipeline — ageing of the live register</h2>
    {bar_chart(bucket_rows, len(active))}
  </section>

  <section>
    <h2>Value falling due by month</h2>
    {column_chart(months) if months else '<p style="color:#7b8794">No dated guarantees to plot.</p>'}
  </section>

  <section>
    <h2>Watch list — next thirty days</h2>
    {table(["BG number", "Vendor", "Issuing bank", "Amount", "Expiry", "Runway"],
           watch_rows, ["", "", "", "num", "", "num"])}
  </section>

  <div class="row">
    <section>
      <h2>Bank-wise exposure</h2>
      {table(["Issuing bank", "Count", "Amount", "Share"], banks, ["", "num", "num", "num"])}
    </section>
    <section>
      <h2>Vendor-wise exposure</h2>
      {table(["Vendor", "Count", "Amount", "Share"], vendors, ["", "num", "num", "num"])}
    </section>
  </div>

  <div class="row">
    <section>
      <h2>Dispatch log summary</h2>
      {table(["Outcome", "Entries"], log_rows, ["", "num"])}
      <h2 style="margin-top:20px">Recent failures</h2>
      {table(["BG number", "When", "Reason"], fail_rows)}
    </section>
    <section>
      <h2>Data quality exceptions</h2>
      {table(["BG number", "Row", "Issue"], prob_rows, ["", "num", ""])}
    </section>
  </div>

  <div class="footer">
    Bank Guarantee Monitoring System &nbsp;·&nbsp; figures read directly from the
    operational register &nbsp;·&nbsp; this dashboard is a read-only view and changes nothing
  </div>
</div>
</body></html>"""
    return html


def main():
    ap = argparse.ArgumentParser(description="Build the BG monitoring dashboard")
    ap.add_argument("--output", default="BG_Dashboard.html")
    ap.add_argument("--no-open", action="store_true", help="write the file but do not open it")
    args = ap.parse_args()

    print("Reading the register...")
    ss = engine.open_spreadsheet()
    config = engine.get_config(ss)
    records, problems = collect(ss)
    log_counts, failures, last_run = read_log(ss)

    if not records:
        print("The BG sheet has no usable rows.")
        return

    html = build_html(records, problems, log_counts, failures, last_run,
                      config.get("SYSTEM_MODE", "TEST").upper())

    path = os.path.abspath(args.output)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"Dashboard written: {path}")
    print(f"{len(records)} records read, {len(problems)} data exceptions flagged.")

    if not args.no_open:
        webbrowser.open(f"file:///{path.replace(os.sep, '/')}")


if __name__ == "__main__":
    main()
