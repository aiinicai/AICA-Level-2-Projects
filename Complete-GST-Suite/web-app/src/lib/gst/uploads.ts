import type { Invoice, Return3B } from "./demo";

/** A file the user uploaded for a client (portal JSON, templates, Tally exports). */
export interface UploadedFile {
  id: string;
  name: string;
  kind: string;
  period: string;
  rows: number;
  at: string;
  by: string;
  gstin: string;
  status: "Imported" | "Rejected";
  message?: string | undefined;
}

/** Data that came from uploads (or a GSP fetch) for one client. Month keys are "YYYY-MM". */
export interface UploadedData {
  gstr1: Record<string, Invoice[]>;
  gstr2b: Record<string, Invoice[]>;
  gstr3b: Record<string, Return3B>;
  sales?: Invoice[] | undefined;
  purchases?: Invoice[] | undefined;
  booksLabel?: { sales?: string | undefined; purchases?: string | undefined } | undefined;
  files: UploadedFile[];
  /** remembered column mapping per register kind */
  mapping?: { sales?: Record<string, string> | undefined; purchase?: Record<string, string> | undefined } | undefined;
}

export const emptyUploads = (): UploadedData => ({ gstr1: {}, gstr2b: {}, gstr3b: {}, files: [] });

let provider: (clientId: string) => UploadedData | undefined = () => undefined;
let version = 0;

/** The store registers where uploads live; the engine stays free of storage code. */
export function setUploadProvider(fn: (clientId: string) => UploadedData | undefined) {
  provider = fn;
  version++;
}
export const uploadsFor = (clientId: string) => provider(clientId);
/** Changes whenever uploaded data changes, so calculation caches are rebuilt. */
export const dataVersion = () => version;
export const bumpDataVersion = () => {
  version++;
};
