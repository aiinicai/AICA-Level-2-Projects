// Client-discussion log — stored per notice case in Supabase.

import { supabase } from '../lib/supabase';
import { getActiveFirmId } from './db';

export interface DiscussionEntry {
  id: string;
  caseId: string;
  date: string;
  mode: 'Call' | 'Meeting' | 'Email' | 'WhatsApp' | 'In-Person';
  topic: string;
  notes: string;
  questionsAsked: string;
  clientResponse: string;
  actionItems: string;
  followUpDate: string;
  status: 'Open' | 'Resolved' | 'Pending Follow-up';
  createdAt: string;
}

const rowToEntry = (r: Record<string, any>): DiscussionEntry => ({
  id: r.id,
  caseId: r.case_id,
  date: r.date,
  mode: r.mode,
  topic: r.topic,
  notes: r.notes,
  questionsAsked: r.questions_asked,
  clientResponse: r.client_response,
  actionItems: r.action_items,
  followUpDate: r.follow_up_date,
  status: r.status,
  createdAt: r.created_at,
});

const entryToRow = (e: DiscussionEntry) => ({
  id: e.id,
  firm_id: getActiveFirmId(),
  case_id: e.caseId,
  date: e.date,
  mode: e.mode,
  topic: e.topic,
  notes: e.notes,
  questions_asked: e.questionsAsked,
  client_response: e.clientResponse,
  action_items: e.actionItems,
  follow_up_date: e.followUpDate,
  status: e.status,
  created_at: e.createdAt,
});

export async function loadDiscussionsForCase(caseId: string): Promise<DiscussionEntry[]> {
  if (!caseId) return [];
  const { data, error } = await supabase
    .from('discussions').select('*').eq('case_id', caseId).order('created_at', { ascending: false });
  if (error) throw new Error(`Load discussions: ${error.message}`);
  return (data ?? []).map(rowToEntry);
}

export async function saveDiscussion(entry: DiscussionEntry): Promise<void> {
  const { error } = await supabase.from('discussions').upsert(entryToRow(entry));
  if (error) throw new Error(`Save discussion: ${error.message}`);
}

export async function deleteDiscussion(id: string): Promise<void> {
  const { error } = await supabase.from('discussions').delete().eq('id', id);
  if (error) throw new Error(`Delete discussion: ${error.message}`);
}

export async function addDiscussions(entries: DiscussionEntry[]): Promise<void> {
  if (entries.length === 0) return;
  const { error } = await supabase.from('discussions').insert(entries.map(entryToRow));
  if (error) throw new Error(`Add discussions: ${error.message}`);
}
