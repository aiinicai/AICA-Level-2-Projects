import type { Category } from "@/lib/recon";

const styles: Record<Category, string> = {
  Matched: "bg-matched-soft text-matched",
  "Amount Mismatch": "bg-mismatch-soft text-mismatch",
  "Missing in 2B": "bg-risk-soft text-risk",
  "ITC Ineligible": "bg-risk-soft text-risk",
  "Missing in Books": "bg-info-soft text-info",
  "Duplicate in Books": "bg-duplicate-soft text-duplicate",
  "Duplicate in 2B": "bg-duplicate-soft text-duplicate",
};

export function CategoryBadge({ category }: { category: Category }) {
  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${styles[category]}`}
    >
      {category}
    </span>
  );
}
