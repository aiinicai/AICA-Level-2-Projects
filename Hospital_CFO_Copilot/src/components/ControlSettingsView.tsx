import React, { useState } from 'react';
import {
  AuditTrailRun,
  ControlRuleConfig,
  UserSession,
} from '../types';
import {
  CheckCircle2,
  FileCheck,
  Lock,
  Play,
  RotateCcw,
  Save,
  Shield,
  Sliders,
} from 'lucide-react';
import { formatIndianDateTime, formatINR } from '../utils/formatters';

interface ControlSettingsViewProps {
  config: ControlRuleConfig;
  auditTrail: AuditTrailRun[];
  currentUser: UserSession;
  onUpdateConfig: (newConfig: ControlRuleConfig) => void;
  onRunControls: () => void;
}

export const ControlSettingsView: React.FC<ControlSettingsViewProps> = ({
  config,
  auditTrail,
  currentUser,
  onUpdateConfig,
  onRunControls,
}) => {
  const [localConfig, setLocalConfig] = useState<ControlRuleConfig>(config);
  const [hasSaved, setHasSaved] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const isReadOnly = currentUser.role === 'Auditor';

  const handleSliderChange = <K extends keyof ControlRuleConfig>(
    key: K,
    val: ControlRuleConfig[K]
  ) => {
    if (isReadOnly) return;
    const updated = { ...localConfig, [key]: val };
    setLocalConfig(updated);
    onUpdateConfig(updated);
    setHasSaved(true);
    setTimeout(() => setHasSaved(false), 2500);
  };

  const handleExecuteControls = () => {
    setIsRunning(true);
    onRunControls();
    setTimeout(() => setIsRunning(false), 1200);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Control Settings &amp; Administration
              </h1>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold tracking-wider text-teal-800 border border-teal-200 uppercase">
                Deterministic Engine Rules
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Configure deterministic control boundaries (C01–C08), set exposure materiality cutoffs, and audit historical control runs.
              {isReadOnly && (
                <span className="ml-2 text-amber-700 font-semibold flex-inline items-center gap-1">
                  <Lock className="h-3 w-3 inline mr-1" />
                  (Read-Only Mode for Auditor)
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            {hasSaved && (
              <span className="text-xs text-emerald-700 font-medium flex items-center gap-1 animate-pulse">
                <CheckCircle2 className="h-4 w-4" /> Changes Applied
              </span>
            )}

            {!isReadOnly && (
              <button
                onClick={handleExecuteControls}
                disabled={isRunning}
                className="flex items-center gap-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 px-4 py-2 text-xs font-semibold text-white shadow-xs transition active:scale-95 cursor-pointer disabled:opacity-50"
              >
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>{isRunning ? 'Executing Controls...' : 'Run Financial Controls'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Deterministic Control Thresholds Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Sliders className="h-4 w-4 text-teal-600" />
              Configurable Deterministic Control Thresholds
            </h3>
            <p className="text-xs text-slate-500">
              Deterministic mathematical thresholds governing exception detection across billing, claims, and receivables.
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* C03 Amount Mismatch Tolerance */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-1.5">
            <div className="flex justify-between text-xs">
              <label className="font-semibold text-slate-800">C03: Tariff Mismatch Tolerance</label>
              <span className="font-mono font-bold text-teal-800">
                {localConfig.amountMismatchTolerancePercent}%
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              step="0.5"
              disabled={isReadOnly}
              value={localConfig.amountMismatchTolerancePercent}
              onChange={(e) =>
                handleSliderChange('amountMismatchTolerancePercent', parseFloat(e.target.value))
              }
              className="w-full accent-teal-600 cursor-pointer disabled:opacity-50"
            />
            <p className="text-[10px] text-slate-500">
              Deviations greater than this % trigger an amount mismatch exception.
            </p>
          </div>

          {/* C06 TPA Shortfall Tolerance */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-1.5">
            <div className="flex justify-between text-xs">
              <label className="font-semibold text-slate-800">C06: TPA Shortfall Tolerance</label>
              <span className="font-mono font-bold text-teal-700">
                {localConfig.tpaShortfallTolerancePercent}%
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              step="0.5"
              disabled={isReadOnly}
              value={localConfig.tpaShortfallTolerancePercent}
              onChange={(e) =>
                handleSliderChange('tpaShortfallTolerancePercent', parseFloat(e.target.value))
              }
              className="w-full accent-teal-600 cursor-pointer disabled:opacity-50"
            />
            <p className="text-[10px] text-slate-500">
              Disallowed claim amount % beyond this threshold flags a TPA shortfall.
            </p>
          </div>

          {/* C07 Collection Due Days */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-1.5">
            <div className="flex justify-between text-xs">
              <label className="font-semibold text-slate-800">C07: Collection Due Limit</label>
              <span className="font-mono font-bold text-emerald-800">
                {localConfig.collectionDueDays} Days
              </span>
            </div>
            <input
              type="range"
              min="7"
              max="90"
              step="1"
              disabled={isReadOnly}
              value={localConfig.collectionDueDays}
              onChange={(e) =>
                handleSliderChange('collectionDueDays', parseInt(e.target.value, 10))
              }
              className="w-full accent-emerald-600 cursor-pointer disabled:opacity-50"
            />
            <p className="text-[10px] text-slate-500">
              Receivables older than this post-discharge duration are flagged overdue.
            </p>
          </div>

          {/* C08 Unusual Discount */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-1.5">
            <div className="flex justify-between text-xs">
              <label className="font-semibold text-slate-800">C08: Unusual Discount Limit</label>
              <span className="font-mono font-bold text-amber-800">
                {localConfig.unusualDiscountPercent}%
              </span>
            </div>
            <input
              type="range"
              min="5"
              max="30"
              step="1"
              disabled={isReadOnly}
              value={localConfig.unusualDiscountPercent}
              onChange={(e) =>
                handleSliderChange('unusualDiscountPercent', parseFloat(e.target.value))
              }
              className="w-full accent-amber-600 cursor-pointer disabled:opacity-50"
            />
            <p className="text-[10px] text-slate-500">
              Any discount exceeding this percentage requires executive authorization.
            </p>
          </div>

          {/* Critical Severity Threshold (INR) */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-1.5">
            <div className="flex justify-between text-xs">
              <label className="font-semibold text-slate-800">Critical Exposure Cutoff</label>
              <span className="font-mono font-bold text-rose-700">
                {formatINR(localConfig.criticalExposureThreshold)}
              </span>
            </div>
            <input
              type="range"
              min="50000"
              max="1000000"
              step="25000"
              disabled={isReadOnly}
              value={localConfig.criticalExposureThreshold}
              onChange={(e) =>
                handleSliderChange('criticalExposureThreshold', parseFloat(e.target.value))
              }
              className="w-full accent-rose-600 cursor-pointer disabled:opacity-50"
            />
            <p className="text-[10px] text-slate-500">
              Exceptions above this exposure escalate automatically to CRITICAL.
            </p>
          </div>

          {/* High Severity Threshold (INR) */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-1.5">
            <div className="flex justify-between text-xs">
              <label className="font-semibold text-slate-800">High Exposure Cutoff</label>
              <span className="font-mono font-bold text-amber-800">
                {formatINR(localConfig.highExposureThreshold)}
              </span>
            </div>
            <input
              type="range"
              min="20000"
              max="500000"
              step="10000"
              disabled={isReadOnly}
              value={localConfig.highExposureThreshold}
              onChange={(e) =>
                handleSliderChange('highExposureThreshold', parseFloat(e.target.value))
              }
              className="w-full accent-amber-600 cursor-pointer disabled:opacity-50"
            />
            <p className="text-[10px] text-slate-500">
              Exceptions above this exposure escalate to HIGH.
            </p>
          </div>
        </div>
      </div>

      {/* Control Execution Audit Trail */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
          <FileCheck className="h-4 w-4 text-emerald-600" />
          Deterministic Control Engine Audit Trail
        </h3>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Run ID</th>
                <th className="py-2.5 px-3 font-semibold">Date / Time</th>
                <th className="py-2.5 px-3 font-semibold">Data Period</th>
                <th className="py-2.5 px-3 font-semibold text-center">Records Processed</th>
                <th className="py-2.5 px-3 font-semibold text-center">Controls Executed</th>
                <th className="py-2.5 px-3 font-semibold text-center">Exceptions Flagged</th>
                <th className="py-2.5 px-3 font-semibold">Auditor / User</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-[11px]">
              {auditTrail.map((log) => (
                <tr key={log.Run_ID} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-mono font-bold text-teal-800">{log.Run_ID}</td>
                  <td className="py-2.5 px-3 text-slate-600">{formatIndianDateTime(log.Run_Date_Time)}</td>
                  <td className="py-2.5 px-3 font-sans text-slate-800">{log.Data_Period}</td>
                  <td className="py-2.5 px-3 text-center text-slate-900">{log.Records_Processed}</td>
                  <td className="py-2.5 px-3 text-center text-teal-700 font-semibold">{log.Controls_Executed}</td>
                  <td className="py-2.5 px-3 text-center font-bold text-amber-900">
                    {log.Exceptions_Generated}
                  </td>
                  <td className="py-2.5 px-3 font-sans text-slate-700">{log.User}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
