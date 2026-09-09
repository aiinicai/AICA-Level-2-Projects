import React, { useState, useEffect } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { RoleSwitcherBar } from './components/RoleSwitcherBar';
import { Navbar } from './components/Navbar';
import { DepartmentForm } from './components/DepartmentForm';
import { FinanceControllerView } from './components/FinanceControllerView';
import { ManagementDashboard } from './components/ManagementDashboard';
import { AdminSettings } from './components/AdminSettings';
import { ApprovalSummaryModal } from './components/ApprovalSummaryModal';
import { AuditTrailModal } from './components/AuditTrailModal';
import { Department } from './types';

const MainApp: React.FC = () => {
  const { currentUser } = useApp();

  // Tab navigation state
  const [currentTab, setCurrentTab] = useState<string>('dept_form');
  const [inspectedDept, setInspectedDept] = useState<Department | undefined>(undefined);

  // Modals state
  const [isAuditTrailOpen, setIsAuditTrailOpen] = useState<boolean>(false);
  const [isApprovalSummaryOpen, setIsApprovalSummaryOpen] = useState<boolean>(false);

  // Update default tab based on role when role changes
  useEffect(() => {
    if (currentUser.role === 'department_submitter') {
      setCurrentTab('dept_form');
      setInspectedDept(currentUser.department);
    } else if (currentUser.role === 'finance_controller') {
      setCurrentTab('controller_view');
      setInspectedDept(undefined);
    } else if (currentUser.role === 'management') {
      setCurrentTab('dashboard');
      setInspectedDept(undefined);
    } else if (currentUser.role === 'admin') {
      setCurrentTab('admin_settings');
      setInspectedDept(undefined);
    }
  }, [currentUser.id, currentUser.role, currentUser.department]);

  const handleNavigateToDeptInspection = (dept: Department) => {
    setInspectedDept(dept);
    setCurrentTab('dept_form');
  };

  return (
    <div className="min-h-screen bg-[#F1F5F9] text-[#1E293B] flex flex-col font-sans antialiased selection:bg-blue-600 selection:text-white">
      {/* Top Interactive Role Switcher Banner */}
      <RoleSwitcherBar />

      {/* Main Corporate Header */}
      <Navbar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        onOpenAuditTrail={() => setIsAuditTrailOpen(true)}
        onOpenApprovalSummary={() => setIsApprovalSummaryOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {currentTab === 'dept_form' && (
          <DepartmentForm departmentOverride={inspectedDept} />
        )}

        {currentTab === 'controller_view' && (
          <FinanceControllerView onNavigateToDept={handleNavigateToDeptInspection} />
        )}

        {currentTab === 'dashboard' && (
          <ManagementDashboard onOpenApprovalSummary={() => setIsApprovalSummaryOpen(true)} />
        )}

        {currentTab === 'admin_settings' && (
          <AdminSettings />
        )}
      </main>

      {/* Global Modals */}
      <ApprovalSummaryModal
        isOpen={isApprovalSummaryOpen}
        onClose={() => setIsApprovalSummaryOpen(false)}
      />

      <AuditTrailModal
        isOpen={isAuditTrailOpen}
        onClose={() => setIsAuditTrailOpen(false)}
      />

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-3.5 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-[10px] text-slate-400 uppercase tracking-wider gap-2">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-700">MAROPOST INDIA</span>
            <span>•</span>
            <span>Monthly Cash Management & Currency Authorization System</span>
          </div>
          <div className="flex items-center gap-3">
            <span>Entity: India Tech & Operations</span>
            <span>•</span>
            <span className="font-mono">Timezone: IST (UTC+5:30)</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <AppProvider>
      <MainApp />
    </AppProvider>
  );
}
