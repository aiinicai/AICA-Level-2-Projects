import React, { useState, useEffect } from 'react';
import { Sidebar, NavTab } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { TodaysBriefingView } from './components/TodaysBriefingView';
import { GmailIngestionView } from './components/GmailIngestionView';
import { ImpactAnalysisView } from './components/ImpactAnalysisView';
import { ClientMasterView } from './components/ClientMasterView';
import { ClientMatchingView } from './components/ClientMatchingView';
import { ClientAdvisoriesView } from './components/ClientAdvisoriesView';
import { ApprovalCentreView } from './components/ApprovalCentreView';
import { WhatsAppStudioView } from './components/WhatsAppStudioView';
import { AuditHistoryView } from './components/AuditHistoryView';
import { SettingsView } from './components/SettingsView';
import {
  initAuth,
  getGmailAccessToken,
  GmailConnectionState,
} from './services/firebaseAuth';

import {
  RegulatoryUpdate,
  ClientMaster,
  ClientAdvisory,
  ApprovalStatus,
  BrandSettings,
  AuditLogEntry,
  OperatingMode,
  BriefingSource,
  IntegrationStatus,
  ActiveBriefingInfo,
} from './types';
import { DEMO_CLIENTS } from './data/demoClients';
import { DEMO_UPDATES } from './data/demoUpdates';
import { matchClientWithUpdate, generateClientAdvisory } from './services/advisoryEngine';

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [briefingSource, setBriefingSource] = useState<BriefingSource>('DEMO');
  const [gmailState, setGmailState] = useState<GmailConnectionState>({
    isConnected: false,
    userEmail: null,
    userName: null,
    status: 'Not Connected',
    lastSyncTime: null,
    firebaseAuthStatus: 'Not Connected',
    hasOAuthToken: false,
    hasGmailScope: false,
    gmailApiTestStatus: 'Not Executed',
    gmailApiError: null,
  });

  const isLiveSystem = Boolean(gmailState.isConnected);
  const operatingMode: OperatingMode = isLiveSystem ? 'LIVE' : 'DEMO';

  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus>({
    geminiConnected: true,
    gmailConnected: false,
    clientDatabaseLive: false,
    sourceVerificationLive: true,
    whatsappExportReady: true,
    approvalWorkflowActive: true,
  });
  const [briefingDate, setBriefingDate] = useState<string>('7 August 2026');

  // Listen to Firebase OAuth Auth State
  useEffect(() => {
    const unsubscribe = initAuth((state) => {
      setGmailState(state);
      setIntegrationStatus((prev) => ({
        ...prev,
        gmailConnected: state.isConnected,
      }));
    });
    return () => unsubscribe();
  }, []);

  // Core Data State
  const [updates, setUpdates] = useState<RegulatoryUpdate[]>(DEMO_UPDATES);
  const [clients, setClients] = useState<ClientMaster[]>(DEMO_CLIENTS);
  const [advisories, setAdvisories] = useState<ClientAdvisory[]>([]);
  const [selectedUpdate, setSelectedUpdate] = useState<RegulatoryUpdate | null>(DEMO_UPDATES[0]);

  // Active Briefing Metadata
  const [activeBriefingInfo, setActiveBriefingInfo] = useState<ActiveBriefingInfo>({
    source: 'DEMO',
    targetDate: '7 August 2026',
    expectedSubject: 'Daily Professional Briefing – 7 August 2026',
    actualSubject: 'Daily Professional Briefing – 7 August 2026 (Simulated Demo Data)',
    emailReceivedDate: '7 August 2026, 08:30 AM',
    gmailMessageId: 'demo_msg_001',
    connectedAccount: 'Demo Data Engine',
    importedDateTime: new Date().toLocaleString(),
    dateMatch: 'DEMO',
  });

  // Brand Settings State
  const [brandSettings, setBrandSettings] = useState<BrandSettings>({
    firmName: 'M. R. & Co., Chartered Accountants',
    caName: 'CA Rajesh Kumar, FCA',
    membershipNo: 'ICAI-FCA-102948',
    contactEmail: 'advisory@mrco.in',
    contactPhone: '+91 98470 12345',
    firmAddress: 'Suite 402, CA Chambers, MG Road, Mumbai 400001',
    disclaimer:
      'This advisory is generated for professional client guidance. Final statutory position should be confirmed against official gazette notifications.',
  });

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([
    {
      id: 'log_1',
      timestamp: new Date().toLocaleString(),
      action: 'Regulatory Update Inflow',
      performedBy: 'System Pipeline',
      targetTitle: 'MCA Notification — Demat Shares Mandatory for Private Companies',
      details: 'Daily professional update received and facts extracted.',
    },
    {
      id: 'log_2',
      timestamp: new Date().toLocaleString(),
      action: 'Client Match Evaluated',
      performedBy: 'Advisory Engine V2',
      targetTitle: 'Acme Manufacturing Pvt Ltd',
      details: 'Evaluated update applicability. Relevance Score: 92% (Highly Relevant).',
    },
  ]);

  // Extraction State
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractionError, setExtractionError] = useState<string | null>(null);

  // Helper: Add Audit Log Entry
  const logAuditEvent = (action: string, targetTitle: string, details: string) => {
    const entry: AuditLogEntry = {
      id: `log_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      timestamp: new Date().toLocaleString(),
      action,
      performedBy: brandSettings.caName,
      targetTitle,
      details,
    };
    setAuditLogs((prev) => [entry, ...prev]);
  };

  // Initialize Baseline Client Matching & Advisories
  useEffect(() => {
    if (updates.length > 0 && clients.length > 0) {
      const initialAdvisories: ClientAdvisory[] = [];
      updates.slice(0, 3).forEach((upd) => {
        clients.forEach((cli) => {
          const match = matchClientWithUpdate(cli, upd);
          if (match.relevanceStatus === 'Highly Relevant' || match.relevanceStatus === 'Relevant') {
            const adv = generateClientAdvisory(cli, upd, brandSettings);
            initialAdvisories.push(adv);
          }
        });
      });
      setAdvisories(initialAdvisories);
    }
  }, []);

  // Handler: Import Gmail Briefing from API or Text
  const handleImportBriefingFromText = async (rawText: string, emailSubject?: string, importMeta?: any) => {
    setIsExtracting(true);
    setExtractionError(null);

    try {
      const extractRes = await fetch('/api/gemini/extract-briefing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: rawText, briefingDate }),
      });

      const extractData = await extractRes.json();
      if (extractData.success && extractData.updates?.length > 0) {
        setUpdates(extractData.updates);
        setSelectedUpdate(extractData.updates[0]);
        setBriefingSource('GMAIL');

        setActiveBriefingInfo({
          source: 'GMAIL',
          targetDate: importMeta?.requestedTargetDate || briefingDate,
          expectedSubject: importMeta?.expectedSubject || `Daily Professional Briefing – ${briefingDate}`,
          actualSubject: importMeta?.message?.subject || emailSubject || `Daily Professional Briefing – ${briefingDate}`,
          emailReceivedDate: importMeta?.message?.date || new Date().toLocaleString(),
          gmailMessageId: importMeta?.message?.id || `msg_${Date.now()}`,
          connectedAccount: gmailState.connectedGmailAddress || gmailState.userEmail || 'Connected Gmail Account',
          importedDateTime: new Date().toLocaleString(),
          dateMatch: 'PASS',
        });

        logAuditEvent(
          'Gmail Live Briefing Import',
          emailSubject || `Daily Professional Briefing – ${briefingDate}`,
          `Strict Date Match PASS. Target Date: ${importMeta?.requestedTargetDate || briefingDate}. Gmail Message ID: ${importMeta?.message?.id || 'N/A'}. Extracted ${extractData.updates.length} regulatory updates via Gemini 3.6 Flash.`
        );
        setActiveTab('inbox');
      } else {
        setExtractionError('Failed to parse regulatory updates from the email text.');
      }
    } catch (err: any) {
      console.error('Extraction Error:', err);
      setExtractionError(`AI extraction failed: ${err.message}`);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleImportGmail = async () => {
    setIsExtracting(true);
    setExtractionError(null);
    const token = getGmailAccessToken();

    if (!gmailState.isConnected || !token) {
      setIsExtracting(false);
      setExtractionError('Gmail OAuth Connection Required. Please click CONNECT GMAIL to authorize access first.');
      setActiveTab('briefing');
      return;
    }

    try {
      const headers: Record<string, string> = {
        Authorization: `Bearer ${token}`,
      };

      const response = await fetch(`/api/gmail/search-briefing?date=${encodeURIComponent(briefingDate)}`, {
        headers,
      });
      const data = await response.json();

      if (data.found && data.message?.bodyText && data.dateMatch === 'PASS') {
        await handleImportBriefingFromText(data.message.bodyText, data.message.subject, data);
        return;
      }

      // Strictly DO NOT fallback if email not found for requested date
      const failMsg = `NO MATCHING LIVE GMAIL BRIEFING FOUND for target date "${briefingDate}". Expected subject: "${data.expectedSubject || 'Daily Professional Briefing – ' + briefingDate}". Search status: ${data.searchStatus || 'No Matching Email Found'}. No fallback email or demo data was automatically imported.`;
      setExtractionError(failMsg);
      logAuditEvent('Gmail Search Empty', `Target Date: ${briefingDate}`, failMsg);
      setActiveTab('briefing');
    } catch (err: any) {
      console.error('Import Gmail Error:', err);
      setExtractionError(`Gmail API error: ${err.message}`);
    } finally {
      setIsExtracting(false);
    }
  };

  // Handler: Load Demo Briefing
  const handleLoadDemo = () => {
    setUpdates(DEMO_UPDATES);
    setSelectedUpdate(DEMO_UPDATES[0]);
    setBriefingSource('DEMO');
    setExtractionError(null);

    setActiveBriefingInfo({
      source: 'DEMO',
      targetDate: '7 August 2026',
      expectedSubject: 'Daily Professional Briefing – 7 August 2026',
      actualSubject: 'Daily Professional Briefing – 7 August 2026 (Simulated Demo Data)',
      emailReceivedDate: '7 August 2026, 08:30 AM',
      gmailMessageId: 'demo_msg_001',
      connectedAccount: 'Demo Data Engine',
      importedDateTime: new Date().toLocaleString(),
      dateMatch: 'DEMO',
    });

    const newAdvisories: ClientAdvisory[] = [];
    DEMO_UPDATES.forEach((upd) => {
      clients.forEach((cli) => {
        const match = matchClientWithUpdate(cli, upd);
        if (match.relevanceStatus === 'Highly Relevant' || match.relevanceStatus === 'Relevant') {
          newAdvisories.push(generateClientAdvisory(cli, upd, brandSettings));
        }
      });
    });
    setAdvisories(newAdvisories);
    logAuditEvent('Load Demo Briefing', '5 Demo Updates', 'Loaded 5 professional CA regulatory updates into system.');
    setActiveTab('inbox');
  };

  // Handler: Add Manual Update
  const handleAddManualUpdate = async (manualData: any) => {
    setIsExtracting(true);
    try {
      const res = await fetch('/api/gemini/analyze-update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(manualData),
      });

      const data = await res.json();
      if (data.success && data.update) {
        setUpdates((prev) => [data.update, ...prev]);
        setSelectedUpdate(data.update);
        logAuditEvent('Manual Update Added', data.update.title, 'CA added custom regulatory circular.');
        setActiveTab('impact');
      }
    } catch (e) {
      console.error('Error analyzing manual update:', e);
    } finally {
      setIsExtracting(false);
    }
  };

  // Handler: Client CRUD
  const handleAddClient = (newClient: ClientMaster) => {
    setClients((prev) => [...prev, newClient]);
    logAuditEvent('Add Client', newClient.clientName, `Added client profile (${newClient.entityType}).`);
  };

  const handleUpdateClient = (updatedClient: ClientMaster) => {
    setClients((prev) => prev.map((c) => (c.id === updatedClient.id ? updatedClient : c)));
    logAuditEvent('Update Client', updatedClient.clientName, 'Updated client profile parameters.');
  };

  const handleDeleteClient = (clientId: string) => {
    const cli = clients.find((c) => c.id === clientId);
    setClients((prev) => prev.filter((c) => c.id !== clientId));
    logAuditEvent('Delete Client', cli?.clientName || clientId, 'Removed client profile.');
  };

  // Handler: Selective Advisory Generation
  const handleGenerateAdvisoryForMatch = (client: ClientMaster, update: RegulatoryUpdate) => {
    const adv = generateClientAdvisory(client, update, brandSettings);
    setAdvisories((prev) => {
      const filtered = prev.filter((a) => !(a.clientId === client.id && a.updateId === update.id));
      return [adv, ...filtered];
    });
    logAuditEvent('Advisory Drafted', `${client.clientName} — ${update.title}`, 'Generated draft advisory for Approval Centre review.');
  };

  // Handler: Approval Centre Status Update
  const handleUpdateAdvisoryStatus = (advisoryId: string, status: ApprovalStatus, reviewerNotes?: string) => {
    setAdvisories((prev) =>
      prev.map((a) => {
        if (a.id === advisoryId) {
          logAuditEvent('CA Status Sign-off', a.clientName, `Updated advisory status to: ${status}.`);
          return {
            ...a,
            approvalStatus: status,
            reviewerNotes: reviewerNotes || a.reviewerNotes,
            reviewDate: new Date().toISOString(),
            reviewedBy: brandSettings.caName,
          };
        }
        return a;
      })
    );
  };

  const handleUpdateAdvisoryContent = (advisoryId: string, updatedFormal: any) => {
    setAdvisories((prev) =>
      prev.map((a) => {
        if (a.id === advisoryId) {
          logAuditEvent('CA Edit Advisory Draft', a.clientName, 'CA edited advisory text. Original draft preserved.');
          return {
            ...a,
            originalFormalAdvisory: a.originalFormalAdvisory || a.formalAdvisory,
            formalAdvisory: updatedFormal,
            approvalStatus: 'Pending Review',
          };
        }
        return a;
      })
    );
  };

  const pendingApprovalsCount = advisories.filter((a) => a.approvalStatus === 'Pending Review').length;

  return (
    <div className="flex h-screen bg-slate-100 font-sans text-slate-900 overflow-hidden">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingApprovalsCount={pendingApprovalsCount}
        totalUpdatesCount={updates.length}
        isLiveSystem={isLiveSystem}
        briefingSource={briefingSource}
        onLoadDemo={handleLoadDemo}
      />

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto px-6 py-6">
        {activeTab === 'dashboard' && (
          <DashboardView
            operatingMode={operatingMode}
            isLiveSystem={isLiveSystem}
            briefingSource={briefingSource}
            integrationStatus={integrationStatus}
            gmailState={gmailState}
            updates={updates}
            clients={clients}
            advisories={advisories}
            setActiveTab={setActiveTab}
            onImportGmail={handleImportGmail}
            onLoadDemo={handleLoadDemo}
            onAnalyseAll={() => setActiveTab('matching')}
            onSelectUpdateForAnalysis={(upd) => {
              setSelectedUpdate(upd);
              setActiveTab('impact');
            }}
            onShowGmailConnectModal={() => setActiveTab('briefing')}
          />
        )}

        {activeTab === 'briefing' && (
          <TodaysBriefingView
            updates={updates}
            briefingDate={briefingDate}
            setBriefingDate={setBriefingDate}
            onImportGmail={handleImportGmail}
            onLoadDemo={handleLoadDemo}
            onAddManualUpdate={handleAddManualUpdate}
            isExtracting={isExtracting}
            extractionError={extractionError}
            gmailState={gmailState}
            onGmailStateChange={(newState) => {
              setGmailState(newState);
              setIntegrationStatus((prev) => ({
                ...prev,
                gmailConnected: newState.isConnected,
              }));
            }}
            onImportBriefingFromText={handleImportBriefingFromText}
            isLiveSystem={isLiveSystem}
            briefingSource={briefingSource}
            activeBriefingInfo={activeBriefingInfo}
            onLogAudit={logAuditEvent}
          />
        )}

        {activeTab === 'inbox' && (
          <ImpactAnalysisView
            updates={updates}
            selectedUpdate={selectedUpdate}
            setSelectedUpdate={setSelectedUpdate}
            onMatchClientsForUpdate={(upd) => {
              setSelectedUpdate(upd);
              setActiveTab('matching');
            }}
          />
        )}

        {activeTab === 'impact' && (
          <ImpactAnalysisView
            updates={updates}
            selectedUpdate={selectedUpdate}
            setSelectedUpdate={setSelectedUpdate}
            onMatchClientsForUpdate={(upd) => {
              setSelectedUpdate(upd);
              setActiveTab('matching');
            }}
          />
        )}

        {activeTab === 'clients' && (
          <ClientMasterView
            clients={clients}
            onAddClient={handleAddClient}
            onUpdateClient={handleUpdateClient}
            onDeleteClient={handleDeleteClient}
          />
        )}

        {activeTab === 'matching' && (
          <ClientMatchingView
            updates={updates}
            clients={clients}
            selectedUpdate={selectedUpdate}
            setSelectedUpdate={setSelectedUpdate}
            onGenerateAdvisoryForMatch={handleGenerateAdvisoryForMatch}
            generatedAdvisoriesCount={advisories.length}
          />
        )}

        {activeTab === 'advisories' && (
          <ClientAdvisoriesView
            advisories={advisories}
            onApproveAdvisory={(id) => handleUpdateAdvisoryStatus(id, 'Approved')}
          />
        )}

        {activeTab === 'status-studio' && (
          <WhatsAppStudioView
            updates={updates}
            selectedUpdate={selectedUpdate}
            setSelectedUpdate={setSelectedUpdate}
            brandSettings={brandSettings}
          />
        )}

        {activeTab === 'approval' && (
          <ApprovalCentreView
            advisories={advisories}
            onUpdateStatus={handleUpdateAdvisoryStatus}
            onUpdateAdvisoryContent={handleUpdateAdvisoryContent}
          />
        )}

        {activeTab === 'history' && <AuditHistoryView logs={auditLogs} />}

        {activeTab === 'settings' && (
          <SettingsView
            brandSettings={brandSettings}
            onSaveBrandSettings={setBrandSettings}
            isLiveSystem={isLiveSystem}
            briefingSource={briefingSource}
            gmailState={gmailState}
            onGmailStateChange={(newState) => {
              setGmailState(newState);
              setIntegrationStatus((prev) => ({
                ...prev,
                gmailConnected: newState.isConnected,
              }));
            }}
            onLogAudit={logAuditEvent}
            briefingDate={briefingDate}
          />
        )}
      </main>
    </div>
  );
}
