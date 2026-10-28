import React, { useState, useMemo } from 'react';
import Decimal from 'decimal.js';
import {
  FileSpreadsheet,
  Download,
  Printer,
  FileText,
  Filter,
  BookOpen,
} from 'lucide-react';
import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { getDb } from '../../core/storage';
import { CHART_OF_ACCOUNTS } from '../../data/chartOfAccounts';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { formatAED } from '../../core/currency';

interface GeneralLedgerReportPageProps {
  onNavigate: (route: string) => void;
}

export const GeneralLedgerReportPage: React.FC<GeneralLedgerReportPageProps> = ({ onNavigate }) => {
  const db = getDb();

  const [selectedBU, setSelectedBU] = useState<string>('All');
  const [accountFrom, setAccountFrom] = useState<string>('2000'); // Trade Payables
  const [accountTo, setAccountTo] = useState<string>('2000');
  const [includeOpening, setIncludeOpening] = useState(true);

  // Filter journals and build account ledgers
  const ledgerData = useMemo(() => {
    const fromCode = parseInt(accountFrom, 10) || 1000;
    const toCode = parseInt(accountTo, 10) || 7300;

    const targetAccounts = CHART_OF_ACCOUNTS.filter((a) => {
      const codeNum = parseInt(a.code, 10);
      return codeNum >= fromCode && codeNum <= toCode;
    });

    const accountLedgers = targetAccounts.map((acct) => {
      let runningBal = new Decimal(0);
      const lines: Array<{
        date: string;
        journalNumber: string;
        sourceModule: string;
        documentNumber: string;
        description: string;
        bu: string;
        debit: number;
        credit: number;
        balance: number;
      }> = [];

      db.glJournals.forEach((j) => {
        if (j.status !== 'Posted') return;

        j.lines.forEach((l) => {
          if (l.account !== acct.code) return;
          if (selectedBU !== 'All' && l.businessUnit !== selectedBU) return;

          const isOpening = j.sourceModule === 'Opening Balances';
          if (!includeOpening && isOpening) return;

          const dr = new Decimal(l.debit || 0);
          const cr = new Decimal(l.credit || 0);

          if (acct.normalBalance === 'Debit') {
            runningBal = runningBal.plus(dr).minus(cr);
          } else {
            runningBal = runningBal.plus(cr).minus(dr);
          }

          lines.push({
            date: j.journalDate,
            journalNumber: j.number,
            sourceModule: j.sourceModule,
            documentNumber: l.sourceDocumentNumber || j.number,
            description: l.description || j.description,
            bu: l.businessUnit,
            debit: dr.toNumber(),
            credit: cr.toNumber(),
            balance: runningBal.toNumber(),
          });
        });
      });

      return {
        account: acct,
        lines,
        closingBalance: runningBal.toNumber(),
      };
    });

    return accountLedgers.filter((al) => al.lines.length > 0);
  }, [db.glJournals, selectedBU, accountFrom, accountTo, includeOpening]);

  // Export to Excel
  const handleExportExcel = () => {
    const rows: any[] = [];
    ledgerData.forEach((al) => {
      rows.push({
        Date: `ACCOUNT: ${al.account.code} - ${al.account.name}`,
        'Journal No.': '',
        'Source Module': '',
        'Doc No.': '',
        BU: '',
        Description: '',
        Debit: '',
        Credit: '',
        Balance: '',
      });
      al.lines.forEach((l) => {
        rows.push({
          Date: l.date,
          'Journal No.': l.journalNumber,
          'Source Module': l.sourceModule,
          'Doc No.': l.documentNumber,
          BU: l.bu,
          Description: l.description,
          Debit: l.debit,
          Credit: l.credit,
          Balance: l.balance,
        });
      });
      rows.push({
        Date: `CLOSING BALANCE`,
        'Journal No.': '',
        'Source Module': '',
        'Doc No.': '',
        BU: '',
        Description: '',
        Debit: '',
        Credit: '',
        Balance: al.closingBalance,
      });
    });

    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'GL Report');
    XLSX.writeFile(wb, `General_Ledger_Report_${accountFrom}_${accountTo}.xlsx`);
  };

  // Export to CSV
  const handleExportCSV = () => {
    const rows: any[] = [];
    ledgerData.forEach((al) => {
      al.lines.forEach((l) => {
        rows.push({
          Account: al.account.code,
          Date: l.date,
          Journal: l.journalNumber,
          Source: l.sourceModule,
          DocNo: l.documentNumber,
          BU: l.bu,
          Description: l.description,
          Debit: l.debit,
          Credit: l.credit,
          RunningBalance: l.balance,
        });
      });
    });
    const ws = XLSX.utils.json_to_sheet(rows);
    const csv = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `General_Ledger_Report_${accountFrom}_${accountTo}.csv`;
    link.click();
  };

  // Export to PDF
  const handleExportPDF = () => {
    const doc = new jsPDF({ orientation: 'landscape' });
    doc.setFontSize(14);
    doc.setTextColor(91, 44, 131);
    doc.text('Meridian Healthcare Group — General Ledger Account Detail Report', 14, 14);
    doc.setFontSize(9);
    doc.setTextColor(100);
    doc.text(
      `Accounts: ${accountFrom} to ${accountTo} | Entity: ${selectedBU} | Year 2026 | Currency: AED`,
      14,
      20
    );

    const headers = [['Date', 'Journal No.', 'Source', 'Doc Ref', 'BU', 'Description', 'Debit', 'Credit', 'Balance']];
    const data: any[] = [];

    ledgerData.forEach((al) => {
      data.push([
        { content: `ACCOUNT: ${al.account.code} - ${al.account.name}`, colSpan: 9, styles: { fontStyle: 'bold', fillColor: [237, 228, 245] } },
      ]);
      al.lines.forEach((l) => {
        data.push([
          l.date,
          l.journalNumber,
          l.sourceModule,
          l.documentNumber,
          l.bu,
          l.description,
          formatAED(l.debit, { zeroAsDash: true }),
          formatAED(l.credit, { zeroAsDash: true }),
          formatAED(l.balance),
        ]);
      });
      data.push([
        { content: `Closing Balance: AED ${formatAED(al.closingBalance)}`, colSpan: 9, styles: { fontStyle: 'bold', halign: 'right' } },
      ]);
    });

    autoTable(doc, {
      head: headers,
      body: data,
      startY: 24,
      styles: { fontSize: 7, cellPadding: 2 },
      headStyles: { fillColor: [91, 44, 131], textColor: [255, 255, 255] },
    });

    doc.save(`General_Ledger_Report_${accountFrom}_${accountTo}.pdf`);
  };

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <BookOpen className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">General Ledger Detail Report</h1>
            <p className="text-xs text-gray-500">
              Account transaction activity with opening balance, movements, and running balance.
            </p>
          </div>
        </div>

        {/* Action Controls */}
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

      {/* Filter Parameters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-5 shadow-xs flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block font-semibold text-gray-600 mb-1">Business Unit</label>
            <select
              value={selectedBU}
              onChange={(e) => setSelectedBU(e.target.value)}
              className="bg-gray-50 border border-gray-300 rounded px-3 py-1 font-semibold text-gray-800"
            >
              <option value="All">All Business Units</option>
              {BUSINESS_UNITS.map((bu) => (
                <option key={bu.code} value={bu.code}>
                  {bu.code} - {bu.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-gray-600 mb-1">Account From</label>
            <input
              type="text"
              value={accountFrom}
              onChange={(e) => setAccountFrom(e.target.value)}
              className="bg-gray-50 border border-gray-300 rounded px-3 py-1 font-mono font-bold w-24 text-gray-800"
            />
          </div>

          <div>
            <label className="block font-semibold text-gray-600 mb-1">Account To</label>
            <input
              type="text"
              value={accountTo}
              onChange={(e) => setAccountTo(e.target.value)}
              className="bg-gray-50 border border-gray-300 rounded px-3 py-1 font-mono font-bold w-24 text-gray-800"
            />
          </div>

          <div className="self-end pb-1.5">
            <label className="flex items-center space-x-1.5 cursor-pointer text-gray-700">
              <input
                type="checkbox"
                checked={includeOpening}
                onChange={(e) => setIncludeOpening(e.target.checked)}
                className="rounded text-[#5B2C83] focus:ring-[#5B2C83]"
              />
              <span>Include Opening Balances</span>
            </label>
          </div>
        </div>

        <span className="text-gray-500 text-xs">
          Showing <strong className="text-gray-900">{ledgerData.length}</strong> matching ledger account(s)
        </span>
      </div>

      {/* Output Tables per Account */}
      <div className="space-y-6">
        {ledgerData.map((al) => (
          <div key={al.account.code} className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
            <div className="bg-[#EDE4F5] p-3.5 border-b border-plum-200 flex items-center justify-between">
              <div>
                <span className="font-mono font-bold text-sm text-[#3F1D5C] mr-2">
                  {al.account.code}
                </span>
                <span className="font-bold text-sm text-gray-900">{al.account.name}</span>
                <span className="text-[11px] text-gray-500 ml-2">
                  ({al.account.type} &bull; Normal {al.account.normalBalance})
                </span>
              </div>
              <div className="font-mono text-xs">
                <span>Closing Balance: </span>
                <strong className="text-[#3F1D5C] font-bold text-sm">
                  AED {formatAED(al.closingBalance, { useBracketsForNegative: true })}
                </strong>
              </div>
            </div>

            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-gray-100 text-gray-700 font-semibold border-b border-gray-200 text-[11px]">
                <tr>
                  <th className="py-2 px-3 w-24">Date</th>
                  <th className="py-2 px-3 w-32">Journal No.</th>
                  <th className="py-2 px-3 w-32">Source Module</th>
                  <th className="py-2 px-3 w-36">Doc Number</th>
                  <th className="py-2 px-3 w-16">BU</th>
                  <th className="py-2 px-3">Description</th>
                  <th className="py-2 px-3 text-right w-28">Debit (AED)</th>
                  <th className="py-2 px-3 text-right w-28">Credit (AED)</th>
                  <th className="py-2 px-3 text-right w-32">Running Bal. (AED)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {al.lines.map((l, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="py-2 px-3 font-medium text-gray-800">{l.date}</td>
                    <td className="py-2 px-3 font-mono font-bold text-[#5B2C83]">{l.journalNumber}</td>
                    <td className="py-2 px-3 text-gray-600">{l.sourceModule}</td>
                    <td className="py-2 px-3 font-mono text-gray-700">{l.documentNumber}</td>
                    <td className="py-2 px-3 font-semibold text-gray-800">{l.bu}</td>
                    <td className="py-2 px-3 text-gray-800">{l.description}</td>
                    <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                      {l.debit > 0 ? formatAED(l.debit) : '—'}
                    </td>
                    <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                      {l.credit > 0 ? formatAED(l.credit) : '—'}
                    </td>
                    <td className="py-2 px-3 text-right font-mono font-bold text-[#3F1D5C]">
                      {formatAED(l.balance, { useBracketsForNegative: true })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
};
