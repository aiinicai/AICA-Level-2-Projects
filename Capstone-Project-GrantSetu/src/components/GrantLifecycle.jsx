import React, { useState } from 'react';
import { useGrant } from '../context/GrantContext';
import {
  Briefcase,
  Layers,
  Calendar,
  IndianRupee,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Archive,
  TrendingUp,
  Sliders
} from 'lucide-react';
import { formatINR, formatDate } from '../utils/formatters';

export const GrantLifecycle = () => {
  const {
    grants,
    selectedGrantId,
    setSelectedGrantId,
    updateGrant,
    setActiveTab
  } = useGrant();

  const activeGrants = grants.filter((g) => g.status === 'Active' || g.status === 'Pending Closure');
  const currentGrant = grants.find((g) => g.id === selectedGrantId) || activeGrants[0];

  const handleKpiChange = (idx, newAchieved) => {
    if (!currentGrant) return;
    const updatedKpis = [...(currentGrant.kpis || [])];
    updatedKpis[idx].achieved = Number(newAchieved);
    updateGrant({
      ...currentGrant,
      kpis: updatedKpis
    });
  };

  const handleTrancheStatusToggle = (trancheId) => {
    if (!currentGrant) return;
    const updatedTranches = (currentGrant.tranches || []).map((t) => {
      if (t.id === trancheId) {
        const nextStatus = t.status === 'Received' ? 'Scheduled' : 'Received';
        return {
          ...t,
          status: nextStatus,
          receivedDate: nextStatus === 'Received' ? new Date().toISOString().slice(0, 10) : null
        };
      }
      return t;
    });

    const newReceivedSum = updatedTranches
      .filter((t) => t.status === 'Received')
      .reduce((sum, t) => sum + (t.amount || 0), 0);

    updateGrant({
      ...currentGrant,
      tranches: updatedTranches,
      receivedAmount: newReceivedSum
    });
  };

  if (!currentGrant) {
    return (
      <div className="card">
        <h3>No Active Grants Found</h3>
        <p>Go to Proposal Studio to draft and sanction your first grant!</p>
      </div>
    );
  }

  const utilPercent = Math.min(100, Math.round(((currentGrant.spentAmount || 0) / (currentGrant.totalSanctionedAmount || 1)) * 100));

  return (
    <div className="grant-lifecycle-view">
      <div className="card-header" style={{ marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Briefcase size={24} style={{ color: 'var(--color-primary)' }} />
            Active Grant Execution & Tranche Monitor
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Monitor multi-disbursement schedules, budget utilization, deliverable KPIs, and Utilization Certificates (UCs).
          </p>
        </div>

        {/* Grant Selector Dropdown */}
        <select
          className="form-control"
          style={{ width: '320px', fontWeight: 600 }}
          value={currentGrant.id}
          onChange={(e) => setSelectedGrantId(e.target.value)}
        >
          {grants.map((g) => (
            <option key={g.id} value={g.id}>
              {g.title} ({g.id})
            </option>
          ))}
        </select>
      </div>

      {/* Grant Overview Card */}
      <div className="card" style={{ background: 'linear-gradient(135deg, var(--bg-card) 0%, rgba(15, 23, 42, 0.9) 100%)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <span className={`badge ${currentGrant.fundingType === 'FCRA Foreign' ? 'badge-fcra' : 'badge-domestic'}`}>
                {currentGrant.fundingType}
              </span>
              <span className="badge badge-active">{currentGrant.status}</span>
              <span className="badge badge-draft">MoU: {currentGrant.sanctionOrderNo}</span>
            </div>
            <h3 style={{ fontSize: '1.3rem', fontWeight: 800 }}>{currentGrant.title}</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
              Donor: <strong>{currentGrant.donorName}</strong> | Period: {formatDate(currentGrant.startDate)} to {formatDate(currentGrant.endDate)}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setSelectedGrantId(currentGrant.id);
                setActiveTab('uc');
              }}
            >
              <FileCheck size={15} /> Generate UC
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => {
                setSelectedGrantId(currentGrant.id);
                setActiveTab('closures');
              }}
            >
              <Archive size={15} /> Proceed to Closure
            </button>
          </div>
        </div>

        {/* Financial Metrics Strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginTop: '24px', paddingTop: '20px', borderTop: '1px solid var(--border-color)' }}>
          <div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Sanctioned</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)' }}>{formatINR(currentGrant.totalSanctionedAmount)}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Tranches Received</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--color-success)' }}>{formatINR(currentGrant.receivedAmount)}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Spent Amount</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--color-primary)' }}>{formatINR(currentGrant.spentAmount)}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Utilization Progress</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <div className="progress-bar-bg" style={{ width: '100px' }}>
                <div className="progress-bar-fill" style={{ width: `${utilPercent}%` }}></div>
              </div>
              <strong style={{ fontSize: '0.9rem' }}>{utilPercent}%</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Tranche Schedule & KPI Targets */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Tranche Disbursement Schedule */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Layers size={18} style={{ color: 'var(--color-secondary)' }} />
              Tranche Disbursement Schedule
            </h3>
          </div>

          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Tranche</th>
                  <th>Amount (₹)</th>
                  <th>Status</th>
                  <th>UC Requirement</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {(currentGrant.tranches || []).map((tranche) => (
                  <tr key={tranche.id}>
                    <td>
                      <strong>Tranche {tranche.trancheNo}</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Due: {formatDate(tranche.expectedDate)}</div>
                    </td>
                    <td>
                      <strong>{formatINR(tranche.amount)}</strong>
                    </td>
                    <td>
                      <span className={`badge ${tranche.status === 'Received' ? 'badge-active' : 'badge-pending'}`}>
                        {tranche.status}
                      </span>
                    </td>
                    <td>
                      {tranche.ucRequired ? (
                        <span style={{ fontSize: '0.78rem', color: tranche.ucSubmitted ? 'var(--color-success)' : 'var(--color-warning)' }}>
                          {tranche.ucSubmitted ? 'UC Verified' : 'UC Mandatory'}
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-subtle)' }}>Advance</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleTrancheStatusToggle(tranche.id)}
                      >
                        {tranche.status === 'Received' ? 'Mark Scheduled' : 'Mark Received'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Deliverable KPI Target Tracker */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <TrendingUp size={18} style={{ color: 'var(--color-success)' }} />
              Deliverable KPI Progress
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {(currentGrant.kpis || []).map((kpi, idx) => {
              const kpiPercent = Math.min(100, Math.round(((kpi.achieved || 0) / (kpi.target || 1)) * 100));
              return (
                <div key={idx} style={{ padding: '14px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>{kpi.name}</span>
                    <span style={{ fontSize: '0.82rem', color: 'var(--color-primary)' }}>
                      {kpi.achieved} / {kpi.target} {kpi.unit} ({kpiPercent}%)
                    </span>
                  </div>

                  <div className="progress-bar-bg" style={{ marginBottom: '10px' }}>
                    <div className="progress-bar-fill" style={{ width: `${kpiPercent}%` }}></div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Update Achieved:</label>
                    <input
                      type="number"
                      className="form-control"
                      style={{ width: '100px', padding: '4px 8px', fontSize: '0.8rem' }}
                      value={kpi.achieved}
                      onChange={(e) => handleKpiChange(idx, e.target.value)}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
