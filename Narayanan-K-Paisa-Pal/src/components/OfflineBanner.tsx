import React from 'react';
import { WifiOff, Wifi } from 'lucide-react';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

export const OfflineBanner: React.FC = () => {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div
      role="status"
      className="no-print bg-amber-600 text-white text-xs md:text-sm px-4 py-2 flex items-center justify-between shadow-md z-40 relative"
    >
      <div className="flex items-center gap-2 max-w-4xl mx-auto w-full">
        <WifiOff className="w-4 h-4 flex-shrink-0 animate-pulse text-amber-200" />
        <span className="font-medium">
          Offline Mode active: All your entries, calculations, and local backups work safely without an internet connection.
        </span>
      </div>
    </div>
  );
};
