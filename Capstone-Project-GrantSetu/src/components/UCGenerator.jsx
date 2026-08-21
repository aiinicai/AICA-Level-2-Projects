import React, { useState } from 'react';
import { useGrant } from '../context/GrantContext';
import { FileCheck, Printer, Download, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { formatINR, formatDate, getIndianFinancialYear } from '../utils/formatters';

export const UCGenerator = () => {
  const { ngoProfile, grants, selectedGrantId, setSelectedGrantId } = useGrant();

  const activeGrants = grants.filter((g) => g.status === 'Active' || g.status === 'Pending Closure' || g.status === 'Completed');
  const currentGrant = grants.find((g) => g.id === selectedGrantId) || activeGrants[0] || grants[0];

  const [ucDetails, setUcDetails] = useState({
    financialYear: getIndianFinancialYear(),
    openingBalance: 0,
    interestEarned: 0,
    caName: 'M/s Joshi & Kulkarni Chartered Accountants',
    caMembershipNo: '048291',
    caFirmRegNo: '104928W',
    udin: `25${Math.floor(100000 + Math.random() * 900000)}AAAAAX${Math.floor(1000 + Math.random() * 9000)}`,
    signingDate: new Date().toISOString().slice(0, 10),
    signatoryName: ngoProfile.contactPerson || 'Dr. Anjali Deshmukh',
    signatoryDesignation: 'Executive Director / Managing Trustee'
  });

  if (!currentGrant) {
    return (
      <div className="card">
        <h3>No Grant Available for Utilization Certificate</h3>
      </div>
    );
  }

  const received = currentGrant.receivedAmount || 0;
  const spent = currentGrant.spentAmount || 0;
  const totalAvailable = Number(ucDetails.openingBalance) + received + Number(ucDetails.interestEarned);
  const closingBalance = totalAvailable - spent;

  const handlePrintUC = () => {
    window.print();
  };

  return (
    <div className="uc-generator-view">
      <div className="card-header no-print" style={{ marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileCheck size={24} style={{ color: 'var(--color-primary)' }} />
            Official Utilization Certificate (UC) Generator (Form GFR 12-A)
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Generate statutory GFR 12-A / CSR Utilization Certificates with CA UDIN verification for submission to Ministry / Donor Foundations.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <select
            className="form-control"
            style={{ width: '280px', fontWeight: 600 }}
            value={currentGrant.id}
            onChange={(e) => setSelectedGrantId(e.target.value)}
          >
            {grants.map((g) => (
              <option key={g.id} value={g.id}>
                {g.title} ({g.id})
              </option>
            ))}
          </select>

          <button className="btn btn-primary" onClick={handlePrintUC}>
            <Printer size={18} /> Print / Save as PDF
          </button>
        </div>
      </div>

      {/* Editable Controls (Hidden during print) */}
      <div className="card no-print" style={{ marginBottom: '24px' }}>
        <h3 className="card-title" style={{ marginBottom: '16px' }}>
          <ShieldCheck size={18} style={{ color: 'var(--color-secondary)' }} />
          UC Certificate Parameters & CA UDIN Setup
        </h3>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Financial Year (FY)</label>
            <input
              type="text"
              className="form-control"
              value={ucDetails.financialYear}
              onChange={(e) => setUcDetails({ ...ucDetails, financialYear: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Opening Unspent Balance (₹)</label>
            <input
              type="number"
              className="form-control"
              value={ucDetails.openingBalance}
              onChange={(e) => setUcDetails({ ...ucDetails, openingBalance: Number(e.target.value) })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Bank Interest Accrued (₹)</label>
            <input
              type="number"
              className="form-control"
              value={ucDetails.interestEarned}
              onChange={(e) => setUcDetails({ ...ucDetails, interestEarned: Number(e.target.value) })}
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Chartered Accountant Firm</label>
            <input
              type="text"
              className="form-control"
              value={ucDetails.caName}
              onChange={(e) => setUcDetails({ ...ucDetails, caName: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">CA Membership / Firm Reg No.</label>
            <input
              type="text"
              className="form-control"
              value={ucDetails.caMembershipNo}
              onChange={(e) => setUcDetails({ ...ucDetails, caMembershipNo: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">UDIN (ICAI Unique Ref)</label>
            <input
              type="text"
              className="form-control"
              value={ucDetails.udin}
              onChange={(e) => setUcDetails({ ...ucDetails, udin: e.target.value })}
            />
          </div>
        </div>
      </div>

      {/* Printable Formal GFR 12-A Utilization Certificate Document */}
      <div className="card printable-uc-doc" style={{ background: '#ffffff', color: '#0f172a', padding: '40px', borderRadius: 'var(--radius-lg)' }}>
        {/* Document Header */}
        <div style={{ textAlign: 'center', borderBottom: '2px solid #0f172a', paddingBottom: '16px', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            FORM GFR 12 - A
          </h2>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#475569' }}>
            [See Rule 238 (1) of General Financial Rules 2017 / CSR Rules]
          </div>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginTop: '8px', color: '#1e293b' }}>
            UTILIZATION CERTIFICATE FOR THE FINANCIAL YEAR {ucDetails.financialYear}
          </h3>
        </div>

        {/* Organization & Grant Info */}
        <div style={{ marginBottom: '24px', fontSize: '0.9rem', lineHeight: '1.7' }}>
          <p>
            Certified that out of <strong>{formatINR(received)}</strong> of Grants-in-aid sanctioned during the year{' '}
            <strong>{ucDetails.financialYear}</strong> in favor of <strong>{ngoProfile.name}</strong> (Registered Trust/Society under Darpan ID:{' '}
            <strong>{ngoProfile.darpanId}</strong>) under Donor MoU Reference No. <strong>{currentGrant.sanctionOrderNo}</strong> for the project{' '}
            <strong>"{currentGrant.title}"</strong>, the financial breakdown is as under:
          </p>
        </div>

        {/* Financial Calculation Table */}
        <div className="table-responsive" style={{ marginBottom: '28px' }}>
          <table className="custom-table" style={{ color: '#0f172a', borderColor: '#cbd5e1' }}>
            <thead>
              <tr style={{ background: '#f1f5f9' }}>
                <th style={{ color: '#1e293b' }}>Sl No.</th>
                <th style={{ color: '#1e293b' }}>Particulars</th>
                <th style={{ color: '#1e293b', textAlign: 'right' }}>Amount in Rupees (₹)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>1.</td>
                <td>Unspent balance carried forward from previous financial year</td>
                <td style={{ textAlign: 'right' }}>{formatINR(ucDetails.openingBalance)}</td>
              </tr>
              <tr>
                <td>2.</td>
                <td>Grant-in-Aid received during the current Financial Year ({ucDetails.financialYear})</td>
                <td style={{ textAlign: 'right' }}>{formatINR(received)}</td>
              </tr>
              <tr>
                <td>3.</td>
                <td>Interest earned on Grant Funds in Designated Bank Account</td>
                <td style={{ textAlign: 'right' }}>{formatINR(ucDetails.interestEarned)}</td>
              </tr>
              <tr style={{ fontWeight: 700, background: '#f8fafc' }}>
                <td><strong>4.</strong></td>
                <td><strong>TOTAL FUNDS AVAILABLE (1 + 2 + 3)</strong></td>
                <td style={{ textAlign: 'right' }}><strong>{formatINR(totalAvailable)}</strong></td>
              </tr>
              <tr>
                <td>5.</td>
                <td>Actual Expenditure incurred for the purpose of the Grant</td>
                <td style={{ textAlign: 'right', color: '#ea580c', fontWeight: 700 }}>{formatINR(spent)}</td>
              </tr>
              <tr style={{ fontWeight: 800, background: '#f1f5f9' }}>
                <td><strong>6.</strong></td>
                <td><strong>CLOSING UNSPENT BALANCE (Carried Forward / Refundable)</strong></td>
                <td style={{ textAlign: 'right', color: '#16a34a' }}><strong>{formatINR(closingBalance)}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* GFR Verification Declaration Clause */}
        <div style={{ fontSize: '0.88rem', lineHeight: '1.6', marginBottom: '36px' }}>
          <p>
            Certified that I have satisfied myself that the conditions on which the grants-in-aid was sanctioned have been duly fulfilled / are being fulfilled and that I have exercised the following checks to see that the money was actually utilized for the purpose for which it was sanctioned:
          </p>
          <ol style={{ paddingLeft: '20px', marginTop: '8px' }}>
            <li>Kinds of checks exercised: Verified Original Vouchers, Bills, Bank Statements, and Payment Receipts.</li>
            <li>Physical verification of asset register and target beneficiary field attendance logs.</li>
            <li>Strict compliance with FCRA 2020 Amendment rules & CSR 5% administrative cap.</li>
          </ol>
        </div>

        {/* Signatures & CA Block */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', paddingTop: '20px', borderTop: '1px solid #cbd5e1' }}>
          <div>
            <div style={{ marginBottom: '50px', fontSize: '0.85rem', color: '#64748b' }}>For & On Behalf of NGO Trustee:</div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{ucDetails.signatoryName}</div>
            <div style={{ fontSize: '0.82rem', color: '#475569' }}>{ucDetails.signatoryDesignation}</div>
            <div style={{ fontSize: '0.82rem', color: '#475569' }}>{ngoProfile.name}</div>
            <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '4px' }}>Date: {formatDate(ucDetails.signingDate)}</div>
          </div>

          <div style={{ borderLeft: '1px solid #cbd5e1', paddingLeft: '30px' }}>
            <div style={{ marginBottom: '50px', fontSize: '0.85rem', color: '#64748b' }}>Statutory Auditor / CA Verification:</div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{ucDetails.caName}</div>
            <div style={{ fontSize: '0.82rem', color: '#475569' }}>Chartered Accountants</div>
            <div style={{ fontSize: '0.82rem', color: '#475569' }}>Reg No: {ucDetails.caFirmRegNo} | Mem No: {ucDetails.caMembershipNo}</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#2563eb', marginTop: '6px' }}>UDIN: {ucDetails.udin}</div>
          </div>
        </div>
      </div>
    </div>
  );
};
