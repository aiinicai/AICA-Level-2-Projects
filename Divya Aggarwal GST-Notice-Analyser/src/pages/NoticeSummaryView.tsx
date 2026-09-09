import React, { useState } from 'react';
import { NoticeCase, NoticeIssue } from '../types';
import { Edit3, Check, ShieldCheck, ChevronRight } from 'lucide-react';
import { NoticePdfViewer } from '../components/NoticePdfViewer';
import { FEATURES } from '../config';

interface NoticeSummaryViewProps {
  activeCase: NoticeCase | null;
  issues: NoticeIssue[];
  onUpdateCase: (updated: NoticeCase) => Promise<void>;
  onNavigateToTab: (tab: any) => void;
}

export const NoticeSummaryView: React.FC<NoticeSummaryViewProps> = ({
  activeCase,
  issues,
  onUpdateCase,
  onNavigateToTab,
}) => {
  // All hooks MUST be called before any conditional return (Rules of Hooks)
  const [isEditMode, setIsEditMode] = useState(false);
  const [formData, setFormData] = useState<NoticeCase | null>(activeCase ? { ...activeCase } : null);
  const [isSaving, setIsSaving] = useState(false);

  React.useEffect(() => {
    if (activeCase) setFormData({ ...activeCase });
  }, [activeCase]);

  if (!activeCase || !formData) {
    return (
      <div className="flex items-center justify-center h-full p-8 text-gray-500 text-xs">
        No active notice case selected. Please select or upload a notice.
      </div>
    );
  }

  const handleSaveCorrection = async () => {
    setIsSaving(true);
    try {
      const tax = Number(formData.principalTax) || 0;
      const interest = Number(formData.interest) || 0;
      const penalty = Number(formData.penalty) || 0;
      const total = tax + interest + penalty;

      const updated: NoticeCase = {
        ...formData,
        principalTax: tax,
        interest,
        penalty,
        totalDemand: total,
        isCaVerified: true,
      };

      await onUpdateCase(updated);
      setIsEditMode(false);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex h-full overflow-hidden p-4 gap-4 bg-[#F8FAFC]">
      <div className="flex-1 h-full flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden shadow-xs">
        <div className="bg-[#F9FAFB] border-b border-gray-200 px-4 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#4338CA]" />
            <span className="text-xs font-bold text-gray-900 uppercase tracking-wider">
              {isEditMode ? 'CA Correction Mode (Editing Extractions)' : 'Notice Metadata & Verified Demand'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {isEditMode ? (
              <button
                disabled={isSaving}
                onClick={handleSaveCorrection}
                className="flex items-center gap-1 px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{isSaving ? 'Saving...' : 'Save & Verify'}</span>
              </button>
            ) : (
              <button
                onClick={() => setIsEditMode(true)}
                className="flex items-center gap-1 px-3 py-1 bg-[#4338CA] hover:bg-[#3730A3] text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Edit Extractions</span>
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
          <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
            activeCase.isCaVerified
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-amber-50 border-amber-200 text-amber-800'
          }`}>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span className="font-bold">
                {activeCase.isCaVerified ? 'Verified by Chartered Accountant' : 'Unverified OCR AI Extraction'}
              </span>
            </div>
            <span className="text-[11px] font-medium">
              {activeCase.isCaVerified ? 'Ready for Legal Reply Filing' : 'Click Edit Extractions to verify figures'}
            </span>
          </div>

          <div className="grid grid-cols-4 gap-2 text-center">
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-2.5">
              <div className="text-[10px] text-gray-500 font-bold uppercase">Principal Tax</div>
              {isEditMode ? (
                <input
                  type="number"
                  value={formData.principalTax}
                  onChange={(e) => setFormData({ ...formData, principalTax: Number(e.target.value) })}
                  className="w-full text-center mt-1 font-bold text-gray-900 border rounded py-0.5"
                />
              ) : (
                <div className="text-sm font-bold text-gray-900 mt-0.5">
                  ₹{activeCase.principalTax.toLocaleString('en-IN')}
                </div>
              )}
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-2.5">
              <div className="text-[10px] text-gray-500 font-bold uppercase">Interest (Sec 50)</div>
              {isEditMode ? (
                <input
                  type="number"
                  value={formData.interest}
                  onChange={(e) => setFormData({ ...formData, interest: Number(e.target.value) })}
                  className="w-full text-center mt-1 font-bold text-amber-700 border rounded py-0.5"
                />
              ) : (
                <div className="text-sm font-bold text-amber-700 mt-0.5">
                  ₹{activeCase.interest.toLocaleString('en-IN')}
                </div>
              )}
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-2.5">
              <div className="text-[10px] text-gray-500 font-bold uppercase">Penalty (Sec 122)</div>
              {isEditMode ? (
                <input
                  type="number"
                  value={formData.penalty}
                  onChange={(e) => setFormData({ ...formData, penalty: Number(e.target.value) })}
                  className="w-full text-center mt-1 font-bold text-red-700 border rounded py-0.5"
                />
              ) : (
                <div className="text-sm font-bold text-red-700 mt-0.5">
                  ₹{activeCase.penalty.toLocaleString('en-IN')}
                </div>
              )}
            </div>

            <div className="bg-[#EEF2FF] border border-indigo-200 rounded-lg p-2.5">
              <div className="text-[10px] text-[#4338CA] font-bold uppercase">Total Demand</div>
              <div className="text-sm font-black text-[#4338CA] mt-0.5">
                ₹{((isEditMode ? formData.principalTax + formData.interest + formData.penalty : activeCase.totalDemand)).toLocaleString('en-IN')}
              </div>
            </div>
          </div>

          <div className="border border-gray-200 rounded-xl overflow-hidden">
            <div className="bg-gray-50 px-3 py-2 font-bold text-gray-700 border-b border-gray-200">
              Statutory Proceeding Details
            </div>
            <div className="divide-y divide-gray-200">
              <div className="grid grid-cols-3 p-2.5">
                <span className="text-gray-500 font-medium">Notice Reference No.</span>
                <div className="col-span-2 font-bold text-gray-900">
                  {isEditMode ? (
                    <input
                      type="text"
                      value={formData.noticeNumber}
                      onChange={(e) => setFormData({ ...formData, noticeNumber: e.target.value })}
                      className="w-full border rounded px-2 py-0.5 text-xs font-mono"
                    />
                  ) : (
                    <span className="font-mono">{activeCase.noticeNumber}</span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 p-2.5">
                <span className="text-gray-500 font-medium">Document ID (DIN)</span>
                <div className="col-span-2 font-mono text-gray-700">
                  {isEditMode ? (
                    <input
                      type="text"
                      value={formData.din || ''}
                      onChange={(e) => setFormData({ ...formData, din: e.target.value })}
                      className="w-full border rounded px-2 py-0.5 text-xs font-mono"
                    />
                  ) : (
                    activeCase.din || 'Not cited on notice'
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 p-2.5">
                <span className="text-gray-500 font-medium">Period / Financial Year</span>
                <div className="col-span-2 font-semibold text-gray-800">
                  {isEditMode ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={formData.financialYear}
                        onChange={(e) => setFormData({ ...formData, financialYear: e.target.value })}
                        className="w-1/2 border rounded px-2 py-0.5 text-xs"
                        placeholder="FY 2022-23"
                      />
                      <input
                        type="text"
                        value={formData.period}
                        onChange={(e) => setFormData({ ...formData, period: e.target.value })}
                        className="w-1/2 border rounded px-2 py-0.5 text-xs"
                        placeholder="Period"
                      />
                    </div>
                  ) : (
                    `FY ${activeCase.financialYear} (${activeCase.period})`
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 p-2.5">
                <span className="text-gray-500 font-medium">Notice Date & Reply Due</span>
                <div className="col-span-2 flex items-center justify-between">
                  {isEditMode ? (
                    <div className="flex gap-2 w-full">
                      <input
                        type="text"
                        value={formData.noticeDate}
                        onChange={(e) => setFormData({ ...formData, noticeDate: e.target.value })}
                        className="w-1/2 border rounded px-2 py-0.5 text-xs"
                      />
                      <input
                        type="text"
                        value={formData.replyDeadline}
                        onChange={(e) => setFormData({ ...formData, replyDeadline: e.target.value })}
                        className="w-1/2 border rounded px-2 py-0.5 text-xs font-bold text-red-600"
                      />
                    </div>
                  ) : (
                    <>
                      <span>{activeCase.noticeDate}</span>
                      <span className="font-bold text-red-600">Due: {activeCase.replyDeadline}</span>
                    </>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 p-2.5">
                <span className="text-gray-500 font-medium">Personal Hearing Date</span>
                <div className="col-span-2 font-semibold text-indigo-700">
                  {isEditMode ? (
                    <input
                      type="text"
                      value={formData.hearingDate || ''}
                      onChange={(e) => setFormData({ ...formData, hearingDate: e.target.value })}
                      placeholder="e.g. 22-10-2024 11:30 AM"
                      className="w-full border rounded px-2 py-0.5 text-xs"
                    />
                  ) : (
                    activeCase.hearingDate || 'Not scheduled yet'
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 p-2.5">
                <span className="text-gray-500 font-medium">Issuing Authority</span>
                <div className="col-span-2 text-gray-800">
                  {isEditMode ? (
                    <input
                      type="text"
                      value={formData.issuingAuthority}
                      onChange={(e) => setFormData({ ...formData, issuingAuthority: e.target.value })}
                      className="w-full border rounded px-2 py-0.5 text-xs"
                    />
                  ) : (
                    activeCase.issuingAuthority
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 p-2.5">
                <span className="text-gray-500 font-medium">Sections & Rules Cited</span>
                <div className="col-span-2 text-gray-800 font-medium">
                  {isEditMode ? (
                    <input
                      type="text"
                      value={formData.sectionsMentioned}
                      onChange={(e) => setFormData({ ...formData, sectionsMentioned: e.target.value })}
                      className="w-full border rounded px-2 py-0.5 text-xs"
                    />
                  ) : (
                    activeCase.sectionsMentioned
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="border border-gray-200 rounded-xl p-3 bg-[#F9FAFB]">
            <div className="flex justify-between items-center mb-2">
              <span className="font-bold text-gray-800 text-xs">
                Extracted Dispute Points ({issues.length} Issues)
              </span>
              {FEATURES.figureSource && (
                <button
                  onClick={() => onNavigateToTab('figure_source')}
                  className="text-xs font-bold text-[#4338CA] hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <span>View Figure Sources</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <div className="space-y-2">
              {issues.map((iss) => (
                <div key={iss.id} className="bg-white p-2.5 rounded-lg border border-gray-200 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-gray-900">
                      {iss.issueNumber}. {iss.title}
                    </div>
                    <div className="text-[11px] text-gray-500">
                      {iss.sectionRule} • {iss.pageRef}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-[#4338CA]">
                      ₹{iss.taxAmount.toLocaleString('en-IN')}
                    </div>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      iss.riskLevel === 'HIGH' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {iss.riskLevel} RISK
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {(activeCase.pdfDataUrl || activeCase.rawText) && (
        <div className="hidden lg:flex w-[42%] h-full">
          <NoticePdfViewer
            pdfDataUrl={activeCase.pdfDataUrl}
            pdfFileName={activeCase.pdfFileName}
            rawText={activeCase.rawText}
            noticeNumber={activeCase.noticeNumber}
            formType={activeCase.formType}
          />
        </div>
      )}
    </div>
  );
};
