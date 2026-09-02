import React, { useState } from 'react';
import { 
  X, 
  Sparkles, 
  CheckCircle2, 
  QrCode, 
  ChevronRight
} from 'lucide-react';
import { Asset } from '../types';
import { formatINR } from '../services/reliabilityScore';

interface DemoAssetShowcaseProps {
  asset: Asset | null;
  isOpen: boolean;
  onClose: () => void;
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  onOpenFullDossier: (asset: Asset) => void;
}

export const DemoAssetShowcase: React.FC<DemoAssetShowcaseProps> = ({
  asset,
  isOpen,
  onClose,
  currencyMode,
  onOpenFullDossier
}) => {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen || !asset) return null;

  const lifecycleSteps = [
    {
      title: '1. Capex & 3-Way Match',
      tagline: 'PO → GRN → Tax Invoice Verification',
      badge: 'Validated',
      content: (
        <div className="space-y-3">
          <p className="text-xs text-slate-600">
            Procured via approved Capex Budget FY24-Q1. 3-Way match executed between Purchase Order <strong className="text-slate-900 font-mono">{asset.poNumber}</strong>, Goods Receipt <strong className="text-slate-900 font-mono">{asset.grnNumber}</strong>, and Vendor Tax Invoice <strong className="text-slate-900 font-mono">{asset.invoiceNumber}</strong> from DMG Mori India Pvt Ltd.
          </p>
          <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs shadow-2xs">
            <div>
              <span className="text-slate-500 text-[11px] block font-semibold">Invoice Cost</span>
              <span className="font-bold text-slate-900 font-mono">{formatINR(asset.costINR, currencyMode)}</span>
            </div>
            <div>
              <span className="text-slate-500 text-[11px] block font-semibold">GST ITC @ 18%</span>
              <span className="font-bold text-emerald-700 font-mono">₹8.73 Lakhs Claimed</span>
            </div>
          </div>
        </div>
      )
    },
    {
      title: '2. AI Capitalisation & Ind AS 16 Component Split',
      tagline: 'Significant Parts Accounting under Para 43',
      badge: 'Componentised',
      content: (
        <div className="space-y-3">
          <p className="text-xs text-slate-600">
            AssetTrust AI determined this 5-Axis machine contains distinct sub-components with unequal economic lifespans. Instead of a single 15-year block, 3 separate sub-assets were capitalised:
          </p>
          <div className="space-y-2">
            {[
              { name: 'Cast Iron Machine Bed & Frame', cost: '₹28,00,000 (58%)', life: '15 Years' },
              { name: 'Electro-Spindle Sub-assembly', cost: '₹12,50,000 (26%)', life: '6 Years' },
              { name: 'Siemens 840D CNC Controller & PLC', cost: '₹8,00,000 (16%)', life: '6 Years' }
            ].map((comp, i) => (
              <div key={i} className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 flex items-center justify-between text-xs shadow-2xs">
                <div>
                  <span className="font-bold text-slate-900 block">{comp.name}</span>
                  <span className="text-slate-500 text-[11px]">{comp.cost}</span>
                </div>
                <span className="font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                  {comp.life}
                </span>
              </div>
            ))}
          </div>
        </div>
      )
    },
    {
      title: '3. Digital Tagging & Physical Verification',
      tagline: 'QR Matrix Tagging with Mobile GPS Stamp',
      badge: 'Verified',
      content: (
        <div className="space-y-3">
          <div className="flex items-center space-x-4 bg-slate-50 p-3 rounded-xl border border-slate-200 shadow-2xs">
            <div className="w-12 h-12 bg-white border border-slate-200 rounded-lg flex items-center justify-center p-1 shrink-0">
              <QrCode className="w-10 h-10 text-slate-900" />
            </div>
            <div className="text-xs">
              <span className="font-mono font-bold text-blue-700 block">{asset.qrCode}</span>
              <span className="text-slate-600 text-[11px] block">Location: {asset.plant} • {asset.subLocation}</span>
              <span className="text-[10px] text-slate-400 font-mono">Verified by: Anuj Patil (Lead Auditor)</span>
            </div>
          </div>
          <p className="text-xs text-slate-600">
            Physical audit matched serial number <strong className="text-slate-900 font-mono">{asset.serialNumber}</strong> on machine nameplate with zero variance.
          </p>
        </div>
      )
    },
    {
      title: '4. Depreciation & Section 32 Tax Engine',
      tagline: 'Companies Act Sch II vs IT Act Dual Books',
      badge: 'Synchronized',
      content: (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs shadow-2xs">
            <div>
              <span className="text-slate-500 text-[11px] block font-semibold">Book Depreciation (SLM)</span>
              <span className="font-bold text-slate-900 font-mono">₹4,85,000 / Year</span>
              <span className="text-[10px] text-slate-500 block">Ind AS 16 / Sch II</span>
            </div>
            <div>
              <span className="text-slate-500 text-[11px] block font-semibold">Tax Depreciation (WDV)</span>
              <span className="font-bold text-emerald-700 font-mono">15% Block Rate</span>
              <span className="text-[10px] text-slate-500 block">Income Tax Sec 32</span>
            </div>
          </div>
          <p className="text-xs text-slate-600">
            Net Book Value after 12 months: <strong className="text-emerald-700 font-mono font-bold">{formatINR(asset.nbvINR, currencyMode)}</strong>. Fully reconciled against General Ledger account 104000 (Plant & Machinery).
          </p>
        </div>
      )
    },
    {
      title: '5. Governance & Audit Assurance Clearance',
      tagline: 'CARO 2020 & Internal Financial Controls Sign-Off',
      badge: 'Assurance Ready',
      content: (
        <div className="space-y-3">
          <div className="bg-emerald-50 border border-emerald-200 p-3.5 rounded-xl text-emerald-900 text-xs space-y-1.5 shadow-2xs">
            <div className="flex items-center space-x-2 font-bold text-emerald-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>100% Audit Trust Score (Clean Control Status)</span>
            </div>
            <p className="text-[11px] text-emerald-700">
              This asset satisfies all statutory benchmarks under CARO 2020 Clause 3(i), Ind AS 16 para 43, and Schedule II useful life mandates.
            </p>
          </div>
        </div>
      )
    }
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col text-slate-800 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-100 bg-slate-50 flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2 text-xs font-bold text-blue-600 uppercase tracking-wider">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <span>Asset Spotlight • End-to-End Governance Lifecycle</span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              {asset.name}
            </h2>
            <p className="text-xs text-slate-500">
              Asset ID: <strong className="text-slate-800 font-mono">{asset.id}</strong> • Gross Block: <strong className="text-blue-700 font-mono">{formatINR(asset.costINR, currencyMode)}</strong>
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Navigation Bar */}
        <div className="grid grid-cols-5 border-b border-slate-200 bg-slate-50/50 text-xs">
          {lifecycleSteps.map((step, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentStep(idx)}
              className={`p-3 text-center transition-all border-b-2 font-medium ${
                currentStep === idx
                  ? 'border-blue-600 text-blue-700 bg-white shadow-2xs font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <span className="block text-[11px]">Step {idx + 1}</span>
              <span className="text-[10px] truncate block opacity-80">{step.title.split('. ')[1]}</span>
            </button>
          ))}
        </div>

        {/* Step Content */}
        <div className="p-6 space-y-4 flex-1">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900">{lifecycleSteps[currentStep].title}</h3>
              <p className="text-xs text-blue-600 font-semibold">{lifecycleSteps[currentStep].tagline}</p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
              {lifecycleSteps[currentStep].badge}
            </span>
          </div>

          <div className="pt-2">
            {lifecycleSteps[currentStep].content}
          </div>
        </div>

        {/* Footer Navigation */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between text-xs">
          <button
            onClick={() => onOpenFullDossier(asset)}
            className="text-blue-600 hover:text-blue-800 underline font-semibold"
          >
            Open Complete Technical Dossier →
          </button>

          <div className="flex items-center space-x-2">
            {currentStep > 0 && (
              <button
                onClick={() => setCurrentStep((prev) => prev - 1)}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg"
              >
                Previous Step
              </button>
            )}

            {currentStep < lifecycleSteps.length - 1 ? (
              <button
                onClick={() => setCurrentStep((prev) => prev + 1)}
                className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg flex items-center space-x-1.5 shadow-xs"
              >
                <span>Next Step</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={onClose}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-xs"
              >
                Done
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
