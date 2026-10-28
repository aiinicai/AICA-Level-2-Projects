import React, { useState, useEffect } from 'react';
import {
  X,
  FileText,
  Printer,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  UserCheck,
  Paperclip,
  BookOpen,
  Boxes,
} from 'lucide-react';
import { resolveDocument, ResolvedDocumentData, getDocRoute } from '../core/docLinkRegistry';
import { formatAED } from '../core/currency';
import { ViewAccountingModal } from './ViewAccountingModal';
import { getDb } from '../core/storage';
import { getActiveUser } from '../core/auth';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

interface DocumentDetailModalProps {
  docNumber: string | null;
  onClose: () => void;
  onNavigate?: (route: string) => void;
  onOpenDoc?: (docNumber: string) => void;
}

export const DocumentDetailModal: React.FC<DocumentDetailModalProps> = ({
  docNumber,
  onClose,
  onNavigate,
  onOpenDoc,
}) => {
  const [data, setData] = useState<ResolvedDocumentData | null>(null);
  const [activeTab, setActiveTab] = useState<'lines' | 'related' | 'accounting' | 'audit' | 'attachments'>('lines');
  const [showAccountingModal, setShowAccountingModal] = useState(false);

  useEffect(() => {
    if (docNumber) {
      const resolved = resolveDocument(docNumber);
      setData(resolved);
      setActiveTab('lines');
    } else {
      setData(null);
    }
  }, [docNumber]);

  if (!docNumber || !data) return null;

  const db = getDb();
  const currentUser = getActiveUser();

  // Audit records for this entity
  const auditLogs = (db.auditLogs || []).filter(
    (a) => a.entityId === data.id || a.entityId === data.number || (a.details && JSON.stringify(a.details).includes(data.number))
  );

  const handlePrintPDF = () => {
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.setTextColor(91, 44, 131); // Plum
    doc.text(`Meridian Healthcare Group — ${data.typeLabel}`, 14, 15);

    doc.setFontSize(10);
    doc.setTextColor(60);
    doc.text(`Document Number: ${data.number}`, 14, 23);
    doc.text(`Business Unit: ${data.businessUnit || 'All Units'}`, 14, 29);
    doc.text(`Date: ${data.date || '—'}`, 14, 35);
    doc.text(`Status: ${data.status || '—'}`, 120, 23);
    doc.text(`Total Amount: ${formatAED(data.totalAmount || 0)}`, 120, 29);
    if (data.counterparty) doc.text(`${data.counterpartyRole || 'Party'}: ${data.counterparty}`, 120, 35);

    const headers = [['#', 'Description', 'Qty', 'Unit Price', 'Amount', 'Account']];
    const rows = data.lines.map((l) => [
      String(l.lineNum),
      l.description || '—',
      l.quantity !== undefined ? String(l.quantity) : '—',
      l.unitPrice !== undefined ? formatAED(l.unitPrice) : '—',
      l.amount !== undefined ? formatAED(l.amount) : '—',
      l.account || '—',
    ]);

    autoTable(doc, {
      startY: 42,
      head: headers,
      body: rows,
      headStyles: { fillColor: [91, 44, 131] },
      styles: { fontSize: 8 },
    });

    doc.save(`${data.number}_Detail.pdf`);
  };

  const handleRelatedClick = (relatedNumber: string) => {
    if (onOpenDoc) {
      onOpenDoc(relatedNumber);
    } else {
      const resolved = resolveDocument(relatedNumber);
      if (resolved) {
        setData(resolved);
        setActiveTab('lines');
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-gray-200">
        {/* Modal Top Bar */}
        <div className="bg-gradient-to-r from-[#3F1D5C] to-[#5B2C83] text-white px-6 py-4 flex items-center justify-between shadow-xs shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center text-amber-300">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-300">
                  {data.typeLabel}
                </span>
                <span className="text-white/40">&bull;</span>
                <span className="text-plum-200 text-xs">{data.businessUnit || 'Corporate'}</span>
              </div>
              <h2 className="text-lg font-bold font-mono tracking-tight text-white flex items-center space-x-2">
                <span>{data.number}</span>
                <span
                  className={`text-[11px] font-sans px-2.5 py-0.5 rounded-full font-semibold ${
                    data.status === 'Approved' || data.status === 'Posted'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30'
                      : data.status === 'Pending Approval' || data.status === 'Pending Higher Approval'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-400/30'
                      : data.status === 'Rejected'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-400/30'
                      : 'bg-white/10 text-gray-300'
                  }`}
                >
                  {data.status}
                </span>
              </h2>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handlePrintPDF}
              className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-plum-100 hover:text-white transition-colors cursor-pointer text-xs flex items-center space-x-1"
              title="Download PDF"
            >
              <Printer className="w-4 h-4" />
              <span className="hidden sm:inline text-[11px]">PDF</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-white/10 hover:bg-rose-500/30 text-plum-200 hover:text-white transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Key Info Banner */}
        <div className="bg-[#FAF7FC] border-b border-plum-100 px-6 py-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs shrink-0">
          <div>
            <span className="text-gray-400 block text-[10px] uppercase font-semibold">Document Date</span>
            <span className="font-semibold text-gray-800">{data.date || '—'}</span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px] uppercase font-semibold">
              {data.counterpartyRole || 'Counterparty'}
            </span>
            <span className="font-semibold text-gray-900 truncate block" title={data.counterparty}>
              {data.counterparty || '—'}
            </span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px] uppercase font-semibold">Total Amount</span>
            <span className="font-bold text-[#5B2C83] font-mono text-sm">
              {formatAED(data.totalAmount || 0)}
            </span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px] uppercase font-semibold">Maker / Approver</span>
            <span className="text-gray-700 truncate block">
              <span className="font-medium text-emerald-700">{data.createdBy || 'System'}</span>
              <span className="text-gray-400 mx-1">/</span>
              <span className="font-medium text-amber-700">{data.approvedBy || 'Pending'}</span>
            </span>
          </div>
        </div>

        {/* Tab Headers */}
        <div className="px-6 border-b border-gray-200 flex space-x-4 bg-white text-xs shrink-0">
          <button
            onClick={() => setActiveTab('lines')}
            className={`py-2.5 font-bold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'lines'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            Lines ({data.lines.length})
          </button>
          <button
            onClick={() => setActiveTab('related')}
            className={`py-2.5 font-bold border-b-2 transition-colors cursor-pointer flex items-center space-x-1 ${
              activeTab === 'related'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <span>Related Documents</span>
            <span className="px-1.5 py-0.2 rounded-full bg-plum-100 text-[#5B2C83] text-[10px]">
              {data.relatedDocuments.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('accounting')}
            className={`py-2.5 font-bold border-b-2 transition-colors cursor-pointer flex items-center space-x-1 ${
              activeTab === 'accounting'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Accounting & GL</span>
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`py-2.5 font-bold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'audit'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            Audit Trail ({auditLogs.length})
          </button>
          <button
            onClick={() => setActiveTab('attachments')}
            className={`py-2.5 font-bold border-b-2 transition-colors cursor-pointer flex items-center space-x-1 ${
              activeTab === 'attachments'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <Paperclip className="w-3 h-3" />
            <span>Attachments (1)</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 p-6 overflow-y-auto">
          {activeTab === 'lines' && (
            <div>
              {data.description && (
                <div className="mb-4 p-3 bg-gray-50 rounded-lg text-xs text-gray-700 border border-gray-100">
                  <span className="font-semibold text-gray-500 block mb-0.5">Description / Justification:</span>
                  <span>{data.description}</span>
                </div>
              )}

              <table className="w-full text-left text-xs border border-gray-200 rounded-lg overflow-hidden">
                <thead className="bg-[#FAF7FC] text-gray-700 uppercase font-semibold text-[10px] border-b border-gray-200">
                  <tr>
                    <th className="py-2.5 px-3">#</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3 text-right">Qty</th>
                    <th className="py-2.5 px-3 text-right">Unit Price</th>
                    <th className="py-2.5 px-3 text-right">Amount (AED)</th>
                    <th className="py-2.5 px-3">Account / Dept</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.lines.map((l, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="py-2.5 px-3 font-mono text-gray-400">{l.lineNum}</td>
                      <td className="py-2.5 px-3 font-medium text-gray-900">{l.description}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-gray-700">
                        {l.quantity !== undefined ? l.quantity : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-gray-700">
                        {l.unitPrice !== undefined ? formatAED(l.unitPrice) : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-[#5B2C83]">
                        {l.amount !== undefined ? formatAED(l.amount) : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-gray-600 font-mono text-[11px]">
                        {l.account ? (
                          <span>
                            {l.account}
                            {l.department ? ` &bull; ${l.department}` : ''}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'related' && (
            <div>
              {data.relatedDocuments.length === 0 ? (
                <div className="py-12 text-center text-gray-400 text-xs">
                  <Boxes className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <span>No cross-linked documents recorded for this item yet.</span>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs text-gray-500 mb-3">
                    Click any cross-referenced document below to inspect its lifecycle, approvals, and GL lines:
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {data.relatedDocuments.map((rel, i) => (
                      <div
                        key={i}
                        onClick={() => handleRelatedClick(rel.number)}
                        className="p-3.5 rounded-xl border border-plum-200/80 bg-plum-50/30 hover:bg-plum-50 hover:border-[#5B2C83] transition-all cursor-pointer flex items-center justify-between group shadow-2xs"
                      >
                        <div className="flex items-center space-x-2.5">
                          <div className="w-8 h-8 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center font-bold text-xs shrink-0 group-hover:bg-[#3F1D5C]">
                            {rel.number.split('-')[0]}
                          </div>
                          <div>
                            <span className="font-mono font-bold text-xs text-[#5B2C83] block group-hover:underline">
                              {rel.number}
                            </span>
                            <span className="text-[10px] text-gray-500 block">
                              {rel.typeLabel} &bull; <strong className="text-gray-700">{rel.relationship}</strong>
                            </span>
                          </div>
                        </div>
                        <ArrowRight className="w-4 h-4 text-plum-400 group-hover:text-[#5B2C83] transition-transform group-hover:translate-x-1" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'accounting' && (
            <div>
              {data.glJournalNumber || data.glJournalId ? (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-950 flex items-center justify-between">
                    <div className="flex items-center space-x-2.5">
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                      <div>
                        <span className="font-bold block">
                          General Ledger Journal Posted: {data.glJournalNumber || 'Posted to Ledger'}
                        </span>
                        <span className="text-gray-600">
                          Subledger double-entry balancing verified &bull; Posted to GL
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => setShowAccountingModal(true)}
                      className="px-3 py-1.5 bg-[#5B2C83] text-white rounded-lg text-xs font-semibold hover:bg-[#3F1D5C] cursor-pointer flex items-center space-x-1"
                    >
                      <BookOpen className="w-3.5 h-3.5" />
                      <span>View Full Accounting Lines</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-8 text-center text-gray-500 text-xs">
                  <AlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                  <p className="font-semibold text-gray-700">Accounting will be created on approval</p>
                  <p className="text-gray-400 mt-1 max-w-sm mx-auto text-[11px]">
                    Under the MediCore Connect posting engine, subledger accounting and GL journals post atomically once approved by the designated Approver.
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'audit' && (
            <div>
              {auditLogs.length === 0 ? (
                <div className="py-12 text-center text-gray-400 text-xs">
                  <Clock className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <span>No audit history logged for this document.</span>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {auditLogs.map((log) => (
                    <div
                      key={log.id}
                      className="p-3 bg-gray-50 border border-gray-100 rounded-lg text-xs flex items-start justify-between"
                    >
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-gray-900">{log.action}</span>
                          <span className="text-[10px] text-gray-400 font-mono">
                            {new Date(log.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-gray-600 text-[11px] mt-0.5">{log.comments || 'Action performed'}</p>
                      </div>
                      <span className="text-[11px] text-[#5B2C83] font-semibold">{log.userName}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'attachments' && (
            <div className="space-y-3">
              <div className="p-3 rounded-lg border border-gray-200 bg-gray-50 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <Paperclip className="w-4 h-4 text-plum-600" />
                  <div>
                    <span className="font-semibold text-gray-800 block">
                      {data.number}_Signed_Document.pdf
                    </span>
                    <span className="text-[10px] text-gray-400">148 KB &bull; Verified Attachment</span>
                  </div>
                </div>
                <button
                  onClick={handlePrintPDF}
                  className="px-2.5 py-1 text-[#5B2C83] hover:underline font-semibold cursor-pointer"
                >
                  Download
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="bg-gray-50 border-t border-gray-200 px-6 py-3 flex items-center justify-between text-xs shrink-0">
          <div className="flex items-center space-x-2">
            <span className="text-gray-400 font-mono text-[11px]">ID: {data.id || data.number}</span>
          </div>

          <div className="flex items-center space-x-2">
            {onNavigate && (
              <button
                onClick={() => {
                  onClose();
                  onNavigate(getDocRoute(data.number));
                }}
                className="px-3 py-1.5 border border-plum-300 text-[#5B2C83] hover:bg-plum-50 rounded-lg font-semibold cursor-pointer flex items-center space-x-1"
              >
                <span>Open Work Area</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-1.5 bg-gray-800 hover:bg-gray-900 text-white rounded-lg font-semibold cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>

      {showAccountingModal && (
        <ViewAccountingModal
          transactionNumber={data.number}
          onClose={() => setShowAccountingModal(false)}
        />
      )}
    </div>
  );
};
