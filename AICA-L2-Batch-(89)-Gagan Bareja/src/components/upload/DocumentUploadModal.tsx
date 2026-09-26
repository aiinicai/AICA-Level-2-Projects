import React, { useState } from 'react';
import {
  Upload,
  Sparkles,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  Eye,
  FileText,
  Layers,
} from 'lucide-react';
import { Customer, SalesInvoice, StockItem, SystemSettings, Vendor, VendorBill } from '../../types';
import { formatINR } from '../../services/accountingEngine';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: SystemSettings;
  customers: Customer[];
  vendors: Vendor[];
  stockItems: StockItem[];
  onInvoiceExtracted: (invoice: SalesInvoice, autoPosted: boolean) => void;
  onBillExtracted: (bill: VendorBill, autoPosted: boolean) => void;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  settings,
  customers,
  vendors,
  stockItems,
  onInvoiceExtracted,
  onBillExtracted,
}) => {
  const [docType, setDocType] = useState<'SALES_INVOICE' | 'VENDOR_BILL'>('VENDOR_BILL');
  const [fileDataUrl, setFileDataUrl] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [extractionResult, setExtractionResult] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  // Preset Sample Invoices for quick test
  const samplePresets = [
    {
      title: 'ABB Robotics High-Confidence Bill (96%)',
      docType: 'VENDOR_BILL' as const,
      data: {
        documentNumber: 'ABB-MH-2026-904',
        documentDate: '2026-03-12',
        partyName: 'ABB Power & Robotics India Ltd',
        partyGstin: '27AAACA0145P1Z8',
        taxableAmount: 185000,
        cgst: 16650,
        sgst: 16650,
        igst: 0,
        totalAmount: 218300,
        confidenceScore: 96,
        confidenceReasons: ['All line items and GSTINs cross-verified with GSTN database'],
        items: [{ description: 'High-Precision Robotics Controller Servos', quantity: 2, rate: 92500, amount: 185000 }],
      },
    },
    {
      title: 'Low-Confidence Vendor Bill with Blurry Stamp (84%)',
      docType: 'VENDOR_BILL' as const,
      data: {
        documentNumber: 'KIR-BLR-0412',
        documentDate: '2026-03-11',
        partyName: 'Kirloskar Pneumatic & Hydraulics',
        partyGstin: '29AABCK3829L1Z2',
        taxableAmount: 94000,
        cgst: 0,
        sgst: 0,
        igst: 16920,
        totalAmount: 110920,
        confidenceScore: 84,
        confidenceReasons: [
          'Partially smudged HSN digit 8481',
          'Slight discrepancy in round-off fraction between header and line items',
        ],
        items: [{ description: 'High-Pressure Hydraulic Valves', quantity: 4, rate: 23500, amount: 94000 }],
      },
    },
    {
      title: 'Outward Sales Tax Invoice (98%)',
      docType: 'SALES_INVOICE' as const,
      data: {
        documentNumber: 'INV-2026-0988',
        documentDate: '2026-03-14',
        partyName: 'Godrej Precision Heavy Systems Ltd',
        partyGstin: '27AABCG1234F1Z1',
        taxableAmount: 480000,
        cgst: 43200,
        sgst: 43200,
        igst: 0,
        totalAmount: 566400,
        confidenceScore: 98,
        confidenceReasons: ['E-way bill 241098812 verified on NIC e-way bill system'],
        items: [{ description: 'Industrial Controller Units Model A400', quantity: 20, rate: 24000, amount: 480000 }],
      },
    },
  ];

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      setFileDataUrl(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleProcessOCR = async (presetData?: any) => {
    setIsProcessing(true);
    setErrorMessage(null);

    try {
      let result;
      if (presetData) {
        // Simulate real extraction from preset
        await new Promise((r) => setTimeout(r, 900));
        result = presetData;
      } else {
        // Call backend server
        const response = await fetch('/api/ocr/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fileDataUrl,
            documentType: docType,
          }),
        });
        const json = await response.json();
        if (!json.success) {
          throw new Error(json.error || 'Extraction failed');
        }
        result = json.data;
      }

      setExtractionResult(result);
    } catch (err: any) {
      console.error(err);
      setErrorMessage(err.message || 'Failed to process document with OCR engine.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCommitExtraction = () => {
    if (!extractionResult) return;

    const willAutoPost = extractionResult.confidenceScore >= settings.ocrAutoPostThreshold;

    if (docType === 'SALES_INVOICE') {
      const inv: SalesInvoice = {
        id: `INV-${Date.now()}`,
        invoiceNumber: extractionResult.documentNumber || `INV-${Math.floor(1000 + Math.random() * 9000)}`,
        date: extractionResult.documentDate || new Date().toISOString().split('T')[0],
        dueDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        customerId: customers[0].id,
        customerName: extractionResult.partyName || customers[0].name,
        customerGstin: extractionResult.partyGstin || customers[0].gstin,
        branchGstin: settings.activeGstin,
        branchName: 'Pune Central Plant (HQ)',
        items: [
          {
            id: `ITEM-${Date.now()}`,
            skuId: stockItems[0].id,
            skuCode: stockItems[0].sku,
            description: extractionResult.items?.[0]?.description || stockItems[0].name,
            hsnSac: '8479',
            quantity: extractionResult.items?.[0]?.quantity || 1,
            unit: 'NOS',
            rate: extractionResult.taxableAmount,
            amount: extractionResult.taxableAmount,
            gstRate: 18,
            cgst: extractionResult.cgst,
            sgst: extractionResult.sgst,
            igst: extractionResult.igst,
            costPrice: Math.round(extractionResult.taxableAmount * 0.65),
          },
        ],
        taxableAmount: extractionResult.taxableAmount,
        cgst: extractionResult.cgst,
        sgst: extractionResult.sgst,
        igst: extractionResult.igst,
        totalAmount: extractionResult.totalAmount,
        totalCogs: Math.round(extractionResult.taxableAmount * 0.65),
        status: willAutoPost ? 'UNPAID' : 'REVIEW_QUEUE',
        paymentReceived: 0,
        confidenceScore: extractionResult.confidenceScore,
        confidenceReasons: extractionResult.confidenceReasons,
        documentUrl: fileDataUrl || undefined,
        isDisputed: false,
        isConsideredDoubtful: false,
      };

      onInvoiceExtracted(inv, willAutoPost);
    } else {
      const bill: VendorBill = {
        id: `BILL-${Date.now()}`,
        billNumber: extractionResult.documentNumber || `VB-${Math.floor(1000 + Math.random() * 9000)}`,
        date: extractionResult.documentDate || new Date().toISOString().split('T')[0],
        dueDate: new Date(Date.now() + 45 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        vendorId: vendors[0].id,
        vendorName: extractionResult.partyName || vendors[0].name,
        vendorGstin: extractionResult.partyGstin || vendors[0].gstin,
        branchGstin: settings.activeGstin,
        category: 'INVENTORY_PURCHASE',
        items: [
          {
            id: `BI-${Date.now()}`,
            description: extractionResult.items?.[0]?.description || 'Industrial Equipment / Components',
            hsnSac: '8479',
            quantity: 1,
            rate: extractionResult.taxableAmount,
            amount: extractionResult.taxableAmount,
            gstRate: 18,
            cgst: extractionResult.cgst,
            sgst: extractionResult.sgst,
            igst: extractionResult.igst,
            isItcEligible: true,
          },
        ],
        taxableAmount: extractionResult.taxableAmount,
        cgst: extractionResult.cgst,
        sgst: extractionResult.sgst,
        igst: extractionResult.igst,
        totalAmount: extractionResult.totalAmount,
        tdsDeducted: 0,
        netPayable: extractionResult.totalAmount,
        status: willAutoPost ? 'UNPAID' : 'REVIEW_QUEUE',
        paymentMade: 0,
        confidenceScore: extractionResult.confidenceScore,
        confidenceReasons: extractionResult.confidenceReasons,
        isMsme: true,
        msmeType: 'MEDIUM',
        isDisputed: false,
        documentUrl: fileDataUrl || undefined,
      };

      onBillExtracted(bill, willAutoPost);
    }

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 text-xs font-mono">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 font-sans shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-base">Gemini 3.8 Flash Document OCR Engine</h3>
              <p className="text-xs text-slate-400">
                Automated document extraction, confidence scoring, and rule-based journal entry routing.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 cursor-pointer text-sm">
            ✕
          </button>
        </div>

        <div className="overflow-y-auto flex-1 space-y-4 pr-1">
          {/* Document Type Selection */}
          <div className="flex items-center gap-3">
            <label className="text-slate-300 font-sans font-semibold">Document Type:</label>
            <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800">
              <button
                type="button"
                onClick={() => setDocType('VENDOR_BILL')}
                className={`px-3 py-1 rounded-md font-sans transition-colors cursor-pointer ${
                  docType === 'VENDOR_BILL' ? 'bg-indigo-600 text-white' : 'text-slate-400'
                }`}
              >
                Purchase Vendor Bill / Expense
              </button>
              <button
                type="button"
                onClick={() => setDocType('SALES_INVOICE')}
                className={`px-3 py-1 rounded-md font-sans transition-colors cursor-pointer ${
                  docType === 'SALES_INVOICE' ? 'bg-indigo-600 text-white' : 'text-slate-400'
                }`}
              >
                Sales Tax Invoice (Outward)
              </button>
            </div>
          </div>

          {/* Quick Presets for Demo */}
          <div className="space-y-1.5 font-sans">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Quick Test Invoices:
            </div>
            <div className="grid grid-cols-1 gap-2">
              {samplePresets.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setDocType(preset.docType);
                    handleProcessOCR(preset.data);
                  }}
                  className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-indigo-500/50 flex items-center justify-between text-left transition-all cursor-pointer group"
                >
                  <div>
                    <div className="font-medium text-slate-200 text-xs group-hover:text-indigo-300">
                      {preset.title}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                      {preset.data.partyName} • Amount: {formatINR(preset.data.totalAmount)}
                    </div>
                  </div>
                  <span className="text-[11px] text-indigo-400 font-semibold flex items-center gap-1">
                    Process <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Or File Upload Box */}
          <div className="border-2 border-dashed border-slate-700 hover:border-indigo-500/50 rounded-xl p-6 text-center bg-slate-950/40 transition-colors">
            <input
              type="file"
              id="invoice-file-input"
              accept="image/*,application/pdf"
              onChange={handleFileUpload}
              className="hidden"
            />
            <label htmlFor="invoice-file-input" className="cursor-pointer block space-y-2">
              <Upload className="w-8 h-8 text-indigo-400 mx-auto" />
              <div className="font-sans font-semibold text-slate-200">
                {fileDataUrl ? 'File selected (Click to change)' : 'Upload Invoice / Bill (Photo or PDF)'}
              </div>
              <p className="text-[11px] text-slate-400 font-sans">Supports JPG, PNG, PDF formats</p>
            </label>

            {fileDataUrl && !isProcessing && (
              <button
                type="button"
                onClick={() => handleProcessOCR()}
                className="mt-3 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-sans font-semibold cursor-pointer shadow-md"
              >
                Execute Gemini 3.8 Flash OCR
              </button>
            )}
          </div>

          {/* Processing Spinner */}
          {isProcessing && (
            <div className="p-6 bg-slate-950 rounded-xl border border-slate-800 text-center space-y-3">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
              <div className="font-sans font-semibold text-slate-200">Processing Document with Gemini 3.8 Flash...</div>
              <p className="text-[11px] text-slate-400 font-sans">
                Extracting legal entities, HSN codes, GST rates, and verifying arithmetic balances.
              </p>
            </div>
          )}

          {/* Extraction Result Showcase */}
          {extractionResult && (
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <span className="font-sans font-bold text-slate-100 text-sm">Extraction Summary</span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      extractionResult.confidenceScore >= settings.ocrAutoPostThreshold
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}
                  >
                    AI Confidence: {extractionResult.confidenceScore}%
                  </span>
                </div>
                <span className="text-[11px] text-slate-400 font-sans">
                  Threshold: {settings.ocrAutoPostThreshold}%
                </span>
              </div>

              {/* Confidence Routing Decision */}
              {extractionResult.confidenceScore >= settings.ocrAutoPostThreshold ? (
                <div className="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-500/30 flex items-center gap-2 text-emerald-300 font-sans text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>
                    Confidence exceeds threshold ({settings.ocrAutoPostThreshold}%). System will <strong>Auto-Post</strong> directly to General Ledger & Stock!
                  </span>
                </div>
              ) : (
                <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-500/30 space-y-1 font-sans text-xs">
                  <div className="flex items-center gap-2 text-amber-300 font-semibold">
                    <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                    <span>Suspended from Auto-Posting: Routes to Review Queue</span>
                  </div>
                  {extractionResult.confidenceReasons && (
                    <ul className="list-disc list-inside text-[11px] text-slate-300 pl-6">
                      {extractionResult.confidenceReasons.map((r: string, idx: number) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Extracted Fields */}
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="bg-slate-900 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block font-sans">Party Name:</span>
                  <span className="text-slate-100 font-sans font-medium">{extractionResult.partyName}</span>
                </div>
                <div className="bg-slate-900 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block font-sans">Party GSTIN:</span>
                  <span className="text-slate-200 font-bold">{extractionResult.partyGstin}</span>
                </div>
                <div className="bg-slate-900 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block font-sans">Document #:</span>
                  <span className="text-slate-100">{extractionResult.documentNumber}</span>
                </div>
                <div className="bg-slate-900 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block font-sans">Gross Total:</span>
                  <span className="text-indigo-300 font-bold">{formatINR(extractionResult.totalAmount)}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="pt-3 border-t border-slate-800 flex items-center justify-between shrink-0 font-sans">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 cursor-pointer"
          >
            Cancel
          </button>

          {extractionResult && (
            <button
              type="button"
              onClick={handleCommitExtraction}
              className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center gap-2 cursor-pointer shadow-lg shadow-emerald-950/60"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>
                {extractionResult.confidenceScore >= settings.ocrAutoPostThreshold
                  ? 'Commit & Auto-Post to Ledger'
                  : 'Submit to Accountant Review Queue'}
              </span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
