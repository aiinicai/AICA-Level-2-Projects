import React, { useState } from 'react';
import { createMappingRule } from '../services/api';
import { Database, Save, Check, Shield } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [rulePattern, setRulePattern] = useState('');
  const [ruleClassification, setRuleClassification] = useState('Trade Receivables');
  const [ruleNote, setRuleNote] = useState('8');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rulePattern) return;
    setSaving(true);
    try {
      await createMappingRule({
        pattern: rulePattern,
        target_classification: ruleClassification,
        target_statement: 'Balance Sheet',
        note_number: ruleNote,
        current_non_current: 'Current'
      });
      setSuccess(true);
      setRulePattern('');
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="border-b border-ca-border pb-4">
        <h1 className="text-xl font-bold text-navy-900 uppercase tracking-tight">APPLICATION SETTINGS & MAPPING RULES DB</h1>
        <p className="text-xs text-ca-muted mt-0.5">Manage SQLite auto-mapping keyword rules and CA firm default parameters.</p>
      </div>

      <div className="ca-card bg-white space-y-4">
        <h3 className="text-xs font-bold text-navy-900 uppercase flex items-center gap-2 border-b border-slate-100 pb-2">
          <Database className="w-4 h-4 text-orange-600" />
          Add Custom Auto-Mapping Keyword Rule (Saved to SQLite `app.db`)
        </h3>

        {success && (
          <div className="p-2.5 bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs rounded font-semibold flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" /> Rule saved to SQLite! Future uploads will automatically use this pattern.
          </div>
        )}

        <form onSubmit={handleAddRule} className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
          <div className="space-y-1 md:col-span-2">
            <label className="font-bold text-navy-900 uppercase">Keyword / Regex Pattern *</label>
            <input
              type="text"
              required
              placeholder="e.g. advance to vendor|supplier deposit"
              className="w-full p-2 border border-ca-border rounded bg-white text-ca-text focus:outline-none focus:border-orange-600"
              value={rulePattern}
              onChange={(e) => setRulePattern(e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <label className="font-bold text-navy-900 uppercase">Target Classification</label>
            <select
              className="w-full p-2 border border-ca-border rounded bg-white font-semibold"
              value={ruleClassification}
              onChange={(e) => setRuleClassification(e.target.value)}
            >
              <option value="Trade Receivables">Trade Receivables</option>
              <option value="Short-term Loans and Advances">Short-term Loans and Advances</option>
              <option value="Other Current Liabilities">Other Current Liabilities</option>
              <option value="Property, Plant and Equipment">Property, Plant and Equipment</option>
              <option value="Revenue from Operations">Revenue from Operations</option>
              <option value="Other Expenses">Other Expenses</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="font-bold text-navy-900 uppercase">Note Number</label>
            <input
              type="text"
              required
              className="w-full p-2 border border-ca-border rounded bg-white font-mono font-bold"
              value={ruleNote}
              onChange={(e) => setRuleNote(e.target.value)}
            />
          </div>

          <div className="md:col-span-4 flex justify-end">
            <button type="submit" disabled={saving} className="ca-button-primary text-xs">
              <Save className="w-4 h-4" />
              {saving ? 'Saving Rule...' : 'Save Mapping Rule'}
            </button>
          </div>
        </form>
      </div>

      <div className="ca-card bg-slate-900 text-white space-y-3">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
          <Shield className="w-5 h-5 text-emerald-400" />
          <h3 className="text-xs font-bold uppercase text-white">Localhost Security & Compliance Status</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3 bg-slate-800 rounded border border-slate-700 space-y-1">
            <span className="text-[10px] text-slate-400 font-bold block uppercase">Cloud AI API Status</span>
            <span className="text-emerald-400 font-bold">DISABLED (100% Deterministic Python)</span>
          </div>

          <div className="p-3 bg-slate-800 rounded border border-slate-700 space-y-1">
            <span className="text-[10px] text-slate-400 font-bold block uppercase">Database Engine</span>
            <span className="text-white font-bold font-mono">SQLite (backend/app.db)</span>
          </div>

          <div className="p-3 bg-slate-800 rounded border border-slate-700 space-y-1">
            <span className="text-[10px] text-slate-400 font-bold block uppercase">Data Privacy</span>
            <span className="text-white font-bold">Local Host Only (Zero Network Egress)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
