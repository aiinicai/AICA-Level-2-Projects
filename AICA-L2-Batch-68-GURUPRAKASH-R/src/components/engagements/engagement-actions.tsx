import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
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
import { Label } from "@/components/ui/label";
import { MoreHorizontal } from "lucide-react";
import { ReasonDialog } from "@/components/common/reason-dialog";
import { useActor } from "@/hooks/use-actor";
import { useRole } from "@/context/role-context";
import {
  advanceBlockedReason,
  canAdvanceEngagement,
  canCancelEngagement,
  canCloseEngagement,
  canCorrectStatus,
  canHoldEngagement,
  canReopenEngagement,
  canResumeEngagement,
} from "@/lib/permissions";
import { services } from "@/services";
import {
  CANCELLABLE_STATUSES,
  CORRECTABLE_STATUSES,
  HOLDABLE_STATUSES,
  nextStatus,
  type EngagementRecord,
  type EngagementStatus,
} from "@/types/engagement";

type ActionKey = "hold" | "resume" | "cancel" | "close" | "reopen" | "correct";



export interface EngagementActionsProps {
  engagement: EngagementRecord;
  variant?: "buttons" | "menu";
  onEdit?: () => void;
  onView?: () => void;
}

/**
 * Controlled workflow transitions. Every action is gated by role and current
 * status, requires confirmation with a reason, and writes to the activity log.
 */
export function EngagementActions({
  engagement,
  variant = "buttons",
  onEdit,
  onView,
}: EngagementActionsProps) {
  const { role } = useRole();
  const actor = useActor();
  const queryClient = useQueryClient();
  const [action, setAction] = useState<ActionKey | null>(null);
  const [correctTarget, setCorrectTarget] = useState<EngagementStatus>(
    engagement.status === "Planned" ? "Draft" : "Planned",
  );

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["engagements"] });
    void queryClient.invalidateQueries({ queryKey: ["clients"] });
    void queryClient.invalidateQueries({ queryKey: ["activity"] });
  };

  const mutation = useMutation({
    mutationFn: async ({ key, reason }: { key: ActionKey | "advance"; reason: string }) => {
      const id = engagement.id;
      switch (key) {
        case "advance":
          return services.engagements.advanceStatus(id, actor, reason);
        case "hold":
          return services.engagements.placeOnHold(id, reason, actor);
        case "resume":
          return services.engagements.resume(id, reason, actor);
        case "cancel":
          return services.engagements.cancel(id, reason, actor);
        case "close":
          return services.engagements.close(id, reason, actor);
        case "reopen":
          return services.engagements.reopen(id, reason, actor);
        case "correct":
          return services.engagements.correctStatus(id, correctTarget, reason, actor);
      }
    },
    onSuccess: (record) => {
      setAction(null);
      invalidate();
      toast.success(`${engagement.reference} is now ${record?.status}.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const target = nextStatus(engagement.status);
  const advanceAllowed = canAdvanceEngagement(role, engagement.status);
  const advanceReason = advanceBlockedReason(role, engagement.status);

  type ActionItem = {
    key: ActionKey | "advance";
    label: string;
    show: boolean;
    disabled?: boolean;
    title?: string;
  };

  const items: ActionItem[] = ([
    {
      key: "advance",
      label: target ? `Advance to ${target}` : "Advance status",
      show:
        Boolean(target) &&
        engagement.status !== "Cancelled" &&
        engagement.status !== "On Hold" &&
        engagement.status !== "Closed",
      disabled: !advanceAllowed,
      title: advanceReason ?? undefined,
    },
    {
      key: "hold",
      label: "Place on hold",
      show: HOLDABLE_STATUSES.includes(engagement.status),
      disabled: !canHoldEngagement(role),
      title: canHoldEngagement(role) ? undefined : "Audit Manager only.",
    },
    {
      key: "resume",
      label: "Resume",
      show: engagement.status === "On Hold",
      disabled: !canResumeEngagement(role),
      title: canResumeEngagement(role) ? undefined : "Audit Manager only.",
    },
    {
      key: "close",
      label: "Close engagement",
      show: engagement.status === "Action Tracking",
      disabled: !canCloseEngagement(role),
      title: canCloseEngagement(role) ? undefined : "Audit Manager only.",
    },
    {
      key: "reopen",
      label: "Reopen engagement",
      show: engagement.status === "Closed",
      disabled: !canReopenEngagement(role),
      title: canReopenEngagement(role) ? undefined : "Audit Manager only.",
    },
    {
      key: "cancel",
      label: "Cancel engagement",
      show: CANCELLABLE_STATUSES.includes(engagement.status),
      disabled: !canCancelEngagement(role),
      title: canCancelEngagement(role) ? undefined : "Audit Manager only.",
    },
    {
      key: "correct",
      label: "Correct status",
      show: canCorrectStatus(role),
    },
  ] as ActionItem[]).filter((item) => item.show);

  const run = (key: ActionKey | "advance") => {
    if (key === "advance") {
      mutation.mutate({ key: "advance", reason: "" });
      return;
    }
    setAction(key);
  };

  const dialogs = (
    <>
      <ReasonDialog
        open={action === "hold"}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Place ${engagement.reference} on hold`}
        description={`The current status (${engagement.status}) and lifecycle stage are stored so the engagement can be resumed later.`}
        pending={mutation.isPending}
        onConfirm={(reason) => mutation.mutate({ key: "hold", reason })}
      />
      <ReasonDialog
        open={action === "resume"}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Resume ${engagement.reference}`}
        description={`The engagement will return to ${engagement.priorStatus ?? "Planned"}.`}
        confirmLabel="Resume"
        pending={mutation.isPending}
        onConfirm={(reason) => mutation.mutate({ key: "resume", reason })}
      />
      <ReasonDialog
        open={action === "cancel"}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Cancel ${engagement.reference}`}
        description="The record is preserved. No further normal workflow transition will be available."
        confirmLabel="Cancel engagement"
        destructive
        pending={mutation.isPending}
        onConfirm={(reason) => mutation.mutate({ key: "cancel", reason })}
      />
      <ReasonDialog
        open={action === "close"}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Close ${engagement.reference}`}
        reasonLabel="Closure remarks"
        confirmLabel="Close engagement"
        pending={mutation.isPending}
        onConfirm={(reason) => mutation.mutate({ key: "close", reason })}
      />
      <ReasonDialog
        open={action === "reopen"}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Reopen ${engagement.reference}`}
        description="The engagement returns to Action Tracking."
        confirmLabel="Reopen"
        pending={mutation.isPending}
        onConfirm={(reason) => mutation.mutate({ key: "reopen", reason })}
      />
      <ReasonDialog
        open={action === "correct"}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Correct status of ${engagement.reference}`}
        description="Use only to fix an incorrectly recorded status. Both the previous and new status are logged."
        confirmLabel="Correct status"
        pending={mutation.isPending}
        onConfirm={(reason) => mutation.mutate({ key: "correct", reason })}
        extra={
          <div className="space-y-1.5">
            <Label htmlFor="correct-status" className="text-xs text-muted-foreground">
              Corrected status
            </Label>
            <Select
              value={correctTarget}
              onValueChange={(value) => setCorrectTarget(value as EngagementStatus)}
            >
              <SelectTrigger id="correct-status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CORRECTABLE_STATUSES.filter((status) => status !== engagement.status).map((status) => (
                  <SelectItem key={status} value={status}>
                    {status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        }
      />
    </>
  );

  if (variant === "menu") {
    return (
      <>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="size-8 p-0" aria-label="Engagement actions">
              <MoreHorizontal className="size-4" aria-hidden />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {onView && <DropdownMenuItem onSelect={onView}>View</DropdownMenuItem>}
            {onEdit && <DropdownMenuItem onSelect={onEdit}>Edit</DropdownMenuItem>}
            {items.map((item) => (
              <DropdownMenuItem
                key={item.key}
                disabled={item.disabled}
                title={item.title}
                onSelect={(event) => {
                  event.preventDefault();
                  run(item.key);
                }}
              >
                {item.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        {dialogs}
      </>
    );
  }

  return (
    <div className="w-full max-w-md sm:w-auto">
      <div className="flex flex-wrap items-center gap-2 sm:justify-end">
        {onEdit && (
          <Button variant="outline" size="sm" onClick={onEdit}>
            Edit
          </Button>
        )}
        {items.map((item) => (
          <Button
            key={item.key}
            size="sm"
            variant={item.key === "advance" ? "default" : "outline"}
            disabled={item.disabled || mutation.isPending}
            title={item.title}
            onClick={() => run(item.key)}
          >
            {item.label}
          </Button>
        ))}
      </div>
      {items.some((item) => item.disabled && item.title) && (
        <p className="mt-2 text-xs text-muted-foreground sm:text-right">
          Some actions are unavailable for the selected role or current status.
        </p>
      )}
      {dialogs}
    </div>
  );
}
