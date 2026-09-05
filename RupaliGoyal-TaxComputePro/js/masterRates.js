/**
 * TaxCompute Pro - Master Statutory Rates & Tax Slabs
 * Calibrated for FY 2025-26 & FY 2026-27 (AY 2026-27 & AY 2027-28)
 * Incorporating Finance (No. 2) Act 2024 amendments
 */

export const MASTER_RATES = {
  CURRENT_FY: '2025-26',
  CURRENT_AY: '2026-27',
  
  // Standard Deductions
  STANDARD_DEDUCTION: {
    NEW_REGIME: 75000, // Budget 2024 enhanced
    OLD_REGIME: 50000,
  },

  // Family Pension Standard Deduction u/s 57(iia)
  FAMILY_PENSION_DEDUCTION: {
    NEW_REGIME_MAX: 25000, // Budget 2024 enhanced
    OLD_REGIME_MAX: 15000,
    PERCENTAGE: 1 / 3,
  },

  // Cess
  HEALTH_AND_EDUCATION_CESS: 0.04, // 4%

  // Section 87A Rebate Thresholds
  REBATE_87A: {
    NEW_REGIME: {
      THRESHOLD: 700000,
      MAX_REBATE: 25000,
      // Marginal relief applies between 7,00,000 and 7,27,777
    },
    OLD_REGIME: {
      THRESHOLD: 500000,
      MAX_REBATE: 12500,
    }
  },

  // Capital Gains Tax Rates (Post Budget 2024)
  CAPITAL_GAINS: {
    STCG_111A_RATE: 0.20, // 20% (increased from 15% w.e.f. 23 July 2024)
    LTCG_112A_RATE: 0.125, // 12.5% (increased from 10% w.e.f. 23 July 2024)
    LTCG_112A_EXEMPTION: 125000, // ₹1,25,000 (increased from ₹1,00,000)
    LTCG_112_RATE: 0.125, // 12.5% without indexation (or 20% with grandfathering where applicable)
    STCG_NORMAL_RATE: 'SLAB',
  },

  // Special Rate Incomes
  SPECIAL_RATES: {
    LOTTERY_115BB: 0.30,      // 30%
    ONLINE_GAMING_115BBJ: 0.30, // 30%
    VDA_CRYPTO_115BBH: 0.30,   // 30% flat (no deduction except cost of acquisition, no loss set-off)
  },

  // Slabs for Individual / HUF / AOP / BOI / AJP
  SLABS: {
    // New Tax Regime u/s 115BAC(1A) for FY 2025-26 & FY 2026-27
    NEW_REGIME: [
      { min: 0, max: 300000, rate: 0.00, label: 'Up to ₹3,00,000' },
      { min: 300000, max: 700000, rate: 0.05, label: '₹3,00,001 to ₹7,00,000' },
      { min: 700000, max: 1000000, rate: 0.10, label: '₹7,00,001 to ₹10,00,000' },
      { min: 1000000, max: 1200000, rate: 0.15, label: '₹10,00,001 to ₹12,00,000' },
      { min: 1200000, max: 1500000, rate: 0.20, label: '₹12,00,001 to ₹15,00,000' },
      { min: 1500000, max: Infinity, rate: 0.30, label: 'Above ₹15,00,000' },
    ],

    // Old Tax Regime - Individual (Below 60 Years) & HUF
    OLD_REGIME_GENERAL: [
      { min: 0, max: 250000, rate: 0.00, label: 'Up to ₹2,50,000' },
      { min: 250000, max: 500000, rate: 0.05, label: '₹2,50,001 to ₹5,00,000' },
      { min: 500000, max: 1000000, rate: 0.20, label: '₹5,00,001 to ₹10,00,000' },
      { min: 1000000, max: Infinity, rate: 0.30, label: 'Above ₹10,00,000' },
    ],

    // Old Tax Regime - Senior Citizen (60 to 79 Years)
    OLD_REGIME_SENIOR: [
      { min: 0, max: 300000, rate: 0.00, label: 'Up to ₹3,00,000' },
      { min: 300000, max: 500000, rate: 0.05, label: '₹3,00,001 to ₹5,00,000' },
      { min: 500000, max: 1000000, rate: 0.20, label: '₹5,00,001 to ₹10,00,000' },
      { min: 1000000, max: Infinity, rate: 0.30, label: 'Above ₹10,00,000' },
    ],

    // Old Tax Regime - Super Senior Citizen (80 Years and above)
    OLD_REGIME_SUPER_SENIOR: [
      { min: 0, max: 500000, rate: 0.00, label: 'Up to ₹5,00,000' },
      { min: 500000, max: 1000000, rate: 0.20, label: '₹5,00,001 to ₹10,00,000' },
      { min: 1000000, max: Infinity, rate: 0.30, label: 'Above ₹10,00,000' },
    ],

    // Cooperative Society Regular Slabs (Old Regime)
    COOPERATIVE_SOCIETY_REGULAR: [
      { min: 0, max: 10000, rate: 0.10, label: 'Up to ₹10,000' },
      { min: 10000, max: 20000, rate: 0.20, label: '₹10,001 to ₹20,000' },
      { min: 20000, max: Infinity, rate: 0.30, label: 'Above ₹20,000' },
    ]
  },

  // Surcharge Rates for Individuals & HUFs
  SURCHARGE_INDIVIDUAL: {
    OLD_REGIME: [
      { threshold: 50000000, rate: 0.37, label: '> ₹5 Crore (37%)' },
      { threshold: 20000000, rate: 0.25, label: '₹2 Cr - ₹5 Cr (25%)' },
      { threshold: 10000000, rate: 0.15, label: '₹1 Cr - ₹2 Cr (15%)' },
      { threshold: 5000000, rate: 0.10, label: '₹50 Lakh - ₹1 Cr (10%)' },
    ],
    // Under New Regime u/s 115BAC, max surcharge is capped at 25% (37% rate eliminated)
    NEW_REGIME: [
      { threshold: 20000000, rate: 0.25, label: '> ₹2 Crore (25%)' },
      { threshold: 10000000, rate: 0.15, label: '₹1 Cr - ₹2 Cr (15%)' },
      { threshold: 5000000, rate: 0.10, label: '₹50 Lakh - ₹1 Cr (10%)' },
    ]
  },

  // Corporate & Entity Tax Rates
  ENTITY_RATES: {
    PARTNERSHIP_FIRM_LLP: {
      name: 'Partnership Firm / LLP',
      baseRate: 0.30,
      surchargeThreshold: 10000000, // ₹1 Crore
      surchargeRate: 0.12,         // 12%
    },
    DOMESTIC_COMPANY_115BAA: {
      name: 'Domestic Co u/s 115BAA (22% Concessional Rate)',
      baseRate: 0.22,
      surchargeRate: 0.10,         // Flat 10% regardless of income
      effectiveRate: 0.25168,      // 22% + 10% SC + 4% Cess = 25.168%
      matApplicable: false,
    },
    DOMESTIC_COMPANY_115BAB: {
      name: 'Domestic Co u/s 115BAB (15% New Manufacturing)',
      baseRate: 0.15,
      surchargeRate: 0.10,
      effectiveRate: 0.1716,       // 15% + 10% SC + 4% Cess = 17.16%
      matApplicable: false,
    },
    DOMESTIC_COMPANY_REGULAR_25: {
      name: 'Regular Domestic Co (Turnover ≤ ₹400 Cr)',
      baseRate: 0.25,
      surcharge: [
        { threshold: 100000000, rate: 0.12 }, // > 10 Cr = 12%
        { threshold: 10000000, rate: 0.07 },  // 1 Cr to 10 Cr = 7%
      ],
      matApplicable: true,
      matRate: 0.15,
    },
    DOMESTIC_COMPANY_REGULAR_30: {
      name: 'Regular Domestic Co (Turnover > ₹400 Cr)',
      baseRate: 0.30,
      surcharge: [
        { threshold: 100000000, rate: 0.12 },
        { threshold: 10000000, rate: 0.07 },
      ],
      matApplicable: true,
      matRate: 0.15,
    },
    FOREIGN_COMPANY: {
      name: 'Foreign Company',
      baseRate: 0.35, // Budget 2024 reduced from 40% to 35%
      surcharge: [
        { threshold: 100000000, rate: 0.05 }, // > 10 Cr = 5%
        { threshold: 10000000, rate: 0.02 },  // 1 Cr to 10 Cr = 2%
      ]
    },
    COOPERATIVE_115BAD: {
      name: 'Cooperative Society u/s 115BAD',
      baseRate: 0.22,
      surchargeRate: 0.10,
      effectiveRate: 0.25168,
      amtApplicable: false,
    },
    COOPERATIVE_115BAE: {
      name: 'New Manufacturing Cooperative u/s 115BAE',
      baseRate: 0.15,
      surchargeRate: 0.10,
      effectiveRate: 0.1716,
      amtApplicable: false,
    }
  },

  // Presumptive Taxation Schemes
  PRESUMPTIVE_SCHEMES: {
    SEC_44AD: {
      name: 'Section 44AD (Eligible Small Business)',
      maxTurnover: 30000000, // ₹3 Crore if digital turnover >= 95% (otherwise ₹2 Cr)
      rateDigital: 0.06,      // 6% of digital receipts
      rateCash: 0.08,         // 8% of cash receipts
    },
    SEC_44ADA: {
      name: 'Section 44ADA (Specified Professionals)',
      maxReceipts: 7500000,  // ₹75 Lakhs if cash receipts <= 5% (otherwise ₹50 Lakhs)
      deemedProfitRate: 0.50, // Minimum 50%
      professions: ['Legal', 'Medical', 'Engineering', 'Architectural', 'Accountancy', 'Technical Consultancy', 'Interior Decoration', 'Authorized Representative', 'Film Artist', 'IT Professionals']
    },
    SEC_44AE: {
      name: 'Section 44AE (Goods Carriages)',
      maxVehicles: 10,
      heavyVehicleRatePerTonPerMonth: 1000, // ₹1000 per gross vehicle weight ton per month
      otherVehicleRatePerMonth: 7500,       // ₹7500 per month
    }
  },

  // Section 32 Income Tax Block Depreciation Rates
  DEPRECIATION_BLOCKS: [
    { id: 'bld_res', block: 'Buildings', asset: 'Residential Buildings (other than hotels/boarding)', rate: 0.05 },
    { id: 'bld_comm', block: 'Buildings', asset: 'Commercial, Industrial & Hotel Buildings', rate: 0.10 },
    { id: 'bld_temp', block: 'Buildings', asset: 'Temporary wooden structures & water treatment structures', rate: 0.40 },
    { id: 'pm_gen', block: 'Plant & Machinery', asset: 'General Plant & Machinery (Default)', rate: 0.15 },
    { id: 'pm_motor_comm', block: 'Plant & Machinery', asset: 'Motor cars/taxis used in business of hiring', rate: 0.30 },
    { id: 'pm_motor_gen', block: 'Plant & Machinery', asset: 'Motor cars other than those used in business of hiring', rate: 0.15 },
    { id: 'pm_comp', block: 'Plant & Machinery', asset: 'Computers, Laptops & Computer Software', rate: 0.40 },
    { id: 'pm_aero', block: 'Plant & Machinery', asset: 'Aeroplanes, Aero-engines', rate: 0.40 },
    { id: 'pm_wind', block: 'Plant & Machinery', asset: 'Windmills installed on or after 01.04.2014', rate: 0.40 },
    { id: 'pm_pollution', block: 'Plant & Machinery', asset: 'Pollution control equipment & solid waste treatment', rate: 0.40 },
    { id: 'ff_gen', block: 'Furniture & Fittings', asset: 'Furniture & Fittings including electrical fittings', rate: 0.10 },
    { id: 'ia_gen', block: 'Intangible Assets', asset: 'Patents, Copyrights, Trademarks, Licenses, Franchises', rate: 0.25 },
  ],

  // Statutory TDS & TCS Master Rates
  TDS_TCS_MASTER: [
    { section: '192', nature: 'Salary', threshold: 'Basic Exemption Limit', rate: 'Average Income Tax Slab Rate', remarks: 'Deducted month-on-month by employer' },
    { section: '194A', nature: 'Interest other than on securities (Banks/Post Office)', threshold: '₹40,000 (₹50,000 for Seniors) / ₹5,000 for others', rate: '10%', remarks: '20% if PAN not furnished u/s 206AA' },
    { section: '194C', nature: 'Payment to Contractors / Sub-contractors', threshold: '₹30,000 (Single) / ₹1,00,000 (Aggregate)', rate: '1% (Ind/HUF) / 2% (Others)', remarks: 'Exempt for transporters filing declaration u/s 194C(6)' },
    { section: '194DA', nature: 'Payment in respect of Life Insurance Policy', threshold: '₹1,00,000', rate: '5% (on net income component)', remarks: 'Applicable when policy is not exempt u/s 10(10D)' },
    { section: '194H', nature: 'Commission or Brokerage', threshold: '₹15,000', rate: '2% / 5%', remarks: 'Budget 2024 reduced rate to 2% w.e.f 1 Oct 2024' },
    { section: '194I(a)', nature: 'Rent on Plant & Machinery', threshold: '₹2,40,000 p.a.', rate: '2%', remarks: 'Applicable to persons liable for tax audit' },
    { section: '194I(b)', nature: 'Rent on Land, Building & Furniture', threshold: '₹2,40,000 p.a.', rate: '10%', remarks: 'Applicable to persons liable for tax audit' },
    { section: '194IB', nature: 'Rent payment by Individual/HUF (not liable for tax audit)', threshold: '₹50,00,000 in FY / ₹50,000 per month', rate: '2% / 5%', remarks: 'Budget 2024 reduced rate to 2% w.e.f 1 Oct 2024' },
    { section: '194IA', nature: 'Transfer of Immovable Property (other than agricultural land)', threshold: '₹50,00,000 (Consideration or SDV)', rate: '1%', remarks: 'Aggregate of all buyers/sellers threshold consideration' },
    { section: '194J', nature: 'Fees for Professional or Technical Services', threshold: '₹30,000', rate: '2% (FTS / Call Centre) / 10% (Professional / Royalty)', remarks: 'Distinct sub-limits for royalty and technical services' },
    { section: '194M', nature: 'Payment to Contractors/Commission/Professionals by Ind/HUF', threshold: '₹50,00,000 in a year', rate: '2% / 5%', remarks: 'Reduced to 2% w.e.f. 1 Oct 2024' },
    { section: '194Q', nature: 'Purchase of Goods by Buyer having turnover > ₹10 Cr', threshold: '₹50,00,000 in FY', rate: '0.1%', remarks: 'Applicable on amount exceeding ₹50 Lakhs' },
    { section: '194S', nature: 'Transfer of Virtual Digital Assets (Crypto/NFT)', threshold: '₹50,00,000 (Specified Person) / ₹10,000 (Others)', rate: '1%', remarks: 'Deducted on gross sale consideration' },
    { section: '206C(1)', nature: 'TCS on Sale of Timber, Scrap, Minerals, Alcoholic Liquor', threshold: 'Nil', rate: '1% to 5%', remarks: 'Alcoholic liquor (1%), Scrap (1%), Minerals (2%)' },
    { section: '206C(1G)', nature: 'TCS on Foreign Remittance under LRS / Overseas Tour Package', threshold: '₹7,00,000 (LRS Education/Medical: 5%, Others: 20%)', rate: '5% / 20%', remarks: 'Tour packages: 5% up to ₹7L, 20% thereafter' },
    { section: '206C(1H)', nature: 'TCS on Sale of Goods exceeding ₹50 Lakhs', threshold: '₹50,00,000 in FY', rate: '0.1%', remarks: 'Subject to non-applicability if 194Q deducted' },
  ]
};
