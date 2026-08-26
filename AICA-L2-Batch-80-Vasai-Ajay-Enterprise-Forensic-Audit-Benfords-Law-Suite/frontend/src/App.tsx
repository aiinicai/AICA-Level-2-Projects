import React, { useState } from 'react';
import { Header } from './components/Header';
import { DisclaimerConsentModal } from './components/DisclaimerConsentModal';
import { DataIngestionView } from './components/DataIngestionView';
import { DPDPVaultView } from './components/DPDPVaultView';
import { BenfordWorkbenchView } from './components/BenfordWorkbenchView';
import { ForensicScannerView } from './components/ForensicScannerView';
import { AuditLedgerView } from './components/AuditLedgerView';
import { ExecutiveReportView } from './components/ExecutiveReportView';
import { ErrorBoundary } from './components/ErrorBoundary';
import { IngestionResult, BenfordSuiteResponse, ForensicTestsResponse } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('ingest');
  const [isConsentModalOpen, setIsConsentModalOpen] = useState<boolean>(true);
  const [consentGranted, setConsentGranted] = useState<boolean>(false);
  const [consentToken, setConsentToken] = useState<string>('');
  const [auditorName, setAuditorName] = useState<string>('Senior Forensic Auditor');
  const [organizationFiduciary, setOrganizationFiduciary] = useState<string>('Enterprise Audit & Risk Council');
  
  const [ingestionResult, setIngestionResult] = useState<IngestionResult | null>(null);
  const [benfordData, setBenfordData] = useState<BenfordSuiteResponse | null>(null);
  const [forensicsData, setForensicsData] = useState<ForensicTestsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // 1. Consent Declaration Handler
  const handleAcceptConsent = async (data: {
    auditorName: string;
    organizationFiduciary: string;
    auditPurpose: string;
  }) => {
    const res = await fetch('/api/consent/declare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        auditor_name: data.auditorName,
        organization_fiduciary: data.organizationFiduciary,
        audit_purpose: data.auditPurpose,
        disclaimer_acknowledged: true,
        dpdp_mandate_acknowledged: true
      })
    });
    const result = await res.json();
    if (!res.ok || !result.success) {
      throw new Error(result.detail || 'Consent declaration rejected.');
    }
    setAuditorName(data.auditorName);
    setOrganizationFiduciary(data.organizationFiduciary);
    setConsentToken(result.consent_token);
    setConsentGranted(true);
  };

  // 2. File Upload Handler
  const handleFileUpload = async (file: File) => {
    if (!consentGranted) {
      setIsConsentModalOpen(true);
      return;
    }
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('consent_token', consentToken);

      const res = await fetch('/api/ingest/upload', {
        method: 'POST',
        body: formData
      });
      const data: IngestionResult = await res.json();
      setIngestionResult(data);
      if (data.success && data.column_mapping && data.column_mapping.amount) {
        triggerFullAnalysis(data.column_mapping.amount, data.column_mapping);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  // 3. Path Ingestion Handler
  const handlePathUpload = async (filePath: string) => {
    if (!consentGranted) {
      setIsConsentModalOpen(true);
      return;
    }
    setIsLoading(true);
    try {
      const res = await fetch('/api/ingest/path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: filePath,
          consent_token: consentToken
        })
      });
      const data: IngestionResult = await res.json();
      setIngestionResult(data);
      if (data.success && data.column_mapping && data.column_mapping.amount) {
        triggerFullAnalysis(data.column_mapping.amount, data.column_mapping);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  // 4. Update Column Mapping
  const handleUpdateColumnMapping = (mapping: Record<string, string>) => {
    if (ingestionResult) {
      const updated = { ...ingestionResult, column_mapping: mapping };
      setIngestionResult(updated);
      if (mapping.amount) {
        triggerFullAnalysis(mapping.amount, mapping);
      }
    }
  };

  // 5. Trigger DPDP Sanitization
  const handleApplySanitization = async (mode: string) => {
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('action_mode', mode);
      formData.append('consent_token', consentToken);

      await fetch('/api/dpdp/sanitize', {
        method: 'POST',
        body: formData
      });

      if (ingestionResult?.column_mapping?.amount) {
        await triggerFullAnalysis(ingestionResult.column_mapping.amount, ingestionResult.column_mapping);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  // 6. Run Benford & Forensic Computations
  const triggerFullAnalysis = async (amountCol: string, mapping: Record<string, string>) => {
    setIsLoading(true);
    try {
      // Benford Suite
      const benfordRes = await fetch('/api/benford/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount_column: amountCol,
          consent_token: consentToken
        })
      });
      const benfordJson: BenfordSuiteResponse = await benfordRes.json();
      setBenfordData(benfordJson);

      // Forensic Anomaly Suite
      const forensicRes = await fetch('/api/forensics/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          column_mapping: mapping,
          consent_token: consentToken
        })
      });
      const forensicJson: ForensicTestsResponse = await forensicRes.json();
      setForensicsData(forensicJson);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Header */}
      <Header
        auditorName={auditorName}
        organizationFiduciary={organizationFiduciary}
        consentGranted={consentGranted}
        onOpenConsentModal={() => setIsConsentModalOpen(true)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        datasetName={ingestionResult?.file_name}
        datasetHash={ingestionResult?.dataset_hash}
      />

      {/* Main Content View Container with Error Boundary */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <ErrorBoundary>
          {activeTab === 'ingest' && (
            <DataIngestionView
              onFileUpload={handleFileUpload}
              onPathUpload={handlePathUpload}
              ingestionResult={ingestionResult}
              isLoading={isLoading}
              onUpdateColumnMapping={handleUpdateColumnMapping}
              onProceedToBenford={() => setActiveTab('benford')}
            />
          )}

          {activeTab === 'dpdp' && (
            <DPDPVaultView
              ingestionResult={ingestionResult}
              onApplySanitization={handleApplySanitization}
              isLoading={isLoading}
              onProceedToBenford={() => setActiveTab('benford')}
            />
          )}

          {activeTab === 'benford' && (
            <BenfordWorkbenchView
              benfordData={benfordData}
              ingestionResult={ingestionResult}
              isLoading={isLoading}
              onProceedToForensics={() => setActiveTab('forensics')}
            />
          )}

          {activeTab === 'forensics' && (
            <ForensicScannerView
              forensicsData={forensicsData}
              ingestionResult={ingestionResult}
              isLoading={isLoading}
              onProceedToLedger={() => setActiveTab('ledger')}
            />
          )}

          {activeTab === 'ledger' && (
            <AuditLedgerView
              onProceedToReport={() => setActiveTab('report')}
            />
          )}

          {activeTab === 'report' && (
            <ExecutiveReportView
              benfordData={benfordData}
              forensicsData={forensicsData}
              ingestionResult={ingestionResult}
              auditorName={auditorName}
              organizationFiduciary={organizationFiduciary}
            />
          )}
        </ErrorBoundary>
      </main>

      {/* Mandatory Disclaimer & DPDP Consent Modal */}
      <DisclaimerConsentModal
        isOpen={isConsentModalOpen}
        onClose={() => setIsConsentModalOpen(false)}
        onAcceptConsent={handleAcceptConsent}
        initialAuditorName={auditorName}
        initialOrganization={organizationFiduciary}
      />
    </div>
  );
}

export default App;
