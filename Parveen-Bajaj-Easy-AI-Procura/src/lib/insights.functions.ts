import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

const FOCUS = {
  overview: "Give an executive overview of procurement health: spend, pipeline, bottlenecks.",
  suppliers: "Analyse supplier concentration and dependency risk, and suggest diversification.",
  variance: "Analyse invoice price variances versus LPO prices and flag overcharging risk.",
  compliance:
    "Assess maker-checker compliance and approval cycle times against ISO 20400 / CIPS good practice.",
  forecast: "Forecast next month's spend from the trend and recommend budget actions.",
} as const;

export type InsightFocus = keyof typeof FOCUS;

export const analyseProcurement = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator(z.object({ focus: z.enum(Object.keys(FOCUS) as [InsightFocus, ...InsightFocus[]]), question: z.string().max(500).optional() }))
  .handler(async ({ data, context }) => {
    const sb = context.supabase;
    const [suppliers, lpos, grns, invoices, lines] = await Promise.all([
      sb.from("suppliers").select("id,supplier_name,status"),
      sb.from("lpo_header").select("lpo_number,lpo_date,status,total_value,supplier_id,created_at,approved_at"),
      sb.from("grn_header").select("grn_number,grn_date,status,receipt_status,created_at,approved_at"),
      sb.from("invoices").select("invoice_number,invoice_date,status,total_value,supplier_id,created_at,approved_at"),
      sb.from("invoice_lines").select("lpo_price,invoice_price,price_variance"),
    ]);
    const names = new Map((suppliers.data ?? []).map((s) => [s.id, s.supplier_name]));
    const withName = <T extends { supplier_id: string }>(rows: T[] | null) =>
      (rows ?? []).slice(0, 150).map(({ supplier_id, ...r }) => ({ ...r, supplier: names.get(supplier_id) }));
    const snapshot = {
      suppliers: (suppliers.data ?? []).map((s) => ({ name: s.supplier_name, status: s.status })),
      lpos: withName(lpos.data),
      grns: (grns.data ?? []).slice(0, 150),
      invoices: withName(invoices.data),
      invoice_lines: (lines.data ?? []).slice(0, 200),
    };
    const { runAnalysis } = await import("@/lib/ai.server");
    const analysis = await runAnalysis(
      "You are a senior procurement analyst. Use only the data provided. Currency is KES. " +
        "Reply in concise Markdown: a 1-line headline, 3-5 key findings with numbers, risks, and 3 concrete recommendations. " +
        "If data is sparse, say so and give guidance on what to capture.",
      `${FOCUS[data.focus]}\n${data.question ? `User question: ${data.question}\n` : ""}Data (JSON):\n${JSON.stringify(snapshot)}`,
    );
    return { analysis };
  });
