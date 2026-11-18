import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  root: 'src',
  base: './',
  plugins: [react()],
  resolve: { alias: { '@shared': path.resolve(__dirname, 'src/shared') } },
  build: { outDir: path.resolve(__dirname, '../app/static'), emptyOutDir: true, chunkSizeWarningLimit: 1200 },
  server: { port: 5173, proxy: { '/api': { target: `http://127.0.0.1:${process.env.PORT ?? 8787}`, changeOrigin: false } } },
});
