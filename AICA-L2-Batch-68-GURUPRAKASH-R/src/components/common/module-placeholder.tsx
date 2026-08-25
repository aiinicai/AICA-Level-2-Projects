import { Plus } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { DataTableShell } from "@/components/common/data-table-shell";
import { PageHeader } from "@/components/common/page-header";
import { SearchBox } from "@/components/common/search-box";
import { FilterPanel, type FilterDefinition } from "@/components/common/filter-panel";
import { useState } from "react";

export interface ModulePlaceholderProps {
  title: string;
  description: string;
  addLabel?: string;
  stageNote?: string;
  columns?: { key: string; header: string }[];
  filters?: FilterDefinition[];
  children?: ReactNode;
}

const DEFAULT_FILTERS: FilterDefinition[] = [
  {
    key: "engagement",
    label: "Engagement",
    options: [
      { value: "ENG-0042", label: "ENG-0042" },
      { value: "ENG-0039", label: "ENG-0039" },
    ],
  },
  {
    key: "status",
    label: "Status",
    options: [
      { value: "pending", label: "Pending" },
      { value: "in-progress", label: "In progress" },
      { value: "closed", label: "Closed" },
    ],
  },
];

/**
 * Standard Stage 1 module page: heading, breadcrumb, toolbar, filters and an
 * empty register. Real registers and forms arrive in later stages.
 */
export function ModulePlaceholder({
  title,
  description,
  addLabel,
  stageNote = "This module will be implemented in a later stage of the build.",
  columns = [
    { key: "reference", header: "Reference" },
    { key: "title", header: "Particulars" },
    { key: "owner", header: "Owner" },
    { key: "status", header: "Status" },
    { key: "updated", header: "Last updated" },
  ],
  filters = DEFAULT_FILTERS,
  children,
}: ModulePlaceholderProps) {
  const [search, setSearch] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});

  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={description}
        breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: title }]}
        actions={
          addLabel ? (
            <Button size="sm" disabled>
              <Plus className="size-4" aria-hidden />
              {addLabel}
            </Button>
          ) : undefined
        }
      />

      {children}

      <FilterPanel
        filters={filters}
        values={filterValues}
        onChange={(key, value) => setFilterValues((prev) => ({ ...prev, [key]: value }))}
        onReset={() => setFilterValues({})}
      />

      <DataTableShell
        columns={columns}
        isEmpty
        emptyTitle="No records available"
        emptyMessage={stageNote}
        toolbar={
          <>
            <SearchBox value={search} onChange={setSearch} placeholder={`Search ${title.toLowerCase()}…`} />
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled>
                Export
              </Button>
              <Button variant="outline" size="sm" disabled>
                Columns
              </Button>
            </div>
          </>
        }
        footer={`Showing 0 records — ${stageNote}`}
      />
    </div>
  );
}
