// Suggestion engine: proposes expense head, TDS, RCM and ITC eligibility.
// Every output is a SUGGESTION for the CA reviewer — the sub-user never sees or edits these.

import type { BlockedRule, ExpenseHead, RcmRule, TdsRate, Vendor } from '../data/types';
import { round2 } from './money';
import { isIndividualOrHuf } from './validators';

export interface HeadSuggestion {
  headId: string;
  confidence: number; // 0..1
  reason: string;
}

export function suggestHead(
  text: string,
  hsnSac: string | undefined,
  heads: ExpenseHead[],
  vendorHistoryHeadId?: string
): HeadSuggestion {
  if (vendorHistoryHeadId) {
    return { headId: vendorHistoryHeadId, confidence: 0.95, reason: 'Same head as previous bills from this vendor' };
  }
  const code = (hsnSac ?? '').replace(/\s/g, '');
  if (code) {
    // longest matching prefix wins (e.g. 998211 Legal beats 9982 Professional)
    let best: { h: ExpenseHead; len: number } | undefined;
    for (const h of heads) {
      for (const p of h.sacHsnPrefixes) {
        if (code.startsWith(p) && (!best || p.length > best.len)) best = { h, len: p.length };
      }
    }
    if (best) return { headId: best.h.id, confidence: 0.85, reason: `HSN/SAC ${code} matches ${best.h.name}` };
  }
  const t = text.toLowerCase();
  let top: { h: ExpenseHead; hits: number } | undefined;
  for (const h of heads) {
    const hits = h.keywords.filter((k) => t.includes(k)).length;
    if (hits > 0 && (!top || hits > top.hits)) top = { h, hits };
  }
  if (top) {
    return { headId: top.h.id, confidence: Math.min(0.5 + top.hits * 0.15, 0.8), reason: `Keywords match ${top.h.name}` };
  }
  const misc = heads.find((h) => h.id === 'h-misc') ?? heads[heads.length - 1];
  return { headId: misc.id, confidence: 0.2, reason: 'No match — needs review' };
}

export interface TdsSuggestion {
  code?: string;
  ratePct: number;
  amount: number;
  reason: string;
}

/**
 * TDS is computed on the taxable value (GST excluded where shown separately on the invoice).
 * `ytdPaidToVendor` = taxable value already booked for this vendor in the FY, for aggregate thresholds.
 * `ytdUntaxed` = part of that on which no TDS was deducted yet. When this bill pushes the yearly total
 * over the aggregate threshold, TDS is due on those earlier bills too, so it is added to this bill.
 */
export function suggestTds(
  head: ExpenseHead | undefined,
  vendor: Pick<Vendor, 'pan' | 'panStatus'> | undefined,
  taxableValue: number,
  ytdPaidToVendor: number,
  rates: TdsRate[],
  ytdUntaxed = 0,
  onDate?: string
): TdsSuggestion {
  if (!head?.defaultTdsCode) return { ratePct: 0, amount: 0, reason: 'Head not liable to TDS' };
  let code = head.defaultTdsCode;
  if (code === 'CONTRACT_OTH' && isIndividualOrHuf(vendor?.pan)) code = 'CONTRACT_IND';
  // the rate in force on the bill date (masters keep history via effectiveFrom / effectiveTo)
  const r = rates.filter((x) => x.code === code && (!onDate || (x.effectiveFrom <= onDate && (!x.effectiveTo || x.effectiveTo >= onDate))))
    .sort((a, b) => b.effectiveFrom.localeCompare(a.effectiveFrom))[0] ?? rates.find((x) => x.code === code);
  if (!r) return { ratePct: 0, amount: 0, reason: `Rate ${code} missing in master` };

  const crossesSingle = r.thresholdSingle !== undefined && taxableValue > r.thresholdSingle;
  const crossesAgg = r.thresholdAggregate !== undefined && ytdPaidToVendor + taxableValue > r.thresholdAggregate;
  const noThreshold = r.thresholdSingle === undefined && r.thresholdAggregate === undefined;
  if (!crossesSingle && !crossesAgg && !noThreshold) {
    return { code, ratePct: 0, amount: 0, reason: 'Below threshold (watching yearly total)' };
  }
  const noPan = !vendor?.pan || vendor.panStatus === 'Inoperative';
  const rate = noPan ? Math.max(r.noPanRatePct ?? r.ratePct, r.ratePct) : r.ratePct;
  // first crossing of the yearly limit → catch up on earlier untaxed bills
  const catchUp = crossesAgg && ytdPaidToVendor <= (r.thresholdAggregate ?? 0) ? ytdUntaxed : 0;
  const base = taxableValue + catchUp;
  const why = noPan ? 'Higher rate: PAN missing or inoperative' : `${r.description} @ ${rate}%`;
  return {
    code,
    ratePct: rate,
    amount: round2((base * rate) / 100),
    reason: catchUp > 0 ? `${why} — includes ₹${catchUp} of earlier bills (yearly limit crossed)` : why
  };
}

export interface RcmSuggestion {
  applicable: boolean;
  code?: string;
  ratePct?: number;
  reason: string;
}

export function suggestRcm(head: ExpenseHead | undefined, vendor: Pick<Vendor, 'gstRegistered' | 'pan'> | undefined, rules: RcmRule[]): RcmSuggestion {
  if (!head?.rcmCode) return { applicable: false, reason: 'Category not notified for RCM' };
  const rule = rules.find((r) => r.code === head.rcmCode);
  if (!rule) return { applicable: false, reason: 'RCM rule missing in master' };
  const bodyCorporate = vendor?.pan?.[3] === 'C';
  if (rule.supplierCondition === 'unregistered' && vendor?.gstRegistered) {
    return { applicable: false, reason: 'Supplier is GST registered' };
  }
  if (rule.supplierCondition === 'non_body_corporate' && bodyCorporate) {
    return { applicable: false, reason: 'Supplier is a company (forward charge)' };
  }
  return { applicable: true, code: rule.code, ratePct: rule.defaultRatePct, reason: `${rule.description} — GST @ ${rule.defaultRatePct}% payable by you` };
}

export interface ItcSuggestion {
  eligible: boolean;
  blockedCode?: string;
  reason: string;
}

export function suggestItc(head: ExpenseHead | undefined, text: string, vendorRegistered: boolean, blocked: BlockedRule[]): ItcSuggestion {
  if (!vendorRegistered) return { eligible: false, reason: 'No GST charged by unregistered supplier' };
  if (head?.blocked175) {
    const b = blocked.find((x) => x.code === head.blocked175);
    return { eligible: false, blockedCode: head.blocked175, reason: `Blocked u/s 17(5): ${b?.description ?? head.blocked175}` };
  }
  const t = text.toLowerCase();
  const hit = blocked.find((b) => b.keywords.some((k) => t.includes(k)));
  if (hit) return { eligible: false, blockedCode: hit.code, reason: `Possibly blocked u/s 17(5): ${hit.description}` };
  return { eligible: true, reason: 'Eligible (subject to 2B match & payment within 180 days)' };
}
