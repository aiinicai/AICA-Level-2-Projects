const inr2 = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** ₹1,23,456.00 */
export const money = (n: number) => '₹' + inr2.format(n || 0);

/** Plain 1,23,456.00 for table cells. */
export const amt = (n: number) => inr2.format(n || 0);

/** ₹1.25 Cr / ₹4.30 L / ₹12,345.00 for headline figures. */
export const short = (n: number) => {
  const a = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(2)} Cr`;
  if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(2)} L`;
  return money(n);
};

export const signed = (n: number) => (Math.abs(n) < 0.005 ? '—' : (n > 0 ? '+' : '') + inr2.format(n));

export const pct = (part: number, whole: number) => (whole ? Math.round((part / whole) * 100) : 0);
