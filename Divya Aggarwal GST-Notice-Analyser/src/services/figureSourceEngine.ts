import { FigureSourceDetail } from '../types';

export function identifyDepartmentFigureSource(
  allegation: string,
  title: string,
  amount: number,
  hasGstr2b = true,
  hasGstr1 = true,
  hasEwb = true,
  hasGstr9c = true
): FigureSourceDetail {
  const query = (allegation + ' ' + title).toLowerCase();

  if (query.includes('itc') || query.includes('2b') || query.includes('2a') || query.includes('3b') || query.includes('16(2)')) {
    return {
      issueTitle: title || 'ITC Discrepancy (2B vs 3B)',
      disputedAmount: amount,
      departmentSource: 'GSTR-2B Auto-populated Eligible ITC vs GSTR-3B Table 4(A)(5) Claimed ITC',
      portalTableReference: 'GSTR-2B Table 3 (ITC Available) matched against GSTR-3B Table 4(A)(5)',
      requiredPortalReport: 'GSTR-2B Monthly Excel / JSON Detailed Supplier Invoice Statement',
      verificationStep: 'Filter GSTR-2B by supplier GSTIN and match invoice date vs GSTR-3B claim month. Check supplier filing dates for quarterly filers.',
      isReportAvailable: hasGstr2b,
      missingReportAction: 'Download GSTR-2B Excel report from GST Portal for the disputed financial year.',
      suggestedPortalPath: 'GST Portal > Services > Returns > Returns Dashboard > Select FY and Period > Auto-drafted ITC Statement GSTR-2B > Download Excel',
    };
  }

  if (query.includes('rcm') || query.includes('reverse charge') || query.includes('freight') || query.includes('gta') || query.includes('legal') || query.includes('9(3)')) {
    return {
      issueTitle: title || 'RCM Tax Liability Discrepancy',
      disputedAmount: amount,
      departmentSource: 'Audited P and L Schedules (Freight and Legal Fees) vs GSTR-3B Table 3.1(d)',
      portalTableReference: 'GSTR-2B Table 3(B) Inward Supplies Attracting Reverse Charge vs GSTR-3B Table 3.1(d)',
      requiredPortalReport: 'GSTR-2B Table 3(B) RCM Inward Supplies and Trial Balance P and L Schedules',
      verificationStep: 'Verify if GTA transporters billed under 12% Forward Charge (with invoice declaration) or 5% RCM. Verify advocate payment vouchers.',
      isReportAvailable: hasGstr1,
      missingReportAction: 'Request GTA Transporter Consignment Notes and 12% Forward Charge Declarations from client.',
      suggestedPortalPath: 'Books of Accounts > P and L Schedule > Ledgers: Freight and Transport, Legal and Professional Charges',
    };
  }

  if (query.includes('turnover') || query.includes('outward') || query.includes('e-way') || query.includes('eway') || query.includes('sales')) {
    return {
      issueTitle: title || 'Outward Turnover and E-Way Bill Mismatch',
      disputedAmount: amount,
      departmentSource: 'E-Way Bill System Consolidated Generation Summary vs GSTR-1 Table 4/9 vs GSTR-3B Table 3.1(a)',
      portalTableReference: 'EWB-01 System Outward Sales Value matched against GSTR-1 Table 4 and GSTR-3B Table 3.1(a)',
      requiredPortalReport: 'E-Way Bill Outward Consolidated Summary and GSTR-1 Filed Return Excel Report',
      verificationStep: 'Isolate non-supply movements (job work, branch transfers, sales returns) from actual outward sales turnover.',
      isReportAvailable: hasEwb,
      missingReportAction: 'Download Consolidated Outward E-Way Bill Report from E-Way Bill Portal (ewaybillgst.gov.in).',
      suggestedPortalPath: 'E-Way Bill Portal > Reports > My EWB Reports > Outward Supplies Consolidated Report',
    };
  }

  if (query.includes('blocked') || query.includes('17(5)') || query.includes('vehicle') || query.includes('car') || query.includes('catering') || query.includes('club')) {
    return {
      issueTitle: title || 'Blocked Credit Under Section 17(5)',
      disputedAmount: amount,
      departmentSource: 'GSTR-2B Auto-populated HSN Codes (HSN 8703 Passenger Vehicles, 9963 Catering) vs GSTR-3B Table 4(D)(1)',
      portalTableReference: 'GSTR-2B Table 4 Ineligible ITC vs GSTR-3B Table 4(D)(1) Blocked ITC Reporting',
      requiredPortalReport: 'GSTR-2B HSN-wise Inward Supply Summary and Fixed Assets Additions Invoices',
      verificationStep: 'Check vehicle seating capacity and commercial registration (Goods Carriage vs Passenger Car). Verify if catering was mandatory under Factories Act.',
      isReportAvailable: hasGstr2b,
      missingReportAction: 'Obtain Vehicle Registration Smart Card (RC Book) and Dealer Tax Invoice.',
      suggestedPortalPath: 'Fixed Assets Register > Motor Vehicle / Delivery Van Tax Invoice and RC Book',
    };
  }

  return {
    issueTitle: title || 'Statutory Tax Discrepancy',
    disputedAmount: amount,
    departmentSource: 'Annual Return GSTR-9 / GSTR-9C Reconciliation Statement vs Monthly GSTR-3B Summary Returns',
    portalTableReference: 'GSTR-9 Table 4 and Table 7 vs DRC-01 Demand Notice',
    requiredPortalReport: 'GSTR-9 and GSTR-9C Filed Portal Copies with CA Certification',
    verificationStep: 'Compare Table 9 tax payable vs actual tax paid through Electronic Cash and Credit Ledgers.',
    isReportAvailable: hasGstr9c,
    missingReportAction: 'Download Filed GSTR-9 Annual Return and GSTR-9C Reconciliation Statement from GST Portal.',
    suggestedPortalPath: 'GST Portal > Services > Returns > Annual Return > GSTR-9 and GSTR-9C',
  };
}
