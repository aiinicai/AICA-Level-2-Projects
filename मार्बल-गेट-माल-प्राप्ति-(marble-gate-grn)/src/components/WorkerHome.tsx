import React from 'react';
import { UserAccount } from '../types/grn';
import { PlusCircle, FileText, Clock, RefreshCw, Truck, CheckCircle, ShieldAlert, Sparkles } from 'lucide-react';

interface WorkerHomeProps {
  currentUser: UserAccount;
  hasDraft: boolean;
  draftSavedAt: string | null;
  pendingSyncCount: number;
  isOnline: boolean;
  isSyncing: boolean;
  todayCount: number;
  todayBlocks: number;
  onNewGrn: () => void;
  onViewOld: () => void;
  onResumeDraft: () => void;
  onDiscardDraft: () => void;
  onSyncNow: () => void;
}

export const WorkerHome: React.FC<WorkerHomeProps> = ({
  currentUser,
  hasDraft,
  draftSavedAt,
  pendingSyncCount,
  isOnline,
  isSyncing,
  todayCount,
  todayBlocks,
  onNewGrn,
  onViewOld,
  onResumeDraft,
  onDiscardDraft,
  onSyncNow,
}) => {
  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      
      {/* Offline Alert Banner */}
      {!isOnline && (
        <div className="bg-amber-100 border-2 border-amber-500 rounded-2xl p-4 text-amber-950 flex items-start gap-3 shadow-md">
          <div className="p-2 bg-amber-500 text-white rounded-xl shrink-0 mt-0.5">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h4 className="font-extrabold text-base">ऑफलाइन मोड चालू है (इंटरनेट नहीं है)</h4>
            <p className="text-xs sm:text-sm text-amber-900 mt-1 leading-relaxed">
              चिंता न करें! आप नई माल प्राप्ति रसीदें सामान्य रूप से बना सकते हैं। सभी रसीदें इस फ़ोन पर सुरक्षित रहेंगी और इंटरनेट आते ही अपने-आप सर्वर पर पहुंच जाएंगी।
            </p>
          </div>
        </div>
      )}

      {/* Pending Sync Reminder */}
      {pendingSyncCount > 0 && isOnline && (
        <div className="bg-blue-50 border-2 border-blue-400 rounded-2xl p-4 text-blue-950 flex items-center justify-between gap-3 shadow-md">
          <div className="flex items-center gap-3">
            <RefreshCw className={`w-6 h-6 text-blue-600 ${isSyncing ? 'animate-spin' : ''}`} />
            <div>
              <div className="font-bold text-sm sm:text-base">
                {pendingSyncCount} रसीदें इस फ़ोन पर हैं (सिंक बाकी)
              </div>
              <div className="text-xs text-blue-700">
                सर्वर और मालिक के फ़ोन पर भेजने के लिए नीचे बटन दबाएं।
              </div>
            </div>
          </div>
          <button
            onClick={onSyncNow}
            disabled={isSyncing}
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-extrabold text-xs sm:text-sm rounded-xl shadow-md transition active:scale-95 shrink-0"
          >
            {isSyncing ? 'सिंक हो रहा है...' : 'अभी सिंक करें'}
          </button>
        </div>
      )}

      {/* Gate Welcome & Today's Metric Badge */}
      <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            कार्यस्थल: {currentUser.gateName}
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-slate-900 mt-0.5">
            नमस्ते, {currentUser.name}
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 mt-1">
            मार्बल एवं स्टोन आवक पर्ची (GRN) दर्ज करने के लिए नीचे विकल्प चुनें:
          </p>
        </div>

        {/* Quick gate stats */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="flex-1 sm:flex-initial bg-teal-50 border border-teal-200 rounded-2xl px-4 py-2.5 text-center">
            <div className="text-xs text-teal-800 font-bold">आज की रसीदें</div>
            <div className="text-2xl font-black text-teal-900">{todayCount}</div>
          </div>
          <div className="flex-1 sm:flex-initial bg-amber-50 border border-amber-200 rounded-2xl px-4 py-2.5 text-center">
            <div className="text-xs text-amber-800 font-bold">आज के ब्लॉक</div>
            <div className="text-2xl font-black text-amber-900">{todayBlocks}</div>
          </div>
        </div>
      </div>

      {/* 3 Main Action Cards */}
      <div className="space-y-4">
        
        {/* Action 1: New Goods Receipt (Primary) */}
        <button
          onClick={onNewGrn}
          className="w-full bg-gradient-to-r from-teal-700 to-teal-800 hover:from-teal-800 hover:to-teal-900 text-white rounded-3xl p-6 shadow-xl shadow-teal-900/20 text-left transition transform active:scale-98 border-2 border-teal-600 flex items-center justify-between group cursor-pointer"
          style={{ minHeight: '110px' }}
        >
          <div className="flex items-center gap-4 sm:gap-5">
            <div className="w-16 h-16 rounded-2xl bg-white/15 border border-white/20 flex items-center justify-center text-amber-300 shadow-inner shrink-0 group-hover:scale-105 transition">
              <PlusCircle className="w-10 h-10" />
            </div>
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-400 text-slate-950 text-[11px] font-black uppercase tracking-wider mb-1">
                <Sparkles className="w-3 h-3" /> मुख्य कार्य
              </div>
              <h3 className="text-2xl sm:text-3xl font-black tracking-tight text-white leading-tight">
                नई माल प्राप्ति
              </h3>
              <p className="text-teal-100 text-xs sm:text-sm font-medium mt-1">
                गाड़ी, सप्लायर और मार्बल ब्लॉक की नई रसीद बनाएं
              </p>
            </div>
          </div>
          <span className="text-3xl text-amber-300 font-bold pr-2 hidden sm:inline">➜</span>
        </button>

        {/* Action 2: View Old Receipts */}
        <button
          onClick={onViewOld}
          className="w-full bg-white hover:bg-slate-50 text-slate-900 rounded-3xl p-6 shadow-md border-2 border-slate-300 text-left transition transform active:scale-98 flex items-center justify-between group cursor-pointer"
          style={{ minHeight: '100px' }}
        >
          <div className="flex items-center gap-4 sm:gap-5">
            <div className="w-14 h-14 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 shrink-0 group-hover:bg-slate-200 transition">
              <FileText className="w-8 h-8 text-teal-700" />
            </div>
            <div>
              <h3 className="text-xl sm:text-2xl font-black text-slate-900">
                पुरानी रसीद देखें
              </h3>
              <p className="text-slate-500 text-xs sm:text-sm font-medium mt-0.5">
                गाड़ी नंबर, रसीद नंबर या सप्लायर से खोजें व दोबारा प्रिंट करें
              </p>
            </div>
          </div>
          <span className="text-2xl text-slate-400 font-bold pr-2 hidden sm:inline">➜</span>
        </button>

        {/* Action 3: Incomplete / Draft Receipts */}
        <div className={`rounded-3xl p-5 border-2 transition ${
          hasDraft
            ? 'bg-amber-50/70 border-amber-400 shadow-md'
            : 'bg-white border-slate-200 shadow-sm opacity-90'
        }`}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 ${
                hasDraft ? 'bg-amber-500 text-white' : 'bg-slate-100 text-slate-400'
              }`}>
                <Clock className="w-8 h-8" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl sm:text-2xl font-black text-slate-900">
                    अधूरी रसीद (ड्राफ्ट)
                  </h3>
                  {hasDraft && (
                    <span className="px-2.5 py-0.5 bg-amber-500 text-slate-950 font-black text-xs rounded-full animate-pulse">
                      1 बाकी है
                    </span>
                  )}
                </div>
                <p className="text-slate-500 text-xs sm:text-sm font-medium mt-0.5">
                  {hasDraft
                    ? `पिछली रसीद जो पूरी नहीं हुई थी (${draftSavedAt ? new Date(draftSavedAt).toLocaleTimeString('hi-IN') : 'हाल ही में'})`
                    : 'फ़िलहाल कोई अधूरी रसीद नहीं है। नया काम सीधे शुरू करें।'}
                </p>
              </div>
            </div>

            {hasDraft && (
              <div className="flex items-center gap-2 w-full sm:w-auto pt-2 sm:pt-0">
                <button
                  onClick={onResumeDraft}
                  className="flex-1 sm:flex-initial px-5 py-3 bg-amber-500 hover:bg-amber-600 text-slate-950 font-black text-sm rounded-2xl shadow-sm transition active:scale-95 cursor-pointer"
                >
                  जारी रखें ➜
                </button>
                <button
                  onClick={onDiscardDraft}
                  className="px-4 py-3 bg-slate-200 hover:bg-red-100 text-slate-700 hover:text-red-700 font-bold text-xs rounded-2xl transition cursor-pointer"
                  title="ड्राफ्ट रद्द करें"
                >
                  हटाएं
                </button>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Helpful Gate Worker Quick Guide */}
      <div className="bg-slate-50 border border-slate-200 rounded-3xl p-5 text-slate-700 text-xs sm:text-sm space-y-2">
        <h4 className="font-black text-slate-900 flex items-center gap-2">
          💡 गेट कर्मचारी के लिए जरूरी निर्देश:
        </h4>
        <ul className="list-disc list-inside space-y-1 text-slate-600">
          <li>गाड़ी गेट पर आने पर उसका <strong>चालान (Challan)</strong> व <strong>गाड़ी नंबर</strong> अवश्य मिलाएं।</li>
          <li>हर मार्बल ब्लॉक पर खदान का <strong>ब्लॉक नंबर</strong> या मार्क देखकर दर्ज करें।</li>
          <li>नाप <strong>इंच (Inches)</strong> में भरते ही आयतन (CFT) स्वतः निकल जाता है।</li>
          <li>यदि धर्मकांटा पर्ची उपलब्ध हो तो <strong>सकल व खाली गाड़ी वजन</strong> अवश्य भरें।</li>
        </ul>
      </div>

    </div>
  );
};
