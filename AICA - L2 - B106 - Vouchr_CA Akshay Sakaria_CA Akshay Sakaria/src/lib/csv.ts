type Cell = string | number | undefined | null;

/** RFC-4180 style CSV; a leading BOM makes Excel open ₹ and Hindi text correctly. Formula-like cells are neutralised. */
export function toCsv(head: string[], rows: Cell[][]): string {
  const cell = (c: Cell) => {
    let v = c === undefined || c === null ? '' : String(c);
    if (/^[=+\-@]/.test(v) && Number.isNaN(Number(v))) v = `'${v}`; // CSV injection guard
    return `"${v.replace(/"/g, '""')}"`;
  };
  return '﻿' + [head, ...rows].map((r) => r.map(cell).join(',')).join('\r\n');
}

export function downloadCsv(file: string, head: string[], rows: Cell[][]) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([toCsv(head, rows)], { type: 'text/csv;charset=utf-8' }));
  a.download = file;
  a.click();
  URL.revokeObjectURL(a.href);
}
