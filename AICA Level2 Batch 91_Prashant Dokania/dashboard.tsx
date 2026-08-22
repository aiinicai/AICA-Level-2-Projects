import { createFileRoute, Link } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { getWeeklyPatterns } from "@/lib/mirror.functions";
import { getDevice } from "@/lib/device";
import { useMirror } from "@/hooks/useMirror";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "This week — MIRROR" },
      {
        name: "description",
        content:
          "Patterns from the last seven days, kept separate by the kind of conversation, each with strengths noticed and one gentle suggestion.",
      },
      { property: "og:title", content: "This week — MIRROR" },
      { property: "og:description", content: "Patterns noticed, never scores." },
    ],
  }),
  component: DashboardScreen,
});

type Group = { context: string; count: number; strengths: string[]; growth: string[] };

function DashboardScreen() {
  const load = useServerFn(getWeeklyPatterns);
  const { state } = useMirror();
  const [groups, setGroups] = useState<Group[] | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setGroups((await load({ data: { device: getDevice() } })) as Group[]);
      } catch {
        setGroups([]);
      }
    })();
  }, [load]);

  if (!state?.identity.email) {
    return (
      <Shell
        eyebrow="This week"
        title="Patterns need somewhere safe to live."
        lead="Weekly patterns are kept for email accounts only. While you're anonymous nothing is stored beyond your last reflection, so a shared device never shows your history to someone else."
      >
        <Link
          to="/auth"
          className="inline-block rounded-full px-7 py-2.5 text-sm font-medium text-primary-foreground"
          style={{ background: "var(--gradient-brass)" }}
        >
          Add my email
        </Link>
      </Shell>
    );
  }

  return (
    <Shell
      eyebrow="This week"
      title="What kept showing up."
      lead="Grouped by the kind of conversation it was, so a work exchange and one at home are never blended into a single score."
    >
      {groups === null ? (
        <p className="text-sm text-muted-foreground">Gathering the week…</p>
      ) : groups.length === 0 ? (
        <div className="panel p-6 text-sm leading-relaxed text-muted-foreground">
          Nothing from the last seven days yet. Talk or write once and this fills in on its own.
        </div>
      ) : (
        groups.map((g) => (
          <section key={g.context} className="panel space-y-4 p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="font-display text-2xl capitalize">
                {g.context === "none" ? "On your own" : g.context.replace(/_/g, " ")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {g.count} {g.count === 1 ? "reflection" : "reflections"}
              </p>
            </div>

            {g.strengths.length > 0 ? (
              <div
                className="rounded-xl border p-4"
                style={{ borderColor: "var(--sage)", backgroundColor: "var(--sage-soft)" }}
              >
                <p className="text-xs uppercase tracking-[0.2em]" style={{ color: "var(--sage)" }}>
                  Strengths noticed
                </p>
                <ul className="mt-2 space-y-2 text-sm leading-relaxed text-foreground/85">
                  {g.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {g.growth.length > 0 ? (
              <div
                className="rounded-xl border p-4"
                style={{ borderColor: "var(--rust)", backgroundColor: "var(--rust-soft)" }}
              >
                <p className="text-xs uppercase tracking-[0.2em]" style={{ color: "var(--rust)" }}>
                  One small thing
                </p>
                <p className="mt-2 text-sm leading-relaxed text-foreground/85">{g.growth[0]}</p>
              </div>
            ) : null}
          </section>
        ))
      )}
    </Shell>
  );
}
