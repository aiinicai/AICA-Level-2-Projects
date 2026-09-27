import {
  Billing,
  DepartmentClearanceRecord,
  DepartmentClearanceStatus,
  Encounter,
  FinancialException,
  HospitalDepartment,
  Service,
} from '../types';
import { mapRevenueCentreToDepartment } from '../utils/departmentMapping';

export const ALL_HOSPITAL_DEPARTMENTS: HospitalDepartment[] = [
  'Laboratory',
  'Pharmacy',
  'Radiology',
  'OT/Surgery',
  'ICU',
  'Operations',
  'Stores',
  'Finance/Admin',
];

export interface DepartmentClearanceSummary {
  totalRecords: number;
  verifiedCount: number;
  pendingCount: number;
  disputedCount: number;
  correctionRequiredCount: number;
  unableToVerifyCount: number;
  clearancePercent: number;
  exposureAwaitingVerification: number;
  disputedExposure: number;
}

export function executeClearanceEngine(
  encounters: Encounter[],
  services: Service[],
  billings: Billing[],
  exceptions: FinancialException[],
  userOverrides: DepartmentClearanceRecord[] = []
): {
  records: DepartmentClearanceRecord[];
  summary: DepartmentClearanceSummary;
} {
  const overridesMap = new Map<string, DepartmentClearanceRecord>();
  userOverrides.forEach((rec) => overridesMap.set(rec.id, rec));

  const records: DepartmentClearanceRecord[] = [];

  // Group services by Encounter_ID
  const servicesByEnc = new Map<string, Service[]>();
  services.forEach((s) => {
    const list = servicesByEnc.get(s.Encounter_ID) || [];
    list.push(s);
    servicesByEnc.set(s.Encounter_ID, list);
  });

  // Group billings by Service_ID
  const billingByService = new Map<string, Billing[]>();
  billings.forEach((b) => {
    const list = billingByService.get(b.Service_ID) || [];
    list.push(b);
    billingByService.set(b.Service_ID, list);
  });

  // Group exceptions by Encounter_ID and Department
  const exceptionsByEncDept = new Map<string, FinancialException[]>();
  exceptions.forEach((exc) => {
    const dept = mapRevenueCentreToDepartment(exc.Revenue_Centre);
    const key = `${exc.Encounter_ID}__${dept}`;
    const list = exceptionsByEncDept.get(key) || [];
    list.push(exc);
    exceptionsByEncDept.set(key, list);
  });

  encounters.forEach((enc) => {
    const encSvcs = servicesByEnc.get(enc.Encounter_ID) || [];

    // Group services by Department
    const svcsByDept = new Map<HospitalDepartment | string, Service[]>();
    encSvcs.forEach((svc) => {
      const dept = mapRevenueCentreToDepartment(svc.Revenue_Centre);
      const list = svcsByDept.get(dept) || [];
      list.push(svc);
      svcsByDept.set(dept, list);
    });

    // Also include departments that have exceptions logged against this encounter
    ALL_HOSPITAL_DEPARTMENTS.forEach((dept) => {
      const deptSvcs = svcsByDept.get(dept) || [];
      const deptExceptions = exceptionsByEncDept.get(`${enc.Encounter_ID}__${dept}`) || [];

      // If no services and no exceptions, department is not applicable for this encounter
      if (deptSvcs.length === 0 && deptExceptions.length === 0) {
        return;
      }

      const id = `CLR-${enc.Encounter_ID}-${dept.replace(/[^a-zA-Z0-9]/g, '')}`;

      // Calculate service total and billed total
      let totalSvcAmt = 0;
      let totalBilledAmt = 0;

      deptSvcs.forEach((svc) => {
        totalSvcAmt += svc.Expected_Amount;
        const bList = billingByService.get(svc.Service_ID) || [];
        bList.forEach((b) => {
          totalBilledAmt += b.Billed_Amount;
        });
      });

      const unbilledExposure = deptExceptions
        .filter((e) => e.Control_ID === 'C01' || e.Control_ID === 'C04')
        .reduce((sum, e) => sum + e.Exposure_Amount, 0);

      const varianceExposure = deptExceptions
        .filter((e) => e.Control_ID === 'C02' || e.Control_ID === 'C03' || e.Control_ID === 'C08')
        .reduce((sum, e) => sum + e.Exposure_Amount, 0);

      // Check if user already reviewed/overrode this clearance item
      const override = overridesMap.get(id);

      let status: DepartmentClearanceStatus = 'VERIFIED';
      if (override) {
        status = override.status;
      } else if (deptExceptions.length > 0) {
        // By default, if exceptions exist, it is Pending Verification
        status = 'PENDING_VERIFICATION';
      }

      const clrRecord: DepartmentClearanceRecord = {
        id,
        encounterId: enc.Encounter_ID,
        department: dept,
        revenueCentre: deptSvcs[0]?.Revenue_Centre || dept,
        totalServicesCount: deptSvcs.length,
        totalServiceAmount: Number(totalSvcAmt.toFixed(2)),
        totalBilledAmount: Number(totalBilledAmt.toFixed(2)),
        unbilledExposure: Number(unbilledExposure.toFixed(2)),
        varianceExposure: Number(varianceExposure.toFixed(2)),
        status,
        exceptionCount: deptExceptions.length,
      };

      if (override?.reviewedBy) clrRecord.reviewedBy = override.reviewedBy;
      if (override?.reviewedAt) clrRecord.reviewedAt = override.reviewedAt;
      if (override?.comment) clrRecord.comment = override.comment;
      if (override?.evidenceRef) clrRecord.evidenceRef = override.evidenceRef;

      records.push(clrRecord);
    });
  });

  const totalRecords = records.length;
  const verifiedCount = records.filter((r) => r.status === 'VERIFIED').length;
  const pendingCount = records.filter((r) => r.status === 'PENDING_VERIFICATION').length;
  const disputedCount = records.filter((r) => r.status === 'DISPUTED').length;
  const correctionRequiredCount = records.filter((r) => r.status === 'CORRECTION_REQUIRED').length;
  const unableToVerifyCount = records.filter((r) => r.status === 'UNABLE_TO_VERIFY').length;

  const clearancePercent = totalRecords > 0 ? Number(((verifiedCount / totalRecords) * 100).toFixed(1)) : 100;

  const exposureAwaitingVerification = records
    .filter((r) => r.status === 'PENDING_VERIFICATION' || r.status === 'CORRECTION_REQUIRED')
    .reduce((sum, r) => sum + r.unbilledExposure + r.varianceExposure, 0);

  const disputedExposure = records
    .filter((r) => r.status === 'DISPUTED')
    .reduce((sum, r) => sum + r.unbilledExposure + r.varianceExposure, 0);

  return {
    records,
    summary: {
      totalRecords,
      verifiedCount,
      pendingCount,
      disputedCount,
      correctionRequiredCount,
      unableToVerifyCount,
      clearancePercent,
      exposureAwaitingVerification: Number(exposureAwaitingVerification.toFixed(2)),
      disputedExposure: Number(disputedExposure.toFixed(2)),
    },
  };
}

export function generateInitialClearanceRecords(
  encounters: Encounter[],
  services: Service[],
  billings: Billing[],
  exceptions: FinancialException[]
): DepartmentClearanceRecord[] {
  return executeClearanceEngine(encounters, services, billings, exceptions).records;
}

export function executeDepartmentClearanceEngine(
  records: DepartmentClearanceRecord[]
): DepartmentClearanceSummary {
  const totalRecords = records.length;
  const verifiedCount = records.filter((r) => r.status === 'VERIFIED').length;
  const pendingCount = records.filter((r) => r.status === 'PENDING_VERIFICATION').length;
  const disputedCount = records.filter((r) => r.status === 'DISPUTED').length;
  const correctionRequiredCount = records.filter((r) => r.status === 'CORRECTION_REQUIRED').length;
  const unableToVerifyCount = records.filter((r) => r.status === 'UNABLE_TO_VERIFY').length;

  const clearancePercent = totalRecords > 0 ? Number(((verifiedCount / totalRecords) * 100).toFixed(1)) : 100;

  const exposureAwaitingVerification = records
    .filter((r) => r.status === 'PENDING_VERIFICATION' || r.status === 'CORRECTION_REQUIRED')
    .reduce((sum, r) => sum + r.unbilledExposure + r.varianceExposure, 0);

  const disputedExposure = records
    .filter((r) => r.status === 'DISPUTED')
    .reduce((sum, r) => sum + r.unbilledExposure + r.varianceExposure, 0);

  return {
    totalRecords,
    verifiedCount,
    pendingCount,
    disputedCount,
    correctionRequiredCount,
    unableToVerifyCount,
    clearancePercent,
    exposureAwaitingVerification: Number(exposureAwaitingVerification.toFixed(2)),
    disputedExposure: Number(disputedExposure.toFixed(2)),
  };
}
