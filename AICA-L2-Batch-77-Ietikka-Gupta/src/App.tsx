import React, { useState } from 'react';
import { 
  FileSpreadsheet, 
  FileText, 
  ShieldCheck, 
  BookOpen, 
  UserCheck, 
  Sparkles,
  Layers,
  Table,
  Receipt,
  AlertCircle,
  HelpCircle,
  Heart,
  LayoutGrid
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { ChallanRecord, AssesseeDetails } from './types';
import { defaultAssessee, sampleChallans } from './utils/sampleData';
import { exportTaxAuditToExcel } from './utils/exportExcel';
import { exportTaxAuditToPdf } from './utils/exportPdf';
import { Header } from './components/Header';
import { FileUpload } from './components/FileUpload';
import { SummaryCards } from './components/SummaryCards';
import { ChallanTable } from './components/ChallanTable';
import { Clause20bView } from './components/Clause20bView';
import { EditChallanModal } from './components/EditChallanModal';
import { AssesseeModal } from './components/AssesseeModal';
import { TaxAuditKnowledgeModal } from './components/TaxAuditKnowledgeModal';
import { SecurityModal } from './components/SecurityModal';

export default function App() {
  const [records, setRecords] = useState<ChallanRecord[]>(sampleChallans);
  const [assessee, setAssessee] = useState<AssesseeDetails>(defaultAssessee);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'clause20b'>('dashboard');
  
  // Modals
  const [isAssesseeModalOpen, setIsAssesseeModalOpen] = useState(false);
  const [isKnowledgeModalOpen, setIsKnowledgeModalOpen] = useState(false);
  const [isSecurityModalOpen, setIsSecurityModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [recordToEdit, setRecordToEdit] = useState<ChallanRecord | null>(null);

  // Notifications
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleRecordsExtracted = (newRecords: ChallanRecord[]) => {
    setRecords(newRecords);
    showToast(`Loaded ${newRecords.length} challans into Tax Audit schedule.`);
    confetti({ particleCount: 50, spread: 70, origin: { y: 0.6 } });
  };

  const handleClearAll = () => {
    if (window.confirm("Are you sure you want to clear all loaded challan records?")) {
      setRecords([]);
      showToast("All challan records cleared.");
    }
  };

  const handleOpenAddModal = () => {
    setRecordToEdit(null);
    setIsEditModalOpen(true);
  };

  const handleEditRecord = (record: ChallanRecord) => {
    setRecordToEdit(record);
    setIsEditModalOpen(true);
  };

  const handleDeleteRecord = (id: string) => {
    if (window.confirm("Delete this challan record from Tax Audit schedule?")) {
      setRecords(prev => prev.filter(r => r.id !== id));
      showToast("Challan record removed.");
    }
  };

  const handleSaveRecord = (savedRecord: ChallanRecord) => {
    setRecords(prev => {
      const existingIdx = prev.findIndex(r => r.id === savedRecord.id);
      if (existingIdx >= 0) {
        const updated = [...prev];
        updated[existingIdx] = savedRecord;
        return updated;
      }
      return [savedRecord, ...prev];
    });
    showToast(recordToEdit ? "Challan record updated." : "New challan record added.");
  };

  const handleExportExcel = () => {
    if (records.length === 0) {
      alert("No records to export.");
      return;
    }
    exportTaxAuditToExcel(records, assessee);
    showToast("Excel workbook downloaded successfully!");
  };

  const handleExportPdf = () => {
    if (records.length === 0) {
      alert("No records to export.");
      return;
    }
    exportTaxAuditToPdf(records, assessee);
    showToast("Tax Audit PDF Annexure downloaded successfully!");
  };

  const delayedCount = records.filter(r => r.status === 'DELAYED').length;
  const totalDisallowed = records.reduce((s, r) => s + r.disallowableAmount, 0);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans antialiased selection:bg-indigo-100 selection:text-indigo-900">
      
      {/* Top Application Header */}
      <Header
        assessee={assessee}
        onOpenAssesseeModal={() => setIsAssesseeModalOpen(true)}
        onOpenKnowledgeModal={() => setIsKnowledgeModalOpen(true)}
        onOpenSecurityModal={() => setIsSecurityModalOpen(true)}
        onOpenAddModal={handleOpenAddModal}
        onExportExcel={handleExportExcel}
        onExportPdf={handleExportPdf}
        recordCount={records.length}
      />

      {/* Main Bento Workspace Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Bento Upload & Telemetry Section */}
        <section aria-label="Upload ESI and PF Challans">
          <FileUpload
            onRecordsExtracted={handleRecordsExtracted}
            onClearAll={handleClearAll}
            recordCount={records.length}
            records={records}
            assessee={assessee}
            onExportExcel={handleExportExcel}
            onExportPdf={handleExportPdf}
          />
        </section>

        {/* Statutory Bento Summary KPIs */}
        {records.length > 0 && (
          <section aria-label="Tax Audit Summary Metrics">
            <SummaryCards records={records} />
          </section>
        )}

        {/* View Switcher Bento Tabs */}
        {records.length > 0 && (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
            
            <div className="flex items-center gap-1.5 bg-slate-200/80 p-1 rounded-2xl self-start shadow-2xs">
              <button
                onClick={() => setActiveTab('dashboard')}
                id="tab-challan-register"
                className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
                  activeTab === 'dashboard'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Table className="w-3.5 h-3.5 text-indigo-600" />
                <span>Interactive Challan Register ({records.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('clause20b')}
                id="tab-clause-20b"
                className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
                  activeTab === 'clause20b'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Receipt className="w-3.5 h-3.5 text-indigo-600" />
                <span>Form 3CD Clause 20(b) Schedule</span>
                {delayedCount > 0 && (
                  <span className="px-2 py-0.5 text-[10px] bg-rose-600 text-white font-bold rounded-full">
                    {delayedCount} Disallowed
                  </span>
                )}
              </button>
            </div>

            {/* Quick Export Shortcuts */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleExportExcel}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold shadow-2xs transition cursor-pointer active:scale-95"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                <span>Export 3CD Excel</span>
              </button>
              <button
                onClick={handleExportPdf}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold shadow-2xs transition cursor-pointer active:scale-95"
              >
                <FileText className="w-3.5 h-3.5 text-indigo-600" />
                <span>Export 3CD PDF</span>
              </button>
            </div>

          </div>
        )}

        {/* Tab Content Display */}
        <section aria-label="Audit Schedules and Tables">
          {activeTab === 'dashboard' ? (
            <ChallanTable
              records={records}
              onEditRecord={handleEditRecord}
              onDeleteRecord={handleDeleteRecord}
            />
          ) : (
            <Clause20bView
              records={records}
              assessee={assessee}
              onExportExcel={handleExportExcel}
              onExportPdf={handleExportPdf}
            />
          )}
        </section>

      </main>

      {/* Bento Grid Application Footer */}
      <footer className="bg-slate-900 border-t border-slate-800 text-slate-400 py-6 mt-12 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          
          <div className="flex items-center gap-2.5 text-center md:text-left">
            <div className="w-6 h-6 rounded-lg bg-indigo-600/30 text-indigo-400 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <span>
              Tax Audit ESI & PF Digitizer • Created by <strong className="text-amber-300 font-bold">{assessee.auditorName}</strong> (Chartered Accountant)
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 text-slate-400 text-[11px]">
            <span className="font-mono">Form 3CD Clause 20(b)</span>
            <span className="text-slate-700">•</span>
            <span className="font-mono">Sec 36(1)(va) Compliance</span>
            <span className="text-slate-700">•</span>
            <span className="font-mono">Checkmate Services SC Ruling (2022)</span>
            <span className="text-slate-700">•</span>
            <button 
              onClick={() => setIsSecurityModalOpen(true)}
              className="text-indigo-400 hover:text-indigo-300 underline cursor-pointer"
            >
              100% Client Data Privacy
            </button>
          </div>

          <div className="flex items-center gap-2 text-slate-500 font-mono text-[10px]">
            <span>Audit Core v2.4</span>
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
          </div>

        </div>
      </footer>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-slate-900 text-white px-4 py-3 rounded-2xl shadow-xl border border-slate-700 text-xs font-semibold flex items-center gap-2 animate-bounce">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Modals */}
      <AssesseeModal
        isOpen={isAssesseeModalOpen}
        onClose={() => setIsAssesseeModalOpen(false)}
        assessee={assessee}
        onSave={(updated) => {
          setAssessee(updated);
          showToast("Client details updated for Form 3CD.");
        }}
      />

      <TaxAuditKnowledgeModal
        isOpen={isKnowledgeModalOpen}
        onClose={() => setIsKnowledgeModalOpen(false)}
      />

      <SecurityModal
        isOpen={isSecurityModalOpen}
        onClose={() => setIsSecurityModalOpen(false)}
      />

      <EditChallanModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSave={handleSaveRecord}
        recordToEdit={recordToEdit}
      />

    </div>
  );
}
