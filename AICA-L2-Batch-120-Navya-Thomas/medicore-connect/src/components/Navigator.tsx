import React from 'react';
import {
  X,
  ShoppingCart,
  Boxes,
  FileSpreadsheet,
  Receipt,
  BookOpen,
  ArrowLeftRight,
  Landmark,
  Building2,
  BarChart3,
  Wrench,
  ChevronRight,
  ShieldCheck,
  Search,
} from 'lucide-react';

interface NavigatorProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (route: string) => void;
}

interface NavModule {
  id: string;
  title: string;
  icon: any;
  apps: { title: string; route: string; description?: string }[];
  quickActions: { title: string; route: string }[];
}

export const NAV_MODULES: NavModule[] = [
  {
    id: 'procurement',
    title: 'Procurement',
    icon: ShoppingCart,
    apps: [
      { title: 'Procurement Dashboard', route: '#/procurement/dashboard', description: 'Spend analytics, open commitments, top vendors' },
      { title: 'Purchase Requisitions', route: '#/procurement/requisitions', description: 'Internal departmental purchase requests' },
      { title: 'Purchase Orders', route: '#/procurement/orders', description: 'Vendor PO commitments and contract line distributions' },
      { title: 'Suppliers', route: '#/payables/suppliers', description: 'Vendor master directory & compliance TRN' },
    ],
    quickActions: [
      { title: 'Create Requisition', route: '#/procurement/requisitions?action=create' },
      { title: 'Manage Requisitions', route: '#/procurement/requisitions' },
      { title: 'Create Order', route: '#/procurement/orders?action=create' },
      { title: 'Manage Orders', route: '#/procurement/orders' },
      { title: 'Approve Orders', route: '#/procurement/orders?status=Pending+Approval' },
      { title: 'Approve Requisitions', route: '#/procurement/requisitions?status=Pending+Approval' },
    ],
  },
  {
    id: 'supply-chain-execution',
    title: 'Supply Chain Execution',
    icon: Boxes,
    apps: [
      { title: 'Inventory & Stock On-hand', route: '#/supply-chain/inventory', description: 'Sub-inventory valuation, weighted average costs' },
      { title: 'Receiving (GRNI)', route: '#/supply-chain/receiving', description: 'Goods receipt note processing and 2010 accruals' },
      { title: 'Item Master', route: '#/supply-chain/items', description: 'Catalog of 120 pharmaceuticals, implants, consumables' },
      { title: 'Stock Transfers & Consumptions', route: '#/supply-chain/transfers', description: 'Sub-inventory distribution and departmental relief' },
    ],
    quickActions: [
      { title: 'Create Receipt', route: '#/supply-chain/receiving?action=create' },
      { title: 'Record Consumption', route: '#/supply-chain/transfers?action=consume' },
      { title: 'Stock On-hand Report', route: '#/supply-chain/inventory' },
    ],
  },
  {
    id: 'payables',
    title: 'Payables',
    icon: FileSpreadsheet,
    apps: [
      { title: 'Payables Dashboard', route: '#/payables/dashboard', description: 'AP aging summary, pending approvals, holds analysis' },
      { title: 'Invoices', route: '#/payables/invoices', description: 'PO 3-way match, standard, credit memo, prepayments' },
      { title: 'Payments', route: '#/payables/payments', description: 'Disbursements, bank payment runs, remittance advice' },
      { title: 'Suppliers', route: '#/payables/suppliers', description: 'Supplier accounts, sites, banking, tax registers' },
    ],
    quickActions: [
      { title: 'Create Invoice', route: '#/payables/invoices?action=create' },
      { title: 'Manage Invoices', route: '#/payables/invoices' },
      { title: 'Create Payment', route: '#/payables/payments?action=create' },
      { title: 'Payables Invoice Aging Report', route: '#/reports/payables-aging' },
    ],
  },
  {
    id: 'receivables',
    title: 'Receivables',
    icon: Receipt,
    apps: [
      { title: 'Billing Work Area', route: '#/receivables/billing', description: 'Patient self-pay, insurance claims, co-pay split' },
      { title: 'Accounts Receivable', route: '#/receivables/transactions', description: 'Customer open items, aging schedules, statements' },
      { title: 'Receipts & Collections', route: '#/receivables/receipts', description: 'Cash, card, and wire receipts application' },
      { title: 'Customers', route: '#/receivables/customers', description: 'Insurers, corporate clients, government health authorities' },
    ],
    quickActions: [
      { title: 'Create Transaction', route: '#/receivables/billing?action=create' },
      { title: 'Manage Receipts', route: '#/receivables/receipts' },
      { title: 'Create Receipt', route: '#/receivables/receipts?action=create' },
      { title: 'Customer Aging Report', route: '#/reports/receivables-aging' },
    ],
  },
  {
    id: 'general-accounting',
    title: 'General Accounting',
    icon: BookOpen,
    apps: [
      { title: 'General Accounting Dashboard', route: '#/general-accounting/dashboard', description: 'Executive ledger overview, revenue/expense trends' },
      { title: 'Journals', route: '#/general-accounting/journals', description: 'General ledger journal entries, drill-down to subledgers' },
      { title: 'Chart of Accounts', route: '#/general-accounting/chart-of-accounts', description: 'Standard 4-digit Account Hierarchy, IFRS lines & Segments' },
      { title: 'Period Close', route: '#/general-accounting/period-close', description: 'Monthly fiscal closing checklists and period control' },
      { title: 'Account Inquiry & Balances', route: '#/general-accounting/account-inquiry', description: 'Real-time account balance verification and drill-down' },
    ],
    quickActions: [
      { title: 'Create Journal', route: '#/general-accounting/journals?action=create' },
      { title: 'Manage Journals', route: '#/general-accounting/journals' },
      { title: 'Manage Chart of Accounts', route: '#/general-accounting/chart-of-accounts' },
      { title: 'Create Account', route: '#/general-accounting/chart-of-accounts?action=create' },
      { title: 'Period Close Checklist', route: '#/general-accounting/period-close' },
    ],
  },
  {
    id: 'intercompany-accounting',
    title: 'Intercompany Accounting',
    icon: ArrowLeftRight,
    apps: [
      { title: 'Transactions (Inbound & Outbound)', route: '#/intercompany/transactions', description: 'Intercompany invoices, credit notes, balancing entries' },
      { title: 'Reconciliation Matrix', route: '#/intercompany/reconciliation', description: 'BU-to-BU due from / due to elimination balance' },
      { title: 'Multitier Operations', route: '#/intercompany/multitier', description: 'Shared clinical labs, pharmacy central logistics recharges' },
    ],
    quickActions: [
      { title: 'Create Intercompany Transaction', route: '#/intercompany/transactions?action=create' },
      { title: 'Manage Outbound Transactions', route: '#/intercompany/transactions' },
      { title: 'Intercompany Reconciliation Matrix', route: '#/intercompany/reconciliation' },
    ],
  },
  {
    id: 'cash-management',
    title: 'Cash Management',
    icon: Landmark,
    apps: [
      { title: 'Bank Statements & Reconciliation', route: '#/cash/bank-reconciliation', description: 'Auto-matching against AP payments & AR collections' },
      { title: 'Petty Cash Registers', route: '#/cash/petty-cash', description: 'Custodian imprest funds, AED 1,000 cap vouchers' },
      { title: 'Main Cash Books', route: '#/cash/main-cash', description: 'Hospital cashier safe, daily reconciliation & deposits' },
    ],
    quickActions: [
      { title: 'Create Petty Cash Voucher', route: '#/cash/petty-cash?action=create' },
      { title: 'Create Main Cash Expense', route: '#/cash/main-cash?action=create' },
      { title: 'Reconcile Bank Statement', route: '#/cash/bank-reconciliation' },
    ],
  },
  {
    id: 'fixed-assets',
    title: 'Fixed Assets',
    icon: Building2,
    apps: [
      { title: 'Assets Work Area', route: '#/fixed-assets/assets', description: 'Additions queue (Incomplete, Ready to Post), Register' },
      { title: 'Asset Inquiry & Depreciation', route: '#/fixed-assets/depreciation', description: 'Monthly straight-line depreciation engine and schedules' },
    ],
    quickActions: [
      { title: 'Prepare Source Lines', route: '#/fixed-assets/assets?tab=additions' },
      { title: 'Run Depreciation (Oct-26)', route: '#/fixed-assets/depreciation' },
      { title: 'Asset Register Report', route: '#/reports/fixed-assets-register' },
    ],
  },
  {
    id: 'reports',
    title: 'Reports & IFRS',
    icon: BarChart3,
    apps: [
      { title: 'General Ledger Report', route: '#/reports/general-ledger', description: 'Account transaction history with opening & closing balances' },
      { title: 'Trial Balance', route: '#/reports/trial-balance', description: 'Period movement, Dr/Cr equality across 15 Business Units' },
      { title: 'IFRS Financial Statements', route: '#/reports/ifrs', description: 'Balance Sheet, P&L, Cash Flows (IAS 7), Notes' },
      { title: 'Subledger Reconciliations', route: '#/reports/reconciliations', description: 'AP, AR, Fixed Assets to General Ledger control ties' },
    ],
    quickActions: [
      { title: 'Generate Trial Balance', route: '#/reports/trial-balance' },
      { title: 'Generate IFRS Statements', route: '#/reports/ifrs' },
      { title: 'General Ledger Listing', route: '#/reports/general-ledger' },
    ],
  },
  {
    id: 'tools',
    title: 'Tools & Administration',
    icon: Wrench,
    apps: [
      { title: 'System Integrity Check', route: '#/tools/integrity', description: 'Automated 13-point self-test: TB, subledgers, IC netting, links' },
      { title: 'Access & Roles Matrix', route: '#/tools/access-roles', description: 'Module Maker-Approver assignment, limits and segregation of duties' },
      { title: 'Administration', route: '#/tools/administration', description: 'Business Units, Chart of Accounts, Users & Limits, Sequences' },
      { title: 'Audit Trail', route: '#/tools/audit-trail', description: 'Complete chronological history of ERP user events' },
    ],
    quickActions: [
      { title: 'Manage Access Matrix', route: '#/tools/access-roles' },
      { title: 'Run Integrity Self-Check', route: '#/tools/integrity' },
      { title: 'Reset Demo Data', route: '#/tools/administration?tab=reset' },
      { title: 'View Audit Trail', route: '#/tools/audit-trail' },
    ],
  },
];

export const Navigator: React.FC<NavigatorProps> = ({ isOpen, onClose, onNavigate }) => {
  const [searchQuery, setSearchQuery] = React.useState('');

  if (!isOpen) return null;

  const filteredModules = NAV_MODULES.map((mod) => {
    if (!searchQuery) return mod;
    const q = searchQuery.toLowerCase();
    const matchesTitle = mod.title.toLowerCase().includes(q);
    const matchedApps = mod.apps.filter(
      (a) => a.title.toLowerCase().includes(q) || a.description?.toLowerCase().includes(q)
    );
    const matchedActions = mod.quickActions.filter((a) => a.title.toLowerCase().includes(q));

    if (matchesTitle || matchedApps.length > 0 || matchedActions.length > 0) {
      return {
        ...mod,
        apps: matchesTitle ? mod.apps : matchedApps,
        quickActions: matchesTitle ? mod.quickActions : matchedActions,
      };
    }
    return null;
  }).filter(Boolean) as NavModule[];

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Slideout Panel */}
      <div className="relative w-full max-w-md sm:max-w-lg bg-white h-full shadow-2xl flex flex-col z-10 animate-in slide-in-from-left duration-200">
        {/* Header */}
        <div className="bg-[#3F1D5C] text-white p-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 rounded bg-gradient-to-br from-[#844db3] to-[#5B2C83] flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-4 h-4 text-amber-300 fill-current">
                <polygon points="12,2 21,7.5 21,16.5 12,22 3,16.5 3,7.5" fill="none" stroke="currentColor" strokeWidth="2" />
                <path d="M12 7v10M7 12h10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
            </div>
            <span className="font-bold text-lg">Navigator</span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-[#5B2C83] text-gray-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="p-3 border-b border-gray-100 bg-gray-50">
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search apps and tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#5B2C83] focus:border-[#5B2C83]"
            />
          </div>
        </div>

        {/* Modules List */}
        <div className="flex-1 overflow-y-auto divide-y divide-gray-100 p-2">
          {filteredModules.map((mod) => {
            const IconComponent = mod.icon;
            return (
              <div key={mod.id} className="py-3 px-2">
                <div className="flex items-center space-x-2 mb-2 text-[#5B2C83]">
                  <IconComponent className="w-5 h-5" />
                  <h3 className="font-bold text-sm tracking-wide text-gray-900">{mod.title}</h3>
                </div>

                {/* Apps Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pl-7 mb-2">
                  {mod.apps.map((app) => (
                    <button
                      key={app.route}
                      onClick={() => {
                        onNavigate(app.route);
                        onClose();
                      }}
                      className="text-left p-2 rounded hover:bg-plum-50 text-gray-700 hover:text-[#5B2C83] transition-colors border border-transparent hover:border-plum-200 group"
                    >
                      <div className="text-xs font-semibold group-hover:underline flex items-center justify-between">
                        <span>{app.title}</span>
                        <ChevronRight className="w-3 h-3 text-gray-400 group-hover:text-[#5B2C83]" />
                      </div>
                      {app.description && (
                        <div className="text-[10px] text-gray-500 line-clamp-1 mt-0.5">
                          {app.description}
                        </div>
                      )}
                    </button>
                  ))}
                </div>

                {/* Quick actions line */}
                {mod.quickActions.length > 0 && (
                  <div className="pl-7 flex flex-wrap gap-1.5 text-[11px]">
                    <span className="text-gray-400 font-medium self-center text-[10px] uppercase">Quick:</span>
                    {mod.quickActions.map((qa) => (
                      <button
                        key={qa.title}
                        onClick={() => {
                          onNavigate(qa.route);
                          onClose();
                        }}
                        className="bg-gray-100 hover:bg-amber-100 hover:text-amber-900 text-gray-700 px-2 py-0.5 rounded text-[11px] transition-colors"
                      >
                        {qa.title}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
          <span>Meridian Healthcare Group</span>
          <button
            onClick={() => {
              onNavigate('#/tools/integrity');
              onClose();
            }}
            className="text-emerald-700 font-semibold hover:underline flex items-center space-x-1"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Integrity Check</span>
          </button>
        </div>
      </div>
    </div>
  );
};
