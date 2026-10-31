import { defineConfig } from 'vite';
export default defineConfig({server:{port:5173,proxy:{'/api':'http://127.0.0.1:5080'}},build:{outDir:'dist'}});
