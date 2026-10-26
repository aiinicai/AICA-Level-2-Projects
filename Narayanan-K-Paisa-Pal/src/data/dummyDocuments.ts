import { AppRow, Kind } from '../types';
import { reclassifyMisplacedEntries } from '../utils/calculations';
import * as XLSX from 'xlsx';
import JSZip from 'jszip';

export interface DummyDocument {
  id: string;
  kind: Kind;
  category:
    | 'passport'
    | 'licence'
    | 'pan'
    | 'aadhaar'
    | 'bank_fd'
    | 'insurance'
    | 'mutual_fund'
    | 'utility_bill';
  subCategory?: 'personal' | 'medical' | 'vehicle' | 'electricity' | 'water';
  title: string;
  fileName: string;
  personName: string;
  docNumber: string;
  institution: string;
  amount?: number;
  currentValue?: number;
  rate?: number;
  date: string; // due / maturity / expiry
  issuedDate?: string;
  notes: string;
  svgDataUrl: string;
  rowData: Record<string, any>;
  isExpired?: boolean;
}

export interface SyntheticPerson {
  id: string;
  name: string;
  city: string;
  role: string;
  docCount: number;
  combinationSummary: string;
}

export const SYNTHETIC_PERSONS: SyntheticPerson[] = [
  {
    id: 'person-1',
    name: 'Vikram Aditya Sharma',
    city: 'New Delhi',
    role: 'Tech Lead / Salaried Professional',
    docCount: 4,
    combinationSummary: 'Passport · PAN · Masked Aadhaar · SBI Term Deposit (Matured Alert)',
  },
  {
    id: 'person-2',
    name: 'Ananya Sundaram',
    city: 'Chennai',
    role: 'Principal Architect',
    docCount: 4,
    combinationSummary: 'Passport · Driving Licence (Expired Alert) · Masked Aadhaar · HDFC Bank FD',
  },
  {
    id: 'person-3',
    name: 'Mohammed Farhan Qureshi',
    city: 'Mumbai',
    role: 'Logistics Business Owner',
    docCount: 4,
    combinationSummary: 'Passport · PAN · Driving Licence · Canara Bank FD',
  },
  {
    id: 'person-4',
    name: 'Dr. Meenakshi Venkatraman',
    city: 'Bengaluru',
    role: 'Healthcare Specialist & Consultant',
    docCount: 4,
    combinationSummary: 'Passport · PAN · Driving Licence · Star Health Insurance (Overdue Alert)',
  },
  {
    id: 'person-5',
    name: 'Rajesh Arvind Kulkarni',
    city: 'Pune',
    role: 'Senior Mechanical Engineer',
    docCount: 4,
    combinationSummary: 'Passport (Expired Alert) · Masked Aadhaar · Driving Licence · ICICI Bank FD',
  },
  {
    id: 'person-6',
    name: 'Sunita Devi Agrawal',
    city: 'Kolkata',
    role: 'Homemaker & Active Portfolio Investor',
    docCount: 4,
    combinationSummary: 'Masked Aadhaar · PAN · Driving Licence · LIC Jeevan Labh Policy',
  },
  {
    id: 'person-7',
    name: 'Chetan Mallappa Gowda',
    city: 'Bengaluru',
    role: 'Civil Infrastructure Contractor',
    docCount: 4,
    combinationSummary: 'Masked Aadhaar · PAN · Bank of Baroda FD · BESCOM Power Bill (Overdue Alert)',
  },
  {
    id: 'person-8',
    name: 'Pooja Harish Nair',
    city: 'Kochi',
    role: 'UI/UX Design Director',
    docCount: 4,
    combinationSummary: 'Care Health Insurance · ICICI Lombard Car Insurance (Expired Alert) · HDFC MF · BWSSB Water Bill',
  },
  {
    id: 'person-9',
    name: 'Gurpreet Singh Dhillon',
    city: 'Chandigarh',
    role: 'Agro-Business Entrepreneur',
    docCount: 4,
    combinationSummary: 'HDFC Life Sanchay Plus (Due Soon) · New India 2-Wheeler Insurance · SBI Bluechip MF · Tata Power Bill',
  },
  {
    id: 'person-10',
    name: 'Irin Joseph',
    city: 'Kochi',
    role: 'Financial Analyst',
    docCount: 5,
    combinationSummary: 'Nippon India MF · ICICI Pru MF · Mirae Asset MF · Adani Power Bill · Delhi Jal Board Bill (Overdue Alert)',
  },
];

// Helper to encode SVG into safe data URI
function svgToDataUrl(svgString: string): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgString.trim())}`;
}

// Common DPDP compliance banner SVG snippet
const DPDP_BANNER = `
  <rect x="20" y="445" width="660" height="32" rx="6" fill="#0f172a" fill-opacity="0.9" />
  <text x="350" y="465" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="10.5" font-weight="700" fill="#38bdf8" text-anchor="middle" letter-spacing="0.5">
    CONFIDENTIAL TRIAL ASSET · DPDP ACT 2023 COMPLIANT · 100% SYNTHETIC TEST DATA
  </text>
`;

// 1. Passport SVG Generator
function generatePassportSvg(p: {
  name: string;
  docNo: string;
  dob: string;
  placeOfIssue: string;
  issueDate: string;
  expiryDate: string;
  gender: string;
  isExpired?: boolean;
}) {
  const [given = '', surname = ''] = p.name.split(' ');
  const mrzName = `${surname.toUpperCase()}<<${given.toUpperCase()}`.padEnd(39, '<');
  const mrzBottom = `${p.docNo}<0IND${p.dob.replace(/-/g, '').slice(2)}4M${p.expiryDate.replace(/-/g, '').slice(2)}8<<<<<<<<<<<<<<4`.slice(0, 44);

  return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 490" width="700" height="490">
  <defs>
    <linearGradient id="passBg_${p.docNo}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b1b3d"/>
      <stop offset="100%" stop-color="#142a5c"/>
    </linearGradient>
    <pattern id="passGrid_${p.docNo}" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#253a6a" stroke-width="0.5"/>
    </pattern>
  </defs>

  <rect width="700" height="490" rx="14" fill="url(#passBg_${p.docNo})"/>
  <rect width="700" height="490" rx="14" fill="url(#passGrid_${p.docNo})" opacity="0.4"/>
  <rect x="15" y="15" width="670" height="460" rx="10" fill="none" stroke="#d4af37" stroke-width="2" stroke-dasharray="6,4" opacity="0.6"/>

  <g transform="translate(350, 45)" text-anchor="middle">
    <path d="M -16 0 L -8 -16 L 0 -8 L 8 -16 L 16 0 Z" fill="#d4af37"/>
    <circle cx="0" cy="5" r="7" fill="none" stroke="#d4af37" stroke-width="2"/>
    <text y="28" font-family="-apple-system, sans-serif" font-size="15" font-weight="800" fill="#fef08a" letter-spacing="2">PASSPORT · पासपोर्ट</text>
    <text y="44" font-family="-apple-system, sans-serif" font-size="12" font-weight="700" fill="#fef08a" letter-spacing="1">REPUBLIC OF INDIA · भारत गणराज्य</text>
  </g>

  <g transform="translate(45, 120)">
    <rect width="130" height="160" rx="8" fill="#1e293b" stroke="#d4af37" stroke-width="2"/>
    <circle cx="65" cy="55" r="28" fill="#475569"/>
    <path d="M 25 145 C 25 105, 105 105, 105 145 Z" fill="#475569"/>
    <rect x="0" y="168" width="130" height="24" rx="4" fill="#0f172a" stroke="#334155"/>
    <text x="65" y="184" font-family="monospace" font-size="10" font-weight="700" fill="#94a3b8" text-anchor="middle">SPECIMEN PHOTO</text>
  </g>

  <g transform="translate(200, 120)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <text x="0" y="14" font-size="10" fill="#94a3b8" font-weight="600">Type / प्रकार: <tspan fill="#ffffff" font-weight="700">P</tspan></text>
    <text x="130" y="14" font-size="10" fill="#94a3b8" font-weight="600">Country Code: <tspan fill="#ffffff" font-weight="700">IND</tspan></text>
    <text x="310" y="14" font-size="10" fill="#94a3b8" font-weight="600">Passport No. / पासपोर्ट नं.:</text>
    <text x="310" y="34" font-size="18" font-family="monospace" font-weight="800" fill="#fef08a">${p.docNo}</text>

    <text x="0" y="62" font-size="10" fill="#94a3b8" font-weight="600">Full Name / पूरा नाम:</text>
    <text x="0" y="82" font-size="16" font-weight="800" fill="#ffffff">${p.name.toUpperCase()}</text>

    <text x="0" y="112" font-size="10" fill="#94a3b8" font-weight="600">Nationality / राष्ट्रीयता:</text>
    <text x="0" y="128" font-size="12" font-weight="700" fill="#ffffff">INDIAN</text>

    <text x="170" y="112" font-size="10" fill="#94a3b8" font-weight="600">Sex / लिंग:</text>
    <text x="170" y="128" font-size="12" font-weight="700" fill="#ffffff">${p.gender}</text>

    <text x="310" y="112" font-size="10" fill="#94a3b8" font-weight="600">Date of Birth / जन्म तिथि:</text>
    <text x="310" y="128" font-size="12" font-family="monospace" font-weight="700" fill="#ffffff">${p.dob}</text>

    <text x="0" y="156" font-size="10" fill="#94a3b8" font-weight="600">Place of Issue / जारी करने का स्थान:</text>
    <text x="0" y="172" font-size="12" font-weight="700" fill="#ffffff">${p.placeOfIssue.toUpperCase()}</text>

    <text x="170" y="156" font-size="10" fill="#94a3b8" font-weight="600">Date of Issue / जारी तिथि:</text>
    <text x="170" y="172" font-size="12" font-family="monospace" font-weight="700" fill="#ffffff">${p.issueDate}</text>

    <text x="310" y="156" font-size="10" fill="${p.isExpired ? '#fca5a5' : '#f87171'}" font-weight="700">Date of Expiry / समाप्ति तिथि:</text>
    <text x="310" y="174" font-size="14" font-family="monospace" font-weight="800" fill="${p.isExpired ? '#ef4444' : '#fef08a'}">${p.expiryDate} ${p.isExpired ? ' [EXPIRED]' : ''}</text>
  </g>

  <g transform="translate(605, 230)">
    <circle cx="0" cy="0" r="38" fill="none" stroke="#d4af37" stroke-width="2" stroke-dasharray="4,2"/>
    <circle cx="0" cy="0" r="32" fill="#d4af37" fill-opacity="0.15"/>
    <text y="-8" font-family="sans-serif" font-size="8" font-weight="700" fill="#d4af37" text-anchor="middle">GOVT OF INDIA</text>
    <text y="4" font-family="sans-serif" font-size="7" font-weight="800" fill="#fef08a" text-anchor="middle">PASSPORT</text>
    <text y="16" font-family="sans-serif" font-size="7" font-weight="700" fill="#d4af37" text-anchor="middle">OFFICIAL SEAL</text>
  </g>

  <g transform="translate(45, 360)">
    <rect width="610" height="65" rx="6" fill="#070e1e" stroke="#1e293b"/>
    <text x="18" y="26" font-family="monospace" font-size="14" font-weight="700" fill="#cbd5e1" letter-spacing="3.2">P&lt;IND${mrzName}</text>
    <text x="18" y="48" font-family="monospace" font-size="14" font-weight="700" fill="#cbd5e1" letter-spacing="3.2">${mrzBottom}</text>
  </g>

  ${p.isExpired ? `
    <g transform="translate(480, 290)">
      <rect width="180" height="34" rx="6" fill="#b91c1c" fill-opacity="0.9" stroke="#fca5a5" stroke-width="1.5"/>
      <text x="90" y="22" font-family="-apple-system, sans-serif" font-size="12" font-weight="900" fill="#ffffff" text-anchor="middle" letter-spacing="1">⚠ EXPIRED · RENEW</text>
    </g>
  ` : ''}

  ${DPDP_BANNER}
</svg>
`);
}

// 2. Driving Licence SVG Generator
function generateLicenceSvg(p: {
  name: string;
  docNo: string;
  state: string;
  rto: string;
  dob: string;
  issueDate: string;
  expiryDate: string;
  bloodGroup: string;
  vehicleClass: string;
  isExpired?: boolean;
}) {
  return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 490" width="700" height="490">
  <defs>
    <linearGradient id="dlHeader_${p.docNo.replace(/[^a-zA-Z0-9]/g, '')}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#14532d"/>
      <stop offset="50%" stop-color="#166534"/>
      <stop offset="100%" stop-color="#0f766e"/>
    </linearGradient>
  </defs>

  <rect width="700" height="490" rx="16" fill="#f8fafc" stroke="#94a3b8" stroke-width="2"/>
  <rect x="8" y="8" width="684" height="474" rx="12" fill="#ffffff" stroke="#e2e8f0"/>

  <rect x="12" y="12" width="676" height="75" rx="8" fill="url(#dlHeader_${p.docNo.replace(/[^a-zA-Z0-9]/g, '')})"/>
  <text x="350" y="38" font-family="-apple-system, sans-serif" font-size="14" font-weight="800" fill="#ffffff" text-anchor="middle" letter-spacing="1">UNION OF INDIA · DRIVING LICENCE</text>
  <text x="350" y="58" font-family="-apple-system, sans-serif" font-size="12" font-weight="700" fill="#bbf7d0" text-anchor="middle">TRANSPORT DEPARTMENT · GOVERNMENT OF ${p.state.toUpperCase()}</text>
  <text x="350" y="74" font-family="-apple-system, sans-serif" font-size="10" font-weight="600" fill="#ffffff" text-anchor="middle">ISSUING RTO: ${p.rto.toUpperCase()}</text>

  <g transform="translate(45, 110)">
    <rect width="70" height="52" rx="6" fill="#eab308" stroke="#ca8a04" stroke-width="1.5"/>
    <path d="M 20 0 L 20 52 M 50 0 L 50 52 M 0 26 L 70 26 M 20 14 L 50 14 M 20 38 L 50 38" stroke="#a16207" stroke-width="1.5" fill="none"/>
    <text x="35" y="72" font-family="sans-serif" font-size="9" font-weight="700" fill="#64748b" text-anchor="middle">SMART CHIP</text>
  </g>

  <g transform="translate(525, 110)">
    <rect width="130" height="150" rx="8" fill="#f1f5f9" stroke="#64748b" stroke-width="1.5"/>
    <circle cx="65" cy="55" r="28" fill="#94a3b8"/>
    <path d="M 25 140 C 25 100, 105 100, 105 140 Z" fill="#94a3b8"/>
    <text x="65" y="170" font-family="sans-serif" font-size="9" font-weight="700" fill="#64748b" text-anchor="middle">SPECIMEN PHOTO</text>
  </g>

  <g transform="translate(135, 110)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <text x="0" y="15" font-size="11" font-weight="700" fill="#64748b">DL NUMBER / चालक अनुज्ञप्ति संख्या:</text>
    <rect x="0" y="24" width="360" height="36" rx="6" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.5"/>
    <text x="15" y="48" font-size="18" font-family="monospace" font-weight="800" fill="#14532d">${p.docNo}</text>

    <text x="0" y="85" font-size="11" font-weight="700" fill="#64748b">HOLDER NAME / नाम:</text>
    <text x="0" y="105" font-size="16" font-weight="800" fill="#0f172a">${p.name.toUpperCase()}</text>

    <text x="0" y="132" font-size="11" font-weight="600" fill="#64748b">DATE OF BIRTH / जन्म तिथि:</text>
    <text x="0" y="148" font-size="13" font-family="monospace" font-weight="700" fill="#0f172a">${p.dob}</text>

    <text x="180" y="132" font-size="11" font-weight="600" fill="#64748b">BLOOD GROUP / रक्त वर्ग:</text>
    <text x="180" y="148" font-size="13" font-weight="800" fill="#dc2626">${p.bloodGroup}</text>

    <text x="0" y="178" font-size="11" font-weight="600" fill="#64748b">AUTHORISED VEHICLE CLASS:</text>
    <rect x="0" y="186" width="220" height="26" rx="4" fill="#f1f5f9" stroke="#cbd5e1"/>
    <text x="12" y="203" font-size="12" font-weight="800" fill="#0369a1">${p.vehicleClass}</text>

    <text x="240" y="178" font-size="11" font-weight="600" fill="#64748b">DATE OF ISSUE:</text>
    <text x="240" y="200" font-size="12" font-family="monospace" font-weight="700" fill="#0f172a">${p.issueDate}</text>
  </g>

  <g transform="translate(45, 340)">
    <rect width="610" height="60" rx="8" fill="${p.isExpired ? '#fef2f2' : '#f0fdf4'}" stroke="${p.isExpired ? '#ef4444' : '#86efac'}" stroke-width="2"/>
    <text x="20" y="25" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="${p.isExpired ? '#991b1b' : '#166534'}">LICENCE VALID TILL (NON-TRANSPORT) / वैधता तिथि:</text>
    <text x="20" y="48" font-family="monospace" font-size="18" font-weight="900" fill="${p.isExpired ? '#dc2626' : '#15803d'}">${p.expiryDate} ${p.isExpired ? '⚠ [EXPIRED / OVERDUE]' : ''}</text>
    <text x="400" y="38" font-family="-apple-system, sans-serif" font-size="11" font-weight="800" fill="${p.isExpired ? '#b91c1c' : '#047857'}">${p.isExpired ? 'STATUS: EXPIRED' : 'STATUS: ACTIVE &amp; VERIFIED'}</text>
  </g>

  ${DPDP_BANNER}
</svg>
`);
}

// 3. PAN Card SVG Generator
function generatePanSvg(p: {
  name: string;
  fatherName: string;
  docNo: string;
  dob: string;
}) {
  return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 490" width="700" height="490">
  <defs>
    <linearGradient id="panBg_${p.docNo}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#eff6ff"/>
      <stop offset="50%" stop-color="#e0f2fe"/>
      <stop offset="100%" stop-color="#f0f9ff"/>
    </linearGradient>
  </defs>

  <rect width="700" height="490" rx="16" fill="url(#panBg_${p.docNo})" stroke="#0284c7" stroke-width="2"/>
  <rect x="12" y="12" width="676" height="466" rx="12" fill="none" stroke="#bae6fd" stroke-width="1.5"/>

  <g transform="translate(35, 30)">
    <text x="0" y="18" font-family="-apple-system, sans-serif" font-size="13" font-weight="800" fill="#0369a1" letter-spacing="1">आयकर विभाग / INCOME TAX DEPARTMENT</text>
    <text x="0" y="36" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#0284c7">भारत सरकार / GOVT. OF INDIA</text>
  </g>

  <g transform="translate(630, 48)">
    <circle cx="0" cy="0" r="24" fill="#0284c7" fill-opacity="0.15"/>
    <text y="5" font-family="sans-serif" font-size="12" font-weight="900" fill="#0369a1" text-anchor="middle">ITD</text>
  </g>

  <g transform="translate(45, 95)">
    <rect width="130" height="150" rx="8" fill="#ffffff" stroke="#94a3b8" stroke-width="1.5"/>
    <circle cx="65" cy="55" r="28" fill="#94a3b8"/>
    <path d="M 25 140 C 25 100, 105 100, 105 140 Z" fill="#94a3b8"/>
    <text x="65" y="170" font-family="sans-serif" font-size="9" font-weight="700" fill="#64748b" text-anchor="middle">SPECIMEN PHOTO</text>
  </g>

  <g transform="translate(205, 95)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <text x="0" y="16" font-size="11" font-weight="600" fill="#64748b">Name / नाम:</text>
    <text x="0" y="38" font-size="18" font-weight="800" fill="#0f172a">${p.name.toUpperCase()}</text>

    <text x="0" y="68" font-size="11" font-weight="600" fill="#64748b">Father's Name / पिता का नाम:</text>
    <text x="0" y="88" font-size="14" font-weight="700" fill="#1e293b">${p.fatherName.toUpperCase()}</text>

    <text x="0" y="118" font-size="11" font-weight="600" fill="#64748b">Date of Birth / जन्म तिथि:</text>
    <text x="0" y="138" font-size="15" font-family="monospace" font-weight="800" fill="#0f172a">${p.dob}</text>
  </g>

  <g transform="translate(45, 280)">
    <rect width="610" height="68" rx="8" fill="#ffffff" stroke="#0284c7" stroke-width="2"/>
    <text x="24" y="24" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#0369a1">PERMANENT ACCOUNT NUMBER / स्थायी लेखा संख्या (PAN):</text>
    <text x="24" y="52" font-family="monospace" font-size="26" font-weight="900" fill="#0c4a6e" letter-spacing="4">${p.docNo}</text>
  </g>

  <g transform="translate(45, 365)">
    <rect width="180" height="40" rx="4" fill="#ffffff" stroke="#94a3b8" stroke-dasharray="2,2"/>
    <text x="90" y="25" font-family="'Brush Script MT', cursive, sans-serif" font-size="16" fill="#1e293b" text-anchor="middle">${p.name}</text>
    <text x="90" y="52" font-family="sans-serif" font-size="9" font-weight="600" fill="#64748b" text-anchor="middle">Signature / हस्ताक्षर</text>
  </g>

  ${DPDP_BANNER}
</svg>
`);
}

// 4. Aadhaar Card SVG Generator
function generateAadhaarSvg(p: {
  name: string;
  docNo: string;
  dob: string;
  gender: string;
  address: string;
}) {
  return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 490" width="700" height="490">
  <rect width="700" height="490" rx="16" fill="#ffffff" stroke="#e2e8f0" stroke-width="2"/>

  <rect x="0" y="0" width="700" height="8" fill="#f97316"/>
  <rect x="0" y="8" width="700" height="6" fill="#ffffff"/>
  <rect x="0" y="14" width="700" height="8" fill="#16a34a"/>

  <g transform="translate(350, 48)" text-anchor="middle">
    <text font-family="-apple-system, sans-serif" font-size="15" font-weight="800" fill="#b91c1c" letter-spacing="1">भारतीय विशिष्ट पहचान प्राधिकरण</text>
    <text y="18" font-family="-apple-system, sans-serif" font-size="12" font-weight="700" fill="#0f172a">UNIQUE IDENTIFICATION AUTHORITY OF INDIA</text>
  </g>

  <g transform="translate(45, 100)">
    <rect width="130" height="155" rx="8" fill="#f8fafc" stroke="#94a3b8" stroke-width="1.5"/>
    <circle cx="65" cy="55" r="28" fill="#94a3b8"/>
    <path d="M 25 145 C 25 105, 105 105, 105 145 Z" fill="#94a3b8"/>
    <text x="65" y="172" font-family="sans-serif" font-size="9" font-weight="700" fill="#64748b" text-anchor="middle">SPECIMEN PHOTO</text>
  </g>

  <g transform="translate(200, 100)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <text x="0" y="20" font-size="11" font-weight="600" fill="#64748b">Name / नाम:</text>
    <text x="0" y="42" font-size="18" font-weight="800" fill="#0f172a">${p.name}</text>

    <text x="0" y="75" font-size="11" font-weight="600" fill="#64748b">Date of Birth / जन्म तिथि:</text>
    <text x="0" y="95" font-size="14" font-family="monospace" font-weight="700" fill="#0f172a">${p.dob}</text>

    <text x="180" y="75" font-size="11" font-weight="600" fill="#64748b">Gender / लिंग:</text>
    <text x="180" y="95" font-size="14" font-weight="700" fill="#0f172a">${p.gender}</text>

    <text x="0" y="128" font-size="11" font-weight="600" fill="#64748b">Address / पता (Masked DPDP):</text>
    <text x="0" y="148" font-size="12" font-weight="600" fill="#334155">${p.address}</text>
  </g>

  <g transform="translate(45, 300)">
    <rect width="610" height="65" rx="10" fill="#fef2f2" stroke="#b91c1c" stroke-width="2"/>
    <text x="305" y="42" font-family="monospace" font-size="28" font-weight="900" fill="#991b1b" text-anchor="middle" letter-spacing="4">${p.docNo}</text>
  </g>

  <g transform="translate(350, 395)" text-anchor="middle">
    <text font-family="-apple-system, sans-serif" font-size="14" font-weight="800" fill="#b91c1c">मेरा आधार, मेरी पहचान</text>
    <text y="18" font-family="-apple-system, sans-serif" font-size="11" font-weight="600" fill="#475569">Mera Aadhaar, Meri Pehchaan · DPDP Act Masked Number</text>
  </g>

  ${DPDP_BANNER}
</svg>
`);
}

// 5. Bank Fixed Deposit Receipt SVG Generator
function generateBankFdSvg(p: {
  bankName: string;
  headerColor: string;
  accentColor: string;
  accNo: string;
  holder: string;
  depositAmount: number;
  maturityAmount: number;
  rate: number;
  startDate: string;
  maturityDate: string;
  tenure: string;
  branch: string;
  isMatured?: boolean;
}) {
  const inrFmt = (n: number) => `₹${n.toLocaleString('en-IN')}`;

  return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 490" width="700" height="490">
  <defs>
    <linearGradient id="fdGrad_${p.accNo}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="${p.headerColor}"/>
      <stop offset="100%" stop-color="${p.accentColor}"/>
    </linearGradient>
  </defs>

  <rect width="700" height="490" rx="14" fill="#ffffff" stroke="${p.headerColor}" stroke-width="3"/>
  <rect x="10" y="10" width="680" height="470" rx="10" fill="#fafafa" stroke="#cbd5e1" stroke-width="1"/>

  <rect x="14" y="14" width="672" height="75" rx="8" fill="url(#fdGrad_${p.accNo})"/>
  <text x="350" y="42" font-family="-apple-system, sans-serif" font-size="18" font-weight="900" fill="#ffffff" text-anchor="middle" letter-spacing="1">${p.bankName.toUpperCase()}</text>
  <text x="350" y="64" font-family="-apple-system, sans-serif" font-size="12" font-weight="700" fill="#fef08a" text-anchor="middle">TERM DEPOSIT RECEIPT / FIXED DEPOSIT ADVICE</text>

  <g transform="translate(35, 105)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <rect width="630" height="52" rx="8" fill="#f1f5f9" stroke="#cbd5e1"/>
    <text x="20" y="22" font-size="11" font-weight="600" fill="#64748b">DEPOSIT ACCOUNT NUMBER / खाता संख्या:</text>
    <text x="20" y="42" font-family="monospace" font-size="18" font-weight="900" fill="${p.headerColor}">${p.accNo}</text>

    <text x="380" y="22" font-size="11" font-weight="600" fill="#64748b">BRANCH / शाखा:</text>
    <text x="380" y="40" font-size="13" font-weight="700" fill="#0f172a">${p.branch}</text>
  </g>

  <g transform="translate(35, 175)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <text x="0" y="16" font-size="11" font-weight="600" fill="#64748b">DEPOSITOR NAME / जमाकर्ता का नाम:</text>
    <text x="0" y="38" font-size="17" font-weight="800" fill="#0f172a">${p.holder.toUpperCase()}</text>

    <text x="380" y="16" font-size="11" font-weight="600" fill="#64748b">INTEREST RATE / ब्याज दर:</text>
    <rect x="380" y="22" width="130" height="28" rx="6" fill="#dcfce7" stroke="#16a34a"/>
    <text x="445" y="41" font-family="monospace" font-size="15" font-weight="900" fill="#15803d" text-anchor="middle">${p.rate.toFixed(2)}% p.a.</text>

    <g transform="translate(0, 60)">
      <rect width="300" height="68" rx="8" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5"/>
      <text x="18" y="24" font-size="11" font-weight="700" fill="#1d4ed8">DEPOSIT PRINCIPAL AMOUNT / जमा राशि</text>
      <text x="18" y="54" font-family="monospace" font-size="24" font-weight="900" fill="#1e3a8a">${inrFmt(p.depositAmount)}</text>

      <g transform="translate(330, 0)">
        <rect width="300" height="68" rx="8" fill="${p.isMatured ? '#fef2f2' : '#f0fdf4'}" stroke="${p.isMatured ? '#ef4444' : '#16a34a'}" stroke-width="1.5"/>
        <text x="18" y="24" font-size="11" font-weight="700" fill="${p.isMatured ? '#b91c1c' : '#15803d'}">MATURITY VALUE / परिपक्वता मूल्य</text>
        <text x="18" y="54" font-family="monospace" font-size="24" font-weight="900" fill="${p.isMatured ? '#991b1b' : '#14532d'}">${inrFmt(p.maturityAmount)}</text>
      </g>
    </g>

    <g transform="translate(0, 150)">
      <text x="0" y="14" font-size="11" font-weight="600" fill="#64748b">VALUE DATE / आरंभ तिथि:</text>
      <text x="0" y="34" font-family="monospace" font-size="14" font-weight="700" fill="#0f172a">${p.startDate}</text>

      <text x="210" y="14" font-size="11" font-weight="600" fill="#64748b">TENURE / अवधि:</text>
      <text x="210" y="34" font-size="14" font-weight="700" fill="#0f172a">${p.tenure}</text>

      <text x="420" y="14" font-size="11" font-weight="700" fill="${p.isMatured ? '#b91c1c' : '#b91c1c'}">MATURITY DATE / परिपक्वता तिथि:</text>
      <text x="420" y="36" font-family="monospace" font-size="17" font-weight="900" fill="${p.isMatured ? '#dc2626' : '#b91c1c'}">${p.maturityDate} ${p.isMatured ? '⚠ [MATURED]' : ''}</text>
    </g>
  </g>

  ${p.isMatured ? `
    <g transform="translate(480, 115)">
      <rect width="180" height="32" rx="6" fill="#b91c1c" fill-opacity="0.9" stroke="#fca5a5"/>
      <text x="90" y="21" font-family="-apple-system, sans-serif" font-size="11" font-weight="900" fill="#ffffff" text-anchor="middle">⚠ MATURED / CLAIM NOW</text>
    </g>
  ` : ''}

  ${DPDP_BANNER}
</svg>
`);
}

// 6. Insurance Policy Certificate SVG Generator
function generateInsuranceSvg(p: {
  policyType: 'Personal' | 'Medical' | 'Vehicle';
  companyName: string;
  policyNo: string;
  holder: string;
  details: string; // plan or vehicle model
  sumAssuredOrIdv: number;
  premiumAmount: number;
  renewalDate: string;
  isOverdue?: boolean;
}) {
  const inrFmt = (n: number) => `₹${n.toLocaleString('en-IN')}`;
  const headerColors: Record<string, string> = {
    Personal: '#1e3a8a',
    Medical: '#047857',
    Vehicle: '#b45309',
  };
  const theme = headerColors[p.policyType] || '#1e3a8a';

  return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 490" width="700" height="490">
  <rect width="700" height="490" rx="14" fill="#ffffff" stroke="${theme}" stroke-width="3"/>

  <rect x="0" y="0" width="700" height="75" rx="14" fill="${theme}"/>
  <text x="40" y="35" font-family="-apple-system, sans-serif" font-size="18" font-weight="900" fill="#ffffff">${p.companyName.toUpperCase()}</text>
  <text x="40" y="56" font-family="-apple-system, sans-serif" font-size="12" font-weight="700" fill="#fef08a">${p.policyType.toUpperCase()} INSURANCE POLICY CERTIFICATE</text>

  <g transform="translate(35, 95)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <rect width="630" height="56" rx="8" fill="#f8fafc" stroke="#cbd5e1"/>
    <text x="20" y="22" font-size="11" font-weight="600" fill="#64748b">POLICY NUMBER / पॉलिसी संख्या:</text>
    <text x="20" y="44" font-family="monospace" font-size="18" font-weight="900" fill="${theme}">${p.policyNo}</text>

    <text x="350" y="22" font-size="11" font-weight="600" fill="#64748b">COVER TYPE / बीमा प्रकार:</text>
    <text x="350" y="42" font-size="14" font-weight="800" fill="#0f172a">${p.policyType} Comprehensive Cover</text>
  </g>

  <g transform="translate(35, 170)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <text x="0" y="16" font-size="11" font-weight="600" fill="#64748b">INSURED NAME / POLICYHOLDER:</text>
    <text x="0" y="38" font-size="17" font-weight="800" fill="#0f172a">${p.holder.toUpperCase()}</text>

    <text x="350" y="16" font-size="11" font-weight="600" fill="#64748b">COVERAGE / SPECIFICATION:</text>
    <text x="350" y="38" font-size="13" font-weight="700" fill="#334155">${p.details}</text>

    <g transform="translate(0, 60)">
      <rect width="300" height="68" rx="8" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5"/>
      <text x="18" y="24" font-size="11" font-weight="700" fill="#1d4ed8">${p.policyType === 'Vehicle' ? 'INSURED DECLARED VALUE (IDV)' : 'SUM ASSURED / HEALTH COVER'}</text>
      <text x="18" y="54" font-family="monospace" font-size="22" font-weight="900" fill="#1e3a8a">${inrFmt(p.sumAssuredOrIdv)}</text>

      <g transform="translate(330, 0)">
        <rect width="300" height="68" rx="8" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.5"/>
        <text x="18" y="24" font-size="11" font-weight="700" fill="#15803d">ANNUAL PREMIUM (INCL. GST)</text>
        <text x="18" y="54" font-family="monospace" font-size="22" font-weight="900" fill="#14532d">${inrFmt(p.premiumAmount)}</text>
      </g>
    </g>

    <g transform="translate(0, 150)">
      <rect width="630" height="50" rx="8" fill="${p.isOverdue ? '#fef2f2' : '#f0fdf4'}" stroke="${p.isOverdue ? '#ef4444' : '#86efac'}" stroke-width="1.5"/>
      <text x="20" y="22" font-size="11" font-weight="700" fill="${p.isOverdue ? '#991b1b' : '#166534'}">NEXT PREMIUM DUE DATE / POLICY EXPIRY:</text>
      <text x="20" y="42" font-family="monospace" font-size="17" font-weight="900" fill="${p.isOverdue ? '#dc2626' : '#15803d'}">${p.renewalDate} ${p.isOverdue ? '⚠ [EXPIRED / OVERDUE ALERT]' : ''}</text>
      <text x="440" y="32" font-size="11" font-weight="800" fill="${p.isOverdue ? '#b91c1c' : '#15803d'}">${p.isOverdue ? 'STATUS: OVERDUE' : 'STATUS: IN FORCE'}</text>
    </g>
  </g>

  ${DPDP_BANNER}
</svg>
`);
}

// 7. Mutual Fund Account Statement SVG Generator
function generateMutualFundSvg(p: {
  amcName: string;
  schemeName: string;
  folioNo: string;
  holder: string;
  nav: number;
  units: number;
  investedAmount: number;
  currentValue: number;
  statementDate: string;
}) {
  const inrFmt = (n: number) => `₹${n.toLocaleString('en-IN')}`;

  return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 490" width="700" height="490">
  <rect width="700" height="490" rx="14" fill="#ffffff" stroke="#0f766e" stroke-width="3"/>

  <rect x="0" y="0" width="700" height="75" rx="14" fill="#0f766e"/>
  <text x="40" y="35" font-family="-apple-system, sans-serif" font-size="18" font-weight="900" fill="#ffffff">${p.amcName.toUpperCase()}</text>
  <text x="40" y="56" font-family="-apple-system, sans-serif" font-size="12" font-weight="700" fill="#a7f3d0">CONSOLIDATED MUTUAL FUND ACCOUNT STATEMENT · FOLIO HOLDINGS</text>
  <text x="660" y="45" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#ffffff" text-anchor="end">AS ON: ${p.statementDate}</text>

  <g transform="translate(35, 95)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <rect width="630" height="56" rx="8" fill="#f0fdfa" stroke="#99f6e4"/>
    <text x="20" y="22" font-size="11" font-weight="600" fill="#0d9488">FOLIO NUMBER / फोलियो नं:</text>
    <text x="20" y="44" font-family="monospace" font-size="18" font-weight="900" fill="#0f766e">${p.folioNo}</text>

    <text x="320" y="22" font-size="11" font-weight="600" fill="#0d9488">SCHEME NAME / योजना का नाम:</text>
    <text x="320" y="42" font-size="14" font-weight="800" fill="#0f172a">${p.schemeName}</text>
  </g>

  <g transform="translate(35, 170)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <text x="0" y="16" font-size="11" font-weight="600" fill="#64748b">INVESTOR NAME / निवेशक का नाम:</text>
    <text x="0" y="38" font-size="17" font-weight="800" fill="#0f172a">${p.holder.toUpperCase()}</text>

    <text x="350" y="16" font-size="11" font-weight="600" fill="#64748b">LATEST NAV / इकाई मूल्य:</text>
    <text x="350" y="38" font-family="monospace" font-size="15" font-weight="800" fill="#0f766e">₹${p.nav.toFixed(2)} (${p.units.toFixed(2)} Units)</text>

    <g transform="translate(0, 60)">
      <rect width="300" height="68" rx="8" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5"/>
      <text x="18" y="24" font-size="11" font-weight="700" fill="#1d4ed8">PURCHASE COST / INVESTED AMOUNT</text>
      <text x="18" y="54" font-family="monospace" font-size="22" font-weight="900" fill="#1e3a8a">${inrFmt(p.investedAmount)}</text>

      <g transform="translate(330, 0)">
        <rect width="300" height="68" rx="8" fill="#ecfdf5" stroke="#10b981" stroke-width="1.5"/>
        <text x="18" y="24" font-size="11" font-weight="700" fill="#047857">CURRENT VALUATION / वर्तमान मूल्य</text>
        <text x="18" y="54" font-family="monospace" font-size="22" font-weight="900" fill="#065f46">${inrFmt(p.currentValue)}</text>
      </g>
    </g>

    <g transform="translate(0, 150)">
      <rect width="630" height="48" rx="8" fill="#f1f5f9" stroke="#cbd5e1"/>
      <text x="20" y="30" font-size="12" font-weight="700" fill="#0f172a">UNREALIZED PROFIT / लाभ: <tspan fill="#16a34a" font-weight="900">+${inrFmt(p.currentValue - p.investedAmount)} (+${(((p.currentValue - p.investedAmount) / p.investedAmount) * 100).toFixed(1)}%)</tspan></text>
      <text x="460" y="30" font-size="11" font-weight="700" fill="#0f766e">KYC STATUS: VERIFIED</text>
    </g>
  </g>

  ${DPDP_BANNER}
</svg>
`);
}

// 8. Utility Bill SVG Generator (Electricity & Water)
function generateUtilityBillSvg(p: {
  utilityType: 'Electricity' | 'Water';
  providerName: string;
  consumerNo: string;
  consumerName: string;
  billingPeriod: string;
  billAmount: number;
  dueDate: string;
  address: string;
  isOverdue?: boolean;
}) {
  const inrFmt = (n: number) => `₹${n.toLocaleString('en-IN')}`;
  const isPower = p.utilityType === 'Electricity';
  const themeColor = isPower ? '#d97706' : '#0284c7';

  return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 490" width="700" height="490">
  <rect width="700" height="490" rx="14" fill="#ffffff" stroke="${themeColor}" stroke-width="3"/>

  <rect x="0" y="0" width="700" height="75" rx="14" fill="${themeColor}"/>
  <text x="40" y="35" font-family="-apple-system, sans-serif" font-size="18" font-weight="900" fill="#ffffff">${p.providerName.toUpperCase()}</text>
  <text x="40" y="56" font-family="-apple-system, sans-serif" font-size="12" font-weight="700" fill="#fef3c7">${p.utilityType.toUpperCase()} CONSUMER BILL / बिल विवरण</text>
  <text x="660" y="45" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" fill="#ffffff" text-anchor="end">PERIOD: ${p.billingPeriod}</text>

  <g transform="translate(35, 95)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <rect width="630" height="56" rx="8" fill="#fefce8" stroke="#fde047"/>
    <text x="20" y="22" font-size="11" font-weight="600" fill="#854d0e">CONSUMER ACCOUNT NUMBER / उपभोक्ता संख्या:</text>
    <text x="20" y="44" font-family="monospace" font-size="18" font-weight="900" fill="#713f12">${p.consumerNo}</text>

    <text x="350" y="22" font-size="11" font-weight="600" fill="#854d0e">TARIFF CATEGORY:</text>
    <text x="350" y="42" font-size="13" font-weight="700" fill="#0f172a">DOMESTIC LT-1 / RESIDENTIAL</text>
  </g>

  <g transform="translate(35, 170)" font-family="-apple-system, BlinkMacSystemFont, sans-serif">
    <text x="0" y="16" font-size="11" font-weight="600" fill="#64748b">CONSUMER NAME / उपभोक्ता का नाम:</text>
    <text x="0" y="38" font-size="17" font-weight="800" fill="#0f172a">${p.consumerName.toUpperCase()}</text>

    <text x="350" y="16" font-size="11" font-weight="600" fill="#64748b">PREMISES ADDRESS:</text>
    <text x="350" y="38" font-size="12" font-weight="600" fill="#334155">${p.address}</text>

    <g transform="translate(0, 60)">
      <rect width="300" height="75" rx="8" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.5"/>
      <text x="18" y="24" font-size="11" font-weight="700" fill="#1d4ed8">TOTAL AMOUNT PAYABLE / देय राशि</text>
      <text x="18" y="58" font-family="monospace" font-size="28" font-weight="900" fill="#1e3a8a">${inrFmt(p.billAmount)}</text>

      <g transform="translate(330, 0)">
        <rect width="300" height="75" rx="8" fill="${p.isOverdue ? '#fef2f2' : '#f0fdf4'}" stroke="${p.isOverdue ? '#ef4444' : '#16a34a'}" stroke-width="1.5"/>
        <text x="18" y="24" font-size="11" font-weight="700" fill="${p.isOverdue ? '#b91c1c' : '#15803d'}">PAYMENT DUE DATE / अंतिम तिथि</text>
        <text x="18" y="58" font-family="monospace" font-size="26" font-weight="900" fill="${p.isOverdue ? '#dc2626' : '#15803d'}">${p.dueDate} ${p.isOverdue ? '⚠ [OVERDUE]' : ''}</text>
      </g>
    </g>

    <g transform="translate(0, 155)">
      <rect width="630" height="42" rx="6" fill="#f1f5f9" stroke="#cbd5e1"/>
      <text x="20" y="26" font-family="monospace" font-size="11" font-weight="700" fill="#475569">BARCODE: |||||| | | |||| ||| | ||||| || |||||| | ||| ${p.consumerNo}</text>
      <text x="460" y="26" font-size="11" font-weight="700" fill="${p.isOverdue ? '#b91c1c' : '#16a34a'}">${p.isOverdue ? '⚠ PAYMENT OVERDUE' : 'UPI / BBPS ENABLED'}</text>
    </g>
  </g>

  ${DPDP_BANNER}
</svg>
`);
}

// Helper to determine document alert status based on current date (2026-10-24)
export function getDocAlertStatus(d: DummyDocument): string {
  if (!d.date) return 'Active / Permanent';
  const today = '2026-10-24';
  if (d.date < today) {
    if (d.category === 'bank_fd') return 'MATURED (Overdue Alert)';
    if (d.category === 'utility_bill') return 'OVERDUE BILL (Payment Alert)';
    if (d.category === 'insurance') return 'PREMIUM OVERDUE (Alert)';
    return 'EXPIRED (Renewal Alert)';
  }
  const diffDays = Math.round((new Date(d.date).getTime() - new Date(today).getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 30) {
    return `DUE SOON (in ${diffDays} days)`;
  }
  return 'Active / Up-to-date';
}

// =========================================================================
// 41 DPDP-COMPLIANT DUMMY DOCUMENTS FOR 10 SYNTHETIC PERSONS
// =========================================================================

export const DUMMY_DOCUMENTS: DummyDocument[] = [
  // -----------------------------------------------------------------------
  // 1. PASSPORTS (5 Documents)
  // -----------------------------------------------------------------------
  {
    id: 'trial-passport-1',
    kind: 'rec',
    category: 'passport',
    title: 'Passport - Vikram Aditya Sharma',
    fileName: 'passport_vikram_aditya_sharma.svg',
    personName: 'Vikram Aditya Sharma',
    docNumber: 'P4920184',
    institution: 'Passport Office, Government of India',
    date: '2034-08-14',
    issuedDate: '2024-08-15',
    notes: 'Govt of India Passport · Type P · Issued at New Delhi · DPDP compliant trial data',
    svgDataUrl: generatePassportSvg({
      name: 'Vikram Aditya Sharma',
      docNo: 'P4920184',
      dob: '1989-05-12',
      placeOfIssue: 'New Delhi',
      issueDate: '2024-08-15',
      expiryDate: '2034-08-14',
      gender: 'M',
      isExpired: false,
    }),
    rowData: {
      title: 'Passport - Vikram Aditya Sharma',
      type: 'passport',
      holder: 'Vikram Aditya Sharma',
      number: 'P4920184',
      issued: '2024-08-15',
      expires: '2034-08-14',
      notes: 'Govt of India Passport · Type P · Issued at New Delhi · DPDP compliant trial data',
      hasAttachment: true,
      attachmentName: 'passport_vikram_aditya_sharma.svg',
    },
  },
  {
    id: 'trial-passport-2',
    kind: 'rec',
    category: 'passport',
    title: 'Passport - Ananya Sundaram',
    fileName: 'passport_ananya_sundaram.svg',
    personName: 'Ananya Sundaram',
    docNumber: 'T8103492',
    institution: 'Passport Office, Government of India',
    date: '2033-03-22',
    issuedDate: '2023-03-23',
    notes: 'Govt of India Passport · Type P · Issued at Chennai · DPDP compliant trial data',
    svgDataUrl: generatePassportSvg({
      name: 'Ananya Sundaram',
      docNo: 'T8103492',
      dob: '1993-11-28',
      placeOfIssue: 'Chennai',
      issueDate: '2023-03-23',
      expiryDate: '2033-03-22',
      gender: 'F',
      isExpired: false,
    }),
    rowData: {
      title: 'Passport - Ananya Sundaram',
      type: 'passport',
      holder: 'Ananya Sundaram',
      number: 'T8103492',
      issued: '2023-03-23',
      expires: '2033-03-22',
      notes: 'Govt of India Passport · Type P · Issued at Chennai · DPDP compliant trial data',
      hasAttachment: true,
      attachmentName: 'passport_ananya_sundaram.svg',
    },
  },
  {
    id: 'trial-passport-3',
    kind: 'rec',
    category: 'passport',
    title: 'Passport - Mohammed Farhan Qureshi',
    fileName: 'passport_mohammed_farhan_qureshi.svg',
    personName: 'Mohammed Farhan Qureshi',
    docNumber: 'M6294017',
    institution: 'Passport Office, Government of India',
    date: '2035-11-09',
    issuedDate: '2025-11-10',
    notes: 'Govt of India Passport · Type P · Issued at Mumbai · DPDP compliant trial data',
    svgDataUrl: generatePassportSvg({
      name: 'Mohammed Farhan Qureshi',
      docNo: 'M6294017',
      dob: '1986-04-17',
      placeOfIssue: 'Mumbai',
      issueDate: '2025-11-10',
      expiryDate: '2035-11-09',
      gender: 'M',
      isExpired: false,
    }),
    rowData: {
      title: 'Passport - Mohammed Farhan Qureshi',
      type: 'passport',
      holder: 'Mohammed Farhan Qureshi',
      number: 'M6294017',
      issued: '2025-11-10',
      expires: '2035-11-09',
      notes: 'Govt of India Passport · Type P · Issued at Mumbai · DPDP compliant trial data',
      hasAttachment: true,
      attachmentName: 'passport_mohammed_farhan_qureshi.svg',
    },
  },
  {
    id: 'trial-passport-4',
    kind: 'rec',
    category: 'passport',
    title: 'Passport - Dr. Meenakshi Venkatraman',
    fileName: 'passport_dr_meenakshi_venkatraman.svg',
    personName: 'Dr. Meenakshi Venkatraman',
    docNumber: 'K7392018',
    institution: 'Passport Office, Government of India',
    date: '2031-07-29',
    issuedDate: '2021-07-30',
    notes: 'Govt of India Passport · Type P · Issued at Bengaluru · DPDP compliant trial data',
    svgDataUrl: generatePassportSvg({
      name: 'Dr. Meenakshi Venkatraman',
      docNo: 'K7392018',
      dob: '1982-09-14',
      placeOfIssue: 'Bengaluru',
      issueDate: '2021-07-30',
      expiryDate: '2031-07-29',
      gender: 'F',
      isExpired: false,
    }),
    rowData: {
      title: 'Passport - Dr. Meenakshi Venkatraman',
      type: 'passport',
      holder: 'Dr. Meenakshi Venkatraman',
      number: 'K7392018',
      issued: '2021-07-30',
      expires: '2031-07-29',
      notes: 'Govt of India Passport · Type P · Issued at Bengaluru · DPDP compliant trial data',
      hasAttachment: true,
      attachmentName: 'passport_dr_meenakshi_venkatraman.svg',
    },
  },
  {
    id: 'trial-passport-5',
    kind: 'rec',
    category: 'passport',
    title: 'Passport - Rajesh Arvind Kulkarni',
    fileName: 'passport_rajesh_arvind_kulkarni.svg',
    personName: 'Rajesh Arvind Kulkarni',
    docNumber: 'V9481024',
    institution: 'Passport Office, Government of India',
    date: '2026-08-20',
    issuedDate: '2016-08-21',
    notes: 'Govt of India Passport · EXPIRED ON 2026-08-20 (Overdue Alert) · Issued at Pune · DPDP compliant trial data',
    isExpired: true,
    svgDataUrl: generatePassportSvg({
      name: 'Rajesh Arvind Kulkarni',
      docNo: 'V9481024',
      dob: '1979-12-03',
      placeOfIssue: 'Pune',
      issueDate: '2016-08-21',
      expiryDate: '2026-08-20',
      gender: 'M',
      isExpired: true,
    }),
    rowData: {
      title: 'Passport - Rajesh Arvind Kulkarni',
      type: 'passport',
      holder: 'Rajesh Arvind Kulkarni',
      number: 'V9481024',
      issued: '2016-08-21',
      expires: '2026-08-20',
      alerts: '60, 30, 7',
      notes: 'Govt of India Passport · EXPIRED ON 2026-08-20 (Requires Renewal) · Issued at Pune',
      hasAttachment: true,
      attachmentName: 'passport_rajesh_arvind_kulkarni.svg',
    },
  },

  // -----------------------------------------------------------------------
  // 2. DRIVING LICENCES (5 Documents)
  // -----------------------------------------------------------------------
  {
    id: 'trial-licence-1',
    kind: 'rec',
    category: 'licence',
    title: 'Driving Licence - Ananya Sundaram',
    fileName: 'driving_licence_ananya_sundaram.svg',
    personName: 'Ananya Sundaram',
    docNumber: 'TN-01-2019-0048192',
    institution: 'Transport Department, Government of Tamil Nadu',
    date: '2026-09-15',
    issuedDate: '2019-09-16',
    notes: 'Tamil Nadu Driving Licence · EXPIRED ON 2026-09-15 (Overdue Alert) · LMV / MCWG · Chennai Central RTO',
    isExpired: true,
    svgDataUrl: generateLicenceSvg({
      name: 'Ananya Sundaram',
      docNo: 'TN-01-2019-0048192',
      state: 'Tamil Nadu',
      rto: 'Chennai Central TN-01',
      dob: '1993-11-28',
      issueDate: '2019-09-16',
      expiryDate: '2026-09-15',
      bloodGroup: 'O+VE',
      vehicleClass: 'LMV / MCWG',
      isExpired: true,
    }),
    rowData: {
      title: 'Driving Licence - Ananya Sundaram',
      type: 'licence',
      holder: 'Ananya Sundaram',
      number: 'TN-01-2019-0048192',
      issued: '2019-09-16',
      expires: '2026-09-15',
      alerts: '60, 30, 7',
      notes: 'Tamil Nadu DL TN-01-2019-0048192 · EXPIRED (Requires Urgent Renewal) · LMV / MCWG',
      hasAttachment: true,
      attachmentName: 'driving_licence_ananya_sundaram.svg',
    },
  },
  {
    id: 'trial-licence-2',
    kind: 'rec',
    category: 'licence',
    title: 'Driving Licence - Mohammed Farhan Qureshi',
    fileName: 'driving_licence_mohammed_farhan_qureshi.svg',
    personName: 'Mohammed Farhan Qureshi',
    docNumber: 'MH-02-2020-0081943',
    institution: 'Motor Vehicles Department, Maharashtra',
    date: '2038-06-18',
    issuedDate: '2020-06-19',
    notes: 'Maharashtra DL MH-02-2020-0081943 · Valid till 2038-06-18 · LMV / MCWG · Mumbai West RTO',
    svgDataUrl: generateLicenceSvg({
      name: 'Mohammed Farhan Qureshi',
      docNo: 'MH-02-2020-0081943',
      state: 'Maharashtra',
      rto: 'Mumbai West MH-02',
      dob: '1986-04-17',
      issueDate: '2020-06-19',
      expiryDate: '2038-06-18',
      bloodGroup: 'B+VE',
      vehicleClass: 'LMV / MCWG',
      isExpired: false,
    }),
    rowData: {
      title: 'Driving Licence - Mohammed Farhan Qureshi',
      type: 'licence',
      holder: 'Mohammed Farhan Qureshi',
      number: 'MH-02-2020-0081943',
      issued: '2020-06-19',
      expires: '2038-06-18',
      notes: 'Maharashtra DL MH-02-2020-0081943 · Valid till 18-06-2038 · Mumbai West RTO',
      hasAttachment: true,
      attachmentName: 'driving_licence_mohammed_farhan_qureshi.svg',
    },
  },
  {
    id: 'trial-licence-3',
    kind: 'rec',
    category: 'licence',
    title: 'Driving Licence - Dr. Meenakshi Venkatraman',
    fileName: 'driving_licence_dr_meenakshi_venkatraman.svg',
    personName: 'Dr. Meenakshi Venkatraman',
    docNumber: 'KA-05-2018-0092841',
    institution: 'Transport Department, Government of Karnataka',
    date: '2036-12-04',
    issuedDate: '2018-12-05',
    notes: 'Karnataka DL KA-05-2018-0092841 · Valid till 2036-12-04 · Bengaluru South RTO',
    svgDataUrl: generateLicenceSvg({
      name: 'Dr. Meenakshi Venkatraman',
      docNo: 'KA-05-2018-0092841',
      state: 'Karnataka',
      rto: 'Bengaluru South KA-05',
      dob: '1982-09-14',
      issueDate: '2018-12-05',
      expiryDate: '2036-12-04',
      bloodGroup: 'A+VE',
      vehicleClass: 'LMV / MCWG',
      isExpired: false,
    }),
    rowData: {
      title: 'Driving Licence - Dr. Meenakshi Venkatraman',
      type: 'licence',
      holder: 'Dr. Meenakshi Venkatraman',
      number: 'KA-05-2018-0092841',
      issued: '2018-12-05',
      expires: '2036-12-04',
      notes: 'Karnataka DL KA-05-2018-0092841 · Valid till 04-12-2036 · Jayanagar Bengaluru',
      hasAttachment: true,
      attachmentName: 'driving_licence_dr_meenakshi_venkatraman.svg',
    },
  },
  {
    id: 'trial-licence-4',
    kind: 'rec',
    category: 'licence',
    title: 'Driving Licence - Rajesh Arvind Kulkarni',
    fileName: 'driving_licence_rajesh_arvind_kulkarni.svg',
    personName: 'Rajesh Arvind Kulkarni',
    docNumber: 'MH-12-2017-0038472',
    institution: 'Motor Vehicles Department, Maharashtra',
    date: '2037-09-24',
    issuedDate: '2017-09-25',
    notes: 'Maharashtra DL MH-12-2017-0038472 · Valid till 2037-09-24 · Pune RTO',
    svgDataUrl: generateLicenceSvg({
      name: 'Rajesh Arvind Kulkarni',
      docNo: 'MH-12-2017-0038472',
      state: 'Maharashtra',
      rto: 'Pune MH-12',
      dob: '1979-12-03',
      issueDate: '2017-09-25',
      expiryDate: '2037-09-24',
      bloodGroup: 'B+VE',
      vehicleClass: 'LMV / MCWG',
      isExpired: false,
    }),
    rowData: {
      title: 'Driving Licence - Rajesh Arvind Kulkarni',
      type: 'licence',
      holder: 'Rajesh Arvind Kulkarni',
      number: 'MH-12-2017-0038472',
      issued: '2017-09-25',
      expires: '2037-09-24',
      notes: 'Maharashtra DL MH-12-2017-0038472 · Valid till 24-09-2037 · Pune RTO',
      hasAttachment: true,
      attachmentName: 'driving_licence_rajesh_arvind_kulkarni.svg',
    },
  },
  {
    id: 'trial-licence-5',
    kind: 'rec',
    category: 'licence',
    title: 'Driving Licence - Sunita Devi Agrawal',
    fileName: 'driving_licence_sunita_devi_agrawal.svg',
    personName: 'Sunita Devi Agrawal',
    docNumber: 'WB-06-2021-0073918',
    institution: 'Transport Department, Government of West Bengal',
    date: '2039-01-30',
    issuedDate: '2021-01-31',
    notes: 'West Bengal DL WB-06-2021-0073918 · Valid till 2039-01-30 · Kolkata RTO',
    svgDataUrl: generateLicenceSvg({
      name: 'Sunita Devi Agrawal',
      docNo: 'WB-06-2021-0073918',
      state: 'West Bengal',
      rto: 'Kolkata WB-06',
      dob: '1975-06-15',
      issueDate: '2021-01-31',
      expiryDate: '2039-01-30',
      bloodGroup: 'AB+VE',
      vehicleClass: 'LMV',
      isExpired: false,
    }),
    rowData: {
      title: 'Driving Licence - Sunita Devi Agrawal',
      type: 'licence',
      holder: 'Sunita Devi Agrawal',
      number: 'WB-06-2021-0073918',
      issued: '2021-01-31',
      expires: '2039-01-30',
      notes: 'West Bengal DL WB-06-2021-0073918 · Valid till 30-01-2039 · Kolkata RTO',
      hasAttachment: true,
      attachmentName: 'driving_licence_sunita_devi_agrawal.svg',
    },
  },

  // -----------------------------------------------------------------------
  // 3. PAN CARDS (5 Documents)
  // -----------------------------------------------------------------------
  {
    id: 'trial-pan-1',
    kind: 'rec',
    category: 'pan',
    title: 'PAN Card - Vikram Aditya Sharma',
    fileName: 'pan_card_vikram_aditya_sharma.svg',
    personName: 'Vikram Aditya Sharma',
    docNumber: 'BPWPS4820K',
    institution: 'Income Tax Department, Government of India',
    date: '',
    notes: 'Income Tax Department PAN · Permanent Account Number BPWPS4820K · Individual Resident',
    svgDataUrl: generatePanSvg({
      name: 'Vikram Aditya Sharma',
      fatherName: 'Harish Chandra Sharma',
      docNo: 'BPWPS4820K',
      dob: '12/05/1989',
    }),
    rowData: {
      title: 'PAN Card - Vikram Aditya Sharma',
      type: 'id',
      holder: 'Vikram Aditya Sharma',
      number: 'BPWPS4820K',
      notes: 'Income Tax Dept Permanent Account Number BPWPS4820K · Linked with Aadhaar',
      hasAttachment: true,
      attachmentName: 'pan_card_vikram_aditya_sharma.svg',
    },
  },
  {
    id: 'trial-pan-2',
    kind: 'rec',
    category: 'pan',
    title: 'PAN Card - Mohammed Farhan Qureshi',
    fileName: 'pan_card_mohammed_farhan_qureshi.svg',
    personName: 'Mohammed Farhan Qureshi',
    docNumber: 'AFBPQ5918E',
    institution: 'Income Tax Department, Government of India',
    date: '',
    notes: 'Income Tax Department PAN · Permanent Account Number AFBPQ5918E · Business Entity Director',
    svgDataUrl: generatePanSvg({
      name: 'Mohammed Farhan Qureshi',
      fatherName: 'Abdul Rashid Qureshi',
      docNo: 'AFBPQ5918E',
      dob: '17/04/1986',
    }),
    rowData: {
      title: 'PAN Card - Mohammed Farhan Qureshi',
      type: 'id',
      holder: 'Mohammed Farhan Qureshi',
      number: 'AFBPQ5918E',
      notes: 'Income Tax Dept Permanent Account Number AFBPQ5918E · Verified KYC',
      hasAttachment: true,
      attachmentName: 'pan_card_mohammed_farhan_qureshi.svg',
    },
  },
  {
    id: 'trial-pan-3',
    kind: 'rec',
    category: 'pan',
    title: 'PAN Card - Dr. Meenakshi Venkatraman',
    fileName: 'pan_card_dr_meenakshi_venkatraman.svg',
    personName: 'Dr. Meenakshi Venkatraman',
    docNumber: 'CGMPV6192M',
    institution: 'Income Tax Department, Government of India',
    date: '',
    notes: 'Income Tax Department PAN · Permanent Account Number CGMPV6192M · Professional Consultant',
    svgDataUrl: generatePanSvg({
      name: 'Dr. Meenakshi Venkatraman',
      fatherName: 'Venkatraman Narayanan',
      docNo: 'CGMPV6192M',
      dob: '14/09/1982',
    }),
    rowData: {
      title: 'PAN Card - Dr. Meenakshi Venkatraman',
      type: 'id',
      holder: 'Dr. Meenakshi Venkatraman',
      number: 'CGMPV6192M',
      notes: 'Income Tax Dept Permanent Account Number CGMPV6192M · Professional Consultant',
      hasAttachment: true,
      attachmentName: 'pan_card_dr_meenakshi_venkatraman.svg',
    },
  },
  {
    id: 'trial-pan-4',
    kind: 'rec',
    category: 'pan',
    title: 'PAN Card - Sunita Devi Agrawal',
    fileName: 'pan_card_sunita_devi_agrawal.svg',
    personName: 'Sunita Devi Agrawal',
    docNumber: 'AHAPA7291F',
    institution: 'Income Tax Department, Government of India',
    date: '',
    notes: 'Income Tax Department PAN · Permanent Account Number AHAPA7291F · Individual Investor',
    svgDataUrl: generatePanSvg({
      name: 'Sunita Devi Agrawal',
      fatherName: 'Radhe Shyam Agrawal',
      docNo: 'AHAPA7291F',
      dob: '15/06/1975',
    }),
    rowData: {
      title: 'PAN Card - Sunita Devi Agrawal',
      type: 'id',
      holder: 'Sunita Devi Agrawal',
      number: 'AHAPA7291F',
      notes: 'Income Tax Dept Permanent Account Number AHAPA7291F · Individual Investor',
      hasAttachment: true,
      attachmentName: 'pan_card_sunita_devi_agrawal.svg',
    },
  },
  {
    id: 'trial-pan-5',
    kind: 'rec',
    category: 'pan',
    title: 'PAN Card - Chetan Mallappa Gowda',
    fileName: 'pan_card_chetan_mallappa_gowda.svg',
    personName: 'Chetan Mallappa Gowda',
    docNumber: 'DMGPG3819L',
    institution: 'Income Tax Department, Government of India',
    date: '',
    notes: 'Income Tax Department PAN · Permanent Account Number DMGPG3819L · Civil Contractor',
    svgDataUrl: generatePanSvg({
      name: 'Chetan Mallappa Gowda',
      fatherName: 'Mallappa Gowda',
      docNo: 'DMGPG3819L',
      dob: '08/03/1984',
    }),
    rowData: {
      title: 'PAN Card - Chetan Mallappa Gowda',
      type: 'id',
      holder: 'Chetan Mallappa Gowda',
      number: 'DMGPG3819L',
      notes: 'Income Tax Dept Permanent Account Number DMGPG3819L · Civil Contractor',
      hasAttachment: true,
      attachmentName: 'pan_card_chetan_mallappa_gowda.svg',
    },
  },

  // -----------------------------------------------------------------------
  // 4. AADHAAR CARDS (5 Documents, Masked DPDP Format)
  // -----------------------------------------------------------------------
  {
    id: 'trial-aadhaar-1',
    kind: 'rec',
    category: 'aadhaar',
    title: 'Masked Aadhaar Card - Vikram Aditya Sharma',
    fileName: 'aadhaar_card_vikram_aditya_sharma.svg',
    personName: 'Vikram Aditya Sharma',
    docNumber: 'XXXX XXXX 4819',
    institution: 'Unique Identification Authority of India (UIDAI)',
    date: '',
    notes: 'UIDAI Masked Aadhaar XXXX-XXXX-4819 · DPDP Compliant Masking · Resident New Delhi',
    svgDataUrl: generateAadhaarSvg({
      name: 'Vikram Aditya Sharma',
      docNo: 'XXXX XXXX 4819',
      dob: '12/05/1989',
      gender: 'Male / पुरुष',
      address: 'Pocket B, Mayur Vihar Phase II, East Delhi 110091',
    }),
    rowData: {
      title: 'Masked Aadhaar Card - Vikram Aditya Sharma',
      type: 'id',
      holder: 'Vikram Aditya Sharma',
      number: 'XXXX-XXXX-4819',
      notes: 'UIDAI Masked Aadhaar XXXX-XXXX-4819 · DPDP Act 2023 Masked Privacy Format',
      hasAttachment: true,
      attachmentName: 'aadhaar_card_vikram_aditya_sharma.svg',
    },
  },
  {
    id: 'trial-aadhaar-2',
    kind: 'rec',
    category: 'aadhaar',
    title: 'Masked Aadhaar Card - Ananya Sundaram',
    fileName: 'aadhaar_card_ananya_sundaram.svg',
    personName: 'Ananya Sundaram',
    docNumber: 'XXXX XXXX 6294',
    institution: 'Unique Identification Authority of India (UIDAI)',
    date: '',
    notes: 'UIDAI Masked Aadhaar XXXX-XXXX-6294 · DPDP Compliant Masking · Resident Chennai',
    svgDataUrl: generateAadhaarSvg({
      name: 'Ananya Sundaram',
      docNo: 'XXXX XXXX 6294',
      dob: '28/11/1993',
      gender: 'Female / महिला',
      address: '4th Main Road, Gandhi Nagar, Adyar, Chennai 600020',
    }),
    rowData: {
      title: 'Masked Aadhaar Card - Ananya Sundaram',
      type: 'id',
      holder: 'Ananya Sundaram',
      number: 'XXXX-XXXX-6294',
      notes: 'UIDAI Masked Aadhaar XXXX-XXXX-6294 · DPDP Act 2023 Masked Privacy Format',
      hasAttachment: true,
      attachmentName: 'aadhaar_card_ananya_sundaram.svg',
    },
  },
  {
    id: 'trial-aadhaar-3',
    kind: 'rec',
    category: 'aadhaar',
    title: 'Masked Aadhaar Card - Rajesh Arvind Kulkarni',
    fileName: 'aadhaar_card_rajesh_arvind_kulkarni.svg',
    personName: 'Rajesh Arvind Kulkarni',
    docNumber: 'XXXX XXXX 1934',
    institution: 'Unique Identification Authority of India (UIDAI)',
    date: '',
    notes: 'UIDAI Masked Aadhaar XXXX-XXXX-1934 · DPDP Compliant Masking · Resident Pune',
    svgDataUrl: generateAadhaarSvg({
      name: 'Rajesh Arvind Kulkarni',
      docNo: 'XXXX XXXX 1934',
      dob: '03/12/1979',
      gender: 'Male / पुरुष',
      address: 'B-402, Shivajinagar Heights, Model Colony, Pune 411016',
    }),
    rowData: {
      title: 'Masked Aadhaar Card - Rajesh Arvind Kulkarni',
      type: 'id',
      holder: 'Rajesh Arvind Kulkarni',
      number: 'XXXX-XXXX-1934',
      notes: 'UIDAI Masked Aadhaar XXXX-XXXX-1934 · DPDP Act 2023 Masked Privacy Format',
      hasAttachment: true,
      attachmentName: 'aadhaar_card_rajesh_arvind_kulkarni.svg',
    },
  },
  {
    id: 'trial-aadhaar-4',
    kind: 'rec',
    category: 'aadhaar',
    title: 'Masked Aadhaar Card - Sunita Devi Agrawal',
    fileName: 'aadhaar_card_sunita_devi_agrawal.svg',
    personName: 'Sunita Devi Agrawal',
    docNumber: 'XXXX XXXX 8302',
    institution: 'Unique Identification Authority of India (UIDAI)',
    date: '',
    notes: 'UIDAI Masked Aadhaar XXXX-XXXX-8302 · DPDP Compliant Masking · Resident Kolkata',
    svgDataUrl: generateAadhaarSvg({
      name: 'Sunita Devi Agrawal',
      docNo: 'XXXX XXXX 8302',
      dob: '15/06/1975',
      gender: 'Female / महिला',
      address: 'Flat 3A, Salt Lake Sector 1, Bidhannagar, Kolkata 700064',
    }),
    rowData: {
      title: 'Masked Aadhaar Card - Sunita Devi Agrawal',
      type: 'id',
      holder: 'Sunita Devi Agrawal',
      number: 'XXXX-XXXX-8302',
      notes: 'UIDAI Masked Aadhaar XXXX-XXXX-8302 · DPDP Act 2023 Masked Privacy Format',
      hasAttachment: true,
      attachmentName: 'aadhaar_card_sunita_devi_agrawal.svg',
    },
  },
  {
    id: 'trial-aadhaar-5',
    kind: 'rec',
    category: 'aadhaar',
    title: 'Masked Aadhaar Card - Chetan Mallappa Gowda',
    fileName: 'aadhaar_card_chetan_mallappa_gowda.svg',
    personName: 'Chetan Mallappa Gowda',
    docNumber: 'XXXX XXXX 5721',
    institution: 'Unique Identification Authority of India (UIDAI)',
    date: '',
    notes: 'UIDAI Masked Aadhaar XXXX-XXXX-5721 · DPDP Compliant Masking · Resident Bengaluru',
    svgDataUrl: generateAadhaarSvg({
      name: 'Chetan Mallappa Gowda',
      docNo: 'XXXX XXXX 5721',
      dob: '08/03/1984',
      gender: 'Male / पुरुष',
      address: '32nd Cross, 4th Block, Jayanagar, Bengaluru 560011',
    }),
    rowData: {
      title: 'Masked Aadhaar Card - Chetan Mallappa Gowda',
      type: 'id',
      holder: 'Chetan Mallappa Gowda',
      number: 'XXXX-XXXX-5721',
      notes: 'UIDAI Masked Aadhaar XXXX-XXXX-5721 · DPDP Act 2023 Masked Privacy Format',
      hasAttachment: true,
      attachmentName: 'aadhaar_card_chetan_mallappa_gowda.svg',
    },
  },

  // -----------------------------------------------------------------------
  // 5. BANK FIXED DEPOSITS (5 Documents)
  // -----------------------------------------------------------------------
  {
    id: 'trial-bank-fd-1',
    kind: 'inv',
    category: 'bank_fd',
    title: 'SBI Term Deposit - Vikram Aditya Sharma',
    fileName: 'sbi_term_deposit_vikram_aditya_sharma.svg',
    personName: 'Vikram Aditya Sharma',
    docNumber: '39482019481',
    institution: 'State Bank of India',
    amount: 450000,
    currentValue: 517450,
    rate: 7.1,
    date: '2026-10-12',
    issuedDate: '2024-10-12',
    notes: 'State Bank of India Term Deposit · Principal ₹4,50,000 · Rate 7.10% · MATURED ON 2026-10-12 (Overdue Alert)',
    isExpired: true,
    svgDataUrl: generateBankFdSvg({
      bankName: 'State Bank of India',
      headerColor: '#1d4ed8',
      accentColor: '#1e40af',
      accNo: '39482019481',
      holder: 'Vikram Aditya Sharma',
      depositAmount: 450000,
      maturityAmount: 517450,
      rate: 7.1,
      startDate: '2024-10-12',
      maturityDate: '2026-10-12',
      tenure: '2 Years (730 Days)',
      branch: 'Connaught Place Main Branch, New Delhi',
      isMatured: true,
    }),
    rowData: {
      name: 'SBI Special Term Deposit',
      type: 'fd',
      institution: 'State Bank of India',
      holder: 'Vikram Aditya Sharma',
      ref: '39482019481',
      invested: 450000,
      current: 517450,
      rate: 7.1,
      maturity: '2026-10-12',
      alerts: '30, 15, 7, 1',
      notes: 'State Bank of India Term Deposit · Principal ₹4,50,000 · Rate 7.10% · MATURED ON 2026-10-12',
      hasAttachment: true,
      attachmentName: 'sbi_term_deposit_vikram_aditya_sharma.svg',
    },
  },
  {
    id: 'trial-bank-fd-2',
    kind: 'inv',
    category: 'bank_fd',
    title: 'HDFC Bank Regular FD - Ananya Sundaram',
    fileName: 'hdfc_bank_fixed_deposit_ananya_sundaram.svg',
    personName: 'Ananya Sundaram',
    docNumber: '50300948210481',
    institution: 'HDFC Bank Ltd',
    amount: 600000,
    currentValue: 714300,
    rate: 7.25,
    date: '2027-04-18',
    issuedDate: '2024-10-18',
    notes: 'HDFC Bank Regular FD · Principal ₹6,00,000 · Rate 7.25% · Maturing 2027-04-18 · Anna Salai Branch',
    svgDataUrl: generateBankFdSvg({
      bankName: 'HDFC Bank Ltd',
      headerColor: '#004c8f',
      accentColor: '#002f5a',
      accNo: '50300948210481',
      holder: 'Ananya Sundaram',
      depositAmount: 600000,
      maturityAmount: 714300,
      rate: 7.25,
      startDate: '2024-10-18',
      maturityDate: '2027-04-18',
      tenure: '2.5 Years (912 Days)',
      branch: 'Anna Salai Branch, Chennai',
      isMatured: false,
    }),
    rowData: {
      name: 'HDFC Bank Regular Fixed Deposit',
      type: 'fd',
      institution: 'HDFC Bank Ltd',
      holder: 'Ananya Sundaram',
      ref: '50300948210481',
      invested: 600000,
      current: 714300,
      rate: 7.25,
      maturity: '2027-04-18',
      alerts: '30, 15, 7, 1',
      notes: 'HDFC Bank Regular FD · Principal ₹6,00,000 · Rate 7.25% · Maturing 18-04-2027',
      hasAttachment: true,
      attachmentName: 'hdfc_bank_fixed_deposit_ananya_sundaram.svg',
    },
  },
  {
    id: 'trial-bank-fd-3',
    kind: 'inv',
    category: 'bank_fd',
    title: 'Canara Bank Kamadhenu Deposit - Mohammed Farhan Qureshi',
    fileName: 'canara_bank_kamadhenu_deposit_mohammed_farhan_qureshi.svg',
    personName: 'Mohammed Farhan Qureshi',
    docNumber: '1849104002941',
    institution: 'Canara Bank',
    amount: 350000,
    currentValue: 402800,
    rate: 7.15,
    date: '2028-02-14',
    issuedDate: '2025-08-14',
    notes: 'Canara Bank Kamadhenu Deposit · Principal ₹3,50,000 · Rate 7.15% · Maturing 2028-02-14',
    svgDataUrl: generateBankFdSvg({
      bankName: 'Canara Bank',
      headerColor: '#0083cb',
      accentColor: '#ffb300',
      accNo: '1849104002941',
      holder: 'Mohammed Farhan Qureshi',
      depositAmount: 350000,
      maturityAmount: 402800,
      rate: 7.15,
      startDate: '2025-08-14',
      maturityDate: '2028-02-14',
      tenure: '2.5 Years (914 Days)',
      branch: 'Bandra West Branch, Mumbai',
      isMatured: false,
    }),
    rowData: {
      name: 'Canara Bank Kamadhenu Term Deposit',
      type: 'fd',
      institution: 'Canara Bank',
      holder: 'Mohammed Farhan Qureshi',
      ref: '1849104002941',
      invested: 350000,
      current: 402800,
      rate: 7.15,
      maturity: '2028-02-14',
      alerts: '30, 15, 7, 1',
      notes: 'Canara Bank Kamadhenu Term Deposit · Principal ₹3,50,000 · Rate 7.15% · Maturing 14-02-2028',
      hasAttachment: true,
      attachmentName: 'canara_bank_kamadhenu_deposit_mohammed_farhan_qureshi.svg',
    },
  },
  {
    id: 'trial-bank-fd-4',
    kind: 'inv',
    category: 'bank_fd',
    title: 'ICICI Bank FD - Rajesh Arvind Kulkarni',
    fileName: 'icici_bank_fixed_deposit_rajesh_arvind_kulkarni.svg',
    personName: 'Rajesh Arvind Kulkarni',
    docNumber: '004810592810',
    institution: 'ICICI Bank Ltd',
    amount: 500000,
    currentValue: 618200,
    rate: 7.2,
    date: '2027-11-20',
    issuedDate: '2024-11-20',
    notes: 'ICICI Bank Fixed Deposit · Principal ₹5,00,000 · Rate 7.20% · Maturing 2027-11-20',
    svgDataUrl: generateBankFdSvg({
      bankName: 'ICICI Bank Ltd',
      headerColor: '#b91c1c',
      accentColor: '#f97316',
      accNo: '004810592810',
      holder: 'Rajesh Arvind Kulkarni',
      depositAmount: 500000,
      maturityAmount: 618200,
      rate: 7.2,
      startDate: '2024-11-20',
      maturityDate: '2027-11-20',
      tenure: '3 Years (1095 Days)',
      branch: 'Shivajinagar Branch, Pune',
      isMatured: false,
    }),
    rowData: {
      name: 'ICICI Bank Cumulative FD',
      type: 'fd',
      institution: 'ICICI Bank Ltd',
      holder: 'Rajesh Arvind Kulkarni',
      ref: '004810592810',
      invested: 500000,
      current: 618200,
      rate: 7.2,
      maturity: '2027-11-20',
      alerts: '30, 15, 7, 1',
      notes: 'ICICI Bank Cumulative FD · Principal ₹5,00,000 · Rate 7.20% · Maturing 20-11-2027',
      hasAttachment: true,
      attachmentName: 'icici_bank_fixed_deposit_rajesh_arvind_kulkarni.svg',
    },
  },
  {
    id: 'trial-bank-fd-5',
    kind: 'inv',
    category: 'bank_fd',
    title: 'Bank of Baroda Advantage FD - Chetan Mallappa Gowda',
    fileName: 'bank_of_baroda_fixed_deposit_chetan_mallappa_gowda.svg',
    personName: 'Chetan Mallappa Gowda',
    docNumber: '28490100038194',
    institution: 'Bank of Baroda',
    amount: 400000,
    currentValue: 498600,
    rate: 7.3,
    date: '2028-09-10',
    issuedDate: '2025-09-10',
    notes: 'Bank of Baroda Baroda Advantage FD · Principal ₹4,00,000 · Rate 7.30% · Maturing 2028-09-10',
    svgDataUrl: generateBankFdSvg({
      bankName: 'Bank of Baroda',
      headerColor: '#ea580c',
      accentColor: '#c2410c',
      accNo: '28490100038194',
      holder: 'Chetan Mallappa Gowda',
      depositAmount: 400000,
      maturityAmount: 498600,
      rate: 7.3,
      startDate: '2025-09-10',
      maturityDate: '2028-09-10',
      tenure: '3 Years (1095 Days)',
      branch: 'Jayanagar Branch, Bengaluru',
      isMatured: false,
    }),
    rowData: {
      name: 'Bank of Baroda Advantage Term Deposit',
      type: 'fd',
      institution: 'Bank of Baroda',
      holder: 'Chetan Mallappa Gowda',
      ref: '28490100038194',
      invested: 400000,
      current: 498600,
      rate: 7.3,
      maturity: '2028-09-10',
      alerts: '30, 15, 7, 1',
      notes: 'Bank of Baroda Advantage FD · Principal ₹4,00,000 · Rate 7.30% · Maturing 10-09-2028',
      hasAttachment: true,
      attachmentName: 'bank_of_baroda_fixed_deposit_chetan_mallappa_gowda.svg',
    },
  },

  // -----------------------------------------------------------------------
  // 6. INSURANCE POLICIES (6 Documents: Personal, Medical, Vehicle)
  // -----------------------------------------------------------------------
  {
    id: 'trial-insurance-1',
    kind: 'due',
    category: 'insurance',
    subCategory: 'personal',
    title: 'LIC Jeevan Labh Policy - Sunita Devi Agrawal',
    fileName: 'lic_jeevan_labh_sunita_devi_agrawal.svg',
    personName: 'Sunita Devi Agrawal',
    docNumber: '849201934',
    institution: 'Life Insurance Corporation of India (LIC)',
    amount: 42500,
    currentValue: 1000000,
    date: '2027-02-28',
    notes: 'LIC Jeevan Labh Table 936 · Sum Assured ₹10,00,000 · Annual Premium ₹42,500 · Next Due 2027-02-28',
    svgDataUrl: generateInsuranceSvg({
      policyType: 'Personal',
      companyName: 'Life Insurance Corporation of India',
      policyNo: '849201934',
      holder: 'Sunita Devi Agrawal',
      details: 'LIC Jeevan Labh Plan (Table 936) · 16-10 Term',
      sumAssuredOrIdv: 1000000,
      premiumAmount: 42500,
      renewalDate: '2027-02-28',
      isOverdue: false,
    }),
    rowData: {
      name: 'LIC Jeevan Labh Policy Premium',
      category: 'insurance',
      provider: 'Life Insurance Corporation of India (LIC)',
      holder: 'Sunita Devi Agrawal',
      ref: 'Policy 849201934',
      amount: 42500,
      due: '2027-02-28',
      freq: 'annual',
      alerts: '30, 15, 7, 1',
      notes: 'LIC Policy 849201934 · Sum Assured ₹10,00,000 · Yearly Premium ₹42,500',
      hasAttachment: true,
      attachmentName: 'lic_jeevan_labh_sunita_devi_agrawal.svg',
    },
  },
  {
    id: 'trial-insurance-2',
    kind: 'due',
    category: 'insurance',
    subCategory: 'personal',
    title: 'HDFC Life Sanchay Plus - Gurpreet Singh Dhillon',
    fileName: 'hdfc_life_sanchay_plus_gurpreet_singh_dhillon.svg',
    personName: 'Gurpreet Singh Dhillon',
    docNumber: '009482014',
    institution: 'HDFC Life Insurance Co Ltd',
    amount: 65000,
    currentValue: 1200000,
    date: '2026-11-10',
    notes: 'HDFC Life Sanchay Plus Guaranteed Return · Sum Assured ₹12,00,000 · Premium ₹65,000 · Due Soon in 17 Days (2026-11-10)',
    svgDataUrl: generateInsuranceSvg({
      policyType: 'Personal',
      companyName: 'HDFC Life Insurance Co Ltd',
      policyNo: '009482014',
      holder: 'Gurpreet Singh Dhillon',
      details: 'HDFC Life Sanchay Plus · Long Term Income Option',
      sumAssuredOrIdv: 1200000,
      premiumAmount: 65000,
      renewalDate: '2026-11-10',
      isOverdue: false,
    }),
    rowData: {
      name: 'HDFC Life Sanchay Plus Premium',
      category: 'insurance',
      provider: 'HDFC Life Insurance Co Ltd',
      holder: 'Gurpreet Singh Dhillon',
      ref: 'Policy 009482014',
      amount: 65000,
      due: '2026-11-10',
      freq: 'annual',
      alerts: '30, 15, 7, 1',
      notes: 'HDFC Life Policy 009482014 · Sum Assured ₹12,00,000 · Annual Premium ₹65,000 · Due 10 Nov 2026',
      hasAttachment: true,
      attachmentName: 'hdfc_life_sanchay_plus_gurpreet_singh_dhillon.svg',
    },
  },
  {
    id: 'trial-insurance-3',
    kind: 'due',
    category: 'insurance',
    subCategory: 'medical',
    title: 'Star Health Comprehensive - Dr. Meenakshi Venkatraman',
    fileName: 'star_health_insurance_dr_meenakshi_venkatraman.svg',
    personName: 'Dr. Meenakshi Venkatraman',
    docNumber: 'SH-COMP-8492018-02',
    institution: 'Star Health & Allied Insurance Co Ltd',
    amount: 19850,
    currentValue: 1500000,
    date: '2026-10-05',
    notes: 'Star Health Comprehensive Insurance · Sum Insured ₹15,00,000 · OVERDUE PREMIUM SINCE 2026-10-05 (Urgent Alert)',
    isExpired: true,
    svgDataUrl: generateInsuranceSvg({
      policyType: 'Medical',
      companyName: 'Star Health & Allied Insurance Co Ltd',
      policyNo: 'SH-COMP-8492018-02',
      holder: 'Dr. Meenakshi Venkatraman',
      details: 'Star Comprehensive Family Floater · 1A + 2C',
      sumAssuredOrIdv: 1500000,
      premiumAmount: 19850,
      renewalDate: '2026-10-05',
      isOverdue: true,
    }),
    rowData: {
      name: 'Star Health Comprehensive Insurance Renewal',
      category: 'mediclaim',
      provider: 'Star Health & Allied Insurance Co Ltd',
      holder: 'Dr. Meenakshi Venkatraman',
      ref: 'SH-COMP-8492018-02',
      amount: 19850,
      due: '2026-10-05',
      freq: 'annual',
      alerts: '30, 15, 7, 1',
      notes: 'Star Health SH-COMP-8492018-02 · Sum Insured ₹15,00,000 · OVERDUE PREMIUM (Due was 05 Oct 2026)',
      hasAttachment: true,
      attachmentName: 'star_health_insurance_dr_meenakshi_venkatraman.svg',
    },
  },
  {
    id: 'trial-insurance-4',
    kind: 'due',
    category: 'insurance',
    subCategory: 'medical',
    title: 'Care Health Care Supreme - Pooja Harish Nair',
    fileName: 'care_health_insurance_pooja_harish_nair.svg',
    personName: 'Pooja Harish Nair',
    docNumber: 'CH-SUP-9284017',
    institution: 'Care Health Insurance Ltd',
    amount: 24800,
    currentValue: 2000000,
    date: '2027-01-15',
    notes: 'Care Supreme Health Insurance · Sum Insured ₹20,00,000 · Premium ₹24,800 · Next Renewal 2027-01-15',
    svgDataUrl: generateInsuranceSvg({
      policyType: 'Medical',
      companyName: 'Care Health Insurance Ltd',
      policyNo: 'CH-SUP-9284017',
      holder: 'Pooja Harish Nair',
      details: 'Care Supreme Plan · Unlimited Recharge Option',
      sumAssuredOrIdv: 2000000,
      premiumAmount: 24800,
      renewalDate: '2027-01-15',
      isOverdue: false,
    }),
    rowData: {
      name: 'Care Supreme Health Insurance Premium',
      category: 'mediclaim',
      provider: 'Care Health Insurance Ltd',
      holder: 'Pooja Harish Nair',
      ref: 'CH-SUP-9284017',
      amount: 24800,
      due: '2027-01-15',
      freq: 'annual',
      alerts: '30, 15, 7, 1',
      notes: 'Care Health Policy CH-SUP-9284017 · ₹20 Lakhs Sum Insured · Yearly Renewal ₹24,800',
      hasAttachment: true,
      attachmentName: 'care_health_insurance_pooja_harish_nair.svg',
    },
  },
  {
    id: 'trial-insurance-5',
    kind: 'due',
    category: 'insurance',
    subCategory: 'vehicle',
    title: 'ICICI Lombard Motor Insurance - Pooja Harish Nair',
    fileName: 'icici_lombard_motor_insurance_pooja_harish_nair.svg',
    personName: 'Pooja Harish Nair',
    docNumber: '3001/MI-8492018/00/000',
    institution: 'ICICI Lombard General Insurance Co Ltd',
    amount: 18450,
    currentValue: 1450000,
    date: '2026-09-28',
    notes: 'ICICI Lombard Comprehensive Motor Insurance · Tata Nexon EV KL-07-CM-4819 · EXPIRED ON 2026-09-28 (Overdue Alert)',
    isExpired: true,
    svgDataUrl: generateInsuranceSvg({
      policyType: 'Vehicle',
      companyName: 'ICICI Lombard General Insurance Co Ltd',
      policyNo: '3001/MI-8492018/00/000',
      holder: 'Pooja Harish Nair',
      details: 'Tata Nexon EV Empowered Plus · KL-07-CM-4819',
      sumAssuredOrIdv: 1450000,
      premiumAmount: 18450,
      renewalDate: '2026-09-28',
      isOverdue: true,
    }),
    rowData: {
      name: 'Tata Nexon EV Car Insurance Renewal',
      category: 'vehicle',
      provider: 'ICICI Lombard General Insurance Co Ltd',
      holder: 'Pooja Harish Nair',
      ref: 'KL-07-CM-4819 (Policy 3001/MI-8492018)',
      amount: 18450,
      due: '2026-09-28',
      freq: 'annual',
      alerts: '30, 15, 7, 1',
      notes: 'Tata Nexon EV Motor Insurance · EXPIRED 28 Sep 2026 (Requires Immediate Renewal to Drive Legally)',
      hasAttachment: true,
      attachmentName: 'icici_lombard_motor_insurance_pooja_harish_nair.svg',
    },
  },
  {
    id: 'trial-insurance-6',
    kind: 'due',
    category: 'insurance',
    subCategory: 'vehicle',
    title: 'New India Assurance 2-Wheeler - Gurpreet Singh Dhillon',
    fileName: 'new_india_two_wheeler_insurance_gurpreet_singh_dhillon.svg',
    personName: 'Gurpreet Singh Dhillon',
    docNumber: '12040031240100094820',
    institution: 'The New India Assurance Co Ltd',
    amount: 2840,
    currentValue: 68000,
    date: '2027-03-14',
    notes: 'New India Two-Wheeler Package Policy · Honda Activa 6G CH-01-BK-8291 · Next Due 2027-03-14',
    svgDataUrl: generateInsuranceSvg({
      policyType: 'Vehicle',
      companyName: 'The New India Assurance Co Ltd',
      policyNo: '12040031240100094820',
      holder: 'Gurpreet Singh Dhillon',
      details: 'Honda Activa 6G DLX · Reg CH-01-BK-8291',
      sumAssuredOrIdv: 68000,
      premiumAmount: 2840,
      renewalDate: '2027-03-14',
      isOverdue: false,
    }),
    rowData: {
      name: 'Honda Activa Scooter Insurance Renewal',
      category: 'vehicle',
      provider: 'The New India Assurance Co Ltd',
      holder: 'Gurpreet Singh Dhillon',
      ref: 'CH-01-BK-8291 (Policy 12040031240100094820)',
      amount: 2840,
      due: '2027-03-14',
      freq: 'annual',
      alerts: '30, 15, 7, 1',
      notes: 'Honda Activa 6G Insurance Policy · Annual Premium ₹2,840 · Due 14-03-2027',
      hasAttachment: true,
      attachmentName: 'new_india_two_wheeler_insurance_gurpreet_singh_dhillon.svg',
    },
  },

  // -----------------------------------------------------------------------
  // 7. MUTUAL FUNDS (5 Documents)
  // -----------------------------------------------------------------------
  {
    id: 'trial-mf-1',
    kind: 'inv',
    category: 'mutual_fund',
    title: 'SBI Bluechip Fund - Gurpreet Singh Dhillon',
    fileName: 'sbi_bluechip_fund_statement_gurpreet_singh_dhillon.svg',
    personName: 'Gurpreet Singh Dhillon',
    docNumber: '8492018/42',
    institution: 'SBI Mutual Fund',
    amount: 400000,
    currentValue: 485000,
    rate: 21.25,
    date: '2026-10-21',
    notes: 'SBI Bluechip Fund Direct Growth · Folio 8492018/42 · Invested ₹4,00,000 · Current ₹4,85,000 · KYC Verified',
    svgDataUrl: generateMutualFundSvg({
      amcName: 'SBI Mutual Fund',
      schemeName: 'SBI Bluechip Fund - Direct Plan Growth',
      folioNo: '8492018/42',
      holder: 'Gurpreet Singh Dhillon',
      nav: 78.12,
      units: 5120.44,
      investedAmount: 400000,
      currentValue: 485000,
      statementDate: '21-Oct-2026',
    }),
    rowData: {
      name: 'SBI Bluechip Fund Direct Growth',
      type: 'mf',
      institution: 'SBI Mutual Fund',
      holder: 'Gurpreet Singh Dhillon',
      ref: 'Folio 8492018/42',
      invested: 400000,
      current: 485000,
      notes: 'SBI Bluechip Fund Folio 8492018/42 · Invested ₹4,00,000 · Valuation ₹4,85,000 (+₹85,000 profit)',
      hasAttachment: true,
      attachmentName: 'sbi_bluechip_fund_statement_gurpreet_singh_dhillon.svg',
    },
  },
  {
    id: 'trial-mf-2',
    kind: 'inv',
    category: 'mutual_fund',
    title: 'Nippon India Small Cap - Irin Joseph',
    fileName: 'nippon_india_small_cap_statement_irin_joseph.svg',
    personName: 'Irin Joseph',
    docNumber: '9482019/33',
    institution: 'Nippon India Mutual Fund',
    amount: 250000,
    currentValue: 335000,
    rate: 34.0,
    date: '2026-10-22',
    notes: 'Nippon India Small Cap Fund Growth · Folio 9482019/33 · Invested ₹2,50,000 · Current ₹3,35,000',
    svgDataUrl: generateMutualFundSvg({
      amcName: 'Nippon India Mutual Fund',
      schemeName: 'Nippon India Small Cap Fund - Growth',
      folioNo: '9482019/33',
      holder: 'Irin Joseph',
      nav: 135.85,
      units: 1840.22,
      investedAmount: 250000,
      currentValue: 335000,
      statementDate: '22-Oct-2026',
    }),
    rowData: {
      name: 'Nippon India Small Cap Fund Growth',
      type: 'mf',
      institution: 'Nippon India Mutual Fund',
      holder: 'Irin Joseph',
      ref: 'Folio 9482019/33',
      invested: 250000,
      current: 335000,
      notes: 'Nippon India Small Cap Fund Folio 9482019/33 · Invested ₹2,50,000 · Valuation ₹3,35,000 (+₹85,000)',
      hasAttachment: true,
      attachmentName: 'nippon_india_small_cap_statement_irin_joseph.svg',
    },
  },
  {
    id: 'trial-mf-3',
    kind: 'inv',
    category: 'mutual_fund',
    title: 'HDFC Balanced Advantage - Pooja Harish Nair',
    fileName: 'hdfc_balanced_advantage_statement_pooja_harish_nair.svg',
    personName: 'Pooja Harish Nair',
    docNumber: '7391048/21',
    institution: 'HDFC Mutual Fund',
    amount: 350000,
    currentValue: 412000,
    rate: 17.71,
    date: '2026-10-20',
    notes: 'HDFC Balanced Advantage Fund Growth · Folio 7391048/21 · Invested ₹3,50,000 · Current ₹4,12,000',
    svgDataUrl: generateMutualFundSvg({
      amcName: 'HDFC Mutual Fund',
      schemeName: 'HDFC Balanced Advantage Fund - Growth',
      folioNo: '7391048/21',
      holder: 'Pooja Harish Nair',
      nav: 41.56,
      units: 8420.15,
      investedAmount: 350000,
      currentValue: 412000,
      statementDate: '20-Oct-2026',
    }),
    rowData: {
      name: 'HDFC Balanced Advantage Fund Growth',
      type: 'mf',
      institution: 'HDFC Mutual Fund',
      holder: 'Pooja Harish Nair',
      ref: 'Folio 7391048/21',
      invested: 350000,
      current: 412000,
      notes: 'HDFC Balanced Advantage Fund Folio 7391048/21 · Invested ₹3,50,000 · Valuation ₹4,12,000',
      hasAttachment: true,
      attachmentName: 'hdfc_balanced_advantage_statement_pooja_harish_nair.svg',
    },
  },
  {
    id: 'trial-mf-4',
    kind: 'inv',
    category: 'mutual_fund',
    title: 'ICICI Prudential Value Discovery - Irin Joseph',
    fileName: 'icici_pru_value_discovery_statement_irin_joseph.svg',
    personName: 'Irin Joseph',
    docNumber: '5820194/19',
    institution: 'ICICI Prudential AMC',
    amount: 280000,
    currentValue: 342000,
    rate: 22.14,
    date: '2026-10-22',
    notes: 'ICICI Prudential Value Discovery Direct Growth · Folio 5820194/19 · Invested ₹2,80,000 · Current ₹3,42,000',
    svgDataUrl: generateMutualFundSvg({
      amcName: 'ICICI Prudential Mutual Fund',
      schemeName: 'ICICI Prudential Value Discovery Fund - Growth',
      folioNo: '5820194/19',
      holder: 'Irin Joseph',
      nav: 274.43,
      units: 1020.3,
      investedAmount: 280000,
      currentValue: 342000,
      statementDate: '22-Oct-2026',
    }),
    rowData: {
      name: 'ICICI Prudential Value Discovery Fund',
      type: 'mf',
      institution: 'ICICI Prudential AMC',
      holder: 'Irin Joseph',
      ref: 'Folio 5820194/19',
      invested: 280000,
      current: 342000,
      notes: 'ICICI Prudential Value Discovery Fund Folio 5820194/19 · Invested ₹2,80,000 · Valuation ₹3,42,000',
      hasAttachment: true,
      attachmentName: 'icici_pru_value_discovery_statement_irin_joseph.svg',
    },
  },
  {
    id: 'trial-mf-5',
    kind: 'inv',
    category: 'mutual_fund',
    title: 'Mirae Asset Large Cap - Irin Joseph',
    fileName: 'mirae_asset_large_cap_statement_irin_joseph.svg',
    personName: 'Irin Joseph',
    docNumber: '6194820/54',
    institution: 'Mirae Asset Mutual Fund',
    amount: 300000,
    currentValue: 368000,
    rate: 22.67,
    date: '2026-10-23',
    notes: 'Mirae Asset Large Cap Fund Direct Growth · Folio 6194820/54 · Invested ₹3,00,000 · Current ₹3,68,000',
    svgDataUrl: generateMutualFundSvg({
      amcName: 'Mirae Asset Mutual Fund',
      schemeName: 'Mirae Asset Large Cap Fund - Direct Growth',
      folioNo: '6194820/54',
      holder: 'Irin Joseph',
      nav: 93.45,
      units: 3210.15,
      investedAmount: 300000,
      currentValue: 368000,
      statementDate: '23-Oct-2026',
    }),
    rowData: {
      name: 'Mirae Asset Large Cap Fund Growth',
      type: 'mf',
      institution: 'Mirae Asset Mutual Fund',
      holder: 'Irin Joseph',
      ref: 'Folio 6194820/54',
      invested: 300000,
      current: 368000,
      notes: 'Mirae Asset Large Cap Fund Folio 6194820/54 · Invested ₹3,00,000 · Valuation ₹3,68,000',
      hasAttachment: true,
      attachmentName: 'mirae_asset_large_cap_statement_irin_joseph.svg',
    },
  },

  // -----------------------------------------------------------------------
  // 8. UTILITY BILLS (5 Documents: Power & Water)
  // -----------------------------------------------------------------------
  {
    id: 'trial-utility-1',
    kind: 'due',
    category: 'utility_bill',
    subCategory: 'electricity',
    title: 'Tata Power Mumbai Electricity Bill - Gurpreet Singh Dhillon',
    fileName: 'tata_power_mumbai_electricity_bill_90001849201.svg',
    personName: 'Gurpreet Singh Dhillon',
    docNumber: '90001849201',
    institution: 'Tata Power Mumbai Distribution',
    amount: 3240,
    date: '2026-11-05',
    notes: 'Tata Power Consumer CA 90001849201 · Bill ₹3,240 · Due 05 Nov 2026 (Due Soon)',
    svgDataUrl: generateUtilityBillSvg({
      utilityType: 'Electricity',
      providerName: 'Tata Power Mumbai Distribution',
      consumerNo: '90001849201',
      consumerName: 'Gurpreet Singh Dhillon',
      billingPeriod: '01 Sep 2026 - 30 Sep 2026',
      billAmount: 3240,
      dueDate: '2026-11-05',
      address: 'Tower 4, Flat 1202, Lokhandwala Complex, Andheri West, Mumbai 400053',
      isOverdue: false,
    }),
    rowData: {
      name: 'Tata Power Electricity Bill',
      category: 'utility',
      provider: 'Tata Power Mumbai',
      holder: 'Gurpreet Singh Dhillon',
      ref: 'CA 90001849201',
      amount: 3240,
      due: '2026-11-05',
      freq: 'monthly',
      alerts: '7, 3, 1',
      notes: 'Tata Power Consumer 90001849201 · Bill ₹3,240 · Due 05 Nov 2026',
      hasAttachment: true,
      attachmentName: 'tata_power_mumbai_electricity_bill_90001849201.svg',
    },
  },
  {
    id: 'trial-utility-2',
    kind: 'due',
    category: 'utility_bill',
    subCategory: 'electricity',
    title: 'BESCOM Electricity Bill - Chetan Mallappa Gowda',
    fileName: 'bescom_bengaluru_electricity_bill_0482019482.svg',
    personName: 'Chetan Mallappa Gowda',
    docNumber: '0482019482',
    institution: 'BESCOM Karnataka',
    amount: 2680,
    date: '2026-10-18',
    notes: 'BESCOM Account 0482019482 · Bill ₹2,680 · OVERDUE SINCE 2026-10-18 (Urgent Payment Alert)',
    isExpired: true,
    svgDataUrl: generateUtilityBillSvg({
      utilityType: 'Electricity',
      providerName: 'Bangalore Electricity Supply Company (BESCOM)',
      consumerNo: '0482019482',
      consumerName: 'Chetan Mallappa Gowda',
      billingPeriod: '01 Sep 2026 - 30 Sep 2026',
      billAmount: 2680,
      dueDate: '2026-10-18',
      address: '32nd Cross, 4th Block, Jayanagar, Bengaluru 560011',
      isOverdue: true,
    }),
    rowData: {
      name: 'BESCOM Bengaluru Electricity Bill',
      category: 'utility',
      provider: 'BESCOM Karnataka',
      holder: 'Chetan Mallappa Gowda',
      ref: 'Account 0482019482',
      amount: 2680,
      due: '2026-10-18',
      freq: 'monthly',
      alerts: '7, 3, 1',
      notes: 'BESCOM Power Bill · OVERDUE (Due was 18 Oct 2026 · Bill ₹2,680)',
      hasAttachment: true,
      attachmentName: 'bescom_bengaluru_electricity_bill_0482019482.svg',
    },
  },
  {
    id: 'trial-utility-3',
    kind: 'due',
    category: 'utility_bill',
    subCategory: 'electricity',
    title: 'Adani Electricity Mumbai Bill - Irin Joseph',
    fileName: 'adani_electricity_mumbai_bill_152049182.svg',
    personName: 'Irin Joseph',
    docNumber: '152049182',
    institution: 'Adani Electricity Mumbai Ltd',
    amount: 2150,
    date: '2026-11-18',
    notes: 'Adani Electricity Consumer 152049182 · Bill ₹2,150 · Due 18 Nov 2026',
    svgDataUrl: generateUtilityBillSvg({
      utilityType: 'Electricity',
      providerName: 'Adani Electricity Mumbai Ltd',
      consumerNo: '152049182',
      consumerName: 'Irin Joseph',
      billingPeriod: '01 Oct 2026 - 31 Oct 2026',
      billAmount: 2150,
      dueDate: '2026-11-18',
      address: 'Sea View Apartments, Worli Sea Face, Mumbai 400018',
      isOverdue: false,
    }),
    rowData: {
      name: 'Adani Electricity Bill',
      category: 'utility',
      provider: 'Adani Electricity Mumbai Ltd',
      holder: 'Irin Joseph',
      ref: 'Consumer 152049182',
      amount: 2150,
      due: '2026-11-18',
      freq: 'monthly',
      alerts: '7, 3, 1',
      notes: 'Adani Electricity Mumbai · Consumer 152049182 · Bill ₹2,150 · Due 18 Nov 2026',
      hasAttachment: true,
      attachmentName: 'adani_electricity_mumbai_bill_152049182.svg',
    },
  },
  {
    id: 'trial-utility-4',
    kind: 'due',
    category: 'utility_bill',
    subCategory: 'water',
    title: 'Delhi Jal Board Water Bill - Irin Joseph',
    fileName: 'delhi_jal_board_water_bill_4920184029.svg',
    personName: 'Irin Joseph',
    docNumber: '4920184029',
    institution: 'Delhi Jal Board (DJB)',
    amount: 840,
    date: '2026-10-15',
    notes: 'Delhi Jal Board K No. 4920184029 · Bill ₹840 · OVERDUE SINCE 2026-10-15 (Urgent Payment Alert)',
    isExpired: true,
    svgDataUrl: generateUtilityBillSvg({
      utilityType: 'Water',
      providerName: 'Delhi Jal Board (Government of NCT of Delhi)',
      consumerNo: '4920184029',
      consumerName: 'Irin Joseph',
      billingPeriod: '01 Aug 2026 - 30 Sep 2026',
      billAmount: 840,
      dueDate: '2026-10-15',
      address: 'Pocket B, Mayur Vihar Phase II, East Delhi 110091',
      isOverdue: true,
    }),
    rowData: {
      name: 'Delhi Jal Board Water Bill',
      category: 'utility',
      provider: 'Delhi Jal Board',
      holder: 'Irin Joseph',
      ref: 'K No. 4920184029',
      amount: 840,
      due: '2026-10-15',
      freq: 'bimonthly',
      alerts: '5, 2, 0',
      notes: 'Delhi Jal Board K No. 4920184029 · OVERDUE (Due was 15 Oct 2026 · Bill ₹840)',
      hasAttachment: true,
      attachmentName: 'delhi_jal_board_water_bill_4920184029.svg',
    },
  },
  {
    id: 'trial-utility-5',
    kind: 'due',
    category: 'utility_bill',
    subCategory: 'water',
    title: 'BWSSB Bengaluru Water Bill - Pooja Harish Nair',
    fileName: 'bwssb_bengaluru_water_bill_e1849201.svg',
    personName: 'Pooja Harish Nair',
    docNumber: 'RR No E1-849201',
    institution: 'Bangalore Water Supply and Sewerage Board (BWSSB)',
    amount: 980,
    date: '2026-11-25',
    notes: 'BWSSB Water RR No E1-849201 · Bill ₹980 · Due 25 Nov 2026 · Jayanagar 4th Block',
    svgDataUrl: generateUtilityBillSvg({
      utilityType: 'Water',
      providerName: 'Bangalore Water Supply and Sewerage Board (BWSSB)',
      consumerNo: 'RR No E1-849201',
      consumerName: 'Pooja Harish Nair',
      billingPeriod: '01 Oct 2026 - 31 Oct 2026',
      billAmount: 980,
      dueDate: '2026-11-25',
      address: '32nd Cross, 4th Block, Jayanagar, Bengaluru 560011',
      isOverdue: false,
    }),
    rowData: {
      name: 'BWSSB Water & Sanitary Bill',
      category: 'utility',
      provider: 'BWSSB',
      holder: 'Pooja Harish Nair',
      ref: 'RR No E1-849201',
      amount: 980,
      due: '2026-11-25',
      freq: 'monthly',
      alerts: '5, 2, 0',
      notes: 'BWSSB Water & Sanitary RR No E1-849201 · Amount ₹980 · Due 25 Nov 2026',
      hasAttachment: true,
      attachmentName: 'bwssb_bengaluru_water_bill_e1849201.svg',
    },
  },
];

// Helper to convert all dummy documents into ready-to-load AppRows with attachments pre-linked
export function getInitialTrialAppRows(): AppRow[] {
  const baseRows = DUMMY_DOCUMENTS.map((doc) => ({
    id: doc.id,
    kind: doc.kind,
    data: {
      ...doc.rowData,
      attachmentUrl: doc.svgDataUrl,
      attachmentName: doc.fileName,
      hasAttachment: true,
    },
  }));
  return reclassifyMisplacedEntries(baseRows).migratedRows;
}

// Helper to trigger browser download of a text or file blob
function triggerBlobDownload(fileName: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Helper to trigger text download
function triggerDownload(fileName: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  triggerBlobDownload(fileName, blob);
}

// Download a single dummy document file (SVG) for OCR testing
export function downloadDummyDocFile(doc: DummyDocument) {
  const svgText = decodeURIComponent(doc.svgDataUrl.replace('data:image/svg+xml;charset=utf-8,', ''));
  triggerDownload(doc.fileName, svgText, 'image/svg+xml');
}

// Returns a safe, in-memory synthetic File object for test auto-scanning without network roundtrips
export function getSyntheticSpecimenFile(category: 'passport' | 'licence' | 'pan' | 'aadhaar' | 'bank_fd' | 'insurance' | 'mutual_fund' | 'utility_bill'): { file: File; doc: DummyDocument } {
  const doc = DUMMY_DOCUMENTS.find((d) => d.category === category) || DUMMY_DOCUMENTS[0];
  const svgText = decodeURIComponent(doc.svgDataUrl.replace('data:image/svg+xml;charset=utf-8,', ''));
  const blob = new Blob([svgText], { type: 'image/svg+xml' });
  const file = new File([blob], doc.fileName, { type: 'image/svg+xml' });
  return { file, doc };
}

// Generate CSV string from dummy documents
export function generateCsvFromDocs(docs: DummyDocument[]): string {
  const cols = [
    'Kind',
    'Category',
    'Title / Name',
    'Institution / Provider',
    'Person / Holder',
    'Document / Account No',
    'Amount / Principal (₹)',
    'Current / Maturity Value (₹)',
    'Interest Rate (%)',
    'Due / Expiry / Maturity Date',
    'Alert Status',
    'DPDP Compliance Status',
    'File Name',
    'Notes / Details',
  ];

  const q = (v: any) => `"${String(v ?? '').replace(/"/g, '""')}"`;

  const rows = docs.map((d) => [
    d.kind.toUpperCase(),
    d.category.toUpperCase(),
    d.title,
    d.institution,
    d.personName,
    d.docNumber,
    d.amount != null ? d.amount : '',
    d.currentValue != null ? d.currentValue : '',
    d.rate != null ? `${d.rate}%` : '',
    d.date || 'N/A',
    getDocAlertStatus(d),
    'DPDP Act 2023 Compliant (Synthetic Test Asset)',
    d.fileName,
    d.notes,
  ]);

  return [cols.map(q).join(','), ...rows.map((r) => r.map(q).join(','))].join('\n');
}

// Generate real multi-sheet Excel workbook using XLSX
export function generateMasterWorkbook(): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();

  // Sheet 1: All 41 Documents
  const allDocsData = DUMMY_DOCUMENTS.map((d, idx) => ({
    'Sl No': idx + 1,
    'Asset ID': d.id,
    'App Kind': d.kind.toUpperCase(),
    'Category': d.category.toUpperCase(),
    'Document Title': d.title,
    'Holder Name (10 Persons)': d.personName,
    'Institution / Provider': d.institution,
    'Account / Doc Number': d.docNumber,
    'Amount / Principal (₹)': d.amount != null ? d.amount : '',
    'Current / Maturity Value (₹)': d.currentValue != null ? d.currentValue : '',
    'Interest Rate (%)': d.rate != null ? `${d.rate}%` : '',
    'Due / Expiry Date': d.date || 'N/A',
    'Alert Status': getDocAlertStatus(d),
    'File Name': d.fileName,
    'DPDP Act 2023 Compliance': '100% Synthetic Test Data',
    'Notes / Description': d.notes,
  }));
  const wsAll = XLSX.utils.json_to_sheet(allDocsData);
  XLSX.utils.book_append_sheet(wb, wsAll, 'All 41 Trial Assets');

  // Sheet 2: 10 Synthetic Persons Index
  const personsData = SYNTHETIC_PERSONS.map((p, idx) => {
    const docs = DUMMY_DOCUMENTS.filter((d) => d.personName === p.name);
    const expiredCount = docs.filter((d) => {
      const status = getDocAlertStatus(d);
      return status.includes('OVERDUE') || status.includes('EXPIRED') || status.includes('MATURED');
    }).length;
    return {
      'Person #': idx + 1,
      'Full Name': p.name,
      'City / Location': p.city,
      'Profile / Occupation': p.role,
      'Total Documents': docs.length,
      'Active Documents': docs.length - expiredCount,
      'Expired / Overdue Alerts': expiredCount,
      'Portfolio Assets Summary': docs.map((d) => d.title).join(' | '),
    };
  });
  const wsPersons = XLSX.utils.json_to_sheet(personsData);
  XLSX.utils.book_append_sheet(wb, wsPersons, '10 Persons Portfolio Index');

  // Sheet 3: Bank Fixed Deposits (5)
  const fdData = DUMMY_DOCUMENTS.filter((d) => d.category === 'bank_fd').map((d, i) => ({
    'Sl No': i + 1,
    'Bank Name': d.institution,
    'Depositor Name': d.personName,
    'Account Number': d.docNumber,
    'Deposit Amount (₹)': d.amount,
    'Maturity Value (₹)': d.currentValue,
    'Interest Rate': `${d.rate}% p.a.`,
    'Maturity Date': d.date,
    'Alert Status': getDocAlertStatus(d),
    'Document File': d.fileName,
  }));
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(fdData), 'Bank Fixed Deposits');

  // Sheet 4: Official ID Records (20)
  const idData = DUMMY_DOCUMENTS.filter((d) => ['passport', 'licence', 'pan', 'aadhaar'].includes(d.category)).map((d, i) => ({
    'Sl No': i + 1,
    'ID Type': d.category.toUpperCase(),
    'Title': d.title,
    'Holder Name': d.personName,
    'Document Number': d.docNumber,
    'Expiry / Validity': d.date || 'Permanent',
    'Alert Status': getDocAlertStatus(d),
    'Document File': d.fileName,
  }));
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(idData), 'Official ID Records');

  // Sheet 5: Insurance Policies (6)
  const insData = DUMMY_DOCUMENTS.filter((d) => d.category === 'insurance').map((d, i) => ({
    'Sl No': i + 1,
    'Insurance Type': (d.subCategory || 'Insurance').toUpperCase(),
    'Insurance Company': d.institution,
    'Policyholder': d.personName,
    'Policy Number': d.docNumber,
    'Sum Assured / IDV (₹)': d.currentValue,
    'Annual Premium (₹)': d.amount,
    'Renewal / Due Date': d.date,
    'Alert Status': getDocAlertStatus(d),
    'Document File': d.fileName,
  }));
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(insData), 'Insurance Policies');

  // Sheet 6: Mutual Funds (5)
  const mfData = DUMMY_DOCUMENTS.filter((d) => d.category === 'mutual_fund').map((d, i) => ({
    'Sl No': i + 1,
    'Fund House (AMC)': d.institution,
    'Scheme Name': d.title,
    'Investor Name': d.personName,
    'Folio Number': d.docNumber,
    'Purchase Cost (₹)': d.amount,
    'Current Valuation (₹)': d.currentValue,
    'Statement Date': d.date,
    'Document File': d.fileName,
  }));
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(mfData), 'Mutual Funds');

  // Sheet 7: Utility Bills (5)
  const billData = DUMMY_DOCUMENTS.filter((d) => d.category === 'utility_bill').map((d, i) => ({
    'Sl No': i + 1,
    'Utility Type': (d.subCategory || 'Utility').toUpperCase(),
    'Service Provider': d.institution,
    'Consumer Name': d.personName,
    'Consumer Account No': d.docNumber,
    'Bill Amount (₹)': d.amount,
    'Payment Due Date': d.date,
    'Alert Status': getDocAlertStatus(d),
    'Document File': d.fileName,
  }));
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(billData), 'Utility Bills');

  return wb;
}

// Download real multi-sheet Excel spreadsheet (.xlsx)
export function downloadMasterTrialXlsx() {
  const wb = generateMasterWorkbook();
  const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
  const blob = new Blob([wbout], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  triggerBlobDownload('PaisaPal_Trial_Master_Data_10_Persons.xlsx', blob);
}

// Download CSV file
export function downloadMasterTrialExcel() {
  const csv = generateCsvFromDocs(DUMMY_DOCUMENTS);
  triggerDownload('paisa_pal_trial_master_41_records_10_persons.csv', csv, 'text/csv;charset=utf-8;');
}

// Download Category specific trial Excel sheets
export function downloadCategoryTrialExcel(category: string) {
  let filtered = DUMMY_DOCUMENTS;
  let filename = 'paisa_pal_trial_records.csv';

  if (category === 'bank_fd') {
    filtered = DUMMY_DOCUMENTS.filter((d) => d.category === 'bank_fd');
    filename = 'trial_bank_fixed_deposits.csv';
  } else if (category === 'records') {
    filtered = DUMMY_DOCUMENTS.filter((d) => ['passport', 'licence', 'pan', 'aadhaar'].includes(d.category));
    filename = 'trial_official_documents_records.csv';
  } else if (category === 'insurance') {
    filtered = DUMMY_DOCUMENTS.filter((d) => d.category === 'insurance');
    filename = 'trial_insurance_policies.csv';
  } else if (category === 'mutual_fund') {
    filtered = DUMMY_DOCUMENTS.filter((d) => d.category === 'mutual_fund');
    filename = 'trial_mutual_funds.csv';
  } else if (category === 'utility_bill') {
    filtered = DUMMY_DOCUMENTS.filter((d) => d.category === 'utility_bill');
    filename = 'trial_utility_bills.csv';
  }

  const csv = generateCsvFromDocs(filtered);
  triggerDownload(filename, csv, 'text/csv;charset=utf-8;');
}

// Download Complete 41 Trial Assets as a structured ZIP Archive with folders, Excel, and README
export async function downloadAllTrialAssetsZip(onProgress?: (percent: number) => void): Promise<void> {
  const zip = new JSZip();

  const readmeContent = `================================================================================
PAISA PAL - COMPLETE 41 TRIAL ASSETS & 10 SYNTHETIC PERSONS TEST PACK
DPDP Act 2023 Compliant · 100% Synthetic Test Documents & Excel Spreadsheets
================================================================================

Welcome to the Paisa Pal Trial Experimentation Pack.
This archive contains:
1. All 41 high-fidelity vector documents (.svg) organized into category subfolders.
2. PaisaPal_Trial_Master_Data_10_Persons.xlsx (7-sheet comprehensive workbook).
3. PaisaPal_Trial_Master_Data_10_Persons.csv (Universal CSV format).

--------------------------------------------------------------------------------
THE 10 SYNTHETIC HOUSEHOLD PERSONS & DOCUMENT COMBINATIONS
--------------------------------------------------------------------------------
All 41 trial assets are distributed across exactly 10 synthetic individuals, 
providing realistic multiple-document combinations for each household member:

1. Vikram Aditya Sharma (New Delhi · Tech Lead / Salaried Professional)
   - 01_Passports/passport_vikram_aditya_sharma.svg [Valid till 2034-08-14]
   - 03_PAN_Cards/pan_card_vikram_aditya_sharma.svg [BPWPS4820K]
   - 04_Aadhaar_Cards/aadhaar_card_vikram_aditya_sharma.svg [XXXX-XXXX-4819]
   - 05_Bank_Fixed_Deposits/sbi_term_deposit_vikram_aditya_sharma.svg [₹4.5L · MATURED 2026-10-12 ⚠ OVERDUE ALERT]

2. Ananya Sundaram (Chennai · Principal Architect)
   - 01_Passports/passport_ananya_sundaram.svg [Valid till 2033-03-22]
   - 02_Driving_Licences/driving_licence_ananya_sundaram.svg [TN-01 · EXPIRED 2026-09-15 ⚠ OVERDUE ALERT]
   - 04_Aadhaar_Cards/aadhaar_card_ananya_sundaram.svg [XXXX-XXXX-6294]
   - 05_Bank_Fixed_Deposits/hdfc_bank_fixed_deposit_ananya_sundaram.svg [₹6.0L · Maturing 2027-04-18]

3. Mohammed Farhan Qureshi (Mumbai · Logistics Business Owner)
   - 01_Passports/passport_mohammed_farhan_qureshi.svg [Valid till 2035-11-09]
   - 02_Driving_Licences/driving_licence_mohammed_farhan_qureshi.svg [MH-02 · Valid till 2038-06-18]
   - 03_PAN_Cards/pan_card_mohammed_farhan_qureshi.svg [AFBPQ5918E]
   - 05_Bank_Fixed_Deposits/canara_bank_kamadhenu_deposit_mohammed_farhan_qureshi.svg [₹3.5L · Maturing 2028-02-14]

4. Dr. Meenakshi Venkatraman (Bengaluru · Healthcare Specialist & Consultant)
   - 01_Passports/passport_dr_meenakshi_venkatraman.svg [Valid till 2031-07-29]
   - 02_Driving_Licences/driving_licence_dr_meenakshi_venkatraman.svg [KA-05 · Valid till 2036-12-04]
   - 03_PAN_Cards/pan_card_dr_meenakshi_venkatraman.svg [CGMPV6192M]
   - 06_Insurance_Policies/star_health_insurance_dr_meenakshi_venkatraman.svg [₹15L Cover · OVERDUE SINCE 2026-10-05 ⚠ ALERT]

5. Rajesh Arvind Kulkarni (Pune · Senior Mechanical Engineer)
   - 01_Passports/passport_rajesh_arvind_kulkarni.svg [V9481024 · EXPIRED 2026-08-20 ⚠ OVERDUE ALERT]
   - 02_Driving_Licences/driving_licence_rajesh_arvind_kulkarni.svg [MH-12 · Valid till 2037-09-24]
   - 04_Aadhaar_Cards/aadhaar_card_rajesh_arvind_kulkarni.svg [XXXX-XXXX-1934]
   - 05_Bank_Fixed_Deposits/icici_bank_fixed_deposit_rajesh_arvind_kulkarni.svg [₹5.0L · Maturing 2027-11-20]

6. Sunita Devi Agrawal (Kolkata · Homemaker & Active Portfolio Investor)
   - 02_Driving_Licences/driving_licence_sunita_devi_agrawal.svg [WB-06 · Valid till 2039-01-30]
   - 03_PAN_Cards/pan_card_sunita_devi_agrawal.svg [AHAPA7291F]
   - 04_Aadhaar_Cards/aadhaar_card_sunita_devi_agrawal.svg [XXXX-XXXX-8302]
   - 06_Insurance_Policies/lic_jeevan_labh_sunita_devi_agrawal.svg [₹10L Sum Assured · Due 2027-02-28]

7. Chetan Mallappa Gowda (Bengaluru · Civil Infrastructure Contractor)
   - 03_PAN_Cards/pan_card_chetan_mallappa_gowda.svg [DMGPG3819L]
   - 04_Aadhaar_Cards/aadhaar_card_chetan_mallappa_gowda.svg [XXXX-XXXX-5721]
   - 05_Bank_Fixed_Deposits/bank_of_baroda_fixed_deposit_chetan_mallappa_gowda.svg [₹4.0L · Maturing 2028-09-10]
   - 08_Utility_Bills/bescom_bengaluru_electricity_bill_0482019482.svg [₹2,680 · OVERDUE SINCE 2026-10-18 ⚠ ALERT]

8. Pooja Harish Nair (Kochi · UI/UX Design Director)
   - 06_Insurance_Policies/care_health_insurance_pooja_harish_nair.svg [₹20L Cover · Due 2027-01-15]
   - 06_Insurance_Policies/icici_lombard_motor_insurance_pooja_harish_nair.svg [Tata Nexon EV · EXPIRED 2026-09-28 ⚠ ALERT]
   - 07_Mutual_Funds/hdfc_balanced_advantage_statement_pooja_harish_nair.svg [₹3.5L Invested · ₹4.12L Current]
   - 08_Utility_Bills/bwssb_bengaluru_water_bill_e1849201.svg [₹980 · Due 2026-11-25]

9. Gurpreet Singh Dhillon (Chandigarh · Agro-Business Entrepreneur)
   - 06_Insurance_Policies/hdfc_life_sanchay_plus_gurpreet_singh_dhillon.svg [₹12L Cover · Due 2026-11-10 ⚡ DUE SOON]
   - 06_Insurance_Policies/new_india_two_wheeler_insurance_gurpreet_singh_dhillon.svg [Honda Activa · Due 2027-03-14]
   - 07_Mutual_Funds/sbi_bluechip_fund_statement_gurpreet_singh_dhillon.svg [₹4.0L Invested · ₹4.85L Current]
   - 08_Utility_Bills/tata_power_mumbai_electricity_bill_90001849201.svg [₹3,240 · Due 2026-11-05 ⚡ DUE SOON]

10. Irin Joseph (Kochi · Financial Analyst)
   - 07_Mutual_Funds/nippon_india_small_cap_statement_irin_joseph.svg [₹2.5L Invested · ₹3.35L Current]
   - 07_Mutual_Funds/icici_pru_value_discovery_statement_irin_joseph.svg [₹2.8L Invested · ₹3.42L Current]
   - 07_Mutual_Funds/mirae_asset_large_cap_statement_irin_joseph.svg [₹3.0L Invested · ₹3.68L Current]
   - 08_Utility_Bills/adani_electricity_mumbai_bill_152049182.svg [₹2,150 · Due 2026-11-18]
   - 08_Utility_Bills/delhi_jal_board_water_bill_4920184029.svg [₹840 · OVERDUE SINCE 2026-10-15 ⚠ ALERT]

--------------------------------------------------------------------------------
EXPIRED & OVERDUE TRIAL ALERTS SUMMARY (TODAY'S DATE: 2026-10-24)
--------------------------------------------------------------------------------
The following 7 documents have intentionally expired / overdue dates to test 
Paisa Pal's alert dashboard, red badge indicators, and WhatsApp digest:
1. Vikram Aditya Sharma: SBI FD (Matured 2026-10-12)
2. Ananya Sundaram: Driving Licence (Expired 2026-09-15)
3. Dr. Meenakshi Venkatraman: Star Health Insurance (Overdue 2026-10-05)
4. Rajesh Arvind Kulkarni: Passport (Expired 2026-08-20)
5. Chetan Mallappa Gowda: BESCOM Power Bill (Overdue 2026-10-18)
6. Pooja Harish Nair: ICICI Lombard Car Insurance (Expired 2026-09-28)
7. Irin Joseph: Delhi Jal Board Water Bill (Overdue 2026-10-15)

--------------------------------------------------------------------------------
HOW TO TEST IN PAISA PAL:
--------------------------------------------------------------------------------
1. Extract this ZIP archive to a folder on your computer.
2. In Paisa Pal, click "Upload Document" or open "Trial Documents Hub".
3. Drag and drop any individual document (.svg) or upload the spreadsheet (.xlsx).
4. Notice how Paisa Pal accurately captures the Holder Name, Provider/Institution, 
   Account/Doc Number, Principal/Maturity Amounts, and Date into the correct view!
================================================================================`;

  zip.file('README_TRIAL_EXPERIMENTATION.txt', readmeContent);

  // Generate Excel workbook & CSV
  const wb = generateMasterWorkbook();
  const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
  zip.file('PaisaPal_Trial_Master_Data_10_Persons.xlsx', wbout);

  const csv = generateCsvFromDocs(DUMMY_DOCUMENTS);
  zip.file('PaisaPal_Trial_Master_Data_10_Persons.csv', csv);

  // Folder mapping
  const categoryFolders: Record<string, string> = {
    passport: '01_Passports',
    licence: '02_Driving_Licences',
    pan: '03_PAN_Cards',
    aadhaar: '04_Aadhaar_Cards',
    bank_fd: '05_Bank_Fixed_Deposits',
    insurance: '06_Insurance_Policies',
    mutual_fund: '07_Mutual_Funds',
    utility_bill: '08_Utility_Bills',
  };

  for (const doc of DUMMY_DOCUMENTS) {
    const folder = categoryFolders[doc.category] || '09_Other_Documents';
    const svgText = decodeURIComponent(doc.svgDataUrl.replace('data:image/svg+xml;charset=utf-8,', ''));
    zip.file(`${folder}/${doc.fileName}`, svgText);
  }

  const blob = await zip.generateAsync({ type: 'blob' }, (metadata) => {
    onProgress?.(Math.round(metadata.percent));
  });

  triggerBlobDownload('PaisaPal_41_Trial_Assets_Pack.zip', blob);
}
