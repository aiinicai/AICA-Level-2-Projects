import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { fetchAll, errMsg } from "@/lib/db";
import { normalizeParty } from "@/lib/party";

// Module tables are addressed by name at runtime, so use an untyped view of the client here.
const db = supabase as any;

/** Rows of one module table for an assessment year, with optimistic edit helpers. */
export function useRows<T extends { id: string }>(table: string, engagementId: string, order = "row_no") {
  const [rows, setRows] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    try {
      const data = await fetchAll<T>((from, to) => db.from(table).select("*").eq("engagement_id", engagementId).order(order, { ascending: true, nullsFirst: false }).order("created_at").range(from, to));
      setRows(data); setError("");
    } catch (e) { setError(errMsg(e)); }
    setLoading(false);
  }, [table, engagementId, order]);
  useEffect(() => { reload(); }, [reload]);

  const patch = async (id: string, p: Partial<T>) => {
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...p } : r)));
    const { error } = await db.from(table).update(p as any).eq("id", id);
    if (error) { await reload(); throw error; }
  };
  /** Same change on many rows (sent in batches of 200 ids). */
  const patchMany = async (ids: string[], p: Partial<T>) => {
    const set = new Set(ids);
    setRows((rs) => rs.map((r) => (set.has(r.id) ? { ...r, ...p } : r)));
    for (let i = 0; i < ids.length; i += 200) {
      const { error } = await db.from(table).update(p as any).in("id", ids.slice(i, i + 200));
      if (error) { await reload(); throw error; }
    }
  };
  const remove = async (ids: string[]) => {
    const { error } = await db.from(table).delete().in("id", ids);
    if (error) throw error;
    setRows((rs) => rs.filter((r) => !ids.includes(r.id)));
  };
  const add = async (row: Record<string, unknown>) => {
    const { data, error } = await db.from(table).insert(row).select("*").single();
    if (error) throw error;
    setRows((rs) => [...rs, data as T]);
    return data as T;
  };
  return { rows, loading, error, reload, patch, patchMany, remove, add };
}

export interface PartyRow {
  id: string; party_name: string; normalized_name: string; gstin: string | null; pan: string | null; address: string | null;
  is_composition: boolean; is_exempt: boolean; msme_category: "micro" | "small" | "medium" | "none" | null; udyam_no: string | null;
  msme_trader: boolean; agreed_credit_days: number | null; is_exempt_lender: boolean; is_transporter: boolean;
  msme_activity?: string | null; is_related?: boolean; relationship?: string | null;
}

/** Client party master as a map by normalized name. */
export function useParties(clientId: string) {
  const [map, setMap] = useState<Record<string, PartyRow>>({});
  const reload = useCallback(async () => {
    const data = await fetchAll<PartyRow>((from, to) => db.from("party_master").select("*").eq("client_id", clientId).order("party_name").range(from, to));
    const m: Record<string, PartyRow> = {};
    data.forEach((p) => { m[p.normalized_name] = p; });
    setMap(m);
  }, [clientId]);
  useEffect(() => { reload(); }, [reload]);

  /** Make sure parties exist (creates missing ones) – then optionally patch attributes. */
  const ensure = async (list: { party_name: string; normalized_name?: string; pan?: string | null; address?: string | null }[]) => {
    const items = list.map((p) => ({ party_name: p.party_name, normalized_name: p.normalized_name || normalizeParty(p.party_name) || p.party_name.toLowerCase(), gstin: null }));
    const uniq = Array.from(new Map(items.map((i) => [i.normalized_name, i])).values());
    for (let i = 0; i < uniq.length; i += 1000) {
      const { error } = await supabase.rpc("upsert_parties", { p_client: clientId, p_parties: uniq.slice(i, i + 1000) });
      if (error) throw error;
    }
    // fill PAN / address where the master has none
    const fresh = await fetchAll<PartyRow>((from, to) => db.from("party_master").select("*").eq("client_id", clientId).range(from, to));
    const byName: Record<string, PartyRow> = {};
    fresh.forEach((p) => { byName[p.normalized_name] = p; });
    for (const p of list) {
      const key = p.normalized_name || normalizeParty(p.party_name) || p.party_name.toLowerCase();
      const cur = byName[key];
      if (!cur) continue;
      const upd: Record<string, string> = {};
      if (p.pan && !cur.pan) upd.pan = p.pan.toUpperCase();
      if (p.address && !cur.address) upd.address = p.address;
      if (Object.keys(upd).length) await db.from("party_master").update(upd).eq("id", cur.id);
    }
    await reload();
  };
  const update = async (normalized: string, patch: Partial<PartyRow>) => {
    const p = map[normalized];
    if (!p) return;
    setMap((m) => ({ ...m, [normalized]: { ...p, ...patch } }));
    const { error } = await supabase.from("party_master").update(patch as any).eq("id", p.id);
    if (error) { await reload(); throw error; }
  };
  return { parties: map, reload, ensure, update };
}
