import * as XLSX from 'xlsx';
import Papa from 'papaparse';
import { Invoice, BankTransaction, TDS26ASRecord, GSTRecord, Customer } from '../types';
import { isValidGSTIN, isValidPAN } from './formatters';

export interface ColumnMappingDefinition {
  field: string;
  label: string;
  required: boolean;
  synonyms: string[];
}

export const INVOICE_COLUMN_MAPPINGS: ColumnMappingDefinition[] = [
  { field: 'invoiceNumber', label: 'Invoice Number', required: true, synonyms: ['inv no', 'invoice no', 'invoice number', 'inv. no.', 'bill no', 'bill number', 'invoice_num', 'doc no', 'invoice #', 'bill #', 'inv_no', 'doc_no', 'voucher no', 'vch no', 'bill_no', 'invoice_id'] },
  { field: 'invoiceDate', label: 'Invoice Date', required: true, synonyms: ['inv date', 'invoice date', 'bill date', 'date', 'doc date', 'invoice_date', 'inv_date', 'bill_date', 'voucher date'] },
  { field: 'customerName', label: 'Customer Name', required: true, synonyms: ['party', 'party name', 'customer', 'customer name', 'client', 'client name', 'buyer', 'buyer name', 'party_name', 'customer_name', 'client_name', 'account name', 'account', 'debtor', 'debtor name', 'billed to', 'bill to', 'company name', 'company', 'm/s', 'name', 'party / customer', 'billed party', 'recipient'] },
  { field: 'customerGstin', label: 'Customer GSTIN', required: false, synonyms: ['gstin', 'gst no', 'gstin/uin', 'customer gstin', 'party gstin', 'tax id', 'gstin uin', 'buyer gstin', 'party_gstin', 'customer_gstin', 'gst', 'gst_no', 'buyer_gstin'] },
  { field: 'taxableValue', label: 'Taxable Value', required: true, synonyms: ['taxable', 'taxable value', 'taxable amount', 'basic amount', 'subtotal', 'net amount', 'taxable_val', 'taxable_amt', 'amount'] },
  { field: 'cgst', label: 'CGST', required: false, synonyms: ['cgst', 'cgst amount', 'central tax', 'cgst_amt'] },
  { field: 'sgst', label: 'SGST', required: false, synonyms: ['sgst', 'sgst amount', 'state tax', 'sgst_amt', 'utgst'] },
  { field: 'igst', label: 'IGST', required: false, synonyms: ['igst', 'igst amount', 'integrated tax', 'igst_amt'] },
  { field: 'totalInvoiceValue', label: 'Total Value', required: true, synonyms: ['total', 'total invoice value', 'gross amount', 'bill amount', 'invoice amount', 'total amount', 'grand total', 'invoice total', 'total_amt', 'total_value'] },
  { field: 'paymentTerms', label: 'Payment Terms (Days)', required: false, synonyms: ['terms', 'credit days', 'payment terms', 'due days', 'credit period'] },
  { field: 'expectedTds', label: 'Expected TDS', required: false, synonyms: ['tds', 'expected tds', 'tds amount', 'it tds', 'tds deducted'] }
];

export const BANK_COLUMN_MAPPINGS: ColumnMappingDefinition[] = [
  { field: 'transactionDate', label: 'Transaction Date', required: true, synonyms: ['txn date', 'transaction date', 'date', 'value date', 'posting date'] },
  { field: 'narration', label: 'Narration / Description', required: true, synonyms: ['narration', 'description', 'particulars', 'remarks', 'transaction details'] },
  { field: 'referenceNumber', label: 'Reference / UTR / Cheque', required: false, synonyms: ['ref no', 'reference', 'utr', 'cheque no', 'chq no', 'ref number', 'chq/ref no'] },
  { field: 'credit', label: 'Credit (Deposit)', required: false, synonyms: ['credit', 'cr', 'deposit', 'received', 'receipt'] },
  { field: 'debit', label: 'Debit (Withdrawal)', required: false, synonyms: ['debit', 'dr', 'withdrawal', 'paid', 'payment'] }
];

export interface ImportValidationResult<T> {
  totalRows: number;
  validCount: number;
  errorCount: number;
  warningCount: number;
  validItems: T[];
  errors: Array<{ row: number; field: string; message: string; rawValue: any }>;
  warnings: Array<{ row: number; field: string; message: string }>;
}

/**
 * Normalizes header string to find matching synonym
 */
function normalizeHeader(header: string): string {
  return header.toLowerCase().replace(/[^a-z0-9]/g, ' ').replace(/\s+/g, ' ').trim();
}

/**
 * Auto-detect mapping between uploaded file headers and required fields
 */
export function autoDetectMappings(
  uploadedHeaders: string[],
  mappingDefs: ColumnMappingDefinition[]
): Record<string, string> {
  const mapping: Record<string, string> = {};

  uploadedHeaders.forEach(header => {
    const norm = normalizeHeader(header);
    for (const def of mappingDefs) {
      if (def.synonyms.some(syn => norm === syn || norm.includes(syn) || syn.includes(norm))) {
        if (!Object.values(mapping).includes(def.field)) {
          mapping[header] = def.field;
          break;
        }
      }
    }
  });

  return mapping;
}

/**
 * Parse an uploaded File (Excel or CSV) into headers and rows
 */
export async function parseFile(file: File): Promise<{ headers: string[]; rows: any[] }> {
  return new Promise((resolve, reject) => {
    const isCsv = file.name.endsWith('.csv');

    if (isCsv) {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          const headers = results.meta.fields || [];
          resolve({ headers, rows: results.data });
        },
        error: (err) => reject(err)
      });
    } else {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target?.result as ArrayBuffer);
          const workbook = XLSX.read(data, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const json: any[] = XLSX.utils.sheet_to_json(worksheet, { defval: '' });
          const headers = json.length > 0 ? Object.keys(json[0]) : [];
          resolve({ headers, rows: json });
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = (err) => reject(err);
      reader.readAsArrayBuffer(file);
    }
  });
}

/**
 * Resolves the best matching customer from the customer master database using
 * GSTIN, PAN, exact name, legal name, aliases, and clean name normalization.
 */
export function findBestCustomerMatch(
  queryName: string,
  queryGstin: string,
  customers: Customer[],
  defaultCustomer?: Customer
): Customer | undefined {
  const cleanGstin = queryGstin ? queryGstin.toUpperCase().trim() : '';

  // 1. By GSTIN (exact 15 characters)
  if (cleanGstin && cleanGstin.length === 15) {
    const gstinMatch = customers.find(c => c.gstin?.toUpperCase() === cleanGstin);
    if (gstinMatch) return gstinMatch;
  }

  // 2. By PAN (characters 3-12 of GSTIN or 10-char PAN)
  const pan = cleanGstin.length >= 12 ? cleanGstin.substring(2, 12) : '';
  if (pan) {
    const panMatch = customers.find(c => c.pan?.toUpperCase() === pan || c.gstin?.substring(2, 12).toUpperCase() === pan);
    if (panMatch) return panMatch;
  }

  // If queryName is empty, return defaultCustomer
  if (!queryName.trim()) {
    return defaultCustomer;
  }

  const cleanQuery = queryName.toLowerCase().replace(/[^a-z0-9]/g, ' ').replace(/\s+/g, ' ').trim();
  const normalize = (str: string) =>
    str.toLowerCase()
      .replace(/[^a-z0-9]/g, ' ')
      .replace(/\b(pvt|ltd|private|limited|corp|corporation|inc|llp|co|enterprises|solutions)\b/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  const normalizedQuery = normalize(queryName);

  // 3. Exact Name match (case-insensitive)
  const exactMatch = customers.find(c => c.name.toLowerCase().trim() === queryName.toLowerCase().trim());
  if (exactMatch) return exactMatch;

  // 4. Exact Legal Name match
  const legalMatch = customers.find(c => c.legalName?.toLowerCase().trim() === queryName.toLowerCase().trim());
  if (legalMatch) return legalMatch;

  // 5. Alias match
  const aliasMatch = customers.find(c => c.aliases?.some(a => a.toLowerCase().trim() === queryName.toLowerCase().trim() || a.toLowerCase().replace(/[^a-z0-9]/g, ' ') === cleanQuery));
  if (aliasMatch) return aliasMatch;

  // 6. Normalized clean name match (ignoring Pvt Ltd, Private Limited, etc.)
  if (normalizedQuery.length >= 3) {
    const normMatch = customers.find(c => {
      const normName = normalize(c.name);
      const normLegal = normalize(c.legalName || '');
      return (normName && normName === normalizedQuery) || (normLegal && normLegal === normalizedQuery);
    });
    if (normMatch) return normMatch;
  }

  // 7. Word inclusion / substring match for significant terms
  if (normalizedQuery.length >= 4) {
    const inclusionMatch = customers.find(c => {
      const normName = normalize(c.name);
      return (normName && normName.includes(normalizedQuery)) || (normName && normalizedQuery.includes(normName));
    });
    if (inclusionMatch) return inclusionMatch;
  }

  return defaultCustomer;
}

/**
 * Validates and transforms raw invoice rows into Invoice entities
 */
export function validateAndTransformInvoices(
  rawRows: any[],
  columnMapping: Record<string, string>,
  existingInvoices: Invoice[],
  customers: Customer[],
  defaultCustomer?: Customer
): ImportValidationResult<Invoice> {
  const result: ImportValidationResult<Invoice> = {
    totalRows: rawRows.length,
    validCount: 0,
    errorCount: 0,
    warningCount: 0,
    validItems: [],
    errors: [],
    warnings: []
  };

  const seenInvoicesInFile = new Set<string>();

  rawRows.forEach((row, idx) => {
    const rowNum = idx + 2; // Accounting 1-based + 1 header
    const mapped: any = {};

    Object.entries(columnMapping).forEach(([sourceCol, targetField]) => {
      mapped[targetField] = row[sourceCol];
    });

    const invoiceNo = String(mapped.invoiceNumber || '').trim();
    const rawCustomerName = String(mapped.customerName || defaultCustomer?.name || '').trim();
    const rawGstin = String(mapped.customerGstin || defaultCustomer?.gstin || '').trim().toUpperCase();
    const rawDate = String(mapped.invoiceDate || '').trim();
    const taxableVal = parseFloat(String(mapped.taxableValue || '0').replace(/[^0-9.-]/g, ''));
    let totalVal = parseFloat(String(mapped.totalInvoiceValue || '0').replace(/[^0-9.-]/g, ''));

    // Validation 1: Required Invoice Number
    if (!invoiceNo) {
      result.errors.push({ row: rowNum, field: 'invoiceNumber', message: 'Invoice number is missing', rawValue: mapped.invoiceNumber });
      return;
    }

    // Validation 2: Duplicate detection within file
    if (seenInvoicesInFile.has(invoiceNo.toUpperCase())) {
      result.errors.push({ row: rowNum, field: 'invoiceNumber', message: `Duplicate invoice number "${invoiceNo}" in this file`, rawValue: invoiceNo });
      return;
    }
    seenInvoicesInFile.add(invoiceNo.toUpperCase());

    // Validation 3: Duplicate detection against existing invoices
    const duplicateExisting = existingInvoices.find(inv => inv.invoiceNumber.toUpperCase() === invoiceNo.toUpperCase());
    if (duplicateExisting) {
      result.errors.push({ row: rowNum, field: 'invoiceNumber', message: `Invoice "${invoiceNo}" already exists in the system`, rawValue: invoiceNo });
      return;
    }

    // Validation 4: Customer Name
    if (!rawCustomerName) {
      result.errors.push({ row: rowNum, field: 'customerName', message: 'Customer/Party name is required', rawValue: mapped.customerName });
      return;
    }

    // Validation 5: Invoice Date
    const parsedDate = new Date(rawDate);
    if (!rawDate || isNaN(parsedDate.getTime())) {
      result.errors.push({ row: rowNum, field: 'invoiceDate', message: 'Invalid invoice date format', rawValue: mapped.invoiceDate });
      return;
    }
    const isoDate = parsedDate.toISOString().split('T')[0];

    // Validation 6: Amounts
    if (isNaN(taxableVal) || taxableVal <= 0) {
      result.errors.push({ row: rowNum, field: 'taxableValue', message: 'Taxable value must be greater than 0', rawValue: mapped.taxableValue });
      return;
    }

    const cgst = parseFloat(String(mapped.cgst || '0').replace(/[^0-9.-]/g, '')) || 0;
    const sgst = parseFloat(String(mapped.sgst || '0').replace(/[^0-9.-]/g, '')) || 0;
    const igst = parseFloat(String(mapped.igst || '0').replace(/[^0-9.-]/g, '')) || 0;

    if (isNaN(totalVal) || totalVal <= 0) {
      totalVal = taxableVal + cgst + sgst + igst;
    }

    // Multi-factor Customer Match
    const matchedCustomer = findBestCustomerMatch(rawCustomerName, rawGstin, customers, defaultCustomer);

    const finalCustomerName = matchedCustomer ? matchedCustomer.name : rawCustomerName;
    const finalGstin = rawGstin || matchedCustomer?.gstin || '';
    const finalPan = matchedCustomer?.pan || (finalGstin.length >= 12 ? finalGstin.substring(2, 12) : '');
    const customerId = matchedCustomer ? matchedCustomer.id : `CUST-AUTO-${Date.now().toString().slice(-4)}`;

    if (finalGstin && !isValidGSTIN(finalGstin)) {
      result.warnings.push({ row: rowNum, field: 'customerGstin', message: `GSTIN "${finalGstin}" does not match standard 15-character format` });
    }

    const paymentTerms = parseInt(String(mapped.paymentTerms || matchedCustomer?.paymentTerms || '30'), 10) || 30;
    const dueDate = new Date(parsedDate.getTime() + paymentTerms * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    // TDS Expected calculation based on customer's applicable rate
    let expectedTds = parseFloat(String(mapped.expectedTds || '0').replace(/[^0-9.-]/g, '')) || 0;
    const tdsApplicable = matchedCustomer ? matchedCustomer.tdsApplicable : expectedTds > 0;
    const tdsRate = matchedCustomer?.tdsRate || (tdsApplicable ? 2 : 0);
    const tdsSection = matchedCustomer?.tdsSection || '194C';

    if (expectedTds === 0 && tdsApplicable && tdsRate) {
      expectedTds = Math.round(taxableVal * (tdsRate / 100));
    }

    const netReceivable = totalVal - expectedTds;

    const newInvoice: Invoice = {
      id: `inv-${Date.now()}-${idx}`,
      invoiceNumber: invoiceNo,
      invoiceDate: isoDate,
      customerId,
      customerName: finalCustomerName,
      customerGstin: finalGstin,
      customerPan: finalPan,
      taxableValue: taxableVal,
      cgst,
      sgst,
      igst,
      cess: 0,
      totalInvoiceValue: totalVal,
      paymentTerms,
      dueDate,
      tdsApplicable,
      tdsSection,
      tdsRate,
      expectedTds,
      netReceivable,
      amountReceived: 0,
      amountAllocated: 0,
      balance: totalVal,
      status: 'Unpaid',
      createdAt: new Date().toISOString()
    };

    result.validItems.push(newInvoice);
  });

  result.validCount = result.validItems.length;
  result.errorCount = result.errors.length;
  result.warningCount = result.warnings.length;

  return result;
}

/**
 * Export data array to CSV file download
 */
export function exportToCSV(data: any[], fileName: string) {
  const csv = Papa.unparse(data);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', `${fileName}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Export data array to Excel (.xlsx) file download
 */
export function exportToExcel(data: any[], fileName: string, sheetName = 'Sheet1') {
  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);
  XLSX.writeFile(workbook, `${fileName}.xlsx`);
}
