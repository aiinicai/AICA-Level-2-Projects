"""
Builds a single self-contained HTML dashboard from the data GST Downloader v2
already saved (the per-GSTIN <FY>/json folder). No portal, no internet - it just
reads local files, so it opens instantly and can be shared as one .html file.

Use from the app (a "Build dashboard" button) or on its own:

    python dashboard.py "C:\\Users\\me\\Documents\\GST_Downloads\\37XXXX\\2025-26"
    python dashboard.py            # picks the most recently updated <FY> folder

It reads:  json/rolestatus.json, json/efiled.json, json/GSTR3B_*.json,
           json/GSTR1_summary_*.json, json/GSTR2B_*.json, json/GSTR9_*.json
and writes <GSTIN>_Dashboard_<FY>.html next to them.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

import compliance as comp
import reports as rp
import issues as iss
import ewaybill as ew
from portal_config import MONTHS, prd_label

# ---- GURU brand + validated dataviz palette tokens ----------------------------
BRAND = "#1F4E79"
C = {  # categorical slots (validated), status, chrome
    "s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a", "s4": "#eda100",
    "good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b",
    "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9",
    "surface": "#ffffff", "plane": "#f4f6f9", "border": "rgba(11,11,11,0.10)",
}
STATE_STATUS = {"Filed on time": "good", "Filed late": "warning",
                "Not filed - overdue": "critical", "Not yet due": "muted",
                "Pending": "warning", "Seen": "muted", "Closed": "good"}

# GURU firm mark: a meditating silhouette + wordmark (the firm's own branding).
LOGO_SVG = (
    '<svg class="logo" viewBox="0 0 40 40" width="34" height="34" aria-label="GURU">'
    '<circle cx="20" cy="9" r="4.4" fill="#9DC3E6"/>'
    '<path d="M20 14c-5 0-9 3.6-9 9 0 2.2 1.1 3.9 3 3.9h12c1.9 0 3-1.7 3-3.9 0-5.4-4-9-9-9z" fill="#9DC3E6"/>'
    '<path d="M11 26c-2.4 1-4 2.6-4 4.2 0 2 3 3 6 3m20-7.2c2.4 1 4 2.6 4 4.2 0 2-3 3-6 3" '
    'stroke="#9DC3E6" stroke-width="2.4" fill="none" stroke-linecap="round"/></svg>')

# Shared page CSS with light + dark tokens and a print layout. Roles are CSS vars so the
# dark theme swaps in one place; body background is explicit.
PAGE_CSS = """
:root{--brand:#1F4E79;--brand-ink:#9DC3E6;--surface:#ffffff;--plane:#f4f6f9;--ink:#0b0b0b;
 --ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--border:rgba(11,11,11,0.10);
 --good:#0ca30c;--warn:#fab219;--crit:#d03b3b;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;
 --row-warn:#FFF7E6;--row-crit:#FDECEC;color-scheme:light;}
:root[data-theme="dark"]{--surface:#1a1a19;--plane:#0d0d0d;--ink:#ffffff;--ink2:#c3c2b7;
 --muted:#898781;--grid:#2c2c2a;--border:rgba(255,255,255,0.12);--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;
 --row-warn:#3a3320;--row-crit:#3a2020;color-scheme:dark;}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--plane);color:var(--ink)}
header{background:var(--brand);color:#fff;padding:14px 24px;display:flex;align-items:center;gap:12px}
header .logo{flex:none}
header .tt{display:flex;flex-direction:column;line-height:1.15}
header .guru{color:var(--brand-ink);font-weight:800;font-size:20px;letter-spacing:1px}
header .sub{font-size:13px;opacity:.95}
header .meta{margin-left:auto;font-size:12.5px;opacity:.92;text-align:right}
header .tools{display:flex;gap:8px;margin-left:14px}
header button{background:rgba(255,255,255,.14);color:#fff;border:1px solid rgba(255,255,255,.3);
 border-radius:7px;padding:6px 11px;font-size:12px;cursor:pointer}
header button:hover{background:rgba(255,255,255,.26)}
main{max-width:1180px;margin:0 auto;padding:18px 24px 60px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:8px 0 18px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.kpi-t{font-size:12px;color:var(--ink2)} .kpi-v{font-size:25px;font-weight:700;margin-top:6px}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;margin-bottom:8px}
.chart{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.chart-h{font-size:14px;font-weight:600;margin-bottom:6px} .lgrow{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:6px}
.lg{font-size:12px;color:var(--ink2);display:flex;align-items:center;gap:6px}
.lg i{width:11px;height:11px;border-radius:3px;display:inline-block}
.donut-wrap{display:flex;gap:18px;align-items:center;flex-wrap:wrap} .donut-lg{display:flex;flex-direction:column;gap:6px}
section{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 18px;margin:16px 0}
h2{font-size:16px;color:var(--brand);margin:0 0 12px}
table.grid{border-collapse:collapse;width:100%;font-size:13px}
table.grid th{background:var(--brand);color:#fff;text-align:left;padding:7px 9px;position:sticky;top:0;font-weight:600}
table.grid td{padding:6px 9px;border-bottom:1px solid var(--grid);white-space:nowrap}
table.grid a{color:var(--s1);text-decoration:none;font-weight:600} table.grid a:hover{text-decoration:underline}
.tbl-wrap{max-height:460px;overflow:auto;border-radius:8px;border:1px solid var(--grid)}
tr.st-good td:nth-child(6){color:var(--good);font-weight:600}
tr.st-warning{background:var(--row-warn)} tr.st-critical{background:var(--row-crit)}
tr.st-muted td:nth-child(6){color:var(--muted)}
.yr-links{display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 8px}
.yr-link{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 14px;
 text-decoration:none;color:var(--brand);font-weight:600;font-size:13px}
.empty{color:var(--muted);font-size:13px}
.note{color:var(--muted);font-size:11px;margin-top:18px;line-height:1.5}
svg text{fill:var(--ink2)}
@media print{header{-webkit-print-color-adjust:exact;print-color-adjust:exact}
 header .tools{display:none} .tbl-wrap{max-height:none;overflow:visible} section{break-inside:avoid}}
"""

THEME_JS = """
<script>
(function(){try{var t=localStorage.getItem('guru-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();
function guruToggle(){var r=document.documentElement;var d=r.getAttribute('data-theme')==='dark'?'light':'dark';
 r.setAttribute('data-theme',d);try{localStorage.setItem('guru-theme',d);}catch(e){}}
</script>"""


def _page(title: str, subtitle: str, meta_html: str, body_html: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><style>{PAGE_CSS}</style>{THEME_JS}</head><body>
<header>{LOGO_SVG}<div class="tt"><span class="guru">GURU</span><span class="sub">{subtitle}</span></div>
<span class="meta">{meta_html}</span>
<span class="tools"><button onclick="guruToggle()">Dark / light</button>
<button onclick="window.print()">Save as PDF</button></span></header>
<main>{body_html}</main></body></html>"""


def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_notices(gstin_root: Path, fy: str | None = None):
    """Notices live once per GSTIN at <root>/json/notices.json."""
    p = gstin_root / "json" / "notices.json"
    if not p.exists():
        return pd.DataFrame(), {"total": 0, "pending": 0, "unread": 0, "orders": 0}
    d = _load_json(p) or {}
    df, summ = rp.notices_frame(d.get("notices") or [], d.get("cases") or [])
    if fy and not df.empty:
        df = df[df["FY"] == fy].reset_index(drop=True)
        summ = {"total": len(df), "pending": int((df["Status"] == "Pending").sum()) if not df.empty else 0,
                "unread": int((df["Read"] == "No").sum()) if not df.empty else 0,
                "orders": int((df["Type"] == "Order").sum()) if not df.empty else 0}
    return df, summ


def load_folder(folder: Path):
    """Read the json/ folder v2 saved and rebuild every dataframe."""
    j = folder / "json"
    if not j.exists():
        raise FileNotFoundError(f"No 'json' folder in {folder}. Run a download with v2 first.")
    gstin = ""
    fy = folder.name

    def collect(prefix):
        out = {}
        for f in sorted(j.glob(f"{prefix}*.json")):
            d = _load_json(f)
            if not d:
                continue
            # recover period code from label in filename, e.g. GSTR3B_2025-04.json
            lbl = f.stem.replace(prefix, "").lstrip("_")
            m = lbl.split("_")[0]
            if "-" in m and len(m) == 7:
                prd = m[5:] + m[:4]        # 2025-04 -> 042025
                out[prd] = d
        return out

    g3b = collect("GSTR3B")
    g1 = collect("GSTR1_summary")
    g2b = collect("GSTR2B")
    rolestatus = _load_json(j / "rolestatus.json") or {}
    efiled = _load_json(j / "efiled.json") or []
    g9 = None
    for f in j.glob("GSTR9_*.json"):
        g9 = _load_json(f)

    # GSTIN from any payload
    for src in (list(g3b.values()) + list(g1.values()) + [efiled]):
        try:
            if isinstance(src, dict):
                gstin = (src.get("data") or {}).get("gstin") or (src.get("data") or {}).get("r3b", {}).get("gstin") or gstin
            elif isinstance(src, list) and src:
                gstin = gstin
        except Exception:
            pass
    if not gstin:
        for v in rolestatus.values():
            gstin = ((v or {}).get("data") or {}).get("gstin", "") or gstin
    if not gstin and folder.parent:
        gstin = folder.parent.name

    # build frames via the tested modules
    g3_detail, g3_sum = rp.gstr3b_frames(g3b) if g3b else (pd.DataFrame(), pd.DataFrame())
    g1_long, g1_piv, g1_tot = rp.gstr1_frames(g1) if g1 else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    g2_sheets, g2_tot = rp.gstr2b_frames(g2b) if g2b else ({}, pd.DataFrame())

    nil_flags = {}
    if not g3_sum.empty:
        nil_flags.update({("GSTR-3B", r["Period"]): r["Nil return"] == "Yes" for _, r in g3_sum.iterrows()})
    for p, d in g1.items():
        nil_flags[("GSTR-1", prd_label(p))] = str((d.get("data") or {}).get("isnil", "")).upper() == "Y"

    status = comp.build_status(fy, rolestatus, efiled, gstin, None, nil_flags)
    recon = rp.reconciliation(g1_tot, g3_sum, g2_tot)
    notices_df, notices_summ = load_notices(folder.parent, fy)

    # e-way bills (from exports in <gstin_root>/ewb/), filtered to this FY
    ewb_df, ewb_an, ewb_summ, ewb_month, ewb_recon, ewb_party_recon = load_ewb(folder.parent, fy, g1_tot, folder)

    # pre-filing issues & risk analysis
    issues_df, issues_summ = iss.analyse_filing(fy, status, g3_sum, g1_tot, g2_tot, recon,
                                         g9json_for(folder), None, ewb_month)

    return {"gstin": gstin, "fy": fy, "g3_sum": g3_sum, "g1_tot": g1_tot, "g2_tot": g2_tot,
            "g2_sheets": g2_sheets, "status": status, "recon": recon, "summary": comp.summary(status),
            "notices": notices_df, "notices_summary": notices_summ, "gstin_root": folder.parent,
            "issues": issues_df, "issues_summary": issues_summ,
            "ewb": ewb_df, "ewb_analysis": ewb_an, "ewb_summary": ewb_summ, "ewb_recon": ewb_recon,
            "ewb_party_recon": ewb_party_recon}


def g9json_for(folder: Path):
    for f in (folder / "json").glob("GSTR9_*.json"):
        return _load_json(f)
    return None


def load_ewb(gstin_root: Path, fy: str, g1_tot, fy_folder=None):
    """Read every EWB export in <root>/ewb/, keep this FY's rows, analyse + reconcile
    (month-wise and party-wise vs GSTR-1 B2B)."""
    empty = (pd.DataFrame(), {}, {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    folder = Path(gstin_root) / "ewb"
    files = []
    if folder.exists():
        for ext in ("*.xlsx", "*.xls", "*.csv"):
            files += list(folder.glob(ext))
    if not files:
        return empty
    frames = []
    for f in files:
        try:
            frames.append(ew.load_export(f))
        except Exception:
            continue
    if not frames:
        return empty
    allrows = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["EWB no"])
    # restrict to the FY
    y0 = int(fy[:4])
    fy_periods = {f"{(y0 if m >= 4 else y0 + 1)}-{m:02d}" for m in list(range(4, 13)) + list(range(1, 4))}
    df = allrows[allrows["Period"].isin(fy_periods)].reset_index(drop=True)
    if df.empty:
        return df, {}, {"count": 0}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    an, summ = ew.analyse_ewb(df)
    month = ew.monthwise_outward(df)
    recon = ew.reconcile_with_gstr1(month, g1_tot)
    g1_b2b = rp.load_gstr1_b2b(fy_folder) if fy_folder else pd.DataFrame()
    party_recon = ew.reconcile_partywise_gstr1(ew.partywise_outward(df), g1_b2b)
    return df, an, summ, month, recon, party_recon


# ---- tiny HTML/SVG chart helpers (self-contained, no libraries) ---------------
def esc(x):
    return html.escape(str(x))


def _fmt(v, money=False):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, float):
        return f"{v:,.0f}" if money else f"{v:,.2f}"
    if hasattr(v, "strftime"):
        return v.strftime("%d-%m-%Y")
    return esc(v)


def grouped_bars(rows, series, title, height=230):
    """rows: list of (label, {series_key: value}). series: [(key,label,color)]."""
    if not rows:
        return ""
    maxv = max([max([r[1].get(s[0], 0) for s in series] + [0]) for r in rows] + [1])
    n = len(rows)
    W, H, padL, padB, padT = max(520, n * 74), height, 54, 34, 16
    plotH = H - padB - padT
    bw = min(20, (W - padL - 20) / (n * len(series) + n))
    gap = bw * 0.35
    group_w = len(series) * bw + (len(series) - 1) * 2
    step = (W - padL - 20) / n
    bars, xlabels, grid = [], [], []
    for gi in range(5):
        y = padT + plotH - plotH * gi / 4
        val = maxv * gi / 4
        grid.append(f'<line x1="{padL}" y1="{y:.1f}" x2="{W-10}" y2="{y:.1f}" stroke="{C["grid"]}" stroke-width="1"/>'
                    f'<text x="{padL-6}" y="{y+3:.1f}" text-anchor="end" font-size="9" fill="{C["muted"]}">{val:,.0f}</text>')
    for ri, (lab, vals) in enumerate(rows):
        gx = padL + ri * step + (step - group_w) / 2
        for si, (key, slabel, col) in enumerate(series):
            v = vals.get(key, 0) or 0
            bh = plotH * (v / maxv) if maxv else 0
            x = gx + si * (bw + 2)
            y = padT + plotH - bh
            bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="3" fill="{col}">'
                        f'<title>{esc(slabel)} {esc(lab)}: {v:,.2f}</title></rect>')
        xlabels.append(f'<text x="{padL + ri*step + step/2:.1f}" y="{H-padB+16}" text-anchor="middle" '
                       f'font-size="10" fill="{C["ink2"]}">{esc(lab)}</text>')
    legend = " ".join(f'<span class="lg"><i style="background:{c}"></i>{esc(l)}</span>' for _, l, c in series)
    return (f'<div class="chart"><div class="chart-h">{esc(title)}</div>'
            f'<div class="lgrow">{legend}</div>'
            f'<svg viewBox="0 0 {W} {H}" width="100%" preserveAspectRatio="xMidYMid meet" role="img">'
            f'{"".join(grid)}{"".join(bars)}{"".join(xlabels)}</svg></div>')


def donut(parts, title):
    """parts: [(label, value, color)]."""
    total = sum(v for _, v, _ in parts) or 1
    cx, cy, r, rin = 80, 80, 70, 44
    import math
    segs, acc = [], 0.0
    for lab, v, col in parts:
        if v <= 0:
            continue
        a0 = acc / total * 2 * math.pi - math.pi / 2
        acc += v
        a1 = acc / total * 2 * math.pi - math.pi / 2
        large = 1 if (a1 - a0) > math.pi else 0
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        xi0, yi0 = cx + rin * math.cos(a1), cy + rin * math.sin(a1)
        xi1, yi1 = cx + rin * math.cos(a0), cy + rin * math.sin(a0)
        segs.append(f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 {large} 1 {x1:.1f},{y1:.1f} '
                    f'L{xi0:.1f},{yi0:.1f} A{rin},{rin} 0 {large} 0 {xi1:.1f},{yi1:.1f} Z" fill="{col}">'
                    f'<title>{esc(lab)}: {int(v)}</title></path>')
    legend = "".join(f'<div class="lg"><i style="background:{c}"></i>{esc(l)} <b>{int(v)}</b></div>'
                     for l, v, c in parts if v > 0)
    return (f'<div class="chart"><div class="chart-h">{esc(title)}</div><div class="donut-wrap">'
            f'<svg viewBox="0 0 160 160" width="160" height="160" role="img">{"".join(segs)}'
            f'<text x="80" y="76" text-anchor="middle" font-size="22" font-weight="700" fill="{C["ink"]}">{int(total)}</text>'
            f'<text x="80" y="94" text-anchor="middle" font-size="10" fill="{C["muted"]}">returns</text></svg>'
            f'<div class="donut-lg">{legend}</div></div></div>')


def table(df: pd.DataFrame, status_col=None, money_cols=(), flag_col=None, raw_cols=()):
    """raw_cols: columns whose cell value is already HTML (not escaped)."""
    if df is None or df.empty:
        return '<p class="empty">No data.</p>'
    cols = list(df.columns)
    head = "".join(f"<th>{esc(c)}</th>" for c in cols)
    rows_html = []
    for _, r in df.iterrows():
        cls = ""
        if status_col and status_col in df:
            cls = "st-" + STATE_STATUS.get(r[status_col], "muted")
        if flag_col and flag_col in df and str(r[flag_col]) not in ("OK", "", "nan"):
            cls = "st-critical"
        tds = "".join((f"<td>{r[c]}</td>" if c in raw_cols else f"<td>{_fmt(r[c], money=(c in money_cols))}</td>")
                      for c in cols)
        rows_html.append(f'<tr class="{cls}">{tds}</tr>')
    return f'<table class="grid"><thead><tr>{head}</tr></thead><tbody>{"".join(rows_html)}</tbody></table>'


def _link_notice_pdfs(df: pd.DataFrame, gstin_root, rel_prefix: str = "") -> pd.DataFrame:
    """Add a 'PDF' column linking each notice to its saved file in <root>/Notices, if present."""
    df = df.copy()
    folder = Path(gstin_root) / "Notices" if gstin_root else None
    files = list(folder.glob("*")) if folder and folder.exists() else []

    def link(ref):
        ref = str(ref).replace("/", "_")
        for f in files:
            if ref and ref in f.name:
                href = f"{rel_prefix}Notices/{f.name}"
                return f'<a href="{esc(href)}" target="_blank">Open</a>'
        return "on portal"
    if "Reference" in df:
        df["PDF"] = df["Reference"].map(link)
    return df


def build_html(d: dict) -> str:
    s = d["summary"]
    status, recon = d["status"], d["recon"]
    g3, g1t, g2t = d["g3_sum"], d["g1_tot"], d["g2_tot"]
    gstin, fy = d["gstin"] or "GSTIN", d["fy"]
    score = s["score"]
    score_col = C["good"] if score >= 90 else (C["warning"] if score >= 70 else C["critical"])

    # KPI cards
    ns = d.get("notices_summary", {})
    isu = d.get("issues_summary", {})
    cards = [("Compliance score", f"{score}%", score_col), ("Returns due", s["due"], C["ink"]),
             ("Filed on time", s["on_time"], C["good"]), ("Filed late", s["late"], C["warning"]),
             ("Overdue / not filed", s["pending"], C["critical"]),
             ("Est. late fee (Rs)", f"{s['late_fee']:,.0f}", C["ink"]),
             ("Notices pending", ns.get("pending", 0), C["critical"] if ns.get("pending", 0) else C["ink"]),
             ("Issues (High)", isu.get("high", 0), C["critical"] if isu.get("high", 0) else C["ink"]),
             ("Mismatch exposure (Rs)", f"{isu.get('exposure', 0):,.0f}",
              C["critical"] if isu.get("exposure", 0) else C["ink"])]
    cards_html = "".join(
        f'<div class="kpi"><div class="kpi-t">{esc(t)}</div><div class="kpi-v" style="color:{col}">{esc(v)}</div></div>'
        for t, v, col in cards)

    # donut of filing status
    don = donut([("On time", s["on_time"], C["good"]), ("Late", s["late"], C["warning"]),
                 ("Overdue", s["pending"], C["critical"])], "Filing status (returns due)")

    # GSTR-1 vs 3B outward tax by month
    charts = [don]
    if recon is not None and not recon.empty and {"GSTR-1 tax", "Output tax 3.1(a)"} <= set(recon):
        rows = [(r["Period"][2:], {"g1": r.get("GSTR-1 tax", 0), "g3b": r.get("Output tax 3.1(a)", 0)})
                for _, r in recon.iterrows()]
        charts.append(grouped_bars(rows, [("g1", "GSTR-1 output tax", C["s1"]), ("g3b", "GSTR-3B output tax", C["s2"])],
                                   "Outward tax: GSTR-1 vs GSTR-3B"))
    if recon is not None and not recon.empty and {"2B ITC (excl. othersup)", "ITC available 4A"} <= set(recon):
        rows = [(r["Period"][2:], {"b2": r.get("2B ITC (excl. othersup)", 0), "b3": r.get("ITC available 4A", 0)})
                for _, r in recon.iterrows()]
        charts.append(grouped_bars(rows, [("b2", "GSTR-2B ITC", C["s3"]), ("b3", "GSTR-3B ITC claimed", C["s4"])],
                                   "ITC: GSTR-2B vs GSTR-3B claimed"))
    charts_html = "".join(charts)

    # tables
    status_show = status.copy() if status is not None and not status.empty else pd.DataFrame()
    if not status_show.empty:
        status_show = status_show[["Return", "Period", "Due date", "Filed on", "Days late", "Status", "Est. late fee", "ARN"]]
    grid = comp.month_grid(status) if status is not None and not status.empty else pd.DataFrame()

    # supplier-wise 2B (top 15 by tax)
    sup = d["g2_sheets"].get("2B_Supplierwise")
    sup_html = ""
    if sup is not None and not sup.empty:
        sup_html = ('<section><h2>Top suppliers (GSTR-2B)</h2>'
                    + table(sup.head(15), money_cols=[c for c in ("IGST", "CGST", "SGST", "Cess", "Total tax") if c in sup])
                    + "</section>")

    recon_html = ""
    if recon is not None and not recon.empty:
        money = [c for c in recon.columns if c not in ("Period", "Flag")]
        recon_html = ('<section><h2>Reconciliation</h2>'
                      + table(recon, money_cols=money, flag_col="Flag") + "</section>")

    notices_html = ""
    ndf = d.get("notices")
    if ndf is not None and not ndf.empty:
        ns = d.get("notices_summary", {})
        linked = _link_notice_pdfs(ndf.drop(columns=["FY"]), d.get("gstin_root"), rel_prefix="../")
        notices_html = (f'<section><h2>Notices &amp; orders this year '
                        f'<span style="font-weight:400;color:var(--ink2);font-size:13px">'
                        f'({ns.get("pending",0)} pending of {ns.get("total",0)})</span></h2>'
                        f'<div class="tbl-wrap">{table(linked, status_col="Status", raw_cols=["PDF"])}</div></section>')

    # pre-filing issues & risk
    issues_html = _issues_section(d.get("issues"), d.get("issues_summary", {}))
    # e-way bill analysis + reconciliation
    ewb_html = _ewb_section(d)

    gen = datetime.now().strftime("%d-%m-%Y %H:%M")
    meta = f'{esc(gstin)} &nbsp;|&nbsp; FY {esc(fy)} &nbsp;|&nbsp; generated {esc(gen)}'
    body = f"""
<div class="kpis">{cards_html}</div>
<div class="charts">{charts_html}</div>
{issues_html}
<section><h2>Return-wise status</h2><div class="tbl-wrap">{table(status_show, status_col="Status", money_cols=["Est. late fee"])}</div></section>
<section><h2>Month grid</h2>{table(grid)}</section>
{recon_html}
{ewb_html}
{notices_html}
{sup_html}
<p class="note">Built from data downloaded earlier by GST Downloader - this page does not connect to the GST portal.
Due dates and filing status are the portal's; late fee and interest are estimates. Run this before filing to clear
mismatches and avoid notices. Mogalapalli &amp; Co., Chartered Accountants.</p>"""
    return _page(f"GST Compliance - {gstin} - FY {fy}", "GST Compliance Dashboard", meta, body)


def _issues_section(issues_df, summ):
    if issues_df is None or issues_df.empty:
        return ('<section><h2>Pre-filing check &amp; risk analysis</h2>'
                f'<p class="empty" style="color:var(--good)">No issues detected in the data available. '
                'Run this again after preparing each period, before filing.</p></section>')
    sev = (f'<span style="color:var(--crit);font-weight:600">{summ.get("high",0)} high</span> &nbsp; '
           f'<span style="color:var(--warn);font-weight:600">{summ.get("medium",0)} medium</span> &nbsp; '
           f'<span style="color:var(--ink2)">{summ.get("low",0)} low</span> &nbsp;|&nbsp; '
           f'exposure Rs {summ.get("exposure",0):,.0f}')
    return (f'<section><h2>Pre-filing check &amp; risk analysis '
            f'<span style="font-weight:400;font-size:13px">({sev})</span></h2>'
            f'<div class="tbl-wrap">{_issue_table(issues_df)}</div>'
            f'<p class="note">Clear the high and medium items before filing to avoid notices. '
            f'Amounts are the tax or value at risk; interest is an estimate.</p></section>')


def _issue_table(df):
    sev_cls = {"High": "st-critical", "Medium": "st-warning", "Low": "", "Info": ""}
    cols = list(df.columns)
    head = "".join(f"<th>{esc(c)}</th>" for c in cols)
    rows = []
    for _, r in df.iterrows():
        cls = sev_cls.get(r.get("Severity", ""), "")
        tds = "".join(f"<td>{_fmt(r[c], money=(c == 'Amount (Rs)'))}</td>" for c in cols)
        rows.append(f'<tr class="{cls}">{tds}</tr>')
    return f'<table class="grid"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def _ewb_section(d):
    an = d.get("ewb_analysis") or {}
    summ = d.get("ewb_summary") or {}
    recon = d.get("ewb_recon")
    if not an and (recon is None or recon.empty):
        return ('<section><h2>E-way bills</h2><p class="empty">No e-way bill export loaded. '
                'Download "EWB generated by me" from the e-way bill portal (Reports) and add it in the app '
                'to see customer-wise and type-wise analysis and a reconciliation with GSTR-1.</p></section>')
    parts = ['<section><h2>E-way bill analysis '
             f'<span style="font-weight:400;font-size:13px">({summ.get("count",0)} e-way bills, '
             f'Rs {summ.get("value",0):,.0f}, {summ.get("cancelled",0)} cancelled, '
             f'{summ.get("customers",0)} customers)</span></h2>']
    if recon is not None and not recon.empty:
        parts.append('<h3 style="font-size:14px;color:var(--brand);margin:6px 0">E-way bills vs GSTR-1 (by month)</h3>'
                     + f'<div class="tbl-wrap">{table(recon, money_cols=["EWB taxable value","GSTR-1 taxable value","Difference (EWB - GSTR-1)"], flag_col="Flag")}</div>')
    # party-wise (recipient-GSTIN) EWB vs GSTR-1 B2B
    precon = d.get("ewb_party_recon")
    if precon is not None and not precon.empty:
        ps = ew.partywise_summary(precon)
        parts.append('<h3 style="font-size:14px;color:var(--brand);margin:12px 0 4px">'
                     'E-way bills vs GSTR-1 B2B (party-wise, recipient GSTIN)</h3>'
                     f'<p class="empty" style="margin:0 0 6px">{ps["parties"]} parties &middot; '
                     f'{ps["matched"]} match &middot; {ps["mismatch"]} value mismatch &middot; '
                     f'{ps["ewb_only"]} in EWB not in GSTR-1 &middot; {ps["gstr1_only"]} in GSTR-1 with no EWB. '
                     f'EWB Rs {ps["ewb_total"]:,.0f} vs GSTR-1 B2B Rs {ps["gstr1_total"]:,.0f}.</p>'
                     f'<div class="tbl-wrap">{table(precon.head(200), money_cols=["EWB taxable value","GSTR-1 taxable value","Difference (EWB - GSTR-1)"], flag_col="Flag")}</div>')
    elif (recon is not None and not recon.empty):
        parts.append('<p class="empty" style="margin:8px 0">Party-wise reconciliation with GSTR-1 B2B needs the '
                     'GSTR-1 full JSON - tick "GSTR-1 full JSON" in the app and collect it (the portal prepares it '
                     'in ~20 min), then rebuild.</p>')
    labels = [("By customer", "Customer-wise"), ("By document type", "Document type"),
              ("By supply type", "Supply type"), ("By transaction type", "Transaction type"),
              ("By status", "Status (incl. cancelled)"), ("By HSN", "HSN-wise (top 50)"),
              ("By transporter", "Transporter-wise"), ("By month", "Month-wise")]
    money = ["Taxable value", "IGST", "CGST", "SGST", "Cess", "Total tax"]
    for key, title in labels:
        t = an.get(key)
        if t is not None and not t.empty:
            parts.append(f'<h3 style="font-size:14px;color:var(--brand);margin:10px 0 4px">{esc(title)}</h3>'
                         + f'<div class="tbl-wrap">{table(t.head(50), money_cols=[c for c in money if c in t])}</div>')
    parts.append("</section>")
    return "".join(parts)


def find_latest_fy_folder(root: Path):
    cands = [p for p in root.rglob("json") if p.is_dir()]
    cands = [p.parent for p in cands]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def generate(folder: Path) -> Path:
    d = load_folder(folder)
    out = folder / f"{d['gstin'] or 'GSTIN'}_Dashboard_{d['fy']}.html"
    out.write_text(build_html(d), encoding="utf-8")
    return out


# ---- multi-year overview across all FY folders under one GSTIN ----------------
def _fy_sort_key(name):
    try:
        return int(name[:4])
    except Exception:
        return -1


def build_overview_html(gstin: str, years: list[dict], notices_df, notices_summ, gstin_root=None) -> str:
    gen = datetime.now().strftime("%d-%m-%Y %H:%M")
    gstin = gstin or "GSTIN"
    # year-comparison bars: compliance score + late fee
    score_rows = [(y["fy"], {"score": y["summary"]["score"]}) for y in years]
    fee_rows = [(y["fy"], {"fee": y["summary"]["late_fee"]}) for y in years]
    pend_rows = [(y["fy"], {"p": y["summary"]["pending"], "l": y["summary"]["late"]}) for y in years]
    charts = grouped_bars(score_rows, [("score", "Compliance score %", C["s1"])], "Compliance score by year", 200) \
        + grouped_bars(fee_rows, [("fee", "Est. late fee (Rs)", C["s2"])], "Estimated late fee by year", 200) \
        + grouped_bars(pend_rows, [("p", "Overdue / not filed", C["critical"]), ("l", "Filed late", C["warning"])],
                       "Defaults by year", 200)

    # per-year summary table
    srows = []
    for y in years:
        su = y["summary"]
        srows.append({"FY": y["fy"], "Returns due": su["due"], "On time": su["on_time"], "Late": su["late"],
                      "Overdue": su["pending"], "Score %": su["score"], "Est. late fee": float(su["late_fee"])})
    sdf = pd.DataFrame(srows)
    tot = {"FY": "TOTAL", "Returns due": sdf["Returns due"].sum(), "On time": sdf["On time"].sum(),
           "Late": sdf["Late"].sum(), "Overdue": sdf["Overdue"].sum(),
           "Score %": int(round(sdf["Score %"].mean())) if len(sdf) else 0, "Est. late fee": sdf["Est. late fee"].sum()}
    sdf = pd.concat([sdf, pd.DataFrame([tot])], ignore_index=True)

    links = " ".join(
        f'<a class="yr-link" href="{esc(y["fy"])}/{esc(y["html"].name)}">FY {esc(y["fy"])} &rarr;</a>'
        for y in years if y.get("html"))

    notices_block = ""
    if notices_df is not None and not notices_df.empty:
        linked = _link_notice_pdfs(notices_df, gstin_root, rel_prefix="")
        notices_block = (f'<section><h2>Notices &amp; orders - all years '
                         f'<span style="font-weight:400;color:var(--ink2);font-size:13px">'
                         f'({notices_summ.get("pending",0)} pending of {notices_summ.get("total",0)}, '
                         f'{notices_summ.get("orders",0)} orders)</span></h2>'
                         f'<div class="tbl-wrap">{table(linked, status_col="Status", raw_cols=["PDF"])}</div></section>')

    total_pending = notices_summ.get("pending", 0)
    high_all = sum(y.get("issues_summary", {}).get("high", 0) for y in years)
    expo_all = sum(y.get("issues_summary", {}).get("exposure", 0) for y in years)
    cards = [("Years covered", len(years), C["ink"]),
             ("Returns due (all)", int(tot["Returns due"]), C["ink"]),
             ("Avg score", f"{tot['Score %']}%", C["good"] if tot["Score %"] >= 90 else (C["warning"] if tot["Score %"] >= 70 else C["critical"])),
             ("Overdue (all)", int(tot["Overdue"]), C["critical"]),
             ("Est. late fee (all)", f"{tot['Est. late fee']:,.0f}", C["ink"]),
             ("Notices pending", total_pending, C["critical"] if total_pending else C["ink"]),
             ("Issues (High)", high_all, C["critical"] if high_all else C["ink"]),
             ("Mismatch exposure", f"{expo_all:,.0f}", C["critical"] if expo_all else C["ink"])]
    cards_html = "".join(f'<div class="kpi"><div class="kpi-t">{esc(t)}</div>'
                         f'<div class="kpi-v" style="color:{col}">{esc(v)}</div></div>' for t, v, col in cards)
    # combined issues across years (high + medium first)
    issue_frames = [y["issues"] for y in years if y.get("issues") is not None]
    issues_block = ""
    if issue_frames:
        allium = pd.concat(issue_frames, ignore_index=True)
        order = {"High": 0, "Medium": 1, "Low": 2, "Info": 3}
        allium["_o"] = allium["Severity"].map(order).fillna(9)
        allium = allium.sort_values(["_o", "FY"]).drop(columns="_o")
        cols = ["Severity", "FY", "Area", "Period", "Issue", "Detail", "Amount (Rs)", "Reference", "Action"]
        allium = allium[[c for c in cols if c in allium.columns]]
        issues_block = (f'<section><h2>Pre-filing issues - all years '
                        f'<span style="font-weight:400;font-size:13px">({high_all} high, exposure Rs {expo_all:,.0f})</span></h2>'
                        f'<div class="tbl-wrap">{_issue_table(allium)}</div></section>')
    body = f"""
<div class="kpis">{cards_html}</div>
<div class="yr-links">{links}</div>
<div class="charts">{charts}</div>
<section><h2>Year-by-year summary</h2>{table(sdf, money_cols=["Est. late fee"])}</section>
{issues_block}
{notices_block}
<p class="note">Built from data downloaded earlier by GST Downloader - this page does not connect to the GST portal.
Click a year above to open its detailed dashboard. Late fee is an estimate and excludes interest u/s 50.
Mogalapalli &amp; Co., Chartered Accountants.</p>"""
    return _page(f"GST Compliance Overview - {gstin}", "GST Compliance - multi-year overview",
                 f'{esc(gstin)} &nbsp;|&nbsp; generated {esc(gen)}', body)


def generate_overview(gstin_root: Path):
    """Build per-year dashboards (if missing) and one overview page across all FY folders."""
    fy_folders = sorted([p.parent for p in gstin_root.glob("*/json") if p.is_dir()],
                        key=lambda p: _fy_sort_key(p.name), reverse=True)
    if not fy_folders:
        return None
    years, gstin = [], gstin_root.name
    for folder in fy_folders:
        try:
            d = load_folder(folder)
        except Exception:
            continue
        gstin = d["gstin"] or gstin
        html_path = folder / f"{d['gstin'] or 'GSTIN'}_Dashboard_{d['fy']}.html"
        try:
            html_path.write_text(build_html(d), encoding="utf-8")
        except Exception:
            html_path = None
        idf = d.get("issues")
        years.append({"fy": d["fy"], "summary": {**d["summary"],
                      "pending_notices": d.get("notices_summary", {}).get("pending", 0)},
                      "issues_summary": d.get("issues_summary", {}),
                      "issues": idf.assign(FY=d["fy"]) if idf is not None and not idf.empty else None,
                      "html": html_path})
    if not years:
        return None
    notices_df, notices_summ = load_notices(gstin_root)
    out = gstin_root / f"{gstin}_Overview.html"
    out.write_text(build_overview_html(gstin, years, notices_df, notices_summ, gstin_root), encoding="utf-8")
    return out


# ---- firm-wide portfolio across every GSTIN folder under the downloads root ----
def generate_portfolio(root: Path):
    """One firm-level page across all GSTINs: who has overdue returns, pending notices, exposure."""
    gstin_dirs = sorted([p for p in root.iterdir() if p.is_dir() and any(p.glob("*/json"))]) if root.exists() else []
    if not gstin_dirs:
        return None
    rows, tot = [], {"due": 0, "overdue": 0, "late": 0, "fee": 0.0, "pending_notices": 0}
    clients = []
    for g in gstin_dirs:
        gstin = g.name
        fy_folders = sorted([p.parent for p in g.glob("*/json")], key=lambda p: _fy_sort_key(p.name), reverse=True)
        agg = {"due": 0, "on_time": 0, "late": 0, "overdue": 0, "fee": 0.0, "years": 0, "scores": [],
               "high": 0, "expo": 0.0}
        for folder in fy_folders:
            try:
                d = load_folder(folder)
            except Exception:
                continue
            su = d["summary"]
            agg["due"] += su["due"]; agg["on_time"] += su["on_time"]; agg["late"] += su["late"]
            agg["overdue"] += su["pending"]; agg["fee"] += su["late_fee"]; agg["years"] += 1
            agg["scores"].append(su["score"])
            isu = d.get("issues_summary", {})
            agg["high"] += isu.get("high", 0); agg["expo"] += isu.get("exposure", 0)
        ov = generate_overview(g)   # also refreshes per-year + overview for drill-down
        nts = load_notices(g)[1]
        score = int(round(sum(agg["scores"]) / len(agg["scores"]))) if agg["scores"] else 0
        link = f'<a href="{esc(g.name)}/{esc(ov.name)}" target="_blank">open</a>' if ov else ""
        rows.append({"GSTIN": gstin, "Years": agg["years"], "Returns due": agg["due"],
                     "Overdue": agg["overdue"], "Late": agg["late"], "Issues (High)": agg["high"],
                     "Mismatch exposure": agg["expo"], "Score %": score,
                     "Est. late fee": agg["fee"], "Notices pending": nts.get("pending", 0), "Dashboard": link})
        tot["due"] += agg["due"]; tot["overdue"] += agg["overdue"]; tot["late"] += agg["late"]
        tot["fee"] += agg["fee"]; tot["pending_notices"] += nts.get("pending", 0)
        tot.setdefault("high", 0); tot.setdefault("expo", 0.0)
        tot["high"] += agg["high"]; tot["expo"] += agg["expo"]
        clients.append(score)
    df = pd.DataFrame(rows).sort_values(["Overdue", "Notices pending"], ascending=False).reset_index(drop=True)
    avg = int(round(sum(clients) / len(clients))) if clients else 0

    df = df.sort_values(["Issues (High)", "Overdue", "Notices pending"], ascending=False).reset_index(drop=True)
    cards = [("Clients", len(rows), C["ink"]),
             ("Avg score", f"{avg}%", C["good"] if avg >= 90 else (C["warning"] if avg >= 70 else C["critical"])),
             ("Issues (High)", int(tot.get("high", 0)), C["critical"] if tot.get("high", 0) else C["ink"]),
             ("Returns overdue", int(tot["overdue"]), C["critical"]),
             ("Notices pending", int(tot["pending_notices"]), C["critical"] if tot["pending_notices"] else C["ink"]),
             ("Mismatch exposure", f"{tot.get('expo', 0):,.0f}", C["critical"] if tot.get("expo", 0) else C["ink"]),
             ("Est. late fee (all)", f"{tot['fee']:,.0f}", C["ink"])]
    cards_html = "".join(f'<div class="kpi"><div class="kpi-t">{esc(t)}</div>'
                         f'<div class="kpi-v" style="color:{col}">{esc(v)}</div></div>' for t, v, col in cards)
    # attention list: clients with high issues, overdue, or pending notices
    att = df[(df["Issues (High)"] > 0) | (df["Overdue"] > 0) | (df["Notices pending"] > 0)]
    att_rows = [(r["GSTIN"], {"i": r["Issues (High)"], "o": r["Overdue"], "n": r["Notices pending"]})
                for _, r in att.head(12).iterrows()]
    chart = grouped_bars(att_rows, [("i", "Issues (High)", C["critical"]), ("o", "Returns overdue", C["s2"]),
                         ("n", "Notices pending", C["s4"])], "Needs attention (by client)", 230) if att_rows else ""
    gen = datetime.now().strftime("%d-%m-%Y %H:%M")
    body = f"""
<div class="kpis">{cards_html}</div>
<div class="charts">{chart}</div>
<section><h2>All clients</h2><div class="tbl-wrap">{table(df, money_cols=["Est. late fee", "Mismatch exposure"], raw_cols=["Dashboard"])}</div></section>
<p class="note">Firm-wide view across every GSTIN downloaded under this folder. Click a client to open its multi-year
dashboard. Sorted by high issues, then returns overdue. Built offline from saved data.
Mogalapalli &amp; Co., Chartered Accountants.</p>"""
    out = root / "Firm_Portfolio.html"
    out.write_text(_page("GST Firm Portfolio", "GST Compliance - firm portfolio",
                         f"{len(rows)} client(s) &nbsp;|&nbsp; generated {esc(gen)}", body), encoding="utf-8")
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
    else:
        root = Path.home() / "Documents" / "GST_Downloads"
        folder = find_latest_fy_folder(root)
        if not folder:
            print(f"No downloaded data found under {root}. Run GST Downloader first.")
            sys.exit(1)
    out = generate(folder)
    print(f"Dashboard written: {out}")
    try:
        import webbrowser
        webbrowser.open(out.as_uri())
    except Exception:
        pass
