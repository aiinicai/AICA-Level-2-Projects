// ============================================================================
//  Data layer — Supabase (PostgreSQL + Auth + Row-Level Security)
//
//  Every function keeps the signature it had in the old IndexedDB version, so
//  the rest of the app is unchanged. Access is scoped to the signed-in user's
//  firm by RLS on the database; writes also stamp `firm_id` explicitly.
// ============================================================================

import type { Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import {
  Client, NoticeCase, NoticeIssue, ReconciliationItem, DocumentItem,
  FirmSettings, PortalFigureSet,
} from '../types';

// ── key-case conversion (app is camelCase, Postgres is snake_case) ──────────
const toSnake = (s: string) => s.replace(/[A-Z]/g, (m) => '_' + m.toLowerCase());
const toCamel = (s: string) => s.replace(/_([a-z])/g, (_, c) => c.toUpperCase());

/** Shallow: converts top-level keys only; jsonb values (figures, customFields) pass through. */
const rowToObj = <T,>(row: Record<string, unknown> | null): T | undefined =>
  row ? (Object.fromEntries(Object.entries(row).map(([k, v]) => [toCamel(k), v])) as T) : undefined;

const objToRow = (obj: Record<string, unknown>): Record<string, unknown> =>
  Object.fromEntries(Object.entries(obj).map(([k, v]) => [toSnake(k), v]));

const list = <T,>(rows: Record<string, unknown>[] | null): T[] =>
  (rows ?? []).map((r) => rowToObj<T>(r)!) as T[];

/** Upsert the given rows for a case, then delete any leftover rows not in the set. */
async function replaceForCase(
  table: 'notice_issues' | 'reconciliations' | 'document_items',
  caseId: string,
  rows: Record<string, unknown>[],
) {
  const { error } = await supabase.from(table).upsert(rows);
  if (error) throw new Error(`Save ${table}: ${error.message}`);
  const keep = new Set(rows.map((r) => r.id as string));
  const { data: existing } = await supabase.from(table).select('id').eq('case_id', caseId);
  const stale = (existing ?? []).map((r) => r.id as string).filter((id) => !keep.has(id));
  if (stale.length) await supabase.from(table).delete().in('id', stale);
}

// ── active firm ────────────────────────────────────────────────────────────
const ACTIVE_FIRM_KEY = 'gst_active_firm';
let activeFirmId: string | null =
  (typeof localStorage !== 'undefined' && localStorage.getItem(ACTIVE_FIRM_KEY)) || null;

export function getActiveFirmId(): string | null {
  return activeFirmId;
}
export function setActiveFirm(id: string | null): void {
  activeFirmId = id;
  try {
    if (id) localStorage.setItem(ACTIVE_FIRM_KEY, id);
    else localStorage.removeItem(ACTIVE_FIRM_KEY);
  } catch { /* ignore */ }
}
function requireFirm(): string {
  if (!activeFirmId) throw new Error('No firm selected. Sign in and choose or create a firm first.');
  return activeFirmId;
}
const fail = (label: string, error: { message: string } | null) => {
  if (error) throw new Error(`${label}: ${error.message}`);
};

// ── auth ───────────────────────────────────────────────────────────────────
export async function getSession(): Promise<Session | null> {
  const { data } = await supabase.auth.getSession();
  return data.session;
}
export function onAuthChange(cb: (session: Session | null) => void): () => void {
  const { data } = supabase.auth.onAuthStateChange((_e, session) => cb(session));
  return () => data.subscription.unsubscribe();
}
export async function signIn(email: string, password: string): Promise<void> {
  const { error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
  fail('Sign in', error);
}
export async function signUp(email: string, password: string): Promise<{ needsConfirmation: boolean }> {
  const { data, error } = await supabase.auth.signUp({ email: email.trim(), password });
  fail('Sign up', error);
  return { needsConfirmation: !data.session };
}
export async function signOut(): Promise<void> {
  await supabase.auth.signOut();
  setActiveFirm(null);
}

// ── firms & membership ─────────────────────────────────────────────────────
export interface FirmMembership {
  firmId: string;
  firmName: string;
  role: 'owner' | 'member';
  joinCode: string;
}
export interface FirmMember {
  userId: string;
  role: 'owner' | 'member';
  email: string | null;
  joinedAt: string;
}

export async function getMyMemberships(): Promise<FirmMembership[]> {
  const { data, error } = await supabase
    .from('firm_members')
    .select('role, firm:firms(id, name, join_code)');
  fail('Load firms', error);
  return (data ?? []).map((r: Record<string, any>) => ({
    firmId: r.firm.id,
    firmName: r.firm.name,
    role: r.role,
    joinCode: r.firm.join_code,
  }));
}

export async function createFirm(name: string): Promise<string> {
  const { data, error } = await supabase.rpc('create_firm', { p_name: name.trim() });
  fail('Create firm', error);
  const firmId = data as string;
  setActiveFirm(firmId);
  await ensureFirmSettings(firmId);
  return firmId;
}

export async function joinFirm(code: string): Promise<string> {
  const { data, error } = await supabase.rpc('join_firm', { p_code: code });
  fail('Join firm', error);
  const firmId = data as string;
  setActiveFirm(firmId);
  return firmId;
}

export async function rotateJoinCode(firmId: string): Promise<string> {
  const { data, error } = await supabase.rpc('rotate_join_code', { p_firm: firmId });
  fail('Rotate code', error);
  return data as string;
}

export async function getFirmMembers(firmId: string): Promise<FirmMember[]> {
  const { data, error } = await supabase
    .from('firm_members')
    .select('user_id, role, email, joined_at')
    .eq('firm_id', firmId)
    .order('joined_at');
  fail('Load members', error);
  return (data ?? []).map((r: Record<string, any>) => ({
    userId: r.user_id, role: r.role, email: r.email, joinedAt: r.joined_at,
  }));
}

export async function leaveFirm(firmId: string): Promise<void> {
  const { data: u } = await supabase.auth.getUser();
  const { error } = await supabase
    .from('firm_members').delete().eq('firm_id', firmId).eq('user_id', u.user?.id ?? '');
  fail('Leave firm', error);
  if (activeFirmId === firmId) setActiveFirm(null);
}

// ── firm settings ──────────────────────────────────────────────────────────
async function ensureFirmSettings(firmId: string): Promise<void> {
  await supabase.from('firm_settings').upsert({ firm_id: firmId }, { onConflict: 'firm_id' });
}

export async function getFirmSettings(): Promise<FirmSettings> {
  const firmId = requireFirm();
  await ensureFirmSettings(firmId);
  const { data, error } = await supabase
    .from('firm_settings').select('*').eq('firm_id', firmId).single();
  fail('Load firm settings', error);
  const r = data as Record<string, string>;
  return {
    caFirmName: r.ca_firm_name || '',
    caName: r.ca_name || '',
    membershipNo: r.membership_no || '',
    firmAddress: r.firm_address || '',
    contactEmail: r.contact_email || '',
    contactPhone: r.contact_phone || '',
    letterheadHeader: r.letterhead_header || '',
  };
}

export async function saveFirmSettings(s: FirmSettings): Promise<void> {
  const firmId = requireFirm();
  const { error } = await supabase.from('firm_settings').upsert({
    firm_id: firmId,
    ca_firm_name: s.caFirmName || '',
    ca_name: s.caName || '',
    membership_no: s.membershipNo || '',
    firm_address: s.firmAddress || '',
    contact_email: s.contactEmail || '',
    contact_phone: s.contactPhone || '',
    letterhead_header: s.letterheadHeader || '',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'firm_id' });
  fail('Save firm settings', error);
}

/** Called on app start once a firm is active — nothing to seed, just ensures the settings row. */
export async function initDatabase(): Promise<void> {
  if (activeFirmId) await ensureFirmSettings(activeFirmId);
}

// ── clients ────────────────────────────────────────────────────────────────
export async function getAllClients(): Promise<Client[]> {
  const { data, error } = await supabase.from('clients').select('*').order('legal_name');
  fail('Load clients', error);
  return list<Client>(data);
}
export async function saveClient(client: Client): Promise<void> {
  const { error } = await supabase.from('clients')
    .upsert({ ...objToRow(client as unknown as Record<string, unknown>), firm_id: requireFirm() });
  fail('Save client', error);
}
export async function deleteClient(clientId: string): Promise<void> {
  const { error } = await supabase.from('clients').delete().eq('id', clientId);
  fail('Delete client', error);
}

// ── notice cases ───────────────────────────────────────────────────────────
export async function getAllCases(): Promise<NoticeCase[]> {
  const { data, error } = await supabase.from('notice_cases').select('*').order('created_at', { ascending: false });
  fail('Load cases', error);
  return list<NoticeCase>(data);
}
export async function getCasesForClient(clientId: string): Promise<NoticeCase[]> {
  const { data, error } = await supabase.from('notice_cases').select('*').eq('client_id', clientId);
  fail('Load cases', error);
  return list<NoticeCase>(data);
}
export async function getCaseById(caseId: string): Promise<NoticeCase | undefined> {
  const { data, error } = await supabase.from('notice_cases').select('*').eq('id', caseId).maybeSingle();
  fail('Load case', error);
  return rowToObj<NoticeCase>(data);
}
export async function saveCase(noticeCase: NoticeCase): Promise<void> {
  const { error } = await supabase.from('notice_cases')
    .upsert({ ...objToRow(noticeCase as unknown as Record<string, unknown>), firm_id: requireFirm() });
  fail('Save case', error);
}
export async function deleteCase(caseId: string): Promise<void> {
  // FK cascade removes issues / reconciliations / documents / figures / discussions.
  const { error } = await supabase.from('notice_cases').delete().eq('id', caseId);
  fail('Delete case', error);
}

// ── issues (full set per case) ─────────────────────────────────────────────
export async function getIssuesForCase(caseId: string): Promise<NoticeIssue[]> {
  const { data, error } = await supabase.from('notice_issues').select('*').eq('case_id', caseId).order('issue_number');
  fail('Load issues', error);
  return list<NoticeIssue>(data);
}
export async function saveIssues(issues: NoticeIssue[]): Promise<void> {
  if (issues.length === 0) return;
  const firmId = requireFirm();
  await replaceForCase('notice_issues', issues[0].caseId,
    issues.map((i) => ({ ...objToRow(i as unknown as Record<string, unknown>), firm_id: firmId })));
}
export async function saveIssue(issue: NoticeIssue): Promise<void> {
  const { error } = await supabase.from('notice_issues')
    .upsert({ ...objToRow(issue as unknown as Record<string, unknown>), firm_id: requireFirm() });
  fail('Save issue', error);
}

// ── reconciliations (full set per case) ────────────────────────────────────
export async function getReconciliationsForCase(caseId: string): Promise<ReconciliationItem[]> {
  const { data, error } = await supabase.from('reconciliations').select('*').eq('case_id', caseId);
  fail('Load reconciliations', error);
  return list<ReconciliationItem>(data);
}
export async function saveReconciliations(recons: ReconciliationItem[]): Promise<void> {
  if (recons.length === 0) return;
  const firmId = requireFirm();
  await replaceForCase('reconciliations', recons[0].caseId,
    recons.map((r) => ({ ...objToRow(r as unknown as Record<string, unknown>), firm_id: firmId })));
}

// ── document tracker (full set per case) ──────────────────────────────────
export async function getDocumentsForCase(caseId: string): Promise<DocumentItem[]> {
  const { data, error } = await supabase.from('document_items').select('*').eq('case_id', caseId);
  fail('Load documents', error);
  return list<DocumentItem>(data);
}
export async function saveDocumentItem(item: DocumentItem): Promise<void> {
  const { error } = await supabase.from('document_items')
    .upsert({ ...objToRow(item as unknown as Record<string, unknown>), firm_id: requireFirm() });
  fail('Save document', error);
}
export async function saveDocumentItems(items: DocumentItem[]): Promise<void> {
  if (items.length === 0) return;
  const firmId = requireFirm();
  await replaceForCase('document_items', items[0].caseId,
    items.map((d) => ({ ...objToRow(d as unknown as Record<string, unknown>), firm_id: firmId })));
}
export async function deleteDocumentItem(docId: string): Promise<void> {
  const { error } = await supabase.from('document_items').delete().eq('id', docId);
  fail('Delete document', error);
}

// ── portal figure set (one per case) ──────────────────────────────────────
export async function getPortalFigures(caseId: string): Promise<PortalFigureSet | undefined> {
  const { data, error } = await supabase.from('portal_figure_sets').select('*').eq('case_id', caseId).maybeSingle();
  fail('Load portal figures', error);
  if (!data) return undefined;
  return { caseId: data.case_id, figures: data.figures ?? [], updatedAt: data.updated_at };
}
export async function savePortalFigures(set: PortalFigureSet): Promise<void> {
  const { error } = await supabase.from('portal_figure_sets').upsert({
    case_id: set.caseId,
    firm_id: requireFirm(),
    figures: set.figures,
    updated_at: new Date().toISOString(),
  }, { onConflict: 'case_id' });
  fail('Save portal figures', error);
}

// ── danger zone ───────────────────────────────────────────────────────────
export async function deleteAllFirmData(): Promise<void> {
  // Deleting clients cascades to every notice, issue, reconciliation, document and figure set.
  const { error } = await supabase.from('clients').delete().neq('id', '');
  fail('Clear data', error);
  await supabase.from('discussions').delete().neq('id', '');
  const firmId = getActiveFirmId();
  if (firmId) {
    await supabase.from('firm_settings').update({
      ca_firm_name: '', ca_name: '', membership_no: '',
      firm_address: '', contact_email: '', contact_phone: '', letterhead_header: '',
    }).eq('firm_id', firmId);
  }
}
