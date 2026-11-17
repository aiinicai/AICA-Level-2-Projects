import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig, Plugin } from 'vite';
import { handleCalendarEnrich, handleMsmeExtract, handleAifAnalyze } from './src/server/geminiService.ts';
import { sendPasswordResetOtpEmail, verifyPasswordResetOtp } from './src/server/emailService.ts';

function apiPlugin(): Plugin {
  return {
    name: 'ca-office-api-plugin',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = req.url?.split('?')[0];

        if (url?.startsWith('/api/')) {
          let body = '';
          req.on('data', chunk => {
            body += chunk;
          });

          req.on('end', async () => {
            let parsedBody: any = {};
            try {
              if (body) parsedBody = JSON.parse(body);
            } catch (e) {
              parsedBody = {};
            }

            res.setHeader('Content-Type', 'application/json');

            try {
              if (url === '/api/calendar/enrich') {
                const year = parsedBody.year || new Date().getFullYear();
                const month = parsedBody.month || new Date().getMonth() + 1;
                const result = await handleCalendarEnrich(year, month);
                res.end(JSON.stringify(result));
                return;
              }

              if (url === '/api/msme/extract') {
                const docSummary = parsedBody.documentsSummary || '';
                const fixedDefaults = parsedBody.fixedDefaults || {};
                const result = await handleMsmeExtract(docSummary, fixedDefaults);
                res.end(JSON.stringify(result));
                return;
              }

              if (url === '/api/aif/analyze') {
                const docSummary = parsedBody.documentsSummary || '';
                const projectDetails = parsedBody.projectDetails || {};
                const result = await handleAifAnalyze(docSummary, projectDetails);
                res.end(JSON.stringify(result));
                return;
              }

              if (url === '/api/auth/reset-password-request') {
                const { email, role } = parsedBody;
                const result = await sendPasswordResetOtpEmail(email, role);
                res.end(JSON.stringify(result));
                return;
              }

              if (url === '/api/auth/verify-reset-otp') {
                const { role, otp } = parsedBody;
                const result = verifyPasswordResetOtp(role, otp);
                res.end(JSON.stringify(result));
                return;
              }

              res.statusCode = 404;
              res.end(JSON.stringify({ error: 'Endpoint not found' }));
            } catch (err: any) {
              res.statusCode = 500;
              res.end(JSON.stringify({ error: err?.message || 'Server error' }));
            }
          });
          return;
        }

        next();
      });
    },
  };
}

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss(), apiPlugin()],
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
    },
  };
});
