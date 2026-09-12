import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { CompanyProvider } from './context/CompanyContext';
import { Navbar } from './components/Navbar';
import { Sidebar, TabType } from './components/Sidebar';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { GenerateTagPage } from './pages/GenerateTagPage';
import { BulkUploadPage } from './pages/BulkUploadPage';
import { AssetRegisterPage } from './pages/AssetRegisterPage';
import { PrintingPage } from './pages/PrintingPage';
import { CompanyManagementPage } from './pages/CompanyManagementPage';
import { TagTemplatesPage } from './pages/TagTemplatesPage';
import { AuditLogPage } from './pages/AuditLogPage';
import { UserManagementPage } from './pages/UserManagementPage';
import { AdminSettingsPage } from './pages/AdminSettingsPage';
import { Activity } from 'lucide-react';

const MainLayout: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white text-sm">
        <Activity className="w-6 h-6 animate-spin text-blue-500 mr-2" />
        Initializing Tagging Suite...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <CompanyProvider>
      <div className="min-h-screen bg-slate-100 flex flex-col font-sans">
        <Navbar />
        <div className="flex-1 flex overflow-hidden">
          <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
          <main className="flex-1 p-6 md:p-8 overflow-y-auto max-h-[calc(100vh-4rem)]">
            {activeTab === 'dashboard' && <DashboardPage onNavigate={setActiveTab} />}
            {activeTab === 'generate' && <GenerateTagPage />}
            {activeTab === 'bulk' && <BulkUploadPage />}
            {activeTab === 'register' && <AssetRegisterPage />}
            {activeTab === 'printing' && <PrintingPage />}
            {activeTab === 'companies' && <CompanyManagementPage />}
            {activeTab === 'templates' && <TagTemplatesPage />}
            {activeTab === 'audit' && <AuditLogPage />}
            {activeTab === 'users' && <UserManagementPage />}
            {activeTab === 'settings' && <AdminSettingsPage />}
          </main>
        </div>
      </div>
    </CompanyProvider>
  );
};

export function App() {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  );
}

export default App;
