import Decimal from 'decimal.js';
import {
  SubledgerEntry,
  SubledgerLine,
  GLJournal,
  GLJournalLine,
  APInvoice,
  APPayment,
  ARTransaction,
  ARReceipt,
  CashVoucher,
  Receipt,
  ICTransaction,
  FixedAsset,
  DepreciationRun,
} from './types';
import { getDb, updateDb, addAuditLog } from './storage';
import { getNextSequenceNumber } from './sequences';
import { getPeriodFromDate } from './dates';
import { isPeriodOpen } from './periods';
import { getAccountByCode, isControlAccount } from '../data/chartOfAccounts';
import { round2, addMoney, subMoney } from './currency';

export interface AccountingValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Validates a subledger entry before posting to GL
 */
export function validateSubledgerEntry(
  entry: SubledgerEntry,
  options?: { isManualJournal?: boolean; allowClosedPeriod?: boolean }
): AccountingValidationResult {
  const errors: string[] = [];

  if (!entry.lines || entry.lines.length < 2) {
    errors.push('Journal must contain at least two lines');
    return { valid: false, errors };
  }

  let totalDebit = new Decimal(0);
  let totalCredit = new Decimal(0);

  // Check period
  const period = getPeriodFromDate(entry.date);
  if (!options?.allowClosedPeriod && !isPeriodOpen(period)) {
    errors.push(`Period ${period} is not open for posting.`);
  }

  // Check lines
  entry.lines.forEach((line, idx) => {
    if (!line.businessUnit) {
      errors.push(`Line ${idx + 1}: Business Unit is required`);
    }
    if (!line.account) {
      errors.push(`Line ${idx + 1}: Account is required`);
    } else {
      const acct = getAccountByCode(line.account);
      if (!acct) {
        errors.push(`Line ${idx + 1}: Account code '${line.account}' does not exist in Chart of Accounts`);
      } else if (!acct.isActive) {
        errors.push(`Line ${idx + 1}: Account '${line.account} - ${acct.name}' is inactive`);
      } else if (options?.isManualJournal && acct.isControlAccount) {
        errors.push(`Line ${idx + 1}: Account '${line.account}' is a Subledger Control Account and cannot be used in manual journals`);
      }
    }

    const dr = new Decimal(line.debit || 0);
    const cr = new Decimal(line.credit || 0);

    if (dr.isNegative() || cr.isNegative()) {
      errors.push(`Line ${idx + 1}: Negative amounts are not allowed; use debit or credit`);
    }
    if (dr.isZero() && cr.isZero()) {
      errors.push(`Line ${idx + 1}: Amount cannot be zero`);
    }
    if (!dr.isZero() && !cr.isZero()) {
      errors.push(`Line ${idx + 1}: Line cannot have both Debit and Credit`);
    }

    totalDebit = totalDebit.plus(dr);
    totalCredit = totalCredit.plus(cr);
  });

  const diff = totalDebit.minus(totalCredit).abs();
  if (diff.greaterThan(0.005)) {
    errors.push(`Journal is out of balance by AED ${diff.toFixed(2)}. Debits (${totalDebit.toFixed(2)}) must equal Credits (${totalCredit.toFixed(2)}).`);
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Single source of truth: Post a Subledger Entry to General Ledger
 */
export function postToGL(
  entry: SubledgerEntry,
  meta: {
    createdBy: string;
    approvedBy: string;
    category: string;
    isManualJournal?: boolean;
    allowClosedPeriod?: boolean;
  }
): { success: boolean; journal?: GLJournal; errors?: string[] } {
  // Check if document already posted (idempotent)
  const db = getDb();
  if (entry.sourceDocumentNumber) {
    const existing = db.glJournals.find(
      (j) => j.lines.some((l) => l.sourceDocumentNumber === entry.sourceDocumentNumber) && j.status === 'Posted'
    );
    if (existing) {
      return { success: true, journal: existing };
    }
  }

  const validation = validateSubledgerEntry(entry, {
    isManualJournal: meta.isManualJournal,
    allowClosedPeriod: meta.allowClosedPeriod,
  });

  if (!validation.valid) {
    return { success: false, errors: validation.errors };
  }

  const journalNumber = getNextSequenceNumber('JV', 2026);
  const period = getPeriodFromDate(entry.date);
  const postedAt = new Date().toISOString();

  let totalDebit = 0;
  let totalCredit = 0;

  const glLines: GLJournalLine[] = entry.lines.map((l, idx) => {
    const debit = round2(l.debit || 0);
    const credit = round2(l.credit || 0);
    totalDebit = addMoney(totalDebit, debit);
    totalCredit = addMoney(totalCredit, credit);

    return {
      lineNumber: idx + 1,
      businessUnit: l.businessUnit,
      account: l.account,
      department: l.department,
      debit,
      credit,
      description: l.description || entry.description,
      sourceModule: entry.sourceModule,
      sourceDocumentNumber: entry.sourceDocumentNumber,
      sourceDocumentId: entry.sourceDocumentId,
    };
  });

  // Determine BU display
  const uniqueBUs = Array.from(new Set(glLines.map((l) => l.businessUnit)));
  const buDisplay = uniqueBUs.length === 1 ? uniqueBUs[0] : 'Multi-BU';

  const journal: GLJournal = {
    id: `GLJ-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
    number: journalNumber,
    period,
    journalDate: entry.date,
    businessUnit: buDisplay,
    sourceModule: entry.sourceModule,
    category: meta.category,
    description: entry.description,
    status: 'Posted',
    totalDebit,
    totalCredit,
    lines: glLines,
    createdBy: meta.createdBy,
    createdAt: postedAt,
    approvedBy: meta.approvedBy,
    postedAt,
  };

  updateDb((state) => {
    state.glJournals.unshift(journal);
  });

  addAuditLog({
    entityType: 'GLJournal',
    entityId: journal.id,
    action: 'POST',
    userId: meta.approvedBy,
    userName: meta.approvedBy,
    comments: `Posted journal ${journal.number} for ${entry.sourceDocumentNumber}`,
    details: { totalAmount: totalDebit, period, sourceModule: entry.sourceModule },
  });

  return { success: true, journal };
}

/**
 * Reverse a GL journal with an opposite entry
 */
export function reverseJournal(
  journalId: string,
  reason: string,
  reversalDate: string,
  user: string
): { success: boolean; reversedJournal?: GLJournal; error?: string } {
  const db = getDb();
  const orig = db.glJournals.find((j) => j.id === journalId);
  if (!orig) {
    return { success: false, error: 'Original journal not found' };
  }
  if (orig.status === 'Reversed') {
    return { success: false, error: 'Journal has already been reversed' };
  }

  const periodCheck = isPeriodOpen(getPeriodFromDate(reversalDate));
  if (!periodCheck) {
    return { success: false, error: `Reversal period is not open` };
  }

  // Create opposite lines (swap Dr and Cr)
  const revLines: SubledgerLine[] = orig.lines.map((l) => ({
    businessUnit: l.businessUnit,
    account: l.account,
    department: l.department,
    debit: l.credit,
    credit: l.debit,
    description: `Reversal of ${orig.number}: ${l.description}`,
  }));

  const subEntry: SubledgerEntry = {
    sourceModule: orig.sourceModule,
    sourceDocumentId: orig.id,
    sourceDocumentNumber: orig.number,
    businessUnit: orig.businessUnit,
    date: reversalDate,
    description: `Reversal of ${orig.number} - Reason: ${reason}`,
    lines: revLines,
  };

  const result = postToGL(subEntry, {
    createdBy: user,
    approvedBy: user,
    category: 'Reversal',
  });

  if (result.success && result.journal) {
    updateDb((state) => {
      const target = state.glJournals.find((j) => j.id === journalId);
      if (target) {
        target.status = 'Reversed';
        target.reversedJournalId = result.journal!.id;
      }
    });

    addAuditLog({
      entityType: 'GLJournal',
      entityId: orig.id,
      action: 'REVERSE',
      userId: user,
      userName: user,
      comments: `Reversed journal ${orig.number} via ${result.journal.number}. Reason: ${reason}`,
    });

    return { success: true, reversedJournal: result.journal };
  }

  return { success: false, error: result.errors?.join(', ') || 'Failed to post reversal journal' };
}

// -------------------------------------------------------------
// POSTING TEMPLATE BUILDERS (from Section 7)
// -------------------------------------------------------------

/**
 * AP Invoice Posting Template
 */
export function buildAPInvoiceAccounting(inv: APInvoice): SubledgerEntry {
  const lines: SubledgerLine[] = [];
  const bu = inv.businessUnit;

  let totalExpenseOrInventory = 0;
  let totalTax = 0;

  for (const line of inv.lines) {
    const lineAmt = round2(line.lineAmount);
    const taxAmt = round2(line.taxAmount);

    totalExpenseOrInventory = addMoney(totalExpenseOrInventory, lineAmt);
    totalTax = addMoney(totalTax, taxAmt);

    if (inv.invoiceType === 'Standard') {
      if (line.isCapital) {
        // Capital purchase: Dr 1610 Asset Clearing (or 1600 if CWIP)
        const acct = line.distributionAccount || '1610';
        lines.push({
          businessUnit: bu,
          account: acct,
          department: line.department,
          debit: lineAmt,
          credit: 0,
          description: line.description || `Capital purchase: ${line.assetCategory || 'Fixed Asset'}`,
        });
      } else if (line.poNumber) {
        // PO Matched: Dr GRNI 2010
        lines.push({
          businessUnit: bu,
          account: '2010', // GRNI
          department: line.department,
          debit: lineAmt,
          credit: 0,
          description: `GRNI PO match: ${line.description}`,
        });
      } else {
        // Non-PO Expense: Dr distribution account
        lines.push({
          businessUnit: bu,
          account: line.distributionAccount || '6290',
          department: line.department,
          debit: lineAmt,
          credit: 0,
          description: line.description,
        });
      }
    } else if (inv.invoiceType === 'Credit Memo') {
      // Reverse of invoice: Cr expense/clearing/GRNI
      const acct = line.distributionAccount || (line.isCapital ? '1610' : line.poNumber ? '2010' : '6290');
      lines.push({
        businessUnit: bu,
        account: acct,
        department: line.department,
        debit: 0,
        credit: lineAmt,
        description: `CM: ${line.description}`,
      });
    } else if (inv.invoiceType === 'Prepayment') {
      // Supplier Advance: Dr 1310
      lines.push({
        businessUnit: bu,
        account: '1310',
        department: line.department,
        debit: lineAmt,
        credit: 0,
        description: `Prepayment: ${line.description}`,
      });
    }
  }

  // VAT Input Recoverable 1400
  if (totalTax > 0) {
    if (inv.invoiceType === 'Standard' || inv.invoiceType === 'Prepayment') {
      lines.push({
        businessUnit: bu,
        account: '1400',
        debit: totalTax,
        credit: 0,
        description: `VAT 5% Input Recoverable - ${inv.supplierInvoiceNumber}`,
      });
    } else {
      // Credit memo: Cr 1400
      lines.push({
        businessUnit: bu,
        account: '1400',
        debit: 0,
        credit: totalTax,
        description: `VAT 5% Input Reversal - ${inv.supplierInvoiceNumber}`,
      });
    }
  }

  // AP Control Account 2000
  const grandTotal = round2(inv.totalAmount);
  if (inv.invoiceType === 'Standard' || inv.invoiceType === 'Prepayment') {
    lines.push({
      businessUnit: bu,
      account: '2000', // Trade Payables
      debit: 0,
      credit: grandTotal,
      description: `Trade Payables: ${inv.supplierName} (${inv.supplierInvoiceNumber})`,
    });
  } else {
    // Credit memo: Dr 2000
    lines.push({
      businessUnit: bu,
      account: '2000',
      debit: grandTotal,
      credit: 0,
      description: `Trade Payables Credit Memo: ${inv.supplierName}`,
    });
  }

  return {
    sourceModule: 'Payables',
    sourceDocumentId: inv.id,
    sourceDocumentNumber: inv.number,
    businessUnit: bu,
    date: inv.glDate || inv.invoiceDate,
    description: `AP Invoice ${inv.number} - ${inv.supplierName} - Ref: ${inv.supplierInvoiceNumber}`,
    lines,
  };
}

/**
 * AP Payment Posting Template
 * Dr 2000 Trade Payables / Cr 1020 Bank
 */
export function buildAPPaymentAccounting(pay: APPayment): SubledgerEntry {
  const bu = pay.businessUnit;
  const amt = round2(pay.amount);

  return {
    sourceModule: 'Payables',
    sourceDocumentId: pay.id,
    sourceDocumentNumber: pay.number,
    businessUnit: bu,
    date: pay.paymentDate,
    description: `AP Payment ${pay.number} to ${pay.supplierName} - Ref: ${pay.referenceNumber}`,
    lines: [
      {
        businessUnit: bu,
        account: '2000', // Trade Payables
        debit: amt,
        credit: 0,
        description: `Clear Trade Payables - ${pay.supplierName}`,
      },
      {
        businessUnit: bu,
        account: pay.bankAccountCode || '1020', // Operating Bank Account
        debit: 0,
        credit: amt,
        description: `Disbursement from Bank - ${pay.referenceNumber}`,
      },
    ],
  };
}

/**
 * AR Invoice Posting Template
 * Dr AR control (1100 / 1110 / 1120) / Dr 4090 discount / Cr Revenue (4000-4060) / Cr 2100 VAT Output
 */
export function buildARInvoiceAccounting(inv: ARTransaction): SubledgerEntry {
  const lines: SubledgerLine[] = [];
  const bu = inv.businessUnit;

  // Choose AR control account based on customer type
  let arControl = '1100'; // Patient
  if (inv.customerType === 'Insurance') arControl = '1110';
  else if (inv.customerType === 'Corporate') arControl = '1120';

  let totalRevenue = 0;
  let totalTax = 0;
  let totalDiscount = 0;

  for (const line of inv.lines) {
    const lineAmt = round2(line.amount);
    const taxAmt = round2(line.taxAmount);
    const discAmt = round2(line.insuranceDiscountAmount);

    totalRevenue = addMoney(totalRevenue, lineAmt);
    totalTax = addMoney(totalTax, taxAmt);
    totalDiscount = addMoney(totalDiscount, discAmt);

    // Cr Revenue
    lines.push({
      businessUnit: bu,
      account: line.revenueAccount || '4010',
      debit: 0,
      credit: lineAmt,
      description: line.description || `${line.serviceCategory} Revenue`,
    });
  }

  // Dr Contractual Discount 4090 if any
  if (totalDiscount > 0) {
    lines.push({
      businessUnit: bu,
      account: '4090',
      debit: totalDiscount,
      credit: 0,
      description: `Contractual Insurance Discount / Adjustment`,
    });
  }

  // Cr VAT Output Payable 2100 if any
  if (totalTax > 0) {
    lines.push({
      businessUnit: bu,
      account: '2100',
      debit: 0,
      credit: totalTax,
      description: `VAT 5% Output Payable`,
    });
  }

  // Dr AR Control with Net Receivable
  const netReceivable = round2(inv.totalAmount);
  lines.push({
    businessUnit: bu,
    account: arControl,
    debit: netReceivable,
    credit: 0,
    description: `Trade Receivable: ${inv.customerName} (${inv.patientName ? 'Patient: ' + inv.patientName : inv.claimReference || ''})`,
  });

  return {
    sourceModule: 'Receivables',
    sourceDocumentId: inv.id,
    sourceDocumentNumber: inv.number,
    businessUnit: bu,
    date: inv.glDate || inv.transactionDate,
    description: `AR Billing ${inv.number} - ${inv.customerName}`,
    lines,
  };
}

export const buildARTransactionAccounting = buildARInvoiceAccounting;

/**
 * AR Receipt Posting Template
 * Dr Bank 1030 (or Main Cash 1000) / Cr AR Control (1100/1110/1120)
 */
export function buildARReceiptAccounting(
  rct: ARReceipt,
  customerType: 'Insurance' | 'Corporate' | 'Patient' | 'Government' = 'Insurance'
): SubledgerEntry {
  const bu = rct.businessUnit;
  const amt = round2(rct.amount);

  let arControl = '1110';
  if (customerType === 'Patient') arControl = '1100';
  else if (customerType === 'Corporate' || customerType === 'Government') arControl = '1120';

  return {
    sourceModule: 'Receivables',
    sourceDocumentId: rct.id,
    sourceDocumentNumber: rct.number,
    businessUnit: bu,
    date: rct.glDate || rct.receiptDate,
    description: `AR Receipt ${rct.number} from ${rct.customerName} - Ref: ${rct.referenceNumber}`,
    lines: [
      {
        businessUnit: bu,
        account: rct.bankAccountCode || '1030', // Collections Bank Account
        debit: amt,
        credit: 0,
        description: `Collections deposit - ${rct.referenceNumber}`,
      },
      {
        businessUnit: bu,
        account: arControl,
        debit: 0,
        credit: amt,
        description: `Apply AR Receipt to ${rct.customerName}`,
      },
    ],
  };
}

/**
 * Goods Receipt (Supply Chain) Posting Template
 * Dr Inventory (1200/1210/1220/1230) / Cr GRNI 2010
 */
export function buildGoodsReceiptAccounting(rcv: Receipt, itemClassMap: Record<string, string>): SubledgerEntry {
  const bu = rcv.businessUnit;
  const lines: SubledgerLine[] = [];
  let totalReceipt = 0;

  for (const line of rcv.lines) {
    const amt = round2(line.lineAmount);
    totalReceipt = addMoney(totalReceipt, amt);

    // Determine inventory account based on item class
    const cls = itemClassMap[line.itemCode] || 'General';
    let invAccount = '1230'; // General Stores
    if (cls === 'Pharmaceutical') invAccount = '1200';
    else if (cls === 'Consumable') invAccount = '1210';
    else if (cls === 'Implants & Surgical') invAccount = '1220';

    lines.push({
      businessUnit: bu,
      account: line.account || invAccount,
      debit: amt,
      credit: 0,
      description: `Stock Receipt: ${line.description} (PO: ${line.poNumber})`,
    });
  }

  // Cr GRNI 2010
  lines.push({
    businessUnit: bu,
    account: '2010', // GRNI
    debit: 0,
    credit: totalReceipt,
    description: `Accrue Goods Received Not Invoiced (GRNI) - PO: ${rcv.poNumber}`,
  });

  return {
    sourceModule: 'Procurement/Inventory',
    sourceDocumentId: rcv.id,
    sourceDocumentNumber: rcv.number,
    businessUnit: bu,
    date: rcv.receiptDate,
    description: `Goods Receipt ${rcv.number} - PO: ${rcv.poNumber} from ${rcv.supplierName}`,
    lines,
  };
}

export function buildReceiptAccounting(rcv: Receipt): SubledgerEntry {
  const db = getDb();
  const classMap: Record<string, string> = {};
  (db.items || []).forEach((it) => {
    classMap[it.code] = it.itemClass;
  });
  return buildGoodsReceiptAccounting(rcv, classMap);
}


/**
 * Fixed Asset Capitalisation Posting Template
 * Dr Asset Cost (1710-1770) / Cr Asset Clearing 1610
 */
export function buildAssetCapitalisationAccounting(asset: FixedAsset, user: string): SubledgerEntry {
  const cost = round2(asset.cost);
  return {
    sourceModule: 'Fixed Assets',
    sourceDocumentId: asset.id,
    sourceDocumentNumber: asset.tagNumber,
    businessUnit: asset.businessUnit,
    date: asset.inServiceDate,
    description: `Capitalise Asset ${asset.tagNumber}: ${asset.name}`,
    lines: [
      {
        businessUnit: asset.businessUnit,
        account: asset.costAccount,
        department: asset.department,
        debit: cost,
        credit: 0,
        description: `Capitalise ${asset.name} (${asset.tagNumber})`,
      },
      {
        businessUnit: asset.businessUnit,
        account: '1610', // Asset Clearing
        department: asset.department,
        debit: 0,
        credit: cost,
        description: `Relieve Asset Clearing for ${asset.tagNumber}`,
      },
    ],
  };
}

/**
 * Monthly Depreciation Run Posting Template
 * Dr 6300 Depreciation Expense / Cr 1810-1870 Accumulated Depreciation
 */
export function buildDepreciationRunAccounting(run: DepreciationRun): SubledgerEntry {
  const lines: SubledgerLine[] = [];
  const bu = run.businessUnit === 'All' ? 'Multi-BU' : run.businessUnit;

  for (const line of run.lines) {
    const amt = round2(line.depreciationAmount);
    if (amt <= 0) continue;

    // Dr 6300
    lines.push({
      businessUnit: line.businessUnit,
      account: line.depExpenseAccount || '6300',
      debit: amt,
      credit: 0,
      description: `Depreciation ${run.period}: ${line.assetName} (${line.assetTag})`,
    });

    // Cr Accum Dep
    lines.push({
      businessUnit: line.businessUnit,
      account: line.accumDepAccount,
      debit: 0,
      credit: amt,
      description: `Accum Dep ${run.period}: ${line.assetName} (${line.assetTag})`,
    });
  }

  return {
    sourceModule: 'Depreciation',
    sourceDocumentId: run.id,
    sourceDocumentNumber: `DEP-${run.period}`,
    businessUnit: bu,
    date: run.runDate,
    description: `Monthly Depreciation Run for ${run.period}`,
    lines,
  };
}

/**
 * Petty Cash Expense Voucher Posting Template
 * Dr Expense / Dr 1400 (if VAT) / Cr 1010 Petty Cash
 */
export function buildCashVoucherAccounting(v: CashVoucher): SubledgerEntry {
  const bu = v.businessUnit;
  const lines: SubledgerLine[] = [];
  const netAmt = subMoney(v.amount, v.taxAmount);
  const taxAmt = round2(v.taxAmount);
  const cashAcct = v.type === 'PettyCash' ? '1010' : '1000';

  // Dr Expense
  lines.push({
    businessUnit: bu,
    account: v.expenseAccount,
    department: v.department,
    debit: netAmt,
    credit: 0,
    description: v.description,
  });

  // Dr VAT if taxable
  if (taxAmt > 0) {
    lines.push({
      businessUnit: bu,
      account: '1400',
      debit: taxAmt,
      credit: 0,
      description: `VAT 5% Input Recoverable - ${v.number}`,
    });
  }

  // Cr Cash / Petty Cash
  lines.push({
    businessUnit: bu,
    account: cashAcct,
    debit: 0,
    credit: round2(v.amount),
    description: `${v.type === 'PettyCash' ? 'Petty Cash' : 'Main Cash'} disbursement to ${v.payee}`,
  });

  return {
    sourceModule: 'Cash Management',
    sourceDocumentId: v.id,
    sourceDocumentNumber: v.number,
    businessUnit: bu,
    date: v.date,
    description: `${v.type === 'PettyCash' ? 'Petty Cash Voucher' : 'Main Cash Expense'} ${v.number} - ${v.payee}`,
    lines,
  };
}

/**
 * Intercompany Invoice Posting Template
 * Provider: Dr 1500 (due from receiver) / Cr 4900 (or inventory/asset)
 * Receiver: Dr Expense/Inventory/Asset / Cr 2500 (due to provider)
 */
export function buildIntercompanyAccounting(ic: ICTransaction): SubledgerEntry {
  const lines: SubledgerLine[] = [];
  const tot = round2(ic.totalAmount);

  for (const line of ic.lines) {
    const amt = round2(line.amount);

    // Provider Side: Cr Provider Account (e.g. 4900 IC Revenue or 1200 Inventory)
    lines.push({
      businessUnit: ic.providerBU,
      account: line.providerAccount || '4900',
      debit: 0,
      credit: amt,
      description: `IC Recharge to ${ic.receiverBU}: ${line.description}`,
    });

    // Receiver Side: Dr Receiver Account (e.g. 6400 IC Expense or 1200 Inventory)
    lines.push({
      businessUnit: ic.receiverBU,
      account: line.receiverAccount || '6400',
      debit: amt,
      credit: 0,
      description: `IC Recharge from ${ic.providerBU}: ${line.description}`,
    });
  }

  // Provider balancing: Dr 1500 Intercompany Receivable
  lines.push({
    businessUnit: ic.providerBU,
    account: '1500',
    debit: tot,
    credit: 0,
    description: `Due from ${ic.receiverBU} (IC Ref: ${ic.number})`,
  });

  // Receiver balancing: Cr 2500 Intercompany Payable
  lines.push({
    businessUnit: ic.receiverBU,
    account: '2500',
    debit: 0,
    credit: tot,
    description: `Due to ${ic.providerBU} (IC Ref: ${ic.number})`,
  });

  return {
    sourceModule: 'Intercompany',
    sourceDocumentId: ic.id,
    sourceDocumentNumber: ic.number,
    businessUnit: 'Multi-BU',
    date: ic.date,
    description: `Intercompany ${ic.type} ${ic.number}: ${ic.providerBU} ➔ ${ic.receiverBU}`,
    lines,
  };
}
