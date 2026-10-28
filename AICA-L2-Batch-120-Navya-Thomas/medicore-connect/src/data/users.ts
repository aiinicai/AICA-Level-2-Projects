import { User } from '../core/types';

export const USERS: User[] = [
  {
    userId: 'charlotte.davis',
    name: 'Charlotte Davis',
    role: 'Finance Controller',
    password: 'Charlotte@2026',
    approvalLimitAED: 250000,
    department: 'Administration',
  },
  {
    userId: 'daniel.reed',
    name: 'Daniel Reed',
    role: 'CFO',
    password: 'Daniel@2026',
    approvalLimitAED: null, // Unlimited
    department: 'Administration',
  },
  {
    userId: 'omar.haddad',
    name: 'Omar Haddad',
    role: 'AP Maker',
    password: 'Omar@2026',
    approvalLimitAED: 0,
    department: 'Procurement',
  },
  {
    userId: 'sofia.marin',
    name: 'Sofia Marin',
    role: 'AR Maker',
    password: 'Sofia@2026',
    approvalLimitAED: 0,
    department: 'Clinical',
  },
  {
    userId: 'liam.carter',
    name: 'Liam Carter',
    role: 'Procurement Maker / Buyer',
    password: 'Liam@2026',
    approvalLimitAED: 0,
    department: 'Procurement',
  },
  {
    userId: 'noah.bennett',
    name: 'Noah Bennett',
    role: 'Store Controller',
    password: 'Noah@2026',
    approvalLimitAED: 0,
    department: 'Procurement',
  },
  {
    userId: 'aisha.khan',
    name: 'Aisha Khan',
    role: 'Treasury Maker',
    password: 'Aisha@2026',
    approvalLimitAED: 0,
    department: 'Administration',
  },
  {
    userId: 'henry.brooks',
    name: 'Henry Brooks',
    role: 'Fixed Asset Accountant',
    password: 'Henry@2026',
    approvalLimitAED: 0,
    department: 'Facilities',
  },
  {
    userId: 'emma.collins',
    name: 'Emma Collins',
    role: 'Intercompany Accountant',
    password: 'Emma@2026',
    approvalLimitAED: 0,
    department: 'Administration',
  },
];

export function findUserById(userId: string): User | undefined {
  return USERS.find((u) => u.userId.toLowerCase() === userId.toLowerCase());
}
