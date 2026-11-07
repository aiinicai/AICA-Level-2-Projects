import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/procurement/PageHeader";
import { Button } from "@/components/ui/button";
import { quoteForDate, type Quote } from "@/lib/quotes";

export const Route = createFileRoute("/_authenticated/motivation")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Daily Motivation — Easy AI Procura" },
      { name: "description", content: "A fresh motivational quote for the procurement team every day." },
      { property: "og:title", content: "Daily Motivation — Easy AI Procura" },
      { property: "og:description", content: "A fresh motivational quote for the procurement team every day." },
    ],
  }),
  component: Motivation,
});

function Motivation() {
  const [today, setToday] = useState<Date | null>(null);
  const [offset, setOffset] = useState(0);
  useEffect(() => setToday(new Date()), []);
  const quote: Quote | null = today ? quoteForDate(today, offset) : null;

  return (
    <div>
      <PageHeader title="Quote of the day" subtitle="A new quote appears every day at midnight." />
      <figure className="doc-grid mx-auto max-w-3xl rounded-xl border border-border bg-card p-10 text-center md:p-16">
        <p className="text-xs uppercase tracking-[0.25em] text-primary">
          {today?.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        </p>
        <blockquote className="mt-8 text-2xl font-medium leading-snug text-foreground md:text-4xl">
          “{quote?.text}”
        </blockquote>
        <figcaption className="mt-6 text-sm text-muted-foreground">— {quote?.author}</figcaption>
        <div className="mt-10 flex flex-wrap justify-center gap-2">
          <Button variant="outline" onClick={() => setOffset((o) => o + 1)}>
            Show another
          </Button>
          {offset !== 0 ? (
            <Button variant="ghost" onClick={() => setOffset(0)}>
              Back to today's quote
            </Button>
          ) : null}
          <Button
            variant="ghost"
            onClick={() => quote && navigator.clipboard?.writeText(`“${quote.text}” — ${quote.author}`)}
          >
            Copy
          </Button>
        </div>
      </figure>
    </div>
  );
}
