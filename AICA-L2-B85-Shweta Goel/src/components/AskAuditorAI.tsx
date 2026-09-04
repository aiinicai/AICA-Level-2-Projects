import React, { useState, useRef, useEffect } from 'react';
import { 
  Sparkles, 
  Send, 
  Bot, 
  User, 
  X, 
  HelpCircle, 
  ChevronRight, 
  BookOpen, 
  Scale, 
  FileCheck 
} from 'lucide-react';
import { AuditModule } from '../types';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface AskAuditorAIProps {
  isOpen: boolean;
  onClose: () => void;
  activeModule: AuditModule;
  currentDocumentData: any;
}

export const AskAuditorAI: React.FC<AskAuditorAIProps> = ({
  isOpen,
  onClose,
  activeModule,
  currentDocumentData,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Hello! I am your **CA Tax & Audit Copilot** powered by Gemini. Ask me any statutory question about this document, GST Rule 46 requirements, Section 194 TDS rates, Section 269ST cash limits, or GSTR-2B reconciliation.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!isOpen) return null;

  const quickPrompts = [
    'Is this invoice eligible for Section 16(2) ITC?',
    'What is the consequence of wrong Place of Supply under Section 77?',
    'How do I calculate interest u/s 201(1A) for short TDS deduction?',
    'Are cash transactions > ₹50,000 reportable in SFT Form 61A?'
  ];

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      // Call backend AI ask endpoint
      const response = await fetch('/api/custom-audit-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: textToSend,
          moduleType: activeModule,
          documentContext: currentDocumentData
        })
      });

      const result = await response.json();
      const assistantMsg: Message = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: result.answer || result.error || 'Unable to process query at this time.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: `ai-err-${Date.now()}`,
          role: 'assistant',
          content: `Tax Copilot statutory analysis: ${err.message || 'Please check network connection.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[460px] bg-white border-l border-slate-200 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
      
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <span>CA Tax &amp; Audit Copilot</span>
              <span className="px-1.5 py-0.2 rounded text-[10px] bg-emerald-50 text-emerald-700 font-mono font-semibold border border-emerald-200">
                Gemini 1.5
              </span>
            </h3>
            <p className="text-[11px] text-slate-500">Contextual Statutory Tax Advice</p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Quick Questions Suggestions */}
      <div className="px-4 py-2.5 bg-slate-50/50 border-b border-slate-100 overflow-x-auto text-[11px] flex gap-1.5 no-scrollbar shrink-0">
        {quickPrompts.slice(0, 2).map((q, i) => (
          <button
            key={i}
            onClick={() => handleSend(q)}
            className="px-2.5 py-1 rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-2xs whitespace-nowrap text-left font-medium transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs bg-slate-50/30">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div className={`max-w-[85%] rounded-2xl p-3.5 space-y-1.5 shadow-2xs ${
              msg.role === 'user'
                ? 'bg-indigo-600 text-white font-medium rounded-tr-none'
                : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none'
            }`}>
              <div className="leading-relaxed whitespace-pre-wrap">
                {msg.content}
              </div>
              <span className={`text-[9px] block text-right font-mono ${
                msg.role === 'user' ? 'text-indigo-200' : 'text-slate-400'
              }`}>
                {msg.timestamp}
              </span>
            </div>

            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-slate-100 border border-slate-200 text-slate-600 flex items-center justify-center shrink-0">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 justify-start items-center text-slate-500 text-xs py-2">
            <div className="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4 animate-spin" />
            </div>
            <div className="bg-white border border-slate-200 p-3 rounded-2xl rounded-tl-none shadow-2xs">
              <span className="italic text-slate-600">Reviewing Indian Tax Statutes &amp; Case Law...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-3.5 border-t border-slate-100 bg-white">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about GSTIN, Sec 194J, 269ST, GSTR-2B..."
            className="flex-1 px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:bg-white transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold transition-all disabled:opacity-50 shadow-xs"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

    </div>
  );
};
