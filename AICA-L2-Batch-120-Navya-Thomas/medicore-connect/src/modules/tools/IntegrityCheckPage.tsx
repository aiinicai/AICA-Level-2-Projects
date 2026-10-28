import React, { useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertCircle,
  Database,
  Lock,
  ArrowRight,
} from 'lucide-react';
import { runSystemIntegrityChecks } from '../../core/integrity';
import { SystemIntegrityResult } from '../../core/types';

interface IntegrityCheckPageProps {
  onNavigate: (route: string) => void;
}

export const IntegrityCheckPage: React.FC<IntegrityCheckPageProps> = ({ onNavigate }) => {
  const [results, setResults] = useState<SystemIntegrityResult[]>(() => runSystemIntegrityChecks());
  const [isRunning, setIsRunning] = useState(false);

  const handleRerun = () => {
    setIsRunning(true);
    setTimeout(() => {
      setResults(runSystemIntegrityChecks());
      setIsRunning(false);
    }, 400);
  };

  const totalPassed = results.filter((r) => r.status === 'PASS').length;
  const allPassed = totalPassed === results.length;

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50 select-none">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <ShieldCheck className="w-6 h-6 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              ERP System Integrity & Audit Self-Check
            </h1>
            <p className="text-xs text-gray-500">
              Automated 8-point accounting verification &bull; Section 13 Specification &bull; Meridian Healthcare Group
            </p>
          </div>
        </div>

        <button
          onClick={handleRerun}
          disabled={isRunning}
          className="px-4 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-2 transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
          <span>Re-run Integrity Verification</span>
        </button>
      </div>

      {/* Global Status Banner */}
      <div
        className={`p-5 rounded-xl border mb-6 flex items-center justify-between shadow-xs ${
          allPassed
            ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
            : 'bg-rose-50 border-rose-300 text-rose-950'
        }`}
      >
        <div className="flex items-center space-x-3">
          {allPassed ? (
            <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 shrink-0">
              <CheckCircle2 className="w-6 h-6" />
            </div>
          ) : (
            <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-700 shrink-0">
              <XCircle className="w-6 h-6" />
            </div>
          )}
          <div>
            <h2 className="font-bold text-base">
              {allPassed
                ? 'All 8 System Integrity Audits Passed (100% Green)'
                : `${results.length - totalPassed} System Integrity Audit(s) Failed`}
            </h2>
            <p className="text-xs text-gray-600 mt-0.5">
              {allPassed
                ? 'Trial balance is balanced to the penny, subledger controls tie out, intercompany eliminates to zero, and maker-checker segregation of duties is fully intact.'
                : 'Please review the offending records flagged below to rectify the ledger discrepancies.'}
            </p>
          </div>
        </div>

        <span className="text-xs font-bold px-3 py-1 rounded-full bg-white border shadow-xs">
          Score: <strong className="text-emerald-700">{totalPassed}</strong> / {results.length} Passing
        </span>
      </div>

      {/* 8 Audit Check Cards */}
      <div className="space-y-4">
        {results.map((res) => {
          const isPass = res.status === 'PASS';
          return (
            <div
              key={res.checkId}
              className={`p-5 rounded-xl border bg-white shadow-xs transition-all ${
                isPass ? 'border-gray-200 hover:border-emerald-300' : 'border-rose-300 bg-rose-50/20'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3">
                  <div
                    className={`p-2 rounded-lg mt-0.5 ${
                      isPass ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                    }`}
                  >
                    {isPass ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-gray-400">
                        Check #{res.checkId}
                      </span>
                      <h3 className="font-bold text-sm text-gray-900">{res.title}</h3>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{res.description}</p>
                    <div className="mt-2.5 p-2 rounded bg-gray-50 border border-gray-100 text-xs font-medium text-gray-800">
                      {res.details}
                    </div>
                  </div>
                </div>

                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                    isPass ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                  }`}
                >
                  {res.status}
                </span>
              </div>

              {/* Show Offending Records if any fail */}
              {res.offendingRecords && res.offendingRecords.length > 0 && (
                <div className="mt-4 pt-3 border-t border-rose-200">
                  <span className="text-xs font-bold text-rose-800 uppercase block mb-1">
                    Offending Records:
                  </span>
                  <pre className="p-3 bg-white rounded border border-rose-200 text-[11px] font-mono text-gray-800 overflow-x-auto">
                    {JSON.stringify(res.offendingRecords, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
