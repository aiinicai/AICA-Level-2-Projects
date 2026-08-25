import React, { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardView } from './components/Dashboard/DashboardView';
import { VendorMasterView } from './components/Vendors/VendorMasterView';
import { MSMEVerificationView } from './components/Verification/MSMEVerificationView';
import { InvoiceRegisterView } from './components/Invoices/InvoiceRegisterView';
import { PaymentRegisterView } from './components/Payments/PaymentRegisterView';
import { InterestCalculatorView } from './components/Calculator/InterestCalculatorView';
import { AgeingAnalysisView } from './components/Ageing/AgeingAnalysisView';
import { ReportsHubView } from './components/Reports/ReportsHubView';
import { MastersManagementView } from './components/Masters/MastersManagementView';
import { AuditTrailView } from './components/Audit/AuditTrailView';
import { ShieldCheck } from 'lucide-react';

const MainContent: React.FC = () => {
  const { activeTab } = useApp();

  return (
    <div className="p-4 sm:p-6 lg:p-8 flex-1 overflow-y-auto min-w-0">
      {activeTab === 'dashboard' && <DashboardView />}
      {activeTab === 'vendors' && <VendorMasterView />}
      {activeTab === 'verification' && <MSMEVerificationView />}
      {activeTab === 'invoices' && <InvoiceRegisterView />}
      {activeTab === 'payments' && <PaymentRegisterView />}
      {activeTab === 'calculator' && <InterestCalculatorView />}
      {activeTab === 'ageing' && <AgeingAnalysisView />}
      {activeTab === 'reports' && <ReportsHubView />}
      {activeTab === 'masters' && <MastersManagementView />}
      {activeTab === 'audit' && <AuditTrailView />}
    </div>
  );
};

const FooterInfoBar: React.FC = () => {
  const { rateMaster } = useApp();
  const currentRate = rateMaster[0] || { referenceRate: 6.5, applicableMSMERate: 19.5, effectiveFrom: '2024-04-01' };

  return (
    <footer className="h-8 bg-white border-t border-slate-200 px-6 flex items-center justify-between text-[10px] font-medium text-slate-500 shrink-0">
      <div className="flex items-center gap-4">
        <span>
          RBI Repo Rate: <strong className="text-slate-900 font-semibold">{currentRate.referenceRate}%</strong>
        </span>
        <span className="hidden sm:inline">•</span>
        <span className="hidden sm:inline">
          MSME Comp. Interest: <strong className="text-slate-900 font-semibold">{currentRate.applicableMSMERate}% (3x Repo)</strong>
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="hidden md:inline">Last Master Update: {currentRate.effectiveFrom}</span>
        <span className="text-blue-600 font-bold flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          SYSTEM COMPLIANT
        </span>
      </div>
    </footer>
  );
};

const AppLayout: React.FC = () => {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-full bg-[#f1f5f9] font-sans overflow-hidden antialiased text-slate-800">
      {/* Sidebar Navigation */}
      <Sidebar
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Header onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)} />
        <MainContent />
        <FooterInfoBar />
      </main>
    </div>
  );
};

export default function App() {
  return (
    <AppProvider>
      <AppLayout />
    </AppProvider>
  );
}
