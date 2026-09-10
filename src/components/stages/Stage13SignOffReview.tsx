import React from 'react';
import { EngagementData, ReviewNoteItem, SignOffReviewData } from '../../types';
import { FileSignature, ShieldCheck, CheckCircle2, AlertTriangle, Plus, Trash2, Clock } from 'lucide-react';

interface Stage13Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

export const Stage13SignOffReview: React.FC<Stage13Props> = ({
  engagement,
  onChange,
}) => {
  const updateSignOff = (updates: Partial<SignOffReviewData>) => {
    onChange({
      ...engagement,
      signOffReview: {
        ...engagement.signOffReview,
        ...updates,
      },
    });
  };

  const updatePreparer = (updates: Partial<SignOffReviewData['preparer']>) => {
    updateSignOff({
      preparer: {
        ...engagement.signOffReview.preparer,
        ...updates,
      },
    });
  };

  const updateReviewer = (updates: Partial<SignOffReviewData['reviewer']>) => {
    updateSignOff({
      reviewer: {
        ...engagement.signOffReview.reviewer,
        ...updates,
      },
    });
  };

  const updateReviewNote = (id: string, updates: Partial<ReviewNoteItem>) => {
    const updatedNotes = engagement.signOffReview.reviewNotes.map((n) =>
      n.id === id ? { ...n, ...updates } : n
    );
    updateSignOff({ reviewNotes: updatedNotes });
  };

  const addReviewNote = () => {
    const newNote: ReviewNoteItem = {
      id: `rn-${Date.now()}`,
      stageRef: 'Stage 10: Materiality',
      query: 'Please review benchmark basis and verify if debt covenants trigger lower threshold.',
      response: '',
      status: 'Open',
    };
    updateSignOff({
      reviewNotes: [...engagement.signOffReview.reviewNotes, newNote],
    });
  };

  const removeReviewNote = (id: string) => {
    updateSignOff({
      reviewNotes: engagement.signOffReview.reviewNotes.filter((n) => n.id !== id),
    });
  };

  const openNotesCount = engagement.signOffReview.reviewNotes.filter((n) => n.status === 'Open').length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 13 • SQC 1 / SA 220
          </span>
          <span className="text-xs text-stone-500">Quality Control for an Audit of Financial Statements</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Sign-Off, Direction, Supervision & Quality Review
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Formalize the preparer declaration, track review points raised by the engagement partner or EQCR, and record the final planning approval.
        </p>
      </div>

      {/* Preparer & Reviewer Side-by-Side Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Preparer Card */}
        <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
              <FileSignature className="w-4 h-4 text-amber-700 dark:text-amber-400" />
              <span>Audit Preparer Sign-Off</span>
            </h3>
            <span className="text-[10px] uppercase font-bold text-stone-400">Audit Senior</span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                Preparer Name & Title
              </label>
              <input
                type="text"
                value={engagement.signOffReview.preparer.name}
                onChange={(e) => updatePreparer({ name: e.target.value })}
                className="w-full px-3 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-medium"
              />
            </div>

            <div>
              <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                Date of Submission
              </label>
              <input
                type="date"
                value={engagement.signOffReview.preparer.date}
                onChange={(e) => updatePreparer({ date: e.target.value })}
                className="w-full px-3 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-mono-num"
              />
            </div>

            <div className="p-3 rounded-lg bg-stone-50 dark:bg-[#1a2027] border border-stone-200 dark:border-stone-800">
              <label className="flex items-start gap-2.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={engagement.signOffReview.preparer.declared}
                  onChange={(e) => updatePreparer({ declared: e.target.checked })}
                  className="w-4 h-4 rounded text-amber-800 focus:ring-amber-700 mt-0.5"
                />
                <span className="text-xs text-stone-700 dark:text-stone-300 leading-snug">
                  <strong>Preparer Declaration (SQC 1):</strong> I confirm that all required preliminary audit planning procedures under ICAI Standards on Auditing (SA 315, SA 240, SA 330, SA 320) have been duly performed and documented without material omissions.
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* Reviewer / Partner Card */}
        <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-700 dark:text-emerald-400" />
              <span>Partner / Reviewer Conclusion</span>
            </h3>
            <span className="text-[10px] uppercase font-bold text-stone-400">SA 220 Review</span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                Engagement Partner / EQCR Name
              </label>
              <input
                type="text"
                value={engagement.signOffReview.reviewer.name}
                onChange={(e) => updateReviewer({ name: e.target.value })}
                className="w-full px-3 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-medium"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                  Review Status
                </label>
                <select
                  value={engagement.signOffReview.reviewer.conclusion}
                  onChange={(e) => updateReviewer({ conclusion: e.target.value as any })}
                  className={`w-full px-2.5 py-1.5 rounded border font-bold ${
                    engagement.signOffReview.reviewer.conclusion === 'Planning Approved'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300'
                      : engagement.signOffReview.reviewer.conclusion === 'Approved with Conditions'
                      ? 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300'
                      : 'bg-stone-100 text-stone-800 border-stone-300 dark:bg-stone-800 dark:text-stone-200'
                  }`}
                >
                  <option value="Pending Review">Pending Review</option>
                  <option value="Planning Approved">Planning Approved</option>
                  <option value="Approved with Conditions">Approved with Conditions</option>
                  <option value="Returned for Revision">Returned for Revision</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                  Date of Approval
                </label>
                <input
                  type="date"
                  value={engagement.signOffReview.reviewer.date}
                  onChange={(e) => updateReviewer({ date: e.target.value })}
                  className="w-full px-2.5 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-mono-num"
                />
              </div>
            </div>

            <div>
              <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                Partner Review Comments / Conditions
              </label>
              <textarea
                rows={2}
                value={engagement.signOffReview.reviewer.comments}
                onChange={(e) => updateReviewer({ comments: e.target.value })}
                placeholder="State any specific instructions or focus areas for substantive fieldwork..."
                className="w-full px-3 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs focus:border-amber-700"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Review Notes / Clearing Log */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
              Review Points & Clearing Log (Audit Workpaper Trails)
            </h3>
            {openNotesCount > 0 ? (
              <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 font-semibold flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{openNotesCount} open point(s)</span>
              </span>
            ) : (
              <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                <span>All review notes cleared</span>
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={addReviewNote}
            className="px-3 py-1.5 rounded-md bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 hover:bg-stone-800 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Review Point</span>
          </button>
        </div>

        <div className="space-y-3">
          {engagement.signOffReview.reviewNotes.length === 0 ? (
            <div className="text-center py-6 text-xs text-stone-500">
              No review points recorded yet. Click "Add Review Point" to log a query from the partner or EQCR.
            </div>
          ) : (
            engagement.signOffReview.reviewNotes.map((note, idx) => (
              <div
                key={note.id}
                className={`p-4 rounded-lg border transition-all text-xs space-y-2 ${
                  note.status === 'Open'
                    ? 'border-amber-300 dark:border-amber-800 bg-amber-50/20'
                    : 'border-stone-200 dark:border-stone-800 bg-stone-50/40 dark:bg-[#1a2027]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono-num font-bold text-stone-400">
                      #{idx + 1}
                    </span>
                    <input
                      type="text"
                      value={note.stageRef}
                      onChange={(e) => updateReviewNote(note.id, { stageRef: e.target.value })}
                      className="px-2 py-0.5 rounded bg-white dark:bg-[#15191f] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-semibold text-xs"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => updateReviewNote(note.id, { status: note.status === 'Open' ? 'Cleared' : 'Open' })}
                      className={`px-2.5 py-1 rounded text-xs font-bold border transition-colors ${
                        note.status === 'Cleared'
                          ? 'bg-emerald-700 text-white border-emerald-700'
                          : 'bg-amber-600 text-white border-amber-600'
                      }`}
                    >
                      {note.status === 'Cleared' ? 'Status: Cleared ✓' : 'Status: Open ⚠'}
                    </button>

                    <button
                      type="button"
                      onClick={() => removeReviewNote(note.id)}
                      className="p-1 text-stone-400 hover:text-rose-600 transition-colors"
                      title="Delete review note"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-0.5">
                      Reviewer Inquiry / Observation
                    </label>
                    <textarea
                      rows={2}
                      value={note.query}
                      onChange={(e) => updateReviewNote(note.id, { query: e.target.value })}
                      placeholder="Note the reviewer's query or required amendment..."
                      className="w-full px-2.5 py-1 rounded bg-white dark:bg-[#15191f] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs"
                    />
                  </div>

                  <div>
                    <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-0.5">
                      Preparer Clearing Action & Response
                    </label>
                    <textarea
                      rows={2}
                      value={note.response}
                      onChange={(e) => updateReviewNote(note.id, { response: e.target.value })}
                      placeholder="Document action taken or explanation provided..."
                      className="w-full px-2.5 py-1 rounded bg-white dark:bg-[#15191f] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs"
                    />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
