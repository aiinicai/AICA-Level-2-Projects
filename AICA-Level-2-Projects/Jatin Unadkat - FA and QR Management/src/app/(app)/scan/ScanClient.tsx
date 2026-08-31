"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Html5Qrcode } from "html5-qrcode";

const READER_ID = "qr-reader-region";

export default function ScanClient() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const scannerRef = useRef<Html5Qrcode | null>(null);

  function handleDecoded(decodedText: string) {
    try {
      const url = new URL(decodedText);
      router.push(url.pathname + url.search);
    } catch {
      // Not a full URL — treat the scanned text as a bare token.
      router.push(`/a/${decodedText}`);
    }
  }

  async function startScanning() {
    setError(null);
    setScanning(true);
    try {
      const { Html5Qrcode } = await import("html5-qrcode");
      const scanner = new Html5Qrcode(READER_ID);
      scannerRef.current = scanner;
      // Explicitly triggered by a tap, not on mount — mobile browsers are
      // far more reliable granting camera access from a direct user gesture
      // than from code that runs automatically when the page loads.
      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 240, height: 240 } },
        (decodedText) => {
          handleDecoded(decodedText);
          scanner.stop().catch(() => {});
        },
        () => {
          // per-frame scan misses are expected while searching for a code; ignore.
        }
      );
    } catch (e) {
      setScanning(false);
      const message = e instanceof Error ? e.message : String(e);
      setError(
        message.toLowerCase().includes("permission")
          ? "Camera permission was denied. Check your browser's site settings and allow camera access, then try again."
          : `Could not start the camera: ${message}`
      );
    }
  }

  async function stopScanning() {
    try {
      await scannerRef.current?.stop();
    } catch {
      // already stopped — nothing to do.
    }
    setScanning(false);
  }

  return (
    <div className="max-w-md mx-auto space-y-4">
      <div className="card p-4">
        <div id={READER_ID} className={scanning ? "" : "hidden"} />
        {!scanning && (
          <button onClick={startScanning} className="btn-primary w-full py-4 text-base">
            Start camera
          </button>
        )}
        {scanning && (
          <button onClick={stopScanning} className="btn-secondary w-full mt-3">
            Cancel
          </button>
        )}
      </div>
      {error && <p className="text-sm text-bad">{error}</p>}
      <p className="text-xs text-muted text-center">
        Point the camera at the asset&apos;s printed QR label. Grant camera permission when your browser asks.
      </p>
    </div>
  );
}
