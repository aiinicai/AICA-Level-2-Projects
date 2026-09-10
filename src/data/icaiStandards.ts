export interface ICAIStandardDoc {
  code: string;
  title: string;
  category: string;
  summary: string;
  keyParagraphs: Array<{
    ref: string;
    title: string;
    content: string;
  }>;
  practicalAuditorGuidance: string[];
}

export const ICAI_STANDARDS: ICAIStandardDoc[] = [
  {
    code: 'SA 315 (Revised)',
    title: 'Identifying and Assessing the Risks of Material Misstatement Through Understanding the Entity and Its Environment',
    category: 'Risk Assessment & Internal Control',
    summary: 'Establishes the auditor\'s responsibility to identify and assess the risks of material misstatement in the financial statements through understanding the entity and its environment, including its internal control, thereby providing a basis for designing and implementing responses to the assessed risks of material misstatement.',
    keyParagraphs: [
      {
        ref: 'Para 11',
        title: 'Understanding the Entity and Its Environment',
        content: 'The auditor shall obtain an understanding of: (a) Relevant industry, regulatory, and other external factors including the applicable financial reporting framework; (b) The nature of the entity, including its operations, ownership and governance structures, types of investments, and the way the entity is structured and financed; (c) The entity\'s selection and application of accounting policies; (d) The entity\'s objectives and strategies, and related business risks; (e) The measurement and review of the entity\'s financial performance.',
      },
      {
        ref: 'Para 14',
        title: 'Control Environment',
        content: 'The auditor shall evaluate whether: (a) Management, with the oversight of those charged with governance, has created and maintained a culture of honesty and ethical behavior; and (b) The strengths in the control environment elements collectively provide an appropriate foundation for the other components of internal control.',
      },
      {
        ref: 'Para 18',
        title: 'Information System and Communication',
        content: 'The auditor shall obtain an understanding of the information system, including related business processes, relevant to financial reporting, including: (a) The classes of transactions in the entity\'s operations that are significant to the financial statements; (b) The procedures by which those transactions are initiated, recorded, processed, corrected as necessary, and transferred to the general ledger.',
      },
      {
        ref: 'Para 27-29',
        title: 'Identifying and Assessing Risks at FS and Assertion Level',
        content: 'The auditor shall identify and assess the risks of material misstatement at: (a) The financial statement level; and (b) The assertion level for classes of transactions, account balances, and disclosures, to provide a basis for designing and performing further audit procedures.',
      },
      {
        ref: 'Para 28',
        title: 'Significant Risks Definition',
        content: 'In exercising judgment as to which risks are significant risks, the auditor shall consider at least: (a) Whether the risk is a risk of fraud; (b) Whether the risk is related to recent significant economic, accounting or other developments; (c) The complexity of transactions; (d) Whether the risk involves significant transactions with related parties; (e) The degree of subjectivity in the measurement of financial information; (f) Whether the risk involves significant transactions outside the normal course of business.',
      },
    ],
    practicalAuditorGuidance: [
      'Document walkthroughs for each significant business process to verify design and implementation of controls, not just operational descriptions.',
      'Distinguish between inherent risk (before controls) and control risk (failure of controls to prevent/detect misstatements).',
      'Significant risks require special audit consideration; routine substantive analytical procedures alone are insufficient.',
    ],
  },
  {
    code: 'SA 240',
    title: 'The Auditor\'s Responsibilities Relating to Fraud in an Audit of Financial Statements',
    category: 'Fraud & Error',
    summary: 'Deals with the auditor\'s responsibilities relating to fraud in an audit of financial statements, distinguishing between fraudulent financial reporting and misappropriation of assets, and outlining mandatory presumptions and required audit procedures.',
    keyParagraphs: [
      {
        ref: 'Para 12-14',
        title: 'Professional Skepticism',
        content: 'The auditor shall maintain professional skepticism throughout the audit, recognizing the possibility that a material misstatement due to fraud could exist, notwithstanding the auditor\'s past experience of the honesty and integrity of the entity\'s management and those charged with governance.',
      },
      {
        ref: 'Para 26',
        title: 'Presumption of Fraud Risk in Revenue Recognition',
        content: 'When identifying and assessing the risks of material misstatement due to fraud, the auditor shall, based on a presumption that there are risks of fraud in revenue recognition, evaluate which types of revenue, revenue transactions or assertions give rise to such risks. If the auditor concludes that the presumption is not applicable, the auditor shall document the reasons.',
      },
      {
        ref: 'Para 31-33',
        title: 'Management Override of Controls',
        content: 'Management is in a unique position to perpetrate fraud because of management\'s ability to manipulate accounting records and prepare fraudulent financial statements by overriding controls that otherwise appear to be operating effectively. Irrespective of the auditor\'s assessment of the risks of management override, the auditor shall design and perform audit procedures to: (a) Test the appropriateness of journal entries and other adjustments; (b) Review accounting estimates for biases; and (c) Evaluate the business rationale for significant transactions that are outside the normal course of business.',
      },
    ],
    practicalAuditorGuidance: [
      'Revenue recognition fraud presumption can only be rebutted with clear written justification (e.g. single long-term lease with fixed predetermined payments).',
      'Management override of controls is non-rebuttable and applies to all entities regardless of size or governance quality.',
      'Journal entries testing should target entries made at the end of a reporting period, by individuals who typically do not make journal entries, or containing round numbers.',
    ],
  },
  {
    code: 'SA 330',
    title: 'The Auditor\'s Responses to Assessed Risks',
    category: 'Audit Responses & Fieldwork',
    summary: 'Governs the auditor\'s responsibility to design and implement overall responses to address the assessed risks of material misstatement at the financial statement level and to design and perform further audit procedures whose nature, timing, and extent are based on and are responsive to the assessed risks of material misstatement at the assertion level.',
    keyParagraphs: [
      {
        ref: 'Para 18',
        title: 'Substantive Procedures for Significant Risks',
        content: 'If the auditor has determined that an assessed risk of material misstatement at the assertion level is a significant risk, the auditor shall perform substantive procedures that are specifically responsive to that risk. When the approach to a significant risk consists only of substantive procedures, those procedures shall include tests of details.',
      },
      {
        ref: 'Para 21',
        title: 'Substantive Procedures Requirement',
        content: 'Irrespective of the assessed risks of material misstatement, the auditor shall design and perform substantive procedures for each material class of transactions, account balance, and disclosure.',
      },
      {
        ref: 'Para 8-10',
        title: 'Tests of Controls',
        content: 'The auditor shall design and perform tests of controls to obtain sufficient appropriate audit evidence as to the operating effectiveness of relevant controls if: (a) The auditor\'s assessment of risks of material misstatement at the assertion level includes an expectation that the controls are operating effectively; or (b) Substantive procedures alone cannot provide sufficient appropriate audit evidence at the assertion level.',
      },
    ],
    practicalAuditorGuidance: [
      'Mandatory rule: Every identified Significant Risk MUST have a corresponding Test of Details (TOD). Substantive Analytical Procedures alone do not suffice.',
      'If relying on operating effectiveness of controls tested in prior audits, controls must be retested at least once in every three audits, provided no changes have occurred.',
      'Interim testing requires roll-forward substantive procedures covering the remaining period to year-end.',
    ],
  },
  {
    code: 'SA 320',
    title: 'Materiality in Planning and Performing an Audit',
    category: 'Materiality & Evaluation',
    summary: 'Deals with the auditor\'s responsibility to apply the concept of materiality in planning and performing an audit of financial statements, determining performance materiality, and revising materiality as the audit progresses.',
    keyParagraphs: [
      {
        ref: 'Para 10',
        title: 'Determining Overall Materiality',
        content: 'When establishing the overall audit strategy, the auditor shall determine materiality for the financial statements as a whole. If, in the specific circumstances of the entity, there is one or more particular classes of transactions, account balances or disclosures for which misstatements of lesser amounts than materiality for the financial statements as a whole could reasonably be expected to influence the economic decisions of users taken on the basis of the financial statements, the auditor shall also determine the materiality level or levels to be applied to those particular classes of transactions, account balances or disclosures.',
      },
      {
        ref: 'Para 11',
        title: 'Performance Materiality',
        content: 'The auditor shall determine performance materiality for purposes of assessing the risks of material misstatement and determining the nature, timing and extent of further audit procedures. Performance materiality is set to reduce to an appropriately low level the probability that the aggregate of uncorrected and undetected misstatements exceeds materiality for the financial statements as a whole.',
      },
      {
        ref: 'Para A3-A8',
        title: 'Benchmark Selection in Practice',
        content: 'Determining materiality involves the exercise of professional judgment. A percentage is often applied to a chosen benchmark as a starting point. Critical factors include: elements of financial statements, whether there are items on which attention of users tends to be focused, nature of entity, ownership structure, and financing. Common conventions: 5-10% of profit before tax from continuing operations; 0.5-1% of total revenue; 1-2% of total assets or equity.',
      },
    ],
    practicalAuditorGuidance: [
      'Materiality is not a mechanical calculation: document qualitative factors including regulatory scrutiny, loan covenants, and volatility.',
      'Performance materiality is typically set between 50% (higher risk / new engagement) and 75% (strong controls / low history of misstatements) of overall materiality.',
      'Clearly Trivial threshold (SA 450) is typically set at 3% to 5% of overall materiality.',
    ],
  },
  {
    code: 'SA 450',
    title: 'Evaluation of Misstatements Identified During the Audit',
    category: 'Materiality & Evaluation',
    summary: 'Deals with the auditor\'s responsibility to evaluate the effect of identified misstatements on the audit and of uncorrected misstatements, if any, on the financial statements.',
    keyParagraphs: [
      {
        ref: 'Para 5',
        title: 'Accumulation of Identified Misstatements',
        content: 'The auditor shall accumulate misstatements identified during the audit, other than those that are clearly trivial. The auditor may designate an amount below which misstatements would be clearly trivial and would not be accumulated because the auditor expects that the accumulation of such amounts clearly would not have a material effect on the financial statements.',
      },
    ],
    practicalAuditorGuidance: [
      'Maintain a Summary of Audit Differences (SAD) sheet categorizing factual, judgmental, and projected misstatements.',
      'Request management to adjust all accumulated misstatements, and document reasons if management declines.',
    ],
  },
  {
    code: 'SQC 1 / SA 220',
    title: 'Quality Control for an Audit of Financial Statements',
    category: 'Quality Control',
    summary: 'Deals with the specific responsibilities of the auditor regarding quality control procedures for an audit of financial statements and the responsibilities of the engagement quality control reviewer.',
    keyParagraphs: [
      {
        ref: 'SQC 1.26',
        title: 'Acceptance and Continuance of Client Relationships',
        content: 'The firm shall establish policies and procedures for the acceptance and continuance of client relationships and specific engagements, designed to provide the firm with reasonable assurance that it will only undertake or continue relationships where the firm: (a) Is competent to perform the engagement; (b) Can comply with relevant ethical requirements; and (c) Has considered the integrity of the client.',
      },
      {
        ref: 'SA 220.15',
        title: 'Direction, Supervision and Performance',
        content: 'The engagement partner shall take responsibility for the direction, supervision and performance of the audit engagement in compliance with professional standards and applicable legal and regulatory requirements, and that the auditor\'s report issued is appropriate in the circumstances.',
      },
    ],
    practicalAuditorGuidance: [
      'Complete pre-engagement inquiries and independence declarations prior to commencing fieldwork.',
      'For listed entities or high-risk private entities, an Engagement Quality Control Reviewer (EQCR) must conduct an objective evaluation before report issuance.',
    ],
  },
];
