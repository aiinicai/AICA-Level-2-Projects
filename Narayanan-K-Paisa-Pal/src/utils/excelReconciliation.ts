import * as XLSX from 'xlsx';
import { AppRow, Kind, RecType, InvType, UtilityType } from '../types';
import { uid, todayIST, toDay, fmtD, inr } from './calculations';
import { findDuplicate } from './duplicateDetector';

export interface ReconciledImportRow {
  id: string;
  sourceSheet: string;
  sourceRowNumber: number;
  originalData: Record<string, any>;
  detectedKind: Kind;
  mappedDestination: 'Investments' | 'Records (Identity)' | 'Records (Insurance)' | 'Utilities' | 'Due Dates';
  categoryOrType: string;
  titleOrName: string;
  holder: string;
  identifierNumber: string; // Account #, Doc #, Policy #, Consumer # (preserves leading zeros)
  amountOrValue: number | '';
  secondaryAmount?: number | ''; // e.g. maturity value or sum insured
  dateOrDue: string; // YYYY-MM-DD
  secondaryDate?: string; // e.g. issued date or renewal date
  validationIssues: string[];
  proposedCorrections: string[];
  isDuplicate: boolean;
  duplicateReason?: string;
  outcome: 'newly_imported' | 'updated' | 'skipped' | 'rejected';
  rejectionReason?: string;
  selected: boolean;
  appRowData: Record<string, any>;
}

export interface ReconciliationReport {
  fileName: string;
  totalSourceRows: number;
  genuinelyEmptyRows: number;
  newlyImportedCount: number;
  updatedCount: number;
  skippedCount: number;
  rejectedCount: number;
  validSourceRowsCount: number;
  breakdown: {
    investments: number;
    recordsIdentity: number;
    recordsInsurance: number;
    utilities: number;
  };
  rows: ReconciledImportRow[];
}

/**
 * Coerces cell value to string while preserving leading zeros and whitespace
 */
function toText(val: any): string {
  if (val == null) return '';
  return String(val).trim();
}

/**
 * Cleans monetary numbers from formatted currency strings (e.g. "₹ 4,50,000", "Rs. 1500")
 */
function cleanMoney(val: any): number | '' {
  if (val == null || val === '') return '';
  if (typeof val === 'number') return isNaN(val) ? '' : val;
  const cleaned = String(val).replace(/[₹,Rs\s]/gi, '').trim();
  const num = parseFloat(cleaned);
  return Number.isFinite(num) ? num : '';
}

/**
 * Standardizes multiple date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, Excel serials) to ISO (YYYY-MM-DD)
 */
function parseDateToIso(v: any): string {
  if (v == null || v === '') return '';
  if (Object.prototype.toString.call(v) === '[object Date]') {
    if (isNaN(v)) return '';
    return v.toISOString().slice(0, 10);
  }
  if (typeof v === 'number' && v > 20000 && v < 80000) {
    return fmtD(Date.UTC(1899, 11, 30) + Math.round(v) * 86400000);
  }
  const s = String(v).trim();
  if (/^(permanent|no expiry|na|n\/a|lifetime|none|—|-)$/i.test(s)) {
    return '';
  }
  // YYYY-MM-DD
  let m = s.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/);
  if (m) {
    const y = +m[1];
    const mon = String(+m[2]).padStart(2, '0');
    const day = String(+m[3]).padStart(2, '0');
    return `${y}-${mon}-${day}`;
  }
  // DD/MM/YYYY or DD-MM-YYYY
  m = s.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})/);
  if (m) {
    let y = +m[3];
    if (y < 100) y += 2000;
    const day = String(+m[1]).padStart(2, '0');
    const mon = String(+m[2]).padStart(2, '0');
    return `${y}-${mon}-${day}`;
  }
  return '';
}

/**
 * Classifies an incoming row into its true business category
 */
function classifyRow(
  sheetName: string,
  row: Record<string, any>
): {
  kind: Kind;
  destination: 'Investments' | 'Records (Identity)' | 'Records (Insurance)' | 'Utilities' | 'Due Dates';
  subType: string;
} {
  const combined = `${sheetName} ${Object.keys(row).join(' ')} ${Object.values(row).join(' ')}`.toLowerCase();

  // 1. Utilities (Electricity, Water, Gas, Broadband, Telephone, Bills)
  if (
    /utility|electricity|power|water|jal board|bescom|tata power|adani electricity|bwssb|broadband|wifi|landline|lpg|gas bill|consumer no|meter no/i.test(
      combined
    )
  ) {
    let sub = 'electricity';
    if (/water|jal board|bwssb/i.test(combined)) sub = 'water';
    else if (/broadband|wifi|internet|fiber/i.test(combined)) sub = 'broadband';
    else if (/gas|lpg|cylinder|piped/i.test(combined)) sub = 'gas';
    else if (/landline|phone|telephone|mobile/i.test(combined)) sub = 'mobile';
    return { kind: 'util', destination: 'Utilities', subType: sub };
  }

  // 2. Official Identity Documents (Passport, Driving Licence, PAN, Aadhaar, Voter ID)
  if (
    /passport|republic of india|driving licen[cs]e|\bdl\b|\bpan\b|permanent account|aadhaar|aadhar|uidai|voter|ration card|official id/i.test(
      combined
    ) &&
    !/insurance|policy|sum assured|premium/i.test(combined)
  ) {
    let sub = 'id';
    if (/passport/i.test(combined)) sub = 'passport';
    else if (/licen[cs]e|\bdl\b/i.test(combined)) sub = 'licence';
    else if (/\bpan\b/i.test(combined)) sub = 'pan';
    else if (/aadhaar|aadhar/i.test(combined)) sub = 'aadhaar';
    return { kind: 'rec', destination: 'Records (Identity)', subType: sub };
  }

  // 3. Insurance Policies (Medical, Vehicle, Life, Accident, Home)
  if (
    /insurance|policy|sum assured|idv\b|premium|mediclaim|health insurance|jeevan|star health|new india assurance|icici lombard|care health/i.test(
      combined
    )
  ) {
    let sub = 'medical';
    if (/vehicle|car|motor|two.?wheeler|activa|karoq|nexon/i.test(combined)) sub = 'vehicle';
    else if (/term|life|jeevan|sanchay/i.test(combined)) sub = 'term';
    return { kind: 'rec', destination: 'Records (Insurance)', subType: sub };
  }

  // 4. Investments (Bank Fixed Deposits, RDs, Mutual Funds, Stocks, Gold, Bonds)
  if (
    /fixed deposit|term deposit|\bfd\b|\brd\b|mutual fund|sip\b|folio|bluechip|small cap|large cap|shares|equity|gold|sgb|bond|ppf|nps/i.test(
      combined
    )
  ) {
    let sub = 'fd';
    if (/mutual fund|fund house|scheme|folio|bluechip|cap\b/i.test(combined)) sub = 'mf';
    else if (/shares|stock|equity|demat/i.test(combined)) sub = 'stocks';
    else if (/gold|silver|sgb/i.test(combined)) sub = 'gold';
    else if (/bond|debenture/i.test(combined)) sub = 'bond';
    return { kind: 'inv', destination: 'Investments', subType: sub };
  }

  // 5. General Dues (EMIs, Loans)
  if (/emi\b|loan\b|installment/i.test(combined)) {
    return { kind: 'due', destination: 'Due Dates', subType: 'emi' };
  }

  // Default fallback based on fields
  return { kind: 'inv', destination: 'Investments', subType: 'other' };
}

/**
 * Master parser and reconciler for multi-sheet or single-sheet workbooks
 */
export function reconcileExcelWorkbook(
  workbook: XLSX.WorkBook,
  fileName: string,
  existingRows: AppRow[]
): ReconciliationReport {
  const resultRows: ReconciledImportRow[] = [];
  let genuinelyEmptyRows = 0;
  let totalSourceRows = 0;

  // Determine if there is a Master Sheet (e.g. "All 41 Trial Assets" or "Master Data")
  const sheetNames = workbook.SheetNames;
  const masterSheetName = sheetNames.find((s) =>
    /all.*(assets|records|documents)|master/i.test(s)
  );

  // If a dedicated master sheet exists, process it exclusively to prevent double counting across subset sheets
  const targetSheets = masterSheetName ? [masterSheetName] : sheetNames;

  for (const sheetName of targetSheets) {
    // Skip auxiliary index sheets like "10 Persons Portfolio Index" if other category sheets exist
    if (!masterSheetName && /person.*index|summary|instructions|readme/i.test(sheetName)) {
      continue;
    }

    const sheet = workbook.Sheets[sheetName];
    if (!sheet) continue;

    // Use raw: false so numbers with leading zeros (e.g. "0482019482") are preserved as formatted text
    const rows = XLSX.utils.sheet_to_json<Record<string, any>>(sheet, {
      defval: '',
      raw: false,
    });

    rows.forEach((row, rowIndex) => {
      totalSourceRows++;
      const sourceRowNumber = rowIndex + 2; // 1-based, accounting for header row

      // Check if genuinely empty row
      const nonBlankValues = Object.values(row).filter(
        (v) => v != null && String(v).trim() !== ''
      );
      if (nonBlankValues.length === 0) {
        genuinelyEmptyRows++;
        return;
      }

      // Column lookup helper
      const getVal = (...matchKeys: string[]): string => {
        for (const k of matchKeys) {
          const foundKey = Object.keys(row).find((header) => {
            const h = header.toLowerCase().replace(/[^a-z0-9]/g, '');
            const target = k.toLowerCase().replace(/[^a-z0-9]/g, '');
            return h === target || h.includes(target);
          });
          if (foundKey && row[foundKey] != null && String(row[foundKey]).trim() !== '') {
            return toText(row[foundKey]);
          }
        }
        return '';
      };

      const validationIssues: string[] = [];
      const proposedCorrections: string[] = [];

      // Extract basic fields with robust aliases
      const rawTitle = getVal('document title', 'title', 'name', 'scheme name', 'particulars', 'description');
      const rawHolder = getVal('holder name', 'holder', 'policyholder', 'depositor name', 'investor name', 'consumer name', 'person');
      const rawInstitution = getVal('institution', 'provider', 'bank name', 'service provider', 'insurance company', 'fund house', 'biller');
      const rawDocNumber = getVal('account doc number', 'account number', 'document number', 'policy number', 'folio number', 'consumer account no', 'consumer no', 'ref', 'docnumber');
      const rawAmount = getVal('amount principal', 'purchase cost', 'deposit amount', 'annual premium', 'bill amount', 'amount', 'invested');
      const rawCurrent = getVal('current maturity value', 'maturity value', 'current valuation', 'sum assured', 'current');
      const rawRate = getVal('interest rate', 'rate', 'roi');
      const rawDate = getVal('due expiry date', 'maturity date', 'expiry validity', 'renewal due date', 'payment due date', 'statement date', 'date', 'due');
      const rawNotes = getVal('notes description', 'notes', 'remark', 'dpdp act');

      // Classification
      const classification = classifyRow(sheetName, row);

      // Value extraction
      const title = rawTitle || rawInstitution || (classification.kind === 'util' ? 'Utility Bill' : 'Item');
      const holder = rawHolder || 'Family Member';
      const identifierNumber = rawDocNumber;
      const amountVal = cleanMoney(rawAmount);
      const currentVal = cleanMoney(rawCurrent);
      const isoDate = parseDateToIso(rawDate);

      // Check date parsing
      if (rawDate && !isoDate && !/permanent|no expiry|na|n\/a|lifetime/i.test(rawDate)) {
        validationIssues.push(`Unrecognized date format: "${rawDate}"`);
      } else if (rawDate && isoDate && rawDate !== isoDate) {
        proposedCorrections.push(`Converted date "${rawDate}" to standard ISO "${isoDate}"`);
      }

      // Check leading zero retention
      if (identifierNumber && identifierNumber.startsWith('0')) {
        proposedCorrections.push(`Preserved leading zero in identifier: "${identifierNumber}"`);
      }

      // Build target application row data
      let appRowData: Record<string, any> = {};

      if (classification.kind === 'util') {
        appRowData = {
          name: title,
          utilityType: classification.subType as UtilityType,
          provider: rawInstitution || title,
          accountNumber: identifierNumber,
          holder,
          billAmount: amountVal !== '' ? amountVal : 0,
          balanceOutstanding: amountVal !== '' ? amountVal : 0,
          dueDate: isoDate || todayIST(),
          due: isoDate || todayIST(),
          status: 'pending',
          freq: 'monthly',
          notes: rawNotes,
          attachmentName: getVal('document file', 'file name', 'file'),
        };
      } else if (classification.kind === 'rec') {
        const isInsurance = classification.destination === 'Records (Insurance)';
        if (isInsurance) {
          appRowData = {
            title,
            type: 'policy',
            category: 'insurance',
            insuranceType: classification.subType,
            insurer: rawInstitution || title,
            policyNumber: identifierNumber,
            policyholder: holder,
            holder,
            insuredPersons: holder,
            sumInsured: currentVal !== '' ? currentVal : '',
            premium: amountVal !== '' ? amountVal : '',
            renewalDate: isoDate,
            premiumDueDate: isoDate,
            expires: isoDate,
            notes: rawNotes,
            attachmentName: getVal('document file', 'file name', 'file'),
          };
        } else {
          appRowData = {
            title,
            type: classification.subType as RecType,
            category: 'identity',
            holder,
            number: identifierNumber,
            expires: isoDate, // Clean empty string for permanent IDs like PAN/Aadhaar
            notes: rawNotes,
            attachmentName: getVal('document file', 'file name', 'file'),
          };
        }
      } else if (classification.kind === 'inv') {
        const rateNum = parseFloat(String(rawRate).replace(/[^0-9.]/g, ''));
        appRowData = {
          name: title,
          type: classification.subType as InvType,
          institution: rawInstitution || 'Institution',
          holder,
          ref: identifierNumber,
          invested: amountVal !== '' ? amountVal : '',
          current: currentVal !== '' ? currentVal : amountVal,
          rate: Number.isFinite(rateNum) ? rateNum : '',
          maturity: isoDate,
          notes: rawNotes,
          attachmentName: getVal('document file', 'file name', 'file'),
        };
      } else {
        // Due date
        appRowData = {
          name: title,
          category: 'emi',
          provider: rawInstitution,
          holder,
          ref: identifierNumber,
          amount: amountVal,
          due: isoDate || todayIST(),
          freq: 'monthly',
          status: 'pending',
          notes: rawNotes,
        };
      }

      // Check duplicate status against existing database AND current batch
      const existingMatch = findDuplicate(existingRows, classification.kind, appRowData);
      const batchMatch = resultRows.find((r) => {
        if (r.detectedKind !== classification.kind) return false;
        if (identifierNumber && r.identifierNumber && identifierNumber === r.identifierNumber) {
          return true;
        }
        return false;
      });

      const isDuplicate = existingMatch.isDuplicate || Boolean(batchMatch);
      const duplicateReason = existingMatch.isDuplicate
        ? existingMatch.reason
        : batchMatch
        ? `Duplicate of row #${batchMatch.sourceRowNumber} in current import batch`
        : undefined;

      // Determine outcome
      let outcome: 'newly_imported' | 'updated' | 'skipped' | 'rejected' = 'newly_imported';
      let rejectionReason: string | undefined;

      if (!title && !identifierNumber && !amountVal && !isoDate) {
        outcome = 'rejected';
        rejectionReason = 'Insufficient data to identify or record financial entry.';
      } else if (isDuplicate) {
        outcome = 'skipped';
      }

      resultRows.push({
        id: uid(),
        sourceSheet: sheetName,
        sourceRowNumber,
        originalData: row,
        detectedKind: classification.kind,
        mappedDestination: classification.destination,
        categoryOrType: classification.subType,
        titleOrName: title,
        holder,
        identifierNumber,
        amountOrValue: amountVal,
        secondaryAmount: currentVal,
        dateOrDue: isoDate,
        validationIssues,
        proposedCorrections,
        isDuplicate,
        duplicateReason,
        outcome,
        rejectionReason,
        selected: outcome === 'newly_imported',
        appRowData,
      });
    });
  }

  const newlyImportedCount = resultRows.filter((r) => r.outcome === 'newly_imported').length;
  const updatedCount = resultRows.filter((r) => r.outcome === 'updated').length;
  const skippedCount = resultRows.filter((r) => r.outcome === 'skipped').length;
  const rejectedCount = resultRows.filter((r) => r.outcome === 'rejected').length;

  const breakdown = {
    investments: resultRows.filter((r) => r.mappedDestination === 'Investments').length,
    recordsIdentity: resultRows.filter(
      (r) => r.mappedDestination === 'Records (Identity)'
    ).length,
    recordsInsurance: resultRows.filter(
      (r) => r.mappedDestination === 'Records (Insurance)'
    ).length,
    utilities: resultRows.filter((r) => r.mappedDestination === 'Utilities').length,
  };

  return {
    fileName,
    totalSourceRows,
    genuinelyEmptyRows,
    validSourceRowsCount: resultRows.length,
    newlyImportedCount,
    updatedCount,
    skippedCount,
    rejectedCount,
    breakdown,
    rows: resultRows,
  };
}

/**
 * Generates a downloadable CSV reconciliation & audit report
 */
export function generateReconciliationCsv(report: ReconciliationReport): string {
  const headers = [
    'Source Sheet',
    'Row Number',
    'Detected Destination',
    'Item Name / Title',
    'Person / Holder',
    'Account / Document Number',
    'Amount (₹)',
    'Date / Due',
    'Import Outcome',
    'Reason / Notes',
  ];

  const escapeCsv = (val: any) => `"${String(val ?? '').replace(/"/g, '""')}"`;

  const lines = [
    `Paisa Pal - Import Reconciliation & Audit Report`,
    `File: ${report.fileName}`,
    `Generated At: ${todayIST()}`,
    `Total Source Rows: ${report.totalSourceRows} | Valid Rows: ${report.validSourceRowsCount} | Newly Imported: ${report.newlyImportedCount} | Skipped: ${report.skippedCount} | Rejected: ${report.rejectedCount} | Empty Rows: ${report.genuinelyEmptyRows}`,
    '',
    headers.map(escapeCsv).join(','),
  ];

  for (const r of report.rows) {
    const reason = r.duplicateReason || r.rejectionReason || r.proposedCorrections.join('; ') || 'Valid record';
    lines.push(
      [
        r.sourceSheet,
        r.sourceRowNumber,
        r.mappedDestination,
        r.titleOrName,
        r.holder,
        r.identifierNumber,
        r.amountOrValue,
        r.dateOrDue,
        r.outcome.toUpperCase(),
        reason,
      ]
        .map(escapeCsv)
        .join(',')
    );
  }

  return lines.join('\n');
}
