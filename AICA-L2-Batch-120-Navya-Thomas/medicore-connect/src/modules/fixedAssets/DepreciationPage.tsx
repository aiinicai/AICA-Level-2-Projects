import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Play,
  ArrowRight,
  Building2,
  Calendar,
  Lock,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { getActiveUser } from '../../core/auth';
import { DepreciationRun, DepreciationRunLine } from '../../core/types';
import { round2, addMoney, formatAED } from '../../core/currency';
import { buildDepreciationRunAccounting, postToGL } from '../../core/postingEngine';

interface DepreciationPageProps {
  onNavigate: (route: string) => void;
}

export const DepreciationPage: React.FC<DepreciationPageProps> = ({ onNavigate }) => {
  const db = getDb();
  const currentUser = getActiveUser();

  const [period, setPeriod] = useState('Oct-26');
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Check if depreciation already posted for selected period
  const existingRun = db.depreciationRuns.find((r) => r.period === period && r.status === 'Posted');

  // Preview lines calculation
  const previewLines: DepreciationRunLine[] = db.fixedAssets
    .filter((a) => a.status === 'Active')
    .map((fa) => {
      const monthlyAmt = round2(fa.cost / (fa.usefulLifeYears * 12));
      return {
        assetId: fa.id,
        assetTag: fa.tagNumber,
        assetName: fa.name,
        businessUnit: fa.businessUnit,
        category: fa.category,
        depreciationAmount: monthlyAmt,
        accumDepAccount: fa.accumDepAccount,
        depExpenseAccount: '6300',
      };
    });

  const totalMonthlyDep = previewLines.reduce((acc, l) => addMoney(acc, l.depreciationAmount), 0);

  const handleExecuteDepreciation = () => {
    setActionMessage(null);
    setErrorMessage(null);

    // Strict rule: Cannot run twice for the same period
    if (existingRun) {
      setErrorMessage(
        `Execution Blocked: Depreciation for period ${period} has already been posted to the General Ledger (Journal: ${existingRun.glJournalId || 'DEP-' + period}). Duplicate depreciation runs are strictly prohibited.`
      );
      return;
    }

    const runId = `DEP-${period}`;
    const runRecord: DepreciationRun = {
      id: runId,
      period,
      runDate: '2026-10-19',
      businessUnit: 'All',
      totalDepreciation: totalMonthlyDep,
      lines: previewLines,
      status: 'Posted',
      createdBy: currentUser.userId,
      approvedBy: currentUser.userId,
    };

    // Subledger posting
    const subEntry = buildDepreciationRunAccounting(runRecord);
    const postRes = postToGL(subEntry, {
      createdBy: currentUser.userId,
      approvedBy: currentUser.userId,
      category: 'Depreciation',
    });

    if (postRes.success && postRes.journal) {
      runRecord.glJournalId = postRes.journal.id;

      updateDb((state) => {
        state.depreciationRuns.unshift(runRecord);
        // Update accumulated depreciation on all fixed assets in register
        previewLines.forEach((l) => {
          const fa = state.fixedAssets.find((a) => a.id === l.assetId);
          if (fa) {
            fa.accumulatedDepreciation = addMoney(fa.accumulatedDepreciation, l.depreciationAmount);
            fa.netBookValue = round2(fa.cost - fa.accumulatedDepreciation);
            fa.lastDepreciationPeriod = period;
          }
        });
      });

      addAuditLog({
        entityType: 'DepreciationRun',
        entityId: runRecord.id,
        action: 'POST',
        userId: currentUser.userId,
        userName: currentUser.name,
        comments: `Executed monthly depreciation run for ${period}. Posted GL journal ${postRes.journal.number}`,
      });

      setActionMessage(
        `Successfully posted ${period} Depreciation Run across ${previewLines.length} assets. Generated GL Journal ${postRes.journal.number} for AED ${formatAED(
          totalMonthlyDep
        )} (Dr 6300 Depreciation Expense / Cr 1810-1870 Accumulated Depreciation).`
      );
    } else {
      setErrorMessage(`Posting Failed: ${postRes.errors?.join('; ')}`);
    }
  };

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <Sparkles className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Run Fixed Asset Depreciation</h1>
            <p className="text-xs text-gray-500">
              Straight-line monthly depreciation engine &bull; Book: MERIDIAN CORPORATE ASSETS – AED
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <label className="text-xs font-semibold text-gray-600">Select Period:</label>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="bg-white border border-gray-300 rounded-lg px-3 py-1.5 text-xs text-gray-800 font-semibold focus:ring-2 focus:ring-[#5B2C83] focus:outline-none"
          >
            <option value="Oct-26">Oct-26 (Current Open Period)</option>
            <option value="Nov-26">Nov-26 (Future)</option>
          </select>
        </div>
      </div>

      {actionMessage && (
        <div className="mb-5 p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs flex items-center justify-between">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="mb-5 p-4 rounded-xl bg-rose-50 border border-rose-300 text-rose-800 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {/* Summary Box */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs p-5 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-xs">
            <div>
              <span className="text-gray-500 block uppercase font-medium">Period Target</span>
              <span className="font-bold text-base text-[#3F1D5C]">{period}</span>
            </div>
            <div>
              <span className="text-gray-500 block uppercase font-medium">Eligible Active Assets</span>
              <span className="font-bold text-base text-gray-900">{previewLines.length} Assets</span>
            </div>
            <div>
              <span className="text-gray-500 block uppercase font-medium">Calculated Monthly Dep.</span>
              <span className="font-bold text-base text-emerald-700 font-mono">
                {formatAED(totalMonthlyDep, { showCurrency: true })}
              </span>
            </div>
            <div>
              <span className="text-gray-500 block uppercase font-medium">Current Status</span>
              {existingRun ? (
                <span className="inline-flex items-center text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full mt-1">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                  Already Posted
                </span>
              ) : (
                <span className="inline-flex items-center text-xs font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded-full mt-1">
                  Ready to Run
                </span>
              )}
            </div>
          </div>

          <button
            onClick={handleExecuteDepreciation}
            disabled={Boolean(existingRun)}
            className="px-5 py-2.5 bg-[#5B2C83] hover:bg-[#3F1D5C] disabled:bg-gray-300 disabled:text-gray-500 text-white font-semibold text-xs rounded-lg shadow-sm flex items-center space-x-2 transition-colors cursor-pointer"
          >
            <Play className="w-4 h-4 fill-current text-amber-300" />
            <span>{existingRun ? 'Period Already Run' : `Execute ${period} Depreciation`}</span>
          </button>
        </div>
      </div>

      {/* Preview Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
          <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
            Asset-by-Asset Depreciation Schedule ({period})
          </h2>
          <span className="text-[11px] text-gray-500">Prorated straight line from in-service date</span>
        </div>

        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider sticky top-0 border-b border-plum-200">
              <tr>
                <th className="py-2.5 px-3 w-10 text-center">#</th>
                <th className="py-2.5 px-3 w-28">Asset Tag</th>
                <th className="py-2.5 px-3">Description</th>
                <th className="py-2.5 px-3 w-16">BU</th>
                <th className="py-2.5 px-3 w-36">Category</th>
                <th className="py-2.5 px-3 text-right w-32">Monthly Dep. (AED)</th>
                <th className="py-2.5 px-3 w-28 font-mono">Dr Expense</th>
                <th className="py-2.5 px-3 w-28 font-mono">Cr Accum Dep</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {previewLines.map((line, idx) => (
                <tr key={idx} className="hover:bg-plum-50/30">
                  <td className="py-2 px-3 text-center text-gray-400">{idx + 1}</td>
                  <td className="py-2 px-3 font-mono font-bold text-[#5B2C83]">{line.assetTag}</td>
                  <td className="py-2 px-3 font-medium text-gray-800">{line.assetName}</td>
                  <td className="py-2 px-3 font-semibold text-gray-700">{line.businessUnit}</td>
                  <td className="py-2 px-3 text-gray-600">{line.category}</td>
                  <td className="py-2 px-3 text-right font-mono font-bold text-gray-900">
                    {formatAED(line.depreciationAmount)}
                  </td>
                  <td className="py-2 px-3 font-mono text-gray-600">6300</td>
                  <td className="py-2 px-3 font-mono text-gray-600">{line.accumDepAccount}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-100 font-bold border-t border-gray-300 text-xs">
              <tr>
                <td colSpan={5} className="py-2.5 px-3 text-right uppercase tracking-wider">
                  Total Monthly Depreciation:
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-emerald-800 text-sm">
                  {formatAED(totalMonthlyDep)}
                </td>
                <td colSpan={2}></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
};
