import React from 'react';
import { EngagementData, AcceptanceChecklistItem } from '../../types';
import { ShieldCheck, FileCheck, Info, CheckCircle2, XCircle, HelpCircle } from 'lucide-react';

interface Stage1Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

export const Stage1ClientAcceptance: React.FC<Stage1Props> = ({
  engagement,
  onChange,
}) => {
  const updateField = <K extends keyof EngagementData>(key: K, value: EngagementData[K]) => {
    onChange({ ...engagement, [key]: value });
  };

  const updateChecklistItem = (id: string, updates: Partial<AcceptanceChecklistItem>) => {
    const updatedChecklist = engagement.acceptanceChecklist.map((item) =>
      item.id === id ? { ...item, ...updates } : item
    );
    onChange({ ...engagement, acceptanceChecklist: updatedChecklist });
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Stage Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 01 • SQC 1 / SA 220
          </span>
          <span className="text-xs text-stone-500">Quality Control for Engagements</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Engagement & Client Acceptance / Continuance
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Evaluate independence, competence, integrity of leadership, and statutory clearances before executing the audit engagement letter.
        </p>
      </div>

      {/* Client & Engagement Metadata Card */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
          <FileCheck className="w-4 h-4 text-amber-700 dark:text-amber-400" />
          <span>Client & Statutory Information</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Client Legal Name *
            </label>
            <input
              type="text"
              value={engagement.clientName}
              onChange={(e) => updateField('clientName', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700"
            />
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Corporate Identification Number (CIN)
            </label>
            <input
              type="text"
              value={engagement.cin}
              onChange={(e) => updateField('cin', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 font-mono-num"
            />
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Permanent Account Number (PAN)
            </label>
            <input
              type="text"
              value={engagement.pan}
              onChange={(e) => updateField('pan', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 font-mono-num"
            />
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Financial Year
            </label>
            <input
              type="text"
              value={engagement.financialYear}
              onChange={(e) => updateField('financialYear', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 font-mono-num"
            />
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Audit Period
            </label>
            <input
              type="text"
              value={engagement.auditPeriod}
              onChange={(e) => updateField('auditPeriod', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700"
            />
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Audit Engagement Type
            </label>
            <select
              value={engagement.auditType}
              onChange={(e) => updateField('auditType', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700"
            >
              <option value="Statutory Audit under Companies Act 2013">Statutory Audit under Companies Act 2013</option>
              <option value="Tax Audit under Section 44AB">Tax Audit under Section 44AB</option>
              <option value="Limited Review / Interim Financial Information">Limited Review / Interim</option>
              <option value="Group Component Audit (SA 600)">Group Component Audit (SA 600)</option>
            </select>
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Engagement Partner
            </label>
            <input
              type="text"
              value={engagement.engagementPartner}
              onChange={(e) => updateField('engagementPartner', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700"
            />
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Audit Senior / Manager
            </label>
            <input
              type="text"
              value={engagement.auditSenior}
              onChange={(e) => updateField('auditSenior', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700"
            />
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Preceding Auditor
            </label>
            <input
              type="text"
              value={engagement.precedingAuditor}
              onChange={(e) => updateField('precedingAuditor', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700"
            />
          </div>

          <div className="md:col-span-3">
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Registered Office Address
            </label>
            <input
              type="text"
              value={engagement.registeredAddress}
              onChange={(e) => updateField('registeredAddress', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700"
            />
          </div>
        </div>
      </div>

      {/* Acceptance Checklist Table */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-amber-700 dark:text-amber-400" />
            <span>Pre-Engagement Checklist (SQC 1 / SA 220)</span>
          </h3>
          <span className="text-xs text-stone-500">
            {engagement.acceptanceChecklist.filter((c) => c.status === 'Yes').length} of {engagement.acceptanceChecklist.length} requirements met
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#1a2027] text-stone-600 dark:text-stone-400">
                <th className="py-2.5 px-3 font-semibold w-10">#</th>
                <th className="py-2.5 px-3 font-semibold w-1/3">Evaluation Factor & Standard Ref</th>
                <th className="py-2.5 px-3 font-semibold w-36 text-center">Status</th>
                <th className="py-2.5 px-3 font-semibold">Documented Rationale & Inquiries</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
              {engagement.acceptanceChecklist.map((item, idx) => (
                <tr key={item.id} className="hover:bg-stone-50/50 dark:hover:bg-[#191e25]">
                  <td className="py-3 px-3 font-mono-num text-stone-400 font-semibold align-top">
                    {idx + 1}
                  </td>
                  <td className="py-3 px-3 align-top">
                    <p className="font-medium text-stone-900 dark:text-stone-100">
                      {item.item}
                    </p>
                    <span className="text-[10px] text-amber-800 dark:text-amber-400 font-mono-num mt-0.5 inline-block">
                      {item.standardRef}
                    </span>
                  </td>
                  <td className="py-3 px-3 align-top text-center">
                    <div className="inline-flex rounded-md shadow-xs" role="group">
                      {(['Yes', 'No', 'N.A.'] as const).map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => updateChecklistItem(item.id, { status: opt })}
                          className={`px-2.5 py-1 text-xs font-semibold border first:rounded-l-md last:rounded-r-md transition-colors ${
                            item.status === opt
                              ? opt === 'Yes'
                                ? 'bg-emerald-700 text-white border-emerald-700 dark:bg-emerald-600'
                                : opt === 'No'
                                ? 'bg-rose-700 text-white border-rose-700 dark:bg-rose-600'
                                : 'bg-stone-700 text-white border-stone-700'
                              : 'bg-white dark:bg-[#1a2027] text-stone-700 dark:text-stone-300 border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800'
                          }`}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 align-top">
                    <textarea
                      rows={2}
                      value={item.rationale}
                      onChange={(e) => updateChecklistItem(item.id, { rationale: e.target.value })}
                      placeholder="Document inquiries made, records inspected, or basis for conclusion..."
                      className="w-full px-2.5 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 placeholder-stone-400 text-xs focus:border-amber-700"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Acceptance Conclusion Card */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
          Overall Client Acceptance / Continuance Conclusion
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Final Acceptance Decision *
            </label>
            <select
              value={engagement.acceptanceConclusion}
              onChange={(e) => updateField('acceptanceConclusion', e.target.value as any)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-semibold focus:border-amber-700"
            >
              <option value="Accepted">Accepted without Conditions</option>
              <option value="Accepted with Conditions">Accepted with Specific Conditions</option>
              <option value="Declined">Declined / Withdrawn</option>
            </select>
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Date of Acceptance / Review
            </label>
            <input
              type="date"
              value={engagement.dateOfAcceptance}
              onChange={(e) => updateField('dateOfAcceptance', e.target.value)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700"
            />
          </div>

          <div className="md:col-span-3">
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Concluding Remarks and Engagement Letter Execution Notes
            </label>
            <textarea
              rows={3}
              value={engagement.acceptanceNotes}
              onChange={(e) => updateField('acceptanceNotes', e.target.value)}
              placeholder="State any conditions, staffing arrangements, or follow-up communications..."
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 text-xs"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
