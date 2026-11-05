import React from 'react';
import {
  X,
  Sparkles,
  Mic,
  TrendingUp,
  PieChart,
  MessageSquare,
  ShieldAlert,
  Smartphone,
  Calendar,
  Layers,
  Zap,
  CheckCircle2,
  Lock,
  Sliders,
  Wallet,
  FileText,
  FileSpreadsheet,
  ArrowRight
} from 'lucide-react';

interface KeyFeaturesModalProps {
  onClose: () => void;
  onOpenVoiceModal?: () => void;
  onOpenAssistantModal?: () => void;
  onOpenForecastModal?: () => void;
}

export interface FeatureItem {
  id: string;
  title: string;
  badge: string;
  badgeColor: string;
  icon: any;
  description: string;
  bullets: string[];
  isNew?: boolean;
}

export const CURRENT_KEY_FEATURES: FeatureItem[] = [
  {
    id: 'statement_import',
    title: 'AI Bank Statement Import & Reconciliation',
    badge: 'PDF • Excel • CSV',
    badgeColor: 'bg-teal-500/10 text-teal-300 border-teal-500/30',
    icon: FileSpreadsheet,
    description: 'Upload bank and credit card statements with automated table extraction, UAE rule categorization, and balance reconciliation.',
    bullets: [
      'Extracts from PDF (scanned/digital), Excel (.xlsx, .xls), and CSV files from all UAE banks',
      'Intelligent Document AI extracts dates, descriptions, debits, credits, and running balances',
      'Anti-duplicate shield cross-references notifications and previous entries to prevent double-posting',
      'Preview before posting: edit categories, exclude duplicates, and automatically learn corrections',
      'Mathematical balance verification ensures opening + credits - debits matches closing balance'
    ],
    isNew: true
  },
  {
    id: 'notification_interceptor',
    title: 'Bank Notification Interceptor & SMS Parsing',
    badge: 'Zero-Click Automation',
    badgeColor: 'bg-teal-500/10 text-teal-300 border-teal-500/30',
    icon: Zap,
    description: 'Automatic real-time transaction recording from Android notification shade & iOS/Android SMS paste.',
    bullets: [
      'Extracts AED/USD amounts, merchants, categories, and account masks (•••• 1234)',
      'Multi-day SMS date extraction: posts historical transactions on their actual dates, not today',
      'Anti-duplicate shield: eliminates double entries when banks send both Push & SMS alerts',
      'Supports all UAE banks: Emirates NBD, ADCB, FAB, Mashreq, Citi, DIB, CBD, RAKBANK, HSBC'
    ],
    isNew: true
  },
  {
    id: 'voice_assistant',
    title: 'Instant AI Voice Expense Assistant',
    badge: 'Fast Rules Engine + Gemini',
    badgeColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    icon: Mic,
    description: 'Sub-millisecond voice and typed expense logging with English & Hindi bilingual support.',
    bullets: [
      'Speaks English & Hindi ("Add AED 200 petrol from ADCB credit card" / "500 rupaye petrol gaadi me dala")',
      'Matches your actual database accounts and categories instantaneously',
      'Pre-posting confirmation card with typed fallback for silent environments',
      'Gemini AI fallback automatically engaged only for complex spoken phrases'
    ],
    isNew: true
  },
  {
    id: 'ai_insights_chatbot',
    title: 'AI Insights Chatbot (Gemini)',
    badge: 'Live Ledger Grounding',
    badgeColor: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
    icon: MessageSquare,
    description: 'Interactive conversational wealth advisor powered by Gemini that answers any question using your real financial data.',
    bullets: [
      'Answers "Where did I overspend?", "How can I save AED 2,000 in UAE?", "Review my credit cards"',
      'Directly analyzes actual transactions, balances, recurring bills, and budget limits',
      'Provides practical UAE resident advice (DEWA seasonal slabs, Salik, supermarket alternatives)'
    ],
    isNew: true
  },
  {
    id: 'cash_flow_forecast',
    title: 'Mobile Cash Flow & Burn Rate Forecast',
    badge: 'Statsmodels Time-Series',
    badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    icon: TrendingUp,
    description: 'Holt-Winters time-series projection calculating month-end balances, daily burn rate, and budget overrun risk.',
    bullets: [
      'Optimized for mobile touchscreens with responsive trajectory charts',
      'Accounts for scheduled recurring bills due in the second half of the month',
      'Instant offline computation fallback ensures zero loading hangs on mobile PWA'
    ],
    isNew: true
  },
  {
    id: 'wps_salary_credit',
    title: 'WPS Salary & Payroll Auto-Credit',
    badge: 'Automated Income',
    badgeColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    icon: Wallet,
    description: 'Automatically detects UAE WPS payroll and salary credit notices, tagging them as Income and immediately boosting liquid bank balances.',
    bullets: [
      'Recognizes salary notifications from Mashreq WPS, Emirates NBD, ADCB, and FAB',
      'Credits your liquid checking account balance immediately without manual entry',
      'Tracks monthly salary cadence and computes real-time savings rate'
    ]
  },
  {
    id: 'red_flag_foreign_fx',
    title: 'Red Flag & Foreign FX Alter System',
    badge: 'Currency Shield',
    badgeColor: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    icon: ShieldAlert,
    description: 'Catches international foreign currency spends (USD, EUR, GBP, INR) and converts to AED with full adjustment control.',
    bullets: [
      'Auto-converts foreign currencies to AED at interbank rates (1 USD = 3.6725 AED)',
      '1-Click "Alter" modal lets you adjust conversion markup to match bank statements',
      'Provides "Confirm Genuine" controls to verify international purchases'
    ]
  },
  {
    id: 'smart_ledger_memory',
    title: 'Smart Ledger Memory',
    badge: 'Intelligent Routing',
    badgeColor: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    icon: Wallet,
    description: 'Learns and remembers which card or bank account each merchant belongs to for automated future routing.',
    bullets: [
      'Remembers that "Spinneys" goes to Citi Card and "DEWA" goes to Mashreq Account',
      'Future transactions for that merchant automatically assign to the correct account',
      'Maintains clean multi-bank balances with zero ledger distortion'
    ]
  },
  {
    id: 'clean_3d_charts',
    title: '3D Tactile Charts & Donut Breakdown',
    badge: 'Modern Donut',
    badgeColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    icon: PieChart,
    description: 'Volumetric glowing Donut chart showing category spending with zero overlapping popup clutter.',
    bullets: [
      'Clean interactive donut slices with tactile center sphere displaying total spend',
      'Eliminated intrusive popup boxes when clicking color slices for smooth mobile navigation',
      'Category cards display exact percentages, transaction counts, and AED totals'
    ],
    isNew: true
  },
  {
    id: 'subscriptions_tracker',
    title: 'Subscriptions & Recurring Bill Tracker',
    badge: 'Bill Reminders',
    badgeColor: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
    icon: Calendar,
    description: 'Track recurring commitments for Du, Etisalat, DEWA, Salik, Gym, and streaming services.',
    bullets: [
      'Billing day countdown alerts and annual cost projections',
      'Factor recurring bills into month-end cash flow forecast',
      'Helps eliminate unwanted zombie subscriptions'
    ]
  },
  {
    id: 'pin_security',
    title: 'PIN Lock & 5-Min Expiry OTP Recovery',
    badge: 'Local-First Security',
    badgeColor: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    icon: Lock,
    description: '4-digit PIN security with auto-lock on app switch, background blur, and physical keyboard support.',
    bullets: [
      'Removed unwanted autofill suggestions for maximum privacy',
      'Auto-locks upon exiting to home screen or switching browser tabs',
      'Tamper-proof recovery with 5-minute expiry email OTP verification'
    ],
    isNew: true
  },
  {
    id: 'monthly_statement_pdf',
    title: 'Monthly Statement & Tax PDF Export',
    badge: 'Reporting & Export',
    badgeColor: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
    icon: FileText,
    description: 'Export professional monthly expense statements and category breakdowns in PDF and CSV format.',
    bullets: [
      'High-fidelity UAE monthly expense summaries with category breakdowns',
      'Account net worth and credit liability reporting ready for accounting and tax records',
      'Print or download directly from mobile or desktop'
    ]
  }
];

export const KeyFeaturesModal: React.FC<KeyFeaturesModalProps> = ({
  onClose,
  onOpenVoiceModal,
  onOpenAssistantModal,
  onOpenForecastModal
}) => {
  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/85 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl p-5 sm:p-6 shadow-2xl flex flex-col max-h-[94vh] sm:max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base sm:text-lg font-bold text-white">DirhamTrack Key Features</h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30 font-mono">
                  v2.4 Active
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Notification automation, AI intelligence &amp; UAE financial management features
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Features List */}
        <div className="py-4 space-y-4 overflow-y-auto flex-1 pr-1">
          {CURRENT_KEY_FEATURES.map((feature) => {
            const IconComponent = feature.icon;
            return (
              <div
                key={feature.id}
                className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800/90 hover:border-slate-700 transition shadow-sm space-y-2.5"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-slate-900 border border-slate-800 text-teal-400 flex items-center justify-center shrink-0">
                      <IconComponent className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-xs sm:text-sm font-bold text-white">{feature.title}</h4>
                        {feature.isNew && (
                          <span className="text-[9px] font-extrabold uppercase px-1.5 py-0.2 rounded bg-teal-500/20 text-teal-300 border border-teal-500/40">
                            New
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border whitespace-nowrap ${feature.badgeColor}`}>
                    {feature.badge}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  {feature.description}
                </p>

                <ul className="space-y-1 pt-1">
                  {feature.bullets.map((b, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-[11px] text-slate-400">
                      <CheckCircle2 className="w-3.5 h-3.5 text-teal-400 shrink-0 mt-0.5" />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>

                {/* Quick Action Buttons for Interactive Features */}
                {feature.id === 'voice_assistant' && onOpenVoiceModal && (
                  <div className="pt-2">
                    <button
                      onClick={() => {
                        onClose();
                        onOpenVoiceModal();
                      }}
                      className="px-3 py-1.5 bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/30 text-teal-300 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition"
                    >
                      <span>Try Voice Assistant</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                )}

                {feature.id === 'ai_insights_chatbot' && onOpenAssistantModal && (
                  <div className="pt-2">
                    <button
                      onClick={() => {
                        onClose();
                        onOpenAssistantModal();
                      }}
                      className="px-3 py-1.5 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-300 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition"
                    >
                      <span>Open AI Chatbot</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                )}

                {feature.id === 'cash_flow_forecast' && onOpenForecastModal && (
                  <div className="pt-2">
                    <button
                      onClick={() => {
                        onClose();
                        onOpenForecastModal();
                      }}
                      className="px-3 py-1.5 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition"
                    >
                      <span>View Cash Flow Forecast</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="pt-3.5 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 shrink-0 gap-2">
          <span className="text-[11px] hidden sm:inline">DirhamTrack UAE Edition</span>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={onClose}
              className="flex-1 sm:flex-none px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-xl transition cursor-pointer text-center"
            >
              Cancel
            </button>
            <button
              onClick={onClose}
              className="flex-1 sm:flex-none px-5 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold rounded-xl transition cursor-pointer text-center"
            >
              Got it
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
