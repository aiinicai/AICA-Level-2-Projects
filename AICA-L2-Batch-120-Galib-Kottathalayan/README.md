# 🏛️ AuditHub — Internal Audit Lifecycle Management

A comprehensive **Streamlit-based** Internal Audit management platform designed for a Sovereign Wealth Fund's Internal Audit Division.

## Features

### 📊 Dashboard
- Real-time KPI metrics: audit universe size, observations, open/overdue actions
- Audit priority visualization by process
- Observations breakdown by status and risk rating
- Activity summary cards with at-a-glance insights

### ⚖️ Risk Assessment
- Weighted risk-based audit prioritization methodology
- Five qualitative scoring dimensions with mandatory rationale
- Live priority preview with combined residual + qualitative scores
- Progress-bar visualization for priority scores

### 📅 Three-Year Audit Plan
- Capacity-driven rolling plan (2027–2029)
- Risk-based scheduling with automatic capacity allocation
- Manual override capability with mandatory justification
- Plan versioning with segregation-of-duties approval workflow

### 🛡️ Risk & Control Matrix (RCM)
- **50+ risk-control pairs** across 15 auditable processes (3–4 per process)
- Impact, likelihood and control effectiveness scoring (1–5 scale)
- Residual risk calculation with mitigation effectiveness factors
- Inline residual risk summary with inherent vs. residual comparison

### 🔍 Observations
- **12 detailed observations** with comprehensive conditions and recommendations
- Full lifecycle workflow: Draft → Manager Review → HIA Approval → Released → Management Response → Action Agreed → Final Issued
- Segregation of duties enforcement throughout the approval chain
- Complete audit trail with timestamped history

### ✅ Action Tracking
- **15 remediation actions** linked to observations
- Status tracking: Open, In Progress, Evidence Submitted, Closed, Risk Accepted
- Overdue action highlighting with visual alerts
- Evidence submission and validation workflow

### ⚙️ Settings
- Configurable planning weights (residual risk vs. qualitative score)
- Team capacity parameters (staff, working days, leave, training, admin)
- Contingency and fieldwork share allocation
- Risk aggregation method selection (max vs. average)

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Technology Stack
- **Frontend:** Streamlit with custom CSS theming
- **Data:** JSON-based persistence
- **Language:** Python 3.10+
