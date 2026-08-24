import { createFileRoute } from "@tanstack/react-router";
import { ClientOnly } from "@tanstack/react-router";
import App from "../lease/App";

const title = "Ind AS 116 & Ind AS 12 Lease Engine";
const description =
  "Compute Ind AS 116 / IFRS 16 lessee schedules, deferred tax under Ind AS 12, journal entries, quarterly reports and portfolio disclosures.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-800">
      <ClientOnly fallback={<div className="p-10 text-sm text-slate-500">Loading lease engine…</div>}>
        <App />
      </ClientOnly>
    </div>
  );
}
