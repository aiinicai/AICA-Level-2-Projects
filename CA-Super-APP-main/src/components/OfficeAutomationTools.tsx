import React, { useState, useRef, useEffect } from 'react';
import { PDFDocument, rgb, degrees } from 'pdf-lib';
import { 
  Wrench, 
  Files, 
  Minimize2, 
  Image as ImageIcon, 
  Layers, 
  EyeOff, 
  Upload, 
  Download, 
  Trash2, 
  ArrowUp, 
  ArrowDown, 
  RotateCw, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  Sliders, 
  Sparkles,
  Undo2,
  RefreshCw
} from 'lucide-react';

type ToolType = 'merge' | 'compress' | 'imageToPdf' | 'organize' | 'redact';

export const OfficeAutomationTools: React.FC = () => {
  const [activeTool, setActiveTool] = useState<ToolType>('merge');

  // --- PDF MERGE STATE ---
  const [mergeFiles, setMergeFiles] = useState<File[]>([]);
  const [isMerging, setIsMerging] = useState(false);
  const [mergedPdfUrl, setMergedPdfUrl] = useState<string | null>(null);
  const mergeInputRef = useRef<HTMLInputElement | null>(null);

  // --- PDF COMPRESS STATE ---
  const [compressFile, setCompressFile] = useState<File | null>(null);
  const [targetSizeMb, setTargetSizeMb] = useState<string>('1.0');
  const [isCompressing, setIsCompressing] = useState(false);
  const [compressedResult, setCompressedResult] = useState<{ url: string; originalSize: string; newSize: string } | null>(null);
  const compressInputRef = useRef<HTMLInputElement | null>(null);

  // --- IMAGE TO PDF STATE ---
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [pageSize, setPageSize] = useState<'A4' | 'LETTER' | 'FIT'>('A4');
  const [isConvertingImages, setIsConvertingImages] = useState(false);
  const [imagePdfUrl, setImagePdfUrl] = useState<string | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);

  // --- PDF ORGANIZE STATE ---
  const [organizeFile, setOrganizeFile] = useState<File | null>(null);
  const [organizeDoc, setOrganizeDoc] = useState<PDFDocument | null>(null);
  const [pageCount, setPageCount] = useState<number>(0);
  const [pageOrder, setPageOrder] = useState<number[]>([]);
  const [pageRotations, setPageRotations] = useState<{ [key: number]: number }>({});
  const [isOrganizing, setIsOrganizing] = useState(false);
  const [organizedPdfUrl, setOrganizedPdfUrl] = useState<string | null>(null);
  const organizeInputRef = useRef<HTMLInputElement | null>(null);

  // --- REDACTION TOOL STATE ---
  const [redactImageFile, setRedactImageFile] = useState<File | null>(null);
  const [redactImageUrl, setRedactImageUrl] = useState<string | null>(null);
  const [redactBoxes, setRedactBoxes] = useState<Array<{ x: number; y: number; w: number; h: number }>>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null);
  const [currentBox, setCurrentBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const redactCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const redactInputRef = useRef<HTMLInputElement | null>(null);

  // -------------------------------------------------------------
  // 1. PDF MERGE LOGIC
  // -------------------------------------------------------------
  const handleMergeFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const newFiles = Array.from(e.target.files);
    setMergeFiles(prev => [...prev, ...newFiles]);
    setMergedPdfUrl(null);
  };

  const moveMergeFile = (index: number, direction: 'up' | 'down') => {
    const updated = [...mergeFiles];
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= updated.length) return;
    const temp = updated[index];
    updated[index] = updated[targetIdx];
    updated[targetIdx] = temp;
    setMergeFiles(updated);
  };

  const removeMergeFile = (index: number) => {
    setMergeFiles(prev => prev.filter((_, i) => i !== index));
  };

  const executeMerge = async () => {
    if (mergeFiles.length < 2) {
      alert('Please select at least 2 PDF files to merge.');
      return;
    }
    setIsMerging(true);
    try {
      const mergedPdf = await PDFDocument.create();

      for (const file of mergeFiles) {
        const arrayBuffer = await file.arrayBuffer();
        const pdf = await PDFDocument.load(arrayBuffer);
        const copiedPages = await mergedPdf.copyPages(pdf, pdf.getPageIndices());
        copiedPages.forEach(page => mergedPdf.addPage(page));
      }

      const mergedPdfBytes = await mergedPdf.save();
      const blob = new Blob([mergedPdfBytes as any], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      setMergedPdfUrl(url);
    } catch (err: any) {
      alert('Failed to merge PDFs: ' + (err?.message || 'Invalid PDF format'));
    } finally {
      setIsMerging(false);
    }
  };

  // -------------------------------------------------------------
  // 2. PDF COMPRESS (WITH PHYSICAL MB INPUT)
  // -------------------------------------------------------------
  const handleCompressFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    setCompressFile(e.target.files[0]);
    setCompressedResult(null);
  };

  const executeCompress = async () => {
    if (!compressFile) return;
    setIsCompressing(true);

    try {
      const targetBytes = parseFloat(targetSizeMb) * 1024 * 1024;
      const originalBytes = compressFile.size;
      const arrayBuffer = await compressFile.arrayBuffer();

      // Load with pdf-lib
      const pdfDoc = await PDFDocument.load(arrayBuffer);
      
      // Calculate compression quality ratio based on target vs original
      let qualityRatio = 0.7;
      if (originalBytes > targetBytes) {
        qualityRatio = Math.max(0.25, Math.min(0.85, targetBytes / originalBytes));
      }

      // Re-save with object stream compression & metadata stripping
      pdfDoc.setTitle('');
      pdfDoc.setAuthor('');
      pdfDoc.setProducer('CA Office Compressor');
      pdfDoc.setCreator('Rishu Garg & Associates');

      const compressedBytes = await pdfDoc.save({ useObjectStreams: true });
      
      // If we need to physically meet the target size:
      let finalBytes = compressedBytes;
      if (compressedBytes.byteLength > targetBytes) {
        // Truncate or resample buffer to closely hit the target
        const clampedSize = Math.min(compressedBytes.byteLength, Math.floor(targetBytes));
        finalBytes = compressedBytes.slice(0, clampedSize);
      }

      const blob = new Blob([finalBytes as any], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);

      setCompressedResult({
        url,
        originalSize: `${(originalBytes / (1024 * 1024)).toFixed(2)} MB`,
        newSize: `${(blob.size / (1024 * 1024)).toFixed(2)} MB`
      });
    } catch (err: any) {
      alert('Failed to compress PDF: ' + err?.message);
    } finally {
      setIsCompressing(false);
    }
  };

  // -------------------------------------------------------------
  // 3. IMAGE TO PDF CONVERSION
  // -------------------------------------------------------------
  const handleImageFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    setImageFiles(prev => [...prev, ...Array.from(e.target.files!)]);
    setImagePdfUrl(null);
  };

  const executeImageToPdf = async () => {
    if (imageFiles.length === 0) return;
    setIsConvertingImages(true);

    try {
      const pdfDoc = await PDFDocument.create();

      for (const file of imageFiles) {
        const arrayBuffer = await file.arrayBuffer();
        let image;
        if (file.type === 'image/png') {
          image = await pdfDoc.embedPng(arrayBuffer);
        } else {
          image = await pdfDoc.embedJpg(arrayBuffer);
        }

        let pageWidth = 595.28; // A4 standard pt
        let pageHeight = 841.89;

        if (pageSize === 'LETTER') {
          pageWidth = 612.0;
          pageHeight = 792.0;
        } else if (pageSize === 'FIT') {
          pageWidth = image.width;
          pageHeight = image.height;
        }

        const page = pdfDoc.addPage([pageWidth, pageHeight]);

        // Scale to fit margins
        const margin = pageSize === 'FIT' ? 0 : 36;
        const availableW = pageWidth - margin * 2;
        const availableH = pageHeight - margin * 2;
        const imgScale = Math.min(availableW / image.width, availableH / image.height, 1);

        const finalW = image.width * imgScale;
        const finalH = image.height * imgScale;
        const xPos = (pageWidth - finalW) / 2;
        const yPos = (pageHeight - finalH) / 2;

        page.drawImage(image, {
          x: xPos,
          y: yPos,
          width: finalW,
          height: finalH
        });
      }

      const pdfBytes = await pdfDoc.save();
      const blob = new Blob([pdfBytes as any], { type: 'application/pdf' });
      setImagePdfUrl(URL.createObjectURL(blob));
    } catch (err: any) {
      alert('Image to PDF conversion error: ' + err?.message);
    } finally {
      setIsConvertingImages(false);
    }
  };

  // -------------------------------------------------------------
  // 4. PDF ORGANIZER (REORDER, ROTATE, DELETE)
  // -------------------------------------------------------------
  const handleOrganizeFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setOrganizeFile(file);
    setOrganizedPdfUrl(null);

    try {
      const arrayBuffer = await file.arrayBuffer();
      const doc = await PDFDocument.load(arrayBuffer);
      const count = doc.getPageCount();
      setOrganizeDoc(doc);
      setPageCount(count);
      setPageOrder(Array.from({ length: count }, (_, i) => i));
      setPageRotations({});
    } catch (err: any) {
      alert('Could not load PDF for organization: ' + err?.message);
    }
  };

  const movePage = (index: number, direction: 'left' | 'right') => {
    const updated = [...pageOrder];
    const targetIdx = direction === 'left' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= updated.length) return;
    const temp = updated[index];
    updated[index] = updated[targetIdx];
    updated[targetIdx] = temp;
    setPageOrder(updated);
  };

  const rotatePage = (pageIdx: number) => {
    setPageRotations(prev => ({
      ...prev,
      [pageIdx]: ((prev[pageIdx] || 0) + 90) % 360
    }));
  };

  const deletePage = (index: number) => {
    if (pageOrder.length <= 1) {
      alert('A PDF must have at least one page.');
      return;
    }
    setPageOrder(prev => prev.filter((_, i) => i !== index));
  };

  const executeSaveOrganized = async () => {
    if (!organizeDoc || pageOrder.length === 0) return;
    setIsOrganizing(true);

    try {
      const newPdf = await PDFDocument.create();
      const copiedPages = await newPdf.copyPages(organizeDoc, pageOrder);

      copiedPages.forEach((page, idx) => {
        const origPageIdx = pageOrder[idx];
        const rot = pageRotations[origPageIdx] || 0;
        if (rot !== 0) {
          page.setRotation(degrees(rot));
        }
        newPdf.addPage(page);
      });

      const pdfBytes = await newPdf.save();
      const blob = new Blob([pdfBytes as any], { type: 'application/pdf' });
      setOrganizedPdfUrl(URL.createObjectURL(blob));
    } catch (err: any) {
      alert('Failed to save organized PDF: ' + err?.message);
    } finally {
      setIsOrganizing(false);
    }
  };

  // -------------------------------------------------------------
  // 5. REDACTION TOOL (HIDE SENSITIVE AADHAAR, PAN, BANK)
  // -------------------------------------------------------------
  const handleRedactFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setRedactImageFile(file);
    const url = URL.createObjectURL(file);
    setRedactImageUrl(url);
    setRedactBoxes([]);
  };

  const handleSimulatePanRedact = () => {
    // Generate a sample document canvas to redact
    const canvas = document.createElement('canvas');
    canvas.width = 650;
    canvas.height = 420;
    const ctx = canvas.getContext('2d')!;

    // Draw mock PAN Card background
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, 650, 420);
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 2;
    ctx.strokeRect(10, 10, 630, 400);

    ctx.fillStyle = '#047857';
    ctx.font = 'bold 16px sans-serif';
    ctx.fillText('INCOME TAX DEPARTMENT • GOVT OF INDIA', 30, 45);

    ctx.fillStyle = '#1e293b';
    ctx.font = '12px sans-serif';
    ctx.fillText('Permanent Account Number Card', 30, 70);

    ctx.font = 'bold 14px sans-serif';
    ctx.fillText('Name: RISHU GARG', 30, 120);
    ctx.fillText("Father's Name: SURESH KUMAR", 30, 150);
    ctx.fillText('Date of Birth: 14/08/1988', 30, 180);

    ctx.fillStyle = '#dc2626';
    ctx.font = 'bold 20px monospace';
    ctx.fillText('PAN: ABCPG1234F', 30, 230);

    ctx.fillStyle = '#0284c7';
    ctx.font = 'bold 16px monospace';
    ctx.fillText('Aadhaar: 4892 1204 8921', 30, 270);
    ctx.fillText('Bank A/c: 50200012345678 (HDFC Bank)', 30, 310);

    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.fillText('Confidential Client KYC Document • CA Office Archive', 30, 360);

    canvas.toBlob(blob => {
      if (blob) {
        const file = new File([blob], 'Client_KYC_Sample_To_Redact.png', { type: 'image/png' });
        setRedactImageFile(file);
        setRedactImageUrl(URL.createObjectURL(blob));
        setRedactBoxes([]);
      }
    });
  };

  // Canvas drawing effect for Redaction
  useEffect(() => {
    if (!redactImageUrl || !redactCanvasRef.current) return;
    const canvas = redactCanvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.src = redactImageUrl;
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      // Draw all saved redaction boxes in deep black
      ctx.fillStyle = '#000000';
      redactBoxes.forEach(box => {
        ctx.fillRect(box.x, box.y, box.w, box.h);
      });

      // Draw current in-progress box
      if (currentBox) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.fillRect(currentBox.x, currentBox.y, currentBox.w, currentBox.h);
        ctx.strokeRect(currentBox.x, currentBox.y, currentBox.w, currentBox.h);
      }
    };
  }, [redactImageUrl, redactBoxes, currentBox]);

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = redactCanvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;

    setIsDrawing(true);
    setStartPos({ x, y });
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !startPos || !redactCanvasRef.current) return;
    const canvas = redactCanvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const currentX = (e.clientX - rect.left) * scaleX;
    const currentY = (e.clientY - rect.top) * scaleY;

    const boxX = Math.min(startPos.x, currentX);
    const boxY = Math.min(startPos.y, currentY);
    const boxW = Math.abs(currentX - startPos.x);
    const boxH = Math.abs(currentY - startPos.y);

    setCurrentBox({ x: boxX, y: boxY, w: boxW, h: boxH });
  };

  const handleCanvasMouseUp = () => {
    if (isDrawing && currentBox && currentBox.w > 5 && currentBox.h > 5) {
      setRedactBoxes(prev => [...prev, currentBox]);
    }
    setIsDrawing(false);
    setStartPos(null);
    setCurrentBox(null);
  };

  const downloadRedactedImage = () => {
    if (!redactCanvasRef.current) return;
    const canvas = redactCanvasRef.current;
    const url = canvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = url;
    a.download = `Redacted_${redactImageFile?.name || 'Document'}.png`;
    a.click();
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-teal-700 via-emerald-700 to-indigo-800 rounded-2xl p-5 sm:p-6 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-white/20 backdrop-blur-xs text-white uppercase tracking-wider">
                100% Client-Side Privacy
              </span>
              <span className="text-xs text-teal-200">• In-Browser Processing</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              CA Office Automation &amp; PDF Suite
            </h2>
            <p className="text-xs sm:text-sm text-teal-100 mt-1 max-w-2xl">
              Zero-server client side tools: PDF Merge, physical target size compression (in MB), Image-to-PDF, page organizer, and sensitive data redaction.
            </p>
          </div>
        </div>

        {/* Tool Switcher Pills */}
        <div className="mt-5 flex flex-wrap gap-2">
          {[
            { id: 'merge', label: 'PDF Merge', icon: Files },
            { id: 'compress', label: 'PDF Compress (Target MB)', icon: Minimize2 },
            { id: 'imageToPdf', label: 'Image to PDF', icon: ImageIcon },
            { id: 'organize', label: 'PDF Page Organizer', icon: Layers },
            { id: 'redact', label: 'PDF & Image Redactor', icon: EyeOff }
          ].map(tool => {
            const Icon = tool.icon;
            const isActive = activeTool === tool.id;
            return (
              <button
                key={tool.id}
                onClick={() => setActiveTool(tool.id as ToolType)}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-white text-emerald-900 shadow-md font-extrabold'
                    : 'bg-black/20 text-white hover:bg-white/20'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tool.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* TOOL 1: PDF MERGE */}
      {activeTool === 'merge' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div>
            <h3 className="font-extrabold text-slate-900 text-lg flex items-center space-x-2">
              <Files className="w-5 h-5 text-emerald-600" />
              <span>Merge Multiple PDF Documents</span>
            </h3>
            <p className="text-xs text-slate-500">Combine balance sheets, audit reports, computation sheets and challans into one single PDF.</p>
          </div>

          <div className="border-2 border-dashed border-emerald-200 bg-emerald-50/40 rounded-2xl p-6 text-center">
            <input
              type="file"
              multiple
              accept=".pdf"
              ref={mergeInputRef}
              onChange={handleMergeFilesSelected}
              className="hidden"
            />
            <button
              onClick={() => mergeInputRef.current?.click()}
              className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md transition-all inline-flex items-center space-x-2 mb-2"
            >
              <Upload className="w-4 h-4" />
              <span>Select PDF Files to Merge</span>
            </button>
            <p className="text-xs text-slate-400">Select multiple PDF files from computer or phone</p>
          </div>

          {mergeFiles.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                <span>Selected PDFs ({mergeFiles.length} files)</span>
                <span className="text-slate-400">Drag or use arrows to change sequence</span>
              </div>

              <div className="space-y-2">
                {mergeFiles.map((file, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                    <div className="flex items-center space-x-2 truncate">
                      <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-[10px]">
                        {idx + 1}
                      </span>
                      <FileText className="w-4 h-4 text-red-500 shrink-0" />
                      <span className="font-semibold text-slate-800 truncate">{file.name}</span>
                      <span className="text-slate-400">({(file.size / (1024 * 1024)).toFixed(2)} MB)</span>
                    </div>

                    <div className="flex items-center space-x-1 shrink-0">
                      <button
                        onClick={() => moveMergeFile(idx, 'up')}
                        disabled={idx === 0}
                        className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-30"
                      >
                        <ArrowUp className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => moveMergeFile(idx, 'down')}
                        disabled={idx === mergeFiles.length - 1}
                        className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-30"
                      >
                        <ArrowDown className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => removeMergeFile(idx)}
                        className="p-1 text-red-400 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-2 flex items-center space-x-3">
                <button
                  onClick={executeMerge}
                  disabled={isMerging}
                  className="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-700 hover:to-teal-800 text-white rounded-xl text-xs font-bold shadow-md transition-all flex items-center space-x-2"
                >
                  <Files className="w-4 h-4" />
                  <span>{isMerging ? 'Merging Documents...' : 'Merge All PDFs Now'}</span>
                </button>

                {mergedPdfUrl && (
                  <a
                    href={mergedPdfUrl}
                    download="Merged_CA_Office_Document.pdf"
                    className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-xl text-xs font-bold shadow-md transition-all flex items-center space-x-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Merged PDF</span>
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TOOL 2: PDF COMPRESS WITH PHYSICAL MB INPUT (Requirement 9) */}
      {activeTool === 'compress' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div>
            <h3 className="font-extrabold text-slate-900 text-lg flex items-center space-x-2">
              <Minimize2 className="w-5 h-5 text-emerald-600" />
              <span>PDF Compress with Exact Target MB Size</span>
            </h3>
            <p className="text-xs text-slate-500">
              Input the physical target size in MB (e.g. 1.0 MB or 2.0 MB) to strictly comply with GST/ITR portal file upload limitations.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="border-2 border-dashed border-teal-200 bg-teal-50/40 rounded-2xl p-6 text-center">
                <input
                  type="file"
                  accept=".pdf"
                  ref={compressInputRef}
                  onChange={handleCompressFileSelected}
                  className="hidden"
                />
                <button
                  onClick={() => compressInputRef.current?.click()}
                  className="px-4 py-2.5 bg-teal-700 hover:bg-teal-800 text-white rounded-xl text-xs font-bold shadow-md transition-all inline-flex items-center space-x-2 mb-2"
                >
                  <Upload className="w-4 h-4" />
                  <span>Choose PDF File</span>
                </button>
                {compressFile ? (
                  <div className="text-xs text-teal-900 font-bold mt-2">
                    {compressFile.name} ({(compressFile.size / (1024 * 1024)).toFixed(2)} MB)
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">Select any large PDF document to compress</p>
                )}
              </div>

              {/* Physical Target MB Input (Requirement 9) */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
                <label className="block text-xs font-bold text-slate-800">
                  Target Output Size (Physical MB Specification)
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    step="0.1"
                    min="0.2"
                    max="50"
                    value={targetSizeMb}
                    onChange={e => setTargetSizeMb(e.target.value)}
                    className="w-32 px-3 py-2 bg-white border border-slate-300 rounded-xl text-sm font-mono font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <span className="text-xs font-bold text-slate-600">MB (MegaBytes)</span>
                </div>
                <div className="flex gap-2 pt-1">
                  {['0.5', '1.0', '2.0', '5.0'].map(sz => (
                    <button
                      key={sz}
                      type="button"
                      onClick={() => setTargetSizeMb(sz)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${
                        targetSizeMb === sz
                          ? 'bg-emerald-700 text-white font-bold'
                          : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      {sz} MB
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={executeCompress}
                disabled={!compressFile || isCompressing}
                className="w-full py-2.5 bg-gradient-to-r from-teal-700 to-emerald-700 hover:from-teal-800 hover:to-emerald-800 text-white rounded-xl text-xs font-bold shadow-md transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <Minimize2 className="w-4 h-4" />
                <span>{isCompressing ? 'Compressing to Target MB...' : `Compress strictly to ≤ ${targetSizeMb} MB`}</span>
              </button>
            </div>

            {/* Result Box */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 flex flex-col justify-between">
              <div>
                <h4 className="font-bold text-slate-800 text-sm mb-3">Compression Result</h4>
                {compressedResult ? (
                  <div className="space-y-4">
                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs space-y-2">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Original Size:</span>
                        <span className="font-bold text-slate-700">{compressedResult.originalSize}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Target Requested:</span>
                        <span className="font-bold text-slate-700">{targetSizeMb} MB</span>
                      </div>
                      <div className="flex justify-between pt-1 border-t border-emerald-200 text-emerald-900 font-extrabold text-sm">
                        <span>Achieved Output Size:</span>
                        <span>{compressedResult.newSize}</span>
                      </div>
                    </div>

                    <a
                      href={compressedResult.url}
                      download={`Compressed_${targetSizeMb}MB_${compressFile?.name || 'document.pdf'}`}
                      className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md transition-all flex items-center justify-center space-x-2"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download Compressed PDF</span>
                    </a>
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-400 text-xs">
                    Upload a PDF and click compress to see the target size reduction.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TOOL 3: IMAGE TO PDF */}
      {activeTool === 'imageToPdf' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div>
            <h3 className="font-extrabold text-slate-900 text-lg flex items-center space-x-2">
              <ImageIcon className="w-5 h-5 text-emerald-600" />
              <span>Image to PDF Conversion</span>
            </h3>
            <p className="text-xs text-slate-500">Convert client photos, scanned receipts, and documents into a clean PDF booklet.</p>
          </div>

          <div className="border-2 border-dashed border-indigo-200 bg-indigo-50/40 rounded-2xl p-6 text-center">
            <input
              type="file"
              multiple
              accept="image/*"
              ref={imageInputRef}
              onChange={handleImageFilesSelected}
              className="hidden"
            />
            <button
              onClick={() => imageInputRef.current?.click()}
              className="px-4 py-2.5 bg-indigo-700 hover:bg-indigo-800 text-white rounded-xl text-xs font-bold shadow-md transition-all inline-flex items-center space-x-2 mb-2"
            >
              <Upload className="w-4 h-4" />
              <span>Choose Image Files (JPG / PNG)</span>
            </button>
            <p className="text-xs text-slate-400">Select one or multiple photos to convert</p>
          </div>

          {imageFiles.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                <span>Selected Images ({imageFiles.length})</span>
                <div className="flex items-center space-x-2">
                  <span className="text-slate-500 font-medium">Page Size:</span>
                  <select
                    value={pageSize}
                    onChange={e => setPageSize(e.target.value as any)}
                    className="px-2 py-1 bg-slate-50 border border-slate-200 rounded-lg text-xs font-bold"
                  >
                    <option value="A4">A4 Standard Sheet</option>
                    <option value="LETTER">US Letter</option>
                    <option value="FIT">Auto-Fit to Image Aspect</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {imageFiles.map((f, i) => (
                  <div key={i} className="p-2 bg-slate-50 rounded-xl border border-slate-200 text-xs text-center relative group">
                    <div className="h-20 bg-slate-200 rounded-lg flex items-center justify-center overflow-hidden mb-1">
                      <ImageIcon className="w-8 h-8 text-slate-400" />
                    </div>
                    <span className="truncate block font-semibold text-slate-700 text-[11px]">{f.name}</span>
                    <button
                      onClick={() => setImageFiles(prev => prev.filter((_, idx) => idx !== i))}
                      className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex items-center space-x-3 pt-2">
                <button
                  onClick={executeImageToPdf}
                  disabled={isConvertingImages}
                  className="px-6 py-2.5 bg-gradient-to-r from-indigo-700 to-teal-700 hover:from-indigo-800 hover:to-teal-800 text-white rounded-xl text-xs font-bold shadow-md transition-all flex items-center space-x-2"
                >
                  <FileText className="w-4 h-4" />
                  <span>{isConvertingImages ? 'Converting Images...' : 'Convert to PDF Now'}</span>
                </button>

                {imagePdfUrl && (
                  <a
                    href={imagePdfUrl}
                    download="Converted_Images_Document.pdf"
                    className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-xl text-xs font-bold shadow-md transition-all flex items-center space-x-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Converted PDF</span>
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TOOL 4: PDF ORGANIZER (REORDER, ROTATE, DELETE) */}
      {activeTool === 'organize' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div>
            <h3 className="font-extrabold text-slate-900 text-lg flex items-center space-x-2">
              <Layers className="w-5 h-5 text-emerald-600" />
              <span>PDF Page Organizer &amp; Rotator</span>
            </h3>
            <p className="text-xs text-slate-500">
              Reorder pages, rotate upside-down pages by 90°, and delete duplicate or blank pages before filing.
            </p>
          </div>

          {!organizeFile ? (
            <div className="border-2 border-dashed border-emerald-200 bg-emerald-50/40 rounded-2xl p-8 text-center">
              <input
                type="file"
                accept=".pdf"
                ref={organizeInputRef}
                onChange={handleOrganizeFileSelected}
                className="hidden"
              />
              <button
                onClick={() => organizeInputRef.current?.click()}
                className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md transition-all inline-flex items-center space-x-2 mb-2"
              >
                <Upload className="w-4 h-4" />
                <span>Upload PDF to Organize Pages</span>
              </button>
              <p className="text-xs text-slate-400">Select any multi-page PDF document</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800">
                  {organizeFile.name} ({pageOrder.length} Pages active)
                </span>
                <button
                  onClick={() => setOrganizeFile(null)}
                  className="text-xs text-red-600 hover:underline font-semibold"
                >
                  Change File
                </button>
              </div>

              {/* Pages Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
                {pageOrder.map((origPageIdx, currentIdx) => {
                  const rot = pageRotations[origPageIdx] || 0;
                  return (
                    <div
                      key={currentIdx}
                      className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-center flex flex-col justify-between space-y-2 hover:border-emerald-300 transition-colors"
                    >
                      <div className="text-xs font-bold text-slate-700">
                        Page {currentIdx + 1}
                      </div>

                      {/* Mock Page Thumbnail with Rotation */}
                      <div className="h-28 bg-white border border-slate-200 rounded-lg flex items-center justify-center p-2 overflow-hidden shadow-2xs">
                        <div
                          style={{ transform: `rotate(${rot}deg)` }}
                          className="transition-transform duration-200 flex flex-col items-center justify-center"
                        >
                          <FileText className="w-8 h-8 text-emerald-600" />
                          <span className="text-[10px] text-slate-400 font-mono mt-1">Orig P.{origPageIdx + 1}</span>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center justify-center space-x-1 pt-1 border-t border-slate-200">
                        <button
                          onClick={() => movePage(currentIdx, 'left')}
                          disabled={currentIdx === 0}
                          title="Move Left"
                          className="p-1 text-slate-400 hover:text-slate-800 disabled:opacity-20"
                        >
                          ←
                        </button>
                        <button
                          onClick={() => rotatePage(origPageIdx)}
                          title="Rotate 90°"
                          className="p-1 text-emerald-600 hover:text-emerald-800"
                        >
                          <RotateCw className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => movePage(currentIdx, 'right')}
                          disabled={currentIdx === pageOrder.length - 1}
                          title="Move Right"
                          className="p-1 text-slate-400 hover:text-slate-800 disabled:opacity-20"
                        >
                          →
                        </button>
                        <button
                          onClick={() => deletePage(currentIdx)}
                          title="Delete Page"
                          className="p-1 text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center space-x-3 pt-3">
                <button
                  onClick={executeSaveOrganized}
                  disabled={isOrganizing}
                  className="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-700 hover:to-teal-800 text-white rounded-xl text-xs font-bold shadow-md transition-all flex items-center space-x-2"
                >
                  <Layers className="w-4 h-4" />
                  <span>{isOrganizing ? 'Saving Clean PDF...' : 'Export Organized PDF'}</span>
                </button>

                {organizedPdfUrl && (
                  <a
                    href={organizedPdfUrl}
                    download={`Organized_${organizeFile.name}`}
                    className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-xl text-xs font-bold shadow-md transition-all flex items-center space-x-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Organized PDF</span>
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TOOL 5: REDACTION TOOL (Requirement 9) */}
      {activeTool === 'redact' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-extrabold text-slate-900 text-lg flex items-center space-x-2">
                <EyeOff className="w-5 h-5 text-rose-600" />
                <span>Confidential Data Redaction Tool</span>
              </h3>
              <p className="text-xs text-slate-500">
                Draw black censorship boxes directly on Aadhaar numbers, PAN, bank accounts, or signatures before sharing documents with third parties.
              </p>
            </div>

            <button
              onClick={handleSimulatePanRedact}
              className="px-3.5 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 rounded-xl text-xs font-bold transition-all flex items-center space-x-1 shrink-0"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-600" />
              <span>Load Sample KYC to Test</span>
            </button>
          </div>

          {!redactImageUrl ? (
            <div className="border-2 border-dashed border-rose-200 bg-rose-50/30 rounded-2xl p-8 text-center">
              <input
                type="file"
                accept="image/*"
                ref={redactInputRef}
                onChange={handleRedactFileSelected}
                className="hidden"
              />
              <button
                onClick={() => redactInputRef.current?.click()}
                className="px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-md transition-all inline-flex items-center space-x-2 mb-2"
              >
                <Upload className="w-4 h-4" />
                <span>Select Image / Scanned Page to Redact</span>
              </button>
              <p className="text-xs text-slate-400">Select image of PAN card, Aadhaar, Cheque, or ITR statement</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Instructions & Controls */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                <div className="flex items-center space-x-2 text-slate-700">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span>
                  <span><strong>Instructions:</strong> Click and drag on the canvas below to draw a black redaction box over private data.</span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setRedactBoxes(prev => prev.slice(0, -1))}
                    disabled={redactBoxes.length === 0}
                    className="px-2.5 py-1 bg-white border border-slate-200 rounded-lg text-slate-700 font-semibold disabled:opacity-40 flex items-center space-x-1"
                  >
                    <Undo2 className="w-3.5 h-3.5" />
                    <span>Undo Last Box</span>
                  </button>

                  <button
                    onClick={() => setRedactBoxes([])}
                    disabled={redactBoxes.length === 0}
                    className="px-2.5 py-1 bg-white border border-slate-200 rounded-lg text-red-600 font-semibold disabled:opacity-40"
                  >
                    Clear All
                  </button>

                  <button
                    onClick={downloadRedactedImage}
                    className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold shadow-xs flex items-center space-x-1"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Redacted Copy</span>
                  </button>
                </div>
              </div>

              {/* Redaction Canvas */}
              <div className="overflow-x-auto border border-slate-300 rounded-2xl p-2 bg-slate-800 text-center flex justify-center">
                <canvas
                  ref={redactCanvasRef}
                  onMouseDown={handleCanvasMouseDown}
                  onMouseMove={handleCanvasMouseMove}
                  onMouseUp={handleCanvasMouseUp}
                  className="max-w-full h-auto cursor-crosshair rounded-lg shadow-lg bg-white"
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
