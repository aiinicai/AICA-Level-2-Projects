import { FAQRecord, SourceCitation, WebhookResponse } from '../types/advisory';
import { RetrievalEngine } from './retrievalEngine';

export const MANDATORY_DISCLAIMER = 'Consult your CA for a case-specific position.';
export const ESCALATION_EMAIL = 'canamratad.ai@gmail.com';

export class AdvisorEngine {
  private retrievalEngine: RetrievalEngine;

  constructor(customEngine?: RetrievalEngine) {
    this.retrievalEngine = customEngine || new RetrievalEngine();
  }

  public getRetrievalEngine(): RetrievalEngine {
    return this.retrievalEngine;
  }

  public async processQuery(
    question: string,
    context?: Record<string, any>,
    history?: { role: string; text: string }[]
  ): Promise<WebhookResponse> {
    const retrieval = this.retrievalEngine.search(question);

    // 1. Handle Prompt Injection Attempts
    if (retrieval.isPromptInjection) {
      return {
        answer: `I cannot comply with requests to ignore or bypass verified advisory guidelines and the authoritative database.\n\nI am configured strictly to provide source-grounded information on Indian Income-tax and FEMA provisions based on verified law.\n\nFor assistance with complex or custom tax structuring, please get in touch with me at ${ESCALATION_EMAIL}.\n\n${MANDATORY_DISCLAIMER}`,
        sources: [],
        topic: 'Security / Compliance Refusal',
        matched_faq_ids: [],
        out_of_scope: true,
        escalation_required: true,
        disclaimer: MANDATORY_DISCLAIMER,
        confidence: 1.0,
        assumptions: ['User prompt attempted to override system guardrails. Request rejected.']
      };
    }

    // 2. Handle Out-Of-Scope or Low Confidence Queries (< 70% Similarity Threshold)
    const hasSufficientMatch = retrieval.confidence >= 0.70 && retrieval.matches.length > 0;

    if (!hasSufficientMatch) {
      return {
        answer: `I don't currently have this query covered in my verified NRI advisory database.

Please drop an email on **${ESCALATION_EMAIL}** for direct advisory assistance.

${MANDATORY_DISCLAIMER}`,
        sources: [],
        topic: retrieval.detectedTopic !== 'Unclassified' ? retrieval.detectedTopic : 'Out of Scope Query',
        matched_faq_ids: [],
        out_of_scope: true,
        escalation_required: true,
        disclaimer: MANDATORY_DISCLAIMER,
        confidence: 0,
        assumptions: ['Query not covered in verified knowledge base. Escalated to email.']
      };
    }

    // 3. Prepare Sources Citations from verified KB records
    const citations: SourceCitation[] = retrieval.matches.map((m) => ({
      provision: `${m.act_or_regulation} – ${m.section_rule_regulation}`,
      authority: m.source_authority,
      source: m.source_type,
      url: m.source_url,
      applicable_period: `${m.relevant_FY} (${m.relevant_AY})`,
      excerpt: m.source_excerpt_or_summary
    }));

    // 4. Format Answer using Verified Knowledge Base
    const primaryRecord = retrieval.matches[0];
    const generatedAnswer = this.formatDeterministicAnswer(primaryRecord, retrieval.matches, retrieval.missingFacts);

    // 5. Answer Validation Step
    const validatedAnswer = this.validateAndEnforceGuardrails(generatedAnswer, citations);

    return {
      answer: validatedAnswer,
      sources: citations,
      topic: primaryRecord.category,
      matched_faq_ids: retrieval.matches.map((m) => m.faq_id),
      out_of_scope: false,
      escalation_required: primaryRecord.professional_review_required === 'YES',
      disclaimer: MANDATORY_DISCLAIMER,
      confidence: retrieval.confidence,
      clarifications_needed: retrieval.missingFacts.length > 0 ? retrieval.missingFacts : undefined,
      assumptions: [
        `Applicable for Financial Year: ${primaryRecord.relevant_FY}`,
        `Taxpayer status: ${primaryRecord.taxpayer_type} (${primaryRecord.NRI_status})`,
        primaryRecord.professional_review_required === 'REVIEW'
          ? 'Provision verified against official gazette / notifications as of current date; professional review recommended.'
          : 'Statutory rule is verified.'
      ]
    };
  }

  private formatDeterministicAnswer(primary: FAQRecord, allMatches: FAQRecord[], missingFacts: string[]): string {
    const factsList = [
      ...primary.conditions.map((c) => `Condition: ${c}`),
      ...missingFacts.map((f) => `Missing detail needed: ${f}`),
      `Holding period / residency day count in India as per Section 6`
    ];

    return `### Short answer
${primary.short_answer}

### How the rule works
${primary.detailed_answer}

${primary.exceptions.length > 0 ? `**Key Exceptions & Caveats:**\n${primary.exceptions.map((e) => `- ${e}`).join('\n')}\n` : ''}

### What this depends on
${factsList.map((fact) => `- ${fact}`).join('\n')}

### Source
* Provision: ${primary.act_or_regulation} – ${primary.section_rule_regulation}
* Authority: ${primary.source_authority}
* Source: ${primary.source_type} (${primary.circular_notification || primary.section_rule_regulation})
* Applicable FY/AY/date: ${primary.relevant_FY} (${primary.relevant_AY}) (Effective from ${primary.effective_from})

### Important
This is general information based on the verified knowledge base and is not case-specific professional advice.

${MANDATORY_DISCLAIMER}`;
  }

  private validateAndEnforceGuardrails(answer: string, citations: SourceCitation[]): string {
    let result = answer.trim();

    // 1. Ensure mandatory disclaimer is present
    if (!result.includes(MANDATORY_DISCLAIMER)) {
      result += `\n\n### Important\nThis is general information based on the verified knowledge base and is not case-specific professional advice.\n\n**${MANDATORY_DISCLAIMER}**`;
    }

    // 2. Ensure sources are represented
    if (!result.includes('### Source') && citations.length > 0) {
      const primary = citations[0];
      result += `\n\n### Source\n* Provision: ${primary.provision}\n* Authority: ${primary.authority}\n* Source: ${primary.source}\n* Applicable FY/AY/date: ${primary.applicable_period}`;
    }

    return result;
  }
}
