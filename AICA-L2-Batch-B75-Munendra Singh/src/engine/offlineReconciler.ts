export interface ReconcilerRow {
  name: string;
  amount: string;
  isDeduction: boolean;
}

export interface ReconcilerResult {
  primaryAmount: number;
  noteComputedSum: number;
  variance: number;
  isTallied: boolean;
  memo: string;
}

export function performOfflineReconciliation(
  primaryLineName: string,
  primaryAmountStr: string,
  noteTitle: string,
  rows: ReconcilerRow[]
): ReconcilerResult {
  const primaryAmount = parseFloat(primaryAmountStr.replace(/[^0-9.-]/g, '')) || 0;

  const noteComputedSum = rows.reduce((acc, r) => {
    const val = parseFloat(r.amount.replace(/[^0-9.-]/g, '')) || 0;
    return r.isDeduction ? acc - val : acc + val;
  }, 0);

  const variance = Math.round((primaryAmount - noteComputedSum) * 100) / 100;
  const isTallied = Math.abs(variance) < 0.01;

  let memo = '';

  if (isTallied) {
    memo = `### STATUTORY AUDIT RECONCILIATION MEMO: TALLIED
**Line Item:** ${primaryLineName}  
**Note Schedule:** ${noteTitle}  
**Date:** ${new Date().toLocaleDateString('en-IN')}  

---

**1. Verification Summary:**
- Primary Statement Face Amount: **₹ ${primaryAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}**
- Sum of Note Breakup Schedule: **₹ ${noteComputedSum.toLocaleString('en-IN', { minimumFractionDigits: 2 })}**
- Net Variance / Discrepancy: **₹ 0.00 (Perfect Match)**

**2. Audit Conclusion:**
The schedule items mathematically tie to the face figure. Casting and footing validation is confirmed in accordance with Ind AS presentation standards. No adjustment journal entry required.`;
  } else {
    const isOverstated = variance > 0;
    memo = `### STATUTORY AUDIT RECONCILIATION MEMO: VARIANCE DETECTED
**Line Item:** ${primaryLineName}  
**Note Schedule:** ${noteTitle}  
**Date:** ${new Date().toLocaleDateString('en-IN')}  

---

**1. Mathematical Verification & Casting:**
- Primary Statement Face Amount: **₹ ${primaryAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}**
- Sum of Note Schedule Items: **₹ ${noteComputedSum.toLocaleString('en-IN', { minimumFractionDigits: 2 })}**
- Net Discrepancy (Variance): **₹ ${Math.abs(variance).toLocaleString('en-IN', { minimumFractionDigits: 2 })} (${isOverstated ? 'Primary Face Exceeds Note Sum' : 'Note Sum Exceeds Primary Face'})**

**2. Audit Analysis & Risk Assessment:**
The reported line item '${primaryLineName}' does not reconcile with the sub-schedules provided in '${noteTitle}'. This presents a material casting discrepancy under ICAI Schedule III Guidance Note and Ind AS 1.

**3. Recommended Corrective Journal Entry (Pre-Signing):**
\`\`\`text
${isOverstated ? `[Dr] Expense / Reconciling Variance Suspense A/c      ₹ ${Math.abs(variance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
      [Cr] ${primaryLineName} (Carrying Asset / Face)          ₹ ${Math.abs(variance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
(Being adjustment to align face of financial statement with verified note sub-breakups)` : `[Dr] ${primaryLineName} (Carrying Asset / Face)          ₹ ${Math.abs(variance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
      [Cr] Retained Earnings / Reconciling Suspense A/c     ₹ ${Math.abs(variance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
(Being adjustment to recognize unmapped schedule items on face of financial statements)`}
\`\`\`

**4. Statutory Action:**
Management must either adjust the General Ledger trial balance or amend the draft Note to Accounts schedule before final Audit Committee sign-off.`;
  }

  return {
    primaryAmount,
    noteComputedSum,
    variance,
    isTallied,
    memo,
  };
}
