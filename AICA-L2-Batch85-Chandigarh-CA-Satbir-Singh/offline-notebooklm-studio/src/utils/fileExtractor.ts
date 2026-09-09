import * as XLSX from 'xlsx';
import * as pdfjsLib from 'pdfjs-dist';
import mammoth from 'mammoth';
import { SourceItem } from '../types';

// Set up pdf.js worker using unpkg / cloudflare CDN or inline worker
try {
  if (typeof window !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version || '3.11.174'}/pdf.worker.min.mjs`;
  }
} catch {
  // Worker fallback
}

async function extractPdfText(buffer: ArrayBuffer): Promise<string> {
  try {
    const loadingTask = pdfjsLib.getDocument({ data: new Uint8Array(buffer) });
    const pdfDoc = await loadingTask.promise;
    const numPages = pdfDoc.numPages;
    const pageTexts: string[] = [];

    for (let pageNum = 1; pageNum <= numPages; pageNum++) {
      const page = await pdfDoc.getPage(pageNum);
      const textContent = await page.getTextContent();
      
      let lastY: number | null = null;
      let pageStr = '';

      for (const item of textContent.items as any[]) {
        if ('str' in item && item.str) {
          const currentY = item.transform ? item.transform[5] : null;
          if (lastY !== null && currentY !== null && Math.abs(currentY - lastY) > 6) {
            pageStr += '\n' + item.str;
          } else {
            pageStr += (pageStr.length > 0 && !pageStr.endsWith(' ') && !pageStr.endsWith('\n') ? ' ' : '') + item.str;
          }
          lastY = currentY;
        }
      }

      const cleanPageText = pageStr.trim();
      if (cleanPageText) {
        pageTexts.push(`--- Page ${pageNum} ---\n${cleanPageText}`);
      }
    }

    const fullText = pageTexts.join('\n\n');
    return fullText.trim();
  } catch (err) {
    console.warn('PDF.js extraction error, falling back:', err);
    return '';
  }
}

export async function parseFileToSourceItem(file: File): Promise<SourceItem> {
  const extLower = file.name.split('.').pop()?.toLowerCase() || 'txt';
  let extractedText = '';
  let fileType: SourceItem['fileType'] = 'TXT';

  if (extLower === 'pdf') {
    fileType = 'PDF';
    try {
      const buffer = await file.arrayBuffer();
      const pdfText = await extractPdfText(buffer);
      
      if (pdfText && pdfText.length > 20) {
        extractedText = pdfText;
      } else {
        // Fallback if scanned image or DRM
        extractedText = `[PDF Document: ${file.name} - ${(file.size / 1024).toFixed(1)} KB (Note: If this is a scanned PDF with no selectable text layer, convert to text/markdown first)]`;
      }
    } catch (e) {
      extractedText = `[PDF Document: ${file.name} - Error reading PDF: ${(e as Error).message}]`;
    }
  } else if (extLower === 'docx' || extLower === 'doc') {
    fileType = 'DOCX';
    try {
      const buffer = await file.arrayBuffer();
      const result = await mammoth.extractRawText({ arrayBuffer: buffer });
      if (result.value && result.value.trim()) {
        extractedText = result.value.trim();
      } else {
        extractedText = `[Word Document: ${file.name} - ${(file.size / 1024).toFixed(1)} KB]`;
      }
    } catch (e) {
      extractedText = `[Word Document: ${file.name} - Error: ${(e as Error).message}]`;
    }
  } else if (extLower === 'xlsx' || extLower === 'xls') {
    fileType = 'XLSX';
    try {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: 'array' });
      const sheetsText: string[] = [];

      workbook.SheetNames.forEach((sheetName) => {
        const sheet = workbook.Sheets[sheetName];
        const csv = XLSX.utils.sheet_to_csv(sheet);
        if (csv.trim()) {
          sheetsText.push(`### Sheet: ${sheetName}\n${csv}`);
        }
      });
      extractedText = sheetsText.join('\n\n');
    } catch (e) {
      extractedText = `[Error parsing spreadsheet ${file.name}: ${(e as Error).message}]`;
    }
  } else if (extLower === 'csv') {
    fileType = 'CSV';
    try {
      extractedText = await file.text();
    } catch {
      extractedText = `[CSV Document: ${file.name}]`;
    }
  } else if (['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(extLower)) {
    fileType = 'IMAGE';
    extractedText = `[Image Reference: ${file.name}]\n- Size: ${(file.size / 1024).toFixed(1)} KB\n- Type: ${file.type}\n- Note: Visual reference source.`;
  } else if (extLower === 'md') {
    fileType = 'MD';
    extractedText = await file.text();
  } else {
    fileType = 'TXT';
    extractedText = await file.text();
  }

  const preview = extractedText.slice(0, 240).replace(/\n+/g, ' ').trim() + (extractedText.length > 240 ? '...' : '');

  return {
    id: 'src-' + Math.random().toString(36).substring(2, 9),
    name: file.name,
    fileType,
    sizeBytes: file.size,
    charCount: extractedText.length,
    preview: preview || 'No text extracted',
    text: extractedText,
    createdAt: new Date().toISOString(),
  };
}

