import React, { useState, useRef, useMemo } from 'react';
import {
  FileSpreadsheet,
  Upload,
  Download,
  Plus,
  Trash2,
  RefreshCw,
  Calculator,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  Sparkles,
  Link as LinkIcon,
  Search,
} from 'lucide-react';
import { DepreciationAssetItem, EntityDetails, LedgerItem } from '../types/accounting';
import {
  readDepreciationFile,
  extractDepreciationSheetData,
  generateDepreciationExcelTemplate,
  exportDepreciationScheduleExcel,
  DepreciationColumnMapping,
  extractAssetsFromTrialBalance,
} from '../utils/depreciationParser';
import { DEFAULT_DEPRECIATION_ASSETS } from '../utils/nonCorporateDefaults';

interface DepreciationScheduleViewProps {
  entity: EntityDetails;
  depreciationAssets: DepreciationAssetItem[];
  onUpdateAssets: (assets: DepreciationAssetItem[]) => void;
  ledgers?: LedgerItem[];
  onSyncWithSchedule8?: (assets: DepreciationAssetItem[]) => void;
  onSyncWithPL?: (depreciationAmount: number) => void;
  onNavigateToTab?: (tab: any) => void;
}

export const DepreciationScheduleView: React.FC<DepreciationScheduleViewProps> = ({
  entity,
  depreciationAssets,
  onUpdateAssets,
  ledgers = [],
  onSyncWithSchedule8,
  onSyncWithPL,
  onNavigateToTab,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isDownloadingTemplate, setIsDownloadingTemplate] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  // File upload staging state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [stagedWorkbook, setStagedWorkbook] = useState<any>(null);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string>('');
  const [availableHeaders, setAvailableHeaders] = useState<string[]>([]);
  const [customMapping, setCustomMapping] = useState<Partial<DepreciationColumnMapping>>({});
  const [previewItems, setPreviewItems] = useState<DepreciationAssetItem[]>([]);
  const [importMode, setImportMode] = useState<'replace' | 'append'>('replace');
  const [importError, setImportError] = useState<string | null>(null);

  const formatCur = (val: number) => {
    return (val || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  // Grand totals
  const totalGrossBlock = depreciationAssets.reduce((sum, item) => sum + (item.grossBlock || 0), 0);
  const totalAccumulatedDepr = depreciationAssets.reduce((sum, item) => sum + (item.accumulatedDepreciation || 0), 0);
  const totalDeprForTheYear = depreciationAssets.reduce((sum, item) => sum + (item.depreciationForTheYear || 0), 0);
  const totalClosingValue = depreciationAssets.reduce((sum, item) => sum + (item.closingValue || 0), 0);
  const totalPreviousYearClosing = depreciationAssets.reduce((sum, item) => sum + (item.previousYearClosing || 0), 0);

  // Filtered list
  const filteredAssets = depreciationAssets.filter(item => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      item.assetName.toLowerCase().includes(term) ||
      (item.category && item.category.toLowerCase().includes(term)) ||
      (item.notes && item.notes.toLowerCase().includes(term))
    );
  });

  // Handle cell edit
  const handleCellChange = (id: string, field: keyof DepreciationAssetItem, value: any) => {
    const updated = depreciationAssets.map(item => {
      if (item.id !== id) return item;
      const copy = { ...item, [field]: value };
      return copy;
    });
    onUpdateAssets(updated);
  };

  // Auto calculate closing value for a single row: Gross Block - (Accum Depr + Depr of year)
  const handleAutoCalcRow = (id: string) => {
    const updated = depreciationAssets.map(item => {
      if (item.id !== id) return item;
      const closing = Math.max(0, (item.grossBlock || 0) - ((item.accumulatedDepreciation || 0) + (item.depreciationForTheYear || 0)));
      const prevClosing = Math.max(0, (item.grossBlock || 0) - (item.accumulatedDepreciation || 0));
      return {
        ...item,
        closingValue: Math.round(closing * 100) / 100,
        previousYearClosing: Math.round(prevClosing * 100) / 100,
      };
    });
    onUpdateAssets(updated);
  };

  // Auto calculate all closing values
  const handleRecalculateAllClosing = () => {
    const updated = depreciationAssets.map(item => {
      const closing = Math.max(0, (item.grossBlock || 0) - ((item.accumulatedDepreciation || 0) + (item.depreciationForTheYear || 0)));
      const prevClosing = Math.max(0, (item.grossBlock || 0) - (item.accumulatedDepreciation || 0));
      return {
        ...item,
        closingValue: Math.round(closing * 100) / 100,
        previousYearClosing: Math.round(prevClosing * 100) / 100,
      };
    });
    onUpdateAssets(updated);
    showTempNotice('Recalculated closing values for all assets based on Gross Block - (Accumulated Depr + Depr of Year).');
  };

  // Auto compute depreciation for year from rate %: (Gross Block - Accumulated Depr) * (Rate / 100)
  const handleComputeDeprFromRate = () => {
    const updated = depreciationAssets.map(item => {
      const openingWdv = Math.max(0, (item.grossBlock || 0) - (item.accumulatedDepreciation || 0));
      const depr = item.depreciationRate > 0 ? openingWdv * (item.depreciationRate / 100) : item.depreciationForTheYear;
      const closing = Math.max(0, openingWdv - depr);
      return {
        ...item,
        depreciationForTheYear: Math.round(depr * 100) / 100,
        closingValue: Math.round(closing * 100) / 100,
        previousYearClosing: Math.round(openingWdv * 100) / 100,
      };
    });
    onUpdateAssets(updated);
    showTempNotice('Recomputed current year depreciation using Rate (%) on Opening WDV.');
  };

  // Add new blank asset row
  const handleAddAssetRow = () => {
    const newAsset: DepreciationAssetItem = {
      id: `depr-${Date.now()}`,
      assetName: 'New Asset Item',
      category: 'Fixed Assets',
      grossBlock: 100000,
      depreciationRate: 15,
      accumulatedDepreciation: 0,
      depreciationForTheYear: 15000,
      closingValue: 85000,
      previousYearClosing: 100000,
      notes: '',
    };
    onUpdateAssets([...depreciationAssets, newAsset]);
  };

  // Delete row
  const handleDeleteRow = (id: string) => {
    onUpdateAssets(depreciationAssets.filter(item => item.id !== id));
  };

  // Download sample template
  const handleDownloadTemplate = async () => {
    try {
      setIsDownloadingTemplate(true);
      const blob = await generateDepreciationExcelTemplate(entity.name);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Depreciation_Schedule_Template_${entity.name.replace(/\s+/g, '_')}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Failed to download template: ${err.message}`);
    } finally {
      setIsDownloadingTemplate(false);
    }
  };

  // Export current schedule to Excel
  const handleExportSchedule = async () => {
    try {
      setIsExporting(true);
      const blob = await exportDepreciationScheduleExcel(entity, depreciationAssets);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Depreciation_Schedule_${entity.name.replace(/\s+/g, '_')}_FY_${entity.financialYear}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  // Reset to sample defaults
  const handleResetToDefaults = () => {
    if (confirm('Reset depreciation schedule to standard non-corporate sample assets?')) {
      onUpdateAssets(DEFAULT_DEPRECIATION_ASSETS);
      showTempNotice('Reset depreciation schedule to default sample non-corporate assets.');
    }
  };

  // Show temporary notice
  const showTempNotice = (msg: string) => {
    setSyncNotice(msg);
    setTimeout(() => setSyncNotice(null), 5000);
  };

  // Sync to Schedule 8 handler
  const handleSyncSchedule8 = () => {
    if (onSyncWithSchedule8) {
      onSyncWithSchedule8(depreciationAssets);
      showTempNotice(`Successfully synced ${depreciationAssets.length} asset blocks (Net Carrying ₹${formatCur(totalClosingValue)}) into Schedule 8 (Property, Plant & Equipment).`);
    }
  };

  // Sync to P&L handler
  const handleSyncPL = () => {
    if (onSyncWithPL) {
      onSyncWithPL(totalDeprForTheYear);
      showTempNotice(`Depreciation of the year (₹${formatCur(totalDeprForTheYear)}) linked with Profit & Loss Statement.`);
    }
  };

  // Find Fixed Assets in the imported Trial Balance
  const tbFixedAssetLedgers = useMemo(() => {
    if (!ledgers || ledgers.length === 0) return [];
    return ledgers.filter(l => {
      const n = (l.ledgerName || '').toLowerCase();
      const g = (l.originalGroup || '').toLowerCase();
      const isContraOrExp =
        n.includes('accumulated depr') ||
        n.includes('provision for depr') ||
        n.includes('acc depr') ||
        n.includes('depreciation a/c') ||
        n.includes('depreciation expense');
      if (isContraOrExp) return false;

      const isPPE = l.headCode === 'A01' || g.includes('fixed asset') || g.includes('capital asset');
      const isAssetKeyword = /machinery|plant|furniture|fixture|computer|laptop|printer|vehicle|car|motor|truck|building|premises|office equipment/i.test(n);
      const isDebit = (l.debit || 0) > 0 || (l.netBalance || 0) > 0 || l.natureDrCr === 'Dr';
      return (isPPE || isAssetKeyword) && isDebit && l.targetType !== 'PROFIT_AND_LOSS';
    });
  }, [ledgers]);

  const totalTBFixedAssets = useMemo(() => {
    return tbFixedAssetLedgers.reduce((sum, l) => {
      const bal = (l.debit || 0) > 0 ? (l.debit || 0) : Math.abs(l.netBalance || 0);
      return sum + bal;
    }, 0);
  }, [tbFixedAssetLedgers]);

  const tbVariance = Math.abs(totalClosingValue - totalTBFixedAssets);
  const isReconciledWithTB = tbFixedAssetLedgers.length > 0 && tbVariance < 1.0;

  // Pick Fixed Assets from Trial Balance handler
  const handlePickFromTrialBalance = (mode: 'replace' | 'append' = 'replace') => {
    if (!ledgers || ledgers.length === 0) {
      alert('No trial balance is currently loaded. Please upload a Trial Balance Excel file first.');
      return;
    }

    const extracted = extractAssetsFromTrialBalance(ledgers);
    if (extracted.length === 0) {
      alert('No Fixed Asset / Property, Plant & Equipment ledgers detected in Trial Balance (scanned Head A01, Fixed Assets groups, and asset keywords).');
      return;
    }

    if (mode === 'replace') {
      onUpdateAssets(extracted);
      const totGross = extracted.reduce((s, i) => s + i.grossBlock, 0);
      const totNet = extracted.reduce((s, i) => s + i.closingValue, 0);
      showTempNotice(`Successfully picked ${extracted.length} fixed asset ledgers from Trial Balance (Gross: ₹${formatCur(totGross)}, Net Closing: ₹${formatCur(totNet)}).`);
    } else {
      const existingNames = new Set(depreciationAssets.map(a => a.assetName.toLowerCase()));
      const newItems = extracted.filter(e => !existingNames.has(e.assetName.toLowerCase()));
      if (newItems.length === 0) {
        showTempNotice('All fixed asset ledgers from the Trial Balance are already in the Depreciation Schedule.');
        return;
      }
      onUpdateAssets([...depreciationAssets, ...newItems]);
      showTempNotice(`Appended ${newItems.length} asset ledgers from Trial Balance.`);
    }
  };

  // Auto-compute IT Act depreciation based on rates
  const handleAutoComputeITDepreciation = () => {
    const updated = depreciationAssets.map(a => {
      const rate = a.depreciationRate > 0 ? a.depreciationRate : 15;
      const openingWdv = Math.max(0, a.grossBlock - a.accumulatedDepreciation);
      const deprForYear = Math.round((openingWdv * (rate / 100)) * 100) / 100;
      const closingValue = Math.round(Math.max(0, a.grossBlock - a.accumulatedDepreciation - deprForYear) * 100) / 100;
      return {
        ...a,
        depreciationRate: rate,
        depreciationForTheYear: deprForYear,
        closingValue,
        previousYearClosing: openingWdv,
      };
    });
    onUpdateAssets(updated);
    showTempNotice(`Recalculated Income Tax Act WDV depreciation for ${updated.length} assets.`);
  };

  // File Upload Handlers
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setImportError(null);
      const { sheetNames, workbook } = await readDepreciationFile(file);
      if (sheetNames.length === 0) {
        throw new Error('No sheets found in Excel file');
      }

      setStagedWorkbook(workbook);
      setSheetNames(sheetNames);
      const initialSheet = sheetNames[0];
      setSelectedSheet(initialSheet);

      const parsed = extractDepreciationSheetData(workbook, initialSheet);
      setAvailableHeaders(parsed.headers);
      setCustomMapping(parsed.detectedMapping);
      setPreviewItems(parsed.parsedItems);
      setIsImportModalOpen(true);
    } catch (err: any) {
      setImportError(err.message || 'Failed to parse Excel file');
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleSheetChange = (sheet: string) => {
    if (!stagedWorkbook) return;
    setSelectedSheet(sheet);
    const parsed = extractDepreciationSheetData(stagedWorkbook, sheet);
    setAvailableHeaders(parsed.headers);
    setCustomMapping(parsed.detectedMapping);
    setPreviewItems(parsed.parsedItems);
  };

  const handleMappingChange = (key: keyof DepreciationColumnMapping, headerVal: string) => {
    const updated = { ...customMapping, [key]: headerVal };
    setCustomMapping(updated);
    if (stagedWorkbook && selectedSheet) {
      const parsed = extractDepreciationSheetData(stagedWorkbook, selectedSheet, updated);
      setPreviewItems(parsed.parsedItems);
    }
  };

  const handleConfirmImport = () => {
    if (!stagedWorkbook || !selectedSheet) return;
    const parsed = extractDepreciationSheetData(stagedWorkbook, selectedSheet, customMapping);
    if (parsed.parsedItems.length === 0) {
      alert('No valid asset rows found with current mapping. Please check column selections.');
      return;
    }

    if (importMode === 'replace') {
      onUpdateAssets(parsed.parsedItems);
    } else {
      onUpdateAssets([...depreciationAssets, ...parsed.parsedItems]);
    }

    setIsImportModalOpen(false);
    setStagedWorkbook(null);
    showTempNotice(`Successfully imported ${parsed.parsedItems.length} asset rows from Excel sheet "${selectedSheet}".`);
  };

  return (
    <div className="space-y-4" id="depreciation-schedule-container">
      {/* Top Banner */}
      <div className="bg-[#141414] text-[#E4E3E0] p-4 border border-[#141414] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Calculator className="w-4 h-4 text-[#86efac]" />
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-white">
              Depreciation Schedule (Property, Plant & Equipment)
            </h2>
          </div>
          <p className="text-[11.5px] text-[#A3A29E] mt-1">
            Import Excel schedule with <strong>Gross Block</strong>, <strong>Rate of Depreciation</strong>,{' '}
            <strong>Accumulated Depreciation</strong>, <strong>Depreciation of the Year</strong>, <strong>Closing Value</strong>, and{' '}
            <strong>Closing of Previous Year</strong>.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".xlsx, .xls, .csv"
            className="hidden"
            id="input-depr-file"
          />

          <button
            onClick={() => handlePickFromTrialBalance('replace')}
            className="inline-flex items-center px-3 py-1.5 bg-[#fef08a] hover:bg-[#fde047] text-[#713f12] text-[11px] font-mono font-bold transition border border-[#ca8a04] shadow-xs"
            title="Pick and load Fixed Asset ledgers & closing balances directly from Trial Balance"
            id="btn-pick-tb-header"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1.5 text-[#a16207]" />
            PICK FROM TB {tbFixedAssetLedgers.length > 0 ? `(${tbFixedAssetLedgers.length})` : ''}
          </button>

          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center px-3 py-1.5 bg-[#86efac] hover:bg-[#6ee7b7] text-[#0f291e] text-[11px] font-mono font-bold transition shadow-xs"
            id="btn-import-depr-excel"
          >
            <Upload className="w-3.5 h-3.5 mr-1.5" />
            IMPORT EXCEL
          </button>

          <button
            onClick={handleDownloadTemplate}
            disabled={isDownloadingTemplate}
            className="inline-flex items-center px-3 py-1.5 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
            title="Download blank template with columns & formulas"
            id="btn-download-depr-template"
          >
            <Download className="w-3.5 h-3.5 mr-1.5 text-[#38bdf8]" />
            {isDownloadingTemplate ? 'PREPARING...' : 'EXCEL TEMPLATE'}
          </button>

          <button
            onClick={handleExportSchedule}
            disabled={isExporting}
            className="inline-flex items-center px-3 py-1.5 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
            title="Export this depreciation schedule to Excel (.xlsx)"
            id="btn-export-depr-schedule"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 mr-1.5 text-[#86efac]" />
            {isExporting ? 'EXPORTING...' : 'EXPORT EXCEL'}
          </button>

          <button
            onClick={handleAddAssetRow}
            className="inline-flex items-center px-3 py-1.5 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
            id="btn-add-asset-row"
          >
            <Plus className="w-3.5 h-3.5 mr-1 text-[#fbbf24]" />
            ADD ASSET
          </button>
        </div>
      </div>

      {/* Sync Notice Banner */}
      {syncNotice && (
        <div className="bg-[#dcfce7] border border-[#86efac] text-[#166534] p-3 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-[#166534] shrink-0" />
            <span>{syncNotice}</span>
          </div>
          <button
            onClick={() => setSyncNotice(null)}
            className="text-[11px] underline text-[#166534] hover:text-[#14532d]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Trial Balance Connection & Reconciliation Banner */}
      <div className="bg-[#FAF9F5] border border-[#141414]/20 p-3.5 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs font-mono" id="tb-depr-sync-banner">
        <div className="flex items-center space-x-3">
          <div className={`p-2 border shrink-0 ${isReconciledWithTB ? 'bg-[#dcfce7] border-[#86efac] text-[#166534]' : 'bg-[#fef9c3] border-[#fde047] text-[#854d0e]'}`}>
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-[#141414] uppercase tracking-wider text-[11px]">
                Trial Balance Integration (Schedule 8 / Head A01)
              </span>
              {isReconciledWithTB ? (
                <span className="inline-flex items-center px-2 py-0.5 bg-[#dcfce7] text-[#166534] border border-[#86efac] text-[10px] font-bold">
                  ✓ RECONCILED WITH TB
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 bg-[#fef9c3] text-[#854d0e] border border-[#fde047] text-[10px]">
                  {tbFixedAssetLedgers.length > 0 ? `TB FA: ₹${formatCur(totalTBFixedAssets)} (${tbFixedAssetLedgers.length} ledgers)` : 'No TB Fixed Assets detected'}
                </span>
              )}
            </div>
            <p className="text-[11px] text-[#5E5E5E] mt-0.5">
              {tbFixedAssetLedgers.length > 0 ? (
                <>
                  Trial Balance contains <strong>{tbFixedAssetLedgers.length}</strong> Fixed Asset ledgers totaling <strong>₹{formatCur(totalTBFixedAssets)}</strong>. Schedule net closing carrying amount: <strong>₹{formatCur(totalClosingValue)}</strong>.
                  {!isReconciledWithTB && tbVariance > 0.01 && (
                    <span className="text-[#b45309] font-bold ml-1.5">Variance: ₹{formatCur(tbVariance)}</span>
                  )}
                </>
              ) : (
                'Upload a Trial Balance or click "PICK FROM TRIAL BALANCE" to sync Property, Plant & Equipment ledgers.'
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2 shrink-0">
          <button
            onClick={() => handlePickFromTrialBalance('replace')}
            className="inline-flex items-center px-3 py-1.5 bg-[#fef08a] hover:bg-[#fde047] text-[#713f12] text-[11px] font-mono font-bold transition border border-[#ca8a04] shadow-xs"
            title="Automatically pick all Fixed Asset / PPE ledgers and closing balances from Trial Balance"
            id="btn-pick-from-tb"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1.5 text-[#a16207]" />
            PICK FROM TRIAL BALANCE ({tbFixedAssetLedgers.length})
          </button>

          <button
            onClick={handleAutoComputeITDepreciation}
            className="inline-flex items-center px-2.5 py-1.5 bg-[#F4F3F0] hover:bg-[#E4E3E0] text-[#141414] text-[11px] font-mono border border-[#141414]/30 transition"
            title="Auto-compute Income Tax Act WDV depreciation based on standard category rates"
            id="btn-auto-compute-depr"
          >
            <Calculator className="w-3.5 h-3.5 mr-1 text-[#2563eb]" />
            AUTO-COMPUTE DEPR
          </button>
        </div>
      </div>

      {/* KPI Metric Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs font-mono">
        <div className="bg-[#F4F3F0] p-3 border border-[#141414]/20">
          <span className="text-[10px] text-[#5E5E5E] uppercase block">Total Gross Block</span>
          <p className="text-sm font-bold text-[#141414] mt-0.5">₹{formatCur(totalGrossBlock)}</p>
          <span className="text-[9.5px] text-[#8E8C85]">{depreciationAssets.length} Assets</span>
        </div>

        <div className="bg-[#F4F3F0] p-3 border border-[#141414]/20">
          <span className="text-[10px] text-[#5E5E5E] uppercase block">Accumulated Depr</span>
          <p className="text-sm font-bold text-[#B45309] mt-0.5">₹{formatCur(totalAccumulatedDepr)}</p>
          <span className="text-[9.5px] text-[#8E8C85]">Upto previous year</span>
        </div>

        <div className="bg-[#F4F3F0] p-3 border border-[#141414]/20">
          <span className="text-[10px] text-[#5E5E5E] uppercase block">Depr of the Year</span>
          <p className="text-sm font-bold text-[#DC2626] mt-0.5">₹{formatCur(totalDeprForTheYear)}</p>
          <span className="text-[9.5px] text-[#8E8C85]">Current FY charge</span>
        </div>

        <div className="bg-[#ecfdf5] p-3 border border-[#a7f3d0]">
          <span className="text-[10px] text-[#065f46] uppercase block font-bold">Closing Net Value</span>
          <p className="text-sm font-bold text-[#047857] mt-0.5">₹{formatCur(totalClosingValue)}</p>
          <span className="text-[9.5px] text-[#059669]">As at {entity.balanceSheetDate}</span>
        </div>

        <div className="bg-[#F4F3F0] p-3 border border-[#141414]/20">
          <span className="text-[10px] text-[#5E5E5E] uppercase block">Previous Year Closing</span>
          <p className="text-sm font-bold text-[#1E293B] mt-0.5">₹{formatCur(totalPreviousYearClosing)}</p>
          <span className="text-[9.5px] text-[#8E8C85]">As at 31-03-2024</span>
        </div>

        <div className="bg-[#F4F3F0] p-3 border border-[#141414]/20 flex flex-col justify-between">
          <span className="text-[10px] text-[#5E5E5E] uppercase block">Statutory Schedule</span>
          <div className="flex items-center space-x-1.5 mt-1">
            <span className="px-1.5 py-0.5 bg-[#141414] text-white text-[10px] font-bold">SCH 8</span>
            <span className="text-[10px] text-[#5E5E5E]">Property, Plant & Equip</span>
          </div>
          {onSyncWithSchedule8 && (
            <button
              onClick={handleSyncSchedule8}
              className="mt-1 text-[10px] text-blue-700 hover:text-blue-900 underline font-bold text-left flex items-center gap-1"
            >
              <LinkIcon className="w-2.5 h-2.5" /> Sync to Sch 8
            </button>
          )}
        </div>
      </div>

      {/* Toolbar / Actions Strip */}
      <div className="bg-[#F4F3F0] p-3 border border-[#141414]/20 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center space-x-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#5E5E5E]" />
            <input
              type="text"
              placeholder="Search assets by name or category..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-white border border-[#141414]/30 text-xs font-mono"
              id="input-search-depr-assets"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleRecalculateAllClosing}
            className="inline-flex items-center px-2.5 py-1 bg-white hover:bg-[#ECEAE5] text-[#141414] text-[11px] font-mono border border-[#141414]/30 transition"
            title="Auto-calculate Closing Value = Gross Block - (Accum Depr + Depr of Year)"
            id="btn-recalc-all-closing"
          >
            <Calculator className="w-3 h-3 mr-1 text-[#2563eb]" />
            CALC CLOSING VALUES
          </button>

          <button
            onClick={handleComputeDeprFromRate}
            className="inline-flex items-center px-2.5 py-1 bg-white hover:bg-[#ECEAE5] text-[#141414] text-[11px] font-mono border border-[#141414]/30 transition"
            title="Compute Current Year Depreciation = Opening WDV * Rate (%)"
            id="btn-compute-depr-rate"
          >
            <Sparkles className="w-3 h-3 mr-1 text-[#d97706]" />
            CALC VIA RATE %
          </button>

          {onSyncWithSchedule8 && (
            <button
              onClick={handleSyncSchedule8}
              className="inline-flex items-center px-2.5 py-1 bg-[#1e293b] hover:bg-[#334155] text-white text-[11px] font-mono transition"
              title="Apply these numbers to Schedule 8 (Property, Plant & Equipment) in the Balance Sheet"
              id="btn-sync-to-sch8"
            >
              <LinkIcon className="w-3 h-3 mr-1 text-[#86efac]" />
              SYNC TO SCHEDULE 8
            </button>
          )}

          {onSyncWithPL && (
            <button
              onClick={handleSyncPL}
              className="inline-flex items-center px-2.5 py-1 bg-white hover:bg-[#ECEAE5] text-[#141414] text-[11px] font-mono border border-[#141414]/30 transition"
              title="Push total depreciation of year (₹X,XX,XXX) to Profit & Loss Statement"
              id="btn-sync-to-pl"
            >
              <ArrowRight className="w-3 h-3 mr-1 text-[#dc2626]" />
              LINK TO P&L (₹{formatCur(totalDeprForTheYear)})
            </button>
          )}

          <button
            onClick={handleResetToDefaults}
            className="inline-flex items-center px-2 py-1 bg-white hover:bg-[#ECEAE5] text-[#5E5E5E] hover:text-[#141414] text-[11px] font-mono border border-[#141414]/20 transition"
            title="Reset to sample non-corporate assets"
            id="btn-reset-depr-defaults"
          >
            <RefreshCw className="w-3 h-3 mr-1" />
            RESET SAMPLE
          </button>
        </div>
      </div>

      {/* Interactive Depreciation Table */}
      <div className="bg-white border border-[#141414]/20 shadow-xs overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[1040px]" id="table-depreciation-schedule">
          <thead>
            <tr className="bg-[#1E293B] text-white font-mono text-[10px] uppercase">
              <th className="py-2 px-2 text-center border-r border-white/20 w-10" rowSpan={2}>
                #
              </th>
              <th className="py-2 px-3 border-r border-white/20 min-w-[220px]" rowSpan={2}>
                Asset Name / Description
              </th>
              <th className="py-2 px-2 border-r border-white/20 min-w-[130px]" rowSpan={2}>
                Category / Block
              </th>
              <th className="py-1 px-2 text-right border-r border-white/20 bg-[#1E3A8A] font-bold" rowSpan={2}>
                Gross Block (₹)
              </th>
              <th className="py-1 px-2 text-center border-r border-white/20 bg-[#0F766E] font-bold w-20" rowSpan={2}>
                Rate (%)
              </th>
              <th className="py-1.5 px-2 text-center border-r border-white/20 bg-[#854D0E]" colSpan={2}>
                Depreciation (₹)
              </th>
              <th className="py-1.5 px-2 text-center border-r border-white/20 bg-[#14532D]" colSpan={2}>
                Carrying Amount / Net Block (₹)
              </th>
              <th className="py-2 px-2 border-r border-white/20 min-w-[140px]" rowSpan={2}>
                Remarks
              </th>
              <th className="py-2 px-2 text-center w-16" rowSpan={2}>
                Action
              </th>
            </tr>
            <tr className="bg-[#ECEAE5] text-[#141414] font-mono text-[9.5px] uppercase border-b border-[#141414]">
              <th className="py-1 px-2 text-right border-r border-[#141414]/20">Accumulated</th>
              <th className="py-1 px-2 text-right border-r border-[#141414]/20 font-bold text-red-700">Depr of Year</th>
              <th className="py-1 px-2 text-right border-r border-[#141414]/20 font-bold text-green-800 bg-[#dcfce7]/60">
                Closing Value
              </th>
              <th className="py-1 px-2 text-right border-r border-[#141414]/20 font-bold">Closing Prev Year</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#141414]/15">
            {filteredAssets.length === 0 ? (
              <tr>
                <td colSpan={11} className="py-8 text-center text-[#5E5E5E] font-mono text-xs">
                  No assets in schedule matching criteria. Click <strong>Import Excel</strong> or <strong>Add Asset</strong> to populate.
                </td>
              </tr>
            ) : (
              filteredAssets.map((item, idx) => {
                const expectedClosing = Math.max(0, item.grossBlock - (item.accumulatedDepreciation + item.depreciationForTheYear));
                const isFormulaAligned = Math.abs(item.closingValue - expectedClosing) < 1;

                return (
                  <tr key={item.id} className="hover:bg-[#F9F8F6] text-xs transition">
                    <td className="py-1.5 px-2 text-center font-mono text-[#5E5E5E] border-r border-[#141414]/10">
                      {idx + 1}
                    </td>

                    {/* Asset Name */}
                    <td className="py-1.5 px-2 border-r border-[#141414]/10">
                      <input
                        type="text"
                        value={item.assetName}
                        onChange={e => handleCellChange(item.id, 'assetName', e.target.value)}
                        className="w-full bg-transparent hover:bg-white focus:bg-white border border-transparent focus:border-[#141414] px-1.5 py-0.5 text-xs font-semibold text-[#141414]"
                      />
                    </td>

                    {/* Category */}
                    <td className="py-1.5 px-2 border-r border-[#141414]/10">
                      <input
                        type="text"
                        value={item.category || ''}
                        onChange={e => handleCellChange(item.id, 'category', e.target.value)}
                        placeholder="e.g. Plant / Building"
                        className="w-full bg-transparent hover:bg-white focus:bg-white border border-transparent focus:border-[#141414] px-1.5 py-0.5 text-[11.5px] text-[#5E5E5E]"
                      />
                    </td>

                    {/* Gross Block */}
                    <td className="py-1.5 px-2 text-right border-r border-[#141414]/10 font-mono">
                      <input
                        type="number"
                        value={item.grossBlock}
                        onChange={e => handleCellChange(item.id, 'grossBlock', parseFloat(e.target.value) || 0)}
                        className="w-full bg-transparent hover:bg-white focus:bg-white border border-transparent focus:border-[#141414] px-1.5 py-0.5 text-xs text-right font-mono font-bold"
                      />
                    </td>

                    {/* Rate of Depr (%) */}
                    <td className="py-1.5 px-2 text-center border-r border-[#141414]/10 font-mono">
                      <div className="flex items-center justify-center">
                        <input
                          type="number"
                          step="0.5"
                          value={item.depreciationRate}
                          onChange={e => handleCellChange(item.id, 'depreciationRate', parseFloat(e.target.value) || 0)}
                          className="w-12 bg-transparent hover:bg-white focus:bg-white border border-transparent focus:border-[#141414] px-1 py-0.5 text-xs text-center font-mono font-medium"
                        />
                        <span className="text-[10px] text-[#5E5E5E]">%</span>
                      </div>
                    </td>

                    {/* Accumulated Depreciation */}
                    <td className="py-1.5 px-2 text-right border-r border-[#141414]/10 font-mono text-[#B45309]">
                      <input
                        type="number"
                        value={item.accumulatedDepreciation}
                        onChange={e => handleCellChange(item.id, 'accumulatedDepreciation', parseFloat(e.target.value) || 0)}
                        className="w-full bg-transparent hover:bg-white focus:bg-white border border-transparent focus:border-[#141414] px-1.5 py-0.5 text-xs text-right font-mono text-[#B45309]"
                      />
                    </td>

                    {/* Depreciation of the Year */}
                    <td className="py-1.5 px-2 text-right border-r border-[#141414]/10 font-mono text-red-700">
                      <input
                        type="number"
                        value={item.depreciationForTheYear}
                        onChange={e => handleCellChange(item.id, 'depreciationForTheYear', parseFloat(e.target.value) || 0)}
                        className="w-full bg-transparent hover:bg-white focus:bg-white border border-transparent focus:border-[#141414] px-1.5 py-0.5 text-xs text-right font-mono font-bold text-red-700"
                      />
                    </td>

                    {/* Closing Value */}
                    <td className="py-1.5 px-2 text-right border-r border-[#141414]/10 font-mono bg-[#dcfce7]/20">
                      <div className="flex items-center justify-end space-x-1">
                        <input
                          type="number"
                          value={item.closingValue}
                          onChange={e => handleCellChange(item.id, 'closingValue', parseFloat(e.target.value) || 0)}
                          className="w-full bg-transparent hover:bg-white focus:bg-white border border-transparent focus:border-[#141414] px-1.5 py-0.5 text-xs text-right font-mono font-bold text-green-900"
                        />
                        {!isFormulaAligned && (
                          <button
                            onClick={() => handleAutoCalcRow(item.id)}
                            title={`Click to set = ₹${formatCur(expectedClosing)} (Gross - Accum - Depr)`}
                            className="text-[#d97706] hover:text-[#b45309] p-0.5"
                          >
                            <HelpCircle className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </td>

                    {/* Closing of Previous Year */}
                    <td className="py-1.5 px-2 text-right border-r border-[#141414]/10 font-mono text-[#1E293B]">
                      <input
                        type="number"
                        value={item.previousYearClosing}
                        onChange={e => handleCellChange(item.id, 'previousYearClosing', parseFloat(e.target.value) || 0)}
                        className="w-full bg-transparent hover:bg-white focus:bg-white border border-transparent focus:border-[#141414] px-1.5 py-0.5 text-xs text-right font-mono text-[#1E293B]"
                      />
                    </td>

                    {/* Remarks */}
                    <td className="py-1.5 px-2 border-r border-[#141414]/10">
                      <input
                        type="text"
                        value={item.notes || ''}
                        onChange={e => handleCellChange(item.id, 'notes', e.target.value)}
                        placeholder="Optional remarks"
                        className="w-full bg-transparent hover:bg-white focus:bg-white border border-transparent focus:border-[#141414] px-1 py-0.5 text-[11px] text-[#5E5E5E]"
                      />
                    </td>

                    {/* Action */}
                    <td className="py-1.5 px-2 text-center font-mono">
                      <button
                        onClick={() => handleDeleteRow(item.id)}
                        className="p-1 text-[#5E5E5E] hover:text-red-700 hover:bg-red-50 transition"
                        title="Delete asset row"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>

          {/* Grand Totals Footer */}
          <tfoot>
            <tr className="bg-[#ECEAE5] font-mono text-xs font-bold border-t-2 border-b-2 border-[#141414]">
              <td className="py-2.5 px-2 text-center border-r border-[#141414]/20" colSpan={3}>
                TOTAL FIXED ASSETS / PPE ({depreciationAssets.length} ASSETS)
              </td>
              <td className="py-2.5 px-2 text-right border-r border-[#141414]/20 text-[#141414]">
                ₹{formatCur(totalGrossBlock)}
              </td>
              <td className="py-2.5 px-2 text-center border-r border-[#141414]/20 text-[#5E5E5E]">
                -
              </td>
              <td className="py-2.5 px-2 text-right border-r border-[#141414]/20 text-[#B45309]">
                ₹{formatCur(totalAccumulatedDepr)}
              </td>
              <td className="py-2.5 px-2 text-right border-r border-[#141414]/20 text-red-700">
                ₹{formatCur(totalDeprForTheYear)}
              </td>
              <td className="py-2.5 px-2 text-right border-r border-[#141414]/20 text-green-900 bg-[#dcfce7]/50">
                ₹{formatCur(totalClosingValue)}
              </td>
              <td className="py-2.5 px-2 text-right border-r border-[#141414]/20 text-[#1E293B]">
                ₹{formatCur(totalPreviousYearClosing)}
              </td>
              <td className="py-2.5 px-2" colSpan={2}></td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Guidance Note on Statutory Accounting */}
      <div className="bg-[#ECEAE5] p-3 border border-[#141414]/20 text-xs font-mono text-[#5E5E5E] flex items-start space-x-2">
        <AlertCircle className="w-4 h-4 text-[#141414] shrink-0 mt-0.5" />
        <div>
          <p className="font-bold text-[#141414]">Statutory & Income Tax Alignment Note:</p>
          <p className="mt-0.5 text-[11px] leading-relaxed">
            In non-corporate entities, depreciation is customarily computed under the Written Down Value (WDV) method at the block rates prescribed under the Income Tax Act, 1961 (e.g. Buildings: 10%, Plant & Machinery: 15%, Computers: 40%).
            When you click <strong>Sync to Schedule 8</strong>, the closing net value (<strong>₹{formatCur(totalClosingValue)}</strong>) is mapped into the Balance Sheet asset side under <em>Schedule 8 - Property, Plant & Equipment</em>.
          </p>
        </div>
      </div>

      {/* IMPORT MAPPING MODAL */}
      {isImportModalOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-[#ECEAE5] border-2 border-[#141414] max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl">
            <div className="bg-[#141414] text-white p-3 flex items-center justify-between">
              <div className="flex items-center space-x-2 font-mono text-xs font-bold uppercase">
                <FileSpreadsheet className="w-4 h-4 text-[#86efac]" />
                <span>Import Depreciation Schedule From Excel</span>
              </div>
              <button
                onClick={() => setIsImportModalOpen(false)}
                className="text-white hover:text-red-400 font-mono text-xs px-1.5"
              >
                [✕]
              </button>
            </div>

            <div className="p-4 space-y-4 overflow-y-auto flex-1 font-mono text-xs">
              {/* Sheet Selector */}
              {sheetNames.length > 1 && (
                <div>
                  <label className="block text-[11px] uppercase font-bold text-[#141414] mb-1">
                    Select Worksheet
                  </label>
                  <select
                    value={selectedSheet}
                    onChange={e => handleSheetChange(e.target.value)}
                    className="w-full bg-white border border-[#141414] p-1.5 text-xs font-semibold"
                  >
                    {sheetNames.map(s => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Column Mapping Grid */}
              <div className="bg-white p-3 border border-[#141414]/20 space-y-3">
                <h4 className="font-bold text-xs uppercase text-[#141414] flex items-center gap-1.5 border-b border-[#141414]/10 pb-1">
                  <Calculator className="w-3.5 h-3.5 text-[#141414]" /> Map Excel Columns to Required Fields
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {/* Asset Name */}
                  <div>
                    <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">
                      Asset Name / Particulars *
                    </label>
                    <select
                      value={customMapping.assetNameCol || ''}
                      onChange={e => handleMappingChange('assetNameCol', e.target.value)}
                      className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs"
                    >
                      <option value="">-- Select Header --</option>
                      {availableHeaders.map(h => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Gross Block */}
                  <div>
                    <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">
                      Gross Block (Cost) *
                    </label>
                    <select
                      value={customMapping.grossBlockCol || ''}
                      onChange={e => handleMappingChange('grossBlockCol', e.target.value)}
                      className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs"
                    >
                      <option value="">-- Select Header --</option>
                      {availableHeaders.map(h => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Rate of Depreciation */}
                  <div>
                    <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">
                      Rate of Depreciation (%) *
                    </label>
                    <select
                      value={customMapping.depreciationRateCol || ''}
                      onChange={e => handleMappingChange('depreciationRateCol', e.target.value)}
                      className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs"
                    >
                      <option value="">-- Select Header --</option>
                      {availableHeaders.map(h => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Accumulated Depreciation */}
                  <div>
                    <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">
                      Accumulated Depreciation *
                    </label>
                    <select
                      value={customMapping.accumulatedDepreciationCol || ''}
                      onChange={e => handleMappingChange('accumulatedDepreciationCol', e.target.value)}
                      className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs"
                    >
                      <option value="">-- Select Header --</option>
                      {availableHeaders.map(h => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Depreciation of the Year */}
                  <div>
                    <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">
                      Depreciation of the Year *
                    </label>
                    <select
                      value={customMapping.depreciationForTheYearCol || ''}
                      onChange={e => handleMappingChange('depreciationForTheYearCol', e.target.value)}
                      className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs"
                    >
                      <option value="">-- Select Header --</option>
                      {availableHeaders.map(h => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Closing Value */}
                  <div>
                    <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">
                      Closing Value (Net Block) *
                    </label>
                    <select
                      value={customMapping.closingValueCol || ''}
                      onChange={e => handleMappingChange('closingValueCol', e.target.value)}
                      className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs"
                    >
                      <option value="">-- Select Header --</option>
                      {availableHeaders.map(h => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Closing of Previous Year */}
                  <div>
                    <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">
                      Closing of Previous Year *
                    </label>
                    <select
                      value={customMapping.previousYearClosingCol || ''}
                      onChange={e => handleMappingChange('previousYearClosingCol', e.target.value)}
                      className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs"
                    >
                      <option value="">-- Select Header --</option>
                      {availableHeaders.map(h => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Category / Block */}
                  <div>
                    <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">
                      Category / Block (Optional)
                    </label>
                    <select
                      value={customMapping.categoryCol || ''}
                      onChange={e => handleMappingChange('categoryCol', e.target.value)}
                      className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs"
                    >
                      <option value="">-- Select Header (Optional) --</option>
                      {availableHeaders.map(h => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Preview of Parsed Items */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-bold text-xs uppercase text-[#141414]">
                    Parsed Preview ({previewItems.length} Asset Blocks Detected)
                  </span>
                  <div className="flex items-center space-x-2">
                    <label className="text-[11px] flex items-center space-x-1 cursor-pointer">
                      <input
                        type="radio"
                        checked={importMode === 'replace'}
                        onChange={() => setImportMode('replace')}
                      />
                      <span>Replace Existing</span>
                    </label>
                    <label className="text-[11px] flex items-center space-x-1 cursor-pointer">
                      <input
                        type="radio"
                        checked={importMode === 'append'}
                        onChange={() => setImportMode('append')}
                      />
                      <span>Append to Existing</span>
                    </label>
                  </div>
                </div>

                <div className="border border-[#141414]/20 max-h-48 overflow-y-auto bg-white">
                  <table className="w-full text-left text-[11px]">
                    <thead className="bg-[#ECEAE5] sticky top-0 font-bold border-b border-[#141414]/20">
                      <tr>
                        <th className="p-1.5">Asset</th>
                        <th className="p-1.5 text-right">Gross Block</th>
                        <th className="p-1.5 text-center">Rate</th>
                        <th className="p-1.5 text-right">Accum Depr</th>
                        <th className="p-1.5 text-right">Depr Year</th>
                        <th className="p-1.5 text-right font-bold text-green-900">Closing</th>
                        <th className="p-1.5 text-right">Prev Closing</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#141414]/10">
                      {previewItems.slice(0, 8).map((p, idx) => (
                        <tr key={idx}>
                          <td className="p-1.5 font-medium truncate max-w-[180px]">{p.assetName}</td>
                          <td className="p-1.5 text-right font-mono">₹{formatCur(p.grossBlock)}</td>
                          <td className="p-1.5 text-center font-mono">{p.depreciationRate}%</td>
                          <td className="p-1.5 text-right font-mono">₹{formatCur(p.accumulatedDepreciation)}</td>
                          <td className="p-1.5 text-right font-mono text-red-700">₹{formatCur(p.depreciationForTheYear)}</td>
                          <td className="p-1.5 text-right font-mono font-bold text-green-900">₹{formatCur(p.closingValue)}</td>
                          <td className="p-1.5 text-right font-mono">₹{formatCur(p.previousYearClosing)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-3 bg-[#E4E3E0] border-t border-[#141414]/20 flex items-center justify-end space-x-2">
              <button
                onClick={() => setIsImportModalOpen(false)}
                className="px-3 py-1.5 bg-white border border-[#141414] text-xs font-mono"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmImport}
                disabled={previewItems.length === 0}
                className="px-4 py-1.5 bg-[#141414] hover:bg-[#2e2e2e] text-white text-xs font-mono font-bold disabled:opacity-50"
                id="btn-confirm-depr-import"
              >
                IMPORT {previewItems.length} ASSETS
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
