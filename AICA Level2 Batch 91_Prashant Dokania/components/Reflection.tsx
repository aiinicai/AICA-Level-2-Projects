import type { Analysis } from "@/lib/mirror-types";
import { Markdown } from "@/components/Markdown";

const LED = {
  problem: "led with the problem",
  context: "led with context",
  unclear: "opening unclear",
} as const;

const TYPE_LABEL: Record<string, string> = {
  conversation: "A conversation you had",
  recap: "Looking back on something",
  rehearsal: "Rehearsing something ahead",
  reflection: "Thinking out loud",
};

export function Reflection({
  analysis,
  sessionType,
  relationshipContext,
  reflection,
  showTranscript = true,
}: {
  analysis: Analysis;
  sessionType: string;
  relationshipContext?: string;
  reflection?: string;
  showTranscript?: boolean;
}) {
  const m = analysis.metrics;
  const hasMetrics = sessionType !== "reflection";
  const stats = [
    { label: "Your airtime", value: `${m.airtimePercent}%` },
    { label: "Questions asked", value: String(m.questionsAsked) },
    { label: '"I" phrasing', value: String(m.iLanguage) },
    { label: '"You" phrasing', value: String(m.youLanguage) },
    { label: "Filler words", value: String(m.fillerWords) },
    { label: "Opening", value: LED[m.ledWith] },
  ];

  return (
    <div className="space-y-8">
      <section className="panel p-6">
        <p className="eyebrow">
          {TYPE_LABEL[sessionType] ?? "Reflection"}
          {relationshipContext && relationshipContext !== "none"
            ? ` · ${relationshipContext.replace(/_/g, " ")}`
            : ""}
        </p>
        {analysis.summary ? (
          <p className="mt-4 font-display text-2xl leading-snug">{analysis.summary}</p>
        ) : null}
        {reflection ? (
          <div className="mt-4 text-sm leading-relaxed text-foreground/85">
            <Markdown source={reflection} />
          </div>
        ) : null}
        {analysis.goalReflection ? (
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            {analysis.goalReflection}
          </p>
        ) : null}
      </section>

      {hasMetrics ? (
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl border border-border bg-surface/50 px-4 py-3">
              <p className="text-lg text-primary">{s.value}</p>
              <p className="mt-1 text-xs text-muted-foreground">{s.label}</p>
            </div>
          ))}
        </section>
      ) : null}

      {analysis.patterns.length > 0 ? (
        <section className="space-y-3">
          <p className="eyebrow">Patterns noticed</p>
          {analysis.patterns.map((p, i) => (
            <article
              key={`${p.title}-${i}`}
              className="rounded-xl border p-5"
              style={{
                borderColor: p.tone === "strength" ? "var(--sage)" : "var(--rust)",
                backgroundColor: p.tone === "strength" ? "var(--sage-soft)" : "var(--rust-soft)",
              }}
            >
              <p
                className="text-xs uppercase tracking-[0.2em]"
                style={{ color: p.tone === "strength" ? "var(--sage)" : "var(--rust)" }}
              >
                {p.tone === "strength" ? "Strength noticed" : "Room to grow"}
              </p>
              <h3 className="mt-2 text-xl">{p.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-foreground/85">{p.observation}</p>
              {p.suggestion ? (
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  <span className="text-primary">One small thing to try — </span>
                  {p.suggestion}
                </p>
              ) : null}
            </article>
          ))}
        </section>
      ) : null}

      {showTranscript && analysis.transcript ? (
        <section className="panel p-6">
          <p className="eyebrow">Your words only</p>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
            {analysis.transcript}
          </p>
        </section>
      ) : null}
    </div>
  );
}
