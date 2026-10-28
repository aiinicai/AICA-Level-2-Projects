export const MAX_SECONDS = 300;

export function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  for (const t of ["audio/mp4", "audio/webm;codecs=opus", "audio/webm", "audio/aac"]) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return "";
}

export async function decodeBlob(blob: Blob): Promise<AudioBuffer> {
  const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new Ctx();
  try {
    return await ctx.decodeAudioData(await blob.arrayBuffer());
  } finally {
    ctx.close();
  }
}

export function toMono16k(buf: AudioBuffer): Float32Array {
  const src = buf.getChannelData(0);
  const ratio = buf.sampleRate / 16000;
  const out = new Float32Array(Math.floor(src.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const s = Math.floor(i * ratio), e = Math.min(src.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = s; j < e; j++) sum += src[j]!;
    out[i] = sum / Math.max(1, e - s);
  }
  return out;
}

export function encodeWavBase64(samples: Float32Array, rate = 16000): string {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buffer);
  const w = (o: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  w(36, "data"); v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]!));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  const bytes = new Uint8Array(buffer);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

export interface Pause { start: number; duration: number }
export interface LocalMetrics {
  duration: number;
  pauses: Pause[];
  pauseCount: number;
  avgPause: number;
  longestPause: number;
  shortPauses: number;
  naturalPauses: number;
  longPauses: number;
  volumeVariation: number; // coefficient of variation of voiced RMS
  monotone: boolean;
  rmsTimeline: number[]; // per 100ms
}

/** Pure analysis of a mono sample array — exported for tests. */
export function computeMetrics(samples: Float32Array, rate: number): LocalMetrics {
  const frame = Math.floor(rate * 0.05); // 50ms
  const rms: number[] = [];
  for (let i = 0; i + frame <= samples.length; i += frame) {
    let s = 0;
    for (let j = i; j < i + frame; j++) s += samples[j]! * samples[j]!;
    rms.push(Math.sqrt(s / frame));
  }
  const sorted = [...rms].sort((a, b) => a - b);
  const noise = sorted[Math.floor(sorted.length * 0.1)] ?? 0;
  const peak = sorted[Math.floor(sorted.length * 0.95)] ?? 0;
  const threshold = Math.max(0.008, noise + (peak - noise) * 0.15);
  const frameSec = frame / rate;
  const duration = samples.length / rate;

  const pauses: Pause[] = [];
  let runStart = -1;
  const firstVoice = rms.findIndex((r) => r >= threshold);
  let lastVoice = -1;
  for (let i = rms.length - 1; i >= 0; i--) if (rms[i]!! >= threshold) { lastVoice = i; break; }
  for (let i = Math.max(0, firstVoice); i <= lastVoice; i++) {
    const silent = rms[i]! < threshold;
    if (silent && runStart < 0) runStart = i;
    if (!silent && runStart >= 0) {
      const d = (i - runStart) * frameSec;
      if (d >= 0.25) pauses.push({ start: runStart * frameSec, duration: d });
      runStart = -1;
    }
  }
  const durs = pauses.map((p) => p.duration);
  const voiced = rms.filter((r) => r >= threshold);
  const mean = voiced.reduce((a, b) => a + b, 0) / Math.max(1, voiced.length);
  const sd = Math.sqrt(voiced.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(1, voiced.length));
  const cv = mean ? sd / mean : 0;
  const timeline: number[] = [];
  for (let i = 0; i < rms.length; i += 2) timeline.push(Math.round(((rms[i]!! + (rms[i + 1] ?? 0)) / 2) * 1000) / 1000);

  return {
    duration,
    pauses,
    pauseCount: pauses.length,
    avgPause: durs.length ? durs.reduce((a, b) => a + b, 0) / durs.length : 0,
    longestPause: durs.length ? Math.max(...durs) : 0,
    shortPauses: durs.filter((d) => d < 0.5).length,
    naturalPauses: durs.filter((d) => d >= 0.5 && d <= 1.5).length,
    longPauses: durs.filter((d) => d > 1.5).length,
    volumeVariation: Math.round(cv * 100) / 100,
    monotone: voiced.length > 20 && cv < 0.35,
    rmsTimeline: timeline,
  };
}

/** WPM in 15-second windows from word start times. */
export function paceSeries(words: { start: number }[], duration: number, win = 15) {
  const out: { t: number; wpm: number }[] = [];
  for (let s = 0; s < duration; s += win) {
    const e = Math.min(duration, s + win);
    if (e - s < 4) break;
    const n = words.filter((w) => w.start >= s && w.start < e).length;
    out.push({ t: Math.round(s), wpm: Math.round((n / (e - s)) * 60) });
  }
  return out;
}

export function wpm(wordCount: number, duration: number) {
  return duration > 0 ? Math.round((wordCount / duration) * 60) : 0;
}

export function paceLabel(w: number) {
  if (w < 130) return "slow";
  if (w > 160) return "fast";
  return "ideal";
}
