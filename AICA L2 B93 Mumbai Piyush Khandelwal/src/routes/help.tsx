import { createFileRoute, Link } from "@tanstack/react-router";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/common/states";
import { InstallAppButton } from "@/components/pwa/InstallAppButton";

export const Route = createFileRoute("/help")({
  head: () => ({
    meta: [
      { title: "Help & getting started — The DASH" },
      { name: "description", content: "How to connect data, build dashboards, schedule reports and install The DASH on your phone." },
      { property: "og:title", content: "Help & getting started — The DASH" },
      { property: "og:description", content: "Connect data, build dashboards, schedule reports, install the app." },
    ],
  }),
  component: HelpPage,
});

const FAQS = [
  {
    q: "Where does the data on my dashboards come from?",
    a: "This workspace is running in demo mode, so every number is generated from a fixed demo dataset and labelled “Demo data”. Once you connect a real system in Integrations, widgets read from that source instead — the widgets themselves don't change.",
  },
  {
    q: "How do I build a dashboard?",
    a: "Open Dashboards → New dashboard, pick a template or start blank, then switch on Edit layout. Add widgets, drag them to reorder, resize from the widget menu and configure data, visualisation, formatting and behaviour in the side panel.",
  },
  {
    q: "How do global filters work?",
    a: "Filters set at the top of a dashboard — date range, branch, region, customer, salesperson — are passed into every widget query. A filter is skipped automatically for widgets whose dataset doesn't contain that field.",
  },
  {
    q: "Can I see the records behind a number?",
    a: "Yes. Open a widget's menu and choose View records, or click a KPI. The drill-down panel lists the underlying rows with search, sorting and CSV export.",
  },
  {
    q: "How do scheduled reports and alerts work?",
    a: "In Automations you can schedule a report (for example Monthly Financial Review on the 1st at 09:00) and define alerts on any metric with a condition and threshold. Delivery needs email set up on your workspace; nothing is sent from demo mode.",
  },
  {
    q: "Are my credentials safe?",
    a: "Credentials for production connectors are only ever handled server-side and stored as secrets. The browser never receives them, and demo adapters never call a provider at all.",
  },
];

function HelpPage() {
  return (
    <div className="pb-10">
      <PageHeader title="Help & getting started" description="Short answers to the questions people ask on day one." />

      <div className="mx-auto max-w-3xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        <section className="panel p-5">
          <h2 className="text-sm font-semibold">Quick start</h2>
          <ol className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li>1. Connect a data source from the integration marketplace.</li>
            <li>2. Start from a dashboard template, or ask a question in Data Explorer.</li>
            <li>3. Schedule a report or alert so the numbers reach you without logging in.</li>
            <li>4. Invite your team and set their roles.</li>
          </ol>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button asChild size="sm">
              <Link to="/integrations">Connect a source</Link>
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link to="/onboarding">Run the setup guide</Link>
            </Button>
            <InstallAppButton variant="menu" />
          </div>
        </section>

        <section className="panel p-5">
          <h2 className="mb-2 text-sm font-semibold">Frequently asked</h2>
          <Accordion type="single" collapsible>
            {FAQS.map((f) => (
              <AccordionItem key={f.q} value={f.q}>
                <AccordionTrigger className="text-left text-sm">{f.q}</AccordionTrigger>
                <AccordionContent className="text-sm text-muted-foreground">{f.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </section>
      </div>
    </div>
  );
}
