import React, { useState, useMemo } from 'react';
import { Purchase, MetalType, BullionForm } from '../../types';
import {
  formatINR,
  formatGrams,
  formatDisplayDate,
} from '../../utils/formatters';
import { exportPurchasesToXLSX, generatePurchaseTemplateXLSX } from '../../utils/purchaseExcel';
import { syncLocalDataToSupabase } from '../../db/repository';
import { isSupabaseConfigured } from '../../services/supabaseClient';
import { AddEditPurchaseModal } from './AddEditPurchaseModal';
import { ImportPurchasesModal } from './ImportPurchasesModal';
import {
  Search,
  Plus,
  Upload,
  Download,
  Trash2,
  Edit2,
  RotateCcw,
  Undo2,
  FileSpreadsheet,
  Coins,
  CheckCircle2,
  AlertCircle,
  Archive,
  Eye,
  Lock,
  Cloud,
} from 'lucide-react';

interface PurchasesScreenProps {
  purchases: Purchase[];
  onSavePurchase: (purchase: Purchase) => void;
  onSoftDeletePurchase: (id: string) => void;
  onRestorePurchase: (id: string) => void;
  onPermanentDeletePurchase: (id: string) => void;
  onImportPurchases: (purchases: Purchase[], batchId: string) => void;
  onUndoLastBatch: () => void;
  lastBatchId: string | null;
  onLoadDemoData: () => void;
  isSuperUser?: boolean;
  onRequireAuth?: () => void;
}

export const PurchasesScreen: React.FC<PurchasesScreenProps> = ({
  purchases,
  onSavePurchase,
  onSoftDeletePurchase,
  onRestorePurchase,
  onPermanentDeletePurchase,
  onImportPurchases,
  onUndoLastBatch,
  lastBatchId,
  onLoadDemoData,
  isSuperUser = true,
  onRequireAuth,
}) => {
  const [search, setSearch] = useState('');
  const [metalFilter, setMetalFilter] = useState<'ALL' | MetalType>('ALL');
  const [formFilter, setFormFilter] = useState<'ALL' | BullionForm>('ALL');
  const [showTrash, setShowTrash] = useState(false);

  // Modal states
  const [isAddEditOpen, setIsAddEditOpen] = useState(false);
  const [editingPurchase, setEditingPurchase] = useState<Purchase | null>(null);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [syncNotice, setSyncNotice] = useState<{ success: boolean; message: string } | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);

  const handleSyncToCloud = async () => {
    if (!isSupabaseConfigured()) {
      setSyncNotice({
        success: false,
        message: 'Supabase credentials not configured. Please go to the Settings tab to enter your Supabase Project URL and Anon Key.',
      });
      return;
    }
    setIsSyncing(true);
    setSyncNotice(null);
    try {
      const res = await syncLocalDataToSupabase();
      setSyncNotice(res);
      if (res.success) {
        setTimeout(() => setSyncNotice(null), 5000);
      }
    } catch (err: any) {
      setSyncNotice({
        success: false,
        message: err.message || 'Sync failed',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  // Active / Trash partition
  const activePurchases = useMemo(
    () => purchases.filter((p) => !p.deleted),
    [purchases]
  );
  const deletedPurchases = useMemo(
    () => purchases.filter((p) => p.deleted),
    [purchases]
  );

  // Filtered view
  const currentList = showTrash ? deletedPurchases : activePurchases;

  const filteredPurchases = useMemo(() => {
    return currentList.filter((p) => {
      if (metalFilter !== 'ALL' && p.metal !== metalFilter) return false;
      if (formFilter !== 'ALL' && p.form !== formFilter) return false;
      if (search.trim()) {
        const query = search.toLowerCase();
        const matchSeller = p.seller.toLowerCase().includes(query);
        const matchInvoice = p.invoiceNumber.toLowerCase().includes(query);
        const matchId = p.id.toLowerCase().includes(query);
        const matchNotes = p.notes?.toLowerCase().includes(query) || false;
        if (!matchSeller && !matchInvoice && !matchId && !matchNotes) return false;
      }
      return true;
    });
  }, [currentList, metalFilter, formFilter, search]);

  // Export to Excel
  const handleExport = () => {
    if (activePurchases.length === 0) return;
    const buffer = exportPurchasesToXLSX(activePurchases);
    const blob = new Blob([buffer as any], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Bullion_Ledger_Purchases_${new Date().toISOString().split('T')[0]}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Download template
  const handleDownloadTemplate = () => {
    const buffer = generatePurchaseTemplateXLSX();
    const blob = new Blob([buffer as any], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Bullion_Ledger_Purchase_Template.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleOpenAdd = () => {
    if (!isSuperUser && onRequireAuth) {
      onRequireAuth();
      return;
    }
    setEditingPurchase(null);
    setIsAddEditOpen(true);
  };

  const handleEdit = (p: Purchase) => {
    if (!isSuperUser && onRequireAuth) {
      onRequireAuth();
      return;
    }
    setEditingPurchase(p);
    setIsAddEditOpen(true);
  };

  const handleOpenImport = () => {
    if (!isSuperUser && onRequireAuth) {
      onRequireAuth();
      return;
    }
    setIsImportOpen(true);
  };

  return (
    <div className="space-y-5">
      {/* Public Shared Link Banner */}
      {!isSuperUser && (
        <div className="bg-amber-50/70 border border-amber-200 text-amber-900 px-4 py-3 rounded-xl text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-[#B88B2A] shrink-0" />
            <span>
              <strong>Public Shared View:</strong> You are viewing stored purchases and live valuations in read-only mode.
              Sign in as Super User to record new purchases, import Excel files, or edit transactions.
            </span>
          </div>
          {onRequireAuth && (
            <button
              type="button"
              onClick={onRequireAuth}
              className="px-3 py-1 text-xs font-semibold text-[#B88B2A] bg-white border border-[#D4AF37]/50 rounded-lg hover:bg-stone-50 shrink-0 shadow-2xs flex items-center gap-1.5"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Super User Login</span>
            </button>
          )}
        </div>
      )}

      {/* Header & Main Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-stone-900 tracking-tight flex items-center gap-2">
            <span>Bullion Purchases</span>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 border border-stone-200">
              {activePurchases.length} lot(s)
            </span>
          </h2>
          <p className="text-xs text-stone-500">
            Recorded acquisitions of physical Gold and Silver with invoice-level cost tracking
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Template Download */}
          <button
            type="button"
            onClick={handleDownloadTemplate}
            className="px-2.5 py-1.5 text-xs font-medium text-stone-700 bg-white hover:bg-stone-50 border border-stone-200 rounded-lg shadow-2xs transition-colors flex items-center gap-1.5"
            title="Download formatted Excel template for bulk import"
          >
            <Download className="w-3.5 h-3.5 text-stone-500" />
            <span className="hidden sm:inline">XLSX</span> Template
          </button>

          {/* Import XLSX */}
          <button
            type="button"
            onClick={handleOpenImport}
            className="px-2.5 py-1.5 text-xs font-medium text-stone-700 bg-white hover:bg-stone-50 border border-stone-200 rounded-lg shadow-2xs transition-colors flex items-center gap-1.5"
            title="Import purchases from XLSX or CSV"
          >
            <Upload className="w-3.5 h-3.5 text-[#B88B2A]" />
            <span>Import</span>
          </button>

          {/* Export */}
          <button
            type="button"
            onClick={handleExport}
            disabled={activePurchases.length === 0}
            className={`px-2.5 py-1.5 text-xs font-medium rounded-lg border shadow-2xs transition-colors flex items-center gap-1.5 ${
              activePurchases.length > 0
                ? 'bg-white hover:bg-stone-50 text-stone-700 border-stone-200 cursor-pointer'
                : 'bg-stone-100 text-stone-400 border-stone-200 cursor-not-allowed'
            }`}
            title="Export all purchases to Excel (.xlsx)"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            <span>Export</span>
          </button>

          {/* Push to Supabase Cloud */}
          {activePurchases.length > 0 && (
            <button
              type="button"
              onClick={handleSyncToCloud}
              disabled={isSyncing}
              className="px-2.5 py-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 rounded-lg shadow-2xs transition-colors flex items-center gap-1.5 cursor-pointer"
              title="Push current local purchases directly to Supabase PostgreSQL cloud"
            >
              <Cloud className={`w-3.5 h-3.5 text-emerald-600 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>{isSyncing ? 'Syncing...' : 'Push to Cloud'}</span>
            </button>
          )}

          {/* Undo Last Batch */}
          {lastBatchId && (
            <button
              type="button"
              onClick={onUndoLastBatch}
              className="px-2.5 py-1.5 text-xs font-medium text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-300 rounded-lg shadow-2xs transition-colors flex items-center gap-1.5"
              title="Undo the last imported batch"
            >
              <Undo2 className="w-3.5 h-3.5 text-amber-700" />
              <span>Undo Import</span>
            </button>
          )}

          {/* Record Purchase CTA */}
          <button
            type="button"
            onClick={handleOpenAdd}
            className="px-3.5 py-1.5 text-xs font-semibold text-white bg-[#B88B2A] hover:bg-[#8E6B1D] rounded-lg shadow-2xs transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Record Purchase</span>
          </button>
        </div>
      </div>

      {/* Cloud Sync Notification Banner */}
      {syncNotice && (
        <div
          className={`p-3 rounded-xl text-xs flex items-center justify-between border ${
            syncNotice.success
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : 'bg-amber-50 text-amber-800 border-amber-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {syncNotice.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
            )}
            <span>{syncNotice.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setSyncNotice(null)}
            className="text-stone-400 hover:text-stone-700 font-bold ml-2 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-[#E7E2DA] shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Jeweller, Invoice #, Holding ID, or Notes..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-stone-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#B88B2A] bg-[#FAF7F2]/50"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={metalFilter}
            onChange={(e) => setMetalFilter(e.target.value as any)}
            className="text-xs px-2.5 py-1.5 border border-stone-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
          >
            <option value="ALL">All Metals</option>
            <option value="GOLD">Gold</option>
            <option value="SILVER">Silver</option>
          </select>

          <select
            value={formFilter}
            onChange={(e) => setFormFilter(e.target.value as any)}
            className="text-xs px-2.5 py-1.5 border border-stone-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
          >
            <option value="ALL">All Forms</option>
            <option value="VEDHANI">Vedhani</option>
            <option value="COIN">Coin</option>
            <option value="BAR">Bar</option>
          </select>

          {/* Trash toggle */}
          <button
            type="button"
            onClick={() => setShowTrash(!showTrash)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1.5 ${
              showTrash
                ? 'bg-rose-50 text-rose-800 border-rose-300 font-bold'
                : 'bg-white text-stone-600 border-stone-200 hover:bg-stone-50'
            }`}
          >
            <Trash2 className="w-3.5 h-3.5 text-stone-500" />
            <span>Trash ({deletedPurchases.length})</span>
          </button>
        </div>
      </div>

      {/* Main Table (Desktop & Tablet) */}
      <div className="hidden md:block bg-white rounded-xl border border-[#E7E2DA] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#FAF7F2] text-stone-700 border-b border-[#E7E2DA] font-semibold">
              <tr>
                <th className="py-2.5 px-3">Holding ID</th>
                <th className="py-2.5 px-3">Date</th>
                <th className="py-2.5 px-3">Jeweller / Seller</th>
                <th className="py-2.5 px-3">Invoice #</th>
                <th className="py-2.5 px-3">Metal / Form</th>
                <th className="py-2.5 px-3 text-right">Weight (g)</th>
                <th className="py-2.5 px-3 text-right">Rate (₹/g)</th>
                <th className="py-2.5 px-3 text-right">Bullion Value</th>
                <th className="py-2.5 px-3 text-right">Taxes Paid</th>
                <th className="py-2.5 px-3 text-right">Invested Cost</th>
                <th className="py-2.5 px-3 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {filteredPurchases.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-8 text-center text-stone-400">
                    {showTrash
                      ? 'No items currently in trash.'
                      : activePurchases.length === 0
                      ? 'No purchases recorded yet. Click "Record Purchase" or "Load Demo Portfolio".'
                      : 'No purchases match your filter criteria.'}
                  </td>
                </tr>
              ) : (
                filteredPurchases.map((p) => (
                  <tr key={p.id} className="hover:bg-stone-50/70 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-medium text-stone-700">
                      {p.id}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap text-stone-600">
                      {formatDisplayDate(p.purchaseDate)}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-stone-900">
                      {p.seller}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-stone-700">
                      {p.invoiceNumber}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 font-semibold text-[11px] px-1.5 py-0.5 rounded ${
                          p.metal === 'GOLD'
                            ? 'bg-[#FBF6E9] text-[#B88B2A]'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {p.metal} {p.purity}k • {p.form}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-stone-800">
                      {formatGrams(p.weightGrams)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-stone-600">
                      {formatINR(p.purchaseRate)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-stone-600">
                      {formatINR(p.bullionValue)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-stone-600">
                      {formatINR(p.taxesPaid)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-stone-900">
                      {formatINR(p.investedAmount)}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        {!showTrash ? (
                          <>
                            <button
                              type="button"
                              onClick={() => handleEdit(p)}
                              className="p-1 text-stone-400 hover:text-stone-800 rounded transition-colors"
                              title="Edit purchase"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => onSoftDeletePurchase(p.id)}
                              className="p-1 text-stone-400 hover:text-rose-600 rounded transition-colors"
                              title="Move to trash"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => onRestorePurchase(p.id)}
                              className="p-1 text-emerald-600 hover:text-emerald-800 rounded transition-colors flex items-center gap-1 text-[11px]"
                              title="Restore purchase"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                              <span>Restore</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => onPermanentDeletePurchase(p.id)}
                              className="p-1 text-rose-500 hover:text-rose-700 rounded transition-colors text-[11px] ml-1"
                              title="Delete permanently"
                            >
                              Purge
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile Stacked Cards (No horizontal overflow at 360px) */}
      <div className="md:hidden space-y-3">
        {filteredPurchases.length === 0 ? (
          <div className="bg-white p-6 rounded-xl border border-stone-200 text-center text-stone-400 text-xs">
            {showTrash
              ? 'No items in trash.'
              : activePurchases.length === 0
              ? 'No purchases recorded yet.'
              : 'No purchases match your search.'}
          </div>
        ) : (
          filteredPurchases.map((p) => (
            <div
              key={p.id}
              className="bg-white rounded-xl p-3.5 border border-[#E7E2DA] shadow-xs space-y-2.5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono text-stone-400 block">{p.id}</span>
                  <span className="font-bold text-xs text-stone-900">{p.seller}</span>
                  <span className="text-[11px] text-stone-500 block">
                    Inv #{p.invoiceNumber} • {formatDisplayDate(p.purchaseDate)}
                  </span>
                </div>
                <span
                  className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                    p.metal === 'GOLD'
                      ? 'bg-[#FBF6E9] text-[#B88B2A]'
                      : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {p.metal} {p.purity} • {p.form}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y border-stone-100">
                <div>
                  <span className="text-[10px] text-stone-500 block">Weight:</span>
                  <span className="font-semibold text-stone-800">
                    {formatGrams(p.weightGrams)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-stone-500 block">Rate / gram:</span>
                  <span className="font-medium text-stone-700">
                    {formatINR(p.purchaseRate)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-stone-500 block">Taxes Paid:</span>
                  <span className="font-medium text-stone-700">{formatINR(p.taxesPaid)}</span>
                </div>
                <div>
                  <span className="text-[10px] text-stone-500 block">Total Invested:</span>
                  <span className="font-bold text-[#B88B2A]">
                    {formatINR(p.investedAmount)}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-1">
                {!showTrash ? (
                  <>
                    <button
                      type="button"
                      onClick={() => handleEdit(p)}
                      className="px-2.5 py-1 text-xs text-stone-700 bg-stone-100 rounded-md font-medium"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => onSoftDeletePurchase(p.id)}
                      className="px-2.5 py-1 text-xs text-rose-700 bg-rose-50 rounded-md font-medium"
                    >
                      Delete
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => onRestorePurchase(p.id)}
                      className="px-2.5 py-1 text-xs text-emerald-700 bg-emerald-50 rounded-md font-medium"
                    >
                      Restore
                    </button>
                    <button
                      type="button"
                      onClick={() => onPermanentDeletePurchase(p.id)}
                      className="px-2.5 py-1 text-xs text-rose-700 bg-rose-50 rounded-md font-medium"
                    >
                      Purge
                    </button>
                  </>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modals */}
      <AddEditPurchaseModal
        isOpen={isAddEditOpen}
        onClose={() => setIsAddEditOpen(false)}
        onSave={onSavePurchase}
        existingPurchases={purchases}
        editingPurchase={editingPurchase}
      />

      <ImportPurchasesModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onImport={onImportPurchases}
        existingPurchases={purchases}
      />
    </div>
  );
};
