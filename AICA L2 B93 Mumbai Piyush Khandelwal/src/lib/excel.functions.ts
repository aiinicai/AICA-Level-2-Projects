import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

const cellValue = z.union([z.string(), z.number(), z.null()]);

const importSchema = z.object({
  sourceId: z.string().uuid().optional(),
  name: z.string().min(1).max(120),
  dataset: z.string().min(1).max(60),
  dateField: z.string().max(60).optional(),
  rows: z.array(z.record(cellValue)).min(1).max(20000),
});

/** Imports mapped spreadsheet rows as a normalised dataset for the signed-in user. */
export const importWorkbook = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((data) => importSchema.parse(data))
  .handler(async ({ data, context }) => {
    const { supabase, userId } = context;

    let sourceId = data.sourceId;
    if (sourceId) {
      const { error } = await supabase
        .from("accounting_sources")
        .update({ name: data.name })
        .eq("id", sourceId)
        .eq("user_id", userId);
      if (error) throw new Error(error.message);
    } else {
      const { data: row, error } = await supabase
        .from("accounting_sources")
        .insert({
          user_id: userId,
          provider: "excel",
          name: data.name,
          token_hash: `excel:${crypto.randomUUID()}`,
          status: "connected",
          frequency: "manual",
        })
        .select("id")
        .single();
      if (error) throw new Error(error.message);
      sourceId = row.id;
    }

    // Replacing a dataset: drop the previous rows for this source + dataset first.
    const { error: delErr } = await supabase
      .from("accounting_records")
      .delete()
      .eq("source_id", sourceId)
      .eq("dataset", data.dataset);
    if (delErr) throw new Error(delErr.message);

    const chunk = 500;
    for (let i = 0; i < data.rows.length; i += chunk) {
      const payload = data.rows.slice(i, i + chunk).map((r) => {
        const raw = data.dateField ? r[data.dateField] : null;
        const date = typeof raw === "string" && /^\d{4}-\d{2}-\d{2}/.test(raw) ? raw.slice(0, 10) : null;
        return { source_id: sourceId!, user_id: userId, dataset: data.dataset, record_date: date, data: r };
      });
      const { error } = await supabase.from("accounting_records").insert(payload);
      if (error) throw new Error(error.message);
    }

    const { count, error: countErr } = await supabase
      .from("accounting_records")
      .select("id", { count: "exact", head: true })
      .eq("source_id", sourceId);
    if (countErr) throw new Error(countErr.message);

    const { error: upErr } = await supabase
      .from("accounting_sources")
      .update({ status: "connected", error: null, last_sync: new Date().toISOString(), record_count: count ?? 0 })
      .eq("id", sourceId);
    if (upErr) throw new Error(upErr.message);

    return { sourceId, imported: data.rows.length, total: count ?? 0 };
  });
