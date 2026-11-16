from datetime import timedelta

import pandas as pd
import streamlit as st

from core import auth, db, duedates, importer, ui
from core.constants import ENTITY_TYPES, GST_FREQ, STATES

from . import common


def health(row) -> str:
    if row["overdue"] > 0:
        return "🔴 Overdue"
    if row["due7"] > 0:
        return "🟡 Due this week"
    return "🟢 On track"


def render():
    u = common.me()
    managers = auth.sees_all_work(u)
    ui.header("Clients", "Client master, compliance health and a 360° view of each client")

    if managers:
        a, b, c, _ = st.columns([1, 1.25, 1.35, 3])
        if a.button("Add client", icon=":material/person_add:", type="primary"):
            client_dialog(None)
        if b.button("Import from Excel", icon=":material/upload_file:"):
            import_dialog()
        c.download_button("Excel template", importer.client_template, "client_import_template.xlsx",
                          icon=":material/download:")

    today = common.today().isoformat()
    week = (common.today() + timedelta(days=7)).isoformat()
    rows = db.query(
        "SELECT c.*, u.name AS manager, "
        "SUM(CASE WHEN t.status<>'Done' AND t.due_date<:t THEN 1 ELSE 0 END) AS overdue, "
        "SUM(CASE WHEN t.status<>'Done' AND t.due_date>=:t AND t.due_date<=:w THEN 1 ELSE 0 END) AS due7, "
        "SUM(CASE WHEN t.status<>'Done' THEN 1 ELSE 0 END) AS open_tasks "
        "FROM clients c LEFT JOIN users u ON u.id=c.manager_id LEFT JOIN tasks t ON t.client_id=c.id "
        "GROUP BY c.id, u.name ORDER BY c.name", t=today, w=week)
    if not rows:
        common.no_clients_yet()
        return
    df = pd.DataFrame(rows)
    for col in ("overdue", "due7", "open_tasks"):
        df[col] = df[col].fillna(0).astype(int)
    active = df[df["active"] == 1]
    ui.kpis([
        ui.kpi_html("Active clients", len(active), f"{len(df) - len(active)} inactive", ui.NAVY, "👥"),
        ui.kpi_html("GST clients", int((active["gst_freq"] != "None").sum()),
                    f"{int((active['gst_freq'] == 'Monthly').sum())} monthly · "
                    f"{int((active['gst_freq'] == 'Quarterly').sum())} QRMP", ui.TEAL, "🧾"),
        ui.kpi_html("Tax audit clients", int(active["needs_audit"].sum()), "u/s 44AB", "#E11D48", "🔍"),
        ui.kpi_html("Clients with overdue work", int((active["overdue"] > 0).sum()), "see health column",
                    "#DC2626", "⚠️"),
        ui.kpi_html("Monthly retainers", ui.inr(active["monthly_fee"].sum(), short=True), "billing potential",
                    "#6366F1", "💰"),
    ])

    f1, f2, f3 = st.columns([2, 1, 1])
    q = f1.text_input("Search", placeholder="Search name, PAN, GSTIN or contact…", label_visibility="collapsed")
    flt = f2.selectbox("Health", ["All", "🔴 Overdue", "🟡 Due this week", "🟢 On track"], label_visibility="collapsed")
    show_inactive = f3.toggle("Show inactive")
    df["health"] = df.apply(health, axis=1)
    view = df if show_inactive else df[df["active"] == 1]
    if q:
        mask = view[["name", "pan", "gstin", "contact_person"]].fillna("").apply(
            lambda c: c.str.contains(q, case=False, regex=False)).any(axis=1)
        view = view[mask]
    if flt != "All":
        view = view[view["health"] == flt]
    view = view.reset_index(drop=True)
    services = view.apply(lambda r: " · ".join(
        [s for s, on in [(f"GST {r['gst_freq']}", r["gst_freq"] != "None"), ("TDS", r["has_tds"]),
                         ("ITR", r["needs_itr"]), ("Audit", r["needs_audit"])] if on]), axis=1)
    table = pd.DataFrame({"Client": view["name"], "Type": view["entity_type"], "PAN": view["pan"],
                          "GSTIN": view["gstin"], "Services": services if len(view) else [],
                          "Health": view["health"], "Open": view["open_tasks"], "Overdue": view["overdue"],
                          "Manager": view["manager"].fillna("—")})
    st.caption("Tick the box at the start of a row to open that client's 360° view.")
    ev = st.dataframe(table, hide_index=True, width="stretch", height=min(640, 40 + 35 * max(len(table), 1)),
                      on_select="rerun", selection_mode="single-row",
                      column_config={"Overdue": st.column_config.NumberColumn(format="%d"),
                                     "Open": st.column_config.NumberColumn("Open tasks")})
    if ev.selection.rows:
        client_360(int(view.iloc[ev.selection.rows[0]]["id"]))


def client_360(cid: int):
    u = common.me()
    managers = auth.sees_all_work(u)
    c = db.one("SELECT c.*, u.name AS manager FROM clients c LEFT JOIN users u ON u.id=c.manager_id WHERE c.id=:i", i=cid)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        h1, h2 = st.columns([3, 1])
        services = [ui.pill(f"GST {c['gst_freq']}", "teal") if c["gst_freq"] != "None" else "",
                    ui.pill("TDS", "violet") if c["has_tds"] else "", ui.pill("ITR", "indigo") if c["needs_itr"] else "",
                    ui.pill("Tax audit", "rose") if c["needs_audit"] else "",
                    "" if c["active"] else ui.pill("Inactive", "slate")]
        h1.markdown(f"<h3 style='margin:0'>{ui.esc(c['name'])}</h3><div style='color:#64748B;margin:4px 0 8px 0'>"
                    f"{ui.esc(c['entity_type'])} · PAN {ui.esc(c['pan'] or '—')} · GSTIN {ui.esc(c['gstin'] or 'Unregistered')} · "
                    f"{ui.esc(c['state'] or '')}</div>{' '.join(services)}", unsafe_allow_html=True)
        h2.markdown(f"<div style='text-align:right;color:#64748B;font-size:0.85rem'>👤 {ui.esc(c['contact_person'] or '—')}"
                    f"<br/>✉️ {ui.esc(c['email'] or '—')}<br/>📞 {ui.esc(c['phone'] or '—')}<br/>Manager: "
                    f"<b>{ui.esc(c['manager'] or '—')}</b></div>", unsafe_allow_html=True)

        tabs = ["Compliance", "Invoices", "Documents"] + (["Edit", "Manage"] if managers else [])
        t = st.tabs(tabs)
        with t[0]:
            tasks = db.query("SELECT t.title, t.period, t.category, t.due_date, t.status, u.name AS assignee "
                             "FROM tasks t LEFT JOIN users u ON u.id=t.assigned_to WHERE t.client_id=:c "
                             "ORDER BY t.due_date", c=cid)
            if tasks:
                tdf = pd.DataFrame(tasks)
                today = common.today().isoformat()
                pending = tdf[tdf["status"] != "Done"]
                done = len(tdf) - len(pending)
                st.markdown(f"{ui.pill(f'{done}/{len(tdf)} done this FY', 'green')} "
                            f"{ui.pill(str(int((pending['due_date'] < today).sum())) + ' overdue', 'red')}",
                            unsafe_allow_html=True)
                nxt = tdf[(tdf["status"] != "Done")].head(40).copy()
                nxt["due_date"] = pd.to_datetime(nxt["due_date"]).dt.date
                st.dataframe(nxt, hide_index=True, width="stretch",
                             column_config={"title": "Compliance", "period": "Period", "category": "Area",
                                            "due_date": st.column_config.DateColumn("Due", format="DD MMM YYYY"),
                                            "status": "Status", "assignee": "Assigned to"})
            else:
                st.caption("No compliance tasks. Tick the client's services under Edit.")
        with t[1]:
            invs = db.query("SELECT invoice_no, invoice_date, description, total, status FROM invoices "
                            "WHERE client_id=:c ORDER BY invoice_date DESC", c=cid)
            if invs:
                idf = pd.DataFrame(invs)
                st.markdown(f"Billed {ui.inr(idf['total'].sum())} · Outstanding "
                            f"**{ui.inr(idf[idf['status'] == 'Unpaid']['total'].sum())}**")
                st.dataframe(idf, hide_index=True, width="stretch",
                             column_config={"total": st.column_config.NumberColumn("Total", format="₹ %.2f")})
            else:
                st.caption("No invoices yet.")
        with t[2]:
            docs = db.query("SELECT filename, category, fin_year, uploaded_on FROM documents WHERE client_id=:c "
                            "ORDER BY uploaded_on DESC", c=cid)
            st.dataframe(pd.DataFrame(docs), hide_index=True, width="stretch") if docs else \
                st.caption("No documents. Upload them from the Documents page.")
        if managers:
            with t[3]:
                client_form(c)
            with t[4]:
                manage(c)


def client_form(c: dict | None):
    """Add (c=None) or edit a client."""
    staff = common.users()
    c = c or {}
    key = f"cf_{c.get('id', 'new')}"
    with st.form(key):
        a, b = st.columns(2)
        name = a.text_input("Client name *", c.get("name", ""))
        etype = b.selectbox("Entity type", ENTITY_TYPES, index=ENTITY_TYPES.index(c.get("entity_type") or "Individual"))
        pan = a.text_input("PAN", c.get("pan") or "", max_chars=10).upper().strip()
        gstin = b.text_input("GSTIN", c.get("gstin") or "", max_chars=15).upper().strip()
        state = a.selectbox("State", STATES, index=STATES.index(c.get("state") or "Gujarat"))
        ids = [None] + list(staff)
        mgr = b.selectbox("Engagement manager", ids, index=ids.index(c.get("manager_id")) if c.get("manager_id") in ids else 0,
                          format_func=lambda i: staff.get(i, "—"), help="New statutory tasks are assigned to this person")
        contact = a.text_input("Contact person", c.get("contact_person") or "")
        email = b.text_input("Email", c.get("email") or "")
        phone = a.text_input("Phone", c.get("phone") or "")
        fee = b.number_input("Monthly retainer (₹, excl. GST)", min_value=0.0, step=500.0, value=float(c.get("monthly_fee") or 0))
        st.markdown("**Services**")
        s1, s2, s3, s4 = st.columns(4)
        gst = s1.selectbox("GST returns", GST_FREQ, index=GST_FREQ.index(c.get("gst_freq") or "None"))
        tds = s2.toggle("TDS", bool(c.get("has_tds")))
        itr = s3.toggle("Income tax return", bool(c.get("needs_itr", 1)))
        aud = s4.toggle("Tax audit (44AB)", bool(c.get("needs_audit")))
        if st.form_submit_button("Save client", type="primary"):
            if not name.strip():
                st.error("Client name is required."); return
            if pan and not importer.PAN_RE.match(pan):
                st.error("PAN should look like ABCDE1234F."); return
            if gstin and not importer.GSTIN_RE.match(gstin):
                st.error("GSTIN should be 15 characters, e.g. 24ABCDE1234F1Z5."); return
            if pan and gstin and gstin[2:12] != pan:
                st.error("GSTIN characters 3–12 should be the PAN."); return
            dup = db.one("SELECT id FROM clients WHERE pan=:p AND pan<>'' AND id<>:i", p=pan, i=c.get("id", 0))
            if pan and dup:
                st.error("Another client already has this PAN."); return
            vals = dict(n=name.strip(), e=etype, pan=pan, g=gstin, s=state, cp=contact, em=email, ph=phone, gf=gst,
                        tds=int(tds), itr=int(itr), aud=int(aud), fee=fee, m=mgr)
            fy = duedates.current_fy_start()
            if c.get("id"):
                db.execute("UPDATE clients SET name=:n, entity_type=:e, pan=:pan, gstin=:g, state=:s, contact_person=:cp, "
                           "email=:em, phone=:ph, gst_freq=:gf, has_tds=:tds, needs_itr=:itr, needs_audit=:aud, "
                           "monthly_fee=:fee, manager_id=:m WHERE id=:id", id=c["id"], **vals)
                added, removed = duedates.sync_client(db.one("SELECT * FROM clients WHERE id=:i", i=c["id"]), fy)
                st.success(f"Saved. {added} task(s) added, {removed} not-started task(s) removed.")
            else:
                cid = db.insert("INSERT INTO clients(name,entity_type,pan,gstin,state,contact_person,email,phone,gst_freq,"
                                "has_tds,needs_itr,needs_audit,monthly_fee,manager_id,created_on) VALUES "
                                "(:n,:e,:pan,:g,:s,:cp,:em,:ph,:gf,:tds,:itr,:aud,:fee,:m,:c) RETURNING id",
                                c=db.now(), **vals)
                n = duedates.generate_for_client(db.one("SELECT * FROM clients WHERE id=:i", i=cid), fy)
                st.success(f"Client added with {n} statutory tasks for FY {duedates.fy_label(fy)}.")
                st.rerun()


def manage(c):
    u = common.me()
    if c["active"]:
        st.write("Mark the client inactive when the engagement ends. History stays; open tasks are hidden.")
        if st.button("Mark inactive", icon=":material/pause_circle:"):
            db.execute("UPDATE clients SET active=0 WHERE id=:i", i=c["id"]); st.rerun()
    elif st.button("Reactivate", icon=":material/play_circle:"):
        db.execute("UPDATE clients SET active=1 WHERE id=:i", i=c["id"]); st.rerun()
    if u["role"] == "Partner":
        st.divider()
        st.markdown("**Delete permanently** (removes tasks, invoices and documents)")
        sure = st.text_input("Type the client name to confirm", key=f"del_{c['id']}")
        if st.button("Delete client", type="primary", disabled=sure.strip() != c["name"]):
            db.execute("DELETE FROM clients WHERE id=:i", i=c["id"]); st.rerun()


@st.dialog("Add client", width="large")
def client_dialog(_):
    client_form(None)


@st.dialog("Import clients from Excel", width="large")
def import_dialog():
    st.markdown("1. Download the **Excel template** (button next to Import).  \n"
                "2. Fill one client per row (drop-downs help).  \n3. Upload it here, check the preview, then import.")
    f = st.file_uploader("Filled template (.xlsx)", type=["xlsx"])
    if not f:
        return
    try:
        prev = importer.parse_clients(f)
    except Exception as e:
        st.error(str(e)); return
    ok = prev[prev["Issues"] == ""]
    bad = prev[prev["Issues"] != ""]
    st.markdown(f"{ui.pill(f'{len(ok)} ready', 'green')} {ui.pill(f'{len(bad)} with problems', 'red' if len(bad) else 'slate')}",
                unsafe_allow_html=True)
    st.dataframe(prev, hide_index=True, width="stretch", height=260)
    if len(bad):
        st.caption("Rows with problems will be skipped. Fix them in Excel and import again.")
    staff = common.users()
    mgr = st.selectbox("Engagement manager for these clients", [None] + list(staff), format_func=lambda i: staff.get(i, "—"))
    if st.button(f"Import {len(ok)} client(s)", type="primary", disabled=len(ok) == 0):
        n, t = importer.import_clients(prev, mgr)
        st.success(f"Imported {n} clients and created {t} statutory tasks.")
        st.rerun()
