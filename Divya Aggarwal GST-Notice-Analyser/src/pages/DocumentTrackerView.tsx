import React, { useState, useRef } from 'react';
import { Client, NoticeCase, DocumentItem, DocumentStatus, DocumentMapping } from '../types';
import {
  exportDocumentTrackerToExcel,
  detectHeadersFromWorkbook,
  parseRowsWithMapping,
  ColumnDetectionResult,
} from '../services/excelMapperEngine';
import {
  ListTodo,
  Download,
  Upload,
  Plus,
  Trash2,
  FileSpreadsheet,
  Filter,
} from 'lucide-react';

interface DocumentTrackerViewProps {
  activeClient: Client | null;
  activeCase: NoticeCase | null;
  documentItems: DocumentItem[];
  onSaveItems: (items: DocumentItem[]) => Promise<void>;
  onDeleteItem: (id: string) => Promise<void>;
}

export const DocumentTrackerView: React.FC<DocumentTrackerViewProps> = ({
  activeClient,
  activeCase,
  documentItems,
  onSaveItems,
  onDeleteItem,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  const [newDocName, setNewDocName] = useState('');
  const [newCategory, setNewCategory] = useState('Portal Report');
  const [newDueDate, setNewDueDate] = useState('');
  const [newRemarks, setNewRemarks] = useState('');

  const [importedBuffer, setImportedBuffer] = useState<ArrayBuffer | null>(null);
  const [detectionResult, setDetectionResult] = useState<ColumnDetectionResult | null>(null);
  const [mapping, setMapping] = useState<DocumentMapping>({
    id: 'custom_map',
    templateName: 'CA Firm Default',
    docNameCol: '',
    categoryCol: '',
    statusCol: '',
    dueDateCol: '',
    remarksCol: '',
    periodCol: '',
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!activeCase || !activeClient) {
    return (
      <div className="flex items-center justify-center h-full p-8 text-gray-500 text-xs">
        No active notice selected. Please select a notice to view document tracking.
      </div>
    );
  }

  const filteredItems = documentItems.filter((item) => {
    if (statusFilter === 'ALL') return true;
    return item.status.toUpperCase() === statusFilter.toUpperCase();
  });

  const handleUpdateStatus = async (item: DocumentItem, newStatus: DocumentStatus) => {
    const updated = documentItems.map((d) =>
      d.id === item.id
        ? {
            ...d,
            status: newStatus,
            receivedDate: newStatus === 'Received' || newStatus === 'Completed' ? new Date().toISOString().split('T')[0] : d.receivedDate,
          }
        : d
    );
    await onSaveItems(updated);
  };

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDocName.trim()) return;

    const newItem: DocumentItem = {
      id: 'doc_' + Date.now(),
      caseId: activeCase.id,
      docName: newDocName.trim(),
      category: newCategory,
      status: 'Pending',
      requestedDate: new Date().toISOString().split('T')[0],
      dueDate: newDueDate || activeCase.replyDeadline || '—',
      remarks: newRemarks.trim(),
      period: activeCase.period,
    };

    await onSaveItems([newItem, ...documentItems]);
    setNewDocName('');
    setNewRemarks('');
    setShowAddModal(false);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const buffer = await file.arrayBuffer();
    setImportedBuffer(buffer);
    const detection = detectHeadersFromWorkbook(buffer);
    setDetectionResult(detection);

    setMapping({
      id: 'custom_map',
      templateName: file.name,
      docNameCol: detection.headers[detection.docNameIndex] || '',
      categoryCol: detection.headers[detection.categoryIndex] || '',
      statusCol: detection.headers[detection.statusIndex] || '',
      dueDateCol: detection.headers[detection.dueDateIndex] || '',
      remarksCol: detection.headers[detection.remarksIndex] || '',
      periodCol: detection.headers[detection.periodIndex] || '',
    });

    setShowImportModal(true);
  };

  const handleApplyImport = async () => {
    if (!importedBuffer) return;
    const parsedItems = parseRowsWithMapping(activeCase.id, importedBuffer, mapping, activeCase.period);
    await onSaveItems([...parsedItems, ...documentItems]);
    setShowImportModal(false);
    alert(`Successfully imported ${parsedItems.length} document items using your custom Excel columns!`);
  };

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full bg-[#F8FAFC]">
      <div className="bg-white rounded-2xl p-5 border border-gray-200 shadow-2xs flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-amber-50 text-amber-700 rounded-xl border border-amber-200">
            <ListTodo className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900">
              CA Firm Document & Client Data Tracker
            </h1>
            <p className="text-xs text-gray-500">
              Track portal reports, vendor declarations (Circular 183), invoices, and client follow-ups with Excel auto-mapping.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={handleFileSelect}
            className="hidden"
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-xl text-xs font-bold transition-all shadow-2xs cursor-pointer"
          >
            <Upload className="w-4 h-4 text-amber-600" />
            <span>Import Firm Excel/CSV</span>
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#4338CA] hover:bg-[#3730A3] text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add Document Item</span>
          </button>

          <button
            onClick={() => exportDocumentTrackerToExcel(activeClient.legalName, activeClient.gstin, activeCase.noticeNumber, documentItems)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>Export Excel (.xlsx)</span>
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-gray-500 mr-2 flex items-center gap-1">
          <Filter className="w-3.5 h-3.5" /> Filter:
        </span>
        {['ALL', 'PENDING', 'RECEIVED', 'PARTLY RECEIVED', 'CLARIFICATION REQUIRED'].map((status) => {
          const isSel = statusFilter === status;
          return (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                isSel
                  ? 'bg-[#4338CA] text-white shadow-2xs'
                  : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {status}
            </button>
          );
        })}
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-2xs">
        <table className="w-full text-left text-xs">
          <thead className="bg-gray-50 text-gray-600 border-b border-gray-200 uppercase text-[10px] font-bold tracking-wider">
            <tr>
              <th className="px-4 py-3">Document / Information Required</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Period</th>
              <th className="px-4 py-3">Target Due Date</th>
              <th className="px-4 py-3 text-center">Status</th>
              <th className="px-4 py-3">Remarks / Follow-up Action</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredItems.map((item) => {
              return (
                <tr key={item.id} className="hover:bg-gray-50/80 transition-colors">
                  <td className="px-4 py-3 font-bold text-gray-900">{item.docName}</td>
                  <td className="px-4 py-3 text-gray-600">{item.category}</td>
                  <td className="px-4 py-3 text-gray-500">{item.period || '-'}</td>
                  <td className="px-4 py-3 font-bold text-red-600">{item.dueDate}</td>
                  <td className="px-4 py-3 text-center">
                    <select
                      value={item.status}
                      onChange={(e) => handleUpdateStatus(item, e.target.value as DocumentStatus)}
                      className={`text-[10px] font-bold px-2 py-1 rounded-full border cursor-pointer ${
                        item.status === 'Received' || item.status === 'Completed'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                          : item.status === 'Partly Received'
                          ? 'bg-blue-50 text-blue-800 border-blue-300'
                          : item.status === 'Clarification Required'
                          ? 'bg-indigo-50 text-indigo-800 border-indigo-300'
                          : 'bg-amber-50 text-amber-800 border-amber-300'
                      }`}
                    >
                      <option value="Pending">Pending</option>
                      <option value="Partly Received">Partly Received</option>
                      <option value="Received">Received</option>
                      <option value="Clarification Required">Clarification Required</option>
                      <option value="Completed">Completed</option>
                    </select>
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-[11px] max-w-xs">{item.remarks || '-'}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => onDeleteItem(item.id)}
                      className="p-1 hover:bg-red-50 rounded text-red-600 transition-colors cursor-pointer"
                      title="Delete item"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
              <h2 className="text-sm font-bold text-gray-900">Add Document Request Item</h2>
              <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600 cursor-pointer">
                ✕
              </button>
            </div>

            <form onSubmit={handleAddItem} className="p-6 space-y-3 text-xs">
              <div>
                <label className="block font-bold text-gray-700 mb-1">Document Name *</label>
                <input
                  type="text"
                  required
                  value={newDocName}
                  onChange={(e) => setNewDocName(e.target.value)}
                  placeholder="e.g. GSTR-2B Oct-Dec Excel Reports"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-[#4338CA]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Category</label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-[#4338CA]"
                  >
                    <option value="Portal Report">Portal Report</option>
                    <option value="Invoices">Purchase / Sales Invoices</option>
                    <option value="Vendor Documents">Vendor Self-Declarations (Cir 183)</option>
                    <option value="Ledger">Books & Ledgers</option>
                    <option value="Vehicle / RC">Vehicle RC / Logistics</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Target Due Date</label>
                  <input
                    type="date"
                    value={newDueDate}
                    onChange={(e) => setNewDueDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-[#4338CA]"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-gray-700 mb-1">Remarks / Note for Client</label>
                <textarea
                  rows={2}
                  value={newRemarks}
                  onChange={(e) => setNewRemarks(e.target.value)}
                  placeholder="e.g. Download from GST portal for FY 2022-23"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-[#4338CA]"
                />
              </div>

              <div className="pt-3 border-t border-gray-200 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-bold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-[#4338CA] text-white font-bold rounded-lg hover:bg-[#3730A3] transition-all cursor-pointer shadow-xs"
                >
                  Save Item
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showImportModal && detectionResult && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                <h2 className="text-sm font-bold text-gray-900">Map Custom Excel / CSV Tracker Columns</h2>
              </div>
              <button onClick={() => setShowImportModal(false)} className="text-gray-400 hover:text-gray-600 cursor-pointer">
                ✕
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <p className="text-gray-600">
                The app automatically detected your spreadsheet headers. Confirm or adjust the column mappings below:
              </p>

              <div className="grid grid-cols-2 gap-3 bg-gray-50 p-4 rounded-xl border border-gray-200">
                <div>
                  <label className="block font-bold text-gray-700 mb-1">Document Name Column *</label>
                  <select
                    value={mapping.docNameCol}
                    onChange={(e) => setMapping({ ...mapping, docNameCol: e.target.value })}
                    className="w-full px-3 py-1.5 border rounded-lg bg-white"
                  >
                    {detectionResult.headers.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Category Column</label>
                  <select
                    value={mapping.categoryCol}
                    onChange={(e) => setMapping({ ...mapping, categoryCol: e.target.value })}
                    className="w-full px-3 py-1.5 border rounded-lg bg-white"
                  >
                    <option value="">-- None --</option>
                    {detectionResult.headers.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Status Column</label>
                  <select
                    value={mapping.statusCol}
                    onChange={(e) => setMapping({ ...mapping, statusCol: e.target.value })}
                    className="w-full px-3 py-1.5 border rounded-lg bg-white"
                  >
                    <option value="">-- None --</option>
                    {detectionResult.headers.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Target Due Date Column</label>
                  <select
                    value={mapping.dueDateCol}
                    onChange={(e) => setMapping({ ...mapping, dueDateCol: e.target.value })}
                    className="w-full px-3 py-1.5 border rounded-lg bg-white"
                  >
                    <option value="">-- None --</option>
                    {detectionResult.headers.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Remarks Column</label>
                  <select
                    value={mapping.remarksCol}
                    onChange={(e) => setMapping({ ...mapping, remarksCol: e.target.value })}
                    className="w-full px-3 py-1.5 border rounded-lg bg-white"
                  >
                    <option value="">-- None --</option>
                    {detectionResult.headers.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-gray-700 mb-1">Period Column</label>
                  <select
                    value={mapping.periodCol}
                    onChange={(e) => setMapping({ ...mapping, periodCol: e.target.value })}
                    className="w-full px-3 py-1.5 border rounded-lg bg-white"
                  >
                    <option value="">-- None --</option>
                    {detectionResult.headers.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-3 border-t border-gray-200 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-bold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleApplyImport}
                  className="px-5 py-2 bg-emerald-600 text-white font-bold rounded-lg hover:bg-emerald-700 transition-all cursor-pointer shadow-xs"
                >
                  Import Rows with This Template
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
