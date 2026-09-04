import { InwardShipment, OutwardShipment, UserProfile, NotificationLog, Organization } from '../types';

export const MOCK_ORGANIZATIONS: Organization[] = [
  {
    id: 'org_singhania_ca',
    name: 'Singhania & Associates CA',
    code: 'SINGH-101',
    createdAt: '2026-01-01T00:00:00.000Z'
  }
];

export const MOCK_USERS: UserProfile[] = [
  {
    id: 'USR-01',
    name: 'CA Rajesh Sharma',
    email: 'rajesh.sharma@firmca.in',
    role: 'admin_partner',
    department: 'Statutory Audit & Assurance',
    designation: 'Senior Partner (FCA)',
    phone: '+91 98200 11223',
    organizationId: 'org_singhania_ca',
    firmName: 'Singhania & Associates CA',
    icaiNumber: 'FCA-048291'
  },
  {
    id: 'USR-02',
    name: 'Pooja Verma',
    email: 'reception@firmca.in',
    role: 'front_desk',
    department: 'Administration & Dispatch',
    designation: 'Front Desk & Dispatch Manager',
    phone: '+91 98200 44556',
    organizationId: 'org_singhania_ca',
    firmName: 'Singhania & Associates CA'
  },
  {
    id: 'USR-03',
    name: 'Aniket Deshmukh',
    email: 'aniket.d@firmca.in',
    role: 'audit_staff',
    department: 'Direct Tax & Litigation',
    designation: 'Manager - Tax Appeals',
    phone: '+91 98200 77889',
    organizationId: 'org_singhania_ca',
    firmName: 'Singhania & Associates CA'
  },
  {
    id: 'USR-04',
    name: 'Sneha Kulkarni',
    email: 'sneha.k@firmca.in',
    role: 'audit_staff',
    department: 'Statutory Audit & Assurance',
    designation: 'Senior Article Assistant',
    phone: '+91 98200 99001',
    organizationId: 'org_singhania_ca',
    firmName: 'Singhania & Associates CA'
  },
  {
    id: 'USR-05',
    name: 'Vikas Patel',
    email: 'vikas.p@firmca.in',
    role: 'audit_staff',
    department: 'GST & Indirect Tax',
    designation: 'GST Lead Consultant',
    phone: '+91 98200 33445',
    organizationId: 'org_singhania_ca',
    firmName: 'Singhania & Associates CA'
  }
];

export const MOCK_CARRIERS = [
  'Blue Dart Express',
  'DTDC Courier',
  'DHL Express',
  'FedEx India',
  'India Post - Speed Post',
  'Professional Couriers',
  'Direct Office Peon / Hand Delivery',
  'Porter / Dunzo Express',
  'Others (Custom Carrier)'
];

export const MOCK_DEPARTMENTS = [
  'Statutory Audit & Assurance',
  'Direct Tax & Litigation',
  'GST & Indirect Tax',
  'Corporate Law & ROC Filings',
  'Valuation & Financial Modeling',
  'Partner Desk & Executive Admin',
  'Administration & Dispatch',
  'Other Department'
];

export const MOCK_CLIENT_JOBS = [
  { code: 'AUD-2026-TATA', client: 'Tata Technologies Ltd', partner: 'CA Rajesh Sharma' },
  { code: 'TAX-2026-RELI', client: 'Reliance Retail Ventures', partner: 'CA Rajesh Sharma' },
  { code: 'GST-2026-HDFC', client: 'HDFC Capital Advisors', partner: 'CA Rajesh Sharma' },
  { code: 'ROC-2026-INFY', client: 'Infosys BPM Solutions', partner: 'CA Rajesh Sharma' },
  { code: 'VAL-2026-ZOMT', client: 'Zomato Financial Services', partner: 'CA Rajesh Sharma' },
  { code: 'ADMIN-GEN-001', client: 'Internal Office / Statutory', partner: 'General Firm Expense' }
];

// Clean / Fresh Couriers for Testing
export const INITIAL_INWARD: InwardShipment[] = [];

export const INITIAL_OUTWARD: OutwardShipment[] = [];

export const INITIAL_NOTIFICATIONS: NotificationLog[] = [];
