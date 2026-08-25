import express from "express";
import path from "path";
import dotenv from "dotenv";
import { GoogleGenAI, Type } from "@google/genai";
import { createServer as createViteServer } from "vite";

dotenv.config();

const app = express();
const PORT = 3000;

// Body parser with 50MB limit to handle uploaded financial PDFs and high-res financial document images
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// Lazy/Safe server-side Gemini client helper
function getGeminiClient(): GoogleGenAI {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not configured in server environment. Please configure it in Settings > Secrets.");
  }
  return new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build",
      },
    },
  });
}

// System instruction enforcing strict Chartered Accountant auditing protocols
const AUDIT_SYSTEM_INSTRUCTION = `You are a Senior Chartered Accountant, Engagement Partner, and Ind AS / AS Quality Review Board (QRB) Compliance Auditor.
Your mandate is to perform an exhaustive, mathematically rigorous financial statement disclosure verification, note-by-note proofreading, and internal consistency audit on the uploaded Financial Statements / Annual Report.

CORE AUDIT OBJECTIVES:
1. Comprehensive Note-by-Note Proofreading (EVERY Note must be audited individually):
   Scrutinize every note present in the financial statements:
   - Note phrasing, title, accounting policy consistency, cross-references on face of Balance Sheet & P&L.
   - Schedule casting math: opening balance + additions - deductions = closing balance.
   - Text vs table figures within notes.
   - Missing mandatory disclosures, itemized breakups, or statutory clauses.

2. ICAI Guidance Note on Schedule III (Division I, II & III) to Companies Act, 2013 & MCA 2021 Amendments:
   Perform strict verification of mandatory Schedule III requirements:
   - 11 Statutory Ratios: Current Ratio, Debt-Equity Ratio, Debt Service Coverage Ratio (DSCR), Return on Equity (ROE), Inventory Turnover Ratio, Trade Receivables Turnover Ratio, Trade Payables Turnover Ratio, Net Capital Turnover Ratio, Net Profit Ratio, Return on Capital Employed (ROCE), Return on Investment (ROI). (Mandatory explanation required if variance is >25% vs prior year).
   - Ageing Schedules:
     * Trade Receivables Ageing Schedule (Undisputed / Disputed, MSME / Non-MSME, <6m, 6m-1yr, 1-2yr, 2-3yr, >3yr, and unbilled dues).
     * Trade Payables Ageing Schedule (MSME / Others, undisputed / disputed, not due, <1yr, 1-2yr, 2-3yr, >3yr, unbilled dues).
     * CWIP Ageing Schedule (<1yr, 1-2yr, 2-3yr, >3yr) & CWIP Completion Schedule (for overdue / cost overrun projects).
     * Intangible Assets under Development Ageing & Completion Schedule.
   - Promoter Shareholding Pattern: Details of shares held by promoters and % change during the year.
   - Title Deeds of Immovable Property: Title deeds not held in company name (promoter/director/relative).
   - Revaluation of PPE / Intangibles: Disclosure whether revaluation was conducted by a Registered Valuer under Section 247.
   - Loans & Advances to Promoters, Directors, KMPs, and Related Parties: Repayable on demand or without terms, % to total loans.
   - Reconciliation of Quarterly Returns / Stock Statements to Banks vs Books of Accounts.
   - Wilful Defaulter Declaration: Bank/FI default declaration.
   - Relationship with Struck-Off Companies under section 248 / 560.
   - Registration of Charges or Satisfaction with ROC.
   - Compliance with approved Scheme of Arrangements.
   - Undisclosed Income surrendered in tax assessments under Income Tax Act 1961.
   - Corporate Social Responsibility (CSR) under Section 135 (Gross required to spend, actual spent, ongoing/other than ongoing, shortfall, unspent CSR bank account).
   - Crypto / Virtual Currency transactions.
   - Benami Property Proceedings under Prohibition of Benami Property Transactions Act, 1988.

3. All Ind AS / AS Standard Disclosures (Ind AS 1 through Ind AS 116):
   - Ind AS 1 (Presentation & Classification), Ind AS 2 (Inventories & NRV), Ind AS 7 (Cash Flow & Non-cash financing/investing), Ind AS 8 (Accounting policies), Ind AS 12 (Tax expense reconciliation & DTA/DTL), Ind AS 16 (PPE additions/deletions), Ind AS 19 (Employee Benefits actuarial tables), Ind AS 23 (Borrowing cost capitalization), Ind AS 24 (Related party & KMP remuneration), Ind AS 33 (Basic/Diluted EPS), Ind AS 36 (Impairment), Ind AS 37 (Provisions & Contingent liabilities quantification), Ind AS 38 (Intangibles), Ind AS 107/109 (Financial instruments ECL, liquidity buckets & sensitivity), Ind AS 108 (Segments), Ind AS 115 (Revenue disaggregation & contract liabilities), Ind AS 116 (ROU asset rollforward & lease liability maturity).

4. Cross-Referencing & Consistency Check:
   - Match figures in the primary statements (Balance Sheet, Profit & Loss, Cash Flow, SOCIE) against Note Schedules.
   - Match text commentary in Directors' Report / MD&A against financial tables.

5. Internal Mathematical & Casting Verification:
   - Check if Total Assets == Total Equity & Liabilities.
   - Check if Note schedule item totals sum up to the Line Item on the Balance Sheet / P&L.
   - Check text figures vs table figures.

OUTPUT REQUIREMENTS:
Output MUST be strict JSON containing summary, part1Disclosures, part2Inconsistencies, noteProofreading, scheduleIIIGuidanceFindings, part3Recommendations, and full rawMarkdownReport.`;

// API route: Perform Financial Statement Audit
app.post("/api/audit/analyze", async (req, res) => {
  try {
    const { text, fileData, mimeType, fileName, options } = req.body;

    if (!text && !fileData) {
      return res.status(400).json({ error: "Please provide financial statement text or an uploaded file (PDF/Image)." });
    }

    const ai = getGeminiClient();

    const parts: Array<any> = [];

    if (fileData && mimeType) {
      parts.push({
        inlineData: {
          data: fileData,
          mimeType: mimeType,
        },
      });
    }

    const promptText = `Please perform a comprehensive statutory, note-by-note proofreading, and internal consistency audit on this financial statement document (${fileName || "Document"}).

Key Audit Directives:
1. Complete Note-by-Note Proofreading:
   - Perform an exhaustive proofreading and review of EVERY single Note to Accounts present in the financial statements.
   - For each note, evaluate: Phrasing, completeness, mathematical footing (opening + additions - deductions = closing), missing statutory tables (e.g., ageing schedules), drafting/grammatical errors, and internal contradictions.

2. ICAI Guidance Note on Schedule III (Div I / Div II / Div III) & MCA 2021 Amendments:
   - Audit 11 Statutory Financial Ratios (Current Ratio, Debt-Equity, DSCR, ROE, Inventory Turnover, Debtors Turnover, Creditors Turnover, Net Capital Turnover, Net Profit, ROCE, ROI) and verify whether explanations for variances >25% are provided.
   - Audit Ageing Schedules: Trade Payables (MSME / Others with >1y, >2y, >3y), Trade Receivables (Undisputed / Disputed with >6m, >1y, >2y, >3y), CWIP ageing and completion schedule, Intangibles under development.
   - Audit Title Deeds of immovable property, Revaluation by registered valuers under Section 247, Promoter shareholding changes, Bank stock statements reconciliation, Wilful Defaulter, Struck-off companies, Charges with ROC, Benami property, Undisclosed income, and CSR disclosures under Section 135.

3. All Ind AS Standards (Ind AS 1 to Ind AS 116):
   - Mandatory disclosures under Ind AS 1, 2, 7, 8, 12, 16, 19, 23, 24, 33, 36, 37, 38, 107, 108, 109, 115, 116.

4. Internal Consistency & Castings:
   - Total Assets == Total Equity & Liabilities.
   - Primary statement figures == Note subtotal figures.
   - Text commentary vs tables.

${text ? `Financial Document Text/Extract:\n"""\n${text}\n"""` : ""}

Return the audit findings structured with strict JSON format containing summary, part1Disclosures, part2Inconsistencies, noteProofreading, scheduleIIIGuidanceFindings, part3Recommendations, and full rawMarkdownReport.`;

    parts.push({ text: promptText });

    const response = await ai.models.generateContent({
      model: "gemini-3.7-flash",
      contents: { parts },
      config: {
        systemInstruction: AUDIT_SYSTEM_INSTRUCTION,
        temperature: 0.1, // Low temperature for audit precision
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            summary: {
              type: Type.OBJECT,
              properties: {
                overallComplianceScore: {
                  type: Type.STRING,
                  description: "Must be 'High', 'Moderate', or 'Needs Immediate Revision'",
                },
                totalDiscrepancies: {
                  type: Type.INTEGER,
                  description: "Total count of missing disclosures + data mismatches",
                },
                missingDisclosuresCount: {
                  type: Type.INTEGER,
                },
                numericalMismatchesCount: {
                  type: Type.INTEGER,
                },
                keyRiskAreas: {
                  type: Type.STRING,
                  description: "Brief 2-3 line summary of critical non-compliances.",
                },
                entityName: {
                  type: Type.STRING,
                },
                reportingPeriod: {
                  type: Type.STRING,
                },
                reportingScale: {
                  type: Type.STRING,
                  description: "e.g. ₹ in Lakhs, ₹ in Crores",
                },
                frameworkIdentified: {
                  type: Type.STRING,
                  description: "e.g. Ind AS (Schedule III Division II)",
                },
              },
              required: [
                "overallComplianceScore",
                "totalDiscrepancies",
                "missingDisclosuresCount",
                "numericalMismatchesCount",
                "keyRiskAreas",
              ],
            },
            part1Disclosures: {
              type: Type.ARRAY,
              description: "Table of mandatory Ind AS disclosures evaluated",
              items: {
                type: Type.OBJECT,
                properties: {
                  standard: {
                    type: Type.STRING,
                    description: "e.g. Ind AS 24, Ind AS 37, Ind AS 16, Ind AS 107, Ind AS 115, Ind AS 116",
                  },
                  standardName: {
                    type: Type.STRING,
                  },
                  requirement: {
                    type: Type.STRING,
                    description: "Specific mandatory statutory disclosure requirement",
                  },
                  status: {
                    type: Type.STRING,
                    description: "Must be 'Complied', 'Missing', or 'Partial'",
                  },
                  observation: {
                    type: Type.STRING,
                    description: "Detail where it is disclosed or what is missing. If missing, state 'Section/Note not found in uploaded file.'",
                  },
                  applicableParagraph: {
                    type: Type.STRING,
                  },
                },
                required: ["standard", "requirement", "status", "observation"],
              },
            },
            part2Inconsistencies: {
              type: Type.ARRAY,
              description: "Detail any mismatch between Primary Financial Statements and Notes to Accounts or internal castings",
              items: {
                type: Type.OBJECT,
                properties: {
                  lineItem: {
                    type: Type.STRING,
                    description: "Financial Statement Line Item, e.g. Trade Receivables, PPE, KMP Remuneration",
                  },
                  primaryFigure: {
                    type: Type.STRING,
                    description: "Figure shown on Balance Sheet, P&L, or Directors Report",
                  },
                  noteFigure: {
                    type: Type.STRING,
                    description: "Corresponding Note Figure or mathematical sum with Note reference",
                  },
                  noteRef: {
                    type: Type.STRING,
                  },
                  discrepancy: {
                    type: Type.STRING,
                    description: "Exact variance explanation and mathematical discrepancy",
                  },
                  riskLevel: {
                    type: Type.STRING,
                    description: "Must be 'High', 'Medium', or 'Low'",
                  },
                  type: {
                    type: Type.STRING,
                    description: "numerical_mismatch, casting_error, text_table_contradiction, or missing_note",
                  },
                },
                required: ["lineItem", "primaryFigure", "noteFigure", "discrepancy", "riskLevel"],
              },
            },
            noteProofreading: {
              type: Type.ARRAY,
              description: "Comprehensive note-by-note proofreading review of EVERY Note in the document",
              items: {
                type: Type.OBJECT,
                properties: {
                  noteNumber: {
                    type: Type.STRING,
                    description: "e.g. Note 3, Note 11, Note 23, Note 33",
                  },
                  noteTitle: {
                    type: Type.STRING,
                    description: "e.g. Property, Plant and Equipment, Trade Receivables, Related Party",
                  },
                  proofreadingStatus: {
                    type: Type.STRING,
                    description: "Must be 'Complied', 'Observations Found', or 'Missing Mandatory Clauses'",
                  },
                  observations: {
                    type: Type.STRING,
                    description: "Detailed auditor review of text phrasing, mathematical footing, and disclosure thoroughness",
                  },
                  mandatoryClausesChecked: {
                    type: Type.STRING,
                    description: "Statutory items verified within this note (e.g. Ageing table, NRV write-down, MSME split, discount rate)",
                  },
                  draftingOrArithmeticIssues: {
                    type: Type.STRING,
                    description: "Any drafting ambiguity, missing sub-schedule, or casting conflict",
                  },
                },
                required: ["noteNumber", "noteTitle", "proofreadingStatus", "observations", "mandatoryClausesChecked"],
              },
            },
            scheduleIIIGuidanceFindings: {
              type: Type.ARRAY,
              description: "Exhaustive evaluation against ICAI Guidance Note on Schedule III (Div I/II/III) & MCA 2021 Amendments",
              items: {
                type: Type.OBJECT,
                properties: {
                  clause: {
                    type: Type.STRING,
                    description: "e.g. 11 Key Ratios (>25% variance), Trade Payables Ageing, Trade Receivables Ageing, CWIP Ageing, Promoter Shareholding, Benami Property, Wilful Defaulter, CSR Section 135, Bank Stock Reconciliation",
                  },
                  requirement: {
                    type: Type.STRING,
                    description: "Mandatory Schedule III / ICAI Guidance Note statutory requirement",
                  },
                  complianceStatus: {
                    type: Type.STRING,
                    description: "Must be 'Complied', 'Non-Compliant', 'Not Disclosed', or 'Not Applicable'",
                  },
                  detailedFinding: {
                    type: Type.STRING,
                    description: "Auditor observation on whether entity complied, missing items, or required note adjustment",
                  },
                  guidanceNoteReference: {
                    type: Type.STRING,
                    description: "e.g. ICAI Guidance Note on Div II to Schedule III / MCA Notification G.S.R. 207(E)",
                  },
                },
                required: ["clause", "requirement", "complianceStatus", "detailedFinding", "guidanceNoteReference"],
              },
            },
            part3Recommendations: {
              type: Type.ARRAY,
              description: "Actionable Audit Recommendations for the CA team before final signing",
              items: {
                type: Type.OBJECT,
                properties: {
                  id: { type: Type.STRING },
                  priority: {
                    type: Type.STRING,
                    description: "Immediate, Pre-Signing, or Management Letter",
                  },
                  category: { type: Type.STRING },
                  recommendation: {
                    type: Type.STRING,
                    description: "Concrete step-by-step audit action item",
                  },
                  statutoryReference: { type: Type.STRING },
                  actionFor: {
                    type: Type.STRING,
                    description: "e.g. Audit Senior, Engagement Partner, CFO / Management",
                  },
                },
                required: ["id", "priority", "category", "recommendation", "actionFor"],
              },
            },
            rawMarkdownReport: {
              type: Type.STRING,
              description: "Complete formal audit report in Markdown adhering strictly to all sections.",
            },
            financialHighlights: {
              type: Type.OBJECT,
              properties: {
                totalRevenue: { type: Type.STRING },
                pat: { type: Type.STRING },
                totalAssets: { type: Type.STRING },
                totalDebt: { type: Type.STRING },
                netWorth: { type: Type.STRING },
              },
            },
            caroObservations: {
              type: Type.ARRAY,
              items: { type: Type.STRING },
            },
          },
          required: [
            "summary",
            "part1Disclosures",
            "part2Inconsistencies",
            "part3Recommendations",
            "rawMarkdownReport",
          ],
        },
      },
    });

    const resultText = response.text;
    if (!resultText) {
      throw new Error("No output received from Gemini audit model.");
    }

    const auditData = JSON.parse(resultText);
    auditData.id = `audit-${Date.now()}`;
    auditData.timestamp = new Date().toISOString();
    auditData.documentTitle = fileName || auditData.summary.entityName || "Audited Financial Statement";

    res.json({ success: true, data: auditData });
  } catch (error: any) {
    console.error("Audit processing error:", error);
    res.status(500).json({
      error: error?.message || "An error occurred during financial statement disclosure analysis.",
    });
  }
});

// API route: Follow-up CA Audit Chat & Query Assistant
app.post("/api/audit/chat", async (req, res) => {
  try {
    const { question, contextReport, conversationHistory } = req.body;

    if (!question) {
      return res.status(400).json({ error: "Question is required." });
    }

    const ai = getGeminiClient();

    const systemPrompt = `You are a Senior Chartered Accountant, Technical Director of Accounting Standards, and Statutory Audit Partner.
You are assisting an audit team currently reviewing financial statements under Ind AS (Indian Accounting Standards) and AS.
You have the full context of the previously audited report and findings.

Answer the CA's technical query with high precision:
- Reference specific Ind AS / AS paragraph numbers, Guidance Notes by ICAI, Schedule III of Companies Act 2013, NFRA circulars, and CARO 2020 clauses.
- If requested to draft Audit Query Memos, MRL clauses, or Qualified Audit Report modifications, provide ready-to-use professional draft language.
- Maintain professional, objective, and authoritative CA communication.`;

    const contents: any[] = [];

    if (contextReport) {
      contents.push({
        role: "user",
        parts: [
          {
            text: `Here is the current Financial Statement Audit Report Context:\nEntity: ${contextReport.summary?.entityName || "Client Entity"}\nCompliance Score: ${contextReport.summary?.overallComplianceScore}\nKey Risks: ${contextReport.summary?.keyRiskAreas}\nDiscrepancies Count: ${contextReport.summary?.totalDiscrepancies}\n\nFull Findings:\n${contextReport.rawMarkdownReport || JSON.stringify(contextReport.part2Inconsistencies)}`,
          },
        ],
      });
      contents.push({
        role: "model",
        parts: [
          {
            text: "Acknowledged. I have reviewed the audit report, Ind AS disclosure checklist, and internal consistency findings for this entity. How can I assist with this audit engagement?",
          },
        ],
      });
    }

    if (Array.isArray(conversationHistory)) {
      for (const msg of conversationHistory) {
        contents.push({
          role: msg.sender === "user" ? "user" : "model",
          parts: [{ text: msg.content }],
        });
      }
    }

    contents.push({
      role: "user",
      parts: [{ text: question }],
    });

    const chatResponse = await ai.models.generateContent({
      model: "gemini-3.7-flash",
      contents,
      config: {
        systemInstruction: systemPrompt,
        temperature: 0.2,
      },
    });

    const reply = chatResponse.text;
    res.json({ success: true, reply });
  } catch (error: any) {
    console.error("Chat assistant error:", error);
    res.status(500).json({ error: error?.message || "Failed to process audit consultation query." });
  }
});

// API route: Quick note reconciliation tool
app.post("/api/audit/reconcile-note", async (req, res) => {
  try {
    const { primaryLineName, primaryAmount, noteTitle, noteBreakupRows } = req.body;
    const ai = getGeminiClient();

    const prompt = `Reconcile the following Primary Statement Line Item against its Note Breakup:
Primary Line Item: "${primaryLineName}" with Reported Amount: "${primaryAmount}"
Note Title: "${noteTitle}"
Note Breakup Rows:
${JSON.stringify(noteBreakupRows, null, 2)}

Check:
1. Arithmetic sum of note items vs primary statement figure.
2. Casting and footing validation.
3. Proper classification under Ind AS / Schedule III.
4. Any MSME or sub-grouping issues.

Return a concise CA Reconciliation Memo with variance quantification and recommended adjustment entry.`;

    const response = await ai.models.generateContent({
      model: "gemini-3.7-flash",
      contents: prompt,
      config: {
        temperature: 0.1,
      },
    });

    res.json({ success: true, memo: response.text });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Vite middleware setup
async function startServer() {
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
    console.log(`Financial Audit Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
