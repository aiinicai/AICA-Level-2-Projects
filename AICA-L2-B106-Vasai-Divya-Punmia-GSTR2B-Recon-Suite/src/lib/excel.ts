import * as XLSX from 'xlsx';

export type SheetSpec = { name: string; rows: Record<string, unknown>[] };

const safeName = (s: string) => s.replace(/[\\/?*[\]:]/g, ' ').slice(0, 31) || 'Sheet';

/** Downloads a workbook; each sheet gets a frozen, filterable header row. */
export function downloadWorkbook(fileName: string, sheets: SheetSpec[]) {
  const wb = XLSX.utils.book_new();
  const used = new Set<string>();
  for (const s of sheets) {
    const rows = s.rows.length ? s.rows : [{ Note: 'No records' }];
    const ws = XLSX.utils.json_to_sheet(rows);
    const keys = Object.keys(rows[0]);
    ws['!cols'] = keys.map((k) => ({
      wch: Math.min(48, Math.max(k.length + 2, ...rows.slice(0, 200).map((r) => String(r[k] ?? '').length + 1))),
    }));
    if (ws['!ref']) ws['!autofilter'] = { ref: ws['!ref'] };
    ws['!freeze'] = { xSplit: 0, ySplit: 1 };
    let name = safeName(s.name);
    for (let i = 2; used.has(name); i++) name = safeName(`${s.name.slice(0, 27)} (${i})`);
    used.add(name);
    XLSX.utils.book_append_sheet(wb, ws, name);
  }
  XLSX.writeFile(wb, fileName.endsWith('.xlsx') ? fileName : `${fileName}.xlsx`, { compression: true });
}

export const stamp = () => {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getDate())}-${p(d.getMonth() + 1)}-${d.getFullYear()}`;
};

export function downloadSample(wb: XLSX.WorkBook, fileName: string) {
  XLSX.writeFile(wb, fileName);
}
