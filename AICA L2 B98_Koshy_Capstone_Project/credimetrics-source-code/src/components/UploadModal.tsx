import React, { useState } from 'react';
import { 
  X, 
  UploadCloud, 
  FileSpreadsheet, 
  FileText, 
  Download, 
  CheckCircle2, 
  AlertCircle, 
  Calculator,
  RefreshCw
} from 'lucide-react';
import { Company, FinancialStatement, BalanceSheet, ProfitAndLoss } from '../types/financial';
import { parseFinancialFile } from '../utils/excelParser';
import { downloadSampleUploadTemplate } from '../utils/reportGenerator';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  company: Company;
  onStatementsUploaded: (statements: FinancialStatement[]) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  company,
  onStatementsUploaded
}) => {
  const [activeTab, setActiveTab] = useState<'upload' | 'manual'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Manual Form State
  const [financialYear, setFinancialYear] = useState('FY 2024-25');
  
  // P&L
  const [revenue, setRevenue] = useState<number>(150);
  const [cogs, setCogs] = useState<number>(90);
  const [operatingExpenses, setOperatingExpenses] = useState<number>(30);
  const [depreciation, setDepreciation] = useState<number>(6);
  const [interestExpense, setInterestExpense] = useState<number>(3);
  const [taxRate, setTaxRate] = useState<number>(25); // %

  // Balance Sheet Assets
  const [cash, setCash] = useState<number>(6);
  const [bank, setBank] = useState<number>(14);
  const [receivables, setReceivables] = useState<number>(25);
  const [inventory, setInventory] = useState<number>(20);
  const [otherCurrentAssets, setOtherCurrentAssets] = useState<number>(5);
  const [fixedAssets, setFixedAssets] = useState<number>(60);
  const [investments, setInvestments] = useState<number>(10);

  // Balance Sheet Liabilities & Equity
  const [payables, setPayables] = useState<number>(18);
  const [shortTermDebt, setShortTermDebt] = useState<number>(8);
  const [otherCurrentLiabilities, setOtherCurrentLiabilities] = useState<number>(4);
  const [longTermDebt, setLongTermDebt] = useState<number>(20);
  const [equity, setEquity] = useState<number>(25);
  const [reserves, setReserves] = useState<number>(65);

  if (!isOpen) return null;

  // Computed P&L
  const grossProfit = revenue - cogs;
  const ebitda = grossProfit - operatingExpenses;
  const ebit = ebitda - depreciation;
  const profitBeforeTax = ebit - interestExpense;
  const taxExpense = Math.max(0, profitBeforeTax * (taxRate / 100));
  const netProfit = profitBeforeTax - taxExpense;

  // Computed Balance Sheet
  const totalCurrentAssets = cash + bank + receivables + inventory + otherCurrentAssets;
  const totalAssets = totalCurrentAssets + fixedAssets + investments;

  const totalCurrentLiabilities = payables + shortTermDebt + otherCurrentLiabilities;
  const totalDebt = shortTermDebt + longTermDebt;
  const totalEquity = equity + reserves;
  const totalLiabilities = totalCurrentLiabilities + longTermDebt + totalEquity;

  const balanceDifference = Number((totalAssets - totalLiabilities).toFixed(2));
  const isBalanced = Math.abs(balanceDifference) < 0.05;

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setErrorMsg(null);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMsg(null);
    }
  };

  const handleProcessFile = async () => {
    if (!file) {
      setErrorMsg('Please select an Excel (.xlsx/.xls) or CSV file first.');
      return;
    }

    try {
      setIsParsing(true);
      setErrorMsg(null);
      const parsed = await parseFinancialFile(file, company.id);
      onStatementsUploaded(parsed);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to parse financial spreadsheet.');
    } finally {
      setIsParsing(false);
    }
  };

  const handleAutoBalance = () => {
    // Automatically balance reserves to match assets
    const neededReserves = totalAssets - (totalCurrentLiabilities + longTermDebt + equity);
    setReserves(Number(neededReserves.toFixed(2)));
  };

  const handleSubmitManual = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isBalanced) {
      setErrorMsg(`Balance Sheet is not in balance! Total Assets (${totalAssets} Cr) ≠ Total Liabilities & Equity (${totalLiabilities} Cr). Difference: ${balanceDifference} Cr.`);
      return;
    }

    const bs: BalanceSheet = {
      cash,
      bank,
      receivables,
      inventory,
      otherCurrentAssets,
      fixedAssets,
      investments,
      otherNonCurrentAssets: 0,
      payables,
      shortTermDebt,
      otherCurrentLiabilities,
      longTermDebt,
      otherNonCurrentLiabilities: 0,
      equity,
      reserves,
      totalCurrentAssets,
      totalCurrentLiabilities,
      totalDebt,
      totalEquity,
      totalAssets,
      totalLiabilities
    };

    const pl: ProfitAndLoss = {
      revenue,
      otherIncome: 0,
      cogs,
      grossProfit,
      operatingExpenses,
      ebitda,
      depreciation,
      ebit,
      interestExpense,
      profitBeforeTax,
      taxExpense,
      netProfit
    };

    const newStmt: FinancialStatement = {
      id: `stmt-${company.id}-${Date.now()}`,
      companyId: company.id,
      financialYear,
      currency: 'INR',
      unit: 'Crores',
      balanceSheet: bs,
      profitAndLoss: pl
    };

    onStatementsUploaded([newStmt]);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden my-8">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-850">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-blue-400" />
              Upload Financial Statements for <span className="text-cyan-300">{company.companyName}</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Supports Excel (.xlsx, .xls), CSV, or interactive Manual Entry with balance verification.
            </p>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab switch */}
        <div className="flex border-b border-slate-800 bg-slate-900/50">
          <button
            onClick={() => { setActiveTab('upload'); setErrorMsg(null); }}
            className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider flex items-center justify-center space-x-2 border-b-2 transition ${
              activeTab === 'upload'
                ? 'border-blue-500 text-blue-400 bg-slate-800/40'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span>Excel / CSV Upload</span>
          </button>

          <button
            onClick={() => { setActiveTab('manual'); setErrorMsg(null); }}
            className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider flex items-center justify-center space-x-2 border-b-2 transition ${
              activeTab === 'manual'
                ? 'border-blue-500 text-blue-400 bg-slate-800/40'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Calculator className="w-4 h-4" />
            <span>Interactive Manual Entry</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {errorMsg && (
            <div className="mb-4 p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {activeTab === 'upload' ? (
            <div className="space-y-6">
              {/* Drag and Drop Zone */}
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleFileDrop}
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition flex flex-col items-center justify-center cursor-pointer ${
                  file ? 'border-cyan-500 bg-cyan-950/10' : 'border-slate-700 hover:border-blue-500 bg-slate-800/30'
                }`}
              >
                <div className="w-14 h-14 rounded-2xl bg-slate-800 flex items-center justify-center mb-3 text-blue-400 border border-slate-700">
                  <FileSpreadsheet className="w-7 h-7" />
                </div>
                
                {file ? (
                  <div>
                    <span className="text-xs uppercase font-bold text-cyan-400">File Selected</span>
                    <p className="text-base font-bold text-white mt-0.5">{file.name}</p>
                    <p className="text-xs text-slate-400 mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <div>
                    <h4 className="text-sm font-bold text-white">Drag and drop your financial spreadsheet here</h4>
                    <p className="text-xs text-slate-400 mt-1">Supports multi-year Balance Sheet &amp; P&amp;L columns (.xlsx, .xls, .csv)</p>
                    <label className="mt-4 inline-block bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer border border-slate-700 transition">
                      Browse Files
                      <input 
                        type="file" 
                        accept=".xlsx, .xls, .csv" 
                        onChange={handleFileChange} 
                        className="hidden" 
                      />
                    </label>
                  </div>
                )}
              </div>

              {/* Template Helper Card */}
              <div className="bg-slate-850 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <h5 className="text-xs font-bold text-white">Need a structured spreadsheet template?</h5>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Download our pre-formatted Excel template with standard Balance Sheet &amp; P&amp;L items ready for import.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={downloadSampleUploadTemplate}
                  className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 px-3.5 py-2 rounded-lg text-xs font-semibold shrink-0 transition"
                >
                  <Download className="w-4 h-4" />
                  <span>Download Excel Template</span>
                </button>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!file || isParsing}
                  onClick={handleProcessFile}
                  className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-xs font-bold transition shadow-lg shadow-blue-600/30"
                >
                  {isParsing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Parsing Financials...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Import &amp; Calculate Ratios</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            /* Interactive Manual Entry Form */
            <form onSubmit={handleSubmitManual} className="space-y-6">
              
              <div className="flex items-center justify-between bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                <div className="flex items-center space-x-2">
                  <label className="text-xs font-bold text-slate-300">Financial Reporting Year:</label>
                  <input
                    type="text"
                    value={financialYear}
                    onChange={(e) => setFinancialYear(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white font-mono focus:border-blue-500 focus:outline-none"
                    placeholder="e.g. FY 2024-25"
                    required
                  />
                </div>
                <span className="text-[11px] text-slate-400 font-mono">All amounts in INR Crores</span>
              </div>

              {/* Grid: P&L and Balance Sheet */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* 1. Profit & Loss Column */}
                <div className="bg-slate-850 p-4 rounded-xl border border-slate-800 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 border-b border-slate-800 pb-2">
                    Profit &amp; Loss Statement
                  </h4>

                  <div className="grid grid-cols-2 gap-2.5 text-xs">
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Revenue from Operations</label>
                      <input
                        type="number"
                        step="any"
                        value={revenue}
                        onChange={e => setRevenue(parseFloat(e.target.value) || 0)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Cost of Goods Sold (COGS)</label>
                      <input
                        type="number"
                        step="any"
                        value={cogs}
                        onChange={e => setCogs(parseFloat(e.target.value) || 0)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-white font-mono"
                      />
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Operating Expenses (SG&amp;A)</label>
                      <input
                        type="number"
                        step="any"
                        value={operatingExpenses}
                        onChange={e => setOperatingExpenses(parseFloat(e.target.value) || 0)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Depreciation &amp; Amort.</label>
                      <input
                        type="number"
                        step="any"
                        value={depreciation}
                        onChange={e => setDepreciation(parseFloat(e.target.value) || 0)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-white font-mono"
                      />
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Interest &amp; Finance Expense</label>
                      <input
                        type="number"
                        step="any"
                        value={interestExpense}
                        onChange={e => setInterestExpense(parseFloat(e.target.value) || 0)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Effective Tax Rate (%)</label>
                      <input
                        type="number"
                        step="any"
                        value={taxRate}
                        onChange={e => setTaxRate(parseFloat(e.target.value) || 0)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-white font-mono"
                      />
                    </div>
                  </div>

                  {/* Computed P&L Subtotals */}
                  <div className="pt-2 border-t border-slate-800 text-[11px] space-y-1 bg-slate-900/60 p-2.5 rounded-lg font-mono">
                    <div className="flex justify-between text-slate-300">
                      <span>Gross Profit:</span>
                      <span className="font-bold">{grossProfit.toFixed(2)} Cr</span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>EBITDA:</span>
                      <span className="font-bold">{ebitda.toFixed(2)} Cr</span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>EBIT (Operating Profit):</span>
                      <span className="font-bold">{ebit.toFixed(2)} Cr</span>
                    </div>
                    <div className="flex justify-between text-cyan-300 font-bold border-t border-slate-800 pt-1">
                      <span>Net Profit After Tax (PAT):</span>
                      <span>{netProfit.toFixed(2)} Cr</span>
                    </div>
                  </div>
                </div>

                {/* 2. Balance Sheet Column */}
                <div className="bg-slate-850 p-4 rounded-xl border border-slate-800 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400 border-b border-slate-800 pb-2">
                    Balance Sheet Elements
                  </h4>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Cash</label>
                      <input type="number" step="any" value={cash} onChange={e => setCash(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Bank Balances</label>
                      <input type="number" step="any" value={bank} onChange={e => setBank(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Receivables (Debtors)</label>
                      <input type="number" step="any" value={receivables} onChange={e => setReceivables(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Inventories</label>
                      <input type="number" step="any" value={inventory} onChange={e => setInventory(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Fixed Assets (PPE)</label>
                      <input type="number" step="any" value={fixedAssets} onChange={e => setFixedAssets(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Investments</label>
                      <input type="number" step="any" value={investments} onChange={e => setInvestments(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    
                    <div className="col-span-2 pt-1 border-t border-slate-800 text-[10px] text-slate-400 uppercase font-bold">
                      Liabilities &amp; Equity
                    </div>

                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Trade Payables</label>
                      <input type="number" step="any" value={payables} onChange={e => setPayables(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Short Term Debt</label>
                      <input type="number" step="any" value={shortTermDebt} onChange={e => setShortTermDebt(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Long Term Debt</label>
                      <input type="number" step="any" value={longTermDebt} onChange={e => setLongTermDebt(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Equity (Share Capital)</label>
                      <input type="number" step="any" value={equity} onChange={e => setEquity(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                    <div className="col-span-2">
                      <label className="text-[10px] text-slate-400 block mb-0.5">Reserves &amp; Surplus</label>
                      <input type="number" step="any" value={reserves} onChange={e => setReserves(parseFloat(e.target.value) || 0)} className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs" />
                    </div>
                  </div>

                  {/* Balancing Inspector */}
                  <div className={`p-2.5 rounded-lg border text-xs ${
                    isBalanced 
                      ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300' 
                      : 'bg-amber-950/40 border-amber-800 text-amber-300'
                  }`}>
                    <div className="flex items-center justify-between font-mono">
                      <span>Total Assets: {totalAssets.toFixed(2)} Cr</span>
                      <span>Total Liab: {totalLiabilities.toFixed(2)} Cr</span>
                    </div>
                    <div className="flex items-center justify-between mt-1 text-[11px]">
                      <span>{isBalanced ? '✓ Balance Sheet is balanced' : `Mismatch: ${balanceDifference > 0 ? '+' : ''}${balanceDifference} Cr`}</span>
                      {!isBalanced && (
                        <button
                          type="button"
                          onClick={handleAutoBalance}
                          className="text-cyan-300 hover:text-cyan-200 underline font-semibold"
                        >
                          Auto-balance Reserves
                        </button>
                      )}
                    </div>
                  </div>

                </div>

              </div>

              {/* Submit Manual */}
              <div className="flex items-center justify-end space-x-3 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!isBalanced}
                  className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-xs font-bold transition shadow-lg shadow-blue-600/30"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Save &amp; Compute Ratios</span>
                </button>
              </div>

            </form>
          )}

        </div>

      </div>
    </div>
  );
};
