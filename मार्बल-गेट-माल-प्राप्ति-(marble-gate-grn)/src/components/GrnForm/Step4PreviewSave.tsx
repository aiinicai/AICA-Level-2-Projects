import React from 'react';
import { StoneBlock, WeighbridgeRecord, FactorySettings, UserAccount } from '../../types/grn';
import { calculateGrnTotals } from '../../utils/calculations';
import { CheckCircle2, ShieldCheck, Truck, Scale, FileText, UserCheck, AlertTriangle, Building2, MapPin } from 'lucide-react';

interface Step4Props {
  formData: {
    supplierName: string;
    supplierQuarry: string;
    challanNumber: string;
    challanDate: string;
    vehicleNumber: string;
    driverName: string;
    driverMobile: string;
    ewayBillNumber: string;
    gateName: string;
    materialType: string;
  };
  blocks: StoneBlock[];
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
  currentUser: UserAccount;
  isOnline: boolean;
  isSaving: boolean;
  onSave: () => void;
  onBack: () => void;
}

export const Step4PreviewSave: React.FC<Step4Props> = ({
  formData,
  blocks,
  weighbridge,
  photos,
  generalRemarks,
  receiverSignature,
  driverSignature,
  settings,
  currentUser,
  isOnline,
  isSaving,
  onSave,
  onBack,
}) => {
  const totals = calculateGrnTotals(blocks);

  return (
    <div className="space-y-6">
      
      {/* Network Status Notice */}
      {!isOnline ? (
        <div className="bg-amber-100 border-2 border-amber-600 rounded-2xl p-4 text-amber-950 flex items-start gap-3 shadow-md">
          <AlertTriangle className="w-6 h-6 text-amber-700 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-extrabold text-base text-amber-900">
              ऑफलाइन रसीद बनेगी (सिंक बाकी)
            </h4>
            <p className="text-xs sm:text-sm text-amber-900 mt-1">
              आपका फोन अभी इंटरनेट से नहीं जुड़ा है। रसीद <strong>अस्थायी नंबर (Provisional GRN)</strong> के साथ तुरंत इस फोन में सुरक्षित हो जाएगी। आप इसे प्रिंट या डाउनलोड कर सकते हैं। इंटरनेट आते ही यह स्वतः मुख्य सर्वर पर सिंक हो जाएगी।
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-emerald-50 border-2 border-emerald-500 rounded-2xl p-3.5 text-emerald-950 flex items-center gap-3">
          <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
          <span className="text-xs sm:text-sm font-bold text-emerald-900">
            ऑनलाइन मोड: रसीद सीधे केंद्रीय सर्वर पर सुरक्षित होगी और मालिक के डैशबोर्ड पर तुरंत दिखेगी।
          </span>
        </div>
      )}

      {/* Field Origin Legend */}
      <div className="bg-slate-100 rounded-2xl p-3 border border-slate-200 flex flex-wrap items-center gap-3 text-xs">
        <span className="font-bold text-slate-700">फील्ड संकेत:</span>
        <span className="inline-flex items-center gap-1 font-semibold text-slate-800">
          <span className="w-2.5 h-2.5 rounded-full bg-teal-600 inline-block"></span>
          मूल भौतिक रसीद (Physical Sample)
        </span>
        <span className="inline-flex items-center gap-1 font-semibold text-blue-700">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block"></span>
          अनुशंसित अतिरिक्त (Recommended Addition)
        </span>
      </div>

      {/* Official Voucher Preview Card */}
      <div className="bg-white rounded-3xl border-2 border-slate-300 p-5 sm:p-7 shadow-lg space-y-6">
        
        {/* Factory Header */}
        <div className="text-center border-b-2 border-slate-800 pb-4">
          <div className="text-[11px] font-bold text-teal-800 tracking-widest uppercase">
            {settings.factoryTagline}
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-slate-900 mt-0.5">
            {settings.factoryName}
          </h2>
          <div className="text-xs text-slate-600 mt-1">
            {settings.factoryAddress} | फोन: {settings.factoryPhone}
          </div>
          <div className="text-xs font-mono font-bold text-slate-700 mt-0.5">
            GSTIN: {settings.factoryGstin}
          </div>

          <div className="mt-3 inline-block bg-slate-900 text-white font-black px-4 py-1.5 rounded-lg text-sm uppercase tracking-wide">
            {settings.receiptTitle}
          </div>
        </div>

        {/* Top Info Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3.5 rounded-2xl border border-slate-200 text-xs">
          <div>
            <span className="text-slate-500 block">रसीद सं. (GRN No):</span>
            <span className="font-bold text-teal-800 text-sm">
              {isOnline ? 'स्वतः जारी होगी' : 'अस्थायी (सिंक बाकी)'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">दिनांक व समय:</span>
            <span className="font-bold text-slate-900">
              {new Date().toLocaleDateString('hi-IN')} {new Date().toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">गेट का नाम:</span>
            <span className="font-bold text-slate-900">{formData.gateName}</span>
          </div>
          <div>
            <span className="text-slate-500 block">प्राप्तकर्ता (Worker):</span>
            <span className="font-bold text-slate-900">{currentUser.name}</span>
          </div>
        </div>

        {/* Supplier & Vehicle Details */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="border border-slate-200 rounded-2xl p-3.5 space-y-1.5 bg-slate-50/50">
            <div className="font-bold text-slate-900 border-b border-slate-200 pb-1 flex items-center justify-between">
              <span>सप्लायर विवरण:</span>
              <span className="text-[10px] text-teal-700 font-bold">मूल फील्ड</span>
            </div>
            <div><strong>सप्लायर:</strong> {formData.supplierName}</div>
            {formData.supplierQuarry && <div><strong>खदान / रेंज:</strong> {formData.supplierQuarry}</div>}
            <div><strong>चालान सं.:</strong> <span className="font-mono font-bold">{formData.challanNumber}</span></div>
            <div><strong>चालान दिनांक:</strong> {formData.challanDate}</div>
            {formData.ewayBillNumber && (
              <div className="text-blue-700">
                <strong>ई-वे बिल नं.:</strong> <span className="font-mono">{formData.ewayBillNumber}</span> (अतिरिक्त)
              </div>
            )}
          </div>

          <div className="border border-slate-200 rounded-2xl p-3.5 space-y-1.5 bg-slate-50/50">
            <div className="font-bold text-slate-900 border-b border-slate-200 pb-1 flex items-center justify-between">
              <span>वाहन एवं ड्राइवर विवरण:</span>
              <span className="text-[10px] text-teal-700 font-bold">मूल फील्ड</span>
            </div>
            <div><strong>गाड़ी नंबर:</strong> <span className="font-mono font-bold text-slate-900">{formData.vehicleNumber}</span></div>
            <div><strong>ड्राइवर का नाम:</strong> {formData.driverName}</div>
            {formData.driverMobile && <div><strong>मोबाइल नंबर:</strong> <span className="font-mono">{formData.driverMobile}</span></div>}
            <div><strong>सामग्री श्रेणी:</strong> {formData.materialType}</div>
          </div>
        </div>

        {/* Blocks Table Preview */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-extrabold text-sm text-slate-900">
              ब्लॉक एवं सामग्री तालिका ({blocks.length} ब्लॉक):
            </h4>
            <span className="text-[11px] font-bold text-teal-800">मूल भौतिक तालिका</span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-300">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-800 text-white font-bold">
                  <th className="p-2 border border-slate-700 text-center">क्र.</th>
                  <th className="p-2 border border-slate-700">ब्लॉक नंबर</th>
                  <th className="p-2 border border-slate-700">किस्म (Variety)</th>
                  <th className="p-2 border border-slate-700 text-center">टुकड़े</th>
                  <th className="p-2 border border-slate-700 text-center">नाप (L × W × H)</th>
                  <th className="p-2 border border-slate-700 text-right">अनुमानित आयतन</th>
                  <th className="p-2 border border-slate-700 text-center">स्थिति</th>
                </tr>
              </thead>
              <tbody>
                {blocks.map((b, idx) => (
                  <tr key={b.id} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                    <td className="p-2 border border-slate-300 text-center font-bold">{idx + 1}</td>
                    <td className="p-2 border border-slate-300 font-mono font-bold text-slate-900">{b.blockNumber}</td>
                    <td className="p-2 border border-slate-300">{b.variety}</td>
                    <td className="p-2 border border-slate-300 text-center font-bold">{b.pieces || 1}</td>
                    <td className="p-2 border border-slate-300 text-center font-mono">
                      {b.length} × {b.width} × {b.height} {b.unit.split(' ')[0]}
                    </td>
                    <td className="p-2 border border-slate-300 text-right font-mono font-bold text-slate-900">
                      {b.estimatedVolume.toFixed(2)} CFT
                    </td>
                    <td className="p-2 border border-slate-300 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        b.condition === 'ठीक' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {b.condition}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100 font-black text-slate-900 border-t-2 border-slate-800">
                  <td colSpan={3} className="p-2 border border-slate-300 text-right">कुल योग (Total):</td>
                  <td className="p-2 border border-slate-300 text-center">{totals.totalPieces}</td>
                  <td className="p-2 border border-slate-300 text-center">-</td>
                  <td className="p-2 border border-slate-300 text-right text-teal-800 font-mono font-black">
                    {totals.totalVolumeEstimateCft.toFixed(2)} CFT
                  </td>
                  <td className="p-2 border border-slate-300"></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* Weighbridge Summary if enabled */}
        {weighbridge.enabled && (
          <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div>
              <span className="font-bold text-slate-800">धर्मकांटा विवरण: </span>
              <span>पर्ची सं.: {weighbridge.slipNumber || '-'} ({weighbridge.weighbridgeName || 'धर्मकांटा'})</span>
            </div>
            <div className="flex gap-4 font-mono">
              <span>सकल: <strong>{weighbridge.grossWeight} {weighbridge.unit.split(' ')[0]}</strong></span>
              <span>खाली: <strong>{weighbridge.tareWeight} {weighbridge.unit.split(' ')[0]}</strong></span>
              <span className="text-teal-900 font-black bg-teal-100 px-2 py-0.5 rounded">
                शुद्ध वजन: {weighbridge.netWeight} {weighbridge.unit.split(' ')[0]}
              </span>
            </div>
          </div>
        )}

        {/* General Remarks */}
        {generalRemarks && (
          <div className="text-xs bg-slate-50 p-3 rounded-xl border border-slate-200">
            <strong>विशेष टिप्पणी:</strong> {generalRemarks}
          </div>
        )}

        {/* Declaration Statement */}
        <div className="bg-amber-50/60 border border-amber-300 p-3 rounded-xl text-xs text-amber-950">
          <strong>घोषणा (Declaration):</strong> {settings.declarationText}
        </div>

        {/* Signature Spaces */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-200 text-xs text-center">
          <div className="space-y-1">
            <div className="h-16 border border-slate-300 rounded-xl bg-slate-50 flex items-center justify-center p-1">
              {receiverSignature ? (
                <img src={receiverSignature} alt="प्राप्तकर्ता साइन" className="max-h-full max-w-full object-contain" />
              ) : (
                <span className="text-slate-400 italic">हस्ताक्षर उपलब्ध</span>
              )}
            </div>
            <div className="font-bold text-slate-800">प्राप्तकर्ता हस्ताक्षर</div>
            <div className="text-[10px] text-slate-500">({currentUser.name})</div>
          </div>

          <div className="space-y-1">
            <div className="h-16 border border-slate-300 rounded-xl bg-slate-50 flex items-center justify-center p-1">
              {driverSignature ? (
                <img src={driverSignature} alt="ड्राइवर साइन" className="max-h-full max-w-full object-contain" />
              ) : (
                <span className="text-slate-400 italic">ड्राइवर साइन</span>
              )}
            </div>
            <div className="font-bold text-slate-800">वाहन चालक हस्ताक्षर</div>
            <div className="text-[10px] text-slate-500">({formData.driverName})</div>
          </div>

          <div className="col-span-2 sm:col-span-1 space-y-1">
            <div className="h-16 border border-dashed border-slate-300 rounded-xl bg-slate-50 flex items-center justify-center text-slate-400 italic text-[11px]">
              सील / मुहर
            </div>
            <div className="font-bold text-slate-800">अधिकृत प्रबंधक हस्ताक्षर</div>
          </div>
        </div>

      </div>

      {/* Confirmation & Save Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 pt-2">
        <button
          type="button"
          onClick={onBack}
          disabled={isSaving}
          className="py-4 px-6 bg-slate-200 hover:bg-slate-300 text-slate-800 font-extrabold text-base rounded-2xl transition cursor-pointer text-center"
          style={{ minHeight: '54px' }}
        >
          ⬅ पीछे जाएं (सुधार करें)
        </button>

        <button
          type="button"
          onClick={onSave}
          disabled={isSaving}
          className="flex-1 py-4 bg-teal-700 hover:bg-teal-800 text-white font-extrabold text-lg sm:text-xl rounded-2xl shadow-xl shadow-teal-900/30 transition active:scale-98 flex items-center justify-center gap-2 cursor-pointer"
          style={{ minHeight: '54px' }}
        >
          {isSaving ? (
            <span>रसीद बनाई जा रही है...</span>
          ) : (
            <>
              <CheckCircle2 className="w-6 h-6 text-amber-300" />
              <span>पुष्टि करें एवं रसीद बनाएं (Generate GRN)</span>
            </>
          )}
        </button>
      </div>

    </div>
  );
};
