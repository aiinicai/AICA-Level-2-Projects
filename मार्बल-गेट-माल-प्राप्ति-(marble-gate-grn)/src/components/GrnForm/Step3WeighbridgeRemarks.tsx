import React, { useRef, useState, useEffect } from 'react';
import { WeighbridgeRecord, FactorySettings, WeightUnit } from '../../types/grn';
import { calculateNetWeight } from '../../utils/calculations';
import { Scale, Camera, Image as ImageIcon, Trash2, PenTool, AlertCircle, CheckCircle, Info } from 'lucide-react';

interface Step3Props {
  weighbridge: WeighbridgeRecord;
  photos: {
    vehicle?: string;
    blocks?: string;
    challan?: string;
    weighbridgeSlip?: string;
  };
  generalRemarks: string;
  receiverSignature?: string;
  driverSignature?: string;
  settings: FactorySettings;
  onChangeWeighbridge: (wb: WeighbridgeRecord) => void;
  onChangePhotos: (photos: any) => void;
  onChangeRemarks: (remarks: string) => void;
  onChangeSignature: (type: 'receiver' | 'driver', dataUrl: string | undefined) => void;
  errors: Record<string, string>;
}

export const Step3WeighbridgeRemarks: React.FC<Step3Props> = ({
  weighbridge,
  photos,
  generalRemarks,
  receiverSignature,
  driverSignature,
  settings,
  onChangeWeighbridge,
  onChangePhotos,
  onChangeRemarks,
  onChangeSignature,
  errors,
}) => {
  const [weighbridgeError, setWeighbridgeError] = useState<string | null>(null);

  // Digital Signature Canvas Refs
  const receiverCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const driverCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isDrawingReceiver, setIsDrawingReceiver] = useState(false);
  const [isDrawingDriver, setIsDrawingDriver] = useState(false);

  // Re-calculate weighbridge net weight
  const handleWeightChange = (field: 'grossWeight' | 'tareWeight', val: number) => {
    const gross = field === 'grossWeight' ? val : weighbridge.grossWeight;
    const tare = field === 'tareWeight' ? val : weighbridge.tareWeight;

    const { netWeight, error } = calculateNetWeight(gross, tare, weighbridge.unit);
    setWeighbridgeError(error);

    onChangeWeighbridge({
      ...weighbridge,
      [field]: val,
      netWeight: error ? 0 : netWeight
    });
  };

  // Photo Upload Handler with base64 compression
  const handlePhotoUpload = (key: keyof typeof photos, file: File | null) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        // Resize onto canvas to keep local storage lightweight
        const canvas = document.createElement('canvas');
        const maxDim = 800;
        let w = img.width;
        let h = img.height;
        if (w > h && w > maxDim) {
          h = Math.round((h * maxDim) / w);
          w = maxDim;
        } else if (h > maxDim) {
          w = Math.round((w * maxDim) / h);
          h = maxDim;
        }
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0, w, h);
          const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.7);
          onChangePhotos({ ...photos, [key]: compressedDataUrl });
        }
      };
      img.src = e.target?.result as string;
    };
    reader.readAsDataURL(file);
  };

  // Canvas drawing handlers for touch / pointer
  const startDrawing = (e: React.PointerEvent<HTMLCanvasElement>, type: 'receiver' | 'driver') => {
    const canvas = type === 'receiver' ? receiverCanvasRef.current : driverCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.setPointerCapture(e.pointerId);
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.beginPath();
    ctx.moveTo(x, y);

    if (type === 'receiver') setIsDrawingReceiver(true);
    else setIsDrawingDriver(true);
  };

  const draw = (e: React.PointerEvent<HTMLCanvasElement>, type: 'receiver' | 'driver') => {
    const isDrawing = type === 'receiver' ? isDrawingReceiver : isDrawingDriver;
    if (!isDrawing) return;

    const canvas = type === 'receiver' ? receiverCanvasRef.current : driverCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const endDrawing = (type: 'receiver' | 'driver') => {
    const canvas = type === 'receiver' ? receiverCanvasRef.current : driverCanvasRef.current;
    if (!canvas) return;

    if (type === 'receiver') {
      setIsDrawingReceiver(false);
      onChangeSignature('receiver', canvas.toDataURL('image/png'));
    } else {
      setIsDrawingDriver(false);
      onChangeSignature('driver', canvas.toDataURL('image/png'));
    }
  };

  const clearCanvas = (type: 'receiver' | 'driver') => {
    const canvas = type === 'receiver' ? receiverCanvasRef.current : driverCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      onChangeSignature(type, undefined);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Weighbridge Section */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-teal-700" />
            <h3 className="font-extrabold text-base text-slate-900">
              धर्मकांटा वजन पर्ची (Weighbridge Record)
            </h3>
          </div>

          <label className="flex items-center gap-2 text-xs font-bold text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={weighbridge.enabled}
              onChange={(e) => onChangeWeighbridge({ ...weighbridge, enabled: e.target.checked })}
              className="w-4 h-4 text-teal-600 rounded"
            />
            <span>वजन उपलब्ध है</span>
          </label>
        </div>

        {weighbridge.enabled ? (
          <div className="space-y-4">
            
            {/* Weight Unit */}
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700">वजन की इकाई (Unit):</label>
              <div className="flex gap-1">
                {(['टन (Tonnes)', 'किलो (Kg)', 'क्विंटल (Quintals)'] as WeightUnit[]).map((u) => (
                  <button
                    type="button"
                    key={u}
                    onClick={() => onChangeWeighbridge({ ...weighbridge, unit: u })}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold border transition ${
                      weighbridge.unit === u
                        ? 'bg-teal-700 text-white border-teal-800'
                        : 'bg-slate-100 text-slate-700 border-slate-200'
                    }`}
                  >
                    {u}
                  </button>
                ))}
              </div>
            </div>

            {/* Gross, Tare, Net Weight */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Gross Weight */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  सकल वजन (Gross Wt) <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type="number"
                    inputMode="decimal"
                    step="0.01"
                    min="0"
                    value={weighbridge.grossWeight === 0 ? '' : (weighbridge.grossWeight ?? '')}
                    onChange={(e) => handleWeightChange('grossWeight', parseFloat(e.target.value) || 0)}
                    placeholder="उदा. 42.50"
                    className="w-full p-3 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base font-mono font-bold text-slate-900 outline-none text-center"
                    style={{ minHeight: '48px' }}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400">
                    {weighbridge.unit.split(' ')[0]}
                  </span>
                </div>
              </div>

              {/* Tare Weight */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  खाली गाड़ी वजन (Tare Wt) <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type="number"
                    inputMode="decimal"
                    step="0.01"
                    min="0"
                    value={weighbridge.tareWeight === 0 ? '' : (weighbridge.tareWeight ?? '')}
                    onChange={(e) => handleWeightChange('tareWeight', parseFloat(e.target.value) || 0)}
                    placeholder="उदा. 16.20"
                    className="w-full p-3 rounded-xl border-2 border-slate-300 focus:border-teal-600 text-base font-mono font-bold text-slate-900 outline-none text-center"
                    style={{ minHeight: '48px' }}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400">
                    {weighbridge.unit.split(' ')[0]}
                  </span>
                </div>
              </div>

              {/* Net Weight (Auto-calculated) */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  शुद्ध वजन (Net Weight)
                </label>
                <div className="p-3 bg-teal-50 border-2 border-teal-500 rounded-xl text-center" style={{ minHeight: '48px' }}>
                  <div className="text-base font-mono font-black text-teal-950">
                    {weighbridge.netWeight} {weighbridge.unit.split(' ')[0]}
                  </div>
                  <div className="text-[10px] text-teal-700 font-semibold">
                    (सकल - खाली गाड़ी)
                  </div>
                </div>
              </div>
            </div>

            {weighbridgeError && (
              <div className="p-3 bg-red-100 border border-red-400 rounded-xl text-red-800 text-xs font-bold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{weighbridgeError}</span>
              </div>
            )}

            {/* Weighbridge Slip No. and Name */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  धर्मकांटा पर्ची नंबर (Slip No.)
                </label>
                <input
                  type="text"
                  value={weighbridge.slipNumber || ''}
                  onChange={(e) => onChangeWeighbridge({ ...weighbridge, slipNumber: e.target.value.toUpperCase() })}
                  placeholder="उदा. WB-99120"
                  className="w-full p-2.5 rounded-xl border border-slate-300 focus:border-teal-600 text-sm font-mono text-slate-900 outline-none"
                  style={{ minHeight: '44px' }}
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  धर्मकांटा का नाम (Weighbridge Name)
                </label>
                <input
                  type="text"
                  value={weighbridge.weighbridgeName || ''}
                  onChange={(e) => onChangeWeighbridge({ ...weighbridge, weighbridgeName: e.target.value })}
                  placeholder="उदा. किशनगढ़ धर्मकांटा"
                  className="w-full p-2.5 rounded-xl border border-slate-300 focus:border-teal-600 text-sm text-slate-900 outline-none"
                  style={{ minHeight: '44px' }}
                />
              </div>
            </div>

          </div>
        ) : (
          <p className="text-xs text-slate-500 italic bg-slate-50 p-3 rounded-xl border border-slate-200">
            धर्मकांटा वजन विकल्प बंद है। यदि गाड़ी का वजन धर्मकांटे पर किया गया है तो ऊपर दिए गए चेकबॉक्स को चालू करें।
          </p>
        )}
      </div>

      {/* Optional Photo Attachment Section */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <div className="flex items-center gap-2">
            <Camera className="w-5 h-5 text-teal-700" />
            <h3 className="font-extrabold text-base text-slate-900">
              फोटो संलग्नक (Photos - वैकल्पिक)
            </h3>
          </div>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            वैकल्पिक सुविधा
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { key: 'vehicle', label: 'गाड़ी फोटो', icon: Camera },
            { key: 'blocks', label: 'मार्बल ब्लॉक फोटो', icon: ImageIcon },
            { key: 'challan', label: 'चालान पर्ची', icon: Camera },
            { key: 'weighbridgeSlip', label: 'कांटा पर्ची', icon: Camera },
          ].map(({ key, label, icon: Icon }) => {
            const photoUrl = photos[key as keyof typeof photos];
            return (
              <div key={key} className="border-2 border-dashed border-slate-300 rounded-2xl p-2.5 text-center relative bg-slate-50 hover:bg-slate-100/60 transition">
                {photoUrl ? (
                  <div className="space-y-1.5">
                    <img
                      src={photoUrl}
                      alt={label}
                      className="w-full h-24 object-cover rounded-xl border border-slate-300 shadow-xs"
                    />
                    <div className="flex items-center justify-between text-[11px] font-bold px-1">
                      <span className="text-emerald-700 truncate">{label}</span>
                      <button
                        type="button"
                        onClick={() => onChangePhotos({ ...photos, [key]: undefined })}
                        className="text-red-500 hover:text-red-700 p-1"
                        title="हटाएं"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center h-28 cursor-pointer">
                    <Icon className="w-7 h-7 text-slate-400 mb-1" />
                    <span className="text-xs font-bold text-slate-700">{label}</span>
                    <span className="text-[10px] text-slate-500 mt-0.5">+ फोटो खींचें</span>
                    <input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      onChange={(e) => handlePhotoUpload(key as keyof typeof photos, e.target.files?.[0] || null)}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Digital Touch Signature Section */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <div className="flex items-center gap-2">
            <PenTool className="w-5 h-5 text-teal-700" />
            <h3 className="font-extrabold text-base text-slate-900">
              हस्ताक्षर (Signatures)
            </h3>
          </div>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            भौतिक रसीद अनुसार
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          
          {/* Gate Worker Signature */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700">
                1. गेट कर्मचारी / प्राप्तकर्ता हस्ताक्षर:
              </label>
              <button
                type="button"
                onClick={() => clearCanvas('receiver')}
                className="text-[11px] font-bold text-red-600 hover:underline cursor-pointer"
              >
                साफ करें
              </button>
            </div>
            
            <div className="border-2 border-slate-300 rounded-xl bg-slate-50 overflow-hidden relative touch-none">
              <canvas
                ref={receiverCanvasRef}
                width={320}
                height={120}
                onPointerDown={(e) => startDrawing(e, 'receiver')}
                onPointerMove={(e) => draw(e, 'receiver')}
                onPointerUp={() => endDrawing('receiver')}
                className="w-full h-28 cursor-crosshair block"
              />
              <div className="absolute bottom-1 right-2 text-[10px] text-slate-400 pointer-events-none">
                अंगुली से साइन करें
              </div>
            </div>
          </div>

          {/* Driver Signature */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700">
                2. ड्राइवर हस्ताक्षर (वैकल्पिक):
              </label>
              <button
                type="button"
                onClick={() => clearCanvas('driver')}
                className="text-[11px] font-bold text-red-600 hover:underline cursor-pointer"
              >
                साफ करें
              </button>
            </div>
            
            <div className="border-2 border-slate-300 rounded-xl bg-slate-50 overflow-hidden relative touch-none">
              <canvas
                ref={driverCanvasRef}
                width={320}
                height={120}
                onPointerDown={(e) => startDrawing(e, 'driver')}
                onPointerMove={(e) => draw(e, 'driver')}
                onPointerUp={() => endDrawing('driver')}
                className="w-full h-28 cursor-crosshair block"
              />
              <div className="absolute bottom-1 right-2 text-[10px] text-slate-400 pointer-events-none">
                अंगुली से साइन करें
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* General Remarks */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
        <label className="block text-xs font-bold text-slate-700">
          सामान्य टिप्पणी (General Remarks - यदि कोई विशेष बात हो)
        </label>
        <textarea
          rows={3}
          value={generalRemarks || ''}
          onChange={(e) => onChangeRemarks(e.target.value)}
          placeholder="उदा. ब्लॉक अनलोडिंग यार्ड 1 में रखी गई, गाड़ी समय पर आई..."
          className="w-full p-3 rounded-xl border border-slate-300 focus:border-teal-600 text-sm text-slate-900 outline-none"
        />
      </div>

    </div>
  );
};
