import React, { useState } from 'react';
import { Client, NoticeCase, NoticeIssue, DocumentItem, ReconciliationItem, FirmSettings } from '../types';
import { generateClientEmail, generateWordReplyDocument } from '../services/documentGenerator';
import {
  FileCheck2,
  Mail,
  Download,
  Copy,
  Check,
  Send,
  FileText,
} from 'lucide-react';

interface ReplyGeneratorViewProps {
  activeClient: Client | null;
  activeCase: NoticeCase | null;
  issues: NoticeIssue[];
  reconciliations: ReconciliationItem[];
  documentItems: DocumentItem[];
  firmSettings: FirmSettings;
}

export const ReplyGeneratorView: React.FC<ReplyGeneratorViewProps> = ({
  activeClient,
  activeCase,
  issues,
  reconciliations,
  documentItems,
  firmSettings,
}) => {
  const [emailTab, setEmailTab] = useState<'REQUEST' | 'FOLLOWUP'>('REQUEST');
  const [emailSubject, setEmailSubject] = useState('');
  const [emailBody, setEmailBody] = useState('');
  const [copied, setCopied] = useState(false);
  const [isGeneratingDocx, setIsGeneratingDocx] = useState(false);

  React.useEffect(() => {
    if (!activeClient || !activeCase) return;
    const draft = generateClientEmail(emailTab, activeClient, activeCase, issues, documentItems);
    setEmailSubject(draft.subject);
    setEmailBody(draft.body);
  }, [emailTab, activeClient, activeCase, issues, documentItems]);

  if (!activeCase || !activeClient) {
    return (
      <div className="flex items-center justify-center h-full p-8 text-gray-500 text-xs">
        No active notice selected. Please select a notice to generate legal reply and emails.
      </div>
    );
  }

  const handleCopyEmail = () => {
    navigator.clipboard.writeText(`${emailSubject}\n\n${emailBody}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadWordDoc = async () => {
    setIsGeneratingDocx(true);
    try {
      await generateWordReplyDocument(activeClient, activeCase, issues, reconciliations, firmSettings);
    } finally {
      setIsGeneratingDocx(false);
    }
  };

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full bg-[#F8FAFC]">
      <div className="bg-white rounded-2xl p-5 border border-gray-200 shadow-2xs flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-indigo-50 text-indigo-700 rounded-xl border border-indigo-200">
            <FileCheck2 className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900">
              CA Legal Reply Builder & Client Communication Studio
            </h1>
            <p className="text-xs text-gray-500">
              Generate ready-to-file legal submissions in Microsoft Word (.docx) & structured client document request emails.
            </p>
          </div>
        </div>

        <button
          onClick={handleDownloadWordDoc}
          disabled={isGeneratingDocx}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#4338CA] hover:bg-[#3730A3] text-white rounded-xl text-xs font-bold transition-all shadow-sm active:scale-98 cursor-pointer"
        >
          <Download className="w-4 h-4" />
          <span>{isGeneratingDocx ? 'Generating Word File...' : 'Download Word Reply (.docx)'}</span>
        </button>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-2xs flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#4338CA]" />
                <span className="text-xs font-bold text-gray-900 uppercase tracking-wider">
                  Formal Legal Written Submission Preview
                </span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-50 text-[#4338CA] font-bold border border-indigo-200">
                Word (.docx) Formatted
              </span>
            </div>

            <div className="bg-[#F9FAFB] border border-gray-200 rounded-xl p-4 font-serif text-[11px] text-gray-800 space-y-2.5 leading-relaxed max-h-96 overflow-y-auto select-text">
              <div className="text-center font-sans">
                <div className="font-bold text-xs tracking-wider text-gray-900 uppercase">
                  {firmSettings.letterheadHeader || firmSettings.caFirmName}
                </div>
                <div className="text-[10px] text-gray-500 font-normal">
                  {firmSettings.firmAddress} • Email: {firmSettings.contactEmail}
                </div>
              </div>

              <div className="border-t border-gray-300 pt-2 text-right text-[10px] font-sans">
                Date: {new Date().toLocaleDateString('en-IN')}
              </div>

              <div>
                <div className="font-bold">To,</div>
                <div>{activeCase.issuingAuthority}</div>
                <div>Goods and Services Tax Department</div>
              </div>

              <div className="font-bold underline text-gray-900">
                SUBJECT: WRITTEN SUBMISSION / PRELIMINARY REPLY TO NOTICE {activeCase.formType} (REF: {activeCase.noticeNumber}) FOR FY {activeCase.financialYear}.
              </div>

              <div>
                <span className="font-bold">Taxpayer:</span> {activeClient.legalName} | <span className="font-bold">GSTIN:</span> {activeClient.gstin}
              </div>

              <p>
                1. The Assessee has diligently discharged statutory taxes and filed all monthly GSTR-3B & GSTR-1 returns within prescribed due dates...
              </p>

              <div className="font-bold text-gray-900">
                2. POINTED SUBMISSIONS ON IMPUGNED ISSUES:
              </div>

              {issues.map((iss, i) => {
                const recs = reconciliations.filter((r) => r.issueNumber === iss.issueNumber && r.status !== 'MISSING_DATA');
                return (
                  <div key={iss.id} className="pl-2 border-l-2 border-indigo-300 space-y-1">
                    <div className="font-bold text-gray-900">
                      2.{i + 1} {iss.title} (Disputed Tax: ₹{iss.taxAmount.toLocaleString('en-IN')})
                    </div>
                    <div className="text-gray-600">
                      <span className="font-semibold">Submissions:</span> {iss.defensePoints}
                    </div>
                    {recs.map((r) => (
                      <div key={r.id} className="text-emerald-900 text-[10px]">
                        <span className="font-semibold">Reconciliation:</span> {r.reconType} — demand ₹{r.noticeValue.toLocaleString('en-IN')} vs return ₹{r.portalValue.toLocaleString('en-IN')} vs books ₹{r.booksValue.toLocaleString('en-IN')}, variance ₹{r.variance.toLocaleString('en-IN')} ({r.status}).
                      </div>
                    ))}
                    <div className="text-indigo-900 text-[10px]">
                      <span className="font-semibold">Legal Reliance:</span> {iss.legalPosition}
                    </div>
                  </div>
                );
              })}

              {reconciliations.some((r) => r.status !== 'MISSING_DATA') && (
                <>
                  <div className="font-bold text-gray-900 mt-2">2A. RECONCILIATION OF FIGURES:</div>
                  {reconciliations.filter((r) => r.status !== 'MISSING_DATA').map((r) => (
                    <div key={r.id} className="text-[10px] text-gray-700">
                      • <span className="font-semibold">{r.reconType}:</span> ₹{r.variance.toLocaleString('en-IN')} variance ({r.status}). {r.varianceReason}
                    </div>
                  ))}
                </>
              )}

              <div className="font-bold text-gray-900 mt-2">
                3. PRAYER & RELIEF SOUGHT:
              </div>
              <p>
                Accept this written explanation and drop the proposed demand of Tax, Interest, and Penalty in its entirety.
              </p>
            </div>
          </div>

          <button
            onClick={handleDownloadWordDoc}
            disabled={isGeneratingDocx}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#4338CA] hover:bg-[#3730A3] text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>Download Formatted Word Reply (.docx)</span>
          </button>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-2xs flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-indigo-700" />
                <span className="text-xs font-bold text-gray-900 uppercase tracking-wider">
                  Client Communication Email Studio
                </span>
              </div>

              <div className="flex bg-gray-100 p-0.5 rounded-lg text-[10px] font-bold">
                <button
                  onClick={() => setEmailTab('REQUEST')}
                  className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                    emailTab === 'REQUEST' ? 'bg-white text-indigo-900 shadow-2xs' : 'text-gray-500'
                  }`}
                >
                  Document Request
                </button>
                <button
                  onClick={() => setEmailTab('FOLLOWUP')}
                  className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                    emailTab === 'FOLLOWUP' ? 'bg-white text-indigo-900 shadow-2xs' : 'text-gray-500'
                  }`}
                >
                  Follow-up Reminder
                </button>
              </div>
            </div>

            <div className="space-y-2 text-xs">
              <div>
                <label className="block font-bold text-gray-700 mb-1">To (Client Email)</label>
                <input
                  type="text"
                  value={activeClient.email}
                  readOnly
                  className="w-full px-3 py-1.5 border border-gray-200 rounded-lg bg-gray-50 text-gray-700 font-mono text-xs"
                />
              </div>

              <div>
                <label className="block font-bold text-gray-700 mb-1">Subject Line</label>
                <input
                  type="text"
                  value={emailSubject}
                  onChange={(e) => setEmailSubject(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded-lg font-bold text-gray-900 focus:outline-none focus:border-[#4338CA]"
                />
              </div>

              <div>
                <label className="block font-bold text-gray-700 mb-1">Editable Email Body</label>
                <textarea
                  rows={9}
                  value={emailBody}
                  onChange={(e) => setEmailBody(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-xl font-mono text-[11px] leading-relaxed focus:outline-none focus:border-[#4338CA]"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleCopyEmail}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-800 rounded-xl text-xs font-bold transition-all shadow-2xs cursor-pointer"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
              <span>{copied ? 'Copied to Clipboard!' : 'Copy Email Body'}</span>
            </button>

            <a
              href={`mailto:${activeClient.email}?subject=${encodeURIComponent(emailSubject)}&body=${encodeURIComponent(emailBody)}`}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-indigo-700 hover:bg-indigo-800 text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer text-center"
            >
              <Send className="w-4 h-4" />
              <span>Open in Outlook / Mail App</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
