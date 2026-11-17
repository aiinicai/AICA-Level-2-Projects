import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import { handleCalendarEnrich, handleMsmeExtract, handleAifAnalyze } from './src/server/geminiService.ts';
import { sendPasswordResetOtpEmail, verifyPasswordResetOtp } from './src/server/emailService.ts';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

app.use(express.json({ limit: '25mb' }));

app.post('/api/calendar/enrich', async (req, res) => {
  const year = req.body.year || new Date().getFullYear();
  const month = req.body.month || new Date().getMonth() + 1;
  const result = await handleCalendarEnrich(year, month);
  res.json(result);
});

app.post('/api/msme/extract', async (req, res) => {
  const { documentsSummary, fixedDefaults } = req.body;
  const result = await handleMsmeExtract(documentsSummary, fixedDefaults);
  res.json(result);
});

app.post('/api/aif/analyze', async (req, res) => {
  const { documentsSummary, projectDetails } = req.body;
  const result = await handleAifAnalyze(documentsSummary, projectDetails);
  res.json(result);
});

app.post('/api/auth/reset-password-request', async (req, res) => {
  const { email, role } = req.body;
  const result = await sendPasswordResetOtpEmail(email, role);
  res.json(result);
});

app.post('/api/auth/verify-reset-otp', (req, res) => {
  const { role, otp } = req.body;
  const result = verifyPasswordResetOtp(role, otp);
  res.json(result);
});

app.use(express.static(path.join(__dirname, 'dist')));

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`CA Office Super App running on port ${PORT}`);
});
