import { useEffect, useState } from "react";
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
import {
  EMAIL_PATTERN,
  ENTITY_TYPES,
  FINANCIAL_YEAR_ENDINGS,
  GSTIN_PATTERN,
  INDIAN_STATES,
  INDUSTRIES,
  MOBILE_PATTERN,
  PAN_PATTERN,
} from "@/data/masters";
import { StatusBadge } from "@/components/common/status-badge";
import { CLIENT_STATUS_TONES, type ClientFormValues, type ClientRecord } from "@/types/client";

const EMPTY: ClientFormValues = {
  legalName: "",
  tradeName: "",
  industry: "",
  entityType: "",
  registeredOffice: "",
  corporateOffice: "",
  city: "",
  state: "",
  country: "India",
  pinCode: "",
  coordinatorName: "",
  coordinatorDesignation: "",
  coordinatorEmail: "",
  coordinatorMobile: "",
  financialYearEnding: "31 March",
  pan: "",
  gstin: "",
  remarks: "",
  status: "Active",
};

function validate(values: ClientFormValues): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!values.legalName.trim()) errors.legalName = "Legal name is mandatory.";
  if (!values.industry) errors.industry = "Industry is mandatory.";
  if (!values.entityType) errors.entityType = "Entity type is mandatory.";
  if (!values.coordinatorName.trim())
    errors.coordinatorName = "Primary audit coordinator is mandatory.";
  if (values.coordinatorEmail && !EMAIL_PATTERN.test(values.coordinatorEmail.trim()))
    errors.coordinatorEmail = "Enter a valid email address.";
  if (values.coordinatorMobile && !MOBILE_PATTERN.test(values.coordinatorMobile.trim()))
    errors.coordinatorMobile = "Enter a valid Indian or international mobile number.";
  if (values.pan && !PAN_PATTERN.test(values.pan.trim().toUpperCase()))
    errors.pan = "PAN must be in the format AAAAA9999A.";
  if (values.gstin && !GSTIN_PATTERN.test(values.gstin.trim().toUpperCase()))
    errors.gstin = "GSTIN must be a valid 15-character identifier.";
  return errors;
}

export interface ClientFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  client?: ClientRecord | null;
  pending?: boolean;
  onSubmit: (values: ClientFormValues) => void;
}

export function ClientFormDialog({
  open,
  onOpenChange,
  client,
  pending,
  onSubmit,
}: ClientFormDialogProps) {
  const isEdit = Boolean(client);
  const [values, setValues] = useState<ClientFormValues>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) return;
    setErrors({});
    if (client) {
      const { id: _id, clientCode: _code, contacts: _c, locations: _l, createdAt, createdBy, updatedAt, updatedBy, isActive, ...rest } = client;
      void createdAt;
      void createdBy;
      void updatedAt;
      void updatedBy;
      void isActive;
      setValues(rest as ClientFormValues);
    } else {
      setValues(EMPTY);
    }
  }, [open, client]);

  const set = <K extends keyof ClientFormValues>(key: K, value: ClientFormValues[K]) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = () => {
    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    onSubmit({
      ...values,
      pan: values.pan.trim().toUpperCase(),
      gstin: values.gstin.trim().toUpperCase(),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] gap-0 overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? `Edit client ${client?.clientCode}` : "Add client"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Amend the client master record. The client code cannot be changed."
              : "The client code is generated automatically in CLT-#### format on save."}
          </DialogDescription>
        </DialogHeader>

        <div className="-mt-2">
          <FormSection title="Basic details" description="Identity of the audited entity.">
            <FormField id="clientCode" label="Client code">
              <Input
                id="clientCode"
                readOnly
                value={client?.clientCode ?? "Auto-generated (CLT-####)"}
                className="bg-muted font-mono"
              />
            </FormField>
            <FormField id="legalName" label="Legal name" required error={errors.legalName}>
              <Input
                id="legalName"
                value={values.legalName}
                onChange={(event) => set("legalName", event.target.value)}
              />
            </FormField>
            <FormField id="tradeName" label="Trade name">
              <Input
                id="tradeName"
                value={values.tradeName}
                onChange={(event) => set("tradeName", event.target.value)}
              />
            </FormField>
            <FormField id="industry" label="Industry" required error={errors.industry}>
              <Select value={values.industry} onValueChange={(value) => set("industry", value)}>
                <SelectTrigger id="industry">
                  <SelectValue placeholder="Select industry" />
                </SelectTrigger>
                <SelectContent>
                  {INDUSTRIES.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField id="entityType" label="Entity type" required error={errors.entityType}>
              <Select value={values.entityType} onValueChange={(value) => set("entityType", value)}>
                <SelectTrigger id="entityType">
                  <SelectValue placeholder="Select entity type" />
                </SelectTrigger>
                <SelectContent>
                  {ENTITY_TYPES.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField
              id="status"
              label="Client status"
              hint={
                isEdit
                  ? "Status changes only through Deactivate, Reactivate or Archive."
                  : "New clients are created as Active."
              }
            >
              <div className="flex h-9 items-center">
                <StatusBadge
                  status={isEdit ? (client?.status ?? "Active") : "Active"}
                  tone={CLIENT_STATUS_TONES[isEdit ? (client?.status ?? "Active") : "Active"]}
                />
              </div>
            </FormField>
          </FormSection>

          <FormSection title="Address" description="Registered and corporate premises.">
            <FormField id="registeredOffice" label="Registered office" className="sm:col-span-2">
              <Input
                id="registeredOffice"
                value={values.registeredOffice}
                onChange={(event) => set("registeredOffice", event.target.value)}
              />
            </FormField>
            <FormField id="corporateOffice" label="Corporate office" className="sm:col-span-2">
              <Input
                id="corporateOffice"
                value={values.corporateOffice}
                onChange={(event) => set("corporateOffice", event.target.value)}
              />
            </FormField>
            <FormField id="city" label="City">
              <Input id="city" value={values.city} onChange={(event) => set("city", event.target.value)} />
            </FormField>
            <FormField id="state" label="State">
              <Select value={values.state} onValueChange={(value) => set("state", value)}>
                <SelectTrigger id="state">
                  <SelectValue placeholder="Select state" />
                </SelectTrigger>
                <SelectContent>
                  {INDIAN_STATES.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField id="country" label="Country">
              <Input
                id="country"
                value={values.country}
                onChange={(event) => set("country", event.target.value)}
              />
            </FormField>
            <FormField id="pinCode" label="PIN code">
              <Input
                id="pinCode"
                value={values.pinCode}
                onChange={(event) => set("pinCode", event.target.value)}
              />
            </FormField>
          </FormSection>

          <FormSection title="Audit coordination" description="Primary point of contact for the audit team.">
            <FormField
              id="coordinatorName"
              label="Primary audit coordinator"
              required
              error={errors.coordinatorName}
            >
              <Input
                id="coordinatorName"
                value={values.coordinatorName}
                onChange={(event) => set("coordinatorName", event.target.value)}
              />
            </FormField>
            <FormField id="coordinatorDesignation" label="Coordinator designation">
              <Input
                id="coordinatorDesignation"
                value={values.coordinatorDesignation}
                onChange={(event) => set("coordinatorDesignation", event.target.value)}
              />
            </FormField>
            <FormField id="coordinatorEmail" label="Coordinator email" error={errors.coordinatorEmail}>
              <Input
                id="coordinatorEmail"
                type="email"
                value={values.coordinatorEmail}
                onChange={(event) => set("coordinatorEmail", event.target.value)}
              />
            </FormField>
            <FormField
              id="coordinatorMobile"
              label="Coordinator mobile number"
              error={errors.coordinatorMobile}
            >
              <Input
                id="coordinatorMobile"
                value={values.coordinatorMobile}
                onChange={(event) => set("coordinatorMobile", event.target.value)}
                placeholder="+91 90000 00000"
              />
            </FormField>
          </FormSection>

          <FormSection
            title="Statutory identifiers"
            description="Optional for demonstration records; validated only when entered."
          >
            <FormField id="pan" label="PAN" error={errors.pan} hint="Format AAAAA9999A">
              <Input
                id="pan"
                value={values.pan}
                onChange={(event) => set("pan", event.target.value.toUpperCase())}
              />
            </FormField>
            <FormField id="gstin" label="GSTIN" error={errors.gstin} hint="15-character GST identifier">
              <Input
                id="gstin"
                value={values.gstin}
                onChange={(event) => set("gstin", event.target.value.toUpperCase())}
              />
            </FormField>
            <FormField id="financialYearEnding" label="Financial year ending">
              <Select
                value={values.financialYearEnding}
                onValueChange={(value) => set("financialYearEnding", value)}
              >
                <SelectTrigger id="financialYearEnding">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FINANCIAL_YEAR_ENDINGS.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          </FormSection>

          <FormSection title="Other details" description="Internal notes on the client relationship.">
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
            {isEdit ? "Save changes" : "Create client"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
