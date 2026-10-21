import Decimal from 'decimal.js';
import {
  Supplier,
  Customer,
  Item,
  BankAccount,
  PettyCashFund,
  AssetCategory,
  Requisition,
  PurchaseOrder,
  Receipt,
  InventoryBalance,
  APInvoice,
  APPayment,
  ARTransaction,
  ARReceipt,
  FixedAsset,
  AssetSourceLine,
  DepreciationRun,
  CashVoucher,
  BankStatement,
  ICTransaction,
  GLJournal,
  Notification,
} from '../core/types';
import { BUSINESS_UNITS } from './businessUnits';
import { round2, addMoney, subMoney } from '../core/currency';
import { resetSequences } from '../core/sequences';
import { DatabaseState, saveDb } from '../core/storage';
import { ENRICHED_CHART_OF_ACCOUNTS } from './chartOfAccounts';

// Mulberry32 deterministic PRNG
function createPRNG(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function generateSeedData(): DatabaseState {
  const rng = createPRNG(2026);
  const randInt = (min: number, max: number) => Math.floor(rng() * (max - min + 1)) + min;
  const randChoice = <T>(arr: T[]): T => arr[Math.floor(rng() * arr.length)];

  // 1. Asset Categories
  const assetCategories: AssetCategory[] = [
    { id: 'AC-BLD', name: 'Buildings', costAccount: '1710', accumDepAccount: '1810', depExpenseAccount: '6300', usefulLifeYears: 25, depMethod: 'Straight Line', residualValuePercentage: 0 },
    { id: 'AC-LHI', name: 'Leasehold Improvements', costAccount: '1720', accumDepAccount: '1820', depExpenseAccount: '6300', usefulLifeYears: 10, depMethod: 'Straight Line', residualValuePercentage: 0 },
    { id: 'AC-MED', name: 'Medical Equipment', costAccount: '1730', accumDepAccount: '1830', depExpenseAccount: '6300', usefulLifeYears: 8, depMethod: 'Straight Line', residualValuePercentage: 0 },
    { id: 'AC-FUR', name: 'Furniture and Fixtures', costAccount: '1740', accumDepAccount: '1840', depExpenseAccount: '6300', usefulLifeYears: 5, depMethod: 'Straight Line', residualValuePercentage: 0 },
    { id: 'AC-ITE', name: 'IT Equipment', costAccount: '1750', accumDepAccount: '1850', depExpenseAccount: '6300', usefulLifeYears: 4, depMethod: 'Straight Line', residualValuePercentage: 0 },
    { id: 'AC-VEH', name: 'Vehicles', costAccount: '1760', accumDepAccount: '1860', depExpenseAccount: '6300', usefulLifeYears: 5, depMethod: 'Straight Line', residualValuePercentage: 0 },
    { id: 'AC-HVAC', name: 'Plant, HVAC and Electrical', costAccount: '1770', accumDepAccount: '1870', depExpenseAccount: '6300', usefulLifeYears: 10, depMethod: 'Straight Line', residualValuePercentage: 0 },
  ];

  // 2. Bank Accounts & Petty Cash Funds per BU
  const bankAccounts: BankAccount[] = [];
  const pettyCashFunds: PettyCashFund[] = [];

  BUSINESS_UNITS.forEach((bu, idx) => {
    bankAccounts.push({
      accountCode: '1020',
      name: `${bu.name} - Operating Account`,
      bankName: 'First Abu Dhabi Bank (FAB)',
      accountNumber: `FAB-${bu.code}-9021${idx + 1}`,
      iban: `AE02033000001020000${bu.code}`,
      businessUnit: bu.code,
      currency: 'AED',
      currentBalance: 850000,
    });
    bankAccounts.push({
      accountCode: '1030',
      name: `${bu.name} - Collections Account`,
      bankName: 'Emirates NBD',
      accountNumber: `ENBD-${bu.code}-4512${idx + 1}`,
      iban: `AE03033000001030000${bu.code}`,
      businessUnit: bu.code,
      currency: 'AED',
      currentBalance: 420000,
    });
    pettyCashFunds.push({
      id: `PCF-${bu.code}`,
      businessUnit: bu.code,
      custodian: `${bu.type} Cashier Desk`,
      imprestLimit: bu.type === 'Hospital' ? 15000 : bu.type === 'Clinic' ? 8000 : 5000,
      currentBalance: bu.type === 'Hospital' ? 12450 : bu.type === 'Clinic' ? 6800 : 4200,
      account: '1010',
    });
  });

  // 3. 40 Realistic Healthcare Suppliers
  const supplierCategories = [
    'Pharmaceuticals', 'Medical Equipment', 'Consumables', 'Facility Services', 'Utilities', 'IT & Telecom', 'Professional Services'
  ] as const;

  const supplierNames = [
    'Gulf Pharmaceutical Industries (Julphar)', 'Modern Pharmaceutical LLC', 'AstraZeneca Gulf FZ',
    'Pfizer Middle East', 'Novartis Pharma Services', 'Sanofi-Aventis Gulf', 'Roche Diagnostics Middle East',
    'GE HealthCare UAE', 'Siemens Healthineers ME', 'Philips Medical Systems ME', 'Medtronic Arab Health',
    'B. Braun Medical Gulf', 'Stryker Middle East', 'Johnson & Johnson Medical', 'Al Hayat Pharmaceuticals',
    'Leader Healthcare LLC', 'Al Khayyat Medical Supplies', 'Gulf Medical Projects', 'Abbott Laboratories UAE',
    'Baxter Healthcare FZ', 'Bio-Rad Laboratories Gulf', 'Dubai Electricity & Water Authority (DEWA)',
    'Abu Dhabi Distribution Company (ADDC)', 'Etisalat by e&', 'du Telecom PJSC', 'Emirates Gas LLC',
    'Sharjah Electricity & Water (SEWA)', 'Rentokil Initial Hygiene', 'G4S Security Services UAE',
    'Dulsco Waste & Facility Solutions', 'Transguard Group Facilities', 'KPMG Lower Gulf Advisory',
    'PwC Middle East Healthcare', 'Ernst & Young Healthcare Audit', 'Al Futtaim Engineering (HVAC)',
    'Alpha Biomedical Calibration', 'Bin Moosa & Daly Water Systems', 'Canon Medical Systems ME',
    'Olympus Middle East Medical', '3M Gulf Health Care Division'
  ];

  const suppliers: Supplier[] = supplierNames.map((name, i) => {
    const isUtilityOrService = name.includes('DEWA') || name.includes('ADDC') || name.includes('SEWA') || name.includes('Etisalat') || name.includes('du Telecom') || name.includes('PwC') || name.includes('KPMG');
    let cat: typeof supplierCategories[number] = 'Pharmaceuticals';
    if (name.includes('Equipment') || name.includes('GE') || name.includes('Siemens') || name.includes('Philips') || name.includes('Canon') || name.includes('Olympus')) cat = 'Medical Equipment';
    else if (name.includes('Consumables') || name.includes('Braun') || name.includes('Johnson') || name.includes('3M')) cat = 'Consumables';
    else if (name.includes('Security') || name.includes('Facility') || name.includes('Waste') || name.includes('Hygiene') || name.includes('Al Futtaim')) cat = 'Facility Services';
    else if (name.includes('DEWA') || name.includes('ADDC') || name.includes('SEWA') || name.includes('Gas')) cat = 'Utilities';
    else if (name.includes('Etisalat') || name.includes('du Telecom')) cat = 'IT & Telecom';
    else if (name.includes('PwC') || name.includes('KPMG') || name.includes('Audit')) cat = 'Professional Services';

    return {
      id: `SUP-${String(i + 1).padStart(4, '0')}`,
      code: `VEND-${1000 + i}`,
      name,
      trn: `10045678900${String(i + 1).padStart(4, '0')}`,
      paymentTerms: isUtilityOrService ? 'Immediate' : 'Net 30',
      bankName: 'First Abu Dhabi Bank',
      bankIban: `AE99033000000000${10000000 + i}`,
      category: cat,
      sites: ['Abu Dhabi HQ', 'Dubai Logistics Hub'],
      poNotRequired: isUtilityOrService,
      status: 'Active',
    };
  });

  // 4. 40 Realistic Healthcare Customers
  const customerNames = [
    'Daman Health Insurance (National Health)', 'Thiqa Healthcare Program', 'NextCare Health Insurance',
    'Oman Insurance Company (Sukoon)', 'AXA Gulf Health Insurance (GIG)', 'Cigna Global Insurance ME',
    'MetLife Middle East Healthcare', 'MedNet UAE Health Solutions', 'Al Buhaira National Insurance',
    'Emirates Insurance Company', 'Dubai Insurance Company', 'ADNOC Corporate Health Program',
    'Emirates Airlines Staff Medical', 'Etihad Airways Medical Scheme', 'Dubai Islamic Bank Staff Health',
    'First Abu Dhabi Bank Corporate Health', 'DP World Corporate Care', 'Emaar Properties Healthcare Plan',
    'Aldar Properties Corporate Health', 'Emirates Global Aluminium Health', 'Ministry of Health & Prevention (MOHAP)',
    'Dubai Health Authority (DHA)', 'Department of Health Abu Dhabi (DOH)', 'Sharjah Health Authority',
    'Zayed Military Hospital Referral', 'Sheikh Khalifa Medical Referral', 'Private Patient Self-Pay A/C',
    'International Medical Tourists Group', 'Al Futtaim Private Healthcare', 'Al Naboodah Corporate Care',
    'Sobha Realty Executive Wellness', 'DAMAC Employee Medical Welfare', 'Dubai Airports Health Program',
    'Mubadala Health Referral Network', 'ADQ Executive Health Network', 'Al Jaber Group Employee Care',
    'Arabtec Construction Medical Trust', 'Chalhoub Group Wellness Care', 'Majid Al Futtaim Employee Care',
    'Apparel Group Staff Healthcare'
  ];

  const customers: Customer[] = customerNames.map((name, i) => {
    let type: Customer['type'] = 'Insurance';
    if (name.includes('Corporate') || name.includes('Airlines') || name.includes('Staff') || name.includes('Group') || name.includes('Employee') || name.includes('Properties')) type = 'Corporate';
    else if (name.includes('Ministry') || name.includes('Authority') || name.includes('Referral') || name.includes('Military')) type = 'Government';
    else if (name.includes('Patient') || name.includes('Tourists')) type = 'Patient';

    return {
      id: `CUST-${String(i + 1).padStart(4, '0')}`,
      code: `CUST-${2000 + i}`,
      name,
      type,
      trn: type !== 'Patient' ? `10088899900${String(i + 1).padStart(4, '0')}` : undefined,
      paymentTerms: type === 'Patient' ? 'Immediate' : 'Net 45',
      creditLimitAED: type === 'Insurance' ? 5000000 : type === 'Corporate' ? 1000000 : 50000,
      currentBalanceAED: randInt(15000, 250000),
      status: 'Active',
    };
  });

  // 5. 120 Realistic Medical Items across classes
  const pharmaItems = [
    'Paracetamol IV 1000mg/100ml Infusion', 'Amoxicillin + Clavulanic Acid 1.2g IV', 'Ceftriaxone 1g Powder for Injection',
    'Enoxaparin Sodium 40mg/0.4ml Prefilled Syringe', 'Insulin Glargine 100 U/ml SoloStar Pen', 'Meropenem 1g IV Injection',
    'Atorvastatin 20mg Tablets (30s)', 'Omeprazole 40mg IV Injection', 'Fentanyl Citrate 100mcg/2ml Ampoules',
    'Propofol 1% 20ml Injectable Emulsion', 'Morphine Sulphate 10mg/ml Ampoule', 'Pantoprazole 40mg Tablets (28s)',
    'Metformin 500mg Tablets (100s)', 'Salbutamol Inhaler 100mcg/dose', 'Heparin Sodium 5000 IU/ml Vial',
    'Furosemide 20mg/2ml Ampoules', 'Midazolam 5mg/ml Injection', 'Tranexamic Acid 500mg/5ml Ampoule',
    'Sodium Chloride 0.9% 500ml Infusion Bag', 'Ringer Lactate Solution 500ml IV', 'Dextrose 5% 500ml IV Infusion',
    'Diclofenac Sodium 75mg/3ml Ampoule', 'Ondansetron 4mg/2ml Ampoule', 'Lidocaine 2% 20ml Multi-dose Vial',
    'Ciprofloxacin 500mg Film-coated Tablets', 'Azithromycin 500mg Tablets', 'Hydrocortisone 100mg IV Injection',
    'Adrenaline (Epinephrine) 1:1000 1mg/ml Ampoule', 'Atropine Sulphate 1mg/ml Ampoule', 'Ketamine 50mg/ml 10ml Vial',
    'Sevoflurane 250ml Inhalation Anaesthetic', 'Potassium Chloride 15% 10ml Concentrated Infusion'
  ];

  const consumableItems = [
    'Sterile Surgical Gloves Size 7.5 (Box of 50)', 'Nitrile Examination Gloves Medium (Box 100)', 'Disposable Surgical Face Mask 3-Ply (Box 50)',
    'IV Cannula 20G Pink with Port (Box 50)', 'IV Infusion Giving Set with Luer Lock', 'Disposable Syringe 5ml with Needle (Box 100)',
    'Sterile Gauze Swabs 10x10cm 8-ply (Pack 100)', 'Non-woven Surgical Drapes Sterile 150x200cm', 'Suction Catheter 12FG with Thumb Control',
    'Endotracheal Tube Cuffed Size 7.5', 'Foley Balloon Catheter 2-Way 16Fr 30ml', 'Urine Drainage Bag 2000ml with Anti-reflux',
    'Blood Collection Tubes EDTA K2 4ml (Rack 100)', 'Serum Gel Separator Tubes 5ml (Rack 100)', 'Adhesive Wound Dressing Waterproof 10x15cm',
    'Hypodermic Needles 21G Green (Box 100)', 'Lancets Sterile Single-Use Safety (Box 200)', 'Scalpel Blade No. 10 Carbon Steel (Box 100)',
    'Silk Suture 2-0 with Cutting Needle', 'Vicryl Polyglactin Suture 3-0 75cm', 'Surgical Gown Disposable Reinforced Sterile (XL)',
    'Electrocardiogram (ECG) Electrodes Disposable (Pack 50)', 'Pulse Oximeter Disposable Finger Sensor Adult', 'Alcohol Prep Pads Sterile (Box 200)'
  ];

  const implantItems = [
    'Total Knee Replacement Femoral Component CoCr Size 4', 'Total Knee Tibial Tray Titanium Modular Size 4', 'Total Hip Acetabular Cup Plasma Porous 52mm',
    'Total Hip Femoral Stem Cementless Size 11', 'Dual Mobility Ceramic Femoral Head 36mm', 'Coronary Drug-Eluting Stent Sirolimus 3.0x18mm',
    'Coronary Balloon Dilatation Catheter NC 3.0x12mm', 'Spinal Pedicle Screw Polyaxial Titanium 6.5x45mm', 'Anterior Cervical Interbody Fusion PEEK Cage 6mm',
    'Intramedullary Interlocking Femoral Nail 10x380mm', 'Titanium Distal Radius Volar Locking Plate 2.4mm', 'Permanent Dual-Chamber Cardiac Pacemaker',
    'Intraocular Foldable Hydrophobic Acrylic Lens +21.0D', 'Biological Heart Valve Pericardial Mitral 29mm', 'Synthetic Surgical Hernia Mesh Polypropylene 15x15cm',
    'Absorbable Hemostatic Gelatin Sponge 8x5x1cm'
  ];

  const generalItems = [
    'Medical Autoclave Sterilizer Indicator Strips (Box 250)', 'Biohazard Waste Disposal Bags 50 Litres Yellow (Roll 50)',
    'Sharps Disposal Container 5 Litres Puncture Resistant', 'Hospital Bed Linen Fitted Sheet Cotton White',
    'Patient Gown Overlap Back Navy Blue', 'Thermal Ultrasound Print Paper Roll Type HD', 'X-Ray Protective Lead Apron 0.5mm Pb Equivalent',
    'Hand Sanitizer Rub 70% Isopropanol 500ml Dispenser', 'Surface Disinfectant Hospital Grade 5 Litres Conc.', 'Disposable Bed Underpads Ultra Absorbent 60x90cm (Pack 30)'
  ];

  const capitalAssetItems = [
    'GE Revolution 256-Slice Dual Energy CT Scanner Unit', 'Siemens Magnetom Vida 3.0T MRI Diagnostic System',
    'Philips Azurion 7 Biplane Cath Lab Angiography Unit', 'Mindray Resona 7 High-End Diagnostic Ultrasound Machine',
    'Drager Perseus A500 Advanced Anaesthesia Workstation', 'Stryker 1688 AIM 4K Endoscopy Laparoscopy Video Tower',
    'Maquet Alphamaquet Hydraulic Modular Operating Table', 'Getinge Clean Care Steam Autoclave Sterilizer 450L',
    'Roche Cobas 8000 Modular Integrated Chemistry Analyzer', 'Sysmex XN-1000 Automated Hematology Analysis System'
  ];

  const serviceItems = [
    'Biomedical Preventive Maintenance & Calibration Service', 'Hospital Linen & Laundry Cleaning Service Contract',
    'Clinical Hazardous Waste Incineration Disposal Service', 'HVAC HEPA Filtration Air Quality Certification'
  ];

  const items: Item[] = [];
  let itemCounter = 1;

  pharmaItems.forEach((desc) => {
    const cost = randInt(15, 350);
    items.push({
      code: `ITM-PH-${String(itemCounter++).padStart(4, '0')}`,
      description: desc,
      itemClass: 'Pharmaceutical',
      uom: desc.includes('Box') ? 'Box' : desc.includes('Infusion') ? 'Bag' : desc.includes('Tablet') ? 'Pack' : 'Vial',
      unitPrice: round2(cost * 1.35),
      weightedAvgCost: cost,
      reorderLevel: 50,
      expiryTracked: true,
      status: 'Active',
    });
  });

  consumableItems.forEach((desc) => {
    const cost = randInt(5, 120);
    items.push({
      code: `ITM-CS-${String(itemCounter++).padStart(4, '0')}`,
      description: desc,
      itemClass: 'Consumable',
      uom: desc.includes('Box') ? 'Box' : desc.includes('Pack') ? 'Pack' : 'Each',
      unitPrice: round2(cost * 1.3),
      weightedAvgCost: cost,
      reorderLevel: 100,
      expiryTracked: false,
      status: 'Active',
    });
  });

  implantItems.forEach((desc) => {
    const cost = randInt(1200, 18000);
    items.push({
      code: `ITM-IMP-${String(itemCounter++).padStart(4, '0')}`,
      description: desc,
      itemClass: 'Implants & Surgical',
      uom: 'Each',
      unitPrice: round2(cost * 1.25),
      weightedAvgCost: cost,
      reorderLevel: 5,
      expiryTracked: true,
      status: 'Active',
    });
  });

  generalItems.forEach((desc) => {
    const cost = randInt(25, 450);
    items.push({
      code: `ITM-GEN-${String(itemCounter++).padStart(4, '0')}`,
      description: desc,
      itemClass: 'General',
      uom: desc.includes('Box') ? 'Box' : desc.includes('Roll') ? 'Roll' : 'Each',
      unitPrice: round2(cost * 1.2),
      weightedAvgCost: cost,
      reorderLevel: 30,
      expiryTracked: false,
      status: 'Active',
    });
  });

  capitalAssetItems.forEach((desc) => {
    const cost = randInt(180000, 1850000);
    items.push({
      code: `ITM-EQ-${String(itemCounter++).padStart(4, '0')}`,
      description: desc,
      itemClass: 'Capital Asset',
      uom: 'Each',
      unitPrice: cost,
      weightedAvgCost: cost,
      reorderLevel: 1,
      expiryTracked: false,
      status: 'Active',
    });
  });

  serviceItems.forEach((desc) => {
    const cost = randInt(5000, 45000);
    items.push({
      code: `ITM-SRV-${String(itemCounter++).padStart(4, '0')}`,
      description: desc,
      itemClass: 'Service',
      uom: 'Session',
      unitPrice: cost,
      weightedAvgCost: cost,
      reorderLevel: 0,
      expiryTracked: false,
      status: 'Active',
    });
  });

  // 6. On-hand Inventory balances
  const inventoryBalances: InventoryBalance[] = [];
  BUSINESS_UNITS.forEach((bu) => {
    items.forEach((itm) => {
      if (itm.itemClass === 'Pharmaceutical' || itm.itemClass === 'Consumable' || itm.itemClass === 'Implants & Surgical') {
        const qty = randInt(15, 250);
        inventoryBalances.push({
          businessUnit: bu.code,
          subInventory: bu.type === 'Pharmacy' ? 'Pharmacy' : bu.type === 'Hospital' ? 'Main Store' : 'Main Store',
          itemCode: itm.code,
          quantityOnHand: qty,
          weightedAvgCost: itm.weightedAvgCost,
          batchNumber: `BAT-2026-${randInt(100, 999)}`,
          expiryDate: '2028-12-31',
        });
      }
    });
  });

  // 7. GL Journals array: initialize opening balances for all 15 BUs
  const glJournals: GLJournal[] = [];

  // Opening Balances as of 01/Jan/2026 per BU
  BUSINESS_UNITS.forEach((bu, i) => {
    const isHosp = bu.type === 'Hospital';
    const isClin = bu.type === 'Clinic';
    const scale = isHosp ? 1 : isClin ? 0.35 : 0.15;

    const cash = round2(50000 * scale);
    const pettyCash = round2(15000 * scale);
    const bankOp = round2(1200000 * scale);
    const bankCol = round2(800000 * scale);
    const arPatients = round2(450000 * scale);
    const arInsurance = round2(1600000 * scale);
    const arCorp = round2(350000 * scale);
    const arECL = round2(85000 * scale); // credit
    const invPharma = round2(900000 * scale);
    const invConsum = round2(400000 * scale);
    const invImplants = round2(isHosp ? 650000 : 0);
    const invGeneral = round2(120000 * scale);
    const prepay = round2(150000 * scale);

    // PPE
    const bldCost = round2(isHosp ? 25000000 : 0);
    const lhiCost = round2(isHosp ? 0 : 2500000 * scale);
    const medCost = round2(12000000 * scale);
    const furCost = round2(800000 * scale);
    const itCost = round2(950000 * scale);
    const vehCost = round2(isHosp ? 450000 : 0);
    const hvacCost = round2(1800000 * scale);

    const bldDep = round2(bldCost * 0.2);
    const lhiDep = round2(lhiCost * 0.3);
    const medDep = round2(medCost * 0.25);
    const furDep = round2(furCost * 0.3);
    const itDep = round2(itCost * 0.4);
    const vehDep = round2(vehCost * 0.3);
    const hvacDep = round2(hvacCost * 0.2);

    // Liabilities
    const ap = round2(1400000 * scale);
    const grni = round2(180000 * scale);
    const accruedExp = round2(220000 * scale);
    const vatOut = round2(95000 * scale);
    const accruedSal = round2(450000 * scale);
    const eosb = round2(1200000 * scale);
    const loans = round2(isHosp ? 8000000 : 0);

    // Equity: Balancing figure
    let totalDebit = cash + pettyCash + bankOp + bankCol + arPatients + arInsurance + arCorp + invPharma + invConsum + invImplants + invGeneral + prepay + bldCost + lhiCost + medCost + furCost + itCost + vehCost + hvacCost;
    let totalCreditBeforeEquity = arECL + bldDep + lhiDep + medDep + furDep + itDep + vehDep + hvacDep + ap + grni + accruedExp + vatOut + accruedSal + eosb + loans;

    const netEquity = round2(totalDebit - totalCreditBeforeEquity);
    const shareCapital = round2(netEquity * 0.6);
    const retainedEarnings = round2(netEquity - shareCapital);

    const jLines = [
      { lineNumber: 1, businessUnit: bu.code, account: '1000', debit: cash, credit: 0, description: 'Opening Balance - Cash on Hand', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 2, businessUnit: bu.code, account: '1010', debit: pettyCash, credit: 0, description: 'Opening Balance - Petty Cash', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 3, businessUnit: bu.code, account: '1020', debit: bankOp, credit: 0, description: 'Opening Balance - Bank Operating', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 4, businessUnit: bu.code, account: '1030', debit: bankCol, credit: 0, description: 'Opening Balance - Bank Collections', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 5, businessUnit: bu.code, account: '1100', debit: arPatients, credit: 0, description: 'Opening Balance - AR Patients', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 6, businessUnit: bu.code, account: '1110', debit: arInsurance, credit: 0, description: 'Opening Balance - AR Insurance', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 7, businessUnit: bu.code, account: '1120', debit: arCorp, credit: 0, description: 'Opening Balance - AR Corporate', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 8, businessUnit: bu.code, account: '1190', debit: 0, credit: arECL, description: 'Opening Balance - ECL Allowance', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 9, businessUnit: bu.code, account: '1200', debit: invPharma, credit: 0, description: 'Opening Balance - Pharma Inventory', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 10, businessUnit: bu.code, account: '1210', debit: invConsum, credit: 0, description: 'Opening Balance - Consumables Inventory', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      ...(invImplants > 0 ? [{ lineNumber: 11, businessUnit: bu.code, account: '1220', debit: invImplants, credit: 0, description: 'Opening Balance - Implants Inventory', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' }] : []),
      { lineNumber: 12, businessUnit: bu.code, account: '1230', debit: invGeneral, credit: 0, description: 'Opening Balance - General Inventory', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 13, businessUnit: bu.code, account: '1300', debit: prepay, credit: 0, description: 'Opening Balance - Prepayments', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      ...(bldCost > 0 ? [{ lineNumber: 14, businessUnit: bu.code, account: '1710', debit: bldCost, credit: 0, description: 'Opening Balance - Buildings Cost', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' }] : []),
      ...(lhiCost > 0 ? [{ lineNumber: 15, businessUnit: bu.code, account: '1720', debit: lhiCost, credit: 0, description: 'Opening Balance - Leasehold Improvements', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' }] : []),
      { lineNumber: 16, businessUnit: bu.code, account: '1730', debit: medCost, credit: 0, description: 'Opening Balance - Medical Equipment Cost', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 17, businessUnit: bu.code, account: '1740', debit: furCost, credit: 0, description: 'Opening Balance - Furniture Cost', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 18, businessUnit: bu.code, account: '1750', debit: itCost, credit: 0, description: 'Opening Balance - IT Equipment Cost', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      ...(vehCost > 0 ? [{ lineNumber: 19, businessUnit: bu.code, account: '1760', debit: vehCost, credit: 0, description: 'Opening Balance - Vehicles Cost', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' }] : []),
      { lineNumber: 20, businessUnit: bu.code, account: '1770', debit: hvacCost, credit: 0, description: 'Opening Balance - HVAC Cost', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      ...(bldDep > 0 ? [{ lineNumber: 21, businessUnit: bu.code, account: '1810', debit: 0, credit: bldDep, description: 'Opening Accum Dep - Buildings', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' }] : []),
      ...(lhiDep > 0 ? [{ lineNumber: 22, businessUnit: bu.code, account: '1820', debit: 0, credit: lhiDep, description: 'Opening Accum Dep - Leasehold', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' }] : []),
      { lineNumber: 23, businessUnit: bu.code, account: '1830', debit: 0, credit: medDep, description: 'Opening Accum Dep - Medical Equipment', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 24, businessUnit: bu.code, account: '1840', debit: 0, credit: furDep, description: 'Opening Accum Dep - Furniture', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 25, businessUnit: bu.code, account: '1850', debit: 0, credit: itDep, description: 'Opening Accum Dep - IT Equipment', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      ...(vehDep > 0 ? [{ lineNumber: 26, businessUnit: bu.code, account: '1860', debit: 0, credit: vehDep, description: 'Opening Accum Dep - Vehicles', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' }] : []),
      { lineNumber: 27, businessUnit: bu.code, account: '1870', debit: 0, credit: hvacDep, description: 'Opening Accum Dep - HVAC', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 28, businessUnit: bu.code, account: '2000', debit: 0, credit: ap, description: 'Opening Balance - Trade Payables', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 29, businessUnit: bu.code, account: '2010', debit: 0, credit: grni, description: 'Opening Balance - GRNI Accrual', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 30, businessUnit: bu.code, account: '2020', debit: 0, credit: accruedExp, description: 'Opening Balance - Accrued Expenses', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 31, businessUnit: bu.code, account: '2100', debit: 0, credit: vatOut, description: 'Opening Balance - VAT Output', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 32, businessUnit: bu.code, account: '2200', debit: 0, credit: accruedSal, description: 'Opening Balance - Accrued Salaries', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 33, businessUnit: bu.code, account: '2210', debit: 0, credit: eosb, description: 'Opening Balance - End of Service Benefits', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      ...(loans > 0 ? [{ lineNumber: 34, businessUnit: bu.code, account: '2710', debit: 0, credit: loans, description: 'Opening Balance - Bank Borrowings', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' }] : []),
      { lineNumber: 35, businessUnit: bu.code, account: '3000', debit: 0, credit: shareCapital, description: 'Opening Balance - Share Capital', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
      { lineNumber: 36, businessUnit: bu.code, account: '3100', debit: 0, credit: retainedEarnings, description: 'Opening Balance - Retained Earnings', sourceModule: 'Opening Balances', sourceDocumentNumber: 'OPEN-2026' },
    ];

    let drSum = 0;
    let crSum = 0;
    jLines.forEach((l) => {
      drSum = addMoney(drSum, l.debit);
      crSum = addMoney(crSum, l.credit);
    });

    glJournals.push({
      id: `GLJ-OPEN-${bu.code}`,
      number: `JV-2026-00000${i + 1}`,
      period: 'Jan-26',
      journalDate: '2026-01-01',
      businessUnit: bu.code,
      sourceModule: 'Opening Balances',
      category: 'Opening Balances',
      description: `Opening Balance Journal 01/Jan/2026 - ${bu.name}`,
      status: 'Posted',
      totalDebit: drSum,
      totalCredit: crSum,
      lines: jLines,
      createdBy: 'daniel.reed',
      createdAt: '2026-01-01T08:00:00Z',
      approvedBy: 'daniel.reed',
      postedAt: '2026-01-01T08:00:00Z',
    });
  });

  // 8. Fixed Assets Register (80 active assets across group)
  const fixedAssets: FixedAsset[] = [];
  const assetSourceLines: AssetSourceLine[] = [];
  let faSeq = 1;

  BUSINESS_UNITS.forEach((bu) => {
    // 5 to 7 assets per BU
    assetCategories.forEach((cat) => {
      if (cat.name === 'Buildings' && bu.type !== 'Hospital') return;
      if (cat.name === 'Vehicles' && bu.type === 'Pharmacy') return;

      const tagNumber = `FA-${String(faSeq++).padStart(6, '0')}`;
      const cost = cat.name === 'Buildings' ? 12000000 : cat.name === 'Medical Equipment' ? randInt(250000, 1500000) : randInt(25000, 180000);
      const monthlyDep = round2(cost / (cat.usefulLifeYears * 12));
      const monthsDepreciated = 9; // Jan to Sep 2026
      const accumDep = round2(monthlyDep * monthsDepreciated);

      fixedAssets.push({
        id: `FA-ID-${tagNumber}`,
        tagNumber,
        name: `${cat.name} Unit - ${bu.code}`,
        businessUnit: bu.code,
        department: cat.name === 'Medical Equipment' ? 'Clinical' : 'Facilities',
        category: cat.name,
        costAccount: cat.costAccount,
        accumDepAccount: cat.accumDepAccount,
        cost,
        salvageValue: 0,
        usefulLifeYears: cat.usefulLifeYears,
        inServiceDate: '2026-01-01',
        accumulatedDepreciation: accumDep,
        netBookValue: round2(cost - accumDep),
        status: 'Active',
        lastDepreciationPeriod: 'Sep-26',
      });
    });
  });

  // Fixed Asset Additions Queue
  // About 30 Incomplete, 3 Exceptions, 20 Ready to Post
  for (let s = 1; s <= 53; s++) {
    const isException = s <= 3;
    const isReady = s > 3 && s <= 23;
    const bu = randChoice(BUSINESS_UNITS).code;

    assetSourceLines.push({
      id: `SRC-${String(s).padStart(4, '0')}`,
      apInvoiceId: `PINV-CAP-${s}`,
      apInvoiceNumber: `PINV-2026-${String(200 + s).padStart(6, '0')}`,
      lineNumber: 1,
      poNumber: `PO-2026-${String(100 + s).padStart(6, '0')}`,
      businessUnit: bu,
      description: isException
        ? 'Diagnostic Imaging Component (In-Service Date Error)'
        : isReady
        ? 'Mindray DC-70 Ultrasound Scanner System'
        : 'Patient Monitoring Workstation Touchscreen',
      cost: randInt(45000, 220000),
      invoiceDate: '2026-10-05',
      inServiceDate: isException ? '2025-12-01' : '2026-10-12', // prior date triggers exception
      categoryName: isException ? undefined : 'Medical Equipment',
      units: 1,
      department: 'Clinical',
      status: isException ? 'Exception' : isReady ? 'Ready to Post' : 'Incomplete',
      exceptionReason: isException ? 'In-service date precedes current fiscal additions calendar or missing asset category classification' : undefined,
      tagNumber: isReady ? `FA-${String(faSeq++).padStart(6, '0')}` : undefined,
      comments: isReady ? 'Prepared and ready for checker capitalization approval' : 'Awaiting category allocation',
    });
  }

  // Monthly Depreciation Runs: Jan-26 to Sep-26 posted
  const months = ['Jan-26', 'Feb-26', 'Mar-26', 'Apr-26', 'May-26', 'Jun-26', 'Jul-26', 'Aug-26', 'Sep-26'];
  const depreciationRuns: DepreciationRun[] = [];

  months.forEach((m, idx) => {
    const runDate = `2026-0${idx + 1}-28`;
    const depLines = fixedAssets.map((fa) => {
      const amt = round2(fa.cost / (fa.usefulLifeYears * 12));
      return {
        assetId: fa.id,
        assetTag: fa.tagNumber,
        assetName: fa.name,
        businessUnit: fa.businessUnit,
        category: fa.category,
        depreciationAmount: amt,
        accumDepAccount: fa.accumDepAccount,
        depExpenseAccount: '6300',
      };
    });

    const totDep = depLines.reduce((acc, l) => addMoney(acc, l.depreciationAmount), 0);
    const jvNum = `JV-2026-00${100 + idx}`;

    depreciationRuns.push({
      id: `DEP-RUN-${m}`,
      period: m,
      runDate,
      businessUnit: 'All',
      totalDepreciation: totDep,
      lines: depLines,
      status: 'Posted',
      glJournalId: `GLJ-DEP-${m}`,
      createdBy: 'henry.brooks',
      approvedBy: 'daniel.reed',
    });

    // Balanced GL Journal for Depreciation
    const jLines: any[] = [];
    let lNo = 1;
    depLines.forEach((dl) => {
      jLines.push({
        lineNumber: lNo++,
        businessUnit: dl.businessUnit,
        account: '6300',
        department: 'Facilities',
        debit: dl.depreciationAmount,
        credit: 0,
        description: `Depreciation ${m} - ${dl.assetName}`,
        sourceModule: 'Depreciation',
        sourceDocumentNumber: `DEP-${m}`,
      });
      jLines.push({
        lineNumber: lNo++,
        businessUnit: dl.businessUnit,
        account: dl.accumDepAccount,
        debit: 0,
        credit: dl.depreciationAmount,
        description: `Accum Dep ${m} - ${dl.assetName}`,
        sourceModule: 'Depreciation',
        sourceDocumentNumber: `DEP-${m}`,
      });
    });

    glJournals.push({
      id: `GLJ-DEP-${m}`,
      number: jvNum,
      period: m,
      journalDate: runDate,
      businessUnit: 'Multi-BU',
      sourceModule: 'Depreciation',
      category: 'Depreciation',
      description: `Monthly Fixed Asset Depreciation Run - ${m}`,
      status: 'Posted',
      totalDebit: totDep,
      totalCredit: totDep,
      lines: jLines,
      createdBy: 'henry.brooks',
      createdAt: `${runDate}T16:00:00Z`,
      approvedBy: 'daniel.reed',
      postedAt: `${runDate}T16:30:00Z`,
    });
  });

  // 9. Requisitions, Purchase Orders, Receipts
  const requisitions: Requisition[] = [];
  const purchaseOrders: PurchaseOrder[] = [];
  const receipts: Receipt[] = [];

  for (let r = 1; r <= 35; r++) {
    const bu = randChoice(BUSINESS_UNITS).code;
    const reqNum = `REQ-2026-${String(r).padStart(6, '0')}`;
    const itm = randChoice(items);
    const qty = randInt(10, 100);
    const cost = round2(qty * itm.weightedAvgCost);

    requisitions.push({
      id: `REQ-ID-${r}`,
      number: reqNum,
      businessUnit: bu,
      date: '2026-10-02',
      department: 'Clinical',
      description: `Replenishment of ${itm.description}`,
      status: 'Approved',
      lines: [{ lineNumber: 1, itemCode: itm.code, description: itm.description, quantity: qty, estimatedCost: cost, department: 'Clinical', isCapital: itm.itemClass === 'Capital Asset' }],
      totalAmount: cost,
      createdBy: 'liam.carter',
      createdAt: '2026-10-02T09:00:00Z',
      approvedBy: 'charlotte.davis',
      approvedAt: '2026-10-02T11:00:00Z',
    });

    // PO
    const poNum = `PO-2026-${String(r).padStart(6, '0')}`;
    const sup = randChoice(suppliers);
    const taxAmt = round2(cost * 0.05);
    const totPo = addMoney(cost, taxAmt);

    purchaseOrders.push({
      id: `PO-ID-${r}`,
      number: poNum,
      requisitionNumber: reqNum,
      businessUnit: bu,
      supplierId: sup.id,
      supplierName: sup.name,
      date: '2026-10-04',
      paymentTerms: 'Net 30',
      currency: 'AED',
      status: r <= 30 ? 'Approved' : 'Pending Approval',
      lines: [{
        lineNumber: 1,
        itemCode: itm.code,
        description: itm.description,
        quantity: qty,
        receivedQuantity: r <= 25 ? qty : 0,
        invoicedQuantity: r <= 20 ? qty : 0,
        unitPrice: itm.weightedAvgCost,
        lineAmount: cost,
        taxCode: 'STANDARD_5',
        account: itm.itemClass === 'Capital Asset' ? '1610' : '1200',
        department: 'Clinical',
        isCapital: itm.itemClass === 'Capital Asset',
      }],
      subtotal: cost,
      taxAmount: taxAmt,
      totalAmount: totPo,
      createdBy: 'liam.carter',
      createdAt: '2026-10-04T10:00:00Z',
      approvedBy: r <= 30 ? 'daniel.reed' : undefined,
      approvedAt: r <= 30 ? '2026-10-04T14:00:00Z' : undefined,
    });

    // Goods Receipt (Created by Noah Bennett, approved by Charlotte Davis, posted to GL)
    if (r <= 25) {
      const rcvNum = `RCV-2026-${String(r).padStart(6, '0')}`;
      const rcvJvNum = `JV-2026-00${150 + r}`;
      const rcvJvId = `GLJ-RCV-${r}`;
      const invAccount = itm.itemClass === 'Capital Asset' ? '1610' : itm.itemClass === 'Pharmaceutical' ? '1200' : itm.itemClass === 'Consumable' ? '1210' : '1230';

      receipts.push({
        id: `RCV-ID-${r}`,
        number: rcvNum,
        poNumber: poNum,
        businessUnit: bu,
        supplierId: sup.id,
        supplierName: sup.name,
        receiptDate: '2026-10-06',
        status: 'Posted',
        lines: [{
          lineNumber: 1,
          poNumber: poNum,
          poLineNumber: 1,
          itemCode: itm.code,
          description: itm.description,
          quantityReceived: qty,
          unitPrice: itm.weightedAvgCost,
          lineAmount: cost,
          account: invAccount,
        }],
        totalAmount: cost,
        createdBy: 'noah.bennett',
        createdAt: '2026-10-06T11:00:00Z',
        approvedBy: 'charlotte.davis',
        approvedAt: '2026-10-06T12:00:00Z',
        glJournalId: rcvJvId,
        glJournalNumber: rcvJvNum,
      });

      // Post balanced GL Journal: Dr Inventory / Cr GRNI 2010
      glJournals.push({
        id: rcvJvId,
        number: rcvJvNum,
        period: 'Oct-26',
        journalDate: '2026-10-06',
        businessUnit: bu,
        sourceModule: 'Supply Chain Execution',
        category: 'Goods Receipt',
        description: `Goods receipt note against ${poNum} - PO: ${poNum} from ${sup.name}`,
        status: 'Posted',
        totalDebit: cost,
        totalCredit: cost,
        lines: [
          {
            lineNumber: 1,
            businessUnit: bu,
            account: invAccount,
            department: 'Clinical',
            debit: cost,
            credit: 0,
            description: `Stock Receipt: ${itm.description}`,
            sourceModule: 'Supply Chain Execution',
            sourceDocumentNumber: rcvNum,
          },
          {
            lineNumber: 2,
            businessUnit: bu,
            account: '2010',
            department: 'Clinical',
            debit: 0,
            credit: cost,
            description: `Accrue Goods Received Not Invoiced (GRNI) - PO: ${poNum}`,
            sourceModule: 'Supply Chain Execution',
            sourceDocumentNumber: rcvNum,
          },
        ],
        createdBy: 'noah.bennett',
        createdAt: '2026-10-06T11:00:00Z',
        approvedBy: 'charlotte.davis',
        postedAt: '2026-10-06T12:00:00Z',
      });
    }
  }

  // 10. AP Invoices & Payments
  const apInvoices: APInvoice[] = [];
  const apPayments: APPayment[] = [];
  let apJvCounter = 200;

  for (let i = 1; i <= 45; i++) {
    const bu = randChoice(BUSINESS_UNITS).code;
    const sup = suppliers[i % suppliers.length];
    const isPending = i >= 35 && i <= 40;
    const isDraft = i > 40 && i <= 43;
    const isRejected = i === 44;
    const isHold = i === 45;
    const isApprovedOrPosted = i < 35;

    const sub = randInt(1500, 48000);
    const tax = round2(sub * 0.05);
    const total = addMoney(sub, tax);

    const invNum = `PINV-2026-${String(i).padStart(6, '0')}`;
    const supInvNo = `INV-SUP-${10000 + i}`;
    const createdBy = 'omar.haddad'; // Payables Maker per matrix

    const apStatus = isPending
      ? 'Pending Approval'
      : isDraft
      ? 'Draft'
      : isRejected
      ? 'Rejected'
      : 'Posted';

    const invoice: APInvoice = {
      id: `AP-INV-${i}`,
      number: invNum,
      businessUnit: bu,
      invoiceType: 'Standard',
      supplierId: sup.id,
      supplierName: sup.name,
      supplierSite: 'Abu Dhabi HQ',
      supplierInvoiceNumber: supInvNo,
      invoiceDate: '2026-10-08',
      glDate: '2026-10-08',
      dueDate: '2026-11-07',
      currency: 'AED',
      description: `Hospital Consumables & Supplies - ${sup.name}`,
      lines: [
        {
          lineNumber: 1,
          poNumber: `PO-2026-0000${(i % 20) + 1}`,
          poLineNumber: 1,
          description: `Consumables and surgical items from ${sup.name}`,
          quantity: 1,
          unitPrice: sub,
          lineAmount: sub,
          taxCode: 'STANDARD_5',
          taxAmount: tax,
          distributionAccount: sup.category === 'Medical Equipment' ? '1610' : '2010',
          department: 'Clinical',
          isCapital: sup.category === 'Medical Equipment',
          assetCategory: sup.category === 'Medical Equipment' ? 'Medical Equipment' : undefined,
        },
      ],
      subtotal: sub,
      taxAmount: tax,
      totalAmount: total,
      paidAmount: isApprovedOrPosted && i <= 20 ? total : 0,
      status: apStatus,
      holds: isHold ? [{ type: 'Price Hold', reason: 'Price variance exceeds PO contract threshold (3.2%)', datePlaced: '2026-10-08', released: false }] : [],
      createdBy,
      createdAt: '2026-10-08T09:30:00Z',
      approvedBy: isApprovedOrPosted ? (createdBy === 'charlotte.davis' ? 'daniel.reed' : 'charlotte.davis') : undefined,
      approvedAt: isApprovedOrPosted ? '2026-10-08T14:00:00Z' : undefined,
      rejectionReason: isRejected ? 'Tax Invoice TRN number mismatch on supporting document' : undefined,
      postedAt: isApprovedOrPosted ? '2026-10-08T14:05:00Z' : undefined,
      glJournalId: isApprovedOrPosted ? `GLJ-AP-${i}` : undefined,
    };

    apInvoices.push(invoice);

    // Balanced GL Journal for posted invoices
    if (isApprovedOrPosted) {
      const jvNum = `JV-2026-00${apJvCounter++}`;
      glJournals.push({
        id: `GLJ-AP-${i}`,
        number: jvNum,
        period: 'Oct-26',
        journalDate: '2026-10-08',
        businessUnit: bu,
        sourceModule: 'Payables',
        category: 'Purchase Invoices',
        description: `AP Invoice ${invNum} - ${sup.name} - Ref: ${supInvNo}`,
        status: 'Posted',
        totalDebit: total,
        totalCredit: total,
        lines: [
          { lineNumber: 1, businessUnit: bu, account: '2010', department: 'Clinical', debit: sub, credit: 0, description: `GRNI PO match: ${sup.name}`, sourceModule: 'Payables', sourceDocumentNumber: invNum },
          { lineNumber: 2, businessUnit: bu, account: '1400', debit: tax, credit: 0, description: `VAT 5% Input Recoverable - ${supInvNo}`, sourceModule: 'Payables', sourceDocumentNumber: invNum },
          { lineNumber: 3, businessUnit: bu, account: '2000', debit: 0, credit: total, description: `Trade Payables: ${sup.name}`, sourceModule: 'Payables', sourceDocumentNumber: invNum },
        ],
        createdBy,
        createdAt: '2026-10-08T14:05:00Z',
        approvedBy: invoice.approvedBy!,
        postedAt: '2026-10-08T14:05:00Z',
      });

      // Payments for the first 20 invoices
      if (i <= 20) {
        const payNum = `PAY-2026-${String(i).padStart(6, '0')}`;
        apPayments.push({
          id: `PAY-ID-${i}`,
          number: payNum,
          businessUnit: bu,
          supplierId: sup.id,
          supplierName: sup.name,
          paymentDate: '2026-10-12',
          bankAccountCode: '1020',
          amount: total,
          paymentMethod: 'Bank Transfer',
          referenceNumber: `FT-FAB-${55000 + i}`,
          applications: [{ invoiceId: invoice.id, invoiceNumber: invoice.number, amountApplied: total }],
          status: 'Posted',
          createdBy: 'omar.haddad',
          createdAt: '2026-10-12T10:00:00Z',
          approvedBy: 'charlotte.davis',
          approvedAt: '2026-10-12T11:00:00Z',
          glJournalId: `GLJ-PAY-${i}`,
        });

        glJournals.push({
          id: `GLJ-PAY-${i}`,
          number: `JV-2026-00${apJvCounter++}`,
          period: 'Oct-26',
          journalDate: '2026-10-12',
          businessUnit: bu,
          sourceModule: 'Payables',
          category: 'Payments',
          description: `AP Payment ${payNum} to ${sup.name}`,
          status: 'Posted',
          totalDebit: total,
          totalCredit: total,
          lines: [
            { lineNumber: 1, businessUnit: bu, account: '2000', debit: total, credit: 0, description: `Clear Trade Payables - ${sup.name}`, sourceModule: 'Payables', sourceDocumentNumber: payNum },
            { lineNumber: 2, businessUnit: bu, account: '1020', debit: 0, credit: total, description: `Disbursement from Operating Bank`, sourceModule: 'Payables', sourceDocumentNumber: payNum },
          ],
          createdBy: 'omar.haddad',
          createdAt: '2026-10-12T11:00:00Z',
          approvedBy: 'charlotte.davis',
          postedAt: '2026-10-12T11:00:00Z',
        });
      }
    }
  }

  // 11. AR Transactions & Receipts
  const arTransactions: ARTransaction[] = [];
  const arReceipts: ARReceipt[] = [];
  let arJvCounter = 400;

  for (let a = 1; a <= 45; a++) {
    const bu = randChoice(BUSINESS_UNITS).code;
    const cust = customers[a % customers.length];
    const isPending = a >= 36 && a <= 40;
    const isDraft = a > 40 && a <= 43;
    const isApprovedOrPosted = a < 36;

    const baseGross = randInt(2500, 68000);
    const discount = cust.type === 'Insurance' ? round2(baseGross * 0.15) : 0;
    const netBilled = subMoney(baseGross, discount);
    const tax = round2(netBilled * 0.05); // standard healthcare VAT if applicable or 0
    const netReceivable = addMoney(netBilled, tax);

    const invNum = `RINV-2026-${String(a).padStart(6, '0')}`;
    const createdBy = 'sofia.marin'; // AR Maker per matrix
    const arControl = cust.type === 'Insurance' ? '1110' : cust.type === 'Patient' ? '1100' : '1120';

    const transaction: ARTransaction = {
      id: `AR-INV-${a}`,
      number: invNum,
      businessUnit: bu,
      transactionClass: 'Invoice',
      customerId: cust.id,
      customerName: cust.name,
      customerType: cust.type,
      patientName: `Patient ${1000 + a}`,
      patientId: `MRN-${202600 + a}`,
      claimReference: `CLM-UAE-${80000 + a}`,
      visitDate: '2026-10-09',
      transactionDate: '2026-10-09',
      glDate: '2026-10-09',
      dueDate: '2026-11-23',
      description: `Inpatient & Clinical Treatment Services - ${cust.name}`,
      lines: [
        {
          lineNumber: 1,
          serviceCategory: 'Inpatient Clinical Services',
          description: `Hospital Inpatient Accommodation and Specialist Consultation`,
          revenueAccount: '4000',
          amount: baseGross,
          taxCode: 'STANDARD_5',
          taxAmount: tax,
          insuranceDiscountAmount: discount,
          patientCoPayAmount: 0,
        },
      ],
      subtotal: baseGross,
      discountAmount: discount,
      taxAmount: tax,
      totalAmount: netReceivable,
      paidAmount: isApprovedOrPosted && a <= 20 ? netReceivable : 0,
      status: isPending ? 'Pending Approval' : isDraft ? 'Draft' : 'Posted',
      createdBy,
      createdAt: '2026-10-09T10:15:00Z',
      approvedBy: isApprovedOrPosted ? (createdBy === 'charlotte.davis' ? 'daniel.reed' : 'charlotte.davis') : undefined,
      approvedAt: isApprovedOrPosted ? '2026-10-09T14:20:00Z' : undefined,
      postedAt: isApprovedOrPosted ? '2026-10-09T14:20:00Z' : undefined,
      glJournalId: isApprovedOrPosted ? `GLJ-AR-${a}` : undefined,
    };

    arTransactions.push(transaction);

    // Balanced GL Journal for posted AR transactions
    if (isApprovedOrPosted) {
      const jvNum = `JV-2026-00${arJvCounter++}`;
      const jLines: any[] = [
        { lineNumber: 1, businessUnit: bu, account: arControl, debit: netReceivable, credit: 0, description: `Trade Receivable: ${cust.name}`, sourceModule: 'Receivables', sourceDocumentNumber: invNum },
      ];
      if (discount > 0) {
        jLines.push({ lineNumber: 2, businessUnit: bu, account: '4090', debit: discount, credit: 0, description: 'Contractual Insurance Discount', sourceModule: 'Receivables', sourceDocumentNumber: invNum });
      }
      jLines.push({ lineNumber: 3, businessUnit: bu, account: '4000', debit: 0, credit: baseGross, description: 'Inpatient Revenue', sourceModule: 'Receivables', sourceDocumentNumber: invNum });
      if (tax > 0) {
        jLines.push({ lineNumber: 4, businessUnit: bu, account: '2100', debit: 0, credit: tax, description: 'VAT 5% Output Payable', sourceModule: 'Receivables', sourceDocumentNumber: invNum });
      }

      let totalDr = 0;
      let totalCr = 0;
      jLines.forEach((l) => {
        totalDr = addMoney(totalDr, l.debit);
        totalCr = addMoney(totalCr, l.credit);
      });

      glJournals.push({
        id: `GLJ-AR-${a}`,
        number: jvNum,
        period: 'Oct-26',
        journalDate: '2026-10-09',
        businessUnit: bu,
        sourceModule: 'Receivables',
        category: 'Sales Invoices',
        description: `AR Billing ${invNum} - ${cust.name}`,
        status: 'Posted',
        totalDebit: totalDr,
        totalCredit: totalCr,
        lines: jLines,
        createdBy,
        createdAt: '2026-10-09T14:20:00Z',
        approvedBy: transaction.approvedBy!,
        postedAt: '2026-10-09T14:20:00Z',
      });

      // Receipts for first 20 transactions
      if (a <= 20) {
        const rctNum = `RCT-2026-${String(a).padStart(6, '0')}`;
        arReceipts.push({
          id: `RCT-ID-${a}`,
          number: rctNum,
          businessUnit: bu,
          customerId: cust.id,
          customerName: cust.name,
          receiptDate: '2026-10-14',
          glDate: '2026-10-14',
          receiptMethod: 'Bank Transfer',
          bankAccountCode: '1030',
          amount: netReceivable,
          unappliedAmount: 0,
          referenceNumber: `WIRE-IN-${99000 + a}`,
          applications: [{ transactionId: transaction.id, transactionNumber: transaction.number, amountApplied: netReceivable }],
          status: 'Posted',
          createdBy: 'sofia.marin',
          createdAt: '2026-10-14T11:00:00Z',
          approvedBy: 'charlotte.davis',
          approvedAt: '2026-10-14T12:00:00Z',
          glJournalId: `GLJ-RCT-${a}`,
        });

        glJournals.push({
          id: `GLJ-RCT-${a}`,
          number: `JV-2026-00${arJvCounter++}`,
          period: 'Oct-26',
          journalDate: '2026-10-14',
          businessUnit: bu,
          sourceModule: 'Receivables',
          category: 'Receipts',
          description: `AR Receipt ${rctNum} from ${cust.name}`,
          status: 'Posted',
          totalDebit: netReceivable,
          totalCredit: netReceivable,
          lines: [
            { lineNumber: 1, businessUnit: bu, account: '1030', debit: netReceivable, credit: 0, description: `Collections deposit - ${cust.name}`, sourceModule: 'Receivables', sourceDocumentNumber: rctNum },
            { lineNumber: 2, businessUnit: bu, account: arControl, debit: 0, credit: netReceivable, description: `Apply AR Receipt to ${cust.name}`, sourceModule: 'Receivables', sourceDocumentNumber: rctNum },
          ],
          createdBy: 'sofia.marin',
          createdAt: '2026-10-14T12:00:00Z',
          approvedBy: 'charlotte.davis',
          postedAt: '2026-10-14T12:00:00Z',
        });
      }
    }
  }

  // 12. Cash Vouchers (Petty Cash & Main Cash)
  const cashVouchers: CashVoucher[] = [];
  let cashJvCounter = 600;

  for (let c = 1; c <= 25; c++) {
    const bu = randChoice(BUSINESS_UNITS).code;
    const isPetty = c % 2 !== 0;
    const amt = isPetty ? randInt(120, 850) : randInt(1200, 3800);
    const tax = round2(amt * 0.05);
    const net = subMoney(amt, tax);
    const vNum = isPetty ? `PCV-2026-${String(c).padStart(6, '0')}` : `MCV-2026-${String(c).padStart(6, '0')}`;
    const isPending = c >= 22;

    const v: CashVoucher = {
      id: `VOUCH-${c}`,
      number: vNum,
      type: isPetty ? 'PettyCash' : 'MainCash',
      businessUnit: bu,
      date: '2026-10-15',
      payee: isPetty ? 'Emirates Courier Express' : 'Local Emergency Maintenance Services',
      expenseCategory: isPetty ? 'Office Supplies and Stationery' : 'Repairs and Maintenance',
      expenseAccount: isPetty ? '6200' : '6120',
      department: 'Administration',
      description: isPetty ? 'Urgent courier delivery of pathology lab specimen samples' : 'Emergency repair of air handler water chilling pump',
      amount: amt,
      taxCode: 'STANDARD_5',
      taxAmount: tax,
      receiptAttached: true,
      status: isPending ? 'Pending Approval' : 'Posted',
      createdBy: 'aisha.khan',
      createdAt: '2026-10-15T09:00:00Z',
      approvedBy: isPending ? undefined : 'charlotte.davis',
      approvedAt: isPending ? undefined : '2026-10-15T10:30:00Z',
      glJournalId: isPending ? undefined : `GLJ-CSH-${c}`,
    };

    cashVouchers.push(v);

    if (!isPending) {
      const cashAcct = isPetty ? '1010' : '1000';
      glJournals.push({
        id: `GLJ-CSH-${c}`,
        number: `JV-2026-00${cashJvCounter++}`,
        period: 'Oct-26',
        journalDate: '2026-10-15',
        businessUnit: bu,
        sourceModule: 'Cash Management',
        category: 'Cash Expense',
        description: `${v.type} Voucher ${vNum} - ${v.payee}`,
        status: 'Posted',
        totalDebit: amt,
        totalCredit: amt,
        lines: [
          { lineNumber: 1, businessUnit: bu, account: v.expenseAccount, department: 'Administration', debit: net, credit: 0, description: v.description, sourceModule: 'Cash Management', sourceDocumentNumber: vNum },
          { lineNumber: 2, businessUnit: bu, account: '1400', debit: tax, credit: 0, description: `VAT 5% Recoverable - ${vNum}`, sourceModule: 'Cash Management', sourceDocumentNumber: vNum },
          { lineNumber: 3, businessUnit: bu, account: cashAcct, debit: 0, credit: amt, description: `Disbursement from ${isPetty ? 'Petty Cash' : 'Main Cash'}`, sourceModule: 'Cash Management', sourceDocumentNumber: vNum },
        ],
        createdBy: 'aisha.khan',
        createdAt: '2026-10-15T10:30:00Z',
        approvedBy: 'charlotte.davis',
        postedAt: '2026-10-15T10:30:00Z',
      });
    }
  }

  // 13. Intercompany Transactions
  // Mirror entries: Provider: Dr 1500 / Cr 4900; Receiver: Dr 6400 / Cr 2500
  const icTransactions: ICTransaction[] = [];
  let icJvCounter = 700;

  for (let k = 1; k <= 10; k++) {
    const pBU = `H0${((k % 5) + 1)}`;
    const rBU = `C0${((k % 5) + 1)}`;
    const amt = randInt(12000, 48000);
    const icNum = `ICI-2026-${String(k).padStart(6, '0')}`;
    const isPending = k === 10;

    const ic: ICTransaction = {
      id: `IC-TXN-${k}`,
      number: icNum,
      type: 'Invoice',
      providerBU: pBU,
      receiverBU: rBU,
      date: '2026-10-16',
      description: `Centralized Clinical Lab & Radiologist Tele-reporting recharge: ${pBU} to ${rBU}`,
      lines: [
        {
          lineNumber: 1,
          description: `Specialist diagnostic radiology tele-reporting sessions`,
          amount: amt,
          providerAccount: '4900', // IC Service Revenue
          receiverAccount: '6400', // IC Service Charge Expense
        },
      ],
      totalAmount: amt,
      status: isPending ? 'Pending Approval' : 'Posted',
      createdBy: 'emma.collins',
      createdAt: '2026-10-16T11:00:00Z',
      receiverAcceptedBy: isPending ? undefined : 'daniel.reed',
      approvedBy: isPending ? undefined : 'daniel.reed',
      approvedAt: isPending ? undefined : '2026-10-16T15:00:00Z',
      glJournalId: isPending ? undefined : `GLJ-IC-${k}`,
    };

    icTransactions.push(ic);

    if (!isPending) {
      glJournals.push({
        id: `GLJ-IC-${k}`,
        number: `JV-2026-00${icJvCounter++}`,
        period: 'Oct-26',
        journalDate: '2026-10-16',
        businessUnit: 'Multi-BU',
        sourceModule: 'Intercompany',
        category: 'Intercompany',
        description: `Intercompany Invoice ${icNum}: ${pBU} ➔ ${rBU}`,
        status: 'Posted',
        totalDebit: round2(amt * 2),
        totalCredit: round2(amt * 2),
        lines: [
          // Provider BU
          { lineNumber: 1, businessUnit: pBU, account: '1500', debit: amt, credit: 0, description: `Due from ${rBU} (IC: ${icNum})`, sourceModule: 'Intercompany', sourceDocumentNumber: icNum },
          { lineNumber: 2, businessUnit: pBU, account: '4900', debit: 0, credit: amt, description: `IC Service Revenue from ${rBU}`, sourceModule: 'Intercompany', sourceDocumentNumber: icNum },
          // Receiver BU
          { lineNumber: 3, businessUnit: rBU, account: '6400', debit: amt, credit: 0, description: `IC Service Expense from ${pBU}`, sourceModule: 'Intercompany', sourceDocumentNumber: icNum },
          { lineNumber: 4, businessUnit: rBU, account: '2500', debit: 0, credit: amt, description: `Due to ${pBU} (IC: ${icNum})`, sourceModule: 'Intercompany', sourceDocumentNumber: icNum },
        ],
        createdBy: 'emma.collins',
        createdAt: '2026-10-16T15:00:00Z',
        approvedBy: 'daniel.reed',
        postedAt: '2026-10-16T15:00:00Z',
      });
    }
  }

  // 14. Bank Statements
  const bankStatements: BankStatement[] = [];
  BUSINESS_UNITS.slice(0, 5).forEach((bu, idx) => {
    bankStatements.push({
      id: `BST-STMT-${idx + 1}`,
      number: `BST-2026-${String(idx + 1).padStart(6, '0')}`,
      bankAccountCode: '1020',
      businessUnit: bu.code,
      statementDate: '2026-10-18',
      openingBalance: 820000,
      closingBalance: 850000,
      status: 'Partially Reconciled',
      lines: [
        { id: `BL-1-${idx}`, statementNumber: `BST-2026-${String(idx + 1).padStart(6, '0')}`, lineDate: '2026-10-10', type: 'Credit', amount: 55000, reference: 'FAB-DEPOSIT-01', description: 'Patient Collections Transfer', isReconciled: true, matchedTransactionType: 'AR_RECEIPT', matchedTransactionNumber: 'RCT-2026-000001' },
        { id: `BL-2-${idx}`, statementNumber: `BST-2026-${String(idx + 1).padStart(6, '0')}`, lineDate: '2026-10-12', type: 'Debit', amount: 25000, reference: 'FAB-WPS-SALARY', description: 'Staff Payroll Disbursement', isReconciled: true, matchedTransactionType: 'AP_PAYMENT', matchedTransactionNumber: 'PAY-2026-000001' },
        { id: `BL-3-${idx}`, statementNumber: `BST-2026-${String(idx + 1).padStart(6, '0')}`, lineDate: '2026-10-15', type: 'Debit', amount: 450, reference: 'FAB-CHG-10', description: 'FAB Monthly Merchant Account Maintenance Fee', isReconciled: false },
      ],
    });
  });

  // 15. Notifications
  const notifications: Notification[] = [
    {
      id: 'NOTIF-001',
      title: 'Pending AP Invoices Awaiting Approval',
      message: 'There are 6 AP invoices in "Pending Approval" queue awaiting Checker authorization.',
      type: 'approval',
      linkUrl: '#/payables/invoices',
      read: false,
      timestamp: '2026-10-19T08:30:00Z',
    },
    {
      id: 'NOTIF-002',
      title: 'Fixed Assets Additions Queue Alert',
      message: '20 source lines are "Ready to Post" in the Fixed Assets additions register.',
      type: 'alert',
      linkUrl: '#/fixed-assets/assets',
      read: false,
      timestamp: '2026-10-19T09:15:00Z',
    },
    {
      id: 'NOTIF-003',
      title: 'Intercompany Acceptance Required',
      message: 'Intercompany Invoice ICI-2026-000010 from H05 to C05 requires receiver acceptance.',
      type: 'approval',
      linkUrl: '#/intercompany/transactions',
      read: false,
      timestamp: '2026-10-19T10:00:00Z',
    },
    {
      id: 'NOTIF-004',
      title: 'October 2026 Fiscal Period Open',
      message: 'Period Oct-26 is currently OPEN for transactions. Ensure all prior month runs are finalized.',
      type: 'system',
      linkUrl: '#/general-accounting/period-close',
      read: true,
      timestamp: '2026-10-19T07:00:00Z',
    },
  ];

  // Reset document sequences to match highest generated
  resetSequences({
    'REQ-2026': 35,
    'PO-2026': 35,
    'RCV-2026': 25,
    'PINV-2026': 45,
    'PAY-2026': 20,
    'RINV-2026': 45,
    'RCT-2026': 20,
    'PCV-2026': 25,
    'MCV-2026': 25,
    'ICI-2026': 10,
    'JV-2026': 850,
    'FA-TAG': faSeq,
  });

  const state: DatabaseState = {
    accounts: [...ENRICHED_CHART_OF_ACCOUNTS],
    suppliers,
    customers,
    items,
    bankAccounts,
    pettyCashFunds,
    assetCategories,
    requisitions,
    purchaseOrders,
    receipts,
    inventoryBalances,
    apInvoices,
    apPayments,
    arTransactions,
    arReceipts,
    fixedAssets,
    assetSourceLines,
    depreciationRuns,
    cashVouchers,
    bankStatements,
    icTransactions,
    glJournals,
    auditLogs: [
      {
        id: 'AUDIT-INIT',
        timestamp: '2026-10-19T08:00:00Z',
        entityType: 'System',
        entityId: 'SYS-2026',
        action: 'CREATE',
        userId: 'daniel.reed',
        userName: 'Daniel Reed (CFO)',
        comments: 'System initialized with Meridian Healthcare Group opening balances and master charts.',
      },
    ],
    notifications,
    favourites: [
      '#/payables/invoices',
      '#/general-accounting/journals',
      '#/reports/trial-balance',
      '#/reports/ifrs',
      '#/fixed-assets/assets',
    ],
  };

  saveDb(state);
  return state;
}
