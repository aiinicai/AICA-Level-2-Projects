import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { ArrowRight, Check, LayoutDashboard, Plug, Sparkles, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useWorkspace } from "@/lib/store";
import { INTEGRATIONS } from "@/lib/integrations/catalog";
import { SEED_DASHBOARDS } from "@/lib/data/seed";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/onboarding")({
  head: () => ({
    meta: [
      { title: "Set up your workspace — The DASH" },
      { name: "description", content: "Four short steps: connect a source, pick a template, name your workspace and invite your team." },
      { property: "og:title", content: "Set up your workspace — The DASH" },
      { property: "og:description", content: "Connect data, pick a template and invite your team." },
    ],
  }),
  component: OnboardingPage,
});

const STEPS = ["Welcome", "Connect", "Template", "Team"];

function OnboardingPage() {
  const navigate = useNavigate();
  const { createDashboard, completeOnboarding, updateSettings, settings, upsertMember } = useWorkspace();
  const [step, setStep] = useState(0);
  const [provider, setProvider] = useState<string | null>(null);
  const [template, setTemplate] = useState(SEED_DASHBOARDS[0]?.id ?? "");
  const [workspace, setWorkspace] = useState(settings.workspaceName);
  const [invites, setInvites] = useState("");

  const popular = INTEGRATIONS.filter((i) => i.popular).slice(0, 6);

  const finish = () => {
    updateSettings({ workspaceName: workspace || settings.workspaceName });
    invites
      .split(",")
      .map((e) => e.trim())
      .filter((e) => e.includes("@"))
      .forEach((email) =>
        upsertMember({
          id: `invite-${email}`,
          name: email.split("@")[0],
          email,
          role: "viewer",
          status: "invited",
        }),
      );
    const from = SEED_DASHBOARDS.find((d) => d.id === template);
    const created = from ? createDashboard(from.name, from) : undefined;
    completeOnboarding();
    toast.success("Workspace ready");
    navigate(created ? { to: "/dashboards/$dashboardId", params: { dashboardId: created.id } } : { to: "/" });
  };

  return (
    <main className="min-h-screen bg-surface-muted px-4 py-10">
      <div className="mx-auto max-w-2xl space-y-5">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-semibold">
            <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
              D
            </span>
            The DASH
          </span>
          <Button variant="ghost" size="sm" onClick={() => { completeOnboarding(); navigate({ to: "/" }); }}>
            Skip setup
          </Button>
        </div>

        <ol className="flex items-center gap-2 text-xs" aria-label="Setup steps">
          {STEPS.map((s, i) => (
            <li key={s} className="flex items-center gap-2">
              <span
                className={cn(
                  "flex size-5 items-center justify-center rounded-full border text-[10px] font-semibold",
                  i < step && "border-positive bg-positive-soft text-positive",
                  i === step && "border-primary bg-primary text-primary-foreground",
                  i > step && "text-muted-foreground",
                )}
              >
                {i < step ? <Check className="size-3" aria-hidden /> : i + 1}
              </span>
              <span className={i === step ? "font-medium" : "text-muted-foreground"}>{s}</span>
            </li>
          ))}
        </ol>

        <div className="panel space-y-4 p-6">
          {step === 0 && (
            <>
              <span className="flex size-10 items-center justify-center rounded-xl bg-primary-soft text-primary">
                <Sparkles className="size-5" aria-hidden />
              </span>
              <h1 className="text-xl font-semibold tracking-tight">Welcome to The DASH</h1>
              <p className="text-sm text-muted-foreground">
                Bring your accounting, payments and sales data into one place, then build dashboards, reports and alerts
                on top of it. Setup takes about a minute — you can skip and come back at any time.
              </p>
              <div className="space-y-1.5">
                <Label htmlFor="ws">What should we call your workspace?</Label>
                <Input id="ws" value={workspace} onChange={(e) => setWorkspace(e.target.value)} />
              </div>
              <Button onClick={() => setStep(1)}>
                Get started <ArrowRight className="size-4" aria-hidden />
              </Button>
            </>
          )}

          {step === 1 && (
            <>
              <span className="flex size-10 items-center justify-center rounded-xl bg-primary-soft text-primary">
                <Plug className="size-5" aria-hidden />
              </span>
              <h1 className="text-xl font-semibold tracking-tight">Connect your first source</h1>
              <p className="text-sm text-muted-foreground">
                Pick where your numbers live. You can add more later, and explore demo data in the meantime.
              </p>
              <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {popular.map((i) => (
                  <li key={i.id}>
                    <button
                      type="button"
                      onClick={() => setProvider(i.id)}
                      className={cn(
                        "w-full rounded-lg border p-3 text-left text-xs transition",
                        provider === i.id ? "border-primary bg-primary-soft" : "hover:border-border-strong",
                      )}
                    >
                      <span
                        className="mb-2 flex size-7 items-center justify-center rounded-md text-[10px] font-semibold text-white"
                        style={{ backgroundColor: i.accent }}
                        aria-hidden
                      >
                        {i.initials}
                      </span>
                      <span className="block font-medium">{i.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap gap-2">
                <Button variant="ghost" onClick={() => setStep(0)}>Back</Button>
                {provider && (
                  <Button variant="outline" asChild>
                    <Link to="/integrations/$providerId" params={{ providerId: provider }}>
                      Connect now
                    </Link>
                  </Button>
                )}
                <Button onClick={() => setStep(2)}>Continue with demo data</Button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <span className="flex size-10 items-center justify-center rounded-xl bg-primary-soft text-primary">
                <LayoutDashboard className="size-5" aria-hidden />
              </span>
              <h1 className="text-xl font-semibold tracking-tight">Choose a starting dashboard</h1>
              <ul className="space-y-2">
                {SEED_DASHBOARDS.map((d) => (
                  <li key={d.id}>
                    <button
                      type="button"
                      onClick={() => setTemplate(d.id)}
                      className={cn(
                        "w-full rounded-lg border p-3 text-left transition",
                        template === d.id ? "border-primary bg-primary-soft" : "hover:border-border-strong",
                      )}
                    >
                      <span className="block text-sm font-medium">{d.name}</span>
                      <span className="block text-xs text-muted-foreground">{d.description}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => setStep(1)}>Back</Button>
                <Button onClick={() => setStep(3)}>Continue</Button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <span className="flex size-10 items-center justify-center rounded-xl bg-primary-soft text-primary">
                <Users className="size-5" aria-hidden />
              </span>
              <h1 className="text-xl font-semibold tracking-tight">Invite your team</h1>
              <div className="space-y-1.5">
                <Label htmlFor="invites">Email addresses</Label>
                <Input
                  id="invites"
                  value={invites}
                  placeholder="priya@acme.in, amit@acme.in"
                  onChange={(e) => setInvites(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Invites are saved to your team list. Email delivery needs a mail sender on your workspace.
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => setStep(2)}>Back</Button>
                <Button onClick={finish}>Finish setup</Button>
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
