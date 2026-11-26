// Database side of the Clause 44 ledger method (browser, through RLS – no new tables).
import { supabase } from "@/integrations/supabase/client";
import { fetchAll } from "@/lib/db";
import { isValidGstin } from "@/lib/validators";
import { safeFileName } from "@/lib/export";
import type { Books } from "./books";
import {
  SETTINGS_NAME, readSettings, prepareImport, rowCategory, rowsToSync, rowState,
  type C44Books, type C44Settings, type PartyMasterLite, type RowLite,
} from "./ledgerMethod";

const db = supabase as any;

export async function loadSettings(clientId: string): Promise<{ id: string | null; settings: C44Settings }> {
  const { data } = await db.from("column_mappings").select("id, mapping").eq("client_id", clientId).eq("name", SETTINGS_NAME).maybeSingle();
  return { id: data?.id ?? null, settings: readSettings(data?.mapping) };
}

export async function saveSettings(firmId: string, clientId: string, s: C44Settings): Promise<void> {
  const { data } = await db.from("column_mappings").select("id").eq("client_id", clientId).eq("name", SETTINGS_NAME).maybeSingle();
  const { error } = data
    ? await db.from("column_mappings").update({ mapping: s }).eq("id", data.id)
    : await db.from("column_mappings").insert({ firm_id: firmId, client_id: clientId, name: SETTINGS_NAME, mapping: s });
  if (error) throw error;
}

export async function loadPartyMaster(clientId: string): Promise<Record<string, PartyMasterLite>> {
  const data = await fetchAll<PartyMasterLite>((from, to) => db.from("party_master").select("normalized_name, party_name, gstin, is_composition, is_exempt").eq("client_id", clientId).range(from, to));
  return Object.fromEntries(data.map((p) => [p.normalized_name, p]));
}

export async function loadRows(engagementId: string): Promise<RowLite[]> {
  return fetchAll<RowLite>((from, to) => db.from("expense_rows").select("id, party_name, normalized_name, gstin, expense_head, amount, include, category, category_override, upload_id, nature")
    .eq("engagement_id", engagementId).order("row_no", { ascending: true }).range(from, to));
}

/** Year's stored Tally summary – only while its upload still exists. */
export async function currentBooks(eng: { id: string; clause_answers: any }): Promise<C44Books | null> {
  const b: C44Books | undefined = eng.clause_answers?.c44_books;
  if (!b?.upload_id) return null;
  const { data } = await db.from("uploads").select("id").eq("id", b.upload_id).maybeSingle();
  return data ? b : null;
}

export async function freshAnswers(engagementId: string): Promise<any> {
  const { data } = await db.from("engagements").select("clause_answers").eq("id", engagementId).single();
  return data?.clause_answers ?? {};
}

export async function saveBooksMeta(eng: { id: string; clause_answers: any }, books: C44Books | null): Promise<void> {
  const { data } = await db.from("engagements").select("clause_answers").eq("id", eng.id).single();
  const { error } = await db.from("engagements").update({ clause_answers: { ...(data?.clause_answers ?? eng.clause_answers ?? {}), c44_books: books } }).eq("id", eng.id);
  if (error) throw error;
}

/** Saves rows whose include / column changed (grouped so one request covers many rows) and the new snapshot. */
export async function syncRows(eng: { id: string; clause_answers: any }, rows: RowLite[], books0: C44Books, pms: Record<string, PartyMasterLite>, s: C44Settings): Promise<number> {
  // the snapshot as saved now (another tab or an earlier sync may have changed it)
  const saved: C44Books | undefined = (await freshAnswers(eng.id))?.c44_books;
  const books: C44Books = saved?.upload_id === books0.upload_id ? { ...books0, synced: saved.synced, b2b: saved.b2b } : books0;
  const diff = rowsToSync(rows, books, pms, s);
  const groups = new Map<string, string[]>();
  diff.forEach((d) => { const k = `${d.include}|${d.category}`; groups.set(k, [...(groups.get(k) ?? []), d.id]); });
  for (const [k, ids] of groups) {
    const [inc, cat] = k.split("|");
    for (let i = 0; i < ids.length; i += 200) {
      const { error } = await db.from("expense_rows").update({ include: inc === "true", category_override: cat, category: cat }).in("id", ids.slice(i, i + 200));
      if (error) throw error;
    }
  }
  if (diff.length || !books.synced) {
    const changed = new Map(diff.map((d) => [d.id, rowState(d.category, d.include)]));
    const synced = { ...(books.synced ?? {}) };
    rows.forEach((r) => { if (r.upload_id === books.upload_id) { const c = changed.get(r.id); if (c) synced[r.id] = c; else if (synced[r.id] === undefined) synced[r.id] = rowState(r.category_override ?? r.category, r.include); } });
    await saveBooksMeta(eng, { ...books, synced });
  }
  return diff.length;
}

/** Brings this year's Tally ledger rows in step with the client's choices and party master (no-op for other years). */
export async function syncLedgerYear(eng: { id: string; client_id: string; clause_answers: any }): Promise<number> {
  const books = await currentBooks(eng);
  if (!books) return 0;
  const [rows, pms, st] = await Promise.all([loadRows(eng.id), loadPartyMaster(eng.client_id), loadSettings(eng.client_id)]);
  return syncRows(eng, rows, books, pms, st.settings);
}

/** Saves a Tally import. The new import is saved first; only then is this year's previous Tally import removed. */
export async function saveImport(o: {
  firmId: string; clientId: string; eng: { id: string; clause_answers: any }; file: File; software: string; books: Books; settings: C44Settings;
  progress: (t: string) => void;
}): Promise<{ rows: number; chosen: number; parties: number }> {
  const { firmId, clientId, eng, file, books, settings, progress } = o;
  // the year's summary as saved now (the page may hold an older copy)
  const { data: fresh } = await db.from("engagements").select("clause_answers").eq("id", eng.id).single();
  const old: C44Books | undefined = fresh?.clause_answers?.c44_books ?? undefined;

  progress("Saving the original file…");
  const path = `${firmId}/${eng.id}/${Date.now()}_${safeFileName(file.name.replace(/\.[^.]+$/, ""))}${(file.name.match(/\.[^.]+$/) ?? [""])[0]}`;
  const st = await supabase.storage.from("uploads").upload(path, file, { upsert: false });
  const { data: up, error: upErr } = await db.from("uploads").insert({ engagement_id: eng.id, firm_id: firmId, module: "clause44", file_name: file.name,
    storage_path: st.error ? null : path, file_size: file.size, software_detected: o.software, row_count: 0 }).select("id").single();
  if (upErr) { if (!st.error) await supabase.storage.from("uploads").remove([path]); throw upErr; }

  try {
    const prep = prepareImport(books, settings, { upload_id: up.id, file: file.name, b2b: old?.b2b ?? null });
    progress("Updating the party master…");
    const list = Object.entries(prep.books.parties).map(([k, p]) => ({ party_name: p.n.slice(0, 300), normalized_name: k.slice(0, 300), gstin: isValidGstin(p.gstin) ? p.gstin : null }));
    for (let i = 0; i < list.length; i += 1000) {
      const { error } = await supabase.rpc("upsert_parties", { p_client: clientId, p_parties: list.slice(i, i + 1000) as any });
      if (error) throw error;
    }
    const pms = await loadPartyMaster(clientId);
    const synced: Record<string, string> = {};
    for (let i = 0; i < prep.rows.length; i += 500) {
      progress(`Saving ledger-wise amounts… ${Math.min(i + 500, prep.rows.length)} / ${prep.rows.length}`);
      const chunk = prep.rows.slice(i, i + 500).map((d) => {
        const cat = rowCategory({ ...d, id: "", category: "", category_override: null, upload_id: up.id }, prep.books, pms[d.normalized_name], settings);
        const g = (pms[d.normalized_name]?.gstin || d.gstin || "").toUpperCase();
        return { ...d, engagement_id: eng.id, firm_id: firmId, upload_id: up.id, category_override: cat, category: cat,
          gstin_status: !g ? "blank" : isValidGstin(g) ? "valid" : "invalid" };
      });
      const { data: ins, error } = await db.from("expense_rows").insert(chunk).select("id, category_override, include");
      if (error) throw error;
      (ins ?? []).forEach((r: any) => { synced[r.id] = rowState(r.category_override, r.include); });
    }
    await db.from("uploads").update({ row_count: prep.rows.length }).eq("id", up.id);
    progress("Saving the year's summary…");
    await saveBooksMeta(eng, { ...prep.books, synced });
    await saveSettings(firmId, clientId, settings);

    if (old?.upload_id && old.upload_id !== up.id) {
      progress("Removing the previous Tally import of this year…");
      const { data: ou } = await db.from("uploads").select("id, storage_path").eq("id", old.upload_id).maybeSingle();
      await db.from("expense_rows").delete().eq("upload_id", old.upload_id);
      if (ou) { if (ou.storage_path) await supabase.storage.from("uploads").remove([ou.storage_path]); await db.from("uploads").delete().eq("id", ou.id); }
    }
    await supabase.rpc("reclassify_engagement", { p_eng: eng.id });
    return { rows: prep.rows.length, chosen: prep.counts.chosen, parties: prep.counts.parties };
  } catch (e) {
    // nothing half-saved stays behind; the earlier import is untouched
    await db.from("expense_rows").delete().eq("upload_id", up.id);
    await db.from("uploads").delete().eq("id", up.id);
    if (!st.error) await supabase.storage.from("uploads").remove([path]);
    throw e;
  }
}
