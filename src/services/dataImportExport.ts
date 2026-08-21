import Papa from 'papaparse';
import { Asset, AssetCategory, CapexItem, CompanyData, PlantLocation } from '../types';

export interface ImportValidationResult<T> {
  success: boolean;
  data: T[];
  errors: string[];
  warnings: string[];
  totalRows: number;
}

/**
 * Standard CSV Template Columns for Fixed Asset Register (FAR)
 */
export const FAR_CSV_HEADERS = [
  'Asset ID',
  'Asset Name',
  'Category',
  'Plant Location',
  'Sub Location / Bay',
  'Gross Cost (INR)',
  'Accumulated Depreciation (INR)',
  'Capitalisation Date (YYYY-MM-DD)',
  'Useful Life (Years)',
  'Sch II Useful Life (Years)',
  'Depreciation Method (SLM/WDV)',
  'Serial Number',
  'Custodian Name',
  'Department',
  'Vendor Name',
  'Invoice Number',
  'PO Number',
  'GST Paid (INR)',
  'ITC Claimed (Yes/No)',
  'Description'
];

/**
 * Standard CSV Template Columns for Capex Review Queue
 */
export const CAPEX_CSV_HEADERS = [
  'PO Number',
  'Invoice Number',
  'Vendor Name',
  'Description',
  'Amount (INR)',
  'Invoice Date (YYYY-MM-DD)',
  'Plant Location',
  'Department',
  'Suggested Category',
  'GRN Status (Complete/Partial/Pending)',
  'Technical Inspection (Passed/Pending/Failed)'
];

/**
 * Download sample CSV template for Asset Register
 */
export function downloadAssetRegisterCsvTemplate(): void {
  const sampleRows = [
    [
      'AST-PUN-CNC-9901',
      '5-Axis Precision CNC Machining Center',
      'Plant & Machinery',
      'Pune Plant - Chakan',
      'Bay 4 - Machining Cell',
      '4850000',
      '1212500',
      '2022-04-15',
      '15',
      '15',
      'SLM',
      'DMG-MORI-IND-99418',
      'Rajesh Kulkarni',
      'Precision Manufacturing',
      'DMG MORI India Pvt. Ltd.',
      'INV-DMG-2022-8812',
      'PO-2022-PUN-0841',
      '873000',
      'Yes',
      'High-speed vertical machining centre with componentised spindle and bed.'
    ],
    [
      'AST-CHE-ROB-0082',
      '6-Axis Heavy Payload Articulated Industrial Robot',
      'Plant & Machinery',
      'Chennai Automotive Hub',
      'Body Shop Line 2',
      '3850000',
      '770000',
      '2023-01-20',
      '12',
      '12',
      'SLM',
      'FANUC-R2000-8812',
      'Suresh Ramanathan',
      'Body Shop Robotics',
      'Fanuc India Pvt. Ltd.',
      'INV-FNC-2023-4412',
      'PO-2023-CHE-0912',
      '693000',
      'Yes',
      'Heavy spot-welding & material transfer articulated arm.'
    ],
    [
      'AST-BLR-SRV-0019',
      'High-Density Dual Xeon Enterprise Rack Server Cluster',
      'IT Hardware & Servers',
      'Bengaluru HQ & Tech Center',
      'Data Center Rack A-04',
      '1850000',
      '616666',
      '2023-08-10',
      '6',
      '6',
      'SLM',
      'DELL-EMC-R750-9941',
      'Kavita Nair',
      'Enterprise IT',
      'Dell Technologies India',
      'INV-DEL-2023-7721',
      'PO-2023-BLR-1142',
      '333000',
      'Yes',
      'Virtualization host cluster for SAP ERP & PLM workload.'
    ]
  ];

  const csv = Papa.unparse({
    fields: FAR_CSV_HEADERS,
    data: sampleRows
  });

  triggerFileDownload(csv, 'AssetTrust_Fixed_Asset_Register_Template.csv', 'text/csv;charset=utf-8;');
}

/**
 * Download sample CSV template for Capex Queue
 */
export function downloadCapexQueueCsvTemplate(): void {
  const sampleRows = [
    [
      'PO-2024-PUN-9921',
      'INV-SCH-2024-8831',
      'Schneider Electric India',
      '11kV Vacuum Circuit Breaker & HT Switchgear Panel',
      '2850000',
      '2024-11-15',
      'Pune Plant - Chakan',
      'Electrical Infrastructure',
      'Plant & Machinery',
      'Complete',
      'Passed'
    ],
    [
      'PO-2024-CHE-4412',
      'INV-ACC-2024-1290',
      'Atlas Copco India Ltd.',
      'Oil-Free Rotary Screw Air Compressor 75kW with Dryer',
      '1950000',
      '2024-11-20',
      'Chennai Automotive Hub',
      'Utility & Power Plant',
      'Plant & Machinery',
      'Complete',
      'Passed'
    ]
  ];

  const csv = Papa.unparse({
    fields: CAPEX_CSV_HEADERS,
    data: sampleRows
  });

  triggerFileDownload(csv, 'AssetTrust_Capex_Review_Queue_Template.csv', 'text/csv;charset=utf-8;');
}

/**
 * Parse CSV string into Asset records with smart column matching and validation
 */
export function parseCsvToAssets(
  csvText: string,
  defaultPlant: string = 'Pune Plant - Chakan'
): ImportValidationResult<Asset> {
  const errors: string[] = [];
  const warnings: string[] = [];
  const parsedAssets: Asset[] = [];

  const result = Papa.parse(csvText, {
    header: true,
    skipEmptyLines: 'greedy',
    transformHeader: (h) => h.trim().toLowerCase()
  });

  if (result.errors && result.errors.length > 0) {
    result.errors.forEach((err) => {
      errors.push(`Row ${err.row || '?'}: ${err.message}`);
    });
  }

  const rows = result.data as Record<string, string>[];
  if (!rows || rows.length === 0) {
    return {
      success: false,
      data: [],
      errors: ['No valid data rows found in the CSV file.'],
      warnings: [],
      totalRows: 0
    };
  }

  rows.forEach((row, index) => {
    const rowNum = index + 2; // 1-indexed including header
    const getValue = (keys: string[]): string => {
      for (const k of keys) {
        const foundKey = Object.keys(row).find((hk) => hk.includes(k.toLowerCase()));
        if (foundKey && row[foundKey] !== undefined && row[foundKey] !== null) {
          return String(row[foundKey]).trim();
        }
      }
      return '';
    };

    const name = getValue(['asset name', 'name', 'asset_name', 'item name', 'description', 'title']);
    if (!name) {
      errors.push(`Row ${rowNum}: Asset Name is required.`);
      return;
    }

    const rawCost = getValue(['gross cost', 'cost', 'gross', 'amount', 'purchase price', 'value', 'gross_cost']);
    const cost = parseFloat(rawCost.replace(/[^0-9.-]+/g, ''));
    if (isNaN(cost) || cost <= 0) {
      errors.push(`Row ${rowNum}: Invalid Gross Cost '${rawCost}'. Must be a positive numeric value.`);
      return;
    }

    const rawAccumDep = getValue(['accumulated depreciation', 'accum dep', 'accum_dep', 'depreciation', 'dep']);
    const accumDep = parseFloat(rawAccumDep.replace(/[^0-9.-]+/g, '')) || 0;

    const rawCategory = getValue(['category', 'asset category', 'class', 'group']);
    const category = normalizeAssetCategory(rawCategory);

    const plantStr = getValue(['plant location', 'plant', 'location', 'factory', 'hub', 'site']) || defaultPlant;
    const plant = plantStr as PlantLocation;

    const subLocation = getValue(['sub location', 'bay', 'room', 'floor', 'area', 'sub_location']) || 'Main Production Bay';
    const capDate = getValue(['capitalisation date', 'cap date', 'acquisition date', 'date', 'capitalized']) || new Date().toISOString().split('T')[0];
    
    const usefulLife = parseInt(getValue(['useful life', 'life', 'useful_life', 'years'])) || 15;
    const schIILife = parseInt(getValue(['sch ii', 'schedule ii', 'statutory life'])) || usefulLife;
    const depMethod = (getValue(['depreciation method', 'method', 'dep_method']).toUpperCase().includes('WDV') ? 'WDV' : 'SLM') as 'SLM' | 'WDV';

    const serialNumber = getValue(['serial number', 'serial', 'sn', 'serial_no', 'tag']) || `SN-IMP-${Date.now().toString().slice(-6)}-${index}`;
    const custodian = getValue(['custodian', 'incharge', 'owner', 'responsible']) || 'Plant Controller';
    const department = getValue(['department', 'dept', 'cost center']) || 'Operations';
    const vendor = getValue(['vendor', 'supplier', 'seller']) || 'Standard Supplier';
    const invoiceNumber = getValue(['invoice number', 'invoice', 'inv', 'bill']) || `INV-IMP-${rowNum}`;
    const poNumber = getValue(['po number', 'po', 'purchase order']) || `PO-IMP-${rowNum}`;
    const desc = getValue(['description', 'notes', 'remark', 'specs']) || `${name} - Imported Fixed Asset record.`;

    const customId = getValue(['asset id', 'id', 'code', 'asset_code', 'asset_no']);
    const assetId = customId || `AST-${plantStr.substring(0, 3).toUpperCase()}-IMP-${Date.now().toString().slice(-4)}${index}`;

    const rawGst = getValue(['gst paid', 'gst', 'tax']);
    const gstPaid = parseFloat(rawGst.replace(/[^0-9.-]+/g, '')) || Math.round(cost * 0.18);
    const rawItc = getValue(['itc claimed', 'itc', 'credit']);
    const itcClaimed = rawItc.toLowerCase().includes('y') || rawItc.toLowerCase().includes('true') || rawItc.toLowerCase().includes('1');

    const nbv = Math.max(0, cost - accumDep);

    // Auto generate 2-part Ind AS 16 component structure if none supplied
    const components = [
      {
        id: `${assetId}-CMP-1`,
        name: `${name} (Core Structural Frame)`,
        costINR: Math.round(cost * 0.7),
        usefulLifeYears: usefulLife,
        depreciationMethod: depMethod,
        accumulatedDepINR: Math.round(accumDep * 0.7),
        nbvINR: Math.round(nbv * 0.7),
        notes: 'Primary structural mechanical component'
      },
      {
        id: `${assetId}-CMP-2`,
        name: `${name} (Auxiliary / Drives / Control Unit)`,
        costINR: Math.round(cost * 0.3),
        usefulLifeYears: Math.min(6, usefulLife),
        depreciationMethod: depMethod,
        accumulatedDepINR: Math.round(accumDep * 0.3),
        nbvINR: Math.round(nbv * 0.3),
        notes: 'Control and high-wear components'
      }
    ];

    parsedAssets.push({
      id: assetId,
      name,
      category,
      plant,
      subLocation,
      costINR: cost,
      accumulatedDepINR: accumDep,
      nbvINR: nbv,
      capitalisationDate: capDate,
      usefulLifeYears: usefulLife,
      schIILifeYears: schIILife,
      depreciationMethod: depMethod,
      verificationStatus: 'Verified',
      lastVerifiedDate: new Date().toISOString().split('T')[0],
      riskLevel: 'Clean',
      custodian,
      department,
      serialNumber,
      qrCode: `QR-${assetId}`,
      vendor,
      invoiceNumber,
      poNumber,
      grnNumber: `GRN-IMP-${rowNum}`,
      gstPaidINR: gstPaid,
      itcClaimed,
      description: desc,
      components,
      anomalies: [],
      status: 'Active',
      historyEvents: [
        {
          id: `EVT-${Date.now()}-${index}`,
          date: new Date().toISOString().split('T')[0],
          type: 'Procurement',
          description: `Imported into subledger via CSV / Excel batch upload (Row ${rowNum}).`,
          actor: 'Data Import Engine',
          status: 'Completed'
        }
      ]
    });
  });

  return {
    success: errors.length === 0,
    data: parsedAssets,
    errors,
    warnings,
    totalRows: rows.length
  };
}

/**
 * Parse CSV into CapexItem records for AI Review
 */
export function parseCsvToCapex(
  csvText: string,
  defaultPlant: string = 'Pune Plant - Chakan'
): ImportValidationResult<CapexItem> {
  const errors: string[] = [];
  const warnings: string[] = [];
  const parsedCapex: CapexItem[] = [];

  const result = Papa.parse(csvText, {
    header: true,
    skipEmptyLines: 'greedy',
    transformHeader: (h) => h.trim().toLowerCase()
  });

  if (result.errors && result.errors.length > 0) {
    result.errors.forEach((err) => {
      errors.push(`Row ${err.row || '?'}: ${err.message}`);
    });
  }

  const rows = result.data as Record<string, string>[];
  if (!rows || rows.length === 0) {
    return {
      success: false,
      data: [],
      errors: ['No valid rows found in Capex CSV.'],
      warnings: [],
      totalRows: 0
    };
  }

  rows.forEach((row, index) => {
    const rowNum = index + 2;
    const getValue = (keys: string[]): string => {
      for (const k of keys) {
        const foundKey = Object.keys(row).find((hk) => hk.includes(k.toLowerCase()));
        if (foundKey && row[foundKey] !== undefined && row[foundKey] !== null) {
          return String(row[foundKey]).trim();
        }
      }
      return '';
    };

    const desc = getValue(['description', 'item', 'details', 'name', 'particulars']);
    if (!desc) {
      errors.push(`Row ${rowNum}: Description is required.`);
      return;
    }

    const rawAmount = getValue(['amount', 'cost', 'gross', 'value', 'price']);
    const amount = parseFloat(rawAmount.replace(/[^0-9.-]+/g, ''));
    if (isNaN(amount) || amount <= 0) {
      errors.push(`Row ${rowNum}: Invalid Amount '${rawAmount}'.`);
      return;
    }

    const poNumber = getValue(['po number', 'po', 'order']) || `PO-IMP-${rowNum}`;
    const invoiceNumber = getValue(['invoice number', 'invoice', 'inv']) || `INV-IMP-${rowNum}`;
    const vendor = getValue(['vendor', 'supplier', 'seller']) || 'Industrial Vendor';
    const invoiceDate = getValue(['invoice date', 'date', 'bill date']) || new Date().toISOString().split('T')[0];
    const plant = (getValue(['plant location', 'plant', 'location']) || defaultPlant) as PlantLocation;
    const department = getValue(['department', 'dept']) || 'Engineering';
    const suggestedCategory = normalizeAssetCategory(getValue(['suggested category', 'category', 'class']));

    parsedCapex.push({
      id: `CPX-IMP-${Date.now().toString().slice(-4)}${index}`,
      poNumber,
      invoiceNumber,
      vendor,
      description: desc,
      amountINR: amount,
      invoiceDate,
      plant,
      department,
      grnStatus: 'Complete',
      technicalInspection: 'Passed',
      suggestedCategory,
      status: 'Pending AI Review'
    });
  });

  return {
    success: errors.length === 0,
    data: parsedCapex,
    errors,
    warnings,
    totalRows: rows.length
  };
}

/**
 * Export active Asset Register to CSV
 */
export function exportAssetsToCsv(assets: Asset[], companyName: string): void {
  const rows = assets.map((a) => [
    a.id,
    a.name,
    a.category,
    a.plant,
    a.subLocation,
    a.costINR,
    a.accumulatedDepINR,
    a.capitalisationDate,
    a.usefulLifeYears,
    a.schIILifeYears,
    a.depreciationMethod || 'SLM',
    a.serialNumber,
    a.custodian,
    a.department,
    a.vendor,
    a.invoiceNumber,
    a.poNumber,
    a.gstPaidINR || 0,
    a.itcClaimed ? 'Yes' : 'No',
    a.description
  ]);

  const csv = Papa.unparse({
    fields: FAR_CSV_HEADERS,
    data: rows
  });

  const sanitized = companyName.replace(/[^a-zA-Z0-9_-]/g, '_');
  triggerFileDownload(csv, `${sanitized}_Fixed_Asset_Register_${new Date().toISOString().split('T')[0]}.csv`, 'text/csv;charset=utf-8;');
}

/**
 * Export full company workspace backup as JSON
 */
export function exportCompanyBackupJson(companyData: CompanyData): void {
  const jsonStr = JSON.stringify(companyData, null, 2);
  const sanitized = companyData.company.name.replace(/[^a-zA-Z0-9_-]/g, '_');
  triggerFileDownload(
    jsonStr,
    `${sanitized}_AssetTrust_Backup_${new Date().toISOString().split('T')[0]}.json`,
    'application/json;charset=utf-8;'
  );
}

function normalizeAssetCategory(raw: string): AssetCategory {
  const lower = (raw || '').toLowerCase();
  if (lower.includes('machin') || lower.includes('plant') || lower.includes('equip') || lower.includes('tooling')) {
    return 'Plant & Machinery';
  }
  if (lower.includes('build') || lower.includes('civil') || lower.includes('shed') || lower.includes('struct')) {
    return 'Buildings & Civil Structures';
  }
  if (lower.includes('it') || lower.includes('server') || lower.includes('comput') || lower.includes('laptop')) {
    return 'IT Hardware & Servers';
  }
  if (lower.includes('office') || lower.includes('lab') || lower.includes('furnitur')) {
    return 'Office & Lab Equipment';
  }
  if (lower.includes('vehic') || lower.includes('car') || lower.includes('truck') || lower.includes('forklift')) {
    return 'Vehicles';
  }
  if (lower.includes('software') || lower.includes('intangib') || lower.includes('license') || lower.includes('erp')) {
    return 'Intangibles (Software)';
  }
  return 'Plant & Machinery';
}

function triggerFileDownload(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
