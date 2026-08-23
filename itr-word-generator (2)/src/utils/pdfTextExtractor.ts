/**
 * PDF Text and Structure Extractor
 * Uses pdfjs-dist with positional sorting to reconstruct table lines and structural text
 * from official Income Tax Department ITR-V Ack and ITR 1-4 forms.
 * Supports password-protected ITR PDFs (standard PAN+DOB encryption).
 */

import * as pdfjsLib from 'pdfjs-dist';

// Configure pdfjs worker safely to avoid CORS and version mismatch errors
if (typeof window !== 'undefined') {
  try {
    // Set standard worker url matching pdfjs-dist
    pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version || '3.11.174'}/build/pdf.worker.min.mjs`;
  } catch (e) {
    console.warn('Could not set pdf workerSrc, falling back:', e);
  }
}

export interface ExtractedPageText {
  pageNumber: number;
  lines: string[];
  fullText: string;
}

export interface PDFExtractionResult {
  pages: ExtractedPageText[];
  fullText: string;
  totalPages: number;
  metadata?: Record<string, any>;
  isPasswordProtected?: boolean;
}

/**
 * Extracts clean, sorted line-by-line text from an uploaded PDF File or ArrayBuffer.
 * Handles password-protected PDFs if a password is provided.
 */
export async function extractTextFromPDF(
  fileOrBuffer: File | ArrayBuffer | Uint8Array,
  password?: string,
  onProgress?: (percent: number, currentStep: string) => void
): Promise<PDFExtractionResult> {
  let arrayBuffer: ArrayBuffer;

  if (fileOrBuffer instanceof File) {
    onProgress?.(10, 'Reading PDF file buffer...');
    arrayBuffer = await fileOrBuffer.arrayBuffer();
  } else if (fileOrBuffer instanceof Uint8Array) {
    arrayBuffer = fileOrBuffer.buffer as ArrayBuffer;
  } else {
    arrayBuffer = fileOrBuffer;
  }

  onProgress?.(25, 'Loading PDF document...');

  const loadingTask = pdfjsLib.getDocument({
    data: new Uint8Array(arrayBuffer),
    password: password || undefined,
    useSystemFonts: true,
  });

  const pdf = await loadingTask.promise;
  const totalPages = pdf.numPages;
  const pages: ExtractedPageText[] = [];
  let combinedFullText = '';

  for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
    const stepProgress = 25 + Math.round((pageNum / totalPages) * 60);
    onProgress?.(stepProgress, `Extracting text from page ${pageNum} of ${totalPages}...`);

    const page = await pdf.getPage(pageNum);
    const textContent = await page.getTextContent();

    interface TextItemPos {
      str: string;
      x: number;
      y: number;
      height: number;
    }

    const items: TextItemPos[] = [];
    for (const item of textContent.items as any[]) {
      if (!item.str || item.str.trim() === '') continue;
      const tx = item.transform ? item.transform[4] : 0;
      const ty = item.transform ? item.transform[5] : 0;
      items.push({
        str: item.str,
        x: tx,
        y: ty,
        height: item.height || 10,
      });
    }

    // Sort items top-to-bottom (Y descending), then left-to-right (X ascending)
    items.sort((a, b) => {
      const yDiff = b.y - a.y;
      if (Math.abs(yDiff) > 4) {
        return yDiff; // Different lines
      }
      return a.x - b.x; // Same line, sort left to right
    });

    // Group into distinct lines
    const lineBuckets: string[] = [];
    let currentLine: TextItemPos[] = [];
    let currentY: number | null = null;

    for (const item of items) {
      if (currentY === null || Math.abs(item.y - currentY) <= 4) {
        currentLine.push(item);
        if (currentY === null) currentY = item.y;
      } else {
        currentLine.sort((a, b) => a.x - b.x);
        lineBuckets.push(currentLine.map((i) => i.str).join(' '));
        currentLine = [item];
        currentY = item.y;
      }
    }

    if (currentLine.length > 0) {
      currentLine.sort((a, b) => a.x - b.x);
      lineBuckets.push(currentLine.map((i) => i.str).join(' '));
    }

    const pageFullText = lineBuckets.join('\n');
    pages.push({
      pageNumber: pageNum,
      lines: lineBuckets,
      fullText: pageFullText,
    });

    combinedFullText += (pageNum > 1 ? '\n\n--- PAGE BREAK ---\n\n' : '') + pageFullText;
  }

  // Check if PDF appears to be a scanned document (very few text layer characters)
  const totalCharCount = combinedFullText.replace(/[\s\n-]/g, '').length;
  if (totalCharCount < 60 && totalPages > 0 && typeof window !== 'undefined') {
    try {
      onProgress?.(70, 'Scanned PDF detected. Initializing browser OCR engine (Tesseract)...');
      const { createWorker } = await import('tesseract.js');
      const worker = await createWorker('eng');
      
      let ocrCombinedText = '';
      for (let pageNum = 1; pageNum <= Math.min(totalPages, 5); pageNum++) {
        onProgress?.(
          70 + Math.round((pageNum / Math.min(totalPages, 5)) * 20),
          `Performing OCR on scanned page ${pageNum}...`
        );
        const page = await pdf.getPage(pageNum);
        const viewport = page.getViewport({ scale: 2.0 });
        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          await page.render({ canvasContext: ctx, canvas, viewport } as any).promise;
          const { data } = await worker.recognize(canvas);
          const ocrText = data.text || '';
          const lines = ocrText.split('\n').map((l) => l.trim()).filter(Boolean);
          if (pages[pageNum - 1]) {
            pages[pageNum - 1].lines = lines;
            pages[pageNum - 1].fullText = ocrText;
          }
          ocrCombinedText += (pageNum > 1 ? '\n\n' : '') + ocrText;
        }
      }
      await worker.terminate();
      if (ocrCombinedText.length > combinedFullText.length) {
        combinedFullText = ocrCombinedText;
      }
    } catch (ocrErr) {
      console.warn('OCR fallback completed with warning or was skipped:', ocrErr);
    }
  }

  onProgress?.(95, 'Finalizing extracted PDF structure...');

  let metadata = {};
  try {
    const meta = await pdf.getMetadata();
    metadata = meta.info || {};
  } catch (e) {
    // metadata is optional
  }

  return {
    pages,
    fullText: combinedFullText,
    totalPages,
    metadata,
  };
}

/**
 * Converts a File object to base64 string for Gemini API or preview.
 */
export async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.split(',')[1] || result;
      resolve(base64);
    };
    reader.onerror = (err) => reject(err);
    reader.readAsDataURL(file);
  });
}
