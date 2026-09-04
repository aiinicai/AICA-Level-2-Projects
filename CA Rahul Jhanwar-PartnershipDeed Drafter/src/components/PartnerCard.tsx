import React, { useState, useRef } from 'react';
import { 
  Trash2, 
  User, 
  UserCheck, 
  Percent, 
  Calendar, 
  MapPin, 
  CreditCard, 
  Upload, 
  FileText, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  Eye, 
  X, 
  RefreshCw,
  ShieldCheck,
  IdCard
} from 'lucide-react';
import { Partner } from '../types';
import { getOrdinal, calculateAge } from '../utils/deedEngine';
import { ocrIdCard } from '../utils/aiService';

interface PartnerCardProps {
  partner: Partner;
  index: number;
  totalPartners: number;
  onUpdate: (index: number, field: keyof Partner, value: any) => void;
  onRemove: (index: number) => void;
  onDobChange: (index: number, dobValue: string) => void;
  onBatchUpdate?: (index: number, updates: Partial<Partner>) => void;
  titlePrefix?: string;
  badgeText?: string;
  badgeTheme?: 'blue' | 'emerald' | 'amber';
  hideProfitShare?: boolean;
}

export const PartnerCard: React.FC<PartnerCardProps> = ({
  partner,
  index,
  totalPartners,
  onUpdate,
  onRemove,
  onDobChange,
  onBatchUpdate,
  titlePrefix,
  badgeText,
  badgeTheme = 'blue',
  hideProfitShare = false,
}) => {
  const [activeUploadSlot, setActiveUploadSlot] = useState<string | null>(null);
  const [isProcessingOcr, setIsProcessingOcr] = useState<boolean>(false);
  const [ocrMessage, setOcrMessage] = useState<string | null>(null);
  const [previewModalUrl, setPreviewModalUrl] = useState<{ title: string; url: string } | null>(null);

  const panFileInputRef = useRef<HTMLInputElement | null>(null);
  const aadhaarFrontInputRef = useRef<HTMLInputElement | null>(null);
  const aadhaarBackInputRef = useRef<HTMLInputElement | null>(null);

  // Client-side image compression to prevent payload limits and proxy timeouts
  const compressImageIfNeeded = (file: File): Promise<string> => {
    return new Promise((resolve) => {
      if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string || '');
        reader.onerror = () => resolve('');
        reader.readAsDataURL(file);
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const maxDim = 1280;
          let width = img.width;
          let height = img.height;

          if (width > maxDim || height > maxDim) {
            if (width > height) {
              height = Math.round((height * maxDim) / width);
              width = maxDim;
            } else {
              width = Math.round((width * maxDim) / height);
              height = maxDim;
            }
          }

          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.drawImage(img, 0, 0, width, height);
            const compressedUrl = canvas.toDataURL('image/jpeg', 0.85);
            resolve(compressedUrl);
          } else {
            resolve(e.target?.result as string || '');
          }
        };
        img.onerror = () => resolve(e.target?.result as string || '');
        img.src = e.target?.result as string;
      };
      reader.onerror = () => resolve('');
      reader.readAsDataURL(file);
    });
  };

  // Handle file selection and AI extraction
  const handleFileUpload = async (
    file: File, 
    docType: 'pan_front' | 'aadhaar_front' | 'aadhaar_back'
  ) => {
    try {
      if (!file) return;

      setIsProcessingOcr(true);
      setActiveUploadSlot(docType);
      const docLabel = docType === 'pan_front' 
        ? 'PAN Card' 
        : docType === 'aadhaar_front' 
        ? 'Aadhaar (Front)' 
        : 'Aadhaar (Back)';

      setOcrMessage(`Reading ${docLabel}...`);

      const dataUrl = await compressImageIfNeeded(file);
      if (!dataUrl) {
        setOcrMessage('Failed to read document file.');
        setIsProcessingOcr(false);
        setActiveUploadSlot(null);
        return;
      }

      // Immediately display attachment preview
      const initialUpdates: Partial<Partner> = {};
      if (docType === 'pan_front') {
        initialUpdates.panCardFrontUrl = dataUrl;
        initialUpdates.panCardFileName = file.name;
      } else if (docType === 'aadhaar_front') {
        initialUpdates.aadhaarCardFrontUrl = dataUrl;
        initialUpdates.aadhaarFrontFileName = file.name;
        if (file.name.toLowerCase().endsWith('.pdf')) {
          initialUpdates.aadhaarCardBackUrl = dataUrl;
          initialUpdates.aadhaarBackFileName = file.name;
        }
      } else if (docType === 'aadhaar_back') {
        initialUpdates.aadhaarCardBackUrl = dataUrl;
        initialUpdates.aadhaarBackFileName = file.name;
        if (file.name.toLowerCase().endsWith('.pdf')) {
          initialUpdates.aadhaarCardFrontUrl = dataUrl;
          initialUpdates.aadhaarFrontFileName = file.name;
        }
      }

      if (onBatchUpdate) {
        onBatchUpdate(index, initialUpdates);
      } else {
        if (docType === 'pan_front') {
          onUpdate(index, 'panCardFrontUrl', dataUrl);
          onUpdate(index, 'panCardFileName', file.name);
        } else if (docType === 'aadhaar_front') {
          onUpdate(index, 'aadhaarCardFrontUrl', dataUrl);
          onUpdate(index, 'aadhaarFrontFileName', file.name);
        } else if (docType === 'aadhaar_back') {
          onUpdate(index, 'aadhaarCardBackUrl', dataUrl);
          onUpdate(index, 'aadhaarBackFileName', file.name);
        }
      }

      setOcrMessage(`Scanning ${docLabel} with AI OCR...`);

      // Call client-side robust AI OCR
      const fileMime = file.type || (file.name.toLowerCase().endsWith('.pdf') ? 'application/pdf' : 'image/jpeg');
      const resData = await ocrIdCard(dataUrl, fileMime, docType);

      if (resData && resData.success && resData.extracted) {
        const ext = resData.extracted;
        const autoFilledFields: string[] = [];
        const updates: Partial<Partner> = {};

        // Always preserve attachment URLs
        if (docType === 'pan_front') {
          updates.panCardFrontUrl = dataUrl;
          updates.panCardFileName = file.name;
        } else if (docType === 'aadhaar_front') {
          updates.aadhaarCardFrontUrl = dataUrl;
          updates.aadhaarFrontFileName = file.name;
          // If this PDF / document contains address as well (e-Aadhaar or combined PDF), also fulfill back slot
          if (ext.address || ext.cardTypeDetected === 'aadhaar_both' || file.name.toLowerCase().endsWith('.pdf')) {
            updates.aadhaarCardBackUrl = dataUrl;
            updates.aadhaarBackFileName = file.name;
          }
        } else if (docType === 'aadhaar_back') {
          updates.aadhaarCardBackUrl = dataUrl;
          updates.aadhaarBackFileName = file.name;
          // If this PDF / document contains Aadhaar number as well, also fulfill front slot
          if (ext.aadhaar || ext.cardTypeDetected === 'aadhaar_both' || file.name.toLowerCase().endsWith('.pdf')) {
            updates.aadhaarCardFrontUrl = dataUrl;
            updates.aadhaarFrontFileName = file.name;
          }
        }

        // 1. Full Legal Name
        if (ext.name && ext.name.trim()) {
          updates.name = ext.name.trim().toUpperCase();
          autoFilledFields.push('Name');
        }

        // 2. Title Prefix
        if (ext.titlePrefix && ext.titlePrefix.trim()) {
          updates.titlePrefix = ext.titlePrefix.trim();
        }

        // 3. Father's / Husband's Name
        if (ext.parentName && ext.parentName.trim()) {
          updates.parentName = ext.parentName.trim().toUpperCase();
          autoFilledFields.push(ext.relationType === 'HUSBAND' ? "Husband's Name" : "Father's Name");
        }

        // 4. Relation Type
        if (ext.relationType) {
          updates.relationType = ext.relationType === 'HUSBAND' ? 'HUSBAND' : 'FATHER';
        }

        // 5. PAN Number
        if (ext.pan && ext.pan.trim()) {
          updates.pan = ext.pan.trim().toUpperCase();
          autoFilledFields.push('PAN');
        }

        // 6. Aadhaar Number
        if (ext.aadhaar && ext.aadhaar.trim()) {
          updates.aadhaar = ext.aadhaar.trim();
          autoFilledFields.push('Aadhaar');
        }

        // 7. Date of Birth & Calculated Age
        if (ext.dob && ext.dob.trim()) {
          updates.dob = ext.dob.trim();
          updates.age = ext.age || calculateAge(ext.dob.trim());
          autoFilledFields.push('DOB & Age');
        }

        // 8. Residential Address
        if (ext.address && ext.address.trim()) {
          updates.address = ext.address.trim().toUpperCase();
          autoFilledFields.push('Address');
        }

        const msg = autoFilledFields.length > 0
          ? `✓ Auto-filled ${autoFilledFields.join(', ')} from ${docLabel}`
          : `✓ ${docLabel} attached. (Details can also be typed manually below)`;

        updates.idOcrStatus = 'extracted';
        updates.idOcrMessage = msg;

        if (onBatchUpdate) {
          onBatchUpdate(index, updates);
        } else {
          // Fallback sequential update
          if (updates.name !== undefined) onUpdate(index, 'name', updates.name);
          if (updates.titlePrefix !== undefined) onUpdate(index, 'titlePrefix', updates.titlePrefix);
          if (updates.parentName !== undefined) onUpdate(index, 'parentName', updates.parentName);
          if (updates.relationType !== undefined) onUpdate(index, 'relationType', updates.relationType);
          if (updates.pan !== undefined) onUpdate(index, 'pan', updates.pan);
          if (updates.aadhaar !== undefined) onUpdate(index, 'aadhaar', updates.aadhaar);
          if (updates.dob !== undefined) {
            onDobChange(index, updates.dob);
          }
          if (updates.address !== undefined) onUpdate(index, 'address', updates.address);
          onUpdate(index, 'idOcrStatus', 'extracted');
          onUpdate(index, 'idOcrMessage', msg);
        }

        setOcrMessage(msg);
      } else {
        const msg = resData?.notice || `✓ ${docLabel} attached. You can type or verify details manually.`;
        setOcrMessage(msg);
        if (onBatchUpdate) {
          onBatchUpdate(index, { idOcrStatus: 'extracted', idOcrMessage: msg });
        } else {
          onUpdate(index, 'idOcrStatus', 'extracted');
          onUpdate(index, 'idOcrMessage', msg);
        }
      }
    } catch (err: any) {
      console.warn('OCR processing notice:', err?.message || err);
      const msg = '✓ Document attached. You can verify or edit details below.';
      setOcrMessage(msg);
      if (onBatchUpdate) {
        onBatchUpdate(index, { idOcrStatus: 'extracted', idOcrMessage: msg });
      } else {
        onUpdate(index, 'idOcrStatus', 'extracted');
      }
    } finally {
      setIsProcessingOcr(false);
      setActiveUploadSlot(null);
    }
  };

  const handleRemoveAttachment = (docType: 'pan_front' | 'aadhaar_front' | 'aadhaar_back') => {
    if (docType === 'pan_front') {
      onUpdate(index, 'panCardFrontUrl', undefined);
      onUpdate(index, 'panCardFileName', undefined);
    } else if (docType === 'aadhaar_front') {
      onUpdate(index, 'aadhaarCardFrontUrl', undefined);
      onUpdate(index, 'aadhaarFrontFileName', undefined);
    } else if (docType === 'aadhaar_back') {
      onUpdate(index, 'aadhaarCardBackUrl', undefined);
      onUpdate(index, 'aadhaarBackFileName', undefined);
    }
    setOcrMessage(null);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs transition hover:border-slate-300 mb-4 relative">
      
      {/* Card Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-4 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className={`w-6 h-6 rounded-md font-bold text-xs flex items-center justify-center border ${
            badgeTheme === 'emerald'
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-blue-50 text-blue-700 border-blue-200'
          }`}>
            #{index + 1}
          </div>
          <div>
            <div className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-2">
              <span>
                {titlePrefix ? `${titlePrefix} #${index + 1}` : `Partner #${index + 1} • Party of the ${getOrdinal(index + 1)} Part`}
              </span>
              {badgeText && (
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                  badgeTheme === 'emerald'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : 'bg-blue-100 text-blue-800 border-blue-300'
                }`}>
                  {badgeText}
                </span>
              )}
              {(partner.panCardFrontUrl || partner.aadhaarCardFrontUrl || partner.aadhaarCardBackUrl) && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  <ShieldCheck className="w-3 h-3 text-emerald-600" />
                  KYC Attached
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-500">
              {partner.isWorking ? 'Active Working Partner (Eligible for Sec 35(e) Remuneration)' : 'Sleeping / Financing Partner'}
            </div>
          </div>
        </div>

        {(totalPartners > 2 || titlePrefix) && (
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="flex items-center gap-1 text-xs text-rose-600 hover:text-rose-800 hover:bg-rose-50 px-2.5 py-1 rounded-lg transition border border-rose-200 font-medium"
            title={`Remove ${titlePrefix || 'Partner'}`}
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Remove</span>
          </button>
        )}
      </div>

      {/* KYC ATTACHMENT SECTION (Optional Auto-fill from PAN & Aadhaar) */}
      <div className="mb-5 bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-slate-50 p-4 rounded-xl border border-blue-200/80 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-blue-600 text-white shadow-xs">
              <IdCard className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wide block">
                Attach PAN Card & Aadhaar Card (Optional AI Auto-Fill & Notary Print)
              </span>
              <span className="text-[11px] text-slate-600">
                Upload images/PDFs. Details (Name, Father's Name, PAN, DOB & Address from Aadhaar back) will auto-fill automatically.
              </span>
            </div>
          </div>

          {isProcessingOcr && (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-600 text-white text-[11px] font-semibold animate-pulse">
              <RefreshCw className="w-3 h-3 animate-spin" />
              <span>Scanning with AI...</span>
            </div>
          )}
        </div>

        {ocrMessage && (
          <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 animate-in fade-in duration-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="truncate">{ocrMessage}</span>
          </div>
        )}

        {/* 3 KYC Upload Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
          
          {/* 1. PAN Card (Front) */}
          <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs hover:border-blue-300 transition flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-bold text-slate-800 uppercase flex items-center gap-1">
                  <CreditCard className="w-3.5 h-3.5 text-blue-600" />
                  PAN Card (Front)
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                  Name & Father's Name
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mb-2">
                Auto-fills Partner Name, Father's Name, PAN No & Date of Birth.
              </p>
            </div>

            {partner.panCardFrontUrl ? (
              <div className="flex items-center justify-between gap-2 p-2 bg-slate-50 rounded-md border border-slate-200">
                <div className="flex items-center gap-2 min-w-0">
                  {partner.panCardFrontUrl.startsWith('data:image') ? (
                    <img 
                      src={partner.panCardFrontUrl} 
                      alt="PAN Card" 
                      className="w-8 h-8 rounded object-cover border border-slate-300 shrink-0"
                    />
                  ) : (
                    <FileText className="w-6 h-6 text-blue-600 shrink-0" />
                  )}
                  <span className="text-[11px] font-medium text-slate-700 truncate">
                    {partner.panCardFileName || 'PAN_Card_Front.jpg'}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => setPreviewModalUrl({ title: 'PAN Card (Front)', url: partner.panCardFrontUrl! })}
                    className="p-1 text-slate-600 hover:text-blue-600 hover:bg-slate-200 rounded"
                    title="View Document"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemoveAttachment('pan_front')}
                    className="p-1 text-rose-600 hover:bg-rose-50 rounded"
                    title="Remove Attachment"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <input
                  type="file"
                  ref={panFileInputRef}
                  accept="image/*,application/pdf"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFileUpload(file, 'pan_front');
                    e.target.value = '';
                  }}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => panFileInputRef.current?.click()}
                  disabled={isProcessingOcr}
                  className="w-full flex items-center justify-center gap-2 py-2 px-3 border border-dashed border-blue-300 rounded-lg bg-blue-50/50 hover:bg-blue-100/60 text-blue-700 text-xs font-semibold transition disabled:opacity-60"
                >
                  {isProcessingOcr && activeUploadSlot === 'pan_front' ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-600" />
                  ) : (
                    <Upload className="w-3.5 h-3.5" />
                  )}
                  <span>{isProcessingOcr && activeUploadSlot === 'pan_front' ? 'Reading PAN...' : 'Upload PAN Front'}</span>
                </button>
              </div>
            )}
          </div>

          {/* 2. Aadhaar Card (Front) */}
          <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs hover:border-blue-300 transition flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-bold text-slate-800 uppercase flex items-center gap-1">
                  <IdCard className="w-3.5 h-3.5 text-indigo-600" />
                  Aadhaar (Front)
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-800 border border-indigo-200 font-semibold">
                  Photo & Aadhaar No
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mb-2">
                Auto-fills 12-digit Aadhaar Number, Full Name & DOB.
              </p>
            </div>

            {partner.aadhaarCardFrontUrl ? (
              <div className="flex items-center justify-between gap-2 p-2 bg-slate-50 rounded-md border border-slate-200">
                <div className="flex items-center gap-2 min-w-0">
                  {partner.aadhaarCardFrontUrl.startsWith('data:image') ? (
                    <img 
                      src={partner.aadhaarCardFrontUrl} 
                      alt="Aadhaar Front" 
                      className="w-8 h-8 rounded object-cover border border-slate-300 shrink-0"
                    />
                  ) : (
                    <FileText className="w-6 h-6 text-indigo-600 shrink-0" />
                  )}
                  <span className="text-[11px] font-medium text-slate-700 truncate">
                    {partner.aadhaarFrontFileName || 'Aadhaar_Front.jpg'}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => setPreviewModalUrl({ title: 'Aadhaar Card (Front)', url: partner.aadhaarCardFrontUrl! })}
                    className="p-1 text-slate-600 hover:text-indigo-600 hover:bg-slate-200 rounded"
                    title="View Document"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemoveAttachment('aadhaar_front')}
                    className="p-1 text-rose-600 hover:bg-rose-50 rounded"
                    title="Remove Attachment"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <input
                  type="file"
                  ref={aadhaarFrontInputRef}
                  accept="image/*,application/pdf"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFileUpload(file, 'aadhaar_front');
                    e.target.value = '';
                  }}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => aadhaarFrontInputRef.current?.click()}
                  disabled={isProcessingOcr}
                  className="w-full flex items-center justify-center gap-2 py-2 px-3 border border-dashed border-indigo-300 rounded-lg bg-indigo-50/50 hover:bg-indigo-100/60 text-indigo-700 text-xs font-semibold transition disabled:opacity-60"
                >
                  {isProcessingOcr && activeUploadSlot === 'aadhaar_front' ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                  ) : (
                    <Upload className="w-3.5 h-3.5" />
                  )}
                  <span>{isProcessingOcr && activeUploadSlot === 'aadhaar_front' ? 'Reading Aadhaar Front...' : 'Upload Aadhaar Front'}</span>
                </button>
              </div>
            )}
          </div>

          {/* 3. Aadhaar Card (Back - Address) */}
          <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-2xs hover:border-blue-300 transition flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-bold text-slate-800 uppercase flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-emerald-600" />
                  Aadhaar (Back Side)
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
                  Residential Address
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mb-2">
                Auto-fills Complete Address, C/O Parent/Spouse & PIN code.
              </p>
            </div>

            {partner.aadhaarCardBackUrl ? (
              <div className="flex items-center justify-between gap-2 p-2 bg-slate-50 rounded-md border border-slate-200">
                <div className="flex items-center gap-2 min-w-0">
                  {partner.aadhaarCardBackUrl.startsWith('data:image') ? (
                    <img 
                      src={partner.aadhaarCardBackUrl} 
                      alt="Aadhaar Back" 
                      className="w-8 h-8 rounded object-cover border border-slate-300 shrink-0"
                    />
                  ) : (
                    <FileText className="w-6 h-6 text-emerald-600 shrink-0" />
                  )}
                  <span className="text-[11px] font-medium text-slate-700 truncate">
                    {partner.aadhaarBackFileName || 'Aadhaar_Back.jpg'}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => setPreviewModalUrl({ title: 'Aadhaar Card (Back)', url: partner.aadhaarCardBackUrl! })}
                    className="p-1 text-slate-600 hover:text-emerald-600 hover:bg-slate-200 rounded"
                    title="View Document"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemoveAttachment('aadhaar_back')}
                    className="p-1 text-rose-600 hover:bg-rose-50 rounded"
                    title="Remove Attachment"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <input
                  type="file"
                  ref={aadhaarBackInputRef}
                  accept="image/*,application/pdf"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFileUpload(file, 'aadhaar_back');
                    e.target.value = '';
                  }}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => aadhaarBackInputRef.current?.click()}
                  disabled={isProcessingOcr}
                  className="w-full flex items-center justify-center gap-2 py-2 px-3 border border-dashed border-emerald-300 rounded-lg bg-emerald-50/50 hover:bg-emerald-100/60 text-emerald-700 text-xs font-semibold transition disabled:opacity-60"
                >
                  {isProcessingOcr && activeUploadSlot === 'aadhaar_back' ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                  ) : (
                    <Upload className="w-3.5 h-3.5" />
                  )}
                  <span>{isProcessingOcr && activeUploadSlot === 'aadhaar_back' ? 'Reading Aadhaar Back...' : 'Upload Aadhaar Back'}</span>
                </button>
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Inputs Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
        
        {/* Prefix & Full Name */}
        <div className="space-y-1 sm:col-span-2">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
            <User className="w-3 h-3 text-slate-400" />
            Prefix & Full Legal Name
          </label>
          <div className="flex gap-2">
            <select
              value={partner.titlePrefix ?? 'MR.'}
              onChange={(e) => onUpdate(index, 'titlePrefix', e.target.value)}
              className="w-28 px-2.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-semibold focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow text-xs shrink-0"
            >
              <option value="MR.">Mr.</option>
              <option value="MRS.">Mrs.</option>
              <option value="MISS">Miss</option>
              <option value="SMT.">Smt.</option>
              <option value="DR.">Dr.</option>
              <option value="">(None)</option>
            </select>
            <input
              type="text"
              value={partner.name}
              onChange={(e) => onUpdate(index, 'name', e.target.value.toUpperCase())}
              placeholder="E.G. PRAMESH JASVANTLAL SANGHVI"
              className="flex-1 px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow uppercase text-xs"
            />
          </div>
        </div>

        {/* Relation Type */}
        <div className="space-y-1">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider">
            Relation Title
          </label>
          <select
            value={partner.relationType}
            onChange={(e) => onUpdate(index, 'relationType', e.target.value)}
            className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow text-xs"
          >
            <option value="FATHER">Son / Daughter of (Father)</option>
            <option value="HUSBAND">Wife of (Husband)</option>
          </select>
        </div>

        {/* Parent / Spouse Name */}
        <div className="space-y-1">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider">
            Father's / Husband's Name
          </label>
          <input
            type="text"
            value={partner.parentName}
            onChange={(e) => onUpdate(index, 'parentName', e.target.value.toUpperCase())}
            placeholder="E.G. JASVANTLAL SANGHVI"
            className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow uppercase text-xs"
          />
        </div>

        {/* PAN No */}
        <div className="space-y-1">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
            <CreditCard className="w-3 h-3 text-slate-400" />
            PAN Number
          </label>
          <input
            type="text"
            maxLength={10}
            value={partner.pan}
            onChange={(e) => onUpdate(index, 'pan', e.target.value.toUpperCase())}
            placeholder="ABCDE1234F / APPLIED FOR"
            className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-mono tracking-wider focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow uppercase text-xs"
          />
        </div>

        {/* Aadhaar No */}
        <div className="space-y-1">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
            <IdCard className="w-3 h-3 text-slate-400" />
            Aadhaar Number (Optional)
          </label>
          <input
            type="text"
            maxLength={14}
            value={partner.aadhaar || ''}
            onChange={(e) => onUpdate(index, 'aadhaar', e.target.value.toUpperCase())}
            placeholder="XXXX XXXX XXXX"
            className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-mono tracking-wider focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow uppercase text-xs"
          />
        </div>

        {/* DOB */}
        <div className="space-y-1">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
            <Calendar className="w-3 h-3 text-slate-400" />
            Date of Birth (DOB)
          </label>
          <input
            type="date"
            value={partner.dob}
            onChange={(e) => onDobChange(index, e.target.value)}
            className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow text-xs"
          />
        </div>

        {/* Age (Auto-calculated) */}
        <div className={`space-y-1 ${hideProfitShare ? 'sm:col-span-1 lg:col-span-2' : ''}`}>
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider">
            Calculated Age (Yrs)
          </label>
          <input
            type="text"
            value={partner.age ? `${partner.age} YEARS` : ''}
            readOnly
            placeholder="Auto-calculated"
            className="w-full px-3.5 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 font-semibold text-xs cursor-not-allowed"
          />
        </div>

        {/* Profit / Loss Share % */}
        {!hideProfitShare && (
          <div className="space-y-1 sm:col-span-2 lg:col-span-1">
            <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
              <Percent className="w-3 h-3 text-slate-400" />
              Profit Share (%)
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              value={partner.profitShare}
              onChange={(e) => onUpdate(index, 'profitShare', e.target.value)}
              placeholder="50"
              className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 font-bold focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow text-xs"
            />
          </div>
        )}

        {/* Working Status */}
        <div className="space-y-1 sm:col-span-2 lg:col-span-4">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
            <UserCheck className="w-3 h-3 text-slate-400" />
            Working Status & Remuneration Eligibility
          </label>
          <div className="flex flex-wrap items-center gap-4 bg-slate-50 p-3 rounded-lg border border-slate-200">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name={`working_status_${partner.id}`}
                checked={partner.isWorking === true}
                onChange={() => onUpdate(index, 'isWorking', true)}
                className="w-4 h-4 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-xs font-semibold text-slate-900">
                Working Partner (Eligible for Remuneration under Sec 35(e))
              </span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name={`working_status_${partner.id}`}
                checked={partner.isWorking === false}
                onChange={() => onUpdate(index, 'isWorking', false)}
                className="w-4 h-4 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-xs text-slate-600">
                Sleeping / Financing Partner
              </span>
            </label>

            {partner.isWorking && (
              <div className="w-full mt-2 pt-2.5 border-t border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                  <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <span>💵</span> Fixed Salary / Remuneration (Optional):
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    Agar is partner ki fixed salary hai toh daalein (e.g. 50000 for Rs. 50,000/month). Agar profit ratio se leni ho toh blank chhod dein.
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-700">Rs.</span>
                  <input
                    type="text"
                    value={partner.salaryMonthly || ''}
                    onChange={(e) => {
                      const val = e.target.value.replace(/[^0-9]/g, '');
                      onUpdate(index, 'salaryMonthly', val);
                      if (val) {
                        const annual = (parseInt(val, 10) * 12).toString();
                        onUpdate(index, 'salaryAnnual', annual);
                      } else {
                        onUpdate(index, 'salaryAnnual', '');
                      }
                    }}
                    placeholder="e.g. 50000"
                    className="w-32 px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-bold text-slate-900 focus:ring-2 focus:ring-blue-500 outline-none text-right shadow-2xs"
                  />
                  <span className="text-xs font-medium text-slate-500">/ month</span>
                  {partner.salaryMonthly && parseInt(partner.salaryMonthly, 10) > 0 && (
                    <span className="text-[11px] font-bold text-emerald-800 bg-emerald-100 px-2 py-1 rounded border border-emerald-300 shrink-0">
                      = Rs. {(parseInt(partner.salaryMonthly, 10) * 12).toLocaleString('en-IN')}/- p.a.
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Full Residential Address */}
        <div className="space-y-1 sm:col-span-2 lg:col-span-4">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider flex items-center gap-1">
            <MapPin className="w-3 h-3 text-slate-400" />
            Residential Address (as per Aadhaar / Passport / KYC)
          </label>
          <textarea
            rows={2}
            value={partner.address}
            onChange={(e) => onUpdate(index, 'address', e.target.value.toUpperCase())}
            placeholder="FLAT / HOUSE NO, APARTMENT / ROAD, LANDMARK, CITY, STATE - PINCODE"
            className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow uppercase text-xs"
          />
        </div>

      </div>

      {/* Document Zoom / Preview Modal */}
      {previewModalUrl && (
        <div className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-5 shadow-2xl space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                <IdCard className="w-4 h-4 text-blue-600" />
                <span>{previewModalUrl.title} — Partner #{index + 1} ({partner.name || 'Partner'})</span>
              </h3>
              <button
                type="button"
                onClick={() => setPreviewModalUrl(null)}
                className="p-1 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-auto flex items-center justify-center bg-slate-100 rounded-xl p-3">
              {previewModalUrl.url.startsWith('data:image') ? (
                <img 
                  src={previewModalUrl.url} 
                  alt={previewModalUrl.title} 
                  className="max-h-[70vh] object-contain rounded-lg border border-slate-300 shadow-sm"
                />
              ) : (
                <iframe 
                  src={previewModalUrl.url} 
                  title={previewModalUrl.title} 
                  className="w-full h-[65vh] rounded-lg border border-slate-300"
                />
              )}
            </div>
            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setPreviewModalUrl(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-lg"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

