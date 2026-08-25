import { useState } from "react";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ActivityTable } from "@/components/common/activity-table";
import { DataTableShell } from "@/components/common/data-table-shell";
import { DetailCard, DetailField } from "@/components/common/detail-card";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading-state";
import { PageHeader } from "@/components/common/page-header";
import { ReasonDialog } from "@/components/common/reason-dialog";
import { StatusBadge } from "@/components/common/status-badge";
import { ClientFormDialog } from "@/components/clients/client-form-dialog";
import { EngagementFormDialog } from "@/components/engagements/engagement-form-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TableCell, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FormField } from "@/components/common/form-field";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import { formatDate, formatDateTime } from "@/lib/format";
import {
  canArchiveClient,
  canCreateEngagement,
  canDeactivateClient,
  canEditClient,
  canReactivateClient,
} from "@/lib/permissions";
import { services } from "@/services";
import { CLIENT_STATUS_TONES } from "@/types/client";
import type { ClientFormValues } from "@/types/client";
import { ENGAGEMENT_STATUS_TONES, resolveStage, type EngagementFormValues } from "@/types/engagement";

type StatusAction = "deactivate" | "reactivate" | "archive";

export function ClientDetailPage() {
  const { clientId } = useParams({ from: "/clients/$clientId" });
  const { role } = useRole();
  const actor = useActor();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [formOpen, setFormOpen] = useState(false);
  const [engagementFormOpen, setEngagementFormOpen] = useState(false);
  const [statusAction, setStatusAction] = useState<StatusAction | null>(null);
  const [contact, setContact] = useState({
    name: "",
    designation: "",
    department: "",
    email: "",
    mobile: "",
  });
  const [location, setLocation] = useState({
    locationCode: "",
    locationName: "",
    address: "",
    city: "",
    state: "",
    contactPerson: "",
  });

  const clientQuery = useQuery({
    queryKey: ["clients", "detail", clientId],
    queryFn: () => services.clients.getById(clientId),
  });
  const engagementsQuery = useQuery({
    queryKey: ["engagements", "by-client", clientId],
    queryFn: () => services.engagements.getByClientId(clientId),
  });
  const activityQuery = useQuery({
    queryKey: ["activity", "client", clientId],
    queryFn: () => services.activity.getByClientId(clientId),
  });
  const allClientsQuery = useQuery({
    queryKey: ["clients", "options"],
    queryFn: () => services.clients.list({ pageSize: 500 }),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["clients"] });
    void queryClient.invalidateQueries({ queryKey: ["engagements"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: ClientFormValues) => services.clients.update(clientId, values, actor),
    onSuccess: () => {
      setFormOpen(false);
      invalidate();
      toast.success("Client updated.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const statusMutation = useMutation({
    mutationFn: ({ key, reason }: { key: StatusAction; reason: string }) => {
      if (key === "deactivate") return services.clients.deactivate(clientId, reason, actor);
      if (key === "reactivate") return services.clients.reactivate(clientId, reason, actor);
      return services.clients.archive(clientId, reason, actor);
    },
    onSuccess: (record) => {
      setStatusAction(null);
      invalidate();
      toast.success(`${record.clientCode} is now ${record.status}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const contactMutation = useMutation({
    mutationFn: () =>
      services.clients.addContact(
        clientId,
        { ...contact, contactType: "Other", isActive: true },
        actor,
      ),
    onSuccess: () => {
      setContact({ name: "", designation: "", department: "", email: "", mobile: "" });
      invalidate();
      toast.success("Secondary contact added.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const locationMutation = useMutation({
    mutationFn: () => services.clients.addLocation(clientId, { ...location, status: "Active" }, actor),
    onSuccess: () => {
      setLocation({ locationCode: "", locationName: "", address: "", city: "", state: "", contactPerson: "" });
      invalidate();
      toast.success("Location added.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const engagementMutation = useMutation({
    mutationFn: (values: EngagementFormValues) => services.engagements.create(values, actor),
    onSuccess: (record) => {
      setEngagementFormOpen(false);
      invalidate();
      toast.success(`${record.reference} created as Draft.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  if (clientQuery.isLoading) return <LoadingState label="Loading client…" />;
  if (clientQuery.isError) return <ErrorState onRetry={() => void clientQuery.refetch()} />;

  const client = clientQuery.data;
  if (!client) {
    return (
      <EmptyState
        title="Client not found"
        message="This client record does not exist. It may have been removed from the mock data set."
        action={
          <Button variant="outline" size="sm" onClick={() => void navigate({ to: "/clients" })}>
            Back to clients
          </Button>
        }
      />
    );
  }

  const engagements = engagementsQuery.data ?? [];
  const blocking = services.clients.blockingEngagements(clientId);

  return (
    <div className="space-y-6">
      <PageHeader
        title={client.legalName}
        description={`${client.clientCode} · ${client.industry} · ${client.entityType}`}
        breadcrumbs={[
          { label: "AuditFlow", to: "/" },
          { label: "Clients", to: "/clients" },
          { label: client.clientCode },
        ]}
        meta={<StatusBadge status={client.status} tone={CLIENT_STATUS_TONES[client.status]} />}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              disabled={!canEditClient(role)}
              title={canEditClient(role) ? undefined : "Auditees may only view client records."}
              onClick={() => setFormOpen(true)}
            >
              Edit
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!canDeactivateClient(role) || client.status !== "Active"}
              onClick={() => setStatusAction("deactivate")}
            >
              Deactivate
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!canReactivateClient(role) || client.status !== "Inactive"}
              title={canReactivateClient(role) ? undefined : "Audit Manager only."}
              onClick={() => setStatusAction("reactivate")}
            >
              Reactivate
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!canArchiveClient(role) || client.status === "Archived" || blocking.length > 0}
              title={
                !canArchiveClient(role)
                  ? "Audit Manager only."
                  : blocking.length > 0
                    ? `Blocked: ${blocking.length} live engagement(s).`
                    : undefined
              }
              onClick={() => setStatusAction("archive")}
            >
              Archive
            </Button>
          </>
        }
      />

      <Tabs defaultValue="overview">
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="contacts">Contacts</TabsTrigger>
          <TabsTrigger value="locations">Locations</TabsTrigger>
          <TabsTrigger value="engagements">Engagements</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 space-y-4">
          <div className="grid gap-4 lg:grid-cols-3">
            <DetailCard title="Entity details" className="lg:col-span-2">
              <dl className="grid gap-4 sm:grid-cols-3">
                <DetailField label="Client code" value={<span className="font-mono">{client.clientCode}</span>} />
                <DetailField label="Legal name" value={client.legalName} />
                <DetailField label="Trade name" value={client.tradeName || "—"} />
                <DetailField label="Industry" value={client.industry} />
                <DetailField label="Entity type" value={client.entityType} />
                <DetailField label="Financial year ending" value={client.financialYearEnding} />
                <DetailField label="Registered office" value={client.registeredOffice || "—"} />
                <DetailField label="Corporate office" value={client.corporateOffice || "—"} />
                <DetailField
                  label="City / state"
                  value={[client.city, client.state, client.pinCode].filter(Boolean).join(", ") || "—"}
                />
                <DetailField label="PAN" value={client.pan || "—"} />
                <DetailField label="GSTIN" value={client.gstin || "—"} />
                <DetailField label="Country" value={client.country || "—"} />
              </dl>
            </DetailCard>

            <div className="space-y-4">
              <DetailCard title="Engagement summary">
                <dl className="grid gap-4 sm:grid-cols-2">
                  <DetailField label="Total engagements" value={client.totalEngagements} />
                  <DetailField label="Active engagements" value={client.activeEngagements} />
                  <DetailField
                    label="Latest engagement status"
                    value={
                      client.latestEngagementStatus ? (
                        <StatusBadge
                          status={client.latestEngagementStatus}
                          tone={ENGAGEMENT_STATUS_TONES[client.latestEngagementStatus]}
                        />
                      ) : (
                        "—"
                      )
                    }
                  />
                </dl>
              </DetailCard>
              <DetailCard title="Record metadata">
                <dl className="grid gap-4 sm:grid-cols-2">
                  <DetailField label="Created" value={`${formatDateTime(client.createdAt)} · ${client.createdBy}`} />
                  <DetailField
                    label="Last updated"
                    value={`${formatDateTime(client.updatedAt)} · ${client.updatedBy}`}
                  />
                  <DetailField label="Active flag" value={client.isActive ? "Yes" : "No"} />
                </dl>
              </DetailCard>
            </div>
          </div>
          {client.remarks && (
            <DetailCard title="Remarks">
              <p className="text-sm text-foreground">{client.remarks}</p>
            </DetailCard>
          )}
        </TabsContent>

        <TabsContent value="contacts" className="mt-4 space-y-4">
          <DetailCard title="Primary audit coordinator">
            <dl className="grid gap-4 sm:grid-cols-4">
              <DetailField label="Name" value={client.coordinatorName} />
              <DetailField label="Designation" value={client.coordinatorDesignation || "—"} />
              <DetailField label="Email" value={client.coordinatorEmail || "—"} />
              <DetailField label="Mobile" value={client.coordinatorMobile || "—"} />
            </dl>
          </DetailCard>

          <DataTableShell
            columns={[
              { key: "name", header: "Name" },
              { key: "designation", header: "Designation" },
              { key: "department", header: "Department" },
              { key: "email", header: "Email" },
              { key: "mobile", header: "Mobile" },
              { key: "type", header: "Contact type" },
              { key: "status", header: "Active" },
            ]}
            caption="Secondary contacts"
            isEmpty={client.contacts.length === 0}
            emptyTitle="No secondary contacts"
            emptyMessage="Add departmental contacts who support the audit."
          >
            {client.contacts.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="text-sm">{row.name}</TableCell>
                <TableCell className="text-sm">{row.designation || "—"}</TableCell>
                <TableCell className="text-sm">{row.department || "—"}</TableCell>
                <TableCell className="text-sm">{row.email || "—"}</TableCell>
                <TableCell className="text-sm">{row.mobile || "—"}</TableCell>
                <TableCell className="text-sm">{row.contactType}</TableCell>
                <TableCell className="text-sm">{row.isActive ? "Yes" : "No"}</TableCell>
              </TableRow>
            ))}
          </DataTableShell>

          {canEditClient(role) && (
            <DetailCard title="Add secondary contact">
              <div className="grid gap-3 sm:grid-cols-5">
                <FormField id="c-name" label="Name">
                  <Input id="c-name" value={contact.name} onChange={(e) => setContact({ ...contact, name: e.target.value })} />
                </FormField>
                <FormField id="c-desig" label="Designation">
                  <Input id="c-desig" value={contact.designation} onChange={(e) => setContact({ ...contact, designation: e.target.value })} />
                </FormField>
                <FormField id="c-dept" label="Department">
                  <Input id="c-dept" value={contact.department} onChange={(e) => setContact({ ...contact, department: e.target.value })} />
                </FormField>
                <FormField id="c-email" label="Email">
                  <Input id="c-email" type="email" value={contact.email} onChange={(e) => setContact({ ...contact, email: e.target.value })} />
                </FormField>
                <FormField id="c-mobile" label="Mobile">
                  <Input id="c-mobile" value={contact.mobile} onChange={(e) => setContact({ ...contact, mobile: e.target.value })} />
                </FormField>
              </div>
              <div className="mt-3">
                <Button size="sm" disabled={!contact.name.trim() || contactMutation.isPending} onClick={() => contactMutation.mutate()}>
                  Add contact
                </Button>
              </div>
            </DetailCard>
          )}
        </TabsContent>

        <TabsContent value="locations" className="mt-4 space-y-4">
          <DataTableShell
            columns={[
              { key: "code", header: "Location code" },
              { key: "name", header: "Location name" },
              { key: "address", header: "Address" },
              { key: "city", header: "City" },
              { key: "state", header: "State" },
              { key: "person", header: "Contact person" },
              { key: "status", header: "Status" },
            ]}
            caption="Client locations"
            isEmpty={client.locations.length === 0}
            emptyTitle="No locations recorded"
            emptyMessage="Add the plants, offices or depots covered by audit work."
          >
            {client.locations.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="font-mono text-xs">{row.locationCode}</TableCell>
                <TableCell className="text-sm">{row.locationName}</TableCell>
                <TableCell className="text-sm">{row.address || "—"}</TableCell>
                <TableCell className="text-sm">{row.city || "—"}</TableCell>
                <TableCell className="text-sm">{row.state || "—"}</TableCell>
                <TableCell className="text-sm">{row.contactPerson || "—"}</TableCell>
                <TableCell>
                  <StatusBadge status={row.status} tone={row.status === "Active" ? "success" : "warning"} />
                </TableCell>
              </TableRow>
            ))}
          </DataTableShell>

          {canEditClient(role) && (
            <DetailCard title="Add location">
              <div className="grid gap-3 sm:grid-cols-3">
                <FormField id="l-code" label="Location code">
                  <Input id="l-code" value={location.locationCode} onChange={(e) => setLocation({ ...location, locationCode: e.target.value })} />
                </FormField>
                <FormField id="l-name" label="Location name">
                  <Input id="l-name" value={location.locationName} onChange={(e) => setLocation({ ...location, locationName: e.target.value })} />
                </FormField>
                <FormField id="l-address" label="Address">
                  <Input id="l-address" value={location.address} onChange={(e) => setLocation({ ...location, address: e.target.value })} />
                </FormField>
                <FormField id="l-city" label="City">
                  <Input id="l-city" value={location.city} onChange={(e) => setLocation({ ...location, city: e.target.value })} />
                </FormField>
                <FormField id="l-state" label="State">
                  <Input id="l-state" value={location.state} onChange={(e) => setLocation({ ...location, state: e.target.value })} />
                </FormField>
                <FormField id="l-person" label="Contact person">
                  <Input id="l-person" value={location.contactPerson} onChange={(e) => setLocation({ ...location, contactPerson: e.target.value })} />
                </FormField>
              </div>
              <div className="mt-3">
                <Button
                  size="sm"
                  disabled={!location.locationName.trim() || locationMutation.isPending}
                  onClick={() => locationMutation.mutate()}
                >
                  Add location
                </Button>
              </div>
            </DetailCard>
          )}
        </TabsContent>

        <TabsContent value="engagements" className="mt-4 space-y-3">
          <div className="flex justify-end">
            <Button
              size="sm"
              disabled={!canCreateEngagement(role)}
              title={canCreateEngagement(role) ? undefined : "Auditees may only view engagement records."}
              onClick={() => setEngagementFormOpen(true)}
            >
              Create engagement
            </Button>
          </div>
          <DataTableShell
            columns={[
              { key: "ref", header: "Reference" },
              { key: "title", header: "Title" },
              { key: "type", header: "Audit type" },
              { key: "period", header: "Audit period" },
              { key: "stage", header: "Stage" },
              { key: "status", header: "Status" },
              { key: "updated", header: "Last updated" },
            ]}
            caption="Engagements for this client"
            isLoading={engagementsQuery.isLoading}
            isEmpty={engagements.length === 0}
            emptyTitle="No engagements yet"
            emptyMessage="Create an engagement to begin planning audit work for this client."
          >
            {engagements.map((engagement) => (
              <TableRow key={engagement.id}>
                <TableCell className="font-mono text-xs">
                  <Link
                    to="/engagements/$engagementId"
                    params={{ engagementId: engagement.id }}
                    className="text-primary hover:underline"
                  >
                    {engagement.reference}
                  </Link>
                </TableCell>
                <TableCell className="text-sm">{engagement.title}</TableCell>
                <TableCell className="text-sm">{engagement.auditType}</TableCell>
                <TableCell className="text-xs whitespace-nowrap">
                  {formatDate(engagement.auditPeriodFrom)} – {formatDate(engagement.auditPeriodTo)}
                </TableCell>
                <TableCell className="text-sm">
                  {resolveStage(engagement.status, engagement.lifecycleStage)}
                </TableCell>
                <TableCell>
                  <StatusBadge
                    status={engagement.status}
                    tone={ENGAGEMENT_STATUS_TONES[engagement.status]}
                  />
                </TableCell>
                <TableCell className="text-xs whitespace-nowrap text-muted-foreground">
                  {formatDateTime(engagement.updatedAt)}
                </TableCell>
              </TableRow>
            ))}
          </DataTableShell>
        </TabsContent>

        <TabsContent value="documents" className="mt-4">
          <EmptyState
            title="Documents"
            message="Client-level document management will be implemented in a later stage."
          />
        </TabsContent>

        <TabsContent value="activity" className="mt-4">
          <ActivityTable
            entries={activityQuery.data ?? []}
            isLoading={activityQuery.isLoading}
            emptyMessage="No client activity has been recorded yet."
          />
        </TabsContent>
      </Tabs>

      <ClientFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        client={client}
        pending={saveMutation.isPending}
        onSubmit={(values) => saveMutation.mutate(values)}
      />

      <EngagementFormDialog
        open={engagementFormOpen}
        onOpenChange={setEngagementFormOpen}
        clients={allClientsQuery.data?.items ?? []}
        defaultClientId={clientId}
        pending={engagementMutation.isPending}
        onSubmit={(values) => engagementMutation.mutate(values)}
      />

      <ReasonDialog
        open={statusAction !== null}
        onOpenChange={(open) => !open && setStatusAction(null)}
        title={statusAction ? `${statusAction[0].toUpperCase()}${statusAction.slice(1)} ${client.clientCode}` : ""}
        description="The record is preserved; only its status changes. This action is written to the activity log."
        destructive={statusAction !== "reactivate"}
        pending={statusMutation.isPending}
        onConfirm={(reason) => statusAction && statusMutation.mutate({ key: statusAction, reason })}
      />
    </div>
  );
}
