import React, { useState } from 'react';
import {
  X,
  FileText,
  Download,
  Eye,
  Sparkles,
  ShieldCheck,
  FileSpreadsheet,
  Check,
  Search,
  Filter,
  Plus,
  RefreshCw,
  ExternalLink,
  Layers,
  ArrowRight,
  Info,
  FolderArchive,
  UserCheck,
  AlertTriangle,
  Clock,
  Users,
} from 'lucide-react';
import {
  DUMMY_DOCUMENTS,
  DummyDocument,
  SYNTHETIC_PERSONS,
  SyntheticPerson,
  getDocAlertStatus,
  downloadDummyDocFile,
  downloadMasterTrialXlsx,
  downloadMasterTrialExcel,
  downloadCategoryTrialExcel,
  downloadAllTrialAssetsZip,
  getInitialTrialAppRows,
} from '../data/dummyDocuments';
import { AppRow, Kind } from '../types';
import { inr } from '../utils/calculations';
import { AttachmentRecord } from '../utils/attachmentStorage';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onViewDocument: (att: AttachmentRecord, title: string) => void;
  onAddSingleTrialDoc: (row: AppRow) => void;
  onLoadAllTrialData: (rows: AppRow[]) => void;
  onTestScanDoc: (file: File, kind: Kind) => void;
  onNotify: (msg: string) => void;
}

export const TrialDocumentsModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onViewDocument,
  onAddSingleTrialDoc,
  onLoadAllTrialData,
  onTestScanDoc,
  onNotify,
}) => {
  const [filterMode, setFilterMode] = useState<'category' | 'person'>('person');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedPerson, setSelectedPerson] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isZipping, setIsZipping] = useState<boolean>(false);
  const [zipProgress, setZipProgress] = useState<number>(0);

  if (!isOpen) return null;

  const categories = [
    { id: 'all', label: 'All Categories', count: 41 },
    { id: 'bank_fd', label: 'Bank Fixed Deposits', count: 5 },
    { id: 'insurance', label: 'Insurance Policies', count: 6 },
    { id: 'mutual_fund', label: 'Mutual Funds', count: 5 },
    { id: 'utility_bill', label: 'Utility Bills', count: 5 },
    { id: 'passport', label: 'Passports', count: 5 },
    { id: 'licence', label: 'Driving Licences', count: 5 },
    { id: 'pan', label: 'PAN Cards', count: 5 },
    { id: 'aadhaar', label: 'Aadhaar (Masked)', count: 5 },
  ];

  const filteredDocs = DUMMY_DOCUMENTS.filter((doc) => {
    const matchesCat =
      filterMode === 'person' || selectedCategory === 'all' || doc.category === selectedCategory;
    const matchesPerson =
      filterMode === 'category' || selectedPerson === 'all' || doc.personName === selectedPerson;
    const matchesSearch =
      !searchQuery ||
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.personName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.docNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.institution.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesPerson && matchesSearch;
  });

  const expiredCount = DUMMY_DOCUMENTS.filter((d) => {
    const s = getDocAlertStatus(d);
    return s.includes('OVERDUE') || s.includes('EXPIRED') || s.includes('MATURED');
  }).length;

  const handleView = (doc: DummyDocument) => {
    const att: AttachmentRecord = {
      id: doc.id,
      rowId: doc.id,
      name: doc.fileName,
      size: 15400,
      type: 'image/svg+xml',
      dataUrl: doc.svgDataUrl,
      previewUrl: doc.svgDataUrl,
      uploadedAt: new Date().toISOString(),
    };
    onViewDocument(att, doc.title);
  };

  const handleTestScan = (doc: DummyDocument) => {
    const svgText = decodeURIComponent(doc.svgDataUrl.replace('data:image/svg+xml;charset=utf-8,', ''));
    const file = new File([svgText], doc.fileName, { type: 'image/svg+xml' });
    onTestScanDoc(file, doc.kind);
    onClose();
  };

  const handleAddSingle = (doc: DummyDocument) => {
    const row: AppRow = {
      id: doc.id,
      kind: doc.kind,
      data: {
        ...doc.rowData,
        attachmentUrl: doc.svgDataUrl,
        attachmentName: doc.fileName,
        hasAttachment: true,
      },
    };
    onAddSingleTrialDoc(row);
    setCopiedId(doc.id);
    onNotify(`Added "${doc.title}" with document attachment.`);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleLoadAll = () => {
    const trialRows = getInitialTrialAppRows();
    onLoadAllTrialData(trialRows);
    onNotify('Loaded all 41 DPDP-compliant trial records (including 7 expired alerts) into the app.');
    onClose();
  };

  const handleDownloadZip = async () => {
    try {
      setIsZipping(true);
      setZipProgress(10);
      await downloadAllTrialAssetsZip((p) => setZipProgress(p));
      onNotify('✓ Downloaded complete 41 Trial Assets ZIP pack with subfolders & Excel workbook!');
    } catch (e: any) {
      console.error('ZIP generation failed', e);
      onNotify('Failed to create ZIP file: ' + (e?.message || 'unknown error'));
    } finally {
      setIsZipping(false);
      setZipProgress(0);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/75 backdrop-blur-xs overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl w-full max-w-5xl max-h-[94vh] flex flex-col shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#DCE2EA] dark:border-[#25324A] bg-slate-50 dark:bg-[#0E1626]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#0E7C86]/10 text-[#0E7C86] flex items-center justify-center flex-shrink-0">
              <FolderArchive className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base sm:text-lg font-bold text-[#0F1B2D] dark:text-[#E8EDF5]">
                  41 Trial Assets · 10 Synthetic Persons Hub
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                  DPDP Act Compliant
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300 border border-rose-300 dark:border-rose-800 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  {expiredCount} Overdue Alerts Included
                </span>
              </div>
              <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
                Download all 41 vector SVG documents in a structured ZIP folder, inspect individual documents with zoom/rotate, and download master multi-sheet Excel files.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-lg text-[#6F7E92] hover:text-[#0F1B2D] dark:text-[#8594AA] dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-slate-800 transition cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Global Action Banner: Excel & CSV Exports */}
        <div className="p-4 bg-gradient-to-r from-teal-50 via-sky-50 to-indigo-50 dark:from-teal-950/30 dark:via-slate-900 dark:to-indigo-950/30 border-b border-[#DCE2EA] dark:border-[#25324A] flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 text-xs">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-200">
              <FileSpreadsheet className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Export Master Spreadsheet &amp; Inspection Data:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {/* Native multi-sheet Excel (.xlsx) */}
              <button
                type="button"
                onClick={() => {
                  downloadMasterTrialXlsx();
                  onNotify('Downloaded PaisaPal_Trial_Master_Data_10_Persons.xlsx (7 sheets).');
                }}
                className="px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition cursor-pointer"
              >
                <FileSpreadsheet className="w-4 h-4" />
                <span>Master Excel Workbook (.XLSX - 7 Sheets)</span>
              </button>

              {/* CSV format */}
              <button
                type="button"
                onClick={() => {
                  downloadMasterTrialExcel();
                  onNotify('Downloaded Master CSV spreadsheet.');
                }}
                className="px-3 py-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-emerald-500 text-slate-700 dark:text-slate-300 font-medium text-xs flex items-center gap-1 transition cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 text-blue-600" />
                <span>Master CSV</span>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 justify-end flex-shrink-0">
            <button
              type="button"
              onClick={handleLoadAll}
              className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm transition cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              <span>Load 41 Records into App</span>
            </button>
          </div>
        </div>

        {/* Filter Bar: Toggle Person vs Category & Search */}
        <div className="px-5 py-3 border-b border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">View By:</span>
            <div className="inline-flex rounded-lg border border-slate-200 dark:border-slate-700 p-0.5 bg-slate-50 dark:bg-slate-900 text-xs">
              <button
                type="button"
                onClick={() => setFilterMode('person')}
                className={`px-3 py-1 rounded-md font-semibold flex items-center gap-1.5 transition cursor-pointer ${
                  filterMode === 'person'
                    ? 'bg-[#0E7C86] text-white shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>10 Persons ({SYNTHETIC_PERSONS.length})</span>
              </button>
              <button
                type="button"
                onClick={() => setFilterMode('category')}
                className={`px-3 py-1 rounded-md font-semibold flex items-center gap-1.5 transition cursor-pointer ${
                  filterMode === 'category'
                    ? 'bg-[#0E7C86] text-white shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <Filter className="w-3.5 h-3.5" />
                <span>Categories</span>
              </button>
            </div>
          </div>

          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by person, document, bank, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-[#0E7C86]"
            />
          </div>
        </div>

        {/* Horizontal Selector Bar (Persons or Categories) */}
        <div className="px-5 py-2.5 border-b border-[#DCE2EA] dark:border-[#25324A] bg-slate-50/70 dark:bg-[#0E1626]/70 flex items-center gap-1.5 overflow-x-auto text-xs no-scrollbar">
          {filterMode === 'person' ? (
            <>
              <button
                type="button"
                onClick={() => setSelectedPerson('all')}
                className={`px-2.5 py-1 rounded-full whitespace-nowrap transition cursor-pointer ${
                  selectedPerson === 'all'
                    ? 'bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 font-bold'
                    : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                All 10 Persons (41 Assets)
              </button>
              {SYNTHETIC_PERSONS.map((p) => {
                const hasExpired = DUMMY_DOCUMENTS.some(
                  (d) =>
                    d.personName === p.name &&
                    (getDocAlertStatus(d).includes('OVERDUE') ||
                      getDocAlertStatus(d).includes('EXPIRED') ||
                      getDocAlertStatus(d).includes('MATURED'))
                );
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setSelectedPerson(p.name)}
                    className={`px-2.5 py-1 rounded-full whitespace-nowrap flex items-center gap-1.5 transition cursor-pointer ${
                      selectedPerson === p.name
                        ? 'bg-[#0E7C86] text-white font-bold shadow-xs'
                        : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700'
                    }`}
                  >
                    <span>{p.name.split(' ')[0]} ({p.docCount})</span>
                    {hasExpired && (
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" title="Has expired / overdue alert" />
                    )}
                  </button>
                );
              })}
            </>
          ) : (
            categories.map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-2.5 py-1 rounded-full whitespace-nowrap transition cursor-pointer ${
                  selectedCategory === cat.id
                    ? 'bg-[#0E7C86] text-white font-bold shadow-xs'
                    : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700'
                }`}
              >
                {cat.label} ({cat.count})
              </button>
            ))
          )}
        </div>

        {/* Document Grid */}
        <div className="flex-1 overflow-y-auto p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 bg-slate-100/50 dark:bg-[#0B111D]">
          {filteredDocs.map((doc) => {
            const alertStatus = getDocAlertStatus(doc);
            const isAlert =
              alertStatus.includes('OVERDUE') ||
              alertStatus.includes('EXPIRED') ||
              alertStatus.includes('MATURED');
            const isDueSoon = alertStatus.includes('DUE SOON');

            return (
              <div
                key={doc.id}
                className="bg-white dark:bg-[#131C2E] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs hover:shadow-md transition flex flex-col group"
              >
                {/* Visual Thumbnail Preview Header */}
                <div
                  className="h-36 bg-slate-900 relative overflow-hidden cursor-pointer flex items-center justify-center"
                  onClick={() => handleView(doc)}
                  title="Click to view high-resolution document"
                >
                  <img
                    src={doc.svgDataUrl}
                    alt={doc.title}
                    className="w-full h-full object-cover object-top group-hover:scale-105 transition duration-300 opacity-90 group-hover:opacity-100"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20 flex flex-col justify-between p-2.5">
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-black/70 text-white backdrop-blur-xs">
                        {doc.category.replace('_', ' ')}
                      </span>
                      {isAlert ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-black bg-rose-600 text-white flex items-center gap-1 shadow-xs animate-pulse">
                          <AlertTriangle className="w-3 h-3" />
                          {alertStatus}
                        </span>
                      ) : isDueSoon ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-black bg-amber-500 text-white flex items-center gap-1 shadow-xs">
                          <Clock className="w-3 h-3" />
                          {alertStatus}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-700">
                          Active
                        </span>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-white text-[11px]">
                      <span className="font-mono font-bold truncate max-w-[170px]">{doc.docNumber}</span>
                      <span className="font-bold flex items-center gap-1 bg-black/60 px-2 py-0.5 rounded backdrop-blur-xs">
                        <Eye className="w-3 h-3" /> View
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Body */}
                <div className="p-3.5 flex-1 flex flex-col justify-between space-y-3">
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 line-clamp-1">
                        {doc.title}
                      </h3>
                    </div>

                    <div className="mt-1 flex items-center gap-1.5 text-[11px] text-[#0E7C86] dark:text-[#38bdf8] font-semibold">
                      <UserCheck className="w-3 h-3 flex-shrink-0" />
                      <span>{doc.personName}</span>
                    </div>

                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
                      {doc.institution}
                    </p>

                    {/* Metadata Pill Box */}
                    <div className="mt-2.5 p-2 rounded-lg bg-slate-50 dark:bg-slate-900/80 border border-slate-100 dark:border-slate-800 text-[11px] space-y-1">
                      {doc.amount != null && (
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500 dark:text-slate-400">
                            {doc.category === 'bank_fd'
                              ? 'Principal Amount:'
                              : doc.category === 'utility_bill'
                              ? 'Bill Amount:'
                              : doc.category === 'insurance'
                              ? 'Annual Premium:'
                              : 'Invested:'}
                          </span>
                          <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                            {inr(doc.amount)}
                          </span>
                        </div>
                      )}
                      {doc.currentValue != null && (
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500 dark:text-slate-400">
                            {doc.category === 'bank_fd'
                              ? 'Maturity Value:'
                              : doc.category === 'insurance'
                              ? 'Sum Assured / IDV:'
                              : 'Current Valuation:'}
                          </span>
                          <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                            {inr(doc.currentValue)}
                          </span>
                        </div>
                      )}
                      {doc.date && (
                        <div className="flex items-center justify-between">
                          <span className="text-slate-500 dark:text-slate-400">
                            {doc.category === 'bank_fd'
                              ? 'Maturity Date:'
                              : doc.category === 'utility_bill'
                              ? 'Payment Due:'
                              : doc.category === 'insurance'
                              ? 'Renewal Due:'
                              : 'Expires:'}
                          </span>
                          <span
                            className={`font-mono font-bold ${
                              isAlert
                                ? 'text-rose-600 dark:text-rose-400 underline'
                                : isDueSoon
                                ? 'text-amber-600 dark:text-amber-400'
                                : 'text-slate-700 dark:text-slate-300'
                            }`}
                          >
                            {doc.date}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between gap-1.5">
                    <button
                      type="button"
                      onClick={() => handleView(doc)}
                      className="px-2 py-1 rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold text-[11px] flex items-center gap-1 transition cursor-pointer"
                      title="View document certificate"
                    >
                      <Eye className="w-3 h-3" />
                      <span>View</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        downloadDummyDocFile(doc);
                        onNotify(`Downloaded "${doc.fileName}" for local testing.`);
                      }}
                      className="px-2 py-1 rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold text-[11px] flex items-center gap-1 transition cursor-pointer"
                      title="Download vector SVG file"
                    >
                      <Download className="w-3 h-3" />
                      <span>.SVG</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleTestScan(doc)}
                      className="px-2 py-1 rounded-md bg-teal-50 hover:bg-teal-100 dark:bg-teal-950/60 dark:hover:bg-teal-900/80 text-teal-700 dark:text-teal-300 border border-teal-300 dark:border-teal-800 font-semibold text-[11px] flex items-center gap-1 transition cursor-pointer"
                      title="Test auto-scan with this file"
                    >
                      <Sparkles className="w-3 h-3 text-teal-600" />
                      <span>Test Scan</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleAddSingle(doc)}
                      className="px-2.5 py-1 rounded-md bg-[#0E7C86] hover:bg-[#0B656D] text-white font-semibold text-[11px] flex items-center gap-1 transition cursor-pointer ml-auto"
                      title="Add to app records"
                    >
                      {copiedId === doc.id ? (
                        <>
                          <Check className="w-3 h-3" />
                          <span>Added</span>
                        </>
                      ) : (
                        <>
                          <Plus className="w-3 h-3" />
                          <span>Add</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#DCE2EA] dark:border-[#25324A] bg-slate-50 dark:bg-[#0E1626] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>
              DPDP Act 2023 Compliant: 100% synthetic trial assets across 10 distinct persons. Matured/expired items trigger real alert flags.
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-semibold transition cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
