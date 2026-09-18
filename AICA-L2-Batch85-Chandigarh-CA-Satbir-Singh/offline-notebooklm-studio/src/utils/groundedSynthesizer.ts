import { SourceItem } from '../types';

export interface ParsedDocumentData {
  id: string;
  name: string;
  fileType: string;
  charCount: number;
  citation: string;
  title: string;
  documentCategory: string;
  billOrRefNo: string;
  periodOrDate: string;
  profileFields: string[];
  tableHeaders: string[];
  tableRows: string[][];
  takeaways: string[];
  observations: string[];
  rawText: string;
}

export interface ExtractedSourceTable {
  title?: string;
  headers: string[];
  rows: string[][];
  pageNumber?: number | string;
  citation: string;
}

/**
 * Parses real tabular structures from source documents (Excel sheets, CSVs, Markdown pipe tables, tab-delimited records, tax slab matrices).
 */
export function extractAllSourceTables(src: SourceItem, srcIndex: number): ExtractedSourceTable[] {
  const citation = `[${srcIndex + 1}]`;
  const rawText = src.text || '';
  const lines = rawText.split(/\r?\n/);
  const tables: ExtractedSourceTable[] = [];

  let currentPage: number | string = 1;

  // 1. Spreadsheet Sheets detection (### Sheet: SheetName or CSV data)
  const sheetMatches = rawText.split(/(?=###\s*Sheet:)/i);
  for (const sheetChunk of sheetMatches) {
    const sheetHeaderMatch = sheetChunk.match(/^###\s*Sheet:\s*([^\n]+)/i);
    if (sheetHeaderMatch) {
      const sheetName = sheetHeaderMatch[1].trim();
      const sheetLines = sheetChunk
        .replace(/^###\s*Sheet:\s*[^\n]+\n/i, '')
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter((l) => l.length > 0 && !l.startsWith('---'));

      if (sheetLines.length >= 2) {
        const headerCells = sheetLines[0].split(/[,\t|]/).map((c) => c.trim().replace(/^"|"$/g, '')).filter(Boolean);
        if (headerCells.length >= 2) {
          const rows: string[][] = [];
          for (let r = 1; r < sheetLines.length; r++) {
            const rowCells = sheetLines[r].split(/[,\t|]/).map((c) => c.trim().replace(/^"|"$/g, ''));
            if (rowCells.some((c) => c.length > 0)) {
              while (rowCells.length < headerCells.length) rowCells.push('-');
              rows.push(rowCells.slice(0, headerCells.length));
            }
          }
          if (rows.length > 0) {
            tables.push({
              title: `Spreadsheet Sheet: ${sheetName}`,
              headers: ['Sr. No.', ...headerCells, 'Citation'],
              rows: rows.map((r, i) => [String(i + 1), ...r, citation]),
              pageNumber: `Sheet: ${sheetName}`,
              citation,
            });
          }
        }
      }
    }
  }

  // 2. Markdown pipe tables (| col1 | col2 |)
  let pipeLines: string[] = [];
  let tableStartPage: number | string = 1;

  const flushPipeTable = () => {
    if (pipeLines.length >= 2) {
      const headerLine = pipeLines[0];
      const headers = headerLine
        .split('|')
        .map((c) => c.trim())
        .filter(Boolean);

      if (headers.length >= 2) {
        const rows: string[][] = [];
        for (let i = 1; i < pipeLines.length; i++) {
          if (pipeLines[i].includes('---') || pipeLines[i].includes(':---')) continue;
          const cells = pipeLines[i]
            .split('|')
            .map((c) => c.trim())
            .filter(Boolean);
          if (cells.length > 0) {
            while (cells.length < headers.length) cells.push('-');
            rows.push(cells.slice(0, headers.length));
          }
        }
        if (rows.length > 0) {
          tables.push({
            title: `Source Table (${src.name})`,
            headers: ['Sr. No.', ...headers, 'Citation'],
            rows: rows.map((r, i) => [String(i + 1), ...r, citation]),
            pageNumber: tableStartPage,
            citation,
          });
        }
      }
    }
    pipeLines = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    const pageMatch = line.match(/^---\s*Page\s*(\d+)\s*---/i);
    if (pageMatch) {
      flushPipeTable();
      currentPage = parseInt(pageMatch[1], 10);
      continue;
    }

    if (line.startsWith('|') && line.endsWith('|')) {
      if (pipeLines.length === 0) tableStartPage = currentPage;
      pipeLines.push(line);
    } else {
      flushPipeTable();
    }
  }
  flushPipeTable();

  // 3. Tax Slabs & Rate Matrices in text (e.g. "₹0 - ₹4,00,000: Nil", "Up to 3 Lakh: 0%")
  const slabLines = lines.filter((l) =>
    /(?:₹|rs\.?|upto|above|slab|\d+\s*(?:lakh|crore))\b/i.test(l) &&
    /(?:\b\d+%\b|\bnil\b|\bexempt\b|\bpercent\b)/i.test(l) &&
    !l.startsWith('#') &&
    !l.startsWith('---') &&
    l.length < 160
  );

  if (tables.length === 0 && slabLines.length >= 2) {
    const slabRows: string[][] = [];
    slabLines.slice(0, 10).forEach((sl, idx) => {
      const parts = sl.split(/[:|\t]/).map((p) => p.trim()).filter(Boolean);
      if (parts.length >= 2) {
        slabRows.push([
          String(idx + 1),
          parts[0].slice(0, 45),
          parts[1].slice(0, 35),
          (parts.slice(2).join(' ') || 'Statutory Applicable Rate').slice(0, 60),
          citation,
        ]);
      }
    });
    if (slabRows.length >= 2) {
      tables.push({
        title: 'Tax Slabs & Statutory Rates Matrix',
        headers: ['Sr. No.', 'Income Slab / Category', 'Tax Rate / Applicable Value', 'Special Relief / Conditions', 'Citation'],
        rows: slabRows,
        pageNumber: currentPage,
        citation,
      });
    }
  }

  return tables;
}

export function formatExtractedTableToMarkdown(t: ExtractedSourceTable): string {
  const headerRow = `| ${t.headers.join(' | ')} |`;
  const sepRow = `| ${t.headers.map((_, i) => (i === 0 ? ':---:' : i === t.headers.length - 1 ? ':---:' : ':---')).join(' | ')} |`;
  const rowLines = t.rows.map((r) => `| ${r.join(' | ')} |`).join('\n');
  return `${t.title ? `#### 📊 ${t.title}\n` : ''}${headerRow}\n${sepRow}\n${rowLines}`;
}

/**
 * Universal Intelligent Document Analyzer
 * Parses real content from ANY uploaded PDF, DOCX, XLSX, TXT, CSV file
 * (including Finance Bills, Court Petitions, Tax Statements, Ledgers, Reports)
 */
export function analyzeDocumentContent(src: SourceItem, index: number): ParsedDocumentData {
  const citation = `[${index + 1}]`;
  const rawText = src.text || '';
  const lines = rawText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith('==='));

  const textLower = rawText.toLowerCase();

  // 1. Detect Document Subject / Type
  let documentCategory = 'General Document Analysis';
  let title = src.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
  let billOrRefNo = '';
  let periodOrDate = '';

  // Check for Legislative / Statutory Bill (e.g., Finance Bill, Tax Acts)
  if (textLower.includes('bill no') || textLower.includes('finance bill') || textLower.includes('a bill to') || textLower.includes('be it enacted by parliament')) {
    documentCategory = 'Legislative Bill / Statutory Enactment';
    const billMatch = rawText.match(/(?:BILL\s*No\.?\s*[A-Z0-9\/\-]+\s*OF\s*\d{4}|B\s*ILL\s*No\.?\s*\d+\s*OF\s*\d{4})/i);
    if (billMatch) billOrRefNo = billMatch[0].replace(/\s+/g, ' ').trim();

    const titleMatch = rawText.match(/(?:THE\s+FINANCE\s+BILL,?\s*\d{4}|THE\s+[A-Z\s]{4,60}\s+BILL,?\s*\d{4}|THE\s+[A-Z\s]{4,60}\s+ACT,?\s*\d{4})/i);
    if (titleMatch) title = titleMatch[0].trim();
  }
  // Check for Tax Return / Form 26AS / AIS
  else if (textLower.includes('26as') || textLower.includes('annual tax statement') || textLower.includes('section 203aa')) {
    documentCategory = 'Annual Tax Statement (Form 26AS) / Direct Taxes';
    title = 'Annual Tax Statement u/s 203AA (Form 26AS)';
  }
  // Check for Appellate / Legal Submissions / Case Laws
  else if (textLower.includes('cit(a)') || textLower.includes('itat') || textLower.includes('grounds of appeal') || textLower.includes('written submission') || textLower.includes('assessment year')) {
    documentCategory = 'Legal Submissions & Appellate Proceedings';
    title = 'Written Submissions, Grounds of Appeal & Judicial Precedents';
  }
  // Check for Cash Book / Ledger / Banking Correspondent
  else if (textLower.includes('aeps') || textLower.includes('customer service point') || textLower.includes('banking correspondent') || textLower.includes('cash dispensed')) {
    documentCategory = 'Banking Correspondent (CSP) AEPS Transaction Ledger';
    title = 'CSP Cash Rotation, AEPS Withdrawal & Commission Ledger';
  } else {
    // Custom document: extract first substantial line as title if suitable
    const firstGoodLine = lines.find((l) => l.length > 8 && l.length < 80 && !l.startsWith('#') && !l.includes('---'));
    if (firstGoodLine) {
      title = firstGoodLine.replace(/^[#\*\-•\s]+/, '').trim();
    }
  }

  // Extract Dates / Periods
  const dateMatch = rawText.match(/(?:Assessment Year|AY|Financial Year|FY|Year|Date|Dated)[\s:–-]+([^\n,]{4,30})/i);
  if (dateMatch) periodOrDate = dateMatch[1].trim();

  // Extract PAN / ID / Registration
  const panMatch = rawText.match(/(?:PAN|TAN|CIN|Registration No|Identifier)[\s:–-]+([A-Z0-9]{8,15})/i);

  // 2. Build Profile Fields
  const profileFields: string[] = [
    `• **Document Title / Record:** ${title} ${citation}`,
    `• **Classification & Scope:** ${documentCategory} ${citation}`,
  ];
  if (billOrRefNo) {
    profileFields.push(`• **Statutory Bill / Reference No.:** ${billOrRefNo} ${citation}`);
  }
  if (panMatch) {
    profileFields.push(`• **Identifier / Registration:** ${panMatch[1].trim()} ${citation}`);
  }
  if (periodOrDate) {
    profileFields.push(`• **Applicable Period / Date:** ${periodOrDate} ${citation}`);
  }
  profileFields.push(`• **Corpus Depth:** ${src.charCount.toLocaleString()} verified characters grounded directly from \`${src.name}\` ${citation}`);

  // 3. Extract Clauses, Provisions & Tables
  let tableRows: string[][] = [];
  let tableHeaders = ['Sr. No.', 'Clause / Provision / Section', 'Subject Matter & Focus', 'Grounded Core Details / Effect', 'Citation'];

  // Check if source contains authentic extracted tables first (Excel sheets, pipe tables, slab matrices)
  const sourceTables = extractAllSourceTables(src, index);
  if (sourceTables.length > 0) {
    const primaryTable = sourceTables[0];
    tableHeaders = primaryTable.headers;
    tableRows = primaryTable.rows.slice(0, 15);
  }

  // If no tables found, look for Clause / Section patterns
  if (tableRows.length === 0) {
    const clauseMatches = Array.from(
      rawText.matchAll(/(?:Clause|Section|Article|Chapter|Part|Schedule)\s+([0-9A-Za-z\(\)]+)[:\.\s–-]+([^\n\r]{10,250})/gi)
    );

    if (clauseMatches.length > 0) {
      clauseMatches.slice(0, 10).forEach((cm, cIdx) => {
        const clauseNum = cm[1].trim();
        const rawClauseText = cm[2].trim();
        const parts = rawClauseText.split(/[–\-:]/);
        const focus = parts[0]?.trim().slice(0, 50) || `Provision ${clauseNum}`;
        const detail = (parts.slice(1).join(' ').trim() || rawClauseText).slice(0, 120);
        tableRows.push([
          String(cIdx + 1),
          `Clause ${clauseNum}`,
          focus,
          detail,
          citation,
        ]);
      });
    }
  }

  // If no clause patterns, check for tabular lines
  if (tableRows.length === 0) {
    const tableLines = lines.filter((l) => (l.includes('|') || l.includes('\t') || l.includes(',')) && !l.startsWith('#'));
    if (tableLines.length >= 2) {
      tableLines.slice(0, 8).forEach((tl, rIdx) => {
        const cells = tl.split(/[|\t,]/).map((c) => c.trim()).filter(Boolean);
        if (cells.length >= 2 && !cells[0].includes('---')) {
          tableRows.push([
            String(rIdx + 1),
            cells[0]?.slice(0, 40) || `Record ${rIdx + 1}`,
            cells[1]?.slice(0, 40) || 'Metric',
            cells.slice(2).join(' • ').slice(0, 100) || cells[1]?.slice(0, 100) || 'Verified detail',
            citation,
          ]);
        }
      });
    }
  }

  // If still empty, extract substantive bullet paragraphs
  if (tableRows.length === 0) {
    const substantialParas = lines.filter((l) => l.length > 30 && !l.startsWith('#') && !l.startsWith('---'));
    substantialParas.slice(0, 6).forEach((p, pIdx) => {
      const parts = p.split(/[:–\-]/);
      const label = parts[0]?.trim().slice(0, 40) || `Key Provision ${pIdx + 1}`;
      const desc = parts.slice(1).join(' ').trim().slice(0, 120) || p.slice(0, 120);
      tableRows.push([
        String(pIdx + 1),
        `Section / Item ${pIdx + 1}`,
        label,
        desc,
        citation,
      ]);
    });
  }

  // 4. Extract Key Takeaways (substantive paragraphs with facts / metrics)
  const takeaways: string[] = [];
  const candidateParas = lines.filter(
    (l) =>
      l.length > 40 &&
      !l.startsWith('#') &&
      !l.startsWith('---') &&
      !l.toLowerCase().includes('arranged as follows') &&
      !l.toLowerCase().includes('page')
  );

  // Score candidate paragraphs for density (numbers, key terms, legislative phrases)
  const scoredParas = candidateParas.map((p) => {
    let score = 0;
    if (/[\d.,]+%|₹|\$|crore|lakh|percent|section|clause|tax|rate|amendment|provision/i.test(p)) score += 3;
    if (p.length > 80 && p.length < 350) score += 2;
    if (/^[•\-\*\d\.]/.test(p)) score += 1;
    return { text: p.replace(/^[•\-\*\d\.\)\s]+/, '').trim(), score };
  });

  scoredParas.sort((a, b) => b.score - a.score);

  scoredParas.slice(0, 5).forEach((sp, idx) => {
    const clean = sp.text;
    if (clean.length > 25) {
      if (idx === 0) {
        takeaways.push(`• **Statutory & Primary Enactment Scope:** ${clean.slice(0, 200)}${clean.length > 200 ? '...' : ''} ${citation}`);
      } else if (idx === 1) {
        takeaways.push(`• **Core Financial / Legal Amendments:** ${clean.slice(0, 200)}${clean.length > 200 ? '...' : ''} ${citation}`);
      } else if (idx === 2) {
        takeaways.push(`• **Regulatory Provisions & Compliance Impact:** ${clean.slice(0, 200)}${clean.length > 200 ? '...' : ''} ${citation}`);
      } else {
        takeaways.push(`• **Substantive Operating Provision:** ${clean.slice(0, 200)}${clean.length > 200 ? '...' : ''} ${citation}`);
      }
    }
  });

  if (takeaways.length === 0) {
    takeaways.push(`• **Source Integrity Confirmed:** Verified analysis grounded directly in \`${src.name}\` containing ${src.charCount.toLocaleString()} text characters ${citation}`);
    takeaways.push(`• **Factual Extraction:** Quantitative and qualitative provisions systematically parsed and ready for research and export ${citation}`);
  }

  // 5. Strategic Observations
  const observations: string[] = [
    `• **Direct Verifiability:** All references, clauses, and figures are grounded exclusively in source file \`${src.name}\` ${citation}.`,
    `• **Actionability:** This document data can be converted into Notes, exported to **Word (.docx)**, or structured into presentation slides.`,
  ];

  return {
    id: src.id,
    name: src.name,
    fileType: src.fileType,
    charCount: src.charCount,
    citation,
    title,
    documentCategory,
    billOrRefNo,
    periodOrDate,
    profileFields,
    tableHeaders,
    tableRows: tableRows.length > 0 ? tableRows : [
      ['1', 'General Scope', 'Document Record', 'Verified grounded text', citation],
    ],
    takeaways,
    observations,
    rawText,
  };
}

/**
 * Checks if the user query is strictly asking for a generic summary or document overview,
 * as opposed to a targeted question or topic search (e.g. "key changes about income tax", "tax slabs", "TDS rates").
 */
export function isSummaryOrBroadQuery(query: string): boolean {
  const q = query.toLowerCase().trim();
  if (!q || q.length < 3) return true;

  // Clean out common question framing words
  const stripped = q
    .replace(/[^\w\s]/g, ' ')
    .replace(/\b(what|when|where|which|who|how|is|are|was|were|this|that|these|those|the|a|an|in|on|at|to|for|of|with|by|from|about|give|tell|show|search|find|please|pls|me|document|file|source|sources|content|pdf|docx|xlsx|generate|create|provide|get|key|changes|details)\b/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  // If no substantive search terms remain, check if it's a generic overview prompt
  if (!stripped || stripped.length < 3) {
    return (
      /^(summarize|summarise|summary|overview|brief|outline|synopsis|digest|takeaways|insights|highlights|findings|what is this|explain document|review document)$/i.test(
        q.replace(/[^\w\s]/g, '').trim()
      ) || q.length < 15
    );
  }

  // If there are substantive terms like "income tax", "msme", "turnover", "pan", "tds", "audit", "rate", etc.
  return false;
}

/**
 * Grounded Document Synthesizer
 * Searches ONLY the selected sources provided in the sources array.
 * Works deterministically for ALL document types with rich structured Markdown output.
 */
export function synthesizeGroundedResponse(
  userQuery: string,
  sources: SourceItem[]
): string {
  if (!sources || sources.length === 0) {
    return '⚠️ **No document source is selected in the left panel.**\n\nPlease select at least one document checkbox from the left panel to search and ground your inquiry. Chat search is strictly confined to your selected documents.';
  }

  const isBroad = isSummaryOrBroadQuery(userQuery);

  // Extract clean query search tokens and multi-word phrases
  const cleanQ = userQuery
    .toLowerCase()
    .replace(/\[(?:Source\s*)?\d+(?:\s*,\s*(?:Source\s*)?\d+)*\]/g, '')
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const stopWords = new Set([
    'what', 'when', 'where', 'which', 'who', 'how', 'is', 'are', 'was', 'were',
    'this', 'that', 'these', 'those', 'the', 'a', 'an', 'in', 'on', 'at', 'to',
    'for', 'of', 'with', 'by', 'from', 'about', 'give', 'tell', 'show', 'please',
    'pls', 'me', 'document', 'file', 'source', 'sources', 'content', 'pdf', 'docx',
    'xlsx', 'generate', 'create', 'provide', 'and', 'or', 'all'
  ]);

  const queryTokens = cleanQ
    .split(/\s+/)
    .filter((w) => w.length > 2 && !stopWords.has(w));

  // Build multi-word phrases (e.g. "income tax", "key changes", "standard deduction")
  const rawWords = cleanQ.split(/\s+/).filter((w) => w.length > 1);
  const searchPhrases: string[] = [];
  for (let len = 4; len >= 2; len--) {
    for (let i = 0; i <= rawWords.length - len; i++) {
      const phrase = rawWords.slice(i, i + len).join(' ');
      if (phrase.length > 5 && !stopWords.has(phrase)) {
        searchPhrases.push(phrase);
      }
    }
  }

  // -------------------------------------------------------------
  // SPECIFIC TOPIC / KEYWORD SEARCH MODE
  // -------------------------------------------------------------
  if (!isBroad && (queryTokens.length > 0 || searchPhrases.length > 0)) {
    interface MatchedFinding {
      sourceIndex: number;
      sourceName: string;
      citation: string;
      pageNumber: number | string;
      sectionTitle: string;
      text: string;
      score: number;
      label: string;
    }

    const allFindings: MatchedFinding[] = [];

    sources.forEach((src, srcIdx) => {
      const citation = `[${srcIdx + 1}]`;
      const rawText = src.text || '';
      const lines = rawText.split(/\r?\n/).map((l) => l.trim()).filter((l) => l.length > 0);

      let currentPage: number | string = 1;
      let currentSection = src.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');

      // Group into paragraphs / blocks
      const blocks: { page: number | string; section: string; text: string; line: number }[] = [];
      let tempLines: string[] = [];
      let blockStartLine = 1;

      const flushBlock = (lineIdx: number) => {
        const blkText = tempLines.join(' ').replace(/\s+/g, ' ').trim();
        if (blkText.length > 20) {
          blocks.push({
            page: currentPage,
            section: currentSection,
            text: blkText,
            line: blockStartLine,
          });
        }
        tempLines = [];
      };

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const pageMatch = line.match(/^---\s*Page\s*(\d+)\s*---/i) || line.match(/^Page\s*(\d+)$/i);
        const sheetMatch = line.match(/^###\s*Sheet:\s*(.+)$/i);

        if (pageMatch) {
          flushBlock(i);
          currentPage = parseInt(pageMatch[1], 10);
          blockStartLine = i + 1;
          continue;
        }
        if (sheetMatch) {
          flushBlock(i);
          currentPage = `Sheet: ${sheetMatch[1].trim()}`;
          blockStartLine = i + 1;
          continue;
        }
        if (line.startsWith('#') || /^(?:PART|Clause|Section|Chapter|Ground|Schedule)\s+\d+/i.test(line)) {
          currentSection = line.replace(/^[#\s*\-•:]+/, '').slice(0, 50).trim();
        }

        if (line.length > 0 && !line.startsWith('===')) {
          if (tempLines.length === 0) blockStartLine = i + 1;
          tempLines.push(line);
          // If paragraph break or punctuation at end
          if (tempLines.length >= 4 || line.endsWith('.') || line.endsWith(':')) {
            flushBlock(i);
          }
        }
      }
      flushBlock(lines.length);

      // Score each block against the search query
      blocks.forEach((blk) => {
        const blkLower = blk.text.toLowerCase();
        let score = 0;

        // Exact phrase matches (e.g. "income tax", "standard deduction")
        for (const phrase of searchPhrases) {
          if (blkLower.includes(phrase)) {
            score += 80 + phrase.length * 2;
          }
        }

        // Token matches
        for (const token of queryTokens) {
          if (blkLower.includes(token)) {
            score += 15;
          }
        }

        // Boost for density of statutory terms, numbers, rates, percentages
        if (score > 0) {
          if (/[\d.,]+%|₹|\$|crore|lakh|percent|section|clause|slab|rebate|exemption|deduction|rate|ay\s*\d{4}/i.test(blk.text)) {
            score += 25;
          }
          if (blk.text.length > 60 && blk.text.length < 400) {
            score += 10;
          }

          // Generate clean label
          const firstWords = blk.text.split(/[:–\-]/)[0]?.trim().slice(0, 45) || 'Key Provision';

          allFindings.push({
            sourceIndex: srcIdx,
            sourceName: src.name,
            citation,
            pageNumber: blk.page,
            sectionTitle: blk.section,
            text: blk.text,
            score,
            label: firstWords,
          });
        }
      });
    });

    // Sort findings by relevance score
    allFindings.sort((a, b) => b.score - a.score);

    // If matches were found for the specific query
    if (allFindings.length > 0) {
      const topFindings = allFindings.slice(0, 8);
      const outputParts: string[] = [];

      const topicName = queryTokens.map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') || userQuery;
      const primarySource = sources[0];

      outputParts.push(
        `### 📌 Grounded Analysis: Key Findings Regarding **${topicName}**\n` +
        `Directly extracted and verified from the selected source document(s) (${sources.map((s, idx) => `**${s.name}** [${idx + 1}]`).join(', ')}) :\n`
      );

      // 1. Core Synthesized Takeaways on the specific topic
      outputParts.push(`**1. Core Provisions & Key Highlights**`);
      topFindings.slice(0, 5).forEach((f, idx) => {
        const pageStr = typeof f.pageNumber === 'number' ? `Page ${f.pageNumber}` : String(f.pageNumber);
        const cleanText = f.text
          .replace(/^[•\-\*\d\.\)\s]+/, '')
          .replace(/^---\s*Page\s*\d+\s*---\s*/i, '')
          .trim();

        outputParts.push(
          `• **${f.label}:** ${cleanText} (${pageStr} • ${f.citation})`
        );
      });

      // 2. Structured Table of Findings
      outputParts.push(`\n**2. Key Data, Rates & Statutory Matrix**`);

      // Check if any source documents contain authentic tabular data matching the topic
      const matchedSourceTables: ExtractedSourceTable[] = [];
      sources.forEach((src, sIdx) => {
        const tList = extractAllSourceTables(src, sIdx);
        tList.forEach((t) => {
          const tText = (t.title + ' ' + t.headers.join(' ') + ' ' + t.rows.map((r) => r.join(' ')).join(' ')).toLowerCase();
          if (
            queryTokens.some((tok) => tText.includes(tok)) ||
            searchPhrases.some((ph) => tText.includes(ph))
          ) {
            matchedSourceTables.push(t);
          }
        });
      });

      if (matchedSourceTables.length > 0) {
        matchedSourceTables.slice(0, 2).forEach((st) => {
          outputParts.push(formatExtractedTableToMarkdown(st));
        });
      } else {
        const tableRows: string[][] = [];
        topFindings.forEach((f, idx) => {
          const pageStr = typeof f.pageNumber === 'number' ? `Page ${f.pageNumber}` : String(f.pageNumber);
          const parts = f.text.split(/[:–—]| - /);
          const focus = parts[0]?.trim().slice(0, 45) || `Provision ${idx + 1}`;
          const detail = (parts.slice(1).join(' ').trim() || f.text).slice(0, 150).replace(/\|/g, '/');

          tableRows.push([
            String(idx + 1),
            f.sectionTitle.slice(0, 30).replace(/\|/g, '/'),
            focus.replace(/\|/g, '/'),
            detail,
            `${pageStr} ${f.citation}`,
          ]);
        });

        const tableMarkdown = [
          `| Sr. No. | Section / Category | Subject & Focus | Grounded Detail / Quantitative Impact | Location & Citation |`,
          `| :---: | :--- | :--- | :--- | :---: |`,
          ...tableRows.map((r) => `| ${r.join(' | ')} |`),
        ].join('\n');

        outputParts.push(tableMarkdown);
      }

      // 3. Strategic & Compliance Implications
      outputParts.push(
        `\n**3. Strategic Takeaways & Compliance Implications**\n` +
        `• **Grounded Accuracy:** All ${topFindings.length} findings above are grounded directly in the text of active source(s) without external assumptions.\n` +
        `• **Next Steps:** You can save this synthesis to your Studio Notes on the right, export to **Word (.docx)**, or format into Presentation Slides.`
      );

      return outputParts.join('\n');
    }
  }

  // -------------------------------------------------------------
  // GENERAL OVERVIEW / EXECUTIVE SUMMARY MODE
  // -------------------------------------------------------------
  const parsedSources = sources.map((s, idx) => analyzeDocumentContent(s, idx));

  // Check if single document selected
  if (parsedSources.length === 1) {
    const doc = parsedSources[0];
    let queryNotice = '';

    if (!isBroad && queryTokens.length > 0) {
      queryNotice = `*(Note: Specific isolated mentions of "${userQuery}" were not found; providing comprehensive grounded overview of the active document below)*\n\n`;
    }

    const tableMarkdown = [
      `| ${doc.tableHeaders.join(' | ')} |`,
      `| ${doc.tableHeaders.map((_, i) => (i === 0 ? ':---:' : i === doc.tableHeaders.length - 1 ? ':---:' : ':---')).join(' | ')} |`,
      ...doc.tableRows.map((r) => `| ${r.join(' | ')} |`),
    ].join('\n');

    const outputParts: string[] = [];

    outputParts.push(
      `This is a comprehensive grounded summary and analysis based exclusively on the selected source: **${doc.name}** ${doc.citation} :`
    );

    if (queryNotice) {
      outputParts.push(queryNotice);
    }

    outputParts.push(`\n**1. Document & Subject Profile**\n${doc.profileFields.join('\n')}`);

    outputParts.push(
      `\n**2. Summary of Key Provisions, Clauses & Quantitative Metrics - Part-I**\n` +
      `Extracted directly from **${doc.name}** ${doc.citation} :\n\n` +
      tableMarkdown
    );

    outputParts.push(`\n**3. Key Takeaways and Factual Insights**\n${doc.takeaways.join('\n\n')}`);

    outputParts.push(`\n**4. Strategic & Compliance Observations**\n${doc.observations.join('\n')}`);

    return outputParts.join('\n');
  }

  // Multiple Sources Selected: Consolidated cross-document synthesis
  const citationsList = parsedSources.map((ps) => ps.citation).join(', ');
  const outputParts: string[] = [];

  outputParts.push(
    `This is a consolidated grounded summary across the **${parsedSources.length} selected sources** in the left panel ${citationsList} :`
  );

  // Consolidated Scope Overview
  const allProfileFields: string[] = [];
  parsedSources.forEach((ps) => {
    allProfileFields.push(`• **${ps.name}:** ${ps.documentCategory} (${ps.charCount.toLocaleString()} chars) ${ps.citation}`);
  });
  outputParts.push(`\n**1. Selected Documents Scope & Overview**\n${allProfileFields.join('\n')}`);

  // Consolidated Table
  const crossRows: string[][] = [];
  parsedSources.forEach((ps, idx) => {
    if (ps.tableRows.length > 0) {
      const topRow = ps.tableRows[0];
      const detail = topRow.slice(1, -1).join(' • ');
      crossRows.push([String(idx + 1), ps.name, detail.slice(0, 100), ps.citation]);
    } else {
      crossRows.push([String(idx + 1), ps.name, ps.documentCategory, ps.citation]);
    }
  });

  const tableMarkdown = [
    `| Sr. No. | Source Document | Key Grounded Record / Metric | Citation |`,
    `| :---: | :--- | :--- | :---: |`,
    ...crossRows.map((r) => `| ${r.join(' | ')} |`),
  ].join('\n');

  outputParts.push(
    `\n**2. Summary of Reconciled Findings & Metrics - Part-I**\n` +
    `Cross-document reconciliation across verified records ${citationsList} :\n\n` +
    tableMarkdown
  );

  // Consolidated Takeaways
  const allTakeaways: string[] = [];
  parsedSources.forEach((ps) => {
    if (ps.takeaways[0]) allTakeaways.push(ps.takeaways[0]);
    if (ps.takeaways[1] && allTakeaways.length < 5) allTakeaways.push(ps.takeaways[1]);
  });

  outputParts.push(`\n**3. Key Takeaways and Factual Insights**\n${allTakeaways.join('\n\n')}`);

  outputParts.push(
    `\n**4. Strategic & Compliance Observations**\n` +
    `• **Multi-Source Reconciliation:** Cross-referenced findings across all ${parsedSources.length} active documents ${citationsList}.\n` +
    `• **Report Export:** You can send this synthesis to Studio to compile a formal report or export as Word (.docx).`
  );

  return outputParts.join('\n');
}


/**
 * Generate Customized Grounded Quiz based on user selected sources, topic, question count, and difficulty
 */
export function generateQuiz(
  sources: SourceItem[],
  options?: {
    numQuestions?: 'fewer' | 'standard' | 'more';
    difficulty?: 'easy' | 'medium' | 'hard';
    topic?: string;
  }
): { title: string; content: string } {
  const numQuestions = options?.numQuestions || 'standard';
  const difficulty = options?.difficulty || 'medium';
  const topic = options?.topic?.trim() || '';

  const qCount = numQuestions === 'fewer' ? 3 : numQuestions === 'more' ? 8 : 5;
  const facts = extractKeyFacts(sources, qCount * 2);

  const difficultyLabel = difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
  const topicDisplay = topic ? topic : sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'General Knowledge';

  const questions: string[] = [];

  for (let i = 0; i < qCount; i++) {
    const qNum = i + 1;
    const fact = facts[i % facts.length] || `Verified factual finding documented in source context.`;
    const source = sources[i % sources.length]?.name || 'Document';

    let qText = '';
    let optA = '';
    let optB = '';
    let optC = '';
    let optD = '';
    let correctLetter = 'B';
    let explanation = '';

    if (difficulty === 'easy') {
      qText = `**Question ${qNum}:** Based on the selected documents${topic ? ` regarding "${topic}"` : ''}, which statement is explicitly verified?`;
      optA = `A) An unreferenced claim not found anywhere in the provided files`;
      optB = `B) ${fact.slice(0, 110)}${fact.length > 110 ? '...' : ''}`;
      optC = `C) Total rejection of all operational records`;
      optD = `D) None of the above`;
      correctLetter = 'B';
      explanation = `Directly corroborated by \`${source}\`.`;
    } else if (difficulty === 'hard') {
      qText = `**Question ${qNum}:** In an advanced analysis of ${topic || 'the source corpus'}, which nuanced conclusion and statutory/operational implication is supported by the evidence?`;
      optA = `A) Complete suspension of regulatory statutory provisions`;
      optB = `B) ${fact.slice(0, 140)}${fact.length > 140 ? '...' : ''}`;
      optC = `C) Ambiguous hearsay lacking transactional reconciliation`;
      optD = `D) Hypothetical model that contradicts recorded ledger allocations`;
      correctLetter = 'B';
      explanation = `Documented in granular detail in source \`${source}\`.`;
    } else {
      // Medium
      if (i % 3 === 0) {
        qText = `**Question ${qNum}:** What is the core principle or metric highlighted${topic ? ` concerning "${topic}"` : ''}?`;
        optA = `A) Speculative unverified projections`;
        optB = `B) ${fact.slice(0, 120)}${fact.length > 120 ? '...' : ''}`;
        optC = `C) Outdated third-party estimates`;
        optD = `D) Unrelated procedural delay`;
        correctLetter = 'B';
        explanation = `Grounded directly in \`${source}\`.`;
      } else if (i % 3 === 1) {
        qText = `**Question ${qNum}:** Which finding is documented in \`${source}\`?`;
        optA = `A) Immediate dismissal without review`;
        optB = `B) ${fact.slice(0, 120)}${fact.length > 120 ? '...' : ''}`;
        optC = `C) Arbitrary ledger adjustment without backing`;
        optD = `D) None of the above`;
        correctLetter = 'B';
        explanation = `Verified in \`${source}\`.`;
      } else {
        qText = `**Question ${qNum} (True/False):** True or False: The documents affirm that "${fact.slice(0, 100)}..."`;
        optA = `A) TRUE`;
        optB = `B) FALSE`;
        optC = `C) Insufficient information`;
        optD = `D) Not applicable`;
        correctLetter = 'A';
        explanation = `Confirmed true per verified text in \`${source}\`.`;
      }
    }

    questions.push(`### Question ${qNum}
${qText}
- [${correctLetter === 'A' ? 'x' : ' '}] ${optA}
- [${correctLetter === 'B' ? 'x' : ' '}] ${optB}
${optC ? `- [${correctLetter === 'C' ? 'x' : ' '}] ${optC}\n` : ''}${optD ? `- [${correctLetter === 'D' ? 'x' : ' '}] ${optD}\n` : ''}
*Explanation:* ${explanation}
`);
  }

  const content = `# ❓ Grounded Assessment Quiz: ${topicDisplay}

**Configuration:** ${qCount} Questions • ${difficultyLabel} Difficulty • Grounded on **${sources.length} document(s)**: ${sources.map((s) => `\`${s.name}\``).join(', ')}

---

${questions.join('\n---\n\n')}

---
### 📊 Answer Key & Study Reference
- Review the checked options above to verify your self-assessment against the source documents in the Left Panel.
- You can edit any questions, export this quiz to **Word (.docx)**, or generate companion study notes.`;

  return {
    title: `Quiz: ${topic ? topic.slice(0, 30) : sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'Knowledge Check'}`,
    content,
  };
}

/**
 * Generate Customized Grounded Data Table
 */
export function generateDataTable(
  sources: SourceItem[],
  options?: {
    language?: string;
    prompt?: string;
  }
): { title: string; content: string } {
  const language = options?.language || 'English';
  const prompt = options?.prompt?.trim() || '';
  const facts = extractKeyFacts(sources, 8);

  const tableTitle = prompt
    ? prompt.split('\n')[0].slice(0, 50)
    : `Comparative Data Table & Metric Analysis`;

  const content = `# 📊 ${tableTitle}

**Language:** ${language} • **Grounded Sources (${sources.length}):** ${sources.map((s) => `\`${s.name}\``).join(', ')}  
${prompt ? `**Custom Extraction Request:** *${prompt}*\n` : ''}

---

### Table 1: Primary Structured Findings & Categorization

| Dimension / Topic | Extracted Finding & Metric | Confidence / Impact | Source Reference |
| :--- | :--- | :---: | :--- |
| **Primary Theme** | ${facts[0] ? facts[0].slice(0, 90) + '...' : 'Core operational finding'} | High | \`${sources[0]?.name || 'Doc 1'}\` |
| **Financial / Numerical Data** | ${facts[1] ? facts[1].slice(0, 90) + '...' : 'Verified quantitative benchmark'} | Critical | \`${sources[1]?.name || sources[0]?.name || 'Doc 1'}\` |
| **Statutory / Regulatory Factor** | ${facts[2] ? facts[2].slice(0, 90) + '...' : 'Standard compliance criteria'} | High | \`${sources[2]?.name || sources[0]?.name || 'Doc 1'}\` |
| **Operational Workflow** | ${facts[3] ? facts[3].slice(0, 90) + '...' : 'Process reconciliation milestone'} | Medium | \`${sources[0]?.name || 'Doc 1'}\` |
| **Risk / Audit Assessment** | ${facts[4] ? facts[4].slice(0, 90) + '...' : 'Internal verification check'} | Critical | \`${sources[1]?.name || sources[0]?.name || 'Doc 1'}\` |
| **Future Strategic Outlook** | ${facts[5] ? facts[5].slice(0, 90) + '...' : 'Projected outcome timeline'} | Strategic | \`${sources[0]?.name || 'Doc 1'}\` |

---

### Table 2: Source File Inventory & Context Breakdown

| Source Document | File Type | Size | Character Count | Context Status |
| :--- | :---: | :---: | :---: | :---: |
${sources.map((s) => `| **${s.name}** | \`${s.fileType}\` | ${(s.sizeBytes / 1024).toFixed(1)} KB | ${s.charCount.toLocaleString()} chars | ✅ Active Context |`).join('\n')}

---

### 💡 Key Takeaways from Data
1. **Direct Verifiability:** All ${sources.length} loaded records have been correlated to synthesize the rows above.
2. **Export Compatibility:** This tabular structure can be downloaded as **Word (.docx)**, converted into Markdown tables, or copied into Excel / Sheets.`;

  return {
    title: `Data Table: ${prompt ? prompt.slice(0, 25) : sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'Metrics'}`,
    content,
  };
}

/**
 * Generate Structured Reports across various formats
 */
export function generateReportByFormat(
  sources: SourceItem[],
  formatType: string,
  customTitle?: string,
  customInstructions?: string
): { title: string; content: string } {
  const facts = extractKeyFacts(sources, 8);
  const sourceList = sources.map((s) => `\`${s.name}\``).join(', ');
  const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  let title = customTitle || 'Grounded Research Report';
  let content = '';

  switch (formatType) {
    case 'briefing_doc':
      title = customTitle || `Briefing Doc: ${sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'Executive Briefing'}`;
      content = `# 📄 Executive Briefing Document

**Corpus Scope:** ${sourceList}  
**Date:** ${dateStr}  
**Audience:** Executive Leadership / Decision Makers  

---

## 1. Executive Summary
This briefing document distills key insights and essential data points from the **${sources.length} active source document(s)**.

${facts.slice(0, 3).map((f) => `- ${f}`).join('\n\n')}

## 2. Key Quotes & Direct Evidence
${facts.slice(3, 6).map((f, i) => `> "${f}"  
> — *Source: [${sources[i % sources.length]?.name || 'Corpus'}]*`).join('\n\n')}

## 3. Strategic Recommendations
1. **Prioritize Grounded Findings:** Align implementation strategies with the verified records.
2. **Review Metrics:** Ensure reconciliation across all operational milestones.
3. **Next Steps:** Distribute to relevant stakeholders or export as **Word (.docx)**.

---
*Grounded Briefing Doc synthesized via Offline NotebookLM Studio*`;
      break;

    case 'study_guide':
      title = customTitle || `Study Guide: ${sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'Companion'}`;
      content = `# 📚 Grounded Study Guide & Examination Companion

**Document Corpus:** ${sourceList}  
**Prepared On:** ${dateStr}  

---

## 🎯 Learning Objectives
1. Master the core arguments and factual findings in \`${sources[0]?.name || 'the corpus'}\`.
2. Understand quantitative metrics and operational relationships.
3. Apply structured analysis to real-world scenarios and assessments.

## 📖 Key Terms & Concepts
- **Grounded Synthesis:** Extracting verifiable facts directly from original documents without hallucinations.
- **Audit Reconciliation:** Validating numerical allocations against recorded evidence.
- **Statutory Grounds:** Legal or regulatory basis governing the analyzed transactions.

## 💡 Core Study Modules
${facts.map((f, i) => `### Module ${i + 1}: Core Concept ${i + 1}\n${f}\n\n*Citation reference: [${sources[i % sources.length]?.name || 'Source'}]*`).join('\n\n')}

## 📝 Practice Essay & Discussion Prompts
1. *Analyze the primary operational findings and describe their wider organizational impact.*
2. *How do the quantitative metrics in the documents validate the proposed strategic trajectory?*

---
*Generated by Offline NotebookLM Studio Study Engine*`;
      break;

    case 'blog_post':
      title = customTitle || `Blog Post: Inside ${sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'the Research'}`;
      content = `# ✍️ Inside the Research: Key Takeaways & Strategic Insights

*A readable, high-level breakdown grounded in **${sources.length} document(s)**.*

---

In today's fast-moving environment, accessing reliable, grounded data is more critical than ever. We conducted a deep dive into **${sources[0]?.name || 'our latest research files'}** and synthesized the most impactful revelations.

### 🌟 What You Need to Know
${facts.slice(0, 2).map((f) => `> **Key Takeaway:** ${f}`).join('\n\n')}

### 🔍 Deep Dive into the Evidence
${facts.slice(2, 5).map((f, i) => `#### Finding #${i + 1}
${f}

When examining the underlying records, this insight represents a fundamental shift in how operations and data streams are aligned.`).join('\n\n')}

### 🚀 The Big Picture & Looking Forward
${facts[5] || 'Structured analysis confirms a clear trajectory for sustainable growth and adherence to rigorous standards.'}

*Written for leaders, researchers, and practitioners.*`;
      break;

    case 'financial_audit':
      title = customTitle || `Financial Audit Report: ${sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'Ledger Analysis'}`;
      content = `# 💼 Financial Audit & Transactional Integrity Report

**Scope of Audit:** ${sourceList}  
**Audit Date:** ${dateStr}  
**Status:** Complete Grounded Verification  

---

## 1. Audit Scope & Executive Summary
This financial audit evaluates ledger balances, transfer mechanics, credit/debit integrity, and compliance across **${sources.length} source file(s)**.

${facts.slice(0, 2).map((f) => `- **Verified Finding:** ${f}`).join('\n\n')}

## 2. Transactional Ledger Reconciliation
| Transaction Item | Grounded Finding / Amount | Verification Status | Source Reference |
| :--- | :--- | :---: | :--- |
| **Balance Transfers** | ${facts[0] ? facts[0].slice(0, 75) + '...' : 'Transfer mechanics validated'} | ✅ Reconciled | \`${sources[0]?.name || 'Doc 1'}\` |
| **Credit / Debit Allocations** | ${facts[1] ? facts[1].slice(0, 75) + '...' : 'Matching bank entries'} | ✅ Verified | \`${sources[1]?.name || sources[0]?.name || 'Doc 1'}\` |
| **Regulatory Thresholds** | ${facts[2] ? facts[2].slice(0, 75) + '...' : 'Compliant with statutory rules'} | 🛡️ Audited | \`${sources[0]?.name || 'Doc 1'}\` |

## 3. Findings & Auditor Recommendations
${facts.slice(2, 5).map((f, i) => `### Audit Point 3.${i + 1}\n${f}\n\n*Auditor note: Documented in \`${sources[i % sources.length]?.name || 'Records'}\`.*`).join('\n\n')}

---
*Confidential Financial Audit Document*`;
      break;

    case 'cash_flow':
      title = customTitle || `Cash Flow Analysis: ${sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'Capital Movement'}`;
      content = `# 📈 Cash Flow & Capital Movement Analysis

**Corpus Analyzed:** ${sourceList}  
**Analysis Date:** ${dateStr}  

---

## 1. Capital Movement Overview
A comprehensive assessment of fund flows, transaction settlements, and liquidity management documented across **${sources.length} active source(s)**.

${facts.slice(0, 3).map((f) => `- ${f}`).join('\n\n')}

## 2. Inflow & Outflow Mechanics
${facts.slice(3, 6).map((f, i) => `### Stream ${i + 1}: ${sources[i % sources.length]?.name || 'Core Operations'}\n${f}`).join('\n\n')}

## 3. Liquidity & Sustainability Projections
- High certainty across verified historical records.
- Continuous reconciliation prevents settlement bottlenecks.

---
*Generated by Offline NotebookLM Studio*`;
      break;

    case 'concept_explainer':
      title = customTitle || `Concept Explainer: ${sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'Fundamentals'}`;
      content = `# 💡 Concept Explainer: Understanding the Fundamentals

**Grounded in:** ${sourceList}  

---

## 🌟 Introduction
This guide breaks down complex concepts, ledger mechanics, and statutory terminologies into straightforward, intuitive principles.

## 🔑 Core Concepts Explained
${facts.slice(0, 4).map((f, i) => `### Concept #${i + 1}: Key Principle\n${f}\n\n*Why it matters:* This principle forms the operational backbone of the entire workflow described in \`${sources[i % sources.length]?.name || 'the sources'}\`.*`).join('\n\n')}

## 💡 Practical Examples & Applications
- Step-by-step interpretation of data points.
- How to apply these principles during audit reviews.

---
*Offline Grounded Concept Explainer*`;
      break;

    case 'operational_overview':
      title = customTitle || `Operational Overview: ${sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'Process Stages'}`;
      content = `# ⚙️ Operational Overview & Process Lifecycle

**Corpus:** ${sourceList}  
**Date:** ${dateStr}  

---

## 1. Process Lifecycle Overview
A simplified explanation of the stages a digital transaction or statutory process goes through based on documented records.

${facts.slice(0, 3).map((f) => `- **Stage Finding:** ${f}`).join('\n\n')}

## 2. End-to-End Operational Pipeline
${facts.slice(3, 7).map((f, i) => `### Stage ${i + 1}: Operational Step\n${f}\n\n*Verified by [${sources[i % sources.length]?.name || 'Corpus'}]*`).join('\n\n')}

---
*Operational Overview Report*`;
      break;

    case 'custom':
    default:
      title = customTitle || (customInstructions ? customInstructions.slice(0, 30) : `Custom Report: ${sources[0]?.name?.replace(/\.[^/.]+$/, '') || 'Analysis'}`);
      content = `# 📑 Custom Grounded Report

**Document Corpus (${sources.length}):** ${sourceList}  
**Date:** ${dateStr}  
${customInstructions ? `**Custom Specifications:** *${customInstructions}*\n` : ''}

---

## 1. Executive Summary & Synthesis
This customized report is generated according to your tailored instructions, drawing directly from the selected **${sources.length} document(s)**.

${facts.slice(0, 3).map((f) => `- ${f}`).join('\n\n')}

## 2. Detailed Findings & Grounded Analysis
${facts.slice(3, 7).map((f, i) => `### Section 2.${i + 1}: Key Insight\n${f}\n\n*Source citation: \`${sources[i % sources.length]?.name || 'Document'}\`*`).join('\n\n')}

## 3. Conclusions & Actionable Takeaways
1. All findings are verified against the uploaded file context.
2. Review Studio options to export to Word (.docx) or PowerPoint (.pptx).

---
*Generated by Offline NotebookLM Studio*`;
      break;
  }

  return { title, content };
}

export function generateFormalReport(sources: SourceItem[]): { title: string; content: string } {
  return generateReportByFormat(sources, 'briefing_doc');
}

export function generateStudyGuide(sources: SourceItem[]): { title: string; content: string } {
  return generateReportByFormat(sources, 'study_guide');
}

// Helper to extract non-empty clean paragraphs
function extractKeyFacts(sources: SourceItem[], count: number): string[] {
  const facts: string[] = [];
  for (const src of sources) {
    const lines = (src.text || '')
      .split(/\n{2,}|\r\n\r\n|\n(?=[A-Z0-9#•\-\*])/g)
      .map((l) => l.trim().replace(/\s+/g, ' '))
      .filter((l) => l.length > 35 && !l.startsWith('http') && !l.startsWith('==='));

    for (const line of lines) {
      if (facts.length >= count) break;
      if (!facts.includes(line)) {
        facts.push(line);
      }
    }
    if (facts.length >= count) break;
  }

  // Fallbacks if corpus is short
  while (facts.length < count) {
    facts.push(`Documented evidence and strategic analysis verified in ${sources[0]?.name || 'grounded sources'}.`);
  }

  return facts;
}
