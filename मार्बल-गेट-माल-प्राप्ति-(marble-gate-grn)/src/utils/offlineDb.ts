import type { GoodsReceiptNote } from '../types/grn';

const DB_NAME = 'MarbleGateGrnDB';
const DB_VERSION = 1;

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      return reject(new Error('IndexedDB not supported'));
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('drafts')) {
        db.createObjectStore('drafts', { keyPath: 'key' });
      }
      if (!db.objectStoreNames.contains('offlineQueue')) {
        db.createObjectStore('offlineQueue', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('cachedGrns')) {
        db.createObjectStore('cachedGrns', { keyPath: 'id' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// ----------------- DRAFTS -----------------
export async function saveLocalDraft(draftData: any): Promise<void> {
  try {
    const db = await openDb();
    const tx = db.transaction('drafts', 'readwrite');
    const store = tx.objectStore('drafts');
    store.put({ key: 'current_draft', data: draftData, savedAt: new Date().toISOString() });
    return new Promise((resolve) => {
      tx.oncomplete = () => resolve();
    });
  } catch (err) {
    console.warn('Could not save draft to IndexedDB:', err);
  }
}

export async function getLocalDraft(): Promise<{ data: any; savedAt: string } | null> {
  try {
    const db = await openDb();
    const tx = db.transaction('drafts', 'readonly');
    const store = tx.objectStore('drafts');
    const request = store.get('current_draft');
    return new Promise((resolve) => {
      request.onsuccess = () => resolve(request.result ? { data: request.result.data, savedAt: request.result.savedAt } : null);
      request.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

export async function clearLocalDraft(): Promise<void> {
  try {
    const db = await openDb();
    const tx = db.transaction('drafts', 'readwrite');
    const store = tx.objectStore('drafts');
    store.delete('current_draft');
    return new Promise((resolve) => {
      tx.oncomplete = () => resolve();
    });
  } catch (err) {
    console.warn('Could not clear draft:', err);
  }
}

// ----------------- OFFLINE QUEUE -----------------
export async function enqueueOfflineGrn(grn: GoodsReceiptNote): Promise<void> {
  try {
    const db = await openDb();
    const tx = db.transaction(['offlineQueue', 'cachedGrns'], 'readwrite');
    const queueStore = tx.objectStore('offlineQueue');
    const cacheStore = tx.objectStore('cachedGrns');

    queueStore.put(grn);
    cacheStore.put(grn);

    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch (err) {
    console.error('Failed to enqueue offline GRN:', err);
    throw err;
  }
}

export async function getOfflineQueue(): Promise<GoodsReceiptNote[]> {
  try {
    const db = await openDb();
    const tx = db.transaction('offlineQueue', 'readonly');
    const store = tx.objectStore('offlineQueue');
    const request = store.getAll();
    return new Promise((resolve) => {
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => resolve([]);
    });
  } catch {
    return [];
  }
}

export async function removeFromOfflineQueue(id: string): Promise<void> {
  try {
    const db = await openDb();
    const tx = db.transaction('offlineQueue', 'readwrite');
    const store = tx.objectStore('offlineQueue');
    store.delete(id);
    return new Promise((resolve) => {
      tx.oncomplete = () => resolve();
    });
  } catch (err) {
    console.warn('Failed to remove from offline queue:', err);
  }
}

// ----------------- CACHED GRNS -----------------
export async function cacheGrns(grns: GoodsReceiptNote[]): Promise<void> {
  try {
    const db = await openDb();
    const tx = db.transaction('cachedGrns', 'readwrite');
    const store = tx.objectStore('cachedGrns');
    for (const grn of grns) {
      store.put(grn);
    }
    return new Promise((resolve) => {
      tx.oncomplete = () => resolve();
    });
  } catch (err) {
    console.warn('Failed to cache GRNs:', err);
  }
}

export async function getCachedGrns(): Promise<GoodsReceiptNote[]> {
  try {
    const db = await openDb();
    const tx = db.transaction('cachedGrns', 'readonly');
    const store = tx.objectStore('cachedGrns');
    const request = store.getAll();
    return new Promise((resolve) => {
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => resolve([]);
    });
  } catch {
    return [];
  }
}

export async function updateCachedGrn(grn: GoodsReceiptNote): Promise<void> {
  try {
    const db = await openDb();
    const tx = db.transaction('cachedGrns', 'readwrite');
    const store = tx.objectStore('cachedGrns');
    store.put(grn);
    return new Promise((resolve) => {
      tx.oncomplete = () => resolve();
    });
  } catch (err) {
    console.warn('Failed to update cached GRN:', err);
  }
}
