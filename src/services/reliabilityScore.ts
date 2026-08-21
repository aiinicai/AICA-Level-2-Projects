import { Asset, RiskFinding, AssetReliabilityScore, ReliabilityDriver } from '../types';

export function calculateAssetReliabilityScore(
  assets: Asset[],
  risks: RiskFinding[]
): AssetReliabilityScore {
  const totalAssets = assets.length || 1;

  // 1. Physical Verification (Weight 25%)
  const verifiedAssets = assets.filter((a) => a.verificationStatus === 'Verified').length;
  const pvRatio = verifiedAssets / totalAssets;
  const pvScore = Math.round(pvRatio * 100);

  // 2. Documentation Completeness (Weight 20%)
  const missingDocAssets = risks.filter(
    (r) => r.riskType === 'Missing Documents' && r.status !== 'Closed'
  ).length;
  const docScore = Math.max(0, Math.round(((totalAssets - missingDocAssets * 2) / totalAssets) * 100));

  // 3. Location Accuracy (Weight 15%)
  const wrongLocationCount = risks.filter(
    (r) => r.riskType === 'Wrong Location' && r.status !== 'Closed'
  ).length;
  const locationScore = Math.max(0, Math.round(((totalAssets - wrongLocationCount * 2.5) / totalAssets) * 100));

  // 4. Capitalisation Quality & Componentisation (Weight 15%)
  const duplicateCapCount = risks.filter(
    (r) => (r.riskType === 'Duplicate Capitalisation' || r.riskType === 'Duplicate Invoice') && r.status !== 'Closed'
  ).length;
  const capQualityScore = Math.max(0, Math.round(((totalAssets - duplicateCapCount * 3) / totalAssets) * 100));

  // 5. Policy & Useful Life Compliance (Weight 10%)
  const policyDeviations = risks.filter(
    (r) => (r.riskType === 'Abnormal Useful Life' || r.riskType === 'Potential Impairment') && r.status !== 'Closed'
  ).length;
  const policyScore = Math.max(0, Math.round(((totalAssets - policyDeviations * 2.5) / totalAssets) * 100));

  // 6. Disposal & Scrap Realisation Accuracy (Weight 10%)
  const ghostDisposalCount = risks.filter(
    (r) => (r.riskType === 'Disposed Still Depreciating' || r.riskType === 'Ghost Asset') && r.status !== 'Closed'
  ).length;
  const disposalScore = Math.max(0, Math.round(((totalAssets - ghostDisposalCount * 3.5) / totalAssets) * 100));

  // 7. Exception Health & Resolution Velocity (Weight 5%)
  const totalRisks = risks.length || 1;
  const resolvedRisks = risks.filter((r) => r.status === 'Approved' || r.status === 'Closed').length;
  const exceptionHealthScore = Math.round((resolvedRisks / totalRisks) * 100);

  const drivers: ReliabilityDriver[] = [
    {
      name: 'Physical Verification Coverage',
      score: pvScore,
      weight: 0.25,
      weightedScore: Math.round(pvScore * 0.25),
      status: pvScore >= 80 ? 'Good' : pvScore >= 60 ? 'Fair' : 'Critical',
      description: `${verifiedAssets} of ${totalAssets} assets verified with QR/Barcode scans`,
      findingsCount: totalAssets - verifiedAssets
    },
    {
      name: 'Documentation Completeness',
      score: docScore,
      weight: 0.20,
      weightedScore: Math.round(docScore * 0.20),
      status: docScore >= 85 ? 'Good' : docScore >= 70 ? 'Fair' : 'Critical',
      description: 'Availability of matching PO, Tax Invoices, GRN and Put-to-Use certificates',
      findingsCount: missingDocAssets
    },
    {
      name: 'Location & Plant Accuracy',
      score: locationScore,
      weight: 0.15,
      weightedScore: Math.round(locationScore * 0.15),
      status: locationScore >= 85 ? 'Good' : locationScore >= 70 ? 'Fair' : 'Critical',
      description: 'Physical location synchronized with Fixed Asset subledger without unapproved movement',
      findingsCount: wrongLocationCount
    },
    {
      name: 'Capitalisation & Componentisation',
      score: capQualityScore,
      weight: 0.15,
      weightedScore: Math.round(capQualityScore * 0.15),
      status: capQualityScore >= 85 ? 'Good' : capQualityScore >= 70 ? 'Fair' : 'Critical',
      description: 'Ind AS 16 component accounting rigor & prevention of duplicate capitalisation',
      findingsCount: duplicateCapCount
    },
    {
      name: 'Policy & Useful Life Compliance',
      score: policyScore,
      weight: 0.10,
      weightedScore: Math.round(policyScore * 0.10),
      status: policyScore >= 85 ? 'Good' : policyScore >= 70 ? 'Fair' : 'Critical',
      description: 'Companies Act Schedule II & Ind AS 36 impairment indicators',
      findingsCount: policyDeviations
    },
    {
      name: 'Disposal & De-recognition Integrity',
      score: disposalScore,
      weight: 0.10,
      weightedScore: Math.round(disposalScore * 0.10),
      status: disposalScore >= 85 ? 'Good' : disposalScore >= 70 ? 'Fair' : 'Critical',
      description: 'Zero ghost assets and timely retirement of scrapped plant equipment',
      findingsCount: ghostDisposalCount
    },
    {
      name: 'Exception Resolution Velocity',
      score: exceptionHealthScore,
      weight: 0.05,
      weightedScore: Math.round(exceptionHealthScore * 0.05),
      status: exceptionHealthScore >= 60 ? 'Good' : exceptionHealthScore >= 30 ? 'Fair' : 'Critical',
      description: 'Timeliness of internal audit remediation and management review sign-off',
      findingsCount: totalRisks - resolvedRisks
    }
  ];

  const totalScore = Math.min(100, Math.max(0, drivers.reduce((acc, d) => acc + d.weightedScore, 0)));

  let grade: AssetReliabilityScore['grade'] = 'A (Strong)';
  if (totalScore >= 90) grade = 'A+ (Exemplary)';
  else if (totalScore >= 80) grade = 'A (Strong)';
  else if (totalScore >= 70) grade = 'B (Moderate Risk)';
  else if (totalScore >= 55) grade = 'C (Action Required)';
  else grade = 'D (Severe Deficiencies)';

  let summary = '';
  if (totalScore >= 80) {
    summary = 'Register reflects robust internal controls with minor open physical verification and documentation remediation items.';
  } else if (totalScore >= 65) {
    summary = 'Moderate risk identified. Immediate management action required on ghost asset de-recognition and location discrepancies prior to statutory audit.';
  } else {
    summary = 'Material control deficiencies detected. High risk of CARO 2020 adverse qualification if unaddressed.';
  }

  return {
    totalScore,
    grade,
    drivers,
    summary,
    lastCalculated: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
  };
}

export function formatINR(val: number, formatMode: 'Lakhs' | 'Crores' | 'Full' = 'Lakhs'): string {
  if (formatMode === 'Crores') {
    return `₹${(val / 10000000).toFixed(2)} Cr`;
  }
  if (formatMode === 'Lakhs') {
    return `₹${(val / 100000).toFixed(2)} L`;
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(val);
}

export const calculateReliabilityScore = calculateAssetReliabilityScore;

