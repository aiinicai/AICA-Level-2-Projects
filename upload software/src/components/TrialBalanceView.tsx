import React, { useState } from 'react';
import {
  UploadCloud,
  FileUp,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Trash2,
  Building2,
  Info,
  Calendar,
  Layers,
  Clock,
  ArrowUpDown,
  History,
  XCircle,
} from 'lucide-react';
import { LedgerItem, EntityDetails } from '../types/accounting';
import { parseExcelTrialBalanceFile } from '../utils/excelParser';

interface TrialBalanceViewProps {
  ledgers: LedgerItem[];
  entity: EntityDetails;
  onImportNewLedgers: (
    rawLedgers: Omit<LedgerItem, 'targetType' | 'status' | 'confidence'>[],
    detectedEntity?: Partial<EntityDetails>
  ) => void;
  onImportPreviousYearLedgers: (
    rawLedgers: Omit<LedgerItem, 'targetType' | 'status' | 'confidence'>[],
    detectedEntity?: Partial<EntityDetails>
  ) => void;
  onClearPreviousYearLedgers: () => void;
  onReclassifyAll: () => void;
  onPurgeNonLedgers: () => void;
  onNavigateToClassification: () => void;
}

type TbDisplayMode = 'CURRENT_YEAR' | 'PREVIOUS_YEAR' | 'COMPARATIVE_TWO_YEAR';

export const TrialBalanceView: React.FC<TrialBalanceViewProps> = ({
  ledgers,
  entity,
  onImportNewLedgers,
  onImportPreviousYearLedgers,
  onClearPreviousYearLedgers,
  onReclassifyAll,
  onPurgeNonLedgers,
  onNavigateToClassification,
}) => {
  const [displayMode, setDisplayMode] = useState<TbDisplayMode>('CURRENT_YEAR');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGroup, setSelectedGroup] = useState<string>('ALL');
  const [isUploadingCY, setIsUploadingCY] = useState(false);
  const [isUploadingPY, setIsUploadingPY] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [lastImportMeta, setLastImportMeta] = useState<{
    count: number;
    ignoredCount: number;
    detectedName?: string;
    detectedPan?: string;
    detectedFy?: string;
    isMultiColumn?: boolean;
    importSourceDescription?: string;
    targetYear?: 'CY' | 'PY';
  } | null>(null);

  // Unique groups from ledgers
  const groups = Array.from(new Set(ledgers.map(l => l.originalGroup).filter(Boolean))).sort();

  // Current Year Totals
  const totalDebitCY = ledgers.reduce((acc, l) => acc + (l.debit || 0), 0);
  const totalCreditCY = ledgers.reduce((acc, l) => acc + (l.credit || 0), 0);
  const differenceCY = totalDebitCY - totalCreditCY;
  const isBalancedCY = Math.abs(differenceCY) < 0.01;

  // Previous Year Totals
  const pyLedgersWithBalances = ledgers.filter(
    l => (l.previousYearDebit || 0) > 0 || (l.previousYearCredit || 0) > 0 || (l.previousYearAmount || 0) !== 0
  );
  const hasPreviousYearData = pyLedgersWithBalances.length > 0;

  const totalDebitPY = ledgers.reduce((acc, l) => acc + (l.previousYearDebit || 0), 0);
  const totalCreditPY = ledgers.reduce((acc, l) => acc + (l.previousYearCredit || 0), 0);
  const differencePY = totalDebitPY - totalCreditPY;
  const isBalancedPY = Math.abs(differencePY) < 0.01;

  // Filtered ledgers
  const filteredLedgers = ledgers.filter(l => {
    const matchesSearch =
      l.ledgerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.originalGroup.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesGroup = selectedGroup === 'ALL' || l.originalGroup === selectedGroup;

    if (displayMode === 'PREVIOUS_YEAR') {
      const hasPy = (l.previousYearDebit || 0) > 0 || (l.previousYearCredit || 0) > 0 || (l.previousYearAmount || 0) !== 0;
      return matchesSearch && matchesGroup && hasPy;
    }

    return matchesSearch && matchesGroup;
  });

  const handleUploadCurrentYear = async (file: File) => {
    setIsUploadingCY(true);
    setUploadError(null);
    try {
      const result = await parseExcelTrialBalanceFile(file);
      if (result.ledgers.length === 0) {
        throw new Error('No valid ledger rows found. Ensure columns for Ledger Name/Particulars and Debit/Credit exist.');
      }

      setLastImportMeta({
        count: result.ledgers.length,
        ignoredCount: result.ignoredMetadataRowsCount,
        detectedName: result.detectedEntity?.name,
        detectedPan: result.detectedEntity?.pan,
        detectedFy: result.detectedEntity?.financialYear,
        isMultiColumn: result.isMultiColumnTrialBalance,
        importSourceDescription: result.mappedColumns?.importSourceDescription,
        targetYear: 'CY',
      });

      onImportNewLedgers(result.ledgers, result.detectedEntity);
    } catch (err: any) {
      console.error('CY Upload error:', err);
      setUploadError(err.message || 'Failed to parse Current Year Trial Balance');
    } finally {
      setIsUploadingCY(false);
    }
  };

  const handleUploadPreviousYear = async (file: File) => {
    setIsUploadingPY(true);
    setUploadError(null);
    try {
      const result = await parseExcelTrialBalanceFile(file);
      if (result.ledgers.length === 0) {
        throw new Error('No valid ledger rows found in the Previous Year file.');
      }

      setLastImportMeta({
        count: result.ledgers.length,
        ignoredCount: result.ignoredMetadataRowsCount,
        detectedName: result.detectedEntity?.name,
        detectedPan: result.detectedEntity?.pan,
        detectedFy: result.detectedEntity?.financialYear,
        isMultiColumn: result.isMultiColumnTrialBalance,
        importSourceDescription: result.mappedColumns?.importSourceDescription,
        targetYear: 'PY',
      });

      onImportPreviousYearLedgers(result.ledgers, result.detectedEntity);
    } catch (err: any) {
      console.error('PY Upload error:', err);
      setUploadError(err.message || 'Failed to parse Previous Year Trial Balance');
    } finally {
      setIsUploadingPY(false);
    }
  };

  const formatCur = (val: number) => {
    return Math.abs(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="space-y-4" id="trial-balance-container">
      {/* Top Header Banner with Mode Selector */}
      <div className="bg-[#141414] text-[#E4E3E0] p-4 border border-[#141414] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-[#A3A29E]" />
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-white">
              Sheet 2: Trial Balance Workspace (Two-Year Balances)
            </h2>
            <span className="px-2 py-0.5 bg-[#282828] text-[#86efac] border border-[#86efac]/40 text-[10px] font-mono font-bold uppercase">
              2-Year Audit Format
            </span>
          </div>
          <p className="text-[11.5px] text-[#A3A29E] mt-1">
            Current Year: <strong className="text-white">{entity.balanceSheetDate}</strong> | Previous Year:{' '}
            <strong className="text-white">{entity.previousYearDate || '31st March 2024'}</strong>. Import closing balances for both years to generate comparative financial statements.
          </p>
        </div>

        {/* View Mode Switcher */}
        <div className="flex items-center border border-[#141414]/40 bg-[#222222] p-0.5">
          <button
            onClick={() => setDisplayMode('CURRENT_YEAR')}
            className={`px-3 py-1 text-[11px] font-mono transition ${
              displayMode === 'CURRENT_YEAR'
                ? 'bg-white text-[#141414] font-bold shadow-xs'
                : 'text-[#A3A29E] hover:text-white'
            }`}
          >
            CURRENT YEAR (CY)
          </button>
          <button
            onClick={() => setDisplayMode('PREVIOUS_YEAR')}
            className={`px-3 py-1 text-[11px] font-mono transition relative ${
              displayMode === 'PREVIOUS_YEAR'
                ? 'bg-white text-[#141414] font-bold shadow-xs'
                : 'text-[#A3A29E] hover:text-white'
            }`}
          >
            PREVIOUS YEAR (PY)
            {hasPreviousYearData && (
              <span className="ml-1.5 px-1 py-0.2 bg-[#166534] text-[#86efac] rounded-full text-[9px]">
                {pyLedgersWithBalances.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setDisplayMode('COMPARATIVE_TWO_YEAR')}
            className={`px-3 py-1 text-[11px] font-mono transition ${
              displayMode === 'COMPARATIVE_TWO_YEAR'
                ? 'bg-white text-[#141414] font-bold shadow-xs'
                : 'text-[#A3A29E] hover:text-white'
            }`}
          >
            2-YEAR COMPARATIVE
          </button>
        </div>
      </div>

      {/* Dual Import Cards: Current Year & Previous Year */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card 1: Current Year TB */}
        <div
          className="bg-[#F5F4F0] border-2 border-dashed border-[#141414]/30 hover:border-[#141414] p-4 transition-colors flex flex-col justify-between"
          id="dropzone-cy-trial-balance"
        >
          <div>
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 bg-[#E4E3E0] border border-[#141414] text-[#141414] flex items-center justify-center shrink-0">
                  <UploadCloud className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-[#141414] text-xs font-mono uppercase tracking-wider">
                    Current Year TB ({entity.financialYear || 'FY 2024-25'})
                  </h3>
                  <span className="text-[11px] text-[#5E5E5E]">As on {entity.balanceSheetDate}</span>
                </div>
              </div>
              <span className="px-1.5 py-0.5 bg-[#dbeafe] text-[#1e40af] text-[10px] font-mono font-bold border border-[#bfdbfe]">
                PRIMARY
              </span>
            </div>

            <p className="text-[11px] text-[#5E5E5E] mt-2.5">
              Extracts closing balances, automatically maps accounts to ICAI heads, and auto-populates Fixed Assets into Schedule 8.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-[#141414]/15 flex items-center justify-between">
            <div className="text-[11px] font-mono text-[#141414]">
              {ledgers.length} Ledgers Active • {isBalancedCY ? 'Balanced ✓' : `Diff ₹${formatCur(differenceCY)}`}
            </div>

            <label className="cursor-pointer inline-flex items-center px-3 py-1.5 bg-[#141414] hover:bg-[#2e2e2e] text-white text-xs font-mono font-bold border border-[#141414] transition">
              <FileUp className="w-3.5 h-3.5 mr-1.5" />
              {isUploadingCY ? 'PARSING...' : 'IMPORT CURRENT YEAR TB'}
              <input
                type="file"
                accept=".xlsx, .xls, .csv"
                className="hidden"
                disabled={isUploadingCY}
                onChange={e => {
                  if (e.target.files && e.target.files[0]) {
                    handleUploadCurrentYear(e.target.files[0]);
                  }
                }}
              />
            </label>
          </div>
        </div>

        {/* Card 2: Previous Year TB */}
        <div
          className={`p-4 border-2 border-dashed transition-colors flex flex-col justify-between ${
            hasPreviousYearData
              ? 'bg-[#f0fdf4] border-[#86efac]/80 hover:border-[#16a34a]'
              : 'bg-[#F5F4F0] border-[#141414]/30 hover:border-[#141414]'
          }`}
          id="dropzone-py-trial-balance"
        >
          <div>
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center space-x-2.5">
                <div
                  className={`w-8 h-8 border flex items-center justify-center shrink-0 ${
                    hasPreviousYearData
                      ? 'bg-[#dcfce7] border-[#166534] text-[#166534]'
                      : 'bg-[#E4E3E0] border-[#141414] text-[#141414]'
                  }`}
                >
                  <History className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-[#141414] text-xs font-mono uppercase tracking-wider">
                    Previous Year TB ({entity.previousYearDate || 'FY 2023-24'})
                  </h3>
                  <span className="text-[11px] text-[#5E5E5E]">
                    {hasPreviousYearData ? `${pyLedgersWithBalances.length} Ledgers Linked` : 'Optional • For 2-Year Format'}
                  </span>
                </div>
              </div>

              {hasPreviousYearData ? (
                <span className="px-1.5 py-0.5 bg-[#dcfce7] text-[#166534] text-[10px] font-mono font-bold border border-[#86efac]">
                  LINKED ✓
                </span>
              ) : (
                <span className="px-1.5 py-0.5 bg-[#fef3c7] text-[#92400e] text-[10px] font-mono font-bold border border-[#fde68a]">
                  NOT IMPORTED
                </span>
              )}
            </div>

            <p className="text-[11px] text-[#5E5E5E] mt-2.5">
              Uploads prior-year trial balance to fill the "Previous Year" columns in Balance Sheet, Schedules 1–15, P&L, and Depreciation Schedule.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-[#141414]/15 flex items-center justify-between gap-2">
            <div className="text-[11px] font-mono text-[#141414]">
              {hasPreviousYearData ? (
                <span className="text-[#166534] font-semibold">
                  Total PY Dr: ₹{totalDebitPY.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </span>
              ) : (
                <span className="text-[#5E5E5E] italic">Import prior year file</span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {hasPreviousYearData && (
                <button
                  onClick={onClearPreviousYearLedgers}
                  className="px-2 py-1 bg-white hover:bg-[#fee2e2] text-[#991b1b] text-xs font-mono border border-[#141414]/30 hover:border-[#ef4444] transition"
                  title="Clear all previous year figures"
                >
                  <Trash2 className="w-3 h-3 inline mr-1" />
                  CLEAR
                </button>
              )}

              <label className="cursor-pointer inline-flex items-center px-3 py-1.5 bg-[#222222] hover:bg-[#333333] text-white text-xs font-mono font-bold border border-[#141414] transition">
                <FileUp className="w-3.5 h-3.5 mr-1.5" />
                {isUploadingPY ? 'MERGING...' : hasPreviousYearData ? 'RE-IMPORT PY TB' : 'IMPORT PREVIOUS YEAR TB'}
                <input
                  type="file"
                  accept=".xlsx, .xls, .csv"
                  className="hidden"
                  disabled={isUploadingPY}
                  onChange={e => {
                    if (e.target.files && e.target.files[0]) {
                      handleUploadPreviousYear(e.target.files[0]);
                    }
                  }}
                />
              </label>
            </div>
          </div>
        </div>
      </div>

      {uploadError && (
        <div className="p-2.5 bg-[#fee2e2] border border-[#ef4444] text-[#991b1b] text-xs font-mono flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-[#ef4444] shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {lastImportMeta && (
        <div className="p-2.5 bg-[#eff6ff] border border-[#93c5fd] text-[#1e40af] text-xs font-mono flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#2563eb] shrink-0" />
              <span>
                {lastImportMeta.targetYear === 'PY' ? 'Previous Year' : 'Current Year'}: Successfully imported{' '}
                <strong>{lastImportMeta.count}</strong> ledgers. Filtered out <strong>{lastImportMeta.ignoredCount}</strong> metadata/header rows.
              </span>
            </div>
            {lastImportMeta.detectedName && (
              <div className="flex items-center gap-1.5 bg-white px-2 py-0.5 border border-[#bfdbfe] text-[11px] text-[#1e3a8a]">
                <Building2 className="w-3 h-3" />
                <span>
                  Detected: <strong>{lastImportMeta.detectedName}</strong>{' '}
                  {lastImportMeta.detectedPan ? `(${lastImportMeta.detectedPan})` : ''}
                </span>
              </div>
            )}
          </div>
          {lastImportMeta.importSourceDescription && (
            <div className="text-[11px] text-[#1d4ed8] font-semibold flex items-center gap-1 bg-[#dbeafe] px-2 py-1 border border-[#bfdbfe]">
              <span>✓ {lastImportMeta.importSourceDescription}</span>
            </div>
          )}
        </div>
      )}

      {/* Trial Balance Statistics Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div className="bg-[#F5F4F0] p-3.5 border border-[#141414]/20">
          <span className="text-[#5E5E5E] font-mono text-[10.5px] uppercase tracking-wider">
            {displayMode === 'PREVIOUS_YEAR' ? 'PY Total Debit (₹)' : 'CY Total Debit (₹)'}
          </span>
          <p className="text-base font-bold font-mono text-[#141414] mt-1">
            ₹
            {(displayMode === 'PREVIOUS_YEAR' ? totalDebitPY : totalDebitCY).toLocaleString('en-IN', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
          <span className="text-[10.5px] font-mono text-[#5E5E5E]">
            {displayMode === 'PREVIOUS_YEAR' ? `PY Assets & Expenses` : `CY Assets & Expenses`}
          </span>
        </div>

        <div className="bg-[#F5F4F0] p-3.5 border border-[#141414]/20">
          <span className="text-[#5E5E5E] font-mono text-[10.5px] uppercase tracking-wider">
            {displayMode === 'PREVIOUS_YEAR' ? 'PY Total Credit (₹)' : 'CY Total Credit (₹)'}
          </span>
          <p className="text-base font-bold font-mono text-[#141414] mt-1">
            ₹
            {(displayMode === 'PREVIOUS_YEAR' ? totalCreditPY : totalCreditCY).toLocaleString('en-IN', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
          <span className="text-[10.5px] font-mono text-[#5E5E5E]">
            {displayMode === 'PREVIOUS_YEAR' ? `PY Liabilities & Incomes` : `CY Liabilities & Incomes`}
          </span>
        </div>

        <div
          className={`p-3.5 border font-mono ${
            (displayMode === 'PREVIOUS_YEAR' ? isBalancedPY : isBalancedCY)
              ? 'bg-[#dcfce7] border-[#86efac] text-[#166534]'
              : 'bg-[#fef3c7] border-[#fde68a] text-[#92400e]'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-bold text-[10.5px] uppercase tracking-wider opacity-80">
              {displayMode === 'PREVIOUS_YEAR' ? 'PY Verification' : 'CY Verification'}
            </span>
            {(displayMode === 'PREVIOUS_YEAR' ? isBalancedPY : isBalancedCY) ? (
              <span className="font-bold flex items-center gap-1 text-[11px]">
                <CheckCircle2 className="w-3.5 h-3.5" /> MATCHED ✓
              </span>
            ) : (
              <span className="font-bold flex items-center gap-1 text-[11px]">
                <AlertTriangle className="w-3.5 h-3.5" /> DIFFERENCE !
              </span>
            )}
          </div>
          <p className="text-base font-bold mt-1">
            {(displayMode === 'PREVIOUS_YEAR' ? isBalancedPY : isBalancedCY)
              ? '₹ 0.00'
              : `₹ ${Math.abs(displayMode === 'PREVIOUS_YEAR' ? differencePY : differenceCY).toLocaleString('en-IN', {
                  minimumFractionDigits: 2,
                })}`}
          </p>
          <span className="text-[10.5px] opacity-80">
            {displayMode === 'PREVIOUS_YEAR' ? `${pyLedgersWithBalances.length} PY Accounts` : `${ledgers.length} Ledgers Active`}
          </span>
        </div>
      </div>

      {/* Trial Balance Table Card */}
      <div className="bg-[#F5F4F0] border border-[#141414]/20 overflow-hidden" id="card-tb-table">
        {/* Table Controls */}
        <div className="p-3 border-b border-[#141414]/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#ECEAE5]">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2.5 top-2.5 text-[#5E5E5E]" />
              <input
                type="text"
                placeholder="Search ledger or group..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-7 pr-2.5 py-1 bg-white border border-[#141414] text-xs font-mono w-56 focus:outline-none"
                id="input-tb-search"
              />
            </div>

            <div className="flex items-center space-x-1">
              <Filter className="w-3 h-3 text-[#5E5E5E]" />
              <select
                value={selectedGroup}
                onChange={e => setSelectedGroup(e.target.value)}
                className="bg-white border border-[#141414] px-2 py-1 text-xs font-mono text-[#141414] focus:outline-none"
                id="select-tb-group"
              >
                <option value="ALL">ALL ERP GROUPS ({groups.length})</option>
                {groups.map(g => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={onReclassifyAll}
              title="Re-run the enhanced ICAI classification rule engine on all ledgers"
              className="inline-flex items-center px-2.5 py-1 bg-white hover:bg-[#F5F4F0] text-[#141414] text-xs font-mono font-semibold border border-[#141414] transition"
              id="btn-tb-reclassify-all"
            >
              <RefreshCw className="w-3 h-3 mr-1 text-[#5E5E5E]" />
              <span>RE-CLASSIFY ALL</span>
            </button>

            <button
              onClick={onPurgeNonLedgers}
              title="Purge non-ledger rows or general particulars from the ledger list"
              className="inline-flex items-center px-2.5 py-1 bg-white hover:bg-[#fee2e2] text-[#991b1b] text-xs font-mono font-semibold border border-[#141414]/30 hover:border-[#ef4444] transition"
              id="btn-tb-purge-junk"
            >
              <Trash2 className="w-3 h-3 mr-1" />
              <span>PURGE NON-LEDGERS</span>
            </button>

            <button
              onClick={onNavigateToClassification}
              className="inline-flex items-center px-3 py-1 bg-[#141414] hover:bg-[#2e2e2e] text-white text-xs font-mono font-bold border border-[#141414] transition"
              id="btn-goto-classification"
            >
              <span>CLASSIFICATION STUDIO</span>
              <ArrowRight className="w-3 h-3 ml-1.5" />
            </button>
          </div>
        </div>

        {/* Ledger Table */}
        <div className="overflow-x-auto max-h-[600px]">
          {displayMode === 'COMPARATIVE_TWO_YEAR' ? (
            /* ======================================================= */
            /* 2-YEAR COMPARATIVE SIDE-BY-SIDE VIEW                    */
            /* ======================================================= */
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider sticky top-0 z-10 border-b border-[#141414]">
                <tr>
                  <th className="py-2 px-2.5 w-10 text-center border-r border-[#141414]/20">#</th>
                  <th className="py-2 px-3 border-r border-[#141414]/20">Ledger Name</th>
                  <th className="py-2 px-3 w-36 border-r border-[#141414]/20">Group</th>
                  <th className="py-2 px-3 w-32 text-right border-r border-[#141414]/20 bg-[#f8fafc]">
                    CY Net (₹)
                    <div className="text-[9px] text-[#64748b] font-normal">{entity.balanceSheetDate}</div>
                  </th>
                  <th className="py-2 px-3 w-32 text-right border-r border-[#141414]/20 bg-[#f0fdf4]">
                    PY Net (₹)
                    <div className="text-[9px] text-[#166534] font-normal">{entity.previousYearDate || '31-03-2024'}</div>
                  </th>
                  <th className="py-2 px-3 w-28 text-right border-r border-[#141414]/20">Variance (₹)</th>
                  <th className="py-2 px-3 w-40">Schedule / Head</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#141414]/15 bg-white">
                {filteredLedgers.map((l, idx) => {
                  const cyNet = Math.abs((l.debit || 0) - (l.credit || 0));
                  const cyNature = (l.debit || 0) >= (l.credit || 0) ? 'Dr' : 'Cr';

                  const pyDr = l.previousYearDebit || 0;
                  const pyCr = l.previousYearCredit || 0;
                  const pyNet = (pyDr > 0 || pyCr > 0) ? Math.abs(pyDr - pyCr) : Math.abs(l.previousYearAmount || 0);
                  const pyNature = pyDr >= pyCr ? 'Dr' : 'Cr';

                  // Signed delta: (CY - PY)
                  const cySigned = (l.debit || 0) - (l.credit || 0);
                  const pySigned = (pyDr > 0 || pyCr > 0) ? (pyDr - pyCr) : (l.previousYearAmount || 0);
                  const variance = cySigned - pySigned;

                  return (
                    <tr key={l.id} className="hover:bg-[#ECEAE5]/60 transition-colors">
                      <td className="py-1.5 px-2 text-center text-[#5E5E5E] font-mono border-r border-[#141414]/10">
                        {idx + 1}
                      </td>
                      <td className="py-1.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                        {l.ledgerName}
                      </td>
                      <td className="py-1.5 px-3 text-[#5E5E5E] border-r border-[#141414]/10">{l.originalGroup}</td>

                      {/* CY Net */}
                      <td className="py-1.5 px-3 text-right font-mono font-bold text-[#141414] border-r border-[#141414]/10 bg-[#f8fafc]">
                        {cyNet > 0 ? (
                          <>
                            {cyNet.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            <span className="text-[9.5px] text-[#5E5E5E] ml-1">{cyNature}</span>
                          </>
                        ) : (
                          <span className="text-[#A3A29E] font-normal">-</span>
                        )}
                      </td>

                      {/* PY Net */}
                      <td className="py-1.5 px-3 text-right font-mono font-bold text-[#166534] border-r border-[#141414]/10 bg-[#f0fdf4]">
                        {pyNet > 0 ? (
                          <>
                            {pyNet.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            <span className="text-[9.5px] text-[#166534]/70 ml-1">{pyNature}</span>
                          </>
                        ) : (
                          <span className="text-[#A3A29E] font-normal">-</span>
                        )}
                      </td>

                      {/* Variance */}
                      <td className="py-1.5 px-3 text-right font-mono border-r border-[#141414]/10">
                        {variance !== 0 ? (
                          <span className={variance >= 0 ? 'text-[#166534]' : 'text-[#b91c1c]'}>
                            {variance >= 0 ? '+' : ''}
                            {variance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </span>
                        ) : (
                          <span className="text-[#A3A29E]">-</span>
                        )}
                      </td>

                      {/* Head */}
                      <td className="py-1.5 px-3">
                        {l.subHead ? (
                          <span className="inline-block px-1.5 py-0.2 font-mono text-[10px] font-semibold bg-[#f0fdf4] text-[#166534] border border-[#86efac]">
                            SCH {l.scheduleNo} - {l.subHead}
                          </span>
                        ) : l.targetType === 'PROFIT_AND_LOSS' ? (
                          <span className="inline-block px-1.5 py-0.2 font-mono text-[10px] font-semibold bg-[#eff6ff] text-[#1d4ed8] border border-[#bfdbfe]">
                            P&L: {l.plCategory?.replace('_', ' ')}
                          </span>
                        ) : (
                          <span className="inline-block px-1.5 py-0.2 font-mono text-[10px] font-semibold bg-[#fef3c7] text-[#92400e] border border-[#fde68a]">
                            UNCLASSIFIED
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot className="bg-[#ECEAE5] font-mono font-bold text-[#141414] border-t-2 border-[#141414]">
                <tr>
                  <td colSpan={3} className="py-2 px-3 text-right text-xs uppercase tracking-wider border-r border-[#141414]/20">
                    TOTAL 2-YEAR TRIAL BALANCES:
                  </td>
                  <td className="py-2 px-3 text-right font-mono border-r border-[#141414]/20 bg-[#f8fafc]">
                    Dr ₹{totalDebitCY.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td className="py-2 px-3 text-right font-mono border-r border-[#141414]/20 bg-[#f0fdf4] text-[#166534]">
                    Dr ₹{totalDebitPY.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td colSpan={2} className="py-2 px-3 text-xs">
                    {hasPreviousYearData
                      ? '✓ Two-year balances ready for Financial Statements'
                      : 'Import Previous Year TB to view comparative figures'}
                  </td>
                </tr>
              </tfoot>
            </table>
          ) : (
            /* ======================================================= */
            /* SINGLE YEAR (CY OR PY) DETAILED DEBIT / CREDIT TABLE    */
            /* ======================================================= */
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider sticky top-0 z-10 border-b border-[#141414]">
                <tr>
                  <th className="py-2 px-2.5 w-10 text-center border-r border-[#141414]/20">#</th>
                  <th className="py-2 px-3 border-r border-[#141414]/20">Ledger Name</th>
                  <th className="py-2 px-3 w-40 border-r border-[#141414]/20">ERP / Tally Group</th>
                  <th className="py-2 px-3 w-32 text-right border-r border-[#141414]/20">
                    {displayMode === 'PREVIOUS_YEAR' ? 'PY Debit (₹)' : 'Debit (₹)'}
                  </th>
                  <th className="py-2 px-3 w-32 text-right border-r border-[#141414]/20">
                    {displayMode === 'PREVIOUS_YEAR' ? 'PY Credit (₹)' : 'Credit (₹)'}
                  </th>
                  <th className="py-2 px-3 w-32 text-right border-r border-[#141414]/20">
                    {displayMode === 'PREVIOUS_YEAR' ? 'PY Net Balance (₹)' : 'Net Balance (₹)'}
                  </th>
                  <th className="py-2 px-3 w-48">Classification Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#141414]/15 bg-white">
                {filteredLedgers.map((l, idx) => {
                  const dr = displayMode === 'PREVIOUS_YEAR' ? (l.previousYearDebit || 0) : l.debit;
                  const cr = displayMode === 'PREVIOUS_YEAR' ? (l.previousYearCredit || 0) : l.credit;
                  const net = Math.abs(dr - cr);
                  const nature = dr >= cr ? 'Dr' : 'Cr';

                  return (
                    <tr key={l.id} className="hover:bg-[#ECEAE5]/60 transition-colors">
                      <td className="py-1.5 px-2 text-center text-[#5E5E5E] font-mono border-r border-[#141414]/10">
                        {idx + 1}
                      </td>
                      <td className="py-1.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                        {l.ledgerName}
                      </td>
                      <td className="py-1.5 px-3 text-[#5E5E5E] border-r border-[#141414]/10">{l.originalGroup}</td>
                      <td className="py-1.5 px-3 text-right font-mono border-r border-[#141414]/10">
                        {dr > 0 ? dr.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '-'}
                      </td>
                      <td className="py-1.5 px-3 text-right font-mono border-r border-[#141414]/10">
                        {cr > 0 ? cr.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '-'}
                      </td>
                      <td className="py-1.5 px-3 text-right font-mono font-bold text-[#141414] border-r border-[#141414]/10">
                        {net.toLocaleString('en-IN', { minimumFractionDigits: 2 })}{' '}
                        <span className="text-[9.5px] text-[#5E5E5E] font-bold">{nature}</span>
                      </td>
                      <td className="py-1.5 px-3">
                        {l.targetType === 'PROFIT_AND_LOSS' ? (
                          <span className="inline-block px-1.5 py-0.2 font-mono text-[10px] font-semibold bg-[#eff6ff] text-[#1d4ed8] border border-[#bfdbfe]">
                            P&L: {l.plCategory?.replace('_', ' ')}
                          </span>
                        ) : l.subHead ? (
                          <span className="inline-block px-1.5 py-0.2 font-mono text-[10px] font-semibold bg-[#f0fdf4] text-[#166534] border border-[#86efac]">
                            SCH {l.scheduleNo} - {l.subHead}
                          </span>
                        ) : (
                          <span className="inline-block px-1.5 py-0.2 font-mono text-[10px] font-semibold bg-[#fef3c7] text-[#92400e] border border-[#fde68a]">
                            UNCLASSIFIED
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot className="bg-[#ECEAE5] font-mono font-bold text-[#141414] border-t-2 border-[#141414]">
                <tr>
                  <td colSpan={3} className="py-2 px-3 text-right text-xs uppercase tracking-wider border-r border-[#141414]/20">
                    TOTAL {displayMode === 'PREVIOUS_YEAR' ? 'PREVIOUS YEAR' : 'CURRENT YEAR'} TRIAL BALANCE:
                  </td>
                  <td className="py-2 px-3 text-right font-mono border-r border-[#141414]/20">
                    ₹
                    {(displayMode === 'PREVIOUS_YEAR' ? totalDebitPY : totalDebitCY).toLocaleString('en-IN', {
                      minimumFractionDigits: 2,
                    })}
                  </td>
                  <td className="py-2 px-3 text-right font-mono border-r border-[#141414]/20">
                    ₹
                    {(displayMode === 'PREVIOUS_YEAR' ? totalCreditPY : totalCreditCY).toLocaleString('en-IN', {
                      minimumFractionDigits: 2,
                    })}
                  </td>
                  <td className="py-2 px-3 text-right font-mono border-r border-[#141414]/20">
                    {(displayMode === 'PREVIOUS_YEAR' ? isBalancedPY : isBalancedCY)
                      ? 'MATCHED ✓'
                      : `DIFF: ₹${formatCur(displayMode === 'PREVIOUS_YEAR' ? differencePY : differenceCY)}`}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
