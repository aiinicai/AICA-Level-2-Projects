import { useState, useEffect, useCallback } from 'react';
import { getOfflineQueue, removeFromOfflineQueue, updateCachedGrn } from '../utils/offlineDb';
import type { GoodsReceiptNote, SyncStatus } from '../types/grn';

export function useNetworkSync(onSyncComplete?: (count: number) => void) {
  const [isOnline, setIsOnline] = useState<boolean>(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [pendingSyncCount, setPendingSyncCount] = useState<number>(0);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  // Refresh pending count
  const refreshPendingCount = useCallback(async () => {
    try {
      const queue = await getOfflineQueue();
      setPendingSyncCount(queue.length);
    } catch (err) {
      console.warn('Error reading offline queue:', err);
    }
  }, []);

  // Perform sync
  const syncNow = useCallback(async (): Promise<{ success: boolean; count: number; error?: string }> => {
    if (!navigator.onLine) {
      setSyncError('इंटरनेट कनेक्शन उपलब्ध नहीं है। कृपया नेटवर्क जांचें।');
      return { success: false, count: 0, error: 'ऑफलाइन' };
    }

    try {
      setIsSyncing(true);
      setSyncError(null);
      const queue = await getOfflineQueue();

      if (queue.length === 0) {
        setIsSyncing(false);
        return { success: true, count: 0 };
      }

      const response = await fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: queue })
      });

      if (!response.ok) {
        throw new Error('सर्वर सिंक विफल रहा। स्थिति: ' + response.status);
      }

      const result = await response.json();
      const syncedList: { provisionalId: string; officialGrnNumber: string; id: string }[] = result.synced || [];

      // Update local storage and remove synced items from queue
      for (const item of queue) {
        const match = syncedList.find(s => s.provisionalId === item.provisionalId || s.provisionalId === item.id);
        if (match) {
          const updated: GoodsReceiptNote = {
            ...item,
            id: match.id,
            grnNumber: match.officialGrnNumber,
            isProvisional: false,
            syncStatus: 'सर्वर पर सुरक्षित'
          };
          await updateCachedGrn(updated);
          await removeFromOfflineQueue(item.id);
        }
      }

      await refreshPendingCount();
      setLastSyncTime(new Date().toLocaleTimeString('hi-IN'));
      setIsSyncing(false);

      if (onSyncComplete) {
        onSyncComplete(syncedList.length);
      }

      return { success: true, count: syncedList.length };
    } catch (err: any) {
      console.error('Sync failed:', err);
      setIsSyncing(false);
      const msg = err.message || 'सर्वर से संपर्क नहीं हो सका। डेटा इस डिवाइस पर सुरक्षित है।';
      setSyncError(msg);
      return { success: false, count: 0, error: msg };
    }
  }, [onSyncComplete, refreshPendingCount]);

  useEffect(() => {
    refreshPendingCount();

    const handleOnline = () => {
      setIsOnline(true);
      // Auto sync when coming back online
      syncNow();
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Periodic check
    const interval = setInterval(() => {
      refreshPendingCount();
    }, 10000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(interval);
    };
  }, [refreshPendingCount, syncNow]);

  return {
    isOnline,
    pendingSyncCount,
    isSyncing,
    lastSyncTime,
    syncError,
    syncNow,
    refreshPendingCount
  };
}
