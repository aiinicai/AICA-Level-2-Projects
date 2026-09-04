import express from 'express';
import path from 'path';
import dotenv from 'dotenv';
import { GoogleGenAI } from '@google/genai';
import { createServer as createViteServer } from 'vite';

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));
app.use(express.static(path.join(process.cwd(), 'public')));

// Lazy initialize Gemini client
let aiClient: GoogleGenAI | null = null;
function getGenAI(): GoogleGenAI | null {
  if (!aiClient && process.env.GEMINI_API_KEY) {
    aiClient = new GoogleGenAI({
      apiKey: process.env.GEMINI_API_KEY,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    });
  }
  return aiClient;
}

// Helper function with automatic multi-model fallback & backoff for 503 high demand / 429 quota
async function generateWithFallback(
  ai: GoogleGenAI,
  options: {
    contents: any;
    systemInstruction?: string;
    responseMimeType?: string;
    temperature?: number;
    preferredModels?: string[];
  }
) {
  // Use gemini-3.1-flash-lite first (fast, high-capacity), then gemini-3.8-flash, then gemini-flash-latest
  const modelsToTry = options.preferredModels && options.preferredModels.length > 0
    ? options.preferredModels
    : ['gemini-3.1-flash-lite', 'gemini-3.8-flash', 'gemini-flash-latest'];

  let lastError: any = null;

  for (const modelName of modelsToTry) {
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const config: any = {};
        if (options.systemInstruction) config.systemInstruction = options.systemInstruction;
        if (options.responseMimeType) config.responseMimeType = options.responseMimeType;
        if (typeof options.temperature === 'number') config.temperature = options.temperature;

        const response = await ai.models.generateContent({
          model: modelName,
          contents: options.contents,
          config: Object.keys(config).length > 0 ? config : undefined
        });

        if (response && response.text) {
          return { text: response.text, modelUsed: modelName };
        }
      } catch (err: any) {
        lastError = err;
        const errMsg = err?.message || String(err);
        const isTransient = errMsg.includes('503') || errMsg.includes('UNAVAILABLE') || errMsg.includes('high demand') || errMsg.includes('429');
        
        console.log(`[AI Pipeline] Model ${modelName} attempt ${attempt} notice: ${errMsg.slice(0, 80)}, switching to next option`);
        
        if (isTransient && attempt === 1) {
          await new Promise((r) => setTimeout(r, 600));
        } else {
          break;
        }
      }
    }
  }

  throw lastError || new Error('All model attempts completed without response');
}

// Normalize various date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, YYYY) into standard ISO YYYY-MM-DD
function normalizeDateToISO(raw: any): string {
  if (!raw) return '';
  const s = String(raw).trim();
  // Already ISO YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  // Match DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
  const dmy = s.match(/^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})$/);
  if (dmy) {
    const day = dmy[1].padStart(2, '0');
    const month = dmy[2].padStart(2, '0');
    const year = dmy[3];
    return `${year}-${month}-${day}`;
  }
  // Match YYYY/MM/DD or YYYY.MM.DD
  const ymd = s.match(/^(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})$/);
  if (ymd) {
    return `${ymd[1]}-${ymd[2].padStart(2, '0')}-${ymd[3].padStart(2, '0')}`;
  }
  // Match 4-digit Year only (common on UIDAI Aadhaar: "Year of Birth: 1985")
  const yearOnly = s.match(/\b(19\d{2}|20\d{2})\b/);
  if (yearOnly) {
    return `${yearOnly[1]}-01-01`;
  }
  return '';
}

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

// AI OCR for Indian PAN Card and UIDAI Aadhaar Card
app.post('/api/ocr-id-card', async (req, res) => {
  try {
    const { fileBase64, mimeType = 'image/jpeg', docType = 'auto' } = req.body;
    
    if (!fileBase64) {
      return res.json({ success: false, error: 'No image or document provided', extracted: {} });
    }

    // Clean base64 string if it contains data URI header
    const cleanBase64 = fileBase64.replace(/^data:[^;]+;base64,/, '');
    const cleanMime = (mimeType || '').toLowerCase();

    const ai = getGenAI();
    if (!ai) {
      return res.json({
        success: false,
        error: 'Gemini AI API key is not configured on the server',
        extracted: {}
      });
    }

    const systemPrompt = `You are a precision Indian KYC and Legal Conveyancing OCR Specialist.
Your job is to examine the uploaded Indian KYC document (Income Tax PAN Card, UIDAI Aadhaar Card front, Aadhaar Card back, or combined e-Aadhaar sheet) and extract the cardholder details with high fidelity.

Extract ALL available information present on the document:
1. "name": The Cardholder's Full Legal Name in English in UPPERCASE (ignore labels like 'Name', 'Shri', 'Mr.').
2. "parentName": Father's Name or Husband's Name in UPPERCASE (found under 'Father\'s Name' on PAN card, or after 'C/O', 'S/O', 'W/O', or 'D/O' on Aadhaar card back). Omit the C/O or S/O prefix from the name string.
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

    const promptPart = {
      text: `Analyze this Indian KYC identity document (${docType}) and extract all cardholder details into JSON format.`
    };

    const filePart = {
      inlineData: {
        data: cleanBase64,
        mimeType: cleanMime.includes('pdf') ? 'application/pdf' : cleanMime.includes('png') ? 'image/png' : cleanMime.includes('webp') ? 'image/webp' : 'image/jpeg'
      }
    };

    const genResult = await generateWithFallback(ai, {
      contents: { parts: [filePart, promptPart] },
      systemInstruction: systemPrompt,
      responseMimeType: 'application/json',
      temperature: 0.1
    });

    const responseText = genResult.text?.trim() || '{}';
    let parsed: any = {};
    try {
      parsed = JSON.parse(responseText);
    } catch (e) {
      // Fallback regex cleanup if markdown wrapped
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          parsed = JSON.parse(jsonMatch[0]);
        } catch {
          parsed = {};
        }
      }
    }

    // Comprehensive key normalization to catch alternative keys returned by GenAI
    const rawName = parsed.name || parsed.fullName || parsed.full_name || parsed.cardHolderName || parsed.card_holder_name || '';
    const rawParent = parsed.parentName || parsed.parent_name || parsed.fatherName || parsed.father_name || parsed.fathersName || parsed.husbandName || parsed.husband_name || parsed.careOf || parsed.coName || '';
    const rawPan = parsed.pan || parsed.panNumber || parsed.pan_number || parsed.panNo || parsed.permanentAccountNumber || '';
    const rawAadhaar = parsed.aadhaar || parsed.aadhaarNumber || parsed.aadhaar_number || parsed.uid || parsed.aadhar || parsed.aadharNumber || '';
    const rawDob = parsed.dob || parsed.date_of_birth || parsed.dateOfBirth || parsed.birthDate || parsed.birth_date || parsed.yob || parsed.yearOfBirth || '';
    const rawAddress = parsed.address || parsed.residentialAddress || parsed.residential_address || parsed.fullAddress || parsed.full_address || '';

    // Clean PAN (10 characters: 5 letters, 4 digits, 1 letter)
    let cleanPan = '';
    if (rawPan) {
      const panMatch = String(rawPan).toUpperCase().replace(/[^A-Z0-9]/g, '').match(/[A-Z]{5}[0-9]{4}[A-Z]/);
      cleanPan = panMatch ? panMatch[0] : String(rawPan).toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10);
    }

    // Clean Aadhaar (12 digits formatted as XXXX XXXX XXXX)
    let cleanAadhaar = '';
    const digitsOnly = String(rawAadhaar).replace(/[^0-9]/g, '');
    if (digitsOnly.length >= 12) {
      const d12 = digitsOnly.slice(0, 12);
      cleanAadhaar = `${d12.slice(0, 4)} ${d12.slice(4, 8)} ${d12.slice(8, 12)}`;
    } else if (digitsOnly.length > 0) {
      cleanAadhaar = digitsOnly;
    }

    // Standardize DOB to YYYY-MM-DD
    const cleanDob = normalizeDateToISO(rawDob);

    // Calculate Age
    let calculatedAge = '';
    if (cleanDob && cleanDob.includes('-')) {
      const birthYear = parseInt(cleanDob.split('-')[0], 10);
      const currentYear = new Date().getFullYear();
      if (!isNaN(birthYear) && birthYear > 1900 && birthYear <= currentYear) {
        calculatedAge = String(currentYear - birthYear);
      }
    }

    // Relation Type
    let cleanRelationType = 'FATHER';
    if (String(parsed.relationType || '').toUpperCase().includes('HUSBAND') || String(rawParent).toUpperCase().includes('W/O')) {
      cleanRelationType = 'HUSBAND';
    }

    // Title Prefix
    let cleanPrefix = 'MR.';
    const g = String(parsed.gender || '').toUpperCase();
    const p = String(parsed.titlePrefix || '').toUpperCase().replace(/\./g, '');
    if (p === 'MRS' || p === 'SMT' || g === 'FEMALE') {
      cleanPrefix = cleanRelationType === 'HUSBAND' ? 'MRS.' : 'SMT.';
    } else if (p === 'MISS') {
      cleanPrefix = 'MISS';
    } else if (p === 'DR') {
      cleanPrefix = 'DR.';
    }

    // Clean parent name (remove C/O, S/O, W/O, D/O prefixes)
    let cleanParentName = String(rawParent || '').trim().replace(/^(C\/O|S\/O|W\/O|D\/O|FATHER'S NAME:?|HUSBAND'S NAME:?)\s*/i, '').trim();

    // Clean address (remove leading 'Address:' or 'To,' prefixes)
    let cleanAddress = String(rawAddress || '').trim().replace(/^(ADDRESS:?|TO,?)\s*/i, '').trim();

    console.log(`[AI OCR] Extraction complete. Found: name=${cleanName(cleanName(rawName)) ? 'yes' : 'no'}, pan=${cleanPan ? 'yes' : 'no'}, aadhaar=${cleanAadhaar ? 'yes' : 'no'}, dob=${cleanDob ? 'yes' : 'no'}, address=${cleanAddress ? 'yes' : 'no'}`);

    function cleanName(n: any) {
      return String(n || '').trim().toUpperCase();
    }

    return res.json({
      success: true,
      extracted: {
        name: cleanName(rawName),
        titlePrefix: cleanPrefix,
        relationType: cleanRelationType,
        parentName: cleanParentName.toUpperCase(),
        pan: cleanPan,
        aadhaar: cleanAadhaar,
        dob: cleanDob,
        age: calculatedAge,
        address: cleanAddress.toUpperCase(),
        city: String(parsed.city || '').trim().toUpperCase(),
        state: String(parsed.state || '').trim().toUpperCase(),
        pinCode: String(parsed.pinCode || '').replace(/[^0-9]/g, '').slice(0, 6),
        cardTypeDetected: parsed.cardTypeDetected || 'unknown'
      }
    });

  } catch (error: any) {
    console.error('[AI OCR] Extraction error:', error?.message || error);
    return res.json({
      success: false,
      error: error?.message || 'AI OCR service currently busy. You can type details manually.',
      notice: 'AI OCR service could not parse document. You may enter details manually.',
      extracted: {}
    });
  }
});

// AI OCR & Intelligent Extraction for Existing Partnership Deed (PDF or Scanned Images)
app.post('/api/extract-deed', async (req, res) => {
  try {
    const { fileBase64, mimeType = 'application/pdf', fileName = '' } = req.body;

    if (!fileBase64) {
      return res.status(400).json({ success: false, error: 'No deed file payload provided' });
    }

    const cleanBase64 = fileBase64.replace(/^data:[^;]+;base64,/, '');
    const cleanMime = (mimeType || '').toLowerCase();
    const effectiveMime = cleanMime.includes('pdf') 
      ? 'application/pdf' 
      : cleanMime.includes('png') 
      ? 'image/png' 
      : cleanMime.includes('webp') 
      ? 'image/webp' 
      : 'image/jpeg';

    const ai = getGenAI();
    if (!ai) {
      return res.json({
        success: false,
        error: 'Gemini AI API key is not configured on the server'
      });
    }

    const systemPrompt = `You are an elite Indian Legal Conveyancing and Partnership Law Specialist with extensive expertise in analyzing Partnership Deeds executed under the Indian Partnership Act, 1932.
Your task is to analyze the uploaded scanned Partnership Deed document (PDF or Image) and extract all factual legal particulars required to draft a Supplementary / Modification Deed or a Deed of Dissolution.

Extract with high fidelity:
1. Firm Name (e.g. "M/S. XYZ ASSOCIATES" or "XYZ TRADERS")
2. Date of execution / Principal Deed date (convert to YYYY-MM-DD format if possible)
3. Place / City of execution (e.g. "AHMEDABAD", "MUMBAI", "DELHI", "JAIPUR")
4. Firm Registration number (RoF or Sub-Registrar / Diary registration number, if mentioned)
5. Principal place of business / Firm address
6. Nature of Business / Business Objects clause
7. Partners: List of all partners with their:
   - Full Legal Name
   - Title prefix ('MR.', 'MRS.', 'MISS', 'SMT.', 'DR.')
   - Relation type ('FATHER' or 'HUSBAND')
   - Father's / Spouse's name
   - PAN card number (10 chars, if found)
   - Aadhaar number (12 digits, if found)
   - Date of birth (YYYY-MM-DD) or calculated age
   - Residential address
   - Profit / Loss sharing ratio percentage (number or string like "50", "33.33")
   - Capital contribution amount if stated
   - Working partner status (true/false)
8. Witnesses (if present on signature page)
9. Interest on Capital rate (e.g. "12")
10. Remuneration details (e.g. whether Section 40(b) / 35(e) or fixed amount)
11. Brief summary of the deed and key conditions

Return ONLY a valid JSON object matching this schema:
{
  "firmName": string,
  "originalDeedDate": string,
  "originalDeedCity": string,
  "registrationNumber": string,
  "firmAddress": string,
  "firmObjects": string,
  "interestRate": string,
  "remunerationSummary": string,
  "bankOperationSummary": string,
  "partners": [
    {
      "name": string,
      "titlePrefix": "MR." | "MRS." | "MISS" | "SMT." | "DR." | "",
      "relationType": "FATHER" | "HUSBAND",
      "parentName": string,
      "pan": string,
      "aadhaar": string,
      "dob": string,
      "age": string,
      "address": string,
      "profitShare": string,
      "capitalContribution": string,
      "isWorking": boolean
    }
  ],
  "witnesses": [
    {
      "name": string,
      "parentName": string,
      "address": string
    }
  ],
  "existingClausesSummary": string,
  "confidenceSummary": string
}`;

    const promptPart = {
      text: `Carefully read and OCR the attached Indian Partnership Deed document (${fileName || 'Partnership_Deed'}). Extract all firm information, execution dates, every partner's complete legal particulars, addresses, profit sharing percentages, and business clauses into the exact JSON schema.`
    };

    const filePart = {
      inlineData: {
        data: cleanBase64,
        mimeType: effectiveMime
      }
    };

    const genResult = await generateWithFallback(ai, {
      contents: { parts: [filePart, promptPart] },
      systemInstruction: systemPrompt,
      responseMimeType: 'application/json',
      temperature: 0.1,
      preferredModels: ['gemini-3.1-flash-lite', 'gemini-3.8-flash']
    });

    const responseText = genResult.text?.trim() || '{}';
    let parsed: any = {};
    try {
      parsed = JSON.parse(responseText);
    } catch (e) {
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        parsed = JSON.parse(jsonMatch[0]);
      }
    }

    // Ensure partners array exists
    if (!Array.isArray(parsed.partners) || parsed.partners.length === 0) {
      parsed.partners = [];
    }

    return res.json({
      success: true,
      extracted: parsed,
      modelUsed: genResult.modelUsed
    });
  } catch (error: any) {
    console.error('[AI Deed OCR Error]:', error);
    return res.status(500).json({
      success: false,
      error: error?.message || 'Failed to extract partnership deed details. Please verify file format.'
    });
  }
});

// AI Draft Business Objects endpoint
app.post('/api/generate-objects', async (req, res) => {
  try {
    const { rawBusinessIdea, industry, customPrompt } = req.body;
    const inputTerms = (rawBusinessIdea || industry || '').trim();
    
    if (!inputTerms) {
      return res.status(400).json({ error: 'Business activity description is required' });
    }

    // Normalize common input typos (e.g. "ITEAM" -> "items")
    const cleanIdea = inputTerms
      .replace(/\biteam\b/gi, 'items')
      .replace(/\biteams\b/gi, 'items')
      .replace(/\bproduck\b/gi, 'products')
      .replace(/\bpackings\b/gi, 'packaging')
      .trim();

    const fallbackDraft = `The business of the partnership shall be to carry on in India or elsewhere the business of designing, manufacturing, processing, creating, handcrafting, procuring, packing, packaging, customizing, assembling, curating, stocking, distributing, marketing, exporting, importing, and dealing in ${cleanIdea.toLowerCase()}, through physical retail outlets, wholesale distribution networks, departmental stores, institutional supply, and e-commerce platforms; and to act as service providers, contractors, consultants, commercial agents, dealers, stockists, and representatives in respect of all allied items, raw materials, accessories, tools, equipment, and consumables connected therewith; and to undertake all incidental, auxiliary, and complementary commercial operations as may be deemed expedient or beneficial by the partners from time to time under the Indian Partnership Act, 1932.`;

    const ai = getGenAI();
    if (!ai) {
      return res.json({
        objectsClause: fallbackDraft,
        source: 'fallback_engine',
        note: 'Generated via built-in Legal Drafting Engine'
      });
    }

    const promptText = `Act as an expert Indian legal drafter specializing in partnership deed drafting under the Indian Partnership Act, 1932.
Draft an exhaustive, highly professional, industry-standard 'Nature of Business / Business Objects' clause for a Partnership Deed.
Business Activity Description: "${cleanIdea}".
${customPrompt ? `Special specific focus: ${customPrompt}` : ''}

Drafting Requirements:
- Write in formal Indian legal conveyancing style in clear sentence case with appropriate capitalizations for defined terms.
- Cover principal operations, allied/ancillary services, trading/procurement of related items/equipment, e-commerce, and a standard enabling clause for incidental activities.
- Provide ONLY the drafted paragraph text. Do not include markdown asterisks, quotation marks, introductory pleasantries, bullet points, or numbering.`;

    const genResult = await generateWithFallback(ai, {
      contents: promptText
    });

    const generatedText = genResult.text?.trim();
    if (!generatedText) {
      throw new Error('No text returned from model');
    }

    res.json({
      objectsClause: generatedText,
      source: genResult.modelUsed
    });
  } catch (error: any) {
    console.log('[AI Objects] Service notice: applying statutory legal fallback');
    const inputTerms = (req.body.rawBusinessIdea || req.body.industry || 'commercial activities and services').trim();
    const cleanIdea = inputTerms
      .replace(/\biteam\b/gi, 'items')
      .replace(/\biteams\b/gi, 'items')
      .replace(/\bproduck\b/gi, 'products')
      .replace(/\bpackings\b/gi, 'packaging')
      .toLowerCase();

    const fallbackDraft = `The business of the partnership shall be to carry on in India or elsewhere the business of designing, manufacturing, processing, creating, handcrafting, procuring, packing, packaging, customizing, assembling, curating, stocking, distributing, marketing, exporting, importing, and dealing in ${cleanIdea}, through physical retail outlets, wholesale distribution networks, departmental stores, institutional supply, and e-commerce platforms; and to act as service providers, contractors, consultants, commercial agents, dealers, stockists, and representatives in respect of all allied items, raw materials, accessories, tools, equipment, and consumables connected therewith; and to undertake all incidental, auxiliary, and complementary commercial operations as may be deemed expedient or beneficial by the partners from time to time under the Indian Partnership Act, 1932.`;
    
    res.json({
      objectsClause: fallbackDraft,
      source: 'fallback_engine',
      error: error?.message || 'Fallback applied'
    });
  }
});

// AI Draft Custom Legal Clause endpoint
app.post('/api/generate-clause', async (req, res) => {
  try {
    const { clauseTitle, clauseIntent } = req.body;
    const ai = getGenAI();

    if (!ai) {
      return res.json({
        clauseText: `The partners mutually covenant and agree that in respect of ${clauseTitle || 'all matters'}, ${clauseIntent || 'the affairs shall be governed by mutual written consent and customary legal standards'}.`,
        source: 'fallback_engine'
      });
    }

    const promptText = `Draft a formal, legally enforceable clause for a Partnership Deed under the Indian Partnership Act, 1932.
Clause Title: "${clauseTitle}"
Intent/Condition: "${clauseIntent}"
Instructions: Return ONLY the formal legal clause text in a single cohesive paragraph. No markdown asterisks, no quotes.`;

    const genResult = await generateWithFallback(ai, {
      contents: promptText
    });

    res.json({
      clauseText: genResult.text?.trim() || '',
      source: genResult.modelUsed
    });
  } catch (error: any) {
    res.json({
      clauseText: `The partners hereby agree that ${req.body.clauseIntent || 'all partners shall comply with applicable statutory standards'}.`,
      source: 'fallback_engine'
    });
  }
});

async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
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
    console.log(`Partnership Deed Drafter server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
