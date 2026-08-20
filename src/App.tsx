/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { ModuleId, Voucher, Client, CompanyProfile, VoucherType, VoucherStatus, User } from './types';
import { StorageService } from './services/storage';

// Common Components
import { Sidebar } from './components/common/Sidebar';
import { Header } from './components/common/Header';
import { BackupRestoreModal } from './components/common/BackupRestoreModal';
import { GettingStartedModal } from './components/common/GettingStartedModal';

// Module 0: Home Dashboard
import { HomeDashboardView } from './components/dashboard/HomeDashboardView';

// Module 1: Vouchers
import { VoucherList } from './components/vouchers/VoucherList';
import { VoucherEditor } from './components/vouchers/VoucherEditor';
import { VoucherPreviewModal } from './components/vouchers/VoucherPreviewModal';
import { AIInvoiceScanModal } from './components/vouchers/AIInvoiceScanModal';

// Module 2: PDF Toolkit
import { PDFToolkitView } from './components/pdfToolkit/PDFToolkitView';

// Module 3: Clientele (CRM)
import { ClientList } from './components/clientele/ClientList';
import { ClientDetailModal } from './components/clientele/ClientDetailModal';
import { ClientFormModal } from './components/clientele/ClientFormModal';
import { BulkImportModal } from './components/clientele/BulkImportModal';

// Module 4: Intelligence
import { GlobalIntelligenceView } from './components/intelligence/GlobalIntelligenceView';
import { AIAssistantModal } from './components/intelligence/AIAssistantModal';

// Branding & Company Profile
import { CompanyProfileSettings } from './components/branding/CompanyProfileSettings';

// Products Master
import { ManageProductsView } from './components/products/ManageProductsView';

// Finance Analytics & Trends
import { PaymentTrendsView } from './components/finance/PaymentTrendsView';

// User Access & Signup Gatekeeper
import { SignupRequestsView } from './components/signups/SignupRequestsView';

// Multi-Tenant Auth & Onboarding Modal
import { AuthModal } from './components/auth/AuthModal';
import { AuthScreen } from './components/auth/AuthScreen';

export default function App() {
  const storage = StorageService.getInstance();

  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => storage.isSessionActive());

  // User State
  const [currentUser, setCurrentUser] = useState<User>(storage.getCurrentUser());
  const [users, setUsers] = useState<User[]>(storage.getUsers());

  // Primary Navigation
  const [activeModule, setActiveModule] = useState<ModuleId>(
    currentUser.role === 'client_portal' ? 'vouchers' : 'dashboard'
  );

  // Core Data States
  const [companyProfile, setCompanyProfile] = useState<CompanyProfile>(storage.getCompanyProfile());
  const [vouchers, setVouchers] = useState<Voucher[]>(storage.getVouchers());
  const [clients, setClients] = useState<Client[]>(storage.getClients());

  // Connectivity
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);

  // Modals & Sub-views
  const [editingVoucher, setEditingVoucher] = useState<Voucher | null | undefined>(undefined);
  const [previewVoucher, setPreviewVoucher] = useState<Voucher | null>(null);
  const [isAIScanOpen, setIsAIScanOpen] = useState(false);
  const [isAIAnalystOpen, setIsAIAnalystOpen] = useState(false);

  const [activeClientDetail, setActiveClientDetail] = useState<Client | null>(null);
  const [editingClient, setEditingClient] = useState<Client | null | undefined>(undefined);
  const [isBulkImportOpen, setIsBulkImportOpen] = useState(false);

  const [isBackupModalOpen, setIsBackupModalOpen] = useState(false);
  const [isGuideModalOpen, setIsGuideModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Initialize theme and online listeners
  useEffect(() => {
    storage.applyTheme(companyProfile.theme);

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const refreshAllData = () => {
    setCompanyProfile(storage.getCompanyProfile());
    setVouchers(storage.getVouchers());
    setClients(storage.getClients());
    setCurrentUser(storage.getCurrentUser());
    setUsers(storage.getUsers());
  };

  const handleSwitchUser = (newUser: User) => {
    storage.setCurrentUser(newUser);
    setCurrentUser(newUser);
    refreshAllData();

    // If switched to client portal, enforce module boundary
    if (newUser.role === 'client_portal') {
      setActiveModule('vouchers');
    }
  };

  const handleLoginSuccess = (newUser: User) => {
    storage.login(newUser);
    setCurrentUser(newUser);
    setIsAuthenticated(true);
    refreshAllData();

    if (newUser.role === 'client_portal') {
      setActiveModule('vouchers');
    } else {
      setActiveModule('dashboard');
    }
  };

  const handleLogout = () => {
    storage.logout();
    setIsAuthenticated(false);
  };

  // Voucher Handlers
  const handleCreateVoucher = (type?: VoucherType) => {
    if (currentUser.role === 'client_portal') return;

    setActiveModule('vouchers');
    if (type) {
      const nextNum = storage.getNextDocNumber(type);
      setEditingVoucher({
        id: `vouch_${Date.now()}`,
        type,
        docNumber: nextNum,
        docDate: new Date().toISOString().slice(0, 10),
        clientId: '',
        clientName: '',
        clientAddress: '',
        clientMobile: '',
        clientTin: '',
        currency: 'TZS',
        items: [
          {
            id: 'item_1',
            itemName: 'Bitumen Grade 60/70 (Steel Drums 200L / Bulk MT)',
            description: '',
            quantity: 1,
            unit: 'MT',
            rate: 1180000,
            vatRule: 'optional',
            vatApplied: true,
            vatPercent: 18,
            amount: 1180000,
            vatAmount: 212400,
            lineTotal: 1392400,
          },
        ],
        subtotal: 1180000,
        totalVat: 212400,
        grandTotal: 1392400,
        roundOffEnabled: false,
        roundOffAdjustment: 0,
        finalGrandTotal: 1392400,
        status: 'draft',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    } else {
      setEditingVoucher(null);
    }
  };

  const handleEditVoucher = (voucher: Voucher) => {
    if (currentUser.role === 'client_portal') return;
    setActiveModule('vouchers');
    setEditingVoucher(voucher);
  };

  const handleDuplicateVoucher = (voucher: Voucher) => {
    if (currentUser.role === 'client_portal') return;
    setActiveModule('vouchers');
    const newDocNum = storage.getNextDocNumber(voucher.type);
    setEditingVoucher({
      ...voucher,
      id: `vouch_${Date.now()}`,
      docNumber: newDocNum,
      docDate: new Date().toISOString().slice(0, 10),
      status: 'draft',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  };

  const handleConvertVoucher = (voucher: Voucher, targetType: VoucherType) => {
    if (currentUser.role === 'client_portal') return;
    setActiveModule('vouchers');
    const newDocNum = storage.getNextDocNumber(targetType);
    setEditingVoucher({
      ...voucher,
      id: `vouch_${Date.now()}`,
      type: targetType,
      docNumber: newDocNum,
      docDate: new Date().toISOString().slice(0, 10),
      status: 'draft',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  };

  const handleSaveVoucher = (savedVoucher: Voucher) => {
    storage.saveVoucher(savedVoucher);
    setVouchers(storage.getVouchers());
    setEditingVoucher(undefined);
  };

  const handleDeleteVoucher = (id: string) => {
    if (currentUser.role === 'client_portal') return;
    storage.deleteVoucher(id);
    setVouchers(storage.getVouchers());
  };

  const handleVoucherStatusChange = (id: string, newStatus: VoucherStatus) => {
    if (currentUser.role === 'client_portal') return;
    storage.updateVoucherStatus(id, newStatus);
    setVouchers(storage.getVouchers());
  };

  const handleAIScanParsed = (parsed: Partial<Voucher>) => {
    if (currentUser.role === 'client_portal') return;
    setActiveModule('vouchers');
    const targetType = parsed.type || 'SALES';
    const nextNum = storage.getNextDocNumber(targetType);

    setEditingVoucher({
      id: `vouch_${Date.now()}`,
      type: targetType,
      docNumber: nextNum,
      docDate: parsed.docDate || new Date().toISOString().slice(0, 10),
      clientId: parsed.clientId || '',
      clientName: parsed.clientName || 'Extracted Supplier / Client',
      clientAddress: parsed.clientAddress || '',
      clientMobile: parsed.clientMobile || '',
      clientTin: parsed.clientTin || '',
      currency: parsed.currency || 'TZS',
      items: parsed.items || [
        {
          id: 'item_1',
          itemName: 'Scanned Items',
          description: '',
          quantity: 1,
          rate: parsed.subtotal || 0,
          vatPercent: 18,
          amount: parsed.subtotal || 0,
          vatAmount: (parsed.subtotal || 0) * 0.18,
          lineTotal: (parsed.subtotal || 0) * 1.18,
        },
      ],
      subtotal: parsed.subtotal || 0,
      totalVat: parsed.totalVat || 0,
      grandTotal: parsed.grandTotal || 0,
      roundOffEnabled: false,
      roundOffAdjustment: 0,
      finalGrandTotal: parsed.finalGrandTotal || parsed.grandTotal || 0,
      notes: parsed.notes || 'Auto-extracted via Gemini OCR',
      status: 'draft',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  };

  // Client Handlers
  const handleSaveClient = (client: Client) => {
    storage.saveClient(client);
    setClients(storage.getClients());
  };

  const handleDeleteClient = (clientId: string) => {
    storage.deleteClient(clientId);
    setClients(storage.getClients());
  };

  const handleCreateVoucherForClient = (client: Client) => {
    if (currentUser.role === 'client_portal') return;
    setActiveModule('vouchers');
    const nextNum = storage.getNextDocNumber('SALES');
    setEditingVoucher({
      id: `vouch_${Date.now()}`,
      type: 'SALES',
      docNumber: nextNum,
      docDate: new Date().toISOString().slice(0, 10),
      clientId: client.id,
      clientName: client.name,
      clientAddress: client.address,
      clientMobile: client.mobile,
      clientTin: client.tin,
      currency: 'TZS',
      items: [
        {
          id: 'item_1',
          itemName: 'Bitumen Grade 60/70 (Steel Drums 200L / Bulk MT)',
          description: '',
          quantity: 1,
          unit: 'MT',
          rate: 1180000,
          vatRule: 'optional',
          vatApplied: true,
          vatPercent: 18,
          amount: 1180000,
          vatAmount: 212400,
          lineTotal: 1392400,
        },
      ],
      subtotal: 1180000,
      totalVat: 212400,
      grandTotal: 1392400,
      roundOffEnabled: false,
      roundOffAdjustment: 0,
      finalGrandTotal: 1392400,
      status: 'draft',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  };

  // If not authenticated, render the dedicated Landing & Authentication Gate
  if (!isAuthenticated) {
    return <AuthScreen onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div id="desktop-app-root" className="flex h-screen w-screen overflow-hidden bg-slate-100 font-sans text-slate-900">
      {/* Persistent Desktop Sidebar */}
      <Sidebar
        activeModule={activeModule}
        onSelectModule={(mod) => {
          // Prevent client portal users from accessing internal routes
          if (currentUser.role === 'client_portal' && !['vouchers', 'pdf-toolkit'].includes(mod)) {
            return;
          }
          setActiveModule(mod);
          setEditingVoucher(undefined);
        }}
        onOpenBackupModal={() => setIsBackupModalOpen(true)}
        onOpenGuideModal={() => setIsGuideModalOpen(true)}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
        companyProfile={companyProfile}
        isOnline={isOnline}
        currentUser={currentUser}
        users={users}
        onSwitchUser={handleSwitchUser}
      />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Top Header */}
        <Header
          activeModule={activeModule}
          companyProfile={companyProfile}
          isOnline={isOnline}
          currentUser={currentUser}
          onCreateVoucher={() => handleCreateVoucher()}
          onCreateClient={() => setEditingClient(null)}
          onOpenBackupModal={() => setIsBackupModalOpen(true)}
          onOpenAIAnalyst={() => setIsAIAnalystOpen(true)}
          onLogout={handleLogout}
        />

        {/* Scrollable Viewport */}
        <main className="flex-1 overflow-y-auto bg-slate-100/90">
          {/* MODULE 0: HOME DASHBOARD (INTERNAL ONLY) */}
          {activeModule === 'dashboard' && currentUser.role !== 'client_portal' && (
            <HomeDashboardView
              onNavigate={(mod) => setActiveModule(mod)}
              onCreateVoucher={(type) => handleCreateVoucher(type)}
              onOpenAIAnalyst={() => setIsAIAnalystOpen(true)}
              onSelectClient={(clientId) => {
                const found = clients.find((c) => c.id === clientId);
                if (found) {
                  setActiveClientDetail(found);
                }
              }}
            />
          )}

          {/* MODULE 1: VOUCHERS & INVOICING */}
          {activeModule === 'vouchers' && (
            <>
              {editingVoucher !== undefined ? (
                <VoucherEditor
                  initialVoucher={editingVoucher}
                  clients={clients}
                  companyProfile={companyProfile}
                  onSave={handleSaveVoucher}
                  onCancel={() => setEditingVoucher(undefined)}
                  onPreview={(v) => setPreviewVoucher(v)}
                />
              ) : (
                <VoucherList
                  vouchers={vouchers}
                  companyProfile={companyProfile}
                  onCreateVoucher={handleCreateVoucher}
                  onEditVoucher={handleEditVoucher}
                  onPreviewVoucher={(v) => setPreviewVoucher(v)}
                  onDuplicateVoucher={handleDuplicateVoucher}
                  onConvertVoucher={handleConvertVoucher}
                  onDeleteVoucher={handleDeleteVoucher}
                  onStatusChange={handleVoucherStatusChange}
                  onOpenAIScan={() => setIsAIScanOpen(true)}
                />
              )}
            </>
          )}

          {/* MODULE 2: OFFLINE PDF TOOLKIT */}
          {activeModule === 'pdf-toolkit' && <PDFToolkitView companyProfile={companyProfile} />}

          {/* MODULE 3: CLIENTELE (CRM) - INTERNAL ONLY */}
          {activeModule === 'clientele' && currentUser.role !== 'client_portal' && currentUser.role !== 'procurement' && (
            <ClientList
              clients={clients}
              vouchers={vouchers}
              onOpenClientDetail={(c) => setActiveClientDetail(c)}
              onOpenClientForm={(c) => setEditingClient(c || null)}
              onDeleteClient={handleDeleteClient}
              onCreateVoucherForClient={handleCreateVoucherForClient}
              onOpenBulkImport={() => setIsBulkImportOpen(true)}
            />
          )}

          {/* MODULE 4: PRODUCTS MASTER - ADMIN ONLY */}
          {activeModule === 'products' && currentUser.role === 'admin' && (
            <ManageProductsView />
          )}

          {/* MODULE 5: PAYMENT TRENDS & DEBT AGING - ADMIN & FINANCE */}
          {activeModule === 'payment-trends' && (currentUser.role === 'admin' || currentUser.role === 'finance') && (
            <PaymentTrendsView />
          )}

          {/* MODULE 6: GLOBAL TRADE INTELLIGENCE - INTERNAL ONLY */}
          {activeModule === 'intelligence' && currentUser.role !== 'client_portal' && (
            <GlobalIntelligenceView onOpenAIAnalyst={() => setIsAIAnalystOpen(true)} />
          )}

          {/* MODULE 7: SIGN-UP GATEKEEPER - ADMIN ONLY */}
          {activeModule === 'signups' && currentUser.role === 'admin' && (
            <SignupRequestsView />
          )}

          {/* MODULE 8: COMPANY PROFILE & BRANDING - ADMIN ONLY */}
          {activeModule === 'branding' && currentUser.role === 'admin' && (
            <CompanyProfileSettings
              companyProfile={companyProfile}
              onProfileUpdated={(updated) => setCompanyProfile(updated)}
            />
          )}
        </main>
      </div>

      {/* Global Modals */}
      {/* 1. Voucher Preview Modal */}
      <VoucherPreviewModal
        voucher={previewVoucher}
        companyProfile={companyProfile}
        isOpen={Boolean(previewVoucher)}
        onClose={() => setPreviewVoucher(null)}
      />

      {/* 2. AI Invoice Scan Modal */}
      <AIInvoiceScanModal
        isOpen={isAIScanOpen}
        onClose={() => setIsAIScanOpen(false)}
        onInvoiceParsed={handleAIScanParsed}
      />

      {/* 3. AI Grounded Trade Analyst Modal */}
      <AIAssistantModal
        isOpen={isAIAnalystOpen}
        onClose={() => setIsAIAnalystOpen(false)}
      />

      {/* 4. Client Detail / Relationship Timeline Modal */}
      <ClientDetailModal
        client={activeClientDetail}
        vouchers={vouchers}
        isOpen={Boolean(activeClientDetail)}
        onClose={() => setActiveClientDetail(null)}
        onDuplicateSale={(v) => {
          setActiveClientDetail(null);
          handleDuplicateVoucher(v);
        }}
        onCreateNewSale={(c) => {
          setActiveClientDetail(null);
          handleCreateVoucherForClient(c);
        }}
        onPreviewVoucher={(v) => setPreviewVoucher(v)}
      />

      {/* 5. Client Form Modal */}
      <ClientFormModal
        initialClient={editingClient}
        isOpen={editingClient !== undefined}
        onClose={() => setEditingClient(undefined)}
        onSave={handleSaveClient}
      />

      {/* 6. Bulk Import Modal */}
      <BulkImportModal
        isOpen={isBulkImportOpen}
        onClose={() => setIsBulkImportOpen(false)}
        onImportComplete={refreshAllData}
      />

      {/* 7. Database Backup & Restore Modal */}
      <BackupRestoreModal
        isOpen={isBackupModalOpen}
        onClose={() => setIsBackupModalOpen(false)}
        onRefreshData={refreshAllData}
      />

      {/* 8. Desktop User Guide Modal */}
      <GettingStartedModal
        isOpen={isGuideModalOpen}
        onClose={() => setIsGuideModalOpen(false)}
      />

      {/* 9. Multi-Tenant Auth & Onboarding Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onUserChanged={handleSwitchUser}
      />
    </div>
  );
}
