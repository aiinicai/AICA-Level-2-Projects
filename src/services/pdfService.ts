/**
 * External PDF & Document Conversion Service Integration
 * Handles direct multipart file uploads to external conversion endpoints:
 * - /convert/pdf-to-word
 * - /convert/pdf-to-excel
 * - /convert/pdf-to-images
 * - /compress/pdf (level="ebook")
 * - /compress/image (quality=60)
 */

export const DEFAULT_PDF_SERVICE_URL =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_PDF_SERVICE_URL) ||
  'https://pdf-toolkit-service.onrender.com';

const STORAGE_KEY = 'kilitrade_pdf_service_url';

export function getPdfServiceUrl(): string {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && saved.trim()) {
      return saved.trim().replace(/\/+$/, '');
    }
  } catch {
    // LocalStorage fallback
  }
  return DEFAULT_PDF_SERVICE_URL.replace(/\/+$/, '');
}

export function setPdfServiceUrl(url: string): void {
  try {
    if (!url || !url.trim()) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, url.trim().replace(/\/+$/, ''));
    }
  } catch {
    // Ignore error
  }
}

function getFilenameFromResponse(res: Response, fallbackFilename: string): string {
  const disposition = res.headers.get('Content-Disposition') || res.headers.get('content-disposition');
  if (disposition) {
    const filenameMatch = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i);
    if (filenameMatch && filenameMatch[1]) {
      return decodeURIComponent(filenameMatch[1].trim());
    }
  }
  return fallbackFilename;
}

export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

async function handleServiceError(res: Response): Promise<never> {
  let errDetail = `Service error (HTTP ${res.status}: ${res.statusText || 'Failed'})`;
  try {
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const errJson = await res.json();
      if (errJson.detail) {
        errDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      } else if (errJson.message) {
        errDetail = errJson.message;
      } else if (errJson.error) {
        errDetail = typeof errJson.error === 'string' ? errJson.error : JSON.stringify(errJson.error);
      }
    } else {
      const text = await res.text();
      if (text && text.length < 500) {
        errDetail = text;
      }
    }
  } catch {
    // Use fallback status text
  }

  // Specific user-friendly explanation for common codes
  if (res.status === 422 && !errDetail.toLowerCase().includes('scanned')) {
    errDetail = `HTTP 422 Unprocessable Entity: ${errDetail} (e.g. Scanned PDF with no native text layer, or unreadable document stream).`;
  }

  throw new Error(errDetail);
}

/**
 * 1. Convert to Word: POST /convert/pdf-to-word
 */
export async function convertPdfToWord(
  file: File | Blob,
  originalFilename = 'document.pdf'
): Promise<{ filename: string; blob: Blob }> {
  const serviceUrl = getPdfServiceUrl();
  const formData = new FormData();
  formData.append('file', file, originalFilename);

  const res = await fetch(`${serviceUrl}/convert/pdf-to-word`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    await handleServiceError(res);
  }

  const blob = await res.blob();
  const fallback = originalFilename.replace(/\.pdf$/i, '') + '.docx';
  const filename = getFilenameFromResponse(res, fallback);
  triggerDownload(blob, filename);
  return { filename, blob };
}

/**
 * 2. Convert to Excel: POST /convert/pdf-to-excel
 */
export async function convertPdfToExcel(
  file: File | Blob,
  originalFilename = 'document.pdf'
): Promise<{ filename: string; blob: Blob }> {
  const serviceUrl = getPdfServiceUrl();
  const formData = new FormData();
  formData.append('file', file, originalFilename);

  const res = await fetch(`${serviceUrl}/convert/pdf-to-excel`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    await handleServiceError(res);
  }

  const blob = await res.blob();
  const fallback = originalFilename.replace(/\.pdf$/i, '') + '.xlsx';
  const filename = getFilenameFromResponse(res, fallback);
  triggerDownload(blob, filename);
  return { filename, blob };
}

/**
 * 3. Convert to Image: POST /convert/pdf-to-images
 */
export async function convertPdfToImages(
  file: File | Blob,
  originalFilename = 'document.pdf'
): Promise<{ filename: string; blob: Blob }> {
  const serviceUrl = getPdfServiceUrl();
  const formData = new FormData();
  formData.append('file', file, originalFilename);

  const res = await fetch(`${serviceUrl}/convert/pdf-to-images`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    await handleServiceError(res);
  }

  const blob = await res.blob();
  const fallback = originalFilename.replace(/\.pdf$/i, '') + '_images.zip';
  const filename = getFilenameFromResponse(res, fallback);
  triggerDownload(blob, filename);
  return { filename, blob };
}

/**
 * 4. Compress PDF: POST /compress/pdf (form field "level"="ebook")
 */
export async function compressPdfService(
  file: File | Blob,
  originalFilename = 'document.pdf',
  level: string = 'ebook'
): Promise<{ filename: string; blob: Blob; compressedSize: number }> {
  const serviceUrl = getPdfServiceUrl();
  const formData = new FormData();
  formData.append('file', file, originalFilename);
  formData.append('level', level || 'ebook');

  const res = await fetch(`${serviceUrl}/compress/pdf`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    await handleServiceError(res);
  }

  const blob = await res.blob();
  const fallback = 'Compressed_' + originalFilename;
  const filename = getFilenameFromResponse(res, fallback);
  triggerDownload(blob, filename);
  return { filename, blob, compressedSize: blob.size };
}

/**
 * 5. Compress Image: POST /compress/image (form field "quality"=60)
 */
export async function compressImageService(
  file: File | Blob,
  originalFilename = 'image.jpg',
  quality: number = 60
): Promise<{ filename: string; blob: Blob; compressedSize: number }> {
  const serviceUrl = getPdfServiceUrl();
  const formData = new FormData();
  formData.append('file', file, originalFilename);
  formData.append('quality', String(quality));

  const res = await fetch(`${serviceUrl}/compress/image`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    await handleServiceError(res);
  }

  const blob = await res.blob();
  const fallback = 'Compressed_' + originalFilename;
  const filename = getFilenameFromResponse(res, fallback);
  triggerDownload(blob, filename);
  return { filename, blob, compressedSize: blob.size };
}
