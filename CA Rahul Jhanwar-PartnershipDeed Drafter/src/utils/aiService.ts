/**
 * AI Service for Partnership Deed Drafter
 * Works everywhere:
 * 1. Inside Electron Desktop App (.EXE) on client machines without Node.js
 * 2. In Chrome / Edge browser with or without local server
 * 3. Automatic fallback between local server API and direct Google Gemini REST API
 */

const GEMINI_API_KEY = 'AQ.Ab8RN6LyXKkbiMbn7CP7B7AhbEBcC4OWpP-0cKAu4CDxSgGvTQ';
const GEMINI_MODELS = [
  'gemini-3.1-flash-lite',
  'gemini-3.8-flash',
  'gemini-flash-latest',
  'gemini-2.0-flash',
  'gemini-3.6-flash'
];

/**
 * Helper to call Gemini REST API directly with model fallback
 */
async function callGeminiDirect(
  contents: any[],
  systemInstruction?: string,
  temperature: number = 0.1
): Promise<any> {
  let lastError: any = null;

  for (const model of GEMINI_MODELS) {
    const url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent?key=" + GEMINI_API_KEY;
    
    try {
      const payload: any = {
        contents,
        generationConfig: {
          responseMimeType: 'application/json',
          temperature
        }
      };

      if (systemInstruction) {
        payload.systemInstruction = {
          parts: [{ text: systemInstruction }]
        };
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errText = await res.text();
        console.warn("[AI Service] Model " + model + " returned " + res.status + ":", errText.slice(0, 120));
        lastError = new Error("Model " + model + " error: " + res.status);
        continue;
      }

      const data = await res.json();
      const rawText = data?.candidates?.[0]?.content?.parts?.[0]?.text;
      if (!rawText) {
        continue;
      }

      // Parse JSON
      const cleaned = rawText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
      return JSON.parse(cleaned);
    } catch (err: any) {
      lastError = err;
      console.warn("[AI Service] Error calling " + model + ":", err?.message || err);
    }
  }

  throw lastError || new Error('Failed to connect to Gemini AI services');
}

/**
 * Extract KYC details from Indian PAN Card or UIDAI Aadhaar Card
 */
export async function ocrIdCard(
  fileBase64: string,
  mimeType: string = 'image/jpeg',
  docType: string = 'auto'
): Promise<{ success: boolean; extracted?: any; error?: string; notice?: string }> {
  // 1. Clean base64 string
  const cleanBase64 = fileBase64.replace(/^data:[^;]+;base64,/, '').trim();
  const cleanMime = (mimeType || 'image/jpeg').toLowerCase();

  // Try local express server if available (e.g. running on localhost)
  if (!window.location.protocol.startsWith('file')) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2500);
      const res = await fetch('/api/ocr-id-card', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileBase64, mimeType: cleanMime, docType }),
        signal: controller.signal
      });
      clearTimeout(timeout);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.extracted) {
          return data;
        }
      }
    } catch {
      // Fallback to direct Gemini call
    }
  }

  // 2. Direct Gemini API Fallback (Works 100% in Electron & Desktop)
  const systemPrompt = `You are a precision Indian KYC and Legal Conveyancing OCR Specialist.
Your job is to examine the uploaded Indian KYC document (Income Tax PAN Card, UIDAI Aadhaar Card front, Aadhaar Card back, or combined e-Aadhaar sheet) and extract the cardholder details with high fidelity.

Extract ALL available information present on the document:
1. "name": The Cardholder's Full Legal Name in English in UPPERCASE (ignore labels like 'Name', 'Shri', 'Mr.').
2. "parentName": Father's Name or Husband's Name in UPPERCASE (found under 'Father's Name' on PAN card, or after 'C/O', 'S/O', 'W/O', or 'D/O' on Aadhaar card back). Omit the C/O or S/O prefix from the name string.
3. "relationType": 'HUSBAND' if 'W/O' or 'Wife of' is indicated; otherwise 'FATHER'.
4. "pan": 10-character Permanent Account Number (format: 5 uppercase letters, 4 numbers, 1 letter, e.g., ABCDE1234F).
5. "aadhaar": 12-digit Aadhaar Number (e.g., 1234 5678 9012 or 123456789012).
6. "dob": Date of Birth in strict YYYY-MM-DD format (if DD/MM/YYYY or DD-MM-YYYY is shown, convert it). If only Year of Birth is shown, format as YYYY-01-01.
7. "address": Full Residential Address in English in UPPERCASE (found on Aadhaar back or e-Aadhaar). Include House/Flat No, Society/Building, Street, Landmark, Village/Town/City, Taluka, District, State, and PIN code.
8. "city": City, Town, or District.
9. "state": State in UPPERCASE (e.g., GUJARAT, MAHARASHTRA, RAJASTHAN, DELHI).
10. "pinCode": 6-digit postal PIN code.
11. "gender": 'MALE', 'FEMALE', or 'OTHER'.
12. "titlePrefix": 'MR.', 'MRS.', 'SMT.', 'MISS', or 'DR.'.

Respond ONLY with a valid JSON object strictly matching this schema:
{
  "name": string,
  "titlePrefix": "MR." | "MRS." | "SMT." | "MISS" | "DR.",
  "relationType": "FATHER" | "HUSBAND",
  "parentName": string,
  "pan": string,
  "aadhaar": string,
  "dob": string,
  "address": string,
  "city": string,
  "state": string,
  "pinCode": string,
  "gender": string,
  "cardTypeDetected": "pan_card" | "aadhaar_front" | "aadhaar_back" | "aadhaar_both" | "unknown",
  "confidenceSummary": string
}`;

  try {
    const contents = [
      {
        parts: [
          { text: `Analyze this Indian KYC identity document (${docType}, PDF or image). Examine all pages, cards, and sides. If both front details (Cardholder Name, Aadhaar Number, DOB, Gender, PAN) and back details (Residential Address, Father's/Husband's Name, PIN code, City, State) are present in this single PDF or image (e.g. e-Aadhaar or combined scan), extract ALL OF THEM completely into the JSON format.` },
          {
            inlineData: {
              mimeType: cleanMime.includes('pdf') ? 'application/pdf' : cleanMime,
              data: cleanBase64
            }
          }
        ]
      }
    ];

    const extracted = await callGeminiDirect(contents, systemPrompt, 0.1);
    return { success: true, extracted };
  } catch (err: any) {
    console.error('[AI Service] OCR error:', err);
    return { success: false, error: err?.message || 'Failed to extract text from ID card' };
  }
}

/**
 * Extract existing deed information from scanned PDF or image
 */
export async function extractDeedFromDocument(
  fileBase64: string,
  mimeType: string = 'application/pdf',
  fileName: string = ''
): Promise<{ success: boolean; extracted?: any; error?: string }> {
  const cleanBase64 = fileBase64.replace(/^data:[^;]+;base64,/, '').trim();
  const cleanMime = (mimeType || 'application/pdf').toLowerCase();

  // Try local server first if not on file://
  if (!window.location.protocol.startsWith('file')) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3500);
      const res = await fetch('/api/extract-deed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileBase64, mimeType: cleanMime, fileName }),
        signal: controller.signal
      });
      clearTimeout(timeout);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.extracted) {
          return data;
        }
      }
    } catch {
      // Fallback
    }
  }

  // Direct Gemini API
  const systemPrompt = `You are an expert Indian Legal Conveyancing and Partnership Deed Drafting Specialist.
Analyze this uploaded Partnership Deed document (scanned PDF or images) and extract key particulars with precision:
- Firm Name
- Deed Type (whether Original Partnership Deed, 1st Supplementary Deed, 2nd Supplementary Deed, Reconstitution Deed, or Dissolution Deed)
- Principal Execution Date (YYYY-MM-DD)
- Effective Date of this deed (YYYY-MM-DD)
- Execution Place (City/State)
- Registrar of Firms (RoF) / Sub-Registrar Registration Number (if registered, or state 'Unregistered')
- Key changes or purpose of this deed (e.g., "Initial constitution", "Admission of Partner X & revision of profit sharing ratio", "Retirement of Partner Y")
- Prior Deeds Recited: Any earlier deeds mentioned or recited inside the recitals ("WHEREAS" clauses) of this deed, including their dates and modifications!
- All Partners details (Name, Father's/Husband's Name, Address, PAN, Aadhaar, Profit/Loss Share percentage, Capital amount)
- Total Initial Capital
- Nature of Business Objects
- Existing clauses and terms

Respond strictly with valid JSON format matching:
{
  "firmName": string,
  "deedType": "original" | "supplementary" | "reconstitution" | "amendment",
  "deedLabel": string,
  "principalDeedDate": string,
  "effectiveDate": string,
  "executionPlace": string,
  "rofRegistrationNumber": string,
  "keyChangesSummary": string,
  "totalCapital": number,
  "businessObjects": string,
  "priorDeedsRecited": [
    {
      "deedLabel": string,
      "executionDate": string,
      "effectiveDate": string,
      "rofRegistrationNumber": string,
      "keyChangesSummary": string
    }
  ],
  "partners": [
    {
      "name": string,
      "parentName": string,
      "relationType": "FATHER" | "HUSBAND",
      "address": string,
      "city": string,
      "state": string,
      "pinCode": string,
      "pan": string,
      "aadhaar": string,
      "profitShare": number,
      "capitalContribution": number,
      "status": "existing"
    }
  ],
  "amendmentPoints": string[]
}`;

  try {
    const contents = [
      {
        parts: [
          { text: `Extract all legal details, deed history, and partner particulars from this partnership deed document (${fileName}).` },
          {
            inlineData: {
              mimeType: cleanMime.includes('pdf') ? 'application/pdf' : cleanMime,
              data: cleanBase64
            }
          }
        ]
      }
    ];

    const extracted = await callGeminiDirect(contents, systemPrompt, 0.2);
    return { success: true, extracted };
  } catch (err: any) {
    console.error('[AI Service] Deed extraction error:', err);
    return { success: false, error: err?.message || 'Failed to extract deed particulars' };
  }
}

/**
 * Generate formal Indian partnership business objects clause
 */
export async function generateBusinessObjectsAI(
  rawBusinessIdea: string
): Promise<{ success: boolean; objectsClause?: string; error?: string }> {
  // Try local server first if not file://
  if (!window.location.protocol.startsWith('file')) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2500);
      const res = await fetch('/api/generate-objects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rawBusinessIdea }),
        signal: controller.signal
      });
      clearTimeout(timeout);
      if (res.ok) {
        const data = await res.json();
        if (data.objectsClause) {
          return { success: true, objectsClause: data.objectsClause };
        }
      }
    } catch {
      // Fallback
    }
  }

  // Direct Gemini API
  const systemPrompt = `You are a Senior Indian Corporate & Conveyancing Advocate.
Draft a formal, comprehensive, and legally robust "BUSINESS OBJECTS" clause for an Indian Partnership Deed under the Indian Partnership Act, 1932.
Include primary activities, allied trades, wholesale, retail, import, export, and mutual agreement expansion provisions.

Respond ONLY with valid JSON:
{
  "objectsClause": string
}`;

  try {
    const contents = [
      {
        parts: [
          { text: `Draft business objects for: ${rawBusinessIdea}` }
        ]
      }
    ];

    const data = await callGeminiDirect(contents, systemPrompt, 0.4);
    return { success: true, objectsClause: data.objectsClause || '' };
  } catch (err: any) {
    console.error('[AI Service] Business objects error:', err);
    return { success: false, error: err?.message || 'Failed to draft business objects' };
  }
}

/**
 * Smart offline fallback templates for legal clauses
 */
function getFallbackClauseText(title: string, intent?: string): string {
  const cleanTitle = (title || '').toUpperCase();
  const cleanIntent = (intent || '').trim();

  if (cleanTitle.includes('BANK') || cleanTitle.includes('SIGNING') || cleanTitle.includes('CHEQUE')) {
    return 'All bank accounts of the partnership firm shall be opened and operated in the name of the Firm. Any designated active partner shall be entitled to operate, sign, and draw instruments up to Rs. 50,000/- (Rupees Fifty Thousand only) singly. Any cheque, bill, withdrawal, or financial commitment exceeding Rs. 50,000/- shall strictly require the joint signatures of at least two partners of the firm.';
  }

  if (cleanTitle.includes('LOCK') || cleanTitle.includes('MINIMUM') || cleanTitle.includes('DURATION')) {
    return 'All partners hereby covenant and undertake not to retire, withdraw, or terminate their association with the partnership firm for a mandatory minimum lock-in period of 3 (three) consecutive financial years from the commencement date, except with the unanimous prior written consent of all remaining partners. Any partner seeking premature exit without unanimous consent shall forfeit their share in the accrued goodwill and firm assets.';
  }

  if (cleanTitle.includes('CONFIDENTIAL') || cleanTitle.includes('SECRET') || cleanTitle.includes('NON-DISCLOSURE') || cleanTitle.includes('NDA')) {
    return 'Each partner covenants to maintain absolute confidentiality in respect of all proprietary trade secrets, customer lists, vendor agreements, pricing methodologies, technical know-how, and commercial operations of the partnership firm. No partner shall disclose or divulge any confidential information to third parties, whether during the tenure of the partnership or at any time within 3 (three) years following their retirement or exit from the firm.';
  }

  if (cleanTitle.includes('ARBITRATION') || cleanTitle.includes('DISPUTE')) {
    return 'All disputes, differences, or claims arising out of or in connection with this Deed or the breach, termination, or invalidity thereof shall be referred to a sole arbitrator mutually appointed by the partners, in accordance with the provisions of the Arbitration and Conciliation Act, 1996. The seat and venue of arbitration shall be at the principal place of business of the firm, and the award rendered shall be final and binding.';
  }

  if (cleanTitle.includes('CAPITAL') || cleanTitle.includes('CONTRIBUTION')) {
    return 'Whenever additional working capital or financial infusion is required for the business of the firm, the partners shall contribute such additional capital in proportion to their respective profit-sharing ratios within 30 days of mutual written call. Any excess capital or partner loan contributed shall carry simple interest at the statutory ceiling rate of 12% per annum.';
  }

  if (cleanIntent) {
    return `It is hereby expressly covenanted and agreed by and between the parties hereto that in respect of ${cleanTitle || 'the matter herein'}, ${cleanIntent}. Any operational decision, variation, or implementation thereunder shall be executed through mutual written consensus among the active partners, and shall be legally binding upon the firm and all parties hereto.`;
  }

  return `It is hereby mutually resolved and agreed between the partners that in respect of ${cleanTitle || 'the matter herein'}, the partners shall act jointly and in the best commercial interest of the partnership firm. All decisions, investments, commitments, and liabilities in connection therewith shall require prior unanimous approval in writing, and proper records thereof shall be maintained in the books of the firm.`;
}

/**
 * Generate customized legal clause for Indian Partnership Deed
 */
export async function generateCustomClauseAI(
  clauseTitle: string,
  clauseIntent?: string
): Promise<{ success: boolean; clauseText?: string; error?: string }> {
  const title = clauseTitle.trim();
  const intent = (clauseIntent || '').trim();

  if (!title) {
    return { success: false, error: 'Clause title is required' };
  }

  // 1. Try local server first if not file://
  if (!window.location.protocol.startsWith('file')) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2500);
      const res = await fetch('/api/generate-clause', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clauseTitle: title, clauseIntent: intent || title }),
        signal: controller.signal
      });
      clearTimeout(timeout);
      if (res.ok) {
        const data = await res.json();
        if (data.clauseText) {
          return { success: true, clauseText: data.clauseText };
        }
      }
    } catch {
      // Fallback to direct Gemini
    }
  }

  // 2. Direct Gemini API
  const systemPrompt = `You are a Senior Indian Conveyancing Advocate & Legal Drafting Specialist.
Your task is to draft a formal, legally binding, enforceable, and precise clause for an Indian Partnership Deed under the Indian Partnership Act, 1932.
Style Guidelines:
- Draft in standard Indian legal conveyancing style ("It is hereby mutually agreed and declared...", "Provided that...", etc.).
- Ensure clarity, legal robustness, and proper covenants.
- Keep the clause concise yet comprehensive (1 to 2 paragraphs, 60-140 words).

Respond ONLY with valid JSON strictly matching this schema:
{
  "clauseText": string
}`;

  try {
    const contents = [
      {
        parts: [
          { text: `Draft a formal partnership deed clause with Title: "${title}" and Specific Objective / Intent: "${intent || title}".` }
        ]
      }
    ];

    const data = await callGeminiDirect(contents, systemPrompt, 0.2);
    if (data && data.clauseText && data.clauseText.trim()) {
      return { success: true, clauseText: data.clauseText.trim() };
    }
  } catch (err: any) {
    console.warn('[AI Service] Gemini clause generation warning:', err?.message || err);
  }

  // 3. Fallback to smart local template library
  const fallback = getFallbackClauseText(title, intent);
  return { success: true, clauseText: fallback };
}

