import express, { Request, Response } from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer as createViteServer } from 'vite';
import type { GoodsReceiptNote, FactorySettings, MasterData, UserAccount, GrnRevision } from './src/types/grn';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = 3000;
const DATA_DIR = path.join(__dirname, 'data');
const DB_FILE = path.join(DATA_DIR, 'db.json');

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

interface DatabaseSchema {
  settings: FactorySettings;
  masters: MasterData;
  users: UserAccount[];
  grns: GoodsReceiptNote[];
  nextSequenceNumber: number;
}

const defaultSettings: FactorySettings = {
  factoryName: 'श्री बालाजी मार्बल एवं ग्रेनाइट इंडस्ट्रीज',
  factoryTagline: 'उच्च गुणवत्ता मार्बल, ग्रेनाइट एवं सैंडस्टोन ब्लॉक्स',
  factoryAddress: 'रीको इंडस्ट्रियल एरिया, फेज़-2, मकराना रोड, किशनगढ़ (राज.) 305801',
  factoryPhone: '+91 98290 12345 / 0145-265432',
  factoryGstin: '08AABCS1429B1ZX',
  receiptTitle: 'माल प्राप्ति रसीद (GOODS RECEIPT NOTE - GRN)',
  declarationText: 'प्रमाणित किया जाता है कि उपरोक्त सामग्री का गेट पर भौतिक निरीक्षण किया गया एवं विवरण अनुसार सही पाई गई।',
  defaultMeasurementUnit: 'इंच (Inches)',
  defaultWeightUnit: 'टन (Tonnes)',
  requireWeighbridge: true,
  requirePhotos: false,
  requireReceiverSignature: true,
  gates: ['गेट नंबर 1 (मुख्य गेट)', 'गेट नंबर 2 (ब्लॉक यार्ड)']
};

const defaultMasters: MasterData = {
  suppliers: [
    'मकराना मार्बल माइन्स प्राइवेट लिमिटेड',
    'अंबिका स्टोन सप्लायर्स, राजसमंद',
    'भवानी मार्बल एंड मिनरल्स, उदयपुर',
    'श्री राम ग्रेनाइट क्वेरीज़, जालौर',
    'गुजरात सैंडस्टोन ट्रेडिंग कॉर्पोरेशन'
  ],
  varieties: [
    'मकराना वाइट (Makrana White)',
    'राजनगर वाइट (Rajnagar White)',
    'अम्बाजी वाइट (Ambaji White)',
    'वियतनाम वाइट (Vietnam White)',
    'ग्रीन मार्बल (Green Marble)',
    'जालौर ब्लैक ग्रेनाइट (Black Granite)',
    'आर कट मार्बल ब्लॉक (R-Cut Block)',
    'सैंडस्टोन रफ ब्लॉक (Sandstone Rough)'
  ],
  frequentDrivers: [
    { name: 'रामनिवास गुर्जर', mobile: '9828112233', vehicle: 'RJ-01-GA-4589' },
    { name: 'बलवंत सिंह राठौड़', mobile: '9414223344', vehicle: 'RJ-14-GH-7812' },
    { name: 'शौकत अली', mobile: '9929334455', vehicle: 'RJ-21-GB-3321' },
    { name: 'महेंद्र चौधरी', mobile: '9784556677', vehicle: 'RJ-09-GA-9045' }
  ],
  frequentVehicles: [
    'RJ-01-GA-4589',
    'RJ-14-GH-7812',
    'RJ-21-GB-3321',
    'RJ-09-GA-9045',
    'GJ-12-AX-5544'
  ]
};

const defaultUsers: UserAccount[] = [
  { id: 'usr-1', name: 'रामेश्वर जाट (गेट ऑपरेटर)', role: 'worker', gateName: 'गेट नंबर 1 (मुख्य गेट)', pin: '1234' },
  { id: 'usr-2', name: 'सुरेश कुमावत (गेट ऑपरेटर)', role: 'worker', gateName: 'गेट नंबर 2 (ब्लॉक यार्ड)', pin: '5678' },
  { id: 'usr-3', name: 'मुकेश शर्मा (मालिक / एडमिन)', role: 'admin', gateName: 'मुख्यालय / ऑफिस', pin: '9999' }
];

const seedGrns: GoodsReceiptNote[] = [
  {
    id: 'grn-seed-1',
    grnNumber: 'GRN-2026-0001',
    isProvisional: false,
    date: '2026-10-20',
    time: '10:30',
    gateName: 'गेट नंबर 1 (मुख्य गेट)',
    receiverName: 'रामेश्वर जाट (गेट ऑपरेटर)',
    receiverRole: 'गेट ऑपरेटर',
    supplierName: 'मकराना मार्बल माइन्स प्राइवेट लिमिटेड',
    supplierQuarry: 'डूंगरी रेंज खदान 4',
    challanNumber: 'CH-8841',
    challanDate: '2026-10-20',
    vehicleNumber: 'RJ-01-GA-4589',
    driverName: 'रामनिवास गुर्जर',
    driverMobile: '9828112233',
    ewayBillNumber: '921820491823',
    materialType: 'मार्बल ब्लॉक',
    blocks: [
      {
        id: 'blk-1',
        blockNumber: 'M-104',
        variety: 'मकराना वाइट (Makrana White)',
        pieces: 1,
        length: 96,
        width: 60,
        height: 54,
        unit: 'इंच (Inches)',
        estimatedVolume: 180.0,
        volumeUnit: 'घन फीट (CFT)',
        weight: 15.2,
        weightUnit: 'टन (Tonnes)',
        condition: 'ठीक',
        inspectionStatus: 'स्वीकृत',
        remarks: 'प्रीमियम क्वालिटी, कोई क्रैक नहीं'
      },
      {
        id: 'blk-2',
        blockNumber: 'M-105',
        variety: 'मकराना वाइट (Makrana White)',
        pieces: 1,
        length: 84,
        width: 52,
        height: 48,
        unit: 'इंच (Inches)',
        estimatedVolume: 121.3,
        volumeUnit: 'घन फीट (CFT)',
        weight: 10.5,
        weightUnit: 'टन (Tonnes)',
        condition: 'दरार',
        inspectionStatus: 'जांच बाकी',
        remarks: 'ऊपरी कोने पर हेयरलाइन क्रैक'
      }
    ],
    weighbridge: {
      enabled: true,
      grossWeight: 42.8,
      tareWeight: 17.1,
      netWeight: 25.7,
      unit: 'टन (Tonnes)',
      slipNumber: 'WB-99120',
      weighbridgeName: 'किशनगढ़ धर्मकांटा'
    },
    photos: {},
    generalRemarks: 'वाहन समय पर पहुंचा। ब्लॉक अनलोडिंग यार्ड B में रखी गई।',
    status: 'जांच बाकी',
    createdAt: '2026-10-20T10:35:00.000Z',
    updatedAt: '2026-10-20T10:35:00.000Z',
    createdBy: 'रामेश्वर जाट (गेट ऑपरेटर)',
    syncStatus: 'सर्वर पर सुरक्षित',
    revisions: [],
    totalBlocks: 2,
    totalPieces: 2,
    totalVolumeEstimateCft: 301.3,
    totalNetWeightTonnes: 25.7
  },
  {
    id: 'grn-seed-2',
    grnNumber: 'GRN-2026-0002',
    isProvisional: false,
    date: '2026-10-21',
    time: '08:15',
    gateName: 'गेट नंबर 2 (ब्लॉक यार्ड)',
    receiverName: 'सुरेश कुमावत (गेट ऑपरेटर)',
    receiverRole: 'गेट ऑपरेटर',
    supplierName: 'श्री राम ग्रेनाइट क्वेरीज़, जालौर',
    challanNumber: 'JLR-4402',
    challanDate: '2026-10-20',
    vehicleNumber: 'RJ-21-GB-3321',
    driverName: 'शौकत अली',
    driverMobile: '9929334455',
    materialType: 'पत्थर/स्टोन ब्लॉक',
    blocks: [
      {
        id: 'blk-3',
        blockNumber: 'J-771',
        variety: 'जालौर ब्लैक ग्रेनाइट (Black Granite)',
        pieces: 1,
        length: 110,
        width: 65,
        height: 60,
        unit: 'इंच (Inches)',
        estimatedVolume: 248.3,
        volumeUnit: 'घन फीट (CFT)',
        weight: 22.4,
        weightUnit: 'टन (Tonnes)',
        condition: 'ठीक',
        inspectionStatus: 'स्वीकृत',
        remarks: 'सटीक कटिंग, एक्सपोर्ट ग्रेड'
      }
    ],
    weighbridge: {
      enabled: true,
      grossWeight: 38.4,
      tareWeight: 16.0,
      netWeight: 22.4,
      unit: 'टन (Tonnes)',
      slipNumber: 'WB-99158',
      weighbridgeName: 'किशनगढ़ धर्मकांटा'
    },
    photos: {},
    generalRemarks: 'सभी दस्तावेज सही पाए गए।',
    status: 'स्वीकृत',
    createdAt: '2026-10-21T08:20:00.000Z',
    updatedAt: '2026-10-21T08:20:00.000Z',
    createdBy: 'सुरेश कुमावत (गेट ऑपरेटर)',
    syncStatus: 'सर्वर पर सुरक्षित',
    revisions: [],
    totalBlocks: 1,
    totalPieces: 1,
    totalVolumeEstimateCft: 248.3,
    totalNetWeightTonnes: 22.4
  }
];

function readDb(): DatabaseSchema {
  try {
    if (fs.existsSync(DB_FILE)) {
      const data = fs.readFileSync(DB_FILE, 'utf-8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error('Error reading db.json, returning default schema:', err);
  }
  const initial: DatabaseSchema = {
    settings: defaultSettings,
    masters: defaultMasters,
    users: defaultUsers,
    grns: seedGrns,
    nextSequenceNumber: 3
  };
  writeDb(initial);
  return initial;
}

function writeDb(data: DatabaseSchema) {
  try {
    const tempFile = `${DB_FILE}.tmp`;
    fs.writeFileSync(tempFile, JSON.stringify(data, null, 2), 'utf-8');
    fs.renameSync(tempFile, DB_FILE);
  } catch (err) {
    console.error('Error writing db.json:', err);
  }
}

async function startServer() {
  const app = express();
  app.use(express.json({ limit: '25mb' }));

  // Initialize DB
  readDb();

  // API Routes
  app.get('/api/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  // Users / Auth
  app.get('/api/users', (_req: Request, res: Response) => {
    const db = readDb();
    // Return users without sensitive fields if needed, but pins are fine in local factory setup
    res.json(db.users.map(u => ({ id: u.id, name: u.name, role: u.role, gateName: u.gateName })));
  });

  app.post('/api/auth/login', (req: Request, res: Response) => {
    const { userId, pin } = req.body;
    const db = readDb();
    const user = db.users.find(u => u.id === userId && u.pin === pin);
    if (!user) {
      return res.status(401).json({ error: 'गलत पिन (PIN) या उपयोगकर्ता' });
    }
    return res.json({
      user: {
        id: user.id,
        name: user.name,
        role: user.role,
        gateName: user.gateName
      },
      token: `token-${user.id}-${Date.now()}`
    });
  });

  // Settings
  app.get('/api/settings', (_req: Request, res: Response) => {
    const db = readDb();
    res.json(db.settings);
  });

  app.put('/api/settings', (req: Request, res: Response) => {
    const db = readDb();
    db.settings = { ...db.settings, ...req.body };
    writeDb(db);
    res.json(db.settings);
  });

  // Master Data
  app.get('/api/masters', (_req: Request, res: Response) => {
    const db = readDb();
    res.json(db.masters);
  });

  app.put('/api/masters', (req: Request, res: Response) => {
    const db = readDb();
    db.masters = { ...db.masters, ...req.body };
    writeDb(db);
    res.json(db.masters);
  });

  // Check Duplicate Receipt
  app.post('/api/grn/check-duplicate', (req: Request, res: Response) => {
    const { supplierName, challanNumber, vehicleNumber } = req.body;
    const db = readDb();
    if (!supplierName || !challanNumber) {
      return res.json({ duplicate: false });
    }
    const cleanSupplier = supplierName.trim().toLowerCase();
    const cleanChallan = challanNumber.trim().toLowerCase();
    const cleanVehicle = (vehicleNumber || '').trim().toLowerCase();

    const existing = db.grns.find(g => 
      g.status !== 'रद्द' &&
      g.supplierName.trim().toLowerCase() === cleanSupplier &&
      g.challanNumber.trim().toLowerCase() === cleanChallan &&
      (!cleanVehicle || g.vehicleNumber.trim().toLowerCase() === cleanVehicle)
    );

    if (existing) {
      return res.json({
        duplicate: true,
        existingGrnNumber: existing.grnNumber,
        existingDate: existing.date,
        existingTime: existing.time,
        supplierName: existing.supplierName,
        vehicleNumber: existing.vehicleNumber,
        challanNumber: existing.challanNumber
      });
    }

    return res.json({ duplicate: false });
  });

  // List GRNs with filtering
  app.get('/api/grn', (req: Request, res: Response) => {
    const db = readDb();
    let results = [...db.grns];

    const { search, supplier, vehicle, status, startDate, endDate } = req.query;

    if (search && typeof search === 'string') {
      const q = search.trim().toLowerCase();
      results = results.filter(g => 
        g.grnNumber.toLowerCase().includes(q) ||
        g.supplierName.toLowerCase().includes(q) ||
        g.vehicleNumber.toLowerCase().includes(q) ||
        g.challanNumber.toLowerCase().includes(q) ||
        g.blocks.some(b => b.blockNumber.toLowerCase().includes(q) || b.variety.toLowerCase().includes(q))
      );
    }

    if (supplier && typeof supplier === 'string') {
      results = results.filter(g => g.supplierName.includes(supplier));
    }

    if (vehicle && typeof vehicle === 'string') {
      results = results.filter(g => g.vehicleNumber.toLowerCase().includes(vehicle.toLowerCase()));
    }

    if (status && typeof status === 'string' && status !== 'सभी') {
      results = results.filter(g => g.status === status);
    }

    if (startDate && typeof startDate === 'string') {
      results = results.filter(g => g.date >= startDate);
    }

    if (endDate && typeof endDate === 'string') {
      results = results.filter(g => g.date <= endDate);
    }

    // Sort newest first
    results.sort((a, b) => new Date(`${b.date}T${b.time || '00:00'}`).getTime() - new Date(`${a.date}T${a.time || '00:00'}`).getTime());

    res.json(results);
  });

  // Get single GRN
  app.get('/api/grn/:id', (req: Request, res: Response) => {
    const db = readDb();
    const grn = db.grns.find(g => g.id === req.params.id || g.grnNumber === req.params.id);
    if (!grn) {
      return res.status(404).json({ error: 'रसीद नहीं मिली' });
    }
    res.json(grn);
  });

  // Helper to generate next official GRN number
  function getNextGrnNumber(db: DatabaseSchema): string {
    const year = new Date().getFullYear();
    const seq = db.nextSequenceNumber;
    db.nextSequenceNumber += 1;
    const formattedSeq = String(seq).padStart(4, '0');
    return `GRN-${year}-${formattedSeq}`;
  }

  // Create new GRN
  app.post('/api/grn', (req: Request, res: Response) => {
    const db = readDb();
    const body = req.body as Partial<GoodsReceiptNote>;

    // Sequential GRN number
    const officialGrnNumber = getNextGrnNumber(db);
    const now = new Date();

    const newGrn: GoodsReceiptNote = {
      id: `grn-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      grnNumber: officialGrnNumber,
      provisionalId: body.provisionalId,
      isProvisional: false,
      date: body.date || now.toISOString().split('T')[0],
      time: body.time || now.toTimeString().substring(0, 5),
      gateName: body.gateName || 'गेट नंबर 1 (मुख्य गेट)',
      receiverName: body.receiverName || 'गेट ऑपरेटर',
      receiverRole: body.receiverRole || 'गेट ऑपरेटर',

      supplierName: body.supplierName || 'अज्ञात सप्लायर',
      supplierQuarry: body.supplierQuarry || '',
      challanNumber: body.challanNumber || '',
      challanDate: body.challanDate || body.date || now.toISOString().split('T')[0],
      vehicleNumber: (body.vehicleNumber || '').toUpperCase().trim(),
      driverName: body.driverName || '',
      driverMobile: body.driverMobile || '',
      ewayBillNumber: body.ewayBillNumber || '',

      materialType: body.materialType || 'मार्बल ब्लॉक',
      blocks: body.blocks || [],
      weighbridge: body.weighbridge || {
        enabled: false,
        grossWeight: 0,
        tareWeight: 0,
        netWeight: 0,
        unit: 'टन (Tonnes)'
      },

      photos: body.photos || {},
      receiverSignature: body.receiverSignature,
      driverSignature: body.driverSignature,

      generalRemarks: body.generalRemarks || '',
      status: body.status || 'स्वीकृत',

      createdAt: now.toISOString(),
      updatedAt: now.toISOString(),
      createdBy: body.createdBy || body.receiverName || 'गेट ऑपरेटर',
      syncStatus: 'सर्वर पर सुरक्षित',
      revisions: [],

      totalBlocks: body.blocks ? body.blocks.length : 0,
      totalPieces: body.blocks ? body.blocks.reduce((sum, b) => sum + (Number(b.pieces) || 1), 0) : 0,
      totalVolumeEstimateCft: body.blocks ? Number(body.blocks.reduce((sum, b) => sum + (Number(b.estimatedVolume) || 0), 0).toFixed(2)) : 0,
      totalNetWeightTonnes: body.weighbridge?.enabled ? Number(body.weighbridge.netWeight || 0) : 0
    };

    // Update masters with any new supplier, vehicle, driver
    if (newGrn.supplierName && !db.masters.suppliers.includes(newGrn.supplierName)) {
      db.masters.suppliers.push(newGrn.supplierName);
    }
    if (newGrn.vehicleNumber && !db.masters.frequentVehicles.includes(newGrn.vehicleNumber)) {
      db.masters.frequentVehicles.push(newGrn.vehicleNumber);
    }

    db.grns.unshift(newGrn);
    writeDb(db);

    res.status(201).json(newGrn);
  });

  // Batch Sync from offline queue
  app.post('/api/sync', (req: Request, res: Response) => {
    const db = readDb();
    const items = req.body.items as GoodsReceiptNote[];

    if (!Array.isArray(items) || items.length === 0) {
      return res.json({ synced: [], message: 'कोई नया सिंक आइटम नहीं' });
    }

    const syncedResults: { provisionalId: string; officialGrnNumber: string; id: string }[] = [];

    for (const item of items) {
      // Idempotency check: see if provisionalId was already synced!
      const existing = db.grns.find(g => 
        (item.provisionalId && g.provisionalId === item.provisionalId) ||
        (item.id && g.id === item.id)
      );

      if (existing) {
        syncedResults.push({
          provisionalId: item.provisionalId || item.id,
          officialGrnNumber: existing.grnNumber,
          id: existing.id
        });
        continue;
      }

      // Assign new sequential GRN
      const officialGrnNumber = getNextGrnNumber(db);
      const syncedRecord: GoodsReceiptNote = {
        ...item,
        id: `grn-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        grnNumber: officialGrnNumber,
        isProvisional: false,
        syncStatus: 'सर्वर पर सुरक्षित',
        updatedAt: new Date().toISOString()
      };

      db.grns.unshift(syncedRecord);
      syncedResults.push({
        provisionalId: item.provisionalId || item.id,
        officialGrnNumber: officialGrnNumber,
        id: syncedRecord.id
      });
    }

    writeDb(db);
    res.json({ synced: syncedResults, totalSynced: syncedResults.length });
  });

  // Update GRN (Revision) - preserves snapshot history
  app.put('/api/grn/:id', (req: Request, res: Response) => {
    const db = readDb();
    const index = db.grns.findIndex(g => g.id === req.params.id);
    if (index === -1) {
      return res.status(404).json({ error: 'रसीद नहीं मिली' });
    }

    const current = db.grns[index];
    const { revisionReason, editorName, ...updatedFields } = req.body;

    const newRevision: GrnRevision = {
      revisionNumber: (current.revisions?.length || 0) + 1,
      revisedBy: editorName || 'सुपरवाइजर',
      revisedAt: new Date().toISOString(),
      reason: revisionReason || 'विवरण सुधार',
      previousSnapshot: { ...current, revisions: [] }
    };

    const updatedGrn: GoodsReceiptNote = {
      ...current,
      ...updatedFields,
      updatedAt: new Date().toISOString(),
      revisions: [...(current.revisions || []), newRevision],
      totalBlocks: updatedFields.blocks ? updatedFields.blocks.length : current.totalBlocks,
      totalPieces: updatedFields.blocks ? updatedFields.blocks.reduce((sum: number, b: any) => sum + (Number(b.pieces) || 1), 0) : current.totalPieces,
      totalVolumeEstimateCft: updatedFields.blocks ? Number(updatedFields.blocks.reduce((sum: number, b: any) => sum + (Number(b.estimatedVolume) || 0), 0).toFixed(2)) : current.totalVolumeEstimateCft
    };

    db.grns[index] = updatedGrn;
    writeDb(db);
    res.json(updatedGrn);
  });

  // Cancel GRN (Soft-cancel with mandatory reason, never permanently deletes)
  app.post('/api/grn/:id/cancel', (req: Request, res: Response) => {
    const { cancellationReason, cancelledBy } = req.body;
    if (!cancellationReason || !cancellationReason.trim()) {
      return res.status(400).json({ error: 'रद्द करने का कारण अनिवार्य है।' });
    }

    const db = readDb();
    const index = db.grns.findIndex(g => g.id === req.params.id);
    if (index === -1) {
      return res.status(404).json({ error: 'रसीद नहीं मिली' });
    }

    const current = db.grns[index];
    current.status = 'रद्द';
    current.cancellationReason = cancellationReason.trim();
    current.cancelledBy = cancelledBy || 'मालिक / एडमिन';
    current.cancelledAt = new Date().toISOString();
    current.updatedAt = new Date().toISOString();

    writeDb(db);
    res.json(current);
  });

  // CSV Export with UTF-8 BOM for perfect Hindi rendering in Excel / Google Sheets
  app.get('/api/export-csv', (_req: Request, res: Response) => {
    const db = readDb();
    const header = [
      'रसीद नंबर (GRN No)',
      'दिनांक (Date)',
      'समय (Time)',
      'गेट (Gate)',
      'आपूर्तिकर्ता (Supplier)',
      'चालान नंबर (Challan No)',
      'गाड़ी नंबर (Vehicle No)',
      'ड्राइवर (Driver)',
      'ड्राइवर मोबाइल (Mobile)',
      'सामग्री प्रकार (Material)',
      'कुल ब्लॉक (Total Blocks)',
      'कुल टुकड़े (Total Pieces)',
      'अनुमानित आयतन घन फीट (CFT)',
      'धर्मकांटा शुद्ध वजन टन (Net Wt Tonnes)',
      'स्थिति (Status)',
      'प्राप्तकर्ता (Received By)'
    ].join(',');

    const rows = db.grns.map(g => [
      `"${g.grnNumber}"`,
      `"${g.date}"`,
      `"${g.time}"`,
      `"${g.gateName}"`,
      `"${g.supplierName.replace(/"/g, '""')}"`,
      `"${g.challanNumber}"`,
      `"${g.vehicleNumber}"`,
      `"${g.driverName.replace(/"/g, '""')}"`,
      `"${g.driverMobile || ''}"`,
      `"${g.materialType}"`,
      g.totalBlocks,
      g.totalPieces,
      g.totalVolumeEstimateCft,
      g.totalNetWeightTonnes,
      `"${g.status}"`,
      `"${g.receiverName.replace(/"/g, '""')}"`
    ].join(','));

    // Prepend UTF-8 BOM \uFEFF so Excel automatically opens Devanagari Hindi cleanly
    const csvContent = '\uFEFF' + [header, ...rows].join('\r\n');

    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="marble-gate-grn-export-${new Date().toISOString().split('T')[0]}.csv"`);
    res.send(csvContent);
  });

  // Setup Vite middleware for development
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa'
    });
    app.use(vite.middlewares);
  } else {
    // Serve production build
    app.use(express.static(path.join(__dirname, 'dist')));
    app.get('*', (_req: Request, res: Response) => {
      res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Marble Factory Gate GRN Server running at http://0.0.0.0:${PORT}`);
  });
}

startServer().catch(err => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
