import { jsPDF } from 'jspdf';
import type { FirmDetails, Supplier } from '../types';
import type { FollowUp } from './engine';
import { itc, msmeLabel } from './engine';

// jsPDF's built-in Helvetica has no ₹ glyph, so amounts in the PDF use "Rs.".
const n2 = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const rs = (n: number) => 'Rs. ' + n2.format(n || 0);

/** Downloads the supplier notice. */
export function supplierNoticePdf(f: FollowUp, firm: FirmDetails, period: string, supplier?: Supplier) {
  buildSupplierNotice(f, firm, period, supplier).save(`GSTR2B_Notice_${f.gstin}.pdf`);
}

/** Supplier notice listing invoices in our books that are missing from GSTR-2B. */
export function buildSupplierNotice(f: FollowUp, firm: FirmDetails, period: string, supplier?: Supplier) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const L = 15;
  const R = 195;
  const today = new Date().toLocaleDateString('en-IN');

  doc.setFillColor(15, 118, 110);
  doc.rect(0, 0, 210, 7, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.setTextColor(15, 23, 42);
  doc.text((firm.name || 'GST compliance notice').toUpperCase(), L, 17);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(100, 116, 139);
  doc.text(`Period: ${period || '-'}   |   Date: ${today}`, L, 22);
  if (firm.email || firm.phone) doc.text(`Contact: ${firm.email || '-'}   |   Phone: ${firm.phone || '-'}`, L, 26);
  doc.setDrawColor(226, 232, 240);
  doc.line(L, 30, R, 30);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11.5);
  doc.setTextColor(185, 28, 28);
  doc.text('STATEMENT OF INVOICES NOT REFLECTED IN GSTR-2B', L, 38);

  const kv = (label: string, value: string, y: number) => {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(71, 85, 105);
    doc.text(label, L, y);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(15, 23, 42);
    doc.text(value, 62, y);
  };
  kv('Supplier:', f.name || '-', 46);
  kv('Supplier GSTIN:', f.gstin, 52);
  kv('Recipient:', firm.name || '-', 58);
  kv('ITC at risk:', rs(f.itcAtRisk), 64);
  const msme = supplier && supplier.msmeStatus !== 'unverified' ? msmeLabel(supplier) + (supplier.udyamNumber ? ` (Udyam ${supplier.udyamNumber})` : '') : 'Not recorded';
  kv('MSME status:', msme, 70);

  const isMse = supplier?.msmeStatus === 'micro' || supplier?.msmeStatus === 'small';
  let para =
    'The input tax credit on the invoices listed below is recorded in our books but does not appear in our GSTR-2B. ' +
    'This usually means the invoice has not been reported in your GSTR-1 / IFF, or was reported with a different GSTIN, ' +
    'invoice number or amount. Under Section 16(2)(aa) of the CGST Act we can claim this credit only after it appears in GSTR-2B. ' +
    'Please report or correct these invoices in your next GSTR-1 and confirm to us.';
  if (isMse)
    para +=
      ' As you are registered as a micro / small enterprise, we note the 15 / 45 day payment period under Section 43B(h) of the Income-tax Act.';
  const lines = doc.splitTextToSize(para, 174);
  const boxH = lines.length * 3.4 + 4.5;
  doc.setFillColor(254, 242, 242);
  doc.setDrawColor(252, 165, 165);
  doc.rect(L, 75, 180, boxH, 'FD');
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(127, 29, 29);
  doc.text(lines, L + 3, 80);

  const cols = [
    { t: 'Invoice no.', x: 17, a: 'left' as const },
    { t: 'Date', x: 52, a: 'left' as const },
    { t: 'Taxable', x: 98, a: 'right' as const },
    { t: 'IGST', x: 122, a: 'right' as const },
    { t: 'CGST', x: 144, a: 'right' as const },
    { t: 'SGST', x: 166, a: 'right' as const },
    { t: 'ITC', x: 193, a: 'right' as const },
  ];
  const header = (y: number) => {
    doc.setFillColor(241, 245, 249);
    doc.rect(L, y, 180, 7, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(51, 65, 85);
    cols.forEach((c) => doc.text(c.t, c.x, y + 4.7, { align: c.a }));
    return y + 7;
  };
  let y = header(75 + boxH + 5);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.8);
  const tot = { taxable: 0, igst: 0, cgst: 0, sgst: 0, itc: 0 };
  f.items.forEach((r, i) => {
    if (y > 268) {
      doc.addPage();
      y = header(15);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.8);
    }
    if (i % 2) {
      doc.setFillColor(248, 250, 252);
      doc.rect(L, y, 180, 6.4, 'F');
    }
    doc.setTextColor(15, 23, 42);
    const vals = [String(r.inv).slice(0, 22), r.date || '-', n2.format(r.taxable), n2.format(r.igst), n2.format(r.cgst), n2.format(r.sgst), n2.format(itc(r))];
    cols.forEach((c, ci) => doc.text(vals[ci], c.x, y + 4.3, { align: c.a }));
    tot.taxable += r.taxable;
    tot.igst += r.igst;
    tot.cgst += r.cgst;
    tot.sgst += r.sgst;
    tot.itc += itc(r);
    y += 6.4;
  });
  if (y > 262) {
    doc.addPage();
    y = 15;
  }
  doc.setFillColor(226, 232, 240);
  doc.rect(L, y, 180, 7, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(15, 23, 42);
  const totals = ['TOTAL', '', n2.format(tot.taxable), n2.format(tot.igst), n2.format(tot.cgst), n2.format(tot.sgst), n2.format(tot.itc)];
  cols.forEach((c, ci) => totals[ci] && doc.text(totals[ci], c.x, y + 4.7, { align: c.a }));
  y += 16;
  if (y > 255) {
    doc.addPage();
    y = 20;
  }
  doc.setFontSize(8.5);
  doc.setTextColor(51, 65, 85);
  doc.text(`For ${firm.name || '________________'}`, L, y);
  doc.setFont('helvetica', 'normal');
  if (firm.ca) doc.text(firm.ca + (firm.memNo ? `  (M. No. ${firm.memNo})` : ''), L, y + 12);
  doc.text('Authorised signatory', L, y + (firm.ca ? 16 : 12));

  const pages = doc.getNumberOfPages();
  for (let p = 1; p <= pages; p++) {
    doc.setPage(p);
    doc.setFontSize(7);
    doc.setTextColor(148, 163, 184);
    doc.text('Computer-generated statement from the recipient\'s books of account.', L, 289);
    doc.text(`Page ${p} of ${pages}`, R, 289, { align: 'right' });
  }
  return doc;
}

/** Plain-text e-mail for the same follow-up. */
export function supplierEmail(f: FollowUp, firm: FirmDetails, period: string) {
  const subject = `Invoices not reflected in our GSTR-2B (${period || 'current period'}) - GSTIN ${f.gstin}`;
  const head = 'Invoice no.          Date         Taxable value         ITC';
  const rule = '-'.repeat(head.length);
  const body = [
    `Dear ${f.name || 'Sir / Madam'},`,
    '',
    `While reconciling our purchase register with GSTR-2B for ${period || 'the current period'}, we found that the invoices below are recorded in our books but do not appear in our GSTR-2B.`,
    '',
    `Supplier GSTIN: ${f.gstin}`,
    '',
    head,
    rule,
    ...f.items.map(
      (r) =>
        `${String(r.inv).padEnd(20).slice(0, 20)} ${String(r.date || '-').padEnd(12)} ${n2.format(r.taxable).padStart(14)} ${n2.format(itc(r)).padStart(14)}`
    ),
    rule,
    `Total ITC at risk: ${rs(f.itcAtRisk)}`,
    '',
    'We can claim this input tax credit only after it appears in our GSTR-2B (Section 16(2)(aa) of the CGST Act). Please report or correct these invoices in your next GSTR-1 / IFF and confirm by reply.',
    '',
    `For any clarification, contact ${firm.email || '[e-mail]'}${firm.phone ? ` / ${firm.phone}` : ''}.`,
    '',
    'Regards,',
    firm.ca || '',
    `For ${firm.name || '[Firm name]'}`,
  ]
    .filter((l, i, a) => !(l === '' && a[i - 1] === ''))
    .join('\n');
  return { subject, body };
}
