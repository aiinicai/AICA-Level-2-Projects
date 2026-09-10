import 'dotenv/config';
import express from 'express';
import path from 'path';
import fs from 'fs';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';

const app = express();
const PORT = 3000;

app.use(express.json({ limit: '10mb' }));

// Safe initialization of Gemini AI
function getGenAI(): GoogleGenAI | null {
  const key = process.env.GEMINI_API_KEY;
  if (!key) return null;
  return new GoogleGenAI({
    apiKey: key,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build',
      },
    },
  });
}

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    hasGeminiKey: Boolean(process.env.GEMINI_API_KEY),
    timestamp: new Date().toISOString(),
  });
});

// 1. Suggest Fraud Risk Factors (SA 240)
app.post(['/api/gemini/suggest-fraud-risks', '/api/gemini/fraud-hint'], async (req, res) => {
  const { lineItemName, clientName, industry, entityUnderstanding, entityContext } = req.body;
  const ai = getGenAI();

  if (!ai) {
    // High quality offline ICAI rule-based response
    const fallbackRisks = [
      {
        fraudTriangleCategory: 'Opportunities',
        impactedAccounts: 'Revenue Recognition / Trade Receivables',
        riskDescription: 'Premature revenue recognition around year-end with incomplete documentation or disputed delivery terms (FOB/CIF).',
        plannedProcedures: 'Detailed sample testing of shipping notes, e-Way bills, and customs manifests for 10 days before and after 31 March; external debtor confirmations under SA 505.',
      },
      {
        fraudTriangleCategory: 'Incentives / Pressures',
        impactedAccounts: 'Inventories (Finished Goods & Raw Materials)',
        riskDescription: 'Overstatement of inventory values to avoid gross margin erosion and prevent debt covenant breaches.',
        plannedProcedures: 'Surprise attendance at physical inventory verification, net realizable value (NRV) testing against subsequent selling prices, and recalculation of overhead absorption.',
      },
      {
        fraudTriangleCategory: 'Opportunities',
        impactedAccounts: 'Related Party Transactions & Advances',
        riskDescription: 'Undisclosed related party loans, advances, or procurement transactions at off-market terms without board approval.',
        plannedProcedures: 'Scrutiny of MCA filings (Form AOC-2), bank statements for round-tripping transactions, and independent market benchmarking.',
      },
    ];

    return res.json({
      risks: fallbackRisks,
      hint: fallbackRisks[0].riskDescription,
      source: 'rule-engine',
    });
  }

  try {
    const prompt = `You are a Senior Audit Technical Director at an Indian Chartered Accountancy firm assisting an engagement team in applying SA 240 (Auditor's Responsibilities Relating to Fraud in an Audit of Financial Statements).
Client: "${clientName || 'Manufacturing & Trading Enterprise'}".
Industry: "${industry || 'Textiles & Industrial Manufacturing'}".
Entity Context: ${JSON.stringify(entityUnderstanding || entityContext || {})}.

Generate 3 realistic, high-risk fraud scenarios under the Fraud Triangle (Incentives/Pressures, Opportunities, Attitudes/Rationalizations) tailored to this client.
Respond in strict JSON format matching this schema:
{
  "risks": [
    {
      "fraudTriangleCategory": "Incentives / Pressures" | "Opportunities" | "Attitudes / Rationalizations",
      "impactedAccounts": "Name of account/line item",
      "riskDescription": "Clear 1-2 sentence description of the fraud scheme",
      "plannedProcedures": "Specific substantive audit procedure compliant with SA 330 and SA 240"
    }
  ]
}`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        responseMimeType: 'application/json',
        systemInstruction: 'You are an expert Indian Chartered Accountant specializing in ICAI Standards on Auditing, specifically SA 240 and SA 315.',
      },
    });

    const parsed = JSON.parse(response.text || '{}');
    return res.json({
      risks: parsed.risks || [],
      hint: parsed.risks?.[0]?.riskDescription || 'Evaluate revenue recognition and inventory valuation for potential management bias.',
      source: 'gemini-3.8-flash',
    });
  } catch (error) {
    console.error('Gemini fraud suggestions error:', error);
    return res.json({
      risks: [
        {
          fraudTriangleCategory: 'Incentives / Pressures',
          impactedAccounts: 'Revenue from Operations',
          riskDescription: 'Pressure to achieve budgeted performance resulting in aggressive cut-off or fictitious sales invoices.',
          plannedProcedures: 'Perform rigorous cut-off testing on dispatches near year end; reconcile GST GSTR-1 with financial records.',
        },
      ],
      source: 'fallback-on-error',
    });
  }
});

// 2. Suggest Risk Rationale (SA 315)
app.post(['/api/gemini/suggest-risk-rationale', '/api/gemini/risk-rationale'], async (req, res) => {
  const { lineItem, lineItemName, category, inherentRisk, assertions, industry } = req.body;
  const targetItem = lineItem || lineItemName || 'Financial Statement Item';
  const ai = getGenAI();

  if (!ai) {
    const fallbackRationale = `Given ${inherentRisk?.toLowerCase() || 'moderate'} inherent risk for ${targetItem} and focus on assertions (${Array.isArray(assertions) ? assertions.join(', ') : 'Valuation, Completeness'}), risks arise from routine estimation complexities, transaction volume, and reconciliation with third-party records.`;
    return res.json({ rationale: fallbackRationale, source: 'rule-engine' });
  }

  try {
    const prompt = `You are an Indian statutory auditor applying SA 315 (Revised).
Line Item: "${targetItem}".
Category: "${category || 'Balance Sheet / P&L'}".
Inherent Risk Assessed: "${inherentRisk || 'Moderate'}".
Relevant Assertions: ${Array.isArray(assertions) ? assertions.join(', ') : 'Existence, Valuation, Cutoff'}.
Industry: "${industry || 'Indian Corporate Enterprise'}".

Provide a concise, 2-sentence formal audit planning rationale explaining why this inherent risk rating is justified for the specified assertions under ICAI standards.`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
    });

    return res.json({ rationale: response.text?.trim(), source: 'gemini-3.8-flash' });
  } catch (error) {
    console.error('Gemini risk rationale error:', error);
    return res.json({
      rationale: `Assessed as ${inherentRisk || 'Moderate'} inherent risk considering the volume of transactions, regulatory scrutiny, and reliance on operational controls across relevant assertions.`,
      source: 'fallback-on-error',
    });
  }
});

// 3. Draft Planning Memorandum Section (SA 300)
app.post(['/api/gemini/draft-planning-memo', '/api/gemini/draft-memo-section'], async (req, res) => {
  const { sectionName, sectionTitle, engagementData, keyContext, currentDraft } = req.body;
  const section = sectionName || sectionTitle || 'Executive Summary';
  const ai = getGenAI();

  if (!ai) {
    return res.json({
      draft: currentDraft || `The engagement team has completed the risk assessment and planning procedures for ${section} in accordance with relevant ICAI Standards on Auditing. All mandatory requirements, benchmark evaluations, and internal control considerations have been documented in the audit file.`,
      source: 'rule-engine',
    });
  }

  try {
    const prompt = `You are drafting a formal Audit Planning Memorandum section for an Indian statutory audit under ICAI Standards on Auditing (SA 300, SA 315, SA 320, SA 240, SA 330).
Section: "${section}".
Engagement Context: ${JSON.stringify(engagementData || keyContext || {})}.
Current working draft (if any): "${currentDraft || ''}".

Draft a rigorous, well-structured 2-3 paragraph memorandum section in authoritative Indian statutory audit phrasing. Cite specific SAs where appropriate. Avoid informal language.`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
    });

    return res.json({ draft: response.text?.trim(), source: 'gemini-3.8-flash' });
  } catch (error) {
    console.error('Gemini draft memo error:', error);
    return res.json({
      draft: currentDraft || 'Audit planning procedures executed in accordance with ICAI Standards on Auditing.',
      source: 'fallback-on-error',
    });
  }
});

// 4. ICAI Knowledge Base Assistant
app.post('/api/gemini/ask-icai-kb', async (req, res) => {
  const { question, standardReference } = req.body;
  const ai = getGenAI();

  if (!ai) {
    return res.json({
      answer: `ICAI Standards on Auditing Reference (${standardReference || 'General Standards'}):
• SA 300: Planning an Audit of Financial Statements requires establishing an overall strategy and detailed audit plan.
• SA 315: Identifying and Assessing the Risks of Material Misstatement through Understanding the Entity and Its Environment mandates understanding internal controls (COSO components), IT systems, and significant risks.
• SA 320: Materiality in Planning and Performing an Audit requires establishing Overall Materiality, Performance Materiality, and Clearly Trivial Threshold using professional judgment.
• SA 240: Mandates presumed fraud risk in revenue recognition and non-rebuttable management override of controls.
• SA 330: Requires substantive procedures, including tests of details (TOD), for each assessed significant risk.`,
      source: 'offline-reference',
    });
  }

  try {
    const prompt = `You are the ICAI Technical Directorate Virtual Assistant for Standards on Auditing (SAs).
The auditor is asking: "${question}".
Standard reference (if specified): "${standardReference || 'Indian SAs'}".

Provide a direct, authoritative explanation strictly grounded in the Indian Standards on Auditing issued by ICAI. Cite specific paragraphs where appropriate.`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
    });

    return res.json({ answer: response.text?.trim(), source: 'gemini-3.8-flash' });
  } catch (error) {
    console.error('Gemini ICAI KB error:', error);
    return res.status(500).json({ error: 'Failed to query Knowledge Base via Gemini' });
  }
});

// 5. Workpaper File Persistence (Save & Load to Container Storage)
const STORAGE_FILE = path.join(process.cwd(), 'audit_engagement_data.json');

app.get('/api/engagement/load', (req, res) => {
  try {
    if (fs.existsSync(STORAGE_FILE)) {
      const data = fs.readFileSync(STORAGE_FILE, 'utf-8');
      return res.json({ success: true, data: JSON.parse(data) });
    }
    return res.json({ success: false, message: 'No stored engagement file found' });
  } catch (err: any) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

app.post('/api/engagement/save', (req, res) => {
  try {
    fs.writeFileSync(STORAGE_FILE, JSON.stringify(req.body, null, 2), 'utf-8');
    return res.json({ success: true, savedAt: new Date().toISOString() });
  } catch (err: any) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

// Vite middleware and static serving
async function startServer() {
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
    console.log(`Audit Planning Workbench server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
