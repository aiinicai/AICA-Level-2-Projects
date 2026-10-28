import { User, TransactionStatus, ERPModule } from './types';
import { USERS, findUserById } from '../data/users';
import {
  checkApproverPermission,
  checkMakerPermission,
  getModuleAccess,
  getUserModuleRole,
  getAccessMatrix,
  saveAccessMatrix,
  getUserAccessSummary,
} from './accessMatrix';

export {
  checkApproverPermission,
  checkMakerPermission,
  getModuleAccess,
  getUserModuleRole,
  getAccessMatrix,
  saveAccessMatrix,
  getUserAccessSummary,
};

const ACTIVE_USER_KEY = 'medicore_active_user';

export function getActiveUser(): User {
  try {
    const stored = localStorage.getItem(ACTIVE_USER_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      const user = findUserById(parsed.userId);
      if (user) return user;
    }
  } catch {
    // fallback
  }
  // Default to Charlotte Davis (primary demo user)
  return USERS[0];
}

export function setActiveUser(user: User): void {
  localStorage.setItem(ACTIVE_USER_KEY, JSON.stringify(user));
  window.dispatchEvent(new Event('medicore-user-changed'));
}

export function signOut(): void {
  localStorage.removeItem(ACTIVE_USER_KEY);
  window.dispatchEvent(new Event('medicore-user-changed'));
}

export interface ApprovalCheckResult {
  allowed: boolean;
  reason?: string;
  mustEscalate?: boolean;
}

export function checkCanApprove(
  user: User,
  txn: { createdBy: string; totalAmount?: number; amount?: number; status: TransactionStatus },
  module?: ERPModule
): ApprovalCheckResult {
  // If transaction is not pending approval
  if (txn.status !== 'Pending Approval' && txn.status !== 'Pending Higher Approval') {
    return {
      allowed: false,
      reason: `Transaction is in '${txn.status}' status, cannot be approved`,
    };
  }

  // Segregation of Duties: cannot approve own transaction
  if (txn.createdBy && txn.createdBy.toLowerCase() === user.userId.toLowerCase()) {
    return {
      allowed: false,
      reason: 'Segregation of Duties: You cannot approve a transaction you created',
    };
  }

  const amount = txn.totalAmount ?? txn.amount ?? 0;

  // If specific module provided, enforce exact module approver matrix
  if (module) {
    return checkApproverPermission(user, module, amount, txn.createdBy);
  }

  // Fallback: CFO or Finance Controller with limits
  if (user.role !== 'Finance Controller' && user.role !== 'CFO') {
    return {
      allowed: false,
      reason: `Users with role '${user.role}' do not have approval permissions`,
    };
  }

  if (user.approvalLimitAED !== null && amount > user.approvalLimitAED) {
    return {
      allowed: false,
      mustEscalate: true,
      reason: `Exceeds your approval limit of AED ${user.approvalLimitAED.toLocaleString()}; escalate to CFO`,
    };
  }

  return { allowed: true };
}

export function checkCanEdit(
  user: User,
  txn: { createdBy: string; status: TransactionStatus },
  module?: ERPModule
): { allowed: boolean; reason?: string } {
  if (txn.status !== 'Draft' && txn.status !== 'Rejected') {
    return {
      allowed: false,
      reason: `Transactions in '${txn.status}' status are read-only and cannot be edited.`,
    };
  }

  // If module specified, check Maker permission
  if (module) {
    const makerCheck = checkMakerPermission(user, module);
    if (!makerCheck.allowed) {
      return makerCheck;
    }
  }

  // Creator can edit
  if (txn.createdBy.toLowerCase() === user.userId.toLowerCase()) {
    return { allowed: true };
  }

  return {
    allowed: false,
    reason: 'Only the original Maker who created this draft can edit it.',
  };
}
