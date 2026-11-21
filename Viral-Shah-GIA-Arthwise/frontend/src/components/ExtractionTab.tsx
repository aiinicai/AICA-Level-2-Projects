import React, { useState, useEffect, useMemo } from 'react';
import { 
  CheckCircle2, Edit3, Trash2, XCircle, FileSpreadsheet, Eye, Info, 
  UploadCloud, RefreshCw, FileText, Calculator, Landmark, Layers, 
  Plus, ArrowRight, ShieldCheck, AlertCircle, Save, Check, Filter, TrendingUp,
  CreditCard, PieChart
} from 'lucide-react';
import { ExtractedDataRecord } from '../types';
import { formatINR, NumberUnitMode } from '../utils/formatters';
import { ApiClient } from '../api/client';
import { NumberInput } from './NumberInput';

interface ExtractionTabProps {
  proposalId: string;
  extractedRecords: ExtractedDataRecord[];
  onRefresh: () => void;
  unitMode: NumberUnitMode;
}

interface FinancialFormState {
  revenue_from_operations: number;
  other_income: number;
  cost_of_goods_sold: number;
  employee_benefits_expense: number;
  finance_costs: number;
  depreciation: number;
  other_expenses: number;
  tax_expense: number;
  pat: number;

  tangible_net_worth: number;
  long_term_borrowings: number;
  short_term_borrowings: number;
  trade_payables: number;
  other_current_liabilities: number;
  fixed_assets: number;
  inventories: number;
  trade_receivables: number;
  cash_and_bank: number;
  other_current_assets: number;
}

const defaultFormState: FinancialFormState = {
  revenue_from_operations: 0,
  other_income: 0,
  cost_of_goods_sold: 0,
  employee_benefits_expense: 0,
  finance_costs: 0,
  depreciation: 0,
  other_expenses: 0,
  tax_expense: 0,
  pat: 0,

  tangible_net_worth: 0,
  long_term_borrowings: 0,
  short_term_borrowings: 0,
  trade_payables: 0,
  other_current_liabilities: 0,
  fixed_assets: 0,
  inventories: 0,
  trade_receivables: 0,
  cash_and_bank: 0,
  other_current_assets: 0,
};

interface MetricDisplayMeta {
  label: string;
  category: 'pnl' | 'liabilities' | 'assets' | 'banking' | 'other';
  order: number;
  isKeyMilestone?: boolean;
  rowHighlight?: string;
}

const METRIC_METADATA: Record<string, MetricDisplayMeta> = {
  // =========================================================================
  // PART I: STATEMENT OF PROFIT & LOSS (P&L / OPERATING STATEMENT)
  // =========================================================================
  revenue_from_operations: { 
    label: 'Revenue from Operations (Gross Turnover / Sales)', 
    category: 'pnl', 
    order: 10, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-brand-50/60 font-semibold' 
  },
  other_income: { 
    label: 'Other Operating & Non-Operating Income', 
    category: 'pnl', 
    order: 12 
  },
  total_income: { 
    label: 'Total Income (Gross Revenue)', 
    category: 'pnl', 
    order: 14, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-slate-100 font-bold text-slate-900' 
  },
  cost_of_goods_sold: { 
    label: 'Cost of Goods Sold (COGS / Material Consumed / Purchases)', 
    category: 'pnl', 
    order: 20 
  },
  employee_benefits_expense: { 
    label: 'Employee Benefits Expense (Salaries, Wages & Staff Costs)', 
    category: 'pnl', 
    order: 22 
  },
  other_expenses: { 
    label: 'Other Operating & Administrative Expenses', 
    category: 'pnl', 
    order: 24 
  },
  ebitda: { 
    label: 'Operating Profit (EBITDA)', 
    category: 'pnl', 
    order: 26, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-emerald-50 text-emerald-950 font-bold' 
  },
  finance_costs: { 
    label: 'Finance Costs (Bank Interest & Finance Charges)', 
    category: 'pnl', 
    order: 28 
  },
  depreciation: { 
    label: 'Depreciation & Amortization Expense', 
    category: 'pnl', 
    order: 30 
  },
  total_expenses: { 
    label: 'Total Expenses', 
    category: 'pnl', 
    order: 32, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-slate-100 font-bold text-slate-900' 
  },
  profit_before_tax: { 
    label: 'Profit Before Tax (PBT)', 
    category: 'pnl', 
    order: 34, 
    isKeyMilestone: true,
    rowHighlight: 'font-semibold' 
  },
  tax_expense: { 
    label: 'Provision for Tax (Current Tax)', 
    category: 'pnl', 
    order: 36 
  },
  pat: { 
    label: 'Profit After Tax (PAT / Net Profit)', 
    category: 'pnl', 
    order: 38, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-emerald-50 text-emerald-950 font-bold' 
  },

  // =========================================================================
  // PART II: BALANCE SHEET — CAPITAL & LIABILITIES
  // =========================================================================
  tangible_net_worth: { 
    label: "Owner's Capital / Tangible Net Worth (TNW)", 
    category: 'liabilities', 
    order: 50, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-brand-50/60 font-bold' 
  },
  long_term_borrowings: { 
    label: 'Long-Term Borrowings (Term Loans / Unsecured Loans)', 
    category: 'liabilities', 
    order: 52 
  },
  short_term_borrowings: { 
    label: 'Short-Term Borrowings (Bank CC / OD / Working Capital)', 
    category: 'liabilities', 
    order: 54 
  },
  trade_payables: { 
    label: 'Trade Payables (Sundry Creditors)', 
    category: 'liabilities', 
    order: 56 
  },
  other_current_liabilities: { 
    label: 'Other Current Liabilities & Provisions', 
    category: 'liabilities', 
    order: 58 
  },
  current_liabilities: { 
    label: 'Total Current Liabilities (TCL)', 
    category: 'liabilities', 
    order: 60, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-slate-100 font-semibold text-slate-900' 
  },
  total_liabilities: { 
    label: 'Total Equity & Liabilities', 
    category: 'liabilities', 
    order: 62, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-slate-200 font-bold text-slate-950' 
  },

  // =========================================================================
  // PART III: BALANCE SHEET — ASSETS
  // =========================================================================
  fixed_assets: { 
    label: 'Property, Plant & Equipment (Fixed Assets / Net Block)', 
    category: 'assets', 
    order: 70, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-brand-50/60 font-bold' 
  },
  inventories: { 
    label: 'Inventories (Closing Stock & Work-in-Progress)', 
    category: 'assets', 
    order: 72 
  },
  trade_receivables: { 
    label: 'Trade Receivables (Sundry Debtors)', 
    category: 'assets', 
    order: 74 
  },
  cash_and_bank: { 
    label: 'Cash & Bank Balances', 
    category: 'assets', 
    order: 76 
  },
  other_current_assets: { 
    label: 'Other Current Assets, Loans & Advances', 
    category: 'assets', 
    order: 78 
  },
  current_assets: { 
    label: 'Total Current Assets (TCA)', 
    category: 'assets', 
    order: 80, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-slate-100 font-semibold text-slate-900' 
  },
  total_assets: { 
    label: 'Total Assets', 
    category: 'assets', 
    order: 82, 
    isKeyMilestone: true, 
    rowHighlight: 'bg-slate-200 font-bold text-slate-950' 
  },

  // =========================================================================
  // PART IV: STATUTORY & BANKING BENCHMARKS
  // =========================================================================
  itr_gross_total_income: { label: 'ITR Gross Total Income', category: 'banking', order: 90 },
  itr_total_income: { label: 'ITR Total Taxable Income', category: 'banking', order: 92 },
  itr_tax_payable: { label: 'ITR Net Tax Paid', category: 'banking', order: 94 },
  gstr3b_taxable_turnover: { label: 'GSTR-3B Outward Taxable Turnover', category: 'banking', order: 100 },
  gstr3b_total_tax: { label: 'GSTR-3B Total Tax Paid', category: 'banking', order: 102 },
  bank_annual_credits: { label: 'Bank Statement Annual Credit Summation', category: 'banking', order: 110 },
  bank_abb: { label: 'Average Bank Balance (ABB)', category: 'banking', order: 112 },
};

export const ExtractionTab: React.FC<ExtractionTabProps> = ({
  proposalId,
  extractedRecords,
  onRefresh,
  unitMode,
}) => {
  // Top-level mode: 'scanner' (Auto document extractor) vs 'manual' (Manual year-wise staff entry)
  const [activeMode, setActiveMode] = useState<'scanner' | 'manual'>('scanner');
  
  // Section filter within Mode 1 (all, pnl, liabilities, assets, banking)
  const [sectionFilter, setSectionFilter] = useState<'all' | 'pnl' | 'liabilities' | 'assets' | 'banking'>('all');

  // Re-parse & Upload States
  const [isReparsing, setIsReparsing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [periodFilter, setPeriodFilter] = useState<string>('all');

  // Edit Single Record Modal State
  const [editingRecord, setEditingRecord] = useState<ExtractedDataRecord | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [editStatus, setEditStatus] = useState<string>('verified');
  const [editNotes, setEditNotes] = useState<string>('');

  // Manual Year-Wise State
  const defaultYears = ['FY 2024-25 (Audited)', 'FY 2025-26 (Provisional)', 'FY 2023-24 (Audited)'];
  const [availableYears, setAvailableYears] = useState<string[]>(defaultYears);
  const [selectedYear, setSelectedYear] = useState<string>('FY 2024-25 (Audited)');
  const [yearData, setYearData] = useState<Record<string, FinancialFormState>>({
    'FY 2024-25 (Audited)': { ...defaultFormState },
    'FY 2025-26 (Provisional)': { ...defaultFormState },
    'FY 2023-24 (Audited)': { ...defaultFormState },
  });
  const [isSavingManual, setIsSavingManual] = useState(false);
  const [newYearInput, setNewYearInput] = useState('');
  const [showAddYearInput, setShowAddYearInput] = useState(false);

  // Initialize manual form with existing extracted records if available
  useEffect(() => {
    if (extractedRecords.length > 0) {
      setYearData((prev) => {
        const updated = { ...prev };
        
        extractedRecords.forEach((rec) => {
          const period = rec.financial_period || 'FY 2024-25 (Audited)';
          if (!updated[period]) {
            updated[period] = { ...defaultFormState };
          }
          const val = typeof rec.normalized_value === 'number' 
            ? rec.normalized_value 
            : parseFloat(String(rec.normalized_value || 0)) || 0;

          if (val > 0) {
            const key = rec.metric_name as keyof FinancialFormState;
            if (key in updated[period] && updated[period][key] === 0) {
              updated[period] = {
                ...updated[period],
                [key]: val,
              };
            }
          }
        });

        const foundPeriods = Array.from(new Set(extractedRecords.map(r => r.financial_period).filter(Boolean))) as string[];
        if (foundPeriods.length > 0) {
          setAvailableYears(prevYears => {
            const combined = Array.from(new Set([...prevYears, ...foundPeriods]));
            return combined;
          });
        }

        return updated;
      });
    }
  }, [extractedRecords]);

  // Handle Re-parse all documents
  const handleReparseDocuments = async () => {
    if (!confirm('This will re-run the spatial document parser on all uploaded case files, clearing obsolete or mismatched numbers. Continue?')) {
      return;
    }
    setIsReparsing(true);
    try {
      const res = await ApiClient.request<{ success: boolean; extracted_metrics_count: number; message: string }>(
        `/proposals/${proposalId}/extractions/reparse`,
        { method: 'POST' }
      );
      alert(res.message);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error re-parsing case documents');
    } finally {
      setIsReparsing(false);
    }
  };

  // Handle direct file upload from this tab
  const handleDirectFileUpload = async (file: File) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append('category', 'financial_statements');
    formData.append('file', file);
    try {
      await ApiClient.uploadFile(`/proposals/${proposalId}/documents`, formData);
      alert(`File '${file.name}' successfully uploaded! Refreshing parser now...`);
      const reparseRes = await ApiClient.request<{ success: boolean; extracted_metrics_count: number; message: string }>(
        `/proposals/${proposalId}/extractions/reparse`,
        { method: 'POST' }
      );
      alert(reparseRes.message);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'File upload error');
    } finally {
      setIsUploading(false);
    }
  };

  // Delete Single Extracted Record
  const handleDeleteRecord = async (recordId: string) => {
    if (!confirm('Are you sure you want to remove this data point?')) return;
    try {
      await ApiClient.request(`/proposals/${proposalId}/extractions/${recordId}`, {
        method: 'DELETE',
      });
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error deleting record');
    }
  };

  // Handle Single Record Edit Modal
  const handleOpenEdit = (rec: ExtractedDataRecord) => {
    setEditingRecord(rec);
    setEditValue(rec.normalized_value !== null && rec.normalized_value !== undefined ? String(rec.normalized_value) : '');
    setEditStatus(rec.verification_status === 'unverified' ? 'verified' : rec.verification_status);
    setEditNotes(rec.reviewer_notes || '');
  };

  const handleSaveEdit = async () => {
    if (!editingRecord) return;
    try {
      await ApiClient.request(`/proposals/${proposalId}/extractions/${editingRecord.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          normalized_value: editValue ? parseFloat(editValue) : null,
          verification_status: editStatus,
          reviewer_notes: editNotes,
        }),
      });
      setEditingRecord(null);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error updating record');
    }
  };

  // Update field in current manual year form
  const handleFormChange = (field: keyof FinancialFormState, val: number) => {
    setYearData((prev) => ({
      ...prev,
      [selectedYear]: {
        ...(prev[selectedYear] || defaultFormState),
        [field]: val,
      },
    }));
  };

  // Manual Calculations for currently selected year
  const curr = yearData[selectedYear] || defaultFormState;
  const calcTotalIncome = (curr.revenue_from_operations || 0) + (curr.other_income || 0);
  const calcEbitda = calcTotalIncome - ((curr.cost_of_goods_sold || 0) + (curr.employee_benefits_expense || 0) + (curr.other_expenses || 0));
  const calcTotalExp = (curr.cost_of_goods_sold || 0) + (curr.employee_benefits_expense || 0) + (curr.finance_costs || 0) + (curr.depreciation || 0) + (curr.other_expenses || 0);
  const calcPbt = calcTotalIncome - calcTotalExp;
  const calcPat = curr.pat !== 0 ? curr.pat : (calcPbt - (curr.tax_expense || 0));
  
  const calcCurrentLiabilities = (curr.short_term_borrowings || 0) + (curr.trade_payables || 0) + (curr.other_current_liabilities || 0);
  const calcTotalLiabilities = (curr.tangible_net_worth || 0) + (curr.long_term_borrowings || 0) + calcCurrentLiabilities;
  const calcCurrentAssets = (curr.inventories || 0) + (curr.trade_receivables || 0) + (curr.cash_and_bank || 0) + (curr.other_current_assets || 0);
  const calcTotalAssets = (curr.fixed_assets || 0) + calcCurrentAssets;
  const balanceDiff = Math.abs(calcTotalAssets - calcTotalLiabilities);
  const isBalanced = balanceDiff < 1.0;
  const netWorkingCapital = calcCurrentAssets - calcCurrentLiabilities;

  // Handle Save Manual Year-Wise Financials
  const handleSaveManualFinancials = async () => {
    setIsSavingManual(true);
    try {
      const entriesToSave = Object.entries(yearData)
        .filter(([_, f]) => f.revenue_from_operations > 0 || f.tangible_net_worth > 0 || f.pat > 0)
        .map(([period, f]) => ({
          financial_period: period,
          revenue_from_operations: f.revenue_from_operations,
          other_income: f.other_income,
          cost_of_goods_sold: f.cost_of_goods_sold,
          employee_benefits_expense: f.employee_benefits_expense,
          finance_costs: f.finance_costs,
          depreciation: f.depreciation,
          other_expenses: f.other_expenses,
          tax_expense: f.tax_expense,
          pat: f.pat || (calcPbt - f.tax_expense),

          tangible_net_worth: f.tangible_net_worth,
          long_term_borrowings: f.long_term_borrowings,
          short_term_borrowings: f.short_term_borrowings,
          trade_payables: f.trade_payables,
          other_current_liabilities: f.other_current_liabilities,
          fixed_assets: f.fixed_assets,
          inventories: f.inventories,
          trade_receivables: f.trade_receivables,
          cash_and_bank: f.cash_and_bank,
          other_current_assets: f.other_current_assets,
        }));

      if (entriesToSave.length === 0) {
        alert('Please enter figures for at least one financial year before saving.');
        setIsSavingManual(false);
        return;
      }

      const res = await ApiClient.request<{ success: boolean; saved_metrics_count: number; message: string }>(
        `/proposals/${proposalId}/extractions/manual-financials`,
        {
          method: 'POST',
          body: JSON.stringify({
            entries: entriesToSave,
            sync_to_cma: true,
          }),
        }
      );

      alert(`Success! ${res.message}\nData has been synchronized into the 9-Year CMA Workspace and Financial Underwriting forms.`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error saving manual financials');
    } finally {
      setIsSavingManual(false);
    }
  };

  // Add custom financial year
  const handleAddYear = () => {
    if (!newYearInput.trim()) return;
    const name = newYearInput.trim();
    if (!availableYears.includes(name)) {
      setAvailableYears([...availableYears, name]);
      setYearData(prev => ({
        ...prev,
        [name]: { ...defaultFormState }
      }));
      setSelectedYear(name);
    }
    setNewYearInput('');
    setShowAddYearInput(false);
  };

  // Filter records in scanner mode
  const displayedRecords = useMemo(() => {
    return extractedRecords.filter(rec => {
      if (periodFilter === 'all') return true;
      return (rec.financial_period || '').includes(periodFilter);
    });
  }, [extractedRecords, periodFilter]);

  // Group records strictly following Financial Statement (FS) structure
  const { pnlRecords, liabilityRecords, assetRecords, bankingRecords, otherRecords } = useMemo(() => {
    const pnl: ExtractedDataRecord[] = [];
    const liab: ExtractedDataRecord[] = [];
    const ast: ExtractedDataRecord[] = [];
    const bnk: ExtractedDataRecord[] = [];
    const oth: ExtractedDataRecord[] = [];

    displayedRecords.forEach(rec => {
      const meta = METRIC_METADATA[rec.metric_name];
      const cat = meta ? meta.category : 'other';
      if (cat === 'pnl') pnl.push(rec);
      else if (cat === 'liabilities') liab.push(rec);
      else if (cat === 'assets') ast.push(rec);
      else if (cat === 'banking') bnk.push(rec);
      else oth.push(rec);
    });

    const sortByFsOrder = (a: ExtractedDataRecord, b: ExtractedDataRecord) => {
      const ordA = METRIC_METADATA[a.metric_name]?.order ?? 999;
      const ordB = METRIC_METADATA[b.metric_name]?.order ?? 999;
      if (ordA !== ordB) return ordA - ordB;
      return (a.financial_period || '').localeCompare(b.financial_period || '');
    };

    pnl.sort(sortByFsOrder);
    liab.sort(sortByFsOrder);
    ast.sort(sortByFsOrder);
    bnk.sort(sortByFsOrder);
    oth.sort(sortByFsOrder);

    return {
      pnlRecords: pnl,
      liabilityRecords: liab,
      assetRecords: ast,
      bankingRecords: bnk,
      otherRecords: oth
    };
  }, [displayedRecords]);

  // Helper renderer for a single table of structured records
  const renderRecordsTable = (records: ExtractedDataRecord[], emptyMessage: string) => {
    if (records.length === 0) {
      return (
        <div className="py-6 text-center text-slate-400 italic text-xs bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
          {emptyMessage}
        </div>
      );
    }

    return (
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-left text-xs min-w-[850px]">
          <thead className="bg-[#1b2632] text-white font-semibold uppercase text-[10px] tracking-wider">
            <tr>
              <th className="py-2.5 px-3 min-w-[260px]">Financial Statement Particulars</th>
              <th className="py-2.5 px-3">Period</th>
              <th className="py-2.5 px-3">Page / Source</th>
              <th className="py-2.5 px-3">Raw String</th>
              <th className="py-2.5 px-3 text-right">Amount (INR ₹)</th>
              <th className="py-2.5 px-3 text-center">Confidence</th>
              <th className="py-2.5 px-3 text-center">Status</th>
              <th className="py-2.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
            {records.map((rec) => {
              const meta = METRIC_METADATA[rec.metric_name];
              const displayLabel = meta ? meta.label : rec.metric_name.replace(/_/g, ' ').toUpperCase();
              const isVerified = rec.verification_status === 'verified';
              const isAdjusted = rec.verification_status === 'adjusted';
              const rowHighlight = meta?.rowHighlight || 'hover:bg-slate-50';

              return (
                <tr key={rec.id} className={`transition-colors ${rowHighlight}`}>
                  <td className="py-2.5 px-3 font-sans">
                    <div className="font-semibold text-slate-900">{displayLabel}</div>
                    <div className="text-[10px] text-slate-500 font-mono uppercase font-normal">{rec.metric_name}</div>
                  </td>
                  <td className="py-2.5 px-3 text-slate-700 whitespace-nowrap">{rec.financial_period || '—'}</td>
                  <td className="py-2.5 px-3 text-slate-500">{rec.page_or_sheet || 'Page 1'}</td>
                  <td className="py-2.5 px-3 text-slate-600 max-w-[160px] truncate" title={rec.raw_value || ''}>
                    {rec.raw_value || '—'}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-slate-900 text-xs">
                    {rec.normalized_value !== null ? formatINR(rec.normalized_value, unitMode) : '—'}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                      {Math.round(rec.confidence * 100)}%
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-sans font-semibold ${
                        isVerified
                          ? 'bg-emerald-100 text-emerald-800'
                          : isAdjusted
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {rec.verification_status.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(rec)}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-100 hover:bg-brand-50 hover:text-brand-800 text-slate-700 border border-slate-200 text-xs font-sans font-semibold transition-colors cursor-pointer"
                        title="Verify or adjust figure"
                      >
                        <Edit3 className="w-3 h-3 text-[#a45139]" />
                        <span>Adjust</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteRecord(rec.id)}
                        className="p-1 rounded bg-slate-100 hover:bg-rose-50 hover:text-rose-700 text-slate-400 border border-slate-200 transition-colors cursor-pointer"
                        title="Remove metric"
                      >
                        <Trash2 className="w-3 h-3 text-rose-500" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Top Banner & Dual-Mode Toggle */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="font-bold text-slate-900 text-sm">Financial Statements &amp; Data Import</h4>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-50 text-brand-900 border border-brand-200">
              Structured FS Presentation
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Classified strictly by <strong>P&amp;L (Revenue, COGS, EBITDA, PAT)</strong>, <strong>Capital &amp; Liabilities</strong>, and <strong>Assets</strong>.
          </p>
        </div>

        {/* Dual Mode Switcher Pills */}
        <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveMode('scanner')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition-all cursor-pointer ${
              activeMode === 'scanner' 
                ? 'bg-[#1b2632] text-white shadow font-bold' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5 text-[#ebb9ab]" />
            <span>Document Scan &amp; Auto-Extract</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveMode('manual')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition-all cursor-pointer ${
              activeMode === 'manual' 
                ? 'bg-[#1b2632] text-white shadow font-bold' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Edit3 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Manual Year-Wise Data Entry</span>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* MODE 1: AUTOMATED DOCUMENT SCAN & FS-STRUCTURED PRESENTATION */}
      {/* ========================================================================= */}
      {activeMode === 'scanner' && (
        <div className="space-y-4">
          {/* Action Header: Re-parse, Direct Upload & Period Filter */}
          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-3">
              <span className="font-semibold text-slate-800">
                {displayedRecords.length} Data Points
              </span>

              {/* Financial Period Filter */}
              <div className="flex items-center gap-1.5 border-l border-slate-300 pl-3">
                <Filter className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-slate-500">Period:</span>
                <select
                  value={periodFilter}
                  onChange={(e) => setPeriodFilter(e.target.value)}
                  className="bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 font-semibold cursor-pointer shadow-2xs"
                >
                  <option value="all">All Financial Periods</option>
                  <option value="2024-25">FY 2024-25 (Audited Base Year)</option>
                  <option value="2025-26">FY 2025-26 (Provisional / Current)</option>
                  <option value="2023-24">FY 2023-24 (Audited)</option>
                </select>
              </div>

              {/* Section Sub-Filter */}
              <div className="hidden sm:flex items-center gap-1 border-l border-slate-300 pl-3">
                <button
                  type="button"
                  onClick={() => setSectionFilter('all')}
                  className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                    sectionFilter === 'all' ? 'bg-[#1b2632] text-white' : 'text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  All Sections
                </button>
                <button
                  type="button"
                  onClick={() => setSectionFilter('pnl')}
                  className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                    sectionFilter === 'pnl' ? 'bg-brand-900 text-white' : 'text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  P&amp;L ({pnlRecords.length})
                </button>
                <button
                  type="button"
                  onClick={() => setSectionFilter('liabilities')}
                  className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                    sectionFilter === 'liabilities' ? 'bg-brand-900 text-white' : 'text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Liab &amp; Capital ({liabilityRecords.length})
                </button>
                <button
                  type="button"
                  onClick={() => setSectionFilter('assets')}
                  className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                    sectionFilter === 'assets' ? 'bg-brand-900 text-white' : 'text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  Assets ({assetRecords.length})
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Direct Upload Button */}
              <label className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 rounded-lg font-semibold border border-slate-300 shadow-2xs transition-all cursor-pointer">
                <UploadCloud className="w-3.5 h-3.5 text-blue-600" />
                <span>{isUploading ? 'Uploading & Parsing...' : 'Scan / Upload PDF'}</span>
                <input
                  type="file"
                  accept=".pdf,.xlsx,.xls,.png,.jpg"
                  className="hidden"
                  disabled={isUploading}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleDirectFileUpload(e.target.files[0]);
                    }
                  }}
                />
              </label>

              {/* Re-parse Button */}
              <button
                type="button"
                onClick={handleReparseDocuments}
                disabled={isReparsing}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#a45139] hover:bg-[#8e4430] text-white rounded-lg font-semibold shadow-2xs transition-all cursor-pointer"
                title="Clears stale/mismatched numbers and re-runs coordinate parser on all case documents"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isReparsing ? 'animate-spin' : ''}`} />
                <span>{isReparsing ? 'Re-parsing Documents...' : 'Re-parse & Refresh Financials'}</span>
              </button>
            </div>
          </div>

          {/* =================================================================== */}
          {/* SECTION 1: STATEMENT OF PROFIT & LOSS (P&L) */}
          {/* =================================================================== */}
          {(sectionFilter === 'all' || sectionFilter === 'pnl') && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-emerald-50 text-emerald-800 rounded-lg border border-emerald-200">
                    <TrendingUp className="w-4 h-4" />
                  </div>
                  <div>
                    <h5 className="font-bold text-slate-900 text-xs flex items-center gap-2">
                      <span>Part I: Statement of Profit &amp; Loss (P&amp;L / Operating Statement)</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                        {pnlRecords.length} Line Items
                      </span>
                    </h5>
                    <p className="text-[11px] text-slate-500">
                      Standard Order: Revenue from Operations &rarr; Other Income &rarr; COGS &rarr; Employee Costs &rarr; Other Expenses &rarr; EBITDA &rarr; Finance Costs &rarr; Depreciation &rarr; PBT &rarr; PAT
                    </p>
                  </div>
                </div>
              </div>

              {renderRecordsTable(pnlRecords, "No P&L metrics extracted for this period. Click 'Re-parse & Refresh' or enter manually.")}
            </div>
          )}

          {/* =================================================================== */}
          {/* SECTION 2: BALANCE SHEET — CAPITAL & LIABILITIES */}
          {/* =================================================================== */}
          {(sectionFilter === 'all' || sectionFilter === 'liabilities') && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-brand-50 text-brand-900 rounded-lg border border-brand-200">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                  <div>
                    <h5 className="font-bold text-slate-900 text-xs flex items-center gap-2">
                      <span>Part II: Balance Sheet — Equity &amp; Liabilities</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-800">
                        {liabilityRecords.length} Line Items
                      </span>
                    </h5>
                    <p className="text-[11px] text-slate-500">
                      Standard Order: Capital / Net Worth (TNW) &rarr; Long-term Borrowings &rarr; Short-term Borrowings (CC/OD) &rarr; Trade Payables &rarr; Other Current Liabilities &rarr; Total Liabilities
                    </p>
                  </div>
                </div>
              </div>

              {renderRecordsTable(liabilityRecords, "No Liabilities metrics extracted for this period.")}
            </div>
          )}

          {/* =================================================================== */}
          {/* SECTION 3: BALANCE SHEET — ASSETS */}
          {/* =================================================================== */}
          {(sectionFilter === 'all' || sectionFilter === 'assets') && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-blue-50 text-blue-900 rounded-lg border border-blue-200">
                    <Layers className="w-4 h-4" />
                  </div>
                  <div>
                    <h5 className="font-bold text-slate-900 text-xs flex items-center gap-2">
                      <span>Part III: Balance Sheet — Assets</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-100 text-indigo-800">
                        {assetRecords.length} Line Items
                      </span>
                    </h5>
                    <p className="text-[11px] text-slate-500">
                      Standard Order: Fixed Assets (Property, Plant, Equip) &rarr; Inventories (Stock) &rarr; Trade Receivables (Debtors) &rarr; Cash &amp; Bank Balances &rarr; Other Current Assets &rarr; Total Assets
                    </p>
                  </div>
                </div>
              </div>

              {renderRecordsTable(assetRecords, "No Assets metrics extracted for this period.")}
            </div>
          )}

          {/* =================================================================== */}
          {/* SECTION 4: STATUTORY & BANKING METRICS (if present) */}
          {/* =================================================================== */}
          {bankingRecords.length > 0 && (sectionFilter === 'all' || sectionFilter === 'banking') && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-amber-50 text-amber-900 rounded-lg border border-amber-200">
                    <Landmark className="w-4 h-4" />
                  </div>
                  <div>
                    <h5 className="font-bold text-slate-900 text-xs flex items-center gap-2">
                      <span>Part IV: Statutory Filings &amp; Banking Benchmarks</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800">
                        {bankingRecords.length} Line Items
                      </span>
                    </h5>
                    <p className="text-[11px] text-slate-500">
                      ITR Acknowledgement, GSTR-3B Outward Turnover &amp; Bank Statement Turnover
                    </p>
                  </div>
                </div>
              </div>

              {renderRecordsTable(bankingRecords, "No Statutory / Banking figures extracted.")}
            </div>
          )}

          {/* =================================================================== */}
          {/* SECTION 5: OTHER SUPPORTING METRICS (if any) */}
          {/* =================================================================== */}
          {otherRecords.length > 0 && sectionFilter === 'all' && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-slate-100 text-slate-800 rounded-lg border border-slate-300">
                    <FileSpreadsheet className="w-4 h-4" />
                  </div>
                  <div>
                    <h5 className="font-bold text-slate-900 text-xs flex items-center gap-2">
                      <span>Part V: Other Supporting Notes &amp; Data Points</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-200 text-slate-800">
                        {otherRecords.length} Items
                      </span>
                    </h5>
                  </div>
                </div>
              </div>

              {renderRecordsTable(otherRecords, "No additional metrics.")}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE 2: MANUAL YEAR-WISE FINANCIALS ENTRY */}
      {/* ========================================================================= */}
      {activeMode === 'manual' && (
        <div className="space-y-4">
          {/* Year Navigation Bar */}
          <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 overflow-x-auto">
              <span className="text-xs font-bold text-slate-600 mr-1">Financial Period:</span>
              {availableYears.map((yr) => (
                <button
                  key={yr}
                  type="button"
                  onClick={() => setSelectedYear(yr)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    selectedYear === yr
                      ? 'bg-[#1b2632] text-white shadow'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  {yr}
                </button>
              ))}

              {showAddYearInput ? (
                <div className="flex items-center gap-1 ml-1">
                  <input
                    type="text"
                    value={newYearInput}
                    onChange={(e) => setNewYearInput(e.target.value)}
                    placeholder="e.g. FY 2022-23 (Audited)"
                    className="border border-slate-300 rounded px-2 py-1 text-xs"
                    autoFocus
                  />
                  <button
                    onClick={handleAddYear}
                    className="p-1 bg-emerald-600 text-white rounded hover:bg-emerald-700"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setShowAddYearInput(false)}
                    className="p-1 bg-slate-200 text-slate-600 rounded hover:bg-slate-300"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowAddYearInput(true)}
                  className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-semibold border border-dashed border-slate-300 transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Year</span>
                </button>
              )}
            </div>

            <div className="flex items-center gap-3">
              {/* Balance Sheet Balancing Check Badge */}
              <div
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold border ${
                  isBalanced
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : 'bg-amber-50 text-amber-800 border-amber-200'
                }`}
              >
                {isBalanced ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Balance Sheet Reconciled (Assets = Liabilities)</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-amber-600" />
                    <span>Diff: {formatINR(balanceDiff, unitMode)} (Assets ≠ Liab)</span>
                  </>
                )}
              </div>

              {/* Save Button */}
              <button
                type="button"
                onClick={handleSaveManualFinancials}
                disabled={isSavingManual}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#1b2632] hover:bg-[#28384a] text-white rounded-lg text-xs font-semibold shadow-sm transition-all cursor-pointer"
              >
                <Save className="w-4 h-4 text-[#ebb9ab]" />
                <span>{isSavingManual ? 'Saving Financials...' : 'Save Year-Wise Financials'}</span>
              </button>
            </div>
          </div>

          {/* Two-Column Grid: P&L Statement (Left) vs Balance Sheet (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* CARD 1: STATEMENT OF PROFIT & LOSS */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-brand-50 text-brand-900 rounded-lg">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <h5 className="font-bold text-slate-900 text-xs">Part I: Statement of Profit &amp; Loss (P&amp;L)</h5>
                    <p className="text-[10px] text-slate-500">Period: {selectedYear}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-500 block">Gross Cash Accrual</span>
                  <span className="font-bold text-emerald-700 text-xs font-mono">
                    {formatINR((calcPat || 0) + (curr.depreciation || 0), unitMode)}
                  </span>
                </div>
              </div>

              <div className="space-y-2.5 text-xs">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">
                    Revenue from Operations (Gross Sales / Turnover) (₹)
                  </label>
                  <NumberInput
                    value={curr.revenue_from_operations}
                    onChange={(val) => handleFormChange('revenue_from_operations', val)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900 focus:bg-white"
                    placeholder="e.g. 190000000"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Other Operating &amp; Non-Operating Income (₹)</label>
                  <NumberInput
                    value={curr.other_income}
                    onChange={(val) => handleFormChange('other_income', val)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                    placeholder="e.g. 450000"
                  />
                </div>

                {/* Subtotal Total Income */}
                <div className="p-2 rounded-lg bg-slate-100 flex items-center justify-between font-semibold text-slate-800">
                  <span>Total Income (Gross Revenue)</span>
                  <span className="font-mono text-slate-950 font-bold">{formatINR(calcTotalIncome, unitMode)}</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                  <div>
                    <label className="block text-slate-600 mb-1">Cost of Goods Sold (COGS / Purchases) (₹)</label>
                    <NumberInput
                      value={curr.cost_of_goods_sold}
                      onChange={(val) => handleFormChange('cost_of_goods_sold', val)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-600 mb-1">Employee Expenses (Salaries &amp; Wages) (₹)</label>
                    <NumberInput
                      value={curr.employee_benefits_expense}
                      onChange={(val) => handleFormChange('employee_benefits_expense', val)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-slate-600 mb-1">Finance Costs (Bank Interest &amp; Charges) (₹)</label>
                    <NumberInput
                      value={curr.finance_costs}
                      onChange={(val) => handleFormChange('finance_costs', val)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-600 mb-1">Depreciation &amp; Amortization (₹)</label>
                    <NumberInput
                      value={curr.depreciation}
                      onChange={(val) => handleFormChange('depreciation', val)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-600 mb-1">Other Administrative &amp; Operating Expenses (₹)</label>
                  <NumberInput
                    value={curr.other_expenses}
                    onChange={(val) => handleFormChange('other_expenses', val)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                  />
                </div>

                {/* Operating Profit EBITDA */}
                <div className="p-2 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-between text-emerald-900 font-semibold">
                  <div>
                    <span>Operating Profit (EBITDA)</span>
                    <span className="text-[10px] text-emerald-700 block font-normal">
                      Margin: {calcTotalIncome > 0 ? ((calcEbitda / calcTotalIncome) * 100).toFixed(1) : 0}%
                    </span>
                  </div>
                  <span className="font-mono text-sm font-bold">{formatINR(calcEbitda, unitMode)}</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-slate-600 mb-1">Provision for Tax (₹)</label>
                    <NumberInput
                      value={curr.tax_expense}
                      onChange={(val) => handleFormChange('tax_expense', val)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-700 font-semibold mb-1">Profit After Tax (PAT) (₹)</label>
                    <NumberInput
                      value={curr.pat || calcPat}
                      onChange={(val) => handleFormChange('pat', val)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900 focus:bg-white"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* CARD 2: BALANCE SHEET */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-blue-50 text-blue-900 rounded-lg">
                    <Landmark className="w-4 h-4" />
                  </div>
                  <div>
                    <h5 className="font-bold text-slate-900 text-xs">Part II &amp; III: Balance Sheet Analysis</h5>
                    <p className="text-[10px] text-slate-500">Period: {selectedYear}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-500 block">Net Working Capital (NWC)</span>
                  <span className="font-bold text-blue-700 text-xs font-mono">
                    {formatINR(netWorkingCapital, unitMode)}
                  </span>
                </div>
              </div>

              <div className="space-y-2.5 text-xs">
                {/* Equity & Liabilities Section */}
                <div className="border-b border-slate-100 pb-3 space-y-2">
                  <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wide">
                    II. Capital &amp; Liabilities
                  </span>

                  <div>
                    <label className="block text-slate-700 font-semibold mb-1">
                      Owner's Capital / Tangible Net Worth (TNW) (₹)
                    </label>
                    <NumberInput
                      value={curr.tangible_net_worth}
                      onChange={(val) => handleFormChange('tangible_net_worth', val)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900 focus:bg-white"
                      placeholder="e.g. 13585024"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <div>
                      <label className="block text-slate-600 mb-1">Long-term Borrowings (Term Loans) (₹)</label>
                      <NumberInput
                        value={curr.long_term_borrowings}
                        onChange={(val) => handleFormChange('long_term_borrowings', val)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-600 mb-1">Short-term Bank Borrowings (CC/OD) (₹)</label>
                      <NumberInput
                        value={curr.short_term_borrowings}
                        onChange={(val) => handleFormChange('short_term_borrowings', val)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <div>
                      <label className="block text-slate-600 mb-1">Sundry Creditors / Trade Payables (₹)</label>
                      <NumberInput
                        value={curr.trade_payables}
                        onChange={(val) => handleFormChange('trade_payables', val)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-600 mb-1">Other Current Liabilities &amp; Provisions (₹)</label>
                      <NumberInput
                        value={curr.other_current_liabilities}
                        onChange={(val) => handleFormChange('other_current_liabilities', val)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                      />
                    </div>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-100 flex items-center justify-between font-semibold text-slate-800">
                    <span>Total Liabilities &amp; Equity</span>
                    <span className="font-mono text-slate-950 font-bold">{formatINR(calcTotalLiabilities, unitMode)}</span>
                  </div>
                </div>

                {/* Assets Section */}
                <div className="space-y-2 pt-1">
                  <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wide">
                    III. Assets
                  </span>

                  <div>
                    <label className="block text-slate-700 font-semibold mb-1">
                      Fixed Assets (Property, Plant, Equipment &amp; Net Block) (₹)
                    </label>
                    <NumberInput
                      value={curr.fixed_assets}
                      onChange={(val) => handleFormChange('fixed_assets', val)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-900 focus:bg-white"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <div>
                      <label className="block text-slate-600 mb-1">Inventories / Closing Stock (₹)</label>
                      <NumberInput
                        value={curr.inventories}
                        onChange={(val) => handleFormChange('inventories', val)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-600 mb-1">Sundry Debtors / Trade Receivables (₹)</label>
                      <NumberInput
                        value={curr.trade_receivables}
                        onChange={(val) => handleFormChange('trade_receivables', val)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <div>
                      <label className="block text-slate-600 mb-1">Cash &amp; Bank Balances (₹)</label>
                      <NumberInput
                        value={curr.cash_and_bank}
                        onChange={(val) => handleFormChange('cash_and_bank', val)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-600 mb-1">Other Current Assets, Loans &amp; Advances (₹)</label>
                      <NumberInput
                        value={curr.other_current_assets}
                        onChange={(val) => handleFormChange('other_current_assets', val)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-slate-800 focus:bg-white"
                      />
                    </div>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-100 flex items-center justify-between font-semibold text-slate-800">
                    <span>Total Assets</span>
                    <span className="font-mono text-slate-950 font-bold">{formatINR(calcTotalAssets, unitMode)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit & Verification Modal */}
      {editingRecord && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-2xl border border-slate-200">
            <h4 className="font-bold text-slate-900 text-sm mb-1">
              Verify / Adjust Extracted Metric
            </h4>
            <p className="text-xs text-slate-500 mb-4">
              Particulars: <strong>{METRIC_METADATA[editingRecord.metric_name]?.label || editingRecord.metric_name}</strong> | Period: <strong>{editingRecord.financial_period}</strong>
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Normalized Value (INR ₹)</label>
                <input
                  type="number"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  step="0.01"
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 font-semibold"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Verification Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800"
                >
                  <option value="verified">Verified (Confirmed from Document)</option>
                  <option value="adjusted">Adjusted (Manual Analyst Correction)</option>
                  <option value="rejected">Rejected (Disputed / Mismatched)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Reviewer Justification Notes</label>
                <textarea
                  rows={2}
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="e.g. Cross-checked with CA-certified Financials Schedule..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800"
                />
              </div>
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditingRecord(null)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-[#1b2632] hover:bg-[#28384a] text-white shadow-sm cursor-pointer"
              >
                Save Verification
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};