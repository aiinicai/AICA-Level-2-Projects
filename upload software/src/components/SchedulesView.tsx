import React, { useState } from 'react';
import {
  ListOrdered,
  Layers,
  Search,
  CheckCircle,
  FileSpreadsheet,
  FileText,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Plus,
} from 'lucide-react';
import {
  BalanceSheetHeadConfig,
  EntityDetails,
  PLStatement,
  ScheduleData,
} from '../types/accounting';

interface SchedulesViewProps {
  entity: EntityDetails;
  heads: BalanceSheetHeadConfig[];
  schedules: ScheduleData[];
  plStatement: PLStatement;
  selectedScheduleNo?: string | number;
  onSelectScheduleNo: (no: string | number) => void;
  onExportPDF?: () => void;
  onExportExcel?: () => void;
}

export const SchedulesView: React.FC<SchedulesViewProps> = ({
  entity,
  heads,
  schedules,
  plStatement,
  selectedScheduleNo,
  onSelectScheduleNo,
  onExportPDF,
  onExportExcel,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const activeHeads = heads
    .filter(h => h.active)
    .sort((a, b) => Number(a.scheduleNo) - Number(b.scheduleNo));
  const currentScheduleNo = selectedScheduleNo || activeHeads[0]?.scheduleNo || 1;
  const currentHead = activeHeads.find(h => String(h.scheduleNo) === String(currentScheduleNo)) || activeHeads[0];
  const currentScheduleData = schedules.find(s => s.headConfig.code === currentHead?.code);

  const formatCur = (val: number) => {
    return val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="space-y-4" id="schedules-view-container">
      {/* Header Banner */}
      <div className="bg-[#141414] text-[#E4E3E0] p-4 border border-[#141414] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <ListOrdered className="w-4 h-4 text-[#A3A29E]" />
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-white">Sheet 6: Schedules Annexed to Balance Sheet</h2>
          </div>
          <p className="text-[11.5px] text-[#A3A29E] mt-1">
            Every schedule acts as an individual sub-ledger worksheet. In the exported Excel workbook, <strong>each schedule generates as a dedicated separate worksheet</strong>.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {onExportPDF && (
            <button
              onClick={onExportPDF}
              className="inline-flex items-center px-2.5 py-1 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
              title="Export complete financial statements with all schedules in PDF"
            >
              <FileText className="w-3 h-3 mr-1 text-[#f87171]" />
              EXPORT PDF
            </button>
          )}
          {onExportExcel && (
            <button
              onClick={onExportExcel}
              className="inline-flex items-center px-2.5 py-1 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
              title="Export complete multi-sheet Excel workbook"
            >
              <FileSpreadsheet className="w-3 h-3 mr-1 text-[#86efac]" />
              EXPORT EXCEL
            </button>
          )}
          <div className="text-xs font-mono text-[#A3A29E] pl-2 border-l border-white/10">
            ACTIVE SCHEDULES: <strong className="text-white">{activeHeads.length}</strong>
          </div>
        </div>
      </div>

      {/* Main Schedule Workspace: Sidebar + Detail Table */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 items-start">
        
        {/* Left Schedule Selector List */}
        <div className="bg-[#F5F4F0] border border-[#141414]/20 overflow-hidden lg:sticky lg:top-36">
          <div className="p-2.5 bg-[#ECEAE5] border-b border-[#141414]/20 font-bold font-mono text-[11px] uppercase text-[#141414] flex items-center justify-between">
            <span>Schedules Index</span>
            <span className="text-[10px] text-[#5E5E5E] font-normal">[SELECT]</span>
          </div>

          <div className="divide-y divide-[#141414]/10 max-h-[580px] overflow-y-auto bg-white">
            {activeHeads.map(head => {
              const sched = schedules.find(s => s.headConfig.code === head.code);
              const isSelected = String(head.scheduleNo) === String(currentScheduleNo);
              const ledgerCount = sched ? sched.ledgers.length : 0;

              return (
                <button
                  key={head.id}
                  onClick={() => onSelectScheduleNo(head.scheduleNo)}
                  className={`w-full text-left p-2.5 text-xs transition-colors flex items-center justify-between ${
                    isSelected
                      ? 'bg-[#141414] text-[#E4E3E0] font-bold'
                      : 'text-[#141414] hover:bg-[#ECEAE5]'
                  }`}
                  id={`btn-sched-${head.scheduleNo}`}
                >
                  <div className="truncate pr-2">
                    <div className="flex items-center space-x-1.5">
                      <span className={`text-[9.5px] px-1 py-0.2 font-mono font-bold border ${
                        isSelected ? 'bg-white/20 text-white border-white/30' : 'bg-[#ECEAE5] text-[#141414] border-[#141414]/20'
                      }`}>
                        SCH {head.scheduleNo}
                      </span>
                      <span className="truncate">{head.subHead}</span>
                    </div>
                    <div className={`text-[10px] mt-0.5 font-mono ${isSelected ? 'text-[#A3A29E]' : 'text-[#5E5E5E]'}`}>
                      {head.nature} • {ledgerCount} ledgers
                    </div>
                  </div>

                  <span className={`font-mono text-xs shrink-0 font-bold ${isSelected ? 'text-[#86efac]' : 'text-[#141414]'}`}>
                    ₹{formatCur(sched?.totalAmount || 0)}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Schedule Detail Worksheet */}
        <div className="lg:col-span-3 space-y-4">
          {currentHead && (
            <div className="bg-[#F5F4F0] border border-[#141414]/20 overflow-hidden">
              
              {/* Schedule Title Header */}
              <div className="bg-[#141414] text-white p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#141414]">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="bg-[#E4E3E0] text-[#141414] text-[10.5px] font-bold font-mono px-1.5 py-0.2">
                      SCHEDULE {currentHead.scheduleNo}
                    </span>
                    <h3 className="font-bold text-sm tracking-wide font-mono">{currentHead.subHead.toUpperCase()}</h3>
                  </div>
                  <p className="text-[11px] text-[#A3A29E] font-mono mt-0.5">
                    Annexed to and forming part of Balance Sheet as at {entity.balanceSheetDate}
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-[10.5px] text-[#A3A29E] font-mono uppercase">Total Balance</span>
                  <p className="text-base font-bold font-mono text-[#86efac]">
                    ₹{formatCur(currentScheduleData?.totalAmount || 0)}
                  </p>
                </div>
              </div>

              {/* SPECIAL SCHEDULE 1: CAPITAL ACCOUNT FORMAT */}
              {currentHead.isSpecialSchedule === 'CAPITAL' || currentHead.code === 'L01' ? (
                <div className="p-4 text-xs space-y-4 bg-white">
                  <div className="border border-[#141414]/20 overflow-hidden">
                    <table className="w-full text-left border-collapse">
                      <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider border-b border-[#141414]">
                        <tr>
                          <th className="py-2 px-2.5 w-12 text-center border-r border-[#141414]/20">SR.</th>
                          <th className="py-2 px-3 border-r border-[#141414]/20">Particulars / Partner Capital Movements</th>
                          <th className="py-2 px-3 w-36 text-right border-r border-[#141414]/20">Details (₹)</th>
                          <th className="py-2 px-3 w-40 text-right">Amount (₹)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#141414]/15">
                        {/* Capital ledgers */}
                        {currentScheduleData?.ledgers.map((l, idx) => {
                          const isDrawing = l.ledgerName.toLowerCase().includes('drawing') || l.debit > l.credit;
                          const amt = Math.abs(l.debit - l.credit);
                          return (
                            <tr key={l.id} className="hover:bg-[#ECEAE5]/60">
                              <td className="py-1.5 px-2.5 text-center text-[#5E5E5E] font-mono border-r border-[#141414]/10">{idx + 1}</td>
                              <td className="py-1.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">{l.ledgerName}</td>
                              <td className="py-1.5 px-3 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">
                                {isDrawing ? `(₹${formatCur(amt)})` : `₹${formatCur(amt)}`}
                              </td>
                              <td className="py-1.5 px-3 text-right font-mono text-[#141414] font-bold">
                                {isDrawing ? `(₹${formatCur(amt)})` : `₹${formatCur(amt)}`}
                              </td>
                            </tr>
                          );
                        })}

                        {/* Net Profit Flow */}
                        <tr className="bg-[#dcfce7] font-semibold text-[#166534]">
                          <td className="py-1.5 px-2.5 text-center font-mono border-r border-[#141414]/10">
                            {(currentScheduleData?.ledgers.length || 0) + 1}
                          </td>
                          <td className="py-1.5 px-3 flex items-center gap-1.5 border-r border-[#141414]/10 font-bold">
                            <TrendingUp className="w-3.5 h-3.5 shrink-0" />
                            <span>Add: Net Profit for the year as per Profit & Loss Statement</span>
                          </td>
                          <td className="py-1.5 px-3 text-right font-mono border-r border-[#141414]/10">
                            ₹{formatCur(plStatement.netProfitAfterTax)}
                          </td>
                          <td className="py-1.5 px-3 text-right font-mono font-bold">
                            ₹{formatCur(plStatement.netProfitAfterTax)}
                          </td>
                        </tr>
                      </tbody>
                      <tfoot className="bg-[#ECEAE5] font-bold font-mono text-[#141414] border-t-2 border-b-4 border-double border-[#141414]">
                        <tr>
                          <td colSpan={3} className="py-2.5 px-3 text-right text-xs uppercase tracking-wide border-r border-[#141414]/20">
                            Closing Balance Transferred to Balance Sheet:
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-sm">
                            ₹{formatCur(currentScheduleData?.totalAmount || 0)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              ) : currentHead.isSpecialSchedule === 'FIXED_ASSETS' || currentHead.code === 'A01' ? (
                /* SPECIAL SCHEDULE: STATUTORY FIXED ASSETS BLOCK */
                <div className="p-4 text-xs space-y-4 bg-white">
                  {/* Metric Summary Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0]">
                      <span className="text-[10.5px] font-mono text-[#64748B] uppercase">Gross Carrying Block</span>
                      <p className="text-sm font-bold font-mono text-[#1E293B] mt-0.5">
                        ₹{formatCur(
                          (currentScheduleData?.fixedAssetDetails || []).reduce((acc, a) => acc + (a.closingGrossBlock || a.openingGrossBlock), 0) ||
                          currentScheduleData?.ledgers.filter(l => !l.ledgerName.toLowerCase().includes('depreciation')).reduce((acc, l) => acc + Math.abs(l.debit - l.credit), 0) || 0
                        )}
                      </p>
                    </div>
                    <div className="p-3 bg-[#FFFBEB] border border-[#FEF3C7]">
                      <span className="text-[10.5px] font-mono text-[#B45309] uppercase">Accumulated Depreciation</span>
                      <p className="text-sm font-bold font-mono text-[#92400E] mt-0.5">
                        ₹{formatCur(
                          (currentScheduleData?.fixedAssetDetails || []).reduce((acc, a) => acc + (a.closingDepreciation || 0), 0) ||
                          currentScheduleData?.ledgers.filter(l => l.ledgerName.toLowerCase().includes('depreciation')).reduce((acc, l) => acc + Math.abs(l.debit - l.credit), 0) || 0
                        )}
                      </p>
                    </div>
                    <div className="p-3 bg-[#F0FDF4] border border-[#DCFCE7]">
                      <span className="text-[10.5px] font-mono text-[#15803D] uppercase">Net Block (Current Year)</span>
                      <p className="text-sm font-bold font-mono text-[#166534] mt-0.5">
                        ₹{formatCur(currentScheduleData?.totalAmount || 0)}
                      </p>
                    </div>
                  </div>

                  <div className="border border-[#141414]/20 overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[840px]">
                      <thead>
                        <tr className="bg-[#1E293B] text-white font-mono text-[10px] uppercase">
                          <th className="py-2 px-3 border-r border-white/20" rowSpan={2}>Asset Description</th>
                          <th className="py-1.5 px-2 text-center border-r border-white/20 bg-[#1E3A8A]" colSpan={5}>
                            Gross Carrying Amount (₹)
                          </th>
                          <th className="py-1.5 px-2 text-center border-r border-white/20 bg-[#854D0E]" colSpan={4}>
                            Accumulated Depreciation (₹)
                          </th>
                          <th className="py-1.5 px-2 text-center bg-[#14532D]" colSpan={2}>
                            Net Block (₹)
                          </th>
                        </tr>
                        <tr className="bg-[#ECEAE5] text-[#141414] font-mono text-[9.5px] uppercase border-b border-[#141414]">
                          <th className="py-1 px-2 text-right border-r border-[#141414]/20">Opening</th>
                          <th className="py-1 px-2 text-right border-r border-[#141414]/20">Add &gt;180d</th>
                          <th className="py-1 px-2 text-right border-r border-[#141414]/20">Add &lt;180d</th>
                          <th className="py-1 px-2 text-right border-r border-[#141414]/20">Deduct</th>
                          <th className="py-1 px-2 text-right border-r border-[#141414]/20 font-bold">Closing</th>

                          <th className="py-1 px-2 text-right border-r border-[#141414]/20">Opening</th>
                          <th className="py-1 px-2 text-right border-r border-[#141414]/20">For Year</th>
                          <th className="py-1 px-2 text-right border-r border-[#141414]/20">Deduct</th>
                          <th className="py-1 px-2 text-right border-r border-[#141414]/20 font-bold">Closing</th>

                          <th className="py-1 px-2 text-right border-r border-[#141414]/20 font-bold">31-03-2025</th>
                          <th className="py-1 px-2 text-right font-bold">31-03-2024</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#141414]/15">
                        {(currentScheduleData?.fixedAssetDetails && currentScheduleData.fixedAssetDetails.length > 0) ? (
                          currentScheduleData.fixedAssetDetails.map((asset) => (
                            <tr key={asset.id} className="hover:bg-[#ECEAE5]/60 text-[11px]">
                              <td className="py-1.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                                {asset.assetName}
                              </td>
                              <td className="py-1.5 px-2 text-right font-mono border-r border-[#141414]/10">
                                ₹{formatCur(asset.openingGrossBlock)}
                              </td>
                              <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">
                                {asset.additionsMoreThan180Days ? `₹${formatCur(asset.additionsMoreThan180Days)}` : '-'}
                              </td>
                              <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">
                                {asset.additionsLessThan180Days ? `₹${formatCur(asset.additionsLessThan180Days)}` : '-'}
                              </td>
                              <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">
                                {asset.deductionsGrossBlock ? `₹${formatCur(asset.deductionsGrossBlock)}` : '-'}
                              </td>
                              <td className="py-1.5 px-2 text-right font-mono font-bold border-r border-[#141414]/10">
                                ₹{formatCur(asset.closingGrossBlock || asset.openingGrossBlock)}
                              </td>

                              <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">
                                {asset.openingDepreciation ? `₹${formatCur(asset.openingDepreciation)}` : '-'}
                              </td>
                              <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">
                                {asset.currentYearDepreciation ? `₹${formatCur(asset.currentYearDepreciation)}` : '-'}
                              </td>
                              <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">
                                {asset.depreciationOnDeletions ? `₹${formatCur(asset.depreciationOnDeletions)}` : '-'}
                              </td>
                              <td className="py-1.5 px-2 text-right font-mono font-bold border-r border-[#141414]/10">
                                ₹{formatCur(asset.closingDepreciation || 0)}
                              </td>

                              <td className="py-1.5 px-2 text-right font-mono font-bold text-[#15803D] border-r border-[#141414]/10">
                                ₹{formatCur(asset.netBlock)}
                              </td>
                              <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E]">
                                ₹{formatCur(asset.previousYearNetBlock || asset.openingGrossBlock)}
                              </td>
                            </tr>
                          ))
                        ) : (
                          currentScheduleData?.ledgers
                            .filter(l => !l.ledgerName.toLowerCase().includes('depreciation'))
                            .map((l) => {
                              const grossAmt = Math.abs(l.debit - l.credit);
                              return (
                                <tr key={l.id} className="hover:bg-[#ECEAE5]/60 text-[11px]">
                                  <td className="py-1.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">{l.ledgerName}</td>
                                  <td className="py-1.5 px-2 text-right font-mono border-r border-[#141414]/10">₹{formatCur(grossAmt)}</td>
                                  <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">-</td>
                                  <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">-</td>
                                  <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">-</td>
                                  <td className="py-1.5 px-2 text-right font-mono font-bold border-r border-[#141414]/10">₹{formatCur(grossAmt)}</td>
                                  <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">-</td>
                                  <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">-</td>
                                  <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E] border-r border-[#141414]/10">-</td>
                                  <td className="py-1.5 px-2 text-right font-mono font-bold border-r border-[#141414]/10">₹0.00</td>
                                  <td className="py-1.5 px-2 text-right font-mono font-bold text-[#15803D] border-r border-[#141414]/10">₹{formatCur(grossAmt)}</td>
                                  <td className="py-1.5 px-2 text-right font-mono text-[#5E5E5E]">₹{formatCur(grossAmt)}</td>
                                </tr>
                              );
                            })
                        )}
                      </tbody>
                      <tfoot className="bg-[#ECEAE5] font-bold font-mono text-[#141414] border-t-2 border-b-4 border-double border-[#141414] text-[10.5px]">
                        <tr>
                          <td className="py-2.5 px-3 uppercase border-r border-[#141414]/20">TOTAL FIXED ASSETS:</td>
                          <td className="py-2.5 px-2 text-right font-mono border-r border-[#141414]/20">
                            ₹{formatCur((currentScheduleData?.fixedAssetDetails || []).reduce((acc, a) => acc + a.openingGrossBlock, 0) || currentScheduleData?.totalAmount || 0)}
                          </td>
                          <td className="py-2.5 px-2 text-right font-mono border-r border-[#141414]/20">-</td>
                          <td className="py-2.5 px-2 text-right font-mono border-r border-[#141414]/20">-</td>
                          <td className="py-2.5 px-2 text-right font-mono border-r border-[#141414]/20">-</td>
                          <td className="py-2.5 px-2 text-right font-mono border-r border-[#141414]/20">
                            ₹{formatCur((currentScheduleData?.fixedAssetDetails || []).reduce((acc, a) => acc + (a.closingGrossBlock || a.openingGrossBlock), 0) || currentScheduleData?.totalAmount || 0)}
                          </td>
                          <td className="py-2.5 px-2 text-right font-mono border-r border-[#141414]/20">-</td>
                          <td className="py-2.5 px-2 text-right font-mono border-r border-[#141414]/20">-</td>
                          <td className="py-2.5 px-2 text-right font-mono border-r border-[#141414]/20">-</td>
                          <td className="py-2.5 px-2 text-right font-mono border-r border-[#141414]/20">
                            ₹{formatCur((currentScheduleData?.fixedAssetDetails || []).reduce((acc, a) => acc + (a.closingDepreciation || 0), 0))}
                          </td>
                          <td className="py-2.5 px-2 text-right font-mono text-xs text-[#15803D] border-r border-[#141414]/20">
                            ₹{formatCur(currentScheduleData?.totalAmount || 0)}
                          </td>
                          <td className="py-2.5 px-2 text-right font-mono text-xs">
                            ₹{formatCur((currentScheduleData?.fixedAssetDetails || []).reduce((acc, a) => acc + (a.previousYearNetBlock || a.openingGrossBlock), 0) || currentScheduleData?.totalAmount || 0)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  <p className="text-[11px] text-[#64748B] italic font-mono pt-1">
                    * Tangible Property, Plant & Equipment schedule complied under AS-10 and ICAI Technical Guide. Depreciation provided on WDV/SLM as applicable under Income Tax Act, 1961.
                  </p>
                </div>
              ) : (
                /* STANDARD SCHEDULE TABLE */
                <div className="p-4 text-xs space-y-4 bg-white">
                  <div className="border border-[#141414]/20 overflow-hidden">
                    <table className="w-full text-left border-collapse">
                      <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider border-b border-[#141414]">
                        <tr>
                          <th className="py-2 px-2.5 w-12 text-center border-r border-[#141414]/20">SR.</th>
                          <th className="py-2 px-3 border-r border-[#141414]/20">Particulars / Ledger Name</th>
                          <th className="py-2 px-3 w-48 border-r border-[#141414]/20">Original ERP Group</th>
                          <th className="py-2 px-3 w-40 text-right border-r border-[#141414]/20">
                            As on {entity.balanceSheetDate} (₹)
                          </th>
                          <th className="py-2 px-3 w-40 text-right">
                            As on {entity.previousYearDate || '31-03-2024'} (₹)
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#141414]/15">
                        {currentScheduleData?.ledgers.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="py-4 px-3 text-center text-[#5E5E5E] italic font-mono">
                              No individual trial balance ledgers currently mapped to this schedule.
                            </td>
                          </tr>
                        ) : (
                          currentScheduleData?.ledgers.map((l, idx) => {
                            const amt = Math.abs(l.debit - l.credit);
                            const pyDr = l.previousYearDebit || 0;
                            const pyCr = l.previousYearCredit || 0;
                            const pyAmt = (pyDr > 0 || pyCr > 0) ? Math.abs(pyDr - pyCr) : Math.abs(l.previousYearAmount || 0);

                            return (
                              <tr key={l.id} className="hover:bg-[#ECEAE5]/60">
                                <td className="py-1.5 px-2.5 text-center text-[#5E5E5E] font-mono border-r border-[#141414]/10">{idx + 1}</td>
                                <td className="py-1.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">{l.ledgerName}</td>
                                <td className="py-1.5 px-3 text-[#5E5E5E] border-r border-[#141414]/10">{l.originalGroup}</td>
                                <td className="py-1.5 px-3 text-right font-mono font-bold text-[#141414] border-r border-[#141414]/10">
                                  ₹{formatCur(amt)}
                                </td>
                                <td className="py-1.5 px-3 text-right font-mono text-[#5E5E5E]">
                                  {pyAmt > 0 ? `₹${formatCur(pyAmt)}` : '-'}
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                      <tfoot className="bg-[#ECEAE5] font-bold font-mono text-[#141414] border-t-2 border-b-4 border-double border-[#141414]">
                        <tr>
                          <td colSpan={3} className="py-2.5 px-3 text-right text-xs uppercase tracking-wide border-r border-[#141414]/20">
                            Total {currentHead.subHead}:
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-sm border-r border-[#141414]/20">
                            ₹{formatCur(currentScheduleData?.totalAmount || 0)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-sm text-[#5E5E5E]">
                            ₹{formatCur(currentScheduleData?.previousYearTotal ?? 0)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              )}

            </div>
          )}
        </div>

      </div>
    </div>
  );
};
