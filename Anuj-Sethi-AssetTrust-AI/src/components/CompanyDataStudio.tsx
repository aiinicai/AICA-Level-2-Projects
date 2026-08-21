import React, { useState, useRef } from 'react';
import { 
  Building2, 
  FileSpreadsheet, 
  FileText, 
  Plus, 
  Upload, 
  Download, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Sparkles, 
  Database, 
  Trash2, 
  Eye, 
  ArrowRight,
  HelpCircle,
  FileCheck,
  Tag,
  Factory,
  Layers,
  Search,
  ExternalLink
} from 'lucide-react';
import { 
  Company, 
  Asset, 
  CapexItem, 
  AssetCategory, 
  PlantLocation, 
  ParsedDocumentResult 
} from '../types';
import { 
  parseCsvToAssets, 
  parseCsvToCapex, 
  downloadAssetRegisterCsvTemplate, 
  downloadCapexQueueCsvTemplate,
  exportAssetsToCsv,
  exportCompanyBackupJson
} from '../services/dataImportExport';

interface CompanyDataStudioProps {
  activeCompany: Company;
  allCompanies: Company[];
  assets: Asset[];
  capexQueue: CapexItem[];
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  onSwitchCompany: (companyId: string) => void;
  onOpenCreateCompanyModal: () => void;
  onDeleteCompany: (companyId: string) => void;
  onImportAssets: (newAssets: Asset[], mode: 'append' | 'overwrite') => void;
  onImportCapex: (newCapex: CapexItem[]) => void;
  onAddManualAsset: (asset: Asset) => void;
  onResetToDefault?: () => void;
}

export const CompanyDataStudio: React.FC<CompanyDataStudioProps> = ({
  activeCompany,
  allCompanies,
  assets,
  capexQueue,
  currencyMode,
  onSwitchCompany,
  onOpenCreateCompanyModal,
  onDeleteCompany,
  onImportAssets,
  onImportCapex,
  onAddManualAsset,
  onResetToDefault
}) => {
  const [activeStudioTab, setActiveStudioTab] = useState<'spreadsheet' | 'pdf-ai' | 'manual' | 'entities'>('spreadsheet');

  // Spreadsheet State
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvContent, setCsvContent] = useState<string>('');
  const [importTarget, setImportTarget] = useState<'assets-append' | 'assets-overwrite' | 'capex-queue'>('assets-append');
  const [previewAssets, setPreviewAssets] = useState<Asset[]>([]);
  const [previewCapex, setPreviewCapex] = useState<CapexItem[]>([]);
  const [importErrors, setImportErrors] = useState<string[]>([]);
  const [importWarnings, setImportWarnings] = useState<string[]>([]);
  const [importSuccessMsg, setImportSuccessMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // PDF & Document AI State
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docBase64, setDocBase64] = useState<string | null>(null);
  const [docMimeType, setDocMimeType] = useState<string>('application/pdf');
  const [docRawText, setDocRawText] = useState<string>('');
  const [isAiParsing, setIsAiParsing] = useState<boolean>(false);
  const [parsedDocResult, setParsedDocResult] = useState<ParsedDocumentResult | null>(null);
  const [aiErrorMsg, setAiErrorMsg] = useState<string | null>(null);
  const docFileInputRef = useRef<HTMLInputElement>(null);

  // Manual Form State
  const [manualName, setManualName] = useState('');
  const [manualCategory, setManualCategory] = useState<AssetCategory>('Plant & Machinery');
  const [manualPlant, setManualPlant] = useState<string>(activeCompany.plants[0] || 'Pune Plant - Chakan');
  const [manualSubLocation, setManualSubLocation] = useState('Bay 1 - Main Production Hall');
  const [manualCost, setManualCost] = useState<number>(2500000);
  const [manualAccumDep, setManualAccumDep] = useState<number>(250000);
  const [manualCapDate, setManualCapDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [manualLife, setManualLife] = useState<number>(15);
  const [manualSchIILife, setManualSchIILife] = useState<number>(15);
  const [manualDepMethod, setManualDepMethod] = useState<'SLM' | 'WDV'>('SLM');
  const [manualSerial, setManualSerial] = useState(`SN-${activeCompany.shortCode}-${Date.now().toString().slice(-4)}`);
  const [manualCustodian, setManualCustodian] = useState('Plant In-Charge');
  const [manualDepartment, setManualDepartment] = useState('Operations & Manufacturing');
  const [manualVendor, setManualVendor] = useState('Siemens Industrial Ltd.');
  const [manualInvoice, setManualInvoice] = useState(`INV-${new Date().getFullYear()}-001`);
  const [manualPO, setManualPO] = useState(`PO-${new Date().getFullYear()}-001`);
  const [manualGstClaimed, setManualGstClaimed] = useState(true);
  const [manualDescription, setManualDescription] = useState('');
  const [enableComponents, setEnableComponents] = useState(true);

  // Stats calculation
  const totalGrossINR = assets.reduce((sum, a) => sum + a.costINR, 0);
  const totalNbvINR = assets.reduce((sum, a) => sum + a.nbvINR, 0);

  const formatCurrency = (amount: number) => {
    if (currencyMode === 'Crores') {
      return `₹${(amount / 10000000).toFixed(2)} Cr`;
    }
    if (currencyMode === 'Lakhs') {
      return `₹${(amount / 100000).toFixed(2)} L`;
    }
    return `₹${amount.toLocaleString('en-IN')}`;
  };

  // ----------------------------------------------------
  // SPREADSHEET IMPORT HANDLERS
  // ----------------------------------------------------
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    processCsvFile(file);
  };

  const processCsvFile = (file: File) => {
    setCsvFile(file);
    setImportSuccessMsg(null);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setCsvContent(text);
      validateAndPreviewCsv(text, importTarget);
    };
    reader.readAsText(file);
  };

  const validateAndPreviewCsv = (text: string, target: 'assets-append' | 'assets-overwrite' | 'capex-queue') => {
    setImportErrors([]);
    setImportWarnings([]);
    setPreviewAssets([]);
    setPreviewCapex([]);

    if (target === 'capex-queue') {
      const res = parseCsvToCapex(text, activeCompany.plants[0]);
      setPreviewCapex(res.data);
      setImportErrors(res.errors);
      setImportWarnings(res.warnings);
    } else {
      const res = parseCsvToAssets(text, activeCompany.plants[0]);
      setPreviewAssets(res.data);
      setImportErrors(res.errors);
      setImportWarnings(res.warnings);
    }
  };

  const handleApplySpreadsheetImport = () => {
    if (importTarget === 'capex-queue') {
      if (previewCapex.length === 0) return;
      onImportCapex(previewCapex);
      setImportSuccessMsg(`Successfully queued ${previewCapex.length} procurement items for AI Capitalisation Review!`);
      setPreviewCapex([]);
      setCsvFile(null);
    } else {
      if (previewAssets.length === 0) return;
      const mode = importTarget === 'assets-overwrite' ? 'overwrite' : 'append';
      onImportAssets(previewAssets, mode);
      setImportSuccessMsg(`Successfully imported ${previewAssets.length} fixed assets into ${activeCompany.name} register!`);
      setPreviewAssets([]);
      setCsvFile(null);
    }
  };

  const loadSampleSpreadsheet = () => {
    const sampleCsv = `Asset ID,Asset Name,Category,Plant Location,Sub Location / Bay,Gross Cost (INR),Accumulated Depreciation (INR),Capitalisation Date (YYYY-MM-DD),Useful Life (Years),Sch II Useful Life (Years),Depreciation Method (SLM/WDV),Serial Number,Custodian Name,Department,Vendor Name,Invoice Number,PO Number,GST Paid (INR),ITC Claimed (Yes/No),Description
AST-${activeCompany.shortCode}-CNC-01,5-Axis High Precision CNC Milling Center,Plant & Machinery,${activeCompany.plants[0] || 'Pune Plant - Chakan'},Bay 4 - Machining Cell,4850000,1212500,2022-04-15,15,15,SLM,DMG-MORI-IND-99418,Rajesh Kulkarni,Precision Manufacturing,DMG MORI India Pvt. Ltd.,INV-DMG-2022-8812,PO-2022-PUN-0841,873000,Yes,Heavy duty 5-axis vertical machining centre for tooling dies.
AST-${activeCompany.shortCode}-ROB-02,6-Axis Industrial Articulated Welding Robot,Plant & Machinery,${activeCompany.plants[0] || 'Pune Plant - Chakan'},Body Shop Line 2,3850000,770000,2023-01-20,12,12,SLM,FANUC-R2000-8812,Suresh Ramanathan,Body Shop Robotics,Fanuc India Pvt. Ltd.,INV-FNC-2023-4412,PO-2023-CHE-0912,693000,Yes,Automated spot-welding robotic arm cell.
AST-${activeCompany.shortCode}-SRV-03,High-Density Dual Xeon Enterprise Rack Server Cluster,IT Hardware & Servers,${activeCompany.plants[0] || 'Pune Plant - Chakan'},Data Center Rack A-04,1850000,616666,2023-08-10,6,6,SLM,DELL-EMC-R750-9941,Kavita Nair,Enterprise IT,Dell Technologies India,INV-DEL-2023-7721,PO-2023-BLR-1142,333000,Yes,Virtualization host cluster for ERP & PLM workload.
AST-${activeCompany.shortCode}-TRF-04,11kV / 433V Step-Down Dry Type Distribution Transformer,Plant & Machinery,${activeCompany.plants[0] || 'Pune Plant - Chakan'},Substation Yard Bay 1,2200000,440000,2022-11-05,15,15,SLM,ABB-DRY-TRF-9021,Pravin Solanki,Electrical Utility,Hitachi Energy India Ltd.,INV-HIT-2022-9901,PO-2022-PUN-0199,396000,Yes,Step-down dry-type auxiliary power transformer.`;

    setCsvContent(sampleCsv);
    setCsvFile(new File([sampleCsv], 'Sample_Fixed_Asset_Register.csv', { type: 'text/csv' }));
    validateAndPreviewCsv(sampleCsv, importTarget);
  };

  // ----------------------------------------------------
  // PDF & DOCUMENT AI HANDLERS
  // ----------------------------------------------------
  const handleDocFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setDocFile(file);
    setAiErrorMsg(null);
    setParsedDocResult(null);

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64Data = result.split(',')[1];
      setDocBase64(base64Data);
      setDocMimeType(file.type || 'application/pdf');
    };
    reader.readAsDataURL(file);
  };

  const handleParseDocumentWithAi = async () => {
    if (!docBase64 && !docRawText.trim()) return;

    setIsAiParsing(true);
    setAiErrorMsg(null);
    setParsedDocResult(null);

    try {
      const payload: any = {
        companyContext: {
          name: activeCompany.name,
          industry: activeCompany.industry,
          plants: activeCompany.plants
        }
      };

      if (docBase64) {
        payload.fileBase64 = docBase64;
        payload.mimeType = docMimeType;
      }
      if (docRawText.trim()) {
        payload.text = docRawText.trim();
      }

      const res = await fetch('/api/ai/parse-document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`Server responded with status ${res.status}`);
      }

      const json = await res.json();
      if (json.data) {
        setParsedDocResult(json.data);
      } else {
        throw new Error('No structured document data returned by parser.');
      }
    } catch (err: any) {
      console.error('AI Document Parsing Error:', err);
      setAiErrorMsg(err?.message || 'Failed to parse document with AI.');
    } finally {
      setIsAiParsing(false);
    }
  };

  const loadSampleDocText = (type: 'siemens' | 'dmg' | 'hvac') => {
    let sample = '';
    if (type === 'dmg') {
      sample = `TAX INVOICE / PURCHASE ORDER
M/S DMG MORI India Pvt. Ltd., Tech Park, Bangalore 560066
GSTIN: 29AAACD9912F1ZK
Invoice No: INV-DMG-2024-9104
Date: 2024-11-20
Buyer: ${activeCompany.name}
PO No: PO-${activeCompany.shortCode}-2024-8841

Item Particulars:
1. Model NTX 2000 2nd Generation High-Precision Turn-Mill CNC Center
   Serial No: NTX-IND-2024-99812
   Location: ${activeCompany.plants[0] || 'Pune Plant'} - Bay 3 Precision Line
   Gross Cost: Rs. 6,850,000.00
   CGST (9%): Rs. 616,500.00
   SGST (9%): Rs. 616,500.00
   Total Invoice Value: Rs. 8,083,000.00
   Component breakdown: Spindle assembly (6 yrs life, Rs. 2,055,000), Main Cast Iron Frame (15 yrs life, Rs. 4,795,000).`;
    } else if (type === 'siemens') {
      sample = `COMMERCIAL TAX INVOICE
Siemens Large Drives India Ltd., Kalwa Works, Thane 400601
Invoice: INV-SIE-2024-4412
Date: 2024-11-18
Customer: ${activeCompany.name}
PO: PO-${activeCompany.shortCode}-2024-1190

Description:
SINAMICS S120 High-Power Multi-Axis Drive System 250kW with Motor Modules & Active Line Module.
Serial Number: SIE-DRV-2024-0091
Delivered to: ${activeCompany.plants[0] || 'Pune Plant'} - Motor Control Center Room 2
Cost: INR 2,450,000.00 + 18% GST (INR 441,000.00).
Useful Life: 8 Years. Full ITC eligible under CGST Section 16.`;
    } else {
      sample = `CAPEX ASSET PROCUREMENT NOTE
Vendor: Voltas Electro-Mechanical Works
Invoice Ref: INV-VOL-2024-7711
Date: 2024-11-25
Destination: ${activeCompany.plants[0] || 'Main Manufacturing Facility'}
Asset Title: 150 TR Water-Cooled Central Screw Chiller & Primary Secondary Pump Skid
Cost: Rs. 3,200,000.00 (excl. 18% GST Rs. 576,000.00)
Department: Utility & Facilities Engineering
Useful Life: 15 Years (Companies Act Sch II Part C).`;
    }

    setDocRawText(sample);
    setDocBase64(null);
    setDocFile(null);
  };

  const handleCommitParsedAssetToRegister = () => {
    if (!parsedDocResult || !parsedDocResult.extractedAssets || parsedDocResult.extractedAssets.length === 0) return;

    const newAssets: Asset[] = parsedDocResult.extractedAssets.map((ea, idx) => {
      const assetId = `AST-${activeCompany.shortCode}-AI-${Date.now().toString().slice(-4)}${idx}`;
      return {
        id: assetId,
        name: ea.name || 'AI Ingested Equipment Asset',
        category: (ea.category as AssetCategory) || 'Plant & Machinery',
        plant: (ea.plant as any) || activeCompany.plants[0] || 'Pune Plant - Chakan',
        subLocation: ea.subLocation || 'Inbound Processing Area',
        costINR: ea.costINR || parsedDocResult.totalGrossAmountINR || 1500000,
        accumulatedDepINR: ea.accumulatedDepINR || 0,
        nbvINR: (ea.costINR || parsedDocResult.totalGrossAmountINR || 1500000) - (ea.accumulatedDepINR || 0),
        capitalisationDate: ea.capitalisationDate || parsedDocResult.documentDate || new Date().toISOString().split('T')[0],
        usefulLifeYears: ea.usefulLifeYears || 15,
        schIILifeYears: ea.schIILifeYears || ea.usefulLifeYears || 15,
        depreciationMethod: ea.depreciationMethod || 'SLM',
        verificationStatus: 'Verified',
        lastVerifiedDate: new Date().toISOString().split('T')[0],
        riskLevel: 'Clean',
        custodian: ea.custodian || 'Operations Manager',
        department: ea.department || 'Manufacturing',
        serialNumber: ea.serialNumber || `SN-${Date.now().toString().slice(-6)}`,
        qrCode: `QR-${assetId}`,
        vendor: ea.vendor || parsedDocResult.vendorName || 'Equipment Supplier',
        invoiceNumber: ea.invoiceNumber || parsedDocResult.invoiceNumber || 'INV-AI-001',
        poNumber: ea.poNumber || parsedDocResult.poNumber || 'PO-AI-001',
        grnNumber: `GRN-${Date.now().toString().slice(-5)}`,
        gstPaidINR: ea.gstPaidINR || parsedDocResult.gstAmountINR || Math.round((ea.costINR || 1500000) * 0.18),
        itcClaimed: true,
        description: ea.description || parsedDocResult.summaryNote || 'Asset ingested via AI document extractor.',
        components: (ea.components as any) || [],
        anomalies: [],
        status: 'Active',
        historyEvents: [
          {
            id: `EVT-${Date.now()}`,
            date: new Date().toISOString().split('T')[0],
            type: 'Procurement',
            description: `Ingested from ${parsedDocResult.documentType} (${parsedDocResult.documentReference || 'Doc'}) via AI Vision Parser.`,
            actor: 'AI Document Studio',
            status: 'Completed'
          }
        ]
      };
    });

    onImportAssets(newAssets, 'append');
    setImportSuccessMsg(`Successfully committed ${newAssets.length} asset(s) from document into ${activeCompany.name} Fixed Asset Register!`);
    setParsedDocResult(null);
    setDocRawText('');
    setDocFile(null);
  };

  const handleCommitParsedCapexToQueue = () => {
    if (!parsedDocResult || !parsedDocResult.extractedCapexItems || parsedDocResult.extractedCapexItems.length === 0) return;

    const newCapex: CapexItem[] = parsedDocResult.extractedCapexItems.map((ec, idx) => ({
      id: `CPX-AI-${Date.now().toString().slice(-4)}${idx}`,
      poNumber: ec.poNumber || parsedDocResult.poNumber || `PO-${Date.now().toString().slice(-4)}`,
      invoiceNumber: ec.invoiceNumber || parsedDocResult.invoiceNumber || `INV-${Date.now().toString().slice(-4)}`,
      vendor: ec.vendor || parsedDocResult.vendorName || 'Equipment Vendor',
      description: ec.description || parsedDocResult.summaryNote || 'Inbound Procurement Item',
      amountINR: ec.amountINR || parsedDocResult.totalGrossAmountINR || 1500000,
      invoiceDate: ec.invoiceDate || parsedDocResult.documentDate || new Date().toISOString().split('T')[0],
      plant: (ec.plant as any) || activeCompany.plants[0] || 'Pune Plant - Chakan',
      department: ec.department || 'Operations',
      grnStatus: 'Complete',
      technicalInspection: 'Passed',
      suggestedCategory: (ec.suggestedCategory as any) || 'Plant & Machinery',
      status: 'Pending AI Review'
    }));

    onImportCapex(newCapex);
    setImportSuccessMsg(`Successfully pushed ${newCapex.length} procurement item(s) to AI Capitalisation Review Queue!`);
    setParsedDocResult(null);
    setDocRawText('');
    setDocFile(null);
  };

  // ----------------------------------------------------
  // MANUAL ENTRY SUBMIT HANDLER
  // ----------------------------------------------------
  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualName.trim() || manualCost <= 0) return;

    const newAssetId = `AST-${activeCompany.shortCode}-MAN-${Date.now().toString().slice(-4)}`;
    const nbv = Math.max(0, manualCost - manualAccumDep);

    let components = [];
    if (enableComponents) {
      components = [
        {
          id: `${newAssetId}-CMP-1`,
          name: `${manualName} (Core Mechanical & Structural Assembly)`,
          costINR: Math.round(manualCost * 0.7),
          usefulLifeYears: manualLife,
          depreciationMethod: manualDepMethod,
          accumulatedDepINR: Math.round(manualAccumDep * 0.7),
          nbvINR: Math.round(nbv * 0.7),
          notes: 'Long-life core structural component'
        },
        {
          id: `${newAssetId}-CMP-2`,
          name: `${manualName} (Electrical / Digital Control Unit)`,
          costINR: Math.round(manualCost * 0.3),
          usefulLifeYears: Math.min(6, manualLife),
          depreciationMethod: manualDepMethod,
          accumulatedDepINR: Math.round(manualAccumDep * 0.3),
          nbvINR: Math.round(nbv * 0.3),
          notes: 'High-wear electronics / drive control block'
        }
      ];
    }

    const newAsset: Asset = {
      id: newAssetId,
      name: manualName.trim(),
      category: manualCategory,
      plant: manualPlant as PlantLocation,
      subLocation: manualSubLocation.trim() || 'Main Production Bay',
      costINR: manualCost,
      accumulatedDepINR: manualAccumDep,
      nbvINR: nbv,
      capitalisationDate: manualCapDate,
      usefulLifeYears: manualLife,
      schIILifeYears: manualSchIILife,
      depreciationMethod: manualDepMethod,
      verificationStatus: 'Verified',
      lastVerifiedDate: new Date().toISOString().split('T')[0],
      riskLevel: 'Clean',
      custodian: manualCustodian.trim() || 'Plant Lead',
      department: manualDepartment.trim() || 'Operations',
      serialNumber: manualSerial.trim() || `SN-${Date.now().toString().slice(-6)}`,
      qrCode: `QR-${newAssetId}`,
      vendor: manualVendor.trim() || 'Equipment Supplier',
      invoiceNumber: manualInvoice.trim() || `INV-${Date.now().toString().slice(-4)}`,
      poNumber: manualPO.trim() || `PO-${Date.now().toString().slice(-4)}`,
      grnNumber: `GRN-${Date.now().toString().slice(-5)}`,
      gstPaidINR: manualGstClaimed ? Math.round(manualCost * 0.18) : undefined,
      itcClaimed: manualGstClaimed,
      description: manualDescription.trim() || `${manualName.trim()} registered manually in subledger.`,
      components,
      anomalies: [],
      status: 'Active',
      historyEvents: [
        {
          id: `EVT-${Date.now()}`,
          date: new Date().toISOString().split('T')[0],
          type: 'Procurement',
          description: 'Manually entered into Fixed Asset Register with Ind AS 16 component breakdown.',
          actor: 'Finance Controller',
          status: 'Completed'
        }
      ]
    };

    onAddManualAsset(newAsset);
    setImportSuccessMsg(`Asset '${newAsset.name}' (ID: ${newAsset.id}) registered successfully!`);
    
    // Reset form
    setManualName('');
    setManualCost(2500000);
    setManualAccumDep(250000);
    setManualSerial(`SN-${activeCompany.shortCode}-${Date.now().toString().slice(-4)}`);
    setManualDescription('');
  };

  return (
    <div className="space-y-6">
      
      {/* Active Entity Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-start space-x-4">
            <div className={`w-14 h-14 rounded-2xl bg-linear-to-br ${activeCompany.logoColor || 'from-blue-600 to-indigo-700'} flex items-center justify-center text-white shadow-md font-bold text-xl shrink-0`}>
              {activeCompany.shortCode}
            </div>
            <div>
              <div className="flex items-center space-x-2.5 flex-wrap gap-y-1">
                <h1 className="text-xl font-bold text-slate-900">{activeCompany.name}</h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                  {activeCompany.industry}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                  CIN: {activeCompany.cin}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                GSTIN: <span className="font-mono text-slate-700 font-medium">{activeCompany.gstin}</span> • Depreciation: <span className="text-slate-700 font-medium">{activeCompany.depreciationPolicy}</span> • Fiscal: <span className="text-slate-700 font-medium">{activeCompany.fiscalYear}</span>
              </p>
              <div className="flex items-center space-x-2 mt-2 text-xs text-slate-600 flex-wrap gap-1">
                <span className="font-semibold text-slate-700">Hubs ({activeCompany.plants.length}):</span>
                {activeCompany.plants.map((p, idx) => (
                  <span key={idx} className="bg-slate-50 px-2 py-0.5 rounded-md border border-slate-200 text-slate-600">
                    {p}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Metrics & Actions */}
          <div className="flex flex-wrap items-center gap-3 lg:self-center shrink-0">
            <div className="bg-slate-50 px-4 py-2 rounded-xl border border-slate-200 text-center">
              <span className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Subledger Assets</span>
              <span className="text-lg font-bold text-slate-900">{assets.length}</span>
            </div>

            <div className="bg-slate-50 px-4 py-2 rounded-xl border border-slate-200 text-center">
              <span className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Gross Block</span>
              <span className="text-lg font-bold text-blue-600">{formatCurrency(totalGrossINR)}</span>
            </div>

            <button
              onClick={onOpenCreateCompanyModal}
              className="px-3.5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs flex items-center space-x-1.5 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>New Company</span>
            </button>
          </div>
        </div>
      </div>

      {/* Success Notification Alert */}
      {importSuccessMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-emerald-800 text-xs font-medium animate-in fade-in duration-200">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>{importSuccessMsg}</span>
          </div>
          <button
            onClick={() => setImportSuccessMsg(null)}
            className="text-emerald-600 hover:text-emerald-800 font-bold ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Studio Navigation Tabs */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="border-b border-slate-200 px-6 pt-4 flex items-center space-x-6 overflow-x-auto">
          <button
            onClick={() => setActiveStudioTab('spreadsheet')}
            className={`pb-3 text-xs font-bold flex items-center space-x-2 border-b-2 transition-all whitespace-nowrap ${
              activeStudioTab === 'spreadsheet'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span>Excel & CSV Spreadsheet Ingestion</span>
          </button>

          <button
            onClick={() => setActiveStudioTab('pdf-ai')}
            className={`pb-3 text-xs font-bold flex items-center space-x-2 border-b-2 transition-all whitespace-nowrap ${
              activeStudioTab === 'pdf-ai'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Sparkles className="w-4 h-4 text-purple-600" />
            <span>PDF & Vendor Document AI Parser</span>
          </button>

          <button
            onClick={() => setActiveStudioTab('manual')}
            className={`pb-3 text-xs font-bold flex items-center space-x-2 border-b-2 transition-all whitespace-nowrap ${
              activeStudioTab === 'manual'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Plus className="w-4 h-4" />
            <span>Manual Asset Entry & Component Split</span>
          </button>

          <button
            onClick={() => setActiveStudioTab('entities')}
            className={`pb-3 text-xs font-bold flex items-center space-x-2 border-b-2 transition-all whitespace-nowrap ${
              activeStudioTab === 'entities'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Entities & Export Hub ({allCompanies.length})</span>
          </button>
        </div>

        <div className="p-6">
          
          {/* ========================================================================= */}
          {/* TAB 1: SPREADSHEET INGESTION (CSV & EXCEL) */}
          {/* ========================================================================= */}
          {activeStudioTab === 'spreadsheet' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Upload Fixed Asset Register or Capex Schedule</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Import existing ERP asset records (SAP, Oracle, Tally, Microsoft Dynamics) in CSV format.
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={downloadAssetRegisterCsvTemplate}
                    className="px-3 py-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold flex items-center space-x-1.5 shadow-2xs"
                  >
                    <Download className="w-3.5 h-3.5 text-blue-600" />
                    <span>Download FAR Template.csv</span>
                  </button>
                  <button
                    onClick={downloadCapexQueueCsvTemplate}
                    className="px-3 py-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold flex items-center space-x-1.5 shadow-2xs"
                  >
                    <Download className="w-3.5 h-3.5 text-purple-600" />
                    <span>Capex Template.csv</span>
                  </button>
                </div>
              </div>

              {/* Upload Drop Zone & Controls */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Left Upload Box */}
                <div className="lg:col-span-2 space-y-4">
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-slate-300 hover:border-blue-500 bg-slate-50/50 hover:bg-blue-50/30 rounded-2xl p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center space-y-3"
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,.txt,.tsv"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                    <div className="w-12 h-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shadow-xs">
                      <Upload className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-800">
                        {csvFile ? csvFile.name : 'Click to select or drag & drop CSV spreadsheet'}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Supports UTF-8 CSV with column headers (Asset ID, Name, Cost, Capitalisation Date, Plant, etc.)
                      </p>
                    </div>
                    {csvFile && (
                      <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">
                        {(csvFile.size / 1024).toFixed(1)} KB loaded
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Don't have a CSV file ready right now?</span>
                    <button
                      onClick={loadSampleSpreadsheet}
                      className="text-blue-600 hover:text-blue-800 font-bold underline flex items-center space-x-1"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blue-500" />
                      <span>Load Sample {activeCompany.name} Register CSV</span>
                    </button>
                  </div>
                </div>

                {/* Right Configuration Card */}
                <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200 space-y-4">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Import Destination & Mode
                  </h4>

                  <div className="space-y-2">
                    <label
                      className={`flex items-start space-x-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                        importTarget === 'assets-append'
                          ? 'border-blue-600 bg-white ring-1 ring-blue-500 shadow-2xs'
                          : 'border-slate-200 bg-white hover:bg-slate-100'
                      }`}
                    >
                      <input
                        type="radio"
                        name="importTarget"
                        checked={importTarget === 'assets-append'}
                        onChange={() => {
                          setImportTarget('assets-append');
                          if (csvContent) validateAndPreviewCsv(csvContent, 'assets-append');
                        }}
                        className="mt-0.5 text-blue-600"
                      />
                      <div>
                        <span className="block text-xs font-bold text-slate-900">Append to Subledger</span>
                        <span className="block text-[11px] text-slate-500">
                          Adds new asset records without deleting existing items in {activeCompany.name}.
                        </span>
                      </div>
                    </label>

                    <label
                      className={`flex items-start space-x-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                        importTarget === 'assets-overwrite'
                          ? 'border-rose-600 bg-white ring-1 ring-rose-500 shadow-2xs'
                          : 'border-slate-200 bg-white hover:bg-slate-100'
                      }`}
                    >
                      <input
                        type="radio"
                        name="importTarget"
                        checked={importTarget === 'assets-overwrite'}
                        onChange={() => {
                          setImportTarget('assets-overwrite');
                          if (csvContent) validateAndPreviewCsv(csvContent, 'assets-overwrite');
                        }}
                        className="mt-0.5 text-rose-600"
                      />
                      <div>
                        <span className="block text-xs font-bold text-rose-900">Overwrite / Replace Subledger</span>
                        <span className="block text-[11px] text-rose-600">
                          Replaces current {assets.length} assets with newly parsed CSV records.
                        </span>
                      </div>
                    </label>

                    <label
                      className={`flex items-start space-x-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                        importTarget === 'capex-queue'
                          ? 'border-purple-600 bg-white ring-1 ring-purple-500 shadow-2xs'
                          : 'border-slate-200 bg-white hover:bg-slate-100'
                      }`}
                    >
                      <input
                        type="radio"
                        name="importTarget"
                        checked={importTarget === 'capex-queue'}
                        onChange={() => {
                          setImportTarget('capex-queue');
                          if (csvContent) validateAndPreviewCsv(csvContent, 'capex-queue');
                        }}
                        className="mt-0.5 text-purple-600"
                      />
                      <div>
                        <span className="block text-xs font-bold text-purple-900">Inbound Capex Queue</span>
                        <span className="block text-[11px] text-purple-600">
                          Send parsed items to AI Review for Ind AS 16 componentisation & GST analysis.
                        </span>
                      </div>
                    </label>
                  </div>

                  {/* Actions */}
                  <div className="pt-2">
                    <button
                      onClick={handleApplySpreadsheetImport}
                      disabled={previewAssets.length === 0 && previewCapex.length === 0}
                      className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-xs font-bold shadow-xs flex items-center justify-center space-x-2 transition-all"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>
                        Commit Import ({previewAssets.length || previewCapex.length} Records)
                      </span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Validation Feedback & Errors */}
              {importErrors.length > 0 && (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-1">
                  <div className="flex items-center space-x-2 text-rose-800 font-bold text-xs">
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    <span>Validation Errors ({importErrors.length}):</span>
                  </div>
                  <ul className="list-disc pl-5 text-xs text-rose-700 space-y-0.5">
                    {importErrors.slice(0, 5).map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                    {importErrors.length > 5 && <li>...and {importErrors.length - 5} more rows</li>}
                  </ul>
                </div>
              )}

              {/* Live Preview Table */}
              {(previewAssets.length > 0 || previewCapex.length > 0) && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Parsed Spreadsheet Preview ({previewAssets.length || previewCapex.length} records ready)
                    </h4>
                    <span className="text-xs text-slate-500">
                      Total Gross: <strong className="text-slate-900">{formatCurrency(previewAssets.reduce((s, a) => s + a.costINR, 0) || previewCapex.reduce((s, c) => s + c.amountINR, 0))}</strong>
                    </span>
                  </div>

                  <div className="border border-slate-200 rounded-xl overflow-x-auto max-h-80 bg-white">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 sticky top-0">
                        <tr>
                          <th className="px-3 py-2">ID / Ref</th>
                          <th className="px-3 py-2">Name / Description</th>
                          <th className="px-3 py-2">Category</th>
                          <th className="px-3 py-2">Plant Location</th>
                          <th className="px-3 py-2 text-right">Gross Cost</th>
                          <th className="px-3 py-2">Cap Date</th>
                          <th className="px-3 py-2">Serial No</th>
                          <th className="px-3 py-2">Vendor</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {previewAssets.map((ast, idx) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="px-3 py-2 font-mono font-bold text-blue-600">{ast.id}</td>
                            <td className="px-3 py-2 font-medium text-slate-900 max-w-xs truncate">{ast.name}</td>
                            <td className="px-3 py-2 text-slate-600">{ast.category}</td>
                            <td className="px-3 py-2 text-slate-600">{ast.plant}</td>
                            <td className="px-3 py-2 text-right font-mono font-semibold text-slate-900">{formatCurrency(ast.costINR)}</td>
                            <td className="px-3 py-2 font-mono text-slate-600">{ast.capitalisationDate}</td>
                            <td className="px-3 py-2 font-mono text-slate-500">{ast.serialNumber}</td>
                            <td className="px-3 py-2 text-slate-600 max-w-[120px] truncate">{ast.vendor}</td>
                          </tr>
                        ))}

                        {previewCapex.map((cpx, idx) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="px-3 py-2 font-mono font-bold text-purple-600">{cpx.poNumber}</td>
                            <td className="px-3 py-2 font-medium text-slate-900 max-w-xs truncate">{cpx.description}</td>
                            <td className="px-3 py-2 text-slate-600">{cpx.suggestedCategory}</td>
                            <td className="px-3 py-2 text-slate-600">{cpx.plant}</td>
                            <td className="px-3 py-2 text-right font-mono font-semibold text-slate-900">{formatCurrency(cpx.amountINR)}</td>
                            <td className="px-3 py-2 font-mono text-slate-600">{cpx.invoiceDate}</td>
                            <td className="px-3 py-2 font-mono text-slate-500">{cpx.invoiceNumber}</td>
                            <td className="px-3 py-2 text-slate-600 max-w-[120px] truncate">{cpx.vendor}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 2: PDF & DOCUMENT AI EXTRACTOR */}
          {/* ========================================================================= */}
          {activeStudioTab === 'pdf-ai' && (
            <div className="space-y-6">
              <div className="bg-purple-50/50 p-4 rounded-xl border border-purple-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-purple-600 text-white shrink-0">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-purple-950">AI Document & Vendor Invoice Vision Parser</h3>
                    <p className="text-xs text-purple-800 mt-0.5">
                      Upload Vendor Tax Invoices, Purchase Orders, or Asset Capitalisation PDFs for automated Ind AS 16 component extraction.
                    </p>
                  </div>
                </div>
              </div>

              {/* Document Input Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Upload or Paste */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                      Upload Document File (PDF / Image)
                    </label>
                    <div
                      onClick={() => docFileInputRef.current?.click()}
                      className="border-2 border-dashed border-purple-200 hover:border-purple-500 bg-purple-50/30 hover:bg-purple-50/60 rounded-xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center space-y-2"
                    >
                      <input
                        ref={docFileInputRef}
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg,.txt"
                        onChange={handleDocFileUpload}
                        className="hidden"
                      />
                      <FileText className="w-8 h-8 text-purple-600" />
                      <p className="text-xs font-bold text-slate-800">
                        {docFile ? docFile.name : 'Choose PDF Tax Invoice, PO or Scan Document'}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        Supported: PDF, PNG, JPG, scanned procurement invoices
                      </p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                      Or Paste Document Text / OCR Content
                    </label>
                    <textarea
                      rows={6}
                      value={docRawText}
                      onChange={(e) => setDocRawText(e.target.value)}
                      placeholder="Paste invoice line items, purchase order text, or vendor bill particulars here..."
                      className="w-full p-3 text-xs font-mono border border-slate-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none"
                    />
                  </div>

                  <div className="flex items-center justify-between flex-wrap gap-2 text-xs">
                    <span className="text-slate-500">Sample Invoices for Testing:</span>
                    <div className="flex items-center space-x-2">
                      <button
                        type="button"
                        onClick={() => loadSampleDocText('dmg')}
                        className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md font-semibold text-[11px]"
                      >
                        ₹68.5L DMG CNC Invoice
                      </button>
                      <button
                        type="button"
                        onClick={() => loadSampleDocText('siemens')}
                        className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md font-semibold text-[11px]"
                      >
                        ₹24.5L Siemens Drive
                      </button>
                      <button
                        type="button"
                        onClick={() => loadSampleDocText('hvac')}
                        className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md font-semibold text-[11px]"
                      >
                        ₹32.0L Chiller PO
                      </button>
                    </div>
                  </div>

                  <button
                    onClick={handleParseDocumentWithAi}
                    disabled={isAiParsing || (!docBase64 && !docRawText.trim())}
                    className="w-full py-2.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-xs font-bold shadow-xs flex items-center justify-center space-x-2 transition-all"
                  >
                    {isAiParsing ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>AI Document Vision Ingesting & Analysing...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        <span>Execute AI Document Extraction</span>
                      </>
                    )}
                  </button>

                  {aiErrorMsg && (
                    <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl">
                      {aiErrorMsg}
                    </div>
                  )}
                </div>

                {/* Right Extracted Results Card */}
                <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200 flex flex-col justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">
                      Structured Extraction Results
                    </h4>

                    {!parsedDocResult && !isAiParsing && (
                      <div className="py-16 text-center text-slate-400 space-y-2">
                        <FileCheck className="w-12 h-12 mx-auto text-slate-300" />
                        <p className="text-xs font-medium">No document extracted yet.</p>
                        <p className="text-[11px] text-slate-400">
                          Upload a file or click one of the sample test invoices on the left.
                        </p>
                      </div>
                    )}

                    {isAiParsing && (
                      <div className="py-16 text-center space-y-3">
                        <RefreshCw className="w-10 h-10 animate-spin text-purple-600 mx-auto" />
                        <p className="text-xs font-bold text-slate-700">AI Agent Extracting Accounting Particulars...</p>
                        <p className="text-[11px] text-slate-400">Parsing vendor, line items, GST ITC eligibility, and Ind AS 16 component lives.</p>
                      </div>
                    )}

                    {parsedDocResult && (
                      <div className="space-y-4">
                        <div className="bg-white p-3.5 rounded-xl border border-slate-200 space-y-2 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-900">{parsedDocResult.documentType}</span>
                            <span className="font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-bold">
                              {parsedDocResult.documentReference || parsedDocResult.invoiceNumber}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                            <div>
                              <span className="text-slate-400">Vendor:</span>
                              <p className="font-semibold text-slate-800 truncate">{parsedDocResult.vendorName}</p>
                            </div>
                            <div>
                              <span className="text-slate-400">Doc Date:</span>
                              <p className="font-semibold text-slate-800">{parsedDocResult.documentDate}</p>
                            </div>
                            <div>
                              <span className="text-slate-400">Total Gross:</span>
                              <p className="font-bold text-blue-600 text-sm">
                                {formatCurrency(parsedDocResult.totalGrossAmountINR || 0)}
                              </p>
                            </div>
                            <div>
                              <span className="text-slate-400">GST (18%):</span>
                              <p className="font-semibold text-slate-700">
                                {formatCurrency(parsedDocResult.gstAmountINR || 0)}
                              </p>
                            </div>
                          </div>

                          {parsedDocResult.summaryNote && (
                            <p className="text-[11px] text-slate-600 bg-slate-50 p-2 rounded-lg border border-slate-100">
                              {parsedDocResult.summaryNote}
                            </p>
                          )}
                        </div>

                        {/* Extracted Asset Component Breakdown */}
                        {parsedDocResult.extractedAssets && parsedDocResult.extractedAssets.length > 0 && (
                          <div className="space-y-2">
                            <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                              Extracted Asset ({parsedDocResult.extractedAssets.length})
                            </span>
                            {parsedDocResult.extractedAssets.map((ea, idx) => (
                              <div key={idx} className="bg-white p-3 rounded-xl border border-slate-200 space-y-2 text-xs">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-slate-900">{ea.name}</span>
                                  <span className="font-semibold text-slate-600">{ea.category}</span>
                                </div>
                                <div className="flex items-center space-x-4 text-[11px] text-slate-500">
                                  <span>Plant: <strong className="text-slate-700">{ea.plant}</strong></span>
                                  <span>Useful Life: <strong className="text-slate-700">{ea.usefulLifeYears} Yrs</strong></span>
                                </div>
                                {ea.components && ea.components.length > 0 && (
                                  <div className="pt-1 border-t border-slate-100 space-y-1">
                                    <span className="text-[10px] font-bold text-purple-700 uppercase">Ind AS 16 Components:</span>
                                    {ea.components.map((cmp: any, cidx: number) => (
                                      <div key={cidx} className="flex items-center justify-between text-[11px] text-slate-600 pl-2">
                                        <span>• {cmp.name} ({cmp.usefulLifeYears} yrs)</span>
                                        <span className="font-mono">{formatCurrency(cmp.costINR)}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Actions to Commit */}
                  {parsedDocResult && (
                    <div className="pt-4 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <button
                        onClick={handleCommitParsedAssetToRegister}
                        className="py-2 px-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 shadow-xs"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Capitalise to Subledger</span>
                      </button>

                      <button
                        onClick={handleCommitParsedCapexToQueue}
                        className="py-2 px-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 shadow-xs"
                      >
                        <ArrowRight className="w-3.5 h-3.5" />
                        <span>Push to Capex Review</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 3: MANUAL ASSET ENTRY */}
          {/* ========================================================================= */}
          {activeStudioTab === 'manual' && (
            <form onSubmit={handleManualSubmit} className="space-y-6">
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Direct Asset Registration & Component Splitter</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Enter individual equipment, machine, vehicle or IT assets with full technical and statutory metadata.
                  </p>
                </div>
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">
                  Entity: {activeCompany.shortCode}
                </span>
              </div>

              {/* Section 1: Basic Particulars */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Asset Name / Title <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={manualName}
                    onChange={(e) => setManualName(e.target.value)}
                    placeholder="e.g. Automated Robotic MIG Welding Station Unit 3"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Asset Category <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={manualCategory}
                    onChange={(e) => setManualCategory(e.target.value as AssetCategory)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                  >
                    <option value="Plant & Machinery">Plant & Machinery</option>
                    <option value="Buildings & Civil Structures">Buildings & Civil Structures</option>
                    <option value="IT Hardware & Servers">IT Hardware & Servers</option>
                    <option value="Office & Lab Equipment">Office & Lab Equipment</option>
                    <option value="Vehicles">Vehicles</option>
                    <option value="Tooling & Moulds">Tooling & Moulds</option>
                    <option value="Intangibles (Software)">Intangibles (Software)</option>
                  </select>
                </div>
              </div>

              {/* Section 2: Location & Custodian */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-slate-50/60 p-4 rounded-xl border border-slate-200">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Plant Location <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={manualPlant}
                    onChange={(e) => setManualPlant(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                  >
                    {activeCompany.plants.map((p, idx) => (
                      <option key={idx} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Sub-Location / Bay / Room
                  </label>
                  <input
                    type="text"
                    value={manualSubLocation}
                    onChange={(e) => setManualSubLocation(e.target.value)}
                    placeholder="e.g. Bay 2 Line 4"
                    className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Custodian / Lead
                  </label>
                  <input
                    type="text"
                    value={manualCustodian}
                    onChange={(e) => setManualCustodian(e.target.value)}
                    placeholder="e.g. Plant Lead"
                    className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Department
                  </label>
                  <input
                    type="text"
                    value={manualDepartment}
                    onChange={(e) => setManualDepartment(e.target.value)}
                    placeholder="e.g. Precision Robotics"
                    className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                  />
                </div>
              </div>

              {/* Section 3: Financials & Depreciation */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Gross Acquisition Cost (INR) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={manualCost}
                    onChange={(e) => setManualCost(parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 text-xs font-mono font-bold text-slate-900 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                  <p className="text-[10px] text-slate-500 mt-0.5">{formatCurrency(manualCost)}</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Accumulated Depreciation (INR)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={manualAccumDep}
                    onChange={(e) => setManualAccumDep(parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                  <p className="text-[10px] text-slate-500 mt-0.5">NBV: {formatCurrency(Math.max(0, manualCost - manualAccumDep))}</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Capitalisation Date
                  </label>
                  <input
                    type="date"
                    value={manualCapDate}
                    onChange={(e) => setManualCapDate(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Useful Life (Years)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={60}
                    value={manualLife}
                    onChange={(e) => {
                      const val = parseInt(e.target.value) || 15;
                      setManualLife(val);
                      setManualSchIILife(val);
                    }}
                    className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
              </div>

              {/* Section 4: Traceability & Vendor Details */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Serial Number / Tag
                  </label>
                  <input
                    type="text"
                    value={manualSerial}
                    onChange={(e) => setManualSerial(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Vendor / Manufacturer
                  </label>
                  <input
                    type="text"
                    value={manualVendor}
                    onChange={(e) => setManualVendor(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Invoice Number
                  </label>
                  <input
                    type="text"
                    value={manualInvoice}
                    onChange={(e) => setManualInvoice(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    PO Number
                  </label>
                  <input
                    type="text"
                    value={manualPO}
                    onChange={(e) => setManualPO(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
              </div>

              {/* Ind AS 16 Component Split Toggle */}
              <div className="bg-blue-50/50 p-4 rounded-xl border border-blue-200 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    id="enableComponents"
                    checked={enableComponents}
                    onChange={(e) => setEnableComponents(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <label htmlFor="enableComponents" className="text-xs font-bold text-blue-950 cursor-pointer">
                    Enable Ind AS 16 Para 43 Component Split (70% Structural Block @ {manualLife} yrs + 30% Control Unit @ 6 yrs)
                  </label>
                </div>
                <span className="text-[11px] text-blue-700 font-semibold">
                  Auditor Compliance Ready
                </span>
              </div>

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="submit"
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-xs flex items-center space-x-2 transition-all"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Register Asset in {activeCompany.name} Subledger</span>
                </button>
              </div>
            </form>
          )}

          {/* ========================================================================= */}
          {/* TAB 4: ENTITIES & EXPORT HUB */}
          {/* ========================================================================= */}
          {activeStudioTab === 'entities' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Multi-Company Registry & Workspace Management</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Switch between corporate entities, export statutory audit registers, and manage enterprise workspaces.
                  </p>
                </div>
                <button
                  onClick={onOpenCreateCompanyModal}
                  className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center space-x-1.5 shadow-2xs self-start sm:self-auto"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create New Company</span>
                </button>
              </div>

              {/* Company Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {allCompanies.map((comp) => {
                  const isActive = comp.id === activeCompany.id;
                  return (
                    <div
                      key={comp.id}
                      className={`p-5 rounded-2xl border transition-all flex flex-col justify-between space-y-4 ${
                        isActive
                          ? 'border-blue-500 bg-blue-50/30 ring-2 ring-blue-500/20 shadow-xs'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-xs'
                      }`}
                    >
                      <div className="space-y-3">
                        <div className="flex items-start justify-between">
                          <div className={`w-10 h-10 rounded-xl bg-linear-to-br ${comp.logoColor || 'from-blue-600 to-indigo-700'} flex items-center justify-center text-white font-bold text-sm shadow-xs`}>
                            {comp.shortCode}
                          </div>
                          {isActive ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-600 text-white">
                              Active Workspace
                            </span>
                          ) : (
                            <button
                              onClick={() => onSwitchCompany(comp.id)}
                              className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-blue-600 hover:text-white text-slate-700 transition-colors"
                            >
                              Switch to Entity
                            </button>
                          )}
                        </div>

                        <div>
                          <h4 className="text-sm font-bold text-slate-900 leading-tight">{comp.name}</h4>
                          <span className="text-[11px] text-slate-500 font-mono mt-0.5 block">CIN: {comp.cin}</span>
                        </div>

                        <p className="text-xs text-slate-600 line-clamp-2">
                          {comp.description || `${comp.industry} workspace.`}
                        </p>

                        <div className="space-y-1 text-[11px] text-slate-500 pt-2 border-t border-slate-100">
                          <div className="flex justify-between">
                            <span>Industry:</span>
                            <span className="font-semibold text-slate-700 truncate max-w-[150px]">{comp.industry}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Plants:</span>
                            <span className="font-semibold text-slate-700">{comp.plants.length} Locations</span>
                          </div>
                        </div>
                      </div>

                      {/* Footer Actions */}
                      <div className="flex items-center justify-between pt-2">
                        {comp.isCustom ? (
                          <button
                            onClick={() => {
                              if (confirm(`Are you sure you want to delete custom company '${comp.name}'?`)) {
                                onDeleteCompany(comp.id);
                              }
                            }}
                            className="text-slate-400 hover:text-rose-600 text-xs flex items-center space-x-1"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>Delete</span>
                          </button>
                        ) : (
                          <span className="text-[10px] text-slate-400 font-semibold uppercase">System Blueprint</span>
                        )}

                        <button
                          onClick={() => {
                            if (!isActive) onSwitchCompany(comp.id);
                            setActiveStudioTab('spreadsheet');
                          }}
                          className="text-blue-600 hover:text-blue-800 text-xs font-bold flex items-center space-x-1"
                        >
                          <span>Import Data</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Data Export & Backup Utilities */}
              <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200 space-y-3">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Active Entity Export & Data Governance ({activeCompany.name})
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    onClick={() => exportAssetsToCsv(assets, activeCompany.name)}
                    className="p-3 bg-white hover:bg-slate-100 rounded-xl border border-slate-200 text-left flex items-center space-x-3 transition-colors"
                  >
                    <div className="p-2 rounded-lg bg-emerald-100 text-emerald-700">
                      <FileSpreadsheet className="w-5 h-5" />
                    </div>
                    <div>
                      <span className="block text-xs font-bold text-slate-900">Export Asset Register to CSV</span>
                      <span className="block text-[11px] text-slate-500">Download all {assets.length} items formatted for Excel/ERP</span>
                    </div>
                  </button>

                  <button
                    onClick={() =>
                      exportCompanyBackupJson({
                        company: activeCompany,
                        assets,
                        capexQueue,
                        risks: [],
                        scanLogs: []
                      })
                    }
                    className="p-3 bg-white hover:bg-slate-100 rounded-xl border border-slate-200 text-left flex items-center space-x-3 transition-colors"
                  >
                    <div className="p-2 rounded-lg bg-blue-100 text-blue-700">
                      <Database className="w-5 h-5" />
                    </div>
                    <div>
                      <span className="block text-xs font-bold text-slate-900">Export Complete JSON Workspace</span>
                      <span className="block text-[11px] text-slate-500">Full backup including plants, assets & audit logs</span>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
