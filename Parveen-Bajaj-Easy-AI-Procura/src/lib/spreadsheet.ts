import { parseCsv, toCsvTemplate, normalizeHeader } from './csv';

export function deliverBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

const aliases: Record<string, string[]> = {
  item_code: ['sku', 'product_code', 'stock_code', 'item', 'name'],
  item_description: ['description', 'product_name', 'item_name', 'stock_item'],
  unit: ['uom', 'unit_of_measure', 'unit_of_measurement', 'units', 'base_unit'],
  standard_price: ['purchase_cost', 'cost', 'purchase_price', 'rate', 'unit_price'],
  supplier_code: ['vendor_code', 'account_code', 'code'],
  supplier_name: ['vendor', 'vendor_name', 'company_name', 'display_name', 'name'],
  email: ['email_address'], phone: ['phone_number', 'telephone'],
  vat_pin: ['tax_registration_number', 'tax_id', 'pin'],
};
export function suggestMapping(headers: string[], targets: string[]): string[] {
  return targets.map(target => {
    const direct = headers.find(h => normalizeHeader(h) === target);
    return direct ?? headers.find(h => aliases[target]?.includes(normalizeHeader(h))) ?? '';
  });
}
export function mappedCsv(grid: string[][], targets: string[], mapping: string[]): string {
  const headers = grid[0] ?? [];
  return toCsvTemplate(targets) + grid.slice(1).map(row =>
    toCsvTemplate(mapping.map(h => row[headers.indexOf(h)] ?? ''))
  ).join('');
}
export async function readSpreadsheet(file: File): Promise<{ name: string; grid: string[][] }[]> {
  if (/\.csv$/i.test(file.name)) return [{ name: 'CSV', grid: parseCsv(await file.text()) }];
  const { Workbook } = await import('exceljs');
  const wb = new Workbook();
  await wb.xlsx.load(await file.arrayBuffer());
  return wb.worksheets.map(sheet => {
    const grid: string[][] = [];
    sheet.eachRow(row => {
      const cells: string[] = [];
      for (let i = 1; i <= sheet.columnCount; i++) cells.push(row.getCell(i).text);
      grid.push(cells);
    });
    return { name: sheet.name, grid };
  });
}
export async function excelBlob(rows: Record<string, unknown>[], sheetName = 'GRN'): Promise<Blob> {
  const { Workbook } = await import('exceljs');
  const wb = new Workbook(); wb.creator = 'Easy AI Procura';
  const sheet = wb.addWorksheet(sheetName);
  const headers = Object.keys(rows[0] ?? {});
  sheet.columns = headers.map(key => ({ header: key, key, width: Math.min(45, Math.max(18, key.length + 3)) }));
  rows.forEach(row => sheet.addRow(row));
  sheet.views = [{ state: 'frozen', ySplit: 1 }];
  if (headers.length) sheet.autoFilter = { from: { row: 1, column: 1 }, to: { row: rows.length + 1, column: headers.length } };
  sheet.eachRow((row, index) => {
    row.font = { name: 'Arial', size: 11, bold: index === 1 };
    row.eachCell(cell => { if (typeof cell.value === 'number') cell.numFmt = '#,##0.###;(#,##0.###);"-"'; });
  });
  const bytes = await wb.xlsx.writeBuffer();
  return new Blob([new Uint8Array(bytes)], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}
