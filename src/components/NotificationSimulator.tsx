import React, { useState } from 'react';
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  Send,
  ShieldAlert,
  Smartphone,
  Zap,
  Radio,
  ChevronDown,
  ChevronUp,
  ClipboardPaste,
  Info
} from 'lucide-react';
import { Transaction } from '../types/finance';
import { parseBankNotificationText, sanitizeBankSMSText } from '../services/notificationParser';
import { findDuplicateTransaction } from '../services/deduplication';
import { ReceiptScannerModal } from './ReceiptScannerModal';

interface NotificationSimulatorProps {
  onRecordTransaction: (tx: Partial<Transaction>) => void;
  onOpenAndroidCode: () => void;
  onOpenAndroidGuide?: () => void;
  transactions?: Transaction[];
}

export const NotificationSimulator: React.FC<NotificationSimulatorProps> = ({
  onRecordTransaction,
  onOpenAndroidCode,
  onOpenAndroidGuide,
  transactions = []
}) => {
  const [customText, setCustomText] = useState('');
  const [bannerAlert, setBannerAlert] = useState<{ type: 'success' | 'redflag' | 'info'; message: string } | null>(null);

  // Receipt OCR Scanner State
  const [ocrModalOpen, setOcrModalOpen] = useState(false);
  const [ocrInitialMerchant, setOcrInitialMerchant] = useState('Nesto Hypermarket');
  const [ocrInitialAmount, setOcrInitialAmount] = useState(100);

  const handleSaveOcrTransaction = (data: {
    merchant: string;
    amount: number;
    date: string;
    items: any[];
    categorySplits: any[];
    receiptImage?: string;
  }) => {
    onRecordTransaction({
      amount: data.amount,
      merchant: data.merchant,
      category: data.categorySplits.length > 1 ? 'Food & Groceries' : (data.categorySplits[0]?.category || 'Food & Groceries'),
      currency: 'AED',
      date: data.date,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      items: data.items,
      categorySplits: data.categorySplits,
      hasReceipt: true,
      receiptImage: data.receiptImage,
      source: 'auto_notification',
      isVerifiedByUser: true,
      notes: `Receipt OCR Scanned (${data.items.length} items): ${data.categorySplits.map(s => `${s.category} AED ${s.amount.toFixed(2)}`).join(' • ')}`,
      isRedFlag: false,
      type: 'expense'
    });

    setBannerAlert({
      type: 'success',
      message: `🧾 Receipt Attached & Itemized: AED ${data.amount.toFixed(2)} at ${data.merchant} categorized into ${data.categorySplits.map(s => `${s.category} (AED ${s.amount.toFixed(2)})`).join(', ')}!`
    });
    setTimeout(() => setBannerAlert(null), 8000);
  };

  // Helper to process and record any real bank notification (supports single or multi-message pasting)
  const processBankNotification = (rawText: string): boolean => {
    if (!rawText || !rawText.trim()) return false;

    // Sanitize input text first (handles iOS Unicode characters and linebreaks)
    const cleanedText = sanitizeBankSMSText(rawText);

    // Check if the user pasted multiple messages (e.g. from the last 3 days)
    const separateMessages = cleanedText
      .split(/(?:\r?\n\s*\r?\n)+|(?:\n(?=[A-Z]))|(?<=\.)\s+(?=(?:Dear Customer|Purchase of|Your (?:credit |debit )?card|Txn of|Transaction of|Alert:|Salary of|debited from|credited to))/i)
      .map(m => m.trim())
      .filter(m => m.length > 15 && /\b(?:AED|DHS|DIRHAM|\$|USD|debited|spent|purchase|credited|salary)\b/i.test(m));

    const messagesToProcess = separateMessages.length > 1 ? separateMessages : [cleanedText];
    let recordedCount = 0;
    const recordedDates: string[] = [];

    for (const msg of messagesToProcess) {
      const parsed = parseBankNotificationText(msg, { existingTransactions: transactions });
      if (!parsed.success) continue;

      const txDate = parsed.date;
      const txTime = parsed.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      const dup = findDuplicateTransaction({
        amount: parsed.amount,
        originalAmount: parsed.originalAmount,
        originalCurrency: parsed.originalCurrency,
        merchant: parsed.cleanedMerchant,
        bankName: parsed.bankName,
        date: txDate,
        time: txTime,
        cardMask: parsed.cardMask,
        type: parsed.type,
        rawNotificationText: parsed.rawText
      }, transactions);

      if (dup.isDuplicate && dup.matchedTransaction) {
        setBannerAlert({
          type: 'info',
          message: `🛡️ DUPLICATE AVOIDED: AED ${parsed.amount.toFixed(2)} at ${dup.matchedTransaction.merchant} on ${txDate} already recorded!`
        });
        setTimeout(() => setBannerAlert(null), 6000);
        continue;
      }

      onRecordTransaction({
        amount: parsed.amount,
        originalAmount: parsed.originalAmount,
        originalCurrency: parsed.originalCurrency,
        exchangeRate: parsed.exchangeRate,
        currency: parsed.currency,
        merchant: parsed.cleanedMerchant,
        category: parsed.category,
        date: txDate,
        time: txTime,
        source: 'auto_notification',
        bankName: parsed.bankName !== 'UAE Bank' ? parsed.bankName : undefined,
        rawNotificationText: parsed.rawText,
        isRedFlag: parsed.isRedFlag,
        redFlagReason: parsed.redFlagReason,
        isVerifiedByUser: !parsed.isRedFlag,
        type: parsed.type
      });

      recordedCount++;
      if (!recordedDates.includes(txDate)) {
        recordedDates.push(txDate);
      }
    }

    if (recordedCount > 0) {
      const datesDisplay = recordedDates.map(d => {
        try {
          return new Date(d + 'T12:00:00').toLocaleDateString('en-AE', { day: 'numeric', month: 'short' });
        } catch {
          return d;
        }
      }).join(', ');

      setBannerAlert({
        type: 'success',
        message: recordedCount === 1
          ? `⚡ Bank SMS Recorded for Date: ${datesDisplay} (${messagesToProcess[0].match(/AED\s*([0-9.]+)/i)?.[0] || 'AED'})!`
          : `⚡ Successfully recorded ${recordedCount} transactions from your bank messages with original dates (${datesDisplay})!`
      });
      setTimeout(() => setBannerAlert(null), 7000);
      return true;
    }

    return false;
  };

  // Auto-Catch button: Captures real Notification Center transactions
  const handleAutoCatch = async () => {
    // 1. Check if an incoming notification was buffered from the native notification center listener
    const bufferedAlert = (window as any).__pendingNotificationCenterAlert;
    if (bufferedAlert && typeof bufferedAlert === 'string') {
      const recorded = processBankNotification(bufferedAlert);
      if (recorded) {
        (window as any).__pendingNotificationCenterAlert = null;
        return;
      }
    }

    // 2. Check if a notification center alert was entered in the input box
    if (customText.trim()) {
      const recorded = processBankNotification(customText);
      if (recorded) {
        setCustomText('');
        return;
      } else {
        setBannerAlert({
          type: 'redflag',
          message: 'Could not extract bank transaction details from this text. Ensure it contains an amount (e.g. AED 150.00 or USD 50.00).'
        });
        setTimeout(() => setBannerAlert(null), 5000);
        return;
      }
    }

    // 3. Check clipboard for any copied bank SMS/notification
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          const recorded = processBankNotification(text);
          if (recorded) {
            setBannerAlert({
              type: 'success',
              message: '⚡ Captured bank transaction alert from your clipboard!'
            });
            setTimeout(() => setBannerAlert(null), 5000);
            return;
          }
        }
      }
    } catch {
      // ignore clipboard permission error
    }

    setBannerAlert({
      type: 'info',
      message: 'Listening for real-time bank alerts. Paste or enter any incoming bank SMS into the box or copy to clipboard to capture.'
    });
    setTimeout(() => setBannerAlert(null), 5000);
  };

  const handleParseCustom = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customText.trim()) return;

    const recorded = processBankNotification(customText);
    if (recorded) {
      setCustomText('');
    } else {
      setBannerAlert({
        type: 'redflag',
        message: 'Could not extract amount or merchant from text. Please ensure the message includes an amount (e.g. AED 150.00 or USD 45.00).'
      });
      setTimeout(() => setBannerAlert(null), 5000);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg">
      {/* Header with Android Automatic Listener Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800/80 mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-500/15 border border-teal-500/30 text-teal-400 flex items-center justify-center shrink-0">
            <Radio className="w-5 h-5 animate-pulse text-teal-400" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              Automatic Notification Interceptor
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                Live 24/7
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Captures Citi, Mashreq (Salary &amp; Debits), Emirates NBD, FAB &amp; SMS bank alerts directly from notification bar
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleAutoCatch}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-lg transition shrink-0 cursor-pointer shadow-md"
            title="Capture notification center bank transaction"
          >
            <Zap className="w-3.5 h-3.5 fill-current" />
            <span>Auto-Catch</span>
          </button>

          <button
            onClick={onOpenAndroidCode}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-teal-300 text-xs font-medium rounded-lg border border-slate-700 transition shrink-0 cursor-pointer"
            title="View native Android background service status & diagnostics"
          >
            <Smartphone className="w-3.5 h-3.5 text-teal-400" />
            <span>Background Service</span>
          </button>
        </div>
      </div>

      {/* Real-time Notification Center Status Banner */}
      <div className="mb-4 p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-300 space-y-1.5">
        <div className="flex items-center gap-2 font-semibold text-white">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Notification Center Interceptor:</span>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed pl-6">
          DirhamTrack records bank transactions received in your device's notification center. Whenever Citi, Mashreq (Salary &amp; Debits), Emirates NBD, or SMS sends an alert to your notification bar, it is automatically captured, USD converted to AED, and recorded into your ledger.
        </p>
      </div>

      {/* Alert Banner if just triggered */}
      {bannerAlert && (
        <div
          className={`mb-4 p-3.5 rounded-xl border flex items-center gap-3 animate-fade-in ${
            bannerAlert.type === 'redflag'
              ? 'bg-rose-950/40 border-rose-500/40 text-rose-200'
              : bannerAlert.type === 'info'
              ? 'bg-slate-800/80 border-slate-700 text-slate-200'
              : 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200'
          }`}
        >
          {bannerAlert.type === 'redflag' ? (
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
          ) : bannerAlert.type === 'info' ? (
            <Radio className="w-5 h-5 text-teal-400 shrink-0" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          )}
          <p className="text-xs font-medium leading-relaxed">{bannerAlert.message}</p>
        </div>
      )}

      {/* Notification Center Alert Input (Accepts real notifications only) */}
      <div className="pt-1">
        <form onSubmit={handleParseCustom} className="space-y-2">
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={customText}
              onChange={e => setCustomText(e.target.value)}
              placeholder="Paste or enter notification center bank alert (e.g. Citi Alert: Card ending 5678 was used for AED 245.50 at CARREFOUR)..."
              className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 transition"
            />
            <button
              type="submit"
              disabled={!customText.trim()}
              className="px-4 py-2.5 bg-teal-500 hover:bg-teal-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 transition whitespace-nowrap cursor-pointer shadow"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Capture Alert</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setOcrInitialMerchant('Nesto Hypermarket');
                setOcrInitialAmount(100);
                setOcrModalOpen(true);
              }}
              className="px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-black text-xs rounded-xl flex items-center justify-center gap-1.5 transition whitespace-nowrap cursor-pointer shadow-md"
              title="Attach photo or scan bill/receipt to allocate expense categories without VAT"
            >
              <span>📸 Scan &amp; Itemize Receipt (OCR)</span>
            </button>
          </div>
          <p className="text-[11px] text-slate-500">
            Accepts real notifications from Citi, Mashreq (Salary &amp; Debits), Emirates NBD, FAB, etc. Automatically converts USD to AED and supports attaching receipts for category splitting (e.g. Nesto AED 100 into Clothing + Food &amp; Groceries).
          </p>
        </form>
      </div>


      {/* Receipt OCR Scanner Modal */}
      {ocrModalOpen && (
        <ReceiptScannerModal
          initialMerchant={ocrInitialMerchant}
          initialAmount={ocrInitialAmount}
          onClose={() => setOcrModalOpen(false)}
          onSaveReceiptData={handleSaveOcrTransaction}
        />
      )}
    </div>
  );
};
