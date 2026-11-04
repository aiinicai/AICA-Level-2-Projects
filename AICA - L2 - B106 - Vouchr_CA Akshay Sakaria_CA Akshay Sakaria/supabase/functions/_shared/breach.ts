// Personal-data breach notices — DPDP Act 2023 s.8(6) and DPDP Rules 2025, Rule 7 (text checked 3 Nov 2026 at
// dpdpa.com/dpdparules/rule7.html; reported to apply from 13 May 2027 — confirm against Gazette G.S.R. 846(E)).
// The templates only arrange facts the firm types in; nothing is filled in by guess. Every [ ] left empty is shown as
// "[to be filled]" so an incomplete notice is obvious. Counsel should review before first use.

export interface BreachFacts {
  firm: string; contactName?: string; contactEmail?: string; contactPhone?: string;
  what?: string;        // nature: what happened (e.g. a phone with the app signed in was stolen)
  data?: string;        // extent: which personal data, how many people
  when?: string;        // when it happened / was discovered
  where?: string;       // location / system
  impact?: string;      // likely consequences
  done?: string;        // measures taken or being taken
  youCan?: string;      // what the person can do
  cause?: string;       // (Board, 72 h) events, circumstances, reasons
  who?: string;         // (Board, 72 h) findings about the person who caused it
  prevent?: string;     // (Board, 72 h) remedial measures to prevent recurrence
  notified?: string;    // (Board, 72 h) report on intimations to Data Principals
}

const v = (s?: string, blank = '[to be filled]') => (s && s.trim() ? s.trim() : blank);
const contact = (f: BreachFacts, blank = '[to be filled]') => [f.contactName, f.contactEmail, f.contactPhone].filter(Boolean).join(' · ') || blank;
const B = '[भरना बाकी]';

/** Rule 7(1): to each affected person — concise, clear, plain; through their account or registered contact. */
export function noticeToPerson(f: BreachFacts, lang: 'en' | 'hi' = 'en'): string {
  if (lang === 'hi') return [
    `विषय: आपके व्यक्तिगत डेटा से जुड़ी सुरक्षा घटना — ${f.firm}`,
    '',
    `क्या हुआ: ${v(f.what, B)}`,
    `कौन-सा डेटा और कितना: ${v(f.data, B)}`,
    `कब: ${v(f.when, B)}`,
    `आप पर संभावित असर: ${v(f.impact, B)}`,
    `हमने क्या किया / कर रहे हैं: ${v(f.done, B)}`,
    `आप अपनी सुरक्षा के लिए क्या कर सकते हैं: ${v(f.youCan, B)}`,
    `प्रश्नों के लिए संपर्क: ${contact(f, B)}`
  ].join('\n');
  return [
    `Subject: Security incident involving your personal data — ${f.firm}`,
    '',
    `What happened: ${v(f.what)}`,
    `Which data and how much: ${v(f.data)}`,
    `When: ${v(f.when)}`,
    `Likely consequences for you: ${v(f.impact)}`,
    `What we have done / are doing: ${v(f.done)}`,
    `What you can do to protect yourself: ${v(f.youCan)}`,
    `Contact for your questions: ${contact(f)}`
  ].join('\n');
}

/** Rule 7(2)(a): to the Data Protection Board, without delay. */
export function firstNoticeToBoard(f: BreachFacts): string {
  return [
    `Intimation of personal data breach — ${f.firm}`,
    `Nature: ${v(f.what)}`, `Extent: ${v(f.data)}`, `Timing: ${v(f.when)}`, `Location: ${v(f.where)}`, `Likely impact: ${v(f.impact)}`,
    `Contact: ${contact(f)}`
  ].join('\n');
}

/** Rule 7(2)(b): detailed report to the Board within 72 hours of becoming aware (or longer if the Board allows in writing). */
export function reportToBoard72h(f: BreachFacts): string {
  return [
    `Detailed report on personal data breach — ${f.firm}`,
    `(i) Updated and detailed description: ${v(f.what)} — data: ${v(f.data)} — when: ${v(f.when)} — where: ${v(f.where)} — impact: ${v(f.impact)}`,
    `(ii) Events, circumstances and reasons: ${v(f.cause)}`,
    `(iii) Measures to mitigate risk (taken / proposed): ${v(f.done)}`,
    `(iv) Findings about the person who caused the breach: ${v(f.who)}`,
    `(v) Remedial measures to prevent recurrence: ${v(f.prevent)}`,
    `(vi) Report on intimations to affected Data Principals: ${v(f.notified)}`,
    `Contact: ${contact(f)}`
  ].join('\n');
}

/** 72 hours from when the firm became aware (ISO date-time) — the latest time for the detailed Board report. */
export const boardReportDue = (awareAt: string) => new Date(new Date(awareAt).getTime() + 72 * 3600_000).toISOString();
