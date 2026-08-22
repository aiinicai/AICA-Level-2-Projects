import {
  AuditReportData,
  ComplianceScore,
  ExecutiveSummary,
  DisclosureItem,
  InconsistencyItem,
  NoteProofreadingItem,
  ScheduleIIIGuidanceItem,
  AuditRecommendation,
} from '../types';
import { ParsedFinancialDocument } from './types';

export function buildAuditReport(
  doc: ParsedFinancialDocument,
  disclosures: DisclosureItem[],
  inconsistencies: InconsistencyItem[],
  noteProofreading: NoteProofreadingItem[],
  scheduleIIIGuidanceFindings: ScheduleIIIGuidanceItem[],
  recommendations: AuditRecommendation[]
): AuditReportData {
  const missingCount = disclosures.filter((d) => d.status === 'Missing').length;
  const partialCount = disclosures.filter((d) => d.status === 'Partial').length;
  const highRiskCount = inconsistencies.filter((i) => i.riskLevel.toLowerCase() === 'high').length;
  const totalDiscrepancies = missingCount + inconsistencies.length;

  let overallComplianceScore: ComplianceScore = 'High';
  if (highRiskCount > 0 || missingCount >= 2 || totalDiscrepancies >= 4) {
    overallComplianceScore = 'Needs Immediate Revision';
  } else if (missingCount > 0 || partialCount >= 2 || totalDiscrepancies > 1) {
    overallComplianceScore = 'Moderate';
  }

  const keyRiskList: string[] = [];
  if (highRiskCount > 0) {
    keyRiskList.push(`${highRiskCount} High-Risk numerical/casting inconsistencies detected.`);
  }
  if (missingCount > 0) {
    const missingStds = Array.from(new Set(disclosures.filter(d => d.status === 'Missing').map(d => d.standard))).join(', ');
    keyRiskList.push(`Mandatory statutory disclosures missing under ${missingStds}.`);
  }
  const nonCompScheduleIII = scheduleIIIGuidanceFindings.filter(s => s.complianceStatus === 'Non-Compliant' || s.complianceStatus === 'Not Disclosed').length;
  if (nonCompScheduleIII > 0) {
    keyRiskList.push(`${nonCompScheduleIII} Schedule III / MCA 2021 statutory reporting gaps.`);
  }
  if (keyRiskList.length === 0) {
    keyRiskList.push('Financial statements show satisfactory alignment with Ind AS framework and Schedule III requirements.');
  }

  const summary: ExecutiveSummary = {
    overallComplianceScore,
    totalDiscrepancies,
    missingDisclosuresCount: missingCount,
    numericalMismatchesCount: inconsistencies.length,
    keyRiskAreas: keyRiskList.join(' '),
    entityName: doc.entityName,
    reportingPeriod: doc.reportingPeriod,
    reportingScale: doc.reportingScale,
    frameworkIdentified: doc.framework,
  };

  const financialHighlights = {
    totalRevenue: doc.totalRevenueCurrent ? `${doc.reportingScale} ${doc.totalRevenueCurrent.toLocaleString('en-IN')}` : undefined,
    pat: doc.patCurrent ? `${doc.reportingScale} ${doc.patCurrent.toLocaleString('en-IN')}` : undefined,
    totalAssets: doc.totalAssetsCurrent ? `${doc.reportingScale} ${doc.totalAssetsCurrent.toLocaleString('en-IN')}` : undefined,
    totalDebt: doc.totalDebtCurrent ? `${doc.reportingScale} ${doc.totalDebtCurrent.toLocaleString('en-IN')}` : undefined,
    netWorth: doc.netWorthCurrent ? `${doc.reportingScale} ${doc.netWorthCurrent.toLocaleString('en-IN')}` : undefined,
  };

  const caroObservations = [
    'Clause (i)(c): Verify title deeds of immovable property not held in entity name against Land Revenue Records.',
    'Clause (ii)(b): Reconcile quarterly stock statements submitted to banks against books of accounts (any material variance >5%).',
    'Clause (vii)(a): Undisputed statutory dues outstanding for > 6 months from due date verified.',
    'Clause (ix)(a): Affirmation that company has not defaulted in repayment of loans or borrowing to banks / FIs.',
  ];

  const rawMarkdownReport = generateMarkdownDossier(
    doc,
    summary,
    financialHighlights,
    disclosures,
    inconsistencies,
    noteProofreading,
    scheduleIIIGuidanceFindings,
    recommendations,
    caroObservations
  );

  return {
    id: `audit-offline-${Date.now()}`,
    timestamp: new Date().toISOString(),
    documentTitle: doc.title,
    summary,
    part1Disclosures: disclosures,
    part2Inconsistencies: inconsistencies,
    noteProofreading,
    scheduleIIIGuidanceFindings,
    part3Recommendations: recommendations,
    rawMarkdownReport,
    financialHighlights,
    caroObservations,
  };
}

function generateMarkdownDossier(
  doc: ParsedFinancialDocument,
  summary: ExecutiveSummary,
  highlights: any,
  disclosures: DisclosureItem[],
  inconsistencies: InconsistencyItem[],
  noteProofreading: NoteProofreadingItem[],
  scheduleIII: ScheduleIIIGuidanceItem[],
  recommendations: AuditRecommendation[],
  caro: string[]
): string {
  const dateStr = new Date().toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });

  return `# STATUTORY AUDIT & IND AS DISCLOSURE CONSISTENCY REPORT
**Entity Name:** ${summary.entityName || 'Client Entity'}  
**Reporting Period:** ${summary.reportingPeriod || 'FY 2024-25'}  
**Reporting Scale:** ${summary.reportingScale || '₹ in Lakhs'}  
**Accounting Framework:** ${summary.frameworkIdentified || 'Ind AS (Schedule III Division II)'}  
**Date of Audit Verification:** ${dateStr}  
**Engine Execution:** Offline Deterministic Chartered Accountant Audit Engine (100% On-Device)

---

## 1. EXECUTIVE AUDIT SUMMARY & QRB RISK ASSESSMENT

- **Overall Compliance Score:** **${summary.overallComplianceScore.toUpperCase()}**
- **Total Discrepancies / Exceptions:** **${summary.totalDiscrepancies}**
- **Missing Statutory Disclosures:** **${summary.missingDisclosuresCount}**
- **Numerical & Casting Inconsistencies:** **${summary.numericalMismatchesCount}**
- **Key Risk Areas:** ${summary.keyRiskAreas}

### Key Financial Indicators
| Metric | Reported Figure |
| :--- | :--- |
| **Total Revenue / Income** | ${highlights.totalRevenue || 'N/A'} |
| **Profit After Tax (PAT)** | ${highlights.pat || 'N/A'} |
| **Total Assets** | ${highlights.totalAssets || 'N/A'} |
| **Total Borrowings / Debt** | ${highlights.totalDebt || 'N/A'} |
| **Net Worth / Total Equity** | ${highlights.netWorth || 'N/A'} |

---

## 2. PART 1: IND AS MANDATORY DISCLOSURE COMPLIANCE MATRIX

| Standard | Mandatory Requirement | Status | Audit Observation & Location |
| :--- | :--- | :--- | :--- |
${disclosures.map(d => `| **${d.standard}** | ${d.requirement} | **${d.status}** | ${d.observation} |`).join('\n')}

---

## 3. PART 2: CROSS-REFERENCING & INTERNAL CONSISTENCY FINDINGS

| Line Item | Primary Statement Figure | Note Figure / Reference | Risk Level | Discrepancy & Variance Detail |
| :--- | :--- | :--- | :--- | :--- |
${inconsistencies.length > 0 ? inconsistencies.map(i => `| **${i.lineItem}** | ${i.primaryFigure} | ${i.noteFigure} | **${i.riskLevel}** | ${i.discrepancy} |`).join('\n') : '| *No numerical inconsistencies detected.* | - | - | Low | All financial tables and note sub-schedules cast accurately. |'}

---

## 4. SCHEDULE III & MCA 2021 AMENDMENTS COMPLIANCE AUDIT

| Statutory Clause | Mandatory Requirement | Status | Auditor Finding | Reference |
| :--- | :--- | :--- | :--- | :--- |
${scheduleIII.map(s => `| **${s.clause}** | ${s.requirement} | **${s.complianceStatus}** | ${s.detailedFinding} | ${s.guidanceNoteReference} |`).join('\n')}

---

## 5. NOTE-BY-NOTE PROOFREADING & CASTING EVALUATION

| Note No. | Note Title | Status | Clauses Verified | Observations / Drafting Issues |
| :--- | :--- | :--- | :--- | :--- |
${noteProofreading.map(n => `| **${n.noteNumber}** | ${n.noteTitle} | **${n.proofreadingStatus}** | ${n.mandatoryClausesChecked} | ${n.observations}${n.draftingOrArithmeticIssues ? ` *(Issue: ${n.draftingOrArithmeticIssues})*` : ''} |`).join('\n')}

---

## 6. CARO 2020 AUDITOR OBSERVATIONS

${caro.map((c, i) => `${i + 1}. **${c}**`).join('\n')}

---

## 7. PART 3: ACTIONABLE AUDIT RECOMMENDATIONS FOR ENGAGEMENT TEAM

| Ref ID | Priority | Category | Action Item / Recommendation | Statutory Ref | Assigned To |
| :--- | :--- | :--- | :--- | :--- | :--- |
${recommendations.map(r => `| **${r.id}** | **${r.priority}** | ${r.category} | ${r.recommendation} | ${r.statutoryReference || '-'} | **${r.actionFor}** |`).join('\n')}

---

*This statutory audit dossier was generated locally by the FinAudit AI Compliance Engine without cloud data transmission.*
`;
}
