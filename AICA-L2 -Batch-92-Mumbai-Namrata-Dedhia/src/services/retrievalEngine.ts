import { FAQRecord } from '../types/advisory';
import { INITIAL_KNOWLEDGE_BASE } from '../data/knowledgeBase';

export interface RetrievalResult {
  matches: FAQRecord[];
  confidence: number;
  detectedTopic: string;
  isAmbiguous: boolean;
  missingFacts: string[];
  isPromptInjection: boolean;
  isOutOfScope: boolean;
}

const INJECTION_PATTERNS = [
  /ignore\s+(previous|prior|above|all)\s+(instructions|rules|prompts|guidelines)/i,
  /disregard\s+(the\s+)?(database|rules|guidelines|instructions)/i,
  /forget\s+(your\s+)?(rules|instructions|knowledge\s*base)/i,
  /you\s+are\s+now\s+(unrestricted|in\s+developer\s+mode|dan|jailbroken)/i,
  /tell\s+me\s+what\s+the\s+tax\s+law\s+really\s+is\s+without\s+the\s+rules/i,
  /system\s*prompt\s*override/i,
  /bypass\s+(safety|guardrails|database)/i
];

const TOPIC_SIGNATURES: Record<string, string[]> = {
  'Repatriation Limits': ['repatriat', 'remit', 'send money abroad', 'transfer money out', 'nro to nre', '1 million', 'usd 1m', '15ca', '15cb', 'outward remittance', 'fema remittance', 'transfer', 'how much can i transfer', 'sold my flat'],
  'TDS on Sale of Indian Property': ['tds on property', 'tds on flat', 'property sale tds', '195', 'section 195', '197', 'lower tds', 'form 13', '12.5%', 'capital gains tds', 'buyer deduct', 'traces', 'tan', 'sold flat', 'sold my flat'],
  'PAN/Aadhaar Linking': ['aadhaar', 'pan linking', 'inoperative pan', 'link pan', 'notification 37/2017', '139aa', 'exempt aadhaar', 'pan aadhaar'],
  'DTAA Relief and Conditions': ['dtaa', 'double tax', 'trc', 'tax residency certificate', 'form 10f', 'treaty', 'foreign tax credit', 'ftc', 'form 67', 'section 90'],
  'FEMA Bank Account Conversion': ['bank account', 'convert account', 'nro account', 'nre account', 'fcnr', 'savings account', 'move abroad', 'became nri', 'penalty resident account', 'redesignat'],
  'FEMA Immovable Property': ['buy property', 'purchase flat', 'agricultural land', 'farm house', 'plantation', 'commercial property', 'can nri buy', 'fema ndi', 'rule 24', 'oci property'],
  'Residential Status': ['residential status', '182 days', '120 days', '60 days', 'deemed resident', '6(1a)', 'rnor', 'ror', 'stay in india', 'tax resident', 'day count'],
  'Foreign Assets & Accounts': ['schedule fa', 'foreign asset', 'foreign bank', 'black money act', 'disclose overseas', 'foreign shares', 'esop foreign'],
  'Foreign Income Taxability': ['foreign income', 'foreign salary', 'taxable in india', 'salary in dubai', 'us salary', 'section 5', 'overseas income', 'accrue outside india']
};

export class RetrievalEngine {
  private knowledgeBase: FAQRecord[];

  constructor(customKB?: FAQRecord[]) {
    this.knowledgeBase = customKB || INITIAL_KNOWLEDGE_BASE;
  }

  public setKnowledgeBase(kb: FAQRecord[]) {
    this.knowledgeBase = kb;
  }

  public getKnowledgeBase(): FAQRecord[] {
    return this.knowledgeBase;
  }

  public detectPromptInjection(query: string): boolean {
    return INJECTION_PATTERNS.some((pattern) => pattern.test(query));
  }

  private calculateCosineSimilarity(str1: string, str2: string): number {
    const stopWords = new Set(['is', 'a', 'the', 'am', 'i', 'to', 'for', 'in', 'of', 'on', 'at', 'what', 'how', 'check', 'if', 'my', 'are', 'you', 'we', 'they', 'he', 'she', 'it', 'and', 'or', 'but', 'can', 'do', 'does', 'did', 'about', 'with', 'by']);
    
    const getTokens = (text: string) => 
      text.toLowerCase()
        .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, '')
        .split(/\s+/)
        .filter(t => t.length > 2 && !stopWords.has(t));

    const tokens1 = getTokens(str1);
    const tokens2 = getTokens(str2);

    if (tokens1.length === 0 || tokens2.length === 0) return 0;

    const map1: Record<string, number> = {};
    const map2: Record<string, number> = {};

    tokens1.forEach(t => map1[t] = (map1[t] || 0) + 1);
    tokens2.forEach(t => map2[t] = (map2[t] || 0) + 1);

    let dotProduct = 0;
    const allWords = new Set([...Object.keys(map1), ...Object.keys(map2)]);
    
    for (const word of allWords) {
      if (map1[word] && map2[word]) {
        dotProduct += map1[word] * map2[word];
      }
    }

    const mag1 = Math.sqrt(Object.values(map1).reduce((sum, val) => sum + val * val, 0));
    const mag2 = Math.sqrt(Object.values(map2).reduce((sum, val) => sum + val * val, 0));

    if (mag1 === 0 || mag2 === 0) return 0;

    return dotProduct / (mag1 * mag2);
  }

  private calculateTrigramSimilarity(str1: string, str2: string): number {
    const getTrigrams = (text: string) => {
      const clean = '  ' + text.toLowerCase().replace(/[^a-z0-9]/g, '') + '  ';
      const trigrams: string[] = [];
      for (let i = 0; i < clean.length - 2; i++) {
        trigrams.push(clean.slice(i, i + 3));
      }
      return trigrams;
    };

    const trigrams1 = getTrigrams(str1);
    const trigrams2 = getTrigrams(str2);

    if (trigrams1.length === 0 || trigrams2.length === 0) return 0;

    const set1 = new Set(trigrams1);
    const set2 = new Set(trigrams2);

    let intersectionCount = 0;
    for (const tri of set1) {
      if (set2.has(tri)) {
        intersectionCount++;
      }
    }

    const unionSize = new Set([...trigrams1, ...trigrams2]).size;
    return intersectionCount / unionSize;
  }

  private calculateLevenshteinSimilarity(str1: string, str2: string): number {
    const s1 = str1.toLowerCase().trim();
    const s2 = str2.toLowerCase().trim();
    if (s1 === s2) return 1.0;
    if (!s1.length || !s2.length) return 0.0;

    const len1 = s1.length;
    const len2 = s2.length;
    const track = Array(len2 + 1).fill(null).map(() => Array(len1 + 1).fill(null));

    for (let i = 0; i <= len1; i += 1) track[0][i] = i;
    for (let j = 0; j <= len2; j += 1) track[j][0] = j;

    for (let j = 1; j <= len2; j += 1) {
      for (let i = 1; i <= len1; i += 1) {
        const indicator = s1[i - 1] === s2[j - 1] ? 0 : 1;
        track[j][i] = Math.min(
          track[j][i - 1] + 1,
          track[j - 1][i] + 1,
          track[j - 1][i - 1] + indicator
        );
      }
    }

    const distance = track[len2][len1];
    const maxLen = Math.max(len1, len2);
    return Math.max(0, (maxLen - distance) / maxLen);
  }

  private calculateTokenJaccard(str1: string, str2: string): number {
    const stopWords = new Set(['is', 'a', 'the', 'am', 'i', 'to', 'for', 'in', 'of', 'on', 'at', 'what', 'how', 'check', 'if', 'my', 'are', 'you', 'we', 'they', 'he', 'she', 'it', 'and', 'or', 'but', 'can', 'do', 'does', 'did', 'about', 'with', 'by']);
    const getTokens = (text: string) =>
      text.toLowerCase()
        .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, '')
        .split(/\s+/)
        .filter(t => t.length > 1 && !stopWords.has(t));

    const set1 = new Set(getTokens(str1));
    const set2 = new Set(getTokens(str2));

    if (set1.size === 0 || set2.size === 0) return 0;

    let intersection = 0;
    for (const token of set1) {
      if (set2.has(token)) intersection++;
    }

    const union = new Set([...set1, ...set2]).size;
    return intersection / union;
  }

  public calculateFuzzySimilarity(query: string, targetText: string): number {
    if (!query || !targetText) return 0;
    const q = query.toLowerCase().trim();
    const t = targetText.toLowerCase().trim();

    if (q === t) return 100;
    if (t.includes(q) || q.includes(t)) {
      const minLen = Math.min(q.length, t.length);
      const maxLen = Math.max(q.length, t.length);
      const ratio = minLen / maxLen;
      if (ratio >= 0.5) return Math.round(Math.max(85, ratio * 100));
    }

    const stopWords = new Set(['is', 'a', 'the', 'am', 'i', 'to', 'for', 'in', 'of', 'on', 'at', 'what', 'how', 'check', 'if', 'my', 'are', 'you', 'we', 'they', 'he', 'she', 'it', 'and', 'or', 'but', 'can', 'do', 'does', 'did', 'about', 'with', 'by']);
    const getCleanTokens = (str: string) => new Set(str.toLowerCase().replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter(x => x.length > 2 && !stopWords.has(x)));

    const qTokens = getCleanTokens(q);
    const tTokens = getCleanTokens(t);

    let synonymMatches = 0;
    for (const tok of qTokens) {
      if (tTokens.has(tok)) {
        synonymMatches++;
      } else if (
        (tok === 'flat' && (tTokens.has('property') || tTokens.has('house'))) ||
        (tok === 'transfer' && (tTokens.has('repatriate') || tTokens.has('remit') || tTokens.has('remittance'))) ||
        (tok === 'sold' && (tTokens.has('sale') || tTokens.has('selling'))) ||
        (tok === 'buy' && (tTokens.has('purchase') || tTokens.has('acquire')))
      ) {
        synonymMatches += 0.9;
      }
    }

    const tokenOverlapScore = qTokens.size > 0 ? (synonymMatches / Math.min(qTokens.size, Math.max(1, tTokens.size))) : 0;

    const cosine = this.calculateCosineSimilarity(q, t);
    const trigram = this.calculateTrigramSimilarity(q, t);
    const jaccard = this.calculateTokenJaccard(q, t);
    const lev = this.calculateLevenshteinSimilarity(q, t);

    // Ensemble combination
    const ensemble = (cosine * 0.35) + (tokenOverlapScore * 0.35) + (jaccard * 0.15) + (trigram * 0.10) + (lev * 0.05);
    const maxVal = Math.max(ensemble, cosine, jaccard, tokenOverlapScore * 0.95);
    return Math.round(maxVal * 100);
  }

  public search(query: string): RetrievalResult {
    const isInjection = this.detectPromptInjection(query);
    if (isInjection) {
      return {
        matches: [],
        confidence: 0,
        detectedTopic: 'Security / Prompt Injection Attempt',
        isAmbiguous: false,
        missingFacts: [],
        isPromptInjection: true,
        isOutOfScope: true
      };
    }

    const cleanQuery = query.toLowerCase().trim();

    // 1. Detect Topic
    let detectedTopic = 'Unclassified';
    let highestTopicScore = 0;

    for (const [topic, keywords] of Object.entries(TOPIC_SIGNATURES)) {
      let topicMatches = 0;
      for (const kw of keywords) {
        if (cleanQuery.includes(kw.toLowerCase())) {
          topicMatches += 2;
        }
      }
      if (topicMatches > highestTopicScore) {
        highestTopicScore = topicMatches;
        detectedTopic = topic;
      }
    }

    // 2. Score KB Records with strict similarity metrics
    const scoredRecords = this.knowledgeBase.map((record) => {
      let bestSimilarityScore = 0;
      const candidates = [
        record.user_question,
        ...record.question_variations,
        record.keywords.join(' '),
        record.category
      ];

      for (const candidate of candidates) {
        if (!candidate) continue;
        const currentScore = this.calculateFuzzySimilarity(cleanQuery, candidate);
        if (currentScore > bestSimilarityScore) {
          bestSimilarityScore = currentScore;
        }
      }

      // Keyword boost if query contains explicit domain key terms
      let keywordBoost = 0;
      for (const kw of record.keywords) {
        if (cleanQuery.includes(kw.toLowerCase())) {
          keywordBoost = 15;
          break;
        }
      }

      // Category alignment boost
      const categoryBoost = (detectedTopic !== 'Unclassified' && record.category.toLowerCase().includes(detectedTopic.toLowerCase())) ? 15 : 0;

      // Section or statutory reference boost
      const sectionBoost = (record.section_rule_regulation && cleanQuery.includes(record.section_rule_regulation.toLowerCase())) ? 20 : 0;

      const finalScore = Math.min(100, bestSimilarityScore + keywordBoost + categoryBoost + sectionBoost);

      return { record, score: finalScore, rawSimilarity: bestSimilarityScore };
    });

    scoredRecords.sort((a, b) => b.score - a.score);

    // Strictly enforce the 70% (0.70) similarity threshold requirement
    const SIMILARITY_THRESHOLD = 70;
    const topMatches = scoredRecords.filter((item) => item.score >= SIMILARITY_THRESHOLD).map((item) => item.record);
    const topScore = scoredRecords[0]?.score || 0;

    const normalizedConfidence = topScore >= SIMILARITY_THRESHOLD ? Math.min(1.0, Math.round((topScore / 100) * 100) / 100) : 0;
    const isOutOfScope = topMatches.length === 0 || normalizedConfidence < 0.70;

    const primaryMatch = topMatches[0];
    const { isAmbiguous, missingFacts } = this.analyzeFactSufficiency(cleanQuery, primaryMatch);

    return {
      matches: topMatches.slice(0, 3),
      confidence: isOutOfScope ? 0 : normalizedConfidence,
      detectedTopic: detectedTopic !== 'Unclassified' ? detectedTopic : (primaryMatch?.category || 'General NRI Query'),
      isAmbiguous,
      missingFacts,
      isPromptInjection: false,
      isOutOfScope
    };
  }

  private analyzeFactSufficiency(query: string, primaryMatch?: FAQRecord): { isAmbiguous: boolean; missingFacts: string[] } {
    if (!primaryMatch) return { isAmbiguous: false, missingFacts: [] };

    const missingFacts: string[] = [];

    // Property sale questions
    if (primaryMatch.category.includes('TDS') || primaryMatch.category.includes('Repatriation Limits')) {
      const mentionsHoldingPeriod = query.includes('holding') || query.includes('years') || query.includes('months') || query.includes('bought in') || query.includes('inherited');
      const mentionsAccountType = query.includes('nro') || query.includes('nre') || query.includes('fcnr') || query.includes('foreign currency');
      
      if (!mentionsHoldingPeriod && (query.includes('property') || query.includes('flat') || query.includes('house'))) {
        missingFacts.push('Holding period of property (> 24 months for LTCG vs ≤ 24 months for STCG)');
      }
      if (!mentionsAccountType && (query.includes('repatriat') || query.includes('transfer') || query.includes('remit'))) {
        missingFacts.push('Source of original purchase funds (foreign inward remittance / NRE vs Rupee/NRO funds / inheritance)');
      }
    }

    // Residential status questions
    if (primaryMatch.category.includes('Residential Status')) {
      const mentionsDays = /\b\d+\s*days?\b/.test(query);
      const mentionsIncome = query.includes('lakh') || query.includes('income') || query.includes('crore');
      if (!mentionsDays) {
        missingFacts.push('Exact number of days spent in India during the relevant financial year (April 1 to March 31)');
      }
      if (!mentionsIncome) {
        missingFacts.push('Whether total taxable income from Indian sources exceeds ₹15 Lakhs (relevant for the 120-day rule and Section 6(1A) deemed residence)');
      }
    }

    return {
      isAmbiguous: missingFacts.length > 0,
      missingFacts
    };
  }
}
