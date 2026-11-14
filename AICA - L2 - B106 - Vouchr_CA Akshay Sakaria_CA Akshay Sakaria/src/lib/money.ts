export const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });
const inrShort = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 });

export const fmtInr = (n: number) => inr.format(n || 0);

export function fmtInrShort(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e7) return '₹' + inrShort.format(n / 1e7) + 'Cr';
  if (a >= 1e5) return '₹' + inrShort.format(n / 1e5) + 'L';
  if (a >= 1e3) return '₹' + inrShort.format(n / 1e3) + 'K';
  return '₹' + inrShort.format(n);
}

export interface AmountSplit {
  taxableValue: number;
  cgst: number;
  sgst: number;
  igst: number;
  totalAmount: number;
}

/** Staff enter the bill total (the number they see); taxable value and GST are derived from it. */
export function splitFromTotal(total: number, gstRatePct: number, interState: boolean): AmountSplit {
  const t = round2(Math.max(total, 0));
  const taxable = round2(t / (1 + gstRatePct / 100));
  const tax = round2(t - taxable);
  const half = round2(tax / 2);
  return interState
    ? { taxableValue: taxable, cgst: 0, sgst: 0, igst: tax, totalAmount: t }
    : { taxableValue: taxable, cgst: half, sgst: round2(tax - half), igst: 0, totalAmount: t };
}

/** Split an amount at a GST rate. Intra-state → CGST+SGST, inter-state → IGST. Discount reduces taxable value. */
export function computeAmounts(gross: number, discount: number, gstRatePct: number, interState: boolean): AmountSplit {
  const taxable = round2(Math.max(gross - discount, 0));
  const tax = round2((taxable * gstRatePct) / 100);
  const half = round2(tax / 2);
  return interState
    ? { taxableValue: taxable, cgst: 0, sgst: 0, igst: tax, totalAmount: round2(taxable + tax) }
    : { taxableValue: taxable, cgst: half, sgst: round2(tax - half), igst: 0, totalAmount: round2(taxable + tax) };
}

/** Keep digits and a single decimal point, max 2 decimals, max 12 digits before the point. */
export function cleanAmount(v: string): string {
  const s = v.replace(/[^0-9.]/g, '');
  const [a, ...rest] = s.split('.');
  const whole = a.replace(/^0+(?=\d)/, '').slice(0, 12);
  return rest.length ? `${whole || '0'}.${rest.join('').slice(0, 2)}` : whole;
}
