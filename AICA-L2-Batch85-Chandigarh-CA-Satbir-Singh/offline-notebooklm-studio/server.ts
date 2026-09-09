import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let aiClient: GoogleGenAI | null = null;
function getGeminiClient(): GoogleGenAI | null {
  if (!aiClient && process.env.GEMINI_API_KEY) {
    aiClient = new GoogleGenAI({
      apiKey: process.env.GEMINI_API_KEY,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    });
  }
  return aiClient;
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '50mb' }));

  // Health check endpoint
  app.get('/api/health', (_req, res) => {
    res.json({
      status: 'ok',
      hasGeminiKey: Boolean(process.env.GEMINI_API_KEY),
      model: 'gemini-3.7-flash',
    });
  });

  // Server-side AI Grounded Chat & Synthesis
  app.post('/api/chat', async (req, res) => {
    try {
      const { prompt, sources, messages = [] } = req.body;
      const ai = getGeminiClient();

      if (!ai) {
        return res.status(503).json({ error: 'GEMINI_API_KEY is not configured on server' });
      }

      if (!sources || !Array.isArray(sources) || sources.length === 0) {
        return res.status(400).json({ error: 'No active source documents provided' });
      }

      // Build rich context blocks from the active sources
      const contextBlocks = sources
        .map(
          (s: any, idx: number) =>
            `=== SOURCE [${idx + 1}]: ${s.name} (${s.fileType || 'Document'}, ${s.charCount || s.text?.length || 0} chars) ===\n${(s.text || '').slice(0, 120000)}\n=== END SOURCE [${idx + 1}] ===`
        )
        .join('\n\n');

      const systemInstruction = `You are an expert research analyst and document synthesizer (NotebookLM style).
You have access to ONLY the ${sources.length} grounded source document(s) provided below:

${contextBlocks}

CRITICAL RULES:
1. Ground your answers EXCLUSIVELY in the provided source document(s). Never hallucinate or assume facts not present in the text.
2. MANDATORY TABLE FORMATTING (IF SOURCE HAS TABLES/SPREADSHEETS/SLABS/METRICS):
   - Whenever the source document contains data in table format, spreadsheet format (e.g. Excel/CSV sheets), matrix format, tax slab charts, financial statements, schedules, multi-column metrics, or rate lists, you MUST present and output that data in clean, well-aligned Markdown Table format (| Col 1 | Col 2 | ... |) in the chat response.
   - Do NOT flatten, compress, or convert structured tables into long plain bullet paragraphs. Preserve the column structure, headers, and exact row values from the source.
   - Include the grounded source citation [1] in the citation column or row.
3. If the user asks a SPECIFIC TOPIC OR KEYWORD QUESTION (e.g. "key changes about income tax", "what are the tax slab rates", "explain clause 12", "what does it say about MSMEs", "what is the date/number"):
   - Directly and thoroughly answer the user's specific question using exact facts, quotes, sections, rates, and numbers found in the text.
   - Whenever the data involves tabular data, comparative rates, slabs, or metrics from the source, present it in Markdown table format.
   - Do NOT output a generic document profile when the user asked a specific question. Answer the exact question asked.
4. If the user asks for a GENERAL SUMMARY, EXECUTIVE OVERVIEW, or asks what the document is:
   - Provide a comprehensive structured breakdown:
     - **Introduction & Scope** [1]
     - **1. Document / Subject Profile** (bold key-value items with citations)
     - **2. Summary of Key Data, Clauses & Provisions** (Markdown table with "Sr. No.")
     - **3. Key Takeaways & Factual Insights**
     - **4. Strategic & Compliance Observations**
5. Always cite sources with bracketed numbers like [1], [2] matching the source document numbers above.`;

      // Build conversation history
      const formattedHistory = (messages || [])
        .filter((m: any) => m.content && (m.role === 'user' || m.role === 'assistant'))
        .slice(-6)
        .map((m: any) => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
        .join('\n\n');

      const userContent = formattedHistory
        ? `PREVIOUS CONVERSATION:\n${formattedHistory}\n\nCURRENT QUESTION:\n${prompt}`
        : prompt;

      const response = await ai.models.generateContent({
        model: 'gemini-3.7-flash',
        contents: userContent,
        config: {
          systemInstruction,
          temperature: 0.2,
        },
      });

      const text = response.text || '';
      return res.json({ content: text });
    } catch (err: any) {
      console.error('Server Gemini error:', err);
      return res.status(500).json({ error: err.message || 'Internal server error' });
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
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
