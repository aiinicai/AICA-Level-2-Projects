import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      // Forward calls to the real mail server (server/index.mjs) so the
      // frontend can call fetch('/api/send-email') during `npm run dev`
      // without hitting CORS or needing a second origin.
      proxy: {
        '/api': {
          target: `http://localhost:${process.env.API_PORT || 5174}`,
          changeOrigin: true,
        },
      },
    },
  };
});
