/** value is always stored in the workbook's source units (Lakhs, per the parse pipeline). */
export function formatINR(valueInLakhs, { unit = 'L' } = {}) {
  if (valueInLakhs == null || !isFinite(valueInLakhs)) return '—';
  const display = unit === 'Cr' ? valueInLakhs / 100 : valueInLakhs;
  const rounded = Math.round(display);
  return `₹${rounded.toLocaleString('en-IN')} ${unit}`;
}

export function formatPct(value, { signed = false, decimals = 1 } = {}) {
  if (value == null || !isFinite(value)) return '—';
  const fixed = Math.abs(value).toFixed(decimals);
  if (!signed) return `${value.toFixed(decimals)}%`;
  if (value > 0) return `▲ ${fixed}%`;
  if (value < 0) return `▼ ${fixed}%`;
  return `${fixed}%`;
}

export function formatRatioX(value, decimals = 2) {
  if (value == null || !isFinite(value)) return '—';
  return `${value.toFixed(decimals)}x`;
}

export function formatDays(value, decimals = 0) {
  if (value == null || !isFinite(value)) return '—';
  return `${value.toFixed(decimals)} days`;
}

export function formatNumber(value, decimals = 2) {
  if (value == null || !isFinite(value)) return '—';
  return value.toLocaleString('en-IN', { maximumFractionDigits: decimals });
}
