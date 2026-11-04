// On-device document reading (free, nothing leaves the phone):
//   PDF → text layer via pdf.js (exact for e-mailed / downloaded bills and challan receipts)
//   PDF → page image → e-invoice QR via jsQR
//   Photo → text via tesseract.js (slower, less accurate — used only when no QR and no AI OCR)
// Libraries are loaded on first use so the app stays light.

import jsQR from 'jsqr';

async function pdfjs() {
  const lib = await import('pdfjs-dist');
  const worker = (await import('pdfjs-dist/build/pdf.worker.min.mjs?url')).default;
  lib.GlobalWorkerOptions.workerSrc = worker;
  return lib;
}

/** Text of the first `maxPages` pages, rebuilt into lines by vertical position. */
export async function pdfText(file: Blob, maxPages = 3): Promise<string> {
  const lib = await pdfjs();
  const doc = await lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
  const out: string[] = [];
  for (let p = 1; p <= Math.min(doc.numPages, maxPages); p++) {
    const page = await doc.getPage(p);
    const content = await page.getTextContent();
    const rows = new Map<number, { x: number; s: string }[]>();
    for (const it of content.items) {
      if (!('str' in it)) continue;
      const y = Math.round(it.transform[5] / 2) * 2; // tolerate tiny baseline differences
      rows.set(y, [...(rows.get(y) ?? []), { x: it.transform[4], s: it.str }]);
    }
    out.push([...rows].sort((a, b) => b[0] - a[0]).map(([, parts]) => parts.sort((a, b) => a.x - b.x).map((x) => x.s).join(' ').trim()).filter(Boolean).join('\n'));
  }
  return out.join('\n');
}

/** Render page 1 and look for a QR code (e-invoice). */
/** Page-image QR scan. Optional, so it gives up after 10 s: pdf.js draws in animation frames, which stop while the app is
 *  in the background (phone locked, other tab) — without a limit the whole Inbox would wait. */
export async function pdfQr(file: Blob, timeoutMs = 10000): Promise<string | null> {
  return Promise.race([pdfQrScan(file), new Promise<null>((res) => setTimeout(() => res(null), timeoutMs))]);
}

async function pdfQrScan(file: Blob): Promise<string | null> {
  const lib = await pdfjs();
  const doc = await lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
  const page = await doc.getPage(1);
  const viewport = page.getViewport({ scale: 2.5 });
  const canvas = document.createElement('canvas');
  canvas.width = viewport.width;
  canvas.height = viewport.height;
  const ctx = canvas.getContext('2d')!;
  await page.render({ canvasContext: ctx, viewport }).promise;
  const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
  return jsQR(img.data, img.width, img.height, { inversionAttempts: 'attemptBoth' })?.data ?? null;
}

/** Files of the on-device reader, served by this app (vite.config.ts → ocrAssets), about 7 MB in all. */
const OCR_BASE = () => `${location.origin}/ocr`;
export const OCR_PATHS = { worker: '/ocr/worker.min.js', core: ['/ocr/core/tesseract-core-simd-lstm.wasm.js', '/ocr/core/tesseract-core-lstm.wasm.js'], lang: '/ocr/lang/eng.traineddata.gz' };

/** Is offline reading already on this phone? (the service worker keeps the files in the "vouchr-readers" cache) */
export async function ocrDownloaded(): Promise<boolean> {
  if (!('caches' in window)) return false;
  const c = await caches.open('vouchr-readers');
  return !!(await c.match(OCR_PATHS.worker)) && !!(await c.match(OCR_PATHS.lang));
}

/** Opt-in: fetch the reader files now (on Wi-Fi) so the first bill photo reads without waiting. */
export async function downloadOcr(onProgress?: (done: number, total: number) => void): Promise<void> {
  const files = [OCR_PATHS.worker, ...OCR_PATHS.core, OCR_PATHS.lang];
  const c = 'caches' in window ? await caches.open('vouchr-readers') : undefined;
  for (let i = 0; i < files.length; i++) {
    const res = await fetch(files[i]);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await c?.put(files[i], res);
    onProgress?.(i + 1, files.length);
  }
}

export class ReadCancelled extends Error { constructor(public timedOut = false) { super(timedOut ? 'Reading took too long' : 'Reading cancelled'); } }

/** On-device OCR for photos (English model, served by this app). Stops on `signal` (Cancel button) or after `limitMs`. */
export async function photoText(image: Blob, onProgress?: (pct: number) => void, signal?: AbortSignal, limitMs = 45_000): Promise<string> {
  // tesseract.js is CommonJS: under Vite the API sits on `default`
  const mod = (await import('tesseract.js')) as unknown as { createWorker?: typeof import('tesseract.js').createWorker; default?: { createWorker: typeof import('tesseract.js').createWorker } };
  const createWorker = mod.createWorker ?? mod.default!.createWorker;
  if (signal?.aborted) throw new ReadCancelled();
  if (location.protocol === 'file:') throw new Error('Photo reading needs the app to be served (not available in the demo file)');
  const worker = await createWorker('eng', 1, {
    workerPath: OCR_PATHS.worker, corePath: `${OCR_BASE()}/core`, langPath: `${OCR_BASE()}/lang`, workerBlobURL: false,
    logger: (m: { status: string; progress: number }) => { if (m.status === 'recognizing text') onProgress?.(Math.round(m.progress * 100)); }
  });
  let timer: number | undefined;
  try {
    const stop = new Promise<never>((_, reject) => {
      if (signal?.aborted) reject(new ReadCancelled()); // Cancel pressed while the reader was starting
      signal?.addEventListener('abort', () => reject(new ReadCancelled()), { once: true });
      timer = window.setTimeout(() => reject(new ReadCancelled(true)), limitMs);
    });
    const { data } = await Promise.race([worker.recognize(image), stop]);
    return data.text;
  } finally {
    window.clearTimeout(timer);
    await worker.terminate(); // also stops a reading that was cancelled
  }
}
