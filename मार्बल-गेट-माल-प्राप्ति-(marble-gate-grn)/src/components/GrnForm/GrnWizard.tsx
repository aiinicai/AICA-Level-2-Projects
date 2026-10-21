import React, { useState, useEffect, useCallback } from 'react';
import { Step1SupplierVehicle } from './Step1SupplierVehicle';
import { Step2Blocks } from './Step2Blocks';
import { Step3WeighbridgeRemarks } from './Step3WeighbridgeRemarks';
import { Step4PreviewSave } from './Step4PreviewSave';
import { MasterData, FactorySettings, UserAccount, StoneBlock, WeighbridgeRecord, GoodsReceiptNote } from '../../types/grn';
import { saveLocalDraft, clearLocalDraft, enqueueOfflineGrn } from '../../utils/offlineDb';
import { ArrowLeft, ArrowRight, Save, CheckCircle, AlertTriangle } from 'lucide-react';

interface GrnWizardProps {
  currentUser: UserAccount;
  masters: MasterData;
  settings: FactorySettings;
  isOnline: boolean;
  initialDraftData?: any;
  onGrnCreated: (grn: GoodsReceiptNote) => void;
  onCancel: () => void;
}

export const GrnWizard: React.FC<GrnWizardProps> = ({
  currentUser,
  masters,
  settings,
  isOnline,
  initialDraftData,
  onGrnCreated,
  onCancel,
}) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Form State
  const [supplierVehicle, setSupplierVehicle] = useState({
    supplierName: initialDraftData?.supplierName || '',
    supplierQuarry: initialDraftData?.supplierQuarry || '',
    challanNumber: initialDraftData?.challanNumber || '',
    challanDate: initialDraftData?.challanDate || new Date().toISOString().split('T')[0],
    vehicleNumber: initialDraftData?.vehicleNumber || '',
    driverName: initialDraftData?.driverName || '',
    driverMobile: initialDraftData?.driverMobile || '',
    ewayBillNumber: initialDraftData?.ewayBillNumber || '',
    gateName: initialDraftData?.gateName || currentUser.gateName || 'गेट नंबर 1 (मुख्य गेट)',
    materialType: (initialDraftData?.materialType || 'मार्बल ब्लॉक') as 'मार्बल ब्लॉक' | 'पत्थर/स्टोन ब्लॉक' | 'अन्य स्लैब/टाइल',
  });

  const [blocks, setBlocks] = useState<StoneBlock[]>(
    initialDraftData?.blocks && initialDraftData.blocks.length > 0
      ? initialDraftData.blocks.map((b: any, idx: number) => ({
          ...b,
          id: b.id || `blk-${Date.now()}-${idx}`,
          blockNumber: b.blockNumber || '',
          variety: b.variety || masters.varieties[0] || 'मकराना वाइट (Makrana White)',
          pieces: b.pieces ?? 1,
          length: b.length ?? 0,
          width: b.width ?? 0,
          height: b.height ?? 0,
          unit: b.unit || settings.defaultMeasurementUnit || 'इंच (Inches)',
          estimatedVolume: b.estimatedVolume ?? 0,
          volumeUnit: b.volumeUnit || 'घन फीट (CFT)',
          condition: b.condition || 'ठीक',
          inspectionStatus: b.inspectionStatus || 'स्वीकृत',
          remarks: b.remarks || '',
        }))
      : [
          {
            id: `blk-${Date.now()}-1`,
            blockNumber: '',
            variety: masters.varieties[0] || 'मकराना वाइट (Makrana White)',
            pieces: 1,
            length: 0,
            width: 0,
            height: 0,
            unit: settings.defaultMeasurementUnit || 'इंच (Inches)',
            estimatedVolume: 0,
            volumeUnit: 'घन फीट (CFT)',
            condition: 'ठीक',
            inspectionStatus: 'स्वीकृत',
            remarks: '',
          },
        ]
  );

  const [weighbridge, setWeighbridge] = useState<WeighbridgeRecord>(
    initialDraftData?.weighbridge
      ? {
          enabled: Boolean(initialDraftData.weighbridge.enabled ?? settings.requireWeighbridge ?? true),
          grossWeight: initialDraftData.weighbridge.grossWeight ?? 0,
          tareWeight: initialDraftData.weighbridge.tareWeight ?? 0,
          netWeight: initialDraftData.weighbridge.netWeight ?? 0,
          unit: initialDraftData.weighbridge.unit || settings.defaultWeightUnit || 'टन (Tonnes)',
          slipNumber: initialDraftData.weighbridge.slipNumber || '',
          weighbridgeName: initialDraftData.weighbridge.weighbridgeName || 'किशनगढ़ धर्मकांटा',
        }
      : {
          enabled: settings.requireWeighbridge ?? true,
          grossWeight: 0,
          tareWeight: 0,
          netWeight: 0,
          unit: settings.defaultWeightUnit || 'टन (Tonnes)',
          slipNumber: '',
          weighbridgeName: 'किशनगढ़ धर्मकांटा',
        }
  );

  const [photos, setPhotos] = useState<{
    vehicle?: string;
    blocks?: string;
    challan?: string;
    weighbridgeSlip?: string;
  }>(initialDraftData?.photos || {});

  const [generalRemarks, setGeneralRemarks] = useState<string>(initialDraftData?.generalRemarks || '');
  const [receiverSignature, setReceiverSignature] = useState<string | undefined>(initialDraftData?.receiverSignature);
  const [driverSignature, setDriverSignature] = useState<string | undefined>(initialDraftData?.driverSignature);

  // Duplicate warning state
  const [duplicateWarning, setDuplicateWarning] = useState<{
    isDuplicate: boolean;
    existingGrnNumber?: string;
    existingDate?: string;
  } | null>(null);
  const [acknowledgedDuplicate, setAcknowledgedDuplicate] = useState<boolean>(false);

  // Auto-save draft whenever anything changes
  useEffect(() => {
    const draftPayload = {
      supplierName: supplierVehicle.supplierName,
      supplierQuarry: supplierVehicle.supplierQuarry,
      challanNumber: supplierVehicle.challanNumber,
      challanDate: supplierVehicle.challanDate,
      vehicleNumber: supplierVehicle.vehicleNumber,
      driverName: supplierVehicle.driverName,
      driverMobile: supplierVehicle.driverMobile,
      ewayBillNumber: supplierVehicle.ewayBillNumber,
      gateName: supplierVehicle.gateName,
      materialType: supplierVehicle.materialType,
      blocks,
      weighbridge,
      photos,
      generalRemarks,
      receiverSignature,
      driverSignature,
    };
    saveLocalDraft(draftPayload);
  }, [supplierVehicle, blocks, weighbridge, photos, generalRemarks, receiverSignature, driverSignature]);

  // Step 1 field change
  const handleSupplierVehicleChange = (field: string, val: any) => {
    setSupplierVehicle((prev) => ({ ...prev, [field]: val }));
    if (errors[field]) {
      setErrors((prev) => {
        const copy = { ...prev };
        delete copy[field];
        return copy;
      });
    }

    // Reset duplicate ack if user edits supplier or challan
    if (field === 'supplierName' || field === 'challanNumber') {
      setAcknowledgedDuplicate(false);
      setDuplicateWarning(null);
    }
  };

  // Check duplicate on server if online
  const checkDuplicate = async (): Promise<boolean> => {
    if (!isOnline || !supplierVehicle.supplierName || !supplierVehicle.challanNumber) {
      return false;
    }
    try {
      const res = await fetch('/api/grn/check-duplicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplierName: supplierVehicle.supplierName,
          challanNumber: supplierVehicle.challanNumber,
          vehicleNumber: supplierVehicle.vehicleNumber,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.duplicate) {
          setDuplicateWarning({
            isDuplicate: true,
            existingGrnNumber: data.existingGrnNumber,
            existingDate: data.existingDate,
          });
          return true;
        }
      }
    } catch {
      // Ignore network errors in duplicate check
    }
    return false;
  };

  // Validation before advancing
  const validateStep = async (step: number): Promise<boolean> => {
    const newErrors: Record<string, string> = {};

    if (step === 1) {
      if (!supplierVehicle.supplierName.trim()) {
        newErrors.supplierName = 'सप्लायर का नाम दर्ज करना अनिवार्य है।';
      }
      if (!supplierVehicle.challanNumber.trim()) {
        newErrors.challanNumber = 'चालान नंबर दर्ज करना अनिवार्य है।';
      }
      if (!supplierVehicle.vehicleNumber.trim()) {
        newErrors.vehicleNumber = 'गाड़ी नंबर दर्ज करना अनिवार्य है।';
      }
      if (!supplierVehicle.driverName.trim()) {
        newErrors.driverName = 'ड्राइवर का नाम दर्ज करना अनिवार्य है।';
      }

      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors);
        return false;
      }

      // Check duplicate
      if (!acknowledgedDuplicate) {
        const isDup = await checkDuplicate();
        if (isDup) {
          return false;
        }
      }
    }

    if (step === 2) {
      if (blocks.length === 0) {
        newErrors.blocks = 'कम से कम एक ब्लॉक का विवरण होना अनिवार्य है।';
      }
      for (let i = 0; i < blocks.length; i++) {
        const b = blocks[i];
        if (!b.blockNumber.trim()) {
          newErrors.blocks = `ब्लॉक #${i + 1} का ब्लॉक नंबर / मार्क दर्ज करें।`;
          break;
        }
        if (b.length <= 0 || b.width <= 0 || b.height <= 0) {
          newErrors.blocks = `ब्लॉक #${i + 1} (ब्लॉक नं. ${b.blockNumber}) की नाप (लंबाई, चौड़ाई, मोटाई) दर्ज करें।`;
          break;
        }
      }

      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors);
        return false;
      }
    }

    if (step === 3) {
      if (weighbridge.enabled) {
        if (weighbridge.tareWeight > weighbridge.grossWeight) {
          newErrors.weighbridge = 'खाली गाड़ी का वजन सकल वजन से अधिक नहीं हो सकता।';
          setErrors(newErrors);
          return false;
        }
      }
    }

    setErrors({});
    return true;
  };

  const handleNext = async () => {
    const isValid = await validateStep(currentStep);
    if (isValid && currentStep < 4) {
      setCurrentStep((prev) => prev + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      onCancel();
    }
  };

  // Final Save Handler
  const handleSaveGrn = async () => {
    try {
      setIsSaving(true);
      const now = new Date();
      const dateStr = now.toISOString().split('T')[0];
      const timeStr = now.toTimeString().substring(0, 5);

      const totalsPieces = blocks.reduce((acc, b) => acc + (Number(b.pieces) || 1), 0);
      const totalsCft = Number(blocks.reduce((acc, b) => acc + (Number(b.estimatedVolume) || 0), 0).toFixed(2));

      const payload: Partial<GoodsReceiptNote> = {
        date: dateStr,
        time: timeStr,
        gateName: supplierVehicle.gateName,
        receiverName: currentUser.name,
        receiverRole: currentUser.role === 'admin' ? 'मालिक / प्रबंधक' : 'गेट ऑपरेटर',
        supplierName: supplierVehicle.supplierName.trim(),
        supplierQuarry: supplierVehicle.supplierQuarry.trim(),
        challanNumber: supplierVehicle.challanNumber.trim(),
        challanDate: supplierVehicle.challanDate,
        vehicleNumber: supplierVehicle.vehicleNumber.trim().toUpperCase(),
        driverName: supplierVehicle.driverName.trim(),
        driverMobile: supplierVehicle.driverMobile.trim(),
        ewayBillNumber: supplierVehicle.ewayBillNumber.trim(),
        materialType: supplierVehicle.materialType,
        blocks,
        weighbridge,
        photos,
        receiverSignature,
        driverSignature,
        generalRemarks,
        status: blocks.some((b) => b.inspectionStatus === 'जांच बाकी') ? 'जांच बाकी' : 'स्वीकृत',
        createdBy: currentUser.name,
        totalBlocks: blocks.length,
        totalPieces: totalsPieces,
        totalVolumeEstimateCft: totalsCft,
        totalNetWeightTonnes: weighbridge.enabled ? weighbridge.netWeight : 0,
      };

      if (isOnline) {
        // Online Save direct to server
        const response = await fetch('/api/grn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          throw new Error('सर्वर पर रसीद सुरक्षित नहीं हो सकी');
        }

        const savedGrn = await response.json();
        await clearLocalDraft();
        setIsSaving(false);
        onGrnCreated(savedGrn);
      } else {
        // Offline Save to IndexedDB queue with provisional collision-safe ID
        const randomHex = Math.random().toString(36).substring(2, 6).toUpperCase();
        const provisionalId = `अस्थायी-${now.getFullYear()}-${randomHex}`;

        const offlineRecord: GoodsReceiptNote = {
          ...payload,
          id: `local-${Date.now()}`,
          grnNumber: provisionalId,
          provisionalId,
          isProvisional: true,
          syncStatus: 'सिंक बाकी',
          createdAt: now.toISOString(),
          updatedAt: now.toISOString(),
          revisions: [],
        } as GoodsReceiptNote;

        await enqueueOfflineGrn(offlineRecord);
        await clearLocalDraft();
        setIsSaving(false);
        onGrnCreated(offlineRecord);
      }
    } catch (err: any) {
      console.error('Save failed:', err);
      alert('रसीद सुरक्षित करने में त्रुटि: ' + (err.message || 'कृपया दोबारा प्रयास करें'));
      setIsSaving(false);
    }
  };

  const stepsMeta = [
    { num: 1, title: 'सप्लायर व गाड़ी' },
    { num: 2, title: 'ब्लॉक विवरण' },
    { num: 3, title: 'धर्मकांटा व साइन' },
    { num: 4, title: 'पूर्वावलोकन व रसीद' },
  ];

  return (
    <div className="max-w-3xl mx-auto px-4 py-5 space-y-6">
      
      {/* Wizard Header & Progress Bar */}
      <div className="bg-white rounded-3xl p-4 sm:p-5 border border-slate-200 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-teal-100 text-teal-900 border border-teal-200">
              कदम {currentStep} / 4
            </span>
            <h2 className="text-lg sm:text-xl font-black text-slate-900">
              {stepsMeta[currentStep - 1].title}
            </h2>
          </div>
          
          <button
            type="button"
            onClick={onCancel}
            className="text-xs font-bold text-slate-500 hover:text-red-600 transition"
          >
            रद्द करें
          </button>
        </div>

        {/* Visual Progress Steps */}
        <div className="grid grid-cols-4 gap-2">
          {stepsMeta.map((s) => {
            const isDone = s.num < currentStep;
            const isCurr = s.num === currentStep;
            return (
              <div key={s.num} className="space-y-1">
                <div
                  className={`h-2 rounded-full transition-all ${
                    isDone
                      ? 'bg-emerald-500'
                      : isCurr
                      ? 'bg-teal-700'
                      : 'bg-slate-200'
                  }`}
                />
                <div className={`text-[10px] font-bold text-center truncate ${
                  isCurr ? 'text-teal-900 font-black' : 'text-slate-400'
                }`}>
                  {s.title}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      {currentStep === 1 && (
        <Step1SupplierVehicle
          formData={supplierVehicle}
          errors={errors}
          masters={masters}
          settings={settings}
          onChange={handleSupplierVehicleChange}
          duplicateWarning={duplicateWarning}
          acknowledgedDuplicate={acknowledgedDuplicate}
          setAcknowledgedDuplicate={setAcknowledgedDuplicate}
        />
      )}

      {currentStep === 2 && (
        <Step2Blocks
          blocks={blocks}
          errors={errors}
          masters={masters}
          onChangeBlocks={setBlocks}
        />
      )}

      {currentStep === 3 && (
        <Step3WeighbridgeRemarks
          weighbridge={weighbridge}
          photos={photos}
          generalRemarks={generalRemarks}
          receiverSignature={receiverSignature}
          driverSignature={driverSignature}
          settings={settings}
          onChangeWeighbridge={setWeighbridge}
          onChangePhotos={setPhotos}
          onChangeRemarks={setGeneralRemarks}
          onChangeSignature={(type, data) => {
            if (type === 'receiver') setReceiverSignature(data);
            else setDriverSignature(data);
          }}
          errors={errors}
        />
      )}

      {currentStep === 4 && (
        <Step4PreviewSave
          formData={supplierVehicle}
          blocks={blocks}
          weighbridge={weighbridge}
          photos={photos}
          generalRemarks={generalRemarks}
          receiverSignature={receiverSignature}
          driverSignature={driverSignature}
          settings={settings}
          currentUser={currentUser}
          isOnline={isOnline}
          isSaving={isSaving}
          onSave={handleSaveGrn}
          onBack={() => setCurrentStep(3)}
        />
      )}

      {/* Navigation Buttons for Steps 1, 2, 3 */}
      {currentStep < 4 && (
        <div className="flex items-center justify-between gap-3 pt-2">
          <button
            type="button"
            onClick={handleBack}
            className="py-4 px-6 bg-slate-200 hover:bg-slate-300 text-slate-800 font-extrabold text-base rounded-2xl transition cursor-pointer flex items-center gap-2 active:scale-95"
            style={{ minHeight: '52px', minWidth: '100px' }}
          >
            <ArrowLeft className="w-5 h-5" />
            <span>पीछे</span>
          </button>

          <button
            type="button"
            onClick={handleNext}
            className="flex-1 py-4 px-6 bg-teal-700 hover:bg-teal-800 text-white font-extrabold text-lg rounded-2xl shadow-lg shadow-teal-900/20 transition cursor-pointer flex items-center justify-center gap-2 active:scale-98"
            style={{ minHeight: '52px' }}
          >
            <span>आगे (कदम {currentStep + 1})</span>
            <ArrowRight className="w-5 h-5 text-amber-300" />
          </button>
        </div>
      )}

    </div>
  );
};
