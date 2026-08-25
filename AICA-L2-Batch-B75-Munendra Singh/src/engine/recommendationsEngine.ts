import { AuditRecommendation, InconsistencyItem, DisclosureItem } from '../types';
import { ParsedFinancialDocument } from './types';

export function generateAuditRecommendations(
  doc: ParsedFinancialDocument,
  disclosures: DisclosureItem[],
  inconsistencies: InconsistencyItem[]
): AuditRecommendation[] {
  const recommendations: AuditRecommendation[] = [];
  let recIndex = 1;

  // 1. High-priority recommendations for inconsistencies
  const highRiskInconsistencies = inconsistencies.filter((i) => i.riskLevel.toLowerCase() === 'high');
  for (const item of highRiskInconsistencies) {
    let actionFor = 'Engagement Partner';
    let statRef = 'SA 700 / Section 134 & Schedule III';
    
    if (item.type === 'casting_error') {
      actionFor = 'Audit Senior / CFO';
      statRef = 'ICAI Schedule III Guidance Note';
    } else if (item.lineItem.includes('KMP') || item.lineItem.includes('Remuneration')) {
      actionFor = 'Engagement Partner / Audit Committee';
      statRef = 'Ind AS 24 & Section 197 Companies Act 2013';
    } else if (item.lineItem.includes('Cash and Cash Equivalents')) {
      actionFor = 'Audit Senior / Financial Controller';
      statRef = 'Ind AS 7.45';
    }

    recommendations.push({
      id: `REC-0${recIndex++}`,
      priority: 'Immediate',
      category: 'Financial Statement Inconsistency & Casting',
      recommendation: `Issue Audit Query Memo regarding '${item.lineItem}'. Require management to rectify the discrepancy (${item.discrepancy}) before balance sheet sign-off or prepare appropriate adjusting journal entries.`,
      statutoryReference: statRef,
      actionFor,
    });
  }

  // 2. Recommendations for Missing Statutory Disclosures
  const missingDisclosures = disclosures.filter((d) => d.status === 'Missing');
  for (const item of missingDisclosures) {
    recommendations.push({
      id: `REC-0${recIndex++}`,
      priority: 'Pre-Signing',
      category: `${item.standard} Statutory Compliance`,
      recommendation: `Incorporate mandatory disclosure for '${item.requirement}' in the Notes to Accounts. Obtain signed management schedule and reconcile against trial balance prior to final report issuance.`,
      statutoryReference: `${item.standard} ${item.applicableParagraph || ''}`.trim(),
      actionFor: 'Audit Senior / Engagement Partner',
    });
  }

  // 3. Recommendations for Partial Disclosures
  const partialDisclosures = disclosures.filter((d) => d.status === 'Partial');
  for (const item of partialDisclosures.slice(0, 3)) {
    recommendations.push({
      id: `REC-0${recIndex++}`,
      priority: 'Pre-Signing',
      category: `${item.standard} Disclosure Enhancement`,
      recommendation: `Expand disclosure for '${item.requirement}'. Ensure all sub-clauses, sensitivity matrices, and category breakdowns meet ICAI / NFRA quality review benchmarks.`,
      statutoryReference: item.applicableParagraph || item.standard,
      actionFor: 'Audit Senior',
    });
  }

  // 4. Management Letter / Internal Controls Recommendations
  if (doc.ratios.some(r => r.variancePercent && Math.abs(r.variancePercent) >= 25 && !r.explanationProvided)) {
    recommendations.push({
      id: `REC-0${recIndex++}`,
      priority: 'Pre-Signing',
      category: 'MCA 2021 Schedule III Ratios',
      recommendation: 'Provide detailed qualitative management explanations for all statutory analytical ratios with >25% year-on-year variance in compliance with MCA GSR 207(E).',
      statutoryReference: 'Schedule III Div II Part I Clause (x)',
      actionFor: 'CFO / Management',
    });
  }

  if (!doc.hasMSMEDisclosure) {
    recommendations.push({
      id: `REC-0${recIndex++}`,
      priority: 'Pre-Signing',
      category: 'MSMED Act Section 22 Compliance',
      recommendation: 'Obtain written confirmation from suppliers regarding MSME Udyam registration status and disclose overdue principal and accrued interest pursuant to Section 22 of MSMED Act, 2006.',
      statutoryReference: 'MSMED Act 2006 & CARO 2020 Clause (b)',
      actionFor: 'Finance Controller / Audit Team',
    });
  }

  recommendations.push({
    id: `REC-0${recIndex++}`,
    priority: 'Management Letter',
    category: 'MRL & Governance Representation',
    recommendation: 'Obtain specific Management Representation Letter (MRL) clauses under SA 580 covering contingent liabilities quantification, title deeds verification, and compliance with struck-off entity rules.',
    statutoryReference: 'SA 580 & CARO 2020',
    actionFor: 'Engagement Partner',
  });

  return recommendations;
}
