import { MonthCycle, DepartmentSubmission, LineItem, Department } from '../types';
import { convertInrToAud } from './formatters';

export function exportConsolidatedToCSV(
  month: MonthCycle,
  submissions: DepartmentSubmission[]
) {
  const headers = [
    'Month',
    'Department',
    'Category',
    'Description',
    'Priority',
    'Amount (INR)',
    'Amount (AUD)',
    'Exchange Rate Used',
    'Approved Amount (INR)',
    'Approved Amount (AUD)',
    'Item Status',
    'Justification / Notes',
    'Adjustment / Review Notes',
  ];

  const rows: string[][] = [];

  submissions.forEach((sub) => {
    sub.lineItems.forEach((item) => {
      const aud = convertInrToAud(item.amountInr, month.exchangeRate);
      const appInr = item.approvedAmountInr !== undefined ? item.approvedAmountInr : item.amountInr;
      const appAud = convertInrToAud(appInr, month.exchangeRate);

      rows.push([
        `"${month.label}"`,
        `"${item.department}"`,
        `"${item.category.replace(/"/g, '""')}"`,
        `"${item.description.replace(/"/g, '""')}"`,
        `"${item.priority}"`,
        item.amountInr.toString(),
        aud.toFixed(2),
        month.exchangeRate.toString(),
        appInr.toString(),
        appAud.toFixed(2),
        `"${item.status || 'pending'}"`,
        `"${(item.notes || '').replace(/"/g, '""')}"`,
        `"${(item.adjustmentNote || '').replace(/"/g, '""')}"`,
      ]);
    });
  });

  const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
  downloadBlob(csvContent, `Maropost_India_Cash_Requirements_${month.id}.csv`, 'text/csv;charset=utf-8;');
}

export function exportDepartmentSummaryToCSV(
  month: MonthCycle,
  submissions: DepartmentSubmission[]
) {
  const headers = [
    'Month',
    'Department',
    'Submission Status',
    'Submitted By',
    'Submitted At (IST)',
    'Total Requested (INR)',
    'Total Requested (AUD)',
    'Critical Items (INR)',
    'Important Items (INR)',
    'Optional Items (INR)',
    'Exchange Rate (INR->AUD)',
  ];

  const rows = submissions.map((sub) => {
    const totalInr = sub.lineItems.reduce((sum, item) => sum + item.amountInr, 0);
    const totalAud = convertInrToAud(totalInr, month.exchangeRate);
    const criticalInr = sub.lineItems
      .filter((i) => i.priority === 'Critical')
      .reduce((sum, i) => sum + i.amountInr, 0);
    const importantInr = sub.lineItems
      .filter((i) => i.priority === 'Important')
      .reduce((sum, i) => sum + i.amountInr, 0);
    const optionalInr = sub.lineItems
      .filter((i) => i.priority === 'Optional')
      .reduce((sum, i) => sum + i.amountInr, 0);

    return [
      `"${month.label}"`,
      `"${sub.department}"`,
      `"${sub.status}"`,
      `"${sub.submittedBy || 'N/A'}"`,
      `"${sub.submittedAt || 'N/A'}"`,
      totalInr.toString(),
      totalAud.toFixed(2),
      criticalInr.toString(),
      importantInr.toString(),
      optionalInr.toString(),
      month.exchangeRate.toString(),
    ].join(',');
  });

  const csvContent = [headers.join(','), ...rows].join('\n');
  downloadBlob(csvContent, `Maropost_India_Dept_Summary_${month.id}.csv`, 'text/csv;charset=utf-8;');
}

function downloadBlob(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
