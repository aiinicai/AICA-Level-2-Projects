import defensive from "@/content/blog/why-do-i-sound-defensive.md?raw";
import ramble from "@/content/blog/why-you-ramble-in-interviews.md?raw";
import relationship from "@/content/blog/relationship-communication.md?raw";

export type Post = {
  slug: string;
  title: string;
  description: string;
  date: string;
  readingMinutes: number;
  tag: string;
  markdown: string;
};

function titleOf(markdown: string) {
  const line = markdown.split("\n").find((l) => l.startsWith("# "));
  return line ? line.slice(2).trim() : "Untitled";
}

function bodyOf(markdown: string) {
  return markdown.replace(/^#\s.*$/m, "").trim();
}

function minutesOf(markdown: string) {
  return Math.max(1, Math.round(markdown.split(/\s+/).length / 200));
}

const RAW: Array<{ slug: string; date: string; tag: string; description: string; raw: string }> = [
  {
    slug: "why-do-i-sound-defensive",
    date: "2026-08-08",
    tag: "Spouse & partner",
    description:
      "Defensiveness rarely sounds like an argument from the inside. Here's what it actually looks like — and how to catch it while it's happening.",
    raw: defensive,
  },
  {
    slug: "relationship-communication",
    date: "2026-08-06",
    tag: "Spouse & partner",
    description:
      '"Communicate more" isn\'t the advice most couples need. The patterns that predict how conflict goes — and how to see your own.',
    raw: relationship,
  },
  {
    slug: "why-you-ramble-in-interviews",
    date: "2026-08-04",
    tag: "Interviews",
    description:
      "Rambling in interviews is a delivery problem, not a knowledge problem. How to hear your own pacing before it costs you the offer.",
    raw: ramble,
  },
];

export const POSTS: Post[] = RAW.map((p) => ({
  slug: p.slug,
  title: titleOf(p.raw),
  description: p.description,
  date: p.date,
  tag: p.tag,
  readingMinutes: minutesOf(p.raw),
  markdown: bodyOf(p.raw),
}));

export function postOf(slug: string): Post | undefined {
  return POSTS.find((p) => p.slug === slug);
}

export function formatDate(iso: string) {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}
