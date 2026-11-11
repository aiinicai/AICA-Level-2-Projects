// Bundles tests/engine.test.ts with esbuild (installed with Vite) and runs it.
import { build } from 'esbuild';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(os.tmpdir(), `gsr-engine-test-${process.pid}.mjs`);
await build({
  entryPoints: [path.join(here, 'engine.test.ts')],
  bundle: true,
  platform: 'node',
  format: 'esm',
  outfile: out,
  logLevel: 'warning',
});
await import(pathToFileURL(out).href);
