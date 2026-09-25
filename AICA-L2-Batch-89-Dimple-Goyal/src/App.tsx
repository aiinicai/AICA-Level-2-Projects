import React, { useState, useEffect } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Navbar } from './components/layout/Navbar';
import { Sidebar, ActiveTab } from './components/layout/Sidebar';
import { GlobalSearchModal } from './components/common/GlobalSearchModal';
import { NotificationsDrawer } from './components/common/NotificationsDrawer';

// Views
import { DashboardView } from './components/dashboard/DashboardView';
import { CustomerMasterView } from './components/customers/CustomerMasterView';
import { InvoiceListView } from './components/invoices/InvoiceListView';
import { BankStatementView } from './components/payments/BankStatementView';
import { ReconciliationCentreView } from './components/reconciliation/ReconciliationCentreView';
import { ReceivablesAgeingView } from './components/ageing/ReceivablesAgeingView';
import { TDSReconciliationView } from './components/tds/TDSReconciliationView';
import { GSTReconciliationView } from './components/gst/GSTReconciliationView';
import { ExceptionsCentreView } from './components/exceptions/ExceptionsCentreView';
import { ReportsView } from './components/reports/ReportsView';
import { DocumentsView } from './components/documents/DocumentsView';
import { SettingsView } from './components/settings/SettingsView';
import { AccountingTestSuiteView } from './components/tests/AccountingTestSuiteView';
import { AccessRestrictedCard } from './components/common/AccessRestrictedCard';
import { hasTabAccess, ROLE_DEFINITIONS } from './utils/rbac';
import { LoginView } from './components/auth/LoginView';

const MainAppContent: React.FC = () => {
  const { exceptions, invoices, bankTransactions, currentUser } = useApp();
  const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard');
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsSearchModalOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const unreadNotificationsCount =
    exceptions.filter(e => e.status === 'Open').length +
    invoices.filter(i => i.status === 'Overdue').length +
    bankTransactions.filter(t => t.isCredit && t.unallocatedAmount > 0).length;

  const handleNavigate = (tab: ActiveTab) => {
    setActiveTab(tab);
    setIsMobileSidebarOpen(false);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-100/70 text-slate-900 font-sans">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex md:flex-col md:w-64 h-full shrink-0 z-20">
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />
      </aside>

      {/* Mobile Sidebar Backdrop & Drawer */}
      {isMobileSidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
            onClick={() => setIsMobileSidebarOpen(false)}
          />
          <div className="relative flex-1 flex flex-col max-w-xs w-full bg-white h-full z-10 shadow-2xl">
            <Sidebar
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              onCloseMobile={() => setIsMobileSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Navbar */}
        <Navbar
          onOpenSearch={() => setIsSearchModalOpen(true)}
          onOpenNotifications={() => setIsNotificationsOpen(true)}
          onToggleSidebar={() => setIsMobileSidebarOpen(prev => !prev)}
          unreadNotificationsCount={unreadNotificationsCount}
        />

        {/* Scrollable View Container */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 space-y-6">
          {!hasTabAccess(currentUser.role, activeTab) ? (
            <AccessRestrictedCard
              attemptedTab={activeTab}
              onNavigateHome={() => setActiveTab(ROLE_DEFINITIONS[currentUser.role]?.allowedTabs[0] || 'dashboard')}
            />
          ) : (
            <>
              {activeTab === 'dashboard' && (
                <DashboardView
                  onNavigate={handleNavigate}
                />
              )}
              {activeTab === 'customers' && <CustomerMasterView />}
              {activeTab === 'invoices' && <InvoiceListView />}
              {activeTab === 'payments' && <BankStatementView />}
              {activeTab === 'reconciliation' && <ReconciliationCentreView />}
              {activeTab === 'ageing' && <ReceivablesAgeingView />}
              {activeTab === 'tds' && <TDSReconciliationView />}
              {activeTab === 'gst' && <GSTReconciliationView />}
              {activeTab === 'exceptions' && <ExceptionsCentreView />}
              {activeTab === 'reports' && <ReportsView />}
              {activeTab === 'documents' && <DocumentsView />}
              {activeTab === 'settings' && <SettingsView />}
              {activeTab === 'tests' && <AccountingTestSuiteView />}
            </>
          )}
        </main>

        {/* Global Modals */}
        <GlobalSearchModal
          isOpen={isSearchModalOpen}
          onClose={() => setIsSearchModalOpen(false)}
          onNavigate={(tab) => {
            setActiveTab(tab);
            setIsSearchModalOpen(false);
          }}
        />

        <NotificationsDrawer
          isOpen={isNotificationsOpen}
          onClose={() => setIsNotificationsOpen(false)}
          onNavigate={(tab) => {
            setActiveTab(tab);
            setIsNotificationsOpen(false);
          }}
        />
      </div>
    </div>
  );
};

const AppRoot: React.FC = () => {
  const { isAuthenticated } = useApp();

  if (!isAuthenticated) {
    return <LoginView />;
  }

  return <MainAppContent />;
};

export default function App() {
  return (
    <AppProvider>
      <AppRoot />
    </AppProvider>
  );
}
