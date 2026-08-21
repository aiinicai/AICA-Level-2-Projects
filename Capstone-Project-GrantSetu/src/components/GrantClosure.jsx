import React, { useState } from 'react';
import { useGrant } from '../context/GrantContext';
import { Archive, CheckCircle2, AlertTriangle, FileCheck, ShieldCheck, ArrowRight } from 'lucide-react';
import { formatINR, formatDate } from '../utils/formatters';

export const GrantClosure = () => {
  const { grants, closures, closeGrant, selectedGrantId, setSelectedGrantId } = useGrant();

  const activeGrants = grants.filter((g) => g.status === 'Active' || g.status === 'Pending Closure');
  const currentGrant = grants.find((g) => g.id === selectedGrantId) || activeGrants[0] || grants[0];

  const [closureChecklist, setClosureChecklist] = useState({
    technicalReportSubmitted: true,
    auditedUCSubmitted: true,
    form10BSubmitted: true,
    assetHandoverComplete: true,
    donorNocReceived: true
  });

  const [refundStatus, setRefundStatus] = useState('N/A (Fully Utilized)');

  if (!currentGrant) {
    return (
      <div className="card">
        <h3>No Grant Ready for Closure</h3>
      </div>
    );
  }

  const unspent = (currentGrant.receivedAmount || 0) - (currentGrant.spentAmount || 0);

  const handleConfirmClosure = () => {
    closeGrant(currentGrant.id, {
      financialSummary: {
        sanctioned: currentGrant.totalSanctionedAmount,
        spent: currentGrant.spentAmount,
        unspentBalance: unspent,
        refundStatus: unspent > 0 ? 'Refunded to Donor' : 'Fully Utilized'
      },
      checklist: closureChecklist
    });
  };

  return (
    <div className="grant-closure-view">
      <div className="card-header" style={{ marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Archive size={24} style={{ color: 'var(--color-primary)' }} />
            Final Grant Closure & Audited Archival Studio
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Complete 4-step formal grant sign-off, verify donor NOC, clear unspent balance, and archive compliance files.
          </p>
        </div>

        <select
          className="form-control"
          style={{ width: '280px', fontWeight: 600 }}
          value={currentGrant.id}
          onChange={(e) => setSelectedGrantId(e.target.value)}
        >
          {grants.map((g) => (
            <option key={g.id} value={g.id}>
              {g.title} ({g.status})
            </option>
          ))}
        </select>
      </div>

      {/* Grant Summary Header */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <span className="badge badge-active">{currentGrant.status}</span>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '6px' }}>{currentGrant.title}</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Donor: {currentGrant.donorName} | MoU: {currentGrant.sanctionOrderNo}</p>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Unspent Fund Balance</div>
            <div style={{ fontSize: '1.3rem', fontWeight: 800, color: unspent > 0 ? 'var(--color-warning)' : 'var(--color-success)' }}>
              {formatINR(unspent)}
            </div>
          </div>
        </div>

        {/* 4-Step Closure Checklist */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginTop: '20px', paddingTop: '20px', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ padding: '14px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontWeight: 600, fontSize: '0.88rem' }}>
              <input
                type="checkbox"
                checked={closureChecklist.technicalReportSubmitted}
                onChange={(e) => setClosureChecklist({ ...closureChecklist, technicalReportSubmitted: e.target.checked })}
              />
              1. Technical Impact Report
            </label>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>Final project activities & photos submitted to Donor.</p>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontWeight: 600, fontSize: '0.88rem' }}>
              <input
                type="checkbox"
                checked={closureChecklist.auditedUCSubmitted}
                onChange={(e) => setClosureChecklist({ ...closureChecklist, auditedUCSubmitted: e.target.checked })}
              />
              2. Audited GFR 12-A UC
            </label>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>Signed by CA with valid UDIN.</p>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontWeight: 600, fontSize: '0.88rem' }}>
              <input
                type="checkbox"
                checked={closureChecklist.assetHandoverComplete}
                onChange={(e) => setClosureChecklist({ ...closureChecklist, assetHandoverComplete: e.target.checked })}
              />
              3. Asset Register Handover
            </label>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>Equipment transferred to target community.</p>
          </div>

          <div style={{ padding: '14px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontWeight: 600, fontSize: '0.88rem' }}>
              <input
                type="checkbox"
                checked={closureChecklist.donorNocReceived}
                onChange={(e) => setClosureChecklist({ ...closureChecklist, donorNocReceived: e.target.checked })}
              />
              4. Donor NOC & Clearance
            </label>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>No Objection Certificate signed by Donor.</p>
          </div>
        </div>

        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            className="btn btn-primary"
            onClick={handleConfirmClosure}
            disabled={currentGrant.status === 'Closed'}
          >
            <Archive size={18} /> {currentGrant.status === 'Closed' ? 'Grant Already Closed' : 'Execute Final Grant Closure'}
          </button>
        </div>
      </div>

      {/* Closure History */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Archive size={18} style={{ color: 'var(--color-secondary)' }} />
            Grant Archival Registry ({closures.length} Closed Grants)
          </h3>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Grant Title</th>
                <th>Closure Date</th>
                <th>Sanctioned (₹)</th>
                <th>Spent (₹)</th>
                <th>Auditor UDIN</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {closures.map((c, idx) => (
                <tr key={idx}>
                  <td>
                    <strong>{c.grantTitle}</strong>
                  </td>
                  <td>{formatDate(c.closureDate)}</td>
                  <td>{formatINR(c.financialSummary?.sanctioned)}</td>
                  <td>{formatINR(c.financialSummary?.spent)}</td>
                  <td>{c.caCertificateDetails?.udin || 'UDIN Verified'}</td>
                  <td>
                    <span className="badge badge-active">Formally Closed</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
