import React, { useState } from 'react';
import {
  Scale,
  FileSpreadsheet,
  FileText,
  Presentation,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  BookOpen,
  LayoutList,
  Columns,
  ShieldCheck,
} from 'lucide-react';
import {
  BalanceSheetHeadConfig,
  BalanceSheetSummary,
  EntityDetails,
  ScheduleData,
} from '../types/accounting';

interface BalanceSheetViewProps {
  entity: EntityDetails;
  heads: BalanceSheetHeadConfig[];
  balanceSheet: BalanceSheetSummary;
  schedules: ScheduleData[];
  onSelectSchedule: (scheduleNo: string | number) => void;
  onExportExcel: () => void;
  onExportPDF: () => void;
  onExportPPT?: () => void;
}

export const BalanceSheetView: React.FC<BalanceSheetViewProps> = ({
  entity,
  heads,
  balanceSheet,
  schedules,
  onSelectSchedule,
  onExportExcel,
  onExportPDF,
  onExportPPT,
}) => {
  const [viewFormat, setViewFormat] = useState<'ICAI_VERTICAL' | 'HORIZONTAL'>('ICAI_VERTICAL');

  const formatCur = (val: number) => {
    return val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const getAmount = (code: string) => {
    const s = schedules.find(sched => sched.headConfig.code === code);
    return s ? s.totalAmount : 0;
  };

  const getPrevAmount = (code: string) => {
    const s = schedules.find(sched => sched.headConfig.code === code);
    return s?.previousYearTotal !== undefined ? s.previousYearTotal : 0;
  };

  // Grouping as per ICAI Technical Guide for Non-Corporate Entities
  const ownersHeads = heads.filter(h => h.active && h.nature === 'Liability' && (h.icaiMajorCategory === 'OWNERS_FUNDS' || h.code === 'L01' || h.code === 'L02'));
  const nonCurLiabHeads = heads.filter(h => h.active && h.nature === 'Liability' && (h.icaiMajorCategory === 'NON_CURRENT_LIABILITIES' || h.code === 'L03' || h.code === 'L04'));
  const curLiabHeads = heads.filter(h => h.active && h.nature === 'Liability' && (h.icaiMajorCategory === 'CURRENT_LIABILITIES' || h.code === 'L05' || h.code === 'L06' || h.code === 'L07'));

  const nonCurAssetHeads = heads.filter(h => h.active && h.nature === 'Asset' && (h.icaiMajorCategory === 'NON_CURRENT_ASSETS' || h.code === 'A01' || h.code === 'A02'));
  const curAssetHeads = heads.filter(h => h.active && h.nature === 'Asset' && (h.icaiMajorCategory === 'CURRENT_ASSETS' || ['A03', 'A04', 'A05', 'A06', 'A07'].includes(h.code)));

  const subTotalOwners = ownersHeads.reduce((acc, h) => acc + getAmount(h.code), 0);
  const subTotalNonCurLiab = nonCurLiabHeads.reduce((acc, h) => acc + getAmount(h.code), 0);
  const subTotalCurLiab = curLiabHeads.reduce((acc, h) => acc + getAmount(h.code), 0);

  const subTotalNonCurAssets = nonCurAssetHeads.reduce((acc, h) => acc + getAmount(h.code), 0);
  const subTotalCurAssets = curAssetHeads.reduce((acc, h) => acc + getAmount(h.code), 0);

  // Previous Year Sub-totals
  const prevSubTotalOwners = ownersHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0);
  const prevSubTotalNonCurLiab = nonCurLiabHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0);
  const prevSubTotalCurLiab = curLiabHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0);

  const prevSubTotalNonCurAssets = nonCurAssetHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0);
  const prevSubTotalCurAssets = curAssetHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0);

  const prevTotalLiab = balanceSheet.totalPreviousYearLiabilities ?? (prevSubTotalOwners + prevSubTotalNonCurLiab + prevSubTotalCurLiab);
  const prevTotalAssets = balanceSheet.totalPreviousYearAssets ?? (prevSubTotalNonCurAssets + prevSubTotalCurAssets);
  const isPyBalanced = balanceSheet.isPreviousYearBalanced ?? (Math.abs(prevTotalAssets - prevTotalLiab) < 0.01);

  // Horizontal T-format heads
  const liabHeads = heads.filter(h => h.active && h.nature === 'Liability').sort((a, b) => a.displayOrder - b.displayOrder);
  const assetHeads = heads.filter(h => h.active && h.nature === 'Asset').sort((a, b) => a.displayOrder - b.displayOrder);
  const maxRows = Math.max(liabHeads.length, assetHeads.length);

  return (
    <div className="space-y-4" id="balance-sheet-container">
      {/* Header Banner */}
      <div className="bg-[#141414] text-[#E4E3E0] p-4 border border-[#141414] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Scale className="w-4 h-4 text-[#A3A29E]" />
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-white">
              Sheet 5: Non-Corporate Entity Balance Sheet
            </h2>
            <span className="px-2 py-0.5 bg-[#282828] text-[#86efac] border border-[#86efac]/40 text-[10px] font-mono font-bold uppercase">
              ICAI Format Compliant
            </span>
          </div>
          <p className="text-[11.5px] text-[#A3A29E] mt-1">
            As on <strong className="text-white">{entity.balanceSheetDate}</strong> | Prepared as per the Technical Guide on Financial Statements of Non-Corporate Entities issued by ICAI.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Format Switcher */}
          <div className="flex items-center border border-[#141414]/40 bg-[#222222] p-0.5">
            <button
              onClick={() => setViewFormat('ICAI_VERTICAL')}
              className={`inline-flex items-center px-2.5 py-1 text-[11px] font-mono transition ${
                viewFormat === 'ICAI_VERTICAL'
                  ? 'bg-white text-[#141414] font-bold shadow-xs'
                  : 'text-[#A3A29E] hover:text-white'
              }`}
            >
              <LayoutList className="w-3.5 h-3.5 mr-1" />
              ICAI VERTICAL FORMAT
            </button>
            <button
              onClick={() => setViewFormat('HORIZONTAL')}
              className={`inline-flex items-center px-2.5 py-1 text-[11px] font-mono transition ${
                viewFormat === 'HORIZONTAL'
                  ? 'bg-white text-[#141414] font-bold shadow-xs'
                  : 'text-[#A3A29E] hover:text-white'
              }`}
            >
              <Columns className="w-3.5 h-3.5 mr-1" />
              TRADITIONAL T-FORMAT
            </button>
          </div>

          {onExportPPT && (
            <button
              onClick={onExportPPT}
              className="inline-flex items-center px-2.5 py-1 bg-[#2b2416] hover:bg-[#3d321d] text-[#fcd34d] text-[11px] font-mono border border-[#f59e0b]/40 transition"
              title="View & Download 5-Slide Project Presentation Deck (.pptx)"
              id="btn-bs-export-pptx"
            >
              <Presentation className="w-3.5 h-3.5 mr-1 text-[#f59e0b]" />
              PPT DECK (5 SLIDES)
            </button>
          )}
          <button
            onClick={onExportPDF}
            className="inline-flex items-center px-3 py-1 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
          >
            <FileText className="w-3.5 h-3.5 mr-1 text-[#f87171]" />
            PRINT / PDF
          </button>
          <button
            onClick={onExportExcel}
            className="inline-flex items-center px-3.5 py-1 bg-[#15803d] hover:bg-[#16a34a] text-white text-[11px] font-mono font-bold border border-[#15803d] transition shadow-xs"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 mr-1" />
            EXPORT EXCEL (.XLSX)
          </button>
        </div>
      </div>

      {/* Main Balance Sheet Statement Table */}
      <div className="bg-[#F5F4F0] border border-[#141414]/20 overflow-hidden" id="table-main-balance-sheet">
        {/* Title Header */}
        <div className="bg-[#141414] text-white p-4 text-center border-b border-[#141414]">
          <h1 className="text-base font-bold uppercase tracking-wider font-mono">{entity.name}</h1>
          <p className="text-xs text-[#A3A29E] font-mono mt-0.5">
            BALANCE SHEET AS AT {entity.balanceSheetDate.toUpperCase()}
          </p>
          <p className="text-[11px] text-[#A3A29E] font-mono mt-0.5">
            [Form of Balance Sheet for Non-Corporate Entities ({entity.entityType})]
          </p>
          <p className="text-[10.5px] text-[#737373] font-mono mt-0.5">
            (Amount in Indian Rupees - ₹)
          </p>
        </div>

        {viewFormat === 'ICAI_VERTICAL' ? (
          /* ============================================================ */
          /* ICAI PRESCRIBED VERTICAL FORMAT (TECHNICAL GUIDE COMPLIANT)   */
          /* ============================================================ */
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider border-b border-[#141414]">
                <tr>
                  <th className="py-2.5 px-4 text-left w-1/2 border-r border-[#141414]/20">
                    PARTICULARS
                  </th>
                  <th className="py-2.5 px-2 text-center w-20 border-r border-[#141414]/20">
                    NOTE / SCH. NO.
                  </th>
                  <th className="py-2.5 px-4 text-right w-1/4 border-r border-[#141414]/20">
                    FIGURES AS AT {entity.balanceSheetDate.toUpperCase()} (₹)
                  </th>
                  <th className="py-2.5 px-4 text-right w-1/4">
                    FIGURES AS AT {entity.previousYearDate?.toUpperCase() || '31-03-2024'} (₹)
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-[#141414]/15 bg-white font-sans">
                {/* ------------------------------------------- */}
                {/* I. EQUITY AND LIABILITIES                   */}
                {/* ------------------------------------------- */}
                <tr className="bg-[#ECEAE5]/80 font-mono font-bold text-[#141414] border-t border-b border-[#141414]/30">
                  <td colSpan={4} className="py-2 px-4 text-xs uppercase tracking-wider">
                    I. EQUITY AND LIABILITIES
                  </td>
                </tr>

                {/* (1) Owners' Funds / Partners' Funds */}
                <tr className="bg-[#F5F4F0] font-semibold text-[#141414]">
                  <td colSpan={4} className="py-1.5 px-6 font-mono text-[11.5px]">
                    (1) Owners' Funds / Partners' Funds
                  </td>
                </tr>
                {ownersHeads.map(h => (
                  <tr key={h.id} className="hover:bg-[#ECEAE5]/40 transition-colors">
                    <td className="py-1.5 px-10 text-[#141414]">
                      {h.subHead}
                    </td>
                    <td className="py-1.5 px-2 text-center border-r border-l border-[#141414]/10">
                      <button
                        onClick={() => onSelectSchedule(h.scheduleNo)}
                        className="inline-flex items-center px-1.5 py-0.2 text-[10px] font-mono font-bold bg-[#ECEAE5] hover:bg-[#141414] hover:text-white border border-[#141414]/30 text-[#141414] transition"
                        title={`View Schedule ${h.scheduleNo} Details`}
                      >
                        {h.scheduleNo}
                        <ExternalLink className="w-2 h-2 ml-0.5" />
                      </button>
                    </td>
                    <td className="py-1.5 px-4 text-right font-mono text-[#141414] border-r border-[#141414]/10">
                      ₹{formatCur(getAmount(h.code))}
                    </td>
                    <td className="py-1.5 px-4 text-right font-mono text-[#5E5E5E]">
                      ₹{formatCur(getPrevAmount(h.code))}
                    </td>
                  </tr>
                ))}
                <tr className="bg-[#ECEAE5]/40 font-mono font-semibold text-[11px] text-[#141414] italic">
                  <td className="py-1 px-10">Sub-total: Owners' Funds</td>
                  <td className="py-1 px-2 text-center border-r border-l border-[#141414]/10">-</td>
                  <td className="py-1 px-4 text-right border-r border-[#141414]/10 font-bold">
                    ₹{formatCur(subTotalOwners)}
                  </td>
                  <td className="py-1 px-4 text-right text-[#5E5E5E]">₹{formatCur(prevSubTotalOwners)}</td>
                </tr>

                {/* (2) Non-Current Liabilities */}
                <tr className="bg-[#F5F4F0] font-semibold text-[#141414]">
                  <td colSpan={4} className="py-1.5 px-6 font-mono text-[11.5px]">
                    (2) Non-Current Liabilities
                  </td>
                </tr>
                {nonCurLiabHeads.map(h => (
                  <tr key={h.id} className="hover:bg-[#ECEAE5]/40 transition-colors">
                    <td className="py-1.5 px-10 text-[#141414]">
                      {h.subHead}
                    </td>
                    <td className="py-1.5 px-2 text-center border-r border-l border-[#141414]/10">
                      <button
                        onClick={() => onSelectSchedule(h.scheduleNo)}
                        className="inline-flex items-center px-1.5 py-0.2 text-[10px] font-mono font-bold bg-[#ECEAE5] hover:bg-[#141414] hover:text-white border border-[#141414]/30 text-[#141414] transition"
                        title={`View Schedule ${h.scheduleNo} Details`}
                      >
                        {h.scheduleNo}
                        <ExternalLink className="w-2 h-2 ml-0.5" />
                      </button>
                    </td>
                    <td className="py-1.5 px-4 text-right font-mono text-[#141414] border-r border-[#141414]/10">
                      ₹{formatCur(getAmount(h.code))}
                    </td>
                    <td className="py-1.5 px-4 text-right font-mono text-[#5E5E5E]">
                      ₹{formatCur(getPrevAmount(h.code))}
                    </td>
                  </tr>
                ))}
                <tr className="bg-[#ECEAE5]/40 font-mono font-semibold text-[11px] text-[#141414] italic">
                  <td className="py-1 px-10">Sub-total: Non-Current Liabilities</td>
                  <td className="py-1 px-2 text-center border-r border-l border-[#141414]/10">-</td>
                  <td className="py-1 px-4 text-right border-r border-[#141414]/10 font-bold">
                    ₹{formatCur(subTotalNonCurLiab)}
                  </td>
                  <td className="py-1 px-4 text-right text-[#5E5E5E]">₹{formatCur(prevSubTotalNonCurLiab)}</td>
                </tr>

                {/* (3) Current Liabilities */}
                <tr className="bg-[#F5F4F0] font-semibold text-[#141414]">
                  <td colSpan={4} className="py-1.5 px-6 font-mono text-[11.5px]">
                    (3) Current Liabilities
                  </td>
                </tr>
                {curLiabHeads.map(h => {
                  if (h.code === 'L05') {
                    // Trade Payables with MSME breakdown as per ICAI guidelines
                    return (
                      <React.Fragment key={h.id}>
                        <tr className="hover:bg-[#ECEAE5]/40 transition-colors">
                          <td className="py-1.5 px-10 text-[#141414] font-medium">
                            Trade Payables:
                          </td>
                          <td className="py-1.5 px-2 text-center border-r border-l border-[#141414]/10">
                            <button
                              onClick={() => onSelectSchedule(h.scheduleNo)}
                              className="inline-flex items-center px-1.5 py-0.2 text-[10px] font-mono font-bold bg-[#ECEAE5] hover:bg-[#141414] hover:text-white border border-[#141414]/30 text-[#141414] transition"
                              title={`View Schedule ${h.scheduleNo} Details`}
                            >
                              {h.scheduleNo}
                              <ExternalLink className="w-2 h-2 ml-0.5" />
                            </button>
                          </td>
                          <td className="py-1.5 px-4 text-right font-mono text-[#141414] border-r border-[#141414]/10">
                            ₹{formatCur(getAmount(h.code))}
                          </td>
                          <td className="py-1.5 px-4 text-right font-mono text-[#5E5E5E]">
                            ₹{formatCur(getPrevAmount(h.code))}
                          </td>
                        </tr>
                        <tr className="text-[11px] text-[#5E5E5E]">
                          <td className="py-1 px-14">
                            (A) Total outstanding dues of micro enterprises & small enterprises (MSME)
                          </td>
                          <td className="py-1 px-2 text-center border-r border-l border-[#141414]/10">-</td>
                          <td className="py-1 px-4 text-right font-mono border-r border-[#141414]/10">₹0.00</td>
                          <td className="py-1 px-4 text-right font-mono">₹0.00</td>
                        </tr>
                        <tr className="text-[11px] text-[#5E5E5E]">
                          <td className="py-1 px-14">
                            (B) Total outstanding dues of creditors other than micro & small enterprises
                          </td>
                          <td className="py-1 px-2 text-center border-r border-l border-[#141414]/10">-</td>
                          <td className="py-1 px-4 text-right font-mono border-r border-[#141414]/10">
                            ₹{formatCur(getAmount(h.code))}
                          </td>
                          <td className="py-1 px-4 text-right font-mono">₹0.00</td>
                        </tr>
                      </React.Fragment>
                    );
                  }
                  return (
                    <tr key={h.id} className="hover:bg-[#ECEAE5]/40 transition-colors">
                      <td className="py-1.5 px-10 text-[#141414]">
                        {h.subHead}
                      </td>
                      <td className="py-1.5 px-2 text-center border-r border-l border-[#141414]/10">
                        <button
                          onClick={() => onSelectSchedule(h.scheduleNo)}
                          className="inline-flex items-center px-1.5 py-0.2 text-[10px] font-mono font-bold bg-[#ECEAE5] hover:bg-[#141414] hover:text-white border border-[#141414]/30 text-[#141414] transition"
                          title={`View Schedule ${h.scheduleNo} Details`}
                        >
                          {h.scheduleNo}
                          <ExternalLink className="w-2 h-2 ml-0.5" />
                        </button>
                      </td>
                      <td className="py-1.5 px-4 text-right font-mono text-[#141414] border-r border-[#141414]/10">
                        ₹{formatCur(getAmount(h.code))}
                      </td>
                      <td className="py-1.5 px-4 text-right font-mono text-[#5E5E5E]">
                        ₹{formatCur(getPrevAmount(h.code))}
                      </td>
                    </tr>
                  );
                })}
                <tr className="bg-[#ECEAE5]/40 font-mono font-semibold text-[11px] text-[#141414] italic">
                  <td className="py-1 px-10">Sub-total: Current Liabilities</td>
                  <td className="py-1 px-2 text-center border-r border-l border-[#141414]/10">-</td>
                  <td className="py-1 px-4 text-right border-r border-[#141414]/10 font-bold">
                    ₹{formatCur(subTotalCurLiab)}
                  </td>
                  <td className="py-1 px-4 text-right text-[#5E5E5E]">₹{formatCur(prevSubTotalCurLiab)}</td>
                </tr>

                {/* Total Equity & Liabilities */}
                <tr className="bg-[#ECEAE5] font-bold font-mono text-[#141414] border-t-2 border-b-2 border-[#141414]">
                  <td className="py-2.5 px-4 text-xs uppercase tracking-wider">
                    TOTAL EQUITY AND LIABILITIES
                  </td>
                  <td className="py-2.5 px-2 text-center border-r border-l border-[#141414]/20">-</td>
                  <td className="py-2.5 px-4 text-right text-sm border-r border-[#141414]/20">
                    ₹{formatCur(balanceSheet.totalLiabilities)}
                  </td>
                  <td className="py-2.5 px-4 text-right text-sm text-[#5E5E5E] font-bold">
                    ₹{formatCur(prevTotalLiab)}
                  </td>
                </tr>

                {/* ------------------------------------------- */}
                {/* II. ASSETS                                  */}
                {/* ------------------------------------------- */}
                <tr className="bg-[#ECEAE5]/80 font-mono font-bold text-[#141414] border-t-2 border-b border-[#141414]/30">
                  <td colSpan={4} className="py-2 px-4 text-xs uppercase tracking-wider">
                    II. ASSETS
                  </td>
                </tr>

                {/* (1) Non-Current Assets */}
                <tr className="bg-[#F5F4F0] font-semibold text-[#141414]">
                  <td colSpan={4} className="py-1.5 px-6 font-mono text-[11.5px]">
                    (1) Non-Current Assets
                  </td>
                </tr>
                {nonCurAssetHeads.map(h => (
                  <tr key={h.id} className="hover:bg-[#ECEAE5]/40 transition-colors">
                    <td className="py-1.5 px-10 text-[#141414]">
                      {h.subHead}
                    </td>
                    <td className="py-1.5 px-2 text-center border-r border-l border-[#141414]/10">
                      <button
                        onClick={() => onSelectSchedule(h.scheduleNo)}
                        className="inline-flex items-center px-1.5 py-0.2 text-[10px] font-mono font-bold bg-[#ECEAE5] hover:bg-[#141414] hover:text-white border border-[#141414]/30 text-[#141414] transition"
                        title={`View Schedule ${h.scheduleNo} Details`}
                      >
                        {h.scheduleNo}
                        <ExternalLink className="w-2 h-2 ml-0.5" />
                      </button>
                    </td>
                    <td className="py-1.5 px-4 text-right font-mono text-[#141414] border-r border-[#141414]/10">
                      ₹{formatCur(getAmount(h.code))}
                    </td>
                    <td className="py-1.5 px-4 text-right font-mono text-[#5E5E5E]">
                      ₹{formatCur(getPrevAmount(h.code))}
                    </td>
                  </tr>
                ))}
                <tr className="bg-[#ECEAE5]/40 font-mono font-semibold text-[11px] text-[#141414] italic">
                  <td className="py-1 px-10">Sub-total: Non-Current Assets</td>
                  <td className="py-1 px-2 text-center border-r border-l border-[#141414]/10">-</td>
                  <td className="py-1 px-4 text-right border-r border-[#141414]/10 font-bold">
                    ₹{formatCur(subTotalNonCurAssets)}
                  </td>
                  <td className="py-1 px-4 text-right text-[#5E5E5E]">₹{formatCur(prevSubTotalNonCurAssets)}</td>
                </tr>

                {/* (2) Current Assets */}
                <tr className="bg-[#F5F4F0] font-semibold text-[#141414]">
                  <td colSpan={4} className="py-1.5 px-6 font-mono text-[11.5px]">
                    (2) Current Assets
                  </td>
                </tr>
                {curAssetHeads.map(h => (
                  <tr key={h.id} className="hover:bg-[#ECEAE5]/40 transition-colors">
                    <td className="py-1.5 px-10 text-[#141414]">
                      {h.subHead}
                    </td>
                    <td className="py-1.5 px-2 text-center border-r border-l border-[#141414]/10">
                      <button
                        onClick={() => onSelectSchedule(h.scheduleNo)}
                        className="inline-flex items-center px-1.5 py-0.2 text-[10px] font-mono font-bold bg-[#ECEAE5] hover:bg-[#141414] hover:text-white border border-[#141414]/30 text-[#141414] transition"
                        title={`View Schedule ${h.scheduleNo} Details`}
                      >
                        {h.scheduleNo}
                        <ExternalLink className="w-2 h-2 ml-0.5" />
                      </button>
                    </td>
                    <td className="py-1.5 px-4 text-right font-mono text-[#141414] border-r border-[#141414]/10">
                      ₹{formatCur(getAmount(h.code))}
                    </td>
                    <td className="py-1.5 px-4 text-right font-mono text-[#5E5E5E]">
                      ₹{formatCur(getPrevAmount(h.code))}
                    </td>
                  </tr>
                ))}
                <tr className="bg-[#ECEAE5]/40 font-mono font-semibold text-[11px] text-[#141414] italic">
                  <td className="py-1 px-10">Sub-total: Current Assets</td>
                  <td className="py-1 px-2 text-center border-r border-l border-[#141414]/10">-</td>
                  <td className="py-1 px-4 text-right border-r border-[#141414]/10 font-bold">
                    ₹{formatCur(subTotalCurAssets)}
                  </td>
                  <td className="py-1 px-4 text-right text-[#5E5E5E]">₹{formatCur(prevSubTotalCurAssets)}</td>
                </tr>

                {/* Total Assets */}
                <tr className="bg-[#ECEAE5] font-bold font-mono text-[#141414] border-t-2 border-b-4 border-double border-[#141414]">
                  <td className="py-2.5 px-4 text-xs uppercase tracking-wider">
                    TOTAL ASSETS
                  </td>
                  <td className="py-2.5 px-2 text-center border-r border-l border-[#141414]/20">-</td>
                  <td className="py-2.5 px-4 text-right text-sm border-r border-[#141414]/20">
                    ₹{formatCur(balanceSheet.totalAssets)}
                  </td>
                  <td className="py-2.5 px-4 text-right text-sm text-[#5E5E5E] font-bold">
                    ₹{formatCur(prevTotalAssets)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : (
          /* ============================================================ */
          /* TRADITIONAL HORIZONTAL T-FORMAT                              */
          /* ============================================================ */
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider border-b border-[#141414]">
                <tr>
                  <th className="py-2 px-3 text-left w-2/5 border-r border-[#141414]/20">CAPITAL & LIABILITIES</th>
                  <th className="py-2 px-1 text-center w-12 border-r border-[#141414]/20">SCH.</th>
                  <th className="py-2 px-3 text-right w-1/5 border-r border-[#141414]">
                    AMOUNT (₹)
                  </th>
                  <th className="py-2 px-3 text-left w-2/5 border-r border-[#141414]/20">ASSETS</th>
                  <th className="py-2 px-1 text-center w-12 border-r border-[#141414]/20">SCH.</th>
                  <th className="py-2 px-3 text-right w-1/5">
                    AMOUNT (₹)
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-[#141414]/15 bg-white">
                {Array.from({ length: maxRows }).map((_, idx) => {
                  const lHead = liabHeads[idx];
                  const aHead = assetHeads[idx];

                  const lAmount = lHead ? getAmount(lHead.code) : 0;
                  const aAmount = aHead ? getAmount(aHead.code) : 0;

                  return (
                    <tr key={idx} className="hover:bg-[#ECEAE5]/60 transition-colors">
                      <td className="py-2 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                        {lHead ? lHead.subHead : ''}
                      </td>
                      <td className="py-2 px-1 text-center border-r border-[#141414]/10">
                        {lHead && (
                          <button
                            onClick={() => onSelectSchedule(lHead.scheduleNo)}
                            className="inline-flex items-center px-1.5 py-0.2 text-[10px] font-mono font-bold bg-[#ECEAE5] hover:bg-[#141414] hover:text-white border border-[#141414]/30 text-[#141414] transition"
                            title={`View Schedule ${lHead.scheduleNo} Details`}
                          >
                            {lHead.scheduleNo}
                            <ExternalLink className="w-2 h-2 ml-0.5" />
                          </button>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right font-mono font-bold text-[#141414] border-r border-[#141414]">
                        {lHead ? `₹${formatCur(lAmount)}` : ''}
                      </td>

                      <td className="py-2 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                        {aHead ? aHead.subHead : ''}
                      </td>
                      <td className="py-2 px-1 text-center border-r border-[#141414]/10">
                        {aHead && (
                          <button
                            onClick={() => onSelectSchedule(aHead.scheduleNo)}
                            className="inline-flex items-center px-1.5 py-0.2 text-[10px] font-mono font-bold bg-[#ECEAE5] hover:bg-[#141414] hover:text-white border border-[#141414]/30 text-[#141414] transition"
                            title={`View Schedule ${aHead.scheduleNo} Details`}
                          >
                            {aHead.scheduleNo}
                            <ExternalLink className="w-2 h-2 ml-0.5" />
                          </button>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right font-mono font-bold text-[#141414]">
                        {aHead ? `₹${formatCur(aAmount)}` : ''}
                      </td>
                    </tr>
                  );
                })}
              </tbody>

              <tfoot className="bg-[#ECEAE5] font-bold font-mono text-[#141414] border-t-2 border-b-4 border-double border-[#141414]">
                <tr>
                  <td colSpan={2} className="py-2.5 px-3 text-left text-xs uppercase tracking-wider border-r border-[#141414]/20">
                    TOTAL LIABILITIES:
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-sm border-r border-[#141414]">
                    ₹{formatCur(balanceSheet.totalLiabilities)}
                  </td>
                  <td colSpan={2} className="py-2.5 px-3 text-left text-xs uppercase tracking-wider border-r border-[#141414]/20">
                    TOTAL ASSETS:
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-sm">
                    ₹{formatCur(balanceSheet.totalAssets)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}

        {/* Audit Difference Strip */}
        <div className="p-3 bg-[#ECEAE5] border-t border-[#141414]/20 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-bold font-mono text-[#141414] text-[11px] uppercase">Audit Verification:</span>
            {balanceSheet.isBalanced ? (
              <span className="inline-flex items-center px-2 py-0.5 bg-[#dcfce7] text-[#166534] border border-[#86efac] font-bold font-mono text-[10.5px]">
                <CheckCircle2 className="w-3 h-3 mr-1" /> CY BALANCED (Diff: ₹0.00) ✓
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 bg-[#fef3c7] text-[#92400e] border border-[#fde68a] font-bold font-mono text-[10.5px]">
                <AlertTriangle className="w-3 h-3 mr-1" /> CY UNBALANCED (Diff: ₹{formatCur(Math.abs(balanceSheet.difference))})
              </span>
            )}

            {prevTotalAssets > 0 || prevTotalLiab > 0 ? (
              isPyBalanced ? (
                <span className="inline-flex items-center px-2 py-0.5 bg-[#dcfce7] text-[#166534] border border-[#86efac] font-bold font-mono text-[10.5px]">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> PY BALANCED (Diff: ₹0.00) ✓
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 bg-[#fef3c7] text-[#92400e] border border-[#fde68a] font-bold font-mono text-[10.5px]">
                  <AlertTriangle className="w-3 h-3 mr-1" /> PY UNBALANCED (Diff: ₹{formatCur(Math.abs(prevTotalAssets - prevTotalLiab))})
                </span>
              )
            ) : null}
          </div>

          <span className="text-[10.5px] font-mono text-[#5E5E5E]">
            CY: ₹{formatCur(balanceSheet.totalAssets)} vs ₹{formatCur(balanceSheet.totalLiabilities)}
            {prevTotalAssets > 0 && ` | PY: ₹${formatCur(prevTotalAssets)} vs ₹${formatCur(prevTotalLiab)}`}
          </span>
        </div>

        {/* Footnote on Schedules & Accounting Policies */}
        <div className="p-3 bg-[#F5F4F0] border-t border-[#141414]/10 text-center font-mono text-[11px] text-[#5E5E5E] italic">
          The accompanying Schedules 1 to 14 and Significant Accounting Policies form an integral part of these Financial Statements.
        </div>

        {/* Formal Statutory Signature Box */}
        <div className="p-6 bg-white border-t border-[#141414]/20 grid grid-cols-1 md:grid-cols-2 gap-8 text-xs text-[#141414]">
          <div className="space-y-2 font-mono">
            <p className="font-bold text-[11px] uppercase">For and on behalf of:</p>
            <p className="font-bold text-xs uppercase">{entity.name}</p>
            <p className="text-[11px] text-[#5E5E5E]">({entity.entityType})</p>
            <div className="pt-10 border-b border-[#141414] w-56"></div>
            <p className="font-bold text-xs">{entity.proprietorOrPartnerNames?.[0] || 'Rajesh K. Sharma (Proprietor)'}</p>
            <p className="text-[11px] text-[#5E5E5E]">Proprietor / Authorized Partner</p>
            <p className="text-[11px] text-[#5E5E5E]">Place: {entity.placeOfSigning || 'Navi Mumbai'}</p>
            <p className="text-[11px] text-[#5E5E5E]">Date: {entity.dateOfSigning || entity.balanceSheetDate}</p>
          </div>

          <div className="space-y-2 md:text-right font-mono">
            <p className="font-bold text-[11px] uppercase">In terms of our audit report of even date attached:</p>
            <p className="font-bold text-xs uppercase">For {entity.auditorName || 'CA Priyanka Garg & Associates'}</p>
            <p className="text-[11px] text-[#5E5E5E]">Chartered Accountants | FRN: {entity.firmRegistrationNo || '124982W'}</p>
            <div className="pt-10 border-b border-[#141414] w-56 ml-auto"></div>
            <p className="font-bold text-xs">Partner / Proprietor</p>
            <p className="text-[11px] text-[#5E5E5E]">Membership No: {entity.membershipNumber || '512948'}</p>
            <p className="text-[11px] text-[#166534] font-bold">UDIN: {entity.udin || '25512948BGXYZW1234'}</p>
            <p className="text-[11px] text-[#5E5E5E]">Place: {entity.placeOfSigning || 'Navi Mumbai'} | Date: {entity.dateOfSigning || entity.balanceSheetDate}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

