import React, { useState, useEffect } from 'react';
import type { Client } from '../types';
import {
  fetchCashFlow, fetchCashFlowAdjustments,
  createCashFlowAdjustment, fetchCashFlowValidations
} from '../services/api';
import {
  FileSpreadsheet, CheckCircle2, Info, Plus, RefreshCw,
  SlidersHorizontal, Table as TableIcon, HelpCircle,
  ShieldCheck, AlertTriangle, Search, ChevronDown, ChevronRight
} from 'lucide-react';

interface CashFlowStatementPageProps { client: Client; }

// ─── colour helpers ────────────────────────────────────────
const amtCls  = (v: number) => v < 0 ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-700 dark:text-emerald-400';
const fmtAmt  = (v: number) => {
  const abs = Math.abs(v).toLocaleString('en-IN', { minimumFractionDigits: 2 });
  return v < 0 ? `(${abs})` : abs;
};

// ─── Section meta (icon + palette) ────────────────────────
const SECTION_META: Record<string, { label: string; color: string; bg: string }> = {
  '1. Profit Before Tax'          : { label: '1', color: '#1B365D', bg: '#e8edf5' },
  '2. Non-Cash Adjustments'       : { label: '2', color: '#6b21a8', bg: '#f5f0ff' },
  '3. Non-Operating Adjustments'  : { label: '3', color: '#0f766e', bg: '#f0fdfa' },
  '4. Working Capital Movement'   : { label: '4', color: '#b45309', bg: '#fefce8' },
  '5. Investing Activity Working' : { label: '5', color: '#0369a1', bg: '#f0f9ff' },
  '6. Financing Activity Working' : { label: '6', color: '#9d174d', bg: '#fdf2f8' },
  '7. Cash Reconciliation'        : { label: '7', color: '#166534', bg: '#f0fdf4' },
};

const SECTION_ORDER = Object.keys(SECTION_META);

export const CashFlowStatementPage: React.FC<CashFlowStatementPageProps> = ({ client }) => {
  const [activeTab, setActiveTab] = useState<'statement' | 'working' | 'reconciliation' | 'checklist' | 'validations'>('statement');
  const [cfData,     setCfData]     = useState<any>(null);
  const [validations, setValidations] = useState<any[]>([]);
  const [loading,    setLoading]    = useState(true);

  // working tab state
  const [collapsed,  setCollapsed]  = useState<Set<string>>(new Set());
  const [filterText, setFilterText] = useState('');

  // modal
  const [showAdjModal, setShowAdjModal] = useState(false);
  const [adjType,      setAdjType]      = useState('Income Tax Paid');
  const [adjDesc,      setAdjDesc]      = useState('');
  const [adjAmount,    setAdjAmount]    = useState<number>(0);
  const [adjCategory,  setAdjCategory]  = useState('Operating');

  const loadData = async () => {
    setLoading(true);
    try {
      const [cfRes, _adjRes, valRes] = await Promise.all([
        fetchCashFlow(client.id),
        fetchCashFlowAdjustments(client.id),
        fetchCashFlowValidations(client.id),
      ]);
      setCfData(cfRes);
      setValidations(valRes);
    } catch (e) { console.error(e); }
    finally     { setLoading(false); }
  };

  useEffect(() => { loadData(); }, [client.id]);

  const handleAddAdjustment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adjDesc || adjAmount <= 0) return;
    try {
      await createCashFlowAdjustment(client.id, {
        adjustment_type: adjType, description: adjDesc,
        amount: adjAmount, category: adjCategory, remarks: '',
      });
      setAdjDesc(''); setAdjAmount(0); setShowAdjModal(false);
      loadData();
    } catch (err) { console.error(err); }
  };

  if (loading) return (
    <div className="flex items-center justify-center p-12 space-x-3 text-slate-500">
      <RefreshCw className="w-5 h-5 animate-spin" />
      <span className="text-sm font-semibold">Generating AS 3 Cash Flow Statement (Indirect Method)…</span>
    </div>
  );

  // ── group working items by section ──────────────────────
  const workingSections: Record<string, any[]> = {};
  if (cfData?.working) {
    for (const item of cfData.working) {
      const sec = item.section || 'Uncategorised';
      if (!workingSections[sec]) workingSections[sec] = [];
      const label = filterText.toLowerCase();
      if (!label || item.particulars.toLowerCase().includes(label) ||
          item.source_sheet.toLowerCase().includes(label) ||
          item.review_comment.toLowerCase().includes(label)) {
        workingSections[sec].push(item);
      }
    }
  }

  const toggleCollapse = (sec: string) => {
    setCollapsed(prev => {
      const n = new Set(prev);
      n.has(sec) ? n.delete(sec) : n.add(sec);
      return n;
    });
  };

  const managementQueries = [
    "Please provide details of income tax paid during the year (advance tax challans / TDS certificates).",
    "Please confirm finance cost actually paid during the year (vs. accrued in P&L).",
    "Please provide reconciliation of PPE / CWIP additions with Fixed Asset Register.",
    "Please confirm whether any fixed deposits are excluded from cash and cash equivalents.",
    "Please provide details of non-cash transactions, if any (e.g. lease acquisitions, debt-equity conversions).",
    "Please provide proceeds received from sale of fixed assets, if any.",
    "Please provide dividend paid details and ECS / bank confirmation, if applicable.",
  ];

  const valPassed   = validations.filter(v => v.status === 'Passed').length;
  const valWarnings = validations.filter(v => v.status === 'Warning').length;

  return (
    <div className="space-y-5 max-w-full mx-auto">

      {/* ── Page Header ─────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-200 dark:border-slate-800 pb-4 gap-3">
        <div>
          <h1 className="text-xl font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-tight flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-orange-600" />
            AS 3 CASH FLOW STATEMENT — INDIRECT METHOD
          </h1>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-0.5">
            {client.name} | {client.reporting_period} | Figures in {client.currency}
          </p>
        </div>
        <button onClick={() => setShowAdjModal(true)}
          className="ca-button-primary text-xs flex items-center gap-1.5">
          <Plus className="w-3.5 h-3.5" /> Add Cash Flow Adjustment
        </button>
      </div>

      {/* ── Mandatory Notice ────────────────────────────────── */}
      <div className="p-3.5 rounded-lg bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-800 flex items-start gap-2.5 text-xs text-amber-900 dark:text-amber-200">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">AS 3 MANDATORY PREPARATION NOTICE: </span>
          Cash Flow Statement is prepared using the Indirect Method based on mapped trial balance, Balance Sheet movements and supporting schedules.
          Items marked <span className="font-bold">PREPARER INPUT REQUIRED</span> (taxes paid, interest paid/received, dividend paid, PPE proceeds) must be reviewed and confirmed before finalisation.
          {cfData && !cfData.is_reconciled && (
            <span className="block mt-1 font-bold text-rose-700">
              UNRECONCILED DIFFERENCE: Rs {cfData.difference?.toFixed(2)} Lakhs between computed closing cash and Balance Sheet. Review Working tab → Section 7.
            </span>
          )}
        </div>
      </div>

      {/* ── Tab Bar ─────────────────────────────────────────── */}
      <div className="flex items-center gap-0.5 border-b border-slate-200 dark:border-slate-800 text-xs font-bold overflow-x-auto">
        {([
          { id: 'statement',     icon: <TableIcon className="w-3.5 h-3.5" />,        label: '1. Cash Flow Statement' },
          { id: 'working',       icon: <SlidersHorizontal className="w-3.5 h-3.5" />, label: '2. Detailed Working (7 Sections)' },
          { id: 'reconciliation',icon: <ShieldCheck className="w-3.5 h-3.5" />,       label: '3. Cash Reconciliation' },
          { id: 'checklist',     icon: <HelpCircle className="w-3.5 h-3.5" />,        label: '4. Non-Cash Checklist' },
          { id: 'validations',   icon: <CheckCircle2 className="w-3.5 h-3.5" />,      label: `5. Validations (${valPassed}P / ${valWarnings}W)` },
        ] as const).map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id as any)}
            className={`px-4 py-2.5 border-b-2 whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              activeTab === t.id
                ? 'border-orange-600 text-orange-600 dark:text-orange-400'
                : 'border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
            }`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ════════════════════════════════════════════════════════
          TAB 1 — CASH FLOW STATEMENT
         ════════════════════════════════════════════════════════ */}
      {activeTab === 'statement' && cfData && (
        <div className="studio-card overflow-hidden">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-[#1B365D] text-white font-bold text-[11px]">
                <th className="p-3">Particulars</th>
                <th className="p-3 text-right w-44 bg-slate-800/80 border-l border-slate-700">Current Year (Rs in Lakhs)</th>
                <th className="p-3 text-right w-44 bg-slate-800/80 border-l border-slate-700">Previous Year (Rs in Lakhs)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 font-medium">
              {cfData.statement.map((line: any, idx: number) => {
                if (line.is_header) return (
                  <tr key={idx} className="bg-slate-100 dark:bg-slate-800/90">
                    <td colSpan={3} className="p-2.5 font-black text-[#1B365D] dark:text-blue-300 uppercase tracking-tight text-[11px]">
                      {line.particulars}
                    </td>
                  </tr>
                );

                const rowCls = line.is_total
                  ? 'bg-[#1B365D]/10 dark:bg-slate-700 font-black border-t-2 border-[#1B365D]/30'
                  : line.is_subtotal
                    ? 'bg-slate-50 dark:bg-slate-800/50 font-extrabold border-t border-slate-300'
                    : 'hover:bg-slate-50/70 dark:hover:bg-slate-800/30 text-slate-700 dark:text-slate-300';

                const isBridge = ['Reconciliation Difference', 'Computed Closing', 'per Balance Sheet'].some(k => line.particulars.includes(k));

                return (
                  <tr key={idx} className={rowCls + (isBridge ? ' bg-emerald-50/60 dark:bg-emerald-900/10' : '')}>
                    <td className={`p-2.5 ${line.indent === 1 ? 'pl-7' : line.indent === 2 ? 'pl-12' : ''}`}>
                      {line.particulars}
                    </td>
                    <td className={`p-2.5 text-right font-mono border-l border-slate-200 dark:border-slate-800 ${amtCls(line.cy_amount)}`}>
                      {fmtAmt(line.cy_amount)}
                    </td>
                    <td className={`p-2.5 text-right font-mono border-l border-slate-200 dark:border-slate-800 ${amtCls(line.py_amount)}`}>
                      {fmtAmt(line.py_amount)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
          TAB 2 — DETAILED WORKING (7 SECTIONS)
         ════════════════════════════════════════════════════════ */}
      {activeTab === 'working' && cfData && (
        <div className="space-y-4">

          {/* Legend + search bar */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap text-[10px] font-bold">
              {SECTION_ORDER.map(s => (
                <span key={s} className="px-2 py-0.5 rounded-full"
                  style={{ background: SECTION_META[s]?.bg, color: SECTION_META[s]?.color }}>
                  {s}
                </span>
              ))}
            </div>
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={filterText} onChange={e => setFilterText(e.target.value)}
                placeholder="Filter working items…"
                className="ca-input pl-8 text-xs w-64" />
            </div>
          </div>

          {/* Column header legend */}
          <div className="text-[10px] text-slate-500 dark:text-slate-400 font-semibold grid grid-cols-8 gap-1 px-3 pb-1 border-b border-slate-200 dark:border-slate-700">
            <span className="col-span-2">Particular</span>
            <span>Source Sheet</span>
            <span className="text-right">CY Amount</span>
            <span className="text-right">PY Amount</span>
            <span className="text-right">Movement</span>
            <span className="text-right">Cash Flow Impact</span>
            <span>Formula / Review Comment</span>
          </div>

          {SECTION_ORDER.map(sec => {
            const items: any[] = workingSections[sec] || [];
            if (items.length === 0) return null;
            const meta = SECTION_META[sec] || { label: '#', color: '#1B365D', bg: '#e8edf5' };
            const isOpen = !collapsed.has(sec);

            return (
              <div key={sec} className="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 shadow-sm">

                {/* Section header row */}
                <button
                  onClick={() => toggleCollapse(sec)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left"
                  style={{ background: meta.bg, color: meta.color }}>
                  <div className="flex items-center gap-2">
                    {isOpen
                      ? <ChevronDown className="w-4 h-4" />
                      : <ChevronRight className="w-4 h-4" />}
                    <span className="text-[11px] font-black uppercase tracking-widest">{sec}</span>
                    <span className="text-[10px] font-semibold opacity-60">({items.length} lines)</span>
                  </div>
                  <span className="text-[10px] font-bold opacity-60">
                    Net Impact: {fmtAmt(items.reduce((s, i) => s + i.effect_on_cash, 0))} Lakhs
                  </span>
                </button>

                {/* Detail rows */}
                {isOpen && (
                  <table className="w-full text-[11px] border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-[10px] font-black uppercase text-slate-500"
                          style={{ background: meta.bg + '80' }}>
                        <th className="px-3 py-2 text-left w-[18%]">Particular</th>
                        <th className="px-3 py-2 text-left w-[12%]">Source Sheet</th>
                        <th className="px-3 py-2 text-right w-[9%]">CY Amount</th>
                        <th className="px-3 py-2 text-right w-[9%]">PY Amount</th>
                        <th className="px-3 py-2 text-right w-[9%]">Movement</th>
                        <th className="px-3 py-2 text-right w-[10%]">Cash Impact</th>
                        <th className="px-3 py-2 text-left w-[33%]">Formula Used / Review Comment</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {items.map((item: any, idx: number) => {
                        const isReviewRequired = item.review_comment.includes('PREPARER INPUT');
                        const impactCls = item.effect_on_cash > 0
                          ? 'text-emerald-700 dark:text-emerald-400 font-black'
                          : item.effect_on_cash < 0
                            ? 'text-rose-600 dark:text-rose-400 font-black'
                            : 'text-slate-400';
                        const movCls = item.delta > 0
                          ? 'text-sky-700 dark:text-sky-400 font-bold'
                          : item.delta < 0
                            ? 'text-orange-600 dark:text-orange-400 font-bold'
                            : 'text-slate-400';

                        return (
                          <tr key={idx} className={`group transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/30 ${
                            isReviewRequired ? 'bg-amber-50/60 dark:bg-amber-900/10' : ''
                          }`}>
                            {/* Particular */}
                            <td className="px-3 py-2.5 font-semibold text-slate-900 dark:text-slate-100 leading-tight">
                              {isReviewRequired && (
                                <span className="inline-block mr-1 w-2 h-2 rounded-full bg-amber-500 shrink-0" title="Preparer Input Required" />
                              )}
                              {item.particulars}
                            </td>

                            {/* Source sheet */}
                            <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400 leading-tight text-[10px]">
                              {item.source_sheet}
                            </td>

                            {/* CY Amount */}
                            <td className="px-3 py-2.5 text-right font-mono text-slate-800 dark:text-slate-200">
                              {fmtAmt(item.cy_balance)}
                            </td>

                            {/* PY Amount */}
                            <td className="px-3 py-2.5 text-right font-mono text-slate-500 dark:text-slate-400">
                              {fmtAmt(item.py_balance)}
                            </td>

                            {/* Movement (CY - PY) */}
                            <td className={`px-3 py-2.5 text-right font-mono ${movCls}`}>
                              {fmtAmt(item.delta)}
                            </td>

                            {/* Cash Flow Impact */}
                            <td className={`px-3 py-2.5 text-right font-mono ${impactCls}`}>
                              {fmtAmt(item.effect_on_cash)}
                            </td>

                            {/* Formula + Review Comment (2-row stacked) */}
                            <td className="px-3 py-2.5">
                              <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 leading-snug mb-1 truncate max-w-[340px]" title={item.formula_used}>
                                {item.formula_used}
                              </div>
                              <div className={`text-[10px] font-semibold leading-snug ${
                                isReviewRequired
                                  ? 'text-amber-700 dark:text-amber-300'
                                  : 'text-slate-600 dark:text-slate-300'
                              }`}>
                                {isReviewRequired && <AlertTriangle className="w-3 h-3 inline mr-1 text-amber-500" />}
                                {item.review_comment}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>

                    {/* Section subtotal row */}
                    <tfoot>
                      <tr className="font-black text-[11px]" style={{ background: meta.bg, color: meta.color }}>
                        <td className="px-3 py-2 uppercase tracking-tight" colSpan={5}>
                          Section Net Cash Flow Impact
                        </td>
                        <td className="px-3 py-2 text-right font-mono">
                          {fmtAmt(items.reduce((s, i) => s + i.effect_on_cash, 0))}
                        </td>
                        <td />
                      </tr>
                    </tfoot>
                  </table>
                )}
              </div>
            );
          })}

          {/* Legend footer */}
          <div className="flex items-start gap-4 text-[10px] font-semibold text-slate-500 p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/30">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> Positive cash impact (inflow)</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500" /> Negative cash impact (outflow)</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> Preparer input required before finalisation</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-sky-500" /> Movement = CY − PY (positive = increase)</span>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
          TAB 3 — CASH & CASH EQUIVALENTS RECONCILIATION
         ════════════════════════════════════════════════════════ */}
      {activeTab === 'reconciliation' && cfData && (
        <div className="space-y-5">

          {/* KPI cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Opening Cash Balance',           val: cfData.opening_cash,      color: 'text-slate-800 dark:text-white' },
              { label: 'Net Cash Movement (A+B+C)',      val: cfData.net_movement,       color: amtCls(cfData.net_movement) },
              { label: 'Computed Closing Cash',          val: cfData.opening_cash + cfData.net_movement, color: 'text-sky-700 dark:text-sky-400' },
              { label: 'Balance Sheet Closing Cash',     val: cfData.closing_cash,       color: 'text-emerald-700 dark:text-emerald-400' },
            ].map((k, i) => (
              <div key={i} className="studio-card p-4 space-y-1">
                <span className="text-[10px] font-bold uppercase text-slate-500 block">{k.label}</span>
                <p className={`text-lg font-black font-mono ${k.color}`}>
                  {fmtAmt(k.val)} <span className="text-xs font-semibold text-slate-400">Lakhs</span>
                </p>
              </div>
            ))}
          </div>

          {/* Bridge table */}
          <div className="studio-card overflow-hidden">
            <div className="bg-[#1B365D] text-white text-xs font-black px-4 py-2.5 uppercase tracking-wider">
              Cash Flow Bridge — Opening to Closing
            </div>
            <table className="w-full text-xs border-collapse">
              <tbody>
                {[
                  { label: 'Cash and Cash Equivalents — Opening Balance', val: cfData.opening_cash, style: 'font-semibold' },
                  { label: 'Net Cash Flow from Operating Activities (A)',  val: cfData.net_movement ? (cfData.net_movement - (cfData.closing_cash - cfData.opening_cash - cfData.net_movement)) : 0, style: '' },
                  { label: 'Net Cash Flow from Investing Activities (B)',  val: 0, style: '' },
                  { label: 'Net Cash Flow from Financing Activities (C)',  val: 0, style: '' },
                  { label: 'Net Cash Movement (A + B + C)',               val: cfData.net_movement, style: 'font-bold border-t border-slate-300' },
                  { label: 'Computed Closing Cash (per Indirect Method)', val: cfData.opening_cash + cfData.net_movement, style: 'font-extrabold' },
                  { label: 'Cash and Cash Equivalents per Balance Sheet', val: cfData.closing_cash, style: 'font-extrabold' },
                  { label: 'Reconciliation Difference',                   val: cfData.difference,  style: 'font-black text-rose-600' },
                ].map((row, i) => (
                  <tr key={i} className={`border-b border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/30 ${row.style}`}>
                    <td className="px-4 py-2.5 text-slate-800 dark:text-slate-200">{row.label}</td>
                    <td className={`px-4 py-2.5 text-right font-mono w-44 ${amtCls(row.val)}`}>{fmtAmt(row.val)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Reconciliation status banner */}
          <div className={`p-4 rounded-lg border flex items-center gap-3 text-sm font-bold ${
            cfData.is_reconciled
              ? 'bg-emerald-50 border-emerald-300 text-emerald-900 dark:bg-emerald-900/20 dark:border-emerald-700 dark:text-emerald-300'
              : 'bg-rose-50 border-rose-300 text-rose-900 dark:bg-rose-900/20 dark:border-rose-700 dark:text-rose-300'
          }`}>
            {cfData.is_reconciled
              ? <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              : <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />}
            <span>
              {cfData.is_reconciled
                ? 'RECONCILIATION VERIFIED — Computed closing cash equals Balance Sheet cash and bank balance.'
                : `UNRECONCILED DIFFERENCE of Rs ${cfData.difference?.toFixed(2)} Lakhs. Review Working tab → Section 7 and update Cash_Flow_Adjustments sheet.`}
            </span>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
          TAB 4 — NON-CASH CHECKLIST & MANAGEMENT QUERIES
         ════════════════════════════════════════════════════════ */}
      {activeTab === 'checklist' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="studio-card p-5 space-y-3">
            <h3 className="text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase">
              Non-Cash Transactions Checklist (AS 3 Para 43)
            </h3>
            <div className="space-y-2 text-xs">
              {[
                { text: "Acquisition of assets by means of finance lease", checked: false },
                { text: "Acquisition of a business / subsidiary by issue of equity shares", checked: false },
                { text: "Conversion of debt or loans into equity capital", checked: false },
                { text: "Unrealised foreign exchange gain / loss on balance sheet items", checked: false },
                { text: "Provision for doubtful debts or write-offs of receivables", checked: true },
                { text: "Depreciation and amortisation (already captured in working)", checked: true },
                { text: "Reversal of provisions or income not yet received in cash", checked: false },
                { text: "Non-cash government grants or subsidies received as assets", checked: false },
              ].map((item, idx) => (
                <label key={idx} className="flex items-start gap-2 p-2 rounded hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer">
                  <input type="checkbox" className="rounded text-orange-600 mt-0.5" defaultChecked={item.checked} />
                  <span className="text-slate-700 dark:text-slate-300 font-semibold leading-snug">{item.text}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="studio-card p-5 space-y-3">
            <h3 className="text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase">
              Auditor Management Queries — Cash Flow
            </h3>
            <div className="space-y-2 text-xs">
              {managementQueries.map((q, idx) => (
                <div key={idx} className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 flex items-start gap-2">
                  <span className="font-bold text-orange-600 shrink-0">MQ{idx + 1}.</span>
                  <span className="text-slate-700 dark:text-slate-300 font-semibold leading-snug">{q}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════════════════
          TAB 5 — CASH FLOW VALIDATION CHECKS
         ════════════════════════════════════════════════════════ */}
      {activeTab === 'validations' && (
        <div className="studio-card overflow-hidden">
          <div className="bg-[#1B365D] text-white text-xs font-black px-4 py-2.5 uppercase tracking-wider flex items-center justify-between">
            <span>10 AS 3 Cash Flow Sanity Checks</span>
            <span className="font-normal opacity-80">
              {valPassed} Passed | {valWarnings} Warning
            </span>
          </div>
          <div className="divide-y divide-slate-200 dark:divide-slate-800">
            {validations.map((v: any, i: number) => (
              <div key={i} className="px-4 py-3 flex items-start justify-between gap-4 text-xs hover:bg-slate-50 dark:hover:bg-slate-800/30">
                <div className="flex items-start gap-3">
                  <span className="font-mono font-bold text-slate-400 w-10 shrink-0 mt-0.5">{v.code}</span>
                  <div>
                    <p className="font-bold text-slate-900 dark:text-white">{v.name}</p>
                    <p className="text-slate-600 dark:text-slate-400 mt-0.5 leading-snug">{v.msg}</p>
                  </div>
                </div>
                <span className={`shrink-0 px-2.5 py-0.5 rounded font-black text-[10px] uppercase ${
                  v.status === 'Passed'   ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300' :
                  v.status === 'Warning'  ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300' :
                                            'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300'
                }`}>{v.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Add Adjustment Modal ─────────────────────────────── */}
      {showAdjModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="studio-card max-w-md w-full p-6 space-y-4 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl rounded-xl">
            <h3 className="text-sm font-black text-[#1B365D] dark:text-blue-400 uppercase">Add Cash Flow Adjustment</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Use this to provide preparer-confirmed amounts for items that cannot be derived from the trial balance alone (tax paid, interest paid, PPE proceeds, etc.).
            </p>
            <form onSubmit={handleAddAdjustment} className="space-y-3 text-xs">
              <div>
                <label className="font-bold block mb-1">Adjustment Type</label>
                <select value={adjType} onChange={e => setAdjType(e.target.value)} className="ca-input w-full">
                  <option value="Income Tax Paid">Income Tax Paid</option>
                  <option value="Interest Paid">Interest Paid (Finance Cost)</option>
                  <option value="Interest Received">Interest Received</option>
                  <option value="Dividend Received">Dividend Received</option>
                  <option value="Profit on Sale of PPE">Profit on Sale of PPE</option>
                  <option value="Loss on Sale of PPE">Loss on Sale of PPE</option>
                  <option value="Proceeds from Sale of PPE">Proceeds from Sale of PPE</option>
                  <option value="Dividend Paid">Dividend Paid</option>
                </select>
              </div>
              <div>
                <label className="font-bold block mb-1">Description / Narration</label>
                <input type="text" value={adjDesc} onChange={e => setAdjDesc(e.target.value)}
                  placeholder="e.g. Advance tax challan payment, FD interest credited" className="ca-input w-full" required />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold block mb-1">CY Amount (Rs Lakhs)</label>
                  <input type="number" step="0.01" value={adjAmount}
                    onChange={e => setAdjAmount(parseFloat(e.target.value) || 0)}
                    className="ca-input w-full" required />
                </div>
                <div>
                  <label className="font-bold block mb-1">Category</label>
                  <select value={adjCategory} onChange={e => setAdjCategory(e.target.value)} className="ca-input w-full">
                    <option value="Operating">Operating Activities</option>
                    <option value="Investing">Investing Activities</option>
                    <option value="Financing">Financing Activities</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowAdjModal(false)} className="ca-button-secondary text-xs">Cancel</button>
                <button type="submit" className="ca-button-primary text-xs">Save Adjustment</button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
