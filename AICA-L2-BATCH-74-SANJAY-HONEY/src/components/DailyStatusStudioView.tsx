import React, { useState, useRef } from 'react';
import {
  Smartphone,
  Download,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  TrendingUp,
  Building2,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Share2,
} from 'lucide-react';
import { toPng } from 'html-to-image';
import { RegulatoryUpdate } from '../types';

interface DailyStatusStudioViewProps {
  updates: RegulatoryUpdate[];
  briefingDate: string;
}

export const DailyStatusStudioView: React.FC<DailyStatusStudioViewProps> = ({
  updates,
  briefingDate,
}) => {
  const [activeCardIndex, setActiveCardIndex] = useState<number>(1);
  const cardRef = useRef<HTMLDivElement>(null);
  const [isExporting, setIsExporting] = useState(false);

  // Take top 3 updates from current briefing or defaults
  const topUpdates = updates.length > 0 ? updates.slice(0, 3) : [];
  const upd1 = topUpdates[0];
  const upd2 = topUpdates[1];
  const upd3 = topUpdates[2];

  const handleExportPng = async () => {
    if (!cardRef.current) return;
    try {
      setIsExporting(true);
      const dataUrl = await toPng(cardRef.current, {
        cacheBust: true,
        pixelRatio: 2, // High resolution output
      });
      const link = document.createElement('a');
      link.download = `CA_Status_Card_${activeCardIndex}_${briefingDate.replace(/\s+/g, '_')}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Export PNG failed:', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-purple-600 mb-1">
            <Smartphone className="w-4 h-4" />
            <span>MODULE 9 — DAILY STATUS STUDIO (WHATSAPP 9:16)</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">Professional Status Card Studio</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Generates 5 sequential 9:16 vertical cards designed for Chartered Accountant WhatsApp & LinkedIn status updates
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleExportPng}
            disabled={isExporting}
            className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-700 hover:from-purple-500 hover:to-indigo-600 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-purple-900/20 transition-all cursor-pointer disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{isExporting ? 'Exporting Image...' : 'DOWNLOAD CARD AS PNG IMAGE'}</span>
          </button>
        </div>
      </div>

      {/* Card Selector Pills */}
      <div className="flex items-center justify-center space-x-2 bg-white border border-slate-200 p-2 rounded-2xl shadow-xs overflow-x-auto text-xs">
        {[
          { idx: 1, label: 'Card 1: COVER' },
          { idx: 2, label: 'Card 2: TOP UPDATE 1' },
          { idx: 3, label: 'Card 3: TOP UPDATE 2' },
          { idx: 4, label: 'Card 4: TOP UPDATE 3 / MARKET' },
          { idx: 5, label: 'Card 5: ACTION SUMMARY' },
        ].map((item) => (
          <button
            key={item.idx}
            onClick={() => setActiveCardIndex(item.idx)}
            className={`px-4 py-2 rounded-xl font-bold transition-all cursor-pointer ${
              activeCardIndex === item.idx
                ? 'bg-purple-600 text-white shadow-md'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Live Interactive 9:16 Preview Container */}
      <div className="flex flex-col items-center justify-center py-6">
        {/* Device Frame Wrapper */}
        <div className="relative p-3 bg-slate-900 rounded-[32px] shadow-2xl border-4 border-slate-800">
          {/* Top Notch */}
          <div className="w-28 h-4 bg-slate-800 rounded-b-xl mx-auto mb-2" />

          {/* 9:16 Card Canvas (360px x 640px) */}
          <div
            ref={cardRef}
            className="w-[360px] h-[640px] bg-slate-950 text-white rounded-[24px] p-6 flex flex-col justify-between overflow-hidden relative select-none shadow-inner border border-slate-800"
            style={{
              backgroundImage: 'radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.15), transparent 70%)',
            }}
          >
            {/* CARD 1: COVER */}
            {activeCardIndex === 1 && (
              <>
                <div className="space-y-6">
                  {/* Top Brand Tag */}
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                    <div className="flex items-center space-x-2">
                      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-slate-950 font-bold">
                        <ShieldCheck className="w-4 h-4" />
                      </div>
                      <span className="text-[11px] font-extrabold tracking-wider text-amber-400 uppercase">
                        CA ADVISORY AGENT
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      {briefingDate}
                    </span>
                  </div>

                  {/* Main Title Banner */}
                  <div className="space-y-3 pt-6">
                    <span className="inline-block px-3 py-1 bg-blue-500/20 text-blue-300 border border-blue-500/30 font-bold text-[10px] rounded-full uppercase tracking-widest">
                      DAILY REGULATORY BRIEFING
                    </span>
                    <h2 className="text-2xl font-extrabold tracking-tight text-white leading-tight">
                      Regulatory & Market Intelligence Status
                    </h2>
                    <p className="text-xs text-slate-300 leading-relaxed pt-1">
                      Key GST, Income Tax, MCA, RBI & Macroeconomic developments impacting Indian businesses today.
                    </p>
                  </div>

                  {/* Highlight Bullets */}
                  <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-xl space-y-2.5 text-xs text-slate-200">
                    <div className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-amber-400" />
                      <span className="font-semibold text-amber-300">5 Key Developments Analyzed</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-blue-400" />
                      <span>E-Invoicing & MSME Sec 43B(h) Rules</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span>MCA Private Demat & RBI Forex</span>
                    </div>
                  </div>
                </div>

                {/* Footer Brand */}
                <div className="border-t border-slate-800/80 pt-3 flex items-center justify-between text-[10px] text-slate-400">
                  <span>General Professional Information</span>
                  <span className="font-bold text-amber-400">Chartered Accountants</span>
                </div>
              </>
            )}

            {/* CARD 2: TOP UPDATE 1 */}
            {activeCardIndex === 2 && (
              <>
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="px-2.5 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-extrabold rounded uppercase">
                      {upd1?.category || 'GST'} UPDATE
                    </span>
                    <span className="text-[10px] text-red-400 font-bold uppercase">{upd1?.riskLevel || 'CRITICAL'} RISK</span>
                  </div>

                  <h3 className="text-base font-extrabold text-white leading-snug">
                    {upd1?.title || 'GST E-Invoicing Threshold Lowered to ₹2 Crore'}
                  </h3>

                  <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-xl space-y-2 text-xs">
                    <div>
                      <span className="text-amber-400 font-bold block text-[10px] uppercase">What Changed?</span>
                      <p className="text-slate-200 text-[11px] leading-relaxed">
                        {upd1?.impactAnalysis?.whatChanged || 'E-invoicing mandated for all businesses with turnover > ₹2 Cr.'}
                      </p>
                    </div>

                    <div>
                      <span className="text-blue-400 font-bold block text-[10px] uppercase">Who Should Care?</span>
                      <p className="text-slate-300 text-[11px]">
                        {upd1?.impactAnalysis?.whoIsAffected || 'All GST registered sellers & distributors.'}
                      </p>
                    </div>

                    <div>
                      <span className="text-emerald-400 font-bold block text-[10px] uppercase">Key Action Required:</span>
                      <p className="text-slate-200 text-[11px]">
                        {upd1?.impactAnalysis?.recommendedAction.slice(0, 120) || 'Upgrade ERP billing software prior to deadline.'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-red-950/40 border border-red-800/40 rounded-xl text-center">
                  <span className="text-red-300 font-extrabold text-xs">STATUTORY DEADLINE: {upd1?.deadline || '01 OCT 2026'}</span>
                </div>
              </>
            )}

            {/* CARD 3: TOP UPDATE 2 */}
            {activeCardIndex === 3 && (
              <>
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="px-2.5 py-0.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[10px] font-extrabold rounded uppercase">
                      {upd2?.category || 'INCOME TAX'} UPDATE
                    </span>
                    <span className="text-[10px] text-amber-400 font-bold uppercase">{upd2?.riskLevel || 'HIGH'} RISK</span>
                  </div>

                  <h3 className="text-base font-extrabold text-white leading-snug">
                    {upd2?.title || 'Strict Disallowance u/s 43B(h) for MSME Supplier Payments'}
                  </h3>

                  <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-xl space-y-2 text-xs">
                    <div>
                      <span className="text-amber-400 font-bold block text-[10px] uppercase">What Changed?</span>
                      <p className="text-slate-200 text-[11px] leading-relaxed">
                        {upd2?.impactAnalysis?.whatChanged || 'Mandatory 45-day payment cutoff for MSME vendors or tax disallowance at 30%.'}
                      </p>
                    </div>

                    <div>
                      <span className="text-blue-400 font-bold block text-[10px] uppercase">Who Should Care?</span>
                      <p className="text-slate-300 text-[11px]">
                        {upd2?.impactAnalysis?.whoIsAffected || 'All businesses procuring goods from Micro/Small enterprises.'}
                      </p>
                    </div>

                    <div>
                      <span className="text-emerald-400 font-bold block text-[10px] uppercase">Key Action Required:</span>
                      <p className="text-slate-200 text-[11px]">
                        {upd2?.impactAnalysis?.recommendedAction.slice(0, 120) || 'Conduct Udyam classification drive for vendor masters.'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-amber-950/40 border border-amber-800/40 rounded-xl text-center">
                  <span className="text-amber-300 font-extrabold text-xs">ACTION TIMELINE: {upd2?.deadline || '30 SEPT 2026'}</span>
                </div>
              </>
            )}

            {/* CARD 4: TOP UPDATE 3 / MARKET */}
            {activeCardIndex === 4 && (
              <>
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="px-2.5 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] font-extrabold rounded uppercase">
                      FOREX & MARKET ALERT
                    </span>
                    <span className="text-[10px] text-purple-300 font-bold uppercase">MACRO IMPACT</span>
                  </div>

                  <h3 className="text-base font-extrabold text-white leading-snug">
                    {upd3?.title || 'Rupee Touches 84.20/USD & Brent Crude Surges to $88/bbl'}
                  </h3>

                  {/* Market Visual Bar Representation */}
                  <div className="p-3.5 bg-slate-900 border border-slate-800 rounded-xl space-y-3 text-xs">
                    <div>
                      <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                        <span>USD/INR Exchange Rate</span>
                        <span className="text-red-400 font-bold">84.20 (+2.4%)</span>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div className="bg-red-500 h-full w-[82%]" />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                        <span>Brent Crude Oil</span>
                        <span className="text-amber-400 font-bold">$88.50/bbl (+6.2%)</span>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div className="bg-amber-500 h-full w-[88%]" />
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-300">
                      <span className="font-bold text-amber-400">Business Takeaway:</span> Importers should evaluate 60-day forward cover hedging for USD payables.
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-purple-950/40 border border-purple-800/40 rounded-xl text-center">
                  <span className="text-purple-300 font-extrabold text-xs">CFO TREASURY ACTION RECOMMENDED</span>
                </div>
              </>
            )}

            {/* CARD 5: ACTION SUMMARY */}
            {activeCardIndex === 5 && (
              <>
                <div className="space-y-5">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="px-2.5 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-extrabold rounded uppercase">
                      TODAY'S ACTION SUMMARY
                    </span>
                    <span className="text-[10px] text-emerald-400 font-bold uppercase">CHECKLIST</span>
                  </div>

                  <h3 className="text-lg font-extrabold text-white">What Businesses Should Watch Today:</h3>

                  <div className="space-y-2.5 text-xs">
                    <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl flex items-start space-x-2.5">
                      <span className="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 font-bold flex items-center justify-center shrink-0 text-[10px]">
                        1
                      </span>
                      <span className="text-slate-200 text-[11px] leading-relaxed">
                        Verify aggregate turnover for GST e-invoicing ₹2 Cr threshold eligibility.
                      </span>
                    </div>

                    <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl flex items-start space-x-2.5">
                      <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 font-bold flex items-center justify-center shrink-0 text-[10px]">
                        2
                      </span>
                      <span className="text-slate-200 text-[11px] leading-relaxed">
                        Tag vendor master with Udyam classification for Sec 43B(h) compliance.
                      </span>
                    </div>

                    <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl flex items-start space-x-2.5">
                      <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold flex items-center justify-center shrink-0 text-[10px]">
                        3
                      </span>
                      <span className="text-slate-200 text-[11px] leading-relaxed">
                        Appoint RTA and secure ISIN for private company share dematerialisation.
                      </span>
                    </div>
                  </div>
                </div>

                <div className="border-t border-slate-800 pt-3 text-center text-[10px] text-slate-400">
                  Shared for <span className="font-bold text-amber-400">General Professional Information</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
