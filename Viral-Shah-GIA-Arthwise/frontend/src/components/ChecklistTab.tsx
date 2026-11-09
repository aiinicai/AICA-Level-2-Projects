import React, { useState, useEffect } from 'react';
import { 
  CheckCircle, AlertCircle, UploadCloud, FileCheck, 
  Clock, ShieldAlert, XCircle, Info, RefreshCw,
  Sparkles, FileText, ChevronDown, CheckCircle2, FolderOpen, Search
} from 'lucide-react';
import { DocumentChecklistItem, DossierFile } from '../types';
import { ApiClient } from '../api/client';

interface ChecklistTabProps {
  proposalId: string;
  checklistItems: DocumentChecklistItem[];
  onRefresh: () => void;
  onOpenWizard?: () => void;
}

export const ChecklistTab: React.FC<ChecklistTabProps> = ({
  proposalId,
  checklistItems,
  onRefresh,
  onOpenWizard,
}) => {
  const [selectedItemForNa, setSelectedItemForNa] = useState<DocumentChecklistItem | null>(null);
  const [naReasonInput, setNaReasonInput] = useState('');
  const [uploadingItemId, setUploadingItemId] = useState<string | null>(null);

  // Dossier Library state
  const [dossierFiles, setDossierFiles] = useState<DossierFile[]>([]);
  const [isLoadingLibrary, setIsLoadingLibrary] = useState(true);
  const [isAutoMapping, setIsAutoMapping] = useState(false);
  const [showFullLibraryModal, setShowFullLibraryModal] = useState(false);
  const [libraryFilterFolder, setLibraryFilterFolder] = useState('all');
  const [librarySearchTerm, setLibrarySearchTerm] = useState('');
  const [isSyncingCaseFolder, setIsSyncingCaseFolder] = useState(false);
  const [caseFolderInfo, setCaseFolderInfo] = useState<{ case_folder: string; total_files: number } | null>(null);

  const fetchCaseFolderInfo = async () => {
    try {
      const data = await ApiClient.request<any>(`/proposals/${proposalId}/documents/case-folder`);
      setCaseFolderInfo(data);
    } catch (_) {}
  };

  const fetchDossierLibrary = async () => {
    setIsLoadingLibrary(true);
    try {
      const data = await ApiClient.request<DossierFile[]>(
        `/proposals/${proposalId}/documents/dossier-library`
      );
      setDossierFiles(data);
    } catch (err: any) {
      console.error('Failed to load dossier library:', err);
    } finally {
      setIsLoadingLibrary(false);
    }
  };

  useEffect(() => {
    fetchDossierLibrary();
    fetchCaseFolderInfo();
  }, [proposalId]);

  // Handle Scan & Auto-Link Dedicated Case Folder
  const handleSyncCaseFolder = async () => {
    setIsSyncingCaseFolder(true);
    try {
      const res = await ApiClient.request<any>(
        `/proposals/${proposalId}/documents/sync-case-folder`,
        { method: 'POST' }
      );
      alert(res.message || `Scanned case folder: ${res.synced_count} documents auto-linked.`);
      await fetchDossierLibrary();
      await fetchCaseFolderInfo();
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error scanning case folder');
    } finally {
      setIsSyncingCaseFolder(false);
    }
  };

  // Handle 1-Click Auto Map
  const handleAutoMapAll = async () => {
    setIsAutoMapping(true);
    try {
      const res = await ApiClient.request<{ documents_attached: number; metrics_extracted: number }>(
        `/proposals/${proposalId}/documents/auto-map-all-dossier`,
        { method: 'POST' }
      );
      alert(`Success! Auto-attached ${res.documents_attached} primary documents and extracted ${res.metrics_extracted} financial metrics.`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Auto-mapping error');
    } finally {
      setIsAutoMapping(false);
    }
  };

  // Handle Dropdown Selection for a single row
  const handleAttachDropdownFile = async (item: DocumentChecklistItem, relativePath: string) => {
    if (!relativePath) return;
    setUploadingItemId(item.id);
    try {
      const res = await ApiClient.request<{ filename: string; extracted_metrics_count: number }>(
        `/proposals/${proposalId}/documents/attach-dossier-file`,
        {
          method: 'POST',
          body: JSON.stringify({
            relative_path: relativePath,
            category: item.category,
            checklist_item_id: item.id,
          }),
        }
      );
      alert(`Attached '${res.filename}'! Extracted ${res.extracted_metrics_count} metrics into Extracted Metrics tab.`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Attachment error');
    } finally {
      setUploadingItemId(null);
    }
  };

  const handleToggleApplicable = async (item: DocumentChecklistItem) => {
    if (item.is_applicable) {
      setSelectedItemForNa(item);
      setNaReasonInput('');
    } else {
      try {
        await ApiClient.request(`/proposals/${proposalId}/checklist/${item.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ is_applicable: true, verification_status: 'requested' }),
        });
        onRefresh();
      } catch (err: any) {
        alert(err.message);
      }
    }
  };

  const handleConfirmNa = async () => {
    if (!selectedItemForNa) return;
    if (!naReasonInput.trim()) {
      alert('A valid justification reason is required when marking a standard document as Not Applicable.');
      return;
    }
    try {
      await ApiClient.request(`/proposals/${proposalId}/checklist/${selectedItemForNa.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          is_applicable: false,
          na_reason: naReasonInput.trim(),
          verification_status: 'not_applicable',
        }),
      });
      setSelectedItemForNa(null);
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleToggleReceived = async (item: DocumentChecklistItem) => {
    const nextReceived = !item.is_received;
    const nextStatus = nextReceived ? (item.verification_status === 'verified' ? 'verified' : 'received') : 'requested';
    try {
      await ApiClient.request(`/proposals/${proposalId}/checklist/${item.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_received: nextReceived, verification_status: nextStatus }),
      });
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleStatusChange = async (item: DocumentChecklistItem, newStatus: string) => {
    try {
      await ApiClient.request(`/proposals/${proposalId}/checklist/${item.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ verification_status: newStatus }),
      });
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleManualFileUpload = async (item: DocumentChecklistItem, file: File) => {
    setUploadingItemId(item.id);
    const formData = new FormData();
    formData.append('category', item.category);
    formData.append('file', file);
    try {
      await ApiClient.uploadFile(`/proposals/${proposalId}/documents`, formData);
      await ApiClient.request(`/proposals/${proposalId}/checklist/${item.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_received: true, verification_status: 'verified' }),
      });
      alert(`Document uploaded & processed! Data figures extracted into Review tab.`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'File upload error');
    } finally {
      setUploadingItemId(null);
    }
  };

  // Helper to filter relevant files for a specific checklist category
  const getRelevantFilesForCategory = (category: string) => {
    const directMatches = dossierFiles.filter(f => f.category === category);
    if (directMatches.length > 0) return directMatches;
    return dossierFiles.slice(0, 15);
  };

  const totalApplicable = checklistItems.filter(i => i.is_applicable).length;
  const totalVerified = checklistItems.filter(i => i.verification_status === 'verified').length;
  const totalReceived = checklistItems.filter(i => i.is_received).length;

  return (
    <div className="space-y-4">
      {/* Case Document Ingestion & Library Action Banner */}
      <div className="bg-gradient-to-r from-brand-900 to-slate-900 text-white rounded-xl p-4 shadow-md flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-brand-700/80 rounded-lg text-amber-300">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-sm block">Case Document Ingestion & Storage</span>
            <p className="text-xs text-brand-100">
              Browse or link files strictly belonging to Case ID <strong className="text-white font-mono">{caseFolderInfo?.case_folder || proposalId}</strong>. Documents are isolated per client case.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onOpenWizard && (
            <button
              onClick={onOpenWizard}
              className="flex items-center gap-1.5 px-3 py-2 bg-[#a45139] hover:bg-[#8e4430] text-white rounded-lg text-xs font-bold border border-[#f5d7cf]/30 transition-all shadow-xs"
              title="Upload documents in a guided logical sequence: Financials, Month-wise GST, ITR, Banking"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>⚡ Guided Upload Wizard</span>
            </button>
          )}

          <button
            onClick={handleSyncCaseFolder}
            disabled={isSyncingCaseFolder}
            className="flex items-center gap-1.5 px-3 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold border border-emerald-600 transition-all shadow-xs"
            title="Scan dedicated case folder (cases/PROP-...) and auto-link all placed files"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncingCaseFolder ? 'animate-spin' : ''}`} />
            <span>{isSyncingCaseFolder ? 'Scanning Folder...' : '⚡ Scan Case Folder'}</span>
          </button>

          <button
            onClick={() => setShowFullLibraryModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-brand-800/80 hover:bg-brand-700 rounded-lg text-xs font-semibold border border-brand-500 transition-all"
          >
            <FolderOpen className="w-4 h-4 text-sky-300" />
            <span>Browse Case Documents ({dossierFiles.length})</span>
          </button>

          <button
            onClick={handleAutoMapAll}
            disabled={isAutoMapping}
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-slate-950 rounded-lg text-xs font-bold shadow-sm transition-all"
            title="Auto-map placed files in this Case ID folder"
          >
            <Sparkles className="w-4 h-4" />
            <span>{isAutoMapping ? 'Mapping Files...' : 'Auto-Map Case Files'}</span>
          </button>
        </div>
      </div>

      {/* Case Dedicated Backend Folder Banner */}
      {caseFolderInfo && (
        <div className="bg-sky-50 border border-sky-200 px-3.5 py-2 rounded-xl flex flex-wrap items-center justify-between gap-2 text-xs text-sky-950">
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-sky-700 flex-shrink-0" />
            <span>
              <strong>Case Backend Storage:</strong> <code className="bg-white px-1.5 py-0.5 rounded border border-sky-300 font-mono text-[11px] text-brand-900 select-all">{caseFolderInfo.case_folder}</code>
            </span>
          </div>
          <div className="flex items-center gap-2 text-[11px] font-semibold text-sky-800">
            <span>{caseFolderInfo.total_files} file(s) in case directory</span>
            <span className="text-slate-400">•</span>
            <span className="text-slate-600 font-normal">Drop any PDF/Excel files into this folder and tap "⚡ Scan Case Folder" to auto-link!</span>
          </div>
        </div>
      )}

      {/* Checklist Stats Bar */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between text-xs">
        <span className="font-semibold text-slate-700">Primary Checklist & Verification Governance (7-Column Format)</span>
        <div className="flex items-center gap-4 text-slate-600">
          <span>Total: <strong>{checklistItems.length}</strong></span>
          <span>Applicable: <strong>{totalApplicable}</strong></span>
          <span className="text-blue-700">Received: <strong>{totalReceived}</strong></span>
          <span className="text-emerald-700">Verified: <strong>{totalVerified}</strong></span>
        </div>
      </div>

      {/* 7-Column Primary Checklist Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <table className="w-full text-left text-xs min-w-[1050px]">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[11px]">
            <tr>
              <th className="py-3 px-3 w-[22%]">Document Description</th>
              <th className="py-3 px-3 w-[7%] text-center">Applicable?</th>
              <th className="py-3 px-3 w-[7%] text-center">Received?</th>
              <th className="py-3 px-3 w-[10%]">Period Required</th>
              <th className="py-3 px-3 w-[14%]">Verification Status</th>
              <th className="py-3 px-3 w-[14%]">Missing / Attached Source</th>
              <th className="py-3 px-3 w-[26%] text-right">Select from Dossier / Upload</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {checklistItems.map((item) => {
              const isUploading = uploadingItemId === item.id;
              const relevantFiles = getRelevantFilesForCategory(item.category);

              return (
                <tr
                  key={item.id}
                  className={`hover:bg-slate-50/70 transition-colors ${
                    !item.is_applicable ? 'bg-slate-50/80 opacity-60' : ''
                  }`}
                >
                  {/* Col 1: Document Name */}
                  <td className="py-3 px-3 font-medium text-slate-900">
                    <div>{item.document_name}</div>
                    {item.remarks && (
                      <div className="text-[10px] text-slate-500 font-normal">{item.remarks}</div>
                    )}
                    {!item.is_applicable && item.na_reason && (
                      <div className="text-[10px] text-amber-700 font-medium italic mt-0.5">
                        Exemption Reason: {item.na_reason}
                      </div>
                    )}
                  </td>

                  {/* Col 2: Applicable? */}
                  <td className="py-3 px-3 text-center">
                    <button
                      onClick={() => handleToggleApplicable(item)}
                      className={`px-2 py-1 rounded text-[11px] font-semibold transition-all ${
                        item.is_applicable
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100'
                          : 'bg-slate-200 text-slate-700 border border-slate-300'
                      }`}
                    >
                      {item.is_applicable ? 'Yes' : 'No'}
                    </button>
                  </td>

                  {/* Col 3: Received? */}
                  <td className="py-3 px-3 text-center">
                    <button
                      disabled={!item.is_applicable}
                      onClick={() => handleToggleReceived(item)}
                      className={`px-2 py-1 rounded text-[11px] font-semibold transition-all ${
                        item.is_received
                          ? 'bg-blue-50 text-blue-800 border border-blue-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100'
                      }`}
                    >
                      {item.is_received ? 'Received' : 'Pending'}
                    </button>
                  </td>

                  {/* Col 4: Period */}
                  <td className="py-3 px-3 font-mono text-[11px] text-slate-700">
                    {item.period_required || 'Current'}
                  </td>

                  {/* Col 5: Verification Status */}
                  <td className="py-3 px-3">
                    <select
                      disabled={!item.is_applicable}
                      value={item.verification_status}
                      onChange={(e) => handleStatusChange(item, e.target.value)}
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-800 font-medium focus:ring-1 focus:ring-brand-500"
                    >
                      <option value="requested">Requested</option>
                      <option value="partially_received">Partially Received</option>
                      <option value="received">Received (Unverified)</option>
                      <option value="verified">Verified & Checked</option>
                      <option value="rejected">Rejected (Discrepancy)</option>
                      <option value="expired">Expired / Obsolete</option>
                      <option value="superseded">Superseded</option>
                      <option value="not_applicable">Not Applicable</option>
                    </select>
                  </td>

                  {/* Col 6: Missing Details / Attached Source */}
                  <td className="py-3 px-3 text-slate-600">
                    <span className="text-[11px]">
                      {item.missing_details || (item.is_received ? 'Document linked' : 'Full document pending upload')}
                    </span>
                  </td>

                  {/* Col 7: Dropdown Selector from Dossier + Manual Upload */}
                  <td className="py-3 px-3 text-right">
                    {item.is_applicable && (
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Dropdown Options for Relevant Files */}
                        <div className="relative inline-block text-left w-48 sm:w-56">
                          <select
                            onChange={(e) => {
                              if (e.target.value) {
                                handleAttachDropdownFile(item, e.target.value);
                                e.target.value = '';
                              }
                            }}
                            defaultValue=""
                            disabled={isUploading}
                            className="w-full text-[11px] bg-slate-50 hover:bg-slate-100 border border-brand-300 text-slate-800 font-medium rounded-lg p-1.5 focus:outline-none focus:ring-1 focus:ring-brand-500 truncate"
                            title="Select relevant file from reference dossier"
                          >
                            <option value="" disabled>
                              ⚡ Link Document (Case Folder or Dossier)...
                            </option>
                            {/* 1. Files located inside this case's folder */}
                            {dossierFiles.filter((f: any) => f.is_case_file).length > 0 && (
                              <optgroup label="📁 Files in Case Backend Folder">
                                {dossierFiles
                                  .filter((f: any) => f.is_case_file)
                                  .map((f, fIdx) => (
                                    <option key={`case-${fIdx}`} value={f.relative_path}>
                                      ★ {f.filename}
                                    </option>
                                  ))}
                              </optgroup>
                            )}
                            <optgroup label={`Relevant from Reference Dossier (${item.category.toUpperCase()})`}>
                              {relevantFiles
                                .filter((f: any) => !f.is_case_file)
                                .map((f, fIdx) => (
                                  <option key={`rel-${fIdx}`} value={f.relative_path}>
                                    {f.filename}
                                  </option>
                                ))}
                            </optgroup>
                            <optgroup label="All Other Reference Dossier Files">
                              {dossierFiles
                                .filter((f: any) => !f.is_case_file && f.category !== item.category)
                                .slice(0, 30)
                                .map((f, fIdx) => (
                                  <option key={`all-${fIdx}`} value={f.relative_path}>
                                    [{f.folder}] {f.filename}
                                  </option>
                                ))}
                            </optgroup>
                          </select>
                        </div>

                        {/* Optional Manual File Upload Icon */}
                        <label
                          className="p-1.5 bg-white hover:bg-slate-100 text-slate-600 border border-slate-300 rounded-lg cursor-pointer transition-colors shadow-2xs"
                          title="Or upload an external file from your computer"
                        >
                          <UploadCloud className="w-3.5 h-3.5 text-slate-700" />
                          <input
                            type="file"
                            accept=".pdf,.xlsx,.xls,.csv,.png,.jpg"
                            className="hidden"
                            onChange={(e) => {
                              if (e.target.files && e.target.files[0]) {
                                handleManualFileUpload(item, e.target.files[0]);
                              }
                            }}
                          />
                        </label>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Full Dossier Library Explorer Modal */}
      {showFullLibraryModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in">
            {/* Header */}
            <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <FolderOpen className="w-5 h-5 text-sky-400" />
                <div>
                  <h3 className="font-bold text-sm">Case ID Documents Explorer</h3>
                  <p className="text-[11px] text-slate-400">
                    Case: <span className="font-mono font-semibold text-sky-300">{caseFolderInfo?.case_folder || proposalId}</span> • {dossierFiles.length} Case-Specific Document{dossierFiles.length !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowFullLibraryModal(false)}
                className="p-1 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {/* Filter & Search Bar */}
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 flex-1 max-w-md">
                <Search className="w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search filename or category..."
                  value={librarySearchTerm}
                  onChange={(e) => setLibrarySearchTerm(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-slate-800"
                />
              </div>

              <select
                value={libraryFilterFolder}
                onChange={(e) => setLibraryFilterFolder(e.target.value)}
                className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-slate-800 font-medium"
              >
                <option value="all">All Categories ({dossierFiles.length} files)</option>
                <option value="financial_statements">Financial Statements & Balance Sheets</option>
                <option value="itr">ITRs & Tax Computations</option>
                <option value="gst">GST Returns (GSTR-3B / Certificates)</option>
                <option value="bank_statement">Bank Statements (Current / CC / OD)</option>
                <option value="purchase_orders">Purchase Orders & Contracts</option>
                <option value="kyc">Company Identity & KYC</option>
              </select>
            </div>

            {/* Files Grid / List */}
            <div className="p-6 overflow-y-auto flex-1 text-xs">
              {dossierFiles.length === 0 ? (
                <div className="py-12 px-6 text-center space-y-3">
                  <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto text-slate-400">
                    <FolderOpen className="w-6 h-6" />
                  </div>
                  <h4 className="font-bold text-slate-800 text-sm">No Documents in Case ID Folder Yet</h4>
                  <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
                    Documents are strictly segregated per client proposal. To attach files to Case ID <strong className="text-slate-700 font-mono">{caseFolderInfo?.case_folder || proposalId}</strong>, click "Upload" on any checklist row or place files directly into <code className="bg-slate-100 px-1.5 py-0.5 rounded text-[11px] font-mono text-slate-800">cases/{caseFolderInfo?.case_folder || proposalId}/</code> on your MacBook, then click "⚡ Scan Case Folder".
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {dossierFiles
                    .filter((f) => {
                      const matchFolder = libraryFilterFolder === 'all' || f.category === libraryFilterFolder;
                      const matchSearch = f.filename.toLowerCase().includes(librarySearchTerm.toLowerCase()) ||
                                          f.folder.toLowerCase().includes(librarySearchTerm.toLowerCase());
                      return matchFolder && matchSearch;
                    })
                    .map((f, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl border border-slate-200 bg-white hover:border-brand-300 hover:shadow-xs transition-all flex items-center justify-between gap-3"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <FileText className="w-4 h-4 text-brand-800 flex-shrink-0" />
                          <div className="min-w-0">
                            <p className="font-semibold text-slate-800 truncate" title={f.filename}>
                              {f.filename}
                            </p>
                            <p className="text-[10px] text-slate-500">
                              Folder: {f.folder} | {(f.size_bytes / 1024).toFixed(0)} KB
                            </p>
                          </div>
                        </div>

                        <button
                          onClick={async () => {
                            const targetItem = checklistItems.find(i => i.category === f.category) || checklistItems[0];
                            if (targetItem) {
                              await handleAttachDropdownFile(targetItem, f.relative_path);
                              setShowFullLibraryModal(false);
                            }
                          }}
                          className="px-2.5 py-1 rounded bg-[#faece7] hover:bg-[#f5d7cf] text-[#a45139] border border-[#f5d7cf] font-semibold text-[11px] whitespace-nowrap"
                        >
                          Attach File
                        </button>
                      </div>
                    ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setShowFullLibraryModal(false)}
                className="px-4 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold"
              >
                Close Library
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal for Mandatory N/A Justification */}
      {selectedItemForNa && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-2xl border border-slate-200">
            <h4 className="font-bold text-slate-900 text-sm mb-1">Mandatory N/A Justification</h4>
            <p className="text-xs text-slate-500 mb-3">
              Explain why <strong>{selectedItemForNa.document_name}</strong> is exempt from this credit proposal.
            </p>
            <textarea
              rows={3}
              value={naReasonInput}
              onChange={(e) => setNaReasonInput(e.target.value)}
              placeholder="e.g. Entity incorporated in current year, or business is exempt under GST Section 23..."
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 focus:ring-1 focus:ring-brand-500"
              autoFocus
            />
            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                onClick={() => setSelectedItemForNa(null)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmNa}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-brand-800 hover:bg-brand-900 text-white shadow-sm"
              >
                Confirm Exemption
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
