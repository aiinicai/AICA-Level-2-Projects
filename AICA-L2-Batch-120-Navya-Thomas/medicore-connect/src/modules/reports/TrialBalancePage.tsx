import React, { useState, useMemo } from 'react';
import Decimal from 'decimal.js';
import {
  FileSpreadsheet,
  Download,
  Printer,
  FileText,
  Filter,
  CheckCircle2,
  AlertCircle,
  BarChart3,
} from 'lucide-react';
import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { getDb } from '../../core/storage';
import { CHART_OF_ACCOUNTS } from '../../data/chartOfAccounts';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { formatAED, round2 } from '../../core/currency';

interface TrialBalancePageProps {
  onNavigate: (route: string) => void;
}

export const TrialBalancePage: React.FC<TrialBalancePageProps> = ({ onNavigate }) => {
  const db = getDb();
  const [selectedBU, setSelectedBU] = useState<string>('All');
  const [period, setPeriod] = useState<string>('All');
  const [includeZeroBalances, setIncludeZeroBalances] = useState(false);

  // Compute TB lines: Opening Dr/Cr, Period Movement Dr/Cr, Closing Dr/Cr
  const tbRows = useMemo(() => {
    const acctMap: Record<
      string,
      {
        openDr: Decimal;
        openCr: Decimal;
        moveDr: Decimal;
        moveCr: Decimal;
      }
    > = {};

    CHART_OF_ACCOUNTS.forEach((a) => {
      acctMap[a.code] = {
        openDr: new Decimal(0),
        openCr: new Decimal(0),
        moveDr: new Decimal(0),
        moveCr: new Decimal(0),
      };
    });

    db.glJournals.forEach((j) => {
      if (j.status !== 'Posted') return;

      const isOpening = j.sourceModule === 'Opening Balances';
      const matchesPeriod = period === 'All' || j.period === period;

      j.lines.forEach((l) => {
        if (selectedBU !== 'All' && l.businessUnit !== selectedBU) return;

        if (acctMap[l.account]) {
          const d = new Decimal(l.debit || 0);
          const c = new Decimal(l.credit || 0);

          if (isOpening) {
            acctMap[l.account].openDr = acctMap[l.account].openDr.plus(d);
            acctMap[l.account].openCr = acctMap[l.account].openCr.plus(c);
          } else if (matchesPeriod) {
            acctMap[l.account].moveDr = acctMap[l.account].moveDr.plus(d);
            acctMap[l.account].moveCr = acctMap[l.account].moveCr.plus(c);
          }
        }
      });
    });

    let totalOpenDr = new Decimal(0);
    let totalOpenCr = new Decimal(0);
    let totalMoveDr = new Decimal(0);
    let totalMoveCr = new Decimal(0);
    let totalCloseDr = new Decimal(0);
    let totalCloseCr = new Decimal(0);

    const rows = CHART_OF_ACCOUNTS.map((acct) => {
      const stats = acctMap[acct.code];
      const isNormalDebit = acct.normalBalance === 'Debit';

      // Net opening
      const netOpen = stats.openDr.minus(stats.openCr);
      let openDr = new Decimal(0);
      let openCr = new Decimal(0);
      if (netOpen.greaterThan(0)) openDr = netOpen;
      else if (netOpen.lessThan(0)) openCr = netOpen.abs();

      // Movements
      const moveDr = stats.moveDr;
      const moveCr = stats.moveCr;

      // Net closing = (openDr + moveDr) - (openCr + moveCr)
      const totalNet = openDr.plus(moveDr).minus(openCr.plus(moveCr));
      let closeDr = new Decimal(0);
      let closeCr = new Decimal(0);

      if (totalNet.greaterThan(0)) closeDr = totalNet;
      else if (totalNet.lessThan(0)) closeCr = totalNet.abs();

      totalOpenDr = totalOpenDr.plus(openDr);
      totalOpenCr = totalOpenCr.plus(openCr);
      totalMoveDr = totalMoveDr.plus(moveDr);
      totalMoveCr = totalMoveCr.plus(moveCr);
      totalCloseDr = totalCloseDr.plus(closeDr);
      totalCloseCr = totalCloseCr.plus(closeCr);

      return {
        code: acct.code,
        name: acct.name,
        type: acct.type,
        ifrsLine: acct.ifrsLine,
        openDr: openDr.toNumber(),
        openCr: openCr.toNumber(),
        moveDr: moveDr.toNumber(),
        moveCr: moveCr.toNumber(),
        closeDr: closeDr.toNumber(),
        closeCr: closeCr.toNumber(),
        isZero: totalNet.isZero() && moveDr.isZero() && moveCr.isZero(),
      };
    });

    const filteredRows = rows.filter((r) => includeZeroBalances || !r.isZero);

    return {
      rows: filteredRows,
      totals: {
        openDr: totalOpenDr.toNumber(),
        openCr: totalOpenCr.toNumber(),
        moveDr: totalMoveDr.toNumber(),
        moveCr: totalMoveCr.toNumber(),
        closeDr: totalCloseDr.toNumber(),
        closeCr: totalCloseCr.toNumber(),
        isBalanced: totalCloseDr.minus(totalCloseCr).abs().lessThanOrEqualTo(0.005),
        diff: totalCloseDr.minus(totalCloseCr).abs().toNumber(),
      },
    };
  }, [db.glJournals, selectedBU, period, includeZeroBalances]);

  // Excel Export
  const handleExportExcel = () => {
    const exportData = tbRows.rows.map((r) => ({
      'Account Code': r.code,
      'Account Name': r.name,
      'Type': r.type,
      'Opening Debit': r.openDr,
      'Opening Credit': r.openCr,
      'Movement Debit': r.moveDr,
      'Movement Credit': r.moveCr,
      'Closing Debit': r.closeDr,
      'Closing Credit': r.closeCr,
    }));

    exportData.push({
      'Account Code': 'TOTAL',
      'Account Name': 'GRAND TOTAL',
      'Type': '' as any,
      'Opening Debit': tbRows.totals.openDr,
      'Opening Credit': tbRows.totals.openCr,
      'Movement Debit': tbRows.totals.moveDr,
      'Movement Credit': tbRows.totals.moveCr,
      'Closing Debit': tbRows.totals.closeDr,
      'Closing Credit': tbRows.totals.closeCr,
    });

    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Trial Balance');
    XLSX.writeFile(wb, `Trial_Balance_${selectedBU}_${period}.xlsx`);
  };

  // CSV Export
  const handleExportCSV = () => {
    const exportData = tbRows.rows.map((r) => ({
      'Account Code': r.code,
      'Account Name': r.name,
      'Type': r.type,
      'Opening Debit': r.openDr,
      'Opening Credit': r.openCr,
      'Movement Debit': r.moveDr,
      'Movement Credit': r.moveCr,
      'Closing Debit': r.closeDr,
      'Closing Credit': r.closeCr,
    }));
    const ws = XLSX.utils.json_to_sheet(exportData);
    const csv = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `Trial_Balance_${selectedBU}_${period}.csv`;
    link.click();
  };

  // PDF Export
  const handleExportPDF = () => {
    const doc = new jsPDF({ orientation: 'landscape' });
    doc.setFontSize(14);
    doc.setTextColor(91, 44, 131);
    doc.text('Meridian Healthcare Group — General Ledger Trial Balance', 14, 14);
    doc.setFontSize(9);
    doc.setTextColor(100);
    doc.text(
      `Entity: ${selectedBU === 'All' ? 'All Units Consolidated' : selectedBU} | Period: ${period} | As of: 19/Oct/2026 | Currency: AED`,
      14,
      20
    );

    const headers = [
      ['Account', 'Description', 'Type', 'Open Dr', 'Open Cr', 'Movement Dr', 'Movement Cr', 'Close Dr', 'Close Cr'],
    ];
    const data = tbRows.rows.map((r) => [
      r.code,
      r.name,
      r.type,
      formatAED(r.openDr, { zeroAsDash: true }),
      formatAED(r.openCr, { zeroAsDash: true }),
      formatAED(r.moveDr, { zeroAsDash: true }),
      formatAED(r.moveCr, { zeroAsDash: true }),
      formatAED(r.closeDr, { zeroAsDash: true }),
      formatAED(r.closeCr, { zeroAsDash: true }),
    ]);

    data.push([
      'TOTAL',
      'GRAND TOTAL',
      '',
      formatAED(tbRows.totals.openDr),
      formatAED(tbRows.totals.openCr),
      formatAED(tbRows.totals.moveDr),
      formatAED(tbRows.totals.moveCr),
      formatAED(tbRows.totals.closeDr),
      formatAED(tbRows.totals.closeCr),
    ]);

    autoTable(doc, {
      head: headers,
      body: data,
      startY: 24,
      styles: { fontSize: 7, cellPadding: 2 },
      headStyles: { fillColor: [91, 44, 131], textColor: [255, 255, 255] },
      alternateRowStyles: { fillColor: [248, 245, 250] },
    });

    doc.save(`Trial_Balance_${selectedBU}_${period}.pdf`);
  };

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <BarChart3 className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">General Ledger Trial Balance</h1>
            <p className="text-xs text-gray-500">
              Double-entry audit schedule: Opening balances, period movements, and closing positions in AED.
            </p>
          </div>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleExportExcel}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-xs font-semibold text-emerald-800 flex items-center space-x-1.5 shadow-xs"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Excel (.xlsx)</span>
          </button>
          <button
            onClick={handleExportPDF}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-xs font-semibold text-rose-700 flex items-center space-x-1.5 shadow-xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>PDF Document</span>
          </button>
          <button
            onClick={handleExportCSV}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-xs font-semibold text-gray-700 flex items-center space-x-1.5 shadow-xs"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>
          <button
            onClick={() => window.print()}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-xs font-semibold text-gray-700 flex items-center space-x-1.5 shadow-xs"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print</span>
          </button>
        </div>
      </div>

      {/* Filter Parameters Strip */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-5 shadow-xs flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block font-semibold text-gray-600 mb-1">Entity / Business Unit</label>
            <select
              value={selectedBU}
              onChange={(e) => setSelectedBU(e.target.value)}
              className="bg-gray-50 border border-gray-300 rounded px-3 py-1 font-semibold text-gray-800 focus:ring-1 focus:ring-[#5B2C83]"
            >
              <option value="All">All 15 Units (Consolidated Group)</option>
              <option value="Hospitals">All Hospitals (H01-H05)</option>
              <option value="Clinics">All Clinics (C01-C05)</option>
              <option value="Pharmacies">All Pharmacies (P01-P05)</option>
              {BUSINESS_UNITS.map((bu) => (
                <option key={bu.code} value={bu.code}>
                  {bu.code} - {bu.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-gray-600 mb-1">Fiscal Period</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="bg-gray-50 border border-gray-300 rounded px-3 py-1 font-semibold text-gray-800 focus:ring-1 focus:ring-[#5B2C83]"
            >
              <option value="All">Full Year 2026 (YTD)</option>
              <option value="Oct-26">Oct-26 (Current Open)</option>
              <option value="Sep-26">Sep-26</option>
              <option value="Aug-26">Aug-26</option>
              <option value="Jul-26">Jul-26</option>
              <option value="Jun-26">Jun-26</option>
            </select>
          </div>

          <div className="self-end pb-1.5">
            <label className="flex items-center space-x-1.5 cursor-pointer text-gray-700">
              <input
                type="checkbox"
                checked={includeZeroBalances}
                onChange={(e) => setIncludeZeroBalances(e.target.checked)}
                className="rounded text-[#5B2C83] focus:ring-[#5B2C83]"
              />
              <span>Include Zero Balances</span>
            </label>
          </div>
        </div>

        {/* Balance Status Banner */}
        <div className="flex items-center space-x-2">
          {tbRows.totals.isBalanced ? (
            <div className="flex items-center px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 mr-1 text-emerald-600" />
              <span>Trial Balance In Perfect Balance: Dr = Cr</span>
            </div>
          ) : (
            <div className="flex items-center px-3 py-1.5 rounded-lg bg-rose-50 border border-rose-300 text-rose-800 text-xs font-semibold">
              <AlertCircle className="w-4 h-4 mr-1 text-rose-600" />
              <span>OUT OF BALANCE BY AED {formatAED(tbRows.totals.diff)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Trial Balance Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider border-b border-plum-200">
              <tr>
                <th rowSpan={2} className="py-2.5 px-3 w-16 border-r border-plum-200">
                  Account
                </th>
                <th rowSpan={2} className="py-2.5 px-3 border-r border-plum-200">
                  Description
                </th>
                <th rowSpan={2} className="py-2.5 px-3 w-20 border-r border-plum-200">
                  Type
                </th>
                <th colSpan={2} className="py-1.5 px-3 text-center border-r border-plum-200 bg-plum-100/60">
                  Opening Balance (AED)
                </th>
                <th colSpan={2} className="py-1.5 px-3 text-center border-r border-plum-200 bg-plum-100/40">
                  Period Movement (AED)
                </th>
                <th colSpan={2} className="py-1.5 px-3 text-center bg-plum-100/80">
                  Closing Balance (AED)
                </th>
              </tr>
              <tr className="border-t border-plum-200 text-[10px]">
                <th className="py-1 px-2 text-right w-24">Debit</th>
                <th className="py-1 px-2 text-right w-24 border-r border-plum-200">Credit</th>
                <th className="py-1 px-2 text-right w-28">Debit</th>
                <th className="py-1 px-2 text-right w-28 border-r border-plum-200">Credit</th>
                <th className="py-1 px-2 text-right w-28">Debit</th>
                <th className="py-1 px-2 text-right w-28">Credit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {tbRows.rows.map((row, idx) => (
                <tr
                  key={row.code}
                  className={`hover:bg-plum-50/30 transition-colors ${
                    idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'
                  }`}
                >
                  <td className="py-2 px-3 font-mono font-bold text-[#5B2C83] border-r border-gray-100">
                    {row.code}
                  </td>
                  <td className="py-2 px-3 font-medium text-gray-900 border-r border-gray-100">
                    {row.name}
                  </td>
                  <td className="py-2 px-3 text-gray-500 border-r border-gray-100">{row.type}</td>
                  <td className="py-2 px-2 text-right font-mono text-gray-800">
                    {formatAED(row.openDr, { zeroAsDash: true })}
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-gray-800 border-r border-gray-100">
                    {formatAED(row.openCr, { zeroAsDash: true })}
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-gray-800">
                    {formatAED(row.moveDr, { zeroAsDash: true })}
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-gray-800 border-r border-gray-100">
                    {formatAED(row.moveCr, { zeroAsDash: true })}
                  </td>
                  <td className="py-2 px-2 text-right font-mono font-bold text-[#3F1D5C]">
                    {formatAED(row.closeDr, { zeroAsDash: true })}
                  </td>
                  <td className="py-2 px-2 text-right font-mono font-bold text-[#3F1D5C]">
                    {formatAED(row.closeCr, { zeroAsDash: true })}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-[#3F1D5C] text-white font-bold border-t-2 border-[#5B2C83] text-xs">
              <tr>
                <td colSpan={3} className="py-3 px-3 uppercase tracking-wider text-right">
                  Trial Balance Totals (AED):
                </td>
                <td className="py-3 px-2 text-right font-mono text-amber-300">
                  {formatAED(tbRows.totals.openDr)}
                </td>
                <td className="py-3 px-2 text-right font-mono text-amber-300 border-r border-plum-400">
                  {formatAED(tbRows.totals.openCr)}
                </td>
                <td className="py-3 px-2 text-right font-mono text-white">
                  {formatAED(tbRows.totals.moveDr)}
                </td>
                <td className="py-3 px-2 text-right font-mono text-white border-r border-plum-400">
                  {formatAED(tbRows.totals.moveCr)}
                </td>
                <td className="py-3 px-2 text-right font-mono text-emerald-300 text-sm">
                  {formatAED(tbRows.totals.closeDr)}
                </td>
                <td className="py-3 px-2 text-right font-mono text-emerald-300 text-sm">
                  {formatAED(tbRows.totals.closeCr)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
};
