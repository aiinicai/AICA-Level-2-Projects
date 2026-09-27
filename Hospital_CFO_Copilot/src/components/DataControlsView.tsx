import React, { useState } from 'react';
import {
  Billing,
  Claim,
  Collection,
  Encounter,
  Service,
  ControlRuleConfig,
  AuditTrailRun,
  UserSession,
} from '../types';
import {
  Sliders,
  Play,
  RotateCcw,
  FileSpreadsheet,
  FileCheck,
  Database,
  Download,
  AlertTriangle,
} from 'lucide-react';
import { exportAllDatasetsToXLSX, exportDatasetToCSV } from '../utils/fileImport';
import { formatIndianDateTime, formatINR } from '../utils/formatters';
import { DynamicIngestionWizard } from './DynamicIngestionWizard';
import { CanonicalDatasetType } from '../types/ingestion';

interface DataControlsViewProps {
  encounters: Encounter[];
  services: Service[];
  billings: Billing[];
  claims: Claim[];
  collections: Collection[];
  config: ControlRuleConfig;
  auditTrail: AuditTrailRun[];
  currentUser: UserSession;
  onUpdateConfig: (newConfig: ControlRuleConfig) => void;
  onUpdateDataset: (
    datasetType: 'encounters' | 'services' | 'billing' | 'claims' | 'collections',
    data: unknown[]
  ) => void;
  onRunControls: () => void;
  onResetStandardData: () => void;
}

export const DataControlsView: React.FC<DataControlsViewProps> = ({
  encounters,
  services,
  billings,
  claims,
  collections,
  config,
  auditTrail,
  currentUser,
  onUpdateConfig,
  onUpdateDataset,
  onRunControls,
  onResetStandardData,
}) => {
  const [activePeriod, setActivePeriod] = useState('September 2026');
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  const handleDynamicDatasetUpdate = (datasetType: CanonicalDatasetType, records: unknown[]) => {
    if (
      datasetType === 'encounters' ||
      datasetType === 'services' ||
      datasetType === 'billing' ||
      datasetType === 'claims' ||
      datasetType === 'collections'
    ) {
      onUpdateDataset(datasetType, records);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Control Actions */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Database className="h-5 w-5 text-teal-600" />
              Hospital Financial Data Intelligence &amp; Control Engine
            </h2>
            <p className="text-xs text-slate-500">
              Manage multi-file tabular data ingestion, customize deterministic control thresholds, and audit engine runs.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <select
              value={activePeriod}
              onChange={(e) => setActivePeriod(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none cursor-pointer"
            >
              <option value="September 2026">September 2026 (Active Accounting Cycle)</option>
              <option value="August 2026">August 2026 (Closed Period)</option>
              <option value="Q3 2026">Q3 2026 Consolidated</option>
            </select>

            <button
              onClick={onRunControls}
              className="flex items-center gap-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 px-4 py-1.5 text-xs font-semibold text-white shadow-xs transition active:scale-95 cursor-pointer"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>Run Financial Controls</span>
            </button>

            <button
              onClick={() =>
                exportAllDatasetsToXLSX(encounters, services, billings, claims, collections)
              }
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 transition shadow-2xs cursor-pointer"
              title="Download consolidated Excel workbook with 5 canonical sheets"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
              <span>Export Consolidated XLSX</span>
            </button>

            {(currentUser.role === 'CFO' || currentUser.role === 'Finance/Billing Manager') && (
              <button
                onClick={() => setShowResetConfirm(true)}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 px-2 py-1 rounded hover:bg-slate-100 transition cursor-pointer"
                title="Reset Standard Ingestion Datasets"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Reset Master Records</span>
              </button>
            )}
          </div>
        </div>

        {/* Current Ingested Counts Strip */}
        <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-600">
          <span className="font-semibold text-slate-800">Current Ingested Records:</span>
          <span className="flex items-center gap-1">
            <span className="font-medium text-slate-500">Encounters:</span>
            <span className="font-bold text-teal-800 font-mono">{encounters.length}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="font-medium text-slate-500">Services:</span>
            <span className="font-bold text-teal-800 font-mono">{services.length}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="font-medium text-slate-500">Billing:</span>
            <span className="font-bold text-teal-800 font-mono">{billings.length}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="font-medium text-slate-500">Claims:</span>
            <span className="font-bold text-teal-800 font-mono">{claims.length}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="font-medium text-slate-500">Collections:</span>
            <span className="font-bold text-teal-800 font-mono">{collections.length}</span>
          </span>
        </div>
      </div>

      {/* DYNAMIC INGESTION & SEMANTIC MAPPING ENGINE */}
      <DynamicIngestionWizard
        currentUser={currentUser}
        onRunControlsAfterImport={onRunControls}
        onUpdateDatasetInApp={handleDynamicDatasetUpdate}
      />

      {/* Configurable Deterministic Control Thresholds */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Sliders className="h-4 w-4 text-teal-600" />
              Configurable Deterministic Control Thresholds
            </h3>
            <p className="text-xs text-slate-500">
              Customize tolerance boundaries for controls C01 through C08. Deterministic math only.
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* C03 Amount Mismatch Tolerance */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 space-y-1.5">
            <div className="flex justify-between text-xs">
              <label className="font-semibold text-slate-800">C03: Tariff Mismatch Tolerance</label>
              <span className="font-mono font-bold text-teal-800">
                {config.amountMismatchTolerancePercent}%
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              step="0.5"
              value={config.amountMismatchTolerancePercent}
              onChange={(e) =>
                onUpdateConfig({
                  ...config,
                  amountMismatchTolerancePercent: parseFloat(e.target.value),
                })
              }
              className="w-full accent-teal-600 cursor-pointer"
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
                {config.tpaShortfallTolerancePercent}%
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              step="0.5"
              value={config.tpaShortfallTolerancePercent}
              onChange={(e) =>
                onUpdateConfig({
                  ...config,
                  tpaShortfallTolerancePercent: parseFloat(e.target.value),
                })
              }
              className="w-full accent-teal-600 cursor-pointer"
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
                {config.collectionDueDays} Days
              </span>
            </div>
            <input
              type="range"
              min="7"
              max="90"
              step="1"
              value={config.collectionDueDays}
              onChange={(e) =>
                onUpdateConfig({
                  ...config,
                  collectionDueDays: parseInt(e.target.value, 10),
                })
              }
              className="w-full accent-emerald-600 cursor-pointer"
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
                {config.unusualDiscountPercent}%
              </span>
            </div>
            <input
              type="range"
              min="5"
              max="30"
              step="1"
              value={config.unusualDiscountPercent}
              onChange={(e) =>
                onUpdateConfig({
                  ...config,
                  unusualDiscountPercent: parseFloat(e.target.value),
                })
              }
              className="w-full accent-amber-600 cursor-pointer"
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
                {formatINR(config.criticalExposureThreshold)}
              </span>
            </div>
            <input
              type="range"
              min="50000"
              max="1000000"
              step="25000"
              value={config.criticalExposureThreshold}
              onChange={(e) =>
                onUpdateConfig({
                  ...config,
                  criticalExposureThreshold: parseFloat(e.target.value),
                })
              }
              className="w-full accent-rose-600 cursor-pointer"
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
                {formatINR(config.highExposureThreshold)}
              </span>
            </div>
            <input
              type="range"
              min="20000"
              max="500000"
              step="10000"
              value={config.highExposureThreshold}
              onChange={(e) =>
                onUpdateConfig({
                  ...config,
                  highExposureThreshold: parseFloat(e.target.value),
                })
              }
              className="w-full accent-amber-600 cursor-pointer"
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

      {/* Confirmation Modal for Reset Baseline */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-amber-600">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-base font-bold text-slate-900">Reset Standard Master Records?</h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              This action will reset the active Firestore database collections to verified hospital accounting records and trigger a fresh C01–C08 control run.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowResetConfirm(false)}
                className="px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowResetConfirm(false);
                  onResetStandardData();
                }}
                className="px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold transition active:scale-95 cursor-pointer"
              >
                Confirm Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
