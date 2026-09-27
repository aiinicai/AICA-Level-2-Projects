import React, { useState, useMemo } from 'react';
import {
  AlertTriangle,
  Building,
  CheckCircle2,
  ChevronLeft,
  CreditCard,
  FileCheck,
  FileText,
  ShieldAlert,
} from 'lucide-react';
import {
  Billing,
  Claim,
  Collection,
  Encounter,
  ExceptionStatus,
  FinancialException,
  Service,
  UserRole,
} from '../types';
import { formatIndianDate, formatIndianDateTime, formatINR } from '../utils/formatters';

interface DischargeFinancialViewProps {
  encounterId: string;
  encounters: Encounter[];
  services: Service[];
  billings: Billing[];
  claims: Claim[];
  collections: Collection[];
  exceptions: FinancialException[];
  userRole: UserRole;
  onBackToMonitor: () => void;
  onUpdateException: (
    exceptionId: string,
    updates: {
      status: ExceptionStatus;
      assignedTo: string;
      resolution: string;
    }
  ) => void;
  onSelectEncounter: (encounterId: string) => void;
}

export const DischargeFinancialView: React.FC<DischargeFinancialViewProps> = ({
  encounterId,
  encounters,
  services,
  billings,
  claims,
  collections,
  exceptions,
  userRole,
  onBackToMonitor,
  onUpdateException,
  onSelectEncounter,
}) => {
  const currentEncounter = encounters.find((e) => e.Encounter_ID === encounterId) || encounters[0];
  const activeEncId = currentEncounter?.Encounter_ID || encounterId;

  // Deduplicate encounters list for selector
  const uniqueEncounters = useMemo(() => {
    const seen = new Set<string>();
    return encounters.filter((e) => {
      if (!e.Encounter_ID || seen.has(e.Encounter_ID)) return false;
      seen.add(e.Encounter_ID);
      return true;
    });
  }, [encounters]);

  // Filter dataset for this encounter
  const encServices = services.filter((s) => s.Encounter_ID === activeEncId);
  const encBillings = billings.filter((b) => b.Encounter_ID === activeEncId);
  const encClaims = claims.filter((c) => c.Encounter_ID === activeEncId);
  const encCollections = collections.filter((c) => c.Encounter_ID === activeEncId);
  const encExceptions = exceptions.filter((e) => e.Encounter_ID === activeEncId);

  // Financial aggregates
  const totalExpected = encServices.reduce((sum, s) => sum + s.Expected_Amount, 0);
  const totalBilled = encBillings.reduce((sum, b) => sum + b.Billed_Amount, 0);
  const totalDiscount = encBillings.reduce((sum, b) => sum + b.Discount, 0);
  const billedVariance = totalExpected - totalBilled;

  const totalClaimed = encClaims.reduce((sum, c) => sum + c.Claim_Amount, 0);
  const totalApproved = encClaims.reduce((sum, c) => sum + c.Approved_Amount, 0);
  const tpaShortfall = Math.max(0, totalClaimed - totalApproved);

  const totalCollected = encCollections.reduce((sum, c) => sum + c.Amount, 0);
  const outstandingBalance = Math.max(0, totalBilled - totalCollected);

  const totalPotentialExposure = encExceptions
    .filter((e) => e.Status === 'OPEN' || e.Status === 'UNDER_REVIEW')
    .reduce((sum, e) => sum + e.Exposure_Amount, 0);

  // Group by Revenue Centre
  const revCenters = Array.from(
    new Set([...encServices.map((s) => s.Revenue_Centre), ...encBillings.map(() => 'Billing / Finance')])
  );

  const revCenterBreakdown = revCenters.map((rc) => {
    const rcSvcs = encServices.filter((s) => s.Revenue_Centre === rc);
    const rcSvcIds = new Set(rcSvcs.map((s) => s.Service_ID));
    const rcBills = encBillings.filter(
      (b) => rcSvcIds.has(b.Service_ID) || (!b.Service_ID && rc === 'Billing / Finance')
    );

    const expected = rcSvcs.reduce((sum, s) => sum + s.Expected_Amount, 0);
    const billed = rcBills.reduce((sum, b) => sum + b.Billed_Amount, 0);
    const variance = expected - billed;

    return {
      revenueCentre: rc,
      serviceCount: rcSvcs.length,
      expected,
      billed,
      variance,
      hasDiscrepancy: variance !== 0,
    };
  });

  // State for active editing exception in modal/section
  const [editingExceptionId, setEditingExceptionId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState<ExceptionStatus>('OPEN');
  const [editAssignedTo, setEditAssignedTo] = useState('');
  const [editResolution, setEditResolution] = useState('');

  const handleStartEdit = (exc: FinancialException) => {
    setEditingExceptionId(exc.Exception_ID);
    setEditStatus(exc.Status);
    setEditAssignedTo(exc.Assigned_To);
    setEditResolution(exc.Resolution || '');
  };

  const handleSaveEdit = (excId: string) => {
    onUpdateException(excId, {
      status: editStatus,
      assignedTo: editAssignedTo,
      resolution: editResolution,
    });
    setEditingExceptionId(null);
  };

  return (
    <div className="space-y-6">
      {/* Top Navigation & Encounter Selector Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToMonitor}
            className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-700 transition shadow-2xs cursor-pointer"
          >
            <ChevronLeft className="h-4 w-4" />
            <span>Discharge Monitor</span>
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Encounter:</span>
              <select
                value={activeEncId}
                onChange={(e) => onSelectEncounter(e.target.value)}
                className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-sm font-bold font-mono text-teal-800 focus:outline-none cursor-pointer"
              >
                {uniqueEncounters.map((e, idx) => (
                  <option key={`${e.Encounter_ID}-${idx}`} value={e.Encounter_ID}>
                    {e.Encounter_ID} — {e.Department} ({e.Discharge_Status})
                  </option>
                ))}
              </select>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Comprehensive Financial Reconciliation &amp; Exception Resolution View
            </p>
          </div>
        </div>

        {/* Potential Exposure Warning Badge */}
        {totalPotentialExposure > 0 ? (
          <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-1.5 text-xs text-amber-900 shadow-2xs">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <span>
              Potential Financial Impact: <strong className="text-amber-900">{formatINR(totalPotentialExposure)}</strong> ({encExceptions.filter(e => e.Status === 'OPEN' || e.Status === 'UNDER_REVIEW').length} active)
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs text-emerald-800 font-medium shadow-2xs">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>Billing Cleared &amp; Verified &bull; No Unresolved Financial Impact</span>
          </div>
        )}
      </div>

      {/* Encounter Metadata Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6 rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-500">Department</span>
          <div className="text-xs font-bold text-slate-900 mt-0.5">{currentEncounter.Department}</div>
        </div>
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-500">Ward &amp; Bed</span>
          <div className="text-xs font-semibold text-slate-700 mt-0.5">
            {currentEncounter.Ward} ({currentEncounter.Bed_Type})
          </div>
        </div>
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-500">Payer Type</span>
          <div className="text-xs font-semibold text-teal-800 mt-0.5">{currentEncounter.Payer_Type}</div>
        </div>
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-500">Admission Date</span>
          <div className="text-xs font-semibold text-slate-700 mt-0.5">
            {formatIndianDate(currentEncounter.Admission_Date)}
          </div>
        </div>
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-500">Discharge Date</span>
          <div className="text-xs font-semibold text-slate-700 mt-0.5">
            {currentEncounter.Discharge_Date ? formatIndianDate(currentEncounter.Discharge_Date) : 'Currently Inpatient'}
          </div>
        </div>
        <div>
          <span className="text-[10px] uppercase font-bold text-slate-500">Status</span>
          <div className="mt-0.5">
            <span
              className={`inline-flex rounded px-2 py-0.5 text-[10px] font-bold ${
                currentEncounter.Discharge_Status === 'Discharged'
                  ? 'bg-slate-100 text-slate-800 border border-slate-200'
                  : 'bg-teal-50 text-teal-800 border border-teal-200'
              }`}
            >
              {currentEncounter.Discharge_Status}
            </span>
          </div>
        </div>
      </div>

      {/* Financial Summary 5-Box Metric Bar */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {/* Box 1: Expected Tariff */}
        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase">1. Services Captured</span>
          <div className="text-lg font-bold text-slate-900 mt-1">{formatINR(totalExpected)}</div>
          <span className="text-[10px] text-slate-500">{encServices.length} clinical tariffs</span>
        </div>

        {/* Box 2: Billed Amount */}
        <div className="rounded-xl border border-teal-200 bg-teal-50/40 p-3.5 shadow-xs">
          <span className="text-[11px] font-semibold text-teal-800 uppercase">2. Gross Billed</span>
          <div className="text-lg font-bold text-teal-950 mt-1">{formatINR(totalBilled)}</div>
          <div className="text-[10px] text-teal-700 font-medium">
            Variance: {formatINR(billedVariance)} {totalDiscount > 0 && `(Disc: ${formatINR(totalDiscount)})`}
          </div>
        </div>

        {/* Box 3: Claimed vs Approved */}
        <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase">3. TPA Claimed</span>
          <div className="text-lg font-bold text-slate-900 mt-1">{formatINR(totalClaimed)}</div>
          <div className="text-[10px] text-amber-800 font-medium">
            Approved: {formatINR(totalApproved)} {tpaShortfall > 0 && `(Shortfall: ${formatINR(tpaShortfall)})`}
          </div>
        </div>

        {/* Box 4: Collected */}
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-3.5 shadow-xs">
          <span className="text-[11px] font-semibold text-emerald-800 uppercase">4. Collections Received</span>
          <div className="text-lg font-bold text-emerald-950 mt-1">{formatINR(totalCollected)}</div>
          <div className="text-[10px] text-emerald-700 font-medium">{encCollections.length} receipt payment(s)</div>
        </div>

        {/* Box 5: Outstanding Balance */}
        <div className="rounded-xl border border-rose-200 bg-rose-50/40 p-3.5 shadow-xs">
          <span className="text-[11px] font-semibold text-rose-800 uppercase">5. Outstanding AR</span>
          <div className="text-lg font-bold text-rose-900 mt-1">{formatINR(outstandingBalance)}</div>
          <div className="text-[10px] text-rose-700 font-medium">Net uncollected balance</div>
        </div>
      </div>

      {/* Related Exceptions Section with Live Resolution Controls */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-amber-600" />
              Related Financial Exceptions on this Encounter ({encExceptions.length})
            </h3>
            <p className="text-xs text-slate-500">
              Deterministic control engine findings. Role: <span className="text-teal-700 font-semibold">{userRole}</span>. Exceptions can be assigned, resolved, or accepted with audit trail notes.
            </p>
          </div>
        </div>

        {encExceptions.length === 0 ? (
          <div className="py-6 text-center text-xs text-slate-500">
            <CheckCircle2 className="mx-auto h-5 w-5 text-emerald-600 mb-1" />
            No exceptions triggered on this encounter. All controls cleared.
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            {encExceptions.map((exc, idx) => {
              const isEditing = editingExceptionId === exc.Exception_ID;
              const isCrit = exc.Severity === 'CRITICAL';
              const isHigh = exc.Severity === 'HIGH';

              return (
                <div
                  key={`${exc.Exception_ID}-${idx}`}
                  className={`rounded-lg border p-4 transition ${
                    isCrit
                      ? 'border-rose-200 bg-rose-50/50'
                      : isHigh
                      ? 'border-amber-200 bg-amber-50/50'
                      : 'border-slate-200 bg-slate-50'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                            isCrit
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : isHigh
                              ? 'bg-amber-50 text-amber-800 border border-amber-200'
                              : 'bg-slate-100 text-slate-700 border border-slate-200'
                          }`}
                        >
                          {exc.Severity}
                        </span>
                        <span className="font-mono text-xs font-bold text-teal-800">
                          {exc.Exception_ID}
                        </span>
                        <span className="font-mono text-xs text-slate-600 font-semibold bg-white px-1.5 py-0.5 rounded border border-slate-200">
                          Control: {exc.Control_ID}
                        </span>
                        <span className="text-xs font-semibold text-slate-800">
                          {exc.Revenue_Centre}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed max-w-3xl">
                        {exc.Description}
                      </p>
                      <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 pt-1">
                        <span>Created: <strong className="text-slate-700">{formatIndianDate(exc.Created_Date)}</strong></span>
                        <span>Assigned To: <strong className="text-slate-700">{exc.Assigned_To || 'Unassigned'}</strong></span>
                        {exc.Resolution && (
                          <span>Resolution Note: <em className="text-emerald-700 font-medium">"{exc.Resolution}"</em></span>
                        )}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-xs uppercase font-medium text-slate-500">Potential Exposure</div>
                      <div className="text-base font-extrabold text-amber-900">
                        {formatINR(exc.Exposure_Amount)}
                      </div>
                      <div className="mt-1">
                        <span
                          className={`inline-flex rounded px-2 py-0.5 text-[10px] font-bold ${
                            exc.Status === 'RESOLVED'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : exc.Status === 'UNDER_REVIEW'
                              ? 'bg-sky-50 text-sky-800 border border-sky-200'
                              : exc.Status === 'ACCEPTED'
                              ? 'bg-purple-50 text-purple-800 border border-purple-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {exc.Status}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Resolution Controls inline */}
                  <div className="mt-3 pt-3 border-t border-slate-200/80 flex flex-wrap items-center justify-between gap-2">
                    {isEditing ? (
                      <div className="w-full space-y-3 bg-white p-3 rounded-lg border border-slate-300 shadow-xs">
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                          <div>
                            <label className="text-[10px] uppercase font-bold text-slate-600">Change Status</label>
                            <select
                              value={editStatus}
                              onChange={(e) => setEditStatus(e.target.value as ExceptionStatus)}
                              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800"
                            >
                              <option value="OPEN">OPEN</option>
                              <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                              <option value="RESOLVED">RESOLVED</option>
                              <option value="ACCEPTED">ACCEPTED (Risk Accepted)</option>
                            </select>
                          </div>
                          <div>
                            <label className="text-[10px] uppercase font-bold text-slate-600">Assign To</label>
                            <input
                              type="text"
                              value={editAssignedTo}
                              onChange={(e) => setEditAssignedTo(e.target.value)}
                              placeholder="e.g. Billing Lead / Duty Manager / TPA Desk"
                              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="text-[10px] uppercase font-bold text-slate-600">Resolution Rationale / Audit Log</label>
                          <input
                            type="text"
                            value={editResolution}
                            onChange={(e) => setEditResolution(e.target.value)}
                            placeholder="Reason for change, tariff verified, invoice re-issued, etc."
                            className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800"
                          />
                        </div>
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setEditingExceptionId(null)}
                            className="rounded px-2.5 py-1 text-xs text-slate-600 hover:text-slate-900 cursor-pointer"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleSaveEdit(exc.Exception_ID)}
                            className="rounded bg-teal-700 hover:bg-teal-800 px-3 py-1 text-xs font-semibold text-white transition cursor-pointer"
                          >
                            Save Audit Entry
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleStartEdit(exc)}
                          className="rounded border border-slate-300 bg-white hover:bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 transition shadow-2xs cursor-pointer"
                        >
                          Update Status / Resolution
                        </button>
                        {exc.Status !== 'RESOLVED' && (
                          <button
                            onClick={() => {
                              onUpdateException(exc.Exception_ID, {
                                status: 'RESOLVED',
                                assignedTo: userRole,
                                resolution: `Marked resolved by ${userRole} after line-item tariff reconciliation`,
                              });
                            }}
                            className="rounded border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800 transition shadow-2xs cursor-pointer"
                          >
                            Quick Mark Resolved
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Revenue Centre Breakdown Table */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
          <Building className="h-4 w-4 text-teal-600" />
          Revenue-Centre-wise Expected vs Billed vs Variance
        </h3>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Revenue Centre</th>
                <th className="py-2.5 px-3 font-semibold text-center">Items Captured</th>
                <th className="py-2.5 px-3 font-semibold text-right">Expected Amount</th>
                <th className="py-2.5 px-3 font-semibold text-right">Billed Amount</th>
                <th className="py-2.5 px-3 font-semibold text-right">Variance</th>
                <th className="py-2.5 px-3 font-semibold text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {revCenterBreakdown.map((row) => (
                <tr key={row.revenueCentre} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-semibold text-slate-800">{row.revenueCentre}</td>
                  <td className="py-2.5 px-3 text-center text-slate-500">{row.serviceCount}</td>
                  <td className="py-2.5 px-3 text-right font-medium text-slate-900">
                    {formatINR(row.expected)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-medium text-teal-800">
                    {formatINR(row.billed)}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${row.variance > 0 ? 'text-amber-900' : 'text-slate-500'}`}>
                    {formatINR(row.variance)}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    {row.hasDiscrepancy ? (
                      <span className="rounded bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
                        Variance Discrepancy
                      </span>
                    ) : (
                      <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200">
                        Balanced
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Services vs Billing Detailed Reconciliation Table */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
          <FileText className="h-4 w-4 text-emerald-600" />
          Clinical Service Capture &amp; Invoicing Line-Item Audit
        </h3>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Service Code</th>
                <th className="py-2.5 px-3 font-semibold">Description</th>
                <th className="py-2.5 px-3 font-semibold">Revenue Centre</th>
                <th className="py-2.5 px-3 font-semibold">Captured Date &amp; Time</th>
                <th className="py-2.5 px-3 font-semibold text-center">Qty (Cap/Bill)</th>
                <th className="py-2.5 px-3 font-semibold text-right">Expected Tariff</th>
                <th className="py-2.5 px-3 font-semibold text-right">Billed Amount</th>
                <th className="py-2.5 px-3 font-semibold text-center">Billing Match</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {encServices.map((svc) => {
                const bill = encBillings.find((b) => b.Service_ID === svc.Service_ID);
                const billedAmount = bill ? bill.Billed_Amount : 0;
                const billedQty = bill ? bill.Billed_Quantity : 0;
                const isBilled = !!bill;
                const hasVariance = svc.Expected_Amount !== billedAmount || svc.Quantity !== billedQty;

                return (
                  <tr key={svc.Service_ID} className="hover:bg-slate-50">
                    <td className="py-2.5 px-3 font-mono font-medium text-teal-800">{svc.Service_Code}</td>
                    <td className="py-2.5 px-3 font-medium text-slate-800">{svc.Description}</td>
                    <td className="py-2.5 px-3 text-slate-500">{svc.Revenue_Centre}</td>
                    <td className="py-2.5 px-3 text-slate-600 text-[11px]">{formatIndianDateTime(svc.Service_DateTime)}</td>
                    <td className="py-2.5 px-3 text-center font-mono">
                      <span className="text-slate-900 font-semibold">{svc.Quantity}</span> / <span className={billedQty !== svc.Quantity ? 'text-amber-800 font-bold' : 'text-slate-500'}>{isBilled ? billedQty : 0}</span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-slate-900">{formatINR(svc.Expected_Amount)}</td>
                    <td className="py-2.5 px-3 text-right font-medium text-teal-800">
                      {isBilled ? formatINR(billedAmount) : <span className="text-rose-600 font-bold">₹0</span>}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {!isBilled ? (
                        <span className="rounded bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-700 border border-rose-200">
                          Unbilled (C01)
                        </span>
                      ) : hasVariance ? (
                        <span className="rounded bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
                          Mismatch
                        </span>
                      ) : (
                        <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200">
                          Matched
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Claims and Collections Sub-Panels */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* TPA Claims Sub-Panel */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <FileCheck className="h-4 w-4 text-sky-600" />
            TPA Insurance Claims ({encClaims.length})
          </h3>
          <div className="mt-3 space-y-3">
            {encClaims.length === 0 ? (
              <p className="py-4 text-center text-xs text-slate-400">
                No TPA claims submitted for this encounter (Non-insurance / Self Pay).
              </p>
            ) : (
              encClaims.map((claim) => (
                <div key={claim.Claim_ID} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="font-mono font-bold text-teal-800">{claim.Claim_ID}</span>
                    <span className="rounded bg-sky-50 px-2 py-0.5 text-[10px] font-bold text-sky-800 border border-sky-200">
                      {claim.Claim_Status}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 pt-1 font-mono">
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-sans">Claimed</div>
                      <div className="text-slate-900 font-bold">{formatINR(claim.Claim_Amount)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-sans">Approved</div>
                      <div className="text-emerald-700 font-bold">{formatINR(claim.Approved_Amount)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-sans">Shortfall</div>
                      <div className={`font-bold ${claim.Rejected_Amount > 0 ? 'text-rose-700' : 'text-slate-500'}`}>
                        {formatINR(claim.Rejected_Amount)}
                      </div>
                    </div>
                  </div>
                  <div className="text-[10px] text-slate-500 flex justify-between pt-1 border-t border-slate-200">
                    <span>Submitted: {formatIndianDate(claim.Submission_Date)}</span>
                    <span>Approved: {claim.Approval_Date ? formatIndianDate(claim.Approval_Date) : 'Pending'}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Collections Sub-Panel */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <CreditCard className="h-4 w-4 text-emerald-600" />
            Receipts &amp; Payments Collected ({encCollections.length})
          </h3>
          <div className="mt-3 space-y-2.5">
            {encCollections.length === 0 ? (
              <p className="py-4 text-center text-xs text-rose-600">
                Zero collections recorded. Outstanding balance: {formatINR(outstandingBalance)}
              </p>
            ) : (
              encCollections.map((col) => (
                <div key={col.Receipt_ID} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs">
                  <div>
                    <div className="font-mono font-bold text-slate-800">{col.Receipt_ID}</div>
                    <div className="text-[10px] text-slate-500">{col.Payment_Mode} &bull; {formatIndianDate(col.Receipt_Date)}</div>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-emerald-700 text-sm">
                      +{formatINR(col.Amount)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
