import {
  BankTransaction,
  Invoice,
  Customer,
  PaymentAllocation,
  MatchRuleType,
  MatchConfidenceLevel,
  ReconciliationSettings,
  MatchSuggestion,
  ReconciliationMatch
} from '../types';

export type { MatchSuggestion, ReconciliationMatch };

/**
 * Normalizes string for fuzzy customer and invoice comparisons
 */
export function normalizeText(text: string): string {
  if (!text) return '';
  return text
    .toUpperCase()
    .replace(/\b(PVT|PRIVATE|LTD|LIMITED|CORP|CORPORATION|LLP|INC|ENTERPRISE|ENTERPRISES|SERVICES|TRADERS|SOLUTIONS)\b/g, '')
    .replace(/[^A-Z0-9]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Bank Narration Parser:
 * Extracts Invoice Number, Reference Number, and potential customer from raw narration
 */
export interface ParsedNarration {
  invoiceNumber: string | null;
  referenceNumber: string | null;
  detectedCustomerText: string | null;
  matchedCustomer: Customer | null;
}

export function parseBankNarration(narration: string, customers: Customer[]): ParsedNarration {
  if (!narration) {
    return { invoiceNumber: null, referenceNumber: null, detectedCustomerText: null, matchedCustomer: null };
  }

  const upper = narration.toUpperCase();

  // 1. Extract Invoice Number Pattern (e.g. INV-2026-001, INV1023, BILL-102, #INV-04)
  const invPatterns = [
    /\b(INV[-_/\s]?[0-9]{3,8}[A-Z0-9-]*)\b/i,
    /\b(BILL[-_/\s]?[0-9]{3,8}[A-Z0-9-]*)\b/i,
    /\b([A-Z]{2,4}[-_/][0-9]{3,8})\b/i,
    /INVOICE\s*(?:NO|NUM|NUMBER)?\s*[:#-]?\s*([A-Z0-9-_/]+)/i
  ];

  let detectedInvoice: string | null = null;
  for (const regex of invPatterns) {
    const match = upper.match(regex);
    if (match && match[1]) {
      detectedInvoice = match[1].replace(/\s+/g, '');
      break;
    }
  }

  // 2. Extract Reference / UTR Number (e.g., NEFT-N12345, CMS..., RTGS..., UPI/402...)
  const refPatterns = [
    /\b(UTR[:\s]*[A-Z0-9]+)\b/i,
    /\b(NEFT[:\s-]*[A-Z0-9]+)\b/i,
    /\b(RTGS[:\s-]*[A-Z0-9]+)\b/i,
    /\b(UPI\/[0-9]{10,14})\b/i,
    /\b(IMPS[:\s-]*[0-9]+)\b/i,
    /\b(CMS[0-9]+)\b/i,
    /\b(N[0-9]{6,12})\b/i
  ];

  let detectedRef: string | null = null;
  for (const regex of refPatterns) {
    const match = upper.match(regex);
    if (match && match[1]) {
      detectedRef = match[1];
      break;
    }
  }

  // 3. Match Customer against Name and Aliases
  let matchedCustomer: Customer | null = null;
  const normalizedNarration = normalizeText(narration);

  for (const cust of customers) {
    const custNorm = normalizeText(cust.name);
    if (custNorm.length >= 3 && normalizedNarration.includes(custNorm)) {
      matchedCustomer = cust;
      break;
    }
    // Check aliases
    if (cust.aliases && cust.aliases.length > 0) {
      for (const alias of cust.aliases) {
        const aliasNorm = normalizeText(alias);
        if (aliasNorm.length >= 3 && normalizedNarration.includes(aliasNorm)) {
          matchedCustomer = cust;
          break;
        }
      }
    }
    if (matchedCustomer) break;
  }

  return {
    invoiceNumber: detectedInvoice,
    referenceNumber: detectedRef,
    detectedCustomerText: null,
    matchedCustomer
  };
}

/**
 * Runs the Multi-Rule Reconciliation Engine across unallocated bank transactions and unpaid invoices
 */
type MatchCandidate = Omit<ReconciliationMatch, 'id' | 'bankTransaction' | 'invoice' | 'tdsAdjustment' | 'differenceAmount'>;

export function runReconciliationEngine(
  transactions: BankTransaction[],
  invoices: Invoice[],
  customers: Customer[],
  settings: ReconciliationSettings
): MatchSuggestion[] {
  const suggestions: MatchSuggestion[] = [];

  // Filter for credit customer receipts that still have unallocated balances
  const openCredits = transactions.filter(
    tx => tx.isCredit && tx.unallocatedAmount > 0 && tx.allocationStatus !== 'Fully Allocated'
  );

  // Filter for invoices with positive balance
  const openInvoices = invoices.filter(
    inv => inv.balance > 0 && inv.status !== 'Cancelled' && inv.status !== 'Written Off'
  );

  for (const tx of openCredits) {
    const parsed = parseBankNarration(tx.narration, customers);
    const txAmount = tx.unallocatedAmount;
    const txCustomer = parsed.matchedCustomer || (tx.customerId ? customers.find(c => c.id === tx.customerId) : null);

    let bestMatch: MatchCandidate | null = null;

    // RULE 1: Direct Invoice Number Match in Narration (95-100% confidence)
    if (parsed.invoiceNumber) {
      const cleanParsedInv = parsed.invoiceNumber.replace(/[^A-Z0-9]/gi, '');
      const matchedInv = openInvoices.find(inv => {
        const cleanInv = inv.invoiceNumber.replace(/[^A-Z0-9]/gi, '');
        return cleanInv.includes(cleanParsedInv) || cleanParsedInv.includes(cleanInv);
      });

      if (matchedInv) {
        let confidence = 98;
        let rule: MatchRuleType = 'Rule 1: Invoice Number Match';
        let tdsAdj = 0;
        let shortAmt = 0;
        let excessAmt = 0;

        // Check if amount perfectly settles the net receivable (Rule 7 TDS check)
        const netExpected = matchedInv.netReceivable;
        if (Math.abs(txAmount - netExpected) <= settings.amountTolerance) {
          rule = 'Rule 7: TDS Adjustment Match';
          tdsAdj = matchedInv.expectedTds;
        } else if (txAmount < matchedInv.balance) {
          shortAmt = matchedInv.balance - txAmount;
        } else if (txAmount > matchedInv.balance) {
          excessAmt = txAmount - matchedInv.balance;
        }

        bestMatch = {
          transaction: tx,
          matchedInvoice: matchedInv,
          confidenceScore: confidence,
          confidenceLevel: 'High',
          ruleApplied: rule,
          allocatedAmount: Math.min(txAmount, matchedInv.balance),
          tdsDeducted: tdsAdj,
          shortPaymentAmount: shortAmt,
          excessPaymentAmount: excessAmt,
          shortPaymentReason: shortAmt > 0 && shortAmt === matchedInv.expectedTds ? 'TDS' : undefined,
          excessHandling: excessAmt > 0 ? 'Advance' : undefined,
          explanation: `Invoice ${matchedInv.invoiceNumber} found directly in bank narration.`
        };
      }
    }

    // RULE 7: TDS Adjustment Match (When payment matches Invoice Total - Expected TDS)
    if (!bestMatch && txCustomer) {
      const tdsMatchInv = openInvoices.find(inv => {
        if (inv.customerId !== txCustomer.id) return false;
        const diff = Math.abs(txAmount - inv.netReceivable);
        return diff <= settings.amountTolerance;
      });

      if (tdsMatchInv) {
        bestMatch = {
          transaction: tx,
          matchedInvoice: tdsMatchInv,
          confidenceScore: 96,
          confidenceLevel: 'High',
          ruleApplied: 'Rule 7: TDS Adjustment Match',
          allocatedAmount: txAmount,
          tdsDeducted: tdsMatchInv.expectedTds,
          shortPaymentAmount: 0,
          excessPaymentAmount: 0,
          explanation: `Payment ₹${txAmount} matches invoice net receivable after expected TDS of ₹${tdsMatchInv.expectedTds} (Total ₹${tdsMatchInv.totalInvoiceValue}).`
        };
      }
    }

    // RULE 2: Exact Customer + Exact Amount Match
    if (!bestMatch && txCustomer) {
      const exactInv = openInvoices.find(inv => {
        if (inv.customerId !== txCustomer.id) return false;
        return Math.abs(txAmount - inv.balance) <= settings.amountTolerance;
      });

      if (exactInv) {
        bestMatch = {
          transaction: tx,
          matchedInvoice: exactInv,
          confidenceScore: 94,
          confidenceLevel: 'High',
          ruleApplied: 'Rule 2: Exact Customer + Amount',
          allocatedAmount: txAmount,
          tdsDeducted: 0,
          shortPaymentAmount: 0,
          excessPaymentAmount: 0,
          explanation: `Exact balance match (₹${exactInv.balance}) for customer ${txCustomer.name}.`
        };
      }
    }

    // RULE 3: Customer + Amount + Date Proximity
    if (!bestMatch && txCustomer) {
      const proximityInv = openInvoices.find(inv => {
        if (inv.customerId !== txCustomer.id) return false;
        const daysDiff = Math.abs(
          (new Date(tx.transactionDate).getTime() - new Date(inv.dueDate).getTime()) / (1000 * 60 * 60 * 24)
        );
        return daysDiff <= settings.dateToleranceDays && Math.abs(txAmount - inv.balance) <= settings.amountTolerance;
      });

      if (proximityInv) {
        bestMatch = {
          transaction: tx,
          matchedInvoice: proximityInv,
          confidenceScore: 88,
          confidenceLevel: 'Medium',
          ruleApplied: 'Rule 3: Customer + Amount + Date Proximity',
          allocatedAmount: txAmount,
          tdsDeducted: 0,
          shortPaymentAmount: 0,
          excessPaymentAmount: 0,
          explanation: `Customer match and payment date is within ${settings.dateToleranceDays} days of invoice due date.`
        };
      }
    }

    // RULE 6 / 8: Partial Payment (Customer matched, payment is lower than outstanding)
    if (!bestMatch && txCustomer) {
      // Pick the oldest unpaid invoice for this customer
      const customerInvoices = openInvoices
        .filter(inv => inv.customerId === txCustomer.id)
        .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime());

      if (customerInvoices.length > 0) {
        const targetInv = customerInvoices[0];
        if (txAmount < targetInv.balance) {
          const short = targetInv.balance - txAmount;
          bestMatch = {
            transaction: tx,
            matchedInvoice: targetInv,
            confidenceScore: 82,
            confidenceLevel: 'Medium',
            ruleApplied: 'Rule 6: Partial Payment',
            allocatedAmount: txAmount,
            tdsDeducted: 0,
            shortPaymentAmount: short,
            excessPaymentAmount: 0,
            shortPaymentReason: short <= (targetInv.expectedTds || 0) ? 'TDS' : 'Other',
            explanation: `Partial receipt of ₹${txAmount} towards oldest unpaid invoice ${targetInv.invoiceNumber} (Balance ₹${targetInv.balance}).`
          };
        } else if (txAmount > targetInv.balance) {
          const excess = txAmount - targetInv.balance;
          bestMatch = {
            transaction: tx,
            matchedInvoice: targetInv,
            confidenceScore: 80,
            confidenceLevel: 'Medium',
            ruleApplied: 'Rule 9: Excess Payment',
            allocatedAmount: targetInv.balance,
            tdsDeducted: 0,
            shortPaymentAmount: 0,
            excessPaymentAmount: excess,
            excessHandling: 'Advance',
            explanation: `Payment exceeds invoice ${targetInv.invoiceNumber} balance by ₹${excess}; candidate for advance allocation.`
          };
        }
      }
    }

    if (bestMatch) {
      const enrichedMatch: MatchSuggestion = {
        ...bestMatch,
        id: `sug-${tx.id}-${bestMatch.matchedInvoice.id}`,
        bankTransaction: tx,
        invoice: bestMatch.matchedInvoice,
        tdsAdjustment: bestMatch.tdsDeducted,
        differenceAmount: bestMatch.shortPaymentAmount || bestMatch.excessPaymentAmount,
        differenceReason: bestMatch.shortPaymentReason || bestMatch.excessHandling
      };
      suggestions.push(enrichedMatch);
    }
  }

  return suggestions;
}

/**
 * Simplified narration parser for testing and utility functions
 */
export function parseNarration(narration: string): {
  extractedInvoiceNumber: string | null;
  matchedCustomerAlias: string | null;
  extractedReference: string | null;
} {
  const upper = (narration || '').toUpperCase();

  // Pattern for invoice
  const invMatch = upper.match(/\b(INV[-_/\s]?[0-9]{3,8}[A-Z0-9-]*)\b/i) ||
    upper.match(/\b(BILL[-_/\s]?[0-9]{3,8}[A-Z0-9-]*)\b/i);

  // Pattern for UTR / Ref
  const refMatch = upper.match(/\b(HDFC[0-9]+|ICICI[0-9]+|SBIN[0-9]+|CMS[0-9]+|NEFT-[A-Z0-9]+|RTGS-[A-Z0-9]+)\b/i);

  // Pattern for customer alias
  let alias: string | null = null;
  if (upper.includes('INFOSYS')) alias = 'INFOSYS';
  else if (upper.includes('TCS')) alias = 'TCS';
  else if (upper.includes('WIPRO')) alias = 'WIPRO';
  else if (upper.includes('HCL')) alias = 'HCL';
  else if (upper.includes('TECHM') || upper.includes('TECH MAHINDRA')) alias = 'TECH MAHINDRA';

  return {
    extractedInvoiceNumber: invMatch ? invMatch[1].replace(/\s+/g, '') : null,
    matchedCustomerAlias: alias,
    extractedReference: refMatch ? refMatch[1] : null
  };
}

