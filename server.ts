import express from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import * as XLSX from 'xlsx';
import crypto from 'crypto';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

  // Increase payload limit for base64 receipt photos
  app.use(express.json({ limit: '25mb' }));
  app.use(express.urlencoded({ extended: true, limit: '25mb' }));

  // Initialize Gemini AI SDK
  let ai: GoogleGenAI | null = null;
  try {
    ai = new GoogleGenAI();
  } catch (err) {
    console.warn('GoogleGenAI initialization warning:', err);
  }

  // Health check endpoint
  app.get('/api/health', (req, res) => {
    res.json({
      status: 'ok',
      service: 'DirhamTrack AI Full-Stack Server',
      geminiConfigured: Boolean(process.env.GEMINI_API_KEY || ai)
    });
  });

  // In-memory OTP storage for secure PIN recovery
  interface OtpRecord {
    otp: string;
    expiresAt: number;
    attempts: number;
    lastSentAt: number;
    verified?: boolean;
    resetToken?: string;
  }

  const otpStore = new Map<string, OtpRecord>();

  // Cleanup expired OTPs every 10 minutes
  setInterval(() => {
    const now = Date.now();
    for (const [email, record] of otpStore.entries()) {
      if (now > record.expiresAt + 15 * 60 * 1000) {
        otpStore.delete(email);
      }
    }
  }, 10 * 60 * 1000);

  // GET /api/auth/status - Check Resend Email API status
  app.get('/api/auth/status', (req, res) => {
    const resendKey = process.env.RESEND_API_KEY?.trim() || '';
    res.json({
      resendConfigured: Boolean(resendKey.length > 5 && resendKey.startsWith('re_')),
      fromEmail: process.env.RESEND_FROM_EMAIL || 'DirhamTrack Security <onboarding@resend.dev>'
    });
  });

  // POST /api/auth/send-otp - Deliver 6-digit OTP code using Resend Email API
  app.post('/api/auth/send-otp', async (req, res) => {
    try {
      const { email } = req.body;
      if (!email || typeof email !== 'string' || !email.includes('@') || !email.includes('.')) {
        return res.status(400).json({ success: false, error: 'Please enter a valid email address.' });
      }

      const normalizedEmail = email.trim().toLowerCase();
      const existing = otpStore.get(normalizedEmail);

      // Enforce 60-second cooldown between email sends
      if (existing && Date.now() - existing.lastSentAt < 60000) {
        const remainingSeconds = Math.ceil((60000 - (Date.now() - existing.lastSentAt)) / 1000);
        return res.status(429).json({
          success: false,
          error: `Please wait ${remainingSeconds}s before requesting another verification code.`,
          retryAfter: remainingSeconds
        });
      }

      // Generate cryptographically secure 6-digit OTP
      const otp = crypto.randomInt(100000, 1000000).toString();
      const expiresAt = Date.now() + 5 * 60 * 1000; // 5-minute validity

      otpStore.set(normalizedEmail, {
        otp,
        expiresAt,
        attempts: 0,
        lastSentAt: Date.now()
      });

      const resendApiKey = process.env.RESEND_API_KEY?.trim();
      if (!resendApiKey) {
        return res.status(503).json({
          success: false,
          error: 'Resend Email API key (RESEND_API_KEY) is not configured in the server environment (.env). Please provide your Resend API key to send real emails.',
          configured: false
        });
      }

      const fromEmail = process.env.RESEND_FROM_EMAIL || 'DirhamTrack Security <onboarding@resend.dev>';
      const emailHtml = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>DirhamTrack AI PIN Reset Code</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #020617; color: #f8fafc; margin: 0; padding: 24px; }
            .card { max-width: 480px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
            .badge { display: inline-block; background-color: rgba(20, 184, 166, 0.15); color: #2dd4bf; border: 1px solid rgba(20, 184, 166, 0.3); padding: 6px 14px; border-radius: 9999px; font-weight: 700; font-size: 13px; margin-bottom: 20px; }
            .title { font-size: 22px; font-weight: 800; color: #ffffff; margin-bottom: 8px; letter-spacing: -0.02em; }
            .subtitle { font-size: 13px; color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }
            .otp-container { background: #020617; border: 2px dashed #14b8a6; border-radius: 14px; text-align: center; padding: 24px; margin: 24px 0; }
            .otp-code { font-family: 'Courier New', Courier, monospace; font-size: 40px; font-weight: 900; letter-spacing: 10px; color: #2dd4bf; margin: 0; }
            .expiry-note { font-size: 12px; color: #f59e0b; margin-top: 10px; font-weight: 600; }
            .warning { font-size: 12px; color: #64748b; line-height: 1.6; margin-top: 24px; border-top: 1px solid #1e293b; padding-top: 18px; }
            .footer { font-size: 11px; color: #475569; text-align: center; margin-top: 28px; line-height: 1.5; }
          </style>
        </head>
        <body>
          <div class="card">
            <div class="badge">د.إ DirhamTrack AI Security</div>
            <div class="title">PIN Reset Verification Code</div>
            <div class="subtitle">A request was received to reset the security PIN for your DirhamTrack AI expense tracker. Use the 6-digit code below to verify your identity:</div>
            
            <div class="otp-container">
              <div class="otp-code">${otp}</div>
              <div class="expiry-note">⏱️ Code expires in 5 minutes (300 seconds)</div>
            </div>

            <div class="warning">
              <strong>Security Warning:</strong> Never share this code with anyone. DirhamTrack support or automated systems will never ask you for this OTP. If you did not initiate this PIN reset, your account is still protected by your existing PIN.
            </div>

            <div class="footer">
              DirhamTrack AI · Smart UAE Budget &amp; Bank Notification Interceptor<br/>
              Developed by Fakhruddin · Dubai, United Arab Emirates
            </div>
          </div>
        </body>
        </html>
      `;

      const resendRes = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${resendApiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          from: fromEmail,
          to: [normalizedEmail],
          subject: `DirhamTrack AI: ${otp} is your PIN reset code`,
          html: emailHtml
        })
      });

      if (!resendRes.ok) {
        const errorData = await resendRes.json().catch(() => ({}));
        console.error('Resend API HTTP error:', resendRes.status, errorData);
        let userFacingError = errorData.message || `Resend delivery failed with status ${resendRes.status}`;
        
        if (userFacingError.toLowerCase().includes('testing emails to your own email') || userFacingError.toLowerCase().includes('validation_error')) {
          userFacingError = `Resend Sandbox Restriction: On the free tier, emails can only be sent to your verified Resend account email address. To send to any recipient, verify your domain at resend.com/domains. (Details: ${userFacingError})`;
        }

        return res.status(resendRes.status).json({
          success: false,
          error: userFacingError,
          details: errorData
        });
      }

      const resendData = await resendRes.json();
      console.log(`[Resend OTP Delivered] to ${normalizedEmail}, Resend message id: ${resendData.id}`);

      return res.json({
        success: true,
        message: `6-digit verification code sent to ${normalizedEmail}`,
        resendId: resendData.id,
        expiresAt
      });

    } catch (err: any) {
      console.error('Error in /api/auth/send-otp:', err);
      return res.status(500).json({ success: false, error: err.message || 'Failed to dispatch OTP email' });
    }
  });

  // POST /api/auth/verify-otp - Verify 6-digit OTP code (5-minute expiry, max 5 attempts)
  app.post('/api/auth/verify-otp', (req, res) => {
    try {
      const { email, otp } = req.body;
      if (!email || !otp) {
        return res.status(400).json({ success: false, error: 'Email and 6-digit OTP code are required.' });
      }

      const normalizedEmail = email.trim().toLowerCase();
      const record = otpStore.get(normalizedEmail);

      if (!record) {
        return res.status(400).json({ success: false, error: 'No active OTP verification code found for this email. Please request a new code.' });
      }

      // Check 5-minute expiry
      if (Date.now() > record.expiresAt) {
        otpStore.delete(normalizedEmail);
        return res.status(400).json({ success: false, error: 'This verification code has expired (5-minute limit). Please request a new code.' });
      }

      // Rate limit failed verification attempts
      record.attempts += 1;
      if (record.attempts > 5) {
        otpStore.delete(normalizedEmail);
        return res.status(429).json({ success: false, error: 'Too many incorrect attempts (5/5). For your security, this code has been revoked. Please request a new OTP.' });
      }

      // Exact match check
      if (record.otp.trim() !== String(otp).trim()) {
        const remaining = 5 - record.attempts;
        return res.status(400).json({
          success: false,
          error: `Incorrect verification code. ${remaining} attempt(s) remaining before revocation.`
        });
      }

      // Mark verified & generate single-use reset token
      const resetToken = crypto.randomBytes(32).toString('hex');
      record.verified = true;
      record.resetToken = resetToken;
      record.expiresAt = Date.now() + 10 * 60 * 1000; // 10 minutes to complete new PIN entry

      return res.json({
        success: true,
        message: 'OTP verified successfully.',
        resetToken
      });

    } catch (err: any) {
      console.error('Error in /api/auth/verify-otp:', err);
      return res.status(500).json({ success: false, error: err.message || 'OTP verification failed' });
    }
  });

  // POST /api/auth/reset-pin - Update security PIN using validated reset token
  app.post('/api/auth/reset-pin', (req, res) => {
    try {
      const { email, resetToken, newPin } = req.body;
      if (!email || !resetToken || !newPin) {
        return res.status(400).json({ success: false, error: 'Missing required parameters (email, resetToken, newPin).' });
      }

      if (!/^\d{4}$/.test(String(newPin).trim())) {
        return res.status(400).json({ success: false, error: 'New PIN must be exactly 4 numeric digits.' });
      }

      const normalizedEmail = email.trim().toLowerCase();
      const record = otpStore.get(normalizedEmail);

      if (!record || !record.verified || record.resetToken !== resetToken) {
        return res.status(401).json({ success: false, error: 'Unauthorized or expired reset session. Please request a new OTP.' });
      }

      if (Date.now() > record.expiresAt) {
        otpStore.delete(normalizedEmail);
        return res.status(401).json({ success: false, error: 'Reset session has expired. Please request a new OTP.' });
      }

      // Clean up the verified token so it cannot be reused
      otpStore.delete(normalizedEmail);

      return res.json({
        success: true,
        message: 'PIN has been reset successfully.'
      });

    } catch (err: any) {
      console.error('Error in /api/auth/reset-pin:', err);
      return res.status(500).json({ success: false, error: err.message || 'PIN reset failed' });
    }
  });

  // POST /api/receipt/ocr - Extract receipt items, amounts & categories
  app.post('/api/receipt/ocr', async (req, res) => {
    try {
      const { imageBase64, mimeType } = req.body;
      if (!imageBase64) {
        return res.status(400).json({ error: 'Missing imageBase64 in request body' });
      }

      if (!ai) {
        try {
          ai = new GoogleGenAI();
        } catch (e) {
          return res.status(503).json({ error: 'Gemini AI not initialized on server' });
        }
      }

      // Strip standard data url prefixes if present
      const cleanBase64 = imageBase64.replace(/^data:image\/[a-zA-Z+]+;base64,/, '');

      const prompt = `You are an expert UAE receipt and bill OCR extractor.
Read the provided receipt or invoice image carefully and extract all individual purchased items.

Output JSON with this exact schema:
{
  "merchant": "string (e.g. Nesto Hypermarket, Carrefour, Lulu, ADNOC, Aster Pharmacy)",
  "date": "string (YYYY-MM-DD or today's date if not clearly visible)",
  "total": number (receipt total amount in AED),
  "currency": "AED",
  "items": [
    {
      "name": "string (item name / description)",
      "amount": number (item price in AED),
      "category": "Food & Groceries" | "Clothing" | "Fuel" | "Healthcare" | "Transport" | "Utilities" | "Telecom" | "Shopping" | "Entertainment" | "Other"
    }
  ]
}

CRITICAL RULES:
1. Do NOT calculate, process, or include any VAT or tax-related figures. No VAT items or deductions.
2. All item amounts must be numeric in AED.
3. Automatically categorize each item into the most appropriate category:
   - "Food & Groceries": for groceries, vegetables, fruits, rice, milk, bread, pantry, packaged food, supermarket goods.
   - "Clothing": for shirts, pants, t-shirts, shoes, apparel, fabrics, fashion accessories.
   - "Fuel": for petrol, special 95, super 98, diesel.
   - "Healthcare": for medicine, pharmacy, vitamins, clinic charges.
   - "Transport": for taxi, parking, tolls.
   - "Shopping": for electronics, home appliances, general merchandise.
4. Ensure the sum of item amounts equals the receipt total.`;

      const response = await ai.models.generateContent({
        model: 'gemini-3.8-flash',
        contents: [
          {
            inlineData: {
              data: cleanBase64,
              mimeType: mimeType || 'image/jpeg',
            },
          },
          prompt,
        ],
        config: {
          responseMimeType: 'application/json',
        },
      });

      const responseText = response.text || '';
      try {
        const parsed = JSON.parse(responseText);
        return res.json({ success: true, data: parsed });
      } catch (jsonErr) {
        const match = responseText.match(/\{[\s\S]*\}/);
        if (match) {
          const extracted = JSON.parse(match[0]);
          return res.json({ success: true, data: extracted });
        }
        return res.status(500).json({ error: 'Failed to parse AI OCR response', raw: responseText });
      }
    } catch (err: any) {
      console.error('OCR Endpoint error:', err);
      return res.status(500).json({ error: err.message || 'OCR processing failed' });
    }
  });

  // Helper to execute Python Bank Statement Processor & Reconciliation
  const runPythonStatement = (payload: any): Promise<any> => {
    return new Promise((resolve, reject) => {
      const pythonScript = path.resolve(__dirname, 'scripts', 'statement_processor.py');
      const child = spawn('python3', [pythonScript]);

      let stdout = '';
      let stderr = '';

      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      child.on('close', (code) => {
        if (code !== 0) {
          console.error(`Python statement script error (code ${code}):`, stderr);
          return reject(new Error(stderr || `Python statement process exited with code ${code}`));
        }
        try {
          const parsed = JSON.parse(stdout);
          resolve(parsed);
        } catch (err) {
          reject(new Error(`Failed to parse Python statement output: ${stdout}`));
        }
      });

      child.stdin.write(JSON.stringify(payload));
      child.stdin.end();
    });
  };

  // POST /api/statement/parse - AI-Powered Bank & Credit Card Statement Extraction
  app.post('/api/statement/parse', async (req, res) => {
    try {
      const { fileBase64, fileName, fileType, bankHint, accounts } = req.body;
      if (!fileBase64 && !req.body.csvText) {
        return res.status(400).json({ error: 'Missing fileBase64 or csvText in request body' });
      }

      if (!ai) {
        try {
          ai = new GoogleGenAI();
        } catch (e) {
          console.warn('Gemini AI initialization warning:', e);
        }
      }

      const cleanBase64 = (fileBase64 || '').replace(/^data:[^;]+;base64,/, '');
      const rawExt = (fileName || '').split('.').pop()?.toLowerCase();
      const detectedType = fileType || (rawExt === 'pdf' ? 'pdf' : (rawExt === 'csv' ? 'csv' : (rawExt === 'xlsx' || rawExt === 'xls' ? 'xlsx' : 'pdf')));

      let rawExtractedData: any = null;

      // Case 1: Excel (.xlsx, .xls)
      if (detectedType === 'xlsx' || rawExt === 'xlsx' || rawExt === 'xls') {
        try {
          const fileBuffer = Buffer.from(cleanBase64, 'base64');
          const workbook = XLSX.read(fileBuffer, { type: 'buffer' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const jsonRows = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as any[][];

          // Fast direct tabular extraction
          rawExtractedData = parseTabularRowsHeuristic(jsonRows, bankHint);

          // If tabular rows were extracted, we can use them directly
          if (!rawExtractedData.transactions || rawExtractedData.transactions.length === 0) {
            const csvText = XLSX.utils.sheet_to_csv(worksheet);
            if (ai && csvText.trim().length > 20) {
              const prompt = `You are an expert Document AI for UAE Bank Statements. Extract transactions to JSON from this CSV:\n${csvText.slice(0, 10000)}`;
              const geminiPromise = ai.models.generateContent({
                model: 'gemini-3.8-flash',
                contents: prompt,
                config: { responseMimeType: 'application/json' }
              });
              const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('AI timeout')), 10000));
              const geminiRes: any = await Promise.race([geminiPromise, timeoutPromise]);
              rawExtractedData = JSON.parse(geminiRes.text || '{}');
            }
          }
        } catch (excelErr: any) {
          console.error('Excel processing error:', excelErr);
          throw new Error(`Failed to parse Excel file: ${excelErr.message}`);
        }
      }
      // Case 2: CSV
      else if (detectedType === 'csv' || rawExt === 'csv') {
        try {
          const csvText = req.body.csvText || Buffer.from(cleanBase64, 'base64').toString('utf-8');
          const lines = csvText.split(/\r?\n/).map((l: string) => l.split(','));
          rawExtractedData = parseTabularRowsHeuristic(lines, bankHint);

          if (!rawExtractedData.transactions || rawExtractedData.transactions.length === 0) {
            if (ai && csvText.trim().length > 20) {
              const prompt = `You are an expert Document AI for UAE Bank Statements. Extract transactions to JSON from this CSV:\n${csvText.slice(0, 10000)}`;
              const geminiPromise = ai.models.generateContent({
                model: 'gemini-3.8-flash',
                contents: prompt,
                config: { responseMimeType: 'application/json' }
              });
              const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('AI timeout')), 10000));
              const geminiRes: any = await Promise.race([geminiPromise, timeoutPromise]);
              rawExtractedData = JSON.parse(geminiRes.text || '{}');
            }
          }
        } catch (csvErr: any) {
          throw new Error(`Failed to parse CSV file: ${csvErr.message}`);
        }
      }
      // Case 3: PDF (Scanned or Native digital UAE Bank/Card statement)
      else {
        if (!ai) {
          return res.status(503).json({ error: 'Gemini Document AI not initialized for PDF processing' });
        }

        const prompt = `You are an expert Document AI for UAE Bank Statements & Credit Card Statements.
Analyze this bank statement PDF carefully (supports Emirates NBD, ADCB, FAB, Mashreq, RAKBANK, CBD, DIB, HSBC, Citi, Standard Chartered).

Extract all data and return a JSON object with this exact structure:
{
  "bankName": "string (e.g. Emirates NBD, Abu Dhabi Commercial Bank, First Abu Dhabi Bank, Mashreq, RAKBANK)",
  "accountNumberMasked": "string (e.g. '•••• 4289' or card last 4 digits)",
  "accountType": "bank" | "credit_card",
  "statementPeriod": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "openingBalance": number (opening or previous balance in AED, or null),
  "closingBalance": number (closing or new balance in AED, or null),
  "totalDebits": number (total withdrawals or debits in AED, or null),
  "totalCredits": number (total deposits or credits in AED, or null),
  "currency": "AED",
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "original description/narrative from the statement table",
      "merchant": "clean merchant name (e.g. Carrefour, ADNOC, DEWA, Al Baik, Amazon)",
      "debit": number (withdrawal/purchase amount, 0 if credit),
      "credit": number (deposit/payment/salary amount, 0 if debit),
      "balance": number (closing balance after this transaction, or null),
      "type": "expense" | "income" | "card_payment" | "transfer",
      "suggestedCategory": "Food & Groceries" | "Food" | "Groceries" | "Fuel" | "Clothing" | "Utilities" | "Telecom" | "Shopping" | "Transport" | "Healthcare" | "Entertainment" | "Travel" | "Education" | "Salary" | "Other"
    }
  ]
}

CRITICAL RULES:
1. Extract EVERY transaction line from all pages without skipping.
2. Convert all dates to YYYY-MM-DD format.
3. Identify Credit Card Payments (e.g. "Autopay Payment", "Credit Card Payment", "Cash/Cheque Settlement") and set type="card_payment".
4. Identify Salary / WPS credits and set type="income" and suggestedCategory="Salary".
5. Identify internal bank transfers (e.g. "Transfer To/From", "Internal Trf") and set type="transfer".
6. Keep amounts positive numbers in AED.`;

        const geminiPromise = ai.models.generateContent({
          model: 'gemini-3.8-flash',
          contents: [
            {
              inlineData: {
                data: cleanBase64,
                mimeType: 'application/pdf',
              },
            },
            prompt,
          ],
          config: {
            responseMimeType: 'application/json',
          },
        });

        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Document AI processing timed out after 25s')), 25000)
        );

        const response: any = await Promise.race([geminiPromise, timeoutPromise]);
        const text = response.text || '';
        try {
          rawExtractedData = JSON.parse(text);
        } catch (jsonErr) {
          const match = text.match(/\{[\s\S]*\}/);
          if (match) {
            rawExtractedData = JSON.parse(match[0]);
          } else {
            throw new Error('Failed to parse Document AI response for PDF statement');
          }
        }
      }

      // Fallback object structure if empty
      if (!rawExtractedData) {
        rawExtractedData = {
          bankName: bankHint || 'UAE Bank',
          accountNumberMasked: '',
          transactions: []
        };
      }

      // Now pass extracted data through Python Statement Processor & Rules Engine for reconciliation and anomaly detection
      const pythonProcessedResult = await runPythonStatement(rawExtractedData);

      // Match target account if available in existing accounts
      const userAccounts = Array.isArray(accounts) ? accounts : [];
      if (pythonProcessedResult.transactions && Array.isArray(pythonProcessedResult.transactions)) {
        const detectedBank = (pythonProcessedResult.bankName || '').toLowerCase();
        const detectedMask = (pythonProcessedResult.accountNumberMasked || '').replace(/[^0-9]/g, '');

        let defaultMatchedAccount = userAccounts.find((a: any) => {
          const accName = a.name.toLowerCase();
          const accBank = (a.bankName || '').toLowerCase();
          const accLast4 = a.accountNumberMasked.replace(/[^0-9]/g, '');
          if (detectedMask && accLast4 && detectedMask.endsWith(accLast4)) return true;
          if (detectedBank && (accName.includes(detectedBank) || accBank.includes(detectedBank))) return true;
          return false;
        });

        if (!defaultMatchedAccount && userAccounts.length > 0) {
          defaultMatchedAccount = userAccounts[0];
        }

        pythonProcessedResult.transactions = pythonProcessedResult.transactions.map((tx: any) => ({
          ...tx,
          matchedAccountId: defaultMatchedAccount?.id || null
        }));
      }

      return res.json({
        success: true,
        data: pythonProcessedResult
      });

    } catch (err: any) {
      console.error('Statement parsing endpoint error:', err);
      return res.status(500).json({ error: err.message || 'Statement parsing failed' });
    }
  });

  // Heuristic Tabular Row Parser for CSV/Excel fallback
  function parseTabularRowsHeuristic(rows: any[][], bankHint?: string): any {
    if (!rows || rows.length === 0) return { bankName: bankHint || 'UAE Bank', transactions: [] };

    // Find header row
    let headerIdx = -1;
    let colDate = -1;
    let colDesc = -1;
    let colDebit = -1;
    let colCredit = -1;
    let colAmount = -1;
    let colBalance = -1;

    for (let i = 0; i < Math.min(rows.length, 15); i++) {
      const row = rows[i].map((cell: any) => String(cell || '').toLowerCase().trim());
      const dIdx = row.findIndex((c: string) => c.includes('date') || c.includes('txn dt'));
      const descIdx = row.findIndex((c: string) => c.includes('desc') || c.includes('narrat') || c.includes('particular') || c.includes('detail') || c.includes('merchant'));

      if (dIdx !== -1 && descIdx !== -1) {
        headerIdx = i;
        colDate = dIdx;
        colDesc = descIdx;
        colDebit = row.findIndex((c: string) => c.includes('debit') || c.includes('dr') || c.includes('withdrawal') || c.includes('spent'));
        colCredit = row.findIndex((c: string) => c.includes('credit') || c.includes('cr') || c.includes('deposit') || c.includes('received'));
        colAmount = row.findIndex((c: string) => c.includes('amount') || c.includes('amt') || c.includes('total'));
        colBalance = row.findIndex((c: string) => c.includes('balance') || c.includes('bal'));
        break;
      }
    }

    if (headerIdx === -1) {
      // Default to columns 0=Date, 1=Desc, 2=Debit, 3=Credit, 4=Balance
      headerIdx = 0;
      colDate = 0;
      colDesc = 1;
      colDebit = 2;
      colCredit = 3;
      colBalance = 4;
    }

    const txs: any[] = [];
    for (let r = headerIdx + 1; r < rows.length; r++) {
      const row = rows[r];
      if (!row || row.length === 0) continue;

      const rawDate = String(row[colDate] || '').trim();
      const rawDesc = String(row[colDesc] || '').trim();
      if (!rawDate || !rawDesc || rawDesc.toLowerCase().includes('total') || rawDesc.toLowerCase().includes('opening balance')) continue;

      const parseNum = (val: any) => {
        if (!val) return 0;
        const clean = String(val).replace(/[^0-9.-]/g, '');
        const n = parseFloat(clean);
        return isNaN(n) ? 0 : Math.abs(n);
      };

      const debit = colDebit !== -1 ? parseNum(row[colDebit]) : (colAmount !== -1 ? parseNum(row[colAmount]) : 0);
      const credit = colCredit !== -1 ? parseNum(row[colCredit]) : 0;
      const balance = colBalance !== -1 ? parseNum(row[colBalance]) : null;

      if (debit === 0 && credit === 0) continue;

      txs.push({
        date: rawDate,
        description: rawDesc,
        debit,
        credit,
        balance,
        currency: 'AED'
      });
    }

    return {
      bankName: bankHint || 'UAE Bank',
      accountNumberMasked: '',
      transactions: txs
    };
  }

  // Helper to execute Python ML Analytics (Isolation Forest & Statsmodels)
  const runPythonML = (action: string, payload: any): Promise<any> => {
    return new Promise((resolve, reject) => {
      const pythonScript = path.resolve(__dirname, 'scripts', 'ml_analytics.py');
      const child = spawn('python3', [pythonScript, `--action=${action}`]);

      let stdout = '';
      let stderr = '';

      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      child.on('close', (code) => {
        if (code !== 0) {
          console.error(`Python ML script error (code ${code}):`, stderr);
          return reject(new Error(stderr || `Python process exited with code ${code}`));
        }
        try {
          const parsed = JSON.parse(stdout);
          resolve(parsed);
        } catch (err) {
          reject(new Error(`Failed to parse Python ML output: ${stdout}`));
        }
      });

      child.stdin.write(JSON.stringify(payload));
      child.stdin.end();
    });
  };

  // POST /api/ai/voice-parse - Speech Recognition + Gemini AI Voice Expense Entry
  app.post('/api/ai/voice-parse', async (req, res) => {
    try {
      const { voiceText, accounts, categories } = req.body;
      if (!voiceText || typeof voiceText !== 'string') {
        return res.status(400).json({ error: 'Missing voiceText in request body' });
      }

      const availableAccounts = accounts && Array.isArray(accounts) ? accounts : [];
      const accountNames = availableAccounts.map((a: any) => `${a.name} (${a.type})`).join(', ');
      const availableCategories = categories && Array.isArray(categories) ? categories.join(', ') : 'Food & Groceries, Fuel, Clothing, Healthcare, Transport, Utilities, Telecom, Shopping, Entertainment, Rent & Housing, Education, Salary, Other';

      if (!ai) {
        try {
          ai = new GoogleGenAI();
        } catch (e) {}
      }

      let parsedResult: any = null;

      if (ai) {
        const prompt = `You are an expert UAE financial voice parser for DirhamTrack AI.
The user spoke a voice command to record a financial transaction:
"${voiceText}"

User's Existing Accounts in app: [${accountNames}]
Valid Expense Categories: [${availableCategories}]

Extract and return a single valid JSON object with this exact schema:
{
  "amount": number (positive numeric float in AED),
  "merchant": "string (e.g. Petrol, ADNOC, Carrefour, Aster Pharmacy, Dinner, Taxi, DEWA)",
  "category": "string (must match the most appropriate valid category)",
  "accountName": "string (the matching bank or card name from existing accounts, or 'Cash Wallet' or 'Main Checking Account')",
  "matchedAccountId": "string or null (id of the matched account if identifiable)",
  "type": "expense" | "income",
  "date": "string (YYYY-MM-DD format, today's date if unspecified)",
  "notes": "string (brief summary of voice instruction)"
}

Examples:
- "Add AED 150 petrol from ADCB credit card" -> amount: 150, merchant: "Petrol", category: "Fuel", accountName: "ADCB Credit Card"
- "Add AED 50 food paid in cash" -> amount: 50, merchant: "Food", category: "Food & Groceries", accountName: "Cash Wallet"
- "Spent 85 dirhams at Carrefour on groceries" -> amount: 85, merchant: "Carrefour", category: "Food & Groceries"
- "Received 15000 AED salary in Emirates NBD" -> amount: 15000, type: "income", merchant: "Employer Salary", category: "Salary"

CRITICAL: Return ONLY JSON. Do not include markdown codeblocks if possible.`;

        try {
          const response = await ai.models.generateContent({
            model: 'gemini-3.8-flash',
            contents: prompt,
            config: {
              responseMimeType: 'application/json',
            },
          });

          const text = response.text || '';
          try {
            parsedResult = JSON.parse(text);
          } catch (e) {
            const match = text.match(/\{[\s\S]*\}/);
            if (match) parsedResult = JSON.parse(match[0]);
          }
        } catch (geminiErr) {
          console.warn('Gemini voice parse error, using heuristic fallback:', geminiErr);
        }
      }

      // Robust heuristic fallback if Gemini is offline
      if (!parsedResult || !parsedResult.amount) {
        const lower = voiceText.toLowerCase();
        const amtMatch = voiceText.match(/(?:aed|dhs|dirhams|dh)?\s*(\d+(?:\.\d{1,2})?)/i) || voiceText.match(/(\d+(?:\.\d{1,2})?)\s*(?:aed|dhs|dirhams|dh)?/i);
        const amount = amtMatch ? parseFloat(amtMatch[1]) : 0;

        let category = 'Other';
        let merchant = 'Expense';
        if (lower.includes('petrol') || lower.includes('fuel') || lower.includes('gas') || lower.includes('enoc') || lower.includes('adnoc')) {
          category = 'Fuel';
          merchant = 'Petrol';
        } else if (lower.includes('food') || lower.includes('restaurant') || lower.includes('dinner') || lower.includes('lunch') || lower.includes('burger') || lower.includes('coffee') || lower.includes('grocery') || lower.includes('carrefour') || lower.includes('lulu')) {
          category = 'Food & Groceries';
          merchant = lower.includes('carrefour') ? 'Carrefour' : (lower.includes('lulu') ? 'Lulu' : 'Food / Dining');
        } else if (lower.includes('cloth') || lower.includes('shirt') || lower.includes('shoes') || lower.includes('zara')) {
          category = 'Clothing';
          merchant = 'Clothing & Apparel';
        } else if (lower.includes('pharmacy') || lower.includes('medicine') || lower.includes('clinic') || lower.includes('doctor')) {
          category = 'Healthcare';
          merchant = 'Healthcare / Pharmacy';
        } else if (lower.includes('taxi') || lower.includes('uber') || lower.includes('careem') || lower.includes('metro') || lower.includes('salik')) {
          category = 'Transport';
          merchant = 'Transport';
        }

        // Match account
        let matchedAcc = availableAccounts.find((a: any) => lower.includes(a.name.toLowerCase()));
        if (!matchedAcc && lower.includes('cash')) {
          matchedAcc = availableAccounts.find((a: any) => a.type === 'cash');
        }
        if (!matchedAcc && (lower.includes('credit') || lower.includes('card'))) {
          matchedAcc = availableAccounts.find((a: any) => a.type === 'credit_card');
        }

        parsedResult = {
          amount,
          merchant,
          category,
          accountName: matchedAcc ? matchedAcc.name : (availableAccounts[0]?.name || 'Default Account'),
          matchedAccountId: matchedAcc ? matchedAcc.id : (availableAccounts[0]?.id || null),
          type: lower.includes('salary') || lower.includes('income') || lower.includes('deposit') ? 'income' : 'expense',
          date: new Date().toISOString().split('T')[0],
          notes: `Voice input: "${voiceText}"`
        };
      }

      // Ensure account ID is mapped if possible
      if (!parsedResult.matchedAccountId && parsedResult.accountName && availableAccounts.length > 0) {
        const found = availableAccounts.find((a: any) =>
          a.name.toLowerCase().includes(parsedResult.accountName.toLowerCase()) ||
          parsedResult.accountName.toLowerCase().includes(a.name.toLowerCase())
        );
        if (found) {
          parsedResult.matchedAccountId = found.id;
          parsedResult.accountName = found.name;
        } else {
          parsedResult.matchedAccountId = availableAccounts[0].id;
          parsedResult.accountName = availableAccounts[0].name;
        }
      }

      return res.json({ success: true, data: parsedResult });
    } catch (err: any) {
      console.error('Voice Parse error:', err);
      return res.status(500).json({ error: err.message || 'Voice parsing failed' });
    }
  });

  // POST /api/ai/fraud-detection - Python Scikit-learn (Isolation Forest) Anomaly Engine
  app.post('/api/ai/fraud-detection', async (req, res) => {
    try {
      const { transactions, accounts } = req.body;
      const mlResult = await runPythonML('fraud', {
        transactions: transactions || [],
        accounts: accounts || []
      });

      return res.json({ success: true, ...mlResult });
    } catch (err: any) {
      console.error('Fraud detection error:', err);
      return res.status(500).json({ error: err.message || 'Fraud detection execution failed' });
    }
  });

  // POST /api/ai/predictive-forecast - Python Statsmodels Time-Series Cash Flow Forecast
  app.post('/api/ai/predictive-forecast', async (req, res) => {
    try {
      const { transactions, budgets, accounts, subscriptions } = req.body;
      const forecastResult = await runPythonML('forecast', {
        transactions: transactions || [],
        budgets: budgets || [],
        accounts: accounts || [],
        subscriptions: subscriptions || []
      });

      return res.json({ success: true, ...forecastResult });
    } catch (err: any) {
      console.error('Predictive forecast error:', err);
      return res.status(500).json({ error: err.message || 'Forecast calculation failed' });
    }
  });

  // POST /api/ai/finance-assistant - Gemini Conversational Financial Coach
  app.post('/api/ai/finance-assistant', async (req, res) => {
    try {
      const { query, history, context } = req.body;
      if (!query || typeof query !== 'string') {
        return res.status(400).json({ error: 'Missing query in request body' });
      }

      if (!ai) {
        try {
          ai = new GoogleGenAI();
        } catch (e) {
          return res.status(503).json({ error: 'Gemini AI not initialized on server' });
        }
      }

      const txs = context?.transactions || [];
      const accs = context?.accounts || [];
      const bgts = context?.budgets || [];
      const subs = context?.subscriptions || [];

      // Calculate context facts
      const totalExpense = txs.filter((t: any) => t.type === 'expense').reduce((s: number, t: any) => s + (Number(t.amount) || 0), 0);
      const totalIncome = txs.filter((t: any) => t.type === 'income').reduce((s: number, t: any) => s + (Number(t.amount) || 0), 0);
      const bankBalance = accs.filter((a: any) => a.type === 'bank' || a.type === 'cash').reduce((s: number, a: any) => s + (Number(a.balance) || 0), 0);
      const creditDebt = accs.filter((a: any) => a.type === 'credit_card').reduce((s: number, a: any) => s + (Number(a.balance) || 0), 0);

      // Category breakdown
      const catSpend: Record<string, number> = {};
      txs.filter((t: any) => t.type === 'expense').forEach((t: any) => {
        catSpend[t.category] = (catSpend[t.category] || 0) + Number(t.amount);
      });

      const topCategories = Object.entries(catSpend)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([c, amt]) => `${c}: AED ${amt.toFixed(0)}`)
        .join(', ');

      const recentTxSummary = txs.slice(-8).map((t: any) =>
        `${t.date}: ${t.merchant} (AED ${t.amount}, ${t.category}, ${t.type})`
      ).join('\n');

      const subsSummary = subs.map((s: any) => `${s.name}: AED ${s.amount}/${s.billingCycle}`).join(', ');

      const systemInstruction = `You are "DirhamTrack Financial AI", an expert personal wealth advisor specializing in UAE residents (Dubai, Abu Dhabi, Sharjah).
Your goal is to provide specific, data-backed, actionable financial advice based on the user's real transactions and ledger.

Current Real Financial Ledger Context:
- Currency: UAE Dirhams (AED)
- Monthly Income: AED ${totalIncome.toLocaleString()}
- Total Spent This Month: AED ${totalExpense.toLocaleString()}
- Liquid Bank Balance: AED ${bankBalance.toLocaleString()}
- Credit Card Outstanding Debt: AED ${creditDebt.toLocaleString()}
- Top Spending Categories: ${topCategories || 'None recorded yet'}
- Active Subscriptions: ${subsSummary || 'None'}
- Recent Transactions:
${recentTxSummary || 'No recent transactions'}

Formatting Rules:
1. Always format currency in AED (e.g. AED 1,250).
2. Answer the user's specific question directly with concrete numbers from their ledger.
3. Be professional, encouraging, practical, and concise. Use clean bullet points with bold highlights.
4. When suggesting savings (e.g. "How can I save AED 2,000?"), identify exact categories with realistic UAE alternatives (e.g., dining out vs meal prep, supermarket alternatives like Viva/Lulu vs Waitrose, subscription audits, credit card interest avoidance).
5. If credit card debt is high relative to bank balance, remind them to clear statement balances before interest charges.`;

      const prompt = `User Question: "${query}"\nProvide clear, structured financial insights tailored to their actual numbers.`;

      let answerText = '';
      try {
        const response = await ai.models.generateContent({
          model: 'gemini-3.8-flash',
          contents: prompt,
          config: {
            systemInstruction,
            temperature: 0.7,
          },
        });
        answerText = response.text || '';
      } catch (geminiError: any) {
        console.warn('Gemini chat error, generating data-backed fallback:', geminiError?.message);
        answerText = `### DirhamTrack Financial Insights\n\nBased on your actual recorded ledger:\n- **Monthly Income:** AED ${totalIncome.toLocaleString()}\n- **Total Spent This Month:** AED ${totalExpense.toLocaleString()}\n- **Liquid Cash & Bank Balance:** AED ${bankBalance.toLocaleString()}\n- **Credit Card Debt:** AED ${creditDebt.toLocaleString()}\n- **Top Categories:** ${topCategories || 'None recorded yet'}\n\n**Financial Assessment:**\n${
          totalExpense > totalIncome && totalIncome > 0
            ? `⚠️ Your monthly spending (AED ${totalExpense.toLocaleString()}) currently exceeds income by AED ${(totalExpense - totalIncome).toLocaleString()}.`
            : `✅ You have positive monthly net savings of AED ${(totalIncome - totalExpense).toLocaleString()}.`
        }\n${
          creditDebt > 0
            ? `💳 Clear your card balance of AED ${creditDebt.toLocaleString()} before the billing cycle ends to prevent 3.25%/month finance charges.`
            : '💳 Your credit card balance is clean with zero outstanding interest liability.'
        }\n\n💡 **Actionable Tip:** ${
          topCategories
            ? `Your largest expenditure is in ${topCategories.split(',')[0]}. Reducing this by 15% would save ~AED ${(
                (catSpend[Object.keys(catSpend)[0] || ''] || 0) * 0.15
              ).toFixed(0)} every month.`
            : 'Add more transactions or budgets to unlock customized savings recommendations.'
        }`;
      }

      // Generate 3 contextual follow-up questions
      const followUps = [
        'Where did I overspend this month?',
        'How can I save AED 2,000 in UAE?',
        'Review my credit card debt & interest risk'
      ];

      return res.json({
        success: true,
        answer: answerText,
        followUps
      });
    } catch (err: any) {
      console.error('Finance Assistant error:', err);
      return res.status(500).json({ error: err.message || 'Finance Assistant request failed' });
    }
  });

  // In development, mount Vite middleware for SPA serving (HMR disabled in preview iframe)
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: {
        middlewareMode: true,
        hmr: false,
      },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    // In production, serve static built assets
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`DirhamTrack Full-Stack server running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start server:', err);
});
