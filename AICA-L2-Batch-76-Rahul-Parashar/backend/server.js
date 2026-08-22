import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import Anthropic from '@anthropic-ai/sdk';

const app = express();
app.use(cors({ origin: 'http://localhost:5173' }));
app.use(express.json({ limit: '15mb' }));

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MODEL = process.env.ANTHROPIC_MODEL || 'claude-sonnet-5';

app.post('/api/chat', async (req, res) => {
  const { message, history, currentPage, financials } = req.body || {};

  if (!message || typeof message !== 'string') {
    return res.status(400).json({ error: 'A "message" string is required.' });
  }
  if (!financials) {
    return res.status(400).json({ error: 'No workbook data loaded — upload a file in the dashboard first.' });
  }

  const systemPrompt = [
    "You are a CFO's financial analyst assistant. Answer only using the JSON financial data provided below.",
    "If the answer isn't in the data, say so plainly — never estimate, guess, or invent a figure.",
    `The user is currently viewing the '${currentPage || 'unknown'}' page of the dashboard.`,
    '',
    'FINANCIAL DATA (JSON):',
    JSON.stringify(financials),
  ].join('\n');

  const priorTurns = Array.isArray(history)
    ? history
        .filter((h) => h && typeof h.content === 'string' && (h.role === 'user' || h.role === 'assistant'))
        .map((h) => ({ role: h.role, content: h.content }))
    : [];

  try {
    const response = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 1024,
      system: systemPrompt,
      messages: [...priorTurns, { role: 'user', content: message }],
    });

    const reply = response.content
      .filter((block) => block.type === 'text')
      .map((block) => block.text)
      .join('\n')
      .trim();

    res.json({ reply: reply || "I couldn't generate a response — please try rephrasing." });
  } catch (err) {
    console.error('[/api/chat] error:', err?.message || err);
    res.status(500).json({ error: 'Could not reach the analyst assistant. Check ANTHROPIC_API_KEY is set correctly in backend/.env and try again.' });
  }
});

app.get('/api/health', (_req, res) => res.json({ ok: true }));

const PORT = process.env.PORT || 8787;
app.listen(PORT, () => {
  console.log(`[backend] listening on http://localhost:${PORT}`);
});
