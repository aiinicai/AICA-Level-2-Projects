// ExcelJS helpers: consistent formatting and byte-for-byte reproducible .xlsx output.
import ExcelJS from 'exceljs';
import JSZip from 'jszip';
import { writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

export const FIXED_DATE = new Date(Date.UTC(2026, 9, 1, 9, 0, 0)); // 01-Oct-2026 09:00 UTC
export const AMT_FMT = '#,##0.00';
export const DATE_FMT = 'dd-mmm-yyyy';

export function newWorkbook() {
  const wb = new ExcelJS.Workbook();
  wb.creator = 'Reco-Do sample generator';
  wb.lastModifiedBy = 'Reco-Do sample generator';
  wb.created = FIXED_DATE;
  wb.modified = FIXED_DATE;
  return wb;
}

/**
 * Write a table to a worksheet.
 * columns: [{ header, key, width, type: 'text' | 'amount' | 'date' | 'int' }]
 * rows: array of objects (keyed by column key); a row may carry `_style: 'balance' | 'total' | 'subtotal'`.
 */
export function writeTable(ws, { columns, rows, headerRow = 1, freeze = true, autoFilter = false }) {
  columns.forEach((c, i) => {
    ws.getColumn(i + 1).width = c.width ?? 14;
  });
  const hr = ws.getRow(headerRow);
  columns.forEach((c, i) => {
    const cell = hr.getCell(i + 1);
    cell.value = c.header;
    cell.font = { bold: true };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDCE6F1' } };
    cell.border = { bottom: { style: 'thin' } };
    cell.alignment = { vertical: 'middle', horizontal: c.type === 'amount' ? 'right' : 'left' };
  });
  if (freeze) ws.views = [{ state: 'frozen', xSplit: 0, ySplit: headerRow }];
  if (autoFilter) ws.autoFilter = { from: { row: headerRow, column: 1 }, to: { row: headerRow, column: columns.length } };
  let r = headerRow + 1;
  for (const row of rows) {
    const xr = ws.getRow(r);
    columns.forEach((c, i) => {
      const v = row[c.key];
      if (v === undefined || v === null || v === '') return;
      const cell = xr.getCell(i + 1);
      cell.value = v;
      if (c.type === 'amount' && typeof v === 'number') cell.numFmt = AMT_FMT;
      if (c.type === 'date' && v instanceof Date) cell.numFmt = DATE_FMT;
      if (c.type === 'int' && typeof v === 'number') cell.numFmt = '0';
    });
    if (row._style === 'balance' || row._style === 'total') xr.font = { bold: true };
    if (row._style === 'subtotal') xr.font = { italic: true, bold: true };
    r++;
  }
  return r; // next free row
}

/** Re-pack the ExcelJS zip with fixed timestamps so the output is reproducible. */
export async function normaliseZip(buf) {
  const src = await JSZip.loadAsync(buf);
  const out = new JSZip();
  const names = Object.keys(src.files); // ExcelJS writes entries in a fixed order
  for (const name of names) {
    const f = src.files[name];
    if (f.dir) continue;
    out.file(name, await f.async('nodebuffer'), { date: FIXED_DATE, createFolders: false });
  }
  return out.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE', compressionOptions: { level: 6 }, platform: 'DOS' });
}

export async function saveWorkbook(wb, file) {
  await mkdir(dirname(file), { recursive: true });
  const buf = await wb.xlsx.writeBuffer();
  await writeFile(file, await normaliseZip(Buffer.from(buf)));
}

export async function saveBytes(file, bytes) {
  await mkdir(dirname(file), { recursive: true });
  await writeFile(file, bytes);
}
