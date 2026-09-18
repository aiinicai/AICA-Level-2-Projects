import React from 'react';
import {
  TrendingUp,
  ArrowRight,
  Sparkles,
  Layers,
  ArrowUpRight,
  Calculator,
  FileText,
} from 'lucide-react';
import { EntityDetails, PLStatement } from '../types/accounting';

interface ProfitAndLossViewProps {
  entity: EntityDetails;
  plStatement: PLStatement;
  onNavigateToTab: (tab: any) => void;
  onOpenAdjustments: () => void;
  onExportPDF?: () => void;
}

export const ProfitAndLossView: React.FC<ProfitAndLossViewProps> = ({
  entity,
  plStatement,
  onNavigateToTab,
  onOpenAdjustments,
  onExportPDF,
}) => {
  const formatCur = (amt: number) => {
    return amt.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="space-y-4" id="pl-statement-container">
      {/* Header Banner */}
      <div className="bg-[#141414] text-[#E4E3E0] p-4 border border-[#141414] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-[#A3A29E]" />
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-white">Sheet 4: Profit & Loss Statement (Trading & P&L)</h2>
          </div>
          <p className="text-[11.5px] text-[#A3A29E] mt-1">
            Standard Indian accounting Trading & Profit and Loss Account for the period ended {entity.balanceSheetDate}. Net Profit automatically transfers to Schedule 1 (Capital Account).
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {onExportPDF && (
            <button
              onClick={onExportPDF}
              className="inline-flex items-center px-2.5 py-1 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
              title="Export complete financial statements PDF"
            >
              <FileText className="w-3 h-3 mr-1 text-[#f87171]" />
              EXPORT PDF
            </button>
          )}
          <button
            onClick={onOpenAdjustments}
            className="inline-flex items-center px-2.5 py-1 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
          >
            <Calculator className="w-3 h-3 mr-1 text-[#A3A29E]" />
            ADJUST CLOSING STOCK
          </button>
          <button
            onClick={() => onNavigateToTab('balance-sheet')}
            className="inline-flex items-center px-3 py-1 bg-[#E4E3E0] hover:bg-white text-[#141414] text-[11px] font-mono font-bold border border-[#141414] transition"
          >
            <span>BALANCE SHEET</span>
            <ArrowRight className="w-3 h-3 ml-1" />
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-[#F5F4F0] p-3.5 border border-[#141414]/20">
          <span className="text-[#5E5E5E] font-mono text-[10.5px] uppercase tracking-wider">Total Direct Turnover / Sales</span>
          <p className="text-base font-bold font-mono text-[#141414] mt-1">₹{formatCur(plStatement.totalDirectIncome)}</p>
          <span className="text-[10.5px] font-mono text-[#5E5E5E]">{plStatement.directIncomes.length} Accounts</span>
        </div>

        <div className="bg-[#F5F4F0] p-3.5 border border-[#141414]/20">
          <span className="text-[#5E5E5E] font-mono text-[10.5px] uppercase tracking-wider">Gross Profit</span>
          <p className="text-base font-bold font-mono text-[#141414] mt-1">₹{formatCur(plStatement.grossProfit)}</p>
          <span className="text-[10.5px] font-mono font-bold text-[#141414]">
            GP Margin: {plStatement.grossProfitPercentage.toFixed(2)}%
          </span>
        </div>

        <div className="bg-[#F5F4F0] p-3.5 border border-[#141414]/20">
          <span className="text-[#5E5E5E] font-mono text-[10.5px] uppercase tracking-wider">Total Indirect Expenses</span>
          <p className="text-base font-bold font-mono text-[#141414] mt-1">₹{formatCur(plStatement.totalIndirectExpenses)}</p>
          <span className="text-[10.5px] font-mono text-[#5E5E5E]">{plStatement.indirectExpenses.length} Expense Accounts</span>
        </div>

        <div className="bg-[#dcfce7] p-3.5 border border-[#86efac] text-[#166534] font-mono">
          <span className="font-bold text-[10.5px] uppercase tracking-wider opacity-80">Net Profit Transferred to Capital</span>
          <p className="text-base font-bold mt-1">₹{formatCur(plStatement.netProfitAfterTax)}</p>
          <span className="text-[10.5px] font-semibold flex items-center gap-1">
            <ArrowUpRight className="w-3 h-3" /> Flows to Capital Sch 1
          </span>
        </div>
      </div>

      {/* Main Trading & P&L Statement Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* Left Side: Particulars (Expenses / Debits) */}
        <div className="bg-[#F5F4F0] border border-[#141414]/20 overflow-hidden">
          <div className="bg-[#141414] text-[#E4E3E0] px-3.5 py-2 flex items-center justify-between border-b border-[#141414]">
            <h3 className="font-bold text-[11px] font-mono tracking-wider uppercase">Particulars (Debit / Expenses)</h3>
            <span className="text-[11px] text-[#A3A29E] font-mono">Amount (₹)</span>
          </div>

          <div className="p-3.5 space-y-3.5 text-xs bg-white">
            {/* Trading Section Debits */}
            <div>
              <div className="font-bold font-mono text-[#141414] text-[11px] uppercase border-b border-[#141414]/20 pb-1 mb-2">
                I. Direct Trading Expenses & Opening Stock
              </div>
              <div className="space-y-1">
                {plStatement.openingStock > 0 && (
                  <div className="flex justify-between py-1 text-[#141414] border-b border-[#141414]/10">
                    <span>To Opening Stock</span>
                    <span className="font-mono font-medium">₹{formatCur(plStatement.openingStock)}</span>
                  </div>
                )}
                {plStatement.directExpenses.map((exp, idx) => (
                  <div key={idx} className="flex justify-between py-1 text-[#141414] border-b border-[#141414]/10">
                    <span>To {exp.name}</span>
                    <span className="font-mono font-medium">₹{formatCur(exp.amount)}</span>
                  </div>
                ))}
                {plStatement.directExpenses.length === 0 && plStatement.openingStock === 0 && (
                  <div className="text-[#8E8C85] py-1 italic font-mono text-[11px]">No direct expense ledgers classified</div>
                )}

                {/* Gross Profit c/d */}
                <div className="flex justify-between py-1.5 font-bold font-mono text-[#141414] bg-[#ECEAE5] px-2 border border-[#141414]/20 mt-2">
                  <span>To Gross Profit c/d (Transferred to P&L)</span>
                  <span>₹{formatCur(plStatement.grossProfit)}</span>
                </div>
              </div>
            </div>

            {/* P&L Section Debits */}
            <div className="pt-2 border-t border-[#141414]/20">
              <div className="font-bold font-mono text-[#141414] text-[11px] uppercase border-b border-[#141414]/20 pb-1 mb-2">
                II. Indirect Operating & Administrative Expenses
              </div>
              <div className="space-y-1 max-h-[320px] overflow-y-auto pr-1">
                {plStatement.indirectExpenses.map((exp, idx) => (
                  <div key={idx} className="flex justify-between py-1 text-[#141414] border-b border-[#141414]/10">
                    <span className="truncate pr-2">To {exp.name}</span>
                    <span className="font-mono font-medium shrink-0">₹{formatCur(exp.amount)}</span>
                  </div>
                ))}
              </div>

              {/* Net Profit */}
              <div className="flex justify-between py-2 font-bold font-mono text-[#166534] bg-[#dcfce7] px-2.5 mt-3 border border-[#86efac]">
                <span>To Net Profit Transferred to Capital Account</span>
                <span>₹{formatCur(plStatement.netProfitAfterTax)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Particulars (Incomes / Credits) */}
        <div className="bg-[#F5F4F0] border border-[#141414]/20 overflow-hidden">
          <div className="bg-[#141414] text-[#E4E3E0] px-3.5 py-2 flex items-center justify-between border-b border-[#141414]">
            <h3 className="font-bold text-[11px] font-mono tracking-wider uppercase">Particulars (Credit / Incomes)</h3>
            <span className="text-[11px] text-[#A3A29E] font-mono">Amount (₹)</span>
          </div>

          <div className="p-3.5 space-y-3.5 text-xs bg-white">
            {/* Trading Section Credits */}
            <div>
              <div className="font-bold font-mono text-[#141414] text-[11px] uppercase border-b border-[#141414]/20 pb-1 mb-2">
                I. Direct Revenue from Operations & Closing Stock
              </div>
              <div className="space-y-1">
                {plStatement.directIncomes.map((inc, idx) => (
                  <div key={idx} className="flex justify-between py-1 text-[#141414] border-b border-[#141414]/10">
                    <span>By {inc.name}</span>
                    <span className="font-mono font-medium">₹{formatCur(inc.amount)}</span>
                  </div>
                ))}
                {plStatement.closingStock > 0 ? (
                  <div className="flex justify-between py-1 text-[#166534] bg-[#f0fdf4] px-1 border border-[#86efac]">
                    <span className="font-semibold font-mono">By Closing Stock (Inventories)</span>
                    <span className="font-mono font-bold">₹{formatCur(plStatement.closingStock)}</span>
                  </div>
                ) : (
                  <div className="flex justify-between py-1 text-[#8E8C85] italic font-mono text-[11px]">
                    <span>By Closing Stock (Click 'Adjustments' to add)</span>
                    <span>₹0.00</span>
                  </div>
                )}
              </div>
            </div>

            {/* P&L Section Credits */}
            <div className="pt-2 border-t border-[#141414]/20">
              <div className="font-bold font-mono text-[#141414] text-[11px] uppercase border-b border-[#141414]/20 pb-1 mb-2">
                II. Gross Profit b/d & Other Indirect Incomes
              </div>
              <div className="space-y-1">
                <div className="flex justify-between py-1 font-bold font-mono text-[#141414] bg-[#ECEAE5] px-2 border border-[#141414]/20">
                  <span>By Gross Profit b/d</span>
                  <span>₹{formatCur(plStatement.grossProfit)}</span>
                </div>

                {plStatement.indirectIncomes.map((inc, idx) => (
                  <div key={idx} className="flex justify-between py-1 text-[#141414] border-b border-[#141414]/10">
                    <span>By {inc.name}</span>
                    <span className="font-mono font-medium">₹{formatCur(inc.amount)}</span>
                  </div>
                ))}
                {plStatement.indirectIncomes.length === 0 && (
                  <div className="text-[#8E8C85] py-1 italic font-mono text-[11px]">No other indirect incomes</div>
                )}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
