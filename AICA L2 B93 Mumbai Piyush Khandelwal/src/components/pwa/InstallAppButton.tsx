import { useState } from "react";
import { Check, Download, Loader2, Share, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useInstallPrompt } from "./useInstallPrompt";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export function InstallAppButton({ variant = "sidebar" }: { variant?: "sidebar" | "menu" }) {
  const { state, platform, promptInstall, canPrompt } = useInstallPrompt();
  const [open, setOpen] = useState(false);

  const label =
    state === "installed" ? "App installed" : state === "installing" ? "Installing…" : "Install App";

  const onClick = () => setOpen(true);

  const doInstall = async () => {
    const outcome = await promptInstall();
    if (outcome === "accepted") {
      toast.success("The DASH is installing — look for it in your apps.");
      setOpen(false);
    } else if (outcome === "dismissed") {
      toast("Installation cancelled.");
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          variant === "sidebar"
            ? "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            : "text-foreground hover:bg-muted",
          state === "installed" && "text-positive",
        )}
      >
        {state === "installed" ? (
          <Check className="size-4 shrink-0" aria-hidden />
        ) : state === "installing" ? (
          <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden />
        ) : (
          <Download className="size-4 shrink-0" aria-hidden />
        )}
        <span className="truncate">{label}</span>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          {state === "installed" ? (
            <>
              <DialogHeader>
                <DialogTitle>App is already installed</DialogTitle>
                <DialogDescription>
                  You're running The DASH as an installed app. Launch it from your home screen, dock or Start menu.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button onClick={() => setOpen(false)}>Done</Button>
              </DialogFooter>
            </>
          ) : canPrompt ? (
            <>
              <DialogHeader>
                <DialogTitle>Install The DASH</DialogTitle>
                <DialogDescription>Get faster access from your desktop or home screen.</DialogDescription>
              </DialogHeader>
              <ul className="space-y-2 text-sm">
                {[
                  "Launches in its own window, like a native app",
                  "Full-screen workspace with no browser chrome",
                  "Faster access from your dock or home screen",
                  "The app shell stays available when you're offline",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <Check className="mt-0.5 size-4 shrink-0 text-positive" aria-hidden />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-muted-foreground">
                Live financial data still needs a connection — offline you'll see the app shell and clearly labelled
                cached information only.
              </p>
              <DialogFooter className="gap-2 sm:gap-2">
                <Button variant="ghost" onClick={() => setOpen(false)}>
                  Not now
                </Button>
                <Button onClick={doInstall}>Install</Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle>Install this app</DialogTitle>
                <DialogDescription>
                  Your browser doesn't currently offer the automatic installation prompt, so here's the manual route.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-3 text-sm">
                {platform === "ios" && (
                  <p className="flex items-start gap-2">
                    <Share className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                    <span>
                      <strong>iPhone / iPad:</strong> tap the Share button in Safari, then choose{" "}
                      <strong>Add to Home Screen</strong>.
                    </span>
                  </p>
                )}
                {platform === "android" && (
                  <p className="flex items-start gap-2">
                    <Smartphone className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                    <span>
                      <strong>Android:</strong> open the browser menu (⋮) and choose{" "}
                      <strong>Add to Home screen</strong> or <strong>Install app</strong>.
                    </span>
                  </p>
                )}
                <p className="flex items-start gap-2">
                  <Download className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                  <span>
                    <strong>Desktop:</strong> use the install icon in the address bar, or the browser menu →{" "}
                    <strong>Install The DASH</strong>.
                  </span>
                </p>
                <p className="text-xs text-muted-foreground">
                  The app stays fully usable in a normal browser tab either way.
                </p>
              </div>
              <DialogFooter>
                <Button onClick={() => setOpen(false)}>Got it</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
