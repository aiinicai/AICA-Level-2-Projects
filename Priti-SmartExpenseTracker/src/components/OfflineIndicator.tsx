import React from 'react';
import { WifiOff } from 'lucide-react';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

export const OfflineIndicator: React.FC = () => {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div className="fixed bottom-24 left-4 z-40 flex items-center gap-2.5 rounded-xl bg-amber-600/95 backdrop-blur-md px-4 py-2.5 text-xs font-semibold text-white shadow-xl animate-in slide-in-from-bottom-2">
      <WifiOff className="w-4 h-4 animate-pulse" />
      <span>Offline Mode — All transactions saved locally</span>
    </div>
  );
};
