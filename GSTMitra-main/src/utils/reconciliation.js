// Main reconciliation function
import Papa from 'papaparse';

// Main reconciliation function
export const reconcileGSTFiles = async (gstr1File, gstr2File, gstr2Type, gstr1Mapping, gstr2Mapping, gstr1StartRow, gstr2StartRow) => {
  try {
    console.log('Starting reconciliation with:', {
      gstr2Type,
      gstr1StartRow,
      gstr2StartRow,
      gstr1Mapping,
      gstr2Mapping
    });
    
    // Parse and normalize both files
    const gstr1Data = await parseFile(gstr1File, gstr1Mapping, gstr1StartRow, 'gstr1');
    const gstr2Data = await parseFile(gstr2File, gstr2Mapping, gstr2StartRow, gstr2Type.toLowerCase());

    console.log('Parsed data lengths:', {
      gstr1: gstr1Data.length,
      gstr2: gstr2Data.length
    });
    
    // Perform reconciliation
    const results = performReconciliation(gstr1Data, gstr2Data);

    return results;
  } catch (error) {
    console.error('Error in reconciliation:', error);
    throw new Error('Failed to reconcile files. Please check file format and try again.');
  }
};

// Parse file based on type (JSON or CSV), applying mapping if provided
const parseFile = (file, mapping = null, startRow = 2, fileType = 'gstr1') => {
  return new Promise((resolve, reject) => {
    const fileExtension = file.name.split('.').pop().toLowerCase();

    if (fileExtension === 'json') {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          resolve(JSON.parse(e.target.result));
        } catch (error) {
          reject(new Error('Invalid JSON format'));
        }
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    } else if (fileExtension === 'csv') {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          if (results.errors.length) {
            return reject(new Error('CSV parsing error: ' + results.errors[0].message));
          }
          let data = results.data;
          
          // Apply start row filtering - startRow is 1-indexed from user perspective
          // Papa Parse with header:true already handles the first row as headers
          // So if startRow is 2, we want to skip 0 rows (start from beginning)
          // If startRow is 3, we want to skip 1 row, etc.
          if (startRow > 1) {
            data = data.slice(startRow - 1);
          }

          if (!mapping) {
            // If no mapping, normalize the raw CSV data
            return resolve(normalizeGSTRData(data, fileType));
          }

          // Apply mapping to transform data
          const mappedData = data.map(row => {
            const newRow = {};
            for (const key in mapping) {
              if (mapping[key] && row[mapping[key]] !== undefined) {
                newRow[key] = row[mapping[key]];
              } else {
                newRow[key] = '';
              }
            }
            return newRow;
          }).filter(row => {
            // Filter out empty rows
            return Object.values(row).some(value => value && value.toString().trim() !== '');
          });
          
          console.log('Mapped data sample:', mappedData.slice(0, 3));
          resolve(mappedData);
        },
        error: (err) => reject(new Error('Failed to parse CSV: ' + err.message)),
      });
    } else {
      reject(new Error('Unsupported file format'));
    }
  });
};

// New function to parse only headers and a preview for mapping screen
export const parseCsvForMapping = (file) => {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      preview: 10, // Get first 10 rows for better preview
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        if (results.errors.length) {
          return reject(new Error('CSV parsing error: ' + results.errors[0].message));
        }
        console.log('CSV preview data:', {
          headers: results.meta.fields,
          dataLength: results.data.length,
          sampleData: results.data.slice(0, 2)
        });
        resolve({
          headers: results.meta.fields,
          preview: results.data,
        });
      },
      error: (err) => reject(new Error('Failed to parse CSV: ' + err.message)),
    });
  });
};

// Normalize data from different GSTR formats
const normalizeGSTRData = (data, type) => {
  if (!Array.isArray(data)) {
    // Handle JSON structure - try to find invoice array
    if (data.invoices) data = data.invoices;
    else if (data.b2b) data = extractFromB2B(data.b2b);
    else if (data.data) data = data.data;
    else throw new Error('Unable to find invoice data in file');
  }

  return data.map(invoice => {
    const normalized = {
      invoiceNumber: extractInvoiceNumber(invoice),
      invoiceDate: extractInvoiceDate(invoice),
      invoiceValue: extractInvoiceValue(invoice),
      taxableValue: extractTaxableValue(invoice),
      gstin: extractGSTIN(invoice),
      igst: extractTaxAmount(invoice, 'igst'),
      cgst: extractTaxAmount(invoice, 'cgst'),
      sgst: extractTaxAmount(invoice, 'sgst'),
      originalData: invoice
    };

    // Ensure all numeric values are numbers
    normalized.invoiceValue = parseFloat(normalized.invoiceValue) || 0;
    normalized.taxableValue = parseFloat(normalized.taxableValue) || 0;
    normalized.igst = parseFloat(normalized.igst) || 0;
    normalized.cgst = parseFloat(normalized.cgst) || 0;
    normalized.sgst = parseFloat(normalized.sgst) || 0;

    return normalized;
  }).filter(invoice => invoice.invoiceNumber); // Filter out invalid entries
};

// Extract invoice data from B2B structure (common in GST JSON)
const extractFromB2B = (b2bData) => {
  const invoices = [];
  b2bData.forEach(supplier => {
    if (supplier.inv) {
      supplier.inv.forEach(invoice => {
        invoices.push({
          ...invoice,
          gstin: supplier.ctin,
          supplierGstin: supplier.ctin
        });
      });
    }
  });
  return invoices;
};

// Field extraction functions with multiple possible field names
const extractInvoiceNumber = (invoice) => {
  return invoice.invoiceNumber || 
         invoice.invoice_number || 
         invoice.inum || 
         invoice.inv_num || 
         invoice.InvoiceNumber ||
         invoice.Invoice_Number ||
         '';
};

const extractInvoiceDate = (invoice) => {
  return invoice.invoiceDate || 
         invoice.invoice_date || 
         invoice.idt || 
         invoice.inv_date || 
         invoice.InvoiceDate ||
         invoice.Invoice_Date ||
         '';
};

const extractInvoiceValue = (invoice) => {
  return invoice.invoiceValue || 
         invoice.invoice_value || 
         invoice.val || 
         invoice.inv_val || 
         invoice.InvoiceValue ||
         invoice.Invoice_Value ||
         invoice.total ||
         0;
};

const extractTaxableValue = (invoice) => {
  return invoice.taxableValue || 
         invoice.taxable_value || 
         invoice.txval || 
         invoice.tax_val || 
         invoice.TaxableValue ||
         invoice.Taxable_Value ||
         0;
};

const extractGSTIN = (invoice) => {
  return invoice.gstin || 
         invoice.GSTIN || 
         invoice.ctin || 
         invoice.supplierGstin || 
         invoice.supplier_gstin ||
         invoice.Supplier_GSTIN ||
         '';
};

const extractTaxAmount = (invoice, taxType) => {
  const upperType = taxType.toUpperCase();
  const lowerType = taxType.toLowerCase();
  
  return invoice[lowerType] || 
         invoice[upperType] || 
         invoice[`${lowerType}_amount`] ||
         invoice[`${upperType}_Amount`] ||
         invoice[`${lowerType}Amount`] ||
         0;
};

// Main reconciliation logic
const getInvoiceKey = (invoice) => {
  // Use GSTIN and Invoice Value (rounded to 2 decimals) for matching
  const gstin = (invoice.gstin || '').toString().trim().toLowerCase();
  const value = parseFloat(invoice.invoiceValue) || 0;
  return `${gstin}-${value}`;
};

// Enhanced sorting function with multiple criteria
const sortInvoicesRobust = (invoices) => {
  return invoices.sort((a, b) => {
    // 1. Sort by GSTIN (case-insensitive)
    const gstinA = (a.gstin || '').toString().toLowerCase();
    const gstinB = (b.gstin || '').toString().toLowerCase();
    if (gstinA !== gstinB) {
      return gstinA.localeCompare(gstinB);
    }

    // 2. Sort by Invoice Number (case-insensitive)
    const invNumA = (a.invoiceNumber || '').toString().toLowerCase();
    const invNumB = (b.invoiceNumber || '').toString().toLowerCase();
    if (invNumA !== invNumB) {
      return invNumA.localeCompare(invNumB);
    }

    // 3. Sort by Invoice Date (chronological)
    const dateA = normalizeDate(a.invoiceDate);
    const dateB = normalizeDate(b.invoiceDate);

    if (dateA && dateB) {
      return new Date(dateA) - new Date(dateB);
    } else if (dateA) {
      return -1; // Dates with value come first
    } else if (dateB) {
      return 1;
    } else {
      return 0; // Both dates are invalid or missing
    }
  });
};

const groupInvoices = (invoices) => {
  const groups = new Map();
  invoices.forEach(invoice => {
    const key = getInvoiceKey(invoice);
    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key).push(invoice);
  });
  return groups;
};

// New robust reconciliation based on GSTIN + Invoice Value (tolerance) then Date check
const VALUE_TOLERANCE = 0.99; // ₹0.99 tolerance - accept if amount difference is less than ₹1

const buildIndex = (data) => {
  // Map<gstin, Map<value, Array<row>>>
  const index = new Map();
  data.forEach(row => {
    const gstin = (row.gstin || '').toString().trim().toUpperCase();
    const value = parseFloat(row.invoiceValue) || 0;
    if (!index.has(gstin)) index.set(gstin, new Map());
    const inner = index.get(gstin);
    if (!inner.has(value)) inner.set(value, []);
    inner.get(value).push({ row, used: false });
  });
  return index;
};

const performReconciliation = (gstr1Data, gstr2Data) => {
  const matched = [];
  const missingInGstr2 = [];
  const missingInGstr1 = [];
  const mismatched = [];

  // Validate and clean data before sorting
  const cleanedGstr1Data = gstr1Data.filter(invoice => 
    invoice && (invoice.gstin || invoice.invoiceNumber)
  );
  const cleanedGstr2Data = gstr2Data.filter(invoice => 
    invoice && (invoice.gstin || invoice.invoiceNumber)
  );

  // Sort data using robust sorting function
  const sortedGstr1Data = sortInvoicesRobust(cleanedGstr1Data);
  const sortedGstr2Data = sortInvoicesRobust(cleanedGstr2Data);


  console.log('Sorted GSTR-2 data sample:', sortedGstr2Data.slice(0, 3));

  // Build index for fast lookup
  const gstr2Index = buildIndex(sortedGstr2Data);

  sortedGstr1Data.forEach(gstr1Inv => {
    const gstinKey = (gstr1Inv.gstin || '').toString().trim().toUpperCase();
    const value1 = parseFloat(gstr1Inv.invoiceValue) || 0;

    if (!gstr2Index.has(gstinKey)) {
      missingInGstr2.push(gstr1Inv);
      return;
    }

    // search values within tolerance
    const inner = gstr2Index.get(gstinKey);
    let candidateEntry = null;
    for (const [valKey, arr] of inner.entries()) {
      const valNum = parseFloat(valKey);
      if (Math.abs(valNum - value1) <= VALUE_TOLERANCE) {
        const unused = arr.find(e => !e.used);
        if (unused) { candidateEntry = unused; break; }
      }
    }

    if (!candidateEntry) {
      missingInGstr2.push(gstr1Inv);
      return;
    }

    candidateEntry.used = true;
    const gstr2Inv = candidateEntry.row;

    if (compareDates(gstr1Inv.invoiceDate, gstr2Inv.invoiceDate)) {
      matched.push({ gstr1: gstr1Inv, gstr2: gstr2Inv });
    } else {
      const differences = { invoiceDate: { gstr1: gstr1Inv.invoiceDate, gstr2: gstr2Inv.invoiceDate } };
      mismatched.push({ gstr1: gstr1Inv, gstr2: gstr2Inv, differences });
    }
  });

  // Any remaining unused GSTR-2 rows are missing in GSTR-1
  gstr2Index.forEach(inner => {
    inner.forEach(arr => {
      arr.forEach(entry => {
        if (!entry.used) missingInGstr1.push(entry.row);
      });
    });
  });

  // Calculate summary statistics
  const totalInvoices = sortedGstr1Data.length + missingInGstr1.length;
  const totalValue = sortedGstr1Data.reduce((sum, inv) => sum + (parseFloat(inv.invoiceValue) || 0), 0);

  // Group zero tax bills (invoiceValue === taxableValue)
  const zeroTaxBills = [];
  function isZeroTax(inv) {
    return (
      typeof inv.invoiceValue !== 'undefined' &&
      typeof inv.taxableValue !== 'undefined' &&
      Number(inv.invoiceValue) === Number(inv.taxableValue)
    );
  }

  // Remove zero tax bills from matched, mismatched, missing
  function filterZeroTax(arr) {
    const zero = [];
    const rest = [];
    arr.forEach(inv => {
      if (isZeroTax(inv)) zero.push(inv);
      else rest.push(inv);
    });
    return { zero, rest };
  }

  // Filter from matched
  const { zero: zeroMatched, rest: filteredMatched } = filterZeroTax(matched);
  const { zero: zeroMiss1, rest: filteredMissingInGstr1 } = filterZeroTax(missingInGstr1);
  const { zero: zeroMiss2, rest: filteredMissingInGstr2 } = filterZeroTax(missingInGstr2);
  const { zero: zeroMismatched, rest: filteredMismatched } = filterZeroTax(mismatched);
  zeroTaxBills.push(...zeroMatched, ...zeroMiss1, ...zeroMiss2, ...zeroMismatched);

  return {
    matched: filteredMatched,
    missingInGstr2: filteredMissingInGstr2,
    missingInGstr1: filteredMissingInGstr1,
    mismatched: filteredMismatched,
    zeroTaxBills,
    summary: {
      totalInvoices,
      totalValue,
      matchedCount: filteredMatched.length,
      mismatchedCount: filteredMismatched.length,
      missingCount: filteredMissingInGstr1.length + filteredMissingInGstr2.length,
      zeroTaxCount: zeroTaxBills.length
    }
  };

};



// Normalize date string to a comparable format
const normalizeDate = (dateStr) => {
  if (!dateStr) return null;
  
  const cleanDate = dateStr.toString().trim();
  if (!cleanDate) return null;
  
  try {
    // Try to parse various date formats
    let parsedDate;
    
    // Handle DD-MMM-YYYY format (e.g., "02-May-2025")
    if (/^\d{1,2}-[A-Za-z]{3}-\d{4}$/.test(cleanDate)) {
      parsedDate = new Date(cleanDate);
    }
    // Handle DD/MM/YYYY format (e.g., "10/05/2025")
    else if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(cleanDate)) {
      const [day, month, year] = cleanDate.split('/');
      parsedDate = new Date(year, month - 1, day); // month is 0-indexed
    }
    // Handle MM/DD/YYYY format (e.g., "05/10/2025")
    else if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(cleanDate)) {
      // This is ambiguous, but we'll assume DD/MM/YYYY as default
      const [day, month, year] = cleanDate.split('/');
      parsedDate = new Date(year, month - 1, day);
    }
    // Handle YYYY-MM-DD format (e.g., "2025-05-10")
    else if (/^\d{4}-\d{1,2}-\d{1,2}$/.test(cleanDate)) {
      parsedDate = new Date(cleanDate);
    }
    // Handle DD.MM.YYYY format (e.g., "10.05.2025")
    else if (/^\d{1,2}\.\d{1,2}\.\d{4}$/.test(cleanDate)) {
      const [day, month, year] = cleanDate.split('.');
      parsedDate = new Date(year, month - 1, day);
    }
    // Try generic Date parsing as fallback
    else {
      parsedDate = new Date(cleanDate);
    }
    
    // Check if the date is valid
    if (isNaN(parsedDate.getTime())) {
      return null;
    }
    
    // Return normalized date string in YYYY-MM-DD format
    return parsedDate.toISOString().split('T')[0];
  } catch (error) {
    console.warn('Date parsing error for:', cleanDate, error);
    return null;
  }
};

// Compare two dates with format normalization
const compareDates = (date1Str, date2Str) => {
  const normalizedDate1 = normalizeDate(date1Str);
  const normalizedDate2 = normalizeDate(date2Str);
  
  // If either date couldn't be parsed, do string comparison
  if (!normalizedDate1 || !normalizedDate2) {
    return date1Str.toString().trim() === date2Str.toString().trim();
  }
  
  return normalizedDate1 === normalizedDate2;
};

// Compare invoice values and return differences
const compareInvoiceValues = (invoice1, invoice2) => {
  const differences = [];
  const tolerance = VALUE_TOLERANCE; // Use same tolerance as main reconciliation logic

  // Compare invoice values
  if (Math.abs((parseFloat(invoice1.invoiceValue) || 0) - (parseFloat(invoice2.invoiceValue) || 0)) > tolerance) {
    differences.push(`Invoice Value: ₹${invoice1.invoiceValue || 0} vs ₹${invoice2.invoiceValue || 0}`);
  }

  // Compare invoice dates with format normalization
  const date1 = (invoice1.invoiceDate || '').toString().trim();
  const date2 = (invoice2.invoiceDate || '').toString().trim();
  if (date1 && date2 && !compareDates(date1, date2)) {
    const normalizedDate1 = normalizeDate(date1);
    const normalizedDate2 = normalizeDate(date2);
    differences.push(`Invoice Date: ${date1} (${normalizedDate1 || 'invalid'}) vs ${date2} (${normalizedDate2 || 'invalid'})`);
  } else if (date1 !== date2 && (!date1 || !date2)) {
    // Handle cases where one date is missing
    differences.push(`Invoice Date: ${date1 || 'missing'} vs ${date2 || 'missing'}`);
  }

  // Compare taxable values if available
  if (invoice1.taxableValue !== undefined && invoice2.taxableValue !== undefined) {
    if (Math.abs((parseFloat(invoice1.taxableValue) || 0) - (parseFloat(invoice2.taxableValue) || 0)) > tolerance) {
      differences.push(`Taxable Value: ₹${invoice1.taxableValue || 0} vs ₹${invoice2.taxableValue || 0}`);
    }
  }

  // Compare tax amounts if available
  if (invoice1.igst !== undefined && invoice2.igst !== undefined) {
    if (Math.abs((parseFloat(invoice1.igst) || 0) - (parseFloat(invoice2.igst) || 0)) > tolerance) {
      differences.push(`IGST: ₹${invoice1.igst || 0} vs ₹${invoice2.igst || 0}`);
    }
  }

  if (invoice1.cgst !== undefined && invoice2.cgst !== undefined) {
    if (Math.abs((parseFloat(invoice1.cgst) || 0) - (parseFloat(invoice2.cgst) || 0)) > tolerance) {
      differences.push(`CGST: ₹${invoice1.cgst || 0} vs ₹${invoice2.cgst || 0}`);
    }
  }

  if (invoice1.sgst !== undefined && invoice2.sgst !== undefined) {
    if (Math.abs((parseFloat(invoice1.sgst) || 0) - (parseFloat(invoice2.sgst) || 0)) > tolerance) {
      differences.push(`SGST: ₹${invoice1.sgst || 0} vs ₹${invoice2.sgst || 0}`);
    }
  }

  return differences;
};
