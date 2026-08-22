/**
 * Hard, code-level check for "is there actually speech from this user?".
 *
 * This runs BEFORE any analysis step (client-side first, and again on the
 * server as a backstop), so a silent or near-empty recording never produces
 * a reflection. Nothing here depends on a model deciding for itself.
 */

export const MIN_SPEECH_SECONDS = 1.5;
export const MIN_SPEECH_WORDS = 12;

export const NO_SPEECH_MESSAGE =
  "No speech was detected from your side of this conversation, so there's nothing to reflect back. Try recording again.";

export type SpeechCheck = {
  ok: boolean;
  voicedSeconds: number;
  words: number;
};

function decodeBase64(base64: string): Uint8Array {
  if (typeof atob === "function") {
    const raw = atob(base64);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
    return out;
  }
  // Server runtime
  return new Uint8Array(Buffer.from(base64, "base64"));
}

type Pcm = { samples: Float32Array; rate: number };

/** Parses a 16-bit PCM WAV. Returns null when the bytes aren't a WAV we can read. */
function parseWav(bytes: Uint8Array): Pcm | null {
  if (bytes.length < 44) return null;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const tag = (offset: number) =>
    String.fromCharCode(
      bytes[offset] ?? 0,
      bytes[offset + 1] ?? 0,
      bytes[offset + 2] ?? 0,
      bytes[offset + 3] ?? 0,
    );
  if (tag(0) !== "RIFF" || tag(8) !== "WAVE") return null;

  let offset = 12;
  let rate = 16000;
  let bits = 16;
  let channels = 1;
  let dataStart = -1;
  let dataLength = 0;

  while (offset + 8 <= bytes.length) {
    const id = tag(offset);
    const size = view.getUint32(offset + 4, true);
    if (id === "fmt ") {
      channels = view.getUint16(offset + 10, true) || 1;
      rate = view.getUint32(offset + 12, true) || 16000;
      bits = view.getUint16(offset + 22, true) || 16;
    } else if (id === "data") {
      dataStart = offset + 8;
      dataLength = Math.min(size, bytes.length - dataStart);
      break;
    }
    offset += 8 + size + (size % 2);
  }
  if (dataStart < 0 || bits !== 16) return null;

  const frames = Math.floor(dataLength / 2);
  const samples = new Float32Array(Math.floor(frames / channels));
  for (let i = 0; i < samples.length; i += 1) {
    samples[i] = view.getInt16(dataStart + i * channels * 2, true) / 0x8000;
  }
  return { samples, rate };
}

/** Rough voice-activity duration using per-frame energy against the noise floor. */
export function voicedSecondsOf(audioBase64: string): number {
  let pcm: Pcm | null = null;
  try {
    pcm = parseWav(decodeBase64(audioBase64));
  } catch {
    pcm = null;
  }
  if (!pcm || pcm.samples.length === 0) return 0;

  const { samples, rate } = pcm;
  const frame = Math.max(1, Math.round(rate * 0.03));
  const energies: number[] = [];
  for (let start = 0; start + frame <= samples.length; start += frame) {
    let sum = 0;
    for (let i = start; i < start + frame; i += 1) {
      const v = samples[i] ?? 0;
      sum += v * v;
    }
    energies.push(Math.sqrt(sum / frame));
  }
  if (energies.length === 0) return 0;

  const sorted = [...energies].sort((a, b) => a - b);
  const floor = sorted[Math.floor(sorted.length * 0.1)] ?? 0;
  // 95th percentile instead of the absolute max, so one click doesn't set the bar.
  const peak = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))] ?? 0;
  if (peak < 0.004) return 0; // whole clip really is silence
  const threshold = Math.max(0.003, floor * 1.8, peak * 0.08);
  const voiced = energies.filter((e) => e >= threshold).length;
  return (voiced * frame) / rate;
}

export function checkSpokenAudio(audioBase64: string): SpeechCheck {
  const voicedSeconds = voicedSecondsOf(audioBase64);
  return { ok: voicedSeconds >= MIN_SPEECH_SECONDS, voicedSeconds, words: 0 };
}

export function checkWrittenText(text: string): SpeechCheck {
  const trimmed = text.trim();
  const words = trimmed ? trimmed.split(/\s+/).length : 0;
  return { ok: words >= MIN_SPEECH_WORDS, voicedSeconds: 0, words };
}

export class NoSpeechError extends Error {
  constructor() {
    super(NO_SPEECH_MESSAGE);
    this.name = "NoSpeechError";
  }
}
