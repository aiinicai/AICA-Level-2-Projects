from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core import db, duedates, invoice_pdf, ui

from . import common


def render():
    ui.header("Billing", "GST invoices, collections and receivables ageing")
    if not common.clients():
        common.no_clients_yet()
        return
    today = common.today()
    fy0 = duedates.current_fy_start()
    fy_start, fy_end = date(fy0, 4, 1).isoformat(), date(fy0 + 1, 3, 31).isoformat()
    invs = db.query("SELECT i.*, c.name AS client FROM invoices i JOIN clients c ON c.id=i.client_id "
                    "ORDER BY i.invoice_date DESC, i.id DESC")
    df = pd.DataFrame(invs)
    if not df.empty:
        fy_df = df[(df["invoice_date"] >= fy_start) & (df["invoice_date"] <= fy_end)]
        unpaid = df[df["status"] == "Unpaid"]
        late = unpaid[unpaid["due_date"] < today.isoformat()]
        ui.kpis([
            ui.kpi_html("Billed this FY", ui.inr(fy_df["taxable_value"].sum(), True), "excluding GST", ui.NAVY, "🧾"),
            ui.kpi_html("Collected this FY", ui.inr(fy_df[fy_df["status"] == "Paid"]["total"].sum(), True),
                        "including GST", "#16A34A", "✅"),
            ui.kpi_html("Outstanding", ui.inr(unpaid["total"].sum(), True), f"{len(unpaid)} invoices", "#6366F1", "💰"),
            ui.kpi_html("Overdue receivables", ui.inr(late["total"].sum(), True), f"{len(late)} past credit period",
                        "#DC2626", "⏰"),
        ])

    a, b, _ = st.columns([1, 1.6, 3])
    if a.button("New invoice", icon=":material/add:", type="primary"):
        invoice_dialog()
    if b.button(f"Raise {today.strftime('%B')} retainer invoices", icon=":material/bolt:"):
        bulk_retainers()

    if df.empty:
        st.markdown(ui.empty("No invoices yet"), unsafe_allow_html=True)
        return

    left, right = st.columns([2.2, 1], gap="medium")
    with right:
        unpaid = df[df["status"] == "Unpaid"].copy()
        unpaid["age"] = unpaid["due_date"].map(lambda d: (today - date.fromisoformat(d)).days if d else 0)
        buckets = [("Not yet due", unpaid[unpaid["age"] <= 0]), ("1–30 days late", unpaid[(unpaid["age"] > 0) & (unpaid["age"] <= 30)]),
                   ("31–60 days late", unpaid[(unpaid["age"] > 30) & (unpaid["age"] <= 60)]), ("60+ days late", unpaid[unpaid["age"] > 60])]
        total = unpaid["total"].sum() or 1
        colors = [ui.TEAL, "#F59E0B", "#F97316", "#DC2626"]
        body = "".join(f'<div style="margin:10px 0"><div style="display:flex;justify-content:space-between;font-size:0.85rem">'
                       f'<span>{lbl}</span><b>{ui.inr(b["total"].sum())}</b></div>{ui.bar(100 * b["total"].sum() / total, col)}</div>'
                       for (lbl, b), col in zip(buckets, colors))
        ui.card("Receivables ageing", body)
        top = unpaid.groupby("client")["total"].sum().sort_values(ascending=False).head(5)
        ui.card("Top outstanding clients", "".join(
            f'<div class="pm-row">{ui.avatar(cname, 28)}<div class="main"><div class="t1">{ui.esc(cname)}</div></div>'
            f'<b>{ui.inr(v)}</b></div>' for cname, v in top.items()) or ui.empty("All paid up"))
    with left:
        flt = st.segmented_control("Show", ["All", "Unpaid", "Overdue", "Paid"], default="All",
                                   label_visibility="collapsed") or "All"
        q = st.text_input("Search invoices", placeholder="Client or invoice no…", label_visibility="collapsed")
        shown = 0
        for inv in invs:
            overdue = inv["status"] == "Unpaid" and (inv["due_date"] or "9") < today.isoformat()
            if (flt == "Unpaid" and inv["status"] != "Unpaid") or (flt == "Paid" and inv["status"] != "Paid") \
                    or (flt == "Overdue" and not overdue):
                continue
            if q and q.lower() not in (inv["client"] + inv["invoice_no"]).lower():
                continue
            shown += 1
            if shown > 40:
                st.caption("Showing the latest 40. Use search to find older invoices."); break
            tone, label = ("green", "Paid") if inv["status"] == "Paid" else ("red", "Overdue") if overdue else ("amber", "Unpaid")
            with st.container(border=True, key=f"inv-{inv['id']}"):
                c1, c2, c3, c4 = st.columns([3, 1.4, 1.1, 1.2], vertical_alignment="center")
                c1.markdown(f"**{ui.esc(inv['client'])}**  \n<span style='color:#64748B;font-size:0.82rem'>"
                            f"{inv['invoice_no']} · {date.fromisoformat(inv['invoice_date']).strftime('%d %b %Y')} · "
                            f"{ui.esc(inv['description'])}</span>", unsafe_allow_html=True)
                c2.markdown(f"<div style='font-weight:800;color:#0B1F3A;font-size:1.05rem'>{ui.inr(inv['total'])}</div>"
                            f"<div style='color:#64748B;font-size:0.75rem'>{'IGST' if inv['igst'] else 'CGST + SGST'}</div>",
                            unsafe_allow_html=True)
                c3.markdown(ui.pill(label, tone), unsafe_allow_html=True)
                with c4:
                    st.download_button("PDF", lambda inv=inv: invoice_pdf.build_pdf(
                                           inv, db.one("SELECT * FROM clients WHERE id=:i", i=inv["client_id"])),
                                       f"{inv['invoice_no'].replace('/', '_')}.pdf",
                                       mime="application/pdf", key=f"pdf{inv['id']}", icon=":material/download:", width="stretch")
                    if inv["status"] == "Unpaid" and st.button("Mark paid", key=f"pd{inv['id']}", width="stretch"):
                        db.execute("UPDATE invoices SET status='Paid', paid_on=:d WHERE id=:i", d=today.isoformat(), i=inv["id"])
                        st.rerun()


@st.dialog("New GST invoice", width="large")
def invoice_dialog():
    cm = common.clients()
    firm = invoice_pdf.firm()
    cid = st.selectbox("Client", list(cm), format_func=lambda i: cm[i])
    client = db.one("SELECT * FROM clients WHERE id=:i", i=cid)
    a, b = st.columns(2)
    service = a.selectbox("Service", list(invoice_pdf.SAC_OPTIONS))
    desc = b.text_input("Description", f"{service} — {common.today().strftime('%B %Y')}")
    c, d, e = st.columns(3)
    amt = c.number_input("Fees (₹, excl. GST)", min_value=0.0, step=500.0, value=float(client["monthly_fee"] or 0))
    rate = d.selectbox("GST rate", [18.0, 0.0], format_func=lambda r: f"{r:g}%")
    days = e.number_input("Credit days", 0, 90, 15)
    g = invoice_pdf.compute_gst(amt, rate, client["state"], firm["firm_state"])
    split = (f"IGST {ui.inr(g['igst'])} (inter-state: client in {client['state']})" if g["igst"]
             else f"CGST {ui.inr(g['cgst'])} + SGST {ui.inr(g['sgst'])} (intra-state)")
    st.markdown(f"<div class='pm-card' style='margin-top:6px'>Taxable {ui.inr(amt)} · {split}<br/>"
                f"<span style='font-size:1.3rem;font-weight:800;color:#0B1F3A'>Total {ui.inr(g['total'])}</span><br/>"
                f"<span style='color:#64748B;font-size:0.8rem'>{invoice_pdf.amount_in_words(g['total'])}</span></div>",
                unsafe_allow_html=True)
    if st.button("Create invoice", type="primary", disabled=amt <= 0):
        create_invoice(client, amt, rate, desc, invoice_pdf.SAC_OPTIONS[service], days)
        st.rerun()


def create_invoice(client, amt, rate, desc, sac, days):
    firm = invoice_pdf.firm()
    g = invoice_pdf.compute_gst(amt, rate, client["state"], firm["firm_state"])
    today = common.today()
    no = invoice_pdf.next_invoice_no(duedates.fy_label(duedates.current_fy_start(today)))
    db.execute("INSERT INTO invoices(invoice_no,client_id,invoice_date,due_date,description,sac,taxable_value,gst_rate,"
               "cgst,sgst,igst,total,created_by) VALUES (:no,:c,:d,:dd,:desc,:sac,:amt,:r,:cg,:sg,:ig,:t,:by)",
               no=no, c=client["id"], d=today.isoformat(), dd=(today + timedelta(days=int(days))).isoformat(),
               desc=desc, sac=sac, amt=amt, r=rate, cg=g["cgst"], sg=g["sgst"], ig=g["igst"], t=g["total"],
               by=common.me()["id"])
    return no


def bulk_retainers():
    today = common.today()
    label = f"Monthly compliance retainer — {today.strftime('%B %Y')}"
    made = 0
    for c in db.query("SELECT * FROM clients WHERE active=1 AND monthly_fee>0"):
        if db.one("SELECT id FROM invoices WHERE client_id=:c AND description=:d", c=c["id"], d=label):
            continue
        create_invoice(c, c["monthly_fee"], 18.0, label, "998231", 15)
        made += 1
    st.toast(f"{made} retainer invoice(s) raised" if made else "Retainer invoices for this month already exist")
