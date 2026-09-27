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

export interface ValidationResult<T> {
  datasetName: 'encounters' | 'services' | 'billing' | 'claims' | 'collections' | 'tariff_master' | 'budget';
  valid: boolean;
  records: T[];
  recordCount: number;
  missingColumns: string[];
  errors: string[];
  warnings: string[];
}

export const REQUIRED_COLUMNS = {
  encounters: [
    'Encounter_ID',
    'Admission_Date',
    'Discharge_Date',
    'Department',
    'Ward',
    'Bed_Type',
    'Payer_Type',
    'Discharge_Status',
  ],
  services: [
    'Service_ID',
    'Encounter_ID',
    'Service_DateTime',
    'Revenue_Centre',
    'Service_Code',
    'Description',
    'Quantity',
    'Expected_Amount',
  ],
  billing: [
    'Bill_ID',
    'Encounter_ID',
    'Service_ID',
    'Bill_DateTime',
    'Billed_Quantity',
    'Billed_Amount',
    'Discount',
    'Bill_Status',
  ],
  claims: [
    'Claim_ID',
    'Encounter_ID',
    'Claim_Amount',
    'Approved_Amount',
    'Rejected_Amount',
    'Claim_Status',
    'Submission_Date',
    'Approval_Date',
  ],
  collections: [
    'Receipt_ID',
    'Encounter_ID',
    'Receipt_Date',
    'Amount',
    'Payment_Mode',
  ],
  tariff_master: [
    'Service_Code',
    'Service_Description',
    'Revenue_Centre',
    'Standard_Tariff',
    'Effective_From',
    'Effective_To',
    'Payer',
    'Payer_Tariff',
  ],
  budget: [
    'Month',
    'Department',
    'Revenue_Budget',
    'Expense_Budget',
  ],
};

function normalizeHeader(h: string): string {
  return h.trim().replace(/\s+/g, '_');
}

export async function parseFileAndValidate<T>(
  file: File,
  datasetType: 'encounters' | 'services' | 'billing' | 'claims' | 'collections'
): Promise<ValidationResult<T>> {
  const errors: string[] = [];
  const warnings: string[] = [];
  const required = REQUIRED_COLUMNS[datasetType];

  try {
    const arrayBuffer = await file.arrayBuffer();
    const workbook = XLSX.read(arrayBuffer, { type: 'array' });
    const firstSheetName = workbook.SheetNames[0];
    if (!firstSheetName) {
      return {
        datasetName: datasetType,
        valid: false,
        records: [],
        recordCount: 0,
        missingColumns: required,
        errors: ['Uploaded file does not contain any sheets or data.'],
        warnings: [],
      };
    }

    const sheet = workbook.Sheets[firstSheetName];
    const rawRows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, {
      defval: '',
      raw: false,
    });

    if (rawRows.length === 0) {
      return {
        datasetName: datasetType,
        valid: false,
        records: [],
        recordCount: 0,
        missingColumns: required,
        errors: ['The selected sheet is empty.'],
        warnings: [],
      };
    }

    // Identify headers from first row
    const firstRow = rawRows[0];
    const originalKeys = Object.keys(firstRow);
    const keyMap = new Map<string, string>(); // lowercased / normalized -> originalKey

    originalKeys.forEach((key) => {
      const norm = normalizeHeader(key).toLowerCase();
      keyMap.set(norm, key);
    });

    const missingColumns: string[] = [];
    required.forEach((reqCol) => {
      const normReq = reqCol.toLowerCase();
      if (!keyMap.has(normReq)) {
        missingColumns.push(reqCol);
      }
    });

    if (missingColumns.length > 0) {
      return {
        datasetName: datasetType,
        valid: false,
        records: [],
        recordCount: 0,
        missingColumns,
        errors: [`Missing mandatory column(s): ${missingColumns.join(', ')}`],
        warnings,
      };
    }

    // Transform and sanitize records
    const parsedRecords: T[] = [];
    rawRows.forEach((row, idx) => {
      const getVal = (col: string): string => {
        const originalKey = keyMap.get(col.toLowerCase());
        const val = originalKey ? row[originalKey] : '';
        return String(val ?? '').trim();
      };

      const getNum = (col: string): number => {
        const raw = getVal(col).replace(/[$,]/g, '');
        const num = parseFloat(raw);
        return isNaN(num) ? 0 : num;
      };

      if (datasetType === 'encounters') {
        const enc: Encounter = {
          Encounter_ID: getVal('Encounter_ID'),
          Admission_Date: getVal('Admission_Date'),
          Discharge_Date: getVal('Discharge_Date') || null,
          Department: getVal('Department') || 'General',
          Ward: getVal('Ward') || 'General Ward',
          Bed_Type: getVal('Bed_Type') || 'Standard',
          Payer_Type: getVal('Payer_Type') || 'Self Pay',
          Discharge_Status: (getVal('Discharge_Status') as Encounter['Discharge_Status']) || 'Admitted',
        };
        if (!enc.Encounter_ID) {
          warnings.push(`Row ${idx + 2}: skipped missing Encounter_ID`);
        } else {
          parsedRecords.push(enc as unknown as T);
        }
      } else if (datasetType === 'services') {
        const svc: Service = {
          Service_ID: getVal('Service_ID'),
          Encounter_ID: getVal('Encounter_ID'),
          Service_DateTime: getVal('Service_DateTime'),
          Revenue_Centre: getVal('Revenue_Centre') || 'General',
          Service_Code: getVal('Service_Code'),
          Description: getVal('Description'),
          Quantity: Math.max(1, getNum('Quantity')),
          Expected_Amount: getNum('Expected_Amount'),
        };
        if (!svc.Service_ID || !svc.Encounter_ID) {
          warnings.push(`Row ${idx + 2}: skipped service missing Service_ID or Encounter_ID`);
        } else {
          parsedRecords.push(svc as unknown as T);
        }
      } else if (datasetType === 'billing') {
        const bil: Billing = {
          Bill_ID: getVal('Bill_ID'),
          Encounter_ID: getVal('Encounter_ID'),
          Service_ID: getVal('Service_ID'),
          Bill_DateTime: getVal('Bill_DateTime'),
          Billed_Quantity: getNum('Billed_Quantity'),
          Billed_Amount: getNum('Billed_Amount'),
          Discount: getNum('Discount'),
          Bill_Status: (getVal('Bill_Status') as Billing['Bill_Status']) || 'Final',
        };
        if (!bil.Bill_ID || !bil.Encounter_ID) {
          warnings.push(`Row ${idx + 2}: skipped billing row missing Bill_ID or Encounter_ID`);
        } else {
          parsedRecords.push(bil as unknown as T);
        }
      } else if (datasetType === 'claims') {
        const clm: Claim = {
          Claim_ID: getVal('Claim_ID'),
          Encounter_ID: getVal('Encounter_ID'),
          Claim_Amount: getNum('Claim_Amount'),
          Approved_Amount: getNum('Approved_Amount'),
          Rejected_Amount: getNum('Rejected_Amount'),
          Claim_Status: (getVal('Claim_Status') as Claim['Claim_Status']) || 'Submitted',
          Submission_Date: getVal('Submission_Date'),
          Approval_Date: getVal('Approval_Date') || null,
        };
        if (!clm.Claim_ID || !clm.Encounter_ID) {
          warnings.push(`Row ${idx + 2}: skipped claim missing Claim_ID or Encounter_ID`);
        } else {
          parsedRecords.push(clm as unknown as T);
        }
      } else if (datasetType === 'collections') {
        const col: Collection = {
          Receipt_ID: getVal('Receipt_ID'),
          Encounter_ID: getVal('Encounter_ID'),
          Receipt_Date: getVal('Receipt_Date'),
          Amount: getNum('Amount'),
          Payment_Mode: (getVal('Payment_Mode') as Collection['Payment_Mode']) || 'Cash',
        };
        if (!col.Receipt_ID || !col.Encounter_ID) {
          warnings.push(`Row ${idx + 2}: skipped collection missing Receipt_ID or Encounter_ID`);
        } else {
          parsedRecords.push(col as unknown as T);
        }
      } else if (datasetType === 'tariff_master') {
        const trf: TariffMasterItem = {
          Service_Code: getVal('Service_Code'),
          Service_Description: getVal('Service_Description'),
          Revenue_Centre: getVal('Revenue_Centre'),
          Standard_Tariff: getNum('Standard_Tariff'),
          Effective_From: getVal('Effective_From') || '2026-01-01',
          Effective_To: getVal('Effective_To') || '2026-12-31',
          Payer: getVal('Payer') || 'Standard',
          Payer_Tariff: getNum('Payer_Tariff') || getNum('Standard_Tariff'),
        };
        if (!trf.Service_Code || !trf.Standard_Tariff) {
          warnings.push(`Row ${idx + 2}: skipped tariff missing Service_Code or Standard_Tariff`);
        } else {
          parsedRecords.push(trf as unknown as T);
        }
      } else if (datasetType === 'budget') {
        const bdg: BudgetRecord = {
          Month: getVal('Month'),
          Department: (getVal('Department') as HospitalDepartment) || 'Operations',
          Revenue_Budget: getNum('Revenue_Budget'),
          Expense_Budget: getNum('Expense_Budget'),
        };
        if (!bdg.Month || !bdg.Department) {
          warnings.push(`Row ${idx + 2}: skipped budget row missing Month or Department`);
        } else {
          parsedRecords.push(bdg as unknown as T);
        }
      }
    });

    return {
      datasetName: datasetType,
      valid: parsedRecords.length > 0,
      records: parsedRecords,
      recordCount: parsedRecords.length,
      missingColumns: [],
      errors,
      warnings,
    };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return {
      datasetName: datasetType,
      valid: false,
      records: [],
      recordCount: 0,
      missingColumns: [],
      errors: [`File parsing error: ${msg}`],
      warnings: [],
    };
  }
}

export function exportDatasetToCSV<T extends object>(data: T[], filename: string): void {
  if (data.length === 0) return;
  const worksheet = XLSX.utils.json_to_sheet(data);
  const csvOutput = XLSX.utils.sheet_to_csv(worksheet);
  const blob = new Blob([csvOutput], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exportAllDatasetsToXLSX(
  encounters: Encounter[],
  services: Service[],
  billings: Billing[],
  claims: Claim[],
  collections: Collection[],
  tariffMaster: TariffMasterItem[] = [],
  budgets: BudgetRecord[] = []
): void {
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(encounters), 'encounters');
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(services), 'services');
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(billings), 'billing');
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(claims), 'claims');
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(collections), 'collections');
  if (tariffMaster.length > 0) {
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(tariffMaster), 'tariff_master');
  }
  if (budgets.length > 0) {
    XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(budgets), 'budget');
  }
  XLSX.writeFile(wb, 'Hospital_CFO_Financial_Dataset_V2.xlsx');
}
