// Auto-approval of low-risk bills (AUDIT-v0.4 B10). OFF unless the CA firm switches it on for a client.
// A bill is approved without review only if EVERY condition holds; any doubt keeps it in the review queue. A share of the
// bills that pass is still sent for a sample check. The tax treatment is copied from the vendor's last approved bills —
// never guessed.
import type { Client, Expense } from '../data/types';
import { round2 } from './money';

export interface AutoApproveSettings { enabled: boolean; maxAmount: number; samplePct: number; minHistory: number }
export const AUTO_DEFAULTS: AutoApproveSettings = { enabled: false, maxAmount: 5000, samplePct: 10, minHistory: 3 };

/** Same bill → same answer (so a re-check never changes whether it was sampled). */
export function inSample(id: string, pct: number): boolean {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) { h ^= id.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0) % 100 < pct;
}

export interface AutoDecision { approve: boolean; sampled: boolean; reasons: string[]; patch?: Pick<Expense, 'headId' | 'itcEligible' | 'blockedCode'> }

/** `history` = the vendor's earlier bills; `riskFlagsForBill` = Bill risk check flags on this bill. */
export function autoApproveDecision(e: Expense, client: Client | undefined, history: Expense[], riskFlagsForBill: number): AutoDecision {
  const set = { ...AUTO_DEFAULTS, ...(client?.autoApprove ?? {}) };
  const reasons: string[] = [];
  if (!set.enabled) return { approve: false, sampled: false, reasons: ['Auto-approval is off for this client'] };
  if (e.totalAmount > set.maxAmount) reasons.push('Above the auto-approval limit');
  if (!(e.fileId || e.imageDataUrl || e.attachmentName) || e.noImageReason) reasons.push('No bill image');
  if (e.tdsAmount > 0 || e.tdsCode) reasons.push('TDS applies');
  if (e.rcmApplicable) reasons.push('Reverse charge applies');
  if (e.blockedCode) reasons.push('Blocked credit (17(5)) suggested');
  if (e.ecoPaysTax || (e.nonTaxableAmount ?? 0) > 0) reasons.push('Aggregator / 9(5) bill');
  if (e.isBackdated) reasons.push('Past-dated entry');
  if (e.notDuplicateOf) reasons.push('Look-alike of another bill');
  if (e.resubmittedAt) reasons.push('Resubmitted after return');
  if (e.irnSignature === 'invalid') reasons.push('E-invoice QR signature does not match');
  if (riskFlagsForBill > 0) reasons.push('Bill risk check has flags');
  if (Math.abs(round2(e.totalAmount - e.taxableValue - (e.nonTaxableAmount ?? 0) - e.cgst - e.sgst - e.igst)) > 1) reasons.push('Taxable + GST does not add up to the total');
  const approved = history.filter((x) => x.status === 'approved' || x.status === 'posted').sort((a, b) => b.invoiceDate.localeCompare(a.invoiceDate)).slice(0, set.minHistory);
  if (approved.length < set.minHistory) reasons.push('Vendor has fewer approved bills than required');
  else {
    const first = approved[0];
    const same = approved.every((x) => x.headId === first.headId && x.itcEligible === first.itcEligible && x.blockedCode === first.blockedCode && !x.tdsAmount && !x.rcmApplicable);
    if (!same) reasons.push('Vendor’s earlier bills were not treated the same way');
    else if (e.headId !== first.headId) reasons.push('Suggested head differs from the vendor’s approved bills');
  }
  if (reasons.length) return { approve: false, sampled: false, reasons };
  if (inSample(e.id, set.samplePct)) return { approve: false, sampled: true, reasons: ['Picked for a sample check'] };
  const f = approved[0];
  return { approve: true, sampled: false, reasons: [], patch: { headId: f.headId, itcEligible: f.itcEligible, blockedCode: f.blockedCode } };
}
