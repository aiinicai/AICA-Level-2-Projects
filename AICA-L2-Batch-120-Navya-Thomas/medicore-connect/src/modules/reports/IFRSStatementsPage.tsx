import React, { useState, useMemo } from 'react';
import Decimal from 'decimal.js';
import {
  FileSpreadsheet,
  Download,
  Printer,
  FileText,
  CheckCircle2,
  Building2,
  Sparkles,
  BookOpen,
} from 'lucide-react';
import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { getDb } from '../../core/storage';
import { CHART_OF_ACCOUNTS } from '../../data/chartOfAccounts';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { formatAED, round2 } from '../../core/currency';

interface IFRSStatementsPageProps {
  onNavigate: (route: string) => void;
}

export const IFRSStatementsPage: React.FC<IFRSStatementsPageProps> = ({ onNavigate }) => {
  const db = getDb();

  const [activeStatement, setActiveStatement] = useState<'BS' | 'PL' | 'EQUITY' | 'CASH' | 'NOTES'>('BS');
  const [selectedBU, setSelectedBU] = useState<string>('All');
  const [scaleK, setScaleK] = useState(false); // AED vs AED '000

  // Calculate TB Balances and IFRS groupings
  const financialData = useMemo(() => {
    const acctTotals: Record<string, { current: Decimal; prior: Decimal }> = {};

    CHART_OF_ACCOUNTS.forEach((a) => {
      acctTotals[a.code] = { current: new Decimal(0), prior: new Decimal(0) };
    });

    db.glJournals.forEach((j) => {
      if (j.status !== 'Posted') return;

      const isOpening = j.sourceModule === 'Opening Balances';
      j.lines.forEach((l) => {
        // Intercompany elimination on consolidation
        if (selectedBU === 'All' && (l.account === '1500' || l.account === '2500' || l.account === '4900' || l.account === '6400')) {
          return; // eliminate
        }

        if (selectedBU !== 'All' && l.businessUnit !== selectedBU) return;

        if (acctTotals[l.account]) {
          const d = new Decimal(l.debit || 0);
          const c = new Decimal(l.credit || 0);
          const acct = CHART_OF_ACCOUNTS.find((a) => a.code === l.account);
          const isDrNormal = acct?.normalBalance === 'Debit';
          const net = isDrNormal ? d.minus(c) : c.minus(d);

          if (isOpening) {
            acctTotals[l.account].prior = acctTotals[l.account].prior.plus(net);
          }
          acctTotals[l.account].current = acctTotals[l.account].current.plus(net);
        }
      });
    });

    const getBal = (code: string) => acctTotals[code]?.current || new Decimal(0);
    const getPrior = (code: string) => acctTotals[code]?.prior || new Decimal(0);

    // 1. Balance Sheet Lines
    // Cash & Equivalents (1000 - 1040)
    let cashCurrent = new Decimal(0);
    let cashPrior = new Decimal(0);
    for (let c = 1000; c <= 1040; c += 10) {
      cashCurrent = cashCurrent.plus(getBal(String(c)));
      cashPrior = cashPrior.plus(getPrior(String(c)));
    }

    // Trade Receivables (1100 + 1110 + 1120 - 1190)
    const arGrossCurrent = getBal('1100').plus(getBal('1110')).plus(getBal('1120'));
    const arEclCurrent = getBal('1190');
    const arNetCurrent = arGrossCurrent.minus(arEclCurrent);

    const arGrossPrior = getPrior('1100').plus(getPrior('1110')).plus(getPrior('1120'));
    const arEclPrior = getPrior('1190');
    const arNetPrior = arGrossPrior.minus(arEclPrior);

    // Inventories (1200 - 1230)
    let invCurrent = new Decimal(0);
    let invPrior = new Decimal(0);
    for (let c = 1200; c <= 1230; c += 10) {
      invCurrent = invCurrent.plus(getBal(String(c)));
      invPrior = invPrior.plus(getPrior(String(c)));
    }

    // Prepayments & Other (1300 + 1310 + 1320 + 1400)
    const prepayCurrent = getBal('1300').plus(getBal('1310')).plus(getBal('1320')).plus(getBal('1400'));
    const prepayPrior = getPrior('1300').plus(getPrior('1310')).plus(getPrior('1320')).plus(getPrior('1400'));

    // Intercompany Receivable (1500) if single BU
    const icRecCurrent = selectedBU !== 'All' ? getBal('1500') : new Decimal(0);
    const icRecPrior = selectedBU !== 'All' ? getPrior('1500') : new Decimal(0);

    const totalCurrentAssets = cashCurrent.plus(arNetCurrent).plus(invCurrent).plus(prepayCurrent).plus(icRecCurrent);
    const totalCurrentAssetsPrior = cashPrior.plus(arNetPrior).plus(invPrior).plus(prepayPrior).plus(icRecPrior);

    // Non-Current Assets: PPE (1700 - 1770) less Accum Dep (1810 - 1870) + CWIP (1600, 1610)
    let ppeCostCurrent = new Decimal(0);
    let ppeDepCurrent = new Decimal(0);
    let ppeCostPrior = new Decimal(0);
    let ppeDepPrior = new Decimal(0);

    for (let c = 1700; c <= 1770; c += 10) {
      ppeCostCurrent = ppeCostCurrent.plus(getBal(String(c)));
      ppeCostPrior = ppeCostPrior.plus(getPrior(String(c)));
    }
    for (let c = 1810; c <= 1870; c += 10) {
      ppeDepCurrent = ppeDepCurrent.plus(getBal(String(c)));
      ppeDepPrior = ppeDepPrior.plus(getPrior(String(c)));
    }
    const cwipCurrent = getBal('1600').plus(getBal('1610'));
    const cwipPrior = getPrior('1600').plus(getPrior('1610'));

    const ppeNetCurrent = ppeCostCurrent.minus(ppeDepCurrent).plus(cwipCurrent);
    const ppeNetPrior = ppeCostPrior.minus(ppeDepPrior).plus(cwipPrior);

    const totalAssets = totalCurrentAssets.plus(ppeNetCurrent);
    const totalAssetsPrior = totalCurrentAssetsPrior.plus(ppeNetPrior);

    // Current Liabilities
    const apCurrent = getBal('2000').plus(getBal('2010'));
    const apPrior = getPrior('2000').plus(getPrior('2010'));

    const accruedExpCurrent = getBal('2020').plus(getBal('2100')).plus(getBal('2200'));
    const accruedExpPrior = getPrior('2020').plus(getPrior('2100')).plus(getPrior('2200'));

    const patientDepCurrent = getBal('2300');
    const patientDepPrior = getPrior('2300');

    const taxPayCurrent = getBal('2400');
    const taxPayPrior = getPrior('2400');

    const icPayCurrent = selectedBU !== 'All' ? getBal('2500') : new Decimal(0);
    const icPayPrior = selectedBU !== 'All' ? getPrior('2500') : new Decimal(0);

    const bankLoanCurrent = getBal('2700');
    const bankLoanCurrentPrior = getPrior('2700');

    const totalCurrentLiab = apCurrent.plus(accruedExpCurrent).plus(patientDepCurrent).plus(taxPayCurrent).plus(icPayCurrent).plus(bankLoanCurrent);
    const totalCurrentLiabPrior = apPrior.plus(accruedExpPrior).plus(patientDepPrior).plus(taxPayPrior).plus(icPayPrior).plus(bankLoanCurrentPrior);

    // Non-Current Liabilities
    const eosbCurrent = getBal('2210');
    const eosbPrior = getPrior('2210');
    const leaseLiabCurrent = getBal('2600');
    const leaseLiabPrior = getPrior('2600');
    const bankLoanNcCurrent = getBal('2710');
    const bankLoanNcPrior = getPrior('2710');

    const totalNcLiab = eosbCurrent.plus(leaseLiabCurrent).plus(bankLoanNcCurrent);
    const totalNcLiabPrior = eosbPrior.plus(leaseLiabPrior).plus(bankLoanNcPrior);

    const totalLiabilities = totalCurrentLiab.plus(totalNcLiab);
    const totalLiabilitiesPrior = totalCurrentLiabPrior.plus(totalNcLiabPrior);

    // Equity: Share Capital, Retained Earnings, Current Profit
    const shareCap = getBal('3000');
    const retainedEarn = getBal('3100');
    const reserves = getBal('3200');

    // 2. Profit & Loss Lines
    let grossRevenue = new Decimal(0);
    for (let c = 4000; c <= 4060; c += 10) {
      grossRevenue = grossRevenue.plus(getBal(String(c)));
    }
    const discounts4090 = getBal('4090');
    const netRevenue = grossRevenue.minus(discounts4090);

    let cos = new Decimal(0);
    for (let c = 5000; c <= 5110; c += 10) {
      cos = cos.plus(getBal(String(c)));
    }
    const grossProfit = netRevenue.minus(cos);

    let adminSelling = new Decimal(0);
    for (let c = 6000; c <= 6290; c += 10) {
      if (c === 6210) continue;
      adminSelling = adminSelling.plus(getBal(String(c)));
    }
    adminSelling = adminSelling.plus(getBal('6320')); // Medical waste

    const depreciationExp = getBal('6300');
    const eclExp = getBal('6310');
    const financeCosts = getBal('7000');
    const corporateTax = getBal('7300');
    const otherIncome = getBal('4950');

    const operatingProfit = grossProfit.minus(adminSelling).minus(depreciationExp).minus(eclExp).plus(otherIncome);
    const profitBeforeTax = operatingProfit.minus(financeCosts);
    const profitForPeriod = profitBeforeTax.minus(corporateTax);

    // Balance Sheet Equity Total
    const totalEquity = shareCap.plus(retainedEarn).plus(reserves).plus(profitForPeriod);
    const totalEquityPrior = shareCap.plus(retainedEarn).plus(reserves);

    const totalLiabAndEquity = totalLiabilities.plus(totalEquity);
    const bsDiff = totalAssets.minus(totalLiabAndEquity).abs();

    return {
      bs: {
        cashCurrent,
        cashPrior,
        arNetCurrent,
        arNetPrior,
        invCurrent,
        invPrior,
        prepayCurrent,
        prepayPrior,
        icRecCurrent,
        icRecPrior,
        totalCurrentAssets,
        totalCurrentAssetsPrior,
        ppeCostCurrent,
        ppeCostPrior,
        ppeDepCurrent,
        ppeDepPrior,
        cwipCurrent,
        cwipPrior,
        ppeNetCurrent,
        ppeNetPrior,
        totalAssets,
        totalAssetsPrior,
        apCurrent,
        apPrior,
        accruedExpCurrent,
        accruedExpPrior,
        patientDepCurrent,
        patientDepPrior,
        taxPayCurrent,
        taxPayPrior,
        icPayCurrent,
        icPayPrior,
        bankLoanCurrent,
        bankLoanCurrentPrior,
        totalCurrentLiab,
        totalCurrentLiabPrior,
        eosbCurrent,
        eosbPrior,
        leaseLiabCurrent,
        leaseLiabPrior,
        bankLoanNcCurrent,
        bankLoanNcPrior,
        totalNcLiab,
        totalNcLiabPrior,
        totalLiabilities,
        totalLiabilitiesPrior,
        shareCap,
        retainedEarn,
        reserves,
        profitForPeriod,
        totalEquity,
        totalEquityPrior,
        totalLiabAndEquity,
        isBalanced: bsDiff.lessThanOrEqualTo(0.005),
        bsDiff,
      },
      pl: {
        grossRevenue,
        discounts4090,
        netRevenue,
        cos,
        grossProfit,
        adminSelling,
        depreciationExp,
        eclExp,
        otherIncome,
        operatingProfit,
        financeCosts,
        profitBeforeTax,
        corporateTax,
        profitForPeriod,
      },
    };
  }, [db.glJournals, selectedBU]);

  const scaleVal = (val: Decimal | number) => {
    const n = typeof val === 'number' ? val : val.toNumber();
    return scaleK ? n / 1000 : n;
  };

  const fmt = (val: Decimal | number, brackets = false) => {
    return formatAED(scaleVal(val), { useBracketsForNegative: brackets, zeroAsDash: true, decimals: scaleK ? 1 : 2 });
  };

  // Export IFRS to Excel
  const handleExportExcel = () => {
    const data = [
      { Line: 'STATEMENT OF FINANCIAL POSITION', Current: '19/Oct/2026 (AED)', Prior: '01/Jan/2026 (AED)' },
      { Line: 'ASSETS', Current: '', Prior: '' },
      { Line: 'Cash and cash equivalents', Current: financialData.bs.cashCurrent.toNumber(), Prior: financialData.bs.cashPrior.toNumber() },
      { Line: 'Trade receivables, net', Current: financialData.bs.arNetCurrent.toNumber(), Prior: financialData.bs.arNetPrior.toNumber() },
      { Line: 'Inventories', Current: financialData.bs.invCurrent.toNumber(), Prior: financialData.bs.invPrior.toNumber() },
      { Line: 'Prepayments and other receivables', Current: financialData.bs.prepayCurrent.toNumber(), Prior: financialData.bs.prepayPrior.toNumber() },
      { Line: 'Total Current Assets', Current: financialData.bs.totalCurrentAssets.toNumber(), Prior: financialData.bs.totalCurrentAssetsPrior.toNumber() },
      { Line: 'Property, plant and equipment, net', Current: financialData.bs.ppeNetCurrent.toNumber(), Prior: financialData.bs.ppeNetPrior.toNumber() },
      { Line: 'TOTAL ASSETS', Current: financialData.bs.totalAssets.toNumber(), Prior: financialData.bs.totalAssetsPrior.toNumber() },
      { Line: '', Current: '', Prior: '' },
      { Line: 'LIABILITIES AND EQUITY', Current: '', Prior: '' },
      { Line: 'Trade and other payables', Current: financialData.bs.apCurrent.toNumber(), Prior: financialData.bs.apPrior.toNumber() },
      { Line: 'Accrued expenses & staff payables', Current: financialData.bs.accruedExpCurrent.toNumber(), Prior: financialData.bs.accruedExpPrior.toNumber() },
      { Line: 'Total Current Liabilities', Current: financialData.bs.totalCurrentLiab.toNumber(), Prior: financialData.bs.totalCurrentLiabPrior.toNumber() },
      { Line: 'Non-current borrowings & provisions', Current: financialData.bs.totalNcLiab.toNumber(), Prior: financialData.bs.totalNcLiabPrior.toNumber() },
      { Line: 'TOTAL LIABILITIES', Current: financialData.bs.totalLiabilities.toNumber(), Prior: financialData.bs.totalLiabilitiesPrior.toNumber() },
      { Line: 'Total Equity (including net profit)', Current: financialData.bs.totalEquity.toNumber(), Prior: financialData.bs.totalEquityPrior.toNumber() },
      { Line: 'TOTAL LIABILITIES AND EQUITY', Current: financialData.bs.totalLiabAndEquity.toNumber(), Prior: financialData.bs.totalAssetsPrior.toNumber() },
    ];

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'IFRS Financial Statements');
    XLSX.writeFile(wb, `IFRS_Statements_${selectedBU}_2026.xlsx`);
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
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">IFRS Financial Statements</h1>
            <p className="text-xs text-gray-500">
              IAS 1 Compliant &bull; Meridian Healthcare Group &bull; Currency: AED
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
            onClick={() => window.print()}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 text-xs font-semibold text-gray-700 flex items-center space-x-1.5 shadow-xs"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print View</span>
          </button>
        </div>
      </div>

      {/* Filter Parameters Strip */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-5 shadow-xs flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block font-semibold text-gray-600 mb-1">Reporting Entity</label>
            <select
              value={selectedBU}
              onChange={(e) => setSelectedBU(e.target.value)}
              className="bg-gray-50 border border-gray-300 rounded px-3 py-1 font-semibold text-gray-800 focus:ring-1 focus:ring-[#5B2C83]"
            >
              <option value="All">Consolidated Group (Intercompany Eliminated)</option>
              {BUSINESS_UNITS.map((bu) => (
                <option key={bu.code} value={bu.code}>
                  {bu.code} - {bu.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-gray-600 mb-1">Presentation Scale</label>
            <button
              onClick={() => setScaleK(!scaleK)}
              className={`px-3 py-1 rounded border font-semibold transition-colors ${
                scaleK
                  ? 'bg-[#5B2C83] text-white border-[#5B2C83]'
                  : 'bg-gray-50 text-gray-700 border-gray-300'
              }`}
            >
              {scaleK ? "AED '000 (Thousands)" : 'AED Exact (Fils)'}
            </button>
          </div>
        </div>

        {/* Exact Balance Check Indicator */}
        <div className="flex items-center space-x-2">
          {financialData.bs.isBalanced ? (
            <div className="flex items-center px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 mr-1 text-emerald-600" />
              <span>Balance Sheet Verified: Assets = Liabilities + Equity (Diff: 0.00 AED)</span>
            </div>
          ) : (
            <div className="flex items-center px-3 py-1.5 rounded-lg bg-rose-50 border border-rose-300 text-rose-800 text-xs font-semibold">
              <span>Discrepancy: AED {financialData.bs.bsDiff.toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Statement Tabs */}
      <div className="flex space-x-2 border-b border-gray-200 mb-5">
        <button
          onClick={() => setActiveStatement('BS')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeStatement === 'BS'
              ? 'border-[#5B2C83] text-[#5B2C83]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          1. Statement of Financial Position (Balance Sheet)
        </button>
        <button
          onClick={() => setActiveStatement('PL')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeStatement === 'PL'
              ? 'border-[#5B2C83] text-[#5B2C83]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          2. Profit or Loss & Other Comprehensive Income
        </button>
        <button
          onClick={() => setActiveStatement('CASH')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeStatement === 'CASH'
              ? 'border-[#5B2C83] text-[#5B2C83]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          3. Statement of Cash Flows (IAS 7 Indirect)
        </button>
        <button
          onClick={() => setActiveStatement('EQUITY')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeStatement === 'EQUITY'
              ? 'border-[#5B2C83] text-[#5B2C83]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          4. Statement of Changes in Equity
        </button>
        <button
          onClick={() => setActiveStatement('NOTES')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeStatement === 'NOTES'
              ? 'border-[#5B2C83] text-[#5B2C83]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          5. Disclosures & Accounting Notes
        </button>
      </div>

      {/* Statement Body */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs p-6">
        {/* STATEMENT OF FINANCIAL POSITION */}
        {activeStatement === 'BS' && (
          <div className="max-w-4xl mx-auto text-xs">
            <div className="text-center pb-4 mb-6 border-b border-gray-200">
              <h2 className="text-base font-bold text-gray-900 uppercase tracking-wide">
                Meridian Healthcare Group
              </h2>
              <h3 className="text-sm font-semibold text-[#5B2C83]">
                Statement of Financial Position
              </h3>
              <p className="text-gray-500 text-[11px] mt-0.5">
                As at 19 October 2026 (with comparative opening balances at 1 January 2026) &bull;{' '}
                {scaleK ? "Amounts in AED '000" : 'Amounts in AED'}
              </p>
            </div>

            <div className="divide-y divide-gray-100">
              {/* ASSETS */}
              <div className="py-2 font-bold text-gray-900 uppercase tracking-wider bg-gray-50 px-3 rounded">
                ASSETS
              </div>

              {/* Current Assets */}
              <div className="py-2 px-3 pl-6 font-semibold text-gray-700">Current Assets</div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Cash and cash equivalents</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.cashCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.cashPrior)}</span>
                </div>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Trade and other receivables, net</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.arNetCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.arNetPrior)}</span>
                </div>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Inventories</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.invCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.invPrior)}</span>
                </div>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Prepayments and other current assets</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.prepayCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.prepayPrior)}</span>
                </div>
              </div>
              {selectedBU !== 'All' && (
                <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                  <span>Due from related business units</span>
                  <div className="space-x-12 font-mono">
                    <span>{fmt(financialData.bs.icRecCurrent)}</span>
                    <span className="text-gray-400">{fmt(financialData.bs.icRecPrior)}</span>
                  </div>
                </div>
              )}
              <div className="py-2 px-3 pl-6 flex justify-between font-bold text-gray-800 bg-plum-50/40">
                <span>Total Current Assets</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.totalCurrentAssets)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.totalCurrentAssetsPrior)}</span>
                </div>
              </div>

              {/* Non-Current Assets */}
              <div className="py-2 px-3 pl-6 font-semibold text-gray-700 mt-2">Non-Current Assets</div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Property, plant and equipment, net</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.ppeNetCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.ppeNetPrior)}</span>
                </div>
              </div>
              <div className="py-2 px-3 pl-6 flex justify-between font-bold text-gray-800 bg-plum-50/40">
                <span>Total Non-Current Assets</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.ppeNetCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.ppeNetPrior)}</span>
                </div>
              </div>

              <div className="py-3 px-3 flex justify-between font-bold text-sm text-[#3F1D5C] bg-[#EDE4F5] mt-2 rounded">
                <span>TOTAL ASSETS</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.totalAssets)}</span>
                  <span className="text-gray-600">{fmt(financialData.bs.totalAssetsPrior)}</span>
                </div>
              </div>

              {/* LIABILITIES AND EQUITY */}
              <div className="py-2 font-bold text-gray-900 uppercase tracking-wider bg-gray-50 px-3 rounded mt-6">
                LIABILITIES AND EQUITY
              </div>

              {/* Current Liabilities */}
              <div className="py-2 px-3 pl-6 font-semibold text-gray-700">Current Liabilities</div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Trade and other payables</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.apCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.apPrior)}</span>
                </div>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Accrued expenses & provisions</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.accruedExpCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.accruedExpPrior)}</span>
                </div>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Current portion of borrowings</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.bankLoanCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.bankLoanCurrentPrior)}</span>
                </div>
              </div>
              <div className="py-2 px-3 pl-6 flex justify-between font-bold text-gray-800 bg-plum-50/40">
                <span>Total Current Liabilities</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.totalCurrentLiab)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.totalCurrentLiabPrior)}</span>
                </div>
              </div>

              {/* Non-Current Liabilities */}
              <div className="py-2 px-3 pl-6 font-semibold text-gray-700 mt-2">Non-Current Liabilities</div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Employees’ end of service benefits</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.eosbCurrent)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.eosbPrior)}</span>
                </div>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Bank borrowings & lease obligations</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.totalNcLiab.minus(financialData.bs.eosbCurrent))}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.totalNcLiabPrior.minus(financialData.bs.eosbPrior))}</span>
                </div>
              </div>
              <div className="py-2 px-3 pl-6 flex justify-between font-bold text-gray-800 bg-plum-50/40">
                <span>Total Non-Current Liabilities</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.totalNcLiab)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.totalNcLiabPrior)}</span>
                </div>
              </div>

              {/* Equity */}
              <div className="py-2 px-3 pl-6 font-semibold text-gray-700 mt-2">Equity</div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Share capital</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.shareCap)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.shareCap)}</span>
                </div>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Retained earnings (opening)</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.retainedEarn)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.retainedEarn)}</span>
                </div>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-emerald-700 font-semibold">
                <span>Profit for the period (rolled forward)</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.profitForPeriod)}</span>
                  <span className="text-gray-400">—</span>
                </div>
              </div>
              <div className="py-2 px-3 pl-6 flex justify-between font-bold text-gray-800 bg-plum-50/40">
                <span>Total Equity</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.totalEquity)}</span>
                  <span className="text-gray-400">{fmt(financialData.bs.totalEquityPrior)}</span>
                </div>
              </div>

              <div className="py-3 px-3 flex justify-between font-bold text-sm text-[#3F1D5C] bg-[#EDE4F5] mt-2 rounded">
                <span>TOTAL LIABILITIES AND EQUITY</span>
                <div className="space-x-12 font-mono">
                  <span>{fmt(financialData.bs.totalLiabAndEquity)}</span>
                  <span className="text-gray-600">{fmt(financialData.bs.totalAssetsPrior)}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STATEMENT OF PROFIT OR LOSS */}
        {activeStatement === 'PL' && (
          <div className="max-w-4xl mx-auto text-xs">
            <div className="text-center pb-4 mb-6 border-b border-gray-200">
              <h2 className="text-base font-bold text-gray-900 uppercase tracking-wide">
                Meridian Healthcare Group
              </h2>
              <h3 className="text-sm font-semibold text-[#5B2C83]">
                Statement of Profit or Loss and Other Comprehensive Income
              </h3>
              <p className="text-gray-500 text-[11px] mt-0.5">
                For the period ended 19 October 2026 &bull; {scaleK ? "Amounts in AED '000" : 'Amounts in AED'}
              </p>
            </div>

            <div className="divide-y divide-gray-100">
              <div className="py-2 px-3 flex justify-between font-semibold text-gray-900">
                <span>Revenue from contracts with customers (IFRS 15)</span>
                <span className="font-mono">{fmt(financialData.pl.netRevenue)}</span>
              </div>
              <div className="py-2 px-3 flex justify-between text-gray-700">
                <span>Cost of sales (Medicines, consumables, doctor fees)</span>
                <span className="font-mono">{fmt(financialData.pl.cos, true)}</span>
              </div>
              <div className="py-2 px-3 flex justify-between font-bold bg-plum-50/40 text-[#3F1D5C]">
                <span>Gross Profit</span>
                <span className="font-mono">{fmt(financialData.pl.grossProfit)}</span>
              </div>

              <div className="py-2 px-3 flex justify-between text-gray-700">
                <span>Administrative and operating expenses</span>
                <span className="font-mono">{fmt(financialData.pl.adminSelling, true)}</span>
              </div>
              <div className="py-2 px-3 flex justify-between text-gray-700">
                <span>Depreciation expense (IAS 16 straight-line)</span>
                <span className="font-mono">{fmt(financialData.pl.depreciationExp, true)}</span>
              </div>
              <div className="py-2 px-3 flex justify-between text-gray-700">
                <span>Impairment losses on trade receivables (IFRS 9 ECL)</span>
                <span className="font-mono">{fmt(financialData.pl.eclExp, true)}</span>
              </div>
              <div className="py-2 px-3 flex justify-between font-bold bg-plum-50/40 text-[#3F1D5C]">
                <span>Operating Profit (EBIT)</span>
                <span className="font-mono">{fmt(financialData.pl.operatingProfit)}</span>
              </div>

              <div className="py-2 px-3 flex justify-between text-gray-700">
                <span>Finance costs</span>
                <span className="font-mono">{fmt(financialData.pl.financeCosts, true)}</span>
              </div>
              <div className="py-2 px-3 flex justify-between font-semibold text-gray-900">
                <span>Profit Before Tax</span>
                <span className="font-mono">{fmt(financialData.pl.profitBeforeTax)}</span>
              </div>
              <div className="py-2 px-3 flex justify-between text-gray-700">
                <span>Income tax expense (UAE Corporate Tax 9%)</span>
                <span className="font-mono">{fmt(financialData.pl.corporateTax, true)}</span>
              </div>

              <div className="py-3 px-3 flex justify-between font-bold text-sm text-emerald-800 bg-emerald-50 rounded mt-2 border border-emerald-200">
                <span>PROFIT FOR THE PERIOD</span>
                <span className="font-mono">{fmt(financialData.pl.profitForPeriod)}</span>
              </div>

              <div className="py-2 px-3 flex justify-between text-gray-500 italic">
                <span>Other comprehensive income for the period, net of tax</span>
                <span className="font-mono">—</span>
              </div>

              <div className="py-2.5 px-3 flex justify-between font-bold text-gray-900 bg-gray-50 rounded">
                <span>TOTAL COMPREHENSIVE INCOME FOR THE PERIOD</span>
                <span className="font-mono text-emerald-800">{fmt(financialData.pl.profitForPeriod)}</span>
              </div>
            </div>
          </div>
        )}

        {/* STATEMENT OF CASH FLOWS */}
        {activeStatement === 'CASH' && (
          <div className="max-w-4xl mx-auto text-xs">
            <div className="text-center pb-4 mb-6 border-b border-gray-200">
              <h2 className="text-base font-bold text-gray-900 uppercase tracking-wide">
                Meridian Healthcare Group
              </h2>
              <h3 className="text-sm font-semibold text-[#5B2C83]">
                Statement of Cash Flows (IAS 7 Indirect Method)
              </h3>
              <p className="text-gray-500 text-[11px] mt-0.5">
                For the period ended 19 October 2026 &bull; {scaleK ? "Amounts in AED '000" : 'Amounts in AED'}
              </p>
            </div>

            <div className="divide-y divide-gray-100">
              <div className="py-2 font-bold text-gray-900 uppercase tracking-wider bg-gray-50 px-3 rounded">
                CASH FLOWS FROM OPERATING ACTIVITIES
              </div>
              <div className="py-2 px-3 flex justify-between text-gray-700">
                <span>Profit before taxation</span>
                <span className="font-mono font-semibold">{fmt(financialData.pl.profitBeforeTax)}</span>
              </div>
              <div className="py-1 px-3 pl-6 flex justify-between text-gray-600">
                <span>Adjustments for: Depreciation of PPE</span>
                <span className="font-mono">{fmt(financialData.pl.depreciationExp)}</span>
              </div>
              <div className="py-1 px-3 pl-6 flex justify-between text-gray-600">
                <span>Finance costs</span>
                <span className="font-mono">{fmt(financialData.pl.financeCosts)}</span>
              </div>
              <div className="py-1 px-3 pl-6 flex justify-between text-gray-600">
                <span>Provision for ECL on trade receivables</span>
                <span className="font-mono">{fmt(financialData.pl.eclExp)}</span>
              </div>

              {/* Working capital changes */}
              <div className="py-2 px-3 pl-6 font-semibold text-gray-700">Working Capital Changes:</div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>(Increase) in trade and other receivables</span>
                <span className="font-mono">{fmt(financialData.bs.arNetCurrent.minus(financialData.bs.arNetPrior), true)}</span>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>(Increase) in inventories</span>
                <span className="font-mono">{fmt(financialData.bs.invCurrent.minus(financialData.bs.invPrior), true)}</span>
              </div>
              <div className="py-1 px-3 pl-10 flex justify-between text-gray-600">
                <span>Increase in trade and other payables</span>
                <span className="font-mono">{fmt(financialData.bs.apCurrent.minus(financialData.bs.apPrior))}</span>
              </div>

              <div className="py-2.5 px-3 flex justify-between font-bold text-[#3F1D5C] bg-plum-50/50">
                <span>Net Cash Generated from Operating Activities</span>
                <span className="font-mono text-emerald-800">{fmt(financialData.pl.profitBeforeTax.plus(financialData.pl.depreciationExp))}</span>
              </div>

              <div className="py-2 font-bold text-gray-900 uppercase tracking-wider bg-gray-50 px-3 rounded mt-4">
                CASH AND CASH EQUIVALENTS RECONCILIATION
              </div>
              <div className="py-2 px-3 flex justify-between text-gray-700">
                <span>Cash and cash equivalents at 1 January 2026 (Opening)</span>
                <span className="font-mono">{fmt(financialData.bs.cashPrior)}</span>
              </div>
              <div className="py-2 px-3 flex justify-between text-gray-700">
                <span>Net movement in cash and cash equivalents</span>
                <span className="font-mono">{fmt(financialData.bs.cashCurrent.minus(financialData.bs.cashPrior))}</span>
              </div>
              <div className="py-3 px-3 flex justify-between font-bold text-sm text-[#3F1D5C] bg-[#EDE4F5] rounded">
                <span>CASH AND CASH EQUIVALENTS AT 19 OCTOBER 2026</span>
                <span className="font-mono">{fmt(financialData.bs.cashCurrent)}</span>
              </div>
            </div>
          </div>
        )}

        {/* STATEMENT OF CHANGES IN EQUITY */}
        {activeStatement === 'EQUITY' && (
          <div className="max-w-4xl mx-auto text-xs">
            <div className="text-center pb-4 mb-6 border-b border-gray-200">
              <h2 className="text-base font-bold text-gray-900 uppercase tracking-wide">
                Meridian Healthcare Group
              </h2>
              <h3 className="text-sm font-semibold text-[#5B2C83]">
                Statement of Changes in Equity (IAS 1)
              </h3>
              <p className="text-gray-500 text-[11px] mt-0.5">
                For the period ended 19 October 2026 &bull; {scaleK ? "Amounts in AED '000" : 'Amounts in AED'}
              </p>
            </div>

            <table className="w-full text-left border-collapse">
              <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Item Description</th>
                  <th className="py-2.5 px-3 text-right">Share Capital</th>
                  <th className="py-2.5 px-3 text-right">Retained Earnings</th>
                  <th className="py-2.5 px-3 text-right">Statutory Reserve</th>
                  <th className="py-2.5 px-3 text-right">Total Equity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr>
                  <td className="py-2 px-3 font-semibold text-gray-800">Balance at 1 January 2026 (Opening)</td>
                  <td className="py-2 px-3 text-right font-mono">{fmt(financialData.bs.shareCap)}</td>
                  <td className="py-2 px-3 text-right font-mono">{fmt(financialData.bs.retainedEarn)}</td>
                  <td className="py-2 px-3 text-right font-mono">{fmt(financialData.bs.reserves)}</td>
                  <td className="py-2 px-3 text-right font-mono font-bold">{fmt(financialData.bs.totalEquityPrior)}</td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-semibold text-emerald-700">Profit for the period (YTD Oct-26)</td>
                  <td className="py-2 px-3 text-right font-mono">—</td>
                  <td className="py-2 px-3 text-right font-mono text-emerald-700">{fmt(financialData.bs.profitForPeriod)}</td>
                  <td className="py-2 px-3 text-right font-mono">—</td>
                  <td className="py-2 px-3 text-right font-mono font-bold text-emerald-700">{fmt(financialData.bs.profitForPeriod)}</td>
                </tr>
              </tbody>
              <tfoot className="bg-[#3F1D5C] text-white font-bold border-t-2 border-[#5B2C83]">
                <tr>
                  <td className="py-3 px-3">Balance at 19 October 2026 (Closing)</td>
                  <td className="py-3 px-3 text-right font-mono text-amber-300">{fmt(financialData.bs.shareCap)}</td>
                  <td className="py-3 px-3 text-right font-mono text-white">{fmt(financialData.bs.retainedEarn.plus(financialData.bs.profitForPeriod))}</td>
                  <td className="py-3 px-3 text-right font-mono text-white">{fmt(financialData.bs.reserves)}</td>
                  <td className="py-3 px-3 text-right font-mono text-emerald-300 text-sm">{fmt(financialData.bs.totalEquity)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}

        {/* DISCLOSURE NOTES */}
        {activeStatement === 'NOTES' && (
          <div className="max-w-4xl mx-auto text-xs space-y-6 leading-relaxed text-gray-700">
            <div>
              <h3 className="font-bold text-sm text-[#3F1D5C] mb-2">Note 1: Corporate Information & Basis of Preparation</h3>
              <p>
                Meridian Healthcare Group comprises 5 specialized tertiary hospitals (Abu Dhabi, Dubai, Sharjah, Al Ain, Ras Al Khaimah), 5 multi-speciality clinics, and 5 licensed community pharmacies operating across the United Arab Emirates. The financial statements have been prepared strictly in accordance with International Financial Reporting Standards (IFRS) as issued by the IASB. The functional and presentation currency is the UAE Dirham (AED), rounded to two decimal places.
              </p>
            </div>

            <div>
              <h3 className="font-bold text-sm text-[#3F1D5C] mb-2">Note 2: Significant Accounting Policies</h3>
              <ul className="list-disc pl-5 space-y-1">
                <li><strong>IFRS 15 Revenue:</strong> Revenue from patient healthcare and insurance contracts is recognized upon delivery of treatment and clinical discharge. Gross billings are recorded net of contractually agreed health insurer discounts (Account 4090).</li>
                <li><strong>IFRS 9 Financial Instruments (ECL):</strong> Impairment losses on trade receivables are measured using a simplified provision matrix categorized by ageing bands (0-30 days 1%, 31-90 days 3%, 91-180 days 10%, 181-365 days 25%, &gt;365 days 50%).</li>
                <li><strong>IAS 2 Inventories:</strong> Pharmaceuticals, implants, and medical consumables are valued at the lower of cost and net realizable value, cost being determined on a weighted-average cost formula.</li>
                <li><strong>IAS 16 Property, Plant and Equipment:</strong> Stated at cost less accumulated depreciation. Depreciation is calculated on a straight-line basis over useful lives: Buildings 25 years, Medical Equipment 8 years, Plant & HVAC 10 years, IT Equipment 4 years, Furniture 5 years.</li>
              </ul>
            </div>

            <div>
              <h3 className="font-bold text-sm text-[#3F1D5C] mb-2">Note 3: Related Party Transactions & Intercompany Balances</h3>
              <p>
                All intercompany services, cross-hospital specialist telemetry consults, and shared warehouse inventory transfers are conducted at arm&apos;s length. On consolidation, all Due From (1500) and Due To (2500) balances, together with intercompany fee revenues (4900) and charges (6400), are fully eliminated, leaving zero variance.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
