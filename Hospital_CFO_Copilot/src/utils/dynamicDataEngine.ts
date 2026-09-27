import * as XLSX from 'xlsx';
import {
  Billing,
  BudgetRecord,
  Claim,
  Collection,
  Encounter,
  HospitalDepartment,
  Service,
  TariffMasterItem,
} from '../types';
import {
  CanonicalDatasetType,
  ColumnMappingItem,
  ColumnProfile,
  DataQualityIssue,
  DataValidationSummary,
  DatasetMappingConfig,
  DetectedRelationship,
  InferredDataType,
  SheetProfile,
  UploadedFileProfile,
} from '../types/ingestion';

// ==========================================
// CANONICAL SCHEMA SPECIFICATIONS
// ==========================================

export interface CanonicalFieldDef {
  key: string;
  label: string;
  description: string;
  type: InferredDataType;
  required: boolean;
  isFinancialAmount?: boolean;
  isIdentifier?: boolean;
}

export const CANONICAL_SCHEMAS: Record<CanonicalDatasetType, CanonicalFieldDef[]> = {
  encounters: [
    { key: 'Encounter_ID', label: 'Encounter ID', description: 'Primary hospital stay or visit identifier (IPD/OPD/UHID)', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Admission_Date', label: 'Admission Date', description: 'Date of patient admission or presentation (YYYY-MM-DD)', type: 'date', required: true },
    { key: 'Discharge_Date', label: 'Discharge Date', description: 'Date of clinical or administrative discharge', type: 'date', required: false },
    { key: 'Department', label: 'Department', description: 'Treating clinical department (Laboratory, Pharmacy, Radiology, etc.)', type: 'string', required: true },
    { key: 'Ward', label: 'Ward / Unit', description: 'Physical ward, unit, floor, or station', type: 'string', required: false },
    { key: 'Bed_Type', label: 'Bed Category', description: 'Bed category (Standard, ICU, Deluxe, Suite, etc.)', type: 'string', required: false },
    { key: 'Payer_Type', label: 'Payer Category', description: 'Primary financial payer (Self Pay, TPA / Insurance, Corporate)', type: 'string', required: false },
    { key: 'Discharge_Status', label: 'Discharge Status', description: 'Discharged, Admitted, Pending Financial Review, or AMA', type: 'string', required: true },
  ],
  services: [
    { key: 'Service_ID', label: 'Service ID', description: 'Unique clinical order or service transaction identifier', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Encounter_ID', label: 'Encounter ID', description: 'Encounter or visit reference linking to patient stay', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Service_DateTime', label: 'Service Date/Time', description: 'Timestamp when service or drug was rendered', type: 'date', required: true },
    { key: 'Revenue_Centre', label: 'Revenue Centre', description: 'Cost/revenue centre rendering service (Laboratory, Pharmacy, OT, etc.)', type: 'string', required: true },
    { key: 'Service_Code', label: 'Service Code', description: 'Hospital charge code, CPT code, or item code', type: 'string', required: false },
    { key: 'Description', label: 'Description', description: 'Clinical investigation, procedure, or pharmaceutical name', type: 'string', required: true },
    { key: 'Quantity', label: 'Quantity', description: 'Delivered clinical quantity or medication units', type: 'number', required: true },
    { key: 'Expected_Amount', label: 'Expected Amount', description: 'Expected tariff or rate value in INR', type: 'number', required: true, isFinancialAmount: true },
  ],
  billing: [
    { key: 'Bill_ID', label: 'Bill / Invoice ID', description: 'Invoice number or charge slip identifier', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Encounter_ID', label: 'Encounter ID', description: 'Encounter or visit reference for billed patient', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Service_ID', label: 'Service ID', description: 'Linked service transaction identifier (if itemized)', type: 'identifier', required: false, isIdentifier: true },
    { key: 'Bill_DateTime', label: 'Bill Date/Time', description: 'Timestamp when invoice was generated', type: 'date', required: true },
    { key: 'Billed_Quantity', label: 'Billed Quantity', description: 'Units charged on the customer invoice', type: 'number', required: true },
    { key: 'Billed_Amount', label: 'Billed Amount', description: 'Total gross or net billed financial charge in INR', type: 'number', required: true, isFinancialAmount: true },
    { key: 'Discount', label: 'Discount Amount', description: 'Concessions, discounts, or waivers applied', type: 'number', required: false, isFinancialAmount: true },
    { key: 'Bill_Status', label: 'Bill Status', description: 'Invoice status (Provisional, Final, Cancelled)', type: 'string', required: true },
  ],
  claims: [
    { key: 'Claim_ID', label: 'Claim ID', description: 'TPA claim or pre-authorization identifier', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Encounter_ID', label: 'Encounter ID', description: 'Encounter reference for insurance submission', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Claim_Amount', label: 'Claim Amount', description: 'Total claimed amount submitted to insurer in INR', type: 'number', required: true, isFinancialAmount: true },
    { key: 'Approved_Amount', label: 'Approved Amount', description: 'Amount authorized or approved by TPA/insurer', type: 'number', required: true, isFinancialAmount: true },
    { key: 'Rejected_Amount', label: 'Rejected Amount', description: 'Disallowed or deducted claim portion', type: 'number', required: false, isFinancialAmount: true },
    { key: 'Claim_Status', label: 'Claim Status', description: 'Status (Submitted, Approved, Partially Approved, Rejected, Pending Info)', type: 'string', required: true },
    { key: 'Submission_Date', label: 'Submission Date', description: 'Date claim was dispatched to TPA', type: 'date', required: true },
    { key: 'Approval_Date', label: 'Approval Date', description: 'Date authorization letter was received', type: 'date', required: false },
  ],
  collections: [
    { key: 'Receipt_ID', label: 'Receipt ID', description: 'Payment receipt number or voucher identifier', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Encounter_ID', label: 'Encounter ID', description: 'Encounter or visit reference for cash receipt', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Receipt_Date', label: 'Receipt Date', description: 'Date collection was posted', type: 'date', required: true },
    { key: 'Amount', label: 'Receipt Amount', description: 'Monetary value received in INR', type: 'number', required: true, isFinancialAmount: true },
    { key: 'Payment_Mode', label: 'Payment Mode', description: 'Cash, Credit Card, Bank Transfer, NEFT/RTGS, Cheque, TPA Settlement', type: 'string', required: true },
  ],
  tariff_master: [
    { key: 'Service_Code', label: 'Service Code', description: 'Standard tariff procedure or test code', type: 'identifier', required: true, isIdentifier: true },
    { key: 'Service_Description', label: 'Description', description: 'Standard service catalogue description', type: 'string', required: true },
    { key: 'Revenue_Centre', label: 'Revenue Centre', description: 'Department or cost centre', type: 'string', required: true },
    { key: 'Standard_Tariff', label: 'Standard Tariff', description: 'Base standard self-pay rate in INR', type: 'number', required: true, isFinancialAmount: true },
    { key: 'Effective_From', label: 'Effective From', description: 'Rate schedule start validity date', type: 'date', required: true },
    { key: 'Effective_To', label: 'Effective To', description: 'Rate schedule expiration date', type: 'date', required: true },
    { key: 'Payer', label: 'Payer Plan', description: 'Payer scheme (Standard, CGHS, Corporate, Star Health, etc.)', type: 'string', required: true },
    { key: 'Payer_Tariff', label: 'Payer Tariff', description: 'Contracted rate for this payer plan', type: 'number', required: true, isFinancialAmount: true },
  ],
  budgets: [
    { key: 'Month', label: 'Month', description: 'Accounting period (e.g. 2026-09)', type: 'date', required: true },
    { key: 'Department', label: 'Department', description: 'Clinical or operating department', type: 'string', required: true },
    { key: 'Revenue_Budget', label: 'Revenue Budget', description: 'Target revenue for the month in INR', type: 'number', required: true, isFinancialAmount: true },
    { key: 'Expense_Budget', label: 'Expense Budget', description: 'Approved operational expense budget in INR', type: 'number', required: true, isFinancialAmount: true },
  ],
  unclassified: [],
};

// ==========================================
// SYNONYM REPOSITORY FOR DETERMINISTIC FALLBACK
// ==========================================

const SYNONYM_DICTIONARY: Record<string, string[]> = {
  Encounter_ID: [
    'encounter_id', 'encounter', 'visit_id', 'visit_no', 'visit', 'uhid', 'ipd_no', 'ip_no',
    'opd_no', 'op_no', 'admission_no', 'adm_no', 'mrn', 'patient_id', 'registration_no',
    'reg_no', 'case_no', 'indoor_no', 'inpatient_no', 'pat_id', 'encounterid', 'visitid',
  ],
  Admission_Date: [
    'admission_date', 'adm_date', 'date_of_admission', 'doa', 'in_date', 'admitted_date',
    'admit_date', 'admission_datetime', 'presentation_date', 'encounter_date',
  ],
  Discharge_Date: [
    'discharge_date', 'dc_date', 'date_of_discharge', 'dod', 'out_date', 'discharged_date',
    'discharge_datetime', 'release_date',
  ],
  Department: [
    'department', 'dept', 'speciality', 'ward_dept', 'clinical_dept', 'treating_department',
    'service_department', 'specialty', 'division',
  ],
  Ward: [
    'ward', 'ward_name', 'floor', 'station', 'nursing_station', 'unit', 'wing', 'location',
  ],
  Bed_Type: [
    'bed_type', 'bed_category', 'room_type', 'bed_class', 'accommodation_class', 'class',
    'bed_grade', 'bed_no',
  ],
  Payer_Type: [
    'payer_type', 'payer', 'payment_class', 'billing_category', 'patient_class',
    'insurance_type', 'scheme', 'tpa_type', 'settlement_category',
  ],
  Discharge_Status: [
    'discharge_status', 'patient_status', 'status', 'encounter_status', 'discharge_disposition',
    'outcome', 'discharge_type',
  ],
  Service_ID: [
    'service_id', 'service_no', 'order_id', 'test_id', 'investigation_id', 'charge_id',
    'item_id', 'line_id', 'order_no', 'requisition_no', 'serviceid',
  ],
  Service_DateTime: [
    'service_datetime', 'service_date', 'order_date', 'dos', 'date_of_service', 'performed_date',
    'dispense_date', 'test_date', 'procedure_date', 'entry_datetime', 'timestamp',
  ],
  Revenue_Centre: [
    'revenue_centre', 'rev_centre', 'revenue_center', 'cost_centre', 'cost_center',
    'performing_department', 'sub_dept', 'section', 'service_group', 'dept_code',
  ],
  Service_Code: [
    'service_code', 'code', 'cpt', 'cpt_code', 'item_code', 'tar_code', 'procedure_code',
    'investigation_code', 'drug_code',
  ],
  Description: [
    'description', 'service_name', 'item_name', 'investigation', 'procedure', 'test_name',
    'drug_name', 'particulars', 'service_description', 'item_description',
  ],
  Quantity: [
    'quantity', 'qty', 'units', 'count', 'no_of_units', 'dispensed_qty', 'ordered_qty',
    'service_qty', 'volume',
  ],
  Expected_Amount: [
    'expected_amount', 'standard_amount', 'standard_rate', 'tariff_amount', 'unit_rate',
    'rate', 'expected_value', 'scheduled_fee', 'catalog_rate',
  ],
  Bill_ID: [
    'bill_id', 'invoice_no', 'invoice_id', 'bill_no', 'bill_number', 'invoice_number',
    'cash_memo_no', 'charge_slip_no', 'voucher_no', 'billid', 'invoiceno',
  ],
  Bill_DateTime: [
    'bill_datetime', 'bill_date', 'invoice_date', 'transaction_date', 'billing_date',
    'invoiced_at', 'invoice_datetime',
  ],
  Billed_Quantity: [
    'billed_quantity', 'billed_qty', 'invoice_qty', 'invoiced_units', 'charged_qty',
    'billed_units',
  ],
  Billed_Amount: [
    'billed_amount', 'invoice_amount', 'net_amount', 'total_amount', 'billed_value',
    'gross_amount', 'charge_amount', 'net_value', 'total_billed', 'line_total',
  ],
  Discount: [
    'discount', 'concession', 'waiver', 'rebate', 'discount_amount', 'deduction_hospital',
  ],
  Bill_Status: [
    'bill_status', 'invoice_status', 'billing_status', 'bill_state', 'status_billing',
  ],
  Claim_ID: [
    'claim_id', 'preauth_id', 'ccn', 'claim_no', 'pre_auth_no', 'insurance_claim_id',
    'case_id', 'claim_ref',
  ],
  Claim_Amount: [
    'claim_amount', 'claimed_amount', 'requested_amount', 'billed_to_tpa', 'claim_val',
  ],
  Approved_Amount: [
    'approved_amount', 'sanctioned_amount', 'authorized_amount', 'settled_amount',
    'tpa_approved', 'admissible_amount',
  ],
  Rejected_Amount: [
    'rejected_amount', 'deducted_amount', 'disallowed_amount', 'shortfall_amount',
    'denial_amount',
  ],
  Claim_Status: [
    'claim_status', 'tpa_status', 'preauth_status', 'approval_status', 'insurance_status',
  ],
  Submission_Date: [
    'submission_date', 'dispatch_date', 'claimed_date', 'claim_date', 'sent_date',
  ],
  Approval_Date: [
    'approval_date', 'sanction_date', 'settlement_date', 'authorized_date',
  ],
  Receipt_ID: [
    'receipt_id', 'receipt_no', 'voucher_id', 'mr_no', 'money_receipt_no', 'payment_id',
    'transaction_id', 'collection_id',
  ],
  Receipt_Date: [
    'receipt_date', 'collection_date', 'payment_date', 'receipt_datetime', 'paid_date',
  ],
  Amount: [
    'amount', 'receipt_amount', 'collected_amount', 'paid_amount', 'deposit_amount',
    'collection_value',
  ],
  Payment_Mode: [
    'payment_mode', 'mode_of_payment', 'payment_type', 'instrument', 'tender',
    'payment_method', 'pay_mode',
  ],
  Standard_Tariff: [
    'standard_tariff', 'base_tariff', 'base_rate', 'cash_rate', 'general_tariff',
  ],
  Effective_From: [
    'effective_from', 'valid_from', 'start_date', 'from_date',
  ],
  Effective_To: [
    'effective_to', 'valid_to', 'expiry_date', 'to_date',
  ],
  Payer: [
    'payer', 'payer_plan', 'tpa_name', 'insurance_company', 'plan_name', 'scheme_name',
  ],
  Payer_Tariff: [
    'payer_tariff', 'contracted_rate', 'agreed_tariff', 'tpa_rate', 'approved_tariff',
  ],
  Revenue_Budget: [
    'revenue_budget', 'budget_revenue', 'target_revenue', 'budgeted_income',
  ],
  Expense_Budget: [
    'expense_budget', 'budget_expense', 'allocated_expense', 'budgeted_cost',
  ],
  Month: [
    'month', 'period', 'budget_month', 'fiscal_period', 'month_year',
  ],
};

// Known Standard Hospital Departments
export const STANDARD_HOSPITAL_DEPARTMENTS: HospitalDepartment[] = [
  'Laboratory',
  'Pharmacy',
  'Radiology',
  'OT/Surgery',
  'ICU',
  'Operations',
  'Stores',
  'Finance/Admin',
];

// Department Aliases Mapping
export function normalizeDepartmentName(deptRaw: string): HospitalDepartment {
  if (!deptRaw) return 'Operations';
  const clean = deptRaw.trim().toLowerCase();

  if (clean.includes('lab') || clean.includes('path') || clean.includes('biochem') || clean.includes('microbio')) {
    return 'Laboratory';
  }
  if (clean.includes('pharm') || clean.includes('drug') || clean.includes('medic') || clean.includes('dispens')) {
    return 'Pharmacy';
  }
  if (clean.includes('radio') || clean.includes('x-ray') || clean.includes('ct') || clean.includes('mri') || clean.includes('ultra') || clean.includes('imaging')) {
    return 'Radiology';
  }
  if (clean.includes('ot') || clean.includes('surg') || clean.includes('theatre') || clean.includes('operation')) {
    return 'OT/Surgery';
  }
  if (clean.includes('icu') || clean.includes('ccu') || clean.includes('nicu') || clean.includes('picu') || clean.includes('critical')) {
    return 'ICU';
  }
  if (clean.includes('store') || clean.includes('procure') || clean.includes('invent') || clean.includes('supply')) {
    return 'Stores';
  }
  if (clean.includes('fin') || clean.includes('bill') || clean.includes('admin') || clean.includes('account') || clean.includes('audit')) {
    return 'Finance/Admin';
  }

  return 'Operations';
}

// ==========================================
// ROBUST DATE & NUMBER PARSERS
// ==========================================

export function parseDateFlexible(val: unknown): string {
  if (!val) return '';

  // Handle Excel numeric dates (e.g. 45000 -> 2023)
  if (typeof val === 'number') {
    try {
      const excelEpoch = new Date(Date.UTC(1899, 11, 30));
      const jsDate = new Date(excelEpoch.getTime() + val * 86400000);
      if (!isNaN(jsDate.getTime())) {
        return jsDate.toISOString().split('T')[0];
      }
    } catch {
      // fallback
    }
  }

  const str = String(val).trim();
  if (!str) return '';

  // Already standard ISO YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
    return str.slice(0, 10);
  }

  // DD/MM/YYYY or DD-MM-YYYY
  const dmyMatch = str.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})/);
  if (dmyMatch) {
    const day = dmyMatch[1].padStart(2, '0');
    const month = dmyMatch[2].padStart(2, '0');
    const year = dmyMatch[3];
    return `${year}-${month}-${day}`;
  }

  // MM/DD/YYYY or MM-DD-YYYY
  const mdyMatch = str.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})/);
  if (mdyMatch && parseInt(mdyMatch[1], 10) > 12) {
    // Definitely DD/MM/YYYY
    const day = mdyMatch[1].padStart(2, '0');
    const month = mdyMatch[2].padStart(2, '0');
    const year = mdyMatch[3];
    return `${year}-${month}-${day}`;
  }

  // Native Date fallback
  const parsed = new Date(str);
  if (!isNaN(parsed.getTime())) {
    try {
      return parsed.toISOString().split('T')[0];
    } catch {
      return str;
    }
  }

  return str;
}

export function parseDateTimeFlexible(val: unknown): string {
  if (!val) return '';
  const str = String(val).trim();
  if (!str) return '';

  if (typeof val === 'number') {
    try {
      const excelEpoch = new Date(Date.UTC(1899, 11, 30));
      const jsDate = new Date(excelEpoch.getTime() + val * 86400000);
      if (!isNaN(jsDate.getTime())) {
        return jsDate.toISOString().replace('T', ' ').slice(0, 19);
      }
    } catch {}
  }

  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(str)) {
    return str.slice(0, 19);
  }

  const d = new Date(str);
  if (!isNaN(d.getTime())) {
    return d.toISOString().replace('T', ' ').slice(0, 19);
  }

  return parseDateFlexible(val) + ' 09:00:00';
}

export function parseNumberFlexible(val: unknown, fallback = 0): number {
  if (typeof val === 'number') return isNaN(val) ? fallback : val;
  if (!val) return fallback;

  let s = String(val).trim();
  // Handle (100) as negative
  let isNegative = false;
  if (s.startsWith('(') && s.endsWith(')')) {
    isNegative = true;
    s = s.slice(1, -1);
  }

  // Remove currency symbols (₹, $, Rs, INR, EUR, etc.), commas, spaces
  s = s.replace(/[₹$,\sRs\.INR]/gi, '');
  const num = parseFloat(s);
  if (isNaN(num)) return fallback;
  return isNegative ? -Math.abs(num) : num;
}

// ==========================================
// FILE PARSING & DATA PROFILING
// ==========================================

export async function parseUploadedFile(file: File): Promise<UploadedFileProfile> {
  const arrayBuffer = await file.arrayBuffer();
  const workbook = XLSX.read(arrayBuffer, { type: 'array', cellDates: false });

  const fileType: 'xlsx' | 'xls' | 'csv' = file.name.endsWith('.csv')
    ? 'csv'
    : file.name.endsWith('.xls')
    ? 'xls'
    : 'xlsx';

  const sheets: SheetProfile[] = [];

  for (const sheetName of workbook.SheetNames) {
    const worksheet = workbook.Sheets[sheetName];
    if (!worksheet) continue;

    const rawRows = XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, {
      defval: '',
      raw: false,
    });

    if (rawRows.length === 0) continue;

    const headers = Object.keys(rawRows[0] || {});
    const columns: ColumnProfile[] = [];

    for (const h of headers) {
      const colProfile = profileColumn(h, rawRows);
      columns.push(colProfile);
    }

    const { suggestedType, confidence, reason } = classifyDatasetType(sheetName, columns, rawRows);

    sheets.push({
      sheetName,
      rowCount: rawRows.length,
      columnCount: headers.length,
      columns,
      rawRows,
      suggestedDatasetType: suggestedType,
      confidenceScore: confidence,
      classificationReason: reason,
    });
  }

  return {
    fileId: `FILE-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    fileName: file.name,
    fileSize: file.size,
    fileType,
    sheets,
    activeSheetName: sheets[0]?.sheetName || '',
  };
}

function profileColumn(header: string, rows: Record<string, unknown>[]): ColumnProfile {
  let nullCount = 0;
  const sampleValues: string[] = [];
  const uniqueSet = new Set<string>();

  let numNumeric = 0;
  let numDate = 0;
  let numBool = 0;

  const total = rows.length;
  const sampleSize = Math.min(total, 50);

  for (let i = 0; i < sampleSize; i++) {
    const raw = rows[i]?.[header];
    const str = String(raw ?? '').trim();

    if (!str || str.toLowerCase() === 'null' || str.toLowerCase() === 'undefined' || str === '-') {
      nullCount++;
      continue;
    }

    uniqueSet.add(str);
    if (sampleValues.length < 5) {
      sampleValues.push(str);
    }

    // Check numeric
    const cleanNum = str.replace(/[₹$,\s()]/g, '');
    if (!isNaN(Number(cleanNum)) && cleanNum !== '') {
      numNumeric++;
    }

    // Check date
    if (
      /^\d{4}[/-]\d{1,2}[/-]\d{1,2}/.test(str) ||
      /^\d{1,2}[/-]\d{1,2}[/-]\d{4}/.test(str) ||
      !isNaN(Date.parse(str)) && isNaN(Number(str))
    ) {
      numDate++;
    }

    // Check boolean
    if (['true', 'false', 'yes', 'no', 'y', 'n', '1', '0'].includes(str.toLowerCase())) {
      numBool++;
    }
  }

  const validSampleCount = sampleSize - nullCount;
  const nullRate = sampleSize > 0 ? nullCount / sampleSize : 1;

  let inferredType: InferredDataType = 'string';
  if (validSampleCount > 0) {
    if (numDate / validSampleCount > 0.6) inferredType = 'date';
    else if (numNumeric / validSampleCount > 0.7) inferredType = 'number';
    else if (numBool / validSampleCount > 0.8) inferredType = 'boolean';
  }

  const hClean = header.toLowerCase().replace(/[^a-z0-9]/g, '_');

  const isLikelyIdentifier =
    hClean.includes('id') ||
    hClean.includes('no') ||
    hClean.includes('code') ||
    hClean.includes('mrn') ||
    hClean.includes('uhid') ||
    hClean.includes('ref');

  const isLikelyAmount =
    (inferredType === 'number' || hClean.includes('amount') || hClean.includes('rate') || hClean.includes('tariff') || hClean.includes('price') || hClean.includes('value') || hClean.includes('fee')) &&
    !hClean.includes('qty') &&
    !hClean.includes('quantity') &&
    !hClean.includes('count') &&
    !hClean.includes('id');

  const isLikelyQuantity =
    (inferredType === 'number' || hClean.includes('qty') || hClean.includes('quantity') || hClean.includes('unit') || hClean.includes('count')) &&
    !isLikelyAmount &&
    !isLikelyIdentifier;

  const isLikelyDate =
    inferredType === 'date' ||
    hClean.includes('date') ||
    hClean.includes('time') ||
    hClean.includes('doa') ||
    hClean.includes('dod') ||
    hClean.includes('dos');

  const isLikelyStatus =
    hClean.includes('status') ||
    hClean.includes('state') ||
    hClean.includes('type') ||
    hClean.includes('mode') ||
    hClean.includes('disposition');

  return {
    columnName: header,
    originalHeader: header,
    inferredType,
    sampleValues,
    totalValues: total,
    nullCount,
    nullRate,
    uniqueCount: uniqueSet.size,
    isLikelyIdentifier,
    isLikelyAmount,
    isLikelyQuantity,
    isLikelyDate,
    isLikelyStatus,
  };
}

// ==========================================
// DATASET CLASSIFICATION (AI / HEURISTIC)
// ==========================================

export function classifyDatasetType(
  sheetName: string,
  columns: ColumnProfile[],
  _rawRows: Record<string, unknown>[]
): { suggestedType: CanonicalDatasetType; confidence: number; reason: string } {
  const scores: Record<CanonicalDatasetType, number> = {
    encounters: 0,
    services: 0,
    billing: 0,
    claims: 0,
    collections: 0,
    tariff_master: 0,
    budgets: 0,
    unclassified: 0,
  };

  const sheetLower = sheetName.toLowerCase();
  if (sheetLower.includes('encounter') || sheetLower.includes('admission') || sheetLower.includes('visit') || sheetLower.includes('patient') || sheetLower.includes('inpatient')) {
    scores.encounters += 35;
  }
  if (sheetLower.includes('service') || sheetLower.includes('order') || sheetLower.includes('clinical') || sheetLower.includes('dispense')) {
    scores.services += 35;
  }
  if (sheetLower.includes('bill') || sheetLower.includes('invoice') || sheetLower.includes('charge')) {
    scores.billing += 35;
  }
  if (sheetLower.includes('claim') || sheetLower.includes('tpa') || sheetLower.includes('insurance') || sheetLower.includes('preauth')) {
    scores.claims += 35;
  }
  if (sheetLower.includes('collect') || sheetLower.includes('receipt') || sheetLower.includes('payment') || sheetLower.includes('settlement')) {
    scores.collections += 35;
  }
  if (sheetLower.includes('tariff') || sheetLower.includes('price') || sheetLower.includes('rate_master') || sheetLower.includes('schedule')) {
    scores.tariff_master += 35;
  }
  if (sheetLower.includes('budget') || sheetLower.includes('target') || sheetLower.includes('financial_plan')) {
    scores.budgets += 35;
  }

  // Inspect column semantics
  for (const col of columns) {
    const h = col.columnName.toLowerCase().replace(/[^a-z0-9]/g, '_');

    // Encounters
    if (h.includes('admission') || h.includes('doa') || h.includes('in_date')) scores.encounters += 25;
    if (h.includes('discharge') || h.includes('dod') || h.includes('out_date')) scores.encounters += 25;
    if (h.includes('bed') || h.includes('ward') || h.includes('room')) scores.encounters += 15;
    if (h.includes('uhid') || h.includes('mrn') || h.includes('ipd')) scores.encounters += 15;

    // Services
    if (h.includes('service_id') || h.includes('order_id') || h.includes('requisition')) scores.services += 25;
    if (h.includes('expected_amount') || h.includes('tariff_amount')) scores.services += 20;
    if (h.includes('procedure') || h.includes('investigation') || h.includes('service_code')) scores.services += 20;
    if (h.includes('revenue_centre') || h.includes('rev_centre') || h.includes('cost_centre')) scores.services += 20;

    // Billing
    if (h.includes('bill_id') || h.includes('invoice_no') || h.includes('bill_no')) scores.billing += 30;
    if (h.includes('billed_amount') || h.includes('invoice_amount') || h.includes('net_amount')) scores.billing += 25;
    if (h.includes('billed_qty') || h.includes('billed_quantity')) scores.billing += 25;
    if (h.includes('discount') || h.includes('concession')) scores.billing += 15;

    // Claims
    if (h.includes('claim_id') || h.includes('preauth_id') || h.includes('ccn')) scores.claims += 30;
    if (h.includes('approved_amount') || h.includes('sanctioned_amount')) scores.claims += 25;
    if (h.includes('rejected_amount') || h.includes('disallowed')) scores.claims += 20;
    if (h.includes('tpa') || h.includes('insurance_company')) scores.claims += 15;

    // Collections
    if (h.includes('receipt_id') || h.includes('receipt_no') || h.includes('voucher_no')) scores.collections += 30;
    if (h.includes('payment_mode') || h.includes('mode_of_payment') || h.includes('tender')) scores.collections += 25;
    if (h.includes('receipt_date') || h.includes('collection_date')) scores.collections += 20;

    // Tariff Master
    if (h.includes('standard_tariff') || h.includes('base_tariff')) scores.tariff_master += 30;
    if (h.includes('payer_tariff') || h.includes('contracted_rate')) scores.tariff_master += 25;
    if (h.includes('effective_from') || h.includes('valid_from')) scores.tariff_master += 20;

    // Budgets
    if (h.includes('revenue_budget') || h.includes('budget_revenue')) scores.budgets += 35;
    if (h.includes('expense_budget') || h.includes('budget_expense')) scores.budgets += 35;
    if (h.includes('fiscal_period') || (h === 'month' && col.inferredType === 'string')) scores.budgets += 20;
  }

  let topType: CanonicalDatasetType = 'unclassified';
  let maxScore = 0;

  for (const [type, score] of Object.entries(scores)) {
    if (type !== 'unclassified' && score > maxScore) {
      maxScore = score;
      topType = type as CanonicalDatasetType;
    }
  }

  const confidence = Math.min(99, Math.max(20, Math.round((maxScore / 90) * 100)));

  let reason = `Classified as ${topType.toUpperCase()} based on header signatures and data types.`;
  if (topType === 'encounters') {
    reason = 'Identified hospital stay lifecycle indicators: admission/discharge timestamps, patient/visit references, and bed assignments.';
  } else if (topType === 'services') {
    reason = 'Identified clinical service log indicators: order IDs, procedure descriptions, delivering revenue centres, and tariff rates.';
  } else if (topType === 'billing') {
    reason = 'Identified financial invoice signatures: invoice numbers, billed quantities, net charged amounts, and discount structures.';
  } else if (topType === 'claims') {
    reason = 'Identified insurance reimbursement fields: claim/pre-auth numbers, submitted claim amounts, and TPA approval status.';
  } else if (topType === 'collections') {
    reason = 'Identified cash receipt ledger: receipt vouchers, collection timestamps, and payment mode indicators.';
  } else if (topType === 'tariff_master') {
    reason = 'Identified rate master schedule: standard tariffs, contracted payer rates, and validity windows.';
  } else if (topType === 'budgets') {
    reason = 'Identified financial budget targets: monthly accounting periods, departmental cost allocations, and revenue targets.';
  } else {
    reason = 'Dataset columns could not be automatically mapped to a canonical schema. Please select the target business domain.';
  }

  return {
    suggestedType: maxScore >= 25 ? topType : 'unclassified',
    confidence: maxScore >= 25 ? confidence : 25,
    reason,
  };
}

// ==========================================
// COLUMN MAPPING GENERATOR (DETERMINISTIC HEURISTIC)
// ==========================================

export function generateDeterministicMapping(
  datasetType: CanonicalDatasetType,
  columns: ColumnProfile[]
): ColumnMappingItem[] {
  const schema = CANONICAL_SCHEMAS[datasetType] || [];
  const mappings: ColumnMappingItem[] = [];

  const matchedCanonicalKeys = new Set<string>();

  for (const col of columns) {
    const rawHeader = col.columnName;
    const cleanHeader = rawHeader.toLowerCase().trim().replace(/[^a-z0-9]/g, '_');

    let matchedCanonicalField = 'unmapped';
    let confidence: 'HIGH' | 'MEDIUM' | 'LOW' = 'LOW';
    let reason = 'No strong semantic match detected.';
    let isAmbiguous = false;
    const alternativeCandidates: string[] = [];

    // 1. Direct exact or synonym dictionary lookup
    for (const field of schema) {
      const fieldKey = field.key;
      const synonyms = SYNONYM_DICTIONARY[fieldKey] || [fieldKey.toLowerCase()];

      if (synonyms.includes(cleanHeader)) {
        matchedCanonicalField = fieldKey;
        confidence = 'HIGH';
        reason = `Direct semantic match: "${rawHeader}" corresponds to canonical ${fieldKey}.`;
        break;
      }

      // Partial / substring matches
      const hasSubstring = synonyms.some(
        (s) => (cleanHeader.includes(s) || s.includes(cleanHeader)) && cleanHeader.length >= 3 && s.length >= 3
      );

      if (hasSubstring) {
        alternativeCandidates.push(fieldKey);
      }
    }

    // 2. Fallback to candidate evaluation
    if (matchedCanonicalField === 'unmapped' && alternativeCandidates.length > 0) {
      matchedCanonicalField = alternativeCandidates[0];
      confidence = 'MEDIUM';
      reason = `Inferred semantic association: "${rawHeader}" resembles ${matchedCanonicalField}. Please verify.`;
      if (alternativeCandidates.length > 1) {
        isAmbiguous = true;
      }
    }

    if (matchedCanonicalField !== 'unmapped') {
      matchedCanonicalKeys.add(matchedCanonicalField);
    }

    mappings.push({
      sourceColumn: rawHeader,
      canonicalField: matchedCanonicalField,
      confidence,
      status: confidence === 'HIGH' ? 'ACCEPTED' : 'PENDING_REVIEW',
      reason,
      isAmbiguous,
      alternativeCandidates: alternativeCandidates.filter((c) => c !== matchedCanonicalField),
      required: schema.find((s) => s.key === matchedCanonicalField)?.required,
    });
  }

  return mappings;
}

// ==========================================
// DATA QUALITY VALIDATION ENGINE
// ==========================================

export function validateDatasetQuality(
  fileId: string,
  fileName: string,
  datasetType: CanonicalDatasetType,
  rawRows: Record<string, unknown>[],
  mappings: ColumnMappingItem[]
): DataValidationSummary {
  const issues: DataQualityIssue[] = [];
  const invalidRowIndices = new Set<number>();

  const activeMappingMap = new Map<string, string>(); // canonicalKey -> sourceHeader
  const reverseMap = new Map<string, string>(); // sourceHeader -> canonicalKey

  for (const m of mappings) {
    if (m.canonicalField && m.canonicalField !== 'unmapped' && m.canonicalField !== 'ignore') {
      activeMappingMap.set(m.canonicalField, m.sourceColumn);
      reverseMap.set(m.sourceColumn, m.canonicalField);
    }
  }

  const schema = CANONICAL_SCHEMAS[datasetType] || [];
  let mappingIssuesCount = 0;

  // Check required canonical fields mapped
  for (const field of schema) {
    if (field.required && !activeMappingMap.has(field.key)) {
      mappingIssuesCount++;
      issues.push({
        id: `MAP-${field.key}`,
        rowNumber: 0,
        column: field.key,
        issueType: 'MISSING_REQUIRED',
        severity: 'ERROR',
        message: `Mandatory canonical field "${field.label}" (${field.key}) is not mapped.`,
      });
    }
  }

  // Row-level validation
  const seenIds = new Set<string>();

  rawRows.forEach((row, idx) => {
    const rowNum = idx + 1;
    let hasRowError = false;

    // Helper to get mapped value
    const getVal = (canonicalKey: string): unknown => {
      const src = activeMappingMap.get(canonicalKey);
      return src ? row[src] : undefined;
    };

    // 1. Encounter / Entity Identifier Check
    const idKey = schema.find((s) => s.isIdentifier && s.required)?.key;
    if (idKey) {
      const idVal = String(getVal(idKey) ?? '').trim();
      if (!idVal) {
        hasRowError = true;
        issues.push({
          id: `ROW-${rowNum}-NO-ID`,
          rowNumber: rowNum,
          column: idKey,
          issueType: 'MISSING_REQUIRED',
          severity: 'ERROR',
          message: `Row ${rowNum}: Primary identifier (${idKey}) is blank or missing.`,
        });
      } else {
        if (seenIds.has(idVal)) {
          issues.push({
            id: `ROW-${rowNum}-DUP-ID`,
            rowNumber: rowNum,
            column: idKey,
            issueType: 'DUPLICATE_ID',
            severity: 'WARNING',
            message: `Row ${rowNum}: Duplicate primary identifier "${idVal}".`,
            rawValue: idVal,
          });
        } else {
          seenIds.add(idVal);
        }
      }
    }

    // 2. Financial Amount Validations
    schema.filter((s) => s.isFinancialAmount).forEach((field) => {
      const val = getVal(field.key);
      if (val !== undefined && val !== null && String(val).trim() !== '') {
        const num = parseNumberFlexible(val, NaN);
        if (isNaN(num)) {
          hasRowError = true;
          issues.push({
            id: `ROW-${rowNum}-${field.key}-NAN`,
            rowNumber: rowNum,
            column: field.key,
            issueType: 'INVALID_NUMERIC',
            severity: 'ERROR',
            message: `Row ${rowNum}: "${field.label}" contains unparseable numeric value: "${val}".`,
            rawValue: val,
          });
        } else if (num < 0 && field.key !== 'Discount') {
          issues.push({
            id: `ROW-${rowNum}-${field.key}-NEG`,
            rowNumber: rowNum,
            column: field.key,
            issueType: 'SUSPICIOUS_AMOUNT',
            severity: 'WARNING',
            message: `Row ${rowNum}: Negative financial value in "${field.label}" (₹${num.toLocaleString('en-IN')}).`,
            rawValue: num,
          });
        }
      } else if (field.required) {
        hasRowError = true;
        issues.push({
          id: `ROW-${rowNum}-${field.key}-BLANK`,
          rowNumber: rowNum,
          column: field.key,
          issueType: 'MISSING_REQUIRED',
          severity: 'ERROR',
          message: `Row ${rowNum}: Required financial amount "${field.label}" is missing.`,
        });
      }
    });

    // 3. Quantity Validations
    if (activeMappingMap.has('Quantity') || activeMappingMap.has('Billed_Quantity')) {
      const qKey = activeMappingMap.has('Quantity') ? 'Quantity' : 'Billed_Quantity';
      const qVal = getVal(qKey);
      if (qVal !== undefined && qVal !== null && String(qVal).trim() !== '') {
        const qNum = parseNumberFlexible(qVal, NaN);
        if (isNaN(qNum) || qNum <= 0) {
          issues.push({
            id: `ROW-${rowNum}-QTY`,
            rowNumber: rowNum,
            column: qKey,
            issueType: 'NEGATIVE_QTY',
            severity: 'WARNING',
            message: `Row ${rowNum}: Quantity is zero or negative (${qVal}).`,
            rawValue: qVal,
          });
        }
      }
    }

    // 4. Date Validations
    schema.filter((s) => s.type === 'date').forEach((field) => {
      const dateVal = getVal(field.key);
      if (dateVal) {
        const parsed = parseDateFlexible(dateVal);
        if (!parsed || !/^\d{4}-\d{2}-\d{2}/.test(parsed)) {
          hasRowError = true;
          issues.push({
            id: `ROW-${rowNum}-${field.key}-DATE`,
            rowNumber: rowNum,
            column: field.key,
            issueType: 'INVALID_DATE',
            severity: 'ERROR',
            message: `Row ${rowNum}: Invalid date format in "${field.label}": "${dateVal}".`,
            rawValue: dateVal,
          });
        }
      }
    });

    // 5. Specific Encounter Date Chronology
    if (datasetType === 'encounters') {
      const admStr = parseDateFlexible(getVal('Admission_Date'));
      const disStr = parseDateFlexible(getVal('Discharge_Date'));
      if (admStr && disStr && disStr < admStr) {
        issues.push({
          id: `ROW-${rowNum}-CHRONO`,
          rowNumber: rowNum,
          column: 'Discharge_Date',
          issueType: 'INVALID_DATE',
          severity: 'ERROR',
          message: `Row ${rowNum}: Discharge Date (${disStr}) is before Admission Date (${admStr}).`,
        });
        hasRowError = true;
      }
    }

    if (hasRowError) {
      invalidRowIndices.add(idx);
    }
  });

  const totalDetected = rawRows.length;
  const invalidRowsCount = invalidRowIndices.size;
  const readyForImport = Math.max(0, totalDetected - invalidRowsCount);

  return {
    fileId,
    fileName,
    datasetType,
    recordsDetected: totalDetected,
    recordsReadyForImport: readyForImport,
    recordsRequiringReview: invalidRowsCount,
    mappingIssuesCount,
    dataQualityIssuesCount: issues.length,
    issues,
    invalidRowIndices: Array.from(invalidRowIndices),
  };
}

// ==========================================
// RELATIONSHIP DETECTION ACROSS MULTI-FILE INGESTION
// ==========================================

export function detectCrossFileRelationships(
  configs: Array<{
    fileName: string;
    datasetType: CanonicalDatasetType;
    rows: Record<string, unknown>[];
    mappings: ColumnMappingItem[];
  }>
): DetectedRelationship[] {
  const relationships: DetectedRelationship[] = [];

  // Index identifiers per dataset
  const datasetIds: Record<string, { encounters: Set<string>; bills: Set<string>; services: Set<string> }> = {};

  configs.forEach((cfg) => {
    const encKey = cfg.mappings.find((m) => m.canonicalField === 'Encounter_ID')?.sourceColumn;
    const billKey = cfg.mappings.find((m) => m.canonicalField === 'Bill_ID')?.sourceColumn;
    const svcKey = cfg.mappings.find((m) => m.canonicalField === 'Service_ID')?.sourceColumn;

    const encSet = new Set<string>();
    const billSet = new Set<string>();
    const svcSet = new Set<string>();

    cfg.rows.forEach((r) => {
      if (encKey && r[encKey]) encSet.add(String(r[encKey]).trim());
      if (billKey && r[billKey]) billSet.add(String(r[billKey]).trim());
      if (svcKey && r[svcKey]) svcSet.add(String(r[svcKey]).trim());
    });

    datasetIds[cfg.datasetType] = {
      encounters: encSet,
      bills: billSet,
      services: svcSet,
    };
  });

  // Evaluate common joins
  const encountersMaster = datasetIds['encounters']?.encounters;

  // Billing -> Encounters
  if (datasetIds['billing'] && encountersMaster && encountersMaster.size > 0) {
    const billingEncs = datasetIds['billing'].encounters;
    let match = 0;
    billingEncs.forEach((id) => {
      if (encountersMaster.has(id)) match++;
    });
    const rate = billingEncs.size > 0 ? Math.round((match / billingEncs.size) * 100) : 0;
    relationships.push({
      id: 'REL-BILL-ENC',
      sourceDataset: 'Billing',
      sourceField: 'Encounter_ID',
      targetDataset: 'Encounters',
      targetField: 'Encounter_ID',
      matchRate: rate,
      matchedCount: match,
      totalSourceCount: billingEncs.size,
      confidence: rate > 80 ? 'HIGH' : rate > 50 ? 'MEDIUM' : 'LOW',
      description: `${rate}% of Billing invoice records correlate to verified patient Encounters.`,
      isValid: rate >= 70,
    });
  }

  // Services -> Encounters
  if (datasetIds['services'] && encountersMaster && encountersMaster.size > 0) {
    const serviceEncs = datasetIds['services'].encounters;
    let match = 0;
    serviceEncs.forEach((id) => {
      if (encountersMaster.has(id)) match++;
    });
    const rate = serviceEncs.size > 0 ? Math.round((match / serviceEncs.size) * 100) : 0;
    relationships.push({
      id: 'REL-SVC-ENC',
      sourceDataset: 'Services',
      sourceField: 'Encounter_ID',
      targetDataset: 'Encounters',
      targetField: 'Encounter_ID',
      matchRate: rate,
      matchedCount: match,
      totalSourceCount: serviceEncs.size,
      confidence: rate > 80 ? 'HIGH' : rate > 50 ? 'MEDIUM' : 'LOW',
      description: `${rate}% of Clinical Services line items link to verified inpatient/outpatient Encounters.`,
      isValid: rate >= 70,
    });
  }

  // Claims -> Encounters
  if (datasetIds['claims'] && encountersMaster && encountersMaster.size > 0) {
    const claimEncs = datasetIds['claims'].encounters;
    let match = 0;
    claimEncs.forEach((id) => {
      if (encountersMaster.has(id)) match++;
    });
    const rate = claimEncs.size > 0 ? Math.round((match / claimEncs.size) * 100) : 0;
    relationships.push({
      id: 'REL-CLM-ENC',
      sourceDataset: 'Claims',
      sourceField: 'Encounter_ID',
      targetDataset: 'Encounters',
      targetField: 'Encounter_ID',
      matchRate: rate,
      matchedCount: match,
      totalSourceCount: claimEncs.size,
      confidence: rate > 80 ? 'HIGH' : rate > 50 ? 'MEDIUM' : 'LOW',
      description: `${rate}% of TPA Insurance Claims correlate to hospital Encounters.`,
      isValid: rate >= 70,
    });
  }

  // Collections -> Encounters
  if (datasetIds['collections'] && encountersMaster && encountersMaster.size > 0) {
    const collEncs = datasetIds['collections'].encounters;
    let match = 0;
    collEncs.forEach((id) => {
      if (encountersMaster.has(id)) match++;
    });
    const rate = collEncs.size > 0 ? Math.round((match / collEncs.size) * 100) : 0;
    relationships.push({
      id: 'REL-COL-ENC',
      sourceDataset: 'Collections',
      sourceField: 'Encounter_ID',
      targetDataset: 'Encounters',
      targetField: 'Encounter_ID',
      matchRate: rate,
      matchedCount: match,
      totalSourceCount: collEncs.size,
      confidence: rate > 80 ? 'HIGH' : rate > 50 ? 'MEDIUM' : 'LOW',
      description: `${rate}% of Cash/Bank Collection Receipts match registered Encounters.`,
      isValid: rate >= 70,
    });
  }

  return relationships;
}

// ==========================================
// CANONICAL TRANSFORMATION EXECUTOR
// ==========================================

export function transformToCanonicalRecords(
  datasetType: CanonicalDatasetType,
  rawRows: Record<string, unknown>[],
  mappings: ColumnMappingItem[],
  invalidRowIndices: number[] = [],
  fileMetadata?: { fileName: string; sheetName?: string }
): unknown[] {
  const map = new Map<string, string>();
  mappings.forEach((m) => {
    if (m.canonicalField && m.canonicalField !== 'unmapped' && m.canonicalField !== 'ignore') {
      map.set(m.canonicalField, m.sourceColumn);
    }
  });

  const getStr = (row: Record<string, unknown>, key: string, fallback = ''): string => {
    const src = map.get(key);
    if (!src) return fallback;
    const v = row[src];
    return v !== undefined && v !== null ? String(v).trim() : fallback;
  };

  const getNum = (row: Record<string, unknown>, key: string, fallback = 0): number => {
    const src = map.get(key);
    if (!src) return fallback;
    return parseNumberFlexible(row[src], fallback);
  };

  const getDate = (row: Record<string, unknown>, key: string, fallback = ''): string => {
    const src = map.get(key);
    if (!src) return fallback;
    return parseDateFlexible(row[src]) || fallback;
  };

  const getDateTime = (row: Record<string, unknown>, key: string, fallback = ''): string => {
    const src = map.get(key);
    if (!src) return fallback;
    return parseDateTimeFlexible(row[src]) || fallback;
  };

  const output: unknown[] = [];
  const skipSet = new Set(invalidRowIndices);

  rawRows.forEach((row, idx) => {
    if (skipSet.has(idx)) return;

    if (datasetType === 'encounters') {
      const rec: Encounter = {
        Encounter_ID: getStr(row, 'Encounter_ID', `ENC-GEN-${idx + 1}`),
        Admission_Date: getDate(row, 'Admission_Date', '2026-09-01'),
        Discharge_Date: getDate(row, 'Discharge_Date') || null,
        Department: normalizeDepartmentName(getStr(row, 'Department', 'Operations')),
        Ward: getStr(row, 'Ward', 'General Ward'),
        Bed_Type: getStr(row, 'Bed_Type', 'Standard'),
        Payer_Type: getStr(row, 'Payer_Type', 'Self Pay'),
        Discharge_Status: (getStr(row, 'Discharge_Status', 'Discharged') as Encounter['Discharge_Status']),
      };
      output.push(rec);
    } else if (datasetType === 'services') {
      const rec: Service = {
        Service_ID: getStr(row, 'Service_ID', `SVC-GEN-${idx + 1}`),
        Encounter_ID: getStr(row, 'Encounter_ID', 'N/A'),
        Service_DateTime: getDateTime(row, 'Service_DateTime', '2026-09-23 10:00:00'),
        Revenue_Centre: getStr(row, 'Revenue_Centre', 'Laboratory'),
        Service_Code: getStr(row, 'Service_Code', 'GEN-01'),
        Description: getStr(row, 'Description', 'Clinical Service'),
        Quantity: Math.max(1, getNum(row, 'Quantity', 1)),
        Expected_Amount: getNum(row, 'Expected_Amount', 0),
      };
      output.push(rec);
    } else if (datasetType === 'billing') {
      const rec: Billing = {
        Bill_ID: getStr(row, 'Bill_ID', `BILL-GEN-${idx + 1}`),
        Encounter_ID: getStr(row, 'Encounter_ID', 'N/A'),
        Service_ID: getStr(row, 'Service_ID', ''),
        Bill_DateTime: getDateTime(row, 'Bill_DateTime', '2026-09-23 12:00:00'),
        Billed_Quantity: Math.max(1, getNum(row, 'Billed_Quantity', 1)),
        Billed_Amount: getNum(row, 'Billed_Amount', 0),
        Discount: getNum(row, 'Discount', 0),
        Bill_Status: (getStr(row, 'Bill_Status', 'Final') as Billing['Bill_Status']),
      };
      output.push(rec);
    } else if (datasetType === 'claims') {
      const claimAmt = getNum(row, 'Claim_Amount', 0);
      const appAmt = getNum(row, 'Approved_Amount', claimAmt);
      const rejAmt = getNum(row, 'Rejected_Amount', Math.max(0, claimAmt - appAmt));

      const rec: Claim = {
        Claim_ID: getStr(row, 'Claim_ID', `CLM-GEN-${idx + 1}`),
        Encounter_ID: getStr(row, 'Encounter_ID', 'N/A'),
        Claim_Amount: claimAmt,
        Approved_Amount: appAmt,
        Rejected_Amount: rejAmt,
        Claim_Status: (getStr(row, 'Claim_Status', 'Approved') as Claim['Claim_Status']),
        Submission_Date: getDate(row, 'Submission_Date', '2026-09-20'),
        Approval_Date: getDate(row, 'Approval_Date') || null,
      };
      output.push(rec);
    } else if (datasetType === 'collections') {
      const rec: Collection = {
        Receipt_ID: getStr(row, 'Receipt_ID', `REC-GEN-${idx + 1}`),
        Encounter_ID: getStr(row, 'Encounter_ID', 'N/A'),
        Receipt_Date: getDate(row, 'Receipt_Date', '2026-09-23'),
        Amount: getNum(row, 'Amount', 0),
        Payment_Mode: (getStr(row, 'Payment_Mode', 'Cash') as Collection['Payment_Mode']),
      };
      output.push(rec);
    } else if (datasetType === 'tariff_master') {
      const rec: TariffMasterItem = {
        Service_Code: getStr(row, 'Service_Code', `TAR-${idx + 1}`),
        Service_Description: getStr(row, 'Service_Description', 'Standard Item'),
        Revenue_Centre: getStr(row, 'Revenue_Centre', 'Laboratory'),
        Standard_Tariff: getNum(row, 'Standard_Tariff', 0),
        Effective_From: getDate(row, 'Effective_From', '2026-01-01'),
        Effective_To: getDate(row, 'Effective_To', '2026-12-31'),
        Payer: getStr(row, 'Payer', 'Standard'),
        Payer_Tariff: getNum(row, 'Payer_Tariff', getNum(row, 'Standard_Tariff', 0)),
      };
      output.push(rec);
    } else if (datasetType === 'budgets') {
      const rec: BudgetRecord = {
        Month: getStr(row, 'Month', '2026-09'),
        Department: normalizeDepartmentName(getStr(row, 'Department', 'Operations')),
        Revenue_Budget: getNum(row, 'Revenue_Budget', 0),
        Expense_Budget: getNum(row, 'Expense_Budget', 0),
      };
      output.push(rec);
    }
  });

  return output;
}
