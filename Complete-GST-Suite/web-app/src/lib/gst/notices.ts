import type { Notice } from "./demo";
import { daysBetween, isoDay } from "./format";

export type NoticeStatus = "Replied" | "Closed" | "Overdue" | "Due soon" | "Open";

export interface LibraryEntry {
  form: string;
  nature: string;
  priority: Notice["priority"];
  action: string;
  /** reconciliation that explains this notice */
  link?: "R1" | "R5" | undefined;
}

/** Form library: nature, priority and the action needed. */
export const NOTICE_LIBRARY: LibraryEntry[] = [
  { form: "ASMT-10", nature: "Scrutiny of returns — discrepancies noticed", priority: "High", action: "Reply in ASMT-11 with explanation or payment" },
  { form: "DRC-01A", nature: "Intimation of tax ascertained before show cause notice", priority: "High", action: "Reply in DRC-01A Part B (accept or object)" },
  { form: "DRC-01B", nature: "GSTR-1 liability exceeds tax paid in GSTR-3B", priority: "High", action: "Pay the difference via DRC-03 or explain in Part B — see R1", link: "R1" },
  { form: "DRC-01C", nature: "ITC claimed in GSTR-3B exceeds GSTR-2B", priority: "High", action: "Reverse the excess via DRC-03 or explain in Part B — see R5", link: "R5" },
  { form: "DRC-01", nature: "Show cause notice (SCN)", priority: "Critical", action: "File reply in DRC-06 with documents; ask for personal hearing" },
  { form: "DRC-07", nature: "Summary of demand order", priority: "Critical", action: "Pay the demand or file appeal in APL-01 within 3 months" },
  { form: "REG-17", nature: "Show cause for cancellation of registration", priority: "Critical", action: "Reply in REG-18 within 7 working days" },
  { form: "REG-03", nature: "Clarification sought on registration application / amendment", priority: "Medium", action: "Reply in REG-04 with documents" },
  { form: "GSTR-3A", nature: "Notice to return defaulter", priority: "High", action: "File the pending return(s) within 15 days" },
  { form: "ADT-01", nature: "Intimation of departmental audit", priority: "High", action: "Prepare records; attend the audit on the date given" },
  { form: "ASMT-14", nature: "Show cause before best-judgement assessment", priority: "Critical", action: "Reply with explanation and file pending returns" },
];

export const libraryFor = (form: string) => NOTICE_LIBRARY.find((l) => l.form === form.trim().toUpperCase());

/** Fill nature / priority / action from the library and default the due date to 30 days from issue. */
export function noticeFromLibrary(n: Partial<Notice>, today = new Date()): Notice {
  const form = (n.form ?? "").trim().toUpperCase();
  const lib = libraryFor(form);
  const issued = n.issued || isoDay(today);
  let due = n.due;
  if (!due) {
    const d = new Date(issued + "T00:00:00");
    d.setDate(d.getDate() + 30);
    due = isoDay(d);
  }
  const status = n.status ?? (n.replied ? "Replied" : "Open");
  return {
    id: n.id ?? `n-${Math.random().toString(36).slice(2, 10)}`,
    clientId: n.clientId ?? "",
    gstin: (n.gstin ?? "").toUpperCase(),
    form,
    subject: n.subject || lib?.nature || "",
    ref: (n.ref ?? "").trim(),
    taxPeriod: n.taxPeriod ?? "",
    issued,
    due,
    amount: n.amount ?? 0,
    priority: n.priority ?? lib?.priority ?? "Medium",
    action: n.action || lib?.action || "",
    portalStatus: n.portalStatus ?? "Issued",
    source: n.source ?? "Manual",
    assignedTo: n.assignedTo ?? "",
    status,
    notes: n.notes ?? "",
    attachment: n.attachment,
    reply: n.reply,
    repliedOn: n.repliedOn,
    replied: status === "Replied" || status === "Closed",
  };
}

export function noticeStatus(n: Notice, today = new Date(), soonDays = 7): NoticeStatus {
  const st = n.status ?? (n.replied ? "Replied" : "Open");
  if (st === "Replied") return "Replied";
  if (st === "Closed") return "Closed";
  const d = daysBetween(today.toISOString(), n.due);
  if (d < 0) return "Overdue";
  if (d <= soonDays) return "Due soon";
  return "Open";
}

export const daysLeft = (n: Notice, today = new Date()) => daysBetween(today.toISOString(), n.due);

/** Deduplicate on form + reference + GSTIN. */
export const noticeKey = (n: Pick<Notice, "form" | "ref" | "gstin">) => `${n.form.trim().toUpperCase()}|${n.ref.trim().toUpperCase()}|${n.gstin.trim().toUpperCase()}`;

export function dedupeNotices(existing: Notice[], incoming: Notice[]): Notice[] {
  const seen = new Set(existing.map(noticeKey));
  const out: Notice[] = [];
  for (const n of incoming) {
    const k = noticeKey(n);
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(n);
  }
  return out;
}
