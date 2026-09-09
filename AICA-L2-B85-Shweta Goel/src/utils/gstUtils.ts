export const INDIAN_STATE_CODES: Record<string, string> = {
  '01': 'Jammu & Kashmir',
  '02': 'Himachal Pradesh',
  '03': 'Punjab',
  '04': 'Chandigarh',
  '05': 'Uttarakhand',
  '06': 'Haryana',
  '07': 'Delhi',
  '08': 'Rajasthan',
  '09': 'Uttar Pradesh',
  '10': 'Bihar',
  '11': 'Sikkim',
  '12': 'Arunachal Pradesh',
  '13': 'Nagaland',
  '14': 'Manipur',
  '15': 'Mizoram',
  '16': 'Tripura',
  '17': 'Meghalaya',
  '18': 'Assam',
  '19': 'West Bengal',
  '20': 'Jharkhand',
  '21': 'Odisha',
  '22': 'Chhattisgarh',
  '23': 'Madhya Pradesh',
  '24': 'Gujarat',
  '26': 'Dadra & Nagar Haveli and Daman & Diu',
  '27': 'Maharashtra',
  '29': 'Karnataka',
  '30': 'Goa',
  '31': 'Lakshadweep',
  '32': 'Kerala',
  '33': 'Tamil Nadu',
  '34': 'Puducherry',
  '35': 'Andaman & Nicobar Islands',
  '36': 'Telangana',
  '37': 'Andhra Pradesh',
  '38': 'Ladakh',
  '97': 'Other Territory',
  '99': 'Centre Jurisdiction'
};

/**
 * Validates 15-character Indian GSTIN format:
 * Pattern: 2-digit State Code + 10-digit PAN (5 alpha + 4 numeric + 1 alpha) + 1-digit entity code (1-9 or A-Z) + 'Z' + 1 checksum digit (alpha or numeric)
 */
export function validateGSTIN(gstin: string): { isValid: boolean; stateCode: string; stateName: string; pan: string; reason?: string } {
  if (!gstin) {
    return { isValid: false, stateCode: '', stateName: '', pan: '', reason: 'GSTIN is empty' };
  }

  const clean = gstin.trim().toUpperCase();
  if (clean.length !== 15) {
    return { isValid: false, stateCode: '', stateName: '', pan: '', reason: `Invalid length: ${clean.length} characters (Must be 15)` };
  }

  const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
  const isValidSyntax = gstinRegex.test(clean);

  const stateCode = clean.substring(0, 2);
  const stateName = INDIAN_STATE_CODES[stateCode] || 'Unknown State';
  const pan = clean.substring(2, 12);

  if (!isValidSyntax) {
    return {
      isValid: false,
      stateCode,
      stateName,
      pan,
      reason: 'Syntax error: format must be 2-digit state + 10-char PAN + 1-entity + Z + 1-checksum'
    };
  }

  if (!INDIAN_STATE_CODES[stateCode]) {
    return {
      isValid: false,
      stateCode,
      stateName: 'Invalid State Code',
      pan,
      reason: `Unrecognized state code prefix '${stateCode}'`
    };
  }

  return { isValid: true, stateCode, stateName, pan };
}

/**
 * Validates 10-digit Indian Permanent Account Number (PAN):
 * 5 letters + 4 digits + 1 letter (e.g. ABCDE1234F)
 */
export function validatePAN(pan: string): boolean {
  if (!pan) return false;
  return /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(pan.trim().toUpperCase());
}

/**
 * Validates 10-digit Tax Deduction and Collection Account Number (TAN):
 * 4 letters + 5 digits + 1 letter (e.g. MUMB12345E)
 */
export function validateTAN(tan: string): boolean {
  if (!tan) return false;
  return /^[A-Z]{4}[0-9]{5}[A-Z]{1}$/.test(tan.trim().toUpperCase());
}

/**
 * Checks Place of Supply rule:
 * If Supplier State == Place of Supply State -> INTRA-STATE (CGST + SGST required, IGST = 0)
 * If Supplier State != Place of Supply State -> INTER-STATE (IGST required, CGST = 0, SGST = 0)
 */
export function evaluatePlaceOfSupplyRule(
  supplierStateCode: string,
  posStateCode: string,
  cgst: number,
  sgst: number,
  igst: number
) {
  const isIntraState = supplierStateCode && posStateCode && supplierStateCode === posStateCode;
  const isInterState = supplierStateCode && posStateCode && supplierStateCode !== posStateCode;

  const hasCgstSgst = (cgst > 0 || sgst > 0);
  const hasIgst = igst > 0;

  if (isIntraState) {
    if (hasIgst && !hasCgstSgst) {
      return {
        compliant: false,
        severity: 'FAIL' as const,
        message: `Intra-state supply (State code ${supplierStateCode} -> ${posStateCode}) requires CGST & SGST, but IGST was charged.`,
        impact: 'Incorrect tax ledgering; Input Tax Credit (ITC) claim may be rejected under GST Section 16(2).',
        remedy: 'Issue Credit Note and re-bill with correct CGST + SGST components.'
      };
    }
    if (cgst !== sgst) {
      return {
        compliant: false,
        severity: 'WARNING' as const,
        message: `CGST (₹${cgst}) and SGST (₹${sgst}) amounts must be equal for intra-state supply.`,
        impact: 'GSTR-3B auto-population discrepancy.',
        remedy: 'Verify tax breakdown in invoice line items.'
      };
    }
    return {
      compliant: true,
      severity: 'PASS' as const,
      message: `Intra-state transaction correctly charged with CGST + SGST (${INDIAN_STATE_CODES[supplierStateCode] || supplierStateCode}).`,
      impact: 'Compliant for GSTR-1 and GSTR-3B filing.',
      remedy: 'None required.'
    };
  }

  if (isInterState) {
    if (hasCgstSgst && !hasIgst) {
      return {
        compliant: false,
        severity: 'FAIL' as const,
        message: `Inter-state supply (Supplier ${supplierStateCode} -> PoS ${posStateCode}) requires IGST, but CGST + SGST were charged.`,
        impact: 'Severe compliance violation under IGST Act Sec 7; Recipient cannot claim ITC in their state.',
        remedy: 'Supplier must cancel invoice or issue credit note and reissue with IGST.'
      };
    }
    return {
      compliant: true,
      severity: 'PASS' as const,
      message: `Inter-state transaction correctly charged with IGST (${supplierStateCode} -> ${posStateCode}).`,
      impact: 'Valid IGST ITC claim for recipient.',
      remedy: 'None required.'
    };
  }

  return {
    compliant: true,
    severity: 'WARNING' as const,
    message: 'State codes could not be determined unambiguously.',
    impact: 'Unable to fully automate Place of Supply validation.',
    remedy: 'Verify 2-digit state prefixes manually on invoice.'
  };
}

/**
 * Standard TDS sections library for Indian Income Tax
 */
export const TDS_SECTIONS_MASTER = [
  {
    code: '194C',
    name: 'Payment to Contractors / Sub-contractors',
    indHufRate: 1.0,
    otherRate: 2.0,
    singleThreshold: 30000,
    aggregateThreshold: 100000,
    description: 'Civil works, advertising, transport, catering, manufacturing through job work.'
  },
  {
    code: '194J(a)',
    name: 'Fees for Technical Services (FTS) / Call Center',
    indHufRate: 2.0,
    otherRate: 2.0,
    singleThreshold: 30000,
    aggregateThreshold: 30000,
    description: 'Technical services, software development, BPO operations, routine IT maintenance.'
  },
  {
    code: '194J(b)',
    name: 'Fees for Professional Services & Royalty',
    indHufRate: 10.0,
    otherRate: 10.0,
    singleThreshold: 30000,
    aggregateThreshold: 30000,
    description: 'Legal, CA/Audit, medical, engineering, architecture, interior decoration, royalty & director fees.'
  },
  {
    code: '194H',
    name: 'Commission & Brokerage',
    indHufRate: 5.0,
    otherRate: 5.0,
    singleThreshold: 15000,
    aggregateThreshold: 15000,
    description: 'Agent commissions, real estate brokerage, consignment sales.'
  },
  {
    code: '194I(a)',
    name: 'Rent - Plant, Machinery or Equipment',
    indHufRate: 2.0,
    otherRate: 2.0,
    singleThreshold: 240000,
    aggregateThreshold: 240000,
    description: 'Lease or hire of generators, machinery, commercial apparatus.'
  },
  {
    code: '194I(b)',
    name: 'Rent - Land, Building or Furniture',
    indHufRate: 10.0,
    otherRate: 10.0,
    singleThreshold: 240000,
    aggregateThreshold: 240000,
    description: 'Office rent, warehouse lease, commercial showroom rentals.'
  },
  {
    code: '194Q',
    name: 'TDS on Purchase of Goods exceeding ₹50 Lakhs',
    indHufRate: 0.1,
    otherRate: 0.1,
    singleThreshold: 5000000,
    aggregateThreshold: 5000000,
    description: 'Buyer whose turnover > ₹10 Cr purchasing goods > ₹50L from a resident seller.'
  },
  {
    code: '194A',
    name: 'Interest other than Interest on Securities',
    indHufRate: 10.0,
    otherRate: 10.0,
    singleThreshold: 5000,
    aggregateThreshold: 40000,
    description: 'Unsecured loan interest, NBFC interest, inter-corporate deposits.'
  }
];
