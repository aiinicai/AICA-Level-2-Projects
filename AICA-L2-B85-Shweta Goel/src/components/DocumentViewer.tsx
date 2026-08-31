import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  ZoomIn, 
  ZoomOut, 
  RotateCw, 
  Maximize2, 
  FileText, 
  FileCheck, 
  Sparkles, 
  Eye, 
  RefreshCw,
  Layers,
  HelpCircle,
  FileSpreadsheet
} from 'lucide-react';
import { UploadedDocument, AuditModule } from '../types';
import { SAMPLE_DOCUMENTS, SampleDocumentItem } from '../utils/sampleData';

interface DocumentViewerProps {
  currentDoc: UploadedDocument | null;
  activeModule: AuditModule;
  onFileUpload: (file: File) => void;
  onSelectSample: (sample: SampleDocumentItem) => void;
  onAnalyzeDocument: () => void;
  isAnalyzing: boolean;
  sampleItem?: SampleDocumentItem;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  currentDoc,
  activeModule,
  onFileUpload,
  onSelectSample,
  onAnalyzeDocument,
  isAnalyzing,
  sampleItem,
}) => {
  const [zoom, setZoom] = useState<number>(100);
  const [rotation, setRotation] = useState<number>(0);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files[0]);
    }
  };

  // Filter samples matching the active module
  const relevantSamples = SAMPLE_DOCUMENTS.filter(s => s.module === activeModule);
  const otherSamples = SAMPLE_DOCUMENTS.filter(s => s.module !== activeModule);

  return (
    <div className="flex flex-col h-full bg-slate-200/90 rounded-xl border border-slate-300 overflow-hidden relative shadow-inner">
      
      {/* Top Controls Toolbar */}
      <div className="p-3 border-b border-slate-300 bg-white/90 backdrop-blur flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-200 shrink-0">
            <FileText className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-bold text-slate-800 truncate">
              {currentDoc?.name || 'Document Inspection Preview'}
            </h3>
            <p className="text-[10px] text-slate-500 font-medium">
              {currentDoc ? `${(currentDoc.size / 1024).toFixed(1)} KB • ${currentDoc.mimeType}` : 'Interactive Document Viewer'}
            </p>
          </div>
        </div>

        {/* Zoom & Rotate Controls */}
        <div className="flex items-center gap-1 shrink-0 bg-slate-100 p-1 rounded-lg border border-slate-200 shadow-2xs">
          <button
            onClick={() => setZoom(prev => Math.max(50, prev - 15))}
            title="Zoom Out"
            className="p-1 text-slate-500 hover:text-slate-800 rounded hover:bg-white transition-colors"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-[11px] font-mono text-slate-700 px-1 font-bold min-w-[38px] text-center">
            {zoom}%
          </span>
          <button
            onClick={() => setZoom(prev => Math.min(200, prev + 15))}
            title="Zoom In"
            className="p-1 text-slate-500 hover:text-slate-800 rounded hover:bg-white transition-colors"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <div className="w-[1px] h-3.5 bg-slate-300 mx-0.5" />
          <button
            onClick={() => setRotation(prev => (prev + 90) % 360)}
            title="Rotate 90°"
            className="p-1 text-slate-500 hover:text-slate-800 rounded hover:bg-white transition-colors"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => { setZoom(100); setRotation(0); }}
            title="Reset View"
            className="p-1 text-slate-500 hover:text-slate-800 rounded hover:bg-white transition-colors text-[10px] font-bold"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Pre-loaded Sample Selector Dropdown Bar */}
      <div className="px-3 py-2 bg-slate-100 border-b border-slate-200 flex items-center justify-between gap-2 overflow-x-auto text-xs shrink-0">
        <div className="flex items-center gap-1.5 text-slate-600 text-[11px] whitespace-nowrap">
          <Layers className="w-3.5 h-3.5 text-indigo-600" />
          <span className="font-bold text-slate-700">Test Cases:</span>
        </div>
        
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          {relevantSamples.map(sample => (
            <button
              key={sample.id}
              onClick={() => onSelectSample(sample)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold whitespace-nowrap transition-all border ${
                currentDoc?.id === sample.id
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                  : 'bg-white text-slate-700 hover:bg-slate-50 hover:text-slate-900 border-slate-200'
              }`}
            >
              {sample.name.split(' (')[0]}
            </button>
          ))}
          {otherSamples.slice(0, 2).map(sample => (
            <button
              key={sample.id}
              onClick={() => onSelectSample(sample)}
              className="px-2 py-1 rounded text-[10px] text-slate-500 hover:text-slate-800 bg-white/70 border border-slate-200 hover:border-slate-300 whitespace-nowrap"
            >
              {sample.tag}
            </button>
          ))}
        </div>
      </div>

      {/* Main Document Display Area / Upload Zone */}
      <div className="flex-1 relative overflow-auto p-4 flex items-center justify-center bg-slate-200/50 min-h-[380px]">
        {/* Floating Document Pill */}
        {currentDoc && (
          <div className="absolute top-4 right-4 bg-white/90 backdrop-blur px-3 py-1 rounded border border-slate-300 text-[10px] font-bold text-slate-600 shadow-xs z-10">
            PREVIEW: {currentDoc.name.toUpperCase()}
          </div>
        )}

        {currentDoc ? (
          <div 
            className="transition-transform duration-200 flex items-center justify-center w-full"
            style={{ 
              transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
              transformOrigin: 'center center'
            }}
          >
            {/* If it's a realistic custom rendered financial document scan */}
            {currentDoc.isSample ? (
              <RenderSampleDocumentDoc sampleId={currentDoc.id} />
            ) : currentDoc.mimeType.startsWith('image/') ? (
              <img 
                src={currentDoc.dataUrl} 
                alt="Document Scan" 
                className="max-h-[620px] max-w-full object-contain rounded-lg shadow-xl border border-slate-300 bg-white"
              />
            ) : (
              /* PDF or other format preview */
              <div className="w-full max-w-lg p-6 bg-white rounded-xl border border-slate-200 text-center shadow-lg">
                <FileText className="w-16 h-16 text-indigo-600 mx-auto mb-3" />
                <h4 className="text-sm font-bold text-slate-800 mb-1">{currentDoc.name}</h4>
                <p className="text-xs text-slate-500 mb-4">PDF Document ready for Gemini Vision analysis</p>
                <div className="text-[11px] font-mono font-bold text-emerald-700 bg-emerald-50 p-2.5 rounded border border-emerald-200">
                  Ready for AI Multimodal Extraction
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Empty State / Upload Drop Zone */
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`w-full h-full max-h-[420px] flex flex-col items-center justify-center p-8 rounded-xl border-2 border-dashed transition-all cursor-pointer text-center ${
              isDragOver 
                ? 'border-indigo-500 bg-indigo-50/50' 
                : 'border-slate-300 bg-white/80 hover:border-indigo-400 hover:bg-white shadow-xs'
            }`}
          >
            <input 
              ref={fileInputRef}
              type="file" 
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              onChange={handleFileChange}
              className="hidden" 
            />

            <div className="w-14 h-14 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center mb-3 shadow-xs">
              <UploadCloud className="w-7 h-7" />
            </div>

            <h4 className="text-sm font-bold text-slate-800 mb-1">
              Upload Financial Document
            </h4>
            <p className="text-xs text-slate-500 max-w-sm mb-4">
              Drag &amp; drop or click to upload Vendor Invoices, GSTR-2B scans, Bank Statements, or TDS bills (PDF, PNG, JPG).
            </p>

            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                PDF
              </span>
              <span className="px-2.5 py-1 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                PNG / JPG
              </span>
              <span className="px-2.5 py-1 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                Up to 25MB
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Action Footer */}
      <div className="p-3 border-t border-slate-300 bg-white flex items-center justify-between gap-3 shrink-0">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-bold flex items-center gap-1.5 transition-colors shadow-2xs"
        >
          <UploadCloud className="w-3.5 h-3.5 text-indigo-600" />
          <span>Upload Another</span>
        </button>

        <input 
          ref={fileInputRef}
          type="file" 
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          onChange={handleFileChange}
          className="hidden" 
        />

        {currentDoc && (
          <button
            id="btn-run-ai-audit"
            onClick={onAnalyzeDocument}
            disabled={isAnalyzing}
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-indigo-100 transition-all disabled:opacity-50 cursor-pointer"
          >
            <Sparkles className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
            <span>{isAnalyzing ? 'Auditing with Gemini AI...' : 'Run AI Vision Audit'}</span>
          </button>
        )}
      </div>

    </div>
  );
};

/**
 * Render visual document templates for realistic Indian CA audit cases
 */
function RenderSampleDocumentDoc({ sampleId }: { sampleId: string }) {
  if (sampleId === 'sample-inv-math-error') {
    return (
      <div className="w-full max-w-[500px] bg-amber-50 text-slate-900 p-6 rounded-lg shadow-2xl font-sans text-[11px] border border-amber-300">
        {/* Header */}
        <div className="border-b-2 border-slate-800 pb-3 mb-3">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[9px] font-bold uppercase tracking-wider bg-slate-800 text-white px-1.5 py-0.5 rounded">TAX INVOICE</span>
              <h2 className="text-sm font-extrabold text-slate-900 mt-1">BHARAT HARDWARE & SUPPLIES PVT LTD</h2>
              <p className="text-[10px] text-slate-600">Plot 45, MIDC Industrial Area, Pune, MH 411018</p>
              <p className="text-[10px] font-mono font-bold text-slate-800">GSTIN: 27AABCB1234F1Z5</p>
            </div>
            <div className="text-right">
              <p className="font-bold text-slate-800">Invoice No: BHE/24-25/0892</p>
              <p className="text-slate-600">Date: 14-Nov-2024</p>
              <p className="text-slate-600">PoS: Maharashtra (27)</p>
            </div>
          </div>
        </div>

        {/* Bill To */}
        <div className="bg-white/80 p-2.5 rounded border border-slate-300 mb-3">
          <span className="text-[9px] font-bold text-slate-500 uppercase">Billed To (Recipient):</span>
          <p className="font-bold text-slate-900">Apex Precision Engineering Ltd</p>
          <p className="text-slate-600">G-12, Andheri East, Mumbai 400069</p>
          <p className="font-mono text-slate-700">GSTIN: 27AAECP9876K1Z2</p>
        </div>

        {/* Items Table */}
        <table className="w-full text-left border-collapse mb-3">
          <thead>
            <tr className="bg-slate-800 text-white text-[10px]">
              <th className="p-1.5">Description</th>
              <th className="p-1.5">HSN</th>
              <th className="p-1.5 text-right">Qty</th>
              <th className="p-1.5 text-right">Rate</th>
              <th className="p-1.5 text-right">Amount (₹)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            <tr>
              <td className="p-1.5 font-medium">SS Fasteners Gr 316</td>
              <td className="p-1.5 font-mono">7318</td>
              <td className="p-1.5 text-right">500 Kg</td>
              <td className="p-1.5 text-right">220</td>
              <td className="p-1.5 text-right font-mono font-semibold">1,10,000</td>
            </tr>
            <tr>
              <td className="p-1.5 font-medium">Pneumatic Actuators</td>
              <td className="p-1.5 font-mono">8412</td>
              <td className="p-1.5 text-right">15 Nos</td>
              <td className="p-1.5 text-right">5,000</td>
              <td className="p-1.5 text-right font-mono font-semibold">75,000</td>
            </tr>
          </tbody>
        </table>

        {/* Calculation Table with Visual Highlight */}
        <div className="flex justify-end">
          <div className="w-64 bg-white p-2.5 rounded border border-slate-300 space-y-1">
            <div className="flex justify-between text-slate-600">
              <span>Taxable Value:</span>
              <span className="font-mono">₹1,85,000.00</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>CGST @ 9%:</span>
              <span className="font-mono">₹16,650.00</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>SGST @ 9%:</span>
              <span className="font-mono">₹16,650.00</span>
            </div>
            <div className="flex justify-between font-bold border-t border-slate-300 pt-1 text-slate-800">
              <span>Actual Calculated Sum:</span>
              <span className="font-mono text-emerald-700">₹2,18,300.00</span>
            </div>
            <div className="flex justify-between font-extrabold border-t-2 border-rose-500 pt-1 text-rose-700 bg-rose-50 p-1 rounded">
              <span>Stated Invoice Total:</span>
              <span className="font-mono">₹2,24,500.00</span>
            </div>
          </div>
        </div>

        <div className="mt-3 p-2 bg-rose-100/80 border border-rose-300 rounded text-[10px] text-rose-900 font-semibold flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-rose-600 animate-pulse" />
          <span>CA Audit Flag: Math mismatch of ₹6,200 between stated total and line item sum.</span>
        </div>
      </div>
    );
  }

  if (sampleId === 'sample-gst-pos-error') {
    return (
      <div className="w-full max-w-[500px] bg-slate-50 text-slate-900 p-6 rounded-lg shadow-2xl font-sans text-[11px] border border-slate-300">
        <div className="border-b border-slate-800 pb-2 mb-3 flex justify-between">
          <div>
            <span className="text-[9px] font-bold bg-indigo-700 text-white px-1.5 py-0.5 rounded">TAX INVOICE</span>
            <h3 className="font-bold text-sm text-slate-900 mt-1">MAHINDRA LOGISTICS TECH HUB</h3>
            <p className="text-[10px] font-mono">Supplier GSTIN: <strong className="text-indigo-800">27AAACM5432E1Z7</strong> (Maharashtra)</p>
          </div>
          <div className="text-right">
            <p className="font-bold">INV: MLT/2024/9021</p>
            <p className="text-[10px]">Date: 22-Oct-2024</p>
          </div>
        </div>

        <div className="bg-indigo-50/70 p-2.5 rounded border border-indigo-200 mb-3">
          <p className="text-[10px] text-slate-600">Recipient: <strong>Karnataka Warehousing Solutions Ltd</strong></p>
          <p className="text-[10px] font-mono">Recipient GSTIN: <strong className="text-indigo-800">29AAACK7654P1Z3</strong> (Karnataka)</p>
          <p className="text-[10px] font-bold text-rose-700 mt-0.5">Place of Supply (PoS): Karnataka (State Code 29)</p>
        </div>

        <table className="w-full text-left border-collapse mb-3 bg-white">
          <thead>
            <tr className="bg-slate-800 text-white text-[10px]">
              <th className="p-1.5">Service Description</th>
              <th className="p-1.5">SAC</th>
              <th className="p-1.5 text-right">Taxable</th>
              <th className="p-1.5 text-right">CGST 9%</th>
              <th className="p-1.5 text-right">SGST 9%</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="p-1.5">Interstate Warehouse Freight</td>
              <td className="p-1.5 font-mono">9965</td>
              <td className="p-1.5 text-right font-mono">₹4,20,000</td>
              <td className="p-1.5 text-right font-mono text-rose-700 font-bold">₹37,800</td>
              <td className="p-1.5 text-right font-mono text-rose-700 font-bold">₹37,800</td>
            </tr>
          </tbody>
        </table>

        <div className="p-2.5 bg-rose-100 border border-rose-300 rounded text-rose-900 text-[10px] space-y-1">
          <p className="font-bold">⚠️ PoS Rule Violation: Inter-State Supply (MH 27 ➔ KA 29)</p>
          <p>Charged CGST+SGST instead of mandatory <strong>IGST ₹75,600</strong> under IGST Act Section 7.</p>
        </div>
      </div>
    );
  }

  if (sampleId === 'sample-gst-blocked-17-5') {
    return (
      <div className="w-full max-w-[500px] bg-slate-50 text-slate-900 p-6 rounded-lg shadow-2xl font-sans text-[11px] border border-slate-300">
        <div className="border-b border-slate-800 pb-2 mb-3 flex justify-between">
          <div>
            <span className="text-[9px] font-bold bg-purple-700 text-white px-1.5 py-0.5 rounded">TAX INVOICE (FLEET & CATERING)</span>
            <h3 className="font-bold text-sm text-slate-900 mt-1">ROYAL AUTO & LUXURY CATERING LLP</h3>
            <p className="text-[10px] font-mono">Supplier GSTIN: <strong className="text-purple-800">27AABCR9876Q1Z4</strong> (Maharashtra)</p>
          </div>
          <div className="text-right">
            <p className="font-bold">INV: RGH/2025/0412</p>
            <p className="text-[10px]">Date: 15-Jan-2025</p>
          </div>
        </div>

        <div className="bg-purple-50/70 p-2.5 rounded border border-purple-200 mb-3">
          <p className="text-[10px] text-slate-600">Recipient: <strong>Apex Precision Engineering Ltd</strong></p>
          <p className="text-[10px] font-mono">Recipient GSTIN: <strong className="text-purple-800">27AAECP9876K1Z2</strong> (Maharashtra)</p>
          <p className="text-[10px] font-bold text-slate-700 mt-0.5">Place of Supply (PoS): Maharashtra (State Code 27)</p>
        </div>

        <table className="w-full text-left border-collapse mb-3 bg-white">
          <thead>
            <tr className="bg-slate-800 text-white text-[10px]">
              <th className="p-1.5">Line Item / Expense</th>
              <th className="p-1.5">HSN/SAC</th>
              <th className="p-1.5 text-right">Taxable</th>
              <th className="p-1.5 text-right">CGST</th>
              <th className="p-1.5 text-right">SGST</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-slate-100">
              <td className="p-1.5 font-medium">5-Seater Passenger Vehicle (28%)</td>
              <td className="p-1.5 font-mono">870323</td>
              <td className="p-1.5 text-right font-mono">₹15,00,000</td>
              <td className="p-1.5 text-right font-mono text-purple-700 font-bold">₹2,10,000 (14%)</td>
              <td className="p-1.5 text-right font-mono text-purple-700 font-bold">₹2,10,000 (14%)</td>
            </tr>
            <tr>
              <td className="p-1.5 font-medium">Outdoor Catering & Beverages (18%)</td>
              <td className="p-1.5 font-mono">996331</td>
              <td className="p-1.5 text-right font-mono">₹50,000</td>
              <td className="p-1.5 text-right font-mono text-purple-700 font-bold">₹4,500 (9%)</td>
              <td className="p-1.5 text-right font-mono text-purple-700 font-bold">₹4,500 (9%)</td>
            </tr>
          </tbody>
        </table>

        <div className="p-2.5 bg-rose-100 border border-rose-300 rounded text-rose-900 text-[10px] space-y-1">
          <p className="font-bold">🚫 SECTION 17(5) BLOCKED CREDIT DETECTED: ₹4,29,000</p>
          <p>• <strong>5-Seater Passenger Vehicle (₹4,20,000 GST)</strong>: Blocked under Sec 17(5)(a) of CGST Act.</p>
          <p>• <strong>Outdoor Catering & Beverages (₹9,000 GST)</strong>: Blocked under Sec 17(5)(b)(i) of CGST Act.</p>
        </div>
      </div>
    );
  }

  if (sampleId === 'sample-bank-statement') {
    return (
      <div className="w-full max-w-[500px] bg-slate-900 text-slate-100 p-5 rounded-lg shadow-2xl font-mono text-[10px] border border-slate-700">
        <div className="border-b border-slate-700 pb-2 mb-2 flex justify-between items-center text-xs">
          <div>
            <h3 className="font-bold text-amber-400">HDFC BANK - CORPORATE CURRENT A/C</h3>
            <p className="text-[10px] text-slate-400">A/C: 50200049281742 • IFSC: HDFC0000240</p>
          </div>
          <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[9px] border border-amber-500/40">
            OCTOBER 2024
          </span>
        </div>

        <div className="space-y-1 bg-slate-950 p-2 rounded border border-slate-800">
          <div className="flex justify-between text-slate-400 text-[9px]">
            <span>07-Oct-24 CASH DEP - COUNTER (SELF)</span>
            <span className="text-rose-400 font-bold">CR: ₹1,80,000.00 [ALERT &gt;₹50k]</span>
          </div>
          <div className="flex justify-between text-slate-400 text-[9px]">
            <span>12-Oct-24 CASH WITHDRAWAL - SELF</span>
            <span className="text-rose-400 font-bold">DR: ₹75,000.00 [ALERT &gt;₹50k]</span>
          </div>
          <div className="flex justify-between text-amber-300 text-[9px] bg-amber-950/40 p-1 rounded">
            <span>15-Oct-24 UPI/428910281 Razorpay</span>
            <span className="font-bold">DR: ₹18,500.00 [DUP 1]</span>
          </div>
          <div className="flex justify-between text-amber-300 text-[9px] bg-amber-950/40 p-1 rounded">
            <span>15-Oct-24 UPI/428910281 Razorpay</span>
            <span className="font-bold">DR: ₹18,500.00 [DUP 2]</span>
          </div>
          <div className="flex justify-between text-slate-400 text-[9px]">
            <span>18-Oct-24 CASH DEP - OUTLET</span>
            <span className="text-rose-400 font-bold">CR: ₹95,000.00 [ALERT &gt;₹50k]</span>
          </div>
        </div>

        <div className="mt-2 text-[9px] text-amber-400 flex items-center gap-1">
          <span>⚡ Flagged: 3 Cash Txns &gt; ₹50,000 (Sec 269ST) + 1 Duplicate Payment</span>
        </div>
      </div>
    );
  }

  if (sampleId === 'sample-tds-short-deduction') {
    return (
      <div className="w-full max-w-[500px] bg-amber-50 text-slate-900 p-5 rounded-lg shadow-2xl font-sans text-[11px] border border-amber-300">
        <div className="border-b border-slate-700 pb-2 mb-2 flex justify-between">
          <div>
            <span className="text-[9px] font-bold bg-amber-700 text-white px-1.5 py-0.5 rounded">FEE MEMORANDUM</span>
            <h3 className="font-bold text-sm text-slate-900 mt-1">ADV. K. R. RAMANATHAN & PARTNERS</h3>
            <p className="text-[10px] text-slate-600">High Court & Supreme Court Legal Consultants</p>
          </div>
          <div className="text-right font-mono text-[10px]">
            <p className="font-bold">REF: LEG/2024/0481</p>
            <p>PAN: AAAFR8921K</p>
          </div>
        </div>

        <div className="bg-white p-2.5 rounded border border-slate-300 mb-2">
          <p className="text-slate-600">Services: <strong>Corporate Legal Advisory & Arbitration</strong></p>
          <p className="text-slate-800 font-mono">Gross Bill Amount: <strong>₹2,50,000.00</strong></p>
        </div>

        <div className="p-2.5 bg-rose-100 border border-rose-300 rounded text-[10px] text-rose-900 space-y-1">
          <div className="flex justify-between">
            <span>Deducted by Client:</span>
            <span className="font-bold font-mono">Sec 194C @ 2% (₹5,000)</span>
          </div>
          <div className="flex justify-between text-emerald-800 font-bold">
            <span>Statutory Legal Requirement:</span>
            <span className="font-mono">Sec 194J(b) @ 10% (₹25,000)</span>
          </div>
          <div className="border-t border-rose-300 pt-1 flex justify-between font-extrabold text-rose-800">
            <span>Short Deduction Amount:</span>
            <span className="font-mono">₹20,000.00 Shortfall</span>
          </div>
        </div>
      </div>
    );
  }

  if (sampleId === 'sample-tds-clean') {
    return (
      <div className="w-full max-w-[500px] bg-slate-900 text-slate-100 p-5 rounded-lg shadow-2xl font-sans text-[11px] border border-emerald-500/40">
        <div className="border-b border-slate-700 pb-2 mb-2 flex justify-between">
          <div>
            <span className="text-[9px] font-bold bg-emerald-600 text-white px-1.5 py-0.5 rounded">FEE INVOICE (CLEAN)</span>
            <h3 className="font-bold text-sm text-emerald-400 mt-1">INFOSYS TECH CONSULTING SERVICES LTD</h3>
            <p className="text-[10px] text-slate-400">Enterprise Cloud & Technical Consulting</p>
          </div>
          <div className="text-right font-mono text-[10px]">
            <p className="font-bold">REF: INF/2024/7712</p>
            <p className="text-slate-400">PAN: AAACI1928K</p>
          </div>
        </div>

        <div className="bg-slate-800 p-2.5 rounded border border-slate-700 mb-2">
          <p className="text-slate-300">Services: <strong>Technical Consulting & Architecture (Sec 194J(a))</strong></p>
          <p className="text-emerald-400 font-mono">Gross Bill Amount: <strong>₹5,00,000.00</strong></p>
        </div>

        <div className="p-2.5 bg-emerald-950/60 border border-emerald-800/60 rounded text-[10px] text-emerald-300 space-y-1">
          <div className="flex justify-between">
            <span>Deducted TDS @ 2% (Sec 194J(a)):</span>
            <span className="font-bold font-mono">₹10,000.00</span>
          </div>
          <div className="flex justify-between text-emerald-400 font-bold">
            <span>Statutory Rate Required:</span>
            <span className="font-mono">2.0% for Technical Services</span>
          </div>
          <div className="border-t border-emerald-800/60 pt-1 flex justify-between font-extrabold text-emerald-300">
            <span>TDS Reconciliation Status:</span>
            <span className="font-mono">✓ 100% MATCHED (₹0 Variance)</span>
          </div>
        </div>
      </div>
    );
  }

  // Default clean invoice
  return (
    <div className="w-full max-w-[500px] bg-slate-900 text-slate-100 p-6 rounded-lg shadow-2xl font-sans text-[11px] border border-emerald-500/30">
      <div className="flex justify-between border-b border-slate-800 pb-3 mb-3">
        <div>
          <span className="text-[9px] font-bold bg-emerald-700 text-white px-2 py-0.5 rounded">TAX INVOICE (CLEAN)</span>
          <h3 className="font-bold text-sm text-emerald-400 mt-1">ZENITH CLOUD & IT LLP</h3>
          <p className="text-[10px] text-slate-400 font-mono">GSTIN: 29AAHFZ4567M1Z8 (Karnataka)</p>
        </div>
        <div className="text-right text-[10px]">
          <p className="font-bold">INV: ZIT/24-25/1102</p>
          <p className="text-slate-400">Total: ₹4,13,000</p>
        </div>
      </div>
      <div className="p-2 bg-emerald-950/40 border border-emerald-800/40 rounded text-emerald-300 text-[10px]">
        ✓ Taxable ₹3,50,000 + 18% IGST ₹63,000 = ₹4,13,000 (100% Math Match)
      </div>
    </div>
  );
}
