import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export function InstallButton({ className }: { className?: string }) {
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [iosLike, setIosLike] = useState(false);

  useEffect(() => {
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      // iOS Safari
      (window.navigator as unknown as { standalone?: boolean }).standalone === true;
    setInstalled(standalone);

    const ua = window.navigator.userAgent;
    setIosLike(/iPhone|iPad|iPod/i.test(ua) || (/Macintosh/.test(ua) && "ontouchend" in document));

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setPromptEvent(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setPromptEvent(null);
    };

    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (installed) return null;

  const handleClick = async () => {
    if (promptEvent) {
      await promptEvent.prompt();
      const choice = await promptEvent.userChoice;
      if (choice.outcome === "accepted") setInstalled(true);
      setPromptEvent(null);
      return;
    }
    setShowHelp((v) => !v);
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleClick}
        className={
          className ??
          "rounded-full border border-primary/40 px-4 py-1.5 text-sm text-primary transition-colors hover:bg-primary/10"
        }
      >
        Install app
      </button>

      {showHelp && !promptEvent ? (
        <div className="panel absolute right-0 z-50 mt-2 w-64 p-4 text-xs leading-relaxed text-muted-foreground">
          {iosLike ? (
            <>
              In Safari, tap <span className="text-foreground">Share</span> then{" "}
              <span className="text-foreground">Add to Home Screen</span>.
            </>
          ) : (
            <>
              Open your browser menu and choose <span className="text-foreground">Install app</span>{" "}
              (or <span className="text-foreground">Add to Home screen</span>). Installing works on
              the published site, not inside the editor preview.
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
