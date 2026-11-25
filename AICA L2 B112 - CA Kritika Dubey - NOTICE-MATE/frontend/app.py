"""NOTICE-MATE V3 — guided Streamlit UI. Talks only to the local FastAPI backend.
Run: streamlit run frontend/app.py --server.address 127.0.0.1

Flow: Home (upload a notice) → case workspace in seven steps:
  1 Upload · 2 Confirm details · 3 Issues & evidence (with reasoning side panel) · 4 Reconcile ·
  5 Law & sources · 6 Draft reply · 7 CA approval
Existing V2 screens are reused from tools.py inside the steps.
"""
from __future__ import annotations

import pathlib
import sys

import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tools as T  # noqa: E402
from ui import (DRAFT_BANNER, alert, badge, call, empty, esc, hero, inject_css, inr, kpi, safe_link, section,  # noqa: E402
                stepper, toast)

st.set_page_config(page_title="NOTICE-MATE · CA Notice Workbench", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")
inject_css()

NAV = T.NAV  # ["🏠 Home", "📋 All cases", "📂 Case workspace", "📚 Legal sources", "🛠️ Settings"]
STEP_KEYS = ["upload", "confirm", "issues", "reconcile", "research", "draft", "approve"]
SOURCE_CLASSES = ["PRIMARY", "SECONDARY", "AI_SUGGESTION"]
SOURCE_TYPES = ["ACT_SECTION", "RULE", "NOTIFICATION", "CIRCULAR", "INSTRUCTION", "CASE_LAW", "COMMENTARY", "ARTICLE", "OTHER"]
ACTS = ["", "IT_ACT_1961", "IT_ACT_2025", "IT_RULES_1962", "IT_RULES_2026", "OTHER"]
COURTS = ["", "SUPREME_COURT", "HIGH_COURT", "ITAT", "AAR_BAR", "OTHER"]
STANCES = ["SUPPORTS", "DIFFERS", "DISTINGUISHABLE", "CONTEXT"]
FACT_TYPES = ["DOCUMENT_SPAN", "NOTICE_TEXT", "EVIDENCE_ITEM", "RECON_RUN", "CLIENT_EXPLANATION", "ASSUMPTION"]
BASES = ["ESTABLISHED", "DOCUMENT_AVAILABLE", "CLIENT_EXPLANATION", "ASSUMPTION", "UNRESOLVED"]
STATUS_WORDS = {"VERIFIED": "Verified by CA", "UNVERIFIED": "Unverified", "OUTDATED": "Outdated", "NEEDS_CA_REVIEW": "Needs CA review",
                "REJECTED": "Rejected by CA"}


def is_ca() -> bool:
    return st.session_state.user["role"] in ("CA", "ADMIN")


def goto(page: str, case_id: int | None = None, step: str | None = None):
    st.session_state["_goto"] = page
    if case_id is not None:
        st.session_state.case_id = case_id
        if step:
            st.session_state[f"step_{case_id}"] = step
    st.rerun()


# ======================= HOME =======================
def home_view():
    user = st.session_state.user
    hero(f"Welcome, {user['full_name'].split()[0]}", "Start with the notice. NOTICE-MATE guides you from reading it to a detailed draft reply for your review.")
    st.markdown('<div class="nm-start"><h2>📨 Start with a notice</h2><p>Upload the notice exactly as received — PDF, scanned PDF, '
                'Word or image. It is read on this computer. You will confirm every detail before anything is relied on.</p></div>',
                unsafe_allow_html=True)
    u1, u2 = st.columns(2)
    f = u1.file_uploader("① The income-tax notice (one file)", type=["pdf", "docx", "png", "jpg", "jpeg", "tif", "tiff", "txt"],
                         key="intake_up")
    sup = u2.file_uploader("② Supporting documents (optional — select several at once)", accept_multiple_files=True,
                           key="intake_sup", help="Bank statements, cash book, ledgers, confirmations, invoices, registers, returns. "
                                                  "You can also add or remove them later in step 1.")
    sup = sup if isinstance(sup, list) else []
    if st.button("📨 Read the notice" + (f" and {len(sup)} document{'s' if len(sup) > 1 else ''}" if sup else ""), type="primary"):
        if not f:
            st.warning("Choose the notice file first.")
        else:
            with st.spinner("Reading the notice (scanned pages can take a minute)…"):
                res = call("POST", "/intake/notice", files={"file": (f.name, f.getvalue())})
            if res:
                cid = res["case"]["id"]
                st.session_state[f"intake_{cid}"] = res
                if sup:
                    with st.spinner("Reading the supporting documents…"):
                        T.upload_files(cid, sup)
                step = "upload" if res["next_step"] in ("FIX_OCR", "ACKNOWLEDGE_PARTIAL") else "confirm"
                toast("Notice read — please confirm the details" if step == "confirm" else "The notice could not be fully read", "📨")
                goto(NAV[2], cid, step)

    cases = call("GET", "/cases") or []
    left, right = st.columns([1.4, 1])
    with left:
        section("Continue where you left off")
        if not cases:
            empty("No cases yet", "Upload a notice above to start your first case.")
        for c in sorted(cases, key=lambda x: x["updated_at"], reverse=True)[:6]:
            wf = call("GET", f"/cases/{c['id']}/workflow", quiet=True) or {}
            nxt = next((s for s in wf.get("steps", []) if s["key"] == wf.get("next")), None)
            done = sum(1 for s in wf.get("steps", []) if s["done"])
            c1, c2 = st.columns([4, 1])
            c1.markdown(f'**{esc(c["case_ref"])}** — {esc(c["assessee_name"])} {badge(c["status"])}'
                        f'<div class="nm-muted">AY/TY {esc(c.get("assessment_year") or "NOT PROVIDED")} · {done}/7 steps · '
                        f'next: {esc(nxt["label"] if nxt else "all steps complete")}</div>', unsafe_allow_html=True)
            if c2.button("Open →", key=f"home_open{c['id']}"):
                goto(NAV[2], c["id"], wf.get("next") or "approve")
    with right:
        section("AI drafting")
        ai_status_banner()
        section("Practice snapshot")
        d = call("GET", "/dashboard", quiet=True)
        if d:
            k = st.columns(2)
            kpi(k[0], "Due ≤ 15 days", len(d["upcoming_deadlines"]),
                f"{sum(1 for x in d['upcoming_deadlines'] if not x['verified'])} unverified", "amber")
            kpi(k[1], "Awaiting CA review", len(d["awaiting_review"]), "latest draft not approved", "amber" if d["awaiting_review"] else "green")
            for a in d["alerts"][:5]:
                alert(a["text"], a["level"])
            st.caption("Full dashboard: 📋 Cases & dashboard.")


# ======================= CASE WORKSPACE =======================
def workspace_view():
    cases = call("GET", "/cases") or []
    if not cases:
        empty("No cases yet", "Go to 🏠 Home and upload a notice.")
        return
    ids = [c["id"] for c in cases]
    cur = st.session_state.get("case_id") if st.session_state.get("case_id") in ids else ids[0]
    sel = st.sidebar.selectbox("Active case", cases, index=ids.index(cur), format_func=lambda c: f"{c['case_ref']} — {c['assessee_name']}")
    cid = sel["id"]
    st.session_state.case_id = cid
    case = call("GET", f"/cases/{cid}")
    wf = call("GET", f"/cases/{cid}/workflow") or {"steps": [], "next": "upload"}
    if not case:
        return
    skey = f"step_{cid}"
    if skey not in st.session_state or st.session_state[skey] not in STEP_KEYS:
        st.session_state[skey] = wf.get("next") or "upload"
    step = st.session_state[skey]

    hero(f"{case['case_ref']} — {case['assessee_name']}",
         f"{case['assessee_category']} · AY/TY {case.get('assessment_year') or 'NOT PROVIDED'} · PAN {case['pan_masked']} · status {case['status']}")
    stepper(wf["steps"], step)
    cols = st.columns(len(STEP_KEYS))
    for col, s in zip(cols, wf["steps"]):
        if col.button(("● " if s["key"] == step else "") + s["label"], key=f"go_{s['key']}_{cid}", use_container_width=True,
                      help=s["hint"]):
            st.session_state[skey] = s["key"]
            st.rerun()
    cur_step = next((s for s in wf["steps"] if s["key"] == step), None)
    if cur_step:
        st.caption(f"Step {STEP_KEYS.index(step) + 1} of 7 · {cur_step['hint']}")

    docs = call("GET", f"/cases/{cid}/documents") or []
    ns = call("GET", f"/cases/{cid}/notices") or []
    if step == "upload":
        step_upload(cid, docs, ns)
    elif step == "confirm":
        step_confirm(cid, case, ns, docs)
    elif step == "issues":
        step_issues(cid, docs)
    elif step == "reconcile":
        step_reconcile(cid, case, docs)
    elif step == "research":
        step_research(cid, docs)
    elif step == "draft":
        step_draft(cid)
    elif step == "approve":
        step_approve(cid)

    idx = STEP_KEYS.index(step)
    st.markdown("---")
    b1, b2, b3 = st.columns([1, 4, 1])
    if idx > 0 and b1.button("← Back", key=f"back_{cid}"):
        st.session_state[skey] = STEP_KEYS[idx - 1]
        st.rerun()
    if idx < len(STEP_KEYS) - 1 and b3.button("Next step →", key=f"next_{cid}", type="primary"):
        st.session_state[skey] = STEP_KEYS[idx + 1]
        st.rerun()
    if st.toggle("Show more for this case — status, redaction terms, AI requests, 13-section analysis, audit history",
                 key=f"more_{cid}"):
        t1, t2, t3, t4 = st.tabs(["Case settings", "🤖 AI requests", "🧠 13-section analysis", "🕘 Audit history"])
        with t1:
            case_settings(cid, case)
        with t2:
            T.tab_ai(cid)
        with t3:
            T.tab_analysis(cid, ns)
        with t4:
            T.tab_history(cid)


def case_settings(cid, case):
    stt = ["OPEN", "AWAITING_CLIENT", "UNDER_REVIEW", "APPROVED", "SUBMITTED", "CLOSED"]
    new = st.selectbox("Case status", stt, index=stt.index(case["status"]) if case["status"] in stt else 0, key=f"cs{cid}")
    if new != case["status"] and st.button("Update status"):
        if call("PUT", f"/cases/{cid}/status", json_body={"status": new}):
            toast("Status updated")
            st.rerun()
    t = st.text_area("🔒 Redaction terms — names that must never leave this computer (one per line)", "\n".join(case["party_names"]),
                     key=f"rt{cid}")
    if st.button("Save redaction terms"):
        if call("PUT", f"/cases/{cid}/redaction-terms", json_body={"names": t.splitlines()}):
            toast("Redaction terms saved")


# ---------- Step 1: upload ----------
def _page_table(d: dict):
    pages = d.get("extraction_pages_json") or []
    if not pages:
        return
    rows = [{"Page": p["page"], "Read by": p["method"], "Result": p["status"].replace("_", " "), "Characters": p["chars"],
             "OCR confidence": "—" if p.get("confidence") is None else f"{p['confidence']:.0f}%"} for p in pages]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def step_upload(cid, docs, ns):
    section("The notice")
    notice_docs = [d for d in docs if d["doc_type"] == "NOTICE"]
    if ns:
        n_doc = next((d for d in docs if d["id"] == ns[-1]["document_id"]), None)
        st.markdown(f"✅ Notice read from **{esc(n_doc['original_name'] if n_doc else 'document')}** "
                    f"{badge(n_doc['extraction_status']) if n_doc else ''}", unsafe_allow_html=True)
        if n_doc:
            with st.expander("Page-by-page reading result"):
                _page_table(n_doc)
                for note in n_doc.get("extraction_notes") or []:
                    alert(note, "high" if ("PARTIAL" in note or "NO TEXT" in note) else "info")
    elif not notice_docs:
        empty("No notice in this case yet", "Upload it below (or start from 🏠 Home), then confirm it as a NOTICE.")
    for d in notice_docs:
        if ns and d["id"] == ns[-1]["document_id"]:
            continue
        st.markdown(f"**{esc(d['original_name'])}** {badge(d['extraction_status'])}", unsafe_allow_html=True)
        _page_table(d)
        if d["extraction_status"] == "FAILED":
            alert("No text could be read from this file, so it cannot be analysed. Open 🛠️ Settings → System check, fix OCR if needed, "
                  "then upload a clearer scan (300 dpi, straight, not password-protected).", "critical")
        elif d["extraction_status"] == "PARTIAL":
            alert("Only part of this notice could be read. You can continue with the readable text, but you must compare the "
                  "unreadable pages with the original yourself.", "high")
            if st.button("I will check the unreadable pages — read the rest of the notice", key=f"ack{d['id']}", type="primary"):
                if call("POST", f"/intake/documents/{d['id']}/acknowledge-partial"):
                    toast("Notice parsed from readable pages")
                    st.session_state[f"step_{cid}"] = "confirm"
                    st.rerun()
        else:
            if st.button("📨 Read this as the notice", key=f"pn3{d['id']}", type="primary"):
                if call("POST", f"/documents/{d['id']}/parse-notice"):
                    st.session_state[f"step_{cid}"] = "confirm"
                    st.rerun()
    section("Supporting documents")
    st.caption("Add bank statements, books, ledgers, AIS/26AS, confirmations and invoices. Each file is read on this computer and its "
               "reading result is shown — nothing incomplete is treated as complete.")
    T.tab_documents(cid, docs)


# ---------- Step 2: confirm ----------
def step_confirm(cid, case, ns, docs):
    intake = st.session_state.get(f"intake_{cid}") or {}
    sug = intake.get("suggestions") or {}
    provisional = case["assessee_name"].startswith("[TO BE CONFIRMED")
    section("Who is the notice addressed to?")
    if sug:
        st.caption("Suggestions read from the notice — check each against the original before confirming:")
        for k, v in sug.items():
            st.markdown(f"&nbsp;&nbsp;{badge('SUGGESTED', 'amber')} **{esc(k.replace('_', ' ').title())}:** {esc(v['value'])} "
                        f"<span class='nm-muted'>({esc(v['source'])})</span>", unsafe_allow_html=True)
    with st.form(f"confirm{cid}"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Assessee name *", value=(sug.get("assessee_name", {}).get("value", "") if provisional else case["assessee_name"]))
        cats = T.CATS
        cat = c2.selectbox("Assessee category *", cats, index=cats.index(case["assessee_category"]) if case["assessee_category"] in cats else 0)
        ref = c3.text_input("Your case reference", value=case["case_ref"])
        c4, c5 = st.columns(2)
        pan = c4.text_input("PAN (stored on this computer only)", value=sug.get("pan", {}).get("value", "") if provisional else "")
        ay = c5.text_input("Assessment / Tax year", value=case.get("assessment_year") or sug.get("assessment_year", {}).get("value", ""))
        if not provisional:
            st.caption("Leave PAN blank to keep the one already saved.")
        if st.form_submit_button("Confirm details", type="primary"):
            body = {"assessee_name": name, "assessee_category": cat, "pan": pan or None, "assessment_year": ay or None,
                    "case_ref": ref or None}
            if call("PUT", f"/cases/{cid}/confirm-details", json_body=body):
                toast("Details confirmed")
                st.rerun()
    section("Notice particulars and deadline")
    st.caption("Every field shows where it was found in the notice. The deadline counts only after you record where you verified it. "
               "Missing or conflicting values are shown as NOT PROVIDED — never guessed.")
    left, right = st.columns([1.35, 1])
    with left:
        T.tab_notice(cid, ns)
    with right:
        n_doc = next((d for d in docs if ns and d["id"] == ns[-1]["document_id"]), None)
        st.markdown("**The notice as read — compare here**")
        if n_doc:
            txt = call("GET", f"/documents/{n_doc['id']}/text", quiet=True) or {}
            st.text_area("Notice text", (txt.get("text") or "(no text)").replace("\f", "\n— next page —\n")[:40000], height=620,
                         key=f"notice_txt_{cid}", label_visibility="collapsed", disabled=True)
        else:
            st.caption("No notice read yet.")


# ---------- reasoning side panel ----------
def source_card(src: dict, key: str, *, show_decide: bool = True, link_pinpoint: str | None = None):
    cls = {"PRIMARY": "primary", "SECONDARY": "secondary", "AI_SUGGESTION": "ai"}[src["source_class"]]
    status = src["effective_status"]
    meta1 = " · ".join(x for x in [src.get("issuing_body"), (src.get("court_level") or "").replace("_", " ").title() or None,
                                   src.get("document_number"), src.get("date_issued") and f"dated {src['date_issued']}"] if x)
    prov = " · ".join(x for x in [src.get("act") and src["act"].replace("_", " "), src.get("provision"),
                                  (link_pinpoint or src.get("pinpoint")) and f"¶ {link_pinpoint or src.get('pinpoint')}"] if x)
    eff = ""
    if src.get("effective_from") or src.get("effective_to"):
        eff = f"Effective {src.get('effective_from') or '?'} → {src.get('effective_to') or 'in force'}"
    ay = f"AY {src.get('ay_from') or '?'} – {src.get('ay_to') or 'onwards'}" if (src.get("ay_from") or src.get("ay_to")) else ""
    html = (f'<div class="nm-src {cls}">{badge(src["source_class"].replace("_", " "))}{badge(src["source_type"], "grey")}'
            f'{badge(STATUS_WORDS.get(status, status), {"VERIFIED": "green", "OUTDATED": "red"}.get(status, "amber"))}'
            + (f'{badge(src["stance"])}' if src.get("stance") else "")
            + f'<div class="t">{esc(src["title"])}</div>'
            + (f'<div>{esc(src["citation"])}</div>' if src.get("citation") else "")
            + (f'<div class="m">{esc(meta1)}</div>' if meta1 else "")
            + (f'<div class="m">{esc(prov)}</div>' if prov else "")
            + (f'<div class="m">{esc(" · ".join(x for x in [eff, ay] if x))}</div>' if (eff or ay) else "")
            + (f'<div class="m">Applicability: {esc(src["applicability_note"])}</div>' if src.get("applicability_note") else "")
            + (f'<div class="nm-quote">{esc(src["excerpt"])}</div>' if src.get("excerpt") else "")
            + (f'<div class="m">{esc(src["summary"])}</div>' if src.get("summary") and not src.get("excerpt") else "")
            + (f'<div class="m">{esc(src["relevance_note"])}</div>' if src.get("relevance_note") else "")
            + f'<div class="m">{safe_link(src.get("official_url"))} '
            + (badge("official government site", "teal") if src.get("url_is_official") else
               (badge("not an official site", "amber") if src.get("official_url") else ""))
            + "</div></div>")
    st.markdown(html, unsafe_allow_html=True)
    if show_decide:
        with st.expander("Verify / history", expanded=False):
            source_decision_form(src["id"], key)


def source_decision_form(source_id: int, key: str):
    full = call("GET", f"/legal-sources/{source_id}") or {}
    for h in (full.get("verification_history") or [])[:5]:
        st.markdown(f"{badge(h['decision'])} by {esc(h['decided_by_name'])} · {esc(h['decided_at'][:16])}"
                    + (f" · checked ¶ {esc(h['checked_pinpoint'])}" if h.get("checked_pinpoint") else "")
                    + (f" · applicability confirmed" if h.get("applicability_confirmed") else "")
                    + (f"<div class='nm-muted'>{esc(h['note'])}</div>" if h.get("note") else ""), unsafe_allow_html=True)
    if not full.get("verification_history"):
        st.caption("Not checked by anyone yet.")
    if full.get("source_class") == "AI_SUGGESTION":
        st.caption("AI suggestions cannot be verified as authority. Add the primary source it points to and verify that.")
    opts = ["VERIFIED", "NEEDS_CA_REVIEW", "OUTDATED", "UNVERIFIED"] if is_ca() else ["NEEDS_CA_REVIEW", "UNVERIFIED"]
    with st.form(f"sd_{key}_{source_id}"):
        st.markdown("**Record your check** — open the source link first.")
        dec = st.selectbox("Decision", opts, key=f"sdd_{key}_{source_id}")
        url = st.text_input("Link you opened (must match the source link)", value="", key=f"sdu_{key}_{source_id}")
        pin = st.text_input("Paragraph / section / sub-rule you checked", value=full.get("pinpoint") or "", key=f"sdp_{key}_{source_id}")
        app = st.checkbox("Applicability confirmed: Act, AY/Tax Year, effective dates and transition provisions", key=f"sda_{key}_{source_id}")
        note = st.text_area("Note", key=f"sdn_{key}_{source_id}")
        if st.form_submit_button("Record decision"):
            if call("POST", f"/legal-sources/{source_id}/decision",
                    json_body={"decision": dec, "checked_url": url or None, "checked_pinpoint": pin or None,
                               "applicability_confirmed": app, "note": note}):
                toast("Decision recorded")
                st.rerun()


def trace_panel(issue_id: int, key: str = "tp"):
    t = call("GET", f"/issues/{issue_id}/trace")
    if not t:
        return
    st.markdown('<div class="nm-panel"><h3>🔎 Why this view? — reasoning trail</h3>'
                f'<div class="nm-muted">{esc(t["disclaimer"])}</div></div>', unsafe_allow_html=True)
    for w in t["warnings"][:8]:
        alert(w, "high" if ("outdated" in w or "AI" in w or "differing" in w) else "medium")
    st.markdown('<div class="nm-tr">1 · What the notice says</div>', unsafe_allow_html=True)
    nd = t.get("notice_document") or {}
    st.markdown(f'<div class="nm-quote">{esc(t["issue"]["query_text"][:700])}</div>'
                f'<div class="nm-muted">From {esc(nd.get("original_name") or "notice (document not linked)")} '
                f'{badge(nd["extraction_status"]) if nd.get("extraction_status") else ""}</div>', unsafe_allow_html=True)
    st.markdown('<div class="nm-tr">2 · Facts and evidence</div>', unsafe_allow_html=True)
    if not t["evidence"]:
        st.markdown('<div class="nm-muted">No evidence mapped.</div>', unsafe_allow_html=True)
    for e in t["evidence"]:
        st.markdown(f'{badge(e["status"])} {esc(e.get("requirement_label") or e["requirement"].replace("_", " "))} '
                    f'<span class="nm-muted">— {esc(e.get("document_name") or "no document")}</span>'
                    + (f'<div class="nm-muted">&nbsp;&nbsp;establishes: {esc(e["establishes"])}</div>' if e.get("establishes") else ""),
                    unsafe_allow_html=True)
    for r in t["reconciliations"][:3]:
        st.markdown(f'{badge(r["status"] or "RUN", "teal")} Reconciliation: {esc(r["recon_type"])} '
                    f'<span class="nm-muted">({esc(r["created_at"][:10])}) — consistency only, not genuineness</span>', unsafe_allow_html=True)
    st.markdown('<div class="nm-tr">3 · Proposed view and the law behind it</div>', unsafe_allow_html=True)
    if not t["propositions"]:
        st.markdown('<div class="nm-muted">No proposition recorded yet — add one in step 5 (Law & sources).</div>', unsafe_allow_html=True)
    for p in t["propositions"]:
        st.markdown(f'{badge(STATUS_WORDS.get(p["effective_status"], p["effective_status"]), "green" if p["effective_status"] == "VERIFIED" else "amber")}'
                    f'{badge(p["origin_label"], "grey")}<div><b>{esc(p["text"])}</b></div>'
                    + (f'<div class="nm-muted">CA note: {esc(p["ca_note"])}</div>' if p.get("ca_note") else ""), unsafe_allow_html=True)
        for f in p["facts"]:
            label = f.get("document_name") or f.get("evidence_requirement") or f.get("recon_type") or f["fact_type"].replace("_", " ").title()
            st.markdown(f'&nbsp;&nbsp;{badge(f["basis"])} {esc(label)}'
                        + (f' p.{f["page"]}' if f.get("page") else "")
                        + (f'<div class="nm-quote">{esc(f["quote"])}</div>' if f.get("quote") else "")
                        + (f'<div class="nm-muted">{esc(f["note"])}</div>' if f.get("note") else ""), unsafe_allow_html=True)
        for title, stances in (("Supports", ("SUPPORTS",)), ("Differs / distinguishable", ("DIFFERS", "DISTINGUISHABLE")),
                               ("Context", ("CONTEXT",))):
            grp = [s for s in p["sources"] if s["stance"] in stances]
            if grp:
                st.markdown(f'<div class="nm-muted"><b>{title}</b></div>', unsafe_allow_html=True)
                for s in grp:
                    source_card(s, f"{key}{p['id']}", link_pinpoint=s.get("link_pinpoint"))
        if not any(s["stance"] in ("DIFFERS", "DISTINGUISHABLE") for s in p["sources"]):
            st.caption("No differing authority recorded. If any exists, add it — the CA must address it.")
        for b in p["blocking_reasons"]:
            st.caption("• " + b)
    with st.expander("Where to verify (official portals)"):
        for pt in t["portals"]:
            st.markdown(f"- {safe_link(pt['url'], pt['name'])}", unsafe_allow_html=True)


# ---------- Step 3: issues & evidence ----------
def _pick_issue(cid, iss, key):
    ids = [i["id"] for i in iss]
    cur = st.session_state.get(f"issue_{cid}") if st.session_state.get(f"issue_{cid}") in ids else ids[0]
    pick = st.selectbox("Issue", iss, index=ids.index(cur), key=f"{key}{cid}",
                        format_func=lambda i: f"Query {i['seq']} · {i.get('title') or i['category'].replace('_', ' ').title()}"
                                              + ("" if (i.get("title") or "").find("₹") >= 0 or not i["amount"] else f" · {inr(i['amount'])}"))
    st.session_state[f"issue_{cid}"] = pick["id"]
    return pick


def step_issues(cid, docs):
    iss = call("GET", f"/cases/{cid}/issues") or []
    mat = call("GET", f"/cases/{cid}/evidence") or []
    if not iss:
        empty("No issues yet", "In step 2, click 'Generate issue-wise analysis from this notice', or add an issue manually.")
        T.add_issue_form(cid)
        return
    import re as _re

    odd = [i for i in iss if _re.match(r"^\s*(?:[a-z]|and\b|or\b|but\b|further\b)", i["query_text"])
           or len(i["query_text"].split()) < 8]
    if odd and len(iss) > 1:
        alert("These issues look like fragments of a longer notice question (they start mid-sentence or are very short): "
              + ", ".join(f"Q{i['seq']}" for i in odd) + ". If so, merge them below — notes and evidence are kept.", "medium")
    if is_ca() and len(iss) > 1:
        with st.expander("🛠 Correct issue splitting — merge parts of one notice question", expanded=bool(odd)):
            st.caption("If the notice has one concern but the parser split it into several rows, select those rows, choose the main issue, and rewrite the single combined question. Earlier CA assessments, evidence notes and legal propositions are retained in the main issue’s history.")
            selected = st.multiselect("Issues that belong to the same concern", iss, default=[],
                                      format_func=lambda row: f"Q{row['seq']} · {row['category'].replace('_', ' ').title()} · {row['query_text'][:90]}",
                                      key=f"merge_select_{cid}")
            if len(selected) >= 2:
                target = st.selectbox("Keep this as the main issue", selected,
                                      format_func=lambda row: f"Q{row['seq']} · {row['category'].replace('_', ' ').title()}",
                                      key=f"merge_target_{cid}_{'_'.join(str(x['id']) for x in selected)}")
                initial = "\n\n".join(row["query_text"] for row in selected)
                corrected_query = st.text_area("One corrected question to use for the issue", value=initial,
                                                height=150, key=f"merge_text_{cid}_{'_'.join(str(x['id']) for x in selected)}",
                                                help="Edit this into one clear statement of the actual concern in the notice; remove duplicated fragments or unrelated boilerplate.")
                st.warning("Merging removes the extra issue rows. Their saved assessments and evidence details stay available in the main issue’s history. Cases with an existing reply draft must be corrected before generating another draft.")
                if st.button("Merge into one issue", type="primary", key=f"merge_go_{cid}"):
                    res = call("POST", f"/cases/{cid}/issues/merge", json_body={
                        "target_issue_id": target["id"],
                        "source_issue_ids": [row["id"] for row in selected if row["id"] != target["id"]],
                        "query_text": corrected_query})
                    if res:
                        st.session_state[f"issue_{cid}"] = res["id"]
                        toast("Issues merged; prior notes retained in history")
                        st.rerun()
            else:
                st.caption("Select at least two rows to see the merge controls.")
    summ = call("GET", f"/cases/{cid}/mapping-summary", quiet=True) or {"issues": [], "contradictions": []}
    rows = [{"Query": f"Q{x['seq']}", "Subject": x.get("title") or x["category"].replace("_", " ").title(),
             "Documents matched": ", ".join(d["name"] for d in x["documents"]) or "none yet",
             "To check": x["uncertain"], "Not among the uploads": "; ".join(x["gaps"]) or "—"} for x in summ["issues"]]
    if rows:
        section("How the uploaded documents match the notice's queries")
        st.dataframe(rows, use_container_width=True, hide_index=True)
        if summ.get("contradictions"):
            for c in summ["contradictions"]:
                alert(("Query " + str(c["issue_seq"]) + ": " if c.get("issue_seq") else "") + c["text"], "high")
        if st.button("🔄 Match the documents again", key=f"remap{cid}"):
            call("POST", f"/cases/{cid}/map-documents")
            st.rerun()
    i = _pick_issue(cid, iss, "isel")
    main, panel = st.columns([1.55, 1])
    with main:
        st.markdown(f"**Query {i['seq']} as worded in the notice**")
        st.markdown(f"<div class='nm-quote'>{esc(i['query_text'])}</div>", unsafe_allow_html=True)
        matched_records(i)
        record_states(cid, i)
        T.issue_block(cid, i, mat, docs, call("GET", "/meta/strategies") or {}, call("GET", "/law/refs") or [])
        T.add_issue_form(cid)
    with panel:
        trace_panel(i["id"], "iss")


def matched_records(i: dict):
    links = call("GET", f"/issues/{i['id']}/links", quiet=True) or []
    section(f"Records matched to query {i['seq']}")
    if not links:
        empty("No uploaded record matches this query yet", "Add the relevant documents in step 1. The reply will say briefly what is "
                                                           "not part of the submission.")
        return
    st.caption("Each passage below was found inside an uploaded document. Strong matches are used in the reply. Uncertain ones are "
               "not used unless you accept them; reject any that do not belong here.")
    by_doc: dict[str, list[dict]] = {}
    for l in links:
        by_doc.setdefault(l["document_name"], []).append(l)
    for name, ls in by_doc.items():
        strong = sum(1 for l in ls if l["certainty"] == "STRONG" or l["status"] == "ACCEPTED")
        with st.expander(f"📄 {name} — {strong} strong, {len(ls) - strong} to check", expanded=False):
            for l in ls:
                tag = ("ACCEPTED", "green") if l["status"] == "ACCEPTED" else (("STRONG", "green") if l["certainty"] == "STRONG"
                                                                               else ("CHECK", "amber"))
                st.markdown(f"{badge(*tag)} {esc(l['passage'][:400])}<div class='nm-muted'>Why: {esc(l['reason'])}</div>",
                            unsafe_allow_html=True)
                a, b, _ = st.columns([1, 1, 3])
                if l["status"] != "ACCEPTED" and a.button("✓ Use", key=f"lk_a{l['id']}"):
                    call("PUT", f"/doc-links/{l['id']}", json_body={"status": "ACCEPTED"})
                    st.rerun()
                if b.button("✗ Not relevant", key=f"lk_r{l['id']}"):
                    call("PUT", f"/doc-links/{l['id']}", json_body={"status": "REJECTED"})
                    st.rerun()


def record_states(cid: int, i: dict):
    """The records this query needs, each in one clear state. The CA's marks say what is held; they do not tell
    anyone what a record says, so the reply only calls such records 'available for production'."""
    summ = call("GET", f"/cases/{cid}/mapping-summary", quiet=True) or {"issues": []}
    me = next((x for x in summ["issues"] if x["issue_id"] == i["id"]), None)
    if not me:
        return
    section(f"Records for query {i['seq']}")
    st.caption("“Uploaded and read” is set automatically from the documents' contents. For records you hold but have not uploaded, "
               "mark them “Available with us” — the reply will say they can be produced, without describing their contents. "
               "Uploading is never required.")
    colours = {"READ": "green", "AVAILABLE_WITH_CA": "blue", "NOT_AVAILABLE": "amber", "CONFLICT": "red", "NOT_PROVIDED": "amber"}
    choices = {"": "Not yet known", "AVAILABLE": "Available with us (not uploaded)", "NOT_AVAILABLE": "Not available"}
    picks = {}
    for r in me["records"]:
        c1, c2 = st.columns([3, 2])
        c1.markdown(f"{esc(r['label'])}{' · <b>asked in the notice</b>' if r['asked'] else ''} "
                    f"{badge(r['state_label'], colours.get(r['state'], 'amber'))}"
                    + (f"<div class='nm-muted'>{esc(r['detail'])}</div>" if r.get("detail") else ""), unsafe_allow_html=True)
        if r["state"] == "READ":
            continue
        cur = "AVAILABLE" if r["state"] == "AVAILABLE_WITH_CA" else ("NOT_AVAILABLE" if r["state"] == "NOT_AVAILABLE" else "")
        if is_ca():
            picks[r["key"]] = c2.selectbox("Your mark", list(choices), index=list(choices).index(cur), format_func=choices.get,
                                           key=f"recstate_{i['id']}_{r['key']}", label_visibility="collapsed")
    if is_ca() and picks and st.button("Save record marks", key=f"recsave_{i['id']}"):
        keep_av = [r["key"] for r in me["records"] if r["state"] == "READ" and r["key"] in
                   ((i.get("analysis_json") or {}).get("available_records") or [])]
        body = {"available_records": sorted({k for k, v in picks.items() if v == "AVAILABLE"} | set(keep_av)),
                "unavailable_records": sorted(k for k, v in picks.items() if v == "NOT_AVAILABLE")}
        if call("PUT", f"/issues/{i['id']}/analysis", json_body={"updates": body}):
            toast("Record marks saved")
            st.rerun()


# ---------- Step 4: reconcile ----------
def step_reconcile(cid, case, docs):
    alert("This step is optional. Skip it if the records are sensitive or detailed matching is not needed. By default, reconciliation stays an internal CA check; choose in Draft reply if you want selected findings reflected in the response.", "info")
    alert("A reconciliation that agrees shows the records are consistent with each other. It does not prove the source or "
          "genuineness of any amount.", "info")
    iss = call("GET", f"/cases/{cid}/issues") or []
    t1, t2, t3 = st.tabs(["🔁 Bank / books / AIS / 26AS", "🏦 Lenders, capital & advances", "🧮 Tax impact (illustrative)"])
    with t1:
        T.tab_recon(cid, docs)
    with t2:
        T.tab_parties(cid, iss)
    with t3:
        T.tab_tax(cid, case)


# ---------- Step 5: law & sources ----------
def step_research(cid, docs):
    iss = call("GET", f"/cases/{cid}/issues") or []
    alert("Only propositions a CA has verified against a current primary source go into the reply. Everything else stays in "
          "internal notes.", "medium")
    if not iss:
        empty("No issues yet", "Generate issues in step 2 first.")
        return
    i = _pick_issue(cid, iss, "rsel")
    tab_law, tab_ai_res = st.tabs(["⚖️ Propositions & sources", "🤖 AI-assisted research (optional)"])
    with tab_ai_res:
        st.caption("Preview and approval are required before anything is sent. AI output is recorded as an AI suggestion, never as authority.")
        T.tab_research(cid, iss)
    with tab_law:
        _law_workbench(cid, i, docs)


def _law_workbench(cid, i, docs):
    main, panel = st.columns([1.35, 1])
    with main:
        t = call("GET", f"/issues/{i['id']}/trace") or {"propositions": [], "evidence": [], "reconciliations": []}
        sources = call("GET", "/legal-sources") or []
        for p in t["propositions"]:
            proposition_editor(cid, p, sources, docs, t)
        with st.expander("➕ Add a proposition for this issue"):
            with st.form(f"np{i['id']}"):
                txt = st.text_area("Proposition (one legal or factual point the reply would rely on)")
                kind = st.selectbox("Kind", ["LEGAL", "FACTUAL", "MIXED"])
                if st.form_submit_button("Add proposition"):
                    if call("POST", f"/cases/{cid}/propositions", json_body={"text": txt, "issue_id": i["id"], "kind": kind}):
                        st.rerun()
        with st.expander("➕ Add a new legal source to the library"):
            add_source_form(f"rs{i['id']}")
    with panel:
        trace_panel(i["id"], "rs")


def proposition_editor(cid, p, sources, docs, t):
    with st.container(border=True):
        st.markdown(f'{badge(STATUS_WORDS.get(p["effective_status"], p["effective_status"]), "green" if p["effective_status"] == "VERIFIED" else "amber")}'
                    f'{badge(p["kind"], "blue")}{badge(p["origin_label"], "grey")} <b>#{p["id"]}</b> {esc(p["text"])}', unsafe_allow_html=True)
        for b in p["blocking_reasons"]:
            st.caption("⚠ " + b)
        c1, c2 = st.columns(2)
        with c1.popover("🔗 Link a source", use_container_width=True):
            if not sources:
                st.caption("The library is empty — add a source below first.")
            else:
                with st.form(f"ls{p['id']}"):
                    sid = st.selectbox("Source", [s["id"] for s in sources],
                                       format_func=lambda x: next(f"[{s['effective_status']}] {s['title'][:80]}" for s in sources if s["id"] == x), key=f"Sourcesel{p['id']}")
                    stance = st.selectbox("How it relates", STANCES, key=f"Howitrelatessel{p['id']}")
                    pin = st.text_input("Relevant paragraph / provision", key=f"Relevantparatex{p['id']}")
                    rn = st.text_input("Why it is relevant", key=f"Whyitisrelevtex{p['id']}")
                    if st.form_submit_button("Link source"):
                        if call("POST", f"/propositions/{p['id']}/sources",
                                json_body={"source_id": sid, "stance": stance, "pinpoint": pin or None, "relevance_note": rn}):
                            st.rerun()
        with c2.popover("📎 Link a fact", use_container_width=True):
            with st.form(f"lf{p['id']}"):
                ft = st.selectbox("Fact type", FACT_TYPES, key=f"Facttypesel{p['id']}")
                basis = st.selectbox("Basis", BASES, key=f"Basissel{p['id']}")
                did = st.selectbox("Document (for document / notice quotes)", [None] + [d["id"] for d in docs],
                                   format_func=lambda x: "—" if x is None else next(d["original_name"] for d in docs if d["id"] == x), key=f"Documentfordsel{p['id']}")
                page = st.number_input("Page (optional)", min_value=0, step=1, value=0, key=f"Pageoptionalnum{p['id']}")
                quote = st.text_area("Exact words copied from the extracted text", key=f"Exactwordscotex{p['id']}")
                evs = [None] + [e["id"] for e in t["evidence"]]
                eid = st.selectbox("Evidence item", evs, format_func=lambda x: "—" if x is None else
                                   next(e.get("requirement_label") or e["requirement"] for e in t["evidence"] if e["id"] == x), key=f"Evidenceitemsel{p['id']}")
                rns = [None] + [r["id"] for r in t["reconciliations"]]
                rid = st.selectbox("Reconciliation run", rns, format_func=lambda x: "—" if x is None else
                                   next(f"#{r['id']} {r['recon_type']}" for r in t["reconciliations"] if r["id"] == x), key=f"Reconciliatisel{p['id']}")
                note = st.text_input("Note", key=f"Notetex{p['id']}")
                if st.form_submit_button("Link fact"):
                    if call("POST", f"/propositions/{p['id']}/facts",
                            json_body={"fact_type": ft, "basis": basis, "document_id": did, "page": int(page) or None, "quote": quote or None,
                                       "evidence_item_id": eid, "recon_run_id": rid, "note": note}):
                        st.rerun()
        for s in p["sources"]:
            cc1, cc2 = st.columns([5, 1])
            cc1.markdown(f'{badge(s["stance"])} {esc(s["title"][:90])} {badge(STATUS_WORDS.get(s["effective_status"], s["effective_status"]), "grey")}',
                         unsafe_allow_html=True)
            if cc2.button("Unlink", key=f"ul{p['id']}_{s['id']}"):
                call("DELETE", f"/propositions/{p['id']}/sources/{s['id']}")
                st.rerun()
        for f in p["facts"]:
            cc1, cc2 = st.columns([5, 1])
            cc1.markdown(f'{badge(f["basis"])} {esc(f["fact_type"].replace("_", " ").title())}: '
                         f'{esc((f.get("quote") or f.get("note") or "")[:120])}', unsafe_allow_html=True)
            if cc2.button("Remove", key=f"rf{f['id']}"):
                call("DELETE", f"/proposition-facts/{f['id']}")
                st.rerun()
        with st.expander("Edit wording / CA decision"):
            with st.form(f"pe{p['id']}"):
                txt = st.text_area("Wording (editing sends a verified proposition back for CA review)", p["text"], key=f"Wordingedititex{p['id']}")
                if st.form_submit_button("Save wording"):
                    if call("PUT", f"/propositions/{p['id']}", json_body={"text": txt}):
                        st.rerun()
            opts = ["VERIFIED", "NEEDS_CA_REVIEW", "REJECTED", "UNVERIFIED"] if is_ca() else ["NEEDS_CA_REVIEW", "UNVERIFIED"]
            with st.form(f"pd{p['id']}"):
                dec = st.selectbox("Decision", opts, key=f"Decisionsel{p['id']}")
                note = st.text_area("CA note (required where authority differs or facts are unconfirmed)", p.get("ca_note") or "", key=f"CAnoterequirtex{p['id']}")
                if st.form_submit_button("Record proposition decision", type="primary"):
                    if call("POST", f"/propositions/{p['id']}/decision", json_body={"decision": dec, "note": note}):
                        toast("Decision recorded")
                        st.rerun()
            for h in p.get("verification_history", [])[:5]:
                st.caption(f"{h['decision']} · {h['decided_by_name']} · {h['decided_at'][:16]}" + (f" — {h['note']}" if h.get("note") else ""))


def add_source_form(key: str):
    st.caption("Record the source exactly as published. It starts UNVERIFIED; a CA verifies it against the official text.")
    with st.form(f"as_{key}"):
        c1, c2, c3 = st.columns(3)
        scls = c1.selectbox("Class", SOURCE_CLASSES[:2], help="AI suggestions are recorded automatically from AI replies.")
        stype = c2.selectbox("Type", SOURCE_TYPES)
        act = c3.selectbox("Act / Rules", ACTS)
        title = st.text_input("Title (case name, section heading, circular subject) *")
        citation = st.text_input("Full citation (as reported / as numbered)")
        c4, c5, c6 = st.columns(3)
        body = c4.text_input("Issuing body / court bench")
        court = c5.selectbox("Court level (judgments)", COURTS)
        docno = c6.text_input("Circular / notification number")
        c7, c8, c9 = st.columns(3)
        dated = c7.text_input("Date issued / decided (YYYY-MM-DD)")
        eff_from = c8.text_input("Effective from (YYYY-MM-DD)")
        eff_to = c9.text_input("Effective to (YYYY-MM-DD, blank if in force)")
        c10, c11, c12 = st.columns(3)
        prov = c10.text_input("Section / rule")
        pin = c11.text_input("Relevant paragraph / sub-section")
        ays = c12.text_input("Applies to AYs (e.g. 2026-27 or 2018-19:2025-26)")
        url = st.text_input("Official link (https://…gov.in / …nic.in for primary sources)")
        excerpt = st.text_area("Relevant paragraph or provision text (short)")
        appl = st.text_area("Applicability note (Act, years, transition)")
        if st.form_submit_button("Add source", type="primary"):
            ay_from, _, ay_to = (ays or "").partition(":")
            payload = {"source_class": scls, "source_type": stype, "title": title, "citation": citation or None, "issuing_body": body or None,
                       "court_level": court or None, "document_number": docno or None, "date_issued": dated or None,
                       "effective_from": eff_from or None, "effective_to": eff_to or None, "act": act or None, "provision": prov or None,
                       "pinpoint": pin or None, "excerpt": excerpt or None, "applicability_note": appl or None,
                       "ay_from": ay_from.strip() or None, "ay_to": (ay_to.strip() or ay_from.strip()) or None, "official_url": url or None}
            if call("POST", "/legal-sources", json_body=payload):
                toast("Source added — UNVERIFIED until a CA checks it")
                st.rerun()


# ---------- Steps 6 & 7 ----------
def step_draft(cid):
    t1, t2 = st.tabs(["✍️ Reply draft", "📋 Client information request"])
    with t1:
        T.tab_draft(cid)
    with t2:
        T.tab_client_request(cid)


def step_approve(cid):
    ap = call("GET", f"/cases/{cid}/approval") or {}
    if ap.get("approved"):
        st.success(f"Approved version {ap.get('approved_version') or ap.get('version')} — the approval is tied to this exact text "
                   f"(hash {str(ap.get('content_hash', ''))[:16]}…). Any edit cancels it.")
    for prob in ap.get("problems", []) or []:
        alert(prob, "critical")
    T.tab_review(cid)


# ======================= LEGAL SOURCES LIBRARY =======================
def sources_view():
    hero("Legal sources", "Acts, rules, notifications, circulars and judgments — with citations, links, applicability and CA verification")
    meta = call("GET", "/legal-sources/portals") or {}
    alert(meta.get("disclaimer", ""), "medium")
    allsrc = call("GET", "/legal-sources") or []
    k = st.columns(4)
    kpi(k[0], "Sources", len(allsrc), "in library", "blue")
    kpi(k[1], "Verified", sum(s["effective_status"] == "VERIFIED" for s in allsrc), "usable in replies", "green")
    kpi(k[2], "Need review", sum(s["effective_status"] in ("UNVERIFIED", "NEEDS_CA_REVIEW") for s in allsrc), "not usable yet", "amber")
    kpi(k[3], "Outdated", sum(s["effective_status"] == "OUTDATED" for s in allsrc), "superseded / expired", "red")
    c1, c2, c3 = st.columns(3)
    fcls = c1.selectbox("Class", ["All"] + SOURCE_CLASSES)
    fst = c2.selectbox("Status", ["All", "VERIFIED", "UNVERIFIED", "NEEDS_CA_REVIEW", "OUTDATED"])
    q = c3.text_input("Search title, citation or section")
    params = {k2: v for k2, v in {"source_class": None if fcls == "All" else fcls, "status": None if fst == "All" else fst,
                                  "q": q or None}.items() if v}
    shown = call("GET", "/legal-sources", params=params) or []
    if not shown:
        empty("No sources match", "Add one below. Nothing is pre-loaded as verified.")
    for s in shown[:60]:
        source_card(s, "lib")
    with st.expander("➕ Add a source", expanded=not allsrc):
        add_source_form("lib")
    with st.expander("Official portals to look things up"):
        for pt in meta.get("portals", []):
            st.markdown(f"- {safe_link(pt['url'], pt['name'])}", unsafe_allow_html=True)


# ======================= SETTINGS =======================
def settings_view():
    hero("Settings", "System check, AI drafting, users and security")
    t1, t0, t2, t3, t4 = st.tabs(["🩺 System check", "✍️ AI drafting", "☁️ Cloud AI providers", "👥 Users & security",
                                  "📜 V2 reference registry"])
    with t1:
        system_check()
    with t0:
        ai_drafting_settings()
    with t2:
        T.providers_view()
    with t3:
        T.admin_view()
    with t4:
        st.caption("The older V2 registry is kept for continuity. Its entries were copied into 📚 Legal sources as UNVERIFIED.")
        T.registry_view()


def ai_status_banner(where: str = ""):
    """Says plainly, before drafting, whether AI can write the reply and where the text would go."""
    stt = call("GET", "/ai/drafting-status", quiet=True)
    if not stt:
        return None
    level = "info" if stt["best"] == "local" else ("medium" if stt["best"] else "high")
    alert(("✍️ " if stt["best"] else "⚠️ ") + stt["message"], level)
    return stt


def ai_drafting_settings():
    section("AI on this computer (recommended)")
    st.markdown(
        "NOTICE-MATE can use a model that runs **on this computer**, so case text never leaves it. It works with "
        "**LM Studio** or **Ollama** (both free for Windows). Nothing is downloaded by NOTICE-MATE; you install and load the "
        "model yourself, once.\n\n"
        "**One-time setup with LM Studio**\n"
        "1. Install LM Studio from lmstudio.ai and open it.\n"
        "2. In *Discover*, download an instruction model that fits your computer — for example a 7–8B \"Instruct\" model "
        "(about 5 GB; 16 GB RAM recommended). Larger models write better but are slower.\n"
        "3. Open the *Developer* tab, load the model, and click **Start server** (address `http://127.0.0.1:1234`).\n"
        "4. Come back here, click **Check the local AI**, then switch it on.\n\n"
        "Ollama works the same way: install it, run `ollama pull <model>`, and use the address `http://127.0.0.1:11434/v1`.")
    cur = call("GET", "/settings/app", quiet=True) or {}
    url = st.text_input("Local AI address (must be on this computer)", value=cur.get("local_ai_url") or "http://127.0.0.1:1234/v1",
                        key="lai_url")
    chk = st.session_state.get("lai_check")
    if st.button("🔎 Check the local AI", key="lai_check_btn"):
        chk = call("GET", "/ai/local-check", params={"url": url, "model": cur.get("local_ai_model") or ""})
        st.session_state["lai_check"] = chk
    if chk:
        alert(chk["message"], "info" if chk["ready"] else "high")
        if chk.get("models"):
            cur_m = cur.get("local_ai_model") or chk.get("model") or chk["models"][0]
            model = st.selectbox("Model to use", chk["models"], index=chk["models"].index(cur_m) if cur_m in chk["models"] else 0,
                                 key="lai_model")
            if st.button("Save address and model", key="lai_save"):
                if call("PUT", "/settings/app", json_body={"key": "local_ai_url", "value": url}) and \
                        call("PUT", "/settings/app", json_body={"key": "local_ai_model", "value": model}):
                    st.session_state.pop("lai_check", None)
                    toast("Local AI address and model saved")
                    st.rerun()
    on = (cur.get("local_ai_enabled") == "1")
    st.markdown(f"Local AI drafting: {badge('ON' if on else 'OFF', 'green' if on else 'amber')}", unsafe_allow_html=True)
    if is_ca():
        if not on and st.button("Turn local AI drafting on", type="primary", key="lai_on"):
            if call("PUT", "/settings/app", json_body={"key": "local_ai_enabled", "value": "1"}):
                st.rerun()
        if on and st.button("Turn local AI drafting off", key="lai_off"):
            if call("PUT", "/settings/app", json_body={"key": "local_ai_enabled", "value": "0"}):
                st.rerun()
    section("Status")
    ai_status_banner()
    st.caption("Cloud providers (Anthropic, Gemini) stay optional. They are set up in the .env file on this computer — never "
               "paste an API key into a chat. With a cloud provider, every request is redacted, shown to you, and sent only "
               "after you approve it; the provider may charge for usage.")


def system_check():
    h = call("GET", "/system/ocr-health")
    if h:
        section("Reading scanned documents (OCR)")
        st.markdown(f"Overall: {badge(h['status'])}", unsafe_allow_html=True)
        t, p, s = h["tesseract"], h["poppler"], h["self_test"]
        st.markdown(f"- **Tesseract** {badge('FOUND' if t['found'] else 'MISSING', 'green' if t['found'] else 'red')} "
                    f"version {esc(t['version'] or '—')} · English data {badge('YES' if t['eng_available'] else 'NO', 'green' if t['eng_available'] else 'red')}"
                    f"<div class='nm-muted'>{esc(t['configured_path'])}</div>", unsafe_allow_html=True)
        st.markdown(f"- **Poppler** pdftoppm {badge('YES' if p['pdftoppm_found'] else 'NO', 'green' if p['pdftoppm_found'] else 'red')} "
                    f"pdfinfo {badge('YES' if p['pdfinfo_found'] else 'NO', 'green' if p['pdfinfo_found'] else 'red')}"
                    f"<div class='nm-muted'>{esc(p['configured_path'])}</div>", unsafe_allow_html=True)
        if s["ran"]:
            st.markdown(f"- **Self-test** {badge('PASSED' if s['ok'] else 'FAILED', 'green' if s['ok'] else 'red')} confidence {esc(s['confidence'])}",
                        unsafe_allow_html=True)
        for e in (t.get("error"), p.get("error"), s.get("error")):
            if e:
                alert(e, "high")
        for n, fx in enumerate(h["fixes"], 1):
            alert(f"{n}. {fx}", "medium")
    prov = call("GET", "/ai/providers", quiet=True)
    if prov:
        section("AI")
        ai_status_banner()


def cases_page():
    t1, t2 = st.tabs(["📋 Cases", "📊 Dashboard"])
    with t1:
        T.cases_view()
    with t2:
        T.dashboard_view()


# ======================= MAIN =======================
def main():
    if not st.session_state.get("token"):
        T.login_view()
        return
    user = st.session_state.user
    with st.sidebar:
        st.markdown('<p class="nm-brand">NOTICE<span>·</span>MATE</p><p class="nm-tag">Income-tax notice workbench for CAs · V3</p>',
                    unsafe_allow_html=True)
        st.markdown(f"**{esc(user['full_name'])}** · {esc(user['role'])}", unsafe_allow_html=True)
        if "_goto" in st.session_state:
            st.session_state.nav = st.session_state.pop("_goto")
        if st.session_state.get("nav") not in NAV:
            st.session_state.nav = NAV[0]
        st.radio("Navigate", NAV, key="nav", label_visibility="collapsed")
        st.markdown("---")
        st.caption(DRAFT_BANNER)
        if st.button("Sign out", use_container_width=True):
            call("POST", "/auth/logout", quiet=True)
            st.session_state.clear()
            st.rerun()
    page = st.session_state.nav
    {NAV[0]: home_view, NAV[1]: cases_page, NAV[2]: workspace_view, NAV[3]: sources_view, NAV[4]: settings_view}[page]()


main()
