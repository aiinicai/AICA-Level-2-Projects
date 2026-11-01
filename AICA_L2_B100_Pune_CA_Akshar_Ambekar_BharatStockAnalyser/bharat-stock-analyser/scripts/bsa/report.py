"""Self-contained HTML research note (charts embedded) and optional PDF via headless Chrome."""

from __future__ import annotations

import base64
import html
import shutil
import subprocess
from pathlib import Path

from .fmt import fmt_cr, fmt_num, fmt_pct, fmt_rs, fmt_x

E = html.escape

RATING_STYLE = {"BUY": ("good", "&#9650;"), "HOLD": ("warn", "&#9670;"), "SELL": ("crit", "&#9660;")}

CSS = """
:root{--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--line:#e6e5e0;--panel:#f7f7f5;--paper:#ffffff;
--navy:#0f2a44;--accent:#2a78d6;--good:#0ca30c;--warn:#fab219;--crit:#d03b3b;color-scheme:light}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;background:#eceae5;color:var(--ink);font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",
"Helvetica Neue",Arial,sans-serif;font-variant-numeric:tabular-nums}
.page{max-width:1040px;margin:24px auto;background:var(--paper);box-shadow:0 1px 3px rgba(0,0,0,.08)}
.masthead{display:flex;justify-content:space-between;align-items:flex-end;background:var(--navy);color:#fff;
padding:14px 28px}
.brand{font-weight:700;font-size:15px;letter-spacing:.02em}
.brand span{display:block;font-weight:400;font-size:11px;opacity:.75;letter-spacing:.04em;text-transform:uppercase}
.dateline{text-align:right;font-size:11px;opacity:.85}
.hero{display:flex;gap:24px;justify-content:space-between;align-items:stretch;padding:22px 28px 14px;
border-bottom:1px solid var(--line)}
.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink2)}
h1{font-size:28px;line-height:1.15;margin:4px 0 4px}
.ticker{font-size:12px;color:var(--ink2)}
.headline{font-size:16px;font-weight:600;margin:12px 0 0;color:var(--navy)}
.rating-card{min-width:190px;border-radius:10px;padding:14px 18px;display:flex;flex-direction:column;
justify-content:center;text-align:center}
.rating-card.good{background:var(--good);color:#fff}
.rating-card.warn{background:var(--warn);color:#3b2a00}
.rating-card.crit{background:var(--crit);color:#fff}
.rating-label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;opacity:.9}
.rating-value{font-size:30px;font-weight:800;letter-spacing:.04em;line-height:1.2}
.conv{font-size:12px;opacity:.95}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);border-bottom:1px solid var(--line)}
.kpi{padding:12px 16px;border-right:1px solid var(--line)}
.kpi:last-child{border-right:0}
.kpi .k{font-size:10.5px;color:var(--ink2);text-transform:uppercase;letter-spacing:.05em}
.kpi .v{font-size:19px;font-weight:700;margin-top:2px}
.kpi .s{font-size:11px;color:var(--muted)}
.pos{color:#0a7d0a}.neg{color:#b42f2f}
.layout{display:grid;grid-template-columns:1fr 300px;gap:0}
main{padding:18px 28px;border-right:1px solid var(--line);min-width:0}
aside{padding:18px 20px;background:var(--panel)}
h2{font-size:15px;margin:18px 0 8px;color:var(--navy);border-bottom:2px solid var(--navy);padding-bottom:4px}
main h2:first-child{margin-top:0}
h3{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--navy);margin:16px 0 6px}
aside h3:first-child{margin-top:0}
p{margin:0 0 10px}
ul.bul{margin:0 0 10px;padding-left:18px}ul.bul li{margin:0 0 6px}
ul.bul.plus li::marker{content:"+  ";color:var(--good);font-weight:700}
ul.bul.minus li::marker{content:"-  ";color:var(--crit);font-weight:700}
.tag{display:inline-block;font-size:10px;text-transform:uppercase;letter-spacing:.06em;background:#e7f0fb;
color:#1c5cab;border-radius:4px;padding:1px 6px;margin-left:6px;vertical-align:middle}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child,th.l,td.l{text-align:left;white-space:normal}
thead th{background:var(--navy);color:#fff;font-weight:600;font-size:11px}
tbody tr.sub td{color:var(--ink2);font-style:italic}
tbody tr.hl td{background:#eef5fd;font-weight:600}
tbody tr.strong td{font-weight:700}
.kv td{padding:4px 2px;font-size:12px}.kv td:first-child{color:var(--ink2)}
.section{padding:6px 28px 14px;border-top:1px solid var(--line)}
.exhibit{margin:14px 0 6px;break-inside:avoid}
.exhibit .cap{font-weight:700;font-size:12.5px;margin-bottom:6px}
.exhibit .src{font-size:10.5px;color:var(--muted);margin-top:4px}
.exhibit img{width:100%;height:auto;display:block}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.bar{height:8px;background:#e6e5e0;border-radius:4px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--accent);border-radius:4px}
.score-row{display:grid;grid-template-columns:1fr 34px;gap:6px;align-items:center;margin:5px 0;font-size:12px}
.score-row .lbl{display:flex;justify-content:space-between}
.sig-Bullish{color:#0a7d0a;font-weight:600}.sig-Bearish{color:#b42f2f;font-weight:600}
.sig-Caution,.sig-Watch{color:#9a6500;font-weight:600}
.note{font-size:11.5px;color:var(--ink2)}
.callout{background:var(--panel);border-left:3px solid var(--accent);padding:10px 14px;margin:10px 0}
.callout.warnbox{background:#fff7e0;border-left-color:var(--warn)}
.callout.warnbox ul{margin:6px 0 0}
.prov{display:inline-block;margin-top:4px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
background:rgba(0,0,0,.18);border-radius:4px;padding:1px 8px}
.disclaimer{font-size:10.5px;color:var(--ink2);line-height:1.45}
.ratingkey{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 10px}
.ratingkey span{padding:3px 10px;border-radius:4px;font-size:11.5px;font-weight:600}
.rk-good{background:var(--good);color:#fff}.rk-warn{background:var(--warn);color:#3b2a00}
.rk-crit{background:var(--crit);color:#fff}
footer{padding:12px 28px;background:var(--navy);color:#fff;font-size:11px;display:flex;justify-content:space-between}
a{color:#1c5cab}
@media (max-width:760px){
 .page{margin:0}.hero{flex-direction:column;padding:16px}.layout{grid-template-columns:1fr}
 main{border-right:0;padding:16px}aside{padding:16px}.kpis{grid-template-columns:repeat(2,1fr)}
 .kpi{border-bottom:1px solid var(--line)}.section{padding:6px 16px 12px}.grid2{grid-template-columns:1fr}
 .masthead{padding:12px 16px}.tablewrap{overflow-x:auto}h1{font-size:23px}footer{padding:12px 16px}
}
@page{size:A4;margin:9mm}
@media print{
 body{background:#fff;font-size:10.5px}.page{margin:0;box-shadow:none;max-width:none}
 table{font-size:10px}th,td{padding:3px 6px}.kpi .v{font-size:16px}h1{font-size:24px}
 .section{break-inside:auto}.pb{break-before:page}
}
"""


def _img(out: Path, rel: str | None) -> str:
    if not rel:
        return ""
    p = out / rel
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b64}" alt="">'


class _Ex:
    def __init__(self):
        self.n = 0

    def __call__(self, title: str, body: str, source: str = "Yahoo Finance; Bharat Stock Analyser") -> str:
        self.n += 1
        return (f'<div class="exhibit"><div class="cap">Exhibit {self.n}: {E(title)}</div>{body}'
                f'<div class="src">Source: {E(source)}</div></div>')


def _sign_cls(v) -> str:
    if v is None:
        return ""
    return "pos" if v > 0 else ("neg" if v < 0 else "")


def _table(head: list[str], rows: list[list[str]], classes: list[str] | None = None,
           left: tuple[int, ...] = ()) -> str:
    """Numeric table. Column 0 and any column index in `left` are left-aligned text."""
    def al(j):
        return ' class="l"' if j in left else ""

    th = "".join(f"<th{al(j)}>{E(h)}</th>" for j, h in enumerate(head))
    body = []
    for i, r in enumerate(rows):
        cls = f' class="{classes[i]}"' if classes and classes[i] else ""
        body.append(f"<tr{cls}>" + "".join(f"<td{al(j)}>{c}</td>" for j, c in enumerate(r)) + "</tr>")
    return f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _series_rows(annual: list[dict], spec: list[tuple]) -> tuple[list[list[str]], list[str]]:
    rows, cls = [], []
    for item in spec:
        label, key, kind = item[:3]
        style = item[3] if len(item) > 3 else ""
        vals = [r.get(key) for r in annual]
        if all(v is None for v in vals) or (key == "one_off" and not any(vals)):
            continue
        if kind == "cr":
            cells = [fmt_cr(v) for v in vals]
        elif kind == "pct":
            cells = [fmt_pct(v) for v in vals]
        elif kind == "x":
            cells = [fmt_x(v, 2) for v in vals]
        elif kind == "x1":
            cells = [fmt_x(v, 1) for v in vals]
        elif kind == "days":
            cells = [fmt_num(v, 0) for v in vals]
        else:
            cells = [fmt_num(v, 2) for v in vals]
        rows.append([E(label)] + cells)
        cls.append(style)
    return rows, cls


def render(a: dict, out: Path) -> str:
    m, p, v, r, sc, f, t = (a["meta"], a["price"], a["valuation"], a["rating"], a["scorecard"], a["fundamentals"],
                            a["technical"])
    c = a.get("commentary") or {}
    nar = a["narrative"]
    ch = a.get("charts", {})
    ex = _Ex()
    fin = m["is_financial"]
    cls, icon = RATING_STYLE.get(r["rating"], ("warn", ""))
    up = v.get("upside")

    # ---------- hero and KPIs ----------
    headline = c.get("headline") or nar["headline"]
    cons = v["consensus"]
    kpis = [
        ("Current price", fmt_rs(p["cmp"]), f"{fmt_pct(p.get('day_change'), 2, signed=True)} on the day"
         if p.get("day_change") is not None else m["price_date"]),
        ("12-month target", fmt_rs(v.get("target")), f"{v['methods_used']} method(s) blended"),
        ("Upside / downside", f'<span class="{_sign_cls(up)}">{fmt_pct(up, signed=True)}</span>', "to target"),
        ("Composite score", f"{fmt_num(sc.get('composite'), 0)}<small>/100</small>", "six pillars"),
        ("Market cap", f"Rs {fmt_cr(p.get('market_cap'), 0)} cr", m["exchange"] + " listed"),
        ("Street view", E(cons.get("view") or "-"), f"{cons.get('analysts') or 0} analysts"),
    ]
    kpi_html = "".join(f'<div class="kpi"><div class="k">{k}</div><div class="v">{val}</div><div class="s">{s}</div>'
                       f"</div>" for k, val, s in kpis)

    # ---------- main column ----------
    main = []
    if r.get("provisional"):
        main.append("<div class='callout warnbox'><b>Provisional rating.</b> Do not act on this rating until these "
                    "points are resolved:<ul class='bul'>" +
                    "".join(f"<li>{E(x)}</li>" for x in r.get("provisional_reasons", [])) + "</ul></div>")
    main.append("<h2>Summary</h2>")
    if c.get("summary"):
        main.append(f"<p>{E(c['summary'])}<span class='tag'>Analyst view</span></p>")
    main.append(f"<p>{E(nar['summary'])}<span class='tag'>Model</span></p>")
    if c.get("highlights"):
        main.append("<h2>Key highlights</h2><ul class='bul'>" +
                    "".join(f"<li>{E(x)}</li>" for x in c["highlights"]) + "</ul>")
    main.append("<h2>Investment rationale (data-backed)</h2><ul class='bul plus'>" +
                ("".join(f"<li>{E(x)}</li>" for x in nar["positives"]) or "<li>No positive trigger fired.</li>") +
                "</ul>")
    risks = list(c.get("risks", []))
    main.append("<h2>Key risks and concerns</h2><ul class='bul minus'>" +
                "".join(f"<li>{E(x)}<span class='tag'>Analyst view</span></li>" for x in risks) +
                ("".join(f"<li>{E(x)}</li>" for x in nar["concerns"]) or
                 ("" if risks else "<li>No negative trigger fired.</li>")) + "</ul>")
    if c.get("catalysts"):
        main.append("<h2>Catalysts to watch</h2><ul class='bul'>" +
                    "".join(f"<li>{E(x)}</li>" for x in c["catalysts"]) + "</ul>")
    main.append("<h2>How the rating was reached</h2><ol class='bul'>" +
                "".join(f"<li>{E(x)}</li>" for x in r["trace"]) + "</ol>")
    biz = c.get("business") or m.get("business")
    if biz:
        if len(biz) > 900 and not c.get("business"):
            biz = biz[:900].rsplit(" ", 1)[0] + " ..."
        main.append(f"<h2>Company profile</h2><p class='note'>{E(biz)}</p>")

    # ---------- sidebar ----------
    kv = [
        ("NSE / BSE symbol", E(m["symbol"])),
        ("Sector", E(m.get("sector") or "-")),
        ("Peer group", E(m.get("peer_group") or "-")),
        ("Shares outstanding (cr)", fmt_num((p.get("shares") or 0) / 1e7, 1) if p.get("shares") else "-"),
        ("Market cap (Rs cr)", fmt_cr(p.get("market_cap"), 0)),
        ("3-m avg daily value (Rs cr)", fmt_cr(p.get("value_3m_avg"))),
        ("52-week high / low", f"{fmt_rs(p.get('high_52w'))} / {fmt_rs(p.get('low_52w'))}"),
        ("Beta vs Nifty (1 yr)", fmt_num(t.get("beta_1y"), 2)),
        ("Dividend yield", fmt_pct(v.get("dividend_yield"))),
        ("Nifty 50 / Sensex", f"{fmt_num(p.get('nifty'), 0)} / {fmt_num(p.get('sensex'), 0)}"),
    ]
    if m.get("bse_code"):
        kv.insert(1, ("BSE code", E(m["bse_code"])))
    meetings = (a.get("exchange") or {}).get("meetings") or {}
    if meetings.get("next"):
        kv.append(("Next results board meeting", E(meetings["next"]["date"])))
    elif meetings.get("last"):
        kv.append(("Last results board meeting", E(meetings["last"]["date"])))
    side = ["<h3>Key stock data</h3><table class='kv'>" +
            "".join(f"<tr><td>{k}</td><td>{val}</td></tr>" for k, val in kv) + "</table>"]
    sr, br = t.get("returns", {}), t.get("bench_returns", {})
    perf_rows = []
    for k, lab in (("1m", "1 month"), ("3m", "3 months"), ("6m", "6 months"), ("1y", "12 months"),
                   ("3y", "3 years")):
        a_ = sr.get(k)
        rel = a_ - br[k] if a_ is not None and br.get(k) is not None else None
        perf_rows.append([lab, f'<span class="{_sign_cls(a_)}">{fmt_pct(a_)}</span>',
                          f'<span class="{_sign_cls(rel)}">{fmt_pct(rel)}</span>'])
    side.append("<h3>Price performance (%)</h3>" + _table(["Period", "Absolute", "Rel. to Nifty"], perf_rows))
    h = a["holdings"]
    if h.get("promoter") is not None:
        tr = h.get("promoter_trend") or []
        trend = (f" Promoter holding was {tr[0]['promoter']:.2f}% on {E(tr[0]['date'])}." if len(tr) >= 2 else "")
        side.append("<h3>Shareholding (%)</h3><table class='kv'>" +
                    f"<tr><td>Promoter and group</td><td>{fmt_num(h.get('promoter'), 2)}</td></tr>"
                    f"<tr><td>FII / FPI</td><td>{fmt_num(h.get('fii'), 2)}</td></tr>"
                    f"<tr><td>DII</td><td>{fmt_num(h.get('dii'), 2)}</td></tr>"
                    f"<tr><td>of which mutual funds</td><td>{fmt_num(h.get('mutual_funds'), 2)}</td></tr>"
                    f"<tr><td>Public and others</td><td>{fmt_num(h.get('public_other'), 2)}</td></tr>"
                    f"<tr><td>Promoter shares pledged</td><td>{fmt_num(h.get('pledged_pct_of_promoter'), 2)}</td></tr>"
                    "</table>"
                    f"<p class='note'>{E(h.get('source') or 'Exchange')} as of {E(h.get('as_of') or '-')}. Pledge is "
                    f"a share of the promoter holding.{trend}</p>")
    else:
        side.append("<h3>Shareholding (%)</h3><table class='kv'>" +
                    f"<tr><td>Promoters and insiders</td><td>{fmt_num(h.get('insiders'), 1)}</td></tr>"
                    f"<tr><td>Institutions (FII + DII)</td><td>{fmt_num(h.get('institutions'), 1)}</td></tr>"
                    f"<tr><td>Public and others</td><td>{fmt_num(h.get('public_other'), 1)}</td></tr></table>"
                    "<p class='note'>Source classification; check the latest exchange filing for the promoter "
                    "and pledge split.</p>")
    vs_cons = (v["target"] / cons["mean"] - 1) * 100 if v.get("target") and cons.get("mean") else None
    side.append("<h3>Our target vs street</h3><table class='kv'>"
                f"<tr><td>Our target</td><td>{fmt_rs(v.get('target'))}</td></tr>"
                f"<tr><td>Consensus mean</td><td>{fmt_rs(cons.get('mean'))}</td></tr>"
                f"<tr><td>Difference</td><td>{fmt_pct(vs_cons, signed=True)}</td></tr>"
                f"<tr><td>Consensus range</td><td>{fmt_rs(cons.get('low'))} to {fmt_rs(cons.get('high'))}</td></tr>"
                "</table>")
    side.append("<h3>Scorecard</h3>" + "".join(
        f"<div class='score-row'><div><div class='lbl'><span>{E(pl['pillar'])}</span></div>"
        f"<div class='bar'><i style='width:{pl['score'] or 0:.0f}%'></i></div></div>"
        f"<b>{fmt_num(pl['score'], 0)}</b></div>" for pl in sc["pillars"]))

    # ---------- sections ----------
    S = []

    # Price and relative performance
    sec = ["<h2>Price action</h2><div class='grid2'>"]
    sec.append(ex("Price with 50-day and 200-day moving averages (2 years)", _img(out, ch.get("price"))))
    sec.append(ex(f"12-month performance rebased to 100 vs Nifty 50{' and ' + m['sector_index'] if m.get('sector_index') else ''}",
                  _img(out, ch.get("relative"))))
    sec.append("</div>")
    S.append("".join(sec))

    # Quarterly
    qs = f["quarters"]
    qc = f["quarter_changes"]
    if qs:
        by_label = {q["label"]: q for q in qs}
        last_q = qs[-1]
        # Comparison quarters are matched by date in fundamentals; a missing quarter shows as unavailable.
        prev_q = by_label.get(qc.get("prev")) if "missing" in qc else (qs[-2] if len(qs) >= 2 else None)
        ya_q = by_label.get(qc.get("year_ago")) if "missing" in qc else (qs[-5] if len(qs) >= 5 else None)
        tail = [("Other income", "other_income", "cr"), ("One-off items, pre-tax (estimated)", "one_off", "cr"),
                ("PBT", "pbt", "cr"), ("Tax", "tax", "cr"), ("Net profit incl. minority interest", "pat_total", "cr"),
                ("Net profit to owners", "pat", "cr"), ("Net profit excl. one-offs", "pat_norm", "cr"),
                ("Net margin (%)", "pat_margin", "pct"), ("EPS excl. one-offs (Rs)", "eps_norm", "num")]
        if fin:
            items = [("Total income", "revenue", "cr"), ("Net interest income", "nii", "cr")] + tail
        else:
            items = [("Revenue", "revenue", "cr"), ("EBITDA (excl. other income)", "ebitda", "cr"),
                     ("EBITDA margin (%)", "ebitda_margin", "pct"), ("Depreciation", "depreciation", "cr"),
                     ("Interest", "interest", "cr")] + tail

        def change(cur, old, kind):
            if cur is None or old is None:
                return "-"
            if kind == "pct":  # margin change in basis points
                return fmt_num((cur - old) * 100, 0) + "bps"
            if old <= 0 or abs(cur / old - 1) > 5:  # changes above 500% carry no information
                return "n.m."
            return fmt_pct((cur / old - 1) * 100)

        rows = []
        for lab, k, kind in items:
            if last_q.get(k) is None:
                continue
            if k == "one_off" and not any(q.get("one_off") for q in (last_q, prev_q, ya_q) if q):
                continue
            if k == "pat_total" and last_q.get("pat_total") == last_q.get("pat"):
                continue
            fmtv = fmt_cr if kind == "cr" else (lambda x: fmt_num(x, 1)) if kind == "pct" else (lambda x: fmt_num(x, 2))
            rows.append([lab, fmtv(last_q[k]), fmtv(prev_q.get(k)) if prev_q else "-",
                         change(last_q[k], prev_q.get(k) if prev_q else None, kind),
                         fmtv(ya_q.get(k)) if ya_q else "-",
                         change(last_q[k], ya_q.get(k) if ya_q else None, kind)])
        head = ["Rs crore", last_q["label"], prev_q["label"] if prev_q else "Prev (n.a.)", "QoQ",
                ya_q["label"] if ya_q else "Year ago (n.a.)", "YoY"]
        qnote = ""
        if qc.get("missing"):
            qnote = (f"<p class='note'>The data source has no figures for {E(', '.join(qc['missing']))}. Comparisons "
                     "are matched by period end date, so a missing quarter shows as not available.</p>")
        by_source: dict[str, list[str]] = {}
        for q in qs:
            by_source.setdefault(q.get("source") or "Yahoo Finance", []).append(q["label"])
        q_src = "; ".join(dict.fromkeys(
            "NSE filings" if s.startswith("NSE") else s for s in by_source)) + "; Bharat Stock Analyser"
        if len(by_source) > 1 or "Yahoo Finance" not in by_source:
            def src_name(s):
                return f"NSE results filings ({s.split('(')[-1].rstrip(')')} XBRL)" if s.startswith("NSE filing") else s
            qnote += ("<p class='note'>Sources: " + "; ".join(
                f"{E(', '.join(labs))} from {E(src_name(src))}" for src, labs in by_source.items()) + ".</p>")
        sec = ["<h2>Quarterly performance</h2><div class='grid2'>",
               ex(f"Quarterly snapshot: {last_q['label']}", _table(head, rows) + qnote, q_src),
               ex("Revenue and net profit, last five quarters (Rs crore)", _img(out, ch.get("quarterly")), q_src),
               "</div>"]
        S.append("".join(sec))

    # Financial summary
    ann = f["annual"]
    if ann:
        years = [x["label"] for x in ann]
        if not fin:
            pl_spec = [("Revenue", "revenue", "cr", "strong"), ("Growth (%)", "revenue_growth", "pct", "sub"),
                       ("EBITDA (excl. other income)", "ebitda", "cr", "strong"),
                       ("EBITDA margin (%)", "ebitda_margin", "pct", "sub"),
                       ("Other income", "other_income", "cr"), ("Depreciation", "depreciation", "cr"),
                       ("EBIT", "ebit", "cr"), ("Interest", "interest", "cr"),
                       ("Profit before tax", "pbt", "cr"), ("Tax", "tax", "cr"),
                       ("Net profit incl. minority interest", "pat_total", "cr"),
                       ("Net profit to owners", "pat", "cr", "strong"), ("Growth (%)", "pat_growth", "pct", "sub"),
                       ("One-off items, pre-tax (estimated)", "one_off", "cr"),
                       ("Net profit excl. one-offs", "pat_norm", "cr"),
                       ("EPS reported (Rs)", "eps_adj", "num"), ("EPS excl. one-offs (Rs)", "eps_norm", "num"),
                       ("DPS (Rs)", "dps_adj", "num"), ("Dividend payout (%)", "payout", "pct")]
            bs_spec = [("Shareholders' funds", "equity", "cr", "strong"), ("Total debt", "total_debt", "cr"),
                       ("Cash and equivalents", "cash", "cr"), ("Net debt", "net_debt", "cr", "strong"),
                       ("Current liabilities", "current_liabilities", "cr"),
                       ("Capital employed", "capital_employed", "cr"), ("Inventories", "inventory", "cr"),
                       ("Receivables", "receivables", "cr"), ("Payables", "payables", "cr"),
                       ("Total assets", "total_assets", "cr", "strong")]
            ratio_spec = [("Return on equity (%)", "roe", "pct"), ("Return on capital employed (%)", "roce", "pct"),
                          ("Return on assets (%)", "roa", "pct"), ("Net margin (%)", "pat_margin", "pct"),
                          ("Asset turnover (x)", "asset_turnover", "x"), ("Leverage factor (x)", "leverage", "x"),
                          ("Net debt / equity (x)", "net_debt_equity", "x"),
                          ("Interest cover (x)", "interest_cover", "x1"), ("CFO / net profit (x)", "cfo_to_pat", "x"),
                          ("Inventory days", "inventory_days", "days"), ("Receivable days", "receivable_days", "days"),
                          ("Payable days", "payable_days", "days"), ("Book value per share (Rs)", "bvps_adj", "num"),
                          ("FY-end P/E excl. one-offs (x)", "pe", "x1"), ("FY-end P/B (x)", "pb", "x")]
        else:
            pl_spec = [("Total income", "revenue", "cr", "strong"), ("Growth (%)", "revenue_growth", "pct", "sub"),
                       ("Net interest income", "nii", "cr"), ("Profit before tax", "pbt", "cr"), ("Tax", "tax", "cr"),
                       ("Net profit to owners", "pat", "cr", "strong"), ("Growth (%)", "pat_growth", "pct", "sub"),
                       ("One-off items, pre-tax (estimated)", "one_off", "cr"),
                       ("Net profit excl. one-offs", "pat_norm", "cr"),
                       ("EPS reported (Rs)", "eps_adj", "num"), ("EPS excl. one-offs (Rs)", "eps_norm", "num"),
                       ("DPS (Rs)", "dps_adj", "num"), ("Dividend payout (%)", "payout", "pct")]
            bs_spec = [("Shareholders' funds", "equity", "cr", "strong"), ("Borrowings", "total_debt", "cr"),
                       ("Cash and equivalents", "cash", "cr"), ("Total assets", "total_assets", "cr", "strong")]
            ratio_spec = [("Return on equity (%)", "roe", "pct"), ("Return on assets (%)", "roa", "pct"),
                          ("Net margin (%)", "pat_margin", "pct"), ("Leverage factor (x)", "leverage", "x1"),
                          ("Book value per share (Rs)", "bvps_adj", "num"), ("FY-end P/E excl. one-offs (x)", "pe", "x1"),
                          ("FY-end P/B (x)", "pb", "x")]
        cf_spec = [("Cash flow from operations", "cfo", "cr", "strong"), ("Capital expenditure", "capex", "cr"),
                   ("Free cash flow", "fcf", "cr", "strong"), ("Cash flow from investing", "cfi", "cr"),
                   ("Cash flow from financing", "cff", "cr"), ("Dividends paid", "dividends", "cr")]
        S.append("<h2 class='pb'>Financial summary</h2>" + "<div class='grid2'>" +
                 ex("Revenue and net profit (Rs crore)", _img(out, ch.get("annual"))) +
                 ex("Return ratios and margins (%)", _img(out, ch.get("ratios"))) + "</div>")
        for title, spec in (("Profit and loss account (Rs crore)", pl_spec), ("Balance sheet (Rs crore)", bs_spec),
                            ("Cash flow statement (Rs crore)", cf_spec), ("Financial ratios", ratio_spec)):
            rows, rcls = _series_rows(ann, spec)
            if rows:
                S.append(ex(f"{title}, year ending March" if all(y.startswith("FY") for y in years) else title,
                            _table(["Year end"] + years, rows, rcls), "Company filings via Yahoo Finance; "
                            "Bharat Stock Analyser calculations"))
        S.append("<p class='note'>EPS, DPS and book value per share are calculated on the current share count so "
                 "that they stay comparable across bonus issues and splits. Return ratios use average equity and "
                 "assets where two years are available.</p>")

    # Valuation
    mrows = []
    for mm in v["methods"]:
        inputs = "<br>".join(f"{E(k)}: {E(val)}" for k, val in mm["inputs"].items())
        status = f"{fmt_num(mm['weight'], 0)}%" if mm["included"] else "0%"
        note = f"<div class='note'>{E(mm['note'])}</div>" if mm.get("note") else ""
        mrows.append([f"<b>{E(mm['name'])}</b>{note}", f"<div style='text-align:left;white-space:normal'>{inputs}</div>",
                      fmt_rs(mm["value"]), status])
    if v.get("target_before_caps") and v.get("target") and abs(v["target_before_caps"] - v["target"]) > 0.5:
        mrows.append(["Blended value before caps", "", fmt_rs(v["target_before_caps"]), ""])
    mrows.append(["<b>Blended 12-month target</b>", "", f"<b>{fmt_rs(v.get('target'))}</b>", "100%"])
    checks = [f"<li>{E(x)}</li>" for x in v.get("adjustments", [])] + \
             [f"<li>Conflict: {E(x)}</li>" for x in v.get("excluded_conflicts", [])]
    checks_html = f"<ul class='bul note'>{''.join(checks)}</ul>" if checks else ""
    # Exhibits are numbered when built, so build them in display order.
    buildup_html = ex("Target price build-up",
                      _table(["Method", "Key inputs", "Value (Rs)", "Weight"], mrows, left=(1,)) + checks_html)
    scen_html = ""
    if v.get("scenarios"):
        unit = "Forward book value (Rs)" if fin else "Forward EPS (Rs)"
        key = "bvps" if fin else "eps"
        srows = [[f"<b>{E(s['case'])}</b>", fmt_num(s.get(key), 1), fmt_x(s["multiple"], 2 if fin else 1),
                  fmt_rs(s["value"]), f'<span class="{_sign_cls(s["upside"])}">{fmt_pct(s["upside"], signed=True)}</span>',
                  f"<div style='text-align:left;white-space:normal'>{E(s['assumption'])}</div>"]
                 for s in v["scenarios"]]
        mult_name = v["scenarios"][0]["multiple_name"]
        scen_html = ex("Scenario analysis (relative method)",
                       _table(["Case", unit, mult_name, "Value (Rs)", "vs CMP", "Assumption"], srows, left=(5,)))
    coc = v["cost_of_capital"]
    asm = v["assumptions"]
    mu = v["multiples"]
    coc_rows = [["Risk-free rate (India 10-yr G-Sec)", fmt_pct(asm["risk_free"])],
                ["Equity risk premium", fmt_pct(asm["equity_risk_premium"])],
                ["Raw beta (1-yr daily vs Nifty 50)", fmt_num(coc.get("beta_raw"), 2)],
                ["Adjusted beta (0.67 x raw + 0.33, bounded 0.7 to 1.5)", fmt_num(coc["beta_used"], 2)],
                ["Cost of equity", fmt_pct(coc["cost_of_equity"])],
                ["Post-tax cost of debt", fmt_pct(coc["cost_of_debt_post_tax"])],
                ["WACC (floor 10%)", fmt_pct(coc["wacc"])], ["Terminal growth", fmt_pct(asm["terminal_growth"])]]
    mult_rows = [["P/E (trailing, excl. one-offs)", fmt_x(mu.get("pe")), fmt_x(f.get("pe_history_median")),
                  fmt_x(a["peers"]["medians"].get("pe"))],
                 ["P/B", fmt_x(mu.get("pb"), 2), fmt_x(f.get("pb_history_median"), 2),
                  fmt_x(a["peers"]["medians"].get("pb"), 2)],
                 ["EV / EBITDA", fmt_x(mu.get("ev_ebitda")), "-", "-"],
                 ["PEG (forward growth)", fmt_x(mu.get("peg"), 2), "-", "-"],
                 ["Free cash flow yield (%)", fmt_num(mu.get("fcf_yield"), 1), "-", "-"]]
    S.append("<h2 class='pb'>Valuation</h2>" + buildup_html + scen_html +
             ex("Valuation football field (Rs per share)", _img(out, ch.get("valuation"))) +
             "<div class='grid2'>" +
             ex(f"FY-end {'P/B' if fin else 'P/E'} history vs current", _img(out, ch.get("multiples"))) +
             "<div>" + ex("Current multiples vs history and peers",
                          _table(["Multiple", "Current", "Own median", "Peer median"], mult_rows)) +
             ex("Cost of capital assumptions", _table(["Assumption", "Value"], coc_rows), "Bharat Stock Analyser") +
             "</div></div>")

    # Scorecard
    srows, scls = [], []
    for pl in sc["pillars"]:
        srows.append([f"<b>{E(pl['pillar'])}</b> ({pl['weight']}%)", "", f"<b>{fmt_num(pl['score'], 0)}</b>"])
        scls.append("hl")
        for x in pl["metrics"]:
            srows.append([f"&nbsp;&nbsp;{E(x['metric'])}", E(x["display"]), fmt_num(x["score"], 0)])
            scls.append("")
    srows.append(["<b>Composite score</b>", "", f"<b>{fmt_num(sc.get('composite'), 0)}</b>"])
    scls.append("hl")
    S.append("<h2 class='pb'>Scorecard</h2><div class='grid2'>" +
             ex("Six-pillar scorecard (0 to 100)", _table(["Pillar and metric", "Value", "Score"], srows, scls)) +
             "<div>" + ex("Pillar scores against the composite", _img(out, ch.get("scorecard"))) +
             "<div class='callout note'>Each metric is scored on a straight line between a weak value (0) and a "
             "strong value (100). Pillar scores average their metrics; the composite weights the pillars as shown. "
             "Thresholds are listed in the methodology section.</div></div></div>")

    # Technicals
    trows = [[E(s["indicator"]), fmt_num(s["value"], 2), E(s["reading"]),
              f"<span class='sig-{E(s['signal'].split()[0])}'>{E(s['signal'])}</span>"] for s in t["signals"]]
    lv = t.get("levels", {})
    lvl_rows = [["Resistance", ", ".join(fmt_rs(x) for x in lv.get("resistances", [])) or "-"],
                ["Support", ", ".join(fmt_rs(x) for x in lv.get("supports", [])) or "-"],
                ["Average true range (14)", f"{fmt_rs(t.get('atr14'))} ({fmt_pct(t.get('atr_pct'))} of price)"],
                ["Annualised volatility (1 yr)", fmt_pct(t.get("volatility_1y"))],
                ["Maximum drawdown (1 yr)", fmt_pct(t.get("max_drawdown_1y"))]]
    if t.get("recent_cross"):
        rc = t["recent_cross"]
        lvl_rows.append(["Recent moving-average cross", f"{rc['type'].title()} cross on {rc['date']}"])
    S.append("<h2>Technical view</h2>" + ex("Technical dashboard", _table(["Indicator", "Value", "Reading", "Signal"],
                                                                           trows, left=(2,))) +
             "<div class='grid2'>" + ex("RSI (14) and MACD (12, 26, 9), 12 months", _img(out, ch.get("momentum"))) +
             ex("Key levels and risk measures", _table(["Measure", "Level"], lvl_rows)) + "</div>")

    # Peers
    prs = a["peers"]["rows"]
    if len(prs) > 1:
        prow, pcls = [], []
        for pr in prs:
            prow.append([f"<b>{E(pr['symbol'])}</b> <span class='note'>{E(pr['name'] or '')}</span>",
                         fmt_cr(pr["market_cap"], 0), fmt_rs(pr["price"]), fmt_num(pr["pe"], 1), fmt_num(pr["pb"], 2),
                         fmt_num(pr["roe"], 1), fmt_num(pr["op_margin"], 1), fmt_num(pr["div_yield"], 2),
                         f'<span class="{_sign_cls(pr["return_1y"])}">{fmt_num(pr["return_1y"], 1)}</span>'])
            pcls.append("hl" if pr.get("is_subject") else "")
        md = a["peers"]["medians"]
        prow.append(["<b>Peer median</b>", "-", "-", fmt_num(md.get("pe"), 1), fmt_num(md.get("pb"), 2),
                     fmt_num(md.get("roe"), 1), "-", "-", fmt_num(md.get("return_1y"), 1)])
        pcls.append("strong")
        S.append(f"<h2 class='pb'>Peer comparison: {E(a['peers']['group'] or '')}</h2>" +
                 ex("Peer valuation and returns",
                    _table(["Company", "Mcap (Rs cr)", "Price", "P/E (x)", "P/B (x)", "ROE (%)", "Op. margin (%)",
                            "Div. yield (%)", "1-yr return (%)"], prow, pcls)))

    # News and sources
    news_html = ""
    if a.get("news"):
        news_html += "<h3>Recent headlines (data feed)</h3><ul class='bul'>" + "".join(
            f"<li>{E(n.get('date') or '')} {E(n.get('publisher') or '')}: "
            + (f"<a href='{E(n['link'])}'>{E(n['title'] or '')}</a>" if n.get("link") else E(n.get("title") or ""))
            + "</li>" for n in a["news"][:8]) + "</ul>"
    if c.get("sources"):
        news_html += "<h3>Sources used in the analyst view</h3><ul class='bul'>" + "".join(
            f"<li>{E(s.get('date') or '')} " + (f"<a href='{E(s['url'])}'>{E(s['title'])}</a>" if s.get("url")
                                                else E(s["title"])) + "</li>" for s in c["sources"]) + "</ul>"
    links = (a.get("exchange") or {}).get("links") or []
    if links:
        news_html += "<h3>Exchange filings used by the model</h3><ul class='bul'>" + "".join(
            f"<li>{E(s.get('date') or '')} <a href='{E(s['url'])}'>{E(s['title'])}</a></li>" for s in links) + "</ul>"
    if news_html:
        S.append("<h2>News flow and sources</h2>" + news_html)

    # Methodology and disclaimer
    warn_html = "".join(f"<li>{E(w)}</li>" for w in a.get("warnings", []))
    S.append(
        "<h2 class='pb'>Methodology and rating key</h2>"
        "<div class='ratingkey'><span class='rk-good'>&#9650; BUY: upside 15% or more</span>"
        "<span class='rk-warn'>&#9670; HOLD: -5% to 15%</span><span class='rk-crit'>&#9660; SELL: below -5%</span>"
        "<span class='rk-warn'>Provisional: never BUY</span></div>"
        "<ul class='bul note'>"
        "<li><b>Earnings basis.</b> EBITDA excludes other income and unusual items. Net profit is profit "
        "attributable to owners. One-off items are the source's unusual items plus any spike in other income "
        "(more than three times the median of the other periods, with the excess at least 10% of profit before "
        "tax); they are removed "
        "after tax at the period's effective rate for EPS, P/E history, growth scores and the target. This is an "
        "estimate; company-defined adjusted figures can differ. Quarterly comparisons are matched by period end "
        "date. Trailing EPS uses four consecutive quarters, or the latest full year when a quarter is missing.</li>"
        "<li><b>Target price.</b> Weighted blend of a relative multiple (40%), an intrinsic method (30%: free cash "
        "flow DCF for non-financials, justified P/B for lenders) and the street consensus mean (30%). A method more "
        "than 2.5x or less than 0.4x the current price is excluded as an outlier; weights are renormalised. The "
        "blended target is capped at 1.15x the highest analyst target.</li>"
        "<li><b>Relative multiple.</b> Forward EPS (consensus where it is between 0.5x and 1.4x of trailing EPS; "
        "capped at 1.4x trailing when consensus expects a sharper rebound, because a historical P/E applied to "
        "recovery earnings double counts the recovery; otherwise trailing EPS grown at the 3-year EPS CAGR bounded "
        "to -10% and 20%) times the median of the company's FY-end P/E history and the peer median P/E, bounded "
        "to 5x and 80x and capped at 1.25x the current P/E, so that no more than a 25% re-rating is assumed within "
        "12 months. Lenders use forward book value and P/B with the same cap. Scenarios: bear case earnings 15% "
        "lower at 0.8x the lower of current and target multiple; bull case earnings 10% higher at 1.15x the target "
        "multiple.</li>"
        "<li><b>DCF.</b> Base free cash flow is the average of the last three years. Growth for years 1 to 5 equals "
        "the revenue CAGR bounded to 3% and 15%, fading to terminal growth by year 10. The present value is rolled "
        "forward 12 months at the cost of equity less the dividend yield. An excluded method that lies on the other "
        "side of the current price from the target lowers conviction to Low.</li>"
        "<li><b>Gates.</b> A BUY with composite score under 50 is cut to HOLD. A HOLD with score under 35 and upside "
        "under 5% becomes SELL. The rating is provisional, cannot be BUY and has Low conviction when only one "
        "valuation method is usable, a download the rating depends on failed, quarterly results are past their SEBI "
        "LODR deadline (45 days; 60 for the March quarter) but missing from the data, or research found newer "
        "results or a data conflict. Otherwise conviction reflects the score and the spread between methods.</li>"
        "<li><b>Scorecard thresholds (0 to 100).</b> ROE 5% to 22% (lenders 8% to 18%); ROCE 6% to 25%; net debt to "
        "equity 1.5x to 0x; interest cover 1.5x to 10x; CFO to PAT 0.5x to 1.1x; revenue CAGR 0% to 15%; EPS CAGR "
        "-5% to 20%; P/E vs own median 1.4x to 0.8x; PEG on forward growth 3 to 1; free cash flow yield 0% to 5%; "
        "price vs 200-DMA -15% to +10%; relative return vs Nifty -15% to +15%; volatility 50% to 18%; drawdown -50% "
        "to -12%; beta 1.6 to 0.7. Upside to the model's own target is not scored.</li>"
        "<li><b>Data.</b> Prices, annual statements, consensus and peer data from Yahoo Finance via the open-source "
        f"yfinance library, fetched {E(m['fetched_at'])}. Quarterly results, results board meeting dates and the "
        "shareholding pattern come from NSE filings (XBRL) where available; a filed quarter replaces Yahoo's figure "
        "for the same quarter, and differences above 2% (revenue) or 5% (profit) are listed in the data notes. If "
        "the exchange cannot be reached, the report uses Yahoo alone and says so. Figures are consolidated where "
        "the company reports them. Rs crore = Rs 10 million.</li>"
        "<li><b>Freshness.</b> Results filed with the exchange, or considered at a results board meeting, for a "
        "quarter that is not in the model data make the rating provisional. A board meeting followed by a later "
        "meeting for the same quarter is treated as rescheduled.</li></ul>"
        + (f"<h3>Data notes for this report</h3><ul class='bul note'>{warn_html}</ul>" if warn_html else "")
        + "<h3>Disclaimer</h3><p class='disclaimer'>This report is produced by Bharat Stock Analyser, an educational "
        "capstone project, using an automated model on public data. The author is not registered with the "
        "Securities and Exchange Board of India (SEBI) as a Research Analyst or Investment Adviser, and this report "
        "is not investment advice, a research report under the SEBI (Research Analysts) Regulations, 2014, or an "
        "offer or solicitation to buy or sell any security. Data may be delayed, incomplete or wrong; figures have "
        "not been audited, and only the quarterly figures are taken from exchange filings. Ratings are mechanical "
        "outputs of the stated rules. "
        "Investing in equities involves risk, including loss of capital. Consult a SEBI-registered adviser before "
        "making any investment decision.</p>")

    sections = "".join(f"<section class='section'>{s}</section>" for s in S)
    analyst_flag = " | includes analyst commentary written with Claude" if c else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(m['name'])}: {E(r['rating'])} | Bharat Stock Analyser</title><style>{CSS}</style></head>
<body><div class="page">
<header class="masthead"><div class="brand">Bharat Stock Analyser<span>Equity research note | Indian markets</span></div>
<div class="dateline">{E(m['report_date'])}<br>Prices as of {E(m['price_date'])}</div></header>
<section class="hero"><div><div class="eyebrow">{E(m.get('sector') or '')} | {E(m.get('industry') or '')}</div>
<h1>{E(m['name'])}</h1><div class="ticker">{E(m['exchange'])}: {E(m['nse_symbol'])} | Yahoo: {E(m['symbol'])}</div>
<p class="headline">{E(headline)}</p></div>
<div class="rating-card {cls}"><div class="rating-label">Rating</div><div class="rating-value">{icon} {E(r['rating'])}</div>
{'<div><span class="prov">Provisional</span></div>' if r.get('provisional') else ''}
<div class="conv">Conviction: {E(r['conviction'])}</div>
<div class="conv">Target {fmt_rs(v.get('target'))} | CMP {fmt_rs(p['cmp'])}</div></div></section>
<section class="kpis">{kpi_html}</section>
<div class="layout"><main>{''.join(main)}</main><aside>{''.join(side)}</aside></div>
{sections}
<footer><span>{E(m['generator'])}{analyst_flag}</span><span>Not investment advice. Educational use only.</span></footer>
</div></body></html>"""


CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_browser() -> str | None:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
        p = shutil.which(name)
        if p:
            return p
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def to_pdf(html_path: Path, pdf_path: Path) -> tuple[bool, str]:
    browser = find_browser()
    if not browser:
        return False, "no Chrome, Edge or Chromium found; open the HTML report and use Print to PDF."
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
           f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
    try:
        subprocess.run(cmd, check=True, timeout=120, capture_output=True)
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"headless browser failed ({type(exc).__name__})."
    return (pdf_path.exists() and pdf_path.stat().st_size > 0), "ok"
