import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig, Plugin } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';
import { GoogleGenAI } from '@google/genai';

function safeViteClientPlugin(): Plugin {
  return {
    name: 'safe-vite-client',
    transform(code, id) {
      if (id.includes('client.mjs') || id.includes('bundledDevClient.mjs')) {
        return code
          .replace(
            'ws.send(JSON.stringify(data));',
            'if (typeof ws !== "undefined" && ws && ws.readyState === 1) { ws.send(JSON.stringify(data)); }'
          )
          .replace(
            'this.transport.send(payload).catch',
            'this.transport?.send?.(payload)?.catch'
          );
      }
    },
  };
}

function cfoCopilotApiPlugin(): Plugin {
  return {
    name: 'cfo-copilot-api-middleware',
    configureServer(server) {
      server.middlewares.use('/api/copilot/query', (req, res, next) => {
        if (req.method !== 'POST') return next();

        let rawBody = '';
        req.on('data', (chunk) => {
          rawBody += chunk;
        });

        req.on('end', async () => {
          try {
            const payload = JSON.parse(rawBody || '{}');
            const { question, metrics, topExceptions, dischargeSummary } = payload;
            const apiKey = process.env.GEMINI_API_KEY;

            if (!apiKey || apiKey === 'MY_GEMINI_API_KEY') {
              // Return 404/fallback signal so client-side deterministic engine executes smoothly
              res.setHeader('Content-Type', 'application/json');
              res.statusCode = 200;
              res.end(JSON.stringify({ fallback: true }));
              return;
            }

            const ai = new GoogleGenAI({
              apiKey,
              httpOptions: {
                headers: {
                  'User-Agent': 'aistudio-build',
                },
              },
            });

            const systemPrompt = `You are the executive Hospital CFO Copilot.
CRITICAL MANDATORY RULES:
1. AI must NOT independently calculate, guess, or invent any financial figures.
2. The deterministic control engine has ALREADY calculated all metrics, exposures, and exceptions.
3. You must ONLY use the provided calculated facts and summarize/explain them with executive precision.
4. Your response MUST be strictly structured in two markdown sections:
### 📊 Calculated Deterministic Facts (Zero Hallucination)
- List key verified metrics and figures verbatim from the context.
### 💡 Executive CFO Strategic Commentary & Action Items
- Provide CFO-level operational risk analysis, root-cause insights, and recommended workflow fixes.
5. Tone: Senior healthcare financial executive, terse, high-conviction, professional.
6. Central terminology: SERVICE -> CAPTURED -> BILLED -> CLAIMED -> APPROVED -> COLLECTED. Always use "Potential Financial Exposure", never call an exception an actual revenue loss.
7. INDIAN CONVENTIONS: Use Indian financial conventions: Rupee symbol (₹), Lakhs (e.g. ₹1.5 Lakh or ₹1,50,000), Crores (e.g. ₹1.2 Crore or ₹1,20,00,000). Never use dollar signs ($).`;

            const formatInrNum = (num: number) => {
              return `₹${(num || 0).toLocaleString('en-IN')}`;
            };

            const contextText = `User Question: "${question}"

CALCULATED DETERMINISTIC METRICS:
- Today's Discharges: ${metrics?.todaysDischarges ?? 0}
- Gross Billing: ${formatInrNum(metrics?.grossBilling ?? 0)}
- Total Expected Amount: ${formatInrNum(metrics?.totalExpectedAmount ?? 0)}
- Total Potential Financial Exposure: ${formatInrNum(metrics?.potentialFinancialExposure ?? 0)}
- Open Exceptions: ${metrics?.openExceptionsCount ?? 0} (${metrics?.criticalExceptionsCount ?? 0} Critical, ${metrics?.highExceptionsCount ?? 0} High, ${metrics?.mediumExceptionsCount ?? 0} Medium, ${metrics?.lowExceptionsCount ?? 0} Low)
- TPA Pending Claims: ${formatInrNum(metrics?.tpaPendingAmount ?? 0)}
- Outstanding Collections: ${formatInrNum(metrics?.outstandingCollections ?? 0)}
- Top Exposure Revenue Centre: ${metrics?.exposureByRevenueCentre?.[0]?.name ?? 'None'} (${formatInrNum(metrics?.exposureByRevenueCentre?.[0]?.amount ?? 0)})
- Top Exposure Department: ${metrics?.exceptionsByDepartment?.[0]?.department ?? 'None'} (${formatInrNum(metrics?.exceptionsByDepartment?.[0]?.exposure ?? 0)})
- Discharges with Exceptions: ${dischargeSummary?.withExceptions ?? 0} of ${dischargeSummary?.totalDischarges ?? 0}
- Top Exposure Encounter: ${dischargeSummary?.highestExposureEncounter ?? 'None'}

EXCEPTIONS BY CONTROL:
${(metrics?.exceptionsByControl ?? []).map((c: { title: string; count: number; exposure: number }) => `- ${c.title}: ${c.count} items, ${formatInrNum(c.exposure)} exposure`).join('\n')}

TOP PRIORITY EXCEPTIONS:
${(topExceptions ?? []).slice(0, 5).map((e: { Exception_ID: string; Encounter_ID: string; Control_ID: string; Revenue_Centre: string; Description: string; Exposure_Amount: number; Severity: string }) => `- [${e.Severity}] ${e.Exception_ID} (${e.Encounter_ID} / ${e.Control_ID}): ${e.Description} [Exposure: ${formatInrNum(e.Exposure_Amount)}]`).join('\n')}
`;

            async function generateWithFallback(): Promise<string | null> {
              const candidateModels = [
                'gemini-3.8-flash',
                'gemini-flash-latest',
                'gemini-3.1-flash-lite',
              ];

              for (const model of candidateModels) {
                for (let attempt = 0; attempt < 2; attempt++) {
                  try {
                    const response = await ai.models.generateContent({
                      model,
                      contents: [
                        {
                          role: 'user',
                          parts: [{ text: `${systemPrompt}\n\n${contextText}` }],
                        },
                      ],
                    });
                    if (response && response.text) {
                      return response.text;
                    }
                  } catch (err: unknown) {
                    const errStr = String(err);
                    const isTransient =
                      errStr.includes('503') ||
                      errStr.includes('UNAVAILABLE') ||
                      errStr.includes('high demand') ||
                      errStr.includes('429') ||
                      errStr.includes('RESOURCE_EXHAUSTED');

                    if (isTransient && attempt === 0) {
                      await new Promise((r) => setTimeout(r, 400));
                      continue;
                    }
                    break;
                  }
                }
              }
              return null;
            }

            const answer = await generateWithFallback();

            if (!answer) {
              res.setHeader('Content-Type', 'application/json');
              res.statusCode = 200;
              res.end(JSON.stringify({ fallback: true }));
              return;
            }

            res.setHeader('Content-Type', 'application/json');
            res.statusCode = 200;
            res.end(
              JSON.stringify({
                answer,
                calculatedFacts: [],
                strategicCommentary: [],
                suggestedFollowUps: [
                  'What needs my attention today?',
                  'Which departments have the highest potential exposure?',
                  'Why are pharmacy exceptions high?',
                  'Which TPA claims need follow-up?',
                ],
                groundedFigures: {
                  grossBilling: metrics?.grossBilling ?? 0,
                  potentialExposure: metrics?.potentialFinancialExposure ?? 0,
                  openExceptions: metrics?.openExceptionsCount ?? 0,
                  tpaPending: metrics?.tpaPendingAmount ?? 0,
                  overdueCollections: metrics?.outstandingCollections ?? 0,
                },
              })
            );
          } catch {
            res.setHeader('Content-Type', 'application/json');
            res.statusCode = 200;
            res.end(JSON.stringify({ fallback: true }));
          }
        });
      });

      // Semantic Column Mapping AI endpoint
      server.middlewares.use('/api/ingestion/map-columns', (req, res, next) => {
        if (req.method !== 'POST') return next();

        let rawBody = '';
        req.on('data', (chunk) => {
          rawBody += chunk;
        });

        req.on('end', async () => {
          try {
            const payload = JSON.parse(rawBody || '{}');
            const { datasetType, columns } = payload;
            const apiKey = process.env.GEMINI_API_KEY;

            if (!apiKey || apiKey === 'MY_GEMINI_API_KEY') {
              res.setHeader('Content-Type', 'application/json');
              res.statusCode = 200;
              res.end(JSON.stringify({ fallback: true }));
              return;
            }

            const ai = new GoogleGenAI({
              apiKey,
              httpOptions: {
                headers: {
                  'User-Agent': 'aistudio-build',
                },
              },
            });

            const schemaContext = `Target Dataset Type: ${datasetType}
Canonical Schemas Available:
- encounters: Encounter_ID (ID), Admission_Date (date), Discharge_Date (date), Department (string), Ward (string), Bed_Type (string), Payer_Type (string), Discharge_Status (string)
- services: Service_ID (ID), Encounter_ID (ID), Service_DateTime (date), Revenue_Centre (string), Service_Code (string), Description (string), Quantity (number), Expected_Amount (number)
- billing: Bill_ID (ID), Encounter_ID (ID), Service_ID (ID), Bill_DateTime (date), Billed_Quantity (number), Billed_Amount (number), Discount (number), Bill_Status (string)
- claims: Claim_ID (ID), Encounter_ID (ID), Claim_Amount (number), Approved_Amount (number), Rejected_Amount (number), Claim_Status (string), Submission_Date (date), Approval_Date (date)
- collections: Receipt_ID (ID), Encounter_ID (ID), Receipt_Date (date), Amount (number), Payment_Mode (string)
- tariff_master: Service_Code, Service_Description, Revenue_Centre, Standard_Tariff, Effective_From, Effective_To, Payer, Payer_Tariff
- budgets: Month, Department, Revenue_Budget, Expense_Budget`;

            const promptText = `You are a clinical and financial data integration specialist for a hospital ERP and Revenue Cycle Management system.
Given the target dataset type and source columns with sample values and inferred types, map each source column to the most appropriate canonical field from the target schema.

${schemaContext}

Source Columns to Map:
${JSON.stringify(columns, null, 2)}

OUTPUT FORMAT REQUIREMENTS:
Return a JSON array of objects. Do not include markdown code block syntax if possible, just the raw JSON:
[
  {
    "sourceColumn": "string",
    "canonicalField": "string (canonical field name or 'unmapped' if non-pertinent)",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "reason": "Clear explanation of semantic match",
    "isAmbiguous": boolean,
    "alternativeCandidates": ["alternative_field_1"]
  }
]

RULES:
1. ONLY map to canonical fields that exist for '${datasetType}'.
2. Mark confidence as 'HIGH' only if unambiguous (e.g. UHID -> Encounter_ID, Net Bill Value -> Billed_Amount, Invoice No -> Bill_ID).
3. If a field could represent multiple things or is ambiguous (e.g., "Amount" which could be gross, net, or discount), mark confidence as 'MEDIUM' or 'LOW' and set isAmbiguous: true.
4. Never create or infer financial values.
5. If non-relevant (e.g., patient phone number, doctor signature), set canonicalField to 'unmapped'.`;

            const candidateModels = [
              'gemini-3.8-flash',
              'gemini-flash-latest',
              'gemini-3.1-flash-lite',
            ];

            let rawResponseText: string | null = null;
            let modelUsed = 'gemini-3.8-flash';

            for (const model of candidateModels) {
              try {
                const response = await ai.models.generateContent({
                  model,
                  contents: [
                    {
                      role: 'user',
                      parts: [{ text: promptText }],
                    },
                  ],
                  config: {
                    responseMimeType: 'application/json',
                  },
                });
                if (response && response.text) {
                  rawResponseText = response.text;
                  modelUsed = model;
                  break;
                }
              } catch {
                continue;
              }
            }

            if (!rawResponseText) {
              res.setHeader('Content-Type', 'application/json');
              res.statusCode = 200;
              res.end(JSON.stringify({ fallback: true }));
              return;
            }

            let parsedMappings: unknown[] = [];
            try {
              parsedMappings = JSON.parse(rawResponseText);
              if (!Array.isArray(parsedMappings)) {
                if (parsedMappings && typeof parsedMappings === 'object' && Array.isArray((parsedMappings as any).mappings)) {
                  parsedMappings = (parsedMappings as any).mappings;
                }
              }
            } catch {
              parsedMappings = [];
            }

            res.setHeader('Content-Type', 'application/json');
            res.statusCode = 200;
            res.end(
              JSON.stringify({
                mappings: parsedMappings,
                modelUsed,
                source: 'gemini',
              })
            );
          } catch {
            res.setHeader('Content-Type', 'application/json');
            res.statusCode = 200;
            res.end(JSON.stringify({ fallback: true }));
          }
        });
      });

      // Agentic CFO Financial Review Endpoint
      server.middlewares.use('/api/cfo-review/generate', (req, res, next) => {
        if (req.method !== 'POST') return next();

        let rawBody = '';
        req.on('data', (chunk) => {
          rawBody += chunk;
        });

        req.on('end', async () => {
          try {
            const payload = JSON.parse(rawBody || '{}');
            const { user, evidence } = payload;

            // Security: Enforce RBAC on server side
            if (!user || (user.role !== 'CFO' && user.role !== 'Finance/Billing Manager')) {
              res.setHeader('Content-Type', 'application/json');
              res.statusCode = 403;
              res.end(JSON.stringify({ error: 'Forbidden: Insufficient privileges for CFO Review generation' }));
              return;
            }

            const apiKey = process.env.GEMINI_API_KEY;
            if (!apiKey || apiKey === 'MY_GEMINI_API_KEY') {
              res.setHeader('Content-Type', 'application/json');
              res.statusCode = 200;
              res.end(JSON.stringify({ fallback: true }));
              return;
            }

            const ai = new GoogleGenAI({
              apiKey,
              httpOptions: {
                headers: {
                  'User-Agent': 'aistudio-build',
                },
              },
            });

            const systemPrompt = `You are the executive Hospital CFO Copilot AI synthesizing an official CFO Financial Review Briefing.

CRITICAL MANDATORY RULES:
1. ZERO INVENTED NUMBERS: All financial amounts, variances, percentages, and IDs MUST strictly match the provided evidence payload. Never calculate or invent numbers.
2. STRICT TAXONOMY: Every bullet point must begin with one of:
   - **[FACT]**: A deterministic value returned directly by the system tools.
   - **[CALCULATED METRIC]**: A deterministic calculated metric (e.g. percentages, variances).
   - **[AI OBSERVATION]**: An analytical interpretation grounded in the supplied facts.
   - **[SUGGESTED ACTION]**: An actionable management recommendation for human consideration.
3. EMPTY STATE HONESTY: If a category, array, or metric has no findings or is 0, explicitly output: "_No material finding identified._" Never manufacture an observation merely to populate a section.
4. 10 MANDATORY SECTIONS (use exactly these markdown headings):
   # CFO Financial Review
   ## 1. Executive Financial Position
   ## 2. Priority Financial Matters
   ## 3. Revenue & Billing
   ## 4. Receivables
   ## 5. Insurance / TPA
   ## 6. Departmental Review
   ## 7. Tariff Review
   ## 8. Budget vs Actual (If budget data unavailable, state: "> ℹ️ **Budget Analysis Unavailable**: Budget data has not been uploaded for this reporting period.")
   ## 9. Suggested Management Actions
   ## 10. Evidence (Cite exact Exception IDs, Encounter IDs, and Claim IDs from the evidence)
5. INDIAN CURRENCY: Use Indian format: ₹ symbol, Lakhs (e.g. ₹1.5 Lakh), Crores (e.g. ₹1.2 Crore). Never use dollar ($) signs.`;

            const promptText = `${systemPrompt}\n\nVERIFIED FINANCIAL EVIDENCE PAYLOAD:\n${JSON.stringify(evidence, null, 2)}`;

            const candidateModels = [
              'gemini-3.8-flash',
              'gemini-flash-latest',
              'gemini-3.1-flash-lite',
            ];

            let markdown: string | null = null;
            let modelUsed = 'gemini-3.8-flash';

            for (const model of candidateModels) {
              try {
                const response = await ai.models.generateContent({
                  model,
                  contents: [
                    {
                      role: 'user',
                      parts: [{ text: promptText }],
                    },
                  ],
                });
                if (response && response.text) {
                  markdown = response.text;
                  modelUsed = model;
                  break;
                }
              } catch {
                continue;
              }
            }

            if (!markdown) {
              res.setHeader('Content-Type', 'application/json');
              res.statusCode = 200;
              res.end(JSON.stringify({ fallback: true }));
              return;
            }

            res.setHeader('Content-Type', 'application/json');
            res.statusCode = 200;
            res.end(
              JSON.stringify({
                markdown,
                modelUsed,
                source: 'ai_gemini',
              })
            );
          } catch {
            res.setHeader('Content-Type', 'application/json');
            res.statusCode = 200;
            res.end(JSON.stringify({ fallback: true }));
          }
        });
      });
    },
  };
}

export default defineConfig(() => {
  return {
    plugins: [
      safeViteClientPlugin(),
      react(),
      tailwindcss(),
      cfoCopilotApiPlugin(),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'icon.svg'],
        manifest: {
          id: '/',
          name: 'Hospital CFO Copilot',
          short_name: 'CFOCopilot',
          description:
            'Revenue Capture, Discharge Control & Financial Intelligence for Hospital CFOs',
          theme_color: '#0f172a',
          background_color: '#0f172a',
          display: 'standalone',
          start_url: '/',
          scope: '/',
          icons: [
            {
              src: '/pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/pwa-maskable-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2}'],
          maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
        },
        devOptions: {
          enabled: false,
        },
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      port: 3000,
      host: '0.0.0.0',
      forwardConsole: false,
      hmr: false,
    },
  };
});
