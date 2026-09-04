import React, { useState } from 'react';
import { Plus, Trash2, ShieldCheck, Sparkles, Loader2, Check, CheckCircle2, AlertCircle, Wand2 } from 'lucide-react';
import { CustomClause } from '../types';
import { generateCustomClauseAI } from '../utils/aiService';

interface CustomClausesEditorProps {
  nonCompete: boolean;
  onToggleNonCompete: (val: boolean) => void;
  clientOwnership: boolean;
  onToggleClientOwnership: (val: boolean) => void;
  customClauses: CustomClause[];
  onAddClause: (clause: CustomClause) => void;
  onUpdateClause: (id: string, field: keyof CustomClause, val: any) => void;
  onRemoveClause: (id: string) => void;
}

const QUICK_CLAUSE_PRESETS = [
  { title: 'BANK ACCOUNT SIGNING LIMITS', prompt: 'Joint signature of two partners above Rs. 50,000; single signature up to Rs. 50,000.' },
  { title: 'LOCK-IN PERIOD & MANDATORY DURATION', prompt: '3 years minimum lock-in period before any partner can retire without unanimous consent.' },
  { title: 'CONFIDENTIALITY & TRADE SECRETS', prompt: 'Absolute non-disclosure of proprietary customer data, pricing, and business secrets for 3 years post-exit.' },
  { title: 'ARBITRATION & DISPUTE RESOLUTION', prompt: 'All disputes referred to sole arbitrator under Indian Arbitration and Conciliation Act, 1996.' },
  { title: 'ADDITIONAL CAPITAL CALL', prompt: 'Partners shall contribute additional working capital in profit ratio within 30 days of written notice.' },
];

export const CustomClausesEditor: React.FC<CustomClausesEditorProps> = ({
  nonCompete,
  onToggleNonCompete,
  clientOwnership,
  onToggleClientOwnership,
  customClauses,
  onAddClause,
  onUpdateClause,
  onRemoveClause,
}) => {
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [isAiDrafting, setIsAiDrafting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'info' | 'error' } | null>(null);

  const handleAddManual = () => {
    if (!newTitle.trim() || !newContent.trim()) return;
    onAddClause({
      id: `clause_${Date.now()}`,
      title: newTitle.trim(),
      content: newContent.trim(),
      enabled: true,
    });
    setNewTitle('');
    setNewContent('');
    setAiPrompt('');
    setStatusMsg({ text: '✓ Clause added to partnership deed successfully!', type: 'success' });
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const handleAiDraftClause = async () => {
    if (!newTitle.trim()) {
      setStatusMsg({ text: 'Please enter a Clause Title first (e.g. BANK SIGNING LIMITS).', type: 'info' });
      setTimeout(() => setStatusMsg(null), 3500);
      return;
    }

    setIsAiDrafting(true);
    setStatusMsg({ text: 'Drafting legal clause with Gemini AI...', type: 'info' });

    try {
      const res = await generateCustomClauseAI(newTitle, aiPrompt || newTitle);
      if (res.success && res.clauseText) {
        setNewContent(res.clauseText);
        setStatusMsg({ text: '✓ Legal clause drafted by AI successfully!', type: 'success' });
        setTimeout(() => setStatusMsg(null), 4000);
      } else {
        setStatusMsg({ text: res.error || 'Failed to draft clause. Please check inputs.', type: 'error' });
      }
    } catch (e: any) {
      console.error('[CustomClauses] Drafting error:', e);
      setStatusMsg({ text: 'Error drafting clause: ' + (e?.message || 'Network error'), type: 'error' });
    } finally {
      setIsAiDrafting(false);
    }
  };

  const handleSelectPreset = (preset: { title: string; prompt: string }) => {
    setNewTitle(preset.title);
    setAiPrompt(preset.prompt);
  };

  return (
    <div className="space-y-4 text-xs">
      
      {/* Standard Special Covenants Checkboxes */}
      <div className="space-y-3">
        
        {/* Non Compete */}
        <label className="flex items-start gap-3 p-3.5 bg-slate-50 hover:bg-slate-100/70 rounded-xl border border-slate-200 cursor-pointer transition">
          <input
            type="checkbox"
            checked={nonCompete}
            onChange={(e) => onToggleNonCompete(e.target.checked)}
            className="w-4 h-4 mt-0.5 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
          />
          <div>
            <span className="font-bold text-slate-900 block text-xs">
              Non-Compete & NOC Clause
            </span>
            <span className="text-[11px] text-slate-500 leading-relaxed block mt-0.5">
              Partners cannot operate, assist, or finance competing businesses without prior written No Objection Certificate (NOC); all secret profits vest in the firm.
            </span>
          </div>
        </label>

        {/* Client Ownership */}
        <label className="flex items-start gap-3 p-3.5 bg-slate-50 hover:bg-slate-100/70 rounded-xl border border-slate-200 cursor-pointer transition">
          <input
            type="checkbox"
            checked={clientOwnership}
            onChange={(e) => onToggleClientOwnership(e.target.checked)}
            className="w-4 h-4 mt-0.5 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
          />
          <div>
            <span className="font-bold text-slate-900 block text-xs">
              Proprietary Clientele & Firm IP Ownership Clause
            </span>
            <span className="text-[11px] text-slate-500 leading-relaxed block mt-0.5">
              All clients, customer databases, goodwill, intellectual property, and mandates belong strictly to the firm entity and not to individual partners.
            </span>
          </div>
        </label>

      </div>

      {/* Existing Custom Clauses */}
      {customClauses && customClauses.length > 0 && (
        <div className="space-y-3 pt-2">
          <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wide">
            Additional Custom Clauses ({customClauses.length})
          </h4>
          {customClauses.map((clause) => (
            <div key={clause.id} className="p-3.5 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-2">
              <div className="flex items-center justify-between">
                <input
                  type="text"
                  value={clause.title}
                  onChange={(e) => onUpdateClause(clause.id, 'title', e.target.value.toUpperCase())}
                  className="font-bold text-slate-900 text-xs bg-transparent border-b border-dashed border-slate-300 focus:border-blue-500 outline-none uppercase w-2/3"
                />
                <button
                  type="button"
                  onClick={() => onRemoveClause(clause.id)}
                  className="text-rose-600 hover:text-rose-800 hover:bg-rose-50 p-1 rounded-lg transition"
                  title="Remove Clause"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              <textarea
                rows={2}
                value={clause.content}
                onChange={(e) => onUpdateClause(clause.id, 'content', e.target.value)}
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:bg-white focus:ring-2 focus:ring-blue-500 outline-none transition"
              />
            </div>
          ))}
        </div>
      )}

      {/* Add New Custom Clause Box */}
      <div className="p-4 bg-slate-50 rounded-xl border border-dashed border-slate-300 space-y-3">
        <div className="flex items-center justify-between">
          <div className="font-bold text-slate-800 text-xs uppercase tracking-wide flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5 text-blue-700" />
            <span>Add Custom Legal Clause (Optional)</span>
          </div>
          <span className="text-[10px] text-blue-700 font-bold bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
            Powered by Gemini AI
          </span>
        </div>

        {/* Quick Clause Presets */}
        <div>
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
            Quick Standard Presets (Click to Auto-fill):
          </span>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_CLAUSE_PRESETS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectPreset(p)}
                className="text-[10px] font-semibold px-2 py-1 rounded-md bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-300 transition shadow-2xs"
              >
                + {p.title}
              </button>
            ))}
          </div>
        </div>

        {statusMsg && (
          <div className={`flex items-center gap-2 p-2.5 rounded-lg text-xs font-semibold ${
            statusMsg.type === 'success' 
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' 
              : statusMsg.type === 'error'
              ? 'bg-rose-50 text-rose-800 border border-rose-200'
              : 'bg-blue-50 text-blue-800 border border-blue-200'
          }`}>
            {statusMsg.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : statusMsg.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            ) : (
              <Loader2 className="w-4 h-4 text-blue-600 animate-spin shrink-0" />
            )}
            <span>{statusMsg.text}</span>
          </div>
        )}
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value.toUpperCase())}
            placeholder="CLAUSE TITLE (E.G. BANK SIGNING LIMITS, LOCK-IN PERIOD)"
            className="px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-xs font-semibold uppercase focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          <input
            type="text"
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
            placeholder="Short intent description for AI drafter..."
            className="px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>

        <textarea
          rows={3}
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          placeholder="Legal clause text (type manually or click 'Draft with AI')..."
          className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
        />

        <div className="flex items-center justify-between gap-2 pt-1">
          <button
            type="button"
            onClick={handleAiDraftClause}
            disabled={!newTitle.trim() || isAiDrafting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 disabled:opacity-50 text-xs font-bold transition"
          >
            {isAiDrafting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            <span>{isAiDrafting ? 'Drafting with AI...' : 'Draft with AI'}</span>
          </button>

          <button
            type="button"
            onClick={handleAddManual}
            disabled={!newTitle.trim() || !newContent.trim()}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-blue-700 hover:bg-blue-800 disabled:bg-slate-300 text-white text-xs font-bold transition shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add to Deed</span>
          </button>
        </div>
      </div>

    </div>
  );
};
