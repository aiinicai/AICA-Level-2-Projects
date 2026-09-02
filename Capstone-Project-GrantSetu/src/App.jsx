import React from 'react';
import { GrantProvider, useGrant } from './context/GrantContext';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { ProfileVault } from './components/ProfileVault';
import { ProposalBuilder } from './components/ProposalBuilder';
import { GrantLifecycle } from './components/GrantLifecycle';
import { SubGranting } from './components/SubGranting';
import { ExpenseTracker } from './components/ExpenseTracker';
import { UCGenerator } from './components/UCGenerator';
import { DocumentVault } from './components/DocumentVault';
import { GrantClosure } from './components/GrantClosure';
import { UserGuide } from './components/UserGuide';
import { CheckCircle2, AlertCircle, Info } from 'lucide-react';

const MainAppContent = () => {
  const { activeTab, notification } = useGrant();

  const renderActiveView = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'profile':
        return <ProfileVault />;
      case 'proposals':
        return <ProposalBuilder />;
      case 'grants':
        return <GrantLifecycle />;
      case 'subgranting':
        return <SubGranting />;
      case 'expenses':
        return <ExpenseTracker />;
      case 'uc':
        return <UCGenerator />;
      case 'vault':
        return <DocumentVault />;
      case 'closures':
        return <GrantClosure />;
      case 'guide':
        return <UserGuide />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-wrapper">
        <Navbar />
        <main className="content-body">
          {renderActiveView()}
        </main>
      </div>

      {/* Toast Notification Container */}
      {notification && (
        <div className="toast-container">
          <div className="toast">
            {notification.type === 'error' ? (
              <AlertCircle size={20} style={{ color: 'var(--color-danger)' }} />
            ) : notification.type === 'info' ? (
              <Info size={20} style={{ color: 'var(--color-info)' }} />
            ) : (
              <CheckCircle2 size={20} style={{ color: 'var(--color-success)' }} />
            )}
            <span>{notification.text}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default function App() {
  return (
    <GrantProvider>
      <MainAppContent />
    </GrantProvider>
  );
}
