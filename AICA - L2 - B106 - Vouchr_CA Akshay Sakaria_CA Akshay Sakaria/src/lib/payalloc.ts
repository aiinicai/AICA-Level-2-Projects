// Spreads one or more payment lines (cash today, UPI tomorrow, cheque next week…) across the bills being paid.
// Bills are filled oldest-first, in the order given; whatever is left on a line stays with the vendor as an advance.
import type { Allocation } from '../data/types';
import { round2 } from './money';

export interface BillTarget {
  expenseId: string;
  amount: number; // how much of this bill is being paid now
}

export function allocateLines(lineAmounts: number[], bills: BillTarget[]): Allocation[][] {
  const left = bills.map((b) => ({ ...b, amount: round2(b.amount) }));
  return lineAmounts.map((amt) => {
    let rem = round2(amt);
    const out: Allocation[] = [];
    for (const b of left) {
      if (rem <= 0) break;
      if (b.amount <= 0) continue;
      const a = round2(Math.min(rem, b.amount));
      out.push({ expenseId: b.expenseId, amount: a });
      b.amount = round2(b.amount - a);
      rem = round2(rem - a);
    }
    return out;
  });
}
