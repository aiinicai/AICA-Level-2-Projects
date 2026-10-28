import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Navigator } from './components/Navigator';
import { HomePage } from './modules/home/HomePage';
import { SignInPage } from './modules/auth/SignInPage';
import { JournalsPage } from './modules/generalAccounting/JournalsPage';
import { PeriodClosePage } from './modules/generalAccounting/PeriodClosePage';
import { AccountInquiryPage } from './modules/generalAccounting/AccountInquiryPage';
import { GeneralAccountingDashboard } from './modules/generalAccounting/GeneralAccountingDashboard';
import { InvoicesPage } from './modules/payables/InvoicesPage';
import { SuppliersPage } from './modules/payables/SuppliersPage';
import { BillingPage } from './modules/receivables/BillingPage';
import { CustomersPage } from './modules/receivables/CustomersPage';
import { AssetsPage } from './modules/fixedAssets/AssetsPage';
import { DepreciationPage } from './modules/fixedAssets/DepreciationPage';
import { PettyCashPage } from './modules/cashManagement/PettyCashPage';
import { BankReconciliationPage } from './modules/cashManagement/BankReconciliationPage';
import { IntercompanyPage } from './modules/intercompany/IntercompanyPage';
import { ReceivingPage } from './modules/supplyChain/ReceivingPage';
import { InventoryPage } from './modules/supplyChain/InventoryPage';
import { PurchaseOrdersPage } from './modules/procurement/PurchaseOrdersPage';
import { CreatePurchaseOrderPage } from './modules/procurement/CreatePurchaseOrderPage';
import { RequisitionsPage } from './modules/procurement/RequisitionsPage';
import { CreateRequisitionPage } from './modules/procurement/CreateRequisitionPage';
import { ProcurementDashboard } from './modules/procurement/ProcurementDashboard';
import { ChartOfAccountsPage } from './modules/generalAccounting/ChartOfAccountsPage';
import { AccessRolesPage } from './modules/tools/AccessRolesPage';
import { TrialBalancePage } from './modules/reports/TrialBalancePage';
import { IFRSStatementsPage } from './modules/reports/IFRSStatementsPage';
import { GeneralLedgerReportPage } from './modules/reports/GeneralLedgerReportPage';
import { IntegrityCheckPage } from './modules/tools/IntegrityCheckPage';
import { AdministrationPage } from './modules/tools/AdministrationPage';
import { AuditTrailPage } from './modules/tools/AuditTrailPage';
import { DocumentDetailModal } from './components/DocumentDetailModal';
import { initStorage, getDb } from './core/storage';
import { generateSeedData } from './data/seedEngine';
import { getActiveUser } from './core/auth';

export default function App() {
  const [currentRoute, setCurrentRoute] = useState(window.location.hash || '#/');
  const [isNavigatorOpen, setIsNavigatorOpen] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [currentUser, setCurrentUser] = useState(getActiveUser());
  const [activeModalDocNumber, setActiveModalDocNumber] = useState<string | null>(null);

  useEffect(() => {
    // Initialize storage and seed if empty
    initStorage().then((db) => {
      if (!db.glJournals || db.glJournals.length === 0) {
        generateSeedData();
      }
      setIsReady(true);
    });

    const handleHashChange = () => {
      setCurrentRoute(window.location.hash || '#/');
      window.scrollTo(0, 0);
    };

    const handleUserChange = () => {
      setCurrentUser(getActiveUser());
    };

    const handleOpenDoc = (e: any) => {
      if (e.detail?.number) {
        setActiveModalDocNumber(e.detail.number);
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    window.addEventListener('medicore-user-changed', handleUserChange);
    window.addEventListener('medicore-open-doc', handleOpenDoc);

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      window.removeEventListener('medicore-user-changed', handleUserChange);
      window.removeEventListener('medicore-open-doc', handleOpenDoc);
    };
  }, []);

  const navigateTo = (route: string) => {
    window.location.hash = route;
    setCurrentRoute(route);
  };

  if (!isReady) {
    return (
      <div className="min-h-screen bg-[#3F1D5C] flex flex-col items-center justify-center text-white">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#844db3] to-[#5B2C83] border border-plum-300 flex items-center justify-center animate-bounce mb-4 shadow-xl">
          <svg viewBox="0 0 24 24" className="w-7 h-7 text-amber-300 fill-current">
            <polygon points="12,2 21,7.5 21,16.5 12,22 3,16.5 3,7.5" fill="none" stroke="currentColor" strokeWidth="2" />
            <path d="M12 7v10M7 12h10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        </div>
        <h2 className="text-xl font-bold">MediCore Connect</h2>
        <p className="text-plum-200 text-xs mt-1 animate-pulse">Initializing Financials & Supply Chain Ledger...</p>
      </div>
    );
  }

  // If on login route or user not signed in
  if (currentRoute === '#/login' || !currentUser) {
    return <SignInPage onSuccess={() => navigateTo('#/')} />;
  }

  // Route router logic
  const renderCurrentPage = () => {
    const route = currentRoute.split('?')[0];
    const params = new URLSearchParams(currentRoute.split('?')[1] || '');
    const action = params.get('action') || undefined;

    switch (route) {
      case '#/':
        return <HomePage onNavigate={navigateTo} />;

      // General Accounting
      case '#/general-accounting/journals':
        return <JournalsPage onNavigate={navigateTo} />;
      case '#/general-accounting/period-close':
        return <PeriodClosePage onNavigate={navigateTo} />;
      case '#/general-accounting/account-inquiry':
        return <AccountInquiryPage onNavigate={navigateTo} />;
      case '#/general-accounting/chart-of-accounts':
        return <ChartOfAccountsPage onNavigate={navigateTo} initialAction={action} />;
      case '#/general-accounting/dashboard':
        return <GeneralAccountingDashboard onNavigate={navigateTo} />;

      // Payables
      case '#/payables/invoices':
        return <InvoicesPage onNavigate={navigateTo} initialAction={action} />;
      case '#/payables/payments':
        return <InvoicesPage onNavigate={navigateTo} initialAction={action} />;
      case '#/payables/suppliers':
        return <SuppliersPage onNavigate={navigateTo} />;
      case '#/payables/dashboard':
        return <GeneralAccountingDashboard onNavigate={navigateTo} />;

      // Receivables
      case '#/receivables/billing':
      case '#/receivables/transactions':
      case '#/receivables/receipts':
        return <BillingPage onNavigate={navigateTo} initialAction={action} />;
      case '#/receivables/customers':
        return <CustomersPage onNavigate={navigateTo} />;

      // Fixed Assets
      case '#/fixed-assets/assets':
        return <AssetsPage onNavigate={navigateTo} initialTab={params.get('tab') as any} />;
      case '#/fixed-assets/depreciation':
        return <DepreciationPage onNavigate={navigateTo} />;

      // Cash Management
      case '#/cash/petty-cash':
      case '#/cash/main-cash':
        return <PettyCashPage onNavigate={navigateTo} initialAction={action} />;
      case '#/cash/bank-reconciliation':
        return <BankReconciliationPage onNavigate={navigateTo} />;

      // Intercompany
      case '#/intercompany/transactions':
      case '#/intercompany/reconciliation':
      case '#/intercompany/multitier':
        return <IntercompanyPage onNavigate={navigateTo} initialAction={action} />;

      // Supply Chain & Receiving
      case '#/supply-chain/receiving':
        return <ReceivingPage onNavigate={navigateTo} initialAction={action} initialPoNumber={params.get('poNumber') || undefined} />;
      case '#/supply-chain/inventory':
      case '#/supply-chain/items':
      case '#/supply-chain/transfers':
        return <InventoryPage onNavigate={navigateTo} />;

      // Procurement
      case '#/procurement/dashboard':
        return <ProcurementDashboard onNavigate={navigateTo} />;
      case '#/procurement/requisitions':
        if (action === 'create') {
          return <CreateRequisitionPage onNavigate={navigateTo} editRequisitionId={params.get('id') || undefined} />;
        }
        return <RequisitionsPage onNavigate={navigateTo} />;
      case '#/procurement/requisitions/create':
        return <CreateRequisitionPage onNavigate={navigateTo} editRequisitionId={params.get('id') || undefined} />;
      case '#/procurement/orders':
        if (action === 'create') {
          return <CreatePurchaseOrderPage onNavigate={navigateTo} sourceReqNumber={params.get('sourceReq') || undefined} />;
        }
        return <PurchaseOrdersPage onNavigate={navigateTo} />;
      case '#/procurement/orders/create':
        return <CreatePurchaseOrderPage onNavigate={navigateTo} sourceReqNumber={params.get('sourceReq') || undefined} />;

      // Reports
      case '#/reports/trial-balance':
        return <TrialBalancePage onNavigate={navigateTo} />;
      case '#/reports/ifrs':
        return <IFRSStatementsPage onNavigate={navigateTo} />;
      case '#/reports/general-ledger':
      case '#/reports/payables-aging':
      case '#/reports/receivables-aging':
      case '#/reports/fixed-assets-register':
      case '#/reports/petty-cash-register':
      case '#/reports/reconciliations':
        return <GeneralLedgerReportPage onNavigate={navigateTo} />;

      // Tools & Administration
      case '#/tools/integrity':
        return <IntegrityCheckPage onNavigate={navigateTo} />;
      case '#/tools/administration':
        return <AdministrationPage onNavigate={navigateTo} initialTab={params.get('tab') || undefined} />;
      case '#/tools/audit-trail':
        return <AuditTrailPage onNavigate={navigateTo} />;
      case '#/tools/access-roles':
      case '#/tools/roles':
        return <AccessRolesPage onNavigate={navigateTo} />;

      default:
        return <HomePage onNavigate={navigateTo} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 text-gray-900 font-sans">
      <Header
        onToggleNavigator={() => setIsNavigatorOpen(true)}
        onNavigate={navigateTo}
      />

      <Navigator
        isOpen={isNavigatorOpen}
        onClose={() => setIsNavigatorOpen(false)}
        onNavigate={navigateTo}
      />

      <main className="flex-1 flex flex-col overflow-hidden">
        {renderCurrentPage()}
      </main>

      {/* Global Enterprise Document Detail Modal */}
      <DocumentDetailModal
        docNumber={activeModalDocNumber}
        onClose={() => setActiveModalDocNumber(null)}
        onNavigate={navigateTo}
        onOpenDoc={(num) => setActiveModalDocNumber(num)}
      />
    </div>
  );
}
