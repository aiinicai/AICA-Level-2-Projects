import { AuditReportData } from '../types';
import { AuditOptions } from './types';
import { parseFinancialDocument } from './parser';
import { STATUTORY_DISCLOSURE_RULES, SCHEDULE_III_MCA_2021_RULES } from './statutoryRules';
import { executeNoteProofreading } from './proofreadingEngine';
import { executeConsistencyVerification } from './consistencyEngine';
import { generateAuditRecommendations } from './recommendationsEngine';
import { buildAuditReport } from './reportGenerator';

export async function runOfflineAudit(
  rawText: string,
  fileName?: string,
  options?: AuditOptions
): Promise<AuditReportData> {
  // Simulate rapid deterministic pipeline
  // Phase 1: Parse financial statements and notes
  const parsedDoc = parseFinancialDocument(rawText, fileName);

  // Phase 2: Evaluate Ind AS Mandatory Disclosures Matrix
  const focusedStandards = options?.standardsFocus;
  const applicableRules = focusedStandards && focusedStandards.length > 0
    ? STATUTORY_DISCLOSURE_RULES.filter(r => focusedStandards.some(f => r.standard.includes(f) || f.includes(r.standard)))
    : STATUTORY_DISCLOSURE_RULES;

  const evaluatedDisclosures = applicableRules.map((rule) => {
    const res = rule.evaluate(parsedDoc);
    return {
      standard: rule.standard,
      standardName: rule.standardName,
      requirement: rule.requirement,
      status: res.status,
      observation: res.observation,
      applicableParagraph: rule.applicableParagraph,
    };
  });

  // Schedule III Findings
  const scheduleIIIFindings = SCHEDULE_III_MCA_2021_RULES.map((rule) => {
    const res = rule.evaluate(parsedDoc);
    return {
      clause: rule.clause,
      requirement: rule.requirement,
      complianceStatus: res.complianceStatus,
      detailedFinding: res.detailedFinding,
      guidanceNoteReference: rule.guidanceNoteReference,
    };
  });

  // Phase 3: Castings, Mathematical Footing & Consistency Check
  const inconsistencies = executeConsistencyVerification(parsedDoc);

  // Note-by-Note Proofreading
  const noteProofreading = executeNoteProofreading(parsedDoc);

  // Phase 4: Actionable CA Recommendations
  const recommendations = generateAuditRecommendations(parsedDoc, evaluatedDisclosures, inconsistencies);

  // Final Synthesis
  const auditReport = buildAuditReport(
    parsedDoc,
    evaluatedDisclosures,
    inconsistencies,
    noteProofreading,
    scheduleIIIFindings,
    recommendations
  );

  return auditReport;
}

export { executeNoteProofreading } from './proofreadingEngine';
