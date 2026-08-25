import { useEffect, useMemo, useState } from "react";
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
import { FormField } from "./form-field";

export type PromptValues = Record<string, string>;

export interface PromptOption {
  value: string;
  label: string;
}

export interface PromptField {
  name: string;
  label: string;
  type?: "text" | "textarea" | "date" | "select" | "number";
  required?: boolean;
  hint?: string;
  rows?: number;
  /** Span the full dialog width. */
  full?: boolean;
  readOnly?: boolean;
  minLength?: number;
  placeholder?: string;
  options?: PromptOption[] | ((values: PromptValues) => PromptOption[]);
  /** Field names cleared when this field changes — used for dependent selects. */
  clears?: string[];
  /** Hide the field when the predicate returns false. */
  visible?: (values: PromptValues) => boolean;
}

export interface PromptDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  fields: PromptField[];
  initialValues?: PromptValues;
  submitLabel?: string;
  pending?: boolean;
  wide?: boolean;
  onSubmit: (values: PromptValues) => void;
}

/**
 * One generic, schema-driven dialog used for every Stage 3 create, edit and
 * controlled-action form. Keeps the module code declarative and consistent
 * with the existing FormField styling.
 */
export function PromptDialog({
  open,
  onOpenChange,
  title,
  description,
  fields,
  initialValues,
  submitLabel = "Save",
  pending = false,
  wide = false,
  onSubmit,
}: PromptDialogProps) {
  const [values, setValues] = useState<PromptValues>({});
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (open) {
      const seeded: PromptValues = {};
      for (const field of fields) seeded[field.name] = initialValues?.[field.name] ?? "";
      setValues(seeded);
      setTouched(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const visibleFields = useMemo(
    () => fields.filter((field) => (field.visible ? field.visible(values) : true)),
    [fields, values],
  );

  const errorFor = (field: PromptField): string | undefined => {
    const value = (values[field.name] ?? "").trim();
    if (field.required && !value) return `${field.label} is required.`;
    if (field.minLength && value.length > 0 && value.length < field.minLength) {
      return `Provide at least ${field.minLength} characters.`;
    }
    if (field.minLength && field.required && value.length < field.minLength) {
      return `Provide at least ${field.minLength} characters.`;
    }
    return undefined;
  };

  const invalid = visibleFields.some((field) => Boolean(errorFor(field)));

  const setValue = (field: PromptField, value: string) => {
    setValues((previous) => {
      const next = { ...previous, [field.name]: value };
      for (const name of field.clears ?? []) next[name] = "";
      return next;
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={wide ? "max-h-[85vh] overflow-y-auto sm:max-w-3xl" : "max-h-[85vh] overflow-y-auto sm:max-w-xl"}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        <div className="grid gap-4 sm:grid-cols-2">
          {visibleFields.map((field) => {
            const error = touched ? errorFor(field) : undefined;
            const options =
              typeof field.options === "function" ? field.options(values) : (field.options ?? []);
            return (
              <FormField
                key={field.name}
                id={`prompt-${field.name}`}
                label={field.label}
                required={field.required}
                hint={field.hint}
                error={error}
                className={field.full || field.type === "textarea" ? "sm:col-span-2" : undefined}
              >
                {field.type === "textarea" ? (
                  <Textarea
                    id={`prompt-${field.name}`}
                    rows={field.rows ?? 3}
                    value={values[field.name] ?? ""}
                    readOnly={field.readOnly}
                    placeholder={field.placeholder}
                    onChange={(event) => setValue(field, event.target.value)}
                  />
                ) : field.type === "select" ? (
                  <Select
                    value={values[field.name] || undefined}
                    disabled={field.readOnly || options.length === 0}
                    onValueChange={(value) => setValue(field, value)}
                  >
                    <SelectTrigger id={`prompt-${field.name}`} className="h-9">
                      <SelectValue placeholder={options.length ? "Select…" : "No options available"} />
                    </SelectTrigger>
                    <SelectContent>
                      {options.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    id={`prompt-${field.name}`}
                    type={field.type === "date" ? "date" : field.type === "number" ? "number" : "text"}
                    value={values[field.name] ?? ""}
                    readOnly={field.readOnly}
                    placeholder={field.placeholder}
                    className="h-9"
                    onChange={(event) => setValue(field, event.target.value)}
                  />
                )}
              </FormField>
            );
          })}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={pending}
            onClick={() => {
              setTouched(true);
              if (invalid) return;
              const payload: PromptValues = {};
              for (const field of visibleFields) payload[field.name] = values[field.name] ?? "";
              onSubmit(payload);
            }}
          >
            {submitLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
