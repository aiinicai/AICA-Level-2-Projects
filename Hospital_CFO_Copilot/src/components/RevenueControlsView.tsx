import React, { useState } from 'react';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  BarChart2,
  CheckCircle2,
  ChevronRight,
  Clock,
  DollarSign,
  Download,
  ExternalLink,
  Eye,
  FileCheck,
  FileSpreadsheet,
  Filter,
  Layers,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import {
  Billing,
  Claim,
  Collection,
  DashboardMetrics,
  DischargeMonitorRow,
  Encounter,
  ExceptionStatus,
  FinancialException,
  HospitalDepartment,
  Service,
  UserRole,
  UserSession,
} from '../types';
import { formatINR } from '../utils/formatters';
import { DischargeFinancialView } from './DischargeFinancialView';
import { DischargeMonitorView } from './DischargeMonitorView';
import { ExceptionsView } from './ExceptionsView';
import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface RevenueControlsViewProps {
  metrics: DashboardMetrics;
  exceptions: FinancialException[];
  encounters: Encounter[];
  services: Service[];
  billings: Billing[];
  claims: Claim[];
  collections: Collection[];
  dischargeMonitor: DischargeMonitorRow[];
  currentUser: UserSession;
  selectedEncounterId: string | null;
  selectedException: FinancialException | null;
  onSelectEncounter: (encounterId: string | null) => void;
  onSelectException: (exc: FinancialException | null) => void;
  onNavigateToTab?: (tabId: string) => void;
  onUpdateException: (
    exceptionId: string,
    updates: {
      status: ExceptionStatus;
      assignedTo: string;
      resolution: string;
    }
  ) => void;
}

export const RevenueControlsView: React.FC<RevenueControlsViewProps> = ({
  metrics,
  exceptions,
  encounters,
  services,
  billings,
  claims,
  collections,
  dischargeMonitor,
  currentUser,
  selectedEncounterId,
  selectedException,
  onSelectEncounter,
  onSelectException,
  onNavigateToTab,
  onUpdateException,
}) => {
  // Sub-tabs: 'exceptions' | 'review-queue' | 'performance'
  const [activeSubTab, setActiveSubTab] = useState<'exceptions' | 'review-queue' | 'performance'>('exceptions');

  // If a department manager is viewing, filter exceptions to their department
  const isDeptManager = currentUser.role === 'Department Manager';
  const userDept = currentUser.department;

  const relevantExceptions = isDeptManager && userDept
    ? exceptions.filter((exc) => {
        const enc = encounters.find((e) => e.Encounter_ID === exc.Encounter_ID);
        return enc?.Department === userDept || exc.Revenue_Centre.includes(userDept);
      })
    : exceptions;

  const relevantEncounters = isDeptManager && userDept
    ? encounters.filter((e) => e.Department === userDept)
    : encounters;

  const relevantMonitorRows = isDeptManager && userDept
    ? dischargeMonitor.filter((r) => r.Department === userDept)
    : dischargeMonitor;

  if (billings.length === 0 && services.length === 0 && encounters.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Billing &amp; Revenue Controls
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Deterministic rule execution across unbilled charges, quantity variances, billing amount variances and receivables ageing thresholds.
          </p>
        </div>
        <EmptyWorkspaceState
          title="No billing data available."
          description="Upload your hospital financial extracts to begin billing and revenue controls analysis."
          badge="Controls Inactive"
          actionText="Upload Hospital Financial Extracts"
          onAction={() => onNavigateToTab?.('data-intelligence')}
        />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Top Banner & Sub-Navigation */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Billing &amp; Revenue Controls
              </h1>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold tracking-wider text-teal-800 border border-teal-200 uppercase">
                Deterministic C01–C08 Control Engine
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Deterministic rule execution across unbilled charges, quantity variances, billing amount variances and receivables ageing thresholds.
              {isDeptManager && (
                <span className="ml-1 text-teal-700 font-bold">
                  (Filtered to your department: {userDept})
                </span>
              )}
            </p>
          </div>

          <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-semibold">
            <button
              onClick={() => {
                setActiveSubTab('exceptions');
                onSelectEncounter(null);
              }}
              className={`rounded-md px-3.5 py-1.5 transition cursor-pointer ${
                activeSubTab === 'exceptions' && !selectedEncounterId
                  ? 'bg-white text-teal-800 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Exceptions Desk ({relevantExceptions.length})
            </button>
            <button
              onClick={() => {
                setActiveSubTab('review-queue');
              }}
              className={`rounded-md px-3.5 py-1.5 transition cursor-pointer ${
                activeSubTab === 'review-queue' || selectedEncounterId
                  ? 'bg-white text-teal-800 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Financial Review Queue
            </button>
            <button
              onClick={() => {
                setActiveSubTab('performance');
                onSelectEncounter(null);
              }}
              className={`rounded-md px-3.5 py-1.5 transition cursor-pointer ${
                activeSubTab === 'performance' && !selectedEncounterId
                  ? 'bg-white text-teal-800 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Control Engine Performance
            </button>
          </div>
        </div>

        {/* 8 Controls Quick Summary Chips */}
        <div className="mt-4 pt-3 border-t border-slate-100 flex overflow-x-auto gap-2 scrollbar-none text-xs">
          {metrics.exceptionsByControl.map((c) => (
            <div
              key={c.controlId}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 shrink-0 flex items-center gap-2"
            >
              <span className="font-mono font-bold text-teal-800 text-[11px]">{c.controlId}</span>
              <span className="text-[11px] text-slate-700 font-medium">{c.title.split(' ')[0]}</span>
              <span
                className={`font-bold px-1.5 rounded text-[10px] ${
                  c.count > 0 ? 'bg-amber-100 text-amber-900' : 'bg-slate-200 text-slate-600'
                }`}
              >
                {c.count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {encounters.length === 0 && billings.length === 0 ? (
        <EmptyWorkspaceState
          title="No Revenue Control Records"
          description="No encounter or billing records have been imported yet. Import your hospital extracts to run the deterministic C01–C08 control engine and monitor revenue leakages."
          badge="C01–C08 Control Engine"
          actionText="Upload Financial Extracts"
          onAction={onNavigateToTab ? () => onNavigateToTab('data-intelligence') : undefined}
        />
      ) : (
        <>
          {/* VIEW: ENCOUNTER DETAIL LINE-ITEM VIEW */}
          {selectedEncounterId ? (
        <DischargeFinancialView
          encounterId={selectedEncounterId}
          encounters={encounters}
          services={services}
          billings={billings}
          claims={claims}
          collections={collections}
          exceptions={exceptions}
          userRole={currentUser.role}
          onBackToMonitor={() => onSelectEncounter(null)}
          onUpdateException={onUpdateException}
          onSelectEncounter={onSelectEncounter}
        />
      ) : activeSubTab === 'exceptions' ? (
        <ExceptionsView
          exceptions={relevantExceptions}
          encounters={relevantEncounters}
          userRole={currentUser.role}
          selectedException={selectedException}
          onSelectException={onSelectException}
          onSelectEncounter={(encId) => {
            onSelectEncounter(encId);
          }}
          onUpdateException={onUpdateException}
        />
      ) : activeSubTab === 'review-queue' ? (
        <DischargeMonitorView
          rows={relevantMonitorRows}
          onSelectEncounter={(encId) => onSelectEncounter(encId)}
        />
      ) : (
        /* Performance & Control Analysis Tab */
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Control Statistics Card */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
              <h2 className="text-sm font-bold text-slate-900 mb-1">
                Deterministic C01–C08 Control Performance
              </h2>
              <p className="text-xs text-slate-500 mb-4">
                Distribution of identified financial leakage by control rule
              </p>
              <div className="space-y-3 text-xs">
                {metrics.exceptionsByControl.map((c) => (
                  <div key={c.controlId} className="space-y-1">
                    <div className="flex justify-between font-medium">
                      <span className="text-slate-800">
                        <strong className="text-teal-800 font-mono mr-1.5">{c.controlId}</strong>
                        {c.title}
                      </span>
                      <span className="font-bold text-slate-900">
                        {formatINR(c.exposure)}{' '}
                        <span className="text-slate-400 font-normal">({c.count} items)</span>
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div
                        className="bg-teal-700 h-1.5 rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            (c.exposure / (metrics.potentialFinancialExposure || 1)) * 100
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Department Exposure Performance Card */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
              <h2 className="text-sm font-bold text-slate-900 mb-1">
                Clinical Department Exception Frequency
              </h2>
              <p className="text-xs text-slate-500 mb-4">
                Leakage risk mapped to clinical units
              </p>
              <div className="space-y-3 text-xs">
                {metrics.exceptionsByDepartment.map((d) => (
                  <div key={d.department} className="space-y-1">
                    <div className="flex justify-between font-medium">
                      <span className="text-slate-800">{d.department}</span>
                      <span className="font-bold text-slate-900">
                        {formatINR(d.exposure)}{' '}
                        <span className="text-slate-400 font-normal">({d.count} exceptions)</span>
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div
                        className="bg-amber-600 h-1.5 rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            (d.exposure / (metrics.potentialFinancialExposure || 1)) * 100
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
};
