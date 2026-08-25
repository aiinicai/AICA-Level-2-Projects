/**
 * Mic capture that always produces a complete, decodable 16 kHz mono WAV file.
 * Deliberately avoids MediaRecorder fragments (headerless chunks fail upstream).
 */

const TARGET_RATE = 16000;

export type Recorder = {
  stop: () => Promise<{ blob: Blob; base64: string; seconds: number; captureFailed: boolean }>;
  cancel: () => void;
  level: () => number;
};

/** iOS Safari (including iPadOS desktop-mode) needs playback-free keep-alive. */
function isIos() {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  return /iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
}

/**
 * Keeps the capture alive when the screen sleeps or the user switches apps.
 * A screen wake lock plus resume-on-wake everywhere. The silent looping media
 * element is used only off-iOS: on iOS Safari, starting an <audio> element
 * flips the page audio session to playback and the mic then feeds the graph
 * pure silence, which is what made recordings read as "no speech".
 */
function keepAlive(ctx: AudioContext) {
  let lock: { release: () => Promise<void> } | null = null;
  const silence =
    "data:audio/wav;base64,UklGRiwAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQgAAAAAAAAAAAAAAA==";
  const audio = isIos() || typeof Audio === "undefined" ? null : new Audio(silence);
  if (audio) {
    audio.loop = true;
    audio.volume = 0.0001;
    audio.setAttribute("playsinline", "true");
    void audio.play().catch(() => undefined);
  }

  const onVisible = () => {
    if (ctx.state === "suspended") void ctx.resume().catch(() => undefined);
    if (audio && audio.paused) void audio.play().catch(() => undefined);
  };
  document.addEventListener("visibilitychange", onVisible);
  window.addEventListener("focus", onVisible);
  window.addEventListener("pageshow", onVisible);
  window.addEventListener("resume", onVisible);

  const nav = navigator as Navigator & {
    wakeLock?: { request: (t: "screen") => Promise<{ release: () => Promise<void> }> };
  };
  void nav.wakeLock
    ?.request("screen")
    .then((sentinel) => {
      lock = sentinel;
    })
    .catch(() => undefined);

  return () => {
    document.removeEventListener("visibilitychange", onVisible);
    window.removeEventListener("focus", onVisible);
    window.removeEventListener("pageshow", onVisible);
    window.removeEventListener("resume", onVisible);
    if (audio) {
      audio.pause();
      audio.src = "";
    }
    void lock?.release().catch(() => undefined);
  };
}

export async function startRecorder(): Promise<Recorder> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true },
  });
  const ctx = new AudioContext();
  // iOS starts contexts suspended; without this the processor never fires.
  if (ctx.state === "suspended") await ctx.resume().catch(() => undefined);
  const releaseKeepAlive = keepAlive(ctx);
  const source = ctx.createMediaStreamSource(stream);
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  const node = ctx.createScriptProcessor(4096, 1, 1);
  const chunks: Float32Array[] = [];
  node.onaudioprocess = (e) => {
    chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  };
  // Muted sink keeps the graph pulling on iOS without any audible playback.
  const sink = ctx.createGain();
  sink.gain.value = 0;
  source.connect(analyser);
  source.connect(node);
  node.connect(sink);
  sink.connect(ctx.destination);

  const bins = new Uint8Array(analyser.frequencyBinCount);

  const teardown = () => {
    releaseKeepAlive();
    stream.getTracks().forEach((t) => t.stop());
    try {
      node.disconnect();
      source.disconnect();
      analyser.disconnect();
      sink.disconnect();
    } catch {
      /* already torn down */
    }
  };

  return {
    level() {
      analyser.getByteFrequencyData(bins);
      let sum = 0;
      for (const b of bins) sum += b;
      return Math.min(1, sum / bins.length / 90);
    },
    cancel() {
      teardown();
      void ctx.close();
    },
    async stop() {
      teardown();
      const rate = ctx.sampleRate;
      await ctx.close();
      const merged = merge(chunks);
      const down = downsample(merged, rate, TARGET_RATE);
      const blob = encodeWav(down, TARGET_RATE);
      // No frames at all, or every sample exactly zero: the mic never fed the
      // graph. That is a capture failure, not a silent speaker.
      const captureFailed = merged.length === 0 || !merged.some((v) => v !== 0);
      return {
        blob,
        base64: await toBase64(blob),
        seconds: down.length / TARGET_RATE,
        captureFailed,
      };
    },
  };
}

function merge(chunks: Float32Array[]) {
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const out = new Float32Array(total);
  let i = 0;
  for (const c of chunks) {
    out.set(c, i);
    i += c.length;
  }
  return out;
}

function downsample(input: Float32Array, from: number, to: number) {
  if (to >= from) return input;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j++) sum += input[j] ?? 0;
    out[i] = sum / Math.max(1, end - start);
  }
  return out;
}

function encodeWav(samples: Float32Array, rate: number) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const str = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };
  str(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  str(8, "WAVE");
  str(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  str(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i] ?? 0));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return new Blob([buffer], { type: "audio/wav" });
}

export function toBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read audio"));
    reader.onload = () => {
      const result = String(reader.result);
      resolve(result.slice(result.indexOf(",") + 1));
    };
    reader.readAsDataURL(blob);
  });
}

export function formatClock(seconds: number) {
  const s = Math.floor(seconds);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
