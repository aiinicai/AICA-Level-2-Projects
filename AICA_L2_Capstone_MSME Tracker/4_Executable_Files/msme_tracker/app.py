"""MSME Payables Compliance Tracker (Section 43B(h) + MSME Form 1) – Streamlit app.

Run:  streamlit run app.py
"""
from __future__ import annotations

import altair as alt
from datetime import date

import pandas as pd
import streamlit as st

import engine as E
import import_ui
import interest as X
import store
import templates as T

st.set_page_config(page_title="MSME Payables Compliance Tracker", page_icon="📒", layout="wide")

DATE_COLS = ["Bill Date", "Accepted On", "Due Date", "Last Payment Date", "Date From Which Due", "Month End"]


def show(df: pd.DataFrame, height: int | str = "auto"):
    d = df.drop(columns=[c for c in ("vkey", "bkey") if c in df.columns]).copy()
    for c in d.columns:                       # every date column -> dd-mm-yyyy
        if pd.api.types.is_datetime64_any_dtype(d[c]):
            d[c] = d[c].dt.strftime("%d-%m-%Y")
    fm = {c: E.fmt_inr for c in d.columns if E.is_amount_col(c, d[c])}      # Indian digit grouping
    st.dataframe(d.style.format(fm, na_rep=""), width="stretch", hide_index=True, height=height)


def inr(x: float) -> str:
    return "₹" + E.fmt_inr(x, 0)


# chart axis labels with Indian digit grouping (vega expression: 1500000 -> 15,00,000)
AX_INR = alt.Axis(title="₹", labelExpr=r"replace(format(datum.value, 'd'), regexp('(\\d)(?=(\\d\\d)+\\d$)', 'g'), '$1,')")


def dl(label: str, data: bytes, name: str, mime: str, key: str):
    st.download_button(label, data, file_name=name, mime=mime, key=key)


# --------------------------------------------------------------------------- #
# Sidebar: company selection
# --------------------------------------------------------------------------- #
st.sidebar.title("📒 MSME Tracker")
companies = store.list_companies()
labels = {c["slug"]: c["name"] for c in companies}

with st.sidebar:
    st.subheader("Company")
    slug = None
    if companies:
        slug = st.selectbox("Select company", options=list(labels), format_func=labels.get, key="company")
    else:
        st.info("No companies yet. Add one below to begin.")
    with st.expander("➕ Add company", expanded=not companies):
        with st.form("add_company", clear_on_submit=True):
            n = st.text_input("Company name *")
            c1, c2 = st.columns(2)
            pan = c1.text_input("PAN")
            gstin = c2.text_input("GSTIN")
            ok = st.form_submit_button("Create")
        if ok:
            try:
                new = store.create_company(n, pan, gstin)
                st.session_state["company"] = new
                st.rerun()
            except ValueError as e:
                st.error(str(e))
    if slug:
        with st.expander("⚙️ Manage company"):
            prof = store.get_profile(slug)
            st.caption(f"PAN: {prof.get('pan') or '–'} · GSTIN: {prof.get('gstin') or '–'}")
            confirm = st.checkbox("I want to delete this company and its vendor master", key=f"del_{slug}")
            if st.button("Delete company", disabled=not confirm):
                store.delete_company(slug)
                st.session_state.pop("company", None)
                st.session_state.pop("result", None)
                st.rerun()
    st.divider()
    st.caption("Templates")
    for kind, nm in E.SHEET_NAMES.items():
        fmt = st.radio(f"{nm} format", ["xlsx", "csv"], horizontal=True, key=f"fmt_{kind}", label_visibility="collapsed")
        data, fname, mime = T.single_template(kind, fmt)
        dl(f"⬇ {nm} template (.{fmt})", data, fname, mime, f"tpl_{kind}")
    data, fname, mime = T.combined_template()
    dl("⬇ All-in-one workbook (.xlsx)", data, fname, mime, "tpl_all")

if not slug:
    st.title("MSME Payables Compliance Tracker")
    st.write("Section 43B(h) exposure and MSME Form 1 for any company. Add a company in the sidebar to begin.")
    st.stop()

prof = store.get_profile(slug)
st.title(f"MSME Payables Compliance Tracker — {prof['name']}")

# Reset results when switching company
if st.session_state.get("result_company") != slug:
    st.session_state.pop("result", None)
    st.session_state["result_company"] = slug

master = store.load_master(slug)

tab_master, tab_run, tab_dash, tab_43, tab_f1, tab_int, tab_help = st.tabs(
    ["1 · Vendor Master", "2 · Upload & Run", "3 · Dashboard", "4 · Section 43B(h)", "5 · MSME Form 1", "6 · MSME Interest", "Help"])

# --------------------------------------------------------------------------- #
# 1. Vendor master
# --------------------------------------------------------------------------- #
with tab_master:
    st.subheader(f"Vendor master — {prof['name']}")
    st.caption("Stored per company. Upload once, then update only when vendors change. Bills and payments uploads are matched to this list by Vendor Name.")
    up = st.file_uploader("Upload vendor master (.xlsx / .xls / .csv)", type=["xlsx", "xls", "csv"], key=f"vm_up_{slug}")
    mode = st.radio("When uploading", ["Merge (add new, update existing)", "Replace entire master"], horizontal=True)
    if up is not None and st.button("Apply upload", type="primary"):
        try:
            raw = E.read_table(up.getvalue(), up.name, "vendor_master")
            clean, issues = E.standardise(raw, "vendor_master")
            if mode.startswith("Replace"):
                store.save_master(slug, clean)
                st.success(f"Master replaced with {len(clean)} vendors.")
            else:
                merged, a, u = store.merge_master(master, clean)
                store.save_master(slug, merged)
                st.success(f"{a} vendor(s) added, {u} updated.")
            for i in issues:
                st.warning(i)
            master = store.load_master(slug)
        except Exception as e:  # noqa: BLE001
            st.error(str(e))

    st.markdown("**Edit directly** (add rows with the + at the bottom of the table, then Save)")
    editable = master[[c.name for c in E.SCHEMAS["vendor_master"]]].copy()
    editable["Udyam Registration Date"] = pd.to_datetime(editable["Udyam Registration Date"], errors="coerce")
    editable["Agreed Credit Days"] = pd.to_numeric(editable["Agreed Credit Days"], errors="coerce")
    edited = st.data_editor(
        editable, num_rows="dynamic", width="stretch", key=f"vm_edit_{slug}",
        column_config={
            "MSME Category": st.column_config.SelectboxColumn(options=E.CATEGORIES, required=True),
            "Udyam Registration Date": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "Agreed Credit Days": st.column_config.NumberColumn(min_value=0, max_value=365, step=1),
        })
    c1, c2 = st.columns([1, 3])
    if c1.button("💾 Save changes"):
        clean, issues = E.standardise(edited.copy(), "vendor_master") if len(edited.dropna(how="all")) else (edited, [])
        store.save_master(slug, clean)
        st.success(f"Saved {len(clean)} vendors.")
        for i in issues:
            st.warning(i)
        st.rerun()
    if len(master):
        cc = master["MSME Category"].value_counts()
        c2.caption("Vendors: " + " · ".join(f"{k}: {v}" for k, v in cc.items()))
        dl("⬇ Export vendor master", E.export_workbook({"Vendor Master": master}), f"{slug}_vendor_master.xlsx",
           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "vm_export")

# --------------------------------------------------------------------------- #
# 2. Upload & run
# --------------------------------------------------------------------------- #
with tab_run:
    saved = store.list_runs(slug)
    if saved:
        with st.expander(f"📂 Saved runs ({len(saved)}) – reopen a previous run", expanded=False):
            labels = {m["id"]: f'{m["name"]} · as at {pd.Timestamp(m["as_of"]):%d-%m-%Y} · saved {m["created"][:16].replace("T", " ")}' for m in saved}
            rid = st.selectbox("Saved run", list(labels), format_func=labels.get, key=f"sr_{slug}")
            use_cur = st.checkbox("Recalculate with the current vendor master (instead of the master saved with the run)", key=f"sr_cur_{slug}")
            b1, b2, b3 = st.columns([1, 1, 3])
            if b1.button("Open run", type="primary"):
                try:
                    run = store.load_run(slug, rid)
                    m_used = master if use_cur else run["master"]
                    st.session_state["result"] = {
                        "bills": run["bills"], "pays": run["pays"], "res": E.build_ledger(run["bills"], run["pays"], m_used, run["as_of"]),
                        "as_of": run["as_of"], "fy": run["fy"], "warnings": list(run["meta"].get("warnings", [])), "master": m_used,
                        "run_id": rid, "run_name": run["meta"]["name"], "reasons": run["reasons"]}
                    st.session_state["load_counter"] = st.session_state.get("load_counter", 0) + 1
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f"Could not open this run: {e}")
            sure = b3.checkbox("Confirm delete", key=f"sr_del_{slug}")
            if b2.button("Delete", disabled=not sure):
                store.delete_run(slug, rid)
                if st.session_state.get("result", {}).get("run_id") == rid:
                    st.session_state["result"]["run_id"] = None
                st.rerun()
    st.subheader("Load transactions")
    if master.empty:
        st.warning("The vendor master for this company is empty. Add vendors in tab 1 first – only Micro/Small vendors are covered by 43B(h).")
    src = st.radio("Source", ["Standard templates", "Vendor statements / software exports (auto-detect)"], horizontal=True, key=f"src_{slug}")
    bills_up = pay_up = None
    if src == "Standard templates":
        c1, c2 = st.columns(2)
        bills_up = c1.file_uploader("Bills (.xlsx / .xls / .csv)", type=["xlsx", "xls", "csv"], key=f"bills_{slug}")
        pay_up = c2.file_uploader("Payments (optional)", type=["xlsx", "xls", "csv"], key=f"pay_{slug}")
    else:
        import_ui.render(slug, master)
    staged = import_ui.staged_totals(slug)
    if staged:
        sc1, sc2 = st.columns([4, 1])
        sc1.info(f"Imported and staged for this run: {len(staged[0])} bill row(s), {len(staged[1])} payment row(s) from {staged[2]} file(s). "
                 "They are combined with any template files uploaded.")
        if sc2.button("Clear imported"):
            st.session_state["staged"][slug] = {}
            st.rerun()
    d1, d2 = st.columns(2)
    default_asof = E.half_year_end(pd.Timestamp.today())
    as_of = d1.date_input("Report as-of date", value=default_asof, format="DD/MM/YYYY",
                          help="Position as at this date. Defaults to the latest half-year end (30 Sep / 31 Mar).")
    fy_default = E.fy_start_year_of(as_of)
    fy = d2.number_input("Financial year starting (for 43B(h))", min_value=2023, max_value=2100, value=fy_default, step=1,
                         help="FY 2025 means 1-Apr-2025 to 31-Mar-2026. 43B(h) applies from FY 2023-24.")
    # ---- Opening balances (optional): dues already unpaid at the start of the period ----
    ob_df = pd.DataFrame()
    ob_mode = "bill"
    ob_date = pd.Timestamp(date(int(fy), 4, 1)) - pd.Timedelta(days=1)
    with st.expander("📘 Opening balances – dues unpaid at the start of the period (optional)"):
        st.caption("Use this when your bills file only covers the current period but some earlier bills were still unpaid. "
                   "Payments in your payments file reduce these balances like any other bill.")
        o1, o2 = st.columns([2, 1])
        ob_label = o1.radio("Enter opening balances", ["Bill-wise (recommended)", "Party-wise (one total per vendor)"], horizontal=True, key=f"obm_{slug}",
                            help="Bill-wise keeps each bill's real date, so due dates, 43B(h) and interest are exact. Party-wise only has a total, so it is dated from the opening date.")
        ob_mode = "bill" if ob_label.startswith("Bill") else "party"
        ob_date = pd.Timestamp(o2.date_input("Opening balance as at", value=ob_date.date(), format="DD/MM/YYYY", key=f"obd_{slug}",
                                             help="Default: the day before the financial year starts. Payments dated on or before this are already reflected in the balance."))
        otpl, _ = st.columns([1, 3])
        d_, f_, m_ = T.single_template("opening", "xlsx")
        dl("⬇ Opening balance template (.xlsx)", d_, f_, m_, "tpl_opening_inline")
        ob_up = st.file_uploader("Upload opening balances (.xlsx / .xls / .csv)", type=["xlsx", "xls", "csv"], key=f"obup_{slug}")
        st.markdown("…or type them in (add rows with the + at the bottom):")
        vnames = sorted(master["Vendor Name"].dropna().astype(str).unique()) if len(master) else []
        if ob_mode == "bill":
            seed = pd.DataFrame({"Vendor Name": pd.Series(dtype=object), "Bill No": pd.Series(dtype=object), "Bill Date": pd.Series(dtype="datetime64[ns]"),
                                 "Outstanding Amount": pd.Series(dtype=float), "Acceptance Date": pd.Series(dtype="datetime64[ns]"), "Branch": pd.Series(dtype=object)})
        else:
            seed = pd.DataFrame({"Vendor Name": pd.Series(dtype=object), "Outstanding Amount": pd.Series(dtype=float),
                                 "Bill Date": pd.Series(dtype="datetime64[ns]"), "Branch": pd.Series(dtype=object)})
        cfg = {"Vendor Name": st.column_config.SelectboxColumn(options=vnames, required=True),
               "Outstanding Amount": st.column_config.NumberColumn(min_value=0.0, format="%.2f", required=True),
               "Bill Date": st.column_config.DateColumn(format="DD-MM-YYYY", help="Party-wise: optional – blank = opening date."),
               "Acceptance Date": st.column_config.DateColumn(format="DD-MM-YYYY")}
        typed = st.data_editor(seed, num_rows="dynamic", width="stretch", column_config=cfg, key=f"obed_{slug}_{ob_mode}")
        parts = []
        try:
            if ob_up is not None:
                parts.append(E.standardise(E.read_table(ob_up.getvalue(), ob_up.name, "opening"), "opening"))
            if len(typed.dropna(how="all")):
                parts.append(E.standardise(typed.copy(), "opening"))
        except ValueError as e:
            st.error(str(e))
        ob_issues = [i for _, w in parts for i in w]
        if parts:
            ob_df = pd.concat([p_ for p_, _ in parts], ignore_index=True)
            st.success(f"{len(ob_df)} opening row(s), total {inr(ob_df['Outstanding Amount'].sum())}, as at {ob_date:%d-%m-%Y}.")
            for i in ob_issues:
                st.warning(i)
    has_bills = bills_up is not None or bool(staged and len(staged[0])) or len(ob_df) > 0
    if st.button("▶ Run tracker", type="primary", disabled=not has_bills or master.empty):
        try:
            warnings: list[str] = []
            bparts, pparts = [], []
            if bills_up is not None:
                braw = E.read_table(bills_up.getvalue(), bills_up.name, "bills")
                bclean, w = E.standardise(braw, "bills"); warnings += [f"Bills: {x}" for x in w]
                bparts.append(bclean)
            if pay_up is not None:
                praw = E.read_table(pay_up.getvalue(), pay_up.name, "payments")
                pclean, w = E.standardise(praw, "payments"); warnings += [f"Payments: {x}" for x in w]
                pparts.append(pclean)
            if staged:
                if len(staged[0]):
                    bclean, w = E.standardise(staged[0], "bills"); warnings += [f"Imported bills: {x}" for x in w]
                    bparts.append(bclean)
                if len(staged[1]):
                    pclean, w = E.standardise(staged[1], "payments"); warnings += [f"Imported payments: {x}" for x in w]
                    pparts.append(pclean)
            if len(ob_df):
                ob_bills, w = E.opening_to_bills(ob_df, ob_mode, ob_date)
                warnings += [f"Opening balances: {x}" for x in w]
                oclean, w = E.standardise(ob_bills, "bills"); warnings += [f"Opening balances: {x}" for x in w]
                bparts.append(oclean)
            if not bparts:
                raise ValueError("Upload a bills file or enter opening balances first.")
            bills = pd.concat(bparts, ignore_index=True)
            n0 = len(bills)
            bills = bills.drop_duplicates(["vkey", "bkey", "Bill Date", "Bill Amount"]).reset_index(drop=True)
            if len(bills) < n0:
                warnings.append(f"{n0 - len(bills)} duplicate bill row(s) (same vendor, bill no, date and amount) were counted once.")
            if pparts:
                pays = pd.concat(pparts, ignore_index=True)
                n0 = len(pays)
                pays = pays.drop_duplicates(["vkey", "Payment Date", "Amount Paid", "bkey"]).reset_index(drop=True)
                if len(pays) < n0:
                    warnings.append(f"{n0 - len(pays)} duplicate payment row(s) were counted once.")
            else:
                pays = pd.DataFrame(columns=["vkey", "bkey", "Payment Date", "Amount Paid", "Reference", "Payment Mode", "Vendor Name", "Bill No"])
            if len(ob_df) and len(pays):
                early = pays["Payment Date"] <= ob_date
                if early.any():
                    warnings.append(f"{int(early.sum())} payment(s) are dated on or before the opening date ({ob_date:%d-%m-%Y}); they are already "
                                    "reflected in the opening balance, so remove them from the payments file to avoid counting them twice.")
            res = E.build_ledger(bills, pays, master, as_of)
            st.session_state["result"] = {"bills": bills, "pays": pays, "res": res, "as_of": pd.Timestamp(as_of),
                                          "fy": int(fy), "warnings": warnings, "master": master, "run_id": None, "run_name": None,
                                          "reasons": {}}
            st.session_state["load_counter"] = st.session_state.get("load_counter", 0) + 1
            st.success(f"Processed {len(res.ledger)} bills as at {pd.Timestamp(as_of):%d-%m-%Y}. Open the Dashboard, 43B(h), Form 1 and Interest tabs.")
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
    r = st.session_state.get("result")
    if r:
        for w in r["warnings"]:
            st.warning(w)
        res = r["res"]
        if res.unknown_vendors:
            st.error(f"{len(res.unknown_vendors)} vendor(s) in the bills are not in the vendor master and are treated as 'Unclassified' (not covered). "
                     "Add them in tab 1 and run again: " + ", ".join(res.unknown_vendors[:15]) + ("…" if len(res.unknown_vendors) > 15 else ""))
            miss = pd.DataFrame({"Vendor Name": res.unknown_vendors, "MSME Category": "", "PAN": "", "Udyam Number": ""})
            if st.button("➕ Add these vendors to master as 'Not MSME' (edit category after)"):
                add = pd.DataFrame({"Vendor Name": res.unknown_vendors, "MSME Category": "Not MSME"})
                add["vkey"] = add["Vendor Name"].map(E.vendor_key)
                for c in [c.name for c in E.SCHEMAS["vendor_master"]]:
                    if c not in add.columns:
                        add[c] = None
                merged, a, _ = store.merge_master(master, add)
                store.save_master(slug, merged)
                st.success(f"Added {a} vendors. Set their MSME Category in tab 1, then run again.")
        if len(res.unmatched_payments):
            st.warning(f"{len(res.unmatched_payments)} payment(s) refer to a Bill No that is not in the bills file:")
            show(res.unmatched_payments[["Vendor Name", "Bill No", "Payment Date", "Amount Paid"]])
        if len(res.unapplied_payments):
            st.info(f"{len(res.unapplied_payments)} payment(s) could not be fully applied (advances / excess payments), total "
                    f"{inr(res.unapplied_payments['Amount Paid'].sum())}.")
            show(res.unapplied_payments[["Vendor Name", "Bill No", "Payment Date", "Amount Paid"]])
        with st.container(border=True):
            st.markdown("**Save this run**")
            if r.get("run_id"):
                st.caption(f'Saved as "{r["run_name"]}". Form 1 reasons can be saved to it from tab 5.')
            sname = st.text_input("Name", value=r.get("run_name") or f"Position at {r['as_of']:%d-%m-%Y}", key=f"sname_{slug}_{st.session_state.get('load_counter', 0)}")
            if st.button("💾 Save as new run" if r.get("run_id") else "💾 Save run"):
                r["run_id"] = store.save_run(slug, sname, r["bills"], r["pays"], r["master"], r["as_of"], r["fy"], r["warnings"])
                r["run_name"] = sname.strip() or r["run_id"]
                st.success(f'Saved "{r["run_name"]}". Reopen it any time from "Saved runs" above.')

r = st.session_state.get("result")
if not r:
    for t in (tab_dash, tab_43, tab_f1, tab_int):
        with t:
            st.info("Upload files and click **Run tracker** in tab 2.")
else:
    L = r["res"].ledger
    as_of = r["as_of"]
    cov = L[L["Covered"]]

    # ---------------- Dashboard ---------------- #
    with tab_dash:
        st.caption(f"Position as at {as_of:%d-%m-%Y} · covered = Micro/Small vendors")
        open_cov = cov[cov["Outstanding"] > 0.005]
        over = open_cov[open_cov["Days Overdue"] > 0]
        k = st.columns(4)
        k[0].metric("Outstanding to Micro/Small", inr(open_cov["Outstanding"].sum()))
        k[1].metric("Of which overdue", inr(over["Outstanding"].sum()))
        k[2].metric("Vendors overdue", over["vkey"].nunique())
        k[3].metric("Bills paid late (period)", int((cov["Paid Late"] > 0.005).sum()))

        a, b = st.columns(2)
        with a:
            st.markdown("**Overdue by ageing bucket**")
            ag = (open_cov.groupby("Age Bucket")["Outstanding"].sum().reindex(E.AGE_BUCKETS).fillna(0).reset_index())
            ag["Amt"] = ag["Outstanding"].map(lambda v: E.fmt_inr(v))
            st.altair_chart(alt.Chart(ag).mark_bar().encode(
                x=alt.X("Age Bucket:N", sort=E.AGE_BUCKETS, title=None), y=alt.Y("Outstanding:Q", axis=AX_INR),
                tooltip=["Age Bucket", alt.Tooltip("Amt:N", title="Outstanding ₹")]), width="stretch")
        with b:
            st.markdown("**Top 10 vendors by overdue amount**")
            tv = over.groupby("Vendor Name")["Outstanding"].sum().sort_values(ascending=False).head(10).reset_index()
            if len(tv):
                tv["Amt"] = tv["Outstanding"].map(lambda v: E.fmt_inr(v))
                st.altair_chart(alt.Chart(tv).mark_bar().encode(
                    y=alt.Y("Vendor Name:N", sort="-x", title=None), x=alt.X("Outstanding:Q", axis=AX_INR),
                    tooltip=["Vendor Name", alt.Tooltip("Amt:N", title="Overdue ₹")]), width="stretch")
            else:
                st.success("Nothing overdue.")

        if L["Branch"].notna().any():
            st.markdown("**Overdue by branch**")
            bb = over.assign(Branch=over["Branch"].fillna("(none)")).groupby("Branch")["Outstanding"].sum().reset_index()
            if len(bb):
                bb["Amt"] = bb["Outstanding"].map(lambda v: E.fmt_inr(v))
                st.altair_chart(alt.Chart(bb).mark_bar().encode(x=alt.X("Branch:N", title=None), y=alt.Y("Outstanding:Q", axis=AX_INR),
                                                                tooltip=["Branch", alt.Tooltip("Amt:N", title="Overdue ₹")]),
                                width="stretch")

        st.markdown("**Month-end trend (last 12 months)**")
        tr = E.month_end_trend(r["bills"], r["pays"], r["master"], as_of)
        tl = tr.melt("Month End", var_name="Measure", value_name="₹")
        tl["Amt"] = tl["₹"].map(lambda v: E.fmt_inr(v))
        st.altair_chart(alt.Chart(tl).mark_line(point=True).encode(
            x=alt.X("Month End:T", title=None), y=alt.Y("₹:Q", axis=AX_INR), color="Measure:N",
            tooltip=["Month End:T", "Measure", alt.Tooltip("Amt:N", title="₹")]), width="stretch")

        st.markdown("**Pay-by list**")
        h = st.slider("Show covered bills due within next N days (plus all overdue)", 0, 45, 15)
        pb = E.pay_by_list(L, as_of, h)
        show(pb, height=300)
        st.markdown("**All bills**")
        show(L, height=350)
        dl("⬇ Download ledger (.xlsx)", E.export_workbook({"Ledger": L, "Pay-by list": pb}), f"{slug}_ledger_{as_of:%Y%m%d}.xlsx",
           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "dl_ledger")

    # ---------------- 43B(h) ---------------- #
    with tab_43:
        d = E.disallowance_43bh(r["bills"], r["pays"], r["master"], r["fy"])
        st.caption(f"FY {d['fy_start']:%d-%m-%Y} to {d['fy_end']:%d-%m-%Y}")
        k = st.columns(3)
        k[0].metric("Disallowance (unpaid beyond due date at year end)", inr(d["disallowed"]["Outstanding"].sum()))
        k[1].metric("Not yet due at year end (pay in time)", inr(d["not_yet_due"]["Outstanding"].sum()))
        k[2].metric("Prior-year disallowance paid this FY (deductible now)", inr(d["reversal"]["Paid In FY"].sum()) if len(d["reversal"]) else "₹0")
        st.markdown("**Disallowed in this FY**")
        show(d["disallowed"][["Vendor Name", "Bill No", "Accepted On", "Due Date", "Days Overdue", "Outstanding", "Branch"]])
        st.markdown("**Prior-year disallowance paid during this FY**")
        if len(d["reversal"]):
            show(d["reversal"][["Vendor Name", "Bill No", "Accepted On", "Due Date", "Paid In FY"]])
        else:
            st.caption("None.")
        sheets = {"Disallowed": d["disallowed"], "Not yet due": d["not_yet_due"], "Prior-yr reversal": d["reversal"], "Paid late in FY": d["paid_late"]}
        dl("⬇ Download 43B(h) workbook (.xlsx)", E.export_workbook(sheets), f"{slug}_43Bh_FY{r['fy']}-{str(r['fy'] + 1)[-2:]}.xlsx",
           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "dl_43")
        st.caption("Logic: Micro/Small bills accepted in the FY and unpaid at 31-Mar with the due date (accepted + agreed days up to 45, else 15) already passed "
                   "are disallowed and become deductible when paid. Bills paid late within the same FY are shown separately for interest awareness.")

    # ---------------- Form 1 ---------------- #
    with tab_f1:
        ps_default = E.half_year_start(as_of)
        ps = pd.Timestamp(st.date_input("Period start", value=ps_default, format="DD/MM/YYYY",
                                        help="Payments made from this date to the as-of date are reported in columns (d) and (e)."))
        f1 = E.form1_table(r["res"], as_of, ps)
        reason_col = E.F1_COLS[-1]
        if len(f1) and r.get("reasons"):
            f1[reason_col] = f1["Name of MSE Supplier"].map(r["reasons"]).fillna("")
        _, ann = E.form1(L, as_of)
        st.caption(f"MSME Form 1 · period {ps:%d-%m-%Y} to {as_of:%d-%m-%Y} · Micro/Small suppliers only")
        k = st.columns(4)
        k[0].metric("Suppliers", len(f1))
        k[1].metric("Paid within 45 days", inr(f1["Paid ≤45d TReDS - Amount (Rs.)"].sum() + f1["Paid ≤45d Other mode - Amount (Rs.)"].sum()) if len(f1) else "₹0")
        k[2].metric("Paid after 45 days", inr(f1["Paid after 45d - Amount (Rs.)"].sum()) if len(f1) else "₹0")
        k[3].metric("Outstanding > 45 days", inr(f1["Outstanding >45d - Amount (Rs.)"].sum()) if len(f1) else "₹0")
        st.caption("Columns: (a) S.No. · (b) Name · (c) PAN · (d) Paid within 45 days: (i) TReDS, (ii) other mode · (e) Paid after 45 days · "
                   "(f) Outstanding ≤ 45 days · (g) Outstanding > 45 days · (h) Reason for delay. Fill (h) below.")
        disp = f1.copy()
        for c in disp.columns:
            if E.is_amount_col(c, f1[c]):
                disp[c] = f1[c].map(E.fmt_inr)
        edited_disp = st.data_editor(disp, width="stretch", hide_index=True, key=f"f1_{slug}_{st.session_state.get('load_counter', 0)}_{as_of:%Y%m%d}_{ps:%Y%m%d}",
                             disabled=[c for c in f1.columns if not c.startswith("Reason")])
        f1e = f1.copy()
        f1e[reason_col] = edited_disp[reason_col].values
        if len(f1e):
            if r.get("run_id"):
                if st.button("💾 Save reasons to this saved run"):
                    r["reasons"] = dict(zip(f1e["Name of MSE Supplier"], f1e[reason_col]))
                    store.save_reasons(slug, r["run_id"], r["reasons"])
                    st.success("Reasons saved.")
            else:
                st.caption("Save the run in tab 2 to keep the reasons you type here.")
        dl("⬇ Download Form 1 workbook (.xlsx)", E.form1_workbook(f1e, ann, prof["name"], as_of, ps),
           f"{slug}_MSME_Form1_{as_of:%Y%m%d}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "dl_f1")
        with st.expander("Bill-level annexure (outstanding > 45 days)"):
            show(ann[["Vendor Name", "Bill No", "Accepted On", "Due Date", "Days Since Acceptance", "Outstanding", "Branch"]] if len(ann) else ann)

    # ---------------- Interest ---------------- #
    with tab_int:
        st.caption("Interest on delayed payments to Micro/Small suppliers – Section 16, MSMED Act: compound interest with monthly rests at "
                   "3 × RBI Bank Rate, from the day after the due date until payment (or the as-of date).")
        rates = store.load_bank_rates()
        with st.expander("RBI Bank Rate table (editable – verify against RBI notifications)"):
            rt = st.data_editor(rates.assign(**{"Effective From": rates["Effective From"].dt.date}), num_rows="dynamic", width="stretch",
                                key="rates_editor", column_config={"Effective From": st.column_config.DateColumn(format="DD-MM-YYYY"),
                                                                   "Bank Rate %": st.column_config.NumberColumn(format="%.2f", min_value=0.0)})
            if st.button("💾 Save rate table"):
                try:
                    store.save_bank_rates(rt)
                    st.success("Saved.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
            st.caption("Bank Rate = MSF rate. The rate in force on each day applies, so the table drives mid-period rate changes.")
            st.markdown(f"🔗 Official source: [RBI home page – *Current Rates* box]({X.RBI_HOME_URL}) · "
                        "the effective date is in the RBI monetary-policy press release.")
            if st.button("🔎 Check latest Bank Rate on RBI website", key="rbi_check"):
                try:
                    st.session_state["rbi_rate"] = X.fetch_rbi_bank_rate()
                    st.session_state.pop("rbi_err", None)
                except RuntimeError as e:
                    st.session_state.pop("rbi_rate", None)
                    st.session_state["rbi_err"] = str(e)
            if st.session_state.get("rbi_err"):
                st.warning(st.session_state["rbi_err"])
            if "rbi_rate" in st.session_state:
                found = float(st.session_state["rbi_rate"])
                latest = float(rates["Bank Rate %"].iloc[-1])
                if abs(found - latest) < 1e-9:
                    st.success(f"RBI shows Bank Rate {found:.2f}% – same as the latest row in your table "
                               f"(effective {rates['Effective From'].iloc[-1]:%d-%m-%Y}). Nothing to change.")
                else:
                    st.info(f"RBI shows Bank Rate **{found:.2f}%**, but your latest row is {latest:.2f}% "
                            f"(from {rates['Effective From'].iloc[-1]:%d-%m-%Y}). Enter the date it took effect "
                            "(see the RBI press release) and add it.")
                    eff = st.date_input("Effective from", value=None, format="DD-MM-YYYY", key="rbi_eff")
                    if st.button("➕ Add this rate to the table", key="rbi_add", disabled=eff is None):
                        try:
                            new = pd.concat([rates.assign(**{"Effective From": rates["Effective From"].dt.date}),
                                             pd.DataFrame({"Effective From": [eff], "Bank Rate %": [found]})], ignore_index=True)
                            store.save_bank_rates(new)
                            st.session_state.pop("rbi_rate", None)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
        mult = st.number_input("Multiplier × Bank Rate", 1.0, 10.0, 3.0, 0.5, help="3 under Section 16 (notwithstanding any agreement).")
        det_i = X.compute_interest(r["res"], as_of, rates, mult)
        vs = X.vendor_summary(det_i)
        k = st.columns(4)
        k[0].metric("Interest payable (total)", inr(det_i["Interest Payable"].sum()))
        k[1].metric("On bills still open", inr(det_i.loc[det_i["Status"] == "Open", "Interest Payable"].sum()))
        k[2].metric("On bills paid late", inr(det_i.loc[det_i["Status"] == "Paid late", "Interest Payable"].sum()))
        k[3].metric("Suppliers", len(vs))
        cur_rate = mult * float(rates.loc[rates["Effective From"] <= as_of, "Bank Rate %"].iloc[-1]) if (rates["Effective From"] <= as_of).any() else float("nan")
        st.caption(f"Rate in force at {as_of:%d-%m-%Y}: {cur_rate:.2f}% p.a. ({mult:g} × Bank Rate). Interest accrues up to {as_of:%d-%m-%Y}.")
        st.markdown("**By supplier**")
        show(vs)
        st.markdown("**By bill**")
        show(det_i, height=350)
        dl("⬇ Download interest workbook (.xlsx)", E.export_workbook({"By supplier": vs, "By bill": det_i, "Bank rates": rates}),
           f"{slug}_MSME_interest_{as_of:%Y%m%d}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "dl_int")
        st.caption("Method: interest starts the day after the due date; accrued interest is added to the interest-bearing base at each month end; "
                   "payments reduce principal only and interest stops once principal is cleared. Interest under s.16 is not an allowable deduction (s.23).")

# --------------------------------------------------------------------------- #
with tab_help:
    st.markdown(f"""
**Workflow:** pick company → (once) set up the Vendor Master → upload Bills (+ Payments) → Run → review Dashboard, 43B(h), Form 1.

**Due date rule:** due date = acceptance date + agreed credit days (written agreement, capped at {E.STATUTORY_MAX_DAYS}); with no agreement, {E.NO_AGREEMENT_DAYS} days.
If Acceptance Date is blank, Bill Date is used. Only **Micro** and **Small** vendors are covered; bills accepted before a vendor's Udyam registration date are not.

**Payments:** a payment with a Bill No settles that bill; a payment without one is applied to the vendor's oldest open bills (by due date).
Credit notes / adjustments should be entered as payments.

**Other sources (tab 2):** instead of the templates you can upload a *vendor statement* or a report exported from your own software
(.xlsx / .xls / .csv / text-based PDF). The header row and columns are detected automatically, rows are classed as Bill / Payment
(Debit–Credit side, wording, running balance or amount sign), opening balances and totals are skipped, and payments are linked to the
invoice named in their narration. Check the preview, correct any row, then add it to the run. Scanned PDFs need OCR first.
Statements carry no acceptance date, so the bill date is used.

**Saved runs:** save a run in tab 2 (inputs + the vendor master used) and reopen it later from "Saved runs", e.g. last half-year's Form 1.
Reasons typed in Form 1 can be saved to the run. Stored under the company's `data/companies/<name>/runs/` folder.

**Interest (tab 6):** Section 16 MSMED Act – 3 × RBI Bank Rate, compounded with monthly rests, from the day after the due date.
The Bank Rate table is editable.

**Files:** .xlsx, .xls and .csv are accepted. Dates are read day-first (dd-mm-yyyy). Column headers are matched flexibly (e.g. *Invoice No* → *Bill No*), but required columns must be present — see the templates in the sidebar.

This is a decision-support tool; confirm treatment with your tax advisor before filing.
""")
