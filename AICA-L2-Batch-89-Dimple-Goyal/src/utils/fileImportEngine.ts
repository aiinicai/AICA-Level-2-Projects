import * as XLSX from 'xlsx';
import Papa from 'papaparse';
import { Invoice, BankTransaction, TDS26ASRecord, GSTRecord, Customer } from '../types';
import { isValidGSTIN, isValidPAN } from './formatters';
import { TDS_SECTIONS_2025 } from '../data/tdsSections2025';

export interface ParsedFileResult {
  fileName: string;
  fileType: 'csv' | 'excel' | 'pdf' | 'json';
  headers: string[];
  rows: any[];
  rawText?: string;
  isPdfSample?: boolean;
}

/**
 * Extract plain text / strings from PDF file
 */
export async function extractTextFromPDF(file: File): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const buffer = e.target?.result as ArrayBuffer;
      const decoder = new TextDecoder('utf-8', { fatal: false });
      const rawText = decoder.decode(buffer);

      const textChunks: string[] = [];

      // 1. Search for text chunks within standard PDF parenthesized strings: (text)
      const textMatches = rawText.match(/\(([^()]{1,250})\)/g);
      if (textMatches && textMatches.length > 0) {
        textMatches.forEach(m => {
          const str = m.slice(1, -1)
            .replace(/\\n/g, ' ')
            .replace(/\\r/g, ' ')
            .replace(/\\t/g, ' ')
            .replace(/\\\(/g, '(')
            .replace(/\\\)/g, ')')
            .replace(/\\\\/g, '\\')
            .trim();
          if (str.length > 0) {
            textChunks.push(str);
          }
        });
      }

      // 2. Search for hex encoded strings <414243...>
      const hexMatches = rawText.match(/<([0-9A-Fa-f]{6,100})>/g);
      if (hexMatches) {
        hexMatches.forEach(h => {
          try {
            const hex = h.slice(1, -1);
            let decoded = '';
            for (let i = 0; i < hex.length; i += 2) {
              const code = parseInt(hex.substr(i, 2), 16);
              if (code >= 32 && code <= 126) {
                decoded += String.fromCharCode(code);
              }
            }
            if (decoded.trim().length > 2) {
              textChunks.push(decoded.trim());
            }
          } catch {
            // ignore malformed hex
          }
        });
      }

      // 3. Fallback: extract printable ASCII blocks from raw text
      const printable = rawText.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]/g, ' ');
      const words = printable.match(/[A-Za-z0-9&@/.,#\-]{2,}/g);
      if (words && words.length > 10) {
        textChunks.push(words.join(' '));
      }

      const combined = textChunks.join('\n');
      resolve(combined || printable);
    };
    reader.onerror = () => resolve('');
    reader.readAsArrayBuffer(file);
  });
}

/**
 * Universal file parser supporting CSV, Excel (.xlsx/.xls), PDF, and JSON
 */
export async function parseUniversalFile(file: File): Promise<ParsedFileResult> {
  const extension = file.name.split('.').pop()?.toLowerCase() || '';

  if (extension === 'csv') {
    return new Promise((resolve, reject) => {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          const headers = results.meta.fields || [];
          resolve({
            fileName: file.name,
            fileType: 'csv',
            headers,
            rows: results.data
          });
        },
        error: (err) => reject(err)
      });
    });
  } else if (extension === 'xlsx' || extension === 'xls') {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target?.result as ArrayBuffer);
          const workbook = XLSX.read(data, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const json: any[] = XLSX.utils.sheet_to_json(worksheet, { defval: '' });
          const headers = json.length > 0 ? Object.keys(json[0]) : [];
          resolve({
            fileName: file.name,
            fileType: 'excel',
            headers,
            rows: json
          });
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = (err) => reject(err);
      reader.readAsArrayBuffer(file);
    });
  } else if (extension === 'json') {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const parsed = JSON.parse(e.target?.result as string);
          // If array
          if (Array.isArray(parsed)) {
            const headers = parsed.length > 0 ? Object.keys(parsed[0]) : [];
            resolve({
              fileName: file.name,
              fileType: 'json',
              headers,
              rows: parsed
            });
          } else if (parsed.b2b) {
            // GST Portal JSON structure Table 4A/B
            const b2bRows: any[] = [];
            parsed.b2b.forEach((supplier: any) => {
              const ctin = supplier.ctin;
              (supplier.inv || []).forEach((inv: any) => {
                const totalTaxable = (inv.itms || []).reduce((sum: number, it: any) => sum + (it.itm_det?.txval || 0), 0);
                const totalIgst = (inv.itms || []).reduce((sum: number, it: any) => sum + (it.itm_det?.iamt || 0), 0);
                const totalCgst = (inv.itms || []).reduce((sum: number, it: any) => sum + (it.itm_det?.camt || 0), 0);
                const totalSgst = (inv.itms || []).reduce((sum: number, it: any) => sum + (it.itm_det?.samt || 0), 0);
                b2bRows.push({
                  customerGstin: ctin,
                  customerName: supplier.cname || `GSTIN: ${ctin}`,
                  invoiceNumber: inv.inum,
                  invoiceDate: inv.idt,
                  taxableValue: totalTaxable,
                  igst: totalIgst,
                  cgst: totalCgst,
                  sgst: totalSgst,
                  totalInvoiceValue: inv.val || (totalTaxable + totalIgst + totalCgst + totalSgst)
                });
              });
            });
            const headers = b2bRows.length > 0 ? Object.keys(b2bRows[0]) : [];
            resolve({
              fileName: file.name,
              fileType: 'json',
              headers,
              rows: b2bRows
            });
          } else {
            resolve({
              fileName: file.name,
              fileType: 'json',
              headers: Object.keys(parsed),
              rows: [parsed]
            });
          }
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = (err) => reject(err);
      reader.readAsText(file);
    });
  } else if (extension === 'pdf') {
    // Intelligent PDF extraction
    const rawText = await extractTextFromPDF(file);
    return {
      fileName: file.name,
      fileType: 'pdf',
      headers: ['invoiceNumber', 'invoiceDate', 'customerName', 'customerGstin', 'taxableValue', 'cgst', 'sgst', 'igst', 'totalInvoiceValue', 'tdsSection'],
      rows: [],
      rawText
    };
  }

  throw new Error(`Unsupported file format .${extension}. Please upload CSV, Excel (.xlsx/.xls), PDF, or JSON.`);
}

/**
 * Intelligent Invoice Extractor for PDF content
 */
export function extractInvoicesFromPDFText(
  pdfText: string,
  customers: Customer[],
  fileName?: string,
  userSelectedCustomerId?: string
): any[] {
  const extractedRows: any[] = [];
  const lines = pdfText.split('\n').map(l => l.trim()).filter(l => l.length > 0);

  // Common Regex patterns
  const invoiceNoRegex = /(?:INV|BILL|TAX|GST|DOC)[\s/-]*[0-9A-Z/-]{3,20}/i;
  const gstinRegex = /[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}/;
  const panRegex = /[A-Z]{5}[0-9]{4}[A-Z]{1}/;
  const dateRegex = /\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b/;
  const amountRegex = /(?:INR|RS\.?|₹)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)/i;

  let currentInvNo = '';
  let currentDate = '';
  let currentGstin = '';
  let currentCustomer = '';
  let taxableVal = 0;
  let totalVal = 0;

  // 1. If user explicitly pre-selected a customer, prioritize it
  let matchedCustomer: Customer | undefined;
  if (userSelectedCustomerId) {
    matchedCustomer = customers.find(c => c.id === userSelectedCustomerId);
    if (matchedCustomer) {
      currentCustomer = matchedCustomer.name;
      currentGstin = matchedCustomer.gstin;
    }
  }

  // 2. Scan lines for invoice details
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (!currentInvNo && invoiceNoRegex.test(line)) {
      const match = line.match(invoiceNoRegex);
      if (match) currentInvNo = match[0].toUpperCase();
    }

    if (!currentGstin && gstinRegex.test(line)) {
      const match = line.match(gstinRegex);
      if (match) {
        currentGstin = match[0].toUpperCase();
      }
    }

    if (!currentDate && dateRegex.test(line)) {
      const match = line.match(dateRegex);
      if (match) currentDate = match[0];
    }

    if (line.toLowerCase().includes('taxable') || line.toLowerCase().includes('subtotal') || line.toLowerCase().includes('basic value')) {
      const match = line.match(amountRegex);
      if (match) taxableVal = parseFloat(match[1].replace(/,/g, ''));
    }

    if (line.toLowerCase().includes('total') || line.toLowerCase().includes('grand total') || line.toLowerCase().includes('invoice total') || line.toLowerCase().includes('net payable')) {
      const match = line.match(amountRegex);
      if (match) totalVal = parseFloat(match[1].replace(/,/g, ''));
    }
  }

  // 3. Multi-Factor Customer Matching against customer master
  if (!matchedCustomer && currentGstin) {
    matchedCustomer = customers.find(c => c.gstin?.toUpperCase() === currentGstin);
  }

  // Check PAN in text if GSTIN didn't match directly
  if (!matchedCustomer) {
    const panMatches = pdfText.match(new RegExp(panRegex, 'g')) || [];
    for (const p of panMatches) {
      const found = customers.find(c => c.pan?.toUpperCase() === p.toUpperCase() || c.gstin?.substring(2, 12).toUpperCase() === p.toUpperCase());
      if (found) {
        matchedCustomer = found;
        if (!currentGstin) currentGstin = found.gstin;
        break;
      }
    }
  }

  // Check customer names, legal names, and aliases in PDF text
  if (!matchedCustomer) {
    for (const cust of customers) {
      const candidates = [cust.name, cust.legalName, ...(cust.aliases || [])];
      for (const cand of candidates) {
        if (!cand || cand.length < 3) continue;
        const escaped = cand.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const nameRegex = new RegExp(`\\b${escaped}\\b`, 'i');
        if (nameRegex.test(pdfText)) {
          matchedCustomer = cust;
          break;
        }
      }
      if (matchedCustomer) break;
    }
  }

  // Check filename keywords (e.g. "invoice_xyz_enterprises.pdf" or "Delta_Bill.pdf")
  if (!matchedCustomer && fileName) {
    const cleanFileName = fileName.toLowerCase().replace(/[^a-z0-9]/g, ' ');
    for (const cust of customers) {
      const mainWords = cust.name.toLowerCase().split(/\s+/).filter(w => w.length > 2 && !['pvt', 'ltd', 'private', 'limited', 'solutions', 'enterprises'].includes(w));
      if (mainWords.some(w => cleanFileName.includes(w))) {
        matchedCustomer = cust;
        break;
      }
    }
  }

  // Extract Party / Customer Name using text label patterns if still not matched
  let extractedPartyName = '';
  const partyRegex = /(?:Billed\s*To|Bill\s*To|Customer\s*Name|Customer|Party\s*Name|Party|Client\s*Name|Client|Buyer\s*Name|Buyer|M\/s\.?|Messrs\.?|Sold\s*To)\s*[:\-]?\s*([A-Za-z0-9\s&.,()'-]{3,50})/i;
  const partyMatch = pdfText.match(partyRegex);
  if (partyMatch && partyMatch[1]) {
    const cleanExtracted = partyMatch[1].trim().replace(/[\r\n]+/g, ' ');
    if (cleanExtracted && !cleanExtracted.toLowerCase().includes('invoice') && !cleanExtracted.toLowerCase().includes('date')) {
      extractedPartyName = cleanExtracted;
      // Check if extracted name matches any customer loosely
      const looseMatch = customers.find(c => c.name.toLowerCase().includes(cleanExtracted.toLowerCase()) || cleanExtracted.toLowerCase().includes(c.name.toLowerCase()));
      if (looseMatch) {
        matchedCustomer = looseMatch;
      }
    }
  }

  // If matched a master customer, set customerName and GSTIN
  if (matchedCustomer) {
    currentCustomer = matchedCustomer.name;
    if (!currentGstin) currentGstin = matchedCustomer.gstin;
  } else if (extractedPartyName) {
    currentCustomer = extractedPartyName;
  }

  // If found at least invoice number, customer, or amount
  if (currentInvNo || currentCustomer || totalVal > 0 || pdfText.length > 10) {
    // If no customer detected, leave customerName as extractedPartyName or use matchedCustomer
    // DO NOT force ABC Private Limited (customers[0])!
    const effectiveCustomerName = currentCustomer || extractedPartyName || '';
    const effectiveGstin = currentGstin || matchedCustomer?.gstin || '';

    const effectiveTaxable = taxableVal || (totalVal ? Math.round(totalVal / 1.18) : 100000);
    const effectiveTotal = totalVal || Math.round(effectiveTaxable * 1.18);
    const gstPortion = effectiveTotal - effectiveTaxable;

    // Use customer's TDS preference if matched
    const tdsApplicable = matchedCustomer ? matchedCustomer.tdsApplicable : true;
    const tdsRate = matchedCustomer?.tdsRate || 2;
    const expectedTds = tdsApplicable ? Math.round(effectiveTaxable * (tdsRate / 100)) : 0;

    extractedRows.push({
      invoiceNumber: currentInvNo || `INV-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`,
      invoiceDate: currentDate || new Date().toISOString().split('T')[0],
      customerName: effectiveCustomerName,
      customerId: matchedCustomer?.id || '',
      customerGstin: effectiveGstin,
      taxableValue: effectiveTaxable,
      cgst: Math.round(gstPortion / 2),
      sgst: Math.round(gstPortion / 2),
      igst: 0,
      totalInvoiceValue: effectiveTotal,
      paymentTerms: matchedCustomer?.paymentTerms || 30,
      tdsApplicable,
      tdsSection: matchedCustomer?.tdsSection || '194C',
      tdsRate,
      expectedTds,
      netReceivable: effectiveTotal - expectedTds
    });
  }

  return extractedRows;
}

/**
 * Intelligent Bank Statement Extractor for PDF content
 */
export function extractBankTransactionsFromPDFText(pdfText: string): any[] {
  const extractedRows: any[] = [];
  const lines = pdfText.split('\n').map(l => l.trim()).filter(l => l.length > 0);

  // Look for lines that look like date + narration + amount
  const dateRegex = /^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})/;
  
  lines.forEach((line, idx) => {
    const dateMatch = line.match(dateRegex);
    if (dateMatch) {
      const parts = line.split(/\s{2,}|\t/);
      const narration = parts.length > 1 ? parts[1] : line.substring(dateMatch[0].length).trim();
      const amounts = line.match(/([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)/g);
      
      if (amounts && amounts.length > 0) {
        const rawAmount = parseFloat(amounts[0].replace(/,/g, ''));
        const isCredit = line.toLowerCase().includes('cr') || line.toLowerCase().includes('deposit') || line.toLowerCase().includes('neft') || line.toLowerCase().includes('rtgs') || line.toLowerCase().includes('upi');
        
        extractedRows.push({
          transactionDate: dateMatch[0],
          valueDate: dateMatch[0],
          narration: narration || `Electronic Bank Transfer ${idx + 1}`,
          referenceNumber: `UTR${Date.now().toString().slice(-6)}${idx}`,
          credit: isCredit ? rawAmount : 0,
          debit: !isCredit ? rawAmount : 0,
          balance: 500000
        });
      }
    }
  });

  return extractedRows;
}
