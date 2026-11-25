"""NOTICE-MATE — working screens reused from V2 (documents, notice, analysis, issues, reconciliation,
lenders, tax, research, client request, draft, review, AI, history, providers, registry, admin).
The V3 guided shell in app.py arranges these into steps. Nothing here sets page config or runs main()."""
from __future__ import annotations

import json
import pathlib
import re
import sys

import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ui import (DRAFT_BANNER, alert, badge, banner, basis_line, call, empty, esc, hero, inject_css, inr, json_download, kpi,  # noqa: E402
                section, steps, toast)

NAV = ["🏠 Home", "📋 Cases & dashboard", "📂 Case workspace", "📚 Legal sources", "🛠️ Settings"]  # must match app.py
DOC_TYPES = ["NOTICE", "BANK_STATEMENT", "BANK_BOOK", "CASH_BOOK", "SALES_LEDGER", "DEBTOR_LEDGER", "CAPITAL_ACCOUNT",
             "FINANCIAL_STATEMENTS", "ITR", "FORM_26AS_AIS", "CONFIRMATION", "INVOICE", "AGREEMENT", "GST_RETURN", "OTHER"]
CATS = ["FIRM", "LLP", "INDIVIDUAL", "HUF", "COMPANY_DOMESTIC", "AOP_BOI", "OTHER"]
EV_STATUSES = ["SUFFICIENT", "PARTIALLY_SUFFICIENT", "INSUFFICIENT", "NOT_PROVIDED", "CONTRADICTORY", "REQUIRES_VERIFICATION"]


def goto(page: str, case_id: int | None = None):
    # The nav radio is already rendered this run, so its key can't be changed directly; apply on next run.
    st.session_state["_goto"] = page
    if case_id is not None:
        st.session_state.case_id = case_id
    st.rerun()


# ======================= LOGIN =======================
def login_view():
    c1, c2, c3 = st.columns([1, 1.25, 1])
    with c2:
        st.markdown('<div style="height:6vh"></div>', unsafe_allow_html=True)
        hero("NOTICE-MATE", "Income-tax notice analysis & resolution workbench for Chartered Accountants · local-first")
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", type="primary", use_container_width=True):
                res = call("POST", "/auth/login", json_body={"username": u, "password": p})
                if res:
                    st.session_state.token = res["token"]
                    st.session_state.user = res["user"]
                    st.rerun()
        st.caption("Documents stay on this computer. Nothing is sent to an AI provider without your explicit approval.")


# ======================= DASHBOARD =======================
def dashboard_view():
    d = call("GET", "/dashboard")
    if d is None:
        return
    user = st.session_state.user
    hero(f"Good to see you, {user['full_name'].split()[0]}", f"Practice overview as of {d['as_of']} · figures are computed from your local case data")
    cols = st.columns(6)
    kpi(cols[0], "Total cases", d["total_cases"], f"{d['active_cases']} active", "blue")
    kpi(cols[1], "Active cases", d["active_cases"], "not submitted/closed", "teal")
    kpi(cols[2], "Pending notices", d["pending_notices"], "in active cases", "blue")
    kpi(cols[3], "Due ≤ 15 days", len(d["upcoming_deadlines"]), f"{sum(1 for x in d['upcoming_deadlines'] if not x['verified'])} unverified", "amber")
    kpi(cols[4], "Overdue", len(d["overdue"]), "deadline passed", "red" if d["overdue"] else "green")
    kpi(cols[5], "Awaiting CA review", len(d["awaiting_review"]), "latest draft not approved", "amber" if d["awaiting_review"] else "green")

    left, right = st.columns([1.35, 1])
    with left:
        section("Deadlines")
        tl = d["deadline_timeline"]
        if not tl:
            empty("No deadlines recorded", "Parse a notice and verify its compliance date.")
        else:
            for x in tl[:12]:
                dl = x["days_left"]
                tone = "red" if dl < 0 else "amber" if dl <= 3 else "blue"
                when = f"{-dl} days overdue" if dl < 0 else ("today" if dl == 0 else f"in {dl} days")
                st.markdown(f'<div class="nm-row"><div><b>{esc(x["case_ref"])}</b> · {esc(x["assessee"])}'
                            f'<div class="nm-muted">Notice #{x["notice_id"]} · {esc(x["deadline"])}</div></div>'
                            f'<div>{badge(when, tone)} {badge("VERIFIED" if x["verified"] else "UNVERIFIED")}</div></div>',
                            unsafe_allow_html=True)
            chart = {x["case_ref"] + f" #{x['notice_id']}": x["days_left"] for x in tl[:15]}
            st.caption("Days remaining per notice (negative = overdue)")
            st.bar_chart(chart, height=220)
        section("Case status distribution")
        if d["status_distribution"]:
            st.bar_chart(d["status_distribution"], height=200)
        else:
            empty("No cases yet")
    with right:
        section("Important alerts")
        if not d["alerts"]:
            alert("No alerts — all recorded deadlines verified and no open review items.", "info")
        for a in d["alerts"][:14]:
            alert(a["text"], a["level"])
        section("Awaiting CA review")
        if not d["awaiting_review"]:
            st.markdown('<div class="nm-muted">Nothing awaiting review.</div>', unsafe_allow_html=True)
        for a in d["awaiting_review"][:8]:
            c1, c2 = st.columns([3, 1])
            c1.markdown(f'**{esc(a["case_ref"])}** · v{a["version"] or "—"} {badge(a["state"], "amber")}', unsafe_allow_html=True)
            if c2.button("Open", key=f"rv{a['case_id']}"):
                goto(NAV[2], a["case_id"])
    section("Recent activity")
    if not d["recent_activity"]:
        st.markdown('<div class="nm-muted">No activity yet.</div>', unsafe_allow_html=True)
    else:
        st.dataframe([{"When (UTC)": a["ts"].replace("T", " ")[:19], "Case": a["case_ref"], "Event": a["event"].replace("_", " ").title(),
                       "By": a["user"]} for a in d["recent_activity"]], use_container_width=True, hide_index=True)


# ======================= CASES =======================
def cases_view():
    hero("Cases", "Create, find and open client matters")
    warn = st.session_state.pop("case_delete_warn", None)
    if warn:
        alert(warn, "high")
    cases = call("GET", "/cases") or []
    with st.expander("➕ New case", expanded=not cases):
        with st.form("newcase"):
            c1, c2, c3 = st.columns(3)
            ref = c1.text_input("Case reference *", placeholder="PQR-2026-27")
            name = c2.text_input("Assessee name *")
            cat = c3.selectbox("Assessee category *", CATS)
            c4, c5 = st.columns(2)
            pan = c4.text_input("PAN (stored locally only; use fictitious PAN for testing)")
            ay = c5.text_input("Assessment / Tax year", placeholder="2026-27")
            parties = st.text_area("Names to redact before any AI use (one per line — partners, lenders, customers)")
            if st.form_submit_button("Create case", type="primary"):
                res = call("POST", "/cases", json_body={"case_ref": ref, "assessee_name": name, "assessee_category": cat,
                                                       "pan": pan or None, "assessment_year": ay or None,
                                                       "party_names": [x for x in parties.splitlines() if x.strip()]})
                if res:
                    toast(f"Case {res['case_ref']} created")
                    goto(NAV[2], res["id"])
    if not cases:
        empty("No cases yet", "Create your first case above.")
        return
    q = st.text_input("🔎 Filter cases", placeholder="reference, assessee, status…").lower()
    shown = [c for c in cases if q in json.dumps([c["case_ref"], c["assessee_name"], c["status"], c.get("assessment_year")]).lower()]
    can_delete = st.session_state.user["role"] in ("CA", "ADMIN")
    pending = st.session_state.get("case_delete_pending")  # {"id", "ref", "name"} fixed when Delete was clicked
    if pending and pending["id"] not in {c["id"] for c in cases}:
        st.session_state.pop("case_delete_pending", None)
        pending = None
    if can_delete:
        st.caption("To keep a finished case, set its status to CLOSED in the case workspace. **Delete** removes a case "
                   "permanently, with all its files and history.")
    for c in shown:
        col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
        col1.markdown(f'**{esc(c["case_ref"])}** — {esc(c["assessee_name"])}<div class="nm-muted">{esc(c["assessee_category"])} · '
                      f'AY/TY {esc(c.get("assessment_year") or "NOT PROVIDED")} · PAN {esc(c["pan_masked"])} · updated {esc(c["updated_at"][:10])}</div>',
                      unsafe_allow_html=True)
        col2.markdown(badge(c["status"]), unsafe_allow_html=True)
        if col3.button("Open →", key=f"open{c['id']}"):
            goto(NAV[2], c["id"])
        if can_delete and col4.button("🗑 Delete", key=f"delcase{c['id']}", disabled=bool(pending)):
            st.session_state["case_delete_pending"] = {"id": c["id"], "ref": c["case_ref"], "name": c["assessee_name"]}
            st.rerun()
        if pending and pending["id"] == c["id"]:
            delete_case_confirm(pending)


def _forget_case(cid: int) -> None:
    for k in list(st.session_state.keys()):
        ks = str(k)
        if ks.endswith(f"_{cid}") or ks in (f"step_{cid}", f"intake_{cid}", f"issue_{cid}", f"cr_{cid}"):
            st.session_state.pop(k, None)
    if st.session_state.get("case_id") == cid:
        st.session_state.pop("case_id", None)


def delete_case_confirm(p: dict):
    """Confirmation bound to one case (id + reference captured when Delete was clicked)."""
    info = call("GET", f"/cases/{p['id']}/delete-preview", quiet=True) or {}
    parts = [f"{info.get('documents', 0)} document(s)", f"{info.get('issues', 0)} issue(s)",
             f"{info.get('drafts', 0)} draft version(s)", f"{info.get('approvals', 0)} approval(s)"]
    alert(f"Permanently delete case “{p['ref']} — {p['name']}”? This removes the notice and supporting files, the text read "
          f"from them, issues, evidence, document matches, drafts and every version, approvals and this case's history "
          f"({', '.join(parts)}). This cannot be undone. To keep the case instead, cancel and set its status to CLOSED.",
          "critical")
    ok = st.checkbox(f"I understand that case {p['ref']} will be deleted permanently", key=f"delcase_ack_{p['id']}")
    a, b = st.columns(2)
    if a.button(f"Delete {p['ref']} permanently", key=f"delcase_go_{p['id']}", type="primary", disabled=not ok):
        res = call("POST", f"/cases/{p['id']}/delete", json_body={"confirm_case_ref": p["ref"]})
        st.session_state.pop("case_delete_pending", None)
        st.session_state.pop(f"delcase_ack_{p['id']}", None)
        if res:
            _forget_case(p["id"])
            if res.get("files_not_removed"):
                st.session_state["case_delete_warn"] = ("The case was deleted, but some files could not be removed (they may be "
                                                        "open in another program): " + "; ".join(res["files_not_removed"]))
            toast(f"Case {p['ref']} deleted", "🗑")
        st.rerun()
    if b.button("Cancel", key=f"delcase_no_{p['id']}"):
        st.session_state.pop("case_delete_pending", None)
        st.session_state.pop(f"delcase_ack_{p['id']}", None)
        st.rerun()


# ======================= CASE WORKSPACE =======================
def workspace_view():
    cases = call("GET", "/cases") or []
    if not cases:
        empty("No cases yet", "Create a case under 📁 Cases.")
        return
    ids = [c["id"] for c in cases]
    cur = st.session_state.get("case_id") if st.session_state.get("case_id") in ids else ids[0]
    sel = st.sidebar.selectbox("Active case", cases, index=ids.index(cur), format_func=lambda c: f"{c['case_ref']} — {c['assessee_name']}")
    st.session_state.case_id = sel["id"]
    cid = sel["id"]
    case = call("GET", f"/cases/{cid}")
    if not case:
        return
    docs = call("GET", f"/cases/{cid}/documents") or []
    ns = call("GET", f"/cases/{cid}/notices") or []
    iss = call("GET", f"/cases/{cid}/issues") or []
    mat = call("GET", f"/cases/{cid}/evidence") or []
    appr = call("GET", f"/cases/{cid}/approval") or {}
    hero(f"{case['case_ref']} — {case['assessee_name']}",
         f"{case['assessee_category']} · AY/TY {case.get('assessment_year') or 'NOT PROVIDED'} · PAN {case['pan_masked']} · status {case['status']}")
    assessed = sum(1 for m in mat if m["source"] == "USER")
    steps([("Documents", bool(docs), f"{len(docs)} uploaded"),
           ("Notice parsed", bool(ns), f"{len(ns)} notice(s)"),
           ("Deadline verified", bool(ns) and all(n["deadline_verified"] for n in ns), "portal check"),
           ("Issues", bool(iss), f"{len(iss)} issue(s)"),
           ("Evidence assessed", bool(mat) and assessed == len(mat), f"{assessed}/{len(mat)} items"),
           ("Draft", bool(appr.get("latest_draft_id")), f"v{appr.get('version') or '—'}"),
           ("Final CA review done", bool(appr.get("approved")), "export unlocked" if appr.get("approved") else "required")])
    c1, c2 = st.columns([3, 1])
    with c2:
        stt = ["OPEN", "AWAITING_CLIENT", "UNDER_REVIEW", "APPROVED", "SUBMITTED", "CLOSED"]
        new = st.selectbox("Case status", stt, index=stt.index(case["status"]) if case["status"] in stt else 0, key=f"cs{cid}")
        if new != case["status"] and st.button("Update status"):
            if call("PUT", f"/cases/{cid}/status", json_body={"status": new}):
                toast("Status updated")
                st.rerun()
    with c1:
        with st.expander("🔒 Redaction terms — names that must never leave this computer"):
            t = st.text_area("One per line (assessee name and PAN are always included)", "\n".join(case["party_names"]), key=f"rt{cid}")
            if st.button("Save redaction terms"):
                if call("PUT", f"/cases/{cid}/redaction-terms", json_body={"names": t.splitlines()}):
                    toast("Redaction terms saved")
    tabs = st.tabs(["📄 Documents", "📨 Notice", "🧠 Analysis", "🧩 Issues & Evidence", "🔁 Reconciliation", "🏦 Lenders & Capital",
                    "🧮 Tax", "⚖️ Research", "📋 Client request", "✍️ Draft", "✅ Review & Export", "🤖 AI", "🕘 History"])
    fns = [lambda: tab_documents(cid, docs), lambda: tab_notice(cid, ns), lambda: tab_analysis(cid, ns), lambda: tab_issues(cid, iss, mat, docs),
           lambda: tab_recon(cid, docs), lambda: tab_parties(cid, iss), lambda: tab_tax(cid, case), lambda: tab_research(cid, iss),
           lambda: tab_client_request(cid), lambda: tab_draft(cid), lambda: tab_review(cid), lambda: tab_ai(cid), lambda: tab_history(cid)]
    for tab, fn in zip(tabs, fns):
        with tab:
            fn()


# ---------- Documents ----------
def upload_files(cid, files) -> int:
    """Upload several files to the case; each is read and then matched to the notice's issues."""
    done = 0
    bar = st.progress(0.0, text="Reading the documents…")
    for n, f in enumerate(files, 1):
        bar.progress(n / max(len(files), 1), text=f"Reading {f.name} ({n} of {len(files)})…")
        res = call("POST", f"/cases/{cid}/documents", files={"file": (f.name, f.getvalue())})
        if res:
            done += 1
            toast(f"{f.name}: read ({res['extraction_status'].lower()})", "📄")
    bar.empty()
    return done


def tab_documents(cid, docs):
    st.markdown("**Add supporting documents** — you can select several files at once (bank statements, cash book, ledgers, "
                "confirmations, invoices, registers, returns). Each file is read on this computer and its contents are matched to "
                "the notice's queries automatically.")
    up = st.file_uploader("Choose supporting documents (PDF, Word, Excel, CSV or images)", accept_multiple_files=True, key=f"up{cid}")
    up = up if isinstance(up, list) else ([up] if up else [])
    if up and st.button(f"⬆️ Upload and read {len(up)} file{'s' if len(up) > 1 else ''}", type="primary", key=f"upb{cid}"):
        with st.spinner("Reading the documents (scanned pages can take a minute)…"):
            n = upload_files(cid, up)
        st.session_state.pop(f"up{cid}", None)
        toast(f"{n} document{'s' if n != 1 else ''} added and matched to the queries", "✅")
        st.rerun()
    if not docs:
        empty("No documents yet", "Add the supporting documents above. You can also add or remove them later.")
        return
    summ = call("GET", f"/cases/{cid}/mapping-summary", quiet=True) or {"issues": []}
    used_by: dict[int, list[str]] = {}
    for i in summ.get("issues", []):
        for d in i["documents"]:
            used_by.setdefault(d["document_id"], []).append(f"Q{i['seq']}")
    for d in docs:
        qs = used_by.get(d["id"])
        title = f"#{d['id']} · {d['original_name']}" + (f"  —  used for {', '.join(qs)}" if qs else
                                                         ("  —  the notice" if d["doc_type"] == "NOTICE" else "  —  not matched to any query yet"))
        with st.expander(title):
            st.markdown(f"{badge(d['doc_type'], 'blue')} {badge('CONFIRMED' if d['doc_type_confirmed'] else 'SUGGESTED', 'green' if d['doc_type_confirmed'] else 'amber')} "
                        f"{badge('Extraction ' + d['extraction_status'], 'green' if d['extraction_status'] == 'OK' else 'amber')}"
                        + (f" {badge('Annexure ' + d['annexure_label'], 'teal')}" if d["is_annexure"] else "")
                        + f'<div class="nm-muted">{d["size_bytes"]:,} bytes · sha256 {d["sha256"][:16]}… · {d["uploaded_at"][:16]}</div>',
                        unsafe_allow_html=True)
            for n in d["extraction_notes"] or []:
                alert(n, "high" if "OCR" in n or "verify" in n.lower() else "info")
            c1, c2, c3 = st.columns(3)
            t = c1.selectbox("Document type", DOC_TYPES, index=DOC_TYPES.index(d["doc_type"]) if d["doc_type"] in DOC_TYPES else 0, key=f"t{d['id']}")
            if c1.button("Confirm type", key=f"st{d['id']}"):
                call("PUT", f"/documents/{d['id']}/type", json_body={"doc_type": t})
                st.rerun()
            lbl = c2.text_input("Annexure label (A, B, A-1…)", value=d["annexure_label"] or "", key=f"a{d['id']}")
            if c2.button("Mark as annexure", key=f"ma{d['id']}"):
                if call("PUT", f"/documents/{d['id']}/annexure", json_body={"is_annexure": True, "label": lbl}):
                    st.rerun()
            if d["is_annexure"] and c2.button("Remove annexure", key=f"ra{d['id']}"):
                call("PUT", f"/documents/{d['id']}/annexure", json_body={"is_annexure": False})
                st.rerun()
            if c3.button("👁 View extracted content", key=f"x{d['id']}"):
                txt = call("GET", f"/documents/{d['id']}/text")
                if txt:
                    st.text_area("Extracted text", txt["text"][:30000] or "(no text extracted)", height=260, key=f"tx{d['id']}")
                    for tb in txt["tables"][:4]:
                        st.caption(f"Table: {tb['name']}")
                        st.dataframe(tb["rows"][:60], use_container_width=True)
            if d["doc_type"] == "NOTICE" and c3.button("📨 Parse as notice", key=f"pn{d['id']}", type="primary"):
                if call("POST", f"/documents/{d['id']}/parse-notice"):
                    toast("Notice parsed — continue at step 2, Confirm details")
                    st.rerun()
            if d["doc_type"] != "NOTICE":
                ck = f"del_ask{d['id']}"
                if not st.session_state.get(ck):
                    if c3.button("🗑 Delete this document", key=f"del{d['id']}"):
                        st.session_state[ck] = True
                        st.rerun()
                else:
                    imp = call("GET", f"/documents/{d['id']}/delete-impact", quiet=True) or {}
                    links = imp.get("issue_links", 0) + imp.get("evidence_links", 0)
                    alert(f"Delete “{d['original_name']}”? The file will be removed from this case"
                          + (f", together with its {links} link{'s' if links != 1 else ''} to the notice's queries" if links else "")
                          + (" and its annexure entry" if imp.get("is_annexure") else "")
                          + ". The reply will no longer use it. This cannot be undone.", "high")
                    y, n_ = st.columns(2)
                    if y.button("Yes, delete it", key=f"dely{d['id']}", type="primary"):
                        if call("DELETE", f"/documents/{d['id']}"):
                            st.session_state.pop(ck, None)
                            toast("Document deleted", "🗑")
                            st.rerun()
                    if n_.button("Cancel", key=f"deln{d['id']}"):
                        st.session_state.pop(ck, None)
                        st.rerun()
    q = st.text_input("🔎 Search inside this case's documents", key=f"q{cid}")
    if q:
        st.dataframe(call("GET", f"/cases/{cid}/search", params={"q": q}) or [], use_container_width=True, hide_index=True)


# ---------- Notice ----------
def tab_notice(cid, ns):
    if not ns:
        empty("No notice parsed yet", "Upload the notice in Documents and click 'Parse as notice'.")
        return
    for n in ns:
        p = n["particulars_json"]
        comp = n.get("completeness") or {}
        section(f"Notice #{n['id']}")
        (st.success if n["deadline_verified"] else st.error)(n["deadline_banner"])
        c = st.columns(4)
        kpi(c[0], "Section", p.get("section", {}).get("value"), (p.get("notice_type") or {}).get("value", ""), "blue")
        kpi(c[1], "Assessment year", p.get("assessment_year", {}).get("value"), f"PY {p.get('previous_year', {}).get('value')}", "teal")
        kpi(c[2], "Deadline", n["deadline_value"] if n["deadline_verified"] else p.get("compliance_deadline", {}).get("value"),
            "verified" if n["deadline_verified"] else "NOT VERIFIED", "green" if n["deadline_verified"] else "red")
        kpi(c[3], "Particulars found", f"{comp.get('completeness_pct', '—')}%", f"{len(comp.get('missing', []))} missing", "amber" if comp.get("missing") else "green")
        if comp.get("missing"):
            alert("Missing / unreadable: " + ", ".join(x.replace("_", " ") for x in comp["missing"]) + " — marked NOT PROVIDED (never assumed).", "high")
        if comp.get("needs_verification"):
            alert("Extracted but needs verification: " + ", ".join(x.replace("_", " ") for x in comp["needs_verification"]), "medium")
        for w in comp.get("extraction_warnings", []):
            alert(w, "medium")
        rows = [{"Field": k.replace("_", " ").title(), "Value": v["value"], "Status": v["status"],
                 "Verify?": "YES" if v["needs_verification"] else "", "Source in notice": v["source_snippet"]} for k, v in p.items()]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        law = n.get("applicable_law_json")
        if law:
            st.markdown(f'<div class="nm-card"><h4>Applicable law</h4>{badge(law["substantive_law"], "blue")} {esc(law["basis"])}</div>',
                        unsafe_allow_html=True)
            for f in law["flags"]:
                alert(f, "high" if "TRANSITION" in f else "medium")
        c1, c2 = st.columns(2)
        with c1, st.form(f"vd{n['id']}"):
            st.markdown("**Record verified deadline**")
            dl = st.text_input("Deadline (YYYY-MM-DD)", value=n["deadline_value"] or "")
            src = st.text_input("Verified from", placeholder="e-proceedings portal, viewed 23-11-2026")
            if st.form_submit_button("Save verified deadline", type="primary"):
                if call("POST", f"/notices/{n['id']}/verify-deadline", json_body={"deadline": dl, "source": src}):
                    st.rerun()
        with c2, st.form(f"ef{n['id']}"):
            st.markdown("**Correct an extracted field**")
            f = st.selectbox("Field", sorted(set(p.keys()) - {"compliance_deadline", "documents_requested"}))
            v = st.text_input("Correct value")
            if st.form_submit_button("Save correction"):
                if call("PUT", f"/notices/{n['id']}/field", json_body={"field": f, "value": v}):
                    st.rerun()
        if st.button("🧩 Generate issue-wise analysis from this notice", key=f"gi{n['id']}", type="primary"):
            if call("POST", f"/notices/{n['id']}/issues", params={"replace": "true"}):
                toast("Issues generated — continue at step 3, Issues & evidence")
                st.rerun()


# ---------- Analysis (13 sections) ----------
SECTIONS = [("summary", "1. Notice summary"), ("notice_type_provision", "2. Notice type & provision"), ("period", "3. AY & tax period"),
            ("deadline", "4. Response deadline"), ("issues", "5. Issue-wise analysis"), ("information_requested", "6. Information requested"),
            ("tax_implications", "7. Potential tax implications"), ("evidence_available", "8. Evidence available"),
            ("evidence_gaps", "9. Evidence gaps"), ("risk_assessment", "10. Risk assessment"), ("strategy", "11. Response strategy"),
            ("client_request", "12. Client information request"), ("ca_checklist", "13. CA review checklist")]


def _render_analysis(c: dict):
    st.markdown(f'<div class="nm-banner">{esc(c.get("_label", ""))}</div>', unsafe_allow_html=True)
    if c.get("_ai_notice"):
        alert(c["_ai_notice"], "high")
    if c.get("parse_error"):
        alert(c["parse_error"], "high")
        st.text_area("Raw AI response", c.get("raw_text", ""), height=200)
    st.markdown(" ".join(badge(b) for b in ["ESTABLISHED_FACT", "DOCUMENT_AVAILABLE", "MANAGEMENT_EXPLANATION", "ASSUMPTION",
                                             "UNRESOLVED", "SYSTEM_DERIVED"]) + '<div class="nm-muted">Basis legend</div>', unsafe_allow_html=True)
    for k, title in SECTIONS:
        items = c.get(k) or []
        with st.expander(f"{title}  ({len(items)})", expanded=k in ("summary", "risk_assessment", "deadline")):
            if not items:
                st.markdown('<div class="nm-muted">Nothing recorded — NOT PROVIDED.</div>', unsafe_allow_html=True)
            for x in items:
                if isinstance(x, dict) and "findings" in x:
                    st.markdown(f"**Q{x.get('seq')}** · {badge(x.get('category', ''), 'blue')} {esc(x.get('query', ''))[:300]}", unsafe_allow_html=True)
                    for f in x["findings"]:
                        st.markdown("&nbsp;&nbsp;" + basis_line(f), unsafe_allow_html=True)
                elif isinstance(x, dict) and "level" in x:
                    st.markdown(f"**Q{x.get('seq')}** {badge(x['level'])} score {esc(x.get('score', '—'))} — " +
                                esc("; ".join(x.get("reasons", []))), unsafe_allow_html=True)
                elif isinstance(x, dict) and "strategy" in x:
                    st.markdown(f"**Q{x.get('seq')}** {badge(x.get('note', 'strategy'), 'teal')} **{esc(x.get('strategy'))}** — {esc(x.get('reason'))}",
                                unsafe_allow_html=True)
                elif isinstance(x, dict) and "requests" in x:
                    st.markdown(f"**Q{x.get('seq')}**")
                    for r in x["requests"]:
                        st.markdown(f"- {esc(r)}", unsafe_allow_html=True)
                elif isinstance(x, dict) and "item" in x:
                    st.markdown(("✅ " if x.get("done") else "⬜ ") + esc(x["item"]), unsafe_allow_html=True)
                else:
                    st.markdown(basis_line(x), unsafe_allow_html=True)


def tab_analysis(cid, ns):
    banner()
    lst = call("GET", f"/cases/{cid}/analysis") or []
    c1, c2, c3 = st.columns(3)
    if c1.button("⚙️ Build local analysis (no AI, no network)", type="primary", use_container_width=True):
        with st.spinner("Building analysis from case data…"):
            if call("POST", f"/cases/{cid}/analysis/local", json_body={}):
                toast("Local analysis saved")
                st.rerun()
    prov = call("GET", "/ai/providers", quiet=True) or {}
    plist = list((prov.get("providers") or {}).keys()) or ["anthropic"]
    pv = c2.selectbox("AI provider", plist, index=plist.index(prov.get("default_provider")) if prov.get("default_provider") in plist else 0,
                      key=f"anp{cid}")
    if c3.button("🤖 Prepare AI analysis (preview first)", use_container_width=True):
        res = call("POST", f"/cases/{cid}/analysis/ai/prepare", json_body={"provider": pv})
        if res:
            st.session_state[f"ai_sub_{cid}"] = res["id"]
            toast("AI request prepared — review and approve it under Show more → 🤖 AI requests", "🔒")
    if not lst:
        empty("No analysis yet", "Build the local analysis — it works offline and uses only your case data.")
        return
    pick = st.selectbox("Version", lst, format_func=lambda a: f"v{a['version']} · {a['source']} · {a['status']} · {a['created_at'][:16]}",
                        key=f"anv{cid}")
    a = call("GET", f"/analysis/{pick['id']}")
    if not a:
        return
    st.markdown(f"{badge(a['status'])} {badge(a['source'], 'blue')}" + (f" · CA comment: {esc(a['review_comment'])}" if a.get("review_comment") else ""),
                unsafe_allow_html=True)
    _render_analysis(a["content_json"])
    with st.expander("✏️ Edit this analysis (saves a new version)"):
        txt = st.text_area("Sections as JSON (edit text and basis tags)",
                           json.dumps({k: a["content_json"].get(k, []) for k, _ in SECTIONS}, indent=1, ensure_ascii=False), height=320,
                           key=f"aed{a['id']}")
        if st.button("Save edited version", key=f"aes{a['id']}"):
            try:
                content = json.loads(txt)
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
            else:
                if call("PUT", f"/analysis/{a['id']}", json_body={"content": content}):
                    toast("New version saved")
                    st.rerun()
    if st.session_state.user["role"] == "CA":
        with st.form(f"adec{a['id']}"):
            st.markdown("**CA decision on this analysis**")
            dec = st.radio("Decision", ["ACCEPTED", "REJECTED"], horizontal=True)
            com = st.text_input("Comment (required to reject)")
            if st.form_submit_button("Record decision"):
                if call("POST", f"/analysis/{a['id']}/decision", json_body={"decision": dec, "comment": com}):
                    st.rerun()
    r = call("GET", f"/analysis/{a['id']}/docx", raw=True, quiet=True)
    if r is not None:
        st.download_button("⬇️ Download analysis (DOCX, marked DRAFT)", r.content, file_name=f"analysis_v{a['version']}_DRAFT.docx")


# ---------- Issues & evidence ----------
def issue_block(cid, i, mat, docs, strategies, refs):
    """One issue: notice question, CA factual position, evidence checklist and optional analysis."""
    a = i["analysis_json"]
    merged_history = a.get("merged_issue_history") or []
    if merged_history:
        with st.expander(f"🗂 Earlier issue rows retained ({len(merged_history)})", expanded=False):
            st.caption("These rows were merged into this concern. Their original assessments and evidence notes are kept for CA reference.")
            for old in merged_history:
                st.markdown(f"**Original Q{old.get('seq', '?')} · {esc(old.get('category', ''))}**")
                st.write(old.get("query_text", ""))
                old_analysis = old.get("analysis_json") or {}
                if old_analysis.get("concern_position"):
                    st.caption("Earlier CA position: " + str(old_analysis["concern_position"]))
                for item in old.get("evidence_history") or []:
                    st.caption(f"{item.get('requirement', 'Record')}: {item.get('status', 'unassessed')}"
                               + (f" · {item.get('document_name')}" if item.get("document_name") else ""))
    all_ev = [m for m in mat if m["issue_id"] == i["id"]]
    ev_by_requirement = {}
    for item in all_ev:
        current = ev_by_requirement.get(item["requirement"])
        if current is None or (current["status"] == "NOT_PROVIDED" and item["status"] != "NOT_PROVIDED"):
            ev_by_requirement[item["requirement"]] = item
    ev = list(ev_by_requirement.values())
    st.markdown(f'<div class="nm-card"><div class="nm-muted">The Department asks</div>{esc(i["query_text"])}</div>', unsafe_allow_html=True)
    if st.session_state.user["role"] in ("ADMIN", "CA"):
        with st.expander("✏️ Correct notice question text", expanded=False):
            st.caption("Remove duplicated fragments or unrelated notice footer text. The original notice stays unchanged; this edits only the question NOTICE-MATE uses for analysis and drafting.")
            with st.form(f"correct_issue_query_{i['id']}"):
                corrected_query = st.text_area("Question to use for this issue", value=i["query_text"], height=180)
                if st.form_submit_button("Save corrected question"):
                    if call("PUT", f"/issues/{i['id']}/query", json_body={"query_text": corrected_query}):
                        toast("Question text corrected")
                        st.rerun()
    section("CA assessment (optional)")
    st.caption("Optional. The reply is written from the records whether or not you record a position here.")
    position_labels = {"": "Choose the factual position", "TRUE": "True", "PARTLY_TRUE": "Partially true",
                       "FALSE": "False", "NEED_CLIENT_INFO": "Not enough information yet"}
    st.caption("True = the transaction or fact described in the notice did happen; the reply will explain it using the records you mark as available below. It does not mean the assessee accepts an addition or wrongdoing.")
    current_position = a.get("concern_position") or ""
    if st.session_state.user["role"] in ("ADMIN", "CA"):
        with st.form(f"position{i['id']}"):
            position = st.radio("Based on the facts reviewed, is the concern raised in the notice:",
                                list(position_labels), index=list(position_labels).index(current_position)
                                if current_position in position_labels else 0, horizontal=True,
                                format_func=lambda value: position_labels[value])
            basis = st.text_input("Short basis or record reference (optional)", value=a.get("concern_position_basis") or "")
            if st.form_submit_button("Save CA assessment", type="primary"):
                if not position:
                    st.warning("Choose a factual position first.")
                elif call("PUT", f"/issues/{i['id']}/analysis", json_body={"updates": {
                        "concern_position": position, "concern_position_basis": basis}}):
                    st.rerun()
    else:
        st.info(f"CA assessment: {position_labels.get(current_position, 'Not assessed yet')} · read-only")
    with st.expander("Possible analysis (system-generated; not client facts or a CA conclusion)"):
        c1, c2, c3 = st.columns(3)
        c1.markdown("**Possible assessee position**<br>" + esc(a["perspectives"]["assessee"]), unsafe_allow_html=True)
        c2.markdown("**Department's likely position**<br>" + esc(a["perspectives"]["revenue"]), unsafe_allow_html=True)
        c3.markdown("**Points to test**<br>" + esc(a["perspectives"]["balanced"]), unsafe_allow_html=True)
        st.caption(a["candidate_provisions_note"])
    section("Evidence")
    st.caption("These are suggested record types for this issue. The CA can mark records held outside NOTICE-MATE in the availability checklist below. Uploading files here is optional and is needed only if the CA wants the app to read or reconcile them.")
    if not ev:
        st.markdown('<div class="nm-muted">No evidence requirements mapped yet.</div>', unsafe_allow_html=True)
    for e in ev:
        friendly_status = {"NOT_PROVIDED": "Not received yet", "REQUIRES_VERIFICATION": "File available · CA review needed",
                           "SUFFICIENT": "Available · CA reviewed", "PARTIALLY_SUFFICIENT": "Available · incomplete",
                           "INSUFFICIENT": "Available · does not support this point", "CONTRADICTORY": "Available · discrepancy to review"}.get(e["status"], e["status"])
        st.markdown(f'<div class="nm-row"><div>{esc(e["requirement_label"])}<div class="nm-muted">{esc(e["document_name"] or "no document linked")}'
                    f'{" · establishes: " + esc(e["establishes"]) if e.get("establishes") else ""}'
                    f'{" · does not establish: " + esc(e["does_not_establish"]) if e.get("does_not_establish") else ""}</div></div>'
                    f'<div>{badge(friendly_status)}</div></div>', unsafe_allow_html=True)
    with st.expander("✏️ Assess an evidence item"):
        with st.form(f"ev{i['id']}"):
            st.markdown("Explain what the document does and does not establish.")
            e = st.selectbox("Requirement", ev, format_func=lambda e: f"{e['requirement_label']} [{e['status']}]") if ev else None
            s = st.selectbox("Assessment", EV_STATUSES)
            dids = [None] + [d["id"] for d in docs]
            doc = st.selectbox("Linked document", dids, format_func=lambda x: "—" if x is None else next(d["original_name"] for d in docs if d["id"] == x))
            est = st.text_area("What it establishes")
            nest = st.text_area("What it does NOT establish")
            sup = st.text_input("Supports the explanation? (Yes / Partly / No — why)")
            inc = st.text_input("Inconsistency (required if CONTRADICTORY)")
            if st.form_submit_button("Save assessment") and e:
                if call("PUT", f"/evidence/{e['id']}", json_body={"status": s, "establishes": est, "does_not_establish": nest,
                                                                  "supports_explanation": sup, "inconsistency": inc, "document_id": doc}):
                    st.rerun()
    with st.expander("Optional client explanation, strategy and legal references"):
        sug = call("GET", f"/issues/{i['id']}/suggest-strategy", quiet=True)
        if sug:
            alert(f"Suggested: {strategies.get(sug['strategy'])} — {sug['reason']}", "info")
        with st.form(f"s{i['id']}"):
            expl = st.text_area("Client explanation (only if received; otherwise leave blank)",
                                value=a.get("client_explanation") or "")
            conf = st.checkbox("Client has confirmed this explanation in writing", value=bool(a.get("client_explanation_confirmed")))
            keys = list(strategies)
            stg = st.selectbox("Reply strategy", keys, format_func=lambda k: strategies[k], index=keys.index(i["strategy"]) if i["strategy"] in keys else 0)
            r = st.text_area("Optional strategy note", value=i["strategy_reason"] or "")
            sel = st.multiselect("Legacy registry references (unverified entries stay out of the reply)", [x["ref_key"] for x in refs],
                                 default=[k for k in (a.get("legal_refs_selected") or []) if k in [x["ref_key"] for x in refs]])
            concl = st.text_area("CA conclusion (optional)", value=a.get("ca_conclusion") or "")
            if st.form_submit_button("Save optional details"):
                call("PUT", f"/issues/{i['id']}/analysis", json_body={"updates": {"client_explanation": expl, "client_explanation_confirmed": conf}})
                if r.strip():
                    call("PUT", f"/issues/{i['id']}/strategy", json_body={"strategy": stg, "reason": r})
                call("PUT", f"/issues/{i['id']}/legal-refs", json_body={"ref_keys": sel})
                if concl.strip() and concl != (a.get("ca_conclusion") or ""):
                    call("PUT", f"/issues/{i['id']}/analysis", json_body={"updates": {"ca_conclusion": concl}})
                st.rerun()


def add_issue_form(cid):
    with st.expander("➕ Add issue manually"):
        with st.form("addissue"):
            q = st.text_area("Query text")
            if st.form_submit_button("Add issue"):
                if call("POST", f"/cases/{cid}/issues", json_body={"query_text": q}):
                    st.rerun()
    if st.button("🔄 Re-run evidence auto-mapping"):
        call("POST", f"/cases/{cid}/evidence/automap")
        st.rerun()
    st.caption("Auto-mapping only suggests a document (REQUIRES VERIFICATION). Absence of evidence is never treated as proof of income.")


def tab_issues(cid, iss, mat, docs):
    strategies = call("GET", "/meta/strategies") or {}
    refs = call("GET", "/law/refs") or []
    if not iss:
        empty("No issues yet", "Generate issues from the notice, or add one manually below.")
    for i in iss:
        ev = [m for m in mat if m["issue_id"] == i["id"]]
        n_ok = sum(1 for e in ev if e["status"] == "SUFFICIENT")
        with st.expander(f"Q{i['seq']} · {i['category'].replace('_', ' ').title()} · {inr(i['amount']) if i['amount'] else 'amount NOT PROVIDED'} · "
                         f"evidence {n_ok}/{len(ev)} sufficient"):
            issue_block(cid, i, mat, docs, strategies, refs)
    add_issue_form(cid)


# ---------- Reconciliation ----------
def _recon_result(res: dict, a_lbl: str = "", b_lbl: str = ""):
    if not res:
        return
    if "status" in res:
        st.markdown(f"Status: {badge(res['status'])}", unsafe_allow_html=True)
    nums = {k: v for k, v in res.items() if k.startswith("total") or k in ("difference", "difference_after_duplicates", "duplicate_total",
                                                                             "matched_total", "corrected_book_total", "statement_credits_total",
                                                                             "book_receipts_total", "difference_book_minus_statement")}
    if nums:
        cols = st.columns(min(4, len(nums)))
        for i, (k, v) in enumerate(list(nums.items())[:8]):
            kpi(cols[i % len(cols)], k.replace("_", " "), inr(v), "", "blue")
    for k in ("matched", "rows", "customers", "results", "date_wise_differences"):
        if res.get(k):
            st.caption(k.replace("_", " ").title())
            st.dataframe(res[k], use_container_width=True, hide_index=True)
    for k, v in res.items():
        if (k.startswith("unmatched") or k.startswith("possible_duplicates") or k.startswith("in_") or k == "probable_duplicate_book_postings") and v:
            st.caption(k.replace("_", " ").title())
            st.dataframe(v, use_container_width=True, hide_index=True)
    for f in (res.get("cash_mode_flags") or {}).get("flags", []):
        alert(f"{f['date']} {inr(f['amount'])}: {f['flag']}", "high")
    if res.get("interpretation"):
        alert(res["interpretation"], "info")
    if res.get("note"):
        alert(res["note"], "info")
    for n in res.get("parse_notes", [])[:10]:
        st.caption("Parse note: " + n)


def tab_recon(cid, docs):
    if not docs:
        empty("No documents", "Upload bank statements, books and ledgers (XLSX/CSV give the best results).")
        return
    opts = {f"#{d['id']} {d['original_name']} ({d['doc_type']})": d["id"] for d in docs}
    keys = list(opts)

    def pick(label, k, prefer=None):
        idx = next((i for i, x in enumerate(keys) if prefer and prefer.lower() in x.lower()), 0)
        return opts[st.selectbox(label, keys, index=idx, key=k)]

    kind = st.radio("Reconciliation", ["Bank statement vs bank book", "Bank book vs ledger", "Sales vs bank credits", "AIS/26AS vs books",
                                       "Debtors vs receipts", "Cash book & cash availability", "Cash book vs sales ledger",
                                       "Custom transaction match", "Financial statements tie-out"], horizontal=True, key=f"rk{cid}")
    alert("A match on amount, date or reference shows the records agree. It never proves genuineness or source.", "medium")
    if kind == "Bank statement vs bank book":
        c1, c2 = st.columns(2)
        with c1:
            a = pick("Bank statement", "r1a", "BANK_STATEMENT")
        with c2:
            b = pick("Bank book", "r1b", "BANK_BOOK")
        if st.button("Run", key="r1", type="primary"):
            _recon_result(call("POST", f"/cases/{cid}/recon/bank-vs-book", json_body={"statement_doc": a, "book_doc": b}))
    elif kind == "Bank book vs ledger":
        c1, c2, c3 = st.columns(3)
        with c1:
            a = pick("Bank book", "r2a", "BANK_BOOK")
        with c2:
            b = pick("Ledger (e.g. debtor ledger)", "r2b", "LEDGER")
        with c3:
            side = st.selectbox("Ledger side to compare", ["outflow", "inflow"], help="Debtor/sales ledgers record receipts on the credit (outflow) side")
            win = st.number_input("Date window (days)", 0, 90, 0, key="r2w")
        if st.button("Run", key="r2", type="primary"):
            _recon_result(call("POST", f"/cases/{cid}/recon/bank-book-vs-ledger", json_body={"bank_book_doc": a, "ledger_doc": b,
                                                                                             "ledger_side": side, "date_window_days": win}))
    elif kind == "Sales vs bank credits":
        c1, c2, c3 = st.columns(3)
        with c1:
            a = pick("Sales ledger", "r3a", "SALES_LEDGER")
        with c2:
            b = pick("Bank statement", "r3b", "BANK_STATEMENT")
        with c3:
            win = st.number_input("Date window (days)", 0, 90, 7, key="r3w")
            flt = st.text_input("Filter sales (regex)", value="", key="r3f", help="e.g. 'customer' to exclude cash sales")
            party = st.checkbox("Require party-name overlap", key="r3p")
        if st.button("Run", key="r3", type="primary"):
            _recon_result(call("POST", f"/cases/{cid}/recon/sales-vs-bank", json_body={"sales_doc": a, "statement_doc": b, "date_window_days": win,
                                                                                       "filter_sales": flt or None, "require_party": party}))
    elif kind == "AIS/26AS vs books":
        c1, c2 = st.columns(2)
        with c1:
            a = pick("AIS / 26AS extract", "r4a", "AIS")
        with c2:
            b = pick("Books (e.g. sales ledger)", "r4b", "SALES_LEDGER")
            side = st.selectbox("Books side", ["outflow", "inflow"], key="r4s", help="Sales are on the credit (outflow) side of a sales ledger")
        if st.button("Run", key="r4", type="primary"):
            _recon_result(call("POST", f"/cases/{cid}/recon/ais-vs-books", json_body={"ais_doc": a, "books_doc": b, "books_side": side}))
    elif kind == "Debtors vs receipts":
        c1, c2 = st.columns(2)
        with c1:
            a = pick("Debtor ledger / schedule", "r5a", "DEBTOR")
        with c2:
            rk = ["(none)"] + keys
            rb = st.selectbox("Receipts record (cash book / bank book)", rk, key="r5b")
        if st.button("Run", key="r5", type="primary"):
            _recon_result(call("POST", f"/cases/{cid}/recon/debtors-vs-receipts",
                               json_body={"debtor_doc": a, "receipts_doc": None if rb == "(none)" else opts[rb]}))
    elif kind == "Cash book & cash availability":
        c1, c2, c3 = st.columns(3)
        with c1:
            cb = pick("Cash book", "r6a", "CASH_BOOK")
        with c2:
            bs = pick("Bank statement", "r6b", "BANK_STATEMENT")
        with c3:
            ob = st.number_input("Opening cash balance (₹)", min_value=0.0, value=0.0)
        mp = st.text_area("Optional management source mapping CSV: deposit_date,receipt_date,amount,description", key="r6m")
        if st.button("Test chronology & availability", key="r6", type="primary"):
            rows = None
            if mp.strip():
                rows = []
                for line in mp.strip().splitlines():
                    p = [x.strip() for x in line.split(",")]
                    if len(p) >= 3 and p[0].lower() != "deposit_date":
                        try:
                            rows.append({"deposit_date": p[0], "receipt_date": p[1], "amount": float(p[2].replace("₹", "").replace(",", "")),
                                         "description": ",".join(p[3:])})
                        except ValueError:
                            st.error(f"Bad mapping line: {line}")
            _recon_result(call("POST", f"/cases/{cid}/recon/cash-chronology",
                               json_body={"cash_book_doc": cb, "statement_doc": bs, "opening_balance": ob, "source_mapping": rows}))
    elif kind == "Cash book vs sales ledger":
        c1, c2 = st.columns(2)
        with c1:
            a = pick("Cash book", "r7a", "CASH_BOOK")
            fa = st.text_input("Filter (regex)", "cash sale", key="r7fa")
        with c2:
            b = pick("Sales ledger", "r7b", "SALES_LEDGER")
            fb = st.text_input("Filter (regex)", "cash sale", key="r7fb")
        if st.button("Compare", key="r7", type="primary"):
            _recon_result(call("POST", f"/cases/{cid}/recon/ledger-compare", json_body={"doc_a": a, "doc_b": b, "label_a": "cash_book",
                                                                                        "label_b": "sales_ledger", "filter_a": fa or None, "filter_b": fb or None}))
    elif kind == "Custom transaction match":
        c1, c2 = st.columns(2)
        with c1:
            a = pick("Record A", "r8a")
            pa = st.selectbox("A is", ["books", "bank_statement"], key="r8pa")
            sa = st.selectbox("A side", ["inflow", "outflow"], key="r8sa")
            fa = st.text_input("Filter A (regex)", key="r8fa")
        with c2:
            b = pick("Record B", "r8b")
            pb = st.selectbox("B is", ["books", "bank_statement"], key="r8pb")
            sb = st.selectbox("B side", ["inflow", "outflow"], key="r8sb")
            fb = st.text_input("Filter B (regex)", key="r8fb")
        win = st.slider("Date window (days)", 0, 30, 0)
        party = st.checkbox("Require party-name overlap", key="r8p")
        if st.button("Match", key="r8", type="primary"):
            _recon_result(call("POST", f"/cases/{cid}/recon/match", json_body={"doc_a": a, "doc_b": b, "perspective_a": pa, "perspective_b": pb,
                                                                               "side_a": sa, "side_b": sb, "filter_a": fa or None, "filter_b": fb or None,
                                                                               "date_window_days": win, "require_party": party}))
    else:
        fs = st.text_area("label, per financial statements, per books, per return (one per line)", key="r9")
        if st.button("Tie out", key="r9b", type="primary"):
            figs = []
            for line in fs.strip().splitlines():
                p = [x.strip() for x in line.split(",")]
                if len(p) >= 3:
                    figs.append({"label": p[0], "per_financial_statements": p[1], "per_books": p[2], "per_return": p[3] if len(p) > 3 else None})
            res = call("POST", f"/cases/{cid}/recon/fs-tie-out", json_body={"figures": figs})
            if res:
                st.dataframe(res["rows"], use_container_width=True, hide_index=True)
                st.caption(res["note"])
    with st.expander("🕘 Previous reconciliation runs"):
        runs = call("GET", f"/cases/{cid}/recon") or []
        for r in runs[:15]:
            st.markdown(f"**#{r['id']} {r['recon_type']}** · {r['created_at'][:16]} · {badge(r['result_json'].get('status', '—'))}", unsafe_allow_html=True)


# ---------- Lenders / partners / advances ----------
def tab_parties(cid, iss):
    banner("Documents such as PAN, ITR, confirmation and a bank transfer support identity and capacity — they are not conclusive proof of genuineness.")
    meta = call("GET", "/meta/party-checklists") or {}
    data = call("GET", f"/cases/{cid}/parties") or {"totals": {}, "records": []}
    cols = st.columns(3)
    for i, t in enumerate(["LENDER", "PARTNER_CAPITAL", "CUSTOMER_ADVANCE"]):
        x = data["totals"].get(t, {"count": 0, "amount": 0, "with_gaps": 0})
        kpi(cols[i], t.replace("_", " ").title(), inr(x["amount"]), f"{x['count']} record(s) · {x['with_gaps']} with gaps", "blue")
    for r in data["records"]:
        an = r["analysis"]
        with st.expander(f"{r['record_type'].replace('_', ' ').title()} · {r['party_name']} · {inr(r['amount'])} · {r.get('txn_date') or 'date NOT PROVIDED'} · {r.get('mode') or ''}"):
            cols = st.columns(len(an["aspects"]) or 1)
            for i, (k, v) in enumerate(an["aspects"].items()):
                cols[i].markdown(f"**{k.replace('_', ' ').title()}**<br>{badge(v['status'])}", unsafe_allow_html=True)
                for it in v["items"]:
                    cols[i].markdown(f"<span class='nm-muted'>{esc(it['label'])}</span> {badge(it['status'])}", unsafe_allow_html=True)
            for f in an["flags"]:
                alert(f, "high")
            if an["evidence_gaps"]:
                st.markdown("**Evidence gaps:** " + "; ".join(an["evidence_gaps"]))
            st.caption(an["note"])
            if r.get("observations"):
                st.markdown(f"Observations: {esc(r['observations'])}", unsafe_allow_html=True)
            if st.button("Delete record", key=f"pd{r['id']}"):
                call("DELETE", f"/parties/{r['id']}")
                st.rerun()
    with st.expander("➕ Add lender / partner capital / customer advance", expanded=not data["records"]):
        rt = st.selectbox("Record type", ["LENDER", "PARTNER_CAPITAL", "CUSTOMER_ADVANCE"], key="prt")
        with st.form("party"):
            c1, c2, c3, c4 = st.columns(4)
            name = c1.text_input("Party name")
            amt = c2.number_input("Amount (₹)", min_value=0.0, step=1000.0)
            dt = c3.text_input("Date (YYYY-MM-DD)")
            mode = c4.selectbox("Mode", ["BANK", "CASH", "CHEQUE", "ADJUSTMENT", "OTHER"])
            ev = {}
            st.markdown("**Evidence status**")
            ec = st.columns(2)
            for i, (k, lbl) in enumerate((meta.get(rt) or {}).items()):
                ev[k] = ec[i % 2].selectbox(lbl, ["NOT_PROVIDED", "AVAILABLE", "REQUIRES_VERIFICATION", "NOT_APPLICABLE"], key=f"pe{rt}{k}")
            lcd_amt = st.number_input("Cash deposited in creditor's account shortly before the transfer (₹, 0 if none / not known)", min_value=0.0)
            lcd_dt = st.text_input("Date of that cash deposit (YYYY-MM-DD)")
            lcd_ex = st.checkbox("Creditor has explained the source of that deposit")
            obs = st.text_area("Observations")
            issue = st.selectbox("Linked issue", [None] + [i["id"] for i in iss], format_func=lambda x: "—" if x is None else f"Q{next(i['seq'] for i in iss if i['id'] == x)}")
            if st.form_submit_button("Save record", type="primary"):
                if lcd_amt > 0:
                    ev["lender_cash_deposit_before"] = {"amount": lcd_amt, "date": lcd_dt or None, "explained": lcd_ex}
                if call("POST", f"/cases/{cid}/parties", json_body={"record_type": rt, "party_name": name, "amount": amt, "txn_date": dt or None,
                                                                    "mode": mode, "evidence": ev, "observations": obs, "issue_id": issue}):
                    st.rerun()


# ---------- Tax ----------
def tab_tax(cid, case):
    banner("Illustrative estimate only — not a tax demand or final liability. Rates, characterisation and law require CA verification.")
    with st.form("tax"):
        c1, c2, c3 = st.columns(3)
        ay = c1.text_input("Assessment Year", value=case.get("assessment_year") or "2026-27")
        cats = ["FIRM", "LLP", "INDIVIDUAL", "HUF", "COMPANY_DOMESTIC"]
        cat = c2.selectbox("Assessee category", cats, index=cats.index(case["assessee_category"]) if case["assessee_category"] in cats else 0)
        ri = c3.text_input("Returned income (₹) — blank if NOT PROVIDED")
        adds = st.text_area("Proposed additions: label, amount (one per line)", placeholder="Cash-sales difference, 150000")
        if st.form_submit_button("Simulate", type="primary"):
            al = []
            for line in adds.strip().splitlines():
                p = [x.strip() for x in line.rsplit(",", 1)]
                if len(p) == 2:
                    try:
                        al.append({"label": p[0], "amount": float(p[1].replace(",", "").replace("₹", ""))})
                    except ValueError:
                        st.error(f"Bad amount in: {line}")
            try:
                ri_v = float(ri.replace(",", "")) if ri.strip() else None
            except ValueError:
                ri_v = None
                st.error("Returned income must be a number.")
            res = call("POST", f"/cases/{cid}/tax/simulate", json_body={"assessment_year": ay, "assessee_category": cat, "returned_income": ri_v, "additions": al})
            if res:
                st.session_state[f"tax_{cid}"] = res
    res = st.session_state.get(f"tax_{cid}")
    if res:
        alert(res["label"], "high")
        cols = st.columns(len(res["scenarios"]))
        for i, s in enumerate(res["scenarios"]):
            kpi(cols[i], f"Scenario {s['key']}", inr(s["incremental_tax"]), s["title"], ["green", "amber", "red"][i % 3])
        for s in res["scenarios"]:
            with st.expander(f"Workings — Scenario {s['key']}: {s['title']}"):
                st.caption(s["provision"])
                st.code("\n".join(s["workings"]))
        st.markdown("**Indicative penalty exposure (separate proceedings)**")
        pe = res["penalty_exposure_indicative"]
        st.dataframe([{"Item": k.replace("_", " "), "Amount": inr(v) if isinstance(v, (int, float)) else v} for k, v in pe.items()],
                     use_container_width=True, hide_index=True)
        c1, c2 = st.columns(2)
        c1.markdown("**Assumptions**\n" + "\n".join(f"- {x}" for x in res["assumptions"]))
        c2.markdown("**Exclusions (not computed)**\n" + "\n".join(f"- {x}" for x in res["exclusions"]))
    section("Applicable-law check")
    with st.form("law"):
        c1, c2, c3 = st.columns(3)
        y = c1.text_input("Year (e.g. 2026-27)", value=case.get("assessment_year") or "")
        lt = c2.selectbox("Year type", ["AY", "TAX_YEAR"])
        nd = c3.text_input("Notice date (YYYY-MM-DD, optional)")
        if st.form_submit_button("Determine"):
            r = call("POST", "/law/applicable", json_body={"year_label": y, "label_type": lt, "notice_date": nd or None})
            if r:
                st.markdown(f"{badge(r['substantive_law'], 'blue')} {esc(r['basis'])}", unsafe_allow_html=True)
                for f in r["flags"]:
                    alert(f, "high" if "TRANSITION" in f else "medium")


# ---------- Research ----------
def tab_research(cid, iss):
    stt = call("GET", "/research/status", quiet=True) or {}
    alert(stt.get("disclosure", "Live legal research status unknown."), "high")
    with st.form("rq"):
        q = st.text_area("Research question", placeholder="e.g. Which Act governs AY 2026-27 scrutiny and how are cash credits examined?")
        iid = st.selectbox("Link to issue", [None] + [i["id"] for i in iss], format_func=lambda x: "—" if x is None else f"Q{next(i['seq'] for i in iss if i['id'] == x)}")
        if st.form_submit_button("Create research note", type="primary"):
            if call("POST", f"/cases/{cid}/research", json_body={"question": q, "issue_id": iid}):
                st.rerun()
    notes = call("GET", f"/cases/{cid}/research") or []
    if not notes:
        empty("No research notes", "A note gathers registry provisions, judgments you have entered, and practical points — kept separate.")
    prov = call("GET", "/ai/providers", quiet=True) or {}
    plist = list((prov.get("providers") or {}).keys()) or ["anthropic"]
    for n in notes:
        c = n["content_json"]
        with st.expander(f"#{n['id']} · {n['question'][:90]} · {n['status']}"):
            if c.get("applicable_law"):
                st.markdown(f"**Applicable law:** {badge(c['applicable_law']['substantive_law'], 'blue')} {esc(c['applicable_law']['basis'])}", unsafe_allow_html=True)
            section("A. Statutory law (registry)")
            if not c["statutory"]:
                st.markdown('<div class="nm-muted">No matching registry provisions.</div>', unsafe_allow_html=True)
            for s in c["statutory"]:
                st.markdown(f"{badge(s['status'])} {badge(s['ref_type'], 'blue')} **{esc(s['provision'])}**, {esc(s['act'])} — {esc(s['title'])}"
                            f"<div class='nm-muted'>Effective from: {esc(s['effective_from'])} · {esc(s.get('applies_to') or '')} · Source: {esc(s['source_url'])}</div>"
                            f"<div>{esc(s['summary'])}</div>", unsafe_allow_html=True)
            section("B. Judicial interpretation (registry only)")
            st.caption(c.get("judicial_note", ""))
            for j in c["judicial"]:
                st.markdown(f"{badge(j['status'])} **{esc(j['title'])}** ({esc(j['provision'])}) · {esc(j['source_url'])}", unsafe_allow_html=True)
            section("C. Practical suggestions (not law)")
            for p in c["practical"]:
                st.markdown(f"- {esc(p['text'])}")
            if c.get("ai_propositions"):
                section("D. AI-suggested propositions — UNVERIFIED until a CA verifies each")
                for d in c.get("disclosures", []):
                    alert(d, "high")
                for idx, p in enumerate(c["ai_propositions"]):
                    txt = p.get("proposition") or p.get("suggestion") or ""
                    extra = " · ".join(f"{k}: {p[k]}" for k in ("act", "provision", "case_name", "citation", "court", "year", "effective_from", "source_url", "confidence") if p.get(k))
                    st.markdown(f"{badge(p['status'])} {badge(p['kind'], 'grey')} {esc(txt)}<div class='nm-muted'>{esc(extra)}</div>", unsafe_allow_html=True)
                    if st.session_state.user["role"] == "CA":
                        cc1, cc2, cc3, cc4 = st.columns([2, 1, 1, 1])
                        url = cc1.text_input("Source checked (URL)", key=f"pu{n['id']}_{idx}")
                        if cc2.button("Verify", key=f"pv{n['id']}_{idx}"):
                            if call("PUT", f"/research/{n['id']}/propositions/{idx}", json_body={"status": "VERIFIED", "source_url": url}):
                                st.rerun()
                        if cc3.button("Discard", key=f"px{n['id']}_{idx}"):
                            call("PUT", f"/research/{n['id']}/propositions/{idx}", json_body={"status": "DISCARDED"})
                            st.rerun()
                        rk = cc4.text_input("Registry key", key=f"pk{n['id']}_{idx}", placeholder="CASE_ABC_2020")
                        if rk and cc4.button("Add to registry", key=f"pp{n['id']}_{idx}"):
                            if call("POST", f"/research/{n['id']}/propositions/{idx}/promote", json_body={"ref_key": rk}):
                                toast("Added to registry as REQUIRES VERIFICATION")
                for s in c.get("provider_sources", []):
                    st.markdown(f"- {badge('UNVERIFIED')} [{esc(s['title'] or s['url'])}]({s['url']})", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            pv = c1.selectbox("Provider", plist, key=f"rp{n['id']}")
            live = c2.checkbox("Request live web search (if enabled)", key=f"rl{n['id']}")
            if c3.button("🤖 Prepare AI research (preview first)", key=f"ra{n['id']}"):
                res = call("POST", f"/research/{n['id']}/ai/prepare", json_body={"provider": pv, "live": live})
                if res:
                    st.session_state[f"ai_sub_{cid}"] = res["id"]
                    if res.get("warning"):
                        alert(res["warning"], "high")
                    toast("Prepared — approve it under Show more → 🤖 AI requests", "🔒")


# ---------- Client request ----------
def tab_client_request(cid):
    st.caption("Create one initial request covering the records needed across all notice issues. When the client replies, the CA can mark what is available; uploading files into NOTICE-MATE is optional and only needed for in-app reading or reconciliation.")
    inc = st.checkbox("Also ask the client to confirm items marked REQUIRES VERIFICATION")
    if st.button("📋 Generate client information request", type="primary"):
        txt = call("POST", f"/cases/{cid}/client-request/text", params={"include_requires_verification": str(inc).lower()})
        if txt:
            st.session_state[f"cr_{cid}"] = txt
    txt = st.session_state.get(f"cr_{cid}")
    if txt:
        st.text_area("Request (edit, then send through your secure client channel)", txt, height=420)
        st.download_button("⬇️ Download .txt", txt, file_name=f"client_request_case{cid}.txt")
    else:
        empty("No request generated yet", "Requests are issue-wise and skip documents already on file.")


# ---------- Draft ----------
def tab_draft(cid):
    banner()
    st.markdown("The reply is written query by query from the notice and the matched records, in the assessee's voice. Anything "
                "that needs your decision is marked **[CA REVIEW: …]** at the exact sentence; requested records that were not "
                "uploaded are mentioned in one line, and the rest of the reply stays complete.")
    o1, o2 = st.columns(2)
    inc_refs = o1.checkbox("Name the records relied on under each query", value=True, key=f"draft_refs_{cid}",
                           help="Adds a short line such as 'Records relied on for this query: …'. Untick to omit document findings.")
    inc_legal = o2.checkbox("Insert suggested legal points for my review", value=False, key=f"draft_legal_{cid}",
                            help="Adds a [CA REVIEW] line listing the provisions to consider. Only CA-verified legal propositions "
                                 "are written into the reply as submissions.")
    recon_runs = call("GET", f"/cases/{cid}/recon") or []
    reflect_reconciliation = st.checkbox("Include selected reconciliation findings in the reply (optional)", value=False,
                                         help="Leave off to keep reconciliation as an internal CA check. A selected result will be described cautiously in the reply.",
                                         key=f"draft_reflect_recon_{cid}")
    selected_recon_ids = []
    if reflect_reconciliation:
        if recon_runs:
            chosen = st.multiselect("Reconciliation runs to reflect", recon_runs,
                                    format_func=lambda r: f"#{r['id']} · {r['recon_type'].replace('_', ' ').title()} · {r['created_at'][:10]} · {r['result_json'].get('status', 'review')}",
                                    key=f"draft_recon_runs_{cid}")
            selected_recon_ids = [r["id"] for r in chosen]
            st.caption("Only the selected results will enter the reply. Reconciliation demonstrates consistency for the items checked; it does not by itself prove source or genuineness.")
        else:
            st.info("No reconciliation runs are available. You can continue without including analysis.")
    stt = call("GET", "/ai/drafting-status", quiet=True) or {"best": None, "message": "", "local": {}, "cloud_ready": []}
    engines = {}
    if stt.get("local", {}).get("enabled") and stt.get("local", {}).get("ready"):
        engines["local"] = f"AI on this computer ({stt['local']['model']}) — nothing leaves this computer"
    for pv in stt.get("cloud_ready") or []:
        engines[pv] = f"Cloud AI ({pv}) — redacted, shown to you, sent only after your approval; may be charged by the provider"
    engines["none"] = "Without AI — from the records only"
    alert(("✍️ " if stt.get("best") else "⚠️ ") + (stt.get("message") or ""), "info" if stt.get("best") == "local" else
          ("medium" if stt.get("best") else "high"))
    keys = list(engines)
    engine = st.radio("How should the issue paragraphs be written?", keys, format_func=lambda k: engines[k],
                      index=keys.index(stt["best"]) if stt.get("best") in keys else len(keys) - 1, key=f"engine_{cid}")
    body = {"reflect_reconciliation": reflect_reconciliation, "reconciliation_run_ids": selected_recon_ids,
            "include_record_references": inc_refs, "include_legal_suggestions": inc_legal}
    c1, c2 = st.columns([1, 3])
    if c1.button("✍️ Write the reply", type="primary"):
        if engine == "local":
            iss = call("GET", f"/cases/{cid}/issues") or []
            ids, failed = [], []
            bar = st.progress(0.0, text="Starting…")
            for n, i in enumerate(iss, 1):
                bar.progress((n - 1) / max(len(iss), 1), text=f"AI is writing query {i['seq']} of {len(iss)} on this computer…")
                row = call("POST", f"/issues/{i['id']}/ai-draft", timeout=900, quiet=True)
                if row:
                    ids.append(row["id"])
                else:
                    failed.append(i["seq"])
            bar.progress(1.0, text="Assembling the reply…")
            ok = call("POST", f"/cases/{cid}/drafts", json_body={**body, "ai_draft_ids": ids})
            bar.empty()
            if failed:
                st.session_state[f"draft_warn_{cid}"] = (
                    f"The AI could not write quer{'y' if len(failed) == 1 else 'ies'} {', '.join(map(str, failed))}; "
                    "those were written from the records without AI. Check that LM Studio/Ollama is still running, then write again.")
            if ok:
                toast(f"New draft version — {len(ids)} of {len(iss)} queries written with AI", "✍️")
                st.rerun()
        elif engine == "none":
            with st.spinner("Writing the point-wise reply from the notice and the records…"):
                ok = call("POST", f"/cases/{cid}/drafts", json_body=body)
            if ok:
                toast("New draft version written (without AI)")
                st.rerun()
        else:
            sub = call("POST", f"/cases/{cid}/ai-draft/cloud", json_body={"provider": engine})
            if sub:
                st.session_state[f"cloud_sub_{cid}"] = sub["id"]
                st.rerun()
    warn = st.session_state.pop(f"draft_warn_{cid}", None)
    if warn:
        alert(warn, "high")
    sid = st.session_state.get(f"cloud_sub_{cid}")
    if sid:
        sub = call("GET", f"/ai/submissions/{sid}", quiet=True)
        if sub and sub["status"] == "PENDING_APPROVAL":
            section("Approve sending to the cloud provider")
            alert(f"This redacted text will be sent to {sub['provider']} at {sub['destination']} (model {sub['model']}). "
                  "Names, PANs and other identifiers are replaced before sending and restored on this computer afterwards. "
                  "The provider may charge for this request. " + (sub.get("disclosure") or ""), "medium")
            with st.expander(f"See exactly what will be sent ({sub['payload_chars']:,} characters)"):
                st.json(sub["exact_payload_preview"])
            ok = st.checkbox("I have reviewed this redacted text and approve sending it.", key=f"cloud_ok_{sid}")
            a1, a2 = st.columns(2)
            if a1.button("🚀 Approve and write the reply", type="primary", disabled=not ok, key=f"cloud_go_{sid}"):
                with st.spinner("Waiting for the provider…"):
                    res = call("POST", f"/ai/submissions/{sid}/send", json_body={"payload_hash": sub["payload_hash"], "confirm": True},
                               timeout=600)
                st.session_state.pop(f"cloud_sub_{cid}", None)
                if res and res.get("drafting_result"):
                    for prob in res["drafting_result"].get("problems") or []:
                        st.session_state[f"draft_warn_{cid}"] = prob
                    toast("New draft version written with cloud AI", "✍️")
                elif res:
                    st.session_state[f"draft_warn_{cid}"] = ("The provider's answer could not be used, so the reply was not changed: "
                                                            + (res.get("drafting_error") or "unknown problem"))
                st.rerun()
            if a2.button("Cancel", key=f"cloud_no_{sid}"):
                call("POST", f"/ai/submissions/{sid}/cancel")
                st.session_state.pop(f"cloud_sub_{cid}", None)
                st.rerun()
        elif sub and sub["status"] == "BLOCKED":
            alert("Nothing was sent: " + (sub.get("block_reason") or "blocked"), "high")
            st.session_state.pop(f"cloud_sub_{cid}", None)
    drafts = call("GET", f"/cases/{cid}/drafts") or []
    if not drafts:
        empty("No draft yet", "Click ‘Write the reply’. You can write it again at any time after adding or removing documents.")
        return
    d = call("GET", f"/drafts/{drafts[0]['id']}")
    if not d:
        return
    c2.markdown(f"Version **{d['version']}** · hash `{d['content_hash'][:16]}…` · {d['created_at'][:16]}")
    if st.session_state.user["role"] in ("ADMIN", "CA"):
        section("Download an editable Word copy")
        st.caption("This is a working draft with a draft banner. Download it, edit it in Word on this computer, then review the final text and attachments before filing.")
        default_name = f"NOTICE-MATE_reply_case{cid}_v{d['version']}"
        filename = st.text_input("Word file name", value=default_name, key=f"draft_docx_name_{d['id']}")
        clean_filename = re.sub(r'[<>:\"/\\|?*]', "_", filename).strip(" .")[:120] or default_name
        if not clean_filename.lower().endswith(".docx"):
            clean_filename += ".docx"
        ready_key = f"draft_docx_ready_{d['id']}"
        if st.button("Prepare Word download", key=f"prepare_working_docx_{d['id']}"):
            response = call("GET", f"/drafts/{d['id']}/working-docx", params={"filename": clean_filename}, raw=True)
            if response:
                st.session_state[ready_key] = response.content
        if st.session_state.get(ready_key):
            st.download_button("⬇️ Download editable Word draft", st.session_state[ready_key],
                               file_name=clean_filename,
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               key=f"download_working_docx_{d['id']}")
        st.caption("Choose the save folder in Edge’s download prompt. If Edge downloads straight to Downloads, turn on ‘Ask where to save each file before downloading’ in its Downloads settings.")
    c = d["content_json"]
    rps = (c.get("_meta") or {}).get("review_points") or []
    if d["unresolved_placeholders"] or rps:
        section("Points for your final review")
        if d["unresolved_placeholders"]:
            st.caption(f"{len(d['unresolved_placeholders'])} marker(s) in the text must be resolved (edit the sentence or delete the "
                       "marker) before approval:")
            for ph in d["unresolved_placeholders"]:
                st.markdown(f"- {esc(ph[:300])}")
        other = [r for r in rps if f"[CA REVIEW: {r['point']}]" not in d["unresolved_placeholders"]]
        if other:
            st.caption("Also worth checking (not in the reply text):")
            for r in other:
                st.markdown(f"- **{esc(r['issue'][:60])}** — {esc(r['point'][:300])}")
    with st.expander("👁 Read the reply", expanded=False):
        st.text(call("GET", f"/drafts/{d['id']}/preview") or "")
    dinfo = (c.get("_meta") or {}).get("drafting") or {}
    by = dinfo.get("by_issue") or {}
    words = {"AI": "written with AI, checked against the records", "RECORDS": "written from the records without AI",
             "BASIC": "basic template — record extracts listed; needs your wording",
             "TEMPLATE": "basic template — no uploaded record relates to it; not complete"}
    section("How this version was written")
    st.markdown(esc(dinfo.get("label") or "Written from your records without AI."))
    for b in c["issues"]:
        k = b.get("drafted_by") or by.get(str(b["issue_id"]), "")
        st.markdown(f"- **{esc(b['heading'][:90])}** — {badge(words.get(k, k or 'edited'), 'green' if k in ('AI', 'RECORDS') else 'amber')}",
                    unsafe_allow_html=True)
    if dinfo.get("basic_template_queries"):
        alert("Queries " + ", ".join(map(str, dinfo["basic_template_queries"])) + " are a basic template, not a complete reply. "
              "Add the records or your explanation for them, or write those paragraphs yourself.", "high")
    ai_blocks = [b for b in c["issues"] if b.get("ai")]
    if ai_blocks:
        with st.expander("🔗 Where each AI-written statement comes from"):
            for b in ai_blocks:
                st.markdown(f"**{esc(b['heading'][:120])}**")
                for n, (ptxt, srcs) in enumerate(zip(b["paragraphs"], b["ai"]["sources"] + [[]] * len(b["paragraphs"])), 1):
                    st.markdown(f"<div class='nm-quote'>¶{n} {esc(ptxt[:500])}</div>", unsafe_allow_html=True)
                    if not srcs:
                        st.caption("No record cited for this paragraph — it relies on the notice, your entries or availability marks.")
                    for sref in srcs:
                        st.caption(f"{sref['ref']} · {sref['file']}{' · ' + sref['location'] if sref.get('location') else ''}: "
                                   f"{sref['text'][:240]}")
                for chk in b["ai"].get("checks") or []:
                    alert(chk["message"], "medium")
    section("Fact basis by issue (internal — not exported)")
    for b in c["issues"]:
        bm = b.get("basis_map") or []
        st.markdown(f"**{esc(b['heading'][:140])}**", unsafe_allow_html=True)
        if not bm:
            st.markdown('<div class="nm-muted">No document-supported facts or client explanations recorded yet.</div>', unsafe_allow_html=True)
        for x in bm:
            st.markdown(f"&nbsp;&nbsp;{badge(x['basis'])} {esc(x['statement'])}" + (f" <span class='nm-muted'>({esc(x.get('source', ''))}"
                        + (f", Annexure {esc(x['annexure'])}" if x.get("annexure") else "") + ")</span>" if x.get("source") else ""), unsafe_allow_html=True)
        for nnote in b["internal_notes"]:
            st.caption("• " + nnote)
        with st.expander(f"🔎 CA reference panel · source context for Q{b['heading'].split(':', 1)[0].replace('Query No. ', '')}"):
            trace = call("GET", f"/issues/{b['issue_id']}/trace") or {}
            st.markdown("**Notice question**")
            st.markdown(f"> {trace.get('issue', {}).get('query_text', b['heading'])}")
            notice_doc = trace.get("notice_document") or {}
            if notice_doc.get("id"):
                with st.expander(f"Read extracted notice · {notice_doc.get('original_name', 'notice')}"):
                    notice_text = call("GET", f"/documents/{notice_doc['id']}/text") or {}
                    st.text(notice_text.get("text") or "No extracted text is available.")
            tr_analysis = trace.get("analysis") or {}
            held = set(tr_analysis.get("available_records") or [])
            st.markdown("**Records CA marked available**")
            rows = trace.get("evidence") or []
            held_labels = [e.get("requirement_label", e.get("requirement", "")) for e in rows if e.get("requirement") in held]
            st.write("; ".join(held_labels) if held_labels else "None marked")
            if c.get("reconciliation"):
                st.markdown("**Reconciliation reflected in this draft**")
                for item in c["reconciliation"]:
                    st.write(item["paragraph"])
            st.markdown("**Legal propositions and sources**")
            propositions = trace.get("propositions") or []
            if not propositions:
                st.caption("No legal proposition is linked to this issue yet.")
            for prop in propositions:
                st.markdown(f"{badge(prop.get('effective_status', 'UNVERIFIED'))} **{esc(prop.get('text', ''))}**", unsafe_allow_html=True)
                for source in prop.get("sources", []):
                    st.markdown(f"**{esc(source.get('title', 'Source'))}** · {esc(source.get('citation') or '')} · {badge(source.get('effective_status', 'UNVERIFIED'))}", unsafe_allow_html=True)
                    if source.get("excerpt"):
                        st.markdown(f"> {esc(source['excerpt'])}")
                    if source.get("applicability_note"):
                        st.caption("Applicability: " + source["applicability_note"])
                    official_url = str(source.get("official_url") or "")
                    if official_url.startswith("https://"):
                        st.link_button("Open source document", official_url, key=f"draft_source_{b['issue_id']}_{source.get('id', source.get('title', 'source'))}")
    if st.session_state.user["role"] in ("ADMIN", "CA"):
        section("Edit the reply (every save creates a new version)")
        with st.form("edit"):
            upd = {}
            for k in ("subject", "reference", "background", "preliminary", "prayer"):
                upd[k] = st.text_area(k.title(), c[k], key=f"e{k}{d['id']}")
            iss = {}
            for b in c["issues"]:
                txt = st.text_area(b["heading"][:150], "\n\n".join(b["paragraphs"]), key=f"ei{b['issue_id']}{d['id']}")
                iss[str(b["issue_id"])] = [x.strip() for x in txt.split("\n\n") if x.strip()]
            legal = st.text_area("Legal submissions (one paragraph per blank line; cite only VERIFIED references)", "\n\n".join(c.get("legal", [])))
            sig = c["signature"]
            s1, s2, s3, s4 = st.columns(4)
            sg = {"name": s1.text_input("Signatory", sig["name"]), "designation": s2.text_input("Designation", sig["designation"]),
                  "date": s3.text_input("Date", sig["date"]), "place": s4.text_input("Place", sig["place"])}
            to = st.text_input("To (authority)", c["to_from"]["to"])
            if st.form_submit_button("💾 Save as new version", type="primary"):
                upd.update({"issues": iss, "legal": [x.strip() for x in legal.split("\n\n") if x.strip()], "signature": sg, "to_from": {"to": to}})
                if call("PUT", f"/drafts/{d['id']}", json_body={"updates": upd}):
                    toast("Saved")
                    st.rerun()
    else:
        st.info("This draft is read-only for your role. A CA can edit it; you may review it and leave comments.")
    pv = call("GET", f"/drafts/{d['id']}/preview")
    if pv:
        with st.expander("👁 Preview (PAN masked, draft banner)", expanded=False):
            st.text(pv)
    ann = call("GET", f"/cases/{cid}/annexures") or []
    section("Annexure index")
    if ann:
        st.dataframe([{"Annexure": a["label"], "Description": a["description"], "Type": a["doc_type"], "Queries": ", ".join(a["relevant_queries"]),
                       "Evidence status": ", ".join(a["evidence_status"]), "SHA-256": a["sha256_prefix"]} for a in ann],
                     use_container_width=True, hide_index=True)
        csvt = call("GET", f"/cases/{cid}/annexures.csv")
        if csvt:
            st.download_button("⬇️ Annexure index (CSV)", csvt, file_name=f"annexure_index_case{cid}.csv")
    else:
        st.markdown('<div class="nm-muted">No files are marked as annexures inside NOTICE-MATE. This is optional: the CA may attach records directly to the final tax-portal response and add or adjust the annexure index in the downloaded Word copy.</div>',
                    unsafe_allow_html=True)


# ---------- Review & export ----------
def tab_review(cid):
    user = st.session_state.user
    h = call("GET", f"/cases/{cid}/review/history") or {}
    ap = h.get("approval") or {}
    if ap.get("approved"):
        st.success(f"APPROVED — version {ap['version']} by {ap['approved_by']} (M.No. {ap.get('membership_no') or 'NOT PROVIDED'}) at {ap['approved_at']}")
    else:
        st.error(f"Not approved: {ap.get('reason', 'no draft yet')}")
    did = ap.get("latest_draft_id")
    if not did:
        empty("No draft to review")
        return
    is_ca = user["role"] == "CA"
    left, right = st.columns([1.2, 1])
    with left:
        section("Final review checklist")
        cl = call("GET", f"/drafts/{did}/checklist") or []
        done = sum(1 for x in cl if x["checked"])
        st.progress(done / max(1, len(cl)), text=f"{done}/{len(cl)} items checked")
        if not is_ca:
            st.info("Only a user with role CA can complete the checklist, approve or reject.")
        elif done < len(cl) and st.button("☑ I have reviewed the whole draft — confirm all checklist items", key=f"ckall{did}"):
            call("POST", f"/drafts/{did}/checklist/confirm-all")
            st.rerun()
        for item in cl:
            c1, c2 = st.columns([3, 2])
            val = c1.checkbox(item["label"], value=item["checked"], key=f"ck{did}{item['item_key']}", disabled=not is_ca)
            note = c2.text_input("Note", value=item["note"] or "", key=f"nt{did}{item['item_key']}", disabled=not is_ca, label_visibility="collapsed",
                                 placeholder="note")
            if is_ca and (val != item["checked"] or (note or "") != (item["note"] or "")):
                call("POST", f"/drafts/{did}/checklist", json_body={"item_key": item["item_key"], "checked": val, "note": note})
        if is_ca:
            decl = call("GET", "/meta/declaration") or {}
            acc = st.checkbox("I accept: " + decl.get("declaration", ""), key=f"decl{did}")
            c1, c2 = st.columns(2)
            if c1.button("✅ Approve latest draft", type="primary", use_container_width=True):
                if call("POST", f"/drafts/{did}/approve", json_body={"declaration_accepted": acc}):
                    toast("Approved")
                    st.rerun()
            with c2.popover("↩️ Reject / request changes", use_container_width=True):
                dec = st.radio("Decision", ["CHANGES_REQUESTED", "REJECTED"], key=f"rj{did}")
                why = st.text_area("Reason", key=f"rjw{did}")
                if st.button("Record decision", key=f"rjb{did}"):
                    if call("POST", f"/drafts/{did}/reject", json_body={"comment": why, "decision": dec}):
                        st.rerun()
            if ap.get("approved"):
                reason = st.text_input("Reason to revoke approval", key=f"rv{did}")
                if st.button("Revoke approval") and reason:
                    call("POST", f"/cases/{cid}/approval/revoke", json_body={"reason": reason})
                    st.rerun()
    with right:
        section("Reviewer comments")
        comments = call("GET", f"/cases/{cid}/review/comments") or []
        if not comments:
            st.markdown('<div class="nm-muted">No comments.</div>', unsafe_allow_html=True)
        for cm in comments:
            st.markdown(f"{badge(cm['status'], 'amber' if cm['status'] == 'OPEN' else 'green')} **v{cm['draft_version']} · {esc(cm['section'])}** — "
                        f"{esc(cm['comment'])}<div class='nm-muted'>{esc(cm['author'])} · {esc(cm['created_at'][:16])}"
                        + (f" · resolved: {esc(cm['resolution'])}" if cm.get("resolution") else "") + "</div>", unsafe_allow_html=True)
            if cm["status"] == "OPEN":
                rs = st.text_input("Resolution", key=f"res{cm['id']}", label_visibility="collapsed", placeholder="How was this resolved?")
                if st.button("Mark resolved", key=f"rsb{cm['id']}") and rs:
                    call("POST", f"/comments/{cm['id']}/resolve", json_body={"resolution": rs})
                    st.rerun()
        with st.form("cmt"):
            sec = st.text_input("Section", placeholder="Q1 / Background / Prayer")
            txt = st.text_area("Comment")
            if st.form_submit_button("Add comment"):
                if call("POST", f"/drafts/{did}/comments", json_body={"section": sec, "comment": txt}):
                    st.rerun()
    section("Version history")
    vers = h.get("versions", [])
    st.dataframe([{"Version": v["version"], "Created": v["created_at"][:16], "Author": v["author"], "Decision": v["latest_decision"] or "—",
                   "Comments": v["comments"], "Hash": v["content_hash"][:12]} for v in vers], use_container_width=True, hide_index=True)
    if len(vers) >= 2:
        c1, c2, c3 = st.columns([1, 1, 1])
        va = c1.selectbox("Compare from", vers, index=1, format_func=lambda v: f"v{v['version']}", key="dfa")
        vb = c2.selectbox("to", vers, index=0, format_func=lambda v: f"v{v['version']}", key="dfb")
        if c3.button("Show changes"):
            df = call("GET", f"/drafts/{va['id']}/diff/{vb['id']}")
            if df:
                st.caption(f"+{df['added']} / −{df['removed']} lines")
                st.code("\n".join(df["diff"]) or "No differences", language="diff")
    section("Export")
    if ap.get("approved"):
        c1, c2, c3 = st.columns(3)
        for col, fmt in ((c1, "docx"), (c2, "pdf")):
            r = call("GET", f"/cases/{cid}/export", params={"format": fmt}, raw=True)
            if r is not None:
                fname = r.headers.get("content-disposition", f"reply.{fmt}").split("filename=")[-1].strip('"')
                col.download_button(f"⬇️ Approved reply ({fmt.upper()})", r.content, file_name=fname, use_container_width=True)
    else:
        alert("Final export (DOCX/PDF) is locked until a CA approves the latest version.", "medium")
    memo = call("GET", f"/cases/{cid}/review-memo")
    if memo:
        st.download_button("⬇️ Internal review memo (not for submission)", memo, file_name=f"review_memo_case{cid}.txt")


# ---------- AI ----------
def tab_ai(cid):
    status = call("GET", "/ai/providers") or {}
    alert(status.get("disclosure", ""), "high")
    st.markdown("Nothing is sent without your approval. Text is redacted on this computer, and sending is **blocked** if any identifier is left.")
    plist = list((status.get("providers") or {}).keys()) or ["anthropic"]
    with st.form("aiprep"):
        c1, c2 = st.columns(2)
        task = c1.selectbox("Task", ["ISSUE_ANALYSIS", "SUMMARISE_NOTICE", "DRAFT_IMPROVE", "EVIDENCE_REVIEW", "CUSTOM"])
        pv = c2.selectbox("Provider", plist, index=plist.index(status.get("default_provider")) if status.get("default_provider") in plist else 0)
        content = st.text_area("Text to analyse (only this text — documents are never attached)", height=180)
        extra = st.text_area("Additional instructions (optional; required for CUSTOM)")
        if st.form_submit_button("🔒 Prepare & preview (nothing is sent)"):
            res = call("POST", f"/cases/{cid}/ai/prepare", json_body={"task": task, "content": content, "extra_instructions": extra, "provider": pv})
            if res:
                st.session_state[f"ai_sub_{cid}"] = res["id"]
    subs = call("GET", f"/cases/{cid}/ai/submissions") or []
    if subs:
        ids = [s["id"] for s in subs]
        cur = st.session_state.get(f"ai_sub_{cid}") if st.session_state.get(f"ai_sub_{cid}") in ids else ids[0]
        pick = st.selectbox("Submission", subs, index=ids.index(cur),
                            format_func=lambda s: f"#{s['id']} · {s.get('purpose', 'GENERAL')} · {s['provider']} · {s['status']} · {s['created_at'][:16]}")
        sid = pick["id"]
        sub = call("GET", f"/ai/submissions/{sid}")
        if sub:
            st.markdown(f"{badge(sub['status'])} {badge(sub.get('purpose', 'GENERAL'), 'blue')} → `{esc(sub['destination'])}` · model `{esc(sub['model'])}`",
                        unsafe_allow_html=True)
            c = sub["pii_summary_json"]["content"]
            st.markdown("**Redacted locally:** " + (", ".join(f"{k} × {v}" for k, v in c["counts"].items()) or "no identifiers detected"))
            if sub["status"] == "BLOCKED":
                alert(sub["block_reason"], "critical")
            if sub["status"] == "FAILED":
                alert(f"{sub.get('error_kind') or 'Error'}: {sub.get('block_reason')}", "critical")
            if sub["exact_payload_preview"]:
                with st.expander("Exact payload to be transmitted (API key travels only in a header and is never shown)", expanded=True):
                    st.code(json.dumps(sub["exact_payload_preview"], indent=2, ensure_ascii=False), language="json")
                    st.caption(f"SHA-256: {sub['payload_hash']}")
                    if sub.get("web_search_requested"):
                        alert("This request enables the provider's web search: the provider will run searches generated from the redacted text.", "high")
            if sub["status"] == "PENDING_APPROVAL":
                ok = st.checkbox("I have reviewed the exact payload above and approve sending it to the AI provider.", key=f"aok{sid}")
                c1, c2 = st.columns(2)
                if c1.button("🚀 Approve & send", type="primary", disabled=not ok):
                    with st.spinner("Waiting for the provider…"):
                        if call("POST", f"/ai/submissions/{sid}/send", json_body={"payload_hash": sub["payload_hash"], "confirm": True}):
                            st.rerun()
                if c2.button("Cancel"):
                    call("POST", f"/ai/submissions/{sid}/cancel")
                    st.rerun()
            if sub.get("response_text"):
                alert(sub.get("response_label", ""), "high")
                if sub.get("purpose") == "AI_DRAFTING":
                    st.caption("This answer was turned into a new reply version automatically (see Draft reply).")
                if sub.get("purpose") == "NOTICE_ANALYSIS" and st.button("📥 Import as structured analysis"):
                    if call("POST", f"/ai/submissions/{sid}/ingest-analysis"):
                        toast("Imported — see Show more → 🧠 13-section analysis")
                if sub.get("purpose") == "RESEARCH" and st.button("📥 Import into research note"):
                    if call("POST", f"/ai/submissions/{sid}/ingest-research"):
                        toast("Imported — see step 5, Law & sources → AI-assisted research")
                st.markdown(sub["response_text"])
    else:
        empty("No AI submissions for this case")


def tab_history(cid):
    h = call("GET", f"/cases/{cid}/history") or []
    if not h:
        empty("No history")
        return
    st.dataframe([{"When (UTC)": e["ts"].replace("T", " ")[:19], "User": e["username"], "Event": e["event"],
                   "Details": json.dumps(e["meta_json"], ensure_ascii=False)} for e in h], use_container_width=True, hide_index=True)
    st.caption("The audit trail records event metadata and hashes only — never document content or AI payloads.")


# ======================= AI PROVIDERS =======================
def providers_view():
    hero("AI providers", "Provider, model and connection status · API keys are read from environment variables only")
    s = call("GET", "/ai/providers")
    if not s:
        return
    alert(s["disclosure"], "high")
    alert(s.get("gemini_disclosure", ""), "medium")
    alert(s.get("live_research_note", ""), "medium")
    c = st.columns(3)
    kpi(c[0], "AI features", "ENABLED" if s["ai_enabled"] else "DISABLED", "NOTICEMATE_AI_ENABLED", "green" if s["ai_enabled"] else "amber")
    kpi(c[1], "Default provider", s["default_provider"], s.get("model", ""), "blue")
    kpi(c[2], "Payload retention", "ON" if s["retain_payloads"] else "OFF", "redacted payload kept after send?", "amber" if s["retain_payloads"] else "green")
    for name, p in s["providers"].items():
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.markdown(f"### {name.title()}\nModel `{esc(p['model'])}`<br><span class='nm-muted'>{esc(p['endpoint'])}</span>", unsafe_allow_html=True)
            c2.markdown(f"Key ({esc(p['key_env'] or '—')}): {badge('CONFIGURED' if p['api_key_configured'] else 'NOT SET', 'green' if p['api_key_configured'] else 'red')}<br>"
                        f"Live web search: {badge('ON' if p['live_web_search_enabled'] else 'OFF', 'teal' if p['live_web_search_enabled'] else 'grey')}",
                        unsafe_allow_html=True)
            if c3.button("Test connection", key=f"tc{name}", help="Sends a fixed test prompt with no client data"):
                with st.spinner("Testing…"):
                    r = call("POST", f"/ai/providers/{name}/test")
                if r:
                    (st.success if r["ok"] else st.error)(f"{'Connected' if r['ok'] else 'Failed'} · model {r['model']}" +
                                                          (f" · {r['error_kind']}: {r['error']}" if not r["ok"] else ""))
    st.caption("To change providers or keys, edit .env (never commit it) and restart the API. Gemini: set GEMINI_API_KEY and NOTICEMATE_GEMINI_MODEL.")


# ======================= LEGAL REGISTRY =======================
def registry_view():
    hero("Legal reference registry", "Only VERIFIED references can appear in replies · no case law is bundled")
    user = st.session_state.user
    refs = call("GET", "/law/refs") or []
    c = st.columns(3)
    kpi(c[0], "References", len(refs), "", "blue")
    kpi(c[1], "Verified", sum(r["status"] == "VERIFIED" for r in refs), "usable in replies", "green")
    kpi(c[2], "Requires verification", sum(r["status"] != "VERIFIED" for r in refs), "render as placeholders", "amber")
    f = st.text_input("🔎 Filter", "").lower()
    st.dataframe([{"Key": r["ref_key"], "Type": r.get("ref_type") or "STATUTE", "Act / Court": r["act"], "Provision / Citation": r["provision"],
                   "Title": r["title"], "Effective from": r.get("effective_from") or "REQUIRES VERIFICATION", "Applies to": r.get("applies_to") or "",
                   "Status": r["status"], "Source": r.get("source_url") or "NOT PROVIDED"}
                  for r in refs if f in json.dumps(r).lower()], use_container_width=True, hide_index=True)
    if user["role"] == "CA" and refs:
        with st.form("vr"):
            st.markdown("**Verify a reference (CA)** — against the official bare Act, notification, circular or judgment")
            k = st.selectbox("Reference", [r["ref_key"] for r in refs])
            url = st.text_input("Source URL checked")
            ef = st.text_input("Effective from (YYYY-MM-DD, optional)")
            note = st.text_input("Verification note (optional)")
            if st.form_submit_button("Mark VERIFIED", type="primary"):
                if call("POST", f"/law/refs/{k}/verify/v2", json_body={"source_url": url, "effective_from": ef or None, "note": note or None}):
                    st.rerun()
    with st.form("ar"):
        st.markdown("**Add a statute, rule, circular, notification or judgment** (starts as REQUIRES VERIFICATION)")
        c1, c2, c3 = st.columns(3)
        k = c1.text_input("Key", placeholder="IT2025_SXXX / CIRC_2026_01 / CASE_ABC_2020")
        typ = c2.selectbox("Type", ["STATUTE", "RULE", "CIRCULAR", "NOTIFICATION", "JUDGMENT", "PRACTICE_NOTE"])
        act = c3.text_input("Act / issuing authority / court")
        c4, c5, c6 = st.columns(3)
        prov = c4.text_input("Provision / number / citation")
        ef = c5.text_input("Effective from (YYYY-MM-DD)")
        ap = c6.text_input("Applies to (e.g. AY 2023-24 onwards)")
        title = st.text_input("Title / case name")
        summ = st.text_area("Short summary in your own words")
        url = st.text_input("Source URL")
        if st.form_submit_button("Add"):
            if call("POST", "/law/refs/v2", json_body={"ref_key": k, "act": act, "provision": prov, "title": title, "summary": summ,
                                                       "source_url": url or None, "ref_type": typ, "effective_from": ef or None,
                                                       "applies_to": ap or None}):
                st.rerun()


# ======================= ADMIN =======================
def admin_view():
    hero("Administration", "Users, roles and audit integrity")
    user = st.session_state.user
    if user["role"] in ("ADMIN", "CA"):
        users = call("GET", "/users") or []
        st.dataframe([{"ID": u["id"], "Username": u["username"], "Name": u["full_name"], "Role": u["role"], "M.No.": u.get("membership_no") or "",
                       "Active": bool(u["active"]), "Locked": bool(u["locked"])} for u in users], use_container_width=True, hide_index=True)
    if user["role"] == "ADMIN":
        c1, c2 = st.columns(2)
        with c1, st.form("nu"):
            st.markdown("**Create user**")
            u = st.text_input("Username")
            fn = st.text_input("Full name")
            r = st.selectbox("Role", ["CA", "STAFF", "ADMIN"])
            mn = st.text_input("ICAI membership no. (CA)")
            pw = st.text_input("Initial password (≥10 chars, 3 character classes)", type="password")
            if st.form_submit_button("Create user", type="primary"):
                if call("POST", "/users", json_body={"username": u, "full_name": fn, "role": r, "password": pw, "membership_no": mn or None}):
                    toast("User created")
        with c2, st.form("unl"):
            st.markdown("**Unlock user**")
            uid = st.number_input("User ID", min_value=1, step=1)
            if st.form_submit_button("Unlock"):
                if call("POST", f"/users/{int(uid)}/unlock"):
                    toast("Unlocked")
    with st.form("pw"):
        st.markdown("**Change my password**")
        o = st.text_input("Current password", type="password")
        n = st.text_input("New password", type="password")
        if st.form_submit_button("Change password"):
            if call("POST", "/auth/password", json_body={"old_password": o, "new_password": n}):
                st.session_state.clear()
                st.rerun()
    if user["role"] in ("ADMIN", "CA") and st.button("🔐 Verify audit-trail integrity"):
        r = call("GET", "/audit/verify")
        if r:
            (st.success if r["valid"] else st.error)(f"Audit chain {'VALID' if r['valid'] else 'BROKEN at entry ' + str(r.get('broken_at_id'))} · {r['entries']} entries")
