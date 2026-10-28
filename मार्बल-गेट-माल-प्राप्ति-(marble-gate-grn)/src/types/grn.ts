export type MeasurementUnit = 'इंच (Inches)' | 'फीट (Feet)' | 'सेमी (cm)' | 'मीटर (m)';
export type WeightUnit = 'टन (Tonnes)' | 'किलो (Kg)' | 'क्विंटल (Quintals)';
export type BlockCondition = 'ठीक' | 'टूटा हुआ' | 'दरार' | 'अन्य';
export type InspectionStatus = 'स्वीकृत' | 'अस्वीकृत' | 'जांच बाकी';
export type GrnStatus = 'स्वीकृत' | 'जांच बाकी' | 'अस्वीकृत' | 'रद्द';
export type SyncStatus = 'सर्वर पर सुरक्षित' | 'सिंक बाकी' | 'इस डिवाइस पर सुरक्षित';
export type UserRole = 'worker' | 'admin';

export interface UserAccount {
  id: string;
  name: string;
  role: UserRole;
  gateName: string;
  pin: string;
}

export interface StoneBlock {
  id: string;
  blockNumber: string; // e.g. "BLK-890" or quarry marking
  variety: string; // e.g. "मकराना वाइट", "राजनगर मार्बल", "वियतनाम वाइट", "ग्रेनाइट"
  pieces: number; // default 1
  length: number;
  width: number;
  height: number;
  unit: MeasurementUnit;
  estimatedVolume: number; // calculated length x width x height converted to standard unit
  volumeUnit: string; // "घन फीट (CFT)" or "घन मीटर (CBM)"
  weight?: number; // optional block-level weight
  weightUnit?: WeightUnit;
  condition: BlockCondition;
  inspectionStatus: InspectionStatus;
  remarks?: string;
}

export interface WeighbridgeRecord {
  enabled: boolean;
  grossWeight: number; // सकल वजन (Gross)
  tareWeight: number; // खाली गाड़ी वजन (Tare)
  netWeight: number; // शुद्ध वजन (Net = Gross - Tare)
  unit: WeightUnit;
  slipNumber?: string; // धर्मकांटा पर्ची नंबर
  weighbridgeName?: string; // धर्मकांटा नाम
}

export interface GrnRevision {
  revisionNumber: number;
  revisedBy: string;
  revisedAt: string;
  reason: string;
  previousSnapshot: Partial<GoodsReceiptNote>;
}

export interface GoodsReceiptNote {
  id: string; // Server UUID or unique ID
  grnNumber: string; // Official sequential GRN number e.g. "GRN-2026-0001" or provisional "अस्थायी-XXXX"
  provisionalId?: string; // Used when generated offline
  isProvisional: boolean;
  date: string; // YYYY-MM-DD
  time: string; // HH:mm
  gateName: string;
  receiverName: string;
  receiverRole: string;

  // Supplier & Transport
  supplierName: string;
  supplierQuarry?: string;
  challanNumber: string;
  challanDate: string;
  vehicleNumber: string;
  driverName: string;
  driverMobile?: string;
  ewayBillNumber?: string;

  // Material & Blocks
  materialType: 'मार्बल ब्लॉक' | 'पत्थर/स्टोन ब्लॉक' | 'अन्य स्लैब/टाइल';
  blocks: StoneBlock[];

  // Weighbridge (धर्मकांटा)
  weighbridge: WeighbridgeRecord;

  // Photos & Signatures
  photos: {
    vehicle?: string; // base64 or url
    blocks?: string;
    challan?: string;
    weighbridgeSlip?: string;
  };
  receiverSignature?: string; // data URL
  driverSignature?: string; // data URL

  // Status & Metadata
  generalRemarks?: string;
  status: GrnStatus;
  cancellationReason?: string;
  cancelledBy?: string;
  cancelledAt?: string;

  createdAt: string;
  updatedAt: string;
  createdBy: string;
  syncStatus: SyncStatus;
  revisions: GrnRevision[];

  // Totals summary
  totalBlocks: number;
  totalPieces: number;
  totalVolumeEstimateCft: number;
  totalNetWeightTonnes: number;
}

export interface FactorySettings {
  factoryName: string;
  factoryTagline: string;
  factoryAddress: string;
  factoryPhone: string;
  factoryGstin: string;
  receiptTitle: string; // Default: "माल प्राप्ति रसीद (GOODS RECEIPT NOTE - GRN)"
  declarationText: string;
  defaultMeasurementUnit: MeasurementUnit;
  defaultWeightUnit: WeightUnit;
  requireWeighbridge: boolean;
  requirePhotos: boolean;
  requireReceiverSignature: boolean;
  gates: string[];
}

export interface MasterData {
  suppliers: string[];
  varieties: string[];
  frequentDrivers: { name: string; mobile: string; vehicle: string }[];
  frequentVehicles: string[];
}
