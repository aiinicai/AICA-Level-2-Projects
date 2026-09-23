import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

export function OfflineBanner() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="status"
      className="flex items-center gap-2 border-b border-warning/30 bg-warning/12 px-4 py-2 text-xs text-foreground"
    >
      <WifiOff className="size-3.5 shrink-0 text-warning" aria-hidden />
      <span>
        <strong>You're offline.</strong> Live data may be unavailable until you reconnect — figures on screen may be
        cached rather than current.
      </span>
    </div>
  );
}
