import type { ParsedFile } from "./sources";

import { MAX_ZIP_MB } from "./zip";

export const ACCEPTED_FILES = ".xlsx,.xls,.xlsm,.xlsb,.ods,.csv,.txt,.tsv,.json,.xml,.zip";
export const MAX_FILE_MB = 25;

/** File made by the Tally Connector ("Tally from the app" button). */
export const isConnectorFile = (name: string) => /^Tally_.+_(DayBook|UnsecuredLoans|LoanGroups)\.xml$/.test(name);

/** Parse a file in a Web Worker. */
export async function parseFile(file: File, module: "c44" | "c31" = "c44"): Promise<ParsedFile> {
  let buffer: ArrayBuffer;
  const zip0 = /\.zip$/i.test(file.name);
  const big0 = zip0 || isConnectorFile(file.name);
  if (file.size > (big0 ? MAX_ZIP_MB : MAX_FILE_MB) * 1024 * 1024) throw new Error(big0 ? `ZIP is larger than ${MAX_ZIP_MB} MB. Use a shorter period.` : `File is larger than ${MAX_FILE_MB} MB. Put it in a ZIP (up to ${MAX_ZIP_MB} MB) or export a shorter period.`);
  try { buffer = await file.arrayBuffer(); }
  catch { throw new Error("The file could not be opened. If it is on OneDrive, make sure it is downloaded to this computer, then choose it again."); }
  return new Promise((resolve, reject) => {
    const zip = /\.zip$/i.test(file.name);
    // a Day Book brought by the Tally Connector is plain XML but can be as big as a ZIP's contents
    const big = zip || isConnectorFile(file.name);
    const worker = new Worker(new URL("../../workers/parse.worker.ts", import.meta.url), { type: "module" });
    const timer = setTimeout(() => { worker.terminate(); reject(new Error("Reading the file took too long.")); }, big ? 600000 : 120000);
    worker.onmessage = (e: MessageEvent<{ ok: boolean; result?: ParsedFile; error?: string }>) => {
      clearTimeout(timer);
      worker.terminate();
      if (e.data.ok && e.data.result) resolve(e.data.result); else reject(new Error(e.data.error || "Could not read the file."));
    };
    worker.onerror = (e) => { clearTimeout(timer); worker.terminate(); reject(new Error(e.message || "Could not read the file.")); };
    worker.postMessage({ name: file.name, buffer, module }, [buffer]);
  });
}
