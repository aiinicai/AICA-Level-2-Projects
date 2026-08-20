import express from 'express';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { extractBriefingWithGemini, analyzeSpecificUpdateWithGemini } from './server/geminiService';

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '10mb' }));

  // API Routes
  app.get('/api/health', (req, res) => {
    res.json({
      status: 'ok',
      service: 'AI Client Intelligence & Advisory Agent',
      timestamp: new Date().toISOString(),
      hasGeminiApiKey: Boolean(process.env.GEMINI_API_KEY),
    });
  });

  // Extract raw Daily Professional Briefing text with Gemini
  app.post('/api/gemini/extract-briefing', async (req, res) => {
    try {
      const { text, briefingDate } = req.body;
      if (!text) {
        return res.status(400).json({ error: 'Missing briefing text' });
      }
      const updates = await extractBriefingWithGemini(text, briefingDate || '7 August 2026');
      res.json({ success: true, updates });
    } catch (err: any) {
      console.error('Error in /api/gemini/extract-briefing:', err);
      res.status(500).json({
        error: err.message || 'Failed to extract briefing updates with Gemini',
      });
    }
  });

  // Analyze specific user-submitted regulatory update with Gemini
  app.post('/api/gemini/analyze-update', async (req, res) => {
    try {
      const { title, source, date, referenceNo, url, fullText } = req.body;
      if (!title || !fullText) {
        return res.status(400).json({ error: 'Title and full update text are required.' });
      }
      const update = await analyzeSpecificUpdateWithGemini({
        title,
        source: source || 'User Input',
        date: date || new Date().toISOString().split('T')[0],
        referenceNo,
        url,
        fullText,
      });
      res.json({ success: true, update });
    } catch (err: any) {
      console.error('Error in /api/gemini/analyze-update:', err);
      res.status(500).json({
        error: err.message || 'Failed to analyze update with Gemini',
      });
    }
  });

  // Gmail Integration Status Check Endpoint
  app.get('/api/gmail/status', (req, res) => {
    const authHeader = req.headers.authorization;
    const isConnected = Boolean(authHeader && authHeader.startsWith('Bearer '));
    res.json({
      connected: isConnected,
      service: 'Gmail API',
      statusMessage: isConnected ? 'Gmail OAuth Connected' : 'Gmail Not Connected',
    });
  });

  // Gmail Profile Verification Endpoint
  app.get('/api/gmail/verify-profile', async (req, res) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        success: false,
        connected: false,
        error: 'Missing or malformed Authorization header. Bearer token required.',
      });
    }

    const token = authHeader.split(' ')[1];
    try {
      const profileRes = await fetch('https://www.googleapis.com/gmail/v1/users/me/profile', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (profileRes.ok) {
        const profileData = await profileRes.json();
        return res.json({
          success: true,
          connected: true,
          profile: {
            emailAddress: profileData.emailAddress,
            messagesTotal: profileData.messagesTotal,
            threadsTotal: profileData.threadsTotal,
            historyId: profileData.historyId,
          },
        });
      } else {
        const errorData = await profileRes.json().catch(() => ({}));
        const errorMsg =
          errorData?.error?.message ||
          `Gmail API returned HTTP ${profileRes.status}: ${profileRes.statusText}`;
        return res.status(profileRes.status).json({
          success: false,
          connected: false,
          error: errorMsg,
        });
      }
    } catch (err: any) {
      console.error('Error verifying Gmail profile:', err);
      return res.status(502).json({
        success: false,
        connected: false,
        error: `Network error calling Gmail API: ${err.message}`,
      });
    }
  });

// Helper functions for normalization and matching
function normalizeText(str: string): string {
  if (!str) return '';
  return str
    .normalize('NFKC')
    .replace(/[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]/g, '-')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function extractBriefingDate(normalizedSubject: string): string {
  const dashMatch = normalizedSubject.match(/(?:daily professional briefing\s*-\s*)(.+)$/i);
  if (dashMatch) {
    return dashMatch[1].trim();
  }
  const datePatternMatch = normalizedSubject.match(/\b(\d{1,2}\s+[a-z]+\s+\d{4})\b/i);
  if (datePatternMatch) {
    return datePatternMatch[1].trim();
  }
  return 'Not Detected';
}

function evaluateCandidateMatch(subjectHeader: string, targetDate: string): {
  normalizedSubject: string;
  extractedBriefingDate: string;
  subjectMatch: 'PASS' | 'FAIL';
  dateMatch: 'PASS' | 'FAIL';
} {
  const normSubject = normalizeText(subjectHeader);
  const normTargetDate = normalizeText(targetDate);

  // Subject Match: Check if subject contains "daily professional briefing"
  const subjectMatch = normSubject.includes('daily professional briefing') ? 'PASS' : 'FAIL';

  // Date Matching:
  const targetDayNoZero = normTargetDate.replace(/\b0(\d)\b/g, '$1');
  const targetDayWithZero = normTargetDate.replace(/\b([1-9])\b(?=\s+[a-z]+)/g, '0$1');

  const extractedDate = extractBriefingDate(normSubject);

  let dateMatch: 'PASS' | 'FAIL' = 'FAIL';

  if (
    normSubject.includes(normTargetDate) ||
    normSubject.includes(targetDayNoZero) ||
    normSubject.includes(targetDayWithZero)
  ) {
    dateMatch = 'PASS';
  } else if (extractedDate !== 'Not Detected') {
    const normExtracted = normalizeText(extractedDate);
    const normExtractedNoZero = normExtracted.replace(/\b0(\d)\b/g, '$1');
    if (normExtracted === normTargetDate || normExtractedNoZero === targetDayNoZero) {
      dateMatch = 'PASS';
    }
  }

  return {
    normalizedSubject: normSubject,
    extractedBriefingDate: extractedDate,
    subjectMatch,
    dateMatch,
  };
}

  // Gmail Briefing Search Endpoint — Two-Stage Matching Engine & Diagnostic Diagnostics
  app.get('/api/gmail/search-briefing', async (req, res) => {
    const authHeader = req.headers.authorization;
    const queryDate = (req.query.date as string) || '7 August 2026';
    const expectedSubject = `Daily Professional Briefing – ${queryDate}`;

    // Check if live OAuth token is provided
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.json({
        found: false,
        connected: false,
        source: 'Gmail Integration Interface',
        requestedTargetDate: queryDate,
        expectedSubject: expectedSubject,
        searchStatus: 'Not Connected',
        error: 'Gmail OAuth access token missing.',
        message: 'Gmail is not connected. Connect Gmail to import today\'s professional briefing or use Load Demo Briefing.',
      });
    }

    const token = authHeader.split(' ')[1];

    try {
      // Fetch connected user profile email for diagnostics
      let connectedUserEmail = 'Connected Gmail Account';
      try {
        const profileRes = await fetch('https://www.googleapis.com/gmail/v1/users/me/profile', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (profileRes.ok) {
          const profileData = await profileRes.json();
          if (profileData.emailAddress) {
            connectedUserEmail = profileData.emailAddress;
          }
        }
      } catch (e) {
        // Non-blocking
      }

      // STAGE 1 — BROAD GMAIL CANDIDATE SEARCH
      // Robust unquoted/unconstrained search query for all emails matching subject keywords without is:unread filter
      const broadQueries = [
        `subject:(Daily Professional Briefing)`,
        `subject:"Daily Professional Briefing"`,
        `Daily Professional Briefing`,
      ];

      let candidateList: any[] = [];
      const seenMsgIds = new Set<string>();
      let usedQuery = broadQueries[0];

      for (const query of broadQueries) {
        const listRes = await fetch(
          `https://www.googleapis.com/gmail/v1/users/me/messages?q=${encodeURIComponent(query)}&maxResults=30`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (listRes.ok) {
          const listData = await listRes.json();
          if (listData.messages && listData.messages.length > 0) {
            usedQuery = query;
            for (const m of listData.messages) {
              if (!seenMsgIds.has(m.id)) {
                seenMsgIds.add(m.id);
                candidateList.push(m);
              }
            }
            if (candidateList.length > 0) break;
          }
        }
      }

      // STAGE 2 — APPLICATION-SIDE DETERMINISTIC VALIDATION & DIAGNOSTICS
      const inspectedCandidates: any[] = [];
      let matchedMessage: any = null;

      for (const msgRef of candidateList.slice(0, 30)) {
        const msgRes = await fetch(
          `https://www.googleapis.com/gmail/v1/users/me/messages/${msgRef.id}?format=full`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (msgRes.ok) {
          const msgData = await msgRes.json();
          const headers = msgData.payload?.headers || [];
          const subjectHeader =
            headers.find((h: any) => h.name.toLowerCase() === 'subject')?.value || '(No Subject)';
          const dateHeader =
            headers.find((h: any) => h.name.toLowerCase() === 'date')?.value ||
            new Date().toDateString();

          const evaluation = evaluateCandidateMatch(subjectHeader, queryDate);

          inspectedCandidates.push({
            id: msgRef.id,
            subject: subjectHeader,
            dateHeader: dateHeader,
            normalizedSubject: evaluation.normalizedSubject,
            extractedBriefingDate: evaluation.extractedBriefingDate,
            subjectMatch: evaluation.subjectMatch,
            dateMatch: evaluation.dateMatch,
          });

          // Match found!
          if (evaluation.subjectMatch === 'PASS' && evaluation.dateMatch === 'PASS' && !matchedMessage) {
            let bodyText = msgData.snippet || '';
            if (msgData.payload?.body?.data) {
              bodyText = Buffer.from(msgData.payload.body.data, 'base64').toString('utf-8');
            } else if (msgData.payload?.parts) {
              const textPart = msgData.payload.parts.find((p: any) => p.mimeType === 'text/plain');
              if (textPart?.body?.data) {
                bodyText = Buffer.from(textPart.body.data, 'base64').toString('utf-8');
              } else {
                const htmlPart = msgData.payload.parts.find((p: any) => p.mimeType === 'text/html');
                if (htmlPart?.body?.data) {
                  bodyText = Buffer.from(htmlPart.body.data, 'base64').toString('utf-8');
                }
              }
            }

            matchedMessage = {
              id: msgRef.id,
              subject: subjectHeader,
              date: dateHeader,
              snippet: msgData.snippet,
              bodyText: bodyText || msgData.snippet,
            };
          }
        }
      }

      const diagnostics = {
        connectedAccount: connectedUserEmail,
        targetDate: queryDate,
        broadGmailQuery: usedQuery,
        candidateMessagesFound: candidateList.length,
        candidates: inspectedCandidates,
      };

      if (matchedMessage) {
        return res.json({
          found: true,
          connected: true,
          source: 'Gmail Live OAuth API',
          requestedTargetDate: queryDate,
          expectedSubject: expectedSubject,
          dateMatch: 'PASS',
          message: matchedMessage,
          diagnostics,
        });
      } else {
        return res.json({
          found: false,
          connected: true,
          source: 'Gmail Live API',
          requestedTargetDate: queryDate,
          expectedSubject: expectedSubject,
          dateMatch: 'FAIL',
          searchStatus: 'No Matching Email Found',
          error: 'NO MATCHING LIVE GMAIL BRIEFING FOUND',
          message: `Connected to Gmail account (${connectedUserEmail}), but no email matching expected subject "${expectedSubject}" was found for target date ${queryDate}.`,
          diagnostics,
        });
      }
    } catch (e: any) {
      console.warn('Gmail API call error:', e);
      return res.status(502).json({
        found: false,
        connected: true,
        source: 'Gmail Live API',
        requestedTargetDate: queryDate,
        expectedSubject: expectedSubject,
        dateMatch: 'FAIL',
        searchStatus: 'Gmail API Error',
        error: `Gmail API request failed: ${e.message}`,
      });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
