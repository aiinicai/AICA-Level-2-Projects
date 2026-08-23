import express from "express";
import path from "path";
import { GoogleGenAI, Type } from "@google/genai";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// Server-side Gemini AI setup
let aiClient: GoogleGenAI | null = null;
function getAIClient(): GoogleGenAI | null {
  if (!aiClient && process.env.GEMINI_API_KEY) {
    aiClient = new GoogleGenAI({
      apiKey: process.env.GEMINI_API_KEY,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiClient;
}

// Health check
app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    hasApiKey: !!process.env.GEMINI_API_KEY,
    timestamp: new Date().toISOString(),
  });
});

// AI ITR Extraction Endpoint with Multi-Model Fallback & Retry
app.post("/api/gemini/extract-itr", async (req, res) => {
  try {
    const { rawText, fileBase64, mimeType } = req.body;
    const ai = getAIClient();

    if (!ai) {
      return res.json({
        success: false,
        fallback: true,
        error: "Gemini API key is not configured. Falling back to local parser.",
      });
    }

    const systemPrompt = `You are an expert Chartered Accountant and Indian Income Tax Return (ITR) parser.
Your task is to extract structured tax computation data from the provided ITR document text or image.
Extract all details accurately into the requested JSON schema.
Ensure all monetary numbers are positive floats/integers, or 0 if not present.
If assessment year is like 2024-25 or 2026-27, capture AY and calculate corresponding Previous Year / FY.
Support all ITR forms: ITR-1, ITR-2, ITR-3, ITR-4, ITR-5, ITR-6, ITR-7, and ITR-V Acknowledgement.`;

    // Prioritize clean rawText if available (faster, smaller payload, immune to multimodal load)
    let contents: any;
    if (rawText && rawText.trim().length > 50) {
      contents = `Extract all Income Tax Return (ITR) data from this text:\n\n${rawText.slice(0, 30000)}`;
    } else if (fileBase64 && mimeType) {
      contents = {
        parts: [
          {
            inlineData: {
              data: fileBase64,
              mimeType: mimeType,
            },
          },
          {
            text: `Extract all Income Tax Return (ITR) data from this document. Provide clean structured JSON according to the schema.`,
          },
        ],
      };
    } else if (rawText) {
      contents = `Extract all Income Tax Return (ITR) data from this text:\n\n${rawText.slice(0, 30000)}`;
    } else {
      return res.status(400).json({ error: "Either rawText or fileBase64 is required" });
    }

    const candidateModels = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.1-pro-preview"];
    let lastError: any = null;
    let responseText: string | null = null;

    for (const modelName of candidateModels) {
      // Try model with 1 retry on 503/429
      for (let attempt = 1; attempt <= 2; attempt++) {
        try {
          const response = await ai.models.generateContent({
            model: modelName,
            contents: contents,
            config: {
              systemInstruction: systemPrompt,
              responseMimeType: "application/json",
              responseSchema: {
                type: Type.OBJECT,
                properties: {
                  personalInfo: {
                    type: Type.OBJECT,
                    properties: {
                      pan: { type: Type.STRING },
                      aadhaar: { type: Type.STRING },
                      name: { type: Type.STRING },
                      fatherName: { type: Type.STRING },
                      dob: { type: Type.STRING },
                      formType: { type: Type.STRING },
                      assessmentYear: { type: Type.STRING },
                      financialYear: { type: Type.STRING },
                      filingStatus: { type: Type.STRING },
                      filingType: { type: Type.STRING },
                      taxRegime: { type: Type.STRING },
                      ackNumber: { type: Type.STRING },
                      filingDate: { type: Type.STRING },
                      address: { type: Type.STRING },
                      city: { type: Type.STRING },
                      state: { type: Type.STRING },
                      pincode: { type: Type.STRING },
                      mobile: { type: Type.STRING },
                      email: { type: Type.STRING },
                      status: { type: Type.STRING },
                      residentialStatus: { type: Type.STRING },
                      bankName: { type: Type.STRING },
                      bankAccountNumber: { type: Type.STRING },
                      bankIfsc: { type: Type.STRING },
                    },
                  },
                  incomeHeads: {
                    type: Type.OBJECT,
                    properties: {
                      salaryGross: { type: Type.NUMBER },
                      salaryExemptAllowances: { type: Type.NUMBER },
                      salaryStandardDeduction: { type: Type.NUMBER },
                      salaryProfessionalTax: { type: Type.NUMBER },
                      salaryNet: { type: Type.NUMBER },
                      housePropertyGross: { type: Type.NUMBER },
                      housePropertyTaxes: { type: Type.NUMBER },
                      housePropertyStandardDeduction: { type: Type.NUMBER },
                      housePropertyInterest: { type: Type.NUMBER },
                      housePropertyNet: { type: Type.NUMBER },
                      businessGrossReceipts: { type: Type.NUMBER },
                      businessGrossProfit: { type: Type.NUMBER },
                      businessExpenses: { type: Type.NUMBER },
                      businessNetProfit: { type: Type.NUMBER },
                      businessPresumptive44AD: { type: Type.NUMBER },
                      businessPresumptive44ADA: { type: Type.NUMBER },
                      capitalGainsSTCG_15Pct: { type: Type.NUMBER },
                      capitalGainsSTCG_20Pct: { type: Type.NUMBER },
                      capitalGainsSTCG_Slab: { type: Type.NUMBER },
                      capitalGainsLTCG_10Pct: { type: Type.NUMBER },
                      capitalGainsLTCG_20Pct: { type: Type.NUMBER },
                      capitalGainsLTCG_12_5Pct: { type: Type.NUMBER },
                      capitalGainsNet: { type: Type.NUMBER },
                      otherSourcesInterestSavings: { type: Type.NUMBER },
                      otherSourcesInterestDeposits: { type: Type.NUMBER },
                      otherSourcesDividends: { type: Type.NUMBER },
                      otherSourcesFamilyPension: { type: Type.NUMBER },
                      otherSourcesOthers: { type: Type.NUMBER },
                      otherSourcesDeductions: { type: Type.NUMBER },
                      otherSourcesNet: { type: Type.NUMBER },
                      grossTotalIncome: { type: Type.NUMBER },
                    },
                  },
                  deductions: {
                    type: Type.OBJECT,
                    properties: {
                      sec80C: { type: Type.NUMBER },
                      sec80CCC: { type: Type.NUMBER },
                      sec80CCD1: { type: Type.NUMBER },
                      sec80CCD1B: { type: Type.NUMBER },
                      sec80CCD2: { type: Type.NUMBER },
                      sec80D: { type: Type.NUMBER },
                      sec80DD: { type: Type.NUMBER },
                      sec80DDB: { type: Type.NUMBER },
                      sec80E: { type: Type.NUMBER },
                      sec80EE: { type: Type.NUMBER },
                      sec80EEA: { type: Type.NUMBER },
                      sec80G: { type: Type.NUMBER },
                      sec80GG: { type: Type.NUMBER },
                      sec80GGA: { type: Type.NUMBER },
                      sec80TTA: { type: Type.NUMBER },
                      sec80TTB: { type: Type.NUMBER },
                      sec80U: { type: Type.NUMBER },
                      otherDeductions: { type: Type.NUMBER },
                      totalDeductions: { type: Type.NUMBER },
                    },
                  },
                  taxComputation: {
                    type: Type.OBJECT,
                    properties: {
                      totalTaxableIncome: { type: Type.NUMBER },
                      taxOnTotalIncome: { type: Type.NUMBER },
                      specialRateTax: { type: Type.NUMBER },
                      rebate87A: { type: Type.NUMBER },
                      taxAfterRebate: { type: Type.NUMBER },
                      surcharge: { type: Type.NUMBER },
                      cess: { type: Type.NUMBER },
                      grossTaxLiability: { type: Type.NUMBER },
                      relief89: { type: Type.NUMBER },
                      relief90_91: { type: Type.NUMBER },
                      netTaxLiability: { type: Type.NUMBER },
                      interest234A: { type: Type.NUMBER },
                      interest234B: { type: Type.NUMBER },
                      interest234C: { type: Type.NUMBER },
                      fee234F: { type: Type.NUMBER },
                      totalTaxAndInterest: { type: Type.NUMBER },
                    },
                  },
                  taxesPaid: {
                    type: Type.OBJECT,
                    properties: {
                      advanceTax: { type: Type.NUMBER },
                      tdsSalary: { type: Type.NUMBER },
                      tdsNonSalary: { type: Type.NUMBER },
                      tcs: { type: Type.NUMBER },
                      selfAssessmentTax: { type: Type.NUMBER },
                      totalTaxesPaid: { type: Type.NUMBER },
                      refundDue: { type: Type.NUMBER },
                      taxPayable: { type: Type.NUMBER },
                    },
                  },
                  confidenceScore: { type: Type.NUMBER },
                  extractionNotes: { type: Type.STRING },
                },
              },
            },
          });

          responseText = response.text || "{}";
          break; // Success, exit retry loop
        } catch (err: any) {
          lastError = err;
          const errMsg = err?.message || String(err);
          console.warn(`Attempt ${attempt} with model ${modelName} returned:`, errMsg);
          
          // If 404 not found, immediately break to next model without retrying
          if (errMsg.includes('404') || errMsg.includes('NOT_FOUND') || errMsg.includes('no longer available')) {
            break;
          }

          if (attempt < 2) {
            await new Promise((resolve) => setTimeout(resolve, 800));
          }
        }
      }

      if (responseText) break; // Success, exit candidate models loop
    }

    if (!responseText) {
      console.warn("All Gemini models temporarily busy. Gracefully signaling client-side fallback.");
      return res.json({
        success: false,
        fallback: true,
        error: lastError?.message || "Model is currently experiencing high demand. Seamlessly using local tax engine.",
      });
    }

    const parsed = JSON.parse(responseText);
    res.json({ success: true, data: parsed });
  } catch (error: any) {
    console.warn("Gemini Extraction caught:", error?.message || error);
    res.json({
      success: false,
      fallback: true,
      error: error.message || "Failed to extract ITR using Gemini AI. Using local parser.",
    });
  }
});

// Vite middleware in dev / Static files in prod
async function setupServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`ITR Word Generator server running on http://0.0.0.0:${PORT}`);
  });
}

setupServer();
