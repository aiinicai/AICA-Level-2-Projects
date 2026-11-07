import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { toast } from "sonner";
import { PageHeader } from "@/components/procurement/PageHeader";
import { Button } from "@/components/ui/button";
import {
  APP_NAME,
  detectPlatform,
  installSteps,
  onInstallAvailability,
  promptInstall,
  shareLinks,
  shareUrl,
  type Platform,
} from "@/lib/install";

export const Route = createFileRoute("/_authenticated/install")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: `Install & Share — ${APP_NAME}` },
      {
        name: "description",
        content:
          "Get the link, QR code and one-tap install button for Easy AI Procura on phones, tablets and desktops.",
      },
      { property: "og:title", content: `Install & Share — ${APP_NAME}` },
      {
        property: "og:description",
        content:
          "Get the link, QR code and one-tap install button for Easy AI Procura on phones, tablets and desktops.",
      },
    ],
  }),
  component: InstallAndShare,
});

function InstallAndShare() {
  const [platform, setPlatform] = useState<Platform>("desktop");
  const [url, setUrl] = useState("");
  const [qr, setQr] = useState("");
  const [canInstall, setCanInstall] = useState(false);

  useEffect(() => {
    setPlatform(detectPlatform(navigator.userAgent));
    setUrl(shareUrl(window.location.hostname.toLowerCase(), window.location.origin));
    return onInstallAvailability(setCanInstall);
  }, []);

  useEffect(() => {
    if (!url) return;
    let active = true;
    QRCode.toDataURL(url, { errorCorrectionLevel: "M", margin: 0, scale: 8 })
      .then((dataUrl) => {
        if (active) setQr(dataUrl);
      })
      .catch(() => {
        if (active) setQr("");
      });
    return () => {
      active = false;
    };
  }, [url]);

  const links = url ? shareLinks(url) : null;
  const steps = installSteps(platform);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Link copied", { description: url });
    } catch {
      toast.error("Could not copy automatically", { description: url });
    }
  }

  async function systemShare() {
    if (!navigator.share) return;
    try {
      await navigator.share({ title: APP_NAME, text: `${APP_NAME} — LPO, GRN & invoice control`, url });
    } catch {
      // The person closed the share sheet; nothing to report.
    }
  }

  async function install() {
    const outcome = await promptInstall();
    if (outcome === "accepted") toast.success("Installing", { description: "Look for the P icon shortly." });
    else if (outcome === "dismissed") toast.info("Install cancelled", { description: "You can install any time." });
    else toast.info("Use the steps below", { description: "This browser did not offer the one-tap install." });
  }

  return (
    <div>
      <PageHeader
        title="Install & share"
        subtitle="One address for everyone: open it on any device, then add it to the Home screen or desktop."
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        <section className="doc-grid rounded-xl border border-border bg-card p-6">
          <p className="num text-xs uppercase tracking-[0.25em] text-primary">Scan to open</p>
          <div className="mt-5 flex size-[268px] items-center justify-center self-center rounded-lg bg-background p-5">
            {qr ? (
              <img src={qr} alt={`QR code linking to ${url}`} width={228} height={228} />
            ) : (
              <div className="size-[228px] animate-pulse rounded bg-muted" />
            )}
          </div>
          <p className="mt-5 break-all text-center font-mono text-xs text-muted-foreground">{url}</p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Button size="sm" onClick={copyLink} disabled={!url}>
              Copy link
            </Button>
            {typeof navigator.share === "function" ? (
              <Button size="sm" variant="outline" onClick={systemShare} disabled={!url}>
                Share
              </Button>
            ) : null}
            {canInstall ? (
              <Button size="sm" variant="secondary" onClick={install}>
                Install {APP_NAME}
              </Button>
            ) : null}
          </div>
          {links ? (
            <div className="mt-4 flex flex-wrap justify-center gap-4 text-xs">
              <a
                href={links.whatsapp}
                target="_blank"
                rel="noreferrer"
                className="text-primary underline-offset-4 hover:underline"
              >
                Send on WhatsApp
              </a>
              <a href={links.email} className="text-primary underline-offset-4 hover:underline">
                Send by email
              </a>
            </div>
          ) : null}
        </section>

        <section className="rounded-xl border border-border bg-card p-6">
          <p className="num text-xs uppercase tracking-[0.25em] text-primary">
            {platform === "desktop"
              ? "Add it to your desktop"
              : "Add it to your Home screen"}
          </p>
          <ol className="mt-6 space-y-5">
            {steps.map((step, index) => (
              <li key={step.title} className="flex gap-4">
                <span className="num grid size-7 shrink-0 place-items-center rounded-full border border-border text-xs font-semibold text-primary">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-foreground">{step.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="mt-8 grid gap-4 border-t border-border pt-6 sm:grid-cols-2">
            <div>
              <p className="text-sm font-medium text-foreground">Works offline</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Open it once while online, then the screens you used load without internet. New orders,
                deliveries and invoices still need a connection.
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">New people sign up themselves</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Anyone with the link can register and starts as a maker. Only you can approve documents and
                give out other roles.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
