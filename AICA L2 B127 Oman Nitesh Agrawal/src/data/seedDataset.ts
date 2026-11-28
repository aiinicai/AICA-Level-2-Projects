import { roundOMR } from '../engine/kpiEngine';
import type {
  AccountingPolicyConfig,
  AccountClass,
  Company,
  ConstructionProgressPoint,
  ContractorRecord,
  FinancingFacility,
  GlMappingRule,
  HandoverWarrantyRecord,
  MisDataset,
  PeriodWorkflowState,
  Project,
  ProjectBudgetLine,
  RentalLeaseRecord,
  RiskItem,
  TrialBalanceRow,
  UnitRecord,
  UnitStatus,
} from '../types/mis';

function build24Periods(): string[] {
  const periods: string[] = [];
  let year = 2024;
  let month = 12;
  for (let i = 0; i < 24; i++) {
    periods.push(`${year}-${String(month).padStart(2, '0')}`);
    month += 1;
    if (month > 12) {
      month = 1;
      year += 1;
    }
  }
  return periods;
}

const COMPANIES: Company[] = [
  {
    id: 'cmp-almajd',
    code: 'AMUD',
    name: 'Al Majd Urban Developments LLC',
    nameAr: 'شركة المجد للتطوير العمراني ش.م.م',
    type: 'Parent',
    ownershipPct: 100,
    baseCurrency: 'OMR',
    crNumber: '1248910',
    vatNumber: 'OM1100489210',
    fiscalYearStartMonth: 1,
  },
  {
    id: 'cmp-qurum',
    code: 'QBRS',
    name: 'Qurum Bay Residences SPV LLC',
    nameAr: 'شركة خليج القرم السكنية (ذات غرض خاص)',
    type: 'SPV',
    ownershipPct: 85,
    baseCurrency: 'OMR',
    crNumber: '1390421',
    vatNumber: 'OM1100512844',
    fiscalYearStartMonth: 1,
  },
  {
    id: 'cmp-sohar',
    code: 'SLCP',
    name: 'Sohar Logistics & Commercial Park SPV',
    nameAr: 'مجمع صحار اللوجستي والتجاري',
    type: 'SPV',
    ownershipPct: 100,
    baseCurrency: 'OMR',
    crNumber: '1412088',
    vatNumber: 'OM1100609912',
    fiscalYearStartMonth: 1,
  },
];

const PROJECTS: Project[] = [
  {
    id: 'prj-marina',
    companyId: 'cmp-almajd',
    code: 'PRJ-01',
    name: 'Al Mouj Marina Terraces',
    nameAr: 'تراسات مرسى الموج',
    category: 'Mixed-Use',
    location: 'Muscat Waterfront, Oman',
    revenueMethod: 'IFRS15_OverTime_PoC',
    phases: 2,
    buildings: 4,
    totalUnits: 420,
    totalSellableSqm: 58800,
    landAreaSqm: 34500,
    startDate: '2024-06',
    plannedCompletion: '2027-06',
    forecastCompletion: '2027-08',
    escrowAccountNo: 'OM44-BMSO-00921844-01',
    escrowBank: 'Bank Muscat Escrow',
    status: 'Active',
    hasSupportingSchedule: true,
  },
  {
    id: 'prj-qurum',
    companyId: 'cmp-qurum',
    code: 'PRJ-02',
    name: 'Qurum Heights Villas & Residences',
    nameAr: 'مرتفعات القرم للفلل والمساكن',
    category: 'Residential',
    location: 'Qurum Hills, Muscat',
    revenueMethod: 'IFRS15_PointInTime_Handover',
    phases: 3,
    buildings: 12,
    totalUnits: 310,
    totalSellableSqm: 68200,
    landAreaSqm: 82000,
    startDate: '2024-01',
    plannedCompletion: '2026-12',
    forecastCompletion: '2027-02',
    escrowAccountNo: 'OM19-NBO-77102931-04',
    escrowBank: 'National Bank of Oman',
    status: 'Handover',
    hasSupportingSchedule: true,
  },
  {
    id: 'prj-plaza',
    companyId: 'cmp-almajd',
    code: 'PRJ-03',
    name: 'Muscat Central Business Plaza',
    nameAr: 'ساحة مسقط للأعمال المركزية',
    category: 'Commercial',
    location: 'Madinat Al Irfan, Muscat',
    revenueMethod: 'IFRS15_OverTime_PoC',
    phases: 2,
    buildings: 3,
    totalUnits: 260,
    totalSellableSqm: 49400,
    landAreaSqm: 26000,
    startDate: '2025-01',
    plannedCompletion: '2027-11',
    forecastCompletion: '2027-11',
    escrowAccountNo: 'OM88-BDOF-44109234-02',
    escrowBank: 'Bank Dhofar Corporate',
    status: 'Active',
    hasSupportingSchedule: true,
  },
  {
    id: 'prj-salalah',
    companyId: 'cmp-qurum',
    code: 'PRJ-04',
    name: 'Salalah Coastal Master Community',
    nameAr: 'مجتمع صلالة الساحلي المتكامل',
    category: 'Master Development',
    location: 'Hawana Corridor, Salalah',
    revenueMethod: 'IFRS15_OverTime_PoC',
    phases: 4,
    buildings: 18,
    totalUnits: 390,
    totalSellableSqm: 93600,
    landAreaSqm: 210000,
    startDate: '2025-04',
    plannedCompletion: '2028-09',
    forecastCompletion: '2028-12',
    escrowAccountNo: 'OM61-OAB-55182900-09',
    escrowBank: 'Oman Arab Bank Escrow',
    status: 'Active',
    hasSupportingSchedule: true,
  },
  {
    id: 'prj-sohar',
    companyId: 'cmp-sohar',
    code: 'PRJ-05',
    name: 'Sohar Business Gate',
    nameAr: 'بوابة صحار للأعمال',
    category: 'Commercial',
    location: 'Sohar Freezone Gateway, Oman',
    revenueMethod: 'IFRS15_PointInTime_Handover',
    phases: 1,
    buildings: 2,
    totalUnits: 180,
    totalSellableSqm: 34200,
    landAreaSqm: 24000,
    startDate: '2023-06',
    plannedCompletion: '2026-06',
    forecastCompletion: '2026-09',
    escrowAccountNo: 'OM32-HSBC-81203941-01',
    escrowBank: 'Sohar International',
    status: 'Completed',
    hasSupportingSchedule: true,
  },
];

// Deterministic pseudo-random helper so dataset is 100% reproducible
function detRand(seed: number): number {
  const x = Math.sin(seed * 9301 + 49297) * 233280;
  return x - Math.floor(x);
}

const CUSTOMER_PREFIXES = [
  'Al Harthy Holdings',
  'Majan Investments',
  'Salim Al Riyami',
  'Noor Al Lawati',
  'Oman Gulf Ventures',
  'Tariq Al Balushi',
  'Fatma Al Zadjali',
  'Bait Al Barakah LLC',
  'Khalid Al Hinai',
  'Amina Al Busaidi',
  'Dhahran Capital',
  'Muscat Horizon Partners',
];

function generate1560Units(periods: string[]): UnitRecord[] {
  const units: UnitRecord[] = [];
  let globalIdx = 0;

  const projectUnitSpecs: Record<
    string,
    {
      unitType: UnitRecord['unitType'];
      avgArea: number;
      pricePerSqm: number;
      soldShare: number;
      handedShare: number;
      bookedShare: number;
      cancelledShare: number;
      collectionRate: number;
      overdueRate: number;
    }
  > = {
    'prj-marina': {
      unitType: 'Apartment',
      avgArea: 140,
      pricePerSqm: 890,
      soldShare: 0.62,
      handedShare: 0.14,
      bookedShare: 0.08,
      cancelledShare: 0.03,
      collectionRate: 0.84,
      overdueRate: 0.09,
    },
    'prj-qurum': {
      unitType: 'Villa',
      avgArea: 220,
      pricePerSqm: 960,
      soldShare: 0.34,
      handedShare: 0.52,
      bookedShare: 0.04,
      cancelledShare: 0.02,
      collectionRate: 0.91,
      overdueRate: 0.05,
    },
    'prj-plaza': {
      unitType: 'Office',
      avgArea: 190,
      pricePerSqm: 820,
      soldShare: 0.56,
      handedShare: 0.06,
      bookedShare: 0.11,
      cancelledShare: 0.03,
      collectionRate: 0.78,
      overdueRate: 0.14,
    },
    'prj-salalah': {
      unitType: 'Townhouse',
      avgArea: 240,
      pricePerSqm: 680,
      soldShare: 0.48,
      handedShare: 0.04,
      bookedShare: 0.09,
      cancelledShare: 0.04,
      collectionRate: 0.74,
      overdueRate: 0.16,
    },
    'prj-sohar': {
      unitType: 'Retail',
      avgArea: 190,
      pricePerSqm: 750,
      soldShare: 0.14,
      handedShare: 0.72,
      bookedShare: 0.02,
      cancelledShare: 0.02,
      collectionRate: 0.95,
      overdueRate: 0.03,
    },
  };

  for (const prj of PROJECTS) {
    const spec = projectUnitSpecs[prj.id];
    for (let i = 1; i <= prj.totalUnits; i++) {
      globalIdx += 1;
      const r = detRand(globalIdx);
      const areaVariance = 0.85 + detRand(globalIdx + 17) * 0.3;
      const areaSqm = Math.round(spec.avgArea * areaVariance);
      const listPriceOMR = roundOMR(areaSqm * spec.pricePerSqm);

      let status: UnitStatus = 'Available';
      if (r < spec.handedShare) status = 'Handed Over';
      else if (r < spec.handedShare + spec.soldShare) status = 'Sold';
      else if (r < spec.handedShare + spec.soldShare + spec.bookedShare) status = 'Booked';
      else if (r < spec.handedShare + spec.soldShare + spec.bookedShare + spec.cancelledShare) status = 'Cancelled';

      const discountPct = status === 'Sold' || status === 'Handed Over' ? detRand(globalIdx + 33) * 0.045 : 0;
      const discountOMR = roundOMR(listPriceOMR * discountPct);
      const contractedPriceOMR =
        status === 'Available' || status === 'Cancelled' ? 0 : roundOMR(listPriceOMR - discountOMR);

      let invoicedOMR = 0;
      let collectedOMR = 0;
      let overdueOMR = 0;
      let saleMonth: string | null = null;
      let customerName: string | null = null;
      let handoverStatus: UnitRecord['handoverStatus'] = 'N/A';
      let dlpExpiryMonth: string | null = null;

      if (status === 'Handed Over') {
        invoicedOMR = contractedPriceOMR;
        collectedOMR = roundOMR(invoicedOMR * (0.94 + detRand(globalIdx + 71) * 0.06));
        overdueOMR = roundOMR(Math.max(0, invoicedOMR - collectedOMR));
        saleMonth = periods[Math.floor(detRand(globalIdx + 5) * 14)];
        customerName = `${CUSTOMER_PREFIXES[globalIdx % CUSTOMER_PREFIXES.length]} #${100 + (globalIdx % 80)}`;
        handoverStatus = 'Completed';
        dlpExpiryMonth = '2027-11';
      } else if (status === 'Sold') {
        const billingStage = 0.4 + detRand(globalIdx + 41) * 0.45;
        invoicedOMR = roundOMR(contractedPriceOMR * billingStage);
        collectedOMR = roundOMR(invoicedOMR * (spec.collectionRate - 0.06 + detRand(globalIdx + 55) * 0.12));
        overdueOMR = roundOMR(Math.max(0, (invoicedOMR - collectedOMR) * spec.overdueRate * 4));
        saleMonth = periods[Math.floor(detRand(globalIdx + 9) * 23)];
        customerName = `${CUSTOMER_PREFIXES[globalIdx % CUSTOMER_PREFIXES.length]} #${100 + (globalIdx % 80)}`;
        handoverStatus = billingStage > 0.78 ? 'Snagging' : 'Pending';
      } else if (status === 'Booked') {
        invoicedOMR = roundOMR(contractedPriceOMR * 0.1);
        collectedOMR = invoicedOMR;
        saleMonth = periods[22 + (globalIdx % 2)];
        customerName = `${CUSTOMER_PREFIXES[globalIdx % CUSTOMER_PREFIXES.length]}`;
        handoverStatus = 'Pending';
      }

      const bldgNum = ((i - 1) % prj.buildings) + 1;
      const phaseNum = ((i - 1) % prj.phases) + 1;
      const floorNum = ((i - 1) % 12) + 1;

      units.push({
        id: `unit-${prj.code}-${String(i).padStart(4, '0')}`,
        projectId: prj.id,
        companyId: prj.companyId,
        unitCode: `${prj.code}-B${bldgNum}-${String(floorNum).padStart(2, '0')}${String((i % 9) + 1)}`,
        phase: `Phase ${phaseNum}`,
        building: `Tower/Block ${String.fromCharCode(64 + bldgNum)}`,
        floor: floorNum,
        unitType: spec.unitType,
        areaSqm,
        listPriceOMR,
        discountOMR,
        contractedPriceOMR,
        invoicedOMR,
        collectedOMR,
        overdueOMR,
        status,
        saleMonth,
        customerName,
        handoverStatus,
        dlpExpiryMonth,
      });
    }
  }

  return units;
}

function generateTrialBalance24Months(periods: string[]): TrialBalanceRow[] {
  const rows: TrialBalanceRow[] = [];

  // Per-company base monthly P&L and closing BS profiles so Debits === Credits identically every month
  const companyTemplates: {
    companyId: string;
    projectId: string;
    monthlyRevBase: number;
    grossMarginRatio: number;
    opexRatio: number;
    finCostBase: number;
    taxRate: number;
    unrestrictedCashStart: number;
    escrowCashStart: number;
    receivablesStart: number;
    contractAssetStart: number;
    wipStart: number;
    invPropStart: number;
    fixedAssetsStart: number;
    payablesStart: number;
    advancesStart: number;
    retentionStart: number;
    debtStart: number;
    intercompanyBal: number; // +ve for cmp-almajd receivable, -ve for cmp-qurum payable
  }[] = [
    {
      companyId: 'cmp-almajd',
      projectId: 'prj-marina',
      monthlyRevBase: 1_950_000,
      grossMarginRatio: 0.34,
      opexRatio: 0.085,
      finCostBase: 92_000,
      taxRate: 0.15,
      unrestrictedCashStart: 8_420_000,
      escrowCashStart: 12_850_000,
      receivablesStart: 9_150_000,
      contractAssetStart: 4_820_000,
      wipStart: 28_400_000,
      invPropStart: 11_200_000,
      fixedAssetsStart: 2_350_000,
      payablesStart: 6_840_000,
      advancesStart: 14_250_000,
      retentionStart: 3_180_000,
      debtStart: 24_500_000,
      intercompanyBal: 2_450_000,
    },
    {
      companyId: 'cmp-qurum',
      projectId: 'prj-qurum',
      monthlyRevBase: 1_480_000,
      grossMarginRatio: 0.31,
      opexRatio: 0.078,
      finCostBase: 64_000,
      taxRate: 0.15,
      unrestrictedCashStart: 4_120_000,
      escrowCashStart: 8_640_000,
      receivablesStart: 6_410_000,
      contractAssetStart: 2_900_000,
      wipStart: 24_600_000,
      invPropStart: 0,
      fixedAssetsStart: 980_000,
      payablesStart: 5_210_000,
      advancesStart: 9_800_000,
      retentionStart: 2_420_000,
      debtStart: 16_200_000,
      intercompanyBal: -2_450_000,
    },
    {
      companyId: 'cmp-sohar',
      projectId: 'prj-sohar',
      monthlyRevBase: 760_000,
      grossMarginRatio: 0.39,
      opexRatio: 0.07,
      finCostBase: 31_000,
      taxRate: 0.15,
      unrestrictedCashStart: 3_280_000,
      escrowCashStart: 1_950_000,
      receivablesStart: 2_180_000,
      contractAssetStart: 640_000,
      wipStart: 4_900_000,
      invPropStart: 14_500_000,
      fixedAssetsStart: 1_120_000,
      payablesStart: 1_890_000,
      advancesStart: 2_100_000,
      retentionStart: 940_000,
      debtStart: 8_100_000,
      intercompanyBal: 0,
    },
  ];

  // Track cumulative balances so Opening(t) === Closing(t-1)
  const prevClosingMap = new Map<string, { debit: number; credit: number }>();

  for (let pIdx = 0; pIdx < periods.length; pIdx++) {
    const period = periods[pIdx];
    const seasonality = 1 + 0.08 * Math.sin((pIdx / 12) * Math.PI * 2) + pIdx * 0.012;

    for (const tpl of companyTemplates) {
      const rev = roundOMR(tpl.monthlyRevBase * seasonality);
      const cogs = roundOMR(rev * (1 - tpl.grossMarginRatio));
      const opex = roundOMR(rev * tpl.opexRatio);
      const finCost = roundOMR(tpl.finCostBase * (1 - pIdx * 0.005));
      const ebt = roundOMR(rev - cogs - opex - finCost);
      const tax = roundOMR(Math.max(0, ebt * tpl.taxRate));
      const netInc = roundOMR(ebt - tax);

      // Movements on BS accounts that sum EXACTLY with P&L to zero net movement
      const dCashUnrestricted = roundOMR(netInc * 0.45);
      const dCashEscrow = roundOMR(netInc * 0.25);
      const dReceivables = roundOMR(rev * 0.06);
      const dContractAsset = roundOMR(rev * 0.02);
      const dWip = roundOMR(cogs * 0.14);
      const dInvProp = roundOMR(pIdx % 6 === 0 ? 120_000 : 0);
      const dFixed = roundOMR(15_000);
      const dAdvances = roundOMR(rev * 0.04);
      const dRetention = roundOMR(cogs * 0.03);
      const dDebt = roundOMR(-45_000);
      // Plug payables so total BS asset movement - liability movement === netInc (exact accounting identity!)
      const totalAssetDelta = roundOMR(
        dCashUnrestricted + dCashEscrow + dReceivables + dContractAsset + dWip + dInvProp + dFixed
      );
      const nonPayableLiabDelta = roundOMR(dAdvances + dRetention + dDebt);
      const dPayables = roundOMR(totalAssetDelta - netInc - nonPayableLiabDelta);

      const accountSpecs: {
        code: string;
        name: string;
        cls: AccountClass;
        costCentre: string;
        dept: string;
        isIc: boolean;
        baseInitDebit: number;
        baseInitCredit: number;
        movDebit: number;
        movCredit: number;
      }[] = [
        {
          code: '1010',
          name: 'Corporate Operating Bank Accounts',
          cls: 'CashUnrestricted',
          costCentre: 'CC-TREASURY',
          dept: 'Treasury',
          isIc: false,
          baseInitDebit: tpl.unrestrictedCashStart,
          baseInitCredit: 0,
          movDebit: dCashUnrestricted >= 0 ? dCashUnrestricted : 0,
          movCredit: dCashUnrestricted < 0 ? Math.abs(dCashUnrestricted) : 0,
        },
        {
          code: '1020',
          name: 'Restricted Project Escrow Accounts',
          cls: 'CashEscrow',
          costCentre: 'CC-ESCROW',
          dept: 'Project Finance',
          isIc: false,
          baseInitDebit: tpl.escrowCashStart,
          baseInitCredit: 0,
          movDebit: dCashEscrow >= 0 ? dCashEscrow : 0,
          movCredit: dCashEscrow < 0 ? Math.abs(dCashEscrow) : 0,
        },
        {
          code: '1210',
          name: 'Customer Installment Receivables',
          cls: 'Receivables',
          costCentre: 'CC-SALES',
          dept: 'Collections',
          isIc: false,
          baseInitDebit: tpl.receivablesStart,
          baseInitCredit: 0,
          movDebit: dReceivables,
          movCredit: 0,
        },
        {
          code: '1250',
          name: 'IFRS 15 Contract Assets (Unbilled PoC)',
          cls: 'ContractAsset',
          costCentre: 'CC-FIN',
          dept: 'Financial Reporting',
          isIc: false,
          baseInitDebit: tpl.contractAssetStart,
          baseInitCredit: 0,
          movDebit: dContractAsset,
          movCredit: 0,
        },
        {
          code: '1310',
          name: 'Development Properties & WIP (IAS 2)',
          cls: 'InventoryWIP',
          costCentre: 'CC-DEV',
          dept: 'Development',
          isIc: false,
          baseInitDebit: tpl.wipStart,
          baseInitCredit: 0,
          movDebit: dWip,
          movCredit: 0,
        },
        {
          code: '1410',
          name: 'Investment Properties (IAS 40)',
          cls: 'InvestmentProperty',
          costCentre: 'CC-REIT',
          dept: 'Asset Management',
          isIc: false,
          baseInitDebit: tpl.invPropStart,
          baseInitCredit: 0,
          movDebit: dInvProp,
          movCredit: 0,
        },
        {
          code: '1510',
          name: 'Property, Plant & Equipment',
          cls: 'FixedAssets',
          costCentre: 'CC-CORP',
          dept: 'Corporate',
          isIc: false,
          baseInitDebit: tpl.fixedAssetsStart,
          baseInitCredit: 0,
          movDebit: dFixed,
          movCredit: 0,
        },
        {
          code: '2010',
          name: 'Trade & Contractor Payables',
          cls: 'Payables',
          costCentre: 'CC-PROC',
          dept: 'Procurement',
          isIc: false,
          baseInitDebit: 0,
          baseInitCredit: tpl.payablesStart,
          movDebit: dPayables < 0 ? Math.abs(dPayables) : 0,
          movCredit: dPayables >= 0 ? dPayables : 0,
        },
        {
          code: '2110',
          name: 'Customer Advances & Unearned Revenue',
          cls: 'CustomerAdvances',
          costCentre: 'CC-SALES',
          dept: 'Sales Admin',
          isIc: false,
          baseInitDebit: 0,
          baseInitCredit: tpl.advancesStart,
          movDebit: 0,
          movCredit: dAdvances,
        },
        {
          code: '2150',
          name: 'Contractor Retention Payable',
          cls: 'RetentionPayable',
          costCentre: 'CC-QS',
          dept: 'Quantity Surveying',
          isIc: false,
          baseInitDebit: 0,
          baseInitCredit: tpl.retentionStart,
          movDebit: 0,
          movCredit: dRetention,
        },
        {
          code: '2310',
          name: 'Project Development Facilities & Murabaha',
          cls: 'Debt',
          costCentre: 'CC-TREASURY',
          dept: 'Treasury',
          isIc: false,
          baseInitDebit: 0,
          baseInitCredit: tpl.debtStart,
          movDebit: Math.abs(dDebt),
          movCredit: 0,
        },
        {
          code: '4010',
          name: 'Property Development Revenue (IFRS 15)',
          cls: 'Revenue',
          costCentre: 'CC-SALES',
          dept: 'Commercial',
          isIc: false,
          baseInitDebit: 0,
          baseInitCredit: 0,
          movDebit: 0,
          movCredit: rev,
        },
        {
          code: '5010',
          name: 'Cost of Development Sales',
          cls: 'COGS',
          costCentre: 'CC-DEV',
          dept: 'Development',
          isIc: false,
          baseInitDebit: 0,
          baseInitCredit: 0,
          movDebit: cogs,
          movCredit: 0,
        },
        {
          code: '6010',
          name: 'Sales, Marketing & G&A Expenses',
          cls: 'OpEx',
          costCentre: 'CC-CORP',
          dept: 'Corporate',
          isIc: false,
          baseInitDebit: 0,
          baseInitCredit: 0,
          movDebit: opex,
          movCredit: 0,
        },
        {
          code: '7010',
          name: 'Facility Interest & Finance Charges',
          cls: 'FinanceCost',
          costCentre: 'CC-TREASURY',
          dept: 'Treasury',
          isIc: false,
          baseInitDebit: 0,
          baseInitCredit: 0,
          movDebit: finCost,
          movCredit: 0,
        },
        {
          code: '8010',
          name: 'Oman Corporate Income Tax Provision',
          cls: 'Tax',
          costCentre: 'CC-TAX',
          dept: 'Taxation',
          isIc: false,
          baseInitDebit: 0,
          baseInitCredit: 0,
          movDebit: tax,
          movCredit: 0,
        },
      ];

      if (tpl.intercompanyBal !== 0) {
        accountSpecs.push({
          code: tpl.intercompanyBal > 0 ? '1910' : '2910',
          name: tpl.intercompanyBal > 0 ? 'Intercompany Due From Qurum SPV' : 'Intercompany Due To Al Majd Parent',
          cls: 'Intercompany',
          costCentre: 'CC-IC',
          dept: 'Group Consolidation',
          isIc: true,
          baseInitDebit: tpl.intercompanyBal > 0 ? tpl.intercompanyBal : 0,
          baseInitCredit: tpl.intercompanyBal < 0 ? Math.abs(tpl.intercompanyBal) : 0,
          movDebit: 0,
          movCredit: 0,
        });
      }

      // Compute balancing initial Share Capital & Retained Earnings for Period 0
      const totalInitAssets = accountSpecs.reduce((a, s) => a + s.baseInitDebit, 0);
      const totalInitLiab = accountSpecs.reduce((a, s) => a + s.baseInitCredit, 0);
      const initEquity = roundOMR(totalInitAssets - totalInitLiab);

      accountSpecs.push({
        code: '3010',
        name: 'Share Capital & Retained Earnings',
        cls: 'Equity',
        costCentre: 'CC-CORP',
        dept: 'Corporate',
        isIc: false,
        baseInitDebit: 0,
        baseInitCredit: initEquity,
        movDebit: 0,
        movCredit: 0,
      });

      for (const acc of accountSpecs) {
        const key = `${tpl.companyId}:${acc.code}`;
        const prev = prevClosingMap.get(key);
        const openDebit = prev ? prev.debit : roundOMR(acc.baseInitDebit);
        const openCredit = prev ? prev.credit : roundOMR(acc.baseInitCredit);

        const netClose = roundOMR(openDebit - openCredit + acc.movDebit - acc.movCredit);
        const closeDebit = netClose >= 0 ? netClose : 0;
        const closeCredit = netClose < 0 ? Math.abs(netClose) : 0;

        prevClosingMap.set(key, { debit: closeDebit, credit: closeCredit });

        rows.push({
          id: `tb-${period}-${tpl.companyId}-${acc.code}`,
          companyId: tpl.companyId,
          projectId: tpl.projectId,
          period,
          accountCode: acc.code,
          accountName: acc.name,
          costCentre: acc.costCentre,
          department: acc.dept,
          accountClass: acc.cls,
          openingDebit: openDebit,
          openingCredit: openCredit,
          periodDebit: roundOMR(acc.movDebit),
          periodCredit: roundOMR(acc.movCredit),
          closingDebit: closeDebit,
          closingCredit: closeCredit,
          isIntercompany: acc.isIc,
          eliminatedWithCompanyId: acc.isIc ? (tpl.companyId === 'cmp-almajd' ? 'cmp-qurum' : 'cmp-almajd') : null,
        });
      }
    }
  }

  return rows;
}

function generateBudgets(): ProjectBudgetLine[] {
  const lines: ProjectBudgetLine[] = [];
  const projectBudgets: {
    projectId: string;
    totalOrig: number;
    revisedFactor: number;
    actualRatio: number;
    accrualRatio: number;
    commitRatio: number;
    varApprovedRatio: number;
    varPendingRatio: number;
    etcRatio: number;
  }[] = [
    { projectId: 'prj-marina', totalOrig: 33_500_000, revisedFactor: 1.04, actualRatio: 0.48, accrualRatio: 0.04, commitRatio: 0.34, varApprovedRatio: 0.03, varPendingRatio: 0.025, etcRatio: 0.16 },
    { projectId: 'prj-qurum', totalOrig: 41_200_000, revisedFactor: 1.02, actualRatio: 0.78, accrualRatio: 0.05, commitRatio: 0.12, varApprovedRatio: 0.02, varPendingRatio: 0.01, etcRatio: 0.06 },
    { projectId: 'prj-plaza', totalOrig: 26_800_000, revisedFactor: 1.03, actualRatio: 0.36, accrualRatio: 0.04, commitRatio: 0.41, varApprovedRatio: 0.02, varPendingRatio: 0.015, etcRatio: 0.21 },
    { projectId: 'prj-salalah', totalOrig: 44_600_000, revisedFactor: 1.06, actualRatio: 0.24, accrualRatio: 0.03, commitRatio: 0.39, varApprovedRatio: 0.04, varPendingRatio: 0.035, etcRatio: 0.42 },
    { projectId: 'prj-sohar', totalOrig: 16_400_000, revisedFactor: 1.01, actualRatio: 0.93, accrualRatio: 0.02, commitRatio: 0.04, varApprovedRatio: 0.01, varPendingRatio: 0.002, etcRatio: 0.015 },
  ];

  const categories: { cat: ProjectBudgetLine['costCategory']; share: number }[] = [
    { cat: 'Land', share: 0.22 },
    { cat: 'Infrastructure', share: 0.12 },
    { cat: 'Substructure & Superstructure', share: 0.31 },
    { cat: 'MEP & Finishes', share: 0.19 },
    { cat: 'Consultancy & Design', share: 0.05 },
    { cat: 'Marketing & Sales', share: 0.04 },
    { cat: 'Capitalized Interest', share: 0.03 },
    { cat: 'Contingency', share: 0.04 },
  ];

  for (const pb of projectBudgets) {
    for (const c of categories) {
      const orig = roundOMR(pb.totalOrig * c.share);
      const rev = roundOMR(orig * pb.revisedFactor);
      const isLand = c.cat === 'Land';
      const actual = isLand ? orig : roundOMR(rev * pb.actualRatio);
      const accruals = isLand ? 0 : roundOMR(rev * pb.accrualRatio);
      const committed = isLand ? 0 : roundOMR(rev * pb.commitRatio);
      const etc = isLand ? 0 : roundOMR(rev * pb.etcRatio);

      lines.push({
        projectId: pb.projectId,
        costCategory: c.cat,
        originalBudgetOMR: orig,
        revisedBudgetOMR: rev,
        actualCostOMR: actual,
        accrualsOMR: accruals,
        committedContractsOMR: committed,
        approvedVariationsOMR: isLand ? 0 : roundOMR(rev * pb.varApprovedRatio),
        pendingVariationsOMR: isLand ? 0 : roundOMR(rev * pb.varPendingRatio),
        estimatedCostToCompleteOMR: etc,
      });
    }
  }

  return lines;
}

function generateConstructionLogs(periods: string[]): ConstructionProgressPoint[] {
  const logs: ConstructionProgressPoint[] = [];
  const profiles = [
    { projectId: 'prj-marina', startP: 18, endP: 66, lag: 3.5, totalBudget: 34_840_000, cpiBias: 0.97 },
    { projectId: 'prj-qurum', startP: 45, endP: 91, lag: 1.8, totalBudget: 42_024_000, cpiBias: 0.99 },
    { projectId: 'prj-plaza', startP: 8, endP: 49, lag: 0.8, totalBudget: 27_604_000, cpiBias: 1.01 },
    { projectId: 'prj-salalah', startP: 4, endP: 34, lag: 6.2, totalBudget: 47_276_000, cpiBias: 0.91 },
    { projectId: 'prj-sohar', startP: 62, endP: 98, lag: 0.5, totalBudget: 16_564_000, cpiBias: 1.02 },
  ];

  for (const prof of profiles) {
    for (let i = 0; i < periods.length; i++) {
      const t = i / (periods.length - 1);
      const planned = roundOMR(prof.startP + (prof.endP - prof.startP) * (3 * t ** 2 - 2 * t ** 3) * 0.3 + (prof.endP - prof.startP) * t * 0.7);
      const actual = roundOMR(Math.max(0, Math.min(100, planned - prof.lag * (0.4 + 0.6 * t))));
      const certified = roundOMR(Math.max(0, actual - 2.4));
      const financial = roundOMR(Math.max(0, actual + 1.8));
      const pv = roundOMR((planned / 100) * prof.totalBudget);
      const ev = roundOMR((actual / 100) * prof.totalBudget);
      const ac = roundOMR(ev / prof.cpiBias);

      logs.push({
        projectId: prof.projectId,
        period: periods[i],
        plannedPhysicalPct: planned,
        actualPhysicalPct: actual,
        certifiedProgressPct: certified,
        financialProgressPct: financial,
        plannedValueOMR: pv,
        earnedValueOMR: ev,
        actualCostOMR: ac,
      });
    }
  }
  return logs;
}

const CONTRACTORS: ContractorRecord[] = [
  {
    id: 'ctr-01',
    projectId: 'prj-marina',
    contractorName: 'Al Ansari Civil Engineering LLC',
    packageTitle: 'Main Building Works — Towers A–D',
    originalContractOMR: 18_400_000,
    approvedVariationsOMR: 620_000,
    pendingClaimsOMR: 485_000,
    certifiedToDateOMR: 10_920_000,
    paidToDateOMR: 9_828_000,
    advanceUnrecoveredOMR: 920_000,
    retentionHeldOMR: 1_092_000,
    performanceBondOMR: 1_840_000,
    status: 'Active',
  },
  {
    id: 'ctr-02',
    projectId: 'prj-qurum',
    contractorName: 'Galfar Engineering & Contracting SAOG',
    packageTitle: 'Villas Superstructure & Landscaping',
    originalContractOMR: 24_200_000,
    approvedVariationsOMR: 410_000,
    pendingClaimsOMR: 140_000,
    certifiedToDateOMR: 21_450_000,
    paidToDateOMR: 19_305_000,
    advanceUnrecoveredOMR: 240_000,
    retentionHeldOMR: 2_145_000,
    performanceBondOMR: 2_420_000,
    status: 'Near Completion',
  },
  {
    id: 'ctr-03',
    projectId: 'prj-plaza',
    contractorName: 'Douglas OHI Oman LLC',
    packageTitle: 'Commercial Towers Core, Facade & MEP',
    originalContractOMR: 16_800_000,
    approvedVariationsOMR: 290_000,
    pendingClaimsOMR: 210_000,
    certifiedToDateOMR: 7_420_000,
    paidToDateOMR: 6_678_000,
    advanceUnrecoveredOMR: 1_120_000,
    retentionHeldOMR: 742_000,
    performanceBondOMR: 1_680_000,
    status: 'Active',
  },
  {
    id: 'ctr-04',
    projectId: 'prj-salalah',
    contractorName: 'Strabag Oman LLC',
    packageTitle: 'Master Infrastructure & Coastal Roads',
    originalContractOMR: 21_500_000,
    approvedVariationsOMR: 940_000,
    pendingClaimsOMR: 1_180_000,
    certifiedToDateOMR: 6_840_000,
    paidToDateOMR: 6_156_000,
    advanceUnrecoveredOMR: 1_650_000,
    retentionHeldOMR: 684_000,
    performanceBondOMR: 2_150_000,
    status: 'Disputed',
  },
  {
    id: 'ctr-05',
    projectId: 'prj-sohar',
    contractorName: 'Towell Construction & Co.',
    packageTitle: 'Retail & Office Turnkey Package',
    originalContractOMR: 11_200_000,
    approvedVariationsOMR: 165_000,
    pendingClaimsOMR: 0,
    certifiedToDateOMR: 11_120_000,
    paidToDateOMR: 10_564_000,
    advanceUnrecoveredOMR: 0,
    retentionHeldOMR: 556_000,
    performanceBondOMR: 560_000,
    status: 'Closed',
  },
];

const FACILITIES: FinancingFacility[] = [
  {
    id: 'fac-01',
    companyId: 'cmp-almajd',
    projectId: 'prj-marina',
    lenderName: 'Bank Muscat Syndicated Facility',
    facilityType: 'Construction Murabaha',
    facilityLimitOMR: 22_000_000,
    drawnAmountOMR: 15_400_000,
    interestRatePct: 6.15,
    maturityDate: '2028-12',
    minDscrCovenant: 1.25,
    maxLtvCovenantPct: 60,
    maxLtcCovenantPct: 65,
    collateralValueOMR: 38_500_000,
    totalProjectCostOMR: 34_840_000,
    ebitdaAnnualizedOMR: 4_850_000,
    annualDebtServiceOMR: 3_120_000,
  },
  {
    id: 'fac-02',
    companyId: 'cmp-qurum',
    projectId: 'prj-qurum',
    lenderName: 'National Bank of Oman Term Loan',
    facilityType: 'Term Loan',
    facilityLimitOMR: 20_000_000,
    drawnAmountOMR: 16_200_000,
    interestRatePct: 5.85,
    maturityDate: '2027-09',
    minDscrCovenant: 1.25,
    maxLtvCovenantPct: 65,
    maxLtcCovenantPct: 70,
    collateralValueOMR: 44_000_000,
    totalProjectCostOMR: 42_024_000,
    ebitdaAnnualizedOMR: 4_120_000,
    annualDebtServiceOMR: 2_950_000,
  },
  {
    id: 'fac-03',
    companyId: 'cmp-almajd',
    projectId: 'prj-plaza',
    lenderName: 'Bank Dhofar Corporate Sukuk',
    facilityType: 'Sukuk Tranche',
    facilityLimitOMR: 15_000_000,
    drawnAmountOMR: 9_100_000,
    interestRatePct: 6.45,
    maturityDate: '2029-06',
    minDscrCovenant: 1.20,
    maxLtvCovenantPct: 55,
    maxLtcCovenantPct: 60,
    collateralValueOMR: 29_000_000,
    totalProjectCostOMR: 27_604_000,
    ebitdaAnnualizedOMR: 2_980_000,
    annualDebtServiceOMR: 2_210_000,
  },
  {
    id: 'fac-04',
    companyId: 'cmp-sohar',
    projectId: 'prj-sohar',
    lenderName: 'Sohar International Asset-Backed Loan',
    facilityType: 'Term Loan',
    facilityLimitOMR: 10_000_000,
    drawnAmountOMR: 8_100_000,
    interestRatePct: 5.5,
    maturityDate: '2030-03',
    minDscrCovenant: 1.30,
    maxLtvCovenantPct: 65,
    maxLtcCovenantPct: 65,
    collateralValueOMR: 19_200_000,
    totalProjectCostOMR: 16_564_000,
    ebitdaAnnualizedOMR: 2_380_000,
    annualDebtServiceOMR: 1_340_000,
  },
];

const RISKS: RiskItem[] = [
  {
    id: 'rsk-01',
    projectId: 'prj-salalah',
    companyId: 'cmp-qurum',
    category: 'Contractual',
    title: 'Coastal soil stabilization claim & variation dispute (Strabag Oman)',
    likelihood: 4,
    impact: 5,
    financialExposureOMR: 1_180_000,
    mitigationOwner: 'Commercial & QS Director',
    dueDate: '2026-12-20',
    status: 'Escalated',
  },
  {
    id: 'rsk-02',
    projectId: 'prj-plaza',
    companyId: 'cmp-almajd',
    category: 'Commercial',
    title: 'Corporate office tenant/buyer collection slippage in >90 days bucket',
    likelihood: 3,
    impact: 4,
    financialExposureOMR: 640_000,
    mitigationOwner: 'Head of Collections',
    dueDate: '2026-12-15',
    status: 'Mitigating',
  },
  {
    id: 'rsk-03',
    projectId: 'prj-marina',
    companyId: 'cmp-almajd',
    category: 'Construction',
    title: 'MEP chiller & elevator switchgear lead-time delay (8 weeks)',
    likelihood: 4,
    impact: 3,
    financialExposureOMR: 420_000,
    mitigationOwner: 'Project Director',
    dueDate: '2027-01-10',
    status: 'Open',
  },
  {
    id: 'rsk-04',
    projectId: null,
    companyId: 'cmp-almajd',
    category: 'Liquidity',
    title: 'Escrow milestone release lag impacting corporate working capital',
    likelihood: 3,
    impact: 4,
    financialExposureOMR: 1_250_000,
    mitigationOwner: 'Group Treasurer',
    dueDate: '2026-12-28',
    status: 'Mitigating',
  },
  {
    id: 'rsk-05',
    projectId: 'prj-qurum',
    companyId: 'cmp-qurum',
    category: 'Regulatory',
    title: 'Final municipality civil defense sign-off for Phase 3 Villa cluster',
    likelihood: 2,
    impact: 4,
    financialExposureOMR: 310_000,
    mitigationOwner: 'Regulatory Affairs Lead',
    dueDate: '2026-12-18',
    status: 'Mitigating',
  },
];

const HANDOVERS: HandoverWarrantyRecord[] = [
  {
    id: 'ho-01',
    projectId: 'prj-qurum',
    totalUnitsForHandover: 310,
    completionCertificateStatus: 'Partial',
    unitsHandedOver: 161,
    unitsInSnagging: 44,
    openWarrantyClaims: 18,
    resolvedWarrantyClaims: 94,
    dlpReserveOMR: 1_072_500,
    outstandingObligationsOMR: 285_000,
  },
  {
    id: 'ho-02',
    projectId: 'prj-sohar',
    totalUnitsForHandover: 180,
    completionCertificateStatus: 'Issued',
    unitsHandedOver: 130,
    unitsInSnagging: 8,
    openWarrantyClaims: 4,
    resolvedWarrantyClaims: 62,
    dlpReserveOMR: 556_000,
    outstandingObligationsOMR: 64_000,
  },
  {
    id: 'ho-03',
    projectId: 'prj-marina',
    totalUnitsForHandover: 420,
    completionCertificateStatus: 'In Progress',
    unitsHandedOver: 59,
    unitsInSnagging: 27,
    openWarrantyClaims: 6,
    resolvedWarrantyClaims: 19,
    dlpReserveOMR: 546_000,
    outstandingObligationsOMR: 195_000,
  },
];

const RENTALS: RentalLeaseRecord[] = [
  {
    id: 'rnt-01',
    projectId: 'prj-sohar',
    propertyName: 'Sohar Business Gate — Retail & Logistics Podium',
    leasableSqm: 14_500,
    occupiedSqm: 13_340,
    annualPassingRentOMR: 1_385_000,
    operatingExpensesOMR: 215_000,
    propertyFairValueOMR: 14_500_000,
    tenantArrearsOMR: 48_500,
    expiringWithin12MonthsPct: 14.5,
  },
  {
    id: 'rnt-02',
    projectId: 'prj-marina',
    propertyName: 'Al Mouj Marina Promenade Retail',
    leasableSqm: 7_800,
    occupiedSqm: 7_020,
    annualPassingRentOMR: 1_120_000,
    operatingExpensesOMR: 180_000,
    propertyFairValueOMR: 11_200_000,
    tenantArrearsOMR: 31_200,
    expiringWithin12MonthsPct: 8.2,
  },
];

const DEFAULT_POLICIES: AccountingPolicyConfig = {
  ifrs15OverTimeThresholdPct: 20,
  ifrs9EclStage1Pct: 0.75,
  ifrs9EclStage2Pct: 4.5,
  ifrs9EclStage3Pct: 35.0,
  ias2NrvHaircutThresholdPct: 5.0,
  ias23CapitalizeBorrowingCosts: true,
  ias40FairValueModel: true,
  omanVatRatePct: 5.0,
  omanCorporateTaxRatePct: 15.0,
  omanWithholdingTaxPct: 10.0,
  materialityThresholdOMR: 500.0,
};

const GL_MAPPINGS: GlMappingRule[] = [
  { id: 'map-1010', accountCode: '1010', accountNamePattern: 'Corporate Operating Bank', targetClass: 'CashUnrestricted', defaultProjectId: null, allocationRule: 'Direct', approvedBy: 'CFO', updatedAt: '2026-01-05' },
  { id: 'map-1020', accountCode: '1020', accountNamePattern: 'Escrow Account', targetClass: 'CashEscrow', defaultProjectId: null, allocationRule: 'Direct Project', approvedBy: 'CFO', updatedAt: '2026-01-05' },
  { id: 'map-1210', accountCode: '1210', accountNamePattern: 'Customer Receivable', targetClass: 'Receivables', defaultProjectId: null, allocationRule: 'Unit Sub-ledger', approvedBy: 'Controller', updatedAt: '2026-01-05' },
  { id: 'map-1250', accountCode: '1250', accountNamePattern: 'Contract Asset', targetClass: 'ContractAsset', defaultProjectId: null, allocationRule: 'IFRS 15 PoC', approvedBy: 'CFO', updatedAt: '2026-01-05' },
  { id: 'map-1310', accountCode: '1310', accountNamePattern: 'Development WIP', targetClass: 'InventoryWIP', defaultProjectId: null, allocationRule: 'Project Cost Centre', approvedBy: 'Controller', updatedAt: '2026-01-05' },
  { id: 'map-2110', accountCode: '2110', accountNamePattern: 'Customer Advances', targetClass: 'CustomerAdvances', defaultProjectId: null, allocationRule: 'Unit Sub-ledger', approvedBy: 'Controller', updatedAt: '2026-01-05' },
  { id: 'map-4010', accountCode: '4010', accountNamePattern: 'Development Revenue', targetClass: 'Revenue', defaultProjectId: null, allocationRule: 'IFRS 15 Policy', approvedBy: 'CFO', updatedAt: '2026-01-05' },
  { id: 'map-5010', accountCode: '5010', accountNamePattern: 'Cost of Sales', targetClass: 'COGS', defaultProjectId: null, allocationRule: 'PoC Cost Match', approvedBy: 'Controller', updatedAt: '2026-01-05' },
];

export function createSeedDataset(): MisDataset {
  const periods = build24Periods();
  const units = generate1560Units(periods);
  const trialBalance = generateTrialBalance24Months(periods);
  const budgets = generateBudgets();
  const constructionLogs = generateConstructionLogs(periods);

  const workflows: PeriodWorkflowState[] = periods.map((p, idx) => {
    const isLatest = idx === periods.length - 1;
    return {
      period: p,
      stage: isLatest ? 'ExceptionReview' : 'Locked',
      tbUploaded: true,
      schedulesCompleted: isLatest ? 10 : 11,
      schedulesTotal: 11,
      reconciled: true,
      openExceptions: isLatest ? 2 : 0,
      preparedBy: 'Tariq Al Maskari (Financial Controller)',
      approvedBy: isLatest ? null : 'Nasser Al Harthy (Group CFO)',
      lockedAt: isLatest ? null : `${p}-28T17:30:00Z`,
      departmentalComments: isLatest
        ? [
            {
              department: 'Quantity Surveying',
              author: 'Eng. Khalid Al Riyami',
              comment: 'Salalah infrastructure pending claim OMR 1.18M under commercial review; not accrued in EAC.',
              timestamp: '2026-11-24T11:20:00Z',
            },
            {
              department: 'Treasury',
              author: 'Maha Al Balushi',
              comment: 'Escrow IPC #14 release of OMR 1.42M submitted to Bank Muscat; expected settlement Dec 4.',
              timestamp: '2026-11-25T09:15:00Z',
            },
          ]
        : [],
    };
  });

  return {
    companies: COMPANIES,
    projects: PROJECTS,
    units,
    periods,
    trialBalance,
    glMappings: GL_MAPPINGS,
    budgets,
    contractors: CONTRACTORS,
    constructionLogs,
    facilities: FACILITIES,
    risks: RISKS,
    handovers: HANDOVERS,
    rentals: RENTALS,
    policies: DEFAULT_POLICIES,
    adjustments: [
      {
        id: 'adj-001',
        period: '2026-11',
        companyId: 'cmp-almajd',
        projectId: 'prj-marina',
        description: 'Accrue November MEP certified works awaiting invoice',
        debitAccountClass: 'COGS',
        creditAccountClass: 'Payables',
        amountOMR: 145_000,
        preparedBy: 'Financial Controller',
        approvedBy: 'Group CFO',
        status: 'Approved',
        createdAt: '2026-11-24T14:00:00Z',
      },
    ],
    workflows,
    auditLogs: [
      {
        id: 'aud-01',
        timestamp: '2026-11-25T08:30:00Z',
        actor: 'Tariq Al Maskari',
        role: 'Finance_Controller',
        action: 'TB_UPLOAD_RECONCILED',
        entity: 'Period 2026-11',
        details: 'Uploaded consolidated Trial Balance for 3 companies (0.000 OMR variance).',
      },
      {
        id: 'aud-02',
        timestamp: '2026-11-25T09:05:00Z',
        actor: 'Nasser Al Harthy',
        role: 'CFO_Admin',
        action: 'ADJUSTMENT_APPROVED',
        entity: 'ADJ-001',
        details: 'Approved OMR 145.000K MEP accrual on Al Mouj Marina Terraces.',
      },
    ],
    license: {
      deviceId: 'RE360-WIN64-9F42-8B1A',
      edition: 'Permanent',
      status: 'Active',
      trialStartedAt: '2026-10-01T00:00:00Z',
      expiresAt: null,
      licensedTo: 'Al Majd Urban Developments LLC (Enterprise Edition)',
      signatureHash: 'SIG-SHA256-48A9E1C70B33F2',
    },
    backups: [
      {
        id: 'bak-01',
        filename: 'realestate360_auto_2026-11-25.db',
        createdAt: '2026-11-25T02:00:00Z',
        sizeBytes: 4_829_184,
        type: 'Automatic',
        checksum: 'sha256:88c1e9f012a4',
      },
    ],
  };
}
