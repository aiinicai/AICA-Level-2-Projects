import React, { useState, useEffect, useCallback } from 'react';
import { 
  User, 
  Client, 
  DeliveryLog, 
  BillingClientSummary, 
  ConfirmationItem, 
  InvoiceItem, 
  AuditLogItem, 
  EmailLogItem 
} from './types';
import { systemService } from './lib/services/systemService';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { WorkflowBar } from './components/WorkflowBar';
import { LoginScreen } from './components/LoginScreen';
import { DashboardScreen } from './components/DashboardScreen';
import { ClientsScreen } from './components/ClientsScreen';
import { DeliveryLogsScreen } from './components/DeliveryLogsScreen';
import { BillingScreen } from './components/BillingScreen';
import { ConfirmationsScreen } from './components/ConfirmationsScreen';
import { InvoicesScreen } from './components/InvoicesScreen';
import { EmailsScreen } from './components/EmailsScreen';
import { AuditTrailScreen } from './components/AuditTrailScreen';
import { DatabaseViewerScreen } from './components/DatabaseViewerScreen';
import { SettingsScreen } from './components/SettingsScreen';

export default function App() {
  // App can only be accessed after login; starts on Login page
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [theme, setTheme] = useState<string>(() => localStorage.getItem('qb_theme') || 'blue');
  useEffect(() => {
    localStorage.setItem('qb_theme', theme);
  }, [theme]);

  // Data states
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [deliveryLogs, setDeliveryLogs] = useState<DeliveryLog[]>([]);
  const [quarter, setQuarter] = useState<string>('Q1');
  const [financialYear, setFinancialYear] = useState<string>('2026-27');
  const [billingData, setBillingData] = useState<{
    summaries: BillingClientSummary[];
    totalFiles: number;
    totalBilling: number;
  }>({ summaries: [], totalFiles: 0, totalBilling: 0 });
  const [confirmations, setConfirmations] = useState<ConfirmationItem[]>([]);
  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [emails, setEmails] = useState<EmailLogItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);

  // Fetch functions using systemService
  const refreshAllData = useCallback(() => {
    setIsRefreshing(true);
    try {
      const dData = systemService.getDashboardData();
      setDashboardData(dData);

      const cData = systemService.getClients();
      setClients(cData);

      const lData = systemService.getDeliveryLogs();
      setDeliveryLogs(lData);

      const bData = systemService.getQuarterlyBilling(quarter, financialYear);
      setBillingData(bData);

      const confData = systemService.getConfirmations();
      setConfirmations(confData);

      const invData = systemService.getInvoices();
      setInvoices(invData);

      const eData = systemService.getEmails();
      setEmails(eData);

      const aData = systemService.getAuditLogs();
      setAuditLogs(aData);
    } catch (e) {
      console.error('Error refreshing system data:', e);
    } finally {
      setIsRefreshing(false);
    }
  }, [quarter, financialYear]);

  useEffect(() => {
    if (currentUser) {
      refreshAllData();
    }
  }, [currentUser, refreshAllData]);

  // Automated follow-up reminders: every 5 minutes while the app is open (and
  // once right on login), check whether any client still awaiting
  // confirmation is overdue for a reminder (Settings > Reminder Interval,
  // default 5 days since the confirmation request or last reminder) and send
  // one if so. This runs app-wide - not tied to the Confirmations tab being
  // open - so a client won't miss a reminder just because the user is
  // working on a different screen. Note this only fires while this browser
  // tab is open (the data lives in localStorage, not a shared backend), so
  // it's a "keep the tab open" automation rather than a true server cron.
  useEffect(() => {
    if (!currentUser) return;

    const runReminderCheck = async () => {
      try {
        const result = await systemService.checkAndSendReminders();
        if (result.sentClients.length > 0) {
          refreshAllData();
        }
      } catch (e) {
        console.error('Error checking/sending confirmation reminders:', e);
      }
    };

    runReminderCheck();
    const interval = setInterval(runReminderCheck, 5 * 60 * 1000); // check every 5 minutes
    return () => clearInterval(interval);
  }, [currentUser, refreshAllData]);

  // Protect Admin-only database viewer
  useEffect(() => {
    if (currentUser && currentUser.role !== 'Admin' && currentTab === 'database') {
      setCurrentTab('dashboard');
    }
  }, [currentUser, currentTab]);

  // Handlers
  const handleLoginSuccess = (user: User) => {
    setCurrentUser(user);
    try {
      localStorage.setItem('qb_user', JSON.stringify(user));
    } catch (e) {
      // ignore
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    try {
      localStorage.removeItem('qb_user');
      sessionStorage.removeItem('qb_user');
    } catch (e) {
      // ignore
    }
  };

  const handleRecalculateBilling = () => {
    systemService.calculateQuarterlyBilling(quarter, financialYear);
    refreshAllData();
  };

  const handleSimulateClientReply = (billingId: string, clientName: string) => {
    try {
      systemService.simulateConfirmation(billingId);
      refreshAllData();
      setCurrentTab('confirmations');
    } catch (err) {
      console.error('Error simulating reply:', err);
    }
  };

  if (!currentUser) {
    return <LoginScreen onLoginSuccess={handleLoginSuccess} />;
  }

  const pendingCount = confirmations.filter((c) => c.status === 'PENDING_CONFIRMATION').length;

  return (
    <div className={`flex h-screen bg-slate-100 text-slate-800 antialiased overflow-hidden font-sans theme-${theme}`}>
      {/* Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        currentUser={currentUser}
        onLogout={handleLogout}
        pendingConfirmationsCount={pendingCount}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <Header
          currentTab={currentTab}
          currentUser={currentUser}
          onRefresh={refreshAllData}
          isRefreshing={isRefreshing}
          onSelectTab={setCurrentTab}
          onLogout={handleLogout}
          theme={theme}
          onThemeChange={setTheme}
        />

        {/* Workflow Guide Bar */}
        <WorkflowBar currentTab={currentTab} onSelectTab={setCurrentTab} />

        {/* Dynamic Screen View */}
        <main className="flex-1 overflow-y-auto">
          {currentTab === 'dashboard' && (
            <DashboardScreen
              data={dashboardData}
              loading={isRefreshing}
              onNavigate={setCurrentTab}
              onRefresh={refreshAllData}
            />
          )}

          {currentTab === 'clients' && (
            <ClientsScreen
              clients={clients}
              loading={isRefreshing}
              onRefresh={refreshAllData}
              currentUserRole={currentUser.role}
            />
          )}

          {currentTab === 'delivery-logs' && (
            <DeliveryLogsScreen
              logs={deliveryLogs}
              loading={isRefreshing}
              onRefresh={refreshAllData}
              onNavigateToBilling={() => {
                setCurrentTab('billing');
                refreshAllData();
              }}
            />
          )}

          {currentTab === 'billing' && (
            <BillingScreen
              quarter={quarter}
              financialYear={financialYear}
              onQuarterChange={(q) => {
                setQuarter(q);
              }}
              onFyChange={(fy) => {
                setFinancialYear(fy);
              }}
              billingData={billingData}
              loading={isRefreshing}
              onRecalculate={handleRecalculateBilling}
              onNavigateToConfirmations={() => {
                refreshAllData();
                setCurrentTab('confirmations');
              }}
              onNavigateToEmails={() => {
                refreshAllData();
                setCurrentTab('emails');
              }}
            />
          )}

          {currentTab === 'confirmations' && (
            <ConfirmationsScreen
              confirmations={confirmations}
              loading={isRefreshing}
              onRefresh={refreshAllData}
              onNavigateToInvoices={() => {
                refreshAllData();
                setCurrentTab('invoices');
              }}
              onNavigateToAudit={() => {
                refreshAllData();
                setCurrentTab('audit');
              }}
            />
          )}

          {currentTab === 'invoices' && (
            <InvoicesScreen
              invoices={invoices}
              loading={isRefreshing}
              onRefresh={refreshAllData}
              onNavigateToEmails={() => {
                refreshAllData();
                setCurrentTab('emails');
              }}
            />
          )}

          {currentTab === 'emails' && (
            <EmailsScreen
              emails={emails}
              loading={isRefreshing}
              onRefresh={refreshAllData}
              onSimulateReply={handleSimulateClientReply}
            />
          )}

          {currentTab === 'audit' && (
            <AuditTrailScreen
              logs={auditLogs}
              loading={isRefreshing}
              onRefresh={refreshAllData}
            />
          )}

          {currentTab === 'database' && currentUser.role === 'Admin' && (
            <DatabaseViewerScreen onRefresh={refreshAllData} />
          )}

          {currentTab === 'settings' && (
            <SettingsScreen onRefresh={refreshAllData} currentUser={currentUser} />
          )}
        </main>
      </div>
    </div>
  );
}
