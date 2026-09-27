/**
 * Hospital CFO Copilot - Deterministic AR Ageing & Working Capital Engine
 *
 * All metrics, buckets, overdue amounts, payer categories, and department breakdowns
 * are calculated deterministically from actual Firestore / imported hospital datasets.
 * Dynamic as-of date is anchored to the selected reporting date or the latest valid
 * transaction timestamp in the imported data.
 */

import { Billing, Claim, Collection, Encounter } from '../types';

export interface EncounterArItem {
  encounterId: string;
  department: string;
  ward?: string;
  payerType: string;
  dischargeDate?: string | null;
  admissionDate: string;
  referenceDate: string;
  billedAmount: number;
  collectedAmount: number;
  outstandingAR: number;
  daysOutstanding: number;
  bucket: '0-30' | '31-60' | '61-90' | '90+';
  claimStatus: string;
}

export interface PayerArBreakdown {
  payer: string;
  billed: number;
  collected: number;
  ar: number;
  percentage: number;
}

export interface DepartmentArBreakdown {
  department: string;
  billed: number;
  collected: number;
  ar: number;
  percentage: number;
}

export interface ArAgeingSummary {
  asOfDate: string;
  asOfDateDisplay: string;
  totalBilled: number;
  totalCollected: number;
  totalAR: number;
  currentAR: number; // 0-30 days
  ar31_60: number;
  ar61_90: number;
  ar90plus: number; // Overdue >90 days
  overdueAR: number; // AR > 30 days
  collectionRate: number; // Percentage
  items: EncounterArItem[];
  ageingBuckets: Array<{
    bucket: string;
    label: string;
    amount: number;
    count: number;
    share: number; // Percentage
    shareFormatted: string;
    color: string;
  }>;
  payerBreakdown: PayerArBreakdown[];
  departmentBreakdown: DepartmentArBreakdown[];
  highValueOverdueAccounts: EncounterArItem[];
}

/**
 * Derives the dynamic as-of date:
 * Uses explicit asOfDate if valid, otherwise finds the latest valid transaction
 * date from billing, collection, encounter discharge/admission, or claim records.
 * Falls back to current system date only if no transaction dates exist.
 */
export function getLatestTransactionDate(
  billings: Billing[] = [],
  collections: Collection[] = [],
  encounters: Encounter[] = [],
  claims: Claim[] = [],
  explicitAsOfDate?: string
): Date {
  if (explicitAsOfDate && !isNaN(new Date(explicitAsOfDate).getTime())) {
    return new Date(explicitAsOfDate);
  }

  let maxTimestamp = 0;

  billings.forEach((b) => {
    const raw = b.Bill_Date || b.Bill_DateTime;
    if (raw) {
      const ts = new Date(raw).getTime();
      if (!isNaN(ts) && ts > maxTimestamp) maxTimestamp = ts;
    }
  });

  collections.forEach((c) => {
    if (c.Receipt_Date) {
      const ts = new Date(c.Receipt_Date).getTime();
      if (!isNaN(ts) && ts > maxTimestamp) maxTimestamp = ts;
    }
  });

  encounters.forEach((e) => {
    const raw = e.Discharge_Date || e.Admission_Date;
    if (raw) {
      const ts = new Date(raw).getTime();
      if (!isNaN(ts) && ts > maxTimestamp) maxTimestamp = ts;
    }
  });

  claims.forEach((c) => {
    if (c.Submission_Date) {
      const ts = new Date(c.Submission_Date).getTime();
      if (!isNaN(ts) && ts > maxTimestamp) maxTimestamp = ts;
    }
  });

  return maxTimestamp > 0 ? new Date(maxTimestamp) : new Date();
}

/**
 * Deterministically computes complete Accounts Receivable ageing and working capital breakdowns.
 */
export function calculateArAgeing(
  encounters: Encounter[] = [],
  billings: Billing[] = [],
  collections: Collection[] = [],
  claims: Claim[] = [],
  explicitAsOfDate?: string
): ArAgeingSummary {
  const asOfDateObj = getLatestTransactionDate(billings, collections, encounters, claims, explicitAsOfDate);
  const asOfDateStr = asOfDateObj.toISOString().split('T')[0];

  // 1. Aggregate Billed by Encounter
  const billedByEnc = new Map<string, number>();
  const latestBillDateByEnc = new Map<string, string>();
  billings.forEach((b) => {
    if (!b.Encounter_ID) return;
    const cur = billedByEnc.get(b.Encounter_ID) || 0;
    billedByEnc.set(b.Encounter_ID, cur + (Number(b.Billed_Amount) || 0));

    const bDate = (b.Bill_Date || b.Bill_DateTime || '').slice(0, 10);
    if (bDate) {
      const prev = latestBillDateByEnc.get(b.Encounter_ID);
      if (!prev || bDate > prev) {
        latestBillDateByEnc.set(b.Encounter_ID, bDate);
      }
    }
  });

  // 2. Aggregate Collections by Encounter
  const collectedByEnc = new Map<string, number>();
  collections.forEach((c) => {
    if (!c.Encounter_ID) return;
    const cur = collectedByEnc.get(c.Encounter_ID) || 0;
    collectedByEnc.set(c.Encounter_ID, cur + (Number(c.Amount) || 0));
  });

  // 3. Claims map for status lookup
  const claimsByEnc = new Map<string, Claim[]>();
  claims.forEach((c) => {
    if (!c.Encounter_ID) return;
    const list = claimsByEnc.get(c.Encounter_ID) || [];
    list.push(c);
    claimsByEnc.set(c.Encounter_ID, list);
  });

  // Deduplicate encounters
  const seenEncounterIds = new Set<string>();
  const uniqueEncounters = encounters.filter((e) => {
    if (!e.Encounter_ID || seenEncounterIds.has(e.Encounter_ID)) return false;
    seenEncounterIds.add(e.Encounter_ID);
    return true;
  });

  // 4. Compute each encounter's AR balance and ageing bucket
  const items: EncounterArItem[] = uniqueEncounters.map((enc) => {
    const billed = billedByEnc.get(enc.Encounter_ID) || 0;
    const collected = collectedByEnc.get(enc.Encounter_ID) || 0;
    const outstanding = Math.max(0, billed - collected);

    // Reference transaction date: latest bill date > discharge date > admission date
    const refDateStr =
      latestBillDateByEnc.get(enc.Encounter_ID) ||
      enc.Discharge_Date ||
      enc.Admission_Date ||
      asOfDateStr;

    const refDate = new Date(refDateStr);
    const msDiff = asOfDateObj.getTime() - refDate.getTime();
    const daysDiff = Math.max(0, Math.ceil(msDiff / (1000 * 60 * 60 * 24)));

    let bucket: EncounterArItem['bucket'] = '0-30';
    if (daysDiff > 90) bucket = '90+';
    else if (daysDiff > 60) bucket = '61-90';
    else if (daysDiff > 30) bucket = '31-60';

    const encClaims = claimsByEnc.get(enc.Encounter_ID) || [];
    const claimStatus = encClaims.length > 0 ? encClaims[0].Claim_Status : 'No Claim';

    return {
      encounterId: enc.Encounter_ID,
      department: enc.Department || 'Unspecified',
      ward: enc.Ward,
      payerType: enc.Payer_Type || 'Self Pay',
      dischargeDate: enc.Discharge_Date,
      admissionDate: enc.Admission_Date,
      referenceDate: refDateStr,
      billedAmount: billed,
      collectedAmount: collected,
      outstandingAR: outstanding,
      daysOutstanding: daysDiff,
      bucket,
      claimStatus,
    };
  });

  const totalBilled = items.reduce((s, e) => s + e.billedAmount, 0);
  const totalCollected = items.reduce((s, e) => s + e.collectedAmount, 0);
  const totalAR = items.reduce((s, e) => s + e.outstandingAR, 0);

  const currentAR = items.filter((e) => e.bucket === '0-30').reduce((s, e) => s + e.outstandingAR, 0);
  const ar31_60 = items.filter((e) => e.bucket === '31-60').reduce((s, e) => s + e.outstandingAR, 0);
  const ar61_90 = items.filter((e) => e.bucket === '61-90').reduce((s, e) => s + e.outstandingAR, 0);
  const ar90plus = items.filter((e) => e.bucket === '90+').reduce((s, e) => s + e.outstandingAR, 0);

  const overdueAR = Math.max(0, totalAR - currentAR);
  const collectionRate = totalBilled > 0 ? Number(((totalCollected / totalBilled) * 100).toFixed(1)) : 100;

  // Ageing Buckets for visual charts
  const bucketDefs: Array<{
    bucket: '0-30' | '31-60' | '61-90' | '90+';
    label: string;
    color: string;
    amount: number;
  }> = [
    { bucket: '0-30', label: '0–30 Days (Current)', color: '#0d9488', amount: currentAR },
    { bucket: '31-60', label: '31–60 Days', color: '#0284c7', amount: ar31_60 },
    { bucket: '61-90', label: '61–90 Days', color: '#f59e0b', amount: ar61_90 },
    { bucket: '90+', label: '90+ Days (Overdue)', color: '#dc2626', amount: ar90plus },
  ];

  const ageingBuckets = bucketDefs.map((b) => {
    const encCount = items.filter((e) => e.bucket === b.bucket && e.outstandingAR > 0).length;
    const share = totalAR > 0 ? Number(((b.amount / totalAR) * 100).toFixed(1)) : 0;
    return {
      bucket: b.bucket,
      label: b.label,
      amount: b.amount,
      count: encCount,
      share,
      shareFormatted: `${share}%`,
      color: b.color,
    };
  });

  // Payer Breakdown
  const payerMap = new Map<string, { billed: number; collected: number; ar: number }>();
  items.forEach((e) => {
    const cur = payerMap.get(e.payerType) || { billed: 0, collected: 0, ar: 0 };
    cur.billed += e.billedAmount;
    cur.collected += e.collectedAmount;
    cur.ar += e.outstandingAR;
    payerMap.set(e.payerType, cur);
  });

  const payerBreakdown: PayerArBreakdown[] = Array.from(payerMap.entries())
    .map(([payer, val]) => ({
      payer,
      ...val,
      percentage: totalAR > 0 ? Number(((val.ar / totalAR) * 100).toFixed(1)) : 0,
    }))
    .sort((a, b) => b.ar - a.ar);

  // Department Breakdown
  const deptMap = new Map<string, { billed: number; collected: number; ar: number }>();
  items.forEach((e) => {
    const cur = deptMap.get(e.department) || { billed: 0, collected: 0, ar: 0 };
    cur.billed += e.billedAmount;
    cur.collected += e.collectedAmount;
    cur.ar += e.outstandingAR;
    deptMap.set(e.department, cur);
  });

  const departmentBreakdown: DepartmentArBreakdown[] = Array.from(deptMap.entries())
    .map(([department, val]) => ({
      department,
      ...val,
      percentage: totalAR > 0 ? Number(((val.ar / totalAR) * 100).toFixed(1)) : 0,
    }))
    .sort((a, b) => b.ar - a.ar);

  // High-value overdue accounts (>30 days with balance > 0, sorted by AR descending)
  const highValueOverdueAccounts = items
    .filter((e) => e.outstandingAR > 0 && e.daysOutstanding > 30)
    .sort((a, b) => b.outstandingAR - a.outstandingAR);

  return {
    asOfDate: asOfDateStr,
    asOfDateDisplay: asOfDateObj.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }),
    totalBilled,
    totalCollected,
    totalAR,
    currentAR,
    ar31_60,
    ar61_90,
    ar90plus,
    overdueAR,
    collectionRate,
    items,
    ageingBuckets,
    payerBreakdown,
    departmentBreakdown,
    highValueOverdueAccounts,
  };
}

/**
 * Canonical TPA pending claim filter.
 * A claim is considered "pending" if it is awaiting any form of insurer response:
 * Submitted, Pending Info, Under Query, or In Adjudication.
 * Also includes claims with no approved/rejected amounts that are not outright Rejected.
 *
 * Use this function in both controlEngine.ts (for DashboardMetrics.tpaPendingAmount)
 * and TpaCollectionsView.tsx to ensure consistent pending amount reporting.
 */
export function getClaimsPendingAdjudication(claims: import('../types').Claim[]): import('../types').Claim[] {
  return claims.filter(
    (c) =>
      c.Claim_Status === 'Submitted' ||
      c.Claim_Status === 'Pending Info' ||
      c.Claim_Status === 'Under Query' ||
      c.Claim_Status === 'In Adjudication' ||
      (!c.Approved_Amount && !c.Rejected_Amount && c.Claim_Status !== 'Rejected')
  );
}
