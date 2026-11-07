import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Easy AI Procura — LPO, GRN & Invoice Matching Control" },
      {
        name: "description",
        content:
          "Procurement control with strict maker–checker approvals: local purchase orders, goods received notes, invoice matching and controlled master data.",
      },
      { property: "og:title", content: "Easy AI Procura — LPO, GRN & Invoice Matching Control" },
      {
        property: "og:description",
        content:
          "Procurement control with strict maker–checker approvals: local purchase orders, goods received notes, invoice matching and controlled master data.",
      },
    ],
  }),
  component: Landing,
});

const flow = [
  {
    step: "01",
    title: "Local Purchase Order",
    body: "Maker raises an LPO against approved suppliers and departments. Line values calculate automatically; the approver locks it.",
  },
  {
    step: "02",
    title: "Goods Received Note",
    body: "Storekeeper receives against an approved LPO only. Shortage or excess and item condition are captured per line.",
  },
  {
    step: "03",
    title: "Invoice Matching",
    body: "Finance raises the invoice from an approved GRN. Price variance against the LPO is flagged before approval.",
  },
];

function Landing() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-2">
            <span className="grid size-8 place-items-center rounded bg-primary text-sm font-bold text-primary-foreground">
              P
            </span>
            <span className="text-sm font-semibold uppercase tracking-[0.22em]">Easy AI Procura</span>
          </div>
          <Link
            to="/auth"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Sign in
          </Link>
        </div>
      </header>

      <section className="doc-grid border-b border-border">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <p className="num text-xs uppercase tracking-[0.3em] text-primary">Maker · Checker · Locked</p>
          <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-tight sm:text-5xl">
            Purchase order to invoice, with every approval on record.
          </h1>
          <p className="mt-5 max-w-2xl text-base text-muted-foreground">
            Controlled master data, auto-numbered documents, three-way matching between LPO, GRN and supplier invoice —
            and no one approving their own work.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/auth"
              className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Open the workspace
            </Link>
            <Link
              to="/dashboard"
              className="rounded-md border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-accent"
            >
              Go to dashboard
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">The document trail</h2>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {flow.map((f) => (
            <article key={f.step} className="rounded-lg border border-border bg-card p-6">
              <p className="num text-2xl font-semibold text-primary">{f.step}</p>
              <h3 className="mt-3 text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="border-t border-border py-8">
        <p className="mx-auto max-w-6xl px-6 text-xs text-muted-foreground">
          Easy AI Procura — internal procurement control. Documents numbered LPO-YYYY-0000, GRN-YYYY-0000, INV-YYYY-0000.
        </p>
      </footer>
    </div>
  );
}
