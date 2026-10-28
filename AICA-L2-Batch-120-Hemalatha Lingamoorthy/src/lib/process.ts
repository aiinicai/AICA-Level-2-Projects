import { computeMetrics, decodeBlob, encodeWavBase64, toMono16k, wpm } from "./audio";
import { saveSession, type Session } from "./db";
import { analyzeSpeech } from "./analysis.functions";

export async function processRecording(opts: {
  blob: Blob;
  mime: string;
  mode: string;
  title: string;
  referenceText?: string | undefined;
}): Promise<Session> {
  let buf: AudioBuffer;
  try {
    buf = await decodeBlob(opts.blob);
  } catch {
    throw new Error("We couldn't read that recording. Please try again.");
  }
  const mono = toMono16k(buf);
  if (buf.duration < 1) throw new Error("That was too short — try speaking for a few seconds.");
  const metrics = computeMetrics(mono, 16000);
  const res = await analyzeSpeech({
    data: { audioBase64: encodeWavBase64(mono), durationSec: buf.duration, mode: opts.mode, referenceText: opts.referenceText },
  });
  if (!res.ok) throw new Error(res.error);
  const a = res.analysis;
  const count = a.words.length || a.verbatim_transcript.split(/\s+/).filter(Boolean).length;
  const session: Session = {
    id: crypto.randomUUID(),
    createdAt: Date.now(),
    mode: opts.mode,
    title: opts.title,
    referenceText: opts.referenceText,
    audio: opts.blob,
    mimeType: opts.mime,
    metrics,
    analysis: a,
    wpm: wpm(count, buf.duration),
  };
  await saveSession(session);
  return session;
}
