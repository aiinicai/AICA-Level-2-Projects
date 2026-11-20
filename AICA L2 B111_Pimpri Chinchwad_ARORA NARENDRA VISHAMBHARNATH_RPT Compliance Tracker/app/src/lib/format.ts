export const number = (v: number, decimals = 0) =>
  v.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
export const rupees = (v: number) => `Rs ${number(v)}`;
export const crore = (v: number) => `Rs ${number(v / 10000000, 2)} crore`;
export const moneyWords = (v: number) =>
  Math.abs(v) >= 10000000
    ? crore(v)
    : Math.abs(v) >= 100000
      ? `Rs ${number(v / 100000, 2)} lakh`
      : rupees(v);
export const percent = (v: number) => `${v >= 0 ? "+" : ""}${number(v * 100, 1)}%`;
export function dateLabel(v: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return v;
  const [year, month, day] = v.split("-");
  return `${day}-${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(month) - 1]}-${year}`;
}
