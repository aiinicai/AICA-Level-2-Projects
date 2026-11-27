/**
 * Phase 0 TDD Security Rules Test Suite for ArthaTerminal
 * Verifies the "Dirty Dozen" adversarial payloads return PERMISSION_DENIED.
 * Intended to run against the Firebase Firestore Rules Emulator (@firebase/rules-unit-testing).
 */

export interface DirtyDozenTestCase {
  id: number;
  name: string;
  operation: 'get' | 'list' | 'create' | 'update' | 'delete';
  path: string;
  auth: { uid: string; email?: string; email_verified?: boolean } | null;
  payload?: Record<string, unknown>;
  expectedResult: 'PERMISSION_DENIED';
  enforcedByPillar: string;
}

export const DIRTY_DOZEN_CASES: DirtyDozenTestCase[] = [
  {
    id: 1,
    name: 'Unauthenticated Profile Read',
    operation: 'get',
    path: '/users/userA',
    auth: null,
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Pillar 6 (PII Isolation) & Global Safety Net',
  },
  {
    id: 2,
    name: 'Cross-User PII Leak',
    operation: 'get',
    path: '/users/userA',
    auth: { uid: 'userB', email: 'b@example.com', email_verified: true },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Pillar 6 (PII Isolation)',
  },
  {
    id: 3,
    name: 'Directory Enumeration (List Users)',
    operation: 'list',
    path: '/users',
    auth: { uid: 'userA', email: 'a@example.com', email_verified: true },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Pillar 8 (Secure List Queries)',
  },
  {
    id: 4,
    name: 'Shadow Field Injection on Profile',
    operation: 'create',
    path: '/users/userA',
    auth: { uid: 'userA', email: 'a@example.com', email_verified: true },
    payload: { uid: 'userA', isAdmin: true },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Pillar 2 (Validation Blueprints hasOnly)',
  },
  {
    id: 5,
    name: 'Email Unverified Write Spoof',
    operation: 'create',
    path: '/users/userA',
    auth: { uid: 'userA', email: 'a@example.com', email_verified: false },
    payload: { uid: 'userA', displayName: 'Spoof' },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Verified Identity Gate (email_verified == true)',
  },
  {
    id: 6,
    name: 'Backdated Timestamp Spoof',
    operation: 'create',
    path: '/users/userA/holdings/h1',
    auth: { uid: 'userA', email: 'a@example.com', email_verified: true },
    payload: { userId: 'userA', ticker: 'RELIANCE', createdAt: '2020-01-01T00:00:00Z' },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Temporal Integrity (createdAt == request.time)',
  },
  {
    id: 7,
    name: 'Immutable Owner Tampering',
    operation: 'update',
    path: '/users/userA/holdings/h1',
    auth: { uid: 'userA', email: 'a@example.com', email_verified: true },
    payload: { userId: 'userB' },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Immortal Field Rule & Action-Based affectedKeys',
  },
  {
    id: 8,
    name: 'ID Poisoning (Denial of Wallet)',
    operation: 'create',
    path: `/users/userA/holdings/${'X'.repeat(200)}!@#`,
    auth: { uid: 'userA', email: 'a@example.com', email_verified: true },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Pillar 3 (Path Variable Hardening isValidId)',
  },
  {
    id: 9,
    name: 'Watchlist Array Flood',
    operation: 'update',
    path: '/users/userA',
    auth: { uid: 'userA', email: 'a@example.com', email_verified: true },
    payload: { watchlist: Array.from({ length: 61 }, (_, i) => `STK${i}`) },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Pillar 5 (Total Array Guarding <= 60)',
  },
  {
    id: 10,
    name: 'Value Poisoning on Allowed Key',
    operation: 'update',
    path: '/users/userA/holdings/h1',
    auth: { uid: 'userA', email: 'a@example.com', email_verified: true },
    payload: { shares: -50 },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Pillar 2 (isValidHolding wraps update block)',
  },
  {
    id: 11,
    name: 'Orphaned Subcollection Record',
    operation: 'create',
    path: '/users/userGhost/alerts/a1',
    auth: { uid: 'userGhost', email: 'g@example.com', email_verified: true },
    payload: { userId: 'userGhost', ticker: 'TCS' },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Pillar 1 (Master Gate hasValidParentProfile)',
  },
  {
    id: 12,
    name: 'Cross-User Subcollection List Scrape',
    operation: 'list',
    path: '/users/userA/holdings',
    auth: { uid: 'userB', email: 'b@example.com', email_verified: true },
    expectedResult: 'PERMISSION_DENIED',
    enforcedByPillar: 'Pillar 8 (Secure List Queries)',
  },
];
