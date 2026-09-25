import express from "express";
import path from "path";
import dotenv from "dotenv";
import { GoogleGenAI } from "@google/genai";

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json());

// Lazy-initialized Gemini client
let aiClient: GoogleGenAI | null = null;
function getAIClient(): GoogleGenAI | null {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || apiKey === "MY_GEMINI_API_KEY") {
    return null;
  }
  if (!aiClient) {
    aiClient = new GoogleGenAI({ apiKey });
  }
  return aiClient;
}

// API Health Check
app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Natural Language Financial Query Endpoint
app.post("/api/ai/query", async (req, res) => {
  const { query, contextData } = req.body;
  if (!query) {
    return res.status(400).json({ error: "Query is required" });
  }

  const ai = getAIClient();
  if (!ai) {
    // Return structured response indicating fallback to deterministic calculation engine
    return res.json({
      usedAI: false,
      message: "Processing query via deterministic Indian financial analysis engine.",
      query
    });
  }

  try {
    const prompt = `You are a financial analyst assistant for an Indian SME receivables & reconciliation platform.
Given this user query: "${query}"
Context Summary:
${JSON.stringify(contextData || {}, null, 2)}

Provide a concise, professional, actionable financial response with specific Indian accounting metrics (INR amounts in ₹/Lakhs, invoice numbers, customer names, days overdue, TDS mismatches). Always trace back to underlying data.
Structure your reply in markdown.`;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: prompt,
    });

    res.json({
      usedAI: true,
      text: response.text,
      query
    });
  } catch (err: any) {
    console.error("Gemini API Error:", err);
    res.json({
      usedAI: false,
      error: err.message || "Failed to generate AI insights",
      fallback: true
    });
  }
});

// Vite middleware setup
async function setupVite() {
  if (process.env.NODE_ENV !== "production") {
    const { createServer: createViteServer } = await import("vite");
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Receivables & Reconciliation platform running on http://0.0.0.0:${PORT}`);
  });
}

setupVite().catch((err) => {
  console.error("Failed to start server:", err);
});
