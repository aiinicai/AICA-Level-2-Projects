import ExcelJS from "exceljs";

export const STANDARD_COLUMNS = [
  "Asset Number",
  "Description 1",
  "Description 2",
  "Asset Class Code",
  "Asset Class Description",
  "Serial Number",
  "Inventory Number",
  "Capitalized",
  "Net Book Value",
  "Gross Book Value",
] as const;

export const CUSTOM_SLOT_COUNT = 15;
export const CUSTOM_COLUMNS = Array.from(
  { length: CUSTOM_SLOT_COUNT },
  (_, i) => `Custom Field ${String(i + 1).padStart(2, "0")}`
);

export const EXPECTED_COLUMNS = [...STANDARD_COLUMNS, ...CUSTOM_COLUMNS];

export type ParsedSapRow = {
  rowNumber: number;
  assetNumber: string;
  description1: string | null;
  description2: string | null;
  assetClassCode: string | null;
  assetClassDescription: string | null;
  serialNumber: string | null;
  inventoryNumber: string | null;
  capitalized: boolean | null;
  netBookValue: number | null;
  grossBookValue: number | null;
  custom: (string | null)[]; // length 15, index 0 = slot 1
};

export type SapImportRowError = {
  rowNumber: number;
  assetNumber: string | null;
  errorType: "MISSING_ASSET_NUMBER" | "INVALID_NUMBER" | "INVALID_BOOLEAN" | "DUPLICATE_IN_FILE";
  errorDetail: string;
  rawRowJson: string;
};

export type SapImportPreview = {
  totalRows: number;
  newCount: number;
  existingCount: number;
  blankValueCounts: Record<string, number>;
  invalidRowCount: number;
  duplicateInFileCount: number;
  unexpectedColumns: string[];
  missingColumns: string[];
  validRows: ParsedSapRow[];
  errors: SapImportRowError[];
};

function blank(v: unknown): boolean {
  return v === undefined || v === null || String(v).trim() === "";
}

function normalizeHeader(h: string): string {
  return h.trim().replace(/\s+/g, " ");
}

/** Minimal RFC4180-ish CSV line splitter: handles quoted fields with embedded commas/quotes. */
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  const pushField = () => {
    row.push(field);
    field = "";
  };
  const pushRow = () => {
    pushField();
    rows.push(row);
    row = [];
  };
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ",") {
      pushField();
    } else if (c === "\r") {
      // skip, \n handles the line break
    } else if (c === "\n") {
      pushRow();
    } else {
      field += c;
    }
  }
  if (field.length > 0 || row.length > 0) pushRow();
  return rows.filter((r) => r.length > 1 || (r.length === 1 && r[0].trim() !== ""));
}

export async function parseWorkbook(
  buffer: Buffer,
  fileName: string
): Promise<{ headers: string[]; rows: Record<string, string>[] }> {
  const isCsv = fileName.toLowerCase().endsWith(".csv");

  if (isCsv) {
    const text = buffer.toString("utf-8");
    const table = parseCsv(text);
    if (table.length === 0) return { headers: [], rows: [] };
    const headers = table[0].map(normalizeHeader);
    const rows = table.slice(1).map((cells) =>
      Object.fromEntries(headers.map((h, i) => [h, (cells[i] ?? "").trim()]))
    );
    return { headers, rows };
  }

  // exceljs's Buffer type and @types/node's Buffer type disagree structurally
  // in this toolchain even though both are real Node Buffers at runtime.
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.load(buffer as never);
  const sheet = workbook.worksheets[0];
  if (!sheet) return { headers: [], rows: [] };

  const headerRow = sheet.getRow(1);
  const headers: string[] = [];
  headerRow.eachCell({ includeEmpty: false }, (cell, colNumber) => {
    headers[colNumber - 1] = normalizeHeader(String(cell.value ?? ""));
  });

  const rows: Record<string, string>[] = [];
  sheet.eachRow((row, rowNumber) => {
    if (rowNumber === 1) return;
    const obj: Record<string, string> = {};
    headers.forEach((h, i) => {
      if (!h) return;
      const cell = row.getCell(i + 1);
      const value = cell.value;
      obj[h] = value === null || value === undefined ? "" : String(
        typeof value === "object" && "result" in (value as object) ? (value as { result: unknown }).result : value
      ).trim();
    });
    if (Object.values(obj).some((v) => v !== "")) rows.push(obj);
  });

  return { headers: headers.filter(Boolean), rows };
}

export function validateColumns(headers: string[]) {
  const headerSet = new Set(headers);
  const missing = EXPECTED_COLUMNS.filter((c) => !headerSet.has(c));
  const unexpected = headers.filter((h) => !EXPECTED_COLUMNS.includes(h as (typeof EXPECTED_COLUMNS)[number]));
  return { missing, unexpected };
}

function parseBooleanish(raw: string): { value: boolean | null; error?: string } {
  if (blank(raw)) return { value: null };
  const v = raw.trim().toLowerCase();
  if (["yes", "true", "1", "y"].includes(v)) return { value: true };
  if (["no", "false", "0", "n"].includes(v)) return { value: false };
  return { value: null, error: `Unrecognized value for Capitalized: "${raw}"` };
}

function parseNumberish(raw: string): { value: number | null; error?: string } {
  if (blank(raw)) return { value: null };
  const cleaned = raw.replace(/[,₹$\s]/g, "");
  const n = Number(cleaned);
  if (!Number.isFinite(n)) return { value: null, error: `Not a valid number: "${raw}"` };
  return { value: n };
}

export function parseAndValidateRows(
  rawRows: Record<string, string>[],
  existingAssetNumbers: Set<string>
): SapImportPreview {
  const blankValueCounts: Record<string, number> = {};
  EXPECTED_COLUMNS.forEach((c) => (blankValueCounts[c] = 0));

  const errors: SapImportRowError[] = [];
  const validRows: ParsedSapRow[] = [];
  const seenInFile = new Set<string>();
  let duplicateInFileCount = 0;

  rawRows.forEach((raw, idx) => {
    const rowNumber = idx + 2; // header is row 1
    EXPECTED_COLUMNS.forEach((c) => {
      if (blank(raw[c])) blankValueCounts[c] += 1;
    });

    const assetNumber = (raw["Asset Number"] ?? "").trim();
    if (blank(assetNumber)) {
      errors.push({
        rowNumber,
        assetNumber: null,
        errorType: "MISSING_ASSET_NUMBER",
        errorDetail: "Asset Number is blank — this row cannot be matched to a record and was skipped.",
        rawRowJson: JSON.stringify(raw),
      });
      return;
    }

    if (seenInFile.has(assetNumber)) {
      duplicateInFileCount += 1;
      errors.push({
        rowNumber,
        assetNumber,
        errorType: "DUPLICATE_IN_FILE",
        errorDetail: `Asset Number ${assetNumber} appears more than once in this file — only the last occurrence is applied.`,
        rawRowJson: JSON.stringify(raw),
      });
      // Remove any previously accepted row for this asset number; the later one wins.
      const prevIdx = validRows.findIndex((r) => r.assetNumber === assetNumber);
      if (prevIdx >= 0) validRows.splice(prevIdx, 1);
    }
    seenInFile.add(assetNumber);

    const capitalized = parseBooleanish(raw["Capitalized"] ?? "");
    const netBookValue = parseNumberish(raw["Net Book Value"] ?? "");
    const grossBookValue = parseNumberish(raw["Gross Book Value"] ?? "");

    const fieldErrors = [capitalized.error, netBookValue.error, grossBookValue.error].filter(Boolean);
    if (fieldErrors.length > 0) {
      errors.push({
        rowNumber,
        assetNumber,
        errorType: capitalized.error ? "INVALID_BOOLEAN" : "INVALID_NUMBER",
        errorDetail: fieldErrors.join("; "),
        rawRowJson: JSON.stringify(raw),
      });
      return;
    }

    validRows.push({
      rowNumber,
      assetNumber,
      description1: raw["Description 1"]?.trim() || null,
      description2: raw["Description 2"]?.trim() || null,
      assetClassCode: raw["Asset Class Code"]?.trim() || null,
      assetClassDescription: raw["Asset Class Description"]?.trim() || null,
      serialNumber: raw["Serial Number"]?.trim() || null,
      inventoryNumber: raw["Inventory Number"]?.trim() || null,
      capitalized: capitalized.value,
      netBookValue: netBookValue.value,
      grossBookValue: grossBookValue.value,
      custom: CUSTOM_COLUMNS.map((c) => raw[c]?.trim() || null),
    });
  });

  const newCount = validRows.filter((r) => !existingAssetNumbers.has(r.assetNumber)).length;
  const existingCount = validRows.length - newCount;

  return {
    totalRows: rawRows.length,
    newCount,
    existingCount,
    blankValueCounts,
    invalidRowCount: errors.filter((e) => e.errorType !== "DUPLICATE_IN_FILE").length,
    duplicateInFileCount,
    unexpectedColumns: [],
    missingColumns: [],
    validRows,
    errors,
  };
}
