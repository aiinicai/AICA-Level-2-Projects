import * as XLSX from 'xlsx';
import { EmployeeMaster, EmployeeDeclaration, PayrollRunSummary } from '../types/payroll';

// Column mappings matching the exact python spec in build_masters.py
export const EMP_MASTER_COLUMNS = [
  { group: 'Identity', key: 'employeeCode', header: 'Employee_Code *', type: 'Text' },
  { group: 'Identity', key: 'employeeName', header: 'Employee_Name *', type: 'Text' },
  { group: 'Identity', key: 'pan', header: 'PAN *', type: 'Text' },
  { group: 'Identity', key: 'dateOfBirth', header: 'Date_of_Birth *', type: 'Date' },
  { group: 'Identity', key: 'gender', header: 'Gender', type: 'List' },
  { group: 'Employment', key: 'dateOfJoining', header: 'Date_of_Joining *', type: 'Date' },
  { group: 'Employment', key: 'dateOfLeaving', header: 'Date_of_Leaving', type: 'Date' },
  { group: 'Employment', key: 'employmentStatus', header: 'Employment_Status *', type: 'List' },
  { group: 'Employment', key: 'department', header: 'Department', type: 'Text' },
  { group: 'Employment', key: 'designation', header: 'Designation', type: 'Text' },
  { group: 'Employment', key: 'locationCity', header: 'Location_City *', type: 'Text' },
  { group: 'Employment', key: 'metroFlag', header: 'Metro_Flag *', type: 'List' },
  { group: 'Employment', key: 'costCenter', header: 'Cost_Center', type: 'Text' },
  { group: 'Contact', key: 'email', header: 'Email', type: 'Text' },
  { group: 'Contact', key: 'mobile', header: 'Mobile', type: 'Text' },
  { group: 'Bank', key: 'bankName', header: 'Bank_Name', type: 'Text' },
  { group: 'Bank', key: 'bankAccountNo', header: 'Bank_Account_No', type: 'Text' },
  { group: 'Bank', key: 'ifsc', header: 'IFSC', type: 'Text' },
  { group: 'Statutory', key: 'uan', header: 'UAN', type: 'Text' },
  { group: 'Statutory', key: 'pfNumber', header: 'PF_Number', type: 'Text' },
  { group: 'Statutory', key: 'pfApplicable', header: 'PF_Applicable *', type: 'List' },
  { group: 'Statutory', key: 'pfWageCeilingApplied', header: 'PF_Wage_Ceiling_Applied', type: 'List' },
  { group: 'Statutory', key: 'esiApplicable', header: 'ESI_Applicable *', type: 'List' },
  { group: 'Tax', key: 'taxRegimeOpted', header: 'Tax_Regime_Opted *', type: 'List' },
  { group: 'Tax', key: 'regimeDeclarationDate', header: 'Regime_Declaration_Date', type: 'Date' },
  { group: 'Salary', key: 'salaryEffectiveFrom', header: 'Salary_Effective_From *', type: 'Date' },
  { group: 'Salary', key: 'revisionReason', header: 'Revision_Reason *', type: 'List' },
  { group: 'Salary', key: 'annualCtc', header: 'Annual_CTC *', type: 'Number' },
  { group: 'Earnings (Monthly)', key: 'basicMonthly', header: 'Basic_Monthly *', type: 'Number' },
  { group: 'Earnings (Monthly)', key: 'hraMonthly', header: 'HRA_Monthly', type: 'Number' },
  { group: 'Earnings (Monthly)', key: 'conveyanceAllowanceMonthly', header: 'Conveyance_Allowance_Monthly', type: 'Number' },
  { group: 'Earnings (Monthly)', key: 'childrenEducationAllowanceMonthly', header: 'Children_Education_Allowance_Monthly', type: 'Number' },
  { group: 'Earnings (Monthly)', key: 'ltaMonthly', header: 'LTA_Monthly', type: 'Number' },
  { group: 'Earnings (Monthly)', key: 'specialAllowanceMonthly', header: 'Special_Allowance_Monthly', type: 'Number' },
  { group: 'Earnings (Monthly)', key: 'otherAllowanceMonthly', header: 'Other_Allowance_Monthly', type: 'Number' },
  { group: 'Earnings (Annual)', key: 'variablePayAnnual', header: 'Variable_Pay_Annual', type: 'Number' },
  { group: 'Earnings (Annual)', key: 'joiningBonus', header: 'Joining_Bonus', type: 'Number' },
  { group: 'Employer Cost', key: 'employerPfMonthly', header: 'Employer_PF_Monthly', type: 'Number' },
  { group: 'Employer Cost', key: 'employerNpsMonthly', header: 'Employer_NPS_Monthly', type: 'Number' },
  { group: 'Employer Cost', key: 'gratuityProvisionMonthly', header: 'Gratuity_Provision_Monthly', type: 'Number' },
  { group: 'Deductions', key: 'employeePfMonthly', header: 'Employee_PF_Monthly', type: 'Number' },
  { group: 'Deductions', key: 'professionalTaxMonthly', header: 'Professional_Tax_Monthly', type: 'Number' },
  { group: 'Deductions', key: 'otherRecurringDeductionMonthly', header: 'Other_Recurring_Deduction_Monthly', type: 'Number' },
  { group: 'Control', key: 'paymentMode', header: 'Payment_Mode', type: 'List' },
  { group: 'Control', key: 'remarks', header: 'Remarks', type: 'Text' },
];

export const EMP_DECL_COLUMNS = [
  { group: 'Key', key: 'employeeCode', header: 'Employee_Code *', type: 'Text' },
  { group: 'Key', key: 'employeeName', header: 'Employee_Name', type: 'Text' },
  { group: 'Key', key: 'pan', header: 'PAN', type: 'Text' },
  { group: 'Key', key: 'financialYear', header: 'Financial_Year *', type: 'Text' },
  { group: 'Key', key: 'declarationType', header: 'Declaration_Type *', type: 'List' },
  { group: 'Key', key: 'declarationDate', header: 'Declaration_Date *', type: 'Date' },
  { group: 'Key', key: 'regimeDeclared', header: 'Regime_Declared *', type: 'List' },
  { group: 'Key', key: 'proofStatus', header: 'Proof_Status', type: 'List' },
  { group: 'HRA (Old regime)', key: 'rentPaidAnnual', header: 'Rent_Paid_Annual', type: 'Number' },
  { group: 'HRA (Old regime)', key: 'rentFromDate', header: 'Rent_From_Date', type: 'Date' },
  { group: 'HRA (Old regime)', key: 'rentToDate', header: 'Rent_To_Date', type: 'Date' },
  { group: 'HRA (Old regime)', key: 'rentedCityMetro', header: 'Rented_City_Metro', type: 'List' },
  { group: 'HRA (Old regime)', key: 'landlordName', header: 'Landlord_Name', type: 'Text' },
  { group: 'HRA (Old regime)', key: 'landlordPan', header: 'Landlord_PAN', type: 'Text' },
  { group: 'House Property', key: 'housingLoanInterestSelfOccupied', header: 'Housing_Loan_Interest_Self_Occupied', type: 'Number' },
  { group: 'House Property', key: 'letOutPropertyNetIncome', header: 'Let_Out_Property_Net_Income', type: 'Number' },
  { group: 'House Property', key: 'lenderName', header: 'Lender_Name', type: 'Text' },
  { group: 'House Property', key: 'lenderPan', header: 'Lender_PAN', type: 'Text' },
  { group: 'Sec 80C', key: 'housingLoanPrincipal', header: 'Housing_Loan_Principal', type: 'Number' },
  { group: 'Sec 80C', key: 'ppf', header: 'PPF', type: 'Number' },
  { group: 'Sec 80C', key: 'licPremium', header: 'LIC_Premium', type: 'Number' },
  { group: 'Sec 80C', key: 'elssMutualFund', header: 'ELSS_Mutual_Fund', type: 'Number' },
  { group: 'Sec 80C', key: 'nsc', header: 'NSC', type: 'Number' },
  { group: 'Sec 80C', key: 'tuitionFees', header: 'Tuition_Fees', type: 'Number' },
  { group: 'Sec 80C', key: 'sukanyaSamriddhi', header: 'Sukanya_Samriddhi', type: 'Number' },
  { group: 'Sec 80C', key: 'taxSaverFd5yr', header: 'Tax_Saver_FD_5yr', type: 'Number' },
  { group: 'Sec 80C', key: 'other80C', header: 'Other_80C', type: 'Number' },
  { group: 'NPS', key: 'npsSelf80CCD1B', header: 'NPS_Self_80CCD1B', type: 'Number' },
  { group: 'NPS', key: 'optInEmployerNps80CCD2', header: 'Opt_In_Employer_NPS_80CCD2', type: 'List' },
  { group: 'Sec 80D', key: 'mediclaimSelfFamily', header: 'Mediclaim_Self_Family', type: 'Number' },
  { group: 'Sec 80D', key: 'mediclaimParents', header: 'Mediclaim_Parents', type: 'Number' },
  { group: 'Sec 80D', key: 'parentsSeniorCitizen', header: 'Parents_Senior_Citizen', type: 'List' },
  { group: 'Sec 80D', key: 'preventiveHealthCheckup', header: 'Preventive_Health_Checkup', type: 'Number' },
  { group: 'Sec 80D', key: 'medicalExpenditureSeniorCitizen', header: 'Medical_Expenditure_Senior_Citizen', type: 'Number' },
  { group: 'Other Chapter VI-A', key: 'sec80DDDisabledDependent', header: 'Sec_80DD_Disabled_Dependent', type: 'List' },
  { group: 'Other Chapter VI-A', key: 'sec80DDBMedicalTreatment', header: 'Sec_80DDB_Medical_Treatment', type: 'Number' },
  { group: 'Other Chapter VI-A', key: 'sec80EEducationLoanInterest', header: 'Sec_80E_Education_Loan_Interest', type: 'Number' },
  { group: 'Other Chapter VI-A', key: 'sec80EEBEVLoanInterest', header: 'Sec_80EEB_EV_Loan_Interest', type: 'Number' },
  { group: 'Other Chapter VI-A', key: 'sec80GDonation100pct', header: 'Sec_80G_Donation_100pct_No_Limit', type: 'Number' },
  { group: 'Other Chapter VI-A', key: 'sec80GDonation50pct', header: 'Sec_80G_Donation_50pct_No_Limit', type: 'Number' },
  { group: 'Other Chapter VI-A', key: 'sec80USelfDisability', header: 'Sec_80U_Self_Disability', type: 'List' },
  { group: 'Exemptions u/s 10', key: 'ltaExemptionClaimed', header: 'LTA_Exemption_Claimed', type: 'Number' },
  { group: 'Exemptions u/s 10', key: 'otherExemptionSec10', header: 'Other_Exemption_u_s_10', type: 'Number' },
  { group: 'Other Income', key: 'savingsBankInterest', header: 'Savings_Bank_Interest', type: 'Number' },
  { group: 'Other Income', key: 'fixedDepositInterest', header: 'Fixed_Deposit_Interest', type: 'Number' },
  { group: 'Other Income', key: 'otherIncomeDeclared', header: 'Other_Income_Declared', type: 'Number' },
  { group: 'Previous Employer', key: 'prevEmployerName', header: 'Prev_Employer_Name', type: 'Text' },
  { group: 'Previous Employer', key: 'prevEmployerGrossSalary', header: 'Prev_Employer_Gross_Salary', type: 'Number' },
  { group: 'Previous Employer', key: 'prevEmployerExemptionsSec10', header: 'Prev_Employer_Exemptions_u_s_10', type: 'Number' },
  { group: 'Previous Employer', key: 'prevEmployerPfDeducted', header: 'Prev_Employer_PF_Deducted', type: 'Number' },
  { group: 'Previous Employer', key: 'prevEmployerPtDeducted', header: 'Prev_Employer_PT_Deducted', type: 'Number' },
  { group: 'Previous Employer', key: 'prevEmployerTdsDeducted', header: 'Prev_Employer_TDS_Deducted', type: 'Number' },
  { group: 'Control', key: 'remarks', header: 'Remarks', type: 'Text' },
];

export function exportEmployeeMasterExcel(employees: EmployeeMaster[], filename: string = '01_Employee_Master.xlsx') {
  const wb = XLSX.utils.book_new();

  // Data sheet
  const headers = EMP_MASTER_COLUMNS.map((c) => c.header);
  const groups = EMP_MASTER_COLUMNS.map((c) => c.group);

  const rows: (string | number)[][] = [groups, headers];

  employees.forEach((emp) => {
    const row: (string | number)[] = EMP_MASTER_COLUMNS.map((c) => {
      const val = (emp as unknown as Record<string, unknown>)[c.key];
      return (val !== undefined && val !== null ? val : '') as string | number;
    });
    rows.push(row);
  });

  const ws = XLSX.utils.aoa_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, 'Data');

  // Download
  XLSX.writeFile(wb, filename);
}

export function exportEmployeeDeclarationExcel(
  declarations: EmployeeDeclaration[],
  filename: string = '02_Employee_Declaration.xlsx'
) {
  const wb = XLSX.utils.book_new();

  const headers = EMP_DECL_COLUMNS.map((c) => c.header);
  const groups = EMP_DECL_COLUMNS.map((c) => c.group);

  const rows: (string | number)[][] = [groups, headers];

  declarations.forEach((decl) => {
    const row: (string | number)[] = EMP_DECL_COLUMNS.map((c) => {
      const val = (decl as unknown as Record<string, unknown>)[c.key];
      return (val !== undefined && val !== null ? val : '') as string | number;
    });
    rows.push(row);
  });

  const ws = XLSX.utils.aoa_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, 'Data');

  XLSX.writeFile(wb, filename);
}

export function exportSalaryRegisterExcel(summary: PayrollRunSummary, filename?: string) {
  const wb = XLSX.utils.book_new();

  const headers = [
    'Emp Code',
    'Employee Name',
    'Designation',
    'Department',
    'PAN',
    'Bank A/C',
    'IFSC',
    'Total Days',
    'Payable Days',
    'LOP Days',
    'Basic Earned',
    'HRA Earned',
    'Special Allw',
    'Gross Earned',
    'Employee PF',
    'ESI',
    'Professional Tax',
    'Monthly TDS',
    'Total Deductions',
    'Net Pay',
    'Employer PF',
    'Regime Applied',
    'Annual Tax',
    'Saving Recommendation',
  ];

  const rows: (string | number)[][] = [headers];

  summary.records.forEach((r) => {
    rows.push([
      r.employeeCode,
      r.employeeName,
      r.designation,
      r.department,
      r.pan,
      r.bankAccountNo,
      r.ifsc,
      r.totalDaysInMonth,
      r.payableDays,
      r.lopDays,
      r.basicEarned,
      r.hraEarned,
      r.specialAllowanceEarned,
      r.grossEarned,
      r.employeePf,
      r.esi,
      r.professionalTax,
      r.tdsDeducted,
      r.totalDeductions,
      r.netPay,
      r.employerPf,
      r.regimeApplied,
      r.annualTaxLiability,
      r.regimeSavingRecommendation,
    ]);
  });

  // Summary row
  rows.push([
    'TOTAL',
    `Headcount: ${summary.headcount}`,
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    summary.totalGross,
    summary.totalPf,
    summary.totalEsi,
    0,
    summary.totalTds,
    summary.totalDeductions,
    summary.totalNetPayout,
    '',
    '',
    '',
    '',
  ]);

  const ws = XLSX.utils.aoa_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, 'Salary_Register');

  const defaultName = `Salary_Register_${summary.financialYear}_${summary.monthLabel.replace(/\s+/g, '_')}.xlsx`;
  XLSX.writeFile(wb, filename || defaultName);
}

export async function parseEmployeeMasterExcel(file: File): Promise<EmployeeMaster[]> {
  const data = await file.arrayBuffer();
  const wb = XLSX.read(data, { type: 'array' });
  const sheetName = wb.SheetNames.includes('Data') ? 'Data' : wb.SheetNames[0];
  const ws = wb.Sheets[sheetName];

  const rawRows: (string | number)[][] = XLSX.utils.sheet_to_json(ws, { header: 1 });
  if (rawRows.length < 2) {
    throw new Error('The uploaded file does not contain valid header and data rows.');
  }

  // Find header row: either row 0 or row 1 (if group band exists)
  let headerRowIndex = 0;
  for (let i = 0; i < Math.min(rawRows.length, 5); i++) {
    const rowStr = rawRows[i].map((c) => String(c).trim().toLowerCase());
    if (rowStr.some((s) => s.includes('employee_code') || s.includes('employeecode'))) {
      headerRowIndex = i;
      break;
    }
  }

  const rawHeaders = rawRows[headerRowIndex].map((h) =>
    String(h || '')
      .replace(/\*/g, '')
      .trim()
      .toLowerCase()
  );

  const keyMap: Record<string, string> = {};
  EMP_MASTER_COLUMNS.forEach((c) => {
    const cleanHeader = c.header.replace(/\*/g, '').trim().toLowerCase();
    keyMap[cleanHeader] = c.key;
    keyMap[c.key.toLowerCase()] = c.key;
  });

  const columnIndices: { colIndex: number; key: string; type: string }[] = [];
  rawHeaders.forEach((h, idx) => {
    if (keyMap[h]) {
      const colDef = EMP_MASTER_COLUMNS.find((c) => c.key === keyMap[h]);
      columnIndices.push({
        colIndex: idx,
        key: keyMap[h],
        type: colDef ? colDef.type : 'Text',
      });
    }
  });

  const employees: EmployeeMaster[] = [];

  for (let r = headerRowIndex + 1; r < rawRows.length; r++) {
    const row = rawRows[r];
    if (!row || row.length === 0) continue;

    const empObj: Record<string, unknown> = {
      // Default fallbacks
      employmentStatus: 'Active',
      metroFlag: 'N',
      pfApplicable: 'Y',
      pfWageCeilingApplied: 'N',
      esiApplicable: 'N',
      taxRegimeOpted: 'New',
      revisionReason: 'Annual Revision',
      paymentMode: 'Bank Transfer',
      professionalTaxMonthly: 0,
    };

    let hasData = false;
    columnIndices.forEach(({ colIndex, key, type }) => {
      const cellVal = row[colIndex];
      if (cellVal !== undefined && cellVal !== null && String(cellVal).trim() !== '') {
        hasData = true;
        if (type === 'Number') {
          const num = typeof cellVal === 'number' ? cellVal : parseFloat(String(cellVal).replace(/,/g, ''));
          empObj[key] = isNaN(num) ? 0 : num;
        } else {
          empObj[key] = String(cellVal).trim();
        }
      }
    });

    if (hasData && empObj.employeeCode) {
      employees.push(empObj as unknown as EmployeeMaster);
    }
  }

  return employees;
}

export async function parseEmployeeDeclarationExcel(file: File): Promise<EmployeeDeclaration[]> {
  const data = await file.arrayBuffer();
  const wb = XLSX.read(data, { type: 'array' });
  const sheetName = wb.SheetNames.includes('Data') ? 'Data' : wb.SheetNames[0];
  const ws = wb.Sheets[sheetName];

  const rawRows: (string | number)[][] = XLSX.utils.sheet_to_json(ws, { header: 1 });
  if (rawRows.length < 2) {
    throw new Error('The uploaded file does not contain valid header and data rows.');
  }

  let headerRowIndex = 0;
  for (let i = 0; i < Math.min(rawRows.length, 5); i++) {
    const rowStr = rawRows[i].map((c) => String(c).trim().toLowerCase());
    if (rowStr.some((s) => s.includes('employee_code') || s.includes('employeecode'))) {
      headerRowIndex = i;
      break;
    }
  }

  const rawHeaders = rawRows[headerRowIndex].map((h) =>
    String(h || '')
      .replace(/\*/g, '')
      .trim()
      .toLowerCase()
  );

  const keyMap: Record<string, string> = {};
  EMP_DECL_COLUMNS.forEach((c) => {
    const cleanHeader = c.header.replace(/\*/g, '').trim().toLowerCase();
    keyMap[cleanHeader] = c.key;
    keyMap[c.key.toLowerCase()] = c.key;
  });

  const columnIndices: { colIndex: number; key: string; type: string }[] = [];
  rawHeaders.forEach((h, idx) => {
    if (keyMap[h]) {
      const colDef = EMP_DECL_COLUMNS.find((c) => c.key === keyMap[h]);
      columnIndices.push({
        colIndex: idx,
        key: keyMap[h],
        type: colDef ? colDef.type : 'Text',
      });
    }
  });

  const declarations: EmployeeDeclaration[] = [];

  for (let r = headerRowIndex + 1; r < rawRows.length; r++) {
    const row = rawRows[r];
    if (!row || row.length === 0) continue;

    const declObj: Record<string, unknown> = {
      financialYear: '2026-27',
      declarationType: 'Proposed',
      regimeDeclared: 'New',
      proofStatus: 'Pending',
      rentedCityMetro: 'N',
      parentsSeniorCitizen: 'N',
      optInEmployerNps80CCD2: 'N',
      sec80DDDisabledDependent: 'None',
      sec80USelfDisability: 'None',
    };

    let hasData = false;
    columnIndices.forEach(({ colIndex, key, type }) => {
      const cellVal = row[colIndex];
      if (cellVal !== undefined && cellVal !== null && String(cellVal).trim() !== '') {
        hasData = true;
        if (type === 'Number') {
          const num = typeof cellVal === 'number' ? cellVal : parseFloat(String(cellVal).replace(/,/g, ''));
          declObj[key] = isNaN(num) ? 0 : num;
        } else {
          declObj[key] = String(cellVal).trim();
        }
      }
    });

    if (hasData && declObj.employeeCode) {
      declarations.push(declObj as unknown as EmployeeDeclaration);
    }
  }

  return declarations;
}
