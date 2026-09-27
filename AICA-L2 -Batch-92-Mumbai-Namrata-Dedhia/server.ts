import express, { Request, Response } from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import { INITIAL_KNOWLEDGE_BASE } from './src/data/knowledgeBase.js';
import { OFFICIAL_SOURCES } from './src/data/sources.js';
import { INITIAL_CHANGE_LOG } from './src/data/changeLog.js';
import { AdvisorEngine, MANDATORY_DISCLAIMER, ESCALATION_EMAIL } from './src/services/advisorEngine.js';
import { AdvisoryTestSuite } from './src/services/testSuite.js';
import { FAQRecord, ChatLogRecord, WebhookRequest, WebhookResponse } from './src/types/advisory.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// In-Memory Database Stores (authoritative application knowledge base)
let knowledgeBase: FAQRecord[] = [...INITIAL_KNOWLEDGE_BASE];
let sources = [...OFFICIAL_SOURCES];
let changeLog = [...INITIAL_CHANGE_LOG];
let chatLogs: ChatLogRecord[] = [];

// Initialize Advisor Engine
const advisorEngine = new AdvisorEngine();
const testSuite = new AdvisoryTestSuite(advisorEngine);

// Helper to parse Google Sheets rows into FAQRecord structures
function parseSheetRowsToKB(headers: string[], rows: any[][]): FAQRecord[] {
  const records: FAQRecord[] = [];
  const headerMap: Record<string, number> = {};
  headers.forEach((h, i) => {
    headerMap[String(h).trim()] = i;
  });

  for (const row of rows) {
    const getValue = (field: string, defaultValue: string = ''): string => {
      const idx = headerMap[field];
      if (idx === undefined || idx >= row.length) return defaultValue;
      const val = row[idx];
      return val !== null && val !== undefined ? String(val).trim() : defaultValue;
    };

    const getArrayValue = (field: string): string[] => {
      const val = getValue(field);
      if (!val) return [];
      return val.split(/[;|]/).map(s => s.trim()).filter(Boolean);
    };

    const faq_id = getValue('faq_id');
    if (!faq_id) continue;

    records.push({
      faq_id,
      category: getValue('category', 'General'),
      subcategory: getValue('subcategory', 'General'),
      user_question: getValue('user_question'),
      question_variations: getArrayValue('question_variations'),
      short_answer: getValue('short_answer'),
      detailed_answer: getValue('detailed_answer'),
      applicability: getValue('applicability'),
      taxpayer_type: getValue('taxpayer_type'),
      NRI_status: getValue('NRI_status'),
      OCI_status: getValue('OCI_status'),
      resident_status: (getValue('resident_status') as any),
      conditions: getArrayValue('conditions'),
      exceptions: getArrayValue('exceptions'),
      thresholds: getValue('thresholds'),
      rates: getValue('rates'),
      limits: getValue('limits'),
      relevant_FY: getValue('relevant_FY'),
      relevant_AY: getValue('relevant_AY'),
      effective_from: getValue('effective_from'),
      effective_until: getValue('effective_until') || undefined,
      source_type: (getValue('source_type') as any),
      source_authority: (getValue('source_authority') as any),
      act_or_regulation: getValue('act_or_regulation'),
      section_rule_regulation: getValue('section_rule_regulation'),
      circular_notification: getValue('circular_notification') || undefined,
      source_url: getValue('source_url'),
      source_excerpt_or_summary: getValue('source_excerpt_or_summary'),
      last_verified: getValue('last_verified'),
      review_status: (getValue('review_status', 'DRAFT') as any),
      professional_review_required: (getValue('professional_review_required', 'NO') as any),
      keywords: getValue('keywords').split(',').map(s => s.trim()).filter(Boolean),
      related_faq_ids: getValue('related_faq_ids').split(',').map(s => s.trim()).filter(Boolean)
    });
  }
  return records;
}

// -------------------------------------------------------------
// 1. API: Webhook Endpoint (n8n API Contract)
// -------------------------------------------------------------
app.post('/api/webhook', async (req: Request, res: Response) => {
  const body: WebhookRequest = req.body;
  const question = (body.question || '').trim();
  const sessionId = body.session_id || `sess_${Date.now()}`;
  const channel = body.channel || 'pwa';

  if (!question) {
    return res.status(400).json({ error: 'Question parameter is required.' });
  }

  // Handle dynamic Google Sheets sync if credentials are provided in headers
  const accessToken = req.headers['x-google-access-token'] as string;
  const spreadsheetId = req.headers['x-google-spreadsheet-id'] as string;

  if (accessToken && spreadsheetId) {
    try {
      const response = await fetch(
        `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/FAQ_KNOWLEDGE_BASE?valueRenderOption=UNFORMATTED_VALUE`,
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Accept': 'application/json'
          }
        }
      );
      if (response.ok) {
        const sheetData: any = await response.json();
        if (sheetData.values && sheetData.values.length > 1) {
          const headers = sheetData.values[0];
          const rows = sheetData.values.slice(1);
          const syncedKB = parseSheetRowsToKB(headers, rows);
          if (syncedKB.length > 0) {
            advisorEngine.getRetrievalEngine().setKnowledgeBase(syncedKB);
            console.log(`Successfully auto-synchronized ${syncedKB.length} FAQ records from Google Sheet prior to answering.`);
          }
        }
      } else {
        console.warn(`Failed to fetch latest FAQ sheet: ${response.statusText}`);
      }
    } catch (err) {
      console.warn('Error dynamically syncing with Google Sheet:', err);
    }
  }

  try {
    const result: WebhookResponse = await advisorEngine.processQuery(
      question,
      body.context,
      body.history
    );

    // Record interaction in CHAT_LOG without sensitive PII
    const logEntry: ChatLogRecord = {
      id: `LOG-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      timestamp: new Date().toISOString(),
      session_id: sessionId,
      channel,
      user_question: question,
      detected_topic: result.topic,
      matched_faq_ids: result.matched_faq_ids,
      answer: result.answer,
      source_references: result.sources.map((s) => s.provision),
      confidence: result.confidence,
      out_of_scope: result.out_of_scope,
      escalation_required: result.escalation_required,
      response_status: result.out_of_scope ? 'OUT_OF_SCOPE' : 'SUCCESS'
    };

    chatLogs.unshift(logEntry);
    if (chatLogs.length > 500) chatLogs.pop();

    return res.json(result);
  } catch (error: any) {
    console.error('Error processing query:', error);

    const errorLog: ChatLogRecord = {
      id: `LOG-${Date.now()}`,
      timestamp: new Date().toISOString(),
      session_id: sessionId,
      channel,
      user_question: question,
      detected_topic: 'System Error',
      matched_faq_ids: [],
      answer: 'A technical error occurred while retrieving verified provisions.',
      source_references: [],
      confidence: 0,
      out_of_scope: true,
      escalation_required: true,
      response_status: 'ERROR'
    };
    chatLogs.unshift(errorLog);

    return res.status(500).json({
      answer: `The verified advisory knowledge base is temporarily encountering a processing delay. Please contact ${ESCALATION_EMAIL} for urgent advisory inquiries.\n\n${MANDATORY_DISCLAIMER}`,
      sources: [],
      topic: 'Technical Service Exception',
      matched_faq_ids: [],
      out_of_scope: true,
      escalation_required: true,
      disclaimer: MANDATORY_DISCLAIMER,
      confidence: 0
    });
  }
});

// -------------------------------------------------------------
// 2. API: Knowledge Base & Sheets Data Endpoints
// -------------------------------------------------------------
app.get('/api/knowledge-base', (req: Request, res: Response) => {
  const currentKB = advisorEngine.getRetrievalEngine().getKnowledgeBase();
  res.json({
    total: currentKB.length,
    records: currentKB
  });
});

app.post('/api/knowledge-base', (req: Request, res: Response) => {
  const newRecord: FAQRecord = req.body;
  if (!newRecord.faq_id || !newRecord.category || !newRecord.short_answer) {
    return res.status(400).json({ error: 'faq_id, category, and short_answer are required' });
  }

  const currentKB = advisorEngine.getRetrievalEngine().getKnowledgeBase();
  const existingIndex = currentKB.findIndex((r) => r.faq_id === newRecord.faq_id);
  if (existingIndex >= 0) {
    // Record old position in change log
    const oldRec = currentKB[existingIndex];
    changeLog.unshift({
      change_id: `CHG-${Date.now()}`,
      date: new Date().toISOString().split('T')[0],
      topic: newRecord.category,
      old_position: oldRec.short_answer,
      new_position: newRecord.short_answer,
      source: newRecord.act_or_regulation + ' ' + newRecord.section_rule_regulation,
      reason: 'Knowledge base administrator modification',
      reviewed_by: 'Authorized Compliance Editor',
      review_status: newRecord.review_status
    });
    currentKB[existingIndex] = newRecord;
  } else {
    currentKB.push(newRecord);
  }

  advisorEngine.getRetrievalEngine().setKnowledgeBase(currentKB);
  res.json({ success: true, record: newRecord });
});

app.post('/api/knowledge-base/bulk', (req: Request, res: Response) => {
  const records = req.body.records;
  if (!Array.isArray(records)) {
    return res.status(400).json({ error: 'records must be an array' });
  }
  advisorEngine.getRetrievalEngine().setKnowledgeBase(records);
  res.json({ success: true, count: records.length });
});

app.get('/api/sources', (req: Request, res: Response) => {
  res.json({ total: sources.length, sources });
});

app.get('/api/change-log', (req: Request, res: Response) => {
  res.json({ total: changeLog.length, changeLog });
});

app.get('/api/chat-logs', (req: Request, res: Response) => {
  res.json({ total: chatLogs.length, logs: chatLogs });
});

// -------------------------------------------------------------
// 3. API: Automated Test Suite Runner
// -------------------------------------------------------------
app.post('/api/test-suite', async (req: Request, res: Response) => {
  try {
    const summary = await testSuite.runAllTests();
    res.json(summary);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// -------------------------------------------------------------
// 4. API: n8n Workflow Export
// -------------------------------------------------------------
app.get('/api/n8n/workflow', (req: Request, res: Response) => {
  try {
    const workflowPath = path.join(__dirname, 'src/data/n8n-workflow.json');
    if (fs.existsSync(workflowPath)) {
      const content = fs.readFileSync(workflowPath, 'utf8');
      res.setHeader('Content-Type', 'application/json');
      res.send(content);
    } else {
      res.status(404).json({ error: 'n8n workflow file not found' });
    }
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// -------------------------------------------------------------
// 5. API: Google Sheets CSV Exporter
// -------------------------------------------------------------
app.get('/api/export/sheets/:sheetName', (req: Request, res: Response) => {
  const { sheetName } = req.params;

  function toCSV(headers: string[], rows: any[][]): string {
    const escape = (val: any) => {
      if (val === undefined || val === null) return '""';
      const s = String(val).replace(/"/g, '""');
      return `"${s}"`;
    };
    const headerRow = headers.map(escape).join(',');
    const bodyRows = rows.map((r) => r.map(escape).join(',')).join('\n');
    return `${headerRow}\n${bodyRows}`;
  }

  if (sheetName === 'FAQ_KNOWLEDGE_BASE') {
    const headers = [
      'faq_id', 'category', 'subcategory', 'user_question', 'question_variations',
      'short_answer', 'detailed_answer', 'applicability', 'taxpayer_type', 'NRI_status',
      'OCI_status', 'resident_status', 'conditions', 'exceptions', 'thresholds',
      'rates', 'limits', 'relevant_FY', 'relevant_AY', 'effective_from',
      'effective_until', 'source_type', 'source_authority', 'act_or_regulation',
      'section_rule_regulation', 'circular_notification', 'source_url',
      'source_excerpt_or_summary', 'last_verified', 'review_status',
      'professional_review_required', 'keywords', 'related_faq_ids'
    ];
    const currentKB = advisorEngine.getRetrievalEngine().getKnowledgeBase();
    const rows = currentKB.map((k) => [
      k.faq_id, k.category, k.subcategory, k.user_question, k.question_variations.join(' | '),
      k.short_answer, k.detailed_answer, k.applicability, k.taxpayer_type, k.NRI_status,
      k.OCI_status, k.resident_status, k.conditions.join('; '), k.exceptions.join('; '), k.thresholds,
      k.rates, k.limits, k.relevant_FY, k.relevant_AY, k.effective_from,
      k.effective_until || '', k.source_type, k.source_authority, k.act_or_regulation,
      k.section_rule_regulation, k.circular_notification || '', k.source_url,
      k.source_excerpt_or_summary, k.last_verified, k.review_status,
      k.professional_review_required, k.keywords.join(', '), k.related_faq_ids.join(', ')
    ]);
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename="FAQ_KNOWLEDGE_BASE.csv"');
    return res.send(toCSV(headers, rows));
  }

  if (sheetName === 'SOURCES') {
    const headers = ['source_id', 'authority', 'source_title', 'source_type', 'url', 'publication_date', 'effective_date', 'subject', 'last_checked', 'notes'];
    const rows = sources.map((s) => [s.source_id, s.authority, s.source_title, s.source_type, s.url, s.publication_date, s.effective_date, s.subject, s.last_checked, s.notes]);
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename="SOURCES.csv"');
    return res.send(toCSV(headers, rows));
  }

  if (sheetName === 'CHANGE_LOG') {
    const headers = ['change_id', 'date', 'topic', 'old_position', 'new_position', 'source', 'reason', 'reviewed_by', 'review_status'];
    const rows = changeLog.map((c) => [c.change_id, c.date, c.topic, c.old_position, c.new_position, c.source, c.reason, c.reviewed_by, c.review_status]);
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename="CHANGE_LOG.csv"');
    return res.send(toCSV(headers, rows));
  }

  if (sheetName === 'CHAT_LOG') {
    const headers = ['id', 'timestamp', 'session_id', 'channel', 'user_question', 'detected_topic', 'matched_faq_ids', 'answer', 'source_references', 'confidence', 'out_of_scope', 'escalation_required', 'response_status'];
    const rows = chatLogs.map((l) => [l.id, l.timestamp, l.session_id, l.channel, l.user_question, l.detected_topic, l.matched_faq_ids.join('; '), l.answer, l.source_references.join('; '), l.confidence, l.out_of_scope, l.escalation_required, l.response_status]);
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename="CHAT_LOG.csv"');
    return res.send(toCSV(headers, rows));
  }

  res.status(404).json({ error: 'Unknown sheet' });
});


// -------------------------------------------------------------
// 6. Vite Middleware Mount or Static Asset Serving
// -------------------------------------------------------------
async function setupViteOrStatic() {
  const isProd = process.env.NODE_ENV === 'production';
  if (!isProd) {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: {
        middlewareMode: true,
        hmr: false,
        ws: false
      },
      appType: 'spa'
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (req: Request, res: Response) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, () => {
    console.log(`NRI Advisory Server listening on port ${PORT}`);
  });
}

setupViteOrStatic().catch((err) => {
  console.error('Failed to start server:', err);
});
