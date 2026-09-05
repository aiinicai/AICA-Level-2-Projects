// When a notice is saved, fan its extracted issues out into the other tabs:
//   • Document Tracker  — the documents each issue needs from the client
//   • Client Discussion — the questions to raise with the client, per issue
// The Reply builder and email drafts already derive from the issues live.

import { AnalysisResponse } from './aiService';
import { DocumentItem } from '../types';
import { DiscussionEntry } from './discussions';

const today = () => new Date().toISOString().split('T')[0];

/** Split a free-text list ("1. GSTR-2B\n2. Invoices" / "a; b; c" / "a, b, c") into clean items. */
export function splitList(text: string): string[] {
  if (!text) return [];
  const rough = text.split(/\r?\n|[;•]/).map((s) => s.trim()).filter(Boolean);
  const items: string[] = [];
  for (const chunk of rough) {
    // Further split a chunk on commas only when it reads as a short comma list.
    const parts = chunk.split(/,\s+/);
    if (parts.length >= 2 && parts.every((p) => p.trim().length <= 60)) {
      items.push(...parts);
    } else {
      items.push(chunk);
    }
  }
  return items
    .map((s) => s.replace(/^\s*(?:\d+[.)]|[-*]|[a-z][.)])\s*/i, '').replace(/\.$/, '').trim())
    .filter((s) => s.length > 2 && s.length < 200);
}

const uniq = (items: string[]) => {
  const seen = new Set<string>();
  return items.filter((i) => {
    const k = i.toLowerCase().replace(/\s+/g, ' ');
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
};

export function buildDocumentsFromAnalysis(caseId: string, analysis: AnalysisResponse): DocumentItem[] {
  const { noticeCase, issues } = analysis;
  const dueDate = noticeCase.replyDeadline || '—';
  const period = noticeCase.period || (noticeCase.financialYear ? `FY ${noticeCase.financialYear}` : '');

  const rows: { name: string; category: string; note: string }[] = [];

  issues.forEach((iss) => {
    const cat = iss.factsCategory?.trim() || 'Client Data';
    // Prefer the explicit documents list; fall back to the "data required" text.
    const fromDocs = splitList(iss.documentsRequired);
    const docs = uniq(fromDocs.length ? fromDocs : splitList(iss.dataRequired));
    docs.forEach((name) =>
      rows.push({
        name,
        category: cat,
        note: `For issue ${iss.issueNumber}: ${iss.title}`,
      })
    );
  });

  let deduped = uniq(rows.map((r) => r.name)).map((name) => rows.find((r) => r.name === name)!);

  if (deduped.length === 0) {
    deduped = [
      { name: 'GSTR-1, GSTR-3B and GSTR-2B for the notice period', category: 'Portal Report', note: 'Download from the GST portal' },
      { name: 'Purchase register, sales register and relevant ledgers', category: 'Books & Ledgers', note: '' },
      { name: 'Copies of tax invoices and bank payment proofs', category: 'Invoices', note: '' },
    ];
  }

  return deduped.slice(0, 20).map((r, i) => ({
    id: `doc_${caseId}_${i + 1}`,
    caseId,
    docName: r.name,
    category: r.category,
    status: 'Pending' as const,
    requestedDate: today(),
    dueDate,
    remarks: r.note,
    period,
  }));
}

export function buildIntakeDiscussions(caseId: string, analysis: AnalysisResponse): DiscussionEntry[] {
  const { noticeCase, issues } = analysis;
  const stamp = new Date().toISOString();

  const entries: DiscussionEntry[] = issues.slice(0, 10).map((iss, i) => {
    const questions = splitList(iss.clientQuestions);
    const questionsText = questions.length
      ? questions.map((q, n) => `${n + 1}. ${q}`).join('\n')
      : `Discuss issue ${iss.issueNumber} (${iss.title}) and gather supporting facts.`;

    return {
      id: `disc_${caseId}_${i + 1}`,
      caseId,
      date: today(),
      mode: 'Meeting' as const,
      topic: `${iss.title} — points to raise with client`,
      notes:
        `Department's allegation: ${iss.allegation}\n\n` +
        (iss.probableReason ? `Likely cause: ${iss.probableReason}` : ''),
      questionsAsked: questionsText,
      clientResponse: '',
      actionItems: splitList(iss.documentsRequired).map((d, n) => `${n + 1}. Obtain: ${d}`).join('\n'),
      followUpDate: '',
      status: 'Open' as const,
      createdAt: stamp,
    };
  });

  // Lead entry summarising the notice itself.
  entries.unshift({
    id: `disc_${caseId}_0`,
    caseId,
    date: today(),
    mode: 'Meeting',
    topic: `Notice ${noticeCase.formType} ${noticeCase.noticeNumber} received — initial client briefing`,
    notes:
      `Total demand ₹${noticeCase.totalDemand.toLocaleString('en-IN')} ` +
      `(tax ₹${noticeCase.principalTax.toLocaleString('en-IN')}, interest ₹${noticeCase.interest.toLocaleString('en-IN')}, ` +
      `penalty ₹${noticeCase.penalty.toLocaleString('en-IN')}). ` +
      `Reply due ${noticeCase.replyDeadline}.` +
      (noticeCase.hearingDate ? ` Personal hearing: ${noticeCase.hearingDate}.` : ''),
    questionsAsked:
      '1. Confirm the notice was received and note the date of service.\n' +
      '2. Brief the client on the demand and the reply deadline.\n' +
      '3. Decide who will collate the documents listed in the tracker.',
    clientResponse: '',
    actionItems: 'Share the document request list with the client and set an internal target date.',
    followUpDate: '',
    status: 'Pending Follow-up',
    createdAt: stamp,
  });

  return entries;
}
