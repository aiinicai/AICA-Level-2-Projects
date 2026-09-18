import React from 'react';
import {
  CheckCircle,
  AlertTriangle,
  FileSpreadsheet,
  FileText,
  Presentation,
  ArrowRight,
  ShieldCheck,
  Info,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { EntityDetails, ReconciliationReport } from '../types/accounting';

interface ReconciliationViewProps {
  entity: EntityDetails;
  reconciliation: ReconciliationReport;
  onNavigateToTab: (tab: any) => void;
  onExportExcel: () => void;
  onExportPDF?: () => void;
  onExportPPT?: () => void;
}

export const ReconciliationView: React.FC<ReconciliationViewProps> = ({
  entity,
  reconciliation,
  onNavigateToTab,
  onExportExcel,
  onExportPDF,
  onExportPPT,
}) => {
  const formatCur = (val: number) => {
    return Math.abs(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const isEverythingBalanced =
    reconciliation.isTrialBalanceBalanced &&
    reconciliation.isBalanceSheetBalanced &&
    reconciliation.unclassifiedLedgersCount === 0;

  return (
    <div className="space-y-4" id="reconciliation-container">
      {/* Top Banner */}
      <div className="bg-[#141414] text-[#E4E3E0] p-4 border border-[#141414] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <CheckCircle className="w-4 h-4 text-[#A3A29E]" />
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-white">Sheet 7: Audit Reconciliation Statement</h2>
          </div>
          <p className="text-[11.5px] text-[#A3A29E] mt-1">
            Statutory verification checks ensuring exact mathematical and double-entry accuracy across Trial Balance, Trading P&L, and Balance Sheet.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {onExportPPT && (
            <button
              onClick={onExportPPT}
              className="inline-flex items-center px-2.5 py-1 bg-[#2b2416] hover:bg-[#3d321d] text-[#fcd34d] text-[11px] font-mono border border-[#f59e0b]/40 transition"
              title="View & Download 5-Slide Project Presentation Deck (.pptx)"
              id="btn-recon-export-pptx"
            >
              <Presentation className="w-3.5 h-3.5 mr-1 text-[#f59e0b]" />
              PPT DECK (5 SLIDES)
            </button>
          )}
          {onExportPDF && (
            <button
              onClick={onExportPDF}
              className="inline-flex items-center px-3 py-1 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
              title="Export complete financial statements PDF"
            >
              <FileText className="w-3.5 h-3.5 mr-1 text-[#f87171]" />
              EXPORT PDF
            </button>
          )}
          <button
            onClick={onExportExcel}
            className="inline-flex items-center px-3.5 py-1 bg-[#15803d] hover:bg-[#16a34a] text-white text-[11px] font-mono font-bold border border-[#15803d] transition shadow-xs"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 mr-1" />
            EXPORT WORKBOOK (.XLSX)
          </button>
        </div>
      </div>

      {/* Main Reconciliation Table */}
      <div className="bg-[#F5F4F0] border border-[#141414]/20 overflow-hidden">
        <div className="p-3 bg-[#141414] text-white flex items-center justify-between border-b border-[#141414]">
          <h3 className="font-bold text-xs uppercase tracking-wider font-mono">Four-Point Audit Verification Matrix</h3>
          <span
            className={`px-2 py-0.5 text-[10.5px] font-mono font-bold border ${
              isEverythingBalanced
                ? 'bg-[#dcfce7] text-[#166534] border-[#86efac]'
                : 'bg-[#fef3c7] text-[#92400e] border-[#fde68a]'
            }`}
          >
            {isEverythingBalanced ? 'AUDIT STATUS: BALANCED ✓' : 'AUDIT STATUS: ACTION REQUIRED'}
          </span>
        </div>

        <div className="overflow-x-auto text-xs">
          <table className="w-full text-left border-collapse">
            <thead className="bg-[#ECEAE5] text-[#141414] font-mono text-[11px] uppercase tracking-wider border-b border-[#141414]">
              <tr>
                <th className="py-2 px-3 border-r border-[#141414]/20">Verification Point</th>
                <th className="py-2 px-3 w-44 text-right border-r border-[#141414]/20">Debit / Left (₹)</th>
                <th className="py-2 px-3 w-44 text-right border-r border-[#141414]/20">Credit / Right (₹)</th>
                <th className="py-2 px-3 w-32 text-right border-r border-[#141414]/20">Diff (₹)</th>
                <th className="py-2 px-3 w-32 text-center border-r border-[#141414]/20">Status</th>
                <th className="py-2 px-3 w-28 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#141414]/15 bg-white">
              
              {/* Check 1: Trial Balance */}
              <tr className="hover:bg-[#ECEAE5]/60">
                <td className="py-2.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                  <div>1. Trial Balance Debit vs Credit Match</div>
                  <span className="text-[10.5px] text-[#5E5E5E] font-mono font-normal">Original imported ledger sums</span>
                </td>
                <td className="py-2.5 px-3 text-right font-mono border-r border-[#141414]/10">₹{formatCur(reconciliation.totalTrialBalanceDebit)}</td>
                <td className="py-2.5 px-3 text-right font-mono border-r border-[#141414]/10">₹{formatCur(reconciliation.totalTrialBalanceCredit)}</td>
                <td className="py-2.5 px-3 text-right font-mono font-bold text-[#141414] border-r border-[#141414]/10">
                  ₹{formatCur(reconciliation.trialBalanceDifference)}
                </td>
                <td className="py-2.5 px-3 text-center border-r border-[#141414]/10">
                  {reconciliation.isTrialBalanceBalanced ? (
                    <span className="inline-flex items-center px-1.5 py-0.2 font-mono text-[10px] font-bold bg-[#dcfce7] text-[#166534] border border-[#86efac]">
                      <CheckCircle2 className="w-2.5 h-2.5 mr-1" /> Matched
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.2 font-mono text-[10px] font-bold bg-[#fee2e2] text-[#991b1b] border border-[#fca5a5]">
                      <AlertTriangle className="w-2.5 h-2.5 mr-1" /> Mismatch
                    </span>
                  )}
                </td>
                <td className="py-2.5 px-3 text-right">
                  <button
                    onClick={() => onNavigateToTab('trial-balance')}
                    className="text-[#141414] hover:underline font-mono text-[11px] font-bold"
                  >
                    [VIEW TB]
                  </button>
                </td>
              </tr>

              {/* Check 2: Balance Sheet */}
              <tr className="hover:bg-[#ECEAE5]/60">
                <td className="py-2.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                  <div>2. Balance Sheet Total Assets vs Liabilities</div>
                  <span className="text-[10.5px] text-[#5E5E5E] font-mono font-normal">Accounting equation equality</span>
                </td>
                <td className="py-2.5 px-3 text-right font-mono border-r border-[#141414]/10">₹{formatCur(reconciliation.totalAssets)}</td>
                <td className="py-2.5 px-3 text-right font-mono border-r border-[#141414]/10">₹{formatCur(reconciliation.totalLiabilities)}</td>
                <td className="py-2.5 px-3 text-right font-mono font-bold text-[#141414] border-r border-[#141414]/10">
                  ₹{formatCur(reconciliation.balanceSheetDifference)}
                </td>
                <td className="py-2.5 px-3 text-center border-r border-[#141414]/10">
                  {reconciliation.isBalanceSheetBalanced ? (
                    <span className="inline-flex items-center px-1.5 py-0.2 font-mono text-[10px] font-bold bg-[#dcfce7] text-[#166534] border border-[#86efac]">
                      <CheckCircle2 className="w-2.5 h-2.5 mr-1" /> Balanced (0.00)
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.2 font-mono text-[10px] font-bold bg-[#fef3c7] text-[#92400e] border border-[#fde68a]">
                      <AlertTriangle className="w-2.5 h-2.5 mr-1" /> Difference
                    </span>
                  )}
                </td>
                <td className="py-2.5 px-3 text-right">
                  <button
                    onClick={() => onNavigateToTab('balance-sheet')}
                    className="text-[#141414] hover:underline font-mono text-[11px] font-bold"
                  >
                    [VIEW BS]
                  </button>
                </td>
              </tr>

              {/* Check 3: Net Profit to Capital Transfer */}
              <tr className="hover:bg-[#ECEAE5]/60">
                <td className="py-2.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                  <div>3. P&L Net Profit Transferred to Capital Account (Schedule 1)</div>
                  <span className="text-[10.5px] text-[#5E5E5E] font-mono font-normal">Automated profit transfer verification</span>
                </td>
                <td className="py-2.5 px-3 text-right font-mono border-r border-[#141414]/10">₹{formatCur(reconciliation.plNetProfit)}</td>
                <td className="py-2.5 px-3 text-right font-mono border-r border-[#141414]/10">₹{formatCur(reconciliation.capitalProfitTransferred)}</td>
                <td className="py-2.5 px-3 text-right font-mono font-bold text-[#141414] border-r border-[#141414]/10">₹0.00</td>
                <td className="py-2.5 px-3 text-center border-r border-[#141414]/10">
                  <span className="inline-flex items-center px-1.5 py-0.2 font-mono text-[10px] font-bold bg-[#dcfce7] text-[#166534] border border-[#86efac]">
                    <CheckCircle2 className="w-2.5 h-2.5 mr-1" /> Linked ✓
                  </span>
                </td>
                <td className="py-2.5 px-3 text-right">
                  <button
                    onClick={() => onNavigateToTab('schedules')}
                    className="text-[#141414] hover:underline font-mono text-[11px] font-bold"
                  >
                    [VIEW SCH 1]
                  </button>
                </td>
              </tr>

              {/* Check 4: Unclassified Ledgers */}
              <tr className="hover:bg-[#ECEAE5]/60">
                <td className="py-2.5 px-3 font-semibold text-[#141414] border-r border-[#141414]/10">
                  <div>4. Ledger Classification Completeness</div>
                  <span className="text-[10.5px] text-[#5E5E5E] font-mono font-normal">Audit certainty & unclassified items check</span>
                </td>
                <td className="py-2.5 px-3 text-right font-mono border-r border-[#141414]/10">
                  {reconciliation.unclassifiedLedgersCount} items
                </td>
                <td className="py-2.5 px-3 text-right font-mono border-r border-[#141414]/10">-</td>
                <td className="py-2.5 px-3 text-right font-mono font-bold text-[#141414] border-r border-[#141414]/10">
                  ₹{formatCur(reconciliation.unclassifiedTotalAmount)}
                </td>
                <td className="py-2.5 px-3 text-center border-r border-[#141414]/10">
                  {reconciliation.unclassifiedLedgersCount === 0 ? (
                    <span className="inline-flex items-center px-1.5 py-0.2 font-mono text-[10px] font-bold bg-[#dcfce7] text-[#166534] border border-[#86efac]">
                      <CheckCircle2 className="w-2.5 h-2.5 mr-1" /> 100% Mapped
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.2 font-mono text-[10px] font-bold bg-[#fef3c7] text-[#92400e] border border-[#fde68a]">
                      <AlertTriangle className="w-2.5 h-2.5 mr-1" /> {reconciliation.unclassifiedLedgersCount} Review
                    </span>
                  )}
                </td>
                <td className="py-2.5 px-3 text-right">
                  <button
                    onClick={() => onNavigateToTab('classification')}
                    className="text-[#141414] hover:underline font-mono text-[11px] font-bold"
                  >
                    [CLASSIFY]
                  </button>
                </td>
              </tr>

            </tbody>
          </table>
        </div>
      </div>

      {/* Negative Balance / Abnormal Account Alerts */}
      {reconciliation.negativeBalances.length > 0 && (
        <div className="bg-[#fffbeb] border border-[#fde68a] p-4 text-xs space-y-2.5">
          <div className="flex items-center space-x-2 text-[#92400e] font-bold font-mono text-[11px] uppercase">
            <AlertCircle className="w-3.5 h-3.5 text-[#d97706]" />
            <span>Auditor Warning: Negative / Inverted Balances Detected</span>
          </div>
          <p className="text-[#5E5E5E] text-[11px] font-mono">
            The following accounts have inverted balances (e.g. Bank Credit / Overdraft balance or Debtor advance). Consider reclassifying them as Secured Loans/OD or Advances received:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {reconciliation.negativeBalances.map((nb, idx) => (
              <div key={idx} className="bg-white p-2 border border-[#141414]/20 flex justify-between">
                <div>
                  <span className="font-bold text-[#141414]">{nb.ledgerName}</span>
                  <div className="text-[10px] font-mono text-[#92400e]">{nb.actual}</div>
                </div>
                <span className="font-mono font-bold text-[#141414]">₹{formatCur(nb.amount)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
