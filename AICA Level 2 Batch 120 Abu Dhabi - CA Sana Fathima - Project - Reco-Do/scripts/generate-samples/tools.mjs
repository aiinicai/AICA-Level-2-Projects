// Tools samples: PDFs for PDF -> Excel / Merge / Split, monthly statements for Merge Files,
// a trial balance for Excel -> PDF and a messy sheet for the Data Cleaner.
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { jsPDF } from 'jspdf';
import { autoTable } from 'jspdf-autotable';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import { Rng } from './lib/rng.mjs';
import { d, addDays, businessDays, fmtDate, fmtDMY, fmtAmt, toAed, pad } from './lib/util.mjs';
import { newWorkbook, writeTable, saveWorkbook, saveBytes, FIXED_DATE, AMT_FMT, DATE_FMT } from './lib/excel.mjs';
import { OUR_COMPANY, CUSTOMERS, SUPPLIERS, POS_MERCHANTS } from './lib/names.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
export const SCANNED_PNG = join(HERE, 'assets', 'scanned_page.png');

function newPdf(opts = {}) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4', compress: true, ...opts });
  doc.setCreationDate(FIXED_DATE);
  doc.setFileId('5245434F444F53414D504C4532303236');
  doc.setProperties({ creator: 'Reco-Do sample generator', author: 'Reco-Do' });
  return doc;
}
const pdfBytes = (doc) => Buffer.from(doc.output('arraybuffer'));

// ------------------------------------------------------------ statement transaction stream
/** Deterministic stream of bank-statement lines (used by the 6-page PDF and the scanned-page PDF). */
export function statementLines(seed, y, m, count, opening) {
  const rng = new Rng(seed);
  const lines = [];
  let bal = opening;
  const days = businessDays(y, m);
  // ~1 in 5 lines gets a long narration that wraps onto exactly 2 lines in the PDF (never 3).
  const tail = () => rng.pick([' - SETTLEMENT OF INV 0412 AND 0413', ' - PART PAYMENT AGAINST LPO 7781', ' - RETENTION RELEASE AS PER CONTRACT', ' - ADVANCE FOR SEPTEMBER DELIVERIES']);
  const push = (date, desc, ref, wd, dep) => {
    bal += dep - wd;
    lines.push({ date, valueDate: date, desc, ref, wd, dep, bal });
  };
  for (let i = 0; lines.length < count; i++) {
    const date = days[Math.floor((lines.length * days.length) / count)]; // spread evenly over the month
    const r = rng.float();
    const long = rng.chance(0.22);
    if (r < 0.18) {
      const p = rng.pick(CUSTOMERS).toUpperCase();
      push(date, `INWARD TT ${p}${long ? tail() : ''}`, `TT2608${rng.digits(4)}`, 0, rng.cents(2500, 65000));
    } else if (r < 0.32) {
      const ref = `${rng.int(1, 9)}${rng.digits(5)}`;
      push(date, `CHQ DEP ${ref} ${rng.pick(CUSTOMERS).toUpperCase()}`, ref, 0, rng.cents(1500, 30000));
    } else if (r < 0.52) {
      const p = rng.pick(SUPPLIERS).toUpperCase();
      push(date, `FT OUT ${p}${long ? tail() : ''}`, `FT2608${rng.letters(3)}`, rng.cents(800, 42000), 0);
    } else if (r < 0.68) {
      const no = pad(4400 + i, 6);
      push(date, `CHQ ${no} PRESENTED - CLEARING`, no, rng.cents(900, 25000), 0);
    } else if (r < 0.86) {
      push(date, `POS ${rng.pick(POS_MERCHANTS)} ****2231`, `6${rng.digits(11)}`, rng.cents(40, 1800), 0);
    } else if (r < 0.95) {
      push(date, `POS SETTLEMENT MID 200456710 TID 0${rng.int(1, 3)}`, `MS2608${rng.digits(4)}`, 0, rng.cents(1200, 9000));
    } else if (lines.length < count - 1) {
      const fee = rng.pick([2500, 5000, 7500, 3500]);
      push(date, 'CHARGES - OUTWARD TT COMMISSION', `SC2608${rng.digits(5)}`, fee, 0);
      push(date, 'VAT 5% ON CHARGES', `SC2608${rng.digits(5)}`, Math.round(fee * 0.05), 0);
    }
  }
  return lines;
}

// ------------------------------------------------------------ 6-page digital statement
function buildStatementPdf(lines, opening) {
  const doc = newPdf();
  const close = lines.length ? lines[lines.length - 1].bal : opening;
  const body = [
    ['01-Aug-2026', '', 'OPENING BALANCE', '', '', '', fmtAmt(opening)],
    ...lines.map((l) => [fmtDate(l.date), fmtDate(l.valueDate), l.desc, l.ref, l.wd ? fmtAmt(l.wd) : '', l.dep ? fmtAmt(l.dep) : '', fmtAmt(l.bal)]),
    ['31-Aug-2026', '', 'CLOSING BALANCE', '', '', '', fmtAmt(close)],
  ];
  autoTable(doc, {
    head: [['Date', 'Value Date', 'Description', 'Cheque / Ref', 'Withdrawals', 'Deposits', 'Balance']],
    body,
    startY: 44,
    margin: { top: 44, bottom: 18, left: 9, right: 9 },
    showHead: 'everyPage',
    theme: 'grid',
    styles: { font: 'helvetica', fontSize: 7.5, cellPadding: 1.1, lineWidth: 0.1, lineColor: [190, 190, 190], textColor: [20, 20, 20] },
    headStyles: { fillColor: [0, 61, 121], textColor: 255, fontStyle: 'bold' },
    columnStyles: {
      0: { cellWidth: 18 }, 1: { cellWidth: 18 }, 2: { cellWidth: 72 }, 3: { cellWidth: 23 },
      4: { cellWidth: 20, halign: 'right' }, 5: { cellWidth: 20, halign: 'right' }, 6: { cellWidth: 21, halign: 'right' },
    },
    didParseCell: (data) => {
      if (data.section === 'body' && /BALANCE$/.test(String(data.row.raw[2]))) data.cell.styles.fontStyle = 'bold';
    },
    didDrawPage: () => {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(14);
      doc.setTextColor(0, 61, 121);
      doc.text('Emirates NBD Bank PJSC', 10, 14);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(60, 60, 60);
      doc.text('Deira Main Branch, Baniyas Road, P.O. Box 777, Dubai, United Arab Emirates', 10, 19);
      doc.setTextColor(20, 20, 20);
      doc.setFontSize(9);
      doc.text(`Account Name: ${OUR_COMPANY.toUpperCase()}`, 10, 27);
      doc.text('Account No: 1012-4587-001      Currency: AED', 10, 32);
      doc.text('Statement Period: 01-Aug-2026 to 31-Aug-2026', 10, 37);
      doc.text('STATEMENT OF ACCOUNT', 200, 27, { align: 'right' });
    },
  });
  const n = doc.getNumberOfPages();
  for (let i = 1; i <= n; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(90, 90, 90);
    doc.text(`Page ${i} of ${n}`, 105, 290, { align: 'center' });
    doc.text('This is a computer generated statement and does not require a signature.', 10, 285);
  }
  return { doc, pages: n, close };
}

/** Count descriptions that autotable wraps onto 2 lines (Description column 72 mm, padding 1.1 mm, 7.5 pt). */
function wrappedCount(doc, lines) {
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  const n = lines.map((l) => doc.splitTextToSize(l.desc, 72 - 2 * 1.1).length);
  if (n.some((x) => x > 2)) throw new Error('a statement description wraps onto 3 lines');
  return n.filter((x) => x === 2).length;
}

function pickRowsForPages(build, targetPages, maxRows) {
  let first = -1, over = -1;
  for (let n = 10; n <= maxRows; n += 2) {
    const p = build(n).pages;
    if (p === targetPages && first < 0) first = n;
    if (p > targetPages) { over = n; break; }
  }
  if (first < 0 || over < 0) throw new Error('could not size PDF');
  return Math.floor((first + over) / 2 / 2) * 2 - 6; // a comfortably full last page
}

// ------------------------------------------------------------ price list
function buildPriceList(items) {
  const doc = newPdf();
  autoTable(doc, {
    head: [['Item Code', 'Description', 'UoM', 'Unit Price AED', 'VAT %']],
    body: items.map((x) => [x.code, x.desc, x.uom, fmtAmt(x.price), x.vat]),
    startY: 40,
    margin: { top: 40, bottom: 20, left: 14, right: 14 },
    theme: 'striped',
    styles: { fontSize: 8.5, cellPadding: 1.8 },
    headStyles: { fillColor: [46, 125, 50] },
    columnStyles: { 0: { cellWidth: 28 }, 1: { cellWidth: 92 }, 2: { cellWidth: 18 }, 3: { cellWidth: 26, halign: 'right' }, 4: { cellWidth: 18, halign: 'center' } },
    didDrawPage: () => {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(15);
      doc.text('GULF SUPPLIES LLC', 14, 16);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.text('Warehouse 7, Al Quoz Industrial Area 4, Dubai  |  TRN 100229384700003', 14, 22);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11);
      doc.text('Price List - effective 01-Sep-2026 (prices exclusive of VAT)', 14, 32);
      doc.setFont('helvetica', 'normal');
    },
  });
  const n = doc.getNumberOfPages();
  for (let i = 1; i <= n; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.text(`Page ${i} of ${n}`, 105, 288, { align: 'center' });
  }
  return { doc, pages: n };
}

function priceItems(rng, n) {
  const base = [
    ['A4 Copier Paper 80gsm', 'BOX'], ['Industrial Nitrile Gloves (L)', 'BOX'], ['Heavy Duty Floor Cleaner 5L', 'CAN'], ['Safety Shoes S3 Steel Toe', 'PAIR'],
    ['Cable Ties 300mm Black', 'PKT'], ['Toner Cartridge 26A Compatible', 'PC'], ['Pallet Racking Beam 2.7m', 'PC'], ['Stretch Film 23mic 500mm', 'ROLL'],
    ['PPE Coverall Disposable', 'PC'], ['Hi-Vis Safety Vest', 'PC'], ['Packing Tape 48mm Clear', 'ROLL'], ['Corrugated Box 5-Ply 600x400', 'PC'],
    ['Hand Sanitiser 500ml', 'BTL'], ['Bin Liners 120L', 'ROLL'], ['LED Tube Light 18W', 'PC'], ['Extension Socket 4-Way 5m', 'PC'],
    ['Whiteboard Marker Assorted', 'PKT'], ['Lever Arch File A4', 'PC'], ['Fire Extinguisher 6kg DCP', 'PC'], ['First Aid Kit (50 person)', 'SET'],
    ['Safety Helmet White', 'PC'], ['Ear Plugs Corded', 'BOX'], ['Pallet Wrap Dispenser', 'PC'], ['Label Roll 100x150 Thermal', 'ROLL'],
  ];
  const out = [];
  for (let i = 0; i < n; i++) {
    const [desc, uom] = base[i % base.length];
    const variant = Math.floor(i / base.length);
    out.push({ code: `GS-${pad(10010 + i * 7, 6)}`, desc: variant ? `${desc} - ${['Premium', 'Economy', 'Bulk pack'][variant - 1] ?? 'Grade ' + variant}` : desc, uom, price: rng.cents(2, 950), vat: i % 17 === 9 ? '0%' : '5%' });
  }
  return out;
}

// ------------------------------------------------------------ scanned page statement (pages 1-2 digital, page 3 image)
export const SCANNED_OPENING = 31245090;
export function scannedStatementData() {
  // 2 digital pages of ~34 lines each + 22 lines on the scanned page 3
  const lines = statementLines(77001, 2026, 8, 90, SCANNED_OPENING);
  return { digital: lines.slice(0, 68), scanned: lines.slice(68) };
}

async function buildScannedPdf() {
  const { digital, scanned } = scannedStatementData();
  const pdf = await PDFDocument.create();
  pdf.setCreationDate(FIXED_DATE);
  pdf.setModificationDate(FIXED_DATE);
  pdf.setProducer('Reco-Do sample generator');
  pdf.setCreator('Reco-Do sample generator');
  pdf.setTitle('Statement with scanned page');
  const font = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const W = 595.28, H = 841.89;
  const cols = [[36, 'Date'], [96, 'Description'], [330, 'Reference'], [410, 'Debit'], [470, 'Credit'], [535, 'Balance']];
  const right = new Set(['Debit', 'Credit', 'Balance']);
  for (let p = 0; p < 2; p++) {
    const page = pdf.addPage([W, H]);
    page.drawText('Al Safa Commercial Bank PJSC - Statement of Account', { x: 36, y: H - 50, size: 13, font: bold, color: rgb(0.1, 0.2, 0.45) });
    page.drawText(`${OUR_COMPANY}   |   Account 0450-7781-0021   |   AED   |   01-Aug-2026 to 31-Aug-2026`, { x: 36, y: H - 68, size: 8.5, font });
    let y = H - 100;
    cols.forEach(([x, h]) => page.drawText(h, { x: right.has(h) ? x + 40 - bold.widthOfTextAtSize(h, 8.5) : x, y, size: 8.5, font: bold }));
    page.drawLine({ start: { x: 36, y: y - 4 }, end: { x: W - 36, y: y - 4 }, thickness: 0.6 });
    y -= 18;
    const rows = digital.slice(p * 34, p * 34 + 34);
    if (p === 0) {
      page.drawText('01-Aug-2026', { x: 36, y, size: 8, font });
      page.drawText('OPENING BALANCE', { x: 96, y, size: 8, font: bold });
      const t = fmtAmt(SCANNED_OPENING);
      page.drawText(t, { x: 575 - font.widthOfTextAtSize(t, 8), y, size: 8, font });
      y -= 18;
    }
    for (const l of rows) {
      const cells = [fmtDate(l.date), l.desc.length > 46 ? l.desc.slice(0, 44) + '..' : l.desc, l.ref, l.wd ? fmtAmt(l.wd) : '', l.dep ? fmtAmt(l.dep) : '', fmtAmt(l.bal)];
      cells.forEach((c, i) => {
        if (!c) return;
        const [x, h] = cols[i];
        const xx = right.has(h) ? x + 40 - font.widthOfTextAtSize(c, 8) : x;
        page.drawText(c, { x: xx, y, size: 8, font });
      });
      y -= 18;
    }
    page.drawText(`Page ${p + 1} of 3`, { x: W / 2 - 20, y: 30, size: 8, font });
  }
  const png = await pdf.embedPng(await readFile(SCANNED_PNG));
  const page3 = pdf.addPage([W, H]);
  page3.drawImage(png, { x: 0, y: 0, width: W, height: H });
  return { bytes: await pdf.save({ useObjectStreams: false }), scanned };
}

// ------------------------------------------------------------ simple labelled pages (merge / split / password)
function labelledPages(title, n, subtitle, opts = {}) {
  const doc = newPdf(opts);
  for (let i = 1; i <= n; i++) {
    if (i > 1) doc.addPage();
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(opts.big ? 54 : 30);
    doc.text(opts.big ? `Page ${i} of ${n}` : `${title}`, 105, opts.big ? 140 : 70, { align: 'center' });
    doc.setFontSize(opts.big ? 18 : 40);
    if (!opts.big) doc.text(`Page ${i} of ${n}`, 105, 110, { align: 'center' });
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(12);
    doc.text(typeof subtitle === 'function' ? subtitle(i) : subtitle, 105, opts.big ? 160 : 135, { align: 'center', maxWidth: 170 });
    doc.setFontSize(9);
    doc.text(`${opts.footer ?? title} - page ${i}`, 105, 285, { align: 'center' });
  }
  return doc;
}

// ------------------------------------------------------------ monthly statements for Merge Files
function monthlyStatement(rng, y, m, opening, n) {
  const days = businessDays(y, m);
  const rows = [];
  let bal = opening;
  for (let i = 0; i < n; i++) {
    const dt = days[Math.min(days.length - 1, Math.floor((i / n) * days.length))];
    const inflow = rng.chance(0.42);
    const amt = inflow ? rng.cents(800, 38000) : rng.cents(45, 26000);
    bal += inflow ? amt : -amt;
    const desc = inflow
      ? rng.pick([`INWARD TT FROM ${rng.pick(CUSTOMERS).toUpperCase()}`, `CHQ DEPOSIT ${rng.digits(6)}`, 'POS SETTLEMENT MID 200456710', 'CASH DEPOSIT CDM'])
      : rng.pick([`FT OUT TO ${rng.pick(SUPPLIERS).toUpperCase()}`, `POS PURCHASE ${rng.pick(POS_MERCHANTS)}`, 'DIRECT DEBIT UTILITIES ELEC & WATER', `CHEQUE NO ${pad(rng.int(4100, 4400), 6)} PRESENTED`]);
    rows.push({ date: dt, desc, ref: `${inflow ? 'CR' : 'DR'}${y % 100}${pad(m, 2)}${pad(i + 1, 4)}`, dr: inflow ? null : toAed(amt), cr: inflow ? toAed(amt) : null, bal: toAed(bal) });
  }
  return { rows, close: bal };
}

// ------------------------------------------------------------ main
export async function generateTools(outDir) {
  const rng = new Rng(2026090606);
  const T = `${outDir}/tools`;
  const out = {};

  // 1. 6-page digital statement
  const build = (n) => buildStatementPdf(statementLines(66001, 2026, 8, n, 87654321), 87654321);
  const nRows = pickRowsForPages(build, 6, 400);
  const st = build(nRows);
  const stmtLines = statementLines(66001, 2026, 8, nRows, 87654321);
  if (st.pages !== 6) throw new Error(`statement PDF has ${st.pages} pages`);
  await saveBytes(`${T}/Bank_Statement_6_pages_digital.pdf`, pdfBytes(st.doc));
  out.statementPdf = { rows: nRows, opening: 87654321, close: st.close, wrapped: wrappedCount(st.doc, stmtLines) };

  // 2. Price list (2 pages)
  const allItems = priceItems(new Rng(55001), 140);
  const nItems = pickRowsForPages((n) => buildPriceList(allItems.slice(0, n)), 2, 140);
  const pl = buildPriceList(allItems.slice(0, nItems));
  if (pl.pages !== 2) throw new Error('price list must be 2 pages');
  await saveBytes(`${T}/Price_List_digital.pdf`, pdfBytes(pl.doc));
  out.priceList = { items: nItems };

  // 3. Statement with scanned page 3
  const sc = await buildScannedPdf();
  await saveBytes(`${T}/Statement_with_scanned_page.pdf`, sc.bytes);
  out.scanned = { scannedRows: sc.scanned.length };

  // 4. Password protected
  {
    const doc = newPdf({ encryption: { userPassword: 'reco123', ownerPassword: 'reco-owner-2026', userPermissions: ['print'] } });
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.text('Confidential - Salary Transfer Advice September 2026', 14, 24);
    doc.setFont('helvetica', 'normal');
    autoTable(doc, {
      startY: 34,
      head: [['Employee No', 'Name', 'Bank', 'Net Pay AED']],
      body: [['00104', 'Ahmed Saleh', 'Emirates NBD', '8,450.00'], ['00117', 'Priya Nair Menon', 'ADCB', '12,275.50'], ['00133', 'Jose Bautista', 'Mashreq', '4,980.25']],
    });
    await saveBytes(`${T}/Password_protected.pdf`, pdfBytes(doc));
  }

  // 5. Merge parts and split file
  await saveBytes(`${T}/Merge_Part1.pdf`, pdfBytes(labelledPages('Merge Part 1', 3, (i) => ['Invoice pack - cover sheet', 'Invoice pack - INV-00151 Al Noor Trading LLC', 'Invoice pack - delivery notes'][i - 1], { footer: 'Merge_Part1.pdf' })));
  await saveBytes(`${T}/Merge_Part2.pdf`, pdfBytes(labelledPages('Merge Part 2', 2, (i) => ['Supporting documents - LPO copy', 'Supporting documents - bank advice'][i - 1], { footer: 'Merge_Part2.pdf' })));
  await saveBytes(`${T}/Split_Me_12_pages.pdf`, pdfBytes(labelledPages('Split me', 12, (i) => `Section ${String.fromCharCode(64 + Math.ceil(i / 3))} - split test document`, { big: true, footer: 'Split_Me_12_pages.pdf' })));

  // 6. Monthly statements with drifting headers
  const mrng = new Rng(44001);
  const jul = monthlyStatement(mrng, 2026, 7, 41234055, 44);
  const aug = monthlyStatement(mrng, 2026, 8, jul.close, 51);
  const sep = monthlyStatement(mrng, 2026, 9, aug.close, 47);
  {
    // Jul: 4 junk rows, header on row 5
    const wb = newWorkbook();
    const ws = wb.addWorksheet('Jul 2026');
    ['Al Safa Commercial Bank PJSC', `Account: 0450-7781-0021  ${OUR_COMPANY}`, 'Statement for July 2026', ''].forEach((t, i) => t && (ws.getCell(i + 1, 1).value = t));
    writeTable(ws, {
      headerRow: 5,
      columns: [
        { header: 'Txn Date', key: 'date', width: 13, type: 'date' }, { header: 'Narration', key: 'desc', width: 48 }, { header: 'Reference', key: 'ref', width: 14 },
        { header: 'Debit', key: 'dr', width: 14, type: 'amount' }, { header: 'Credit', key: 'cr', width: 14, type: 'amount' }, { header: 'Balance', key: 'bal', width: 16, type: 'amount' },
      ],
      rows: [{ date: d(2026, 7, 1), desc: 'Opening balance', bal: toAed(41234055), _style: 'balance' }, ...jul.rows, { date: d(2026, 7, 31), desc: 'Closing balance', bal: toAed(jul.close), _style: 'balance' }],
    });
    await saveWorkbook(wb, `${T}/Statement_Jul2026.xlsx`);
  }
  {
    // Aug: header on row 1, a repeated header row in the middle (page-break export)
    const wb = newWorkbook();
    const ws = wb.addWorksheet('Aug 2026');
    const hdr = { date: 'Transaction Date', desc: 'Description', ref: 'Ref No', dr: 'Withdrawal', cr: 'Deposit', bal: 'Balance', _style: 'balance' };
    const rows = [{ date: d(2026, 8, 1), desc: 'Opening balance', bal: toAed(jul.close), _style: 'balance' }, ...aug.rows.slice(0, 26), hdr, ...aug.rows.slice(26), { date: d(2026, 8, 31), desc: 'Closing balance', bal: toAed(aug.close), _style: 'balance' }];
    writeTable(ws, {
      headerRow: 1,
      columns: [
        { header: 'Transaction Date', key: 'date', width: 16, type: 'date' }, { header: 'Description', key: 'desc', width: 48 }, { header: 'Ref No', key: 'ref', width: 14 },
        { header: 'Withdrawal', key: 'dr', width: 14, type: 'amount' }, { header: 'Deposit', key: 'cr', width: 14, type: 'amount' }, { header: 'Balance', key: 'bal', width: 16, type: 'amount' },
      ],
      rows,
    });
    await saveWorkbook(wb, `${T}/Statement_Aug2026.xlsx`);
  }
  {
    // Sep: 2 title rows, header on row 3, total row at the end
    const wb = newWorkbook();
    const ws = wb.addWorksheet('Sep 2026');
    ws.getCell('A1').value = 'Al Safa Commercial Bank PJSC - Account 0450-7781-0021 - September 2026';
    const totDr = sep.rows.reduce((s, r) => s + Math.round((r.dr ?? 0) * 100), 0);
    const totCr = sep.rows.reduce((s, r) => s + Math.round((r.cr ?? 0) * 100), 0);
    writeTable(ws, {
      headerRow: 3,
      columns: [
        { header: 'Date', key: 'date', width: 13, type: 'date' }, { header: 'Details', key: 'desc', width: 48 }, { header: 'Reference No.', key: 'ref', width: 14 },
        { header: 'Debit (AED)', key: 'dr', width: 14, type: 'amount' }, { header: 'Credit (AED)', key: 'cr', width: 14, type: 'amount' }, { header: 'Running Balance', key: 'bal', width: 16, type: 'amount' },
      ],
      rows: [
        { date: d(2026, 9, 1), desc: 'Balance brought forward', bal: toAed(aug.close), _style: 'balance' },
        ...sep.rows,
        { desc: 'Total', dr: toAed(totDr), cr: toAed(totCr), _style: 'total' },
        { date: d(2026, 9, 30), desc: 'Closing balance', bal: toAed(sep.close), _style: 'balance' },
      ],
    });
    await saveWorkbook(wb, `${T}/Statement_Sep2026.xlsx`);
  }
  out.monthly = { jul: jul.rows.length, aug: aug.rows.length, sep: sep.rows.length, julClose: jul.close, augClose: aug.close, sepClose: sep.close };

  // 7. Trial balance to print (~120 rows)
  {
    const groups = [
      ['1', 'Non-current assets', 'Dr', ['Land & building', 'Furniture & fixtures', 'Motor vehicles', 'Computer equipment', 'Warehouse racking', 'Accumulated depreciation - furniture', 'Accumulated depreciation - vehicles', 'Accumulated depreciation - computers', 'Capital work in progress', 'Right-of-use asset - warehouse']],
      ['12', 'Current assets', 'Dr', ['Cash in hand - Deira', 'Cash in hand - Al Quoz', 'Petty cash', 'ENBD current a/c 1012-4587-001', 'ENBD call a/c 1012-4587-002', 'Al Safa Bank a/c 0450-7781-0021', 'Trade receivables - local', 'Trade receivables - export', 'Allowance for doubtful debts', 'Advances to suppliers', 'Staff advances', 'Prepaid rent', 'Prepaid insurance', 'Security deposits', 'Inventory - packaging', 'Inventory - consumables', 'Inventory - goods in transit', 'VAT recoverable', 'Due from DPI Abu Dhabi', 'Other receivables']],
      ['2', 'Current liabilities', 'Cr', ['Trade payables - local', 'Trade payables - import', 'Accrued expenses', 'Accrued salaries', 'End of service benefits provision', 'Leave salary provision', 'Air ticket provision', 'VAT payable', 'Corporate tax payable', 'Customer advances', 'PDC payable', 'Lease liability - current', 'Due to directors', 'Retention payable']],
      ['3', 'Equity', 'Cr', ['Share capital', 'Statutory reserve', 'Retained earnings - b/f', 'Current year drawings']],
      ['4', 'Revenue', 'Cr', ['Sales - packaging materials', 'Sales - consumables', 'Sales - export', 'Sales returns', 'Discount allowed', 'Other income', 'Interest income', 'Foreign exchange gain', 'Scrap sales']],
      ['5', 'Cost of sales', 'Dr', ['Purchases - packaging', 'Purchases - consumables', 'Freight inwards', 'Customs duty', 'Clearing charges', 'Purchase returns', 'Discount received', 'Stock adjustment']],
      ['6', 'Operating expenses', 'Dr', ['Salaries & wages', 'Housing allowance', 'Transport allowance', 'Overtime', 'Staff medical insurance', 'Visa & labour charges', 'Staff accommodation', 'Staff welfare', 'Office rent', 'Warehouse rent', 'Electricity & water', 'Telephone & internet', 'Printing & stationery', 'Courier & postage', 'Fuel - vehicles', 'Vehicle repairs', 'Vehicle insurance', 'Salik & parking', 'Repairs & maintenance', 'Cleaning services', 'Security services', 'Advertising', 'Exhibition expenses', 'Travel - local', 'Travel - overseas', 'Entertainment', 'Legal fees', 'Audit fees', 'Consultancy fees', 'Trade licence renewal', 'Insurance - general', 'Bank charges', 'Interest on lease', 'Depreciation - furniture', 'Depreciation - vehicles', 'Depreciation - computers', 'Depreciation - ROU asset', 'Bad debts written off', 'Software subscriptions', 'IT support', 'Training', 'Uniforms', 'Donations', 'Miscellaneous expenses', 'Penalties & fines', 'Recruitment costs', 'Management fee - group', 'Shared staff cost recharge', 'Exchange loss', 'Sundry expenses', 'Packing materials consumed', 'Pest control', 'Water dispensers', 'Medical tests', 'Gifts & samples']],
    ];
    const trng = new Rng(33001);
    const rows = [];
    let dr = 0, cr = 0;
    for (const [code, grp, side, names] of groups) {
      names.forEach((nm, i) => {
        const v = trng.cents(800, side === 'Dr' && code === '6' ? 240000 : 1800000);
        const contra = /Accumulated|Allowance|returns|Discount/.test(nm);
        const isDr = contra ? side === 'Cr' : side === 'Dr';
        rows.push({ code: `${code}${pad(i + 1, code.length > 1 ? 3 : 4)}`, name: nm, grp, dr: isDr ? v : null, cr: isDr ? null : v });
        if (isDr) dr += v; else cr += v;
      });
    }
    // Suspense line makes the trial balance agree
    const diff = dr - cr;
    rows.push({ code: '29999', name: 'Suspense account', grp: 'Current liabilities', dr: diff < 0 ? -diff : null, cr: diff > 0 ? diff : null });
    if (diff > 0) cr += diff; else dr -= diff;
    const wb = newWorkbook();
    const ws = wb.addWorksheet('Trial Balance');
    ws.getCell('A1').value = `${OUR_COMPANY} - Trial Balance as at 30-Sep-2026 (AED)`;
    ws.getCell('A1').font = { bold: true, size: 13 };
    writeTable(ws, {
      headerRow: 3,
      autoFilter: true,
      columns: [
        { header: 'Account Code', key: 'code', width: 13 }, { header: 'Account Name', key: 'name', width: 40 }, { header: 'Account Group', key: 'grp', width: 22 },
        { header: 'Debit (AED)', key: 'dr', width: 17, type: 'amount' }, { header: 'Credit (AED)', key: 'cr', width: 17, type: 'amount' },
      ],
      rows: [...rows.map((r) => ({ ...r, dr: r.dr ? toAed(r.dr) : null, cr: r.cr ? toAed(r.cr) : null })), { name: 'Total', dr: toAed(dr), cr: toAed(cr), _style: 'total' }],
    });
    await saveWorkbook(wb, `${T}/Sheet_to_print.xlsx`);
    out.tb = { accounts: rows.length, total: dr };
  }

  // 8. Messy data for the Data Cleaner
  out.messy = await writeMessy(`${T}/Messy_Data_for_Cleaner.xlsx`, rng);
  return out;
}

async function writeMessy(file, rng) {
  const wb = newWorkbook();
  const ws = wb.addWorksheet('Expense export');
  ws.getCell('A1').value = 'EXPENSE REGISTER - EXPORTED FROM LEGACY SYSTEM';
  ws.getCell('A2').value = 'Printed: 01/10/2026 09:14   User: accounts2';
  const header = ['Category', 'Txn Date', 'Description', 'Ref', 'Amount', 'Paid By'];
  header.forEach((h, i) => (ws.getCell(4, i + 1).value = h));
  ws.getRow(4).font = { bold: true };
  [16, 14, 44, 12, 18, 14].forEach((w, i) => (ws.getColumn(i + 1).width = w));
  // Planted messy amount formats, cycled through the rows
  const fmts = [
    (c) => fmtAmt(c), // "1,234.50" as text
    (c) => `${fmtAmt(c)} DR`,
    (c) => `${fmtAmt(c)} CR`,
    (c) => `(${fmtAmt(c)})`,
    (c) => `${fmtAmt(c)}-`,
    (c) => toAed(c), // a real number
    (c) => ` ${fmtAmt(c)} `,
  ];
  const ambiguous = [d(2026, 9, 3), d(2026, 8, 7), d(2026, 9, 8), d(2026, 8, 11), d(2026, 9, 1), d(2026, 8, 4)];
  const cats = [
    ['Travel', ['Taxi fare to  DXB airport', 'Hotel - Abu Dhabi client visit', 'Toll gate top up', 'Fuel - pool car', 'Parking - Dubai Mall']],
    ['Office', ['Printer toner', 'A4 paper  (10 boxes)', 'Courier to Sharjah', 'Water dispenser refill', 'Stationery - files & pens']],
    ['Staff welfare', ['Team lunch - month end', 'Birthday cake - Sep', 'Iftar boxes', 'Tea & coffee supplies']],
    ['Repairs', ['AC servicing - showroom', 'Forklift battery repair', 'Plumbing - pantry', 'Door lock replacement', 'Racking bolt replacement', 'Electrical works - warehouse']],
  ];
  let r = 5;
  let ambi = 0, idx = 0;
  // Ambiguous dates that end up as DD/MM/YYYY text (every 4th row gets a real date cell instead).
  const ambiguousText = [];
  const stats = { dataRows: 0, blankRows: 0, subtotalRows: 0, duplicateRows: 0, mergedBlocks: 0 };
  let grand = 0;
  for (const [cat, items] of cats) {
    const start = r;
    let sub = 0;
    const blockRows = [];
    for (const it of [...items, ...items]) {
      const c = rng.cents(18, 4800);
      const isAmbiguous = rng.chance(0.3) && ambi < ambiguous.length;
      const dt = isAmbiguous ? ambiguous[ambi++] : d(2026, rng.pick([8, 9]), rng.int(13, 28));
      const fmt = fmts[idx++ % fmts.length];
      if (isAmbiguous && idx % 4 !== 0) ambiguousText.push(fmtDMY(dt));
      const signed = /CR|\(|-$/.test(String(fmt(100))) ? -c : c;
      sub += signed;
      const row = [null, idx % 4 === 0 ? dt : fmtDMY(dt), (idx % 3 === 0 ? `  ${it}  ` : it).replace('Courier', 'Courier '), `EXP-${pad(3000 + idx, 5)}`, fmt(c), rng.pick(['Petty cash', 'Company card', 'Reimbursed'])];
      blockRows.push(row);
    }
    // exact duplicate row inside two of the blocks
    if (cat === 'Office' || cat === 'Repairs') {
      blockRows.splice(2, 0, blockRows[1].slice());
      const v = blockRows[1][4];
      const c = typeof v === 'number' ? Math.round(v * 100) : Math.round(Number(String(v).replace(/[^0-9.]/g, '')) * 100);
      sub += /CR|\(|-\s*$/.test(String(v)) ? -c : c;
      stats.duplicateRows++;
    }
    for (const row of blockRows) {
      row.forEach((v, i) => {
        if (v === null || v === undefined) return;
        const cell = ws.getCell(r, i + 1);
        cell.value = v;
        if (v instanceof Date) cell.numFmt = DATE_FMT;
        if (typeof v === 'number') cell.numFmt = AMT_FMT;
      });
      r++;
      stats.dataRows++;
    }
    ws.getCell(start, 1).value = cat;
    ws.getCell(start, 1).alignment = { vertical: 'middle' };
    ws.mergeCells(start, 1, r - 1, 1);
    stats.mergedBlocks++;
    ws.getCell(r, 3).value = `Subtotal - ${cat}`;
    ws.getCell(r, 5).value = fmtAmt(sub);
    ws.getRow(r).font = { bold: true };
    r++;
    stats.subtotalRows++;
    grand += sub;
    r++; // blank row
    stats.blankRows++;
  }
  ws.getCell(r, 3).value = 'TOTAL';
  ws.getCell(r, 5).value = fmtAmt(grand);
  ws.getRow(r).font = { bold: true };
  await saveWorkbook(wb, file);
  return { ...stats, grandTotal: grand, ambiguousDates: ambiguousText };
}
