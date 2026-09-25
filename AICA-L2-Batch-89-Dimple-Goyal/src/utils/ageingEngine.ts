import { Invoice, CustomerAgeingSummary, AgeingBucketSummary } from '../types';

export const DEFAULT_AGEING_BUCKETS = [
  { label: 'Not Due', min: -999999, max: 0 },
  { label: '0–30 Days', min: 1, max: 30 },
  { label: '31–60 Days', min: 31, max: 60 },
  { label: '61–90 Days', min: 61, max: 90 },
  { label: '91–180 Days', min: 91, max: 180 },
  { label: '181–365 Days', min: 181, max: 365 },
  { label: '> 365 Days', min: 366, max: null }
];

/**
 * Calculate overdue days for an invoice relative to an asOfDate.
 * If dueDate is today or in future, overdue days is <= 0 (Not Due).
 */
export function calculateOverdueDays(dueDateStr: string, asOfDateStr: string = new Date().toISOString().split('T')[0]): number {
  const due = new Date(dueDateStr);
  const asOf = new Date(asOfDateStr);
  due.setHours(0, 0, 0, 0);
  asOf.setHours(0, 0, 0, 0);
  
  const diffTime = asOf.getTime() - due.getTime();
  return Math.floor(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * Assign an invoice to an ageing bucket label
 */
export function getAgeingBucketLabel(overdueDays: number): string {
  if (overdueDays <= 0) return 'Not Due';
  if (overdueDays <= 30) return '0–30 Days';
  if (overdueDays <= 60) return '31–60 Days';
  if (overdueDays <= 90) return '61–90 Days';
  if (overdueDays <= 180) return '91–180 Days';
  if (overdueDays <= 365) return '181–365 Days';
  return '> 365 Days';
}

export const getAgeingBucket = getAgeingBucketLabel;
export const buildCustomerAgeingMatrix = computeCustomerAgeing;

/**
 * Compute bucket-level aggregation
 */
export function computeBucketSummaries(
  invoices: Invoice[],
  asOfDateStr: string = new Date().toISOString().split('T')[0]
): AgeingBucketSummary[] {
  const buckets: Record<string, { amount: number; count: number; min: number; max: number | null }> = {
    'Not Due': { amount: 0, count: 0, min: -999999, max: 0 },
    '0–30 Days': { amount: 0, count: 0, min: 1, max: 30 },
    '31–60 Days': { amount: 0, count: 0, min: 31, max: 60 },
    '61–90 Days': { amount: 0, count: 0, min: 61, max: 90 },
    '91–180 Days': { amount: 0, count: 0, min: 91, max: 180 },
    '181–365 Days': { amount: 0, count: 0, min: 181, max: 365 },
    '> 365 Days': { amount: 0, count: 0, min: 366, max: null }
  };

  let totalOutstanding = 0;

  invoices.forEach(inv => {
    // Only consider invoices with an outstanding balance
    if (inv.balance > 0 && inv.status !== 'Cancelled' && inv.status !== 'Written Off') {
      const overdueDays = calculateOverdueDays(inv.dueDate, asOfDateStr);
      const label = getAgeingBucketLabel(overdueDays);
      if (buckets[label]) {
        buckets[label].amount += inv.balance;
        buckets[label].count += 1;
        totalOutstanding += inv.balance;
      }
    }
  });

  return Object.entries(buckets).map(([name, data]) => ({
    bucketName: name,
    minDays: data.min,
    maxDays: data.max,
    amount: data.amount,
    invoiceCount: data.count,
    percentage: totalOutstanding > 0 ? (data.amount / totalOutstanding) * 100 : 0
  }));
}

/**
 * Compute Customer-wise Ageing Matrix
 */
export function computeCustomerAgeing(
  invoices: Invoice[],
  asOfDateOrCustomers?: string | any[]
): CustomerAgeingSummary[] {
  const asOfDateStr = typeof asOfDateOrCustomers === 'string' ? asOfDateOrCustomers : new Date().toISOString().split('T')[0];
  const customerMap = new Map<string, CustomerAgeingSummary>();

  invoices.forEach(inv => {
    if (inv.balance <= 0 || inv.status === 'Cancelled' || inv.status === 'Written Off') {
      return;
    }

    if (!customerMap.has(inv.customerId)) {
      customerMap.set(inv.customerId, {
        customerId: inv.customerId,
        customerName: inv.customerName,
        totalOutstanding: 0,
        notDue: 0,
        days0to30: 0,
        days31to60: 0,
        days61to90: 0,
        days91to180: 0,
        days181to365: 0,
        daysAbove365: 0,
        days0_30: 0,
        days31_60: 0,
        days61_90: 0,
        days91_180: 0,
        days181_365: 0,
        days365Plus: 0,
        overdueAmount: 0,
        averageAgeDays: 0
      });
    }

    const summary = customerMap.get(inv.customerId)!;
    summary.totalOutstanding += inv.balance;

    const overdueDays = calculateOverdueDays(inv.dueDate, asOfDateStr);
    if (overdueDays <= 0) {
      summary.notDue += inv.balance;
    } else {
      summary.overdueAmount += inv.balance;
      if (overdueDays <= 30) {
        summary.days0to30 += inv.balance;
        summary.days0_30 = (summary.days0_30 || 0) + inv.balance;
      } else if (overdueDays <= 60) {
        summary.days31to60 += inv.balance;
        summary.days31_60 = (summary.days31_60 || 0) + inv.balance;
      } else if (overdueDays <= 90) {
        summary.days61to90 += inv.balance;
        summary.days61_90 = (summary.days61_90 || 0) + inv.balance;
      } else if (overdueDays <= 180) {
        summary.days91to180 += inv.balance;
        summary.days91_180 = (summary.days91_180 || 0) + inv.balance;
      } else if (overdueDays <= 365) {
        summary.days181to365 += inv.balance;
        summary.days181_365 = (summary.days181_365 || 0) + inv.balance;
      } else {
        summary.daysAbove365 += inv.balance;
        summary.days365Plus = (summary.days365Plus || 0) + inv.balance;
      }
    }
  });

  return Array.from(customerMap.values()).sort((a, b) => b.totalOutstanding - a.totalOutstanding);
}

/**
 * Calculate Days Sales Outstanding (DSO)
 * Standard Formula: (Total Outstanding Receivables / Total Credit Sales) * Period in Days
 */
export function calculateDSO(totalReceivables: number, totalSales: number, periodDays = 90): number {
  if (totalSales <= 0) return 0;
  return Math.round((totalReceivables / totalSales) * periodDays);
}
