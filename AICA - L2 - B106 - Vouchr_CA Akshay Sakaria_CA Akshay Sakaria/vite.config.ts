import { defineConfig, loadEnv, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { viteSingleFile } from 'vite-plugin-singlefile';
import { appendFileSync, readFileSync } from 'node:fs';
import { DEFAULT_MODELS, runTask, TASKS, type TaskName } from './supabase/functions/_shared/ai/tasks.ts';

/** LOCAL TESTING ONLY (`npm run dev`): runs the same AI tasks as the Supabase function, with GEMINI_API_KEY read from
 *  .env.local on this computer. The key stays in this Node process — it is never sent to the browser or into a build.
 *  Token use per call is appended to ai-dev-log.jsonl so real cost per bill can be measured. */
function aiDevProxy(env: Record<string, string>): Plugin {
  let today = '', used = 0;
  return {
    name: 'vouchr-ai-dev-proxy',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/__ai', async (req, res) => {
        const send = (code: number, body: unknown) => { res.statusCode = code; res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(body)); };
        const key = env.GEMINI_API_KEY;
        const models = { heavy: env.GEMINI_MODEL || DEFAULT_MODELS.heavy, fast: env.GEMINI_MODEL_FAST || DEFAULT_MODELS.fast };
        if (!/^(localhost|127\.0\.0\.1)(:\d+)?$/.test(req.headers.host ?? '')) return send(403, { error: 'local only' });
        if (req.method === 'GET') return send(200, { ready: !!key, model: models.heavy, fast: models.fast, paid: env.GEMINI_TIER === 'paid' });
        if (!key) return send(503, { error: 'GEMINI_API_KEY is not set in .env.local' });
        const chunks: Buffer[] = [];
        for await (const c of req) chunks.push(c as Buffer);
        let body: { model?: string; task: TaskName; role: 'super_admin' | 'client_admin' | 'sub_user'; ctx?: Record<string, unknown>; files?: { mime: string; data: string }[]; today: string };
        try { body = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { return send(400, { error: 'bad request' }); }
        const def = TASKS[body.task];
        if (!def) return send(400, { error: 'Unknown task' });
        if (!def.roles.includes(body.role)) return send(403, { error: 'Not allowed for your role' });
        if (today !== body.today) { today = body.today; used = 0; }
        if (++used > Number(env.AI_DAILY_LIMIT_PER_CLIENT || 200)) return send(429, { error: 'Daily AI limit reached' });
        try {
          // local testing only: compare models on the same input
          const use = body.model && [models.heavy, models.fast].includes(body.model) ? { heavy: body.model, fast: body.model } : models;
          const r = await runTask(key, use, body.task, body.ctx ?? {}, body.files ?? [], body.today);
          appendFileSync('ai-dev-log.jsonl', JSON.stringify({ at: new Date().toISOString(), task: body.task, model: r.model, inTok: r.inTok, outTok: r.outTok, doubts: r.doubts.length }) + '\n');
          send(200, r);
        } catch (err) {
          appendFileSync('ai-dev-log.jsonl', JSON.stringify({ at: new Date().toISOString(), task: body.task, error: String(err).slice(0, 300) }) + '\n');
          send(502, { error: String((err as Error).message ?? err).slice(0, 300) });
        }
      });
    }
  };
}

/** On-device bill reading files, served from this app under /ocr/ instead of a public CDN (no outside download, works
 *  offline once cached). Same versions as the installed tesseract.js packages. */
const OCR_FILES: Record<string, string> = {
  'ocr/worker.min.js': 'node_modules/tesseract.js/dist/worker.min.js',
  'ocr/core/tesseract-core-simd-lstm.wasm.js': 'node_modules/tesseract.js-core/tesseract-core-simd-lstm.wasm.js',
  'ocr/core/tesseract-core-lstm.wasm.js': 'node_modules/tesseract.js-core/tesseract-core-lstm.wasm.js',
  'ocr/lang/eng.traineddata.gz': 'node_modules/@tesseract.js-data/eng/4.0.0_best_int/eng.traineddata.gz'
};
function ocrAssets(): Plugin {
  return {
    name: 'vouchr-ocr-assets',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const key = (req.url ?? '').split('?')[0].replace(/^\//, '');
        if (!OCR_FILES[key]) return next();
        res.setHeader('Content-Type', key.endsWith('.gz') ? 'application/gzip' : 'text/javascript');
        res.end(readFileSync(OCR_FILES[key]));
      });
    },
    generateBundle() {
      for (const [fileName, src] of Object.entries(OCR_FILES)) this.emitFile({ type: 'asset', fileName, source: readFileSync(src) });
    }
  };
}

export default defineConfig(({ mode }) => ({
  // mode 'file' = one self-contained "Vouchr demo.html" that opens from a folder (see package.json build:file)
  ...(mode === 'file' ? { base: './', build: { outDir: 'dist-file', emptyOutDir: true } } : {}),
  plugins: [
    react(),
    aiDevProxy(loadEnv(mode, process.cwd(), '')),
    ...(mode === 'file' ? [viteSingleFile()] : [ocrAssets()]),
    VitePWA({
      disable: mode === 'file',
      registerType: 'autoUpdate',
      includeAssets: ['icon.svg'],
      manifest: {
        name: 'Vouchr — Expense Recorder',
        short_name: 'Vouchr',
        description: 'Snap, record and track business expenses with GST & TDS compliance.',
        theme_color: '#0f2a44',
        background_color: '#f6f4ef',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' }
        ]
      },
      workbox: {
        navigateFallback: '/index.html',
        importScripts: ['push-sw.js'], // phone notifications (public/push-sw.js)
        // heavy readers are NOT part of the install: fetched on first use (or the opt-in download) and then kept offline
        globIgnores: ['**/ocr/**', '**/pdf.worker*'],
        navigateFallbackDenylist: [/^\/__ai/],
        // fonts are fetched only for the scripts a page uses (Latin / Devanagari) and then kept for offline use
        runtimeCaching: [
          { urlPattern: ({ request }) => request.destination === 'font', handler: 'CacheFirst', options: { cacheName: 'vouchr-fonts', expiration: { maxEntries: 30, maxAgeSeconds: 60 * 60 * 24 * 365 } } },
          { urlPattern: ({ url }) => url.pathname.startsWith('/ocr/') || /\/assets\/pdf\.worker/.test(url.pathname), handler: 'CacheFirst', options: { cacheName: 'vouchr-readers', expiration: { maxEntries: 12 } } }
        ]
      }
    })
  ],
  test: { environment: 'node' }
}));
