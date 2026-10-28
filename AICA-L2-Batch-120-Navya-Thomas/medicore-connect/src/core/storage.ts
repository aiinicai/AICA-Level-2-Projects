import { get, set } from 'idb-keyval';
import {
  Supplier,
  Customer,
  Item,
  Requisition,
  PurchaseOrder,
  Receipt,
  InventoryBalance,
  APInvoice,
  APPayment,
  ARTransaction,
  ARReceipt,
  FixedAsset,
  AssetSourceLine,
  DepreciationRun,
  PettyCashFund,
  CashVoucher,
  BankAccount,
  BankStatement,
  ICTransaction,
  GLJournal,
  AuditLog,
  Notification,
  AssetCategory,
  Account,
} from './types';
import { ENRICHED_CHART_OF_ACCOUNTS } from '../data/chartOfAccounts';

export interface DatabaseState {
  accounts: Account[];
  suppliers: Supplier[];
  customers: Customer[];
  items: Item[];
  bankAccounts: BankAccount[];
  pettyCashFunds: PettyCashFund[];
  assetCategories: AssetCategory[];
  requisitions: Requisition[];
  purchaseOrders: PurchaseOrder[];
  receipts: Receipt[];
  inventoryBalances: InventoryBalance[];
  apInvoices: APInvoice[];
  apPayments: APPayment[];
  arTransactions: ARTransaction[];
  arReceipts: ARReceipt[];
  fixedAssets: FixedAsset[];
  assetSourceLines: AssetSourceLine[];
  depreciationRuns: DepreciationRun[];
  cashVouchers: CashVoucher[];
  bankStatements: BankStatement[];
  icTransactions: ICTransaction[];
  glJournals: GLJournal[];
  auditLogs: AuditLog[];
  notifications: Notification[];
  favourites: string[];
}

const DB_STORAGE_KEY = 'medicore_connect_db_v1';

let memoryDb: DatabaseState = {
  accounts: [...ENRICHED_CHART_OF_ACCOUNTS],
  suppliers: [],
  customers: [],
  items: [],
  bankAccounts: [],
  pettyCashFunds: [],
  assetCategories: [],
  requisitions: [],
  purchaseOrders: [],
  receipts: [],
  inventoryBalances: [],
  apInvoices: [],
  apPayments: [],
  arTransactions: [],
  arReceipts: [],
  fixedAssets: [],
  assetSourceLines: [],
  depreciationRuns: [],
  cashVouchers: [],
  bankStatements: [],
  icTransactions: [],
  glJournals: [],
  auditLogs: [],
  notifications: [],
  favourites: [
    '/payables/invoices',
    '/general-accounting/journals',
    '/reports/trial-balance',
    '/reports/ifrs',
  ],
};

let isInitialized = false;
const listeners: Array<() => void> = [];

export function subscribeToDb(callback: () => void): () => void {
  listeners.push(callback);
  return () => {
    const idx = listeners.indexOf(callback);
    if (idx >= 0) listeners.splice(idx, 1);
  };
}

function notifySubscribers() {
  for (const fn of listeners) {
    try {
      fn();
    } catch (e) {
      console.error('Error in DB subscriber:', e);
    }
  }
}

function runDataRepairMigration(db: DatabaseState): boolean {
  let changed = false;

  // 1. Ensure accounts is populated
  if (!db.accounts || db.accounts.length === 0) {
    db.accounts = [...ENRICHED_CHART_OF_ACCOUNTS];
    changed = true;
  }

  // 2. Repair Receipts without GL Journal
  if (db.receipts && db.receipts.length > 0) {
    db.receipts.forEach((rcv, idx) => {
      if (rcv.createdBy !== 'noah.bennett') {
        rcv.createdBy = 'noah.bennett';
        changed = true;
      }
      if (rcv.status === 'Posted' || rcv.status === 'Approved') {
        if (!rcv.approvedBy) {
          rcv.approvedBy = 'charlotte.davis';
          changed = true;
        }

        const existingJv = db.glJournals.find(
          (j) => j.lines.some((l) => l.sourceDocumentNumber === rcv.number) || j.id === rcv.glJournalId
        );

        if (!existingJv) {
          const jvId = `GLJ-RCV-REPAIR-${idx + 1}`;
          const jvNum = `JV-2026-00${150 + idx + 1}`;
          const cost = rcv.totalAmount || 0;
          const bu = rcv.businessUnit;

          const lines: any[] = (rcv.lines || []).map((rl, lIdx) => ({
            lineNumber: lIdx + 1,
            businessUnit: bu,
            account: rl.account || (rl.itemCode?.includes('PH') ? '1200' : rl.itemCode?.includes('CS') ? '1210' : '1230'),
            department: 'Clinical',
            debit: rl.lineAmount || (rl.quantityReceived * (rl.unitPrice || 0)),
            credit: 0,
            description: `Stock Receipt: ${rl.description} (PO: ${rcv.poNumber})`,
            sourceModule: 'Supply Chain Execution',
            sourceDocumentNumber: rcv.number,
            sourceDocumentId: rcv.id,
          }));

          lines.push({
            lineNumber: lines.length + 1,
            businessUnit: bu,
            account: '2010',
            department: 'Clinical',
            debit: 0,
            credit: cost,
            description: `Accrue Goods Received Not Invoiced (GRNI) - PO: ${rcv.poNumber}`,
            sourceModule: 'Supply Chain Execution',
            sourceDocumentNumber: rcv.number,
            sourceDocumentId: rcv.id,
          });

          const journal: any = {
            id: jvId,
            number: jvNum,
            period: 'Oct-26',
            journalDate: rcv.receiptDate || '2026-10-06',
            businessUnit: bu,
            sourceModule: 'Supply Chain Execution',
            category: 'Goods Receipt',
            description: `Goods receipt note against ${rcv.poNumber} [Seed Repair]`,
            status: 'Posted',
            totalDebit: cost,
            totalCredit: cost,
            lines,
            createdBy: 'noah.bennett',
            createdAt: rcv.createdAt || '2026-10-06T11:00:00Z',
            approvedBy: 'charlotte.davis',
            postedAt: rcv.approvedAt || '2026-10-06T12:00:00Z',
          };

          db.glJournals.unshift(journal);
          rcv.glJournalId = jvId;
          rcv.glJournalNumber = jvNum;
          changed = true;

          db.auditLogs.unshift({
            id: `AUDIT-REPAIR-${Date.now()}-${idx}`,
            entityType: 'Receipt',
            entityId: rcv.id,
            action: 'POST',
            userId: 'system',
            userName: 'System Migration Engine',
            timestamp: new Date().toISOString(),
            comments: `Seed Repair: Generated missing GL journal ${jvNum} for Goods Receipt ${rcv.number}`,
          });
        }
      }
    });
  }

  // 3. Align Makers & Approvers on Master/Seed records
  if (db.apInvoices) {
    db.apInvoices.forEach((inv) => {
      if (inv.createdBy !== 'omar.haddad' && inv.createdBy !== 'charlotte.davis') {
        inv.createdBy = 'omar.haddad';
        changed = true;
      }
      if ((inv.status === 'Approved' || inv.status === 'Posted') && !inv.approvedBy) {
        inv.approvedBy = (inv.totalAmount || 0) > 250000 ? 'daniel.reed' : 'charlotte.davis';
        changed = true;
      }
    });
  }

  if (db.arTransactions) {
    db.arTransactions.forEach((ar) => {
      if (ar.createdBy !== 'sofia.marin') {
        ar.createdBy = 'sofia.marin';
        changed = true;
      }
      if ((ar.status === 'Approved' || ar.status === 'Posted') && !ar.approvedBy) {
        ar.approvedBy = (ar.totalAmount || 0) > 250000 ? 'daniel.reed' : 'charlotte.davis';
        changed = true;
      }
    });
  }

  if (db.purchaseOrders) {
    db.purchaseOrders.forEach((po) => {
      if (po.createdBy !== 'liam.carter') {
        po.createdBy = 'liam.carter';
        changed = true;
      }
      if ((po.status === 'Approved' || po.status === 'Partially Received' || po.status === 'Received') && !po.approvedBy) {
        po.approvedBy = 'daniel.reed';
        changed = true;
      }
    });
  }

  if (db.requisitions) {
    db.requisitions.forEach((req) => {
      if (req.createdBy !== 'liam.carter') {
        req.createdBy = 'liam.carter';
        changed = true;
      }
      if (req.status === 'Approved' && !req.approvedBy) {
        req.approvedBy = 'daniel.reed';
        changed = true;
      }
    });
  }

  if (db.icTransactions) {
    db.icTransactions.forEach((ic) => {
      if (ic.createdBy !== 'emma.collins') {
        ic.createdBy = 'emma.collins';
        changed = true;
      }
      if (ic.status === 'Posted' && !ic.approvedBy) {
        ic.approvedBy = 'daniel.reed';
        changed = true;
      }
    });
  }

  return changed;
}

export async function initStorage(forceReset = false): Promise<DatabaseState> {
  if (isInitialized && !forceReset) {
    return memoryDb;
  }

  try {
    if (!forceReset) {
      const persisted = await get<DatabaseState>(DB_STORAGE_KEY);
      if (persisted && persisted.glJournals && persisted.glJournals.length > 0) {
        memoryDb = persisted;
        const wasRepaired = runDataRepairMigration(memoryDb);
        if (wasRepaired) {
          saveDb(memoryDb);
        }
        isInitialized = true;
        notifySubscribers();
        return memoryDb;
      }
    }
  } catch (err) {
    console.warn('Could not read from IndexedDB, will seed fresh database:', err);
  }

  // Not initialized or reset requested
  isInitialized = true;
  return memoryDb;
}

export function getDb(): DatabaseState {
  return memoryDb;
}

export function saveDb(updated: DatabaseState): void {
  memoryDb = { ...updated };
  set(DB_STORAGE_KEY, memoryDb).catch((err) => {
    console.error('Failed to persist to IndexedDB:', err);
  });
  notifySubscribers();
}

export function updateDb(updater: (state: DatabaseState) => void): void {
  updater(memoryDb);
  saveDb(memoryDb);
}

// Log an audit trail entry
export function addAuditLog(entry: Omit<AuditLog, 'id' | 'timestamp'>): void {
  const log: AuditLog = {
    ...entry,
    id: `AUDIT-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    timestamp: new Date().toISOString(),
  };
  memoryDb.auditLogs.unshift(log);
  // Keep up to 1000 logs in memory
  if (memoryDb.auditLogs.length > 1000) {
    memoryDb.auditLogs.length = 1000;
  }
  saveDb(memoryDb);
}

// Add a notification
export function addNotification(notif: Omit<Notification, 'id' | 'timestamp' | 'read'>): void {
  const newNotif: Notification = {
    ...notif,
    id: `NOTIF-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    timestamp: new Date().toISOString(),
    read: false,
  };
  memoryDb.notifications.unshift(newNotif);
  saveDb(memoryDb);
}
