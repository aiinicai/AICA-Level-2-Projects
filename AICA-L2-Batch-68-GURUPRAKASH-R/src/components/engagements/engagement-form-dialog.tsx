import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { FormField } from "@/components/common/form-field";
import { FormSection } from "@/components/common/form-section";
import { StatusBadge } from "@/components/common/status-badge";
import type { ClientListItem } from "@/services/client.service";
import {
  AUDIT_AREAS,
  AUDIT_TYPES,
  ENGAGEMENT_STATUS_TONES,
  type EngagementFormValues,
  type EngagementRecord,
} from "@/types/engagement";
import type { ClientId } from "@/types/common";

const EMPTY: EngagementFormValues = {
  clientId: "CLT-0000" as ClientId,
  title: "",
  auditType: "",
  auditArea: "",
  auditPeriodFrom: "",
  auditPeriodTo: "",
  location: "",
  objective: "",
  engagementManager: "",
  auditTeam: [],
  processOwner: "",
  auditCoordinator: "",
  plannedStartDate: "",
  plannedCompletionDate: "",
  reportingDueDate: "",
  remarks: "",
};

function validate(values: EngagementFormValues): Record<string, string> {
  const e: Record<string, string> = {};
  if (!values.clientId || values.clientId === "CLT-0000") e.clientId = "Client is mandatory.";
  if (!values.title.trim()) e.title = "Engagement title is mandatory.";
  if (!values.auditType) e.auditType = "Audit type is mandatory.";
  if (!values.auditArea) e.auditArea = "Audit area is mandatory.";
  if (!values.auditPeriodFrom) e.auditPeriodFrom = "Audit period from is mandatory.";
  if (!values.auditPeriodTo) e.auditPeriodTo = "Audit period to is mandatory.";
  if (!values.engagementManager.trim()) e.engagementManager = "Engagement manager is mandatory.";
  if (!values.processOwner.trim()) e.processOwner = "Process owner is mandatory.";
  if (!values.plannedStartDate) e.plannedStartDate = "Planned start date is mandatory.";
  if (!values.plannedCompletionDate)
    e.plannedCompletionDate = "Planned completion date is mandatory.";
  if (!values.reportingDueDate) e.reportingDueDate = "Reporting due date is mandatory.";

  if (values.auditPeriodFrom && values.auditPeriodTo && values.auditPeriodTo < values.auditPeriodFrom)
    e.auditPeriodTo = "Audit period end cannot be earlier than the start.";
  if (
    values.plannedStartDate &&
    values.plannedCompletionDate &&
    values.plannedCompletionDate < values.plannedStartDate
  )
    e.plannedCompletionDate = "Planned completion cannot be earlier than planned start.";
  if (
    values.plannedStartDate &&
    values.reportingDueDate &&
    values.reportingDueDate < values.plannedStartDate
  )
    e.reportingDueDate = "Reporting due date cannot be earlier than planned start.";
  return e;
}

export interface EngagementFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  engagement?: EngagementRecord | null;
  clients: ClientListItem[];
  defaultClientId?: string;
  pending?: boolean;
  onSubmit: (values: EngagementFormValues) => void;
}

export function EngagementFormDialog({
  open,
  onOpenChange,
  engagement,
  clients,
  defaultClientId,
  pending,
  onSubmit,
}: EngagementFormDialogProps) {
  const isEdit = Boolean(engagement);
  const [values, setValues] = useState<EngagementFormValues>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [teamInput, setTeamInput] = useState("");

  useEffect(() => {
    if (!open) return;
    setErrors({});
    setTeamInput("");
    if (engagement) {
      setValues({
        clientId: engagement.clientId,
        title: engagement.title,
        auditType: engagement.auditType,
        auditArea: engagement.auditArea,
        auditPeriodFrom: engagement.auditPeriodFrom,
        auditPeriodTo: engagement.auditPeriodTo,
        location: engagement.location,
        objective: engagement.objective,
        engagementManager: engagement.engagementManager,
        auditTeam: [...engagement.auditTeam],
        processOwner: engagement.processOwner,
        auditCoordinator: engagement.auditCoordinator,
        plannedStartDate: engagement.plannedStartDate,
        plannedCompletionDate: engagement.plannedCompletionDate,
        reportingDueDate: engagement.reportingDueDate,
        remarks: engagement.remarks,
      });
    } else {
      const client = clients.find((item) => item.id === defaultClientId);
      setValues({
        ...EMPTY,
        clientId: (client?.id ?? EMPTY.clientId) as ClientId,
        auditCoordinator: client?.coordinatorName ?? "",
      });
    }
  }, [open, engagement, defaultClientId, clients]);

  const set = <K extends keyof EngagementFormValues>(key: K, value: EngagementFormValues[K]) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const onClientChange = (clientId: string) => {
    const client = clients.find((item) => item.id === clientId);
    setValues((prev) => ({
      ...prev,
      clientId: clientId as ClientId,
      // Coordinator defaults from the client but stays editable.
      auditCoordinator: prev.auditCoordinator || client?.coordinatorName || "",
    }));
  };

  const addTeamMember = () => {
    const name = teamInput.trim();
    if (!name || values.auditTeam.includes(name)) return;
    set("auditTeam", [...values.auditTeam, name]);
    setTeamInput("");
  };

  const handleSubmit = () => {
    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    onSubmit(values);
  };

  const selectableClients = clients.filter(
    (client) => client.status === "Active" || client.id === values.clientId,
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] gap-0 overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? `Edit engagement ${engagement?.reference}` : "Create engagement"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Status is controlled through workflow actions and cannot be edited here."
              : "The engagement reference is generated automatically as ENG-####. New engagements start as Draft in the Planning stage."}
          </DialogDescription>
        </DialogHeader>

        <div className="-mt-2">
          <FormSection title="Engagement details" description="Identification and audit mandate.">
            <FormField id="reference" label="Engagement reference">
              <Input
                id="reference"
                readOnly
                value={engagement?.reference ?? "Auto-generated (ENG-####)"}
                className="bg-muted font-mono"
              />
            </FormField>
            <FormField id="clientId" label="Client" required error={errors.clientId}>
              <Select value={values.clientId} onValueChange={onClientChange}>
                <SelectTrigger id="clientId">
                  <SelectValue placeholder="Select client" />
                </SelectTrigger>
                <SelectContent>
                  {selectableClients.map((client) => (
                    <SelectItem key={client.id} value={client.id}>
                      {client.clientCode} — {client.legalName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField id="title" label="Engagement title" required error={errors.title} className="sm:col-span-2">
              <Input id="title" value={values.title} onChange={(event) => set("title", event.target.value)} />
            </FormField>
            <FormField id="auditType" label="Audit type" required error={errors.auditType}>
              <Select value={values.auditType} onValueChange={(value) => set("auditType", value)}>
                <SelectTrigger id="auditType">
                  <SelectValue placeholder="Select audit type" />
                </SelectTrigger>
                <SelectContent>
                  {AUDIT_TYPES.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField id="auditArea" label="Audit area" required error={errors.auditArea}>
              <Select value={values.auditArea} onValueChange={(value) => set("auditArea", value)}>
                <SelectTrigger id="auditArea">
                  <SelectValue placeholder="Select audit area" />
                </SelectTrigger>
                <SelectContent>
                  {AUDIT_AREAS.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField id="location" label="Location">
              <Input
                id="location"
                value={values.location}
                onChange={(event) => set("location", event.target.value)}
              />
            </FormField>
            {isEdit && (
              <FormField id="currentStatus" label="Current status">
                <div className="flex h-9 items-center">
                  <StatusBadge
                    status={engagement!.status}
                    tone={ENGAGEMENT_STATUS_TONES[engagement!.status]}
                  />
                </div>
              </FormField>
            )}
            <FormField id="objective" label="Audit objective" className="sm:col-span-2">
              <Textarea
                id="objective"
                rows={3}
                value={values.objective}
                onChange={(event) => set("objective", event.target.value)}
              />
            </FormField>
          </FormSection>

          <FormSection title="Audit period" description="Period of operations under review.">
            <FormField id="auditPeriodFrom" label="Audit period from" required error={errors.auditPeriodFrom}>
              <Input
                id="auditPeriodFrom"
                type="date"
                value={values.auditPeriodFrom}
                onChange={(event) => set("auditPeriodFrom", event.target.value)}
              />
            </FormField>
            <FormField id="auditPeriodTo" label="Audit period to" required error={errors.auditPeriodTo}>
              <Input
                id="auditPeriodTo"
                type="date"
                value={values.auditPeriodTo}
                onChange={(event) => set("auditPeriodTo", event.target.value)}
              />
            </FormField>
          </FormSection>

          <FormSection title="Team and coordination" description="Who performs and supports the audit.">
            <FormField
              id="engagementManager"
              label="Engagement manager"
              required
              error={errors.engagementManager}
            >
              <Input
                id="engagementManager"
                value={values.engagementManager}
                onChange={(event) => set("engagementManager", event.target.value)}
              />
            </FormField>
            <FormField id="processOwner" label="Process owner" required error={errors.processOwner}>
              <Input
                id="processOwner"
                value={values.processOwner}
                onChange={(event) => set("processOwner", event.target.value)}
              />
            </FormField>
            <FormField id="auditCoordinator" label="Audit coordinator" hint="Defaults from the client; editable.">
              <Input
                id="auditCoordinator"
                value={values.auditCoordinator}
                onChange={(event) => set("auditCoordinator", event.target.value)}
              />
            </FormField>
            <FormField id="auditTeam" label="Audit team" hint="Type a name and press Enter to add.">
              <div className="space-y-2">
                <Input
                  id="auditTeam"
                  value={teamInput}
                  onChange={(event) => setTeamInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      addTeamMember();
                    }
                  }}
                  placeholder="Add team member"
                />
                {values.auditTeam.length > 0 && (
                  <ul className="flex flex-wrap gap-1.5">
                    {values.auditTeam.map((member) => (
                      <li
                        key={member}
                        className="inline-flex items-center gap-1 rounded-sm border border-border bg-surface px-2 py-0.5 text-xs"
                      >
                        {member}
                        <button
                          type="button"
                          aria-label={`Remove ${member}`}
                          onClick={() =>
                            set(
                              "auditTeam",
                              values.auditTeam.filter((item) => item !== member),
                            )
                          }
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <X className="size-3" aria-hidden />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </FormField>
          </FormSection>

          <FormSection title="Planning dates" description="Execution and reporting timeline.">
            <FormField id="plannedStartDate" label="Planned start date" required error={errors.plannedStartDate}>
              <Input
                id="plannedStartDate"
                type="date"
                value={values.plannedStartDate}
                onChange={(event) => set("plannedStartDate", event.target.value)}
              />
            </FormField>
            <FormField
              id="plannedCompletionDate"
              label="Planned completion date"
              required
              error={errors.plannedCompletionDate}
            >
              <Input
                id="plannedCompletionDate"
                type="date"
                value={values.plannedCompletionDate}
                onChange={(event) => set("plannedCompletionDate", event.target.value)}
              />
            </FormField>
            <FormField id="reportingDueDate" label="Reporting due date" required error={errors.reportingDueDate}>
              <Input
                id="reportingDueDate"
                type="date"
                value={values.reportingDueDate}
                onChange={(event) => set("reportingDueDate", event.target.value)}
              />
            </FormField>
            <FormField id="remarks" label="Remarks" className="sm:col-span-2">
              <Textarea
                id="remarks"
                rows={3}
                value={values.remarks}
                onChange={(event) => set("remarks", event.target.value)}
              />
            </FormField>
          </FormSection>
        </div>

        <DialogFooter className="border-t border-border pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={pending}>
            {isEdit ? "Save changes" : "Create engagement"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
