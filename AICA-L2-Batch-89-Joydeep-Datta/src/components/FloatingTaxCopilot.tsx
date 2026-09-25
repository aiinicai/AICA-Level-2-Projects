import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  MessageSquare,
  X,
  Send,
  Loader2,
  ChevronDown,
  User,
  Scale,
  ShieldCheck,
  Minimize2,
  Maximize2,
  RotateCcw,
} from 'lucide-react';
import { EmployeeMaster, EmployeeDeclaration, TaxConfig } from '../types/payroll';
import { computeTaxBreakdown } from '../utils/taxEngine';
import { formatInr } from '../utils/payrollEngine';

interface FloatingTaxCopilotProps {
  employees: EmployeeMaster[];
  declarations: EmployeeDeclaration[];
  taxConfig: TaxConfig;
  currentMonth: number;
  activeEmployeeCode?: string;
}

export const FloatingTaxCopilot: React.FC<FloatingTaxCopilotProps> = ({
  employees,
  declarations,
  taxConfig,
  currentMonth,
  activeEmployeeCode,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCode, setSelectedCode] = useState<string>(
    activeEmployeeCode || (employees.length > 0 ? employees[0].employeeCode : '')
  );
  const [inputVal, setInputVal] = useState('');
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'model'; text: string }>>([
    {
      role: 'model',
      text: `Hello! I am your AI Indian Tax Copilot for FY ${taxConfig.financialYear} (AY 2026-27). Ask me anything about salary structuring, Old vs New tax regime trade-offs, HRA exemptions, Section 80C/80D limits, or TDS calculations.`,
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Sync selected code if activeEmployeeCode prop changes
  useEffect(() => {
    if (activeEmployeeCode && activeEmployeeCode !== selectedCode) {
      setSelectedCode(activeEmployeeCode);
    }
  }, [activeEmployeeCode]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  // Scroll to bottom on new message
  useEffect(() => {
    if (isOpen) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading, isOpen]);

  const currentEmp = employees.find((e) => e.employeeCode === selectedCode) || employees[0];
  const currentDecl = declarations.find((d) => d.employeeCode === selectedCode);

  const projectedAnnualBasic = currentEmp ? currentEmp.basicMonthly * 12 : 0;
  const projectedAnnualHra = currentEmp ? currentEmp.hraMonthly * 12 : 0;
  const projectedAnnualGross = currentEmp
    ? (currentEmp.basicMonthly +
        currentEmp.hraMonthly +
        currentEmp.conveyanceAllowanceMonthly +
        currentEmp.childrenEducationAllowanceMonthly +
        currentEmp.ltaMonthly +
        currentEmp.specialAllowanceMonthly +
        currentEmp.otherAllowanceMonthly) *
        12 +
      currentEmp.variablePayAnnual +
      currentEmp.joiningBonus
    : 0;

  const annualPf = currentEmp
    ? currentEmp.pfApplicable === 'Y'
      ? (currentEmp.pfWageCeilingApplied === 'Y' ? Math.min(currentEmp.basicMonthly, 15000) : currentEmp.basicMonthly) *
        0.12 *
        12
      : 0
    : 0;

  const remainingMonths = 12 - currentMonth + 1;

  const oldBreakdown = currentEmp
    ? computeTaxBreakdown(
        currentEmp,
        currentDecl,
        taxConfig,
        'Old',
        projectedAnnualGross,
        projectedAnnualBasic,
        projectedAnnualHra,
        annualPf,
        remainingMonths,
        0
      )
    : null;

  const newBreakdown = currentEmp
    ? computeTaxBreakdown(
        currentEmp,
        currentDecl,
        taxConfig,
        'New',
        projectedAnnualGross,
        projectedAnnualBasic,
        projectedAnnualHra,
        annualPf,
        remainingMonths,
        0
      )
    : null;

  const handleSendMessage = async (textToSend?: string) => {
    const q = (textToSend || inputVal).trim();
    if (!q || isLoading) return;

    const newMsgs = [...messages, { role: 'user' as const, text: q }];
    setMessages(newMsgs);
    setInputVal('');
    setIsLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    try {
      const res = await fetch('/api/ai/tax-ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          question: q,
          employee: currentEmp,
          declaration: currentDecl,
          taxConfig,
          oldBreakdown,
          newBreakdown,
        }),
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: 'model', text: data.answer }]);
    } catch (err: any) {
      clearTimeout(timeoutId);
      let fallbackText = `**Tax Advice for ${currentEmp?.employeeName || 'Employee'}:**\n\n`;
      const qLower = q.toLowerCase();

      if (qLower.includes('hra') || qLower.includes('rent')) {
        fallbackText += `• **HRA Exemption:** Eligible exemption is ${formatInr(
          oldBreakdown?.exemptionsSec10?.hra || 0
        )} under Old Regime. Rent receipts and landlord's PAN (if annual rent > ₹1L) are mandatory.`;
      } else if (qLower.includes('nps') || qLower.includes('80ccd')) {
        fallbackText += `• **Section 80CCD(1B):** An extra ₹50,000 deduction is available for Tier-1 NPS in Old Regime, yielding up to ₹15,600 additional tax savings.`;
      } else if (qLower.includes('80c')) {
        fallbackText += `• **Section 80C:** Maximum limit is ₹1,50,000 in Old Regime. Section 80C is not eligible under the New Regime.`;
      } else {
        const diff = (oldBreakdown?.totalAnnualTaxLiability || 0) - (newBreakdown?.totalAnnualTaxLiability || 0);
        const better = diff > 0 ? 'New Regime' : 'Old Regime';
        fallbackText += `• Old Regime Tax: ${formatInr(oldBreakdown?.totalAnnualTaxLiability || 0)}\n• New Regime Tax: ${formatInr(
          newBreakdown?.totalAnnualTaxLiability || 0
        )}\n**Recommendation:** ${better} saves ${formatInr(Math.abs(diff))} annually.`;
      }

      setMessages((prev) => [...prev, { role: 'model', text: fallbackText }]);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  };

  const quickPrompts = [
    'Old vs New Regime comparison',
    'How is my HRA calculated?',
    'What if I invest ₹50k in NPS?',
    'Can I switch regimes before lock-in?',
  ];

  return (
    <>
      {/* Floating launcher trigger button */}
      {!isOpen && (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2.5 px-4 py-3 bg-gradient-to-r from-indigo-600 via-indigo-700 to-purple-700 hover:from-indigo-500 hover:to-purple-600 text-white rounded-full shadow-xl hover:shadow-2xl transition-all transform hover:-translate-y-0.5 cursor-pointer border border-white/20 print:hidden"
          title="Open AI Tax Copilot"
        >
          <div className="relative">
            <Sparkles className="h-5 w-5 text-amber-300 animate-pulse" />
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
          <span className="text-xs font-bold tracking-wide">AI Tax Copilot</span>
          <span className="px-1.5 py-0.5 text-[9px] font-extrabold uppercase bg-amber-400 text-slate-900 rounded">
            Gemini
          </span>
        </button>
      )}

      {/* Floating Chat Window */}
      {isOpen && (
        <div className="fixed bottom-4 right-4 z-50 w-[95vw] sm:w-[430px] h-[580px] max-h-[90vh] bg-white rounded-2xl shadow-2xl border border-slate-300 flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-5 duration-200 print:hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-3.5 flex items-center justify-between border-b border-indigo-500/20">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-xl bg-indigo-600/40 border border-indigo-400/30 flex items-center justify-center text-amber-300">
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <h3 className="font-bold text-xs text-white">AI Tax Copilot</h3>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/30 text-emerald-300 border border-emerald-400/30 font-semibold">
                    AY 2026–27
                  </span>
                </div>
                <p className="text-[10px] text-slate-300">Statutory Tax & Compensation Advisor</p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() =>
                  setMessages([
                    {
                      role: 'model',
                      text: `Conversation reset. Ask any question regarding Indian Income Tax rules for ${currentEmp.employeeName}.`,
                    },
                  ])
                }
                title="Reset conversation"
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                title="Close Copilot"
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Context Employee Bar */}
          <div className="bg-indigo-50/70 border-b border-indigo-100 px-3 py-1.5 flex items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-1.5 text-indigo-950 truncate">
              <User className="h-3.5 w-3.5 text-indigo-600 shrink-0" />
              <span className="text-[11px] text-indigo-700 font-semibold shrink-0">Context:</span>
              <select
                value={selectedCode}
                onChange={(e) => setSelectedCode(e.target.value)}
                className="text-[11px] font-bold text-indigo-900 bg-white border border-indigo-200 rounded-lg px-2 py-0.5 outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer max-w-[200px] truncate"
              >
                {employees.map((emp) => (
                  <option key={emp.employeeCode} value={emp.employeeCode}>
                    {emp.employeeName} ({emp.employeeCode})
                  </option>
                ))}
              </select>
            </div>
            {currentEmp && (
              <span className="text-[10px] text-slate-500 font-mono shrink-0">
                CTC: {formatInr(currentEmp.annualCtc)}
              </span>
            )}
          </div>

          {/* Chat Messages */}
          <div className="flex-1 p-3.5 overflow-y-auto space-y-2.5 bg-slate-50/60 text-xs">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl p-3 text-xs leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-xs shadow-xs'
                      : 'bg-white border border-slate-200 text-slate-800 rounded-bl-xs shadow-xs whitespace-pre-line'
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white border border-slate-200 rounded-2xl p-2.5 text-xs text-slate-500 flex items-center gap-2 shadow-xs">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                  <span>AI Advisor is reviewing tax rules...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Quick Prompts */}
          <div className="px-3 py-1.5 bg-slate-100/90 border-t border-slate-200 flex items-center gap-1.5 overflow-x-auto text-[10px]">
            <span className="text-slate-400 font-semibold shrink-0">Suggestions:</span>
            {quickPrompts.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSendMessage(prompt)}
                className="px-2 py-0.5 bg-white hover:bg-indigo-50 hover:text-indigo-700 border border-slate-200 rounded-md text-slate-700 transition-colors whitespace-nowrap cursor-pointer shadow-2xs"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Chat Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="p-2.5 bg-white border-t border-slate-200 flex items-center gap-2"
          >
            <div className="relative flex-1 flex items-center min-w-0">
              <input
                ref={inputRef}
                type="text"
                id="floating-copilot-input"
                name="copilotQuestion"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                autoComplete="off"
                placeholder={`Ask tax question for ${currentEmp?.employeeName || 'employee'}...`}
                className="w-full text-xs text-slate-900 placeholder:text-slate-400 bg-white border border-slate-300 rounded-xl pl-3 pr-7 py-2.5 outline-none ring-1 ring-slate-200 focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600 transition-all shadow-xs cursor-text"
              />
              {inputVal && (
                <button
                  type="button"
                  onClick={() => {
                    setInputVal('');
                    inputRef.current?.focus();
                  }}
                  className="absolute right-2 text-slate-400 hover:text-slate-600 p-0.5 rounded cursor-pointer"
                  title="Clear"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={!inputVal.trim() || isLoading}
              className="px-3.5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold rounded-xl transition-colors flex items-center gap-1 shadow-xs cursor-pointer shrink-0"
            >
              <span>Send</span>
              <Send className="h-3 w-3" />
            </button>
          </form>
        </div>
      )}
    </>
  );
};
