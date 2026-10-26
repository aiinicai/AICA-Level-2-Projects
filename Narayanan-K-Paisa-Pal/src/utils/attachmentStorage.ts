import { DUMMY_DOCUMENTS } from '../data/dummyDocuments';

// IndexedDB storage for document photo scans, receipts and attachments
const DB_NAME = 'paisa_pal_db';
const DB_VERSION = 1;
const STORE_NAME = 'attachments';

export interface AttachmentRecord {
  id: string; // usually `att_${rowId}`
  rowId: string;
  name: string;
  type: string;
  dataUrl: string; // compressed base64 data (or encrypted base64)
  pdfUrl?: string; // direct link to original PDF file
  previewUrl?: string; // direct link or dataUrl to high-resolution image preview
  size: number;
  uploadedAt: string;
  encrypted?: boolean;
  iv?: string;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      return reject(new Error('IndexedDB not supported in this environment'));
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Compress image to max 1200px width/height and quality 0.8
export async function compressImage(file: File): Promise<{ dataUrl: string; size: number }> {
  if (!file.type.startsWith('image/')) {
    // For non-images (e.g. small PDF/txt), convert directly to dataURL if under 2.5MB
    if (file.size > 2.5 * 1024 * 1024) {
      throw new Error('File exceeds 2.5MB. Please choose a smaller photo or document.');
    }
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve({ dataUrl: String(reader.result), size: file.size });
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const MAX_DIM = 1200;
        let w = img.width;
        let h = img.height;
        if (w > MAX_DIM || h > MAX_DIM) {
          if (w > h) {
            h = Math.round((h * MAX_DIM) / w);
            w = MAX_DIM;
          } else {
            w = Math.round((w * MAX_DIM) / h);
            h = MAX_DIM;
          }
        }
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) return reject(new Error('Canvas context error'));
        ctx.drawImage(img, 0, 0, w, h);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.82);
        // Estimate byte size from base64
        const approxSize = Math.round((dataUrl.length * 3) / 4);
        resolve({ dataUrl, size: approxSize });
      };
      img.onerror = () => reject(new Error('Invalid image file'));
      img.src = String(e.target?.result);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export async function saveAttachment(
  rowId: string,
  file: File
): Promise<AttachmentRecord> {
  const { dataUrl, size } = await compressImage(file);
  const record: AttachmentRecord = {
    id: `att_${rowId}`,
    rowId,
    name: file.name,
    type: file.type || 'image/jpeg',
    dataUrl,
    size,
    uploadedAt: new Date().toISOString(),
  };

  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req = store.put(record);
    req.onsuccess = () => resolve(record);
    req.onerror = () => reject(req.error);
  });
}

export async function getAttachment(
  rowId: string,
  fallbackUrl?: string,
  fallbackName?: string
): Promise<AttachmentRecord | null> {
  try {
    const db = await openDB();
    const stored = await new Promise<AttachmentRecord | null>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(`att_${rowId}`);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });

    if (stored) {
      return stored;
    }

    // Resolve synthetic trial document or linked attachments
    let url = fallbackUrl;
    let name = fallbackName || 'document.pdf';
    let previewUrl: string | undefined = undefined;
    let pdfUrl: string | undefined = undefined;

    if (!url) {
      const synthDoc = DUMMY_DOCUMENTS.find(
        (d) => d.id === rowId || (d.fileName && d.fileName === fallbackName)
      );
      if (synthDoc) {
        url = synthDoc.svgDataUrl;
        name = synthDoc.fileName;
      }
    }

    // If url is already a data URI (such as our synthetic trial document SVGs), return immediately
    if (url && url.startsWith('data:')) {
      const mime = url.match(/data:([^;,]+)/)?.[1] || 'image/svg+xml';
      const isImg = mime.startsWith('image/') || name.endsWith('.svg');
      const rec: AttachmentRecord = {
        id: `att_${rowId}`,
        rowId,
        name,
        type: mime,
        dataUrl: url,
        previewUrl: isImg ? url : undefined,
        pdfUrl: !isImg ? url : undefined,
        size: Math.round(url.length * 0.75),
        uploadedAt: new Date().toISOString(),
      };
      return rec;
    }

    if (url && typeof window !== 'undefined') {
      try {
        const resp = await fetch(url);
        if (resp.ok) {
          const blob = await resp.blob();
          const reader = new FileReader();
          const dataUrl = await new Promise<string>((resolve, reject) => {
            reader.onload = () => resolve(reader.result as string);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
          });

          const rec: AttachmentRecord = {
            id: `att_${rowId}`,
            rowId,
            name,
            type: blob.type || 'application/pdf',
            dataUrl,
            pdfUrl,
            previewUrl,
            size: blob.size,
            uploadedAt: new Date().toISOString(),
          };

          // Cache in IndexedDB
          const tx = db.transaction(STORE_NAME, 'readwrite');
          tx.objectStore(STORE_NAME).put(rec);
          return rec;
        }
      } catch (err) {
        console.warn('Could not fetch fallback asset for attachment', err);
      }
    }

    return null;
  } catch (e) {
    console.error('Error fetching attachment', e);
    return null;
  }
}

export async function getAllAttachments(): Promise<AttachmentRecord[]> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  } catch (e) {
    console.error('Error getting all attachments from IndexedDB', e);
    return [];
  }
}

export async function restoreAttachments(records: AttachmentRecord[]): Promise<boolean> {
  if (!Array.isArray(records) || records.length === 0) return true;
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      for (const rec of records) {
        if (rec && rec.id) {
          store.put(rec);
        }
      }
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => reject(tx.error);
    });
  } catch (e) {
    console.error('Error restoring attachments into IndexedDB', e);
    return false;
  }
}

export async function deleteAttachment(rowId: string): Promise<boolean> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.delete(`att_${rowId}`);
      req.onsuccess = () => resolve(true);
      req.onerror = () => reject(req.error);
    });
  } catch (e) {
    console.error('Error deleting attachment', e);
    return false;
  }
}

export async function clearAllAttachments(): Promise<boolean> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.clear();
      req.onsuccess = () => resolve(true);
      req.onerror = () => reject(req.error);
    });
  } catch (e) {
    console.error('Error clearing attachments', e);
    return false;
  }
}
