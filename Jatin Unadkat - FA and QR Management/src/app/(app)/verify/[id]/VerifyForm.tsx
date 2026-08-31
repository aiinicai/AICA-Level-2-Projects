"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { submitVerification } from "@/actions/verifications";

type Option = { id: string; label: string };

const RESULTS: { value: "VERIFIED" | "RELOCATED" | "DAMAGED" | "NOT_FOUND"; label: string; style: string }[] = [
  { value: "VERIFIED", label: "Verified — as expected", style: "peer-checked:bg-good peer-checked:text-white peer-checked:border-good" },
  { value: "RELOCATED", label: "Relocated", style: "peer-checked:bg-warn peer-checked:text-white peer-checked:border-warn" },
  { value: "DAMAGED", label: "Damaged", style: "peer-checked:bg-bad peer-checked:text-white peer-checked:border-bad" },
  { value: "NOT_FOUND", label: "Not found", style: "peer-checked:bg-bad peer-checked:text-white peer-checked:border-bad" },
];

export default function VerifyForm({
  assetId,
  locations,
  currentLocationId,
  campaignId,
  gpsEnabled,
}: {
  assetId: string;
  locations: Option[];
  currentLocationId?: string;
  campaignId?: string;
  gpsEnabled: boolean;
}) {
  const [result, setResult] = useState("VERIFIED");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [gps, setGps] = useState<{ lat: number; lng: number } | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!gpsEnabled || !("geolocation" in navigator)) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setGps({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => setGps(null),
      { timeout: 4000 }
    );
  }, [gpsEnabled]);

  async function onSubmit(formData: FormData) {
    setPending(true);
    setErrorMsg(null);
    try {
      const outcome = await submitVerification(assetId, formData);
      if (outcome.ok) {
        router.push(`/verify/${assetId}/done?result=${outcome.result}`);
        return;
      }
    } catch (e) {
      setErrorMsg((e as Error).message);
    }
    setPending(false);
  }

  return (
    <form ref={formRef} action={onSubmit} className="space-y-6">
      <section className="card p-5">
        <h2 className="text-sm font-semibold mb-3">What did you find?</h2>
        <div className="grid grid-cols-2 gap-3">
          {RESULTS.map((r) => (
            <label key={r.value} className="cursor-pointer">
              <input
                type="radio"
                name="result"
                value={r.value}
                checked={result === r.value}
                onChange={() => setResult(r.value)}
                className="peer sr-only"
              />
              <div className={`rounded-lg border border-line py-4 text-center text-sm font-medium transition-colors ${r.style}`}>
                {r.label}
              </div>
            </label>
          ))}
        </div>
      </section>

      <section className="card p-5">
        <label className="label" htmlFor="verifiedLocationId">Physical location right now</label>
        <select id="verifiedLocationId" name="verifiedLocationId" required defaultValue={currentLocationId ?? ""} className="input">
          <option value="" disabled>Select a location…</option>
          {locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
        </select>
      </section>

      <section className="card p-5">
        <label className="label" htmlFor="condition">Physical condition</label>
        <select id="condition" name="condition" defaultValue="Good" className="input">
          <option value="Good">Good</option>
          <option value="Fair">Fair</option>
          <option value="Poor">Poor</option>
          <option value="Damaged">Damaged</option>
        </select>
      </section>

      <section className="card p-5">
        <label className="label" htmlFor="observedSerialNumber">Serial number on the physical label (optional)</label>
        <input id="observedSerialNumber" name="observedSerialNumber" className="input font-mono" placeholder="Only fill in if it looks different from SAP's record" />
      </section>

      <section className="card p-5">
        <label className="label" htmlFor="photo">Photograph</label>
        <input
          id="photo"
          name="photo"
          type="file"
          accept="image/*"
          capture="environment"
          className="input"
          onChange={(e) => {
            const file = e.target.files?.[0];
            setPreviewUrl(file ? URL.createObjectURL(file) : null);
          }}
        />
        {previewUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={previewUrl} alt="Preview" className="mt-3 rounded-md max-h-48 object-cover" />
        )}
      </section>

      <section className="card p-5">
        <label className="label" htmlFor="remarks">Remarks (optional)</label>
        <textarea id="remarks" name="remarks" rows={2} className="input" placeholder="One line is enough" />
      </section>

      <input type="hidden" name="campaignId" value={campaignId ?? ""} />
      <input type="hidden" name="gpsLat" value={gps?.lat ?? ""} />
      <input type="hidden" name="gpsLng" value={gps?.lng ?? ""} />

      {errorMsg && <p className="text-sm text-bad">{errorMsg}</p>}

      <button type="submit" disabled={pending} className="btn-primary w-full text-base py-3">
        {pending ? "Submitting…" : "Submit verification"}
      </button>
    </form>
  );
}
