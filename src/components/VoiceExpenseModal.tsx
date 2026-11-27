import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  X,
  Sparkles,
  Check,
  AlertCircle,
  HelpCircle,
  Volume2,
  Calendar,
  CreditCard,
  RefreshCw,
  Zap,
  Globe,
  Keyboard,
  ArrowRight
} from 'lucide-react';
import { Account, ExpenseCategory, Transaction } from '../types/finance';
import { parseVoiceExpenseRules } from '../services/voiceRulesEngine';

interface VoiceExpenseModalProps {
  accounts: Account[];
  onClose: () => void;
  onAddTransaction: (tx: Partial<Transaction>) => void;
  onOpenVoiceGuide?: () => void;
}

export const VoiceExpenseModal: React.FC<VoiceExpenseModalProps> = ({
  accounts,
  onClose,
  onAddTransaction,
  onOpenVoiceGuide
}) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);
  const [language, setLanguage] = useState<'en-US' | 'hi-IN'>('en-US');
  const [engineBadge, setEngineBadge] = useState<{ type: 'rules' | 'gemini'; label: string; timeMs?: number } | null>(null);
  const [isSpeechSupported, setIsSpeechSupported] = useState(true);

  // Extracted confirmation state before posting
  const [extractedData, setExtractedData] = useState<{
    amount: number;
    merchant: string;
    category: ExpenseCategory;
    matchedAccountId: string | null;
    accountName: string;
    type: 'expense' | 'income';
    date: string;
    notes: string;
  } | null>(null);

  const recognitionRef = useRef<any>(null);
  const transcriptRef = useRef<string>('');

  // Keep transcriptRef in sync
  useEffect(() => {
    transcriptRef.current = transcript;
  }, [transcript]);

  // Initialize Web Speech API
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSpeechSupported(false);
      return;
    }

    setIsSpeechSupported(true);
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = language;

    recognition.onstart = () => {
      setIsListening(true);
      setErrorMessage(null);
    };

    recognition.onresult = (event: any) => {
      let fullTranscript = '';
      for (let i = 0; i < event.results.length; i++) {
        fullTranscript += event.results[i][0].transcript;
      }
      transcriptRef.current = fullTranscript;
      setTranscript(fullTranscript);
    };

    recognition.onerror = (event: any) => {
      if (event.error === 'not-allowed') {
        setErrorMessage(
          'Microphone permission was denied. Tap the lock/permissions icon in your address bar to enable mic, or use the typed command fallback below.'
        );
      } else if (event.error !== 'no-speech') {
        setErrorMessage(`Speech recognition notice: ${event.error}. You can also type commands below.`);
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      const spokenText = transcriptRef.current?.trim();
      if (spokenText) {
        handleProcessVoiceText(spokenText);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
    };
  }, [language]);

  const handleLanguageChange = (lang: 'en-US' | 'hi-IN') => {
    setLanguage(lang);
    if (recognitionRef.current) {
      recognitionRef.current.lang = lang;
    }
  };

  const startListening = async () => {
    setErrorMessage(null);
    setTranscript('');
    transcriptRef.current = '';
    setExtractedData(null);
    setEngineBadge(null);

    // Request getUserMedia first to trigger browser permission dialog if not yet granted
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
      } catch (err: any) {
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          setErrorMessage(
            'Microphone access is not allowed by browser settings. Please allow mic in browser permissions or type your command below.'
          );
          setIsListening(false);
          return;
        }
      }
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.lang = language;
        recognitionRef.current.start();
      } catch (e) {
        try {
          recognitionRef.current.stop();
          setTimeout(() => {
            try {
              recognitionRef.current.lang = language;
              recognitionRef.current.start();
            } catch (err) {}
          }, 150);
        } catch (err) {
          setIsListening(false);
        }
      }
    } else {
      setErrorMessage('Speech recognition is not supported in this browser. Please type your command below.');
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    setIsListening(false);
  };

  /**
   * Primary processing pipeline:
   * 1. Evaluates client-side JavaScript Rules Engine instantly (< 1ms).
   * 2. If valid amount and details are extracted, IMMEDIATELY presents confirmation card without server latency.
   * 3. Falls back to Gemini AI strictly when JS rules cannot extract required fields.
   */
  const handleProcessVoiceText = async (textToProcess?: string) => {
    const text = (textToProcess || transcript).trim();
    if (!text) {
      setErrorMessage('Please speak or type a transaction command first.');
      return;
    }

    setErrorMessage(null);

    // 1. Instant Client-Side Rules Engine Execution (< 1ms)
    const localResult = parseVoiceExpenseRules(text, accounts);

    if (localResult.success && localResult.amount > 0) {
      setExtractedData({
        amount: localResult.amount,
        merchant: localResult.merchant,
        category: localResult.category,
        matchedAccountId: localResult.matchedAccountId,
        accountName: localResult.accountName,
        type: localResult.type,
        date: localResult.date,
        notes: localResult.notes
      });
      setEngineBadge({
        type: 'rules',
        label: `⚡ Instant JS Rules Engine (${localResult.debugTimingMs || 1}ms)`,
        timeMs: localResult.debugTimingMs
      });
      setIsProcessing(false);
      return;
    }

    // 2. Strict Fallback: Gemini AI when JS engine cannot comprehend the command
    setIsProcessing(true);
    setEngineBadge({ type: 'gemini', label: '🤖 Gemini AI Fallback' });

    try {
      const res = await fetch('/api/ai/voice-parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voiceText: text,
          accounts: accounts.map(a => ({ id: a.id, name: a.name, type: a.type, bankName: a.bankName })),
          categories: [
            'Petrol',
            'Fuel',
            'Food',
            'Groceries',
            'Food & Groceries',
            'Clothing',
            'Healthcare',
            'Transport',
            'Utilities',
            'Telecom',
            'Shopping',
            'Entertainment',
            'Rent & Housing',
            'Education',
            'Salary',
            'Other'
          ]
        })
      });

      const json = await res.json();
      if (json.success && json.data) {
        const d = json.data;
        let targetAccId = d.matchedAccountId;
        if (!targetAccId && accounts.length > 0) {
          const match = accounts.find(a =>
            a.name.toLowerCase().includes((d.accountName || '').toLowerCase()) ||
            (d.accountName || '').toLowerCase().includes(a.name.toLowerCase())
          );
          targetAccId = match ? match.id : accounts[0].id;
        }

        setExtractedData({
          amount: Number(d.amount) || 0,
          merchant: d.merchant || 'Expense',
          category: (d.category as ExpenseCategory) || 'Other',
          matchedAccountId: targetAccId,
          accountName: d.accountName || (accounts.find(a => a.id === targetAccId)?.name || 'Default Account'),
          type: d.type === 'income' ? 'income' : 'expense',
          date: d.date || new Date().toISOString().split('T')[0],
          notes: d.notes || text
        });
      } else {
        setErrorMessage(json.error || 'Could not recognize expense command. Please rephrase or use one of the samples below.');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to process voice command.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmAndAdd = () => {
    if (!extractedData) return;

    if (extractedData.amount <= 0) {
      setErrorMessage('Please specify an amount greater than AED 0.');
      return;
    }

    onAddTransaction({
      amount: extractedData.amount,
      currency: 'AED',
      merchant: extractedData.merchant,
      category: extractedData.category,
      accountId: extractedData.matchedAccountId || accounts[0]?.id || 'acc-cash',
      type: extractedData.type,
      date: extractedData.date,
      notes: extractedData.notes,
      source: 'manual'
    });

    onClose();
  };

  const sampleCommands = [
    'Add AED 200 petrol from ADCB credit card',
    'Spent 85 dirhams at Carrefour on groceries',
    'Add AED 50 food paid in cash',
    '500 rupaye petrol gaadi me dala ADCB card se',
    'Paid 300 AED for taxi to Dubai Mall with Emirates NBD card',
    'Add AED 220 DEWA electricity bill from checking account',
    'Received AED 18,000 monthly salary deposit'
  ];

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/80 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[94vh] sm:max-h-[90vh] overflow-hidden">
        {/* Header - Fixed & sticky */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-800 bg-slate-950/80 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0">
              <Mic className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm sm:text-base font-bold text-white">AI Voice Expense Entry</h3>
                {engineBadge ? (
                  <span
                    className={`text-[9px] sm:text-[10px] font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                      engineBadge.type === 'rules'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                    }`}
                  >
                    <Zap className="w-3 h-3 text-emerald-400" />
                    {engineBadge.label}
                  </span>
                ) : (
                  <span className="text-[9px] sm:text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30 flex items-center gap-1">
                    <Zap className="w-3 h-3 text-teal-400" />
                    Instant JS (&lt;1ms)
                  </span>
                )}
              </div>
              <p className="text-[11px] sm:text-xs text-slate-400">Speak in English or Hindi to log expenses instantly</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Language Selector */}
            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-[11px]">
              <Globe className="w-3.5 h-3.5 text-teal-400 ml-1 hidden xs:block" />
              <button
                type="button"
                onClick={() => handleLanguageChange('en-US')}
                className={`px-2 py-0.5 rounded-lg font-bold transition cursor-pointer ${
                  language === 'en-US' ? 'bg-teal-500 text-slate-950 shadow' : 'text-slate-400 hover:text-white'
                }`}
                title="English (UAE / US)"
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => handleLanguageChange('hi-IN')}
                className={`px-2 py-0.5 rounded-lg font-bold transition cursor-pointer ${
                  language === 'hi-IN' ? 'bg-teal-500 text-slate-950 shadow' : 'text-slate-400 hover:text-white'
                }`}
                title="हिन्दी (Hindi)"
              >
                हिन्दी
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Body Container */}
        <div className="overflow-y-auto p-4 sm:p-5 flex-1 min-h-0 space-y-4">
          {/* Microphone Action Area (Optimized for Android PWA) */}
          <div className="flex flex-col items-center justify-center p-4 sm:p-5 bg-slate-950 rounded-2xl border border-slate-800 relative overflow-hidden">
          {/* Animated Glow Rings when listening */}
          {isListening && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-32 h-32 rounded-full bg-teal-500/20 animate-ping" />
              <div className="w-48 h-48 rounded-full bg-teal-500/10 animate-pulse" />
            </div>
          )}

          {/* Central Mic Button */}
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            className={`w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 cursor-pointer shadow-xl relative z-10 ${
              isListening
                ? 'bg-rose-500 text-white shadow-rose-500/40 scale-110'
                : 'bg-gradient-to-tr from-teal-500 to-emerald-400 text-slate-950 hover:scale-105 shadow-teal-500/30'
            }`}
            title={isListening ? 'Tap to Stop Listening' : 'Tap to Start Speaking'}
          >
            {isListening ? (
              <MicOff className="w-8 h-8 animate-pulse" />
            ) : (
              <Mic className="w-8 h-8" />
            )}
          </button>

          <p className="mt-3 text-xs font-semibold text-white">
            {isListening
              ? language === 'hi-IN'
                ? 'सुन रहे हैं... अपना खर्च बोलिए'
                : 'Listening... Speak your expense command now'
              : language === 'hi-IN'
              ? 'बोलने के लिए माइक दबाएं'
              : 'Tap microphone to speak'}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5 text-center px-4">
            {language === 'hi-IN'
              ? 'उदा. "200 rupaye petrol ADCB credit card se dala"'
              : 'e.g. "Add AED 200 petrol from ADCB credit card"'}
          </p>

          {!isSpeechSupported && (
            <div className="mt-2 text-[10px] text-amber-400 flex items-center gap-1">
              <Keyboard className="w-3 h-3" />
              <span>Mic not supported in this browser. Use typed input below.</span>
            </div>
          )}
        </div>

        {/* Live Transcript / Manual Typed-Input Fallback */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 font-semibold flex items-center gap-1.5">
              <Keyboard className="w-3.5 h-3.5 text-teal-400" />
              Recognized Speech / Typed Input:
            </span>
            <button
              type="button"
              onClick={() => setShowGuide(!showGuide)}
              className="text-teal-400 hover:text-teal-300 text-[11px] font-semibold flex items-center gap-1 cursor-pointer"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              <span>{showGuide ? 'Hide Guide' : 'Voice Command Guide'}</span>
            </button>
          </div>

          <div className="relative">
            <textarea
              rows={2}
              value={transcript}
              onChange={e => setTranscript(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey && transcript.trim()) {
                  e.preventDefault();
                  handleProcessVoiceText();
                }
              }}
              placeholder={
                language === 'hi-IN'
                  ? 'उदा. 200 rupaye petrol ADCB card se ya 50 rupaye food cash diya...'
                  : 'e.g. Add AED 200 petrol from ADCB credit card or 50 food cash...'
              }
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 leading-relaxed font-sans"
            />
          </div>

          {/* Quick Click-to-Test Prompts */}
          <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
            <span className="text-[10px] text-slate-400 font-medium">Quick test:</span>
            <button
              type="button"
              onClick={() => {
                const cmd = 'Add AED 200 petrol from ADCB credit card';
                setTranscript(cmd);
                handleProcessVoiceText(cmd);
              }}
              className="text-[10px] bg-slate-800 hover:bg-slate-750 text-teal-300 px-2 py-1 rounded-lg border border-slate-700 transition cursor-pointer font-medium"
            >
              ⛽ Petrol AED 200 ADCB
            </button>
            <button
              type="button"
              onClick={() => {
                const cmd = 'Spent 85 dirhams at Carrefour on groceries';
                setTranscript(cmd);
                handleProcessVoiceText(cmd);
              }}
              className="text-[10px] bg-slate-800 hover:bg-slate-750 text-teal-300 px-2 py-1 rounded-lg border border-slate-700 transition cursor-pointer font-medium"
            >
              🛒 Groceries AED 85
            </button>
            <button
              type="button"
              onClick={() => {
                const cmd = 'Add AED 50 food paid in cash';
                setTranscript(cmd);
                handleProcessVoiceText(cmd);
              }}
              className="text-[10px] bg-slate-800 hover:bg-slate-750 text-teal-300 px-2 py-1 rounded-lg border border-slate-700 transition cursor-pointer font-medium"
            >
              🍔 Food AED 50 Cash
            </button>
            <button
              type="button"
              onClick={() => {
                const cmd = '500 rupaye petrol gaadi me dala ADCB card se';
                setTranscript(cmd);
                handleProcessVoiceText(cmd);
              }}
              className="text-[10px] bg-slate-800 hover:bg-slate-750 text-amber-300 px-2 py-1 rounded-lg border border-slate-700 transition cursor-pointer font-medium"
            >
              🇮🇳 500 Petrol (Hindi)
            </button>
          </div>

          {/* Process Button */}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!transcript.trim() || isProcessing}
              onClick={() => handleProcessVoiceText()}
              className="flex-1 py-2.5 px-4 bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-xl transition shadow flex items-center justify-center gap-2 cursor-pointer"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Processing with Gemini Fallback...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 fill-current" />
                  <span>Parse Instantly (JS Rules Engine)</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Voice Command Examples Guide Drawer */}
        {showGuide && (
          <div className="mb-4 p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-xs space-y-2 animate-fadeIn">
            <div className="flex items-center gap-2 text-teal-400 font-bold">
              <Volume2 className="w-4 h-4" />
              <span>Voice Command Guide &amp; Examples (Tap to test):</span>
            </div>
            <div className="grid grid-cols-1 gap-1.5 pt-1">
              {sampleCommands.map((cmd, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setTranscript(cmd);
                    handleProcessVoiceText(cmd);
                  }}
                  className="text-left px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-850 border border-slate-800 text-[11px] text-slate-300 hover:text-white transition flex items-center justify-between cursor-pointer"
                >
                  <span>&ldquo;{cmd}&rdquo;</span>
                  <span className="text-[10px] text-teal-400 font-medium flex items-center gap-0.5">
                    Try <ArrowRight className="w-3 h-3" />
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error message if any */}
        {errorMessage && (
          <div className="mb-4 p-3 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Confirmation Card Before Posting */}
        {extractedData && (
          <div className="p-4 rounded-2xl bg-gradient-to-b from-slate-950 to-slate-900 border border-teal-500/40 space-y-3 mb-4 animate-fadeIn">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs">
              <span className="text-teal-400 font-bold flex items-center gap-1.5">
                <Check className="w-4 h-4 text-emerald-400" />
                Review &amp; Confirm Before Posting
              </span>
              <span className="text-[11px] text-slate-400">Step 2 of 2</span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              {/* Amount */}
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-400 block mb-0.5">Amount (AED):</span>
                <input
                  type="number"
                  step="0.01"
                  value={extractedData.amount}
                  onChange={e => setExtractedData({ ...extractedData, amount: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-transparent font-black text-lg text-teal-400 tabular-nums focus:outline-none"
                />
              </div>

              {/* Category */}
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-400 block mb-0.5">Category:</span>
                <select
                  value={extractedData.category}
                  onChange={e => setExtractedData({ ...extractedData, category: e.target.value as ExpenseCategory })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-1 text-white text-xs font-semibold focus:outline-none"
                >
                  <option value="Petrol">Petrol</option>
                  <option value="Fuel">Fuel</option>
                  <option value="Food">Food</option>
                  <option value="Groceries">Groceries</option>
                  <option value="Food & Groceries">Food &amp; Groceries</option>
                  <option value="Clothing">Clothing</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Transport">Transport</option>
                  <option value="Utilities">Utilities</option>
                  <option value="Telecom">Telecom</option>
                  <option value="Shopping">Shopping</option>
                  <option value="Entertainment">Entertainment</option>
                  <option value="Rent & Housing">Rent &amp; Housing</option>
                  <option value="Education">Education</option>
                  <option value="Salary">Salary</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              {/* Merchant / Description */}
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-400 block mb-0.5">Merchant / Item:</span>
                <input
                  type="text"
                  value={extractedData.merchant}
                  onChange={e => setExtractedData({ ...extractedData, merchant: e.target.value })}
                  className="w-full bg-transparent font-bold text-white text-xs focus:outline-none"
                />
              </div>

              {/* Account */}
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-400 block mb-0.5">Bank / Account:</span>
                <select
                  value={extractedData.matchedAccountId || ''}
                  onChange={e => {
                    const acc = accounts.find(a => a.id === e.target.value);
                    setExtractedData({
                      ...extractedData,
                      matchedAccountId: e.target.value,
                      accountName: acc ? acc.name : extractedData.accountName
                    });
                  }}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-1 text-white text-xs font-semibold focus:outline-none truncate"
                >
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.type})
                    </option>
                  ))}
                </select>
              </div>

              {/* Date */}
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-400 block mb-0.5 flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-teal-400" />
                  Date:
                </span>
                <input
                  type="date"
                  value={extractedData.date}
                  onChange={e => setExtractedData({ ...extractedData, date: e.target.value })}
                  className="w-full bg-transparent font-medium text-white text-xs focus:outline-none"
                />
              </div>

              {/* Type (Expense vs Income) */}
              <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-400 block mb-0.5">Transaction Type:</span>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => setExtractedData({ ...extractedData, type: 'expense' })}
                    className={`flex-1 py-1 rounded text-[11px] font-bold cursor-pointer transition ${
                      extractedData.type === 'expense'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                        : 'bg-slate-900 text-slate-400'
                    }`}
                  >
                    Expense
                  </button>
                  <button
                    type="button"
                    onClick={() => setExtractedData({ ...extractedData, type: 'income' })}
                    className={`flex-1 py-1 rounded text-[11px] font-bold cursor-pointer transition ${
                      extractedData.type === 'income'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : 'bg-slate-900 text-slate-400'
                    }`}
                  >
                    Income
                  </button>
                </div>
              </div>
            </div>

            {/* Action Buttons: Cancel / Re-speak and Confirm */}
            <div className="flex items-center gap-2.5 mt-3">
              <button
                type="button"
                onClick={() => setExtractedData(null)}
                className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded-xl border border-slate-700 transition text-center cursor-pointer"
              >
                Cancel / Re-speak
              </button>
              <button
                type="button"
                onClick={handleConfirmAndAdd}
                className="flex-1 py-2.5 bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg transition flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Check className="w-4 h-4" />
                <span>Confirm &amp; Post</span>
              </button>
            </div>
          </div>
        )}

        {/* Dismiss Button at bottom for mobile ergonomics */}
        {!extractedData && (
          <div className="pt-2">
            <button
              type="button"
              onClick={onClose}
              className="w-full py-2.5 rounded-xl bg-slate-950/70 hover:bg-slate-950 border border-slate-800 text-slate-400 hover:text-white text-xs font-semibold transition cursor-pointer text-center"
            >
              Cancel / Close
            </button>
          </div>
        )}
        </div>
      </div>
    </div>
  );
};
