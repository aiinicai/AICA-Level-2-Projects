import React, { useState, useRef } from 'react';
import {
  X,
  UploadCloud,
  Camera,
  Sparkles,
  AlertCircle,
  AlertTriangle,
  Check,
  Calendar,
  Tag,
  CreditCard,
  Store,
  FileText,
  ListOrdered,
  RefreshCw,
  Plus,
  Trash2,
} from 'lucide-react';
import { Transaction, TransactionCategory, PaymentMode, ExtractedInvoiceData, LineItem } from '../types';
import { CATEGORY_CONFIG } from './CategoryIcon';
import { checkDuplicateTransaction } from '../utils/storage';
import { formatINR } from '../utils/formatters';

interface ScanInvoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (transactionData: Omit<Transaction, 'id' | 'createdAt'>) => void;
}

const CATEGORIES: TransactionCategory[] = [
  'Food',
  'Travel',
  'Shopping',
  'Bills',
  'Investment',
  'Healthcare',
  'Entertainment',
  'Other',
];

const PAYMENT_MODES: PaymentMode[] = ['UPI', 'Card', 'Cash', 'Bank Transfer'];

export const ScanInvoiceModal: React.FC<ScanInvoiceModalProps> = ({ isOpen, onClose, onSave }) => {
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [mimeType, setMimeType] = useState<string>('image/jpeg');
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState<string>('');
  const [scanError, setScanError] = useState<string | null>(null);

  // Extracted & Editable Fields
  const [extractedData, setExtractedData] = useState<ExtractedInvoiceData | null>(null);
  const [date, setDate] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [category, setCategory] = useState<TransactionCategory>('Food');
  const [merchantName, setMerchantName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [paymentMode, setPaymentMode] = useState<PaymentMode>('UPI');
  const [lineItems, setLineItems] = useState<LineItem[]>([]);
  const [showLineItems, setShowLineItems] = useState(true);

  // Duplicate Check
  const [duplicates, setDuplicates] = useState<Transaction[]>([]);
  const [acknowledgedDuplicate, setAcknowledgedDuplicate] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const resetModal = () => {
    setImagePreview(null);
    setIsScanning(false);
    setScanStep('');
    setScanError(null);
    setExtractedData(null);
    setDate('');
    setAmount('');
    setCategory('Food');
    setMerchantName('');
    setDescription('');
    setPaymentMode('UPI');
    setLineItems([]);
    setDuplicates([]);
    setAcknowledgedDuplicate(false);
  };

  const handleClose = () => {
    resetModal();
    onClose();
  };

  const loadSampleImage = async (url: string, name: string) => {
    try {
      setIsScanning(true);
      setScanError(null);
      setScanStep(`Loading sample: ${name}...`);
      const resp = await fetch(url);
      const blob = await resp.blob();
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        setImagePreview(base64);
        scanImageWithAI(base64, 'image/png');
      };
      reader.onerror = () => {
        setScanError('Failed to read sample document.');
        setIsScanning(false);
      };
      reader.readAsDataURL(blob);
    } catch (err: any) {
      setScanError('Could not load sample image. Please try again.');
      setIsScanning(false);
    }
  };

  const processFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      setScanError('Please select a valid image file (PNG, JPEG, WebP, etc.).');
      return;
    }

    setScanError(null);
    setMimeType(file.type);

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setImagePreview(result);
      scanImageWithAI(result, file.type);
    };
    reader.onerror = () => {
      setScanError('Failed to read the selected file.');
    };
    reader.readAsDataURL(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const scanImageWithAI = async (base64Image: string, type: string) => {
    setIsScanning(true);
    setScanError(null);
    setScanStep('Optimizing document & reading visual tokens...');

    try {
      setTimeout(() => {
        setScanStep('AI Vision extracting merchant, date, amounts & items...');
      }, 900);

      const response = await fetch('/api/scan-invoice', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          imageBase64: base64Image,
          mimeType: type,
        }),
      });

      const resData = await response.json();

      if (!response.ok || !resData.success) {
        throw new Error(resData.error || 'Failed to scan image with AI.');
      }

      const data: ExtractedInvoiceData = resData.data;
      setExtractedData(data);

      // Handle unreadable / blurry edge case per instructions:
      // "If the AI cannot confidently read the image (blurry, unrelated image, unreadable text),
      // show a clear message asking the user to retake the photo or enter manually — do not guess or fabricate values."
      if (data.confidence === 'unreadable' || (!data.merchantName && (!data.totalAmount || data.totalAmount <= 0))) {
        setScanError(
          data.unreadableReason ||
            'Unable to read document clearly (image might be blurry, too dark, or not an invoice/receipt). Please retake the photo in better light or enter details manually.'
        );
        setIsScanning(false);
        return;
      }

      // Pre-fill editable form with extracted data
      const extractedDate = data.date && data.date.match(/^\d{4}-\d{2}-\d{2}$/)
        ? data.date
        : new Date().toISOString().slice(0, 10);
      setDate(extractedDate);

      const extractedAmt = data.totalAmount && data.totalAmount > 0 ? data.totalAmount.toString() : '';
      setAmount(extractedAmt);

      if (data.category && CATEGORIES.includes(data.category)) {
        setCategory(data.category);
      } else {
        setCategory('Food');
      }

      setMerchantName(data.merchantName || '');
      setDescription(data.description || data.merchantName || 'Scanned expense');

      if (data.paymentMode && PAYMENT_MODES.includes(data.paymentMode)) {
        setPaymentMode(data.paymentMode);
      } else {
        setPaymentMode('UPI');
      }

      if (Array.isArray(data.lineItems) && data.lineItems.length > 0) {
        setLineItems(data.lineItems);
      } else {
        setLineItems([]);
      }

      // Check duplicates with extracted values
      if (extractedDate && extractedAmt) {
        const foundDups = checkDuplicateTransaction(extractedDate, parseFloat(extractedAmt));
        setDuplicates(foundDups);
      }
    } catch (err: any) {
      console.error('AI Scan error:', err);
      setScanError(err.message || 'Error communicating with AI vision scanner. Please try again or enter manually.');
    } finally {
      setIsScanning(false);
    }
  };

  // Re-check duplicates if user modifies date or amount
  const handleAmountChange = (val: string) => {
    setAmount(val);
    const num = parseFloat(val);
    if (date && !isNaN(num) && num > 0) {
      setDuplicates(checkDuplicateTransaction(date, num));
    } else {
      setDuplicates([]);
    }
  };

  const handleDateChange = (val: string) => {
    setDate(val);
    const num = parseFloat(amount);
    if (val && !isNaN(num) && num > 0) {
      setDuplicates(checkDuplicateTransaction(val, num));
    } else {
      setDuplicates([]);
    }
  };

  const handleAddLineItem = () => {
    setLineItems([...lineItems, { item: '', amount: 0 }]);
  };

  const handleRemoveLineItem = (index: number) => {
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const handleLineItemChange = (index: number, field: 'item' | 'amount', value: any) => {
    const updated = [...lineItems];
    if (field === 'amount') {
      updated[index].amount = parseFloat(value) || 0;
    } else {
      updated[index].item = value;
    }
    setLineItems(updated);
  };

  const handleConfirmAndSave = (e: React.FormEvent) => {
    e.preventDefault();
    const numAmount = parseFloat(amount);

    if (isNaN(numAmount) || numAmount <= 0) {
      setScanError('Please enter a valid total amount.');
      return;
    }

    if (!merchantName.trim() && !description.trim()) {
      setScanError('Please enter a merchant or description.');
      return;
    }

    if (duplicates.length > 0 && !acknowledgedDuplicate) {
      setScanError('Please acknowledge potential duplicate warning before saving.');
      return;
    }

    // Save with image source
    onSave({
      date,
      amount: numAmount,
      category,
      merchantName: merchantName.trim() || undefined,
      description: description.trim() || merchantName.trim() || 'Scanned expense',
      paymentMode,
      source: 'image',
      lineItems: lineItems.filter((li) => li.item.trim() !== ''),
    });

    handleClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto animate-in fade-in">
      <div className="relative w-full max-w-2xl rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden my-8 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Scan Invoice or Receipt
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                AI Vision extracts merchant, date, total amount & line items
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          {/* Step 1: Upload or Retake Area */}
          {!imagePreview ? (
            <div className="space-y-4">
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const file = e.dataTransfer.files?.[0];
                  if (file) processFile(file);
                }}
                className="group border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-emerald-500 dark:hover:border-emerald-400 rounded-2xl p-8 text-center transition cursor-pointer bg-slate-50/50 dark:bg-slate-800/30"
              >
                <div className="mx-auto w-14 h-14 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-3 group-hover:scale-105 transition">
                  <UploadCloud className="w-7 h-7" />
                </div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  Drop invoice, bill or statement here
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Supports PNG, JPG, JPEG, WebP. Receipts, UPI screenshots, or investment statements.
                </p>

                <div className="mt-5 flex items-center justify-center gap-3">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition active:scale-95 cursor-pointer"
                  >
                    <UploadCloud className="w-4 h-4" />
                    <span>Choose File</span>
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      cameraInputRef.current?.click();
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold transition active:scale-95 cursor-pointer"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Take Photo</span>
                  </button>
                </div>
              </div>

              {/* Hidden file inputs */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileChange}
              />
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={handleFileChange}
              />

              {/* Ready-made Test Samples Section */}
              <div className="pt-2 border-t border-slate-200/80 dark:border-slate-800">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                    <span>Try With Ready-Made Test Samples:</span>
                  </span>
                  <span className="text-[10px] text-slate-400 font-semibold">
                    Click any sample to scan
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {/* Sample 1: Handwritten Tea Stall Bill */}
                  <button
                    type="button"
                    onClick={() => loadSampleImage('/samples/handwritten-tea-bill.png', 'Handwritten Tea Stall Bill')}
                    className="flex items-center gap-3 p-3 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/60 dark:bg-amber-950/30 hover:bg-amber-100/70 dark:hover:bg-amber-900/40 text-left transition cursor-pointer group shadow-2xs hover:scale-[1.01]"
                  >
                    <div className="w-12 h-12 rounded-lg bg-amber-200/80 dark:bg-amber-900/60 text-amber-800 dark:text-amber-200 flex items-center justify-center font-bold text-lg shrink-0 overflow-hidden border border-amber-300">
                      ☕
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-slate-900 dark:text-white truncate">
                          Handwritten Tea Bill
                        </span>
                        <span className="text-xs font-extrabold text-amber-700 dark:text-amber-300">
                          ₹180
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                        Sharma Tea Stall • Chai, bun maska, samosa
                      </p>
                      <span className="inline-block mt-1 text-[9px] font-bold text-amber-800 dark:text-amber-300 bg-amber-200/60 dark:bg-amber-900/80 px-1.5 py-0.5 rounded">
                        Tests Handwriting AI Vision
                      </span>
                    </div>
                  </button>

                  {/* Sample 2: Shopping Thermal Receipt */}
                  <button
                    type="button"
                    onClick={() => loadSampleImage('/samples/shopping-bill.png', 'Supermarket Shopping Receipt')}
                    className="flex items-center gap-3 p-3 rounded-xl border border-purple-200 dark:border-purple-900/60 bg-purple-50/60 dark:bg-purple-950/30 hover:bg-purple-100/70 dark:hover:bg-purple-900/40 text-left transition cursor-pointer group shadow-2xs hover:scale-[1.01]"
                  >
                    <div className="w-12 h-12 rounded-lg bg-purple-200/80 dark:bg-purple-900/60 text-purple-800 dark:text-purple-200 flex items-center justify-center font-bold text-lg shrink-0 overflow-hidden border border-purple-300">
                      🛒
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-slate-900 dark:text-white truncate">
                          Shopping Superstore Bill
                        </span>
                        <span className="text-xs font-extrabold text-purple-700 dark:text-purple-300">
                          ₹1,870
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                        Reliance Smart • Rice, oil, ghee, chocolate
                      </p>
                      <span className="inline-block mt-1 text-[9px] font-bold text-purple-800 dark:text-purple-300 bg-purple-200/60 dark:bg-purple-900/80 px-1.5 py-0.5 rounded">
                        Tests Multi-Item Table Extraction
                      </span>
                    </div>
                  </button>

                  {/* Sample 3: Mutual Fund Investment Statement */}
                  <button
                    type="button"
                    onClick={() => loadSampleImage('/samples/investment-statement.png', 'Mutual Fund SIP Statement')}
                    className="flex items-center gap-3 p-3 rounded-xl border border-emerald-300 dark:border-emerald-800/80 bg-emerald-50/60 dark:bg-emerald-950/30 hover:bg-emerald-100/70 dark:hover:bg-emerald-900/40 text-left transition cursor-pointer group shadow-2xs hover:scale-[1.01]"
                  >
                    <div className="w-12 h-12 rounded-lg bg-emerald-200/80 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200 flex items-center justify-center font-bold text-lg shrink-0 overflow-hidden border border-emerald-300">
                      📈
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-slate-900 dark:text-white truncate">
                          Investment Statement
                        </span>
                        <span className="text-xs font-extrabold text-emerald-700 dark:text-emerald-300">
                          ₹25,000
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                        HDFC Mutual Fund • Nifty 50 Index Fund SIP
                      </p>
                      <span className="inline-block mt-1 text-[9px] font-bold text-emerald-800 dark:text-emerald-300 bg-emerald-200/60 dark:bg-emerald-900/80 px-1.5 py-0.5 rounded">
                        Tests Investment Category Categorization
                      </span>
                    </div>
                  </button>

                  {/* Sample 4: Airline Flight Tax Invoice */}
                  <button
                    type="button"
                    onClick={() => loadSampleImage('/samples/flight-invoice.png', 'Flight Booking Tax Invoice')}
                    className="flex items-center gap-3 p-3 rounded-xl border border-sky-200 dark:border-sky-900/60 bg-sky-50/60 dark:bg-sky-950/30 hover:bg-sky-100/70 dark:hover:bg-sky-900/40 text-left transition cursor-pointer group shadow-2xs hover:scale-[1.01]"
                  >
                    <div className="w-12 h-12 rounded-lg bg-sky-200/80 dark:bg-sky-900/60 text-sky-800 dark:text-sky-200 flex items-center justify-center font-bold text-lg shrink-0 overflow-hidden border border-sky-300">
                      ✈️
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-slate-900 dark:text-white truncate">
                          Flight Tax Invoice
                        </span>
                        <span className="text-xs font-extrabold text-sky-700 dark:text-sky-300">
                          ₹6,285
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                        IndiGo Airlines • BOM to DEL (Mumbai - Delhi)
                      </p>
                      <span className="inline-block mt-1 text-[9px] font-bold text-sky-800 dark:text-sky-300 bg-sky-200/60 dark:bg-sky-900/80 px-1.5 py-0.5 rounded">
                        Tests Travel Category &amp; Taxes
                      </span>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Image Preview Card with Retake Option */
            <div className="flex items-center gap-4 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40">
              <div className="relative w-16 h-16 rounded-lg overflow-hidden bg-slate-200 dark:bg-slate-700 shrink-0 border border-slate-200 dark:border-slate-700">
                <img
                  src={imagePreview}
                  alt="Scanned Receipt"
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                  Uploaded Document
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  {isScanning ? scanStep : 'Processed with Gemini AI Vision'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setImagePreview(null);
                  setExtractedData(null);
                  setScanError(null);
                }}
                disabled={isScanning}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 text-xs font-medium transition cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retake</span>
              </button>
            </div>
          )}

          {/* Loading Indicator with Animated Scanner Pulse */}
          {isScanning && (
            <div className="py-8 px-4 text-center rounded-2xl border border-emerald-200 dark:border-emerald-800/50 bg-emerald-50/40 dark:bg-emerald-950/20">
              <div className="relative mx-auto w-16 h-16 mb-3">
                <div className="absolute inset-0 rounded-2xl bg-emerald-500/20 animate-ping" />
                <div className="relative w-16 h-16 rounded-2xl bg-emerald-600 text-white flex items-center justify-center shadow-lg">
                  <Sparkles className="w-8 h-8 animate-spin" style={{ animationDuration: '4s' }} />
                </div>
              </div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                Scanning Document with AI...
              </h4>
              <p className="text-xs text-emerald-700 dark:text-emerald-400 mt-1 max-w-sm mx-auto font-medium">
                {scanStep}
              </p>
              <div className="w-48 h-1.5 bg-emerald-200 dark:bg-emerald-900/60 rounded-full mx-auto mt-4 overflow-hidden">
                <div className="w-full h-full bg-emerald-600 rounded-full animate-pulse" />
              </div>
            </div>
          )}

          {/* Scan Error or Unreadable Message */}
          {scanError && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs space-y-2">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold text-rose-900 dark:text-rose-200">
                    Cannot Clearly Read Document
                  </p>
                  <p className="mt-0.5">{scanError}</p>
                </div>
              </div>
              <div className="flex gap-2 pt-2 border-t border-rose-200 dark:border-rose-900">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3 py-1.5 rounded-lg bg-rose-600 text-white text-xs font-semibold hover:bg-rose-700 transition"
                >
                  Retake Photo
                </button>
              </div>
            </div>
          )}

          {/* Edge Case: Handwriting or non-English script detected */}
          {extractedData?.isHandwrittenOrNonEnglish && (
            <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Handwritten or Non-English Text Detected: </span>
                Extraction confidence is moderate. Please review the prefilled values below and make any necessary adjustments before saving.
              </div>
            </div>
          )}

          {/* Edge Case: Duplicate Warning Banner */}
          {duplicates.length > 0 && (
            <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold">Similar Transaction Detected</p>
                  <p>
                    Found {duplicates.length} existing entry for {formatINR(parseFloat(amount))} on {date}:
                  </p>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                    {duplicates[0].merchantName || duplicates[0].description} ({duplicates[0].category})
                  </p>
                  <label className="flex items-center gap-2 mt-2 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={acknowledgedDuplicate}
                      onChange={(e) => setAcknowledgedDuplicate(e.target.checked)}
                      className="rounded text-emerald-600 focus:ring-emerald-500 w-4 h-4"
                    />
                    <span>I confirm this is not a duplicate and want to save</span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Pre-filled Editable Form: ONLY visible when data is extracted and not currently scanning */}
          {extractedData && !isScanning && extractedData.confidence !== 'unreadable' && (
            <form onSubmit={handleConfirmAndSave} className="space-y-4 pt-2">
              <div className="flex items-center justify-between pb-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
                  Review & Correct Extracted Details
                </span>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400">
                  Confidence: {extractedData.confidence.toUpperCase()}
                </span>
              </div>

              {/* Amount & Date Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Total Amount (₹) <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 font-semibold text-base">
                      ₹
                    </span>
                    <input
                      type="number"
                      step="any"
                      required
                      value={amount}
                      onChange={(e) => handleAmountChange(e.target.value)}
                      className="w-full pl-8 pr-4 py-2.5 text-base font-bold rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-hidden focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Transaction Date <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <Calendar className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                    <input
                      type="date"
                      required
                      value={date}
                      onChange={(e) => handleDateChange(e.target.value)}
                      className="w-full pl-10 pr-3 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-hidden focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                    />
                  </div>
                </div>
              </div>

              {/* Category Selector with AI suggestion badge */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Tag className="w-3.5 h-3.5" />
                    <span>Suggested Category</span>
                  </span>
                  <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-normal">
                    AI chosen based on merchant & items
                  </span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {CATEGORIES.map((cat) => {
                    const config = CATEGORY_CONFIG[cat];
                    const isSelected = category === cat;
                    const Icon = config.icon;
                    return (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => setCategory(cat)}
                        className={`flex items-center gap-2 p-2 rounded-xl border text-xs font-medium transition cursor-pointer text-left ${
                          isSelected
                            ? 'border-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 font-semibold ring-1 ring-emerald-600'
                            : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 hover:border-slate-300'
                        }`}
                      >
                        <div
                          className={`p-1 rounded-lg ${
                            isSelected ? 'bg-emerald-600 text-white' : `${config.bg} ${config.color}`
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <span className="truncate">{cat}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Merchant & Description */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
                    <Store className="w-3.5 h-3.5" />
                    <span>Merchant / Entity</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={merchantName}
                    onChange={(e) => setMerchantName(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-hidden focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5" />
                    <span>Description</span>
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-hidden focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition"
                  />
                </div>
              </div>

              {/* Payment Mode */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
                  <CreditCard className="w-3.5 h-3.5" />
                  <span>Payment Mode</span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {PAYMENT_MODES.map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setPaymentMode(mode)}
                      className={`py-2 px-3 text-xs font-medium rounded-xl border transition cursor-pointer text-center ${
                        paymentMode === mode
                          ? 'border-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 font-semibold ring-1 ring-emerald-600'
                          : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 hover:border-slate-300'
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              {/* Multi-Item Invoices: Line Items section */}
              <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 p-3.5">
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setShowLineItems(!showLineItems)}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200 cursor-pointer"
                  >
                    <ListOrdered className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span>
                      Detected Line Items ({lineItems.length})
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={handleAddLineItem}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Item</span>
                  </button>
                </div>

                {showLineItems && (
                  <div className="mt-3 space-y-2">
                    {lineItems.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">
                        No distinct line items extracted. You can add them if you wish to track breakdown.
                      </p>
                    ) : (
                      lineItems.map((li, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <input
                            type="text"
                            placeholder="Item name"
                            value={li.item}
                            onChange={(e) => handleLineItemChange(idx, 'item', e.target.value)}
                            className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                          />
                          <div className="relative w-28">
                            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 text-xs">
                              ₹
                            </span>
                            <input
                              type="number"
                              step="any"
                              placeholder="0"
                              value={li.amount || ''}
                              onChange={(e) => handleLineItemChange(idx, 'amount', e.target.value)}
                              className="w-full pl-6 pr-2 py-1.5 text-xs font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            />
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveLineItem(idx)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 transition cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* Explicit Confirmation Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 text-xs font-semibold rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
                >
                  Discard
                </button>
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 px-6 py-2.5 text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition active:scale-98 cursor-pointer"
                >
                  <Check className="w-4 h-4" />
                  <span>Confirm & Save Transaction</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
