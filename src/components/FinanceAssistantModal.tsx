import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Send,
  X,
  Bot,
  User,
  RefreshCw,
  HelpCircle,
  TrendingDown,
  PiggyBank,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { Account, CategoryBudget, Subscription, Transaction } from '../types/finance';

interface FinanceAssistantModalProps {
  transactions: Transaction[];
  accounts: Account[];
  budgets: CategoryBudget[];
  subscriptions: Subscription[];
  onClose: () => void;
}

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
}

export const FinanceAssistantModal: React.FC<FinanceAssistantModalProps> = ({
  transactions,
  accounts,
  budgets,
  subscriptions,
  onClose
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: `Hello! I am your **DirhamTrack Insights Chatbot**, powered by Gemini.\n\nI have live access to your financial records:\n- 📊 **${transactions.length} Transactions** recorded\n- 💳 **AED ${accounts.filter(a => a.type === 'bank' || a.type === 'cash').reduce((s, a) => s + a.balance, 0).toLocaleString()}** liquid balance\n- 🎯 **${budgets.length} Category Budgets** & limits\n- 📅 **${subscriptions.length} Recurring Bills**\n\nAsk me anything about your finances:\n- **"Where did I overspend this month?"**\n- **"How can I save AED 2,000?"**\n- **"Review my credit card debt & interest risk"**\n- **"Breakdown my spending pace & bills"**`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);

  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendQuery = async (queryToSend?: string) => {
    const q = (queryToSend || inputQuery).trim();
    if (!q || isLoading) return;

    const userMsg: Message = {
      id: `user_${Date.now()}`,
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/ai/finance-assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          history: messages.slice(-6).map(m => ({ role: m.sender, text: m.text })),
          context: {
            transactions,
            accounts,
            budgets,
            subscriptions
          }
        })
      });

      const json = await res.json();
      if (json.success && json.answer) {
        const assistantMsg: Message = {
          id: `bot_${Date.now()}`,
          sender: 'assistant',
          text: json.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, assistantMsg]);
      } else {
        const errorMsg: Message = {
          id: `err_${Date.now()}`,
          sender: 'assistant',
          text: `⚠️ ${json.error || 'Unable to generate response right now. Please try again.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, errorMsg]);
      }
    } catch (err: any) {
      const errorMsg: Message = {
        id: `err_${Date.now()}`,
        sender: 'assistant',
        text: `⚠️ Network error: ${err.message || 'Failed to reach AI Finance Assistant'}.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const sampleQuestions = [
    'Where did I overspend?',
    'How can I save AED 2,000?',
    'Compare my monthly expenses',
    'Am I carrying high credit card debt?',
    'Analyze my grocery and food spend'
  ];

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/85 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl p-4 sm:p-6 shadow-2xl flex flex-col h-[94vh] sm:h-[85vh] max-h-[94vh] sm:max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-3.5 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-500/20 to-teal-500/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">AI Insights Chatbot</h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 flex items-center gap-1 font-mono">
                  <Sparkles className="w-3 h-3 text-indigo-400" />
                  Gemini AI
                </span>
              </div>
              <p className="text-xs text-slate-400">Answers any question based on your actual ledger, budgets &amp; reports</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Quick Questions Strip */}
        <div className="py-2 flex items-center gap-1.5 overflow-x-auto scrollbar-none shrink-0 border-b border-slate-800/80">
          <span className="text-[11px] text-slate-400 font-semibold whitespace-nowrap pl-1">Ask AI:</span>
          {sampleQuestions.map((q, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSendQuery(q)}
              className="py-1 px-2.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-teal-500/40 text-[11px] font-medium text-slate-300 hover:text-white transition whitespace-nowrap cursor-pointer shrink-0"
            >
              {q}
            </button>
          ))}
        </div>

        {/* Chat History Messages Feed */}
        <div className="flex-1 overflow-y-auto py-4 space-y-3.5 pr-1">
          {messages.map(msg => {
            const isUser = msg.sender === 'user';
            return (
              <div
                key={msg.id}
                className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}
              >
                <div
                  className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold ${
                    isUser
                      ? 'bg-teal-500 text-slate-950'
                      : 'bg-slate-800 text-teal-400 border border-slate-700'
                  }`}
                >
                  {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                    isUser
                      ? 'bg-teal-500 text-slate-950 font-semibold rounded-tr-none'
                      : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-tl-none space-y-2'
                  }`}
                >
                  <div className="whitespace-pre-line font-sans">
                    {msg.text}
                  </div>
                  <span
                    className={`block text-[9px] mt-1 ${
                      isUser ? 'text-slate-900/70 text-right' : 'text-slate-500'
                    }`}
                  >
                    {msg.timestamp}
                  </span>
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex items-start gap-2.5">
              <div className="w-7 h-7 rounded-xl bg-slate-800 text-teal-400 border border-slate-700 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-slate-950 border border-slate-800 rounded-2xl rounded-tl-none p-3.5 text-xs text-slate-400 flex items-center gap-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-teal-400" />
                <span>Analyzing your financial ledger with Gemini AI...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="pt-3 border-t border-slate-800 shrink-0">
          <form
            onSubmit={e => {
              e.preventDefault();
              handleSendQuery();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={e => setInputQuery(e.target.value)}
              placeholder="Ask about spending, cuts, savings (e.g. 'How can I save AED 2,000?')..."
              className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 font-sans"
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || isLoading}
              className="p-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 font-bold transition cursor-pointer shadow shrink-0"
              title="Send to AI Assistant"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
