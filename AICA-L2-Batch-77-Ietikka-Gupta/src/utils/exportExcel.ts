import * as XLSX from 'xlsx';
import { ChallanRecord, AssesseeDetails } from '../types';

export function exportTaxAuditToExcel(
  records: ChallanRecord[],
  assessee: AssesseeDetails
) {
  const wb = XLSX.utils.book_new();

  // 1. Prepare Clause 20(b) Sheet
  const clause20bData: any[] = [
    ["FORM 3CD - CLAUSE 20(b) STATEMENT"],
    ["Details of contributions received from employees for various funds as referred to in section 36(1)(va)"],
    [],
    ["Name of Assessee:", assessee.name, "", "PAN:", assessee.pan],
    ["Assessment Year:", assessee.assessmentYear, "", "Financial Year:", assessee.financialYear],
    ["Tax Auditor:", assessee.auditorName, "", "Firm:", assessee.firmName || "Chartered Accountant"],
    ["Date of Report:", assessee.dateOfReport, "", "Tool:", "Tax Audit ESI & PF Digitizer by CA Ietikka Gupta"],
    [],
    [
      "Sl. No.",
      "Nature of Fund",
      "Sum received from employees (Rs.)",
      "Due date for payment",
      "Actual date of payment to concerned authorities",
      "The actual amount paid (Rs.)",
      "Amount not paid to employee's account by due date (Disallowed u/s 36(1)(va)) (Rs.)",
      "Remarks / TRRN / Challan No."
    ]
  ];

  let totalEmployeeContrib = 0;
  let totalActualPaid = 0;
  let totalDisallowed = 0;

  records.forEach((rec, idx) => {
    const fundNature = rec.fundType === 'PF' 
      ? `Employees' Provident Fund (${rec.wageMonth})` 
      : `Employees' State Insurance (${rec.wageMonth})`;

    totalEmployeeContrib += rec.employeeContribution;
    totalActualPaid += rec.employeeContribution; // in 20(b) actual amount paid against employee share
    totalDisallowed += rec.disallowableAmount;

    clause20bData.push([
      idx + 1,
      fundNature,
      rec.employeeContribution,
      rec.statutoryDueDate,
      rec.actualPaymentDate,
      rec.employeeContribution,
      rec.disallowableAmount > 0 ? rec.disallowableAmount : 0,
      rec.status === 'DELAYED' 
        ? `Delayed by ${rec.delayDays} day(s) | Ref: ${rec.challanReference}`
        : `Paid on time | Ref: ${rec.challanReference}`
    ]);
  });

  // Summary Row
  clause20bData.push([
    "TOTAL",
    "",
    totalEmployeeContrib,
    "",
    "",
    totalActualPaid,
    totalDisallowed,
    `Total Disallowance u/s 36(1)(va): Rs. ${totalDisallowed.toLocaleString('en-IN')}`
  ]);

  const wsClause20b = XLSX.utils.aoa_to_sheet(clause20bData);

  // Set column widths
  wsClause20b['!cols'] = [
    { wch: 8 },  // Sl No
    { wch: 35 }, // Nature of Fund
    { wch: 24 }, // Sum received
    { wch: 16 }, // Due date
    { wch: 18 }, // Actual date
    { wch: 20 }, // Actual amount paid
    { wch: 28 }, // Disallowed amount
    { wch: 40 }, // Remarks
  ];

  XLSX.utils.book_append_sheet(wb, wsClause20b, "Form 3CD Clause 20(b)");

  // 2. Prepare Executive Summary Sheet
  const taxRate = 0.312; // 30% + 4% cess
  const estimatedTaxLiability = Math.round(totalDisallowed * taxRate);

  const summaryData: any[] = [
    ["INCOME TAX AUDIT EXECUTIVE SUMMARY - ESI & PF COMPLIANCE"],
    ["Prepared by: " + assessee.auditorName + " (Chartered Accountant)"],
    [],
    ["CLIENT PARTICULARS"],
    ["Assessee Name", assessee.name],
    ["Permanent Account Number (PAN)", assessee.pan],
    ["Assessment Year", assessee.assessmentYear],
    ["Previous Year (Financial Year)", assessee.financialYear],
    ["Tax Auditor", assessee.auditorName],
    ["Auditor Membership No.", assessee.membershipNumber || "N/A"],
    ["Date of Report", assessee.dateOfReport],
    [],
    ["STATUTORY COMPLIANCE BREAKDOWN (Section 36(1)(va) read with Section 43B)"],
    ["Total Challans Analyzed", records.length],
    ["Total Statutory Amount Deposited (EE + ER + Admin)", records.reduce((s, r) => s + r.totalChallanAmount, 0)],
    ["Total Employee Contribution Recovered", totalEmployeeContrib],
    ["Total Employee Contribution Paid ON OR BEFORE Due Date (Allowed)", totalEmployeeContrib - totalDisallowed],
    ["Total Employee Contribution Paid AFTER Due Date (DISALLOWED u/s 36(1)(va))", totalDisallowed],
    ["Estimated Additional Income Tax Liability (approx @ 31.2%)", estimatedTaxLiability],
    [],
    ["STATUTORY PROVISIONS & LEGAL CITATION"],
    ["Section 36(1)(va)", "Deduction for employee contribution is allowable ONLY if credited on or before the due date under respective Act."],
    ["Supreme Court Ruling", "Checkmate Services P. Ltd vs CIT (2022) 448 ITR 518 (SC) confirms Section 43B relaxation does NOT apply to employee share."],
    ["Tax Audit Reporting", "Amount in Column 7 MUST be reported under Clause 20(b) and added back to taxable business profits."]
  ];

  const wsSummary = XLSX.utils.aoa_to_sheet(summaryData);
  wsSummary['!cols'] = [{ wch: 38 }, { wch: 60 }];
  XLSX.utils.book_append_sheet(wb, wsSummary, "Executive Summary");

  // 3. Complete Challan Register Sheet
  const registerData: any[] = [
    [
      "S.No",
      "Fund Type",
      "Est. Name",
      "Est. ID / Code",
      "Wage Month",
      "Statutory Due Date",
      "Payment Date",
      "TRRN / Challan Ref",
      "Employee Share (Rs.)",
      "Employer Share (Rs.)",
      "Admin Charges (Rs.)",
      "Total Challan (Rs.)",
      "Compliance Status",
      "Delay (Days)",
      "36(1)(va) Disallowance (Rs.)",
      "Source Document"
    ]
  ];

  records.forEach((rec, idx) => {
    registerData.push([
      idx + 1,
      rec.fundType,
      rec.establishmentName,
      rec.establishmentId,
      rec.wageMonth,
      rec.statutoryDueDate,
      rec.actualPaymentDate,
      rec.challanReference,
      rec.employeeContribution,
      rec.employerContribution,
      rec.adminOtherCharges,
      rec.totalChallanAmount,
      rec.status === 'ON_TIME' ? 'Complied On Time' : 'Delayed (Disallowable)',
      rec.delayDays,
      rec.disallowableAmount,
      rec.fileName || 'Digitized Upload'
    ]);
  });

  const wsRegister = XLSX.utils.aoa_to_sheet(registerData);
  wsRegister['!cols'] = [
    { wch: 6 },  // S No
    { wch: 10 }, // Fund Type
    { wch: 30 }, // Est Name
    { wch: 20 }, // Est ID
    { wch: 16 }, // Wage Month
    { wch: 14 }, // Due Date
    { wch: 14 }, // Pay Date
    { wch: 18 }, // TRRN
    { wch: 18 }, // EE Share
    { wch: 18 }, // ER Share
    { wch: 16 }, // Admin
    { wch: 18 }, // Total
    { wch: 22 }, // Status
    { wch: 12 }, // Delay
    { wch: 24 }, // Disallowed
    { wch: 25 }, // File
  ];
  XLSX.utils.book_append_sheet(wb, wsRegister, "Full Challan Register");

  // Trigger download
  const cleanAssesseeName = (assessee.name || "Assessee").replace(/[^a-zA-Z0-9]/g, "_");
  const fileName = `Form_3CD_Clause_20b_Tax_Audit_${cleanAssesseeName}_AY_${assessee.assessmentYear.replace('/', '_')}.xlsx`;
  XLSX.writeFile(wb, fileName);
}
