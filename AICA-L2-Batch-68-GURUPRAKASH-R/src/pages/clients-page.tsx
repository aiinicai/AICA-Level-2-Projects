import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { DataTableShell } from "@/components/common/data-table-shell";
import { FilterPanel } from "@/components/common/filter-panel";
import { PageHeader } from "@/components/common/page-header";
import { ReasonDialog } from "@/components/common/reason-dialog";
import { SearchBox } from "@/components/common/search-box";
import { StatusBadge } from "@/components/common/status-badge";
import { ClientFormDialog } from "@/components/clients/client-form-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TableCell, TableRow } from "@/components/ui/table";
import { MoreHorizontal } from "lucide-react";
import { ENTITY_TYPES, INDUSTRIES } from "@/data/masters";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDateTime } from "@/lib/format";
import { useCachedState } from "@/lib/list-state";
import {
  canArchiveClient,
  canCreateClient,
  canDeactivateClient,
  canEditClient,
  canReactivateClient,
} from "@/lib/permissions";
import { services } from "@/services";
import type { ClientListItem, ClientListQuery } from "@/services/client.service";
import { CLIENT_STATUSES, CLIENT_STATUS_TONES, type ClientFormValues } from "@/types/client";

const COLUMNS = [
  { key: "code", header: "Client code", width: "110px" },
  { key: "legalName", header: "Legal name" },
  { key: "tradeName", header: "Trade name" },
  { key: "industry", header: "Industry" },
  { key: "entityType", header: "Entity type" },
  { key: "office", header: "Registered office" },
  { key: "coordinator", header: "Coordinator" },
  { key: "email", header: "Email" },
  { key: "mobile", header: "Mobile" },
  { key: "engagements", header: "Active eng.", align: "right" as const },
  { key: "status", header: "Status" },
  { key: "updated", header: "Last updated" },
  { key: "actions", header: "Actions", align: "right" as const },
];

type StatusAction = "deactivate" | "reactivate" | "archive";

export function ClientsPage() {
  const { role } = useRole();
  const actor = useActor();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [search, setSearch] = useCachedState("clients.search", "");
  const [filters, setFilters] = useCachedState<Record<string, string>>("clients.filters", {});
  const [sortBy, setSortBy] = useCachedState<NonNullable<ClientListQuery["sortBy"]>>(
    "clients.sortBy",
    "clientCode",
  );
  const [pageSize, setPageSize] = useCachedState("clients.pageSize", 10);
  const [page, setPage] = useState(1);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ClientListItem | null>(null);
  const [statusAction, setStatusAction] = useState<{ key: StatusAction; client: ClientListItem } | null>(
    null,
  );

  const query: ClientListQuery = {
    search,
    industry: filters.industry,
    entityType: filters.entityType,
    status: filters.status,
    activeOnly: (filters.activeOnly as ClientListQuery["activeOnly"]) ?? "all",
    sortBy,
    page,
    pageSize,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["clients", "list", query],
    queryFn: () => services.clients.list(query),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["clients"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: ClientFormValues) =>
      editing
        ? services.clients.update(editing.id, values, actor)
        : services.clients.create(values, actor),
    onSuccess: (client) => {
      setFormOpen(false);
      setEditing(null);
      invalidate();
      toast.success(`${client.clientCode} saved.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const statusMutation = useMutation({
    mutationFn: ({ key, id, reason }: { key: StatusAction; id: string; reason: string }) => {
      if (key === "deactivate") return services.clients.deactivate(id, reason, actor);
      if (key === "reactivate") return services.clients.reactivate(id, reason, actor);
      return services.clients.archive(id, reason, actor);
    },
    onSuccess: (client) => {
      setStatusAction(null);
      invalidate();
      toast.success(`${client.clientCode} is now ${client.status}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const total = data?.total ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / pageSize));

  const blocking = statusAction?.key === "archive"
    ? services.clients.blockingEngagements(statusAction.client.id)
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Clients"
        description="Client master containing entity details, locations, contacts and the audit coordination team used across all engagements."
        breadcrumbs={[{ label: "AuditFlow", to: "/" }, { label: "Clients" }]}
        actions={
          canCreateClient(role) ? (
            <Button
              size="sm"
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
            >
              <Plus className="size-4" aria-hidden />
              Add client
            </Button>
          ) : (
            <Button size="sm" disabled title="Auditees may only view client records.">
              <Plus className="size-4" aria-hidden />
              Add client
            </Button>
          )
        }
      />

      <FilterPanel
        filters={[
          { key: "industry", label: "Industry", options: INDUSTRIES.map((i) => ({ value: i, label: i })) },
          {
            key: "entityType",
            label: "Entity type",
            options: ENTITY_TYPES.map((i) => ({ value: i, label: i })),
          },
          { key: "status", label: "Status", options: CLIENT_STATUSES.map((i) => ({ value: i, label: i })) },
          {
            key: "activeOnly",
            label: "Active / inactive",
            options: [
              { value: "active", label: "Active only" },
              { value: "inactive", label: "Inactive only" },
            ],
          },
        ]}
        values={filters}
        onChange={(key, value) => {
          setPage(1);
          setFilters({ ...filters, [key]: value });
        }}
        onReset={() => {
          setFilters({});
          setPage(1);
        }}
      />

      <DataTableShell
        columns={COLUMNS}
        caption="Client master"
        isLoading={isLoading}
        error={isError ? "The client register could not be loaded." : null}
        onRetry={() => void refetch()}
        isEmpty={(data?.items.length ?? 0) === 0}
        emptyTitle="No clients match these filters"
        emptyMessage="Adjust the search or filters, or add a new client to the master."
        toolbar={
          <>
            <SearchBox
              value={search}
              onChange={(value) => {
                setSearch(value);
                setPage(1);
              }}
              placeholder="Search code, legal name or trade name…"
            />
            <div className="flex flex-wrap items-center gap-2">
              <Select value={sortBy} onValueChange={(value) => setSortBy(value as typeof sortBy)}>
                <SelectTrigger className="h-9 w-[180px]" aria-label="Sort by">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="clientCode">Sort: Client code</SelectItem>
                  <SelectItem value="legalName">Sort: Legal name</SelectItem>
                  <SelectItem value="status">Sort: Status</SelectItem>
                  <SelectItem value="updatedAt">Sort: Last updated</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={String(pageSize)}
                onValueChange={(value) => {
                  setPageSize(Number(value));
                  setPage(1);
                }}
              >
                <SelectTrigger className="h-9 w-[110px]" aria-label="Rows per page">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[10, 25, 50].map((size) => (
                    <SelectItem key={size} value={String(size)}>
                      {size} / page
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                onClick={() => toast.success("Export queued — file generation arrives with the Google integration.")}
              >
                Export
              </Button>
            </div>
          </>
        }
        footer={`Showing ${data?.items.length ?? 0} of ${total} client(s) — page ${page} of ${lastPage}.`}
      >
        {data?.items.map((client) => (
          <TableRow key={client.id}>
            <TableCell className="font-mono text-xs">
              <Link
                to="/clients/$clientId"
                params={{ clientId: client.id }}
                className="text-primary hover:underline"
              >
                {client.clientCode}
              </Link>
            </TableCell>
            <TableCell className="text-sm font-medium">{client.legalName}</TableCell>
            <TableCell className="text-sm">{client.tradeName || "—"}</TableCell>
            <TableCell className="text-sm">{client.industry}</TableCell>
            <TableCell className="text-sm">{client.entityType}</TableCell>
            <TableCell className="max-w-[200px] truncate text-sm">{client.registeredOffice || "—"}</TableCell>
            <TableCell className="text-sm">{client.coordinatorName}</TableCell>
            <TableCell className="text-sm">{client.coordinatorEmail || "—"}</TableCell>
            <TableCell className="text-sm whitespace-nowrap">{client.coordinatorMobile || "—"}</TableCell>
            <TableCell className="text-right text-sm tabular-nums">{client.activeEngagements}</TableCell>
            <TableCell>
              <StatusBadge status={client.status} tone={CLIENT_STATUS_TONES[client.status]} />
            </TableCell>
            <TableCell className="text-xs whitespace-nowrap text-muted-foreground">
              {formatDateTime(client.updatedAt)}
            </TableCell>
            <TableCell className="text-right">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="size-8 p-0" aria-label={`Actions for ${client.clientCode}`}>
                    <MoreHorizontal className="size-4" aria-hidden />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onSelect={() => void navigate({ to: "/clients/$clientId", params: { clientId: client.id } })}
                  >
                    View
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={!canEditClient(role)}
                    onSelect={() => {
                      setEditing(client);
                      setFormOpen(true);
                    }}
                  >
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={!canDeactivateClient(role) || client.status !== "Active"}
                    onSelect={() => setStatusAction({ key: "deactivate", client })}
                  >
                    Deactivate
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={!canReactivateClient(role) || client.status !== "Inactive"}
                    title={canReactivateClient(role) ? undefined : "Audit Manager only."}
                    onSelect={() => setStatusAction({ key: "reactivate", client })}
                  >
                    Reactivate
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={!canArchiveClient(role) || client.status === "Archived"}
                    title={canArchiveClient(role) ? undefined : "Audit Manager only."}
                    onSelect={() => setStatusAction({ key: "archive", client })}
                  >
                    Archive
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        ))}
      </DataTableShell>

      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= lastPage}
          onClick={() => setPage(page + 1)}
        >
          Next
        </Button>
      </div>

      <ClientFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        client={editing}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />

      <ReasonDialog
        open={statusAction !== null}
        onOpenChange={(open) => !open && setStatusAction(null)}
        title={
          statusAction
            ? `${statusAction.key === "deactivate" ? "Deactivate" : statusAction.key === "reactivate" ? "Reactivate" : "Archive"} ${statusAction.client.clientCode}`
            : ""
        }
        description={
          statusAction?.key === "archive" && blocking.length > 0
            ? `This client has ${blocking.length} live engagement(s): ${blocking.map((item) => `${item.reference} (${item.status})`).join(", ")}. Archiving is blocked until they are closed or cancelled.`
            : "The record is preserved; only its status changes. This action is written to the activity log."
        }
        destructive={statusAction?.key !== "reactivate"}
        confirmLabel="Confirm"
        pending={statusMutation.isPending || (statusAction?.key === "archive" && blocking.length > 0)}
        onConfirm={(reason) =>
          statusAction &&
          statusMutation.mutate({ key: statusAction.key, id: statusAction.client.id, reason })
        }
      />
    </div>
  );
}
