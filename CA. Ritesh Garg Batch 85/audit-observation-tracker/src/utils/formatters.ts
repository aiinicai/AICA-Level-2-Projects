import { SeverityLevel, ObservationStatus, RectificationStatus, EngagementStatus } from '../types/audit';

export function formatINR(amount?: number | null): string {
  if (amount === undefined || amount === null || isNaN(amount)) {
    return '—';
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatINRNumberOnly(amount?: number | null): string {
  if (amount === undefined || amount === null || isNaN(amount)) {
    return '0';
  }
  return new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '—';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const year = parts[0];
      const month = parts[1];
      const day = parts[2];
      return `${day}-${month}-${year}`;
    }
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  } catch {
    return dateStr;
  }
}

export function formatFY(fy: string): string {
  return fy.startsWith('FY ') ? fy : `FY ${fy}`;
}

export function getFYShortCode(fy: string): string {
  // e.g. "2024-25" -> "2425", "2025-26" -> "2526", "24-25" -> "2425"
  const cleaned = fy.replace(/[^\d-]/g, '');
  const parts = cleaned.split('-');
  if (parts.length === 2) {
    const y1 = parts[0].slice(-2);
    const y2 = parts[1].slice(-2);
    return `${y1}${y2}`;
  }
  return fy.replace(/[^\w]/g, '').slice(0, 4).toUpperCase();
}

export function generateClientCode(name: string): string {
  if (!name) return 'CLI';
  // If words exist, take first letters of first 3 words
  const words = name.trim().split(/\s+/).filter(w => !['ltd', 'limited', 'pvt', 'private', 'llp', 'co', 'and', '&'].includes(w.toLowerCase()));
  if (words.length >= 2) {
    const code = words.map(w => w[0]).join('').toUpperCase().slice(0, 4);
    if (code.length >= 2) return code;
  }
  // Otherwise take first 3-4 alphanumeric chars
  return name.replace(/[^A-Za-z0-9]/g, '').slice(0, 4).toUpperCase() || 'CLI';
}

export function getSeverityBadgeClass(severity?: SeverityLevel | string | null): {
  bg: string;
  text: string;
  border: string;
  dot: string;
} {
  const norm = severity ? String(severity).trim().toLowerCase() : '';
  switch (norm) {
    case 'critical':
      return {
        bg: 'bg-rose-50',
        text: 'text-rose-800',
        border: 'border-rose-200',
        dot: 'bg-rose-700',
      };
    case 'high':
      return {
        bg: 'bg-amber-50',
        text: 'text-amber-900',
        border: 'border-amber-200',
        dot: 'bg-amber-700',
      };
    case 'medium':
      return {
        bg: 'bg-stone-100',
        text: 'text-stone-800',
        border: 'border-stone-300',
        dot: 'bg-[#5A5A40]',
      };
    case 'low':
      return {
        bg: 'bg-[#F5F2ED]',
        text: 'text-stone-700',
        border: 'border-stone-200',
        dot: 'bg-stone-500',
      };
    default:
      return {
        bg: 'bg-stone-100',
        text: 'text-stone-700',
        border: 'border-stone-200',
        dot: 'bg-stone-400',
      };
  }
}

export function getStatusBadgeClass(status?: ObservationStatus | string | null): {
  bg: string;
  text: string;
  border: string;
} {
  const norm = status ? String(status).trim().toLowerCase() : '';
  switch (norm) {
    case 'open':
      return { bg: 'bg-rose-50', text: 'text-rose-800', border: 'border-rose-200' };
    case 'under discussion':
      return { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200' };
    case 'management response awaited':
      return { bg: 'bg-stone-100', text: 'text-stone-800', border: 'border-stone-300' };
    case 'rectified':
      return { bg: 'bg-[#5A5A40]/10', text: 'text-[#5A5A40]', border: 'border-[#5A5A40]/25' };
    case 'closed':
      return { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200' };
    case 'not accepted':
      return { bg: 'bg-stone-100', text: 'text-stone-600', border: 'border-stone-200' };
    default:
      return { bg: 'bg-stone-100', text: 'text-stone-700', border: 'border-stone-200' };
  }
}

export function getRectificationBadgeClass(status?: RectificationStatus | string | null): {
  bg: string;
  text: string;
} {
  const norm = status ? String(status).trim().toLowerCase() : '';
  switch (norm) {
    case 'rectified':
      return { bg: 'bg-emerald-100 text-emerald-900', text: 'text-emerald-900' };
    case 'in progress':
      return { bg: 'bg-amber-100 text-amber-900', text: 'text-amber-900' };
    case 'not started':
      return { bg: 'bg-stone-100 text-stone-700', text: 'text-stone-700' };
    case 'not rectified':
      return { bg: 'bg-rose-100 text-rose-900', text: 'text-rose-900' };
    case 'not applicable':
      return { bg: 'bg-stone-100 text-stone-600', text: 'text-stone-600' };
    default:
      return { bg: 'bg-stone-100 text-stone-600', text: 'text-stone-600' };
  }
}

export function getEngagementStatusBadgeClass(status?: EngagementStatus | string | null): {
  bg: string;
  text: string;
  border: string;
} {
  const norm = status ? String(status).trim().toLowerCase() : '';
  switch (norm) {
    case 'planning':
      return { bg: 'bg-stone-100', text: 'text-stone-700', border: 'border-stone-200' };
    case 'in progress':
      return { bg: 'bg-amber-50', text: 'text-amber-900', border: 'border-amber-200' };
    case 'fieldwork complete':
      return { bg: 'bg-[#5A5A40]/10', text: 'text-[#5A5A40]', border: 'border-[#5A5A40]/30' };
    case 'report issued':
      return { bg: 'bg-emerald-50', text: 'text-emerald-900', border: 'border-emerald-200' };
    case 'closed':
      return { bg: 'bg-stone-200', text: 'text-stone-800', border: 'border-stone-300' };
    default:
      return { bg: 'bg-stone-100', text: 'text-stone-700', border: 'border-stone-200' };
  }
}
