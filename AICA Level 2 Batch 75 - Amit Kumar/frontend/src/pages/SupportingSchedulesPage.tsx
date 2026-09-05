import React, { useEffect, useState } from 'react';
import type { Client, SupportingSchedules } from '../types';
import { fetchSchedules } from '../services/api';
import { RefreshCw } from 'lucide-react';

interface SupportingSchedulesProps {
  client: Client;
}

const amtCls = (v: number) =>
  v > 0 ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400';

const fmt = (v?: number) =>
  typeof v === 'number' ? v.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '–';

export const SupportingSchedulesPage: React.FC<SupportingSchedulesProps> = ({ client }) => {
  const [activeTab, setActiveTab] = useState<'ar' | 'ap' | 'cwip' | 'rpt' | 'borrowings' | 'contingencies'>('ar');
  const [schedules, setSchedules] = useState<SupportingSchedules | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSchedules(client.id);
      setSchedules(data);
    } catch (e) {
      console.error(e);
      setError('Failed to load schedules. Please check the backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (client) loadData();
  }, [client.id]);

  const tabs = [
    { id: 'ar',            label: '1. AR Ageing',       count: schedules?.ar.length || 0 },
    { id: 'ap',            label: '2. AP Ageing',       count: schedules?.ap.length || 0 },
    { id: 'cwip',          label: '3. CWIP Ageing',     count: schedules?.cwip.length || 0 },
    { id: 'rpt',           label: '4. Related Parties', count: schedules?.rpt.length || 0 },
    { id: 'borrowings',    label: '5. Borrowings',      count: schedules?.borrowings.length || 0 },
    { id: 'contingencies', label: '6. Contingencies',   count: schedules?.contingencies.length || 0 },
  ] as const;

  return (
    <div className="space-y-5 max-w-full">

      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-tight">
            Supporting Audit Schedules
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-semibold">
            {client.name} | {client.reporting_period} — Parsed schedule data for all 6 ageing and disclosure modules
          </p>
        </div>
        <button onClick={loadData} className="ca-button-secondary text-xs flex items-center gap-1.5">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-slate-200 dark:border-slate-800 pb-2">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as any)}
            className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${
              activeTab === t.id
                ? 'bg-[#1B365D] text-white'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            {t.label} <span className="text-[10px] ml-1 opacity-70">({t.count})</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12 gap-2 text-slate-500 text-xs font-semibold">
          <RefreshCw className="w-4 h-4 animate-spin" /> Loading schedule records…
        </div>
      ) : error ? (
        <div className="p-6 text-xs text-rose-700 font-bold bg-rose-50 border border-rose-200 rounded-lg">{error}</div>
      ) : (
        <div className="studio-card overflow-x-auto">

          {/* ── 1. AR AGEING ─────────────────────────────────────── */}
          {activeTab === 'ar' && (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-[#1B365D] text-white text-[11px] font-black">
                  <th className="p-2.5 text-left">Customer Name</th>
                  <th className="p-2.5 text-right">Total Outstanding</th>
                  <th className="p-2.5 text-right">Not Due / &lt;6M</th>
                  <th className="p-2.5 text-right">6M – 1Y</th>
                  <th className="p-2.5 text-right">1Y – 2Y</th>
                  <th className="p-2.5 text-right">2Y – 3Y</th>
                  <th className="p-2.5 text-right">&gt;3 Years</th>
                  <th className="p-2.5 text-right">PY Total</th>
                  <th className="p-2.5 text-center">Category</th>
                  <th className="p-2.5 text-center">Disputed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {(schedules?.ar || []).map((row: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 font-medium">
                    <td className="p-2.5 font-bold text-[#1B365D] dark:text-blue-300">{row.customer_name}</td>
                    <td className={`p-2.5 text-right font-mono font-bold ${amtCls(row.total)}`}>{fmt(row.total)}</td>
                    <td className="p-2.5 text-right font-mono">{fmt(row.l6m)}</td>
                    <td className="p-2.5 text-right font-mono">{fmt(row.m6_1y)}</td>
                    <td className="p-2.5 text-right font-mono">{fmt(row.y1_2y)}</td>
                    <td className={`p-2.5 text-right font-mono ${row.y2_3y > 0 ? 'text-amber-600 font-bold' : ''}`}>{fmt(row.y2_3y)}</td>
                    <td className={`p-2.5 text-right font-mono ${row.mor_3y > 0 ? 'text-rose-600 font-bold' : ''}`}>{fmt(row.mor_3y)}</td>
                    <td className="p-2.5 text-right font-mono text-slate-500">{fmt(row.py_total)}</td>
                    <td className="p-2.5 text-center">
                      <span className="bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded">
                        {row.category}
                      </span>
                    </td>
                    <td className="p-2.5 text-center">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        row.disputed === 'Yes'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-slate-100 text-slate-600'
                      }`}>{row.disputed}</span>
                    </td>
                  </tr>
                ))}
                {/* Total row */}
                <tr className="bg-[#1B365D]/10 dark:bg-slate-700 font-black text-[#1B365D] dark:text-white border-t-2 border-slate-400">
                  <td className="p-2.5">TOTAL</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ar.reduce((s: number, r: any) => s + (r.total || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ar.reduce((s: number, r: any) => s + (r.l6m || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ar.reduce((s: number, r: any) => s + (r.m6_1y || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ar.reduce((s: number, r: any) => s + (r.y1_2y || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ar.reduce((s: number, r: any) => s + (r.y2_3y || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ar.reduce((s: number, r: any) => s + (r.mor_3y || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ar.reduce((s: number, r: any) => s + (r.py_total || 0), 0))}</td>
                  <td colSpan={2} />
                </tr>
              </tbody>
            </table>
          )}

          {/* ── 2. AP AGEING ─────────────────────────────────────── */}
          {activeTab === 'ap' && (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-[#1B365D] text-white text-[11px] font-black">
                  <th className="p-2.5 text-left">Vendor Name</th>
                  <th className="p-2.5 text-center">MSME</th>
                  <th className="p-2.5 text-right">Total Outstanding</th>
                  <th className="p-2.5 text-right">&lt;1 Year</th>
                  <th className="p-2.5 text-right">1Y – 2Y</th>
                  <th className="p-2.5 text-right">2Y – 3Y</th>
                  <th className="p-2.5 text-right">&gt;3 Years</th>
                  <th className="p-2.5 text-right">PY Total</th>
                  <th className="p-2.5 text-center">Category</th>
                  <th className="p-2.5 text-center">Disputed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {(schedules?.ap || []).map((row: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 font-medium">
                    <td className="p-2.5 font-bold text-[#1B365D] dark:text-blue-300">{row.vendor_name}</td>
                    <td className="p-2.5 text-center">
                      {row.msme === 'Yes'
                        ? <span className="bg-orange-100 text-orange-800 font-black text-[10px] px-2 py-0.5 rounded">MSME</span>
                        : <span className="text-slate-400 text-[10px]">No</span>}
                    </td>
                    <td className={`p-2.5 text-right font-mono font-bold ${amtCls(row.outstanding_amount)}`}>{fmt(row.outstanding_amount)}</td>
                    <td className="p-2.5 text-right font-mono">{fmt(row.l1y)}</td>
                    <td className="p-2.5 text-right font-mono">{fmt(row.y1_2y)}</td>
                    <td className={`p-2.5 text-right font-mono ${row.y2_3y > 0 ? 'text-amber-600 font-bold' : ''}`}>{fmt(row.y2_3y)}</td>
                    <td className={`p-2.5 text-right font-mono ${row.mor_3y > 0 ? 'text-rose-600 font-bold' : ''}`}>{fmt(row.mor_3y)}</td>
                    <td className="p-2.5 text-right font-mono text-slate-500">{fmt(row.py_outstanding_amount)}</td>
                    <td className="p-2.5 text-center">
                      <span className="bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-[10px] font-bold px-2 py-0.5 rounded">
                        {row.category}
                      </span>
                    </td>
                    <td className="p-2.5 text-center">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        row.disputed === 'Yes' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-600'
                      }`}>{row.disputed}</span>
                    </td>
                  </tr>
                ))}
                <tr className="bg-[#1B365D]/10 dark:bg-slate-700 font-black text-[#1B365D] dark:text-white border-t-2 border-slate-400">
                  <td className="p-2.5" colSpan={2}>TOTAL</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ap.reduce((s: number, r: any) => s + (r.outstanding_amount || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ap.reduce((s: number, r: any) => s + (r.l1y || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ap.reduce((s: number, r: any) => s + (r.y1_2y || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ap.reduce((s: number, r: any) => s + (r.y2_3y || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ap.reduce((s: number, r: any) => s + (r.mor_3y || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.ap.reduce((s: number, r: any) => s + (r.py_outstanding_amount || 0), 0))}</td>
                  <td colSpan={2} />
                </tr>
              </tbody>
            </table>
          )}

          {/* ── 3. CWIP AGEING ───────────────────────────────────── */}
          {activeTab === 'cwip' && (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-[#1B365D] text-white text-[11px] font-black">
                  <th className="p-2.5 text-left">Project Name</th>
                  <th className="p-2.5 text-right">Closing CWIP</th>
                  <th className="p-2.5 text-right">&lt;1 Year</th>
                  <th className="p-2.5 text-right">1Y – 2Y</th>
                  <th className="p-2.5 text-right">2Y – 3Y</th>
                  <th className="p-2.5 text-right">&gt;3 Years</th>
                  <th className="p-2.5 text-right">PY CWIP</th>
                  <th className="p-2.5 text-center">Status</th>
                  <th className="p-2.5 text-left">Reason / Remarks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {(schedules?.cwip || []).map((row: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 font-medium">
                    <td className="p-2.5 font-bold text-[#1B365D] dark:text-blue-300">{row.project_name}</td>
                    <td className="p-2.5 text-right font-mono font-bold">{fmt(row.closing_cwip)}</td>
                    <td className="p-2.5 text-right font-mono">{fmt(row.l1y)}</td>
                    <td className="p-2.5 text-right font-mono">{fmt(row.y1_2y)}</td>
                    <td className={`p-2.5 text-right font-mono ${row.y2_3y > 0 ? 'text-amber-600 font-bold' : ''}`}>{fmt(row.y2_3y)}</td>
                    <td className={`p-2.5 text-right font-mono ${row.mor_3y > 0 ? 'text-rose-600 font-bold' : ''}`}>{fmt(row.mor_3y)}</td>
                    <td className="p-2.5 text-right font-mono text-slate-500">{fmt(row.py_closing_cwip)}</td>
                    <td className="p-2.5 text-center">
                      <span className="bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 text-[10px] font-bold px-2 py-0.5 rounded">{row.status}</span>
                    </td>
                    <td className="p-2.5 text-slate-600 dark:text-slate-400 text-[11px]">{row.reason_delay || '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* ── 4. RELATED PARTIES ───────────────────────────────── */}
          {activeTab === 'rpt' && (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-[#1B365D] text-white text-[11px] font-black">
                  <th className="p-2.5 text-left">Related Party Name</th>
                  <th className="p-2.5 text-left">Relationship</th>
                  <th className="p-2.5 text-left">Nature of Transaction</th>
                  <th className="p-2.5 text-right">Opening Bal</th>
                  <th className="p-2.5 text-right">Debit Tx</th>
                  <th className="p-2.5 text-right">Credit Tx</th>
                  <th className="p-2.5 text-right">Closing Bal</th>
                  <th className="p-2.5 text-right">PY Closing</th>
                  <th className="p-2.5 text-center">Category</th>
                  <th className="p-2.5 text-left">Terms</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {(schedules?.rpt || []).map((row: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 font-medium">
                    <td className="p-2.5 font-bold text-[#1B365D] dark:text-blue-300">{row.name}</td>
                    <td className="p-2.5 text-slate-700 dark:text-slate-300">{row.relationship}</td>
                    <td className="p-2.5 text-slate-700 dark:text-slate-300">{row.nature_tx}</td>
                    <td className="p-2.5 text-right font-mono">{fmt(row.opening_bal)}</td>
                    <td className="p-2.5 text-right font-mono text-sky-700 dark:text-sky-400">{fmt(row.debit_tx)}</td>
                    <td className="p-2.5 text-right font-mono text-emerald-700 dark:text-emerald-400">{fmt(row.credit_tx)}</td>
                    <td className="p-2.5 text-right font-mono font-bold">{fmt(row.closing_bal)}</td>
                    <td className="p-2.5 text-right font-mono text-slate-500">{fmt(row.py_closing_bal)}</td>
                    <td className="p-2.5 text-center">
                      <span className="bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-[10px] font-bold px-2 py-0.5 rounded">{row.category}</span>
                    </td>
                    <td className="p-2.5 text-slate-600 dark:text-slate-400 text-[11px]">{row.terms || '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* ── 5. BORROWINGS ────────────────────────────────────── */}
          {activeTab === 'borrowings' && (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-[#1B365D] text-white text-[11px] font-black">
                  <th className="p-2.5 text-left">Lender Name</th>
                  <th className="p-2.5 text-left">Loan Type</th>
                  <th className="p-2.5 text-center">Secured / Unsecured</th>
                  <th className="p-2.5 text-center">Current / NC</th>
                  <th className="p-2.5 text-right">Opening Bal</th>
                  <th className="p-2.5 text-right">Additions</th>
                  <th className="p-2.5 text-right">Repayments</th>
                  <th className="p-2.5 text-right">Closing Bal</th>
                  <th className="p-2.5 text-right">PY Closing</th>
                  <th className="p-2.5 text-center">Rate</th>
                  <th className="p-2.5 text-left">Security</th>
                  <th className="p-2.5 text-center">Default</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {(schedules?.borrowings || []).map((row: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 font-medium">
                    <td className="p-2.5 font-bold text-[#1B365D] dark:text-blue-300">{row.lender_name}</td>
                    <td className="p-2.5">{row.loan_type}</td>
                    <td className="p-2.5 text-center">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        row.secured_unsecured === 'Secured'
                          ? 'bg-orange-100 text-orange-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}>{row.secured_unsecured}</span>
                    </td>
                    <td className="p-2.5 text-center">
                      <span className="bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-[10px] font-bold px-2 py-0.5 rounded">
                        {row.current_non_current}
                      </span>
                    </td>
                    <td className="p-2.5 text-right font-mono">{fmt(row.opening_bal)}</td>
                    <td className="p-2.5 text-right font-mono text-emerald-700 dark:text-emerald-400">{fmt(row.additions)}</td>
                    <td className="p-2.5 text-right font-mono text-rose-600 dark:text-rose-400">{fmt(row.repayments)}</td>
                    <td className="p-2.5 text-right font-mono font-bold">{fmt(row.closing_bal)}</td>
                    <td className="p-2.5 text-right font-mono text-slate-500">{fmt(row.py_closing_bal)}</td>
                    <td className="p-2.5 text-center font-mono text-[11px]">{row.interest_rate || '–'}</td>
                    <td className="p-2.5 text-slate-600 dark:text-slate-400 text-[11px] max-w-[200px] truncate" title={row.security_details}>{row.security_details || '–'}</td>
                    <td className="p-2.5 text-center">
                      {row.is_default === 'Yes'
                        ? <span className="bg-rose-100 text-rose-800 font-black text-[10px] px-2 py-0.5 rounded">DEFAULT: {row.default_amount}</span>
                        : <span className="bg-emerald-100 text-emerald-800 text-[10px] px-2 py-0.5 rounded">None</span>}
                    </td>
                  </tr>
                ))}
                <tr className="bg-[#1B365D]/10 dark:bg-slate-700 font-black text-[#1B365D] dark:text-white border-t-2 border-slate-400">
                  <td className="p-2.5" colSpan={4}>TOTAL</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.borrowings.reduce((s: number, r: any) => s + (r.opening_bal || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.borrowings.reduce((s: number, r: any) => s + (r.additions || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.borrowings.reduce((s: number, r: any) => s + (r.repayments || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.borrowings.reduce((s: number, r: any) => s + (r.closing_bal || 0), 0))}</td>
                  <td className="p-2.5 text-right font-mono">{fmt(schedules?.borrowings.reduce((s: number, r: any) => s + (r.py_closing_bal || 0), 0))}</td>
                  <td colSpan={3} />
                </tr>
              </tbody>
            </table>
          )}

          {/* ── 6. CONTINGENCIES ─────────────────────────────────── */}
          {activeTab === 'contingencies' && (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-[#1B365D] text-white text-[11px] font-black">
                  <th className="p-2.5 text-left">Nature of Contingency / Commitment</th>
                  <th className="p-2.5 text-left">Forum / Authority</th>
                  <th className="p-2.5 text-right">CY Amount (Rs Lakhs)</th>
                  <th className="p-2.5 text-right">PY Amount (Rs Lakhs)</th>
                  <th className="p-2.5 text-left">Management Assessment</th>
                  <th className="p-2.5 text-center">Provision Required</th>
                  <th className="p-2.5 text-left">Remarks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {(schedules?.contingencies || []).map((row: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 font-medium">
                    <td className="p-2.5 font-bold text-[#1B365D] dark:text-blue-300">{row.nature}</td>
                    <td className="p-2.5 font-semibold text-slate-700 dark:text-slate-300">{row.forum || '–'}</td>
                    <td className="p-2.5 text-right font-mono font-bold">{fmt(row.cy_amount)}</td>
                    <td className="p-2.5 text-right font-mono text-slate-500">{fmt(row.py_amount)}</td>
                    <td className="p-2.5 text-slate-600 dark:text-slate-400 text-[11px] max-w-[220px]">{row.assessment || '–'}</td>
                    <td className="p-2.5 text-center">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        row.provision_required === 'Yes'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
                      }`}>{row.provision_required}</span>
                    </td>
                    <td className="p-2.5 text-slate-500 text-[11px]">{row.remarks || '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Empty state */}
          {(
            (activeTab === 'ar' && schedules?.ar.length === 0) ||
            (activeTab === 'ap' && schedules?.ap.length === 0) ||
            (activeTab === 'cwip' && schedules?.cwip.length === 0) ||
            (activeTab === 'rpt' && schedules?.rpt.length === 0) ||
            (activeTab === 'borrowings' && schedules?.borrowings.length === 0) ||
            (activeTab === 'contingencies' && schedules?.contingencies.length === 0)
          ) && (
            <div className="p-12 text-center text-xs text-slate-500 font-semibold">
              No records found for this schedule. Upload the corresponding file from the Upload Centre or load sample data.
            </div>
          )}

        </div>
      )}
    </div>
  );
};
