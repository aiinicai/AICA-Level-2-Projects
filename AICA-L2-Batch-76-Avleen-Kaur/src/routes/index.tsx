import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ShieldCheck, ArrowRight, RotateCcw } from "lucide-react";
import { UploadZone } from "@/components/UploadZone";
import { Dashboard } from "@/components/Dashboard";
import { ReconTable } from "@/components/ReconTable";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Toaster } from "@/components/ui/sonner";
import { reconcile, rowsToInvoices, type RawRow, type ReconRow } from "@/lib/recon";

const title = "GST Reconciliation Assistant — GSTR-2B vs Purchase Register";
const description =
  "Reconcile GSTR-2B against your purchase register in seconds. Match invoices, spot ITC at risk, and export an audit-ready Excel report.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: Index,
});

const STEPS = ["Upload", "Review", "Report"] as const;

function Index() {
  const [gstr2b, setGstr2b] = useState<RawRow[] | null>(null);
  const [books, setBooks] = useState<RawRow[] | null>(null);
  const [rows, setRows] = useState<ReconRow[] | null>(null);
  const step = rows ? 2 : gstr2b && books ? 1 : 0;

  const run = () => {
    if (!gstr2b || !books) return;
    setRows(reconcile(rowsToInvoices(books), rowsToInvoices(gstr2b)));
  };

  return (
    <div className="min-h-screen bg-background">
      <Toaster />
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <ShieldCheck className="size-5" />
            </span>
            <div>
              <h1 className="text-base font-semibold leading-tight text-foreground">
                GST Reconciliation Assistant
              </h1>
              <p className="text-xs text-muted-foreground">GSTR-2B vs Purchase Register</p>
            </div>
          </div>
          <nav className="ml-auto flex items-center gap-2 text-sm">
            {STEPS.map((s, i) => (
              <span key={s} className="flex items-center gap-2">
                <span
                  className={`rounded-full px-3 py-1 ${
                    i === step
                      ? "bg-primary text-primary-foreground"
                      : i < step
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground"
                  }`}
                >
                  {s}
                </span>
                {i < STEPS.length - 1 && <ArrowRight className="size-3.5 text-muted-foreground" />}
              </span>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
        {!rows ? (
          <>
            <Card className="border-l-4 border-l-primary p-4">
              <p className="text-sm text-muted-foreground">
                Upload your GSTR-2B export downloaded from the GST Portal. This tool does not connect to or
                store any GST portal credentials. All matching runs in your browser.
              </p>
            </Card>

            <div className="grid gap-6 lg:grid-cols-2">
              <UploadZone
                title="Upload GSTR-2B (Excel/CSV)"
                hint="Expected: GSTIN, Supplier Name, Invoice Number, Invoice Date, Invoice Value, Taxable Value, IGST, CGST, SGST, ITC Availability"
                onLoaded={(r) => setGstr2b(r)}
              />
              <UploadZone
                title="Upload Purchase Register (Excel/CSV)"
                hint="Expected: GSTIN, Supplier Name, Invoice Number, Invoice Date, Invoice Value, Taxable Value, IGST, CGST, SGST"
                onLoaded={(r) => setBooks(r)}
              />
            </div>

            <div className="flex justify-end">
              <Button size="lg" disabled={!gstr2b || !books} onClick={run}>
                Run reconciliation <ArrowRight />
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="mr-auto text-xl font-semibold text-foreground">Reconciliation report</h2>
              <Button
                variant="outline"
                onClick={() => {
                  setRows(null);
                  setGstr2b(null);
                  setBooks(null);
                }}
              >
                <RotateCcw /> Start over
              </Button>
            </div>
            <Dashboard rows={rows} />
            <ReconTable rows={rows} />
          </>
        )}
      </main>

      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        Matching on GSTIN + normalised invoice number, with ₹1 rounding tolerance.
      </footer>
    </div>
  );
}
