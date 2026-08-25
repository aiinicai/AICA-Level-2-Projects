import React, { useState } from 'react';
import {
  FileText,
  Copy,
  Check,
  Building2,
  Clock,
  ShieldCheck,
  Send,
  MessageSquare,
  ClipboardList,
  AlertCircle,
  Download,
  Globe,
  HelpCircle,
} from 'lucide-react';
import { ClientAdvisory } from '../types';

interface ClientAdvisoriesViewProps {
  advisories: ClientAdvisory[];
  onApproveAdvisory: (advisoryId: string) => void;
}

export const ClientAdvisoriesView: React.FC<ClientAdvisoriesViewProps> = ({
  advisories,
  onApproveAdvisory,
}) => {
  const [selectedAdvisory, setSelectedAdvisory] = useState<ClientAdvisory | null>(
    advisories.length > 0 ? advisories[0] : null
  );
  const [activeFormat, setActiveFormat] = useState<'formal' | 'plain' | 'short' | 'management' | 'internal'>('plain');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const activeAdvisory = selectedAdvisory || (advisories.length > 0 ? advisories[0] : null);

  const handleCopyText = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(label);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
            <FileText className="w-4 h-4" />
            <span>MODULE 7 — MULTILINGUAL CLIENT ADVISORY GENERATOR V2</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">Generated Client Advisories ({advisories.length})</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Plain English client communications, regional translations, WhatsApp alerts & formal advisories.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Advisories List */}
        <div className="lg:col-span-4 space-y-2">
          {advisories.length === 0 ? (
            <div className="p-8 text-center bg-white border border-slate-200 rounded-2xl">
              <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-xs text-slate-500">No client advisories generated yet. Select a client in Client Matching and click "Generate Advisory".</p>
            </div>
          ) : (
            advisories.map((adv) => {
              const isSelected = activeAdvisory?.id === adv.id;
              return (
                <div
                  key={adv.id}
                  onClick={() => setSelectedAdvisory(adv)}
                  className={`p-3.5 rounded-2xl border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-teal-50/90 border-teal-500 shadow-xs'
                      : 'bg-white border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-bold text-slate-900 truncate">{adv.clientName}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        adv.approvalStatus === 'Approved'
                          ? 'bg-emerald-100 text-emerald-800'
                          : adv.approvalStatus === 'Pending Review'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {adv.approvalStatus}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600 line-clamp-2 mt-1">
                    {adv.formalAdvisory.subject}
                  </p>

                  <div className="mt-2 text-[10px] text-slate-400">
                    Deadline: {adv.formalAdvisory.statutoryDate}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Output Viewer */}
        <div className="lg:col-span-8">
          {activeAdvisory ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-5">
              {/* Output Format Switcher Tabs */}
              <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-3 text-xs">
                <button
                  onClick={() => setActiveFormat('plain')}
                  className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-xl font-bold transition-all cursor-pointer ${
                    activeFormat === 'plain'
                      ? 'bg-teal-700 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>1. Plain English Client Alert</span>
                </button>

                <button
                  onClick={() => setActiveFormat('short')}
                  className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-xl font-bold transition-all cursor-pointer ${
                    activeFormat === 'short'
                      ? 'bg-teal-700 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>2. WhatsApp Alert (Short)</span>
                </button>

                <button
                  onClick={() => setActiveFormat('formal')}
                  className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-xl font-bold transition-all cursor-pointer ${
                    activeFormat === 'formal'
                      ? 'bg-teal-700 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>3. Formal Legal Advisory</span>
                </button>

                <button
                  onClick={() => setActiveFormat('management')}
                  className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-xl font-bold transition-all cursor-pointer ${
                    activeFormat === 'management'
                      ? 'bg-teal-700 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <Building2 className="w-3.5 h-3.5" />
                  <span>4. Management Note</span>
                </button>
              </div>

              {/* Format 1: Plain English Client Communication (Requirement G) */}
              {activeFormat === 'plain' && (
                <div className="space-y-4 text-xs">
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                    <div className="text-sm font-bold text-slate-900 border-b border-slate-200 pb-2">
                      PLAIN LANGUAGE CLIENT ALERT — {activeAdvisory.clientName}
                    </div>

                    <div className="space-y-3 text-slate-800 leading-relaxed">
                      <div>
                        <span className="font-bold text-teal-800 uppercase text-[10px] block">WHAT HAPPENED?</span>
                        <p className="mt-0.5">{activeAdvisory.plainLanguageCommunication.whatHappened}</p>
                      </div>

                      <div>
                        <span className="font-bold text-teal-800 uppercase text-[10px] block">DOES THIS AFFECT MY BUSINESS?</span>
                        <p className="mt-0.5">{activeAdvisory.plainLanguageCommunication.doesThisAffectMyBusiness}</p>
                      </div>

                      <div>
                        <span className="font-bold text-teal-800 uppercase text-[10px] block">WHY DOES IT MATTER?</span>
                        <p className="mt-0.5">{activeAdvisory.plainLanguageCommunication.whyDoesItMatter}</p>
                      </div>

                      <div>
                        <span className="font-bold text-teal-800 uppercase text-[10px] block">WHAT SHOULD I DO?</span>
                        <p className="mt-0.5">{activeAdvisory.plainLanguageCommunication.whatShouldIDo}</p>
                      </div>

                      <div>
                        <span className="font-bold text-teal-800 uppercase text-[10px] block">BY WHEN?</span>
                        <p className="mt-0.5 font-bold text-rose-700">{activeAdvisory.plainLanguageCommunication.byWhen}</p>
                      </div>

                      <div>
                        <span className="font-bold text-teal-800 uppercase text-[10px] block">WHAT WILL MY CA / ADVISOR DO?</span>
                        <p className="mt-0.5">{activeAdvisory.plainLanguageCommunication.whatWillMyCaDo}</p>
                      </div>
                    </div>

                    {/* Regional Language Section if available */}
                    {activeAdvisory.plainLanguageCommunication.regionalLanguageText && (
                      <div className="mt-4 pt-3 border-t border-slate-200 p-3 bg-teal-50 border border-teal-200 rounded-xl">
                        <span className="font-bold text-teal-900 block text-xs mb-1">
                          {activeAdvisory.plainLanguageCommunication.regionalLanguageText.languageHeader}
                        </span>
                        <p className="text-teal-950 leading-relaxed text-xs">
                          {activeAdvisory.plainLanguageCommunication.regionalLanguageText.summary}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="flex justify-end space-x-2">
                    <button
                      onClick={() =>
                        handleCopyText(
                          `${activeAdvisory.plainLanguageCommunication.whatHappened}\n\nAFFECTS BUSINESS: ${activeAdvisory.plainLanguageCommunication.doesThisAffectMyBusiness}\n\nWHY IT MATTERS: ${activeAdvisory.plainLanguageCommunication.whyDoesItMatter}\n\nWHAT TO DO: ${activeAdvisory.plainLanguageCommunication.whatShouldIDo}\n\nBY WHEN: ${activeAdvisory.plainLanguageCommunication.byWhen}`,
                          'email'
                        )
                      }
                      className="flex items-center space-x-1.5 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all cursor-pointer shadow-xs"
                    >
                      {copiedId === 'email' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedId === 'email' ? 'COPIED!' : 'COPY EMAIL TEXT'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Format 2: Short WhatsApp Alert */}
              {activeFormat === 'short' && (
                <div className="space-y-3">
                  <div className="p-4 bg-emerald-50/80 border border-emerald-200/80 rounded-xl font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed relative">
                    {activeAdvisory.shortAlert.fullFormattedText}
                  </div>

                  <div className="flex justify-end">
                    <button
                      onClick={() => handleCopyText(activeAdvisory.shortAlert.fullFormattedText, 'wa')}
                      className="flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all cursor-pointer shadow-xs"
                    >
                      {copiedId === 'wa' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedId === 'wa' ? 'COPIED!' : 'COPY WHATSAPP ALERT'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Format 3: Formal Legal Advisory */}
              {activeFormat === 'formal' && (
                <div className="space-y-4 text-xs">
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                    <div className="text-sm font-bold text-slate-900 border-b border-slate-200 pb-2">
                      {activeAdvisory.formalAdvisory.subject}
                    </div>

                    <div>
                      <span className="font-bold text-slate-800 uppercase text-[10px] block">Key Regulatory Development:</span>
                      <p className="text-slate-700 leading-relaxed mt-0.5">{activeAdvisory.formalAdvisory.development}</p>
                    </div>

                    <div>
                      <span className="font-bold text-slate-800 uppercase text-[10px] block">Applicability to Your Enterprise:</span>
                      <p className="text-slate-700 leading-relaxed mt-0.5">{activeAdvisory.formalAdvisory.applicability}</p>
                    </div>

                    <div>
                      <span className="font-bold text-slate-800 uppercase text-[10px] block">Business & Financial Impact:</span>
                      <p className="text-slate-700 leading-relaxed mt-0.5">{activeAdvisory.formalAdvisory.clientSpecificImpact}</p>
                    </div>

                    <div>
                      <span className="font-bold text-slate-800 uppercase text-[10px] block">Required Action & Statutory Date:</span>
                      <p className="text-slate-700 leading-relaxed mt-0.5">{activeAdvisory.formalAdvisory.requiredAction}</p>
                      <div className="font-bold text-rose-600 mt-1">Statutory Date: {activeAdvisory.formalAdvisory.statutoryDate}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Format 4: Management Note */}
              {activeFormat === 'management' && (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 text-xs">
                  <div className="font-bold text-slate-900 border-b border-slate-200 pb-2 text-sm">
                    Executive Management Action Note
                  </div>

                  <div>
                    <span className="font-bold text-slate-700 text-[10px] uppercase block">Issue:</span>
                    <span className="text-slate-800">{activeAdvisory.managementNote.issue}</span>
                  </div>

                  <div>
                    <span className="font-bold text-slate-700 text-[10px] uppercase block">Risk Level:</span>
                    <span className="text-rose-600 font-bold">{activeAdvisory.managementNote.risk}</span>
                  </div>

                  <div>
                    <span className="font-bold text-slate-700 text-[10px] uppercase block">Financial Implication:</span>
                    <span className="text-slate-800">{activeAdvisory.managementNote.financialImplication}</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-20 bg-white border border-slate-200 rounded-2xl">
              <p className="text-slate-500 text-xs">Select an advisory from the left list to view generated outputs.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
