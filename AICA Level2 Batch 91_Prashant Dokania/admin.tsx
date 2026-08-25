import { createFileRoute } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { listAdminData, reviewPayment } from "@/lib/billing.functions";

export const Route = createFileRoute("/_authenticated/admin")({
  head: () => ({
    meta: [
      { title: "Top-up approvals — MIRROR" },
      {
        name: "description",
        content: "Review UPI top-up receipts and add credit to the account that sent them.",
      },
      { property: "og:title", content: "Top-up approvals — MIRROR" },
      { property: "og:description", content: "Manual credit approvals for MIRROR top-ups." },
    ],
  }),
  component: AdminScreen,
});

type AdminData = Awaited<ReturnType<typeof listAdminData>>;

function AdminScreen() {
  const load = useServerFn(listAdminData);
  const review = useServerFn(reviewPayment);
  const [data, setData] = useState<AdminData | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setData(await load({}));
    } catch (e) {
      setError(e instanceof Error ? e.message : "That could not be loaded.");
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function act(paymentId: string, action: "approve" | "reject") {
    setBusyId(paymentId);
    setError(null);
    try {
      await review({ data: { paymentId, action } });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not go through.");
    } finally {
      setBusyId(null);
    }
  }

  const accountLabel = (accountId: string | null) => {
    if (!accountId) return "Unknown account";
    const account = (data?.accounts ?? []).find((a) => a.id === accountId);
    return account?.email ?? `Anonymous device ${accountId.slice(0, 8)}`;
  };

  const pending = (data?.payments ?? []).filter((p) => p.status === "pending");
  const reviewed = (data?.payments ?? []).filter((p) => p.status !== "pending");

  return (
    <Shell
      eyebrow="Admin"
      title="Top-up approvals."
      lead="Every UPI receipt lands here. Approving one adds that credit to the account straight away."
    >
      {error ? (
        <p className="text-sm" style={{ color: "var(--rust)" }}>
          {error}
        </p>
      ) : null}

      <section className="space-y-3">
        <p className="eyebrow">Waiting on you ({pending.length})</p>
        {pending.length === 0 ? (
          <div className="panel p-5 text-sm text-muted-foreground">Nothing pending right now.</div>
        ) : (
          pending.map((p) => (
            <div key={p.id} className="panel space-y-3 p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-display text-2xl">{accountLabel(p.account_id)}</p>
                <p className="text-xs text-muted-foreground">
                  {new Date(p.created_at).toLocaleString()} · ₹{p.amount_inr} · $
                  {Number(p.credit_usd).toFixed(2)} credit
                </p>
              </div>
              {p.reference ? (
                <p className="text-sm text-muted-foreground">Reference: {p.reference}</p>
              ) : null}
              {data?.signedShots[p.id] ? (
                <a href={data.signedShots[p.id]} target="_blank" rel="noreferrer">
                  <img
                    src={data.signedShots[p.id]}
                    alt={`Payment receipt from ${accountLabel(p.account_id)}`}
                    className="max-h-64 rounded-xl border border-border"
                  />
                </a>
              ) : (
                <p className="text-xs text-muted-foreground">No screenshot attached.</p>
              )}
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={busyId === p.id}
                  onClick={() => void act(p.id, "approve")}
                  className="rounded-full px-6 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
                  style={{ background: "var(--gradient-brass)" }}
                >
                  Approve credit
                </button>
                <button
                  type="button"
                  disabled={busyId === p.id}
                  onClick={() => void act(p.id, "reject")}
                  className="rounded-full border border-border px-6 py-2 text-sm text-muted-foreground hover:text-foreground disabled:opacity-60"
                >
                  Reject
                </button>
              </div>
            </div>
          ))
        )}
      </section>

      <section className="space-y-3">
        <p className="eyebrow">Accounts</p>
        <div className="panel divide-y divide-border/60">
          {(data?.accounts ?? []).slice(0, 40).map((a) => (
            <div key={a.id} className="flex flex-wrap justify-between gap-2 p-4 text-sm">
              <span className="text-foreground">
                {a.email ?? `Anonymous device ${a.id.slice(0, 8)}`}
              </span>
              <span className="text-xs text-muted-foreground">
                welcome ${Number(a.welcome_credit_remaining_usd).toFixed(2)} · monthly $
                {Number(a.monthly_credit_remaining_usd).toFixed(2)} · purchased $
                {Number(a.purchased_credit_balance_usd).toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </section>

      {reviewed.length > 0 ? (
        <section className="space-y-3">
          <p className="eyebrow">Already handled</p>
          <div className="panel divide-y divide-border/60">
            {reviewed.slice(0, 30).map((p) => (
              <div key={p.id} className="flex flex-wrap justify-between gap-2 p-4 text-sm">
                <span className="text-foreground">{accountLabel(p.account_id)}</span>
                <span className="text-xs text-muted-foreground">
                  {p.status} · {new Date(p.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </Shell>
  );
}
