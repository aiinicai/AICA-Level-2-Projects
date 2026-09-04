import React, { useState, useRef } from 'react';
import { 
  Upload, 
  FileText, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  RotateCcw, 
  FileCheck2,
  Calendar,
  Check,
  Plus,
  Trash2,
  Edit2,
  Clock,
  History,
  FileSpreadsheet
} from 'lucide-react';
import { PriorDeedRecord } from '../types';
import { extractDeedFromDocument } from '../utils/aiService';
import { getOrdinal } from '../utils/deedEngine';

interface DeedUploaderOCRCardProps {
  onDeedExtracted: (extractedData: any, fileName: string) => void;
  currentFileName?: string;
  formatType: 'supplementary' | 'dissolution';
  priorDeeds?: PriorDeedRecord[];
  onUpdatePriorDeeds?: (deeds: PriorDeedRecord[]) => void;
}

export const DeedUploaderOCRCard: React.FC<DeedUploaderOCRCardProps> = ({
  onDeedExtracted,
  currentFileName,
  formatType,
  priorDeeds = [],
  onUpdatePriorDeeds
}) => {
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractionProgress, setExtractionProgress] = useState<string>('');
  const [extractionResult, setExtractionResult] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [showManualAdd, setShowManualAdd] = useState<boolean>(false);
  const [editingDeedId, setEditingDeedId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Manual deed entry form state
  const [manualForm, setManualForm] = useState<Partial<PriorDeedRecord>>({
    deedType: 'supplementary',
    deedLabel: '',
    executionDate: '',
    effectiveDate: '',
    executionCity: '',
    rofRegistrationNumber: '',
    keyChangesSummary: ''
  });

  const processFile = async (file: File) => {
    if (!file) return;

    // Check if Chrome download was incomplete (.crdownload)
    if (file.name.toLowerCase().endsWith('.crdownload')) {
      setErrorMessage('This file is still downloading in Google Chrome (.crdownload). Please wait for the download to finish (100%), or rename the file to remove .crdownload.');
      return;
    }

    // Validate type (PDF or Image)
    const isValidType = file.type === 'application/pdf' || 
      file.type.startsWith('image/') || 
      file.name.toLowerCase().endsWith('.pdf') ||
      file.name.toLowerCase().endsWith('.jpg') ||
      file.name.toLowerCase().endsWith('.jpeg') ||
      file.name.toLowerCase().endsWith('.png');

    if (!isValidType) {
      setErrorMessage('Please upload a valid PDF document or scanned image (JPG/PNG).');
      return;
    }

    // Check size limit: max 100MB
    if (file.size > 100 * 1024 * 1024) {
      setErrorMessage('Document file size exceeds 100MB limit. Please provide an optimized scanned copy.');
      return;
    }

    setIsExtracting(true);
    setExtractionProgress("Reading " + file.name + "...");
    setErrorMessage(null);

    try {
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve, reject) => {
        reader.onload = () => resolve(reader.result as string || '');
        reader.onerror = () => reject(new Error('Failed to read file'));
      });
      reader.readAsDataURL(file);

      const dataUrl = await base64Promise;
      setExtractionProgress("AI Extracting particulars & legal recitals from " + file.name + "...");

      const fileMime = file.type || (file.name.toLowerCase().endsWith('.pdf') ? 'application/pdf' : 'image/jpeg');
      const json = await extractDeedFromDocument(dataUrl, fileMime, file.name);

      if (!json.success || !json.extracted) {
        throw new Error(json.error || 'Could not extract deed information from the uploaded file.');
      }

      setExtractionResult(json.extracted);
      onDeedExtracted(json.extracted, file.name);

      // Construct a new PriorDeedRecord and append to priorDeeds if handler is provided
      if (onUpdatePriorDeeds) {
        const ext = json.extracted;
        const currentCount = priorDeeds.length;
        const isOriginal = currentCount === 0 || ext.deedType === 'original';

        const newRecord: PriorDeedRecord = {
          id: 'deed_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
          deedType: isOriginal ? 'original' : 'supplementary',
          deedLabel: ext.deedLabel || (isOriginal ? 'Original Partnership Deed' : (getOrdinal(currentCount) + ' Supplementary Deed')),
          executionDate: ext.principalDeedDate || ext.executionDate || '',
          effectiveDate: ext.effectiveDate || ext.principalDeedDate || '',
          executionCity: ext.executionPlace || '',
          rofRegistrationNumber: ext.rofRegistrationNumber || '',
          keyChangesSummary: ext.keyChangesSummary || (ext.amendmentPoints && ext.amendmentPoints.length > 0 ? ext.amendmentPoints.join(', ') : (isOriginal ? 'Initial constitution of partnership' : 'Reconstitution and amendment of covenants')),
          fileName: file.name
        };

        let updatedDeeds = [...priorDeeds, newRecord];

        // If this uploaded deed recited prior deeds internally, also incorporate them
        if (Array.isArray(ext.priorDeedsRecited) && ext.priorDeedsRecited.length > 0) {
          ext.priorDeedsRecited.forEach((r: any, idx: number) => {
            const alreadyExists = updatedDeeds.some(d => d.executionDate && d.executionDate === r.executionDate);
            if (!alreadyExists && r.executionDate) {
              updatedDeeds.unshift({
                id: 'deed_recited_' + Date.now() + '_' + idx,
                deedType: idx === 0 ? 'original' : 'supplementary',
                deedLabel: r.deedLabel || (idx === 0 ? 'Original Partnership Deed' : 'Prior Supplementary Deed'),
                executionDate: r.executionDate,
                effectiveDate: r.effectiveDate || r.executionDate,
                rofRegistrationNumber: r.rofRegistrationNumber || '',
                keyChangesSummary: r.keyChangesSummary || 'Earlier constitutional modification',
                fileName: 'Recited in ' + file.name
              });
            }
          });
        }

        // Sort deeds chronologically by execution date if available
        updatedDeeds.sort((a, b) => {
          if (!a.executionDate) return 1;
          if (!b.executionDate) return -1;
          return a.executionDate.localeCompare(b.executionDate);
        });

        onUpdatePriorDeeds(updatedDeeds);
      }
    } catch (err: any) {
      console.error('Extraction error:', err);
      setErrorMessage(err.message || 'Failed to process and OCR deed. Please verify the document clarity.');
    } finally {
      setIsExtracting(false);
      setExtractionProgress('');
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files) as File[];
      for (const file of filesArray) {
        await processFile(file);
      }
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files) as File[];
      for (const file of filesArray) {
        await processFile(file);
      }
    }
  };

  // Add / Save manual deed record
  const handleSaveManualDeed = () => {
    if (!manualForm.executionDate) {
      alert('Please specify the Deed Execution Date.');
      return;
    }

    if (!onUpdatePriorDeeds) return;

    if (editingDeedId) {
      const updated = priorDeeds.map(d => d.id === editingDeedId ? { ...d, ...manualForm } as PriorDeedRecord : d);
      onUpdatePriorDeeds(updated);
      setEditingDeedId(null);
    } else {
      const count = priorDeeds.length;
      const isOriginal = count === 0 || manualForm.deedType === 'original';
      const newRecord: PriorDeedRecord = {
        id: 'deed_' + Date.now(),
        deedType: manualForm.deedType || (isOriginal ? 'original' : 'supplementary'),
        deedLabel: manualForm.deedLabel?.trim() || (isOriginal ? 'Original Partnership Deed' : (getOrdinal(count) + ' Supplementary Deed')),
        executionDate: manualForm.executionDate || '',
        effectiveDate: manualForm.effectiveDate || manualForm.executionDate || '',
        executionCity: manualForm.executionCity || '',
        rofRegistrationNumber: manualForm.rofRegistrationNumber || '',
        keyChangesSummary: manualForm.keyChangesSummary || (isOriginal ? 'Initial constitution of partnership' : 'Reconstitution and amendment of terms'),
        fileName: 'Manually Entered'
      };

      const updated = [...priorDeeds, newRecord];
      updated.sort((a, b) => (a.executionDate || '').localeCompare(b.executionDate || ''));
      onUpdatePriorDeeds(updated);
    }

    setManualForm({
      deedType: 'supplementary',
      deedLabel: '',
      executionDate: '',
      effectiveDate: '',
      executionCity: '',
      rofRegistrationNumber: '',
      keyChangesSummary: ''
    });
    setShowManualAdd(false);
  };

  const handleEditDeed = (deed: PriorDeedRecord) => {
    setManualForm({ ...deed });
    setEditingDeedId(deed.id);
    setShowManualAdd(true);
  };

  const handleDeleteDeed = (deedId: string) => {
    if (!onUpdatePriorDeeds) return;
    if (window.confirm('Are you sure you want to remove this deed from the historical chain?')) {
      onUpdatePriorDeeds(priorDeeds.filter(d => d.id !== deedId));
    }
  };

  const titleText = formatType === 'supplementary' 
    ? 'Upload Previous Partnership Deeds (Batch Upload & AI Chain Extraction)' 
    : 'Upload Previous Deeds of Partnership (For Dissolution Recitals)';

  const subText = formatType === 'supplementary'
    ? 'Upload all previous deeds (Original Deed, 1st Supplementary, 2nd Supplementary, etc.). The AI automatically extracts dates, registration details, and amendments to recite the complete unbroken chain of title in the Supplementary Deed.'
    : 'Upload all previous deeds to automatically construct the complete historical chain of deeds leading up to the final Dissolution Deed.';

  return (
    <div className="bg-gradient-to-br from-blue-50/70 via-indigo-50/40 to-slate-50 border border-blue-200/80 rounded-2xl p-5 mb-6 shadow-xs">
      
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs shrink-0">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
              <span>{titleText}</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">
                Multi-Deed AI OCR
              </span>
            </h3>
            <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
              {subText}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setEditingDeedId(null);
              setManualForm({
                deedType: priorDeeds.length === 0 ? 'original' : 'supplementary',
                deedLabel: priorDeeds.length === 0 ? 'Original Partnership Deed' : (getOrdinal(priorDeeds.length) + ' Supplementary Deed'),
                executionDate: '',
                effectiveDate: '',
                executionCity: '',
                rofRegistrationNumber: '',
                keyChangesSummary: ''
              });
              setShowManualAdd(!showManualAdd);
            }}
            className="flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900 px-2.5 py-1.5 rounded-lg border border-blue-200 bg-white hover:bg-blue-50 transition shrink-0 font-medium"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Deed Manually</span>
          </button>

          {extractionResult && (
            <button
              type="button"
              onClick={() => {
                setExtractionResult(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
              }}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition shrink-0"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Upload Another</span>
            </button>
          )}
        </div>
      </div>

      {/* Hidden Multi-File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,image/png,image/jpeg,image/webp"
        onChange={handleFileChange}
        multiple
        className="hidden"
      />

      {/* Drag & Drop Upload Zone */}
      {!isExtracting && (
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all duration-200 ${
            isDragOver 
              ? 'border-blue-500 bg-blue-100/50 scale-[0.99]' 
              : 'border-blue-300 hover:border-blue-500 bg-white/80 hover:bg-white'
          }`}
        >
          <div className="w-11 h-11 mx-auto rounded-full bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center mb-2.5">
            <Upload className="w-5 h-5" />
          </div>
          <div className="font-semibold text-sm text-slate-800">
            Click to upload or drag & drop ALL previous Partnership Deed PDFs (Single or Multiple)
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Upload Original Deed, 1st Supplementary, 2nd Supplementary, etc. AI will extract all dates & chronological changes.
          </p>
        </div>
      )}

      {/* Extracting State Indicator */}
      {isExtracting && (
        <div className="border border-blue-200 bg-white rounded-xl p-6 text-center shadow-2xs">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-3" />
          <div className="text-sm font-bold text-slate-900">
            {extractionProgress || 'Extracting Partnership Deed via AI OCR...'}
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Analyzing document text, identifying deed dates, registration particulars, all partner details, and historical amendment covenants...
          </p>
        </div>
      )}

      {/* Error Banner */}
      {errorMessage && (
        <div className="mt-3 bg-red-50 border border-red-200 rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-red-800">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold">Extraction Notice: </span>
            {errorMessage}
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="font-bold underline text-red-700 hover:text-red-900 shrink-0 ml-2"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Manual Add / Edit Deed Modal Form */}
      {showManualAdd && (
        <div className="mt-4 p-4 rounded-xl border border-blue-300 bg-white shadow-sm animate-fadeIn">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 flex items-center gap-1.5">
              <History className="w-4 h-4 text-blue-600" />
              <span>{editingDeedId ? 'Edit Recorded Prior Deed' : 'Add Prior Deed to Historical Chain'}</span>
            </h4>
            <button
              type="button"
              onClick={() => { setShowManualAdd(false); setEditingDeedId(null); }}
              className="text-xs text-slate-400 hover:text-slate-600 font-bold"
            >
              ✕ Cancel
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Deed Classification</label>
              <select
                value={manualForm.deedType || 'supplementary'}
                onChange={(e) => setManualForm({ ...manualForm, deedType: e.target.value as any })}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white font-medium"
              >
                <option value="original">Original Partnership Deed</option>
                <option value="supplementary">Supplementary / Amendment Deed</option>
                <option value="reconstitution">Deed of Reconstitution</option>
              </select>
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Deed Title / Label</label>
              <input
                type="text"
                value={manualForm.deedLabel || ''}
                onChange={(e) => setManualForm({ ...manualForm, deedLabel: e.target.value })}
                placeholder="e.g. 1st Supplementary Deed"
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Execution Date *</label>
              <input
                type="date"
                value={manualForm.executionDate || ''}
                onChange={(e) => setManualForm({ ...manualForm, executionDate: e.target.value })}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Execution Place / City</label>
              <input
                type="text"
                value={manualForm.executionCity || ''}
                onChange={(e) => setManualForm({ ...manualForm, executionCity: e.target.value })}
                placeholder="e.g. Surat, Gujarat"
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">RoF Registration / Diary No.</label>
              <input
                type="text"
                value={manualForm.rofRegistrationNumber || ''}
                onChange={(e) => setManualForm({ ...manualForm, rofRegistrationNumber: e.target.value })}
                placeholder="e.g. GUJ/SRT/12345/2018 (or Unregistered)"
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Effective Date (Optional)</label>
              <input
                type="date"
                value={manualForm.effectiveDate || ''}
                onChange={(e) => setManualForm({ ...manualForm, effectiveDate: e.target.value })}
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
              />
            </div>

            <div className="sm:col-span-2 md:col-span-3">
              <label className="block font-medium text-slate-700 mb-1">Key Changes & Amendments in this Deed *</label>
              <input
                type="text"
                value={manualForm.keyChangesSummary || ''}
                onChange={(e) => setManualForm({ ...manualForm, keyChangesSummary: e.target.value })}
                placeholder="e.g. Admission of Partner Mr. Ramesh Patel and revision of profit sharing ratio to 33.33% each"
                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white"
              />
            </div>
          </div>

          <div className="mt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => { setShowManualAdd(false); setEditingDeedId(null); }}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSaveManualDeed}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs"
            >
              {editingDeedId ? 'Update Deed' : 'Save to Historical Chain'}
            </button>
          </div>
        </div>
      )}

      {/* Chronological Deeds Timeline Card */}
      {priorDeeds.length > 0 && (
        <div className="mt-4 border border-blue-200 bg-white rounded-xl p-4 shadow-2xs">
          <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Chronological Chain of Recorded Deeds ({priorDeeds.length})
              </h4>
            </div>
            <span className="text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              ✓ Sequentially Recited in "WHEREAS" Clauses
            </span>
          </div>

          <div className="space-y-2.5">
            {priorDeeds.map((deed, index) => (
              <div 
                key={deed.id || index}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-blue-300 bg-slate-50/50 hover:bg-blue-50/30 transition text-xs gap-2"
              >
                <div className="flex items-start gap-2.5">
                  <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center shrink-0 text-[11px] mt-0.5">
                    {index + 1}
                  </div>
                  <div>
                    <div className="font-bold text-slate-900 flex items-center gap-2 flex-wrap">
                      <span>{deed.deedLabel || (deed.deedType === 'original' ? 'Original Deed' : `${getOrdinal(index + 1)} Deed`)}</span>
                      {deed.executionDate && (
                        <span className="text-slate-600 font-semibold bg-white px-2 py-0.5 rounded border border-slate-200">
                          📅 {deed.executionDate}
                        </span>
                      )}
                      {deed.rofRegistrationNumber && (
                        <span className="text-indigo-700 font-medium bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200 text-[10px]">
                          RoF: {deed.rofRegistrationNumber}
                        </span>
                      )}
                      {deed.executionCity && (
                        <span className="text-slate-500">
                          at {deed.executionCity}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-600 mt-1 leading-snug">
                      <span className="font-semibold text-slate-700">Particulars: </span>
                      {deed.keyChangesSummary || 'Constitutional amendment and alteration'}
                    </p>
                    {deed.fileName && (
                      <span className="text-[10px] text-slate-400 mt-0.5 block">
                        Source: {deed.fileName}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 self-end sm:self-center shrink-0">
                  <button
                    type="button"
                    onClick={() => handleEditDeed(deed)}
                    className="p-1.5 rounded hover:bg-slate-200 text-slate-600 transition"
                    title="Edit particulars"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteDeed(deed.id)}
                    className="p-1.5 rounded hover:bg-red-100 text-red-600 transition"
                    title="Remove deed"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-3 text-[11px] text-slate-500 italic bg-blue-50/50 p-2 rounded border border-blue-100">
            ℹ️ <b>Legal Conveyancing Note:</b> Under Indian conveyancing principles and Registrar of Firms (RoF) guidelines, each previous deed listed above will be formally recited in chronological sequence in the <b>"WHEREAS"</b> recitals and on the <b>Cover Page</b> of the Supplementary Deed / Dissolution Deed.
          </div>
        </div>
      )}

      {/* Extracted Details Confirmation Banner */}
      {extractionResult && (
        <div className="mt-4 border border-emerald-300 bg-white rounded-xl p-4 shadow-2xs animate-fadeIn">
          <div className="flex items-center gap-2 text-emerald-800 font-bold text-xs mb-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Successfully Extracted Deed Details via AI</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-slate-500 block text-[10px]">FIRM NAME</span>
              <span className="font-bold text-slate-900 truncate block">
                {extractionResult.firmName || '—'}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-slate-500 block text-[10px]">DEED DATE</span>
              <span className="font-bold text-slate-900">
                {extractionResult.principalDeedDate || extractionResult.executionDate || '—'}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-slate-500 block text-[10px]">EXECUTION PLACE</span>
              <span className="font-bold text-slate-900 truncate block">
                {extractionResult.executionPlace || '—'}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-slate-500 block text-[10px]">PARTNERS DETECTED</span>
              <span className="font-bold text-slate-900">
                {Array.isArray(extractionResult.partners) ? extractionResult.partners.length : 0} Partners
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
