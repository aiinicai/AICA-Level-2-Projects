import React, { useState } from 'react';
import { X, Sparkles, Send, Bot, User, CheckCircle2, ShieldCheck } from 'lucide-react';
import { EntityDetails, LedgerItem, PLStatement, ReconciliationReport } from '../types/accounting';

interface AiAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  entity: EntityDetails;
  ledgers: LedgerItem[];
  plStatement: PLStatement;
  reconciliation: ReconciliationReport;
}

export const AiAssistantModal: React.FC<AiAssistantModalProps> = ({
  isOpen,
  onClose,
  entity,
  ledgers,
  plStatement,
  reconciliation,
}) => {
  const [messages, setMessages] = useState<{ role: 'ai' | 'user'; content: string }[]>([
    {
      role: 'ai',
      content: `Hello! I am your AI Chartered Accountant & Audit Assistant for **${entity.name}**. I can analyze your financial ratios, check ICAI non-corporate presentation norms, recommend tax audit clauses, and suggest treatments for ambiguous accounts. How can I assist you today?`,
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleGenerateAuditNotes = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/ai/audit-notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityDetails: entity,
          reconciliation,
          plStatement,
          ledgerCount: ledgers.length,
        }),
      });

      if (!response.ok) throw new Error('AI Server error');
      const data = await response.json();

      let formatted = `### Audit Observations & Financial Analysis for ${entity.name}\n\n`;
      if (data.summary) formatted += `**Executive Summary:** ${data.summary}\n\n`;
      if (data.observations && Array.isArray(data.observations)) {
        formatted += `**Key Observations:**\n` + data.observations.map((o: string) => `• ${o}`).join('\n') + '\n\n';
      }
      if (data.complianceNotes && Array.isArray(data.complianceNotes)) {
        formatted += `**Statutory & ICAI Compliance:**\n` + data.complianceNotes.map((c: string) => `• ${c}`).join('\n');
      }

      setMessages(prev => [...prev, { role: 'ai', content: formatted }]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'ai',
          content: 'Unable to generate audit notes. Please try again.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userText = inputMessage.trim();
    setInputMessage('');
    setMessages(prev => [...prev, { role: 'user', content: userText }]);
    setIsLoading(true);

    try {
      const response = await fetch('/api/ai/audit-notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityDetails: entity,
          reconciliation,
          plStatement,
          userQuestion: userText,
        }),
      });

      if (!response.ok) throw new Error('AI Server error');
      const data = await response.json();

      const aiReply = data.answer || data.summary || (data.observations ? data.observations.join('\n') : 'Analysis complete.');
      setMessages(prev => [...prev, { role: 'ai', content: aiReply }]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'ai', content: 'Apologies, I encountered an issue processing your query. Please try again.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#141414]/70 backdrop-blur-xs p-4 animate-in fade-in" id="modal-ai-assistant">
      <div className="bg-[#F5F4F0] max-w-2xl w-full h-[620px] shadow-2xl border border-[#141414] flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="bg-[#141414] text-[#E4E3E0] p-3.5 px-4 flex items-center justify-between border-b border-[#141414]">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 bg-[#282828] border border-white/20 flex items-center justify-center">
              <Sparkles className="w-3.5 h-3.5 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-xs uppercase tracking-wider font-mono text-white">AI CA & Audit Assistant</h3>
              <p className="text-[10.5px] text-[#A3A29E] font-mono">Built-in ICAI Rule Engine • Works Offline</p>
            </div>
          </div>
          <button onClick={onClose} className="text-[#A3A29E] hover:text-white p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Quick Prompts Strip */}
        <div className="bg-[#ECEAE5] px-3.5 py-2 border-b border-[#141414]/20 flex items-center gap-2 overflow-x-auto text-[11px]">
          <span className="font-bold font-mono text-[#141414] shrink-0 text-[10px] uppercase">ACTIONS:</span>
          <button
            onClick={handleGenerateAuditNotes}
            disabled={isLoading}
            className="px-2 py-0.5 bg-white hover:bg-[#E4E3E0] text-[#141414] border border-[#141414]/30 font-mono text-[10.5px] font-bold transition shrink-0"
          >
            [AUDIT OBSERVATIONS]
          </button>
          <button
            onClick={() => setInputMessage('Check for any 40A(3) cash expense or 269ST risks in trial balance')}
            className="px-2 py-0.5 bg-white hover:bg-[#E4E3E0] text-[#141414] border border-[#141414]/30 font-mono text-[10.5px] font-bold transition shrink-0"
          >
            [TAX AUDIT CHECKLIST]
          </button>
        </div>

        {/* Chat History */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3 text-xs bg-white">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex gap-2.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {m.role === 'ai' && (
                <div className="w-6 h-6 bg-[#141414] text-white flex items-center justify-center shrink-0 mt-0.5 text-[10px] font-mono font-bold">
                  AI
                </div>
              )}
              <div
                className={`max-w-[85%] p-3 leading-relaxed whitespace-pre-wrap font-sans text-xs border ${
                  m.role === 'user'
                    ? 'bg-[#141414] text-white border-[#141414] font-medium'
                    : 'bg-[#F5F4F0] text-[#141414] border-[#141414]/20'
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-2 justify-start items-center text-xs text-[#5E5E5E] font-mono italic">
              <Bot className="w-3.5 h-3.5 animate-spin" />
              <span>Analyzing financial statements...</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSendMessage} className="p-2.5 border-t border-[#141414]/20 bg-[#ECEAE5] flex items-center gap-2">
          <input
            type="text"
            placeholder="Ask anything (e.g. 'How should I treat partner salary vs interest on capital?')..."
            value={inputMessage}
            onChange={e => setInputMessage(e.target.value)}
            className="flex-1 bg-white border border-[#141414]/30 px-3 py-1.5 text-xs font-mono focus:outline-none focus:border-[#141414]"
          />
          <button
            type="submit"
            disabled={isLoading || !inputMessage.trim()}
            className="px-3.5 py-1.5 bg-[#141414] hover:bg-[#282828] text-white font-mono font-bold text-xs border border-[#141414] transition disabled:opacity-40"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

      </div>
    </div>
  );
};
