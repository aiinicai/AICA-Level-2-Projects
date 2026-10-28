"""Tally trial balance -> Schedule III statements, cash flow, notes and a reviewer's report."""
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fsbuilder import pipeline as P  # noqa: E402
from fsbuilder.format import UNITS, inr, rs  # noqa: E402
from fsbuilder.mapping import Rulebook, map_ledgers  # noqa: E402
from fsbuilder.model import Signatories, build_model  # noqa: E402
from fsbuilder.reviewer import run_review  # noqa: E402
from fsbuilder.reviewer.checklist import STATUSES  # noqa: E402
from fsbuilder.reviewer.llm import GeminiLLM, LLMError  # noqa: E402
from fsbuilder.reviewer.ratios import fmt_value, fmt_variance  # noqa: E402
from fsbuilder.tb import TallyError, fetch_from_tally, normalise  # noqa: E402
from ui import ai, charts, theme  # noqa: E402


@st.cache_resource
def rulebook():
    return Rulebook.load()


ss = st.session_state
for k, v in {"tb": None, "load_id": 0, "committed": {}, "frames": {}, "ai": None, "files": None}.items():
    ss.setdefault(k, v)
rb = rulebook()

theme.header("Financial Statements Builder", "Trial balance in. Schedule III statements, AS 3 cash flow, linked notes and a reviewer's "
             "report out. Everything is computed on this computer; only the optional AI review contacts Google.", "📑")


def cell_text(v, unit):
    """An amount in the presentation unit, or the words a text note holds."""
    return v if isinstance(v, str) else ("-" if v is None else unit.fmt(v))


def note_frame(n, unit):
    rows = []
    for r in n.rows:
        vals = [""] * len(n.header[1:]) if len(r) == 1 else [cell_text(v, unit) for v in r[1:]]
        rows.append(dict(zip(n.header, [r[0]] + vals)))
    if n.total:
        rows.append(dict(zip(n.header, [n.total[0]] + [cell_text(v, unit) for v in n.total[1:]])))
    return pd.DataFrame(rows)


def show_note(model, no):
    """A note, with the statement lines that use it. This is the link from the face of the statements to the notes."""
    n = next(x for x in model.notes if x.no == no)
    used = [r.label for r in model.bs + model.pl if r.note == n.no]
    with st.container(border=True):
        st.markdown(f"**Note {n.no}: {n.title}**")
        st.caption("Used by: " + (", ".join(used) or "no statement line"))
        st.dataframe(note_frame(n, model.unit), hide_index=True, width="stretch")
        if n.movement:
            mv = n.movement
            st.markdown(f"**{mv['title']}**")
            body = [dict(zip(mv["header"], [r[0]] + [cell_text(v, model.unit) for v in r[1:]])) for r in mv["rows"]]
            if mv["total"]:
                body.append(dict(zip(mv["header"], [mv["total"][0]] + [cell_text(v, model.unit) for v in mv["total"][1:]])))
            st.dataframe(pd.DataFrame(body), hide_index=True, width="stretch")
        if n.comment:
            st.caption(n.comment)
        if n.gaps:
            bullets = "\n".join(f"- {g}" for g in n.gaps)
            st.warning(f"Information required (not available in Tally):\n{bullets}")


def statement_table(frame, key):
    """A statement. Select a line that has a note to open that note underneath."""
    ev = st.dataframe(frame, hide_index=True, width="stretch", height=560, key=key, on_select="rerun",
                      selection_mode="single-row")
    rows = ev.selection.rows if ev and ev.selection else []
    if rows and "Note" in frame and frame.iloc[rows[0]]["Note"]:
        show_note(model, int(frame.iloc[rows[0]]["Note"]))
    else:
        st.caption("Select a line with a note number to open the note.")



t_load, t_map, t_fs, t_rev, t_dl = st.tabs(["1 · Load", "2 · Check & map", "3 · Statements", "4 · Review & AI", "5 · Download"])

with t_load:
    # ============================== 1. trial balance ==============================
    st.subheader("Load the trial balance")
    source = st.radio("Source", ["Upload Excel or CSV", "Pull from TallyPrime"], horizontal=True)
    d_from, d_to = P.last_financial_year()
    c1, c2, c3 = st.columns([3, 1, 1])
    company_label = {"Pull from TallyPrime": "Company name (exactly as in Tally)",
                     "Upload Excel or CSV": "Company name (leave blank to use the name in the file)"}.get(source, "Company name")
    company = c1.text_input(company_label, "", key=f"co_{source}")
    start = c2.date_input("From", d_from, format="DD/MM/YYYY", key=f"from_{source}")
    end = c3.date_input("To", d_to, format="DD/MM/YYYY", key=f"to_{source}")

    tb_file = groups_file = ledger_list = None
    host, port = "localhost", 9000
    if source == "Upload Excel or CSV":
        st.caption("Upload the trial balance exactly as Tally exports it (TallyPrime: Trial Balance, set the period to the "
                   "whole financial year with F2, then Alt+E and Excel). Company, period and Dr/Cr are read from the file, "
                   "so the dates above are only used for layouts that do not state a period.")
        u1, u2 = st.columns(2)
        tb_file = u1.file_uploader("Trial balance exported from Tally (Excel)", type=["xlsx", "csv"])
        ledger_list = u2.file_uploader("Ledger list with groups (optional, makes the mapping exact)", type=["xlsx", "csv"],
                                       help="Tally's trial balance has no ledger groups, so they are guessed from ledger names "
                                            "and flagged. A list of ledgers with the group each sits under (columns Name and "
                                            "Under) removes the guesswork.")
        with st.expander("Another layout, custom groups, or a template"):
            groups_file = st.file_uploader("Custom groups file (name, parent, nature), only if you added your own groups",
                                           type=["xlsx", "csv"])
            st.write("Instead of Tally's export you can use a simple layout: one row per ledger with the columns "
                     "`name, group, opening_amount, opening_dr_cr, closing_amount, closing_dr_cr`. Title rows, extra sheets "
                     "and a Total row are fine, and headers such as Ledger Name, Under and Opening Balance are recognised.")
            d1, d2 = st.columns(2)
            d1.download_button("Download the Excel template", P.sample_xlsx_bytes(), "trial_balance_template.xlsx",
                               P.MIME["xlsx"], help="Sample data with a 'Read me' sheet explaining each column")
            d2.download_button("Download the CSV layout", P.sample_csv_bytes(), "trial_balance_layout.csv", "text/csv")
    elif source == "Pull from TallyPrime":
        t1, t2 = st.columns(2)
        host = t1.text_input("Host", "localhost")
        port = int(t2.number_input("Port", 1, 65535, 9000))
        st.caption("TallyPrime must be open with the company loaded and acting as a server: "
                   "F1 Help > Settings > Connectivity > Client/Server configuration.")

    if st.button("Load trial balance", type="primary"):
        try:
            upload = source == "Upload Excel or CSV"
            if not company.strip() and not upload:
                raise ValueError("Enter the company name.")
            if start >= end and not upload:
                raise ValueError("The 'From' date must be before the 'To' date.")
            with st.spinner("Loading..."):
                if upload:
                    if tb_file is None:
                        raise ValueError("Choose a trial balance file (Excel or CSV) first.")
                    tb = P.read_trial_balance(tb_file, tb_file.name, groups_file, groups_file.name if groups_file else "",
                                              company.strip(), start, end, ledger_list,
                                              ledger_list.name if ledger_list else "")
                else:
                    tb = fetch_from_tally(company.strip(), start, end, host, port, timeout=20)
            tb = normalise(tb)
            if not tb.company:
                raise ValueError("Enter the company name: the file does not state one.")
            if tb.from_date >= tb.to_date:
                raise ValueError("The 'From' date must be before the 'To' date.")
            ss.update(tb=tb, load_id=ss.load_id + 1, committed={}, frames={}, ai=None, files=None)
        except (ValueError, TallyError) as e:
            st.error(str(e))

    tb = ss.tb
    if tb is None:
        st.info("Load a trial balance to continue: choose Upload Excel or CSV and add the trial balance exported from Tally. "
                "Example files in Tally's own layout are in the samples folder.")
        for t in (t_map, t_fs, t_rev, t_dl):
            t.info("Load a trial balance on the first tab to continue.")
        st.stop()
    st.success(f"Loaded {len(tb.ledgers)} ledgers for {tb.company}, {tb.from_date:%d/%m/%Y} to {tb.to_date:%d/%m/%Y}.")


with t_map:
    # ============================== 2. check the trial balance ==============================
    st.subheader("Check the trial balance")
    L = tb.ledgers
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ledgers", len(L))
    m2.metric("Closing debits", inr(round(L.loc[L["closing"] > 0, "closing"].sum())))
    m3.metric("Closing credits", inr(round(-L.loc[L["closing"] < 0, "closing"].sum())))
    m4.metric("Opening difference", inr(round(L["opening"].sum())) if abs(L["opening"].sum()) >= 0.5 else "Agrees")
    for note in tb.adjustments:
        st.info(note)
    for w in tb.warnings:
        st.warning(w)
    if not tb.adjustments and not tb.warnings:
        st.caption("Debits equal credits, and opening balances agree. Nothing needed adjusting.")

    # ============================== 3. mapping ==============================
    st.subheader("Review the mapping to Schedule III")
    st.caption("Each ledger is placed on a Schedule III line by the rules in `fsbuilder/rulebook_non_ind_as.json`. "
               "Change the line or sub-head where you disagree; your changes are kept as overrides.")
    rule_mapped = map_ledgers(tb)
    only_attention = st.toggle("Show only ledgers that need attention (unmapped or with a review note)", value=True)
    fkey = f"{ss.load_id}_{only_attention}"
    if fkey not in ss.frames:   # frozen per view so Streamlit never re-applies an edit twice
        cur_map = map_ledgers(tb, overrides=ss.committed)
        frame = P.editor_frame(cur_map, rb)
        live = (cur_map["opening"].abs() + cur_map["closing"].abs()) > 0.005
        keep = (cur_map["source"] == "unmapped") | ((cur_map["review"] != "") & live) | (cur_map["source"] == "override")
        frame = frame[keep.values] if only_attention else frame
        order = (cur_map["source"] != "unmapped").values[frame.index]
        ss.frames[fkey] = frame.iloc[sorted(range(len(frame)), key=lambda i: order[i])].reset_index(drop=True)
    edited = st.data_editor(
        ss.frames[fkey], key=f"ed_{fkey}", hide_index=True, width="stretch",
        height=min(420, 45 + 35 * max(len(ss.frames[fkey]), 1)), num_rows="fixed",
        disabled=["Ledger", "Tally group", "Closing Dr / (Cr)", "Source", "Review note"],
        column_config={
            "Schedule III line": st.column_config.SelectboxColumn(options=P.line_options(rb), required=True, width="large"),
            "Sub-head": st.column_config.TextColumn(width="medium"),
            "Review note": st.column_config.TextColumn(width="large"),
            "Override reason": st.column_config.TextColumn(width="medium", help="Why you changed it; recorded in the Mapping sheet")})
    shown = set(edited["Ledger"])
    ss.committed = {**{k: v for k, v in ss.committed.items() if k not in shown},
                    **P.overrides_from_edits(rule_mapped, edited, ss.committed)}
    mapped = map_ledgers(tb, overrides=ss.committed)
    unmapped = mapped[mapped["source"] == "unmapped"]["ledger"].tolist()

    b1, b2, b3 = st.columns([1, 1, 2])
    b1.download_button("Download overrides (JSON)", P.overrides_bytes(ss.committed), "overrides.json", "application/json",
                       disabled=not ss.committed, help="Reuse next year or for another run")
    if b2.button("Clear all overrides", disabled=not ss.committed):
        ss.update(committed={}, frames={}, ai=None, files=None)
        st.rerun()
    up = b3.file_uploader("Load overrides (JSON)", type=["json"], label_visibility="collapsed")
    if up is not None and st.button("Apply the overrides file"):
        try:
            ss.update(committed=P.parse_overrides_json(up.getvalue(), rb), frames={}, ai=None, files=None)
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    n_notes = int(((mapped["review"] != "") & ((mapped["opening"].abs() + mapped["closing"].abs()) > 0.005)).sum())
    st.caption(f"{len(ss.committed)} override(s) in force. {n_notes} ledger(s) with a balance carry a review note.")
    if unmapped:
        st.error(f"{len(unmapped)} ledger(s) are not mapped and are left out of the statements: {', '.join(unmapped)}. "
                 "Choose a Schedule III line for each above.")


with t_fs:
    # ============================== 4. statements ==============================
    st.subheader("Statements, notes and disclosures")
    units, default_unit = P.unit_choices(mapped)
    keys = [u.key for u in units]
    uc1, uc2 = st.columns([1, 3])
    unit_key = uc1.selectbox("Presentation unit", keys, index=keys.index(default_unit.key), format_func=lambda k: UNITS[k].label,
                             key=f"unit_{ss.load_id}")
    uc2.caption("Schedule III makes rounding off compulsory (ICAI Guidance Note, para 6.15): with total income below "
                "Rs 100 crore, figures are rounded to hundreds, thousands, lakhs or millions; from Rs 100 crore, to lakhs, "
                "millions or crores. One unit is used throughout the statements and notes.")
    try:
        model = build_model(tb, mapped, unit=unit_key)
    except Exception as e:
        st.error(f"The statements could not be built: {e}")
        for t in (t_rev, t_dl):
            t.info("Fix the error on the Statements tab first.")
        st.stop()
    sig = P.signature(model)
    tabs = st.tabs(["Balance sheet", "Profit and loss", "Cash flow", "Notes", "Disclosures", "Open items"])
    with tabs[0]:
        statement_table(P.statement_frame(model.bs, unit=model.unit), "bs_table")
    with tabs[1]:
        statement_table(P.statement_frame(model.pl, prev_col=False, unit=model.unit), "pl_table")
    with tabs[2]:
        st.dataframe(P.statement_frame(model.cashflow, prev_col=False, note_col=False, unit=model.unit), hide_index=True, width="stretch", height=640)
        for n in model.cf_notes:
            st.caption("• " + n)
    with tabs[3]:
        labels = [f"Note {n.no}: {n.title}" for n in model.notes]
        pick = st.selectbox("Open a note", labels, key="note_pick")
        show_note(model, model.notes[labels.index(pick)].no)
    with tabs[4]:
        st.caption("Additional regulatory information and other statutory disclosures under Schedule III, the Companies Act 2013 and the "
                   "accounting standards. Facts the books show are filled in; items only management can answer say so. "
                   "They are in the Word file after the notes and on the Disclosures sheet of the Excel file.")
        for d in model.disclosures:
            with st.expander(f"{d.no}. {d.title}", expanded=d.no in ("D1", "D2")):
                st.caption(d.ref)
                st.table(pd.DataFrame(d.rows, columns=d.header).set_index(d.header[0]))
                if d.comment:
                    st.caption(d.comment)
    with tabs[5]:
        st.caption("[R#] are classification judgements shown on the face of the statements; [O#] are observations.")
        st.dataframe(pd.DataFrame([{"Ref": f.ref, "Area": f.area, "Ledger": f.ledger or "-", "Amount": model.unit.fmt(f.amount),
                                    "Matter": f.text} for f in model.flags]), hide_index=True, width="stretch", height=420,
                     column_config={"Matter": st.column_config.TextColumn(width="large")})
    for b in model.basis:
        st.caption("Note: " + b)


with t_rev:
    # ============================== 5. review ==============================
    st.subheader("Review the statements")
    rev = ss.ai[1] if ss.ai is not None and ss.ai[0] == sig else run_review(model, mapped)

    s = rev.summary
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Tie-out checks passed", f"{s['passed']} of {s['checks']}")
    r2.metric("Ratios moved over 25%", s["ratios_flagged"])
    r3.metric("Information required", s["checklist"].get("Information required", 0))
    r4.metric("AI observations", s["ai_observations"] if rev.ai_requested else "not run")
    if rev.ai_requested:
        st.info(f"The AI raised {s['ai_observations']} observation(s) and drafted reasons for the ratios that moved over 25%. "
                "Read them on the **AI review of the statements** tab just below (the last tab); they are also on the AI analysis sheet of the Excel file.")
    if s["failed"]:
        st.error(f"{s['failed']} casting or tie-out check(s) failed. See the Tie-outs tab.")
    for e in rev.ai.errors:
        st.warning(e)

    rt = st.tabs(["Overview", "Tie-outs", "Ratios", "Checklist", "AI review of the statements"])
    with rt[0]:
        charts.statements(model, rev)
    with rt[1]:
        df = pd.DataFrame([{"Ref": c.id, "Area": c.area, "Check": c.description, "Expected": inr(round(c.expected or 0)),
                            "Actual": inr(round(c.actual or 0)), "Result": c.status} for c in rev.tieouts])
        df = df.sort_values("Result", key=lambda x: x.map({"Fail": 0, "Pass": 1}), kind="stable")
        st.dataframe(df, hide_index=True, width="stretch", height=420, column_config={"Check": st.column_config.TextColumn(width="large")})
    with rt[2]:
        st.dataframe(pd.DataFrame([{"Ratio": x.name, "Current": fmt_value(x, x.cur), "Previous": fmt_value(x, x.prev),
                                    "Change": fmt_variance(x.variance), "Over 25%": "Yes" if x.flagged else "",
                                    "Explanation": (f"{x.explanation} ({x.explanation_source})" if x.flagged else x.note)}
                                   for x in rev.ratios]), hide_index=True, width="stretch",
                     column_config={"Explanation": st.column_config.TextColumn(width="large")})
        st.caption("Ratios needing the previous year's profit and loss cannot be tested for change; load that year to complete them.")
    with rt[3]:
        pick = st.multiselect("Status", STATUSES, default=[x for x in STATUSES if x not in ("Not applicable", "Complete")])
        st.dataframe(pd.DataFrame([{"Ref": i.id, "Area": i.area, "Requirement": i.requirement, "Status": i.status,
                                    "Evidence / what to obtain": i.evidence + (f" Obtain: {i.ask}." if i.ask else "")}
                                   for i in rev.checklist if i.status in pick]), hide_index=True, width="stretch", height=420,
                     column_config={"Requirement": st.column_config.TextColumn(width="large"),
                                    "Evidence / what to obtain": st.column_config.TextColumn(width="large")})
    with rt[4]:
        st.info("**This AI reviews the financial statements above**: the figures, ratios and cash flow of this trial balance. "
                "It does not read the Day Book. The Day Book has its own AI review on the Day Book Audit page.")
        st.markdown("**What it adds.** Everything on the other tabs is computed by code. The AI reads the same figures and does two things "
                    "code cannot: it drafts the *reason* for each ratio that moved over 25%, and it raises *analytical observations* an "
                    "experienced reviewer would (for example, profit far above operating cash flow). It sees figures and labels only, never "
                    "ledger or party names. It cites the facts it relied on, and any number it states that is not in the books is flagged.")
        api_key, model_name, consent = ai.config()
        ai.badge()
        ai.consent_box("the figures and statement labels of this trial balance (no ledger or party names)")
        if not ai.ready():
            st.caption("Add your key and give consent on the Settings & AI page to enable this.")
            theme.safe_link("ui/settings.py", "Open Settings & AI", ":material/tune:")
        if st.button("Run AI review", disabled=not ai.ready(), type="primary"):
            try:
                with st.spinner("Asking Gemini..."):
                    ss.ai = (sig, run_review(model, mapped, GeminiLLM(api_key, model_name)))
                ss.ai_error = ""
            except LLMError as e:
                ss.ai_error = str(e)
            st.rerun()                                  # so the counts above and the other tabs show the AI's work
        if ss.get("ai_error"):
            st.error(ss.ai_error)
        if ss.ai is not None and ss.ai[0] != sig:
            st.warning("The numbers have changed since the AI review was run, so its results are not shown. Run it again.")
        if not rev.ai_requested:
            st.caption("The AI review has not been run for this trial balance. Everything else in the tool works without it.")
        else:
            a1, a2, a3 = st.columns(3)
            drafted = sum(1 for x in rev.ratios if x.flagged and x.explanation_source and "AI" in x.explanation_source)
            a1.metric("Observations raised", len(rev.ai.observations))
            a2.metric("Ratio reasons drafted", drafted)
            a3.metric("Needing verification", s["ai_ungrounded"], help="Observations that contain a figure not taken from the books")
            flagged = [x for x in rev.ratios if x.flagged]
            if flagged:
                st.markdown("**Ratio movements over 25%: reasons drafted by the AI**")
                st.table(pd.DataFrame([{"Ratio": x.name, "Current": fmt_value(x, x.cur), "Previous": fmt_value(x, x.prev),
                                        "Change": fmt_variance(x.variance), "Reason (" + (x.explanation_source or "rule") + ")": x.explanation}
                                       for x in flagged]).set_index("Ratio"))
                st.caption("These are drafts for the reviewer to confirm with management, not conclusions.")
            st.markdown("**Analytical observations**")
            if not rev.ai.observations:
                st.write("The model raised no further observations.")
            for o in rev.ai.observations:
                with st.container(border=True):
                    st.markdown(f"**{o.title}**  ·  {o.severity}" + ("" if o.grounded else "  ·  ⚠ contains figures not taken from the books: verify"))
                    st.write("Why it matters: " + o.why)
                    st.write("Procedure: " + o.procedure)
                    st.caption("Based on: " + "; ".join(f"{rev.facts.get(i).label}: {rev.facts.get(i).text}" for i in o.fact_ids if rev.facts.get(i)))


with t_dl:
    # ============================== 6. download ==============================
    st.subheader("Download the files")
    if unmapped:
        st.warning("Map every ledger in step 3 before generating the files.")
    with st.expander("Signatures (printed at the end of the balance sheet, profit and loss, cash flow and the disclosures)", expanded=True):
        st.caption("Leave a field empty to print a line to fill in by hand. Nothing here changes any figure.")
        a, b = st.columns(2)
        with a:
            st.markdown("**Auditors**")
            firm = st.text_input("Firm name", "XYZ Chartered Accountants", key="sg_firm")
            frn = st.text_input("Firm Registration No. (FRN)", key="sg_frn")
            partner = st.text_input("Name of partner", key="sg_partner")
            membership = st.text_input("Membership No.", key="sg_mem")
            place = st.text_input("Place", key="sg_place")
            sign_date = st.date_input("Date of signing (auditors)", value=None, format="DD/MM/YYYY", key="sg_date")
        with b:
            st.markdown("**Board of Directors**")
            company = st.text_input("Name of company", model.company, key="sg_company")
            d1 = st.text_input("Director 1: name", key="sg_d1")
            n1 = st.text_input("Director 1: DIN", key="sg_n1")
            d2 = st.text_input("Director 2: name", key="sg_d2")
            n2 = st.text_input("Director 2: DIN", key="sg_n2")
            board_date = st.date_input("Date of signing (directors)", value=None, format="DD/MM/YYYY", key="sg_bdate")
    sign = Signatories(firm.strip(), frn.strip(), partner.strip(), membership.strip(), place.strip(), sign_date, company.strip(),
                       [(d1.strip(), n1.strip()), (d2.strip(), n2.strip())], board_date)
    files_key = sig + ("-ai" if rev.ai_requested else "") + "-" + repr(sign)
    if st.button("Generate Word and Excel files", type="primary", disabled=bool(unmapped)):
        with st.spinner("Writing files..."):
            ss.files = (files_key, P.build_files(model, rev, sign))
    if ss.files is not None:
        if ss.files[0] == files_key:
            cols = st.columns(4)
            for col, (label, (name, data, mime)) in zip(cols, ss.files[1].items()):
                col.download_button(label, data, name, mime, width="stretch")
            st.caption(f"{rs(model.profit)} profit. The Excel file is linked: each statement figure reads its note, so a change "
                       "in a note flows through. It also holds the Disclosures sheet and an AI analysis sheet (ratio reasons and the AI's "
                       "observations, or a note that the AI was not run). Files carry the [R#] review markers and are marked DRAFT.")
        else:
            st.info("The mapping, review or signatures have changed since the files were generated. Generate them again.")


