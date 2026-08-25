import React, { useState, useRef, useEffect } from 'react';
import { 
  X, 
  Send, 
  MessageSquareText, 
  Copy, 
  Check, 
  User, 
  Bot 
} from 'lucide-react';
import { AuditReportData, ChatMessage } from '../types';
import { handleOfflineChatQuery } from '../engine/offlineChatAssistant';

interface AuditChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  report: AuditReportData | null;
  isOfflineMode?: boolean;
}

export const AuditChatDrawer: React.FC<AuditChatDrawerProps> = ({
  isOpen,
  onClose,
  report,
  isOfflineMode = true,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      content: `Hello, I am your Senior CA & Technical Compliance Consultant.

I have full context of the audited financial statements and findings for **${
        report?.summary?.entityName || 'the uploaded entity'
      }**.

How can I assist you with this engagement? You can ask me to:
- Draft an **Audit Query Memo** to management for any observed discrepancy
- Draft specific **Management Representation Letter (MRL)** clauses
- Assess **CARO 2020** or **Schedule III** non-compliance penalties
- Prepare draft wording for a **Modified / Qualified Audit Opinion** or **Emphasis of Matter (EoM)**`,
      suggestions: [
        'Draft Audit Query Memo for CFO on KMP Remuneration gap',
        'Draft MRL clause for Contingent Liabilities under Ind AS 37',
        'What is CARO 2020 impact of the fixed asset / PPE discrepancy?',
        'Draft Qualified Opinion paragraph for unresolved casting errors',
      ],
    },
  ]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  if (!isOpen) return null;

  const handleSendMessage = async (textToSend?: string) => {
    const query = textToSend || input.trim();
    if (!query || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      content: query,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      if (isOfflineMode) {
        // Fast offline deterministic assistant
        setTimeout(() => {
          const offlineResp = handleOfflineChatQuery(
            query,
            report,
            messages.slice(1).map(m => ({ sender: m.sender, content: m.content }))
          );

          const botMsg: ChatMessage = {
            id: `bot-${Date.now()}`,
            sender: 'assistant',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            content: offlineResp.reply,
            suggestions: offlineResp.suggestedFollowUps,
          };
          setMessages((prev) => [...prev, botMsg]);
          setLoading(false);
        }, 300);
      } else {
        const response = await fetch('/api/audit/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: query,
            contextReport: report,
            conversationHistory: messages.slice(1), // Exclude initial welcome
          }),
        });

        const data = await response.json();

        if (data.reply) {
          const botMsg: ChatMessage = {
            id: `bot-${Date.now()}`,
            sender: 'assistant',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            content: data.reply,
          };
          setMessages((prev) => [...prev, botMsg]);
        } else {
          throw new Error(data.error || 'Failed to get consultation response');
        }
        setLoading(false);
      }
    } catch (err: any) {
      // Automatic fallback to offline engine if server is unreachable
      const offlineResp = handleOfflineChatQuery(
        query,
        report,
        messages.slice(1).map(m => ({ sender: m.sender, content: m.content }))
      );

      const botMsg: ChatMessage = {
        id: `bot-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: offlineResp.reply,
        suggestions: offlineResp.suggestedFollowUps,
      };
      setMessages((prev) => [...prev, botMsg]);
      setLoading(false);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex justify-end">
      <div className="bg-white w-full max-w-xl h-full flex flex-col border-l-2 border-[#141414] animate-slideLeft shadow-dense">
        {/* Drawer Header */}
        <div className="bg-[#141414] text-white p-4 flex items-center justify-between border-b border-[#141414]">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 bg-[#00FF00] flex items-center justify-center text-[#141414] font-bold">
              <MessageSquareText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-xs sm:text-sm uppercase tracking-tight text-white font-mono">
                CA Technical & Audit Consultation
              </h3>
              <p className="text-[10px] text-neutral-400 font-serif italic">
                Ind AS Interpretation, Memo Drafting & ICAI Standards
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-white p-1 hover:bg-neutral-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message Log */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-[#E4E3E0]">
          {messages.map((msg) => {
            const isUser = msg.sender === 'user';
            return (
              <div
                key={msg.id}
                className={`flex items-start space-x-2 ${
                  isUser ? 'flex-row-reverse space-x-reverse' : ''
                }`}
              >
                <div
                  className={`w-6 h-6 flex items-center justify-center shrink-0 text-xs font-mono font-bold border border-[#141414] ${
                    isUser
                      ? 'bg-[#141414] text-white'
                      : 'bg-[#00FF00] text-[#141414]'
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                <div
                  className={`max-w-[85%] p-3.5 text-xs border border-[#141414] shadow-dense-sm ${
                    isUser
                      ? 'bg-[#141414] text-white font-sans'
                      : 'bg-white text-[#141414]'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1 opacity-70 text-[9px] font-mono uppercase">
                    <span>{isUser ? 'Auditor' : 'CA Technical Advisor'}</span>
                    <span>{msg.timestamp}</span>
                  </div>

                  <div className="whitespace-pre-wrap font-serif italic text-xs leading-snug">
                    {msg.content}
                  </div>

                  {/* Copy Button for Assistant replies */}
                  {!isUser && (
                    <div className="mt-2.5 pt-2 border-t border-[#141414]/20 flex justify-end">
                      <button
                        onClick={() => handleCopy(msg.id, msg.content)}
                        className="inline-flex items-center space-x-1 text-[10px] font-mono font-bold uppercase text-[#141414] hover:underline transition"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <Check className="w-3 h-3 text-green-700" />
                            <span className="text-green-700">COPIED</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span>COPY DRAFT</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}

                  {/* Quick Suggestions Chips */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-[#141414]/20 space-y-1">
                      <span className="text-[9px] font-mono font-bold text-[#141414]/70 uppercase tracking-wider block">
                        RECOMMENDED PROMPTS:
                      </span>
                      {msg.suggestions.map((sug, sIdx) => (
                        <button
                          key={sIdx}
                          onClick={() => handleSendMessage(sug)}
                          className="w-full text-left p-1.5 bg-[#F9F9F7] hover:bg-white text-[#141414] border border-[#141414] text-[10px] font-mono uppercase transition"
                        >
                          {sug}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex items-start space-x-2">
              <div className="w-6 h-6 bg-[#00FF00] text-[#141414] border border-[#141414] flex items-center justify-center shrink-0">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="bg-white border border-[#141414] p-3 text-xs text-[#141414] flex items-center space-x-2 font-mono shadow-dense-sm">
                <div className="w-1.5 h-1.5 bg-[#141414] animate-bounce" />
                <div className="w-1.5 h-1.5 bg-[#141414] animate-bounce [animation-delay:0.2s]" />
                <div className="w-1.5 h-1.5 bg-[#141414] animate-bounce [animation-delay:0.4s]" />
                <span className="text-[10px] uppercase">Consulting Ind AS Technical Standards & Drafting response...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 bg-white border-t border-[#141414]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center space-x-1.5"
          >
            <input
              type="text"
              placeholder="Ask CA question or request draft memo / MRL clause..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 text-xs p-2 border border-[#141414] bg-[#F9F9F7] font-mono text-[#141414] focus:outline-none"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="p-2 bg-[#141414] text-white hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition border border-[#141414]"
            >
              <Send className="w-4 h-4 text-[#00FF00]" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

