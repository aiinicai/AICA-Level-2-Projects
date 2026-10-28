/**
 * MediCore Connect - Central Document Link Registry & Resolver
 * Section 5: Maps every document number to route, type, related records & accounting
 */

import { getDb } from './storage';

export interface DocRouteInfo {
  prefix: string;
  entityType: string;
  route: string;
  label: string;
}

export const PREFIX_REGISTRY: Record<string, DocRouteInfo> = {
  REQ: { prefix: 'REQ', entityType: 'Requisition', route: '#/procurement/requisitions', label: 'Purchase Requisition' },
  PO: { prefix: 'PO', entityType: 'PurchaseOrder', route: '#/procurement/orders', label: 'Purchase Order' },
  RCV: { prefix: 'RCV', entityType: 'Receipt', route: '#/supply-chain/receiving', label: 'Goods Receipt Note (GRN)' },
  STO: { prefix: 'STO', entityType: 'StockTransfer', route: '#/supply-chain/inventory', label: 'Stock Transfer' },
  ADJ: { prefix: 'ADJ', entityType: 'Adjustment', route: '#/supply-chain/inventory', label: 'Inventory Adjustment' },
  CNS: { prefix: 'CNS', entityType: 'Consumption', route: '#/supply-chain/inventory', label: 'Consumption Entry' },
  PINV: { prefix: 'PINV', entityType: 'APInvoice', route: '#/payables/invoices', label: 'Payables Invoice' },
  PCM: { prefix: 'PCM', entityType: 'APCreditMemo', route: '#/payables/invoices', label: 'AP Credit Memo' },
  PAY: { prefix: 'PAY', entityType: 'APPayment', route: '#/payables/payments', label: 'Payables Payment' },
  RINV: { prefix: 'RINV', entityType: 'ARInvoice', route: '#/receivables/billing', label: 'Receivables Invoice' },
  RCM: { prefix: 'RCM', entityType: 'ARCreditMemo', route: '#/receivables/billing', label: 'AR Credit Memo' },
  RCT: { prefix: 'RCT', entityType: 'ARReceipt', route: '#/receivables/billing', label: 'AR Customer Receipt' },
  PCV: { prefix: 'PCV', entityType: 'PettyCashVoucher', route: '#/cash/petty-cash', label: 'Petty Cash Voucher' },
  MCV: { prefix: 'MCV', entityType: 'MainCashVoucher', route: '#/cash/petty-cash', label: 'Main Cash Voucher' },
  CTR: { prefix: 'CTR', entityType: 'CashTransfer', route: '#/cash/petty-cash', label: 'Cash Transfer' },
  BST: { prefix: 'BST', entityType: 'BankStatement', route: '#/cash/bank-reconciliation', label: 'Bank Statement' },
  FA: { prefix: 'FA', entityType: 'FixedAsset', route: '#/fixed-assets/assets', label: 'Fixed Asset' },
  FAB: { prefix: 'FAB', entityType: 'AssetBatch', route: '#/fixed-assets/assets', label: 'Asset Addition Batch' },
  ICI: { prefix: 'ICI', entityType: 'ICTransaction', route: '#/intercompany/transactions', label: 'Intercompany Invoice' },
  ICC: { prefix: 'ICC', entityType: 'ICTransaction', route: '#/intercompany/transactions', label: 'Intercompany Credit Note' },
  ICJ: { prefix: 'ICJ', entityType: 'ICTransaction', route: '#/intercompany/transactions', label: 'Intercompany Journal' },
  JV: { prefix: 'JV', entityType: 'GLJournal', route: '#/general-accounting/journals', label: 'General Ledger Journal' },
  SLA: { prefix: 'SLA', entityType: 'GLJournal', route: '#/general-accounting/journals', label: 'Subledger Accounting Journal' },
};

export function getDocPrefix(docNumber: string): string {
  if (!docNumber) return '';
  if (docNumber.startsWith('FA-')) return 'FA';
  const match = docNumber.match(/^([A-Z]+)-/);
  return match ? match[1] : '';
}

export function getDocRoute(docNumber: string): string {
  const prefix = getDocPrefix(docNumber);
  const info = PREFIX_REGISTRY[prefix];
  if (!info) return '#/';
  return `${info.route}?docNumber=${encodeURIComponent(docNumber)}`;
}

export interface ResolvedDocumentData {
  number: string;
  id?: string;
  typeLabel: string;
  entityType: string;
  businessUnit?: string;
  date?: string;
  status?: string;
  totalAmount?: number;
  currency?: string;
  counterparty?: string;
  counterpartyRole?: string;
  description?: string;
  createdBy?: string;
  approvedBy?: string;
  rejectionReason?: string;
  rawRecord: any;
  lines: Array<{
    lineNum: number | string;
    description: string;
    quantity?: number;
    unitPrice?: number;
    amount?: number;
    account?: string;
    department?: string;
  }>;
  relatedDocuments: Array<{
    number: string;
    typeLabel: string;
    relationship: string;
  }>;
  glJournalId?: string;
  glJournalNumber?: string;
}

/**
 * Resolves full document details and cross-references across all modules
 */
export function resolveDocument(docNumber: string): ResolvedDocumentData | null {
  if (!docNumber) return null;
  const db = getDb();
  const prefix = getDocPrefix(docNumber);

  // 1. Purchase Requisitions (REQ)
  if (prefix === 'REQ') {
    const req = db.requisitions?.find((r) => r.number === docNumber || r.id === docNumber);
    if (req) {
      const relatedPOs = db.purchaseOrders?.filter(
        (po) =>
          po.requisitionNumber === req.number ||
          po.lines?.some((l) => l.sourceRequisitionNumber === req.number) ||
          req.relatedPoNumbers?.includes(po.number)
      ) || [];

      return {
        number: req.number,
        id: req.id,
        typeLabel: 'Purchase Requisition',
        entityType: 'Requisition',
        businessUnit: req.businessUnit,
        date: req.requisitionDate || req.date || req.createdAt,
        status: req.status,
        totalAmount: req.totalAmount,
        currency: 'AED',
        counterparty: req.department,
        counterpartyRole: 'Department',
        description: req.description || req.justification,
        createdBy: req.createdBy,
        approvedBy: req.approvedBy,
        rejectionReason: req.rejectionReason,
        rawRecord: req,
        lines: (req.lines || []).map((l, i) => ({
          lineNum: l.lineNumber || i + 1,
          description: l.description,
          quantity: l.quantity,
          unitPrice: l.estimatedUnitPrice || l.estimatedCost,
          amount: l.estimatedAmount || (l.quantity * (l.estimatedCost || 0)),
          account: l.chargeAccount,
          department: l.department,
        })),
        relatedDocuments: relatedPOs.map((po) => ({
          number: po.number,
          typeLabel: 'Purchase Order',
          relationship: 'Converted Purchase Order',
        })),
      };
    }
  }

  // 2. Purchase Orders (PO)
  if (prefix === 'PO') {
    const po = db.purchaseOrders?.find((p) => p.number === docNumber || p.id === docNumber);
    if (po) {
      const relatedReqs = po.requisitionNumber
        ? [{ number: po.requisitionNumber, typeLabel: 'Requisition', relationship: 'Source Requisition' }]
        : [];
      const relatedReceipts = (db.receipts || [])
        .filter((r) => r.poNumber === po.number)
        .map((r) => ({ number: r.number, typeLabel: 'Goods Receipt (GRN)', relationship: 'Goods Receipt' }));
      const relatedInvoices = (db.apInvoices || [])
        .filter((inv) => inv.poNumber === po.number)
        .map((inv) => ({ number: inv.number, typeLabel: 'Payables Invoice', relationship: 'AP Invoice' }));

      return {
        number: po.number,
        id: po.id,
        typeLabel: 'Purchase Order',
        entityType: 'PurchaseOrder',
        businessUnit: po.businessUnit,
        date: po.poDate || po.date || po.createdAt,
        status: po.status,
        totalAmount: po.totalAmount,
        currency: po.currency || 'AED',
        counterparty: po.supplierName,
        counterpartyRole: 'Supplier',
        description: po.notes || `PO for ${po.supplierName}`,
        createdBy: po.createdBy,
        approvedBy: po.approvedBy,
        rejectionReason: po.rejectionReason,
        rawRecord: po,
        lines: (po.lines || []).map((l, i) => ({
          lineNum: l.lineNumber || i + 1,
          description: l.description,
          quantity: l.quantity,
          unitPrice: l.unitPrice,
          amount: l.lineAmount,
          account: l.account,
          department: l.department,
        })),
        relatedDocuments: [...relatedReqs, ...relatedReceipts, ...relatedInvoices],
      };
    }
  }

  // 3. Receipts / GRN (RCV)
  if (prefix === 'RCV') {
    const rcv = db.receipts?.find((r) => r.number === docNumber || r.id === docNumber);
    if (rcv) {
      const relPO = rcv.poNumber
        ? [{ number: rcv.poNumber, typeLabel: 'Purchase Order', relationship: 'Source Purchase Order' }]
        : [];
      const relInvoices = (db.apInvoices || [])
        .filter((inv) => inv.poNumber === rcv.poNumber || inv.lines?.some((l) => l.receiptNumber === rcv.number))
        .map((inv) => ({ number: inv.number, typeLabel: 'Payables Invoice', relationship: 'Matched AP Invoice' }));

      const glJournal = db.glJournals?.find(
        (j) => j.id === rcv.glJournalId || j.number === rcv.glJournalNumber || (j.sourceModule === 'Procurement/Inventory' && j.lines?.some((l) => l.sourceDocumentNumber === rcv.number))
      );

      const relGL = glJournal
        ? [{ number: glJournal.number, typeLabel: 'GL Journal', relationship: 'Posted Subledger Journal' }]
        : [];

      return {
        number: rcv.number,
        id: rcv.id,
        typeLabel: 'Goods Receipt Note (GRN)',
        entityType: 'Receipt',
        businessUnit: rcv.businessUnit,
        date: rcv.receiptDate || rcv.createdAt,
        status: rcv.status,
        totalAmount: rcv.totalAmount,
        currency: 'AED',
        counterparty: rcv.supplierName,
        counterpartyRole: 'Supplier',
        description: rcv.notes || `Receipt against ${rcv.poNumber}`,
        createdBy: rcv.createdBy,
        approvedBy: rcv.approvedBy,
        rejectionReason: rcv.rejectionReason,
        glJournalId: glJournal?.id || rcv.glJournalId,
        glJournalNumber: glJournal?.number || rcv.glJournalNumber,
        rawRecord: rcv,
        lines: (rcv.lines || []).map((l, i) => ({
          lineNum: l.lineNumber || i + 1,
          description: l.description,
          quantity: l.quantityReceived,
          unitPrice: l.unitPrice,
          amount: l.lineAmount,
          account: l.account,
        })),
        relatedDocuments: [...relPO, ...relInvoices, ...relGL],
      };
    }
  }

  // 4. Payables Invoices & Credit Memos (PINV / PCM)
  if (prefix === 'PINV' || prefix === 'PCM') {
    const inv = db.apInvoices?.find((i) => i.number === docNumber || i.id === docNumber);
    if (inv) {
      const relPO = inv.poNumber
        ? [{ number: inv.poNumber, typeLabel: 'Purchase Order', relationship: 'Matched Purchase Order' }]
        : [];
      const relPayments = (db.apPayments || [])
        .filter((p) => p.applications?.some((a) => a.invoiceNumber === inv.number))
        .map((p) => ({ number: p.number, typeLabel: 'Payables Payment', relationship: 'Disbursement Payment' }));
      const glJournal = db.glJournals?.find(
        (j) => j.id === inv.glJournalId || j.lines?.some((l) => l.sourceDocumentNumber === inv.number)
      );
      const relGL = glJournal
        ? [{ number: glJournal.number, typeLabel: 'GL Journal', relationship: 'Posted Subledger Journal' }]
        : [];

      return {
        number: inv.number,
        id: inv.id,
        typeLabel: inv.invoiceType === 'Credit Memo' ? 'AP Credit Memo' : 'Payables Invoice',
        entityType: 'APInvoice',
        businessUnit: inv.businessUnit,
        date: inv.invoiceDate,
        status: inv.status,
        totalAmount: inv.totalAmount,
        currency: inv.currency,
        counterparty: inv.supplierName,
        counterpartyRole: 'Supplier',
        description: inv.description,
        createdBy: inv.createdBy,
        approvedBy: inv.approvedBy,
        rejectionReason: inv.rejectionReason,
        glJournalId: glJournal?.id || inv.glJournalId,
        glJournalNumber: glJournal?.number,
        rawRecord: inv,
        lines: (inv.lines || []).map((l, i) => ({
          lineNum: l.lineNumber || i + 1,
          description: l.description,
          quantity: l.quantity,
          unitPrice: l.unitPrice,
          amount: l.lineAmount,
          account: l.account,
          department: l.department,
        })),
        relatedDocuments: [...relPO, ...relPayments, ...relGL],
      };
    }
  }

  // 5. AP Payments (PAY)
  if (prefix === 'PAY') {
    const pay = db.apPayments?.find((p) => p.number === docNumber || p.id === docNumber);
    if (pay) {
      const relInvoices = (pay.applications || []).map((a) => ({
        number: a.invoiceNumber,
        typeLabel: 'AP Invoice',
        relationship: `Applied AED ${a.appliedAmount}`,
      }));
      const glJournal = db.glJournals?.find(
        (j) => j.id === pay.glJournalId || j.lines?.some((l) => l.sourceDocumentNumber === pay.number)
      );
      const relGL = glJournal
        ? [{ number: glJournal.number, typeLabel: 'GL Journal', relationship: 'Posted Subledger Journal' }]
        : [];

      return {
        number: pay.number,
        id: pay.id,
        typeLabel: 'Payables Payment',
        entityType: 'APPayment',
        businessUnit: pay.businessUnit,
        date: pay.paymentDate,
        status: pay.status,
        totalAmount: pay.amount,
        currency: 'AED',
        counterparty: pay.supplierName,
        counterpartyRole: 'Supplier',
        description: `Payment via ${pay.paymentMethod}`,
        createdBy: pay.createdBy,
        approvedBy: pay.approvedBy,
        glJournalId: glJournal?.id || pay.glJournalId,
        glJournalNumber: glJournal?.number,
        rawRecord: pay,
        lines: (pay.applications || []).map((a, i) => ({
          lineNum: i + 1,
          description: `Applied against invoice ${a.invoiceNumber}`,
          amount: a.appliedAmount,
        })),
        relatedDocuments: [...relInvoices, ...relGL],
      };
    }
  }

  // 6. Receivables Invoices & Credit Memos (RINV / RCM)
  if (prefix === 'RINV' || prefix === 'RCM') {
    const ar = db.arTransactions?.find((i) => i.number === docNumber || i.id === docNumber);
    if (ar) {
      const relReceipts = (db.arReceipts || [])
        .filter((r) => r.applications?.some((a) => a.transactionNumber === ar.number))
        .map((r) => ({ number: r.number, typeLabel: 'AR Receipt', relationship: 'Customer Receipt' }));
      const glJournal = db.glJournals?.find(
        (j) => j.id === ar.glJournalId || j.lines?.some((l) => l.sourceDocumentNumber === ar.number)
      );
      const relGL = glJournal
        ? [{ number: glJournal.number, typeLabel: 'GL Journal', relationship: 'Posted Subledger Journal' }]
        : [];

      return {
        number: ar.number,
        id: ar.id,
        typeLabel: ar.transactionClass === 'Credit Memo' ? 'AR Credit Memo' : 'Receivables Invoice',
        entityType: 'ARTransaction',
        businessUnit: ar.businessUnit,
        date: ar.transactionDate,
        status: ar.status,
        totalAmount: ar.totalAmount,
        currency: 'AED',
        counterparty: ar.customerName,
        counterpartyRole: 'Customer',
        description: ar.description,
        createdBy: ar.createdBy,
        approvedBy: ar.approvedBy,
        rejectionReason: ar.rejectionReason,
        glJournalId: glJournal?.id || ar.glJournalId,
        glJournalNumber: glJournal?.number,
        rawRecord: ar,
        lines: (ar.lines || []).map((l, i) => ({
          lineNum: l.lineNumber || i + 1,
          description: l.description,
          quantity: l.quantity,
          unitPrice: l.unitPrice,
          amount: l.lineAmount,
          account: l.revenueAccount,
          department: l.department,
        })),
        relatedDocuments: [...relReceipts, ...relGL],
      };
    }
  }

  // 7. AR Customer Receipts (RCT)
  if (prefix === 'RCT') {
    const rct = db.arReceipts?.find((r) => r.number === docNumber || r.id === docNumber);
    if (rct) {
      const relInvoices = (rct.applications || []).map((a) => ({
        number: a.transactionNumber,
        typeLabel: 'Receivables Invoice',
        relationship: `Applied AED ${a.appliedAmount}`,
      }));
      const glJournal = db.glJournals?.find(
        (j) => j.id === rct.glJournalId || j.lines?.some((l) => l.sourceDocumentNumber === rct.number)
      );
      const relGL = glJournal
        ? [{ number: glJournal.number, typeLabel: 'GL Journal', relationship: 'Posted Subledger Journal' }]
        : [];

      return {
        number: rct.number,
        id: rct.id,
        typeLabel: 'AR Customer Receipt',
        entityType: 'ARReceipt',
        businessUnit: rct.businessUnit,
        date: rct.receiptDate,
        status: rct.status,
        totalAmount: rct.amount,
        currency: 'AED',
        counterparty: rct.customerName,
        counterpartyRole: 'Customer',
        description: `Customer collection via ${rct.receiptMethod}`,
        createdBy: rct.createdBy,
        approvedBy: rct.approvedBy,
        glJournalId: glJournal?.id || rct.glJournalId,
        glJournalNumber: glJournal?.number,
        rawRecord: rct,
        lines: (rct.applications || []).map((a, i) => ({
          lineNum: i + 1,
          description: `Applied against invoice ${a.transactionNumber}`,
          amount: a.appliedAmount,
        })),
        relatedDocuments: [...relInvoices, ...relGL],
      };
    }
  }

  // 8. Cash Vouchers (PCV / MCV)
  if (prefix === 'PCV' || prefix === 'MCV') {
    const v = db.cashVouchers?.find((c) => c.number === docNumber || c.id === docNumber);
    if (v) {
      const glJournal = db.glJournals?.find(
        (j) => j.id === v.glJournalId || j.lines?.some((l) => l.sourceDocumentNumber === v.number)
      );
      const relGL = glJournal
        ? [{ number: glJournal.number, typeLabel: 'GL Journal', relationship: 'Posted Subledger Journal' }]
        : [];

      return {
        number: v.number,
        id: v.id,
        typeLabel: v.voucherType === 'Main Cash' ? 'Main Cash Voucher' : 'Petty Cash Voucher',
        entityType: 'CashVoucher',
        businessUnit: v.businessUnit,
        date: v.date,
        status: v.status,
        totalAmount: v.totalAmount,
        currency: 'AED',
        counterparty: v.payee,
        counterpartyRole: 'Payee',
        description: v.description,
        createdBy: v.createdBy,
        approvedBy: v.approvedBy,
        rejectionReason: v.rejectionReason,
        glJournalId: glJournal?.id || v.glJournalId,
        glJournalNumber: glJournal?.number,
        rawRecord: v,
        lines: (v.lines || []).map((l, i) => ({
          lineNum: l.lineNumber || i + 1,
          description: l.description,
          amount: l.amount,
          account: l.expenseAccount,
          department: l.department,
        })),
        relatedDocuments: relGL,
      };
    }
  }

  // 9. Fixed Assets (FA-...)
  if (prefix === 'FA') {
    const fa = db.fixedAssets?.find((a) => a.tagNumber === docNumber || a.id === docNumber);
    if (fa) {
      const relInv = fa.sourceInvoiceNumber
        ? [{ number: fa.sourceInvoiceNumber, typeLabel: 'AP Capital Invoice', relationship: 'Source Invoice' }]
        : [];
      const relGL = (db.glJournals || [])
        .filter((j) => j.lines?.some((l) => l.description.includes(fa.tagNumber)))
        .map((j) => ({ number: j.number, typeLabel: 'GL Journal', relationship: 'Capitalisation / Depreciation' }));

      return {
        number: fa.tagNumber,
        id: fa.id,
        typeLabel: 'Fixed Asset Record',
        entityType: 'FixedAsset',
        businessUnit: fa.businessUnit,
        date: fa.inServiceDate,
        status: fa.status,
        totalAmount: fa.cost,
        currency: 'AED',
        counterparty: fa.category,
        counterpartyRole: 'Category',
        description: `${fa.name} (Net Book Value: AED ${fa.netBookValue})`,
        createdBy: 'henry.brooks',
        approvedBy: 'daniel.reed',
        rawRecord: fa,
        lines: [
          { lineNum: 1, description: 'Original Cost', amount: fa.cost, account: fa.costAccount },
          { lineNum: 2, description: 'Accumulated Depreciation', amount: -fa.accumulatedDepreciation, account: fa.accumDepAccount },
        ],
        relatedDocuments: [...relInv, ...relGL],
      };
    }
  }

  // 10. Intercompany Transactions (ICI / ICC / ICJ)
  if (prefix === 'ICI' || prefix === 'ICC' || prefix === 'ICJ') {
    const ic = db.icTransactions?.find((i) => i.number === docNumber || i.id === docNumber);
    if (ic) {
      const glJournal = db.glJournals?.find(
        (j) => j.id === ic.glJournalId || j.lines?.some((l) => l.sourceDocumentNumber === ic.number)
      );
      const relGL = glJournal
        ? [{ number: glJournal.number, typeLabel: 'GL Journal', relationship: 'Intercompany Subledger Journal' }]
        : [];

      return {
        number: ic.number,
        id: ic.id,
        typeLabel: `Intercompany ${ic.type}`,
        entityType: 'ICTransaction',
        businessUnit: `${ic.providerBU} → ${ic.receiverBU}`,
        date: ic.date,
        status: ic.status,
        totalAmount: ic.totalAmount,
        currency: 'AED',
        counterparty: ic.receiverBU,
        counterpartyRole: 'Receiver Entity',
        description: ic.description,
        createdBy: ic.createdBy,
        approvedBy: ic.approvedBy,
        glJournalId: glJournal?.id || ic.glJournalId,
        glJournalNumber: glJournal?.number,
        rawRecord: ic,
        lines: (ic.lines || []).map((l, i) => ({
          lineNum: l.lineNumber || i + 1,
          description: l.description,
          amount: l.amount,
          account: `${l.providerAccount} / ${l.receiverAccount}`,
        })),
        relatedDocuments: relGL,
      };
    }
  }

  // 11. General Ledger Journals (JV / SLA)
  if (prefix === 'JV' || prefix === 'SLA' || docNumber.startsWith('JV-')) {
    const jv = db.glJournals?.find((j) => j.number === docNumber || j.id === docNumber);
    if (jv) {
      const sourceDocs = Array.from(
        new Set(jv.lines.map((l) => l.sourceDocumentNumber).filter(Boolean))
      ).map((doc) => ({
        number: doc,
        typeLabel: 'Originating Subledger Document',
        relationship: 'Source Document',
      }));

      return {
        number: jv.number,
        id: jv.id,
        typeLabel: 'General Ledger Journal',
        entityType: 'GLJournal',
        businessUnit: jv.businessUnit,
        date: jv.journalDate,
        status: jv.status,
        totalAmount: jv.totalDebit,
        currency: 'AED',
        counterparty: jv.sourceModule,
        counterpartyRole: 'Source Subledger',
        description: jv.description,
        createdBy: jv.createdBy,
        approvedBy: jv.approvedBy,
        rejectionReason: jv.rejectionReason,
        glJournalId: jv.id,
        glJournalNumber: jv.number,
        rawRecord: jv,
        lines: (jv.lines || []).map((l, i) => ({
          lineNum: l.lineNumber || i + 1,
          description: l.description,
          amount: l.debit > 0 ? l.debit : -l.credit,
          account: `${l.businessUnit} - ${l.account}${l.department ? ` - ${l.department}` : ''}`,
          department: l.department,
        })),
        relatedDocuments: sourceDocs,
      };
    }
  }

  return null;
}
