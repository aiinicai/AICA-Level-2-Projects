import { useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Check, Plug, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, PageHeader } from "@/components/common/states";
import { CATEGORIES, INTEGRATIONS } from "@/lib/integrations/catalog";
import { useWorkspace } from "@/lib/store";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/integrations/")({
  head: () => ({
    meta: [
      { title: "Connect your business — The DASH" },
      {
        name: "description",
        content: "Connect Tally, Zoho, QuickBooks, Razorpay, Shopify, Google Sheets and more to The DASH in a few steps.",
      },
      { property: "og:title", content: "Connect your business — The DASH" },
      { property: "og:description", content: "Accounting, payments, CRM and e-commerce systems in one place." },
    ],
  }),
  component: IntegrationsPage,
});

function IntegrationsPage() {
  const { connections } = useWorkspace();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<string>("All");

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    return INTEGRATIONS.filter(
      (i) =>
        (category === "All" || i.category === category) &&
        (!term || i.name.toLowerCase().includes(term) || i.tagline.toLowerCase().includes(term)),
    );
  }, [q, category]);

  return (
    <div className="pb-10">
      <PageHeader
        title="Connect your business"
        description="Bring accounting, payments, CRM and e-commerce data into one workspace."
        actions={
          <Button variant="outline" asChild>
            <Link to="/data-sources">
              <Plug className="size-4" aria-hidden /> Connected sources
            </Link>
          </Button>
        }
      />

      <div className="space-y-5 px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search integrations"
              aria-label="Search integrations"
              className="pl-9"
            />
          </div>
        </div>

        <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
          {["All", ...CATEGORIES].map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCategory(c)}
              aria-pressed={category === c}
              className={cn(
                "shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium transition",
                category === c ? "border-primary bg-primary text-primary-foreground" : "bg-surface hover:border-border-strong",
              )}
            >
              {c}
            </button>
          ))}
        </div>

        {results.length === 0 ? (
          <EmptyState
            icon={Search}
            title="No integrations found"
            description="Try a different search term, or connect any system through the generic REST API adapter."
            action={
              <Button asChild>
                <Link to="/integrations/$providerId" params={{ providerId: "custom_rest" }}>
                  Use REST API
                </Link>
              </Button>
            }
          />
        ) : (
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {results.map((i) => {
              const connected = connections.some((c) => c.providerId === i.id && c.status === "connected");
              return (
                <li key={i.id}>
                  <Link
                    to="/integrations/$providerId"
                    params={{ providerId: i.id }}
                    className="panel flex h-full items-start gap-3 p-4 transition hover:border-border-strong hover:shadow-soft"
                  >
                    <span
                      className="flex size-10 shrink-0 items-center justify-center rounded-lg text-sm font-semibold text-white"
                      style={{ backgroundColor: i.accent }}
                      aria-hidden
                    >
                      {i.initials}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate text-sm font-semibold">{i.name}</span>
                        {connected && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-positive-soft px-1.5 py-0.5 text-[10px] font-medium text-positive">
                            <Check className="size-3" aria-hidden /> Connected
                          </span>
                        )}
                      </span>
                      <span className="mt-0.5 block line-clamp-2 text-xs text-muted-foreground">{i.tagline}</span>
                      <span className="mt-2 block text-[11px] uppercase tracking-wide text-muted-foreground">
                        {i.category}
                      </span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
