"""Local web UI (runs on 127.0.0.1 only). Start with:  streamlit run app.py"""
import json
import re
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from auditsignoff.cli import set_engagement, set_team, review_ct, review_fa, review_fs, review_liq, review_tp
from auditsignoff.workflow import RANK as RANK_, RESPONSES, DECISIONS, Workflow, WorkflowError, load_cfg
from auditsignoff.folder import LIQ_ROLES, ROLES, scan_folder, scan_liq_folder
from auditsignoff.prefill import prefill, rows_to_engagement, write_fact_sheet_xlsx

st.set_page_config(page_title="AuditSignOff Suite UAE - Partner/Manager Review Automation", page_icon="🛡️", layout="wide")

# ---- Theme (offline: system fonts only, no external files). Change colours here. ----
NAVY, GOLD, TEAL, INK, MIST = "#0B1F3A", "#B8892B", "#0F7C8C", "#1B2B45", "#F5F7FB"
SEV = {"High": ("#FDE8E8", "#B42318"), "Medium": ("#FFF4DB", "#9A6700"), "Low": ("#E6F4EA", "#1E7A3C")}
st.markdown(f"""
<style>
html, body, [class*="css"] {{ font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; }}
.block-container {{ padding-top: 4rem; max-width: 1250px; }}
.hero {{ background: linear-gradient(120deg, {NAVY} 0%, #17407A 60%, {TEAL} 130%); border-radius: 18px;
        padding: 28px 34px; color: #fff; box-shadow: 0 10px 30px rgba(11,31,58,.25); margin-bottom: 18px; }}
.hero h1 {{ font-family: Georgia, "Times New Roman", serif; font-size: 2.0rem; margin: 0 0 4px 0; color: #fff; }}
.hero .tag {{ color: #E8D3A1; letter-spacing: .14em; font-size: .72rem; text-transform: uppercase; font-weight: 600; }}
.hero p {{ margin: 6px 0 0 0; color: #D6E0F0; font-size: .92rem; }}
.pill {{ display:inline-block; background: rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.25);
        border-radius: 999px; padding: 3px 12px; font-size: .75rem; margin: 10px 8px 0 0; color:#fff; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 8px; border-bottom: 2px solid #D5DDEB; }}
.stTabs [data-baseweb="tab"] {{ background: #fff; border-radius: 10px 10px 0 0; padding: 10px 22px; font-weight: 600; white-space: nowrap; color: {INK}; }}
.stTabs [aria-selected="true"] {{ background: {NAVY}; color: #fff !important; }}
div[data-testid="stFileUploader"] section {{ background: #fff; border: 2px dashed {GOLD}; border-radius: 14px; }}
.stButton > button[kind="primary"], .stDownloadButton > button {{ border-radius: 10px; font-weight: 600; padding: .55rem 1.2rem; }}
.stButton > button[kind="primary"] {{ background: {NAVY}; border: 0; color: #fff; }}
.stButton > button[kind="primary"]:hover {{ background: {GOLD}; color: #fff; }}
.card {{ background:#fff; border-radius:14px; padding:16px 20px; box-shadow:0 2px 10px rgba(11,31,58,.08); border-left:6px solid var(--c); }}
.card .n {{ font-size:2rem; font-weight:700; color:var(--c); line-height:1.1; }}
.card .l {{ font-size:.8rem; color:#5B6B85; text-transform:uppercase; letter-spacing:.08em; }}
section[data-testid="stSidebar"] {{ background:#fff; border-right:1px solid #D5DDEB; }}
section[data-testid="stSidebar"] .stButton > button {{ text-align:left; justify-content:flex-start; border-radius:10px; }}
.foot {{ color:#6B7A93; font-size:.78rem; text-align:center; margin-top:28px; }}
</style>
<div class="hero">
  <div class="tag">UAE audit and tax &nbsp;·&nbsp; Partner / Manager Review</div>
  <h1>AuditSignOff Suite UAE - Partner/Manager Review Automation</h1>
  <p>Software finds and records; the reviewer decides and signs.</p>
  <span class="pill">🔒 Offline · files stay on this computer</span><span class="pill">📄 Final Review Paper</span><span class="pill">🧾 Audit trail (SHA-256)</span>
</div>
""", unsafe_allow_html=True)

NAV = [
    ("Review modules", [("fs", "📑", "Statutory audit FS pack", "Module A - audit FS pack review"), ("liq", "⏱️", "Liquidation clock & documents", "Module B - tracker, SOA, BR, liquidator's report, CT/VAT"),
                        ("tp", "🔁", "Transfer pricing", "Module C - TP report, benchmarking, disclosure"), ("ct", "🧮", "Corporate tax", "Module D - CT computation and return"),
                        ("fa", "🕵️", "Forensic audit", "Module E - GL, vendor, employee and evidence tests")]),
    ("Preparation", [("pre", "🪪", "Pre-fill fact sheet", "Build the engagement fact sheet from licence, MOA, AOA")]),
    ("Review control", [("wf", "✅", "Review workflow", "First review → Manager → Partner, with preparer corrections")]),
]
FLAT = {k: (ic, nm, ds) for _, items in NAV for k, ic, nm, ds in items}
if "page" not in st.session_state:
    st.session_state["page"] = "home"
with st.sidebar:
    st.markdown("### 🛡️ AuditSignOff Suite UAE")
    q = st.text_input("Search", placeholder="Search modules…", label_visibility="collapsed", key="nav_q").strip().lower()
    if st.button("🏠  All categories", use_container_width=True, type="primary" if st.session_state["page"] == "home" else "secondary", key="nav_home"):
        st.session_state["page"] = "home"; st.rerun()
    for grp, items in NAV:
        shown = [i for i in items if not q or q in (i[2] + " " + i[3]).lower()]
        if not shown:
            continue
        st.caption(grp.upper())
        for k, ic, nm, ds in shown:
            if st.button(f"{ic}  {nm}", use_container_width=True, key=f"nav_{k}", help=ds, type="primary" if st.session_state["page"] == k else "secondary"):
                st.session_state["page"] = k; st.rerun()
    st.divider()
    with st.expander("👥 Review team (appears on the review paper)", expanded=True):
        _w = Workflow(Path(st.session_state.get("wf_dir", Path(__file__).parent / "review_workflow")) / "workflow.db")
        _st = _w.staff()
        _rk = {"preparer": 0, "L1": 1, "L2": 2, "L3": 3}
        def _pick(label, minrank, key):
            opts = [""] + [r["name"] for r in _st if _rk[r["role"]] >= minrank]
            return st.selectbox(label, opts, key=key)
        _p = _pick("Prepared by", 0, "tm_prep"); _r1 = _pick("First reviewer", 1, "tm_r1")
        _r2 = _pick("Manager", 2, "tm_r2"); _r3 = _pick("Partner", 3, "tm_r3")
        _engs = _w.engagements()
        _lk = st.selectbox("Link to workflow engagement (optional)", [""] + [e["ref"] for e in _engs], key="tm_eng",
                           help="When linked, every review paper you generate is stamped with the live review status, sign-off dates/times and the movement trail.")
        _auto = st.checkbox("Record every review I run in the workflow (auto-create the engagement)", value=True, key="tm_auto",
                            help="Creates the engagement from the client, module and year, assigns the people picked above, and stamps the paper with status, sign-off dates/times and the trail.")
        st.caption("Add or import names on the Review workflow page (Team panel).")
    if _lk:
        _a = _w.assignees(_lk)
        _p, _r1, _r2, _r3 = _a.get("preparer", _p), _a.get("L1", _r1), _a.get("L2", _r2), _a.get("L3", _r3)
        set_engagement(_w.db_path, _lk)
    elif _auto and _p:
        set_engagement(_w.db_path, None, auto=True)
    else:
        set_engagement()
        if _p:
            st.sidebar.warning("Not linked to the workflow: the paper will show names only (no status, sign-off times or trail).")
    set_team(_p, _r1, _r2, _r3)
    st.divider()
    st.caption("Offline · files stay on this computer")
PAGE = st.session_state["page"]
if PAGE == "home":
    st.subheader("All categories")
    for grp, items in NAV:
        st.markdown(f"**{grp}**")
        cols = st.columns(3)
        for n, (k, ic, nm, ds) in enumerate(items):
            with cols[n % 3]:
                st.markdown(f'<div class="card" style="--c:{TEAL};margin-bottom:6px;min-height:104px"><div class="l">{ds}</div><div style="font-size:1.1rem;font-weight:700;color:{INK}">{ic} {nm}</div></div>', unsafe_allow_html=True)
                if st.button("Open", key=f"home_{k}"):
                    st.session_state["page"] = k; st.rerun()
else:
    ic, nm, ds = FLAT[PAGE]
    st.markdown(f"#### {ic} {nm}")
    st.caption(ds)
TPL = Path(__file__).parent / "templates"


def _save(upload, folder):
    p = Path(folder) / upload.name
    p.write_bytes(upload.getbuffer())
    return p


def _card(col, label, n, color):
    col.markdown(f'<div class="card" style="--c:{color}"><div class="n">{n}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)


def _show(json_path, docx_path):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    rows = [{"Ref": f"{r['check']}", "Severity": f["severity"], "Finding": f["title"], "Detail": f["detail"], "Page / evidence": f["location"]}
            for r in data["results"] if r["status"] == "EXC" for f in r["findings"]]
    assist = [{"Check": r["check"], "Reviewer to confirm": f["detail"], "Where": f["location"]}
              for r in data["results"] if r["status"] == "REVIEW" for f in r["findings"]]
    notrun = [{"Check": r["check"], "Why not run": r["note"]} for r in data["results"] if r["status"] == "NOTRUN"]
    sev = pd.Series([r["Severity"] for r in rows]).value_counts() if rows else pd.Series(dtype=int)
    c = st.columns(4)
    _card(c[0], "Exceptions", len(rows), NAVY)
    _card(c[1], "High", int(sev.get("High", 0)), SEV["High"][1])
    _card(c[2], "Medium", int(sev.get("Medium", 0)), SEV["Medium"][1])
    _card(c[3], "Low", int(sev.get("Low", 0)), SEV["Low"][1])
    st.write("")
    if rows:
        def _paint(v):
            bg, fg = SEV.get(v, ("", ""))
            return f"background-color:{bg}; color:{fg}; font-weight:700" if bg else ""
        df = pd.DataFrame(rows)
        st.dataframe(df.style.map(_paint, subset=["Severity"]), use_container_width=True, hide_index=True)
    else:
        st.success("No exceptions from the automated checks. Complete the manual and judgement items before sign-off.")
    if assist:
        with st.expander(f"Items the software extracted for you to confirm ({len(assist)})"):
            st.dataframe(pd.DataFrame(assist), use_container_width=True, hide_index=True)
    if notrun:
        with st.expander(f"Not checked - input missing or not readable ({len(notrun)})"):
            st.dataframe(pd.DataFrame(notrun), use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    c1.download_button("⬇ Final Review Paper (DOCX)", Path(docx_path).read_bytes(), file_name=Path(docx_path).name)
    x = Path(docx_path).with_suffix(".xlsx")
    c2.download_button("⬇ Exception log (XLSX)", x.read_bytes(), file_name=x.name)
    if data.get("milestones"):
        st.subheader("Clock schedule")
        st.dataframe(pd.DataFrame(data["milestones"]), use_container_width=True, hide_index=True)


ANY_DOC = ["docx", "doc", "rtf", "pdf", "xlsx", "xls", "jpg", "jpeg", "png", "tif", "tiff"]
FACT_TYPES = ANY_DOC + ["xlsm", "yaml", "yml"]
FIELD_LABELS = {"client.name": "Client name", "client.legal_status": "Legal status", "client.authority": "Licensing authority",
                "client.emirate": "Emirate", "client.shareholders": "Shareholders", "client.signatories_legal": "Legal signatories",
                "client.year_end": "Year end", "allowed_years": "Allowed years (incorporation)", "info.licence_no": "Licence no. (info)",
                "info.licence_expiry": "Licence expiry (info)"}


def _run_fs(e, f, t):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            res, docx_path = review_fs(e, f, t, Path(tmp) / "out")
            _show(docx_path.with_suffix(".json"), docx_path)
        except Exception as ex:   # show the reason, never a stack trace to a reviewer
            st.error(f"Could not complete the review: {ex}")


def _prefill_table(paths, key):
    """Extract -> editable table. Returns the reviewed rows (or None)."""
    rows, conflicts = prefill(paths)
    if not rows:
        st.warning("Nothing recognisable found. Use clearer scans or the fact-sheet template.")
        return None
    if any(r["confidence"] == "Low" for r in rows):
        st.warning("Low-confidence values come from OCR or inference: check them against the original document.")
    for c in conflicts:
        st.warning(f"Documents disagree on **{FIELD_LABELS.get(c['field'], c['field'])}**: " + " vs ".join(c["values"]))
    df = pd.DataFrame([{"Field": FIELD_LABELS.get(r["field"], r["field"]), "Value": r["value"], "Confidence": r["confidence"],
                        "Source": r["source"], "Matched text": r["snippet"], "_k": r["field"]} for r in rows])
    ed = st.data_editor(df.drop(columns="_k"), hide_index=True, use_container_width=True, key=key,
                        disabled=["Field", "Confidence", "Source", "Matched text"])
    out = []
    for i, r in enumerate(rows):
        out.append({**r, "value": ed.iloc[i]["Value"]})
    return out


if PAGE == "fs":
    st.write("Review an FS pack in **any format** (Word, old .doc, PDF, Excel, scanned JPG/PNG) - upload files, or point to the whole engagement folder.")
    mode = st.radio("How do you want to supply the files?", ["Upload files", "Engagement folder on this PC"], horizontal=True)
    if mode == "Upload files":
        st.download_button("⬇ Fact-sheet template (Excel)", (TPL / "Engagement_Fact_Sheet.xlsx").read_bytes(), file_name="Engagement_Fact_Sheet.xlsx")
        st.download_button("⬇ Fact-sheet template (Word)", (TPL / "Engagement_Fact_Sheet.docx").read_bytes(), file_name="Engagement_Fact_Sheet.docx")
        pre = st.session_state.get("prefilled_xlsx")
        use_pre = st.checkbox("Use the fact sheet pre-filled and confirmed in the Pre-fill tab", value=False, disabled=pre is None)
        eng = None if use_pre else st.file_uploader("Engagement fact sheet (any format)", type=FACT_TYPES, key="eng")
        fs = st.file_uploader("FS pack (any format)", type=ANY_DOC, key="fs")
        tb = st.file_uploader("Trial balance (Excel / CSV / old .xls, optional)", type=["xlsx", "xls", "csv"], key="tb")
        st.caption("Formatting checks (font, size, margins, alignment) run fully only on Word; PDF gets font/size/left margin; Excel, scanned and image inputs are content and tie-out checks only (OCR needs Tesseract).")
        if st.button("Run review", type="primary", disabled=not ((eng or (use_pre and pre)) and fs)):
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                if use_pre:
                    e = Path(tmp) / "Engagement_Fact_Sheet_prefilled.xlsx"; e.write_bytes(pre)
                else:
                    e = _save(eng, tmp)
                f = _save(fs, tmp); t = _save(tb, tmp) if tb else None
                _run_fs(e, f, t)
    else:
        folder = st.text_input("Folder path (e.g. C:\\Clients\\GoldenCrest\\FY2025)", key="fs_folder")
        st.caption("The app runs on this PC, so it reads the folder directly. Files are sorted by name; correct any role below.")
        if folder and st.button("Scan folder"):
            try:
                st.session_state["scan"] = scan_folder(folder)
            except Exception as ex:
                st.session_state.pop("scan", None); st.error(str(ex))
        scan = st.session_state.get("scan")
        if scan:
            df = pd.DataFrame(scan)
            ed = st.data_editor(df.drop(columns="_path"), hide_index=True, use_container_width=True, key="scan_ed",
                                disabled=["File", "Size KB"],
                                column_config={"Role": st.column_config.SelectboxColumn("Role", options=ROLES, required=True)})
            roles = {}
            for i, r in ed.iterrows():
                roles.setdefault(r["Role"], []).append(scan[i]["_path"])
            fs_files, fact, tbf = roles.get("FS pack", []), roles.get("Engagement fact sheet", []), roles.get("Trial balance", [])
            src = roles.get("Trade licence", []) + roles.get("MOA / AOA", []) + roles.get("Other source document (pre-fill)", [])
            ok_pack = len(fs_files) == 1
            if not ok_pack:
                st.info("Mark exactly one file as 'FS pack'.")
            fact_path, confirmed = None, True
            if fact:
                fact_path = fact[0]
            elif src:
                st.markdown("**No fact sheet in the folder - pre-filled from the licence / MOA / source documents. Check and correct:**")
                reviewed = _prefill_table(src, "folder_pre")
                if reviewed:
                    fy = st.number_input("Financial year under review", 2015, 2100, date.today().year - 1, key="folder_fy")
                    confirmed = st.checkbox("I have checked these values against the original documents")
                    if confirmed:
                        eng_d = rows_to_engagement(reviewed, int(fy))
                        fact_path = str(Path(tempfile.mkdtemp()) / "Engagement_Fact_Sheet_prefilled.xlsx")
                        write_fact_sheet_xlsx(eng_d, fact_path)
                else:
                    confirmed = False
            else:
                st.info("Add a fact sheet, or mark a trade licence / MOA so one can be pre-filled.")
            if st.button("Run review on this folder", type="primary", disabled=not (ok_pack and fact_path and confirmed)):
                _run_fs(fact_path, fs_files[0], tbf[0] if tbf else None)

if PAGE == "pre":
    st.write("Upload the **trade licence, MOA / AOA, certificate of incorporation** and similar documents (any format), or point to a folder. "
             "The app proposes the fact-sheet fields; you confirm or correct them, then download the fact sheet or use it in the FS tab.")
    st.caption("Assisted check: extraction relies on label wording and can miss or misread. Scanned and image documents are OCR and always shown as Low confidence.")
    src_mode = st.radio("Source", ["Upload files", "Folder on this PC"], horizontal=True, key="pre_mode")
    paths, tmpd = [], tempfile.mkdtemp()
    if src_mode == "Upload files":
        ups = st.file_uploader("Licence / MOA / AOA / certificates (any format, several allowed)", type=ANY_DOC, accept_multiple_files=True, key="pre_ups")
        paths = [str(_save(u, tmpd)) for u in ups or []]
    else:
        pf = st.text_input("Folder path", key="pre_folder")
        if pf:
            try:
                paths = [r["_path"] for r in scan_folder(pf) if r["Role"] in ("Trade licence", "MOA / AOA", "Other source document (pre-fill)")]
                st.caption(f"{len(paths)} source document(s) recognised by file name (licence, MOA/AOA, passport, certificate, resolution).")
            except Exception as ex:
                st.error(str(ex))
    fy_pre = st.number_input("Financial year under review", 2015, 2100, date.today().year - 1, key="pre_fy")
    if paths:
        try:
            reviewed = _prefill_table(paths, "pre_ed")
        except Exception as ex:
            reviewed = None; st.error(f"Could not read the documents: {ex}")
        if reviewed:
            ok = st.checkbox("I have checked these values against the original documents", key="pre_ok")
            if st.button("Create fact sheet", type="primary", disabled=not ok):
                eng_d = rows_to_engagement(reviewed, int(fy_pre))
                x = Path(tmpd) / "Engagement_Fact_Sheet_prefilled.xlsx"
                write_fact_sheet_xlsx(eng_d, x)
                st.session_state["prefilled_xlsx"] = x.read_bytes()
                st.success("Fact sheet created. Tick 'Use the fact sheet pre-filled...' in the FS tab, or download it here. Shareholders, FS signatories and the Board Resolution flag still need confirming by the team.")
    if st.session_state.get("prefilled_xlsx"):
        st.download_button("⬇ Download pre-filled fact sheet (Excel)", st.session_state["prefilled_xlsx"], file_name="Engagement_Fact_Sheet_prefilled.xlsx")

def _run(fn, *a, **k):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            res, docx_path = fn(*a, out_dir=Path(tmp) / "out", **k)
            _show(docx_path.with_suffix(".json"), docx_path)
        except Exception as ex:
            st.error(f"Could not complete the review: {ex}")


def _optional_date(label, key):
    on = st.checkbox(label, key=key + "_on")
    return st.date_input(label, value=date.today(), key=key, label_visibility="collapsed") if on else None


if PAGE == "tp":
    st.write("Review a **transfer pricing report** against the benchmarking workbook, the engagement facts, the audited FS and the CT working sheet. "
             "Report: Word is best (formatting checks), PDF/scan also works for content checks.")
    pre = st.session_state.get("prefilled_xlsx")
    use_pre_tp = st.checkbox("Use the fact sheet pre-filled in the Pre-fill tab", value=False, disabled=pre is None, key="tp_pre")
    tp_eng = None if use_pre_tp else st.file_uploader("Engagement fact sheet (any format)", type=FACT_TYPES, key="tp_eng")
    tp_rep = st.file_uploader("TP report (Word / PDF / scan)", type=ANY_DOC, key="tp_rep")
    tp_wb = st.file_uploader("Benchmarking workbook (Excel: company + PLI columns, tested-party figures)", type=["xlsx", "xls"], key="tp_wb")
    c1, c2 = st.columns(2)
    tp_fs = c1.file_uploader("Audited FS (optional; needed for the notes-to-accounts checks)", type=ANY_DOC, key="tp_fs")
    tp_ct = c2.file_uploader("CT working sheet (optional, ties the TP adjustment)", type=["xlsx", "xls"], key="tp_ct")
    from auditsignoff.birf_template import build_birf_template
    import io as _io
    _bt = Path(tempfile.gettempdir()) / "BIRF_Template.xlsx"
    build_birf_template(_bt)
    st.download_button("⬇ BIRF template (Excel) - fill it, then upload it below", _bt.read_bytes(), file_name="BIRF_Template.xlsx", key="dl_birf")
    tp_birf = st.file_uploader("BIRF - Benchmarking Information Request Form (optional; checks remuneration split, connected persons). Use the template above, or any Word/PDF form.", type=ANY_DOC, key="tp_birf")
    st.caption("A Financial Update needs the prior-year report attached after the update inside the same Word/PDF file; the year-on-year checks (1.12) read it from there.")
    with st.expander("Related-party values for the Disclosure Form / Master-Local File test (optional, AED)"):
        g = st.columns(5)
        facts = {k: v for k, v in {"rp_aggregate": g[0].number_input("RP aggregate", 0.0, step=100000.0), "rp_max_category": g[1].number_input("Largest category", 0.0, step=100000.0),
                                   "connected_payments": g[2].number_input("Connected persons", 0.0, step=10000.0), "revenue": g[3].number_input("Own revenue", 0.0, step=1000000.0),
                                   "group_revenue": g[4].number_input("Group revenue", 0.0, step=1000000.0)}.items() if v}
    if st.button("Run TP review", type="primary", disabled=not ((tp_eng or (use_pre_tp and pre)) and tp_rep)):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            e = (Path(tmp) / "fact.xlsx") if use_pre_tp else _save(tp_eng, tmp)
            if use_pre_tp:
                e.write_bytes(pre)
            _run(review_tp, e, _save(tp_rep, tmp), _save(tp_wb, tmp) if tp_wb else None, fs_path=_save(tp_fs, tmp) if tp_fs else None,
                 ct_path=_save(tp_ct, tmp) if tp_ct else None, facts=facts, birf_path=_save(tp_birf, tmp) if tp_birf else None)

if PAGE == "ct":
    st.write("Re-performs the **corporate tax computation** from the firm CT working sheet and compares it with what the sheet says, the EmaraTax return figures and the FS.")
    ct_wb = st.file_uploader("CT working sheet (see samples/ct_demo_locked.xlsx)", type=["xlsx", "xls", "xlsm"], key="ct_wb")
    st.caption("If the sheet was never opened in Excel it has no calculated values; the app then calculates it with LibreOffice if installed, otherwise open and save it in Excel first.")
    ct_ret = st.file_uploader("EmaraTax return figures (any format; lines such as 'Taxable income', 'Corporate tax payable'; optional)", type=ANY_DOC, key="ct_ret")
    c1, c2 = st.columns(2)
    ct_fs = c1.file_uploader("Audited FS (optional, ties accounting profit)", type=ANY_DOC, key="ct_fs")
    tp_adj_in = c2.number_input("TP adjustment per TP report (AED, optional)", 0.0, step=1000.0, key="ct_tpadj")
    filed = _optional_date("Return filing date is known", "ct_filed")
    if st.button("Run CT review", type="primary", disabled=not ct_wb):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            _run(review_ct, _save(ct_wb, tmp), return_path=_save(ct_ret, tmp) if ct_ret else None, tp_report_adj=tp_adj_in or None,
                 filing_date=filed, fs_path=_save(ct_fs, tmp) if ct_fs else None)

if PAGE == "fa":
    st.write("**Forensic analytics and evidence integrity**: GL tests, vendor/employee matching, related-party screening, document authenticity and chain of custody. "
             "Results are indicators to examine, not proof of fraud.")
    case = st.text_input("Case / client name", key="fa_case")
    c1, c2 = st.columns(2)
    gl_up = c1.file_uploader("General ledger / transactions (Excel or CSV)", type=["xlsx", "xls", "csv"], key="fa_gl")
    pe = _optional_date("Period end date is known", "fa_pe")
    yrs = c2.text_input("Years in the signed scope (e.g. 2023, 2024, 2025)", key="fa_years")
    c3, c4 = st.columns(2)
    ven = c3.file_uploader("Vendor master (optional)", type=["xlsx", "xls", "csv"], key="fa_ven")
    emp = c4.file_uploader("Employee master (optional)", type=["xlsx", "xls", "csv"], key="fa_emp")
    rel = st.text_input("Related parties / persons of interest (comma-separated)", key="fa_rel")
    reg = st.file_uploader("Evidence / confirmation register (optional)", type=["xlsx", "xls", "csv"], key="fa_reg")
    evd = st.text_input("Evidence folder on this PC (for authenticity metadata and hash check)", key="fa_evd")
    with st.expander("Fraud-scenario inputs (optional): bank diversion, signatures, FS manipulation, inventory, holidays"):
        c5, c6 = st.columns(2)
        bank_up = c5.file_uploader("Bank statement (Date, Narration, Beneficiary, Beneficiary IBAN, Debit, Credit, Balance)", type=["xlsx", "xls", "csv"], key="fa_bank")
        stock_up = c6.file_uploader("Stock register (Item, Opening, GRN, Issued, Adjustments, Closing book, Physical count, Unit cost, Invoiced sales, Invoiced purchases)", type=["xlsx", "xls", "csv"], key="fa_stock")
        fsd_up = c5.file_uploader("Financial statement data, current and prior year (Item, CY, PY)", type=["xlsx", "xls", "csv"], key="fa_fsd")
        man_up = c6.file_uploader("Authorised-signatory mandate (Name, Designation, Single limit, Specimen, Valid from, Valid to)", type=["xlsx", "xls", "csv"], key="fa_man")
        sigf = st.text_input("Signatures folder on this PC (holds the signature register and the image files)", key="fa_sigf")
        hol = st.text_input("Public holidays in the period (YYYY-MM-DD, comma-separated; check the official UAE calendar)", key="fa_hol")
    if st.button("Run forensic review", type="primary", disabled=not (case and (gl_up or evd or reg or bank_up or stock_up or fsd_up))):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            sy = [int(x) for x in re.findall(r"\d{4}", yrs)]
            _run(review_fa, case, gl=_save(gl_up, tmp) if gl_up else None, period_end=pe.isoformat() if pe else None, scope_years=sy or None,
                 vendors=_save(ven, tmp) if ven else None, employees=_save(emp, tmp) if emp else None,
                 related=[x.strip() for x in rel.split(",") if x.strip()], register=_save(reg, tmp) if reg else None, evidence_dir=evd.strip().strip('"') or None,
                 bank=_save(bank_up, tmp) if bank_up else None, stock=_save(stock_up, tmp) if stock_up else None, fs_data=_save(fsd_up, tmp) if fsd_up else None,
                 mandate=_save(man_up, tmp) if man_up else None, signatures=sigf.strip().strip('"') or None, holidays=re.findall(r"\d{4}-\d{2}-\d{2}", hol) or None)

if PAGE == "liq":
    st.write("Upload the tracker **and** the liquidation documents. The tool computes the clocks and checks each document against the tracker and against each other. "
             "Anything not uploaded is listed as *not checked* with the document to upload.")
    st.download_button("⬇ Liquidation tracker template (Excel)", (TPL / "Liquidation_Tracker.xlsx").read_bytes(), file_name="Liquidation_Tracker.xlsx")
    ANY = ["docx", "doc", "pdf", "xlsx", "xls", "xlsm", "csv", "jpg", "jpeg", "png", "tif", "tiff"]
    li = st.file_uploader("Liquidation tracker (Excel)", type=["xlsx", "xls", "xlsm", "yaml", "yml"], key="liq")
    c1, c2 = st.columns(2)
    br_up = c1.file_uploader("Board Resolution", type=ANY, key="liq_br")
    tb_up = c2.file_uploader("Trial balance (optional)", type=["xlsx", "xls", "xlsm", "csv", "pdf", "docx"], key="liq_tb")
    sr_up = st.file_uploader("Statement of Affairs and Liquidator's report / audit report (upload the combined file, or both files - the tool recognises each by its content)",
                             type=ANY, accept_multiple_files=True, key="liq_sr")
    ct_up = st.file_uploader("CT / VAT registration certificates, EmaraTax or FTA letters (any number)", type=ANY, accept_multiple_files=True, key="liq_ct")
    lic_up = st.file_uploader("Trade licence / MOA (optional, for name consistency)", type=ANY, accept_multiple_files=True, key="liq_lic")
    lf = st.text_input("…or a folder on this PC holding all of these (files are matched by name; adjust the roles below)", key="liq_folder")
    if st.button("Scan liquidation folder", disabled=not lf.strip()):
        try:
            st.session_state["liq_scan"] = scan_liq_folder(lf)
        except Exception as ex:
            st.error(str(ex))
    scan = st.session_state.get("liq_scan")
    if scan:
        df = pd.DataFrame(scan)
        ed = st.data_editor(df.drop(columns="_path"), hide_index=True, use_container_width=True, key="liq_scan_ed",
                            column_config={"Role": st.column_config.SelectboxColumn(options=LIQ_ROLES)}, disabled=["File", "Size KB"])
        for i, r in ed.iterrows():
            scan[i]["Role"] = r["Role"]
    asat = st.date_input("As at", value=date.today())
    if st.button("Run liquidation review", type="primary", disabled=not (li or scan)):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            try:
                docs = {"br": [], "soa_report": [], "soa": [], "report": [], "tb": [], "ctvat": [], "licence": []}
                for key, up in (("br", br_up), ("tb", tb_up)):
                    if up:
                        docs[key].append(_save(up, tmp))
                for key, ups in (("soa_report", sr_up), ("ctvat", ct_up), ("licence", lic_up)):
                    for u in ups or []:
                        docs[key].append(_save(u, tmp))
                p = _save(li, tmp) if li else None
                rolemap = {"Board Resolution": "br", "Statement of Affairs": "soa", "Liquidator's report": "report", "Trial balance": "tb",
                           "CT / VAT registration or FTA letter": "ctvat", "Trade licence / MOA": "licence"}
                for r in scan or []:
                    if r["Role"] == "Liquidation tracker" and not p:
                        p = r["_path"]
                    elif r["Role"] in rolemap:
                        docs[rolemap[r["Role"]]].append(r["_path"])
                if not p:
                    st.error("Upload the liquidation tracker (or tag one in the folder list).")
                else:
                    res, ms, docx_path = review_liq(p, Path(tmp) / "out", asat, docs={k: v for k, v in docs.items() if v})
                    _show(docx_path.with_suffix(".json"), docx_path)
            except Exception as ex:
                st.error(f"Could not complete the review: {ex}")

if PAGE == "wf":
    st.write("Track every review point from the **first review** to **Manager** to **Partner** sign-off. Each review run (the .json the other tabs create) is loaded here; "
             "points go back to the preparer, are answered, re-checked, and only pass forward when closed.")
    cfg = load_cfg()
    wdir = st.text_input("Workflow database folder", value=str(Path(__file__).parent / "review_workflow"), key="wf_dir")
    wf = Workflow(Path(wdir) / "workflow.db", cfg)
    RL = {"preparer": "Preparer", "L1": "First reviewer", "L2": "Manager", "L3": "Partner"}
    with st.expander("👥 Team - staff names and roles", expanded=not wf.c.execute("select 1 from staff").fetchone()):
        st.caption("Type a name and pick a role, or upload your staff list (Excel/CSV with columns Name, Role, optional Email).")
        t1, t2, t3, t4 = st.columns([3, 2, 3, 1])
        tn = t1.text_input("Name", key="tm_name"); tr = t2.selectbox("Role", list(RL.values()), key="tm_role"); te = t3.text_input("Email (optional)", key="tm_mail")
        if t4.button("Add", disabled=not tn.strip()):
            try:
                wf.add_staff(tn, tr, te); st.rerun()
            except WorkflowError as ex:
                st.error(str(ex))
        su = st.file_uploader("Upload staff list", type=["xlsx", "csv"], key="tm_up")
        rep = st.checkbox("Replace the current list", key="tm_rep")
        cu1, cu2 = st.columns(2)
        if cu1.button("Import staff list", disabled=not su):
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpd:
                try:
                    r = wf.import_staff(_save(su, tmpd), replace=rep); st.success(f"{r['added']} added" + (f"; rejected: {r['rejected']}" if r["rejected"] else "")); st.rerun()
                except WorkflowError as ex:
                    st.error(str(ex))
        import io, openpyxl
        _b = io.BytesIO(); _w = openpyxl.Workbook(); _s = _w.active; _s.append(["Name", "Role", "Email"]); _s.append(["Example Name", "Preparer", ""]); _s.append(["Example Reviewer", "First reviewer", ""]); _s.append(["Example Manager", "Manager", ""]); _s.append(["Example Partner", "Partner", ""]); _w.save(_b)
        cu2.download_button("⬇ Staff list template (Excel)", _b.getvalue(), file_name="Staff_List_Template.xlsx")
        cur = wf.staff()
        if wf.c.execute("select 1 from staff").fetchone():
            st.dataframe(pd.DataFrame([{"Name": r["name"], "Role": RL[r["role"]], "Email": r["email"]} for r in cur]), hide_index=True, use_container_width=True)
            rm = st.selectbox("Remove a person", [""] + [r["name"] for r in cur], key="tm_rm")
            if rm and st.button("Remove"):
                wf.remove_staff(rm); st.rerun()
        else:
            st.info("No staff saved yet - the sample names from rules/workflow.yaml are shown until you add your own.")
    users = wf.users()
    me = st.selectbox("You are", list(users), format_func=lambda n: f"{n} ({RL[users[n]]})", key="wf_me")
    role = users[me]
    st.caption(f"Role: **{RL[role]}**. This is an honour-system record: every action is time-stamped in the audit log.")
    engs = wf.engagements()
    q = wf.my_queue(me)
    if q:
        st.markdown(f"##### 📥 Waiting for you ({len(q)})")
        st.dataframe(pd.DataFrame([{"Engagement": x["ref"], "Client": x["client"], "Module": x["module"], "Action needed": x["action"], "Open points": x["open"]} for x in q]), hide_index=True, use_container_width=True)
    else:
        st.caption("Nothing is waiting for you right now.")
    with st.expander("➕ New engagement"):
        c1, c2, c3, c4 = st.columns(4)
        nref = c1.text_input("Reference (e.g. ABC-TP-2025)", key="wf_nref")
        nmod = c2.selectbox("Module", ["Statutory FS", "Transfer pricing", "Corporate tax", "Forensic", "Liquidation"], key="wf_nmod")
        ncl = c3.text_input("Client", key="wf_ncl")
        nper = c4.text_input("Period", key="wf_nper")
        if st.button("Create engagement", disabled=not (nref and ncl)):
            try:
                wf.create(nref.strip(), nmod, ncl.strip(), nper.strip(), me); st.success("Created"); st.rerun()
            except WorkflowError as ex:
                st.error(str(ex))
    if not engs:
        st.info("No engagement yet. Create one above.")
    else:
        ref = st.selectbox("Engagement", [e["ref"] for e in engs], format_func=lambda r: next(f"{e['ref']} - {e['client']} ({e['module']}, {e['period']})" for e in engs if e["ref"] == r), key="wf_ref")
        e = wf.eng(ref)
        st.subheader(wf.state_text(ref))
        lvs = wf.levels
        cur = e["state"].split("_")[0] if e["state"] != "SIGNED_OFF" else None
        fl = wf.flow(ref)
        (st.success if e["state"] == "SIGNED_OFF" else st.warning)(f"**{fl['headline']}**" + (f"  ·  Next after this: {fl['next']}" if fl["next"] else ""))
        ICON = {"Signed off": "✅", "Pending": "⏳"}
        st.dataframe(pd.DataFrame([{"Stage": r["label"], "Owner": r["owner"], "Status": ("✅ " if r["status"] == "Signed off" else "🔵 " if r["status"] not in ("Pending", "-") else "⏳ ") + r["status"],
                                    "Signed off by": r["signed_by"], "Date": r["signed_at"][:16].replace("T", " "), "Note": ("⚠ file changed after sign-off" if r["changed_after_signoff"] else r["comment"])} for r in fl["rows"]]),
                     hide_index=True, use_container_width=True)
        stt = e["state"]
        cur_as = wf.assignees(ref)
        STG = (("preparer", "Preparer"), ("L1", "First reviewer"), ("L2", "Manager"), ("L3", "Partner"))
        with st.expander("👥 Allocate people to this file (pick a name for each stage)", expanded=any(not cur_as.get(rl) for rl, _ in STG)):
            st.caption("Pick a name for each stage - the flow table above and the review paper update at once. A person who is not in the list can be typed below and is added to the staff list.")
            cols = st.columns(4)
            for col, (rl, lab) in zip(cols, STG):
                opts = [""] + [n for n, r in users.items() if RANK_[r] >= RANK_[rl]]
                val = col.selectbox(lab, opts, index=opts.index(cur_as.get(rl, "")) if cur_as.get(rl, "") in opts else 0, key=f"as_{ref}_{rl}_{cur_as.get(rl, '')}")
                if val and val != cur_as.get(rl):
                    wf.assign(ref, rl, val, me, role); st.rerun()
            n1, n2, n3 = st.columns([3, 2, 1])
            newn = n1.text_input("Person not in the list - type the name", key=f"as_new_{ref}")
            newr = n2.selectbox("For stage", [lab for _, lab in STG], index=1, key=f"as_newr_{ref}")
            if n3.button("Add & allocate", disabled=not newn.strip(), key=f"as_add_{ref}"):
                rl = next(r for r, lab in STG if lab == newr)
                wf.add_staff(newn.strip(), RL[rl] if rl in RL else newr)
                wf.assign(ref, rl, newn.strip(), me, role); st.rerun()
            sb = [x for x in (st.session_state.get("tm_prep"), st.session_state.get("tm_r1"), st.session_state.get("tm_r2"), st.session_state.get("tm_r3"))]
            if any(sb) and st.button("Use the team picked in the sidebar", key=f"as_sb_{ref}"):
                for (rl, _lab), nm in zip(STG, sb):
                    if nm:
                        wf.assign(ref, rl, nm, me, role)
                st.rerun()
        pts = wf.points(ref)
        openp = [p for p in pts if p["status"] in ("OPEN", "RESPONDED", "REOPENED")]
        m1, m2, m3 = st.columns(3)
        m1.metric("Open points", len(openp)); m2.metric("Blocking (High/Medium)", len(wf.blocking_open(ref))); m3.metric("Closed", len(pts) - len(openp))

        if stt.endswith(("READY", "REVIEW")) and stt != "SIGNED_OFF":
            st.markdown(f"##### {wf.names[cur]} - load the latest review run")
            up = st.file_uploader("Review run (.json created by a review tab)", type=["json"], key="wf_json")
            if st.button("Load run into this round", disabled=not up):
                with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                    try:
                        r = wf.ingest(ref, _save(up, tmp), me, role); st.success(f"Round {r['round']}: {r['new']} new, {r['reopened']} reopened, {r['auto_cleared']} auto-cleared"); st.rerun()
                    except WorkflowError as ex:
                        st.error(str(ex))
        if stt.endswith("REVIEW"):
            with st.expander("Add a manual review point (judgement items the engine cannot test)"):
                t1 = st.text_input("Review point", key="wf_mt"); sv = st.selectbox("Severity", ["High", "Medium", "Low"], key="wf_ms")
                d1 = st.text_area("Detail", key="wf_md"); l1 = st.text_input("Page / evidence", key="wf_ml")
                if st.button("Add point", disabled=not t1):
                    try:
                        wf.add_manual_point(ref, t1, sv, d1, l1, me, role); st.rerun()
                    except WorkflowError as ex:
                        st.error(str(ex))

        if pts:
            st.markdown("##### Review points")
            df = pd.DataFrame([{"#": p["id"], "Raised": f"{p['raised_level']} R{p['raised_round']}", "Check": p["check_id"], "Sev": p["severity"], "Point": p["title"], "Page / evidence": p["location"],
                                "Status": p["status"], "Preparer response": p["response"] or "", "Preparer comment": p["response_note"] or "", "Reviewer note": p["decision_note"] or ""} for p in pts])
            if stt.endswith("REWORK"):
                st.caption("Preparer: answer every open point, then submit.")
                cfgc = {"Preparer response": st.column_config.SelectboxColumn(options=[""] + list(RESPONSES))}
                ed = st.data_editor(df, hide_index=True, use_container_width=True, key=f"wf_pe_{ref}", column_config=cfgc,
                                    disabled=[c for c in df.columns if c not in ("Preparer response", "Preparer comment")])
                cA, cB = st.columns(2)
                if cA.button("Save responses"):
                    n = 0
                    for _, r in ed.iterrows():
                        if r["Preparer response"] and r["Status"] in ("OPEN", "REOPENED", "RESPONDED"):
                            try:
                                wf.respond(int(r["#"]), r["Preparer response"], r["Preparer comment"] or "", me, role); n += 1
                            except WorkflowError as ex:
                                st.error(f"#{r['#']}: {ex}")
                    st.success(f"{n} response(s) saved"); st.rerun()
                upf = st.file_uploader("Upload the corrected / updated file (kept with this engagement)", key=f"wf_upd_{ref}")
                if cB.button("Submit corrected file for review", type="primary"):
                    try:
                        if upf:
                            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpd:
                                wf.attach(ref, _save(upf, tmpd), me, role, "Corrected file", "submitted for review")
                        wf.submit_for_review(ref, me, role); st.rerun()
                    except WorkflowError as ex:
                        st.error(str(ex))
            elif stt.endswith("REVIEW"):
                st.caption("Reviewer: clear each point once verified, reopen with a reason, or (Manager/Partner only) waive with a reason.")
                df["Decision"] = ""; df["Reason"] = ""
                cfgc = {"Decision": st.column_config.SelectboxColumn(options=[""] + list(DECISIONS))}
                ed = st.data_editor(df, hide_index=True, use_container_width=True, key=f"wf_re_{ref}", column_config=cfgc,
                                    disabled=[c for c in df.columns if c not in ("Decision", "Reason")])
                cA, cB = st.columns(2)
                if cA.button("Save decisions"):
                    n = 0
                    for _, r in ed.iterrows():
                        if r["Decision"]:
                            try:
                                wf.decide(int(r["#"]), r["Decision"], r["Reason"] or "", me, role); n += 1
                            except WorkflowError as ex:
                                st.error(f"#{r['#']}: {ex}")
                    st.success(f"{n} decision(s) saved"); st.rerun()
                mk = st.file_uploader("Marked-up file / review paper for this round (optional)", key=f"wf_mk_{ref}")
                sg = st.checkbox(f"I have completed the {wf.names[cur]} and sign it off as {me}", key=f"wf_sg_{ref}")
                sgc = st.text_input("Sign-off comment (optional)", key=f"wf_sgc_{ref}")
                if cB.button("Close this review round", type="primary"):
                    try:
                        if mk:
                            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpd:
                                wf.attach(ref, _save(mk, tmpd), me, role, "Reviewer file", "round close")
                        st.success(wf.complete_round(ref, me, role, signed=sg, comment=sgc)); st.rerun()
                    except WorkflowError as ex:
                        st.error(str(ex))
            else:
                st.dataframe(df, hide_index=True, use_container_width=True)
        if stt.endswith("READY") and not pts:
            pass
        with st.expander("🖋 Stamp the review status and sign-offs onto a Final Review Paper (.docx)"):
            sp = st.file_uploader("Final Review Paper (Word)", type=["docx"], key=f"wf_stamp_{ref}")
            if sp:
                with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpd:
                    outp = wf.stamp_docx(ref, _save(sp, tmpd), Path(tmpd) / f"{Path(sp.name).stem}_STATUS.docx")
                    st.download_button("⬇ Download stamped review paper", outp.read_bytes(), file_name=outp.name, key=f"wf_stamp_dl_{ref}")
            st.caption("Adds a banner such as 'PENDING - Manager review awaiting start (Meera)', the stage table, and fills Name/Date in the paper's sign-off table.")
        st.markdown("##### Hand-off message (copy into Teams)")
        st.code(wf.handoff_message(ref, cfg.get("app_url", "")), language=None)
        fl = wf.attachments(ref)
        if fl:
            with st.expander(f"📎 Files kept with this engagement ({len(fl)})"):
                for a in fl:
                    st.caption(f"{a['at']} · {a['who']} · {a['level']} · {a['kind']} · {a['filename']} · sha {a['sha'][:10]}")
                    if Path(a["stored"]).exists():
                        st.download_button("⬇ " + a["filename"], Path(a["stored"]).read_bytes(), file_name=a["filename"], key=f"dl_{a['id']}")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            xp = wf.export_trail(ref, Path(tmp) / f"{ref}_review_trail.xlsx")
            st.download_button("⬇ Review trail (Excel: points, rounds, audit log)", xp.read_bytes(), file_name=f"{ref}_review_trail.xlsx")

st.markdown('<div class="foot">UAE audit and tax · Offline review engine · Not a substitute for reviewer judgement</div>', unsafe_allow_html=True)
