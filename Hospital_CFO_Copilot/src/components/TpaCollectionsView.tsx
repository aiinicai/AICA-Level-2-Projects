import React, { useMemo, useState } from 'react';
import {
  Building,
  Calendar,
  Clock,
  FileCheck,
  ShieldAlert,
  TrendingDown,
} from 'lucide-react';
import { Billing, Claim, Collection, Encounter } from '../types';
import { getLatestTransactionDate, getClaimsPendingAdjudication, calculateArAgeing } from '../utils/arCalculations';
import { formatINR } from '../utils/formatters';
import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface TpaCollectionsViewProps {
  encounters: Encounter[];
  billings: Billing[];
  claims: Claim[];
  collections: Collection[];
  onSelectEncounter: (encounterId: string) => void;
  asOfDate?: string;
  onNavigateToTab?: (tab: string) => void;
}

export const TpaCollectionsView: React.FC<TpaCollectionsViewProps> = ({
  encounters,
  billings,
  claims,
  collections,
  onSelectEncounter,
  asOfDate: propAsOfDate,
  onNavigateToTab,
}) => {
  const [customAsOfDate, setCustomAsOfDate] = useState<string | undefined>(propAsOfDate);

  // Dynamic as-of date anchored to actual transaction history
  const asOfDateObj = useMemo(() => {
    return getLatestTransactionDate(billings, collections, encounters, claims, customAsOfDate);
  }, [billings, collections, encounters, claims, customAsOfDate]);

  const asOfDateStr = asOfDateObj.toISOString().split('T')[0];

  // Compute encounter receivables from actual billing and collection records
  const billingByEnc = useMemo(() => {
    const map = new Map<string, number>();
    billings.forEach((b) => {
      map.set(b.Encounter_ID, (map.get(b.Encounter_ID) || 0) + (Number(b.Billed_Amount) || 0));
    });
    return map;
  }, [billings]);

  const collectionByEnc = useMemo(() => {
    const map = new Map<string, number>();
    collections.forEach((c) => {
      map.set(c.Encounter_ID, (map.get(c.Encounter_ID) || 0) + (Number(c.Amount) || 0));
    });
    return map;
  }, [collections]);

  // Actual TPA Metrics
  const totalClaimsSubmitted = claims.reduce((sum, c) => sum + (Number(c.Claim_Amount) || 0), 0);
  const totalApproved = claims.reduce((sum, c) => sum + (Number(c.Approved_Amount) || 0), 0);
  const totalShortfall = claims.reduce((sum, c) => sum + (Number(c.Rejected_Amount) || 0), 0);

  // Use canonical pending-claim filter (same logic used in Dashboard/controlEngine for consistency)
  const pendingClaims = getClaimsPendingAdjudication(claims);
  const pendingAmount = pendingClaims.reduce((sum, c) => sum + (Number(c.Claim_Amount) || 0), 0);

  // Collections Metrics
  const grossBilling = billings.reduce((sum, b) => sum + (Number(b.Billed_Amount) || 0), 0);
  const totalCollected = collections.reduce((sum, c) => sum + (Number(c.Amount) || 0), 0);
  const totalOutstanding = Math.max(0, grossBilling - totalCollected);

  // Collections specifically against approved claims
  const approvedEncounters = new Set(
    claims.filter((c) => c.Approved_Amount > 0).map((c) => c.Encounter_ID)
  );
  const collectionsAgainstApprovedClaims = collections
    .filter((c) => approvedEncounters.has(c.Encounter_ID))
    .reduce((sum, c) => sum + (Number(c.Amount) || 0), 0);

  // Ageing Buckets calculation based on actual transaction dates (bill date / discharge date)
  // AgeingRow type is no longer needed: canonical AR ageing is computed via calculateArAgeing()

  // Use canonical AR ageing calculation for bucket consistency with ArWorkingCapitalView
  const canonicalArSummary = useMemo(() => {
    return calculateArAgeing(encounters, billings, collections, claims, asOfDateStr);
  }, [encounters, billings, collections, claims, asOfDateStr]);

  // Map canonical AR items to the local ageingRows shape (encounters with outstanding balance)
  const ageingRows = useMemo(() => {
    return canonicalArSummary.items
      .filter((item) => item.outstandingAR > 0)
      .map((item) => {
        const enc = encounters.find((e) => e.Encounter_ID === item.encounterId);
        if (!enc) return null;
        return {
          encounter: enc,
          billed: item.billedAmount,
          collected: item.collectedAmount,
          outstanding: item.outstandingAR,
          daysElapsed: item.daysOutstanding,
          bucket: item.bucket,
        };
      })
      .filter((r): r is NonNullable<typeof r> => r !== null);
  }, [canonicalArSummary.items, encounters]);

  const bucketSummary = useMemo(() => {
    const buckets = canonicalArSummary.ageingBuckets;
    const get = (key: string) => buckets.find((b) => b.bucket === key);
    return {
      '0-30':  { count: get('0-30')?.count  ?? 0, amount: get('0-30')?.amount  ?? 0 },
      '31-60': { count: get('31-60')?.count ?? 0, amount: get('31-60')?.amount ?? 0 },
      '61-90': { count: get('61-90')?.count ?? 0, amount: get('61-90')?.amount ?? 0 },
      '90+':   { count: get('90+')?.count   ?? 0, amount: get('90+')?.amount   ?? 0 },
    };
  }, [canonicalArSummary.ageingBuckets]);

  if (claims.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-teal-600" />
            TPA Insurance Adjudication &amp; Collections Ageing Desk
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Insurance claim approvals, shortfalls, payment realization against approved claims, and aged receivables.
          </p>
        </div>
        <EmptyWorkspaceState
          title="No claims data available."
          description="Insurance claim adjudication, denial patterns, and TPA receivables require insurance claim records with adjudication status. Upload your TPA claim extracts to begin analysis."
          badge="TPA Inactive"
          actionText="Upload Hospital Financial Extracts"
          onAction={() => onNavigateToTab?.('data-intelligence')}
          suggestedDatasets={[
            'TPA / Insurance Claims (Claim_ID, Encounter_ID, Payer, Claim_Amount, Approved_Amount, Claim_Status)',
            'Payment Receipts & Collections Register',
            'Inpatient Encounters (UHID, Discharge_Date)',
          ]}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-teal-600" />
              TPA Insurance Adjudication &amp; Collections Ageing Desk
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Insurance claim approvals, shortfalls, payment realization against approved claims, and aged receivables.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">As-of Date:</span>
            <input
              type="date"
              value={asOfDateStr}
              onChange={(e) => setCustomAsOfDate(e.target.value)}
              className="border border-slate-300 rounded px-2 py-1 text-xs bg-white text-slate-800 font-semibold focus:outline-teal-600"
            />
          </div>
        </div>
      </div>

      {/* TPA Claims Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {/* Total Submitted */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-500 uppercase">TPA Claims Submitted</span>
          <div className="mt-1 text-2xl font-extrabold text-slate-900">
            {formatINR(totalClaimsSubmitted, { compact: true })}
          </div>
          <span className="text-[11px] text-slate-500">{claims.length} claims filed</span>
        </div>

        {/* Total Approved */}
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 shadow-xs">
          <span className="text-[11px] font-semibold text-emerald-800 uppercase">Approved Amount</span>
          <div className="mt-1 text-2xl font-extrabold text-emerald-950">
            {formatINR(totalApproved, { compact: true })}
          </div>
          <span className="text-[11px] text-emerald-700 font-medium">
            {totalClaimsSubmitted > 0 ? ((totalApproved / totalClaimsSubmitted) * 100).toFixed(1) : 0}% clearance rate
          </span>
        </div>

        {/* Shortfall / Rejections */}
        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 shadow-xs">
          <span className="text-[11px] font-semibold text-amber-800 uppercase">Disallowed / Shortfall</span>
          <div className="mt-1 text-2xl font-extrabold text-amber-950">
            {formatINR(totalShortfall)}
          </div>
          <span className="text-[11px] text-amber-800">
            {totalClaimsSubmitted > 0 ? ((totalShortfall / totalClaimsSubmitted) * 100).toFixed(1) : 0}% disallowance
          </span>
        </div>

        {/* Pending Claims */}
        <div className="rounded-xl border border-sky-200 bg-sky-50/50 p-4 shadow-xs">
          <span className="text-[11px] font-semibold text-sky-800 uppercase">Pending Adjudication</span>
          <div className="mt-1 text-2xl font-extrabold text-sky-950">
            {formatINR(pendingAmount, { compact: true })}
          </div>
          <span className="text-[11px] text-sky-700">{pendingClaims.length} awaiting insurer response</span>
        </div>
      </div>

      {/* Additional Metrics Row: Collections Realized against Approved Claims */}
      {approvedEncounters.size > 0 && (
        <div className="rounded-xl border border-teal-200 bg-teal-50/40 p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
          <div>
            <span className="font-bold text-teal-950 uppercase text-[10px] tracking-wider">
              Cash Realisation Against Approved Claims
            </span>
            <div className="text-lg font-bold text-teal-900 mt-0.5">
              {formatINR(collectionsAgainstApprovedClaims)} of {formatINR(totalApproved)} approved
            </div>
          </div>
          <div className="text-right text-teal-800">
            <span className="font-semibold">
              {totalApproved > 0 ? ((collectionsAgainstApprovedClaims / totalApproved) * 100).toFixed(1) : 0}%
            </span>
            <span className="text-[11px] text-teal-700 block">collected to hospital bank account</span>
          </div>
        </div>
      )}

      {/* Ageing Buckets Summary Cards */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Clock className="h-4 w-4 text-teal-600" />
            Receivables Ageing Buckets (Post-Discharge)
          </h3>
          <span className="text-xs text-slate-500">
            Total Outstanding: <strong className="text-rose-600 font-bold">{formatINR(totalOutstanding)}</strong>
          </span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {/* 0-30 Days */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5">
            <div className="text-[11px] uppercase font-bold text-emerald-800">0 – 30 Days (Current)</div>
            <div className="mt-1 text-xl font-extrabold text-slate-900">
              {formatINR(bucketSummary['0-30'].amount)}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              {bucketSummary['0-30'].count} encounter{bucketSummary['0-30'].count !== 1 ? 's' : ''} &bull; Normal billing cycle
            </div>
          </div>

          {/* 31-60 Days */}
          <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3.5">
            <div className="text-[11px] uppercase font-bold text-amber-800">31 – 60 Days (Overdue)</div>
            <div className="mt-1 text-xl font-extrabold text-amber-950">
              {formatINR(bucketSummary['31-60'].amount)}
            </div>
            <div className="text-[11px] text-amber-800 mt-0.5">
              {bucketSummary['31-60'].count} encounter{bucketSummary['31-60'].count !== 1 ? 's' : ''} &bull; Dunning alert
            </div>
          </div>

          {/* 61-90 Days */}
          <div className="rounded-lg border border-rose-200 bg-rose-50/40 p-3.5">
            <div className="text-[11px] uppercase font-bold text-rose-800">61 – 90 Days (High Risk)</div>
            <div className="mt-1 text-xl font-extrabold text-rose-900">
              {formatINR(bucketSummary['61-90'].amount)}
            </div>
            <div className="text-[11px] text-rose-700 mt-0.5">
              {bucketSummary['61-90'].count} encounter{bucketSummary['61-90'].count !== 1 ? 's' : ''} &bull; Escalation notice
            </div>
          </div>

          {/* 90+ Days */}
          <div className="rounded-lg border border-rose-300 bg-rose-50 p-3.5">
            <div className="text-[11px] uppercase font-bold text-rose-800">90+ Days (Critical Delinquent)</div>
            <div className="mt-1 text-xl font-extrabold text-rose-950">
              {formatINR(bucketSummary['90+'].amount)}
            </div>
            <div className="text-[11px] text-rose-800 mt-0.5">
              {bucketSummary['90+'].count} encounter{bucketSummary['90+'].count !== 1 ? 's' : ''} &bull; Bad debt provision
            </div>
          </div>
        </div>
      </div>

      {/* Two Columns: TPA Claims Table & Aged Encounters */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* TPA Claims Adjudication Table */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <Building className="h-4 w-4 text-sky-600" />
            TPA Insurance Claims Register ({claims.length} Claims)
          </h3>
          <div className="mt-3 overflow-x-auto max-h-[380px] overflow-y-auto">
            {claims.length > 0 ? (
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 sticky top-0 border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Claim ID</th>
                    <th className="py-2.5 px-3 font-semibold">Encounter</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Claimed</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Approved</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Shortfall</th>
                    <th className="py-2.5 px-3 font-semibold text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-[11px]">
                  {claims.map((claim, idx) => (
                    <tr
                      key={`${claim.Claim_ID}-${idx}`}
                      onClick={() => onSelectEncounter(claim.Encounter_ID)}
                      className="hover:bg-slate-50 transition cursor-pointer"
                    >
                      <td className="py-2.5 px-3 font-mono font-bold text-teal-800">{claim.Claim_ID}</td>
                      <td className="py-2.5 px-3 text-slate-700 font-mono">{claim.Encounter_ID}</td>
                      <td className="py-2.5 px-3 text-right font-medium text-slate-900">{formatINR(claim.Claim_Amount)}</td>
                      <td className="py-2.5 px-3 text-right font-medium text-emerald-800">{formatINR(claim.Approved_Amount)}</td>
                      <td className={`py-2.5 px-3 text-right font-bold ${claim.Rejected_Amount > 0 ? 'text-rose-700' : 'text-slate-400'}`}>
                        {formatINR(claim.Rejected_Amount)}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                            claim.Claim_Status === 'Approved'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : claim.Claim_Status === 'Partially Approved'
                              ? 'bg-amber-50 text-amber-800 border border-amber-200'
                              : claim.Claim_Status === 'Rejected'
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : 'bg-sky-50 text-sky-800 border border-sky-200'
                          }`}
                        >
                          {claim.Claim_Status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="py-12 text-center text-slate-400 text-xs">
                Data not available for the selected period
              </div>
            )}
          </div>
        </div>

        {/* Aged Outstanding Encounters */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <TrendingDown className="h-4 w-4 text-rose-600" />
            Aged Uncollected Accounts Receivable (AR)
          </h3>
          <div className="mt-3 overflow-x-auto max-h-[380px] overflow-y-auto">
            {ageingRows.length > 0 ? (
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 sticky top-0 border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Encounter</th>
                    <th className="py-2.5 px-3 font-semibold">Dept</th>
                    <th className="py-2.5 px-3 font-semibold">Payer</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Age (Days)</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Outstanding</th>
                    <th className="py-2.5 px-3 font-semibold text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ageingRows
                    .sort((a, b) => b.daysElapsed - a.daysElapsed)
                    .map((row, idx) => (
                      <tr
                        key={`${row.encounter.Encounter_ID}-${idx}`}
                        onClick={() => onSelectEncounter(row.encounter.Encounter_ID)}
                        className="hover:bg-slate-50 transition cursor-pointer text-xs"
                      >
                        <td className="py-2.5 px-3 font-mono font-bold text-teal-800">
                          {row.encounter.Encounter_ID}
                        </td>
                        <td className="py-2.5 px-3 text-slate-700">{row.encounter.Department}</td>
                        <td className="py-2.5 px-3 text-slate-500">{row.encounter.Payer_Type}</td>
                        <td className="py-2.5 px-3 text-right font-mono">
                          <span
                            className={`font-bold ${
                              row.daysElapsed > 30 ? 'text-rose-700' : 'text-slate-600'
                            }`}
                          >
                            {row.daysElapsed}d
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-bold text-amber-900">
                          {formatINR(row.outstanding)}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <button
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              onSelectEncounter(row.encounter.Encounter_ID);
                            }}
                            className="rounded bg-slate-100 hover:bg-slate-200 px-2 py-0.5 text-[11px] font-medium text-slate-800 border border-slate-200 transition cursor-pointer"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            ) : (
              <div className="py-12 text-center text-slate-400 text-xs">
                No outstanding uncollected encounters
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
