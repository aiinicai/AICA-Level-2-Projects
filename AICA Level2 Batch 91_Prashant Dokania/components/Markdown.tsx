import type { ReactNode } from "react";

/** Minimal, dependency-free markdown renderer for MIRROR blog posts. */

function inline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${i++}`;

    if (token.startsWith("**")) {
      nodes.push(
        <strong key={key} className="text-foreground">
          {token.slice(2, -2)}
        </strong>,
      );
    } else if (token.startsWith("[")) {
      const linkMatch = /\[([^\]]+)\]\(([^)]+)\)/.exec(token);
      nodes.push(
        <a
          key={key}
          href={linkMatch?.[2] ?? "#"}
          className="text-primary underline underline-offset-4"
        >
          {linkMatch?.[1]}
        </a>,
      );
    } else {
      nodes.push(
        <em key={key} className="italic">
          {token.slice(1, -1)}
        </em>,
      );
    }
    last = match.index + token.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function Markdown({ source }: { source: string }) {
  const blocks = source.split(/\n{2,}/);

  return (
    <div className="space-y-6">
      {blocks.map((block, index) => {
        const key = `block-${index}`;
        const trimmed = block.trim();
        if (!trimmed) return null;

        if (trimmed === "---") {
          return <hr key={key} className="border-border/60" />;
        }

        if (trimmed.startsWith("## ")) {
          return (
            <h2 key={key} className="pt-4 font-display text-2xl leading-snug sm:text-3xl">
              {inline(trimmed.slice(3), key)}
            </h2>
          );
        }

        if (trimmed.startsWith("### ")) {
          return (
            <h3 key={key} className="pt-2 font-display text-xl leading-snug">
              {inline(trimmed.slice(4), key)}
            </h3>
          );
        }

        if (trimmed.split("\n").every((line) => line.trim().startsWith("- "))) {
          return (
            <ul key={key} className="space-y-3 pl-5">
              {trimmed.split("\n").map((line, li) => (
                <li
                  key={`${key}-${li}`}
                  className="list-disc text-base leading-relaxed text-muted-foreground"
                >
                  {inline(line.trim().slice(2), `${key}-${li}`)}
                </li>
              ))}
            </ul>
          );
        }

        const isClosing = trimmed.startsWith("*") && trimmed.endsWith("*");
        return (
          <p
            key={key}
            className={
              isClosing
                ? "text-sm leading-relaxed text-muted-foreground"
                : "text-base leading-relaxed text-muted-foreground"
            }
          >
            {inline(trimmed, key)}
          </p>
        );
      })}
    </div>
  );
}
