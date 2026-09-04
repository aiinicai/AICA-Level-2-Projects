import React, { useState } from 'react';
import { Sparkles, Loader2, CheckCircle, Wand2, Lightbulb, FileText, Check, AlertCircle } from 'lucide-react';
import { INDUSTRY_PRESETS, generateLegalObjectsClause } from '../utils/deedEngine';
import { generateBusinessObjectsAI } from '../utils/aiService';

interface BusinessObjectsAIProps {
  rawBusinessIdea: string;
  onUpdateRawIdea: (value: string) => void;
  firmObjects: string;
  onUpdateFirmObjects: (value: string) => void;
}

export const BusinessObjectsAI: React.FC<BusinessObjectsAIProps> = ({
  rawBusinessIdea,
  onUpdateRawIdea,
  firmObjects,
  onUpdateFirmObjects,
}) => {
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'info' | 'error' } | null>(null);

  const quickSamples = [
    'Art, Craft, Marriage Packing & Gifts',
    'Unisex Salon & Beauty Spa',
    'IT Software, AI & Mobile Apps',
    'Real Estate Builders & Infra',
    'FMCG Wholesale & Retail Trading',
    'Accounting, Audit & Tax Advisory',
    'Restaurant & Cafe Hospitality',
    'Logistics, Transport & Cargo'
  ];

  const handleGenerateAI = async () => {
    const inputContent = rawBusinessIdea.trim();
    if (!inputContent) {
      setStatusMessage({
        text: 'Please enter keywords or a business description first.',
        type: 'info'
      });
      setTimeout(() => setStatusMessage(null), 3000);
      return;
    }

    setLoading(true);
    setStatusMessage({
      text: 'Drafting formal legal objects clause with Gemini AI...',
      type: 'info'
    });

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    try {
      const data = await generateBusinessObjectsAI(inputContent);
      clearTimeout(timeoutId);

      if (data.success && data.objectsClause) {
        onUpdateFirmObjects(data.objectsClause);
        setStatusMessage({
          text: 'Successfully drafted legal objects clause!',
          type: 'success'
        });
      } else {
        throw new Error(data.error || 'Could not generate objects draft');
      }
    } catch (err: any) {
      console.warn('Applying built-in Legal Conveyancing Engine:', err);
      // Instant robust fallback from deed engine
      const legalDraft = generateLegalObjectsClause(inputContent);
      onUpdateFirmObjects(legalDraft);
      setStatusMessage({
        text: 'Drafted successfully using Legal Conveyancing Engine!',
        type: 'success'
      });
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleSelectQuickSample = (sample: string) => {
    const matchedPreset = INDUSTRY_PRESETS.find(p => 
      p.label.toLowerCase().includes(sample.toLowerCase().split(' ')[0]) ||
      p.businessIdea.toLowerCase().includes(sample.toLowerCase().split(' ')[0])
    );

    if (matchedPreset) {
      onUpdateRawIdea(matchedPreset.businessIdea);
      onUpdateFirmObjects(matchedPreset.firmObjects);
      setStatusMessage({
        text: `Loaded legal objects for ${sample}`,
        type: 'success'
      });
      setTimeout(() => setStatusMessage(null), 3000);
    } else {
      onUpdateRawIdea(sample.toUpperCase());
      const legalDraft = generateLegalObjectsClause(sample);
      onUpdateFirmObjects(legalDraft);
    }
  };

  const handleInstantFormat = () => {
    const textToFormat = rawBusinessIdea.trim() || firmObjects.trim() || 'commercial trading and professional services';
    const formatted = generateLegalObjectsClause(textToFormat);
    onUpdateFirmObjects(formatted);
    setStatusMessage({
      text: 'Formatted into standard Indian Partnership Act objects clause.',
      type: 'success'
    });
    setTimeout(() => setStatusMessage(null), 3000);
  };

  return (
    <div className="space-y-4">
      {/* AI Drafting Card */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                Business Objects Clause Drafter (AI Assisted)
              </h3>
              <p className="text-[11px] text-slate-500">
                Transforms keywords into an exhaustive Indian Partnership Act objects clause
              </p>
            </div>
          </div>
        </div>

        {/* Quick Industry Pills */}
        <div className="flex flex-wrap items-center gap-1.5 mb-3.5">
          <span className="text-[11px] text-slate-600 font-semibold flex items-center gap-1 mr-1">
            <Lightbulb className="w-3 h-3 text-amber-500" />
            Quick Presets:
          </span>
          {quickSamples.map((sample) => (
            <button
              key={sample}
              type="button"
              onClick={() => handleSelectQuickSample(sample)}
              className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-white hover:bg-blue-600 hover:text-white text-slate-700 border border-slate-300 transition shadow-2xs cursor-pointer"
            >
              {sample}
            </button>
          ))}
        </div>

        {/* Input box */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-slate-700 mb-1 uppercase tracking-wider">
            Enter Business Activities / Keywords / Industry
          </label>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={rawBusinessIdea}
              onChange={(e) => onUpdateRawIdea(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleGenerateAI();
                }
              }}
              placeholder="E.G., CREATIVE ART & CRAFT, MARRIAGE PACKING, UNIQUE GIFTS, SALON..."
              className="flex-1 px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-slate-900 text-xs font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow uppercase"
            />
            <button
              type="button"
              onClick={handleGenerateAI}
              disabled={loading}
              className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-blue-700 hover:bg-blue-800 disabled:bg-slate-300 text-white text-xs font-bold transition shadow-xs shrink-0 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Drafting...</span>
                </>
              ) : (
                <>
                  <Wand2 className="w-3.5 h-3.5" />
                  <span>Draft with AI</span>
                </>
              )}
            </button>
          </div>
          <p className="text-[10px] text-slate-400">
            Tip: Press <kbd className="px-1 py-0.5 bg-slate-200 text-slate-700 rounded text-[9px] font-mono">Enter</kbd> or click <b>Draft with AI</b> to generate.
          </p>
        </div>

        {/* Status Toast */}
        {statusMessage && (
          <div className={`mt-3 text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 border transition ${
            statusMessage.type === 'error'
              ? 'text-rose-900 bg-rose-50 border-rose-200'
              : statusMessage.type === 'success'
              ? 'text-emerald-900 bg-emerald-50 border-emerald-200'
              : 'text-blue-900 bg-blue-50 border-blue-200'
          }`}>
            {statusMessage.type === 'error' ? (
              <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
            ) : statusMessage.type === 'success' ? (
              <Check className="w-3.5 h-3.5 text-emerald-600" />
            ) : (
              <CheckCircle className="w-3.5 h-3.5 text-blue-600" />
            )}
            <span>{statusMessage.text}</span>
          </div>
        )}
      </div>

      {/* Final Objects Clause Textarea */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
            Final Nature of Business / Objects Clause (Clause #3 in Deed)
          </label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleInstantFormat}
              className="text-[11px] font-semibold text-blue-700 hover:text-blue-900 hover:underline flex items-center gap-1 cursor-pointer"
            >
              <FileText className="w-3 h-3" />
              Auto-Format into Legal Clause
            </button>
            <span className="text-[11px] text-slate-400">|</span>
            <span className="text-[11px] text-slate-400">Editable Legal Clause</span>
          </div>
        </div>
        <textarea
          rows={5}
          value={firmObjects}
          onChange={(e) => onUpdateFirmObjects(e.target.value)}
          placeholder="The business of the partnership shall be..."
          className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-900 text-xs leading-relaxed focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow"
        />
      </div>
    </div>
  );
};
