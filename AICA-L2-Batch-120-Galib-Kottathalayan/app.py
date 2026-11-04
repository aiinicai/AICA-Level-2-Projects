"""AuditHub (Streamlit) - Internal Audit lifecycle management. Sovereign Wealth Fund."""
import streamlit as st, pandas as pd, json, os, datetime as dt, re

st.set_page_config(page_title="AuditHub", page_icon="🏛️", layout="wide")

# ─── Enhanced Professional CSS ───────────────────────────────────────────────
st.markdown("""<style>
/* ── Google Font Import ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Global Typography ── */
*{font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif}

/* ── Sidebar ── */
[data-testid=stSidebar]{
  background:linear-gradient(180deg,#0f172a 0%,#1e293b 100%);
  box-shadow:2px 0 16px rgba(0,0,0,0.08);
}
[data-testid=stSidebar] *{color:#cbd5e1!important;font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif!important}
[data-testid=stSidebar] .stSelectbox label,
[data-testid=stSidebar] .stRadio label{font-weight:500;letter-spacing:0.4px;font-size:0.92em}
[data-testid=stSidebar] .stRadio div[role="radiogroup"] label{
  font-weight:500;font-size:0.92em;letter-spacing:0.3px;
  padding:4px 0;transition:color 0.2s
}
[data-testid=stSidebar] .stRadio div[role="radiogroup"] label:hover{color:#fff!important}
[data-testid=stSidebar] hr{border-color:rgba(148,163,184,0.15)!important;margin:12px 0}
[data-testid=stSidebar] .stButton>button{
  background:rgba(255,255,255,0.06)!important;color:#cbd5e1!important;
  border:1px solid rgba(255,255,255,0.1)!important;font-weight:500;
  border-radius:10px;transition:all 0.2s
}
[data-testid=stSidebar] .stButton>button:hover{
  background:rgba(255,255,255,0.12)!important;color:#fff!important;
  border-color:rgba(255,255,255,0.2)!important
}

/* ── Main App ── */
.stApp{background:linear-gradient(135deg,#fafbfc 0%,#f1f5f9 100%)}
h1,h2,h3{color:#0f172a;font-weight:700;font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif}

/* ── Company Top Bar ── */
.company-bar{
  background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);
  color:#fff;padding:14px 28px;border-radius:14px;margin-bottom:10px;
  display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 2px 12px rgba(15,23,42,0.12);position:relative;overflow:hidden
}
.company-bar::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%230d9488' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  opacity:0.3}
.company-bar .logo{display:flex;align-items:center;gap:14px;position:relative;z-index:1}
.company-bar .logo-icon{
  width:44px;height:44px;background:linear-gradient(135deg,#0d9488,#0f766e);
  border-radius:10px;display:flex;align-items:center;justify-content:center;
  font-size:1.5em;box-shadow:0 2px 8px rgba(13,148,136,0.25)
}
.company-bar .logo h1{margin:0;font-size:1.3em;font-weight:800;color:#fff;letter-spacing:0.8px;line-height:1.2;font-family:'Inter',sans-serif}
.company-bar .logo .subtitle{font-size:0.72em;font-weight:300;color:rgba(255,255,255,0.5);letter-spacing:1.8px;text-transform:uppercase}
.company-bar .bar-right{position:relative;z-index:1;text-align:right;font-size:0.78em;color:rgba(255,255,255,0.55);line-height:1.5}
.company-bar .bar-right strong{color:#5eead4;font-weight:600}

/* ── Hero Banner ── */
.hero{
  background:linear-gradient(135deg,#1e293b 0%,#334155 100%);
  color:#fff;padding:18px 26px;border-radius:14px;margin-bottom:16px;
  border-left:4px solid #0d9488;box-shadow:0 2px 10px rgba(15,23,42,0.08);
  position:relative;overflow:hidden
}
.hero::after{content:'';position:absolute;top:-50%;right:-15%;width:220px;height:220px;background:radial-gradient(circle,rgba(13,148,136,0.08) 0%,transparent 70%);border-radius:50%}
.hero h2{color:#fff;margin:0 0 3px 0;font-size:1.3em;font-weight:700;letter-spacing:0.3px;font-family:'Inter',sans-serif}
.hero p{color:rgba(255,255,255,0.65);margin:0;font-size:0.85em;font-weight:300}

/* ── KPI Cards ── */
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:20px}
.kpi-card{
  background:#fff;border:1px solid #e8ecf1;border-radius:14px;padding:18px 16px;
  box-shadow:0 1px 6px rgba(0,0,0,0.03);transition:transform 0.2s,box-shadow 0.2s;
  position:relative;overflow:hidden
}
.kpi-card:hover{transform:translateY(-2px);box-shadow:0 4px 14px rgba(0,0,0,0.06)}
.kpi-card::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;border-radius:14px 0 0 14px}
.kpi-card.kpi-teal{background:linear-gradient(135deg,#fff,#f0fdfa)}.kpi-card.kpi-teal::before{background:#0d9488}
.kpi-card.kpi-blue{background:linear-gradient(135deg,#fff,#eef2ff)}.kpi-card.kpi-blue::before{background:#6366f1}
.kpi-card.kpi-amber{background:linear-gradient(135deg,#fff,#fffbeb)}.kpi-card.kpi-amber::before{background:#d97706}
.kpi-card.kpi-red{background:linear-gradient(135deg,#fff,#fff1f2)}.kpi-card.kpi-red::before{background:#e11d48}
.kpi-card.kpi-purple{background:linear-gradient(135deg,#fff,#f5f3ff)}.kpi-card.kpi-purple::before{background:#7c3aed}
.kpi-card .kpi-icon{font-size:1.5em;margin-bottom:6px}
.kpi-card .kpi-value{font-size:1.9em;font-weight:800;color:#0f172a;line-height:1.1}
.kpi-card .kpi-label{font-size:0.78em;color:#64748b;font-weight:500;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px}

/* ── Dashboard Section Card ── */
.dash-section{background:#fff;border:1px solid #e8ecf1;border-radius:16px;padding:22px 24px;margin-bottom:16px;box-shadow:0 1px 6px rgba(0,0,0,0.03)}
.dash-section h3{margin:0 0 14px 0;font-size:1.02em;font-weight:700;color:#0f172a;display:flex;align-items:center;gap:8px;font-family:'Inter',sans-serif}
.dash-section h3 .icon{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:8px;font-size:0.9em}
.icon-teal{background:#ccfbf1;color:#0f766e}.icon-blue{background:#e0e7ff;color:#4338ca}.icon-red{background:#ffe4e6;color:#be123c}
.icon-amber{background:#fef3c7;color:#92400e}.icon-purple{background:#ede9fe;color:#5b21b6}

/* ── Heatmap Table ── */
.heatmap-table{width:100%;border-collapse:separate;border-spacing:0;font-size:0.85em}
.heatmap-table th{background:#f8fafc;color:#475569;font-weight:600;padding:10px 12px;text-align:left;border-bottom:2px solid #e8ecf1}
.heatmap-table th:first-child{border-radius:10px 0 0 0}.heatmap-table th:last-child{border-radius:0 10px 0 0}
.heatmap-table td{padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#334155}
.heatmap-table tr:nth-child(even) td{background:#fafbfc}
.heatmap-table tr:hover td{background:#f1f5f9}
.heatmap-table .band-high{color:#be123c;font-weight:700}.heatmap-table .band-medium{color:#92400e;font-weight:600}.heatmap-table .band-low{color:#0f766e;font-weight:600}
.priority-bar{height:6px;border-radius:3px;background:#e8ecf1;overflow:hidden;min-width:80px}
.priority-bar .fill{height:100%;border-radius:3px;transition:width 0.4s ease}
.fill-high{background:linear-gradient(90deg,#e11d48,#be123c)}.fill-medium{background:linear-gradient(90deg,#d97706,#b45309)}.fill-low{background:linear-gradient(90deg,#0d9488,#0f766e)}

/* ── Finding Rows ── */
.finding-row{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid #f1f5f9}
.finding-row:last-child{border-bottom:none}
.finding-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.dot-high{background:#e11d48}.dot-medium{background:#d97706}.dot-low{background:#0d9488}
.finding-text{flex:1;font-size:0.88em;color:#334155;line-height:1.3}
.finding-meta{font-size:0.75em;color:#94a3b8;white-space:nowrap}

/* ── Metric Cards ── */
[data-testid=stMetric]{
  background:linear-gradient(135deg,#ffffff,#fafbfc);
  border:1px solid #e8ecf1;border-top:3px solid #0d9488;
  border-radius:12px;padding:16px 20px;
  box-shadow:0 1px 6px rgba(0,0,0,0.03);transition:transform 0.2s,box-shadow 0.2s
}
[data-testid=stMetric]:hover{transform:translateY(-2px);box-shadow:0 4px 14px rgba(0,0,0,0.06)}

/* ── Tabs ── */
.stTabs [aria-selected=true]{border-bottom:3px solid #0d9488!important;font-weight:600}

/* ── Buttons ── */
.stApp .stButton>button{
  background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;
  border-radius:10px;border:none;padding:8px 20px;font-weight:500;
  box-shadow:0 1px 6px rgba(15,23,42,0.12);transition:all 0.2s;
  font-family:'Inter',sans-serif
}
.stApp .stButton>button:hover{background:linear-gradient(135deg,#0d9488,#0f766e);color:#fff;box-shadow:0 3px 12px rgba(13,148,136,0.2)}

/* ── Expander ── */
.streamlit-expanderHeader{background:#f8fafc;border-radius:10px;font-weight:600;color:#0f172a}

/* ── Data Editor / Dataframe ── */
[data-testid=stDataFrame]{border-radius:12px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.03)}

/* ── Badges ── */
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:0.78em;font-weight:600;letter-spacing:0.3px}
.badge-high{background:#ffe4e6;color:#be123c}.badge-medium{background:#fef3c7;color:#92400e}.badge-low{background:#ccfbf1;color:#0f766e}
.badge-open{background:#e0e7ff;color:#4338ca}.badge-closed{background:#ccfbf1;color:#0f766e}
.badge-overdue{background:#ffe4e6;color:#be123c;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.7}}

/* ── Status Cards ── */
.status-card{background:#fff;border:1px solid #e8ecf1;border-radius:14px;padding:16px;margin:8px 0;box-shadow:0 1px 4px rgba(0,0,0,0.03)}
.status-card:hover{box-shadow:0 3px 12px rgba(0,0,0,0.06)}

/* ── Section Headers ── */
.section-header{display:flex;align-items:center;gap:10px;margin:20px 0 12px 0;padding-bottom:8px;border-bottom:2px solid #e8ecf1}
.section-header h3{margin:0;color:#0f172a}

/* ── Progress Bars ── */
.stProgress > div > div{border-radius:8px}

/* ── Forms ── */
[data-testid=stForm]{background:#fff;border:1px solid #e8ecf1;border-radius:16px;padding:20px;box-shadow:0 1px 6px rgba(0,0,0,0.03)}

/* ── Alerts ── */
.stAlert{border-radius:12px}

/* ── Divider ── */
hr{border-color:#e8ecf1!important}

/* ── Login Page Styles ── */
.login-container{
  max-width:440px;margin:60px auto;background:#fff;
  border:1px solid #e8ecf1;border-radius:20px;padding:40px 36px;
  box-shadow:0 4px 24px rgba(0,0,0,0.06)
}
.login-logo{text-align:center;margin-bottom:24px}
.login-logo .icon{
  width:64px;height:64px;background:linear-gradient(135deg,#0d9488,#0f766e);
  border-radius:16px;display:inline-flex;align-items:center;justify-content:center;
  font-size:2em;box-shadow:0 4px 16px rgba(13,148,136,0.2);margin-bottom:12px
}
.login-logo h1{margin:0;font-size:1.6em;font-weight:800;color:#0f172a;letter-spacing:0.8px;font-family:'Inter',sans-serif}
.login-logo p{margin:4px 0 0 0;font-size:0.82em;color:#94a3b8;font-weight:300;letter-spacing:1.5px;text-transform:uppercase}
.login-divider{height:1px;background:linear-gradient(90deg,transparent,#e8ecf1,transparent);margin:20px 0}

/* ── Sidebar User Badge ── */
.sidebar-user-badge{
  background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);
  border-radius:10px;padding:10px 14px;margin:8px 0;text-align:center
}
.sidebar-user-badge .name{font-weight:600;font-size:0.92em;color:#e2e8f0!important}
.sidebar-user-badge .role{font-weight:300;font-size:0.75em;color:rgba(148,163,184,0.8)!important;letter-spacing:0.5px}
</style>""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
F = "data.json"
MIT = {1: 0, 2: .15, 3: .3, 4: .45, 5: .6}

TEAM = {
    "Maya Rahman": "Head of Internal Audit",
    "Omar Hassan": "Audit Manager",
    "Lina Patel": "Audit Manager",
    "Daniel Chen": "Senior Auditor",
    "Sara Ahmed": "Senior Auditor",
    "James Okafor": "Auditor",
    "Noor Ali": "Auditor",
    "Elena Petrova": "IT Audit Specialist",
}

# ─── Audit Universe ─────────────────────────────────────────────────────────
P = [
    ("Front Office — Public Equities", "Equities", 2024, (5,4,3,2,3), (5,4,3)),
    ("Front Office — Fixed Income and Credit", "Fixed Income", 2023, (5,4,2,3,4), (5,4,3)),
    ("Front Office — Private Equity and Venture Capital", "PE/VC", 2021, (5,3,4,3,5), (5,4,2)),
    ("Front Office — Real Estate and Infrastructure", "Real Assets", 2022, (4,3,4,3,4), (5,3,3)),
    ("Front Office — Treasury, FX and Derivatives", "Treasury", 2024, (5,5,3,3,3), (5,4,3)),
    ("Middle Office — Investment Risk and Performance", "Cross-asset", 2023, (4,3,3,2,4), (4,4,3)),
    ("Back Office — Trade Settlement and Reconciliation", "Cross-asset", 2024, (4,4,2,3,2), (4,4,4)),
    ("Investment Operations — Fund Accounting and Valuation", "Cross-asset", 2025, (5,4,3,3,3), (5,4,3)),
    ("Finance and Financial Reporting", "Support", 2024, (4,5,2,2,2), (5,3,4)),
    ("Compliance, AML and Regulatory Affairs", "Support", 2023, (5,5,3,3,3), (5,4,3)),
    ("Legal and Corporate Governance", "Support", 2022, (3,4,2,2,3), (4,3,4)),
    ("Human Resources", "Support", 2021, (3,3,3,3,4), (3,3,4)),
    ("Procurement and Vendor Management", "Support", 2023, (3,4,3,3,4), (4,4,3)),
    ("Information Technology and Cybersecurity", "Support", 2023, (5,5,4,4,4), (5,5,3)),
    ("General Services and Facilities", "Support", 2022, (2,2,2,2,5), (3,3,4)),
]

# ─── Expanded RCM Data (3-4 controls per process) ───────────────────────────
RCM_DATA = [
    # 0: Public Equities
    [
        dict(risk="Unauthorized trades or mandate breaches", ctrl="Pre-trade mandate compliance checks and daily exception review by compliance team", i=5, l=4, e=3, note="Automated pre-trade checks with manual override monitoring"),
        dict(risk="Excessive concentration in single securities or sectors", ctrl="Real-time position monitoring with automated concentration limit alerts", i=4, l=3, e=3, note="System-enforced hard limits with compliance dashboard"),
        dict(risk="Inaccurate trade execution or best execution failures", ctrl="Transaction cost analysis and best execution committee quarterly review", i=4, l=3, e=4, note="Independent TCA reporting with broker performance scoring"),
        dict(risk="Front-running or market manipulation", ctrl="Employee personal trading pre-clearance and surveillance monitoring", i=5, l=2, e=3, note="Automated surveillance with restricted list enforcement"),
    ],
    # 1: Fixed Income and Credit
    [
        dict(risk="Excess issuer exposure or weak credit assessment", ctrl="Issuer concentration limits with daily monitoring and credit committee approval", i=5, l=4, e=3, note="Tiered approval matrix based on credit quality and exposure size"),
        dict(risk="Inadequate credit risk assessment for new issuers", ctrl="Independent credit analysis with rating agency cross-reference and stress testing", i=5, l=3, e=3, note="Mandatory internal credit scoring before onboarding"),
        dict(risk="Interest rate risk exceeding approved tolerances", ctrl="Duration and DV01 monitoring with real-time limit checks and escalation procedures", i=4, l=4, e=4, note="Automated alerts when duration deviates from benchmark"),
        dict(risk="Illiquid bond positions creating redemption risk", ctrl="Liquidity classification framework with periodic liquidity stress testing", i=4, l=3, e=3, note="Weekly liquidity scoring and monthly stress test reporting"),
    ],
    # 2: Private Equity and Venture Capital
    [
        dict(risk="Unsupported valuations or weak due diligence", ctrl="Investment committee approval with independent valuation challenge and third-party review", i=5, l=4, e=2, note="Quarterly independent valuation with external specialist input"),
        dict(risk="Inadequate post-investment monitoring", ctrl="Quarterly portfolio company reporting with board representation and milestone tracking", i=4, l=4, e=3, note="Standardized KPI dashboard for each portfolio company"),
        dict(risk="Key person dependency on deal teams", ctrl="Succession planning, knowledge documentation and cross-training of investment professionals", i=4, l=3, e=2, note="Annual review of key person risk with mitigation plans"),
        dict(risk="Conflict of interest in co-investment arrangements", ctrl="Conflict of interest policy, mandatory disclosure and independent allocation committee", i=5, l=3, e=3, note="Pre-deal conflict screening with compliance sign-off"),
    ],
    # 3: Real Estate and Infrastructure
    [
        dict(risk="Weak project oversight or overstated property values", ctrl="Milestone monitoring with independent external valuations and construction audits", i=5, l=3, e=3, note="Semi-annual independent appraisals with site inspections"),
        dict(risk="Environmental and regulatory compliance failures", ctrl="Environmental due diligence checklist and ongoing regulatory compliance monitoring", i=4, l=3, e=3, note="Third-party environmental assessments before acquisition"),
        dict(risk="Tenant concentration risk and rental income volatility", ctrl="Tenant diversification analysis and lease expiry profiling with revenue stress tests", i=4, l=4, e=3, note="Monthly tenant risk dashboard with early warning indicators"),
    ],
    # 4: Treasury, FX and Derivatives
    [
        dict(risk="Liquidity shortfalls or collateral management errors", ctrl="Daily liquidity monitoring with collateral reconciliation and margin call tracking", i=5, l=4, e=3, note="Real-time collateral management system with automated alerts"),
        dict(risk="Unauthorized derivative transactions exceeding limits", ctrl="Pre-trade approval workflow with automated notional and Greeks limit checking", i=5, l=3, e=4, note="System-enforced limits with dual authorization for large trades"),
        dict(risk="FX hedging mismatch creating unintended currency exposure", ctrl="Daily hedge effectiveness testing and currency exposure reporting to CIO", i=4, l=4, e=3, note="Automated hedge ratio monitoring with weekly rebalancing review"),
        dict(risk="Counterparty credit risk in OTC derivatives", ctrl="Counterparty exposure monitoring, ISDA/CSA compliance and netting agreement reviews", i=5, l=3, e=3, note="Real-time counterparty exposure dashboard with credit triggers"),
    ],
    # 5: Investment Risk and Performance
    [
        dict(risk="Inaccurate risk reporting leading to poor investment decisions", ctrl="Independent data validation with automated reconciliation and report review sign-off", i=4, l=4, e=3, note="Four-eye review process for all published risk reports"),
        dict(risk="Model risk from flawed VaR or stress test methodologies", ctrl="Model validation framework with independent back-testing and annual model review", i=5, l=3, e=3, note="Independent model validation team with quarterly back-testing"),
        dict(risk="Performance attribution errors misrepresenting fund returns", ctrl="Automated attribution calculations with independent verification and benchmark review", i=4, l=3, e=4, note="Monthly reconciliation of performance attribution to custodian returns"),
    ],
    # 6: Trade Settlement and Reconciliation
    [
        dict(risk="Failed settlements causing financial loss or reputational damage", ctrl="Daily reconciliations with T+1 exception management and aged-break escalation", i=4, l=4, e=4, note="Automated matching with priority escalation for fails exceeding threshold"),
        dict(risk="Unresolved reconciliation breaks accumulating over time", ctrl="Aged break reporting with mandatory escalation timelines and root cause analysis", i=4, l=4, e=3, note="Weekly aged break review with mandatory resolution deadlines"),
        dict(risk="Corporate action processing errors affecting portfolio positions", ctrl="Corporate action capture workflow with dual verification and deadline monitoring", i=4, l=3, e=4, note="Automated corporate action alerts with independent verification"),
    ],
    # 7: Fund Accounting and Valuation
    [
        dict(risk="Incorrect NAV or pricing errors affecting investor allocations", ctrl="Independent price verification from multiple sources with NAV review and approval", i=5, l=4, e=3, note="Automated price challenge workflow with threshold-based escalation"),
        dict(risk="Stale or illiquid security pricing", ctrl="Stale price detection with valuation committee escalation and fair value methodology", i=5, l=3, e=3, note="Automated stale price flagging with independent fair valuation"),
        dict(risk="Accounting policy misapplication for complex instruments", ctrl="Accounting policy manual with specialist review and quarterly technical updates", i=4, l=3, e=3, note="Centralized policy library with change management process"),
        dict(risk="Unauthorized journal entries or manual adjustments", ctrl="Journal entry approval workflow with segregation of duties and post-entry review", i=4, l=3, e=4, note="Automated workflow with dual authorization for entries above threshold"),
    ],
    # 8: Finance and Financial Reporting
    [
        dict(risk="Material reporting errors in financial statements", ctrl="Month-end close checklist with journal approval workflow and management review", i=5, l=3, e=4, note="Automated close checklist with real-time completion tracking"),
        dict(risk="Regulatory reporting deadline breaches", ctrl="Regulatory reporting calendar with automated reminders and escalation procedures", i=5, l=3, e=3, note="Centralized regulatory calendar with owner assignment and tracking"),
        dict(risk="Inadequate financial controls over manual processes", ctrl="Key control self-assessment with independent monitoring and quarterly testing", i=4, l=3, e=3, note="Annual control self-assessment with risk-based independent testing"),
    ],
    # 9: Compliance, AML and Regulatory Affairs
    [
        dict(risk="Regulatory breaches or weak sanctions screening", ctrl="Risk-based due diligence with automated screening and enhanced monitoring", i=5, l=4, e=3, note="Real-time sanctions screening with case management workflow"),
        dict(risk="Inadequate AML transaction monitoring", ctrl="Automated transaction monitoring with risk-based alert investigation and SAR filing", i=5, l=4, e=3, note="Machine learning-enhanced monitoring with analyst investigation workflow"),
        dict(risk="Failure to identify and manage regulatory changes", ctrl="Regulatory horizon scanning with impact assessment and implementation tracking", i=4, l=3, e=3, note="Weekly regulatory bulletin with assigned impact assessments"),
        dict(risk="Incomplete or inaccurate regulatory filings", ctrl="Filing checklist with dual review, automated data extraction and submission tracking", i=4, l=3, e=4, note="Standardized filing templates with quality assurance review"),
    ],
    # 10: Legal and Corporate Governance
    [
        dict(risk="Unmanaged contractual obligations or expired agreements", ctrl="Contract lifecycle management system with renewal alerts and delegated authority checks", i=4, l=3, e=4, note="Centralized contract repository with automated expiry notifications"),
        dict(risk="Governance framework gaps or board reporting deficiencies", ctrl="Annual governance review with board effectiveness assessment and gap analysis", i=3, l=3, e=3, note="Independent governance assessment with action plan tracking"),
        dict(risk="Litigation risk from inadequate legal review of transactions", ctrl="Mandatory legal review for transactions above threshold with sign-off protocol", i=4, l=3, e=3, note="Legal review checklist integrated into deal approval workflow"),
    ],
    # 11: Human Resources
    [
        dict(risk="Payroll errors or inappropriate system access by former employees", ctrl="Automated payroll reconciliation with joiner-mover-leaver process and access revocation", i=3, l=3, e=4, note="Integration between HR system and access management for real-time updates"),
        dict(risk="Non-compliance with employment regulations", ctrl="Employment law compliance monitoring with regular policy updates and mandatory training", i=3, l=3, e=3, note="Annual compliance review with external legal counsel input"),
        dict(risk="Inadequate succession planning for critical roles", ctrl="Annual talent review with succession planning framework and development programs", i=3, l=4, e=3, note="Critical role identification with documented succession plans"),
    ],
    # 12: Procurement and Vendor Management
    [
        dict(risk="Conflicts of interest or vendor failure impacting operations", ctrl="Competitive sourcing requirements with conflict declarations and vendor risk assessment", i=4, l=4, e=3, note="Annual conflict declaration with vendor risk tiering methodology"),
        dict(risk="Third-party data breaches or service disruptions", ctrl="Vendor security assessments, SLA monitoring and business continuity requirements", i=4, l=3, e=3, note="Risk-based vendor due diligence with ongoing monitoring program"),
        dict(risk="Contract terms unfavorable or poorly negotiated", ctrl="Standardized procurement framework with legal review and competitive benchmarking", i=3, l=3, e=4, note="Category management approach with market benchmarking analysis"),
    ],
    # 13: IT and Cybersecurity
    [
        dict(risk="Cyber incidents or data breaches compromising sensitive information", ctrl="Multi-factor authentication, endpoint protection and security incident response plan", i=5, l=5, e=3, note="24/7 SOC monitoring with automated incident response playbooks"),
        dict(risk="Excessive privileged access creating insider threat risk", ctrl="Quarterly privileged access reviews with automated deprovisioning and monitoring", i=5, l=4, e=3, note="PAM solution with session recording and just-in-time access"),
        dict(risk="System availability failures affecting business operations", ctrl="Business continuity planning with recovery testing and redundant infrastructure", i=5, l=3, e=4, note="Annual DR testing with documented RTO/RPO compliance"),
        dict(risk="Unpatched vulnerabilities in critical systems", ctrl="Vulnerability management program with risk-based patching and regular penetration testing", i=5, l=4, e=3, note="Automated vulnerability scanning with SLA-based remediation tracking"),
    ],
    # 14: General Services and Facilities
    [
        dict(risk="Physical security failures compromising asset protection", ctrl="Access monitoring with CCTV surveillance, visitor management and security patrols", i=3, l=3, e=4, note="Integrated access control system with real-time monitoring"),
        dict(risk="Business disruption from facility maintenance failures", ctrl="Preventive maintenance schedules with vendor SLAs and incident reporting", i=3, l=3, e=3, note="Computerized maintenance management system with work order tracking"),
        dict(risk="Health and safety compliance gaps", ctrl="Regular HSE inspections with corrective action tracking and staff training programs", i=3, l=2, e=4, note="Monthly HSE inspections with digital reporting and trend analysis"),
    ],
]

# ─── Expanded Observations with Detailed Conditions / Recommendations ──────
SEED_OBS = [
    dict(
        title="Pricing exceptions not approved within SLA",
        pi=7, rating="High", status="Released", prep="Daniel Chen",
        cond="Review of 120 pricing exceptions during Q3 2025 identified that 34 (28%) were not reviewed and approved within the 24-hour SLA. Exceptions ranged from 2 to 7 business days overdue. Root cause analysis indicated insufficient staffing coverage during month-end periods and lack of automated escalation for unactioned items.",
        reco="Implement automated escalation workflow that notifies the team lead after 12 hours and the department head after 24 hours. Increase pricing team capacity during month-end close periods. Establish KPI tracking for exception resolution timeliness.",
    ),
    dict(
        title="Privileged access not reviewed quarterly as required",
        pi=13, rating="High", status="Action Agreed", prep="Elena Petrova",
        cond="Analysis of privileged account management revealed that quarterly access reviews were not performed for Q1 and Q2 2025 across 14 critical systems. Additionally, 8 dormant administrator accounts (inactive for 90+ days) were identified, including 3 belonging to employees who had transferred to other departments. No compensating controls were in place during the review gap.",
        reco="Establish a formal privileged access review schedule with automated reminders and tracking. Implement automated detection and disabling of dormant accounts after 60 days of inactivity. Deploy a Privileged Access Management (PAM) solution with session recording capabilities.",
    ),
    dict(
        title="Conflict of interest declarations incomplete across procurement",
        pi=12, rating="Medium", status="HIA Approval", prep="James Okafor",
        cond="Examination of the annual conflict of interest declaration process identified that only 67% (42 of 63) of procurement staff completed declarations by the deadline. Of completed declarations, 5 disclosed potential conflicts that had not been escalated to the Ethics Committee. Three active vendor relationships were identified where procurement officers had undisclosed familial connections.",
        reco="Enforce mandatory completion of conflict declarations as a condition of system access renewal. Implement automated escalation of disclosed conflicts to the Ethics Committee within 5 business days. Conduct targeted ethics training for procurement staff. Establish an annual vendor relationship audit program.",
    ),
    dict(
        title="Aged reconciliation breaks not escalated per policy",
        pi=6, rating="Medium", status="Manager Review", prep="Sara Ahmed",
        cond="Testing of the reconciliation process across 3 months (April-June 2025) identified 47 reconciliation breaks aged beyond 30 days that were not escalated to management as required by policy. The total unresolved value was approximately $12.4M. Investigation revealed that the escalation policy threshold was not configured in the reconciliation system, requiring manual tracking.",
        reco="Configure automated escalation rules in the reconciliation system aligned with policy thresholds (15 days = team lead, 30 days = department manager, 45 days = COO). Implement an aged break dashboard with real-time visibility. Require documented root cause analysis for all breaks exceeding $1M or 15 days.",
    ),
    dict(
        title="Investment mandate compliance monitoring gaps identified",
        pi=0, rating="High", status="Released", prep="Daniel Chen",
        cond="Review of the investment mandate compliance framework identified that 3 of 12 active mandates had outdated compliance rules in the pre-trade system, referencing superseded Investment Policy Statement versions. Post-trade compliance checks detected 7 instances where positions temporarily breached sector concentration limits, with an average breach duration of 3.2 trading days before correction.",
        reco="Conduct a comprehensive reconciliation of all active mandate rules against current IPS documentation. Implement a formal change management process requiring compliance sign-off before IPS amendments take effect. Establish daily automated breach reporting to the Chief Compliance Officer with mandatory 24-hour remediation timeline.",
    ),
    dict(
        title="Disaster recovery testing results below target",
        pi=13, rating="High", status="Action Agreed", prep="Elena Petrova",
        cond="Annual disaster recovery testing conducted in September 2025 revealed that 4 of 9 critical systems failed to meet their documented Recovery Time Objectives (RTOs). The trading platform recovered in 6.5 hours against a 4-hour RTO, and the risk management system took 8 hours against a 2-hour RTO. Two systems had not been tested in over 18 months due to infrastructure migration delays.",
        reco="Prioritize remediation of DR gaps for trading and risk management systems. Update DR runbooks with current infrastructure configurations. Conduct quarterly tabletop exercises and semi-annual technical recovery tests. Establish a DR readiness dashboard with RTO/RPO compliance tracking for all critical systems.",
    ),
    dict(
        title="AML transaction monitoring alert backlog exceeding thresholds",
        pi=9, rating="High", status="Manager Review", prep="Noor Ali",
        cond="Review of the AML transaction monitoring system identified a backlog of 234 unresolved alerts, of which 89 (38%) were aged beyond the 30-day investigation SLA. The average investigation closure time increased from 12 days in Q1 to 28 days in Q3 2025. Staffing analysis indicated that the current team of 4 analysts is insufficient for the alert volume of approximately 180 new alerts per month. Three potentially suspicious transactions totaling $4.2M had not been escalated for SAR consideration.",
        reco="Immediately triage and prioritize the existing alert backlog with focus on high-risk typologies. Augment the investigation team with 2 additional trained analysts. Implement risk-based alert scoring to improve investigation efficiency. Conduct a tuning exercise on monitoring rules to reduce false positive rates while maintaining detection effectiveness.",
    ),
    dict(
        title="Vendor risk assessments overdue for critical service providers",
        pi=12, rating="Medium", status="Released", prep="Sara Ahmed",
        cond="Assessment of the third-party risk management program identified that annual risk assessments were overdue for 11 of 28 (39%) Tier 1 vendors, including 3 cloud infrastructure providers and 2 market data vendors. Four vendors had not provided updated SOC 2 Type II reports within 90 days of report period end. Business continuity plans were not documented for 6 critical vendor relationships.",
        reco="Establish a centralized vendor risk assessment calendar with automated tracking and escalation. Require contractual provisions for timely delivery of SOC reports and right-to-audit clauses. Develop documented business continuity and exit strategies for all Tier 1 vendor relationships. Implement a vendor risk dashboard with real-time compliance status.",
    ),
    dict(
        title="Journal entry controls insufficient for manual adjustments",
        pi=8, rating="Medium", status="Draft", prep="James Okafor",
        cond="Testing of 250 manual journal entries during Q2 2025 identified 18 entries (7.2%) that lacked required supporting documentation. Additionally, 12 entries exceeding the $500K dual-authorization threshold were approved by a single individual. The journal entry log revealed that 3 preparers had the ability to both create and approve their own entries in the system, representing a segregation of duties violation.",
        reco="Enforce system-level segregation of duties preventing users from approving self-prepared entries. Implement automated workflow requiring documentation attachment before approval. Configure system controls to enforce dual authorization for entries above the materiality threshold. Conduct monthly reviews of journal entry access rights and approval patterns.",
    ),
    dict(
        title="Employee onboarding access provisioning delays",
        pi=11, rating="Low", status="Released", prep="Noor Ali",
        cond="Analysis of 45 new employee onboardings between January and June 2025 identified that average system access provisioning took 8.3 business days against a target of 3 business days. 12 employees (27%) received temporary shared credentials during the provisioning delay, creating accountability gaps. Role-based access profiles were not defined for 5 of 18 job functions, requiring manual access specification for each new hire.",
        reco="Define standardized role-based access profiles for all job functions. Implement automated access provisioning triggered by HR system events. Eliminate the use of shared credentials by implementing emergency individual access procedures. Establish SLA monitoring for access provisioning with weekly reporting to HR and IT management.",
    ),
    dict(
        title="Board reporting package lacks consistent risk metrics",
        pi=10, rating="Medium", status="Manager Review", prep="Daniel Chen",
        cond="Review of the past 6 quarterly board reporting packages revealed inconsistent presentation of key risk indicators. Risk appetite metrics changed format 3 times without documented rationale. The board received aggregated risk scores without underlying methodology disclosure. Comparison with regulatory expectations identified 4 areas where reporting fell below industry best practice standards, including cyber risk reporting and ESG risk integration.",
        reco="Develop a standardized board reporting template aligned with governance best practices and regulatory expectations. Establish a formal change management process for any modifications to board reporting formats. Include methodology notes and trend analysis in all risk metric presentations. Integrate cyber risk and ESG risk reporting into the standard board package.",
    ),
    dict(
        title="Incomplete hedge documentation under IFRS 9 requirements",
        pi=4, rating="High", status="Draft", prep="Sara Ahmed",
        cond="Examination of the hedge accounting documentation for 32 active FX and interest rate hedges identified that 8 (25%) lacked complete prospective effectiveness testing documentation as required by IFRS 9. Retrospective effectiveness testing for 5 hedges showed results outside the 80-125% effectiveness range, but discontinuation of hedge accounting was not applied timely. The hedging policy had not been updated since 2022 and did not address basis risk or credit valuation adjustments.",
        reco="Conduct a comprehensive review and remediation of all active hedge documentation to ensure IFRS 9 compliance. Implement an automated hedge effectiveness monitoring system with alerts for out-of-range results. Update the hedging policy to address current portfolio complexity including basis risk, CVA and DVA considerations. Engage external specialists to validate hedge accounting treatment for complex structures.",
    ),
]

# ─── Expanded Action Items ─────────────────────────────────────────────
SEED_ACTIONS = [
    dict(obs=2, desc="Perform quarterly privileged access reviews for all critical systems", owner="Ravi Menon", due="2026-09-30", status="Open"),
    dict(obs=2, desc="Remove dormant administrator accounts and implement automated deprovisioning", owner="Ravi Menon", due="2026-11-30", status="Evidence Submitted"),
    dict(obs=2, desc="Document and formalize access review procedures with RACI matrix", owner="Ravi Menon", due="2026-06-30", status="Closed"),
    dict(obs=1, desc="Implement automated pricing exception escalation workflow", owner="Priya Singh", due="2026-08-31", status="Open"),
    dict(obs=1, desc="Hire two additional pricing analysts for month-end coverage", owner="Priya Singh", due="2026-10-31", status="In Progress"),
    dict(obs=5, desc="Reconcile all active mandate rules against current IPS documentation", owner="Omar Hassan", due="2026-07-31", status="Open"),
    dict(obs=5, desc="Deploy automated daily breach reporting to Chief Compliance Officer", owner="Omar Hassan", due="2026-09-30", status="Open"),
    dict(obs=6, desc="Update disaster recovery runbooks for trading and risk management systems", owner="Ravi Menon", due="2026-08-31", status="In Progress"),
    dict(obs=6, desc="Establish quarterly DR tabletop exercises schedule", owner="Ravi Menon", due="2026-07-31", status="Evidence Submitted"),
    dict(obs=6, desc="Deploy DR readiness dashboard with RTO/RPO compliance metrics", owner="Ravi Menon", due="2026-12-31", status="Open"),
    dict(obs=8, desc="Complete overdue Tier 1 vendor risk assessments within 60 days", owner="Lina Patel", due="2026-07-15", status="Open"),
    dict(obs=8, desc="Develop vendor exit strategies for all critical service providers", owner="Lina Patel", due="2026-09-30", status="Open"),
    dict(obs=3, desc="Deploy automated conflict of interest declaration tracking system", owner="James Okafor", due="2026-08-31", status="Open"),
    dict(obs=10, desc="Define role-based access profiles for all 18 job functions", owner="Noor Ali", due="2026-07-31", status="In Progress"),
    dict(obs=10, desc="Implement automated access provisioning via HR system integration", owner="Noor Ali", due="2026-11-30", status="Open"),
]


def seed():
    D = {
        "cfg": dict(wr=60, wq=40, n=8, days=220, leave=25, train=8, admin=30, cont=15, share=30, hi=70, med=45, agg="max"),
        "ov": {},
        "obs": [],
        "act": [],
        "plans": [],
        "users": {},
    }

    # Seed user accounts from TEAM with default password
    for name, role in TEAM.items():
        username = name.lower().replace(" ", ".")
        D["users"][username] = {"name": name, "password": "Audit1", "role": role}

    D["p"] = []
    for i, (n, c, l, s, r) in enumerate(P):
        rcm = RCM_DATA[i] if i < len(RCM_DATA) else [dict(risk="Risk to be assessed", ctrl="Control to be documented", i=3, l=3, e=3, note="Pending detailed assessment")]
        D["p"].append(dict(
            name=n, cls=c, last=l, s=list(s),
            rat=[
                "High strategic alignment with fund mandate and investment objectives",
                "Subject to regulatory scrutiny and stakeholder reporting requirements",
                "Ongoing transformation and process changes requiring close monitoring",
                "Management oversight framework with identified areas for enhancement",
                "Extended period since last comprehensive audit engagement",
            ],
            rcm=rcm,
        ))

    for idx, o in enumerate(SEED_OBS):
        D["obs"].append(dict(
            id=idx + 1,
            title=o["title"],
            pi=o["pi"],
            rating=o["rating"],
            status=o["status"],
            prep=o["prep"],
            cond=o["cond"],
            reco=o["reco"],
            resp="" if o["status"] not in ("Action Agreed", "Management Response") else "Management acknowledges the findings and commits to implementing corrective actions within the agreed timelines.",
            notes="",
            hist=[],
        ))

    for idx, a in enumerate(SEED_ACTIONS):
        D["act"].append(dict(
            id=idx + 1,
            obs=a["obs"],
            desc=a["desc"],
            owner=a["owner"],
            due=a["due"],
            orig=a["due"],
            status=a["status"],
            evid="Completed: procedure documented and approved by department head. Access review schedule configured in GRC system." if a["status"] == "Closed" else ("Evidence package submitted for validation: screenshots of deprovisioned accounts and updated access matrix." if a["status"] == "Evidence Submitted" else ""),
            why="",
        ))

    return D


if "D" not in st.session_state:
    st.session_state.D = json.load(open(F)) if os.path.exists(F) else seed()
D = st.session_state.D

# Ensure users dict exists (backward compat with old data.json)
if "users" not in D:
    D["users"] = {}
    for name, role in TEAM.items():
        username = name.lower().replace(" ", ".")
        D["users"][username] = {"name": name, "password": "Audit1", "role": role}


def save():
    json.dump(D, open(F, "w"), indent=1)


def calc(p):
    c = D["cfg"]
    res = [r["i"] * r["l"] * (1 - MIT[r["e"]]) for r in p["rcm"]]
    v = (max(res) if c["agg"] == "max" else sum(res) / len(res)) if res else 0
    norm = v / 25 * 100 if v is not None else 0
    ok = all(p["s"])
    q = (sum(p["s"]) / 5 - 1) / 4 * 100 if ok else 0
    if not ok:
        return norm, q, norm * c["wr"] / 100, "Low"
    pr = c["wr"] / 100 * norm + c["wq"] / 100 * q
    return norm, q, pr, "High" if pr >= c["hi"] else "Medium" if pr >= c["med"] else "Low"


def cap():
    c = D["cfg"]
    return round(c["n"] * (c["days"] - c["leave"] - c["train"] - c["admin"]) * (1 - c["cont"] / 100) * c["share"] / 100)


def plan():
    C = cap()
    yrs = [2027, 2028, 2029]
    used = {y: 0 for y in yrs}
    days_map = {"High": 60, "Medium": 40, "Low": 25}
    L = []
    for i, p in enumerate(D["p"]):
        n, q, pr, b = calc(p)
        L.append(dict(i=i, name=p["name"], cls=p["cls"], last=p["last"] or 2019, prio=pr or 0, band=b, days=days_map.get(b, 40)))
    L.sort(key=lambda x: (-x["prio"], x["last"]))
    for x in L:
        o = D["ov"].get(str(x["i"]))
        if o:
            x["year"] = o["year"]
            if "days" in o:
                x["days"] = o["days"]
            used[o["year"]] += x["days"]
            x["why"] = "MANUAL OVERRIDE: " + o["why"]
    for x in L:
        if str(x["i"]) in D["ov"]:
            continue
        x["year"] = next((y for y in yrs if used[y] + x["days"] <= C), None)
        if x["year"]:
            used[x["year"]] += x["days"]
        x["why"] = f"Priority {x['prio']:.1f} ({x['band']}); last audit {x['last']}; " + (
            f"scheduled in {x['year']} within capacity" if x["year"] else "UNSCHEDULED — capacity constraint"
        )
    return L, used, C


def overdue(a):
    return a["status"] in ("Open", "In Progress", "Evidence Submitted") and a["due"] < str(dt.date.today())


def rating_badge(rating):
    cls_map = {"High": "badge-high", "Medium": "badge-medium", "Low": "badge-low"}
    return f'<span class="badge {cls_map.get(rating, "badge-medium")}">{rating}</span>'


def status_badge(status):
    color_map = {
        "Draft": "#94a3b8", "Manager Review": "#d97706", "HIA Approval": "#7c3aed",
        "Released": "#6366f1", "Management Response": "#6366f1",
        "Action Agreed": "#0d9488", "Final Issued": "#0f766e",
        "Open": "#6366f1", "In Progress": "#d97706", "Evidence Submitted": "#7c3aed",
        "Closed": "#0d9488", "Risk Accepted": "#6b7280", "Submitted": "#d97706",
        "Approved": "#0d9488", "Superseded": "#94a3b8",
    }
    color = color_map.get(status, "#94a3b8")
    return f'<span style="display:inline-block;padding:4px 12px;border-radius:20px;font-size:0.78em;font-weight:600;background:{color}15;color:{color};border:1px solid {color}30">{status}</span>'


# ─── Authentication Gate ─────────────────────────────────────────────────────
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

if st.session_state.logged_in_user is None:
    st.markdown("""
    <div class="login-logo" style="text-align:center;margin-top:40px">
        <div class="icon" style="width:72px;height:72px;background:linear-gradient(135deg,#0d9488,#0f766e);
            border-radius:18px;display:inline-flex;align-items:center;justify-content:center;
            font-size:2.2em;box-shadow:0 6px 24px rgba(13,148,136,0.25);margin-bottom:14px">🏛️</div>
        <h1 style="margin:0;font-size:1.8em;font-weight:800;color:#0f172a;letter-spacing:0.8px;font-family:'Inter',sans-serif">AuditHub</h1>
        <p style="margin:6px 0 0 0;font-size:0.85em;color:#94a3b8;font-weight:300;letter-spacing:2px;text-transform:uppercase">Zen Investments LLC · Internal Audit Division</p>
    </div>
    """, unsafe_allow_html=True)

    login_tab, register_tab = st.tabs(["🔑 Sign In", "📝 Create Account"])

    with login_tab:
        with st.form("login_form"):
            st.markdown("#### Welcome Back")
            st.caption("Enter your credentials to access AuditHub.")
            login_user = st.text_input("Username", placeholder="e.g. maya.rahman")
            login_pass = st.text_input("Password", type="password", placeholder="6-digit alphanumeric")
            login_submit = st.form_submit_button("Sign In", use_container_width=True)
            if login_submit:
                if login_user in D["users"] and D["users"][login_user]["password"] == login_pass:
                    st.session_state.logged_in_user = login_user
                    st.rerun()
                else:
                    st.error("⚠️ Invalid username or password.")

        st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,#e8ecf1,transparent);margin:16px 0"></div>', unsafe_allow_html=True)
        st.caption("**Default accounts:** username format is `firstname.lastname` (e.g. `maya.rahman`), default password: `Audit1`")

    with register_tab:
        with st.form("register_form"):
            st.markdown("#### Create New Account")
            st.caption("Set up your AuditHub access credentials.")
            reg_name = st.text_input("Full Name", placeholder="e.g. John Smith")
            reg_user = st.text_input("Choose Username", placeholder="e.g. john.smith")
            reg_role = st.selectbox("Role", [
                "Head of Internal Audit", "Audit Manager", "Senior Auditor",
                "Auditor", "IT Audit Specialist",
            ])
            reg_pass = st.text_input("Password (6 characters, alphanumeric)", type="password", placeholder="e.g. Pass12")
            reg_pass2 = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            reg_submit = st.form_submit_button("Create Account", use_container_width=True)
            if reg_submit:
                errors = []
                if not reg_name.strip():
                    errors.append("Full name is required.")
                if not reg_user.strip():
                    errors.append("Username is required.")
                if reg_user in D["users"]:
                    errors.append("Username already exists.")
                if len(reg_pass) != 6:
                    errors.append("Password must be exactly 6 characters.")
                if not re.match(r'^[A-Za-z0-9]{6}$', reg_pass):
                    errors.append("Password must be alphanumeric only (letters and digits).")
                if reg_pass != reg_pass2:
                    errors.append("Passwords do not match.")
                if errors:
                    for e in errors:
                        st.error(f"⚠️ {e}")
                else:
                    D["users"][reg_user] = {"name": reg_name.strip(), "password": reg_pass, "role": reg_role}
                    save()
                    st.success(f"✅ Account created for **{reg_name.strip()}**. You can now sign in.")

    st.stop()

# ─── Get current user info ───────────────────────────────────────────────────
current_user_data = D["users"][st.session_state.logged_in_user]
me = current_user_data["name"]
role = current_user_data["role"]

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:8px 0 4px 0">
        <div style="width:50px;height:50px;background:linear-gradient(135deg,#0d9488,#0f766e);border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:1.6em;box-shadow:0 4px 16px rgba(13,148,136,0.2),0 0 20px rgba(13,148,136,0.1);margin-bottom:8px">🏛️</div>
        <div style="font-size:1.3em;font-weight:800;letter-spacing:1px;font-family:'Inter',sans-serif">AuditHub</div>
        <div style="font-size:0.7em;color:rgba(148,163,184,0.45)!important;letter-spacing:1.8px;text-transform:uppercase;margin-top:2px;font-weight:300">Zen Investments LLC</div>
    </div>
    """, unsafe_allow_html=True)

    # User badge
    st.markdown(f"""
    <div class="sidebar-user-badge">
        <div class="name">👤 {me}</div>
        <div class="role">{role}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    page = st.radio("📋 Navigate", [
        "📊 Dashboard",
        "⚖️ Risk Assessment",
        "📅 Three-Year Plan",
        "🛡️ Risk & Control Matrix",
        "🔍 Observations",
        "✅ Action Tracking",
        "⚙️ Settings",
    ])
    st.markdown("---")
    if st.button("🔄 Reset Data"):
        st.session_state.D = seed()
        save()
        st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.logged_in_user = None
        st.rerun()
    st.markdown("---")
    st.caption("AuditHub v2.0 · Zen Investments LLC")

MGR = role in ("Head of Internal Audit", "Audit Manager")
HEAD = role == "Head of Internal Audit"

# ─── Company Top Bar + Hero Banner ───────────────────────────────────────────
today_str = dt.date.today().strftime("%B %d, %Y")
st.markdown(f"""
<div class="company-bar">
    <div class="logo">
        <div class="logo-icon">🏛️</div>
        <div>
            <h1>Zen Investments LLC</h1>
            <div class="subtitle">Internal Audit Division</div>
        </div>
    </div>
    <div class="bar-right">
        <strong>AuditHub</strong> · Audit Management Platform<br>
        {today_str} · {me} · {role}
    </div>
</div>
""", unsafe_allow_html=True)

page_names = {
    "📊 Dashboard": ("Dashboard", "Executive overview of audit activities, key performance indicators and portfolio risk distribution"),
    "⚖️ Risk Assessment": ("Risk Assessment", "Evaluate and score processes against the risk-based audit methodology"),
    "📅 Three-Year Plan": ("Three-Year Audit Plan", "Capacity-driven rolling plan with risk-based prioritization"),
    "🛡️ Risk & Control Matrix": ("Risk & Control Matrix", "Document risks, controls and effectiveness assessments by process"),
    "🔍 Observations": ("Observations", "Manage audit findings through the full observation lifecycle"),
    "✅ Action Tracking": ("Action Tracking", "Track remediation actions, evidence submission and validation"),
    "⚙️ Settings": ("Settings", "Configure planning parameters, weights and capacity assumptions"),
}
pname, pdesc = page_names.get(page, ("AuditHub", ""))
st.markdown(f'<div class="hero"><h2>{pname}</h2><p>{pdesc}</p></div>', unsafe_allow_html=True)

# ─── Dashboard ───────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    A = D["act"]
    n_universe = len(D["p"])
    n_obs = len(D["obs"])
    n_open = sum(a["status"] in ("Open", "In Progress") for a in A)
    n_overdue = sum(overdue(a) for a in A)
    n_pending = sum(a["status"] == "Evidence Submitted" for a in A)
    n_closed = sum(a["status"] == "Closed" for a in A)

    # KPI Cards (custom HTML)
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card kpi-teal">
            <div class="kpi-icon">📋</div>
            <div class="kpi-value">{n_universe}</div>
            <div class="kpi-label">Audit Universe</div>
        </div>
        <div class="kpi-card kpi-blue">
            <div class="kpi-icon">🔍</div>
            <div class="kpi-value">{n_obs}</div>
            <div class="kpi-label">Observations</div>
        </div>
        <div class="kpi-card kpi-amber">
            <div class="kpi-icon">📌</div>
            <div class="kpi-value">{n_open}</div>
            <div class="kpi-label">Open Actions</div>
        </div>
        <div class="kpi-card kpi-red">
            <div class="kpi-icon">⚠️</div>
            <div class="kpi-value">{n_overdue}</div>
            <div class="kpi-label">Overdue</div>
        </div>
        <div class="kpi-card kpi-purple">
            <div class="kpi-icon">⏳</div>
            <div class="kpi-value">{n_pending}</div>
            <div class="kpi-label">Pending Validation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Row 2: Risk Priority Heatmap + Observation Breakdown ──
    col_left, col_right = st.columns([3, 2])

    with col_left:
        # Top Processes by Priority — custom heatmap table
        sorted_procs = []
        for p in D["p"]:
            n, q, pr, b = calc(p)
            sorted_procs.append(dict(name=p["name"], cls=p["cls"], last=p["last"], prio=round(pr or 0, 1), band=b))
        sorted_procs.sort(key=lambda x: -x["prio"])

        table_rows = ""
        for sp in sorted_procs[:10]:
            pct = min(100, sp["prio"])
            fill_cls = f"fill-{sp['band'].lower()}"
            band_cls = f"band-{sp['band'].lower()}"
            short = sp["name"].split("— ")[-1] if "— " in sp["name"] else sp["name"]
            table_rows += f"""<tr>
                <td style="font-weight:600">{short}</td>
                <td><span style="font-size:0.78em;background:#f1f5f9;padding:2px 8px;border-radius:12px;color:#475569">{sp['cls']}</span></td>
                <td>{sp['last']}</td>
                <td style="font-weight:700">{sp['prio']}</td>
                <td><div class="priority-bar"><div class="fill {fill_cls}" style="width:{pct}%"></div></div></td>
                <td class="{band_cls}">{sp['band']}</td>
            </tr>"""

        st.markdown(f"""
        <div class="dash-section">
            <h3><span class="icon icon-teal">📊</span> Audit Priority Ranking</h3>
            <table class="heatmap-table">
                <thead><tr><th>Process</th><th>Classification</th><th>Last Audit</th><th>Score</th><th>Priority</th><th>Band</th></tr></thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        # Observation Distribution — split into status + rating
        high_c = sum(1 for o in D["obs"] if o["rating"] == "High")
        med_c = sum(1 for o in D["obs"] if o["rating"] == "Medium")
        low_c = sum(1 for o in D["obs"] if o["rating"] == "Low")
        total_obs = max(n_obs, 1)

        # Rating summary with visual bars
        st.markdown(f"""
        <div class="dash-section">
            <h3><span class="icon icon-red">🎯</span> Findings by Rating</h3>
            <div style="margin-bottom:14px">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                    <span style="font-size:0.85em;color:#64748b;width:65px">High</span>
                    <div style="flex:1;height:24px;background:#f1f5f9;border-radius:6px;overflow:hidden">
                        <div style="height:100%;width:{high_c/total_obs*100:.0f}%;background:linear-gradient(90deg,#e11d48,#be123c);border-radius:6px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:0.78em;font-weight:700">{high_c}</div>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                    <span style="font-size:0.85em;color:#64748b;width:65px">Medium</span>
                    <div style="flex:1;height:24px;background:#f1f5f9;border-radius:6px;overflow:hidden">
                        <div style="height:100%;width:{med_c/total_obs*100:.0f}%;background:linear-gradient(90deg,#d97706,#b45309);border-radius:6px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:0.78em;font-weight:700">{med_c}</div>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:10px">
                    <span style="font-size:0.85em;color:#64748b;width:65px">Low</span>
                    <div style="flex:1;height:24px;background:#f1f5f9;border-radius:6px;overflow:hidden">
                        <div style="height:100%;width:{low_c/total_obs*100:.0f}%;background:linear-gradient(90deg,#0d9488,#0f766e);border-radius:6px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:0.78em;font-weight:700">{low_c}</div>
                    </div>
                </div>
            </div>
            <div style="display:flex;gap:12px;margin-top:12px">
                <div style="flex:1;text-align:center;background:#ffe4e6;border-radius:10px;padding:12px">
                    <div style="font-size:1.4em;font-weight:800;color:#be123c">{high_c}</div>
                    <div style="font-size:0.75em;color:#be123c;font-weight:500">HIGH</div>
                </div>
                <div style="flex:1;text-align:center;background:#fef3c7;border-radius:10px;padding:12px">
                    <div style="font-size:1.4em;font-weight:800;color:#92400e">{med_c}</div>
                    <div style="font-size:0.75em;color:#92400e;font-weight:500">MEDIUM</div>
                </div>
                <div style="flex:1;text-align:center;background:#ccfbf1;border-radius:10px;padding:12px">
                    <div style="font-size:1.4em;font-weight:800;color:#0f766e">{low_c}</div>
                    <div style="font-size:0.75em;color:#0f766e;font-weight:500">LOW</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Action status summary
        n_in_prog = sum(a["status"] == "In Progress" for a in A)
        n_open_only = sum(a["status"] == "Open" for a in A)
        n_risk_acc = sum(a["status"] == "Risk Accepted" for a in A)
        act_total = max(len(A), 1)
        closed_pct = round(n_closed / act_total * 100)

        st.markdown(f"""
        <div class="dash-section">
            <h3><span class="icon icon-blue">✅</span> Action Completion</h3>
            <div style="text-align:center;margin:8px 0 14px 0">
                <div style="font-size:2.2em;font-weight:800;color:#0f172a">{closed_pct}%</div>
                <div style="font-size:0.82em;color:#64748b">Actions Closed ({n_closed} of {len(A)})</div>
                <div style="height:8px;background:#e8ecf1;border-radius:4px;margin-top:10px;overflow:hidden">
                    <div style="height:100%;width:{closed_pct}%;background:linear-gradient(90deg,#0d9488,#0f766e);border-radius:4px"></div>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.85em">
                <div style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:#6366f1;flex-shrink:0"></span> Open: <b>{n_open_only}</b></div>
                <div style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:#d97706;flex-shrink:0"></span> In Progress: <b>{n_in_prog}</b></div>
                <div style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:#7c3aed;flex-shrink:0"></span> Evidence Submitted: <b>{n_pending}</b></div>
                <div style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:#e11d48;flex-shrink:0"></span> Overdue: <b>{n_overdue}</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Row 3: Charts side by side ──
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown('<div class="dash-section">', unsafe_allow_html=True)
        st.markdown('<h3 style="margin:0 0 10px 0;font-size:1.02em;font-weight:700;color:#0f172a;font-family:Inter,sans-serif">📊 Priority Score Distribution</h3>', unsafe_allow_html=True)
        df_chart = pd.DataFrame([
            dict(Process=p["name"].split("— ")[-1][:25], Priority=round(calc(p)[2] or 0, 1))
            for p in D["p"]
        ]).set_index("Process").sort_values("Priority", ascending=True)
        st.bar_chart(df_chart, color="#0d9488", horizontal=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_chart2:
        st.markdown('<div class="dash-section">', unsafe_allow_html=True)
        st.markdown('<h3 style="margin:0 0 10px 0;font-size:1.02em;font-weight:700;color:#0f172a;font-family:Inter,sans-serif">📈 Observations by Workflow Stage</h3>', unsafe_allow_html=True)
        status_counts = pd.Series([o["status"] for o in D["obs"]]).value_counts()
        st.bar_chart(status_counts, color="#1e293b")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Row 4: Findings detail + Overdue Actions ──
    col_find, col_over = st.columns(2)

    with col_find:
        findings_rows = []
        for o in D["obs"][:8]:
            dot_cls = "dot-" + o["rating"].lower()
            sbadge = status_badge(o["status"])
            findings_rows.append(
                '<div class="finding-row">'
                f'<div class="finding-dot {dot_cls}"></div>'
                f'<div class="finding-text"><b>#{o["id"]}</b> {o["title"][:55]}</div>'
                f'<div class="finding-meta">{sbadge}</div>'
                '</div>'
            )
        findings_body = "".join(findings_rows)
        st.markdown(
            '<div class="dash-section">'
            '<h3><span class="icon icon-amber">🔍</span> Recent Findings</h3>'
            + findings_body +
            '</div>',
            unsafe_allow_html=True,
        )

    with col_over:
        overdue_acts = [a for a in A if overdue(a)]
        display_acts = overdue_acts if overdue_acts else [a for a in A if a["status"] in ("Open", "In Progress")][:6]
        action_rows = []
        for a in display_acts[:6]:
            is_od = overdue(a)
            dot_class = "dot-high" if is_od else "dot-medium"
            meta_badge = '<span class="badge badge-overdue">OVERDUE</span>' if is_od else status_badge(a["status"])
            action_rows.append(
                '<div class="finding-row">'
                f'<div class="finding-dot {dot_class}"></div>'
                f'<div class="finding-text"><b>#{a["id"]}</b> {a["desc"][:48]}<br>'
                f'<span style="font-size:0.82em;color:#94a3b8">👤 {a["owner"]} · Due: {a["due"]}</span></div>'
                f'<div class="finding-meta">{meta_badge}</div>'
                '</div>'
            )
        section_title = "Overdue Actions" if overdue_acts else "Open Actions"
        section_icon = "icon-red" if overdue_acts else "icon-blue"
        section_emoji = "⚠️" if overdue_acts else "📌"
        if action_rows:
            actions_body = "".join(action_rows)
        else:
            actions_body = '<div style="text-align:center;padding:20px;color:#94a3b8">No overdue actions — all on track ✅</div>'
        st.markdown(
            '<div class="dash-section">'
            f'<h3><span class="icon {section_icon}">{section_emoji}</span> {section_title}</h3>'
            + actions_body +
            '</div>',
            unsafe_allow_html=True,
        )

# ─── Risk Assessment ─────────────────────────────────────────────────────────
elif page == "⚖️ Risk Assessment":
    rows = []
    for p in D["p"]:
        n, q, pr, b = calc(p)
        rows.append({
            "Process": p["name"],
            "Residual Risk": round(n, 1),
            "Qualitative Score": round(q, 1),
            "Combined Priority": round(pr, 1) if pr else 0,
            "Priority Band": b,
        })
    df = pd.DataFrame(rows).sort_values("Combined Priority", ascending=False)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Combined Priority": st.column_config.ProgressColumn("Combined Priority", min_value=0, max_value=100, format="%.1f"),
        },
    )
    st.caption("Priority = weighted normalized residual risk + qualitative score. Mitigation effectiveness factors (1-5) reduce residual risk proportionally.")

    st.markdown("---")
    st.markdown('<div class="section-header"><h3>📝 Score a Process</h3></div>', unsafe_allow_html=True)
    i = st.selectbox("Select Process", range(len(D["p"])), format_func=lambda i: D["p"][i]["name"])
    p = D["p"][i]
    names = [
        "Strategic Significance",
        "Regulatory & Stakeholder Sensitivity",
        "Extent of Change & Transformation",
        "Management & Control Environment Concerns",
        "Assurance Gap & Time Since Last Audit",
    ]
    hint = "**Scoring Guide:** 1 = Low risk / well-controlled · 3 = Moderate · 5 = High risk / critical concern"
    with st.form("score_form"):
        st.markdown(hint)
        s = []
        r = []
        for k, n in enumerate(names):
            a, b = st.columns([1, 2])
            s.append(a.select_slider(n, [1, 2, 3, 4, 5], value=p["s"][k] or 3))
            r.append(b.text_input(f"Rationale — {n}", p["rat"][k]))
        n_, _, _, _ = calc(p)
        q = (sum(s) / 5 - 1) / 4 * 100
        pr = D["cfg"]["wr"] / 100 * (n_ or 0) + D["cfg"]["wq"] / 100 * q
        band = "High" if pr >= D["cfg"]["hi"] else "Medium" if pr >= D["cfg"]["med"] else "Low"
        st.info(f"📊 **Live Preview:** Qualitative {q:.1f} · Residual {n_:.1f} → Combined Priority **{pr:.1f}** ({band}) — {D['cfg']['wr']}% residual + {D['cfg']['wq']}% qualitative")
        if st.form_submit_button("💾 Submit Score"):
            if not all(x.strip() for x in r):
                st.error("⚠️ Rationale is mandatory for every scoring parameter.")
            else:
                p["s"] = s
                p["rat"] = r
                save()
                st.success("✅ Score saved successfully. Priority and plan updated.")
                st.rerun()

# ─── Three-Year Plan ─────────────────────────────────────────────────────────
elif page == "📅 Three-Year Plan":
    L, used, C = plan()
    st.info(f"📊 **Capacity Calculation:** {D['cfg']['n']} staff × ({D['cfg']['days']} working days − {D['cfg']['leave']} leave − {D['cfg']['train']} training − {D['cfg']['admin']} admin) × (1 − {D['cfg']['cont']}% contingency) × {D['cfg']['share']}% fieldwork = **{C} person-days/year**")

    gap = [x["name"] for x in L if not x.get("year")]
    if gap:
        st.error("⚠️ **Capacity Constraint — Unscheduled Audits:** " + "; ".join(gap))

    # ── Editable Plan Table ──
    if MGR:
        st.markdown('---')
        st.markdown('<div class="section-header"><h3>📝 Modify Audit Plan</h3></div>', unsafe_allow_html=True)
        st.caption("Change the scheduled year or estimated days for any audit entity. Click **Save Plan Changes** to apply.")

        plan_rows = []
        for x in L:
            short_name = x['name'].split('— ')[-1] if '— ' in x['name'] else x['name']
            plan_rows.append({
                "Process": short_name,
                "Priority Band": x["band"],
                "Priority Score": round(x["prio"], 1),
                "Last Audit": x["last"],
                "Estimated Days": x["days"],
                "Scheduled Year": x.get("year") or 0,
                "_idx": x["i"],
            })

        plan_df = pd.DataFrame(plan_rows)
        edited_plan = st.data_editor(
            plan_df,
            use_container_width=True,
            hide_index=True,
            key="plan_editor",
            disabled=["Process", "Priority Band", "Priority Score", "Last Audit", "_idx"],
            column_config={
                "Process": st.column_config.TextColumn("Process", width="large"),
                "Priority Band": st.column_config.TextColumn("Band", width="small"),
                "Priority Score": st.column_config.ProgressColumn("Priority", min_value=0, max_value=100, format="%.1f"),
                "Last Audit": st.column_config.NumberColumn("Last Audit", format="%d"),
                "Estimated Days": st.column_config.NumberColumn("Est. Days", min_value=10, max_value=120, step=5),
                "Scheduled Year": st.column_config.SelectboxColumn("Year", options=[0, 2027, 2028, 2029], help="Set to 0 to unschedule"),
                "_idx": None,
            },
        )

        if st.button("💾 Save Plan Changes"):
            changes_made = False
            for _, row in edited_plan.iterrows():
                idx = int(row["_idx"])
                orig = next((x for x in L if x["i"] == idx), None)
                if orig is None:
                    continue

                new_year = int(row["Scheduled Year"]) if row["Scheduled Year"] else 0
                new_days = int(row["Estimated Days"]) if row["Estimated Days"] else orig["days"]
                old_year = orig.get("year") or 0

                if new_year != old_year or new_days != orig["days"]:
                    if new_year in (2027, 2028, 2029):
                        D["ov"][str(idx)] = dict(
                            year=new_year,
                            why=f"Plan modified: moved to {new_year}, {new_days} days (by {me})",
                            by=me,
                            days=new_days,
                        )
                    elif new_year == 0 and str(idx) in D["ov"]:
                        del D["ov"][str(idx)]
                    changes_made = True

            if changes_made:
                save()
                st.success("✅ Plan changes saved successfully.")
                st.rerun()
            else:
                st.info("ℹ️ No changes detected.")

    # ── Year Columns View ──
    st.markdown('---')
    L, used, C = plan()  # Recalculate after potential edits

    cols = st.columns(3)
    for col, y in zip(cols, [2027, 2028, 2029]):
        with col:
            pct = min(1.0, used[y] / C) if C > 0 else 0
            st.markdown(f"### 📅 {y}")
            st.progress(pct, text=f"{used[y]} / {C} person-days ({pct*100:.0f}%)")
            year_items = [x for x in L if x.get("year") == y]
            for x in year_items:
                short = x['name'].split('— ')[-1] if '— ' in x['name'] else x['name']
                is_override = str(x["i"]) in D["ov"]
                override_tag = ' <span style="font-size:0.72em;background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:10px;font-weight:600">MANUAL</span>' if is_override else ''
                st.markdown(
                    f"""<div class="status-card">
                        <div style="font-weight:700;color:#0f172a;margin-bottom:4px">{short}{override_tag}</div>
                        <div>{rating_badge(x['band'])} <span style="font-size:0.85em;color:#64748b">Priority {x['prio']:.1f} · {x['days']} days</span></div>
                        <div style="font-size:0.8em;color:#94a3b8;margin-top:4px">{x['why']}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                # Inline move controls for managers
                if MGR:
                    other_years = [yr for yr in [2027, 2028, 2029] if yr != y]
                    move_cols = st.columns(len(other_years) + 1)
                    for mi, my in enumerate(other_years):
                        if move_cols[mi].button(f"➡️ {my}", key=f"move_{x['i']}_{my}"):
                            D["ov"][str(x["i"])] = dict(
                                year=my,
                                why=f"Moved from {y} to {my} (by {me})",
                                by=me,
                            )
                            save()
                            st.rerun()
                    if is_override and move_cols[-1].button("🗑️ Clear", key=f"clear_ov_{x['i']}"):
                        del D["ov"][str(x["i"])]
                        save()
                        st.rerun()

    # ── Unscheduled items ──
    unscheduled = [x for x in L if not x.get("year")]
    if unscheduled:
        st.markdown('---')
        st.markdown('<div class="section-header"><h3>🚫 Unscheduled Audits (Capacity Constraint)</h3></div>', unsafe_allow_html=True)
        for x in unscheduled:
            short = x['name'].split('— ')[-1] if '— ' in x['name'] else x['name']
            st.markdown(
                f"""<div class="status-card" style="border-left:4px solid #e11d48">
                    <div style="font-weight:700;color:#0f172a;margin-bottom:4px">{short}</div>
                    <div>{rating_badge(x['band'])} <span style="font-size:0.85em;color:#64748b">Priority {x['prio']:.1f} · {x['days']} days</span></div>
                    <div style="font-size:0.8em;color:#e11d48;margin-top:4px">⚠️ {x['why']}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            if MGR:
                sched_cols = st.columns(3)
                for si, sy in enumerate([2027, 2028, 2029]):
                    if sched_cols[si].button(f"📅 Schedule → {sy}", key=f"sched_{x['i']}_{sy}"):
                        D["ov"][str(x["i"])] = dict(
                            year=sy,
                            why=f"Manually scheduled to {sy} (by {me})",
                            by=me,
                        )
                        save()
                        st.rerun()

    if MGR:
        st.markdown("---")
        st.markdown('<div class="section-header"><h3>🔧 Manual Override</h3></div>', unsafe_allow_html=True)
        st.caption("Justification is mandatory for all manual schedule overrides.")
        a, b, c_ = st.columns([2, 1, 2])
        oi = a.selectbox("Process", [x["i"] for x in L], format_func=lambda i: D["p"][i]["name"])
        oy = b.selectbox("Target Year", [2027, 2028, 2029])
        ow = c_.text_input("Justification")
        if st.button("✅ Apply Override"):
            if ow.strip():
                D["ov"][str(oi)] = dict(year=oy, why=ow, by=me)
                save()
                st.rerun()
            else:
                st.error("⚠️ Justification is required for all overrides.")

        # Clear all overrides button
        if D["ov"] and st.button("🔄 Clear All Overrides"):
            D["ov"] = {}
            save()
            st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-header"><h3>📄 Plan Versions</h3></div>', unsafe_allow_html=True)
    st.caption("An approved plan is frozen until a revised version is approved. The submitter cannot approve their own plan (segregation of duties).")

    if MGR and st.button("📤 Submit Current Plan for Approval"):
        D["plans"] = [dict(v, status="Superseded") if v["status"] == "Submitted" else v for v in D["plans"]]
        D["plans"].append(dict(
            id=len(D["plans"]) + 1,
            status="Submitted",
            by=me,
            ts=str(dt.datetime.now())[:16],
            items=[(x["name"], x.get("year")) for x in L],
        ))
        save()
        st.rerun()

    for v in D["plans"]:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"**v{v['id']}** · {status_badge(v['status'])} · submitted by **{v['by']}** · {v['ts']}", unsafe_allow_html=True)
        if v["status"] == "Submitted" and HEAD and c2.button("✅ Approve", key=f"ap{v['id']}"):
            if v["by"] == me:
                st.error("⚠️ Segregation of duties: the submitter cannot approve their own plan.")
            else:
                for w in D["plans"]:
                    if w["status"] == "Approved":
                        w["status"] = "Superseded"
                v["status"] = "Approved"
                save()
                st.rerun()

# ─── RCM ─────────────────────────────────────────────────────────────────────
elif page == "🛡️ Risk & Control Matrix":
    pi = st.selectbox("Select Process", range(len(D["p"])), format_func=lambda i: D["p"][i]["name"])
    p = D["p"][pi]

    # Display process info
    _, _, pr, band = calc(p)
    st.markdown(
        f"""<div class="status-card" style="border-left:4px solid {'#e11d48' if band=='High' else '#d97706' if band=='Medium' else '#0d9488'}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-weight:700;font-size:1.1em;color:#0f172a">{p['name']}</div>
                    <div style="font-size:0.85em;color:#64748b">Classification: {p['cls']} · Last Audited: {p['last']}</div>
                </div>
                <div style="text-align:right">
                    {rating_badge(band)}
                    <div style="font-size:0.85em;color:#64748b;margin-top:4px">Priority Score: {pr:.1f}</div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.caption("Control effectiveness ratings: 1 = Ineffective, 2 = Needs improvement, 3 = Adequate, 4 = Effective, 5 = Highly effective. Higher effectiveness reduces residual risk.")

    df = st.data_editor(
        pd.DataFrame(p["rcm"]),
        num_rows="dynamic",
        use_container_width=True,
        key=f"rcm_{pi}",
        column_config={
            "risk": st.column_config.TextColumn("Risk Description", width="large"),
            "ctrl": st.column_config.TextColumn("Control Description", width="large"),
            "i": st.column_config.NumberColumn("Impact (1-5)", min_value=1, max_value=5, help="1=Low, 5=Critical"),
            "l": st.column_config.NumberColumn("Likelihood (1-5)", min_value=1, max_value=5, help="1=Rare, 5=Almost certain"),
            "e": st.column_config.NumberColumn("Effectiveness (1-5)", min_value=1, max_value=5, help="1=Ineffective, 5=Highly effective"),
            "note": st.column_config.TextColumn("Assessment Notes", width="medium"),
        },
    )
    if st.button("💾 Save RCM Changes"):
        p["rcm"] = df.dropna(subset=["i", "l", "e"]).astype({"i": int, "l": int, "e": int}).to_dict("records")
        save()
        st.success("✅ Risk & Control Matrix saved successfully.")
        st.rerun()

    # RCM Summary
    st.markdown("---")
    st.markdown('<div class="section-header"><h3>📊 Residual Risk Summary</h3></div>', unsafe_allow_html=True)
    if p["rcm"]:
        rcm_df = pd.DataFrame([
            {
                "Risk": r["risk"][:60] + "..." if len(r.get("risk", "")) > 60 else r.get("risk", ""),
                "Impact": r["i"],
                "Likelihood": r["l"],
                "Effectiveness": r["e"],
                "Inherent Risk": r["i"] * r["l"],
                "Residual Risk": round(r["i"] * r["l"] * (1 - MIT[r["e"]]), 1),
            }
            for r in p["rcm"]
        ])
        st.dataframe(rcm_df, use_container_width=True, hide_index=True)

# ─── Observations ────────────────────────────────────────────────────────────
elif page == "🔍 Observations":
    # Summary metrics
    obs_statuses = [o["status"] for o in D["obs"]]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📋 Total Observations", len(D["obs"]))
    m2.metric("🔴 High-Rated", sum(1 for o in D["obs"] if o["rating"] == "High"))
    m3.metric("🟡 Medium-Rated", sum(1 for o in D["obs"] if o["rating"] == "Medium"))
    m4.metric("🟢 Low-Rated", sum(1 for o in D["obs"] if o["rating"] == "Low"))

    st.markdown("---")

    with st.expander("➕ Create New Observation"):
        with st.form("new_obs_form"):
            t = st.text_input("📝 Observation Title")
            pi = st.selectbox("📂 Related Process", range(len(D["p"])), format_func=lambda i: D["p"][i]["name"])
            col_a, col_b = st.columns(2)
            cnd = col_a.text_area("🔍 Condition (What was found)", height=120)
            rc = col_b.text_area("💡 Recommendation (What should be done)", height=120)
            rt = st.selectbox("⚖️ Rating", ["High", "Medium", "Low"], 1)
            if st.form_submit_button("💾 Save as Draft") and t:
                D["obs"].append(dict(
                    id=len(D["obs"]) + 1,
                    title=t, pi=pi, rating=rt, status="Draft",
                    prep=me, cond=cnd, reco=rc, resp="", notes="", hist=[],
                ))
                save()
                st.rerun()

    for o in D["obs"]:
        header = f"#{o['id']} · {o['title']}"
        with st.expander(header):
            st.markdown(
                f"""<div style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
                    {rating_badge(o['rating'])} {status_badge(o['status'])}
                    <span style="font-size:0.85em;color:#64748b">Prepared by: <b>{o['prep']}</b></span>
                </div>""",
                unsafe_allow_html=True,
            )

            st.markdown(f"**📂 Process:** {D['p'][o['pi']]['name']}")
            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**🔍 Condition:**")
                st.markdown(o["cond"])
            with col2:
                st.markdown("**💡 Recommendation:**")
                st.markdown(o["reco"])

            if o["resp"]:
                st.markdown("---")
                st.markdown("**📋 Management Response:**")
                st.info(o["resp"])

            if o["notes"]:
                st.markdown("---")
                st.caption("🔒 Internal Notes (not visible to auditees): " + o["notes"])

            st.markdown("---")
            cm = st.text_input("💬 Comment / Response", key=f"comment_{o['id']}")
            s = o["status"]
            b = st.columns(4)

            def mv(n):
                o["hist"].append(f"{dt.datetime.now():%Y-%m-%d %H:%M} {me}: {s} → {n} | {cm}")
                o["status"] = n
                save()
                st.rerun()

            if s == "Draft" and b[0].button("📤 Submit for Review", key=f"submit_{o['id']}"):
                mv("Manager Review")
            if s == "Manager Review" and MGR:
                if b[0].button("✅ Manager Approve", key=f"mgr_approve_{o['id']}"):
                    if me == o["prep"]:
                        st.error("⚠️ Segregation of duties: the preparer cannot review their own work.")
                    else:
                        mv("HIA Approval")
            if s in ("Manager Review", "HIA Approval") and MGR and b[1].button("↩️ Return for Revision", key=f"return_{o['id']}"):
                if cm:
                    o["notes"] += f"\n{me}: {cm}"
                    mv("Draft")
                else:
                    st.error("⚠️ A comment is required when returning an observation.")
            if s == "HIA Approval" and HEAD and b[0].button("✅ Approve & Release", key=f"hia_approve_{o['id']}"):
                if me == o["prep"]:
                    st.error("⚠️ Segregation of duties: the preparer cannot give final approval.")
                else:
                    mv("Released")
            if s == "Released" and b[0].button("📋 Record Management Response", key=f"mgmt_resp_{o['id']}"):
                if cm:
                    o["resp"] = cm
                    mv("Management Response")
                else:
                    st.error("⚠️ A management response is required.")
            if s == "Management Response" and b[0].button("🤝 Agree Actions", key=f"agree_{o['id']}"):
                if any(a["obs"] == o["id"] for a in D["act"]):
                    mv("Action Agreed")
                else:
                    st.error("⚠️ At least one action must be linked before agreeing.")
            if s == "Action Agreed" and HEAD and b[0].button("📄 Issue Final", key=f"final_{o['id']}"):
                if me == o["prep"]:
                    st.error("⚠️ Segregation of duties: the preparer cannot finalise.")
                else:
                    mv("Final Issued")

            if o["hist"]:
                st.markdown("**📜 Audit Trail:**")
                st.code("\n".join(o["hist"]))

# ─── Action Tracking ─────────────────────────────────────────────────────────
elif page == "✅ Action Tracking":
    # Summary metrics
    acts = D["act"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📋 Total Actions", len(acts))
    m2.metric("📌 Open / In Progress", sum(a["status"] in ("Open", "In Progress") for a in acts))
    m3.metric("🔴 Overdue", sum(overdue(a) for a in acts))
    m4.metric("✅ Closed", sum(a["status"] == "Closed" for a in acts))

    st.markdown("---")

    with st.expander("➕ Add New Action"):
        with st.form("new_action_form"):
            ob = st.selectbox("🔍 Linked Observation", [o["id"] for o in D["obs"]], format_func=lambda oid: f"#{oid} — {next((o['title'] for o in D['obs'] if o['id']==oid), '')}")
            d = st.text_input("📝 Action Description")
            col_a, col_b = st.columns(2)
            ow = col_a.text_input("👤 Accountable Owner")
            du = col_b.date_input("📅 Due Date")
            if st.form_submit_button("💾 Add Action") and d:
                D["act"].append(dict(
                    id=len(D["act"]) + 1,
                    obs=ob, desc=d, owner=ow,
                    due=str(du), orig=str(du),
                    status="Open", evid="", why="",
                ))
                save()
                st.rerun()

    for a in acts:
        is_overdue = overdue(a)
        border_color = "#e11d48" if is_overdue else "#e8ecf1"
        obs_title = next((o["title"] for o in D["obs"] if o["id"] == a["obs"]), f"Observation #{a['obs']}")

        st.markdown(
            f"""<div class="status-card" style="border-left:4px solid {border_color}">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                        <div style="font-weight:700;color:#0f172a;font-size:1.05em">#{a['id']} · {a['desc']}</div>
                        <div style="font-size:0.85em;color:#64748b;margin-top:4px">
                            👤 {a['owner']} · 📅 Due: {a['due']} (Original: {a['orig']}) · 🔍 {obs_title[:40]}
                        </div>
                    </div>
                    <div style="text-align:right">
                        {status_badge(a['status'])}
                        {'<div class="badge badge-overdue" style="margin-top:4px">⚠️ OVERDUE</div>' if is_overdue else ''}
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        c = st.columns([3, 1, 1, 1])
        t = c[0].text_input("Evidence / Reason", key=f"evidence_{a['id']}", label_visibility="collapsed", placeholder="Enter evidence description or reason...")
        if a["status"] in ("Open", "In Progress") and c[1].button("📤 Submit Evidence", key=f"submit_ev_{a['id']}") and t:
            a["status"] = "Evidence Submitted"
            a["evid"] = t
            save()
            st.rerun()
        if a["status"] == "Evidence Submitted":
            if c[1].button("✅ Validate & Close", key=f"validate_{a['id']}"):
                a["status"] = "Closed"
                save()
                st.rerun()
            if c[2].button("↩️ Return", key=f"return_act_{a['id']}"):
                a["status"] = "In Progress"
                a["why"] = t
                save()
                st.rerun()
        if HEAD and a["status"] in ("Open", "In Progress") and c[2].button("⚠️ Accept Risk", key=f"accept_{a['id']}") and t:
            a["status"] = "Risk Accepted"
            a["why"] = t
            save()
            st.rerun()
        if a["evid"]:
            st.caption(f"📎 Evidence: {a['evid']}")
        st.divider()

# ─── Settings ────────────────────────────────────────────────────────────────
else:
    c = D["cfg"]
    st.info("⚙️ Planning weights must total 100%. Adjust capacity assumptions to reflect your team's available resources.")

    with st.form("settings_form"):
        st.markdown("### ⚖️ Priority Weighting")
        a, b = st.columns(2)
        c["wr"] = a.number_input("Residual Risk Weight %", 0, 100, c["wr"])
        c["wq"] = b.number_input("Qualitative Score Weight %", 0, 100, c["wq"])

        st.markdown("### 👥 Team Capacity")
        cols = st.columns(4)
        params = [
            ("n", "Audit Staff Count"),
            ("days", "Working Days per Year"),
            ("leave", "Leave Days"),
            ("train", "Training Days"),
        ]
        for idx, (k, l) in enumerate(params):
            c[k] = cols[idx].number_input(l, 0, 365, c[k])

        st.markdown("### 📊 Planning Parameters")
        cols2 = st.columns(3)
        c["admin"] = cols2[0].number_input("Admin Days", 0, 365, c["admin"])
        c["cont"] = cols2[1].number_input("Contingency %", 0, 100, c["cont"])
        c["share"] = cols2[2].number_input("Fieldwork Share %", 0, 100, c["share"])

        c["agg"] = st.selectbox("Risk Aggregation Method", ["max", "avg"], 0 if c["agg"] == "max" else 1,
                                help="'max' uses the highest residual risk; 'avg' uses the average across all controls")

        if st.form_submit_button("💾 Save Settings"):
            if c["wr"] + c["wq"] != 100:
                st.error("⚠️ Priority weights must total exactly 100%.")
            else:
                save()
                st.success("✅ Settings saved successfully.")
