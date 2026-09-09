import { NoticeCase, NoticeIssue, ReconciliationItem, NoticeFormType } from '../types';
import { supabase } from '../lib/supabase';

export interface AnalysisResponse {
  noticeCase: Omit<NoticeCase, 'id' | 'clientId' | 'createdAt' | 'updatedAt'>;
  issues: Omit<NoticeIssue, 'id' | 'caseId'>[];
  reconciliations: Omit<ReconciliationItem, 'id' | 'caseId'>[];
  /** Taxpayer identified in the notice — used to match / create the client automatically. */
  taxpayer: { gstin: string; legalName: string };
}

async function readInvokeError(error: unknown): Promise<string> {
  try {
    const ctx = (error as { context?: { json?: () => Promise<{ error?: string }> } })?.context;
    const body = ctx?.json ? await ctx.json() : null;
    if (body?.error) return body.error;
  } catch { /* fall through */ }
  return (error as Error)?.message || 'The extraction service could not be reached.';
}

/**
 * Automatic extraction. Runs server-side in the `extract-notice` Supabase Edge
 * Function so the Anthropic key never reaches the browser. If that function is
 * not configured, this throws and the caller falls back to the manual
 * "paste from Claude.ai" flow.
 *
 * `forceLocal` uses the built-in regex parser instead — an offline last resort.
 */
export async function analyzeNotice(
  text: string,
  formTypeHint?: string,
  pdfDataUrl?: string,
  forceLocal = false,
): Promise<AnalysisResponse> {
  if (forceLocal) return parseNoticeLocally(text, formTypeHint);

  const { data, error } = await supabase.functions.invoke('extract-notice', {
    body: { noticeText: text, pdfDataUrl },
  });
  if (error) throw new Error(await readInvokeError(error));
  if (data?.error) throw new Error(data.error);
  if (data?.parsed) return buildAnalysisResponse(data.parsed, text);
  throw new Error('The extraction service returned no result.');
}

// ─────────────────────────────────────────────────────────────
// Extraction prompt — used for the Claude API call and for the
// "run it in Claude.ai yourself" manual copy-paste workflow.
// ─────────────────────────────────────────────────────────────
export const EXTRACTION_PROMPT = `You are a Senior Indian Chartered Accountant specializing in GST litigation.

A GST Notice document has been provided. READ IT COMPLETELY AND CAREFULLY — every page, every table, every paragraph.

TASK: Extract ALL of the following information EXACTLY as it appears in the document. 
DO NOT guess, hallucinate, or fill in generic values. If something is not in the document, use "" or 0.

EXTRACT:
1. Notice/Reference Number (exact string as printed, e.g. "ZA2709240123456" or "ASMT-10/DL/2023/889")
2. Form Type — one of: DRC-01, DRC-01A, DRC-07, ASMT-10, REG-17, ADT-01, RFD-08, MOV-06, SCN
3. Taxpayer GSTIN (15-character alphanumeric)
4. Taxpayer Legal Name
5. Financial Year (format: YYYY-YY, e.g. "2022-23")  
6. Period covered (e.g. "April 2022 to March 2023" or "Q3 & Q4 of FY 2021-22")
7. Notice Date (exact date as printed)
8. Reply/Response Deadline date (look for "reply by", "submit reply within", "due date")
9. Personal Hearing date and time (if mentioned)
10. Issuing Officer — name and designation (look at bottom of notice, signature block)
11. DIN (Document Identification Number — usually a long alphanumeric near the top or bottom)
12. Sections and Rules cited in the notice (e.g. "Section 73(1), Section 16(2)(aa), Rule 36(4)")

FINANCIAL AMOUNTS (read the demand table/summary table carefully):
- Principal Tax demanded (IGST + CGST + SGST combined, excluding interest and penalty)
- Interest amount (Section 50)
- Penalty amount 
- Total Demand

FOR EACH ISSUE/DISCREPANCY listed in the notice (read all paragraphs carefully):
- Issue number
- Short title/heading
- The exact allegation text (what the department says is wrong)
- Sections and Rules the department relies on
- Page/paragraph reference
- Tax amount for this specific issue
- Interest for this issue
- Penalty for this issue
- Total for this issue
- Why this discrepancy likely arose (probable reason from CA perspective)
- Where the department got their figures from (which GST portal return/table)
- What documents/data are needed to respond
- What reconciliation is required
- Specific questions to ask the client
- Required documents list
- Defense points available
- Legal position with relevant case laws/circulars [Verify before use]
- Risk level: HIGH / MEDIUM / LOW

FORMATTING RULES for the lists (these feed the app's Document Tracker and Client Discussion tabs):
- "clientQuestions": a newline-separated numbered list, one clear question per line.
- "documentsRequired": a newline-separated list, ONE document or record per line (no sentences, no "and").
- "dataRequired" and "reconciliationRequired": short phrases.

OUTPUT FORMAT: Return ONLY a valid JSON object — no explanation, no markdown, no code blocks. Just pure JSON:
{
  "noticeNumber": "",
  "formType": "DRC-01",
  "gstin": "",
  "taxpayerName": "",
  "financialYear": "",
  "period": "",
  "noticeDate": "",
  "replyDeadline": "",
  "hearingDate": "",
  "issuingAuthority": "",
  "sectionsMentioned": "",
  "din": "",
  "principalTax": 0,
  "interest": 0,
  "penalty": 0,
  "totalDemand": 0,
  "issues": [
    {
      "issueNumber": 1,
      "title": "",
      "allegation": "",
      "sectionRule": "",
      "pageRef": "",
      "taxAmount": 0,
      "interestAmount": 0,
      "penaltyAmount": 0,
      "totalAmount": 0,
      "probableReason": "",
      "figureSource": "",
      "dataRequired": "",
      "reconciliationRequired": "",
      "clientQuestions": "",
      "documentsRequired": "",
      "defensePoints": "",
      "legalPosition": " [Verify before use]",
      "riskLevel": "HIGH",
      "factsCategory": ""
    }
  ]
}`;

// ─────────────────────────────────────────────────────────────
// Manual bridge — parse a JSON block the user pasted back after
// running EXTRACTION_PROMPT in claude.ai (no API key / credits used).
// Accepts raw JSON, a ```json fenced block, or JSON with surrounding prose.
// ─────────────────────────────────────────────────────────────
export function parsePastedAnalysis(raw: string, noticeText = ''): AnalysisResponse {
  const trimmed = (raw || '').trim();
  if (!trimmed) throw new Error('Nothing pasted. Copy Claude\'s full reply and paste it here.');

  let jsonStr = trimmed;
  if (jsonStr.startsWith('```')) {
    jsonStr = jsonStr.replace(/^```(?:json)?\s*/i, '').replace(/\s*```\s*$/, '');
  }

  let parsed: any;
  try {
    parsed = JSON.parse(jsonStr);
  } catch {
    const match = jsonStr.match(/\{[\s\S]*\}/);
    if (!match) {
      throw new Error(
        'Could not find a JSON object in the pasted text. Make sure you copied Claude\'s whole reply, including the { … } block.'
      );
    }
    try {
      parsed = JSON.parse(match[0]);
    } catch (err: any) {
      throw new Error(`The pasted text is not valid JSON: ${err.message}`);
    }
  }

  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('The pasted JSON is not a notice object. Expected a single { … } with noticeNumber, issues, etc.');
  }

  return buildAnalysisResponse(parsed, noticeText);
}

// ─────────────────────────────────────────────────────────────
// Convert raw extracted JSON into typed AnalysisResponse
// ─────────────────────────────────────────────────────────────
function buildAnalysisResponse(parsed: any, rawText: string): AnalysisResponse {
  const principalTax = Number(parsed.principalTax) || 0;
  const interest = Number(parsed.interest) || 0;
  const penalty = Number(parsed.penalty) || 0;
  const totalDemand = Number(parsed.totalDemand) || (principalTax + interest + penalty);

  const noticeCase: Omit<NoticeCase, 'id' | 'clientId' | 'createdAt' | 'updatedAt'> = {
    noticeNumber: parsed.noticeNumber || '',
    formType: (parsed.formType as NoticeFormType) || 'DRC-01',
    financialYear: parsed.financialYear || '',
    period: parsed.period || (parsed.financialYear ? `FY ${parsed.financialYear}` : ''),
    noticeDate: parsed.noticeDate || '',
    replyDeadline: parsed.replyDeadline || 'Within 30 Days',
    hearingDate: parsed.hearingDate || '',
    issuingAuthority: parsed.issuingAuthority || '',
    sectionsMentioned: parsed.sectionsMentioned || '',
    principalTax,
    interest,
    penalty,
    totalDemand,
    status: 'UNDER_REVIEW',
    isCaVerified: false,
    din: parsed.din || '',
    rawText: rawText || '',
  };

  const issues: Omit<NoticeIssue, 'id' | 'caseId'>[] = (parsed.issues || []).map((iss: any, index: number) => {
    const taxAmt = Number(iss.taxAmount) || 0;
    const intAmt = Number(iss.interestAmount) || 0;
    const penAmt = Number(iss.penaltyAmount) || 0;
    const legalPos = String(iss.legalPosition || '');
    return {
      issueNumber: Number(iss.issueNumber) || index + 1,
      title: iss.title || `Issue ${index + 1}`,
      allegation: iss.allegation || '',
      sectionRule: iss.sectionRule || '',
      pageRef: iss.pageRef || `Para ${index + 1}`,
      taxAmount: taxAmt,
      interestAmount: intAmt,
      penaltyAmount: penAmt,
      totalAmount: Number(iss.totalAmount) || (taxAmt + intAmt + penAmt),
      probableReason: iss.probableReason || '',
      figureSource: iss.figureSource || '',
      dataRequired: iss.dataRequired || '',
      reconciliationRequired: iss.reconciliationRequired || '',
      clientQuestions: iss.clientQuestions || '',
      documentsRequired: iss.documentsRequired || '',
      defensePoints: iss.defensePoints || '',
      legalPosition: legalPos.includes('[Verify before use]') ? legalPos : `${legalPos} [Verify before use]`,
      riskLevel: (iss.riskLevel === 'LOW' || iss.riskLevel === 'MEDIUM') ? iss.riskLevel : 'HIGH',
      factsCategory: iss.factsCategory || '',
    };
  });

  // Build reconciliations from extracted data
  const reconciliations: Omit<ReconciliationItem, 'id' | 'caseId'>[] = principalTax > 0 ? [
    {
      reconType: 'Notice Demand vs Books',
      period: noticeCase.period,
      noticeValue: principalTax,
      portalValue: 0,
      booksValue: 0,
      variance: principalTax,
      varianceReason: 'Pending reconciliation — verify actual figures from GST portal and books.',
      status: 'MISSING_DATA',
    },
  ] : [];

  const taxpayer = {
    gstin: String(parsed.gstin || '').trim().toUpperCase(),
    legalName: String(parsed.taxpayerName || parsed.taxpayerLegalName || '').trim(),
  };

  return { noticeCase, issues, reconciliations, taxpayer };
}

// ─────────────────────────────────────────────────────────────
// Local fallback parser (no API key) — enhanced regex extractor
// ─────────────────────────────────────────────────────────────
export function parseNoticeLocally(text: string, formTypeHint?: string): AnalysisResponse {
  let formType: NoticeFormType = 'DRC-01';
  if (text.includes('ASMT-10') || text.includes('ASMT 10') || text.includes('ASMT10')) formType = 'ASMT-10';
  else if (text.includes('DRC-01A') || text.includes('DRC 01A')) formType = 'DRC-01A';
  else if (text.includes('REG-17') || text.includes('REG 17')) formType = 'REG-17';
  else if (text.includes('ADT-01') || text.includes('ADT 01')) formType = 'ADT-01';
  else if (text.includes('RFD-08') || text.includes('RFD 08')) formType = 'RFD-08';
  else if (text.includes('MOV-06') || text.includes('MOV 06')) formType = 'MOV-06';
  else if (text.includes('DRC-07') || text.includes('DRC 07')) formType = 'DRC-07';
  else if (formTypeHint) formType = formTypeHint as NoticeFormType;

  const cleanNum = (val: string) => parseFloat(val.replace(/,/g, '').trim()) || 0;
  const firstMatch = (patterns: RegExp[]) => {
    for (const p of patterns) {
      const m = text.match(p);
      if (m && m[1]) return m[1].trim();
    }
    return '';
  };
  const firstAmount = (patterns: RegExp[]) => {
    for (const p of patterns) {
      const m = text.match(p);
      if (m && m[1]) { const n = cleanNum(m[1]); if (n > 0) return n; }
    }
    return 0;
  };


  const noticeNumber = firstMatch([
    /(?:Notice\s*(?:Ref(?:erence)?\s*)?No|Ref\s*No|Notice\s*Number)[.:\s]*([A-Z0-9\/\-]{6,})/i,
    /(?:ZA|DL|MH|GJ|KA|TN|AP|UP|HR|RJ|MP|WB|OR|AS|PB|TG|KL|BR|JH|CT|UK|HP|GA|AR|NL|MN|TR|SK|MZ)(\d{10,})/i,
    /(?:F\.?No\.?|File\s*No)[.:\s]*([A-Z0-9\/\-]{6,50})/i,
  ]);

  const financialYear = firstMatch([
    /(?:Financial\s*Year|F\.?Y\.?)[.\s:–-]*(\d{4}[-\/]\d{2,4})/i,
    /\b(20\d{2}[-\/]\d{2})\b/,
  ]).replace('/', '-');

  const noticeDate = firstMatch([
    /(?:Notice\s*Date|Date\s*of\s*(?:Issue|Notice)|Dated?)[.:\s]*(\d{1,2}[-\/. ]\d{1,2}[-\/. ]\d{2,4})/i,
    /(?:Date)[.:\s]+(\d{2}[-\/]\d{2}[-\/]\d{4})/,
  ]);

  const replyDeadline = firstMatch([
    /(?:Reply\s*(?:by|Deadline|Due\s*Date)|submit\s*(?:your\s*)?reply\s*(?:by|within)|due\s*date)[.:\s]*(\d{1,2}[-\/. ]\d{1,2}[-\/. ]\d{2,4})/i,
    /(?:within)\s*(\d+\s*days?)/i,
  ]) || 'Within 30 Days';

  const hearingDate = firstMatch([
    /(?:Personal\s*Hearing|hearing\s*(?:date|on|scheduled))[.:\s]*(\d{1,2}[-\/. ]\d{1,2}[-\/. ]\d{2,4}(?:\s*(?:at|@)?\s*\d{1,2}:\d{2}\s*(?:AM|PM)?)?)/i,
  ]);

  const issuingAuthority = firstMatch([
    /(?:Deputy|Assistant|Joint|Additional|Principal|State)\s*Commissioner[^\n\r]{0,120}/i,
    /Superintendent[^\n\r]{0,80}GST[^\n\r]{0,40}/i,
    /(?:State|Central)\s*Tax\s*Officer[^\n\r]{0,80}/i,
    /(?:Proper\s*Officer)[^\n\r]{0,60}/i,
  ]).substring(0, 150);

  const din = firstMatch([
    /DIN\s*[:\-]?\s*([A-Z0-9]{15,30})/i,
    /Document\s*Identification\s*Number\s*[:\-]?\s*([A-Z0-9]{15,30})/i,
  ]);

  const gstin = firstMatch([/\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b/]);
  const taxpayerName = firstMatch([
    /(?:M\/s\.?|Taxpayer\s*Name|Trade\s*Name|Legal\s*Name)[.:\s]+([A-Za-z0-9& ,.()\-]{5,80})/i,
    /(?:GSTIN\s*[:\-]\s*[0-9A-Z]{15}\s*[\n\r]\s*)([A-Za-z][A-Za-z0-9& ,.()\-]{4,60})/i,
  ]);

  const igst = firstAmount([/IGST[^\n]{0,30}[:\s]*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i]);
  const cgst = firstAmount([/CGST[^\n]{0,30}[:\s]*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i]);
  const sgst = firstAmount([/(?:SGST|UTGST)[^\n]{0,30}[:\s]*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i]);

  const principalTax = firstAmount([
    /(?:Tax\s*Amount|Principal\s*Tax|Total\s*Tax)[^\n]{0,20}[:\s]*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i,
    /(?:Tax\s*Disputed|Tax\s*Due)[:\s]*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i,
    /(?:(?:IGST|CGST|SGST|Tax\s*Amount|Principal\s*Tax)[^\n]{0,20})[:\s]*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i,
  ]) || (igst + cgst + sgst);

  const interest = firstAmount([/Interest[^\n]{0,20}[:\s]*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i]);
  const penalty = firstAmount([/Penalty[^\n]{0,20}[:\s]*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i]);
  const foundTotal = firstAmount([
    /(?:Total\s*(?:Demand|Amount|Liability|Due)|Grand\s*Total)[^\n]{0,20}[:\s]*(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i,
  ]);
  const totalDemand = foundTotal || (principalTax + interest + penalty);

  const sectionMatches = text.match(/(?:Section|Sec\.?)\s*\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]+\))?/gi);
  const sectionsMentioned = sectionMatches
    ? [...new Set(sectionMatches.map(s => s.trim()))].slice(0, 10).join(', ')
    : (formType === 'ASMT-10' ? 'Section 61' : 'Section 73(1)');

  type RiskLvl = 'HIGH' | 'MEDIUM' | 'LOW';
  interface KwDef {
    keyword: RegExp;
    title: string;
    section: string;
    docs: string;
    defense: string;
    risk: RiskLvl;
  }
  const ISSUE_KEYWORDS: KwDef[] = [
    {
      keyword: /(?:ITC|Input\s*Tax\s*Credit)\s*(?:reversal|mismatch|ineligible|not\s*available|excess|availed)/i,
      title: 'ITC Mismatch / Ineligible Input Tax Credit',
      section: 'Section 16(2), Rule 36(4)',
      docs: 'GSTR-2B month-wise, purchase invoices with supplier GSTIN, bank payment proof for tax paid',
      defense: 'Section 16(2)(aa) — ITC must match GSTR-2B. Rule 36(4) cap reconciliation. Verify supplier filing status on portal. Rule 37A allows reversal and re-availment when supplier files later.',
      risk: 'HIGH',
    },
    {
      keyword: /(?:turnover|outward\s*supply|output)\s*(?:mismatch|difference|discrepancy|not\s*reported|suppressed)/i,
      title: 'Turnover / Output Supply Mismatch (GSTR-1 vs GSTR-3B)',
      section: 'Section 37, Section 39',
      docs: 'GSTR-1, GSTR-3B, sales register, e-way bills, tax invoices, credit notes',
      defense: 'Reconcile GSTR-1 vs GSTR-3B. Differences may be due to timing, credit notes, or exempt supplies. Show amendment returns filed if applicable.',
      risk: 'HIGH',
    },
    {
      keyword: /(?:RCM|reverse\s*charge)/i,
      title: 'Reverse Charge Mechanism (RCM) Liability',
      section: 'Section 9(3), Section 9(4)',
      docs: 'RCM liability register, invoices from unregistered dealers, GSTR-3B Table 3.1(d) data',
      defense: 'Verify specific notifications under Section 9(3). Confirm if RCM was paid in cash ledger and ITC re-availed in same period.',
      risk: 'MEDIUM',
    },
    {
      keyword: /(?:e-?way\s*bill|EWB|transportation|detained|seized|MOV)/i,
      title: 'E-Way Bill / Transportation Compliance Issue',
      section: 'Section 129, Section 130, Rule 138',
      docs: 'E-way bills, tax invoices, lorry receipts / GR, transporter details, gate entry records',
      defense: 'Minor procedural lapses attract penalty under Section 125 only. If tax is paid, goods not liable for confiscation. Section 129(1) — owner can pay tax+penalty and release goods.',
      risk: 'MEDIUM',
    },
    {
      keyword: /(?:GSTR-2B|2[Aa]\s*vs|purchase\s*register|supplier.*not\s*filed|ineligible.*ITC)/i,
      title: 'GSTR-2B vs Purchase Register Mismatch',
      section: 'Section 16(2)(aa), Rule 36(4)',
      docs: 'GSTR-2B month-wise download, purchase register, supplier GSTIN filing status report',
      defense: 'Pending supplier filing does not permanently deny ITC. Rule 37A provides for reversal and re-availment when supplier files. Show supplier has since filed.',
      risk: 'HIGH',
    },
    {
      keyword: /(?:refund|RFD-08|rejection\s*of\s*refund)/i,
      title: 'GST Refund Rejection / Deficiency',
      section: 'Section 54, Rule 89',
      docs: 'Original refund application (RFD-01), GSTR-2B, export invoices / shipping bills, ITC ledger',
      defense: 'Section 54(3) — refund of unutilized ITC. Ensure complete documentation. Check if RFD-03 deficiency memo was issued and whether deficiencies are rectifiable.',
      risk: 'MEDIUM',
    },
    {
      keyword: /(?:exempt|exemption|zero.?rated|nil.?rated|classification)/i,
      title: 'Supply Classification / Exemption Dispute',
      section: 'Section 2(47), Schedule I, II, III',
      docs: 'Contract/agreement, HSN/SAC classification evidence, nature of supply description, AAR ruling if any',
      defense: 'Cite relevant GST exemption notification. Refer to AAR/AAAR rulings. Provide supply classification rationale with HSN code details.',
      risk: 'MEDIUM',
    },
    {
      keyword: /(?:registration|REG-17|cancel)/i,
      title: 'GST Registration Cancellation / Compliance',
      section: 'Section 29, Section 30, Rule 22',
      docs: 'Business continuity proof, filed returns, bank statements showing business activity, reply to SCN',
      defense: 'Section 30 — apply for revocation within 30 days. Show business is active. File all pending returns.',
      risk: 'HIGH',
    },
  ];

  type IssueOmit = Omit<NoticeIssue, 'id' | 'caseId'>;
  const detectedIssues: IssueOmit[] = [];

  for (const kw of ISSUE_KEYWORDS) {
    if (kw.keyword.test(text) && detectedIssues.length < 5) {
      const isFirst = detectedIssues.length === 0;
      detectedIssues.push({
        issueNumber: detectedIssues.length + 1,
        title: kw.title,
        allegation: `Department has raised a discrepancy relating to "${kw.title}" for ${financialYear ? `FY ${financialYear}` : 'the period under notice'}. Review the relevant paragraphs of the notice for specific figures.`,
        sectionRule: kw.section,
        pageRef: `Notice Para ${detectedIssues.length + 1}`,
        taxAmount: isFirst ? principalTax : 0,
        interestAmount: isFirst ? interest : 0,
        penaltyAmount: isFirst ? penalty : 0,
        totalAmount: isFirst ? totalDemand : 0,
        probableReason: `Likely a data mismatch between GST portal filings and departmental audit data${financialYear ? ` for FY ${financialYear}` : ''}.`,
        figureSource: `GST Portal — ASMT/DRC system. ${gstin ? `Taxpayer GSTIN: ${gstin}.` : ''} Verify from portal.`,
        dataRequired: kw.docs,
        reconciliationRequired: 'Prepare month-wise reconciliation of portal data vs books of accounts for the disputed period.',
        clientQuestions: `1. Were all ${kw.title.split('/')[0].trim()} transactions correctly reported in GST returns?\n2. Any credit notes, amendments, or pending supplier GSTR-1 filings?\n3. Are there transactions that are exempt/zero-rated explaining the difference?`,
        documentsRequired: kw.docs,
        defensePoints: kw.defense,
        legalPosition: `Relevant provisions: ${kw.section}, CGST Act 2017. Case laws and circulars to be cited as applicable. [Verify before use]`,
        riskLevel: kw.risk,
        factsCategory: kw.title.split('/')[0].trim(),
      });
    }
  }

  if (detectedIssues.length === 0) {
    detectedIssues.push({
      issueNumber: 1,
      title: '⚠ Offline Parse — Add API Key for Full AI Extraction',
      allegation: `Notice parsed offline (no API key). ${gstin ? `GSTIN detected: ${gstin}. ` : ''}${taxpayerName ? `Taxpayer: ${taxpayerName}. ` : ''}For full issue-by-issue breakdown with defense strategy, add a Claude API key in Settings.`,
      sectionRule: sectionsMentioned,
      pageRef: 'Entire Notice',
      taxAmount: principalTax,
      interestAmount: interest,
      penaltyAmount: penalty,
      totalAmount: totalDemand,
      probableReason: 'Could not auto-detect issue type without AI. Add API key in ⚙ Settings for full analysis.',
      figureSource: `Extracted from pasted text. ${gstin ? `GSTIN: ${gstin}.` : ''}`,
      dataRequired: 'GST returns, invoices, and ledgers for the disputed period',
      reconciliationRequired: 'Portal returns vs books of accounts reconciliation required',
      clientQuestions: 'Please provide all documents related to the disputes raised in the notice.',
      documentsRequired: 'GSTR-1, GSTR-3B, GSTR-2B, purchase register, sales register, invoices, bank statements',
      defensePoints: 'To be determined after detailed notice review. Add AI API key for automated defense point generation.',
      legalPosition: 'Applicable provisions under CGST Act, 2017. [Verify before use]',
      riskLevel: 'HIGH',
      factsCategory: 'GST Notice',
    });
  }

  const noticeCase: Omit<NoticeCase, 'id' | 'clientId' | 'createdAt' | 'updatedAt'> = {
    noticeNumber: noticeNumber || '',
    formType,
    financialYear: financialYear || '',
    period: financialYear ? `FY ${financialYear}` : '',
    noticeDate: noticeDate || '',
    replyDeadline,
    hearingDate,
    issuingAuthority,
    sectionsMentioned,
    principalTax,
    interest,
    penalty,
    totalDemand,
    status: 'UNDER_REVIEW',
    isCaVerified: false,
    din,
    rawText: text,
  };


  const reconciliations: Omit<ReconciliationItem, 'id' | 'caseId'>[] = [
    ...(principalTax > 0 ? [{
      reconType: 'Notice Demand vs Books',
      period: noticeCase.period,
      noticeValue: principalTax,
      portalValue: 0,
      booksValue: 0,
      variance: principalTax,
      varianceReason: 'Pending reconciliation — verify actual figures from GST portal and books.',
      status: 'MISSING_DATA' as const,
    }] : []),
    ...(igst > 0 ? [{
      reconType: 'IGST Demand vs GSTR-3B',
      period: noticeCase.period,
      noticeValue: igst,
      portalValue: 0,
      booksValue: 0,
      variance: igst,
      varianceReason: 'IGST demand from notice — verify Table 3.1 of GSTR-3B.',
      status: 'MISSING_DATA' as const,
    }] : []),
    ...(cgst > 0 ? [{
      reconType: 'CGST Demand vs GSTR-3B',
      period: noticeCase.period,
      noticeValue: cgst,
      portalValue: 0,
      booksValue: 0,
      variance: cgst,
      varianceReason: 'CGST demand from notice — verify Table 3.1 of GSTR-3B.',
      status: 'MISSING_DATA' as const,
    }] : []),
  ];

  return {
    noticeCase,
    issues: detectedIssues,
    reconciliations,
    taxpayer: { gstin: (gstin || '').toUpperCase(), legalName: taxpayerName || '' },
  };
}
