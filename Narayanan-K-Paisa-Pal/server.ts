import express from 'express';
import path from 'path';
import fs from 'fs';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';

async function startServer() {
  const app = express();
  const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

  // JSON body parser with generous limit for document scans and PDFs
  app.use(express.json({ limit: '35mb' }));

  // AI-powered document scanning endpoint via Gemini API
  app.post('/api/scan-document', async (req, res) => {
    try {
      const { fileBase64, mimeType = 'application/pdf', fileName = '', kind = 'auto' } = req.body;

      if (!fileBase64) {
        return res.status(400).json({ error: 'Missing fileBase64 data' });
      }

      if (!process.env.GEMINI_API_KEY) {
        return res.status(503).json({
          error: 'Gemini API key is not configured in environment. Using client fallback parser.',
        });
      }

      const ai = new GoogleGenAI();

      const fnLower = (fileName || '').toLowerCase();
      let hint = '';
      if (
        fnLower.includes('passport') ||
        fnLower.includes('licen') ||
        fnLower.includes('dl') ||
        fnLower.includes('aadhaar') ||
        fnLower.includes('aadhar') ||
        fnLower.includes('pan') ||
        fnLower.includes('voter') ||
        fnLower.includes('rc') ||
        fnLower.includes('id')
      ) {
        hint = 'This document appears to be an official ID or personal record (Passport, Licence, Aadhaar, PAN, RC). Classify as "rec".';
      } else if (
        fnLower.includes('sbi') ||
        fnLower.includes('gramin') ||
        fnLower.includes('deposit') ||
        fnLower.includes('fd') ||
        fnLower.includes('fund') ||
        fnLower.includes('share') ||
        fnLower.includes('bond')
      ) {
        hint = 'This document appears to be a bank deposit or investment (FD receipt, bond, mutual fund). Classify as "inv".';
      }

      // Helper to clean and format dates to YYYY-MM-DD
      const normalizeDate = (val: any): string => {
        if (!val || typeof val !== 'string') return '';
        const s = val.trim();
        if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
        // DD/MM/YYYY or DD-MM-YYYY
        let m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})/);
        if (m) {
          const day = m[1].padStart(2, '0');
          const mon = m[2].padStart(2, '0');
          return `${m[3]}-${mon}-${day}`;
        }
        // DD-MMM-YYYY e.g. 30-DEC-2022
        const monthMap: Record<string, string> = {
          jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06',
          jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12'
        };
        m = s.match(/^(\d{1,2})[\s\-]+([A-Za-z]{3})[a-z]*[\s\-]+(\d{4})/i);
        if (m) {
          const day = m[1].padStart(2, '0');
          const mon = monthMap[m[2].toLowerCase()] || '01';
          return `${m[3]}-${mon}-${day}`;
        }
        return s;
      };

      const normalizeNum = (val: any): number | undefined => {
        if (val == null) return undefined;
        if (typeof val === 'number') return isNaN(val) ? undefined : val;
        const n = parseFloat(String(val).replace(/[^0-9.]/g, ''));
        return isNaN(n) ? undefined : n;
      };

      const prompt = `You are an expert document analyzer and scanner for Indian personal finance, banking, tax, and identity documents.
Analyze this uploaded document (${fileName}) and classify it accurately:
1. 'rec' for Official Records, Identity documents (Passport, Driving Licence, Vehicle RC, Aadhaar, PAN card, Voter ID, Insurance policy certificate)
2. 'inv' for Bank Investments (Fixed Deposits, Term Deposits, Mutual Funds, SGB, Shares, Bonds)
3. 'due' for Bills & Recurring Dues (Car/Health Insurance Renewal, Electricity, Water, Loan EMI, Credit card, LPG cylinder)

Return ONLY a valid raw JSON object (no markdown, no backtick wrappers) matching these schemas:

If 'rec':
{
  "detectedKind": "rec",
  "title": "Document title e.g. 'Passport - Nila Menon' or 'Driving Licence'",
  "type": "passport" | "licence" | "vehicle" | "policy" | "bank" | "id" | "other",
  "holder": "Person full name",
  "number": "Document or ID number",
  "issued": "YYYY-MM-DD or empty string",
  "expires": "YYYY-MM-DD or empty string",
  "notes": "Key details from document"
}

If 'inv':
{
  "detectedKind": "inv",
  "name": "Investment name e.g. 'Federal Bank Term Deposit' or 'Mutual Fund Portfolio'",
  "type": "fd" | "rd" | "mf" | "stocks" | "bond" | "gold" | "other",
  "institution": "Bank or fund house name",
  "holder": "Account holder full name",
  "ref": "Account or folio number",
  "invested": numeric principal or total cost,
  "current": numeric current or maturity value,
  "rate": annual interest rate in percent as a number,
  "start": "YYYY-MM-DD or empty string",
  "maturity": "YYYY-MM-DD or empty string",
  "notes": "Key details"
}

If 'due':
{
  "detectedKind": "due",
  "name": "Bill or obligation name e.g. 'Car Insurance Renewal' or 'Electricity Bill'",
  "category": "emi" | "insurance" | "mediclaim" | "vehicle" | "utility" | "lpg",
  "provider": "Company / provider / insurer name",
  "holder": "Policyholder or customer name",
  "amount": numeric payment amount,
  "due": "YYYY-MM-DD",
  "ref": "Policy / account / registration number",
  "freq": "monthly" | "annual" | "quarterly" | "once",
  "notes": "Key details"
}`;

      // Multi-model resilience: try fast flash-lite, then fallback to flash
      const candidateModels = ['gemini-3.1-flash-lite', 'gemini-3.8-flash'];
      let rawText = '';
      let usedModel = '';

      for (const model of candidateModels) {
        try {
          const genPromise = ai.models.generateContent({
            model,
            contents: [
              {
                role: 'user',
                parts: [
                  {
                    inlineData: {
                      mimeType,
                      data: fileBase64,
                    },
                  },
                  {
                    text: prompt,
                  },
                ],
              },
            ],
          });

          const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error(`Timeout with model ${model}`)), 40000)
          );

          const response: any = await Promise.race([genPromise, timeoutPromise]);
          rawText = response.text || '';
          usedModel = model;
          if (rawText) break;
        } catch (err: any) {
          console.warn(`Model ${model} failed, trying next:`, err.message || err);
        }
      }

      if (!rawText) {
        throw new Error('AI scanner models unavailable. Using local fallback parser.');
      }

      // Strip markdown code fences if present
      const cleanJson = rawText
        .replace(/^```json\s*/i, '')
        .replace(/^```\s*/i, '')
        .replace(/\s*```$/i, '')
        .trim();

      const parsedData = JSON.parse(cleanJson);

      // Normalize dates and numbers
      if (parsedData.issued) parsedData.issued = normalizeDate(parsedData.issued);
      if (parsedData.expires) parsedData.expires = normalizeDate(parsedData.expires);
      if (parsedData.start) parsedData.start = normalizeDate(parsedData.start);
      if (parsedData.maturity) parsedData.maturity = normalizeDate(parsedData.maturity);
      if (parsedData.due) parsedData.due = normalizeDate(parsedData.due);

      if (parsedData.invested != null) parsedData.invested = normalizeNum(parsedData.invested);
      if (parsedData.current != null) parsedData.current = normalizeNum(parsedData.current);
      if (parsedData.rate != null) parsedData.rate = normalizeNum(parsedData.rate);
      if (parsedData.amount != null) parsedData.amount = normalizeNum(parsedData.amount);

      // Verify or enforce detectedKind based on document content & hints
      const combinedMeta = `${fileName} ${parsedData.title || ''} ${parsedData.name || ''} ${parsedData.notes || ''}`.toLowerCase();
      
      if (combinedMeta.includes('passport') || String(parsedData.type).toLowerCase() === 'passport') {
        parsedData.detectedKind = 'rec';
        parsedData.type = 'passport';
        parsedData.title = parsedData.title || (parsedData.holder ? `Passport - ${parsedData.holder}` : 'Passport');
      } else if (combinedMeta.includes('pan') || (parsedData.title && /pan\b/i.test(parsedData.title))) {
        parsedData.detectedKind = 'rec';
        parsedData.type = 'id';
        parsedData.title = parsedData.title || (parsedData.holder ? `PAN Card - ${parsedData.holder}` : 'PAN Card');
        parsedData.expires = '';
      } else if (combinedMeta.includes('car insurance') || combinedMeta.includes('motor insurance') || combinedMeta.includes('package policy')) {
        // Car insurance: if requested under due dates, format as a vehicle insurance renewal due
        if (kind === 'due') {
          parsedData.detectedKind = 'due';
          parsedData.category = 'vehicle';
          parsedData.name = parsedData.name || 'Motor Insurance Renewal';
          if (!parsedData.due && parsedData.expires) parsedData.due = parsedData.expires;
          if (!parsedData.due && parsedData.maturity) parsedData.due = parsedData.maturity;
        } else if (kind === 'rec') {
          parsedData.detectedKind = 'rec';
          parsedData.type = 'vehicle';
          parsedData.title = parsedData.title || 'Motor Insurance Policy';
        }
      } else if (!parsedData.detectedKind) {
        parsedData.detectedKind = kind !== 'auto' ? kind : 'due';
      }

      return res.json({
        success: true,
        data: parsedData,
        detectedKind: parsedData.detectedKind,
        raw: rawText,
        model: usedModel,
      });
    } catch (err: any) {
      console.error('Error in /api/scan-document:', err);
      return res.status(500).json({
        error: err.message || 'Failed to process document with AI scanner',
      });
    }
  });

  // Serve static assets from public/assets
  app.use('/assets', express.static(path.resolve('public/assets')));

  // In development, hook Vite middleware
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    // In production, serve dist folder
    app.use(express.static(path.resolve('dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve('dist/index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server listening on port ${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
