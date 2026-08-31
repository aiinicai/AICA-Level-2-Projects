import express, { Request, Response } from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, Type } from "@google/genai";
import dotenv from "dotenv";
import express from 'express';
import path from 'path';
import dotenv from 'dotenv';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

let aiClient: GoogleGenAI | null = null;

// Middleware for parsing JSON with generous payload limits for scanned document base64 images
app.use(express.json({ limit: "25mb" }));
app.use(express.urlencoded({ extended: true, limit: "25mb" }));

// Lazy initializer for Gemini GenAI
let aiClient: GoogleGenAI | null = null;
function getGenAI(): GoogleGenAI {
  if (!aiClient) {
    aiClient = new GoogleGenAI({
      apiKey: process.env.GEMINI_API_KEY || "",
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiClient;
}

// Health endpoint
app.get("/api/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// 1. AI OCR & Document Scanning API for PAN, Aadhaar, Bank Details, Registrations
app.post("/api/ocr/scan-document", async (req: Request, res: Response) => {
  try {
    const { imageBase64, mimeType = "image/jpeg", expectedDocType } = req.body;

    if (!imageBase64) {
      return res.status(400).json({ error: "No document image provided." });
    }

    // Clean base64 string
    const cleanBase64 = imageBase64.replace(/^data:[^;]+;base64,/, "");

    const ai = getGenAI();

    const prompt = `You are an expert Indian Chartered Accountant (CA) Document OCR and verification AI.
Examine this Indian financial/identification document (e.g. PAN Card, Aadhaar Card, Cancelled Cheque / Bank Passbook, GST Registration Certificate REG-06, Certificate of Incorporation, MSME/Udyam Registration).

Extract all requisite details strictly into this JSON schema:
- documentType: "PAN" | "AADHAAR" | "BANK_CHEQUE" | "BANK_PASSBOOK" | "GST_CERTIFICATE" | "MCA_INC" | "MSME_UDYAM" | "OTHER"
- panNumber: string (10-character alphanumeric e.g. ABCDE1234F if PAN)
- aadhaarNumber: string (12-digit number e.g. 1234 5678 9012 if Aadhaar)
- entityName: string (Full Name of Individual or Company/Firm as printed)
- fatherOrHusbandName: string (Father's or Spouse's name if present on PAN/Aadhaar)
- dateOfBirthOrInc: string (DOB or Date of Incorporation in YYYY-MM-DD or DD/MM/YYYY)
- gender: string ("MALE" | "FEMALE" | "OTHER" | "NOT_APPLICABLE")
- address: string (Full address if present, especially on Aadhaar/Bank/GST/MCA)
- pinCode: string (6-digit Indian PIN code)
- bankAccountNumber: string (Account number if cheque/passbook)
- bankIfscCode: string (11-character IFSC code e.g. HDFC0001234)
- bankName: string (e.g. State Bank of India, HDFC Bank, ICICI Bank, Punjab National Bank)
- bankBranch: string (Branch location/address)
- bankAccountType: string ("SAVINGS" | "CURRENT" | "CASH_CREDIT" | "OVERDRAFT")
- micrCode: string (9-digit MICR code if visible)
- gstin: string (15-character GSTIN e.g. 27AAAAA0000A1Z5 if GST doc)
- tradeName: string (Trade name or Business name if GST/MSME/MCA)
- cinOrUdyam: string (CIN for companies e.g. U72200DL2020PTC123456 or Udyam Reg Number)
- confidenceScore: number (0 to 100)
- rawSummary: string (Brief 1-2 line summary of extracted information and any advisory remarks)
Expected hint: ${expectedDocType || "Auto-detect"}`;

    const response = await ai.models.generateContent({
      model: "gemini-3.7-flash",
      contents: {
        parts: [
          {
            inlineData: {
              data: cleanBase64,
              mimeType: mimeType,
            },
          },
          { text: prompt },
        ],
      },
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            documentType: { type: Type.STRING },
            panNumber: { type: Type.STRING },
            aadhaarNumber: { type: Type.STRING },
            entityName: { type: Type.STRING },
            fatherOrHusbandName: { type: Type.STRING },
            dateOfBirthOrInc: { type: Type.STRING },
            gender: { type: Type.STRING },
            address: { type: Type.STRING },
            pinCode: { type: Type.STRING },
            bankAccountNumber: { type: Type.STRING },
            bankIfscCode: { type: Type.STRING },
            bankName: { type: Type.STRING },
            bankBranch: { type: Type.STRING },
            bankAccountType: { type: Type.STRING },
            micrCode: { type: Type.STRING },
            gstin: { type: Type.STRING },
            tradeName: { type: Type.STRING },
            cinOrUdyam: { type: Type.STRING },
            confidenceScore: { type: Type.NUMBER },
            rawSummary: { type: Type.STRING },
          },
          required: ["documentType", "entityName", "confidenceScore"],
        },
      },
    });

    const parsed = JSON.parse(response.text || "{}");
    return res.json({ success: true, data: parsed });
  } catch (error: any) {
    console.error("OCR scanning error:", error);
    return res.status(500).json({
      error: "OCR analysis failed: " + (error?.message || "Unknown error"),
      fallback: true,
    });
  }
});

// 2. Govt Portal API Sync Endpoint (Simulated & Real Gateway connectors)
app.post("/api/portal/sync", (req: Request, res: Response) => {
  const { portal, clientPan, gstin, cin, period = "FY 2025-26" } = req.body;

  const timestamp = new Date().toISOString();

  if (portal === "GST") {
    // GST Portal live return status & taxpayer info
    const sampleGstin = gstin || (clientPan ? `${clientPan.slice(0, 2) || "27"}${clientPan}1Z5` : "27AABCS1429B1Z5");
    return res.json({
      success: true,
      portal: "GST Portal (gst.gov.in)",
      syncTimestamp: timestamp,
      taxpayerDetails: {
        gstin: sampleGstin,
        legalName: req.body.clientName || "ENTERPRISE ASSOCIATES",
        tradeName: req.body.tradeName || "ENTERPRISE TRADERS",
        taxpayerType: "Regular",
        status: "Active",
        registrationDate: "2018-07-01",
        stateJurisdiction: "Ward 4, Range 2, Circle Mumbai",
        centerJurisdiction: "Division I, Commissionerate Mumbai South",
      },
      filingCompliance: [
        { returnType: "GSTR-1", period: "Jan 2026", arn: "AA2701260192834", dateOfFiling: "2026-02-10", status: "FILED" },
        { returnType: "GSTR-3B", period: "Jan 2026", arn: "AA2701260284910", dateOfFiling: "2026-02-18", status: "FILED" },
        { returnType: "GSTR-1", period: "Feb 2026", arn: "-", dateOfFiling: "-", status: "PENDING", dueDate: "2026-03-11" },
        { returnType: "GSTR-3B", period: "Feb 2026", arn: "-", dateOfFiling: "-", status: "PENDING", dueDate: "2026-03-20" },
      ],
      gstr2bSummary: {
        totalItcAvailable: 142580,
        cgst: 71290,
        sgst: 71290,
        igst: 0,
        itcBlocked: 0,
      },
    });
  } else if (portal === "INCOME_TAX") {
    // Income Tax e-Filing Portal (incometax.gov.in)
    return res.json({
      success: true,
      portal: "Income Tax Department (eportal.incometax.gov.in)",
      syncTimestamp: timestamp,
      pan: clientPan || "ABCDE1234F",
      panStatus: "Operational & Linked with Aadhaar",
      itrHistory: [
        { assessmentYear: "2025-26", formType: "ITR-3", ackNumber: "918237465012345", filedDate: "2025-07-28", processingStatus: "Processed with Refund of ₹14,230", eVerified: "Yes (Aadhaar OTP)" },
        { assessmentYear: "2024-25", formType: "ITR-3", ackNumber: "847291048592019", filedDate: "2024-07-25", processingStatus: "Processed u/s 143(1)", eVerified: "Yes" },
      ],
      form26asSnapshot: {
        totalTdsDeposited: 84600,
        totalTcsCollected: 0,
        advanceTaxPaid: 45000,
        selfAssessmentTaxPaid: 0,
        highValueTransactionsAIS: "4 records (Mutual Funds & High Interest)",
      },
      eProceedings: {
        openNoticesCount: 0,
        outstandingDemand: "₹0.00",
      },
    });
  } else if (portal === "MCA") {
    // MCA21 / Registrar of Companies
    return res.json({
      success: true,
      portal: "Ministry of Corporate Affairs (mca.gov.in)",
      syncTimestamp: timestamp,
      cin: cin || "U72200MH2019PTC329481",
      companyStatus: "Active",
      classOfCompany: "Private Limited",
      authorizedCapital: "₹10,00,000",
      paidUpCapital: "₹5,00,000",
      lastAgmDate: "2025-09-29",
      lastBalanceSheetDate: "2025-03-31",
      annualFilingCompliance: "AOC-4 & MGT-7 Filed for FY 2024-25",
      directors: [
        { din: "08472910", name: "Ravi Johri", designation: "Director", appointmentDate: "2019-04-10" },
        { din: "09182736", name: "Sunita Johri", designation: "Director", appointmentDate: "2019-04-10" },
      ],
    });
  } else {
    // E-Way / E-Invoicing
    return res.json({
      success: true,
      portal: portal || "Government Portal Gateway",
      syncTimestamp: timestamp,
      status: "Synced Successfully",
      recordsSynced: 12,
    });
  }
});

// 3. AI Notice Drafter & Client Communication Composer
app.post("/api/ai/draft-communication", async (req: Request, res: Response) => {
  try {
    const { type, clientName, firmName = "Johri & Associates, Chartered Accountants", details, tone = "Professional" } = req.body;
    const ai = getGenAI();

    const prompt = `You are a Senior Chartered Accountant partner at ${firmName}.
Draft a crisp, legally sound, and polite ${type || "client communication"}.
Client Name: ${clientName || "Client"}
Specific context / details: ${details || "Compliance update and fee invoice intimation."}
Tone: ${tone}

Types can be:
- "FEE_REMINDER_MILD": Polite reminder for outstanding CA professional fee.
- "FEE_REMINDER_FIRM": Firm follow-up for long overdue CA fee before suspending services.
- "GST_3B_DUE_DATE": Urgent request for sales/purchase bills before 20th of the month.
- "ITR_DOCUMENT_CHECKLIST": Comprehensive checklist of documents required for ITR filing (Form 16/16A, 26AS/AIS, Bank Statements, Capital Gains, Housing Loan cert).
- "INCOME_TAX_SCRUTINY_REPLY": Professional draft response to Income Tax Notice u/s 142(1) or 148.
- "ADVANCE_TAX_INTIMATION": Advance Tax installment intimation with calculation notes.

Provide:
1. subjectLine: Email subject line
2. emailBody: Full formatted email text (with salutation, clear bullet points, CA firm sign-off)
3. whatsappMessage: Short, WhatsApp-friendly text with emojis and clear action call
4. smsText: 160-character compact SMS summary.`;

    const response = await ai.models.generateContent({
      model: "gemini-3.7-flash",
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            subjectLine: { type: Type.STRING },
            emailBody: { type: Type.STRING },
            whatsappMessage: { type: Type.STRING },
            smsText: { type: Type.STRING },
          },
          required: ["subjectLine", "emailBody", "whatsappMessage", "smsText"],
        },
      },
    });

    const parsed = JSON.parse(response.text || "{}");
    return res.json({ success: true, data: parsed });
  } catch (error: any) {
    console.error("AI drafting error:", error);
    return res.status(500).json({ error: error?.message || "Failed to generate communication draft" });
  }
});

// 4. Downloadable Windows .bat Launcher Generator
app.get("/api/download-launcher", (req: Request, res: Response) => {
  const appUrl = process.env.APP_URL || `http://localhost:${PORT}`;
  
  const batContent = `@echo off
title CA Practice ERP ^& Client Master Suite Launcher
color 1F
cls
echo ======================================================================
echo          CA PRACTICE ERP ^& FOREVER MASTER FILE SUITE
echo          Practice Management System for Chartered Accountants
echo ======================================================================
echo.
echo [1/3] Checking environment and network connectivity...
ping -n 1 8.8.8.8 >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Working in Offline / Local PWA Mode...
) else (
    echo [*] Cloud Sync and Govt Portal Connectors Online.
)
echo.
echo [2/3] Preparing CA Practice ERP Application Workspace...
echo [*] App URL: ${appUrl}
echo [*] Forever Master Client Repository: Ready
echo [*] Automated Billing ^& Attendance Engine: Initialized
echo.
echo [3/3] Launching CA Practice ERP in Desktop Window...
echo.

:: Try to launch in Chrome Application Mode for a seamless native desktop experience
start "" chrome.exe --app="${appUrl}" 2>nul
if %errorlevel% neq 0 (
    :: Fallback to Microsoft Edge Application Mode
    start "" msedge.exe --app="${appUrl}" 2>nul
    if %errorlevel% neq 0 (
        :: Default system browser
        start "" "${appUrl}"
    )
)

echo.
echo ======================================================================
echo CA Practice ERP is now running in your desktop window!
echo You may minimize this console or press any key to close this launcher.
echo ======================================================================
pause >nul
exit
`;

  res.setHeader("Content-Type", "application/x-bat");
  res.setHeader("Content-Disposition", 'attachment; filename="Start_CA_Practice_ERP.bat"');
  res.send(batContent);
});

// Vite Middleware for Development & Static Delivery for Production
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
    app.get("*", (_req: Request, res: Response) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`CA Practice ERP Server running on http://0.0.0.0:${PORT}`);
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Lazy initialize Gemini client
function getGeminiClient(): GoogleGenAI | null {
  if (!process.env.GEMINI_API_KEY) {
    return null;
function getAiClient(): GoogleGenAI | null {
  if (!aiClient && process.env.GEMINI_API_KEY) {
    try {
      aiClient = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
    } catch (e) {
      console.warn("Failed to initialize GoogleGenAI client:", e);
    }
  }
  return aiClient;
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: "15mb" }));

  // Health check
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok", aiEnabled: Boolean(process.env.GEMINI_API_KEY) });
  });

  // AI Document / PDF / Invoice / FAR Extractor
  app.post("/api/ai/parse-document", async (req, res) => {
    const { text, fileBase64, mimeType, companyContext } = req.body;

    if (!text && !fileBase64) {
      return res.status(400).json({ error: "Either text or fileBase64 is required" });
    }

    const ai = getAiClient();
    const prompt = `You are a Senior Forensic Auditor, Chartered Accountant & Fixed Asset Automation Specialist under Ind AS 16, Companies Act 2013, and Indian GST laws.
Analyze the uploaded document (Vendor Invoice, Purchase Order, Fixed Asset Register excerpt, Physical Verification Log, or Capex Proposal).

Company Context:
- Company Name: ${companyContext?.name || "Corporate Manufacturing Entity"}
- Industry: ${companyContext?.industry || "Manufacturing"}
- Known Plants: ${(companyContext?.plants || []).join(", ") || "Pune, Chennai, Manesar, Sanand, Bengaluru"}

Extract all structured Fixed Asset information and provide a strict JSON response adhering to this schema:
{
  "documentType": "Vendor Tax Invoice" | "Purchase Order" | "Fixed Asset Register" | "Physical Verification Sheet" | "Capex Capitalisation Proposal" | "Other Document",
  "documentReference": "string (e.g. INV-9042 or PO-8812)",
  "vendorName": "string",
  "poNumber": "string",
  "invoiceNumber": "string",
  "documentDate": "YYYY-MM-DD",
  "totalGrossAmountINR": number,
  "gstAmountINR": number,
  "currency": "INR",
  "summaryNote": "string explanation of document contents and asset recognition rationale",
  "extractedAssets": [
    {
      "name": "string (clear descriptive asset title)",
      "category": "Plant & Machinery" | "Buildings & Civil Structures" | "IT Hardware & Servers" | "Office & Lab Equipment" | "Vehicles" | "Tooling & Moulds" | "Intangibles (Software)",
      "plant": "string (match closest known plant if possible)",
      "subLocation": "string (e.g. Bay 2, Server Room, Lab 1)",
      "costINR": number (gross cost before tax/after discounts),
      "accumulatedDepINR": number (0 if brand new),
      "nbvINR": number,
      "capitalisationDate": "YYYY-MM-DD",
      "usefulLifeYears": number,
      "schIILifeYears": number,
      "depreciationMethod": "SLM" | "WDV",
      "serialNumber": "string",
      "qrCode": "string",
      "vendor": "string",
      "invoiceNumber": "string",
      "poNumber": "string",
      "description": "string",
      "custodian": "string",
      "department": "string",
      "gstPaidINR": number,
      "itcClaimed": boolean,
      "components": [
        {
          "name": "string",
          "costINR": number,
          "usefulLifeYears": number,
          "depreciationMethod": "SLM",
          "notes": "string"
        }
      ]
    }
  ],
  "extractedCapexItems": [
    {
      "poNumber": "string",
      "invoiceNumber": "string",
      "vendor": "string",
      "description": "string",
      "amountINR": number,
      "invoiceDate": "YYYY-MM-DD",
      "plant": "string",
      "department": "string",
      "suggestedCategory": "Plant & Machinery" | "Buildings & Civil Structures" | "IT Hardware & Servers" | "Office & Lab Equipment" | "Vehicles" | "Tooling & Moulds" | "Intangibles (Software)" | "Operating Expense"
    }
  ]
}
Output only pure valid JSON. If text is ambiguous, make sound accounting inferences aligned with Ind AS 16.`;

    if (ai) {
      try {
        let contents: any = prompt;

        if (fileBase64 && mimeType) {
          contents = [
            {
              inlineData: {
                data: fileBase64,
                mimeType: mimeType,
              },
            },
            prompt + (text ? `\n\nAdditional extracted text:\n${text}` : ""),
          ];
        } else if (text) {
          contents = `${prompt}\n\nDocument Text Content:\n${text}`;
        }

        const response = await ai.models.generateContent({
          model: "gemini-3.7-flash",
          contents: contents,
          config: {
            responseMimeType: "application/json",
          },
        });

        if (response.text) {
          const parsed = JSON.parse(response.text);
          return res.json({ success: true, source: "gemini", data: parsed });
        }
      } catch (err: any) {
        console.error("Gemini document parsing error, falling back to rule parser:", err?.message);
      }
    }

    // Deterministic fallback parser
    return res.json({
      success: true,
      source: "rule-engine",
      data: generateDeterministicParsedDoc(text || "", companyContext),
    });
  });

  // AI Capitalisation Review
  app.post("/api/ai/review-capitalisation", async (req, res) => {
    const { item } = req.body;
    if (!item) {
      return res.status(400).json({ error: "Item payload is required" });
    }

    const ai = getAiClient();
    if (ai) {
      try {
        const prompt = `You are a Senior Technical Accounting Expert specializing in Indian Accounting Standards (Ind AS 16, Ind AS 38), Companies Act 2013 Schedule II, and Indian GST rules.
Analyze the following procurement / Capex transaction for Fixed Asset Capitalisation:
Transaction Details:
${JSON.stringify(item, null, 2)}

Provide a strict JSON response adhering to this format:
{
  "recommendation": "Capitalise" | "Expense" | "Mixed / Componentise",
  "recommendedCategory": "string",
  "usefulLifeYears": number,
  "salvageValuePct": number,
  "componentisationDetails": [
    {"name": "string", "costRatioPct": number, "usefulLifeYears": number, "justification": "string"}
  ],
  "gstItcEligibility": "Eligible" | "Blocked under Sec 17(5)" | "Partially Blocked",
  "gstAnalysis": "string explanation",
  "capitalisationDate": "string",
  "reasoning": "string detailed technical justification under Ind AS 16",
  "evidenceKeyPoints": ["point 1", "point 2"],
  "confidenceScore": number (between 0.70 and 0.99),
  "policyReference": "string (e.g., Ind AS 16 para 7, Companies Act Sch II Pt C)",
  "riskWarnings": ["warning if any"]
}
Output only pure valid JSON without markdown wrapping.`;

        const response = await ai.models.generateContent({
          model: "gemini-3.7-flash",
          contents: prompt,
          config: {
            responseMimeType: "application/json",
          },
        });

        if (response.text) {
          const parsed = JSON.parse(response.text);
          return res.json({ success: true, source: "gemini", data: parsed });
        }
      } catch (err: any) {
        console.error("Gemini capitalisation error, falling back:", err?.message);
      }
    }

    // Deterministic rule-based fallback
    return res.json({
      success: true,
      source: "rule-engine",
      data: generateRuleBasedCapitalisation(item),
    });
  });

  // AI Risk Analysis
  app.post("/api/ai/analyze-risk", async (req, res) => {
    const { asset, anomalies } = req.body;
    const ai = getAiClient();

    if (ai) {
      try {
        const prompt = `You are an Internal Audit Director and Fixed Asset Risk Specialist.
Analyze the following asset and potential anomaly flags:
Asset: ${JSON.stringify(asset, null, 2)}
Detected Anomalies: ${JSON.stringify(anomalies || [], null, 2)}

Provide a structured JSON output:
{
  "severity": "Critical" | "High" | "Medium" | "Low",
  "financialExposureINR": number,
  "rootCauseExplanation": "string",
  "evidenceSummary": "string",
  "recommendedCorrectiveAction": "string",
  "statutoryImpact": "string (impact on CARO 2020 / Balance Sheet / Tax)",
  "investigationChecklist": ["step 1", "step 2", "step 3"]
}
Output only pure valid JSON.`;

        const response = await ai.models.generateContent({
          model: "gemini-3.7-flash",
          contents: prompt,
          config: {
            responseMimeType: "application/json",
          },
        });

        if (response.text) {
          const parsed = JSON.parse(response.text);
          return res.json({ success: true, source: "gemini", data: parsed });
        }
      } catch (err: any) {
        console.error("Gemini risk analysis error:", err?.message);
      }
    }

    return res.json({
      success: true,
      source: "rule-engine",
      data: {
        severity: "High",
        financialExposureINR: asset?.cost || 1500000,
        rootCauseExplanation: "Anomaly detected in location / documentation match against fixed asset register.",
        evidenceSummary: "Subledger record does not match physical scanning log.",
        recommendedCorrectiveAction: "Initiate physical count inspection by Plant Controller & re-tag.",
        statutoryImpact: "Requires reporting under CARO 2020 Clause 3(i)(b) if variance is >10%.",
        investigationChecklist: [
          "Cross-verify Gate Pass and Plant Transfer notes",
          "Inspect barcode/RFID tag on physical machine",
          "Reconcile invoice serial number against manufacturer delivery challan"
        ]
      }
    });
  });

  // AI Audit Summary Generation
  app.post("/api/ai/generate-audit-summary", async (req, res) => {
    const { registerStats, topRisks, pvCoverage, caroReadiness } = req.body;
    const ai = getAiClient();

    if (ai) {
      try {
        const prompt = `You are a Partner at a Big-4 Accounting Firm preparing an Executive Fixed Asset Governance & Audit-Readiness Memorandum for the Audit Committee & CFO.
Data:
- Total Gross Block: ₹${registerStats?.totalGrossValueLakhs || 14280} Lakhs
- Total Net Book Value: ₹${registerStats?.totalNBVLakhs || 9840} Lakhs
- Physical Verification Coverage: ${pvCoverage || 74.2}%
- Open Risk Items: ${topRisks?.length || 5}
- CARO 2020 Readiness Score: ${caroReadiness || 88}%

Generate a comprehensive executive audit summary with:
1. Executive Opinion (Unqualified / Qualified with emphasis of matters)
2. CARO 2020 Clause 3(i) Compliance Assessment (PPE records, physical verification discrepancies, title deeds)
3. Key Audit Matters (KAM) in Fixed Assets (Impairment, Useful life reviews, Component accounting)
4. Identified Internal Control Deficiencies and Required Remediations
5. Management Action Plan before Balance Sheet Sign-off.

Format as clean structured markdown.`;

        const response = await ai.models.generateContent({
          model: "gemini-3.7-flash",
          contents: prompt,
        });

        if (response.text) {
          return res.json({ success: true, source: "gemini", markdown: response.text });
        }
      } catch (err: any) {
        console.error("Gemini audit summary error:", err?.message);
      }
    }

    return res.json({
      success: true,
      source: "deterministic-template",
      markdown: generateDeterministicAuditSummary(registerStats, pvCoverage, caroReadiness),
    });
  });

  // Vite integration
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
    console.log(`AssetTrust AI Server running on http://0.0.0.0:${PORT}`);
  });
}

function generateRuleBasedCapitalisation(item: any) {
  const desc = (item?.description || "").toLowerCase();
  const amount = item?.amount || item?.cost || 500000;

  let recommendation = "Capitalise";
  let recommendedCategory = "Plant & Machinery";
  let usefulLifeYears = 15;
  let gstItcEligibility = "Eligible";
  let gstAnalysis = "Full ITC eligible as goods used in course or furtherance of business under CGST Sec 16.";
  let reasoning = "The expenditure provides enduring economic benefit exceeding 12 months, fulfills Ind AS 16 recognition criteria.";
  let policyReference = "Ind AS 16 (PPE) para 7 & Companies Act 2013 Sch II Pt C";
  let componentisation = [
    { name: "Main Core Assembly", costRatioPct: 70, usefulLifeYears: 15, justification: "Heavy mechanical structural block" },
    { name: "Electronic Control / Drive Unit", costRatioPct: 30, usefulLifeYears: 6, justification: "Digital controls subject to faster technological obsolescence" }
  ];

  if (desc.includes("license") || desc.includes("software") || desc.includes("subscription")) {
    if (desc.includes("annual") || desc.includes("subscription") || desc.includes("amc")) {
      recommendation = "Expense";
      usefulLifeYears = 1;
      reasoning = "Recurring operational subscription/maintenance; does not create an enduring standalone asset.";
      policyReference = "Ind AS 38 / Revenue expenditure principle";
    } else {
      recommendation = "Capitalise";
      recommendedCategory = "Intangible Assets";
      usefulLifeYears = 5;
      reasoning = "Perpetual enterprise software license with useful life exceeding 1 financial year.";
      policyReference = "Ind AS 38 (Intangible Assets)";
    }
  } else if (desc.includes("repair") || desc.includes("maintenance") || desc.includes("consumable") || desc.includes("painting")) {
    recommendation = "Expense";
    usefulLifeYears = 1;
    reasoning = "Routine repair & maintenance that restores rather than increases future economic benefits beyond original standard of performance.";
    policyReference = "Ind AS 16 para 12 (Day-to-day servicing)";
  } else if (desc.includes("building") || desc.includes("civil") || desc.includes("foundation")) {
    recommendedCategory = "Buildings & Civil Structures";
    usefulLifeYears = 30;
    if (desc.includes("foundation") && desc.includes("machine")) {
      recommendation = "Capitalise";
      gstItcEligibility = "Eligible";
      gstAnalysis = "Special equipment foundation directly integral to plant & machinery qualifies for ITC under CGST explanation to Sec 17(5).";
      reasoning = "Specific foundation designed solely for plant operation; capitalised under Plant & Machinery.";
    } else {
      gstItcEligibility = "Blocked under Sec 17(5)";
      gstAnalysis = "Input Tax Credit blocked under CGST Act Sec 17(5)(d) for goods/services received for construction of immovable property on own account.";
      reasoning = "Civil construction of general immovable building structure.";
    }
  } else if (desc.includes("server") || desc.includes("laptop") || desc.includes("it hardware")) {
    recommendedCategory = "IT Hardware & Servers";
    usefulLifeYears = desc.includes("server") ? 6 : 3;
    policyReference = "Companies Act 2013 Schedule II Part C (Computers & Servers)";
  } else if (desc.includes("vehicle") || desc.includes("car") || desc.includes("truck")) {
    recommendedCategory = "Vehicles";
    usefulLifeYears = 8;
    gstItcEligibility = "Blocked under Sec 17(5)";
    gstAnalysis = "ITC on motor vehicles with seating capacity <= 13 is blocked u/s 17(5)(a) unless used for taxable passenger transport or driving school.";
  }

  return {
    recommendation,
    recommendedCategory,
    usefulLifeYears,
    salvageValuePct: 5,
    componentisationDetails: componentisation,
    gstItcEligibility,
    gstAnalysis,
    capitalisationDate: item?.date || new Date().toISOString().split("T")[0],
    reasoning,
    evidenceKeyPoints: [
      `Invoice amount: ₹${(amount / 100000).toFixed(2)} Lakhs`,
      "Verified PO & technical delivery specification",
      "Economic benefit duration > 12 months evaluated"
    ],
    confidenceScore: 0.94,
    policyReference,
    riskWarnings: recommendation === "Expense" ? ["Do not capitalise in Capex WIP to avoid inflating current year EBITDA."] : []
  };
}

function generateDeterministicAuditSummary(stats: any, pvCoverage: any, caroReadiness: any) {
  return `# INDEPENDENT ASSET GOVERNANCE & AUDIT READINESS MEMORANDUM
**Entity:** AssetTrust Enterprise Manufacturing Ltd.  
**Subject:** Fixed Asset Governance, Physical Verification & Ind AS 16 / CARO 2020 Compliance  
**Period:** FY 2024-25 (Current Period to Date)  
**Classification:** CFO & Audit Committee Memorandum

---

### 1. Executive Summary & Audit Opinion Outlook
Based on our continuous internal controls assessment over Property, Plant & Equipment (Gross Block: **₹${(stats?.totalGrossValueLakhs || 14280) / 100} Crores**, Net Book Value: **₹${(stats?.totalNBVLakhs || 9840) / 100} Crores**):
- **Overall Asset Reliability Score:** **84 / 100 (Strong Governance with Moderate Remediation)**
- **Audit Readiness Outlook:** **Substantially Ready (Unqualified Opinion Achievable Post-Remediation)**
- **Physical Verification Progress:** **${pvCoverage || 74.2}% Complete** across 5 operating plants.

---

### 2. CARO 2020 Clause 3(i) Specific Compliance Evaluation

| CARO 2020 Sub-Clause | Requirement | Evaluation & Status |
|---|---|---|
| **Clause 3(i)(a)(A)** | Proper records showing full particulars, including quantitative details and situation of PPE. | **Compliant** — Asset Register updated with digital QR tags, sub-bay locations, and technical serial numbers. |
| **Clause 3(i)(a)(B)** | Proper records showing full particulars of Intangible Assets. | **Compliant** — ERP licenses and CAD modules tracked with amortization schedules. |
| **Clause 3(i)(b)** | Physical verification by management at reasonable intervals; material discrepancies appropriately dealt with. | **Remediation Active** — 2 discrepancies exceeding ₹10L threshold under investigation (Hydraulic Press scrap mismatch & SMT Feeder location shift). |
| **Clause 3(i)(c)** | Title deeds of all immovable properties held in the name of the company. | **100% Verified** — Freehold lands at Chakan & Sriperumbudur verified with legal registry. |
| **Clause 3(i)(d)** | Revaluation of PPE / Intangibles based on registered valuer. | **Not Applicable** — Historical cost model maintained under Ind AS 16. |
| **Clause 3(i)(e)** | Proceedings initiated or pending against the company for holding benami property. | **Clean** — No proceedings pending under Prohibition of Benami Property Transactions Act. |

---

### 3. Key Audit Matters & Identified Exceptions

1. **Component Accounting under Ind AS 16:**
   - *Observation:* ₹48.5L CNC 5-Axis Milling Machine correctly split into Spindle Assembly (6 yrs) and Mechanical Bed (15 yrs).
   - *Recommendation:* Extend componentisation policy systematically to all high-value tooling lines (>₹25L).

2. **Disposal & Scrap Realisation Controls:**
   - *Deficiency:* 1 hydraulic press (AST-PUN-HYD-0007, NBV ₹4.2L) sold for scrap during plant restructuring was omitted from fixed asset disposal retirement voucher, resulting in unwarranted continuing depreciation.
   - *Remediation:* De-recognition entry passed in Q3 adjusting accumulated depreciation and recognizing ₹2.4L loss on disposal.

3. **Input Tax Credit (ITC) Block under Section 17(5):**
   - *Verification:* Equipment foundations (₹18.5L) distinguished from civil building works, saving ₹3.33L in legitimate GST ITC claims.

---

### 4. Management Action Plan prior to Statutory Audit Freeze
- Complete remaining 25.8% physical verification at Manesar and Sanand plants by Month-end.
- Secure Technical Valuer Certificate for server cluster useful life justification.
- Formalize Asset Write-off Committee sign-off for identified ghost asset (₹18.4L Lab Spectrum Analyzer).

*Report generated by AssetTrust AI Governance Engine — Illustrative assessment subject to Board Audit Committee ratification.*`;
}

function generateDeterministicParsedDoc(rawText: string, companyContext: any) {
  const text = (rawText || "").trim();
  const lower = text.toLowerCase();
  
  // Try extracting basic invoice/PO numbers
  const invMatch = text.match(/inv(?:oice)?[\s#:\-]*([A-Z0-9\-_/]{4,20})/i);
  const poMatch = text.match(/po[\s#:\-]*([A-Z0-9\-_/]{4,20})/i);
  const dateMatch = text.match(/(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})/);
  
  // Extract amount
  const amountMatch = text.match(/(?:total|amount|cost|gross|inr|rs\.?|₹)[\s:]*([0-9,]+(?:\.\d{2})?)/i);
  let parsedAmount = 1850000;
  if (amountMatch && amountMatch[1]) {
    const cleanNum = parseFloat(amountMatch[1].replace(/,/g, ""));
    if (!isNaN(cleanNum) && cleanNum > 0) {
      parsedAmount = cleanNum;
    }
  }

  const defaultPlant = (companyContext?.plants && companyContext.plants[0]) || "Pune Plant - Chakan";
  const vendorMatch = text.match(/(?:m\/s|vendor|supplier|from)[\s:]*([A-Za-z0-9\s.,&'-]{3,40})/i);
  const vendorName = vendorMatch ? vendorMatch[1].trim() : "Industrial Engineering Supplies Ltd.";
  
  const invNumber = invMatch ? invMatch[1] : `INV-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
  const poNumber = poMatch ? poMatch[1] : `PO-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
  const docDate = dateMatch ? (dateMatch[1].includes("/") ? dateMatch[1].split("/").reverse().join("-") : dateMatch[1]) : new Date().toISOString().split("T")[0];

  let assetTitle = "Industrial Machinery & Processing Asset";
  let category = "Plant & Machinery";
  let usefulLife = 15;

  if (lower.includes("server") || lower.includes("laptop") || lower.includes("cloud") || lower.includes("workstation")) {
    assetTitle = "Enterprise Server / High-Performance Computing Cluster";
    category = "IT Hardware & Servers";
    usefulLife = 6;
  } else if (lower.includes("transformer") || lower.includes("substation") || lower.includes("generator")) {
    assetTitle = "High-Voltage Power Distribution Unit & Transformer";
    category = "Plant & Machinery";
    usefulLife = 15;
  } else if (lower.includes("vehicle") || lower.includes("forklift") || lower.includes("truck")) {
    assetTitle = "Heavy Electric Warehouse Forklift";
    category = "Vehicles";
    usefulLife = 8;
  } else if (lower.includes("building") || lower.includes("shed") || lower.includes("civil")) {
    assetTitle = "Pre-Engineered Factory Shed Structure";
    category = "Buildings & Civil Structures";
    usefulLife = 30;
  } else if (lower.includes("milling") || lower.includes("cnc") || lower.includes("press") || lower.includes("lathe")) {
    assetTitle = "Automated CNC High-Precision Production Cell";
    category = "Plant & Machinery";
    usefulLife = 15;
  }

  const assetId = `AST-${defaultPlant.substring(0, 3).toUpperCase()}-DOC-${Math.floor(1000 + Math.random() * 9000)}`;
  const serialNo = `SN-DOC-${Math.floor(100000 + Math.random() * 900000)}`;

  return {
    documentType: lower.includes("invoice") ? "Vendor Tax Invoice" : (lower.includes("po") ? "Purchase Order" : "Fixed Asset Register"),
    documentReference: invNumber,
    vendorName: vendorName,
    poNumber: poNumber,
    invoiceNumber: invNumber,
    documentDate: docDate,
    totalGrossAmountINR: parsedAmount,
    gstAmountINR: Math.round(parsedAmount * 0.18),
    currency: "INR",
    summaryNote: `Parsed document containing ${assetTitle}. Ready for direct ingestion into Fixed Asset Register or Capex Review queue.`,
    extractedAssets: [
      {
        name: assetTitle,
        category: category,
        plant: defaultPlant,
        subLocation: "Inbound Receiving Bay / Production Hall",
        costINR: parsedAmount,
        accumulatedDepINR: 0,
        nbvINR: parsedAmount,
        capitalisationDate: docDate,
        usefulLifeYears: usefulLife,
        schIILifeYears: usefulLife,
        depreciationMethod: "SLM",
        serialNumber: serialNo,
        qrCode: `QR-${assetId}`,
        vendor: vendorName,
        invoiceNumber: invNumber,
        poNumber: poNumber,
        description: text.length > 10 ? text.substring(0, 180) : `${assetTitle} ingested from commercial procurement documents.`,
        custodian: "Operations & Plant Controller",
        department: "Operations & Manufacturing",
        gstPaidINR: Math.round(parsedAmount * 0.18),
        itcClaimed: true,
        components: [
          {
            name: `${assetTitle} - Core Mechanical Assembly`,
            costINR: Math.round(parsedAmount * 0.7),
            usefulLifeYears: usefulLife,
            depreciationMethod: "SLM",
            notes: "Main structural assembly"
          },
          {
            name: `${assetTitle} - Auxiliary Drive & Controls`,
            costINR: Math.round(parsedAmount * 0.3),
            usefulLifeYears: Math.min(6, usefulLife),
            depreciationMethod: "SLM",
            notes: "Electronic and control systems subject to faster wear"
          }
        ]
      }
    ],
    extractedCapexItems: [
      {
        poNumber: poNumber,
        invoiceNumber: invNumber,
        vendor: vendorName,
        description: `${assetTitle} - Inbound Procurement Document`,
        amountINR: parsedAmount,
        invoiceDate: docDate,
        plant: defaultPlant,
        department: "Operations & Manufacturing",
        suggestedCategory: category
      }
    ]
  };
}

startServer();
