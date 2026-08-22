import { GoogleGenAI } from '@google/genai';
import { RegulatoryUpdate, SourceVerificationStatus } from '../src/types';

// Initialize Gemini Client
const apiKey = process.env.GEMINI_API_KEY;

function getAiClient() {
  if (!apiKey) {
    console.warn('GEMINI_API_KEY environment variable is missing.');
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

/**
 * Uses Gemini to parse a raw text Daily Professional Briefing email into separate structured regulatory updates.
 */
export async function extractBriefingWithGemini(rawText: string, briefingDate: string): Promise<RegulatoryUpdate[]> {
  const ai = getAiClient();
  if (!ai) {
    throw new Error('Gemini API key not configured. Using Demo Mode fallback.');
  }

  const prompt = `You are a Senior Chartered Accountant & Regulatory Analyst in India.
Analyze the following Daily Professional Briefing email received on ${briefingDate}.
Extract every distinct regulatory, tax, legal, banking, forex, corporate, labour, or market development into a structured array of updates.

CRITICAL ANTI-HALLUCINATION INSTRUCTIONS:
- NEVER invent circular numbers, notification numbers, section numbers, tax rates, or statutory deadlines if not mentioned in the text.
- If circular or section numbers are missing from the text, write "Verification Required — Not specified in source email".

BRIEFING TEXT:
${rawText}

For each item, extract and classify accurately into JSON with these exact fields:
- title
- category (GST | Income Tax | TDS / TCS | MCA / Companies Act | RBI / Banking | FEMA / Foreign Exchange | SEBI / Capital Markets | Labour Law | PF | ESI | Accounting | Audit | Corporate Finance | Economic Development | Forex | Gold | Crude Oil | Commodities | Equity Market | Industry Development | Other)
- subCategory
- nature (New Requirement | Amendment | Rate Change | Deadline | Deadline Extension | Clarification | Procedural Change | Exemption | Reporting Requirement | Judicial Development | Draft Proposal | Market Development | Economic Development | Risk Alert | Opportunity)
- issuingAuthority
- source
- referenceNo
- sourceFacts (What the authoritative source actually states)
- aiImpactAnalysisText (AI interpretation of business, financial, compliance consequences)
- caRecommendedAction (Suggested CA professional actions requiring human review)
- dates: {
    notificationDate: string,
    effectiveDate: string,
    statutoryDeadline: string,
    recommendedInternalActionDate: string,
    reviewDate: string
  }
- keyDevelopment
- importantAmounts
- importantPercentages
- importantThresholds
- industryRelevance
- entityRelevance
- verificationStatus ("Verified from Authoritative Source" | "Source Identified — Verification Pending" | "Secondary Source Only" | "Unable to Verify")
- confidenceScore (0-100)
- riskLevel (Critical | High | Medium | Low | Informational)
- actionPriority (Immediate | Within 3 Days | Within 7 Days | Before Statutory Deadline | Monitor | Information Only)
- isMarketItem (boolean)
- impactAnalysis: {
    whatChanged: string,
    whoIsAffected: string,
    applicabilityConditions: object,
    complianceImpact: string,
    financialImpact: string,
    operationalImpact: string,
    recommendedAction: string,
    deadline: string,
    professionalReviewNote: string
  }

Return ONLY valid JSON array.`;

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3.6-flash',
      contents: prompt,
      config: {
        responseMimeType: 'application/json',
      },
    });

    const text = response.text || '[]';
    const parsed = JSON.parse(text);
    const items = Array.isArray(parsed) ? parsed : [parsed];

    return items.map((item: any, idx: number) => ({
      id: `upd_gemini_${Date.now()}_${idx}`,
      briefingDate: briefingDate || 'Current Date',
      title: item.title || 'Regulatory Update',
      category: item.category || 'Other',
      subCategory: item.subCategory || 'General',
      nature: item.nature || 'Amendment',
      issuingAuthority: item.issuingAuthority || 'Verification Required — Official Source Unconfirmed',
      source: item.source || 'Daily Professional Briefing Email',
      referenceNo: item.referenceNo || 'Verification Required',
      dates: {
        notificationDate: item.dates?.notificationDate || item.publicationDate || briefingDate,
        effectiveDate: item.dates?.effectiveDate || item.effectiveDate || 'Verification Required',
        statutoryDeadline: item.dates?.statutoryDeadline || item.deadline || 'Statutory Deadline Verification Required',
        recommendedInternalActionDate: item.dates?.recommendedInternalActionDate || '14 days prior to statutory date',
        reviewDate: item.dates?.reviewDate || briefingDate,
      },
      originalSummary: rawText.slice(0, 300),
      sourceFacts: item.sourceFacts || item.keyDevelopment || 'Official source facts extracted from briefing text.',
      aiImpactAnalysisText: item.aiImpactAnalysisText || 'AI interpretation of potential business and financial impact.',
      caRecommendedAction: item.caRecommendedAction || 'CA review required to confirm specific client applicability.',
      keyDevelopment: item.keyDevelopment || '',
      importantAmounts: item.importantAmounts || 'None specified',
      importantPercentages: item.importantPercentages || 'None specified',
      importantThresholds: item.importantThresholds || 'None specified',
      industryRelevance: item.industryRelevance || 'General Business',
      entityRelevance: item.entityRelevance || 'All taxpayers',
      verificationStatus: (item.verificationStatus || 'Source Identified — Verification Pending') as SourceVerificationStatus,
      provenance: {
        sourceType: 'Gmail',
        emailSubject: `Daily Professional Briefing – ${briefingDate}`,
        emailReceivedDateTime: new Date().toISOString(),
        importedDateTime: new Date().toISOString(),
        extractedCount: items.length,
        authoritativeSourceCheck: 'Pending Independent Gazette Verification',
      },
      unconfirmedNotice: item.referenceNo?.includes('Verification')
        ? 'Notice: Circular and reference numbers could not be independently verified from briefing text.'
        : undefined,
      confidenceScore: typeof item.confidenceScore === 'number' ? item.confidenceScore : 88,
      confidenceRating: item.confidenceScore >= 90 ? 'High (90-100%)' : item.confidenceScore >= 75 ? 'Moderate (75-89%)' : 'Limited (50-74%)',
      riskLevel: item.riskLevel || 'Medium',
      actionPriority: item.actionPriority || 'Within 7 Days',
      isMarketItem: Boolean(item.isMarketItem),
      sourceType: 'Gmail',
      createdAt: new Date().toISOString(),
      impactAnalysis: {
        whatChanged: item.impactAnalysis?.whatChanged || item.keyDevelopment || '',
        whoIsAffected: item.impactAnalysis?.whoIsAffected || item.entityRelevance || '',
        applicabilityConditions: item.impactAnalysis?.applicabilityConditions || {},
        complianceImpact: item.impactAnalysis?.complianceImpact || 'Filing & reporting required.',
        financialImpact: item.impactAnalysis?.financialImpact || 'Potential tax / compliance costs.',
        operationalImpact: item.impactAnalysis?.operationalImpact || 'ERP & billing software alignment.',
        recommendedAction: item.impactAnalysis?.recommendedAction || 'Review official circular and verify applicability.',
        deadline: item.dates?.statutoryDeadline || item.deadline || 'Statutory Deadline Verification Required',
        professionalReviewNote: item.impactAnalysis?.professionalReviewNote || 'CA review required prior to client communication.',
      },
    }));
  } catch (error) {
    console.error('Error in extractBriefingWithGemini:', error);
    throw error;
  }
}

/**
 * Analyzes a standalone user-submitted update using Gemini.
 */
export async function analyzeSpecificUpdateWithGemini(data: {
  title: string;
  source: string;
  date: string;
  referenceNo?: string;
  url?: string;
  fullText: string;
}): Promise<RegulatoryUpdate> {
  const ai = getAiClient();
  if (!ai) {
    throw new Error('Gemini API key unavailable.');
  }

  const prompt = `You are an expert Chartered Accountant and Tax Advocate in India.
Analyze this user-submitted regulatory update:

TITLE: ${data.title}
SOURCE: ${data.source}
DATE: ${data.date}
REFERENCE: ${data.referenceNo || 'N/A'}
URL: ${data.url || 'N/A'}
TEXT:
${data.fullText}

Return JSON with fields:
category, subCategory, nature, issuingAuthority, referenceNo, sourceFacts, aiImpactAnalysisText, caRecommendedAction, dates: { notificationDate, effectiveDate, statutoryDeadline, recommendedInternalActionDate, reviewDate }, keyDevelopment, importantAmounts, importantPercentages, importantThresholds, industryRelevance, entityRelevance, verificationStatus, confidenceScore, riskLevel, actionPriority, isMarketItem, impactAnalysis.`;

  const response = await ai.models.generateContent({
    model: 'gemini-3.6-flash',
    contents: prompt,
    config: { responseMimeType: 'application/json' },
  });

  const parsed = JSON.parse(response.text || '{}');

  return {
    id: `upd_manual_${Date.now()}`,
    briefingDate: data.date || new Date().toISOString().split('T')[0],
    title: data.title,
    category: parsed.category || 'Other',
    subCategory: parsed.subCategory || 'General',
    nature: parsed.nature || 'Amendment',
    issuingAuthority: parsed.issuingAuthority || data.source || 'User Manual Source',
    source: data.source,
    referenceNo: data.referenceNo || parsed.referenceNo || 'Verification Required',
    dates: {
      notificationDate: parsed.dates?.notificationDate || data.date,
      effectiveDate: parsed.dates?.effectiveDate || 'Verification Required',
      statutoryDeadline: parsed.dates?.statutoryDeadline || 'Verification Required',
      recommendedInternalActionDate: parsed.dates?.recommendedInternalActionDate || 'Prior to statutory deadline',
      reviewDate: parsed.dates?.reviewDate || data.date,
    },
    originalSummary: data.fullText,
    sourceFacts: parsed.sourceFacts || data.fullText.slice(0, 300),
    aiImpactAnalysisText: parsed.aiImpactAnalysisText || 'AI interpretation of business, financial, compliance consequences.',
    caRecommendedAction: parsed.caRecommendedAction || 'Chartered Accountant review required.',
    keyDevelopment: parsed.keyDevelopment || data.fullText.slice(0, 200),
    importantAmounts: parsed.importantAmounts || 'None specified',
    importantPercentages: parsed.importantPercentages || 'None specified',
    importantThresholds: parsed.importantThresholds || 'None specified',
    industryRelevance: parsed.industryRelevance || 'General',
    entityRelevance: parsed.entityRelevance || 'All taxpayers',
    sourceUrl: data.url,
    verificationStatus: 'Source Identified — Verification Pending',
    provenance: {
      sourceType: 'Manual Entry',
      emailSubject: 'Manual Entry Submission',
      importedDateTime: new Date().toISOString(),
      authoritativeSourceCheck: 'User Provided Document',
    },
    confidenceScore: parsed.confidenceScore || 90,
    confidenceRating: 'High (90-100%)',
    riskLevel: parsed.riskLevel || 'High',
    actionPriority: parsed.actionPriority || 'Within 7 Days',
    isMarketItem: Boolean(parsed.isMarketItem),
    sourceType: 'Manual',
    createdAt: new Date().toISOString(),
    impactAnalysis: parsed.impactAnalysis || {
      whatChanged: parsed.keyDevelopment || data.title,
      whoIsAffected: parsed.entityRelevance || 'Affected entities',
      applicabilityConditions: {},
      complianceImpact: 'Filing & reporting requirements.',
      financialImpact: 'Potential penalty or tax implications.',
      operationalImpact: 'Software & process alignment.',
      recommendedAction: 'Verify applicability with CA team.',
      deadline: parsed.dates?.statutoryDeadline || 'Verification Required',
      professionalReviewNote: 'CA verification mandatory before client communication.',
    },
  };
}
