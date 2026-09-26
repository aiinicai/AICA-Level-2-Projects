"""
AuditVault - Guided Interactive Product Tour
Tailored per user role (Admin, Manager, Engagement Team Member).
Can be dismissed, stepped through, or relaunched anytime.
"""

import streamlit as st

def render_guided_tour():
    """Display interactive guided tour card if active in session state."""
    if not st.session_state.get("show_tour", False):
        return

    role = st.session_state.get("role", "Team Member")
    name = st.session_state.get("name", "Auditor")

    tour_steps = {
        "Admin": [
            {
                "title": "Welcome to AuditVault Administration",
                "content": f"Hello {name}! As an Administrator, your primary responsibility is maintaining user accounts, security policies, and team credentials.",
                "highlight": "Admin Panel: Create new Managers and Auditors, reset forgotten passwords, and view system health."
            },
            {
                "title": "Impersonate / Switch User Feature",
                "content": "Need to support an auditor or manager? Use the 'Switch User' button to log in as any user without credentials. Every single impersonation action is permanently recorded in the immutable audit trail with your true identity.",
                "highlight": "Security Rule: Admins cannot directly create engagements or RCMs; workflows must be initiated by Audit Managers."
            },
            {
                "title": "Immutable Audit Trail Monitoring",
                "content": "AuditVault maintains a tamper-proof log of every file upload, status update, login, and manager lock. Logs cannot be modified or purged by any user.",
                "highlight": "Audit Trail: Access from the sidebar anytime to inspect chronological activity across the firm."
            }
        ],
        "Manager": [
            {
                "title": "Welcome, Audit Manager",
                "content": f"Welcome {name}! AuditVault empowers you to direct multiple audit engagements, manage risk control matrices, and supervise teams with total version control.",
                "highlight": "Dashboard: Live view of all active engagements, completion percentages, and overdue alerts."
            },
            {
                "title": "Engagement & Team Setup",
                "content": "Start an audit by clicking 'New Engagement'. Upload the signed Engagement Letter, set Indian audit periods (DD-MM-YYYY), define scope, and assign cross-functional teams.",
                "highlight": "Client & Team Management: Group your team members into Team 1, Team 2, etc. and reassign dynamically."
            },
            {
                "title": "IDR, RCM & Manager Override Controls",
                "content": "Upload Initial Data Requests (IDR) and Risk Control Matrices (RCM). You hold override rights: when you lock a control line item, team members cannot alter your criteria.",
                "highlight": "Field Lock: Locked fields are visually highlighted with a lock badge and gray background for auditors."
            },
            {
                "title": "Review, Finalization & Clean Consolidation",
                "content": "Review submitted evidence in dedicated line-item tabs. Post in-app query comments to resolve gaps. Once complete, click 'Complete Audit' to auto-consolidate final versions into a clean ZIP archive.",
                "highlight": "Reopen Control: Only you can unlock a finalized engagement if subsequent testing is needed."
            }
        ],
        "Team Member": [
            {
                "title": "Welcome, Engagement Team Member",
                "content": f"Hello {name}! AuditVault is your digital audit workspace where working papers, evidence, and audit observations are securely organized.",
                "highlight": "Personal Dashboard: View only the engagements you are officially assigned to."
            },
            {
                "title": "IDR & RCM Execution",
                "content": "Review information requested from the client in the IDR tab. Inspect the Risk Control Matrix for your assigned test procedures and manager guidance.",
                "highlight": "Permission Boundary: You can edit fieldwork and observations, but manager-locked controls remain protected."
            },
            {
                "title": "Dedicated Line Item Workspace & Daily Versioning",
                "content": "Each RCM line item features its own dedicated tab! Upload testing sheets and evidence. AuditVault automatically creates date-wise version subfolders so no prior work is ever lost.",
                "highlight": "In-App Queries: Discuss queries directly with your Manager right under the line item without messy email threads."
            }
        ]
    }

    steps = tour_steps.get(role, tour_steps["Team Member"])
    total_steps = len(steps)

    if "tour_step_idx" not in st.session_state:
        st.session_state.tour_step_idx = 0

    curr_idx = min(st.session_state.tour_step_idx, total_steps - 1)
    step = steps[curr_idx]

    # Render visual tour container
    st.markdown(f"""
    <div class="tour-card">
        <span class="tour-step-badge">TOUR STEP {curr_idx + 1} OF {total_steps}</span>
        <h3 style="margin-top: 4px; margin-bottom: 8px; color: #FFFFFF; font-weight: 700;">{step['title']}</h3>
        <p style="font-size: 14px; line-height: 1.5; color: #E2E8F0; margin-bottom: 12px;">{step['content']}</p>
        <div style="background: rgba(255,255,255,0.1); border-left: 3px solid #F59E0B; padding: 8px 12px; border-radius: 4px; font-size: 13px; color: #F59E0B; font-weight: 600;">
            💡 {step['highlight']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
    with c1:
        if curr_idx > 0:
            if st.button("⬅️ Previous", key="tour_prev"):
                st.session_state.tour_step_idx -= 1
                st.rerun()
    with c2:
        if curr_idx < total_steps - 1:
            if st.button("Next ➡️", key="tour_next", type="primary"):
                st.session_state.tour_step_idx += 1
                st.rerun()
        else:
            if st.button("Got It! 🎉", key="tour_finish", type="primary"):
                st.session_state.show_tour = False
                st.session_state.tour_step_idx = 0
                st.rerun()
    with c3:
        if st.button("Skip Tour", key="tour_skip"):
            st.session_state.show_tour = False
            st.session_state.tour_step_idx = 0
            st.rerun()
    st.markdown("<hr style='margin: 12px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)
