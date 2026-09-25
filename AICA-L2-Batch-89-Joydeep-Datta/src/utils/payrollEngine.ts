import {
  EmployeeMaster,
  EmployeeDeclaration,
  TaxConfig,
  MonthlySalaryRecord,
  PayrollRunSummary,
  TaxRegime,
} from '../types/payroll';
import { computeTaxBreakdown } from './taxEngine';

export const FY_MONTHS = [
  { index: 1, name: 'April', short: 'Apr', days: 30, calMonth: 3 },
  { index: 2, name: 'May', short: 'May', days: 31, calMonth: 4 },
  { index: 3, name: 'June', short: 'Jun', days: 30, calMonth: 5 },
  { index: 4, name: 'July', short: 'Jul', days: 31, calMonth: 6 },
  { index: 5, name: 'August', short: 'Aug', days: 31, calMonth: 7 },
  { index: 6, name: 'September', short: 'Sep', days: 30, calMonth: 8 },
  { index: 7, name: 'October', short: 'Oct', days: 31, calMonth: 9 },
  { index: 8, name: 'November', short: 'Nov', days: 30, calMonth: 10 },
  { index: 9, name: 'December', short: 'Dec', days: 31, calMonth: 11 },
  { index: 10, name: 'January', short: 'Jan', days: 31, calMonth: 0 },
  { index: 11, name: 'February', short: 'Feb', days: 28, calMonth: 1 },
  { index: 12, name: 'March', short: 'Mar', days: 31, calMonth: 2 },
];

export function parseDateSafe(dateStr?: string): Date | null {
  if (!dateStr || !dateStr.trim()) return null;
  const s = dateStr.trim();
  if (s.includes('-')) {
    const parts = s.split('-');
    if (parts[0].length === 4) {
      // YYYY-MM-DD
      return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    } else if (parts[2].length === 4) {
      // DD-MM-YYYY
      return new Date(parseInt(parts[2], 10), parseInt(parts[1], 10) - 1, parseInt(parts[0], 10));
    }
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

export function getDaysInMonth(year: number, calMonth: number): number {
  return new Date(year, calMonth + 1, 0).getDate();
}

export function calculatePayableDays(
  emp: EmployeeMaster,
  fyStartYear: number,
  fyMonthIndex: number,
  lopDays: number = 0
): { totalDays: number; payableDays: number; prorationFactor: number } {
  const monthInfo = FY_MONTHS[fyMonthIndex - 1];
  const calYear = fyMonthIndex <= 9 ? fyStartYear : fyStartYear + 1;
  const totalDays = getDaysInMonth(calYear, monthInfo.calMonth);

  const monthStart = new Date(calYear, monthInfo.calMonth, 1);
  const monthEnd = new Date(calYear, monthInfo.calMonth, totalDays);

  const joinDate = parseDateSafe(emp.dateOfJoining);
  const leaveDate = parseDateSafe(emp.dateOfLeaving);

  // If joined after this month
  if (joinDate && joinDate > monthEnd) {
    return { totalDays, payableDays: 0, prorationFactor: 0 };
  }
  // If left before this month starts
  if (leaveDate && leaveDate < monthStart) {
    return { totalDays, payableDays: 0, prorationFactor: 0 };
  }

  let effectiveStartDay = 1;
  if (joinDate && joinDate >= monthStart) {
    effectiveStartDay = joinDate.getDate();
  }

  let effectiveEndDay = totalDays;
  if (leaveDate && leaveDate <= monthEnd) {
    effectiveEndDay = leaveDate.getDate();
  }

  let activeDays = Math.max(0, effectiveEndDay - effectiveStartDay + 1);
  let payableDays = Math.max(0, activeDays - lopDays);
  const prorationFactor = totalDays > 0 ? payableDays / totalDays : 0;

  return {
    totalDays,
    payableDays,
    prorationFactor,
  };
}

export function processEmployeeMonthlySalary(
  emp: EmployeeMaster,
  decl: EmployeeDeclaration | undefined,
  config: TaxConfig,
  fyMonthIndex: number, // 1 = April, 12 = March
  priorMonthsEarnedGross: number = 0,
  tdsDeductedYtd: number = 0,
  lopDays: number = 0
): MonthlySalaryRecord {
  const fyStartYear = parseInt(config.financialYear.split('-')[0], 10);
  const monthInfo = FY_MONTHS[fyMonthIndex - 1];
  const calYear = fyMonthIndex <= 9 ? fyStartYear : fyStartYear + 1;

  // 1. Proration (Answer 2: Option A - Calendar Days)
  const { totalDays, payableDays, prorationFactor } = calculatePayableDays(emp, fyStartYear, fyMonthIndex, lopDays);

  // 2. Earnings Computation
  const basicEarned = Math.round(emp.basicMonthly * prorationFactor);
  const hraEarned = Math.round(emp.hraMonthly * prorationFactor);
  const conveyanceEarned = Math.round(emp.conveyanceAllowanceMonthly * prorationFactor);
  const ceaEarned = Math.round(emp.childrenEducationAllowanceMonthly * prorationFactor);
  const ltaEarned = Math.round(emp.ltaMonthly * prorationFactor);
  const specialAllowanceEarned = Math.round(emp.specialAllowanceMonthly * prorationFactor);
  const otherAllowanceEarned = Math.round(emp.otherAllowanceMonthly * prorationFactor);

  // Annual components paid in specific months or spread (variable pay/joining bonus)
  let variablePayEarned = 0;
  let joiningBonusEarned = 0;
  // If mid-year joiner with joining bonus, pay in joining month
  const joinDate = parseDateSafe(emp.dateOfJoining);
  if (joinDate && joinDate.getFullYear() === calYear && joinDate.getMonth() === monthInfo.calMonth) {
    joiningBonusEarned = emp.joiningBonus || 0;
  }
  // Variable pay in last month of FY (March) or spread if any
  if (fyMonthIndex === 12 && emp.variablePayAnnual > 0) {
    variablePayEarned = emp.variablePayAnnual;
  }

  const grossEarned =
    basicEarned +
    hraEarned +
    conveyanceEarned +
    ceaEarned +
    ltaEarned +
    specialAllowanceEarned +
    otherAllowanceEarned +
    variablePayEarned +
    joiningBonusEarned;

  // 3. Statutory Deductions
  let employeePf = 0;
  let employerPf = 0;
  if (emp.pfApplicable === 'Y' && basicEarned > 0) {
    let pfWage = basicEarned;
    if (emp.pfWageCeilingApplied === 'Y') {
      const proratedCeiling = Math.round(config.common.pfWageCeiling * prorationFactor);
      pfWage = Math.min(basicEarned, proratedCeiling);
    }
    employeePf = Math.round(pfWage * config.common.pfEmployeeRate);
    employerPf = Math.round(pfWage * config.common.pfEmployerRate);
  }

  // ESI
  let esi = 0;
  if (emp.esiApplicable === 'Y' && grossEarned <= 21000 && grossEarned > 0) {
    esi = Math.round(grossEarned * 0.0075);
  }

  // Professional Tax: User explicit instruction (Answer 5) -> PT does not exist
  const professionalTax = 0;

  const otherDeductions = Math.round(emp.otherRecurringDeductionMonthly * prorationFactor);

  // 4. Employer Contributions
  let employerNps = 0;
  if (decl?.optInEmployerNps80CCD2 === 'Y' || emp.employerNpsMonthly > 0) {
    employerNps = Math.round(emp.employerNpsMonthly * prorationFactor);
  }
  const gratuityProvision = Math.round(emp.gratuityProvisionMonthly * prorationFactor);
  const totalEmployerCost = employerPf + employerNps + gratuityProvision;

  // 5. Projected Annual Salary & TDS Computation
  const remainingMonthsInFy = 12 - fyMonthIndex + 1;
  const projectedFutureGross = emp.basicMonthly + emp.hraMonthly + emp.specialAllowanceMonthly + emp.conveyanceAllowanceMonthly;
  
  // Projected annual figures for full tax calculation
  const projectedAnnualGross =
    priorMonthsEarnedGross + grossEarned + Math.max(0, remainingMonthsInFy - 1) * projectedFutureGross;
  const projectedAnnualBasic = emp.basicMonthly * 12;
  const projectedAnnualHra = emp.hraMonthly * 12;
  const projectedAnnualPf = employeePf * 12;

  // Compute under both Old and New Tax Regimes
  const oldBreakdown = computeTaxBreakdown(
    emp,
    decl,
    config,
    'Old',
    projectedAnnualGross,
    projectedAnnualBasic,
    projectedAnnualHra,
    projectedAnnualPf,
    remainingMonthsInFy,
    tdsDeductedYtd
  );

  const newBreakdown = computeTaxBreakdown(
    emp,
    decl,
    config,
    'New',
    projectedAnnualGross,
    projectedAnnualBasic,
    projectedAnnualHra,
    projectedAnnualPf,
    remainingMonthsInFy,
    tdsDeductedYtd
  );

  // Determine Regime to Apply (Declaration overrides Master)
  const regimeApplied: TaxRegime = decl?.regimeDeclared || emp.taxRegimeOpted || 'New';
  const appliedBreakdown = regimeApplied === 'Old' ? oldBreakdown : newBreakdown;

  // Tax Saving recommendation
  let regimeSavingRecommendation = '';
  const diff = oldBreakdown.totalAnnualTaxLiability - newBreakdown.totalAnnualTaxLiability;
  if (diff > 500) {
    regimeSavingRecommendation = `New Regime saves ₹${Math.abs(diff).toLocaleString('en-IN')}`;
  } else if (diff < -500) {
    regimeSavingRecommendation = `Old Regime saves ₹${Math.abs(diff).toLocaleString('en-IN')}`;
  } else {
    regimeSavingRecommendation = 'Tax is equal in both regimes';
  }

  const tdsDeducted = payableDays > 0 ? appliedBreakdown.currentMonthTds : 0;

  // 6. Net Pay
  const totalDeductions = employeePf + esi + professionalTax + otherDeductions + tdsDeducted;
  const netPay = Math.max(0, grossEarned - totalDeductions);

  return {
    employeeCode: emp.employeeCode,
    employeeName: emp.employeeName,
    designation: emp.designation,
    department: emp.department,
    pan: emp.pan,
    bankAccountNo: emp.bankAccountNo,
    bankName: emp.bankName,
    ifsc: emp.ifsc,
    employmentStatus: emp.employmentStatus,
    month: fyMonthIndex,
    monthName: monthInfo.name,
    year: calYear,
    totalDaysInMonth: totalDays,
    payableDays,
    lopDays,
    prorationFactor,
    basicEarned,
    hraEarned,
    conveyanceEarned,
    ceaEarned,
    ltaEarned,
    specialAllowanceEarned,
    otherAllowanceEarned,
    variablePayEarned,
    joiningBonusEarned,
    grossEarned,
    employeePf,
    esi,
    professionalTax,
    otherDeductions,
    tdsDeducted,
    totalDeductions,
    netPay,
    employerPf,
    employerNps,
    gratuityProvision,
    totalEmployerCost,
    regimeApplied,
    annualTaxLiability: appliedBreakdown.totalAnnualTaxLiability,
    oldRegimeTax: oldBreakdown.totalAnnualTaxLiability,
    newRegimeTax: newBreakdown.totalAnnualTaxLiability,
    regimeSavingRecommendation,
    taxCalculation: appliedBreakdown,
  };
}

export function executeMonthlyPayrollRun(
  employees: EmployeeMaster[],
  declarations: EmployeeDeclaration[],
  config: TaxConfig,
  fyMonthIndex: number, // 1 to 12
  historicalPayroll: Record<number, MonthlySalaryRecord[]> = {}
): PayrollRunSummary {
  const monthInfo = FY_MONTHS[fyMonthIndex - 1];
  const records: MonthlySalaryRecord[] = [];

  for (const emp of employees) {
    // Collect YTD figures for this employee from previous months in the same FY
    let ytdGross = 0;
    let ytdTds = 0;

    for (let m = 1; m < fyMonthIndex; m++) {
      const pastMonthRecords = historicalPayroll[m];
      if (pastMonthRecords) {
        const pastRecord = pastMonthRecords.find((r) => r.employeeCode === emp.employeeCode);
        if (pastRecord) {
          ytdGross += pastRecord.grossEarned;
          ytdTds += pastRecord.tdsDeducted;
        }
      }
    }

    const decl = declarations.find((d) => d.employeeCode === emp.employeeCode);
    const rec = processEmployeeMonthlySalary(emp, decl, config, fyMonthIndex, ytdGross, ytdTds);
    records.push(rec);
  }

  const headcount = records.filter((r) => r.payableDays > 0).length;
  const totalGross = records.reduce((sum, r) => sum + r.grossEarned, 0);
  const totalPf = records.reduce((sum, r) => sum + r.employeePf, 0);
  const totalEsi = records.reduce((sum, r) => sum + r.esi, 0);
  const totalTds = records.reduce((sum, r) => sum + r.tdsDeducted, 0);
  const totalOtherDeductions = records.reduce((sum, r) => sum + r.otherDeductions, 0);
  const totalDeductions = records.reduce((sum, r) => sum + r.totalDeductions, 0);
  const totalNetPayout = records.reduce((sum, r) => sum + r.netPay, 0);
  const totalEmployerCost = records.reduce((sum, r) => sum + r.totalEmployerCost, 0);

  return {
    financialYear: config.financialYear,
    month: fyMonthIndex,
    monthLabel: `${monthInfo.name} ${fyMonthIndex <= 9 ? config.financialYear.split('-')[0] : parseInt(config.financialYear.split('-')[0], 10) + 1}`,
    runDate: new Date().toISOString().split('T')[0],
    headcount,
    totalGross,
    totalPf,
    totalEsi,
    totalTds,
    totalOtherDeductions,
    totalDeductions,
    totalNetPayout,
    totalEmployerCost,
    records,
  };
}

export const runPayrollMonth = executeMonthlyPayrollRun;

export function createDefaultDeclaration(emp: EmployeeMaster, fy: string = '2026-27'): EmployeeDeclaration {
  return {
    employeeCode: emp.employeeCode,
    employeeName: emp.employeeName,
    pan: emp.pan,
    financialYear: fy,
    declarationDate: new Date().toISOString().split('T')[0],
    declarationType: 'Proposed',
    regimeDeclared: emp.taxRegimeOpted,
    proofStatus: 'Pending',
    rentPaidAnnual: 0,
    rentedCityMetro: emp.metroFlag,
    housingLoanInterestSelfOccupied: 0,
    letOutPropertyNetIncome: 0,
    housingLoanPrincipal: 0,
    ppf: 0,
    licPremium: 0,
    elssMutualFund: 0,
    nsc: 0,
    tuitionFees: 0,
    sukanyaSamriddhi: 0,
    taxSaverFd5yr: 0,
    other80C: 0,
    npsSelf80CCD1B: 0,
    optInEmployerNps80CCD2: 'N',
    mediclaimSelfFamily: 0,
    mediclaimParents: 0,
    parentsSeniorCitizen: 'N',
    preventiveHealthCheckup: 0,
    medicalExpenditureSeniorCitizen: 0,
    sec80DDDisabledDependent: 'None',
    sec80DDBMedicalTreatment: 0,
    sec80EEducationLoanInterest: 0,
    sec80EEBEVLoanInterest: 0,
    sec80GDonation100pct: 0,
    sec80GDonation50pct: 0,
    sec80USelfDisability: 'None',
    ltaExemptionClaimed: 0,
    otherExemptionSec10: 0,
    savingsBankInterest: 0,
    fixedDepositInterest: 0,
    otherIncomeDeclared: 0,
    prevEmployerGrossSalary: 0,
    prevEmployerExemptionsSec10: 0,
    prevEmployerPfDeducted: 0,
    prevEmployerPtDeducted: 0,
    prevEmployerTdsDeducted: 0,
  };
}

export function formatInr(amount: number): string {
  return '₹' + Math.round(amount || 0).toLocaleString('en-IN');
}

/**
 * Calculates progressive historical monthly salary records for a single employee
 * across months 1 to maxMonth (default 12 for the full FY), carrying forward
 * actual YTD gross and YTD TDS as required under Indian IT Section 192.
 */
export function getEmployeeAllMonthlyRecords(
  employee: EmployeeMaster,
  declaration: EmployeeDeclaration | undefined,
  config: TaxConfig,
  maxMonth: number = 12
): MonthlySalaryRecord[] {
  const records: MonthlySalaryRecord[] = [];
  let ytdGross = 0;
  let ytdTds = 0;

  for (let m = 1; m <= maxMonth; m++) {
    const rec = processEmployeeMonthlySalary(
      employee,
      declaration,
      config,
      m,
      ytdGross,
      ytdTds
    );
    records.push(rec);
    ytdGross += rec.grossEarned;
    ytdTds += rec.tdsDeducted;
  }

  return records;
}


