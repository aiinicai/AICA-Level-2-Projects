import { RedactionToken, ClientProfile } from '../types';

export class PrivacyShield {
  private static tokenStore: Map<string, RedactionToken> = new Map();
  private static reverseTokenStore: Map<string, string> = new Map();
  private static counters = {
    COMPANY: 1,
    PERSON: 1,
    BANK_ACCOUNT: 1,
    TAX_ID: 1,
    ADDRESS: 1,
    PHONE: 1,
    EMAIL: 1,
    CARD: 1,
    CUSTOM: 1,
  };

  /**
   * Initialize or register known client entities for tokenization
   */
  static registerClientEntities(client: ClientProfile) {
    if (!client) return;

    if (client.name) {
      this.getOrCreateToken(client.name, 'COMPANY');
    }
    if (client.legalEntityName && client.legalEntityName !== client.name) {
      this.getOrCreateToken(client.legalEntityName, 'COMPANY');
    }
    if (client.contactEmail) {
      this.getOrCreateToken(client.contactEmail, 'EMAIL');
    }
    if (client.contactPhone) {
      this.getOrCreateToken(client.contactPhone, 'PHONE');
    }
    if (client.taxId) {
      this.getOrCreateToken(client.taxId, 'TAX_ID');
    }
    if (client.bankAccountMasked) {
      this.getOrCreateToken(client.bankAccountMasked, 'BANK_ACCOUNT');
    }
  }

  static getOrCreateToken(
    originalText: string,
    type: 'COMPANY' | 'PERSON' | 'BANK_ACCOUNT' | 'TAX_ID' | 'ADDRESS' | 'PHONE' | 'EMAIL' | 'CARD' | 'CUSTOM',
    sourceDoc: string = 'System Profile'
  ): RedactionToken {
    const trimmed = originalText.trim();
    if (!trimmed) {
      return {
        id: 'empty',
        originalText: '',
        tokenType: type,
        tokenValue: '',
        occurrences: 0,
        confidence: 1,
        status: 'approved',
        sourceDocuments: [],
      };
    }

    const key = trimmed.toLowerCase();
    if (this.tokenStore.has(key)) {
      const existing = this.tokenStore.get(key)!;
      existing.occurrences += 1;
      if (!existing.sourceDocuments.includes(sourceDoc)) {
        existing.sourceDocuments.push(sourceDoc);
      }
      return existing;
    }

    const num = this.counters[type]++;
    const tokenVal = `[${type}_${String(num).padStart(3, '0')}]`;
    
    const newToken: RedactionToken = {
      id: `token_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      originalText: trimmed,
      tokenType: type,
      tokenValue: tokenVal,
      occurrences: 1,
      confidence: 0.98,
      status: 'approved',
      sourceDocuments: [sourceDoc],
    };

    this.tokenStore.set(key, newToken);
    this.reverseTokenStore.set(tokenVal, trimmed);
    return newToken;
  }

  /**
   * Scan text or JSON object and redact sensitive information
   */
  static redact(text: string, privacyMode: 'standard' | 'strict' | 'maximum' = 'strict'): { redactedText: string; tokensDetected: RedactionToken[] } {
    if (!text) return { redactedText: '', tokensDetected: [] };

    let result = text;
    const detected: RedactionToken[] = [];

    // 1. Check known registered tokens
    for (const [key, token] of this.tokenStore.entries()) {
      const regex = new RegExp(`\\b${this.escapeRegExp(token.originalText)}\\b`, 'gi');
      if (regex.test(result)) {
        result = result.replace(regex, token.tokenValue);
        if (!detected.some(d => d.id === token.id)) {
          detected.push(token);
        }
      }
    }

    // 2. Regex Patterns for dynamic PII detection
    // Email regex
    const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/gi;
    result = result.replace(emailRegex, (match) => {
      const t = this.getOrCreateToken(match, 'EMAIL', 'Document Scan');
      if (!detected.some(d => d.id === t.id)) detected.push(t);
      return t.tokenValue;
    });

    // Phone regex
    const phoneRegex = /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g;
    result = result.replace(phoneRegex, (match) => {
      if (match.length >= 10) {
        const t = this.getOrCreateToken(match, 'PHONE', 'Document Scan');
        if (!detected.some(d => d.id === t.id)) detected.push(t);
        return t.tokenValue;
      }
      return match;
    });

    // SSN / EIN / Tax ID regex (e.g. 12-3456789 or 123-45-6789)
    const taxRegex = /\b(\d{2}-\d{7}|\d{3}-\d{2}-\d{4})\b/g;
    result = result.replace(taxRegex, (match) => {
      const t = this.getOrCreateToken(match, 'TAX_ID', 'Document Scan');
      if (!detected.some(d => d.id === t.id)) detected.push(t);
      return t.tokenValue;
    });

    // Credit Card regex
    const cardRegex = /\b(?:\d{4}[-\s]?){3}\d{4}\b/g;
    result = result.replace(cardRegex, (match) => {
      const t = this.getOrCreateToken(match, 'CARD', 'Document Scan');
      if (!detected.some(d => d.id === t.id)) detected.push(t);
      return t.tokenValue;
    });

    return { redactedText: result, tokensDetected: detected };
  }

  /**
   * Restore original text on authorized export or view
   */
  static restore(redactedText: string): string {
    if (!redactedText) return '';
    let restored = redactedText;

    for (const [tokenVal, original] of this.reverseTokenStore.entries()) {
      restored = restored.split(tokenVal).join(original);
    }

    return restored;
  }

  /**
   * Helper for string text redaction
   */
  static redactText(text: string): string {
    return this.redact(text, 'strict').redactedText;
  }

  /**
   * Helper to sanitize an entire financial model before sending to Gemini API
   */
  static sanitizeFinancialModel(model: any) {
    const client = model.client;
    this.registerClientEntities(client);

    return {
      industry: client.industry,
      industryName: client.industryName,
      reportingPeriod: client.reportingPeriod,
      currency: client.currency,
      historicalMonthly: model.historicalMonthly.map((m: any) => ({
        periodKey: m.periodKey,
        periodLabel: m.periodLabel,
        revenue: m.revenue,
        cogs: m.cogs,
        grossProfit: m.grossProfit,
        grossMarginPercent: m.grossMarginPercent,
        totalOpex: m.totalOpex,
        ebitda: m.ebitda,
        ebitdaMarginPercent: m.ebitdaMarginPercent,
        netIncome: m.netIncome,
        netMarginPercent: m.netMarginPercent,
        cashAndEquivalents: m.cashAndEquivalents,
        accountsReceivable: m.accountsReceivable,
        accountsPayable: m.accountsPayable,
        operatingCashFlow: m.operatingCashFlow,
        workingCapital: m.workingCapital,
        dso: m.dso,
        dpo: m.dpo,
      })),
      summary: model.summary,
    };
  }

  /**
   * Helper to de-anonymize text returned by AI
   */
  static deAnonymizeText(text: string): string {
    return this.restore(text);
  }

  /**
   * Get all active tokens with compatibility properties
   */
  static getAllTokens(): RedactionToken[] {
    return Array.from(this.tokenStore.values()).map(t => ({
      ...t,
      category: t.tokenType,
      originalValue: t.originalText,
      token: t.tokenValue,
    }));
  }

  /**
   * Add custom redaction term
   */
  static addCustomRedaction(term: string): RedactionToken {
    return this.getOrCreateToken(term, 'CUSTOM', 'User Defined Rule');
  }

  /**
   * Delete token
   */
  static removeToken(id: string): boolean {
    for (const [key, token] of this.tokenStore.entries()) {
      if (token.id === id) {
        this.reverseTokenStore.delete(token.tokenValue);
        this.tokenStore.delete(key);
        return true;
      }
    }
    return false;
  }

  private static escapeRegExp(string: string): string {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
}
