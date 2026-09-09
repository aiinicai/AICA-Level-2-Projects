import express from "express";
import path from "path";
import dotenv from "dotenv";
import { GoogleGenAI, Type } from "@google/genai";
import { createServer as createViteServer } from "vite";

dotenv.config();

const app = express();
const PORT = 3000;

// Set max JSON body size for PDF / image uploads
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// Lazy/safe initialization for Gemini
function getGeminiClient(): GoogleGenAI {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY environment variable is missing.");
  }
  return new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build",
      },
    },
  });
}

// Health check endpoint
app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    service: "Tax Audit ESI & PF Digitizer",
    creator: "CA Ietikka Gupta",
  });
});

// Helper to compute standard Statutory Due Date in India for PF & ESI:
// 15th day of the month following the wage month.
// e.g. Wage month April 2024 (04/2024) -> Due date is 2024-05-15.
function calculateStatutoryDueDate(wageMonthStr: string, yearStr?: string): { dueDate: string; wageKey: string; standardMonth: string } {
  try {
    const monthNames = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"];
    const monthAbbr = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
    
    let monthIndex = -1;
    let year = new Date().getFullYear();

    const lower = (wageMonthStr || "").toLowerCase();
    
    // Check for "MM/YYYY" or "YYYY-MM"
    const mmYyyyMatch = lower.match(/(\d{1,2})[\/\-](\d{4})/);
    const yyyyMmMatch = lower.match(/(\d{4})[\/\-](\d{1,2})/);

    if (mmYyyyMatch) {
      monthIndex = parseInt(mmYyyyMatch[1], 10) - 1;
      year = parseInt(mmYyyyMatch[2], 10);
    } else if (yyyyMmMatch) {
      year = parseInt(yyyyMmMatch[1], 10);
      monthIndex = parseInt(yyyyMmMatch[2], 10) - 1;
    } else {
      for (let i = 0; i < 12; i++) {
        if (lower.includes(monthNames[i]) || lower.includes(monthAbbr[i])) {
          monthIndex = i;
          break;
        }
      }
      const yearMatch = lower.match(/\b(20\d{2})\b/) || (yearStr ? yearStr.match(/\b(20\d{2})\b/) : null);
      if (yearMatch) {
        year = parseInt(yearMatch[1], 10);
      }
    }

    if (monthIndex >= 0 && monthIndex < 12) {
      // Succeeding month
      let dueMonth = monthIndex + 1; // 0-indexed becomes 1-indexed next month
      let dueYear = year;
      if (dueMonth > 11) {
        dueMonth = 0; // January
        dueYear += 1;
      }
      
      const dueMonthPad = String(dueMonth + 1).padStart(2, '0');
      const wageMonthPad = String(monthIndex + 1).padStart(2, '0');
      const dueDate = `${dueYear}-${dueMonthPad}-15`;
      const wageKey = `${year}-${wageMonthPad}`;
      const standardMonth = `${monthNames[monthIndex].charAt(0).toUpperCase() + monthNames[monthIndex].slice(1)} ${year}`;

      return { dueDate, wageKey, standardMonth };
    }
  } catch (e) {
    console.error("Error parsing wage month:", e);
  }

  return { dueDate: "2024-05-15", wageKey: "2024-04", standardMonth: wageMonthStr || "April 2024" };
}

// API endpoint to analyze Challan PDFs or images
app.post("/api/analyze-challan", async (req, res) => {
  try {
    const { files } = req.body; // array of { name, mimeType, base64Data }

    if (!files || !Array.isArray(files) || files.length === 0) {
      return res.status(400).json({
        success: false,
        message: "No files provided. Please upload one or more ESI / PF Challan PDF or image files.",
      });
    }

    const ai = getGeminiClient();
    const extractedRecords: any[] = [];
    const warnings: string[] = [];

    const systemInstruction = `You are an expert Indian Chartered Accountant (CA) Tax Auditor assistant specialized in Form 3CD Clause 20(b) & Section 36(1)(va) Income Tax Audit compliance.
Your job is to digitize and extract structured data with 100% precision from Indian Employee Provident Fund (EPFO / ECR Challan / TRRN Receipt) and Employees' State Insurance Corporation (ESIC Monthly Contribution Challan / Return) documents.

For each challan in the document, extract:
1. "fundType": "PF" (for EPFO / ECR / PMRPY / Provident Fund) or "ESI" (for ESIC / Employees' State Insurance).
2. "establishmentName": Establishment / Company / Employer name.
3. "establishmentId": Establishment ID (e.g. DLCPM0012345000 for PF) or 17-digit Employer Code (e.g. 11000123450001001 for ESI).
4. "wageMonth": Wage / Salary month for which contribution is paid (e.g. "April 2024", "04/2024", "MAY-2024").
5. "financialYear": Relevant Financial Year in YYYY-YYYY format (e.g. "2024-2025" for April 2024 to March 2025).
6. "challanReference": TRRN (Temporary Return Reference Number) for PF, or CRN / Challan Number / Transaction ID for ESI.
7. "actualPaymentDate": Realization / Payment date / Challan Confirmation Date (format: YYYY-MM-DD). If time is included, use the date.
8. "employeeContribution": Total employee's share amount in INR (Numbers only, e.g. 45000). For PF, this is A/C No. 1 Employee share (12%). For ESI, this is Total IP (Insured Person) Contribution (0.75%).
9. "employerContribution": Total employer's share amount in INR (Numbers only). For PF: Employer EPF + EPS + EDLI. For ESI: Employer share (3.25%).
10. "adminOtherCharges": Administration charges / EDLI admin / Inspection charges for PF (A/C No. 2, 22), or 0 for ESI.
11. "totalChallanAmount": Total challan amount paid in INR (Sum of Employee + Employer + Admin charges).
12. "rawExtractedNotes": Any specific notes (e.g. "A/C 1: 45,000, A/C 2: 1,875, A/C 10: 31,245, TRRN: 1012405012345").

Note on Section 36(1)(va) statutory due date:
- In India, due date for depositing employee contribution to PF & ESI is the 15th of the succeeding month (e.g. for April 2024 wage month, statutory due date is 2024-05-15).
- Under Supreme Court Checkmate Services ruling, any deposit after the 15th (or notified extended statutory date) is strictly disallowable under Section 36(1)(va).

Return a clean JSON array matching the schema.`;

    for (let index = 0; index < files.length; index++) {
      const file = files[index];
      const mimeType = file.mimeType || (file.name.endsWith('.pdf') ? 'application/pdf' : 'image/jpeg');
      
      // Clean base64 string if data URL prefix is attached
      let cleanBase64 = file.base64Data;
      if (cleanBase64.includes('base64,')) {
        cleanBase64 = cleanBase64.split('base64,')[1];
      }

      try {
        const response = await ai.models.generateContent({
          model: "gemini-3.7-flash",
          contents: {
            parts: [
              {
                inlineData: {
                  mimeType: mimeType,
                  data: cleanBase64,
                },
              },
              {
                text: `Digitize and extract all PF / ESI challans present in this document "${file.name}". Ensure accurate separation of Employee Share, Employer Share, Wage Month, Payment Date, and TRRN/Challan Reference for Clause 20(b) Tax Audit reporting.`,
              },
            ],
          },
          config: {
            systemInstruction,
            responseMimeType: "application/json",
            responseSchema: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  fundType: {
                    type: Type.STRING,
                    description: "'PF' or 'ESI'",
                  },
                  establishmentName: {
                    type: Type.STRING,
                    description: "Company or establishment name",
                  },
                  establishmentId: {
                    type: Type.STRING,
                    description: "Est ID / Employer Code",
                  },
                  wageMonth: {
                    type: Type.STRING,
                    description: "Wage month, e.g. 'April 2024' or '04/2024'",
                  },
                  financialYear: {
                    type: Type.STRING,
                    description: "Financial Year, e.g. '2024-2025'",
                  },
                  challanReference: {
                    type: Type.STRING,
                    description: "TRRN for PF or Challan/CRN for ESI",
                  },
                  actualPaymentDate: {
                    type: Type.STRING,
                    description: "Payment / Realization Date in YYYY-MM-DD format",
                  },
                  employeeContribution: {
                    type: Type.NUMBER,
                    description: "Employee share amount in INR",
                  },
                  employerContribution: {
                    type: Type.NUMBER,
                    description: "Employer share amount in INR",
                  },
                  adminOtherCharges: {
                    type: Type.NUMBER,
                    description: "Admin & EDLI charges",
                  },
                  totalChallanAmount: {
                    type: Type.NUMBER,
                    description: "Total amount paid",
                  },
                  rawExtractedNotes: {
                    type: Type.STRING,
                    description: "Reference notes or breakdown details",
                  },
                },
                required: [
                  "fundType",
                  "establishmentName",
                  "wageMonth",
                  "challanReference",
                  "actualPaymentDate",
                  "employeeContribution",
                  "totalChallanAmount",
                ],
              },
            },
          },
        });

        const jsonText = response.text?.trim() || "[]";
        let parsedList = [];
        try {
          parsedList = JSON.parse(jsonText);
        } catch (parseErr) {
          console.error("JSON parsing error:", parseErr, jsonText);
        }

        if (Array.isArray(parsedList) && parsedList.length > 0) {
          for (let pIdx = 0; pIdx < parsedList.length; pIdx++) {
            const item = parsedList[pIdx];
            
            // Standardize fundType
            const fundType: 'PF' | 'ESI' = (item.fundType && item.fundType.toUpperCase().includes('ESI')) ? 'ESI' : 'PF';
            
            // Calculate due date & wage month normalization
            const { dueDate, wageKey, standardMonth } = calculateStatutoryDueDate(item.wageMonth, item.financialYear);
            
            // Payment date validation
            let paymentDate = item.actualPaymentDate;
            if (!paymentDate || !paymentDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
              // Try fixing date format or fallback
              const dateMatch = (paymentDate || "").match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
              if (dateMatch) {
                paymentDate = `${dateMatch[3]}-${String(dateMatch[2]).padStart(2, '0')}-${String(dateMatch[1]).padStart(2, '0')}`;
              } else {
                paymentDate = dueDate; // fallback
              }
            }

            // Compliance status determination
            const dueTime = new Date(dueDate).getTime();
            const payTime = new Date(paymentDate).getTime();
            const diffDays = Math.round((payTime - dueTime) / (1000 * 60 * 60 * 24));
            
            const isDelayed = diffDays > 0;
            const status: 'ON_TIME' | 'DELAYED' = isDelayed ? 'DELAYED' : 'ON_TIME';
            const delayDays = isDelayed ? diffDays : 0;
            
            const employeeAmount = Number(item.employeeContribution) || 0;
            const employerAmount = Number(item.employerContribution) || 0;
            const adminAmount = Number(item.adminOtherCharges) || 0;
            let totalAmount = Number(item.totalChallanAmount) || (employeeAmount + employerAmount + adminAmount);

            // Disallowance under Section 36(1)(va) applies ONLY to Employee's contribution if delayed
            const disallowableAmount = isDelayed ? employeeAmount : 0;

            const record = {
              id: `rec_${Date.now()}_${index}_${pIdx}_${Math.random().toString(36).substring(2, 6)}`,
              fundType,
              establishmentName: item.establishmentName || "Establishment",
              establishmentId: item.establishmentId || (fundType === 'PF' ? "DLCPM0000000000" : "11000000000000001"),
              wageMonth: standardMonth,
              wageMonthKey: wageKey,
              financialYear: item.financialYear || (wageKey ? `20${wageKey.slice(2, 4)}-20${parseInt(wageKey.slice(2, 4), 10) + 1}` : "2024-2025"),
              statutoryDueDate: dueDate,
              actualPaymentDate: paymentDate,
              challanReference: item.challanReference || `CH-${Math.floor(100000000000 + Math.random() * 900000000000)}`,
              employeeContribution: employeeAmount,
              employerContribution: employerAmount,
              adminOtherCharges: adminAmount,
              totalChallanAmount: totalAmount,
              status,
              delayDays,
              disallowableAmount,
              fileName: file.name,
              fileType: file.mimeType,
              rawExtractedNotes: item.rawExtractedNotes || `Extracted from ${file.name}`,
            };

            extractedRecords.push(record);
          }
        } else {
          warnings.push(`Could not detect PF or ESI challan structure in "${file.name}". Please verify the document format.`);
        }
      } catch (fileErr: any) {
        console.error(`Error processing file ${file.name}:`, fileErr);
        warnings.push(`Error processing ${file.name}: ${fileErr.message || "Failed to parse document"}`);
      }
    }

    return res.json({
      success: true,
      records: extractedRecords,
      warnings: warnings.length > 0 ? warnings : undefined,
      message: `Successfully processed ${extractedRecords.length} challan record(s).`,
    });
  } catch (err: any) {
    console.error("General error in /api/analyze-challan:", err);
    return res.status(500).json({
      success: false,
      message: err.message || "An unexpected error occurred during digitization.",
    });
  }
});

async function startServer() {
  // Vite middleware for development
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
    console.log(`Tax Audit ESI & PF Digitizer server running on http://localhost:${PORT}`);
  });
}

startServer();
