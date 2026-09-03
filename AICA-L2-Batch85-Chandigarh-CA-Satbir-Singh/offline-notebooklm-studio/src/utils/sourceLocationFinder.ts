import { SourceItem } from '../types';

export interface SourceLocationInfo {
  pageNumber: number | string;
  sectionTitle: string;
  locationLabel: string;
  snippet: string;
  matchedKeywords: string[];
  charOffset: number;
  lineNumber: number;
  totalLength: number;
}

export interface DocumentPassage {
  pageNumber: number | string;
  sectionTitle: string;
  text: string;
  charOffset: number;
  lineNumber: number;
}

/**
 * Parses any source text into pages, sections, and searchable passages.
 */
export function parseDocumentPassages(source: SourceItem): DocumentPassage[] {
  const rawText = source.text || '';
  if (!rawText.trim()) return [];

  const lines = rawText.split(/\r?\n/);
  const passages: DocumentPassage[] = [];

  let currentPage: number | string = 1;
  let currentSection = source.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
  let runningCharOffset = 0;

  let currentBlockLines: string[] = [];
  let blockStartLine = 1;
  let blockStartOffset = 0;

  const flushBlock = (endLineIdx: number) => {
    const blockText = currentBlockLines.join('\n').trim();
    if (blockText.length > 0) {
      // If block is very long (over 600 chars), split into sentence chunks for granular pinpointing
      if (blockText.length > 600) {
        const sentences = blockText.split(/(?<=[.?!;:])\s+/);
        let sentenceOffset = blockStartOffset;
        for (const sent of sentences) {
          const trimmedSent = sent.trim();
          if (trimmedSent.length > 15) {
            passages.push({
              pageNumber: currentPage,
              sectionTitle: currentSection,
              text: trimmedSent,
              charOffset: sentenceOffset,
              lineNumber: blockStartLine,
            });
          }
          sentenceOffset += sent.length + 1;
        }
      } else {
        passages.push({
          pageNumber: currentPage,
          sectionTitle: currentSection,
          text: blockText,
          charOffset: blockStartOffset,
          lineNumber: blockStartLine,
        });
      }
    }
    currentBlockLines = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    const lineOffset = runningCharOffset;
    runningCharOffset += line.length + 1; // +1 for newline

    // Check for explicit page markers
    const pageMatch =
      trimmed.match(/^---\s*Page\s*(\d+)\s*---/i) ||
      trimmed.match(/^Page\s*(\d+)(?:\s*of\s*\d+)?$/i) ||
      trimmed.match(/\[Page\s*(\d+)\]/i);

    if (pageMatch) {
      flushBlock(i);
      currentPage = parseInt(pageMatch[1], 10);
      blockStartLine = i + 1;
      blockStartOffset = lineOffset;
      continue;
    }

    // Check for Excel sheet markers
    const sheetMatch = trimmed.match(/^###\s*Sheet:\s*(.+)$/i);
    if (sheetMatch) {
      flushBlock(i);
      currentPage = `Sheet: ${sheetMatch[1].trim()}`;
      blockStartLine = i + 1;
      blockStartOffset = lineOffset;
      continue;
    }

    // Check for section headings
    if (
      trimmed.startsWith('#') ||
      /^(?:PART\s+[I|V|X|0-9]+|Section\s+[0-9A-Z]+|Ground\s+\d+|Clause\s+\d+|Chapter\s+\d+|Taxpayer Profile|Summary of|Background|Objective|Conclusion|Table\s+\d+)/i.test(
        trimmed
      )
    ) {
      const cleanHeading = trimmed.replace(/^[#\s*\-•:]+/, '').trim();
      if (cleanHeading.length > 3 && cleanHeading.length < 80) {
        currentSection = cleanHeading;
      }
    }

    // Empty line indicates paragraph boundary
    if (trimmed === '') {
      flushBlock(i);
      blockStartLine = i + 2;
      blockStartOffset = runningCharOffset;
    } else {
      if (currentBlockLines.length === 0) {
        blockStartLine = i + 1;
        blockStartOffset = lineOffset;
      }
      currentBlockLines.push(line);
    }
  }

  flushBlock(lines.length);

  // If no explicit page markers existed and document is large, assign virtual page numbers
  const hasExplicitPages = rawText.includes('--- Page') || rawText.includes('### Sheet:');
  if (!hasExplicitPages && passages.length > 0) {
    const charsPerPage = 1800;
    for (const p of passages) {
      p.pageNumber = Math.max(1, Math.floor(p.charOffset / charsPerPage) + 1);
    }
  }

  return passages;
}

/**
 * Finds the exact location, page, section heading, and relevant snippet
 * within a source document based on the claim context / citation context.
 */
export function findExactSourceLocation(
  source: SourceItem,
  claimContext?: string
): SourceLocationInfo {
  const rawText = source.text || '';
  if (!rawText.trim()) {
    return {
      pageNumber: 1,
      sectionTitle: source.name,
      locationLabel: `Page 1 • ${source.name}`,
      snippet: 'No text extracted for this document.',
      matchedKeywords: [],
      charOffset: 0,
      lineNumber: 1,
      totalLength: 0,
    };
  }

  // 1. Clean claimContext and extract tokens
  const cleanContext = (claimContext || '')
    .replace(/\[(?:Source\s*)?\d+(?:\s*,\s*(?:Source\s*)?\d+)*\]/g, '')
    .replace(/[#*`_~|•]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  // If claim context is very short or empty, provide first clean paragraph
  if (cleanContext.length < 5) {
    const passages = parseDocumentPassages(source);
    const firstGood = passages.find((p) => p.text.length > 30 && !p.text.startsWith('FORM NO')) || passages[0];
    return {
      pageNumber: firstGood?.pageNumber || 1,
      sectionTitle: firstGood?.sectionTitle || source.name,
      locationLabel: `${typeof firstGood?.pageNumber === 'number' ? `Page ${firstGood.pageNumber}` : firstGood?.pageNumber || 'Page 1'}`,
      snippet: (firstGood?.text || rawText.slice(0, 200)).slice(0, 280),
      matchedKeywords: [],
      charOffset: firstGood?.charOffset || 0,
      lineNumber: firstGood?.lineNumber || 1,
      totalLength: rawText.length,
    };
  }

  // Extract alphanumeric identifiers, currency amounts, section names, uppercase codes
  const specificTokens = Array.from(
    cleanContext.matchAll(/\b(?:[A-Z0-9]{4,15}|(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?|[0-9]{1,2}[A-Z]{1,3}|FY\s*\d{4}-\d{2}|AY\s*\d{4}-\d{2}|Section\s+\d+[A-Z]*|194[A-Z]|203[A-Z]*|44AD[A-Z]*)\b/gi)
  ).map((m) => m[0]);

  // Extract multi-word phrases (3 to 6 words)
  const wordsList = cleanContext
    .split(/\s+/)
    .map((w) => w.replace(/^[^\w\d]+|[^\w\d]+$/g, '').trim())
    .filter((w) => w.length > 0);

  const phrases: string[] = [];
  for (let len = 4; len >= 2; len--) {
    for (let i = 0; i <= wordsList.length - len; i++) {
      const phrase = wordsList.slice(i, i + len).join(' ');
      if (phrase.length > 10) {
        phrases.push(phrase.toLowerCase());
      }
    }
  }

  // Stop words to filter out
  const stopWords = new Set([
    'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'were',
    'been', 'their', 'which', 'about', 'across', 'total', 'under', 'also',
    'over', 'each', 'such', 'into', 'than', 'them', 'these', 'those', 'where',
    'will', 'would', 'should', 'could', 'shall', 'been', 'being', 'having',
    'regulatory', 'provision', 'substantive', 'operating', 'summary', 'details',
    'amount', 'number', 'name', 'item', 'points', 'note'
  ]);

  const meaningfulWords = wordsList
    .map((w) => w.toLowerCase())
    .filter((w) => w.length > 2 && !stopWords.has(w));

  // 2. Parse all passages from the source document
  const passages = parseDocumentPassages(source);
  if (passages.length === 0) {
    return {
      pageNumber: 1,
      sectionTitle: source.name,
      locationLabel: `Page 1 • ${source.name}`,
      snippet: rawText.slice(0, 240),
      matchedKeywords: [],
      charOffset: 0,
      lineNumber: 1,
      totalLength: rawText.length,
    };
  }

  // 3. Score every passage across all pages
  interface ScoredPassage {
    passage: DocumentPassage;
    score: number;
    matchedKeywords: string[];
    matchedPhrases: string[];
  }

  const scoredPassages: ScoredPassage[] = [];

  for (const p of passages) {
    const pText = p.text;
    const pTextLower = pText.toLowerCase();
    let score = 0;
    const matchedKw: string[] = [];
    const matchedPhr: string[] = [];

    // Exact phrase matches (highest priority)
    for (const ph of phrases) {
      if (pTextLower.includes(ph)) {
        score += 80 + ph.length * 2;
        if (!matchedPhr.includes(ph)) matchedPhr.push(ph);
      }
    }

    // Specific codes and numbers (high priority)
    for (const token of specificTokens) {
      if (pText.includes(token) || pTextLower.includes(token.toLowerCase())) {
        score += 60;
        if (!matchedKw.includes(token)) matchedKw.push(token);
      }
    }

    // Meaningful distinct words
    for (const w of meaningfulWords) {
      if (pTextLower.includes(w)) {
        score += 12;
        if (!matchedKw.includes(w)) matchedKw.push(w);
      }
    }

    if (score > 0) {
      scoredPassages.push({
        passage: p,
        score,
        matchedKeywords: Array.from(new Set([...matchedKw, ...matchedPhr])),
        matchedPhrases: matchedPhr,
      });
    }
  }

  // Sort by highest matching score
  scoredPassages.sort((a, b) => b.score - a.score);

  // Pick top scoring passage or best fallback
  const winner = scoredPassages[0];
  const bestPassage = winner && winner.score > 15
    ? winner.passage
    : passages.find((p) => p.text.length > 40 && !p.text.startsWith('FORM NO') && !p.text.startsWith('===') && !p.text.startsWith('---')) ||
      passages[0];

  const matchedKeywords = winner ? winner.matchedKeywords : [];

  // Format snippet
  let displaySnippet = bestPassage.text.trim();
  displaySnippet = displaySnippet
    .replace(/^---\s*Page\s*\d+\s*---\s*/i, '')
    .replace(/^###\s*Sheet:[^\n]+\n/i, '')
    .trim();

  if (displaySnippet.length > 360) {
    // Find best sentence inside passage if too long
    const sentMatch = displaySnippet.split(/(?<=[.?!;])\s+/);
    const topSent = sentMatch.find((s) => meaningfulWords.some((w) => s.toLowerCase().includes(w)));
    if (topSent && topSent.length > 30) {
      displaySnippet = topSent.trim();
    } else {
      displaySnippet = displaySnippet.slice(0, 320) + '...';
    }
  }

  const pageNum = bestPassage.pageNumber;
  const pageLabel = typeof pageNum === 'number' ? `Page ${pageNum}` : String(pageNum);
  const sectionLabel =
    bestPassage.sectionTitle && bestPassage.sectionTitle !== source.name
      ? bestPassage.sectionTitle.slice(0, 45)
      : '';

  const locationLabel = sectionLabel
    ? `${pageLabel} • ${sectionLabel}`
    : `${pageLabel} • Line ${bestPassage.lineNumber}`;

  return {
    pageNumber: pageNum,
    sectionTitle: bestPassage.sectionTitle,
    locationLabel,
    snippet: displaySnippet,
    matchedKeywords,
    charOffset: bestPassage.charOffset,
    lineNumber: bestPassage.lineNumber,
    totalLength: rawText.length,
  };
}
