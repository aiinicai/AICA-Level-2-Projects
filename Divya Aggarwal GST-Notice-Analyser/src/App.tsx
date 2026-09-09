import { useState, useEffect } from 'react';
import {
  Client,
  NoticeCase,
  NoticeIssue,
  ReconciliationItem,
  DocumentItem,
  FirmSettings,
  ParsedFigure,
} from './types';
import {
  initDatabase,
  getSession,
  onAuthChange,
  signOut,
  getActiveFirmId,
  setActiveFirm,
  getMyMemberships,
  deleteAllFirmData,
  getAllClients,
  getAllCases,
  getIssuesForCase,
  getReconciliationsForCase,
  getDocumentsForCase,
  getFirmSettings,
  getPortalFigures,
  savePortalFigures,
  saveClient,
  saveCase,
  saveIssues,
  saveReconciliations,
  saveDocumentItems,
  deleteDocumentItem,
  saveFirmSettings,
} from './services/db';
import { isSupabaseConfigured } from './lib/supabase';
import { FEATURES } from './config';
import { analyzeNotice, AnalysisResponse } from './services/aiService';
import { buildDocumentsFromAnalysis, buildIntakeDiscussions } from './services/noticeArtifacts';
import { buildRequiredSchedules } from './services/reconciliationEngine';
import { addDiscussions } from './services/discussions';
import { AuthScreen, FirmPicker } from './components/AuthScreen';
import { Header } from './components/Header';
import { Sidebar, ActiveTab } from './components/Sidebar';
import { NoticeIntakeModal } from './components/NoticeIntakeModal';
import { AddClientModal } from './components/AddClientModal';
import { SettingsModal } from './components/SettingsModal';

import { DashboardView } from './pages/DashboardView';
import { NoticeSummaryView } from './pages/NoticeSummaryView';
import { FigureSourceView } from './pages/FigureSourceView';
import { ReconciliationView } from './pages/ReconciliationView';
import { DocumentTrackerView } from './pages/DocumentTrackerView';
import { ReplyGeneratorView } from './pages/ReplyGeneratorView';
import { DeadlinesView } from './pages/DeadlinesView';
import { SetupGuideView } from './pages/SetupGuideView';
import { ClientDiscussionView } from './pages/ClientDiscussionView';

const EMPTY_SETTINGS: FirmSettings = {
  caFirmName: '', caName: '', membershipNo: '',
  firmAddress: '', contactEmail: '', contactPhone: '', letterheadHeader: '',
};

type Phase = 'checking' | 'auth' | 'firm' | 'ready';

export function App() {
  const [phase, setPhase] = useState<Phase>('checking');
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard');
  const [firmName, setFirmName] = useState('');

  const [allClients, setAllClients] = useState<Client[]>([]);
  const [activeClient, setActiveClient] = useState<Client | null>(null);
  const [allCases, setAllCases] = useState<NoticeCase[]>([]);
  const [activeCase, setActiveCase] = useState<NoticeCase | null>(null);
  const [issues, setIssues] = useState<NoticeIssue[]>([]);
  const [reconciliations, setReconciliations] = useState<ReconciliationItem[]>([]);
  const [documentItems, setDocumentItems] = useState<DocumentItem[]>([]);
  const [portalFigures, setPortalFigures] = useState<ParsedFigure[]>([]);
  const [firmSettings, setFirmSettings] = useState<FirmSettings>(EMPTY_SETTINGS);

  const [intakeModalOpen, setIntakeModalOpen] = useState(false);
  const [addClientModalOpen, setAddClientModalOpen] = useState(false);
  const [addClientPrefill, setAddClientPrefill] = useState<{ legalName?: string; gstin?: string } | null>(null);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [onClientAddedCallback, setOnClientAddedCallback] = useState<((id: string) => void) | null>(null);

  const openAddClient = (
    prefill?: { legalName?: string; gstin?: string } | null,
    onAdded?: (id: string) => void,
  ) => {
    setAddClientPrefill(prefill || null);
    setOnClientAddedCallback(onAdded ? () => onAdded : null);
    setAddClientModalOpen(true);
  };

  const clearWorkspaceState = () => {
    setAllClients([]); setActiveClient(null);
    setAllCases([]); setActiveCase(null);
    setIssues([]); setReconciliations([]); setDocumentItems([]); setPortalFigures([]);
    setFirmSettings(EMPTY_SETTINGS);
  };

  // ── session / firm gate ───────────────────────────────────────────────────
  useEffect(() => {
    let mounted = true;
    (async () => {
      const session = await getSession();
      if (!mounted) return;
      if (!session) { setPhase('auth'); return; }
      await resolveFirmThenBoot();
    })();
    const unsub = onAuthChange((session) => {
      if (!session) { setActiveFirm(null); clearWorkspaceState(); setPhase('auth'); }
    });
    return () => { mounted = false; unsub(); };
  }, []);

  const resolveFirmThenBoot = async () => {
    try {
      const memberships = await getMyMemberships();
      let fid = getActiveFirmId();
      if (!fid || !memberships.some((m) => m.firmId === fid)) {
        if (memberships.length === 1) { setActiveFirm(memberships[0].firmId); fid = memberships[0].firmId; }
        else { setPhase('firm'); return; }
      }
      setFirmName(memberships.find((m) => m.firmId === fid)?.firmName ?? '');
      await boot();
    } catch {
      setPhase('firm');
    }
  };

  const boot = async () => {
    setPhase('ready');
    setIsLoading(true);
    try {
      await initDatabase();
      const [clients, cases, settings] = await Promise.all([
        getAllClients(), getAllCases(), getFirmSettings(),
      ]);
      setAllClients(clients);
      setAllCases(cases);
      setFirmSettings(settings);
      if (clients.length > 0) {
        const firstClient = clients[0];
        setActiveClient(firstClient);
        const clientCases = cases.filter((c) => c.clientId === firstClient.id);
        if (clientCases.length > 0) {
          setActiveCase(clientCases[0]);
          await loadCaseDetails(clientCases[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load workspace:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    clearWorkspaceState();
    setPhase('auth');
  };

  // ── data ──────────────────────────────────────────────────────────────────
  const loadCaseDetails = async (caseId: string) => {
    const [caseIssues, caseRecons, caseDocs, figs] = await Promise.all([
      getIssuesForCase(caseId),
      getReconciliationsForCase(caseId),
      getDocumentsForCase(caseId),
      getPortalFigures(caseId),
    ]);
    setIssues(caseIssues);
    setReconciliations(caseRecons);
    setDocumentItems(caseDocs);
    setPortalFigures(figs?.figures || []);
  };

  const handleSelectClient = (clientId: string) => {
    const selected = allClients.find((c) => c.id === clientId) || null;
    setActiveClient(selected);
    const clientCases = allCases.filter((c) => c.clientId === clientId);
    if (clientCases.length > 0) {
      setActiveCase(clientCases[0]);
      loadCaseDetails(clientCases[0].id);
    } else {
      setActiveCase(null);
      setIssues([]); setReconciliations([]); setDocumentItems([]); setPortalFigures([]);
    }
  };

  const handleSelectCase = async (caseId: string) => {
    const selected = allCases.find((c) => c.id === caseId) || null;
    setActiveCase(selected);
    if (selected) {
      setActiveClient(allClients.find((cl) => cl.id === selected.clientId) || null);
      await loadCaseDetails(selected.id);
    }
  };

  const handleSaveClient = async (client: Client) => {
    await saveClient(client);
    setAllClients(await getAllClients());
    setActiveClient(client);
    setActiveCase(null);
    setIssues([]); setReconciliations([]); setDocumentItems([]); setPortalFigures([]);
    if (onClientAddedCallback) {
      onClientAddedCallback(client.id);
      setOnClientAddedCallback(null);
    }
  };

  const handleUpdateCase = async (updatedCase: NoticeCase) => {
    await saveCase(updatedCase);
    setAllCases(await getAllCases());
    setActiveCase(updatedCase);
  };

  const handleSaveReconciliations = async (newRecons: ReconciliationItem[]) => {
    await saveReconciliations(newRecons);
    if (activeCase) setReconciliations(await getReconciliationsForCase(activeCase.id));
  };

  const handleSavePortalFigures = async (figs: ParsedFigure[]) => {
    setPortalFigures(figs);
    if (activeCase && activeCase.id !== '__temp__' && !activeCase.id.startsWith('temp_')) {
      await savePortalFigures({ caseId: activeCase.id, figures: figs, updatedAt: new Date().toISOString() });
    }
  };

  const handleSaveDocumentItems = async (newItems: DocumentItem[]) => {
    await saveDocumentItems(newItems);
    if (activeCase) setDocumentItems(await getDocumentsForCase(activeCase.id));
  };

  const handleDeleteDocumentItem = async (id: string) => {
    await deleteDocumentItem(id);
    if (activeCase) setDocumentItems(await getDocumentsForCase(activeCase.id));
  };

  const handleSaveFirmSettings = async (newSettings: FirmSettings) => {
    await saveFirmSettings(newSettings);
    setFirmSettings(newSettings);
  };

  const handleResetDb = async () => {
    await deleteAllFirmData();
    clearWorkspaceStateKeepFirm();
    setFirmSettings(EMPTY_SETTINGS);
  };
  const clearWorkspaceStateKeepFirm = () => {
    setAllClients([]); setActiveClient(null);
    setAllCases([]); setActiveCase(null);
    setIssues([]); setReconciliations([]); setDocumentItems([]); setPortalFigures([]);
  };

  const handleSaveAnalysis = async (
    clientId: string,
    analysis: AnalysisResponse,
    pdfDataUrl?: string,
    pdfFileName?: string,
  ) => {
    const newCaseId = 'case_' + Date.now();
    const newCase: NoticeCase = {
      ...analysis.noticeCase,
      id: newCaseId,
      clientId,
      pdfDataUrl,
      pdfFileName,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const newIssues: NoticeIssue[] = analysis.issues.map((iss, idx) => ({
      ...iss,
      id: `issue_${newCaseId}_${idx + 1}`,
      caseId: newCaseId,
    }));

    const newRecons: ReconciliationItem[] = buildRequiredSchedules(newIssues, newCase).map((r) => ({
      ...r,
      caseId: newCaseId,
    }));

    const newDocs: DocumentItem[] = buildDocumentsFromAnalysis(newCaseId, analysis);

    await saveCase(newCase);
    await saveIssues(newIssues);
    await saveReconciliations(newRecons);
    await saveDocumentItems(newDocs);
    await savePortalFigures({ caseId: newCaseId, figures: [], updatedAt: new Date().toISOString() });
    await addDiscussions(buildIntakeDiscussions(newCaseId, analysis));

    const [cases, clients] = await Promise.all([getAllCases(), getAllClients()]);
    setAllCases(cases);
    setAllClients(clients);
    setActiveClient(clients.find((c) => c.id === clientId) || null);
    setActiveCase(newCase);
    setIssues(newIssues);
    setReconciliations(newRecons);
    setDocumentItems(newDocs);
    setPortalFigures([]);
    setActiveTab('split_view');
  };

  const applyAnalysisPreview = (
    analysis: AnalysisResponse,
    pdfDataUrl?: string,
    pdfFileName?: string,
  ) => {
    const tempCaseId = 'temp_' + Date.now();
    const tempCase: NoticeCase = {
      ...analysis.noticeCase,
      id: tempCaseId,
      clientId: '__temp__',
      pdfDataUrl,
      pdfFileName,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    const tempIssues: NoticeIssue[] = analysis.issues.map((iss, idx) => ({
      ...iss,
      id: `issue_${tempCaseId}_${idx + 1}`,
      caseId: tempCaseId,
    }));
    const tempRecons: ReconciliationItem[] = buildRequiredSchedules(tempIssues, tempCase).map((r) => ({
      ...r,
      caseId: tempCaseId,
    }));
    setActiveCase(tempCase);
    setIssues(tempIssues);
    setReconciliations(tempRecons);
    setDocumentItems(buildDocumentsFromAnalysis(tempCaseId, analysis));
    setPortalFigures([]);
    setActiveTab('split_view');
  };

  const handleAnalyzeOnly = async (
    text: string,
    formTypeHint: string,
    pdfDataUrl?: string,
    _pdfFileName?: string,
    forceLocal = false,
  ): Promise<AnalysisResponse> => {
    const analysis = await analyzeNotice(text, formTypeHint, pdfDataUrl, forceLocal);
    applyAnalysisPreview(analysis, pdfDataUrl, _pdfFileName);
    return analysis;
  };

  const handleManualAnalysis = (
    analysis: AnalysisResponse,
    pdfDataUrl?: string,
    pdfFileName?: string,
  ) => {
    applyAnalysisPreview(analysis, pdfDataUrl, pdfFileName);
  };

  // ── render gates ──────────────────────────────────────────────────────────
  if (!isSupabaseConfigured) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 bg-[#F8FAFC] p-8 text-center">
        <div className="text-sm font-bold text-slate-900">Backend not configured</div>
        <div className="max-w-md text-xs text-slate-500">
          Set <code className="font-mono">VITE_SUPABASE_URL</code> and{' '}
          <code className="font-mono">VITE_SUPABASE_ANON_KEY</code> — see <strong>SUPABASE-SETUP.md</strong>.
        </div>
      </div>
    );
  }

  if (phase === 'checking') {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-[#F8FAFC] text-gray-700">
        <div className="mb-4 h-10 w-10 animate-spin rounded-full border-4 border-[#4338CA] border-t-transparent" />
        <div className="text-sm font-semibold text-gray-900">Loading…</div>
      </div>
    );
  }
  if (phase === 'auth') return <AuthScreen onSignedIn={resolveFirmThenBoot} />;
  if (phase === 'firm') return <FirmPicker onReady={resolveFirmThenBoot} />;

  if (isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-[#F8FAFC] text-gray-700 select-none">
        <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-[#4338CA] border-t-transparent" />
        <div className="text-sm font-bold text-gray-900">Loading your workspace…</div>
        <div className="mt-1 text-xs text-gray-500">{firmName}</div>
      </div>
    );
  }

  const pendingDocs = documentItems.filter((d) => d.status === 'Pending' || d.status === 'Partly Received').length;
  const today = new Date();
  const thirtyDaysFromNow = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
  const urgentDeadlines = allCases.filter((c) => {
    const dl = new Date(c.replyDeadline);
    return !isNaN(dl.getTime()) && dl >= today && dl <= thirtyDaysFromNow;
  }).length;

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-[#F8FAFC] select-none">
      <Header
        activeClient={activeClient}
        allClients={allClients}
        activeCase={activeCase}
        allCases={allCases}
        firmName={firmName}
        onSelectClient={handleSelectClient}
        onSelectCase={handleSelectCase}
        onOpenIntake={() => setIntakeModalOpen(true)}
        onOpenSettings={() => setSettingsModalOpen(true)}
        onOpenAddClient={() => openAddClient()}
        onSignOut={handleSignOut}
      />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          caseCount={allCases.filter((c) => c.clientId === activeClient?.id).length}
          issueCount={issues.length}
          pendingDocCount={pendingDocs}
          urgentDeadlineCount={urgentDeadlines}
        />

        <main className="flex-1 overflow-hidden">
          {activeTab === 'dashboard' && (
            <DashboardView
              activeClient={activeClient}
              activeCase={activeCase}
              allClients={allClients}
              allCases={allCases}
              onSelectCase={handleSelectCase}
              onOpenIntake={() => setIntakeModalOpen(true)}
              onOpenAddClient={() => openAddClient()}
              onNavigateToTab={setActiveTab}
            />
          )}

          {activeTab === 'split_view' && (
            <NoticeSummaryView
              activeCase={activeCase}
              issues={issues}
              onUpdateCase={handleUpdateCase}
              onNavigateToTab={setActiveTab}
            />
          )}

          {FEATURES.figureSource && activeTab === 'figure_source' && (
            <FigureSourceView
              activeCase={activeCase}
              issues={issues}
              reconciliations={reconciliations}
              onNavigateToTracker={() => setActiveTab('tracker')}
              onNavigateToReconciliation={() => setActiveTab('reconciliation')}
            />
          )}

          {FEATURES.reconciliation && activeTab === 'reconciliation' && (
            <ReconciliationView
              activeClient={activeClient}
              activeCase={activeCase}
              issues={issues}
              documentItems={documentItems}
              reconciliations={reconciliations}
              portalFigures={portalFigures}
              onSaveReconciliations={handleSaveReconciliations}
              onSavePortalFigures={handleSavePortalFigures}
            />
          )}

          {activeTab === 'tracker' && (
            <DocumentTrackerView
              activeClient={activeClient}
              activeCase={activeCase}
              documentItems={documentItems}
              onSaveItems={handleSaveDocumentItems}
              onDeleteItem={handleDeleteDocumentItem}
            />
          )}

          {activeTab === 'reply_gen' && (
            <ReplyGeneratorView
              activeClient={activeClient}
              activeCase={activeCase}
              issues={issues}
              reconciliations={reconciliations}
              documentItems={documentItems}
              firmSettings={firmSettings}
            />
          )}

          {activeTab === 'deadlines' && (
            <DeadlinesView
              allCases={allCases}
              allClients={allClients}
              onSelectCase={handleSelectCase}
              onNavigateToTab={setActiveTab}
            />
          )}

          {activeTab === 'client_discussion' && (
            <ClientDiscussionView activeClient={activeClient} activeCase={activeCase} />
          )}

          {activeTab === 'setup_guide' && <SetupGuideView />}
        </main>
      </div>

      <NoticeIntakeModal
        isOpen={intakeModalOpen}
        onClose={() => setIntakeModalOpen(false)}
        allClients={allClients}
        selectedClientId={activeClient?.id || ''}
        onAnalyzeOnly={handleAnalyzeOnly}
        onManualAnalysis={handleManualAnalysis}
        onSaveAnalysis={handleSaveAnalysis}
        onOpenAddClient={(onAdded, prefill) => openAddClient(prefill, onAdded)}
      />

      <AddClientModal
        isOpen={addClientModalOpen}
        onClose={() => setAddClientModalOpen(false)}
        onSave={handleSaveClient}
        prefill={addClientPrefill}
      />

      <SettingsModal
        isOpen={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        settings={firmSettings}
        onSave={handleSaveFirmSettings}
        onResetDb={handleResetDb}
      />
    </div>
  );
}

export default App;
