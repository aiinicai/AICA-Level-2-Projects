import {
  Billing,
  Encounter,
  HospitalDepartment,
  Service,
  TariffDeviationItem,
  TariffMasterItem,
  TariffVarianceType,
} from '../types';
import { mapRevenueCentreToDepartment } from '../utils/departmentMapping';

export interface TariffIntelligenceSummary {
  totalServicesAnalyzed: number;
  deviationsCount: number;
  underbillingCount: number;
  overbillingCount: number;
  expiredTariffCount: number;
  missingTariffCount: number;
  totalNetVariance: number;
  underbilledExposure: number;
  overbilledExposure: number;
  deviationsByPayer: { payer: string; count: number; exposure: number }[];
  deviationsByDepartment: { department: HospitalDepartment | string; count: number; exposure: number }[];
}

export function executeTariffEngine(
  services: Service[],
  billings: Billing[],
  encounters: Encounter[],
  tariffMaster: TariffMasterItem[],
  investigationOverrides: Record<string, { status: TariffDeviationItem['status']; notes?: string; investigatedBy?: string }> = {}
): {
  deviations: TariffDeviationItem[];
  summary: TariffIntelligenceSummary;
} {
  const encounterMap = new Map<string, Encounter>();
  encounters.forEach((e) => encounterMap.set(e.Encounter_ID, e));

  const serviceMap = new Map<string, Service>();
  services.forEach((s) => serviceMap.set(s.Service_ID, s));

  const deviations: TariffDeviationItem[] = [];

  billings.forEach((b) => {
    const svc = serviceMap.get(b.Service_ID);
    if (!svc) return;

    const enc = encounterMap.get(svc.Encounter_ID);
    const payer = enc?.Payer_Type || 'Standard';

    // Find applicable tariff: try matching specific payer first, fallback to 'Standard'
    let applicableMaster = tariffMaster.find(
      (t) => t.Service_Code === svc.Service_Code && t.Payer.toLowerCase() === payer.toLowerCase()
    );

    if (!applicableMaster) {
      applicableMaster = tariffMaster.find(
        (t) => t.Service_Code === svc.Service_Code && t.Payer.toLowerCase() === 'standard'
      );
    }

    const devId = `TAR-DEV-${b.Bill_ID}`;
    const override = investigationOverrides[devId];

    if (!applicableMaster) {
      // Missing Tariff in master
      deviations.push({
        id: devId,
        serviceId: svc.Service_ID,
        encounterId: svc.Encounter_ID,
        serviceCode: svc.Service_Code,
        serviceDescription: svc.Description,
        revenueCentre: svc.Revenue_Centre,
        payer,
        expectedTariff: svc.Expected_Amount,
        applicableTariff: 0,
        actualBilled: b.Billed_Amount,
        variance: b.Billed_Amount,
        variancePercent: 100,
        varianceType: 'MISSING_TARIFF',
        effectiveFrom: 'N/A',
        effectiveTo: 'N/A',
        status: override?.status || 'PENDING_INVESTIGATION',
        investigatedBy: override?.investigatedBy,
        notes: override?.notes || 'No entry found in Tariff Master for this service code.',
      });
      return;
    }

    // Check expiry
    const sDate = svc.Service_DateTime.slice(0, 10);
    const isExpired = sDate < applicableMaster.Effective_From || sDate > applicableMaster.Effective_To;

    const expectedTariff = applicableMaster.Payer_Tariff || applicableMaster.Standard_Tariff;
    const actualBilled = b.Billed_Amount;
    const variance = Number((actualBilled - expectedTariff).toFixed(2));
    const variancePct = expectedTariff > 0 ? Number(((Math.abs(variance) / expectedTariff) * 100).toFixed(1)) : 0;

    // We consider material variance if difference is > 2% or expired
    if (isExpired) {
      deviations.push({
        id: devId,
        serviceId: svc.Service_ID,
        encounterId: svc.Encounter_ID,
        serviceCode: svc.Service_Code,
        serviceDescription: svc.Description,
        revenueCentre: svc.Revenue_Centre,
        payer,
        expectedTariff,
        applicableTariff: expectedTariff,
        actualBilled,
        variance,
        variancePercent: variancePct,
        varianceType: 'EXPIRED_TARIFF',
        effectiveFrom: applicableMaster.Effective_From,
        effectiveTo: applicableMaster.Effective_To,
        status: override?.status || 'PENDING_INVESTIGATION',
        investigatedBy: override?.investigatedBy,
        notes: override?.notes || `Service rendered on ${sDate} outside valid tariff schedule (${applicableMaster.Effective_From} to ${applicableMaster.Effective_To}).`,
      });
    } else if (Math.abs(variance) >= 50 && variancePct >= 2.0) {
      let vType: TariffVarianceType = 'STANDARD_VARIANCE';
      if (variance < 0) {
        vType = 'UNDERBILLING';
      } else if (variance > 0) {
        vType = 'OVERBILLING';
      }

      if (applicableMaster.Payer !== 'Standard') {
        vType = 'PAYER_TARIFF_VARIANCE';
      }

      deviations.push({
        id: devId,
        serviceId: svc.Service_ID,
        encounterId: svc.Encounter_ID,
        serviceCode: svc.Service_Code,
        serviceDescription: svc.Description,
        revenueCentre: svc.Revenue_Centre,
        payer,
        expectedTariff,
        applicableTariff: expectedTariff,
        actualBilled,
        variance,
        variancePercent: variancePct,
        varianceType: vType,
        effectiveFrom: applicableMaster.Effective_From,
        effectiveTo: applicableMaster.Effective_To,
        status: override?.status || 'PENDING_INVESTIGATION',
        investigatedBy: override?.investigatedBy,
        notes: override?.notes || (variance < 0 ? 'Underbilled against contracted tariff schedule.' : 'Billed amount exceeds contracted tariff schedule.'),
      });
    }
  });

  const underbillingCount = deviations.filter((d) => d.variance < 0).length;
  const overbillingCount = deviations.filter((d) => d.variance > 0).length;
  const expiredTariffCount = deviations.filter((d) => d.varianceType === 'EXPIRED_TARIFF').length;
  const missingTariffCount = deviations.filter((d) => d.varianceType === 'MISSING_TARIFF').length;

  const totalNetVariance = deviations.reduce((sum, d) => sum + d.variance, 0);
  const underbilledExposure = deviations
    .filter((d) => d.variance < 0)
    .reduce((sum, d) => sum + Math.abs(d.variance), 0);
  const overbilledExposure = deviations
    .filter((d) => d.variance > 0)
    .reduce((sum, d) => sum + d.variance, 0);

  // Group by Payer
  const payerMap = new Map<string, { count: number; exposure: number }>();
  deviations.forEach((d) => {
    const cur = payerMap.get(d.payer) || { count: 0, exposure: 0 };
    cur.count += 1;
    cur.exposure += Math.abs(d.variance);
    payerMap.set(d.payer, cur);
  });
  const deviationsByPayer = Array.from(payerMap.entries()).map(([payer, val]) => ({
    payer,
    count: val.count,
    exposure: Number(val.exposure.toFixed(2)),
  }));

  // Group by Department
  const deptMap = new Map<HospitalDepartment | string, { count: number; exposure: number }>();
  deviations.forEach((d) => {
    const dept = mapRevenueCentreToDepartment(d.revenueCentre);
    const cur = deptMap.get(dept) || { count: 0, exposure: 0 };
    cur.count += 1;
    cur.exposure += Math.abs(d.variance);
    deptMap.set(dept, cur);
  });
  const deviationsByDepartment = Array.from(deptMap.entries()).map(([department, val]) => ({
    department,
    count: val.count,
    exposure: Number(val.exposure.toFixed(2)),
  }));

  return {
    deviations,
    summary: {
      totalServicesAnalyzed: billings.length,
      deviationsCount: deviations.length,
      underbillingCount,
      overbillingCount,
      expiredTariffCount,
      missingTariffCount,
      totalNetVariance: Number(totalNetVariance.toFixed(2)),
      underbilledExposure: Number(underbilledExposure.toFixed(2)),
      overbilledExposure: Number(overbilledExposure.toFixed(2)),
      deviationsByPayer,
      deviationsByDepartment,
    },
  };
}

export function executeTariffIntelligenceEngine(
  tariffMaster: TariffMasterItem[],
  services: Service[],
  billings: Billing[],
  encounters: Encounter[],
  investigationOverrides: Record<string, { status: TariffDeviationItem['status']; notes?: string; investigatedBy?: string }> = {}
): {
  deviations: TariffDeviationItem[];
  summary: TariffIntelligenceSummary;
} {
  return executeTariffEngine(services, billings, encounters, tariffMaster, investigationOverrides);
}
