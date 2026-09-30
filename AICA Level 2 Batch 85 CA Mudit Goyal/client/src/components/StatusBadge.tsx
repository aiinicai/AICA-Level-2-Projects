import React from 'react';
import { InvoiceStatus, AttendanceStatus } from '../api';

const INVOICE_TONES: Record<InvoiceStatus, string> = {
  DRAFT: 'bg-gray-100 text-gray-700',
  SENT: 'bg-blue-100 text-blue-800',
  PARTIALLY_PAID: 'bg-amber-100 text-amber-800',
  PAID: 'bg-green-100 text-green-800',
  CANCELLED: 'bg-red-100 text-red-800',
};

const ATTENDANCE_TONES: Record<AttendanceStatus, string> = {
  PRESENT: 'bg-green-100 text-green-800',
  WFH: 'bg-teal-100 text-teal-800',
  HALF_DAY: 'bg-amber-100 text-amber-800',
  ON_LEAVE: 'bg-blue-100 text-blue-800',
  ABSENT: 'bg-gray-100 text-gray-600',
};

/** Enum values are SCREAMING_SNAKE; people read "Partially paid". */
const humanise = (value: string) =>
  value.charAt(0) + value.slice(1).toLowerCase().replace(/_/g, ' ');

const StatusBadge: React.FC<{ status: InvoiceStatus | AttendanceStatus }> = ({ status }) => {
  const tone =
    (INVOICE_TONES as Record<string, string>)[status] ??
    (ATTENDANCE_TONES as Record<string, string>)[status] ??
    'bg-gray-100 text-gray-700';
  return <span className={`badge ${tone}`}>{humanise(status)}</span>;
};

export default StatusBadge;
