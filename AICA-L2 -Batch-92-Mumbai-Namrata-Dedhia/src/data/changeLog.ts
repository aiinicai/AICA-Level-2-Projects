import { ChangeLogRecord } from '../types/advisory';

export const INITIAL_CHANGE_LOG: ChangeLogRecord[] = [
  {
    change_id: 'CHG-2024-001',
    date: '2024-07-23',
    topic: 'TDS & Capital Gains on Immovable Property',
    old_position: 'LTCG on immovable property taxed at 20% with cost inflation indexation (CII).',
    new_position: 'Finance (No. 2) Act 2024 revised LTCG rate on real estate to 12.5% without indexation. Grandfathering choice (12.5% without indexation or 20% with indexation) introduced for resident individuals for properties acquired before 23 July 2024. For NRIs, application of indexation grandfathering requires specific evaluation by CA.',
    source: 'Finance (No. 2) Act, 2024, Sections 112 & 115AD amendments',
    reason: 'Statutory rationalization of capital gains tax framework across asset classes.',
    reviewed_by: 'Domain Architect / Senior NRI Tax Counsel',
    review_status: 'VERIFIED'
  },
  {
    change_id: 'CHG-2023-002',
    date: '2023-04-01',
    topic: 'DTAA Form 10F Mandatory Electronic Filing',
    old_position: 'Manual/physical Form 10F was accepted along with Tax Residency Certificate (TRC).',
    new_position: 'Directorate of Income Tax (Systems) mandated electronic submission of Form 10F on the e-filing portal for non-residents claiming DTAA relief where TRC lacks statutory particulars.',
    source: 'DGIT (Systems) Notification No. 03/2022 read with Order dated 28.03.2023',
    reason: 'Digital verification and portal automation for foreign tax withholding.',
    reviewed_by: 'FEMA & International Tax Lead',
    review_status: 'VERIFIED'
  },
  {
    change_id: 'CHG-2020-003',
    date: '2020-04-01',
    topic: 'Residential Status 120-Day Rule & Deemed Residence',
    old_position: 'Visiting Indian citizens/PIOs retained non-resident status if stay in India was under 182 days.',
    new_position: 'Finance Act 2020 reduced threshold from 182 days to 120 days for Indian citizens / PIOs visiting India having total income in India exceeding ₹15 Lakhs (excluding foreign sources). Introduced Deemed Resident under Section 6(1A) for stateless Indian citizens with Indian income > ₹15 Lakhs. Both categories classified as RNOR.',
    source: 'Finance Act 2020, Section 6(1) Expl. 1(b) & Section 6(1A)',
    reason: 'Anti-abuse measure against tax residency planning without territorial taxation.',
    reviewed_by: 'Senior Tax Counsel',
    review_status: 'VERIFIED'
  }
];
