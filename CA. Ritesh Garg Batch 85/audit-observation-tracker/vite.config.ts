import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';
import {defineConfig} from 'vite';

const fixCommonjsSpaceBug = () => ({
  name: 'fix-commonjs-space-bug',
  enforce: 'pre' as const,
  resolveId(id: string, importer?: string) {
    const cleanId = id ? id.trim().replace(/\?.*$/, '') : '';
    if (cleanId.includes('internals/') || (importer && importer.includes('internals/'))) {
      let baseDir = path.resolve(__dirname, 'node_modules/core-js/modules');
      if (importer) {
        const cleanImporter = importer.trim().replace(/\?.*$/, '');
        if (fs.existsSync(cleanImporter)) {
          baseDir = path.dirname(cleanImporter);
        }
      }
      const target = path.resolve(baseDir, cleanId);
      const withExt = target.endsWith('.js') ? target : target + '.js';
      if (fs.existsSync(withExt)) {
        return withExt;
      }
    }
    return null;
  }
});

export default defineConfig(() => {
  return {
    plugins: [fixCommonjsSpaceBug(), react(), tailwindcss()],
    resolve: {
      alias: [
        { find: '@', replacement: path.resolve(__dirname, '.') },
        { find: 'jspdf', replacement: path.resolve(__dirname, 'node_modules/jspdf/dist/jspdf.umd.min.js') },
        { find: /^core-js\/.*/, replacement: path.resolve(__dirname, 'src/empty-shim.js') },
        { find: 'core-js', replacement: path.resolve(__dirname, 'src/empty-shim.js') },
      ],
    },
    optimizeDeps: {
      include: ['docx', 'xlsx', 'jspdf', 'jspdf-autotable', 'file-saver'],
    },
    build: {
      commonjsOptions: {
        include: [/node_modules/],
        transformMixedEsModules: true,
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modifyâ€”file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
  };
});
