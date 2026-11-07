// Turns an uploaded CSV into supplier / item master rows, reporting every
// problem by row number so a maker can fix the file before anything is saved.

import { normalizeHeader, parseCsv } from "./csv";

export const MAX_IMPORT_ROWS = 1000;

export const SUPPLIER_TEMPLATE = [
  "supplier_code",
  "supplier_name",
  "contact_person",
  "phone",
  "email",
  "vat_pin",
  "payment_terms",
  "address",
];

export const ITEM_TEMPLATE = ["item_code", "item_description", "unit", "standard_price"];

export type ImportIssue = { line: number; message: string };

export type ImportResult<T> = {
  rows: T[];
  issues: ImportIssue[];
  ignoredColumns: string[];
};

export type SupplierImportRow = {
  supplier_code: string;
  supplier_name: string;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  vat_pin: string | null;
  payment_terms: string | null;
  address: string | null;
};

export type ItemImportRow = {
  item_code: string;
  item_description: string;
  unit: string;
  standard_price: number | null;
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function readTable(text: string, required: string[], allowed: string[]) {
  const grid = parseCsv(text);
  const issues: ImportIssue[] = [];

  if (grid.length === 0) {
    return { body: [] as string[][], index: new Map<string, number>(), issues: [{ line: 1, message: "The file is empty." }], ignored: [] as string[] };
  }

  const firstRow = grid[0];
  if (!firstRow) throw new Error("The file is empty.");
  const header = firstRow.map(normalizeHeader);
  const index = new Map<string, number>();
  header.forEach((name, position) => {
    if (name && !index.has(name)) index.set(name, position);
  });

  for (const column of required) {
    if (!index.has(column)) issues.push({ line: 1, message: `The file needs a "${column}" column.` });
  }

  const ignored = [...new Set(header.filter((name) => name && !allowed.includes(name)))];
  return { body: grid.slice(1), index, issues, ignored };
}

function cellAt(index: Map<string, number>, cells: string[], column: string): string {
  const position = index.get(column);
  if (position === undefined) return "";
  return (cells[position] ?? "").trim();
}

function tooManyRows(body: string[][], issues: ImportIssue[]): string[][] {
  if (body.length <= MAX_IMPORT_ROWS) return body;
  issues.push({
    line: 1,
    message: `The file has ${body.length} rows. Split it into parts of ${MAX_IMPORT_ROWS} or fewer.`,
  });
  return body.slice(0, MAX_IMPORT_ROWS);
}

export function parseSupplierImport(text: string, existingCodes: string[] = []): ImportResult<SupplierImportRow> {
  const { body, index, issues, ignored } = readTable(text, ["supplier_code", "supplier_name"], SUPPLIER_TEMPLATE);
  const rows: SupplierImportRow[] = [];
  const seen = new Set<string>();
  const alreadyInMaster = new Set(existingCodes.map((code) => code.trim().toLowerCase()));

  for (const [offset, cells] of tooManyRows(body, issues).entries()) {
    const line = offset + 2;
    const code = cellAt(index, cells, "supplier_code");
    const name = cellAt(index, cells, "supplier_name");

    if (!code) {
      issues.push({ line, message: "Supplier code is missing." });
      continue;
    }
    if (!name) {
      issues.push({ line, message: `${code}: supplier name is missing.` });
      continue;
    }

    const key = code.toLowerCase();
    if (seen.has(key)) {
      issues.push({ line, message: `${code} appears more than once in this file.` });
      continue;
    }
    if (alreadyInMaster.has(key)) {
      issues.push({ line, message: `${code} is already in the supplier master.` });
      continue;
    }

    const email = cellAt(index, cells, "email");
    if (email && !EMAIL_PATTERN.test(email)) {
      issues.push({ line, message: `${code}: "${email}" is not a valid email address.` });
      continue;
    }

    seen.add(key);
    rows.push({
      supplier_code: code,
      supplier_name: name,
      contact_person: cellAt(index, cells, "contact_person") || null,
      phone: cellAt(index, cells, "phone") || null,
      email: email || null,
      vat_pin: cellAt(index, cells, "vat_pin") || null,
      payment_terms: cellAt(index, cells, "payment_terms") || null,
      address: cellAt(index, cells, "address") || null,
    });
  }

  return { rows, issues, ignoredColumns: ignored };
}

export function parseItemImport(text: string, existingCodes: string[] = []): ImportResult<ItemImportRow> {
  const { body, index, issues, ignored } = readTable(
    text,
    ["item_code", "item_description", "unit"],
    ITEM_TEMPLATE,
  );
  const rows: ItemImportRow[] = [];
  const seen = new Set<string>();
  const alreadyInMaster = new Set(existingCodes.map((code) => code.trim().toLowerCase()));

  for (const [offset, cells] of tooManyRows(body, issues).entries()) {
    const line = offset + 2;
    const code = cellAt(index, cells, "item_code");
    const description = cellAt(index, cells, "item_description");
    const unit = cellAt(index, cells, "unit");

    if (!code) {
      issues.push({ line, message: "Item code is missing." });
      continue;
    }
    if (!description) {
      issues.push({ line, message: `${code}: description is missing.` });
      continue;
    }
    if (!unit) {
      issues.push({ line, message: `${code}: unit is missing (for example PCS, BOX, KG).` });
      continue;
    }

    const key = code.toLowerCase();
    if (seen.has(key)) {
      issues.push({ line, message: `${code} appears more than once in this file.` });
      continue;
    }
    if (alreadyInMaster.has(key)) {
      issues.push({ line, message: `${code} is already in the item master.` });
      continue;
    }

    const priceText = cellAt(index, cells, "standard_price");
    let standardPrice: number | null = null;
    if (priceText !== "") {
      const price = Number(priceText.replace(/,/g, ""));
      if (!Number.isFinite(price) || price < 0) {
        issues.push({ line, message: `${code}: "${priceText}" is not a valid price.` });
        continue;
      }
      standardPrice = price;
    }

    seen.add(key);
    rows.push({
      item_code: code,
      item_description: description,
      unit: unit.toUpperCase(),
      standard_price: standardPrice,
    });
  }

  return { rows, issues, ignoredColumns: ignored };
}
