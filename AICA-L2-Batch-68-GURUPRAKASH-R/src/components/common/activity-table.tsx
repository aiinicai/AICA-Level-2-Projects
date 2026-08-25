import { DataTableShell } from "@/components/common/data-table-shell";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/format";
import type { ActivityRecord } from "@/types/activity";

const COLUMNS = [
  { key: "timestamp", header: "Timestamp", width: "170px" },
  { key: "user", header: "User / role" },
  { key: "module", header: "Module" },
  { key: "reference", header: "Record" },
  { key: "action", header: "Action" },
  { key: "transition", header: "Status change" },
  { key: "remarks", header: "Remarks" },
];

/** Read-only rendering of the append-only activity trail. */
export function ActivityTable({
  entries,
  isLoading,
  emptyMessage = "No activity has been recorded for this record yet.",
}: {
  entries: ActivityRecord[];
  isLoading?: boolean;
  emptyMessage?: string;
}) {
  return (
    <DataTableShell
      columns={COLUMNS}
      caption="Activity log"
      isLoading={isLoading}
      isEmpty={!isLoading && entries.length === 0}
      emptyTitle="No activity yet"
      emptyMessage={emptyMessage}
      footer={entries.length > 0 ? `${entries.length} activity record(s) — append-only.` : undefined}
    >
      {entries.map((entry) => (
        <TableRow key={entry.id}>
          <TableCell className="font-mono text-xs whitespace-nowrap">
            {formatDateTime(entry.timestamp)}
          </TableCell>
          <TableCell className="text-xs">
            <span className="block text-foreground">{entry.user}</span>
            <span className="text-muted-foreground">{entry.role}</span>
          </TableCell>
          <TableCell className="text-xs">{entry.module}</TableCell>
          <TableCell className="font-mono text-xs">{entry.recordReference}</TableCell>
          <TableCell className="text-xs">{entry.action}</TableCell>
          <TableCell className="text-xs text-muted-foreground">
            {entry.previousStatus || entry.newStatus
              ? `${entry.previousStatus ?? "—"} → ${entry.newStatus ?? "—"}`
              : "—"}
          </TableCell>
          <TableCell className="max-w-xs text-xs text-muted-foreground">{entry.remarks || "—"}</TableCell>
        </TableRow>
      ))}
    </DataTableShell>
  );
}
