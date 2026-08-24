import { useEffect, useState } from 'react';
import type { Client, ValidationItem, FinancialStatements, User } from './types';
import { fetchClients, fetchValidations, fetchFinancialStatements, fetchCurrentUser, logout } from './services/api';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { AuditInspectorDrawer } from './components/AuditInspectorDrawer';
import { LoginPage } from './components/LoginPage';

import { DashboardPage } from './pages/DashboardPage';
import { ClientSetupPage } from './pages/ClientSetupPage';
import { UploadCenterPage } from './pages/UploadCenterPage';
import { SplitWorkbenchPage } from './pages/SplitWorkbenchPage';
import { LedgerMappingPage } from './pages/LedgerMappingPage';
import { RuleStudioPage } from './pages/RuleStudioPage';
import { SupportingSchedulesPage } from './pages/SupportingSchedulesPage';
import { FinancialStatementsPage } from './pages/FinancialStatementsPage';
import { CashFlowStatementPage } from './pages/CashFlowStatementPage';
import { AccountingPoliciesPage } from './pages/AccountingPoliciesPage';
import { NotesAccountsPage } from './pages/NotesAccountsPage';
import { RatioAnalysisPage } from './pages/RatioAnalysisPage';
import { ValidationChecksPage } from './pages/ValidationChecksPage';
import { ExportReportsPage } from './pages/ExportReportsPage';
import { UsersPage } from './pages/UsersPage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authChecking, setAuthChecking] = useState<boolean>(true);

  const [clients, setClients] = useState<Client[]>([]);
  const [activeClient, setActiveClient] = useState<Client | null>(null);
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [loading, setLoading] = useState<boolean>(true);

  const [validations, setValidations] = useState<ValidationItem[]>([]);
  const [financialStatements, setFinancialStatements] = useState<FinancialStatements | null>(null);

  // Check stored auth session
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const u = await fetchCurrentUser();
        setCurrentUser(u);
      } catch (e) {
        setCurrentUser(null);
      } finally {
        setAuthChecking(false);
      }
    };
    checkAuth();
  }, []);

  const handleLogout = async () => {
    await logout();
    setCurrentUser(null);
  };

  const loadClients = async () => {
    try {
      const data = await fetchClients();
      setClients(data);
      if (data.length > 0 && !activeClient) {
        setActiveClient(data[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadComplianceMetadata = async (clientId: number) => {
    try {
      const [vRes, fsRes] = await Promise.all([
        fetchValidations(clientId),
        fetchFinancialStatements(clientId)
      ]);
      setValidations(vRes);
      setFinancialStatements(fsRes);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (currentUser) {
      loadClients();
    }
  }, [currentUser]);

  useEffect(() => {
    if (activeClient) {
      loadComplianceMetadata(activeClient.id);
    }
  }, [activeClient?.id]);

  const handleSelectClient = (client: Client) => {
    setActiveClient(client);
  };

  if (authChecking) {
    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-8 font-sans text-xs">
        Initializing FS BUILDER LITE Audit Security Services & Session Authentication...
      </div>
    );
  }

  if (!currentUser) {
    return <LoginPage onLoginSuccess={(u) => setCurrentUser(u)} />;
  }

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-900 text-slate-900 dark:text-slate-100 flex flex-col font-sans">
      <Header
        clients={clients}
        client={activeClient}
        onSelectClient={handleSelectClient}
        currentUser={currentUser}
        onLogout={handleLogout}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} validationsCount={validations.length} />

        <main className="flex-1 p-6 overflow-y-auto bg-slate-100 dark:bg-slate-950 transition-colors">
          {loading || !activeClient ? (
            <div className="p-12 text-center text-slate-500 text-xs font-semibold">
              Initializing FS Builder Lite v0.2 Application Engine...
            </div>
          ) : (
            <>
              {activeTab === 'dashboard' && (
                <DashboardPage client={activeClient} onNavigate={setActiveTab} />
              )}
              {activeTab === 'client-setup' && (
                <ClientSetupPage client={activeClient} onClientUpdated={loadClients} />
              )}
              {activeTab === 'upload-center' && (
                <UploadCenterPage client={activeClient} onUploadSuccess={loadClients} />
              )}
              {activeTab === 'split-workbench' && (
                <SplitWorkbenchPage client={activeClient} />
              )}
              {activeTab === 'ledger-mapping' && (
                <LedgerMappingPage client={activeClient} onNavigate={setActiveTab} />
              )}
              {activeTab === 'rule-studio' && (
                <RuleStudioPage />
              )}
              {activeTab === 'supporting-schedules' && (
                <SupportingSchedulesPage client={activeClient} />
              )}
              {activeTab === 'financial-statements' && (
                <FinancialStatementsPage client={activeClient} onNavigate={setActiveTab} />
              )}
              {activeTab === 'cash-flow' && (
                <CashFlowStatementPage client={activeClient} />
              )}
              {activeTab === 'accounting-policies' && (
                <AccountingPoliciesPage client={activeClient} />
              )}
              {activeTab === 'notes-accounts' && (
                <NotesAccountsPage client={activeClient} />
              )}
              {activeTab === 'ratio-analysis' && (
                <RatioAnalysisPage client={activeClient} />
              )}
              {activeTab === 'validation-checks' && (
                <ValidationChecksPage client={activeClient} />
              )}
              {activeTab === 'export-reports' && (
                <ExportReportsPage client={activeClient} />
              )}
              {activeTab === 'users' && (
                <UsersPage currentUser={currentUser} />
              )}
              {activeTab === 'settings' && <SettingsPage />}
            </>
          )}
        </main>
      </div>

      {/* Floating Audit Inspector Bottom Drawer */}
      <AuditInspectorDrawer 
        validations={validations} 
        financialStatements={financialStatements} 
      />
    </div>
  );
}


export default App;
