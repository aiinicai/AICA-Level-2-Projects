import React from 'react';
import { useGrant } from '../context/GrantContext';
import {
  IndianRupee,
  FileCheck,
  Building2,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  PlusCircle,
  Receipt,
  Network,
  Folder,
  ShieldCheck
} from 'lucide-react';
import { formatINR, formatINRShorthand, formatDate, isExpiringSoon } from '../utils/formatters';

export const Dashboard = () => {
  const {
    ngoProfile,
    grants,
    proposals,
    expenses,
    subGrants,
    setActiveTab,
    setSelectedGrantId
  } = useGrant();

  const activeGrants = grants.filter((g) => g.status === 'Active');
  const totalActiveSanctioned = activeGrants.reduce((sum, g) => sum + (g.totalSanctionedAmount || 0), 0);
  const totalFundsReceived = activeGrants.reduce((sum, g) => sum + (g.receivedAmount || 0), 0);
  const totalSpent = activeGrants.reduce((sum, g) => sum + (g.spentAmount || 0), 0);
  const unspentFunds = totalFundsReceived - totalSpent;

  const pipelineValue = proposals
    .filter((p) => p.status === 'Draft' || p.status === 'Under Internal Review' || p.status === 'Submitted')
    .reduce((sum, p) => sum + (p.totalBudget || 0), 0);

  const fcraSanctioned = grants
    .filter((g) => g.fundingType === 'FCRA Foreign')
    .reduce((sum, g) => sum + (g.totalSanctionedAmount || 0), 0);

  const domesticSanctioned = grants
    .filter((g) => g.fundingType !== 'FCRA Foreign')
    .reduce((sum, g) => sum + (g.totalSanctionedAmount || 0), 0);

  const totalSubGranted = subGrants.reduce((sum, sg) => sum + (sg.sanctionedAmount || 0), 0);

  const is12AAlert = isExpiringSoon(ngoProfile.twelveAValidTill, 120);

  return (
    <div className="dashboard-view">
      {/* Welcome Banner */}
      <div className="card" style={{ background: 'linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(99, 102, 241, 0.1) 100%)', borderColor: 'rgba(249, 115, 22, 0.3)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '6px' }}>
              Welcome back, {ngoProfile.shortName || ngoProfile.name}!
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Local NGO Grant Management Portal with FCRA & Non-FCRA Sub-Granting, Document Vault & GFR 12-A UCs
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-primary btn-sm" onClick={() => setActiveTab('proposals')}>
              <PlusCircle size={15} /> New Proposal
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('subgranting')}>
              <Network size={15} /> Sub-Granting
            </button>
          </div>
        </div>
      </div>

      {/* Compliance Expiry Banners */}
      {is12AAlert && (
        <div className="alert-banner">
          <AlertTriangle style={{ color: 'var(--color-warning)' }} size={24} />
          <div style={{ flex: 1 }}>
            <h4 style={{ fontWeight: 700, color: 'var(--color-warning)' }}>
              12A / 80G Tax Exemption Renewal Reminder
            </h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Your 12A Certificate ({ngoProfile.twelveARef}) is valid till {formatDate(ngoProfile.twelveAValidTill)}. Submit Form 10A re-validation on Income Tax Portal within 90 days.
            </p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('profile')}>
            Check Vault
          </button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon saffron">
            <IndianRupee size={24} />
          </div>
          <div>
            <div className="stat-label">Active Grant Sanctioned</div>
            <div className="stat-value">{formatINRShorthand(totalActiveSanctioned)}</div>
            <div className="stat-sub">{activeGrants.length} Active Donor Grants</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon indigo">
            <TrendingUp size={24} />
          </div>
          <div>
            <div className="stat-label">Pipeline Proposals</div>
            <div className="stat-value">{formatINRShorthand(pipelineValue)}</div>
            <div className="stat-sub">{proposals.length} Proposals in Studio</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon emerald">
            <Network size={24} />
          </div>
          <div>
            <div className="stat-label">Non-FCRA Sub-Granted</div>
            <div className="stat-value">{formatINRShorthand(totalSubGranted)}</div>
            <div className="stat-sub">{subGrants.length} Grassroots NGO Partners</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon amber">
            <Building2 size={24} />
          </div>
          <div>
            <div className="stat-label">Unspent Balance</div>
            <div className="stat-value">{formatINRShorthand(unspentFunds)}</div>
            <div className="stat-sub">Available in Bank Accounts</div>
          </div>
        </div>
      </div>

      {/* Main Row: Active Grants & FCRA Split */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        {/* Active Grants Overview */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Building2 size={18} style={{ color: 'var(--color-primary)' }} />
              Active Grants & Budget Utilization
            </h3>
            <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('grants')}>
              View All Grants <ArrowRight size={14} />
            </button>
          </div>

          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Grant Title</th>
                  <th>Donor & Type</th>
                  <th>Sanctioned (₹)</th>
                  <th>Utilization</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeGrants.map((grant) => {
                  const utilPercent = Math.min(100, Math.round(((grant.spentAmount || 0) / (grant.totalSanctionedAmount || 1)) * 100));
                  return (
                    <tr key={grant.id}>
                      <td>
                        <strong>{grant.title}</strong>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          ID: {grant.id} | MoU: {grant.sanctionOrderNo}
                        </div>
                      </td>
                      <td>
                        <div>{grant.donorName}</div>
                        <span className={`badge ${grant.fundingType === 'FCRA Foreign' ? 'badge-fcra' : 'badge-domestic'}`}>
                          {grant.fundingType}
                        </span>
                      </td>
                      <td>
                        <strong>{formatINR(grant.totalSanctionedAmount)}</strong>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div className="progress-bar-bg" style={{ width: '80px' }}>
                            <div className="progress-bar-fill" style={{ width: `${utilPercent}%` }}></div>
                          </div>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{utilPercent}%</span>
                        </div>
                      </td>
                      <td>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => {
                            setSelectedGrantId(grant.id);
                            setActiveTab('grants');
                          }}
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Account & Regulatory Segregation */}
        <div>
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <ShieldCheck size={18} style={{ color: 'var(--color-secondary)' }} />
                Fund Breakdown
              </h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ padding: '14px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-secondary)' }}>FCRA Foreign Grants</span>
                  <strong>{formatINR(fcraSanctioned)}</strong>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Bank: SBI New Delhi Main Branch (Acc: {ngoProfile.fcraAccountNo || '40019283741'})
                </div>
              </div>

              <div style={{ padding: '14px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-info)' }}>Domestic CSR & Govt Grants</span>
                  <strong>{formatINR(domesticSanctioned)}</strong>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Bank: {ngoProfile.domesticBankName} (Acc: {ngoProfile.domesticAccountNo})
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Folder size={18} style={{ color: 'var(--color-primary)' }} />
                Document Vault
              </h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('vault')}>
                Open Vault
              </button>
            </div>

            <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              All uploaded proposal pitch decks, vendor invoices, sub-grant MoUs, and GFR 12-A UCs are archived and downloadable.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
