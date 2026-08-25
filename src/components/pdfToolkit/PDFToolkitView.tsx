import React, { useState, useRef } from 'react';
import {
  Files,
  FilePlus,
  Layers,
  Scissors,
  RotateCw,
  Trash2,
  Stamp,
  PenTool,
  Download,
  Upload,
  Eye,
  CheckCircle2,
  AlertCircle,
  FileText,
  Image as ImageIcon,
  Type,
  ArrowUp,
  ArrowDown,
  Hash,
  Loader2,
  RefreshCw,
  FileSpreadsheet,
  FileCode,
  Unlock,
  KeyRound,
  FileCheck,
  Minimize2,
  Sliders,
  Sparkles,
  Server,
  Settings,
  Globe,
  Check,
  X,
  ExternalLink
} from 'lucide-react';
import { CompanyProfile } from '../../types';
import { PDFEngine } from '../../services/pdfEngine';
import {
  convertPdfToWord,
  convertPdfToExcel,
  convertPdfToImages,
  compressPdfService,
  compressImageService,
  getPdfServiceUrl,
  setPdfServiceUrl,
  DEFAULT_PDF_SERVICE_URL,
} from '../../services/pdfService';

interface PDFToolkitViewProps {
  companyProfile: CompanyProfile;
}

type ToolkitTab =
  | 'pdf2word'
  | 'pdf2excel'
  | 'pdf2img'
  | 'compress_pdf'
  | 'compress_img'
  | 'merge'
  | 'split'
  | 'rotate_delete'
  | 'img2pdf'
  | 'decrypt'
  | 'watermark_stamp'
  | 'text_overlay';

interface LoadedFile {
  id: string;
  name: string;
  size: number;
  arrayBuffer: ArrayBuffer;
  rawFile?: File;
  pageCount?: number;
}

export const PDFToolkitView: React.FC<PDFToolkitViewProps> = ({ companyProfile }) => {
  const [activeTab, setActiveTab] = useState<ToolkitTab>('pdf2word');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // External PDF Service Endpoint Configuration state
  const [serviceUrl, setServiceUrlState] = useState<string>(getPdfServiceUrl());
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [tempServiceUrl, setTempServiceUrl] = useState<string>(serviceUrl);
  const [pingStatus, setPingStatus] = useState<'idle' | 'checking' | 'ok' | 'error'>('idle');
  const [pingMessage, setPingMessage] = useState<string>('');

  // Merge state
  const [mergeFiles, setMergeFiles] = useState<LoadedFile[]>([]);

  // Split state
  const [splitFile, setSplitFile] = useState<LoadedFile | null>(null);
  const [splitRanges, setSplitRanges] = useState<string>('1-2, 3');

  // Rotate & Delete state
  const [rotateFile, setRotateFile] = useState<LoadedFile | null>(null);
  const [rotationDegrees, setRotationDegrees] = useState<90 | 180 | 270>(90);
  const [rotatePageTarget, setRotatePageTarget] = useState<string>('all');
  const [deletePagesStr, setDeletePagesStr] = useState<string>('');

  // Compress PDF state
  const [compressPdfFile, setCompressPdfFile] = useState<LoadedFile | null>(null);
  const [compressPdfLevel, setCompressPdfLevel] = useState<'low' | 'medium' | 'high'>('medium');
  const [pdfCompressionStats, setPdfCompressionStats] = useState<{
    originalSize: number;
    compressedSize: number;
    savedPercent: number;
  } | null>(null);

  // Compress Image state
  const [compressImageFile, setCompressImageFile] = useState<{
    name: string;
    originalDataUrl: string;
    size: number;
    rawFile?: File;
  } | null>(null);
  const [imgQuality, setImgQuality] = useState<number>(60);
  const [imgMaxWidth, setImgMaxWidth] = useState<number>(1920);
  const [imgFormat, setImgFormat] = useState<'image/jpeg' | 'image/png' | 'image/webp'>('image/jpeg');
  const [imgCompressionResult, setImgCompressionResult] = useState<{
    compressedDataUrl: string;
    originalSize: number;
    compressedSize: number;
    savedPercent: number;
  } | null>(null);

  // Img to PDF state
  const [imageFiles, setImageFiles] = useState<{ name: string; base64: string }[]>([]);

  // PDF to Images state
  const [pdfToImagesFile, setPdfToImagesFile] = useState<LoadedFile | null>(null);

  // PDF to Excel state
  const [pdfToExcelFile, setPdfToExcelFile] = useState<LoadedFile | null>(null);

  // PDF to Word state
  const [pdfToWordFile, setPdfToWordFile] = useState<LoadedFile | null>(null);

  // Decrypt / Password Removal state
  const [decryptFile, setDecryptFile] = useState<LoadedFile | null>(null);
  const [pdfPassword, setPdfPassword] = useState<string>('');

  // Watermark & Stamp state
  const [stampFile, setStampFile] = useState<LoadedFile | null>(null);
  const [watermarkText, setWatermarkText] = useState<string>('CONFIDENTIAL — TRADE CLEARANCE');
  const [watermarkOpacity, setWatermarkOpacity] = useState<number>(0.25);
  const [applyStamp, setApplyStamp] = useState<boolean>(true);
  const [applySignature, setApplySignature] = useState<boolean>(true);
  const [stampPageNum, setStampPageNum] = useState<number>(1);
  const [stampPosition, setStampPosition] = useState<'bottom-right' | 'bottom-left' | 'center'>('bottom-right');
  const [addPageNumbers, setAddPageNumbers] = useState<boolean>(false);

  // In-Place Text Overlay & Redaction state
  const [overlayFile, setOverlayFile] = useState<LoadedFile | null>(null);
  const [overlayText, setOverlayText] = useState<string>('APPROVED FOR CUSTOMS DISPATCH');
  const [overlayX, setOverlayX] = useState<number>(100);
  const [overlayY, setOverlayY] = useState<number>(150);
  const [overlayFontSize, setOverlayFontSize] = useState<number>(14);
  const [overlayPageNum, setOverlayPageNum] = useState<number>(1);
  const [overlayRedactBg, setOverlayRedactBg] = useState<boolean>(true);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const showFeedback = (type: 'success' | 'error', message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 6000);
  };

  // Merge Handlers
  const handleMergeFilesUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const newLoaded: LoadedFile[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const buf = await file.arrayBuffer();
      const pageCount = await PDFEngine.getPageCount(buf);
      newLoaded.push({
        id: `file_${Date.now()}_${i}`,
        name: file.name,
        size: file.size,
        arrayBuffer: buf,
        pageCount,
      });
    }
    setMergeFiles((prev) => [...prev, ...newLoaded]);
  };

  const moveMergeFile = (index: number, direction: 'up' | 'down') => {
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= mergeFiles.length) return;
    const updated = [...mergeFiles];
    const temp = updated[index];
    updated[index] = updated[targetIdx];
    updated[targetIdx] = temp;
    setMergeFiles(updated);
  };

  const removeMergeFile = (index: number) => {
    setMergeFiles(mergeFiles.filter((_, i) => i !== index));
  };

  const handleExecuteMerge = async () => {
    if (mergeFiles.length < 2) {
      showFeedback('error', 'Please upload at least 2 PDF files to merge.');
      return;
    }

    setIsProcessing(true);
    try {
      const mergedBytes = await PDFEngine.mergePDFs(mergeFiles.map((f) => f.arrayBuffer));
      PDFEngine.downloadFile(mergedBytes, `Merged_Document_${Date.now()}.pdf`);
      showFeedback('success', `Merged ${mergeFiles.length} documents successfully.`);
    } catch (err: any) {
      showFeedback('error', `Merge error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Split Handlers
  const handleSplitFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const pageCount = await PDFEngine.getPageCount(buf);
    setSplitFile({
      id: `split_${Date.now()}`,
      name: file.name,
      size: file.size,
      arrayBuffer: buf,
      pageCount,
    });
  };

  const handleExecuteSplit = async () => {
    if (!splitFile) {
      showFeedback('error', 'Please upload a PDF file to split.');
      return;
    }

    setIsProcessing(true);
    try {
      const chunks = await PDFEngine.splitPDF(splitFile.arrayBuffer, splitRanges);
      chunks.forEach((chunk, idx) => {
        PDFEngine.downloadFile(chunk, `${splitFile.name.replace('.pdf', '')}_Part_${idx + 1}.pdf`);
      });
      showFeedback('success', `Generated ${chunks.length} separated PDF document(s).`);
    } catch (err: any) {
      showFeedback('error', `Split error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Rotate & Delete Handlers
  const handleRotateUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const pageCount = await PDFEngine.getPageCount(buf);
    setRotateFile({
      id: `rot_${Date.now()}`,
      name: file.name,
      size: file.size,
      arrayBuffer: buf,
      pageCount,
    });
  };

  const handleExecuteRotateOrDelete = async () => {
    if (!rotateFile) {
      showFeedback('error', 'Please upload a PDF file.');
      return;
    }

    setIsProcessing(true);
    try {
      let currentBuffer = rotateFile.arrayBuffer;

      // 1. Rotation if specified
      if (rotatePageTarget) {
        currentBuffer = (
          await PDFEngine.rotatePages(currentBuffer, rotationDegrees, rotatePageTarget)
        ).buffer;
      }

      // 2. Deletion if specified
      if (deletePagesStr.trim()) {
        const pagesToDelete = deletePagesStr
          .split(',')
          .map((p) => parseInt(p.trim(), 10))
          .filter((p) => !isNaN(p) && p > 0);

        if (pagesToDelete.length > 0) {
          currentBuffer = (await PDFEngine.deletePages(currentBuffer, pagesToDelete)).buffer;
        }
      }

      PDFEngine.downloadFile(new Uint8Array(currentBuffer), `Modified_${rotateFile.name}`);
      showFeedback('success', `PDF rotated & updated successfully.`);
    } catch (err: any) {
      showFeedback('error', `Operation error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Compress PDF Handlers
  const handleCompressPdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const pageCount = await PDFEngine.getPageCount(buf);
    setCompressPdfFile({
      id: `comp_pdf_${Date.now()}`,
      name: file.name,
      size: file.size,
      arrayBuffer: buf,
      rawFile: file,
      pageCount,
    });
    setPdfCompressionStats(null);
  };

  const handleExecuteCompressPdf = async () => {
    if (!compressPdfFile) {
      showFeedback('error', 'Please upload a PDF file to compress.');
      return;
    }

    setIsProcessing(true);
    try {
      const fileToUpload = compressPdfFile.rawFile || new Blob([compressPdfFile.arrayBuffer], { type: 'application/pdf' });
      // Call external service: POST {YOUR_PDF_SERVICE_URL}/compress/pdf with form field level="ebook"
      const result = await compressPdfService(fileToUpload, compressPdfFile.name, 'ebook');
      const savedBytes = Math.max(0, compressPdfFile.size - result.compressedSize);
      const savedPercent = compressPdfFile.size > 0 ? Math.round((savedBytes / compressPdfFile.size) * 100) : 0;

      setPdfCompressionStats({
        originalSize: compressPdfFile.size,
        compressedSize: result.compressedSize,
        savedPercent,
      });

      showFeedback(
        'success',
        `PDF compressed successfully: Reduced by ${savedPercent}% (${(
          (compressPdfFile.size - result.compressedSize) /
          1024
        ).toFixed(1)} KB saved)`
      );
    } catch (err: any) {
      showFeedback('error', `Compression error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Compress Image Handlers
  const handleCompressImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setCompressImageFile({
        name: file.name,
        originalDataUrl: dataUrl,
        size: file.size,
        rawFile: file,
      });
      setImgCompressionResult(null);
    };
    reader.readAsDataURL(file);
  };

  const handleExecuteCompressImage = async () => {
    if (!compressImageFile) {
      showFeedback('error', 'Please upload an image to compress.');
      return;
    }

    setIsProcessing(true);
    try {
      let fileToUpload: File | Blob;
      if (compressImageFile.rawFile) {
        fileToUpload = compressImageFile.rawFile;
      } else {
        const resp = await fetch(compressImageFile.originalDataUrl);
        fileToUpload = await resp.blob();
      }

      // Call external service: POST {YOUR_PDF_SERVICE_URL}/compress/image with form field quality=60
      const result = await compressImageService(fileToUpload, compressImageFile.name, 60);
      const savedBytes = Math.max(0, compressImageFile.size - result.compressedSize);
      const savedPercent = compressImageFile.size > 0 ? Math.round((savedBytes / compressImageFile.size) * 100) : 0;

      setImgCompressionResult({
        compressedDataUrl: URL.createObjectURL(result.blob),
        originalSize: compressImageFile.size,
        compressedSize: result.compressedSize,
        savedPercent,
      });

      showFeedback(
        'success',
        `Image compressed successfully: ${(compressImageFile.size / 1024).toFixed(1)} KB → ${(
          result.compressedSize / 1024
        ).toFixed(1)} KB (${savedPercent}% smaller)`
      );
    } catch (err: any) {
      showFeedback('error', `Image compression error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Img to PDF Handlers
  const handleImagesToPdfUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    Array.from(files).forEach((file: File) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const base64 = event.target?.result as string;
        setImageFiles((prev) => [...prev, { name: file.name, base64 }]);
      };
      reader.readAsDataURL(file);
    });
  };

  const handleExecuteImagesToPdf = async () => {
    if (imageFiles.length === 0) {
      showFeedback('error', 'Please upload at least one image.');
      return;
    }

    setIsProcessing(true);
    try {
      const pdfBytes = await PDFEngine.convertImagesToPDF(imageFiles.map((img) => img.base64));
      PDFEngine.downloadFile(pdfBytes, `Images_Compiled_${Date.now()}.pdf`);
      showFeedback('success', `Converted ${imageFiles.length} image(s) to PDF.`);
    } catch (err: any) {
      showFeedback('error', `Conversion error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // PDF to Images Handlers (Convert to Image)
  const handlePdfToImagesUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const pageCount = await PDFEngine.getPageCount(buf);
    setPdfToImagesFile({
      id: `p2img_${Date.now()}`,
      name: file.name,
      size: file.size,
      arrayBuffer: buf,
      rawFile: file,
      pageCount,
    });
  };

  const handleExecutePdfToImages = async () => {
    if (!pdfToImagesFile) {
      showFeedback('error', 'Please upload a PDF file to convert to image(s).');
      return;
    }
    setIsProcessing(true);
    try {
      const fileToUpload = pdfToImagesFile.rawFile || new Blob([pdfToImagesFile.arrayBuffer], { type: 'application/pdf' });
      // Call external service: POST {YOUR_PDF_SERVICE_URL}/convert/pdf-to-images
      const result = await convertPdfToImages(fileToUpload, pdfToImagesFile.name);
      showFeedback('success', `PDF rendered to image(s) and downloaded: ${result.filename}`);
    } catch (err: any) {
      showFeedback('error', `Image conversion error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // PDF to Excel Handlers (Convert to Excel)
  const handlePdfToExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const pageCount = await PDFEngine.getPageCount(buf);
    setPdfToExcelFile({
      id: `p2e_${Date.now()}`,
      name: file.name,
      size: file.size,
      arrayBuffer: buf,
      rawFile: file,
      pageCount,
    });
  };

  const handleExecutePdfToExcel = async () => {
    if (!pdfToExcelFile) {
      showFeedback('error', 'Please upload a PDF file to convert to Excel.');
      return;
    }
    setIsProcessing(true);
    try {
      const fileToUpload = pdfToExcelFile.rawFile || new Blob([pdfToExcelFile.arrayBuffer], { type: 'application/pdf' });
      // Call external service: POST {YOUR_PDF_SERVICE_URL}/convert/pdf-to-excel
      const result = await convertPdfToExcel(fileToUpload, pdfToExcelFile.name);
      showFeedback('success', `PDF converted to Excel spreadsheet and downloaded: ${result.filename}`);
    } catch (err: any) {
      showFeedback('error', `Excel conversion error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // PDF to Word Handlers (Convert to Word)
  const handlePdfToWordUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const pageCount = await PDFEngine.getPageCount(buf);
    setPdfToWordFile({
      id: `p2w_${Date.now()}`,
      name: file.name,
      size: file.size,
      arrayBuffer: buf,
      rawFile: file,
      pageCount,
    });
  };

  const handleExecutePdfToWord = async () => {
    if (!pdfToWordFile) {
      showFeedback('error', 'Please upload a PDF file to convert to Word.');
      return;
    }
    setIsProcessing(true);
    try {
      const fileToUpload = pdfToWordFile.rawFile || new Blob([pdfToWordFile.arrayBuffer], { type: 'application/pdf' });
      // Call external service: POST {YOUR_PDF_SERVICE_URL}/convert/pdf-to-word
      const result = await convertPdfToWord(fileToUpload, pdfToWordFile.name);
      showFeedback('success', `PDF converted to Word document and downloaded: ${result.filename}`);
    } catch (err: any) {
      showFeedback('error', `Word conversion error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Decrypt / Password Removal
  const handleDecryptUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    setDecryptFile({
      id: `dec_${Date.now()}`,
      name: file.name,
      size: file.size,
      arrayBuffer: buf,
      pageCount: 1,
    });
  };

  const handleExecuteDecrypt = async () => {
    if (!decryptFile) {
      showFeedback('error', 'Please upload a password-protected PDF.');
      return;
    }
    setIsProcessing(true);
    try {
      const unlockedBytes = await PDFEngine.decryptPDF(decryptFile.arrayBuffer, pdfPassword);
      PDFEngine.downloadFile(unlockedBytes, `Unlocked_${decryptFile.name}`);
      showFeedback('success', `Password restrictions removed successfully.`);
      setPdfPassword('');
    } catch (err: any) {
      showFeedback('error', `Decryption error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Watermark & Stamp Handlers
  const handleStampUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const pageCount = await PDFEngine.getPageCount(buf);
    setStampFile({
      id: `stamp_${Date.now()}`,
      name: file.name,
      size: file.size,
      arrayBuffer: buf,
      pageCount,
    });
  };

  const handleExecuteWatermarkAndStamp = async () => {
    if (!stampFile) {
      showFeedback('error', 'Please upload a PDF file.');
      return;
    }

    setIsProcessing(true);
    try {
      let currentBytes = new Uint8Array(stampFile.arrayBuffer);

      if (watermarkText.trim()) {
        currentBytes = await PDFEngine.addWatermark(currentBytes.buffer, watermarkText, watermarkOpacity);
      }

      if (addPageNumbers) {
        currentBytes = await PDFEngine.addPageNumbers(currentBytes.buffer, 'bottom-center');
      }

      if (applyStamp && companyProfile.stampUrl) {
        currentBytes = await PDFEngine.applyStamp(
          currentBytes.buffer,
          companyProfile.stampUrl,
          stampPageNum,
          stampPosition
        );
      }

      if (applySignature && companyProfile.signatureUrl) {
        currentBytes = await PDFEngine.applySignature(
          currentBytes.buffer,
          companyProfile.signatureUrl,
          stampPageNum,
          'bottom-left'
        );
      }

      PDFEngine.downloadFile(currentBytes, `Stamped_${stampFile.name}`);
      showFeedback('success', `Watermark, Stamp & Signature applied successfully.`);
    } catch (err: any) {
      showFeedback('error', `Stamp error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Text Overlay & Redaction
  const handleOverlayUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const pageCount = await PDFEngine.getPageCount(buf);
    setOverlayFile({
      id: `overlay_${Date.now()}`,
      name: file.name,
      size: file.size,
      arrayBuffer: buf,
      pageCount,
    });
  };

  const handleExecuteOverlay = async () => {
    if (!overlayFile || !overlayText.trim()) {
      showFeedback('error', 'Please provide a PDF and overlay text.');
      return;
    }

    setIsProcessing(true);
    try {
      const outputBytes = await PDFEngine.addTextOverlay(
        overlayFile.arrayBuffer,
        overlayPageNum,
        overlayText,
        overlayX,
        overlayY,
        overlayFontSize,
        overlayRedactBg,
        '#000000'
      );
      PDFEngine.downloadFile(outputBytes, `Redacted_${overlayFile.name}`);
      showFeedback('success', `Text overlay / replacement rendered successfully.`);
    } catch (err: any) {
      showFeedback('error', `Overlay error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const tabs = [
    { id: 'pdf2word' as ToolkitTab, label: 'Convert to Word', icon: <FileCode className="w-4 h-4" /> },
    { id: 'pdf2excel' as ToolkitTab, label: 'Convert to Excel', icon: <FileSpreadsheet className="w-4 h-4" /> },
    { id: 'pdf2img' as ToolkitTab, label: 'Convert to Image', icon: <ImageIcon className="w-4 h-4" /> },
    { id: 'compress_pdf' as ToolkitTab, label: 'Compress PDF', icon: <Minimize2 className="w-4 h-4" /> },
    { id: 'compress_img' as ToolkitTab, label: 'Compress Image', icon: <Sliders className="w-4 h-4" /> },
    { id: 'merge' as ToolkitTab, label: 'Merge PDFs', icon: <Files className="w-4 h-4" /> },
    { id: 'split' as ToolkitTab, label: 'Split PDF', icon: <Scissors className="w-4 h-4" /> },
    { id: 'rotate_delete' as ToolkitTab, label: 'Rotate & Delete', icon: <RotateCw className="w-4 h-4" /> },
    { id: 'img2pdf' as ToolkitTab, label: 'Image to PDF', icon: <ImageIcon className="w-4 h-4" /> },
    { id: 'decrypt' as ToolkitTab, label: 'Remove Password', icon: <Unlock className="w-4 h-4" /> },
    { id: 'watermark_stamp' as ToolkitTab, label: 'Watermark & Stamp', icon: <Stamp className="w-4 h-4" /> },
    { id: 'text_overlay' as ToolkitTab, label: 'Redact & Overlay', icon: <Type className="w-4 h-4" /> },
  ];

  const handleSaveServiceUrl = () => {
    const trimmed = tempServiceUrl.trim() || DEFAULT_PDF_SERVICE_URL;
    setPdfServiceUrl(trimmed);
    setServiceUrlState(trimmed);
    setIsConfigModalOpen(false);
    showFeedback('success', `PDF Service Endpoint URL set to: ${trimmed}`);
  };

  const handlePingService = async () => {
    setPingStatus('checking');
    setPingMessage('Testing connection to external conversion service...');
    try {
      const url = (tempServiceUrl.trim() || serviceUrl).replace(/\/+$/, '');
      const resp = await fetch(`${url}/health`, { method: 'GET', signal: AbortSignal.timeout(5000) });
      if (resp.ok) {
        setPingStatus('ok');
        setPingMessage(`Connected successfully (${resp.status} OK). Service is online and ready.`);
      } else {
        setPingStatus('error');
        setPingMessage(`Service responded with HTTP ${resp.status}. Verify endpoint route.`);
      }
    } catch (err: any) {
      setPingStatus('error');
      setPingMessage(`Connection failed: ${err.message}. Endpoints will be called directly during operations.`);
    }
  };

  return (
    <div id="pdf-toolkit-screen" className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <Files className="w-5 h-5 text-blue-900" />
            <span>Universal PDF & Media Document Processing Toolkit</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Role-independent suite for converting, compressing, extracting, merging, and signing trade documents.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => {
              setTempServiceUrl(serviceUrl);
              setPingStatus('idle');
              setPingMessage('');
              setIsConfigModalOpen(true);
            }}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition"
            title="Configure External PDF Conversion Service URL"
          >
            <Server className="w-3.5 h-3.5 text-slate-600" />
            <span>Service Endpoint</span>
          </button>
          <div className="px-3 py-1.5 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-lg text-xs font-semibold flex items-center space-x-1.5 shrink-0">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
            <span>Available to All Roles</span>
          </div>
        </div>
      </div>

      {/* External Service Endpoint Status Bar */}
      <div className="bg-slate-900 text-slate-100 px-4 py-2.5 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs border border-slate-800 shadow-2xs">
        <div className="flex items-center space-x-2.5 overflow-hidden">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
          <span className="font-semibold text-slate-300 shrink-0">External PDF Service URL:</span>
          <span className="font-mono text-emerald-300 text-[11px] truncate">{serviceUrl}</span>
        </div>
        <button
          onClick={() => {
            setTempServiceUrl(serviceUrl);
            setPingStatus('idle');
            setPingMessage('');
            setIsConfigModalOpen(true);
          }}
          className="self-end sm:self-auto px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded border border-slate-700 font-medium text-[11px] transition flex items-center space-x-1 shrink-0"
        >
          <Settings className="w-3 h-3 text-slate-400" />
          <span>Change URL</span>
        </button>
      </div>

      {/* Service URL Configuration Modal */}
      {isConfigModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center space-x-2">
                <Server className="w-5 h-5 text-blue-900" />
                <h3 className="font-bold text-slate-900 text-sm">External PDF Service Configuration</h3>
              </div>
              <button
                onClick={() => setIsConfigModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-slate-600">
                Conversion and compression endpoints (PDF to Word, PDF to Excel, PDF to Image, Compress PDF, Compress Image) are routed to this external service URL:
              </p>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Service Base URL</label>
                <input
                  type="url"
                  value={tempServiceUrl}
                  onChange={(e) => setTempServiceUrl(e.target.value)}
                  placeholder="https://pdf-toolkit-service.onrender.com"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:outline-hidden focus:ring-2 focus:ring-blue-900"
                />
              </div>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-1 font-mono text-[11px] text-slate-600">
                <div className="font-bold text-slate-700 font-sans text-xs mb-1">Target Endpoints:</div>
                <div>• POST <span className="text-blue-900 font-bold">{tempServiceUrl.replace(/\/+$/, '')}/convert/pdf-to-word</span></div>
                <div>• POST <span className="text-blue-900 font-bold">{tempServiceUrl.replace(/\/+$/, '')}/convert/pdf-to-excel</span></div>
                <div>• POST <span className="text-blue-900 font-bold">{tempServiceUrl.replace(/\/+$/, '')}/convert/pdf-to-images</span></div>
                <div>• POST <span className="text-blue-900 font-bold">{tempServiceUrl.replace(/\/+$/, '')}/compress/pdf</span> (level="ebook")</div>
                <div>• POST <span className="text-blue-900 font-bold">{tempServiceUrl.replace(/\/+$/, '')}/compress/image</span> (quality=60)</div>
              </div>

              {pingMessage && (
                <div
                  className={`p-2.5 rounded-lg text-xs flex items-center space-x-2 ${
                    pingStatus === 'ok'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : pingStatus === 'error'
                      ? 'bg-rose-50 text-rose-800 border border-rose-200'
                      : 'bg-blue-50 text-blue-800 border border-blue-200'
                  }`}
                >
                  {pingStatus === 'checking' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {pingStatus === 'ok' && <Check className="w-3.5 h-3.5 text-emerald-600" />}
                  {pingStatus === 'error' && <AlertCircle className="w-3.5 h-3.5 text-rose-600" />}
                  <span>{pingMessage}</span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-200">
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handlePingService}
                  disabled={pingStatus === 'checking'}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition"
                >
                  Test Connection
                </button>
                <button
                  type="button"
                  onClick={() => setTempServiceUrl(DEFAULT_PDF_SERVICE_URL)}
                  className="px-2.5 py-1.5 text-slate-500 hover:text-slate-800 text-[11px] underline"
                >
                  Reset Default
                </button>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setIsConfigModalOpen(false)}
                  className="px-3 py-1.5 border border-slate-300 text-slate-700 hover:bg-slate-100 rounded-lg text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveServiceUrl}
                  className="px-4 py-1.5 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold transition shadow-xs"
                >
                  Save Endpoint URL
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Feedback Banner */}
      {feedback && (
        <div
          className={`p-3.5 rounded-lg flex items-center space-x-2 text-xs font-medium ${
            feedback.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          )}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-xs font-bold transition ${
                isActive
                  ? 'bg-blue-900 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* 1. MERGE TAB */}
      {activeTab === 'merge' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Merge Multiple PDF Documents</h3>
              <p className="text-xs text-slate-500">
                Combine purchase orders, clearance manifests, and bill of lading files into a single sequential PDF.
              </p>
            </div>

            <label className="flex items-center space-x-1.5 px-3.5 py-2 bg-blue-50 hover:bg-blue-100 text-blue-900 border border-blue-200 rounded-lg text-xs font-bold cursor-pointer transition">
              <Upload className="w-3.5 h-3.5" />
              <span>Add PDF Files</span>
              <input
                type="file"
                multiple
                accept="application/pdf"
                ref={fileInputRef}
                onChange={handleMergeFilesUpload}
                className="hidden"
              />
            </label>
          </div>

          {mergeFiles.length === 0 ? (
            <div className="border-2 border-dashed border-slate-200 rounded-xl p-12 text-center text-slate-400 text-xs">
              <Files className="w-10 h-10 mx-auto text-slate-300 mb-2" />
              <p className="font-semibold text-slate-600">No PDF files added yet</p>
              <p className="mt-1">Click "Add PDF Files" above to select documents to combine</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xs font-bold text-slate-700">Merge Sequence ({mergeFiles.length} documents):</p>
              <div className="space-y-2">
                {mergeFiles.map((file, idx) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-900 flex items-center justify-center font-bold font-mono text-[11px]">
                        {idx + 1}
                      </span>
                      <div className="min-w-0">
                        <p className="font-bold text-slate-900 truncate">{file.name}</p>
                        <p className="text-[10px] text-slate-400 font-mono">
                          {file.pageCount} pages • {(file.size / 1024).toFixed(0)} KB
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => moveMergeFile(idx, 'up')}
                        disabled={idx === 0}
                        className="p-1 text-slate-500 hover:text-blue-900 disabled:opacity-30"
                      >
                        <ArrowUp className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => moveMergeFile(idx, 'down')}
                        disabled={idx === mergeFiles.length - 1}
                        className="p-1 text-slate-500 hover:text-blue-900 disabled:opacity-30"
                      >
                        <ArrowDown className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => removeMergeFile(idx)}
                        className="p-1 text-slate-400 hover:text-rose-600 ml-2"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  onClick={handleExecuteMerge}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-5 py-2.5 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold shadow-xs transition disabled:opacity-50"
                >
                  {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  <span>Merge & Download PDF</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. SPLIT TAB */}
      {activeTab === 'split' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Split PDF into Separate Pages / Ranges</h3>
            <p className="text-xs text-slate-500">
              Extract specific page ranges (e.g. 1-2, 3-5) into individual documents.
            </p>
          </div>

          <div className="space-y-4">
            <input
              type="file"
              accept="application/pdf"
              onChange={handleSplitFileUpload}
              className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-900 hover:file:bg-blue-100 cursor-pointer"
            />

            {splitFile && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800">{splitFile.name}</span>
                  <span className="font-mono text-slate-500">{splitFile.pageCount} Pages Total</span>
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Split Ranges (Comma separated)</label>
                  <input
                    type="text"
                    value={splitRanges}
                    onChange={(e) => setSplitRanges(e.target.value)}
                    placeholder="e.g. 1-2, 3, 4-6"
                    className="w-full px-3 py-1.5 border border-slate-300 rounded font-mono text-xs"
                  />
                  <span className="text-[10px] text-slate-400">
                    Each range creates a separate downloaded PDF file.
                  </span>
                </div>

                <button
                  onClick={handleExecuteSplit}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                  <span>Execute Split & Download</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. ROTATE & DELETE TAB */}
      {activeTab === 'rotate_delete' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Rotate & Delete Pages</h3>
            <p className="text-xs text-slate-500">
              Re-orient inverted scans or strip redundant pages from PDF dossiers.
            </p>
          </div>

          <div className="space-y-4">
            <input
              type="file"
              accept="application/pdf"
              onChange={handleRotateUpload}
              className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-900 hover:file:bg-blue-100 cursor-pointer"
            />

            {rotateFile && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-4 text-xs">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <span className="font-bold text-slate-800">{rotateFile.name}</span>
                  <span className="font-mono text-slate-500">{rotateFile.pageCount} Pages</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Rotate section */}
                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-2">
                    <span className="font-bold text-slate-700 flex items-center space-x-1">
                      <RotateCw className="w-3.5 h-3.5 text-blue-700" />
                      <span>Rotation Settings</span>
                    </span>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-600">Degrees Clockwise</label>
                      <select
                        value={rotationDegrees}
                        onChange={(e) => setRotationDegrees(Number(e.target.value) as any)}
                        className="w-full px-2 py-1 border border-slate-300 rounded text-xs"
                      >
                        <option value={90}>90° Clockwise</option>
                        <option value={180}>180° Flip</option>
                        <option value={270}>270° Counter-Clockwise</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-600">Target Pages</label>
                      <input
                        type="text"
                        value={rotatePageTarget}
                        onChange={(e) => setRotatePageTarget(e.target.value)}
                        placeholder="all or 1, 3, 5"
                        className="w-full px-2 py-1 border border-slate-300 rounded text-xs font-mono"
                      />
                    </div>
                  </div>

                  {/* Delete section */}
                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-2">
                    <span className="font-bold text-slate-700 flex items-center space-x-1">
                      <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                      <span>Delete Pages</span>
                    </span>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-600">Pages to Delete (Comma separated)</label>
                      <input
                        type="text"
                        value={deletePagesStr}
                        onChange={(e) => setDeletePagesStr(e.target.value)}
                        placeholder="e.g. 2, 4"
                        className="w-full px-2 py-1 border border-slate-300 rounded text-xs font-mono"
                      />
                      <span className="text-[10px] text-slate-400">Leave blank if no pages to delete</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={handleExecuteRotateOrDelete}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                  <span>Apply & Download Result</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. COMPRESS PDF TAB */}
      {activeTab === 'compress_pdf' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Compress & Optimize PDF File Size</h3>
            <p className="text-xs text-slate-500">
              Reduce heavy commercial scan sizes for email dispatch, fast loading, and regulatory filings.
            </p>
          </div>

          <div className="space-y-4">
            <input
              type="file"
              accept="application/pdf"
              onChange={handleCompressPdfUpload}
              className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-900 hover:file:bg-blue-100 cursor-pointer"
            />

            {compressPdfFile && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-4 text-xs">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <div>
                    <span className="font-bold text-slate-800">{compressPdfFile.name}</span>
                    <p className="text-[11px] text-slate-500">
                      Original Size: <strong className="font-mono">{(compressPdfFile.size / 1024).toFixed(1)} KB</strong> • {compressPdfFile.pageCount} Pages
                    </p>
                  </div>
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-900 font-bold text-[10px] rounded">
                    Ready to Compress
                  </span>
                </div>

                <div className="space-y-2">
                  <label className="font-bold text-slate-700">Compression Strength</label>
                  <div className="grid grid-cols-3 gap-3">
                    <button
                      type="button"
                      onClick={() => setCompressPdfLevel('low')}
                      className={`p-3 rounded-lg border text-left transition ${
                        compressPdfLevel === 'low'
                          ? 'bg-blue-50 border-blue-600 text-blue-900 shadow-xs'
                          : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <span className="font-bold text-xs block">Low Compression</span>
                      <span className="text-[10px] text-slate-500">Best Quality (~10% reduction)</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setCompressPdfLevel('medium')}
                      className={`p-3 rounded-lg border text-left transition ${
                        compressPdfLevel === 'medium'
                          ? 'bg-blue-50 border-blue-600 text-blue-900 shadow-xs'
                          : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <span className="font-bold text-xs block">Balanced (Recommended)</span>
                      <span className="text-[10px] text-slate-500">Good Quality (~20% reduction)</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setCompressPdfLevel('high')}
                      className={`p-3 rounded-lg border text-left transition ${
                        compressPdfLevel === 'high'
                          ? 'bg-blue-50 border-blue-600 text-blue-900 shadow-xs'
                          : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <span className="font-bold text-xs block">Maximum Compression</span>
                      <span className="text-[10px] text-slate-500">Smallest Size (~35% reduction)</span>
                    </button>
                  </div>
                </div>

                {pdfCompressionStats && (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between text-xs">
                    <div>
                      <span className="font-bold text-emerald-900">Compression Complete</span>
                      <p className="text-[11px] text-emerald-700">
                        Reduced from {(pdfCompressionStats.originalSize / 1024).toFixed(1)} KB to{' '}
                        {(pdfCompressionStats.compressedSize / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-lg font-bold text-emerald-800">
                        -{pdfCompressionStats.savedPercent}%
                      </span>
                    </div>
                  </div>
                )}

                <button
                  onClick={handleExecuteCompressPdf}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-5 py-2.5 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Minimize2 className="w-4 h-4" />}
                  <span>Compress & Download PDF</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. COMPRESS IMAGE TAB */}
      {activeTab === 'compress_img' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Compress & Resize Images (JPEG / PNG / WebP)</h3>
            <p className="text-xs text-slate-500">
              Downsample high-resolution photos, receipts, and cargo photos for fast uploading and low bandwidth.
            </p>
          </div>

          <div className="space-y-4">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleCompressImageUpload}
              className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-900 hover:file:bg-blue-100 cursor-pointer"
            />

            {compressImageFile && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-4 text-xs">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <span className="font-bold text-slate-800">{compressImageFile.name}</span>
                  <span className="font-mono text-slate-500">
                    Original Size: {(compressImageFile.size / 1024).toFixed(1)} KB
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Quality Slider */}
                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-2">
                    <label className="font-bold text-slate-700 flex justify-between">
                      <span>Quality Level</span>
                      <span className="font-mono text-blue-900 font-bold">{Math.round(imgQuality * 100)}%</span>
                    </label>
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      value={imgQuality}
                      onChange={(e) => setImgQuality(parseFloat(e.target.value))}
                      className="w-full accent-blue-900"
                    />
                    <span className="text-[10px] text-slate-400 block">
                      Lower percentage yields smaller file size.
                    </span>
                  </div>

                  {/* Max Width */}
                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-2">
                    <label className="font-bold text-slate-700">Max Dimension</label>
                    <select
                      value={imgMaxWidth}
                      onChange={(e) => setImgMaxWidth(Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs bg-white"
                    >
                      <option value={3840}>4K Ultra HD (3840px)</option>
                      <option value={1920}>Full HD (1920px) — Standard</option>
                      <option value={1280}>HD (1280px) — Compact</option>
                      <option value={800}>VGA (800px) — Ultra Low Size</option>
                    </select>
                    <span className="text-[10px] text-slate-400 block">
                      Scales dimensions proportionally.
                    </span>
                  </div>

                  {/* Format */}
                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-2">
                    <label className="font-bold text-slate-700">Target Output Format</label>
                    <select
                      value={imgFormat}
                      onChange={(e) => setImgFormat(e.target.value as any)}
                      className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs bg-white"
                    >
                      <option value="image/jpeg">JPEG (.jpg) — Best Compression</option>
                      <option value="image/webp">WebP (.webp) — Modern Web Standard</option>
                      <option value="image/png">PNG (.png) — Lossless</option>
                    </select>
                  </div>
                </div>

                {/* Preview Comparison */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                  <div className="p-2 bg-white border border-slate-200 rounded text-center">
                    <p className="text-[10px] font-bold text-slate-500 mb-1">Source Preview</p>
                    <img
                      src={compressImageFile.originalDataUrl}
                      alt="Original"
                      className="max-h-36 mx-auto rounded object-contain"
                    />
                  </div>
                  {imgCompressionResult && (
                    <div className="p-2 bg-emerald-50 border border-emerald-200 rounded text-center">
                      <p className="text-[10px] font-bold text-emerald-800 mb-1">
                        Compressed Preview ({(imgCompressionResult.compressedSize / 1024).toFixed(1)} KB -{' '}
                        {imgCompressionResult.savedPercent}% saved)
                      </p>
                      <img
                        src={imgCompressionResult.compressedDataUrl}
                        alt="Compressed"
                        className="max-h-36 mx-auto rounded object-contain"
                      />
                    </div>
                  )}
                </div>

                <button
                  onClick={handleExecuteCompressImage}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-5 py-2.5 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sliders className="w-4 h-4" />}
                  <span>Compress & Download Image</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 6. IMAGE TO PDF TAB */}
      {activeTab === 'img2pdf' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Compile Images into Single PDF</h3>
              <p className="text-xs text-slate-500">
                Upload JPG/PNG scans or equipment photos to bundle into a standardized A4 document.
              </p>
            </div>

            <label className="flex items-center space-x-1.5 px-3.5 py-2 bg-blue-50 hover:bg-blue-100 text-blue-900 border border-blue-200 rounded-lg text-xs font-bold cursor-pointer transition">
              <Upload className="w-3.5 h-3.5" />
              <span>Select Images</span>
              <input
                type="file"
                multiple
                accept="image/png,image/jpeg,image/jpg"
                onChange={handleImagesToPdfUpload}
                className="hidden"
              />
            </label>
          </div>

          {imageFiles.length === 0 ? (
            <div className="border-2 border-dashed border-slate-200 rounded-xl p-12 text-center text-slate-400 text-xs">
              <ImageIcon className="w-10 h-10 mx-auto text-slate-300 mb-2" />
              <p className="font-semibold text-slate-600">No images selected</p>
              <p className="mt-1">Click "Select Images" to add photos or scans</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {imageFiles.map((img, idx) => (
                  <div
                    key={idx}
                    className="relative group p-2 bg-slate-50 border border-slate-200 rounded-lg overflow-hidden"
                  >
                    <img src={img.base64} alt={img.name} className="h-24 w-full object-cover rounded" />
                    <p className="text-[10px] text-slate-600 truncate mt-1">{img.name}</p>
                    <button
                      onClick={() => setImageFiles((prev) => prev.filter((_, i) => i !== idx))}
                      className="absolute top-3 right-3 p-1 bg-rose-600 text-white rounded opacity-0 group-hover:opacity-100 transition"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={handleExecuteImagesToPdf}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-5 py-2.5 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                  <span>Generate PDF ({imageFiles.length} Pages)</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 7. PDF TO EXCEL (Convert to Excel) */}
      {activeTab === 'pdf2excel' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Convert to Excel</h3>
              <p className="text-xs text-slate-500">
                Upload a PDF document to convert data tables, items, and figures into Excel spreadsheet format via external service.
              </p>
            </div>
            <span className="px-2.5 py-1 bg-slate-100 border border-slate-200 text-slate-700 font-mono text-[11px] rounded-md shrink-0">
              POST /convert/pdf-to-excel
            </span>
          </div>

          <div className="space-y-4">
            <input
              type="file"
              accept="application/pdf"
              onChange={handlePdfToExcelUpload}
              className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-900 hover:file:bg-blue-100 cursor-pointer"
            />

            {pdfToExcelFile && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800">{pdfToExcelFile.name}</span>
                  <span className="font-mono text-slate-500">
                    {pdfToExcelFile.pageCount} Pages • {(pdfToExcelFile.size / 1024).toFixed(0)} KB
                  </span>
                </div>

                <div className="p-3 bg-emerald-50/60 border border-emerald-200 text-emerald-900 rounded-lg text-xs">
                  <p className="font-semibold flex items-center space-x-1.5">
                    <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
                    <span>External PDF to Excel Conversion Engine</span>
                  </p>
                  <p className="text-[11px] mt-0.5 text-emerald-800">
                    Posts file multipart payload to <code className="font-mono bg-white/70 px-1 py-0.5 rounded">{serviceUrl}/convert/pdf-to-excel</code> and streams the resulting spreadsheet file directly to your downloads.
                  </p>
                </div>

                <button
                  onClick={handleExecutePdfToExcel}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4" />}
                  <span>Convert to Excel</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 8. PDF TO WORD (Convert to Word) */}
      {activeTab === 'pdf2word' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Convert to Word</h3>
              <p className="text-xs text-slate-500">
                Upload a PDF document to convert to editable Microsoft Word format via external service endpoint.
              </p>
            </div>
            <span className="px-2.5 py-1 bg-slate-100 border border-slate-200 text-slate-700 font-mono text-[11px] rounded-md shrink-0">
              POST /convert/pdf-to-word
            </span>
          </div>

          <div className="space-y-4">
            <input
              type="file"
              accept="application/pdf"
              onChange={handlePdfToWordUpload}
              className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-900 hover:file:bg-blue-100 cursor-pointer"
            />

            {pdfToWordFile && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800">{pdfToWordFile.name}</span>
                  <span className="font-mono text-slate-500">
                    {pdfToWordFile.pageCount} Pages • {(pdfToWordFile.size / 1024).toFixed(0)} KB
                  </span>
                </div>

                <div className="p-3 bg-blue-50/60 border border-blue-200 text-blue-900 rounded-lg text-xs">
                  <p className="font-semibold flex items-center space-x-1.5">
                    <FileCode className="w-4 h-4 text-blue-700" />
                    <span>External PDF to Word Conversion Engine</span>
                  </p>
                  <p className="text-[11px] mt-0.5 text-blue-800">
                    Posts file multipart payload to <code className="font-mono bg-white/70 px-1 py-0.5 rounded">{serviceUrl}/convert/pdf-to-word</code> and streams the resulting document file directly to your downloads.
                  </p>
                </div>

                <button
                  onClick={handleExecutePdfToWord}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileCode className="w-4 h-4" />}
                  <span>Convert to Word</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 9. DECRYPT / REMOVE PASSWORD TAB */}
      {activeTab === 'decrypt' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Remove PDF Passwords & Permissions</h3>
            <p className="text-xs text-slate-500">
              Strip owner passwords and printing/copying restrictions from secured PDF documents.
            </p>
          </div>

          <div className="space-y-4">
            <input
              type="file"
              accept="application/pdf"
              onChange={handleDecryptUpload}
              className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-900 hover:file:bg-blue-100 cursor-pointer"
            />

            {decryptFile && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800">{decryptFile.name}</span>
                  <span className="font-mono text-slate-500">{(decryptFile.size / 1024).toFixed(0)} KB</span>
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Known Document Password (if required)</label>
                  <input
                    type="password"
                    value={pdfPassword}
                    onChange={(e) => setPdfPassword(e.target.value)}
                    placeholder="Enter password (leave blank for restriction removal)"
                    className="w-full px-3 py-1.5 border border-slate-300 rounded text-xs font-mono"
                  />
                </div>

                <button
                  onClick={handleExecuteDecrypt}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  <Unlock className="w-4 h-4" />
                  <span>Unlock & Download PDF</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 10. WATERMARK & STAMP TAB */}
      {activeTab === 'watermark_stamp' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Apply Watermarks, Company Stamp & Signature</h3>
            <p className="text-xs text-slate-500">
              Stamp trade contracts and manifests with corporate verification seals and diagonal diagonal security text.
            </p>
          </div>

          <div className="space-y-4">
            <input
              type="file"
              accept="application/pdf"
              onChange={handleStampUpload}
              className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-900 hover:file:bg-blue-100 cursor-pointer"
            />

            {stampFile && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-4 text-xs">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <span className="font-bold text-slate-800">{stampFile.name}</span>
                  <span className="font-mono text-slate-500">{stampFile.pageCount} Pages</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Watermark */}
                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-2">
                    <span className="font-bold text-slate-700">Diagonal Security Watermark</span>
                    <input
                      type="text"
                      value={watermarkText}
                      onChange={(e) => setWatermarkText(e.target.value)}
                      placeholder="e.g. CONFIDENTIAL"
                      className="w-full px-2 py-1 border border-slate-300 rounded text-xs"
                    />
                    <div className="flex items-center space-x-2">
                      <label className="text-[11px] text-slate-600">Opacity:</label>
                      <input
                        type="range"
                        min="0.05"
                        max="0.8"
                        step="0.05"
                        value={watermarkOpacity}
                        onChange={(e) => setWatermarkOpacity(parseFloat(e.target.value))}
                        className="accent-blue-900 flex-1"
                      />
                      <span className="text-[10px] font-mono">{Math.round(watermarkOpacity * 100)}%</span>
                    </div>
                  </div>

                  {/* Stamp & Signature */}
                  <div className="p-3 bg-white border border-slate-200 rounded-lg space-y-2">
                    <span className="font-bold text-slate-700">Official Brand Assets</span>
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={applyStamp}
                        onChange={(e) => setApplyStamp(e.target.checked)}
                        className="text-blue-900 rounded"
                      />
                      <span>Apply Company Stamp Seal (Page {stampPageNum})</span>
                    </label>

                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={applySignature}
                        onChange={(e) => setApplySignature(e.target.checked)}
                        className="text-blue-900 rounded"
                      />
                      <span>Apply Authorized Signature</span>
                    </label>

                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={addPageNumbers}
                        onChange={(e) => setAddPageNumbers(e.target.checked)}
                        className="text-blue-900 rounded"
                      />
                      <span>Add Page Numbers ("Page X of Y")</span>
                    </label>
                  </div>
                </div>

                <button
                  onClick={handleExecuteWatermarkAndStamp}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                  <span>Apply & Download Stamped PDF</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 11. REDACT & OVERLAY TAB */}
      {activeTab === 'text_overlay' && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Redact & In-Place Text Overlay</h3>
            <p className="text-xs text-slate-500">
              Cover sensitive numbers with an opaque badge and overlay verified clearance numbers.
            </p>
          </div>

          <div className="space-y-4">
            <input
              type="file"
              accept="application/pdf"
              onChange={handleOverlayUpload}
              className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-900 hover:file:bg-blue-100 cursor-pointer"
            />

            {overlayFile && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3 text-xs">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <span className="font-bold text-slate-800">{overlayFile.name}</span>
                  <span className="font-mono text-slate-500">{overlayFile.pageCount} Pages</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Overlay Text</label>
                    <input
                      type="text"
                      value={overlayText}
                      onChange={(e) => setOverlayText(e.target.value)}
                      className="w-full px-2 py-1 border border-slate-300 rounded text-xs"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Position (X, Y in points)</label>
                    <div className="flex space-x-2">
                      <input
                        type="number"
                        value={overlayX}
                        onChange={(e) => setOverlayX(Number(e.target.value))}
                        className="w-1/2 px-2 py-1 border border-slate-300 rounded text-xs font-mono"
                        placeholder="X"
                      />
                      <input
                        type="number"
                        value={overlayY}
                        onChange={(e) => setOverlayY(Number(e.target.value))}
                        className="w-1/2 px-2 py-1 border border-slate-300 rounded text-xs font-mono"
                        placeholder="Y"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="font-semibold text-slate-700">Target Page #</label>
                    <input
                      type="number"
                      min={1}
                      max={overlayFile.pageCount || 1}
                      value={overlayPageNum}
                      onChange={(e) => setOverlayPageNum(Number(e.target.value))}
                      className="w-full px-2 py-1 border border-slate-300 rounded text-xs font-mono"
                    />
                  </div>
                </div>

                <div className="pt-1">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={overlayRedactBg}
                      onChange={(e) => setOverlayRedactBg(e.target.checked)}
                      className="text-blue-900 rounded"
                    />
                    <span>Cover background underneath text with opaque white block (Redaction)</span>
                  </label>
                </div>

                <button
                  onClick={handleExecuteOverlay}
                  disabled={isProcessing}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                  <span>Render Overlay & Download</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
