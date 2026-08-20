/**
 * Client-side File & PDF Text Extractor (100% Offline)
 */

export async function extractTextFromFile(file: File): Promise<string> {
  const extension = file.name.split('.').pop()?.toLowerCase();

  // 1. Plain Text / CSV / JSON
  if (
    file.type === 'text/plain' ||
    file.type === 'text/csv' ||
    file.type === 'application/json' ||
    extension === 'txt' ||
    extension === 'csv' ||
    extension === 'json' ||
    extension === 'md'
  ) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve((e.target?.result as string) || '');
      reader.onerror = (e) => reject(new Error('Failed to read text file.'));
      reader.readAsText(file);
    });
  }

  // 2. PDF Files: Extract text streams using FileReader ArrayBuffer
  if (file.type === 'application/pdf' || extension === 'pdf') {
    try {
      const arrayBuffer = await file.arrayBuffer();
      const text = await extractTextFromPdfBuffer(arrayBuffer);
      if (text && text.trim().length > 30) {
        return text;
      }
    } catch (err) {
      console.warn('PDF stream extraction encountered error, attempting fallback string decode:', err);
    }

    // Binary text scraper fallback for PDFs without external heavy CDN
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const raw = (e.target?.result as string) || '';
        // Extract printable text chunks from PDF streams
        const cleanText = extractReadableAscii(raw);
        if (cleanText.length > 50) {
          resolve(cleanText);
        } else {
          resolve(`[PDF Document: ${file.name}]\n(Note: If this PDF is a scanned image, please copy/paste the OCR extracted text into the manual input box for note-by-note audit.)`);
        }
      };
      reader.onerror = () => reject(new Error('Failed to read PDF file.'));
      reader.readAsBinaryString(file);
    });
  }

  throw new Error(`Unsupported file type: ${file.type || extension}`);
}

async function extractTextFromPdfBuffer(buffer: ArrayBuffer): Promise<string> {
  const uint8 = new Uint8Array(buffer);
  let text = '';
  const decoder = new TextDecoder('utf-8', { fatal: false });
  const rawString = decoder.decode(uint8);

  // Extract text within BT ... ET blocks (PDF standard text blocks)
  const btRegex = /BT[\s\S]*?ET/g;
  const matches = rawString.match(btRegex);

  if (matches && matches.length > 0) {
    const extractedLines: string[] = [];
    for (const match of matches) {
      // Find (text) or [(text)] or /Tj /TJ
      const stringMatches = match.match(/\((?:[^()\\]|\\.)*\)|\[(?:[^[\]\\]|\\.)*\]/g);
      if (stringMatches) {
        const chunk = stringMatches
          .map((s) => s.replace(/^[(\[]|[)\]]$/g, '').replace(/\\([()\\])/g, '$1'))
          .join(' ');
        if (chunk.trim()) extractedLines.push(chunk);
      }
    }
    if (extractedLines.length > 5) {
      return extractedLines.join('\n');
    }
  }

  // Fallback: extract clean text segments
  return extractReadableAscii(rawString);
}

function extractReadableAscii(raw: string): string {
  // Filter for readable strings and financial table patterns
  const lines = raw.split(/[\r\n]+/);
  const validLines: string[] = [];

  for (const line of lines) {
    // Keep lines that have alphanumeric characters and reasonable ASCII printable ratio
    const printable = line.replace(/[^\x20-\x7E\t]/g, ' ').trim();
    if (printable.length > 3 && /[a-zA-Z0-9]/.test(printable)) {
      // Avoid raw pdf metadata chunks like << /Length 1234 >>
      if (!printable.startsWith('<<') && !printable.startsWith('xref') && !printable.startsWith('trailer') && !printable.startsWith('obj')) {
        validLines.push(printable);
      }
    }
  }

  return validLines.join('\n');
}
