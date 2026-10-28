"""EditLog Auditor (Rule 11(g)).  Run:  streamlit run app.py

Layout: 1 Settings (what stays the same for the client)  ->  2 Input (get the data from Tally)  ->  3 Edit Log Findings (the tests)
        ->  4 Guided audit (ICAI judgement steps)  ->  5 Reports (opinion wording and downloads)  ->  6 History.
"""
import io
import os
import re
import threading
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import checks
import editlog_import
import importlib
importlib.reload(editlog_import)   # a running Streamlit keeps old modules in memory after an update
import extract as X
import guided
import workpapers as W
import opinion
import tally_connector as tc

HERE = Path(__file__).parent
COLORS = {"High": "#d62728", "Medium": "#ff9f1c", "Low": "#7b8794"}
DROP = Path(os.environ.get("AT_DROP", r"C:\AuditTrail\Drop"))
st.set_page_config(page_title="EditLog Auditor", page_icon="🧾", layout="wide")

# ------------------------------------------------------------------ column mapping for uploads
SYN = {
    "LogTime": ["logtime", "altered on", "date and time", "timestamp", "modified on", "time"],
    "User": ["user", "altered by", "changed by", "modified by", "created by"],
    "Action": ["action", "activity", "operation", "change type"],
    "VoucherType": ["vouchertype", "voucher type", "vch type"],
    "VoucherNo": ["voucherno", "voucher no", "voucher number", "vch no"],
    "VoucherDate": ["voucherdate", "voucher date", "vch date", "date"],
    "Field": ["field"], "OldValue": ["oldvalue", "old value", "before"], "NewValue": ["newvalue", "new value", "after"],
    "Amount": ["amount", "debit amount", "value"], "Party": ["party", "particulars", "ledger"],
}


def read_any(up):
    """CSV or Excel upload. Tally exports Excel by default; for Excel the first sheet is read, header row auto-detected."""
    if up.name.lower().endswith((".xlsx", ".xls")):
        raw = pd.read_excel(up, header=None)
        hdr = next((i for i in range(min(len(raw), 30)) if raw.iloc[i].notna().sum() >= max(3, raw.shape[1] // 2)), 0)
        df = raw.iloc[hdr + 1:].copy()
        df.columns = [str(c) if pd.notna(c) else f"col{i}" for i, c in enumerate(raw.iloc[hdr])]
        return df.dropna(how="all").reset_index(drop=True)
    name = up.name.lower()
    if name.endswith(".json"):
        import json
        data = json.load(up)
        return pd.json_normalize(data if isinstance(data, list) else next((v for v in data.values() if isinstance(v, list)), [data]))
    if name.endswith(".xml"):
        return pd.read_xml(up)
    return pd.read_csv(up)


def _n(s):
    return re.sub(r"[^a-z]", "", str(s).lower())


def guess(cols, name):
    keys = [_n(k) for k in SYN.get(name, [name])]
    for k in keys:
        for c in cols:
            if _n(c) == k:
                return c
    for k in keys:
        for c in cols:
            if k and k in _n(c):
                return c
    return None


def map_ui(df, required, optional, prefix):
    cols = list(df.columns)
    out = pd.DataFrame(index=df.index)
    for name in required + optional:
        g = guess(cols, name)
        opts = ["(none)"] + cols
        if name == "Amount" and any("debit" in _n(c) for c in cols) and any("credit" in _n(c) for c in cols):
            opts.append("(Debit + Credit)")
        pick = st.selectbox(name + ("" if name in required else " (optional)"), opts,
                            index=opts.index(g) if g in opts else 0, key=f"{prefix}_{name}", help='Match each column of your file to the field the checker needs. Optional fields improve the tests but are not required.')
        if pick == "(Debit + Credit)":
            dc = [c for c in cols if "debit" in _n(c)][0]
            cc = [c for c in cols if "credit" in _n(c)][0]
            out[name] = pd.to_numeric(df[dc], errors="coerce").fillna(0) + pd.to_numeric(df[cc], errors="coerce").fillna(0)
        elif pick == "(none)":
            if name in required:
                st.warning(f"Map {name} to continue")
                st.stop()
            out[name] = ""
        else:
            out[name] = df[pick]
    return out



# Start from Tally: on the first load look for the companies that are open in TallyPrime (quiet, short timeout).
if "tl_auto_done" not in st.session_state:
    st.session_state["tl_auto_done"] = True
    try:
        st.session_state["tl_companies"] = tc.TallyConnector("localhost", 9000, timeout=6).list_companies()
        st.session_state["tl_auto_err"] = ""
    except Exception as e_:
        st.session_state["tl_companies"] = []
        st.session_state["tl_auto_err"] = str(e_)
    _c0 = [c["name"] for c in st.session_state["tl_companies"]]
    if _c0 and st.session_state.get("co_name", "") not in _c0:
        st.session_state["co_name"] = _c0[0]

import history as H
HIST = H.History(HERE / "state" / "history.db")
_GUIDED_PREFIX = ("gap_", "gcf_", "gr_", "gn_", "grp_", "gp_", "gw_", "wpn_", "wpd_", "gwp_", "g_inv", "g_fyend", "g_comp_", "in_co_pick",
                  "set_co_", "fys_", "fye_", "fin_", "el_types_", "el_mon_", "h_co_")
_DATA_KEYS = ("tl_reg", "tl_log", "tl_log_raw", "tl_log_raw_name", "tl_rawtdl", "tl_masters", "tl_meta", "eng", "g_concl", "ex_loaded",
              "wp_open", "confirm_all_flag", "am_memo", "tl_self", "tl_probe", "hist_loaded")


def _close_open_company():
    """Forget the company that is open now, so that the next one starts clean."""
    for k_ in list(st.session_state.keys()):
        if k_ in _DATA_KEYS or str(k_).startswith(_GUIDED_PREFIX):
            del st.session_state[k_]


_pend = st.session_state.pop("hist_pending", None)
if _pend:                                            # a saved check was chosen on the History tab: swap the open company for it
    _sn = HIST.snapshot(_pend)
    if _sn:
        _close_open_company()
        st.session_state["tl_reg"], st.session_state["tl_log"] = _sn["reg_raw"], _sn["log_raw"]
        for _k in ("tl_rawtdl", "tl_masters"):
            if _sn.get(_k) is not None:
                st.session_state[_k] = _sn[_k]
        st.session_state["tl_meta"] = (_sn["company"], _sn["fy_start"], _sn["fy_end"], len(_sn["reg_raw"]))
        st.session_state["co_name"] = _sn["company"]
        st.session_state["src_radio"] = "Pull from Tally"
        for _k, _v in _sn.get("params", {}).items():
            st.session_state[_k] = _v
        st.session_state[f"fin_{_sn['fy_end']}"] = _sn["finalised"]
        try:
            st.session_state["eng"] = H.eng_from_json(HIST.engagement(_pend), guided.Engagement)
        except Exception:
            pass
        st.session_state["hist_loaded"] = {"id": _pend, "saved_at": _sn.get("saved_at", ""), "company": _sn["company"]}
        st.session_state["main_tabs"] = "📊 3 · Edit Log Findings"      # open the workspace on the results
        st.session_state["hist_note"] = f"Loaded {_sn['company']} (check #{_pend}). The previously open company was closed."

def tally_alert(co: str):
    """Red notice when the selected company is not among the companies open in TallyPrime."""
    opened = [c["name"].strip().lower() for c in st.session_state.get("tl_companies", [])]
    if co and (co.strip().lower() not in opened):
        st.error(f"Open the relevant company in Tally: **{co}** is not open in TallyPrime now. "
                 "Open it there, then press Refresh list on the Input tab.", icon="🔴")


def hint(text: str):
    """Symbol-only hint button: a small ℹ️ that opens a note explaining what the section is for."""
    with st.popover("ℹ️", help="What is this section for?"):
        st.markdown(text)


st.title("🧾 EditLog Auditor")
st.caption("Rule 11(g) of the Companies (Audit and Auditors) Rules, 2014. Work left to right: Settings → Input → Edit Log Findings → Guided audit → Reports → History.")
_TABS = ["⚙️ 1 · Settings", "📥 2 · Input", "📊 3 · Edit Log Findings", "🧭 4 · Guided audit (ICAI)", "📤 5 · Reports", "🗂️ 6 · History"]
try:
    (tab_set, tab_in, tab_res, tab_guide, tab_rep, tab_hist) = st.tabs(_TABS, key="main_tabs", on_change="rerun")
except TypeError:                                    # older Streamlit: no programmatic tab selection
    (tab_set, tab_in, tab_res, tab_guide, tab_rep, tab_hist) = st.tabs(_TABS)

# ================================================================== 1 · SETTINGS
with tab_set:
    st.subheader("Settings")
    st.caption("Things that stay the same for the client and the year. The data itself goes in on the Input tab.")
    s1, s2 = st.columns(2)
    with s1:
        _h1, _h2 = st.columns([8, 1]); _h1.markdown("**Engagement**")
        with _h2: hint("The client and year you are reporting on. Company and dates are used in every test, working paper and report. "
                       "The company comes from Tally when it is open; the year defaults to the previous financial year.")
        _co = st.session_state.get("co_name", "")
        comps = [c["name"] for c in st.session_state.get("tl_companies", [])]
        if _co and comps and _co not in comps:
            comps = comps + [_co]                 # e.g. a company loaded from History that is not open in Tally now
        if comps:
            t_comp = st.selectbox("Company", comps, index=comps.index(_co) if _co in comps else 0, help='The Tally company this check is for. It fills the company name everywhere else (opinion, guided audit, history).')
        else:
            t_comp = st.text_input("Company (exactly as in Tally)", _co, key=f"set_co_{_co or 'none'}", help='Type the company name exactly as Tally shows it. Tally matches on the exact name when the tool pulls data.')
        st.session_state["co_name"] = t_comp
        _tm = st.session_state.get("tl_meta")
        _today = date.today()
        _fy0 = date((_today.year if _today.month >= 4 else _today.year - 1) - 1, 4, 1)   # default: the previous financial year
        fy_start = st.date_input("Financial year starts", _tm[1] if _tm else _fy0, key=f"fys_{_tm[1] if _tm else 0}", help='First day of the year being audited. Default is the previous financial year. The Edit Log is pulled for this period.')
        fy_end = st.date_input("Financial year ends", _tm[2] if _tm else date(_fy0.year + 1, 3, 31), key=f"fye_{_tm[2] if _tm else 0}", help='Last day of the year being audited. Entries after this date are flagged as post-year-end changes.')
        _prof = HERE / "state" / "profile.json"
        try:
            import json as _json
            _aud0 = _json.loads(_prof.read_text(encoding="utf-8")).get("auditor", "") if _prof.exists() else ""
        except Exception:
            _aud0 = ""
        auditor_name = st.text_input("Auditor / firm name (signs the report)", st.session_state.get("auditor_name", _aud0), key="auditor_name",
                                     help="The statutory auditor or audit firm, for example 'KIRAN R & Associates, Chartered Accountants'. It is the addressee of the management representation letter and appears on the working paper. It is not the company being audited. Saved on this computer.")
        if auditor_name != _aud0:
            try:
                import json as _json
                _prof.parent.mkdir(parents=True, exist_ok=True)
                _prof.write_text(_json.dumps({"auditor": auditor_name}), encoding="utf-8")
            except Exception:
                pass
        finalised = st.date_input("Books finalised on", date(fy_end.year, 4, 30), key=f"fin_{fy_end}", help='Date the books were closed or signed off. Default is 30 April after the year end. Changes made after this date are flagged (test B1).')
    with s2:
        _h1, _h2 = st.columns([8, 1]); _h1.markdown("**Test thresholds**")
        with _h2: hint("These settings decide how sensitive the tests are. The defaults suit most engagements; tighten them for high-risk "
                       "clients and record any change in the working paper.")
        backdate = st.slider("Back-dated if created more than (days)", 5, 90, 30, key="th_backdate", help='A voucher entered more than this many days after its own date is flagged as back-dated (test B2). Raise it if month-end entries are normal.')
        big = st.number_input("High-value limit (₹)", 100_000, 10_000_000, 500_000, step=100_000, key="th_big", help='Changes to vouchers above this value are given a higher risk level. Set it near the engagement materiality or a performance-materiality fraction.')
        gap = st.slider("Silent run of working days", 2, 10, 4, key="th_gap", help='If no Edit Log activity occurs for this many working days while the company is posting vouchers, a possible logging gap is raised (test A2).')
        generic = st.text_input("Generic user-ID words", ", ".join(checks.GENERIC_TOKENS), key="th_generic", help='Words that mark shared or generic logins, such as admin or test. Alterations or deletions by such IDs are flagged (test D2). Separate with commas.')

    _h1, _h2 = st.columns([12, 1]); _h1.markdown("**Connection to TallyPrime**")
    with _h2: hint("How the checker talks to TallyPrime on this PC. Tally must be open, the company loaded and the HTTP server on (F1 Help, "
                   "Settings, Connectivity, port 9000). The tool only reads; it never changes data in Tally.")
    k1, k2, k3 = st.columns([2, 1, 1])
    t_host = k1.text_input("Tally host", "localhost", help='The computer running TallyPrime. Use localhost when Tally is on this same PC.')
    t_port = k2.number_input("Port", 1, 65535, 9000, help="The port of Tally's HTTP server. The default is 9000 (F1 Help, Settings, Connectivity).")
    conn = tc.TallyConnector(t_host, int(t_port))
    k3.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
    if k3.button("Test connection / list companies", width="stretch", help='Checks that Tally is reachable and lists the companies that are open in it.'):
        try:
            st.session_state["tl_companies"] = conn.list_companies()
            st.success(f"Connected. {len(st.session_state['tl_companies'])} company(ies) open in Tally.")
            st.rerun()
        except tc.TallyError as e:
            st.session_state["tl_companies"] = []
            st.error(f"{e}")
    st.caption("Tally must be open on this computer, with the company open and the HTTP server on "
               "(F1 Help → Settings → Connectivity → Client/Server configuration, port 9000).")

    _h1, _h2 = st.columns([12, 1]); _h1.markdown("**Folders and file format for the Edit Log**")
    with _h2: hint("Tally does not release the Edit Log through its data connection, so the tool presses Tally's own export keys. "
                   "Tally writes each export to the 'export' folder; the tool checks it and moves it to the 'collection' folder.")
    g1, g2, g3 = st.columns([2, 2, 2])
    fold_s = g1.text_input("Folder for the Edit Log files the tool collects", st.session_state.get("el_folder", str(DROP)), key="el_folder_in", help='Where the tool keeps the Edit Log files it collects, one per voucher type and month. It reads and loads them from here.')
    st.session_state["el_folder"] = fold_s
    FOLD = Path(fold_s)
    out_dir = g2.text_input("Folder where TallyPrime saves its export", st.session_state.get("tl_out", r"C:\AuditTrail\TallyOut"), key="tl_out_in", help="The folder set in Tally's export screen (Ctrl+E, Configure, Folder Path). The tool picks each export up from here, so the two must be the same.")
    st.session_state["tl_out"] = out_dir
    fmt_labels = [f"{k}  (suggested)" if k == X.SUGGESTED_FORMAT else k for k in X.FORMATS]
    fmt = g3.selectbox("File format Tally should save", fmt_labels, 0, help='The format Tally writes when the tool exports. ASCII is the most reliable to read; the others are also supported.').replace("  (suggested)", "")
    ext = X.FORMATS[fmt]
    if g1.button("Open / create these folders", help='Creates the two folders if they do not exist and opens the collection folder in Explorer.'):
        try:
            for p_ in (FOLD, Path(out_dir)):
                p_.mkdir(parents=True, exist_ok=True)
            if hasattr(os, "startfile"):
                os.startfile(str(FOLD))
        except Exception as e_:
            st.error(f"Could not create the folders: {e_}")
    with st.expander("Advanced extraction settings"):
        tog = st.checkbox("Press Alt+F5 on each list to switch to the detailed view (only if the test shows no version lines)", False, help="Alt+F5 switches Tally's Edit Log list to the detailed view with one line per version. Tick only if the first-month test shows no version lines.")
        esc = st.number_input("Escape presses after each export", 1, 5, 2, help='How many times the tool presses Esc after an export to return to the Voucher Type list. Increase if the screens drift.')

    with st.expander("One-time set-up in TallyPrime (needed for the Edit Log extraction)"):
        st.markdown(f"""
1. Open the company in Tally and log in yourself (the tool never types a password).
2. Press **Alt+G**, type *Edit Log Summary*, choose **Voucher Types**. Press **F5** (all vouchers) and **F9** (all versions); the heading must read *All Vouchers for Any Activity - All Versions*.
3. Press **Ctrl+E**, then **C** (Configure). Set **File Format** to *{fmt}* and **Folder Path** to *{out_dir}* (create the folder first). Leave **File Name** as it is. Close the dialogs with **Esc** and stay on the Voucher Type list.
4. For the voucher register itself, also turn on the HTTP server (F1 Help → Settings → Connectivity, port 9000).

Optional: *AuditTrail_EditLog.tdl* adds master-data changes and Company Activity (Gateway of Tally → Audit Trail - Edit Log Export). It cannot read the per-voucher versions on this Tally release, so it is not needed for the voucher-level work.
""")
        tdl_path = HERE / "tdl" / "AuditTrail_EditLog.tdl"
        if tdl_path.exists():
            st.download_button("Download AuditTrail_EditLog.tdl (optional)", tdl_path.read_text(encoding="utf-8"), "AuditTrail_EditLog.tdl", key="dl_199")
    st.caption("This tool reads and exports. It does not change anything in Tally. Use dummy or anonymised data when presenting; do not paste real client data into AI tools.")

st.session_state.setdefault("eng", guided.Engagement(fy_end=fy_end)).auditor = st.session_state.get("auditor_name", "")

# ================================================================== 2 · INPUT
with tab_in:
    st.subheader("Input")
    _opts = ["Pull from Tally", "Upload files", "Sample data (fictional)"]
    src = st.radio("Where does the data come from?", _opts, index=0, horizontal=True, key="src_radio", help='Pull from Tally reads the open company directly. Upload files is for a Tally on another PC. Sample data is fictional, for practice only.')
    reg_raw = log_raw = None
    t_from, t_to = fy_start, fy_end

    def _take_tdl(raw_, label):
        """Version rows (any source) -> checker log, master changes, company activity."""
        if len(raw_) == 0:
            st.error(f"{label}: 0 version rows. Nothing was loaded.")
            return False
        st.session_state["tl_log"] = editlog_import.convert(raw_)
        st.session_state["tl_masters"] = editlog_import.convert_masters(raw_)
        st.session_state["tl_rawtdl"] = raw_
        m_ = st.session_state["tl_masters"]
        st.success(f"{label}: {len(raw_):,} version rows → {len(st.session_state['tl_log']):,} voucher log entries"
                   f" + {int((m_.Object != 'Company').sum()):,} master-data changes + {int((m_.Object == 'Company').sum()):,} company activities.")
        return True

    def _load_files(items, label):
        got_, tables_, bad_ = [], [], []
        for nm_, by_ in items:
            kind_, df_ = editlog_import.parse_file(nm_, by_)
            if kind_ in ("summary", "tdl"):
                got_.append(df_)
            elif kind_ == "table":
                tables_.append((nm_, df_))
            else:
                bad_.append(nm_)
        if bad_:
            st.warning("Not readable as an Edit Log (skipped): " + ", ".join(bad_))
        if got_:
            d_ = pd.concat(got_, ignore_index=True)
            d_ = d_.drop_duplicates(subset=[c for c in ("Source", "MasterID", "Version", "LogTime", "User") if c in d_.columns])
            if _take_tdl(d_, f"{label} ({len(got_)} file(s))"):
                return True
        if tables_:
            st.session_state["tl_log_raw"] = tables_[0][1]
            st.session_state["tl_log_raw_name"] = tables_[0][0]
        return False

    if src == "Sample data (fictional)":
        st.info("Showing the built-in fictional sample so that you can see every screen. Choose **Pull from Tally** to work on a real company.")

    elif src == "Upload files":
        st.caption("Use this if Tally is on another computer. Export the Day Book (voucher register) and the Edit Log from Tally and upload both.")
        up_reg = st.file_uploader("Voucher register / Day Book (CSV, Excel, JSON or XML)", type=["csv", "xlsx", "xls", "json", "xml"], help='The Day Book or voucher register exported from Tally: one row per voucher with type, number, date and amount.')
        up_log = st.file_uploader("Edit Log (Tally's Edit Log Summary export, or any CSV, Excel, JSON or XML)",
                                  type=["txt", "csv", "xlsx", "xls", "json", "xml", "html"], help="Tally's Edit Log Summary export (any format) or a table with user, date-time, action and voucher.")
        if up_reg and up_log:
            reg_raw = read_any(up_reg)
            kind_, df_ = editlog_import.parse_file(up_log.name, up_log.getvalue())
            if kind_ in ("summary", "tdl"):
                st.session_state["tl_masters"] = editlog_import.convert_masters(df_)
                st.session_state["tl_rawtdl"] = df_
                log_raw = editlog_import.convert(df_)
                st.success(f"Tally Edit Log recognised: {len(df_):,} version lines.")
            else:
                with st.expander("Map edit-log columns", expanded=True):
                    log_raw = map_ui(df_ if len(df_) else read_any(up_log), ["LogTime", "User", "Action", "VoucherType", "VoucherNo", "VoucherDate"],
                                     ["Field", "OldValue", "NewValue", "Amount"], "log")
            with st.expander("Map register columns", expanded=True):
                reg_raw = map_ui(reg_raw, ["VoucherType", "VoucherNo", "VoucherDate", "Amount"], ["Party"], "reg")
        else:
            st.info("Upload both files, then map the columns if asked.")

    else:   # ---- Pull from Tally
        # ---- company picker: companies currently open in TallyPrime
        def _pick_co():
            st.session_state["co_name"] = st.session_state["in_co_pick"]

        pc1, pc2 = st.columns([4, 1])
        _open = [c["name"] for c in st.session_state.get("tl_companies", [])]
        _cur = st.session_state.get("co_name", "")
        if _open and _cur and _cur not in _open and st.session_state.get("hist_loaded"):
            _open = _open + [_cur]                # company loaded from History; Tally may not have it open
        if _open:
            pc1.selectbox("Companies open in TallyPrime", _open, index=_open.index(_cur) if _cur in _open else 0,
                          key="in_co_pick", on_change=_pick_co)
            t_comp = st.session_state.get("in_co_pick", t_comp)
            st.session_state["co_name"] = t_comp
        else:
            pc1.warning("No open company found in TallyPrime. " + (st.session_state.get("tl_auto_err") or "")
                        + " Open TallyPrime, log in, load the company, switch on the HTTP server (port 9000) and press Refresh.")
        pc2.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
        if pc2.button("🔄 Refresh list", width="stretch", help='Asks Tally again which companies are open. Use it after you open or change a company in Tally.'):
            try:
                st.session_state["tl_companies"] = conn.list_companies()
                st.session_state["tl_auto_err"] = ""
            except tc.TallyError as e:
                st.session_state["tl_companies"] = []
                st.session_state["tl_auto_err"] = str(e)
            st.rerun()
        if st.session_state.get("hist_loaded"):
            _hl = st.session_state["hist_loaded"]
            st.info(f"Showing the saved data of **{_hl['company']}** (check #{_hl['id']}, saved {_hl['saved_at']}), not a live pull. "
                    "Press **Pull vouchers from Tally** to refresh it from Tally.")
        tally_alert(t_comp)
        if not t_comp:
            st.warning("Choose the company above (or type it on the **Settings** tab).")
        st.markdown(f"**Company:** {t_comp or '-'}  ·  **Year:** {fy_start:%d-%b-%Y} to {fy_end:%d-%b-%Y}  ·  **Tally:** {t_host}:{int(t_port)}")

        # ---- step 1: vouchers
        st.markdown("**Step 1 · Voucher register** (read-only, straight from Tally)")
        with st.expander("Diagnostics (only if the pull fails)"):
            attr = st.text_input("User field in Tally (optional)", "", help="Fill after 'Check fields' shows which field carries the user")
            d1_, d2_ = st.columns(2)
            if d1_.button("Self-test", width="stretch", disabled=not t_comp, help='Runs a short series of requests to see which part of the connection to Tally fails.'):
                with st.spinner("Testing…"):
                    st.session_state["tl_self"] = pd.DataFrame(conn.selftest(t_comp, t_from, t_to))
            if d2_.button("Check fields", width="stretch", disabled=not t_comp, help='Shows which voucher fields Tally returns, so you can find the one that carries the user name.'):
                try:
                    st.session_state["tl_probe"] = pd.DataFrame(conn.probe_fields(t_comp, t_from, t_to))
                except tc.TallyError as e:
                    st.error(f"{e}")
            for k_ in ("tl_self", "tl_probe"):
                if k_ in st.session_state:
                    st.dataframe(st.session_state[k_], hide_index=True, width="stretch")
        if st.button("Pull vouchers from Tally", type="primary", disabled=not t_comp, help='Reads every voucher for the Settings period straight from Tally. Read-only; nothing in Tally is changed.'):
            try:
                with st.spinner("Fetching from Tally…"):
                    v = conn.fetch_vouchers(t_comp, t_from, t_to, extra_fields=[attr] if attr else ())
                st.session_state.pop("hist_loaded", None)
                st.session_state["tl_reg"] = tc.to_register(v)
                st.session_state["tl_meta"] = (t_comp, t_from, t_to, len(v))
                st.rerun()
            except tc.TallyError as e:
                st.error(f"Could not pull from Tally: {e}")
                st.info("Fallback: choose **Upload files** above and use a Day Book export.")
        if "tl_reg" in st.session_state:
            _m = st.session_state.get("tl_meta") or (t_comp, t_from, t_to, len(st.session_state["tl_reg"]))
            n, comp_, f_, t_ = _m[3], *_m[:3]
            st.success(f"✅ {n:,} vouchers pulled for {comp_} ({f_:%d-%b-%Y} to {t_:%d-%b-%Y}).")
        st.divider()

        # ---- step 2: edit log, version by version
        st.markdown("**Step 2 · Edit Log** (every version of every voucher)")
        st.caption("The tool presses these keys on Tally for you, one voucher type and month at a time, and checks each file. "
                   "It never types a user name or password and changes nothing in Tally.")
        st.code('Gateway of Tally  >  Display more reports  >  Edit Log Summary\n'
                'F5 "All vouchers"  >  F9 "All versions"  >  Period (F2, as set on the Settings tab)\n'
                'Export current (Ctrl+E)  >  File format: ASCII (Comma Delimited)', language=None)
        reg_ = st.session_state.get("tl_reg")
        types_default = sorted(reg_["VoucherType"].astype(str).unique()) if reg_ is not None and len(reg_) else []
        with st.expander("Voucher types and months to extract", expanded=False):
            types_txt = st.text_area("Voucher types, one per line, in the order Tally lists them (alphabetical on the screens seen)",
                                     "\n".join(types_default), height=120,
                                     key="el_types_" + str(abs(hash(tuple(types_default)))), help='The voucher types to export, in the order Tally lists them. Filled from the register; edit only if Tally lists them differently.')
            mon_all = [X.month_name(t_from, i) for i in range(12)]
            mon_pick = st.multiselect("Months", mon_all, mon_all, key=f"el_mon_{t_from}", help='The months to export. All twelve are selected; deselect to test one month only.')
        tp = [t.strip() for t in types_txt.splitlines() if t.strip()] or types_default
        mon_pick = mon_pick or mon_all
        plan_ = X.build_plan(tp, t_from, reg_, [mon_all.index(m) for m in mon_pick]) if tp and mon_pick else []
        if reg_ is None:
            st.info("Pull the vouchers first (Step 1); the tool then knows which voucher types and months to export.")
        elif plan_:
            st.caption(f"{len(plan_)} export(s) planned: every voucher type and month that has vouchers in the register.")
        else:
            _dd_ = editlog_import._dt(reg_["VoucherDate"]) if len(reg_) else pd.Series(dtype="datetime64[ns]")
            _in = int(((_dd_ >= pd.Timestamp(t_from)) & (_dd_ <= pd.Timestamp(t_to))).sum()) if len(reg_) else 0
            st.warning(f"0 exports planned, so the buttons are off. Register: {len(reg_):,} vouchers, {_in:,} dated inside "
                       f"{t_from:%d-%b-%Y} to {t_to:%d-%b-%Y}; voucher types listed: {len(tp)}; months chosen: {len(mon_pick)}. "
                       "Check the Financial year dates on Settings (they must match the pulled period) and the list under 'Voucher types and months'.")
        stf, stopf = HERE / "state" / "extract_state.json", HERE / "state" / "extract_stop"
        stf.parent.mkdir(parents=True, exist_ok=True)
        thr = st.session_state.get("ex_thread")
        running = bool(thr and thr.is_alive())

        def _start(items):
            if stopf.exists():
                stopf.unlink()
            try:
                snd = X.WinKeys()
            except Exception as e_:
                st.error(f"{e_}")
                return
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            st.session_state.pop("ex_loaded", None)
            t_ = threading.Thread(target=X.run, daemon=True, args=(items, snd, Path(out_dir), FOLD, ext, stf, stopf),
                                  kwargs={"detailed_toggle": tog, "escapes_after": int(esc), "period": (t_from, t_to)})
            st.session_state["ex_thread"] = t_
            t_.start()
            st.rerun()
        b1, b2, b3 = st.columns([3, 2, 1])
        if b1.button("⬇ Pull Edit Log from Tally", type="primary", disabled=running or not plan_, width="stretch",
                     help="Takes over the keyboard for a few minutes. Keep Tally on the Voucher Type list, logged in, and do not touch the keyboard or mouse."):
            _start(plan_)
        if b2.button("Test with the first month", disabled=running or not plan_, width="stretch", help='Exports only the first voucher type and month, so you can check that the keys reach Tally before the full run.'):
            _start(plan_[:1])
        if b3.button("Stop", disabled=not running, width="stretch", help='Stops the extraction after the current export. Files already collected are kept.'):
            stopf.write_text("stop")

        @st.fragment(run_every=3 if running else None)
        def _prog():
            import json as _j
            if not stf.exists():
                return
            try:
                s_ = _j.loads(stf.read_text())
            except Exception:
                return
            st.progress(min(1.0, s_["done"] / max(1, s_["total"])), text=f"{s_['done']} of {s_['total']} done" + (f" · now: {s_['current']}" if s_.get("current") else ""))
            if s_["status"] == "finished":
                if st.session_state.get("ex_loaded") != s_["started"] and s_["files"]:
                    st.session_state["ex_loaded"] = s_["started"]
                    _load_files([(f, (FOLD / f).read_bytes()) for f in s_["files"] if (FOLD / f).exists()], "Edit Log pulled from Tally")
                    st.rerun()
                st.success(s_["message"])
            elif s_["status"] == "stopped":
                st.warning(s_["message"])
        _prog()

        with st.expander("Or load Edit Log files that you exported yourself (Ctrl+E in Tally)"):
            st.caption("Formats read: ASCII (CSV/TXT), Excel, HTML, JSON, XML. JPEG and PDF cannot be read.")
            EXT = (".txt", ".csv", ".asc", ".xlsx", ".xls", ".html", ".htm", ".json", ".xml")
            fl_ = sorted([f for f in FOLD.glob("*") if f.suffix.lower() in EXT and not f.name.startswith("PROBLEM_")],
                         key=lambda f: f.stat().st_mtime, reverse=True) if FOLD.exists() else []
            sel_ = st.multiselect(f"Files found in {FOLD} ({len(fl_)}), all selected", fl_, default=fl_,
                                  format_func=lambda f: f"{f.name}  ({pd.Timestamp(f.stat().st_mtime, unit='s'):%d-%b-%Y %H:%M})", help='Edit Log files found in the collection folder. All are selected; deselect any you do not want to load.') if fl_ else []
            ups = st.file_uploader("Or upload file(s) from another place", type=[e[1:] for e in EXT], accept_multiple_files=True, key="tl_up_any", help='Use if the Edit Log files are somewhere else, for example copied from another PC.')
            if st.button("Load these Edit Log files", disabled=not (ups or sel_), help='Reads the selected files and loads them as the Edit Log for the tests.'):
                _load_files([(u.name, u.getvalue()) for u in ups] + [(f.name, f.read_bytes()) for f in sel_], "Edit Log")
        if "tl_log_raw" in st.session_state:
            with st.expander(f"Match the columns of {st.session_state.get('tl_log_raw_name', 'the file')} (not a standard Tally Edit Log layout)", expanded=True):
                st.session_state["tl_log"] = map_ui(st.session_state["tl_log_raw"],
                                                    ["LogTime", "User", "Action", "VoucherType", "VoucherNo", "VoucherDate"],
                                                    ["Field", "OldValue", "NewValue", "Amount"], "tlog")
        if "tl_log" in st.session_state:
            st.success(f"✅ Edit Log loaded: {len(st.session_state['tl_log']):,} log entries ready for the tests.")

        cov = X.coverage(reg_, st.session_state.get("tl_rawtdl"), t_from)
        if len(cov):
            st.markdown("**Coverage:** vouchers in the register against vouchers found in the Edit Log")
            st.dataframe(cov, hide_index=True, width="stretch", height=min(300, 36 + 35 * len(cov)))
        st.divider()
        with st.expander("Step 3 (optional) · Master-data changes and Company Activity (needs AuditTrail_EditLog.tdl loaded in Tally)"):
            if st.button("Pull master and company activity", disabled=not t_comp, help='Optional. Reads ledger, group and stock-item changes and Company Activity through the TDL. Needs AuditTrail_EditLog.tdl loaded in Tally.'):
                try:
                    with st.spinner("Asking Tally…"):
                        g_ = conn.fetch_editlog_tdl(t_comp, t_from, t_to)
                    m_ = editlog_import.convert_masters(g_)
                    if len(m_):
                        st.session_state["tl_masters"] = m_
                        st.success(f"{int((m_.Object != 'Company').sum()):,} master-data changes and {int((m_.Object == 'Company').sum()):,} company activities loaded.")
                    else:
                        st.info("Nothing returned.")
                except tc.TallyError as e_:
                    st.error(f"{e_}")

        if "tl_reg" in st.session_state:
            reg_raw = st.session_state["tl_reg"]
        if "tl_log" in st.session_state:
            log_raw = st.session_state["tl_log"]

# ================================================================== compute
SAMPLE = src == "Sample data (fictional)"
if SAMPLE:
    reg_raw, log_raw = pd.read_csv(HERE / "data" / "vouchers.csv"), pd.read_csv(HERE / "data" / "editlog.csv")
    fy_start, fy_end, finalised = date(2025, 4, 1), date(2026, 3, 31), date(2026, 5, 31)


@st.cache_data(show_spinner=False)
def run(reg_df, log_df, fy_start, fy_end, finalised, backdate, big, gap, generic):
    p = checks.Params(fy_start=fy_start, fy_end=fy_end, finalised_on=finalised, backdate_days=backdate,
                      big_amount=float(big), gap_working_days=gap,
                      generic=tuple(w.strip().lower() for w in generic.split(",") if w.strip()))
    return checks.run_checks(checks.prepare_register(reg_df), checks.prepare_log(log_df), p)


# ================================================================== 6 · HISTORY
def render_history(has_data: bool):
    hist = HIST
    E_h = st.session_state.setdefault("eng", guided.Engagement(fy_end=fy_end))
    st.subheader("History of checks")
    st.caption("Every saved check keeps its data, test results, guided answers and reports. Click a row to see its results at once; "
               "selecting a row opens that company's whole workspace (Edit Log Findings, Guided audit, Reports) and closes the one that is open now.")
    if st.session_state.get("hist_note"):
        st.success(st.session_state.pop("hist_note"))
    co_h = st.session_state.get("co_name") or E_h.company or ""
    by_default = st.session_state.get("h_by", "")

    def _save_current(co_in, by_in, note_in):
        E_h.company = co_in
        concl_h = guided.conclude(E_h, res, None)
        raw_ = st.session_state.get("tl_rawtdl")
        mg_ = st.session_state.get("tl_masters")
        deleted_df = None
        n_del = n_alt = 0
        if raw_ is not None and len(raw_):
            _v = raw_[raw_["Action"].astype(str).str.lower().str.contains("delet|cancel")] if "Action" in raw_ else raw_.iloc[0:0]
            n_del = int(_v["MasterID"].nunique()) if len(_v) else 0
            n_alt = int((pd.to_numeric(raw_["Version"], errors="coerce") > 1).sum()) if "Version" in raw_ else 0
            deleted_df = _v[[c for c in ["VoucherDate", "VoucherType", "VoucherNo", "User", "LogTime"] if c in _v]]
        meta = dict(company=co_in, fy_start=str(fy_start), fy_end=str(fy_end), source=src, prepared_by=by_in,
                    conclusion=concl_h["conclusion"], vouchers=len(res.reg), log_events=len(log), exceptions=len(ex),
                    high=int((ex.Severity == "High").sum()), tests_failed=int((res.summary.Exceptions > 0).sum()),
                    tests_total=len(res.summary), deleted=n_del, altered=n_alt, notes=note_in)
        tag = re.sub(r"[^A-Za-z0-9]+", "_", co_in)[:30]
        files = [(f"{tag}_findings.xlsx", H.XLSX, checks.workbook(res)),
                 (f"{tag}_annexure_A_voucher_editlog.xlsx", H.XLSX,
                  guided.annexure_xlsx(raw_, log, mg_, res.reg, co_in, f"{fy_start} to {fy_end}")),
                 (f"{tag}_working_paper.docx", H.DOCX, guided.working_paper_docx(E_h, concl_h, res)),
                 (f"{tag}_representation_letter.docx", H.DOCX, guided.rep_letter_docx(E_h))]
        try:
            files.append((f"{tag}_check_summary.pdf", "application/pdf",
                          H.check_pdf({**meta, "saved_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}, res.summary,
                                      guided.control_summary(E_h), ex, deleted_df, caution=concl_h.get("caution"))))
        except ImportError:
            st.warning("PDF support (reportlab) is not installed yet: run INSTALL.bat again to add it. The check was saved without the PDF.")
        snap = dict(company=co_in, fy_start=fy_start, fy_end=fy_end, finalised=finalised, reg_raw=reg_raw, log_raw=log_raw,
                    tl_rawtdl=raw_, tl_masters=mg_, saved_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                    params={"th_backdate": backdate, "th_big": big, "th_gap": gap, "th_generic": generic},
                    summary=res.summary, priority=res.priority.head(25) if res.priority is not None else None)
        return hist.save(meta, files, H.eng_to_json(E_h), snap)

    if has_data:
        s1, s2, s3 = st.columns([2, 2, 3])
        co_in = s1.text_input("Company for this check", co_h, key=f"h_co_{co_h or 'none'}", help='Saved with the check so that you can find it later and compare years.')
        by_in = s2.text_input("Prepared by", by_default, key="h_by", help='Your name or initials, shown on the saved check and exports.')
        note_in = s3.text_input("Notes (optional)", "", key="h_note", help='A short remark kept with the saved check.')
        if src.startswith("Sample"):
            st.warning("The Input tab is on sample (fictional) data. Switch to 'Pull from Tally' or 'Upload files' before saving a real check.")
        if st.button("💾 Save this check to history", type="primary", disabled=not co_in, help='Saves the data, test results, guided answers and reports of this check on this computer, so that it can be loaded again.'):
            try:
                cid_ = _save_current(co_in, by_in, note_in)
                st.success(f"Saved as check #{cid_} for {co_in}.")
            except Exception as e_:
                st.error(f"Could not save: {e_}")
    else:
        st.info("No company is open now. Select a saved check below to open its workspace, or load data on the Input tab.")
    st.divider()
    cos = hist.companies()
    fco = st.selectbox("Show company", ["All companies"] + cos, help='Filter the saved checks by company.')
    dfh = hist.list(None if fco == "All companies" else fco)
    if not len(dfh):
        st.info("Nothing saved yet. Run a check and press 'Save this check to history'.")
        return
    show = dfh.rename(columns={**H.LABEL, "exceptions_vs_previous": "Exceptions vs previous check"}).drop(columns=["Notes"])
    save_first = st.checkbox("Save the open company to history before switching", True, key="h_save_first",
                             help="Selecting a saved check opens it at once and closes the company that is open now. This keeps the open one as a new saved check first, so that you can come back to it from this list.")
    ev = st.dataframe(show, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row", key="hist_tbl")
    x1, x2 = st.columns(2)
    x1.download_button("Export register (Excel)", H.register_xlsx(dfh), "audit_trail_check_history.xlsx", H.XLSX, width="stretch", key="dl_hist_x")
    try:
        x2.download_button("Export register (PDF)", H.register_pdf(dfh), "audit_trail_check_history.pdf", "application/pdf", width="stretch", key="dl_hist_p")
    except ImportError:
        x2.info("PDF export needs reportlab: run INSTALL.bat again.")

    rows_ = list(ev.selection.rows) if ev is not None else []
    if not rows_:
        st.info("👆 Click a row to see that check's results here.")
        return
    row = dfh.iloc[rows_[0]]
    pick_id = int(row["id"])
    st.markdown(f"### {row['company']} · FY end {row['fy_end']} · check #{pick_id}")
    st.caption(f"Saved {row['saved_at']} · prepared by {row['prepared_by'] or '-'} · data source: {row['source']}"
               + (f" · notes: {row['notes']}" if row["notes"] else ""))
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Suggested conclusion", str(row["conclusion"]).title())
    m2.metric("Vouchers", f"{int(row['vouchers']):,}")
    m3.metric("Edit Log entries", f"{int(row['log_events']):,}")
    m4.metric("Exceptions", f"{int(row['exceptions']):,}", f"{int(row['high'])} high", delta_color="off")
    m5.metric("Tests with exceptions", f"{int(row['tests_failed'])} of {int(row['tests_total'])}")
    sn_ = hist.snapshot(pick_id)
    snap_ok = sn_ is not None
    if sn_ and sn_.get("summary") is not None:
        st.markdown("**Test results**")
        st.dataframe(sn_["summary"], hide_index=True, width="stretch")
        pr_ = sn_.get("priority")
        if pr_ is not None and len(pr_):
            with st.expander("Priority vouchers (top 25 by risk)"):
                st.dataframe(pr_, hide_index=True, width="stretch")
    fl_ = hist.files(pick_id)
    if not snap_ok:
        st.warning("This check was saved by an earlier version, which kept the reports but not the data, so it cannot be opened as a workspace. "
                   "Its results are shown below from the saved findings workbook. To make this company loadable: open it in the checker "
                   "(pull from Tally, or upload the files), then press **Save this check to history** once. Every check saved from now on can be loaded.")
        _fw = next((f for f in fl_ if f["name"].endswith("_findings.xlsx")), None)
        if _fw:
            try:
                _xs = pd.read_excel(io.BytesIO(_fw["data"]), sheet_name=None)
                if "Test summary" in _xs:
                    st.markdown("**Test results (from the saved findings workbook)**")
                    st.dataframe(_xs["Test summary"], hide_index=True, width="stretch")
                if "Priority vouchers" in _xs and len(_xs["Priority vouchers"]):
                    with st.expander("Priority vouchers (top 25 by risk)"):
                        st.dataframe(_xs["Priority vouchers"].head(25), hide_index=True, width="stretch")
            except Exception:
                pass
    if fl_:
        with st.expander(f"Reports saved with this check ({len(fl_)})"):
            for f_ in fl_:
                st.download_button(f"⬇ {f_['name']}", f_["data"], f_["name"], f_["mime"], key=f"hf_{f_['id']}")

    _hl = st.session_state.get("hist_loaded")
    if snap_ok and not (_hl and _hl["id"] == pick_id):
        # selecting a row opens that company's whole workspace here, closing the one that is open now
        cur_open = st.session_state.get("co_name") or (E_h.company if has_data else "")
        unchanged = bool(_hl) and H.eng_to_json(E_h) == hist.engagement(_hl["id"])
        if has_data and not src.startswith("Sample") and cur_open and save_first and not unchanged:
            try:
                _save_current(cur_open, st.session_state.get("h_by", ""), "saved automatically before switching company")
            except Exception as e_:
                st.error(f"The open company could not be saved, so nothing was switched: {e_}")
                return
        st.session_state["hist_pending"] = pick_id
        st.rerun()
    elif snap_ok:
        st.success(f"This company is open now. Use the other tabs to work on it, or press 'Reload' to discard changes and open the saved version again.")
        tally_alert(row["company"])
    b1, b2, b3 = st.columns([2, 2, 1])
    if b1.button("↻ Reload the saved version", width="stretch", key="h_reload", disabled=not snap_ok,
                 help="Discards the changes made since this check was loaded and opens the saved data and answers again."):
        st.session_state["hist_pending"] = pick_id
        st.rerun()
    if b2.button("Restore guided-audit answers only", width="stretch", key="h_restore",
                 help="Puts this check's guided answers into the Guided audit tab without changing the data that is open."):
        st.session_state["eng"] = H.eng_from_json(hist.engagement(pick_id), guided.Engagement)
        st.success("Restored. Open the Guided audit tab.")
    if b3.button("🗑 Delete", width="stretch", key="h_del", help="Deletes this saved check and its reports permanently."):
        st.session_state["h_confirm"] = pick_id
    if st.session_state.get("h_confirm") == pick_id:
        st.warning(f"Delete check #{pick_id} and its reports permanently?")
        if st.button("Yes, delete it", key="h_del_yes"):
            hist.delete(pick_id); st.session_state.pop("h_confirm", None); st.rerun()




def _need_data(why):
    for t_ in (tab_res, tab_guide, tab_rep):
        with t_:
            st.info(why)
    with tab_hist:
        st.info(why)
        render_history(False)
    st.stop()


if reg_raw is None or log_raw is None:
    _need_data("No data yet. Go to **2 · Input**: pull the vouchers and the Edit Log from Tally (or upload the files). "
               "The tests, guided audit, reports and history unlock as soon as both are loaded.")
try:
    res = run(reg_raw, log_raw, fy_start, fy_end, finalised, backdate, big, gap, generic)
except Exception as e:
    _need_data(f"Could not process the data: {e}")

ex, log = res.exceptions, res.log
colour, text = checks.indicator(res)

with st.sidebar:
    st.header("This engagement")
    st.write(f"**{t_comp or '(company not set)'}**")
    tally_alert(t_comp)
    st.write(f"Year {fy_start:%d-%b-%Y} to {fy_end:%d-%b-%Y}")
    st.write("Data: " + ("sample (fictional)" if SAMPLE else src.lower()))
    st.metric("Vouchers", f"{len(res.reg):,}")
    st.metric("Edit Log entries", f"{len(log):,}")
    st.metric("Exceptions", f"{len(ex):,}")
    {"Red": st.error, "Amber": st.warning, "Green": st.success}[colour](f"Indicator: **{colour}**")

# ================================================================== 3 · RESULTS
with tab_res:
    st.subheader("Findings from Edit Log Analysis")
    {"Red": st.error, "Amber": st.warning, "Green": st.success}[colour](f"**Indicator: {colour}.** {text}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Audit-trail events", f"{len(log):,}")
    c2.metric("Vouchers in register", f"{len(res.reg):,}")
    c3.metric("Exceptions", f"{len(ex):,}")
    c4.metric("High severity", int((ex.Severity == "High").sum()))
    c5.metric("Tests with exceptions", f"{int((res.summary.Exceptions > 0).sum())} of {len(res.summary)}")
    tab_over, tab_ex, tab_pri = st.tabs(["📊 Overview", "📋 Exceptions", "🎯 Priority vouchers"])

# ------------------------------------------------------------------ overview
with tab_over:
    st.subheader("What each test found")
    sm = res.summary.copy()
    st.dataframe(sm, hide_index=True, width="stretch")
    st.caption("A1–A2 completeness (did the trail capture everything?) · B timing (when were changes made?) · "
               "C substance (what was changed?) · D access (who and when?)")

    cr = log[(log.Action == "Created") & log.VoucherDate.notna()].copy()
    cr["lag"] = (cr.LogTime.dt.normalize() - cr.VoucherDate).dt.days
    late = cr.lag > backdate
    fig = go.Figure()
    for flag, name, colr, size in ((False, "Entered promptly", "#9db4c0", 6), (True, f"Entered > {backdate} days later", COLORS["High"], 11)):
        s = cr[late == flag]
        fig.add_trace(go.Scatter(x=s.VoucherDate, y=s.lag, mode="markers", name=name,
                                 marker=dict(size=size, color=colr, line=dict(width=1, color="white")),
                                 text=s.VoucherType + " " + s.VoucherNo + " · " + s.User,
                                 hovertemplate="%{text}<br>Voucher date %{x|%d-%b-%Y}<br>%{y} days later<extra></extra>"))
    fig.update_layout(title="When was each voucher actually entered? (days after its voucher date)", height=380,
                      margin=dict(l=0, r=0, t=50, b=0), yaxis_title="days", plot_bgcolor="white",
                      legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, width="stretch")

    m = log.assign(Month=log.LogTime.dt.to_period("M").dt.to_timestamp()).groupby(["Month", "Action"]).size().unstack(fill_value=0)
    fig2 = go.Figure()
    for act, colr in (("Created", "#9db4c0"), ("Altered", COLORS["Medium"]), ("Deleted", COLORS["High"])):
        if act in m:
            fig2.add_trace(go.Bar(x=m.index, y=m[act], name=act, marker_color=colr))
    fig2.add_shape(type="line", x0=pd.Timestamp(finalised), x1=pd.Timestamp(finalised), y0=0, y1=1, yref="paper",
                   line=dict(color="#1f2d3d", dash="dash"))
    fig2.add_annotation(x=pd.Timestamp(finalised), y=1, yref="paper", text="books finalised", showarrow=False,
                        xanchor="left", yanchor="top")
    fig2.update_layout(barmode="stack", title="Audit-trail activity by month", height=340,
                       margin=dict(l=0, r=0, t=50, b=0), plot_bgcolor="white", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig2, width="stretch")

    hh = log.assign(Hour=log.LogTime.dt.hour).groupby(["User", "Hour"]).size().unstack(fill_value=0)
    hh = hh.reindex(columns=range(24), fill_value=0)
    fig3 = go.Figure(go.Heatmap(z=hh.values, x=[f"{h:02d}" for h in hh.columns], y=hh.index, colorscale="Blues",
                                hovertemplate="%{y} at %{x}:00 · %{z} events<extra></extra>"))
    fig3.update_layout(title="Who changed the books, and at what hour?", height=300, margin=dict(l=0, r=0, t=50, b=0),
                       xaxis_title="hour of day")
    st.plotly_chart(fig3, width="stretch")
    st.subheader("Activity by user")
    st.dataframe(res.users.rename(columns={"Night_Sunday": "Night / Sunday", "After_year_end": "After year end"}),
                 hide_index=True, width="stretch")

# ------------------------------------------------------------------ exceptions
with tab_ex:
    f1, f2, f3 = st.columns([2, 2, 3])
    tsel = f1.multiselect("Test", list(checks.TESTS), default=list(checks.TESTS))
    ssel = f2.multiselect("Severity", ["High", "Medium", "Low"], default=["High", "Medium"])
    q = f3.text_input("Search voucher, user or text")
    v = ex[ex.Test.isin(tsel) & ex.Severity.isin(ssel)].copy()
    if q:
        blob = v.apply(lambda r: " ".join(map(str, r.values)).lower(), axis=1)
        v = v[blob.str.contains(q.lower(), regex=False)]
    show = v.copy()
    show["LogTime"] = show.LogTime.dt.strftime("%d-%b-%Y %H:%M").fillna("")
    show["Amount"] = show.Amount.map(lambda a: checks.inr(a) if pd.notna(a) and a else "")
    st.caption(f"{len(show)} of {len(ex)} exceptions")
    st.dataframe(show, hide_index=True, width="stretch", height=520)
    st.download_button("Download all findings (Excel)", checks.workbook(res), "audit_trail_findings.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_563")

# ------------------------------------------------------------------ priority
with tab_pri:
    st.write("Vouchers flagged by more than one test. Pick these first for vouching and enquiry.")
    pr = res.priority.head(25).copy()
    pr["Amount"] = pr.Amount.map(lambda a: checks.inr(a) if pd.notna(a) else "")
    st.dataframe(pr, hide_index=True, width="stretch")


# ================================================================== 5 · REPORTS
with tab_rep:
    tab_op, tab_memo, tab_dl = st.tabs(["✍️ Draft audit opinion", "📝 AI memo", "⬇ Downloads"])

with tab_dl:
    E_dl = st.session_state.setdefault("eng", guided.Engagement(fy_end=fy_end))
    E_dl.company = E_dl.company or t_comp
    concl_dl = guided.conclude(E_dl, res, None)
    st.write("Everything the engagement file needs, in one place. The guided answers (tab 4) feed the working paper and letter.")
    d1, d2 = st.columns(2)
    d1.download_button("Annexure A: voucher-level Edit Log (Excel)",
                       guided.annexure_xlsx(st.session_state.get("tl_rawtdl"), log, st.session_state.get("tl_masters"), res.reg,
                                            t_comp or E_dl.company, f"{fy_start} to {fy_end}"),
                       "voucher_editlog_annexure.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch", key="dl_584")
    d2.download_button("All test findings (Excel)", checks.workbook(res), "audit_trail_findings.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch", key="dl_588")
    d3, d4 = st.columns(2)
    d3.download_button("Working paper (Word)", guided.working_paper_docx(E_dl, concl_dl, res), "rule11g_working_paper.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document", width="stretch", key="dl_591")
    d4.download_button("Management representation letter (Word)", guided.rep_letter_docx(E_dl), "management_representation_audit_trail.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document", width="stretch", key="dl_593")
    st.caption("The draft opinion wording (Word) is on the 'Draft audit opinion' tab. Save the whole check, with these files, on the History tab.")

# ------------------------------------------------------------------ draft opinion
with tab_op:
    st.write("Answer the few questions only you can answer. The draft Rule 11(g) wording, basis-for-qualification text and "
             "management-letter points update from the findings. " + opinion.DISCLAIMER)
    reg11 = None
    st.caption("Evidence used: the tests on the data loaded on the Input tab.")
    o1, o2, o3 = st.columns(3)
    _co = st.session_state.get("co_name", "")
    comp = o1.text_input("Company", _co or "[Company name]", key=f"op_comp_{_co}")
    fye = o2.text_input("Year ended", f"{fy_end:%B %d, %Y}".replace(" 0", " "), key=f"op_fye_{fy_end}")
    soft = o3.text_input("Accounting software", "TallyPrime")
    q1, q2, q3, q4, q5 = st.columns(5)
    hf = q1.selectbox("Software has audit-trail feature?", ["Yes", "No"])
    dbl = q2.selectbox("Enabled at database level?", ["Yes", "No", "Not applicable"])
    sor = q3.selectbox("Third-party service-auditor report", ["Not applicable", "Obtained", "Not obtained"])
    mex = q4.selectbox("Management's explanations", ["Awaited", "Satisfactory", "Not satisfactory"], help='Whether management explained the flagged changes satisfactorily. It affects whether the tampering sentence can be concluded.')
    prs = q5.selectbox("Audit trail preserved?", ["Yes", "No", "Evidence awaited"])
    rp = st.checkbox("Include the preservation sentence (as applicable to this year)", True, help='From FY 2024-25 the report also says whether the audit trail was preserved as per statute. Untick for the first year of reporting (FY 2023-24).')
    notes = st.text_area("Your own notes to append (optional)", "", help='Anything you add here is appended to the draft wording.')
    dr = opinion.build(res, reg11, opinion.Inputs(comp, fye, soft, hf, dbl, sor, mex, prs, rp, notes))
    tone = {"unmodified": st.success, "modified": st.warning, "adverse": st.error, "pending": st.info}[dr.conclusion]
    tone(f"**Suggested: {dr.conclusion.upper()}.** " + " ".join(dr.why))
    for c_ in dr.caution:
        st.caption("⚠ " + c_)
    sug = dr.paras["_suggested"]
    for k_, v_ in dr.paras.items():
        if k_.startswith("_"):
            continue
        with st.expander(k_ + ("  ← suggested" if k_ == sug else ""), expanded=(k_ == sug)):
            st.text_area("Edit and copy", v_, height=200 if len(v_) < 900 else 360, key="op_" + k_)
    if dr.open_items:
        st.markdown("**Open items before you sign:**\n" + "\n".join("- " + o_ for o_ in dr.open_items))
    st.download_button("Download all as Word (.docx)", opinion.to_docx(dr, comp), "draft_rule11g_reporting.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_629")

# ------------------------------------------------------------------ memo
with tab_memo:
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    st.write("The AI turns the test results into observations, questions for management and draft Rule 11(g) wording. "
             + ("**Live AI is on** (API key found); only summary results and a few examples are sent."
                if has_key else "No API key found, so the offline template is used. Set `ANTHROPIC_API_KEY` for live AI."))
    if st.button("Generate memo and reporting paragraph", type="primary", help='Writes a short memo and a draft reporting paragraph from the test results. Review and edit before use.'):
        with st.spinner("Drafting…"):
            memo, mode = checks.memo_ai(res)
        st.session_state["am_memo"], st.session_state["am_mode"] = memo, mode
    if "am_memo" in st.session_state:
        st.caption(f"Source: {st.session_state['am_mode']}")
        st.text_area("Draft (edit before use)", st.session_state["am_memo"], height=560)
        st.download_button("Download (.txt)", st.session_state["am_memo"], "audit_trail_memo.txt", key="dl_645")
        st.warning("Draft for professional judgement. The final Rule 11(g) wording must follow the ICAI Implementation "
                   "Guide and your evidence on configuration, access, preservation and management's explanations.")


# ================================================================== 4 · GUIDED AUDIT (ICAI Implementation Guide)
with tab_guide:
    E_ = st.session_state.setdefault("eng", guided.Engagement(fy_end=fy_end))
    st.subheader("Guided Rule 11(g) audit-trail engagement")
    st.caption("Follows the ICAI Implementation Guide on Reporting on Audit Trail (Revised 2024) and the ICAI EKM material. "
               "It proposes; you decide. " + guided.DISCLAIMER)
    _gb1, _gb2 = st.columns([3, 1])
    _gb1.caption("💡 Suggested answers are marked 💡 and count only after you confirm them.")
    _gb_slot = _gb2
    stp = st.radio("Step", [f"{n} · {t}" for n, t, _, _ in guided.STEPS], horizontal=True, label_visibility="collapsed")
    n_ = stp.split(" · ")[0]
    meta = next(x for x in guided.STEPS if x[0] == n_)
    st.markdown(f"**{meta[1]}** — {meta[2]}  \n<small>ICAI: {meta[3]}</small>", unsafe_allow_html=True)

    CTX = W.Ctx(res=res, log=log, reg=res.reg, masters=st.session_state.get("tl_masters"), raw=st.session_state.get("tl_rawtdl"),
                fy_start=fy_start, fy_end=fy_end, company=st.session_state.get("co_name") or E_.company, source=src)
    SG = W.suggest(E_, CTX)
    for _f in ("confirmed", "wp_notes"):
        if not hasattr(E_, _f) or getattr(E_, _f) is None:
            setattr(E_, _f, {})
    def _flag_confirm():
        st.session_state["confirm_all_flag"] = True

    if st.session_state.pop("confirm_all_flag", False):      # one click confirms every suggestion on every step
        for _k, (_v, _w) in SG["app"].items():
            if not E_.confirmed.get(f"ap_{_k}"):
                setattr(E_, _k, _v)
            E_.confirmed[f"ap_{_k}"] = True
            st.session_state[f"gcf_ap_{_k}"] = True
        E_.confirmed["inventory"] = True
        st.session_state["gcf_inventory"] = True
        for _c in guided.CONTROLS:
            _cur = E_.controls.get(_c.id)
            if _cur is None or not _cur.get("confirmed", True):
                E_.controls[_c.id] = {"result": SG["controls"][_c.id][0], "note": SG["controls"][_c.id][1], "confirmed": True}
            st.session_state[f"gcf_{_c.id}"] = True

    def _confirm_btn(where, key, label="✔ Confirm all suggestions"):
        where.button(label, on_click=_flag_confirm, key=key, width="stretch",
                     help="Accepts every suggested answer on all steps (applicability, software inventory and the 12 controls). "
                          "Answers you have already changed stay as you set them. Review the working papers first.")

    _confirm_btn(_gb_slot, "cab_top", "✔ Confirm all (all steps)")
    import zlib

    def _crc(x) -> str:
        return format(zlib.crc32(repr(x).encode()) & 0xffff, "x")

    def _ck(ck, key, differs=False):
        """Confirm tick for a suggested answer. An answer the auditor changed is their own and counts as confirmed."""
        if key not in st.session_state:
            st.session_state[key] = bool(E_.confirmed.get(ck, False))
        if differs:
            st.session_state[key] = True
        v = st.checkbox("✔ Confirm this answer", key=key)
        E_.confirmed[ck] = bool(v)
        return bool(v)

    @st.dialog("Working paper", width="large")
    def _wp_dialog(cid):
        p = W.paper(cid, E_, CTX, SG["controls"].get(cid))
        st.markdown(f"### {p['title']}")
        st.table(pd.DataFrame(p["header"], columns=["", ""]).set_index(""))
        st.markdown("**Procedure**")
        for i_, t_ in enumerate(p["procedure"], 1):
            st.markdown(f"{i_}. {t_}")
        badge_ = f"**Result:** {p['result']} " + ("(confirmed)" if p["confirmed"] else "(suggested, not yet confirmed)")
        st.markdown(badge_)
        if p["suggested"]:
            st.caption(f"💡 Suggested: {p['suggested'][0]} — {p['suggested'][1]}")
        for name_, df_ in p["tables"]:
            st.markdown(f"**{name_}**")
            st.dataframe(df_, hide_index=True, width="stretch", height=min(320, 60 + 35 * len(df_)))
        E_.wp_notes[cid] = st.text_area("Auditor's conclusion on this working paper", E_.wp_notes.get(cid, ""), key=f"wpn_{cid}")
        p["conclusion"] = E_.wp_notes[cid]
        st.download_button("⬇ Download this working paper (Excel)", W.papers_xlsx([p]), f"working_paper_{cid}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"wpd_{cid}")

    if n_ == "1":
        _co = st.session_state.get("co_name", "")
        if _co and getattr(E_, "_co_src", None) != _co:      # a company pulled from Tally replaces the engagement's company name
            E_.company = _co
            E_._co_src = _co
        E_.company = st.text_input("Company", E_.company, key=f"g_comp_{_co or 'none'}", help='The company this engagement is for. It follows the company chosen in Settings.')
        E_.fy_end = st.date_input("Financial year ended", E_.fy_end, key="g_fyend", help='Year-end date used for applicability and the wording (for example 31 March 2026).')
        _c1_, _c2_ = st.columns([3, 1])
        _c1_.caption("💡 Answers are suggested from what the tool can see. Tick **Confirm** on each, or change it.")
        _confirm_btn(_c2_, "cab_1")
        for key, label, opts, why in guided.APPLICABILITY_QS:
            ck = f"ap_{key}"
            sv = SG["app"].get(key)
            cur = getattr(E_, key)
            if sv and not E_.confirmed.get(ck):
                cur = sv[0]
            val = st.radio(label, opts, opts.index(cur) if cur in opts else 0, help=why, key=f"gap_{key}_{_crc(sv)}")
            setattr(E_, key, val)
            st.caption(why)
            if sv:
                st.caption(f"💡 Suggested: **{sv[0]}** — {sv[1]}.")
                _ck(ck, f"gcf_{ck}", differs=val != sv[0])
        ap_ = guided.applicability(E_)
        if ap_["applies"]:
            st.success("Rule 11(g) applies. " + " ".join(ap_["reasons"]))
        else:
            st.warning("Not applicable: " + ap_["statement"])
    elif n_ == "2":
        for t_ in guided.INVENTORY_PROMPTS:
            st.caption("• " + t_)
        E_.software_main = st.text_input("Main accounting software (as it should appear in the report)", E_.software_main, help='The name of the software that holds the books, as it should read in the report.')
        inv = st.data_editor(pd.DataFrame(E_.inventory, columns=guided.INVENTORY_COLS), num_rows="dynamic", width="stretch", key="g_inv")
        E_.inventory = inv.fillna("").to_dict("records")
        st.caption("💡 Suggested: TallyPrime with the details above (pre-filled example). Correct the hosting, database and audit-trail columns to the facts.")
        _ck("inventory", "gcf_inventory")
        _confirm_btn(st, "cab_2")
        st.caption("Appendix I of the Implementation Guide: assess management's own identification of software and records (para 21).")
    elif n_ == "3":
        done_ = sum(1 for c__ in guided.CONTROLS if E_.controls.get(c__.id, {}).get("confirmed", False))
        h1, h2 = st.columns([3, 1])
        h1.caption(f"💡 Each answer below is a suggestion from your data (or a starting point where management's evidence is needed). "
                   f"Open the working paper, then tick **Confirm**. Only confirmed answers count in the conclusion. Confirmed: {done_} of {len(guided.CONTROLS)}.")
        _confirm_btn(h2, "cab_3")
        for c_ in guided.CONTROLS:
            sg_ = SG["controls"][c_.id]
            cur = E_.controls.get(c_.id)
            confirmed_ = bool(cur and cur.get("confirmed", True)) if cur else False
            if cur is None or cur.get("confirmed") is False:
                cur = {"result": sg_[0], "note": sg_[1], "confirmed": False}
            tag_ = "✔ confirmed" if confirmed_ else "💡 suggested"
            sk = _crc(sg_)
            with st.expander(f"{c_.id} · {c_.area} — {cur['result']}  ·  {tag_}", expanded=not confirmed_ and c_.critical):
                st.write(c_.test)
                st.caption(f"ICAI: {c_.ref}  \nTally: {c_.how}")
                st.caption(("💡 Suggested from your data: " if sg_[2] == "data" else "💡 Starting point — needs management's evidence: ")
                           + f"**{sg_[0]}**. {sg_[1]}")
                a_, b_ = st.columns([1, 3])
                r_ = a_.selectbox("Result", guided.RESULTS, guided.RESULTS.index(cur["result"]), key=f"gr_{c_.id}_{sk}")
                nt_ = b_.text_input("Evidence / note", cur["note"], key=f"gn_{c_.id}_{sk}")
                w1, w2 = st.columns([1, 1])
                if w1.button("📄 Open working paper", key=f"gwp_{c_.id}", width="stretch"):
                    st.session_state["wp_open"] = c_.id
                with w2:
                    conf_ = _ck(c_.id, f"gcf_{c_.id}", differs=(r_ != sg_[0] or nt_ != sg_[1]))
                E_.controls[c_.id] = {"result": r_, "note": nt_, "confirmed": conf_}
        if st.session_state.get("wp_open"):
            _w = st.session_state.pop("wp_open")
            _wp_dialog(_w)
        E_.third_party_unable = st.checkbox("Software is run by a third party and no service-auditor report covering the whole year is available",
                                            E_.third_party_unable, help='Tick if a vendor hosts or operates the software and you have no service-auditor report covering the whole year. The wording becomes an inability to comment.')
        E_.migration = st.checkbox("Software was migrated/upgraded during the year and audit-trail controls are not yet established", E_.migration, help='Tick if the software changed during or after the year and audit-trail controls are not yet set up (para 31, scenario 5).')
        st.dataframe(guided.control_summary(E_)[["Ref", "Area", "Result", "Status", "Note"]], hide_index=True, width="stretch")
    elif n_ == "4":
        st.markdown("**Data source for this step:** the Overview/Exceptions tabs use the data chosen in the sidebar. "
                    "For a real Tally company: 📥 2 · Input → Pull from Tally.")
        cA, cB = st.columns(2)
        cA.metric("Voucher log entries tested", f"{len(log):,}")
        cB.metric("Exceptions", f"{len(ex):,}")
        st.dataframe(res.summary, hide_index=True, width="stretch")
        mg = st.session_state.get("tl_masters")
        if mg is not None and len(mg):
            st.markdown("**Master-data and company-level changes** (ICAI FAQ 25: part of the books of account)")
            st.dataframe(mg.groupby(["Object", "User"]).size().rename("Changes").reset_index(), hide_index=True)
            with st.expander("Detail"):
                st.dataframe(mg, hide_index=True, width="stretch", height=300)
            ca_ = mg[mg.Object == "Company"]
            if len(ca_):
                st.caption("Company activity can show who switched features or took backups; read it for any change to the Edit Log setting (C2/C3).")
        else:
            st.info("No master/company log loaded. The TDL export includes ledgers, groups, stock items and company activity.")
        st.caption("FAQ 17: only the latest change is not enough. The TDL exports every version, so a voucher altered three times shows three rows.")
        st.download_button("Annexure A: voucher-level Edit Log (Excel: every version, field changes, deleted vouchers)",
                           guided.annexure_xlsx(st.session_state.get("tl_rawtdl"), log, mg, res.reg, E_.company, f"{fy_start} to {fy_end}"),
                           "voucher_editlog_annexure.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_791")
        E_.mgmt_explanation = st.selectbox("Management's explanation of flagged changes",
                                           ["Awaited", "Satisfactory", "Not satisfactory"],
                                           ["Awaited", "Satisfactory", "Not satisfactory"].index(E_.mgmt_explanation), help='Whether management explained the flagged changes satisfactorily. It affects whether the tampering sentence can be concluded.')
    elif n_ == "5":
        for key, q, ref in guided.PRESERVATION_QS:
            opts = ["Not yet evidenced", "Yes", "No"]
            cur = E_.preservation.get(key, "Not yet evidenced")
            E_.preservation[key] = st.radio(q, opts, opts.index(cur), horizontal=True, help=ref, key=f"gp_{key}")
            st.caption(ref)
    elif n_ == "6":
        for key, q in guided.REP_ITEMS:
            E_.reps[key] = st.checkbox(q, E_.reps.get(key, False), key=f"grp_{key}")
        st.caption("SA 580: refusal or inability to obtain representations is a limitation on scope (para 34).")
        st.download_button("Download the representation letter (Word, Appendix II)", guided.rep_letter_docx(E_),
                           "management_representation_audit_trail.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_808")
    elif n_ == "7":
        concl = guided.conclude(E_, res, None)
        st.session_state["g_concl"] = concl
        badge = {"unmodified": st.success, "pending": st.info, "modified": st.warning, "adverse": st.error,
                 "inability to conclude": st.warning, "not applicable": st.info}[concl["conclusion"]]
        badge(f"Suggested conclusion: **{concl['conclusion'].upper()}**")
        st.dataframe(guided.readiness(E_, res), hide_index=True, width="stretch")
        for x in concl["exceptions"]:
            st.write(f"• **{x['severity']}** ({x['evidence']}): {x['clause']}")
        for c_ in concl["caution"]:
            st.caption("⚠ " + c_)
        E_.notes = st.text_area("Your own notes / reasons for the conclusion", E_.notes, help='Your own reasoning for the conclusion. It goes into the working paper.')
    elif n_ == "8":
        concl = st.session_state.get("g_concl") or guided.conclude(E_, res, None)
        st.info(f"Suggested conclusion: {concl['conclusion'].upper()}. Edit the wording before use; clause numbers are placeholders.")
        for k_, v_ in concl["paras"].items():
            if k_.startswith("_"):
                continue
            st.markdown(f"**{k_}**" + ("  ← suggested" if k_ == concl["paras"].get("_suggested") else ""))
            st.text_area(k_, v_, height=140, key=f"gw_{k_}", label_visibility="collapsed")
        st.download_button("Annexure A: voucher-level Edit Log (Excel)",
                           guided.annexure_xlsx(st.session_state.get("tl_rawtdl"), log, st.session_state.get("tl_masters"), res.reg,
                                                E_.company, f"{fy_start} to {fy_end}"),
                           "voucher_editlog_annexure.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_831")
        _allp = [W.paper(c__.id, E_, CTX, SG["controls"].get(c__.id)) for c__ in guided.CONTROLS]
        st.download_button("All control working papers (Excel, one sheet per control)", W.papers_xlsx(_allp), "rule11g_control_working_papers.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_836")
        d1, d2 = st.columns(2)
        d1.download_button("Working paper (Word)", guided.working_paper_docx(E_, concl, res), "rule11g_working_paper.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", width="stretch", key="dl_839")
        d2.download_button("Representation letter (Word)", guided.rep_letter_docx(E_), "management_representation_audit_trail.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", width="stretch", key="dl_841")



with tab_hist:
    render_history(True)
