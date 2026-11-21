import React, { useState, useEffect } from 'react';
import { 
  Building2, ArrowLeft, Layers, FileCheck, FileSearch, 
  Calculator, Landmark, FileSpreadsheet, Download, UserCheck, AlertTriangle, Sliders, Sparkles
} from 'lucide-react';
import { Header } from './components/Header';
import { ProposalPipeline } from './components/ProposalPipeline';
import { ChecklistTab } from './components/ChecklistTab';
import { ExtractionTab } from './components/ExtractionTab';
import { EvaluationTab } from './components/EvaluationTab';
import { LenderMatrixTab } from './components/LenderMatrixTab';
import { CmaWorkspaceTab } from './components/CmaWorkspaceTab';
import { ReportsTab } from './components/ReportsTab';
import { ReviewerTab } from './components/ReviewerTab';
import { AdminIntegrationsModal } from './components/AdminIntegrationsModal';
import { InstallAppModal } from './components/InstallAppModal';
import { LoginPage } from './components/LoginPage';
import { SwitchRoleModal } from './components/SwitchRoleModal';
import { EditRequirementsModal } from './components/EditRequirementsModal';
import { SequentialUploadWizardModal } from './components/SequentialUploadWizardModal';

import { Proposal, Client, UserRole, DocumentChecklistItem, ExtractedDataRecord, CompanyProfile } from './types';
import { NumberUnitMode, formatProductType, formatINR, formatProposalStatus } from './utils/formatters';
import { ApiClient } from './api/client';

export const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return !!localStorage.getItem('gia_arthwise_token');
  });
  const [currentUser, setCurrentUser] = useState<{ id: string; email: string; full_name: string; role: UserRole } | null>(() => {
    const raw = localStorage.getItem('gia_arthwise_user');
    if (raw) {
      try {
        return JSON.parse(raw);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [currentRole, setCurrentRole] = useState<UserRole>(() => {
    const raw = localStorage.getItem('gia_arthwise_user');
    if (raw) {
      try {
        const u = JSON.parse(raw);
        if (u?.role) return u.role;
      } catch {}
    }
    return 'analyst';
  });
  const [isVerifyingSession, setIsVerifyingSession] = useState<boolean>(() => {
    return !!localStorage.getItem('gia_arthwise_token');
  });
  const [activeCompany, setActiveCompany] = useState<CompanyProfile | null>(null);
  const [unitMode, setUnitMode] = useState<NumberUnitMode>('standard');
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'checklist' | 'extraction' | 'evaluation' | 'lenders' | 'cma' | 'reports' | 'reviewer'>('checklist');

  const [checklistItems, setChecklistItems] = useState<DocumentChecklistItem[]>([]);
  const [extractedRecords, setExtractedRecords] = useState<ExtractedDataRecord[]>([]);
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [showInstallModal, setShowInstallModal] = useState(false);
  const [showEditRequirementsModal, setShowEditRequirementsModal] = useState(false);
  const [wizardProposal, setWizardProposal] = useState<{
    id: string;
    code: string;
    clientName?: string;
    productType?: string;
    requestedAmount?: number | string;
  } | null>(null);
  const [roleSwitchTarget, setRoleSwitchTarget] = useState<UserRole | null>(null);
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadActiveCompany = async () => {
    try {
      const comp = await ApiClient.request<CompanyProfile>('/companies/active');
      setActiveCompany(comp);
    } catch (err) {
      console.warn('Failed to load active company profile:', err);
    }
  };

  useEffect(() => {
    loadActiveCompany();
  }, []);

  // Verify persistent session on mount so page refresh retains login state
  useEffect(() => {
    const verifySavedSession = async () => {
      const savedToken = ApiClient.getToken();
      if (!savedToken) {
        setIsVerifyingSession(false);
        setIsAuthenticated(false);
        return;
      }

      try {
        const user = await ApiClient.request<{ id: string; email: string; full_name: string; role: UserRole }>('/auth/me');
        setCurrentUser(user);
        setCurrentRole(user.role);
        setIsAuthenticated(true);
        localStorage.setItem('gia_arthwise_user', JSON.stringify(user));
      } catch (err) {
        console.warn('Session verification failed on refresh:', err);
        ApiClient.setToken(null);
        localStorage.removeItem('gia_arthwise_user');
        setIsAuthenticated(false);
        setCurrentUser(null);
      } finally {
        setIsVerifyingSession(false);
      }
    };

    verifySavedSession();
  }, []);

  // Catch PWA beforeinstallprompt
  useEffect(() => {
    const handleBeforeInstall = (e: any) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };
    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
  }, []);

  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      const [props, clis] = await Promise.all([
        ApiClient.request<Proposal[]>('/proposals'),
        ApiClient.request<Client[]>('/clients'),
      ]);
      setProposals(props);
      setClients(clis);
      // Retain selectedProposalId as null so it lands on the Home Page showing list of proposals!
    } catch (err) {
      console.error('Data load error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInitiateRoleChange = (newRole: UserRole) => {
    if (newRole === currentRole) return;
    setRoleSwitchTarget(newRole);
  };

  const handleRoleSwitchSuccess = async (
    token: string,
    user: { id: string; email: string; full_name: string; role: UserRole }
  ) => {
    ApiClient.setToken(token);
    localStorage.setItem('gia_arthwise_user', JSON.stringify(user));
    setCurrentUser(user);
    setCurrentRole(user.role);
    setRoleSwitchTarget(null);
    setSelectedProposalId(null);
    await loadInitialData();
  };

  const handleLogout = () => {
    ApiClient.setToken(null);
    localStorage.removeItem('gia_arthwise_user');
    setIsAuthenticated(false);
    setCurrentUser(null);
    setSelectedProposalId(null);
    setProposals([]);
  };

  const loadProposalDetails = async (propId: string) => {
    try {
      const [chk, ext] = await Promise.all([
        ApiClient.request<DocumentChecklistItem[]>(`/proposals/${propId}/checklist`),
        ApiClient.request<ExtractedDataRecord[]>(`/proposals/${propId}/extractions`),
      ]);
      setChecklistItems(chk);
      setExtractedRecords(ext);
    } catch (err) {
      console.error('Error fetching proposal details:', err);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadInitialData();
    }
  }, [currentRole, isAuthenticated]);

  useEffect(() => {
    if (selectedProposalId) {
      loadProposalDetails(selectedProposalId);
    }
  }, [selectedProposalId]);

  const handleCreateProposal = async (data: any) => {
    const newProp = await ApiClient.request<Proposal>('/proposals', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    setProposals([newProp, ...proposals]);
    setSelectedProposalId(newProp.id);
    setActiveTab('checklist');
    const matchedClient = clients.find(c => c.id === newProp.client_id);
    setWizardProposal({
      id: newProp.id,
      code: newProp.proposal_code,
      clientName: matchedClient?.primary_contact_name,
      productType: newProp.product_type,
      requestedAmount: newProp.requested_amount,
    });
    return newProp;
  };

  // 1-Click Synthetic Persona Loader
  const handleLoadSyntheticDemo = async (persona: 'home_loan' | 'lap' | 'tech_sme') => {
    setIsLoading(true);
    try {
      let clientName = '';
      let constitution = '';
      let product: any = 'cash_credit_od';
      let amount = 10000000;
      let tenure = 60;
      let purpose = '';

      if (persona === 'tech_sme') {
        clientName = 'GIA Tech Solutions Private Limited';
        constitution = 'pvt_ltd';
        product = 'cash_credit_od';
        amount = 10000000; // 1 Cr
        tenure = 12;
        purpose = 'Working capital against enterprise cybersecurity contracts and receivables';
      } else if (persona === 'lap') {
        clientName = 'Dr. Rajesh Sharma (Consulting Diagnostics)';
        constitution = 'proprietorship';
        product = 'lap';
        amount = 7500000; // 75 Lakhs
        tenure = 120;
        purpose = 'Secured Loan Against Commercial Property for diagnostic equipment';
      } else {
        clientName = 'Amit Verma (Senior Software Architect)';
        constitution = 'salaried';
        product = 'home_loan';
        amount = 5000000; // 50 Lakhs
        tenure = 240;
        purpose = 'Home Loan for purchase of residential apartment';
      }

      // Create client
      const cli = await ApiClient.request<Client>('/clients', {
        method: 'POST',
        body: JSON.stringify({
          primary_contact_name: clientName,
          phone: '+91 98765 43210',
          email: `${persona}@synthetic-test.in`,
          constitution,
          city: 'Vadodara',
          state: 'Gujarat',
        }),
      });

      // Create entity
      const ent = await ApiClient.request<any>(`/clients/${cli.id}/entities`, {
        method: 'POST',
        body: JSON.stringify({
          legal_name: clientName,
          constitution,
          pan: persona === 'tech_sme' ? 'AAACX0000M' : 'ABCPV1234D',
          date_of_incorporation: '2020-08-15',
        }),
      });

      // Add promoter
      await ApiClient.request(`/clients/entities/${ent.id}/promoters`, {
        method: 'POST',
        body: JSON.stringify({
          name: clientName,
          role: 'director',
          pan: 'ACAPX0000P',
          ownership_pct: 100,
          cibil_score: 742,
        }),
      });

      // Create proposal
      const prop = await ApiClient.request<Proposal>('/proposals', {
        method: 'POST',
        body: JSON.stringify({
          client_id: cli.id,
          entity_id: ent.id,
          product_type: product,
          requested_amount: amount,
          tenure_months: tenure,
          purpose,
          target_rate: 9.25,
        }),
      });

      setProposals([prop, ...proposals]);
      setClients([cli, ...clients]);
      setSelectedProposalId(prop.id);
      setActiveTab('evaluation');
      alert(`Loaded synthetic ${persona.toUpperCase()} demo dossier!`);
    } catch (err: any) {
      alert(err.message || 'Error loading demo');
    } finally {
      setIsLoading(false);
    }
  };

  const selectedProposal = proposals.find(p => p.id === selectedProposalId);
  const selectedClient = clients.find(c => c.id === selectedProposal?.client_id);
  const selectedEntity = selectedClient?.entities?.find(e => e.id === selectedProposal?.entity_id);

  if (isVerifyingSession) {
    return (
      <div className="min-h-screen bg-[#1b2632] flex flex-col items-center justify-center text-white font-sans">
        <div className="w-12 h-12 rounded-xl bg-[#a45139] flex items-center justify-center animate-pulse mb-3 shadow-lg">
          <Building2 className="w-6 h-6 text-white" />
        </div>
        <div className="text-sm font-semibold tracking-wide text-slate-200">Restoring GIA_Arthwise Session...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <LoginPage
        activeCompany={activeCompany}
        onLoginSuccess={async (token, user) => {
          ApiClient.setToken(token);
          localStorage.setItem('gia_arthwise_user', JSON.stringify(user));
          setIsAuthenticated(true);
          setCurrentUser(user);
          setCurrentRole(user.role);
          setSelectedProposalId(null); // LAND ON HOME PAGE WITH LIST OF PROPOSALS
          await loadInitialData();
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Header
        activeCompany={activeCompany}
        currentRole={currentRole}
        userEmail={currentUser?.email}
        onRoleChange={handleInitiateRoleChange}
        unitMode={unitMode}
        onUnitModeChange={setUnitMode}
        onOpenAdmin={() => setShowAdminModal(true)}
        onOpenInstallApp={() => setShowInstallModal(true)}
        onLogout={handleLogout}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* If no proposal is selected, show Pipeline (Home Page) */}
        {!selectedProposal ? (
          <ProposalPipeline
            proposals={proposals}
            clients={clients}
            selectedProposalId={selectedProposalId}
            onSelectProposal={(id) => {
              setSelectedProposalId(id);
              setActiveTab('checklist');
            }}
            onCreateProposal={handleCreateProposal}
            onLoadSyntheticDemo={handleLoadSyntheticDemo}
            onRefresh={loadInitialData}
            unitMode={unitMode}
            onOpenWizard={(info) => setWizardProposal(info)}
          />
        ) : (
          <div className="space-y-5">
            {/* Proposal Workspace Top Bar */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSelectedProposalId(null)}
                  className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 hover:text-[#1b2632] transition-colors"
                  title="Return to Proposals List (Home)"
                >
                  <ArrowLeft className="w-5 h-5 text-[#a45139]" />
                </button>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-[#1b2632] text-base">{selectedProposal.proposal_code}</span>
                    <span className="px-2.5 py-0.5 rounded-full bg-[#1b2632]/10 text-[#1b2632] border border-[#1b2632]/20 text-xs font-semibold">
                      {formatProductType(selectedProposal.product_type)}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full border text-xs font-semibold ${formatProposalStatus(selectedProposal.status).color}`}>
                      {formatProposalStatus(selectedProposal.status).label}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 flex flex-wrap items-center gap-2">
                    <span>
                      Borrower: <strong>{selectedEntity?.legal_name || selectedClient?.primary_contact_name || 'Client Entity'}</strong> | Requested Limit:{' '}
                      <strong>{formatINR(selectedProposal.requested_amount, unitMode)}</strong> ({selectedProposal.tenure_months} Months @ {selectedProposal.target_rate}% p.a.)
                    </span>
                    <button
                      onClick={() => setShowEditRequirementsModal(true)}
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-semibold bg-[#faece7] hover:bg-[#f5d7cf] text-[#a45139] border border-[#f5d7cf] transition-all shadow-2xs cursor-pointer"
                      title="Modify Loan Product, Requested Amount, Tenure, or Rate"
                    >
                      <Sliders className="w-3 h-3" />
                      <span>Change Requirements</span>
                    </button>
                    <button
                      onClick={() => setWizardProposal({
                        id: selectedProposal.id,
                        code: selectedProposal.proposal_code,
                        clientName: selectedEntity?.legal_name || selectedClient?.primary_contact_name,
                        productType: selectedProposal.product_type,
                        requestedAmount: selectedProposal.requested_amount,
                      })}
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-semibold bg-[#faece7] hover:bg-[#f5d7cf] text-[#a45139] border border-[#f5d7cf] transition-all shadow-2xs cursor-pointer"
                      title="Launch Guided Document Upload Wizard (Financials, GST, ITR, Banking)"
                    >
                      <Sparkles className="w-3 h-3 text-[#a45139]" />
                      <span>Upload Wizard</span>
                    </button>
                  </p>
                </div>
              </div>

              {/* Workspace Navigation Tabs */}
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold border border-slate-200 overflow-x-auto">
                <button
                  onClick={() => setActiveTab('checklist')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                    activeTab === 'checklist' ? 'bg-[#1b2632] text-white shadow font-bold' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <FileCheck className={`w-3.5 h-3.5 ${activeTab === 'checklist' ? 'text-[#ebb9ab]' : 'text-brand-700'}`} />
                  <span>Primary Checklist</span>
                </button>

                <button
                  onClick={() => setActiveTab('extraction')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                    activeTab === 'extraction' ? 'bg-[#1b2632] text-white shadow font-bold' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <FileSearch className={`w-3.5 h-3.5 ${activeTab === 'extraction' ? 'text-[#ebb9ab]' : 'text-purple-700'}`} />
                  <span>Financials &amp; Extractions</span>
                  {extractedRecords.length > 0 && (
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-700 text-white font-mono">
                      {extractedRecords.length}
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setActiveTab('evaluation')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                    activeTab === 'evaluation' ? 'bg-[#1b2632] text-white shadow font-bold' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Calculator className={`w-3.5 h-3.5 ${activeTab === 'evaluation' ? 'text-[#ebb9ab]' : 'text-emerald-700'}`} />
                  <span>Financial Underwriting</span>
                </button>

                <button
                  onClick={() => setActiveTab('lenders')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                    activeTab === 'lenders' ? 'bg-[#1b2632] text-white shadow font-bold' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Landmark className={`w-3.5 h-3.5 ${activeTab === 'lenders' ? 'text-[#ebb9ab]' : 'text-amber-700'}`} />
                  <span>Lender Matrix</span>
                </button>

                <button
                  onClick={() => setActiveTab('cma')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                    activeTab === 'cma' ? 'bg-[#1b2632] text-white shadow font-bold' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <FileSpreadsheet className={`w-3.5 h-3.5 ${activeTab === 'cma' ? 'text-[#ebb9ab]' : 'text-blue-700'}`} />
                  <span>9-Yr CMA</span>
                </button>

                <button
                  onClick={() => setActiveTab('reports')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                    activeTab === 'reports' ? 'bg-[#1b2632] text-white shadow font-bold' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Download className={`w-3.5 h-3.5 ${activeTab === 'reports' ? 'text-[#ebb9ab]' : 'text-slate-700'}`} />
                  <span>Report Exports</span>
                </button>

                <button
                  onClick={() => setActiveTab('reviewer')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                    activeTab === 'reviewer' ? 'bg-[#1b2632] text-white shadow font-bold' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <UserCheck className={`w-3.5 h-3.5 ${activeTab === 'reviewer' ? 'text-[#ebb9ab]' : 'text-orange-700'}`} />
                  <span>Reviewer Queue</span>
                </button>
              </div>
            </div>

            {/* Tab Body */}
            <div>
              {activeTab === 'checklist' && (
                <ChecklistTab
                  proposalId={selectedProposal.id}
                  checklistItems={checklistItems}
                  onRefresh={() => loadProposalDetails(selectedProposal.id)}
                  onOpenWizard={() => setWizardProposal({
                    id: selectedProposal.id,
                    code: selectedProposal.proposal_code,
                    clientName: selectedEntity?.legal_name || selectedClient?.primary_contact_name,
                    productType: selectedProposal.product_type,
                    requestedAmount: selectedProposal.requested_amount,
                  })}
                />
              )}

              {activeTab === 'extraction' && (
                <ExtractionTab
                  proposalId={selectedProposal.id}
                  extractedRecords={extractedRecords}
                  onRefresh={() => loadProposalDetails(selectedProposal.id)}
                  unitMode={unitMode}
                />
              )}

              {activeTab === 'evaluation' && (
                <EvaluationTab
                  proposal={selectedProposal}
                  onRefresh={() => loadProposalDetails(selectedProposal.id)}
                  unitMode={unitMode}
                />
              )}

              {activeTab === 'lenders' && (
                <LenderMatrixTab
                  proposalId={selectedProposal.id}
                  unitMode={unitMode}
                />
              )}

              {activeTab === 'cma' && (
                <CmaWorkspaceTab
                  proposalId={selectedProposal.id}
                  unitMode={unitMode}
                />
              )}

              {activeTab === 'reports' && (
                <ReportsTab
                  proposal={selectedProposal}
                  client={selectedClient}
                  entity={selectedEntity}
                  unitMode={unitMode}
                />
              )}

              {activeTab === 'reviewer' && (
                <ReviewerTab
                  proposal={selectedProposal}
                  currentRole={currentRole}
                  onRefresh={() => loadInitialData()}
                />
              )}
            </div>
          </div>
        )}
      </main>

      {/* Bottom Footer Notice */}
      <footer className="bg-[#1b2632] text-slate-300 border-t border-[#2a3c4f] py-3 px-4 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[#ebb9ab] flex-shrink-0" />
            <span>
              <strong className="text-white">Preliminary Assessment Notice:</strong> All eligibility figures, ratios, and policy comparisons are strictly preliminary estimates for professional credit facilitator review. Never represent them as a bank sanction or guarantee.
            </span>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-slate-400 font-mono flex-shrink-0">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#1b2632] border border-slate-400 inline-block" /> #1b2632
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#a45139] inline-block" /> #a45139
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">{activeCompany?.brand_name || 'GIA_Arthwise'}</span>
          </div>
        </div>
      </footer>

      {/* Switch Role Profile Modal with Username & Password Authentication */}
      {roleSwitchTarget && (
        <SwitchRoleModal
          targetRole={roleSwitchTarget}
          currentRole={currentRole}
          onSuccess={handleRoleSwitchSuccess}
          onCancel={() => setRoleSwitchTarget(null)}
        />
      )}

      {/* Admin Integrations Modal */}
      {showAdminModal && (
        <AdminIntegrationsModal
          onClose={() => setShowAdminModal(false)}
          onCompanyChanged={loadActiveCompany}
        />
      )}

      {/* PWA App Installation Guidance Modal */}
      {showInstallModal && (
        <InstallAppModal
          onClose={() => setShowInstallModal(false)}
          deferredPrompt={deferredPrompt}
        />
      )}

      {/* Edit Loan Requirements Modal Dialog (Workspace) */}
      {showEditRequirementsModal && selectedProposal && (
        <EditRequirementsModal
          proposal={selectedProposal}
          borrowerName={selectedEntity?.legal_name || selectedClient?.primary_contact_name || 'Client Entity'}
          unitMode={unitMode}
          onClose={() => setShowEditRequirementsModal(false)}
          onSuccess={async () => {
            setShowEditRequirementsModal(false);
            await loadInitialData();
          }}
        />
      )}

      {/* Guided Sequential Document Upload Wizard */}
      {wizardProposal && (
        <SequentialUploadWizardModal
          proposalId={wizardProposal.id}
          proposalCode={wizardProposal.code}
          clientName={wizardProposal.clientName}
          productType={wizardProposal.productType}
          requestedAmount={wizardProposal.requestedAmount}
          isOpen={!!wizardProposal}
          onClose={() => setWizardProposal(null)}
          onComplete={async () => {
            setWizardProposal(null);
            if (selectedProposalId) {
              await loadProposalDetails(selectedProposalId);
            }
            await loadInitialData();
          }}
        />
      )}
    </div>
  );
};
