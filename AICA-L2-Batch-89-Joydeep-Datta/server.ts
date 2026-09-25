import express, { Request, Response } from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import path from 'path';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

app.use(express.json());

// Initialize Gemini API client according to @google/genai guidelines
const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
  httpOptions: {
    headers: {
      'User-Agent': 'aistudio-build',
    },
  },
});

// Resilient caller with model fallback and per-request timeout
async function generateGeminiWithFallback(
  contents: string,
  options: { responseMimeType?: string; temperature?: number } = {},
  timeoutMs = 12000
) {
  const models = ['gemini-flash-latest', 'gemini-3.1-flash-lite', 'gemini-3.8-flash'];
  let lastError: any = null;

  for (const model of models) {
    try {
      const callPromise = ai.models.generateContent({
        model,
        contents,
        config: {
          ...(options.responseMimeType ? { responseMimeType: options.responseMimeType } : {}),
          temperature: options.temperature ?? 0.3,
        },
      });

      // Race with timeout
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout after ${timeoutMs}ms on model ${model}`)), timeoutMs)
      );

      const response = await Promise.race([callPromise, timeoutPromise]);
      if (response && response.text) {
        return response.text;
      }
    } catch (err: any) {
      console.warn(`Model ${model} failed, trying next:`, err?.message || err);
      lastError = err;
    }
  }

  throw lastError || new Error('All Gemini model fallbacks exhausted');
}

/**
 * Endpoint 1: Comprehensive Smart Tax Regime Optimization & Advisory
 */
app.post('/api/ai/tax-optimize', async (req: Request, res: Response) => {
  try {
    const { employee, declaration, taxConfig, oldBreakdown, newBreakdown } = req.body;

    if (!employee || !taxConfig) {
      return res.status(400).json({ error: 'Missing employee or tax configuration data.' });
    }

    const diff = (oldBreakdown?.totalAnnualTaxLiability || 0) - (newBreakdown?.totalAnnualTaxLiability || 0);
    const betterRegime = diff > 0 ? 'New' : diff < 0 ? 'Old' : 'Equal';
    const annualSavings = Math.abs(diff);

    const prompt = `You are a senior Indian Chartered Accountant (CA) and Statutory Payroll Specialist for Assessment Year 2026-27 (FY 2026-27).
Provide an in-depth, personalized, and actionable tax regime optimization and advisory report for this employee based on their exact compensation and declared deductions.

EMPLOYEE PROFILE:
- Name: ${employee.employeeName} (${employee.employeeCode})
- Designation: ${employee.designation} | Department: ${employee.department}
- Annual CTC: ₹${(employee.annualCtc || 0).toLocaleString('en-IN')}
- Basic Monthly: ₹${(employee.basicMonthly || 0).toLocaleString('en-IN')} (Annual Basic: ₹${((employee.basicMonthly || 0) * 12).toLocaleString('en-IN')})
- HRA Monthly: ₹${(employee.hraMonthly || 0).toLocaleString('en-IN')} (Annual HRA: ₹${((employee.hraMonthly || 0) * 12).toLocaleString('en-IN')})
- Special Allowance Monthly: ₹${(employee.specialAllowanceMonthly || 0).toLocaleString('en-IN')}
- Other Allowances Monthly: ₹${((employee.conveyanceAllowanceMonthly || 0) + (employee.childrenEducationAllowanceMonthly || 0) + (employee.ltaMonthly || 0)).toLocaleString('en-IN')}
- Employee PF (12%): ₹${(employee.employeePfMonthly || 0).toLocaleString('en-IN')}/mo
- Current Opted Regime in Master/Declaration: ${declaration?.regimeDeclared || employee.taxRegimeOpted || 'New'} Regime

DECLARED DEDUCTIONS & EXEMPTIONS (AY 2026-27):
- Annual Rent Paid: ₹${(declaration?.rentPaidAnnual || 0).toLocaleString('en-IN')} (${declaration?.rentedCityMetro === 'Y' ? 'Metro 50%' : 'Non-Metro 40%'})
- Landlord PAN: ${declaration?.landlordPan || 'Not Provided'}
- Section 80C (PPF, ELSS, EPF, LIC, Housing Principal, etc.): Total Declared ₹${(
      (declaration?.ppf || 0) +
      (declaration?.licPremium || 0) +
      (declaration?.elssMutualFund || 0) +
      (declaration?.housingLoanPrincipal || 0) +
      (declaration?.tuitionFees || 0) +
      (declaration?.taxSaverFd5yr || 0)
    ).toLocaleString('en-IN')} (Capped at ₹1,50,000 in Old Regime)
- Section 80CCD(1B) Tier-1 NPS: ₹${(declaration?.npsSelf80CCD1B || 0).toLocaleString('en-IN')} (Eligible up to ₹50,000 in Old Regime)
- Section 80D Mediclaim (Self & Family): ₹${(declaration?.mediclaimSelfFamily || 0).toLocaleString('en-IN')}
- Section 80D Mediclaim (Parents): ₹${(declaration?.mediclaimParents || 0).toLocaleString('en-IN')} (Senior citizen: ${declaration?.parentsSeniorCitizen === 'Y' ? 'Yes, up to ₹50,000' : 'No, up to ₹25,000'})
- Section 24(b) Home Loan Interest: ₹${(declaration?.housingLoanInterestSelfOccupied || 0).toLocaleString('en-IN')} (Capped at ₹2,00,000 in Old Regime)

DETERMINISTIC TAX ENGINE COMPUTATION (AY 2026-27 Budget Provisions):
- Old Regime:
  * Gross Total Income: ₹${(oldBreakdown?.annualGrossSalary || 0).toLocaleString('en-IN')}
  * Standard Deduction: ₹50,000
  * Section 10 Exemptions (HRA): ₹${(oldBreakdown?.exemptionsSec10?.hra || 0).toLocaleString('en-IN')}
  * Total Deductions (80C + 80D + NPS + 24b): ₹${(oldBreakdown?.chapterViaDeductions?.total || 0).toLocaleString('en-IN')}
  * Net Taxable Income: ₹${(oldBreakdown?.netTaxableIncome || 0).toLocaleString('en-IN')}
  * Total Annual Tax Liability (including 4% cess): ₹${(oldBreakdown?.totalAnnualTaxLiability || 0).toLocaleString('en-IN')}

- New Regime (Section 115BAC Default):
  * Gross Total Income: ₹${(newBreakdown?.annualGrossSalary || 0).toLocaleString('en-IN')}
  * Standard Deduction: ₹75,000 (Revised under FY 2026-27 rules)
  * Net Taxable Income: ₹${(newBreakdown?.netTaxableIncome || 0).toLocaleString('en-IN')}
  * Total Annual Tax Liability (including 4% cess, with Sec 87A full rebate up to ₹12L net taxable income): ₹${(newBreakdown?.totalAnnualTaxLiability || 0).toLocaleString('en-IN')}

- Difference: ${diff > 0 ? `New Regime saves ₹${annualSavings.toLocaleString('en-IN')}` : diff < 0 ? `Old Regime saves ₹${annualSavings.toLocaleString('en-IN')}` : 'Both regimes yield equal tax'}

Please output a structured JSON response matching this exact schema:
{
  "recommendedRegime": "Old" | "New",
  "annualTaxSavings": number (exact positive integer),
  "monthlyTakeHomeGain": number (exact positive integer),
  "headline": string (one powerful sentence with the financial verdict),
  "executiveSummary": string (2-3 crisp sentences summarizing why this regime wins for this employee),
  "keyDrivers": [
    string (e.g. "₹75,000 higher standard deduction in New Regime...", "High HRA exemption of ₹X under Old Regime...")
  ],
  "actionableTips": [
    {
      "section": string (e.g. "Section 80CCD(1B) NPS", "Section 80D Health Insurance", "HRA Documentation"),
      "title": string,
      "maxLimit": string,
      "currentDeclared": string,
      "potentialSavings": string,
      "actionRecommendation": string,
      "priority": "High" | "Medium" | "Low"
    }
  ],
  "hraDeepDive": {
    "annualHraReceived": number,
    "exemptAmount": number,
    "taxableHra": number,
    "landlordPanRequired": boolean,
    "complianceNote": string
  },
  "regimeSwitchGuidance": {
    "actionNeeded": string,
    "deadline": string,
    "impactOnMonthlyTds": string
  },
  "personalizedFaqs": [
    {
      "question": string,
      "answer": string
    }
  ]
}`;

    const rawJson = await generateGeminiWithFallback(
      prompt,
      { responseMimeType: 'application/json', temperature: 0.2 },
      14000
    );

    const parsed = JSON.parse(rawJson || '{}');
    return res.json(parsed);
  } catch (error: any) {
    console.error('Error generating AI tax optimization report:', error);
    return res.status(500).json({
      error: 'Failed to generate AI tax optimization report.',
      details: error?.message || String(error),
    });
  }
});

/**
 * Endpoint 2: Interactive Tax & Payroll AI Copilot
 */
app.post('/api/ai/tax-ask', async (req: Request, res: Response) => {
  try {
    const { question, employee, declaration, taxConfig, oldBreakdown, newBreakdown } = req.body;

    if (!question) {
      return res.status(400).json({ error: 'Question is required.' });
    }

    const contextPrompt = `You are the AI Personal Tax Advisor for ${employee?.employeeName || 'the employee'} at Acme Enterprises.
The employee's financial context:
- Designation: ${employee?.designation}, Department: ${employee?.department}
- Annual CTC: ₹${(employee?.annualCtc || 0).toLocaleString('en-IN')}
- Basic: ₹${((employee?.basicMonthly || 0) * 12).toLocaleString('en-IN')}/year, HRA: ₹${((employee?.hraMonthly || 0) * 12).toLocaleString('en-IN')}/year
- Currently Opted Regime: ${declaration?.regimeDeclared || employee?.taxRegimeOpted || 'New'}
- Computed Old Regime Tax: ₹${(oldBreakdown?.totalAnnualTaxLiability || 0).toLocaleString('en-IN')}
- Computed New Regime Tax: ₹${(newBreakdown?.totalAnnualTaxLiability || 0).toLocaleString('en-IN')}
- Annual Rent Paid: ₹${(declaration?.rentPaidAnnual || 0).toLocaleString('en-IN')}
- Section 80C Declared: ₹${(
      (declaration?.ppf || 0) +
      (declaration?.licPremium || 0) +
      (declaration?.elssMutualFund || 0) +
      (declaration?.housingLoanPrincipal || 0)
    ).toLocaleString('en-IN')}
- Section 80CCD(1B) NPS Declared: ₹${(declaration?.npsSelf80CCD1B || 0).toLocaleString('en-IN')}
- Section 80D Mediclaim: ₹${((declaration?.mediclaimSelfFamily || 0) + (declaration?.mediclaimParents || 0)).toLocaleString('en-IN')}

Answer the employee's question directly, clearly, and empathetically using the rules of Indian Income Tax Act for AY 2026-27 (FY 2026-27).
Keep figures accurate to Indian currency formatting (₹). Keep the response conversational, structured with bullet points where appropriate, and actionable.

EMPLOYEE QUESTION:
"${question}"`;

    try {
      const answer = await generateGeminiWithFallback(contextPrompt, { temperature: 0.3 }, 12000);
      return res.json({ answer });
    } catch (aiErr: any) {
      console.warn('Gemini fallback triggered for question:', question, aiErr);
      // Deterministic expert tax response generator
      const lower = question.toLowerCase();
      let response = `**Statutory Tax Guidance for AY 2026–27:**\n\n`;

      if (lower.includes('hra') || lower.includes('rent')) {
        const exempt = oldBreakdown?.exemptionsSec10?.hra || 0;
        response += `• **HRA Exemption (Sec 10(13A)):** In the Old Regime, HRA exemption is computed as the minimum of:
1. Actual HRA received (₹${((employee?.hraMonthly || 0) * 12).toLocaleString('en-IN')}/year)
2. Rent paid minus 10% of basic (Declared rent: ₹${(declaration?.rentPaidAnnual || 0).toLocaleString('en-IN')})
3. ${declaration?.rentedCityMetro === 'Y' ? '50%' : '40%'} of basic salary.
Your currently eligible exempt HRA is **₹${exempt.toLocaleString('en-IN')}**.
${(declaration?.rentPaidAnnual || 0) > 100000 ? '\n*Note:* Because annual rent exceeds ₹1,00,000, your landlord’s PAN is legally mandatory for TDS deduction relief.' : ''}`;
      } else if (lower.includes('80c') || lower.includes('ppf') || lower.includes('elss')) {
        response += `• **Section 80C Cap:** Maximum deduction allowed is **₹1,50,000** under the Old Tax Regime (EPF, PPF, ELSS, life insurance premiums, housing loan principal). Section 80C is *not* deductible under the New Tax Regime.`;
      } else if (lower.includes('nps') || lower.includes('80ccd')) {
        response += `• **NPS Tier-1 (Section 80CCD(1B)):** You can claim an exclusive deduction of up to **₹50,000** over and above the ₹1.5L Section 80C limit in the Old Tax Regime. In the 30% bracket, this saves ₹15,600 in tax.`;
      } else if (lower.includes('switch') || lower.includes('change') || lower.includes('opt')) {
        response += `• **Regime Switching:** Salaried employees can elect their preferred regime with their employer before the monthly payroll cut-off, or make a final choice when filing their annual Income Tax Return (ITR) u/s 139(1).`;
      } else {
        response += `• **Old vs New Regime:** The New Tax Regime offers lower tax rates, standard deduction of ₹75,000, and full rebate up to ₹7,00,000 net income. The Old Tax Regime allows claiming HRA, 80C, 80D, and home loan interest.`;
      }

      return res.json({ answer: response });
    }
  } catch (error: any) {
    console.error('Error answering tax question:', error);
    return res.status(500).json({
      error: 'Failed to answer question.',
      details: error?.message || String(error),
    });
  }
});

// Setup Vite development server middleware or static production serve
async function startServer() {
  if (process.env.NODE_ENV === 'production') {
    app.use(express.static('dist'));
    app.get('*', (_req: Request, res: Response) => {
      res.sendFile(path.resolve('dist', 'index.html'));
    });
  } else {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
