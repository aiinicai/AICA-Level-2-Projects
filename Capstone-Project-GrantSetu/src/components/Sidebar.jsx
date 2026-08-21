import React from 'react';
import { useGrant } from '../context/GrantContext';
import {
  LayoutDashboard,
  Building2,
  FileText,
  Briefcase,
  Network,
  Receipt,
  FileCheck,
  Folder,
  Archive,
  BookOpen,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import { isExpiringSoon } from '../utils/formatters';

export const Sidebar = () => {
  const {
    activeTab,
    setActiveTab,
    ngoProfile,
    grants,
    proposals,
    subGrants
  } = useGrant();

  const activeGrantsCount = grants.filter((g) => g.status === 'Active').length;
  const draftProposalsCount = proposals.filter((p) => p.status === 'Draft' || p.status === 'Under Internal Review').length;
  const activeSubGrantsCount = subGrants.length;

  const pendingUcsCount = grants.reduce((count, grant) => {
    const pendingInGrant = (grant.tranches || []).filter((t) => t.ucRequired && !t.ucSubmitted).length;
    return count + pendingInGrant;
  }, 0);

  const is12AExpiring = isExpiringSoon(ngoProfile.twelveAValidTill, 120);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'profile', label: 'NGO Profile & Vault', icon: Building2, alert: is12AExpiring },
    { id: 'proposals', label: 'Proposal Studio', icon: FileText, badge: draftProposalsCount },
    { id: 'grants', label: 'Active Grants', icon: Briefcase, badge: activeGrantsCount },
    { id: 'subgranting', label: 'Non-FCRA Sub-Granting', icon: Network, badge: activeSubGrantsCount },
    { id: 'expenses', label: 'Expenses & Ledger', icon: Receipt },
    { id: 'uc', label: 'UC Generator (GFR-12A)', icon: FileCheck, badge: pendingUcsCount, badgeClass: 'warning' },
    { id: 'vault', label: 'Central Document Vault', icon: Folder },
    { id: 'closures', label: 'Grant Closure', icon: Archive },
    { id: 'guide', label: 'User Guide & SOPs', icon: BookOpen }
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo-icon">
          <ShieldCheck size={24} />
        </div>
        <div className="sidebar-title">
          <h1>GrantSetu</h1>
          <span>NGO Desktop ERP</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <div
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.alert && <AlertTriangle size={15} style={{ color: 'var(--color-warning)', marginLeft: 'auto' }} />}
              {!item.alert && item.badge > 0 && (
                <span className={`nav-badge ${item.badgeClass || ''}`}>{item.badge}</span>
              )}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="ngo-mini-card">
          <div className="ngo-mini-name">{ngoProfile.name || 'Local NGO'}</div>
          <div className="ngo-mini-darpan">
            <span>Darpan:</span>
            <strong>{ngoProfile.darpanId || 'Not Set'}</strong>
          </div>
        </div>
      </div>
    </aside>
  );
};
