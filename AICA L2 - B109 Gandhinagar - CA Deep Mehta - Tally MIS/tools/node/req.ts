import * as R from '../src/server/connectors/tally/requests.js';
const s=[R.voucherRangeRequest('Demo & Co','2024-04-01','2024-04-30'), R.companyListRequest(), ...Object.values(R.masterRequests('Demo & Co','2026-09-30','2024-04-01')), R.stockValuationRequest('Demo & Co','2024-04-01','2024-04-30'), R.voucherRangeRequest('Demo & Co','2024-04-01','2024-04-30',55)];
console.log(JSON.stringify(s));
