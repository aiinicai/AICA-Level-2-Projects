import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';
dotenv.config();

function getAiClient(): GoogleGenAI | null {
  dotenv.config();
  const apiKey = (process.env.GEMINI_API_KEY || '').trim();
  if (!apiKey || apiKey === 'MY_GEMINI_API_KEY') {
    return null;
  }
  return new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build',
      },
    },
  });
}

function formatGeminiError(err: any): string {
  const raw = err?.message || String(err || 'Unknown Gemini AI error');
  try {
    const parsed = JSON.parse(raw);
    const code = parsed?.error?.code;
    const msg = parsed?.error?.message;
    if (code === 400 || code === 403 || String(msg).toLowerCase().includes('api key')) {
      return 'Invalid or unauthorized Gemini API key. Please verify GEMINI_API_KEY in Settings > Secrets.';
    }
    if (code === 429) {
      return 'Gemini API quota/rate limit reached. Please wait a moment or check your billing tier in Settings > Secrets.';
    }
    if (code === 503) {
      return 'Gemini AI service is temporarily busy. Please try again in a few seconds.';
    }
    if (msg) return msg;
  } catch {
    // Not a JSON string
  }
  if (raw.includes('API_KEY_INVALID') || raw.includes('403')) {
    return 'Invalid or unauthorized Gemini API key. Please check GEMINI_API_KEY in Settings > Secrets.';
  }
  return raw;
}

function parseCleanJson<T>(rawText: string | undefined, fallback: T): T {
  if (!rawText) return fallback;
  const cleaned = rawText
    .trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim();
  return JSON.parse(cleaned) as T;
}

async function generateJsonWithRetry(ai: GoogleGenAI, prompt: string): Promise<string | undefined> {
  const attempts: Array<{ model: string; delayMs: number }> = [
    { model: 'gemini-4-hydrogen', delayMs: 0 },
    { model: 'gemini-4-hydrogen', delayMs: 800 },
    { model: 'gemini-3.1-flash-lite', delayMs: 400 }
  ];

  let lastError: any;
  for (const attempt of attempts) {
    if (attempt.delayMs > 0) {
      await new Promise(resolve => setTimeout(resolve, attempt.delayMs));
    }
    try {
      const response = await ai.models.generateContent({
        model: attempt.model,
        contents: prompt,
        config: {
          responseMimeType: 'application/json',
        },
      });
      return response.text;
    } catch (err: any) {
      lastError = err;
      const msg = String(err?.message || err || '');
      const isTransient =
        msg.includes('503') ||
        msg.includes('429') ||
        msg.includes('UNAVAILABLE') ||
        msg.toLowerCase().includes('high demand') ||
        msg.toLowerCase().includes('overloaded');
      if (!isTransient) {
        throw err;
      }
    }
  }
  throw lastError;
}

export async function handleCalendarEnrich(year: number, month: number) {
  const ai = getAiClient();
  if (!ai) {
    return {
      success: true,
      source: 'offline_fallback',
      message: 'Using built-in statutory calendar. To enable live Gemini AI updates, set GEMINI_API_KEY in Settings > Secrets.',
      events: []
    };
  }

  try {
    const prompt = `You are an expert Indian Chartered Accountant specializing in Punjab and Central tax compliance.
Provide all statutory tax deadlines and Punjab/National holidays & festivals for Month: ${month}, Year: ${year}.
Specifically include:
1. GST Deadlines: GSTR-1, GSTR-3B (monthly/quarterly), CMP-08, GSTR-9, GSTR-9C, ITC-04.
2. Income Tax Deadlines: TDS/TCS payments (7th), TDS quarterly returns (24Q, 26Q, 27Q), Advance Tax installments (15th of June/Sept/Dec/Mar), ITR filing due dates (31st July, 31st Oct, 30th Nov), Tax Audit report u/s 44AB (30th Sept).
3. Indian National & Gazetted Holidays + Punjab State Festivals: Lohri, Maghi, Baisakhi, Republic Day, Independence Day, Gandhi Jayanti, Children's Day, Guru Nanak Dev Ji Gurpurab, Shaheedi Jor Mela Fatehgarh Sahib, Diwali, Dussehra, Holi, etc.

Return strictly a JSON array of objects with keys:
- title (string): short event name
- date (string): YYYY-MM-DD
- category: one of ["GST", "INCOME_TAX", "PUNJAB_FESTIVAL", "GAZETTED_HOLIDAY", "STATUTORY"]
- description: brief note about the obligation or celebration
- urgency: "HIGH" | "MEDIUM" | "NORMAL"
`;

    const text = await generateJsonWithRetry(ai, prompt);
    const parsed = parseCleanJson<any[]>(text, []);
    return { success: true, source: 'gemini', events: Array.isArray(parsed) ? parsed : [] };
  } catch (err: any) {
    console.error('Gemini calendar error:', err);
    return { success: false, error: formatGeminiError(err) };
  }
}

export async function handleMsmeExtract(documentsSummary: string, fixedDefaults: Record<string, string>) {
  const ai = getAiClient();
  if (!ai) {
    return {
      success: true,
      source: 'offline_fallback',
      data: {
        applicantName: 'M/S GARG TRADING COMPANY',
        panNumber: 'ABCPG1234F',
        aadhaarMasked: 'XXXX-XXXX-8921',
        mobileNumber: '9876543210',
        emailId: 'rishugarg006@gmail.com',
        businessType: fixedDefaults.organizationType || fixedDefaults.businessType || 'Proprietorship',
        bankAccountNo: '50200012345678',
        ifscCode: fixedDefaults.defaultIfsc || 'HDFC0001234',
        dateOfCommencement: '2021-04-01',
        plantMachineryInvestmentLakhs: '18.50',
        annualTurnoverLakhs: '74.20',
        nicCode: fixedDefaults.defaultNicCode || fixedDefaults.defaultNic || '47110 - Retail sale in non-specialised stores',
        unitAddress: 'Bishnandi Bazaar, Jaitu, Punjab - 151202',
        extractedFromDocCount: 3,
        confidenceScore: 0.96,
        notes: 'Using built-in office preset extraction. Add GEMINI_API_KEY in Settings > Secrets for live Gemini AI document extraction.'
      }
    };
  }

  try {
    const prompt = `You are a Chartered Accountant Office AI assistant in Punjab.
A client submitted the following document text / metadata for an MSME Udyam Registration application:
"${documentsSummary}"

Office Fixed Defaults:
${JSON.stringify(fixedDefaults)}

Extract variable data and synthesize with office presets. If a field is missing, infer standard plausible CA client data or leave flag.
Return JSON with keys:
- applicantName (string)
- panNumber (string, 10 chars)
- aadhaarMasked (string, format XXXX-XXXX-1234)
- mobileNumber (string)
- emailId (string)
- businessType (e.g. Proprietorship, Partnership, Private Limited)
- bankAccountNo (string)
- ifscCode (string)
- dateOfCommencement (YYYY-MM-DD)
- plantMachineryInvestmentLakhs (string number)
- annualTurnoverLakhs (string number)
- nicCode (string with 5-digit NIC and description)
- unitAddress (string)
- extractedFromDocCount (number)
- confidenceScore (number between 0 and 1)
- notes (string CA guidance)
`;

    const text = await generateJsonWithRetry(ai, prompt);
    const parsed = parseCleanJson<Record<string, any>>(text, {});
    return { success: true, source: 'gemini', data: parsed };
  } catch (err: any) {
    console.error('Gemini MSME extract error:', err);
    return { success: false, error: formatGeminiError(err) };
  }
}

export async function handleAifAnalyze(documentsSummary: string, projectDetails: Record<string, any>) {
  const ai = getAiClient();
  if (!ai) {
    return {
      success: true,
      source: 'offline_fallback',
      analysis: {
        eligibleProject: true,
        projectType: projectDetails.activity || projectDetails.projectType || 'Cold Storage & Agro Processing Unit',
        location: projectDetails.location || 'Bathinda, Punjab',
        totalProjectCostLakhs: projectDetails.totalCost || '150.00',
        eligibleTermLoanLakhs: projectDetails.loanAmount || '120.00',
        promoterContributionLakhs: (
          Math.max(0, parseFloat(projectDetails.totalCost || '150') - parseFloat(projectDetails.loanAmount || '120'))
        ).toFixed(2),
        interestSubventionRatePercent: 3.0,
        subventionCapCrores: 2.0,
        tenureYears: 7,
        cgtmseCoverage: 'Eligible for 85% credit guarantee without collateral requirement',
        annualInterestSavingsLakhs: (parseFloat(projectDetails.loanAmount || '120') * 0.03).toFixed(2),
        totalInterestSaved7YearsLakhs: (parseFloat(projectDetails.loanAmount || '120') * 0.03 * 7 * 0.85).toFixed(2),
        eligibilityChecklist: [
          { item: 'Eligible Post-Harvest Infrastructure Activity', status: 'PASSED' },
          { item: 'Land Ownership / Clear Leasehold (Minimum 10 yrs)', status: 'PASSED' },
          { item: 'Viable DPR with DSCR > 1.50', status: 'PASSED' },
          { item: 'Bank In-Principle Sanction Availability', status: 'REQUIRED' }
        ],
        summaryRecommendation: 'Highly suitable project for Agriculture Infrastructure Fund (AIF). Full 3% interest subvention available on Term Loan up to ₹2 Crore. (Add GEMINI_API_KEY in Settings > Secrets for live Gemini AI DPR evaluation.)'
      }
    };
  }

  try {
    const prompt = `You are a specialist CA advisor for Central Govt Agriculture Infrastructure Fund (AIF) scheme in Punjab.
Analyze the project details and documents:
Project: ${JSON.stringify(projectDetails)}
Documents Content: "${documentsSummary}"

AIF Scheme Guidelines:
- 3% interest subvention per annum on term loans up to ₹2.00 Crore for a maximum period of 7 years.
- Credit guarantee coverage under CGTMSE for loans up to ₹2 Crore.
- Eligible activities: Cold chains, pack houses, ripening chambers, silos, sorting/grading, primary processing, custom hiring centers, etc.

Return JSON with keys:
- eligibleProject (boolean)
- projectType (string)
- location (string)
- totalProjectCostLakhs (string)
- eligibleTermLoanLakhs (string)
- promoterContributionLakhs (string)
- interestSubventionRatePercent (number, 3.0)
- subventionCapCrores (number, 2.0)
- tenureYears (number, max 7)
- cgtmseCoverage (string)
- annualInterestSavingsLakhs (string)
- totalInterestSaved7YearsLakhs (string)
- eligibilityChecklist (array of { item: string, status: "PASSED" | "WARNING" | "REQUIRED" })
- summaryRecommendation (string)
`;

    const text = await generateJsonWithRetry(ai, prompt);
    const parsed = parseCleanJson<Record<string, any>>(text, {});
    return { success: true, source: 'gemini', analysis: parsed };
  } catch (err: any) {
    console.error('Gemini AIF analyze error:', err);
    return { success: false, error: formatGeminiError(err) };
  }
}
