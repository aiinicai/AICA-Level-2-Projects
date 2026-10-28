import { createFileRoute } from "@tanstack/react-router";
import { toast } from "sonner";
import { deleteAll } from "@/lib/db";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "Privacy & data — Speakwell" },
      { name: "description", content: "How Speakwell handles your recordings, and how to delete all your data." },
      { property: "og:title", content: "Privacy & data — Speakwell" },
      { property: "og:description", content: "Your recordings stay on your device." },
    ],
  }),
  component: Privacy,
});

function Privacy() {
  return (
    <main className="px-5 pt-[max(1.5rem,env(safe-area-inset-top))]">
      <h1 className="text-3xl">Privacy</h1>
      <div className="mt-5 space-y-4 rounded-2xl bg-card p-5 leading-relaxed text-muted-foreground">
        <p><b className="text-foreground">Your recordings stay on this device.</b> Sessions, audio and scores are saved only in this browser's storage.</p>
        <p>When you finish a recording, the audio is sent once to our server to be analysed by AI, and the result is sent back. It isn't stored on the server.</p>
        <p>No account, no tracking. Clearing your browser data or using the button below removes everything.</p>
      </div>
      <button
        onClick={async () => {
          if (!confirm("Delete all sessions, recordings and goals? This can't be undone.")) return;
          await deleteAll();
          toast.success("All your data has been deleted.");
        }}
        className="mt-6 min-h-14 w-full rounded-full bg-destructive font-semibold text-destructive-foreground"
      >
        Delete all my data
      </button>
      <p className="mt-6 text-center text-sm text-muted-foreground">Tip: in Safari tap Share › Add to Home Screen to install Speakwell.</p>
    </main>
  );
}
