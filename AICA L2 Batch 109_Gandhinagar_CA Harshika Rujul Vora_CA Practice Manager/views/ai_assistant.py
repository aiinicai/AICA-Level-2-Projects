"""AI Assistant page: ask about the practice, draft client reminders, read tax notices."""
import urllib.parse
from datetime import date, timedelta

import streamlit as st

from core import ai, auth, db, ui
from core.constants import CATEGORIES

from . import common

QUESTIONS = [
    "What is overdue right now, and who is handling it?",
    "Which statutory deadlines fall in the next 7 days?",
    "Plan my day: what should I finish first and why?",
    "Which clients owe us the most fees?",
    "Which team member has the heaviest workload?",
]
LANGS = ["English", "Hindi", "Gujarati", "Marathi"]


def render():
    u = common.me()
    ui.header("AI Assistant", f"Google Gemini ({ai.model()}) · client names, PAN, GSTIN and contact details are "
                              "masked before anything is sent")
    if not ai.enabled():
        setup_card(u)
        return
    t1, t2, t3 = st.tabs(["Ask about your practice", "Client reminder", "Notice reader"])
    with t1:
        ask_tab(u)
    with t2:
        reminder_tab(u)
    with t3:
        notice_tab(u)


def setup_card(u):
    if auth.can(u, "settings"):
        st.info("The AI Assistant needs a free Google Gemini API key. Get one at **aistudio.google.com** → "
                "**Get API key** (sign in with any Google account, no payment needed), then paste it in "
                "**Settings → AI assistant**.", icon=":material/key:")
    else:
        st.info("The AI Assistant hasn't been switched on yet. Ask a Partner to add the Gemini API key in "
                "Settings → AI assistant.", icon=":material/key:")


def sent_box(sent: str, leaks: list):
    with st.expander("What was sent to the AI (masked)", icon=":material/visibility:"):
        if leaks:
            st.error("Some identifiers were not masked: " + ", ".join(sorted(set(leaks)))[:300])
        else:
            st.caption("No client names, staff names, PAN, GSTIN, Aadhaar, phone numbers or e-mails were sent.")
        st.text(sent[:6000] + ("\n…" if len(sent) > 6000 else ""))


def ai_call(fn, *args, **kwargs):
    try:
        with st.spinner("Thinking…"):
            return fn(*args, **kwargs)
    except ai.AIError as e:
        st.error(str(e), icon=":material/error:")
        return None


# ------------------------------------------------------------------ ask
def ask_tab(u):
    st.caption("Answers come from your firm's live data: tasks, due dates, invoices and team workload"
               + ("." if auth.sees_all_work(u) else " (your own tasks only)."))
    pick = st.pills("Try", QUESTIONS if auth.sees_all_work(u) else [q for q in QUESTIONS if "fees" not in q and
                                                                     "team member" not in q],
                    label_visibility="collapsed", key="ai_pick")
    q = st.text_area("Your question", value=pick or "", height=80, key=f"ai_q_{pick}",
                     placeholder="e.g. Which GSTR-3B returns are still pending for October?")
    if st.button("Ask", type="primary", icon=":material/auto_awesome:"):
        if not q.strip():
            st.warning("Type a question first.")
        else:
            res = ai_call(ai.ask, u, q.strip())
            if res:
                st.session_state.setdefault("ai_history", []).insert(0, {"q": q.strip(), **res})
    for i, h in enumerate(st.session_state.get("ai_history", [])[:5]):
        with st.container(border=True, key=f"aians-{i}"):
            st.markdown(f"**{ui.esc(h['q'])}**")
            st.markdown(h["answer"])
            sent_box(h["sent"], h["leaks"])


# ------------------------------------------------------------------ reminder
def reminder_tab(u):
    cm = common.clients()
    if not cm:
        common.no_clients_yet()
        return
    st.caption("Drafts a reminder listing the client's pending compliances, the documents needed and the due dates.")
    a, b, c, d = st.columns([2, 1, 1, 1])
    cid = a.selectbox("Client", list(cm), format_func=lambda i: cm[i], key="rem_client")
    channel = b.segmented_control("Channel", ["WhatsApp", "Email"], default="WhatsApp", key="rem_ch") or "WhatsApp"
    lang = c.selectbox("Language", LANGS, key="rem_lang")
    tone = d.selectbox("Tone", ["Polite", "Friendly", "Firm (overdue)"], key="rem_tone")
    extra = st.text_input("Anything to add (optional)", placeholder="e.g. Also ask for the Q2 TDS challans",
                          key="rem_extra")
    if st.button("Draft reminder", type="primary", icon=":material/edit_note:"):
        res = ai_call(ai.client_reminder, u, cid, channel, lang, tone, extra)
        if res:
            st.session_state.reminder = {"cid": cid, "channel": channel, **res}
    r = st.session_state.get("reminder")
    if r and r["cid"] == cid:
        client = db.one("SELECT name, phone, email FROM clients WHERE id=:i", i=cid)
        text = st.text_area("Draft (edit before sending)", r["draft"], height=260, key=f"rem_text_{cid}")
        c1, c2, _ = st.columns([1.3, 1.3, 3])
        if r["channel"] == "WhatsApp":
            phone = "".join(ch for ch in (client["phone"] or "") if ch.isdigit())
            if phone:
                phone = phone if len(phone) > 10 else "91" + phone
                c1.link_button("Open in WhatsApp", f"https://wa.me/{phone}?text={urllib.parse.quote(text)}",
                               icon=":material/chat:")
            else:
                c1.caption("No phone number on file for this client.")
        else:
            lines = text.strip().splitlines()
            subject = lines[0].replace("Subject:", "").strip() if lines and lines[0].lower().startswith("subject") else "Pending compliances"
            body = "\n".join(lines[1:]).strip() if subject != "Pending compliances" else text
            c1.link_button("Open in email", f"mailto:{client['email'] or ''}?subject={urllib.parse.quote(subject)}"
                                            f"&body={urllib.parse.quote(body)}", icon=":material/mail:")
        c2.download_button("Save as text", text, f"reminder_{cid}.txt", icon=":material/download:")
        st.caption("AI drafts can be wrong. Check the dates and the list before sending.")
        sent_box(r["sent"], r["leaks"])


# ------------------------------------------------------------------ notice
def notice_tab(u):
    cm = common.clients()
    st.caption("Upload or paste a GST / Income Tax / TDS notice. The app masks identifiers on this computer, "
               "shows you the exact text that will be sent, and only sends it after you confirm.")
    a, b = st.columns([1.2, 1])
    cid = a.selectbox("Which client is this notice for?", [0] + list(cm),
                      format_func=lambda i: "Not linked to a client" if i == 0 else cm[i], key="nt_client")
    others = b.text_input("Other names to hide (comma-separated)", placeholder="e.g. proprietor's name, officer's name",
                          key="nt_others")
    f = st.file_uploader("Notice (PDF or text file)", type=["pdf", "txt"], key="nt_file")
    pasted = st.text_area("…or paste the notice text", height=110, key="nt_paste")
    if st.button("Prepare for the AI", icon=":material/shield_lock:"):
        try:
            raw = ai.extract_text(f.name, f.getvalue()) if f else pasted
        except ai.AIError as e:
            st.error(str(e))
            raw = ""
        if raw.strip():
            m = ai.Masker(extra_names=[n.strip() for n in others.split(",")])
            st.session_state.notice = {"cid": cid, "masked": m.mask(raw)[:ai.MAX_DOC_CHARS],
                                       "leaks": m.leaks(m.mask(raw)), "back": m.back, "analysis": None, "reply": None}
        elif not f:
            st.warning("Upload a file or paste the notice text first.")
    n = st.session_state.get("notice")
    if not n:
        return
    st.markdown("##### 1. Review what will be sent")
    if n["leaks"]:
        st.warning("These still look like identifiers: " + ", ".join(sorted(set(n["leaks"])))[:300])
    n["masked"] = st.text_area("Masked notice text: remove anything else confidential before sending",
                               n["masked"], height=220, key="nt_masked")
    ok = st.checkbox("I have reviewed this text and it contains no confidential client information. Send it to "
                     "Google Gemini for analysis.", key="nt_consent")
    if st.button("Analyse notice", type="primary", disabled=not ok, icon=":material/auto_awesome:"):
        res = ai_call(ai.analyse_notice, u, n["masked"])
        if res:
            n["analysis"], n["reply"] = res, None
    an = n.get("analysis")
    if not an:
        return
    unmask = _unmasker(n["back"])
    st.markdown("##### 2. What the notice says")
    risk_tone = {"High": "#DC2626", "Medium": "#F59E0B", "Low": "#16A34A"}.get(an["risk_level"], ui.NAVY)
    ui.kpis([ui.kpi_html("Notice", an["notice_type"] or "—", an["law"] or "", ui.NAVY),
             ui.kpi_html("Section", an["section"] or "—", an["period"] or "", ui.TEAL),
             ui.kpi_html("Reply due", _fmt(an["reply_due_date"]) or "Not stated", "check the notice", "#F59E0B"),
             ui.kpi_html("Amount involved", ui.inr(an["amount_involved"], True) if an["amount_involved"] else "—",
                         "as read by AI", "#6366F1"),
             ui.kpi_html("Risk", an["risk_level"] or "—", "AI assessment", risk_tone)])
    with st.container(border=True):
        st.markdown(unmask(an["summary"]))
        c1, c2, c3 = st.columns(3)
        for col, title, items in [(c1, "Issues raised", an["issues"]), (c2, "Documents needed", an["documents_needed"]),
                                  (c3, "Points for the reply", an["reply_points"])]:
            col.markdown(f"**{title}**")
            col.markdown("\n".join(f"- {unmask(str(x))}" for x in items) or "—")
        if an.get("confidence_note"):
            st.caption("AI note: " + unmask(an["confidence_note"]))
    st.markdown("##### 3. Act on it")
    t1, t2 = st.columns(2)
    with t1, st.container(border=True):
        st.markdown("**Add a task to the board**")
        if not n["cid"]:
            st.caption("Pick the client at the top to create a task.")
        else:
            due_default = _parse(an["reply_due_date"]) or (common.today() + timedelta(days=7))
            title = st.text_input("Task", f"Reply to {an['notice_type'] or 'notice'}"
                                          f"{(' u/s ' + an['section']) if an['section'] else ''}"
                                          f"{(' (' + an['period'] + ')') if an['period'] else ''}", key="nt_title")
            x, y = st.columns(2)
            due = x.date_input("Due date", due_default, format="DD/MM/YYYY", key="nt_due")
            cat = y.selectbox("Area", CATEGORIES, index=CATEGORIES.index(an["law"]) if an["law"] in CATEGORIES else 4,
                              key="nt_cat")
            if st.button("Create task", type="primary", key="nt_create"):
                notes = unmask(an["summary"]) + "\n\nDocuments needed:\n" + "\n".join(
                    f"- {unmask(str(x))}" for x in an["documents_needed"])
                tid = db.insert("INSERT INTO tasks(client_id,title,category,period,due_date,priority,assigned_to,notes,"
                                "updated_on) VALUES (:c,:t,:cat,:p,:d,'High',:a,:n,:u) RETURNING id",
                                c=n["cid"], t=title, cat=cat, p=due.strftime("%b-%Y"), d=due.isoformat(),
                                a=u["id"], n=notes, u=db.now())
                db.log(tid, u["id"], "Created", "from AI notice reader")
                st.success("Task added to the Task Board (High priority, assigned to you).")
    with t2, st.container(border=True):
        st.markdown("**Draft a reply**")
        pts = st.text_area("Your points for the reply (optional)", height=90, key="nt_points",
                           placeholder="e.g. Difference is due to ITC of March 2025 claimed in April 2025; "
                                       "challan copy attached")
        if st.button("Draft reply", key="nt_draft", icon=":material/description:"):
            masker = ai.Masker()
            masker.back.update(n["back"])
            draft = ai_call(ai.draft_notice_reply, u, n["masked"], an, masker.mask(pts))
            if draft:
                n["reply"] = unmask(draft)
    if n.get("reply"):
        reply = st.text_area("Draft reply (review with the engagement partner before filing)", n["reply"],
                             height=360, key="nt_reply_text")
        st.download_button("Save draft reply", reply, "notice_reply_draft.txt", icon=":material/download:")


def _unmasker(back: dict):
    def f(text: str) -> str:
        for tok in sorted(back, key=len, reverse=True):
            text = text.replace(tok, back[tok])
        return text
    return f


def _parse(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError):
        return None


def _fmt(s):
    d = _parse(s)
    return d.strftime("%d %b %Y") if d else ""
