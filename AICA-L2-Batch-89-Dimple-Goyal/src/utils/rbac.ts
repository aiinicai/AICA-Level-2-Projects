import { UserRole } from '../types';
import { ActiveTab } from '../components/layout/Sidebar';

export interface RolePermissions {
  role: UserRole;
  displayName: string;
  badgeClass: string;
  allowedTabs: ActiveTab[];
  canUploadInvoices: boolean;
  canUploadBankStatements: boolean;
  canUpload26AS: boolean;
  canUploadGSTR1: boolean;
  canReconcile: boolean;
  canCreateInvoices: boolean;
  canCreateBankEntries: boolean;
  canEditCustomers: boolean;
  canDeleteRecords: boolean;
  canManageSettings: boolean;
  canResolveExceptions: boolean;
  description: string;
}

export const ROLE_DEFINITIONS: Record<UserRole, RolePermissions> = {
  'Business Owner': {
    role: 'Business Owner',
    displayName: 'Business Owner / Admin',
    badgeClass: 'bg-purple-100 text-purple-900 border-purple-300',
    allowedTabs: [
      'dashboard',
      'customers',
      'invoices',
      'payments',
      'reconciliation',
      'ageing',
      'tds',
      'gst',
      'exceptions',
      'reports',
      'documents',
      'settings',
      'tests'
    ],
    canUploadInvoices: true,
    canUploadBankStatements: true,
    canUpload26AS: true,
    canUploadGSTR1: true,
    canReconcile: true,
    canCreateInvoices: true,
    canCreateBankEntries: true,
    canEditCustomers: true,
    canDeleteRecords: true,
    canManageSettings: true,
    canResolveExceptions: true,
    description: 'Full unrestricted governance, multi-tenant company setup, master approvals, and user role configuration.'
  },

  'Finance Manager': {
    role: 'Finance Manager',
    displayName: 'Finance Manager',
    badgeClass: 'bg-emerald-100 text-emerald-900 border-emerald-300',
    allowedTabs: [
      'dashboard',
      'customers',
      'invoices',
      'payments',
      'reconciliation',
      'ageing',
      'tds',
      'gst',
      'exceptions',
      'reports',
      'documents',
      'tests'
    ],
    canUploadInvoices: true,
    canUploadBankStatements: true,
    canUpload26AS: true,
    canUploadGSTR1: true,
    canReconcile: true,
    canCreateInvoices: true,
    canCreateBankEntries: true,
    canEditCustomers: true,
    canDeleteRecords: false,
    canManageSettings: false,
    canResolveExceptions: true,
    description: 'Financial controls, high-value payment allocations, exception resolutions, tolerance configurations, and statutory reports.'
  },

  'Accountant': {
    role: 'Accountant',
    displayName: 'Operational Accountant',
    badgeClass: 'bg-blue-100 text-blue-900 border-blue-300',
    allowedTabs: [
      'dashboard',
      'customers',
      'invoices',
      'payments',
      'reconciliation',
      'ageing',
      'tds',
      'gst',
      'documents'
    ],
    canUploadInvoices: true,
    canUploadBankStatements: true,
    canUpload26AS: true,
    canUploadGSTR1: true,
    canReconcile: true,
    canCreateInvoices: true,
    canCreateBankEntries: true,
    canEditCustomers: true,
    canDeleteRecords: false,
    canManageSettings: false,
    canResolveExceptions: false,
    description: 'Operational data entry, batch invoice imports, bank statement feeds, 26AS/GSTR-1 imports, and day-to-day reconciliation.'
  },

  'CA / Consultant': {
    role: 'CA / Consultant',
    displayName: 'Chartered Accountant / Tax Auditor',
    badgeClass: 'bg-amber-100 text-amber-900 border-amber-300',
    allowedTabs: [
      'dashboard',
      'invoices',
      'reconciliation',
      'ageing',
      'tds',
      'gst',
      'reports',
      'documents',
      'tests'
    ],
    canUploadInvoices: false,
    canUploadBankStatements: false,
    canUpload26AS: true,
    canUploadGSTR1: true,
    canReconcile: true,
    canCreateInvoices: false,
    canCreateBankEntries: false,
    canEditCustomers: false,
    canDeleteRecords: false,
    canManageSettings: false,
    canResolveExceptions: true,
    description: 'Statutory audit, TDS 26AS compliance, GSTR-1 debtor-wise variance audit, accounting test validation, and tax reports.'
  },

  'Viewer': {
    role: 'Viewer',
    displayName: 'Read-Only Viewer',
    badgeClass: 'bg-slate-100 text-slate-700 border-slate-300',
    allowedTabs: [
      'dashboard',
      'ageing',
      'reports'
    ],
    canUploadInvoices: false,
    canUploadBankStatements: false,
    canUpload26AS: false,
    canUploadGSTR1: false,
    canReconcile: false,
    canCreateInvoices: false,
    canCreateBankEntries: false,
    canEditCustomers: false,
    canDeleteRecords: false,
    canManageSettings: false,
    canResolveExceptions: false,
    description: 'Read-only stakeholder access to executive dashboards, aging receivables analytics, and management summaries.'
  }
};

/**
 * Checks if a role is authorized to access a given navigation tab
 */
export function isTabAllowed(role: UserRole, tab: ActiveTab): boolean {
  const perms = ROLE_DEFINITIONS[role];
  if (!perms) return false;
  return perms.allowedTabs.includes(tab);
}

export const hasTabAccess = isTabAllowed;

/**
 * Get human-readable module title for tab
 */
export function getTabTitle(tab: ActiveTab): string {
  const map: Record<ActiveTab, string> = {
    dashboard: 'Executive Dashboard',
    customers: 'Customer Master',
    invoices: 'Sales / Invoices Register',
    payments: 'Bank Payments & Statements',
    reconciliation: '3-Way Reconciliation Centre',
    ageing: 'Receivables Ageing Matrix',
    tds: 'TDS & Form 26AS Verification',
    gst: 'GST Reconciliation (GSTR-1 Debtor-wise)',
    exceptions: 'Exceptions & Dispute Center',
    reports: 'Statutory Reports & Audit Export',
    documents: 'Document Storage & Proofs',
    settings: 'Platform Settings & User Access',
    tests: 'Accounting Integrity Test Suite'
  };
  return map[tab] || tab;
}

/**
 * Get list of roles authorized to view a specific tab
 */
export function getAuthorizedRolesForTab(tab: ActiveTab): UserRole[] {
  return (Object.keys(ROLE_DEFINITIONS) as UserRole[]).filter(r =>
    ROLE_DEFINITIONS[r].allowedTabs.includes(tab)
  );
}
