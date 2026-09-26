import React, { useState } from 'react';
import { Sidebar, MainNavSection } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { DashboardView } from './components/dashboard/DashboardView';
import { AnalyticsView } from './components/analytics/AnalyticsView';
import { SalesView } from './components/sales/SalesView';
import { ProcurementView } from './components/procurement/ProcurementView';
import { StockView } from './components/stock/StockView';
import { ComplianceView } from './components/compliance/ComplianceView';
import { AccountingView } from './components/accounting/AccountingView';
import { BankingPayrollView } from './components/banking/BankingPayrollView';
import { SettingsView } from './components/settings/SettingsView';
import { AuditTrailModal } from './components/audit/AuditTrailModal';
import { DocumentUploadModal } from './components/upload/DocumentUploadModal';

import {
  initialAccounts,
  initialAuditLogs,
  initialBankTransactions,
  initialCustomers,
  initialJournalEntries,
  initialPayrollRuns,
  initialSalesInvoices,
  initialSettings,
  initialStockItems,
  initialStockTransactions,
  initialVendorBills,
  initialVendors,
} from './data/initialData';

import {
  Account,
  AuditLogEntry,
  BankTransaction,
  Customer,
  JournalEntry,
  PayrollRun,
  SalesInvoice,
  StockItem,
  StockTransaction,
  SystemSettings,
  UserRole,
  Vendor,
  VendorBill,
} from './types';

export default function App() {
  // Global State
  const [activeSection, setActiveSection] = useState<MainNavSection>('dashboard');
  const [activeRole, setActiveRole] = useState<UserRole>('CFO');
  const [settings, setSettings] = useState<SystemSettings>(initialSettings);
  const [activeGstin, setActiveGstin] = useState<string>(initialSettings.activeGstin);

  // Accounting & Operations Domain State
  const [accounts, setAccounts] = useState<Account[]>(initialAccounts);
  const [journalEntries, setJournalEntries] = useState<JournalEntry[]>(initialJournalEntries);
  const [salesInvoices, setSalesInvoices] = useState<SalesInvoice[]>(initialSalesInvoices);
  const [vendorBills, setVendorBills] = useState<VendorBill[]>(initialVendorBills);
  const [stockItems, setStockItems] = useState<StockItem[]>(initialStockItems);
  const [stockTransactions, setStockTransactions] = useState<StockTransaction[]>(initialStockTransactions);
  const [customers, setCustomers] = useState<Customer[]>(initialCustomers);
  const [vendors, setVendors] = useState<Vendor[]>(initialVendors);
  const [bankTransactions, setBankTransactions] = useState<BankTransaction[]>(initialBankTransactions);
  const [payrollRuns, setPayrollRuns] = useState<PayrollRun[]>(initialPayrollRuns);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>(initialAuditLogs);

  // Modals State
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);

  // Review Queue Counts
  const reviewQueueInvoices = salesInvoices.filter((i) => i.status === 'REVIEW_QUEUE').length;
  const reviewQueueBills = vendorBills.filter((b) => b.status === 'REVIEW_QUEUE').length;
  const totalReviewQueue = reviewQueueInvoices + reviewQueueBills;

  // Audit Log Recorder Helper
  const logAuditEvent = (action: string, ref: string, details: string) => {
    const newLog: AuditLogEntry = {
      id: `LOG-${Date.now()}`,
      timestamp: new Date().toISOString(),
      performedBy: 'Gagan Bareja (CFO)',
      role: activeRole,
      action,
      documentReference: ref,
      details,
      hash: Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
    };
    setAuditLogs((prev) => [newLog, ...prev]);
  };

  // HANDLER: Post Sales Invoice (Double Entry Engine)
  const handlePostInvoice = (invoice: SalesInvoice) => {
    const isInterState = invoice.igst > 0;
    const jeId = `JE-2026-${Math.floor(100 + Math.random() * 900)}`;

    const newJE: JournalEntry = {
      id: jeId,
      date: invoice.date,
      sourceDocumentType: 'SALES_INVOICE',
      sourceDocumentId: invoice.invoiceNumber,
      lines: [
        {
          id: `L1-${Date.now()}`,
          accountId: 'acc-1201',
          accountCode: '1201',
          accountName: `Trade Receivables (${invoice.customerName})`,
          debit: invoice.totalAmount,
          credit: 0,
        },
        {
          id: `L2-${Date.now()}`,
          accountId: 'acc-3001',
          accountCode: '3001',
          accountName: 'Revenue from Operations',
          debit: 0,
          credit: invoice.taxableAmount,
        },
        ...(isInterState
          ? [
              {
                id: `L3-${Date.now()}`,
                accountId: 'acc-2303',
                accountCode: '2303',
                accountName: 'Output IGST Payable',
                debit: 0,
                credit: invoice.igst,
              },
            ]
          : [
              {
                id: `L3-${Date.now()}`,
                accountId: 'acc-2301',
                accountCode: '2301',
                accountName: 'Output CGST Payable',
                debit: 0,
                credit: invoice.cgst,
              },
              {
                id: `L4-${Date.now()}`,
                accountId: 'acc-2302',
                accountCode: '2302',
                accountName: 'Output SGST Payable',
                debit: 0,
                credit: invoice.sgst,
              },
            ]),
        {
          id: `L5-${Date.now()}`,
          accountId: 'acc-4001',
          accountCode: '4001',
          accountName: 'Cost of Materials Consumed (COGS)',
          debit: invoice.totalCogs,
          credit: 0,
        },
        {
          id: `L6-${Date.now()}`,
          accountId: 'acc-1102',
          accountCode: '1102',
          accountName: 'Finished Goods Inventory',
          debit: 0,
          credit: invoice.totalCogs,
        },
      ],
      totalDebit: invoice.totalAmount + invoice.totalCogs,
      totalCredit: invoice.totalAmount + invoice.totalCogs,
      status: 'POSTED',
      narration: `Tax Invoice ${invoice.invoiceNumber} to ${invoice.customerName} with perpetual COGS derecognition.`,
      postedBy: 'Gagan Bareja (CFO)',
      postedAt: new Date().toISOString(),
    };

    setJournalEntries((prev) => [newJE, ...prev]);

    // Update Accounts Balance
    setAccounts((prev) =>
      prev.map((acc) => {
        if (acc.code === '1201') return { ...acc, balance: acc.balance + invoice.totalAmount };
        if (acc.code === '3001') return { ...acc, balance: acc.balance + invoice.taxableAmount };
        if (acc.code === '2301') return { ...acc, balance: acc.balance + invoice.cgst };
        if (acc.code === '2302') return { ...acc, balance: acc.balance + invoice.sgst };
        if (acc.code === '2303') return { ...acc, balance: acc.balance + invoice.igst };
        if (acc.code === '4001') return { ...acc, balance: acc.balance + invoice.totalCogs };
        if (acc.code === '1102') return { ...acc, balance: acc.balance - invoice.totalCogs };
        return acc;
      })
    );

    // Update Sales Invoices List
    setSalesInvoices((prev) => [{ ...invoice, journalEntryId: jeId }, ...prev]);

    // Update Stock Levels
    invoice.items.forEach((item) => {
      setStockItems((prev) =>
        prev.map((s) => (s.id === item.skuId ? { ...s, currentStock: Math.max(0, s.currentStock - item.quantity) } : s))
      );
    });

    logAuditEvent(
      'POST_SALES_INVOICE',
      invoice.invoiceNumber,
      `Generated sales voucher total ${invoice.totalAmount} INR, journal ${jeId} posted`
    );
  };

  // HANDLER: Approve Invoice from Review Queue
  const handleApproveReviewQueue = (invoiceId: string) => {
    const inv = salesInvoices.find((i) => i.id === invoiceId);
    if (!inv) return;

    const approvedInv: SalesInvoice = {
      ...inv,
      status: 'UNPAID',
    };

    // Remove from old and re-post
    setSalesInvoices((prev) => prev.filter((i) => i.id !== invoiceId));
    handlePostInvoice(approvedInv);

    logAuditEvent(
      'APPROVE_REVIEW_QUEUE',
      inv.invoiceNumber,
      `Maker-checker verification approved for low-confidence invoice by CFO`
    );
  };

  // HANDLER: Post Vendor Bill
  const handlePostBill = (bill: VendorBill) => {
    const isInterState = bill.igst > 0;
    const jeId = `JE-2026-${Math.floor(100 + Math.random() * 900)}`;

    const newJE: JournalEntry = {
      id: jeId,
      date: bill.date,
      sourceDocumentType: 'PURCHASE_BILL',
      sourceDocumentId: bill.billNumber,
      lines: [
        {
          id: `L1-${Date.now()}`,
          accountId: bill.category === 'INVENTORY_PURCHASE' ? 'acc-1101' : 'acc-4203',
          accountCode: bill.category === 'INVENTORY_PURCHASE' ? '1101' : '4203',
          accountName: bill.category === 'INVENTORY_PURCHASE' ? 'Raw Materials Inventory' : 'Operating Other Expenses',
          debit: bill.taxableAmount,
          credit: 0,
        },
        ...(isInterState
          ? [
              {
                id: `L2-${Date.now()}`,
                accountId: 'acc-1303',
                accountCode: '1303',
                accountName: 'Input IGST Credit (ITC)',
                debit: bill.igst,
                credit: 0,
              },
            ]
          : [
              {
                id: `L2-${Date.now()}`,
                accountId: 'acc-1301',
                accountCode: '1301',
                accountName: 'Input CGST Credit (ITC)',
                debit: bill.cgst,
                credit: 0,
              },
              {
                id: `L3-${Date.now()}`,
                accountId: 'acc-1302',
                accountCode: '1302',
                accountName: 'Input SGST Credit (ITC)',
                debit: bill.sgst,
                credit: 0,
              },
            ]),
        ...(bill.tdsDeducted > 0
          ? [
              {
                id: `L4-${Date.now()}`,
                accountId: 'acc-2201',
                accountCode: '2201',
                accountName: `TDS Payable (${bill.tdsSection || 'Sec 194'})`,
                debit: 0,
                credit: bill.tdsDeducted,
              },
            ]
          : []),
        {
          id: `L5-${Date.now()}`,
          accountId: 'acc-2101',
          accountCode: '2101',
          accountName: `Trade Payables (${bill.vendorName})`,
          debit: 0,
          credit: bill.netPayable,
        },
      ],
      totalDebit: bill.taxableAmount + (bill.cgst + bill.sgst + bill.igst),
      totalCredit: bill.taxableAmount + (bill.cgst + bill.sgst + bill.igst),
      status: 'POSTED',
      narration: `Vendor Bill ${bill.billNumber} from ${bill.vendorName} with input ITC & TDS deduction.`,
      postedBy: 'Gagan Bareja (CFO)',
      postedAt: new Date().toISOString(),
    };

    setJournalEntries((prev) => [newJE, ...prev]);

    // Update Accounts Balance
    setAccounts((prev) =>
      prev.map((acc) => {
        if (acc.code === '1101' && bill.category === 'INVENTORY_PURCHASE') {
          return { ...acc, balance: acc.balance + bill.taxableAmount };
        }
        if (acc.code === '4203' && bill.category !== 'INVENTORY_PURCHASE') {
          return { ...acc, balance: acc.balance + bill.taxableAmount };
        }
        if (acc.code === '1301') return { ...acc, balance: acc.balance + bill.cgst };
        if (acc.code === '1302') return { ...acc, balance: acc.balance + bill.sgst };
        if (acc.code === '1303') return { ...acc, balance: acc.balance + bill.igst };
        if (acc.code === '2201') return { ...acc, balance: acc.balance + bill.tdsDeducted };
        if (acc.code === '2101') return { ...acc, balance: acc.balance + bill.netPayable };
        return acc;
      })
    );

    setVendorBills((prev) => [{ ...bill, journalEntryId: jeId }, ...prev]);

    logAuditEvent(
      'POST_VENDOR_BILL',
      bill.billNumber,
      `Vendor bill posted for ${bill.vendorName} net ${bill.netPayable} INR`
    );
  };

  // HANDLER: Approve Bill from Review Queue
  const handleApproveBillReviewQueue = (billId: string) => {
    const bill = vendorBills.find((b) => b.id === billId);
    if (!bill) return;

    const approvedBill: VendorBill = {
      ...bill,
      status: 'UNPAID',
    };

    setVendorBills((prev) => prev.filter((b) => b.id !== billId));
    handlePostBill(approvedBill);

    logAuditEvent(
      'APPROVE_BILL_QUEUE',
      bill.billNumber,
      `Maker-checker verified vendor bill by CFO`
    );
  };

  // HANDLER: Add Stock Adjustment
  const handleAddStockAdjustment = (tx: StockTransaction) => {
    setStockTransactions((prev) => [tx, ...prev]);
    setStockItems((prev) =>
      prev.map((s) => {
        if (s.id === tx.skuId) {
          const newQty = tx.type === 'OUT_SALE' ? s.currentStock - tx.quantity : s.currentStock + tx.quantity;
          return { ...s, currentStock: Math.max(0, newQty) };
        }
        return s;
      })
    );
    logAuditEvent('STOCK_ADJUSTMENT', tx.referenceDoc, `Movement of ${tx.quantity} units for ${tx.skuName}`);
  };

  // HANDLER: Add Manual Journal Entry
  const handleAddManualJournalEntry = (entry: JournalEntry) => {
    setJournalEntries((prev) => [entry, ...prev]);

    // Adjust accounts
    entry.lines.forEach((line) => {
      setAccounts((prev) =>
        prev.map((acc) => {
          if (acc.code === line.accountCode) {
            const netChange = line.debit - line.credit;
            return { ...acc, balance: acc.balance + netChange };
          }
          return acc;
        })
      );
    });

    logAuditEvent('POST_MANUAL_JV', entry.id, entry.narration);
  };

  // HANDLER: Reconcile Bank Transaction
  const handleReconcileTransaction = (txId: string) => {
    setBankTransactions((prev) =>
      prev.map((t) => (t.id === txId ? { ...t, status: 'RECONCILED' as const } : t))
    );
    logAuditEvent('BANK_RECONCILE', txId, 'Bank statement entry reconciled against General Ledger');
  };

  // HANDLER: Invoice Extracted from OCR
  const handleInvoiceExtracted = (inv: SalesInvoice, autoPosted: boolean) => {
    if (autoPosted) {
      handlePostInvoice(inv);
    } else {
      setSalesInvoices((prev) => [inv, ...prev]);
      logAuditEvent(
        'OCR_QUEUE_ROUTED',
        inv.invoiceNumber,
        `Invoice routed to review queue (confidence: ${inv.confidenceScore}%)`
      );
    }
  };

  // HANDLER: Bill Extracted from OCR
  const handleBillExtracted = (bill: VendorBill, autoPosted: boolean) => {
    if (autoPosted) {
      handlePostBill(bill);
    } else {
      setVendorBills((prev) => [bill, ...prev]);
      logAuditEvent(
        'OCR_QUEUE_ROUTED',
        bill.billNumber,
        `Vendor bill routed to review queue (confidence: ${bill.confidenceScore}%)`
      );
    }
  };

  return (
    <div id="cfo-platform-root" className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Context & Switcher Bar */}
      <TopBar
        settings={settings}
        activeGstin={activeGstin}
        onSelectGstin={setActiveGstin}
        activeRole={activeRole}
        onSelectRole={setActiveRole}
        onOpenAuditLog={() => setIsAuditModalOpen(true)}
        onOpenUploadModal={() => setIsUploadModalOpen(true)}
        totalAlertsCount={totalReviewQueue}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Persistent 10-Module Sidebar */}
        <Sidebar
          activeSection={activeSection}
          onSelectSection={(sec) => {
            if (sec === 'audit') {
              setIsAuditModalOpen(true);
            } else {
              setActiveSection(sec);
            }
          }}
          reviewQueueCount={totalReviewQueue}
        />

        {/* Main Workspace Stage */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-950/60">
          <div className="max-w-7xl mx-auto">
            {activeSection === 'dashboard' && (
              <DashboardView
                accounts={accounts}
                salesInvoices={salesInvoices}
                vendorBills={vendorBills}
                stockItems={stockItems}
                customers={customers}
                onNavigate={setActiveSection}
                onOpenUpload={() => setIsUploadModalOpen(true)}
              />
            )}

            {activeSection === 'sales' && (
              <SalesView
                salesInvoices={salesInvoices}
                customers={customers}
                stockItems={stockItems}
                settings={settings}
                onPostInvoice={handlePostInvoice}
                onApproveReviewQueue={handleApproveReviewQueue}
                onOpenUpload={() => setIsUploadModalOpen(true)}
              />
            )}

            {activeSection === 'procurement' && (
              <ProcurementView
                vendorBills={vendorBills}
                vendors={vendors}
                settings={settings}
                onPostBill={handlePostBill}
                onApproveBillReviewQueue={handleApproveBillReviewQueue}
                onOpenUpload={() => setIsUploadModalOpen(true)}
              />
            )}

            {activeSection === 'stock' && (
              <StockView
                stockItems={stockItems}
                stockTransactions={stockTransactions}
                settings={settings}
                onAddStockAdjustment={handleAddStockAdjustment}
              />
            )}

            {activeSection === 'compliance' && (
              <ComplianceView
                salesInvoices={salesInvoices}
                vendorBills={vendorBills}
              />
            )}

            {activeSection === 'accounting' && (
              <AccountingView
                accounts={accounts}
                journalEntries={journalEntries}
                settings={settings}
                onAddManualJournalEntry={handleAddManualJournalEntry}
              />
            )}

            {activeSection === 'banking' && (
              <BankingPayrollView
                bankTransactions={bankTransactions}
                payrollRuns={payrollRuns}
                onReconcileTransaction={handleReconcileTransaction}
                onPostPayroll={(run) => {
                  setPayrollRuns((prev) => [run, ...prev]);
                }}
              />
            )}

            {activeSection === 'analytics' && (
              <AnalyticsView
                salesInvoices={salesInvoices}
                stockItems={stockItems}
                customers={customers}
                settings={settings}
              />
            )}

            {activeSection === 'settings' && (
              <SettingsView
                settings={settings}
                onUpdateSettings={(newS) => {
                  setSettings(newS);
                  setActiveGstin(newS.activeGstin);
                }}
              />
            )}
          </div>
        </main>
      </div>

      {/* Global Modals */}
      <AuditTrailModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
        auditLogs={auditLogs}
      />

      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        settings={settings}
        customers={customers}
        vendors={vendors}
        stockItems={stockItems}
        onInvoiceExtracted={handleInvoiceExtracted}
        onBillExtracted={handleBillExtracted}
      />
    </div>
  );
}
