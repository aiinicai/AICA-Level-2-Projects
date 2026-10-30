"""Self-contained HTML dashboard (inline SVG, no external libraries).

Colour roles follow a validated palette: categorical slots in fixed order,
status colours reserved for severity, text always in ink tokens.
"""
from __future__ import annotations

import html
from datetime import date

import pandas as pd

from .config import FY_LABEL, SOCIETY

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SERIES_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500"]
SEQ = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]
STATUS = {"High": "#d03b3b", "Medium": "#ec835a", "Low": "#fab219", "Info": "#0ca30c"}
STATUS_ICON = {"High": "&#9650;", "Medium": "&#9679;", "Low": "&#9632;", "Info": "&#10003;"}


def inr(x: float) -> str:
    neg = x < 0
    s = str(int(round(abs(x))))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if neg else "") + "₹" + s


def lakh(x: float) -> str:
    return f"₹{x / 1e5:.1f} L" if abs(x) >= 1e5 else inr(x)


def _esc(s) -> str:
    return html.escape(str(s))


# ----------------------------------------------------------------------------- chart primitives
def hbar(cats, vals, colors, width=430, fmt=inr, title=""):
    n = len(cats)
    bar_h, gap, left, top = 22, 10, 128, 8
    h = top + n * (bar_h + gap) + 8
    vmax = max(vals) if vals and max(vals) > 0 else 1
    plot_w = width - left - 76
    out = [f'<svg class="chart" viewBox="0 0 {width} {h}" role="img" aria-label="{_esc(title)}">']
    for i, (c, v) in enumerate(zip(cats, vals)):
        y = top + i * (bar_h + gap)
        w = max(2, plot_w * v / vmax)
        out.append(f'<text x="{left - 10}" y="{y + bar_h / 2 + 4}" text-anchor="end" class="lbl">{_esc(c)}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="4" fill="{colors[i % len(colors)]}" class="bar" data-tip="{_esc(c)}: {_esc(fmt(v))}"/>')
        out.append(f'<text x="{left + w + 8:.1f}" y="{y + bar_h / 2 + 4}" class="val">{_esc(fmt(v))}</text>')
    out.append("</svg>")
    return "\n".join(out)


def grouped_bars(cats, series: dict[str, list[float]], colors, width=620, height=240, fmt=lambda v: f"{v:.1f}%", title=""):
    left, right, top, bottom = 44, 12, 12, 34
    pw, ph = width - left - right, height - top - bottom
    n, k = len(cats), len(series)
    vmax = max(max(v) for v in series.values()) * 1.15 or 1
    group_w = pw / n
    bar_w = (group_w - 8) / k
    out = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(title)}">']
    for g in range(5):
        y = top + ph - ph * g / 4
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end" class="tick">{fmt(vmax * g / 4)}</text>')
    for i, c in enumerate(cats):
        gx = left + i * group_w + 4
        for j, (name, vals) in enumerate(series.items()):
            v = vals[i]
            bh = ph * v / vmax
            x = gx + j * bar_w
            out.append(f'<rect x="{x:.1f}" y="{top + ph - bh:.1f}" width="{bar_w - 2:.1f}" height="{bh:.1f}" rx="3" fill="{colors[j]}" class="bar" data-tip="{_esc(name)} · {_esc(c)}: {_esc(fmt(v))}"/>')
        out.append(f'<text x="{gx + (group_w - 8) / 2:.1f}" y="{height - 12}" text-anchor="middle" class="tick">{_esc(c)}</text>')
    out.append(f'<line x1="{left}" x2="{width - right}" y1="{top + ph}" y2="{top + ph}" class="axis"/>')
    out.append("</svg>")
    legend = "".join(f'<span class="lg"><i style="background:{colors[j]}"></i>{_esc(n)}</span>' for j, n in enumerate(series))
    return f'<div class="legend">{legend}</div>' + "\n".join(out)


def line_chart(cats, series: dict[str, list[float]], colors, width=440, height=230, fmt=lakh, title=""):
    left, right, top, bottom = 56, 16, 12, 34
    pw, ph = width - left - right, height - top - bottom
    vmax = max(max(v) for v in series.values()) * 1.1 or 1
    vmin = 0
    n = len(cats)
    xs = [left + pw * i / (n - 1) for i in range(n)]
    out = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(title)}">']
    for g in range(5):
        y = top + ph - ph * g / 4
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end" class="tick">{fmt(vmax * g / 4)}</text>')
    for j, (name, vals) in enumerate(series.items()):
        pts = " ".join(f"{x:.1f},{top + ph - ph * v / vmax:.1f}" for x, v in zip(xs, vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{colors[j]}" stroke-width="2" stroke-linejoin="round"/>')
        for x, v, c in zip(xs, vals, cats):
            out.append(f'<circle cx="{x:.1f}" cy="{top + ph - ph * v / vmax:.1f}" r="4" fill="{colors[j]}" stroke="var(--surface)" stroke-width="2" class="bar" data-tip="{_esc(name)} · {_esc(c)}: {_esc(fmt(v))}"/>')
    for i, c in enumerate(cats):
        if i % 2 == 0:
            out.append(f'<text x="{xs[i]:.1f}" y="{height - 12}" text-anchor="middle" class="tick">{_esc(c)}</text>')
    out.append("</svg>")
    legend = "".join(f'<span class="lg"><i style="background:{colors[j]}"></i>{_esc(n)}</span>' for j, n in enumerate(series))
    return f'<div class="legend">{legend}</div>' + "\n".join(out)


# ----------------------------------------------------------------------------- page
def build_dashboard(ctx: dict) -> str:
    f: pd.DataFrame = ctx["findings"]
    ledger: pd.DataFrame = ctx["ledger"]
    cal: pd.DataFrame = ctx["calendar"]
    gst_summary: pd.DataFrame = ctx["gst_summary"]
    benford: pd.DataFrame = ctx["benford"]
    monthly: pd.DataFrame = ctx["monthly"]
    tax = ctx["tax_summary"]
    as_of: date = ctx["as_of"]

    sev_counts = f.severity.value_counts()
    kpis = [
        ("Member dues at 31-Mar-2026", lakh(ledger.closing_balance.clip(lower=0).sum()), f"{int((ledger.months_of_arrears >= 3).sum())} members over 3 months"),
        ("Audit observations", str(len(f)), f"{int(sev_counts.get('High', 0))} high · {int(sev_counts.get('Medium', 0))} medium · {int(sev_counts.get('Low', 0) + sev_counts.get('Info', 0))} low"),
        ("GST billing errors", lakh(gst_summary.amount.abs().sum()), f"{int(gst_summary.bills.sum())} bills across {int(gst_summary.flats.sum())} flats"),
        ("Sinking fund under-invested", lakh(ctx["sf_gap"]), "vs earmarked fixed deposits"),
        ("Quantified exposure", lakh(f.amount.sum()), "sum of all observations"),
        ("Income-tax payable", inr(tax["net_payable"] + tax["interest_234b"] + tax["interest_234c"]), f"incl. s.234B/C interest · {tax['regime']}"),
    ]
    kpi_html = "".join(f'<div class="tile"><div class="k">{_esc(k)}</div><div class="v">{_esc(v)}</div><div class="s">{_esc(s)}</div></div>' for k, v, s in kpis)

    # ageing chart (ordinal -> sequential ramp)
    order = ["Regular", "Arrears 1-3 months", "Defaulter (>3 months)", "Chronic defaulter (>6 months)"]
    counts = [int((ledger.status == o).sum()) for o in order]
    amounts = [float(ledger[ledger.status == o].closing_balance.clip(lower=0).sum()) for o in order]
    short = ["Regular", "1-3 months", "3-6 months", "Over 6 months"]
    ageing = hbar([f"{o} ({c})" for o, c in zip(short, counts)], amounts, SEQ[1:], fmt=lakh, title="Member dues by ageing bucket")

    # findings by module (stacked by severity shown as separate bars per severity for simplicity)
    mods = f.groupby("module").size().sort_values(ascending=False)
    by_mod = hbar(list(mods.index), [float(x) for x in mods.values], [SERIES[0]] * len(mods), fmt=lambda v: f"{int(v)}", title="Observations by module")

    gst_chart = hbar([_short(i) for i in gst_summary.issue], [abs(float(a)) for a in gst_summary.amount], [SERIES[1], SERIES[1], SERIES[2]], fmt=inr, title="GST billing errors by cause")

    benford_chart = grouped_bars([str(d) for d in benford.first_digit], {"Benford expected": list(benford.expected_pct), "Actual": list(benford.actual_pct)}, [SERIES[3], SERIES[0]], title="First-digit test on expense invoices")

    monthly_chart = line_chart(list(monthly.month), {"Billed": list(monthly.billed), "Collected": list(monthly.collected)}, [SERIES[0], SERIES[2]], title="Monthly billing and collection")

    def sev_chip(s):
        return f'<span class="chip" style="--c:{STATUS[s]}">{STATUS_ICON[s]} {s}</span>'

    rows = "".join(
        f"<tr><td>{_esc(r.id)}</td><td>{sev_chip(r.severity)}</td><td>{_esc(r.module)}</td><td><b>{_esc(r.area)}</b><br><span class='muted'>{_esc(r.observation)}</span></td>"
        f"<td class='num'>{_esc(inr(r.amount)) if r.amount else '-'}</td><td class='muted'>{_esc(r.recommendation)}</td></tr>"
        for r in f.itertuples())

    def cal_chip(s):
        c = "#d03b3b" if s.startswith("Overdue") else "#ec835a" if s.startswith("Due") else "#0ca30c" if s.startswith("Complied") else "#52514e"
        return f'<span class="chip" style="--c:{c}">{_esc(s)}</span>'
    cal_rows = "".join(f"<tr><td>{r.due_date:%d-%b-%Y}</td><td>{_esc(r.obligation)}</td><td class='muted'>{_esc(r.authority)}</td><td>{cal_chip(r.status)}</td></tr>" for r in cal.itertuples())

    defaulters = ledger[ledger.months_of_arrears >= 3].sort_values("closing_balance", ascending=False)
    def_rows = "".join(f"<tr><td>{_esc(r.flat_no)}</td><td>{_esc(r.flat_type)}</td><td class='num'>{_esc(inr(r.opening_arrears))}</td><td class='num'>{_esc(inr(r.billed_fy))}</td><td class='num'>{_esc(inr(r.received_fy))}</td><td class='num'><b>{_esc(inr(r.closing_balance))}</b></td><td class='num'>{r.months_of_arrears:.1f}</td></tr>" for r in defaulters.itertuples())

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CHS Audit Dashboard - JJAA</title>
<style>
:root{{color-scheme:light;--surface:#fcfcfb;--card:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#6f6e6a;--line:#e6e5e1;--grid:#eceae5;--accent:#2a78d6}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--surface:#1a1a19;--card:#242422;--ink:#f0efec;--ink2:#c3c2b7;--muted:#9c9b93;--line:#36352f;--grid:#2f2e2a;--accent:#3987e5}}}}
:root[data-theme="dark"]{{color-scheme:dark;--surface:#1a1a19;--card:#242422;--ink:#f0efec;--ink2:#c3c2b7;--muted:#9c9b93;--line:#36352f;--grid:#2f2e2a;--accent:#3987e5}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--surface);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:24px 16px 48px}}
header h1{{font-size:22px;margin:0 0 4px}}header p{{margin:0;color:var(--ink2)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}}
.tile{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
.tile .k{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}}.tile .v{{font-size:24px;font-weight:600;margin:4px 0 2px;font-variant-numeric:tabular-nums}}.tile .s{{font-size:12px;color:var(--ink2)}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;overflow:hidden}}
.card h2{{font-size:15px;margin:0 0 2px}}.card .sub{{font-size:12px;color:var(--muted);margin:0 0 10px}}
svg.chart{{width:100%;height:auto;display:block}}
.lbl{{font-size:11px;fill:var(--ink2)}}.val{{font-size:11px;fill:var(--ink)}}.tick{{font-size:10px;fill:var(--muted)}}
.grid{{stroke:var(--grid);stroke-width:1}}.axis{{stroke:var(--line);stroke-width:1}}
.bar{{cursor:pointer;transition:opacity .15s}}.bar:hover{{opacity:.75}}
.legend{{display:flex;gap:14px;font-size:12px;color:var(--ink2);margin:0 0 6px}}.lg i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th{{text-align:left;color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em;padding:8px 8px;border-bottom:1px solid var(--line)}}
td{{padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top}}td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.muted{{color:var(--ink2)}}.chip{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;color:var(--c);border:1px solid var(--c);white-space:nowrap}}
.section{{margin-top:22px}}.tbl{{overflow-x:auto}}
#tip{{position:fixed;pointer-events:none;background:var(--ink);color:var(--surface);padding:6px 9px;border-radius:6px;font-size:12px;opacity:0;transition:opacity .1s;z-index:9}}
footer{{margin-top:28px;font-size:12px;color:var(--muted)}}
</style></head><body><div class="wrap">
<header><h1>{_esc(SOCIETY.name)} - Statutory Audit Dashboard {FY_LABEL}</h1>
<p>AI-assisted audit assistant · {len(ledger)} flats · data as at {as_of:%d %B %Y} · Regn. {_esc(SOCIETY.reg_no)}</p></header>
<div class="tiles">{kpi_html}</div>
<div class="grid2">
<div class="card"><h2>Member dues by ageing</h2><p class="sub">Closing balance at 31-Mar-2026 grouped by months of arrears (members in brackets)</p>{ageing}</div>
<div class="card"><h2>Monthly billing vs collection</h2><p class="sub">Maintenance billed on the 1st against receipts in the month</p>{monthly_chart}</div>
<div class="card"><h2>GST billing errors</h2><p class="sub">Society-charged GST compared with the Rs 7,500 per member test (Circular 109/28/2019)</p>{gst_chart}</div>
<div class="card"><h2>Observations by module</h2><p class="sub">{len(f)} observations across {f.module.nunique()} audit areas</p>{by_mod}</div>
<div class="card" style="grid-column:1/-1"><h2>Benford first-digit test</h2><p class="sub">Expense invoice first digits against Benford's expected distribution; deviations guided the detailed tests</p>{benford_chart}</div>
</div>
<div class="card section"><h2>Audit observations</h2><p class="sub">Generated by the rule-based modules; narrative drafted by the AI layer and reviewed by the auditor</p>
<div class="tbl"><table><thead><tr><th>ID</th><th>Severity</th><th>Module</th><th>Observation</th><th>Amount</th><th>Recommendation</th></tr></thead><tbody>{rows}</tbody></table></div></div>
<div class="grid2 section">
<div class="card"><h2>Defaulters (over 3 months)</h2><p class="sub">Candidates for s.101 recovery</p><div class="tbl"><table><thead><tr><th>Flat</th><th>Type</th><th>Opening</th><th>Billed</th><th>Received</th><th>Closing</th><th>Months</th></tr></thead><tbody>{def_rows}</tbody></table></div></div>
<div class="card"><h2>Compliance calendar</h2><p class="sub">Status as at {as_of:%d-%b-%Y}</p><div class="tbl"><table><thead><tr><th>Due</th><th>Obligation</th><th>Authority</th><th>Status</th></tr></thead><tbody>{cal_rows}</tbody></table></div></div>
</div>
<footer>Synthetic data for an AICA Level 2 capstone project. Member identities are fictitious; PANs masked. Legal references are as supplied to the model and verified by the auditor.</footer>
</div>
<div id="tip"></div>
<script>
const tip=document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el=>{{el.addEventListener('mousemove',e=>{{tip.textContent=el.dataset.tip;tip.style.opacity=1;tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';}});el.addEventListener('mouseleave',()=>tip.style.opacity=0);}});
</script></body></html>"""


def _short(issue: str) -> str:
    return {"GST charged on property tax component (over-charged)": "Prop. tax taxed (over)",
            "GST charged although monthly contribution below Rs 7,500": "Below ₹7,500 (over)",
            "GST not charged although contribution exceeds Rs 7,500": "Above ₹7,500 (under)"}.get(issue, issue[:28])
