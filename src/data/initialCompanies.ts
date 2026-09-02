import { Company, CompanyData, Asset, CapexItem, RiskFinding, VerificationScanRecord } from '../types';
import { INITIAL_ASSETS, INITIAL_CAPEX_QUEUE, INITIAL_RISK_FINDINGS, INITIAL_SCAN_LOGS } from './mockData';

export const DEFAULT_COMPANIES: Company[] = [
  {
    id: 'comp-assettrust',
    name: 'AssetTrust Enterprise Manufacturing Ltd.',
    shortCode: 'AST',
    legalEntityType: 'Public Limited',
    cin: 'L28920MH2012PLC234567',
    gstin: '27AABCA1234F1Z5',
    industry: 'Automotive & Precision Engineering',
    fiscalYear: '2024-2025',
    depreciationPolicy: 'Dual Depreciation (Both)',
    plants: [
      'Pune Plant - Chakan',
      'Chennai Automotive Hub',
      'Manesar Tooling Hub',
      'Sanand EV Plant',
      'Bengaluru HQ & Tech Center'
    ],
    baseCurrency: 'INR',
    description: 'Enterprise precision manufacturing & automotive components conglomerate operating 5 major manufacturing hubs.',
    logoColor: 'from-blue-600 to-indigo-700',
    createdAt: '2024-04-01',
    isCustom: false
  },
  {
    id: 'comp-biozenith',
    name: 'BioZenith Life Sciences & API Pharma Ltd.',
    shortCode: 'BZP',
    legalEntityType: 'Public Limited',
    cin: 'L24230TG2015PLC098765',
    gstin: '36AABCB5678G2Z1',
    industry: 'Pharmaceuticals & Life Sciences',
    fiscalYear: '2024-2025',
    depreciationPolicy: 'Companies Act 2013 Sch II (SLM)',
    plants: [
      'Hyderabad Genome Valley Sterile Unit',
      'Vizag Bulk Drugs & API Facility',
      'Baddi Formulation Plant'
    ],
    baseCurrency: 'INR',
    description: 'US-FDA compliant pharmaceutical formulation & bulk active pharmaceutical ingredients manufacturing.',
    logoColor: 'from-emerald-600 to-teal-700',
    createdAt: '2024-04-01',
    isCustom: false
  },
  {
    id: 'comp-sunvolt',
    name: 'SunVolt CleanTech & Solar Energy Ltd.',
    shortCode: 'SVT',
    legalEntityType: 'Private Limited',
    cin: 'U40106GJ2018PTC104521',
    gstin: '24AABCS9912K1Z9',
    industry: 'Renewable Energy & Solar Infrastructure',
    fiscalYear: '2024-2025',
    depreciationPolicy: 'Companies Act 2013 Sch II (SLM)',
    plants: [
      'Kutch 500MW Solar Park',
      'Bhadla Solar Grid Hub',
      'Ahmedabad Inverter & Battery Plant'
    ],
    baseCurrency: 'INR',
    description: 'Grid-scale utility solar developer with extensive ground-mounted PV arrays, central inverters, and high-voltage substations.',
    logoColor: 'from-amber-500 to-orange-600',
    createdAt: '2024-04-01',
    isCustom: false
  }
];

export const INITIAL_COMPANY_DATA_MAP: Record<string, CompanyData> = {
  'comp-assettrust': {
    company: DEFAULT_COMPANIES[0],
    assets: INITIAL_ASSETS,
    capexQueue: INITIAL_CAPEX_QUEUE,
    risks: INITIAL_RISK_FINDINGS,
    scanLogs: INITIAL_SCAN_LOGS
  },
  'comp-biozenith': {
    company: DEFAULT_COMPANIES[1],
    assets: [
      {
        id: 'AST-HYD-LYO-0012',
        name: 'Industrial Freeze Dryer (Lyophilizer) 200kg Capacity',
        category: 'Plant & Machinery',
        plant: 'Hyderabad Genome Valley Sterile Unit' as any,
        subLocation: 'Sterile Block B - Cleanroom Grade A',
        costINR: 6500000,
        accumulatedDepINR: 1300000,
        nbvINR: 5200000,
        capitalisationDate: '2022-08-10',
        usefulLifeYears: 15,
        schIILifeYears: 15,
        verificationStatus: 'Verified',
        lastVerifiedDate: '2024-10-15',
        riskLevel: 'Clean',
        custodian: 'Dr. Venkat Rao (Sterile Operations)',
        department: 'Sterile Formulations',
        serialNumber: 'TELSTAR-LYO-2022-901',
        qrCode: 'QR-AST-HYD-LYO-0012',
        poNumber: 'PO-2022-HYD-0419',
        grnNumber: 'GRN-2022-08-0112',
        invoiceNumber: 'INV-TEL-2022-1082',
        vendor: 'Telstar Technologies India Pvt. Ltd.',
        description: 'cGMP automated lyophilization chamber for injectable oncology vials.',
        gstPaidINR: 1170000,
        itcClaimed: true,
        components: [
          {
            id: 'CMP-LYO-1',
            name: 'Stainless 316L Vacuum Chamber & Shelves',
            costINR: 4200000,
            usefulLifeYears: 15,
            depreciationMethod: 'SLM',
            accumulatedDepINR: 840000,
            nbvINR: 3360000,
            notes: 'High-grade pharmaceutical 316L chamber'
          },
          {
            id: 'CMP-LYO-2',
            name: 'Cascade Refrigeration Compressor Skid',
            costINR: 1500000,
            usefulLifeYears: 8,
            depreciationMethod: 'SLM',
            accumulatedDepINR: 375000,
            nbvINR: 1125000,
            notes: 'High-stress dual-stage cryogenic compressors'
          },
          {
            id: 'CMP-LYO-3',
            name: 'SCADA 21 CFR Part 11 Compliance Controller',
            costINR: 800000,
            usefulLifeYears: 5,
            depreciationMethod: 'SLM',
            accumulatedDepINR: 160000,
            nbvINR: 640000,
            notes: 'Audit trail compliant PLC system'
          }
        ],
        historyEvents: [],
        anomalies: [],
        status: 'Active'
      },
      {
        id: 'AST-VIZ-REA-0044',
        name: 'Hastelloy C-276 Chemical Reaction Vessel 5000L',
        category: 'Plant & Machinery',
        plant: 'Vizag Bulk Drugs & API Facility' as any,
        subLocation: 'Reactor Hall 3 - Acid Synthesis Bay',
        costINR: 3800000,
        accumulatedDepINR: 760000,
        nbvINR: 3040000,
        capitalisationDate: '2023-01-20',
        usefulLifeYears: 15,
        schIILifeYears: 15,
        verificationStatus: 'Verified',
        lastVerifiedDate: '2024-09-12',
        riskLevel: 'Clean',
        custodian: 'K. S. Narayanan (API Lead)',
        department: 'API Synthesis',
        serialNumber: 'GLATT-HAST-5000-881',
        qrCode: 'QR-AST-VIZ-REA-0044',
        poNumber: 'PO-2022-VIZ-9901',
        grnNumber: 'GRN-2023-01-0021',
        invoiceNumber: 'INV-GLT-2023-4512',
        vendor: 'Glatt Systems India Pvt. Ltd.',
        description: 'Corrosion-resistant high-pressure jacketed reactor for acidic intermediate synthesis.',
        gstPaidINR: 684000,
        itcClaimed: true,
        components: [],
        historyEvents: [],
        anomalies: [],
        status: 'Active'
      }
    ],
    capexQueue: [
      {
        id: 'CPX-BIO-001',
        poNumber: 'PO-2024-HYD-9912',
        invoiceNumber: 'INV-WAT-2024-5512',
        vendor: 'Waters India Pvt. Ltd.',
        description: 'ACQUITY Ultra Performance LC (UPLC) Quadrupole Mass Spectrometer System',
        amountINR: 4200000,
        invoiceDate: '2024-11-28',
        plant: 'Hyderabad Genome Valley Sterile Unit' as any,
        department: 'QC & Analytical Chemistry',
        grnStatus: 'Complete',
        technicalInspection: 'Passed',
        suggestedCategory: 'Plant & Machinery',
        status: 'Pending AI Review'
      }
    ],
    risks: [
      {
        id: 'RSK-BIO-001',
        title: 'QC HPLC System Moved Between Cleanrooms Without Gate Pass',
        riskType: 'Wrong Location',
        severity: 'Medium',
        assetId: 'AST-HYD-HPLC-0008',
        assetName: 'Waters Alliance HPLC System',
        location: 'Hyderabad Genome Valley Sterile Unit' as any,
        financialExposureINR: 1850000,
        explanation: 'Asset registered in QC Stability Lab 2 was scanned in Formulations Analytical Bay without physical transfer challan.',
        evidence: 'RFID scan log location mismatch with Master Register.',
        statutoryReference: 'CARO 2020 Clause 3(i)(a)(A)',
        recommendedAction: 'Execute internal transfer memo and update location records.',
        owner: 'Quality Assurance Lead',
        status: 'Investigating',
        createdDate: '2024-11-15',
        updatedDate: '2024-11-20',
        auditTrail: []
      }
    ],
    scanLogs: []
  },
  'comp-sunvolt': {
    company: DEFAULT_COMPANIES[2],
    assets: [
      {
        id: 'AST-KUT-TRF-001',
        name: '33kV / 220kV Step-Up Power Transformer 100MVA',
        category: 'Plant & Machinery',
        plant: 'Kutch 500MW Solar Park' as any,
        subLocation: 'Main Inverter Pooling Substation Yard',
        costINR: 12500000,
        accumulatedDepINR: 1875000,
        nbvINR: 10625000,
        capitalisationDate: '2021-06-18',
        usefulLifeYears: 25,
        schIILifeYears: 25,
        verificationStatus: 'Verified',
        lastVerifiedDate: '2024-11-05',
        riskLevel: 'Clean',
        custodian: 'Pravin Solanki (Grid Engineer)',
        department: 'Substation & Grid Operations',
        serialNumber: 'ABB-TRF-100MVA-99124',
        qrCode: 'QR-AST-KUT-TRF-001',
        poNumber: 'PO-2021-KUT-0014',
        grnNumber: 'GRN-2021-06-0045',
        invoiceNumber: 'INV-ABB-2021-9988',
        vendor: 'Hitachi Energy India Ltd.',
        description: 'Oil-immersed grid step-up transformer connected to GETCO 220kV transmission line.',
        gstPaidINR: 2250000,
        itcClaimed: true,
        components: [
          {
            id: 'CMP-TRF-1',
            name: 'Core Windings & Transformer Tank',
            costINR: 9000000,
            usefulLifeYears: 25,
            depreciationMethod: 'SLM',
            accumulatedDepINR: 1350000,
            nbvINR: 7650000,
            notes: 'Heavy core windings & oil containment tank'
          },
          {
            id: 'CMP-TRF-2',
            name: 'On-Load Tap Changer (OLTC) & Bushings',
            costINR: 3500000,
            usefulLifeYears: 12,
            depreciationMethod: 'SLM',
            accumulatedDepINR: 875000,
            nbvINR: 2625000,
            notes: 'Dynamic mechanical switching mechanism subject to electrical arcing'
          }
        ],
        historyEvents: [],
        anomalies: [],
        status: 'Active'
      }
    ],
    capexQueue: [],
    risks: [],
    scanLogs: []
  }
};
