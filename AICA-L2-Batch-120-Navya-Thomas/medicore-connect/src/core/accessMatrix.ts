/**
 * MediCore Connect - Enterprise Access Control & Maker-Approver Matrix
 * Section 1: View for all, one Maker and one Approver per module
 */

import { ERPModule, ModuleAccessConfig, User } from './types';
import { USERS, findUserById } from '../data/users';

const ACCESS_MATRIX_STORAGE_KEY = 'medicore_access_matrix_v2';

export const DEFAULT_ACCESS_MATRIX: ModuleAccessConfig[] = [
  {
    module: 'Procurement',
    makerUserId: 'liam.carter',
    makerName: 'Liam Carter',
    approverUserId: 'daniel.reed',
    approverName: 'Daniel Reed',
    approvalLimitAED: null, // Unlimited
    description: 'Purchase Requisitions, Purchase Orders & Supplier Sourcing',
  },
  {
    module: 'Supply Chain Execution',
    makerUserId: 'noah.bennett',
    makerName: 'Noah Bennett',
    approverUserId: 'charlotte.davis',
    approverName: 'Charlotte Davis',
    approvalLimitAED: 250000,
    description: 'Goods Receipts (GRN), Inventory, Stock Transfers & Consumption Adjustments',
  },
  {
    module: 'Payables',
    makerUserId: 'omar.haddad',
    makerName: 'Omar Haddad',
    approverUserId: 'charlotte.davis',
    approverName: 'Charlotte Davis',
    approvalLimitAED: 250000,
    description: 'Supplier Invoices, Credit Memos, Supplier Payments & 3-Way Match',
  },
  {
    module: 'Receivables',
    makerUserId: 'sofia.marin',
    makerName: 'Sofia Marin',
    approverUserId: 'charlotte.davis',
    approverName: 'Charlotte Davis',
    approvalLimitAED: 250000,
    description: 'Patient/Insurance Billing, Credit Memos, Receipts & Cash Applications',
  },
  {
    module: 'Fixed Assets',
    makerUserId: 'henry.brooks',
    makerName: 'Henry Brooks',
    approverUserId: 'daniel.reed',
    approverName: 'Daniel Reed',
    approvalLimitAED: null,
    description: 'Asset Additions, Capitalisations, Depreciation Runs, Adjustments & Retirements',
  },
  {
    module: 'Cash Management',
    makerUserId: 'aisha.khan',
    makerName: 'Aisha Khan',
    approverUserId: 'charlotte.davis',
    approverName: 'Charlotte Davis',
    approvalLimitAED: 250000,
    description: 'Petty Cash Vouchers, Main Cash, Bank Statements & Reconciliations',
  },
  {
    module: 'Intercompany Accounting',
    makerUserId: 'emma.collins',
    makerName: 'Emma Collins',
    approverUserId: 'daniel.reed',
    approverName: 'Daniel Reed',
    approvalLimitAED: null,
    description: 'Intercompany Invoices, Credit Notes, Cross-BU Transfers & Reconciliations',
  },
  {
    module: 'General Accounting',
    makerUserId: 'charlotte.davis',
    makerName: 'Charlotte Davis',
    approverUserId: 'daniel.reed',
    approverName: 'Daniel Reed',
    approvalLimitAED: null,
    description: 'General Ledger Manual Journals, Recurring Accruals & Chart of Accounts changes',
  },
];

export function getAccessMatrix(): ModuleAccessConfig[] {
  try {
    const raw = localStorage.getItem(ACCESS_MATRIX_STORAGE_KEY);
    if (raw) {
      const parsed: ModuleAccessConfig[] = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length >= DEFAULT_ACCESS_MATRIX.length) {
        return parsed;
      }
    }
  } catch {
    // fallback
  }
  return DEFAULT_ACCESS_MATRIX;
}

export function saveAccessMatrix(matrix: ModuleAccessConfig[]): void {
  localStorage.setItem(ACCESS_MATRIX_STORAGE_KEY, JSON.stringify(matrix));
  window.dispatchEvent(new Event('medicore-access-matrix-changed'));
}

export function getModuleAccess(module: ERPModule): ModuleAccessConfig {
  const matrix = getAccessMatrix();
  const rule = matrix.find((m) => m.module.toLowerCase() === module.toLowerCase());
  if (rule) return rule;

  const defaultRule = DEFAULT_ACCESS_MATRIX.find((m) => m.module.toLowerCase() === module.toLowerCase());
  if (defaultRule) return defaultRule;

  // Fallback safe rule
  return {
    module,
    makerUserId: 'charlotte.davis',
    makerName: 'Charlotte Davis',
    approverUserId: 'daniel.reed',
    approverName: 'Daniel Reed',
    approvalLimitAED: 250000,
  };
}

/**
 * Checks whether the user is the designated Maker for a module.
 */
export function checkMakerPermission(
  user: User,
  module: ERPModule
): { allowed: boolean; reason?: string } {
  // Period close, Reset Demo Data, Access and Roles are CFO-only
  if (module === 'Period Close' || module === 'Access and Roles') {
    if (user.role === 'CFO' || user.userId === 'daniel.reed') {
      return { allowed: true };
    }
    return {
      allowed: false,
      reason: `Only the CFO (Daniel Reed) has administrative authorization for ${module}.`,
    };
  }

  const access = getModuleAccess(module);
  if (user.userId.toLowerCase() === access.makerUserId.toLowerCase()) {
    return { allowed: true };
  }

  return {
    allowed: false,
    reason: `Only the designated ${module} Maker (${access.makerName}) is authorized to create, edit, or submit transactions in this module.`,
  };
}

/**
 * Checks whether the user is authorized to approve/reject in a module.
 */
export function checkApproverPermission(
  user: User,
  module: ERPModule,
  amountAED = 0,
  createdBy?: string
): { allowed: boolean; mustEscalate?: boolean; reason?: string } {
  // Segregation of Duties: cannot approve own transaction
  if (createdBy && createdBy.toLowerCase() === user.userId.toLowerCase()) {
    return {
      allowed: false,
      reason: 'Segregation of Duties: You cannot approve a transaction you created.',
    };
  }

  // CFO has overarching approval capability when escalated or designated
  if (user.role === 'CFO' || user.userId === 'daniel.reed') {
    return { allowed: true };
  }

  const access = getModuleAccess(module);
  const isNamedApprover = user.userId.toLowerCase() === access.approverUserId.toLowerCase();

  if (!isNamedApprover) {
    return {
      allowed: false,
      reason: `Only the designated ${module} Approver (${access.approverName}) is authorized to approve or reject items in this module.`,
    };
  }

  // Check approval limit
  if (access.approvalLimitAED !== null && amountAED > access.approvalLimitAED) {
    return {
      allowed: false,
      mustEscalate: true,
      reason: `Transaction amount (AED ${amountAED.toLocaleString()}) exceeds ${access.approverName}'s approval limit of AED ${access.approvalLimitAED.toLocaleString()}; must escalate to CFO (Daniel Reed).`,
    };
  }

  return { allowed: true };
}

/**
 * Returns the user's role on the specific module
 */
export function getUserModuleRole(user: User, module: ERPModule): 'Maker' | 'Approver' | 'Viewer' {
  const access = getModuleAccess(module);
  if (user.userId.toLowerCase() === access.makerUserId.toLowerCase()) return 'Maker';
  if (user.userId.toLowerCase() === access.approverUserId.toLowerCase() || user.role === 'CFO') return 'Approver';
  return 'Viewer';
}

/**
 * Returns access overview for "My Access"
 */
export function getUserAccessSummary(user: User) {
  const matrix = getAccessMatrix();
  const isCFO = user.role === 'CFO' || user.userId === 'daniel.reed';
  const makerModules: ERPModule[] = [];
  const approverModules: ERPModule[] = [];
  const viewerModules: ERPModule[] = [];

  for (const m of matrix) {
    if (user.userId.toLowerCase() === m.makerUserId.toLowerCase()) {
      makerModules.push(m.module);
    } else if (user.userId.toLowerCase() === m.approverUserId.toLowerCase() || isCFO) {
      approverModules.push(m.module);
    } else {
      viewerModules.push(m.module);
    }
  }

  return {
    isCFO,
    makerModules,
    approverModules,
    viewerModules,
  };
}
