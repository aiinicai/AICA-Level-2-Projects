import { BusinessUnit } from '../core/types';

export const BUSINESS_UNITS: BusinessUnit[] = [
  // 5 Hospitals
  {
    code: 'H01',
    name: 'Meridian Hospital Abu Dhabi',
    type: 'Hospital',
    emirate: 'Abu Dhabi',
    vatTrn: '100234567800001',
    status: 'Active',
  },
  {
    code: 'H02',
    name: 'Meridian Hospital Dubai',
    type: 'Hospital',
    emirate: 'Dubai',
    vatTrn: '100234567800002',
    status: 'Active',
  },
  {
    code: 'H03',
    name: 'Meridian Hospital Sharjah',
    type: 'Hospital',
    emirate: 'Sharjah',
    vatTrn: '100234567800003',
    status: 'Active',
  },
  {
    code: 'H04',
    name: 'Meridian Hospital Al Ain',
    type: 'Hospital',
    emirate: 'Abu Dhabi',
    vatTrn: '100234567800004',
    status: 'Active',
  },
  {
    code: 'H05',
    name: 'Meridian Hospital Ras Al Khaimah',
    type: 'Hospital',
    emirate: 'Ras Al Khaimah',
    vatTrn: '100234567800005',
    status: 'Active',
  },

  // 5 Clinics
  {
    code: 'C01',
    name: 'Meridian Clinic Khalifa City',
    type: 'Clinic',
    emirate: 'Abu Dhabi',
    vatTrn: '100234567800006',
    status: 'Active',
  },
  {
    code: 'C02',
    name: 'Meridian Clinic Jumeirah',
    type: 'Clinic',
    emirate: 'Dubai',
    vatTrn: '100234567800007',
    status: 'Active',
  },
  {
    code: 'C03',
    name: 'Meridian Clinic Al Nahda',
    type: 'Clinic',
    emirate: 'Sharjah',
    vatTrn: '100234567800008',
    status: 'Active',
  },
  {
    code: 'C04',
    name: 'Meridian Clinic Al Jimi',
    type: 'Clinic',
    emirate: 'Abu Dhabi',
    vatTrn: '100234567800009',
    status: 'Active',
  },
  {
    code: 'C05',
    name: 'Meridian Clinic Al Nakheel',
    type: 'Clinic',
    emirate: 'Ras Al Khaimah',
    vatTrn: '100234567800010',
    status: 'Active',
  },

  // 5 Pharmacies
  {
    code: 'P01',
    name: 'Meridian Pharmacy Corniche',
    type: 'Pharmacy',
    emirate: 'Abu Dhabi',
    vatTrn: '100234567800011',
    status: 'Active',
  },
  {
    code: 'P02',
    name: 'Meridian Pharmacy Marina',
    type: 'Pharmacy',
    emirate: 'Dubai',
    vatTrn: '100234567800012',
    status: 'Active',
  },
  {
    code: 'P03',
    name: 'Meridian Pharmacy Muweilah',
    type: 'Pharmacy',
    emirate: 'Sharjah',
    vatTrn: '100234567800013',
    status: 'Active',
  },
  {
    code: 'P04',
    name: 'Meridian Pharmacy Al Ain Mall',
    type: 'Pharmacy',
    emirate: 'Abu Dhabi',
    vatTrn: '100234567800014',
    status: 'Active',
  },
  {
    code: 'P05',
    name: 'Meridian Pharmacy Julphar Road',
    type: 'Pharmacy',
    emirate: 'Ras Al Khaimah',
    vatTrn: '100234567800015',
    status: 'Active',
  },
];

export function getBUByCode(code: string): BusinessUnit | undefined {
  return BUSINESS_UNITS.find((b) => b.code === code);
}
