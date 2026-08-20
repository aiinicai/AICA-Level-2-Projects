import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

export const ADMIN_EMAIL = "caprashantdokania@gmail.com";

/** Links this signed-in email to an account row and grants admin to the owner. */
export const ensureAccount = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const claims = context.claims as { email?: string };
    const email = (claims.email ?? "").toLowerCase();

    if (email === ADMIN_EMAIL) {
      await supabaseAdmin
        .from("user_roles")
        .upsert({ user_id: context.userId, role: "admin" }, { onConflict: "user_id,role" });
    }

    return { isAdmin: email === ADMIN_EMAIL };
  });

const reviewInput = z.object({
  paymentId: z.string().uuid(),
  action: z.enum(["approve", "reject"]),
  note: z.string().max(500).optional(),
});

/** Admin-only: approve a UPI top-up, which adds purchased credit. */
export const reviewPayment = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: unknown) => reviewInput.parse(input))
  .handler(async ({ data, context }) => {
    const { data: isAdmin } = await context.supabase.rpc("has_role", {
      _user_id: context.userId,
      _role: "admin",
    });
    if (!isAdmin) throw new Error("Forbidden");

    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: payment, error } = await supabaseAdmin
      .from("payments")
      .select("*")
      .eq("id", data.paymentId)
      .maybeSingle();
    if (error || !payment) throw new Error("Payment not found");

    await supabaseAdmin
      .from("payments")
      .update({
        status: data.action === "approve" ? "approved" : "rejected",
        admin_note: data.note ?? null,
        reviewed_by: context.userId,
        reviewed_at: new Date().toISOString(),
      })
      .eq("id", data.paymentId);

    const accountId = (payment as { account_id?: string | null }).account_id ?? null;
    const creditUsd = Number((payment as { credit_usd?: number | null }).credit_usd ?? 5);

    if (data.action === "approve" && accountId) {
      const { grantPurchase } = await import("./account.server");
      await grantPurchase({
        accountId,
        usd: creditUsd,
        paymentRef: (payment as { reference?: string | null }).reference ?? data.paymentId,
      });
    }

    return { ok: true };
  });

/** Admin-only: every top-up submission with its account balance. */
export const listAdminData = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { data: isAdmin } = await context.supabase.rpc("has_role", {
      _user_id: context.userId,
      _role: "admin",
    });
    if (!isAdmin) throw new Error("Forbidden");

    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const [{ data: payments }, { data: accounts }] = await Promise.all([
      supabaseAdmin.from("payments").select("*").order("created_at", { ascending: false }),
      supabaseAdmin.from("accounts").select("*").order("created_at", { ascending: false }),
    ]);

    const signedShots: Record<string, string> = {};
    for (const p of payments ?? []) {
      const path = (p as { screenshot_path?: string | null }).screenshot_path;
      if (!path) continue;
      const { data: signed } = await supabaseAdmin.storage
        .from("receipts")
        .createSignedUrl(path, 60 * 60);
      if (signed?.signedUrl) signedShots[p.id] = signed.signedUrl;
    }

    return { payments: payments ?? [], accounts: accounts ?? [], signedShots };
  });
