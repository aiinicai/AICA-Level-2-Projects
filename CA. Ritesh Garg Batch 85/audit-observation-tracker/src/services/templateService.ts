import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';
import { 
  AuditType, 
  AuditChecklistItem, 
  ParsedChecklistRow, 
  ParsedEngagementRow, 
  Engagement, 
  SeverityLevel, 
  EngagementStatus 
} from '../types/audit';

export class TemplateService {
  /**
   * Generates and downloads the official Sample Excel Template for Audit Checklists
   */
  public static downloadChecklistSampleTemplate(auditTypes: AuditType[]) {
    const wb = XLSX.utils.book_new();

    // Sample checklist items covering Indian CA audit domains
    const sampleRows = [
      {
        'Audit Type Code *': 'SA',
        'Audit Type Name': 'Stock Audit',
        'Category *': 'Physical Verification of Inventory',
        'Item No': '1.1',
        'Check Point / Audit Procedure *': 'Conduct physical test check count of high-value raw materials and finished goods contributing to 80% inventory valuation.',
        'Verification Guidance / Procedure': 'Match physical count sheets with ERP/Tally stock registers on cut-off date. Note differences and physical damages.',
        'Statutory / Regulatory Reference': 'CARO 2020 Cl. 3(ii)(a) / SA 501',
        'Risk Level (Critical/High/Medium/Low) *': 'High',
        'Mandatory (Yes/No)': 'Yes',
      },
      {
        'Audit Type Code *': 'SA',
        'Audit Type Name': 'Stock Audit',
        'Category *': 'Drawing Power & Bank Security',
        'Item No': '1.2',
        'Check Point / Audit Procedure *': 'Verify Drawing Power (DP) computation: Ensure exclusion of unpaid stocks (sundry creditors) and obsolete stocks (>90 days).',
        'Verification Guidance / Procedure': 'Obtain stock statement submitted to consortium bank and recompute DP applying stipulated margin (e.g. 25%).',
        'Statutory / Regulatory Reference': 'RBI Master Circular on Working Capital / DP Norms',
        'Risk Level (Critical/High/Medium/Low) *': 'Critical',
        'Mandatory (Yes/No)': 'Yes',
      },
      {
        'Audit Type Code *': 'SA',
        'Audit Type Name': 'Stock Audit',
        'Category *': 'Insurance & Warehouse Security',
        'Item No': '1.3',
        'Check Point / Audit Procedure *': 'Check insurance policy validity, coverage amount vs peak stock value, and bank hypothecation clause endorsement.',
        'Verification Guidance / Procedure': 'Verify reinstatement value clause, earthquake/STFI perils, and location endorsement matches actual godowns.',
        'Statutory / Regulatory Reference': 'Bank Sanction Terms / Hypothecation Agreement',
        'Risk Level (Critical/High/Medium/Low) *': 'High',
        'Mandatory (Yes/No)': 'Yes',
      },
      {
        'Audit Type Code *': 'TA',
        'Audit Type Name': 'Tax Audit',
        'Category *': 'Clause 22 / MSME Compliance',
        'Item No': '2.1',
        'Check Point / Audit Procedure *': 'Verify compliance with Section 43B(h) of Income Tax Act for payments to registered Micro & Small Enterprises (MSEs).',
        'Verification Guidance / Procedure': 'Review aged creditors >45 days (or written agreement term). Verify Udyam registration certificates and interest calculation.',
        'Statutory / Regulatory Reference': 'Section 43B(h) / MSMED Act 2006 / Form 3CD Cl. 22',
        'Risk Level (Critical/High/Medium/Low) *': 'Critical',
        'Mandatory (Yes/No)': 'Yes',
      },
      {
        'Audit Type Code *': 'TA',
        'Audit Type Name': 'Tax Audit',
        'Category *': 'Clause 21 / TDS Defaults',
        'Item No': '2.2',
        'Check Point / Audit Procedure *': 'Verify TDS/TCS deduction & timely deposit on contractor payments, professional fees, and contractual provisions.',
        'Verification Guidance / Procedure': 'Check Form 26AS reconciliation, challan deposit dates before due date of filing return under Section 139(1).',
        'Statutory / Regulatory Reference': 'Section 40(a)(ia) / Form 3CD Cl. 21(b)',
        'Risk Level (Critical/High/Medium/Low) *': 'High',
        'Mandatory (Yes/No)': 'Yes',
      },
      {
        'Audit Type Code *': 'CAG',
        'Audit Type Name': 'CAG Audit',
        'Category *': 'Public Procurement & GeM Compliance',
        'Item No': '3.1',
        'Check Point / Audit Procedure *': 'Verify mandatory procurement of goods and services via Government e-Marketplace (GeM) and tender threshold compliance.',
        'Verification Guidance / Procedure': 'Check Non-Availability Certificate (NAC) where procurement was done outside GeM portal. Verify purchase committee approvals.',
        'Statutory / Regulatory Reference': 'GFR 2017 Rule 149 / CVC Guidelines',
        'Risk Level (Critical/High/Medium/Low) *': 'Critical',
        'Mandatory (Yes/No)': 'Yes',
      },
      {
        'Audit Type Code *': 'CA',
        'Audit Type Name': 'Concurrent Audit',
        'Category *': 'Loan Sanction & Pre-Disbursement',
        'Item No': '4.1',
        'Check Point / Audit Procedure *': 'Verify compliance with sanction terms, title deeds verification report (TDVR), CIBIL check, and security creation.',
        'Verification Guidance / Procedure': 'Check loan docket for ROC charge registration (Form CHG-1) within 30 days of mortgage creation.',
        'Statutory / Regulatory Reference': 'RBI Master Directions on Credit Management / SARFAESI',
        'Risk Level (Critical/High/Medium/Low) *': 'Critical',
        'Mandatory (Yes/No)': 'Yes',
      },
    ];

    const wsChecklist = XLSX.utils.json_to_sheet(sampleRows);

    // Auto-fit column widths
    wsChecklist['!cols'] = [
      { wch: 18 }, // Audit Type Code
      { wch: 20 }, // Audit Type Name
      { wch: 32 }, // Category
      { wch: 10 }, // Item No
      { wch: 60 }, // Check Point
      { wch: 60 }, // Verification Guidance
      { wch: 35 }, // Statutory Reference
      { wch: 20 }, // Risk Level
      { wch: 16 }, // Mandatory
    ];

    XLSX.utils.book_append_sheet(wb, wsChecklist, 'Checklist_Template');

    // Instructions Sheet
    const instructionsData = [
      { 'Instruction Field': 'Instructions for Excel Checklist Template Upload', 'Details / Permitted Values': '' },
      { 'Instruction Field': 'Audit Type Code *', 'Details / Permitted Values': 'Use the exact Code of the audit type (e.g. SA, TA, CAG, CA, or custom code configured in Settings).' },
      { 'Instruction Field': 'Category *', 'Details / Permitted Values': 'Process/Area (e.g., Physical Verification, MSME Compliance, Loan Disbursement, IFC).' },
      { 'Instruction Field': 'Item No', 'Details / Permitted Values': 'Optional sequence identifier e.g. 1.1, 1.2, CL-01.' },
      { 'Instruction Field': 'Check Point / Audit Procedure *', 'Details / Permitted Values': 'Required audit test question or procedure that the audit team will verify.' },
      { 'Instruction Field': 'Verification Guidance', 'Details / Permitted Values': 'Detailed instructions, sampling size, or checking guidelines for the audit staff.' },
      { 'Instruction Field': 'Statutory / Regulatory Reference', 'Details / Permitted Values': 'Relevant law clause (e.g. CARO 2020 Cl 3, Sec 43B(h), GFR 2017, RBI IRAC).' },
      { 'Instruction Field': 'Risk Level *', 'Details / Permitted Values': 'Must be one of: Critical, High, Medium, Low.' },
      { 'Instruction Field': 'Mandatory', 'Details / Permitted Values': 'Yes or No (defaults to Yes if empty).' },
      { 'Instruction Field': '---', 'Details / Permitted Values': '---' },
      { 'Instruction Field': 'Available Audit Types in your System:', 'Details / Permitted Values': auditTypes.map(at => `${at.code}: ${at.name}`).join(' | ') },
    ];

    const wsInstructions = XLSX.utils.json_to_sheet(instructionsData);
    wsInstructions['!cols'] = [{ wch: 35 }, { wch: 70 }];
    XLSX.utils.book_append_sheet(wb, wsInstructions, 'Instructions_Guide');

    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    saveAs(blob, 'Audit_Checklist_Template_Sample.xlsx');
  }

  /**
   * Generates and downloads the official Sample Excel Template for Bulk Audit Assignments
   */
  public static downloadAssignmentsSampleTemplate(auditTypes: AuditType[]) {
    const wb = XLSX.utils.book_new();

    const sampleAssignments = [
      {
        'Client Name *': 'Tata Steel Limited (West Bokaro Division)',
        'Client Code *': 'TSL',
        'Audit Type (Code or Name) *': 'Stock Audit',
        'Financial Year (e.g. 2024-25) *': '2024-25',
        'PAN / GSTIN': '20AAACT2727Q1ZT',
        'Engagement Partner': 'CA Ritesh Garg, FCA',
        'Team Members': 'Ankit Sharma (Senior), Priya Verma (Article)',
        'Start Date (YYYY-MM-DD)': '2024-10-01',
        'End Date (YYYY-MM-DD)': '2024-10-25',
        'Branch / Location': 'Jamshedpur Central Stockyard & Works',
        'Status (Planning/In Progress/Fieldwork Complete/Report Issued/Closed)': 'In Progress',
        'Notes / Audit Scope': 'Quarterly consortium stock & book debt verification mandated by lead bank SBI.',
      },
      {
        'Client Name *': 'Bharat Electronics & Logistics Private Limited',
        'Client Code *': 'BEL',
        'Audit Type (Code or Name) *': 'Tax Audit',
        'Financial Year (e.g. 2024-25) *': '2024-25',
        'PAN / GSTIN': '07AABCB9876K1Z3',
        'Engagement Partner': 'CA Ritesh Garg, FCA',
        'Team Members': 'Rohit Gupta (Article), Sneha Patel',
        'Start Date (YYYY-MM-DD)': '2024-09-01',
        'End Date (YYYY-MM-DD)': '2024-09-30',
        'Branch / Location': 'Head Office & Okhla Warehouse, New Delhi',
        'Status (Planning/In Progress/Fieldwork Complete/Report Issued/Closed)': 'Fieldwork Complete',
        'Notes / Audit Scope': 'Form 3CD tax audit with special focus on Section 43B(h) MSME overdue payments.',
      },
      {
        'Client Name *': 'Northern Coalfields Power Transmission Ltd (PSU)',
        'Client Code *': 'NCP',
        'Audit Type (Code or Name) *': 'CAG Audit',
        'Financial Year (e.g. 2024-25) *': '2024-25',
        'PAN / GSTIN': '08AAACN4432M1ZA',
        'Engagement Partner': 'CA Ritesh Garg, FCA',
        'Team Members': 'Vikas Malhotra (Manager), Ankit Sharma',
        'Start Date (YYYY-MM-DD)': '2024-11-01',
        'End Date (YYYY-MM-DD)': '2024-11-20',
        'Branch / Location': 'Singrauli Thermal Power Project',
        'Status (Planning/In Progress/Fieldwork Complete/Report Issued/Closed)': 'Planning',
        'Notes / Audit Scope': 'Propriety & compliance audit as per CAG supplementary audit guidelines & GeM rules.',
      },
      {
        'Client Name *': 'State Bank of India - Mid Corporate Branch',
        'Client Code *': 'SBI',
        'Audit Type (Code or Name) *': 'Concurrent Audit',
        'Financial Year (e.g. 2024-25) *': '2024-25',
        'PAN / GSTIN': '07AAACS0414L1Z2',
        'Engagement Partner': 'CA Ritesh Garg, FCA',
        'Team Members': 'Rajesh Kumar, Priya Verma',
        'Start Date (YYYY-MM-DD)': '2024-10-01',
        'End Date (YYYY-MM-DD)': '2025-03-31',
        'Branch / Location': 'Parliament Street, New Delhi',
        'Status (Planning/In Progress/Fieldwork Complete/Report Issued/Closed)': 'In Progress',
        'Notes / Audit Scope': 'Monthly concurrent audit covering high-value credit sanction, KYC/AML, and revenue leakage.',
      },
    ];

    const wsAssignments = XLSX.utils.json_to_sheet(sampleAssignments);

    wsAssignments['!cols'] = [
      { wch: 38 }, // Client Name
      { wch: 14 }, // Client Code
      { wch: 24 }, // Audit Type
      { wch: 18 }, // Financial Year
      { wch: 20 }, // PAN / GSTIN
      { wch: 24 }, // Partner
      { wch: 36 }, // Team Members
      { wch: 16 }, // Start Date
      { wch: 16 }, // End Date
      { wch: 32 }, // Branch / Location
      { wch: 22 }, // Status
      { wch: 50 }, // Notes
    ];

    XLSX.utils.book_append_sheet(wb, wsAssignments, 'Audit_Assignments');

    // Reference Sheet
    const refData = [
      { 'Field': 'Available Audit Types', 'Accepted Codes & Names': auditTypes.map(at => `${at.code} (${at.name})`).join(', ') },
      { 'Field': 'Valid Engagement Statuses', 'Accepted Codes & Names': 'Planning, In Progress, Fieldwork Complete, Report Issued, Closed' },
      { 'Field': 'Financial Year Format', 'Accepted Codes & Names': '2024-25, 2025-26 (YYYY-YY)' },
      { 'Field': 'Date Format', 'Accepted Codes & Names': 'YYYY-MM-DD (e.g. 2024-10-15) or standard Excel Date' },
      { 'Field': 'Client Code', 'Accepted Codes & Names': '3 to 6 letter alphanumeric code (used in Observation Reference numbering, e.g. TSL, SBI, BEL)' },
    ];

    const wsRef = XLSX.utils.json_to_sheet(refData);
    wsRef['!cols'] = [{ wch: 28 }, { wch: 70 }];
    XLSX.utils.book_append_sheet(wb, wsRef, 'Reference_Guide');

    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    saveAs(blob, 'Bulk_Audit_Assignments_Template.xlsx');
  }

  /**
   * Helper to normalize Excel header strings
   */
  private static cleanKey(key: string): string {
    return key.toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  /**
   * Helper to format dates from Excel
   */
  private static parseDateValue(val: any): string {
    if (!val) return new Date().toISOString().split('T')[0];
    if (val instanceof Date) {
      return val.toISOString().split('T')[0];
    }
    if (typeof val === 'number') {
      // Excel serial date format
      const date = new Date((val - (25567 + 2)) * 86400 * 1000);
      if (!isNaN(date.getTime())) {
        return date.toISOString().split('T')[0];
      }
    }
    const str = String(val).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) return str;
    if (/^\d{2}[/-]\d{2}[/-]\d{4}$/.test(str)) {
      const parts = str.split(/[/-]/);
      return `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
    }
    return new Date().toISOString().split('T')[0];
  }

  /**
   * Parses uploaded Excel file for Checklist Items
   */
  public static async parseChecklistExcel(
    file: File,
    auditTypes: AuditType[]
  ): Promise<{
    validItems: AuditChecklistItem[];
    parsedRows: ParsedChecklistRow[];
    totalRows: number;
    errors: string[];
  }> {
    const data = await file.arrayBuffer();
    const workbook = XLSX.read(data, { type: 'array', cellDates: true });
    
    // Grab first sheet or sheet containing 'checklist'
    const sheetName = workbook.SheetNames.find(n => n.toLowerCase().includes('checklist')) || workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];

    if (!sheet) {
      throw new Error('No valid worksheet found in the uploaded workbook.');
    }

    const rawRows = XLSX.utils.sheet_to_json<Record<string, any>>(sheet, { defval: '' });
    const parsedRows: ParsedChecklistRow[] = [];
    const validItems: AuditChecklistItem[] = [];
    const errors: string[] = [];

    // Build lookup maps for Audit Types
    const typeCodeMap = new Map<string, AuditType>();
    const typeNameMap = new Map<string, AuditType>();
    auditTypes.forEach(at => {
      typeCodeMap.set(at.code.trim().toUpperCase(), at);
      typeNameMap.set(at.name.trim().toLowerCase(), at);
    });

    rawRows.forEach((row, idx) => {
      // Extract values with flexible column key matches
      let codeVal = '';
      let nameVal = '';
      let categoryVal = '';
      let itemNoVal = '';
      let checkPointVal = '';
      let guidanceVal = '';
      let refVal = '';
      let riskVal = '';
      let mandatoryVal = '';

      Object.entries(row).forEach(([rawKey, val]) => {
        const k = TemplateService.cleanKey(rawKey);
        const strVal = String(val).trim();

        if (k.includes('code') && !k.includes('ref')) codeVal = strVal;
        else if (k.includes('type') || k.includes('name') && !k.includes('client')) nameVal = strVal;
        else if (k.includes('category') || k.includes('area') || k.includes('process')) categoryVal = strVal;
        else if (k.includes('itemno') || k.includes('item') || k.includes('seq') || k.includes('clauseno')) itemNoVal = strVal;
        else if (k.includes('checkpoint') || k.includes('procedure') || k.includes('question') || k.includes('test') || k.includes('requirement')) checkPointVal = strVal;
        else if (k.includes('guidance') || k.includes('instruction') || k.includes('method')) guidanceVal = strVal;
        else if (k.includes('reference') || k.includes('statutory') || k.includes('clause') || k.includes('section') || k.includes('caro')) refVal = strVal;
        else if (k.includes('risk') || k.includes('severity')) riskVal = strVal;
        else if (k.includes('mandatory') || k.includes('required') || k.includes('compulsory')) mandatoryVal = strVal;
      });

      // Also fallback if checkPointVal is still empty and any non-empty column exists
      if (!checkPointVal) {
        const textCandidates = Object.values(row).map(v => String(v).trim()).filter(v => v.length > 15);
        if (textCandidates.length > 0) checkPointVal = textCandidates[0];
      }

      if (!checkPointVal && !categoryVal && !codeVal) {
        // Skip empty row
        return;
      }

      let rowErrors: string[] = [];

      // Validate checkPoint
      if (!checkPointVal) {
        rowErrors.push('Check Point / Audit Procedure is required');
      }

      // Match Audit Type
      let matchedType: AuditType | undefined;
      if (codeVal) {
        matchedType = typeCodeMap.get(codeVal.toUpperCase());
      }
      if (!matchedType && nameVal) {
        matchedType = typeNameMap.get(nameVal.toLowerCase());
      }
      if (!matchedType && auditTypes.length > 0) {
        // Default to first audit type if not specified
        matchedType = auditTypes[0];
      }

      const auditTypeId = matchedType ? matchedType.id : (auditTypes[0]?.id || 'SA');
      const finalTypeCode = matchedType ? matchedType.code : (codeVal || 'SA');

      // Normalize Risk Level
      let severity: SeverityLevel = 'High';
      const rLower = riskVal.toLowerCase();
      if (rLower.includes('crit')) severity = 'Critical';
      else if (rLower.includes('high')) severity = 'High';
      else if (rLower.includes('med')) severity = 'Medium';
      else if (rLower.includes('low')) severity = 'Low';

      // Normalize Mandatory
      const isMandatory = !mandatoryVal || mandatoryVal.toLowerCase().startsWith('y') || mandatoryVal.toLowerCase() === '1' || mandatoryVal.toLowerCase() === 'true';

      const isValid = rowErrors.length === 0;

      const parsedRow: ParsedChecklistRow = {
        auditTypeCode: finalTypeCode,
        auditTypeName: matchedType?.name,
        category: categoryVal || 'General Audit Verification',
        itemNumber: itemNoVal || `CL-${idx + 1}`,
        checkPoint: checkPointVal,
        procedureGuidance: guidanceVal,
        statutoryReference: refVal,
        riskLevel: severity,
        isMandatory,
        isValid,
        validationError: rowErrors.join('; '),
      };

      parsedRows.push(parsedRow);

      if (isValid) {
        validItems.push({
          id: `CHK-${Date.now()}-${Math.floor(Math.random() * 100000)}`,
          auditTypeId,
          category: parsedRow.category,
          itemNumber: parsedRow.itemNumber,
          checkPoint: parsedRow.checkPoint,
          procedureGuidance: parsedRow.procedureGuidance,
          statutoryReference: parsedRow.statutoryReference,
          riskLevel: parsedRow.riskLevel,
          isMandatory: parsedRow.isMandatory,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        });
      } else {
        errors.push(`Row ${idx + 2}: ${rowErrors.join(', ')}`);
      }
    });

    return {
      validItems,
      parsedRows,
      totalRows: parsedRows.length,
      errors,
    };
  }

  /**
   * Parses uploaded Excel file for Bulk Audit Assignments
   */
  public static async parseAssignmentsExcel(
    file: File,
    auditTypes: AuditType[],
    defaultPartner = 'CA Ritesh Garg, FCA'
  ): Promise<{
    validEngagements: Engagement[];
    parsedRows: ParsedEngagementRow[];
    totalRows: number;
    errors: string[];
  }> {
    const data = await file.arrayBuffer();
    const workbook = XLSX.read(data, { type: 'array', cellDates: true });
    
    // Find assignments sheet
    const sheetName = workbook.SheetNames.find(n => n.toLowerCase().includes('assignment') || n.toLowerCase().includes('engagement')) || workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];

    if (!sheet) {
      throw new Error('No valid worksheet found in the uploaded workbook.');
    }

    const rawRows = XLSX.utils.sheet_to_json<Record<string, any>>(sheet, { defval: '' });
    const parsedRows: ParsedEngagementRow[] = [];
    const validEngagements: Engagement[] = [];
    const errors: string[] = [];

    // Build lookup maps for Audit Types
    const typeCodeMap = new Map<string, AuditType>();
    const typeNameMap = new Map<string, AuditType>();
    auditTypes.forEach(at => {
      typeCodeMap.set(at.code.trim().toUpperCase(), at);
      typeNameMap.set(at.name.trim().toLowerCase(), at);
    });

    const usedClientCodes = new Set<string>();

    rawRows.forEach((row, idx) => {
      let clientName = '';
      let clientCode = '';
      let auditTypeVal = '';
      let fyVal = '';
      let panGstin = '';
      let partner = '';
      let team = '';
      let startDateVal = '';
      let endDateVal = '';
      let location = '';
      let statusVal = '';
      let notes = '';

      Object.entries(row).forEach(([rawKey, val]) => {
        const k = TemplateService.cleanKey(rawKey);
        const strVal = String(val).trim();

        if (k.includes('clientname') || k.includes('company') || k.includes('auditee') || (k.includes('name') && !k.includes('partner') && !k.includes('team'))) {
          clientName = strVal;
        } else if (k.includes('clientcode') || k.includes('shortcode') || k.includes('code') && !k.includes('audit') && !k.includes('type')) {
          clientCode = strVal;
        } else if (k.includes('audit') || k.includes('type')) {
          auditTypeVal = strVal;
        } else if (k.includes('fy') || k.includes('year') || k.includes('financial')) {
          fyVal = strVal;
        } else if (k.includes('pan') || k.includes('gst') || k.includes('gstin')) {
          panGstin = strVal;
        } else if (k.includes('partner') || k.includes('engagementpartner') || k.includes('ca')) {
          partner = strVal;
        } else if (k.includes('team') || k.includes('member') || k.includes('article') || k.includes('staff')) {
          team = strVal;
        } else if (k.includes('start') || k.includes('commence') || k.includes('from')) {
          startDateVal = TemplateService.parseDateValue(val);
        } else if (k.includes('end') || k.includes('close') || k.includes('to') || k.includes('completion')) {
          endDateVal = TemplateService.parseDateValue(val);
        } else if (k.includes('location') || k.includes('branch') || k.includes('unit') || k.includes('plant') || k.includes('city')) {
          location = strVal;
        } else if (k.includes('status') || k.includes('stage')) {
          statusVal = strVal;
        } else if (k.includes('note') || k.includes('scope') || k.includes('remark') || k.includes('description')) {
          notes = strVal;
        }
      });

      if (!clientName && !clientCode && !auditTypeVal) {
        // Skip empty row
        return;
      }

      let rowErrors: string[] = [];

      // Validate Client Name
      if (!clientName) {
        rowErrors.push('Client Name is required');
      }

      // Auto-generate client code if missing
      if (!clientCode && clientName) {
        clientCode = clientName.replace(/[^A-Za-z0-9]/g, '').slice(0, 4).toUpperCase() || 'CLI';
      }
      clientCode = clientCode.toUpperCase();

      // Normalize Audit Type
      let matchedType: AuditType | undefined;
      if (auditTypeVal) {
        matchedType = typeCodeMap.get(auditTypeVal.toUpperCase()) || typeNameMap.get(auditTypeVal.toLowerCase());
      }
      if (!matchedType) {
        // Match partial
        matchedType = auditTypes.find(at => 
          auditTypeVal.toLowerCase().includes(at.code.toLowerCase()) || 
          at.name.toLowerCase().includes(auditTypeVal.toLowerCase())
        );
      }
      if (!matchedType && auditTypes.length > 0) {
        matchedType = auditTypes[0]; // fallback
      }

      // Normalize Financial Year
      let finalFY = fyVal || '2024-25';
      if (/^\d{4}$/.test(finalFY)) {
        const yr = parseInt(finalFY, 10);
        finalFY = `${yr}-${String(yr + 1).slice(2)}`;
      }

      // Normalize Status
      let finalStatus: EngagementStatus = 'Planning';
      const sLower = statusVal.toLowerCase();
      if (sLower.includes('progress')) finalStatus = 'In Progress';
      else if (sLower.includes('fieldwork') || sLower.includes('complete')) finalStatus = 'Fieldwork Complete';
      else if (sLower.includes('report') || sLower.includes('issued')) finalStatus = 'Report Issued';
      else if (sLower.includes('close')) finalStatus = 'Closed';
      else if (sLower.includes('plan')) finalStatus = 'Planning';

      // Team members array
      const teamArray = team
        ? team.split(/[,;\n]/).map(s => s.trim()).filter(Boolean)
        : [];

      const isValid = rowErrors.length === 0;

      const parsedRow: ParsedEngagementRow = {
        clientName,
        clientCode,
        auditTypeCodeOrName: auditTypeVal || matchedType?.code || 'SA',
        financialYear: finalFY,
        clientPanGstin: panGstin,
        engagementPartner: partner || defaultPartner,
        teamMembers: team,
        startDate: startDateVal || new Date().toISOString().split('T')[0],
        endDate: endDateVal || new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
        branchLocation: location,
        overallStatus: finalStatus,
        notes,
        isValid,
        validationError: rowErrors.join('; '),
        matchedAuditTypeId: matchedType?.id,
        matchedAuditTypeName: matchedType?.name,
      };

      parsedRows.push(parsedRow);

      if (isValid) {
        const engId = `ENG-${finalFY.slice(0, 4)}-${String(idx + 101).padStart(3, '0')}`;
        validEngagements.push({
          id: engId,
          clientName: parsedRow.clientName,
          clientCode: parsedRow.clientCode,
          auditTypeId: matchedType ? matchedType.id : (auditTypes[0]?.id || 'SA'),
          financialYear: parsedRow.financialYear,
          clientPanGstin: parsedRow.clientPanGstin,
          engagementPartner: parsedRow.engagementPartner || defaultPartner,
          teamMembers: teamArray,
          startDate: parsedRow.startDate || new Date().toISOString().split('T')[0],
          endDate: parsedRow.endDate || new Date().toISOString().split('T')[0],
          branchLocation: parsedRow.branchLocation,
          overallStatus: parsedRow.overallStatus,
          notes: parsedRow.notes,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        });
      } else {
        errors.push(`Row ${idx + 2}: ${rowErrors.join(', ')}`);
      }
    });

    return {
      validEngagements,
      parsedRows,
      totalRows: parsedRows.length,
      errors,
    };
  }

  /**
   * Exports active checklists to an Excel file
   */
  public static exportChecklistsToExcel(
    items: AuditChecklistItem[],
    auditTypes: AuditType[]
  ) {
    const auditTypeMap = new Map<string, AuditType>(auditTypes.map(at => [at.id, at]));

    const exportRows = items.map(item => {
      const at = auditTypeMap.get(item.auditTypeId);
      return {
        'Audit Type Code': at?.code || 'SA',
        'Audit Type Name': at?.name || 'Audit',
        'Category': item.category,
        'Item No': item.itemNumber || '',
        'Check Point / Audit Procedure': item.checkPoint,
        'Verification Guidance / Procedure': item.procedureGuidance || '',
        'Statutory / Regulatory Reference': item.statutoryReference || '',
        'Risk Level': item.riskLevel,
        'Mandatory': item.isMandatory ? 'Yes' : 'No',
      };
    });

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(exportRows);

    ws['!cols'] = [
      { wch: 18 },
      { wch: 22 },
      { wch: 32 },
      { wch: 10 },
      { wch: 60 },
      { wch: 60 },
      { wch: 35 },
      { wch: 16 },
      { wch: 12 },
    ];

    XLSX.utils.book_append_sheet(wb, ws, 'Audit_Checklists');

    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    saveAs(blob, `CA_Audit_Checklists_Master_${new Date().toISOString().split('T')[0]}.xlsx`);
  }
}
