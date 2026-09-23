import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

export interface LiveSource {
  id: string;
  provider: string;
  name: string;
  company: string | null;
  status: string;
  error: string | null;
  frequency: string;
  lastSync: string | null;
  records: number;
}

async function sha256(value: string) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export const listSources = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }): Promise<LiveSource[]> => {
    const { data, error } = await context.supabase
      .from("accounting_sources")
      .select("id, provider, name, company, status, error, frequency, last_sync, record_count")
      .order("created_at", { ascending: true });
    if (error) throw new Error(error.message);
    return (data ?? []).map((r) => ({
      id: r.id,
      provider: r.provider,
      name: r.name,
      company: r.company,
      status: r.status,
      error: r.error,
      frequency: r.frequency,
      lastSync: r.last_sync,
      records: r.record_count,
    }));
  });

export const createSource = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) =>
    z
      .object({
        provider: z.string().min(1).max(40).default("tally"),
        name: z.string().min(1).max(120),
        company: z.string().max(200).optional(),
      })
      .parse(data),
  )
  .handler(async ({ data, context }) => {
    const token = `dash_${crypto.randomUUID().replace(/-/g, "")}${crypto.randomUUID().slice(0, 8)}`;
    const { data: row, error } = await context.supabase
      .from("accounting_sources")
      .insert({
        user_id: context.userId,
        provider: data.provider,
        name: data.name,
        company: data.company ?? null,
        token_hash: await sha256(token),
        status: "pending",
      })
      .select("id")
      .single();
    if (error) throw new Error(error.message);
    // The token is returned exactly once — only its hash is stored.
    return { id: row.id, token };
  });

export const deleteSource = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => z.object({ id: z.string().uuid() }).parse(data))
  .handler(async ({ data, context }) => {
    const { error } = await context.supabase.from("accounting_sources").delete().eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const getLiveTables = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }): Promise<Record<string, Record<string, string | number | null>[]>> => {
    const tables: Record<string, Record<string, string | number | null>[]> = {};
    const page = 1000;
    for (let offset = 0; ; offset += page) {
      const { data, error } = await context.supabase
        .from("accounting_records")
        .select("dataset, data")
        .range(offset, offset + page - 1);
      if (error) throw new Error(error.message);
      for (const r of data ?? []) {
        (tables[r.dataset] ??= []).push(r.data as Record<string, string | number | null>);
      }
      if (!data || data.length < page) break;
    }
    return tables;
  });
