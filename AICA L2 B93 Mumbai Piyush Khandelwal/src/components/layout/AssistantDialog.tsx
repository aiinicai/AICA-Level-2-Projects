import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const SUGGESTIONS = [
  "What was our revenue growth last quarter?",
  "Which customers owe us the most?",
  "Show expenses by category for this year",
  "Which products are slow moving?",
];

/**
 * Placeholder assistant surface. It deliberately does not fabricate answers —
 * no model or analysis backend is connected yet.
 */
export function AssistantDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState<string | null>(null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="size-4 text-primary" aria-hidden />
            Ask your data
          </DialogTitle>
          <DialogDescription>
            Natural-language questions over your connected datasets.
          </DialogDescription>
        </DialogHeader>

        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (question.trim()) setAsked(question.trim());
          }}
        >
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What was our revenue growth last quarter?"
            aria-label="Your question"
          />
          <Button type="submit" size="icon" aria-label="Ask">
            <ArrowRight className="size-4" aria-hidden />
          </Button>
        </form>

        {asked ? (
          <div className="rounded-lg border bg-surface-muted p-4 text-sm">
            <p className="font-medium">“{asked}”</p>
            <p className="mt-2 text-muted-foreground">
              The assistant isn't connected to an analysis engine yet, so no answer is generated — nothing here is
              invented. Once it's switched on, questions like this will resolve into a live query and a chart you can
              drop straight onto a dashboard.
            </p>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => onOpenChange(false)} asChild>
              <a href="/explorer">Build this in Data Explorer</a>
            </Button>
          </div>
        ) : (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Examples</p>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setQuestion(s)}
                className="block w-full rounded-lg border bg-surface px-3 py-2 text-left text-sm transition hover:border-border-strong"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
