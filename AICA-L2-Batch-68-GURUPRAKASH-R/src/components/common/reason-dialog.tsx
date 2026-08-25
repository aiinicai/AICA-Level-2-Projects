import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export interface ReasonDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  reasonLabel?: string;
  confirmLabel?: string;
  destructive?: boolean;
  pending?: boolean;
  /** Optional extra controls rendered above the reason field. */
  extra?: ReactNode;
  onConfirm: (reason: string) => void;
}


/**
 * Confirmation dialog with a mandatory reason. Used for every consequential
 * client and engagement action so the activity log always carries a remark.
 */
export function ReasonDialog({
  open,
  onOpenChange,
  title,
  description,
  reasonLabel = "Reason",
  confirmLabel = "Confirm",
  destructive = false,
  pending = false,
  extra,
  onConfirm,

}: ReasonDialogProps) {
  const [reason, setReason] = useState("");
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (open) {
      setReason("");
      setTouched(false);
    }
  }, [open]);

  const invalid = reason.trim().length < 5;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        {extra && <div className="mb-3">{extra}</div>}
        <div className="space-y-2">

          <Label htmlFor="reason-input">
            {reasonLabel} <span className="text-destructive">*</span>
          </Label>
          <Textarea
            id="reason-input"
            rows={4}
            value={reason}
            maxLength={500}
            onChange={(event) => setReason(event.target.value)}
            onBlur={() => setTouched(true)}
            placeholder="Record the justification for this action…"
          />
          {touched && invalid && (
            <p className="text-xs text-destructive">
              Please provide at least 5 characters — this is recorded in the activity log.
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            disabled={invalid || pending}
            onClick={() => onConfirm(reason.trim())}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
