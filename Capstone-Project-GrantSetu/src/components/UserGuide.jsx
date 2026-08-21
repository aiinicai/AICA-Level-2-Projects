import React from 'react';
import { useGrant } from '../context/GrantContext';
import { BookOpen, ShieldCheck, FileText, Briefcase, Network, Receipt, FileCheck, Folder, HelpCircle } from 'lucide-react';

export const UserGuide = () => {
  const { handleResetDemoData } = useGrant();

  return (
    <div className="user-guide-view">
      <div className="card-header" style={{ marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BookOpen size={24} style={{ color: 'var(--color-primary)' }} />
            User Operating Manual & Statutory Compliance Guide
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Complete step-by-step instructions for Indian NGO directors, proposal writers, finance officers, and project auditors.
          </p>
        </div>

        <button className="btn btn-primary" onClick={handleResetDemoData}>
          Load Sample Demo Data
        </button>
      </div>

      {/* Workflow Steps Overview */}
      <div className="card" style={{ background: 'linear-gradient(135deg, var(--bg-card) 0%, rgba(30, 41, 59, 0.8) 100%)' }}>
        <h3 className="card-title" style={{ marginBottom: '16px' }}>
          <HelpCircle size={18} style={{ color: 'var(--color-secondary)' }} />
          End-to-End Grant Management Workflow (7 Key Modules)
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
          <div style={{ padding: '16px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="badge badge-active">Module 1</span>
              <strong style={{ fontSize: '0.95rem' }}>NGO Setup & Statutory Vault</strong>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              Enter NITI Aayog Darpan ID, PAN, TAN, 12A/80G URNs, CSR-1 Registration, and SBI New Delhi FCRA bank account details. System alerts 90 days before tax renewal deadlines.
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="badge badge-active">Module 2</span>
              <strong style={{ fontSize: '0.95rem' }}>Proposal Studio & Document Uploads</strong>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              Draft grant proposals, attach Pitch Decks / Detailed Project Reports (DPRs), construct Logical Frameworks, convert FX budgets (USD/EUR/GBP to INR), and validate admin caps.
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="badge badge-active">Module 3</span>
              <strong style={{ fontSize: '0.95rem' }}>Non-FCRA Sub-Granting ERP</strong>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              Award sub-grants to grassroots partner CBOs/NGOs under Domestic CSR grants. Enforces automatic FCRA 2020 ban on foreign grant sub-granting while tracking partner UCs.
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="badge badge-active">Module 4</span>
              <strong style={{ fontSize: '0.95rem' }}>Expense Vouching & Invoice Uploads</strong>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              Log expense vouchers tagging each expense to its grant line item, payment bank account, and upload vendor tax invoices or bills. Track real-time Budget vs Actuals (BvA) burn rates.
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="badge badge-active">Module 5</span>
              <strong style={{ fontSize: '0.95rem' }}>Form GFR 12-A UC Generator</strong>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              Auto-generate standard Indian Utilization Certificates (Form GFR 12-A) with Opening Balance, Funds Received, Interest Earned, and Spent Amount. Includes CA UDIN block for PDF export.
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="badge badge-active">Module 6</span>
              <strong style={{ fontSize: '0.95rem' }}>Central Document Vault</strong>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              Central repository aggregating all uploaded proposal pitch decks, vendor invoices, sub-grant MoUs, tax certificates, and UCs with single-click download capabilities.
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="badge badge-active">Module 7</span>
              <strong style={{ fontSize: '0.95rem' }}>Grant Closure & Archival</strong>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              Execute 4-step grant closure checklist: Technical report, Audited UC, Asset register handover, and Donor No Objection Certificate (NOC). Formally archive completed grants.
            </p>
          </div>
        </div>
      </div>

      {/* Statutory Rules Reference Guide */}
      <div className="card">
        <h3 className="card-title" style={{ marginBottom: '16px' }}>
          <ShieldCheck size={18} style={{ color: 'var(--color-primary)' }} />
          Indian NGO Statutory & Regulatory Compliance Reference Cheat-Sheet
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.88rem' }}>
          <div style={{ borderLeft: '4px solid var(--color-danger)', paddingLeft: '14px' }}>
            <strong style={{ color: 'var(--text-main)' }}>1. FCRA 2020 Amendment Section 7 Ban on Sub-Granting:</strong>
            <ul style={{ paddingLeft: '20px', marginTop: '4px', color: 'var(--text-muted)' }}>
              <li>Foreign contribution grants <strong>CANNOT be sub-granted</strong> or transferred to any other NGO, regardless of whether the receiving NGO has FCRA registration.</li>
              <li>Sub-granting is legally valid ONLY under Domestic CSR, Central/State Govt Grants, or HNI domestic funds.</li>
              <li>All foreign grants must be received strictly into SBI New Delhi Main Branch Account (# 40019283741). Administrative cap is max 20%.</li>
            </ul>
          </div>

          <div style={{ borderLeft: '4px solid var(--color-secondary)', paddingLeft: '14px' }}>
            <strong style={{ color: 'var(--text-main)' }}>2. Corporate Social Responsibility (CSR) - Companies Act 2013 Sec 135:</strong>
            <ul style={{ paddingLeft: '20px', marginTop: '4px', color: 'var(--text-muted)' }}>
              <li>NGO must possess active <strong>CSR-1 Registration Number</strong> from Ministry of Corporate Affairs (MCA).</li>
              <li>Administrative overheads for CSR projects are generally capped at <strong>5%</strong> of total CSR expenditure.</li>
              <li>Sub-granting to grassroots implementation partners is permitted under CSR MoUs.</li>
            </ul>
          </div>

          <div style={{ borderLeft: '4px solid var(--color-success)', paddingLeft: '14px' }}>
            <strong style={{ color: 'var(--text-main)' }}>3. Income Tax Act 12A & 80G Renewal Rules:</strong>
            <ul style={{ paddingLeft: '20px', marginTop: '4px', color: 'var(--text-muted)' }}>
              <li>12A and 80G re-validations are valid for 5 years. Renewal applications (Form 10A / 10AB) must be submitted 6 months prior to expiry.</li>
              <li>Filing of Form 10B / 10BB audit report and Form 9A / 10 accumulation notices required for tax exemption.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
