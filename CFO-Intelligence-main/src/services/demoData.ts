import { ClientProfile, FinancialModel, MonthlyFinancialRecord, RedFlagAlert, WinHighlight, OpportunityInsight, CfoCommentary } from '../types';

export interface DemoClientBundle {
  client: ClientProfile;
  model: FinancialModel;
  wins: WinHighlight[];
  concerns: string[];
  redFlags: RedFlagAlert[];
  opportunities: OpportunityInsight[];
  cfoCommentary: CfoCommentary;
}

// 1. AeroHealth Physicians Group (Medical Practice)
export const DEMO_MEDICAL: DemoClientBundle = {
  client: {
    id: 'demo_medical_001',
    name: 'AeroHealth Physicians Group',
    legalEntityName: 'AeroHealth Clinical Associates LLC',
    industry: 'medical',
    industryName: 'Medical & Healthcare Practices',
    businessDescription: 'Multi-specialty outpatient medical group with 7 clinic locations, 14 board-certified physicians, and an ambulatory diagnostic wing.',
    entityType: 'LLC',
    country: 'United States',
    currency: 'USD',
    currencySymbol: '$',
    fiscalYearEnd: 'December 31',
    reportingPeriod: 'YTD Aug 2026',
    businessSize: 'Mid-Market ($5M - $25M)',
    headcount: 28,
    contactEmail: 'finance@aerohealth-demo.com',
    contactPhone: '+1 (555) 382-9100',
    taxId: '84-9182736',
    bankAccountMasked: '•••• 4819 (JPMorgan Chase)',
    isDemo: true,
    privacyMode: 'strict',
    lastUpdated: '2026-08-25T04:00:00Z',
  },
  wins: [
    {
      id: 'w1',
      title: 'Net Patient Revenue Surge',
      metric: 'Revenue +14.2% YoY',
      change: '+$94,000 / mo',
      businessImpact: 'Expansion of outpatient ultrasound imaging and cardiology diagnostics accelerated top-line collections.',
      category: 'revenue',
    },
    {
      id: 'w2',
      title: 'AR Days Compression',
      metric: 'DSO dropped from 46 to 34 days',
      change: '-12 days',
      businessImpact: 'Automated payer claim scrubbing reduced initial denial rate by 22%, expediting cash receipts.',
      category: 'efficiency',
    },
    {
      id: 'w3',
      title: 'Operating Cash Flow Expansion',
      metric: 'Free Cash Flow Margin 18.4%',
      change: '+$142,000 YTD',
      businessImpact: 'Robust cash generation built up a 14.8-month liquid operating buffer.',
      category: 'cash',
    }
  ],
  concerns: [
    'Rising cost of specialized clinical nursing temp staffing during peak flu and procedural months.',
    'Commercial payer contract renegotiations pending for Q4 with Blue Cross Blue Shield.',
    'Ultrasound diagnostic unit maintenance contract fee increasing 8% starting September 2026.',
  ],
  redFlags: [
    {
      id: 'rf1',
      severity: 'medium',
      title: 'Provider Productivity Variance in Clinic #4',
      metric: 'Rev / Provider',
      currentValue: '$72,000 / mo',
      threshold: '$90,000 / mo',
      impact: 'Clinic #4 scheduling utilization is 20% below the group average due to front-desk booking lag.',
      recommendation: 'Reassign centralized scheduling templates to eliminate appointment gap times.',
      category: 'expenses',
    },
    {
      id: 'rf2',
      severity: 'low',
      title: 'Medical Supply Price Index Drift',
      metric: 'Clinical Supplies %',
      currentValue: '9.8% of Rev',
      threshold: '8.5% of Rev',
      impact: 'Direct consumable supplies increased $11,500 over budget across Q2.',
      recommendation: 'Enforce consolidated group purchasing organization (GPO) vendor contract pricing.',
      category: 'margins',
    }
  ],
  opportunities: [
    {
      id: 'op1',
      title: 'Transition High-Volume Payers to Electronic Remittance',
      potentialImpact: '+$45,000 Working Capital / -4 DSO Days',
      effort: 'Low',
      timeframe: 'Immediate (<30d)',
      actionPlan: 'Enable instant EFT auto-reconciliation for regional Medicaid and secondary Medicare plans.',
    },
    {
      id: 'op2',
      title: 'In-House Physical Therapy Ancillary Addition',
      potentialImpact: '+$380,000 Annual EBITDA (+4.5%)',
      effort: 'Medium',
      timeframe: 'Quarterly (90d)',
      actionPlan: 'Utilize 1,800 sq ft unleased suite in North Clinic for dedicated musculoskeletal rehab therapy.',
    }
  ],
  cfoCommentary: {
    headlineSummary: 'Strong clinical momentum with revenue reaching $742k/mo and healthy 21.6% EBITDA margin.',
    whatHappened: 'AeroHealth recorded $5.68M in net collections through August 2026, outperforming budget by 6.8%. Operating expenses remained disciplined, yielding $1.23M in YTD EBITDA.',
    whyItHappened: 'Patient encounter volume rose 9% following the onboarding of two orthopedic mid-level providers in March, while automated billing improvements cut AR days down to 34 days.',
    whyItMatters: 'Healthy operating margins have raised total liquidity to $1.84M in unencumbered cash, establishing an unshakeable 14.8-month runway buffer and preparing the practice for Q4 facility expansions.',
    recommendedActions: [
      'Lock in master GPO supply contracts to arrest the 1.3% drift in disposable medical supplies.',
      'Deploy standardized provider scheduling templates across Clinics #4 and #6 to lift underperforming provider revenue to the $95k benchmark.',
      'Maintain quarterly partner draw discipline at 65% of net profit to reserve capital for North Clinic physical therapy suite buildout.',
    ],
    strategicSummary: 'Practice is in optimal financial health with low leverage, accelerating collection velocity, and strong unit economics.',
    confidenceScore: 96,
    isAiGenerated: true,
    lastEditedBy: 'Jasleen Daswal, CPA / Lead FP&A Consultant',
    lastEditedAt: '2026-08-25T04:15:00Z',
  },
  model: {
    client: {} as ClientProfile, // assigned below
    periods: [
      { periodKey: '2026-01', label: 'Jan 2026', isActual: true },
      { periodKey: '2026-02', label: 'Feb 2026', isActual: true },
      { periodKey: '2026-03', label: 'Mar 2026', isActual: true },
      { periodKey: '2026-04', label: 'Apr 2026', isActual: true },
      { periodKey: '2026-05', label: 'May 2026', isActual: true },
      { periodKey: '2026-06', label: 'Jun 2026', isActual: true },
      { periodKey: '2026-07', label: 'Jul 2026', isActual: true },
      { periodKey: '2026-08', label: 'Aug 2026', isActual: true },
      { periodKey: '2026-09', label: 'Sep 2026', isActual: false, isForecast: true },
      { periodKey: '2026-10', label: 'Oct 2026', isActual: false, isForecast: true },
      { periodKey: '2026-11', label: 'Nov 2026', isActual: false, isForecast: true },
      { periodKey: '2026-12', label: 'Dec 2026', isActual: false, isForecast: true },
    ],
    historicalMonthly: [
      {
        periodKey: '2026-01', periodLabel: 'Jan 2026',
        revenue: 660000, cogs: 132000, grossProfit: 528000, grossMarginPercent: 80.0,
        salariesAndWages: 250000, salesAndMarketing: 18000, rentAndFacilities: 48000, generalAndAdmin: 52000, depreciationAndAmort: 14000, otherOpex: 12000, totalOpex: 394000,
        ebitda: 148000, ebitdaMarginPercent: 22.4, interestExpense: 3500, taxExpense: 22000, netIncome: 108500, netMarginPercent: 16.4,
        cashAndEquivalents: 1420000, accountsReceivable: 880000, inventory: 45000, otherCurrentAssets: 35000, totalCurrentAssets: 2380000, fixedAssets: 1650000, totalAssets: 4030000,
        accountsPayable: 195000, shortTermDebt: 45000, accruedLiabilities: 85000, totalCurrentLiabilities: 325000, longTermDebt: 720000, totalLiabilities: 1045000, totalEquity: 2985000,
        operatingCashFlow: 125000, investingCashFlow: -20000, financingCashFlow: -35000, netCashFlow: 70000, endingCash: 1490000,
        workingCapital: 2055000, currentRatio: 7.32, quickRatio: 7.08, dso: 40, dpo: 44, dio: 31, ccc: 27,
      },
      {
        periodKey: '2026-02', periodLabel: 'Feb 2026',
        revenue: 675000, cogs: 135000, grossProfit: 540000, grossMarginPercent: 80.0,
        salariesAndWages: 255000, salesAndMarketing: 19000, rentAndFacilities: 48000, generalAndAdmin: 53000, depreciationAndAmort: 14000, otherOpex: 13000, totalOpex: 402000,
        ebitda: 152000, ebitdaMarginPercent: 22.5, interestExpense: 3400, taxExpense: 23000, netIncome: 111600, netMarginPercent: 16.5,
        cashAndEquivalents: 1490000, accountsReceivable: 865000, inventory: 46000, otherCurrentAssets: 35000, totalCurrentAssets: 2436000, fixedAssets: 1640000, totalAssets: 4076000,
        accountsPayable: 190000, shortTermDebt: 45000, accruedLiabilities: 88000, totalCurrentLiabilities: 323000, longTermDebt: 710000, totalLiabilities: 1033000, totalEquity: 3043000,
        operatingCashFlow: 132000, investingCashFlow: -15000, financingCashFlow: -35000, netCashFlow: 82000, endingCash: 1572000,
        workingCapital: 2113000, currentRatio: 7.54, quickRatio: 7.30, dso: 38, dpo: 42, dio: 31, ccc: 27,
      },
      {
        periodKey: '2026-03', periodLabel: 'Mar 2026',
        revenue: 710000, cogs: 142000, grossProfit: 568000, grossMarginPercent: 80.0,
        salariesAndWages: 268000, salesAndMarketing: 21000, rentAndFacilities: 48000, generalAndAdmin: 54000, depreciationAndAmort: 14000, otherOpex: 14000, totalOpex: 419000,
        ebitda: 163000, ebitdaMarginPercent: 23.0, interestExpense: 3300, taxExpense: 25000, netIncome: 120700, netMarginPercent: 17.0,
        cashAndEquivalents: 1572000, accountsReceivable: 840000, inventory: 48000, otherCurrentAssets: 36000, totalCurrentAssets: 2496000, fixedAssets: 1630000, totalAssets: 4126000,
        accountsPayable: 185000, shortTermDebt: 45000, accruedLiabilities: 90000, totalCurrentLiabilities: 320000, longTermDebt: 700000, totalLiabilities: 1020000, totalEquity: 3106000,
        operatingCashFlow: 145000, investingCashFlow: -22000, financingCashFlow: -35000, netCashFlow: 88000, endingCash: 1660000,
        workingCapital: 2176000, currentRatio: 7.80, quickRatio: 7.55, dso: 36, dpo: 39, dio: 31, ccc: 28,
      },
      {
        periodKey: '2026-04', periodLabel: 'Apr 2026',
        revenue: 705000, cogs: 141000, grossProfit: 564000, grossMarginPercent: 80.0,
        salariesAndWages: 270000, salesAndMarketing: 20000, rentAndFacilities: 48000, generalAndAdmin: 55000, depreciationAndAmort: 14000, otherOpex: 14000, totalOpex: 421000,
        ebitda: 157000, ebitdaMarginPercent: 22.3, interestExpense: 3200, taxExpense: 24000, netIncome: 115800, netMarginPercent: 16.4,
        cashAndEquivalents: 1660000, accountsReceivable: 830000, inventory: 49000, otherCurrentAssets: 36000, totalCurrentAssets: 2575000, fixedAssets: 1620000, totalAssets: 4195000,
        accountsPayable: 188000, shortTermDebt: 45000, accruedLiabilities: 91000, totalCurrentLiabilities: 324000, longTermDebt: 690000, totalLiabilities: 1014000, totalEquity: 3181000,
        operatingCashFlow: 138000, investingCashFlow: -18000, financingCashFlow: -35000, netCashFlow: 85000, endingCash: 1745000,
        workingCapital: 2251000, currentRatio: 7.95, quickRatio: 7.69, dso: 35, dpo: 40, dio: 31, ccc: 26,
      },
      {
        periodKey: '2026-05', periodLabel: 'May 2026',
        revenue: 725000, cogs: 145000, grossProfit: 580000, grossMarginPercent: 80.0,
        salariesAndWages: 275000, salesAndMarketing: 21000, rentAndFacilities: 48000, generalAndAdmin: 56000, depreciationAndAmort: 14000, otherOpex: 15000, totalOpex: 429000,
        ebitda: 165000, ebitdaMarginPercent: 22.8, interestExpense: 3100, taxExpense: 26000, netIncome: 121900, netMarginPercent: 16.8,
        cashAndEquivalents: 1745000, accountsReceivable: 820000, inventory: 50000, otherCurrentAssets: 37000, totalCurrentAssets: 2652000, fixedAssets: 1610000, totalAssets: 4262000,
        accountsPayable: 192000, shortTermDebt: 45000, accruedLiabilities: 93000, totalCurrentLiabilities: 330000, longTermDebt: 680000, totalLiabilities: 1010000, totalEquity: 3252000,
        operatingCashFlow: 148000, investingCashFlow: -25000, financingCashFlow: -35000, netCashFlow: 88000, endingCash: 1833000,
        workingCapital: 2322000, currentRatio: 8.04, quickRatio: 7.78, dso: 34, dpo: 40, dio: 31, ccc: 25,
      },
      {
        periodKey: '2026-06', periodLabel: 'Jun 2026',
        revenue: 735000, cogs: 147000, grossProfit: 588000, grossMarginPercent: 80.0,
        salariesAndWages: 280000, salesAndMarketing: 22000, rentAndFacilities: 48000, generalAndAdmin: 57000, depreciationAndAmort: 14000, otherOpex: 15000, totalOpex: 436000,
        ebitda: 166000, ebitdaMarginPercent: 22.6, interestExpense: 3000, taxExpense: 26000, netIncome: 123000, netMarginPercent: 16.7,
        cashAndEquivalents: 1833000, accountsReceivable: 815000, inventory: 51000, otherCurrentAssets: 38000, totalCurrentAssets: 2737000, fixedAssets: 1600000, totalAssets: 4337000,
        accountsPayable: 195000, shortTermDebt: 45000, accruedLiabilities: 95000, totalCurrentLiabilities: 335000, longTermDebt: 670000, totalLiabilities: 1005000, totalEquity: 3332000,
        operatingCashFlow: 152000, investingCashFlow: -15000, financingCashFlow: -35000, netCashFlow: 102000, endingCash: 1935000,
        workingCapital: 2402000, currentRatio: 8.17, quickRatio: 7.91, dso: 33, dpo: 40, dio: 31, ccc: 24,
      },
      {
        periodKey: '2026-07', periodLabel: 'Jul 2026',
        revenue: 730000, cogs: 146000, grossProfit: 584000, grossMarginPercent: 80.0,
        salariesAndWages: 282000, salesAndMarketing: 21000, rentAndFacilities: 48000, generalAndAdmin: 57000, depreciationAndAmort: 14000, otherOpex: 16000, totalOpex: 438000,
        ebitda: 160000, ebitdaMarginPercent: 21.9, interestExpense: 2900, taxExpense: 25000, netIncome: 118100, netMarginPercent: 16.2,
        cashAndEquivalents: 1935000, accountsReceivable: 825000, inventory: 52000, otherCurrentAssets: 38000, totalCurrentAssets: 2850000, fixedAssets: 1590000, totalAssets: 4440000,
        accountsPayable: 190000, shortTermDebt: 45000, accruedLiabilities: 96000, totalCurrentLiabilities: 331000, longTermDebt: 660000, totalLiabilities: 991000, totalEquity: 3449000,
        operatingCashFlow: 146000, investingCashFlow: -20000, financingCashFlow: -35000, netCashFlow: 91000, endingCash: 2026000,
        workingCapital: 2519000, currentRatio: 8.61, quickRatio: 8.35, dso: 34, dpo: 39, dio: 32, ccc: 27,
      },
      {
        periodKey: '2026-08', periodLabel: 'Aug 2026',
        revenue: 742000, cogs: 148000, grossProfit: 594000, grossMarginPercent: 80.1,
        salariesAndWages: 285000, salesAndMarketing: 22000, rentAndFacilities: 48000, generalAndAdmin: 58000, depreciationAndAmort: 14000, otherOpex: 16000, totalOpex: 443000,
        ebitda: 165000, ebitdaMarginPercent: 22.2, interestExpense: 2800, taxExpense: 26000, netIncome: 122200, netMarginPercent: 16.5,
        cashAndEquivalents: 2026000, accountsReceivable: 830000, inventory: 53000, otherCurrentAssets: 39000, totalCurrentAssets: 2948000, fixedAssets: 1580000, totalAssets: 4528000,
        accountsPayable: 194000, shortTermDebt: 45000, accruedLiabilities: 98000, totalCurrentLiabilities: 337000, longTermDebt: 650000, totalLiabilities: 987000, totalEquity: 3541000,
        operatingCashFlow: 155000, investingCashFlow: -18000, financingCashFlow: -35000, netCashFlow: 102000, endingCash: 2128000,
        workingCapital: 2611000, currentRatio: 8.75, quickRatio: 8.48, dso: 34, dpo: 40, dio: 32, ccc: 26,
      },
    ],
    budgetMonthly: [],
    forecastMonthly: [],
    annualSummaries: [
      { year: 2024, revenue: 6850000, grossProfit: 5480000, ebitda: 1350000, netIncome: 920000, operatingCashFlow: 1100000, endingCash: 1250000 },
      { year: 2025, revenue: 7780000, grossProfit: 6224000, ebitda: 1680000, netIncome: 1190000, operatingCashFlow: 1450000, endingCash: 1420000 },
    ]
  }
};

DEMO_MEDICAL.model.client = DEMO_MEDICAL.client;

// 2. Artisan Culinary Group (Restaurant & Hospitality)
export const DEMO_RESTAURANT: DemoClientBundle = {
  client: {
    id: 'demo_restaurant_002',
    name: 'Artisan Culinary Group',
    legalEntityName: 'Artisan Hospitality & Dining S-Corp',
    industry: 'restaurant',
    industryName: 'Restaurant & Hospitality',
    businessDescription: 'Contemporary farm-to-table bistro collection with 3 dining venues, craft cocktail lounge, and private event catering operations.',
    entityType: 'S-Corp',
    country: 'United States',
    currency: 'USD',
    currencySymbol: '$',
    fiscalYearEnd: 'December 31',
    reportingPeriod: 'YTD Aug 2026',
    businessSize: 'Emerging ($1M - $5M)',
    headcount: 45,
    contactEmail: 'gm@artisanculinary-demo.com',
    contactPhone: '+1 (555) 749-2180',
    taxId: '22-8374619',
    bankAccountMasked: '•••• 9142 (Wells Fargo)',
    isDemo: true,
    privacyMode: 'strict',
    lastUpdated: '2026-08-25T04:00:00Z',
  },
  wins: [
    {
      id: 'rw1',
      title: 'Beverage & Bar Gross Margin Record',
      metric: 'Bar Margin 81.4%',
      change: '+3.2% vs budget',
      businessImpact: 'Premium seasonal craft cocktail pairings boosted high-margin bar sales by $28,000/mo.',
      category: 'margin',
    },
    {
      id: 'rw2',
      title: 'Prime Cost Stabilized',
      metric: 'Prime Cost 58.6%',
      change: '-2.4% MoM',
      businessImpact: 'Dynamic kitchen prep scheduling and meat butchery yield optimizations lowered combined food & labor costs under the 60% threshold.',
      category: 'efficiency',
    }
  ],
  concerns: [
    'Dairy and specialty organic produce supplier prices increased 6.4% in July due to regional heat waves.',
    'Weekend dinner reservation no-show rate rose slightly to 7.8% during late August.',
  ],
  redFlags: [
    {
      id: 'rrf1',
      severity: 'high',
      title: 'Midweek Lunch Labor Inefficiency in Downtown Venue',
      metric: 'Lunch Labor %',
      currentValue: '38.2% of Lunch Rev',
      threshold: '31.0%',
      impact: 'Downtown venue carries excess back-of-house line cooks during Tuesday-Thursday lunch shifts.',
      recommendation: 'Transition to flex-shift cross-trained kitchen prep schedules to save $4,200/month.',
      category: 'expenses',
    }
  ],
  opportunities: [
    {
      id: 'rop1',
      title: 'Launch Pre-Paid Prix-Fixe Holiday Tasting Menu',
      potentialImpact: '+$95,000 Q4 Advance Cash Flow',
      effort: 'Low',
      timeframe: 'Immediate (<30d)',
      actionPlan: 'Deploy non-refundable holiday booking deposits on Resy platform to lock in high-margin banquet revenue.',
    }
  ],
  cfoCommentary: {
    headlineSummary: 'Prime cost discipline achieved at 58.6% with monthly revenues pacing at $285k/mo across all 3 venues.',
    whatHappened: 'YTD sales reached $2.24M with a healthy 15.4% EBITDA margin. Beverage sales represented 34% of total turnover with high 81% gross margins.',
    whyItHappened: 'Implementation of weekly inventory recipe costing software reduced kitchen prep waste by 18%, keeping food costs locked at 28.5%.',
    whyItMatters: 'Healthy operating margins generated $340k in YTD operating cash flow, allowing the group to fully repay its high-interest kitchen equipment loan 4 months ahead of schedule.',
    recommendedActions: [
      'Adjust downtown lunch line prep hours to bring lunch labor percentage under 32%.',
      'Lock in 6-month contract pricing on prime ribeye and organic poultry with regional wholesale distributor.',
    ],
    strategicSummary: 'Restaurant group operations are profitable, lean, and generating consistent weekly operating cash flows.',
    confidenceScore: 94,
    isAiGenerated: true,
    lastEditedBy: 'Jasleen Daswal, CPA / Lead FP&A Consultant',
    lastEditedAt: '2026-08-25T04:10:00Z',
  },
  model: {
    client: {} as ClientProfile,
    periods: [
      { periodKey: '2026-01', label: 'Jan 2026', isActual: true },
      { periodKey: '2026-02', label: 'Feb 2026', isActual: true },
      { periodKey: '2026-03', label: 'Mar 2026', isActual: true },
      { periodKey: '2026-04', label: 'Apr 2026', isActual: true },
      { periodKey: '2026-05', label: 'May 2026', isActual: true },
      { periodKey: '2026-06', label: 'Jun 2026', isActual: true },
      { periodKey: '2026-07', label: 'Jul 2026', isActual: true },
      { periodKey: '2026-08', label: 'Aug 2026', isActual: true },
    ],
    historicalMonthly: [
      {
        periodKey: '2026-01', periodLabel: 'Jan 2026',
        revenue: 255000, cogs: 74000, grossProfit: 181000, grossMarginPercent: 71.0,
        salariesAndWages: 76500, salesAndMarketing: 8000, rentAndFacilities: 28000, generalAndAdmin: 18000, depreciationAndAmort: 6500, otherOpex: 8500, totalOpex: 145500,
        ebitda: 42000, ebitdaMarginPercent: 16.5, interestExpense: 2200, taxExpense: 6000, netIncome: 27300, netMarginPercent: 10.7,
        cashAndEquivalents: 240000, accountsReceivable: 12000, inventory: 32000, otherCurrentAssets: 14000, totalCurrentAssets: 298000, fixedAssets: 680000, totalAssets: 978000,
        accountsPayable: 45000, shortTermDebt: 15000, accruedLiabilities: 22000, totalCurrentLiabilities: 82000, longTermDebt: 220000, totalLiabilities: 302000, totalEquity: 676000,
        operatingCashFlow: 38000, investingCashFlow: -6000, financingCashFlow: -12000, netCashFlow: 20000, endingCash: 260000,
        workingCapital: 216000, currentRatio: 3.63, quickRatio: 3.24, dso: 2, dpo: 22, dio: 16, ccc: -4,
      },
      {
        periodKey: '2026-02', periodLabel: 'Feb 2026',
        revenue: 268000, cogs: 77000, grossProfit: 191000, grossMarginPercent: 71.3,
        salariesAndWages: 79000, salesAndMarketing: 9000, rentAndFacilities: 28000, generalAndAdmin: 18500, depreciationAndAmort: 6500, otherOpex: 9000, totalOpex: 150000,
        ebitda: 47500, ebitdaMarginPercent: 17.7, interestExpense: 2100, taxExpense: 6800, netIncome: 32100, netMarginPercent: 12.0,
        cashAndEquivalents: 260000, accountsReceivable: 14000, inventory: 33000, otherCurrentAssets: 14000, totalCurrentAssets: 321000, fixedAssets: 675000, totalAssets: 996000,
        accountsPayable: 46000, shortTermDebt: 15000, accruedLiabilities: 23000, totalCurrentLiabilities: 84000, longTermDebt: 215000, totalLiabilities: 299000, totalEquity: 697000,
        operatingCashFlow: 44000, investingCashFlow: -5000, financingCashFlow: -12000, netCashFlow: 27000, endingCash: 287000,
        workingCapital: 237000, currentRatio: 3.82, quickRatio: 3.43, dso: 2, dpo: 22, dio: 16, ccc: -4,
      },
      {
        periodKey: '2026-03', periodLabel: 'Mar 2026',
        revenue: 280000, cogs: 80000, grossProfit: 200000, grossMarginPercent: 71.4,
        salariesAndWages: 82000, salesAndMarketing: 9500, rentAndFacilities: 28000, generalAndAdmin: 19000, depreciationAndAmort: 6500, otherOpex: 9000, totalOpex: 154000,
        ebitda: 52500, ebitdaMarginPercent: 18.8, interestExpense: 2000, taxExpense: 7500, netIncome: 36500, netMarginPercent: 13.0,
        cashAndEquivalents: 287000, accountsReceivable: 15000, inventory: 34000, otherCurrentAssets: 15000, totalCurrentAssets: 351000, fixedAssets: 670000, totalAssets: 1021000,
        accountsPayable: 48000, shortTermDebt: 15000, accruedLiabilities: 24000, totalCurrentLiabilities: 87000, longTermDebt: 210000, totalLiabilities: 297000, totalEquity: 724000,
        operatingCashFlow: 48000, investingCashFlow: -8000, financingCashFlow: -12000, netCashFlow: 28000, endingCash: 315000,
        workingCapital: 264000, currentRatio: 4.03, quickRatio: 3.64, dso: 2, dpo: 22, dio: 15, ccc: -5,
      },
      {
        periodKey: '2026-04', periodLabel: 'Apr 2026',
        revenue: 278000, cogs: 79000, grossProfit: 199000, grossMarginPercent: 71.6,
        salariesAndWages: 81500, salesAndMarketing: 9000, rentAndFacilities: 28000, generalAndAdmin: 19000, depreciationAndAmort: 6500, otherOpex: 9000, totalOpex: 153000,
        ebitda: 52500, ebitdaMarginPercent: 18.9, interestExpense: 1900, taxExpense: 7600, netIncome: 36500, netMarginPercent: 13.1,
        cashAndEquivalents: 315000, accountsReceivable: 15000, inventory: 34000, otherCurrentAssets: 15000, totalCurrentAssets: 379000, fixedAssets: 665000, totalAssets: 1044000,
        accountsPayable: 47000, shortTermDebt: 15000, accruedLiabilities: 24000, totalCurrentLiabilities: 86000, longTermDebt: 205000, totalLiabilities: 291000, totalEquity: 753000,
        operatingCashFlow: 46000, investingCashFlow: -5000, financingCashFlow: -12000, netCashFlow: 29000, endingCash: 344000,
        workingCapital: 293000, currentRatio: 4.41, quickRatio: 4.01, dso: 2, dpo: 22, dio: 16, ccc: -4,
      },
      {
        periodKey: '2026-05', periodLabel: 'May 2026',
        revenue: 292000, cogs: 83000, grossProfit: 209000, grossMarginPercent: 71.6,
        salariesAndWages: 85000, salesAndMarketing: 10000, rentAndFacilities: 28000, generalAndAdmin: 19500, depreciationAndAmort: 6500, otherOpex: 9500, totalOpex: 158500,
        ebitda: 57000, ebitdaMarginPercent: 19.5, interestExpense: 1800, taxExpense: 8200, netIncome: 40500, netMarginPercent: 13.9,
        cashAndEquivalents: 344000, accountsReceivable: 16000, inventory: 35000, otherCurrentAssets: 15000, totalCurrentAssets: 410000, fixedAssets: 660000, totalAssets: 1070000,
        accountsPayable: 50000, shortTermDebt: 15000, accruedLiabilities: 25000, totalCurrentLiabilities: 90000, longTermDebt: 200000, totalLiabilities: 290000, totalEquity: 780000,
        operatingCashFlow: 52000, investingCashFlow: -7000, financingCashFlow: -12000, netCashFlow: 33000, endingCash: 377000,
        workingCapital: 320000, currentRatio: 4.56, quickRatio: 4.17, dso: 2, dpo: 22, dio: 15, ccc: -5,
      },
      {
        periodKey: '2026-06', periodLabel: 'Jun 2026',
        revenue: 295000, cogs: 84000, grossProfit: 211000, grossMarginPercent: 71.5,
        salariesAndWages: 86000, salesAndMarketing: 10500, rentAndFacilities: 28000, generalAndAdmin: 20000, depreciationAndAmort: 6500, otherOpex: 9500, totalOpex: 160500,
        ebitda: 57000, ebitdaMarginPercent: 19.3, interestExpense: 1700, taxExpense: 8300, netIncome: 40500, netMarginPercent: 13.7,
        cashAndEquivalents: 377000, accountsReceivable: 17000, inventory: 36000, otherCurrentAssets: 16000, totalCurrentAssets: 446000, fixedAssets: 655000, totalAssets: 1101000,
        accountsPayable: 51000, shortTermDebt: 15000, accruedLiabilities: 26000, totalCurrentLiabilities: 92000, longTermDebt: 195000, totalLiabilities: 287000, totalEquity: 814000,
        operatingCashFlow: 54000, investingCashFlow: -6000, financingCashFlow: -12000, netCashFlow: 36000, endingCash: 413000,
        workingCapital: 354000, currentRatio: 4.85, quickRatio: 4.46, dso: 2, dpo: 22, dio: 16, ccc: -4,
      },
      {
        periodKey: '2026-07', periodLabel: 'Jul 2026',
        revenue: 288000, cogs: 82500, grossProfit: 205500, grossMarginPercent: 71.4,
        salariesAndWages: 84500, salesAndMarketing: 10000, rentAndFacilities: 28000, generalAndAdmin: 19800, depreciationAndAmort: 6500, otherOpex: 9500, totalOpex: 158300,
        ebitda: 53700, ebitdaMarginPercent: 18.6, interestExpense: 1600, taxExpense: 7800, netIncome: 37800, netMarginPercent: 13.1,
        cashAndEquivalents: 413000, accountsReceivable: 16000, inventory: 36000, otherCurrentAssets: 16000, totalCurrentAssets: 481000, fixedAssets: 650000, totalAssets: 1131000,
        accountsPayable: 49000, shortTermDebt: 15000, accruedLiabilities: 25500, totalCurrentLiabilities: 89500, longTermDebt: 190000, totalLiabilities: 279500, totalEquity: 851500,
        operatingCashFlow: 49000, investingCashFlow: -5000, financingCashFlow: -12000, netCashFlow: 32000, endingCash: 445000,
        workingCapital: 391500, currentRatio: 5.37, quickRatio: 4.97, dso: 2, dpo: 22, dio: 16, ccc: -4,
      },
      {
        periodKey: '2026-08', periodLabel: 'Aug 2026',
        revenue: 298000, cogs: 85000, grossProfit: 213000, grossMarginPercent: 71.5,
        salariesAndWages: 87000, salesAndMarketing: 11000, rentAndFacilities: 28000, generalAndAdmin: 20200, depreciationAndAmort: 6500, otherOpex: 9800, totalOpex: 162500,
        ebitda: 57000, ebitdaMarginPercent: 19.1, interestExpense: 1500, taxExpense: 8300, netIncome: 40700, netMarginPercent: 13.7,
        cashAndEquivalents: 445000, accountsReceivable: 18000, inventory: 37000, otherCurrentAssets: 17000, totalCurrentAssets: 517000, fixedAssets: 645000, totalAssets: 1162000,
        accountsPayable: 52000, shortTermDebt: 15000, accruedLiabilities: 26500, totalCurrentLiabilities: 93500, longTermDebt: 185000, totalLiabilities: 278500, totalEquity: 883500,
        operatingCashFlow: 55000, investingCashFlow: -6000, financingCashFlow: -12000, netCashFlow: 37000, endingCash: 482000,
        workingCapital: 423500, currentRatio: 5.53, quickRatio: 5.13, dso: 2, dpo: 22, dio: 16, ccc: -4,
      },
    ],
    budgetMonthly: [],
    forecastMonthly: [],
    annualSummaries: [
      { year: 2024, revenue: 2650000, grossProfit: 1881500, ebitda: 420000, netIncome: 265000, operatingCashFlow: 380000, endingCash: 210000 },
      { year: 2025, revenue: 3050000, grossProfit: 2165500, ebitda: 540000, netIncome: 375000, operatingCashFlow: 490000, endingCash: 240000 },
    ]
  }
};

DEMO_RESTAURANT.model.client = DEMO_RESTAURANT.client;

// 3. Apex Precision Dynamics (Manufacturing)
export const DEMO_MANUFACTURING: DemoClientBundle = {
  client: {
    id: 'demo_mfg_003',
    name: 'Apex Precision Dynamics',
    legalEntityName: 'Apex Precision Dynamics Corporation',
    industry: 'manufacturing',
    industryName: 'Manufacturing & Precision Engineering',
    businessDescription: 'Advanced CNC machining, aerospace component fabrication, and hydraulic assemblies supplier.',
    entityType: 'C-Corp',
    country: 'United States',
    currency: 'USD',
    currencySymbol: '$',
    fiscalYearEnd: 'December 31',
    reportingPeriod: 'YTD Aug 2026',
    businessSize: 'Mid-Market ($5M - $25M)',
    headcount: 52,
    contactEmail: 'cfo@apexprecision-demo.com',
    contactPhone: '+1 (555) 902-3341',
    taxId: '36-4928172',
    bankAccountMasked: '•••• 1088 (Bank of America)',
    isDemo: true,
    privacyMode: 'strict',
    lastUpdated: '2026-08-25T04:00:00Z',
  },
  wins: [
    {
      id: 'mw1',
      title: 'Scrap Rate Reduction',
      metric: 'Scrap Rate 1.6%',
      change: '-0.7% vs last year',
      businessImpact: 'Upgraded 5-axis robotic tool presetting decreased machining defects, saving $68,000 YTD in scrap metal.',
      category: 'efficiency',
    },
    {
      id: 'mw2',
      title: 'Gross Margin Expansion',
      metric: 'Gross Margin 39.4%',
      change: '+2.1% YoY',
      businessImpact: 'Long-term raw aluminum index procurement contracts shielded margins from spot commodity swings.',
      category: 'margin',
    }
  ],
  concerns: [
    'Inventory days (DIO) at 52 days due to excess safety buffer stock of titanium alloy rods.',
    'Customer payment terms for Tier-1 aerospace prime average 60 days.',
  ],
  redFlags: [
    {
      id: 'mrf1',
      severity: 'medium',
      title: 'Customer Concentration in Top 2 Aerospace Accounts',
      metric: 'Top 2 Revenue Share',
      currentValue: '54.2% of Total Sales',
      threshold: '40.0%',
      impact: 'Heavy dependency on Northrop and Boeing sub-contracts exposes backlog to program schedule delays.',
      recommendation: 'Target medical robotics and semiconductor tooling contracts to diversify customer base.',
      category: 'concentration',
    }
  ],
  opportunities: [
    {
      id: 'mop1',
      title: 'Supply Chain Financing / Dynamic Vendor Discounting',
      potentialImpact: '+$110,000 Working Capital Cash Release',
      effort: 'Medium',
      timeframe: 'Quarterly (90d)',
      actionPlan: 'Negotiate 2% 10 Net 30 terms with secondary metal distribution suppliers.',
    }
  ],
  cfoCommentary: {
    headlineSummary: 'Manufacturing throughput pacing strongly at $1.25M/mo with $14.5M annual projection and 20.2% EBITDA margin.',
    whatHappened: 'Apex generated $9.72M in top-line manufacturing shipments through August with $1.96M in YTD EBITDA.',
    whyItHappened: 'Machine tool utilization in Plant 2 averaged 84%, while raw material inventory turns improved to 7.8x.',
    whyItMatters: 'Strong free cash generation funded a $450k capital expenditure for two high-speed DMG MORI CNC machines with zero external bank debt.',
    recommendedActions: [
      'Implement consignment inventory model for raw titanium bar stock to trim 8 days from DIO.',
      'Establish credit insurance limits for Tier-2 aerospace contracts with over 60-day terms.',
    ],
    strategicSummary: 'Firm possesses strong competitive moats, modern manufacturing assets, and high operating leverage.',
    confidenceScore: 97,
    isAiGenerated: true,
    lastEditedBy: 'Jasleen Daswal, CPA / Lead FP&A Consultant',
    lastEditedAt: '2026-08-25T04:20:00Z',
  },
  model: {
    client: {} as ClientProfile,
    periods: [
      { periodKey: '2026-01', label: 'Jan 2026', isActual: true },
      { periodKey: '2026-02', label: 'Feb 2026', isActual: true },
      { periodKey: '2026-03', label: 'Mar 2026', isActual: true },
      { periodKey: '2026-04', label: 'Apr 2026', isActual: true },
      { periodKey: '2026-05', label: 'May 2026', isActual: true },
      { periodKey: '2026-06', label: 'Jun 2026', isActual: true },
      { periodKey: '2026-07', label: 'Jul 2026', isActual: true },
      { periodKey: '2026-08', label: 'Aug 2026', isActual: true },
    ],
    historicalMonthly: [
      {
        periodKey: '2026-01', periodLabel: 'Jan 2026',
        revenue: 1150000, cogs: 700000, grossProfit: 450000, grossMarginPercent: 39.1,
        salariesAndWages: 145000, salesAndMarketing: 25000, rentAndFacilities: 35000, generalAndAdmin: 42000, depreciationAndAmort: 28000, otherOpex: 15000, totalOpex: 290000,
        ebitda: 188000, ebitdaMarginPercent: 16.3, interestExpense: 6500, taxExpense: 32000, netIncome: 121500, netMarginPercent: 10.6,
        cashAndEquivalents: 1650000, accountsReceivable: 1950000, inventory: 1100000, otherCurrentAssets: 120000, totalCurrentAssets: 4820000, fixedAssets: 3400000, totalAssets: 8220000,
        accountsPayable: 680000, shortTermDebt: 90000, accruedLiabilities: 140000, totalCurrentLiabilities: 910000, longTermDebt: 1200000, totalLiabilities: 2110000, totalEquity: 6110000,
        operatingCashFlow: 160000, investingCashFlow: -40000, financingCashFlow: -30000, netCashFlow: 90000, endingCash: 1740000,
        workingCapital: 3910000, currentRatio: 5.30, quickRatio: 4.09, dso: 62, dpo: 35, dio: 57, ccc: 84,
      },
      {
        periodKey: '2026-02', periodLabel: 'Feb 2026',
        revenue: 1180000, cogs: 715000, grossProfit: 465000, grossMarginPercent: 39.4,
        salariesAndWages: 148000, salesAndMarketing: 26000, rentAndFacilities: 35000, generalAndAdmin: 43000, depreciationAndAmort: 28000, otherOpex: 16000, totalOpex: 296000,
        ebitda: 197000, ebitdaMarginPercent: 16.7, interestExpense: 6300, taxExpense: 34000, netIncome: 128700, netMarginPercent: 10.9,
        cashAndEquivalents: 1740000, accountsReceivable: 1980000, inventory: 1090000, otherCurrentAssets: 120000, totalCurrentAssets: 4930000, fixedAssets: 3380000, totalAssets: 8310000,
        accountsPayable: 690000, shortTermDebt: 90000, accruedLiabilities: 145000, totalCurrentLiabilities: 925000, longTermDebt: 1180000, totalLiabilities: 2105000, totalEquity: 6205000,
        operatingCashFlow: 172000, investingCashFlow: -35000, financingCashFlow: -30000, netCashFlow: 107000, endingCash: 1847000,
        workingCapital: 4005000, currentRatio: 5.33, quickRatio: 4.15, dso: 61, dpo: 35, dio: 56, ccc: 82,
      },
      {
        periodKey: '2026-03', periodLabel: 'Mar 2026',
        revenue: 1220000, cogs: 738000, grossProfit: 482000, grossMarginPercent: 39.5,
        salariesAndWages: 152000, salesAndMarketing: 27000, rentAndFacilities: 35000, generalAndAdmin: 44000, depreciationAndAmort: 28000, otherOpex: 16000, totalOpex: 302000,
        ebitda: 208000, ebitdaMarginPercent: 17.0, interestExpense: 6100, taxExpense: 37000, netIncome: 136900, netMarginPercent: 11.2,
        cashAndEquivalents: 1847000, accountsReceivable: 2010000, inventory: 1080000, otherCurrentAssets: 125000, totalCurrentAssets: 5062000, fixedAssets: 3360000, totalAssets: 8422000,
        accountsPayable: 710000, shortTermDebt: 90000, accruedLiabilities: 150000, totalCurrentLiabilities: 950000, longTermDebt: 1160000, totalLiabilities: 2110000, totalEquity: 6312000,
        operatingCashFlow: 185000, investingCashFlow: -45000, financingCashFlow: -30000, netCashFlow: 110000, endingCash: 1957000,
        workingCapital: 4112000, currentRatio: 5.33, quickRatio: 4.19, dso: 60, dpo: 35, dio: 53, ccc: 78,
      },
      {
        periodKey: '2026-04', periodLabel: 'Apr 2026',
        revenue: 1210000, cogs: 732000, grossProfit: 478000, grossMarginPercent: 39.5,
        salariesAndWages: 151000, salesAndMarketing: 26500, rentAndFacilities: 35000, generalAndAdmin: 44000, depreciationAndAmort: 28000, otherOpex: 16000, totalOpex: 300500,
        ebitda: 205500, ebitdaMarginPercent: 17.0, interestExpense: 5900, taxExpense: 36000, netIncome: 135600, netMarginPercent: 11.2,
        cashAndEquivalents: 1957000, accountsReceivable: 1990000, inventory: 1070000, otherCurrentAssets: 125000, totalCurrentAssets: 5142000, fixedAssets: 3340000, totalAssets: 8482000,
        accountsPayable: 700000, shortTermDebt: 90000, accruedLiabilities: 148000, totalCurrentLiabilities: 938000, longTermDebt: 1140000, totalLiabilities: 2078000, totalEquity: 6404000,
        operatingCashFlow: 180000, investingCashFlow: -30000, financingCashFlow: -30000, netCashFlow: 120000, endingCash: 2077000,
        workingCapital: 4204000, currentRatio: 5.48, quickRatio: 4.34, dso: 60, dpo: 35, dio: 53, ccc: 78,
      },
      {
        periodKey: '2026-05', periodLabel: 'May 2026',
        revenue: 1240000, cogs: 750000, grossProfit: 490000, grossMarginPercent: 39.5,
        salariesAndWages: 154000, salesAndMarketing: 28000, rentAndFacilities: 35000, generalAndAdmin: 45000, depreciationAndAmort: 28000, otherOpex: 17000, totalOpex: 307000,
        ebitda: 211000, ebitdaMarginPercent: 17.0, interestExpense: 5700, taxExpense: 38000, netIncome: 139300, netMarginPercent: 11.2,
        cashAndEquivalents: 2077000, accountsReceivable: 2020000, inventory: 1060000, otherCurrentAssets: 128000, totalCurrentAssets: 5285000, fixedAssets: 3320000, totalAssets: 8605000,
        accountsPayable: 715000, shortTermDebt: 90000, accruedLiabilities: 152000, totalCurrentLiabilities: 957000, longTermDebt: 1120000, totalLiabilities: 2077000, totalEquity: 6528000,
        operatingCashFlow: 192000, investingCashFlow: -40000, financingCashFlow: -30000, netCashFlow: 122000, endingCash: 2199000,
        workingCapital: 4328000, currentRatio: 5.52, quickRatio: 4.41, dso: 59, dpo: 35, dio: 51, ccc: 75,
      },
      {
        periodKey: '2026-06', periodLabel: 'Jun 2026',
        revenue: 1260000, cogs: 762000, grossProfit: 498000, grossMarginPercent: 39.5,
        salariesAndWages: 156000, salesAndMarketing: 28500, rentAndFacilities: 35000, generalAndAdmin: 46000, depreciationAndAmort: 28000, otherOpex: 17500, totalOpex: 311000,
        ebitda: 215000, ebitdaMarginPercent: 17.1, interestExpense: 5500, taxExpense: 39000, netIncome: 142500, netMarginPercent: 11.3,
        cashAndEquivalents: 2199000, accountsReceivable: 2040000, inventory: 1050000, otherCurrentAssets: 130000, totalCurrentAssets: 5419000, fixedAssets: 3300000, totalAssets: 8719000,
        accountsPayable: 725000, shortTermDebt: 90000, accruedLiabilities: 155000, totalCurrentLiabilities: 970000, longTermDebt: 1100000, totalLiabilities: 2070000, totalEquity: 6649000,
        operatingCashFlow: 198000, investingCashFlow: -35000, financingCashFlow: -30000, netCashFlow: 133000, endingCash: 2332000,
        workingCapital: 4449000, currentRatio: 5.59, quickRatio: 4.50, dso: 59, dpo: 35, dio: 50, ccc: 74,
      },
      {
        periodKey: '2026-07', periodLabel: 'Jul 2026',
        revenue: 1230000, cogs: 745000, grossProfit: 485000, grossMarginPercent: 39.4,
        salariesAndWages: 154000, salesAndMarketing: 27500, rentAndFacilities: 35000, generalAndAdmin: 45000, depreciationAndAmort: 28000, otherOpex: 17000, totalOpex: 306500,
        ebitda: 206500, ebitdaMarginPercent: 16.8, interestExpense: 5300, taxExpense: 37000, netIncome: 136200, netMarginPercent: 11.1,
        cashAndEquivalents: 2332000, accountsReceivable: 2010000, inventory: 1045000, otherCurrentAssets: 130000, totalCurrentAssets: 5517000, fixedAssets: 3280000, totalAssets: 8797000,
        accountsPayable: 710000, shortTermDebt: 90000, accruedLiabilities: 153000, totalCurrentLiabilities: 953000, longTermDebt: 1080000, totalLiabilities: 2033000, totalEquity: 6764000,
        operatingCashFlow: 188000, investingCashFlow: -30000, financingCashFlow: -30000, netCashFlow: 128000, endingCash: 2460000,
        workingCapital: 4564000, currentRatio: 5.79, quickRatio: 4.69, dso: 59, dpo: 35, dio: 51, ccc: 75,
      },
      {
        periodKey: '2026-08', periodLabel: 'Aug 2026',
        revenue: 1255000, cogs: 760000, grossProfit: 495000, grossMarginPercent: 39.4,
        salariesAndWages: 157000, salesAndMarketing: 29000, rentAndFacilities: 35000, generalAndAdmin: 46500, depreciationAndAmort: 28000, otherOpex: 17500, totalOpex: 313000,
        ebitda: 210000, ebitdaMarginPercent: 16.7, interestExpense: 5100, taxExpense: 38000, netIncome: 138900, netMarginPercent: 11.1,
        cashAndEquivalents: 2460000, accountsReceivable: 2030000, inventory: 1040000, otherCurrentAssets: 132000, totalCurrentAssets: 5662000, fixedAssets: 3260000, totalAssets: 8922000,
        accountsPayable: 720000, shortTermDebt: 90000, accruedLiabilities: 156000, totalCurrentLiabilities: 966000, longTermDebt: 1060000, totalLiabilities: 2026000, totalEquity: 6896000,
        operatingCashFlow: 195000, investingCashFlow: -40000, financingCashFlow: -30000, netCashFlow: 125000, endingCash: 2585000,
        workingCapital: 4696000, currentRatio: 5.86, quickRatio: 4.78, dso: 59, dpo: 35, dio: 50, ccc: 74,
      },
    ],
    budgetMonthly: [],
    forecastMonthly: [],
    annualSummaries: [
      { year: 2024, revenue: 12200000, grossProfit: 4636000, ebitda: 1850000, netIncome: 1180000, operatingCashFlow: 1650000, endingCash: 1450000 },
      { year: 2025, revenue: 13600000, grossProfit: 5236000, ebitda: 2240000, netIncome: 1480000, operatingCashFlow: 2050000, endingCash: 1650000 },
    ]
  }
};

DEMO_MANUFACTURING.model.client = DEMO_MANUFACTURING.client;

export const ALL_DEMO_CLIENTS: Record<string, DemoClientBundle> = {
  [DEMO_MEDICAL.client.id]: DEMO_MEDICAL,
  [DEMO_RESTAURANT.client.id]: DEMO_RESTAURANT,
  [DEMO_MANUFACTURING.client.id]: DEMO_MANUFACTURING,
};

export function getAvailableDemoClients(): ClientProfile[] {
  return [DEMO_MEDICAL.client, DEMO_RESTAURANT.client, DEMO_MANUFACTURING.client];
}

export function getMedicalPracticeDemoData(client?: ClientProfile): MonthlyFinancialRecord[] {
  return DEMO_MEDICAL.model.historicalMonthly;
}

export function getRestaurantGroupDemoData(client?: ClientProfile): MonthlyFinancialRecord[] {
  return DEMO_RESTAURANT.model.historicalMonthly;
}

export function getManufacturingDemoData(client?: ClientProfile): MonthlyFinancialRecord[] {
  return DEMO_MANUFACTURING.model.historicalMonthly;
}
