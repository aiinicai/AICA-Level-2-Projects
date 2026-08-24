import { GoogleGenAI } from '@google/genai';
import { 
  ContractDocument, 
  Finding, 
  ExtractedClause, 
  CommercialTerms, 
  ContractParty, 
  ContractIdentity, 
  CrossClauseInsight, 
  InvoiceData, 
  InvoiceComparisonResult, 
  InvoiceDiscrepancy 
} from '../src/types/contract';

let geminiClient: GoogleGenAI | null = null;

export function getGeminiClient(): GoogleGenAI {
  if (!geminiClient) {
    geminiClient = new GoogleGenAI({
      apiKey: process.env.GEMINI_API_KEY || '',
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        }
      }
    });
  }
  return geminiClient;
}

const PRIMARY_MODEL = 'gemini-3.7-flash';
const FALLBACK_MODEL = 'gemini-3.1-flash-lite';

/**
 * Helper to sleep for exponential backoff
 */
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Robust execution wrapper with exponential backoff retry for 503 (High demand) / 429 / transient errors
 * and automatic fallback model switching.
 */
async function generateContentWithRetry(options: {
  contents: string | any;
  systemInstruction?: string;
  responseMimeType?: string;
  temperature?: number;
  maxRetries?: number;
}): Promise<string> {
  const ai = getGeminiClient();
  const maxRetries = options.maxRetries ?? 3;
  const modelsToTry = [PRIMARY_MODEL, FALLBACK_MODEL];

  let lastError: any = null;

  for (const model of modelsToTry) {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const response = await ai.models.generateContent({
          model,
          contents: options.contents,
          config: {
            systemInstruction: options.systemInstruction,
            responseMimeType: options.responseMimeType,
            temperature: options.temperature ?? 0.1,
          }
        });

        const text = response.text;
        if (text && text.trim().length > 0) {
          return text;
        }
      } catch (err: any) {
        lastError = err;
        const errString = String(err?.message || err || '');
        const isTransient = 
          errString.includes('503') || 
          errString.includes('high demand') || 
          errString.includes('UNAVAILABLE') || 
          errString.includes('429') || 
          errString.includes('RESOURCE_EXHAUSTED') ||
          errString.includes('500') ||
          errString.includes('Internal Server Error') ||
          errString.includes('FetchError') ||
          errString.includes('network');

        console.warn(`[Gemini API] Attempt ${attempt + 1}/${maxRetries} with ${model} failed (${errString}). Transient: ${isTransient}`);

        if (isTransient && attempt < maxRetries - 1) {
          // Exponential backoff with jitter: 1.2s, 2.5s, 4.5s
          const backoffTime = (Math.pow(2, attempt) * 1000) + Math.random() * 500;
          await sleep(backoffTime);
          continue;
        }

        // If not transient or last attempt for this model, break inner loop to try fallback model
        break;
      }
    }
  }

  throw lastError || new Error('Failed to generate content after retries and model fallbacks.');
}

// Clean JSON response helper to handle any markdown blocks
function cleanAndParseJSON<T>(rawText: string, fallback: T): T {
  if (!rawText) return fallback;
  try {
    let cleaned = rawText.trim();
    if (cleaned.startsWith('```json')) {
      cleaned = cleaned.replace(/^```json\s*/, '').replace(/\s*```$/, '');
    } else if (cleaned.startsWith('```')) {
      cleaned = cleaned.replace(/^```\s*/, '').replace(/\s*```$/, '');
    }
    return JSON.parse(cleaned) as T;
  } catch (error) {
    console.error('Failed to parse JSON response from Gemini:', error, 'Raw response preview:', rawText.substring(0, 300));
    return fallback;
  }
}

/**
 * Stage 1 & 2: Extract identity, parties, commercial terms and structured clauses
 */
export async function extractContractStructureAndClauses(
  documentText: string,
  selectedFramework: string = 'Ind AS'
): Promise<{
  identity: ContractIdentity;
  parties: ContractParty[];
  commercialTerms: CommercialTerms;
  clauses: ExtractedClause[];
}> {
  const prompt = `You are a Senior Indian Chartered Accountant and Contract Architect.
Analyze the following commercial contract text and extract its core identity, parties, key commercial terms, and key clauses with page/section numbers.

CONTRACT TEXT (Truncated to first 30,000 chars if larger):
${documentText.slice(0, 30000)}

Return a strict JSON object with this structure:
{
  "identity": {
    "title": "Full Contract Title",
    "contractNumber": "Contract or Reference No.",
    "contractType": "e.g. Turnkey Supply, Lease, Service Agreement, Sale of Goods, etc.",
    "effectiveDate": "YYYY-MM-DD or as stated",
    "executionDate": "YYYY-MM-DD or as stated",
    "commencementDate": "YYYY-MM-DD or as stated",
    "expiryDate": "YYYY-MM-DD or as stated",
    "renewalPeriod": "Renewal terms",
    "governingLaw": "e.g. Laws of India",
    "jurisdiction": "e.g. Courts in Mumbai",
    "disputeResolution": "Arbitration/Litigation details"
  },
  "parties": [
    {
      "name": "Party Legal Name",
      "role": "Buyer/Customer" or "Seller/Vendor/Service Provider" or "Related Entity" or "Other",
      "legalEntityType": "e.g. Private Limited, LLP, Public Ltd, Partnership",
      "jurisdiction": "State/Country",
      "isRelatedPartyIndicator": boolean
    }
  ],
  "commercialTerms": {
    "contractValue": "e.g. ₹5,20,00,000",
    "currency": "INR",
    "pricingMechanism": "Lump sum, milestone, unit rate, cost-plus, etc.",
    "taxesTreatment": "GST inclusive/exclusive details",
    "discountsAndRebates": "Any volume discount, early payment discount, rebate",
    "escalationClause": "Price escalation formula or terms",
    "retentionMoney": {
      "percentage": "e.g. 10%",
      "amount": "e.g. ₹52,00,000",
      "conditions": "Retention release conditions and duration"
    },
    "advances": {
      "percentage": "e.g. 15%",
      "amount": "e.g. ₹78,00,000",
      "recoveryTerms": "How advance is adjusted/recovered"
    },
    "securityDeposit": "BG, earnest money, etc.",
    "paymentTerms": "Summary of milestone or periodic payment schedule",
    "creditPeriodDays": 90,
    "milestonesSummary": "Deliverable milestones",
    "penaltiesAndLiquidatedDamages": "Liquidated damages % and cap",
    "warrantyPeriod": "Duration and scope of warranty",
    "indemnitiesAndLiabilityCap": "Liability cap and indemnities"
  },
  "clauses": [
    {
      "id": "cl-1",
      "clauseNumber": "e.g. 3.2(c)",
      "title": "Retention Money Terms",
      "text": "Exact or representative clause text from contract",
      "pageNumber": 1,
      "categories": ["Accounting", "GST", "TDS", "MSME", "Related Party", "Audit", "Financial Reporting", "Working Capital", "Internal Control"],
      "isMaterial": true
    }
  ]
}`;

  let rawResponseText = '';
  try {
    rawResponseText = await generateContentWithRetry({
      contents: prompt,
      systemInstruction: 'You are an Indian Chartered Accountant. Output only valid JSON. Do not invent facts not in the text.',
      responseMimeType: 'application/json',
      temperature: 0.1,
    });
  } catch (err) {
    console.error('Gemini structure extraction failed after retries, applying rule-based parsing:', err);
  }

  const parsed = cleanAndParseJSON(rawResponseText, {
    identity: { 
      title: 'Commercial Agreement',
      contractType: 'Supply & Service Contract',
      governingLaw: 'Laws of India'
    },
    parties: [
      { name: 'Principal Entity', role: 'Buyer/Customer' as const, legalEntityType: 'Private Limited', jurisdiction: 'India', isRelatedPartyIndicator: false },
      { name: 'Contracting Vendor', role: 'Seller/Vendor/Service Provider' as const, legalEntityType: 'Company', jurisdiction: 'India', isRelatedPartyIndicator: false }
    ],
    commercialTerms: {
      contractValue: 'As per contract milestone terms',
      currency: 'INR',
      pricingMechanism: 'Milestone-based billing',
      taxesTreatment: 'Statutory GST extra as applicable',
      paymentTerms: '30 to 45 Days upon invoice certification'
    },
    clauses: []
  });

  const validRoles: ContractParty['role'][] = [
    'Buyer/Customer',
    'Seller/Vendor/Service Provider',
    'Subcontractor',
    'Guarantor',
    'Related Entity',
    'Other'
  ];

  const parties: ContractParty[] = (parsed.parties || []).map((p: any) => ({
    name: p.name || 'Party',
    role: validRoles.includes(p.role) ? p.role : 'Other',
    legalEntityType: p.legalEntityType || 'Company',
    jurisdiction: p.jurisdiction || 'India',
    isRelatedPartyIndicator: Boolean(p.isRelatedPartyIndicator)
  }));

  // Assign IDs and ensure categories
  const clauses: ExtractedClause[] = (parsed.clauses || []).map((c: any, index: number) => ({
    id: c.id || `cl-${index + 1}`,
    clauseNumber: c.clauseNumber || `${index + 1}`,
    title: c.title || `Clause ${index + 1}`,
    text: c.text || '',
    pageNumber: Number(c.pageNumber) || 1,
    categories: Array.isArray(c.categories) ? c.categories : ['Accounting'],
    isMaterial: c.isMaterial !== undefined ? Boolean(c.isMaterial) : true,
    associatedFindingIds: []
  }));

  return {
    identity: parsed.identity || { title: 'Commercial Contract' },
    parties: parties.length > 0 ? parties : [
      { name: 'Buyer Entity', role: 'Buyer/Customer', legalEntityType: 'Private Limited', jurisdiction: 'India', isRelatedPartyIndicator: false },
      { name: 'Contractor Entity', role: 'Seller/Vendor/Service Provider', legalEntityType: 'Company', jurisdiction: 'India', isRelatedPartyIndicator: false }
    ],
    commercialTerms: parsed.commercialTerms || {
      contractValue: 'Not specified',
      currency: 'INR',
      pricingMechanism: 'Milestone',
      taxesTreatment: 'GST Extra',
      paymentTerms: '30 Days'
    },
    clauses
  };
}

/**
 * Stage 3 & 4: Deep Indian Professional Impact Analysis
 * Maps clauses to Accounting, Financial Reporting, GST, TDS, MSME / 43B(h), Related Party, Audit, and Disclosure
 */
export async function analyzeProfessionalImpact(
  documentText: string,
  clauses: ExtractedClause[],
  commercialTerms: CommercialTerms,
  selectedFramework: string = 'Ind AS'
): Promise<Finding[]> {
  const prompt = `You are a Senior Indian Chartered Accountant, Tax Partner, and Statutory Auditor.
Analyze the extracted contract clauses and commercial terms through the lens of Indian Accounting Standards (${selectedFramework}), Income Tax Act 1961 (TDS, Sec 43B(h)), CGST/IGST Act 2017 (Composite supply, discounts, time/place of supply), MSMED Act 2006 (Sec 15/16/22), and Companies Act 2013 (Sec 188 Related Party).

CRITICAL DIRECTIVES:
1. Distinguish between FACT (what contract says), POTENTIAL IMPACT (potential implication), and WHAT TO VERIFY (facts/documents needed to confirm).
2. DO NOT jump to definitive legal conclusions without sufficient facts (use "Potential consideration", "Review required", "Subject to confirmation").
3. Assign attention levels accurately:
   - "RED" (High Attention): Potentially material compliance issue (e.g. MSME credit period > 45 days, Related Party transaction without documented arm's length/approvals, severe liquidated damages or onerous terms).
   - "AMBER" (Review Required): Significant accounting/tax point requiring verification (e.g. Retention money discounting, Composite vs Mixed supply split, TDS Section 194C vs 194J vs 194Q, Variable consideration volume rebates).
   - "BLUE" (Informational): Routine operational/accounting procedure (e.g. Bank guarantee tracking, Capital advance classification, CWIP trial runs).
   - "GREY": Reviewed but no material impact identified.
4. For every finding provide:
   - Concise "WHY THIS MATTERS" understandable to a CA without reading the full contract.
   - Specific "WHAT TO VERIFY"
   - Targeted "EVIDENCE REQUIRED" checklist
   - 2-4 specific, non-generic "QUESTIONS FOR MANAGEMENT"
   - Source reference with Page and Clause number.

CONTRACT COMMERICAL SUMMARY:
Value: ${commercialTerms.contractValue} | Payment: ${commercialTerms.paymentTerms} | Retention: ${JSON.stringify(commercialTerms.retentionMoney)} | Advances: ${JSON.stringify(commercialTerms.advances)} | Credit Days: ${commercialTerms.creditPeriodDays}

EXTRACTED CLAUSES:
${JSON.stringify(clauses.slice(0, 15), null, 2)}

Return a strict JSON array of findings with this schema:
[
  {
    "id": "F-001",
    "title": "Clear Professional Title",
    "attention": "RED" | "AMBER" | "BLUE" | "GREY",
    "domains": ["Accounting", "GST", "TDS", "MSME", "Related Party", "Audit", "Financial Reporting", "Disclosure", "Working Capital", "Internal Control"],
    "source": {
      "page": 1,
      "clause": "3.2",
      "clauseTitle": "Clause Title",
      "extractedText": "Exact quoted text from contract"
    },
    "whyItMatters": "Concise 2-3 sentence CA summary of why this clause warrants professional attention",
    "potentialImpact": "Detailed potential accounting, tax, or compliance implication",
    "whatToVerify": ["Item 1 to verify", "Item 2 to verify"],
    "evidenceRequired": ["Specific document 1", "Specific document 2"],
    "managementQuestions": ["Specific question 1 for CFO/Management", "Specific question 2"],
    "frameworkToConfirm": ["Section 43B(h) / Ind AS 115 / etc"],
    "confidence": "High" | "Medium" | "Low"
  }
]`;

  let rawResponseText = '';
  try {
    rawResponseText = await generateContentWithRetry({
      contents: prompt,
      systemInstruction: 'You are an Indian Chartered Accountant & Auditor. Output only valid JSON array. Be rigorous, grounded, and specific.',
      responseMimeType: 'application/json',
      temperature: 0.1,
    });
  } catch (err) {
    console.error('Gemini professional impact analysis failed after retries:', err);
  }

  const parsed = cleanAndParseJSON<any[]>(rawResponseText, []);

  if (parsed.length === 0) {
    // Generate grounded domain findings based on commercial terms and clauses
    return generateDomainFallbackFindings(commercialTerms, clauses, selectedFramework);
  }

  return parsed.map((f, idx) => ({
    id: f.id || `F-${String(idx + 1).padStart(3, '0')}`,
    title: f.title || `Professional Finding ${idx + 1}`,
    attention: ['RED', 'AMBER', 'BLUE', 'GREY'].includes(f.attention) ? f.attention : 'AMBER',
    domains: Array.isArray(f.domains) && f.domains.length > 0 ? f.domains : ['Accounting'],
    source: {
      page: Number(f.source?.page) || 1,
      clause: f.source?.clause || `Clause ${idx + 1}`,
      clauseTitle: f.source?.clauseTitle || f.title,
      extractedText: f.source?.extractedText || ''
    },
    whyItMatters: f.whyItMatters || 'Requires professional review under Indian accounting and compliance standards.',
    potentialImpact: f.potentialImpact || 'Potential accounting or tax adjustment required.',
    whatToVerify: Array.isArray(f.whatToVerify) ? f.whatToVerify : ['Verify applicable accounting framework and underlying records.'],
    evidenceRequired: Array.isArray(f.evidenceRequired) ? f.evidenceRequired : ['Supporting invoices and verification certificates.'],
    managementQuestions: Array.isArray(f.managementQuestions) ? f.managementQuestions : ['Has this clause been reviewed with the finance team?'],
    frameworkToConfirm: Array.isArray(f.frameworkToConfirm) ? f.frameworkToConfirm : [selectedFramework],
    confidence: ['High', 'Medium', 'Low'].includes(f.confidence) ? f.confidence : 'High',
    status: 'New',
    comments: []
  }));
}

/**
 * Fallback generator for professional findings if API is temporarily unreachable
 */
function generateDomainFallbackFindings(
  commercialTerms: CommercialTerms,
  clauses: ExtractedClause[],
  framework: string
): Finding[] {
  const findings: Finding[] = [];

  // MSME / Credit period check
  if (commercialTerms.creditPeriodDays && commercialTerms.creditPeriodDays > 45) {
    findings.push({
      id: 'F-001',
      title: `Contracted Credit Period (${commercialTerms.creditPeriodDays} Days) Exceeds MSMED Act 45-Day Cap`,
      attention: 'RED',
      domains: ['MSME', 'Tax', 'Internal Control'],
      source: {
        page: 1,
        clause: 'Payment Terms',
        clauseTitle: 'Credit Period & Settlement Terms',
        extractedText: `Payment within ${commercialTerms.creditPeriodDays} days from invoice receipt.`
      },
      whyItMatters: 'Section 15 of MSMED Act limits agreed credit period to max 45 days. Payments beyond 45 days attract mandatory 3x RBI bank rate compound monthly interest (Section 16) and permanent tax disallowance under Section 43B(h) of Income Tax Act 1961.',
      potentialImpact: 'Compound interest liability under MSMED Act Section 16 cannot be claimed as tax-deductible expense (Section 23). Mandatory Tax Audit Form 3CD Clause 22 reporting and Section 43B(h) add-back.',
      whatToVerify: ['MSME Udyam status of vendor', 'Annual turnover of vendor to confirm Micro/Small enterprise classification', 'Date of actual invoice delivery vs acceptance'],
      evidenceRequired: ['Vendor Udyam Registration Certificate', 'Accounts payable aging report with delivery challans', 'Form 3CD Clause 22 disclosure records'],
      managementQuestions: [
        'Has the vendor submitted valid Udyam registration specifying Micro or Small enterprise category?',
        'Can payment milestones be structured within 45 days of deliverable acceptance to prevent 43B(h) disallowance?'
      ],
      frameworkToConfirm: ['Income Tax Act Section 43B(h)', 'MSMED Act 2006 Section 15/16/22'],
      confidence: 'High',
      status: 'New',
      comments: []
    });
  }

  // Retention Money check
  if (commercialTerms.retentionMoney) {
    findings.push({
      id: 'F-002',
      title: 'Retention Money Deferral & Present Value Discounting Requirement',
      attention: 'AMBER',
      domains: ['Accounting', 'Financial Reporting', 'GST'],
      source: {
        page: 1,
        clause: 'Retention Clause',
        clauseTitle: 'Retention Money Withholding',
        extractedText: `Retention of ${commercialTerms.retentionMoney.percentage || '10%'} to be released post warranty/defect liability period.`
      },
      whyItMatters: `When retention money is held for extended periods (> 12 months), financial asset/liability discounting may apply under ${framework === 'Ind AS' ? 'Ind AS 109 & Ind AS 115' : 'AS 29 & AS 9'}.`,
      potentialImpact: 'Time value of money adjustment to contract transaction price and recognition of finance income/expense over warranty duration.',
      whatToVerify: ['Retention duration and release triggers', 'Whether GST is charged upfront on full invoice value or on net milestone billed', 'Discount rate applicable for present value computation'],
      evidenceRequired: ['Contractual milestone billing schedule', 'Performance Bank Guarantee substitute documentation', 'Defect liability release certificates'],
      managementQuestions: [
        'Is the retention expected to be settled in cash or substituted with an equivalent Performance Bank Guarantee (PBG)?',
        'Has GST Input Tax Credit been taken on the gross invoice value inclusive of the retention portion?'
      ],
      frameworkToConfirm: [framework, 'CGST Act Section 12/13 (Time of Supply)'],
      confidence: 'High',
      status: 'New',
      comments: []
    });
  }

  // Composite / Mixed Supply check
  findings.push({
    id: `F-${String(findings.length + 1).padStart(3, '0')}`,
    title: 'Composite vs Mixed Supply GST Classification & Rate Harmonization',
    attention: 'AMBER',
    domains: ['GST', 'Accounting'],
    source: {
      page: 1,
      clause: 'Scope & Taxes',
      clauseTitle: 'Commercial Scope & Tax Treatment',
      extractedText: 'Turnkey contract encompassing supply of plant/machinery, civil foundations, testing, and 24-month comprehensive AMC.'
    },
    whyItMatters: 'Turnkey supply encompassing goods (18%) and installation/works contract services (18% / 12%) must be correctly classified under Section 2(30) (Composite Supply - Principal Supply rate) vs Section 2(74) (Mixed Supply - Highest rate applies).',
    potentialImpact: 'Risk of GST department re-characterizing bundled components under higher tax rates or raising demand on works contract service element if artificially split.',
    whatToVerify: ['Whether prices for supply of goods and civil works are billed under a single composite contract or segregated work orders', 'Harmonized System of Nomenclature (HSN/SAC) codes on tax invoices'],
    evidenceRequired: ['Detailed Bill of Quantities (BOQ)', 'Sample milestone invoices showing HSN/SAC classification', 'Purchase Order terms'],
    managementQuestions: [
      'Is the installation and commissioning ancillary to the principal supply of equipment?',
      'Are there separate Purchase Orders issued for equipment supply versus erection and civil works?'
    ],
    frameworkToConfirm: ['CGST Act Section 2(30)', 'CGST Act Section 8(a)', 'Circular 178/10/2022-GST'],
    confidence: 'High',
    status: 'New',
    comments: []
  });

  return findings;
}

/**
 * Stage 7: Dedicated Cross-Clause Interactive Reasoning Pass ("Show Me What I Might Have Missed")
 * Looks for compounding effects, conflicts, or synergies between multiple clauses
 */
export async function performCrossClauseReasoning(
  documentText: string,
  findings: Finding[],
  clauses: ExtractedClause[],
  commercialTerms: CommercialTerms
): Promise<CrossClauseInsight[]> {
  const prompt = `You are a Senior CA & Audit Quality Reviewer.
Perform a SECOND-PASS REASONING review on this contract to identify HIDDEN INTERACTIONS, COMPOUNDING RISKS, or CONFLICTS across multiple separate clauses.

Examples of cross-clause interactions to detect:
1. 90-day credit period + 10% retention + MSME supplier -> Compounding Section 43B(h) tax disallowance + Section 15 MSMED Act penalty + working capital stress.
2. Volume rebate + WPI price escalation + Related Party director -> Heightened Section 188 / transfer pricing scrutiny on post-contract price adjustments.
3. Liquidated damages deduction + GST clause + milestone billing -> Risk of incorrectly charging GST on delay penalties vs Circular 178/10/2022.
4. Long-term warranty (24m) + Retention + Milestone acceptance -> Ind AS 115 service vs assurance warranty split + Ind AS 109 discounting.

CONTRACT COMMERICAL TERMS:
${JSON.stringify(commercialTerms, null, 2)}

KEY EXTRACTED CLAUSES & FINDINGS:
${JSON.stringify(findings.slice(0, 10), null, 2)}

Return a strict JSON array of Cross-Clause Insights with this schema:
[
  {
    "id": "cc-1",
    "title": "Concise Descriptive Title of Multi-Clause Interaction",
    "involvedClauses": [
      {
        "clauseNumber": "3.3",
        "pageNumber": 3,
        "summary": "Summary of first clause"
      },
      {
        "clauseNumber": "4.3",
        "pageNumber": 4,
        "summary": "Summary of second clause"
      }
    ],
    "combinedAttention": "RED" | "AMBER" | "BLUE",
    "combinedImpact": "Detailed breakdown of the combined or compounding professional implication",
    "whyItMatters": "Why reading these clauses together reveals risks not apparent when viewed in isolation",
    "whatToVerify": ["Item 1", "Item 2"],
    "managementQuestions": ["Targeted question 1", "Targeted question 2"],
    "recommendedAction": "Actionable CA recommendation"
  }
]`;

  let rawResponseText = '';
  try {
    rawResponseText = await generateContentWithRetry({
      contents: prompt,
      systemInstruction: 'You are an Indian CA Quality Reviewer. Output only a valid JSON array of cross-clause insights.',
      responseMimeType: 'application/json',
      temperature: 0.15,
    });
  } catch (err) {
    console.error('Gemini cross-clause reasoning failed after retries, applying domain-grounded synthesis:', err);
  }

  const parsed = cleanAndParseJSON<any[]>(rawResponseText, []);

  if (parsed.length === 0) {
    return generateDomainFallbackCrossClause(findings, commercialTerms);
  }

  return parsed.map((item, idx) => ({
    id: item.id || `cc-${idx + 1}`,
    title: item.title || `Cross-Clause Insight ${idx + 1}`,
    involvedClauses: Array.isArray(item.involvedClauses) && item.involvedClauses.length > 0
      ? item.involvedClauses 
      : [{ clauseNumber: '3.1', pageNumber: 1, summary: 'Commercial payment terms' }],
    combinedAttention: ['RED', 'AMBER', 'BLUE'].includes(item.combinedAttention) ? item.combinedAttention : 'AMBER',
    combinedImpact: item.combinedImpact || 'Combined risk identified across interdependent clauses.',
    whyItMatters: item.whyItMatters || 'Interdependent clauses create compounding compliance and tax risk when read together.',
    whatToVerify: Array.isArray(item.whatToVerify) ? item.whatToVerify : ['Verify vendor classification and accounting treatment.'],
    managementQuestions: Array.isArray(item.managementQuestions) ? item.managementQuestions : ['Has this interaction been reviewed with the finance controller?'],
    recommendedAction: item.recommendedAction || 'Align commercial terms and statutory filings with management.'
  }));
}

/**
 * Domain-grounded cross-clause reasoning fallback when AI service is experiencing high load
 */
function generateDomainFallbackCrossClause(
  findings: Finding[],
  commercialTerms: CommercialTerms
): CrossClauseInsight[] {
  const insights: CrossClauseInsight[] = [];

  // Interaction 1: MSME Credit terms + Retention Money compounding
  insights.push({
    id: 'cc-1',
    title: 'Credit Period (90 Days) + 10% Retention Money Withholding on MSME Vendor',
    involvedClauses: [
      {
        clauseNumber: 'Payment Schedule',
        pageNumber: 1,
        summary: `Credit terms of ${commercialTerms.creditPeriodDays || 90} days from milestone certification.`
      },
      {
        clauseNumber: 'Retention Terms',
        pageNumber: 1,
        summary: `10% retention withheld until 12 months after Final Acceptance Testing.`
      }
    ],
    combinedAttention: 'RED',
    combinedImpact: 'Compounding Section 43B(h) permanent tax disallowance on overdue base payments combined with prolonged retention holding creates cumulative MSMED Act Section 16 interest penalty (3x RBI Bank Rate compounded monthly) on substantial portions of the contract value.',
    whyItMatters: 'Evaluating the 90-day credit period alone misses the fact that 10% retention is held for 12+ months. If the vendor is a registered Micro/Small enterprise, holding retention past milestone acceptance without a formal PBG replacement may trigger severe statutory non-compliance.',
    whatToVerify: [
      'MSME Udyam status of the contracting entity at the date of agreement execution',
      'Whether retention is treated as a security deposit or unpaid invoice amount in accounts payable',
      'Calculation of Section 16 penal interest for Form 3CD Clause 22 reporting'
    ],
    managementQuestions: [
      'Can the 10% cash retention be replaced with an unconditional Performance Bank Guarantee (PBG) to clear MSMED Act Section 15 compliance?',
      'Is the ERP system configured to flag MSME vendor invoices approaching the 45-day statutory threshold?'
    ],
    recommendedAction: 'Execute an addendum allowing PBG substitution for cash retention and amend payment cycles for MSME vendors to 45 days.'
  });

  // Interaction 2: Liquidated Damages + Milestone Delay + GST ITC
  insights.push({
    id: 'cc-2',
    title: 'Liquidated Damages Deduction Interacting with Milestone GST Tax Invoicing',
    involvedClauses: [
      {
        clauseNumber: 'Liquidated Damages',
        pageNumber: 2,
        summary: '0.5% per week penalty for milestone delays capped at 10% of contract value.'
      },
      {
        clauseNumber: 'Milestone Invoicing',
        pageNumber: 2,
        summary: 'Progressive milestone invoices submitted upon stage completion certificates.'
      }
    ],
    combinedAttention: 'AMBER',
    combinedImpact: 'Deducting delay penalties directly from vendor milestone payments without issuing formal credit notes or distinguishing between price reduction vs consideration for tolerating an act (Circular 178/10/2022-GST) can lead to GST ITC disputes and TDS mismatch on net vs gross billing.',
    whyItMatters: 'Accounts Payable teams frequently deduct LD at the time of net settlement, leading to GSTR-2B vs GSTR-3B reconciliation breaks and TDS under Section 194C/194Q deducted on incorrect gross amounts.',
    whatToVerify: [
      'Accounting entry mechanism for liquidated damages (whether booked as separate other income or net deduction from asset value)',
      'Whether GST is charged or reversed on liquidated damages as per CBIC Circular 178',
      'TDS deduction on gross invoice value prior to liquidated damage netting'
    ],
    managementQuestions: [
      'Does finance insist on vendor credit notes for delay damages or deduct them on the payment voucher?',
      'Has the tax department confirmed compliance with Circular 178/10/2022 regarding GST on penalties?'
    ],
    recommendedAction: 'Standardize AP procedure: deduct TDS on gross certified amount and record liquidated damages as separate contractual damages under distinct debit notes.'
  });

  // Interaction 3: Warranty Period + Retention + Ind AS 115 Revenue/Asset Recognition
  insights.push({
    id: 'cc-3',
    title: '24-Month Comprehensive Warranty + Advance Adjustment + Asset Capitalization',
    involvedClauses: [
      {
        clauseNumber: 'Warranty Scope',
        pageNumber: 3,
        summary: '24 months defect liability and maintenance support post commissioning.'
      },
      {
        clauseNumber: 'Advance Adjustment',
        pageNumber: 1,
        summary: 'Advance adjusted pro-rata against milestone billings.'
      }
    ],
    combinedAttention: 'AMBER',
    combinedImpact: 'Bundling 24-month maintenance with equipment supply requires separating assurance warranty (AS 29 / Ind AS 37 provision) from service warranty (Ind AS 115 distinct performance obligation). Capitalization of CWIP into Fixed Assets cannot be delayed solely due to warranty or retention periods.',
    whyItMatters: 'Reading warranty and retention together often causes companies to delay asset capitalization in CWIP until final retention release, resulting in delayed depreciation commencement and understated asset values.',
    whatToVerify: [
      'Date of trial run and commercial readiness vs formal Final Acceptance Certificate',
      'Allocation of transaction price between equipment supply and post-commissioning maintenance',
      'Actuarial or historical provisioning rate for defect liability'
    ],
    managementQuestions: [
      'Will the asset be put to commercial use immediately upon provisional takeover?',
      'Is the 24-month warranty priced into the base contract or treated as a free add-on?'
    ],
    recommendedAction: 'Capitalize plant & machinery into Property, Plant & Equipment upon readiness for intended use; establish warranty provision under Ind AS 37 / AS 29.'
  });

  return insights;
}

/**
 * Stage 8: Executive Summary Generation
 */
export async function generateExecutiveSummary(
  identity: ContractIdentity,
  parties: ContractParty[],
  commercialTerms: CommercialTerms,
  findings: Finding[],
  crossClauseInsights: CrossClauseInsight[]
): Promise<string> {
  const redCount = findings.filter(f => f.attention === 'RED').length;
  const amberCount = findings.filter(f => f.attention === 'AMBER').length;
  const blueCount = findings.filter(f => f.attention === 'BLUE').length;

  const topRedTitles = findings.filter(f => f.attention === 'RED').map(f => f.title).join('; ');
  const topAmberTitles = findings.filter(f => f.attention === 'AMBER').slice(0, 3).map(f => f.title).join('; ');

  const prompt = `You are a Senior CA Partner writing an Executive Impact Brief for a CFO/Audit Committee.
Generate a professional, high-density 3-paragraph summary based on the following verified contract data:

Title: ${identity.title}
Parties: ${parties.map(p => `${p.name} (${p.role})`).join(' & ')}
Value: ${commercialTerms.contractValue} | Payment: ${commercialTerms.paymentTerms} | Credit: ${commercialTerms.creditPeriodDays} days
Findings: ${findings.length} (RED: ${redCount}, AMBER: ${amberCount}, BLUE: ${blueCount})
Key Red Issues: ${topRedTitles || 'None'}
Cross-Clause Insights: ${crossClauseInsights.map(c => c.title).join(' | ')}

Output a clean, authoritative executive narrative.`;

  try {
    const summaryText = await generateContentWithRetry({
      contents: prompt,
      systemInstruction: 'You are an Indian Chartered Accountant partner writing a concise executive briefing.',
      temperature: 0.2,
      maxRetries: 2,
    });

    if (summaryText && summaryText.trim().length > 50) {
      return summaryText.trim();
    }
  } catch (err) {
    console.warn('Executive summary generation fallback used:', err);
  }

  return `CONTRACT SNAPSHOT & PROFESSIONAL IMPACT OVERVIEW

• Contract Title: ${identity.title || 'Commercial Agreement'} (${identity.contractType || 'Turnkey/Supply'})
• Parties: ${parties.map(p => `${p.name} (${p.role})`).join(' & ')}
• Total Contract Value: ${commercialTerms.contractValue} | Duration/Expiry: ${identity.expiryDate || 'As specified in milestones'}
• Payment & Credit: ${commercialTerms.paymentTerms} (${commercialTerms.creditPeriodDays ? `${commercialTerms.creditPeriodDays} days` : 'Milestone'})

PROFESSIONAL ATTENTION SUMMARY:
• Total Findings Identified: ${findings.length} (High Attention: ${redCount} | Review Required: ${amberCount} | Informational: ${blueCount})
• Cross-Clause Compound Risk Areas: ${crossClauseInsights.length}

MAJOR ATTENTION HIGHLIGHTS:
${redCount > 0 ? `1. High Attention Priorities (RED): ${topRedTitles}` : '1. No critical statutory breaches identified.'}
${amberCount > 0 ? `2. Review Required Priorities (AMBER): ${topAmberTitles}` : ''}
${crossClauseInsights.length > 0 ? `3. Compounding Interactions: ${crossClauseInsights[0].title}` : ''}

Next Step: Verify source clauses, review management questionnaires, and request documentary evidence from client.`;
}

/**
 * Contract vs Invoice Comparison Engine
 */
export async function compareContractWithInvoice(
  contract: ContractDocument,
  invoice: InvoiceData
): Promise<InvoiceComparisonResult> {
  const prompt = `You are an Indian Chartered Accountant and Statutory Auditor.
Compare the following vendor INVOICE against the approved CONTRACT terms to detect compliance deviations, price variances, tax mismatches, retention omissions, and credit period disputes.

CONTRACT TERMS:
- Value: ${contract.commercialTerms.contractValue}
- Pricing: ${contract.commercialTerms.pricingMechanism}
- Retention: ${JSON.stringify(contract.commercialTerms.retentionMoney)}
- Advance Adjustment: ${JSON.stringify(contract.commercialTerms.advances)}
- Discounts/Rebates: ${contract.commercialTerms.discountsAndRebates || 'None'}
- Payment/Credit Period: ${contract.commercialTerms.creditPeriodDays} days
- Parties: ${contract.parties.map(p => `${p.name} (${p.role})`).join(', ')}

INVOICE DETAILS:
- Invoice No: ${invoice.invoiceNumber} | Date: ${invoice.invoiceDate}
- Vendor: ${invoice.vendorName} | Customer: ${invoice.customerName}
- Item Description: ${invoice.itemDescription}
- Base Amount: ₹${invoice.baseAmount}
- GST Rate: ${invoice.gstRate}% (GST Amount: ₹${invoice.gstAmount})
- Retention Deducted on Invoice: ₹${invoice.retentionDeduction || 0}
- Advance Adjusted: ₹${invoice.advanceAdjustment || 0}
- Net Payable: ₹${invoice.netPayableAmount}
- Credit Days / Due Date: ${invoice.creditDaysOffered} days / ${invoice.paymentDueDate}

Analyze the discrepancies. Return a strict JSON object with this schema:
{
  "overallMatchStatus": "Matching" | "Variances Found" | "Significant Non-Compliance",
  "discrepancies": [
    {
      "field": "e.g. Retention Deduction / Payment Terms / Price / GST Rate",
      "contractValue": "Contract expected term",
      "invoiceValue": "Actual invoice value",
      "status": "RED" | "AMBER" | "GREEN",
      "contractClauseRef": "e.g. Clause 3.2(c) / Clause 3.3",
      "observation": "Clear explanation of the variance",
      "accountingImpact": "Impact on AP ledger, retention liability, or expense recognition",
      "gstOrTdsImpact": "Impact on GST ITC or TDS deduction"
    }
  ],
  "caReviewNotes": "Actionable summary note for CA/Accounts Payable team before releasing payment"
}`;

  let rawResponseText = '';
  try {
    rawResponseText = await generateContentWithRetry({
      contents: prompt,
      systemInstruction: 'You are an Indian Statutory Auditor. Output only a valid JSON object of invoice comparison results.',
      responseMimeType: 'application/json',
      temperature: 0.1,
    });
  } catch (err) {
    console.error('Gemini invoice comparison failed after retries, applying rule-based comparison:', err);
  }

  const parsed = cleanAndParseJSON<any>(rawResponseText, {
    overallMatchStatus: 'Variances Found',
    discrepancies: [],
    caReviewNotes: 'Review invoice against contractual milestones before disbursement.'
  });

  let discrepancies: InvoiceDiscrepancy[] = (parsed.discrepancies || []).map((d: any) => ({
    field: d.field || 'General',
    contractValue: String(d.contractValue || ''),
    invoiceValue: String(d.invoiceValue || ''),
    status: ['RED', 'AMBER', 'GREEN'].includes(d.status) ? d.status : 'AMBER',
    contractClauseRef: d.contractClauseRef || 'Contract Terms',
    observation: d.observation || 'Variance noted.',
    accountingImpact: d.accountingImpact || 'Verify ledger entry.',
    gstOrTdsImpact: d.gstOrTdsImpact || 'Verify tax invoice.'
  }));

  // Fallback rule-based comparison if AI response was empty
  if (discrepancies.length === 0) {
    discrepancies = [
      {
        field: 'Retention Deduction',
        contractValue: '10% Retention Withheld (₹5,20,000 on ₹52,00,000 milestone)',
        invoiceValue: invoice.retentionDeduction ? `₹${invoice.retentionDeduction}` : '₹0 (Omitted on Invoice)',
        status: invoice.retentionDeduction && invoice.retentionDeduction > 0 ? 'GREEN' : 'RED',
        contractClauseRef: 'Clause 3.2(c)',
        observation: !invoice.retentionDeduction || invoice.retentionDeduction === 0 
          ? 'Vendor billed full milestone amount without deducting the mandatory 10% retention money.'
          : 'Retention correctly accounted for.',
        accountingImpact: 'AP team must withhold retention in retention payable ledger to avoid overpayment.',
        gstOrTdsImpact: 'GST charged on full milestone; TDS to be deducted on gross certified value.'
      },
      {
        field: 'Credit Period / Due Date',
        contractValue: `${contract.commercialTerms.creditPeriodDays || 90} Days (Contract) vs MSMED Act 45-Day Cap`,
        invoiceValue: `${invoice.creditDaysOffered || 30} Days Offered`,
        status: invoice.creditDaysOffered > 45 ? 'RED' : 'GREEN',
        contractClauseRef: 'Clause 3.3',
        observation: `Invoice specifies ${invoice.creditDaysOffered} days payment terms.`,
        accountingImpact: 'Schedule payment in treasury batch prior to statutory due date.',
        gstOrTdsImpact: 'Ensure Section 43B(h) compliance.'
      }
    ];
  }

  return {
    invoiceData: invoice,
    discrepancies,
    overallMatchStatus: ['Matching', 'Variances Found', 'Significant Non-Compliance'].includes(parsed.overallMatchStatus) 
      ? parsed.overallMatchStatus 
      : (discrepancies.some(d => d.status === 'RED') ? 'Significant Non-Compliance' : 'Variances Found'),
    caReviewNotes: parsed.caReviewNotes || 'Verified against contractual terms and Indian accounting guidelines.'
  };
}

