import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Department, DepartmentSubmission } from '../types';
import {
  formatINR,
  formatAUD,
  convertInrToAud,
  formatIST,
  formatVariance,
} from '../utils/formatters';
import {
  Sliders,
  DollarSign,
  Lock,
  Unlock,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  ArrowRight,
  FileCheck,
  Building,
  Users,
  Server,
  IndianRupee,
  RefreshCw,
  Edit3,
  Check,
} from 'lucide-react';

interface FinanceControllerViewProps {
  onNavigateToDept?: (dept: Department) => void;
}

export const FinanceControllerView: React.FC<FinanceControllerViewProps> = ({ onNavigateToDept }) => {
  const {
    currentUser,
    activeMonth,
    activeMonthId,
    submissions,
    updateExchangeRate,
    setControllerConsolidationNotes,
    markPackReadyForApproval,
    getPriorMonthSubmission,
  } = useApp();

  // Exchange rate local form state
  const [rateInput, setRateInput] = useState<string>(activeMonth.exchangeRate.toString());
  const [sourceInput, setSourceInput] = useState<string>(activeMonth.rateSource || '');
  const [isUpdatingRate, setIsUpdatingRate] = useState<boolean>(false);
  const [isFetchingLiveFx, setIsFetchingLiveFx] = useState<boolean>(false);
  const [consolidationNotes, setConsolidationNotes] = useState<string>(
    activeMonth.consolidationNotes || ''
  );
  const [isNotesSaved, setIsNotesSaved] = useState<boolean>(false);

  // Submissions for this month
  const currentSubs = submissions[activeMonthId] || [];
  const departments: Department[] = ['HR', 'Admin', 'IT', 'Finance'];

  // Check submission status per department
  const deptStatuses = departments.map((dept) => {
    const sub = currentSubs.find((s) => s.department === dept);
    const priorSub = getPriorMonthSubmission(activeMonthId, dept);
    const totalInr = sub?.lineItems.reduce((acc, i) => acc + (Number(i.amountInr) || 0), 0) || 0;
    const priorTotalInr = priorSub?.lineItems.reduce((acc, i) => acc + (i.approvedAmountInr ?? i.amountInr), 0) || 0;
    
    return {
      department: dept,
      submission: sub,
      status: sub?.status || ('Not Started' as const),
      isSubmitted: sub?.status === 'Submitted' || sub?.status === 'Locked' || sub?.status === 'Approved',
      totalInr,
      totalAud: convertInrToAud(totalInr, activeMonth.exchangeRate),
      itemCount: sub?.lineItems.length || 0,
      submittedBy: sub?.submittedBy || '—',
      submittedAt: sub?.submittedAt,
      variance: formatVariance(totalInr, priorTotalInr),
    };
  });

  const allSubmitted = deptStatuses.every((d) => d.isSubmitted);
  const submittedCount = deptStatuses.filter((d) => d.isSubmitted).length;

  // Grand totals
  const grandTotalInr = deptStatuses.reduce((acc, d) => acc + d.totalInr, 0);
  const grandTotalAud = convertInrToAud(grandTotalInr, activeMonth.exchangeRate);

  const isLocked = activeMonth.status === 'Ready for Approval' || activeMonth.status === 'Approved' || activeMonth.status === 'Closed';

  // Save exchange rate
  const handleSaveRate = () => {
    const num = parseFloat(rateInput);
    if (isNaN(num) || num <= 0) {
      alert('Please enter a valid positive exchange rate.');
      return;
    }
    updateExchangeRate(activeMonthId, num, sourceInput);
    setIsUpdatingRate(false);
  };

  // Simulated live FX benchmark fetch
  const handleFetchLiveRate = () => {
    setIsFetchingLiveFx(true);
    setTimeout(() => {
      // Small simulated live fluctuation
      const base = 0.01824;
      const jitter = (Math.random() - 0.5) * 0.0003;
      const liveRate = parseFloat((base + jitter).toFixed(5));
      const today = new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      setRateInput(liveRate.toString());
      setSourceInput(`Live Interbank FX Benchmark via RBA & Market Feed (${today})`);
      setIsFetchingLiveFx(false);
      setIsUpdatingRate(true);
    }, 600);
  };

  // Save consolidation notes
  const handleSaveNotes = () => {
    setControllerConsolidationNotes(activeMonthId, consolidationNotes);
    setIsNotesSaved(true);
    setTimeout(() => setIsNotesSaved(false), 2500);
  };

  // Mark ready for approval
  const handleMarkReady = () => {
    if (!allSubmitted) {
      const confirmOverride = confirm(
        `Warning: Only ${submittedCount} of 4 departments have submitted their requirements. Do you still want to lock the pack and route to Management for review?`
      );
      if (!confirmOverride) return;
    }

    if (confirm(`Lock the monthly exchange rate and mark the ${activeMonth.label} Cash Pack as 'Ready for Approval'? Management will receive immediate review authorization.`)) {
      markPackReadyForApproval(activeMonthId);
    }
  };

  const getDeptIcon = (dept: Department) => {
    switch (dept) {
      case 'HR':
        return <Users className="w-4 h-4 text-blue-600" />;
      case 'Admin':
        return <Building className="w-4 h-4 text-amber-600" />;
      case 'IT':
        return <Server className="w-4 h-4 text-indigo-600" />;
      case 'Finance':
        return <IndianRupee className="w-4 h-4 text-emerald-600" />;
    }
  };

  return (
    <div id="finance-controller-container" className="space-y-6">
      
      {/* Top Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200 uppercase tracking-widest">
                Finance Controller Module
              </span>
              <h2 className="text-xl font-black text-slate-900 tracking-tight">
                Monthly Consolidation & FX Treasury Command
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Consolidation cycle for <strong className="text-slate-800">{activeMonth.label}</strong> • Review department submissions, lock exchange rate, and route combined pack to Management.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {isLocked ? (
              <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 text-blue-800 px-3.5 py-2 rounded-lg text-xs font-bold">
                <Lock className="w-4 h-4 text-blue-600" />
                <span>Pack Locked & Routed to Management</span>
              </div>
            ) : (
              <button
                id="btn-mark-ready-for-approval"
                onClick={handleMarkReady}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-bold text-white bg-[#0F172A] hover:bg-black shadow-sm transition-all"
              >
                <FileCheck className="w-4 h-4 text-emerald-400" />
                <span>Mark Pack as Ready for Approval</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Grid: Exchange Rate Engine + Consolidation Checklist */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Module 2: Currency Conversion & Exchange Rate Engine */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-emerald-50 rounded-lg text-emerald-700">
                <DollarSign className="w-4 h-4" />
              </div>
              <h3 className="font-bold text-slate-900 text-sm">
                INR → AUD FX Engine
              </h3>
            </div>
            {isLocked ? (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                <Lock className="w-3 h-3 text-slate-500" /> Rate Locked
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                <Unlock className="w-3 h-3 text-emerald-600" /> Active Rate
              </span>
            )}
          </div>

          {/* Current Rate Display */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div className="text-xs text-slate-500 font-medium">Official Monthly Conversion Rate</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-black text-slate-900 font-mono">
                1 INR = {activeMonth.exchangeRate} AUD
              </span>
            </div>
            <div className="text-xs font-mono text-emerald-700 font-semibold mt-1">
              (1 AUD ≈ ₹{(1 / activeMonth.exchangeRate).toFixed(2)} INR)
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              Source: <span className="font-medium text-slate-700">{activeMonth.rateSource || 'RBI Reference Rate'}</span>
            </p>
            {activeMonth.rateLockedAt && (
              <p className="text-[10px] text-slate-400 mt-0.5">
                Locked at: {formatIST(activeMonth.rateLockedAt)} by {activeMonth.rateLockedBy}
              </p>
            )}
          </div>

          {/* Edit Rate Form */}
          {!isLocked ? (
            <div className="space-y-3 pt-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700">Update Exchange Rate:</span>
                <button
                  type="button"
                  onClick={handleFetchLiveRate}
                  disabled={isFetchingLiveFx}
                  className="flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:text-blue-800 disabled:opacity-50"
                  title="Simulate fetching live FX benchmark rate"
                >
                  <RefreshCw className={`w-3 h-3 ${isFetchingLiveFx ? 'animate-spin' : ''}`} />
                  <span>Fetch Benchmark</span>
                </button>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-600 mb-1">
                  Exchange Rate (INR to AUD multiplier):
                </label>
                <input
                  type="number"
                  step="0.00001"
                  value={rateInput}
                  onChange={(e) => {
                    setRateInput(e.target.value);
                    setIsUpdatingRate(true);
                  }}
                  placeholder="0.01825"
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs font-mono font-bold text-slate-900 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-600 mb-1">
                  Rate Source / Reference Documentation:
                </label>
                <input
                  type="text"
                  value={sourceInput}
                  onChange={(e) => {
                    setSourceInput(e.target.value);
                    setIsUpdatingRate(true);
                  }}
                  placeholder="e.g. RBI reference rate as of 25/08/2026"
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {isUpdatingRate && (
                <button
                  type="button"
                  onClick={handleSaveRate}
                  className="w-full flex items-center justify-center gap-1.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Apply & Save Exchange Rate</span>
                </button>
              )}
            </div>
          ) : (
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
              Exchange rate is currently locked for this cycle. Rate changes are disabled after marking pack ready for approval to prevent shifting approval calculations.
            </div>
          )}

        </div>

        {/* Department Submissions Readiness & Summary */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <span>Department Submissions Status</span>
              <span className="text-xs px-2 py-0.5 rounded-full font-bold bg-blue-50 text-blue-700 border border-blue-200">
                {submittedCount} of 4 Ready
              </span>
            </h3>

            <div className="text-right">
              <span className="text-xs text-slate-500">Consolidated Pack Total:</span>
              <div className="text-base font-bold text-slate-900 font-mono">
                {formatINR(grandTotalInr)} <span className="text-emerald-700 font-semibold">({formatAUD(grandTotalAud)})</span>
              </div>
            </div>
          </div>

          {/* Department Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {deptStatuses.map((dept) => (
              <div
                key={dept.department}
                className="bg-slate-50/70 border border-slate-200 rounded-xl p-4 flex flex-col justify-between hover:border-slate-300 transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 font-bold text-slate-900 text-xs">
                      {getDeptIcon(dept.department)}
                      <span>{dept.department} Department</span>
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        dept.status === 'Submitted'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : dept.status === 'Locked'
                          ? 'bg-blue-50 text-blue-700 border-blue-200'
                          : dept.status === 'Approved'
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                          : 'bg-amber-50 text-amber-700 border-amber-200'
                      }`}
                    >
                      {dept.status}
                    </span>
                  </div>

                  <div className="mt-1">
                    <div className="text-lg font-bold text-slate-900 font-mono">
                      {formatINR(dept.totalInr)}
                    </div>
                    <div className="text-xs text-emerald-700 font-semibold font-mono">
                      {formatAUD(dept.totalAud)}
                    </div>
                  </div>

                  <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
                    <span>{dept.itemCount} line items</span>
                    <span className="font-semibold text-slate-700">MoM: {dept.variance.formatted}</span>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-200/80 flex items-center justify-between text-[11px]">
                  <span className="text-slate-500 truncate max-w-[140px]">
                    By: {dept.submittedBy}
                  </span>
                  {onNavigateToDept && (
                    <button
                      type="button"
                      onClick={() => onNavigateToDept(dept.department)}
                      className="text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-0.5"
                    >
                      <span>Inspect</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Consolidation Notes Editor */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-slate-800">
                Controller Review & Consolidation Notes for Management:
              </label>
              {isNotesSaved && (
                <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Notes Saved!
                </span>
              )}
            </div>
            <textarea
              rows={2}
              value={consolidationNotes}
              onChange={(e) => setConsolidationNotes(e.target.value)}
              placeholder="Add key highlights (e.g. major variance drivers, tax deadlines, foreign exchange exposure) for the Management Approver..."
              className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-800 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            />
            <div className="mt-2 flex justify-end">
              <button
                type="button"
                onClick={handleSaveNotes}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold shadow-xs"
              >
                Save Consolidation Notes
              </button>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};
