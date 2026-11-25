import { mkdir, writeFile, readFile } from "fs/promises";
import path from "path";

// Deliberately outside public/ — files here (SAP exports, bulk QR PDFs) are
// only ever served through an authenticated route handler (design dossier,
// ADD16), never as a static, link-guessable asset.
const VAR_ROOT = path.join(process.cwd(), "var");

export async function writeVarFile(subdir: string, fileName: string, data: Uint8Array | string): Promise<string> {
  const dir = path.join(VAR_ROOT, subdir);
  await mkdir(dir, { recursive: true });
  const filePath = path.join(dir, fileName);
  await writeFile(filePath, data);
  return filePath;
}

export async function readVarFile(filePath: string): Promise<Buffer> {
  return readFile(filePath);
}
