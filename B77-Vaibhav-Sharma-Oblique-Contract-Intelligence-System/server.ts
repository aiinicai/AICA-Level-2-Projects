import express from 'express';
import path from 'path';
import multer from 'multer';
import * as pdfParseModule from 'pdf-parse';
const pdfParse = (pdfParseModule as any).default || pdfParseModule;
import mammoth from 'mammoth';
import { createServer as createViteServer } from 'vite';
import dotenv from 'dotenv';
import { DEMO_CONTRACT_DOCUMENT, DEMO_INVOICE_DATA } from './src/data/demoContract';
import { 
  extractContractStructureAndClauses, 
  analyzeProfessionalImpact, 
  performCrossClauseReasoning, 
  generateExecutiveSummary,
  compareContractWithInvoice
} from './server/geminiService';
import { ContractDocument, InvoiceData } from './src/types/contract';

dotenv.config();

const app = express();
const PORT = 3000;

// Body parser
app.use(express.json({ limit: '25mb' }));
app.use(express.urlencoded({ extended: true, limit: '25mb' }));

// Multer in-memory storage for file uploads (PDF, DOCX, TXT)
const storage = multer.memoryStorage();
const upload = multer({
  storage,
  limits: { fileSize: 20 * 1024 * 1024 }, // 20MB limit
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    if (['.pdf', '.docx', '.txt', '.doc', '.rtf'].includes(ext) || file.mimetype.includes('pdf') || file.mimetype.includes('text')) {
      cb(null, true);
    } else {
      cb(new Error('Only PDF, DOCX, and TXT files are supported.'));
    }
  }
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString(), model: 'gemini-3.7-flash' });
});

// Demo contract endpoint
app.get('/api/demo-contract', (req, res) => {
  res.json({ success: true, contract: DEMO_CONTRACT_DOCUMENT, sampleInvoice: DEMO_INVOICE_DATA });
});

// Document parsing helper
async function extractDocumentContent(buffer: Buffer, fileType: string, fileName: string) {
  let rawText = '';
  let pageCount = 1;
  let pages: { pageNumber: number; text: string }[] = [];

  const ext = path.extname(fileName).toLowerCase();

  if (ext === '.pdf' || fileType.includes('pdf')) {
    try {
      const data = await pdfParse(buffer);
      rawText = data.text || '';
      pageCount = data.numpages || 1;
      
      // Split roughly by page markers or character length if explicit page breaks aren't delimited
      const rawPages = rawText.split(/\f|\n\s*Page \d+|\n\s*-- Page \d+ --/i);
      if (rawPages.length > 1) {
        pages = rawPages.filter(p => p.trim().length > 0).map((pText, i) => ({
          pageNumber: i + 1,
          text: pText.trim()
        }));
        pageCount = pages.length;
      } else {
        // Approximate chunks of ~2500 characters per page if no delimiter found
        const charsPerPage = 2500;
        const totalPages = Math.max(1, Math.ceil(rawText.length / charsPerPage));
        for (let i = 0; i < totalPages; i++) {
          pages.push({
            pageNumber: i + 1,
            text: rawText.slice(i * charsPerPage, (i + 1) * charsPerPage).trim()
          });
        }
        pageCount = totalPages;
      }
    } catch (pdfErr) {
      console.warn('pdf-parse failed, falling back to text representation:', pdfErr);
      rawText = buffer.toString('utf-8');
      pages = [{ pageNumber: 1, text: rawText }];
    }
  } else if (ext === '.docx' || ext === '.doc') {
    try {
      const docxResult = await mammoth.extractRawText({ buffer });
      rawText = docxResult.value || '';
      const paragraphs = rawText.split(/\n\s*\n/);
      const charsPerPage = 2500;
      const totalPages = Math.max(1, Math.ceil(rawText.length / charsPerPage));
      for (let i = 0; i < totalPages; i++) {
        pages.push({
          pageNumber: i + 1,
          text: rawText.slice(i * charsPerPage, (i + 1) * charsPerPage).trim()
        });
      }
      pageCount = totalPages;
    } catch (docxErr) {
      console.warn('mammoth docx extraction failed, using raw string:', docxErr);
      rawText = buffer.toString('utf-8');
      pages = [{ pageNumber: 1, text: rawText }];
    }
  } else {
    // Plain text / markdown
    rawText = buffer.toString('utf-8');
    const charsPerPage = 2500;
    const totalPages = Math.max(1, Math.ceil(rawText.length / charsPerPage));
    for (let i = 0; i < totalPages; i++) {
      pages.push({
        pageNumber: i + 1,
        text: rawText.slice(i * charsPerPage, (i + 1) * charsPerPage).trim()
      });
    }
    pageCount = totalPages;
  }

  return { rawText, pageCount, pages };
}

// Upload endpoint
app.post('/api/upload-contract', upload.single('file'), async (req, res) => {
  try {
    let rawText = '';
    let pageCount = 1;
    let pages: { pageNumber: number; text: string }[] = [];
    let fileName = 'Uploaded_Contract.txt';
    let fileSize = 0;
    let fileType: 'pdf' | 'docx' | 'txt' = 'txt';

    if (req.file) {
      fileName = req.file.originalname;
      fileSize = req.file.size;
      const ext = path.extname(fileName).toLowerCase();
      fileType = ext === '.pdf' ? 'pdf' : ext === '.docx' || ext === '.doc' ? 'docx' : 'txt';

      const extracted = await extractDocumentContent(req.file.buffer, fileType, fileName);
      rawText = extracted.rawText;
      pageCount = extracted.pageCount;
      pages = extracted.pages;
    } else if (req.body.text) {
      rawText = req.body.text;
      fileName = req.body.fileName || 'Manual_Input_Contract.txt';
      fileSize = Buffer.byteLength(rawText, 'utf8');
      fileType = 'txt';
      pages = [{ pageNumber: 1, text: rawText }];
      pageCount = 1;
    } else {
      return res.status(400).json({ error: 'No file or text content provided.' });
    }

    if (!rawText.trim()) {
      return res.status(400).json({ error: 'Extracted document text is empty. Please provide a valid readable document.' });
    }

    return res.json({
      success: true,
      documentMetadata: {
        id: `contract-${Date.now()}`,
        fileName,
        fileSize,
        fileType,
        pageCount,
        uploadedAt: new Date().toISOString(),
        rawText,
        pages
      }
    });
  } catch (error: any) {
    console.error('Error during upload / document extraction:', error);
    return res.status(500).json({ error: error.message || 'Failed to process document.' });
  }
});

// Full AI Analysis Endpoint (Executes multi-stage pipeline)
app.post('/api/analyze-contract', async (req, res) => {
  try {
    const { rawText, pages, fileName, fileSize, fileType, selectedFramework } = req.body;

    if (!rawText || typeof rawText !== 'string' || rawText.trim().length === 0) {
      return res.status(400).json({ error: 'Contract text is required for analysis.' });
    }

    const framework = selectedFramework || 'Ind AS';

    // Stage 1 & 2: Extract identity, parties, commercial terms and segmented clauses
    const structureResult = await extractContractStructureAndClauses(rawText, framework);

    // Stage 3, 4, 5, 6: Deep Professional Impact Analysis (Accounting, GST, TDS, MSME, Related Party, Audit, Disclosure)
    const findings = await analyzeProfessionalImpact(
      rawText, 
      structureResult.clauses, 
      structureResult.commercialTerms, 
      framework
    );

    // Stage 7: Cross-clause interactive reasoning pass
    const crossClauseInsights = await performCrossClauseReasoning(
      rawText,
      findings,
      structureResult.clauses,
      structureResult.commercialTerms
    );

    // Stage 8: Executive summary
    const executiveSummary = await generateExecutiveSummary(
      structureResult.identity,
      structureResult.parties,
      structureResult.commercialTerms,
      findings,
      crossClauseInsights
    );

    const fullDocument: ContractDocument = {
      id: `contract-${Date.now()}`,
      fileName: fileName || 'Contract.pdf',
      fileSize: fileSize || Buffer.byteLength(rawText, 'utf8'),
      fileType: fileType || 'pdf',
      uploadedAt: new Date().toISOString(),
      rawText,
      pageCount: pages?.length || 1,
      pages: pages || [{ pageNumber: 1, text: rawText }],
      parties: structureResult.parties,
      identity: structureResult.identity,
      commercialTerms: structureResult.commercialTerms,
      clauses: structureResult.clauses,
      findings,
      crossClauseInsights,
      selectedFramework: framework,
      invoiceComparisons: [],
      executiveSummary
    };

    return res.json({
      success: true,
      contract: fullDocument
    });
  } catch (error: any) {
    console.error('Error during AI contract analysis:', error);
    return res.status(500).json({ 
      error: error.message || 'AI analysis failed. Please check your document format or try again.' 
    });
  }
});

// Cross-clause reasoning endpoint
app.post('/api/cross-clause-review', async (req, res) => {
  try {
    const { contract } = req.body;
    if (!contract || !contract.rawText) {
      return res.status(400).json({ error: 'Contract data is required.' });
    }

    const insights = await performCrossClauseReasoning(
      contract.rawText,
      contract.findings || [],
      contract.clauses || [],
      contract.commercialTerms || {}
    );

    return res.json({ success: true, crossClauseInsights: insights });
  } catch (error: any) {
    console.error('Error during cross-clause reasoning:', error);
    return res.status(500).json({ error: error.message || 'Failed to perform cross-clause reasoning.' });
  }
});

// Contract vs Invoice comparison endpoint
app.post('/api/compare-invoice', async (req, res) => {
  try {
    const { contract, invoiceData } = req.body;
    if (!contract || !invoiceData) {
      return res.status(400).json({ error: 'Both contract and invoice data are required.' });
    }

    const result = await compareContractWithInvoice(contract, invoiceData);
    return res.json({ success: true, comparison: result });
  } catch (error: any) {
    console.error('Error comparing contract with invoice:', error);
    return res.status(500).json({ error: error.message || 'Failed to compare invoice against contract.' });
  }
});

// Vite Middleware for SPA
async function setupServer() {
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
    console.log(`Contract Impact Intelligence server running on http://0.0.0.0:${PORT}`);
  });
}

setupServer();
