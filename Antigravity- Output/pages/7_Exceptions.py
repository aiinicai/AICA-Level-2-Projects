"""
Page 7: Exceptions & Claim Workflow (pages/7_Exceptions.py)
Exceptions management:
- Flagged financial discrepancies with recoverable amount
- Status lifecycle: Open -> Claimed -> Recovered with audit notes
- 'Draft claim email' generator using a fixed seller support template
- Local persistence in SQLite
"""
import streamlit as st
import pandas as pd
from decimal import Decimal

from core.session import init_session_state
from core.formatting import format_inr
from core.exceptions import generate_claim_email, EXCEPTION_STATUSES
from core.db import get_all_exceptions, update_exception_status, get_all_settings

init_session_state()
settings = get_all_settings()

st.title("🚨 Exceptions & Claims Management")
st.markdown("Track unresolved disputes, audit short-paid orders, update recovery statuses, and draft claims for Amazon Seller Support.")

# Fetch stored exceptions from SQLite
all_exceptions = get_all_exceptions()

if not all_exceptions:
    st.info("No actionable exceptions currently logged. Reconcile reports or load demo data.")
    st.stop()

# Metrics
total_recoverable = sum(r["recoverable_amount"] for r in all_exceptions if r["status"] in ("Open", "Claimed"))
open_count = sum(1 for r in all_exceptions if r["status"] == "Open")
claimed_count = sum(1 for r in all_exceptions if r["status"] == "Claimed")
recovered_count = sum(1 for r in all_exceptions if r["status"] == "Recovered")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Recoverable Amount", format_inr(total_recoverable))
c2.metric("Open Exceptions", open_count)
c3.metric("Under Claim", claimed_count)
c4.metric("Recovered", recovered_count)

st.markdown("---")

# Filter Controls
col_f1, col_f2 = st.columns([1, 3])
with col_f1:
    status_filter = st.selectbox("Status Filter", ["All", "Open", "Claimed", "Recovered"], index=0)

filtered_exceptions = all_exceptions
if status_filter != "All":
    filtered_exceptions = [e for e in all_exceptions if e["status"] == status_filter]

# Display Table
tbl_exc = []
for e in filtered_exceptions:
    tbl_exc.append({
        "ID": e["id"],
        "Order ID": e["order_id"],
        "Invoice No": e.get("invoice_no") or "N/A",
        "Reason Code": e["reason_code"],
        "Description": e["description"],
        "Recoverable Amount": format_inr(e["recoverable_amount"]),
        "Status": e["status"],
        "Notes": e.get("notes") or "",
        "Updated At": e["updated_at"]
    })

df_exc = pd.DataFrame(tbl_exc)
st.dataframe(df_exc, use_container_width=True, hide_index=True)

st.markdown("---")

# Action Drawer: Update Status & Draft Claim Email
st.subheader("📝 Action Drawer & Seller Support Claim Email")

selected_exc_id = st.selectbox(
    "Select Exception to Update Status or Draft Claim:",
    [e["id"] for e in filtered_exceptions],
    index=0 if filtered_exceptions else None
)

if selected_exc_id:
    exc = next((e for e in filtered_exceptions if e["id"] == selected_exc_id), None)
    if exc:
        st.markdown(f"#### Exception `{exc['id']}` - Order `{exc['order_id']}`")
        col_m1, col_m2 = st.columns(2)
        col_m1.write(f"**Discrepancy:** {exc['description']}")
        col_m2.write(f"**Recoverable Balance:** `{format_inr(exc['recoverable_amount'])}`")

        # Status Update Form
        with st.form(f"form_status_{exc['id']}"):
            col_u1, col_u2 = st.columns([1, 2])
            with col_u1:
                new_status = st.selectbox("Update Status", EXCEPTION_STATUSES, index=EXCEPTION_STATUSES.index(exc["status"]))
            with col_u2:
                new_notes = st.text_input("Audit Notes / Amazon Case ID", value=exc.get("notes") or "")

            btn_update = st.form_submit_button("Save Status & Notes")
            if btn_update:
                update_exception_status(exc["id"], new_status, new_notes)
                st.success(f"Exception {exc['id']} updated to '{new_status}'!")
                st.rerun()

        # Draft Claim Email
        st.markdown("##### ✉️ Amazon Seller Support Dispute Email Draft")
        email_body = generate_claim_email(
            seller_name=settings["seller_name"],
            seller_gstin=settings["seller_gstin"],
            order_id=exc["order_id"],
            invoice_no=exc.get("invoice_no") or "",
            reason_code=exc["reason_code"],
            claim_amount=Decimal(str(exc["recoverable_amount"])),
            details=exc["description"],
            as_of=settings["as_of_date"]
        )

        st.text_area("Dispute Email Draft (Copy & Send via Seller Central):", value=email_body, height=320)
        st.download_button(
            "Download Claim Draft (.txt)",
            data=email_body,
            file_name=f"Claim_Order_{exc['order_id']}.txt",
            mime="text/plain"
        )

st.markdown("<br><hr><small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
