import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { Invoice, Settings } from '../api';
import { formatRupeesPrint, formatDateDdMmmYyyy } from './format';

export interface FirmLetterhead {
  name: string;
  address: string;
  gstin: string;
  email: string;
  phone: string;
}

/**
 * Used only if the settings could not be loaded — a PDF with no letterhead at
 * all is worse than one carrying the firm's registered name.
 */
const FALLBACK_FIRM: FirmLetterhead = {
  name: 'M G S G & Associates',
  address: '',
  gstin: '',
  email: '',
  phone: '',
};

export function letterheadFrom(settings: Settings | null): FirmLetterhead {
  if (!settings) return FALLBACK_FIRM;
  return {
    name: settings.firmName,
    address: settings.firmAddress,
    gstin: settings.firmGstin,
    email: settings.firmEmail,
    phone: settings.firmPhone,
  };
}

const num = (v: string | number | null | undefined): number => {
  const n = Number(v ?? 0);
  return isFinite(n) ? n : 0;
};

/**
 * Render an invoice as a PDF and hand it to the browser.
 *
 * Money is printed with two decimals here — the rule in CLAUDE.md is that the
 * UI rounds to whole rupees but anything printed or sent to a client shows the
 * exact figure.
 */
export function downloadInvoicePdf(invoice: Invoice, firm: FirmLetterhead = FALLBACK_FIRM): void {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const left = 40;
  const right = pageWidth - 40;

  // ── Header ────────────────────────────────────────────────────────────────
  doc.setFont('helvetica', 'bold').setFontSize(16);
  doc.text(firm.name, left, 52);

  // Each line is skipped when empty, so a firm that has not filled in its
  // GSTIN gets a clean letterhead rather than a dangling label.
  doc.setFont('helvetica', 'normal').setFontSize(9).setTextColor(90);
  let headerY = 68;
  const headerLine = (text: string) => {
    if (!text.trim()) return;
    doc.text(text, left, headerY);
    headerY += 13;
  };
  headerLine(firm.address);
  headerLine(firm.gstin ? `GSTIN: ${firm.gstin}` : '');
  headerLine([firm.email, firm.phone].filter(Boolean).join('  •  '));

  doc.setTextColor(0).setFont('helvetica', 'bold').setFontSize(13);
  doc.text('TAX INVOICE', right, 52, { align: 'right' });
  doc.setFont('helvetica', 'normal').setFontSize(9);
  doc.text(invoice.invoiceNumber, right, 68, { align: 'right' });
  doc.text(`Date: ${formatDateDdMmmYyyy(invoice.invoiceDate)}`, right, 81, { align: 'right' });
  if (invoice.dueDate) doc.text(`Due: ${formatDateDdMmmYyyy(invoice.dueDate)}`, right, 94, { align: 'right' });

  doc.setDrawColor(200).line(left, 108, right, 108);

  // ── Bill to ───────────────────────────────────────────────────────────────
  doc.setFont('helvetica', 'bold').setFontSize(9);
  doc.text('BILL TO', left, 128);
  doc.setFont('helvetica', 'normal').setFontSize(10);
  doc.text(invoice.clientName, left, 144);

  let y = 158;
  doc.setFontSize(9).setTextColor(90);
  if (invoice.clientAddress) {
    // splitTextToSize wraps a long address instead of letting it run off the page.
    for (const line of doc.splitTextToSize(invoice.clientAddress, 260) as string[]) {
      doc.text(line, left, y);
      y += 12;
    }
  }
  if (invoice.clientGstin) {
    doc.text(`GSTIN: ${invoice.clientGstin}`, left, y);
    y += 12;
  }
  if (invoice.clientState) {
    doc.text(`Place of supply: ${invoice.clientState}`, left, y);
    y += 12;
  }
  doc.setTextColor(0);

  // ── Line items ────────────────────────────────────────────────────────────
  autoTable(doc, {
    startY: Math.max(y + 8, 196),
    head: [['#', 'Description', 'HSN/SAC', 'Qty', 'Rate', 'Amount']],
    body: invoice.lineItems.map((line, i) => [
      String(line.slNo ?? i + 1),
      line.description,
      line.hsnSac || '—',
      String(num(line.quantity)),
      formatRupeesPrint(num(line.rate)),
      formatRupeesPrint(num(line.amount)),
    ]),
    theme: 'grid',
    headStyles: { fillColor: [30, 58, 95], textColor: 255, fontSize: 9 },
    bodyStyles: { fontSize: 9 },
    columnStyles: {
      0: { cellWidth: 26, halign: 'center' },
      2: { cellWidth: 62 },
      3: { cellWidth: 40, halign: 'right' },
      4: { cellWidth: 70, halign: 'right' },
      5: { cellWidth: 80, halign: 'right' },
    },
    margin: { left, right: 40 },
  });

  // ── Totals ────────────────────────────────────────────────────────────────
  const totals: Array<[string, string]> = [['Taxable value', formatRupeesPrint(invoice.amount)]];
  if (invoice.cgstAmount) totals.push([`CGST @ ${num(invoice.cgstRate)}%`, formatRupeesPrint(invoice.cgstAmount)]);
  if (invoice.sgstAmount) totals.push([`SGST @ ${num(invoice.sgstRate)}%`, formatRupeesPrint(invoice.sgstAmount)]);
  if (invoice.igstAmount) totals.push([`IGST @ ${num(invoice.igstRate)}%`, formatRupeesPrint(invoice.igstAmount)]);
  totals.push(['Total', formatRupeesPrint(invoice.totalAmount)]);
  if (num(invoice.paidAmount) > 0) {
    totals.push(['Received', formatRupeesPrint(invoice.paidAmount)]);
    totals.push(['Balance due', formatRupeesPrint(num(invoice.totalAmount) - num(invoice.paidAmount))]);
  }

  const afterTable = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY;
  autoTable(doc, {
    startY: afterTable + 12,
    body: totals.map(([label, value]) => [label, `INR ${value}`]),
    theme: 'plain',
    bodyStyles: { fontSize: 9 },
    columnStyles: { 0: { halign: 'right', cellWidth: 120 }, 1: { halign: 'right', cellWidth: 100 } },
    // Right-aligned block: the table is pushed over rather than stretched.
    margin: { left: right - 220, right: 40 },
    didParseCell: (data) => {
      if (data.row.index === totals.findIndex(([l]) => l === 'Total')) {
        data.cell.styles.fontStyle = 'bold';
      }
    },
  });

  let footerY = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 24;

  if (invoice.notes) {
    doc.setFont('helvetica', 'bold').setFontSize(9);
    doc.text('Notes', left, footerY);
    doc.setFont('helvetica', 'normal').setTextColor(90);
    footerY += 13;
    for (const line of doc.splitTextToSize(invoice.notes, right - left) as string[]) {
      doc.text(line, left, footerY);
      footerY += 12;
    }
    doc.setTextColor(0);
  }

  doc.setFont('helvetica', 'normal').setFontSize(8).setTextColor(120);
  doc.text('This is a computer-generated invoice.', left, footerY + 16);
  doc.text(`For ${firm.name}`, right, footerY + 16, { align: 'right' });

  doc.save(`${invoice.invoiceNumber.replace(/\//g, '-')}.pdf`);
}
