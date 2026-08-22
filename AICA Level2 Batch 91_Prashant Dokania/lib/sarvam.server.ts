/**
 * Sarvam AI Batch Speech-to-Text.
 *
 * Flow: init job -> signed upload URL -> PUT the WAV -> start -> poll status ->
 * download the diarized transcript JSON. Batch jobs run for minutes, so the
 * polling step never happens inside one request: `startSarvamJob` returns the
 * job id and `fetchSarvamResult` is called again later by the client poller.
 */

const BASE = "https://api.sarvam.ai/speech-to-text/job/v1";

type Signed = { file_url: string };
type FilesResponse = {
  job_id: string;
  job_state: string;
  upload_urls?: Record<string, Signed>;
  download_urls?: Record<string, Signed>;
};

export type SpeakerSegment = { speaker: string; text: string; seconds: number };

function headers(key: string) {
  return { "api-subscription-key": key, "Content-Type": "application/json" };
}

async function jsonOrThrow(res: Response, what: string) {
  const body = await res.text();
  if (!res.ok) throw new Error(`Sarvam ${what} failed (${res.status}): ${body.slice(0, 400)}`);
  return body ? (JSON.parse(body) as Record<string, unknown>) : {};
}

/**
 * Sarvam needs the explicit language code. Sending "unknown" for everything
 * except English made regional audio auto-detect (and usually come back
 * anglicised), which is why Tamil/Telugu/Marathi/Gujarati read wrong.
 */
const SARVAM_LANGUAGE: Record<string, string> = {
  en: "en-IN",
  hi: "hi-IN",
  hinglish: "hi-IN",
  mr: "mr-IN",
  gu: "gu-IN",
  ta: "ta-IN",
  te: "te-IN",
};

export function sarvamLanguageCode(id: string) {
  return SARVAM_LANGUAGE[id] ?? "unknown";
}

export async function startSarvamJob(input: {
  apiKey: string;
  audioBase64: string;
  languageCode: string;
}): Promise<string> {
  const params = {
    // Verbatim transcription. The saaras family is speech-to-text-TRANSLATE and
    // pulls regional audio toward English/Hindi even in transcribe mode.
    model: "saarika:v2.5",
    mode: "transcribe",
    language_code: sarvamLanguageCode(input.languageCode),
    with_diarization: true,
    num_speakers: 2,
  };


  // The init body nests tuning under job_parameters; older deployments accept it
  // flattened, so fall back once rather than failing the whole recording.
  let init = await fetch(BASE, {
    method: "POST",
    headers: headers(input.apiKey),
    body: JSON.stringify({ job_parameters: params }),
  });
  if (!init.ok && init.status >= 400 && init.status < 500) {
    init = await fetch(BASE, {
      method: "POST",
      headers: headers(input.apiKey),
      body: JSON.stringify(params),
    });
  }
  const initBody = await jsonOrThrow(init, "job init");
  const jobId = String(initBody["job_id"] ?? "");
  if (!jobId) throw new Error("Sarvam did not return a job id.");

  const fileName = "conversation.wav";
  const upload = (await jsonOrThrow(
    await fetch(`${BASE}/upload-files`, {
      method: "POST",
      headers: headers(input.apiKey),
      body: JSON.stringify({ job_id: jobId, files: [fileName] }),
    }),
    "upload url",
  )) as unknown as FilesResponse;

  const target = upload.upload_urls?.[fileName]?.file_url;
  if (!target) throw new Error("Sarvam did not return an upload URL.");

  const raw = Uint8Array.from(atob(input.audioBase64), (c) => c.charCodeAt(0));
  const put = await fetch(target, {
    method: "PUT",
    headers: { "x-ms-blob-type": "BlockBlob", "Content-Type": "audio/wav" },
    body: raw,
  });
  if (!put.ok) throw new Error(`Uploading the recording failed (${put.status}).`);

  await jsonOrThrow(
    await fetch(`${BASE}/${jobId}/start`, { method: "POST", headers: headers(input.apiKey) }),
    "job start",
  );

  return jobId;
}

export type SarvamResult =
  | { state: "running" }
  | { state: "failed"; error: string }
  | { state: "done"; segments: SpeakerSegment[]; transcript: string };

export async function fetchSarvamResult(input: {
  apiKey: string;
  jobId: string;
}): Promise<SarvamResult> {
  const status = await jsonOrThrow(
    await fetch(`${BASE}/${input.jobId}/status`, { headers: headers(input.apiKey) }),
    "job status",
  );
  const state = String(status["job_state"] ?? "Running");
  if (state === "Failed") return { state: "failed", error: "Transcription failed at Sarvam." };
  if (state !== "Completed") return { state: "running" };

  const details =
    (status["job_details"] as Array<{ outputs?: Array<{ file_name?: string }> }>) ?? [];
  const files = details
    .flatMap((d) => d.outputs ?? [])
    .map((o) => o.file_name)
    .filter((n): n is string => Boolean(n));
  if (files.length === 0) return { state: "failed", error: "No transcript file was produced." };

  const download = (await jsonOrThrow(
    await fetch(`${BASE}/download-files`, {
      method: "POST",
      headers: headers(input.apiKey),
      body: JSON.stringify({ job_id: input.jobId, files }),
    }),
    "download",
  )) as unknown as FilesResponse;

  const segments: SpeakerSegment[] = [];
  let flat = "";
  for (const name of files) {
    const url = download.download_urls?.[name]?.file_url;
    if (!url) continue;
    const payload = (await (await fetch(url)).json()) as {
      transcript?: string;
      diarized_transcript?: { entries?: Array<Record<string, unknown>> };
    };
    flat += `${payload.transcript ?? ""} `;
    for (const entry of payload.diarized_transcript?.entries ?? []) {
      const speaker = String(entry["speaker_id"] ?? entry["speaker"] ?? "Speaker 1");
      const text = String(entry["transcript"] ?? entry["text"] ?? "").trim();
      const start = Number(entry["start_time_seconds"] ?? entry["start_time"] ?? 0);
      const end = Number(entry["end_time_seconds"] ?? entry["end_time"] ?? start);
      if (text) segments.push({ speaker, text, seconds: Math.max(0, end - start) });
    }
  }

  if (segments.length === 0 && flat.trim()) {
    segments.push({ speaker: "Speaker 1", text: flat.trim(), seconds: 0 });
  }
  return { state: "done", segments, transcript: flat.trim() };
}

/** Groups diarized segments per speaker and guesses the loudest talker is the user. */
export function groupSpeakers(segments: SpeakerSegment[]) {
  const map = new Map<string, { speaker: string; text: string; seconds: number }>();
  for (const s of segments) {
    const current = map.get(s.speaker) ?? { speaker: s.speaker, text: "", seconds: 0 };
    current.text = `${current.text} ${s.text}`.trim();
    current.seconds += s.seconds;
    map.set(s.speaker, current);
  }
  const list = [...map.values()].sort(
    (a, b) => b.seconds - a.seconds || b.text.length - a.text.length,
  );
  return list.map((entry) => ({
    ...entry,
    sample: entry.text
      .split(/(?<=[.!?])\s+/)
      .slice(0, 2)
      .join(" ")
      .slice(0, 220),
  }));
}
