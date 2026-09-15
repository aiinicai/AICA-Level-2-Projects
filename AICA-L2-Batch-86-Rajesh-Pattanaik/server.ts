import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { GoogleGenAI, Type } from '@google/genai';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(express.json({ limit: '10mb' }));

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Verification API endpoint
app.post('/api/verify', async (req, res) => {
  const { question, aiAnswer, sourceMaterial } = req.body;

  if (!question?.trim() || !aiAnswer?.trim()) {
    return res.status(400).json({
      error: 'Please provide both the Professional Question / Case Facts and the AI-Generated Answer.'
    });
  }

  const hasSources = Boolean(sourceMaterial && sourceMaterial.trim().length > 0);
  const cleanSources = hasSources ? sourceMaterial.trim() : '';

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return res.status(500).json({
      error: 'GEMINI_API_KEY environment variable is not configured. Please ensure your Gemini API key is configured in Settings > Secrets.'
    });
  }

  try {
    const ai = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build'
        }
      }
    });

    const systemInstruction = `You are CA VerifyAI, a rigorous and meticulous AI-assisted statutory, regulatory and professional assurance engine for Chartered Accountants and CA students.
Core Purpose: "Don't just check what AI said. Check what AI may have missed."
Identify what an AI-generated professional answer says, what the authoritative sources support, and most importantly, what the AI may have missed.

CORE ARCHITECTURAL MANDATES:
1. Grounding & Anti-Hallucination:
   - Ground all verifications strictly against the supplied authoritative research sources when provided.
   - NEVER invent statutory sections, clauses, rules, circulars, notifications, case laws, quotations, citations or evidence.
   - If sources are provided and a statement is not corroborated, explicitly classify it as "NOT ESTABLISHED BY SUPPLIED SOURCES" or state "Not established by the supplied sources."

2. No-Source Behavior:
   ${
     !hasSources
       ? `CRITICAL: NO AUTHORITATIVE SOURCE WAS SUPPLIED BY THE USER.
   - Do NOT pretend the answer has been legally or statutorily verified.
   - Set isLimitedVerification to true.
   - Set limitedVerificationNotice to: "No authoritative reference material was supplied. The analysis below is an AI-assisted risk and completeness review and requires independent verification against current authoritative sources."
   - Set sourceReliability to "No Source Supplied".
   - Cap the Source-Supported Reliability Score at a maximum of 40/100, and explicitly explain that lack of primary documentation prevents legal corroboration.`
       : `Authoritative sources are supplied. Evaluate source hierarchy: distinguish PRIMARY/AUTHORITATIVE (Acts, Rules, Notifications, Circulars, ICAI guidance) vs SECONDARY (articles, commentaries). Secondary sources must not override primary statutory provisions.`
   }

3. Professional Impact & Missed-Issue Analysis (Central Differentiating Feature):
   - First identify the material facts from the question.
   - Determine which professional domains are reasonably triggered (e.g. Income Tax, GST / Indirect Tax, TDS / TCS, Accounting Standards / Ind AS, Companies Act / Corporate Law, Auditing / Standards on Auditing, CARO reporting, FEMA, etc.).
   - DO NOT force every domain into every case. Only include domains reasonably triggered by the actual facts.
   - For each triggered domain, state:
     * domain name
     * why it may apply based on facts
     * relevant statutory provision / area
     * practical impact
     * whether the AI answer addressed it ("Addressed", "Partially Addressed", or "Missed / Omitted")
     * verification required by the CA

4. Missed-Issue Engine:
   - Ask: "Even if the AI's primary answer is correct, what relevant professional consequences, provisions, reporting requirements, penalties, accounting effects or related issues may have been missed?"
   - Look specifically for: connected laws, GST consequences, TDS/TCS obligations, reporting thresholds, penalties/interest, CARO implications, financial statement impact, conditions precedent, documentation/evidence requirements.
   - Do NOT invent artificial issues. If no additional issue is reasonably triggered, state: "No material additional issue was identified from the supplied information."

5. Claim-by-Claim Statuses:
   For key assertions in the AI answer, assess:
   - "SUPPORTED" (🟢 Direct source corroboration)
   - "REQUIRES VERIFICATION" (🟠 Ambiguous, conditional, or assumption-dependent)
   - "POTENTIAL ERROR" (🔴 Statutory contradiction, outdated provision, or threshold misstatement)
   - "NOT ESTABLISHED BY SUPPLIED SOURCES" (🔵 Source silent or unprovided)

6. Source-Supported Reliability Score (0 to 100):
   - Score reflects support, consistency, and completeness against supplied information and sources. It is NOT a probability of legal correctness.
   - Provide breakdown: sourceSupport ("High" | "Moderate" | "Low" | "None"), completeness ("Comprehensive" | "Partial" | "Significant Omissions"), professionalRisk ("Low" | "Moderate" | "Elevated" | "Critical").`;

    const userPrompt = `TASK: Perform a comprehensive CA VerifyAI professional verification and missed-issue analysis.

CASE / PROFESSIONAL QUESTION:
${question}

AI-GENERATED ANSWER TO VERIFY:
${aiAnswer}

AUTHORITATIVE RESEARCH SOURCES:
${hasSources ? cleanSources : '[NO SOURCES PROVIDED BY USER — EXECUTE LIMITED RISK & COMPLETENESS REVIEW]'}

Execute rigorous professional analysis and return structured JSON matching the schema.`;

    const modelsToTry = ['gemini-3.8-flash', 'gemini-3.1-flash-lite', 'gemini-2.5-flash'];
    let lastError: any = null;
    let reportText: string | undefined;

    for (const model of modelsToTry) {
      try {
        const response = await ai.models.generateContent({
          model,
          contents: userPrompt,
          config: {
            systemInstruction,
            temperature: 0.1,
            responseMimeType: 'application/json',
            responseSchema: {
              type: Type.OBJECT,
              properties: {
                isLimitedVerification: { type: Type.BOOLEAN },
                limitedVerificationNotice: { type: Type.STRING },
                sourceReliability: {
                  type: Type.STRING,
                  description: 'Must be one of: "Primary Authoritative", "Mixed / Secondary", "Limited / Unverified", "No Source Supplied"'
                },
                sourceReliabilityDetails: { type: Type.STRING },
                overallStatus: {
                  type: Type.STRING,
                  description: 'Must be one of: "High Support", "Generally Supported — Verify", "Significant Verification Required", "Potentially Unreliable"'
                },
                verificationScore: {
                  type: Type.INTEGER,
                  description: 'Source-Supported Reliability Score from 0 to 100'
                },
                scoreExplanation: { type: Type.STRING },
                scoreBreakdown: {
                  type: Type.OBJECT,
                  properties: {
                    sourceSupport: { type: Type.STRING, description: 'High, Moderate, Low, or None' },
                    completeness: { type: Type.STRING, description: 'Comprehensive, Partial, or Significant Omissions' },
                    professionalRisk: { type: Type.STRING, description: 'Low, Moderate, Elevated, or Critical' }
                  },
                  required: ['sourceSupport', 'completeness', 'professionalRisk']
                },
                executiveVerdict: { type: Type.STRING },
                keyFacts: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      id: { type: Type.STRING },
                      fact: { type: Type.STRING },
                      category: { type: Type.STRING }
                    },
                    required: ['id', 'fact', 'category']
                  }
                },
                applicableDomains: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      domain: { type: Type.STRING },
                      whyItApplies: { type: Type.STRING },
                      relevantProvision: { type: Type.STRING },
                      impact: { type: Type.STRING },
                      aiAddressedStatus: {
                        type: Type.STRING,
                        description: 'Must be one of: "Addressed", "Partially Addressed", "Missed / Omitted"'
                      },
                      verificationRequired: { type: Type.STRING }
                    },
                    required: ['domain', 'whyItApplies', 'relevantProvision', 'impact', 'aiAddressedStatus', 'verificationRequired']
                  }
                },
                supportedClaims: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      id: { type: Type.STRING },
                      claim: { type: Type.STRING },
                      status: { type: Type.STRING, description: 'SUPPORTED' },
                      sourceEvidence: { type: Type.STRING },
                      analysis: { type: Type.STRING },
                      professionalImplication: { type: Type.STRING }
                    },
                    required: ['id', 'claim', 'status', 'sourceEvidence', 'analysis', 'professionalImplication']
                  }
                },
                questionableClaims: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      id: { type: Type.STRING },
                      claim: { type: Type.STRING },
                      status: { type: Type.STRING, description: '"REQUIRES VERIFICATION" or "NOT ESTABLISHED BY SUPPLIED SOURCES"' },
                      sourceEvidence: { type: Type.STRING },
                      analysis: { type: Type.STRING },
                      professionalImplication: { type: Type.STRING },
                      missingEvidenceNotice: { type: Type.STRING }
                    },
                    required: ['id', 'claim', 'status', 'sourceEvidence', 'analysis', 'professionalImplication']
                  }
                },
                potentialErrors: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      id: { type: Type.STRING },
                      errorType: {
                        type: Type.STRING,
                        description: 'One of: statutory_misstatement, numerical_or_threshold_error, factual_contradiction, outdated_provision'
                      },
                      statementInAIAnswer: { type: Type.STRING },
                      contradictingSourceEvidence: { type: Type.STRING },
                      analysis: { type: Type.STRING },
                      professionalImplication: { type: Type.STRING },
                      severity: { type: Type.STRING, description: 'high or medium' }
                    },
                    required: ['id', 'errorType', 'statementInAIAnswer', 'contradictingSourceEvidence', 'analysis', 'professionalImplication', 'severity']
                  }
                },
                missedIssues: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      id: { type: Type.STRING },
                      domain: { type: Type.STRING },
                      issueTitle: { type: Type.STRING },
                      applicableProvision: { type: Type.STRING },
                      description: { type: Type.STRING },
                      whyMissedByAI: { type: Type.STRING },
                      consequenceOrPenalty: { type: Type.STRING },
                      severity: { type: Type.STRING, description: 'high, medium, or low' },
                      actionRequired: { type: Type.STRING }
                    },
                    required: ['id', 'domain', 'issueTitle', 'applicableProvision', 'description', 'whyMissedByAI', 'consequenceOrPenalty', 'severity', 'actionRequired']
                  }
                },
                sourceEvidenceList: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      id: { type: Type.STRING },
                      aiClaim: { type: Type.STRING },
                      status: { type: Type.STRING, description: 'SUPPORTED, REQUIRES VERIFICATION, POTENTIAL ERROR, or NOT ESTABLISHED' },
                      sourceHierarchy: { type: Type.STRING, description: 'PRIMARY / AUTHORITATIVE, SECONDARY, or NOT SUPPLIED' },
                      sourceEvidence: { type: Type.STRING },
                      analysis: { type: Type.STRING },
                      professionalImplication: { type: Type.STRING }
                    },
                    required: ['id', 'aiClaim', 'status', 'sourceHierarchy', 'sourceEvidence', 'analysis', 'professionalImplication']
                  }
                },
                consequencesAndPenalties: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      id: { type: Type.STRING },
                      area: { type: Type.STRING },
                      provision: { type: Type.STRING },
                      riskLevel: { type: Type.STRING, description: 'Critical, Moderate, or Advisory' },
                      description: { type: Type.STRING },
                      statutoryPenaltyOrImpact: { type: Type.STRING }
                    },
                    required: ['id', 'area', 'provision', 'riskLevel', 'description', 'statutoryPenaltyOrImpact']
                  }
                },
                recommendedProfessionalActions: {
                  type: Type.ARRAY,
                  items: { type: Type.STRING }
                },
                professionalRelianceWarning: { type: Type.STRING }
              },
              required: [
                'sourceReliability',
                'sourceReliabilityDetails',
                'overallStatus',
                'verificationScore',
                'scoreExplanation',
                'scoreBreakdown',
                'executiveVerdict',
                'professionalRelianceWarning'
              ]
            }
          }
        });

        reportText = response.text;
        if (reportText) {
          break;
        }
      } catch (err: any) {
        console.warn(`Model ${model} attempt failed:`, err?.message || err);
        lastError = err;
        await new Promise((resolve) => setTimeout(resolve, 800));
      }
    }

    if (!reportText) {
      throw lastError || new Error('Empty response received from Gemini API');
    }

    const parsedReport = JSON.parse(reportText);
    parsedReport.verificationTimestamp = new Date().toISOString();

    // Ensure array safety
    parsedReport.keyFacts = parsedReport.keyFacts || [];
    parsedReport.applicableDomains = parsedReport.applicableDomains || [];
    parsedReport.supportedClaims = parsedReport.supportedClaims || [];
    parsedReport.questionableClaims = parsedReport.questionableClaims || [];
    parsedReport.potentialErrors = parsedReport.potentialErrors || [];
    parsedReport.missedIssues = parsedReport.missedIssues || [];
    parsedReport.sourceEvidenceList = parsedReport.sourceEvidenceList || [];
    parsedReport.consequencesAndPenalties = parsedReport.consequencesAndPenalties || [];
    parsedReport.recommendedProfessionalActions = parsedReport.recommendedProfessionalActions || [];

    if (!hasSources) {
      parsedReport.isLimitedVerification = true;
      parsedReport.limitedVerificationNotice =
        'No authoritative reference material was supplied. The analysis below is an AI-assisted risk and completeness review and requires independent verification against current authoritative sources.';
      parsedReport.sourceReliability = 'No Source Supplied';
    }

    return res.json(parsedReport);
  } catch (error: any) {
    console.error('Error during verification:', error);
    return res.status(500).json({
      error: error?.message || 'Failed to complete verification. Please try again.'
    });
  }
});

// Setup Vite middleware in dev or static serving in production
async function setupViteOrStatic() {
  if (process.env.NODE_ENV !== 'production') {
    const { createServer: createViteServer } = await import('vite');
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
    console.log(`CA VerifyAI Server running on http://0.0.0.0:${PORT}`);
  });
}

setupViteOrStatic();
