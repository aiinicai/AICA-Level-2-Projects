import React, { useState, useEffect, useMemo } from 'react';
import { 
  AuditModule, 
  UploadedDocument, 
  CAFirmProfile, 
  InvoiceReviewData, 
  GSTComplianceData, 
  BankStatementData, 
  TDSAnalysisData 
} from './types';
import { 
  SAMPLE_DOCUMENTS, 
  SAMPLE_AUDIT_DATA, 
  DEFAULT_CA_FIRM_PROFILE, 
  SampleDocumentItem 
} from './utils/sampleData';
import { exportAuditToExcel } from './utils/excelExport';

// Subcomponents
import { Header } from './components/Header';
import { Navigation } from './components/Navigation';
import { DocumentViewer } from './components/DocumentViewer';
import { InvoiceReviewModule } from './components/InvoiceReviewModule';
import { GSTComplianceModule } from './components/GSTComplianceModule';
import { BankStatementModule } from './components/BankStatementModule';
import { TDSAnalyserModule } from './components/TDSAnalyserModule';
import { RawJsonModal } from './components/RawJsonModal';
import { FirmSettingsModal } from './components/FirmSettingsModal';
import { AskAuditorAI } from './components/AskAuditorAI';

// Lucide Icons
import { 
  Sparkles, 
  FileSpreadsheet, 
  Code2, 
  MessageSquare, 
  CheckCircle2, 
  AlertCircle,
  FileCheck2,
  RefreshCw,
  Layers,
  ArrowRight
} from 'lucide-react';

export default function App() {
  // Navigation & Active Module State
  const [activeModule, setActiveModule] = useState<AuditModule>('invoice');

  // CA Firm & Audit Engagement Profile
  const [firmProfile, setFirmProfile] = useState<CAFirmProfile>(DEFAULT_CA_FIRM_PROFILE);

  // Active Document State
  const [currentDoc, setCurrentDoc] = useState<UploadedDocument | null>(() => {
    const initialSample = SAMPLE_DOCUMENTS[0]; // Sample Invoice
    return {
      id: initialSample.id,
      name: initialSample.name,
      size: initialSample.size,
      mimeType: initialSample.mimeType,
      dataUrl: '',
      uploadedAt: new Date().toISOString(),
      isSample: true,
      sampleType: initialSample.module,
    };
  });

  // Module Data States
  const [invoiceData, setInvoiceData] = useState<InvoiceReviewData>(SAMPLE_AUDIT_DATA.invoice);
  const [gstData, setGstData] = useState<GSTComplianceData>(SAMPLE_AUDIT_DATA.gst);
  const [bankData, setBankData] = useState<BankStatementData>(SAMPLE_AUDIT_DATA.bank);
  const [tdsData, setTdsData] = useState<TDSAnalysisData>(SAMPLE_AUDIT_DATA.tds);

  // Processing & UI States
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isRawJsonOpen, setIsRawJsonOpen] = useState<boolean>(false);
  const [isCopilotOpen, setIsCopilotOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Auto-dismiss toast notification
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => setToastMessage(null), 3500);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
  };

  // Switch Module handler
  const handleSelectModule = (mod: AuditModule) => {
    setActiveModule(mod);
    
    // Automatically match the sample document if current is a sample
    if (currentDoc?.isSample) {
      const matchingSample = SAMPLE_DOCUMENTS.find(s => s.module === mod) || SAMPLE_DOCUMENTS[0];
      setCurrentDoc({
        id: matchingSample.id,
        name: matchingSample.name,
        size: matchingSample.size,
        mimeType: matchingSample.mimeType,
        dataUrl: '',
        uploadedAt: new Date().toISOString(),
        isSample: true,
        sampleType: matchingSample.module,
      });

      if (matchingSample.module === 'invoice') {
        setInvoiceData(matchingSample.sampleData as InvoiceReviewData);
      } else if (matchingSample.module === 'gst') {
        setGstData(matchingSample.sampleData as GSTComplianceData);
      } else if (matchingSample.module === 'bank') {
        setBankData(matchingSample.sampleData as BankStatementData);
      } else if (matchingSample.module === 'tds') {
        setTdsData(matchingSample.sampleData as TDSAnalysisData);
      }
    }
  };

  // Select a pre-loaded CA sample document
  const handleSelectSample = (sample: SampleDocumentItem) => {
    setCurrentDoc({
      id: sample.id,
      name: sample.name,
      size: sample.size,
      mimeType: sample.mimeType,
      dataUrl: '',
      uploadedAt: new Date().toISOString(),
      isSample: true,
      sampleType: sample.module,
    });

    if (sample.module !== activeModule) {
      setActiveModule(sample.module);
    }

    if (sample.module === 'invoice') {
      setInvoiceData(sample.sampleData as InvoiceReviewData);
    } else if (sample.module === 'gst') {
      setGstData(sample.sampleData as GSTComplianceData);
    } else if (sample.module === 'bank') {
      setBankData(sample.sampleData as BankStatementData);
    } else if (sample.module === 'tds') {
      setTdsData(sample.sampleData as TDSAnalysisData);
    }

    showToast(`Loaded "${sample.name}" for CA Audit verification.`);
  };

  // File Upload Handler (Base64 conversion and Gemini Vision API call)
  const handleFileUpload = async (file: File) => {
    const reader = new FileReader();

    reader.onload = async () => {
      const base64Data = (reader.result as string).split(',')[1] || '';
      const dataUrl = reader.result as string;

      const newDoc: UploadedDocument = {
        id: `upload-${Date.now()}`,
        name: file.name,
        size: file.size,
        mimeType: file.type || 'application/pdf',
        dataUrl: dataUrl,
        base64Data: base64Data,
        uploadedAt: new Date().toISOString(),
        isSample: false,
      };

      setCurrentDoc(newDoc);
      showToast(`Uploaded ${file.name}. Triggering Gemini AI Vision audit...`);

      // Trigger AI analysis
      await analyzeDocument(newDoc, activeModule);
    };

    reader.readAsDataURL(file);
  };

  // Call Gemini Multimodal Backend
  const analyzeDocument = async (doc: UploadedDocument, module: AuditModule) => {
    setIsAnalyzing(true);

    // If it's a sample test document, run instant verification with loading state
    if (doc.isSample) {
      const matchingSample = SAMPLE_DOCUMENTS.find(s => s.id === doc.id) || 
                             SAMPLE_DOCUMENTS.find(s => s.module === module) || 
                             SAMPLE_DOCUMENTS[0];
      
      await new Promise(resolve => setTimeout(resolve, 600));
      
      if (module === 'invoice') {
        setInvoiceData(matchingSample.sampleData as InvoiceReviewData);
      } else if (module === 'gst') {
        setGstData(matchingSample.sampleData as GSTComplianceData);
      } else if (module === 'bank') {
        setBankData(matchingSample.sampleData as BankStatementData);
      } else if (module === 'tds') {
        setTdsData(matchingSample.sampleData as TDSAnalysisData);
      }

      setIsAnalyzing(false);
      showToast(`✅ Gemini AI Vision audit completed for ${doc.name}!`);
      return;
    }

    if (!doc.base64Data) {
      setIsAnalyzing(false);
      showToast("Ready for analysis.");
      return;
    }

    const endpoints = {
      invoice: '/api/analyze-invoice',
      gst: '/api/analyze-gst',
      bank: '/api/analyze-bank-statement',
      tds: '/api/analyze-tds',
    };

    try {
      const res = await fetch(endpoints[module], {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fileBase64: doc.base64Data,
          mimeType: doc.mimeType,
          filename: doc.name,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.error || `Server error (${res.status}): ${res.statusText}`);
      }

      const result = await res.json();

      // Update state according to module
      if (module === 'invoice') {
        setInvoiceData(result);
      } else if (module === 'gst') {
        setGstData(result);
      } else if (module === 'bank') {
        setBankData(result);
      } else if (module === 'tds') {
        setTdsData(result);
      }

      showToast(`✅ Gemini AI Vision audit completed for ${doc.name}!`);
    } catch (err: any) {
      console.error("AI Audit error:", err);
      showToast(`⚠️ AI Vision notice: ${err.message || 'Please retry analysis.'}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Dynamically resolve client name and identifiers based on active document and module
  const activeDocumentClient = useMemo(() => {
    let name = firmProfile.clientName;
    let gstin = firmProfile.clientGSTIN;
    let pan = firmProfile.clientPAN;

    if (activeModule === 'invoice') {
      if (invoiceData.receiverName) name = invoiceData.receiverName;
      if (invoiceData.receiverGSTIN) {
        gstin = invoiceData.receiverGSTIN;
        if (invoiceData.receiverGSTIN.length >= 12) {
          pan = invoiceData.receiverGSTIN.substring(2, 12);
        }
      }
    } else if (activeModule === 'gst') {
      if (gstData.receiverName) name = gstData.receiverName;
      if (gstData.receiverGSTIN) {
        gstin = gstData.receiverGSTIN;
        if (gstData.receiverGSTIN.length >= 12) {
          pan = gstData.receiverGSTIN.substring(2, 12);
        }
      }
    } else if (activeModule === 'bank') {
      if (bankData.accountHolder) name = bankData.accountHolder;
    } else if (activeModule === 'tds') {
      if (tdsData.deductorName) name = tdsData.deductorName;
    }

    return { name, gstin, pan };
  }, [activeModule, invoiceData, gstData, bankData, tdsData, firmProfile]);

  const effectiveFirmProfile: CAFirmProfile = useMemo(() => ({
    ...firmProfile,
    clientName: activeDocumentClient.name || firmProfile.clientName,
    clientGSTIN: activeDocumentClient.gstin || firmProfile.clientGSTIN,
    clientPAN: activeDocumentClient.pan || firmProfile.clientPAN,
    financialYear: firmProfile.financialYear || 'FY 2025-26 (AY 2026-27)',
    assessmentYear: firmProfile.assessmentYear || 'AY 2026-27',
  }), [firmProfile, activeDocumentClient]);

  // Direct Excel Export Handler
  const handleExportExcel = () => {
    let activeData: any = invoiceData;
    if (activeModule === 'gst') activeData = gstData;
    if (activeModule === 'bank') activeData = bankData;
    if (activeModule === 'tds') activeData = tdsData;

    try {
      const filename = exportAuditToExcel(activeModule, activeData, effectiveFirmProfile);
      showToast(`📥 Generated & Downloaded: ${filename}`);
    } catch (err: any) {
      console.error("Excel export error:", err);
      showToast(`Export failed: ${err.message}`);
    }
  };

  // Get current active module payload for Raw JSON Modal
  const getCurrentModuleData = () => {
    switch (activeModule) {
      case 'invoice': return invoiceData;
      case 'gst': return gstData;
      case 'bank': return bankData;
      case 'tds': return tdsData;
      default: return invoiceData;
    }
  };

  // Compute risk indicators for navigation pills
  const moduleRisks = {
    invoice: {
      count: (!invoiceData.isMathValid || (invoiceData.mathDiscrepancy || 0) > 1 || invoiceData.riskStatus === 'critical') ? 1 : 0,
      level: (!invoiceData.isMathValid || (invoiceData.mathDiscrepancy || 0) > 1 || invoiceData.riskStatus === 'critical')
        ? 'critical'
        : (invoiceData.riskStatus === 'warning' ? 'warning' : 'compliant')
    },
    gst: {
      count: (gstData.isPoSCompliant === false || (gstData.itcEligibility && gstData.itcEligibility.blockedITCAmount > 0) || gstData.riskStatus === 'critical') ? 1 : 0,
      level: (gstData.isPoSCompliant === false || (gstData.itcEligibility && gstData.itcEligibility.blockedITCAmount > 0) || gstData.riskStatus === 'critical')
        ? 'critical'
        : (gstData.riskStatus === 'warning' ? 'warning' : 'compliant')
    },
    bank: {
      count: (bankData.highCashTransactionsCount || 0) + (bankData.duplicateTransactionsCount || 0),
      level: ((bankData.highCashTransactionsCount || 0) > 0 || (bankData.duplicateTransactionsCount || 0) > 0 || bankData.riskStatus === 'critical')
        ? 'critical'
        : (bankData.riskStatus === 'warning' ? 'warning' : 'compliant')
    },
    tds: {
      count: (tdsData.isShortDeduction || (tdsData.tdsVariance || 0) > 0 || tdsData.riskStatus === 'critical') ? 1 : 0,
      level: (tdsData.isShortDeduction || (tdsData.tdsVariance || 0) > 0 || tdsData.riskStatus === 'critical')
        ? 'critical'
        : (tdsData.riskStatus === 'warning' ? 'warning' : 'compliant')
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans selection:bg-indigo-100 selection:text-indigo-900">
      
      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 animate-in fade-in slide-in-from-bottom duration-200">
          <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-slate-900 text-white shadow-2xl text-xs font-semibold">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Header with CA Firm Identity & Primary Actions */}
      <Header 
        firmProfile={effectiveFirmProfile}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onExportExcel={handleExportExcel}
        onOpenRawJson={() => setIsRawJsonOpen(true)}
        isProcessing={isAnalyzing}
        activeModuleTitle={activeModule.toUpperCase()}
      />

      {/* 4 Core Modules Navigation Bar */}
      <Navigation 
        activeModule={activeModule}
        onSelectModule={handleSelectModule}
        moduleRisks={moduleRisks}
      />

      {/* Main Content: Split-Screen Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5">
        
        {/* Module Title & Quick Action Sub-bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base sm:text-lg font-bold text-slate-800 tracking-tight">
                {activeModule === 'invoice' && '1. Vendor Invoice Review & Arithmetic Audit'}
                {activeModule === 'gst' && '2. GST Place of Supply & Section 16(2) ITC Compliance'}
                {activeModule === 'tds' && '3. TDS Section Classifier & Short-Deduction Analyser'}
                {activeModule === 'bank' && '4. Bank Statement Forensic & Cash >₹50k SFT Audit'}
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Multimodal document extraction grounded in Indian Tax Statutes (CGST/IGST Act 2017 &amp; Income Tax Act 1961).
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Ask AI Copilot Button */}
            <button
              id="btn-open-copilot"
              onClick={() => setIsCopilotOpen(true)}
              className="px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-2xs"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              <span>Ask CA Copilot</span>
            </button>

            {/* Quick Export Excel */}
            <button
              onClick={handleExportExcel}
              className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-2xs"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
              <span>Export .xlsx</span>
            </button>
          </div>
        </div>

        {/* Split Screen Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          
          {/* Left Column (5/12): Document Inspector / Scan Viewer */}
          <div className="lg:col-span-5 sticky top-20">
            <DocumentViewer
              currentDoc={currentDoc}
              activeModule={activeModule}
              onFileUpload={handleFileUpload}
              onSelectSample={handleSelectSample}
              onAnalyzeDocument={() => currentDoc && analyzeDocument(currentDoc, activeModule)}
              isAnalyzing={isAnalyzing}
            />
          </div>

          {/* Right Column (7/12): AI Extraction & Audit Verification Dashboard */}
          <div className="lg:col-span-7">
            {activeModule === 'invoice' && (
              <InvoiceReviewModule 
                data={invoiceData} 
                onExportExcel={handleExportExcel}
              />
            )}

            {activeModule === 'gst' && (
              <GSTComplianceModule 
                data={gstData} 
                onExportExcel={handleExportExcel}
              />
            )}

            {activeModule === 'tds' && (
              <TDSAnalyserModule 
                data={tdsData} 
                onExportExcel={handleExportExcel}
              />
            )}

            {activeModule === 'bank' && (
              <BankStatementModule 
                data={bankData} 
                onExportExcel={handleExportExcel}
              />
            )}
          </div>

        </div>

      </main>

      {/* Modals & Slide-out Drawers */}
      <RawJsonModal
        isOpen={isRawJsonOpen}
        onClose={() => setIsRawJsonOpen(false)}
        data={getCurrentModuleData()}
        title={`Gemini Vision JSON: ${activeModule.toUpperCase()} Module`}
      />

      <FirmSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        firmProfile={effectiveFirmProfile}
        onSave={(updated) => {
          setFirmProfile(updated);
          showToast("Updated CA Firm & Engagement details.");
        }}
      />

      <AskAuditorAI
        isOpen={isCopilotOpen}
        onClose={() => setIsCopilotOpen(false)}
        activeModule={activeModule}
        currentDocumentData={getCurrentModuleData()}
      />

    </div>
  );
}
