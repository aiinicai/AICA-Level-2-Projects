import React, { useState } from 'react';
import {
  FolderArchive,
  Upload,
  Search,
  FileText,
  Download,
  Eye,
  Trash2,
  CheckCircle2,
  FileSpreadsheet,
  X
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { DocumentRecord } from '../../types';
import { formatDate } from '../../utils/formatters';

export const DocumentsView: React.FC = () => {
  const { documents, customers, currentUser } = useApp();
  const [docList, setDocList] = useState<DocumentRecord[]>(documents);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('All');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<DocumentRecord | null>(null);

  const canEdit = currentUser.role !== 'Viewer';

  const filteredDocs = docList.filter(d => {
    const matchSearch =
      d.fileName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (d.customerName && d.customerName.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (d.invoiceNumber && d.invoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchType = typeFilter === 'All' || d.type === typeFilter;
    return matchSearch && matchType;
  });

  const handleUpload = (newDoc: Omit<DocumentRecord, 'id' | 'uploadedAt'>) => {
    const created: DocumentRecord = {
      ...newDoc,
      id: `doc-${Date.now()}`,
      uploadedAt: new Date().toISOString()
    };
    setDocList(prev => [created, ...prev]);
    setIsUploadModalOpen(false);
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Delete this document?')) {
      setDocList(prev => prev.filter(d => d.id !== id));
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Financial Documents & Tax Filings</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Store and audit customer invoices, bank statements, TRACES Form 26AS files, and GSTR-1 returns.
          </p>
        </div>
        {canEdit && (
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="px-3.5 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Upload className="w-4 h-4" />
            <span>Upload Document</span>
          </button>
        )}
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-white p-4 rounded-xl border border-slate-200 text-xs">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search documents by file name, customer, or invoice number..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600 bg-slate-50/50"
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="font-semibold text-slate-700">Type:</label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="p-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-700"
          >
            <option value="All">All Types</option>
            <option value="Invoice">Invoices</option>
            <option value="Bank Statement">Bank Statements</option>
            <option value="26AS">Form 26AS</option>
            <option value="GSTR-1">GSTR-1</option>
            <option value="Tax Challan">Tax Challans</option>
          </select>
        </div>
      </div>

      {/* Document Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDocs.map((doc) => (
          <div
            key={doc.id}
            className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <span className="px-2 py-0.5 bg-slate-100 rounded text-[10px] font-bold text-slate-700">
                  {doc.type}
                </span>
              </div>

              <h4 className="font-bold text-slate-900 text-xs truncate" title={doc.fileName}>
                {doc.fileName}
              </h4>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {doc.customerName || 'Company Internal'} {doc.invoiceNumber ? `• ${doc.invoiceNumber}` : ''}
              </p>
              <p className="text-[10px] text-slate-400 mt-1 font-mono">
                Uploaded {formatDate(doc.uploadedAt)}
              </p>
            </div>

            <div className="pt-3 mt-3 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-[10px] text-slate-400 font-mono">PDF / XLSX</span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPreviewDoc(doc)}
                  className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded"
                  title="Preview"
                >
                  <Eye className="w-4 h-4" />
                </button>
                <button
                  onClick={() => alert(`Downloading ${doc.fileName}...`)}
                  className="p-1.5 text-slate-500 hover:text-blue-700 hover:bg-blue-50 rounded"
                  title="Download"
                >
                  <Download className="w-4 h-4" />
                </button>
                {canEdit && (
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Upload Document Modal */}
      {isUploadModalOpen && (
        <UploadDocModal
          customers={customers}
          onClose={() => setIsUploadModalOpen(false)}
          onUpload={handleUpload}
        />
      )}

      {/* Preview Simulator Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden p-6 space-y-4 text-center">
            <FileText className="w-12 h-12 text-emerald-600 mx-auto" />
            <h3 className="font-bold text-slate-900 text-sm">{previewDoc.fileName}</h3>
            <p className="text-xs text-slate-500">
              Type: {previewDoc.type} • Associated Party: {previewDoc.customerName || 'General'}
            </p>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-left text-xs font-mono text-slate-600 space-y-1">
              <p>File Hash: SHA256-8a9d19c02b34...</p>
              <p>Storage: Secure Cloud Bucket (Encrypted at Rest)</p>
              <p>Verification: Digitally Signed with FinRecon Audit Seal</p>
            </div>
            <button
              onClick={() => setPreviewDoc(null)}
              className="px-6 py-2 bg-slate-900 text-white text-xs font-bold rounded-lg shadow-xs"
            >
              Close Preview
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

interface UploadDocModalProps {
  customers: any[];
  onClose: () => void;
  onUpload: (data: Omit<DocumentRecord, 'id' | 'uploadedAt'>) => void;
}

const UploadDocModal: React.FC<UploadDocModalProps> = ({ customers, onClose, onUpload }) => {
  const [fileName, setFileName] = useState('');
  const [type, setType] = useState<any>('Invoice');
  const [customerId, setCustomerId] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileName.trim()) return;

    const cust = customers.find(c => c.id === customerId);

    onUpload({
      fileName: fileName.trim(),
      fileSize: '1.2 MB',
      type,
      customerId: cust?.id,
      customerName: cust?.name,
      invoiceNumber: invoiceNumber.trim() || undefined,
      uploadedBy: 'Finance User',
      fileUrl: '#'
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-sm">Upload Financial Document</h3>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          <div>
            <label className="font-semibold text-slate-700 block mb-1">Document Title / File Name *</label>
            <input
              type="text"
              required
              value={fileName}
              onChange={e => setFileName(e.target.value)}
              placeholder="e.g. Form_26AS_Q1_2026.pdf"
              className="w-full p-2 rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
            />
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">Document Type *</label>
            <select
              value={type}
              onChange={e => setType(e.target.value as any)}
              className="w-full p-2 rounded-lg border border-slate-200 bg-white"
            >
              <option value="Invoice">Customer Invoice</option>
              <option value="Bank Statement">Bank Statement</option>
              <option value="26AS">Form 26AS / AIS File</option>
              <option value="GSTR-1">GSTR-1 Filing Return</option>
              <option value="Tax Challan">Advance Tax / TDS Challan</option>
            </select>
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">Associated Customer (Optional)</label>
            <select
              value={customerId}
              onChange={e => setCustomerId(e.target.value)}
              className="w-full p-2 rounded-lg border border-slate-200 bg-white"
            >
              <option value="">-- None / General Company File --</option>
              {customers.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="font-semibold text-slate-700 block mb-1">Invoice Number (Optional)</label>
            <input
              type="text"
              value={invoiceNumber}
              onChange={e => setInvoiceNumber(e.target.value)}
              placeholder="e.g. INV-2026-001"
              className="w-full p-2 font-mono rounded-lg border border-slate-200"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100">
              Cancel
            </button>
            <button type="submit" className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold shadow-xs">
              Upload Document
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
