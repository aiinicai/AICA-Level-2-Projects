import {
  AuditTrailRun,
  Billing,
  Claim,
  Collection,
  ControlId,
  ControlRuleConfig,
  DashboardMetrics,
  DischargeMonitorRow,
  Encounter,
  FinancialException,
  Service,
  Severity,
} from '../types';
import { formatINR } from '../utils/formatters';
import { getLatestTransactionDate, getClaimsPendingAdjudication } from '../utils/arCalculations';

export const DEFAULT_CONFIG: ControlRuleConfig = {
  amountMismatchTolerancePercent: 5.0, // 5%
  tpaShortfallTolerancePercent: 5.0, // 5%
  collectionDueDays: 30, // 30 days
  unusualDiscountPercent: 10.0, // 10%
  criticalExposureThreshold: 5000.0, // $5,000
  highExposureThreshold: 1500.0, // $1,500
};

export interface ControlRunResult {
  runId: string;
  timestamp: string;
  auditTrail: AuditTrailRun;
  exceptions: FinancialException[];
  metrics: DashboardMetrics;
  dischargeMonitor: DischargeMonitorRow[];
}

/**
 * Deterministically evaluate all 8 financial controls on the hospital datasets.
 * Strict rules: No AI involved in calculations or severity ratings.
 */
export function executeControlEngine(
  encounters: Encounter[],
  services: Service[],
  billings: Billing[],
  claims: Claim[],
  collections: Collection[],
  config: ControlRuleConfig = DEFAULT_CONFIG,
  user: string = 'CFO (System)',
  existingExceptions: FinancialException[] = []
): ControlRunResult {
  const runId = `RUN-${Date.now().toString().slice(-6)}`;
  // Dynamic as-of date: anchored to latest transaction in the dataset, falls back to real wall-clock time
  const now = getLatestTransactionDate(billings, collections, encounters, claims);
  const todayStr = now.toISOString().split('T')[0];

  const generatedExceptions: FinancialException[] = [];

  // Indexing structures for deterministic performance
  const encountersMap = new Map<string, Encounter>();
  encounters.forEach((e) => encountersMap.set(e.Encounter_ID, e));

  const servicesByEncounter = new Map<string, Service[]>();
  services.forEach((s) => {
    const list = servicesByEncounter.get(s.Encounter_ID) || [];
    list.push(s);
    servicesByEncounter.set(s.Encounter_ID, list);
  });

  const billingByEncounter = new Map<string, Billing[]>();
  const billingByService = new Map<string, Billing>();
  billings.forEach((b) => {
    const list = billingByEncounter.get(b.Encounter_ID) || [];
    list.push(b);
    billingByEncounter.set(b.Encounter_ID, list);
    if (b.Service_ID) {
      billingByService.set(b.Service_ID, b);
    }
  });

  const claimsByEncounter = new Map<string, Claim[]>();
  claims.forEach((c) => {
    const list = claimsByEncounter.get(c.Encounter_ID) || [];
    list.push(c);
    claimsByEncounter.set(c.Encounter_ID, list);
  });

  const collectionsByEncounter = new Map<string, Collection[]>();
  collections.forEach((col) => {
    const list = collectionsByEncounter.get(col.Encounter_ID) || [];
    list.push(col);
    collectionsByEncounter.set(col.Encounter_ID, list);
  });

  let excCounter = 1;
  const nextId = (prefix: string) => `EXC-${prefix}-${String(excCounter++).padStart(3, '0')}`;

  // ==========================================
  // C01 — Unbilled Service
  // Service exists but has no corresponding billing record.
  // Exposure = Expected Amount.
  // ==========================================
  services.forEach((svc) => {
    const billingRecord = billingByService.get(svc.Service_ID);
    if (!billingRecord) {
      const encounter = encountersMap.get(svc.Encounter_ID);
      const isDischarged = encounter?.Discharge_Status === 'Discharged';
      let sev: Severity = 'MEDIUM';
      if (isDischarged && svc.Expected_Amount >= config.highExposureThreshold) {
        sev = 'CRITICAL';
      } else if (isDischarged || svc.Expected_Amount >= 1000) {
        sev = 'HIGH';
      } else if (svc.Expected_Amount < 250) {
        sev = 'LOW';
      }

      generatedExceptions.push({
        Exception_ID: nextId('C01'),
        Run_ID: runId,
        Encounter_ID: svc.Encounter_ID,
        Control_ID: 'C01',
        Revenue_Centre: svc.Revenue_Centre,
        Description: `Unbilled clinical service: ${svc.Description} (${svc.Service_Code}). Expected tariff ${formatINR(svc.Expected_Amount)} has no corresponding bill.`,
        Exposure_Amount: Number(svc.Expected_Amount.toFixed(2)),
        Severity: sev,
        Status: 'OPEN',
        Created_Date: todayStr,
        Assigned_To: 'Billing Lead',
        Resolution: '',
        Resolved_Date: null,
      });
    }
  });

  // ==========================================
  // C02 — Quantity Mismatch
  // Service Quantity differs from Billed Quantity.
  // Exposure = relevant billing variance.
  // ==========================================
  services.forEach((svc) => {
    const b = billingByService.get(svc.Service_ID);
    if (b && svc.Quantity !== b.Billed_Quantity) {
      const unitExpected = svc.Quantity > 0 ? svc.Expected_Amount / svc.Quantity : 0;
      const unbilledQty = svc.Quantity - b.Billed_Quantity;
      const exposure = Math.abs(unbilledQty * unitExpected);

      let sev: Severity = 'MEDIUM';
      if (exposure >= config.criticalExposureThreshold) sev = 'CRITICAL';
      else if (exposure >= config.highExposureThreshold) sev = 'HIGH';
      else if (exposure < 200) sev = 'LOW';

      generatedExceptions.push({
        Exception_ID: nextId('C02'),
        Run_ID: runId,
        Encounter_ID: svc.Encounter_ID,
        Control_ID: 'C02',
        Revenue_Centre: svc.Revenue_Centre,
        Description: `Quantity mismatch: Service recorded ${svc.Quantity} units, but only ${b.Billed_Quantity} units were billed (${svc.Description}).`,
        Exposure_Amount: Number(exposure.toFixed(2)),
        Severity: sev,
        Status: 'OPEN',
        Created_Date: todayStr,
        Assigned_To: 'Pharmacy/Stores Manager',
        Resolution: '',
        Resolved_Date: null,
      });
    }
  });

  // ==========================================
  // C03 — Amount Mismatch
  // Expected service amount differs materially from billed amount.
  // Default tolerance = 5%.
  // Exposure = absolute amount variance.
  // ==========================================
  services.forEach((svc) => {
    const b = billingByService.get(svc.Service_ID);
    if (b && svc.Expected_Amount > 0) {
      const variance = Math.abs(svc.Expected_Amount - b.Billed_Amount);
      const variancePct = (variance / svc.Expected_Amount) * 100;

      if (variancePct > config.amountMismatchTolerancePercent && variance >= 50) {
        let sev: Severity = 'MEDIUM';
        if (variance >= config.criticalExposureThreshold) sev = 'CRITICAL';
        else if (variance >= config.highExposureThreshold) sev = 'HIGH';
        else if (variance < 200) sev = 'LOW';

        generatedExceptions.push({
          Exception_ID: nextId('C03'),
          Run_ID: runId,
          Encounter_ID: svc.Encounter_ID,
          Control_ID: 'C03',
          Revenue_Centre: svc.Revenue_Centre,
          Description: `Material tariff variance: Billed amount ${formatINR(b.Billed_Amount)} deviates by ${variancePct.toFixed(1)}% from expected tariff ${formatINR(svc.Expected_Amount)} (${svc.Description}).`,
          Exposure_Amount: Number(variance.toFixed(2)),
          Severity: sev,
          Status: 'OPEN',
          Created_Date: todayStr,
          Assigned_To: 'Tariff Audit Desk',
          Resolution: '',
          Resolved_Date: null,
        });
      }
    }
  });

  // ==========================================
  // C04 — Post-Billing Service
  // Service timestamp is later than the relevant final bill timestamp.
  // Exposure = Expected Amount.
  // ==========================================
  encounters.forEach((enc) => {
    const encBills = billingByEncounter.get(enc.Encounter_ID) || [];
    const finalBills = encBills.filter((b) => b.Bill_Status === 'Final');
    if (finalBills.length > 0) {
      // Find latest final bill time
      const latestFinalBillTime = finalBills.reduce((latest, b) => {
        return b.Bill_DateTime > latest ? b.Bill_DateTime : latest;
      }, finalBills[0].Bill_DateTime);

      const encServices = servicesByEncounter.get(enc.Encounter_ID) || [];
      encServices.forEach((svc) => {
        if (svc.Service_DateTime > latestFinalBillTime) {
          let sev: Severity = 'HIGH';
          if (svc.Expected_Amount >= config.highExposureThreshold) sev = 'CRITICAL';
          else if (svc.Expected_Amount < 300) sev = 'MEDIUM';

          generatedExceptions.push({
            Exception_ID: nextId('C04'),
            Run_ID: runId,
            Encounter_ID: enc.Encounter_ID,
            Control_ID: 'C04',
            Revenue_Centre: svc.Revenue_Centre,
            Description: `Post-billing service captured: ${svc.Description} entered at ${svc.Service_DateTime}, after final bill closure at ${latestFinalBillTime}. Risk of unbilled discharge leakage.`,
            Exposure_Amount: Number(svc.Expected_Amount.toFixed(2)),
            Severity: sev,
            Status: 'OPEN',
            Created_Date: todayStr,
            Assigned_To: 'Discharge Coordinator',
            Resolution: '',
            Resolved_Date: null,
          });
        }
      });
    }
  });

  // ==========================================
  // C05 — Missing/Pending Final Bill
  // Discharged encounter has no final bill or billing remains provisional.
  // Exposure = relevant unbilled/provisional amount.
  // ==========================================
  encounters.forEach((enc) => {
    if (enc.Discharge_Status === 'Discharged') {
      const encBills = billingByEncounter.get(enc.Encounter_ID) || [];
      const hasFinalBill = encBills.some((b) => b.Bill_Status === 'Final');

      if (!hasFinalBill) {
        const provisionalTotal = encBills
          .filter((b) => b.Bill_Status === 'Provisional')
          .reduce((sum, b) => sum + b.Billed_Amount, 0);

        const encServices = servicesByEncounter.get(enc.Encounter_ID) || [];
        const unbilledServices = encServices.filter((s) => !billingByService.has(s.Service_ID));
        const unbilledAmount = unbilledServices.reduce((sum, s) => sum + s.Expected_Amount, 0);

        const totalExposure = Math.max(provisionalTotal + unbilledAmount, 100);

        let sev: Severity = 'CRITICAL';
        if (totalExposure < config.highExposureThreshold) sev = 'HIGH';

        generatedExceptions.push({
          Exception_ID: nextId('C05'),
          Run_ID: runId,
          Encounter_ID: enc.Encounter_ID,
          Control_ID: 'C05',
          Revenue_Centre: 'Billing / Finance',
          Description: `Discharged patient missing final bill closure. Billing status is provisional or incomplete with unfinalized exposure of ${formatINR(totalExposure)}.`,
          Exposure_Amount: Number(totalExposure.toFixed(2)),
          Severity: sev,
          Status: 'OPEN',
          Created_Date: todayStr,
          Assigned_To: 'Inpatient Billing Manager',
          Resolution: '',
          Resolved_Date: null,
        });
      }
    }
  });

  // ==========================================
  // C06 — TPA Shortfall
  // Claim Amount minus Approved Amount exceeds 5% tolerance.
  // Exposure = Claim Amount - Approved Amount.
  // ==========================================
  claims.forEach((claim) => {
    if (claim.Claim_Amount > 0 && claim.Approved_Amount >= 0 && claim.Claim_Status !== 'Submitted') {
      const shortfall = claim.Claim_Amount - claim.Approved_Amount;
      const shortfallPct = (shortfall / claim.Claim_Amount) * 100;

      if (shortfallPct > config.tpaShortfallTolerancePercent && shortfall > 50) {
        let sev: Severity = 'MEDIUM';
        if (shortfall >= config.criticalExposureThreshold) sev = 'CRITICAL';
        else if (shortfall >= config.highExposureThreshold) sev = 'HIGH';
        else if (shortfall < 300) sev = 'LOW';

        generatedExceptions.push({
          Exception_ID: nextId('C06'),
          Run_ID: runId,
          Encounter_ID: claim.Encounter_ID,
          Control_ID: 'C06',
          Revenue_Centre: 'TPA Desk',
          Description: `TPA claim adjudication shortfall: Insurer approved ${formatINR(claim.Approved_Amount)} against submitted claim ${formatINR(claim.Claim_Amount)} (${shortfallPct.toFixed(1)}% disallowed, ${formatINR(shortfall)} shortfall).`,
          Exposure_Amount: Number(shortfall.toFixed(2)),
          Severity: sev,
          Status: 'OPEN',
          Created_Date: todayStr,
          Assigned_To: 'Insurance TPA Coordinator',
          Resolution: '',
          Resolved_Date: null,
        });
      }
    }
  });

  // ==========================================
  // C07 — Collection Outstanding
  // Amount remains outstanding beyond 30 days from discharge/collection due basis.
  // Exposure = outstanding amount.
  // ==========================================
  encounters.forEach((enc) => {
    if (enc.Discharge_Date) {
      const dischargeDate = new Date(enc.Discharge_Date);
      const diffTime = Math.abs(now.getTime() - dischargeDate.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

      if (diffDays > config.collectionDueDays) {
        const encBills = billingByEncounter.get(enc.Encounter_ID) || [];
        const totalBilled = encBills.reduce((sum, b) => sum + b.Billed_Amount, 0);

        const encCols = collectionsByEncounter.get(enc.Encounter_ID) || [];
        const totalCollected = encCols.reduce((sum, c) => sum + c.Amount, 0);

        const outstanding = totalBilled - totalCollected;

        if (outstanding > 50) {
          let sev: Severity = 'HIGH';
          if (diffDays > 60 || outstanding >= config.criticalExposureThreshold) {
            sev = 'CRITICAL';
          } else if (outstanding < 300) {
            sev = 'MEDIUM';
          }

          generatedExceptions.push({
            Exception_ID: nextId('C07'),
            Run_ID: runId,
            Encounter_ID: enc.Encounter_ID,
            Control_ID: 'C07',
            Revenue_Centre: 'Cashier / Collections',
            Description: `Aged outstanding receivable: ${formatINR(outstanding)} uncollected ${diffDays} days post-discharge (Total billed: ${formatINR(totalBilled)}, Collected: ${formatINR(totalCollected)}).`,
            Exposure_Amount: Number(outstanding.toFixed(2)),
            Severity: sev,
            Status: 'OPEN',
            Created_Date: todayStr,
            Assigned_To: 'Collections Officer',
            Resolution: '',
            Resolved_Date: null,
          });
        }
      }
    }
  });

  // ==========================================
  // C08 — Unusual Discount
  // Discount exceeds 10%.
  // Exposure = discount amount.
  // ==========================================
  billings.forEach((b) => {
    if (b.Discount > 0) {
      const grossAmount = b.Billed_Amount + b.Discount;
      const discountPct = grossAmount > 0 ? (b.Discount / grossAmount) * 100 : 0;

      if (discountPct > config.unusualDiscountPercent) {
        let sev: Severity = 'MEDIUM';
        if (b.Discount >= config.criticalExposureThreshold) sev = 'CRITICAL';
        else if (b.Discount >= config.highExposureThreshold || discountPct > 20) sev = 'HIGH';
        else if (b.Discount < 200) sev = 'LOW';

        generatedExceptions.push({
          Exception_ID: nextId('C08'),
          Run_ID: runId,
          Encounter_ID: b.Encounter_ID,
          Control_ID: 'C08',
          Revenue_Centre: 'Finance / Admin',
          Description: `Unusual discount applied: ${formatINR(b.Discount)} (${discountPct.toFixed(1)}%) on bill ${b.Bill_ID}, exceeding authorized ${config.unusualDiscountPercent}% threshold.`,
          Exposure_Amount: Number(b.Discount.toFixed(2)),
          Severity: sev,
          Status: 'OPEN',
          Created_Date: todayStr,
          Assigned_To: 'Finance Director',
          Resolution: '',
          Resolved_Date: null,
        });
      }
    }
  });

  // ==========================================
  // Deterministic Multi-Exception Severity Escalation
  // If an encounter has >= 2 exceptions, bump severity by 1 step
  // ==========================================
  const exceptionsByEnc = new Map<string, FinancialException[]>();
  generatedExceptions.forEach((e) => {
    const list = exceptionsByEnc.get(e.Encounter_ID) || [];
    list.push(e);
    exceptionsByEnc.set(e.Encounter_ID, list);
  });

  generatedExceptions.forEach((exc) => {
    const siblingCount = (exceptionsByEnc.get(exc.Encounter_ID) || []).length;
    if (siblingCount >= 2 && exc.Severity !== 'CRITICAL') {
      if (exc.Severity === 'LOW') exc.Severity = 'MEDIUM';
      else if (exc.Severity === 'MEDIUM') exc.Severity = 'HIGH';
      else if (exc.Severity === 'HIGH' && exc.Exposure_Amount > 1000) exc.Severity = 'CRITICAL';
    }
  });

  // Merge with any preserved resolutions from existingExceptions if user has updated statuses
  if (existingExceptions.length > 0) {
    const existingMap = new Map<string, FinancialException>();
    existingExceptions.forEach((ex) => existingMap.set(ex.Exception_ID, ex));

    generatedExceptions.forEach((gen) => {
      const match = existingMap.get(gen.Exception_ID);
      if (match) {
        gen.Status = match.Status;
        gen.Assigned_To = match.Assigned_To;
        gen.Resolution = match.Resolution;
        gen.Resolved_Date = match.Resolved_Date;
      }
    });
  }

  // ==========================================
  // Compute Complete Dashboard Metrics
  // ==========================================
  const activeExceptions = generatedExceptions.filter(
    (e) => e.Status === 'OPEN' || e.Status === 'UNDER_REVIEW'
  );

  const todaysDischarges = encounters.filter(
    (e) => e.Discharge_Date === todayStr && e.Discharge_Status === 'Discharged'
  ).length;

  const grossBilling = billings.reduce((sum, b) => sum + b.Billed_Amount, 0);
  const grossBilledPreDiscount = billings.reduce((sum, b) => sum + b.Billed_Amount + (Number(b.Discount) || 0), 0);
  const totalExpectedAmount = services.length > 0
    ? services.reduce((sum, s) => sum + s.Expected_Amount, 0)
    : grossBilling;
  const billingCaptureRate = totalExpectedAmount > 0
    ? Number(((grossBilling / totalExpectedAmount) * 100).toFixed(1))
    : 100;
  const potentialFinancialExposure = activeExceptions.reduce(
    (sum, e) => sum + e.Exposure_Amount,
    0
  );

  // Use canonical pending filter (consistent with TpaCollectionsView - F08 audit fix)
  const tpaPendingAmount = getClaimsPendingAdjudication(claims)
    .reduce((sum, c) => sum + c.Claim_Amount, 0);

  const totalCollected = collections.reduce((sum, c) => sum + c.Amount, 0);
  const outstandingCollections = Math.max(0, grossBilling - totalCollected);

  // Group by Revenue Centre
  const revCenterExposureMap = new Map<string, { amount: number; count: number }>();
  activeExceptions.forEach((e) => {
    const curr = revCenterExposureMap.get(e.Revenue_Centre) || { amount: 0, count: 0 };
    curr.amount += e.Exposure_Amount;
    curr.count += 1;
    revCenterExposureMap.set(e.Revenue_Centre, curr);
  });
  const exposureByRevenueCentre = Array.from(revCenterExposureMap.entries())
    .map(([name, data]) => ({ name, amount: Number(data.amount.toFixed(2)), count: data.count }))
    .sort((a, b) => b.amount - a.amount);

  // Group by Control
  const controlOrder: ControlId[] = ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08'];
  const exceptionsByControl = controlOrder.map((cid) => {
    const exList = activeExceptions.filter((e) => e.Control_ID === cid);
    const count = exList.length;
    const exposure = exList.reduce((sum, e) => sum + e.Exposure_Amount, 0);
    const titles: Record<ControlId, string> = {
      C01: 'C01 Unbilled Service',
      C02: 'C02 Qty Mismatch',
      C03: 'C03 Amount Mismatch',
      C04: 'C04 Post-Billing Svc',
      C05: 'C05 Missing Final Bill',
      C06: 'C06 TPA Shortfall',
      C07: 'C07 Overdue Receivables',
      C08: 'C08 Unusual Discount',
    };
    return {
      controlId: cid,
      title: titles[cid],
      count,
      exposure: Number(exposure.toFixed(2)),
    };
  });

  // Group by Department
  const deptExposureMap = new Map<string, { count: number; exposure: number }>();
  activeExceptions.forEach((e) => {
    const enc = encountersMap.get(e.Encounter_ID);
    const dept = enc?.Department || 'General';
    const curr = deptExposureMap.get(dept) || { count: 0, exposure: 0 };
    curr.count += 1;
    curr.exposure += e.Exposure_Amount;
    deptExposureMap.set(dept, curr);
  });
  const exceptionsByDepartment = Array.from(deptExposureMap.entries())
    .map(([department, data]) => ({
      department,
      count: data.count,
      exposure: Number(data.exposure.toFixed(2)),
    }))
    .sort((a, b) => b.exposure - a.exposure);

  // Priority Exceptions (sorted by exposure descending, CRITICAL/HIGH prioritized)
  const priorityExceptions = [...activeExceptions]
    .sort((a, b) => {
      const sevScore = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
      const diff = sevScore[b.Severity] - sevScore[a.Severity];
      return diff !== 0 ? diff : b.Exposure_Amount - a.Exposure_Amount;
    })
    .slice(0, 10);

  // Lifecycle Funnel
  const claimedTotal = claims.reduce((sum, c) => sum + c.Claim_Amount, 0);
  const approvedTotal = claims.reduce((sum, c) => sum + c.Approved_Amount, 0);

  // Discharge Monitor Table Generation (Deduplicated by Encounter_ID)
  const uniqueEncountersMap = new Map<string, Encounter>();
  for (const enc of encounters) {
    if (enc.Encounter_ID && !uniqueEncountersMap.has(enc.Encounter_ID)) {
      uniqueEncountersMap.set(enc.Encounter_ID, enc);
    }
  }
  const dischargeMonitor: DischargeMonitorRow[] = Array.from(uniqueEncountersMap.values()).map((enc) => {
    const encBills = billingByEncounter.get(enc.Encounter_ID) || [];
    const encSvcs = servicesByEncounter.get(enc.Encounter_ID) || [];
    const encClaims = claimsByEncounter.get(enc.Encounter_ID) || [];
    const encCols = collectionsByEncounter.get(enc.Encounter_ID) || [];
    const encExceptions = activeExceptions.filter((e) => e.Encounter_ID === enc.Encounter_ID);

    const billedAmt = encBills.reduce((sum, b) => sum + b.Billed_Amount, 0);
    const expectedAmt = encSvcs.reduce((sum, s) => sum + s.Expected_Amount, 0);
    const collectedAmt = encCols.reduce((sum, c) => sum + c.Amount, 0);

    // Completeness
    let billingCompleteness: DischargeMonitorRow['Billing_Completeness'] = 'Complete';
    if (encBills.length === 0 && encSvcs.length > 0) {
      billingCompleteness = 'No Billing';
    } else if (encBills.every((b) => b.Bill_Status === 'Provisional')) {
      billingCompleteness = 'Provisional Only';
    } else if (encSvcs.some((s) => !billingByService.has(s.Service_ID))) {
      billingCompleteness = 'Unbilled Items';
    }

    // TPA Status
    let tpaStatus: DischargeMonitorRow['TPA_Status'] = 'Not Applicable';
    if (enc.Payer_Type.includes('TPA') || encClaims.length > 0) {
      if (encClaims.some((c) => c.Claim_Status === 'Partially Approved')) {
        tpaStatus = 'Partially Approved';
      } else if (encClaims.some((c) => c.Claim_Status === 'Approved')) {
        tpaStatus = 'Approved';
      } else if (encClaims.some((c) => c.Claim_Status === 'Rejected')) {
        tpaStatus = 'Rejected';
      } else {
        tpaStatus = 'Pending';
      }
    }

    // Collection Status
    let collectionStatus: DischargeMonitorRow['Collection_Status'] = 'Uncollected';
    if (billedAmt > 0 && collectedAmt >= billedAmt) {
      collectionStatus = 'Fully Collected';
    } else if (collectedAmt > 0) {
      collectionStatus = 'Partially Collected';
    } else if (enc.Discharge_Date) {
      const dDate = new Date(enc.Discharge_Date);
      const days = Math.ceil(Math.abs(now.getTime() - dDate.getTime()) / (1000 * 60 * 60 * 24));
      if (days > 30) collectionStatus = 'Overdue >30d';
    }

    // Highest Severity
    const severities = encExceptions.map((e) => e.Severity);
    let highestSeverity: DischargeMonitorRow['Highest_Severity'] = 'NONE';
    if (severities.includes('CRITICAL')) highestSeverity = 'CRITICAL';
    else if (severities.includes('HIGH')) highestSeverity = 'HIGH';
    else if (severities.includes('MEDIUM')) highestSeverity = 'MEDIUM';
    else if (severities.includes('LOW')) highestSeverity = 'LOW';

    const totalExposure = encExceptions.reduce((sum, e) => sum + e.Exposure_Amount, 0);

    return {
      Encounter_ID: enc.Encounter_ID,
      Department: enc.Department,
      Ward: enc.Ward,
      Payer_Type: enc.Payer_Type,
      Discharge_Status: enc.Discharge_Status,
      Admission_Date: enc.Admission_Date,
      Discharge_Date: enc.Discharge_Date,
      Billed_Amount: Number(billedAmt.toFixed(2)),
      Expected_Amount: Number(expectedAmt.toFixed(2)),
      Billing_Completeness: billingCompleteness,
      TPA_Status: tpaStatus,
      Collection_Status: collectionStatus,
      Exception_Count: encExceptions.length,
      Highest_Severity: highestSeverity,
      Total_Exposure: Number(totalExposure.toFixed(2)),
    };
  });

  const totalRecords =
    encounters.length + services.length + billings.length + claims.length + collections.length;

  const auditTrail: AuditTrailRun = {
    Run_ID: runId,
    Run_Date_Time: new Date().toISOString().replace('T', ' ').slice(0, 19),
    Data_Period: (() => {
      const allDates: string[] = [
        ...billings.map((b) => (b.Bill_Date || b.Bill_DateTime || '').slice(0, 10)),
        ...encounters.map((e) => (e.Discharge_Date || e.Admission_Date || '')),
      ].filter(Boolean).sort();
      const minDate = allDates[0] || todayStr;
      const maxDate = allDates[allDates.length - 1] || todayStr;
      return minDate === maxDate ? minDate : `${minDate} to ${maxDate}`;
    })(),
    Records_Processed: totalRecords,
    Controls_Executed: 8,
    Exceptions_Generated: generatedExceptions.length,
    User: user,
  };

  return {
    runId,
    timestamp: new Date().toISOString(),
    auditTrail,
    exceptions: generatedExceptions,
    metrics: {
      todaysDischarges,
      grossBilling: Number(grossBilling.toFixed(2)),
      totalExpectedAmount: Number(totalExpectedAmount.toFixed(2)),
      potentialFinancialExposure: Number(potentialFinancialExposure.toFixed(2)),
      openExceptionsCount: activeExceptions.length,
      tpaPendingAmount: Number(tpaPendingAmount.toFixed(2)),
      outstandingCollections: Number(outstandingCollections.toFixed(2)),
      billingCaptureRate,
      grossBilledPreDiscount: Number(grossBilledPreDiscount.toFixed(2)),
      criticalExceptionsCount: activeExceptions.filter((e) => e.Severity === 'CRITICAL').length,
      highExceptionsCount: activeExceptions.filter((e) => e.Severity === 'HIGH').length,
      mediumExceptionsCount: activeExceptions.filter((e) => e.Severity === 'MEDIUM').length,
      lowExceptionsCount: activeExceptions.filter((e) => e.Severity === 'LOW').length,
      exposureByRevenueCentre,
      exceptionsByControl,
      exceptionsByDepartment,
      priorityExceptions,
      funnel: {
        captured: Number(totalExpectedAmount.toFixed(2)),
        billed: Number(grossBilling.toFixed(2)),
        claimed: Number(claimedTotal.toFixed(2)),
        approved: Number(approvedTotal.toFixed(2)),
        collected: Number(totalCollected.toFixed(2)),
      },
    },
    dischargeMonitor,
  };
}
