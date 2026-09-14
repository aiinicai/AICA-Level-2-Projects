import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Sliders, Play, Plus, Code, Sparkles } from 'lucide-react';

interface MappingRule {
  id: number;
  pattern: string;
  target_classification: string;
  target_statement: string;
  note_number: string;
  current_non_current: string;
}

export const RuleStudioPage: React.FC = () => {
  const [rules, setRules] = useState<MappingRule[]>([]);
  const [testText, setTestText] = useState<string>('Interest Income on Bank Fixed Deposit');
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState<boolean>(false);
  const [classifications, setClassifications] = useState<string[]>([]);
  
  // New rule form
  const [newPattern, setNewPattern] = useState<string>('');
  const [newClass, setNewClass] = useState<string>('Other Income');
  const [newStatement, setNewStatement] = useState<string>('Profit & Loss');
  const [newNote, setNewNote] = useState<string>('13');
  const [savingRule, setSavingRule] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    loadRulesData();
  }, []);

  const loadRulesData = async () => {
    try {
      const [rulesRes, classRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/api/rules').then(r => r.ok ? r.json() : []).catch(() => []),
        api.getClassifications()
      ]);
      setRules(rulesRes);
      setClassifications(classRes.classifications);
      runTest('Interest Income on Bank Fixed Deposit');
    } catch (err) {
      console.error(err);
    }
  };

  const runTest = async (text: string) => {
    setTesting(true);
    try {
      const formData = new FormData();
      formData.append('test_text', text);
      const res = await fetch('http://127.0.0.1:8000/api/rules/test', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setTesting(false);
    }
  };

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPattern.trim()) return;
    setSavingRule(true);
    setMessage(null);
    try {
      await api.saveRule({
        pattern: newPattern,
        target_classification: newClass,
        target_statement: newStatement,
        note_number: newNote,
        current_non_current: newStatement === 'Balance Sheet' ? 'Current' : 'P&L'
      });
      setMessage(`Rule saved for pattern "${newPattern}"!`);
      setNewPattern('');
      loadRulesData();
    } catch (err: any) {
      setMessage(`Error: ${err.message || 'Failed to save rule'}`);
    } finally {
      setSavingRule(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-400 rounded-lg">
            <Sliders className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-black text-[#1B365D] dark:text-blue-400 flex items-center gap-2">
              Rule & Keyword Tuning Studio
              <span className="text-[10px] bg-orange-600 text-white font-extrabold px-2 py-0.5 rounded uppercase">
                Google AI Studio Parameters Style
              </span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Configure deterministic regex patterns and test rule matching logic in real-time
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Rule Sandbox & Simulator (Col 5) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Sandbox Input Box */}
          <div className="studio-card p-5 space-y-4">
            <div className="flex items-center gap-2 text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider">
              <Sparkles className="w-4 h-4 text-orange-600" /> Interactive Rule Sandbox
            </div>
            
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Enter any Trial Balance ledger string below to simulate how the rule engine will map it:
            </p>

            <div className="flex gap-2">
              <input
                type="text"
                value={testText}
                onChange={(e) => setTestText(e.target.value)}
                placeholder="e.g. Interest on Machinery Loan"
                className="studio-input text-xs font-medium flex-1"
              />
              <button
                onClick={() => runTest(testText)}
                disabled={testing}
                className="ca-button-primary text-xs py-1.5 px-3 flex items-center gap-1.5"
              >
                <Play className="w-3.5 h-3.5" /> Test Rule
              </button>
            </div>

            {/* Simulated Result Card */}
            {testResult && (
              <div className="p-4 bg-slate-900 text-white rounded-lg space-y-2 border border-slate-800 font-mono text-xs">
                <div className="text-slate-400 text-[11px] uppercase tracking-wider border-b border-slate-800 pb-1">
                  Target Classification Result:
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">Input String:</span>
                  <span className="text-amber-400 font-bold">{testResult.input_text}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">Suggested Classification:</span>
                  <span className="text-emerald-400 font-extrabold">{testResult.matched_classification}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">Target Statement:</span>
                  <span className="text-blue-400 font-bold">{testResult.target_statement}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-300">Note Reference:</span>
                  <span className="text-orange-400 font-bold">Note {testResult.note_number}</span>
                </div>
              </div>
            )}
          </div>

          {/* Add New Custom Rule Form */}
          <div className="studio-card p-5 space-y-3">
            <h3 className="text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider flex items-center gap-2">
              <Plus className="w-4 h-4 text-orange-600" /> Create Custom Keyword Rule
            </h3>

            {message && (
              <div className="p-2 bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 text-xs rounded border border-emerald-200 dark:border-emerald-800">
                {message}
              </div>
            )}

            <form onSubmit={handleAddRule} className="space-y-3">
              <div>
                <label className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Regex Keyword Pattern:
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. bonus payable|commission"
                  value={newPattern}
                  onChange={(e) => setNewPattern(e.target.value)}
                  className="studio-input w-full text-xs font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Target Statement:
                  </label>
                  <select
                    value={newStatement}
                    onChange={(e) => setNewStatement(e.target.value)}
                    className="studio-input w-full text-xs font-bold"
                  >
                    <option value="Balance Sheet">Balance Sheet</option>
                    <option value="Profit & Loss">Profit & Loss</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Note No.:
                  </label>
                  <input
                    type="text"
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    className="studio-input w-full text-xs font-bold"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Target Schedule III Line:
                </label>
                <select
                  value={newClass}
                  onChange={(e) => setNewClass(e.target.value)}
                  className="studio-input w-full text-xs font-bold"
                >
                  {classifications.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={savingRule}
                className="ca-button-primary w-full text-xs py-2 mt-2"
              >
                {savingRule ? 'Saving Rule...' : 'Save & Append Rule to DB'}
              </button>
            </form>
          </div>
        </div>

        {/* RIGHT COLUMN: Active Rule Inspection Panel (Col 7) */}
        <div className="lg:col-span-7 studio-card p-5 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
            <h2 className="text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider flex items-center gap-2">
              <Code className="w-4 h-4 text-orange-600" /> Active Keyword Rule Database (Priority Order)
            </h2>
            <span className="text-xs font-mono font-bold text-slate-500">{rules.length} Rules Active</span>
          </div>

          <div className="overflow-y-auto max-h-[600px] border border-slate-200 dark:border-slate-800 rounded-lg">
            <table className="ca-table">
              <thead className="sticky top-0 z-10">
                <tr>
                  <th className="w-12 text-center">#</th>
                  <th>Regex Pattern</th>
                  <th>Target Line Item</th>
                  <th>Statement</th>
                  <th className="text-center">Note</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule, index) => (
                  <tr key={rule.id || index}>
                    <td className="text-center font-mono text-slate-400 text-xs">{index + 1}</td>
                    <td className="font-mono text-xs font-bold text-orange-600 dark:text-orange-400">
                      {rule.pattern}
                    </td>
                    <td className="font-semibold text-slate-800 dark:text-slate-200">
                      {rule.target_classification}
                    </td>
                    <td className="text-xs font-bold text-blue-600 dark:text-blue-400">
                      {rule.target_statement}
                    </td>
                    <td className="text-center font-mono font-bold text-slate-700 dark:text-slate-300">
                      {rule.note_number}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
