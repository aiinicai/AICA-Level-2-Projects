import React, { useState, useMemo } from 'react';
import {
  BookOpen,
  FolderTree,
  Table as TableIcon,
  Plus,
  Search,
  Filter,
  Download,
  Building2,
  Layers,
  ChevronRight,
  ChevronDown,
  Eye,
  Edit2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Lock,
  ArrowRight,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { Account, AccountType } from '../../core/types';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { DEPARTMENTS } from '../../data/chartOfAccounts';
import { ModuleAccessBanner } from '../../components/ModuleAccessBanner';
import { DocLink } from '../../components/DocLink';
import { formatAED, round2, addMoney, subMoney } from '../../core/currency';
import { getActiveUser, checkMakerPermission, checkCanApprove } from '../../core/auth';
import * as XLSX from 'xlsx';

interface ChartOfAccountsPageProps {
  onNavigate: (route: string) => void;
  initialAction?: string;
}

interface RollupGroupDef {
  id: string;
  name: string;
  codeMin: number;
  codeMax: number;
  type: AccountType;
  ifrsCategory: string;
}

const ROLLUP_GROUPS: RollupGroupDef[] = [
  { id: '1000', name: 'Cash and Bank', codeMin: 1000, codeMax: 1099, type: 'Asset', ifrsCategory: 'Cash and cash equivalents' },
  { id: '1100', name: 'Trade Receivables & Allowances', codeMin: 1100, codeMax: 1199, type: 'Asset', ifrsCategory: 'Trade receivables' },
  { id: '1200', name: 'Inventories (Pharma, Consumables, Implants)', codeMin: 1200, codeMax: 1299, type: 'Asset', ifrsCategory: 'Inventories' },
  { id: '1300', name: 'Prepayments and Other Current Assets', codeMin: 1300, codeMax: 1499, type: 'Asset', ifrsCategory: 'Prepayments and other receivables' },
  { id: '1500', name: 'Intercompany Receivables', codeMin: 1500, codeMax: 1599, type: 'Asset', ifrsCategory: 'Due from related units' },
  { id: '1600', name: 'Capital Work in Progress (CWIP)', codeMin: 1600, codeMax: 1699, type: 'Asset', ifrsCategory: 'Property, plant and equipment' },
  { id: '1700', name: 'PPE Cost (Land, Buildings, Medical Eq.)', codeMin: 1700, codeMax: 1799, type: 'Asset', ifrsCategory: 'Property, plant and equipment' },
  { id: '1800', name: 'Accumulated Depreciation', codeMin: 1800, codeMax: 1899, type: 'Contra', ifrsCategory: 'Property, plant and equipment' },
  { id: '2000', name: 'Trade and Other Payables (AP, GRNI, Accruals)', codeMin: 2000, codeMax: 2099, type: 'Liability', ifrsCategory: 'Trade and other payables' },
  { id: '2100', name: 'Tax Payables (VAT Output)', codeMin: 2100, codeMax: 2199, type: 'Liability', ifrsCategory: 'Trade and other payables' },
  { id: '2200', name: 'Employee Liabilities & End of Service', codeMin: 2200, codeMax: 2299, type: 'Liability', ifrsCategory: 'Employee benefits provision' },
  { id: '2300', name: 'Contract Liabilities & Deferred Revenue', codeMin: 2300, codeMax: 2399, type: 'Liability', ifrsCategory: 'Contract liabilities' },
  { id: '2400', name: 'Corporate Tax Payable', codeMin: 2400, codeMax: 2499, type: 'Liability', ifrsCategory: 'Current tax liability' },
  { id: '2500', name: 'Intercompany Payables', codeMin: 2500, codeMax: 2599, type: 'Liability', ifrsCategory: 'Due to related units' },
  { id: '2600', name: 'Lease Liabilities', codeMin: 2600, codeMax: 2699, type: 'Liability', ifrsCategory: 'Lease liabilities' },
  { id: '2700', name: 'Borrowings & Bank Loans', codeMin: 2700, codeMax: 2999, type: 'Liability', ifrsCategory: 'Borrowings' },
  { id: '3000', name: 'Equity & Retained Earnings', codeMin: 3000, codeMax: 3999, type: 'Equity', ifrsCategory: 'Equity & Reserves' },
  { id: '4000', name: 'Revenue from Contracts with Customers', codeMin: 4000, codeMax: 4999, type: 'Revenue', ifrsCategory: 'Revenue' },
  { id: '5000', name: 'Cost of Sales (Medicines, Consumables, Clinical)', codeMin: 5000, codeMax: 5999, type: 'Expense', ifrsCategory: 'Cost of sales' },
  { id: '6000', name: 'Operating & Administrative Expenses', codeMin: 6000, codeMax: 6999, type: 'Expense', ifrsCategory: 'Administrative expenses' },
  { id: '7000', name: 'Other Income, Financing & Tax', codeMin: 7000, codeMax: 7999, type: 'Expense', ifrsCategory: 'Other / Financing / Tax' },
];

const IFRS_LINES = [
  'Cash and cash equivalents',
  'Trade receivables',
  'Inventories',
  'Prepayments and other receivables',
  'Property, plant and equipment (CWIP)',
  'Property, plant and equipment',
  'Trade and other payables',
  'Contract liabilities',
  'Current tax liability',
  'Employee benefits provision',
  'Lease liabilities',
  'Borrowings (current)',
  'Borrowings (non-current)',
  'Due from related units (eliminated on consolidation)',
  'Due to related units (eliminated on consolidation)',
  'Share capital',
  'Retained earnings',
  'Reserves',
  'Revenue from contracts with customers',
  'Cost of sales',
  'Administrative expenses',
  'Selling and distribution expenses',
  'Impairment losses on financial assets',
  'Finance costs',
  'Income tax expense',
  'Other income',
  'Other income / other expenses',
  'Eliminated on consolidation',
];

export const ChartOfAccountsPage: React.FC<ChartOfAccountsPageProps> = ({
  onNavigate,
  initialAction,
}) => {
  const db = getDb();
  const currentUser = getActiveUser();
  const accounts: Account[] = db.accounts && db.accounts.length > 0 ? db.accounts : [];

  const makerCheck = checkMakerPermission(currentUser, 'General Accounting');
  const approverCheck = checkCanApprove(currentUser, { createdBy: 'charlotte.davis' }, 'General Accounting');

  // Primary navigation / tabs
  const [activeMainTab, setActiveMainTab] = useState<'accounts' | 'segments' | 'combination'>('accounts');
  const [viewMode, setViewMode] = useState<'tree' | 'table'>('tree');
  const [selectedBU, setSelectedBU] = useState<string>('All');

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('All');
  const [filterIfrs, setFilterIfrs] = useState<string>('All');
  const [filterControl, setFilterControl] = useState<string>('All'); // All, Control, Non-Control
  const [filterStatus, setFilterStatus] = useState<string>('All'); // All, Active, Inactive

  // Expanded tree groups
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    '1000': true,
    '1100': true,
    '1200': true,
    '2000': true,
    '4000': true,
    '5000': true,
  });

  // Selected account for drilldown
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);

  // Create / Edit modal state
  const [isModalOpen, setIsModalOpen] = useState(initialAction === 'create');
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [formCode, setFormCode] = useState('');
  const [formName, setFormName] = useState('');
  const [formType, setFormType] = useState<AccountType>('Asset');
  const [formNormalBalance, setFormNormalBalance] = useState<'Debit' | 'Credit'>('Debit');
  const [formIfrsLine, setFormIfrsLine] = useState(IFRS_LINES[0]);
  const [formIsNonCurrent, setFormIsNonCurrent] = useState(false);
  const [formIsControl, setFormIsControl] = useState(false);
  const [formManualAllowed, setFormManualAllowed] = useState(true);
  const [formSubledger, setFormSubledger] = useState<Account['subledgerSource']>('None');
  const [formIsActive, setFormIsActive] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Combination inquiry state
  const [inquiryBU, setInquiryBU] = useState('H01');
  const [inquiryAccountCode, setInquiryAccountCode] = useState('1000');

  // Compute live account balances from glJournals
  const accountBalances = useMemo(() => {
    const map: Record<string, { debit: number; credit: number; balance: number }> = {};

    accounts.forEach((acc) => {
      map[acc.code] = { debit: 0, credit: 0, balance: 0 };
    });

    (db.glJournals || []).forEach((j) => {
      if (j.status !== 'Posted') return;

      j.lines.forEach((l) => {
        if (selectedBU !== 'All' && l.businessUnit !== selectedBU) return;

        if (!map[l.account]) {
          map[l.account] = { debit: 0, credit: 0, balance: 0 };
        }
        const d = l.debit || 0;
        const c = l.credit || 0;
        map[l.account].debit = addMoney(map[l.account].debit, d);
        map[l.account].credit = addMoney(map[l.account].credit, c);
      });
    });

    accounts.forEach((acc) => {
      if (map[acc.code]) {
        const d = map[acc.code].debit;
        const c = map[acc.code].credit;
        map[acc.code].balance = acc.normalBalance === 'Debit' ? subMoney(d, c) : subMoney(c, d);
      }
    });

    return map;
  }, [accounts, db.glJournals, selectedBU]);

  // Filter accounts
  const filteredAccounts = useMemo(() => {
    return accounts.filter((acc) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesCode = acc.code.toLowerCase().includes(q);
        const matchesName = acc.name.toLowerCase().includes(q);
        if (!matchesCode && !matchesName) return false;
      }
      if (filterType !== 'All' && acc.type !== filterType) return false;
      if (filterIfrs !== 'All' && acc.ifrsLine !== filterIfrs) return false;
      if (filterControl === 'Control' && !acc.isControlAccount) return false;
      if (filterControl === 'Non-Control' && acc.isControlAccount) return false;
      if (filterStatus === 'Active' && !acc.isActive) return false;
      if (filterStatus === 'Inactive' && acc.isActive) return false;
      return true;
    });
  }, [accounts, searchQuery, filterType, filterIfrs, filterControl, filterStatus]);

  // Group accounts by rollup group
  const groupedAccounts = useMemo(() => {
    const result: Record<string, Account[]> = {};
    ROLLUP_GROUPS.forEach((g) => {
      result[g.id] = [];
    });

    filteredAccounts.forEach((acc) => {
      const num = parseInt(acc.code, 10);
      const group = ROLLUP_GROUPS.find((g) => num >= g.codeMin && num <= g.codeMax);
      if (group) {
        result[group.id].push(acc);
      }
    });

    return result;
  }, [filteredAccounts]);

  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  };

  const handleOpenCreate = () => {
    if (!makerCheck.allowed) {
      setToastMessage(makerCheck.reason || 'Only Charlotte Davis (General Accounting Maker) can create accounts.');
      return;
    }
    setEditingAccount(null);
    setFormCode('');
    setFormName('');
    setFormType('Asset');
    setFormNormalBalance('Debit');
    setFormIfrsLine(IFRS_LINES[0]);
    setFormIsNonCurrent(false);
    setFormIsControl(false);
    setFormManualAllowed(true);
    setFormSubledger('None');
    setFormIsActive(true);
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (acc: Account) => {
    if (!makerCheck.allowed) {
      setToastMessage(makerCheck.reason || 'Only Charlotte Davis can edit accounts.');
      return;
    }
    setEditingAccount(acc);
    setFormCode(acc.code);
    setFormName(acc.name);
    setFormType(acc.type);
    setFormNormalBalance(acc.normalBalance);
    setFormIfrsLine(acc.ifrsLine);
    setFormIsNonCurrent(Boolean(acc.isNonCurrent));
    setFormIsControl(Boolean(acc.isControlAccount));
    setFormManualAllowed(Boolean(acc.manualJournalAllowed));
    setFormSubledger(acc.subledgerSource || 'None');
    setFormIsActive(acc.isActive);
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSaveAccount = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    // 1. Validation
    const cleanCode = formCode.trim();
    if (!cleanCode || cleanCode.length !== 4 || !/^\d{4}$/.test(cleanCode)) {
      setFormError('Account code must be exactly 4 numeric digits (e.g. 1050, 2040).');
      return;
    }

    if (!formName.trim()) {
      setFormError('Account name is required.');
      return;
    }

    // Check code range for type
    const cNum = parseInt(cleanCode, 10);
    if (formType === 'Asset' && (cNum < 1000 || cNum > 1999)) {
      setFormError('Asset account code must be in the range 1000–1999.');
      return;
    }
    if (formType === 'Liability' && (cNum < 2000 || cNum > 2999)) {
      setFormError('Liability account code must be in the range 2000–2999.');
      return;
    }
    if (formType === 'Equity' && (cNum < 3000 || cNum > 3999)) {
      setFormError('Equity account code must be in the range 3000–3999.');
      return;
    }
    if (formType === 'Revenue' && (cNum < 4000 || cNum > 4999)) {
      setFormError('Revenue account code must be in the range 4000–4999.');
      return;
    }
    if (formType === 'Expense' && (cNum < 5000 || cNum > 7999)) {
      setFormError('Expense account code must be in the range 5000–7999.');
      return;
    }

    // Check unique code if creating
    if (!editingAccount) {
      const exists = accounts.some((a) => a.code === cleanCode);
      if (exists) {
        setFormError(`Account code ${cleanCode} already exists.`);
        return;
      }
    } else {
      // If editing existing account:
      // Validation: cannot change type if postings exist
      const bal = accountBalances[editingAccount.code];
      const hasPostings = (bal?.debit || 0) > 0 || (bal?.credit || 0) > 0;
      if (hasPostings && editingAccount.type !== formType) {
        setFormError('Cannot change the account type of an account that has existing transactions or postings.');
        return;
      }
      // Cannot inactivate if balance is not zero
      if (editingAccount.isActive && !formIsActive && Math.abs(bal?.balance || 0) > 0.005) {
        setFormError(`Cannot inactivate account ${editingAccount.code} with a non-zero balance (AED ${formatAED(bal?.balance || 0)}). Inactivation is blocked until balance is zero.`);
        return;
      }
    }

    const updatedAccount: Account = {
      code: cleanCode,
      name: formName.trim(),
      type: formType,
      normalBalance: formNormalBalance,
      ifrsLine: formIfrsLine,
      isNonCurrent: formIsNonCurrent,
      isControlAccount: formIsControl,
      manualJournalAllowed: formIsControl ? false : formManualAllowed,
      subledgerSource: formSubledger,
      isActive: formIsActive,
      createdBy: editingAccount ? editingAccount.createdBy : currentUser.userId,
      approvedBy: approverCheck.allowed ? currentUser.userId : 'daniel.reed',
    };

    updateDb((state) => {
      if (!state.accounts) state.accounts = [];
      const idx = state.accounts.findIndex((a) => a.code === cleanCode);
      if (idx >= 0) {
        state.accounts[idx] = updatedAccount;
      } else {
        state.accounts.push(updatedAccount);
        state.accounts.sort((a, b) => a.code.localeCompare(b.code));
      }
    });

    addAuditLog({
      entityType: 'ChartOfAccounts',
      entityId: cleanCode,
      action: editingAccount ? 'UPDATE' : 'CREATE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `${editingAccount ? 'Updated' : 'Created'} account ${cleanCode} - ${updatedAccount.name} (${updatedAccount.type}, IFRS: ${updatedAccount.ifrsLine})`,
      details: updatedAccount as any,
    });

    setToastMessage(`Account ${cleanCode} - ${updatedAccount.name} saved successfully.`);
    setIsModalOpen(false);
  };

  const handleExport = (format: 'xlsx' | 'csv') => {
    const rows = filteredAccounts.map((a) => ({
      Code: a.code,
      Name: a.name,
      Type: a.type,
      'Normal Balance': a.normalBalance,
      'IFRS Statement Line': a.ifrsLine,
      'Current / Non-current': a.isNonCurrent ? 'Non-current' : 'Current',
      'Control Account': a.isControlAccount ? 'Yes' : 'No',
      'Manual Journal Allowed': a.manualJournalAllowed ? 'Yes' : 'No',
      'Subledger Source': a.subledgerSource || 'None',
      Status: a.isActive ? 'Active' : 'Inactive',
      [`YTD Balance (${selectedBU})`]: accountBalances[a.code]?.balance || 0,
    }));

    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Chart of Accounts');

    if (format === 'xlsx') {
      XLSX.writeFile(wb, `MediCore_ChartOfAccounts_${selectedBU}_2026.xlsx`);
    } else {
      XLSX.writeFile(wb, `MediCore_ChartOfAccounts_${selectedBU}_2026.csv`);
    }
  };

  // Ledger lines for selected account drilldown
  const drilldownLines = useMemo(() => {
    if (!selectedAccount) return [];
    const lines: Array<{
      journalNumber: string;
      journalDate: string;
      period: string;
      businessUnit: string;
      sourceModule: string;
      description: string;
      debit: number;
      credit: number;
      sourceDocumentNumber?: string;
    }> = [];

    (db.glJournals || []).forEach((j) => {
      if (j.status !== 'Posted') return;
      j.lines.forEach((l) => {
        if (l.account === selectedAccount.code) {
          if (selectedBU === 'All' || l.businessUnit === selectedBU) {
            lines.push({
              journalNumber: j.number,
              journalDate: j.journalDate,
              period: j.period,
              businessUnit: l.businessUnit,
              sourceModule: j.sourceModule,
              description: l.description || j.description,
              debit: l.debit || 0,
              credit: l.credit || 0,
              sourceDocumentNumber: l.sourceDocumentNumber,
            });
          }
        }
      });
    });

    lines.sort((a, b) => b.journalDate.localeCompare(a.journalDate));
    return lines;
  }, [selectedAccount, db.glJournals, selectedBU]);

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50 select-none">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <BookOpen className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Chart of Accounts & Segments</h1>
            <p className="text-xs text-gray-500">
              Standard 4-digit Account Hierarchy, IFRS Statement Lines & Accounting Flexfield (BU × Account × Dept)
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          {/* Export Options */}
          <button
            onClick={() => handleExport('xlsx')}
            className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 text-xs font-semibold flex items-center space-x-1.5 shadow-xs transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-gray-500" />
            <span>Export Excel</span>
          </button>
          <button
            onClick={() => handleExport('csv')}
            className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 text-xs font-semibold flex items-center space-x-1.5 shadow-xs transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-gray-500" />
            <span>CSV</span>
          </button>

          {/* Create Account Button */}
          {makerCheck.allowed ? (
            <button
              onClick={handleOpenCreate}
              className="px-3.5 py-1.5 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4 text-amber-300" />
              <span>Create Account</span>
            </button>
          ) : (
            <span
              title={makerCheck.reason}
              className="px-3.5 py-1.5 bg-gray-200 text-gray-500 text-xs font-semibold rounded-lg flex items-center space-x-1.5 cursor-not-allowed opacity-70"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Create Account (Locked)</span>
            </span>
          )}
        </div>
      </div>

      {/* Module Access Banner */}
      <div className="mb-4">
        <ModuleAccessBanner module="General Accounting" />
      </div>

      {toastMessage && (
        <div className="mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{toastMessage}</span>
          </div>
          <button onClick={() => setToastMessage(null)} className="text-emerald-700 hover:text-emerald-900 font-bold ml-2">
            ×
          </button>
        </div>
      )}

      {/* Main Tabs: Accounts | Segments | Combination Inquiry */}
      <div className="flex items-center justify-between border-b border-gray-200 mb-4">
        <div className="flex space-x-4">
          <button
            onClick={() => setActiveMainTab('accounts')}
            className={`pb-2.5 text-xs font-bold border-b-2 flex items-center space-x-1.5 transition-colors cursor-pointer ${
              activeMainTab === 'accounts'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Accounts Directory ({accounts.length})</span>
          </button>
          <button
            onClick={() => setActiveMainTab('segments')}
            className={`pb-2.5 text-xs font-bold border-b-2 flex items-center space-x-1.5 transition-colors cursor-pointer ${
              activeMainTab === 'segments'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Accounting Segments (BUs & Depts)</span>
          </button>
          <button
            onClick={() => setActiveMainTab('combination')}
            className={`pb-2.5 text-xs font-bold border-b-2 flex items-center space-x-1.5 transition-colors cursor-pointer ${
              activeMainTab === 'combination'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            <span>Account Combination Inquiry (BU × Account)</span>
          </button>
        </div>

        {activeMainTab === 'accounts' && (
          <div className="flex items-center space-x-2 pb-2">
            <div className="bg-gray-100 p-0.5 rounded-lg border border-gray-200 flex items-center">
              <button
                onClick={() => setViewMode('tree')}
                className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1 transition-all cursor-pointer ${
                  viewMode === 'tree'
                    ? 'bg-white text-[#5B2C83] shadow-xs'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <FolderTree className="w-3.5 h-3.5" />
                <span>Hierarchy View</span>
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1 transition-all cursor-pointer ${
                  viewMode === 'table'
                    ? 'bg-white text-[#5B2C83] shadow-xs'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <TableIcon className="w-3.5 h-3.5" />
                <span>Flat Table View</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* TAB 1: ACCOUNTS */}
      {activeMainTab === 'accounts' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="bg-white p-3.5 rounded-xl border border-gray-200 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2.5 flex-1">
              {/* Text Search */}
              <div className="relative min-w-[200px]">
                <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search code or account name..."
                  className="w-full pl-8 pr-3 py-1.5 bg-gray-50 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
                />
              </div>

              {/* BU Selector (Live Balance Context) */}
              <div className="flex items-center space-x-1.5">
                <span className="text-gray-500 font-medium">BU Balance:</span>
                <select
                  value={selectedBU}
                  onChange={(e) => setSelectedBU(e.target.value)}
                  className="py-1.5 px-2 bg-gray-50 border border-gray-300 rounded-lg text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
                >
                  <option value="All">All 15 Units (Consolidated)</option>
                  {BUSINESS_UNITS.map((bu) => (
                    <option key={bu.code} value={bu.code}>
                      {bu.code} - {bu.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Account Type Filter */}
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="py-1.5 px-2 bg-gray-50 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
              >
                <option value="All">All Types</option>
                <option value="Asset">Asset</option>
                <option value="Liability">Liability</option>
                <option value="Equity">Equity</option>
                <option value="Revenue">Revenue</option>
                <option value="Expense">Expense</option>
                <option value="Contra">Contra Asset</option>
              </select>

              {/* IFRS Line Filter */}
              <select
                value={filterIfrs}
                onChange={(e) => setFilterIfrs(e.target.value)}
                className="py-1.5 px-2 bg-gray-50 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#5B2C83] max-w-[180px] truncate"
              >
                <option value="All">All IFRS Lines</option>
                {IFRS_LINES.map((line) => (
                  <option key={line} value={line}>
                    {line}
                  </option>
                ))}
              </select>

              {/* Control Account Filter */}
              <select
                value={filterControl}
                onChange={(e) => setFilterControl(e.target.value)}
                className="py-1.5 px-2 bg-gray-50 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
              >
                <option value="All">All Accounts</option>
                <option value="Control">Control Accounts Only</option>
                <option value="Non-Control">Manual Allowed Only</option>
              </select>

              {/* Status Filter */}
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="py-1.5 px-2 bg-gray-50 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
              >
                <option value="All">Active & Inactive</option>
                <option value="Active">Active Only</option>
                <option value="Inactive">Inactive Only</option>
              </select>
            </div>

            <div className="text-gray-500 font-medium">
              Showing <strong className="text-gray-800">{filteredAccounts.length}</strong> of {accounts.length} accounts
            </div>
          </div>

          {/* VIEW 1: HIERARCHY TREE VIEW */}
          {viewMode === 'tree' ? (
            <div className="space-y-3">
              {ROLLUP_GROUPS.map((group) => {
                const groupAccounts = groupedAccounts[group.id] || [];
                if (groupAccounts.length === 0 && (searchQuery || filterType !== 'All' || filterIfrs !== 'All' || filterControl !== 'All' || filterStatus !== 'All')) {
                  return null; // hide empty groups during active filter
                }

                const isExpanded = Boolean(expandedGroups[group.id]);
                // Compute rollup balance
                let groupBalance = 0;
                groupAccounts.forEach((a) => {
                  groupBalance = addMoney(groupBalance, accountBalances[a.code]?.balance || 0);
                });

                return (
                  <div key={group.id} className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
                    {/* Rollup Header */}
                    <div
                      onClick={() => toggleGroup(group.id)}
                      className="px-4 py-3 bg-gray-50/80 hover:bg-plum-50/40 border-b border-gray-200 flex items-center justify-between cursor-pointer transition-colors"
                    >
                      <div className="flex items-center space-x-2.5">
                        <button className="text-gray-500 hover:text-gray-800">
                          {isExpanded ? <ChevronDown className="w-4 h-4 text-[#5B2C83]" /> : <ChevronRight className="w-4 h-4" />}
                        </button>
                        <span className="font-mono font-bold text-xs px-2 py-0.5 rounded bg-plum-100 text-[#5B2C83]">
                          {group.codeMin}–{group.codeMax}
                        </span>
                        <span className="font-bold text-xs text-gray-900">{group.name}</span>
                        <span className="text-[11px] text-gray-500">
                          ({groupAccounts.length} {groupAccounts.length === 1 ? 'account' : 'accounts'})
                        </span>
                      </div>

                      <div className="flex items-center space-x-4 text-xs">
                        <span className="text-[11px] text-gray-500">
                          IFRS: <span className="font-medium text-gray-700">{group.ifrsCategory}</span>
                        </span>
                        <div className="text-right">
                          <span className="text-[11px] text-gray-400 block">Rollup Balance ({selectedBU})</span>
                          <span className="font-mono font-bold text-gray-900">
                            AED {formatAED(groupBalance)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Group Accounts List */}
                    {isExpanded && (
                      <div className="divide-y divide-gray-100">
                        {groupAccounts.length === 0 ? (
                          <div className="p-4 text-center text-xs text-gray-400 italic">
                            No accounts match active filters in this rollup range.
                          </div>
                        ) : (
                          groupAccounts.map((acc) => {
                            const bal = accountBalances[acc.code]?.balance || 0;
                            return (
                              <div
                                key={acc.code}
                                className="px-5 py-2.5 hover:bg-gray-50 flex items-center justify-between text-xs transition-colors group"
                              >
                                <div className="flex items-center space-x-3">
                                  <button
                                    onClick={() => setSelectedAccount(acc)}
                                    className="font-mono font-bold text-sm text-[#5B2C83] hover:text-[#3F1D5C] hover:underline cursor-pointer"
                                  >
                                    {acc.code}
                                  </button>
                                  <span className="font-medium text-gray-900">{acc.name}</span>
                                  {acc.isControlAccount && (
                                    <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-semibold">
                                      Control
                                    </span>
                                  )}
                                  {!acc.isActive && (
                                    <span className="px-1.5 py-0.5 rounded bg-rose-100 text-rose-700 text-[10px] font-semibold">
                                      Inactive
                                    </span>
                                  )}
                                  {acc.subledgerSource && acc.subledgerSource !== 'None' && (
                                    <span className="text-[10px] text-gray-400">
                                      [{acc.subledgerSource}]
                                    </span>
                                  )}
                                </div>

                                <div className="flex items-center space-x-6">
                                  <div className="text-right">
                                    <span className="text-[10px] text-gray-400 block">
                                      {acc.normalBalance} Balance
                                    </span>
                                    <span className={`font-mono font-semibold ${bal < 0 ? 'text-rose-600' : 'text-gray-900'}`}>
                                      AED {formatAED(bal)}
                                    </span>
                                  </div>

                                  <div className="flex items-center space-x-1.5 opacity-90 group-hover:opacity-100">
                                    <button
                                      onClick={() => setSelectedAccount(acc)}
                                      title="Account Drill-down & Ledger Lines"
                                      className="p-1 rounded hover:bg-gray-200 text-gray-600 cursor-pointer"
                                    >
                                      <Eye className="w-3.5 h-3.5" />
                                    </button>
                                    {makerCheck.allowed && (
                                      <button
                                        onClick={() => handleOpenEdit(acc)}
                                        title="Edit Account Definition"
                                        className="p-1 rounded hover:bg-plum-100 text-[#5B2C83] cursor-pointer"
                                      >
                                        <Edit2 className="w-3.5 h-3.5" />
                                      </button>
                                    )}
                                  </div>
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            /* VIEW 2: FLAT TABLE VIEW */
            <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider border-b border-plum-200">
                    <tr>
                      <th className="py-2.5 px-3 w-20">Code</th>
                      <th className="py-2.5 px-3 min-w-[200px]">Account Name</th>
                      <th className="py-2.5 px-3 w-24">Type</th>
                      <th className="py-2.5 px-3 w-20">Normal</th>
                      <th className="py-2.5 px-3 min-w-[180px]">IFRS Statement Line</th>
                      <th className="py-2.5 px-3 w-24">Term</th>
                      <th className="py-2.5 px-3 w-24">Subledger</th>
                      <th className="py-2.5 px-3 w-20 text-center">Control</th>
                      <th className="py-2.5 px-3 w-20 text-center">Manual JV</th>
                      <th className="py-2.5 px-3 w-20 text-center">Status</th>
                      <th className="py-2.5 px-3 text-right w-28">YTD Balance ({selectedBU})</th>
                      <th className="py-2.5 px-3 text-center w-20">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {filteredAccounts.map((acc) => {
                      const bal = accountBalances[acc.code]?.balance || 0;
                      return (
                        <tr key={acc.code} className="hover:bg-gray-50">
                          <td className="py-2.5 px-3 font-mono font-bold text-[#5B2C83]">
                            <button
                              onClick={() => setSelectedAccount(acc)}
                              className="hover:underline cursor-pointer"
                            >
                              {acc.code}
                            </button>
                          </td>
                          <td className="py-2.5 px-3 font-medium text-gray-900">{acc.name}</td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-100 text-gray-700">
                              {acc.type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-gray-600">{acc.normalBalance}</td>
                          <td className="py-2.5 px-3 text-gray-700 truncate max-w-[200px]" title={acc.ifrsLine}>
                            {acc.ifrsLine}
                          </td>
                          <td className="py-2.5 px-3 text-gray-600">
                            {acc.isNonCurrent ? 'Non-current' : 'Current'}
                          </td>
                          <td className="py-2.5 px-3 text-gray-600">{acc.subledgerSource || 'None'}</td>
                          <td className="py-2.5 px-3 text-center">
                            {acc.isControlAccount ? (
                              <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold text-[10px]">
                                Yes
                              </span>
                            ) : (
                              <span className="text-gray-400">No</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            {acc.manualJournalAllowed ? (
                              <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold text-[10px]">
                                Yes
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 font-semibold text-[10px]">
                                Blocked
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            {acc.isActive ? (
                              <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold text-[10px]">
                                Active
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-semibold text-[10px]">
                                Inactive
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-gray-900">
                            AED {formatAED(bal)}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <div className="flex items-center justify-center space-x-1">
                              <button
                                onClick={() => setSelectedAccount(acc)}
                                title="Drill-down"
                                className="p-1 rounded hover:bg-gray-100 text-gray-600 cursor-pointer"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>
                              {makerCheck.allowed && (
                                <button
                                  onClick={() => handleOpenEdit(acc)}
                                  title="Edit"
                                  className="p-1 rounded hover:bg-plum-100 text-[#5B2C83] cursor-pointer"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: ACCOUNTING SEGMENTS (BUs & Departments) */}
      {activeMainTab === 'segments' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Business Units Segment (Segment 1) */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
            <div className="px-4 py-3 bg-[#EDE4F5] text-[#3F1D5C] border-b border-plum-200 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Building2 className="w-4 h-4 text-[#5B2C83]" />
                <span className="font-bold text-xs uppercase tracking-wider">
                  Segment 1: Balancing Business Units (15 Entities)
                </span>
              </div>
              <span className="text-[11px] text-plum-700 font-medium">UAE Legal Entities</span>
            </div>
            <div className="p-4 overflow-x-auto max-h-[600px] overflow-y-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-gray-50 text-gray-600 font-semibold">
                  <tr>
                    <th className="py-2 px-3">BU Code</th>
                    <th className="py-2 px-3">Entity Name</th>
                    <th className="py-2 px-3">Type</th>
                    <th className="py-2 px-3">Emirate</th>
                    <th className="py-2 px-3">VAT TRN</th>
                    <th className="py-2 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {BUSINESS_UNITS.map((bu) => (
                    <tr key={bu.code} className="hover:bg-gray-50">
                      <td className="py-2 px-3 font-mono font-bold text-[#5B2C83]">{bu.code}</td>
                      <td className="py-2 px-3 font-semibold text-gray-900">{bu.name}</td>
                      <td className="py-2 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          bu.type === 'Hospital'
                            ? 'bg-plum-100 text-[#5B2C83]'
                            : bu.type === 'Clinic'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}>
                          {bu.type}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-gray-600">{bu.emirate}</td>
                      <td className="py-2 px-3 font-mono text-gray-500">{bu.vatTrn}</td>
                      <td className="py-2 px-3 text-center">
                        <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px] font-semibold">
                          {bu.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Departments Segment (Segment 3) */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
            <div className="px-4 py-3 bg-[#EDE4F5] text-[#3F1D5C] border-b border-plum-200 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-[#5B2C83]" />
                <span className="font-bold text-xs uppercase tracking-wider">
                  Segment 3: Operational Departments (Cost Centers)
                </span>
              </div>
              <span className="text-[11px] text-plum-700 font-medium">8 Standard Centers</span>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-2 gap-3">
                {DEPARTMENTS.map((dept, idx) => (
                  <div key={dept} className="p-3 rounded-lg border border-gray-200 bg-gray-50 flex items-center justify-between">
                    <div>
                      <span className="font-mono text-xs text-gray-400 block">DEP-{String(idx + 1).padStart(2, '0')}</span>
                      <span className="font-semibold text-xs text-gray-900">{dept}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-white border border-gray-200 text-gray-600">
                      Active
                    </span>
                  </div>
                ))}
              </div>

              {/* Flexfield Architecture Note */}
              <div className="mt-6 p-4 rounded-xl bg-plum-50 border border-plum-200 text-xs">
                <h4 className="font-bold text-[#3F1D5C] mb-1">Accounting Flexfield Structure:</h4>
                <div className="font-mono text-xs text-[#5B2C83] bg-white p-2.5 rounded-lg border border-plum-200 font-semibold mb-2">
                  [Business Unit: 3 chars] — [Natural Account: 4 digits] — [Department: Cost Center]
                </div>
                <p className="text-[11px] text-gray-600">
                  Example: <strong className="text-gray-800">H01-1200-Pharmacy</strong> represents Meridian Hospital Dubai Main Pharmacy Stock. Every transaction is balanced and audited along this flexfield.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: ACCOUNT COMBINATION INQUIRY */}
      {activeMainTab === 'combination' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
            <h3 className="font-bold text-xs text-gray-800 uppercase tracking-wider mb-3">
              Account Combination Balance Inquiry
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="block text-gray-600 font-semibold mb-1">Business Unit</label>
                <select
                  value={inquiryBU}
                  onChange={(e) => setInquiryBU(e.target.value)}
                  className="w-full py-2 px-3 bg-gray-50 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
                >
                  {BUSINESS_UNITS.map((bu) => (
                    <option key={bu.code} value={bu.code}>
                      {bu.code} - {bu.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-gray-600 font-semibold mb-1">Natural Account</label>
                <select
                  value={inquiryAccountCode}
                  onChange={(e) => setInquiryAccountCode(e.target.value)}
                  className="w-full py-2 px-3 bg-gray-50 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
                >
                  {accounts.map((a) => (
                    <option key={a.code} value={a.code}>
                      {a.code} - {a.name} ({a.type})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col justify-end">
                <div className="p-2.5 rounded-lg bg-plum-50 border border-plum-200">
                  <span className="text-[10px] text-gray-500 block uppercase font-semibold">Net Balance:</span>
                  <span className="font-mono font-bold text-sm text-[#3F1D5C]">
                    AED {formatAED(accountBalances[inquiryAccountCode]?.balance || 0)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ACCOUNT DETAIL / DRILL-DOWN DRAWER MODAL */}
      {selectedAccount && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={() => setSelectedAccount(null)} />
          <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-4xl max-h-[90vh] flex flex-col z-10 animate-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="bg-[#3F1D5C] text-white px-6 py-4 rounded-t-xl flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <BookOpen className="w-5 h-5 text-amber-300" />
                <div>
                  <h2 className="font-bold text-base">
                    Account Detail: <span className="font-mono text-amber-300">{selectedAccount.code}</span> — {selectedAccount.name}
                  </h2>
                  <p className="text-xs text-plum-200">
                    Type: <strong className="text-white">{selectedAccount.type}</strong> | Normal: <strong className="text-white">{selectedAccount.normalBalance}</strong> | IFRS: {selectedAccount.ifrsLine}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedAccount(null)}
                className="p-1 rounded-full hover:bg-[#5B2C83] text-gray-200 transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
              {/* Account Meta Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <span className="text-gray-400 block text-[10px]">Total Debits</span>
                  <span className="font-mono font-bold text-sm text-gray-900">
                    AED {formatAED(accountBalances[selectedAccount.code]?.debit || 0)}
                  </span>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <span className="text-gray-400 block text-[10px]">Total Credits</span>
                  <span className="font-mono font-bold text-sm text-gray-900">
                    AED {formatAED(accountBalances[selectedAccount.code]?.credit || 0)}
                  </span>
                </div>
                <div className="p-3 bg-plum-50 rounded-lg border border-plum-200">
                  <span className="text-gray-500 block text-[10px]">Net Balance ({selectedBU})</span>
                  <span className="font-mono font-bold text-sm text-[#3F1D5C]">
                    AED {formatAED(accountBalances[selectedAccount.code]?.balance || 0)}
                  </span>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <span className="text-gray-400 block text-[10px]">Subledger Source</span>
                  <span className="font-semibold text-gray-800">
                    {selectedAccount.subledgerSource || 'None'}
                  </span>
                </div>
              </div>

              {/* Drill-down Ledger Lines Table */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-bold text-xs text-gray-800 uppercase tracking-wider">
                    General Ledger Transaction Activity ({drilldownLines.length} postings)
                  </h4>
                  <span className="text-[11px] text-gray-500">Filtered by BU: <strong>{selectedBU}</strong></span>
                </div>

                <div className="border border-gray-200 rounded-lg overflow-hidden max-h-72 overflow-y-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold sticky top-0">
                      <tr>
                        <th className="py-2 px-3">Date</th>
                        <th className="py-2 px-3">Period</th>
                        <th className="py-2 px-3">BU</th>
                        <th className="py-2 px-3">Journal No.</th>
                        <th className="py-2 px-3">Source Doc</th>
                        <th className="py-2 px-3">Description</th>
                        <th className="py-2 px-3 text-right">Debit (AED)</th>
                        <th className="py-2 px-3 text-right">Credit (AED)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {drilldownLines.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="py-6 text-center text-gray-400 italic">
                            No ledger postings found for account {selectedAccount.code} in {selectedBU}.
                          </td>
                        </tr>
                      ) : (
                        drilldownLines.map((l, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="py-2 px-3 text-gray-700">{l.journalDate}</td>
                            <td className="py-2 px-3 text-gray-700 font-medium">{l.period}</td>
                            <td className="py-2 px-3 font-semibold text-gray-800">{l.businessUnit}</td>
                            <td className="py-2 px-3">
                              <DocLink number={l.journalNumber} />
                            </td>
                            <td className="py-2 px-3">
                              {l.sourceDocumentNumber ? (
                                <DocLink number={l.sourceDocumentNumber} />
                              ) : (
                                <span className="text-gray-400">—</span>
                              )}
                            </td>
                            <td className="py-2 px-3 text-gray-800 truncate max-w-xs">{l.description}</td>
                            <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                              {l.debit > 0 ? formatAED(l.debit) : '—'}
                            </td>
                            <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                              {l.credit > 0 ? formatAED(l.credit) : '—'}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CREATE / EDIT ACCOUNT MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={() => setIsModalOpen(false)} />
          <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-lg z-10 animate-in zoom-in-95 duration-150 overflow-hidden">
            <div className="bg-[#3F1D5C] text-white px-6 py-4 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <BookOpen className="w-5 h-5 text-amber-300" />
                <h3 className="font-bold text-sm">
                  {editingAccount ? `Edit Account: ${editingAccount.code}` : 'Create Natural Account'}
                </h3>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="text-gray-200 hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveAccount} className="p-6 space-y-4 text-xs">
              {formError && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">
                    Account Code (4 digits) *
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={4}
                    disabled={Boolean(editingAccount)}
                    value={formCode}
                    onChange={(e) => setFormCode(e.target.value)}
                    placeholder="e.g. 1050"
                    className="w-full py-2 px-3 bg-white border border-gray-300 rounded-lg font-mono focus:outline-none focus:ring-1 focus:ring-[#5B2C83] disabled:bg-gray-100"
                  />
                </div>

                <div>
                  <label className="block text-gray-700 font-semibold mb-1">
                    Account Type *
                  </label>
                  <select
                    value={formType}
                    onChange={(e) => {
                      const newType = e.target.value as AccountType;
                      setFormType(newType);
                      setFormNormalBalance(newType === 'Asset' || newType === 'Expense' ? 'Debit' : 'Credit');
                    }}
                    className="w-full py-2 px-3 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
                  >
                    <option value="Asset">Asset (1000–1999)</option>
                    <option value="Liability">Liability (2000–2999)</option>
                    <option value="Equity">Equity (3000–3999)</option>
                    <option value="Revenue">Revenue (4000–4999)</option>
                    <option value="Expense">Expense (5000–7999)</option>
                    <option value="Contra">Contra Asset</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-gray-700 font-semibold mb-1">
                  Account Name *
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g. Bank – Special Operating Account"
                  className="w-full py-2 px-3 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-700 font-semibold mb-1">
                    Normal Balance *
                  </label>
                  <select
                    value={formNormalBalance}
                    onChange={(e) => setFormNormalBalance(e.target.value as any)}
                    className="w-full py-2 px-3 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
                  >
                    <option value="Debit">Debit</option>
                    <option value="Credit">Credit</option>
                  </select>
                </div>

                <div>
                  <label className="block text-gray-700 font-semibold mb-1">
                    Subledger Source
                  </label>
                  <select
                    value={formSubledger}
                    onChange={(e) => setFormSubledger(e.target.value as any)}
                    className="w-full py-2 px-3 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
                  >
                    <option value="None">None (General Ledger)</option>
                    <option value="Payables">Payables</option>
                    <option value="Receivables">Receivables</option>
                    <option value="Inventory">Inventory</option>
                    <option value="Fixed Assets">Fixed Assets</option>
                    <option value="Cash">Cash Management</option>
                    <option value="Intercompany">Intercompany</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-gray-700 font-semibold mb-1">
                  IFRS Statement Line *
                </label>
                <select
                  value={formIfrsLine}
                  onChange={(e) => setFormIfrsLine(e.target.value)}
                  className="w-full py-2 px-3 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
                >
                  {IFRS_LINES.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2 pt-2 border-t border-gray-200">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formIsControl}
                    onChange={(e) => {
                      setFormIsControl(e.target.checked);
                      if (e.target.checked) setFormManualAllowed(false);
                    }}
                    className="rounded text-[#5B2C83] focus:ring-[#5B2C83]"
                  />
                  <span className="font-semibold text-gray-800">
                    Control Account (Strictly blocked from direct manual journals)
                  </span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formManualAllowed}
                    disabled={formIsControl}
                    onChange={(e) => setFormManualAllowed(e.target.checked)}
                    className="rounded text-[#5B2C83] focus:ring-[#5B2C83]"
                  />
                  <span className="text-gray-700">Manual General Journals Allowed</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formIsNonCurrent}
                    onChange={(e) => setFormIsNonCurrent(e.target.checked)}
                    className="rounded text-[#5B2C83] focus:ring-[#5B2C83]"
                  />
                  <span className="text-gray-700">Non-Current Balance Sheet Item</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formIsActive}
                    onChange={(e) => setFormIsActive(e.target.checked)}
                    className="rounded text-[#5B2C83] focus:ring-[#5B2C83]"
                  />
                  <span className="text-gray-700">Account Active (Available for postings)</span>
                </label>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white font-semibold rounded-lg shadow-xs cursor-pointer"
                >
                  {editingAccount ? 'Save Changes' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
