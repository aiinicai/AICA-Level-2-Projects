import React, { useState } from 'react';
import { usePWAInstall } from '../hooks/usePWAInstall';
import { Download, Share, PlusSquare, X } from 'lucide-react';

export const PWAInstallBanner: React.FC = () => {
  const { isInstallable, isInstalled, isIOS, install } = usePWAInstall();
  const [showIOSGuide, setShowIOSGuide] = useState(false);

  if (isInstalled) {
    return null;
  }

  return (
    <>
      {isInstallable && (
        <button
          onClick={install}
          className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold px-3 py-2 rounded-xl text-sm shadow-md transition active:scale-95"
          title="मोबाइल पर ऍप इंस्टॉल करें"
        >
          <Download className="w-4 h-4 text-slate-900" />
          <span>ऍप इंस्टॉल करें</span>
        </button>
      )}

      {isIOS && (
        <button
          onClick={() => setShowIOSGuide(true)}
          className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 text-amber-300 font-medium px-3 py-2 rounded-xl text-xs hover:bg-slate-700 transition"
        >
          <PlusSquare className="w-4 h-4 text-amber-400" />
          <span>iPhone में जोड़ें</span>
        </button>
      )}

      {showIOSGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl text-slate-900">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900">iPhone / iPad पर ऍप इंस्टॉल करें</h3>
              <button
                onClick={() => setShowIOSGuide(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="mt-4 space-y-4 text-sm text-slate-700">
              <div className="flex items-start gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
                <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-sm shrink-0">1</div>
                <div>Safari ब्राउज़र में नीचे दिए गए <Share className="w-4 h-4 inline text-blue-600 mx-1" /> <strong>शेयर (Share)</strong> बटन पर टैप करें।</div>
              </div>

              <div className="flex items-start gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
                <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-sm shrink-0">2</div>
                <div>नीचे स्क्रॉल करें और <PlusSquare className="w-4 h-4 inline text-slate-700 mx-1" /> <strong>"होम स्क्रीन पर जोड़ें" (Add to Home Screen)</strong> चुनें।</div>
              </div>

              <div className="flex items-start gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
                <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-sm shrink-0">3</div>
                <div>ऊपर दाईं ओर <strong>"जोड़ें" (Add)</strong> पर क्लिक करें। ऍप आपके फ़ोन पर उपलब्ध हो जाएगी।</div>
              </div>
            </div>

            <button
              onClick={() => setShowIOSGuide(false)}
              className="mt-5 w-full rounded-xl bg-teal-700 hover:bg-teal-800 py-3 text-sm font-bold text-white transition active:scale-98"
            >
              समझ गया / बंद करें
            </button>
          </div>
        </div>
      )}
    </>
  );
};
