import { InconsistencyItem, RiskLevel } from '../types';
import { ParsedFinancialDocument } from './types';
import { parseNumberString } from './parser';

export function executeConsistencyVerification(doc: ParsedFinancialDocument): InconsistencyItem[] {
  const inconsistencies: InconsistencyItem[] = [];

  // 1. Balance Sheet Equality: Total Assets vs Total Equity & Liabilities
  if (doc.totalAssetsCurrent !== undefined && doc.totalEquityLiabCurrent !== undefined) {
    const variance = Math.round((doc.totalAssetsCurrent - doc.totalEquityLiabCurrent) * 100) / 100;
    if (Math.abs(variance) > 1.0) {
      inconsistencies.push({
        lineItem: 'Balance Sheet Balance Check (Total Assets vs Total Equity & Liabilities)',
        primaryFigure: `${doc.reportingScale} ${doc.totalAssetsCurrent.toLocaleString('en-IN')}`,
        noteFigure: `${doc.reportingScale} ${doc.totalEquityLiabCurrent.toLocaleString('en-IN')}`,
        noteRef: 'Face of Balance Sheet',
        discrepancy: `Fundamental accounting equation failed: Total Assets (${doc.reportingScale} ${doc.totalAssetsCurrent.toLocaleString('en-IN')}) do not balance with Total Equity & Liabilities (${doc.reportingScale} ${doc.totalEquityLiabCurrent.toLocaleString('en-IN')}). Variance of ${doc.reportingScale} ${variance.toLocaleString('en-IN')}.`,
        riskLevel: 'High',
        type: 'casting_error',
      });
    }
  }

  // 2. Note Subtotal vs Primary Statement Line Item cross-referencing
  for (const item of [...doc.balanceSheetItems, ...doc.plItems]) {
    if (item.noteRef && doc.notes.has(item.noteRef)) {
      const note = doc.notes.get(item.noteRef)!;
      if (item.currentAmount !== undefined) {
        // Compare with note reported total or computed total
        const noteTargetAmt = note.totalReported !== undefined ? note.totalReported : (note.breakupRows.length > 0 ? note.totalComputed : undefined);
        
        if (noteTargetAmt !== undefined) {
          const diff = Math.round((item.currentAmount - noteTargetAmt) * 100) / 100;
          if (Math.abs(diff) > 1.0) {
            inconsistencies.push({
              lineItem: `${item.name} (${item.section === 'assets' || item.section === 'equity' || item.section === 'liabilities' ? 'Balance Sheet' : 'P&L Statement'})`,
              primaryFigure: `${doc.reportingScale} ${item.currentAmount.toLocaleString('en-IN')}`,
              noteFigure: `${doc.reportingScale} ${noteTargetAmt.toLocaleString('en-IN')} (Note ${item.noteRef})`,
              noteRef: `Note ${item.noteRef}: ${note.noteTitle}`,
              discrepancy: `Face of statement reports ${doc.reportingScale} ${item.currentAmount.toLocaleString('en-IN')} for '${item.name}', but Note ${item.noteRef} total schedule specifies ${doc.reportingScale} ${noteTargetAmt.toLocaleString('en-IN')}. Net variance of ${doc.reportingScale} ${diff.toLocaleString('en-IN')}.`,
              riskLevel: Math.abs(diff) > 500 ? 'High' : 'Medium',
              type: 'numerical_mismatch',
            });
          }
        }
      }
    }
  }

  // 3. Check for Note internal casting errors
  for (const [noteNum, note] of doc.notes.entries()) {
    if (note.hasCastingDiscrepancy && note.totalReported !== undefined && note.totalComputed !== undefined) {
      // Don't duplicate if already captured as primary mismatch
      const alreadyCaptured = inconsistencies.some(i => i.noteRef?.includes(`Note ${noteNum}`));
      if (!alreadyCaptured) {
        inconsistencies.push({
          lineItem: `Note ${noteNum}: ${note.noteTitle} (Schedule Mathematical Footing)`,
          primaryFigure: `${doc.reportingScale} ${note.totalReported.toLocaleString('en-IN')}`,
          noteFigure: `${doc.reportingScale} ${note.totalComputed.toLocaleString('en-IN')}`,
          noteRef: `Note ${noteNum}`,
          discrepancy: `Internal schedule casting error: Sum of break-up items (${doc.reportingScale} ${note.totalComputed.toLocaleString('en-IN')}) does not tie to reported subtotal (${doc.reportingScale} ${note.totalReported.toLocaleString('en-IN')}). Discrepancy: ${doc.reportingScale} ${note.castingDifference?.toLocaleString('en-IN')}.`,
          riskLevel: 'High',
          type: 'casting_error',
        });
      }
    }
  }

  // 4. Cross-reference Cash Flow vs Balance Sheet Cash & Cash Equivalents
  const bsCash = doc.balanceSheetItems.find(i => i.name.toLowerCase().includes('cash and cash') || i.name.toLowerCase().includes('cash & cash'));
  const cfClosingCash = doc.cashFlowItems.find(i => i.name.toLowerCase().includes('cash and cash equivalents at the end') || i.name.toLowerCase().includes('closing cash') || i.name.toLowerCase().includes('cash and cash equivalents at end'));

  if (bsCash && cfClosingCash && bsCash.currentAmount !== undefined && cfClosingCash.currentAmount !== undefined) {
    const diff = Math.round((bsCash.currentAmount - cfClosingCash.currentAmount) * 100) / 100;
    if (Math.abs(diff) > 1.0) {
      inconsistencies.push({
        lineItem: 'Cash and Cash Equivalents (Balance Sheet vs Cash Flow Statement)',
        primaryFigure: `${doc.reportingScale} ${bsCash.currentAmount.toLocaleString('en-IN')} (Balance Sheet)`,
        noteFigure: `${doc.reportingScale} ${cfClosingCash.currentAmount.toLocaleString('en-IN')} (Cash Flow Statement)`,
        noteRef: 'Statement of Cash Flows & BS Note',
        discrepancy: `Closing Cash and Cash Equivalents in Cash Flow Statement (${doc.reportingScale} ${cfClosingCash.currentAmount.toLocaleString('en-IN')}) does not reconcile with Balance Sheet line item (${doc.reportingScale} ${bsCash.currentAmount.toLocaleString('en-IN')}). Ind AS 7 para 45 mismatch.`,
        riskLevel: 'High',
        type: 'numerical_mismatch',
      });
    }
  }

  // 5. Cross-reference Directors' Report / MD&A Text vs Financial Statements
  const rawText = doc.rawText;
  
  // Specific checks for common inconsistencies found in statutory audits
  // Check KMP Remuneration text vs Note 24 / P&L
  const kmpNote = Array.from(doc.notes.values()).find(n => n.noteTitle.toLowerCase().includes('related party') || n.noteTitle.toLowerCase().includes('kmp'));
  const directorReportMatch = rawText.match(/(?:Managing Director|MD|CEO|KMP)[^.\n]*remuneration[^.\n]*₹?\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:Lakhs|Crores)?/i);
  if (directorReportMatch && kmpNote) {
    const textKmpAmount = parseNumberString(directorReportMatch[1]);
    const noteKmpAmount = kmpNote.totalReported || kmpNote.totalComputed;
    if (textKmpAmount && noteKmpAmount && Math.abs(textKmpAmount - noteKmpAmount) > 5.0) {
      inconsistencies.push({
        lineItem: "KMP / Directors' Remuneration (Board's Report vs Note to Accounts)",
        primaryFigure: `${doc.reportingScale} ${textKmpAmount.toLocaleString('en-IN')} (Directors' Report)`,
        noteFigure: `${doc.reportingScale} ${noteKmpAmount.toLocaleString('en-IN')} (Note ${kmpNote.noteNumber})`,
        noteRef: `Note ${kmpNote.noteNumber}: ${kmpNote.noteTitle}`,
        discrepancy: `Contradiction between Governance commentary and financial disclosures: Board's Report mentions KMP remuneration of ${doc.reportingScale} ${textKmpAmount.toLocaleString('en-IN')}, but Note ${kmpNote.noteNumber} reports ${doc.reportingScale} ${noteKmpAmount.toLocaleString('en-IN')}.`,
        riskLevel: 'High',
        type: 'text_table_contradiction',
      });
    }
  }

  // Check Capex commentary vs PPE additions
  const capexMatch = rawText.match(/(?:incurred capital expenditure|capex of|addition to fixed assets)[^.\n]*₹?\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:Lakhs|Crores)?/i);
  const ppeNote = Array.from(doc.notes.values()).find(n => n.noteTitle.toLowerCase().includes('property, plant') || n.noteTitle.toLowerCase().includes('fixed asset'));
  if (capexMatch && ppeNote) {
    const textCapex = parseNumberString(capexMatch[1]);
    const ppeAdditions = ppeNote.breakupRows.find(r => r.name.toLowerCase().includes('additions'))?.currentAmount;
    if (textCapex && ppeAdditions && Math.abs(textCapex - ppeAdditions) > 10.0) {
      inconsistencies.push({
        lineItem: "Capital Expenditure / PPE Additions (MD&A Text vs Note 3)",
        primaryFigure: `${doc.reportingScale} ${textCapex.toLocaleString('en-IN')} (Management Commentary)`,
        noteFigure: `${doc.reportingScale} ${ppeAdditions.toLocaleString('en-IN')} (Note ${ppeNote.noteNumber} Additions)`,
        noteRef: `Note ${ppeNote.noteNumber}: ${ppeNote.noteTitle}`,
        discrepancy: `MD&A claims capital expenditure additions of ${doc.reportingScale} ${textCapex.toLocaleString('en-IN')}, but PPE Note rollforward records gross additions of only ${doc.reportingScale} ${ppeAdditions.toLocaleString('en-IN')}.`,
        riskLevel: 'Medium',
        type: 'text_table_contradiction',
      });
    }
  }

  // Check 11 Statutory Ratios with missing explanations
  for (const ratio of doc.ratios) {
    if (ratio.variancePercent && Math.abs(ratio.variancePercent) >= 25 && !ratio.explanationProvided) {
      inconsistencies.push({
        lineItem: `Statutory Ratio: ${ratio.name} (Variance > 25%)`,
        primaryFigure: `${ratio.currentRaw || ratio.currentValue} (Current) vs ${ratio.priorRaw || ratio.priorValue} (Prior)`,
        noteFigure: `Variance: ${ratio.variancePercent > 0 ? '+' : ''}${ratio.variancePercent.toFixed(1)}%`,
        noteRef: 'Schedule III Statutory Ratios Note',
        discrepancy: `Mandatory disclosure requirement violated: ${ratio.name} changed by ${ratio.variancePercent.toFixed(1)}% (exceeds 25% threshold), but mandatory explanation for variance required under Schedule III is missing.`,
        riskLevel: 'Medium',
        type: 'missing_note',
      });
    }
  }

  // If no inconsistencies were discovered, add clean assertion
  if (inconsistencies.length === 0) {
    // Keep array empty or minimal
  }

  return inconsistencies;
}
