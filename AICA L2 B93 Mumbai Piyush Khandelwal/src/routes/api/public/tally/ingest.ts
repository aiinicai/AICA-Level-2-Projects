import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { normaliseTally, type TallyPayload } from "@/lib/tally/normalize";

const payloadSchema = z.object({
  company: z.string().max(200).optional(),
  vouchers: z
    .array(
      z.object({
        date: z.string(),
        type: z.string(),
        number: z.string().optional(),
        party: z.string().optional(),
        amount: z.number(),
        taxable: z.number().optional(),
        cgst: z.number().optional(),
        sgst: z.number().optional(),
        igst: z.number().optional(),
        narration: z.string().optional(),
      }),
    )
    .max(50000)
    .optional(),
  ledgers: z
    .array(z.object({ name: z.string(), group: z.string().optional(), closing: z.number().optional() }))
    .max(20000)
    .optional(),
  stock: z
    .array(
      z.object({
        name: z.string(),
        quantity: z.number().optional(),
        value: z.number().optional(),
        category: z.string().optional(),
      }),
    )
    .max(20000)
    .optional(),
});

async function sha256(value: string) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

export const Route = createFileRoute("/api/public/tally/ingest")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const token = request.headers.get("x-dash-token");
        if (!token) return json({ error: "Missing sync token" }, 401);

        const parsed = payloadSchema.safeParse(await request.json().catch(() => null));
        if (!parsed.success) return json({ error: "Invalid payload", details: parsed.error.issues.slice(0, 5) }, 400);

        const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
        const tokenHash = await sha256(token);
        const { data: source, error } = await supabaseAdmin
          .from("accounting_sources")
          .select("id, user_id")
          .eq("token_hash", tokenHash)
          .maybeSingle();

        if (error) return json({ error: error.message }, 500);
        if (!source) return json({ error: "Unknown sync token" }, 401);

        const records = normaliseTally(parsed.data as TallyPayload);

        await supabaseAdmin.from("accounting_records").delete().eq("source_id", source.id);

        for (let i = 0; i < records.length; i += 500) {
          const chunk = records.slice(i, i + 500).map((r) => ({
            source_id: source.id,
            user_id: source.user_id,
            dataset: r.dataset,
            record_date: r.record_date,
            data: r.data,
          }));
          const { error: insertError } = await supabaseAdmin.from("accounting_records").insert(chunk);
          if (insertError) return json({ error: insertError.message }, 500);
        }

        await supabaseAdmin
          .from("accounting_sources")
          .update({
            status: "connected",
            error: null,
            last_sync: new Date().toISOString(),
            record_count: records.length,
            ...(parsed.data.company ? { company: parsed.data.company } : {}),
          })
          .eq("id", source.id);

        return json({ ok: true, records: records.length });
      },
    },
  },
});
