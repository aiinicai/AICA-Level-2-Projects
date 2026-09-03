import React, { useState } from 'react';
import {
  FileText,
  DollarSign,
  TrendingUp,
  Download,
  Calendar,
  Layers,
  ArrowRight,
  Filter,
  CheckCircle2,
} from 'lucide-react';
import { FinancialModel, MonthlyFinancialRecord, ClientProfile } from '../../types';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';

interface FinancialStatementsViewProps {
  model: FinancialModel;
  onExportExcel: () => void;
  firmName?: string;
}

export const FinancialStatementsView: React.FC<FinancialStatementsViewProps> = ({
  model,
  onExportExcel,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const [statementType, setStatementType] = useState<'pnl' | 'balance_sheet' | 'cash_flow' | 'working_capital'>('pnl');
  const [viewMode, setViewMode] = useState<'monthly' | 'quarterly'>('monthly');

  const client = model.client;
  const records = model.historicalMonthly;

  const formatMoney = (val: number | undefined) => {
    if (val === undefined || isNaN(val)) return '-';
    return `${client.currencySymbol}${Number(val).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  };

  const formatPct = (val: number | undefined) => {
    if (val === undefined || isNaN(val)) return '-';
    return `${val.toFixed(1)}%`;
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="Comprehensive Financial Statements" firmName={firmName} />

      {/* Top Controls: Statement Type Tabs & Export */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <button
            onClick={() => setStatementType('pnl')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              statementType === 'pnl'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            Profit & Loss (P&L)
          </button>
          <button
            onClick={() => setStatementType('balance_sheet')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              statementType === 'balance_sheet'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            Balance Sheet
          </button>
          <button
            onClick={() => setStatementType('cash_flow')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              statementType === 'cash_flow'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            Cash Flow Statement
          </button>
          <button
            onClick={() => setStatementType('working_capital')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              statementType === 'working_capital'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            Working Capital & Liquidity
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onExportExcel}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-indigo-400" />
            Download Excel Spreadsheet
          </button>
        </div>
      </div>

      {/* Financial Statement Tables */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-900">
              {statementType === 'pnl' && 'Multi-Period Profit & Loss Statement'}
              {statementType === 'balance_sheet' && 'Balance Sheet Statement'}
              {statementType === 'cash_flow' && 'Statement of Cash Flows'}
              {statementType === 'working_capital' && 'Working Capital & Cash Conversion Cycle'}
            </h3>
          </div>
          <div className="text-xs text-slate-500 font-medium">
            All values in <span className="font-semibold text-slate-900">{client.currency}</span> ({client.currencySymbol})
          </div>
        </div>

        <div className="overflow-x-auto">
          {/* P&L Statement Table */}
          {statementType === 'pnl' && (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/80 text-slate-700 font-bold border-b border-slate-200">
                  <th className="py-3 px-4 min-w-[220px]">Line Item</th>
                  {records.map(r => (
                    <th key={r.periodKey} className="py-3 px-3 text-right min-w-[105px]">
                      {r.periodLabel}
                    </th>
                  ))}
                  <th className="py-3 px-4 text-right min-w-[120px] bg-slate-200/70 text-slate-900">YTD Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {/* Revenue */}
                <tr className="font-bold text-slate-900 bg-indigo-50/30">
                  <td className="py-2.5 px-4">Gross Revenue</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.revenue)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-indigo-50/60 font-black">{formatMoney(records.reduce((s, r) => s + r.revenue, 0))}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 text-slate-500 pl-8">Cost of Goods Sold (COGS)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right text-slate-500">{formatMoney(r.cogs)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 text-slate-600">{formatMoney(records.reduce((s, r) => s + r.cogs, 0))}</td>
                </tr>
                <tr className="font-bold text-emerald-900 bg-emerald-50/40">
                  <td className="py-2.5 px-4">Gross Profit</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.grossProfit)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-emerald-100/50 font-black">{formatMoney(records.reduce((s, r) => s + r.grossProfit, 0))}</td>
                </tr>
                <tr className="text-slate-500 italic bg-emerald-50/20">
                  <td className="py-1.5 px-4 pl-8">Gross Margin %</td>
                  {records.map(r => <td key={r.periodKey} className="py-1.5 px-3 text-right">{formatPct(r.grossMarginPercent)}</td>)}
                  <td className="py-1.5 px-4 text-right bg-emerald-50/40 font-bold">
                    {formatPct((records.reduce((s, r) => s + r.grossProfit, 0) / records.reduce((s, r) => s + r.revenue, 0)) * 100)}
                  </td>
                </tr>

                {/* OPEX */}
                <tr className="bg-slate-100/50 font-semibold text-slate-800">
                  <td colSpan={records.length + 2} className="py-2 px-4 uppercase text-[10px] tracking-wider text-slate-500">
                    Operating Expenses (OPEX)
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Salaries & Wages</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.salariesAndWages)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50">{formatMoney(records.reduce((s, r) => s + r.salariesAndWages, 0))}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Sales & Marketing</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.salesAndMarketing)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50">{formatMoney(records.reduce((s, r) => s + r.salesAndMarketing, 0))}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Rent & Facilities</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.rentAndFacilities)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50">{formatMoney(records.reduce((s, r) => s + r.rentAndFacilities, 0))}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">General & Administrative</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.generalAndAdmin)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50">{formatMoney(records.reduce((s, r) => s + r.generalAndAdmin, 0))}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Depreciation & Amortization</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.depreciationAndAmort)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50">{formatMoney(records.reduce((s, r) => s + r.depreciationAndAmort, 0))}</td>
                </tr>
                <tr className="font-bold text-slate-900 bg-slate-100/60">
                  <td className="py-2.5 px-4">Total Operating Expenses</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.totalOpex)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-slate-200 font-black">{formatMoney(records.reduce((s, r) => s + r.totalOpex, 0))}</td>
                </tr>

                {/* EBITDA & Net Income */}
                <tr className="font-bold text-violet-900 bg-violet-50/40">
                  <td className="py-2.5 px-4">EBITDA</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.ebitda)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-violet-100/60 font-black">{formatMoney(records.reduce((s, r) => s + r.ebitda, 0))}</td>
                </tr>
                <tr className="text-slate-500 italic bg-violet-50/20">
                  <td className="py-1.5 px-4 pl-8">EBITDA Margin %</td>
                  {records.map(r => <td key={r.periodKey} className="py-1.5 px-3 text-right">{formatPct(r.ebitdaMarginPercent)}</td>)}
                  <td className="py-1.5 px-4 text-right bg-violet-50/40 font-bold">
                    {formatPct((records.reduce((s, r) => s + r.ebitda, 0) / records.reduce((s, r) => s + r.revenue, 0)) * 100)}
                  </td>
                </tr>
                <tr className="font-bold text-slate-900 bg-slate-900 text-white">
                  <td className="py-3 px-4">Net Income</td>
                  {records.map(r => <td key={r.periodKey} className="py-3 px-3 text-right">{formatMoney(r.netIncome)}</td>)}
                  <td className="py-3 px-4 text-right bg-indigo-950 font-black">{formatMoney(records.reduce((s, r) => s + r.netIncome, 0))}</td>
                </tr>
              </tbody>
            </table>
          )}

          {/* Balance Sheet Table */}
          {statementType === 'balance_sheet' && (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/80 text-slate-700 font-bold border-b border-slate-200">
                  <th className="py-3 px-4 min-w-[220px]">Balance Sheet Account</th>
                  {records.map(r => (
                    <th key={r.periodKey} className="py-3 px-3 text-right min-w-[105px]">
                      {r.periodLabel}
                    </th>
                  ))}
                  <th className="py-3 px-4 text-right min-w-[120px] bg-slate-200/70 text-slate-900">Ending Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                <tr className="bg-slate-100/50 font-semibold text-slate-800">
                  <td colSpan={records.length + 2} className="py-2 px-4 uppercase text-[10px] tracking-wider text-slate-500">
                    Current Assets
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Cash & Cash Equivalents</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.cashAndEquivalents)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{formatMoney(records[records.length - 1].cashAndEquivalents)}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Accounts Receivable (AR)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.accountsReceivable)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{formatMoney(records[records.length - 1].accountsReceivable)}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Inventory</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.inventory)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{formatMoney(records[records.length - 1].inventory)}</td>
                </tr>
                <tr className="font-bold text-slate-900 bg-indigo-50/40">
                  <td className="py-2.5 px-4">Total Current Assets</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.totalCurrentAssets)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-indigo-100/60 font-black">{formatMoney(records[records.length - 1].totalCurrentAssets)}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4">Fixed Assets (PP&E)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.fixedAssets)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{formatMoney(records[records.length - 1].fixedAssets)}</td>
                </tr>
                <tr className="font-bold text-slate-900 bg-slate-200/60">
                  <td className="py-2.5 px-4">Total Assets</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.totalAssets)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-slate-300 font-black">{formatMoney(records[records.length - 1].totalAssets)}</td>
                </tr>

                <tr className="bg-slate-100/50 font-semibold text-slate-800">
                  <td colSpan={records.length + 2} className="py-2 px-4 uppercase text-[10px] tracking-wider text-slate-500">
                    Liabilities & Equity
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Accounts Payable (AP)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.accountsPayable)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{formatMoney(records[records.length - 1].accountsPayable)}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Short-Term Debt</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.shortTermDebt)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{formatMoney(records[records.length - 1].shortTermDebt)}</td>
                </tr>
                <tr className="font-bold text-slate-900 bg-amber-50/40">
                  <td className="py-2.5 px-4">Total Current Liabilities</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.totalCurrentLiabilities)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-amber-100/60 font-black">{formatMoney(records[records.length - 1].totalCurrentLiabilities)}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4">Long-Term Debt</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{formatMoney(r.longTermDebt)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{formatMoney(records[records.length - 1].longTermDebt)}</td>
                </tr>
                <tr className="font-bold text-slate-900 bg-slate-900 text-white">
                  <td className="py-3 px-4">Total Shareholders' Equity</td>
                  {records.map(r => <td key={r.periodKey} className="py-3 px-3 text-right">{formatMoney(r.totalEquity)}</td>)}
                  <td className="py-3 px-4 text-right bg-indigo-950 font-black">{formatMoney(records[records.length - 1].totalEquity)}</td>
                </tr>
              </tbody>
            </table>
          )}

          {/* Cash Flow Statement */}
          {statementType === 'cash_flow' && (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/80 text-slate-700 font-bold border-b border-slate-200">
                  <th className="py-3 px-4 min-w-[220px]">Cash Flow Activity</th>
                  {records.map(r => (
                    <th key={r.periodKey} className="py-3 px-3 text-right min-w-[105px]">
                      {r.periodLabel}
                    </th>
                  ))}
                  <th className="py-3 px-4 text-right min-w-[120px] bg-slate-200/70 text-slate-900">YTD Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                <tr className="font-bold text-emerald-900 bg-emerald-50/40">
                  <td className="py-2.5 px-4">Operating Cash Flow (OCF)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.operatingCashFlow)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-emerald-100/60 font-black">{formatMoney(records.reduce((s, r) => s + r.operatingCashFlow, 0))}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Investing Cash Flow (CapEx)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right text-rose-600">{formatMoney(r.investingCashFlow)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 text-rose-700 font-bold">{formatMoney(records.reduce((s, r) => s + r.investingCashFlow, 0))}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Financing Cash Flow (Debt/Draws)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right text-rose-600">{formatMoney(r.financingCashFlow)}</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 text-rose-700 font-bold">{formatMoney(records.reduce((s, r) => s + r.financingCashFlow, 0))}</td>
                </tr>
                <tr className="font-bold text-indigo-900 bg-indigo-50/60">
                  <td className="py-2.5 px-4">Net Cash Generation</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.netCashFlow)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-indigo-100 font-black">{formatMoney(records.reduce((s, r) => s + r.netCashFlow, 0))}</td>
                </tr>
                <tr className="font-bold text-slate-900 bg-slate-900 text-white">
                  <td className="py-3 px-4">Ending Cash Balance</td>
                  {records.map(r => <td key={r.periodKey} className="py-3 px-3 text-right">{formatMoney(r.endingCash)}</td>)}
                  <td className="py-3 px-4 text-right bg-indigo-950 font-black">{formatMoney(records[records.length - 1].endingCash)}</td>
                </tr>
              </tbody>
            </table>
          )}

          {/* Working Capital Statement */}
          {statementType === 'working_capital' && (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/80 text-slate-700 font-bold border-b border-slate-200">
                  <th className="py-3 px-4 min-w-[220px]">Working Capital Metric</th>
                  {records.map(r => (
                    <th key={r.periodKey} className="py-3 px-3 text-right min-w-[105px]">
                      {r.periodLabel}
                    </th>
                  ))}
                  <th className="py-3 px-4 text-right min-w-[120px] bg-slate-200/70 text-slate-900">Current Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                <tr className="font-bold text-indigo-900 bg-indigo-50/40">
                  <td className="py-2.5 px-4">Net Working Capital ($)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{formatMoney(r.workingCapital)}</td>)}
                  <td className="py-2.5 px-4 text-right bg-indigo-100 font-black">{formatMoney(records[records.length - 1].workingCapital)}</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Current Ratio (CA / CL)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{r.currentRatio.toFixed(2)}x</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{records[records.length - 1].currentRatio.toFixed(2)}x</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Quick Ratio (Acid Test)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{r.quickRatio.toFixed(2)}x</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{records[records.length - 1].quickRatio.toFixed(2)}x</td>
                </tr>
                <tr className="bg-slate-100/50 font-semibold text-slate-800">
                  <td colSpan={records.length + 2} className="py-2 px-4 uppercase text-[10px] tracking-wider text-slate-500">
                    Cash Conversion Cycle (CCC Days)
                  </td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Days Sales Outstanding (DSO)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{r.dso} days</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{records[records.length - 1].dso} days</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Days Inventory Outstanding (DIO)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{r.dio} days</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{records[records.length - 1].dio} days</td>
                </tr>
                <tr>
                  <td className="py-2 px-4 pl-8">Days Payable Outstanding (DPO)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2 px-3 text-right">{r.dpo} days</td>)}
                  <td className="py-2 px-4 text-right bg-slate-50 font-bold">{records[records.length - 1].dpo} days</td>
                </tr>
                <tr className="font-bold text-slate-900 bg-slate-200/80">
                  <td className="py-2.5 px-4">Cash Conversion Cycle (DSO + DIO - DPO)</td>
                  {records.map(r => <td key={r.periodKey} className="py-2.5 px-3 text-right">{r.ccc} days</td>)}
                  <td className="py-2.5 px-4 text-right bg-slate-300 font-black">{records[records.length - 1].ccc} days</td>
                </tr>
              </tbody>
            </table>
          )}
        </div>
      </div>

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
