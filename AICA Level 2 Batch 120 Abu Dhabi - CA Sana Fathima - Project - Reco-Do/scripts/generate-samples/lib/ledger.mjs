// Helpers shared by the AR, AP and intercompany generators.
import { newWorkbook, writeTable, saveWorkbook } from './excel.mjs';
import { addDays, isWeekend } from './util.mjs';

/** Write a ledger/SOA with optional title rows above the header. */
export async function writeLedger(file, { sheet, titles = [], headerRow, columns, rows }) {
  const wb = newWorkbook();
  const ws = wb.addWorksheet(sheet);
  titles.forEach((t, i) => {
    if (t) ws.getCell(i + 1, 1).value = t;
  });
  if (titles.length) ws.getCell(1, 1).font = { bold: true, size: 13 };
  writeTable(ws, { headerRow: headerRow ?? titles.length + 1, columns, rows, autoFilter: true });
  await saveWorkbook(wb, file);
}

/** Move a date forward to the next business day (Mon-Fri). */
export function bizFwd(x) {
  let y = x;
  while (isWeekend(y)) y = addDays(y, 1);
  return y;
}
export function bizBack(x) {
  let y = x;
  while (isWeekend(y)) y = addDays(y, -1);
  return y;
}

/** Add running balance (in cents) to rows given a sign function. */
export function runBalance(rows, opening, delta) {
  let b = opening;
  for (const r of rows) {
    b += delta(r);
    r.balance = b;
  }
  return b;
}
