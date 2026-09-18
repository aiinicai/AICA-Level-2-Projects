// Single-file build: everything inlined into one .html (no server, no licensing).
// Build:  npx vite build --config vite.singlefile.config.ts
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

export default defineConfig(() => ({
  plugins: [react(), tailwindcss(), viteSingleFile()],
  define: {
    'import.meta.env.VITE_SINGLE_FILE': JSON.stringify('true'),
  },
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'release-html',
    chunkSizeWarningLimit: 10000,
  },
}));
