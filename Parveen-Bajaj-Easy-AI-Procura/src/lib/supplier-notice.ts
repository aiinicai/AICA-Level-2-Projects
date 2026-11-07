// Works out what went wrong with a delivery and writes the message to the
// supplier. Pure functions so the wording can be checked without a browser.

export type ProblemKind = "not_supplied" | "short" | "damaged" | "wrong_item";

export type DeliveryLine = {
  itemCode: string;
  description: string;
  unit: string;
  ordered: number;
  received: number;
  condition: string;
  remarks?: string | null;
};

export type SupplyProblem = {
  kind: ProblemKind;
  itemCode: string;
  description: string;
  detail: string;
};

const KIND_LABEL: Record<ProblemKind, string> = {
  not_supplied: "Not supplied",
  short: "Short supply",
  damaged: "Damaged",
  wrong_item: "Wrong item delivered",
};

export function findSupplyProblems(lines: DeliveryLine[]): SupplyProblem[] {
  const problems: SupplyProblem[] = [];

  for (const line of lines) {
    const ordered = Number(line.ordered ?? 0);
    const received = Number(line.received ?? 0);

    if (ordered > 0 && received <= 0) {
      problems.push({
        kind: "not_supplied",
        itemCode: line.itemCode,
        description: line.description,
        detail: `nothing received against ${ordered} ${line.unit} ordered`,
      });
    } else if (received < ordered) {
      problems.push({
        kind: "short",
        itemCode: line.itemCode,
        description: line.description,
        detail: `received ${received} of ${ordered} ${line.unit}`,
      });
    }

    if (line.condition === "DAMAGED") {
      problems.push({
        kind: "damaged",
        itemCode: line.itemCode,
        description: line.description,
        detail: `items were received damaged${line.remarks ? ` — ${line.remarks}` : ""}`,
      });
    } else if (line.condition === "WRONG_ITEM") {
      problems.push({
        kind: "wrong_item",
        itemCode: line.itemCode,
        description: line.description,
        detail: `the item delivered was not the one ordered${line.remarks ? ` — ${line.remarks}` : ""}`,
      });
    }
  }

  return problems;
}

export type NoticeInput = {
  grnNumber: string;
  lpoNumber: string;
  supplierName: string;
  contactPerson?: string | null;
  receivedDate: string;
  deliveryNoteNo?: string | null;
  receivedBy?: string | null;
  departmentName?: string | null;
  problems: SupplyProblem[];
};

export function buildSupplierNotice(input: NoticeInput): { subject: string; body: string } {
  const greeting = input.contactPerson ? `Dear ${input.contactPerson},` : "Dear Supplier,";
  const list = input.problems
    .map(
      (problem, index) =>
        `${index + 1}. ${problem.itemCode} ${problem.description} — ${KIND_LABEL[problem.kind]} (${problem.detail})`,
    )
    .join("\n");

  const body = [
    greeting,
    "",
    `We checked the delivery on ${input.grnNumber} against purchase order ${input.lpoNumber}, received on ${input.receivedDate}, and noted the following:`,
    "",
    list,
    "",
    input.deliveryNoteNo ? `Delivery note: ${input.deliveryNoteNo}` : null,
    input.receivedBy ? `Received by: ${input.receivedBy}` : null,
    "",
    "Please confirm in writing when the outstanding items will be delivered or replaced.",
    "",
    `Regards,\n${input.departmentName ? `${input.departmentName} — ` : ""}Easy AI Procura`,
  ]
    .filter((part): part is string => part !== null)
    .join("\n");

  return {
    subject: `Delivery problem on ${input.grnNumber} — ${input.supplierName}`,
    body,
  };
}

export function mailtoLink(email: string, subject: string, body: string): string {
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
