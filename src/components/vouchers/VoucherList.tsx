import React, { useState, useMemo } from 'react';
import {
  FileText,
  Search,
  Filter,
  Plus,
  Eye,
  Edit,
  Copy,
  ArrowRightLeft,
  Download,
  Printer,
  Trash2,
  CheckCircle2,
  Clock,
  DollarSign,
  Calendar,
  Sparkles,
  ShieldCheck,
  Building2
} from 'lucide-react';
import { Voucher, VoucherType, VoucherStatus, CompanyProfile } from '../../types';
import { PDFEngine } from '../../services/pdfEngine';
import { StorageService } from '../../services/storage';

interface VoucherListProps {
  vouchers: Voucher[];
  companyProfile: CompanyProfile;
  onCreateVoucher: (type?: VoucherType) => void;
  onEditVoucher: (voucher: Voucher) => void;
  onPreviewVoucher: (voucher: Voucher) => void;
  onDuplicateVoucher: (voucher: Voucher) => void;
  onConvertVoucher: (voucher: Voucher, targetType: VoucherType) => void;
  onDeleteVoucher: (id: string) => void;
  onStatusChange: (id: string, newStatus: VoucherStatus) => void;
  onOpenAIScan: () => void;
}

export const VoucherList: React.FC<VoucherListProps> = ({
  vouchers,
  companyProfile,
  onCreateVoucher,
  onEditVoucher,
  onPreviewVoucher,
  onDuplicateVoucher,
  onConvertVoucher,
  onDeleteVoucher,
  onStatusChange,
  onOpenAIScan,
}) => {
  const storage = StorageService.getInstance();
  const currentUser = storage.getCurrentUser();
  const isClientPortal = currentUser.role === 'client_portal';
  const isProcurement = currentUser.role === 'procurement';

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [convertTargetVoucher, setConvertTargetVoucher] = useState<Voucher | null>(null);

  const typeLabels: Record<VoucherType, { label: string; badgeColor: string }> = {
    PO: { label: 'Purchase Order', badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
    LPO: { label: 'Local PO (LPO)', badgeColor: 'bg-purple-50 text-purple-700 border-purple-200' },
    PROFORMA: { label: 'Proforma Invoice', badgeColor: 'bg-amber-50 text-amber-700 border-amber-200' },
    SALES: { label: 'Tax Invoice', badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    DELIVERY: { label: 'Delivery Note', badgeColor: 'bg-blue-50 text-blue-700 border-blue-200' },
    GATE_PASS: { label: 'Gate Pass', badgeColor: 'bg-teal-50 text-teal-700 border-teal-200' },
  };

  const filteredVouchers = useMemo(() => {
    return vouchers.filter((v) => {
      const matchSearch =
        v.docNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
        v.clientName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        v.clientTin.includes(searchTerm);
      const matchType = selectedType === 'ALL' || v.type === selectedType;
      const matchStatus = selectedStatus === 'ALL' || v.status === selectedStatus;
      return matchSearch && matchType && matchStatus;
    });
  }, [vouchers, searchTerm, selectedType, selectedStatus]);

  // Metric Totals
  const totalSalesTZS = useMemo(() => {
    return vouchers
      .filter((v) => v.type === 'SALES' && v.currency === 'TZS')
      .reduce((sum, v) => sum + v.finalGrandTotal, 0);
  }, [vouchers]);

  const totalSalesUSD = useMemo(() => {
    return vouchers
      .filter((v) => v.type === 'SALES' && v.currency === 'USD')
      .reduce((sum, v) => sum + v.finalGrandTotal, 0);
  }, [vouchers]);

  const pendingDraftsCount = useMemo(() => {
    return vouchers.filter((v) => v.status === 'draft').length;
  }, [vouchers]);

  const handleExportPDF = async (voucher: Voucher) => {
    try {
      const pdfBytes = await PDFEngine.generateVoucherPDF(voucher, companyProfile);
      PDFEngine.downloadFile(
        pdfBytes,
        `${voucher.docNumber}_${voucher.clientName.replace(/\s+/g, '_')}.pdf`
      );
    } catch (e: any) {
      alert(`Error generating PDF: ${e.message}`);
    }
  };

  return (
    <div id="vouchers-list-screen" className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Client Portal Specialized Header Banner */}
      {isClientPortal && (
        <div className="bg-gradient-to-r from-purple-900 to-indigo-900 text-white rounded-2xl p-5 shadow-xs flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
              <ShieldCheck className="w-6 h-6 text-purple-200" />
            </div>
            <div>
              <h3 className="font-bold text-sm">Client Portal — Authorized Invoices & Statements</h3>
              <p className="text-xs text-purple-200">
                You are viewing finalized tax invoices and proforma quotations issued by <span className="font-semibold text-white">{companyProfile.name}</span>.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Top Metrics Cards (Hidden for Client Portal for confidentiality) */}
      {!isClientPortal && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <p className="text-xs text-slate-500 font-medium">Total Invoiced (TZS)</p>
            <p className="text-lg font-bold text-slate-900 mt-1 font-mono">
              TZS {totalSalesTZS.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </p>
            <p className="text-[11px] text-emerald-600 font-medium mt-0.5">Commercial Tax Invoices</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <p className="text-xs text-slate-500 font-medium">Total Invoiced (USD)</p>
            <p className="text-lg font-bold text-slate-900 mt-1 font-mono">
              ${totalSalesUSD.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            <p className="text-[11px] text-blue-600 font-medium mt-0.5">Foreign / Port Transit Invoices</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <p className="text-xs text-slate-500 font-medium">Draft Documents</p>
            <p className="text-lg font-bold text-amber-600 mt-1 font-mono">{pendingDraftsCount}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Pending finalization</p>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <p className="text-xs text-slate-500 font-medium">Total Records</p>
            <p className="text-lg font-bold text-slate-900 mt-1 font-mono">{vouchers.length}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">PO, LPO, PI, Invoices, Delivery</p>
          </div>
        </div>
      )}

      {/* Control Bar: Search, Filters & Action Buttons */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by doc number (INV-2026-0001), client, TIN..."
            className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
          />
        </div>

        {/* Filters & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 bg-white focus:ring-2 focus:ring-blue-500/20"
          >
            <option value="ALL">All Document Types</option>
            <option value="SALES">Tax Invoice (INV)</option>
            <option value="PROFORMA">Proforma Invoice (PI)</option>
            <option value="LPO">Local Purchase Order (LPO)</option>
            <option value="PO">Purchase Order (PO)</option>
            <option value="DELIVERY">Delivery Note (DN)</option>
            <option value="GATE_PASS">Gate Pass (GP)</option>
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 bg-white focus:ring-2 focus:ring-blue-500/20"
          >
            <option value="ALL">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="finalized">Finalized</option>
            <option value="paid">Paid</option>
          </select>

          {/* AI Scan Button (internal users only) */}
          {!isClientPortal && (
            <button
              onClick={onOpenAIScan}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-semibold transition"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>AI OCR Scan</span>
            </button>
          )}

          {/* Create Button (internal users only) */}
          {!isClientPortal && (
            <button
              id="btn-create-voucher-main"
              onClick={() => onCreateVoucher(isProcurement ? 'LPO' : 'SALES')}
              className="flex items-center space-x-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white rounded-lg text-xs font-semibold shadow-xs transition"
            >
              <Plus className="w-4 h-4" />
              <span>{isProcurement ? 'Create LPO' : 'Create Document'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Vouchers Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-600 uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Doc Number</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Client / Vendor</th>
                <th className="py-3 px-4">Items</th>
                <th className="py-3 px-4 text-right">Grand Total</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filteredVouchers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    No documents match your filter criteria.
                  </td>
                </tr>
              ) : (
                filteredVouchers.map((voucher) => {
                  const typeConfig = typeLabels[voucher.type] || {
                    label: voucher.type,
                    badgeColor: 'bg-slate-100',
                  };
                  return (
                    <tr key={voucher.id} className="hover:bg-slate-50/80 transition">
                      {/* Doc Number */}
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">
                        {voucher.docNumber}
                      </td>

                      {/* Type Badge */}
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${typeConfig.badgeColor}`}
                        >
                          {typeConfig.label}
                        </span>
                      </td>

                      {/* Date */}
                      <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                        {voucher.docDate}
                      </td>

                      {/* Client */}
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 truncate max-w-xs">
                          {voucher.clientName}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono">
                          TIN: {voucher.clientTin || 'N/A'}
                        </div>
                      </td>

                      {/* Items count */}
                      <td className="py-3 px-4 text-slate-600">
                        {voucher.items.length} {voucher.items.length === 1 ? 'item' : 'items'}
                      </td>

                      {/* Grand Total */}
                      <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 whitespace-nowrap">
                        {voucher.type === 'GATE_PASS' ? (
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-sans">
                            {voucher.quantityUnit || 'Non-Financial'}
                          </span>
                        ) : (
                          `${voucher.currency} ${voucher.finalGrandTotal.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}`
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4 text-center">
                        {isClientPortal ? (
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                              voucher.status === 'paid'
                                ? 'bg-emerald-100 text-emerald-800'
                                : voucher.status === 'finalized'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-amber-100 text-amber-800'
                            }`}
                          >
                            {voucher.status}
                          </span>
                        ) : (
                          <select
                            value={voucher.status}
                            onChange={(e) =>
                              onStatusChange(voucher.id, e.target.value as VoucherStatus)
                            }
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border cursor-pointer ${
                              voucher.status === 'paid'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                                : voucher.status === 'finalized'
                                ? 'bg-blue-50 text-blue-700 border-blue-300'
                                : 'bg-amber-50 text-amber-700 border-amber-300'
                            }`}
                          >
                            <option value="draft">Draft</option>
                            <option value="finalized">Finalized</option>
                            <option value="paid">Paid</option>
                          </select>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end space-x-1">
                          {/* Preview & Print */}
                          <button
                            title="A4 Preview & Print"
                            onClick={() => onPreviewVoucher(voucher)}
                            className="p-1 text-slate-500 hover:text-blue-600 rounded hover:bg-slate-100 transition"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {/* Export PDF */}
                          <button
                            title="Export Vector PDF"
                            onClick={() => handleExportPDF(voucher)}
                            className="p-1 text-slate-500 hover:text-emerald-600 rounded hover:bg-slate-100 transition"
                          >
                            <Download className="w-4 h-4" />
                          </button>

                          {/* Internal-only actions */}
                          {!isClientPortal && (
                            <>
                              {/* Edit */}
                              <button
                                title="Edit Document"
                                onClick={() => onEditVoucher(voucher)}
                                className="p-1 text-slate-500 hover:text-indigo-600 rounded hover:bg-slate-100 transition"
                              >
                                <Edit className="w-4 h-4" />
                              </button>

                              {/* Duplicate */}
                              <button
                                title="Duplicate Document"
                                onClick={() => onDuplicateVoucher(voucher)}
                                className="p-1 text-slate-500 hover:text-purple-600 rounded hover:bg-slate-100 transition"
                              >
                                <Copy className="w-4 h-4" />
                              </button>

                              {/* Convert (e.g. Proforma -> Invoice) */}
                              <button
                                title="Convert Document Type"
                                onClick={() => setConvertTargetVoucher(voucher)}
                                className="p-1 text-slate-500 hover:text-amber-600 rounded hover:bg-slate-100 transition"
                              >
                                <ArrowRightLeft className="w-4 h-4" />
                              </button>

                              {/* Delete */}
                              <button
                                title="Delete"
                                onClick={() => {
                                  if (window.confirm(`Delete document ${voucher.docNumber}?`)) {
                                    onDeleteVoucher(voucher.id);
                                  }
                                }}
                                className="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-slate-100 transition"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Convert Document Type Modal */}
      {convertTargetVoucher && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-2xl border border-slate-200 space-y-4">
            <h3 className="font-bold text-sm text-slate-900">
              Convert Document Type — {convertTargetVoucher.docNumber}
            </h3>
            <p className="text-xs text-slate-600">
              Select the new commercial format to convert this voucher into. All line items, client details, and calculated totals will be transferred to a new document number.
            </p>

            <div className="grid grid-cols-1 gap-2 pt-2">
              {(['SALES', 'PROFORMA', 'DELIVERY', 'LPO', 'PO'] as VoucherType[])
                .filter((t) => t !== convertTargetVoucher.type)
                .map((targetT) => (
                  <button
                    key={targetT}
                    onClick={() => {
                      onConvertVoucher(convertTargetVoucher, targetT);
                      setConvertTargetVoucher(null);
                    }}
                    className="p-2.5 text-left border border-slate-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition text-xs font-semibold text-slate-800 flex items-center justify-between"
                  >
                    <span>Convert to {typeLabels[targetT].label}</span>
                    <ArrowRightLeft className="w-4 h-4 text-slate-400" />
                  </button>
                ))}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setConvertTargetVoucher(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
