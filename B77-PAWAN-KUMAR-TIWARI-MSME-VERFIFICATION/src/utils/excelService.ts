import * as XLSX from 'xlsx';
import { Vendor, Invoice, RateMasterEntry, StatutoryRuleConfig, PartPayment } from '../types';
import { calculateMSMEDueDate } from './calculator';
import { formatINR } from './formatters';

// Helper to reliably parse date from Excel (strings, timestamps, or Excel serial numbers)
export function parseExcelDate(val: any): string {
  if (!val && val !== 0) return '';
  if (typeof val === 'number') {
    // Excel serial number (days since 1899-12-30)
    const utcDays = Math.floor(val - 25569);
    const utcValue = utcDays * 86400;
    const dateInfo = new Date(utcValue * 1000);
    const yyyy = dateInfo.getUTCFullYear();
    const mm = String(dateInfo.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(dateInfo.getUTCDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  const str = String(val).trim();
  if (!str) return '';

  // Match YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
    return str;
  }

  // Match DD/MM/YYYY or DD-MM-YYYY
  const ddmmyyyy = str.match(/^(\d{1,2})[\/\.-](\d{1,2})[\/\.-](\d{4})$/);
  if (ddmmyyyy) {
    const dd = ddmmyyyy[1].padStart(2, '0');
    const mm = ddmmyyyy[2].padStart(2, '0');
    const yyyy = ddmmyyyy[3];
    return `${yyyy}-${mm}-${dd}`;
  }

  // Match YYYY/MM/DD
  const yyyymmdd = str.match(/^(\d{4})[\/\.-](\d{1,2})[\/\.-](\d{1,2})$/);
  if (yyyymmdd) {
    const yyyy = yyyymmdd[1];
    const mm = yyyymmdd[2].padStart(2, '0');
    const dd = yyyymmdd[3].padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  // Try Date object
  const parsed = new Date(str);
  if (!isNaN(parsed.getTime())) {
    return parsed.toISOString().split('T')[0];
  }

  return str;
}

// Normalized header key finder
function findColumnIndex(headers: string[], aliases: string[]): number {
  const normalizedAliases = aliases.map((a) => a.toLowerCase().replace(/[^a-z0-9]/g, ''));
  for (let i = 0; i < headers.length; i++) {
    const normHeader = String(headers[i] || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    for (const alias of normalizedAliases) {
      if (normHeader === alias || normHeader.includes(alias) || alias.includes(normHeader)) {
        return i;
      }
    }
  }
  return -1;
}

// -------------------------------------------------------------
// VENDOR EXCEL TEMPLATE & PARSER
// -------------------------------------------------------------

export function downloadVendorExcelTemplate() {
  const headers = [
    'Vendor Code',
    'Vendor Name',
    'PAN',
    'GSTIN',
    'Udyam Registration Number',
    'MSME Category (Micro/Small/Medium/Not Applicable)',
    'Major Activity (Manufacturing/Services/Trading)',
    'Udyam Registration Date (YYYY-MM-DD)',
    'Has Written Agreement (Yes/No)',
    'Agreed Credit Days (e.g. 30, 45)',
    'Contact Person',
    'Email',
    'Phone',
    'Remarks',
  ];

  const sampleData = [
    [
      'V-2001',
      'Apex Tech Industries',
      'AABCT1234F',
      '27AABCT1234F1Z8',
      'UDYAM-MH-01-0099881',
      'Micro',
      'Manufacturing',
      '2022-04-15',
      'Yes',
      '30',
      'Ramesh Kumar',
      'ramesh@apextech.in',
      '+91 98200 98765',
      'Precision fasteners and springs supplier',
    ],
    [
      'V-2002',
      'Quality Packaging Solutions',
      'AACFQ5678K',
      '24AACFQ5678K1Z3',
      'UDYAM-GJ-02-0055443',
      'Small',
      'Manufacturing',
      '2021-09-10',
      'Yes',
      '45',
      'Girish Patel',
      'girish@qualitypack.com',
      '+91 98980 12345',
      'Corrugated shipping boxes',
    ],
    [
      'V-2003',
      'National Foundry & Alloy Works',
      'AAACN9988D',
      '29AAACN9988D1Z2',
      '',
      'Not Applicable',
      'Manufacturing',
      '',
      'No',
      '60',
      'S. Kulkarni',
      'accounts@nationalfoundry.com',
      '+91 80 22334455',
      'Large enterprise raw casting supplier',
    ],
  ];

  const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleData]);
  ws['!cols'] = [
    { wch: 15 },
    { wch: 32 },
    { wch: 15 },
    { wch: 20 },
    { wch: 26 },
    { wch: 26 },
    { wch: 20 },
    { wch: 24 },
    { wch: 24 },
    { wch: 20 },
    { wch: 20 },
    { wch: 25 },
    { wch: 18 },
    { wch: 35 },
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Vendor_Master_Template');
  XLSX.writeFile(wb, 'MSME_Vendor_Master_Template.xlsx');
}

export function getDemoVendorExcelRows(): Partial<Vendor>[] {
  return [
    {
      id: `VEND-DEMO-${Date.now()}-1`,
      vendorCode: 'V-3001',
      vendorName: 'Mahalaxmi Micro Gears & Spares',
      pan: 'AAECM4455G',
      gstin: '27AAECM4455G1ZX',
      udyamNumber: 'UDYAM-MH-01-0087654',
      isMSME: true,
      msmeStatus: 'MSME',
      msmeCategory: 'Micro',
      majorActivity: 'Manufacturing',
      udyamRegistrationDate: '2023-01-15',
      verificationDate: '',
      verificationStatus: 'Pending',
      hasWrittenAgreement: true,
      agreedCreditDays: 30,
      contactPerson: 'Suresh Patil',
      email: 'spatil@mahalaxmigears.in',
      phone: '+91 98220 54321',
      remarks: 'Automotive pinion and spur gears supplier (Imported via Demo Excel)',
      verificationHistory: [],
      createdDate: new Date().toISOString().split('T')[0],
      updatedDate: new Date().toISOString().split('T')[0],
    },
    {
      id: `VEND-DEMO-${Date.now()}-2`,
      vendorCode: 'V-3002',
      vendorName: 'Zenith Electro-Plating Works',
      pan: 'AABCZ9921K',
      gstin: '24AABCZ9921K1Z5',
      udyamNumber: 'UDYAM-GJ-03-0044332',
      isMSME: true,
      msmeStatus: 'MSME',
      msmeCategory: 'Small',
      majorActivity: 'Services',
      udyamRegistrationDate: '2022-08-20',
      verificationDate: '',
      verificationStatus: 'Pending',
      hasWrittenAgreement: true,
      agreedCreditDays: 45,
      contactPerson: 'Ketan Shah',
      email: 'kshah@zenithplating.com',
      phone: '+91 98790 99887',
      remarks: 'Zinc nickel plating and surface treatment service provider',
      verificationHistory: [],
      createdDate: new Date().toISOString().split('T')[0],
      updatedDate: new Date().toISOString().split('T')[0],
    },
    {
      id: `VEND-DEMO-${Date.now()}-3`,
      vendorCode: 'V-3003',
      vendorName: 'Bharat Fasteners & Rivets',
      pan: 'AABCB1122D',
      gstin: '29AABCB1122D1Z9',
      udyamNumber: 'UDYAM-KR-04-0012345',
      isMSME: true,
      msmeStatus: 'MSME',
      msmeCategory: 'Micro',
      majorActivity: 'Manufacturing',
      udyamRegistrationDate: '2024-02-10',
      verificationDate: '',
      verificationStatus: 'Pending',
      hasWrittenAgreement: false,
      agreedCreditDays: 15,
      contactPerson: 'Anand Rao',
      email: 'anand@bharatfasteners.in',
      phone: '+91 80 44556677',
      remarks: 'Standard Grade 8.8 structural bolts and nuts',
      verificationHistory: [],
      createdDate: new Date().toISOString().split('T')[0],
      updatedDate: new Date().toISOString().split('T')[0],
    },
  ];
}

export async function parseVendorExcelFile(file: File): Promise<{
  validVendors: Partial<Vendor>[];
  errors: { row: number; reason: string }[];
}> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        const rows: any[] = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

        if (rows.length < 2) {
          return resolve({ validVendors: [], errors: [{ row: 1, reason: 'File is empty or contains only headers.' }] });
        }

        const headers = (rows[0] || []).map((h: any) => String(h || '').trim());
        const codeIdx = findColumnIndex(headers, ['vendorcode', 'code', 'vendorid']);
        const nameIdx = findColumnIndex(headers, ['vendorname', 'vendor', 'name', 'partyname', 'suppliername']);
        const panIdx = findColumnIndex(headers, ['pan', 'pannumber', 'panno']);
        const gstinIdx = findColumnIndex(headers, ['gstin', 'gstno', 'gstnumber']);
        const udyamIdx = findColumnIndex(headers, ['udyam', 'udyamnumber', 'udyamreg', 'msmeno']);
        const catIdx = findColumnIndex(headers, ['msmecategory', 'category', 'enterprisetype', 'type']);
        const actIdx = findColumnIndex(headers, ['majoractivity', 'activity', 'sector']);
        const udyamDateIdx = findColumnIndex(headers, ['udyamdate', 'udyamregdate', 'registrationdate']);
        const agrIdx = findColumnIndex(headers, ['haswrittenagreement', 'agreement', 'writtenagreement', 'contract']);
        const daysIdx = findColumnIndex(headers, ['agreedcreditdays', 'creditdays', 'paymentterms', 'days']);
        const contactIdx = findColumnIndex(headers, ['contactperson', 'contact', 'person']);
        const emailIdx = findColumnIndex(headers, ['email', 'emailid', 'mail']);
        const phoneIdx = findColumnIndex(headers, ['phone', 'mobile', 'tel', 'contactno']);
        const remarksIdx = findColumnIndex(headers, ['remarks', 'notes', 'comments', 'description']);

        const validVendors: Partial<Vendor>[] = [];
        const errors: { row: number; reason: string }[] = [];

        for (let i = 1; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length === 0 || row.every((c: any) => c === undefined || c === '')) {
            continue;
          }

          const vendorCode = String(row[codeIdx >= 0 ? codeIdx : 0] || '').trim();
          const vendorName = String(row[nameIdx >= 0 ? nameIdx : 1] || '').trim();
          const pan = String(row[panIdx >= 0 ? panIdx : 2] || '').trim().toUpperCase();
          const gstin = String(row[gstinIdx >= 0 ? gstinIdx : 3] || '').trim().toUpperCase();
          const udyamNumber = String(row[udyamIdx >= 0 ? udyamIdx : 4] || '').trim().toUpperCase();
          const rawCategory = String(row[catIdx >= 0 ? catIdx : 5] || '').trim();
          const rawActivity = String(row[actIdx >= 0 ? actIdx : 6] || 'Manufacturing').trim();
          const udyamDate = parseExcelDate(row[udyamDateIdx >= 0 ? udyamDateIdx : 7]);
          const writtenAgreementStr = String(row[agrIdx >= 0 ? agrIdx : 8] || 'Yes').trim().toLowerCase();
          const agreedDays = Number(row[daysIdx >= 0 ? daysIdx : 9]) || 30;
          const contact = String(row[contactIdx >= 0 ? contactIdx : 10] || '').trim();
          const email = String(row[emailIdx >= 0 ? emailIdx : 11] || '').trim();
          const phone = String(row[phoneIdx >= 0 ? phoneIdx : 12] || '').trim();
          const remarks = String(row[remarksIdx >= 0 ? remarksIdx : 13] || '').trim();

          if (!vendorName) {
            errors.push({ row: i + 1, reason: 'Vendor Name is mandatory.' });
            continue;
          }

          let msmeCategory: Vendor['msmeCategory'] = 'Not Applicable';
          if (rawCategory.toLowerCase().includes('micro')) msmeCategory = 'Micro';
          else if (rawCategory.toLowerCase().includes('small')) msmeCategory = 'Small';
          else if (rawCategory.toLowerCase().includes('medium')) msmeCategory = 'Medium';
          else if (udyamNumber) msmeCategory = 'Small';

          const isMSME = msmeCategory !== 'Not Applicable' || Boolean(udyamNumber);

          validVendors.push({
            id: `VEND-IMP-${Date.now()}-${i}`,
            vendorCode: vendorCode || `V-${1000 + i}`,
            vendorName,
            pan,
            gstin,
            udyamNumber,
            isMSME,
            msmeStatus: isMSME ? 'MSME' : 'Non-MSME',
            msmeCategory,
            majorActivity: rawActivity.toLowerCase().includes('service')
              ? 'Services'
              : rawActivity.toLowerCase().includes('trading')
              ? 'Trading'
              : 'Manufacturing',
            udyamRegistrationDate: udyamDate,
            verificationDate: '',
            verificationStatus: udyamNumber ? 'Pending' : 'Not Verified',
            hasWrittenAgreement:
              writtenAgreementStr === 'yes' ||
              writtenAgreementStr === 'y' ||
              writtenAgreementStr === 'true' ||
              writtenAgreementStr === '1',
            agreedCreditDays: agreedDays,
            contactPerson: contact,
            email,
            phone,
            remarks: remarks || 'Imported via Excel template',
            verificationHistory: [],
            createdDate: new Date().toISOString().split('T')[0],
            updatedDate: new Date().toISOString().split('T')[0],
          });
        }

        resolve({ validVendors, errors });
      } catch (err: any) {
        reject(new Error(`Failed to parse Excel file: ${err.message}`));
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file.'));
    reader.readAsArrayBuffer(file);
  });
}

// -------------------------------------------------------------
// INVOICE EXCEL TEMPLATE & PARSER
// -------------------------------------------------------------

export function downloadInvoiceExcelTemplate() {
  const headers = [
    'Vendor Code or Name',
    'Invoice Number',
    'Invoice Date (YYYY-MM-DD)',
    'Invoice Amount (Basic ₹)',
    'GST Amount (₹)',
    'PO Number',
    'PO Date (YYYY-MM-DD)',
    'Material or Service Description',
    'MRN Date (YYYY-MM-DD)',
    'Acceptance Date (YYYY-MM-DD)',
    'Agreed Payment Terms (e.g. 30 Days Credit)',
    'Agreed Credit Days',
    'Payment Date (if paid YYYY-MM-DD)',
    'Amount Paid (₹)',
    'Payment Reference No',
  ];

  const sampleData = [
    [
      'V-1001',
      'INV/APEX/26/101',
      '2026-06-01',
      '500000',
      '90000',
      'PO/2026/0890',
      '2026-05-15',
      'Precision Brass Bushings & CNC Parts',
      '2026-06-03',
      '2026-06-05',
      '30 Days from Acceptance',
      '30',
      '2026-07-25',
      '300000',
      'NEFT/AXIS/1109923',
    ],
    [
      'Shree Sai Industrial Polymers Pvt Ltd',
      'SSP/2026/902',
      '2026-06-10',
      '800000',
      '144000',
      'PO/2026/0912',
      '2026-05-28',
      'Specialty Polymer Seals (Grade A)',
      '2026-06-12',
      '2026-06-14',
      '45 Days Credit',
      '45',
      '',
      '0',
      '',
    ],
    [
      'V-1003',
      'DTDE/2026/145',
      '2026-06-15',
      '350000',
      '63000',
      'PO/2026/0950',
      '2026-06-01',
      'Progressive Tooling Dies Maintenance',
      '2026-06-18',
      '2026-06-20',
      '15 Days (No written agreement)',
      '15',
      '',
      '0',
      '',
    ],
  ];

  const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleData]);
  ws['!cols'] = [
    { wch: 32 },
    { wch: 22 },
    { wch: 22 },
    { wch: 24 },
    { wch: 18 },
    { wch: 18 },
    { wch: 20 },
    { wch: 36 },
    { wch: 22 },
    { wch: 24 },
    { wch: 30 },
    { wch: 18 },
    { wch: 25 },
    { wch: 18 },
    { wch: 25 },
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Invoice_Upload_Template');
  XLSX.writeFile(wb, 'MSME_Invoice_Upload_Template.xlsx');
}

export function getDemoInvoiceExcelRows(
  existingVendors: Vendor[],
  existingInvoices: Invoice[],
  rules: StatutoryRuleConfig
): Invoice[] {
  const v1 = existingVendors[0] || {
    id: 'V-1001',
    vendorName: 'Apex Precision Engineering Ltd',
    vendorCode: 'V-1001',
    msmeCategory: 'Micro',
    isMSME: true,
    hasWrittenAgreement: true,
    agreedCreditDays: 30,
  };
  const v2 = existingVendors[1] || {
    id: 'V-1002',
    vendorName: 'Shree Sai Industrial Polymers Pvt Ltd',
    vendorCode: 'V-1002',
    msmeCategory: 'Small',
    isMSME: true,
    hasWrittenAgreement: true,
    agreedCreditDays: 45,
  };
  const v3 = existingVendors[2] || {
    id: 'V-1003',
    vendorName: 'Dynamic Tooling & Dies Enterprises',
    vendorCode: 'V-1003',
    msmeCategory: 'Micro',
    isMSME: true,
    hasWrittenAgreement: false,
    agreedCreditDays: 15,
  };

  const stamp = Date.now().toString().slice(-4);

  const samples = [
    {
      invoiceNumber: `INV/TEST/2026/${stamp}A`,
      vendor: v1,
      invoiceDate: '2026-06-01',
      invoiceAmount: 420000,
      gstAmount: 75600,
      poNumber: `PO/2026/${stamp}1`,
      poDate: '2026-05-20',
      materialDescription: 'High precision lathe shafts and collets',
      mrnDate: '2026-06-03',
      acceptanceDate: '2026-06-05',
      agreedCreditDays: 30,
      hasWrittenAgreement: true,
      pmtAmount: 200000,
      pmtDate: '2026-07-20',
      pmtRef: `NEFT/HDFC/${stamp}01`,
    },
    {
      invoiceNumber: `INV/TEST/2026/${stamp}B`,
      vendor: v2,
      invoiceDate: '2026-06-12',
      invoiceAmount: 950000,
      gstAmount: 171000,
      poNumber: `PO/2026/${stamp}2`,
      poDate: '2026-05-28',
      materialDescription: 'High density polyethylene molded liners',
      mrnDate: '2026-06-15',
      acceptanceDate: '2026-06-17',
      agreedCreditDays: 45,
      hasWrittenAgreement: true,
      pmtAmount: 0,
      pmtDate: '',
      pmtRef: '',
    },
    {
      invoiceNumber: `INV/TEST/2026/${stamp}C`,
      vendor: v3,
      invoiceDate: '2026-06-20',
      invoiceAmount: 280000,
      gstAmount: 50400,
      poNumber: `PO/2026/${stamp}3`,
      poDate: '2026-06-10',
      materialDescription: 'EDM carbide wire electrodes and tooling parts',
      mrnDate: '2026-06-22',
      acceptanceDate: '2026-06-24',
      agreedCreditDays: 15,
      hasWrittenAgreement: false,
      pmtAmount: 0,
      pmtDate: '',
      pmtRef: '',
    },
  ];

  return samples.map((s, idx) => {
    const totalInvoiceAmount = s.invoiceAmount + s.gstAmount;
    const calc = calculateMSMEDueDate(
      s.mrnDate,
      s.acceptanceDate,
      s.hasWrittenAgreement,
      s.agreedCreditDays,
      s.vendor.isMSME,
      rules
    );

    const payments: PartPayment[] = [];
    if (s.pmtAmount > 0 && s.pmtDate) {
      payments.push({
        id: `pmt-demo-${Date.now()}-${idx}`,
        invoiceId: `INV-DEMO-${Date.now()}-${idx}`,
        paymentReference: s.pmtRef || `PMT/${s.invoiceNumber}`,
        paymentDate: s.pmtDate,
        amount: s.pmtAmount,
        paymentMode: 'NEFT',
        remarks: 'Sample payment from Excel loader',
        recordedBy: 'Demo Excel Loader',
        recordedAt: new Date().toISOString(),
      });
    }

    const amountPaid = s.pmtAmount;
    const outstandingAmount = Math.max(0, totalInvoiceAmount - amountPaid);
    const status = outstandingAmount === 0 ? 'Paid' : amountPaid > 0 ? 'Partially Paid' : 'Unpaid';

    return {
      id: `INV-DEMO-${Date.now()}-${idx}`,
      invoiceNumber: s.invoiceNumber,
      vendorId: s.vendor.id,
      vendorName: s.vendor.vendorName,
      vendorCode: s.vendor.vendorCode,
      msmeCategory: s.vendor.msmeCategory,
      isMSME: s.vendor.isMSME,
      invoiceDate: s.invoiceDate,
      invoiceAmount: s.invoiceAmount,
      gstAmount: s.gstAmount,
      totalInvoiceAmount,
      poNumber: s.poNumber,
      poDate: s.poDate,
      materialDescription: s.materialDescription,
      mrnDate: s.mrnDate,
      acceptanceDate: calc.effectiveAcceptanceDate,
      deemedAcceptanceDate: calc.deemedAcceptanceDate,
      hasWrittenAgreement: s.hasWrittenAgreement,
      agreedPaymentTerms: `${s.agreedCreditDays} Days Credit`,
      creditDays: calc.effectiveCreditDays,
      statutoryLimitDays: calc.statutoryLimitDays,
      finalDueDate: calc.finalDueDate,
      payments,
      amountPaid,
      outstandingAmount,
      status,
      disputeFlag: false,
      financialYear: '2026-27',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  });
}

export async function parseInvoiceExcelFile(
  file: File,
  existingVendors: Vendor[],
  existingInvoices: Invoice[],
  rules: StatutoryRuleConfig
): Promise<{
  validInvoices: Invoice[];
  errors: { row: number; reason: string }[];
}> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        const rows: any[] = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

        if (rows.length < 2) {
          return resolve({ validInvoices: [], errors: [{ row: 1, reason: 'File is empty or contains only headers.' }] });
        }

        const headers = (rows[0] || []).map((h: any) => String(h || '').trim());
        const vendorIdx = findColumnIndex(headers, ['vendor', 'vendorcode', 'vendorname', 'supplier', 'party']);
        const invNumIdx = findColumnIndex(headers, ['invoicenumber', 'invoiceno', 'invno', 'billno', 'invoice#']);
        const invDateIdx = findColumnIndex(headers, ['invoicedate', 'invdate', 'billdate', 'date']);
        const amtIdx = findColumnIndex(headers, ['invoiceamount', 'basicamount', 'taxablevalue', 'amount', 'netamount', 'value']);
        const gstIdx = findColumnIndex(headers, ['gstamount', 'gst', 'taxamount', 'igst', 'cgstsgst']);
        const poNumIdx = findColumnIndex(headers, ['ponumber', 'pono', 'po#', 'purchaseorder']);
        const poDateIdx = findColumnIndex(headers, ['podate', 'orderdate']);
        const descIdx = findColumnIndex(headers, ['materialdescription', 'description', 'item', 'itemdescription', 'service']);
        const mrnIdx = findColumnIndex(headers, ['mrndate', 'grndate', 'receiptdate', 'deliverydate', 'goodsreceiptdate']);
        const accIdx = findColumnIndex(headers, ['acceptancedate', 'deemedacceptancedate', 'inspectiondate', 'signoffdate']);
        const termsIdx = findColumnIndex(headers, ['agreedpaymentterms', 'paymentterms', 'terms', 'condition']);
        const creditDaysIdx = findColumnIndex(headers, ['agreedcreditdays', 'creditdays', 'days']);
        const pmtDateIdx = findColumnIndex(headers, ['paymentdate', 'paiddate', 'settlementdate']);
        const pmtAmtIdx = findColumnIndex(headers, ['amountpaid', 'paidamount', 'pmtamount', 'paymentvalue']);
        const pmtRefIdx = findColumnIndex(headers, ['paymentreferenceno', 'paymentref', 'utr', 'chequeno', 'bankref']);

        const validInvoices: Invoice[] = [];
        const errors: { row: number; reason: string }[] = [];
        const existingInvoiceSet = new Set(
          existingInvoices.map((inv) => `${inv.vendorId}_${inv.invoiceNumber.toLowerCase().trim()}`)
        );

        for (let i = 1; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length === 0 || row.every((c: any) => c === undefined || c === '')) {
            continue;
          }

          const vendorIdentifier = String(row[vendorIdx >= 0 ? vendorIdx : 0] || '').trim();
          const invoiceNumber = String(row[invNumIdx >= 0 ? invNumIdx : 1] || '').trim();
          const invoiceDate = parseExcelDate(row[invDateIdx >= 0 ? invDateIdx : 2]) || new Date().toISOString().split('T')[0];
          const rawAmount = row[amtIdx >= 0 ? amtIdx : 3];
          const invoiceAmount = Number(String(rawAmount || 0).replace(/[^0-9.-]+/g, '')) || 0;
          const rawGst = row[gstIdx >= 0 ? gstIdx : 4];
          let gstAmount = Number(String(rawGst || 0).replace(/[^0-9.-]+/g, '')) || 0;
          if (gstAmount === 0 && invoiceAmount > 0 && (rawGst === undefined || rawGst === '')) {
            gstAmount = Math.round(invoiceAmount * 0.18); // Default 18% GST estimate if not explicitly 0
          }

          const poNumber = String(row[poNumIdx >= 0 ? poNumIdx : 5] || '').trim();
          const poDate = parseExcelDate(row[poDateIdx >= 0 ? poDateIdx : 6]) || invoiceDate;
          const materialDescription = String(row[descIdx >= 0 ? descIdx : 7] || '').trim();
          const mrnDate = parseExcelDate(row[mrnIdx >= 0 ? mrnIdx : 8]) || invoiceDate;
          const acceptanceDate = parseExcelDate(row[accIdx >= 0 ? accIdx : 9]) || mrnDate;
          const agreedTerms = String(row[termsIdx >= 0 ? termsIdx : 10] || '30 Days Credit').trim();
          const creditDaysRaw = Number(row[creditDaysIdx >= 0 ? creditDaysIdx : 11]);
          const pmtDate = parseExcelDate(row[pmtDateIdx >= 0 ? pmtDateIdx : 12]);
          const rawPmtAmt = row[pmtAmtIdx >= 0 ? pmtAmtIdx : 13];
          const pmtAmount = Number(String(rawPmtAmt || 0).replace(/[^0-9.-]+/g, '')) || 0;
          const pmtRef = String(row[pmtRefIdx >= 0 ? pmtRefIdx : 14] || '').trim();

          if (!invoiceNumber) {
            errors.push({ row: i + 1, reason: 'Invoice Number is mandatory.' });
            continue;
          }

          if (!invoiceAmount || invoiceAmount <= 0) {
            errors.push({ row: i + 1, reason: `Invalid Invoice Amount for "${invoiceNumber}".` });
            continue;
          }

          // Match Vendor by code or name
          let matchedVendor = existingVendors.find(
            (v) =>
              (vendorIdentifier && v.vendorCode.toLowerCase() === vendorIdentifier.toLowerCase()) ||
              (vendorIdentifier && v.vendorName.toLowerCase().includes(vendorIdentifier.toLowerCase())) ||
              (vendorIdentifier && vendorIdentifier.toLowerCase().includes(v.vendorName.toLowerCase()))
          );

          if (!matchedVendor) {
            matchedVendor = existingVendors[0] || {
              id: 'VEND-001',
              vendorName: vendorIdentifier || 'General MSME Supplier',
              vendorCode: 'V-1001',
              msmeCategory: 'Micro',
              isMSME: true,
              hasWrittenAgreement: true,
              agreedCreditDays: 30,
            } as any;
          }

          const vendorId = matchedVendor ? matchedVendor.id : 'VEND-001';
          const vendorName = matchedVendor ? matchedVendor.vendorName : vendorIdentifier || 'MSME Supplier';
          const vendorCode = matchedVendor ? matchedVendor.vendorCode : 'V-1001';
          const isMSME = matchedVendor ? matchedVendor.isMSME : true;
          const msmeCategory = matchedVendor ? matchedVendor.msmeCategory : 'Micro';
          const hasWrittenAgreement = matchedVendor ? matchedVendor.hasWrittenAgreement : true;
          const agreedCreditDays =
            !isNaN(creditDaysRaw) && creditDaysRaw > 0
              ? creditDaysRaw
              : matchedVendor
              ? matchedVendor.agreedCreditDays
              : 30;

          // Duplicate check
          const duplicateKey = `${vendorId}_${invoiceNumber.toLowerCase().trim()}`;
          if (existingInvoiceSet.has(duplicateKey)) {
            errors.push({
              row: i + 1,
              reason: `Duplicate invoice number "${invoiceNumber}" for vendor "${vendorName}".`,
            });
            continue;
          }
          existingInvoiceSet.add(duplicateKey);

          const totalInvoiceAmount = invoiceAmount + gstAmount;

          // Calculate MSME Due date
          const dueDateCalculation = calculateMSMEDueDate(
            mrnDate,
            acceptanceDate,
            hasWrittenAgreement,
            agreedCreditDays,
            isMSME,
            rules
          );

          const payments: PartPayment[] = [];
          if (pmtAmount > 0 && pmtDate) {
            payments.push({
              id: `pmt-imp-${Date.now()}-${i}`,
              invoiceId: `INV-IMP-${Date.now()}-${i}`,
              paymentReference: pmtRef || `PMT/EXCEL/${invoiceNumber}`,
              paymentDate: pmtDate,
              amount: pmtAmount,
              paymentMode: 'NEFT',
              remarks: 'Imported via Excel invoice file',
              recordedBy: 'Excel Bulk Ingestion',
              recordedAt: new Date().toISOString(),
            });
          }

          const amountPaid = pmtAmount;
          const outstandingAmount = Math.max(0, totalInvoiceAmount - amountPaid);
          const status = outstandingAmount === 0 ? 'Paid' : amountPaid > 0 ? 'Partially Paid' : 'Unpaid';

          validInvoices.push({
            id: `INV-IMP-${Date.now()}-${i}`,
            invoiceNumber,
            vendorId,
            vendorName,
            vendorCode,
            msmeCategory,
            isMSME,
            invoiceDate,
            invoiceAmount,
            gstAmount,
            totalInvoiceAmount,
            poNumber: poNumber || `PO/${invoiceNumber}`,
            poDate,
            materialDescription: materialDescription || 'Industrial Supply / Services',
            mrnDate,
            acceptanceDate: dueDateCalculation.effectiveAcceptanceDate,
            deemedAcceptanceDate: dueDateCalculation.deemedAcceptanceDate,
            hasWrittenAgreement,
            agreedPaymentTerms: agreedTerms,
            creditDays: dueDateCalculation.effectiveCreditDays,
            statutoryLimitDays: dueDateCalculation.statutoryLimitDays,
            finalDueDate: dueDateCalculation.finalDueDate,
            payments,
            amountPaid,
            outstandingAmount,
            status,
            disputeFlag: false,
            financialYear: '2026-27',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          });
        }

        resolve({ validInvoices, errors });
      } catch (err: any) {
        reject(new Error(`Failed to parse invoice file: ${err.message}`));
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file.'));
    reader.readAsArrayBuffer(file);
  });
}

// -------------------------------------------------------------
// PAYMENT / BANK CLEARING EXCEL TEMPLATE & PARSER
// -------------------------------------------------------------

export function downloadPaymentExcelTemplate() {
  const headers = [
    'Invoice Number *',
    'Payment Date (YYYY-MM-DD) *',
    'Amount Paid (₹) *',
    'Payment Mode (NEFT/RTGS/Cheque/UPI/Direct Debit)',
    'Bank Reference / UTR Number',
    'Payment Reference',
    'Vendor Code or Name (Optional)',
    'Remarks',
  ];

  const sampleData = [
    [
      'INV/APEX/26/101',
      '2026-07-20',
      '250000',
      'NEFT',
      'UTR99882233110',
      'PMT/NEFT/0912',
      'V-1001',
      'Tranche 1 payment against precision shafts delivery',
    ],
    [
      'SSP/2026/902',
      '2026-07-28',
      '400000',
      'RTGS',
      'AXISR520260728001',
      'PMT/RTGS/8892',
      'Shree Sai Industrial Polymers Pvt Ltd',
      'Mid-month polymer seals settlement',
    ],
    [
      'DTDE/2026/145',
      '2026-07-05',
      '413000',
      'NEFT',
      'HDFCN26186004921',
      'PMT/FULL/0034',
      'V-1003',
      'Full settlement of dies maintenance within statutory 15 days',
    ],
  ];

  const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleData]);
  ws['!cols'] = [
    { wch: 24 },
    { wch: 24 },
    { wch: 20 },
    { wch: 28 },
    { wch: 30 },
    { wch: 22 },
    { wch: 32 },
    { wch: 40 },
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Payment_Clearing_Template');
  XLSX.writeFile(wb, 'MSME_Payment_Clearing_Template.xlsx');
}

export function getDemoPaymentExcelRows(existingInvoices: Invoice[]): {
  invoiceId: string;
  invoiceNumber: string;
  vendorName: string;
  amount: number;
  paymentDate: string;
  paymentReference: string;
  paymentMode: 'NEFT' | 'RTGS' | 'Cheque' | 'UPI' | 'Direct Debit';
  bankReferenceNo: string;
  remarks: string;
}[] {
  const targetInvoices = existingInvoices.filter((i) => i.outstandingAmount > 0).slice(0, 3);
  if (targetInvoices.length === 0) {
    const first = existingInvoices[0] || {
      id: 'INV-1',
      invoiceNumber: 'INV/2026/DEMO',
      vendorName: 'Apex Precision Engineering',
      outstandingAmount: 200000,
    };
    return [
      {
        invoiceId: first.id,
        invoiceNumber: first.invoiceNumber,
        vendorName: first.vendorName,
        amount: 150000,
        paymentDate: '2026-07-22',
        paymentReference: 'PMT/DEMO/001',
        paymentMode: 'NEFT',
        bankReferenceNo: 'UTR202607229988',
        remarks: 'Part settlement via demo Excel batch loader',
      },
    ];
  }

  return targetInvoices.map((inv, idx) => {
    const payAmt = Math.min(inv.outstandingAmount, Math.round(inv.outstandingAmount * (idx === 0 ? 0.5 : 1)));
    return {
      invoiceId: inv.id,
      invoiceNumber: inv.invoiceNumber,
      vendorName: inv.vendorName,
      amount: payAmt || 50000,
      paymentDate: '2026-07-25',
      paymentReference: `PMT/BATCH/2026/0${idx + 1}`,
      paymentMode: idx % 2 === 0 ? 'NEFT' : 'RTGS',
      bankReferenceNo: `UTR/AXIS/26072500${idx + 10}`,
      remarks: `Demo tranche payment for ${inv.invoiceNumber} (${inv.vendorName})`,
    };
  });
}

export async function parsePaymentExcelFile(
  file: File,
  existingInvoices: Invoice[]
): Promise<{
  validPayments: {
    invoiceId: string;
    invoiceNumber: string;
    vendorName: string;
    amount: number;
    paymentDate: string;
    paymentReference: string;
    paymentMode: 'NEFT' | 'RTGS' | 'Cheque' | 'UPI' | 'Direct Debit';
    bankReferenceNo: string;
    remarks: string;
  }[];
  errors: { row: number; reason: string }[];
}> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        const rows: any[] = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

        if (rows.length < 2) {
          return resolve({ validPayments: [], errors: [{ row: 1, reason: 'File is empty or contains only headers.' }] });
        }

        const headers = (rows[0] || []).map((h: any) => String(h || '').trim());
        const invNumIdx = findColumnIndex(headers, ['invoicenumber', 'invoiceno', 'invno', 'billno', 'invoice#']);
        const pmtDateIdx = findColumnIndex(headers, ['paymentdate', 'paiddate', 'date', 'clearingdate']);
        const amtIdx = findColumnIndex(headers, ['amountpaid', 'amount', 'paidamount', 'paymentamount', 'value']);
        const modeIdx = findColumnIndex(headers, ['paymentmode', 'mode', 'channel', 'type']);
        const utrIdx = findColumnIndex(headers, ['bankreference', 'utr', 'bankref', 'utrno', 'chequeno']);
        const refIdx = findColumnIndex(headers, ['paymentreference', 'paymentref', 'refno', 'voucherno']);
        const vendorIdx = findColumnIndex(headers, ['vendor', 'vendorname', 'vendorcode', 'supplier']);
        const remarksIdx = findColumnIndex(headers, ['remarks', 'notes', 'narration', 'description']);

        const validPayments: any[] = [];
        const errors: { row: number; reason: string }[] = [];

        for (let i = 1; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length === 0 || row.every((c: any) => c === undefined || c === '')) {
            continue;
          }

          const invoiceNumberRaw = String(row[invNumIdx >= 0 ? invNumIdx : 0] || '').trim();
          const pmtDate = parseExcelDate(row[pmtDateIdx >= 0 ? pmtDateIdx : 1]) || new Date().toISOString().split('T')[0];
          const rawAmt = row[amtIdx >= 0 ? amtIdx : 2];
          const amount = Number(String(rawAmt || 0).replace(/[^0-9.-]+/g, '')) || 0;
          const rawMode = String(row[modeIdx >= 0 ? modeIdx : 3] || 'NEFT').trim().toUpperCase();
          const bankRef = String(row[utrIdx >= 0 ? utrIdx : 4] || '').trim();
          const pmtRef = String(row[refIdx >= 0 ? refIdx : 5] || '').trim() || `PMT/IMP/${Date.now().toString().slice(-4)}/${i}`;
          const vendorHint = String(row[vendorIdx >= 0 ? vendorIdx : 6] || '').trim();
          const remarks = String(row[remarksIdx >= 0 ? remarksIdx : 7] || '').trim();

          if (!invoiceNumberRaw) {
            errors.push({ row: i + 1, reason: 'Invoice Number is mandatory to apply payments.' });
            continue;
          }

          if (amount <= 0) {
            errors.push({ row: i + 1, reason: `Invalid Payment Amount for invoice "${invoiceNumberRaw}".` });
            continue;
          }

          // Match invoice
          const matchedInvoice = existingInvoices.find(
            (inv) =>
              inv.invoiceNumber.toLowerCase().trim() === invoiceNumberRaw.toLowerCase().trim() ||
              inv.invoiceNumber.toLowerCase().replace(/[^a-z0-9]/g, '') ===
                invoiceNumberRaw.toLowerCase().replace(/[^a-z0-9]/g, '')
          );

          if (!matchedInvoice) {
            errors.push({
              row: i + 1,
              reason: `Invoice "${invoiceNumberRaw}" was not found in the Invoice Register.`,
            });
            continue;
          }

          let mode: 'NEFT' | 'RTGS' | 'Cheque' | 'UPI' | 'Direct Debit' = 'NEFT';
          if (rawMode.includes('RTGS')) mode = 'RTGS';
          else if (rawMode.includes('CHEQ') || rawMode.includes('CHQ')) mode = 'Cheque';
          else if (rawMode.includes('UPI')) mode = 'UPI';
          else if (rawMode.includes('DIRECT') || rawMode.includes('DEBIT')) mode = 'Direct Debit';

          validPayments.push({
            invoiceId: matchedInvoice.id,
            invoiceNumber: matchedInvoice.invoiceNumber,
            vendorName: matchedInvoice.vendorName,
            amount,
            paymentDate: pmtDate,
            paymentReference: pmtRef,
            paymentMode: mode,
            bankReferenceNo: bankRef,
            remarks: remarks || `Bank settlement tranche imported from Excel for ${matchedInvoice.invoiceNumber}`,
          });
        }

        resolve({ validPayments, errors });
      } catch (err: any) {
        reject(new Error(`Failed to parse payment Excel file: ${err.message}`));
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file.'));
    reader.readAsArrayBuffer(file);
  });
}

// -------------------------------------------------------------
// EXCEL EXPORTER
// -------------------------------------------------------------

export function exportTableToExcel(data: any[], fileName: string, sheetName: string = 'Report') {
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  XLSX.writeFile(wb, `${fileName}.xlsx`);
}
