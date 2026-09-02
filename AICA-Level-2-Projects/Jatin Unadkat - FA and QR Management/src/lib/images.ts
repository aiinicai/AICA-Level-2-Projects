import sharp from "sharp";
import { randomUUID } from "crypto";
import { writeVarFile } from "@/lib/fileStorage";

// Photo optimization pipeline (design dossier, Section L):
// resize to a max long edge, re-encode lossy WebP, strip metadata,
// generate a thumbnail. Discards the original after processing.
const MAX_DIMENSION = 1600;
const MAIN_QUALITY = 75;
const THUMB_DIMENSION = 320;
const THUMB_QUALITY = 70;

// Stored under var/ (not public/) and served through an authenticated route
// handler (src/app/api/photos/[...path]/route.ts). Files written to public/
// at runtime never become servable once the app is built for production —
// next start only serves what existed in public/ at build time — so runtime
// uploads have to go through a real route handler instead, same as SAP
// exports and bulk QR PDFs.
export async function processAndStorePhoto(buffer: Buffer, folder: string) {
  const id = randomUUID();
  const mainName = `${id}.webp`;
  const thumbName = `${id}_thumb.webp`;

  const mainBuffer = await sharp(buffer)
    .rotate() // apply EXIF orientation before stripping metadata
    .resize({ width: MAX_DIMENSION, height: MAX_DIMENSION, fit: "inside", withoutEnlargement: true })
    .webp({ quality: MAIN_QUALITY })
    .toBuffer();

  const thumbBuffer = await sharp(buffer)
    .rotate()
    .resize({ width: THUMB_DIMENSION, height: THUMB_DIMENSION, fit: "cover" })
    .webp({ quality: THUMB_QUALITY })
    .toBuffer();

  await writeVarFile(`photos/${folder}`, mainName, mainBuffer);
  await writeVarFile(`photos/${folder}`, thumbName, thumbBuffer);

  return {
    storageKey: `/api/photos/${folder}/${mainName}`,
    thumbnailKey: `/api/photos/${folder}/${thumbName}`,
  };
}

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]);

export function validateUpload(file: File) {
  if (file.size > MAX_UPLOAD_BYTES) throw new Error("Photo exceeds the 10 MB upload limit.");
  if (!ACCEPTED_TYPES.has(file.type)) throw new Error("Unsupported file type — use JPEG, PNG, HEIC, or WebP.");
}
