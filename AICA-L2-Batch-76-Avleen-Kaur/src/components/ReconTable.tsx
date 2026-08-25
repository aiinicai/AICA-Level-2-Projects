import { useMemo, useState } from "react";
import { Download, Search } from "lucide-react";
import { exportToExcel, formatINR, type Category, type ReconRow } from "@/lib/recon";
import { CategoryBadge } from "@/components/CategoryBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const CATEGORIES: Category[] = [
  "Matched",
  "Amount Mismatch",
  "Missing in 2B",
  "Missing in Books",
  "ITC Ineligible",
  "Duplicate in Books",
  "Duplicate in 2B",
];

export function ReconTable({ rows }: { rows: ReconRow[] }) {
  const [category, setCategory] = useState<string>("all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter(
      (r) =>
        (category === "all" || r.category === category) &&
        (!q || r.gstin.toLowerCase().includes(q) || r.supplier.toLowerCase().includes(q)),
    );
  }, [rows, category, query]);

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="mr-auto text-lg font-semibold text-foreground">Detailed reconciliation</h2>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search GSTIN or supplier"
            className="w-56 pl-9"
          />
        </div>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {CATEGORIES.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button onClick={() => exportToExcel(filtered)}>
          <Download /> Export Excel
        </Button>
      </div>

      <p className="mt-2 text-xs text-muted-foreground">
        Showing {filtered.length} of {rows.length} records
      </p>

      <div className="mt-4 overflow-x-auto rounded-md border border-border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted">
            <tr>
              {[
                "GSTIN",
                "Supplier Name",
                "Invoice Number",
                "Invoice Date",
                "Value (Books)",
                "Value (2B)",
                "Difference",
                "Category",
                "Remarks",
              ].map((h) => (
                <th key={h} className="whitespace-nowrap px-3 py-2.5 text-xs font-semibold text-foreground">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, i) => (
              <tr key={`${r.key}-${i}`} className="border-t border-border align-top hover:bg-muted/50">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-xs">{r.gstin}</td>
                <td className="px-3 py-2">{r.supplier}</td>
                <td className="whitespace-nowrap px-3 py-2">{r.invoiceNumber}</td>
                <td className="whitespace-nowrap px-3 py-2">{r.invoiceDate}</td>
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">
                  {r.valueBooks === null ? "—" : formatINR(r.valueBooks)}
                </td>
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">
                  {r.value2B === null ? "—" : formatINR(r.value2B)}
                </td>
                <td
                  className={`whitespace-nowrap px-3 py-2 tabular-nums ${
                    Math.abs(r.difference) > 1 ? "font-medium text-risk" : "text-muted-foreground"
                  }`}
                >
                  {formatINR(r.difference)}
                </td>
                <td className="px-3 py-2">
                  <CategoryBadge category={r.category} />
                </td>
                <td className="min-w-[220px] px-3 py-2 text-xs text-muted-foreground">{r.remarks}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={9} className="px-3 py-10 text-center text-sm text-muted-foreground">
                  No records match your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
