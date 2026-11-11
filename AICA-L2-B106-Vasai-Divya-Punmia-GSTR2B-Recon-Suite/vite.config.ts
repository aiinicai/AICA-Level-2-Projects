import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  // Relative asset paths: works on localhost, a LAN IP, a domain, or behind a sub-path proxy
  base: './',
  build: { chunkSizeWarningLimit: 2500 },
  plugins: [react(), tailwindcss()],
});
